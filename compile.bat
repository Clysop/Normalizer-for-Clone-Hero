pyinstaller --noconfirm .\src\Normalizer.py
rmdir /s /q build
rmdir /s /q src\__pycache__
del Normalizer.spec