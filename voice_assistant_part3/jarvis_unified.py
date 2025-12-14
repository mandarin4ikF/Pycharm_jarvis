#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS Unified System - Complete Integration
Объединенная система голосового помощника с полной интеграцией всех компонентов
"""
import asyncio
import threading
import time
import queue
from typing import Optional
import webview  # Added for floating window

# Import all our components
from whisper_recognizer import recognize_from_microphone
from coqui_tts import speak
from ollama_client import ask_ollama
from web_server import start_web_server, update_state
from picovoice_wrapper import PicovoiceWakeWordListener
from emotion_integration import EmotionAnalyzer, get_emotional_prompt

class JARVISUnifiedSystem:
    """
    Unified JARVIS Voice Assistant with complete integration:
    Picovoice → Whisper → Emotion Analysis → Ollama → TTS + WebSocket Sync
    """
    
    def __init__(self):
        """Initialize all components"""
        print("🚀 Инициализация JARVIS Unified System...")
        
        # Core components
        self.emotion_analyzer = EmotionAnalyzer(enable_logging=True)
        self.wake_word_listener = None
        self.web_thread = None
        self.window = None  # For pywebview window
        
        # System state
        self.is_running = False
        self.is_processing = False
        
        # Communication
        self.event_queue = queue.Queue()
        
        print("✅ JARVIS Unified System инициализирован")
    
    def start_web_interface(self):
        """Start the web interface in a separate thread"""
        print("🌐 Запуск веб-интерфейса...")
        self.web_thread = threading.Thread(target=start_web_server, daemon=True)
        self.web_thread.start()
        time.sleep(2)  # Wait for server to start
        print("✅ Веб-интерфейс запущен на http://127.0.0.1:5000")
    
    def create_floating_window(self):
        """Create a floating window using pywebview"""
        print("🖼️ Создание плавающего окна...")
        try:
            self.window = webview.create_window(
                'JARVIS',  # Window title
                'http://127.0.0.1:5000',  # URL of our interface
                width=320,  # Width of the window
                height=600,  # Height of the window
                resizable=False,  # Disable resizing
                frameless=True,  # No window frame for a cleaner look
                on_top=True,  # Keep window on top of others
                hidden=True,  # Start hidden, show only when needed
                x=10,  # Position from left
                y=10   # Position from top
            )
            print("✅ Плавающее окно создано")
            return True
        except Exception as e:
            print(f"❌ Ошибка создания плавающего окна: {e}")
            return False
    
    def show_window(self):
        """Show the floating window"""
        if self.window:
            try:
                self.window.show()
                print("👁️ Плавающее окно показано")
            except Exception as e:
                print(f"❌ Ошибка показа окна: {e}")
    
    def hide_window(self):
        """Hide the floating window"""
        if self.window:
            try:
                self.window.hide()
                print("🙈 Плавающее окно скрыто")
            except Exception as e:
                print(f"❌ Ошибка скрытия окна: {e}")
    
    def start_wake_word_listener(self):
        """Start Picovoice wake word detection"""
        print("👂 Запуск детектора wake word...")
        
        def on_wake_word_detected(keyword, index):
            """Callback when wake word is detected"""
            print(f"🎯 Wake Word '{keyword}' обнаружено!")
            update_state('WAKE_WORD_LISTENING', f'Обнаружено: "{keyword}"', wake_word=keyword)
            
            # Show the floating window when wake word is detected
            self.show_window()
            
            # Put event in queue for main loop
            self.event_queue.put({
                'type': 'wake_word_detected',
                'keyword': keyword,
                'timestamp': time.time()
            })
        
        # Create and start wake word listener
        self.wake_word_listener = PicovoiceWakeWordListener(
            on_wake_word_detected=on_wake_word_detected
        )
        
        if self.wake_word_listener.start_listening():
            print("✅ Wake word listener активен")
            return True
        else:
            print("❌ Не удалось запустить wake word listener")
            return False
    
    async def process_voice_interaction(self):
        """Complete voice interaction pipeline"""
        if self.is_processing:
            print("⚠️ Уже обрабатываю запрос...")
            return
        
        self.is_processing = True
        
        try:
            # Step 1: Speech Recognition
            print("🎤 Начинаю распознавание речи...")
            update_state('LISTENING', 'Слушаю ваш запрос')
            
            user_text = recognize_from_microphone()
            
            if not user_text.strip():
                print("🔇 Речь не распознана")
                update_state('IDLE', 'Речь не распознана')
                self.hide_window()  # Hide window when done
                return
            
            print(f"🗣️ Распознано: '{user_text}'")
            
            # Step 2: Emotion Analysis
            print("🎭 Анализирую эмоцию...")
            emotion = await self.emotion_analyzer.analyze_text_emotion_async(user_text)
            
            emotion_context = ""
            if emotion:
                print(f"😊 Обнаружена эмоция: {emotion}")
                emotion_context = f" (эмоция: {emotion})"
            
            # Step 3: Generate Response with Emotional Context
            print("🧠 Генерирую ответ...")
            update_state('THINKING', f'Обдумываю ответ{emotion_context}')
            
            # Create emotionally-aware prompt
            base_prompt = "Ты — голосовой помощник JARVIS. Отвечай кратко и по делу на русском языке. Учитывай эмоциональное состояние пользователя."
            
            if emotion:
                enhanced_prompt = get_emotional_prompt(base_prompt, user_text)
            else:
                enhanced_prompt = f"{base_prompt}\n\nВопрос: {user_text}"
            
            response = ask_ollama(enhanced_prompt)
            print(f"🤖 JARVIS: {response}")
            
            # Step 4: Text-to-Speech
            print("🗣️ Озвучиваю ответ...")
            update_state('SPEAKING', f'Отвечаю{emotion_context}')
            
            speak(response)
            
            # Step 5: Return to ready state
            time.sleep(0.5)
            update_state('WAKE_WORD_LISTENING', 'Готов к новым командам')
            self.hide_window()  # Hide window when done
            
        except Exception as e:
            print(f"❌ Ошибка в пайплайне: {e}")
            update_state('ERROR', f'Ошибка: {e}')
            self.hide_window()  # Hide window on error
        finally:
            self.is_processing = False
    
    async def main_loop(self):
        """Main event processing loop"""
        print("🔄 Запуск основного цикла...")
        update_state('WAKE_WORD_LISTENING', 'Ожидаю команды...')
        
        while self.is_running:
            try:
                # Check for wake word events
                if self.wake_word_listener and self.wake_word_listener.has_events():
                    event = self.wake_word_listener.get_event()
                    if event and event['type'] == 'wake_word_detected':
                        print(f"📢 Обрабатываю wake word event: {event['keyword']}")
                        await self.process_voice_interaction()
                
                # Small delay to prevent high CPU usage
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Ошибка в основном цикле: {e}")
                await asyncio.sleep(1)
    
    async def start_async(self):
        """Start the complete system asynchronously"""
        print("🟢 Запуск JARVIS Unified System...")
        
        # Start web interface
        self.start_web_interface()
        
        # Create floating window
        if not self.create_floating_window():
            print("⚠️ Продолжаю без плавающего окна")
        
        # Start wake word detection
        if not self.start_wake_word_listener():
            print("⚠️ Продолжаю без wake word detection")
        
        # Set running flag
        self.is_running = True
        update_state('WAKE_WORD_LISTENING', 'Система готова к работе')
        
        print("✅ Все компоненты запущены!")
        print("🎤 Скажите 'JARVIS' или 'COMPUTER' для активации")
        print("🌐 Веб-интерфейс: http://127.0.0.1:5000")
        print("⏹️ Нажмите Ctrl+C для остановки")
        
        # Run main event loop
        await self.main_loop()
    
    def start(self):
        """Start the system (synchronous wrapper)"""
        try:
            # First create the window and web interface
            self.start_web_interface()
            self.create_floating_window()
            
            # Start wake word detection
            self.start_wake_word_listener()
            
            # Set running flag
            self.is_running = True
            update_state('WAKE_WORD_LISTENING', 'Система готова к работе')
            
            print("✅ Все компоненты запущены!")
            print("🎤 Скажите 'JARVIS' или 'COMPUTER' для активации")
            print("⏹️ Нажмите Ctrl+C для остановки")
            
            # Start the webview GUI (this will block and run the main loop)
            webview.start(self.gui_loop, debug=False)
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал остановки...")
            self.stop()
        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            self.stop()
    
    def gui_loop(self):
        """GUI loop that runs in the webview thread"""
        # This runs in the GUI thread and can interact with the window
        print("🔄 Запуск GUI цикла...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.main_loop())
    
    def stop(self):
        """Stop all components gracefully"""
        print("🛑 Остановка JARVIS Unified System...")
        
        self.is_running = False
        
        # Stop wake word listener
        if self.wake_word_listener:
            self.wake_word_listener.stop_listening()
        
        # Update final state
        update_state('IDLE', 'Система остановлена')
        
        print("✅ JARVIS Unified System остановлен")
    
    def get_system_stats(self):
        """Get comprehensive system statistics"""
        stats = {
            'is_running': self.is_running,
            'is_processing': self.is_processing,
            'wake_word_active': self.wake_word_listener is not None and self.wake_word_listener.is_listening,
            'web_interface_active': self.web_thread is not None and self.web_thread.is_alive(),
            'emotion_stats': self.emotion_analyzer.get_stats()
        }
        return stats

# Convenience function for easy startup
def start_jarvis():
    """Start JARVIS Unified System"""
    jarvis = JARVISUnifiedSystem()
    jarvis.start()

# Demo/Test mode
async def demo_mode():
    """Run system in demo mode without Picovoice for testing"""
    print("🎬 JARVIS Demo Mode (без Picovoice)")
    
    jarvis = JARVISUnifiedSystem()
    jarvis.start_web_interface()
    jarvis.create_floating_window()
    
    # Simulate wake word detection and processing
    demo_phrases = [
        "Как дела? Я очень рад сегодня!",
        "Мне грустно... Помоги мне",
        "Боюсь, что не справлюсь с задачей",
        "Вау! Это просто невероятно!"
    ]
    
    update_state('WAKE_WORD_LISTENING', 'Demo режим активен')
    await asyncio.sleep(2)
    
    for phrase in demo_phrases:
        print(f"\n🎭 Demo: '{phrase}'")
        
        # Show window for demo
        jarvis.show_window()
        
        # Simulate emotion analysis
        emotion = jarvis.emotion_analyzer.analyze_text_emotion(phrase)
        
        # Simulate thinking
        update_state('THINKING', f'Обдумываю ответ (эмоция: {emotion})')
        await asyncio.sleep(2)
        
        # Simulate response
        update_state('SPEAKING', 'Отвечаю эмоционально')
        await asyncio.sleep(3)
        
        # Hide window after demo
        jarvis.hide_window()
        
        update_state('WAKE_WORD_LISTENING', 'Готов к следующей команде')
        await asyncio.sleep(1)
    
    print("✅ Demo завершено")
    return jarvis

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # Run demo mode
        asyncio.run(demo_mode())
    else:
        # Run full system
        start_jarvis()