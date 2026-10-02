-- Plain Lua 5.1 self-contained mirror of src/cell_api.luau (no require, no types).
local total = 0
local fails = 0
local function eq(g, w, label)
  total = total + 1
  if g == w then return end
  fails = fails + 1
  print("FAIL " .. label .. ": got " .. tostring(g) .. " want " .. tostring(w))
end
local function near(g, w, label)
  total = total + 1
  if math.abs(g - w) < 1e-6 then return end
  fails = fails + 1
  print("FAIL " .. label .. ": got " .. tostring(g) .. " want " .. tostring(w))
end

local NDIALS = 16
local EDGE_CAP = 8
local DIAL_MIN = 0
local DIAL_MAX = 1
local DEFAULT_LINK_W = 0.5
local DEFAULT_LEAK = 0.1

local function clamp01(v)
  if v ~= v then return 0.0 end
  if v < 0 then return 0.0 end
  if v > 1 then return 1.0 end
  return v
end

local function newRegistry()
  local reg = {cells = {}, byName = {}, order = {}, nextId = 1}
  reg.count = function(self) return #self.order end
  return reg
end

local function qm_bind(reg, name)
  local existingId = reg.byName[name]
  if existingId ~= nil then return reg.cells[tostring(existingId)] end
  local id = reg.nextId
  local cell = {id = id, name = name, dials = {}, edges = {}, act = 0.0, bound = true}
  for i = 1, NDIALS do cell.dials[i] = 0.0 end
  reg.cells[tostring(id)] = cell
  reg.byName[name] = id
  reg.order[#reg.order + 1] = id
  reg.nextId = id + 1
  return cell
end

local function qm_link(reg, srcId, dstId, weight)
  local dst = reg.cells[tostring(dstId)]
  local src = reg.cells[tostring(srcId)]
  if dst == nil or src == nil then return nil end
  local w = (weight ~= nil) and clamp01(weight) or DEFAULT_LINK_W
  for _, edge in ipairs(dst.edges) do
    if edge.dst == srcId then edge.weight = w; return edge end
  end
  if #dst.edges >= EDGE_CAP then
    local minIdx = 1
    local minW = dst.edges[1].weight
    local i = 2
    while i <= #dst.edges do
      if dst.edges[i].weight < minW then minW = dst.edges[i].weight; minIdx = i end
      i = i + 1
    end
    dst.edges[minIdx] = {dst = srcId, weight = w}
    return dst.edges[minIdx]
  end
  local edge = {dst = srcId, weight = w}
  dst.edges[#dst.edges + 1] = edge
  return edge
end

local function getCell(reg, id) return reg.cells[tostring(id)] end
local function getCellByName(reg, name)
  local id = reg.byName[name]
  if id == nil then return nil end
  return reg.cells[tostring(id)]
end

local function setDial(cell, addr, value)
  if math.floor(addr) ~= addr then return nil end
  if addr < DIAL_MIN or addr > NDIALS - 1 then return nil end
  local v = clamp01(value)
  cell.dials[addr + 1] = v
  return v
end

local function getDial(cell, addr)
  if math.floor(addr) ~= addr then return nil end
  if addr < DIAL_MIN or addr > NDIALS - 1 then return nil end
  return cell.dials[addr + 1]
end

local function qm_effect(reg, srcId, dstId, activation)
  local dst = reg.cells[tostring(dstId)]
  if dst == nil then return {delivered = false, weight = 0, applied = 0} end
  local src = reg.cells[tostring(srcId)]
  if src == nil then return {delivered = false, weight = 0, applied = 0} end
  local edge = nil
  for _, e in ipairs(dst.edges) do
    if e.dst == srcId then edge = e; break end
  end
  if edge == nil then return {delivered = false, weight = 0, applied = 0} end
  local applied = clamp01(activation)
  dst.act = clamp01(dst.act + edge.weight * applied)
  return {delivered = true, weight = edge.weight, applied = applied}
end

local function qm_tick(cell, leak)
  local l = (leak ~= nil) and clamp01(leak) or DEFAULT_LEAK
  local i = 1
  while i <= #cell.edges do
    cell.edges[i].weight = clamp01(cell.edges[i].weight * (1 - l))
    i = i + 1
  end
  cell.act = clamp01(cell.act * (1 - l))
  return {edges = #cell.edges, act = cell.act}
end

local function qm_view(reg, id, kind, arg)
  local cell = reg.cells[tostring(id)]
  if cell == nil then return nil end
  if kind == 0 then return cell.act
  elseif kind == 1 then
    local s = 0.0
    for _, e in ipairs(cell.edges) do s = s + e.weight end
    return clamp01(s)
  elseif kind == 2 then return getDial(cell, (arg or 0))
  end
  return nil
end

return { clamp01=clamp01, newRegistry=newRegistry, qm_bind=qm_bind, qm_link=qm_link,
         getCell=getCell, getCellByName=getCellByName, setDial=setDial, getDial=getDial,
         qm_effect=qm_effect, qm_tick=qm_tick, qm_view=qm_view,
         count=function(r) return #r.order end }
