# ttfarm-views

Bot de views con Playwright. Abre cada URL de `targets.json` en Chromium headless
y simula reproducción para registrar la view.

## Uso

pip install -r requirements.txt
python -m playwright install chromium
python ver.py

## targets.json

[{"plataforma": "tiktok", "url": "https://..."}]
