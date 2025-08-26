# ==============================================================================
# Файл: main.py
# Назначение: Главная точка входа в систему Jarvis
# Описание: Инициализирует систему через глобальный контекст, обрабатывает задачу,
#           использует маршрутизацию, декомпозицию, улучшение плана и выполнение.
# ==============================================================================

import sys
import json
import asyncio
import logging

# === Ядро системы ===
from src.core.router import RequestRouter
from src.core.decomposer import TaskDecomposer
from src.core.graph import GraphExecutor
from src.core.crew import PlanRefinementCrew
from src.core.context import CONTEXT
from src.core.memory import WorkingMemory
# === Настройка логирования ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    """Главная асинхронная функция, запускающая всю систему Jarvis."""
    logger.info("🤖 Система Jarvis: Инициализация через глобальный контекст...")

    try:
        # --- Инициализация всей системы через контекст ---
        CONTEXT.initialize()
        logger.info("✅ Контекст инициализирован: LLM-клиент, память, инструменты и т.д.")
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при инициализации контекста: {e}")
        sys.exit(1)

    # --- Инициализация маршрутизатора (использует клиент из контекста) ---
    router = RequestRouter(config_path='AI/src/config/routing.yaml')
    logger.info("🔧 Маршрутизатор запросов загружен.")

    # --- Получение задачи ---
    complex_goal = "Напиши сложное приложение для определения цены монеты, проведи ее ревью и протестируй."
    logger.info(f"🎯 Получена задача: '{complex_goal}'")

    # --- Маршрутизация (теперь асинхронная) ---
    try:
        complexity, model_name = await router.route(complex_goal)
        logger.info(f"🧠 Запрос классифицирован как '{complexity}', выбрана модель '{model_name}'.")
    except Exception as e:
        logger.error(f"❌ Ошибка при маршрутизации запроса: {e}")
        await CONTEXT.close()
        sys.exit(1)

    # --- Декомпозиция задачи (если сложная) ---
    initial_plan = None
    if complexity == 'complex':
        try:
            decomposer = TaskDecomposer(planning_model_name=model_name)
            initial_plan = await decomposer.decompose(complex_goal)
            logger.info("✅ Первоначальный план успешно сгенерирован.")
        except Exception as e:
            logger.error(f"❌ Ошибка во время декомпозиции: {e}")

    # --- Улучшение плана с помощью CrewAI (Совет Мыслителей) ---
    final_plan = initial_plan
    if initial_plan:
        try:
            refinement_crew = PlanRefinementCrew()
            refined_plan_str = await asyncio.to_thread(
                refinement_crew.run,
                json.dumps(initial_plan, indent=2, ensure_ascii=False),
                complex_goal
            )
            final_plan = json.loads(refined_plan_str)
            logger.info("✅ План успешно улучшен 'Советом Мыслителей'.")
            print("\n--- 📋 ФИНАЛЬНЫЙ ПЛАН ---")
            print(json.dumps(final_plan, indent=2, ensure_ascii=False))
            print("----------------------")
        except Exception as e:
            logger.error(f"❌ Ошибка во время улучшения плана: {e}. Используется первоначальный план.")
            final_plan = initial_plan

    # --- Выполнение плана через GraphExecutor ---
    if final_plan:
        logger.info("🚀 Запуск выполнения финального плана через GraphExecutor...")
        try:
            graph_executor = GraphExecutor()
            working_memory = WorkingMemory()  # если у тебя есть класс WorkingMemory
            await graph_executor.run(plan=final_plan, working_memory=working_memory)
            logger.info("✅ Выполнение плана завершено.")
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении плана: {e}")



    # Затем в блоке выполнения:
    if final_plan:
        logger.info("🚀 Запуск выполнения финального плана через GraphExecutor...")
        try:
            graph_executor = GraphExecutor()
            working_memory = WorkingMemory()  # Создаем объект памяти
            await graph_executor.run(plan=final_plan, working_memory=working_memory)
            logger.info("✅ Выполнение плана завершено.")
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении плана: {e}")


# --- Точка входа ---
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Завершение работы по команде пользователя (Ctrl+C).")
    except Exception as e:
        logger.critical(f"💥 Произошла непредвиденная ошибка: {e}")
        sys.exit(1)