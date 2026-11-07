#!/usr/bin/env bash
# Applies the mouse and dock tweaks for the current user. Needs no root.
# Existing values for the keys in dconf/ are overwritten; other keys are left alone.
set -euo pipefail
cd "$(dirname "$0")"

install -Dm644 mouse/10-macos-pointer-accel.lua \
	"$HOME/.config/libinput/plugins/10-macos-pointer-accel.lua"

dconf load /org/gnome/desktop/peripherals/mouse/ < dconf/mouse.ini
dconf load /org/gnome/desktop/peripherals/trackball/ < dconf/trackball.ini
dconf load /org/gnome/shell/extensions/dash-to-dock/ < dconf/dash-to-dock.ini

echo "Done. Log out and back in once so Mutter loads the mouse plugin."
