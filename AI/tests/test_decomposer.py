import pytest
import json
from unittest.mock import MagicMock, AsyncMock


# Добавляем корневую папку проекта в sys.path для корректных импортов
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from src.core.decomposer import TaskDecomposer
from src.core.llm_client import OllamaClient


# --- Моки ответов от LLM для разных сценариев ---


# Корректный ответ
VALID_PLAN_JSON = """
{
 "title": "Тестовый план",
 "tasks": [
   { "id": 1, "description": "Шаг 1", "agent": "CodeGenerator", "dependencies": [] },
   { "id": 2, "description": "Шаг 2", "agent": "CodeExecutor", "dependencies": [1] }
 ]
}
"""


# Ответ, который не является JSON
INVALID_JSON = "Это точно не JSON"


# Ответ с нарушенной структурой (отсутствуют обязательные ключи)
PLAN_WITH_MISSING_KEYS = '{"title": "План", "tasks": [{"id": 1, "agent": "CodeGenerator"}]}'


# Ответ с некорректной зависимостью (задача ссылается на несуществующий id)
PLAN_WITH_BAD_DEPENDENCY = """
{
 "title": "План с ошибкой",
 "tasks": [
   { "id": 1, "description": "Шаг 1", "agent": "CodeGenerator", "dependencies": [99] }
 ]
}
"""


@pytest.fixture
def mock_ollama_client():
   """
   Фикстура, которая создает имитацию (мок) клиента Ollama.
   Это позволяет нам тестировать логику декомпозитора, не делая реальных вызовов к LLM.
   """
   client = MagicMock(spec=OllamaClient)
   # Для асинхронных методов используется AsyncMock
   client.invoke = AsyncMock()
   return client


@pytest.mark.asyncio
async def test_decompose_successful(mock_ollama_client):
   """
   Тест "счастливого пути": LLM возвращает корректный JSON с первого раза.
   """
   mock_ollama_client.invoke.return_value = VALID_PLAN_JSON
   decomposer = TaskDecomposer("test_model", mock_ollama_client)
  
   plan = await decomposer.decompose("сделай что-нибудь")
  
   # Проверяем, что метод invoke был вызван один раз
   mock_ollama_client.invoke.assert_awaited_once()
   # Проверяем, что результат корректно распарсился
   assert plan["title"] == "Тестовый план"
   assert len(plan["tasks"]) == 2


@pytest.mark.asyncio
async def test_decompose_retries_on_invalid_json(mock_ollama_client):
   """
   Тест механизма повторных попыток: LLM сначала возвращает мусор, а со второй попытки - валидный JSON.
   """
   mock_ollama_client.invoke.side_effect = [INVALID_JSON, VALID_PLAN_JSON]
   decomposer = TaskDecomposer("test_model", mock_ollama_client, max_retries=2)


   plan = await decomposer.decompose("цель")
  
   # Проверяем, что было ровно две попытки
   assert mock_ollama_client.invoke.call_count == 2
   # Проверяем, что в итоге мы получили корректный план
   assert plan["title"] == "Тестовый план"


@pytest.mark.asyncio
async def test_decompose_fails_after_all_retries(mock_ollama_client):
   """
   Тест полного провала: LLM все время возвращает некорректные данные.
   """
   mock_ollama_client.invoke.return_value = INVALID_JSON
   decomposer = TaskDecomposer("test_model", mock_ollama_client, max_retries=2)


   # Проверяем, что decomposer выбрасывает исключение ValueError после всех неудачных попыток
   with pytest.raises(ValueError, match="Не удалось сгенерировать валидный план"):
       await decomposer.decompose("цель")
  
   # Проверяем, что было сделано ровно столько попыток, сколько указано в max_retries
   assert mock_ollama_client.invoke.call_count == 2


@pytest.mark.asyncio
async def test_validation_fails_on_bad_dependency(mock_ollama_client):
   """
   Тест внутренней логики валидации: LLM вернул JSON, но в нем логическая ошибка (несуществующая зависимость).
   """
   mock_ollama_client.invoke.return_value = PLAN_WITH_BAD_DEPENDENCY
   decomposer = TaskDecomposer("test_model", mock_ollama_client, max_retries=1)


   # Проверяем, что будет выброшено исключение с конкретным текстом ошибки
   with pytest.raises(ValueError, match="ссылается на несуществующую зависимость 99"):
       await decomposer.decompose("цель")