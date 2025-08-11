from aniemore.recognizers.emotion_recognizer import EmotionRecognizer

model = EmotionRecognizer()
result = model.predict("Я очень рад!")
print(result)
