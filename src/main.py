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

if platform.system() == "Linux":
    import gi
    gi.require_version("AppIndicator3", "0.1")
import pystray

API_URL = "https://ollama.com/api/balance"
USAGE_API_URL = "https://ollama.com/api/usage"
DEFAULT_USAGE_RANGE = "24h"
USAGE_RANGES = ["24h", "7d", "30d"]
POLL_RATES = [15, 30, 45, 60]
DEFAULT_POLL_RATE = 15
ICON_SIZE = 32
TIMEOUT = 15
GREEN_TINT = (76, 175, 80)
RED_TINT = (229, 57, 53)

state = {"text": "Ollama balance: loading..."}
startup_state = {"enabled": False}
polling_state = {"enabled": True}
figures_state = {"enabled": True}
percentages_state = {"enabled": False}
progress_bar_state = {"enabled": False}
usage_range_state = {"value": "24h"}
poll_rate_state = {"value": DEFAULT_POLL_RATE}
latest_state = {
    "allowance": 0.0,
    "used": 0.0,
    "remaining_included": 0.0,
    "remaining_purchased": 0.0,
    "daily": 0.0,
    "expected": 0.0,
    "over": False,
    "from_dt": None,
    "until_dt": None,
    "usage": None,
}
APP_NAME = "ollama-balance-monitor"
REGISTRY_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def base_path() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


_logo_cache: Image.Image | None = None


def load_logo() -> Image.Image:
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


def safe_update_menu(icon: pystray.Icon) -> None:
    title = icon.title
    try:
        icon.update_menu()
    finally:
        icon.title = title


def is_startup_enabled() -> bool:
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
    if platform.system() != "Windows":
        return
    import winreg
    if getattr(sys, "frozen", False):
        key_path = os.path.abspath(sys.argv[0])
    else:
        key_path = f'"{os.path.abspath(sys.executable)}" "{os.path.abspath(sys.argv[0])}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, key_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def toggle_startup(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    new_state = not startup_state["enabled"]
    set_startup_enabled(new_state)
    startup_state["enabled"] = is_startup_enabled()
    safe_update_menu(icon)


def toggle_polling(icon: pystray.Icon, logo: Image.Image, item: pystray.MenuItem) -> None:
    was_enabled = polling_state["enabled"]
    polling_state["enabled"] = not was_enabled
    if polling_state["enabled"] and not was_enabled:
        threading.Thread(target=refresh, args=(icon, logo), daemon=True).start()
    safe_update_menu(icon)


def polling_menu_label(item: pystray.MenuItem) -> str:
    return "Polling [✓]" if polling_state["enabled"] else "Polling [ ]"


def is_polling_enabled(item: pystray.MenuItem) -> bool:
    return polling_state["enabled"]


