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
- Windows, Linux, or macOS
- `OLLAMA_API_KEY` environment variable

## Installation

Clone the repository:

```bash
git clone https://github.com/jakeewart/ollama-balance-monitor.git
cd ollama-balance-monitor
```

Install dependencies:

```bash
pip install -r src/requirements.txt
```

## Usage

Run directly from source:

```bash
python src/main.py
```

On Windows, you can also use `pythonw` to avoid a console window:

```bash
pythonw src/main.py
```

The tray icon refreshes every 10 seconds by default. Right-click the icon to refresh manually, toggle launch on boot, or quit.

## Setting your API key

You need to set `OLLAMA_API_KEY` as an environment variable. The easiest way on Windows is to run the provided helper script.

### Windows

Double-click:

```text
obb-update-api-key.bat
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

```bash
export OLLAMA_API_KEY="your-api-key-here"
```

Add that line to your `~/.bashrc` or `~/.zshrc` to make it persistent.

## Building a standalone Windows executable

On Windows, run:

```bash
obb-build.bat
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
- You can update your key later by running `obb-update-api-key.bat`

## Launch on boot (Windows)

Right-click the tray icon and select **Launch on boot** to add or remove the app from your startup registry. The app will start automatically the next time you log in.

## Project structure

```text
ollama-balance-monitor/
├── README.md
├── obb-build.bat
├── obb-update-api-key.bat
├── assets/
│   └── ollama.ico
└── src/
    ├── main.py
    ├── requirements.txt
    └── set-api-key.ps1
```

## License

MIT