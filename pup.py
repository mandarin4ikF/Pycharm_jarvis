import sys
import os

print("--- Запуск диагностики окружения ---")

try:
    print("\n[1] Информация о текущем интерпретаторе Python:")
    # Печатаем путь к исполняемому файлу python, который запускает этот скрипт
    print(f"    - Путь к Python.exe: {sys.executable}")

    print("\n[2] Попытка импортировать 'pvporcupine'...")
    import pvporcupine
    print("    - [✅] Пакет 'pvporcupine' успешно импортирован.")

    print("\n[3] Анализ импортированного пакета:")
    
    # Пытаемся узнать версию пакета
    try:
        version = pvporcupine.__version__
        print(f"    - Обнаруженная версия: {version}")
    except AttributeError:
        print("    - [⚠️] Версия не найдена (атрибут version отсутствует). Это признак очень старой версии пакета (v1.x).")

    # Узнаем, из какого файла он был загружен
    try:
        file_location = pvporcupine.__file__
        print(f"    - Расположение файла: {file_location}")
    except AttributeError:
         print("    - [⚠️] Расположение файла не найдено.")


    print("\n--- Диагностика завершена ---")
    print("Если версия старая (v1.x) или расположение файла НЕ находится в папке вашего проекта .venv, то мы нашли проблему.")


except ImportError:
    print("\n[❌] ОШИБКА: Не удалось импортировать 'pvporcupine'.")
    print("    - Это значит, что пакет не установлен в окружении, которое использует этот интерпретатор:")
    print(f"    - {sys.executable}")
except Exception as e:
    print(f"\n[❌] Произошла непредвиденная ошибка: {e}")