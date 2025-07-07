# assistant.py
import json  # работа с JSON
import os  # взаимодействие с ОС
from aliases import ALIASES  # импорт синонимов команд

# Загрузка JSON-индекса программ
def load_app_index(filename="app_index.json"):
    if not os.path.exists(filename):  # если файла нет → ошибка
        print("❌ Файл app_index.json не найден. Сначала запусти indexer.py")
        exit(1)
    with open(filename, "r", encoding="utf-8") as f:  # читаем UTF-8
        return json.load(f)  # возвращаем словарь {программа: путь}

# Поиск соответствия команды алиасу
def match_alias(command):
    for key, synonyms in ALIASES.items():  # перебираем синонимы
        for word in synonyms:
            if word in command:  # если команда содержит синоним
                return key  # возвращаем ключ (например, "chrome")
    return None  # не нашли → None

# Поиск и запуск программы
def find_and_run(command, app_index):
    app_key = match_alias(command)  # получаем ключ (например, "chrome")
    if app_key and app_key in app_index:  # если ключ и путь существуют
        print(f"🚀 Открываю {app_key}...")
        os.startfile(app_index[app_key])  # запускаем программу
    else:
        print("❓ Не смог найти программу по команде.")

# Главный цикл
if __name__ == "__main__":
    app_index = load_app_index()  # загружаем индекс программ
    while True:  # бесконечный цикл
        cmd = input("🗣 Введи команду (или 'выход'): ").lower().strip()
        if cmd in ("выход", "exit", "стоп"):  # команда выхода
            break
        find_and_run(cmd, app_index)  # обработка команды