import torch
import soundfile as sf
import os

# Выбираем устройство
use_cuda = torch.cuda.is_available()
device = torch.device('cuda' if use_cuda else 'cpu')
print(f"🖥 Используем устройство: {device}")

# Путь к модели
model_path = os.path.join(os.path.dirname(__file__), 'v4_ru.pt')

# Загружаем модель
imp = torch.package.PackageImporter(model_path)
model = imp.load_pickle("tts_models", "model")
model.to(device)

# Текст и параметры
text = "Сейчас я говорю через видеокарту, если она доступна."
sample_rate = 48000

# Синтез речи
with torch.no_grad():
    audio = model.apply_tts(text=text, sample_rate=sample_rate)

# Перевод аудио на CPU (если оно на GPU)
if isinstance(audio, torch.Tensor):
    audio = audio.cpu().numpy()

# Сохраняем в WAV
sf.write("output.wav", audio, sample_rate)

print("✅ Готово. Файл 'output.wav' создан.")