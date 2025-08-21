import asyncio
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__)


async def code_generator_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   """Симуляция агента, который пишет код."""
   task_id = task['id']
   description = task['description']
   logger.info(f"[Agent: CodeGenerator] 🤖 Начал выполнять задачу {task_id}: '{description}'")
   await asyncio.sleep(2)
   result = f"Код для задачи '{description}' был успешно сгенерирован."
   logger.info(f"[Agent: CodeGenerator] ✅ Задача {task_id} выполнена.")
   return {"task_id": task_id, "result": result}


async def test_generator_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   """Симуляция агента, который пишет тесты."""
   task_id = task['id']
   description = task['description']
   logger.info(f"[Agent: TestGenerator] 🧪 Начал выполнять задачу {task_id}: '{description}'")
   await asyncio.sleep(1.5)
   result = f"Тесты для задачи '{description}' были успешно сгенерированы."
   logger.info(f"[Agent: TestGenerator] ✅ Задача {task_id} выполнена.")
   return {"task_id": task_id, "result": result}


async def code_executor_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   """Симуляция агента, который выполняет код или команды."""
   task_id = task['id']
   description = task['description']
   logger.info(f"[Agent: CodeExecutor] ⚡️ Начал выполнять задачу {task_id}: '{description}'")
   await asyncio.sleep(1)
   result = f"Код/команда для задачи '{description}' была успешно выполнена."
   logger.info(f"[Agent: CodeExecutor] ✅ Задача {task_id} выполнена.")
   return {"task_id": task_id, "result": result}


AGENT_MAPPING = {
   "CodeGenerator": code_generator_agent,
   "TestGenerator": test_generator_agent,
   "CodeExecutor": code_executor_agent,
   "ReportGenerator": code_generator_agent,
}
