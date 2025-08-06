import pvporcupine
import sounddevice as sd
import numpy as np

# Попробуем стандартное ключевое слово
porcupine = pvporcupine.create(
    access_key='dKC22W2ibDye540Q0XXg9UkQOrGYPV0k0NrX3EUBo01/GZ0p2qqKCA==',
    keywords=['porcupine']  # Самое надежное стандартное слово
)

print("🎤 Говорите 'Porcupine'...")

def get_next_audio_frame():
    audio = sd.rec(
        frames=porcupine.frame_length,
        samplerate=porcupine.sample_rate,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    return audio.flatten()

try:
    for i in range(100):  # Ограниченное число попыток
        audio_frame = get_next_audio_frame()
        keyword_index = porcupine.process(audio_frame)
        
        volume = np.abs(audio_frame).mean()
        print(f"Попытка {i+1}: громкость {volume:.0f}, индекс {keyword_index}")
        
        if keyword_index >= 0:
            print("🟢 РАБОТАЕТ! Ключевое слово обнаружено!")
            break
    else:
        print("❌ Не работает даже с 'porcupine'")
        
except Exception as e:
    print(f"Ошибка: {e}")
finally:
    porcupine.delete()