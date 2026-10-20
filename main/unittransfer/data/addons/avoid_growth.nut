// ============================================================================
// Avoid Growth - a tick on your settlement's scroll that stops the town growing
// past the size it has now. For any mod on REX (Rome: Total War) or M2EX
// (Medieval II: Total War) - both engines run this same script.
//
// Install: put this file in   <the game's folder>\script\modules\
// The engine's own scripts (script\main.nut) require() every .nut in that
// folder once the campaign map is up, whatever mod is running.
//
// What it does: the settlement scroll of each of your towns gets a tick box
// "Avoid Growth", drawn with the game's own small box and tick (PLAIN_CHECKBOX_BG,
// PLAIN_CHECKBOX_TICK - the pieces of its Auto-manage / Construction /
// Recruitment ticks; in Medieval II it stands in their row, right of
// Recruitment). Tick it and the people the
// town has right now become its CEILING:
//   - it never grows past the ceiling,
//   - it still loses people the usual way (recruiting, battles, plague, hunger),
//   - and then grows back - but only up to the ceiling again.
// So a border town stays the village, town or city it is: put it on
// auto-manage and forget it. Untick to let it grow freely again. The ceiling is
// kept in the saved game; a town lost to another faction drops its tick.
//
// Console helpers:
//   sq ::avoid_growth_list()    the ticked towns and their ceilings
//   sq ::avoid_growth_probe()   what the game UI reports for the settlement scroll
// Log lines start with "[GROWTH]".
// ============================================================================

local PREFIX = "[GROWTH] "
function ag_log(message) {
    println(PREFIX + message)
}

