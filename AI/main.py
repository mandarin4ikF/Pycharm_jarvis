import sys
import json
import asyncio
import logging
from src.core.router import RequestRouter
from src.core.decomposer import TaskDecomposer
from src.core.llm_client import OllamaClient
from src.core.graph import GraphExecutor
from src.utils.config_loader import load_config


# Настройка логирования для вывода информации от всех модулей
logging.basicConfig(
   level=logging.INFO,
   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
   stream=sys.stdout
)

# Создаем глобальный логгер
logger = logging.getLogger(__name__)

async def main():
   """Главная асинхронная функция, запускающая всю систему."""
   logger.info("🤖 Система Jarvis: Инициализация...")
  
   try:
       app_config = load_config('AI/src/config/app_config.yaml')
       router = RequestRouter(config_path='AI/src/config/routing.yaml')
       ollama_client = OllamaClient(config=app_config['ollama_client'])
   except Exception as e:
       logger.critical(f"❌ Критическая ошибка при инициализации: {e}")
       sys.exit(1)


   complex_goal = "Создай Робо-руку как у железного человека"
  
   # 1. Маршрутизация
   result = router.route(complex_goal)
   if not result or not result[1]:
       logger.error("Не удалось определить модель для маршрутизации.")
       await ollama_client.close()
       sys.exit(1)
       
   complexity, model_name = result
   logger.info(f"Запрос классифицирован как '{complexity}', выбрана модель '{model_name}'.")


   # 2. Декомпозиция
   plan = None
   if complexity == 'complex':
       try:
           decomposer = TaskDecomposer(model_name, ollama_client)
           plan = await decomposer.decompose(complex_goal)
           logger.info("✅ План успешно сгенерирован.")
           print(json.dumps(plan, indent=2, ensure_ascii=False))
       except Exception as e:
           logger.error(f"❌ Ошибка во время декомпозиции: {e}")
  
   await ollama_client.close()


   # 3. Выполнение
   if plan:
       logger.info("🚀 Запуск выполнения плана через LangGraph...")
       try:
           graph_executor = GraphExecutor()
           await graph_executor.run(plan)
       except Exception as e:
           logger.error(f"❌ Ошибка при выполнении графа: {e}")
   else:
       logger.warning("План не был сгенерирован, выполнение пропускается.")


if __name__ == '__main__':
   # Этот скрипт ожидает, что у вас есть папка src/config/
   # с файлами app_config.yaml и routing.yaml.
   # Убедитесь, что Ollama запущена и модель llama3:8b загружена.
   try:
       asyncio.run(main())
   except KeyboardInterrupt:
       print("\nЗавершение работы по команде пользователя.")
   except Exception as e:
       print(f"Произошла непредвиденная ошибка: {e}")