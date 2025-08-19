# src/utils/config_loader.py
import yaml
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Загружает конфигурационный YAML-файл.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Ошибка парсинга YAML файла {config_path}: {e}")
