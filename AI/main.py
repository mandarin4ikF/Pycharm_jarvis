import sys
import json
import asyncio
import os
from pathlib import Path
from src.core.router import RequestRouter
from src.core.decomposer import TaskDecomposer
from src.core.llm_client import OllamaClient
from src.utils.config_loader import load_config

async def main():
    print("🤖 Система Jarvis: Инициализация...")
    try:
        # Получаем абсолютный путь к директории проекта
        base_dir = Path(__file__).parent
        config_path = base_dir / 'src/config/app_config.yaml'
        routing_path = base_dir / 'src/config/routing.yaml'
        
        # Проверяем существование файлов
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        if not routing_path.exists():
            raise FileNotFoundError(f"Routing file not found: {routing_path}")
        
        app_config = load_config(str(config_path))
        router = RequestRouter(config_path=str(routing_path))
        ollama_client = OllamaClient(config=app_config['ollama_client'])
    except Exception as e:
        print(f"❌ Критическая ошибка при инициализации: {e}", file=sys.stderr)
        sys.exit(1)

    complex_goal = "Создай реферат по созданию робо-руки."
  
    print("\n--- 1. Маршрутизация ---")
    complexity, model_name = router.route(complex_goal)
    print(f"Запрос: '{complex_goal}'")
    print(f"-> Сложность: {complexity}, Рекомендуемая модель: {model_name}")

    if complexity == 'complex':
        print("\n--- 2. Декомпозиция (реальный вызов LLM) ---")
        try:
            decomposer = TaskDecomposer(model_name, ollama_client)
            plan = await decomposer.decompose(complex_goal)
            print("\n✅ Успех! Сгенерированный план:")
            print(json.dumps(plan, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"\n❌ Ошибка во время декомпозиции: {e}")
  
    await ollama_client.close()
    print("\nКлиент Ollama успешно завершил работу.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nЗавершение работы...")