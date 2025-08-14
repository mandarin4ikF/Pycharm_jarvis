"""
Асинхронный клиент для взаимодействия с локальным Ollama API.
Поддерживает потоковую генерацию (streaming), автоматические повторы запросов и полную обработку ошибок.
Оптимизирован для интеграции с LangChain и CrewAI. Использует llama3.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Optional, Any

import httpx

logger = logging.getLogger(__name__)


class OllamaAPIError(Exception):
    """Исключение для ошибок API Ollama с деталями статуса и ответа."""
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(f"Ошибка API Ollama [{status_code}]: {message}")


class OllamaClient:
    """
    Асинхронный клиент для Ollama с поддержкой контекстного менеджера, повторов и полного стриминга.
    
    Особенности:
    - Полная поддержка потоковой передачи (возвращает оригинальные JSON-чанки)
    - Умные повторы: только для 5xx ошибок и сетевых сбоев
    - Экспоненциальная задержка между попытками
    - Интеграция с системой логирования для отладки и мониторинга
    - Совместим с LangChain (использует httpx)
    - Поддержка кастомных параметров модели (температура, контекст и т.д.)

    Работает с llama3 (и другими моделями Ollama).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,  # Увеличено для llama3
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 16.0
    ):
        """
        Инициализация клиента.

        Args:
            base_url: Адрес сервера Ollama (по умолчанию — локальный)
            timeout: Общий таймаут на один запрос (в секундах)
            max_retries: Максимальное число попыток при ошибках
            initial_backoff: Начальная задержка перед повтором (в секундах)
            max_backoff: Максимальная задержка между попытками
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout)
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self._session: Optional[httpx.AsyncClient] = None
        logger.info("OllamaClient инициализирован | URL=%s | Таймаут=%.1fс", base_url, timeout)

    async def __aenter__(self):
        """Создаёт HTTP-сессию при входе в контекст."""
        self._session = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает сессию при выходе из контекста."""
        if self._session:
            await self._session.aclose()
            self._session = None
            logger.debug("HTTP-сессия закрыта")

    async def generate(
        self,
        prompt: str,
        model: str = "llama3",  # Изменено: теперь по умолчанию llama3
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,  # Добавлено: поддержка format=json
        system: Optional[str] = None,  # Добавлено: system prompt
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Отправляет запрос к модели Ollama и возвращает ответ.

        Args:
            prompt: Входной текст для модели
            model: Название модели (по умолчанию — "llama3")
            stream: Если True — возвращает поток чанков по мере генерации
            options: Дополнительные параметры модели (температура, длина контекста и т.д.)
            format: Если "json", модель попытается вернуть JSON (требует поддержки от модели)
            system: Системный промпт (например, "Ты — ассистент Jarvis")
            **kwargs: Любые другие поля, поддерживаемые Ollama API

        Yields:
            Словарь с данными от Ollama (включая "response", "done", "model", "context" и др.)

        Raises:
            OllamaAPIError: При ошибках 4xx (клиент) или 5xx (сервер), если превышено число попыток
            RuntimeError: Если клиент используется без контекстного менеджера
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": options or {},
            **kwargs
        }

        if system:
            payload["system"] = system
        if format:
            payload["format"] = format

        if not self._session:
            raise RuntimeError("OllamaClient должен использоваться внутри 'async with'")

        logger.debug("Отправка запроса | Модель=%s | Длина промпта=%d", model, len(prompt))

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()

                if stream:
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                yield chunk
                                response_part = chunk.get("response", "")[:50]
                                logger.debug("Получен чанк | Модель=%s | Ответ: %s...", 
                                           chunk.get("model", "неизвестно"), response_part)
                            except json.JSONDecodeError:
                                logger.error("Ошибка парсинга JSON в потоке: %s", line)
                                continue
                else:
                    full_response = response.json()
                    yield full_response
                    logger.debug("Полный ответ получен | Модель=%s", full_response.get("model", "неизвестно"))

                break  # Успех

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt >= self.max_retries:
                    logger.error("Все попытки подключения исчерпаны: %s", e)
                    raise
                logger.warning("Ошибка сети (попытка %d/%d): %s", attempt + 1, self.max_retries, e)
                await asyncio.sleep(self._get_backoff(attempt))

            except httpx.HTTPStatusError as e:
                if 500 <= e.response.status_code < 600:
                    if attempt >= self.max_retries:
                        error_text = e.response.text
                        logger.error("Ошибка сервера %d после всех попыток: %s", e.response.status_code, error_text)
                        raise OllamaAPIError(e.response.status_code, error_text)
                    logger.warning("Ошибка сервера %d — повтор...", e.response.status_code)
                    await asyncio.sleep(self._get_backoff(attempt))
                else:
                    error_text = e.response.text
                    response_json = None
                    content_type = e.response.headers.get("content-type", "")
                    if "json" in content_type:
                        try:
                            response_json = e.response.json()
                        except json.JSONDecodeError:
                            pass
                    logger.error("Ошибка клиента %d: %s", e.response.status_code, error_text)
                    raise OllamaAPIError(e.response.status_code, error_text, response_json)

    def _get_backoff(self, attempt: int) -> float:
        """Вычисляет экспоненциальную задержку между попытками."""
        backoff = min(self.initial_backoff * (2 ** attempt), self.max_backoff)
        logger.debug("Задержка перед повтором: %.1f сек (попытка %d)", backoff, attempt)
        return backoff


# === ТЕСТОВОЕ ВЫПОЛНЕНИЕ ===
if __name__ == "__main__":
    """
    Пример использования OllamaClient с llama3.
    Убедитесь, что:
    1. Ollama запущен: `ollama serve`
    2. Модель загружена: `ollama pull llama3`
    """

    async def main():
        try:
            async with OllamaClient(timeout=120.0) as client:
                print("➡️ Отправка запроса в Ollama (llama3)...")
                print("Ответ (streaming): ", end="", flush=True)

                full_response = ""
                async for chunk in client.generate(
                    prompt="Расскажи о теории относительности Эйнштейна в двух абзацах",
                    model="llama3",
                    stream=True,
                    options={"temperature": 0.7, "num_ctx": 4096},
                    system="Ты — научный ассистент Jarvis. Отвечай кратко и точно."
                ):
                    text = chunk.get("response", "")
                    print(text, end="", flush=True)
                    full_response += text

                print("\n\n✅ Генерация завершена.")
                if full_response.strip():
                    print(f"Объём ответа: {len(full_response.strip())} символов.")
                else:
                    print("❌ Ответ пуст — проверьте, запущен ли Ollama и доступна ли модель 'llama3'.")

        except Exception as e:
            print(f"\n\n🔴 Ошибка: {e}")
            if "Connection refused" in str(e):
                print("💡 Подсказка: Убедитесь, что Ollama запущен командой `ollama serve` в отдельном терминале.")
            elif "404" in str(e) or "model not found" in str(e).lower():
                print("💡 Подсказка: Установите модель: `ollama pull llama3`")
            else:
                print(f"💡 Проверьте логи и настройки. Ошибка: {e}")

    asyncio.run(main())