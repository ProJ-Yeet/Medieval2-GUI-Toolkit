// ============================================================================
// Sack Settlement - a 4th option on the capture scroll, for any mod on REX.
//
// Install: put this file in   <Rome Total War Gold>\script\modules\
// REX's own squi scripts (script\main.nut) require() every .nut in that folder
// once the campaign map is up, whatever mod is running - no edits to the mod.
//
// What it does: when the player takes a settlement, a "Sack Settlement" button
// appears under Occupy / Enslave / Exterminate. It presses the engine's own
// Exterminate (native loot, sounds and events all run), waits for the scroll to
// close, then:
//   1. demolishes every building except the kept chains (walls and roads by
//      default; the governor's core chain always stays),
//   2. drops the population to RAZE_PEOPLE_LEFT (600 at least - a town cannot be
//      wiped out) and pays a sack reward,
//   3. hands the ruins to the rebels (changeOwner - the army steps outside),
//   4. lets the engine raise its own rebel garrison (give_settlement slave), from
//      the region's rebel_type in the mod's descr_rebel_factions.txt.
// Plain Exterminate stays a plain extermination.
//
// Needs REX 06cf83322 (Sep 26 2026) or newer. Mod-specific settings are at the
// top: kept building chains, reward, button text. Console helpers:
//   sq ::sack_ask_test()     the confirm window (RAZE_BUTTON = false mode)
//   sq ::sack_loot_probe()   what the game UI reports for the capture scroll
//   sq ::sack_ui_fonts()     the game fonts squi can draw with
// Log lines start with "[SACK]".
// ============================================================================

local PREFIX = "[SACK] "
function log(message) {
    println(PREFIX + message)
}

function listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        log("events.on(" + name + ") failed: " + err)
    }
}

