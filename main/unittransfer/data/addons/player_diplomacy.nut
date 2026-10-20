// ============================================================================
// Player Diplomacy - AI factions stop attacking the player when it makes no
// sense, for any mod on REX. Only the AI's attitude to the HUMAN player is
// touched; AI-AI diplomacy is left alone.
//
// Install: put this file in   <Rome Total War Gold>\script\modules\
// (create the folder if it is missing - REX's squi loads every .nut in it).
//
// Three rules. Each AI turn, in the calculateLtgd hook (REX's documented place
// to steer the campaign AI), a faction the rules cover is told "do not invade
// the player" (invasionType 5, invadePriority 0, mustInvade false). Its single
// attack slot then goes to someone else - rebels, a weaker neighbour.
//   1. TRUCE: war with the player turned into peace (a ceasefire, whoever asked)
//      -> no attack for TRUCE_TURNS of the player's turns. If it still declares
//      war during the truce, peace is put back at once (Campaign.setStance).
//   2. CLIENT: a protectorate (client kingdom) of the player never plans an
//      invasion of the player while it is one.
//   3. DETERRENCE: a faction far weaker than the player does not plan one either:
//      player strength >= DETER_RATIO x its own. Strength = land/navy units in all
//      armies and garrisons + STRENGTH_PER_SETTLEMENT per settlement. At war it
//      is also marked as wanting peace, so it tends to offer a ceasefire.
//      COALITIONS: its allies already at war with the player count towards its
//      side, so small factions still join a big alliance war against you.
// The player may break a truce freely: declaring war yourself ends it.
//
// Console:  sq ::truce_status()            running truces
//           sq ::truce_set("egypt", 10)    start / change one by hand (0 ends it)
//           sq ::power("egypt")            strength of a faction vs the player
// Log lines start with "[DIPLO]".
// ============================================================================

local TRUCE_TURNS = 10              // player turns a ceasefire holds
local CLIENT_NEVER_ATTACK = true    // rule 2
local DETER_ENABLED = true          // rule 3
local DETER_RATIO = 3.0             // player this many times stronger -> no attack
local STRENGTH_PER_SETTLEMENT = 4   // a settlement counts as this many units
local COALITIONS_COUNT = true       // allies already at war with the player add their strength
local TRUCE_STEER_AI = true         // tell the AI not to plan invasions of the player
local TRUCE_RESTORE_PEACE = true    // undo a war declared on the player during a truce
local INVADE_NONE = 5               // FactionAttitude.invasionType: 5 = do not invade

local PREFIX = "[DIPLO] "
function log(message) {
    println(PREFIX + message)
    return message
}

function listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        log("events.on(" + name + ") failed: " + err)
    }
}

// ---- campaign, factions, the player ----
function tr_campaign() {
    try {
        local c = ::Campaign.current()
        if (c != null && c.isOpen) {
            return c
        }
    } catch (err) {
    }
    local root = getroottable()
    try {
        if ("campaign" in root && root.campaign != null && root.campaign.isOpen) {
            return root.campaign
        }
    } catch (err) {
    }
    return null
}

function tr_each_faction(fn) {
    try {
        local n = ::game.factionCount()
        for (local i = 0; i < n; i++) {
            local f = ::game.faction(i)
            if (f != null) {
                fn(f)
            }
        }
        return
    } catch (err) {
    }
    local c = tr_campaign()
    if (c == null) {
        return
    }
    try {
        for (local i = 0; i < c.factionCount; i++) {
            local f = c.factionByOrder(i)
            if (f != null) {
                fn(f)
            }
        }
    } catch (err) {
    }
}

function tr_name(f) {
    try {
        return f.name
    } catch (err) {
    }
    return null
}

function tr_id(f) {
    foreach (field in ["id", "factionId", "factionID", "index"]) {
        try {
            local v = f[field]
            if (v != null) {
                return v
            }
        } catch (err) {
        }
    }
    return null
}

