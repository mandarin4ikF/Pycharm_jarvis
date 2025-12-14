#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Emotion Analyzer for testing without aniemore dependency
"""
import re
import random

def get_emotion(text):
    """
    Mock функция для анализа эмоций на основе ключевых слов
    Заменяет aniemore до установки библиотеки
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Словари ключевых слов для разных эмоций
    emotion_keywords = {
        'joy': ['рад', 'радость', 'счастлив', 'весел', 'отлично', 'супер', 'класс', 
                'здорово', 'прекрасно', 'замечательно', 'получилось', '!', '😊', '😄'],
        'sadness': ['грустно', 'грусть', 'печально', 'одиноко', 'плохо', 'ужасно',
                   'тоскливо', 'слез', 'расстроен', 'печаль', '😢', '😭'],
        'anger': ['злой', 'гнев', 'ярость', 'бесит', 'раздражает', 'ненавижу',
                 'дурак', 'идиот', 'достал', 'надоел', 'гневный', '😡', '😠'],
        'fear': ['боюсь', 'страх', 'пугает', 'тревожно', 'переживаю', 'опасно',
                'боязнь', 'испуган', 'волнуюсь', 'нервничаю', '😨', '😰'],
        'surprise': ['неожиданно', 'удивлен', 'вау', 'ого', 'ничего себе', 'сюрприз',
                    'поразительно', 'невероятно', '!', 'о боже', '😲', '😮'],
        'disgust': ['отвратительно', 'противно', 'гадко', 'фу', 'тошнит', 'мерзко',
                   'ужас', 'кошмар', '🤢', '🤮'],
        'neutral': ['нормально', 'обычно', 'ничего особенного', 'как всегда', 'окей']
    }
    
    # Подсчитываем совпадения для каждой эмоции
    emotion_scores = {}
    
    for emotion, keywords in emotion_keywords.items():
        score = 0
        for keyword in keywords:
            # Учитываем количество вхождений ключевого слова
            if keyword in text_lower:
                score += text_lower.count(keyword)
        emotion_scores[emotion] = score
    
    # Находим эмоцию с наибольшим счетом
    max_score = max(emotion_scores.values())
    
    if max_score == 0:
        return 'neutral'  # Если ничего не найдено, считаем нейтральным
    
    # Возвращаем эмоцию с наибольшим счетом
    for emotion, score in emotion_scores.items():
        if score == max_score:
            return emotion
    
    return 'neutral'

if __name__ == "__main__":
    # Тестирование mock функции
    test_texts = [
        "Я так рад, что все получилось!",
        "Мне очень грустно и одиноко...", 
        "Это просто ужасно! Я в ярости!",
        "Боюсь, что ничего не получится",
        "Вау, не ожидал такого поворота!",
        "Как дела? Что нового?"
    ]
    
    for text in test_texts:
        emotion = get_emotion(text)
        print(f"'{text}' -> {emotion}")