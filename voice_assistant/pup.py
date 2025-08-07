import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
DURATION = 0.5  # длина блока в секундах

def rms(data):
    return np.sqrt(np.mean(np.square(data)))

def measure_noise():
    print("🔊 Измерение шума с микрофона. Нажмите Ctrl+C для выхода.")
    try:
        while True:
            audio = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            audio = audio.flatten()
            level = rms(audio)
            print(f"Уровень шума (RMS): {level:.5f}")
    except KeyboardInterrupt:
        print("\nВыход.")

if __name__ == "__main__":
    measure_noise()
