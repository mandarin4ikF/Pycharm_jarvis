import logging
from typing import Tuple
from RestrictedPython import compile_restricted, safe_globals
from io import StringIO
import sys


logger = logging.getLogger(__name__)


class CodeSandbox:
   """Безопасная песочница для выполнения Python-кода с использованием RestrictedPython."""
   def __init__(self):
       self.safe_globals = safe_globals.copy()
       # RestrictedPython не позволяет использовать print напрямую.
       # Мы предоставляем безопасную версию через _print_ и перехватываем ее вывод.
       self.safe_globals['_print_'] = self._safe_print_utility


   def _safe_print_utility(self, *args, **kwargs):
       """Перехватывает вывод от print для возврата пользователю."""
       # Эта функция будет доступна внутри песочницы как _print_()
       # Мы перенаправляем ее вывод в sys.stdout, который мы перехватываем.
       print(*args, **kwargs)


   def run(self, code: str) -> Tuple[str, str, bool]:
       """
       Компилирует и выполняет код в безопасной среде.
       Блокирует опасные операции, такие как импорт 'os' или доступ к файлам.
       """
       stdout_capture = StringIO()
       stderr_capture = StringIO()
       success = True
      
       # Заменяем print на нашу безопасную версию
       safe_code = code.replace("print", "_print_")


       try:
           logger.info("Компиляция кода в безопасном режиме...")
           byte_code = compile_restricted(safe_code, '<inline code>', 'exec')
          
           # Перенаправляем stdout и stderr, чтобы перехватить вывод
           original_stdout, original_stderr = sys.stdout, sys.stderr
           sys.stdout, sys.stderr = stdout_capture, stderr_capture
          
           logger.info("Выполнение скомпилированного безопасного кода...")
           exec(byte_code, self.safe_globals, None)


       except Exception as e:
           logger.error(f"Ошибка выполнения кода в песочнице: {e}")
           stderr_capture.write(f"Ошибка безопасности или выполнения: {e}\n")
           success = False
       finally:
           # Всегда восстанавливаем стандартные потоки вывода
           sys.stdout, sys.stderr = original_stdout, original_stderr


       stdout = stdout_capture.getvalue()
       stderr = stderr_capture.getvalue()
      
       logger.info(f"Выполнение завершено. Success: {success}, Stdout: '{stdout.strip()}', Stderr: '{stderr.strip()}'")