"""Run the plugin on the box's real liblua 5.4, in libinput's sandbox, with a stubbed API."""
import ctypes
import math
import os
import sys
import tempfile

plugin_path = sys.argv[1]
out_path = tempfile.mktemp()

DRIVER = r"""
local plugin_path, out_path = ...
local evdev = { REL_X = 0x20000, REL_Y = 0x20001, REL_WHEEL = 0x20008, BTN_LEFT = 0x10110, KEY_A = 0x1001e }
local new_device
local libinput = {
  register = function(_, versions) assert(versions[1] == 1); return 1 end,
  connect = function(_, name, fn) assert(name == "new-evdev-device"); new_device = fn end,
}
-- Only what libinput's plugin sandbox exposes.
local env = { assert=assert, error=error, ipairs=ipairs, next=next, pairs=pairs, tonumber=tonumber,
  pcall=pcall, select=select, print=print, tostring=tostring, type=type, xpcall=xpcall,
  table=table, string=string, math=math, _VERSION=_VERSION, libinput=libinput, evdev=evdev }
local fh = assert(io.open(plugin_path)); local src = fh:read("a"); fh:close()
assert(load(src, "plugin", "t", env))()
assert(new_device, "plugin did not connect")

local function make(usages)
  local d = { cb = nil }
  function d:usages() return usages end
  function d:connect(name, fn) assert(name == "evdev-frame"); self.cb = fn end
  new_device(d)
  return d
end
local mouse = { [evdev.REL_X]=true, [evdev.REL_Y]=true, [evdev.BTN_LEFT]=true }

local out = assert(io.open(out_path, "w"))
-- 1. gain per report size, both directions and diagonal
for _, n in ipairs({1,2,3,5,8,12,20,40,60,80,100,143,200}) do
  for _, sign in ipairs({1,-1}) do
    local d = make(mouse); local total, frames = 0, 4000
    for _ = 1, frames do
      local r = d.cb(d, { { usage = evdev.REL_X, value = sign * n } })
      for _, e in ipairs(r) do
        assert(math.type(e.value) == "integer", "non-integer output")
        assert(e.usage == evdev.REL_X)
        total = total + e.value
      end
    end
    out:write(string.format("gain %d %d %.6f\n", n, sign, total / (sign * n * frames)))
  end
end
do
  local d = make(mouse); local x, y = 0, 0
  for _ = 1, 4000 do
    for _, e in ipairs(d.cb(d, { { usage = evdev.REL_X, value = 3 }, { usage = evdev.REL_Y, value = -4 } })) do
      if e.usage == evdev.REL_X then x = x + e.value else y = y + e.value end
    end
  end
  out:write(string.format("diag %.6f %.6f\n", x / (3 * 4000), y / (-4 * 4000)))
end
-- 2. buttons survive; wheel-only frames are left alone; sub-pixel frames drop only motion
do
  local d = make(mouse)
  local r = d.cb(d, { { usage = evdev.REL_X, value = 1 }, { usage = evdev.BTN_LEFT, value = 1 } })
  out:write(string.format("button_kept %d %d\n", #r, r[#r].usage == evdev.BTN_LEFT and r[#r].value or -1))
  out:write(string.format("wheel_untouched %s\n", tostring(d.cb(d, { { usage = evdev.REL_WHEEL, value = 1 } }))))
  out:write(string.format("subpixel_frame_len %d\n", #d.cb(make(mouse), { { usage = evdev.REL_X, value = 1 } })))
end
-- 3. devices without relative motion are not hooked
do
  local k = make({ [evdev.KEY_A] = true })
  out:write(string.format("keyboard_hooked %s\n", tostring(k.cb ~= nil)))
end
out:close()
"""

lua = ctypes.CDLL("/usr/lib64/liblua-5.4.so")
lua.luaL_newstate.restype = ctypes.c_void_p
lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pushstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
lua.lua_tolstring.restype = ctypes.c_char_p

L = lua.luaL_newstate()
lua.luaL_openlibs(L)
assert lua.luaL_loadstring(L, DRIVER.encode()) == 0, lua.lua_tolstring(L, -1, None)
lua.lua_pushstring(L, plugin_path.encode())
lua.lua_pushstring(L, out_path.encode())
if lua.lua_pcallk(L, 2, 0, 0, 0, None) != 0:
    sys.exit("LUA ERROR: " + lua.lua_tolstring(L, -1, None).decode())

# Independent expected values: same formula, from the Apple source, in Python.
GL, GP, GC, T0, T1 = 61604 / 65536, 46531 / 65536, 7864 / 65536, 550502 / 65536, 1114112 / 65536
y0 = GL * T0 + (GP * T0) ** 2 + (GC * T0) ** 3
m0 = GL + 2 * T0 * GP ** 2 + 3 * T0 ** 2 * GC ** 3
b0 = y0 - m0 * T0
y1 = m0 * T1 + b0
m1 = 2 * y1 * m0
b1 = y1 ** 2 - m1 * T1


def mac(n):
    v = n / (400 / 67)
    y = GL * v + (GP * v) ** 2 + (GC * v) ** 3 if v <= T0 else (m0 * v + b0 if v <= T1 else math.sqrt(m1 * v + b1))
    return y * (96 / 67) / n


fail = 0
for line in open(out_path):
    p = line.split()
    if p[0] == "gain":
        n, sign, got = int(p[1]), int(p[2]), float(p[3])
        exp = mac(n)
        ok = abs(got - exp) <= 1 / (n * 4000) + 1e-6
        fail += not ok
        if sign == 1:
            print(f"counts/report {n:>3}: plugin {got:.4f} px/count, macOS {exp:.4f} {'ok' if ok else 'FAIL'}")
    elif p[0] == "diag":
        exp = mac(5)
        ok = abs(float(p[1]) - exp) < 1e-3 and abs(float(p[2]) - exp) < 1e-3
        fail += not ok
        print(f"diagonal 3,-4: x {p[1]} y {p[2]}, macOS {exp:.4f} {'ok' if ok else 'FAIL'}")
    else:
        print(line.strip())
os.unlink(out_path)
print("RESULT:", "FAIL" if fail else "all gain checks passed")
sys.exit(1 if fail else 0)
