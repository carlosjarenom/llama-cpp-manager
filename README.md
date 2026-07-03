# llama.cpp Model Manager

A **Tauri 2** graphical application for managing **Qwen3.6-27B** and **Qwen3.6-35B** models running with `llama.cpp` on Arch Linux.

Control systemd user services: start, stop, restart, and view logs — all from a native GNOME-style desktop app. No terminal commands needed.

## Features

- **▶ Start** — Start the selected model's systemd service
- **⏹ Stop** — Stop the selected model's service
- **↻ Restart** — Reload + restart (with visual feedback)
- **📄 Log** — Open the service journal in a terminal emulator
- **Auto-refresh** — Status updates every 5 seconds
- **Dark GNOME theme** — Adwaita-dark with color-coded cards
- **Native binary** — ~13MB, no Python/runtime dependencies

## Supported Models

| Model | Service | Port | VRAM |
|---|---|---|---|
| Qwen3.6-27B | `llama-cpp-server` | 8002 | ~16 GB |
| Qwen3.6-35B | `llama-cpp-server-35b` | 8003 | ~22 GB |

## Installation

### From AUR (recommended on Arch)

```bash
yay -S llama-cpp-manager
# or
paru -S llama-cpp-manager
```

### Manual installation

```bash
# Build the Tauri app
cd llama-cpp-gui/src-tauri
cargo tauri build

# Copy binary
sudo cp ../target/release/bundle/linux/deb/llama-manager /usr/bin/llama-manager

# Copy desktop entry
sudo cp ../llama-cpp-manager.desktop /usr/share/applications/
```

### From App Launcher

After installation, press the **Super (Windows) key** and search for **"llama.cpp Model Manager"**.

## Requirements

- **Arch Linux** (or derivative)
- `systemd` (user services for both `llama-cpp-server` and `llama-cpp-server-35b`)
- `gtk3`
- `python-gobject`
- A terminal emulator (`gnome-terminal`, `kitty`, or `alacritty`) for log viewing

### Systemd services

Both services must exist in `~/.config/systemd/user/`:
- `llama-cpp-server.service`
- `llama-cpp-server-35b.service`

Enable with:
```bash
systemctl --user enable --now llama-cpp-server
```

## Project Structure

```
llama-cpp-gui/
├── llama-cpp-manager.desktop   # Desktop entry
├── PKGBUILD                    # Arch Linux AUR package
├── src/
│   ├── index.html              # Main page
│   ├── style.css               # GNOME dark theme
│   └── app.js                  # Frontend logic
└── src-tauri/
    ├── Cargo.toml              # Rust dependencies
    ├── tauri.conf.json         # Tauri config
    ├── capabilities/           # Permission caps
    └── src/
        └── main.rs             # Rust backend (systemctl commands)
```

## Building from Source

```bash
# Prerequisites
sudo pacman -S rust cargo gtk3 python-gobject

# Build
cd src-tauri
cargo tauri build

# Binary location
# target/release/bundle/linux/deb/llama-manager
```

## Tech Stack

| Layer | Technology |
|---|---|
| UI Framework | Tauri 2 (Rust) |
| Frontend | Vanilla HTML/CSS/JS |
| Backend | Rust + `systemctl` |
| Packaging | Arch PKGBUILD + Tauri Linux bundles |

## Customization

Edit `src/style.css` for colors:

```css
.btn-start { background: #1db954; }      /* green */
.btn-stop { background: #e0245e; }       /* red */
.btn-restart { background: #4a90d9; }    /* blue */
```

## License

MIT
