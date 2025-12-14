#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emotion Analysis Integration for JARVIS Voice Assistant
Интеграция анализа эмоций в основной пайплайн голосового помощника
"""
import asyncio
import time
from typing import Optional, Dict, Any

# Try to import real emotion analyzer, fallback to mock if not available
try:
    from emotion import get_emotion
    print("🎭 Using real emotion analyzer")
except ImportError:
    from emotion_mock import get_emotion
    print("🎭 Using mock emotion analyzer (install aniemore for real analysis)")

from web_server import update_state

class EmotionAnalyzer:
    """
    Wrapper для анализа эмоций с интеграцией в систему состояний
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        Инициализация анализатора эмоций
        
        Args:
            enable_logging: Включить логирование процесса анализа
        """
        self.enable_logging = enable_logging
        self.last_emotion = None
        self.emotion_history = []
        self.max_history = 10
        
        # Mapping эмоций на русский язык для интерфейса
        self.emotion_mapping = {
            'joy': 'радость',
            'sadness': 'грусть', 
            'anger': 'гнев',
            'fear': 'страх',
            'surprise': 'удивление',
            'disgust': 'отвращение',
            'neutral': 'спокойствие'
        }
        
        if self.enable_logging:
            print("🎭 Emotion Analyzer инициализирован")
    
    def _log(self, message: str):
        """Логирование с проверкой флага"""
        if self.enable_logging:
            print(f"🎭 {message}")
    
    def analyze_text_emotion(self, text: str, update_ui: bool = True) -> Optional[str]:
        """
        Синхронный анализ эмоции в тексте
        
        Args:
            text: Текст для анализа
            update_ui: Обновлять ли состояние в UI
            
        Returns:
            str: Определенная эмоция на русском языке или None при ошибке
        """
        if not text or not text.strip():
            return None
        
        try:
            if update_ui:
                update_state('EMOTION_ANALYZING', 'Анализирую эмоцию в тексте')
            
            self._log(f"Анализирую текст: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Вызываем оригинальную функцию анализа эмоций
            start_time = time.time()
            raw_emotion = get_emotion(text)
            analysis_time = time.time() - start_time
            
            if raw_emotion:
                # Преобразуем в русский язык
                emotion_ru = self.emotion_mapping.get(raw_emotion.lower(), raw_emotion)
                
                # Сохраняем в истории
                self.last_emotion = emotion_ru
                self.emotion_history.append({
                    'text': text,
                    'emotion': emotion_ru,
                    'raw_emotion': raw_emotion,
                    'timestamp': time.time(),
                    'analysis_time': analysis_time
                })
                
                # Ограничиваем размер истории
                if len(self.emotion_history) > self.max_history:
                    self.emotion_history.pop(0)
                
                self._log(f"Эмоция определена: {emotion_ru} ({raw_emotion}) за {analysis_time:.2f}с")
                
                if update_ui:
                    update_state('EMOTION_ANALYZING', f'Обнаружена эмоция: {emotion_ru}', emotion=emotion_ru)
                
                return emotion_ru
            else:
                self._log("Эмоция не определена")
                if update_ui:
                    update_state('EMOTION_ANALYZING', 'Эмоция не определена')
                return None
                
        except Exception as e:
            self._log(f"Ошибка анализа эмоций: {e}")
            if update_ui:
                update_state('ERROR', f'Ошибка анализа эмоций: {e}')
            return None
    
    async def analyze_text_emotion_async(self, text: str, update_ui: bool = True) -> Optional[str]:
        """
        Асинхронный анализ эмоции в тексте
        
        Args:
            text: Текст для анализа
            update_ui: Обновлять ли состояние в UI
            
        Returns:
            str: Определенная эмоция на русском языке или None при ошибке
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze_text_emotion, text, update_ui)
    
    def get_emotion_context(self, include_history: bool = False) -> Dict[str, Any]:
        """
        Получает контекст текущей эмоции для передачи в LLM
        
        Args:
            include_history: Включать ли историю эмоций
            
        Returns:
            dict: Контекст эмоции для использования в промпте
        """
        context = {
            'current_emotion': self.last_emotion,
            'has_emotion': self.last_emotion is not None
        }
        
        if include_history and self.emotion_history:
            recent_emotions = [entry['emotion'] for entry in self.emotion_history[-3:]]
            context['recent_emotions'] = recent_emotions
            context['emotion_trend'] = self._analyze_emotion_trend(recent_emotions)
        
        return context
    
    def _analyze_emotion_trend(self, emotions: list) -> str:
        """Анализирует тренд эмоций"""
        if not emotions:
            return "нейтральный"
        
        if len(emotions) == 1:
            return emotions[0]
        
        # Простой анализ: если последние эмоции одинаковые
        if len(set(emotions[-2:])) == 1:
            return f"стабильно {emotions[-1]}"
        
        # Если эмоции разные
        return f"переменчивое (от {emotions[0]} к {emotions[-1]})"
    
    def create_emotional_prompt(self, base_prompt: str, user_text: str) -> str:
        """
        Создает эмоционально-адаптированный промпт для LLM
        
        Args:
            base_prompt: Базовый промпт системы
            user_text: Текст пользователя
            
        Returns:
            str: Модифицированный промпт с учетом эмоции
        """
        emotion_context = self.get_emotion_context(include_history=True)
        
        if not emotion_context['has_emotion']:
            return f"{base_prompt}\n\nВопрос: {user_text}"
        
        emotion = emotion_context['current_emotion']
        
        # Эмоциональные модификаторы для разных эмоций
        emotion_modifiers = {
            'радость': "Пользователь в хорошем настроении. Отвечай позитивно и поддерживающе.",
            'грусть': "Пользователь грустит. Будь деликатным, сопереживающим и поддерживающим.",
            'гнев': "Пользователь раздражен или зол. Отвечай спокойно и стараясь успокоить.",
            'страх': "Пользователь обеспокоен или напуган. Будь утешающим и обнадеживающим.",
            'удивление': "Пользователь удивлен. Можешь быть более экспрессивным в ответе.",
            'отвращение': "Пользователь выражает неприятие. Будь тактичным и понимающим.",
            'спокойствие': "Пользователь в спокойном состоянии. Отвечай нейтрально и информативно."
        }
        
        modifier = emotion_modifiers.get(emotion, "")
        
        enhanced_prompt = f"""{base_prompt}

Эмоциональный контекст: Определена эмоция пользователя - {emotion}. {modifier}

Вопрос: {user_text}"""
        
        return enhanced_prompt
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику работы анализатора"""
        return {
            'last_emotion': self.last_emotion,
            'total_analyses': len(self.emotion_history),
            'emotion_distribution': self._get_emotion_distribution(),
            'average_analysis_time': self._get_average_analysis_time()
        }
    
    def _get_emotion_distribution(self) -> Dict[str, int]:
        """Подсчитывает распределение эмоций"""
        distribution = {}
        for entry in self.emotion_history:
            emotion = entry['emotion']
            distribution[emotion] = distribution.get(emotion, 0) + 1
        return distribution
    
    def _get_average_analysis_time(self) -> float:
        """Вычисляет среднее время анализа"""
        if not self.emotion_history:
            return 0.0
        
        total_time = sum(entry['analysis_time'] for entry in self.emotion_history)
        return total_time / len(self.emotion_history)

# Глобальный экземпляр для использования в приложении
emotion_analyzer = EmotionAnalyzer()

# Convenience функции для легкого использования
def analyze_emotion(text: str, update_ui: bool = True) -> Optional[str]:
    """Convenience функция для анализа эмоций"""
    return emotion_analyzer.analyze_text_emotion(text, update_ui)

async def analyze_emotion_async(text: str, update_ui: bool = True) -> Optional[str]:
    """Convenience функция для асинхронного анализа эмоций"""
    return await emotion_analyzer.analyze_text_emotion_async(text, update_ui)

def get_emotional_prompt(base_prompt: str, user_text: str) -> str:
    """Convenience функция для создания эмоционального промпта"""
    return emotion_analyzer.create_emotional_prompt(base_prompt, user_text)

# Тестирование
if __name__ == "__main__":
    import threading
    from web_server import start_web_server
    
    # Запускаем веб-сервер для тестирования
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    time.sleep(2)
    
    print("🎭 Тестирование Emotion Analyzer")
    
    test_texts = [
        "Я так рад, что все получилось!",
        "Мне очень грустно и одиноко...",
        "Это просто ужасно! Я в ярости!",
        "Боюсь, что ничего не получится",
        "Вау, не ожидал такого поворота!",
        "Как дела? Что нового?"
    ]
    
    for text in test_texts:
        print(f"\n--- Тестирую: '{text}' ---")
        emotion = analyze_emotion(text)
        
        if emotion:
            context = emotion_analyzer.get_emotion_context(include_history=True)
            print(f"Контекст: {context}")
            
            # Тест создания эмоционального промпта
            enhanced_prompt = get_emotional_prompt(
                "Ты голосовой помощник. Отвечай кратко и по делу.", 
                text
            )
            print(f"Эмоциональный промпт:\n{enhanced_prompt[:200]}...")
        
        time.sleep(1)
    
    print(f"\n📊 Статистика: {emotion_analyzer.get_stats()}")
    print("✅ Тестирование завершено")