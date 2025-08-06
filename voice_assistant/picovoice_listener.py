import pvporcupine
import sounddevice as sd
import numpy as np


def wait_for_wakeword():
    # Выбираем микрофон (например, JBL Quantum350 Wireless с индексом 1)
    sd.default.device = (1, None)

    porcupine = pvporcupine.create(
        access_key='',
        keywords=['picovoice']
    )

    print("🎤 Жду ключевое слово 'jarvis'...")

    def get_next_audio_frame():
        audio = sd.rec(
            frames=porcupine.frame_length,
            samplerate=porcupine.sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        return np.squeeze(audio)

    try:
        while True:
            audio_frame = get_next_audio_frame()

            volume = np.abs(audio_frame).mean()
            keyword_index = porcupine.process(audio_frame)

            print(f"🔊 Громкость: {volume:.0f}, keyword_index: {keyword_index}")

            if keyword_index >= 0:
                print("🟢 Ключевое слово обнаружено!")
                break

    finally:
        porcupine.delete()
        print("🧹 Porcupine завершён.")


if __name__ == "__main__":
    wait_for_wakeword()
