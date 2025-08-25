import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from collections import deque


logger = logging.getLogger(__name__)


class WorkingMemory:
   """
   Управляет контекстом (рабочей памятью) для ОДНОЙ конкретной задачи.
   Работает по принципу FIFO (первый вошел, первый вышел) при переполнении.
   """
   def __init__(self, max_entries: int = 10):
       self.max_entries = max_entries
       # Используем deque для эффективного добавления и удаления элементов с обоих концов
       self.entries = deque(maxlen=self.max_entries)
       logger.info(f"Рабочая память инициализирована с лимитом в {max_entries} записей.")


   def add_entry(self, source: str, content: str, data_type: str = "text"):
       """Добавляет новую запись в рабочую память."""
       entry = {
           "source": source, # Например, 'CodeGenerator' или 'User'
           "type": data_type, # Например, 'code', 'text', 'review'
           "content": content
       }
       self.entries.append(entry)
       logger.info(f"В рабочую память добавлена запись от '{source}'.")


   def get_full_context(self) -> str:
       """Возвращает весь текущий контекст в виде одной строки."""
       if not self.entries:
           return "Рабочая память пуста."
      
       context_str = "--- НАЧАЛО КОНТЕКСТА РАБОЧЕЙ ПАМЯТИ ---\n\n"
       for entry in self.entries:
           context_str += f"Источник: {entry['source']} (Тип: {entry['type']})\n"
           context_str += f"Содержимое:\n{entry['content']}\n\n"
       context_str += "--- КОНЕЦ КОНТЕКСТА РАБОЧЕЙ ПАМЯТИ ---"
       return context_str


class MemoryManager:
   """
   Управляет долговременной векторной памятью Jarvis с помощью ChromaDB.
   """
   def __init__(self, db_path: str = "jarvis_memory", collection_name: str = "main_collection"):
       try:
           self.client = chromadb.PersistentClient(path=db_path)
           self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
               model_name="paraphrase-multilingual-MiniLM-L12-v2"
           )
           self.collection = self.client.get_or_create_collection(
               name=collection_name,
               embedding_function=self.embedding_function
           )
       except Exception as e:
           logger.critical(f"Не удалось инициализировать ChromaDB: {e}")
           raise


   def add_memory(self, text: str, metadata: Dict[str, Any], doc_id: str):
       """Добавляет фрагмент текста в долговременную память."""
       self.collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])


   def search_memory(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
       """Ищет наиболее релевантную информацию в памяти."""
       results = self.collection.query(query_texts=[query], n_results=n_results)
       found_docs = []
       if results and results["documents"]:
           for i, doc in enumerate(results["documents"][0]):
               found_docs.append({
                   "id": results["ids"][0][i],
                   "document": doc,
                   "metadata": results["metadatas"][0][i],
                   "distance": results["distances"][0][i]
               })
       return found_docs
