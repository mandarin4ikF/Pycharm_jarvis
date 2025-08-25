import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
from src.core.context import CONTEXT
import sys
logger = logging.getLogger(__name__)


REVIEWER_SYSTEM_PROMPT = """
Ты — 'Jarvis Code Reviewer', элитный AI тимлид. Твоя задача — провести ревью предоставленного Python-кода.
Ты получаешь сам код и отчеты от статических анализаторов 'ruff' (стиль и качество) и 'bandit' (безопасность).


ПРАВИЛА:
1.  **Цель**: Твой отзыв должен быть кратким, по делу и полезным для улучшения кода.
2.  **Формат**: Напиши ревью в формате Markdown.
3.  **Анализ**: Обязательно упомяни ключевые находки из отчетов `ruff` и `bandit`. Если отчеты пустые, похвали код за чистоту и безопасность.
4.  **Итог**: В конце отзыва поставь общую оценку: "Оценка: ОТЛИЧНО", "Оценка: ХОРОШО" или "Оценка: ТРЕБУЕТ ДОРАБОТКИ".
"""


TESTER_SYSTEM_PROMPT = """
Ты — элитный QA-инженер. Твоя задача — писать исчерпывающие unit-тесты для предоставленного Python-кода с использованием фреймворка pytest.


ПРАВИЛА:
1.  **Формат вывода**: Твой ответ должен быть ТОЛЬКО валидным Python-кодом. Никаких лишних слов, объяснений или ```python.
2.  **Покрытие**: Сгенерируй как минимум 1 позитивный и 1 негативный тест (проверка на ошибки или граничные случаи).
3.  **Импорты**: Убедись, что все необходимые импорты, включая тестируемую функцию, присутствуют. Предполагай, что тестируемый код находится в файле `app.py`.
"""


async def code_generator_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   task_id, description = task['id'], task['description']
   logger.info(f"[Agent: CodeGenerator] 🤖 Начал задачу {task_id}: '{description}'")
  
   # Агент может прочитать текущий контекст перед работой
   current_context = state["working_memory"].get_full_context()
   logger.info(f"CodeGenerator видит контекст: {current_context[:200]}...")


   generated_code = "def add(a, b):\n    return a + b\n"
   result = {"message": "Код сгенерирован.", "generated_code": generated_code}
  
   # Агент добавляет свой результат в рабочую память
   state["working_memory"].add_entry(source="CodeGenerator", content=generated_code, data_type="code")
  
   logger.info(f"[Agent: CodeGenerator] ✅ Задача {task_id} выполнена.")
   return {"task_id": task_id, "result": result}



async def code_review_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   """Агент, который проводит ревью кода с помощью ruff, bandit и LLM."""
   task_id = task['id']
   description = task['description']
   logger.info(f"[Agent: CodeReviewer] 🧐 Начал выполнять задачу {task_id}: '{description}'")


   # Получаем код от предыдущего шага
   code_to_review = ""
   dependencies = task.get("dependencies", [])
   if dependencies:
       prev_task_id = dependencies[0]
       prev_result = state.get("results", {}).get(prev_task_id, {})
       if isinstance(prev_result, dict):
           code_to_review = prev_result.get("generated_code", "")


   if not code_to_review:
       raise ValueError("Не найден код для ревью от предыдущего шага.")


   # Запускаем анализаторы во временной директории
   with tempfile.TemporaryDirectory() as temp_dir:
       temp_path = Path(temp_dir)
       code_file = temp_path / "app.py"
       code_file.write_text(code_to_review, encoding='utf-8')


       # Запуск ruff
       ruff_process = await asyncio.create_subprocess_exec(
           sys.executable, "-m", "ruff", "check", ".",
           cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
       )
       ruff_stdout, _ = await ruff_process.communicate()


       # Запуск bandit
       bandit_process = await asyncio.create_subprocess_exec(
           sys.executable, "-m", "bandit", "-r", ".",
           cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
       )
       bandit_stdout, _ = await bandit_process.communicate()


   ruff_report = ruff_stdout.decode('utf-8', errors='ignore').strip()
   bandit_report = bandit_stdout.decode('utf-8', errors='ignore').strip()


   # Формируем промпт для LLM
   user_prompt = (
       "Проведи ревью следующего кода, основываясь на отчетах анализаторов.\n\n"
       f"**Код для ревью:**\n```python\n{code_to_review}\n```\n\n"
       f"**Отчет Ruff (стиль и качество):**\n```\n{ruff_report or 'Замечаний нет.'}\n```\n\n"
       f"**Отчет Bandit (безопасность):**\n```\n{bandit_report or 'Уязвимостей не найдено.'}\n```"
   )


   logger.info("Обращение к LLM для генерации ревью...")
   review_summary = await CONTEXT.ollama_client.invoke(
       model="llama3",
       system_prompt=REVIEWER_SYSTEM_PROMPT,
       user_prompt=user_prompt
   )


   result = {
       "message": "Ревью кода завершено.",
       "review_summary": review_summary,
       "app_code": code_to_review # Передаем код дальше для тестов
   }
   logger.info(f"[Agent: CodeReviewer] ✅ Задача {task_id} выполнена.")
   return {"task_id": task_id, "result": result}