function tr_is_player(f) {
    if (f == null) {
        return false
    }
    try {
        local v = f.isPlayerControlled
        if (v == true || v == 1) {
            return true
        }
    } catch (err) {
    }
    local name = tr_name(f)
    local c = tr_campaign()
    if (c != null && name != null) {
        try {
            for (local i = 0; i < c.humanFactionCount; i++) {
                local pf = c.playerFaction(i)
                if (pf != null && pf.name == name) {
                    return true
                }
            }
        } catch (err) {
        }
    }
    return false
}

function tr_player() {
    local box = { p = null }
    tr_each_faction(function(f) {
        if (box.p == null && tr_is_player(f)) {
            box.p = f
        }
    })
    return box.p
}

function tr_faction(name) {
    local box = { f = null }
    tr_each_faction(function(f) {
        if (box.f == null && tr_name(f) == name) {
            box.f = f
        }
    })
    return box.f
}

// ---- diplomacy: Enum.DiplomaticRelation + Campaign.checkStance / setStance ----
local tr_rel_cache = {}
function tr_relation(word) {
    if (word in tr_rel_cache) {
        return tr_rel_cache[word]
    }
    local found = null
    try {
        foreach (k, v in ::Enum.DiplomaticRelation) {
            if (("" + k).tolower().indexof(word) != null) {
                found = v
                break
            }
        }
    } catch (err) {
    }
    if (found == null) {
        local keys = ""
        try {
            foreach (k, v in ::Enum.DiplomaticRelation) {
                keys += " " + k + "=" + v
            }
        } catch (err) {
            keys = " (Enum.DiplomaticRelation not reachable: " + err + ")"
        }
        log("no DiplomaticRelation for '" + word + "':" + keys)
    }
    tr_rel_cache[word] <- found
    return found
}

// Calls <one of names>(a, b, rel) on the open campaign, then on ::Campaign,
// trying faction objects, then ids, then names, and both argument orders.
// Returns the call's result, or throws every error it met.
function tr_stance_call(names, a, b, rel) {
    local c = tr_campaign()
    if (c == null) {
        throw "no open campaign"
    }
    local targets = [c]
    try {
        targets.append(::Campaign)
    } catch (err) {
    }
    local errors = []
    foreach (t in targets) {
        foreach (name in names) {
            local fn = null
            try {
                fn = t[name]
            } catch (err) {
                continue
            }
            foreach (pair in [[a, b], [tr_id(a), tr_id(b)], [tr_name(a), tr_name(b)]]) {
                if (pair[0] == null || pair[1] == null) {
                    continue
                }
                foreach (args in [[pair[0], pair[1], rel], [pair[0], rel, pair[1]]]) {
                    try {
                        return fn.acall([t].extend(args))
                    } catch (err) {
                        errors.append(name + "(" + typeof(args[0]) + ", " + typeof(args[1]) + ", " + typeof(args[2]) + "): " + err)
                    }
                }
            }
        }
    }
    local text = ""
    foreach (i, e in errors) {
        text += (i == 0 ? "" : " | ") + e
    }
    throw (text == "" ? "none of " + names[0] + " exists" : text)
}

// The engine's own record of how a and b stand (a's side of it), or null.
// Tried as campaign.diplomacyWith(a, b) and faction.diplomacyWith(b), with
// objects and ids - whichever the binding takes.
local tr_dip_warned = false
function tr_dip(a, b) {
    local errors = []
    local c = tr_campaign()
    local tries = []
    if (c != null) {
        tries.append([c, [a, b]])
        tries.append([c, [tr_id(a), tr_id(b)]])
    }
    tries.append([a, [b]])
    tries.append([a, [tr_id(b)]])
    foreach (t in tries) {
        local ok = true
        foreach (v in t[1]) {
            if (v == null) {
                ok = false
            }
        }
        if (!ok || t[0] == null) {
            continue
        }
        try {
            local d = t[0].diplomacyWith.acall([t[0]].extend(t[1]))
            if (d != null) {
                return d
            }
        } catch (err) {
            errors.append("" + err)
        }
    }
    if (!tr_dip_warned) {
        tr_dip_warned = true
        local text = ""
        foreach (i, e in errors) {
            text += (i == 0 ? "" : " | ") + e
        }
        log("diplomacyWith not reachable: " + text)
    }
    return null
}

