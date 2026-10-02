local API = require("./src/cell_api")

local function f(x)
  if x == nil then return "nil" end
  if type(x) == "number" then return string.format("%.10g", x) end
  return tostring(x)
end
local function p(label, a, b, c) print(label .. "|" .. f(a) .. "|" .. f(b) .. "|" .. f(c)) end

local reg = API.newRegistry()
local names = {"alpha","beta","gamma","delta","epsilon","zeta"}
local cells = {}
for i = 1, #names do cells[i] = API.qm_bind(reg, names[i]) end
p("count", reg.count(reg), API.count(reg), #reg.order)
for i = 1, #cells do p("id", i, cells[i].id, cells[i].name) end
p("getbyname", API.getCellByName(reg,"gamma").id, API.getCell(reg, 3).id, API.getCell(reg, 99))

-- links + clamp + find-or-create
local pairs_ = {{1,2,0.9},{1,3,0.5},{1,4,0.8},{1,5,0.3},{1,6,0.7}}
for _,q in ipairs(pairs_) do local e = API.qm_link(reg, cells[q[1]].id, cells[q[2]].id, q[3]); p("link", e.dst, e.weight, #cells[q[2]].edges) end
local e2 = API.qm_link(reg, cells[1].id, cells[2].id, 0.42); p("relink", e2.dst, e2.weight, #cells[2].edges)
local ec = API.qm_link(reg, cells[1].id, cells[2].id, 7.0); p("clamphi", ec.weight, #cells[2].edges, 0)
local ec2 = API.qm_link(reg, cells[1].id, cells[2].id, -3.0); p("clamplo", ec2.weight, #cells[2].edges, 0)
p("linknil", API.qm_link(reg, 1, 999, 0.5), API.qm_link(reg, 999, 2, 0.5), "end")

-- dials
for _,addr in ipairs({0,3,15}) do p("setdial", addr, API.setDial(cells[2], addr, 0.25*addr+0.1), API.getDial(cells[2], addr)) end
p("dialclamp", API.setDial(cells[2], 4, 5.0), API.setDial(cells[2], 5, -5.0), API.getDial(cells[2], 7))
p("dialoob", API.setDial(cells[2], 16, 0.5), API.getDial(cells[2], -1), API.setDial(cells[2], 2.5, 0.5))

-- effects (link-before-effect) + saturation
local r0 = API.qm_effect(reg, cells[6].id, cells[2].id, 0.5); p("effpre", r0.delivered, r0.weight, r0.applied)
local r1 = API.qm_effect(reg, cells[1].id, cells[2].id, 0.5); p("eff", r1.delivered, r1.weight, r1.applied)
p("act", cells[2].act, 0, 0)
local r2 = API.qm_effect(reg, cells[1].id, cells[2].id, 10.0); p("effsat", r2.applied, cells[2].act, r2.weight)

-- ticks
cells[2].act = 1.0
local t0 = API.qm_tick(cells[2], 0.0); p("tick0", t0.edges, t0.act, cells[2].edges[1].weight)
local t1 = API.qm_tick(cells[2], 0.5); p("tick5", t1.edges, t1.act, cells[2].edges[1].weight)
local t2 = API.qm_tick(cells[2], 1.0); p("tick1", t2.edges, t2.act, cells[2].edges[1].weight)

-- view
p("viewact", API.qm_view(reg, cells[3].id, 0, 0), API.qm_view(reg, cells[1].id, 0, 0), 0)
p("viewwsum", API.qm_view(reg, cells[2].id, 1, 0), API.qm_view(reg, cells[4].id, 1, 0), 0)
p("viewdial", API.qm_view(reg, cells[2].id, 2, 0), API.qm_view(reg, cells[2].id, 2, 15), API.qm_view(reg, 999, 0, 0))
p("viewbad", API.qm_view(reg, cells[2].id, 9, 0), 0, 0)
