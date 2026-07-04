# llama.cpp Model Manager

Una aplicación gráfica **Tauri 2** para gestionar los modelos **Qwen3.6-27B** y **Qwen3.6-35B** que corren con `llama.cpp` en Arch Linux.

Controla los servicios de systemd de usuario: iniciar, parar, reiniciar y ver logs — todo desde una app de escritorio nativa estilo GNOME. Sin tocar terminal.

## Funcionalidades

- **▶ Iniciar** — Arranca el servicio systemd del modelo seleccionado
- **⏹ Parar** — Para el servicio del modelo
- **↻ Reiniciar** — daemon-reload + restart (con feedback visual)
- **📋 Logs** — Muestra el journal del servicio integrado en la app
- **Auto-refresco** — Estado actualizado cada 5 segundos
- **Tema oscuro** — Estilo dark con tarjetas por colores
- **Binario nativo** — ~13MB, sin dependencias de Python/runtime

## Modelos Soportados

| Modelo | Servicio | Puerto | VRAM |
|---|---|---|---|
| Qwen3.6-27B | `llama-cpp-server` | 8002 | ~16 GB |
| Qwen3.6-35B | `llama-cpp-server-35b` | 8003 | ~22 GB |

## Instalación

### Desde AUR (recomendado en Arch)

```bash
yay -S llama-cpp-manager
# o
paru -S llama-cpp-manager
```

### Instalación manual

```bash
# Compilar la app Tauri
cd llama-cpp-gui/src-tauri
cargo tauri build

# Copiar binario
sudo cp ../target/release/bundle/linux/deb/llama-manager /usr/bin/llama-manager

# Copiar entrada de escritorio
sudo cp ../llama-cpp-manager.desktop /usr/share/applications/
```

### Desde el Lanzador de Apps

Tras la instalación, pulsa la tecla **Super (Windows)** y busca **"llama.cpp Model Manager"**.

## Requisitos

- **Arch Linux** (o derivado)
- `systemd` (servicios de usuario para `llama-cpp-server` y `llama-cpp-server-35b`)
- `gtk3`
- Un emulador de terminal (`gnome-terminal`, `kitty`, o `alacritty`) para ver logs

### Servicios de systemd

Ambos servicios deben existir en `~/.config/systemd/user/`:
- `llama-cpp-server.service`
- `llama-cpp-server-35b.service`

Activar con:
```bash
systemctl --user enable --now llama-cpp-server
```

## Estructura del Proyecto

```
llama-cpp-gui/
├── llama-cpp-manager.desktop   # Entrada de escritorio
├── PKGBUILD                    # Paquete AUR para Arch
├── src/
│   ├── index.html              # Página principal
│   ├── style.css               # Tema oscuro
│   └── app.js                  # Lógica del frontend
└── src-tauri/
    ├── Cargo.toml              # Dependencias Rust
    ├── tauri.conf.json         # Configuración Tauri
    ├── capabilities/           # Permisos
    └── src/
        └── main.rs             # Backend Rust (comandos systemctl)
```

## Compilar desde el Código Fuente

```bash
# Prerrequisitos
sudo pacman -S rust cargo gtk3 python-gobject

# Compilar
cd src-tauri
cargo tauri build

# Ubicación del binario
# target/release/bundle/linux/deb/llama-manager
```

## Tecnologías

| Capa | Tecnología |
|---|---|
| Framework UI | Tauri 2 (Rust) |
| Frontend | HTML/CSS/JS vanilla |
| Backend | Rust + `systemctl` |
| Empaquetado | PKGBUILD Arch + bundles de Tauri Linux |

## Personalización

Edita `src/style.css` para los colores:

```css
.btn-start { background: #1db954; }      /* verde */
.btn-stop { background: #e0245e; }       /* rojo */
.btn-restart { background: #4a90d9; }    /* azul */
```

## Licencia

MIT
