# my-gnome-tweaks

Makes the mouse and dock on Fedora + GNOME behave like my Mac's.

Tested on Fedora 44 with GNOME Shell 50.6 (Mutter 50.5) and libinput 1.31.3.

## Install

You need these extensions first, from [extensions.gnome.org](https://extensions.gnome.org):

- [Dash to Dock](https://extensions.gnome.org/extension/307/dash-to-dock/)
- [Impatience](https://extensions.gnome.org/extension/277/impatience/)

Then run this in your GNOME session, without root:

```bash
./install.sh
```

Log out and back in once, because Mutter only loads libinput plugins when the session starts. The dock settings apply right away. Until you log back in, the mouse has no acceleration and feels too fast.

## Mouse

GNOME's speed slider can't match macOS, because the two systems use differently shaped curves:

| | macOS (IOHIDFamily) | Linux (libinput default) |
|---|---|---|
| **Slowest speed** | About 0.25 px per count (assumes 400 dpi) | 1 px per count (assumes 1000 dpi); it only drops below that at very slow speeds |
| **Curve** | Rises smoothly from the first count | Flat, then a straight ramp, then a hard cap |
| **Range** | 0.25 to about 1.85 px per count | 1 to 2 px per count |
| **Speed slider** | Picks a different curve | Moves where the ramp starts, its slope and its cap |
| **Hand speed** | From that single mouse report | Averaged over recent motion |

Below about -0.67, GNOME's slider only lowers the cap, which removes acceleration completely.

[`mouse/10-macos-pointer-accel.lua`](mouse/10-macos-pointer-accel.lua) is a [libinput Lua plugin](https://wayland.freedesktop.org/libinput/doc/latest/lua-plugins.html) that applies Apple's formula to mouse motion. GNOME's `flat` profile then stops libinput from adding its own acceleration. Mutter loads the plugin from `~/.config/libinput/plugins/`, so it needs no root.

The curve values are for tracking speed 0.6875 (`HIDMouseAcceleration` = 45056). If you change your Mac's tracking speed, read the new value and copy the matching entry from [`mouse/mac-accel-curves.txt`](mouse/mac-accel-curves.txt) into the plugin:

```bash
hidutil property --get HIDMouseAcceleration
```

The same file came from this command, so it can be refreshed the same way:

```bash
ioreg -r -c AppleUserHIDEventService -l -w0 | grep -m1 '"HIDAccelCurves" = '
```

## Dock

[`dconf/dash-to-dock.ini`](dconf/dash-to-dock.ini) sets Dash to Dock to:

- Stay hidden until the pointer touches the bottom edge, with no delay or pressure needed.
- Show one dot for each running app, and use the Mac's icon size (46).
- Bring an app forward on click, with a second click doing nothing.
- Hide mounted drives.
- Keep Show Apps as the first icon. This one is on purpose and differs from my Mac.

The Mac's slide time comes from timing the real Dock, not from its setting. `autohide-time-modifier` is 0.5, but the slide takes about 110 ms in and 120 ms out. `animation-time` here is 0.23 because Impatience halves animation times ([`dconf/impatience.ini`](dconf/impatience.ini)), which gives about 115 ms. If you disable Impatience, change it to 0.115.

`dash-to-dock.ini` is a snapshot of one machine, so `preferred-monitor-by-connector` may need changing on yours.

### What can't match macOS

- A click brings forward only the app's most recent window, while macOS brings all of them.
- Minimized windows don't get their own tile.
- There's no Downloads stack and no bounce when an app launches.
- The slide-in starts fast, while the Mac eases in and out. Dash to Dock has no setting for this curve.

## Tools

| File | What it does | Where to run it |
|---|---|---|
| [`tools/test-mouse-plugin.py`](tools/test-mouse-plugin.py) | Runs the plugin on real Lua 5.4 with libinput's API simulated, and checks its output against the macOS formula | Linux |
| [`tools/dock-slide-probe.swift`](tools/dock-slide-probe.swift) | Times the Dock's slide. It moves the pointer to the bottom edge and back for about 3 seconds, without clicking | macOS |
| [`tools/compare-mouse-curves.py`](tools/compare-mouse-curves.py) | Prints macOS and libinput curves side by side, including the `MOUSE_DPI` approach I didn't use | Anywhere |

```bash
python3 tools/test-mouse-plugin.py mouse/10-macos-pointer-accel.lua
```

```bash
swiftc -O tools/dock-slide-probe.swift -o /tmp/dock-slide-probe && /tmp/dock-slide-probe
```

## Undo

Run this, then log out and back in. It also clears any other changes you've made to these settings:

```bash
rm ~/.config/libinput/plugins/10-macos-pointer-accel.lua
dconf reset -f /org/gnome/shell/extensions/dash-to-dock/
dconf reset -f /org/gnome/shell/extensions/net/gfxmonk/impatience/
dconf reset -f /org/gnome/desktop/peripherals/mouse/
dconf reset -f /org/gnome/desktop/peripherals/trackball/
```