def toggle_figures(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    figures_state["enabled"] = not figures_state["enabled"]
    update_tooltip(icon)
    safe_update_menu(icon)


def figures_menu_label(item: pystray.MenuItem) -> str:
    return "Show figures [✓]" if figures_state["enabled"] else "Show figures [ ]"


def are_figures_enabled(item: pystray.MenuItem) -> bool:
    return figures_state["enabled"]


def toggle_percentages(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    percentages_state["enabled"] = not percentages_state["enabled"]
    update_tooltip(icon)
    safe_update_menu(icon)


def percentages_menu_label(item: pystray.MenuItem) -> str:
    return "Show percentages [✓]" if percentages_state["enabled"] else "Show percentages [ ]"


def are_percentages_enabled(item: pystray.MenuItem) -> bool:
    return percentages_state["enabled"]


def toggle_progress_bar(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    progress_bar_state["enabled"] = not progress_bar_state["enabled"]
    update_tooltip(icon)
    safe_update_menu(icon)


def progress_bar_menu_label(item: pystray.MenuItem) -> str:
    return "Show progress bar [✓]" if progress_bar_state["enabled"] else "Show progress bar [ ]"


def is_progress_bar_enabled(item: pystray.MenuItem) -> bool:
    return progress_bar_state["enabled"]


def details_menu_item(logo: Image.Image) -> pystray.MenuItem:
    return build_details_menu(logo)


def next_usage_range() -> str:
    """Cycle to the next usage range value."""
    current = usage_range_state["value"]
    try:
        idx = USAGE_RANGES.index(current)
    except ValueError:
        idx = -1
    return USAGE_RANGES[(idx + 1) % len(USAGE_RANGES)]


def toggle_usage_range(icon: pystray.Icon, _item: pystray.MenuItem, logo: Image.Image) -> None:
    usage_range_state["value"] = next_usage_range()
    threading.Thread(target=refresh, args=(icon, logo), daemon=True).start()


def usage_range_menu_label(item: pystray.MenuItem) -> str:
    return f"Usage range: {usage_range_state['value']}"


def next_poll_rate() -> int:
    """Cycle to the next polling rate value."""
    current = poll_rate_state["value"]
    try:
        idx = POLL_RATES.index(current)
    except ValueError:
        idx = -1
    return POLL_RATES[(idx + 1) % len(POLL_RATES)]


def toggle_poll_rate(icon: pystray.Icon, _item: pystray.MenuItem, logo: Image.Image) -> None:
    poll_rate_state["value"] = next_poll_rate()
    icon.menu = build_menu(logo)
    safe_update_menu(icon)


def poll_rate_menu_label(item: pystray.MenuItem) -> str:
    return f"Poll rate: {poll_rate_state['value']}s"


def fetch_balance() -> dict:
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


def fetch_usage(range_value: str = DEFAULT_USAGE_RANGE) -> dict:
    """Return usage data from the Ollama API for the given range."""
    key = os.environ.get("OLLAMA_API_KEY")
    if not key:
        raise RuntimeError("OLLAMA_API_KEY is not set")

    resp = requests.get(
        f"{USAGE_API_URL}?range={range_value}",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def parse_period(balance: dict) -> tuple[datetime, datetime]:
    period = (balance.get("included") or {}).get("period") or {}
    from_str = period.get("from")
    until_str = period.get("until")
    if not from_str or not until_str:
        raise ValueError("API response missing included.period.from/until")
    from_dt = datetime.fromisoformat(from_str.replace("Z", "+00:00"))
    until_dt = datetime.fromisoformat(until_str.replace("Z", "+00:00"))
    return from_dt, until_dt


def budget_status(allowance: float, used: float, from_dt: datetime, until_dt: datetime) -> tuple[float, float, bool]:
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


def plan_name(allowance: float) -> str:
    plans = {0.0: "Free", 60.0: "Pro", 300.0: "Max", 1000.0: "Team"}
    return plans.get(allowance, f"${allowance:.0f}")


def ascii_progress_bar(used: float, total: float, width: int = 27) -> str:
    if width < 2:
        return ""
    if total <= 0:
        filled = 0
    else:
        ratio = min(max(used / total, 0.0), 1.0)
        filled = int(round(width * ratio))
    empty = width - filled
    return "█" * filled + "░" * empty


def fmt(value: float) -> str:
    return f"${value:.2f}"


def pct(value: float, total: float) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(value / total * 100.0):.2f}%"


def build_details_content(allowance: float, used: float, remaining_included: float, remaining_purchased: float, daily: float, expected: float, over: bool, from_dt: datetime, until_dt: datetime, usage: dict | None) -> tuple[list[str], list[str]]:
    total_days = max(1, (until_dt - from_dt).days + 1)
    now = datetime.now(timezone.utc)
    if now < from_dt:
        day_index = 0
    elif now > until_dt:
        day_index = total_days
    else:
        day_index = (now - from_dt).days + 1

    rows = [
        ("Plan", plan_name(allowance)),
        ("Included", fmt(allowance)),
        ("Purchased", fmt(remaining_purchased)),
        ("Used", f"{fmt(used)} ({pct(used, allowance)})"),
        ("Remaining", f"{fmt(remaining_included)} ({pct(remaining_included, allowance)})"),
        ("Daily rate", f"{fmt(daily)}/day"),
        ("On rate spend", fmt(expected)),
        ("Status", "Over rate" if over else "On rate"),
        ("Period", f"{from_dt.strftime('%Y-%m-%d')} → {until_dt.strftime('%Y-%m-%d')}"),
        ("Day", f"{day_index} / {total_days}"),
    ]

    width = max(len(label) for label, _ in rows)
    budget_lines = [f"{label:<{width}}  {value}" for label, value in rows]

    if usage:
        totals = usage.get("totals") or {}
        usage_rows = [
            ("Usage range", f"{usage_range_state['value']} ({usage.get('range', 'N/A')})"),
            ("Usage from", str(usage.get("from", "N/A"))),
            ("Usage until", str(usage.get("until", "N/A"))),
            ("Requests", str(totals.get("request_count", 0))),
            ("Usage cost", fmt(float(totals.get("usage_usd") or 0.0))),
            ("Input tokens", f"{int(totals.get('input_tokens') or 0):,}"),
            ("Cached tokens", f"{int(totals.get('cached_input_tokens') or 0):,}"),
            ("Output tokens", f"{int(totals.get('output_tokens') or 0):,}"),
        ]
        usage_width = max(len(label) for label, _ in usage_rows)
        usage_lines = [f"{label:<{usage_width}}  {value}" for label, value in usage_rows]
    else:
        usage_lines = []

    return budget_lines, usage_lines


def build_details_menu(logo: Image.Image) -> pystray.MenuItem:
    s = latest_state

    submenu_items: list[pystray.MenuItem | None] = [
        pystray.MenuItem(usage_range_menu_label, lambda icon, item: toggle_usage_range(icon, item, logo)),
        pystray.Menu.SEPARATOR,
    ]

    if s["from_dt"] is None or s["until_dt"] is None:
        submenu_items.append(pystray.MenuItem("Loading...", None, enabled=False))
    else:
        budget_lines, usage_lines = build_details_content(
            s["allowance"],
            s["used"],
            s["remaining_included"],
            s["remaining_purchased"],
            s["daily"],
            s["expected"],
            s["over"],
            s["from_dt"],
            s["until_dt"],
            s["usage"],
        )

        submenu_items.append(pystray.MenuItem("-- Budget --", None, enabled=False))
        for line in budget_lines:
            submenu_items.append(pystray.MenuItem(line, None, enabled=False))

        if usage_lines:
            submenu_items.append(pystray.Menu.SEPARATOR)
            submenu_items.append(pystray.MenuItem("-- Usage --", None, enabled=False))
            for line in usage_lines:
                submenu_items.append(pystray.MenuItem(line, None, enabled=False))

    return pystray.MenuItem("Details >", pystray.Menu(*[item for item in submenu_items if item is not None]))


def build_tooltip_menu(logo: Image.Image) -> pystray.MenuItem:
    submenu = pystray.Menu(
        pystray.MenuItem(figures_menu_label, toggle_figures, checked=are_figures_enabled),
        pystray.MenuItem(percentages_menu_label, toggle_percentages, checked=are_percentages_enabled),
        pystray.MenuItem(progress_bar_menu_label, toggle_progress_bar, checked=is_progress_bar_enabled),
    )
    return pystray.MenuItem("Tooltip >", submenu)


def build_tooltip(allowance: float, used: float, remaining_included: float, remaining_purchased: float, daily: float, expected: float, over: bool) -> str:
    status = "Over rate" if over else "On rate"
    plan = plan_name(allowance)
    used_pct = (used / allowance * 100.0) if allowance > 0 else 0.0
    remaining_pct = (remaining_included / allowance * 100.0) if allowance > 0 else 0.0

    lines: list[str] = [f"{plan} @ ${daily:.2f}/day  ·  {status}"]
    if figures_state["enabled"]:
        if remaining_purchased > 0:
            lines.append(f"${used:.2f} used  ·  ${remaining_included:.2f} (+${remaining_purchased:.2f}) left")
        else:
            lines.append(f"${used:.2f} used  ·  ${remaining_included:.2f} left")
    if percentages_state["enabled"]:
        lines.append(f"{used_pct:.2f}% used  ·  {remaining_pct:.2f}% left")
    if progress_bar_state["enabled"]:
        lines.append(ascii_progress_bar(used, allowance))

    return "\n".join(lines)


def update_tooltip(icon: pystray.Icon) -> None:
    s = latest_state
    icon.title = build_tooltip(
        s["allowance"],
        s["used"],
        s["remaining_included"],
        s["remaining_purchased"],
        s["daily"],
        s["expected"],
        s["over"],
    )
    state["text"] = icon.title


def refresh(icon: pystray.Icon, logo: Image.Image) -> None:
    try:
        balance = fetch_balance()
        included = balance.get("included") or {}
        purchased = balance.get("purchased") or {}
        allowance = float(included.get("allowance_usd") or 0.0)
        remaining_included = float(included.get("balance_usd") or 0.0)
        remaining_purchased = float(purchased.get("balance_usd") or 0.0)
        used = max(0.0, allowance - remaining_included)
        from_dt, until_dt = parse_period(balance)
        daily, expected, over = budget_status(allowance, used, from_dt, until_dt)

        try:
            usage = fetch_usage(usage_range_state["value"])
        except Exception as usage_exc:
            usage = None
            print(f"[ollama-balance] usage fetch failed: {usage_exc}", file=sys.stderr)

        latest_state.update({
            "allowance": allowance,
            "used": used,
            "remaining_included": remaining_included,
            "remaining_purchased": remaining_purchased,
            "daily": daily,
            "expected": expected,
            "over": over,
            "from_dt": from_dt,
            "until_dt": until_dt,
            "usage": usage,
        })

        icon.icon = tint_image(logo, RED_TINT if over else GREEN_TINT)
        update_tooltip(icon)
    except Exception as exc:
        icon.icon = tint_image(logo, RED_TINT)
        icon.title = "Ollama balance: unavailable"
        state["text"] = icon.title
        print(f"[ollama-balance] {exc}", file=sys.stderr)
    try:
        safe_update_menu(icon)
    except Exception as exc:
        print(f"[ollama-balance] menu update failed: {exc}", file=sys.stderr)

    try:
        icon.menu = build_menu(logo)
    except Exception as exc:
        print(f"[ollama-balance] menu rebuild failed: {exc}", file=sys.stderr)


def poll_loop(icon: pystray.Icon, logo: Image.Image) -> None:
    while True:
        if polling_state["enabled"]:
            refresh(icon, logo)
        time.sleep(poll_rate_state["value"])


def manual_refresh(icon: pystray.Icon, logo: Image.Image, _item=None) -> None:
    threading.Thread(target=refresh, args=(icon, logo), daemon=True).start()


def startup_menu_item() -> pystray.MenuItem | None:
    if platform.system() != "Windows":
        return None
    startup_state["enabled"] = is_startup_enabled()
    def checked(item: pystray.MenuItem) -> bool:
        return startup_state["enabled"]
    return pystray.MenuItem("Launch on boot", toggle_startup, checked=checked)


def build_polling_menu(logo: Image.Image) -> pystray.MenuItem:
    submenu = pystray.Menu(
        pystray.MenuItem(polling_menu_label, lambda icon, item: toggle_polling(icon, logo, item), checked=is_polling_enabled),
        pystray.MenuItem(poll_rate_menu_label, lambda icon, item: toggle_poll_rate(icon, item, logo)),
    )
    return pystray.MenuItem("Polling >", submenu)


def build_menu(logo: Image.Image) -> pystray.Menu:
    items: list[pystray.MenuItem | None] = [
        pystray.MenuItem(lambda _item: state["text"], None, enabled=False),
        pystray.Menu.SEPARATOR,
        build_tooltip_menu(logo),
        details_menu_item(logo),
        pystray.Menu.SEPARATOR,
        build_polling_menu(logo),
        pystray.MenuItem("Refresh now", lambda icon, item: manual_refresh(icon, logo, item)),
        pystray.Menu.SEPARATOR,
    ]

    startup = startup_menu_item()
    if startup is not None:
        items.append(startup)

    items.append(pystray.MenuItem("Quit", lambda icon, _item: icon.stop()))

    return pystray.Menu(*[item for item in items if item is not None])


def main() -> None:
    logo = load_logo()
    icon = pystray.Icon("ollama-balance", logo, "Ollama balance: loading...", menu=build_menu(logo))
    threading.Thread(target=poll_loop, args=(icon, logo), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()