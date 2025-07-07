from pathlib import Path
p = Path(r"C:\Users\Огузок\Downloads\Yandex.exe")
print(p.exists(), p.stat().st_size)
