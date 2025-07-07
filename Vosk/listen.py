from vosk import Model, KaldiRecognizer
import pyaudio
import json
import os
from openai import OpenAI  # Импортируем новый клиент
import pyttsx3

# --- Конфигурация ---
MODEL_PATH = os.path.join(os.path.dirname(__file__), "vosk-model-small-ru-0.22")
OPENAI_KEY = ''

# --- Инициализация ---
client = OpenAI(api_key=OPENAI_KEY)  # Новый клиент OpenAI

# 1. Проверка модели Vosk
if not os.path.exists(MODEL_PATH):
    print(f"Ошибка: папка модели '{MODEL_PATH}' не найдена!")
    exit(1)

# 2. Загрузка модели Vosk
model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)

# 3. Настройка микрофона
mic = pyaudio.PyAudio()
stream = mic.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=8192
)

# 4. Инициализация синтеза речи (оффлайн)
engine = pyttsx3.init()
engine.setProperty('rate', 150)
voices = engine.getProperty('voices')
for voice in voices:
    if 'russian' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break

# --- Функции ---
def ask_chatgpt(prompt):
    """Отправка запроса в ChatGPT (новый API)"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

def text_to_speech(text):
    """Озвучивание текста"""
    engine.say(text)
    engine.runAndWait()

# --- Основной цикл ---
print("Говорите... (для выхода нажмите Ctrl+C)")

try:
    while True:
        data = stream.read(4096)
        
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            user_text = result.get("text", "")
            
            if user_text:
                print(f"Вы: {user_text}")
                response = ask_chatgpt(user_text)
                print(f"GPT: {response}")
                text_to_speech(response)

except KeyboardInterrupt:
    print("Завершение...")
finally:
    stream.stop_stream()
    stream.close()
    mic.terminate()
    engine.stop()