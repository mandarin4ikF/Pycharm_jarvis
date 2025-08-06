import sounddevice as sd
import numpy as np

print("Тест микрофона - говорите что-нибудь:")
audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='int16')
sd.wait()
volume = np.abs(audio).mean()
print(f"Уровень звука: {volume}")