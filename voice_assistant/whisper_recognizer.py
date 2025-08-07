import pyaudio
import numpy as np
import webrtcvad
import whisper
import threading

# --- Константы ---
FORMAT = pyaudio.paInt16  # Формат аудио
CHANNELS = 1              # Моно-канал
RATE = 16000              # Частота дискретизации
CHUNK_DURATION_MS = 30    # Длительность чанка в миллисекундах
CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # Размер чанка
SILENCE_TIMEOUT = 1.0     # Таймаут тишины для остановки записи (секунды)
RMS_THRESHOLD = 200       # Порог громкости для фильтрации тишины

# --- Загрузка модели Whisper ---
model = whisper.load_model("small")

def recognize_from_microphone():
    # 1. Настройка детектора голоса (более строгий режим)
    vad = webrtcvad.Vad()
    vad.set_mode(3)  # Режим 3 - самый строгий (лучше фильтрует шумы)

    # Настройка аудиопотока
    audio_interface = pyaudio.PyAudio()
    stream = audio_interface.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK_SIZE)

    frames = []
    silence_duration = 0
    stop_flag = {"stop": False}

    # Поток для остановки записи по нажатию Enter
    def listen_for_enter(stop_flag):
        input()
        stop_flag["stop"] = True

    threading.Thread(target=listen_for_enter, args=(stop_flag,), daemon=True).start()
    print("🎤 Идёт запись... Нажмите Enter чтобы остановить.")

    # Основной цикл записи
    while not stop_flag["stop"]:
        try:
            audio_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        except (IOError, OSError) as e:
            print(f"Ошибка чтения аудио: {e}")
            continue

        is_speech = vad.is_speech(audio_data, RATE)

        if is_speech:
            silence_duration = 0
            frames.append(np.frombuffer(audio_data, dtype=np.int16))
        else:
            silence_duration += CHUNK_DURATION_MS / 1000

        # Остановка если долго нет голоса (но только если уже что-то записано)
        if frames and silence_duration > SILENCE_TIMEOUT:
            break

    stream.stop_stream()
    stream.close()
    audio_interface.terminate()

    if not frames:
        return ""

    # Объединение всех фрагментов аудио
    full_audio = np.concatenate(frames)
    
    # 2. Фильтрация по громкости
    rms = np.sqrt(np.mean(full_audio.astype(np.float32)**2))
    if rms < RMS_THRESHOLD:
        print(f"🎤 Аудио слишком тихое (RMS: {rms:.2f}), пропускаем.")
        return ""

    # Нормализация аудио для Whisper
    audio_for_whisper = full_audio.astype(np.float32) / 32768.0

    try:
        print("🧠 Распознавание речи...")
        # 3. Распознавание с защитой от "галлюцинаций"
        result = model.transcribe(audio_for_whisper, language="ru", no_speech_threshold=0.78)
        text = result["text"].strip()
        
        if len(text) < 2:  # Игнорируем слишком короткие результаты
            return ""
            
        return text
    except Exception as e:
        print(f"Ошибка при распознавании: {e}")
        return ""

# Пример использования
if __name__ == '__main__':
    recognized_text = recognize_from_microphone()
    if recognized_text:
        print("\n📝 Распознанный текст:")
        print(recognized_text)