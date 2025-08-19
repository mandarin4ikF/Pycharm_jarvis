import sys
import os
from src.core.router import RequestRouter

def main():
    """
    Главная функция, демонстрирующая работу маршрутизатора.
    """
    print("🤖 Система Jarvis: Инициализация маршрутизатора...")
    
    try:
        # Определяем абсолютный путь к конфигурационному файлу
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, 'src', 'config', 'routing.yaml')
        
        # Создаем экземпляр роутера
        router = RequestRouter(config_path=config_path)
        
    except Exception as e:
        print(f"❌ Критическая ошибка при инициализации: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n--- Тестирование маршрутизации ---")
    
    prompts = [
        "Сколько будет 5+5?",
        "Напиши функцию на Python, которая сортирует список чисел.",
        "Предложи архитектуру для системы обработки больших данных в реальном времени."
    ]
    
    for prompt in prompts:
        result = router.route(prompt)
        if result and result[1]:
            complexity, model_name = result
            print(f"Запрос: '{prompt}' -> Сложность: {complexity}, Модель: {model_name}")
        else:
            complexity, _ = result
            print(f"Запрос: '{prompt}' -> Сложность: {complexity}, Модель не найдена в конфигурации.")

    print("\n--- Тестирование механизма отката (fallback) ---")
    
    # Симулируем, что модель для 'simple' не справилась
    failed_complexity = 'simple'
    fallback_result = router.get_fallback_model(failed_complexity)
    if fallback_result:
        new_complexity, fallback_model = fallback_result
        print(f"Откат с '{failed_complexity}': используем '{new_complexity}' -> {fallback_model}")

    # Симулируем отказ на последнем уровне
    failed_complexity_3 = 'complex'
    fallback_result_3 = router.get_fallback_model(failed_complexity_3)
    if not fallback_result_3:
        print(f"Откат с '{failed_complexity_3}': больше моделей нет, как и ожидалось.")


if __name__ == '__main__':
    main()