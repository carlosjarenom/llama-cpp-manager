#!/usr/bin/env python3
"""
llama-cpp-model-manager — Gestor de modelos Qwen con llama.cpp
GTK3 + Adwaita (GNOME HIG) — Arch Linux

Servicios gestionados:
  llama-cpp-server      → Qwen3.6-27B  (puerto 8002)
  llama-cpp-server-35b  → Qwen3.6-35B  (puerto 8003)
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk,Gio, Pango, GLib, GdkPixbuf
import subprocess, re, sys, os

# ─── Servicios ────────────────────────────────────────────────────────────
SERVICES = {
    "27b": {
        "name": "Qwen3.6-27B",
        "service": "llama-cpp-server",
        "port": "8002",
        "icon": "🧠",
        "color": (0.0, 0.6, 0.9),       # azul
        "css_id": "card-27b",
    },
    "35b": {
        "name": "Qwen3.6-35B",
        "service": "llama-cpp-server-35b",
        "port": "8003",
        "icon": "🧠",
        "color": (0.9, 0.4, 0.0),       # naranja
        "css_id": "card-35b",
    },
}

def run(cmd: list[str], timeout: int = 5) -> tuple[int, str, str]:
    """Ejecutar comando y devolver (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        return -1, e.stdout or "", e.stderr or ""
    except FileNotFoundError:
        return -1, "", "systemctl no encontrado"

def service_status(service: str) -> str:
    """Devuelve el estado legible de un servicio systemd."""
    rc, out, _ = run(["systemctl", "--user", "is-active", service])
    if rc == 0:
        # Está activo, ver si está en modo auto-restart o no
        rc2, out2, _ = run(["systemctl", "--user", "show",
                             "-p", "SubState,ExecMainStatus", "--value", service])
        sub = out2.strip()
        if sub == "running":
            return "active"
        elif sub == "exited":
            # Ejecutado y salió limpio — técnicamente active (exited)
            return "active"
        return "active"
    else:
        rc3, out3, _ = run(["systemctl", "--user", "is-enabled", service])
        if rc3 == 0:
            return "inactive"
        return "not-found"

def format_status_text(service: str, st: str) -> str:
    """Texto descriptivo del estado."""
    if st == "active":
        # Intentar obtener PID
        rc, out, _ = run(["systemctl", "--user", "show",
                           "-p", "MainPID,SubState", "--value", service])
        pid = out.strip().split("\n")[0].replace("MainPID=", "")
        sub = out.strip().split("\n")[-1].replace("SubState=", "") if "\n" in out else ""
        if pid and pid != "0":
            return f"✅ Ejecutando (PID {pid})"
        return "✅ Ejecutando"
    elif st == "inactive":
        return "⏹️ Detenido"
    return "❌ No encontrado"

# ─── Widget: Tarjeta de servicio ──────────────────────────────────────────
class ServiceCard(Gtk.Box):
    """Tarjeta GTK3 con estilo Adwaita para un servicio."""

    def __init__(self, key: str, svc: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.key = key
        self.svc = svc
        self.status_label = None
        self.log_label = None

        # Contenedor principal con borde
        self.frame = Gtk.Frame()
        self.frame.set_border_width(0)

        # Caja interior
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(1)
        box.set_margin_end(1)
        box.set_margin_top(1)
        box.set_margin_bottom(1)
        self.frame.add(box)

        # Cabecera con nombre y puerto
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_start(16)
        header.set_margin_end(16)
        header.set_margin_top(12)
        header.set_margin_bottom(8)

        icon_label = Gtk.Label(label=svc["icon"])
        icon_label.get_style_context().add_class("large-icon")
        icon_label.set_halign(Gtk.Align.START)
        icon_label.set_size_request(40, -1)

        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_label = Gtk.Label(label=svc["name"])
        name_label.get_style_context().add_class("body-heading")
        name_label.set_halign(Gtk.Align.START)

        port_label = Gtk.Label(label=f"Puerto {svc['port']}")
        port_label.get_style_context().add_class("dim-label")
        port_label.set_halign(Gtk.Align.START)

        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(port_label, False, False, 0)

        header.pack_start(icon_label, False, False, 0)
        header.pack_start(name_box, True, True, 0)
        box.pack_start(header, False, False, 0)

        # Indicador de estado
        self.status_label = Gtk.Label(label="Cargando…")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_start(16)
        self.status_label.set_margin_bottom(12)
        self.status_label.set_selectable(True)
        self.update_status()
        box.pack_start(self.status_label, False, False, 0)

        # Separador
        sep = Gtk.Separator()
        sep.set_margin_start(16)
        sep.set_margin_end(16)
        box.pack_start(sep, False, False, 0)

        # Botones de acción
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_margin_start(16)
        btn_box.set_margin_end(16)
        btn_box.set_margin_top(10)
        btn_box.set_margin_bottom(14)

        self.btn_start = self._btn("▶ Iniciar", "success")
        self.btn_stop = self._btn("⏹ Detener", "destructive-action")
        self.btn_restart = self._btn("↻ Reiniciar", "primary-action")
        self.btn_log = Gtk.Button(label="📄 Log")
        self.btn_log.get_style_context().add_class("flat")
        self.btn_start.connect("clicked", self._on_start)
        self.btn_stop.connect("clicked", self._on_stop)
        self.btn_restart.connect("clicked", self._on_restart)
        self.btn_log.connect("clicked", self._on_log)

        btn_box.pack_start(self.btn_start, True, False, 0)
        btn_box.pack_start(self.btn_stop, True, False, 0)
        btn_box.pack_start(self.btn_restart, True, False, 0)
        btn_box.pack_start(self.btn_log, False, False, 0)
        box.pack_start(btn_box, False, False, 0)

        self.pack_start(self.frame, True, True, 0)

    def _btn(self, label: str, css_class: str) -> Gtk.Button:
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class(css_class)
        btn.get_style_context().add_class("flat")
        # Hacer que los botones principales tengan fondo
        btn.set_hexpand(True)
        return btn

    def update_status(self):
        st = service_status(self.svc["service"])
        text = format_status_text(self.svc["service"], st)
        self.status_label.set_label(text)

        # Habilitar/deshabilitar botones
        if st == "active":
            self.btn_start.set_sensitive(False)
            self.btn_start.get_style_context().add_class("sensitive-false")
            self.btn_stop.set_sensitive(True)
            self.btn_stop.get_style_context().remove_class("sensitive-false")
            self.btn_restart.set_sensitive(True)
        elif st == "inactive":
            self.btn_start.set_sensitive(True)
            self.btn_start.get_style_context().remove_class("sensitive-false")
            self.btn_stop.set_sensitive(False)
            self.btn_stop.get_style_context().add_class("sensitive-false")
            self.btn_restart.set_sensitive(True)
        else:
            self.btn_start.set_sensitive(False)
            self.btn_stop.set_sensitive(False)
            self.btn_restart.set_sensitive(False)

        self.st = st

    def _execute(self, action: str):
        """Ejecutar acción del servicio."""
        svc = self.svc["service"]
        if action == "start":
            run(["systemctl", "--user", "start", svc])
        elif action == "stop":
            run(["systemctl", "--user", "stop", svc])
        elif action == "restart":
            run(["systemctl", "--user", "daemon-reload"])
            run(["systemctl", "--user", "restart", svc])
        elif action == "status":
            self.update_status()
            return
        # Actualizar estado con retardo para dar tiempo a systemd
        GLib.timeout_add_seconds(1, self.update_status)

    def _on_start(self, _btn):
        self._execute("start")
        self._execute("status")  # refresco inmediato

    def _on_stop(self, _btn):
        self._execute("stop")
        self._execute("status")

    def _on_restart(self, _btn):
        self.btn_restart.set_label("↻ Reiniciando…")
        self.btn_restart.set_sensitive(False)
        self._execute("restart")
        self.update_status()
        GLib.timeout_add_seconds(3, self._on_restart_done)

    def _on_restart_done(self):
        self.btn_restart.set_label("↻ Reiniciar")
        self.btn_restart.set_sensitive(True)
        self.update_status()

    def _on_log(self, _btn):
        """Abrir journal del servicio en un terminal."""
        svc = self.svc["service"]
        # Intentar abrir gnome-terminal o xterm
        for term in ["gnome-terminal", "kitty", "alacritty", "xterm"]:
            if os.path.isfile(f"/usr/bin/{term}") or os.path.isfile(f"/usr/bin/{term}.desktop"):
                subprocess.Popen(["/usr/bin/" + term, "bash", "-c",
                    f"journalctl --user -u {svc} -f --no-pager; exec bash"])
                return
        # Fallback
        print(f"\n=== Log de {svc} ===")
        subprocess.run(["journalctl", "--user", "-u", svc, "-n", "50", "--no-pager"], check=False)

# ─── Ventana principal ─────────────────────────────────────────────────────
class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="llama.cpp Model Manager")
        self.set_default_size(680, 480)
        self.set_icon_name("accessories-text-editor")

        # CSS custom
        self._setup_css()

        # Contenedor
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # Header
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("")
        header.pack_end(Gtk.Label(label="🦙 llama.cpp Model Manager"))
        vbox.pack_start(header, False, False, 0)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(16)

        info = Gtk.Label()
        info.set_markup(
            '<span size="small" weight="normal" alpha="0.7">'
            'Gestiona los servicios de Qwen con llama.cpp.<br/>'
            'Haz clic en los botones para controlar cada modelo.'
            '</span>'
        )
        info.set_halign(Gtk.Align.START)
        info.set_selectable(False)
        content.pack_start(info, False, False, 0)

        # Tarjetas
        self.cards = {}
        for key, svc in SERVICES.items():
            card = ServiceCard(key, svc)
            self.cards[key] = card
            content.pack_start(card, True, True, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.NONE)
        scroll.add(content)
        vbox.pack_start(scroll, True, True, 0)

        # Barra inferior con refresh
        bar = Gtk.Statusbar()
        vbox.pack_start(bar, False, False, 0)
        self.bar = bar

        # Actualizar estados iniciales
        self._refresh_all()
        GLib.timeout_add_seconds(5, self._refresh_all)

    def _setup_css(self):
        css = """
        window { background-color: #1a1a2e; color: #d4d4d4; }

        .body-heading {
            font-size: 14px;
            font-weight: 600;
            color: #ffffff;
        }

        .large-icon {
            font-size: 28px;
        }

        .dim-label {
            color: #999999;
            font-size: 11px;
        }

        .flat {
            background: transparent;
            border: none;
            box-shadow: none;
        }

        /* Botón Iniciar */
        .success {
            background-color: #1db954;
            color: #ffffff;
            border-radius: 6px;
            font-size: 12px;
            padding: 4px 12px;
        }
        .success:hover {
            background-color: #1ed760;
        }

        /* Botón Detener */
        .destructive-action {
            background-color: #e0245e;
            color: #ffffff;
            border-radius: 6px;
            font-size: 12px;
            padding: 4px 12px;
        }
        .destructive-action:hover {
            background-color: #ef4476;
        }

        /* Botón Reiniciar */
        .primary-action {
            background-color: #4a90d9;
            color: #ffffff;
            border-radius: 6px;
            font-size: 12px;
            padding: 4px 12px;
        }
        .primary-action:hover {
            background-color: #5ba0e9;
        }

        .sensitive-false {
            opacity: 0.3;
        }

        .card-frame {
            border-radius: 8px;
            border: 1px solid #333355;
            background-color: #16213e;
        }

        headerbar {
            background-color: #0f0f23;
            color: #ffffff;
        }

        statusbar {
            background-color: #0f0f23;
            color: #666;
            font-size: 10px;
            padding: 2px 8px;
        }

        GtkSeparator {
            border-color: #2a2a4a;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _refresh_all(self):
        for card in self.cards.values():
            card.update_status()
        self.bar.pop_all(0)
        self.bar.push(0, "Última actualización: " +
                     __import__("datetime").datetime.now().strftime("%H:%M:%S"))
        return True  # seguir ejecutando

# ─── Main ─────────────────────────────────────────────────────────────────
def main():
    if not os.access(os.path.expanduser("~/.config/systemd/user/llama-cpp-server.service"),
                      os.R_OK) and \
       not os.access(os.path.expanduser("~/.config/systemd/user/llama-cpp-server-35b.service"),
                      os.R_OK):
        print("⚠️ No se encontraron los servicios de llama.cpp.")
        print("   Asegúrate de que están creados en ~/.config/systemd/user/")
        sys.exit(1)

    win = MainWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
