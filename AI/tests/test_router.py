# tests/test_router.py
import pytest
import os
import sys
from unittest.mock import MagicMock

# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.router import RequestRouter, ComplexityClassifier

CONFIG_PATH = "src/config/routing.yaml"

@pytest.fixture(scope="module")
def router():
    if not os.path.exists(CONFIG_PATH):
        pytest.fail(f"Файл конфигурации {CONFIG_PATH} не найден.")
    return RequestRouter(config_path=CONFIG_PATH)

@pytest.mark.parametrize("prompt, expected_complexity", [
    ("привет", "simple"),
    ("какая столица франции?", "simple"),
    ("напиши мне email", "medium"),
    ("создай docker-compose файл", "medium"),
    ("разработай комплексную стратегию цифровой трансформации", "complex"),
])
def test_classification_logic(router, prompt, expected_complexity):
    complexity = router.classifier.classify(prompt)
    assert complexity == expected_complexity

def test_routing_logic_returns_tuple(router):
    router.classifier.classify = MagicMock(return_value="medium")
    result = router.route("любой текст")
    assert isinstance(result, tuple)
    complexity, model_name = result
    assert complexity == "medium"
    assert model_name == "qwen2:7b"

def test_fallback_mechanism(router):
    result = router.get_fallback_model('simple')
    assert isinstance(result, tuple)
    complexity, model_name = result
    assert complexity == 'medium'
    assert model_name == router.complexity_map['medium']
    
    result_last = router.get_fallback_model('complex')
    assert result_last is None
