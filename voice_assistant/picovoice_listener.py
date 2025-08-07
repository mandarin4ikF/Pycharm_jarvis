import tensorflow as tf
import sounddevice as sd
import numpy as np
import time
import sys
import os

model_path = r"C:\Pycharm_jarvis\.venv\Lib\site-packages\openwakeword\resources\models\alexa_v0.1.tflite"

# Проверка микрофонов
print("[Проверка микрофона]")
try:
    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    if not input_devices:
        print("[❌] Не найдено микрофонов!")
        sys.exit(1)
    print(f"[✅] Найдено устройств: {len(input_devices)}")
except Exception as e:
    print(f"[Ошибка доступа к микрофону] {e}")
    sys.exit(1)

# Загружаем tflite модель через TensorFlow Lite Interpreter
try:
    print("[Загрузка модели wake word...]")
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    print("[✅] Модель загружена успешно!")
except Exception as e:
    print(f"[Ошибка загрузки модели] {e}")
    sys.exit(1)

# Настройки аудио
samplerate = 16000  # Обычно модель ожидает 16 кГц
block_duration = 0.5  # 0.5 секунды
block_size = int(samplerate * block_duration)

# Для работы с моделями wake word нужно использовать специальный обработчик
# В данном случае, мы будем использовать предварительно подготовленные признаки

def predict_wake_word(audio_chunk):
    # Преобразуем аудио в нужный формат для модели
    # Модель ожидает int8 данные с размерностью [1, 1, 40]
    
    # Убедимся, что у нас правильное количество сэмплов
    if len(audio_chunk) != 40:
        print(f"[Ошибка] Ожидалось 40 сэмплов, получено {len(audio_chunk)}")
        return 0.0
    
    # Преобразуем float32 в int8
    audio_int8 = np.clip(audio_chunk * 127, -128, 127).astype(np.int8)
    
    # Подготовка данных для модели: [batch, time, features] -> [1, 1, 40]
    input_data = np.expand_dims(np.expand_dims(audio_int8, axis=0), axis=0)
    
    try:
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        confidence = output_data[0][0]
        return confidence
    except Exception as e:
        print(f"[Ошибка выполнения модели] {e}")
        return 0.0

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[Статус потока] {status}")
    try:
        # Получаем только первый канал
        audio_data = indata[:, 0]
        
        # Для модели wake word нам нужно передавать уже обработанные признаки
        # В данном случае, мы просто используем raw аудио как есть (не рекомендуется)
        # Но для корректной работы нужно использовать специальную обработку
        
        # Проверяем размер данных - модель ожидает 40 значений
        if len(audio_data) >= 40:
            # Используем последние 40 сэмплов
            data_for_model = audio_data[-40:]
            
            confidence = predict_wake_word(data_for_model)
            if confidence > 0.6:
                print(f"[🎤 Активировано слово с уверенностью {confidence:.2f}]")
        else:
            print(f"[Ошибка] Недостаточно данных для модели: {len(audio_data)} сэмплов")
            
    except Exception as e:
        print(f"[Ошибка обработки аудио] {e}")

print("\n[⏳] Инициализация потока... Говори wake word.")
try:
    with sd.InputStream(callback=audio_callback, channels=1, samplerate=samplerate, blocksize=block_size):
        print("[✅] Готов к прослушиванию. Нажми Ctrl+C для выхода.\n")
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\n[🛑] Завершено пользователем.")
except Exception as e:
    print(f"[Ошибка запуска аудио потока] {e}")
    print(f"[Ошибка запуска аудио потока] {e}")
    