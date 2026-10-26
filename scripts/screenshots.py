"""Capture README screenshots of the app at its default settings.

Usage: python scripts/screenshots.py   (after scripts/build_data.py)
Needs the dev tools: pip install -r requirements-dev.txt && python -m playwright install chromium
Writes docs/screenshots/app.png (default view), comparison.png (four strategies),
coverage.png and robustness.png.
"""
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
PORT = 8765
URL = f"http://localhost:{PORT}"


def wait_for_server(timeout=120):
    stop = time.monotonic() + timeout
    while time.monotonic() < stop:
        try:
            if urlopen(f"{URL}/_stcore/health", timeout=2).read() == b"ok":
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("the app didn't start")


def shoot(page, out):
    page.wait_for_selector(".js-plotly-plot", timeout=180_000)
    page.wait_for_load_state("networkidle")
    time.sleep(3)  # let charts finish drawing
    height = page.evaluate("document.querySelector('[data-testid=\"stMainBlockContainer\"]').scrollHeight")
    page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1440, "height": min(height + 120, 6000)})
    print(f"wrote {out.relative_to(ROOT)}")


def capture(page, path, out, wait_text):
    page.goto(f"{URL}{path}")
    page.get_by_text(wait_text).first.wait_for(timeout=180_000)
    shoot(page, out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
                               "--server.headless", "true", "--server.port", str(PORT),
                               "--browser.gatherUsageStats", "false", "--theme.base", "light"],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Streamlit scrolls inside its own container, so a "full page" capture only gets one
            # screen: use a window tall enough to show everything instead.
            page = browser.new_page(viewport={"width": 1440, "height": 6000}, device_scale_factor=1)
            capture(page, "/", OUT / "app.png", "Year by year")
            # The comparison view: add momentum and low volatility to the default two strategies.
            for option in ("Momentum (top 10%, monthly)", "Low volatility (50 calmest, quarterly)"):
                page.locator('[data-testid="stMultiSelect"] input').first.click()
                page.get_by_role("option", name=option).click()
                page.keyboard.press("Escape")
            # Wait until the new strategies' charts exist, then for the rerun to finish.
            page.locator(".js-plotly-plot text", has_text="Low volatility").first.wait_for(timeout=180_000)
            page.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=180_000)
            shoot(page, OUT / "comparison.png")
            capture(page, "/Coverage", OUT / "coverage.png", "Members not covered or flagged")
            capture(page, "/Robustness", OUT / "robustness.png", "All 36 variants")
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
