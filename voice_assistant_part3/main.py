import asyncio
import concurrent.futures
from whisper_recognizer import recognize_from_microphone, preload_whisper_model
from coqui_tts import speak, preload_tts_model
from ollama_client import ask_ollama, get_cache_stats, clear_ollama_cache
import time
import threading
import sys
import os
from queue import Queue

# Импортируем конфигурацию для оптимизации
try:
    from config import (
        THREAD_POOL_SIZE, USE_ASYNC_PROCESSING, PRELOAD_MODELS, 
        USE_RESPONSE_CACHE, MAX_CACHE_SIZE, PERFORMANCE_LOGGING
    )
except ImportError:
    # Настройки по умолчанию
    THREAD_POOL_SIZE = 3
    USE_ASYNC_PROCESSING = True
    PRELOAD_MODELS = True
    USE_RESPONSE_CACHE = True
    MAX_CACHE_SIZE = 50
    PERFORMANCE_LOGGING = True

# Импортируем веб-сервер
try:
    from web_server import start_web_server, update_state, socketio
    WEB_ENABLED = True
except ImportError:
    print("⚠️ Веб-интерфейс недоступен. Запуск в обычном режиме.")
    WEB_ENABLED = False
    def update_state(status, message=''):
        pass

class VoiceAssistantPipeline:
    """Оптимизированный пайплайн обработки с кэшированием и предзагрузкой"""
    
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE)
        self.response_cache = {} if USE_RESPONSE_CACHE else None
        self.is_processing = False
        self.models_loaded = False
        
    def preload_models(self):
        """Предзагрузка всех моделей в фоне"""
        if not PRELOAD_MODELS or self.models_loaded:
            return
            
        print("🔄 Предзагрузка моделей...")
        start_time = time.time()
        
        # Предзагружаем TTS модель
        future_tts = self.executor.submit(self._preload_tts)
        
        # Предзагружаем Whisper модель  
        future_whisper = self.executor.submit(self._preload_whisper)
        
        # Ждем завершения загрузки
        try:
            tts_success = future_tts.result(timeout=30)
            whisper_success = future_whisper.result(timeout=30)
            
            if PERFORMANCE_LOGGING:
                duration = time.time() - start_time
                print(f"✅ Модели предзагружены за {duration:.2f}s (TTS: {tts_success}, Whisper: {whisper_success})")
            else:
                print("✅ Все модели предзагружены")
                
            self.models_loaded = True
            
        except Exception as e:
            print(f"⚠️ Ошибка предзагрузки моделей: {e}")
    
    def _preload_tts(self):
        """Предзагрузка TTS модели"""
        try:
            return preload_tts_model()
        except Exception as e:
            print(f"⚠️ Ошибка предзагрузки TTS: {e}")
            return False
    
    def _preload_whisper(self):
        """Предзагрузка Whisper модели"""
        try:
            return preload_whisper_model()
        except Exception as e:
            print(f"⚠️ Ошибка предзагрузки Whisper: {e}")
            return False
    
    async def process_voice_request(self):
        """Асинхронная обработка голосового запроса"""
        if self.is_processing:
            return
            
        self.is_processing = True
        total_start_time = time.time() if PERFORMANCE_LOGGING else None
        
        try:
            # Этап 1: Распознавание речи
            loop = asyncio.get_event_loop()
            
            if PERFORMANCE_LOGGING:
                print("🎤 Начинаю распознавание речи...")
                speech_start = time.time()
                
            user_text = await loop.run_in_executor(
                self.executor, recognize_from_microphone
            )
            
            if PERFORMANCE_LOGGING:
                speech_duration = time.time() - speech_start
                print(f"🎤 Распознавание завершено за {speech_duration:.2f}s")
            
            if not user_text.strip():
                return
                
            print(f"🗣 Вы: {user_text}")
            
            # Проверяем кэш ответов
            response = None
            if self.response_cache is not None:
                cache_key = user_text.lower().strip()
                response = self.response_cache.get(cache_key)
                if response and PERFORMANCE_LOGGING:
                    print("💾 Ответ получен из кэша")
            
            if response is None:
                # Этап 2: Генерация ответа
                update_state('THINKING', 'JARVIS думает')
                
                if PERFORMANCE_LOGGING:
                    llm_start = time.time()
                
                prompt = f"Ты — голосовой помощник. Отвечай кратко и по делу на русском. Часто есть похожие по звучанию слова, ориентируйся на мысль.\n\nВопрос: {user_text}"
                
                response = await loop.run_in_executor(
                    self.executor, ask_ollama, prompt
                )
                
                if PERFORMANCE_LOGGING:
                    llm_duration = time.time() - llm_start
                    print(f"🤖 LLM ответил за {llm_duration:.2f}s")
                
                # Кэшируем ответ (ограничиваем размер кэша)
                if self.response_cache is not None and not response.startswith("❌"):
                    if len(self.response_cache) >= MAX_CACHE_SIZE:
                        # Удаляем старые записи (простая FIFO стратегия)
                        oldest_key = next(iter(self.response_cache))
                        del self.response_cache[oldest_key]
                    self.response_cache[cache_key] = response
            
            print(f"🤖 JARVIS: {response}")
            
            # Этап 3: Озвучивание
            update_state('SPEAKING', 'JARVIS отвечает')
            
            if PERFORMANCE_LOGGING:
                tts_start = time.time()
                
            await loop.run_in_executor(self.executor, speak, response)
            
            if PERFORMANCE_LOGGING:
                tts_duration = time.time() - tts_start
                total_duration = time.time() - total_start_time
                print(f"🗣️ TTS завершен за {tts_duration:.2f}s")
                print(f"⏱️ Общее время обработки: {total_duration:.2f}s")
            
        except Exception as e:
            print(f"❌ Ошибка в пайплайне: {e}")
        finally:
            self.is_processing = False
            update_state('IDLE', 'Готов к работе')
    
    def get_stats(self):
        """Возвращает статистику пайплайна"""
        cache_stats = get_cache_stats()
        return {
            'models_loaded': self.models_loaded,
            'is_processing': self.is_processing,
            'cache_size': len(self.response_cache) if self.response_cache else 0,
            'ollama_cache': cache_stats,
            'thread_pool_size': THREAD_POOL_SIZE
        }
    
    def clear_cache(self):
        """Очищает все кэши"""
        if self.response_cache:
            self.response_cache.clear()
        clear_ollama_cache()
        print("🗑️ Все кэши очищены")
    
    def shutdown(self):
        """Корректное завершение работы пайплайна"""
        print("🛑 Завершение работы пайплайна...")
        self.executor.shutdown(wait=True)

