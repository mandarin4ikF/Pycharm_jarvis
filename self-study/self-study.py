# -*- coding: utf-8 -*-
import os
import sys
import requests
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()


class AIAssistant:
    def __init__(self):
        """Инициализация ассистента с автоматическим определением версии"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.pycharm_path = os.getenv("PYCHARM_PATH")
        self.version = self.detect_current_version()

    def detect_current_version(self) -> int:
        """Автоматически определяет текущую версию на основе файлов"""
        max_version = 1
        for file in os.listdir('..'):
            if file.startswith('assistant_v') and file.endswith('.py'):
                try:
                    ver = int(file.split('_v')[1].split('.py')[0])
                    if ver > max_version:
                        max_version = ver
                except ValueError:
                    continue
        return max_version

    def ask_ai(self, prompt: str, max_retries=3) -> str:
        """Улучшенный запрос к API с повторными попытками"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7
                    },
                    timeout=30  # Увеличенный таймаут
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    return "Ошибка: превышено время ожидания сервера"
                time.sleep(5)  # Пауза между попытками
            except requests.exceptions.RequestException as e:
                return f"Ошибка: {str(e)}"
        return "Не удалось получить ответ от API"

    def self_upgrade(self, instruction: str) -> str:
        """Создание новой версии с автоматической нумерацией"""
        with open(__file__, 'r', encoding='utf-8') as f:
            current_code = f.read()

        prompt = (f"Улучши этот код Python строго соблюдая требования:\n"
                  f"1. Инструкция: {instruction}\n"
                  f"2. Сохрани все существующие функции\n"
                  f"3. Добавь номер версии в название нового файла\n\n"
                  f"{current_code}")

        new_code = self.ask_ai(prompt)
        if new_code.startswith("Ошибка"):
            print(new_code)
            return None

        self.version += 1
        new_file = f"self-study_v{self.version}.py"

        with open(new_file, 'w', encoding='utf-8') as f:
            f.write(new_code)

        print(f"✅ Создана версия v{self.version}")
        return new_file

    def download_file_from_url(self, url: str, save_path: str) -> bool:
        """Загрузка файла с улучшенной обработкой ошибок"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        except requests.exceptions.RequestException as e:
            print(f"Ошибка загрузки: {e}")
            return False

    def delete_file(self, file_path: str) -> bool:
        """Безопасное удаление файла"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Ошибка удаления: {e}")
            return False


def main():
    assistant = AIAssistant()
    print(f"🤖 Ассистент v{assistant.version}")
    print("Команды: 'улучшить [инструкция]', 'выход'")

    while True:
        command = input("\n> ").strip().lower()

        if command == "выход":
            print("Завершение работы")
            break

        elif command.startswith("улучшить "):
            instruction = command[9:].strip()
            if not instruction:
                print("Укажите инструкцию для улучшения")
                continue

            new_file = assistant.self_upgrade(instruction)
            if new_file:
                try:
                    subprocess.Popen([sys.executable, new_file])
                    print(f"🚀 Запускаю {new_file}...")
                    break
                except Exception as e:
                    print(f"Ошибка запуска: {e}")
        else:
            print("Некорректная команда")


if __name__ == "__main__":
    main()