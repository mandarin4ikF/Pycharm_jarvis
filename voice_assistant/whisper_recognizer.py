import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
import torch


SAMPLE_RATE = 16000
DURATION = 5
TEMP_PATH = "temp_audio.wav"

def record_audio(path=TEMP_PATH, duration=DURATION):
    print("▶️ Начинаем запись с микрофона...")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    audio = np.squeeze(audio)
    
    print(f"✅ Запись завершена. Длина: {len(audio)} сэмплов")
    print(f"📈 Средняя громкость: {np.mean(np.abs(audio)):.5f}")
    
    audio_int16 = np.int16(audio * 32767)
    wav.write(path, SAMPLE_RATE, audio_int16)
    print(f"💾 Аудио сохранено в файл: {path}")

def recognize(path=TEMP_PATH):
    try:
        print("🤖 Загружаем модель Whisper (turbo)...")
        model = whisper.load_model("turbo")

        print("📂 Загружаем аудио безопасно...")
        audio = whisper.load_audio(path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        print("🧠 Распознаём...")
        options = whisper.DecodingOptions(language="ru", fp16=torch.cuda.is_available())
        result = model.transcribe("temp_audio.wav", language="ru")
        return result["text"].strip()

    except Exception as e:
        print(f"❌ Ошибка распознавания: {e}")
        return ""

# === Запуск ===
print("🎤 Распознавание речи через Whisper")
record_audio()
text = recognize()
print("\n📝 Итог:")
print(text if text else "[Ничего не распознано]")