def main():
    print("🟢 JARVIS запущен. Инициализация...")
    
    # Создаем оптимизированный пайплайн
    pipeline = VoiceAssistantPipeline()
    
    # Запускаем веб-сервер если доступен
    if WEB_ENABLED:
        print("🌐 Веб-интерфейс доступен по адресу: http://127.0.0.1:5000")
        web_thread = threading.Thread(target=start_web_server, daemon=True)
        web_thread.start()
        time.sleep(1)
        update_state('LOADING', 'Загрузка моделей')
    
    # Предзагружаем модели
    pipeline.preload_models()
    
    # Показываем статистику
    stats = pipeline.get_stats()
    if PERFORMANCE_LOGGING:
        print(f"📊 Статистика системы: {stats}")
    
    update_state('IDLE', 'Готов к работе')
    print("🟢 Готов к работе. Говорите, чтобы начать.")
    
    # Выбираем режим обработки
    if USE_ASYNC_PROCESSING:
        # Асинхронный режим
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while True:
                update_state('LISTENING', 'JARVIS слушает')
                loop.run_until_complete(pipeline.process_voice_request())
                time.sleep(0.1)  # Маленькая пауза между циклами
                
        except KeyboardInterrupt:
            print("\n🛑 Ассистент остановлен.")
        finally:
            pipeline.shutdown()
            loop.close()
            if WEB_ENABLED:
                update_state('IDLE', 'Остановлен')
    else:
        # Обычный синхронный режим
        try:
            while True:
                update_state('LISTENING', 'JARVIS слушает')
                
                user_text = recognize_from_microphone()
                if not user_text.strip():
                    update_state('IDLE', 'Готов к работе')
                    continue
                    
                print(f"🗣 Вы: {user_text}")
                
                update_state('THINKING', 'JARVIS думает')
                
                prompt = f"Ты — голосовой помощник. Отвечай кратко и по делу на русском. Часто есть прхожие по звучаниб слова орентируйся на мысль.\n\nВопрос: {user_text}"
                response = ask_ollama(prompt)
                print(f"🤖 JARVIS: {response}")
                
                update_state('SPEAKING', 'JARVIS отвечает')
                
                speak(response)
                
                time.sleep(0.5)
                update_state('IDLE', 'Готов к работе')
                
        except KeyboardInterrupt:
            print("\n🛑 Ассистент остановлен.")
            if WEB_ENABLED:
                update_state('IDLE', 'Остановлен')

if __name__ == "__main__":
    main()
