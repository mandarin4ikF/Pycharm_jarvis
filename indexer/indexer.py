import os
import json

# Настройка путей сканирования:
# Укажите корневые папки, где лежат ваши приложения/скрипты.
START_PATHS = [
    r"C:\Users\Огузок\PycharmProjects\pup",   # необходима

]

# Список директорий для исключения из сканирования
SKIP_DIR_NAMES = [
    '.venv', '.git', '__pycache__', 'node_modules', '.cache',
    'dist', 'build', 'env', 'venv'
]

# Расширения файлов, которые ищем: .exe и .py (скрипты)
TARGET_EXTENSIONS = ('.exe', '.py')

# Имя выходного JSON-файла
OUTPUT_FILE = 'app_index.json'


def scan_system(start_paths):
    """
    Сканирует указанные директории в поисках файлов с нужными расширениями.
    Пропускает папки из списка SKIP_DIR_NAMES.

    :param start_paths: список корневых директорий для сканирования
    :return: словарь {имя_файла: полный_путь}
    """
    app_paths = {}

    for base in start_paths:
        if not os.path.exists(base):
            print(f"⚠️ Путь не найден, пропускаем: {base}")
            continue
        print(f"🔍 Сканирование: {base}")
        for root, dirs, files in os.walk(base):
            # Исключаем ненужные поддиректории
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_NAMES]
            # Если в пути есть любая папка из SKIP_DIR_NAMES, пропускаем
            if any(part.lower() in SKIP_DIR_NAMES for part in root.split(os.sep)):
                continue
            for file in files:
                if file.lower().endswith(TARGET_EXTENSIONS):
                    name = os.path.splitext(file)[0].lower()
                    full_path = os.path.join(root, file)
                    # сохраняем только первое найденное вхождение по имени
                    if name not in app_paths:
                        app_paths[name] = full_path
    return app_paths


def save_app_index(apps, filename):
    """
    Сохраняет словарь путей в JSON-файл.

    :param apps: словарь {имя_файла: путь}
    :param filename: имя выходного файла
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(apps, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    index = scan_system(START_PATHS)
    save_app_index(index, OUTPUT_FILE)
    print(f"✅ Найдено объектов: {len(index)}")
    print(f"💾 Список сохранён в '{OUTPUT_FILE}'")