// 0 allied, 100 suspicious, 200 neutral, 400 hostile, 600 at war - or null.
function tr_dip_stance(a, b) {
    local d = tr_dip(a, b)
    if (d == null) {
        return null
    }
    foreach (field in ["state", "stance", "dipStance", "currentStance"]) {
        try {
            local v = d[field]
            if (v != null) {
                return v
            }
        } catch (err) {
        }
    }
    return null
}

local tr_war_warned = false
function tr_at_war(a, b) {
    local stance = tr_dip_stance(a, b)
    if (stance != null) {
        return stance >= 600
    }
    local war = tr_relation("war")
    if (war == null) {
        return null
    }
    try {
        local r = tr_stance_call(["checkStance", "checkDipStance"], a, b, war)
        return r == true || r == 1
    } catch (err) {
        if (!tr_war_warned) {
            tr_war_warned = true
            log("cannot read war/peace: " + err)
        }
    }
    return null
}

function tr_make_peace(a, b) {
    local peace = tr_relation("peace")
    if (peace == null) {
        peace = tr_relation("neutral")
    }
    if (peace == null) {
        return false
    }
    try {
        local r = tr_stance_call(["setStance", "setDipStance"], a, b, peace)
        return r != false
    } catch (err) {
        log("setStance(peace) failed: " + err)
    }
    return false
}

// ---- state, kept in ::persistent so it survives save / load ----
local tr_local_state = null
function tr_state() {
    local root = getroottable()
    try {
        if ("persistent" in root && root.persistent != null) {
            if (!("player_truce" in root.persistent)) {
                root.persistent.player_truce <- { atWar = {}, truce = {} }
            }
            local st = root.persistent.player_truce
            if (!("atWar" in st)) {
                st.atWar <- {}
            }
            if (!("truce" in st)) {
                st.truce <- {}
            }
            return st
        }
    } catch (err) {
    }
    if (tr_local_state == null) {
        tr_local_state = { atWar = {}, truce = {} }
    }
    return tr_local_state
}

function tr_truce_left(name) {
    local st = tr_state()
    return (name in st.truce) ? st.truce[name] : 0
}

function tr_set_truce(name, turns, why) {
    local st = tr_state()
    if (turns <= 0) {
        if (name in st.truce) {
            st.truce.rawdelete(name)
            log(name + ": truce ended (" + why + ")")
        }
        return
    }
    st.truce[name] <- turns
    log(name + ": truce for " + turns + " turns (" + why + ")")
}

// War -> peace with the player starts a truce. Run at every faction's turn start,
// so it is seen before the other side's AI plans its turn.
function tr_scan() {
    local player = tr_player()
    if (player == null) {
        return
    }
    local st = tr_state()
    tr_each_faction(function(f) {
        local name = tr_name(f)
        if (name == null || f == player || name == tr_name(player) || name == "slave") {
            return
        }
        local war = tr_at_war(player, f)
        if (war == null) {
            return
        }
        local was = (name in st.atWar) ? st.atWar[name] : null
        st.atWar[name] <- war
        if (was == true && war == false) {
            tr_set_truce(name, TRUCE_TURNS, "war with the player ended")
        }
        if (war == true && tr_truce_left(name) > 0) {
            // At war during a truce without us seeing a declaration.
            if (TRUCE_RESTORE_PEACE && tr_make_peace(f, player)) {
                st.atWar[name] <- false
                log(name + ": found at war with the player during the truce - peace restored")
            }
        }
    })
}

