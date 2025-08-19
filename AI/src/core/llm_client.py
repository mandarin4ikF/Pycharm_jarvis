# src/core/llm_client.py
import logging
import time

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Клиент для взаимодействия с LLM (симуляция).
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        logger.info(f"Инициализирован (симулированный) LLM клиент для модели: {self.model_name}")

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        logger.info(f"Вызов LLM (симуляция) с промптом: {user_prompt[:100]}...")
        time.sleep(1) # Имитация работы сети и модели
        mock_response = """
{
  "title": "Создание простого Flask-приложения с API и тестами",
  "tasks": [
    { "id": 1, "description": "Создать базовую структуру проекта: папки app/, tests/, requirements.txt.", "agent": "CodeGenerator", "dependencies": [] },
    { "id": 2, "description": "Написать основной файл приложения app/__init__.py с инициализацией Flask.", "agent": "CodeGenerator", "dependencies": [1] },
    { "id": 3, "description": "Реализовать эндпоинт /api/hello, возвращающий JSON.", "agent": "CodeGenerator", "dependencies": [2] },
    { "id": 4, "description": "Написать unit-тест для эндпоинта /api/hello.", "agent": "TestGenerator", "dependencies": [3] },
    { "id": 5, "description": "Запустить тесты и убедиться, что они проходят.", "agent": "CodeExecutor", "dependencies": [4] },
    { "id": 6, "description": "Подготовить финальный отчет о выполненной работе.", "agent": "ReportGenerator", "dependencies": [5] }
  ]
}
        """
        logger.info("LLM (симуляция) вернул структурированный план.")
        return mock_response.strip()

