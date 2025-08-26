import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
from src.core.context import CONTEXT  # твой JarvisContext
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- PROMPTS ---
REVIEWER_SYSTEM_PROMPT = """
Ты — 'Jarvis Code Reviewer', элитный AI тимлид. Твоя задача — провести ревью предоставленного Python-кода.
Ты получаешь сам код и отчеты от статических анализаторов 'ruff' (стиль и качество) и 'bandit' (безопасность).

ПРАВИЛА:
1. Цель: Твой отзыв должен быть кратким, по делу и полезным для улучшения кода.
2. Формат: Markdown.
3. Анализ: Обязательно упомяни ключевые находки из отчетов ruff и bandit. Если отчеты пустые, похвали код за чистоту и безопасность.
4. Итог: В конце — общая оценка: "Оценка: ОТЛИЧНО", "Оценка: ХОРОШО" или "Оценка: ТРЕБУЕТ ДОРАБОТКИ".
"""

TESTER_SYSTEM_PROMPT = """
Ты — элитный QA-инженер. Твоя задача — писать unit-тесты для предоставленного Python-кода с использованием pytest.

ПРАВИЛА:
1. Формат вывода: ТОЛЬКО валидный Python-код.
2. Покрытие: Минимум 1 позитивный и 1 негативный тест.
3. Импорты: Все необходимые импорты должны быть включены. Код находится в файле app.py.
"""

# --- AGENTS ---
async def code_generator_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task["id"]
    description = task["description"]
    logger.info(f"[Agent: CodeGenerator] 🤖 Начал задачу {task_id}: '{description}'")

    # Берём контекст
    current_context = state.get("working_memory", {}).get_full_context() if "working_memory" in state else ""
    logger.info(f"CodeGenerator видит контекст: {current_context[:200]}...")

    # Пример кода, можно заменить на LLM
    generated_code = "def add(a, b):\n    return a + b\n"

    # Добавляем в рабочую память
    if "working_memory" in state:
        state["working_memory"].add_entry(source="CodeGenerator", content=generated_code, data_type="code")

    return {"task_id": task_id, "result": {"message": "Код сгенерирован.", "generated_code": generated_code}}

async def code_review_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task["id"]
    description = task["description"]
    logger.info(f"[Agent: CodeReviewer] 🧐 Начал задачу {task_id}: '{description}'")

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

    # Статический анализ через ruff и bandit
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        code_file = temp_path / "app.py"
        code_file.write_text(code_to_review, encoding='utf-8')

        ruff_proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "ruff", "check", ".", cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        ruff_stdout, _ = await ruff_proc.communicate()

        bandit_proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "bandit", "-r", ".", cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        bandit_stdout, _ = await bandit_proc.communicate()

    ruff_report = ruff_stdout.decode("utf-8", errors="ignore").strip()
    bandit_report = bandit_stdout.decode("utf-8", errors="ignore").strip()

    # LLM ревью
    user_prompt = (
        f"Проведи ревью кода:\n\n**Код:**\n```python\n{code_to_review}\n```\n\n"
        f"**Ruff:**\n```\n{ruff_report or 'Замечаний нет.'}\n```\n\n"
        f"**Bandit:**\n```\n{bandit_report or 'Уязвимостей не найдено.'}\n```"
    )
    review_summary = await CONTEXT.ollama_client.invoke(
        model="llama3",
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        user_prompt=user_prompt
    )

    return {"task_id": task_id, "result": {"message": "Ревью завершено.", "review_summary": review_summary, "app_code": code_to_review}}

async def test_generator_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task["id"]
    description = task["description"]
    logger.info(f"[Agent: TestGenerator] 🧪 Начал задачу {task_id}: '{description}'")

    # Код для тестов
    code_to_test = ""
    dependencies = task.get("dependencies", [])
    if dependencies:
        prev_task_id = dependencies[0]
        prev_result = state.get("results", {}).get(prev_task_id, {})
        if isinstance(prev_result, dict):
            code_to_test = prev_result.get("app_code", "")

    if not code_to_test:
        raise ValueError("Не найден код для тестирования от шага ревью.")

    user_prompt = f"Напиши тесты для следующего кода:\n```python\n{code_to_test}\n```"
    test_code = await CONTEXT.ollama_client.invoke(
        model="llama3",
        system_prompt=TESTER_SYSTEM_PROMPT,
        user_prompt=user_prompt
    )

    return {"task_id": task_id, "result": {"message": "Unit-тесты сгенерированы.", "app_code": code_to_test, "test_code": test_code}}

async def code_executor_agent(state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task["id"]
    description = task["description"]
    logger.info(f"[Agent: CodeExecutor] ⚡️ Выполнение кода для {task_id}: '{description}'")

    prev_result = state["results"][task["dependencies"][0]]
    app_code, test_code = prev_result.get("app_code", ""), prev_result.get("test_code", "")
    if not app_code or not test_code:
        raise ValueError("Не найден код приложения или тестов.")

    with tempfile.TemporaryDirectory() as temp_dir:
        (Path(temp_dir) / "app.py").write_text(app_code, encoding="utf-8")
        (Path(temp_dir) / "test_app.py").write_text(test_code, encoding="utf-8")
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pytest", cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

    success = process.returncode == 0
    return {
        "task_id": task_id,
        "result": {"message": "Тесты выполнены.", "stdout": stdout.decode(), "stderr": stderr.decode(), "success": success}
    }

# --- Mapping ---
AGENT_MAPPING = {
    "CodeGenerator": code_generator_agent,
    "CodeReviewer": code_review_agent,
    "TestGenerator": test_generator_agent,
    "CodeExecutor": code_executor_agent,
}
