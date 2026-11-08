# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [0.2.0] -  2026-08-11

- Arch/linux build tested as functioniong

## [0.1.0] - 2026-05-11

- Initial release with balance polling, tray icon, and Windows launch-on-boot support.
