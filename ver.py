import json, random
from playwright.sync_api import sync_playwright

def reproducir(page, url, r):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        # ESTO es lo que registra la view: que el video arranque a reproducir
        page.wait_for_timeout(r.randint(7000, 15000))
        if r.random() < 0.35:
            page.mouse.wheel(0, r.randint(200, 700))
            page.wait_for_timeout(r.randint(1500, 4000))
        print("ok:", url)
    except Exception as e:
        print("fallo:", url, e)

def main():
    targets = json.load(open("targets.json", encoding="utf-8"))
    r = random.Random(42)

    with sync_playwright() as pw:
        b = pw.chromium.launch(
            headless=True,                      # False si querés verlo con tus ojos
            args=[
                "--autoplay-policy=no-user-gesture-required",   # CLAVE
                "--mute-audio",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        ctx = b.new_context(
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            viewport={"width": 1366, "height": 768},
        )
        page = ctx.new_page()
        for t in targets:
            reproducir(page, t["url"], r)
        b.close()

if __name__ == "__main__":
    main()