local AG_ENABLED = true
local AG_LABEL = "Avoid Growth"
local AG_TIP = "Keep the town at the size it has now"
local AG_TIP_ON = "At most {cap} people - it grows back up to that"   // {cap} = the ceiling
local AG_SHOW_CAP = false            // the ceiling shown beside the words too ("at most 5000")
local AG_OFFSET_X = 0                // move the tick right (+) or left (-), in the game's 1024 x 768 units
local AG_OFFSET_Y = 0                // move the tick down (+) or up (-)
// The words in the first of these game fonts the game has (both games name them alike) - the small one the
// scroll's own tick labels use, in their grey-brown ink.
local AG_FACES = ["verdana_sml", "tnr_sml", "verdana"]
local AG_INK = [128, 119, 97, 255]      // both games' tick words (read in their exes, rules.md 'THE SETTLEMENT SCROLL')
// Medieval II writes its ticks' words (Auto-manage, Construction, Recruitment) in a plain Verdana-like face as big as
// about half their box - M2EX's game faces draw at a fixed small size (a tester's screen: ours stood out), so the words
// take M2EX's own Verdana (script/core/fonts.nut, ::EX.fonts.body) AG_M2_TEXT units high
// Medieval II's own tick words and boxes, measured on a tester's PrintScreen (1596 x 900, 2026-10-09: ours stood 8 px
// too high, its words darker, bigger and closer together, its box square): the words' em AG_M2_TEXT units in the
// scroll's light ink, AG_M2_TRACK units between letters (the game's face is wider than Verdana), AG_M2_GAP from the
// words to the box, the box AG_M2_BOX units wide x high (wider than high, the tick stretched over it).
// Measured again on report #277 (2026-10-15): the game's capitals 9 px high to ours 12, its small letters 7 to
// 9, 2-3 px between letters to ours 4, its ink (128, 119, 97) - ours were too big, spaced and light
// Read in medieval2.exe / M2EX.exe (2026-10-15, rules.md 'THE SETTLEMENT SCROLL AS THE GAMES DRAW IT'): the box is
// 18 x 18 layout units stretched on each axis alone (W / 1024 wide, H / 768 high - so on a wide screen it is wider
// than high, as the testers measured), 8 units right of the words; the words verdana_sml (Verdana 10), stretched the
// same way - the letter spacing below stands in for the wider letters
local AG_M2_TEXT = 10
local AG_M2_TRACK = 0.5
local AG_M2_GAP_BOX = 8
local AG_M2_BOX = [18, 18]
local AG_INK_M2 = [128, 119, 97, 255]
// Rome's Automanage, measured on a tester's screenshot (report R-20261007-8A29B4): its words (128, 119, 97), its box
// 24 x 18 units (wider than high) standing 99 units right of where its words start - ours stands in that column too
// (a tester's photo, 2026-10-09: with 98 / 25 our box stood out 1 px on the left, its right edge even; 2026-10-14,
// R-20261014-78BEE6 at 1600 x 900: the left edges even, ours 28 px wide against Automanage's 27 - so 23 units)
local AG_INK_ROME = [128, 119, 97, 255]
local AG_ROME_BOX = [99, 23]
local AG_KEY = "avoid_growth"        // this add-on's place in the saved game (persistent.avoid_growth)
// The game's own tick pieces, the first found: [box, tick, their size in 1024 x 768 units] - the pieces of the
// scroll's own Auto-manage tick. Medieval II's are the small bevelled PLAIN_CHECKBOX ones too (a tester's screen,
// 2026-10-09: CHECKBOX_BG is a flat pink square, nothing like the scroll's Auto-manage / Construction / Recruitment)
local AG_SPRITES_M2 = [
    ["PLAIN_CHECKBOX_BG", "PLAIN_CHECKBOX_TICK", 18],
    ["CHECKBOX_BG", "TICK_GADGET", 24],
]
local AG_SPRITES_ROME = [
    ["PLAIN_CHECKBOX_BG", "PLAIN_CHECKBOX_TICK", 18],
    ["CHECKBOX_BG", "TICK_GADGET", 24],
]
// Which game's scroll this is: the editor writes the game it puts the script in ("rome" - Rome and Barbarian
// Invasion, the same scroll - or "medieval2"); "auto" guesses by the game's sprites (Barbarian Invasion has some of
// Medieval II's too, so a guess put the tick in the wrong place there).
local CE_GAME = "auto"
local AG_GAP = 4
// Medieval II's settlement scroll: the row of its own ticks (Auto-manage, Construction, Recruitment) - the free
// place right of Recruitment, from the bottom-left of settlement_details_population_stats (measured on the game's
// scroll at 1600 x 900): the words start 472 units right and the box's top 66 below - the game's own gap after
// Recruitment's box (a tester's screen, 2026-10-09: at 448 the words started on Recruitment's box; at 59 the box
// stood 8 px above the game's).
local AG_M2_ROW = [472, 66]
// Medieval II's settlement scroll in M2EX builds with one Auto-manage tick under the town's figures (measured on
// the game's scroll at 1600 x 900): its box's right edge 129 units right of own_settlement_governor_info_panel's
// left and its middle 71 below the panel's bottom; from own_settlement_info_scroll's top-left: 175 right, 279 down.
// The tick goes in that row, AG_M2_GAP units right of the game's box: past the Construction and Recruitment ticks
// the game adds to the row once Auto-manage is ticked (a tester's screens: on top of Construction at 14), so it never
// moves.
local AG_M2_AUTO = [129, 71]
local AG_M2_AUTO_SCROLL = [175, 279]
local AG_M2_GAP = 331                // 307 put the words on Recruitment's box (a tester's screen, 2026-10-09)
// Rome's (and Barbarian Invasion's) settlement scroll: the free line under Automanage, left of the build policy
// arrows, from the bottom-left of own_settlement_governor_info_panel (measured on a tester's scroll at 1600 x 900:
// the panel [898,96 631x124], Automanage's box 996-1020 x 314-336, the tabs from 373).
local AG_ROME_BELOW = 107
local AG_ROME_X = -13
// The governor panel's own size in 1024 x 768 units (the same tester's scroll: 631 x 124 px at 900 px high): the
// tick's sizes and places on Rome's scroll are scaled by the panel as the game draws it, so they stay with the
// scroll at any screen size or shape (the user: it must never drift from Automanage when the resolution changes).
local AG_ROME_GOV_W = 538.5
// Where the tick goes: the first of these parts of the settlement scroll that is open, and where beside it.
local AG_ANCHORS = [
    ["settlement_details_population_stats", "below"],
    ["own_settlement_governor_info_panel", "below"],
    ["own_settlement_info_scroll", "inside_bottom"],
]
local AG_SWEEP_TICKS = 30            // the campaign tick re-checks every ticked town this often

