import torch
from aniemore.recognizers.text import TextRecognizer
from aniemore.models import HuggingFaceModel

# Инициализация модели для распознавания эмоций
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = HuggingFaceModel.Text.Bert_Tiny2
text_recognizer = TextRecognizer(model=model, device=device)

def get_emotion(text):
    """
    Возвращает эмоцию текста.
    """
    # Возвращаем один наиболее вероятный лейбл (эмоцию)
    try:
        emotion = text_recognizer.recognize(text, return_single_label=True)
        return emotion
    except Exception as e:
        print(f"Ошибка распознавания эмоции: {e}")
        return None

if __name__ == "__main__":
    # Для проверки запускаем тест
    test_text = "это работает? :("
    print(f"Текст: {test_text}")
    print(f"Эмоция: {get_emotion(test_text)}")
