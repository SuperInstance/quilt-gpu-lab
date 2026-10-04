--!strict
--[[ Roblox stub: this module runs under plain luau with no Roblox globals. ]]

export type Edge = {dst: number, weight: number}

export type Cell = {
	id: number,
	name: string,
	dials: {number},
	edges: {Edge},
	act: number,
	bound: boolean,
}

export type Registry = {
	cells: {[string]: Cell},
	byName: {[string]: number},
	order: {number},
	nextId: number,
	count: (self: Registry) -> number,
}

local NDIALS = 16
local EDGE_CAP = 8
local DIAL_MIN = 0
local DIAL_MAX = 1
local DEFAULT_LINK_W = 0.5
local DEFAULT_LEAK = 0.1

local function clamp01(v: number): number
	if v ~= v then -- NaN
		return 0.0
	end
	if v < 0 then return 0.0 end
	if v > 1 then return 1.0 end
	return v
end

local function newRegistry(): Registry
	local reg: Registry = {
		cells = {},
		byName = {},
		order = {},
		nextId = 1,
	}
	-- count exposed as a method so reg.count(reg) works; also CellAPI.count.
	reg.count = function(self: Registry): number
		return #self.order
	end
	return reg
end

local function qm_bind(reg: Registry, name: string): Cell
	local existingId = reg.byName[name]
	if existingId ~= nil then
		return reg.cells[tostring(existingId)]
	end
	local id = reg.nextId
	local cell: Cell = {
		id = id,
		name = name,
		dials = {},
		edges = {},
		act = 0.0,
		bound = true,
	}
	for i = 1, NDIALS do
		cell.dials[i] = 0.0
	end
	reg.cells[tostring(id)] = cell
	reg.byName[name] = id
	reg.order[#reg.order + 1] = id
	reg.nextId = id + 1
	return cell
end

local function qm_link(reg: Registry, srcId: number, dstId: number, weight: number?): Edge?
	local dst = reg.cells[tostring(dstId)]
	local src = reg.cells[tostring(srcId)]
	if dst == nil or src == nil then return nil end
	local w = if weight ~= nil then clamp01(weight) else DEFAULT_LINK_W
	for _, edge in ipairs(dst.edges) do
		if edge.dst == srcId then
			edge.weight = w
			return edge
		end
	end
	if #dst.edges >= EDGE_CAP then
		local minIdx = 1
		local minW = dst.edges[1].weight
		for i = 2, #dst.edges do
			if dst.edges[i].weight < minW then
				minW = dst.edges[i].weight
				minIdx = i
			end
		end
		dst.edges[minIdx] = {dst = srcId, weight = w}
		return dst.edges[minIdx]
	end
	local edge: Edge = {dst = srcId, weight = w}
	dst.edges[#dst.edges + 1] = edge
	return edge
end

local function getCell(reg: Registry, id: number): Cell?
	return reg.cells[tostring(id)]
end

local function getCellByName(reg: Registry, name: string): Cell?
	local id = reg.byName[name]
	if id == nil then return nil end
	return reg.cells[tostring(id)]
end

local function setDial(cell: Cell, addr: number, value: number): number?
	if math.floor(addr) ~= addr then return nil end
	if addr < DIAL_MIN or addr > NDIALS - 1 then return nil end
	local v = clamp01(value)
	cell.dials[addr + 1] = v
	return v
end

local function getDial(cell: Cell, addr: number): number?
	if math.floor(addr) ~= addr then return nil end
	if addr < DIAL_MIN or addr > NDIALS - 1 then return nil end
	return cell.dials[addr + 1]
end

local function qm_effect(reg: Registry, srcId: number, dstId: number, activation: number): {delivered: boolean, weight: number, applied: number}
	local dst = reg.cells[tostring(dstId)]
	if dst == nil then return {delivered = false, weight = 0, applied = 0} end
	local src = reg.cells[tostring(srcId)]
	if src == nil then return {delivered = false, weight = 0, applied = 0} end
	local edge: Edge? = nil
	for _, e in ipairs(dst.edges) do
		if e.dst == srcId then edge = e; break end
	end
	if edge == nil then return {delivered = false, weight = 0, applied = 0} end
	local applied = clamp01(activation)
	dst.act = clamp01(dst.act + edge.weight * applied)
	return {delivered = true, weight = edge.weight, applied = applied}
end

local function qm_tick(cell: Cell, leak: number?): {edges: number, act: number}
	local l = if leak ~= nil then clamp01(leak) else DEFAULT_LEAK
	for _, edge in ipairs(cell.edges) do
		edge.weight = clamp01(edge.weight * (1 - l))
	end
	cell.act = clamp01(cell.act * (1 - l))
	return {edges = #cell.edges, act = cell.act}
end

local function qm_view(reg: Registry, id: number, kind: number, arg: number?): number?
	local cell = reg.cells[tostring(id)]
	if cell == nil then return nil end
	if kind == 0 then
		return cell.act
	elseif kind == 1 then
		local s = 0.0
		for _, e in ipairs(cell.edges) do s = s + e.weight end
		return clamp01(s)
	elseif kind == 2 then
		return getDial(cell, (arg or 0))
	end
	return nil
end

local CellAPI = {
	clamp01 = clamp01,
	newRegistry = newRegistry,
	qm_bind = qm_bind,
	qm_link = qm_link,
	getCell = getCell,
	getCellByName = getCellByName,
	setDial = setDial,
	getDial = getDial,
	qm_effect = qm_effect,
	qm_tick = qm_tick,
	qm_view = qm_view,
}
CellAPI.count = function(reg: Registry): number
	return #reg.order
end
return CellAPI