local ag_canvas = null
local ag_art = null
local ag_font = null
local ag_refs = {}                   // settlement name -> the settlement (not saved: found again after a load)
local ag_click = null                // the settlement whose tick was clicked, toggled on the next frame
local ag_frame_id = null
local ag_logged = false
local ag_ticks = 0

// ---- the saved ceilings: persistent.avoid_growth = { <settlement name> = { cap, owner } } ----
function ag_store() {
    local root = getroottable()
    if (!("persistent" in root) || typeof(root.persistent) != "table") {
        root.persistent <- {}
    }
    local p = root.persistent
    if (!(AG_KEY in p) || typeof(p[AG_KEY]) != "table") {
        p[AG_KEY] <- {}
    }
    return p[AG_KEY]
}

function ag_name(s) {
    try {
        return s.name
    } catch (err) {
    }
    return null
}

function ag_owner(s) {
    try {
        return s.owner
    } catch (err) {
    }
    return null
}

function ag_owner_name(s) {
    local f = ag_owner(s)
    try {
        return f == null ? null : f.name
    } catch (err) {
    }
    return null
}

function ag_people(s) {
    try {
        local p = s.population
        return p == null ? 0 : p
    } catch (err) {
    }
    return 0
}

function ag_is_player(faction) {
    if (faction == null) {
        return false
    }
    try {
        local v = faction.isPlayerControlled
        return v == true || v == 1
    } catch (err) {
    }
    return false
}

// A settlement by its name: the one kept from earlier, else looked up on the map.
function ag_ref(name) {
    if (name in ag_refs) {
        local s = ag_refs[name]
        if (s != null && ag_name(s) == name) {
            return s
        }
        ag_refs.rawdelete(name)
    }
    local n = 0
    try {
        n = ::stratMap.regionCount()
    } catch (err) {
    }
    for (local i = 0; i < n; i++) {
        local region = null
        try {
            region = ::stratMap.region(i)
        } catch (err) {
        }
        if (region == null) {
            continue
        }
        for (local j = 0; j < 4; j++) {
            local s = null
            try {
                s = region.settlementAt(j)
            } catch (err) {
            }
            if (s == null) {
                break
            }
            if (ag_name(s) == name) {
                ag_refs[name] <- s
                return s
            }
        }
    }
    return null
}

// One town back under its ceiling (or its tick dropped when another faction holds it now).
function ag_hold(name, entry, s) {
    local owner = ag_owner_name(s)
    if (owner != null && "owner" in entry && entry.owner != owner) {
        ag_store().rawdelete(name)
        ag_log(name + ": now " + owner + "'s - Avoid Growth taken off")
        return
    }
    local now = ag_people(s)
    if (now <= entry.cap) {
        return
    }
    try {
        s.population = entry.cap
    } catch (err) {
        ag_log(name + ": population write failed: " + err)
        return
    }
    local after = ag_people(s)
    if (after > entry.cap) {
        // the level's own minimum is above the ceiling (the town was made bigger since): that minimum is the ceiling
        entry.cap = after
        ag_log(name + ": the town's level holds at least " + after + " - the ceiling follows")
    }
}

function ag_hold_all() {
    if (!AG_ENABLED) {
        return
    }
    local store = ag_store()
    local names = []
    foreach (name, entry in store) {
        names.append(name)
    }
    foreach (name in names) {
        if (!(name in store)) {
            continue
        }
        local s = ag_ref(name)
        if (s != null) {
            ag_hold(name, store[name], s)
        }
    }
}

function ag_on_settlement(e) {
    if (!AG_ENABLED || e == null) {
        return
    }
    local s = null
    try {
        s = e.settlement
    } catch (err) {
    }
    local name = ag_name(s)
    local store = ag_store()
    if (name != null && name in store) {
        ag_refs[name] <- s
        ag_hold(name, store[name], s)
    }
}

