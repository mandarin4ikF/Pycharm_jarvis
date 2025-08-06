from vosk import Model, KaldiRecognizer
import pyaudio
import json
import os
import pyttsx3
import requests
from dotenv import load_dotenv
import time

# ╔═══════════════════════════════════════╗
# ║     Загрузка переменных окружения      ║
# ╚═══════════════════════════════════════╝
load_dotenv()  # Подгружаем настройки из .env (например, API ключи)

# ╔═══════════════════════════════════════╗
# ║         Настройка путей и параметров    ║
# ╚═══════════════════════════════════════╝
MODEL_PATH = os.path.join(os.path.dirname(__file__), "vosk-model-small-ru-0.22")  # Путь к модели Vosk
OLLAMA_URL = "http://localhost:11434"  # Локальный адрес сервера Ollama
OLLAMA_MODEL = "llama3"                  # Имя модели Ollama, которую используем

# ╔═══════════════════════════════════════╗
# ║         Проверка наличия модели Vosk    ║
# ╚═══════════════════════════════════════╝
if not os.path.exists(MODEL_PATH):
    print(f"Ошибка: папка модели '{MODEL_PATH}' не найдена!")
    exit(1)

# ╔═══════════════════════════════════════╗
# ║       Инициализация модели Vosk         ║
# ╚═══════════════════════════════════════╝
model = Model(MODEL_PATH)  # Загружаем модель для распознавания речи
recognizer = KaldiRecognizer(model, 16000)  # Инициализируем распознаватель с частотой 16 кГц

# ╔═══════════════════════════════════════╗
# ║        Настройка микрофона PyAudio      ║
# ╚═══════════════════════════════════════╝
mic = pyaudio.PyAudio()  # Инициализация PyAudio
stream = mic.open(
    format=pyaudio.paInt16,     # 16-битный звук
    channels=1,                 # Моно канал
    rate=16000,                 # Частота дискретизации 16 кГц (та же, что у Vosk)
    input=True,                 # Вход с микрофона
    frames_per_buffer=4096      # Размер буфера для чтения данных
)

# ╔═══════════════════════════════════════╗
# ║      Инициализация синтеза речи        ║
# ╚═══════════════════════════════════════╝
engine = pyttsx3.init()  # Инициализируем движок озвучивания
engine.setProperty('rate', 150)  # Скорость речи (слов в минуту)
voices = engine.getProperty('voices')
for voice in voices:
    if 'russian' in voice.name.lower():  # Ищем и устанавливаем русский голос
        engine.setProperty('voice', voice.id)
        break


# ╔═══════════════════════════════════════╗
# ║         П О Л Е З Н Ы Е  Ф-Ц И И      ║
# ╚═══════════════════════════════════════╝

def ask_ollama(prompt):
    """
    Отправляет запрос на локальный Ollama сервер и возвращает ответ модели.
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",  # Эндпоинт для генерации текста
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()  # Проверяем успешный ответ сервера
        data = response.json()
        return data.get("response", "Нет поля 'response' в ответе")
    except Exception as e:
        return f"Ошибка при обращении к локальному ИИ: {e}"

def text_to_speech(text):
    """
    Озвучивает текст через pyttsx3.
    """
    engine.say(text)
    engine.runAndWait()

# ╔═══════════════════════════════════════╗
# ║              Основной цикл            ║
# ╚═══════════════════════════════════════╝

print("Говорите... (для выхода нажмите Ctrl+C)")

try:
    while True:
        try:
            # Читаем аудиоданные с микрофона, игнорируем переполнение буфера
            data = stream.read(4096, exception_on_overflow=False)
        except IOError as e:
            print(f"Ошибка чтения микрофона: {e}")
            continue  # Если ошибка — пропускаем итерацию

        # Если получена полноценная часть речи
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            user_text = result.get("text", "").strip()

            if user_text:
                print(f"Вы: {user_text}")

                prompt = (
                    "Ты — голосовой помощник Джарвис. Отвечай кратко и по существу. Отвечай на русском.\n\n"
                    f"Вопрос: {user_text}"
                )

                response = ask_ollama(prompt)
                print(f"JARVIS: {response}")
                text_to_speech(response)

        time.sleep(0.01)# Небольшая пауза для разгрузки процессора

except KeyboardInterrupt:
    print("Завершение...")

finally:
    # Безопасно закрываем аудио поток
    try:
        stream.stop_stream()
        stream.close()
        mic.terminate()
    except Exception as e:
        print(f"Ошибка при остановке аудио: {e}")
    engine.stop()
