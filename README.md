# Ollama Balance Monitor

A lightweight system tray monitor for your [Ollama](https://ollama.com) cloud balance.

It polls `https://ollama.com/api/balance` at a set interval and shows the Ollama logo in your system tray. The icon is tinted **green** when you are under your monthly budget pace, and **red** when you are spending faster than expected. Hovering over the tray icon shows your current usage, remaining balance, daily budget rate, and expected spend so far.

Ollama API documentation: https://docs.ollama.com/api/introduction

<p align="center">
  <img src="assets/ollama.png" alt="Tray icon preview" width="128">
</p>

## Features

- Live balance check from the Ollama cloud balance API
- Tray icon tinted green or red based on monthly budget pacing
- Monthly budget automatically derived from your Ollama Pro `allowance_usd`
- Daily expected spend calculated from the number of days in your billing period
- Manual refresh from the tray menu
- Windows: launch on boot toggle
- Windows: standalone `.exe` build via PyInstaller

## Requirements

- Python 3.10+
- Windows or Linux (Arch + Hyprland/Wayland tested; other distros/desktop environments should work with the same dependencies)
- macOS currently untested
- `OLLAMA_API_KEY` environment variable

## Installation

Clone the repository:

```bash
git clone https://github.com/jakeewart/ollama-balance-monitor.git
cd ollama-balance-monitor
```

### Building a standalone Windows executable

On Windows, run:

```bash
build.bat
```

This script will:

1. Check that Python is installed
2. Prompt for your Ollama Cloud API key (if not already set)
3. Install Python dependencies from `src/requirements.txt`
4. Build a single `.exe` file using PyInstaller

The output is:

```text
dist/ollama-balance-monitor.exe
```

Run that file to start the monitor in the background with no console window.

### Notes on the build

- `assets/ollama.ico` is used for both the application icon and the tray icon
- The API key is set as a user environment variable during the build
- You can update your key later by running `update-api-key.bat`

### Linux

The app has been tested on **Arch Linux with Hyprland/Wayland**. It should work on any Wayland or X11 desktop with a system tray that supports the SNI/AppIndicator protocol (e.g., Waybar, KDE, GNOME).

1. Install system dependencies:

   ```bash
   sudo pacman -S gobject-introspection gtk3 libappindicator-gtk3
   ```

   On Debian/Ubuntu-based distros the equivalent packages are roughly (untested):

   ```bash
   sudo apt install libgirepository1.0-dev libcairo2-dev python3-gi python3-gi-cairo libappindicator3-1 gir1.2-appindicator3-0.1
   ```

2. Create a virtual environment and install Python packages:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r src/requirements.txt
   ```

3. Run:

   ```bash
   export OLLAMA_API_KEY="your-api-key-here"
   python src/main.py
   ```

   For Waybar/Hyprland, make sure the tray module is enabled in `~/.config/waybar/config`.
   Then restart Waybar.

### Manual Install (all platforms)

Install dependencies:

```bash
pip install -r src/requirements.txt
```

Run directly from source:

```bash
python src/main.py
```

The tray icon refreshes every 10 seconds by default. Right-click the icon to refresh manually, toggle launch on boot, or quit.

## Setting your API key

You need to set `OLLAMA_API_KEY` as an environment variable. The easiest way on Windows is to run the provided helper script or entering during build.bat.

### Windows

Double-click:

```text
update-api-key.bat
```

This opens a small popup asking for your Ollama Cloud API key.

- **Save** — saves the key to your user environment variables so it persists across reboots
- **Skip** — closes the popup without making any changes

The key is masked in the input box. You can re-run this script any time to update your key.

### Manual setup

If you prefer to set the key yourself:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_API_KEY", "your-api-key-here", "User")
```

Restart your terminal or log out and back in for the change to take effect.

### Linux / macOS

On Linux, set the key in your current shell:

```bash
export OLLAMA_API_KEY="your-api-key-here"
```

To make it persistent, add the same line to `~/.bashrc`, `~/.zshrc`, or use a systemd service (see [Launch on boot](#launch-on-boot-linux) below).

On macOS, add it to `~/.zshrc` or `~/.bash_profile`:

```bash
export OLLAMA_API_KEY="your-api-key-here"
```

Then reload your shell or open a new terminal.

## Launch on boot

### Windows

Right-click the tray icon and select **Launch on boot** to add or remove the app from your startup registry. The app will start automatically the next time you log in.

### Linux {#launch-on-boot-linux}

Create a systemd user service. Adjust the paths and API key to match your setup.

`~/.config/systemd/user/ollama-balance.service`:

```ini
[Unit]
Description=Ollama Balance Monitor

[Service]
Type=simple
Environment=OLLAMA_API_KEY=your-api-key-here
WorkingDirectory=%h/source/ollama-balance-monitor
ExecStart=%h/source/ollama-balance-monitor/.venv/bin/python %h/source/ollama-balance-monitor/src/main.py
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable and start it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ollama-balance.service
```

To view logs:

```bash
journalctl --user -u ollama-balance.service -f
```

#### Storing the API key in a separate env file

If you prefer not to keep your API key in the unit file, you can put it in an environment file with restricted permissions instead.

`~/.config/ollama-balance/env`:

```bash
OLLAMA_API_KEY=your-api-key-here
```

Lock down the file so only your user can read it:

```bash
chmod 600 ~/.config/ollama-balance/env
```

Then change the service to load it with `EnvironmentFile`:

```ini
[Service]
Type=simple
EnvironmentFile=%h/.config/ollama-balance/env
WorkingDirectory=%h/source/ollama-balance-monitor
ExecStart=%h/source/ollama-balance-monitor/.venv/bin/python %h/source/ollama-balance-monitor/src/main.py
Restart=on-failure
```

Then reload and restart:

```bash
systemctl --user daemon-reload
systemctl --user restart ollama-balance.service
```

## Project structure

```text
ollama-balance-monitor/
├── README.md
├── build.bat
├── update-api-key.bat
├── assets/
│   └── ollama.ico
└── src/
    ├── main.py
    ├── requirements.txt
    └── set-api-key.ps1
```

## ToDo

- **_Initial build is AI-assisted, optimisation required_**
- Add plan options dropdown with built-in selection to match plan to title on hover.
- ~~Full Linux port and build - Arch will be completed first, with universal Linux support to follow.~~ Linux support added (Arch/Hyprland/Wayland tested; other distros pending feedback).
- Develop icon options further with improved UI.
- Pop-up UI improvements.

## License

MIT