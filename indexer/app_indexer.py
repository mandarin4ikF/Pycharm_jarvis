"""
indexer.py ― «умный» индексатор приложений для Agent Zero
=========================================================
🔍  Ищет .exe / .lnk / .py, но пропускает явный мусор ‑ uninstall, update, helper и т. д.
⚖️  Каждому файлу начисляется score; в индекс попадают только те, у кого score ≥ TRESHOLD.
📄  Итог сохраняется в app_index.json (читается assistant.py / listen.py).

Запуск
------
    python indexer.py                         # сканирует стандартные директории
    python indexer.py "D:/Games" "E:/Portable"  # + любые ваши пути

Зависимости
-----------
- pefile (опционально, для проверки цифровой подписи): `pip install pefile`
- indexer/aliases.py — словарь синонимов (нужно для бонусов по score)

"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import ctypes
import time
from typing import Dict, List

# --- внешняя необязательная зависимость --------------------------------------
try:
    import pefile  # проверка цифровой подписи
except ImportError:     # если не установлена — подпись просто не учитываем
    pefile = None

# импортируем словарь синонимов
import aliases
ALIASES = aliases.ALIASES



# ╔═══════════════════════════════════════╗
# ║           К О Н С Т А Н Т Ы           ║
# ╚═══════════════════════════════════════╝
SKIP_DIR_NAMES: set[str] = {
    ".venv", "venv", "env", ".git", "__pycache__", ".cache",
    "node_modules", "dist", "build", ".idea", ".vscode",
    "appdata", "temp", "packages"
}

TARGET_EXTENSIONS: tuple[str, ...] = (".exe", ".py", ".url")

DEFAULT_PATHS: list[pathlib.Path] = [
    pathlib.Path.home() / "Downloads",
    pathlib.Path.home() / "Desktop",
    pathlib.Path.home() / "Documents",
    pathlib.Path.home() / "AppData" / "Local" / "Programs",
    pathlib.Path("C:/Program Files"),
    pathlib.Path("C:/Program Files (x86)"),
    pathlib.Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Steam",
]

OUTPUT_FILE = pathlib.Path(__file__).with_name("app_index.json")

# --- эвристические правила ----------------------------------------------------
GOOD_MATCH_PARENTS = 10  # exe=имя_папки
GOOD_ALIAS_HIT     = 8   # имя совпало с ключом из ALIASES
BAD_STOPWORD       = -10 # uninstall / update …
BAD_DIRNAME        = -5  # installer / redist …
BAD_SIZE           = -10  # подозрительный размер

TRESHOLD = 3       # минимальный score, чтобы войти в индекс

STOPWORDS = {
    "uninstall", "update", "setup", "helper", "crash",
    "service", "patch", "install", "debug"
}
BAD_DIR_PARTS = {
    "update", "installer", "redist", "patcher",
    "resources", "bin", "debug", "x64", "x86"
}


# ╔═══════════════════════════════════════╗
# ║         П О Л Е З Н Ы Е  Ф-Ц И И      ║
# ╚═══════════════════════════════════════╝
def _sanitize_key(path: pathlib.Path) -> str:
    """Имя файла → нижний регистр, без пробелов."""
    return path.stem.lower().replace(" ", "")


def _resolve_windows_shortcut(lnk_path: str) -> str | None:
    """
    Возвращает целевой путь ярлыка (.lnk) или None, если не удалось.
    Работает только на Windows; на других ОС просто вернёт None.
    """
    if sys.platform != "win32":
        return None

    CLSID_ShellLink = ctypes.c_buffer(b'\x01\x14\x02\x00\x00\x00\x00\x00\xC0'
                                      b'\x00\x00\x00\x00\x00\x00F')
    IID_IShellLink  = ctypes.c_buffer(b'\xF9\x14\x02\x00\x00\x00\x00\x00\xC0'
                                      b'\x00\x00\x00\x00\x00\x00F')

    shell = ctypes.OleDLL('ole32').CoCreateInstance
    psl = ctypes.c_void_p()
    if shell(CLSID_ShellLink, None, 1, IID_IShellLink, ctypes.byref(psl)):
        return None

    lnk = ctypes.POINTER(ctypes.c_void_p)()
    if ctypes.cast(psl, ctypes.POINTER(ctypes.c_void_p * 5))[0][4](lnk_path, 0):
        return None

    buf = ctypes.create_unicode_buffer(260)
    if ctypes.cast(psl, ctypes.POINTER(ctypes.c_void_p * 21))[0][20](buf, 260, None, 0):
        return None
    return buf.value or None


def score_exe(path: pathlib.Path) -> int:
    """Оценивает файл по набору эвристик и возвращает итоговый score."""
    score = 0
    stem = path.stem.lower()

    # 1) exe = имя родительской папки
    if stem == path.parent.stem.lower().replace(" ", ""):
        score += GOOD_MATCH_PARENTS

    # 2) попадание в словарь ALIASES
    if stem in ALIASES:
        score += GOOD_ALIAS_HIT

    # 3) стоп‑слова в названии файла
    if any(w in stem for w in STOPWORDS):
        score += BAD_STOPWORD

    # 4) «плохие» части пути
    if any(part.lower() in BAD_DIR_PARTS for part in path.parts):
        score += BAD_DIRNAME

    # 5) подозрительный размер (<30 КБ или >1 ГБ)
    try:
        size_mb = path.stat().st_size / 1_048_576
        if size_mb < 3:
            score += BAD_SIZE
    except PermissionError:
        pass  # нет доступа → не трогаем
    
    # 6) не показывать те, что давно не открывал
    mtime = path.stat().st_mtime
    years_ago = (time.time() - mtime) / (30*24*3600)
    if years_ago > 1:
        score -= 3
    
    # 7) игры из стим
    if path.suffix.lower() == ".url" and "steam" in str(path).lower():
        score += 15

    return score


# ╔═══════════════════════════════════════╗
# ║          Г Л А В Н Ы Е  Ф‑Ц И И       ║
# ╚═══════════════════════════════════════╝
def scan_folders(start_paths: List[pathlib.Path]) -> Dict[str, str]:
    """
    Обходит все start_paths, применяет score_exe(), формирует словарь
    {ключ: полный_путь}.
    """
    results: Dict[str, str] = {}

    for base in start_paths:
        if not base.exists():
            continue
        print(f"🔍 Сканируем: {base}")

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_NAMES]

            for file in files:
                if not file.lower().endswith(TARGET_EXTENSIONS):
                    continue

                p = pathlib.Path(root) / file

                # разворачиваем ярлык .lnk
                if p.suffix.lower() == ".lnk":
                    target = _resolve_windows_shortcut(str(p))
                    if target and pathlib.Path(target).exists():
                        p = pathlib.Path(target)
                    else:
                        continue

                key = _sanitize_key(p)
                file_score = score_exe(p)

                # оставляем, если хороший score и .exe приоритетнее .py
                if file_score >= TRESHOLD and (
                    key not in results or p.suffix.lower() == ".exe"
                ):
                    results[key] = str(p)

    return results


def save_index(index: Dict[str, str], path: pathlib.Path = OUTPUT_FILE) -> None:
    """Записывает итоговый индекс в JSON."""
    path.write_text(json.dumps(index, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"💾 Индекс сохранён: {path}  ({len(index)} объектов)")


# ╔═══════════════════════════════════════╗
# ║               C L I                  ║
# ╚═══════════════════════════════════════╝
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сканирует директории и создаёт app_index.json с полезными программами."
    )
    parser.add_argument("extra", nargs="*", help="Дополнительные папки для сканирования")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    start_dirs = DEFAULT_PATHS + [pathlib.Path(p) for p in args.extra]
    start_dirs = [p.resolve() for p in start_dirs if p.exists()]

    if not start_dirs:
        print("❌ Ни одной валидной стартовой директории не найдено.")
        sys.exit(1)

    index = scan_folders(start_dirs)
    if not index:
        print("⚠️  Ни одного подходящего файла не найдено.")
        sys.exit(0)

    save_index(index)
