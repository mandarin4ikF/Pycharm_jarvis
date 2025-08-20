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
       if hasattr(self, '_initialized'): return
       with self._lock:
           if hasattr(self, '_initialized'): return
           self.model_name = config['model_name']
           logger.info(f"Загрузка и кэширование модели для классификатора: {self.model_name}...")
           self.model = SentenceTransformer(self.model_name)
           self.prototypes = config['prototypes']
           self._precompute_prototype_embeddings()
           self._initialized = True
   def _precompute_prototype_embeddings(self):
       self.prototype_embeddings = {}
       for complexity, phrases in self.prototypes.items():
           self.prototype_embeddings[complexity] = self.model.encode(phrases)
   def classify(self, text: str) -> str:
       if not text or not text.strip(): return 'simple'
       text_embedding = self.model.encode([text])
       max_similarity, best_match_complexity = -1, 'simple'
       for complexity, embeddings in self.prototype_embeddings.items():
           similarities = cosine_similarity(text_embedding, embeddings)
           if similarities.max() > max_similarity:
               max_similarity = similarities.max()
               best_match_complexity = complexity
       logger.info(f"Текст классифицирован как '{best_match_complexity}' с макс. сходством {max_similarity:.2f}")
       return best_match_complexity


class RequestRouter:
   def __init__(self, config_path: str = "src/config/routing.yaml"):
       self.config = load_config(config_path)
       self.classifier = ComplexityClassifier(self.config['classifier'])
       self.complexity_map = self.config['complexity_map']
   def route(self, prompt: str) -> Tuple[str, Optional[str]]:
       complexity = self.classifier.classify(prompt)
       model = self.complexity_map.get(complexity)
       return complexity, model
