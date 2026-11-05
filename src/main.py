#!/usr/bin/env python3


from __future__ import annotations

import os
import platform
import sys
import threading
import time
from datetime import datetime, timezone

import requests
from PIL import Image
import pystray

API_URL = "https://ollama.com/api/balance"

POLL_SECONDS = 10               # API allows 10 req/min per user (min 6s interval)
ICON_SIZE = 32
TIMEOUT = 15

GREEN_TINT = (76, 175, 80)
RED_TINT = (229, 57, 53)

state = {"text": "Ollama balance: loading\u2026"}
startup_state = {"enabled": False}

APP_NAME = "ollama-balance-monitor"
REGISTRY_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def base_path() -> str:
    """Return the base path for bundled resources, handling PyInstaller."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


_logo_cache: Image.Image | None = None


def load_logo() -> Image.Image:
    """Load the Ollama logo from the assets directory, cached after first call."""
    global _logo_cache
    if _logo_cache is not None:
        return _logo_cache.copy()

    script_dir = base_path()
    candidates = [
        os.path.join(script_dir, "assets", "ollama.ico"),
        os.path.join(os.path.dirname(script_dir), "assets", "ollama.ico"),
    ]

    for path in candidates:
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            img.thumbnail((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
            _logo_cache = img
            return img.copy()

    raise FileNotFoundError(f"ollama.ico not found; searched: {', '.join(candidates)}")


def tint_image(img: Image.Image, tint: tuple[int, int, int]) -> Image.Image:
    """Apply a colour tint to the non-transparent parts of the image."""
    tinted = img.copy()
    r, g, b = tint
    pixels = tinted.load()
    if pixels is None:
        return tinted

    for y in range(tinted.height):
        for x in range(tinted.width):
            _, _, _, alpha = pixels[x, y]
            if alpha > 0:
                pixels[x, y] = (r, g, b, alpha)
    return tinted


def is_startup_enabled() -> bool:
    """Check whether the app is registered to start on Windows boot."""
    if platform.system() != "Windows":
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_startup_enabled(enabled: bool) -> None:
    """Register or unregister the app to start on Windows boot."""
    if platform.system() != "Windows":
        return

    import winreg

    if getattr(sys, "frozen", False):
        key_path = os.path.abspath(sys.argv[0])
    else:
        key_path = f'"{os.path.abspath(sys.executable)}" "{os.path.abspath(sys.argv[0])}"'

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REGISTRY_RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, key_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def toggle_startup(icon: pystray.Icon, item: pystray.MenuItem) -> None: # type: ignore
    """Toggle launch-on-boot and refresh the menu."""
    new_state = not startup_state["enabled"]
    set_startup_enabled(new_state)
    startup_state["enabled"] = is_startup_enabled()
    icon.update_menu()


def fetch_balance() -> dict:
    """Return the raw balance JSON from the Ollama API."""
    key = os.environ.get("OLLAMA_API_KEY")
    if not key:
        raise RuntimeError("OLLAMA_API_KEY is not set")

    resp = requests.get(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def parse_period(balance: dict) -> tuple[datetime, datetime]:
    """Extract the current period 'from' and 'until' datetimes."""
    period = (balance.get("included") or {}).get("period") or {}
    from_str = period.get("from")
    until_str = period.get("until")
    if not from_str or not until_str:
        raise ValueError("API response missing included.period.from/until")

    from_dt = datetime.fromisoformat(from_str.replace("Z", "+00:00"))
    until_dt = datetime.fromisoformat(until_str.replace("Z", "+00:00"))
    return from_dt, until_dt


def budget_status(allowance: float, used: float, from_dt: datetime, until_dt: datetime) -> tuple[float, float, bool]:
    """Return (daily_budget, expected_spend_by_now, is_over_pace).

    The monthly budget is spread evenly across the days in the period.
    Day counting is inclusive: day 1 is the start date, the last day is
    the 'until' date.
    """
    total_days = max(1, (until_dt - from_dt).days + 1)
    daily_budget = allowance / total_days

    now = datetime.now(timezone.utc)
    if now < from_dt:
        day_index = 0
    elif now > until_dt:
        day_index = total_days - 1
    else:
        day_index = (now - from_dt).days

    expected_spend_by_now = daily_budget * (day_index + 1)
    is_over_pace = used > expected_spend_by_now
    return daily_budget, expected_spend_by_now, is_over_pace


def format_title(allowance: float, used: float, remaining: float, pctremaining: float, daily: float, expected: float, over: bool) -> str:
    status = "OVER" if over else "OK"
    return (
        f"Ollama Cloud  |  Pro  |  {status}"
        f"\nUsed: ${used:.2f}  |  ${remaining:.2f} ({pctremaining:.1f}%)"
        f"\nRate:  ${expected:.2f} @ ${daily:.2f}/day"
    )


def refresh(icon: pystray.Icon, logo: Image.Image) -> None: # type: ignore
    try:
        balance = fetch_balance()
        included = balance.get("included") or {}
        purchased = balance.get("purchased") or {}

        allowance = float(included.get("allowance_usd") or 0.0)
        remaining_included = float(included.get("balance_usd") or 0.0)
        remaining_purchased = float(purchased.get("balance_usd") or 0.0)
        remaining = remaining_included + remaining_purchased

        total_budget = allowance + remaining_purchased
        used = max(0.0, total_budget - remaining)
        pctremaining = (remaining / total_budget * 100.0) if total_budget else 0.0

        from_dt, until_dt = parse_period(balance)
        daily, expected, over = budget_status(allowance, used, from_dt, until_dt)

        icon.icon = tint_image(logo, RED_TINT if over else GREEN_TINT)
        icon.title = format_title(allowance, used, remaining, pctremaining, daily, expected, over)
        state["text"] = icon.title
    except Exception as exc:
        icon.icon = tint_image(logo, RED_TINT)
        icon.title = "Ollama balance: unavailable"
        state["text"] = icon.title
        print(f"[ollama-balance] {exc}", file=sys.stderr)

    try:
        icon.update_menu()
    except Exception as exc:
        print(f"[ollama-balance] menu update failed: {exc}", file=sys.stderr)


def poll_loop(icon: pystray.Icon, logo: Image.Image) -> None: # type: ignore
    while True:
        refresh(icon, logo)
        time.sleep(POLL_SECONDS)


def manual_refresh(icon: pystray.Icon, logo: Image.Image, _item=None) -> None: # type: ignore
    threading.Thread(target=refresh, args=(icon, logo), daemon=True).start()


def startup_menu_item() -> pystray.MenuItem | None:
    """Return the launch-on-boot menu item on Windows, or None on other platforms."""
    if platform.system() != "Windows":
        return None

    startup_state["enabled"] = is_startup_enabled()

    def checked(item: pystray.MenuItem) -> bool:
        return startup_state["enabled"]

    return pystray.MenuItem("Launch on boot", toggle_startup, checked=checked)


def build_menu(logo: Image.Image) -> pystray.Menu:
    items: list[pystray.MenuItem | None] = [
        pystray.MenuItem(lambda _item: state["text"], None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Refresh now", lambda icon, item: manual_refresh(icon, logo, item)),
        startup_menu_item(),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, _item: icon.stop()),
    ]
    return pystray.Menu(*[item for item in items if item is not None])


def main() -> None:
    logo = load_logo()
    icon = pystray.Icon(
        "ollama-balance",
        logo,
        "Ollama balance: loading\u2026",
        menu=build_menu(logo),
    )
    threading.Thread(target=poll_loop, args=(icon, logo), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()