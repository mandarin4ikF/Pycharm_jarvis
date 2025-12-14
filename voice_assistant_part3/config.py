#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурационный файл для оптимизации производительности голосового помощника
Этот файл содержит все настройки для тонкой настройки скорости работы системы
"""

import os
import torch

# =============================================================================
# ОБЩИЕ НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ
# =============================================================================

# Использование асинхронной обработки
USE_ASYNC_PROCESSING = True

# Предзагрузка всех моделей при старте
PRELOAD_MODELS = True

# Использование кэширования ответов
USE_RESPONSE_CACHE = True
MAX_CACHE_SIZE = 50

# Размер пула потоков для параллельной обработки
THREAD_POOL_SIZE = 3

# Оптимизация использования памяти
MEMORY_OPTIMIZATION = True

# =============================================================================
# НАСТРОЙКИ TTS (Text-to-Speech)
# =============================================================================

# Частота дискретизации для TTS (поддерживаемые: 8000, 24000, 48000)
TTS_SAMPLE_RATE = 24000  # Оптимальный баланс качества и скорости

# Использование кэширования TTS модели
TTS_USE_CACHE = True

# Предзагрузка TTS модели при инициализации
TTS_PRELOAD = True

# Использование оптимизированного inference режима
TTS_USE_INFERENCE_MODE = True

# Сохранение промежуточных аудио файлов (False = воспроизведение напрямую)
TTS_SAVE_AUDIO_FILES = False

# =============================================================================
# НАСТРОЙКИ WHISPER (Speech Recognition)
# =============================================================================

# Размер модели Whisper (tiny, base, small, medium, large)
# tiny - самая быстрая, large - самая точная
WHISPER_MODEL_SIZE = "base"  # Увеличиваем размер для лучшего качества

# Beam size для поиска (1 = быстрее, больше = точнее)
WHISPER_BEAM_SIZE = 3  # Увеличиваем для лучшего качества

# Использование GPU для Whisper если доступно
WHISPER_USE_GPU = torch.cuda.is_available()

# Тип вычислений для CPU (оптимизировано для процессора)
WHISPER_COMPUTE_TYPE = "int8" if not WHISPER_USE_GPU else "int8_float16"

# Количество CPU потоков для Whisper
WHISPER_CPU_THREADS = os.cpu_count() or 4  # Используем все доступные ядра

# Количество workers для обработки
WHISPER_NUM_WORKERS = 2  # Увеличиваем для лучшей производительности

# Оптимизированные параметры транскрипции для лучшего качества
WHISPER_TEMPERATURE = [0.0, 0.2, 0.4]  # Несколько попыток с разной температурой
WHISPER_BEST_OF = 2  # Увеличиваем количество попыток
WHISPER_CONDITION_ON_PREVIOUS_TEXT = True  # Включаем контекст для лучшего понимания
WHISPER_NO_SPEECH_THRESHOLD = 0.5  # Снижаем порог для лучшего обнаружения речи
WHISPER_COMPRESSION_RATIO_THRESHOLD = 2.4

# =============================================================================
# НАСТРОЙКИ VAD (Voice Activity Detection)
# =============================================================================

# Агрессивность VAD (0-3, где 3 - самый строгий)
VAD_AGGRESSIVENESS = 2  # Уменьшаем для лучшего обнаружения тихой речи

# Длительность аудио фрейма в миллисекундах (10, 20 или 30)
VAD_FRAME_DURATION = 20  # Уменьшаем для более чувствительного обнаружения

# Таймаут тишины для окончания записи (секунды)
SILENCE_TIMEOUT = 2.0  # Увеличиваем для захвата длинных фраз

# Максимальная длительность записи (секунды)
MAX_UTTERANCE = 10.0  # Увеличиваем для длинных сообщений

# Множители для определения начала и конца речи
START_MULTIPLIER = 2.5  # Снижаем для лучшего обнаружения тихой речи
END_MULTIPLIER = 1.2    # Порог окончания речи

# Время калибровки фонового шума (секунды)
CALIBRATE_SECONDS = 1.0  # Увеличиваем для лучшей калибровки

# Целевая громкость после автоматической регулировки
TARGET_RMS = 0.08  # Немного увеличиваем целевую громкость

# Параметр сглаживания громкости
EMA_ALPHA = 0.3  # Увеличиваем для более быстрого отклика

# =============================================================================
# НАСТРОЙКИ АУДИО
# =============================================================================

# Формат аудио данных
AUDIO_FORMAT = "int16"

# Количество каналов
AUDIO_CHANNELS = 1

# Частота дискретизации для записи
AUDIO_SAMPLE_RATE = 16000

# Размер аудио чанка (20ms при 16kHz)
AUDIO_CHUNK_SIZE = 320  # Обновлено для 20ms фреймов

# =============================================================================
# НАСТРОЙКИ OLLAMA (LLM)
# =============================================================================

# URL сервера Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Модель для использования
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Таймаут запроса (секунды)
OLLAMA_TIMEOUT = 10  # Уменьшено для быстрого отклика

# Максимальное количество токенов в ответе
OLLAMA_MAX_TOKENS = 100

# Параметры генерации текста
OLLAMA_TEMPERATURE = 0.7
OLLAMA_TOP_P = 0.9
OLLAMA_NUM_CTX = 2048  # Контекст для экономии памяти

# Использование переиспользуемой HTTP сессии
OLLAMA_USE_SESSION = True

# Кэширование коротких запросов (длина меньше указанной)
OLLAMA_CACHE_SHORT_REQUESTS = True
OLLAMA_CACHE_THRESHOLD = 200  # символов

# =============================================================================
# НАСТРОЙКИ СИСТЕМЫ
# =============================================================================

# Путь к директории проекта
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Пути к моделям
TTS_MODEL_PATH = os.path.join(PROJECT_DIR, 'model.pt')
TTS_V4_MODEL_PATH = os.path.join(PROJECT_DIR, 'v4_ru.pt')

# Логирование производительности
PERFORMANCE_LOGGING = True

# Мониторинг использования памяти
MEMORY_MONITORING = True

# =============================================================================
# ФУНКЦИИ УТИЛИТЫ
# =============================================================================

def get_optimal_device():
    """Возвращает оптимальное устройство для вычислений"""
    if torch.cuda.is_available():
        return torch.device('cuda')
    return torch.device('cpu')

def get_whisper_config():
    """Возвращает конфигурацию для Whisper модели"""
    return {
        'model_size': WHISPER_MODEL_SIZE,
        'device': 'cuda' if WHISPER_USE_GPU else 'cpu',
        'compute_type': WHISPER_COMPUTE_TYPE,
        'cpu_threads': WHISPER_CPU_THREADS,
        'num_workers': WHISPER_NUM_WORKERS
    }

def get_ollama_config():
    """Возвращает конфигурацию для Ollama"""
    return {
        'url': OLLAMA_URL,
        'model': OLLAMA_MODEL,
        'timeout': OLLAMA_TIMEOUT,
        'options': {
            'temperature': OLLAMA_TEMPERATURE,
            'top_p': OLLAMA_TOP_P,
            'num_ctx': OLLAMA_NUM_CTX,
            'num_predict': OLLAMA_MAX_TOKENS
        }
    }

def get_vad_config():
    """Возвращает конфигурацию для VAD"""
    return {
        'aggressiveness': VAD_AGGRESSIVENESS,
        'frame_duration': VAD_FRAME_DURATION,
        'silence_timeout': SILENCE_TIMEOUT,
        'max_utterance': MAX_UTTERANCE,
        'start_multiplier': START_MULTIPLIER,
        'end_multiplier': END_MULTIPLIER,
        'calibrate_seconds': CALIBRATE_SECONDS,
        'target_rms': TARGET_RMS,
        'ema_alpha': EMA_ALPHA
    }

def print_config_summary():
    """Выводит сводку текущей конфигурации"""
    print("🔧 Конфигурация системы:")
    print(f"   TTS: model_path={TTS_MODEL_PATH}, sample_rate={TTS_SAMPLE_RATE}")
    print(f"   Whisper: model={WHISPER_MODEL_SIZE}, device={'GPU' if WHISPER_USE_GPU else 'CPU'}")
    print(f"   Ollama: url={OLLAMA_URL}, model={OLLAMA_MODEL}")
    print(f"   Audio: rate={AUDIO_SAMPLE_RATE}Hz, channels={AUDIO_CHANNELS}")
    print(f"   Performance: async={USE_ASYNC_PROCESSING}, cache={USE_RESPONSE_CACHE}")

# =============================================================================
# АВТОМАТИЧЕСКАЯ ОПТИМИЗАЦИЯ
# =============================================================================

def auto_optimize_for_system():
    """Автоматическая оптимизация настроек под текущую систему"""
    global WHISPER_MODEL_SIZE, WHISPER_BEAM_SIZE, THREAD_POOL_SIZE
    
    # Проверяем доступную память GPU
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        
        if gpu_memory >= 8:  # 8GB+ VRAM
            WHISPER_MODEL_SIZE = "medium"
            WHISPER_BEAM_SIZE = 3
        elif gpu_memory >= 4:  # 4-8GB VRAM
            WHISPER_MODEL_SIZE = "small" 
            WHISPER_BEAM_SIZE = 1
        else:  # <4GB VRAM
            WHISPER_MODEL_SIZE = "base"
            WHISPER_BEAM_SIZE = 1
    
    # Проверяем количество CPU ядер
    cpu_count = os.cpu_count() or 4
    if cpu_count >= 8:
        THREAD_POOL_SIZE = 4
    elif cpu_count >= 4:
        THREAD_POOL_SIZE = 3
    else:
        THREAD_POOL_SIZE = 2
    
    print(f"🎯 Автооптимизация: Whisper={WHISPER_MODEL_SIZE}, Threads={THREAD_POOL_SIZE}")

# Запускаем автооптимизацию при импорте модуля
if __name__ != "__main__":
    auto_optimize_for_system()