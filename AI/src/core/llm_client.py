# src/core/llm_client.py
import logging
import asyncio
from typing import Dict, Any
import httpx


logger = logging.getLogger(__name__)


class OllamaClient:
   def __init__(self, config: Dict[str, Any]):
       self.base_url = config.get("base_url", "http://localhost:11434")
       self.timeout = config.get("request_timeout", 180.0)
       self.max_retries = config.get("max_retries", 3)
       self.retry_delay = config.get("retry_delay", 1.0)
       self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
       logger.info(f"Клиент Ollama инициализирован для URL: {self.base_url}")


   async def invoke(self, model: str, system_prompt: str, user_prompt: str) -> str:
       payload = {
           "model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
           "format": "json", "stream": False
       }
       last_exception = None
       for attempt in range(self.max_retries):
           try:
               logger.info(f"Отправка запроса к Ollama (модель: {model}, попытка {attempt + 1})...")
               response = await self.client.post("/api/chat", json=payload)
               response.raise_for_status()
               content = response.json().get("message", {}).get("content", "")
               if not content: raise ValueError("Ответ LLM не содержит 'content'.")
               return content.strip()
           except (httpx.RequestError, httpx.HTTPStatusError) as e:
               logger.warning(f"Ошибка при запросе к Ollama: {e}. Попытка {attempt + 1} из {self.max_retries}.")
               last_exception = e
               await asyncio.sleep(self.retry_delay * (2 ** attempt))
       raise ConnectionError(f"Не удалось подключиться к Ollama после {self.max_retries} попыток.") from last_exception


   async def close(self):
       await self.client.aclose()
