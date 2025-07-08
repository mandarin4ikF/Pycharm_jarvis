# ╔═══════════════════════════════════════╗
# ║       З А Г Р У З К А   Ф А Й Л О В    ║
# ╚═══════════════════════════════════════╝
import json
import ast
import os
import openai
from dotenv import load_dotenv

# Абсолютные пути к файлам ВНУТРИ indexer/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_INDEX_PATH = os.path.join(BASE_DIR, 'app_index.json')
ALIASES_PATH = os.path.join(BASE_DIR, 'aliases.py')

# ╔═══════════════════════════════════════╗
# ║          Г Л А В Н Ы Е  Ф‑Ц И И       ║
# ╚═══════════════════════════════════════╝

def load_app_index(path):
    """Загрузка файла app_index.json"""
    if not os.path.exists(path):
        print(f"❌ Не найден файл app_index.json по пути: {path}")
        exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_aliases(path):
    """Загрузка aliases.py и извлечение словаря ALIASES через AST"""
    if not os.path.exists(path):
        print(f"❌ Не найден файл aliases.py по пути: {path}")
        exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == 'ALIASES':
            return ast.literal_eval(node.value), source
    raise ValueError('ALIASES dict not found')


def get_russian_synonyms_from_gpt(key):
    """Используем OpenAI для генерации синонимов команды на русском"""
    prompt = f"""
    Ты — голосовой помощник на русском языке, задача которого — помочь понять Vosk, как пользователь может произнести название программы на русском в разговорной речи.

    Тебе даётся ключ — название программы (например, "telegram", "chrome", "vscode"), которое совпадает с официальным именем программы в системе.

    Твоя задача — сгенерировать 5–10 реальных русскоязычных сокращений, жаргонизмовб, траскрипцию с англиского на русский или распространённых вариантов произношения этого слова, которые часто используют люди, говоря голосом. Но не уменшительно ласкательно

    Ответ должен быть строго в формате JSON-массива строк.
    Никаких пояснений, никаких комментариев — только JSON.

    Примеры:

    Вход: "telegram"  
    Выход: ["телега", "тг", "телеграм", "телеграмм", "telegram"]

    Вход: "chrome"  
    Выход: ["гугл", "хром", "браузер", "chrome"]

    Вход: "vscode"  
    Выход: ["код", "вскод", "вскоде", "видео код", "vs code"]

    ---

    Начинаем. Вот ключ: "{key}"  
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        print(f"Ошибка при обращении к OpenAI для '{key}':", e)
        return [key]


def update_aliases(app_index, aliases):
    """Добавление новых ключей из app_index в ALIASES, без дублирования синонимов,
    с ограничением максимум 15 синонимов в списке"""
    updated = False
    MAX_SYNONYMS = 15

    for key in app_index:
        synonyms = get_russian_synonyms_from_gpt(key)

        if key in aliases:
            # Объединяем старые и новые синонимы вместе с ключом
            combined = set(aliases[key]) | set(synonyms) | {key}
        else:
            combined = set(synonyms) | {key}

        # Ограничиваем до MAX_SYNONYMS (сохраняем уникальные)
        limited = list(combined)[:MAX_SYNONYMS]

        if key not in aliases or set(limited) != set(aliases.get(key, [])):
            aliases[key] = limited
            updated = True

    return updated



def write_aliases(path, original_source, aliases_dict):
    """Перезапись aliases.py с обновленным ALIASES"""
    new_dict = 'ALIASES = ' + json.dumps(aliases_dict, ensure_ascii=False, indent=4)
    lines = original_source.splitlines()
    out_lines = []
    in_aliases = False
    for line in lines:
        if line.startswith('ALIASES'):
            in_aliases = True
            out_lines.append(new_dict)
        elif in_aliases:
            if line.strip().startswith('#') or line.strip() == '':
                continue
            if not line.startswith(' '):
                in_aliases = False
                out_lines.append(line)
        else:
            out_lines.append(line)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))


# ╔═══════════════════════════════════════╗
# ║            Т О Ч К А  В Х О Д А       ║
# ╚═══════════════════════════════════════╝
if __name__ == '__main__':
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    app_index = load_app_index(APP_INDEX_PATH)
    aliases, src = load_aliases(ALIASES_PATH)
    if update_aliases(app_index, aliases):
        write_aliases(ALIASES_PATH, src, aliases)
        print('✅ aliases.py обновлён.')
    else:
        print('ℹ️ Новых программ для добавления нет.')
