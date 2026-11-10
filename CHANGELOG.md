# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-11

### Added
- **Poll rate selector**: new `Polling >` submenu lets you cycle between `15s`, `30s`, `45s`, and `60s` refresh intervals.
- **Tooltip submenu**: new `Tooltip >` submenu groups the figures, percentages, and progress-bar toggles.
- **Details submenu**: detailed budget and usage data is now always available under `Details >`, separate from the tooltip.
- **`latest_state` cache**: stores the most recent balance and usage data so the menu can be rebuilt on demand without re-fetching.
- **`update_tooltip()` helper**: rebuilds the tooltip text after display toggles change, fixing blank-hover issues on Windows.
- **Submenu indicators**: menu items that open submenus now show `>` for clarity on Linux/AppIndicator.

### Changed
- **Tooltip is now always compact**: the long advanced view no longer appears in the tooltip; it lives in the `Details >` submenu. This avoids Windows' 127-character tray-tooltip limit which truncated the advanced view (Issue #1).
- **Menu reorganised**:
  - `Tooltip >`
  - `Details >`
  - separator
  - `Polling >`
  - `Refresh now`
  - separator
  - `Launch on boot [ ]`
  - `Quit`
- **Poll rate default lowered to 15 seconds**: fastest option is now `15s` (with `30s`, `45s`, `60s`) to stay safely below the API rate limit when both the balance and usage endpoints are called each poll.
- **Progress bar restyled**: uses `█` and `░` block characters and no longer wraps in brackets.
- **Usage API**: now always fetched because it is only displayed inside the `Details >` submenu.
- Renamed `build_advanced_view()` to `build_details_content()` and split budget/usage lines for cleaner separators.
- `build_details_menu()` now handles the pre-fetch loading state safely.

### Removed
- Simple/Advanced view toggle and `advanced_view_state` (replaced by persistent submenus).
- Flat `Show figures`, `Show percentages`, and `Show progress bar` items from the main menu.

### Fixed
- Blank tooltip that appeared after toggling tooltip display options.
- Startup crash caused by building the Details submenu before the first API response.
- Usage range changes now trigger an immediate refresh and update the displayed usage data.

## [0.3.0] - 2026-08-11

### Added
- **Usage API integration**: new optional advanced view pulls usage stats from `https://ollama.com/api/usage`.
- **Usage range selector**: cycle between `24h`, `7d`, and `30d` ranges from the tray menu (advanced view only).
- **Simple / Advanced view toggle**: switch between a compact tooltip and an expanded details view.
- **Polling toggle**: enable or disable automatic background refreshes from the tray menu.
- **Simple view display options**: individually toggle figures, percentages, and progress bar.
- **Progress bar**: optional ASCII progress bar; mandatory when advanced view is enabled.
- `safe_update_menu()` helper to preserve tooltip text while updating the menu.

### Changed
- **Budget calculations are now based purely on the plan allowance**, not purchased credits. Pacing, daily rate, expected spend, percentages, and the progress bar all use the plan amount only.
- **Tooltip redesigned**:
  - Simple view header now shows `Plan @ $daily/day · On/Over rate`.
  - Simple view left amount now displays remaining included balance plus purchased credits separately, e.g. `$47.66 (+$20.00) left`.
  - Advanced view shows detailed aligned rows: plan, included amount, purchased credits, used, remaining, daily rate, expected spend, status, period, day, progress bar, and usage totals.
- **Menu reorganised**:
  - `Launch on boot` moved to the top.
  - View switcher label changes dynamically between "Switch to Advanced View" and "Switch to Simple View".
  - Context-sensitive options: simple-view toggles hide in advanced view; usage range hides in simple view.
- Percentages now display with two decimal places.
- Default progress bar width adjusted to 27 characters.

### Removed
- Legacy `format_title()` function replaced by `build_tooltip()` and `build_advanced_view()`.
- Inline docstrings removed for a more compact source file.

### Fixed
- Menu now correctly rebuilds when switching between simple and advanced views so only the relevant options are shown.
- Usage API is no longer called when advanced view is disabled, avoiding unnecessary requests and error logs.

## [0.2.0] - 2026-08-11

- Arch/Linux build tested as functioning.

## [0.1.0] - 2026-05-11

- Initial release with balance polling, tray icon, and Windows launch-on-boot support.