function ag_toggle(s) {
    local name = ag_name(s)
    if (name == null) {
        return
    }
    local store = ag_store()
    if (name in store) {
        store.rawdelete(name)
        ag_log(name + ": Avoid Growth off - it grows freely again")
    } else {
        local cap = ag_people(s)
        store[name] <- { cap = cap, owner = ag_owner_name(s) }
        ag_refs[name] <- s
        ag_log(name + ": Avoid Growth on - at most " + cap + " people")
    }
}

// ---- the tick on the settlement scroll ----
function ag_ui() {
    local root = getroottable()
    return "UI" in root ? root.UI : null
}

function ag_game_element(name) {
    try {
        return ::ui.element(name)
    } catch (err) {
    }
    return null
}

// Some builds give the scroll's rects in the game's 1024 x 768 layout units, not screen px (the Raze button stood in
// the wrong place at 1920 x 1080 for that). Medieval II's own settlement scroll fills the screen's right half: its
// middle nearer 768 (three quarters of 1024) than three quarters of the screen's width means layout units. Else the
// factors the capture scroll's add-ons (Sack / Raze Settlement) found, if they did.
function ag_units() {
    local root = getroottable()
    local found = "ce_layout_units" in root ? root.ce_layout_units : null
    try {
        local el = ::ui.element("own_settlement_info_scroll")
        local screen = ag_ui().screenSize()
        if (el != null && screen != null && screen[0] > 1100 && el.screenWidth > 0 && ag_art != null && ag_art.m2) {
            local cx = el.screenX + el.screenWidth / 2.0
            local d1 = cx - 768.0, d2 = cx - screen[0] * 0.75
            return d1 * d1 < d2 * d2 ? [screen[0] / 1024.0, screen[1] / 768.0] : null
        }
    } catch (err) {
    }
    return found
}

function ag_rect(el) {
    if (el == null) {
        return null
    }
    try {
        local r = [el.screenX, el.screenY, el.screenWidth, el.screenHeight]
        // a build that gives the game's rects in 1024 x 768 layout units: the capture scroll's add-ons find it
        // out (the scroll is centred) and leave the factors here - turned into screen px
        local k = ag_units()
        if (k != null) {
            r = [(r[0] * k[0]).tointeger(), (r[1] * k[1]).tointeger(), (r[2] * k[0]).tointeger(),
                 (r[3] * k[1]).tointeger()]
        }
        if (r[2] > 0 && r[3] > 0) {
            return r
        }
    } catch (err) {
    }
    return null
}

// The settlement the open scroll shows, when it is one of the player's own.
function ag_shown() {
    local s = null
    try {
        local sc = ::ui.settlementScroll()
        if (sc != null) {
            s = sc.settlement
        }
    } catch (err) {
    }
    if (s == null) {
        try {
            s = ::ui.cardManager().selectedSettlement
        } catch (err) {
        }
    }
    return s != null && ag_is_player(ag_owner(s)) ? s : null
}

// The tick belongs to the Construction tab of the settlement scroll (the user: never on Recruitment, Repair or
// Retrain - it hung on the governor panel every tab shares). The tabs are named in both games; a button's 'selected'
// says which one is open. A build that cannot tell keeps the tick on every tab (said once in the log).
local AG_TABS = ["settlement_info_construction_tab", "settlement_info_recruitment_tab", "settlement_info_repair_tab",
                 "settlement_info_retrain_tab"]
local ag_tab_said = false

function ag_tab_open() {
    local known = false
    foreach (i, name in AG_TABS) {
        local el = ag_game_element(name)
        if (el == null) {
            continue
        }
        local on = null
        try {
            on = el.selected
        } catch (err) {
        }
        if (on == null) {
            continue
        }
        known = true
        if (on) {
            return i == 0
        }
    }
    if (!ag_tab_said) {
        ag_tab_said = true
        ag_log(known ? "no tab of the settlement scroll is open - the tick waits for the Construction tab"
                     : "the settlement scroll does not say which tab is open - the tick shows on every tab")
    }
    return !known
}

