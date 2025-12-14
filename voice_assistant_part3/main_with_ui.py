from whisper_recognizer import recognize_from_microphone
from coqui_tts import speak
from ollama_client import ask_ollama
from web_server import start_web_server, update_state
import time
import threading

def main():
    print("🟢 JARVIS запущен. Говорите, чтобы начать.")
    print("🌐 Веб-интерфейс доступен по адресу: http://127.0.0.1:5000")
    
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # Небольшая задержка для запуска сервера
    time.sleep(2)
    
    try:
        # Устанавливаем начальное состояние
        update_state('IDLE', 'Готов к работе')
        
        while True:
            # Обновляем состояние - слушаем
            update_state('LISTENING', 'Слушаю...')
            
            user_text = recognize_from_microphone()
            if not user_text.strip():
                update_state('IDLE', 'Готов к работе')
                continue
                
            print(f"🗣 Вы: {user_text}")
            
            # Обновляем состояние - думаем
            update_state('THINKING', 'Обрабатываю запрос')
            
            prompt = f"Ты — голосовой помощник. Отвечай кратко и по делу на русском. Часто есть прхожие по звучаниб слова орентируйся на мысль.\n\nВопрос: {user_text}"
            response = ask_ollama(prompt)
            print(f"🤖 JARVIS: {response}")
            
            # Обновляем состояние - говорим
            update_state('SPEAKING', 'Отвечаю')
            
            speak(response)
            
            # Небольшая пауза перед возвратом в состояние ожидания
            time.sleep(0.5)
            update_state('IDLE', 'Готов к работе')
            
    except KeyboardInterrupt:
        print("\n🛑 Ассистент остановлен.")
        update_state('IDLE', 'Остановлен')

if __name__ == "__main__":
    main()