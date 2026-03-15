#!/usr/bin/env python3
"""Interactive market data source setup for Text2trade.

No API keys. No signup. No demat account.
All data comes directly from NSE India.
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv, set_key

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_PATH)


def print_banner():
    print()
    print("=" * 52)
    print("  MARKET DATA SOURCE SETUP")
    print("=" * 52)
    print()
    print("  Your app needs historical stock data for backtesting.")
    print("  All data comes directly from NSE India.")
    print()
    print("  *** No signup needed. No API key. No demat account. ***")
    print()


def check_dependency(pkg_name: str, pip_name: str = None) -> bool:
    try:
        __import__(pkg_name)
        return True
    except ImportError:
        return False


def install_dependency(pip_name: str):
    print(f"  Installing {pip_name}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pip_name, "-q"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  -> {pip_name} installed")
        return True
    else:
        print(f"  -> FAILED: {result.stderr.strip()}")
        return False


def test_nse_connection():
    print()
    print("  Testing NSE connection...")
    try:
        from nsepython import nse_marketStatus
        import time
        time.sleep(1.5)
        status = nse_marketStatus()
        market_state = "Unknown"
        if isinstance(status, dict):
            market_state = status.get("marketState", [{}])
            if isinstance(market_state, list) and len(market_state) > 0:
                market_state = market_state[0].get("marketStatus", "Unknown")
        elif isinstance(status, list) and len(status) > 0:
            market_state = status[0].get("marketStatus", "Unknown")
        print(f"  -> NSE India reachable. Market status: {market_state}")
        return True
    except Exception as e:
        err = str(e)
        if "maintenance" in err.lower() or "403" in err or "blocked" in err:
            print("  -> NSE website is in maintenance. Try again after 6 AM IST.")
        else:
            print(f"  -> Connection failed: {err}")
            print("  -> NSE may be temporarily unavailable. Try again in a few minutes.")
        return False


def main():
    print_banner()

    print("  Choose your data strategy:")
    print()
    print("  [1] Full (RECOMMENDED)")
    print("      -> nsepython for daily OHLCV (3 years)")
    print("      -> NseIndiaApi for intraday data")
    print("      -> NSE Bhavcopy as backup")
    print("      -> Zero configuration. Works immediately.")
    print()
    print("  [2] Daily Only (lightweight)")
    print("      -> NSE Bhavcopy for daily OHLCV only")
    print("      -> No intraday data")
    print("      -> Smallest footprint, fastest setup")
    print()

    choice = input("  Enter choice [1/2]: ").strip()
    if choice not in ("1", "2"):
        print("  Invalid choice. Exiting.")
        sys.exit(1)

    strategy = "full" if choice == "1" else "daily_only"

    print()
    print("  Installing dependencies...")

    # Always install nsepython (needed for both strategies)
    if not check_dependency("nsepython"):
        install_dependency("nsepython")
    else:
        print(f"  -> nsepython already installed")

    if strategy == "full":
        if not check_dependency("nse"):
            install_dependency("nse")
        else:
            print(f"  -> nse (NseIndiaApi) already installed")

    if not check_dependency("pandas"):
        install_dependency("pandas")

    # Test connection
    connected = test_nse_connection()
    if not connected:
        print()
        print("  Setup will continue anyway. Data ingestion can be retried later.")

    # Save to .env
    print()
    print(f"  Saving to .env -> DATA_STRATEGY={strategy}")
    set_key(ENV_PATH, "DATA_STRATEGY", strategy)
    print(f"  -> Done")

    print()
    print("  Ready to download data. Run:")
    print("    python scripts/ingest_data.py")
    print()
    print("=" * 52)


if __name__ == "__main__":
    main()
