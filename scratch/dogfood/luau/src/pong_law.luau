--!strict

export type Side = "left" | "right"
export type BounceResult = { fired: boolean, y: number, vy: number }
export type PaddleResult = { fired: boolean, vx: number, vy: number }
export type ScoreResult = "left" | "right" | nil

local function clamp(v: number, lo: number, hi: number): number
	if v < lo then return lo end
	if v > hi then return hi end
	return v
end

local function sign(d: number): number
	if d < 0 then return -1 end
	if d > 0 then return 1 end
	return 0
end

export function track(side: Side, paddleY: number, ballY: number): number
	local speed = side == "left" and 0.85 or 0.70
	local dead = 1.5
	local d = ballY - paddleY
	local y: number
	if math.abs(d) > dead then
		y = paddleY + sign(d) * math.min(speed, math.abs(d) - dead)
	else
		y = paddleY
	end
	return clamp(y, 6, 54)
end

export function wallBounce(y: number, vy: number): BounceResult
	if y < 1 then
		return { fired = true, y = 2 - y, vy = -vy }
	elseif y > 59 then
		return { fired = true, y = 118 - y, vy = -vy }
	else
		return { fired = false, y = y, vy = vy }
	end
end

export function paddleReturn(x: number, vx: number, ballY: number, paddleY: number, side: Side): PaddleResult
	local face = side == "left" and 2 or 98
	local reach = math.abs(ballY - paddleY) <= 7
	local atFace: boolean
	if side == "left" then
		atFace = (x - 1 <= face) and (x > face - 2.5)
	else
		atFace = (x + 1 >= face) and (x < face + 2.5)
	end
	local approaching: boolean
	if side == "left" then
		approaching = vx < 0
	else
		approaching = vx > 0
	end
	if atFace and reach and approaching then
		local speed = math.min(math.abs(vx) * 1.04, 2.6)
		local nvx = side == "left" and speed or -speed
		local nvy = (ballY - paddleY) * 0.12
		return { fired = true, vx = nvx, vy = nvy }
	else
		return { fired = false, vx = vx, vy = vy }
	end
end

export function score(x: number, side: Side): ScoreResult
	if side == "left" and x < -3 then
		return "right"
	elseif side == "right" and x > 103 then
		return "left"
	else
		return nil
	end
end
