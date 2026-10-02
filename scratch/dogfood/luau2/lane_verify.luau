-- lane_verify.luau — LANE-side authoritative driver for the REAL module.
-- Loads src/cell_api.luau via require and checks the canon spec semantics.
local CellAPI = require("./src/cell_api")

local total, fails = 0, 0
local function eq(g, w, label)
	total = total + 1
	if g ~= w then
		fails = fails + 1
		print(string.format("FAIL %s: got %s want %s", label, tostring(g), tostring(w)))
	end
end
local function near(g, w, label)
	total = total + 1
	if math.abs((g or 1e9) - w) > 1e-9 then
		fails = fails + 1
		print(string.format("FAIL %s: got %s want %s", label, tostring(g), tostring(w)))
	end
end

-- clamp01
near(CellAPI.clamp01(-1), 0.0, "clamp_below")
near(CellAPI.clamp01(2), 1.0, "clamp_above")
near(CellAPI.clamp01(0), 0.0, "clamp_zero")
near(CellAPI.clamp01(1), 1.0, "clamp_one")
near(CellAPI.clamp01(0 / 0), 0.0, "clamp_nan")
near(CellAPI.clamp01(0.42), 0.42, "clamp_passthru")

-- bind
local reg = CellAPI.newRegistry()
local s = CellAPI.qm_bind(reg, "s")
eq(s.id, 1, "bind_first_id1")
eq(CellAPI.qm_bind(reg, "s").id, 1, "bind_idempotent")
eq(#reg.order, 1, "bind_no_dup_order")
local d = CellAPI.qm_bind(reg, "d")
eq(d.id, 2, "bind_second_id2")
eq(reg.count(reg), 2, "reg_count")
eq(CellAPI.getCell(reg, 1), s, "getCell_by_id")
eq(CellAPI.getCellByName(reg, "d"), d, "getCellByName")
eq(CellAPI.getCellByName(reg, "zzz"), nil, "getCellByName_unknown_nil")

-- link: default, explicit, clamp, find-or-create, unknown
local e = CellAPI.qm_link(reg, s.id, d.id)
near(e.weight, 0.5, "link_default")
near(CellAPI.qm_link(reg, s.id, d.id, 0.7).weight, 0.7, "link_update")
eq(#d.edges, 1, "link_find_or_create")
near(CellAPI.qm_link(reg, s.id, d.id, 5).weight, 1.0, "link_clamp_high")
near(CellAPI.qm_link(reg, s.id, d.id, -5).weight, 0.0, "link_clamp_low")
eq(CellAPI.qm_link(reg, s.id, 9999, 0.5), nil, "link_unknown_dst")
eq(CellAPI.qm_link(reg, 9999, d.id, 0.5), nil, "link_unknown_src")

-- link eviction at cap 8 with 8 DISTINCT srcs
local reg2 = CellAPI.newRegistry()
local hub = CellAPI.qm_bind(reg2, "hub")
local ws = {0.9, 0.5, 0.8, 0.3, 0.7, 0.6, 0.4, 0.2}
for i = 1, 8 do
	local src = CellAPI.qm_bind(reg2, "p" .. i)
	CellAPI.qm_link(reg2, src.id, hub.id, ws[i])
end
eq(#hub.edges, 8, "evict_cap_reached")
local coldest = CellAPI.qm_bind(reg2, "p8") -- weight 0.2 = min, index 8
local coldDstBefore = hub.edges[8].dst
eq(coldDstBefore, coldest.id, "evict_coldest_is_index8")
local newsrc = CellAPI.qm_bind(reg2, "p9")
local ne = CellAPI.qm_link(reg2, newsrc.id, hub.id, 0.25)
eq(#hub.edges, 8, "evict_stays_at_cap")
eq(hub.edges[8].dst, newsrc.id, "evict_slot_reused_by_new")
near(hub.edges[8].weight, 0.25, "evict_new_weight")
local found = false
for _, ed in ipairs(hub.edges) do if ed.dst == coldest.id then found = true end end
eq(found, false, "evict_removed_coldest")

-- dials
local c = CellAPI.qm_bind(reg2, "c")
near(CellAPI.setDial(c, 3, 0.6), 0.6, "dial_store")
near(CellAPI.getDial(c, 3), 0.6, "dial_read")
near(CellAPI.setDial(c, 3, 2), 1.0, "dial_clamp_high")
near(CellAPI.getDial(c, 3), 1.0, "dial_clamped_read")
near(CellAPI.setDial(c, 3, -1), 0.0, "dial_clamp_low")
near(CellAPI.getDial(c, 7), 0.0, "dial_unset_zero")
eq(CellAPI.setDial(c, 16, 0.5), nil, "dial_addr16_nil")
eq(CellAPI.getDial(c, 16), nil, "dial_get_addr16_nil")
eq(CellAPI.setDial(c, -1, 0.5), nil, "dial_addr_neg_nil")
eq(CellAPI.setDial(c, 1.5, 0.5), nil, "dial_addr_frac_nil")

-- effect: link-before-effect
local reg3 = CellAPI.newRegistry()
local a = CellAPI.qm_bind(reg3, "a")
local b = CellAPI.qm_bind(reg3, "b")
local drop = CellAPI.qm_effect(reg3, a.id, b.id, 0.5)
eq(drop.delivered, false, "effect_pre_link_dropped")
eq(drop.applied, 0, "effect_pre_link_applied0")
CellAPI.qm_link(reg3, a.id, b.id, 0.6)
local r1 = CellAPI.qm_effect(reg3, a.id, b.id, 0.5)
eq(r1.delivered, true, "effect_delivered")
near(r1.weight, 0.6, "effect_weight")
near(r1.applied, 0.5, "effect_applied")
near(b.act, 0.3, "effect_act_accum")
local r2 = CellAPI.qm_effect(reg3, a.id, b.id, 10)
near(r2.applied, 1.0, "effect_applied_clamped")
near(b.act, 0.3 + 0.6, "effect_act_accum2")
near(r2.weight, 0.6, "effect_weight_unchanged")

-- tick
local t = CellAPI.qm_bind(reg3, "t")
CellAPI.qm_link(reg3, a.id, t.id, 1.0)
t.act = 1.0
local k0 = CellAPI.qm_tick(t, 0.0)
near(k0.act, 1.0, "tick_leak0_act")
near(t.edges[1].weight, 1.0, "tick_leak0_weight")
eq(k0.edges, 1, "tick_edges_count")
local k5 = CellAPI.qm_tick(t, 0.5)
near(k5.act, 0.5, "tick_half_act")
near(t.edges[1].weight, 0.5, "tick_half_weight")
local k1 = CellAPI.qm_tick(t, 1.0)
near(k1.act, 0.0, "tick_leak1_act0")
near(t.edges[1].weight, 0.0, "tick_leak1_weight0")

-- view
local reg4 = CellAPI.newRegistry()
local v = CellAPI.qm_bind(reg4, "v")
eq(CellAPI.qm_view(reg4, v.id, 0, 0), 0.0, "view_act0")
v.act = 0.7
near(CellAPI.qm_view(reg4, v.id, 0, 0), 0.7, "view_act")
local x1 = CellAPI.qm_bind(reg4, "x1")
local x2 = CellAPI.qm_bind(reg4, "x2")
CellAPI.qm_link(reg4, x1.id, v.id, 0.4)
CellAPI.qm_link(reg4, x2.id, v.id, 0.3)
near(CellAPI.qm_view(reg4, v.id, 1, 0), 0.7, "view_wsum_two_srcs")
eq(CellAPI.qm_view(reg4, v.id, 2, 3), 0.0, "view_dial_default")
CellAPI.setDial(v, 3, 0.5)
near(CellAPI.qm_view(reg4, v.id, 2, 3), 0.5, "view_dial")
eq(CellAPI.qm_view(reg4, 9999, 0, 0), nil, "view_unknown_cell")
eq(CellAPI.qm_view(reg4, v.id, 9, 0), nil, "view_unknown_kind")

print(string.format("LANE-PASS %d/%d", total - fails, total))
if fails > 0 then error(string.format("%d lane assertions failed", fails)) end
