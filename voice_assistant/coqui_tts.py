import torch
import soundfile as sf
import os

# Проверка доступности GPU
use_cuda = torch.cuda.is_available()
device = torch.device('cuda' if use_cuda else 'cpu')

# Загрузка модели Coqui
model_path = os.path.join(os.path.dirname(__file__), 'v4_ru.pt')
imp = torch.package.PackageImporter(model_path)
model = imp.load_pickle("tts_models", "model")
model.to(device)

def speak(text, sample_rate=48000):
    try:
        with torch.no_grad():
            audio = model.apply_tts(text=text, sample_rate=sample_rate)

        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()

        sf.write("output.wav", audio, sample_rate)

        import sounddevice as sd
        sd.play(audio, sample_rate)
        sd.wait()

    except Exception as e:
        print(f"❌ Ошибка озвучки: {e}")
