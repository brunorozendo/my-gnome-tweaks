-- macOS pointer acceleration for mice under libinput.
--
-- Port of IOHIDParametricAcceleration::multiplier and
-- IOHIDPointerAccelerator::accelerate from apple-oss-distributions/IOHIDFamily
-- (IOHIDEventSystemPlugIns/IOHIDAccelerationAlgorithm.cpp, IOHIDAcceleration.cpp).
--
-- Curve values: the HIDAccelCurves entry for HIDMouseAcceleration = 45056
-- (tracking speed 0.6875), read from the Mac's IORegistry on 2026-11-04.
-- macOS assumes 400 dpi for these mice (HIDPointerResolution = 26214400).
--
-- Needs GNOME accel-profile 'flat' and speed 0, so that libinput adds nothing:
-- with those, one count emitted here moves the cursor one pixel.
-- Mutter loads this file when the session starts, so changes need a new login.

libinput:register({1})

local GAIN_LINEAR = 61604 / 65536.0
local GAIN_PARABOLIC = 46531 / 65536.0
local GAIN_CUBIC = 7864 / 65536.0
local TANGENT_LINEAR = 550502 / 65536.0
local TANGENT_ROOT = 1114112 / 65536.0

local DEVICE_SCALE = 400.0 / 67.0 -- resolution / FRAME_RATE
local CURSOR_SCALE = 96.0 / 67.0  -- kCursorScale

local function polynomial(v)
	return GAIN_LINEAR * v + (GAIN_PARABOLIC * v) ^ 2 + (GAIN_CUBIC * v) ^ 3
end

local M0 = GAIN_LINEAR
	+ 2 * TANGENT_LINEAR * GAIN_PARABOLIC ^ 2
	+ 3 * TANGENT_LINEAR ^ 2 * GAIN_CUBIC ^ 3
local B0 = polynomial(TANGENT_LINEAR) - M0 * TANGENT_LINEAR
local Y1 = M0 * TANGENT_ROOT + B0
local M1 = 2 * Y1 * M0
local B1 = Y1 ^ 2 - M1 * TANGENT_ROOT

-- Cursor pixels per device count for a frame moving `velocity` counts.
local function gain(velocity)
	local v = velocity / DEVICE_SCALE
	local y
	if v <= TANGENT_LINEAR then
		y = polynomial(v)
	elseif v <= TANGENT_ROOT then
		y = M0 * v + B0
	else
		y = math.sqrt(M1 * v + B1)
	end
	return y * CURSOR_SCALE / velocity
end

local function truncate(x)
	return x >= 0 and math.floor(x) or math.ceil(x)
end

libinput:connect("new-evdev-device", function(device)
	local usages = device:usages()
	if not (usages[evdev.REL_X] and usages[evdev.REL_Y]) then
		return
	end

	-- Fractions of a pixel carried to the next frame, so slow motion isn't lost.
	local rest_x, rest_y = 0.0, 0.0

	device:connect("evdev-frame", function(_, frame)
		local dx, dy = 0, 0
		for _, event in ipairs(frame) do
			if event.usage == evdev.REL_X then
				dx = event.value
			elseif event.usage == evdev.REL_Y then
				dy = event.value
			end
		end
		if dx == 0 and dy == 0 then
			return nil
		end

		-- macOS takes velocity from this report alone, with no history.
		local multiplier = gain(math.floor(math.sqrt(dx * dx + dy * dy)))
		local exact_x = dx * multiplier + rest_x
		local exact_y = dy * multiplier + rest_y
		local out_x, out_y = truncate(exact_x), truncate(exact_y)
		rest_x, rest_y = exact_x - out_x, exact_y - out_y

		local result = {}
		for _, event in ipairs(frame) do
			if event.usage == evdev.REL_X then
				if out_x ~= 0 then
					result[#result + 1] = { usage = evdev.REL_X, value = out_x }
				end
			elseif event.usage == evdev.REL_Y then
				if out_y ~= 0 then
					result[#result + 1] = { usage = evdev.REL_Y, value = out_y }
				end
			else
				result[#result + 1] = event
			end
		end
		return result
	end)
end)
