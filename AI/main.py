import sys
import json
import os
from src.core.router import RequestRouter
from src.core.decomposer import TaskDecomposer

def main():
    """
    Главная функция, демонстрирующая совместную работу маршрутизатора и декомпозитора.
    """
    print("🤖 Система Jarvis: Инициализация...")
    
    try:
        # Получаем абсолютный путь к файлу конфигурации
# Получаем базовую директорию проекта (на уровень выше src)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'AI', 'src', 'config', 'routing.yaml')
        
        router = RequestRouter(config_path=config_path)
    except Exception as e:
        print(f"❌ Критическая ошибка при инициализации: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n--- 1. Тестирование маршрутизации ---")
    
    complex_goal = "Создай сложное приложение которое по фото определяет калории в еде"
    
    result = router.route(complex_goal)
    if not result or not result[1]:
        print("Не удалось определить модель для маршрутизации.")
        sys.exit(1)
        
    complexity, model_name = result
    print(f"Запрос: '{complex_goal}'")
    print(f"-> Сложность: {complexity}, Рекомендуемая модель: {model_name}")

    print("\n--- 2. Тестирование декомпозиции ---")
    
    # Мы используем декомпозитор только для сложных задач
    if complexity == 'complex':
        try:
            # Передаем модель, рекомендованную роутером, в декомпозитор
            decomposer = TaskDecomposer(planning_model_name=model_name)
            plan = decomposer.decompose(complex_goal)
            
            print("\n✅ Успех! Сгенерированный план:")
            # Выводим красивый JSON
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            
        except ValueError as e:
            print(f"\n❌ Ошибка планирования: {e}")
    else:
        print(f"Задача определена как '{complexity}', декомпозиция не требуется.")


if __name__ == '__main__':
    main()