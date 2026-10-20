// ============================================================================
// Recruitment Order - the recruitment panel in the order you want. For any mod
// on REX (Rome: Total War) or M2EX (Medieval II: Total War) - both engines run
// this same script.
//
// Install: put this file in   <the game's folder>\script\modules\
// The engine's own scripts (script\main.nut) require() every .nut in that
// folder once the campaign map is up, whatever mod is running.
//
// Why a script: the game sorts the recruitment panel ITSELF, by the 6th number
// of each unit's stat_cost line (the custom-battle price) - Rome smaller first,
// ships after the land units, agents last; Medieval II the other way round
// (it lays the cards from the end of its list: the larger number first). The order of the recruit lines in
// export_descr_buildings.txt does not count. The engines let a script change
// that number while the game runs (UnitType.trueCost), so during YOUR turn
// this script gives every unit type a small number in the order below, and
// puts the real numbers back before every battle and at the end of your turn -
// the computer's factions, battles and autoresolve keep the real values.
// Nothing is written into the mod's files or the saved game: take the file
// out and everything is as before.
//
// The order: by kind - infantry, missiles (archers, slingers, skirmishers),
// cavalry, missile cavalry (horse archers, skirmisher horse), chariots (those that
// charge, then those with bows or javelins), elephants (the same way), animals
// (war dogs, pigs and their handlers), siege, ships, the rest - and inside each kind by
// the campaign price (stat_cost's 2nd number): the dearest first (the top left
// corner gets the strongest) or the cheapest first.
// Medieval II splits the panel into its own kind blocks (infantry, missile
// infantry, cavalry, missile cavalry, handlers, siege, ships) unless
// recruitment_sort_simple is on: with RO_ONE_PANEL the add-on switches it on
// (M2EX, while the game runs - descr_campaign_db.xml stays as it is), so the
// whole panel follows the order. Rome has no such blocks. In that one panel
// Medieval II puts the agents first and then the ships, before every land unit
// - the game itself does that, no number changes it; with RO_ONE_PANEL false
// the agents stay in their own block at the end.
//
// Console helpers:
//   sq ::recruit_order_list()   the order the panel follows now
//   sq ::recruit_order_off()    the real numbers back (until the next turn or battle)
// Log lines start with "[ORDER]".
// ============================================================================

local PREFIX = "[ORDER] "
function ro_log(message) {
    println(PREFIX + message)
}

local RO_ENABLED = true
local RO_ORDER = "dearest"           // "dearest" or "cheapest" first inside each kind
local RO_ONE_PANEL = true            // Medieval II: one panel for every kind (else the game's kind blocks)

// ---- the order ----
local RO_KINDS = ["infantry", "missiles", "cavalry", "missile cavalry", "chariots", "missile chariots", "elephants",
                  "missile elephants", "animals", "siege", "ships", "non-combatants", "other"]

local ro_real = {}                   // type index -> its real trueCost (as the file has it)
local ro_on = false                  // the ranks are in place now
local ro_turn = false                // your turn now (the ranks belong in it)

function ro_enum(table, name, fallback) {
    try {
        return ::Enum[table][name]
    } catch (err) {
    }
    return fallback
}

// the class of the unit's mount: 0 horse, 1 camel, 2 elephant, 3 chariot, 4 scorpion cart (descr_mount); -1 none
function ro_mount_class(t) {
    try {
        local m = t.mount
        if (m != null) {
            return m.mountClass
        }
    } catch (err) {
    }
    return -1
}

function ro_kind(t) {
    local cat = -1
    local cls = -1
    try {
        cat = t.category
        cls = t.unitClass
    } catch (err) {
        return "other"
    }
    if (cat == ro_enum("UnitCategory", "infantry", 0)) {
        if (cls == ro_enum("UnitClass", "missile", 4) || cls == ro_enum("UnitClass", "skirmish", 2)) {
            return "missiles"
        }
        return "infantry"
    }
    if (cat == ro_enum("UnitCategory", "handler", 5)) {
        return "animals"                        // war dogs, pigs: after the elephants (the user, 2026-10-16)
    }
    if (cat == ro_enum("UnitCategory", "cavalry", 1)) {
        // the shooters after those that fight hand to hand, as the infantry's after its foot; chariots and then
        // elephants after all the horse (the user, 2026-10-16) - told by the mount's class (descr_mount)
        local shoots = cls == ro_enum("UnitClass", "missile", 4) || cls == ro_enum("UnitClass", "skirmish", 2)
        local mount = ro_mount_class(t)
        if (mount == 3) {
            return shoots ? "missile chariots" : "chariots"
        }
        if (mount == 2) {
            return shoots ? "missile elephants" : "elephants"
        }
        return shoots ? "missile cavalry" : "cavalry"
    }
    if (cat == ro_enum("UnitCategory", "siege", 2)) {
        return "siege"
    }
    if (cat == ro_enum("UnitCategory", "ship", 4)) {
        return "ships"
    }
    if (cat == ro_enum("UnitCategory", "nonCombatant", 3)) {
        return "non-combatants"
    }
    return "other"
}

