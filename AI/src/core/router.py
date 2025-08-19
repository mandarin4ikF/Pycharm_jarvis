# src/core/router.py
import logging
from typing import Dict, Optional, Tuple, Any
from threading import Lock

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils.config_loader import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComplexityClassifier:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Dict[str, Any]):
        if hasattr(self, '_initialized'):
            return
        with self._lock:
            if hasattr(self, '_initialized'):
                return
            self.model_name = config['model_name']
            logger.info(f"Загрузка и кэширование модели для классификатора: {self.model_name}...")
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info("Модель успешно загружена в кэш.")
            except Exception as e:
                logger.error(f"Критическая ошибка: не удалось загрузить модель SentenceTransformer: {e}")
                raise
            self.prototypes = config['prototypes']
            self._precompute_prototype_embeddings()
            self._initialized = True

    def _precompute_prototype_embeddings(self):
        logger.info("Вычисление эмбеддингов для эталонных фраз...")
        self.prototype_embeddings = {}
        for complexity, phrases in self.prototypes.items():
            self.prototype_embeddings[complexity] = self.model.encode(phrases)
        logger.info("Эмбеддинги эталонов успешно вычислены.")

    def classify(self, text: str) -> str:
        if not text or not text.strip():
            logger.warning("Получен пустой текст для классификации, возвращаем 'simple'.")
            return 'simple'
        text_embedding = self.model.encode([text])
        max_similarity = -1
        best_match_complexity = 'simple'
        for complexity, embeddings in self.prototype_embeddings.items():
            similarities = cosine_similarity(text_embedding, embeddings)
            current_max_similarity = similarities.max()
            if current_max_similarity > max_similarity:
                max_similarity = current_max_similarity
                best_match_complexity = complexity
        logger.info(f"Текст классифицирован как '{best_match_complexity}' с макс. сходством {max_similarity:.2f}")
        return best_match_complexity

class RequestRouter:
    def __init__(self, config_path: str = "src/config/routing.yaml"):
        logger.info(f"Инициализация маршрутизатора с конфигурацией: {config_path}")
        try:
            self.config = load_config(config_path)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Не удалось загрузить или распарсить конфигурацию: {e}")
            raise
        self.classifier = ComplexityClassifier(self.config['classifier'])
        self.complexity_map = self.config['complexity_map']
        self.fallback_order = self.config['fallback_order']

    def route(self, prompt: str) -> Tuple[str, Optional[str]]:
        complexity = self.classifier.classify(prompt)
        model = self.complexity_map.get(complexity)
        if model:
            logger.info(f"Запрос '{prompt[:50]}...' направлен на модель: {model} (сложность: {complexity})")
            return complexity, model
        else:
            logger.warning(f"Для сложности '{complexity}' модель не найдена в config/routing.yaml.")
            return complexity, None

    def get_fallback_model(self, failed_model_complexity: str) -> Optional[Tuple[str, str]]:
        try:
            current_index = self.fallback_order.index(failed_model_complexity)
            if current_index + 1 < len(self.fallback_order):
                next_complexity = self.fallback_order[current_index + 1]
                fallback_model = self.complexity_map.get(next_complexity)
                logger.warning(f"Перенаправление на следующий уровень: '{next_complexity}' (модель: {fallback_model})")
                return next_complexity, fallback_model
        except ValueError:
            logger.error(f"Тег сложности '{failed_model_complexity}' не найден в fallback_order.")
            return None
        logger.error(f"Достигнут максимальный уровень отката ({failed_model_complexity}).")
        return None