// ---- strength and client status ----
function tr_army_units(f) {
    local total = 0
    local n = 0
    try {
        n = f.armyCount
    } catch (err) {
        return null
    }
    for (local i = 0; i < n; i++) {
        local army = null
        foreach (getter in ["army", "armyAt"]) {
            try {
                army = f[getter](i)
                break
            } catch (err) {
            }
        }
        if (army == null) {
            continue
        }
        try {
            total += army.unitCount
        } catch (err) {
        }
    }
    return total
}

// Units in every army and garrison + STRENGTH_PER_SETTLEMENT per settlement.
function tr_strength(f) {
    local settlements = 0
    try {
        settlements = f.settlementCount
    } catch (err) {
    }
    local units = tr_army_units(f)
    return (units == null ? 0 : units) + settlements * STRENGTH_PER_SETTLEMENT
}

function tr_is_client_of(f, player) {
    local d = tr_dip(f, player)
    if (d != null) {
        try {
            local v = d.isProtectorate
            if (v != null) {
                return v == true || v == 1
            }
        } catch (err) {
        }
    }
    local rel = tr_relation("suzerain")
    if (rel == null) {
        rel = tr_relation("protect")
    }
    if (rel != null) {
        try {
            local r = tr_stance_call(["checkStance", "checkDipStance"], f, player, rel)
            if (r == true || r == 1) {
                return true
            }
        } catch (err) {
        }
    }
    try {
        return f.aiStats().protectorId == tr_id(player)
    } catch (err) {
    }
    try {
        return f.aiStats.protectorId == tr_id(player)
    } catch (err) {
    }
    return false
}

// The side a faction would fight the player with: itself plus every ally of
// its that is already at war with the player. A coalition is judged by its
// combined strength, so a small faction can still join a big alliance war.
function tr_coalition(me, player) {
    local out = { strength = tr_strength(me), members = 1 }
    if (!COALITIONS_COUNT) {
        return out
    }
    local ally = tr_relation("alli")
    if (ally == null) {
        return out
    }
    tr_each_faction(function(f) {
        if (f == me || tr_name(f) == tr_name(me) || tr_name(f) == tr_name(player) || tr_name(f) == "slave") {
            return
        }
        local stance = tr_dip_stance(me, f)
        local allied = stance == 0
        if (stance == null) {
            try {
                local r = tr_stance_call(["checkStance", "checkDipStance"], me, f, ally)
                allied = r == true || r == 1
            } catch (err) {
            }
        }
        if (allied && tr_at_war(f, player) == true) {
            out.strength += tr_strength(f)
            out.members++
        }
    })
    return out
}

// ---- events ----
function tr_on_turn_start(e) {
    local f = null
    try {
        f = e.faction
    } catch (err) {
    }
    try {
        tr_scan()
    } catch (err) {
        log("scan failed: " + err)
    }
    // The player's own turn ticks every truce down.
    if (tr_is_player(f)) {
        local st = tr_state()
        local names = []
        foreach (k, v in st.truce) {
            names.append(k)
        }
        foreach (k in names) {
            local left = st.truce[k] - 1
            if (left <= 0) {
                tr_set_truce(k, 0, "expired")
            } else {
                st.truce[k] = left
            }
        }
    }
}

function tr_on_war_declared(e) {
    local a = null
    local b = null
    try {
        a = e.faction
    } catch (err) {
    }
    try {
        b = e.targetFaction
    } catch (err) {
    }
    if (a == null || b == null) {
        return
    }
    local an = tr_name(a)
    local bn = tr_name(b)
    local st = tr_state()
    if (tr_is_player(a)) {
        // The player breaks it: allowed, the truce is over.
        st.atWar[bn] <- true
        tr_set_truce(bn, 0, "the player declared war")
        return
    }
    if (!tr_is_player(b)) {
        return
    }
    st.atWar[an] <- true
    local left = tr_truce_left(an)
    if (left <= 0) {
        return
    }
    log(an + " declared war on the player with " + left + " truce turns left")
    if (TRUCE_RESTORE_PEACE && tr_make_peace(a, b)) {
        st.atWar[an] <- false
        log(an + ": peace restored")
    }
}

