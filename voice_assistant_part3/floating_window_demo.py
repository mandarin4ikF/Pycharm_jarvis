#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo of Floating Window Interface for JARVIS
Демонстрация плавающего окна для JARVIS
"""

import webview
import threading
import time
from web_server import start_web_server, update_state

def create_floating_window():
    """Create and configure the floating window"""
    # Start the web server in a separate thread
    print("🌐 Starting web server...")
    server_thread = threading.Thread(target=start_web_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Give the server time to start
    
    # Create the floating window
    print("🖼️ Creating floating window...")
    window = webview.create_window(
        'JARVIS Assistant',  # Window title
        'http://127.0.0.1:5000',  # URL to load
        width=320,               # Window width
        height=600,              # Window height
        resizable=False,         # Disable resizing
        frameless=True,          # No window frame
        on_top=True,             # Keep window on top
        hidden=False,            # Show window immediately for demo
        x=100,                   # X position
        y=100                    # Y position
    )
    
    print("✅ Floating window is ready!")
    print("👉 The window should now be visible on your screen")
    print("⏹️ Close the window or press Ctrl+C to exit")
    
    # Start the webview GUI
    webview.start(debug=False)

def demo_states():
    """Demo the different states of the interface"""
    states = [
        ('LOADING', 'Инициализация систем'),
        ('WAKE_WORD_LISTENING', 'Скажите "JARVIS"'),
        ('LISTENING', 'Слушаю ваш запрос'),
        ('THINKING', 'Обрабатываю информацию'),
        ('SPEAKING', 'Формирую ответ'),
        ('IDLE', 'Готов к работе')
    ]
    
    for status, message in states:
        print(f"🔄 Switching to state: {status}")
        update_state(status, message)
        time.sleep(3)
    
    print("✅ Demo completed")

if __name__ == "__main__":
    # Run the demo in a separate thread so we can show state changes
    demo_thread = threading.Thread(target=demo_states, daemon=True)
    demo_thread.start()
    
    # Create and show the floating window
    create_floating_window()