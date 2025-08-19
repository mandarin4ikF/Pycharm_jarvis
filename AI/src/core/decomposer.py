# src/core/decomposer.py
import json
import logging
from typing import Dict, Any
from src.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """
Ты — 'Jarvis Planner', элитный ИИ-агент по планированию и декомпозиции задач. Твоя единственная цель — разбивать сложные, высокоуровневые цели на последовательность четких, атомарных и выполнимых подзадач.
ПРАВИЛА:
1.  **Формат вывода**: Ты ОБЯЗАН отвечать ТОЛЬКО в формате JSON. Никаких лишних слов до или после JSON-объекта.
2.  **Структура JSON**: Твой JSON должен иметь структуру: {"title": "...", "tasks": [{"id": 1, "description": "...", "agent": "...", "dependencies": []}]}.
3.  **Атомарность задач**: Каждая подзадача должна быть максимально простой и представлять собой один логический шаг.
4.  **Выбор агента**: В поле `agent` выбери наиболее подходящего исполнителя из списка: `CodeGenerator`, `TestGenerator`, `CodeExecutor`, `Researcher`, `ReportGenerator`.
"""

class TaskDecomposer:
    def __init__(self, planning_model_name: str, max_retries: int = 3):
        self.llm_client = LLMClient(model_name=planning_model_name)
        self.max_retries = max_retries

    def decompose(self, goal: str) -> Dict[str, Any]:
        for attempt in range(self.max_retries):
            logger.info(f"Попытка декомпозиции цели (попытка {attempt + 1}/{self.max_retries})...")
            raw_response = self.llm_client.invoke(system_prompt=PLANNER_SYSTEM_PROMPT, user_prompt=goal)
            try:
                plan = json.loads(raw_response)
                self._validate_plan(plan)
                logger.info(f"Декомпозиция успешна. Создано {len(plan.get('tasks', []))} задач.")
                return plan
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка валидации/декодирования плана: {e}")
        error_message = "Не удалось сгенерировать валидный план после нескольких попыток."
        logger.error(error_message)
        raise ValueError(error_message)

    @staticmethod
    def _validate_plan(plan: Dict[str, Any]):
        if not isinstance(plan, dict): raise ValueError("План не является словарем.")
        if "title" not in plan or not isinstance(plan["title"], str): raise ValueError("Отсутствует ключ 'title'.")
        if "tasks" not in plan or not isinstance(plan["tasks"], list): raise ValueError("Отсутствует ключ 'tasks'.")
        task_ids = {task["id"] for task in plan["tasks"] if isinstance(task.get("id"), int)}
        for task in plan["tasks"]:
            if not all(k in task for k in ["id", "description", "agent", "dependencies"]): raise ValueError(f"Задача {task.get('id', '?')} имеет неполную структуру.")
            for dep_id in task["dependencies"]:
                if dep_id not in task_ids: raise ValueError(f"Задача {task['id']} ссылается на несуществующую зависимость {dep_id}.")