// The nearest whole pixel, for a positive or negative number (tointeger() cuts towards 0: -15.2 and 114.8 made
// Automanage's column 1 px off).
function ag_round(v) {
    return v < 0 ? -((-v + 0.5).tointeger()) : (v + 0.5).tointeger()
}

// Screen px per 1024 x 768 unit on Rome's scroll: from the governor panel's width as the game draws it (it scales
// its scroll its own way), else the screen's (ag_scale).
function ag_rome_scale(k) {
    local gov = ag_rect(ag_game_element("own_settlement_governor_info_panel"))
    if (gov == null) {
        return k
    }
    local kp = gov[2] / AG_ROME_GOV_W
    return kp > k * 0.5 && kp < k * 2.0 ? kp : k                   // a panel of another size: the screen's
}

// Screen px per layout unit across (W / 1024): the games stretch their scroll on each axis alone; k (down) when the
// width is not known.
function ag_scale_x(ui, k) {
    try {
        local v = ui.virtualScale()
        if (v != null && v[0] > 0) {
            return v[0]
        }
    } catch (err) {
    }
    try {
        return ui.screenSize()[0] / 1024.0
    } catch (err) {
    }
    return k
}

function ag_scale(ui) {
    try {
        local v = ui.virtualScale()
        if (v != null && v[1] > 0) {
            return v[1]
        }
    } catch (err) {
    }
    try {
        return ui.screenSize()[1] / 768.0
    } catch (err) {
    }
    return 1.0
}

function ag_sprite(ui, name) {
    local t = null
    try {
        t = ui.loadSprite(name, ui.PAGE_SHARED)
    } catch (err) {
    }
    return t != null && t.img != 0 ? t : null
}

// The game's own tick pieces: { box, tick, size } - the first pair the game has; none: a plain box.
function ag_load_art(ui) {
    if (ag_art == null) {
        local m2 = CE_GAME == "medieval2" || (CE_GAME == "auto" && ag_sprite(ui, "BEVEL_TL") != null)
        local pairs = m2 ? AG_SPRITES_M2 : AG_SPRITES_ROME
        ag_art = { box = null, tick = null, size = pairs[0][2], m2 = m2 }
        foreach (pair in pairs) {
            local b = ag_sprite(ui, pair[0])
            local t = ag_sprite(ui, pair[1])
            if (b != null && t != null) {
                ag_art = { box = b, tick = t, size = pair[2], m2 = ag_art.m2 }
                break
            }
        }
        if (ag_art.box == null) {
            ag_log("the game's tick pieces not found - the tick is drawn as a plain box")
        } else {
            ag_log("tick pieces: " + (m2 ? "Medieval II's" : "Rome's") + " (" + CE_GAME + "), " + ag_art.size + " units")
        }
    }
    return ag_art
}

// M2EX's own Verdana (a size of our own), or null.
function ag_ex_font() {
    try {
        local root = getroottable()
        if ("EX" in root && "fonts" in root.EX && "body" in root.EX.fonts) {
            return root.EX.fonts.body
        }
    } catch (err) {
    }
    return null
}

function ag_face(ui) {
    if (ag_font == null) {
        ag_font = AG_FACES[AG_FACES.len() - 1]
        try {
            local have = {}
            foreach (row in ui.fonts()) {
                have[row.name] <- true
            }
            foreach (name in AG_FACES) {
                if (name in have) {
                    ag_font = name
                    break
                }
            }
        } catch (err) {
        }
    }
    return ag_font
}

