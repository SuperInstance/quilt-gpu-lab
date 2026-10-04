-- Self-contained plain Lua 5.1 harness (no require)
-- Inlined laws mirroring the Luau module above

local function clamp(v, lo, hi)
	if v < lo then return lo end
	if v > hi then return hi end
	return v
end

local function sign(d)
	if d < 0 then return -1 end
	if d > 0 then return 1 end
	return 0
end

local function track(side, paddleY, ballY)
	local speed = side == "left" and 0.85 or 0.70
	local dead = 1.5
	local d = ballY - paddleY
	local y
	if math.abs(d) > dead then
		y = paddleY + sign(d) * math.min(speed, math.abs(d) - dead)
	else
		y = paddleY
	end
	return clamp(y, 6, 54)
end

local function wallBounce(y, vy)
	if y < 1 then
		return true, 2 - y, -vy
	elseif y > 59 then
		return true, 118 - y, -vy
	else
		return false, y, vy
	end
end

local function paddleReturn(x, vx, ballY, paddleY, side)
	local face = side == "left" and 2 or 98
	local reach = math.abs(ballY - paddleY) <= 7
	local atFace
	if side == "left" then
		atFace = (x - 1 <= face) and (x > face - 2.5)
	else
		atFace = (x + 1 >= face) and (x < face + 2.5)
	end
	local approaching
	if side == "left" then
		approaching = vx < 0
	else
		approaching = vx > 0
	end
	if atFace and reach and approaching then
		local speed = math.min(math.abs(vx) * 1.04, 2.6)
		local nvx = side == "left" and speed or -speed
		local nvy = (ballY - paddleY) * 0.12
		return true, nvx, nvy
	else
		return false, vx, vy
	end
end

local function score(x, side)
	if side == "left" and x < -3 then
		return "right"
	elseif side == "right" and x > 103 then
		return "left"
	else
		return nil
	end
end

-- Test harness
local function near(a, b)
	return math.abs(a - b) < 0.0001
end

local fails = 0
local total = 0

local function check(cond)
	total = total + 1
	if not cond then
		fails = fails + 1
		print("FAIL #" .. total)
	end
end

-- TRACK (9)
check(near(track("left", 30, 30.5), 30) and near(track("right", 30, 30.5), 30)) -- inside deadzone unchanged (both sides)
check(near(track("left", 30, 100), 30.85))   -- ramp up L=30.85
check(near(track("left", 30, -100), 29.15))  -- ramp down L=29.15
check(near(track("left", 30, 1000), 30.85))  -- saturation L=30.85
check(near(track("left", 6, 100), 6.85))     -- band edge 6 -> 6.85
check(near(track("left", 54, -100), 53.15))  -- band edge 54 -> 53.15
check(near(track("right", 30, 100), 30.70))  -- right speed 0.70 in ramp
check(near(track("left", 30, 31.5), 30))     -- |d|==1.5 -> NO move
check(near(track("left", 53.15, 100), 54.0)) -- lands exactly on 54.0

-- WALLBOUNCE (5)
local f, y, vy = wallBounce(0.5, 5)
check(f and near(y, 1.5) and vy == -5)       -- floor
f, y, vy = wallBounce(60, -3)
check(f and near(y, 58) and vy == 3)         -- ceiling
f, y, vy = wallBounce(30, 2)
check(not f and y == 30 and vy == 2)         -- neither
f, y, vy = wallBounce(1, 4)
check(not f and y == 1 and vy == 4)          -- exact y=1 no fire
f, y, vy = wallBounce(59, -2)
check(not f and y == 59 and vy == -2)        -- exact y=59 no fire

-- PADDLERETURN (5)
local fired, nvx, nvy = paddleReturn(1.5, -5, 30, 30, "left")
check(fired and near(nvx, 2.6) and near(nvy, 0))  -- fire left
fired, nvx, nvy = paddleReturn(98.5, 5, 30, 30, "right")
check(fired and near(nvx, -2.6) and near(nvy, 0)) -- fire right
fired, nvx, nvy = paddleReturn(1.5, -5, 30, 40, "left")
check(not fired)                                  -- reach miss
fired, nvx, nvy = paddleReturn(5, -5, 30, 30, "left")
check(not fired)                                  -- face miss
fired, nvx, nvy = paddleReturn(1.5, 5, 30, 30, "left")
check(not fired)                                  -- wrong direction

-- SCORE (3)
check(score(-5, "left") == "right")   -- left goal
check(score(105, "right") == "left")  -- right goal
check(score(50, "left") == nil)       -- in-play

print("PASS " .. (total - fails) .. "/" .. total)
os.exit(fails == 0 and 0 or 1)
