# src/core/decomposer.py
import json
import logging
import asyncio
from typing import Dict, Any
from src.core.llm_client import OllamaClient


logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """
Ты — 'Jarvis Planner', элитный ИИ-агент по планированию и декомпозиции задач. Твоя единственная цель — разбивать сложные, высокоуровневые цели на последовательность четких, атомарных и выполнимых подзадач.
ПРАВИЛА:
1.  **Формат вывода**: Ты ОБЯЗАН отвечать ТОЛЬКО в формате JSON.
2.  **Структура JSON**: {"title": "...", "tasks": [{"id": 1, "description": "...", "agent": "...", "dependencies": []}]}.
3.  **Атомарность**: Каждая задача - один логический шаг.
4.  **Выбор агента**: Используй только этих агентов: `CodeGenerator`, `TestGenerator`, `CodeExecutor`, `Researcher`, `ReportGenerator`.
"""


class TaskDecomposer:
   def __init__(self, planning_model_name: str, ollama_client: OllamaClient, max_retries: int = 3):
       self.model_name = planning_model_name
       self.llm_client = ollama_client
       self.max_retries = max_retries


   async def decompose(self, goal: str) -> Dict[str, Any]:
       for attempt in range(self.max_retries):
           try:
               raw_response = await self.llm_client.invoke(self.model_name, PLANNER_SYSTEM_PROMPT, goal)
               plan = json.loads(raw_response)
               self._validate_plan(plan)
               return plan
           except (json.JSONDecodeError, ValueError) as e:
               logger.warning(f"Ошибка валидации/декодирования плана: {e}, попытка {attempt + 1}")
               await asyncio.sleep(1)
           except Exception as e:
               logger.error(f"Непредвиденная ошибка при декомпозиции: {e}")
               break
       raise ValueError("Не удалось сгенерировать валидный план после нескольких попыток.")


   @staticmethod
   def _validate_plan(plan: Dict[str, Any]):
       if not isinstance(plan, dict): raise ValueError("План не словарь.")
       if "title" not in plan: raise ValueError("Нет ключа 'title'.")
       if "tasks" not in plan or not isinstance(plan["tasks"], list): raise ValueError("Нет ключа 'tasks'.")
       task_ids = {t["id"] for t in plan["tasks"] if isinstance(t.get("id"), int)}
       for task in plan["tasks"]:
           if not all(k in task for k in ["id", "description", "agent", "dependencies"]):
               raise ValueError(f"Задача {task.get('id', '?')} неполная.")
           for dep_id in task["dependencies"]:
               if dep_id not in task_ids:
                   raise ValueError(f"Задача {task['id']} ссылается на несуществующую зависимость {dep_id}.")