function ro_kind_index(kind) {
    foreach (i, k in RO_KINDS) {
        if (k == kind) {
            return i
        }
    }
    return RO_KINDS.len()
}

// [[kind index, price, name, type], ...] of every unit type, in the panel's order
function ro_sorted() {
    local all = []
    local n = 0
    try {
        n = ::units.count()
    } catch (err) {
        ro_log("the unit types cannot be read: " + err)
        return all
    }
    for (local i = 0; i < n; i++) {
        local t = null
        try {
            t = ::units.at(i)
        } catch (err) {
        }
        if (t == null) {
            continue
        }
        local price = 0
        local name = ""
        try {
            price = t.recruitCost
            name = t.name
        } catch (err) {
        }
        all.append([ro_kind_index(ro_kind(t)), price, name, t, i])
    }
    local dearest = RO_ORDER != "cheapest"
    all.sort(function(a, b) {
        if (a[0] != b[0]) {
            return a[0] <=> b[0]
        }
        if (a[1] != b[1]) {
            return dearest ? b[1] <=> a[1] : a[1] <=> b[1]
        }
        return a[2] <=> b[2]
    })
    return all
}

// Medieval II: the engine has campaignVoice, Rome's does not
function ro_medieval2() {
    return "campaignVoice" in getroottable()
}

// every unit type gets its place as the number the panel sorts by: 1, 2, 3... in Rome (smaller first), the
// other way round in Medieval II (its panel shows the larger number first)
function ro_apply() {
    if (!RO_ENABLED || ro_on) {
        return
    }
    local order = ro_sorted()
    local m2 = ro_medieval2()
    local rank = m2 ? order.len() : 1
    local done = 0
    foreach (u in order) {
        try {
            if (!(u[4] in ro_real)) {
                ro_real[u[4]] <- u[3].trueCost
            }
            u[3].trueCost = rank
            done++
        } catch (err) {
            ro_log("unit " + u[2] + ": " + err)
        }
        rank += m2 ? -1 : 1
    }
    ro_on = true
    ro_log("the recruitment panel follows the order (" + done + " unit types, " + RO_ORDER + " first)")
}

// the real numbers back - battles, autoresolve and the computer's turns use them
function ro_restore() {
    if (!ro_on) {
        return
    }
    foreach (i, v in ro_real) {
        try {
            local t = ::units.at(i)
            if (t != null) {
                t.trueCost = v
            }
        } catch (err) {
        }
    }
    ro_on = false
}

function ro_is_player(e) {
    try {
        local v = e.faction.isPlayerControlled
        return v == true || v == 1
    } catch (err) {
    }
    return false
}

function ro_list() {
    local out = []
    foreach (u in ro_sorted()) {
        out.append(RO_KINDS[u[0] < RO_KINDS.len() ? u[0] : RO_KINDS.len() - 1] + " " + u[2] + " (" + u[1] + ")")
    }
    foreach (line in out) {
        ro_log(line)
    }
    return out.len()
}
getroottable().recruit_order_list <- ro_list
getroottable().recruit_order_off <- ro_restore

// ---- wiring ----
function ro_listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        ro_log("events.on(" + name + ") failed: " + err)
    }
}

// The panel is sorted afresh at every fill, from the numbers as they are then (exe study): the ranks go in at the
// start of your turn, after a loaded game and after a battle in your turn; the real numbers come back before every
// battle, at the end of your turn and when the campaign closes.
ro_listen("FactionTurnStart", function(e) {
    if (ro_is_player(e)) {
        ro_turn = true
        ro_apply()
    } else {
        ro_turn = false
        ro_restore()
    }
})
ro_listen("FactionTurnEnd", function(e) {
    if (ro_is_player(e)) {
        ro_turn = false
    }
    ro_restore()
})
ro_listen("campaignMapLoaded", function(...) {   // a game loaded (or begun) stands in your turn
    ro_turn = true
    ro_apply()
})
ro_listen("SettlementPanelOpen", function(...) {
    if (ro_turn) {
        ro_apply()
    }
})
ro_listen("PreBattle", function(...) { ro_restore() })
ro_listen("PostBattle", function(...) {
    if (ro_turn) {
        ro_apply()
    }
})
ro_listen("unloadCampaign", function(...) {
    ro_restore()
    ro_turn = false
    ro_real = {}
})
ro_log("Recruitment Order module loaded")
// Medieval II (M2EX): one panel for every kind - the game's recruitment_sort_simple switched on (REX has no
// descr_campaign_db: the engine says so in its log and does nothing)
function ro_one_panel() {
    if (!RO_ENABLED || !RO_ONE_PANEL) {
        return
    }
    try {
        if (::campaignDb.extra.recruitmentSortSimple() != true) {
            ::campaignDb.extra.setRecruitmentSortSimple(true)
            ro_log("one panel for every kind (recruitment_sort_simple on)")
        }
    } catch (err) {
    }
}
ro_listen("campaignMapLoaded", function(...) { ro_one_panel() })

// the engines load this file once the campaign map is up - in your turn
ro_one_panel()
ro_turn = true
ro_apply()