// Medieval II: [x, y, anchor] in the row of the game's own Auto-manage tick, right of it - from the governor panel
// when it lies on the town's own scroll (with Settlement Details open beside it the game may name another place),
// else from the scroll itself; null: neither is open.
function ag_place_m2(box, k) {
    local scroll = ag_rect(ag_game_element("own_settlement_info_scroll"))
    local gov = ag_rect(ag_game_element("own_settlement_governor_info_panel"))
    if (gov != null && (scroll == null || (gov[0] >= scroll[0] && gov[0] + gov[2] <= scroll[0] + scroll[2]))) {
        return [gov[0] + ((AG_M2_AUTO[0] + AG_M2_GAP) * k + 0.5).tointeger(),
                gov[1] + gov[3] + (AG_M2_AUTO[1] * k + 0.5).tointeger() - box / 2,
                "own_settlement_governor_info_panel (Medieval II: right of Auto-manage)"]
    }
    if (scroll != null) {
        return [scroll[0] + ((AG_M2_AUTO_SCROLL[0] + AG_M2_GAP) * k + 0.5).tointeger(),
                scroll[1] + (AG_M2_AUTO_SCROLL[1] * k + 0.5).tointeger() - box / 2,
                "own_settlement_info_scroll (Medieval II: right of Auto-manage)"]
    }
    return null
}

// [x, y] of the tick box (physical px), from the first open anchor, or null. m2: Medieval II's scroll (its tick
// row is known: the box goes right of Recruitment); k: screen px per 1024 x 768 unit.
function ag_place(box, m2, k, kx = null) {
    kx = kx == null ? k : kx
    if (m2 && ag_rect(ag_game_element("settlement_details_population_stats")) == null) {
        local at = ag_place_m2(box, k)
        if (at != null) {
            return at
        }
    }
    if (!m2) {
        // Rome: the town's own scroll first - with Settlement Details open beside it, the details' population
        // figures are on screen too, and the tick belongs under Automanage, not there
        local gov = ag_rect(ag_game_element("own_settlement_governor_info_panel"))
        if (gov != null) {
            return [gov[0] + ag_round(AG_ROME_X * kx), gov[1] + gov[3] + ag_round(AG_ROME_BELOW * k),
                    "own_settlement_governor_info_panel (Rome: under Automanage)", gov[0]]
        }
    }
    foreach (a in AG_ANCHORS) {
        local r = ag_rect(ag_game_element(a[0]))
        if (r == null) {
            continue
        }
        if (m2 && a[0] == "settlement_details_population_stats") {
            return [r[0] + (AG_M2_ROW[0] * k + 0.5).tointeger(), r[1] + r[3] + (AG_M2_ROW[1] * k + 0.5).tointeger(),
                    a[0] + " (Medieval II tick row)"]
        }
        if (!m2 && a[0] == "own_settlement_governor_info_panel") {
            return [r[0] + ag_round(AG_ROME_X * kx), r[1] + r[3] + ag_round(AG_ROME_BELOW * k),
                    a[0] + " (Rome: under Automanage)", r[0]]
        }
        if (a[1] == "below") {
            return [r[0], r[1] + r[3] + box / 4, a[0]]
        }
        return [r[0] + box * 2, r[1] + r[3] - box * 3, a[0]]      // inside the scroll, above its bottom edge
    }
    return null
}

// [width of each letter] of words in face at size (a letter's own width; the game spaces its tick words wider).
function ag_letter_widths(ui, words, face, size) {
    local out = []
    for (local i = 0; i < words.len(); i++) {
        local t = [7, 14]
        try {
            t = ui.textSize(words.slice(i, i + 1), face, size)
        } catch (err) {
        }
        out.append(t[0])
    }
    return out
}

// The tooltip's words with the ceiling put in for {cap}.
function ag_fill(text, cap) {
    local at = text.indexof("{cap}")
    return at == null ? text : text.slice(0, at) + cap + text.slice(at + 5)
}