async def test_generator_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   """Агент, который генерирует unit-тесты для кода, прошедшего ревью."""
   task_id = task['id']
   description = task['description']
   logger.info(f"[Agent: TestGenerator] 🧪 Начал выполнять задачу {task_id}: '{description}'")


   # Находим код, который прошел ревью
   code_to_test = ""
   dependencies = task.get("dependencies", [])
   if dependencies:
       prev_task_id = dependencies[0]
       prev_result = state.get("results", {}).get(prev_task_id, {})
       if isinstance(prev_result, dict):
           code_to_test = prev_result.get("app_code", "")


   if not code_to_test:
       raise ValueError("Не найден код для тестирования от шага ревью.")


   user_prompt = f"Вот код, для которого нужно написать тесты:\n\n```python\n{code_to_test}\n```"
  
   logger.info("Обращение к LLM для генерации тестов...")
   test_code = await CONTEXT.ollama_client.invoke(
       model="llama3",
       system_prompt=TESTER_SYSTEM_PROMPT,
       user_prompt=user_prompt
   )
  
   result = {
       "message": "Unit-тесты были успешно сгенерированы.",
       "app_code": code_to_test,
       "test_code": test_code
   }
   logger.info(f"[Agent: TestGenerator] ✅ Задача {task_id} выполнена.")
   return {"task_id": task_id, "result": result}



async def code_executor_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
   task_id, description = task['id'], task['description']
   logger.info(f"[Agent: CodeExecutor] ⚡️ Начал задачу {task_id}: '{description}'")
   prev_result = state["results"][task["dependencies"][0]]
   app_code, test_code = prev_result.get("app_code", ""), prev_result.get("test_code", "")
   if not app_code or not test_code: raise ValueError("Не найден код приложения или тестов.")


   with tempfile.TemporaryDirectory() as temp_dir:
       (Path(temp_dir) / "app.py").write_text(app_code, encoding='utf-8')
       (Path(temp_dir) / "test_app.py").write_text(test_code, encoding='utf-8')
       process = await asyncio.create_subprocess_exec(sys.executable, "-m", "pytest", cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
       stdout, stderr = await process.communicate()


   stdout_str, stderr_str = stdout.decode('utf-8'), stderr.decode('utf-8')
   success = process.returncode == 0
   result = {"message": "Тесты выполнены.", "stdout": stdout_str, "stderr": stderr_str, "success": success}
   logger.info(f"[Agent: CodeExecutor] ✅ Тесты {'пройдены' if success else 'провалены'}.")
   return {"task_id": task_id, "result": result}


AGENT_MAPPING = {
   "CodeGenerator": code_generator_agent,
   "CodeReviewer": code_review_agent, # <-- Новый агент
   "TestGenerator": test_generator_agent,
   "CodeExecutor": code_executor_agent,
   "ReportGenerator": code_generator_agent,
}
