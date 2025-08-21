import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str) -> Dict[str, Any]:
   """
   Загружает конфигурационный YAML-файл.
   ИСПРАВЛЕНО: Добавлена обработка разных кодировок.
   """
   path = Path(config_path)
   if not path.is_file():
       raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")
  
   # Пытаемся прочитать в стандартной кодировке UTF-8
   try:
       with open(path, 'r', encoding='utf-8') as f:
           return yaml.safe_load(f)
   except UnicodeDecodeError:
       # Если не получилось, пробуем стандартную кодировку Windows для кириллицы
       try:
           with open(path, 'r', encoding='cp1251') as f:
               return yaml.safe_load(f)
       except Exception as e:
           raise ValueError(f"Не удалось прочитать файл {config_path} ни в одной из кодировок.") from e
   except yaml.YAMLError as e:
       raise ValueError(f"Ошибка парсинга YAML файла {config_path}: {e}")