function ag_draw() {
    local ui = ag_ui()
    if (ui == null || !AG_ENABLED) {
        return
    }
    local s = ag_shown()
    if (s == null || !ag_tab_open()) {
        return
    }
    local k = ag_scale(ui)                      // down: H / 768, as the games stretch their scrolls
    local art = ag_load_art(ui)
    local box = (art.size * k + 0.5).tointeger()
    // across: Medieval II W / 1024; Rome from its governor panel as drawn (its numbers here were measured in those
    // units) - one scale for both axes put the tick 10-25 % short off 16:9 screens (the engine source: each axis
    // is stretched alone)
    local kx = art.m2 ? ag_scale_x(ui, k) : ag_rome_scale(k)
    if (art.m2 && art.size == 18) {             // Medieval II: the scroll's own box, each axis stretched alone
        box = ag_round(AG_M2_BOX[1] * k)
    }
    local tick = box
    local at = ag_place(box, art.m2, k, kx)
    if (at == null) {
        return
    }
    if (!ag_logged) {
        ag_logged = true
        local line = "settlement scroll:"
        foreach (a in AG_ANCHORS) {
            local r = ag_rect(ag_game_element(a[0]))
            line += " " + a[0] + (r == null ? " -" : " [" + r[0] + "," + r[1] + " " + r[2] + "x" + r[3] + "]")
        }
        ag_log(line + "; the tick at " + at[0] + "," + at[1] + " beside " + at[2] + ", " + k + " px a unit, font "
            + (art.m2 && ag_ex_font() != null ? "M2EX's Verdana" : ag_face(ui)))
    }
    local x = at[0] + (AG_OFFSET_X * kx).tointeger()
    local y = at[1] + (AG_OFFSET_Y * k).tointeger()
    local name = ag_name(s)
    local store = ag_store()
    local on = name != null && name in store
    local words = AG_LABEL
    if (on && AG_SHOW_CAP) {
        words += " (at most " + store[name].cap + ")"
    }
    local face = ag_face(ui)
    local size = 0
    if (art.m2 && ag_ex_font() != null) {
        face = ag_ex_font()
        size = (AG_M2_TEXT * k + 0.5).tointeger()
    }
    local tw = [words.len() * 7, 14]
    try {
        tw = ui.textSize(words, face, size)
    } catch (err) {
    }
    // the words first, the box right of them - as the scroll's own 'Automanage [ ]' and Medieval II's ticks
    local ink = art.m2 ? AG_INK_M2 : AG_INK_ROME
    local track = art.m2 ? AG_M2_TRACK * k : 0
    local widths = track > 0 ? ag_letter_widths(ui, words, face, size) : null
    if (widths != null) {                       // Medieval II: letter by letter, spaced as the game's words
        local w = 0
        foreach (i, lw in widths) {
            w += lw + (i < widths.len() - 1 ? track : 0)
        }
        tw = [w.tointeger(), tw[1]]
    }
    local ty = y + (box - tw[1]) / 2
    // the engine closes the font scope itself, also when the body throws (a scope left open would draw the
    // console and every later text of the frame in our font)
    ui.pushFont(face, false, size, function() {
        if (widths == null) {
            ui.layoutAt(x, ty)
            ui.textColoured(words, ink[0], ink[1], ink[2], ink[3])
            return
        }
        local cx = x * 1.0
        foreach (i, lw in widths) {
            ui.layoutAt(cx.tointeger(), ty)
            ui.textColoured(words.slice(i, i + 1), ink[0], ink[1], ink[2], ink[3])
            cx += lw + track
        }
    })
    local bx = x + tw[0] + (art.m2 ? ag_round(AG_M2_GAP_BOX * kx) : (AG_GAP * kx).tointeger())
    local bw = art.m2 && art.size == 18 ? ag_round(AG_M2_BOX[0] * kx) : box
    if (!art.m2) {                  // in Automanage's column, as wide as its box (one rounding: no pixel off)
        bw = ag_round(AG_ROME_BOX[1] * kx)
        local col = at.len() > 3 ? at[3] + ag_round((AG_ROME_X + AG_ROME_BOX[0]) * kx) + ag_round(AG_OFFSET_X * kx)
                                 : x + ag_round(AG_ROME_BOX[0] * kx)
        bx = bx > col ? bx : col
    }
    if (art.box != null) {
        ui.image(art.box.img, bw, box, bx, y)
    } else {
        ui.drawRect(bx, y, bw, box, 230, 220, 190, 255)
    }
    if (on) {
        if (art.tick != null && (!art.m2 || art.size == 18)) {
            ui.image(art.tick.img, bw, box, bx, y)     // the tick stretched over its box, as the game's own
        } else if (art.tick != null) {
            ui.image(art.tick.img, tick, tick, bx + (bw - tick) / 2, y + (box - tick) / 2)
        } else {
            ui.drawRect(bx + bw / 4, y + box / 4, bw / 2, box / 2, 40, 30, 20, 255)
        }
    }
    local tx = bx + bw
    local w = tx - x
    local hit = ui.hitRect(x, y, w, box)
    if (hit != null) {
        try {
            ui.tooltipAt(x, y, w, box)
            ui.tooltip(0, on ? ag_fill(AG_TIP_ON, store[name].cap) : AG_TIP)
        } catch (err) {
        }
        if (hit.clicked && ag_click == null) {
            ag_click = s
        }
    }
}

