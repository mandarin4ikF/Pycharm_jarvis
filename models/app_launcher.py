import json
import os
import subprocess
import re
from pathlib import Path

# Изменяем импорт на абсолютный
try:
    from indexer import aliases
except ImportError:
    # Альтернативный вариант для случаев, когда модуль запускается напрямую
    import sys
    from os.path import dirname, abspath
    sys.path.append(dirname(dirname(abspath(__file__))))
    from indexer import aliases

class AppLauncher:
    def __init__(self):
        self.app_paths = self.load_app_index()
        self.app_mapping = self.build_app_mapping()
    
    def load_app_index(self):
        """Загрузка путей из JSON-файла"""
        base_dir = Path(__file__).resolve().parent.parent
        index_path = base_dir / "indexer" / "app_index.json"
        
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Файл конфигурации не найден: {index_path}")
            return {}
        except json.JSONDecodeError:
            print(f"Ошибка чтения JSON: {index_path}")
            return {}
    
    def build_app_mapping(self):
        """Создание словаря для поиска приложений"""
        mapping = {}
        
        # Добавляем основные названия
        for app_name, path in self.app_paths.items():
            mapping[app_name] = path
        
        # Добавляем синонимы
        for app_name, synonyms in aliases.ALIASES.items():
            if app_name in self.app_paths:
                for synonym in synonyms:
                    mapping[synonym] = self.app_paths[app_name]
        
        return mapping
    
    def execute_command(self, text: str) -> str:
        """Обработка команд запуска приложений"""
        text = text.lower()
        
        # Проверка триггерных слов
        triggers = r'открыть|включить|переключить|запусти|запустить|включи|открой'
        if not re.search(triggers, text):
            return ""
        
        # Поиск приложения в команде
        for app_name, app_path in self.app_mapping.items():
            if app_name in text:
                try:
                    subprocess.Popen(app_path)
                    return f"Открываю {app_name}"
                except Exception as e:
                    return f"Ошибка при открытии {app_name}: {str(e)}"
        
        return "Не удалось распознать название программы"

# Для тестирования модуля отдельно
if __name__ == "__main__":
    launcher = AppLauncher()
    print("Тест запуска приложений:")
    print(launcher.execute_command("запусти вартандер"))