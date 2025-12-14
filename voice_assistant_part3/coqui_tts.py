import torch
import soundfile as sf
import os
import sys
import time

# Проверка доступности GPU
use_cuda = torch.cuda.is_available()
device = torch.device('cuda' if use_cuda else 'cpu')

# Глобальные переменные для ленивой загрузки модели
_model_cache = None
_model_loaded = False
_model_loading = False

def load_model_once():
    """Ленивая загрузка модели только при первом использовании"""
    global _model_cache, _model_loaded, _model_loading
    
    if _model_loaded:
        return _model_cache
    
    if _model_loading:
        # Ждем завершения загрузки в другом потоке
        while _model_loading and not _model_loaded:
            time.sleep(0.1)
        return _model_cache
    
    _model_loading = True
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'model.pt')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель не найдена: {model_path}")
        
        print(f"🔊 Загружаю TTS модель: {model_path}")
        
        # Загружаем модель
        imp = torch.package.PackageImporter(model_path)
        _model_cache = imp.load_pickle("tts_models", "model")
        _model_cache.to(device)
        
        # Оптимизация модели для inference (если доступно)
        if hasattr(_model_cache, 'eval'):
            _model_cache.eval()
        
        # Используем FP16 для GPU ускорения если доступно
        if hasattr(_model_cache, 'half') and device.type == 'cuda':
            _model_cache = _model_cache.half()
        
        _model_loaded = True
        print(f"✅ TTS модель загружена на устройство: {device}")
        return _model_cache
        
    except Exception as e:
        print(f"❌ Ошибка загрузки TTS модели: {e}")
        print("⚠️ TTS будет работать в режиме вывода текста")
        _model_loaded = True
        _model_cache = None
        return None
    finally:
        _model_loading = False

# Модель будет загружена при первом вызове speak()
model = None

def speak(text, sample_rate=24000):  # Используем поддерживаемый sample_rate
    """Оптимизированная функция для синтеза речи"""
    global model
    
    # Ленивая загрузка модели
    if model is None:
        model = load_model_once()
    
    if model is None:
        print(f"⚠️ TTS недоступен, текст: {text}")
        return
        
    try:
        print(f"🗣️ Озвучиваю: {text}")
        start_time = time.time()
        
        # Используем torch.inference_mode для максимальной скорости
        with torch.inference_mode():
            audio = model.apply_tts(text=text, sample_rate=sample_rate)

        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()

        # Воспроизводим напрямую без сохранения файла (экономия времени)
        import sounddevice as sd
        sd.play(audio, sample_rate)
        sd.wait()
        
        duration = time.time() - start_time
        print(f"✅ Озвучивание завершено за {duration:.2f}s")

    except Exception as e:
        print(f"❌ Ошибка озвучки: {e}")

def preload_tts_model():
    """Предзагрузка TTS модели (для использования в async режиме)"""
    global model
    if model is None:
        model = load_model_once()
    return model is not None