// The documented place to steer the campaign AI: its long-term goal director,
// handed over (writable) once it has read its per-turn parameters.
local tr_ltgd_seen = false
function tr_on_ltgd(...) {
    if (!TRUCE_STEER_AI || vargv.len() == 0) {
        return
    }
    local ltgd = vargv[0]
    if (!tr_ltgd_seen) {
        tr_ltgd_seen = true
        log("calculateLtgd hook reached (" + typeof(ltgd) + ")")
    }
    local me = null
    foreach (field in ["faction", "ownerFaction"]) {
        try {
            me = ltgd[field]
            if (me != null) {
                break
            }
        } catch (err) {
        }
    }
    if (me == null) {
        try {
            me = ltgd.aiFaction.faction
        } catch (err) {
        }
    }
    if (me == null || typeof(me) == "integer") {
        local id = me
        me = null
        if (id != null) {
            tr_each_faction(function(f) {
                if (me == null && tr_id(f) == id) {
                    me = f
                }
            })
        }
    }
    local name = tr_name(me)
    local player = tr_player()
    if (name == null || player == null || name == tr_name(player)) {
        return
    }
    local reasons = []
    local left = tr_truce_left(name)
    if (left > 0) {
        reasons.append("truce, " + left + " turns left")
    }
    if (CLIENT_NEVER_ATTACK && tr_is_client_of(me, player)) {
        reasons.append("client of the player")
    }
    local deterred = false
    if (DETER_ENABLED) {
        local side = tr_coalition(me, player)
        local theirs = tr_strength(player)
        if (side.strength > 0 && theirs >= side.strength * DETER_RATIO) {
            deterred = true
            reasons.append("outmatched " + theirs + " vs " + side.strength
                + (side.members > 1 ? " with " + (side.members - 1) + " allies" : ""))
        }
    }
    if (reasons.len() == 0) {
        return
    }
    local pid = tr_id(player)
    if (pid == null) {
        return
    }
    try {
        local att = ltgd.attitudeTowards(pid)
        if (att == null) {
            return
        }
        att.invasionType = INVADE_NONE
        att.invadePriority = 0
        try {
            att.mustInvade = false
        } catch (err) {
        }
        if (deterred) {
            try {
                att.wantsPeace = true
            } catch (err) {
            }
        }
        local why = ""
        foreach (i, r in reasons) {
            why += (i == 0 ? "" : "; ") + r
        }
        log(name + ": not invading the player (" + why + ")")
    } catch (err) {
        log(name + ": could not steer the AI: " + err)
    }
}

// ---- console ----
function truce_status() {
    local st = tr_state()
    local n = 0
    foreach (k, v in st.truce) {
        log(k + ": " + v + " turns left")
        n++
    }
    return log(n == 0 ? "no truces running" : n + " truce(s)")
}

function truce_set(name, turns = TRUCE_TURNS) {
    if (tr_faction(name) == null) {
        return log("no faction named '" + name + "'")
    }
    tr_set_truce(name, turns, "set by hand")
    return "ok"
}

function power(name) {
    local f = tr_faction(name)
    local player = tr_player()
    if (f == null || player == null) {
        return log("no faction named '" + name + "' (or no player)")
    }
    local mine = tr_strength(f)
    local theirs = tr_strength(player)
    return log(name + " strength " + mine + ", player " + theirs
        + (mine > 0 ? " (x" + (theirs * 1.0 / mine) + ")" : "")
        + (tr_is_client_of(f, player) ? ", client of the player" : "")
        + (tr_truce_left(name) > 0 ? ", truce " + tr_truce_left(name) + " turns" : ""))
}

getroottable().truce_status <- truce_status
getroottable().power <- power
getroottable().truce_set <- truce_set

listen("FactionTurnStart", tr_on_turn_start)
listen("FactionWarDeclared", tr_on_war_declared)
listen("calculateLtgd", tr_on_ltgd)
log("Player Diplomacy module loaded (truce " + TRUCE_TURNS + " turns, deterrence x" + DETER_RATIO + ")")
