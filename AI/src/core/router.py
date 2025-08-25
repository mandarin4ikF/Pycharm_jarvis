import logging
from typing import Optional, Tuple, Dict, Any
from src.utils.config_loader import load_config
from src.core.context import CONTEXT


logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """
Ты — 'Jarvis Router', сверхбыстрый и эффективный ИИ-диспетчер. Твоя единственная задача — проанализировать запрос пользователя и классифицировать его по одной из трёх категорий.

Категории:
- `simple`: Простой вопрос, требующий короткого фактического ответа.
- `medium`: Генерация кода, инструкции или объяснения.
- `complex`: Многошаговая задача, требующая планирования и проверки.

❗ Твой ответ ДОЛЖЕН быть ТОЛЬКО одним словом: `simple`, `medium` или `complex`.
❗ Никаких кавычек, JSON, объяснений, знаков препинания.
❗ Только одно слово, в нижнем регистре.
❗ Примеры правильных ответов: simple, complex, medium

Запрос: {prompt}
Ответ:
"""


class RequestRouter:
   """
   Маршрутизирует запросы, используя LLM для интеллектуальной классификации.
   """
   def __init__(self, config_path: str = "src/config/routing.yaml"):
       try:
           self.config = load_config(config_path)
           self.router_model = self.config.get("router_model", "phi3:mini")
           self.complexity_map = self.config.get("complexity_map", {})
           logger.info(f"LLM-Роутер инициализирован. Модель для маршрутизации: {self.router_model}")
       except Exception as e:
           logger.critical(f"Не удалось инициализировать LLM-Роутер: {e}")
           raise


   async def route(self, prompt: str) -> Tuple[str, Optional[str]]:
       """
       Классифицирует промпт с помощью LLM и возвращает уровень сложности и модель.
       """
       try:
           # Используем ollama_client из глобального контекста
           raw_classification = await CONTEXT.ollama_client.invoke(
               model=self.router_model,
               system_prompt=ROUTER_SYSTEM_PROMPT,
               user_prompt=prompt
           )
          
           # Очищаем ответ от возможных лишних символов
           classification = raw_classification.strip().lower()


           if classification not in self.complexity_map:
               logger.warning(f"LLM-роутер вернул неизвестную категорию '{classification}'. По умолчанию используется 'simple'.")
               classification = "simple"


           model_name = self.complexity_map.get(classification)
           return classification, model_name


       except Exception as e:
           logger.error(f"Ошибка при LLM-маршрутизации: {e}. По умолчанию используется 'simple'.")
           return "simple", self.complexity_map.get("simple")