local cached_campaign = null
function live_campaign() {
    if (cached_campaign != null) {
        try {
            if (cached_campaign.isOpen) {
                return cached_campaign
            }
        } catch (err) {
        }
        cached_campaign = null
    }
    try {
        local c = ::Campaign.current()
        if (c != null && c.isOpen) {
            cached_campaign = c
            return cached_campaign
        }
    } catch (err) {
    }
    local root = getroottable()
    try {
        if ("campaign" in root && root.campaign != null && root.campaign.isOpen) {
            cached_campaign = root.campaign
            return cached_campaign
        }
    } catch (err) {
    }
    return null
}
function game_tbl() {
    try {
        return ::game
    } catch (err) {
        return null
    }
}
function game_has(name) {
    local g = game_tbl()
    if (g == null) {
        return false
    }
    try {
        return name in g
    } catch (err) {
        return false
    }
}
function each_faction(fn) {
    try {
        local n = ::game.factionCount()
        if (n != null && n > 0) {
            for (local i = 0; i < n; i++) {
                local faction = ::game.faction(i)
                if (faction != null) {
                    fn(faction)
                }
            }
            return
        }
    } catch (err) {
    }
    local campaign = live_campaign()
    if (campaign != null) {
        try {
            local n = campaign.factionCount
            if (n != null && n > 0) {
                for (local i = 0; i < n; i++) {
                    local faction = campaign.factionByOrder(i)
                    if (faction != null) {
                        fn(faction)
                    }
                }
                return
            }
        } catch (err) {
        }
    }
    local n = ::stratMap.regionCount()
    if (n == null || n <= 0) {
        return
    }
    local seen = {}
    for (local i = 0; i < n; i++) {
        local region = ::stratMap.region(i)
        if (region == null) {
            continue
        }
        local faction = null
        try {
            faction = region.faction
        } catch (err) {
        }
        if (faction == null) {
            try {
                local settlement = region.settlementAt(0)
                if (settlement != null) {
                    faction = settlement.owner
                }
            } catch (err) {
            }
        }
        if (faction == null || faction.name == null || faction.name in seen) {
            continue
        }
        seen[faction.name] <- true
        fn(faction)
    }
}
function faction_is_player(faction) {
    if (faction == null) {
        return false
    }
    try {
        local v = faction.isPlayerControlled
        if (v == true || v == 1) {
            return true
        }
    } catch (err) {
    }
    // Fallback: compare with the campaign's human factions.
    local name = null
    try {
        name = faction.name
    } catch (err) {
    }
    local c = live_campaign()
    if (c != null && name != null) {
        try {
            local n = c.humanFactionCount
            for (local i = 0; i < n; i++) {
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

// HLR ships the same feature inside its own plugin; do not double it.
if ("hlr_raze_ask_test" in getroottable()) {
    log("HLR's built-in raze is active - this module stands down")
    return
}

local RAZE_ENABLED = true
// Who may sack:
//   "player"              the human player only (the button on the capture scroll)
//   "everyone"            the player, and every computer faction whenever it exterminates a town
//   "homeless"            only factions without a town of their own (hordes) - player or computer
//   "player_and_homeless" the player, and computer factions without a town
//   "ai"                  the computer's factions only
//   "list"                only the factions named in RAZE_FACTIONS
local RAZE_WHO = "player"
local RAZE_FACTIONS = []             // faction names for RAZE_WHO = "list"
local RAZE_GIVE_TO_REBELS = true     // false = the ruins stay yours
local RAZE_REBEL_GARRISON = true     // false = rebels get the town without an army
local RAZE_GOLD_PER_BUILDING = 300   // denarii per demolished building
local RAZE_GOLD_PER_CITIZEN = 1      // denarii per inhabitant removed by the raze
local RAZE_PEOPLE_LEFT = 600         // inhabitants left in the ruins (600 at least)
local RAZE_MIN_PEOPLE = 600          // the floor: a town is never emptied below this
local RAZE_KEEP_CHAINS = {           // chains that are never demolished (core_* always stays anyway)
    core_building = true,            // governor's building = settlement tier
    defenses = true,                 // walls: pallisade .. epic stone wall
    hinterland_roads = true,         // roads, paved roads, highways
}
// Last resort if the engine installs no rebel garrison: unit types that exist in
// YOUR mod's export_descr_unit.txt, e.g. ["barb peasant slave", "barb infantry slave"].
local RAZE_DEFAULT_REBEL_UNITS = []
local raze_queue = []
// Ask first: after "Exterminate" a Yes/No window asks whether to raze and leave.
// Yes = the raze below; No = a plain extermination, the town stays yours.
// false = raze straight away, without asking (the old behaviour).
local RAZE_ASK = true
// The 4th button: a "Raze" button drawn on the capture scroll next to Occupy /
// Enslave / Exterminate. Pressing it presses the engine's own Exterminate and
// then razes. With it on, the plain Exterminate button is a plain extermination
// again (no question); RAZE_ASK only matters when RAZE_BUTTON is false.
local RAZE_BUTTON = true
// The capture scroll's buttons are TEXT buttons (RomeTW.exe, settlement_info_pieces:
// "Occupy Settlement" / "Enslave Populace" / "Exterminate Populace" from strat.txt,
// game font 5, black, all three as wide as the widest). Ours copies that.
local RAZE_BUTTON_LABEL = "Sack Settlement"
local RAZE_BUTTON_FONT = 5
local RAZE_BUTTON_INK = [0, 0, 0, 255]
// {gold} {buildings} {people} = what this raze brings, filled for the town just taken
local RAZE_BUTTON_TIP = "Sack: about {gold} denarii - {buildings} buildings pulled down, up to {people} people driven out"
local raze_force_region = null       // region the Raze button asked for
local raze_button_canvas = null
local raze_button_art = null          // { l, m, r, dl, dm, dr } text-button sprites
local raze_button_logged = false
local raze_units_logged = false
local raze_scroll_flag = false        // loot_settlement_scroll open, from ScrollOpened (a hint only)
local RAZE_HOLD_TICKS = 300           // longest wait for the capture scroll to shut
local raze_hold_ticks = 0
local RAZE_UI_FONT = 5               // fallback game font id when REX's own fonts are missing
local raze_pending = []              // exterminations waiting for an answer
local raze_dialog = null             // { handle, item } of the open window
local raze_ui_click = null           // answer clicked in the window, run on the next frame
local raze_ui_frame_id = null        // UI.onFrame registration that runs it
local raze_last_capture = null       // { region, faction } of the player's latest capture
local raze_capture_denied = false    // the player's latest capture may not be sacked (RAZE_WHO): no button
local raze_homeless = {}             // factions without a town at the start of their turn (hordes), by name

function faction_name_of(faction) {
    try {
        return faction.name
    } catch (err) {
    }
    return null
}

// A horde / homeless faction: asked of the engine, and remembered from the start of its turn (taking a town ends
// the horde, but the town it takes that turn is the one it may sack).
function faction_is_homeless(faction) {
    if (faction == null) {
        return false
    }
    try {
        if (faction.isHorde || faction.isHomeless) {
            return true
        }
    } catch (err) {
    }
    local name = faction_name_of(faction)
    return name != null && name in raze_homeless
}

function raze_on_turn_start(e) {
    local faction = null
    try {
        faction = e.faction
    } catch (err) {
    }
    local name = faction_name_of(faction)
    if (name == null) {
        return
    }
    local homeless = false
    try {
        homeless = faction.isHorde || faction.isHomeless || faction.settlementCount == 0
    } catch (err) {
    }
    if (homeless) {
        raze_homeless[name] <- true
    } else if (name in raze_homeless) {
        raze_homeless.rawdelete(name)
    }
}

// Whether this faction may sack (RAZE_WHO).
function raze_allowed(faction) {
    local player = faction_is_player(faction)
    if (RAZE_WHO == "everyone") {
        return true
    }
    if (RAZE_WHO == "ai") {
        return !player
    }
    if (RAZE_WHO == "homeless") {
        return faction_is_homeless(faction)
    }
    if (RAZE_WHO == "player_and_homeless") {
        return player || faction_is_homeless(faction)
    }
    if (RAZE_WHO == "list") {
        local name = faction_name_of(faction)
        return name != null && RAZE_FACTIONS.find(name) != null
    }
    return player
}
local raze_handled = {}              // regions already asked about this turn


function raze_log(message) {
    log("raze: " + message)
}

function raze_find_faction(name) {
    local box = { found = null }
    each_faction(function(faction) {
        if (box.found == null && faction.name == name) {
            box.found = faction
        }
    })
    return box.found
}

// One dev-console verb. runConsoleCommand hands back the console's reply,
// which goes to the log; the script-command route is the fallback.
function raze_console(verb, rest) {
    if (game_has("runConsoleCommand")) {
        try {
            local reply = ::game.runConsoleCommand(verb, rest)
            if (reply != null && reply != "") {
                raze_log(verb + " " + rest + " -> " + reply)
            }
            return true
        } catch (err) {
            raze_log("runConsoleCommand " + verb + " failed: " + err)
        }
    }
    if (game_has("runScriptCommand")) {
        try {
            ::game.runScriptCommand("console_command", verb + " " + rest)
            return true
        } catch (err) {
            raze_log("console_command " + verb + " failed: " + err)
        }
    }
    return false
}

function raze_destroy_chain(settlement, chain) {
    try {
        settlement.destroyBuilding(chain, false)
        return true
    } catch (err) {
    }
    try {
        settlement.destroyBuilding(chain)
        return true
    } catch (err) {
        raze_log("destroyBuilding(" + chain + ") failed: " + err)
    }
    return false
}

function raze_owner_name(settlement) {
    try {
        local owner = settlement.owner
        if (owner != null) {
            return owner.name
        }
    } catch (err) {
    }
    return null
}

function raze_garrison_units(settlement) {
    try {
        local army = settlement.army
        if (army == null) {
            return 0
        }
        local n = army.unitCount
        return n == null ? 0 : n
    } catch (err) {
    }
    return 0
}

// BI hands a razed town to the rebels. Primary path: changeOwner, the real
// capture handover - it evacuates the garrison out of the town onto the map,
// the same way a lost settlement does. `give_settlement slave` is only the
// fallback: it does bring its own rebel garrison, but it also relocates the
// former owner's characters (the razing army ended up in the capital).
function raze_hand_to_rebels(settlement, sname) {
    local rebels = raze_find_faction("slave")
    if (rebels != null) {
        try {
            settlement.changeOwner(rebels, true)        // (faction, convertGarrison): the engines take exactly two
        } catch (err) {
            try {
                settlement.owner = rebels
            } catch (err2) {
                raze_log("changeOwner failed: " + err2)
            }
        }
        if (raze_owner_name(settlement) == "slave") {
            raze_log(sname + ": handed to the rebels via changeOwner, garrison evacuated")
            return true
        }
    } else {
        raze_log("rebel faction 'slave' not found")
    }
    if (sname != null && game_has("runScriptCommand")) {
        local args = ["slave, " + sname, "slave " + sname]
        foreach (i, rest in args) {
            try {
                ::game.runScriptCommand("give_settlement", rest)
            } catch (err) {
                raze_log("give_settlement " + rest + " failed: " + err)
            }
            if (raze_owner_name(settlement) == "slave") {
                raze_log(sname + ": handed to the rebels via give_settlement (fallback)")
                return true
            }
        }
    }
    raze_log(sname + ": could not hand the town to the rebels")
    return false
}

// changeOwner leaves the rebel town without an army, so raise one from the
// region's own descr_rebel_factions entry, one unit per line, like a revolt.
// The rebel garrison is the engine's own: give_settlement to 'slave' installs a
// fresh rebel garrison from the region's rebel_type in the running mod's
// descr_rebel_factions (REX docs: "With 'slave' it turns rebel and installs a
// fresh rebel garrison"). It runs after changeOwner, so the town is already the
// rebels' and the player's army is already outside - nothing of the player's is
// relocated. Verified in-game (REX 06cf83322): "rebel garrison now 14 units".
function raze_ensure_rebel_garrison(settlement, sname, region_id = null) {
    local before = raze_garrison_units(settlement)
    if (before > 0) {
        raze_log(sname + ": rebel garrison already there (" + before + " units)")
        return
    }
    if (game_has("runScriptCommand")) {
        foreach (rest in ["slave, " + sname, "slave " + sname]) {
            try {
                ::game.runScriptCommand("give_settlement", rest)
            } catch (err) {
                raze_log("give_settlement " + rest + " failed: " + err)
            }
            if (raze_garrison_units(settlement) > 0) {
                break
            }
        }
    }
    if (raze_garrison_units(settlement) == 0 && RAZE_DEFAULT_REBEL_UNITS.len() > 0) {
        raze_log(sname + ": no native garrison - using RAZE_DEFAULT_REBEL_UNITS")
        foreach (unit in RAZE_DEFAULT_REBEL_UNITS) {
            raze_console("create_unit", sname + " \"" + unit + "\" 1")
        }
    }
    raze_log(sname + ": rebel garrison now " + raze_garrison_units(settlement) + " units")
}

function raze_settlement_name(settlement, region_id) {
    try {
        local n = settlement.name
        if (n != null && n != "") {
            return n
        }
    } catch (err) {
    }
    // No guessing from the region index: engine region ids do not follow the
    // order of descr_regions.txt, and a wrong name would arm the wrong town.
    return null
}

function raze_settlement_in_region(region_id, faction_name) {
    local region = null
    try {
        region = ::stratMap.region(region_id)
    } catch (err) {
    }
    if (region == null) {
        raze_log("region " + region_id + " not found")
        return
    }
    local settlement = null
    try {
        settlement = region.settlementAt(0)
    } catch (err) {
    }
    if (settlement == null) {
        raze_log("no settlement in region " + region_id)
        return
    }
    local sname = raze_settlement_name(settlement, region_id)
    // Collect first, demolish after: indices shift while buildings go away.
    local chains = []
    local n = settlement.buildingCount
    if (n != null) {
        for (local i = 0; i < n; i++) {
            local building = settlement.building(i)
            if (building == null) {
                continue
            }
            local chain = building.chainName
            // the governor's chain (core_building, Medieval II's core_castle_building) always stays, whatever the
            // settings say: without it the town can never be built up again
            if (chain != null && !(chain in RAZE_KEEP_CHAINS) && chain.indexof("core") != 0) {
                chains.append(chain)
            }
        }
    }
    local destroyed = 0
    foreach (i, chain in chains) {
        if (raze_destroy_chain(settlement, chain)) {
            destroyed++
        }
    }
    // Population: cut to RAZE_PEOPLE_LEFT. Only the people the raze actually
    // removes are paid for; those left behind stay in the town (with the rebels).
    local before = 0
    try {
        local p = settlement.population
        before = p == null ? 0 : p
    } catch (err) {
    }
    // Never fewer than RAZE_MIN_PEOPLE (a town cannot be wiped off the map), never raised; the engine clamps to
    // the level's own minimum too.
    local keep = RAZE_PEOPLE_LEFT > RAZE_MIN_PEOPLE ? RAZE_PEOPLE_LEFT : RAZE_MIN_PEOPLE
    if (before > keep) {
        try {
            settlement.population = keep
        } catch (err) {
            raze_log("population write failed: " + err)
        }
    }
    local after = before
    try {
        local p = settlement.population
        after = p == null ? before : p
    } catch (err) {
    }
    local removed = before > after ? before - after : 0
    local gold = destroyed * RAZE_GOLD_PER_BUILDING + removed * RAZE_GOLD_PER_CITIZEN
    if (gold > 0 && faction_name != null) {
        raze_console("add_money", faction_name + " " + gold)
    }
    raze_log(sname + ": population " + before + " -> " + after + ", sack reward " + gold
        + " (" + destroyed + " buildings, " + removed + " people)")
    if (RAZE_GIVE_TO_REBELS) {
        local handed = raze_hand_to_rebels(settlement, sname)
        if (handed && RAZE_REBEL_GARRISON && sname != null) {
            raze_ensure_rebel_garrison(settlement, sname, region_id)
        }
    }
    raze_log("region " + region_id + " (" + sname + "): demolished " + destroyed + " of " + chains.len() + " buildings")
}

// ---- Yes/No window (REX squi UI) ----
local RAZE_TEXT = {
    title = "Raze and Leave?",
    body_a = "",
    body_b = " will be razed: every building except the walls and roads is torn down, the town is sacked and the ruins are left to the rebels. Are you sure you wish to proceed?",
    yes = "Yes - raze and leave",
    no = "No - keep the town",
}

function raze_text(key) {
    return RAZE_TEXT[key]
}

// The squi namespace. Documented as `UI`; looked up at call time.
function raze_ui() {
    local root = getroottable()
    if ("UI" in root && root.UI != null) {
        return root.UI
    }
    return null
}

// Look of the window: like the game's own confirm boxes ("Attack Neutral
// Faction?") - the parchment scroll, a title, the text, and the round tick and
// cross buttons without captions. Art and fonts come from the game and from
// REX's squi scripts (script/core/images.nut, fonts.nut, published as ::EX).
local RAZE_UI_W = 620                 // window width (1080p px, scaled with the screen)
local RAZE_UI_PAD_X = 64              // keeps the text off the scroll's rolled edges
local RAZE_UI_PAD_TOP = 34            // top edge of the scroll to the title
local RAZE_UI_PAD_BOTTOM = 40         // buttons to the bottom edge
local RAZE_UI_TITLE_INK = [36, 24, 12, 255]    // near-black brown, like the game's titles
local RAZE_UI_BODY_INK = [92, 80, 66, 255]     // the game's grey-brown body text
local RAZE_UI_TITLE_FACE = "tnr_med"  // game face for the title (drawn at its own size)
local RAZE_UI_BODY_SIZE = 14          // body text size (Verdana)
local RAZE_UI_ICON = 32               // tick / cross size, in the game's 1024x768 units (native size)
local RAZE_UI_ICON_GAP = 28           // space between them, same units
local RAZE_UI_GAP = 8                 // title -> text -> buttons
local RAZE_UI_RINGS = true            // draw the game's gold ring (BUTTON_OVERLAY_SMALL) over them

// ::EX.<path> or null when REX's squi scripts did not publish it.
function raze_ex(path) {
    local node = getroottable()
    local keys = ["EX"]
    foreach (k in path) {
        keys.append(k)
    }
    foreach (key in keys) {
        try {
            if (node == null || !(key in node)) {
                return null
            }
            node = node[key]
        } catch (err) {
            return null
        }
    }
    return node
}

function raze_art_ok(set) {
    if (set == null || typeof(set) != "array" || set.len() != 9) {
        return false
    }
    foreach (img in set) {
        if (img == null || img == 0) {
            return false
        }
    }
    return true
}

function raze_style(ui, handle, token, value) {
    try {
        ui.setWidgetStyle(handle, token, value)
    } catch (err) {
    }
}

// Our boxes are drawn in physical pixels, their fonts too: a game face draws at the size the game baked, and in a
// subtree that scales fonts the engine writes 'font autoscale: game font N ...' into the script console.
function raze_fonts_fixed(ui, handle) {
    try {
        ui.setWidgetStyle(handle, ui.Cap.autoScaleFonts, 0)
    } catch (err) {
    }
}

// The first of `names` the game has as a font face, else `fallback`.
function raze_pick_face(ui, names, fallback) {
    try {
        local have = {}
        foreach (row in ui.fonts()) {
            have[row.name] <- true
        }
        foreach (name in names) {
            if (name in have) {
                return name
            }
        }
    } catch (err) {
    }
    return fallback
}

// A sprite from the shared UI page, or null.
function raze_sprite(ui, name) {
    try {
        local t = ui.loadSprite(name, ui.PAGE_SHARED)
        if (t != null && t.img != 0) {
            return t
        }
    } catch (err) {
    }
    return null
}

// A click in the window is only remembered here; it runs on the next frame,
// outside the window's own draw, so the window can safely be destroyed.
function raze_ui_run_click() {
    if (raze_ui_click == null) {
        return
    }
    local fn = raze_ui_click
    raze_ui_click = null
    try {
        fn()
    } catch (err) {
        raze_log("window answer failed: " + err)
    }
}

function raze_ui_arm_frame(ui) {
    if (raze_ui_frame_id != null) {
        return
    }
    try {
        raze_ui_frame_id = ui.onFrame(function() { raze_ui_run_click() })
    } catch (err) {
        raze_log("UI.onFrame failed, answers wait for the campaign tick: " + err)
        raze_ui_frame_id = -1
    }
}

// Builds the centred confirm box and returns its handle. Throws on failure.
// Drawn the way REX's own HUD draws (script/ui/campaign/hud): the modal is the
// scroll and the input-grabbing backdrop; the title, the text and the two round
// buttons are painted by its draw callback at physical pixels every frame.
function raze_build_window(ui, id, body_text, on_yes, on_no) {
    local s = 1.0
    try {
        s = ui.dpiScale()
    } catch (err) {
    }
    if (s <= 0.0) {
        s = 1.0
    }
    local px = function(v) { return (v * s + 0.5).tointeger() }

    // Fonts: the game's Times face for the title, REX's Verdana for the text.
    local title_font = raze_pick_face(ui, [RAZE_UI_TITLE_FACE], raze_ex(["fonts", "petrock"]))
    local title_size = title_font == RAZE_UI_TITLE_FACE ? 0 : px(24)
    local body_font = raze_ex(["fonts", "body"])
    if (body_font == null) {
        body_font = raze_pick_face(ui, ["verdana"], RAZE_UI_FONT)
    }
    local body_size = px(RAZE_UI_BODY_SIZE)
    if (title_font == null) {
        title_font = RAZE_UI_FONT
    }

    local accept = raze_sprite(ui, "ACCEPT_BUTTON_IMAGE")
    local cancel = raze_sprite(ui, "CANCEL_BUTTON_IMAGE")
    if (accept == null || cancel == null) {
        throw "ACCEPT_BUTTON_IMAGE / CANCEL_BUTTON_IMAGE not found on the shared UI page"
    }
    // The game's confirm boxes put the thin gold ring BUTTON_OVERLAY_SMALL
    // (shared page) over ACCEPT/CANCEL_BUTTON_IMAGE - compared against the
    // HLR / vanilla textures (sharedpage_01.tga, stratpage_01/02.tga).
    local ring = null
    if (RAZE_UI_RINGS) {
        ring = raze_sprite(ui, "BUTTON_OVERLAY_SMALL")
        if (ring == null) {
            raze_log("BUTTON_OVERLAY_SMALL not found - buttons without rings")
        }
    }

    // Measure, in physical px, so the scroll fits its text.
    local w = px(RAZE_UI_W)
    local inner = w - 2 * px(RAZE_UI_PAD_X)
    local title = raze_text("title")
    local title_wh = [0, px(22)]
    local body_wh = [inner, px(40)]
    try {
        title_wh = ui.textSize(title, title_font, title_size)
    } catch (err) {
    }
    try {
        body_wh = ui.textSize(body_text, body_font, body_size, inner)
    } catch (err) {
    }
    // The buttons follow the engine's own 1024x768 space, like the game's.
    local native = s
    try {
        native = ui.screenSize()[1] / 768.0
    } catch (err) {
    }
    local icon = (RAZE_UI_ICON * native + 0.5).tointeger()
    local igap = (RAZE_UI_ICON_GAP * native + 0.5).tointeger()
    local gap = px(RAZE_UI_GAP)
    local h = px(RAZE_UI_PAD_TOP) + title_wh[1] + gap + body_wh[1] + gap * 2 + icon + px(RAZE_UI_PAD_BOTTOM)
    local x = 0
    local y = 0
    try {
        local screen = ui.screenSize()
        x = (screen[0] - w) / 2
        y = (screen[1] - h) / 2
    } catch (err) {
    }

    raze_ui_click = null
    raze_ui_arm_frame(ui)

    // Everything below is physical px: no autoscale on the box or its drawing.
    ui.pushStyle({ [ui.Cap.autoScale] = 0 })
    local handle = null
    try {
        handle = ui.modal(id, w, h, x, y)
    } catch (err) {
        ui.popStyle()
        throw err
    }
    ui.popStyle()
    try {
        raze_style(ui, handle, ui.Cap.autoScale, 0)
        raze_style(ui, handle, ui.Cap.autoScaleCanvas, 0)
        raze_fonts_fixed(ui, handle)
        local scroll = raze_ex(["shared", "images", "tileable_scroll"])
        if (raze_art_ok(scroll)) {
            raze_style(ui, handle, ui.Surface.window, scroll)
        } else {
            raze_log("scroll art not found - plain window")
        }
        raze_style(ui, handle, ui.Metric.roundWindow, 0)
        raze_style(ui, handle, ui.Metric.borderWindow, 0)

        local logged = { err = false }
        local fit = { done = false }
        ui.onDraw(handle, function() {
            try {
                local r = ui.widgetRectGet(handle)
                if (r == null) {
                    return
                }
                local left = r[0] + px(RAZE_UI_PAD_X)
                local top = r[1] + px(RAZE_UI_PAD_TOP)

                // Title, centred. Every font / style scope is handed its body as a closure: the engine closes it
                // itself, also when the body throws (a scope left open draws the console and every later text of
                // the frame in our font).
                ui.pushFont(title_font, false, title_size, function() {
                    ui.layoutAt(r[0] + (r[2] - title_wh[0]) / 2, top)
                    ui.textColoured(title, RAZE_UI_TITLE_INK[0], RAZE_UI_TITLE_INK[1], RAZE_UI_TITLE_INK[2], RAZE_UI_TITLE_INK[3])
                })

                // The text, wrapped to the scroll.
                local body_top = top + title_wh[1] + gap
                local bottom = { v = body_top + body_wh[1] }
                ui.pushFont(body_font, false, body_size, function() {
                    ui.pushStyle({ [ui.Colour.text] = RAZE_UI_BODY_INK }, function() {
                        ui.layoutAt(left, body_top)
                        ui.textWrapped(body_text, inner)
                        try {
                            local cur = ui.layoutCursor()
                            if (cur != null && cur[1] > bottom.v) {
                                bottom.v = cur[1]
                            }
                        } catch (err) {
                        }
                    })
                })
                local body_bottom = bottom.v

                // Tick and cross, centred under the text.
                local by = body_bottom + gap * 2
                // Grow the scroll once if the text came out taller than measured.
                local need = by + icon + px(RAZE_UI_PAD_BOTTOM) - r[1]
                if (!fit.done && need > r[3]) {
                    fit.done = true
                    try {
                        ui.widgetRect(handle, r[0], r[1] - (need - r[3]) / 2, r[2], need)
                    } catch (err) {
                    }
                }
                local cx = r[0] + r[2] / 2
                local yx = cx - igap / 2 - icon
                local nx = cx + igap / 2
                local yes = ui.imageButton("##" + id + "_yes", accept, icon, icon, yx, by)
                local no = ui.imageButton("##" + id + "_no", cancel, icon, icon, nx, by)
                if (ring != null) {
                    ui.image(ring, icon, icon, yx, by)
                    ui.image(ring, icon, icon, nx, by)
                }
                if (raze_ui_click == null) {
                    if (yes != null && yes.clicked) {
                        raze_ui_click = on_yes
                    } else if (no != null && no.clicked) {
                        raze_ui_click = on_no
                    }
                }
            } catch (err) {
                if (!logged.err) {
                    logged.err = true
                    raze_log("drawing the window failed: " + err)
                }
            }
        })
    } catch (err) {
        try {
            ui.destroy(handle)
        } catch (err2) {
        }
        throw err
    }
    try {
        ui.setParent(0)
    } catch (err) {
    }
    return handle
}

function raze_region_settlement_name(region_id) {
    try {
        local settlement = ::stratMap.region(region_id).settlementAt(0)
        local n = raze_settlement_name(settlement, region_id)
        if (n != null) {
            return n
        }
    } catch (err) {
    }
    return "region " + region_id
}

function raze_dialog_close() {
    if (raze_dialog == null) {
        return
    }
    local ui = raze_ui()
    local handle = raze_dialog.handle
    raze_dialog = null
    if (ui != null) {
        try {
            if (ui.alive(handle)) {
                ui.destroy(handle)
            }
        } catch (err) {
        }
    }
}

function raze_dialog_answer(yes) {
    if (raze_dialog == null) {
        return
    }
    local item = raze_dialog.item
    raze_dialog_close()
    if (yes) {
        raze_queue.append(item)
        raze_log("region " + item.region + ": player chose to raze and leave")
    } else {
        raze_log("region " + item.region + ": player kept the town")
    }
}

// Returns false when the window could not be built.
function raze_dialog_open(item) {
    local ui = raze_ui()
    if (ui == null) {
        raze_log("UI (squi) is not available in this VM")
        return false
    }
    local sname = raze_region_settlement_name(item.region)
    local handle = null
    try {
        handle = raze_build_window(ui, "sack_dialog",
            raze_text("body_a") + sname + raze_text("body_b"),
            function() { raze_dialog_answer(true) },
            function() { raze_dialog_answer(false) })
        try {
            ui.modalCloseOnBackdrop(handle, false)
        } catch (err) {
        }
        try {
            ui.modalOnClose(handle, function() { raze_dialog_answer(false) })
        } catch (err) {
        }
    } catch (err) {
        raze_log("could not build the raze window: " + err)
        return false
    }
    raze_dialog = { handle = handle, item = item }
    raze_log(sname + ": asking the player")
    return true
}

// Called every campaignTick: shows the next question, notices a window that
// went away without an answer (ESC, a load) and counts that as "No".
function raze_dialog_tick() {
    raze_ui_run_click()
    if (raze_dialog != null) {
        local ui = raze_ui()
        local gone = ui == null
        if (!gone) {
            try {
                gone = !ui.alive(raze_dialog.handle) || !ui.widgetVisibleGet(raze_dialog.handle)
            } catch (err) {
            }
        }
        if (gone) {
            raze_dialog_answer(false)
        }
        return
    }
    if (raze_pending.len() == 0) {
        return
    }
    local item = raze_pending.remove(0)
    if (!raze_dialog_open(item)) {
        // No window possible: fall back to the old behaviour.
        raze_log("region " + item.region + ": no window, razing without asking")
        raze_queue.append(item)
    }
}

// Console test: sq ::sack_ask_test() opens the window for the selected
// settlement without razing anything on either answer.
function raze_dialog_test() {
    local ui = raze_ui()
    if (ui == null) {
        return raze_log("UI (squi) is not available in this VM")
    }
    local box = { h = null }
    box.h = raze_build_window(ui, "sack_test",
        raze_text("body_a") + "Test" + raze_text("body_b"),
        function() { raze_log("test: YES pressed"); ui.destroy(box.h) },
        function() { raze_log("test: NO pressed"); ui.destroy(box.h) })
    return raze_log("test window opened")
}

// Console: sq ::sack_ui_fonts() lists the game fonts the window can use.
function raze_list_fonts() {
    local ui = raze_ui()
    if (ui == null) {
        return raze_log("UI (squi) is not available in this VM")
    }
    local rows = ui.fonts()
    foreach (i, row in rows) {
        local id = "?"
        local name = "?"
        try {
            id = row.id
        } catch (err) {
        }
        try {
            name = row.name
        } catch (err) {
        }
        raze_log("font " + id + ": " + name)
    }
    return raze_log(rows.len() + " fonts")
}
getroottable().sack_ui_fonts <- raze_list_fonts
getroottable().sack_ask_test <- raze_dialog_test

// One raze per region per turn, whichever signal saw it first. `forced` is the
// Raze button: no question, and with RAZE_BUTTON on nothing else razes.
function raze_request(region_id, faction_name, source, forced = false) {
    if (RAZE_BUTTON && !forced) {
        if (raze_force_region == null || raze_force_region != region_id) {
            raze_log("region " + region_id + " (" + source + "): plain extermination, the Raze button was not used")
            return
        }
        forced = true
    }
    if (region_id in raze_handled) {
        return
    }
    raze_handled[region_id] <- true
    if (forced) {
        raze_force_region = null
    }
    local item = { region = region_id, faction = faction_name }
    if (RAZE_ASK && !forced) {
        raze_pending.append(item)
        raze_log("region " + region_id + " (" + faction_name + ", " + source + "): waiting for the player's answer")
    } else {
        raze_queue.append(item)
        raze_log("queued region " + region_id + " (" + faction_name + ", " + source + ")")
    }
}

// ---- the Raze button on the capture scroll ----
function raze_game_ui() {
    local root = getroottable()
    if ("ui" in root && root.ui != null) {
        return root.ui
    }
    return null
}

// A named element of the game's own UI, or null while it is not open.
function raze_game_element(name) {
    local gui = raze_game_ui()
    if (gui == null) {
        return null
    }
    try {
        return gui.element(name)
    } catch (err) {
    }
    return null
}

// [x, y, w, h] in physical px, or null.
function raze_element_rect(el) {
    if (el == null) {
        return null
    }
    try {
        local r = [el.screenX, el.screenY, el.screenWidth, el.screenHeight]
        if (r[2] > 0 && r[3] > 0) {
            return r
        }
    } catch (err) {
    }
    return null
}

// Open while its Exterminate button answers. The engine never reports this
// scroll closing (no "scroll closed" line, no ScrollClosed event - 18:17 log),
// so the ScrollOpened flag is only a hint and is dropped here.
function raze_capture_scroll_open() {
    local open = raze_element_rect(raze_game_element("loot_settlement_extermintate_button")) != null
    if (!open) {
        raze_scroll_flag = false
    }
    return open
}

// The id a ButtonPressed / ScrollOpened / ScrollClosed payload carries.
function raze_event_id(e) {
    if (e == null) {
        return null
    }
    foreach (field in ["resourceDescription", "scrollId", "elementId", "buttonId", "id", "name"]) {
        try {
            local v = e[field]
            if (v != null) {
                return "" + v
            }
        } catch (err) {
        }
    }
    return null
}

function raze_on_scroll_opened(e) {
    local id = raze_event_id(e)
    if (id != null && id.indexof("loot_settlement_scroll") != null) {
        raze_scroll_flag = true
        raze_button_logged = false
    }
}

function raze_on_scroll_closed(e) {
    local id = raze_event_id(e)
    if (id != null && id.indexof("loot_settlement_scroll") != null) {
        raze_scroll_flag = false
    }
}

// Console: sq ::sack_loot_probe() - with the capture scroll open, logs what the
// game UI answers for each of its names, and the children it reports.
local RAZE_PROBE_NAMES = ["loot_settlement_scroll", "loot_settlement_occupy_button",
    "loot_settlement_enslave_button", "loot_settlement_extermintate_button", "settlement_taken", "raze_settlement_scroll"]
function raze_probe() {
    local gui = raze_game_ui()
    if (gui == null) {
        return raze_log("probe: no ::ui")
    }
    raze_log("probe: scroll flag " + raze_scroll_flag)
    foreach (name in RAZE_PROBE_NAMES) {
        local el = raze_game_element(name)
        if (el == null) {
            raze_log("probe: " + name + " -> null")
            continue
        }
        local line = "probe: " + name + " ->"
        foreach (f in ["screenX", "screenY", "screenWidth", "screenHeight", "x", "y", "width", "height", "childCount", "enabled"]) {
            try {
                line += " " + f + "=" + el[f]
            } catch (err) {
            }
        }
        raze_log(line)
        try {
            local n = el.childCount
            for (local i = 0; i < n && i < 20; i++) {
                local c = el.child(i)
                local cn = "?"
                try {
                    cn = c.name
                } catch (err) {
                }
                local r = raze_element_rect(c)
                raze_log("probe:   child " + i + " '" + cn + "' " + (r == null ? "-" : r[0] + "," + r[1] + " " + r[2] + "x" + r[3]))
            }
        } catch (err) {
        }
    }
    return "probe done - see the log"
}
getroottable().sack_loot_probe <- raze_probe

function raze_button_load_art(ui) {
    if (raze_button_art != null) {
        return raze_button_art
    }
    local art = {}
    foreach (key, name in { l = "TEXT_BUTTON_BG_L_END", m = "TEXT_BUTTON_BG_MID", r = "TEXT_BUTTON_BG_R_END",
                            dl = "TEXT_BUTTON_BG_DOWN_L_END", dm = "TEXT_BUTTON_BG_DOWN_MID", dr = "TEXT_BUTTON_BG_DOWN_R_END" }) {
        art[key] <- raze_sprite(ui, name)
    }
    if (art.l == null || art.m == null || art.r == null) {
        raze_log("TEXT_BUTTON_BG sprites not found - the Raze button is drawn as a plain box")
    }
    raze_button_art = art
    return art
}

// What the Raze button does, on the frame after the click.
function raze_button_pressed() {
    if (raze_last_capture == null) {
        raze_log("Raze pressed, but no captured settlement is known")
        return
    }
    local ext = raze_game_element("loot_settlement_extermintate_button")
    if (ext == null) {
        raze_log("Raze pressed, but the Exterminate button is gone")
        return
    }
    raze_force_region = raze_last_capture.region
    local ok = false
    try {
        ok = ext.press()
    } catch (err) {
        raze_log("pressing Exterminate failed: " + err)
    }
    raze_log("Raze pressed for region " + raze_last_capture.region + " - Exterminate pressed: " + ok)
    if (ok) {
        // In case the engine's own signals do not reach us, ask directly.
        raze_request(raze_last_capture.region, raze_last_capture.faction, "raze button", true)
    } else {
        raze_force_region = null
    }
}

// What the raze would bring, before the button is pressed (the game's own three buttons say their gold at once):
// { gold, buildings, people } - buildings that would come down (not the kept chains, never core) and the people
// above the floor. The people part is the most it can be: Exterminate runs first and takes its own share.
function raze_estimate(region_id) {
    local out = { gold = 0, buildings = 0, people = 0 }
    local settlement = null
    try {
        settlement = ::stratMap.region(region_id).settlementAt(0)
    } catch (err) {
    }
    if (settlement == null) {
        return out
    }
    try {
        local n = settlement.buildingCount
        for (local i = 0; n != null && i < n; i++) {
            local building = settlement.building(i)
            local chain = building == null ? null : building.chainName
            if (chain != null && !(chain in RAZE_KEEP_CHAINS) && chain.indexof("core") != 0) {
                out.buildings++
            }
        }
    } catch (err) {
    }
    local keep = RAZE_PEOPLE_LEFT > RAZE_MIN_PEOPLE ? RAZE_PEOPLE_LEFT : RAZE_MIN_PEOPLE
    try {
        local p = settlement.population
        out.people = p != null && p > keep ? p - keep : 0
    } catch (err) {
    }
    out.gold = out.buildings * RAZE_GOLD_PER_BUILDING + out.people * RAZE_GOLD_PER_CITIZEN
    return out
}

// RAZE_BUTTON_TIP with {gold}, {buildings} and {people} filled for the town just taken.
function raze_tip_text() {
    local text = RAZE_BUTTON_TIP
    if (raze_last_capture == null || text.find("{") == null) {
        return text
    }
    local e = raze_estimate(raze_last_capture.region)
    foreach (key, value in { gold = e.gold, buildings = e.buildings, people = e.people }) {
        local mark = "{" + key + "}"
        local at = text.find(mark)
        while (at != null) {
            text = text.slice(0, at) + value + text.slice(at + mark.len())
            at = text.find(mark)
        }
    }
    return text
}


// Every frame: while the capture scroll is up, draw the Raze button beside
// Exterminate, sized and spaced like the engine's own buttons.
function raze_button_draw() {
    local ui = raze_ui()
    if (ui == null || !RAZE_BUTTON || !RAZE_ENABLED || raze_capture_denied) {
        return
    }
    local ext = raze_element_rect(raze_game_element("loot_settlement_extermintate_button"))
    if (ext == null) {
        if (raze_scroll_flag && !raze_button_logged) {
            raze_button_logged = true
            raze_log("capture scroll is open but its Exterminate button does not answer ui.element() - run sq ::sack_loot_probe()")
        }
        if (!raze_scroll_flag) {
            raze_button_logged = false
        }
        return
    }
    local scroll = raze_element_rect(raze_game_element("loot_settlement_scroll"))
    local ens = raze_element_rect(raze_game_element("loot_settlement_enslave_button"))
    local occ = raze_element_rect(raze_game_element("loot_settlement_occupy_button"))
    // Some builds give the scroll's rects in the game's 1024x768 layout units, not screen px (a tester at
    // 1920x1080: the button stood left of the scroll, where Exterminate would be on a 1024x768 screen). The
    // capture scroll is centred: a centre nearer 512 than half the screen's width means layout units.
    local screen = null
    local units = null
    try {
        screen = ui.screenSize()
    } catch (err) {
    }
    local mid = scroll != null ? scroll : ext
    if (screen != null && screen[0] > 1100 && mid != null) {
        local cx = mid[0] + mid[2] / 2.0
        local d1 = cx - 512.0, d2 = cx - screen[0] / 2.0
        if (d1 * d1 < d2 * d2) {
            units = [screen[0] / 1024.0, screen[1] / 768.0]
            getroottable().ce_layout_units <- units   // the other add-ons (Avoid Growth) read it too
            if (!raze_units_logged) {
                raze_units_logged = true
                raze_log("the scroll's rects are in 1024x768 layout units - scaled to the " + screen[0] + "x"
                    + screen[1] + " screen")
            }
        }
    }
    if (!raze_button_logged) {
        raze_button_logged = true
        local fmt = function(r) { return r == null ? "-" : "[" + r[0] + "," + r[1] + " " + r[2] + "x" + r[3] + "]" }
        raze_log("capture scroll " + fmt(scroll) + ", occupy " + fmt(occ)
            + ", enslave " + fmt(ens) + ", exterminate " + fmt(ext))
    }
    // Next in the column/row: the same step as from Enslave to Exterminate
    // (vertical or horizontal, whichever the scroll uses), same size.
    local dx = ens != null ? ext[0] - ens[0] : 0
    local dy = ens != null ? ext[1] - ens[1] : 0
    if (dx == 0 && dy == 0) {
        dy = ext[3] + ext[3] / 4
    }
    local x = ext[0] + dx
    local y = ext[1] + dy
    local w = ext[2]
    local h = ext[3]
    // Off the scroll to the right: go under Exterminate instead.
    if (scroll != null && x + w > scroll[0] + scroll[2]) {
        x = ext[0]
        y = ext[1] + h + h / 4
    }
    if (units != null) {                           // layout units -> screen px
        x = (x * units[0]).tointeger()
        w = (w * units[0]).tointeger()
        y = (y * units[1]).tointeger()
        h = (h * units[1]).tointeger()
    }

    local hit = ui.hitRect(x, y, w, h)
    local down = hit != null && hit.held
    local art = raze_button_load_art(ui)
    local l = down && art.dl != null ? art.dl : art.l
    local m = down && art.dm != null ? art.dm : art.m
    local r = down && art.dr != null ? art.dr : art.r
    if (l != null && m != null && r != null) {
        // Three-slice: fixed ends, stretched middle, scaled to the button height.
        local sl = ui.imageSize(l.img)
        local sr = ui.imageSize(r.img)
        local lw = sl != null && sl[1] > 0 ? (sl[0] * h / sl[1]) : h / 4
        local rw = sr != null && sr[1] > 0 ? (sr[0] * h / sr[1]) : h / 4
        ui.image(l.img, lw, h, x, y)
        ui.image(m.img, w - lw - rw, h, x + lw, y)
        ui.image(r.img, rw, h, x + w - rw, y)
    } else {
        ui.drawRect(x, y, w, h, 200, 190, 160, 255)
    }

    // The label, centred, in the scroll buttons' own font and ink.
    local tw = [0, 0]
    try {
        tw = ui.textSize(RAZE_BUTTON_LABEL, RAZE_BUTTON_FONT, 0)
    } catch (err) {
    }
    local off = down ? 1 : 0
    ui.pushFont(RAZE_BUTTON_FONT, false, 0, function() {   // the engine closes the scope, also on a throw
        ui.layoutAt(x + (w - tw[0]) / 2 + off, y + (h - tw[1]) / 2 + off)
        ui.textColoured(RAZE_BUTTON_LABEL, RAZE_BUTTON_INK[0], RAZE_BUTTON_INK[1], RAZE_BUTTON_INK[2], RAZE_BUTTON_INK[3])
    })

    if (hit != null) {
        try {
            ui.tooltipAt(x, y, w, h)
            ui.tooltip(0, raze_tip_text())
        } catch (err) {
        }
        if (hit.clicked && raze_ui_click == null) {
            raze_ui_click = raze_button_pressed
        }
    }
}

// Built once, on the first campaign tick: a screen-wide overlay canvas that
// draws above the game's own scrolls, the way REX's HUD canvases do.
function raze_button_arm() {
    if (!RAZE_BUTTON || raze_button_canvas != null) {
        return
    }
    local ui = raze_ui()
    if (ui == null) {
        return
    }
    try {
        raze_ui_arm_frame(ui)
        raze_button_canvas = ui.canvas("##sack_capture_canvas", 0, 0, 4, 4)
        raze_style(ui, raze_button_canvas, ui.Cap.autoScaleCanvas, 0)
        raze_style(ui, raze_button_canvas, ui.Cap.autoScale, 0)
        raze_fonts_fixed(ui, raze_button_canvas)
        local logged = { err = false }
        ui.onDraw(raze_button_canvas, function() {
            try {
                raze_button_draw()
            } catch (err) {
                if (!logged.err) {
                    logged.err = true
                    raze_log("drawing the Raze button failed: " + err)
                }
            }
        })
        raze_log("Raze button armed on the capture scroll")
    } catch (err) {
        raze_log("could not arm the Raze button: " + err)
        raze_button_canvas = -1
    }
}

function flush_raze_queue() {
    try {
        raze_button_arm()
    } catch (err) {
    }
    try {
        raze_dialog_tick()
    } catch (err) {
        raze_log("raze window: " + err)
    }
    if (raze_queue.len() == 0) {
        return
    }
    // Let the engine finish the capture first: wait until its scroll is shut,
    // but never longer than RAZE_HOLD_TICKS ticks.
    if (raze_capture_scroll_open() && raze_hold_ticks < RAZE_HOLD_TICKS) {
        raze_hold_ticks++
        return
    }
    if (raze_hold_ticks >= RAZE_HOLD_TICKS) {
        raze_log("capture scroll still reported open after " + raze_hold_ticks + " ticks - razing anyway")
    }
    raze_hold_ticks = 0
    local todo = raze_queue
    raze_queue = []
    foreach (i, item in todo) {
        try {
            raze_settlement_in_region(item.region, item.faction)
        } catch (err) {
            raze_log("raze failed: " + err)
        }
    }
}


function on_exterminate_population(e) {
    raze_log("ExterminatePopulation received")
    if (!RAZE_ENABLED || e == null) {
        return
    }
    local region_id = null
    try {
        region_id = e.regionId
    } catch (err) {
    }
    if (region_id == null) {
        raze_log("ExterminatePopulation carried no regionId")
        return
    }
    // Who exterminated: the payload faction, and the settlement's owner right
    // after the capture. A capture on the enemy's turn (a failed sally) can hand
    // the payload the wrong side, so either one being the player counts.
    local payload_faction = null
    try {
        payload_faction = e.faction
    } catch (err) {
    }
    local owner = null
    try {
        owner = ::stratMap.region(region_id).settlementAt(0).owner
    } catch (err) {
    }
    local faction = null
    if (faction_is_player(owner)) {
        faction = owner
    } else if (faction_is_player(payload_faction)) {
        faction = payload_faction
    } else {
        faction = owner != null ? owner : payload_faction
    }
    local faction_name = null
    try {
        faction_name = faction.name
    } catch (err) {
    }
    local payload_name = null
    try {
        payload_name = payload_faction.name
    } catch (err) {
    }
    if (!raze_allowed(faction)) {
        raze_log("region " + region_id + ": exterminated by " + faction_name
            + " (event faction " + payload_name + "), not allowed to sack (RAZE_WHO " + RAZE_WHO + ") - no raze")
        return
    }
    // A computer faction has no button to press and no question to answer: its extermination is the sack.
    raze_request(region_id, faction_name, "event", !faction_is_player(faction))
}

// Second signal: the player's own click on the capture scroll's Exterminate
// button (the engine spells it loot_settlement_extermintate_button). The
// settlement is the one the player captured last.
function raze_on_capture(e) {
    if (e == null) {
        return
    }
    local region_id = null
    try {
        region_id = e.regionId
    } catch (err) {
    }
    local faction = null
    try {
        faction = e.faction
    } catch (err) {
    }
    // only when the event names no taker: a town that revolted to another faction (a shadow taking a town of
    // the player's) is still the player's settlement at that moment - it must not count as the player's capture
    if (region_id != null && faction == null) {
        try {
            faction = ::stratMap.region(region_id).settlementAt(0).owner
        } catch (err) {
        }
    }
    if (region_id == null || !faction_is_player(faction)) {
        return
    }
    local faction_name = null
    try {
        faction_name = faction.name
    } catch (err) {
    }
    raze_capture_denied = !raze_allowed(faction)
    if (raze_capture_denied) {
        raze_last_capture = null
        raze_log("player captured region " + region_id + " - may not sack (RAZE_WHO " + RAZE_WHO + ")")
        return
    }
    raze_last_capture = { region = region_id, faction = faction_name }
    raze_log("player captured region " + region_id)
}

function raze_on_button(e) {
    if (!RAZE_ENABLED || e == null) {
        return
    }
    local id = null
    foreach (field in ["resourceDescription", "elementId", "buttonId", "id"]) {
        try {
            local v = e[field]
            if (v != null) {
                id = "" + v
                break
            }
        } catch (err) {
        }
    }
    if (id == null || id.indexof("loot_settlement") == null) {
        return
    }
    raze_log("capture scroll button: " + id)
    if (id.indexof("extermin") == null) {
        return
    }
    if (raze_last_capture == null) {
        raze_log("Exterminate pressed but no captured region is known")
        return
    }
    raze_request(raze_last_capture.region, raze_last_capture.faction, "button")
}

// ---- wiring ----
function sack_reset() {
    raze_queue = []
    raze_pending = []
    raze_handled = {}
    raze_last_capture = null
    raze_force_region = null
    raze_scroll_flag = false
    raze_hold_ticks = 0
    raze_dialog_close()
}

listen("campaignTick", function(...) {
    try {
        flush_raze_queue()
    } catch (err) {
        raze_log("flush failed: " + err)
    }
})
listen("turnChanged", function(...) { raze_handled = {} })
listen("unloadCampaign", function(...) { sack_reset() })
listen("ExterminatePopulation", on_exterminate_population)
listen("GeneralCaptureSettlement", raze_on_capture)
listen("FactionTurnStart", raze_on_turn_start)
listen("ButtonPressed", raze_on_button)
listen("ScrollOpened", raze_on_scroll_opened)
listen("ScrollClosed", raze_on_scroll_closed)
log("Sack Settlement module loaded")
