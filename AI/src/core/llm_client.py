import logging
import asyncio
import httpx
from typing import Dict, Any


logger = logging.getLogger(__name__)


class OllamaClient:
   """Асинхронный клиент для взаимодействия с API Ollama."""
   def __init__(self, config: Dict[str, Any]):
       self.base_url = config.get("base_url", "http://localhost:11434")
       self.timeout = config.get("request_timeout", 180.0)
       self.max_retries = config.get("max_retries", 3)
       self.retry_delay = config.get("retry_delay", 1.0)
       self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)


   async def invoke(self, model: str, system_prompt: str, user_prompt: str) -> str:
       payload = {
           "model": model,
           "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
           "stream": False
       }
       # Для запросов на ревью и тесты лучше не использовать format="json", чтобы получить чистый текст/код
       if "JSON" not in system_prompt:
            payload["format"] = "json"


       last_exception = None
       for attempt in range(self.max_retries):
           try:
               response = await self.client.post("/api/chat", json=payload)
               response.raise_for_status()
               content = response.json().get("message", {}).get("content", "")
               if not content: raise ValueError("Ответ LLM не содержит 'content'.")
               return content.strip()
           except (httpx.RequestError, httpx.HTTPStatusError) as e:
               last_exception = e
               delay = self.retry_delay * (2 ** attempt)
               await asyncio.sleep(delay)
       raise ConnectionError("Не удалось подключиться к Ollama.") from last_exception


   async def close(self):
       await self.client.aclose()