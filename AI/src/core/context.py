import logging
from src.core.llm_client import OllamaClient
from src.core.sandbox import CodeSandbox
from src.utils.config_loader import load_config


logger = logging.getLogger(__name__)


class JarvisContext:
   """Синглтон для хранения глобальных, разделяемых ресурсов."""
   _instance = None
   def __new__(cls):
       if cls._instance is None:
           cls._instance = super(JarvisContext, cls).__new__(cls)
           cls._instance._initialized = False
       return cls._instance


   def initialize(self):
       if self._initialized: return
       app_config = load_config('AI/src/config/app_config.yaml')
       self.ollama_client = OllamaClient(config=app_config['ollama_client'])
       self.sandbox = CodeSandbox()
       self._initialized = True
       logger.info("Глобальный контекст успешно инициализирован.")


   async def close(self):
       if hasattr(self, 'ollama_client') and self.ollama_client:
           await self.ollama_client.close()
       logger.info("Ресурсы контекста успешно освобождены.")


CONTEXT = JarvisContext()
