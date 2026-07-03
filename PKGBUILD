# Maintainer: Carlos Jareño <carlos@jareno.com>
# PKGBUILD for llama-cpp-manager (AUR)

pkgname=llama-cpp-manager
pkgver=0.1.0
pkgrel=1
pkgdesc="GUI for managing llama.cpp Qwen model services on Arch Linux"
arch=('x86_64')
url="https://github.com/carlosjarenom/llama-cpp-manager"
license=('MIT')
depends=('gtk3' 'python-gobject')
makedepends=('python')
optdepends=(
  'gnome-terminal: for log viewing'
  'kitty: alternative terminal emulator'
  'alacritty: alternative terminal emulator'
)
provides=('$pkgname')
conflicts=('$pkgname')

package() {
  # Install binary (assumes pre-built)
  install -Dm755 "$srcdir/llama-manager" "$pkgdir/usr/bin/llama-manager"

  # Install desktop entry
  install -Dm644 "$srcdir/llama-cpp-manager.desktop" \
    "$pkgdir/usr/share/applications/llama-cpp-manager.desktop"

  # Install icons (placeholder - replace with real icons)
  install -Dm644 "$srcdir/icon.png" \
    "$pkgdir/usr/share/icons/hicolor/128x128/apps/llama-manager.png"
}

# Build instructions:
# 1. Build the Tauri app first:
#    cd src-tauri && cargo tauri build
# 2. Copy the built binary to this PKGBUILD's src/
# 3. Then: makepkg -si
