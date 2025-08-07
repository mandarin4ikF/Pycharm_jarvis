import sounddevice as sd
import vosk
import queue
import sys
import json

# Путь к модели Vosk
model_path = r"c:/Pycharm_jarvis/voice_assistant/vosk-model-small-ru-0.22"

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

# Инициализация модели Vosk
try:
    print("[Загрузка модели Vosk...]")
    model = vosk.Model(model_path)
    print("[✅] Модель загружена успешно!")
except Exception as e:
    print(f"[Ошибка загрузки модели] {e}")
    sys.exit(1)

# Настройки аудио
samplerate = 16000  # Обычно модель ожидает 16 кГц
block_duration = 0.5  # 0.5 секунды
block_size = int(samplerate * block_duration)

# Очередь для аудио данных
q = queue.Queue()

# Колбэк для записи аудио
def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[Статус потока] {status}")
    q.put(bytes(indata))

# Функция для распознавания речи
def recognize_wake_word():
    print("\n[⏳] Инициализация потока... Говори слово-активатор.")
    with sd.InputStream(samplerate=samplerate, blocksize=block_size, callback=audio_callback, channels=1, dtype='int16'):
        print("[✅] Готов к прослушиванию. Нажми Ctrl+C для выхода.\n")
        rec = vosk.KaldiRecognizer(model, samplerate)
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if result['text']:
                    print(f"[🎤 Распознано: {result['text']}]")
                    if "привет" in result['text'].lower():
                        print(f"[🎤 Активировано слово с уверенностью]")
                        break
            else:
                partial_result = json.loads(rec.PartialResult())
                if partial_result['partial']:
                    print(f"[🎤 Частичный результат: {partial_result['partial']}]")

try:
    recognize_wake_word()
except KeyboardInterrupt:
    print("\n[🛑] Завершено пользователем.")
except Exception as e:
    print(f"[Ошибка запуска аудио потока] {e}")
