"""Rebuild everything the app needs, in order.

Usage:
  python scripts/build_data.py                 needs EODHD_API_KEY in .env (Historian plan)
  python scripts/build_data.py --no-download   offline: uses data already in data/raw/eodhd/

Steps:
  1. scripts/download_eodhd.py --scope v1   prices, dividends and splits for every S&P 500
                                            member since 1996, plus SPY and RSP. Files already
                                            downloaded are never fetched again.
  2. scripts/build_price_cache.py           map members to price series, apply hand fixes and
                                            price exclusions, run the trap test
  3. scripts/build_universes.py             coverage results and universes for the app
Then: streamlit run app.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def step(script: str, *args: str):
    print(f"\n=== {script} {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], check=True)


def main():
    if "--no-download" not in sys.argv:
        step("download_eodhd.py", "--scope", "v1")
    step("build_price_cache.py")
    step("build_universes.py")
    print("\ndone - now run: streamlit run app.py")


if __name__ == "__main__":
    main()
