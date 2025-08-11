import time
import threading

import pyaudio
import numpy as np
import webrtcvad
import torch
from faster_whisper import WhisperModel

# Попытка импортировать noisereduce (опционально для шумоподавления)
try:
    import noisereduce as nr
    USE_NOISEREDUCE = True
except ImportError:
    USE_NOISEREDUCE = False

# -------------- Настройки --------------
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

CHUNK_MS = 30  # Размер аудио-фрейма в миллисекундах (10, 20 или 30 для webrtcvad)
CHUNK_SIZE = int(RATE * CHUNK_MS / 1000)

CALIBRATE_SECONDS = 0.8  # Сколько секунд слушаем тишину для калибровки фонового шума

SILENCE_TIMEOUT = 1.5  # Время тишины (в секундах), по которому считаем конец фразы

MAX_UTTERANCE = 12.0  # Максимальная длина записи (сек)

START_MULTIPLIER = 3.0  # Порог начала речи = фон * этот множитель
END_MULTIPLIER = 1.3    # Порог окончания речи = фон * этот множитель

TARGET_RMS = 0.07  # Целевая громкость после AGC

EMA_ALPHA = 0.25  # Параметр сглаживания громкости

BEAM_SIZE = 5  # Beam search — точность распознавания, можно увеличить, но будет медленнее

MODEL_SIZE = "small"  # Размер модели whisper (tiny, base, small, medium и т.д.)

# ----------------------------------------

def create_model(size=MODEL_SIZE):
    """
    Загружает faster-whisper модель с попыткой оптимального compute_type.
    Для RTX 4060 рекомендуем float16 (быстро и эффективно).
    Если модель не грузится — пробует другие варианты.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tries = ["float16", "int8_float16", "float32"] if device == "cuda" else ["int8", "float32"]

    last_exception = None
    for compute_type in tries:
        try:
            print(f"[model] Загружаю модель: device={device}, compute_type={compute_type}")
            model = WhisperModel(size, device=device, compute_type=compute_type)
            print(f"[model] Модель успешно загружена: device={device}, compute_type={compute_type}")
            return model
        except Exception as e:
            print(f"[model] Не удалось загрузить с compute_type={compute_type}: {e}")
            last_exception = e
    raise RuntimeError(f"Не удалось загрузить модель faster-whisper: {last_exception}")

model = create_model()

def recognize_from_microphone():
    """
    Записывает аудио с микрофона, используя VAD и RMS для определения речи.
    После окончания записи (пауза по тишине или превышение лимита),
    выполняет шумоподавление (опционально), нормализацию и передает аудио в faster-whisper.
    """

    vad = webrtcvad.Vad(3)  # Максимально строгий режим для детекции речи

    audio_interface = pyaudio.PyAudio()
    stream = audio_interface.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK_SIZE)

    stop_flag = {"stop": False}

    def wait_for_enter():
        input("🎤 Говорите. Нажмите Enter, чтобы остановить запись вручную...\n")
        stop_flag["stop"] = True

    threading.Thread(target=wait_for_enter, daemon=True).start()

    print("🔊 Запускаем короткую калибровку фона, пожалуйста, тишина...")
    calib_frames = []
    calib_end_time = time.time() + CALIBRATE_SECONDS
    while time.time() < calib_end_time:
        try:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        except Exception as e:
            print(f"Ошибка чтения во время калибровки: {e}")
            continue
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        calib_frames.append(arr)

    ambient_rms = float(np.sqrt(np.mean(np.concatenate(calib_frames) ** 2))) if calib_frames else 1e-4

    # Вычисляем пороги начала и окончания речи на основе фонового шума
    start_threshold = max(ambient_rms * START_MULTIPLIER, 1e-4)
    end_threshold = max(ambient_rms * END_MULTIPLIER, 1e-4)

    # Если фоновый уровень слишком низкий — сообщаем, но продолжаем
    if ambient_rms < 0.005:
        print(f"📉 Внимание: уровень фонового шума очень низкий (RMS={ambient_rms:.5f}). "
              f"Проверьте микрофон или громкость.")

    print("🎙️ Готов к записи. Начинайте говорить.")

    frames = []
    recording = False
    silence_duration = 0.0
    recorded_time = 0.0
    ema_energy = ambient_rms

    while not stop_flag["stop"]:
        try:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        except Exception as e:
            print(f"Ошибка чтения аудио: {e}")
            continue

        # Проверяем, есть ли речь с помощью VAD
        is_speech = vad.is_speech(data, RATE)

        # Конвертируем в float32 [-1..1]
        frame = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

        # RMS для текущего кадра
        frame_rms = float(np.sqrt(np.mean(frame ** 2)))

        # Сглаживаем громкость для устойчивого порога
        ema_energy = EMA_ALPHA * frame_rms + (1 - EMA_ALPHA) * ema_energy

        # Запускаем запись если есть речь по VAD или громкость выше порога начала
        if not recording:
            if is_speech or ema_energy > start_threshold:
                recording = True
                frames = []
                silence_duration = 0.0
                recorded_time = 0.0
                print("🔴 Запись началась...")

        if recording:
            frames.append(frame)
            recorded_time += CHUNK_MS / 1000.0

            # Если речь или громкость выше порога окончания — сбрасываем таймер тишины
            if is_speech or ema_energy > end_threshold:
                silence_duration = 0.0
            else:
                silence_duration += CHUNK_MS / 1000.0

            # Если пауза слишком длинная — завершаем запись
            if silence_duration > SILENCE_TIMEOUT:
                print(f"🔇 Таймаут тишины ({silence_duration:.2f} сек) — заканчиваем запись.")
                break

            # Если превысили максимально допустимую длину — завершаем
            if recorded_time > MAX_UTTERANCE:
                print("⏱️ Максимальная длительность записи достигнута — заканчиваем.")
                break

    # Закрываем аудио поток
    try:
        stream.stop_stream()
        stream.close()
    except Exception:
        pass
    audio_interface.terminate()

    if not frames:
        print("⛔ Ничего не записано.")
        return ""

    full_audio = np.concatenate(frames)

    # Автоматическая регулировка громкости (AGC)
    current_rms = float(np.sqrt(np.mean(full_audio ** 2))) + 1e-9
    gain = TARGET_RMS / current_rms
    gain = float(max(0.5, min(gain, 10.0)))  # ограничиваем усиление
    full_audio = full_audio * gain

    # Опциональное шумоподавление, если есть библиотека noisereduce
    if USE_NOISEREDUCE:
        try:
            full_audio = nr.reduce_noise(y=full_audio, sr=RATE)
        except Exception as e:
            print(f"noisereduce ошибка: {e}")

    # Нормализация по пику (чтобы не клиппить)
    peak = np.max(np.abs(full_audio)) + 1e-9
    full_audio = full_audio / peak * 0.99

    # Передаём в модель (faster-whisper)
    print("🧠 Распознавание...")
    try:
        segments, _ = model.transcribe(full_audio.astype(np.float32),
                                      language="ru",
                                      beam_size=BEAM_SIZE)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        print("✅ Распознано:", text)
        return text
    except Exception as e:
        print(f"⚠️ Ошибка распознавания: {e}")
        return ""

if __name__ == "__main__":
    recognize_from_microphone()
