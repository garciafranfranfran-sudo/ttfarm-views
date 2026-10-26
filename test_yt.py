import os
import time
import csv
import random
import threading
from queue import Queue
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.youtube.com/shorts/e1RHntfsUww"

SHARD  = int(os.environ.get("SHARD", "0"))
SHARDS = int(os.environ.get("SHARDS", "1"))
N      = int(os.environ.get("N", "100"))

WORKERS = int(os.environ.get("WORKERS", "4"))
LOG = Path("views.csv")
lock = threading.Lock()

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['es-AR', 'es']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
"""

def bind_video(pg):
    """Marca el video que realmente reproduce y le saca el loop."""
    return pg.evaluate("""() => {
        const vs = Array.from(document.querySelectorAll('video')).filter(v => v.videoWidth > 0);
        if (!vs.length) return null;
        const v = vs.find(x => !x.paused && x.currentTime > 0) || vs[0];
        document.querySelectorAll('video').forEach(x => x.removeAttribute('data-ttfarm'));
        v.setAttribute('data-ttfarm', '1');
        v.loop = false;
        if (v.paused) { v.muted = true; v.play().catch(() => {}); }
        return { t: v.currentTime, dur: v.duration };
    }""")

def wait_until_playing(pg, timeout_ms=90000):
    end = time.time() + timeout_ms / 1000
    while time.time() < end:
        st = bind_video(pg)
        if st and st["t"] > 0.5:
            return st
        pg.wait_for_timeout(500)
    raise RuntimeError("el video nunca arrancó")

def run_target(pg, idx, url, n_shots=1):
    pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    info = wait_until_playing(pg)
    dur = info.get("dur") or 0
    step = max(2.0, min(dur / (n_shots + 1), 8.0)) if dur and dur > 0 else 3.0
    for i in range(n_shots):
        pg.wait_for_timeout(int(step * 1000))
        pg.locator("video[data-ttfarm]").screenshot(path=f"shots/{idx:05d}.png")

def log_row(row):
    with lock:
        new = not LOG.exists()
        with LOG.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["ts", "worker", "idx", "url", "ok", "nota"])
            w.writerow(row)

def worker(n, q):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=[
            "--autoplay-policy=no-user-gesture-required",
            "--mute-audio",
            "--disable-blink-features=AutomationControlled",
        ])
        while True:
            try:
                idx, url = q.get_nowait()
            except Exception:
                break
            try:
                ctx = b.new_context(
                    user_agent=random.choice(UAS),
                    locale="es-AR",
                    timezone_id="America/Argentina/Buenos_Aires",
                    viewport={"width": random.choice([1366, 1440, 1536]),
                              "height": random.choice([768, 900, 864])},
                )
                ctx.add_init_script(STEALTH)
                pg = ctx.new_page()
                run_target(pg, idx, url, n_shots=1)
                log_row([time.time(), n, idx, url, 1, ""])
                ctx.close()
            except Exception as e:
                log_row([time.time(), n, idx, url, 0, str(e)[:120]])
            finally:
                q.task_done()
        b.close()

def main():
    Path("shots").mkdir(exist_ok=True)
    done = set()
    if LOG.exists():
        with LOG.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["ok"] == "1":
                    done.add(int(r["idx"]))
    q = Queue()
    for i in range(N):
        if i % SHARDS == SHARD and i not in done:
            q.put((i, URL))
    ts = [threading.Thread(target=worker, args=(i, q)) for i in range(WORKERS)]
    [t.start() for t in ts]
    [t.join() for t in ts]

if __name__ == "__main__":
    main()
