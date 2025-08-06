from whisper_recognizer import recognize_from_microphone
from coqui_tts import speak
from ollama_client import ask_ollama
from picovoice_listener import wait_for_wakeword

import time

def main():
    try:
        while True:
            wait_for_wakeword()
            print("Активация! Говорите...")

            user_text = recognize_from_microphone()
            if not user_text:
                continue

            print(f"Вы: {user_text}")

            prompt = (
                "Ты — голосовой помощник Джарвис. Отвечай кратко и по существу. Отвечай на русском.\n\n"
                f"Вопрос: {user_text}"
            )

            response = ask_ollama(prompt)
            print(f"JARVIS: {response}")

            speak(response)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nЗавершение работы ассистента...")

main()