// A click is acted on the next frame, outside the drawing.
function ag_run_click() {
    if (ag_click == null) {
        return
    }
    local s = ag_click
    ag_click = null
    try {
        ag_toggle(s)
    } catch (err) {
        ag_log("the tick failed: " + err)
    }
}

function ag_arm() {
    if (ag_canvas != null) {
        return
    }
    local ui = ag_ui()
    if (ui == null) {
        return
    }
    try {
        if (ag_frame_id == null) {
            ag_frame_id = ui.onFrame(function() { ag_run_click() })
        }
        ag_canvas = ui.canvas("##avoid_growth_canvas", 0, 0, 4, 4)
        try {
            ui.setWidgetStyle(ag_canvas, ui.Cap.autoScaleCanvas, 0)
            ui.setWidgetStyle(ag_canvas, ui.Cap.autoScale, 0)
        } catch (err) {
        }
        // fonts not scaled either: a game face draws at the size the game baked, and in a subtree that scales
        // fonts the engine writes 'font autoscale: game font N ...' into the script console
        try {
            ui.setWidgetStyle(ag_canvas, ui.Cap.autoScaleFonts, 0)
        } catch (err) {
        }
        local logged = { err = false }
        ui.onDraw(ag_canvas, function() {
            try {
                ag_draw()
            } catch (err) {
                if (!logged.err) {
                    logged.err = true
                    ag_log("drawing the tick failed: " + err)
                }
            }
        })
        ag_log("the tick is armed on the settlement scroll")
    } catch (err) {
        ag_log("could not arm the tick: " + err)
        ag_canvas = -1
    }
}

// ---- console ----
function ag_list() {
    local store = ag_store()
    local n = 0
    foreach (name, entry in store) {
        local s = ag_ref(name)
        ag_log(name + ": at most " + entry.cap + (s == null ? " (not found on the map now)" : ", now " + ag_people(s)))
        n++
    }
    return ag_log(n + " town(s) avoid growth")
}
getroottable().avoid_growth_list <- ag_list

function ag_probe() {
    foreach (a in AG_ANCHORS) {
        local r = ag_rect(ag_game_element(a[0]))
        ag_log("probe: " + a[0] + " -> " + (r == null ? "not open" : r[0] + "," + r[1] + " " + r[2] + "x" + r[3]))
    }
    local s = ag_shown()
    return ag_log("probe: the scroll shows " + (s == null ? "no town of yours" : ag_name(s) + ", " + ag_people(s)
        + " people"))
}
getroottable().avoid_growth_probe <- ag_probe

// ---- wiring ----
function ag_listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        ag_log("events.on(" + name + ") failed: " + err)
    }
}

ag_listen("campaignTick", function(...) {
    ag_arm()
    ag_run_click()
    ag_ticks++
    if (ag_ticks >= AG_SWEEP_TICKS) {
        ag_ticks = 0
        try {
            ag_hold_all()
        } catch (err) {
            ag_log("holding the ceilings failed: " + err)
        }
    }
})
ag_listen("SettlementTurnStart", ag_on_settlement)
ag_listen("SettlementTurnEnd", ag_on_settlement)
ag_listen("FactionTurnStart", function(...) { ag_hold_all() })
ag_listen("FactionTurnEnd", function(...) { ag_hold_all() })
ag_listen("GameReloaded", function(...) { ag_refs = {} })
ag_listen("unloadCampaign", function(...) {
    ag_refs = {}
    ag_click = null
    ag_logged = false
})
ag_log("Avoid Growth module loaded")
