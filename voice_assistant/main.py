from whisper_recognizer import recognize_from_microphone
from coqui_tts import speak
from ollama_client import ask_ollama
import time

def main():
    print("🟢 JARVIS запущен. Говорите, чтобы начать.")
    try:
        while True:
            user_text = recognize_from_microphone()
            if not user_text.strip():
                continue
            print(f"🗣 Вы: {user_text}")
            prompt = f"Ты — голосовой помощник. Отвечай кратко и по делу на русском. Часто есть прхожие по звучаниб слова орентируйся на мысль.\n\nВопрос: {user_text}"
            response = ask_ollama(prompt)
            print(f"🤖 JARVIS: {response}")
            speak(response)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 Ассистент остановлен.")

if __name__ == "__main__":
    main()
