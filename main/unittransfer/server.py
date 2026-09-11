"""Local web server for the Unit Transfer UI (Stage 4).

Serves a single-page app to browse a source mod's units faction-wise (with icons),
pick a destination mod, and transfer units with options + conflict resolution.
Transfers apply in-place into the destination mod (backing up first) and every
transfer is logged with an undo.

API
  GET  /                         -> SPA
  GET  /api/settings             -> {med2_root, last_source, last_dest}
  POST /api/settings             -> set {med2_root,...} (persisted)
  GET  /api/detect_med2_root     -> {path}  (registry lookup, not persisted)
  GET  /api/port?kind=&source=&dest=
                                 -> every trait / ancillary the source mod has,
                                    marked with what the destination already has
  POST /api/port/plan | /apply   -> copy them over: the block, the triggers that
                                    grant it and its text keys, in one backed-up,
                                    undoable job. See :mod:`unittransfer.portrecords`
  POST /api/m2ex                 -> {mod[, on]} -> {m2ex}. Whether the mod runs on
                                    M2EX, which replaces the engine's hardcoded
                                    ceilings - so the toolkit stops reporting
                                    them. See :mod:`unittransfer.modflags`
  POST /api/browse_folder        -> {title} -> {path}  (native OS folder dialog)
  POST /api/reveal               -> {mod, rel} -> show that file in the OS file
                                    manager. Mod-relative only.
  POST /api/image/plan           -> {mod, url, src} -> what the picture behind an
                                    /icon or /building_icon URL is, where a
                                    replacement lands, and every warning about it
                                    (resolution mismatch above all)
  POST /api/image/replace        -> the same, applied - backups + undo included
  POST /api/image/reveal         -> "Open file location" for that same URL, which
                                    can land outside the mod when the art is the
                                    game's own
  GET  /api/mods                 -> [{name, root, pack}]  (scanned under
                                    med2_root/mods, plus any mounted unit pack)

Unit packs (see :mod:`unittransfer.pack`)
  POST /api/pack/plan            -> what a pack of these units would hold
  POST /api/pack/write           -> write it to {path}
  POST /api/pack/open            -> read someone else's pack: manifest + units
  POST /api/pack/mount           -> register it as a source mod for this session;
                                    importing is then an ordinary transfer out of
                                    it, with every check that implies
  POST /api/pack/unmount         -> drop it again and delete what was unpacked
  GET  /api/units?mod=NAME       -> {mod, factions, categories, classes, units}
  GET  /icon?mod=&type=&kind=    -> image/png
  GET  /api/unit_models?mod=&type= -> the battle-model entries a unit is
                                    affiliated with + the folder each lives in
                                    (the composer's "bmdb entries only" list)
  POST /api/plan                 -> {source,dest,unit,options} -> plan preview
  POST /api/apply                -> {source,dest,unit,options} -> apply + record
  GET  /api/log[?mode=&limit=&offset=]  -> a PAGE of the log, newest first
  POST /api/undo                 -> {id} -> undo a transfer

Unit-editor mode (edits inside ONE mod, see :mod:`unittransfer.edit`)
  GET  /api/edit/unit?mod=&type= -> fields + localisation + modeldb entries
  POST /api/edit/model_folder    -> {mod,entry,target} -> where an entry's files
                                    live + what moving them would touch
  POST /api/edit/plan            -> preview an edit / delete
  POST /api/edit/apply           -> apply it (same backups + undo as a transfer)
  POST /api/browse_file          -> native file dialog (mesh/texture import)
  POST /api/browse_save          -> native Save-As dialog (unit pack export)

BMDB mode (the whole battle_models.modeldb, see :mod:`unittransfer.bmdb`)
  GET  /api/bmdb/entries?mod=    -> every entry, light (the browser list)
  GET  /api/bmdb/skeletons?mod=  -> every entry keyed by the animation skeleton(s)
                                    it uses, plus a tally per skeleton - what the
                                    soldier-model picker searches
  GET  /api/bmdb/entry?mod=&name= -> one entry, in the editor's model-card shape
  POST /api/bmdb/plan | /apply   -> edit entries that belong to no single unit
  GET  /api/bmdb/audit?mod=      -> unused entries, soldier-merge twins, orphan files
  GET  /api/bmdb/dupes?mod=      -> names the file carries twice (the game reads the
                                    first block and ignores the rest)
  POST /api/bmdb/dupes_plan | /dupes_apply
                                 -> rename or remove the copies the game never reads
  POST /api/bmdb/cleanup_plan    -> what a cleanup would move/remove
  POST /api/bmdb/cleanup_apply   -> do it (backups + undo, assets exported first)
  GET  /api/bmdb/recheck?mod=    -> what PAST cleanups removed that today's wider
                                    safety nets say they should not have
  POST /api/bmdb/recheck_revert  -> put the ticked ones back (itself undoable)
  GET  /api/bmdb/ownership?mod=&mode=units|all
                                 -> entries with no texture record for a faction
                                    that fields a unit drawn with them (or for
                                    every faction in the roster)
  POST /api/bmdb/ownership_plan | /ownership_apply
                                 -> add those records (backups + undo, through
                                    the same planner the model card uses)
  GET  /api/progress?job=ID      -> where a long job (audit / cleanup) has got to

Strat map mode (descr_model_strat.txt + data/models_strat, see
:mod:`unittransfer.stratmap`)
  GET  /api/stratmap/entries?mod= -> every strat model, with who uses it
  GET  /api/stratmap/entry?mod=&name= -> one entry, block verbatim
  GET  /api/stratmap/audit?mod=  -> unused strat models and orphan files
  POST /api/stratmap/cleanup_plan  -> what a cleanup would move/remove
  POST /api/stratmap/cleanup_apply -> do it (backups + undo, assets exported first)

Unit / info cards (see :mod:`unittransfer.cards`)
  GET  /api/cards/audit?mod=     -> cards for units that are gone, cards copied
                                    identically into several faction folders, and
                                    the sets that really do differ per faction
  POST /api/cards/plan | /apply  -> remove them, or fold them into the merc folder

Sprites mode (far-LOD unit sprites, see :mod:`unittransfer.sprites`)
  GET  /api/sprites?mod=         -> models, CFG state, what's waiting in export/,
                                    and an audit of the modeldb's sprite lines
  POST /api/sprites/prep_plan    -> what prepping generation would touch
  POST /api/sprites/prep_apply   -> write sprite_script.txt / CFG flag (or the
                                    M2TWEOP console snippet, which writes nothing)
  POST /api/sprites/revert_cfg   -> comment the bypass flag back out
  POST /api/sprites/mark         -> mark models as sprited by hand (or unmark)
  POST /api/sprites/convert_plan -> what the TGA -> .texture run would do
  POST /api/sprites/convert_apply-> run it, dedup, install into the mod
  POST /api/sprites/wire         -> point the modeldb's sprite lines at the
                                    result (backups + undo, via bmdb mode)

Home (see :mod:`unittransfer.modfiles`)
  GET  /api/mod_files?mod=       -> which of the files each module reads this mod
                                    actually has, with size + encoding, plus the
                                    campaign's in-game name

Triggers (the shared builder's vocabulary, see :mod:`unittransfer.triggers`)
  GET  /api/triggers/vocab?mod=  -> every engine condition and event, with what
                                    each condition REQUIRES and each event
                                    EXPORTS, plus this mod's own trait /
                                    ancillary / faction / culture / building
                                    names for the operand pickers

Traits mode (export_descr_character_traits.txt, see :mod:`unittransfer.traits`)
  GET  /api/traits?mod=          -> every trait, light: levels, thresholds, how
                                    many triggers feed it, how many findings
  GET  /api/trait?mod=&name=     -> one trait in full: header, levels, effects,
                                    its text keys, and the triggers that give it
  POST /api/traits/plan|/apply   -> add, edit or delete a trait and the triggers
                                    that feed it, adding any missing
                                    export_VnVs.txt keys (backups + undo)

Ancillaries mode (export_descr_ancillaries.txt, see :mod:`unittransfer.ancillaries`)
  GET  /api/ancillaries?mod=     -> every ancillary, light: type, effects, how
                                    many triggers grant it, how many findings
  GET  /api/ancillary?mod=&name= -> one in full: its lines, effects, text keys,
                                    picture and the triggers that grant it
  POST /api/ancillaries/plan|/apply
                                 -> add, edit or delete an ancillary and the
                                    triggers that grant it, adding any missing
                                    export_ancillaries.txt keys (backups + undo)
  GET  /icon?mod=&kind=ancillary&image=
                                 -> that ancillary's picture as a PNG

Factions mode (descr_sm_factions.txt, see :mod:`unittransfer.factions`)
  GET  /api/factions?mod=        -> every faction, light: culture, religion, its
                                    two map colours, horde size, findings
  GET  /api/faction?mod=&name=   -> one in full: every line, the pickers its
                                    boxes need, and its expanded.txt name
  POST /api/factions/clone_plan|/clone_apply
                                 -> ADD a faction, by cloning one that already
                                    works into all twelve files that name a slot
                                    plus its art (backups + undo, one id for the
                                    lot). See :mod:`unittransfer.factionclone`.
  POST /api/factions/plan|/apply -> edit one faction and its shown name together
                                    (backups + undo). Editing only: a faction
                                    slot lives in twelve files at once
  GET  /api/factions/audit?mod=&campaign=
                                 -> 21, D6: every faction against every file
                                    that should name it, gap or note per row,
                                    and a template to repair each one from.
                                    See :mod:`unittransfer.factionaudit`
  POST /api/factions/repair_plan|/repair_apply
                                 -> copy the records one faction is missing out
                                    of a template, with the clone's own cloners
                                    (one backup set + undo)

Raw text (21, D11, see :mod:`unittransfer.rawtext`) - the escape hatch
  GET  /api/raw/files?mod=       -> every text file the toolkit reads, grouped,
                                    with its size, encoding and which screen
                                    edits it properly
  GET  /api/raw/file?mod=&rel=   -> one file as text, its line ending and a
                                    signature the save is checked against
  POST /api/raw/plan|/apply      -> the lines a save would change and what the
                                    toolkit's own reader makes of the result;
                                    then the write (backups + undo). Refused if
                                    the file changed on disk since it was read

EDU cleanup (export_descr_unit.txt as a whole, see :mod:`unittransfer.edusort`)
  GET  /api/edu/order?mod=       -> every section and the units in it, in the
                                    order a cleanup would leave them
  POST /api/edu/sort/plan|/apply -> tidy, tier, group and reorder the whole unit
                                    file. `marks` sets a unit's tier, variant or
                                    classification; `style` is how the section
                                    banners are drawn
                                    file (one backup + undo). `plan` never
                                    returns the new text, only what would change

Campaign Map mode (the ten TGA layers and descr_regions.txt, see
:mod:`unittransfer.campmap`)
  GET  /api/map?mod=             -> the manifest: tile grid, ten layers with
                                    what is wrong with each, the region table
  GET  /api/map/layer?mod=&code=&fit=
                                 -> one layer as PNG, cached on disk by mtime
  GET  /api/map/legend?mod=&code=
                                 -> that layer's colours named and counted, and
                                    which of them means "nothing here"
  GET  /api/map/probe?mod=&x=&y= -> one tile as all ten layers name it
  GET  /api/map/markers?mod=&campaign=
                                 -> everything in descr_strat.txt that stands on
                                    a tile: settlements, characters, forts,
                                    watchtowers and trade resources (17d)
  GET  /api/map/region?mod=&name=
                                 -> one region: its record, its pixels, its
                                    neighbours, the pickers its boxes need, its
                                    mercenary pool (18a) and the two names the
                                    player reads for it (19a)
  POST /api/map/plan|/apply      -> edit one region of descr_regions.txt. The
                                    save also deletes map.rwm, because the game
                                    reads the compiled map in preference to the
                                    text (one backup set + undo)

The paint tool (16e, see :mod:`unittransfer.campaint`). Every route below acts
on one unsaved paint session per mod, held in memory; the strokes go into the
very layer images the routes above are served from, so the probe and the legend
show the unsaved map rather than the one on disk.
  GET  /api/map/palette?mod=     -> what each paintable layer may be painted,
                                    and the sea colours measured off this map
  POST /api/map/paint            -> one stroke: pointer samples in, the tiles
                                    that changed out
  POST /api/map/paint_undo|_redo -> one step of the unlimited stack
  POST /api/map/paint_state      -> what is unsaved, without changing anything
  POST /api/map/paint_discard    -> throw the session away and re-read the disk
  POST /api/map/region_start|_cancel
                                 -> the new-region wizard's record, decided
                                    before a pixel of it is painted
  POST /api/map/region_vocab     -> the wizard's pickers: the creator factions,
                                    the owners, the music types and which
                                    campaigns read this map (B1)
  POST /api/map/paint_plan|_apply
                                 -> write every painted layer, the new region's
                                    record, and (19a) the two names the player
                                    reads for it, in one backup set + undo

The validator (16f, see :mod:`unittransfer.mapcheck`). Run against the map the
session is holding, so it answers "would what I am about to save load?" rather
than "does what is on disk load?".
  GET  /api/map/check?mod=&campaign=
                                 -> every rule, its findings, what could not be
                                    checked and why, and the stamped baseline
  POST /api/map/baseline         -> stamp what is already wrong as inherited, or
                                    clear the stamp (`action`: take / clear)
  POST /api/map/fix_plan|fix_apply
                                 -> Geomod's three debugger actions, in one
                                    backup set + undo

Query, themes and information maps (16g, see :mod:`unittransfer.mapquery`)
  GET  /api/map/query/vocab?mod=&campaign=
                                 -> every filter with the values it can take,
                                    every theme and information map, and the
                                    reason on each one that cannot be asked
  GET  /api/map/colouring?mod=&code=&campaign=
                                 -> one theme or information map: the region to
                                    colour table the browser paints, its legend
                                    and any faction colour that had to be swapped
  POST /api/map/query            -> {rules, match} -> which provinces match, why
                                    each one does, and the colour table for them
  POST /api/map/export           -> the same as a TGA in the cache: one picture
                                    (`what`: colouring / query) or Geomod's batch
                                    (`what`: factions, one file per faction)

Settlements and buildings (16h, see :mod:`unittransfer.stratedit`). The first of
the three sub-phases that write descr_strat.txt itself.
  GET  /api/map/settlement?mod=&campaign=&region=
                                 -> one settlement: its fields, its buildings
                                    with what the EDB says about each, who owns
                                    it, whether it is that faction's capital,
                                    and the pickers its boxes need
  POST /api/map/settlement_plan|_apply
                                 -> edit the fields, the building list and the
                                    owner. A move is one slice of lines lifted
                                    from between two faction blocks and put back
                                    between two others (one backup + undo)

Characters, armies and the family tree (16i, see :mod:`unittransfer.stratchar`)
  GET  /api/map/faction?mod=&campaign=&faction=
                                 -> that faction's people: every character with
                                    their traits, ancillaries and army, the
                                    leader and heir, the character_records and
                                    the relative lines, and the pickers the
                                    boxes need
  POST /api/map/character_plan|_apply
                                 -> `action`: edit / add / delete / move. A new
                                    character is inserted after the faction's
                                    last one; a move is the block's own span
                                    lifted into another faction (one backup +
                                    undo)

The campaign's own settings (16j, see :mod:`unittransfer.stratcamp`). The third
sub-phase that writes descr_strat.txt, and the half of it that only ever
rewrites lines that are already there.
  GET  /api/map/campaign?mod=&campaign=
                                 -> the header's globals and flags, the three
                                    faction lists, the whole diplomacy matrix
                                    both ways, and every faction's own scalars
  POST /api/map/campaign_plan|_apply
                                 -> `what`: globals / rosters / standings /
                                    relationships / faction / create / delete.
                                    A save declares the runs of the file it may
                                    touch and how many lines it puts back, and
                                    the guard walks the two files rather than
                                    diffing them (one backup + undo)
  GET  /api/map/wins?mod=&campaign=
                                 -> descr_win_conditions.txt: every faction's
                                    long and short campaign, with the provinces
                                    checked against the map
  POST /api/map/wins_plan|_apply -> `action`: edit / add / delete, one faction's
                                    win conditions (one backup + undo)

Minor Files mode (the five small campaign files, see :mod:`unittransfer.minorfiles`)
  GET  /api/minor?mod=&tab=      -> one tab's whole list (rebels / religions /
                                    resources / cultures / names), with the
                                    findings counted per record
  GET  /api/minor/record?mod=&tab=&name=
                                 -> one record in full: its fields, spans, the
                                    pickers its boxes need and its text key
Guilds (18a, see :mod:`unittransfer.guilds`). ``export_descr_guilds.txt``, the
file the building side has refused against since Phase 12 and could not open.
  GET  /api/guilds?mod=          -> every guild, what it grants, how many trigger
                                    lines feed it, and the file's own findings
  GET  /api/guild?mod=&name=     -> one guild: its block, the triggers that award
                                    it points, and the pickers its boxes need
  POST /api/guilds/plan|/apply   -> add, edit or delete a guild and its triggers
                                    (one backup set + undo)

The campaign folder's small files (18a, see :mod:`unittransfer.campfiles`)
  GET  /api/campfiles/descriptions?mod=&campaign=
                                 -> the campaign's menu title and one row a
                                    faction, from campaign_descriptions.txt
  GET  /api/campfiles/movies?mod=&campaign=
                                 -> descr_faction_movies.xml as one row a
                                    faction, with the four movie slots
  GET  /api/campfiles/mercenaries?mod=&campaign=&region=
                                 -> every pool in descr_mercenaries.txt and
                                    which one that province draws on
  GET  /api/map/campaigns?mod=   -> 20b, D14: every campaign the mod ships, at
                                    any depth, with its dates, its rosters,
                                    what stands in it, which of the campaign
                                    folder's files it has and whether it ships
                                    map layers of its own
  POST /api/campfiles/plan|/apply
                                 -> one save over any of the three (`what`:
                                    descriptions / movies / mercenaries). A
                                    description write goes into the .txt and
                                    recompiles the .strings.bin beside it

Events and disasters (18b, see :mod:`unittransfer.campevents`). The two files
that say what happens without anybody doing it, and the first customers for
17d's marker layer after 17d itself.
  GET  /api/campevents/events?mod=&campaign=
                                 -> every block in descr_events.txt with its
                                    dates, positions and what is wrong with it
  GET  /api/campevents/disasters?mod=
                                 -> descr_disasters.txt (under world/maps/base,
                                    not in the campaign folder), same shape
  POST /api/campevents/plan|/apply
                                 -> add, edit or delete one block in either
                                    (`what`: events / disasters). Backups + undo

The names a new record needs (19a, see :mod:`unittransfer.namekeys`). Both of
these are "a record was written and the words the player reads for it were not",
and one of them closes a finding the validator reports against our own output.
  POST /api/namekeys/plan|/apply -> `what`: region_names writes the province and
                                    settlement lines of
                                    imperial_campaign_regions_and_settlement_names.txt;
                                    name_pool puts a character's name in the
                                    faction's descr_names.txt section AND gives
                                    it a key in text/names.txt, which are one job
                                    because either alone still shows a token.
                                    Both recompile the .strings.bin they wrote
                                    (one backup set + undo)

Renaming a thing whose name is its identity (19b, see :mod:`unittransfer.renames`).
  POST /api/renames/plan|/apply  -> `subject`: region / settlement / faction,
                                    `old`, `new`. The plan lists every file and
                                    line it would rewrite, every occurrence in a
                                    campaign script (which it refuses to edit),
                                    and every other line in the mod that writes
                                    the word and is left alone. One backup set
                                    for all of it - a rename half applied is a
                                    mod that will not load

  POST /api/minor/plan|/apply    -> add, edit or delete one record. A religion's
                                    save is four files at once - its block, the
                                    `religions` list, descr_religions_lookup.txt
                                    and text/religions.txt (backups + undo)

Strings mode (compiled data/text/*.strings.bin, see :mod:`unittransfer.strings`)
  GET  /api/strings?mod=         -> every archive: entry count, .txt state, size
  GET  /api/strings/entries?mod=&file=&q=&limit=&offset=
                                 -> that archive's rows, filtered and paged here
                                    rather than in the page (names.txt is 20 757)
  POST /api/strings/plan|/apply  -> edit entries, or `action: 'rebuild'` to
                                    recompile the archive from the .txt beside it
                                    (backups + undo, same as a transfer)

Sounds mode (the unit voice bank, see :mod:`unittransfer.sounds`)
  GET  /api/sounds?mod=          -> accents/classes, donors, and every unit split
                                    into "has a voice entry" / "doesn't"
  POST /api/sounds/plan | /apply -> stage voice edits, then write them (backups +
                                    undo, same as a transfer)

Buildings mode (export_descr_buildings.txt, see :mod:`unittransfer.buildings`)
  GET  /api/buildings?mod=&culture=
                                 -> every building line, light (the browser grid);
                                    `culture` picks which per-culture name shows
  GET  /api/buildings/variants?mod=&line=&culture=
                                 -> one building line beside its city/castle
                                    twin, tier by tier, with every unit marked
                                    as trained on both sides or on one
  GET  /api/building?mod=&line=&culture=
                                 -> one line in full: levels, stats, capabilities,
                                    recruit pools, which cultures have art and
                                    every culture's name / description
  GET  /api/buildings/checks?mod=&line=
                                 -> recruitment checks: units that stop being
                                    recruitable further up a chain, units one
                                    settlement type has and its city/castle twin
                                    does not, and units listed twice in a level.
                                    No `line` = every line with a finding
  GET  /api/buildings/unit?mod=&type=&culture=
                                 -> every recruit pool in the mod that trains one
                                    unit, so its numbers can be compared (and
                                    edited) across all the trees at once
  GET  /building_icon?mod=&culture=&level=&kind=&any=
                                 -> the small / constructed icon, falling back to
                                    unpacked vanilla art, then to a placeholder
  POST /api/buildings/plan|/apply-> preview then write EDB + building-name edits
                                    (backups + undo, same as a transfer). `also`
                                    carries edits to further building lines, saved
                                    in the same pass - mirroring into the castle
                                    variant and cross-tree pool edits both use it
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import urllib.parse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional

from . import (bmdb, buildings, cards, cleaner, codeview, config, dupes, edit,
               modflags, modfiles, sounds, stratmap)
from . import ancillaries, campaint, campevents, campfiles, campmap, campstrat, cas, guilds, mapcheck, mapquery, edusort, factionaudit, factionclone, factions, images, mesh, minorfiles, namekeys, portrecords, rawtext, renames, sprites, stratcamp, stratchar, stratedit, strings, traits, triggers, winconds
from . import eop as _eop
from . import logutil
from .logutil import log, setup as setup_logging
from .icons import IconCache
from .mod import Mod, ModDataError
from .transfer import (TransferOptions, plan_transfer, apply_transfer, undo, revert_to,
                       base_field_groups_for, compose_with_base, mount_base_import,
                       officer_base_import, unit_model_index)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Liveness: the page sends /api/heartbeat every few seconds and /api/bye when its
# tab closes, so the (often windowless) server shuts down instead of lingering and
# holding the port. A watchdog thread does the actual shutdown.
#: ``last_beat`` is the page's own heartbeat and is what proves a browser really
#: rendered the UI; ``last_seen`` is any other request from it. The watchdog
#: takes the later of the two, so a page that is busy fetching cannot be
#: mistaken for a page that has gone away.
_LIVENESS: Dict[str, Optional[float]] = {"last_beat": None, "pending_close": None,
                                         "last_seen": None}


def page_ever_loaded() -> bool:
    """True once a browser has actually rendered the UI and started heartbeating.

    The one trustworthy "did a browser really open?" signal. ``webbrowser.open()``
    returns True on Windows even when nothing opens (no default browser, a broken
    file association, a blocked handler), so the launcher can't rely on it - but a
    heartbeat can only come from a real page that really loaded.
    """
    return _LIVENESS["last_beat"] is not None
_BYE_GRACE = 8.0          # seconds after a tab-close beacon before we stop (survives a refresh)
#: Seconds of total silence before we stop. Generous on purpose: the cost of
#: waiting too long is a server holding a port nobody wanted; the cost of firing
#: too early is killing the tool under someone who is still using it.
_DEAD_MAN = 300.0

#: Paths that must NOT count as a sign of life. ``/api/ping`` is how a second
#: launch asks "are you already running", and answering it is not evidence that
#: anyone still has the page open.
_NOT_ALIVE = ("/api/ping", "/api/bye")


def note_request(path: str) -> None:
    """Any request from the page is proof the page is alive - not just heartbeats.

    The heartbeat used to be the only thing keeping the server up, and it is a
    ``setInterval`` in the tab: the browser throttles those in a background tab,
    and it shares the origin's ~6 connections with every unit-card request the
    grid is making. Both happened at once here - hundreds of slow icon reads out
    of a cloud-synced cache filled the connection pool, no heartbeat got through
    for two and a half minutes, and the watchdog shut down a server that was busy
    serving that very page. From the browser: black unit cards, "TypeError:
    Failed to fetch", a grey composer and a dead Settings button, all at once.

    Traffic *is* liveness, so every request now says so. The heartbeat stays as
    the proof of life for a page that is merely sitting there being read.
    """
    if path in _NOT_ALIVE:
        return
    _LIVENESS["last_seen"] = time.time()


def _restart_into(httpd, console: bool) -> None:
    """Hand this port to a fresh server, then get out of the way.

    Order matters and there is only one that works: the replacement cannot bind
    the port while we still hold it, and we cannot answer the request after we
    have stopped. So the reply goes out first, then this thread stops serving,
    closes the socket, spawns the replacement and ends the process. The page
    waits for the new server on the same address and reloads itself.
    """
    from . import startup
    app = Path(__file__).resolve().parent.parent / "app.py"
    port = httpd.server_address[1]
    # Spawn BEFORE stopping. Stopping first ends serve_forever, which unwinds
    # main() and takes the whole process with it - including this thread, before
    # it ever got to the spawn. The child is told to wait for the port instead.
    try:
        startup.spawn_server(app, ["--port", str(port), "--wait-port"],
                             console=console)
        log.info("RESTART replacement server starting%s - handing over port %d",
                 " with a console" if console else "", port)
    except Exception:
        log.error("restart: could not start the replacement - staying up",
                  exc_info=True)
        return
    try:
        httpd.shutdown()                     # stop serving (blocks until it has)
        httpd.server_close()                 # …and let go of the port
    except Exception:
        log.warning("restart: could not stop cleanly", exc_info=True)
    # This process must actually end: two servers on one port is the one outcome
    # worse than none.
    os._exit(0)


def should_stop(now: float, liveness: Optional[dict] = None) -> str:
    """'' to keep serving, otherwise why we are stopping. Pure, so it is testable.

    Two ways a server outlives its page: the tab was closed (it said so), or the
    tab went away without saying so (a crash, a killed browser). The second is a
    guess, and it used to be a bad one - see :func:`note_request`.
    """
    lv = _LIVENESS if liveness is None else liveness
    lb, pc, ls = lv["last_beat"], lv["pending_close"], lv.get("last_seen")
    alive = max(x for x in (lb, ls, 0.0) if x is not None)
    if pc is not None and now - pc > _BYE_GRACE and alive < pc:
        return "tab closed"
    if lb is not None and now - alive > _DEAD_MAN:
        return f"idle >{int(_DEAD_MAN)}s"
    return ""


def _liveness_watchdog(httpd) -> None:
    while True:
        time.sleep(2)
        why = should_stop(time.time())
        if why:
            log.info("browser %s - shutting down", why)
            threading.Thread(target=httpd.shutdown, daemon=True).start()
            return


# ---------------------------------------------------------------------------
# progress for the long jobs (the BMDB audit and the cleanup)
#
# Both are a single request that can run for many seconds, and a bar parked at a
# made-up width tells the user nothing. The page makes up a job id, passes it with
# the request and polls /api/progress?job=ID beside it; the job writes where it is
# under that id from its own thread (ThreadingHTTPServer serves the poll meanwhile).
_PROGRESS: Dict[str, dict] = {}
_PROGRESS_LOCK = threading.Lock()
_PROGRESS_TTL = 300.0        # seconds a finished job's last report is kept


def _progress_sink(job: str):
    """A ``(percent, label)`` callback the poller can read back, or ``None``."""
    job = (job or "").strip()
    if not job:
        return None

    def report(pct: int, label: str) -> None:
        now = time.time()
        with _PROGRESS_LOCK:
            for k, v in list(_PROGRESS.items()):
                if now - v["when"] > _PROGRESS_TTL:
                    _PROGRESS.pop(k, None)      # a page that never polled again
            _PROGRESS[job] = {"pct": pct, "label": label, "when": now}
    return report


def _progress_read(job: str) -> dict:
    with _PROGRESS_LOCK:
        rec = _PROGRESS.get((job or "").strip())
        return {"pct": rec["pct"], "label": rec["label"]} if rec else {}


def _strings_bin_wanted(body: dict) -> bool:
    """Whether to clear ``export_units.txt.strings.bin`` after this job.

    One setting, ``clear_strings_bin`` (on by default), decides it for every
    transfer / edit / voice change / cleanup - the game keeps showing the OLD
    unit text until that cache is gone, and it writes a fresh one on the next
    launch, so there is nothing to lose by clearing it every time.

    A job body may still say ``clear_strings_bin`` explicitly to override the
    setting for that one call (a batch transfer asks for it on its last unit
    only, and the tests switch it off).
    """
    if body.get("clear_strings_bin") is not None:
        return bool(body.get("clear_strings_bin"))
    return config.load_settings().get("clear_strings_bin", True)


def _clear_cache(mod_root, out: dict, rec: dict, mod_name: str,
                 rel: str = cleaner.STRINGS_BIN_REL) -> None:
    """Refresh the compiled cache for a finished job and record what it did.

    Recompiles it from the ``.txt`` the job just wrote where it can, and falls
    back to the old delete-and-let-the-game-rebuild where it cannot - see
    :func:`cleaner.refresh_strings_bin`.
    """
    res = cleaner.refresh_strings_bin(mod_root, rel)
    out["strings_bin"] = res
    if res.get("rebuilt"):
        log.info("CACHE  rebuilt %s in %s (%d entries)", rel, mod_name,
                 res.get("entries", 0))
    elif res.get("deleted"):
        log.info("CACHE  cleared %s in %s", rel, mod_name)
    elif res.get("missing"):
        log.info("CACHE  %s not present in %s - nothing to clear", rel, mod_name)
    else:
        log.warning("CACHE  not cleared: %s", res.get("error"))
    config.update_log(rec.get("id", ""), strings_bin=res)


def _stat_sig(path: Path) -> tuple:
    """(name, size, mtime) of one file, or a miss that compares unequal to none.

    A file that is not there and a file that is are different states, and both
    have to be noticed: a layer added to a mod while the tool is open must
    invalidate what was read without it.
    """
    try:
        st = path.stat()
        return (path.name, st.st_size, int(st.st_mtime_ns))
    except OSError:
        return (path.name, -1, -1)


def _safe_stem(name: str) -> str:
    """A mod name reduced to something safe to use as a folder name."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", (name or "pack").strip()).strip("._") or "pack"


#: How long a resolved mod is trusted before its files are stat'ed again. Short
#: enough that editing a mod's file in another program still shows up on the next
#: click; long enough that a page full of unit cards resolves the mod once
#: instead of once per card.
REVALIDATE_SECONDS = 1.0


class Registry:
    def __init__(self, cache_dir: Path):
        self.icons = IconCache(cache_dir)
        self._mods: Dict[str, Mod] = {}
        self._sigs: Dict[str, tuple] = {}      # name -> on-disk signature when cached
        # name -> extracted root, for unit packs mounted this session
        self._packs: Dict[str, Path] = {}
        # ThreadingHTTPServer serves the ~dozens of icon requests of one page
        # concurrently; Mod's cached_property parsers and this dict are not
        # thread-safe, so serialise mod resolution + first-parse behind a lock.
        self._lock = threading.RLock()
        # name -> when this mod was last checked against the disk. Every request
        # used to re-scan the mods folder and stat twelve files before it could
        # be answered, all of it inside the lock above: a screen of unit cards is
        # hundreds of requests, so they queued behind each other for no reason.
        # An on-disk edit still shows up without a restart, just up to a second
        # later - and our own writes call invalidate(), so they are immediate.
        self._checked: Dict[str, float] = {}
        # name -> (signature, CampaignMap). Its own cache rather than a field on
        # Mod: the map is half a second to read and most modes never touch it.
        self._maps: Dict[str, tuple] = {}
        #: (mod, campaign) -> (the map it was built from, the campaign
        #: files' signature, the fact table). See :meth:`map_facts`.
        self._facts: Dict[tuple, tuple] = {}

    @staticmethod
    def _signature(mod: Mod) -> tuple:
        """(size, mtime) of a mod's key data files, so an edit on disk is noticed.

        Lets a running server pick up a changed source bmdb / EDU / projectile file
        without a restart - every request rebuilds the Mod when the files move.
        """
        sig = []
        for p in (mod.edu_path, mod.export_units_path, mod.modeldb_path,
                  mod.descr_mount_path, mod.descr_projectile_path,
                  mod.descr_engines_path, mod.descr_mounted_engines_path,
                  mod.descr_engine_skeleton_path, mod.expanded_path,
                  mod.eds_path, mod.edb_path, mod.building_loc_path):
            try:
                st = p.stat()
                sig.append((p.name, st.st_size, int(st.st_mtime_ns)))
            except OSError:
                sig.append((p.name, -1, -1))
        return tuple(sig)

    # ---- mod discovery from the MED2 root ----
    def mods_root(self) -> Optional[Path]:
        root = config.get_med2_root()
        if not root:
            return None
        p = Path(root)
        # accept either the install root (has a 'mods' subfolder) or a mods folder itself
        if (p / "mods").is_dir():
            return p / "mods"
        return p

    def discover(self) -> Dict[str, Path]:
        mr = self.mods_root()
        out: Dict[str, Path] = {}
        if mr and mr.is_dir():
            for child in sorted(mr.iterdir()):
                if child.is_dir() and (child / "data").is_dir():
                    out[child.name] = child
        # A mounted unit pack is a mod like any other from here on - that is the
        # whole point of the format (see :mod:`unittransfer.pack`). Registering it
        # here means the composer, the base picker, the conflict handling, the
        # preview and the undo log all work on it with no import-specific code.
        for name, root in self._packs.items():
            if (root / "data").is_dir():
                out[name] = root
        return out

    # ---- unit packs mounted as read-only source mods ----
    def mount_pack(self, zip_path) -> dict:
        """Unpack a zip and register it as a source mod for this session."""
        from . import pack as pack_mod
        manifest = pack_mod.read_manifest(Path(zip_path))
        # named after the mod it CAME from, not the zip: the transfer engine puts
        # relocated assets in a folder named after the source, and
        # "unit_models/p-20260811-155044/" tells nobody anything
        # …and the source's name comes FIRST, because transfer._tag builds rename
        # suffixes from a mod's leading letters: "pack_Divide…" would tag every
        # renamed entry "_pack", which says nothing about where it came from.
        stem = _safe_stem(manifest.get("source_mod") or Path(zip_path).stem)
        with self._lock:
            name = f"{stem}_pack"
            n = 2
            while name in self._packs:
                name = f"{stem}_pack{n}"
                n += 1
            root = config.CONFIG_DIR / "packs" / name
            shutil.rmtree(root, ignore_errors=True)
            pack_mod.unpack(Path(zip_path), root)
            self._packs[name] = root
        log.info("PACK   mounted %s as %s", zip_path, name)
        return {"name": name, "root": str(root), "manifest": manifest}

    def unmount_pack(self, name: str) -> bool:
        with self._lock:
            root = self._packs.pop(name, None)
            self._mods.pop(name, None)
            self._sigs.pop(name, None)
        if root is None:
            return False
        shutil.rmtree(root, ignore_errors=True)
        log.info("PACK   unmounted %s", name)
        return True

    def is_pack(self, name: str) -> bool:
        return name in self._packs

    def names(self) -> List[str]:
        return list(self.discover())

    def get(self, name: str) -> Mod:
        """The mod, with its light databases already parsed."""
        return self._locate(name, warm=True)

    def describe(self, name: str) -> Mod:
        """The mod object, having read nothing.

        Home's readiness report and the M2TWEOP folder list ask only about files
        on disk. Warming the parsed databases for them meant a mod whose roster
        is missing could not even be asked WHY: the report that exists to say
        "this file is not there" was itself the request that died on it, and the
        card that should have explained the mod went blank instead.

        Deliberately does not stamp ``_checked``: the next real
        :meth:`get` must still take the slow path and warm the databases inside
        the lock, or it reopens the parse race that stamp exists to close.
        """
        return self._locate(name, warm=False)

    def _locate(self, name: str, warm: bool) -> Mod:
        with self._lock:
            fresh = self._checked.get(name)
            cached = self._mods.get(name)
            if (cached is not None and fresh is not None
                    and time.monotonic() - fresh < REVALIDATE_SECONDS):
                return cached
            paths = self.discover()
            if name not in paths:
                raise KeyError(name)
            # cache by resolved path; drop cache if the path changed OR any of the
            # mod's data files changed on disk (so edits to the source bmdb/EDU show
            # up without restarting the tool).
            key = str(paths[name])
            cached = self._mods.get(name)
            if cached is not None and str(cached.root) == key:
                if self._signature(cached) != self._sigs.get(name):
                    cached = None                # a data file changed -> reparse
            elif cached is not None:
                cached = None                    # mod path changed
            cold = cached is None
            if cold:
                cached = Mod(paths[name])
                self._mods[name] = cached
                self._sigs[name] = self._signature(cached)
            if not warm:
                # describe(): the object, not its contents - see its docstring
                return cached
            if cold:
                # The log has to say what the tool was doing while the screen was
                # still empty, and this is it: the first request for a mod reads
                # its files, everything after that is served from memory.
                log.info("PARSE  %s: reading its files (%s)", name, paths[name])
                started = time.perf_counter()
            # Warm the light parsed DBs *inside the lock* so concurrent icon /
            # units requests never trigger a cached_property parse race (which
            # would surface as sporadic 500s -> broken card images). The heavy
            # modeldb is left lazy; it's only needed by the serialised plan/apply.
            _ = cached.edu, cached.loc, cached.faction_names, cached.mounts
            if cold:
                # `faction_names` is the mod's whole name lookup, not its factions
                # (which /api/units counts) - say which, or the number reads as a
                # mod with 1941 factions in it.
                log.info("PARSE  %s: %d units, %d mounts, %d localised names in %.2fs",
                         name, len(cached.edu.units), len(cached.mounts),
                         len(cached.faction_names), time.perf_counter() - started)
            self._checked[name] = time.monotonic()
            return cached

    def invalidate(self, name: str):
        with self._lock:
            self._mods.pop(name, None)
            self._sigs.pop(name, None)
            self._checked.pop(name, None)
            self._maps.pop(name, None)
            for k in [k for k in self._facts if k[0] == name]:
                self._facts.pop(k, None)

    # ---- the campaign map, kept because building its index is not free ----

    @staticmethod
    def _map_signature(mod: Mod) -> tuple:
        """(size, mtime) of every file the map is read out of.

        The same trick as :meth:`_signature`, over a different set: the terrain
        header, the regions file and the ten layers. 16e paints through this
        server and calls :meth:`invalidate`, but a layer edited in Photoshop
        while the tool is open is a real workflow too, and this is what makes
        the next request notice.
        """
        base = mod.data / campmap.BASE_REL
        sig = []
        for rel in ("descr_terrain.txt", "descr_regions.txt"):
            sig.append(_stat_sig(base / rel))
        for ly in campmap.LAYERS:
            sig.append(_stat_sig(base / ly["file"]))
        return tuple(sig)

    @staticmethod
    def _campaign_signature(mod: Mod, campaign: str) -> tuple:
        """(size, mtime) of the campaign files the fact table is joined from.

        The map's own signature is not enough: a query reads descr_strat.txt,
        the mercenary pools and the win conditions, and none of those is a
        layer. Editing descr_strat.txt in a text editor while the panel is open
        is an ordinary workflow, and this is what makes the next query notice.
        """
        base = mod.data / campstrat.CAMPAIGN_DIR_REL / campaign
        return tuple(_stat_sig(base / rel) for rel in
                     (campstrat.STRAT_NAME, mapquery.MERCS_NAME,
                      mapquery.WIN_NAME)) + (
            _stat_sig(mod.data / mapquery.MUSIC_REL),)

    def map_facts(self, name: str, campaign: str = "") -> "mapquery.Facts":
        """This mod's campaign-map fact table, built once and kept.

        Held beside the map rather than inside it, and dropped when either the
        map object it was built from is replaced or a campaign file it was
        joined from changes on disk. The join is the expensive half of a query
        - one pass over descr_strat.txt and every settlement's buildings - and
        the filters after it are dictionary lookups, so a panel that changes a
        dropdown pays nothing.
        """
        campaign = campaign or campstrat.DEFAULT_CAMPAIGN
        mod = self.describe(name)
        cm = self.campaign_map(name)
        sig = self._campaign_signature(mod, campaign)
        with self._lock:
            held = self._facts.get((name, campaign))
            if held is not None and held[0] is cm and held[1] == sig:
                return held[2]
        facts = mapquery.Facts(mod, cm, campaign)
        with self._lock:
            self._facts[(name, campaign)] = (cm, sig, facts)
        log.info("QUERY  %s/%s: %d regions in %d ms", name, campaign,
                 len(facts.regions), facts.ms)
        return facts

    def campaign_map(self, name: str) -> "campmap.CampaignMap":
        """This mod's campaign map, read once and kept.

        Reading it is about half a second on DaC - the ten layers, the exact
        label image and the per-region pass - and every layer request, every
        probe and every stroke would otherwise pay it again. Held per mod,
        dropped when any file it was read from changes on disk.

        Raises :class:`campmap.MapError` when the mod has no map of its own,
        which is normal: most mods ship units and let the game's own map stand.

        :meth:`describe` rather than :meth:`get`, deliberately. A map needs
        ``data/world/maps/base`` and nothing else, and warming the unit
        databases first would mean a mod that ships only a map - or one whose
        roster is missing - could not have its map read at all, which is the
        same mistake Home's readiness report was fixed for.
        """
        mod = self.describe(name)
        with self._lock:
            held = self._maps.get(name)
            sig = self._map_signature(mod)
            if held is not None and held[0] == sig:
                return held[1]
            started = time.perf_counter()
            cm = campmap.CampaignMap(mod)
            # The expensive half, warmed inside the lock so two requests never
            # build it twice. Warmed in a try: a map whose layers disagree
            # cannot have an index, and refusing the whole map for it would
            # take away the one screen that says WHICH file is the wrong shape.
            # campmap.view degrades to the layer list; that is the answer here.
            try:
                regions = len(cm.index.regions)
            except campmap.MapError as exc:
                regions = -1
                log.info("MAP    %s: %s", name, exc)
            self._maps[name] = (sig, cm)
        log.info("MAP    %s: %dx%d, %s, read in %.2fs", name,
                 cm.terrain.width, cm.terrain.height,
                 f"{regions} regions" if regions >= 0 else "no index (see above)",
                 time.perf_counter() - started)
        return cm


def _engine_groups(m: Mod, u) -> list:
    """Model-group names of the unit's siege engine, for the composer's summary.

    ['normal', 'dying', 'dead'] for a typical engine, [] when the unit has none or
    the engine isn't defined in this mod (a mounted engine has no model groups).
    """
    for name, defs in ((u.engine, m.engine_defs), (u.mounted_engine, m.mounted_engine_defs)):
        if not name:
            continue
        groups = [g.name for b in defs(name) for g in b.groups]
        return list(dict.fromkeys(groups))
    return []


def _mounted_engine_class(m: Mod, u) -> str:
    """The ``descr_engine_skeleton.txt`` entry a mounted engine's ``class`` names.

    A mounted engine has no model groups (the model is the mount's), so ``class``
    is the only thing pointing at an animation set - usually ``serpentine``,
    ``rocket_launcher`` or ``ballista``. '' when the unit has no mounted engine or
    this mod doesn't define it.
    """
    if not u.mounted_engine:
        return ""
    for b in m.mounted_engine_defs(u.mounted_engine):
        if b.engine_class:
            return b.engine_class
    return ""


def _unit_payload(m: Mod, u) -> dict:
    loc = m.loc.get(u.dictionary)
    disp = (loc.name.strip() if loc and loc.name else "") or u.type
    return {
        "type": u.type, "dictionary": u.dictionary, "name": disp,
        "category": u.category, "kind": u.kind(),
        "class": u.class_type, "ownership": u.ownership,
        "eras": {"0": u.era0, "1": u.era1, "2": u.era2},
        "attributes": u.attributes, "mercenary": u.mercenary_unit,
        "models": u.model_names(),
        # the soldier line's model and the armour-upgrade list separately: when the
        # upgrade list is nothing but the soldier model, "armour upgrades from the
        # source" names no model of its own and the composer ties the two rows
        # together (see transfer._follow_soldier_upgrades)
        "soldier_model": u.soldier_model, "armour_ug_models": u.armour_ug_models,
        "officers": u.officers, "mount": u.mount,
        # crew = ship / engine / mounted_engine / animal (drives the "Crew"
        # transfer option, greyed out when the unit has none). These name entries
        # in descr_ship / descr_engines / descr_mounted_engines / descr_animals,
        # NOT battle models - the siege engine is resolved separately below.
        "crew": [x for x in (u.ship, u.engine, u.mounted_engine, u.animal) if x],
        # siege engine: the descr_engines.txt / descr_mounted_engines.txt entry
        # this unit drives, and how many blocks + model groups it spans.
        "engine": u.engine, "mounted_engine": u.mounted_engine,
        "engine_groups": _engine_groups(m, u),
        # a mounted engine has no model groups: its `class` is the skeleton name
        "engine_class": _mounted_engine_class(m, u),
        # projectile(s) the unit fires (stat_pri/stat_sec slot 3); [] for melee.
        "projectiles": u.projectiles(),
        "has_card": m.find_unit_card(u) is not None,
        "has_info": m.find_unit_info(u) is not None,
        # M2TWEOP unit: defined in one of the extender's own files rather than in
        # data/export_descr_unit.txt. The UI badges these, and the 500-unit cap
        # does not apply to them.
        "eop": u.is_eop,
        "eop_file": _eop.rel_to_root(m, u.eop_file) if u.is_eop else "",
    }


#: How many log entries one page carries.
LOG_PAGE = 40
#: A summary longer than this is cut for the LIST. Nothing is lost - the whole
#: record is still in `config/transfers.json`, and the diagnostic log has the
#: detail - but one 310 KB entry (a mod-wide cleanup's file-by-file account) must
#: not decide how long the log takes to open.
LOG_SUMMARY_CAP = 4000
#: Dropped from a listed entry. `manifest` is the backup bookkeeping undo reads
#: server-side; the page has never used it, and it is most of the file's weight.
LOG_LIST_DROP = ("manifest",)


def log_page(mode: str = "", offset: int = 0, limit: int = LOG_PAGE) -> dict:
    """One page of the transfer log, newest first, plus what the filter needs.

    The log used to be sent whole, and the panel built HTML for every entry in
    it: 480 entries, 1.1 MB of JSON and 600 KB of markup for a screen that shows
    about six. It also has to be read off disk first, which on a machine where
    `config/` is inside OneDrive is where the "opening the log takes minutes"
    report comes from.

    `counts` is over the WHOLE log (a filter has to say what it would show), and
    `newer_count` is computed here because it needs the whole log too - it is
    what "Revert to here" reverts, and the page must not have to hold 480 entries
    to work out one number.
    """
    entries = config.load_log()
    counts: Dict[str, int] = {}
    for e in entries:
        counts[e.get("mode") or "transfer"] = counts.get(e.get("mode") or "transfer", 0) + 1

    # "how many applied, not-yet-undone writes to this same mod came after it"
    newer: Dict[str, int] = {}
    seen: Dict[str, int] = {}
    for e in reversed(entries):                       # newest first
        key = e.get("dest_root") or ""
        newer[e.get("id") or ""] = seen.get(key, 0)
        if e.get("applied") and not e.get("undone"):
            seen[key] = seen.get(key, 0) + 1

    picked = [e for e in reversed(entries)
              if not mode or (e.get("mode") or "transfer") == mode]
    total = len(picked)
    offset = max(0, offset)
    page = picked[offset:offset + max(1, limit)]

    out = []
    for e in page:
        item = {k: v for k, v in e.items() if k not in LOG_LIST_DROP}
        summary = item.get("summary") or ""
        if len(summary) > LOG_SUMMARY_CAP:
            item["summary"] = summary[:LOG_SUMMARY_CAP]
            item["summary_cut"] = len(summary) - LOG_SUMMARY_CAP
        item["newer_count"] = newer.get(e.get("id") or "", 0)
        out.append(item)
    return {"entries": out, "total": total, "offset": offset, "limit": limit,
            "counts": counts, "grand_total": len(entries), "mode": mode}


def build_units_response(m: Mod) -> dict:
    started = time.perf_counter()
    units = [_unit_payload(m, u) for u in m.edu.units]
    factions = sorted({f for u in m.edu.units for f in u.ownership})
    # Which units have no card is worth saying plainly: a blank card in the grid
    # is either "this mod ships no art for it" or "the conversion failed", and
    # those look identical on screen.
    cardless = [u.type for u in m.edu.units if not m.find_unit_card(u)]
    log.info("UNITS  %s: %d units, %d with a card, %d factions in %.2fs",
             m.name, len(units), len(units) - len(cardless), len(factions),
             time.perf_counter() - started)
    if cardless:
        log.debug("UNITS  %s: %d units ship no unit card: %s", m.name, len(cardless),
                  ", ".join(cardless)[:800])
    return {
        "mod": m.name,
        "factions": factions,
        # M2TWEOP state, so the picker can show the badge legend and the settings
        # panel can say whether the folders were configured or auto-detected
        "eop_dirs": [str(p) for p in m.eop_dirs],
        "eop_configured": [str(p) for p in _eop.configured_dirs(m)],
        "eop_count": len(m.edu.eop_units),
        "edu_count": len(m.edu.main_units),
        "faction_names": {f: m.faction_names.get(f.lower(), "") for f in factions},
        # "categories" is the refined kind (cavalry split into Cavalry /
        # Cavalry_Lance / Cavalry_Archer) - it drives the filter and the base picker.
        "categories": sorted({u.kind() for u in m.edu.units if u.kind()}),
        "classes": sorted({u.class_type for u in m.edu.units if u.class_type}),
        "units": units,
    }


def _edit_payload(plan) -> dict:
    """Preview shape of an edit plan (never the whole rewritten files -
    the modeldb alone is 20+ MB on a big mod)."""
    return {
        "mod": plan.mod.name,
        "unit_type": plan.unit_type,
        "resolved_type": plan.resolved_type,
        "resolved_dict": plan.resolved_dict,
        "action": "delete" if plan.request.delete else "edit",
        "changes": plan.changes,
        "warnings": plan.warnings,
        "errors": plan.errors,
        "files_written": ([f for f, on in (("export_descr_unit.txt", plan.edu_text),
                                           ("text/export_units.txt", plan.loc_text),
                                           ("unit_models/battle_models.modeldb",
                                            plan.modeldb_touched)) if on]),
        # every other file a `type` rename reaches, with how many lines in each
        "ref_counts": [{"file": f, "hits": n} for f, n in plan.ref_counts],
        "copies": [rel for _src, rel in plan.copies],
        "icon_copies": [rel for _src, rel in plan.icon_copies]
                       + [rel for _src, rel in plan.icon_converts],
        "deletes": list(plan.deletes),
        "new_entries": [n for n, _r, _p in plan.new_entries],
        "entry_updates": sorted(plan.entry_updates.keys()),
        "entry_renames": plan.entry_renames,
        "entry_deletes": list(plan.entry_deletes),
        "summary": plan.summary(),
    }


def _cleanup_payload(plan) -> dict:
    """Preview shape of a cleanup plan (file lists capped - a big mod exports
    thousands of files and the browser only needs enough to show the user)."""
    return {
        "mod": plan.mod.name,
        "target": str(plan.target or ""),
        "entry_deletes": list(plan.entry_deletes),
        "merges": [{"entry": a, "into": b} for a, b in plan.merges],
        "mount_deletes": list(plan.mount_deletes),
        "edu_rewritten": bool(plan.edu_text),
        "mounts_rewritten": bool(plan.mount_text),
        "export_count": len(plan.exports),
        "exports": [rel for _src, rel in plan.exports[:300]],
        "kept_files": plan.kept_files[:60],
        "kept_count": len(plan.kept_files),
        "orphan_count": plan.orphan_count,
        "orphan_bytes": plan.orphan_bytes,
        "changes": plan.changes,
        "warnings": plan.warnings,
        "errors": plan.errors,
        "summary": plan.summary(),
    }


def _strat_payload(plan) -> dict:
    """Preview shape of a strat-map cleanup plan - the same fields the BMDB one
    answers with wherever the two mean the same thing, so the page's plan box is
    one function rather than two that drift."""
    return {
        "mod": plan.mod.name,
        "target": str(plan.target or ""),
        "file": stratmap.REL,
        "entry_deletes": list(plan.entry_deletes),
        "file_rewritten": bool(plan.strat_text),
        "export_count": len(plan.exports),
        "exports": [rel for _src, rel in plan.exports[:300]],
        "kept_files": plan.kept_files[:60],
        "kept_count": len(plan.kept_files),
        "orphan_count": plan.orphan_count,
        "orphan_bytes": plan.orphan_bytes,
        "changes": plan.changes,
        "warnings": plan.warnings,
        "errors": plan.errors,
        "summary": plan.summary(),
    }


def _cards_payload(plan) -> dict:
    """Preview shape of a card cleanup plan. File lists capped: consolidating a
    big mod's info cards moves three thousand files and the browser needs enough
    to show what is happening, not all of it."""
    return {
        "mod": plan.mod.name,
        "target": str(plan.target or ""),
        "removed": plan.removed,
        "consolidated": plan.consolidated,
        "freed": plan.freed,
        "copy_count": len(plan.copies),
        "copies": [rel for _src, rel in plan.copies[:200]],
        "export_count": len(plan.exports),
        "exports": [rel for _src, rel in plan.exports[:300]],
        "delete_count": len(plan.deletes),
        "changes": plan.changes,
        "warnings": plan.warnings,
        "errors": plan.errors,
        "summary": plan.summary(),
    }


def _sound_payload(plan) -> dict:
    """Preview shape of a voice-edit plan (never the whole rewritten voice bank -
    it is a megabyte of text the browser has no use for)."""
    return {
        "mod": plan.mod.name,
        "count": len(plan.ops),
        "eds_rewritten": bool(plan.eds_text),
        "edu_rewritten": bool(plan.edu_text),
        "changes": plan.changes,
        "warnings": plan.warnings,
        "errors": plan.errors,
        "summary": plan.summary(),
    }


def _building_payload(plan) -> dict:
    """Preview shape of a building-edit plan.

    Like the voice-edit preview, the rewritten file itself is deliberately left
    out - the EDB is 17k lines and the page only needs the change list."""
    return {
        "mod": plan.mod.name,
        "line": plan.line,
        "edb_rewritten": bool(plan.edb_text),
        "loc_rewritten": bool(plan.loc_text),
        "edu_rewritten": bool(plan.edu_text or plan.eop_texts),
        "modeldb_rewritten": bool(plan.modeldb_text),
        "changes": plan.changes,
        "warnings": plan.warnings,
        "errors": plan.errors,
        "summary": plan.summary(),
        # only a new tree carries these: it is the one building edit that has
        # something to say about art, and it says it rather than writing it
        "created": plan.created,
        "slots": plan.slots,
    }


def _sprite_prep_payload(plan) -> dict:
    return {
        "mod": plan.mod.name,
        "method": plan.request.method,
        "known": plan.known,
        "unknown": plan.unknown,
        "mounts": plan.mounts,
        "script_path": str(plan.script_path) if plan.script_path else "",
        "export_dir": str(plan.export_dir) if plan.export_dir else "",
        "cfg_edit": plan.cfg_edit,
        "lua": plan.lua,
        "warnings": plan.warnings,
        "summary": plan.summary(),
    }


def _sprite_convert_payload(plan) -> dict:
    return {
        "mod": plan.mod.name,
        "sets": [{"stem": s.stem, "model": s.model, "faction": s.faction,
                  "sheets": len(s.sheets)} for s in plan.sets],
        "install_dir": str(plan.install_dir) if plan.install_dir else "",
        "incomplete": plan.incomplete,
        "warnings": plan.warnings,
        "summary": plan.summary(),
    }


def _options_from(d: dict) -> TransferOptions:
    return TransferOptions(
        include_officers=bool(d.get("include_officers", True)),
        include_mount=bool(d.get("include_mount", True)),
        include_crew=bool(d.get("include_crew", True)),
        include_projectile=bool(d.get("include_projectile", True)),
        include_engine=bool(d.get("include_engine", True)),
        exclude_models=[str(m).lower() for m in (d.get("exclude_models") or [])],
        eop_target=d.get("eop_target", "auto"),
        on_conflict=d.get("on_conflict", "rename"),
        new_type=d.get("new_type") or None,
        new_dictionary=d.get("new_dictionary") or None,
        new_name=d.get("new_name") or None,
        base_type=d.get("base_type") or None,
        mode=d.get("mode", "new"),
        replace_type=d.get("replace_type") or None,
        models_only=[str(m).lower() for m in (d.get("models_only") or [])],
        import_card=bool(d.get("import_card", False)),
        import_info_card=bool(d.get("import_info_card", False)),
        soldier_from=d.get("soldier_from", "source"),
        officer_from=d.get("officer_from", "source"),
        mount_from=d.get("mount_from", "source"),
        crew_from=d.get("crew_from", "source"),
        upgrade_from=d.get("upgrade_from", "source"),
        import_mount_with_base=bool(d.get("import_mount_with_base", True)),
        import_officers_with_base=bool(d.get("import_officers_with_base", True)),
        field_overrides=dict(d.get("field_overrides") or {}),
        asset_conflict=d.get("asset_conflict", "mod_folder"),
        asset_reroute_dir=d.get("asset_reroute_dir") or None,
        icon_conflict=d.get("icon_conflict", "use_existing"),
        engine_conflict=d.get("engine_conflict", "use_existing"),
        make_mercenary=bool(d.get("make_mercenary", False)),
        merc_icons=bool(d.get("merc_icons", False)),
        sound_mode=d.get("sound_mode", "base"),
        sound_donor=d.get("sound_donor") or None,
    )


def _plan_payload(plan) -> dict:
    return {
        "unit_type": plan.unit_type,
        "resolved_type": plan.resolved_type,
        "resolved_dict": plan.resolved_dict,
        # what the player will see the unit called ("" = the source's own name)
        "resolved_name": plan.resolved_name,
        "unit_conflict": plan.unit_conflict,
        "skipped": plan.skipped,
        "on_conflict": plan.options.on_conflict,
        "base_type": plan.options.base_type or "",
        # "replace an existing unit": the destination unit rewritten in place
        # ("" in the normal mode). The composer uses it to say what happened and
        # to keep the 500-unit banner honest - a replacement adds no unit.
        "mode": plan.options.mode,
        # "battle-model entries only": no unit is written at all, so the composer
        # drops every panel that describes one and the summary reads differently
        "models_mode": plan.models_mode,
        "models_only": list(plan.options.models_only),
        "replace_type": plan.replace_type,
        "import_card": plan.options.import_card,
        "import_info_card": plan.options.import_info_card,
        "soldier_from": plan.options.soldier_from,
        "base_field_groups": list(dict.fromkeys(plan.base_field_groups)),
        "base_error": plan.base_error,
        "option_error": plan.option_error,
        "model_actions": [asdict(a) for a in plan.model_actions],
        "add_count": len(plan.add_entries),
        "asset_count": len(plan.asset_files),
        "icon_count": len(plan.icon_files),
        "asset_conflicts": [asdict(c) for c in plan.asset_conflicts],
        "asset_conflict": plan.options.asset_conflict,
        "icon_conflict": plan.options.icon_conflict,
        "mercenary": plan.mercenary,
        "sound_mode": plan.options.sound_mode,
        "sound_action": plan.sound_action,
        "sound_donor": plan.sound_donor,
        "sound_accent": plan.sound_accent,
        "sound_class": plan.sound_class,
        "sound_detail": plan.sound_detail,
        "mount_action": plan.mount_action,
        "mount_name": plan.mount_name,
        "mount_from_base_import": plan.mount_from_base_import,
        "mount_anim_donor": plan.mount_anim_donor,
        "mount_skeletons_swapped": plan.mount_skeletons_swapped,
        "officer_from_base_import": plan.officer_from_base_import,
        "officer_anim_donor": plan.officer_anim_donor,
        "officer_skeletons_swapped": plan.officer_skeletons_swapped,
        "projectile_actions": [{"name": n, "action": a, "detail": d}
                               for n, a, d in plan.projectile_actions],
        "projectile_effects_blanked": plan.projectile_effects_blanked,
        # what the M2EX destinations carry across instead of blanking
        "effect_actions": [{"name": n, "action": a, "detail": d}
                           for n, a, d in plan.effect_actions],
        "effect_assets": plan.effect_assets,
        "engine_conflict": plan.options.engine_conflict,
        "engine_actions": [{"name": n, "action": a, "detail": d}
                           for n, a, d in plan.engine_actions],
        "engine_skeleton_actions": [{"name": n, "action": a, "detail": d}
                                    for n, a, d in plan.engine_skeleton_actions],
        "engine_assets": plan.engine_assets,
        "engine_vanilla_refs": plan.engine_vanilla_refs,
        "engine_dest_overrides": plan.engine_dest_overrides,
        "reroute_dir": plan.reroute_dir,
        "relocated_count": len(plan.path_map),
        # Only EDU units count against the vanilla 500 cap - M2TWEOP units are
        # loaded from the extender's own files, which is the point of them.
        "dest_unit_count": len(plan.dest.edu.main_units),
        "dest_eop_count": len(plan.dest.edu.eop_units),
        "dest_new_units": plan.dest_new_units,
        # M2TWEOP: where this unit's block will be written ("" = the EDU)
        "eop_target": plan.options.eop_target,
        "eop_file": _eop.rel_to_root(plan.dest, plan.eop_file) if plan.eop_file else "",
        "dest_has_eop": bool(plan.dest.eop_dirs),
        "source_is_eop": bool(getattr(
            plan.source.edu.by_type().get(plan.unit_type), "is_eop", False)),
        "excluded_secondaries": plan.excluded_secondaries,
        "missing_models": plan.missing_models,
        "missing_skeletons": plan.missing_skeletons,
        # which copied model asks for each missing skeleton, and the subset the
        # Soldier row owns - the composer warns beside that row, not in general
        "skeleton_models": plan.skeleton_models,
        "soldier_model_name": plan.soldier_model_name,
        "soldier_skeletons_missing": plan.soldier_skeletons_missing(),
        # graded the same way: a missing skeleton is blamed on the slot whose fix
        # is real, and an armour-upgrade one is cosmetic rather than a crash
        "mount_skeletons_missing": plan.mount_skeletons_missing(),
        "officer_skeletons_missing": plan.officer_skeletons_missing(),
        "cosmetic_skeletons_missing": plan.cosmetic_skeletons_missing(),
        "base_soldier_model": plan.base_soldier_model,
        "soldier_anim_changed": list(plan.soldier_anim_changed),
        "missing_assets": plan.missing_assets[:20],
        "warnings": plan.warnings,
        "summary": plan.summary(),
    }


class Handler(BaseHTTPRequestHandler):
    registry: Registry = None
    # HTTP/1.0 (connection-per-request): ThreadingHTTPServer keep-alive plays
    # badly with the browser's pooled connections (sporadic "Failed to fetch").
    # The lock + atomic-cache + always-return-a-PNG fixes are what actually cure
    # the broken card icons, not connection reuse.

    def log_message(self, fmt, *args):
        # http.server's per-request line. Icons are dozens per page view, so keep
        # the request log at debug level; real actions are logged explicitly below.
        try:
            log.debug("HTTP %s", fmt % args)
        except Exception:
            pass

    # ---- io helpers ----
    def _send(self, code, body: bytes, ctype: str, headers: Optional[dict] = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        # Say the connection is closing, because it is (HTTP/1.0, above). Left
        # unsaid, the browser is free to decide otherwise and write its NEXT
        # request into a socket this handler is about to close - and a socket
        # closed with unread bytes in it is reset rather than finished, which
        # throws away the reply we just wrote. That is not theoretical: a page
        # load here would log a clean 200 for two dozen scripts and the browser
        # would receive twenty-one of them, leaving whichever modules lost the
        # race undefined. See uiFailedFiles in web/js/core.js for the other half.
        self.send_header("Connection", "close")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def _err(self, code, msg):
        self._json({"error": msg}, code)

    #: One batch of UI events may not turn into a thousand log lines.
    ACTIVITY_MAX = 60
    #: How much of one event's text is kept. A field's new value can be a whole
    #: EDU line; the record of the save has the rest.
    ACTIVITY_CHARS = 300

    def _activity(self, body: dict) -> int:
        """Write what the person did into the same log as what the tool did.

        Half of "what happened" was missing: the log recorded every file the tool
        wrote and nothing at all about the clicks that led there, so reading it
        back meant inferring intent from effects. The page reports its own actions
        here - mode opened, mod picked, record opened, field changed from X to Y,
        dialog closed with edits still pending - batched, so a burst of typing is
        one request rather than one per keystroke.

        Never trusted, only recorded: each line is truncated, the whole batch is
        capped, and it is written as text at DEBUG (the file's level) rather than
        interpreted. The UI cannot make the server do anything through here.
        """
        events = body.get("events")
        if not isinstance(events, list):
            return 0
        written = 0
        for ev in events[:self.ACTIVITY_MAX]:
            if not isinstance(ev, dict):
                continue
            what = str(ev.get("what") or "")[:60].replace("\n", " ")
            detail = str(ev.get("detail") or "")[:self.ACTIVITY_CHARS].replace("\n", " ")
            if not what:
                continue
            log.debug("UI     %-16s %s", what, detail)
            written += 1
        if len(events) > self.ACTIVITY_MAX:
            log.debug("UI     (%d more events in that batch were dropped)",
                      len(events) - self.ACTIVITY_MAX)
        return written

    def _diag(self):
        """The diagnostic log as a download.

        Served rather than merely pointed at, because "send me your log file"
        fails at the first step for most people: ``config/`` is next to the app,
        the app was unzipped somewhere they don't remember, and the log may not
        even be there (see :func:`unittransfer.logutil.setup`). A button that
        hands them the file removes every one of those steps.
        """
        # Flush first - a diagnostic download that stops one line short of the
        # thing that went wrong is worse than useless.
        for h in log.handlers:
            try:
                h.flush()
            except Exception:
                pass
        text = logutil.tail()
        path = logutil.log_path()
        if not text:
            text = (f"(no log file - logutil found nowhere writable)\n"
                    f"Expected location: {path or config.CONFIG_DIR / 'server.log'}\n")
        name = f"unit-transfer-log-{time.strftime('%Y%m%d-%H%M%S')}.txt"
        log.info("DIAG   log downloaded from the UI (%d bytes from %s)", len(text), path)
        return self._send(200, text.encode("utf-8", errors="replace"),
                          "text/plain; charset=utf-8",
                          {"Content-Disposition": f'attachment; filename="{name}"'})

    def _read_body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def _drain_body(self) -> None:
        """Consume and discard any request body (for beacons we don't parse)."""
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n:
                self.rfile.read(n)
        except (ValueError, OSError):
            pass

    # ---- GET ----
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        note_request(u.path)
        try:
            if u.path in ("/", "/index.html"):
                return self._file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            if u.path.startswith("/js/"):
                return self._web_asset(u.path)
            if u.path == "/api/ping":
                # identifies an already-running instance to a second launch
                import os as _os
                from . import __version__ as _ver
                return self._json({"app": "unit-transfer", "pid": _os.getpid(),
                                   "version": _ver})
            if u.path == "/api/settings":
                s = config.load_settings()
                # unsaved yet -> offer the registry-detected install as a prefill
                s["med2_root"] = s.get("med2_root") or config.detect_med2_root()
                return self._json(s)
            if u.path == "/api/detect_med2_root":
                # explicit re-lookup for the Settings "Auto-detect" button, on
                # demand rather than only as an initial prefill.
                return self._json({"path": config.detect_med2_root()})
            if u.path == "/api/mods":
                # `m2ex` comes off the settings table by path, not off a parsed
                # mod: this list is the header dropdown and it has to answer
                # before anything is read.
                return self._json([{"name": n, "root": str(p),
                                    "pack": self.registry.is_pack(n),
                                    "m2ex": modflags.is_m2ex(p)}
                                   for n, p in self.registry.discover().items()])
            if u.path == "/api/units":
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._json(build_units_response(self.registry.get(name)))
            if u.path == "/api/unit_models":
                # Every battle-model entry this unit is affiliated with, and the
                # folder each one's files live in - what the composer's
                # "battle-model entries only" mode ticks off (see
                # transfer.unit_model_index).
                name = (q.get("mod") or [None])[0]
                utype = (q.get("type") or [None])[0]
                if not name or name not in self.registry.names() or not utype:
                    return self._err(404, "unknown mod/unit")
                try:
                    models = unit_model_index(self.registry.get(name), utype)
                except KeyError as e:
                    return self._err(404, str(e))
                return self._json({"mod": name, "type": utype, "models": models})
            if u.path == "/api/unit_fields":
                name = (q.get("mod") or [None])[0]
                utype = (q.get("type") or [None])[0]
                if not name or name not in self.registry.names() or not utype:
                    return self._err(404, "unknown mod/unit")
                m = self.registry.get(name)
                unit = m.edu.by_type().get(utype)
                if unit is None:
                    return self._err(404, "unit not found")
                from . import edu as _edu
                return self._json({"type": utype, "fields": _edu.block_fields(unit.raw)})
            if u.path == "/api/codeview":
                # the raw text of one record plus its field->line map, for the
                # side-by-side code view. `kind` names the file shape so the
                # same endpoint serves every editor that adopts the widget.
                name = (q.get("mod") or [None])[0]
                kind = (q.get("kind") or ["edu"])[0]
                ident = (q.get("id") or [None])[0]
                if not name or name not in self.registry.names() or not ident:
                    return self._err(404, "unknown mod/record")
                # `describe` for the map's kind, `get` for the rest: a region
                # record needs data/world/maps/base and nothing else, and
                # warming the unit databases first would mean a mod that ships
                # only a map could not have its regions read at all. Same fix
                # the map routes and Home's readiness report already carry.
                mod = (self.registry.describe(name) if kind == "regions"
                       else self.registry.get(name))
                loaders = {"edu": codeview.unit_document,
                           "bmdb": codeview.entry_document,
                           "strings": codeview.strings_document,
                           "traits": codeview.trait_document,
                           "ancillaries": codeview.ancillary_document,
                           "guilds": codeview.guild_document,
                           "factions": codeview.faction_document,
                           "sounds": codeview.sounds_document,
                           "pools": codeview.pools_document,
                           "regions": codeview.region_document,
                           "edb": lambda m, i: codeview.building_document(
                               m, i, (q.get("culture") or [""])[0])}
                # the five minor files: the kind IS the tab, one name for one
                # file shape, so a tab cannot end up pointed at another's parser
                for t in minorfiles.TABS:
                    loaders[t.id] = (lambda tab_id: lambda m, i:
                                     codeview.minor_document(m, tab_id, i))(t.id)
                if kind not in loaders:
                    return self._err(400, f"no code view for '{kind}'")
                doc = loaders[kind](mod, ident)
                # `hide=1` asks for the comment-only lines to be left out of the
                # text the pane draws; `full` in the answer is still the record's
                # real bytes, and `hidden` is how they go back.
                out = codeview.view_payload(doc, (q.get("hide") or ["0"])[0] == "1")
                out["can_repair"] = codeview.can_repair(kind)
                out["can_tidy"] = codeview.can_tidy(kind)
                return self._json(out)
            if u.path == "/api/edu_vocab":
                # what the guided field editor puts in its drop-downs: the
                # engine's fixed sets plus everything THIS mod defines or uses
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._json(self.registry.get(name).edu_vocab)
            if u.path == "/api/base_fields":
                # Fields the unit would have AFTER inheriting from a destination
                # base unit - so the editor shows what will actually be written.
                return self._json(self._base_fields(q))
            if u.path == "/api/dirs":
                return self._json(self._dirs(q))
            if u.path == "/api/edit/unit":
                # everything the unit editor needs for one unit: EDU fields,
                # localisation, and each battle-model entry it points at
                name = (q.get("mod") or [None])[0]
                utype = (q.get("type") or [None])[0]
                if not name or name not in self.registry.names() or not utype:
                    return self._err(404, "unknown mod/unit")
                return self._json(edit.unit_detail(self.registry.get(name), utype))
            if u.path == "/api/progress":
                return self._json(_progress_read((q.get("job") or [""])[0]))
            if u.path in ("/api/bmdb/entries", "/api/bmdb/entry", "/api/bmdb/audit",
                          "/api/bmdb/skeletons", "/api/bmdb/ownership",
                          "/api/bmdb/recheck", "/api/bmdb/dupes"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                # reported before the mod is resolved: parsing its EDU is already
                # a second or two, and the page is showing a bar by then
                job = (q.get("job") or [""])[0]
                sink = _progress_sink(job) if job else None
                if sink:
                    sink(1, f"reading {name}'s files")
                mod = self.registry.get(name)
                if u.path == "/api/bmdb/entries":
                    return self._json(bmdb.overview(mod, progress=sink))
                if u.path == "/api/bmdb/entry":
                    return self._json(bmdb.entry_detail(mod, (q.get("name") or [""])[0]))
                if u.path == "/api/bmdb/skeletons":
                    return self._json(bmdb.skeleton_index(mod))
                if u.path == "/api/bmdb/ownership":
                    # which entries have no texture record for a faction that
                    # fields a unit drawn with them (mode=units), or for every
                    # faction in the roster (mode=all)
                    return self._json(bmdb.ownership_audit(
                        mod, (q.get("mode") or ["units"])[0], progress=sink))
                if u.path == "/api/bmdb/dupes":
                    # names the file carries more than once. The game reads the
                    # first block and ignores the rest, so the later ones are
                    # models the mod cannot reach - see unittransfer.dupes
                    log.info("BMDB   duplicate scan of %s", name)
                    return self._json(dupes.audit(mod))
                if u.path == "/api/bmdb/recheck":
                    # what PAST cleanups of this mod took out that today's wider
                    # nets would have refused to touch - see bmdb.recheck
                    log.info("BMDB   recheck of %s", name)
                    return self._json(bmdb.recheck(mod, progress=sink))
                log.info("BMDB   audit of %s", name)
                return self._json(bmdb.audit(mod, progress=sink))
            if u.path in ("/api/stratmap/entries", "/api/stratmap/entry",
                          "/api/stratmap/audit"):
                # The strat-map half of the same job: descr_model_strat.txt and
                # data/models_strat, rather than the modeldb and unit_models.
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                job = (q.get("job") or [""])[0]
                sink = _progress_sink(job) if job else None
                if sink:
                    sink(1, f"reading {name}'s files")
                mod = self.registry.get(name)
                if u.path == "/api/stratmap/entries":
                    return self._json(stratmap.overview(mod, progress=sink))
                if u.path == "/api/stratmap/entry":
                    return self._json(stratmap.entry_detail(
                        mod, (q.get("name") or [""])[0]))
                log.info("STRAT  audit of %s", name)
                return self._json(stratmap.audit(mod, progress=sink))
            if u.path == "/api/cards/audit":
                # Every unit card and info card in the mod, grouped by the
                # dictionary they belong to - see :mod:`unittransfer.cards`.
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                job = (q.get("job") or [""])[0]
                sink = _progress_sink(job) if job else None
                if sink:
                    sink(1, f"reading {name}'s files")
                log.info("CARDS  audit of %s", name)
                return self._json(cards.audit(self.registry.get(name), progress=sink))
            if u.path == "/api/sounds":
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._json(sounds.overview(self.registry.get(name)))
            if u.path in ("/api/strings", "/api/strings/entries"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                if u.path == "/api/strings":
                    return self._json(strings.overview(mod))
                # rows are filtered and paged here, not in the page: the biggest
                # archives run to five figures (see :func:`strings.entries`)
                return self._json(strings.entries(
                    mod, (q.get("file") or [""])[0], (q.get("q") or [""])[0],
                    int((q.get("limit") or [strings.PAGE])[0] or 0),
                    int((q.get("offset") or ["0"])[0] or 0)))
            if u.path == "/api/port":
                return self._json(self._port_overview(q))
            if u.path in ("/api/ancillaries", "/api/ancillary"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                if u.path == "/api/ancillaries":
                    return self._json(ancillaries.overview(mod))
                try:
                    return self._json(
                        ancillaries.detail(mod, (q.get("name") or [""])[0]))
                except KeyError as e:
                    return self._err(404, str(e))
            if u.path in ("/api/raw/files", "/api/raw/file"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                # describe, not get: a raw file is bytes on disk, and a mod whose
                # EDU will not parse is exactly the mod that needs this screen
                mod = self.registry.describe(name)
                if u.path == "/api/raw/files":
                    return self._json(rawtext.files(mod))
                try:
                    return self._json(rawtext.read(mod, (q.get("rel") or [""])[0]))
                except (rawtext.RawError, OSError) as e:
                    return self._err(404, str(e))
            if u.path == "/api/factions/audit":
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                # warmed when it can be: the census reads the EDU and the modeldb
                # off the Mod, and those must be parsed inside the registry's lock
                # (see Registry.describe). A mod whose EDU will not read is still
                # audited - that row just says so.
                try:
                    mod = self.registry.get(name)
                except Exception:
                    mod = self.registry.describe(name)
                return self._json(factionaudit.audit(
                    mod, (q.get("campaign") or [""])[0]))
            if u.path in ("/api/factions", "/api/faction"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                if u.path == "/api/factions":
                    return self._json(factions.overview(mod))
                try:
                    return self._json(factions.detail(mod, (q.get("name") or [""])[0]))
                except KeyError as e:
                    return self._err(404, str(e))
            if u.path == "/api/edu/order":
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._json(edusort.overview(self.registry.get(name)))
            if u.path in ("/api/minor", "/api/minor/record"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                which = (q.get("tab") or ["rebels"])[0]
                try:
                    if u.path == "/api/minor":
                        return self._json(minorfiles.overview(mod, which))
                    return self._json(minorfiles.detail(
                        mod, which, (q.get("name") or [""])[0]))
                except KeyError as e:
                    return self._err(404, str(e))
            if u.path in ("/api/traits", "/api/trait"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                if u.path == "/api/traits":
                    return self._json(traits.overview(mod))
                try:
                    return self._json(traits.detail(mod, (q.get("name") or [""])[0]))
                except KeyError as e:
                    return self._err(404, str(e))
            if u.path in ("/api/guilds", "/api/guild"):
                # 18a. One file, both halves: the definitions and the triggers
                # that feed them, because the two cross-checks that matter -
                # points awarded to a guild nothing declares, and a guild no
                # trigger ever feeds - need both at once.
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                try:
                    if u.path == "/api/guilds":
                        return self._json(guilds.overview(mod))
                    return self._json(guilds.detail(
                        mod, (q.get("name") or [""])[0]))
                except guilds.GuildError as e:
                    return self._err(404, e.message)
            if u.path in ("/api/campfiles/descriptions",
                          "/api/campfiles/movies",
                          "/api/campfiles/mercenaries"):
                # 18a. The campaign folder's three small files. All three are
                # per campaign, so all three take `campaign` and default to the
                # one campstrat defaults to.
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                camp = (q.get("campaign") or [campfiles.DEFAULT_CAMPAIGN])[0]
                what = u.path.rsplit("/", 1)[-1]
                try:
                    if what == "descriptions":
                        return self._json(campfiles.descr_view(mod, camp))
                    if what == "movies":
                        return self._json(campfiles.movies_view(mod, camp))
                    return self._json(campfiles.mercs_view(
                        mod, camp, (q.get("region") or [""])[0]))
                except (campfiles.CampFileError, OSError) as e:
                    return self._err(404, getattr(e, "message", str(e)))
            if u.path in ("/api/campevents/events", "/api/campevents/disasters"):
                # 18b. Events are per campaign; disasters are not - that file is
                # under world/maps/base with the layers, and one map has one set
                # of them however many campaigns are painted on it. So only the
                # first route takes `campaign`, and passing it to the other one
                # would be a lie the URL told.
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                try:
                    if u.path.endswith("/disasters"):
                        return self._json(campevents.disasters_view(mod))
                    return self._json(campevents.events_view(
                        mod, (q.get("campaign") or [campevents.DEFAULT_CAMPAIGN])[0]))
                except (campevents.CampEventError, OSError) as e:
                    return self._err(404, getattr(e, "message", str(e)))
            if u.path == "/api/triggers/vocab":
                # the condition/event vocabulary the trigger builder draws its
                # pickers from. Generated data (dev/reference/trigger_vocab.py), not code,
                # and the same for every mod - so `mod` only adds that mod's own
                # trait / ancillary / faction names as operand suggestions.
                name = (q.get("mod") or [""])[0]
                mod = (self.registry.get(name)
                       if name and name in self.registry.names() else None)
                return self._json(triggers.vocab_payload(mod))
            if u.path == "/api/mod_files":
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._json(modfiles.report(self.registry.describe(name)))
            if u.path in ("/api/buildings", "/api/building",
                          "/api/buildings/checks", "/api/buildings/unit",
                          "/api/buildings/variants"):
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                # which culture's building names to resolve - see buildings.loc_key
                culture = (q.get("culture") or [""])[0]
                if u.path == "/api/buildings":
                    return self._json(buildings.overview(mod, culture))
                if u.path == "/api/buildings/checks":
                    try:
                        return self._json(buildings.checks(mod, (q.get("line") or [""])[0]))
                    except KeyError as e:
                        return self._err(404, f"no building line {e}")
                if u.path == "/api/buildings/unit":
                    return self._json(buildings.unit_instances(
                        mod, (q.get("type") or [""])[0], culture))
                if u.path == "/api/buildings/variants":
                    # one line beside its city/castle twin, tier by tier
                    try:
                        return self._json(buildings.variant_compare(
                            mod, (q.get("line") or [""])[0], culture))
                    except KeyError as e:
                        return self._err(404, f"no building line {e}")
                return self._json(buildings.detail(mod, (q.get("line") or [""])[0],
                                                   culture))
            if u.path == "/building_icon":
                return self._building_icon(q)
            if u.path == "/preview_image":
                # Preview of a file the user just picked in the native browse
                # dialog - it lives outside the mod, so /icon (mod + unit) can't
                # reach it. Decoded to PNG rather than served raw, and only for
                # image extensions, so this can't be used to read arbitrary files.
                return self._preview_image((q.get("path") or [""])[0])
            if u.path == "/api/sprites":
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._json(sprites.overview(self.registry.get(name)))
            if u.path in ("/api/map/models", "/api/map/model",
                          "/api/map/model/geometry"):
                # 16k, and ahead of _map_route on purpose: a strat model is a
                # file in the mod, not a layer of a map, and a mod that ships
                # models and no map of its own should still preview them.
                name = (q.get("mod") or [None])[0]
                if not name or name not in self.registry.names():
                    return self._err(404, "unknown mod")
                return self._strat_model_route(u.path, name, q)
            if u.path.startswith("/api/map"):
                return self._map_route(u.path, q)
            if u.path == "/api/log":
                return self._json(log_page(
                    mode=(q.get("mode") or [""])[0],
                    offset=int((q.get("offset") or ["0"])[0] or 0),
                    limit=int((q.get("limit") or [str(LOG_PAGE)])[0] or LOG_PAGE)))
            if u.path == "/api/diag":
                return self._diag()
            if u.path == "/icon":
                return self._icon(q)
            if u.path in ("/api/model", "/api/model/geometry", "/model_texture"):
                return self._model_route(u.path, q)
            return self._err(404, "not found")
        except ModDataError as e:
            # A file this mod needs is missing or will not parse. The sentence is
            # the whole answer - which file, and where in it - so it goes back as
            # the reply rather than into a traceback nobody reads, and the log
            # keeps one line instead of twenty.
            log.warning("GET %s: %s", u.path, e)
            return self._err(409, str(e))
        except KeyError as e:
            # an unknown mod / unit / model entry is a 404, not a server fault
            log.warning("GET %s: not found: %s", u.path, e)
            return self._err(404, str(e))
        except Exception as e:
            log.exception("GET %s failed: %s", u.path, e)
            return self._err(500, f"{type(e).__name__}: {e}")

    # `_send` already withholds the body for HEAD, so the same routing serves both
    # - without this, BaseHTTPRequestHandler answers every HEAD with a 501.
    do_HEAD = do_GET

    # ---- POST ----
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        note_request(u.path)
        # liveness signals: no body needed, kept out of the body-parsing path so a
        # sendBeacon (empty/other content-type) can't 500.
        if u.path == "/api/heartbeat":
            _LIVENESS["last_beat"] = time.time()
            _LIVENESS["pending_close"] = None
            self._drain_body()
            return self._json({"ok": True})
        if u.path == "/api/bye":
            _LIVENESS["pending_close"] = time.time()
            self._drain_body()
            return self._json({"ok": True})
        try:
            body = self._read_body()
            if u.path == "/api/activity":
                return self._json({"ok": self._activity(body)})
            if u.path == "/api/settings":
                s = config.save_settings(**body)
                return self._json(s)
            if u.path == "/api/browse_folder":
                # a browser page can't hand back a real filesystem path from its
                # own file input, so pop the OS's native folder dialog instead -
                # the server IS this machine, unlike a normal web app.
                from .folder_dialog import browse_for_folder
                path = browse_for_folder(body.get("title") or "Select a folder")
                return self._json({"path": path})
            if u.path == "/api/reveal":
                # "Open file location". The page sends the mod and a path
                # RELATIVE to that mod's data folder, never an absolute one, so
                # a reveal cannot be aimed at anything the mod does not own.
                name = body.get("mod") or ""
                if name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                root = mod.data.resolve()
                try:
                    target = (mod.data / str(body.get("rel") or "")).resolve()
                    target.relative_to(root)
                except (ValueError, OSError):
                    return self._json({"ok": False,
                                       "error": "that path is not inside the mod"})
                if not target.exists():
                    return self._json({"ok": False,
                                       "error": "that file is not there any more"})
                from .folder_dialog import reveal
                return self._json({"ok": reveal(str(target)),
                                   "path": str(target)})
            if u.path in ("/api/image/plan", "/api/image/replace",
                          "/api/image/reveal"):
                # "Replace this picture" for any art the page shows. The body
                # carries the very URL the <img> was given, because that is the
                # only thing the page reliably knows about a picture it did not
                # resolve itself; `images.parse_url` refuses anything that is
                # not one of the two image routes, and every path it hands back
                # is resolved under the mod's own data folder.
                name = body.get("mod") or ""
                if name not in self.registry.names():
                    return self._err(404, "unknown mod")
                mod = self.registry.get(name)
                van = config.get_vanilla_ui_root()
                try:
                    if u.path == "/api/image/plan":
                        return self._json(images.plan(
                            mod, body.get("url") or "", body.get("src") or "", van))
                    if u.path == "/api/image/reveal":
                        spot = images.reveal_target(mod, body.get("url") or "", van)
                        if spot["ok"]:
                            from .folder_dialog import reveal
                            spot["ok"] = reveal(spot["path"])
                            if not spot["ok"]:
                                spot["error"] = "that folder could not be opened"
                        return self._json(spot)
                    out = images.apply(
                        mod, body.get("url") or "", body.get("src") or "", van)
                except ValueError as exc:
                    return self._json({"ok": False, "error": str(exc)})
                self.registry.invalidate(name)  # the art on disk changed under us
                return self._json(out)
            if u.path == "/api/eop_dirs":
                return self._json(self._eop_dirs(body))
            if u.path == "/api/m2ex":
                return self._json(self._m2ex(body))
            if u.path == "/api/browse_file":
                # same reason as browse_folder: the editor needs a real path to
                # the .mesh/.texture being imported, which a file input can't give.
                from .folder_dialog import browse_for_file
                path = browse_for_file(body.get("title") or "Select a file",
                                       body.get("filter") or "",
                                       body.get("dir") or "")
                return self._json({"path": path})
            if u.path == "/api/browse_save":
                # …and the other direction, for writing a unit pack out
                from .folder_dialog import browse_for_save
                path = browse_for_save(body.get("title") or "Save as",
                                       body.get("filter") or "",
                                       body.get("dir") or "",
                                       body.get("name") or "",
                                       body.get("ext") or "")
                return self._json({"path": path})
            if u.path == "/api/edit/model_folder":
                # "do all this entry's files live in one folder, and who else
                # would a move affect" - answered before the user commits to it.
                mod = self.registry.get(body.get("mod") or "")
                return self._json(edit.model_folder_report(
                    mod, body.get("entry") or "", body.get("target") or ""))
            if u.path in ("/api/codeview/parse", "/api/codeview/render",
                          "/api/codeview/repair", "/api/codeview/tidy"):
                return self._json(self._codeview(u.path.rsplit("/", 1)[-1], body))
            if u.path == "/api/edit/plan":
                return self._json(self._edit_plan(body))
            if u.path == "/api/edit/apply":
                return self._json(self._edit_apply(body))
            if u.path == "/api/bmdb/plan":
                mod = self.registry.get(body["mod"])
                return self._json(_edit_payload(
                    edit.plan_bmdb(mod, edit.bmdb_request_from_dict(body))))
            if u.path == "/api/bmdb/apply":
                return self._json(self._bmdb_apply(body))
            if u.path == "/api/cards/plan":
                mod = self.registry.get(body["mod"])
                return self._json(_cards_payload(cards.plan_cleanup(
                    mod, cards.cleanup_request_from_dict(body))))
            if u.path == "/api/cards/apply":
                return self._json(self._cards_cleanup(body))
            if u.path == "/api/stratmap/cleanup_plan":
                mod = self.registry.get(body["mod"])
                return self._json(_strat_payload(stratmap.plan_cleanup(
                    mod, stratmap.cleanup_request_from_dict(body))))
            if u.path == "/api/stratmap/cleanup_apply":
                return self._json(self._strat_cleanup(body))
            if u.path in ("/api/bmdb/ownership_plan", "/api/bmdb/ownership_apply"):
                return self._json(self._bmdb_ownership(
                    body, apply=u.path.endswith("apply")))
            if u.path in ("/api/bmdb/dupes_plan", "/api/bmdb/dupes_apply"):
                return self._json(self._bmdb_dupes(
                    body, apply=u.path.endswith("apply")))
            if u.path == "/api/bmdb/cleanup_plan":
                mod = self.registry.get(body["mod"])
                return self._json(_cleanup_payload(bmdb.plan_cleanup(
                    mod, bmdb.cleanup_request_from_dict(body))))
            if u.path == "/api/bmdb/cleanup_apply":
                return self._json(self._bmdb_cleanup(body))
            if u.path == "/api/bmdb/recheck_revert":
                return self._json(self._bmdb_recheck_revert(body))
            if u.path in ("/api/strings/plan", "/api/strings/apply"):
                return self._json(self._strings(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/traits/plan", "/api/traits/apply"):
                return self._json(self._traits(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/ancillaries/plan", "/api/ancillaries/apply"):
                return self._json(self._ancillaries(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/port/plan", "/api/port/apply"):
                return self._json(self._port(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/factions/plan", "/api/factions/apply"):
                return self._json(self._factions(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/factions/clone_plan", "/api/factions/clone_apply"):
                return self._json(
                    self._faction_clone(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/factions/repair_plan", "/api/factions/repair_apply"):
                return self._json(
                    self._faction_repair(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/raw/plan", "/api/raw/apply"):
                return self._json(self._raw(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/minor/plan", "/api/minor/apply"):
                return self._json(self._minor(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/guilds/plan", "/api/guilds/apply"):
                return self._json(self._guilds(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/campfiles/plan", "/api/campfiles/apply"):
                return self._json(self._campfiles(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/campevents/plan", "/api/campevents/apply"):
                return self._json(self._campevents(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/namekeys/plan", "/api/namekeys/apply"):
                return self._json(self._namekeys(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/renames/plan", "/api/renames/apply"):
                return self._json(self._renames(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/map/plan", "/api/map/apply"):
                return self._json(self._map_write(u.path.rsplit("/", 1)[-1], body))
            if (u.path.startswith("/api/map/paint")
                    or u.path in ("/api/map/region_start", "/api/map/region_cancel",
                                  "/api/map/region_vocab")):
                return self._json(self._paint(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/map/settlement_plan", "/api/map/settlement_apply"):
                return self._json(self._settlement(
                    u.path.rsplit("_", 1)[-1], body))
            if u.path in ("/api/map/character_plan", "/api/map/character_apply"):
                return self._json(self._character(
                    u.path.rsplit("_", 1)[-1], body))
            if u.path in ("/api/map/campaign_plan", "/api/map/campaign_apply"):
                return self._json(self._campaign(
                    u.path.rsplit("_", 1)[-1], body))
            if u.path in ("/api/map/wins_plan", "/api/map/wins_apply"):
                return self._json(self._wins(
                    u.path.rsplit("_", 1)[-1], body))
            if u.path in ("/api/map/query", "/api/map/export"):
                return self._json(self._mapquery(
                    u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/map/baseline", "/api/map/fix_plan",
                          "/api/map/fix_apply"):
                return self._json(self._mapcheck(u.path.rsplit("/", 1)[-1], body))
            if u.path in ("/api/edu/sort/plan", "/api/edu/sort/apply"):
                return self._json(self._edu_sort(u.path.rsplit("/", 1)[-1], body))
            if u.path == "/api/sounds/plan":
                mod = self.registry.get(body["mod"])
                return self._json(_sound_payload(
                    sounds.plan_sounds(mod, sounds.ops_from_dicts(body.get("ops")))))
            if u.path == "/api/sounds/apply":
                return self._json(self._sounds_apply(body))
            if u.path.startswith("/api/pack/"):
                return self._json(self._pack(u.path.rsplit("/", 1)[-1], body))
            if u.path == "/api/buildings/plan":
                mod = self.registry.get(body["mod"])
                return self._json(_building_payload(buildings.plan_edit(mod, body)))
            if u.path == "/api/buildings/apply":
                return self._json(self._buildings_apply(body))
            if u.path == "/api/buildings/ownership":
                # asked on demand rather than baked into /api/building: it needs
                # the heavy modeldb parse, and only the clause editor wants it
                mod = self.registry.get(body["mod"])
                return self._json({"rows": buildings.ownership_report(
                    mod, body.get("checks"))})
            if u.path.startswith("/api/sprites/"):
                return self._json(self._sprites(u.path.rsplit("/", 1)[-1], body))
            if u.path == "/api/plan":
                return self._json(self._plan(body))
            if u.path == "/api/apply":
                return self._json(self._apply(body))
            if u.path == "/api/undo":
                log.info("UNDO   id=%s", body.get("id"))
                rec = undo(body["id"])
                if rec.get("dest"):
                    self.registry.invalidate(rec["dest"])   # dest files changed on disk
                log.info("UNDO   restored %r in %s", rec.get("resolved_type"), rec.get("dest"))
                return self._json(rec)
            if u.path == "/api/restart":
                # "Keep the console window open" is read once, at launch, so a
                # session that is already running cannot grow a console - which
                # is why ticking the box looked like it did nothing. This puts the
                # setting into effect now: reply first, then let go of the port
                # and start a replacement, with or without a console as asked.
                want_console = bool(body.get("console"))
                log.info("RESTART requested from the UI (console=%s)", want_console)
                self._json({"ok": True, "console": want_console})
                threading.Thread(target=_restart_into, args=(self.server, want_console),
                                 daemon=True).start()
                return None
            if u.path == "/api/quit":
                log.info("QUIT requested from the UI - shutting down")
                # Silent mode has no console to Ctrl+C, so the UI can stop us.
                # shutdown() blocks until serve_forever returns, so it must not
                # run on this handler's thread.
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return self._json({"ok": True, "message": "server stopping"})
            if u.path == "/api/revert":
                log.info("REVERT to id=%s", body.get("id"))
                res = revert_to(body["id"])
                if res.get("dest"):
                    self.registry.invalidate(res["dest"])
                log.info("REVERT %s: undid %d newer transfer(s)",
                         res.get("dest"), res.get("count", 0))
                return self._json(res)
            return self._err(404, "not found")
        except ModDataError as e:
            # see the same handler in do_GET: a mod's own broken or absent file
            # is answered with the sentence, not a stack trace
            log.warning("POST %s: %s", u.path, e)
            return self._err(409, str(e))
        except KeyError as e:
            log.warning("POST %s: not found: %s", u.path, e)
            return self._err(404, str(e))
        except Exception as e:
            log.exception("POST %s failed: %s", u.path, e)
            return self._err(500, f"{type(e).__name__}: {e}")

    def _plan(self, body):
        src = self.registry.get(body["source"])
        dest = self.registry.get(body["dest"])
        plan = plan_transfer(src, body["unit"], dest, _options_from(body.get("options", {})))
        return _plan_payload(plan)

    def _apply(self, body):
        src = self.registry.get(body["source"])
        dest = self.registry.get(body["dest"])
        plan = plan_transfer(src, body["unit"], dest, _options_from(body.get("options", {})))
        log.info("APPLY  %r  %s -> %s%s", body["unit"], body["source"], body["dest"],
                 f" (base={plan.options.base_type})" if plan.options.base_type else "")
        rec = apply_transfer(plan)
        self.registry.invalidate(body["dest"])   # dest files changed on disk
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        log.info("APPLY  done id=%s  (%s)", rec.get("id"),
                 "skipped" if plan.skipped else f"type={plan.resolved_type!r}")
        out = {"record": rec, "plan": _plan_payload(plan)}
        # Clear the localisation cache so the new unit's text actually shows up.
        # A batch asks for it on its final unit and no earlier.
        if _strings_bin_wanted(body) and not plan.skipped:
            _clear_cache(dest.root, out, rec, dest.name)
        return out

    # ---- code view ----
    def _codeview(self, what, body):
        """Re-read hand-edited text, re-serialise GUI edits, or repair text.

        Every answer carries the same shape as ``GET /api/codeview`` so the
        widget has one code path, and a text the parser rejects comes back as
        ``{ok: false, error, line}`` rather than an HTTP error: the page shows it
        beside the offending line and keeps the state it already had.

        The per-kind context (which mod, which entry's padding, the text last
        known good) is assembled by :func:`codeview.context` - the endpoints
        deliberately don't know what each kind needs, so a new kind adds nothing
        here. ``base`` from the request wins over the on-disk text, because after
        a hand edit the pane's own last-good text is what a repair must diff
        against.
        """
        kind = body.get("kind") or "edu"
        mod_name = body.get("mod") or ""
        # The pane may be hiding this record's comment-only lines, in which case
        # `text` is the view and `hidden` holds the rest. Everything below works
        # on the REAL text: the comments go back before a parser or a serialiser
        # ever sees it, and the answer hides them again.
        hide = bool(body.get("hide"))
        text = codeview.show_comments(kind, body.get("text") or "",
                                      body.get("hidden") or [])
        try:
            ctx = (codeview.context(kind, self.registry.get(mod_name),
                                    body.get("id") or "", body.get("culture") or "")
                   if mod_name in self.registry.names() else {})
            if body.get("base"):
                ctx = dict(ctx, base=body["base"])
            if what == "parse":
                doc = codeview.parse(kind, text, ctx)
            elif what == "repair":
                doc = codeview.repair(kind, text, ctx)
            elif what == "tidy":
                doc = codeview.tidy(kind, text, ctx)
            else:
                doc = codeview.render(kind, body.get("base") or "",
                                      body.get("edits") or {}, ctx)
        except codeview.CodeViewError as e:
            # the line the parser objected to counts the comments the pane is
            # not showing, so it is moved onto the view's numbering - pointing
            # at the wrong line is worse than pointing at none
            line = e.line
            if hide and line and what != "render":
                line = codeview.line_map(kind, text).get(line, 0) or line
            return {"ok": False, "error": e.message, "line": line}
        out = codeview.view_payload(doc, hide)
        out["ok"] = True
        return out

    # ---- edit mode ----
    def _edit_plan(self, body):
        mod = self.registry.get(body["mod"])
        plan = edit.plan_edit(mod, edit.request_from_dict(body))
        return _edit_payload(plan)

    def _edit_apply(self, body):
        mod = self.registry.get(body["mod"])
        plan = edit.plan_edit(mod, edit.request_from_dict(body))
        log.info("EDIT   %r in %s (%s)", plan.unit_type, mod.name,
                 "delete" if plan.request.delete else "edit")
        rec = edit.apply_edit(plan)
        self.registry.invalidate(body["mod"])       # files changed on disk
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        log.info("EDIT   done id=%s", rec.get("id"))
        out = {"record": rec, "plan": _edit_payload(plan)}
        if _strings_bin_wanted(body):
            _clear_cache(mod.root, out, rec, mod.name)
        return out

    # ---- sounds mode ----
    def _sounds_apply(self, body):
        mod = self.registry.get(body["mod"])
        plan = sounds.plan_sounds(mod, sounds.ops_from_dicts(body.get("ops")))
        if plan.errors:
            return {"error": "; ".join(plan.errors), "plan": _sound_payload(plan)}
        log.info("VOICE  %d edit(s) in %s", len(plan.ops), mod.name)
        rec = sounds.apply_sounds(plan)
        self.registry.invalidate(body["mod"])       # files changed on disk
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        log.info("VOICE  done id=%s", rec.get("id"))
        out = {"record": rec, "plan": _sound_payload(plan)}
        # a voice change can move the `accent` / `voice_type` lines in the EDU,
        # so clear the unit-text cache here too
        if _strings_bin_wanted(body):
            _clear_cache(mod.root, out, rec, mod.name)
        return out

    # ---- buildings mode ----
    def _buildings_apply(self, body):
        mod = self.registry.get(body["mod"])
        plan = buildings.plan_edit(mod, body)
        if plan.errors:
            return {"error": "; ".join(plan.errors), "plan": _building_payload(plan)}
        if not (plan.edb_text or plan.loc_text or plan.edu_text or plan.eop_texts
                or plan.modeldb_text):
            return {"error": "nothing to change", "plan": _building_payload(plan)}
        log.info("BUILD  %r in %s (%d change(s))", plan.line, mod.name, len(plan.changes))
        rec = buildings.apply_edit(plan)
        self.registry.invalidate(body["mod"])       # files changed on disk
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        log.info("BUILD  done id=%s", rec.get("id"))
        out = {"record": rec, "plan": _building_payload(plan)}
        # a renamed building writes text/export_buildings.txt, whose compiled
        # .strings.bin would otherwise keep showing the old name in game
        if plan.loc_text and _strings_bin_wanted(body):
            _clear_cache(mod.root, out, rec, mod.name,
                         cleaner.BUILDINGS_STRINGS_BIN_REL)
        return out

    # ---- strings archives ----
    def _strings(self, action, body):
        """Preview or write one ``*.strings.bin``.

        Same plan-then-apply shape as every other editor, so the page can show
        exactly what a save would do before it does it. A file or row this mod
        does not have comes back as ``{error}`` rather than an HTTP failure -
        the browser is showing a list that may be a moment out of date.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = strings.plan(mod, body)
        except strings.StringsError as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.data:
            out["error"] = "nothing to change"
            return out
        out["record"] = strings.apply(plan)
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- traits ----
    def _traits(self, action, body):
        """Preview or write one trait, its triggers and its text keys together.

        Same plan-then-apply shape as every other editor. A save here can touch
        the EDCT twice over (the trait block and the triggers hundreds of lines
        below it) and ``export_VnVs.txt`` as well - one job, one backup set, one
        undo, because half of it landing is a mod that crashes.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = traits.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.text and not plan.loc_writes:
            out["error"] = "nothing to change"
            return out
        out.update(traits.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- guilds (18a) ----
    def _guilds(self, action, body):
        """Preview or write one guild and the triggers that feed it.

        The traits handler's shape, because it is the same job over the same
        two-halves-of-one-file grammar: the block and the triggers hundreds of
        lines below it go into one backup set and come back on one undo.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = guilds.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.text:
            out["error"] = "nothing to change"
            return out
        out.update(guilds.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- the campaign folder's small files (18a) ----
    def _campfiles(self, action, body):
        """Preview or write one of the three: descriptions, movies, mercenaries.

        One handler over three files because a save is the same shape for all
        three - ``what`` says which - and because two of them can be edited from
        the same faction screen, where two handlers would mean two undo entries
        for one visible action.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = campfiles.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.text and not plan.loc_writes:
            out["error"] = "nothing to change"
            return out
        out.update(campfiles.apply(plan))
        self.registry.invalidate(body["mod"])       # the files changed on disk
        return out

    # ---- events and disasters (18b) ----
    def _campevents(self, action, body):
        """Preview or write one block of descr_events or descr_disasters.

        The campfiles handler's shape over two files instead of three, and for
        the same reason: a save is the same shape for both, ``what`` says which,
        and one handler means one undo entry per visible action.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = campevents.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.text:
            out["error"] = "nothing to change"
            return out
        out.update(campevents.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    def _namekeys(self, action, body):
        """Preview or write the text a new region or a new character needs (19a).

        Two subjects and one handler, because both are the same sentence: a
        record exists and the words the player reads for it do not. ``what``
        says which - ``region_names`` is one file, ``name_pool`` is two written
        together, and either way it is one undo entry for one visible action.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = namekeys.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        out.update(namekeys.apply(plan))
        self.registry.invalidate(body["mod"])       # the files changed on disk
        return out

    def _renames(self, action, body):
        """Preview or write a rename of a province, a settlement or a faction (19b).

        One handler for all three because they are one engine: the name is the
        identity, the files that point at it are found by asking each file's own
        parser which of its lines may hold one, and the campaign script is
        reported line by line and never written. ``subject`` says which.

        The preview is the whole point of the split - a faction rename in a real
        mod rewrites twenty-four files and four thousand lines, and nobody should
        be asked to agree to that without seeing the list first.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = renames.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        out.update(renames.apply(plan))
        self.registry.invalidate(body["mod"])       # the whole mod changed
        return out

    # ---- ancillaries ----
    def _ancillaries(self, action, body):
        """Preview or write one ancillary, its triggers and its text keys together.

        The traits handler with one word changed - the two editors share their
        request shape because they share their file format.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = ancillaries.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.text and not plan.loc_writes:
            out["error"] = "nothing to change"
            return out
        out.update(ancillaries.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- porting a trait / an ancillary between two mods ----
    def _port_overview(self, q):
        """Every record the source mod has, marked with what the destination has.

        The only GET in the toolkit that names two mods, because it is the only
        answer that depends on both: "which of these 799 traits does the other
        mod already have" is the question the picker opens on.
        """
        names = self.registry.names()
        src = (q.get("source") or [""])[0]
        dst = (q.get("dest") or [""])[0]
        if src not in names or dst not in names:
            return {"error": "pick two mods this toolkit can see"}
        try:
            return portrecords.overview(self.registry.get(src),
                                        self.registry.get(dst),
                                        (q.get("kind") or ["traits"])[0])
        except (portrecords.PortError, OSError, ValueError) as e:
            return {"error": str(e)}

    def _port(self, action, body):
        """Preview or write a port: the blocks, their triggers and their text.

        Same plan-then-apply shape as every other editor, and the same backup
        set - one job, because a definition that lands without its text keys is
        a crash the first time anyone gets the record.
        """
        names = self.registry.names()
        src, dst = body.get("source") or "", body.get("dest") or ""
        if src not in names or dst not in names:
            return {"error": "pick two mods this toolkit can see"}
        try:
            plan = portrecords.plan(
                self.registry.get(src), self.registry.get(dst),
                body.get("kind") or "traits",
                [str(n) for n in (body.get("names") or [])],
                with_triggers=body.get("with_triggers", True),
                overwrite=bool(body.get("overwrite")))
        except (portrecords.PortError, KeyError, OSError, ValueError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.text and not plan.loc_writes:
            out["error"] = "nothing to change"
            return out
        out.update(portrecords.apply(plan))
        self.registry.invalidate(dst)               # the files changed on disk
        return out

    # ---- factions ----
    def _factions(self, action, body):
        """Preview or write one faction and its shown name together.

        Editing only, and the refusal is the format's: a faction slot lives in
        twelve files at once, so one that exists only in this file is a
        mod that will not load - see :data:`factions.REFUSED`.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = factions.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.touched():
            out["error"] = "nothing to change"
            return out
        out.update(factions.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- adding a faction, by cloning one that works ----
    def _faction_clone(self, action, body):
        """Preview or write a whole new faction slot copied from an existing one.

        The other half of :meth:`_factions`' refusal. That one will not create a
        slot because a slot lives in twelve files; this one creates it *in* all
        twelve - see :mod:`unittransfer.factionclone`, which also says why
        ``descr_strat.txt`` is reported rather than written.

        One transfer id covers every file and every copied picture, so undo puts
        the whole faction back out of existence in one go.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = factionclone.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "clone_plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.touched():
            out["error"] = "nothing to change"
            return out
        out.update(factionclone.apply(plan))
        # twelve files and a folder of art changed: everything cached about this
        # mod is now stale, the faction roster most of all
        self.registry.invalidate(body["mod"])
        return out

    # ---- repairing a faction from a template (21, D6) ----
    def _faction_repair(self, action, body):
        """Preview or write the records one faction is missing, copied out of
        another - see :mod:`unittransfer.factionaudit`.

        The clone's handler over the clone's plan and the clone's write, pointed
        at a slot that already exists, so it is one backup set and one undo for
        however many files the repair touches.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = factionaudit.repair_plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "repair_plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        out.update(factionclone.apply(plan))
        self.registry.invalidate(body["mod"])
        return out

    # ---- the raw text editor (21, D11) ----
    def _raw(self, action, body):
        """Preview or write one whole text file - see :mod:`unittransfer.rawtext`.

        The plan is the confirmation's content: the lines that change, and what
        the toolkit's own reader makes of the result. The write is one backup
        and one log entry, so the Log's Undo takes it back like any other.
        """
        try:
            mod = self.registry.describe(body["mod"])
            plan = rawtext.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        out.update(rawtext.apply(plan))
        # any file at all may have changed, so everything cached is suspect
        self.registry.invalidate(body["mod"])
        return out

    # ---- the EDU cleanup ----
    def _edu_sort(self, action, body):
        """Preview or write a whole-file cleanup of ``export_descr_unit.txt``.

        One file, so one backup and one undo entry - but the widest single write
        in the toolkit, which is why :func:`edusort.plan` refuses to hand over a
        text that is not purely a reordering of the one it read.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = edusort.plan(
                mod,
                banners=body.get("banners", True), tidy=body.get("tidy", True),
                group=body.get("group", True), tiers=body.get("tiers", True),
                hand=body.get("hand"),
                # the ordering screen's per-unit tier / variant / classification
                marks=body.get("marks"),
                # and how the section banners it writes are drawn
                style=body.get("style"))
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.touched():
            out["error"] = "nothing to change"
            return out
        out.update(edusort.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- minor files ----
    def _minor(self, action, body):
        """Preview or write one record of one of the five small campaign files.

        The ancillaries handler with a tab on it. What is different is on the
        other side: a religion's save writes four files, so ``plan`` is what says
        which - and all four ride one backup set, because a religion that reaches
        three of them is a religion that half exists.
        """
        try:
            mod = self.registry.get(body["mod"])
            plan = minorfiles.plan(mod, body)
        except (KeyError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        if not plan.touched():
            out["error"] = "nothing to change"
            return out
        out.update(minorfiles.apply(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- the campaign map, written ----
    def _map_write(self, action, body):
        """Preview or write one region of ``descr_regions.txt``.

        The minor-files handler with a different plan in it, and one thing of
        its own: the mod is reached through :meth:`Registry.describe` rather
        than :meth:`get`, for the same reason the map is read that way - a mod
        that ships a map and no roster still has a map to edit.

        A save deletes ``map.rwm``, which is why the answer says so: the game
        reads the compiled binary in preference to the text files, and a mod
        whose regions changed under a stale one loads the old map and shows
        none of the edit.
        """
        try:
            mod = self.registry.describe(body["mod"])
            plan = campmap.plan_region(mod, body)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        out.update(campmap.apply_region(plan))
        self.registry.invalidate(body["mod"])       # the file changed on disk
        return out

    # ---- the campaign map, painted ----
    def _paint(self, action, body):
        """Every stroke, undo and save of the paint tool (16e).

        One session per mod, and it is fetched rather than created here so the
        one thing that can lose work says so: the session holds the
        :class:`~unittransfer.campmap.CampaignMap` it painted, and
        :meth:`Registry.campaign_map` hands back a different object once a file
        the map was read from changes on disk. When that happens the strokes are
        gone, and every answer from then on carries ``reset`` saying why -
        rather than a fresh session appearing silently under somebody's hand.

        A save invalidates the mod, which drops the map, which is what makes the
        next request re-read the layers this one just wrote.
        """
        try:
            name = body["mod"]
            mod = self.registry.describe(name)
            cm = self.registry.campaign_map(name)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        sess, reset = campaint.session(name, mod, cm)
        try:
            if action == "paint":
                out = campaint.paint(sess, body)
            elif action == "paint_undo":
                out = campaint.undo_stroke(sess)
            elif action == "paint_redo":
                out = campaint.redo_stroke(sess)
            elif action == "paint_state":
                out = {"ok": True, "state": sess.state()}
            elif action == "paint_discard":
                campaint.drop(name)
                self.registry.invalidate(name)      # re-read, the strokes go
                # the state AFTER, like every other answer here: an empty one,
                # because that is what the next request will build
                out = {"ok": True, "discarded": True,
                       "state": campaint.PaintSession(mod, cm).state()}
            elif action == "region_start":
                out = campaint.start_region(sess, body)
            elif action == "region_cancel":
                out = campaint.cancel_region(sess)
            elif action == "region_vocab":
                out = campaint.wizard_vocab(sess)
            elif action in ("paint_plan", "paint_apply"):
                plan = campaint.plan_paint(sess)
                out = {"plan": plan.payload(), "state": sess.state()}
                if action == "paint_plan" or plan.errors:
                    if plan.errors:
                        out["error"] = "; ".join(plan.errors)
                else:
                    out.update(campaint.apply_paint(plan))
                    campaint.drop(name)
                    self.registry.invalidate(name)  # the files changed on disk
                    # the state in `out` was taken before the write and says
                    # there are unsaved strokes, which stopped being true a line
                    # ago - the screen reads this to decide whether to offer a
                    # save, so it has to be the state after
                    out["state"] = campaint.PaintSession(mod, cm).state()
            else:
                return {"error": f"no such paint action {action!r}"}
        except (campmap.MapError, ValueError, OSError) as e:
            return {"error": str(e), "state": sess.state()}
        if reset:
            out["reset"] = ("the map was re-read from disk, so the strokes that "
                            "had not been saved are gone")
        return out

    # ---- the campaign map, queried (16g) ----
    def _mapquery(self, action, body):
        """Run a set of filters over the map, or write a picture of one.

        The browser sends which filters to run and what is picked in each; it
        never sends what matched. Every rule is Python's, the same division the
        validator and the paint tool make, so there is no second copy of
        "has a port" on the far side to drift out of step with this one.

        An export writes into the cache rather than into the mod - it is
        derived data about somebody else's files - and answers with the folder,
        which the browser then reveals.
        """
        try:
            name = body["mod"]
            facts = self.registry.map_facts(name, body.get("campaign") or "")
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}

        rules = body.get("rules") or []
        match = body.get("match") or "all"
        if action == "query":
            return mapquery.run_query(facts, rules, match).payload(facts)

        what = str(body.get("what") or "")
        try:
            if what == "factions":
                out = mapquery.export_factions(facts)
            elif what == "query":
                out = mapquery.export_query(
                    facts, mapquery.run_query(facts, rules, match))
            else:
                out = mapquery.export_colouring(facts, str(body.get("code") or ""))
        except (campmap.MapError, OSError, ValueError) as e:
            return {"error": str(e)}
        got = out.payload()
        if not got["count"]:
            got["error"] = "; ".join(f"{s['what']}: {s['why']}"
                                     for s in out.skipped) or "nothing to write"
        elif body.get("reveal") and out.folder:
            from .folder_dialog import reveal
            got["revealed"] = bool(reveal(str(Path(out.folder)
                                              / out.files[0]["name"])))
        return got

    # ---- the campaign map's settlements, written (16h) ----
    def _settlement(self, action, body):
        """Preview or write one settlement block of ``descr_strat.txt``.

        Two objects go in and they are not interchangeable. The fact table is
        the vocabulary - which factions there are, which building levels the
        EDB declares, what ``settlement_min`` each one wants - and it is a
        cache. The file the plan splices is read from disk inside
        :func:`~unittransfer.stratedit.plan_settlement`, so a save writes over
        the file as it is now rather than over the copy this process happened
        to be holding.

        A save invalidates the mod, which drops the map and the fact table with
        it, so the next request reads the file this one just wrote.
        """
        try:
            name = body["mod"]
            mod = self.registry.describe(name)
            facts = self.registry.map_facts(name, body.get("campaign") or "")
            plan = stratedit.plan_settlement(mod, facts, body)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        try:
            out.update(stratedit.apply_settlement(plan))
        except (OSError, ValueError) as e:
            return {"error": str(e), "plan": plan.payload()}
        self.registry.invalidate(name)              # the file changed on disk
        return out

    # ---- the campaign map's characters, written (16i) ----
    def _character(self, action, body):
        """Preview or write one character block of ``descr_strat.txt``.

        The settlement handler above with a different plan in it, and the same
        division of labour: the fact table is the vocabulary and the map the
        coordinates are checked against, and the file the plan splices is read
        from disk inside
        :func:`~unittransfer.stratchar.plan_character`.
        """
        try:
            name = body["mod"]
            mod = self.registry.describe(name)
            facts = self.registry.map_facts(name, body.get("campaign") or "")
            plan = stratchar.plan_character(mod, facts, body)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        try:
            out.update(stratchar.apply_character(plan))
        except (OSError, ValueError) as e:
            return {"error": str(e), "plan": plan.payload()}
        self.registry.invalidate(name)              # the file changed on disk
        return out

    # ---- the campaign's own settings, written (16j) ----
    def _campaign(self, action, body):
        """Preview or write the campaign header, a roster or a diplomacy row.

        The character handler above with a different plan in it, and the same
        division of labour: the fact table is the vocabulary - which factions
        this mod declares and what they are called - and the file the plan
        splices is read from disk inside
        :func:`~unittransfer.stratcamp.plan_campaign`.
        """
        try:
            name = body["mod"]
            mod = self.registry.describe(name)
            facts = self.registry.map_facts(name, body.get("campaign") or "")
            plan = stratcamp.plan_campaign(mod, facts, body)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        try:
            out.update(stratcamp.apply_campaign(plan))
        except (OSError, ValueError) as e:
            return {"error": str(e), "plan": plan.payload()}
        self.registry.invalidate(name)              # the file changed on disk
        return out

    # ---- what a faction has to do to win (16j-2) ----
    def _wins(self, action, body):
        """Preview or write one faction's ``descr_win_conditions.txt`` record.

        The campaign handler above with a different file under it. The fact
        table is the vocabulary - which provinces this map declares and which
        factions this campaign runs - and the file the plan splices is read from
        disk inside :func:`~unittransfer.winconds.plan_win`.
        """
        try:
            name = body["mod"]
            mod = self.registry.describe(name)
            facts = self.registry.map_facts(name, body.get("campaign") or "")
            plan = winconds.plan_win(mod, facts, body)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        out = {"plan": plan.payload()}
        if action == "plan" or plan.errors:
            if plan.errors:
                out["error"] = "; ".join(plan.errors)
            return out
        try:
            out.update(winconds.apply_win(plan))
        except (OSError, ValueError) as e:
            return {"error": str(e), "plan": plan.payload()}
        self.registry.invalidate(name)              # the file changed on disk
        return out

    # ---- the campaign map, checked (16f) ----
    def _mapcheck(self, action, body):
        """The baseline stamp, and Geomod's three auto-fixes.

        The plan re-runs the rules rather than trusting the finding list the
        browser is holding, so a fix acts on the map as it is now. What the
        browser sends is which fixes to run and, optionally, which findings of
        them - never what to change.

        A fix that writes a layer invalidates the mod, which drops the map,
        which is what makes the next request read the file this one wrote. A
        paint session over the same map is dropped with it: the strokes were
        never on disk, and silently reapplying them over a fixed layer would be
        the one way a fix could make a map worse.
        """
        try:
            name = body["mod"]
            mod = self.registry.describe(name)
            cm = self.registry.campaign_map(name)
        except (KeyError, campmap.MapError, ModDataError, OSError) as e:
            return {"error": str(e)}
        campaign = body.get("campaign") or ""
        try:
            if action == "baseline":
                if body.get("action") == "clear":
                    mapcheck.clear_baseline(mod)
                    stamp = {"taken": "", "keys": []}
                else:
                    stamp = mapcheck.take_baseline(
                        mod, mapcheck.run(mod, cm, campaign, use_baseline=False))
                rep = mapcheck.run(mod, cm, campaign)
                return {"ok": True, "baseline": {"taken": stamp.get("taken", ""),
                                                 "keys": len(stamp.get("keys") or ())},
                        "report": rep.payload(cm)}
            plan = mapcheck.plan_fix(mod, body.get("fixes") or [], cm, campaign,
                                     body.get("keys") or None)
            out = {"plan": plan.payload()}
            if action == "fix_plan" or plan.errors:
                if plan.errors:
                    out["error"] = "; ".join(plan.errors)
                return out
            out.update(mapcheck.apply_fix(plan))
            campaint.drop(name)
            self.registry.invalidate(name)          # the files changed on disk
            fresh = self.registry.campaign_map(name)
            out["report"] = mapcheck.run(mod, fresh, campaign).payload(fresh)
            return out
        except (campmap.MapError, ValueError, OSError) as e:
            return {"error": str(e)}

    # ---- unit packs ----
    def _pack(self, action, body):
        """Export units to a zip, or mount someone else's zip as a source mod.

        There is no "import" action: mounting is the import. Once a pack is a
        registered mod, the ordinary transfer endpoints move units out of it with
        every check, option and undo step they always had.
        """
        from . import pack as pack_mod
        try:
            if action in ("plan", "write"):
                mod = self.registry.get(body["mod"])
                units = [str(t) for t in (body.get("units") or []) if str(t).strip()]
                plan = pack_mod.plan_pack(mod, units)
                out = {"units": [u.type for u in plan.units],
                       "missing": plan.missing, "models": plan.models,
                       "assets": len(plan.assets), "icons": len(plan.icons),
                       "mounts": plan.mounts, "projectiles": plan.projectiles,
                       "engines": plan.engines, "bytes": plan.bytes,
                       "warnings": plan.warnings, "summary": plan.summary()}
                if action == "plan":
                    return out
                dest = (body.get("path") or "").strip()
                if not dest:
                    return {"error": "no destination file chosen"}
                out["record"] = pack_mod.write_pack(plan, Path(dest))
                return out
            if action == "open":                 # what the import dialog previews
                return pack_mod.pack_overview(Path(body.get("path") or ""))
            if action == "mount":                # …and what makes it importable
                return self.registry.mount_pack(Path(body.get("path") or ""))
            if action == "unmount":
                return {"unmounted": self.registry.unmount_pack(body.get("name") or "")}
        except pack_mod.PackError as e:
            return {"error": str(e)}
        except (OSError, ValueError) as e:
            return {"error": f"{type(e).__name__}: {e}"}
        return {"error": f"unknown pack action {action!r}"}

    # ---- sprites mode ----
    def _sprites(self, action, body):
        """Dispatch one sprite action. Split out because the five endpoints share
        a mod lookup and the same "SpriteError means the user can fix it" rule."""
        try:
            if action == "revert_cfg":              # no mod needed, just the CFG
                return sprites.revert_prep(body.get("cfg") or "")

            mod = self.registry.get(body["mod"])

            if action in ("prep_plan", "prep_apply"):
                req = sprites.PrepRequest(
                    models=[str(m) for m in (body.get("models") or [])],
                    method=(body.get("method") or "eop").lower(),
                    cfg_path=body.get("cfg_path") or "")
                plan = sprites.plan_prep(mod, req)
                out = _sprite_prep_payload(plan)
                if action == "prep_apply":
                    out["record"] = sprites.apply_prep(plan)
                return out

            if action in ("convert_plan", "convert_apply"):
                req = sprites.ConvertRequest(
                    stems=[str(s) for s in (body.get("stems") or [])],
                    mipmaps=bool(body.get("mipmaps", False)),
                    dedup=bool(body.get("dedup", True)),
                    install=bool(body.get("install", True)),
                    cleanup=bool(body.get("cleanup", True)))
                plan = sprites.plan_convert(mod, req)
                out = _sprite_convert_payload(plan)
                if action == "convert_apply":
                    sink = _progress_sink(body.get("job") or "")
                    log.info("SPRITE convert %d set(s) in %s", len(plan.sets), mod.name)
                    out["record"] = sprites.apply_convert(plan, progress=sink)
                    self.registry.invalidate(body["mod"])   # data/ changed on disk
                return out

            if action == "mark":
                # a toggle, not a replace: the page sends the models whose mark
                # changed, so two tabs can't wipe each other's marks
                cur = set(sprites.marked_done(mod))
                names = {str(n).strip().lower()
                         for n in (body.get("models") or []) if str(n).strip()}
                cur |= names if body.get("done") else set()
                cur -= set() if body.get("done") else names
                return {"marked": sprites.set_marked_done(mod, cur)}

            if action == "wire":
                # reuse bmdb mode's planner so the modeldb write inherits its
                # backups + undo rather than us hand-rolling a second writer
                edits = sprites.wire_model_edits(
                    mod, {str(k): [str(f) for f in v]
                          for k, v in (body.get("models") or {}).items()},
                    body.get("duplicates") or {})
                if not edits:
                    return {"error": "nothing to wire up"}
                return self._bmdb_apply({"mod": body["mod"], "model_edits": edits})
        except sprites.SpriteError as e:
            return {"error": str(e)}
        return {"error": f"unknown sprite action {action!r}"}

    # ---- bmdb mode ----
    def _bmdb_apply(self, body):
        mod = self.registry.get(body["mod"])
        plan = edit.plan_bmdb(mod, edit.bmdb_request_from_dict(body))
        log.info("BMDB   edit %s in %s",
                 ", ".join(sorted(plan.entry_updates) + [n for n, _r, _p in plan.new_entries])
                 or "(nothing)", mod.name)
        rec = edit.apply_edit(plan)
        self.registry.invalidate(body["mod"])
        log.info("BMDB   done id=%s", rec.get("id"))
        return {"record": rec, "plan": _edit_payload(plan)}

    def _bmdb_ownership(self, body, apply: bool):
        """Add the missing faction texture records, through the ordinary edit path.

        The ``model_edits`` are built HERE rather than in the page - see
        :func:`unittransfer.bmdb.ownership_edits` - and then handed to the same
        planner the model card's faction checklist uses, so the write inherits
        its backup, its undo record and its guards instead of getting its own.
        """
        sink = _progress_sink(body.get("job") or "")
        if sink:
            sink(1, "working out which records are missing")
        mod = self.registry.get(body["mod"])
        mode = str(body.get("mode") or "units")
        only = body.get("entries")
        edits = bmdb.ownership_edits(
            mod, mode, only if isinstance(only, list) else None)
        if not edits:
            return {"plan": {"changes": ["no changes"], "warnings": [], "errors": [],
                             "summary": "nothing to add"}, "empty": True}
        if sink:
            sink(20, f"planning {len(edits)} entr"
                     f"{'y' if len(edits) == 1 else 'ies'}")
        payload = {"mod": body["mod"], "model_edits": edits}
        if not apply:
            plan = edit.plan_bmdb(mod, edit.bmdb_request_from_dict(payload))
            return {"plan": _edit_payload(plan), "entries": len(edits),
                    "records": sum(len(e["factions"]) for e in edits)}
        log.info("BMDB   ownership fix (%s) on %s: %d entries", mode, mod.name,
                 len(edits))
        if sink:
            sink(45, "writing battle_models.modeldb")
        out = self._bmdb_apply(payload)
        out["entries"] = len(edits)
        if sink:
            sink(100, "done")
        return out

    def _bmdb_dupes(self, body, apply: bool):
        """Preview or write a tidy-up of the names the modeldb carries twice.

        One method for both because the preview IS the plan: the page shows
        exactly the object that gets applied, and the apply re-plans from the
        mod rather than trusting what the page was shown, so a file that
        changed underneath cannot be written from a stale set of block indices.
        """
        mod = self.registry.get(body["mod"])
        plan = dupes.plan(mod, dupes.request_from_dict(body))
        payload = {"plan": {"changes": plan.changes, "warnings": plan.warnings,
                            "errors": plan.errors, "summary": plan.summary()},
                   "removes": plan.removes, "renames": plan.renames}
        if not apply or plan.errors:
            return payload
        log.info("BMDB   duplicates in %s: %d remove(s), %d rename(s)",
                 mod.name, len(plan.removes), len(plan.renames))
        out = dupes.apply(plan)
        self.registry.invalidate(body["mod"])
        payload["record"] = out["record"]
        payload["removed"] = out["removed"]
        payload["renamed"] = out["renamed"]
        return payload

    def _bmdb_cleanup(self, body):
        sink = _progress_sink(body.get("job") or "")
        if sink:
            sink(1, "working out what moves")
        mod = self.registry.get(body["mod"])
        plan = bmdb.plan_cleanup(mod, bmdb.cleanup_request_from_dict(body))
        log.info("BMDB   cleanup %s -> %s (%d entries, %d mounts, %d files)", mod.name,
                 plan.target, len(plan.entry_deletes), len(plan.mount_deletes),
                 len(plan.exports))
        rec = bmdb.apply_cleanup(plan, progress=sink)
        self.registry.invalidate(body["mod"])
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        out = {"record": rec, "plan": _cleanup_payload(plan)}
        if _strings_bin_wanted(body):
            if sink:
                sink(99, "clearing the unit-text cache")
            _clear_cache(mod.root, out, rec, mod.name)
        return out

    def _bmdb_recheck_revert(self, body):
        """Put back the rows the recheck dialog ticked."""
        sink = _progress_sink(body.get("job") or "")
        if sink:
            sink(1, "reading the cleanup log")
        mod = self.registry.get(body["mod"])
        picks = [p for p in (body.get("picks") or [])
                 if p.get("kind") in ("file", "entry") and p.get("name")]
        if not picks:
            return {"error": "nothing was ticked"}
        out = bmdb.revert_recheck(mod, picks, progress=sink)
        self.registry.invalidate(body["mod"])
        return out

    # ---- unit / info cards ----
    def _cards_cleanup(self, body):
        sink = _progress_sink(body.get("job") or "")
        if sink:
            sink(1, "working out what moves")
        mod = self.registry.get(body["mod"])
        plan = cards.plan_cleanup(mod, cards.cleanup_request_from_dict(body))
        log.info("CARDS  cleanup %s -> %s (%d removed, %d consolidated, %d files)",
                 mod.name, plan.target, plan.removed, plan.consolidated,
                 len(plan.deletes))
        rec = cards.apply_cleanup(plan, progress=sink)
        self.registry.invalidate(body["mod"])
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        return {"record": rec, "plan": _cards_payload(plan)}

    # ---- strat-map mode ----
    def _strat_cleanup(self, body):
        sink = _progress_sink(body.get("job") or "")
        if sink:
            sink(1, "working out what moves")
        mod = self.registry.get(body["mod"])
        plan = stratmap.plan_cleanup(mod, stratmap.cleanup_request_from_dict(body))
        log.info("STRAT  cleanup %s -> %s (%d entries, %d files)", mod.name,
                 plan.target, len(plan.entry_deletes), len(plan.exports))
        rec = stratmap.apply_cleanup(plan, progress=sink)
        self.registry.invalidate(body["mod"])
        for line in plan.summary().splitlines()[1:]:
            if line.strip():
                log.info("   %s", line.strip())
        return {"record": rec, "plan": _strat_payload(plan)}

    def _base_fields(self, q):
        """EDU fields of ``unit`` after applying ``base``'s stat template.

        Also serves replace mode (``mode=replace``), where the "base" is the unit
        being replaced: the same composition, plus the icon-folder pins, so the
        editor's rows are exactly the block that will be written and each B button
        switches a field the transfer engine will actually honour.
        """
        from . import edu as _edu
        sname = (q.get("source") or [None])[0]
        dname = (q.get("dest") or [None])[0]
        utype = (q.get("unit") or [None])[0]
        btype = (q.get("base") or [None])[0]
        replacing = (q.get("mode") or [""])[0] == "replace"
        what = "unit to replace" if replacing else "base"
        names = self.registry.names()
        if not (sname in names and dname in names and utype and btype):
            return {"error": "bad params"}
        unit = self.registry.get(sname).edu.by_type().get(utype)
        base = self.registry.get(dname).edu.by_type().get(btype)
        if unit is None or base is None:
            return {"error": f"unit or {what} not found"}
        if base.kind() != unit.kind():
            return {"error": f"{what} is {base.kind() or '?'}, unit is {unit.kind() or '?'}"}
        # mirror the real transfer exactly, including whole groups taken from the base
        body = {k: (q.get(k) or ["source"])[0]
                for k in ("soldier_from", "officer_from", "mount_from",
                          "crew_from", "upgrade_from")}
        for k in ("import_mount_with_base", "import_officers_with_base"):
            body[k] = (q.get(k) or ["1"])[0] not in ("0", "false", "")
        opts = _options_from(body)
        keys = _edu.REPLACE_COPY_KEYS if replacing else _edu.BASE_COPY_KEYS
        groups = base_field_groups_for(opts)
        # a group goes back to the source when its models are being imported over
        # the base's (only their animations are borrowed) - the composed preview
        # has to show the same block the transfer will actually write
        if mount_base_import(base, self.registry.get(dname), unit, opts)[0]:
            groups = [g for g in groups if g != "mount"]
        if officer_base_import(base, self.registry.get(dname), unit, opts)[0]:
            groups = [g for g in groups if g != "officer"]
        composed = compose_with_base(unit.raw, base.raw, groups, copy_keys=keys)
        return {"unit": utype, "base": btype,
                "fields": _edu.block_fields(composed),
                "inherited": list(keys) + groups,
                "base_field_groups": groups}

    def _m2ex(self, body):
        """Read or set the M2EX mark on one mod.

        A POST with no ``on`` key only reads. Setting it drops the mod's caches:
        the mark decides which findings its editors report, and those are built
        from the parsed file the registry is holding.
        """
        name = body.get("mod") or ""
        if name not in self.registry.names():
            return {"error": f"unknown mod {name!r}"}
        mod = self.registry.describe(name)
        if "on" in body:
            modflags.set_m2ex(mod, bool(body.get("on")))
            self.registry.invalidate(name)
            log.info("FLAG   %s: m2ex=%s", name, bool(body.get("on")))
        return {"mod": mod.name, "root": str(mod.root),
                "m2ex": modflags.is_m2ex(mod)}

    def _eop_dirs(self, body):
        """Read or set one mod's M2TWEOP unit folders.

        A POST with no ``dirs`` key only reads (so the settings panel can show the
        auto-detected folders without saving them as an explicit choice); a POST
        that carries ``dirs`` saves it, and an empty list clears the setting and
        goes back to detection.
        """
        name = body.get("mod") or ""
        if name not in self.registry.names():
            return {"error": f"unknown mod {name!r}"}
        # Folders on disk, so nothing has to be parsed to answer - which matters
        # for the one mod this panel is most likely to be opened on: the one
        # whose roster the toolkit just refused to read.
        mod = self.registry.describe(name)
        if "dirs" in body:
            _eop.set_configured_dirs(mod, [str(d) for d in (body.get("dirs") or [])])
            edit._invalidate(mod)             # units move between files as this changes
        out = {
            "mod": mod.name,
            "configured": [str(p) for p in _eop.configured_dirs(mod)],
            "detected": [str(p) for p in _eop.detect_dirs(mod)],
            "dirs": [str(p) for p in mod.eop_dirs],
            "files": [_eop.rel_to_root(mod, p) for p in _eop.unit_files(mod)],
        }
        try:
            out["eop_count"] = len(mod.edu.eop_units)
            out["edu_count"] = len(mod.edu.main_units)
        except ModDataError as e:
            # The folder list is the point of this panel and it is still true, so
            # an unreadable roster costs the two counts and says why - not the
            # whole answer.
            out["note"] = str(e)
        return out

    def _dirs(self, q):
        """List sub-folders under a mod's data/ dir, for the reroute browser.

        Always resolves inside data/ (never escapes it) and defaults to unit_models.
        """
        name = (q.get("mod") or [None])[0]
        rel = (q.get("path") or ["unit_models"])[0] or "unit_models"
        if not name or name not in self.registry.names():
            return {"error": "unknown mod"}
        data = self.registry.get(name).data.resolve()
        rel = rel.replace("\\", "/").strip("/")
        target = (data / rel).resolve()
        try:                                   # refuse anything outside data/
            target.relative_to(data)
        except ValueError:
            target, rel = data / "unit_models", "unit_models"
        if not target.is_dir():
            target, rel = data / "unit_models", "unit_models"
        dirs = sorted((p.name for p in target.iterdir() if p.is_dir()),
                      key=str.lower) if target.is_dir() else []
        parent = "/".join(rel.split("/")[:-1]) if "/" in rel else ""
        return {"path": rel, "parent": parent, "dirs": dirs,
                "can_up": rel.lower() != "unit_models" and bool(rel)}

    def _file(self, p: Path, ctype: str):
        if not p.exists():
            return self._err(404, f"missing {p.name}")
        self._send(200, p.read_bytes(), ctype)

    #: What a URL path under web/ is allowed to be. The UI is the only thing
    #: served from disk, so this stays deliberately short.
    WEB_TYPES = {".js": "application/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8",
                 ".svg": "image/svg+xml", ".png": "image/png"}

    def _web_asset(self, url_path: str):
        """Serve a file from web/ - the UI's own scripts, nothing else.

        The path is resolved and then checked to be *inside* web/, so `..` or an
        absolute path cannot walk out of it and turn the tool into a file reader
        for whatever the browser asks for.
        """
        rel = urllib.parse.unquote(url_path.lstrip("/"))
        p = (WEB_DIR / rel).resolve()
        try:
            p.relative_to(WEB_DIR.resolve())
        except ValueError:
            return self._err(403, "outside web/")
        ctype = self.WEB_TYPES.get(p.suffix.lower())
        if not ctype or not p.is_file():
            return self._err(404, f"no such asset: {rel}")
        self._send(200, p.read_bytes(), ctype)

    #: what the browse dialog is allowed to preview - the formats a card can be
    #: imported from, and nothing that would turn this into a file reader
    PREVIEW_EXTS = {".tga", ".dds", ".png", ".jpg", ".jpeg", ".bmp", ".gif"}

    def _preview_image(self, path: str):
        """Decode an off-mod image to PNG for the editor's card preview.

        Same never-500 rule as :meth:`_icon`: a failure paints a blank, because a
        broken-image glyph in the editor reads as "your file is corrupt".
        """
        try:
            p = Path(path)
            if (path and p.is_file()
                    and p.suffix.lower() in self.PREVIEW_EXTS
                    and p.stat().st_size <= 64 * 1024 * 1024):
                return self._send(200, self.registry.icons.png_bytes(p), "image/png")
        except Exception:
            pass
        try:
            self._send(200, self.registry.icons.png_bytes(None), "image/png")
        except Exception:
            pass

    #: Native sizes of M2TW building art - the small browser icon and the big
    #: "constructed" picture. Used only for the placeholder, so a missing icon
    #: occupies exactly the space the real one would.
    BUILDING_ICON_SIZE = {"small": (78, 62), "large": (300, 245)}

    def _building_icon(self, q):
        """Serve one building icon as PNG, or a placeholder if there is none.

        Never 500s, for the same reason as :meth:`_icon`: a failed response
        paints a broken-image glyph across the grid. The ``X-Icon-Source``
        header says where the art came from (``mod`` / ``vanilla`` /
        ``placeholder``) so the UI can badge borrowed art.
        """
        kind = (q.get("kind") or ["small"])[0]
        source = "placeholder"
        data = None
        try:
            name = (q.get("mod") or [None])[0]
            culture = (q.get("culture") or [""])[0]
            level = (q.get("level") or [""])[0]
            if name and culture and level and name in self.registry.names():
                mod = self.registry.get(name)
                src, source = mod.find_building_icon(
                    culture, level, kind, config.get_vanilla_ui_root(),
                    # `any=1`: the caller is not showing a culture, so a level
                    # only one of them draws is still that level's art
                    (q.get("any") or [""])[0] == "1")
                if src is not None:
                    data = self.registry.icons.png_bytes(src)
                else:
                    source = "placeholder"
        except Exception:
            log.debug("building icon failed", exc_info=True)
            data = None
        try:
            if data is None:
                w, h = self.BUILDING_ICON_SIZE.get(kind, self.BUILDING_ICON_SIZE["small"])
                data = self.registry.icons.placeholder_png(w, h)
            self._send(200, data, "image/png", {"X-Icon-Source": source})
        except Exception:
            pass

    #: A model's own texture can be 2048x2048, and the viewer draws it on a
    #: soldier a few hundred pixels tall. Halving the big ones costs nothing to
    #: look at and takes a 16 MB upload down to 4.
    #:
    #: The viewer asks for ``hd=1`` when the "HD textures" toggle is on, and
    #: then the cap is lifted and the sheet is sent at the size the mod ships
    #: it. That is the size the game draws, so it is the only size worth
    #: looking at when the errand is checking a skin's own detail rather than
    #: identifying which model this is. It is off by default because the
    #: default errand is the second one, and because a 2048 sheet is four times
    #: the bytes and the memory of a 1024 one for a soldier on screen at
    #: 300 pixels. Both sizes are cached separately on disk (``max_side`` is
    #: part of the icon cache's key), so toggling back and forth converts each
    #: sheet once and never again.
    MODEL_TEXTURE_MAX = 1024

    def _model_route(self, path: str, q):
        """The three things the 3D viewer asks for.

        ``/api/model`` is the picker: which LODs and skins the entry has and
        which of them are actually in this mod. ``/api/model/geometry`` is one
        decoded LOD as the binary payload :func:`mesh.geometry_payload` builds.
        ``/model_texture`` is a skin as a PNG.

        A model that will not decode answers 400 with the decoder's own
        sentence, because that sentence is the useful part - the viewer puts it
        on screen rather than showing an empty box.
        """
        name = (q.get("mod") or [None])[0]
        if not name or name not in self.registry.names():
            return self._err(404, "unknown mod")
        mod = self.registry.get(name)

        if path == "/model_texture":
            # `rel` comes from the entry we just served, but it is still a path
            # out of a mod's own file, so it is resolved and then checked to be
            # under data/ - the same rule /icon's `rel` routes follow.
            src = factions.picture_path(mod, (q.get("rel") or [""])[0])
            hd = (q.get("hd") or ["0"])[0] == "1"
            data = self.registry.icons.png_bytes(
                src, 0 if hd else self.MODEL_TEXTURE_MAX)
            # the viewer puts the served size on the facts panel, so "HD" can be
            # seen to have done something rather than taken on trust
            return self._send(200, data, "image/png",
                              {"X-Texture-Full-Size": "1" if hd else "0"})

        entry = mod.modeldb.by_name().get((q.get("entry") or [""])[0].lower())
        if entry is None:
            return self._err(404, f"no model entry {(q.get('entry') or [''])[0]!r}"
                                  f" in {name}")
        if path == "/api/model":
            return self._json(mesh.entry_view(entry, mod.data))

        lod = int((q.get("lod") or ["0"])[0] or 0)
        rels = entry.mesh_files()
        if not 0 <= lod < len(rels):
            return self._err(404, f"{entry.name} has no LOD {lod}")
        src = factions.picture_path(mod, rels[lod])
        if src is None or not src.is_file():
            return self._err(404, f"{rels[lod]} is not in {name} - the mod "
                                  f"references it but does not ship it")
        try:
            decoded = mesh.read_mesh(src)
        except mesh.MeshError as e:
            return self._err(400, str(e))
        return self._send(200, mesh.geometry_payload(decoded),
                          "application/octet-stream")

    def _strat_model_route(self, path: str, name: str, q):
        """The three things the strat preview asks for, 16k.

        ``/api/map/models`` is the picker - every ``.cas`` in the mod, grouped.
        ``/api/map/model`` is one scene's facts: its meshes, its materials and
        anything the decoder could not read. ``/api/map/model/geometry`` is the
        same scene as the binary payload Phase 15's viewer already draws, which
        is the whole reason :func:`unittransfer.cas.as_mesh` exists.

        A model that will not decode answers 400 with the decoder's sentence,
        for the reason ``/api/model/geometry`` does: that sentence is the useful
        part, and the viewer puts it on screen instead of an empty box.
        """
        mod = self.registry.get(name)
        if path == "/api/map/models":
            return self._json({"mod": name, "models": cas.list_models(mod.data)})

        rel = (q.get("rel") or [""])[0]
        # `rel` came out of the list we just served, but it is still a path from
        # a query string, so it is resolved and checked to be under data/ - the
        # rule every `rel` route in this server follows.
        src = factions.picture_path(mod, rel)
        if src is None or not src.is_file():
            return self._err(404, f"{rel!r} is not a file in {name}")
        try:
            scene = cas.read_cas(src)
        except cas.CasError as exc:
            return self._err(400, str(exc))
        if path == "/api/map/model":
            view = cas.scene_view(scene)
            for row, mat in zip(view["materials"], scene.materials):
                found = cas.texture_path(src, mat.texture)
                row["rel"] = (found.relative_to(mod.data).as_posix()
                              if found else "")
            return self._json(view)
        try:
            geometry = cas.as_mesh(scene)
        except cas.CasError as exc:
            return self._err(400, str(exc))
        return self._send(200, mesh.geometry_payload(geometry),
                          "application/octet-stream")

    def _map_route(self, path: str, q):
        """Everything the campaign map screen reads.

        ``/api/map`` is the manifest - the tile grid, the ten layers with what
        is wrong with each, and the region table the browser picks against.
        ``/api/map/layer`` is one layer as PNG. 16d adds three more, all of
        them small and all of them on a click rather than on the pointer:
        ``/api/map/legend`` is one layer's colours named, ``/api/map/probe`` is
        one tile named by all ten layers, and ``/api/map/region`` is one
        region's record, its pixels, its neighbours and the pickers its boxes
        need.

        A mod with no map of its own answers 404 with that sentence rather than
        an empty screen, because it is the ordinary case: most mods ship units
        and let the game's own map stand.
        """
        name = (q.get("mod") or [None])[0]
        if not name or name not in self.registry.names():
            return self._err(404, "unknown mod")

        if path == "/api/map/campaigns":
            # 20b, D14. Before the map is read, deliberately: a campaign list
            # is a folder walk and a parse of each descr_strat.txt, and none of
            # it needs the ten layers. It is also the one map route that still
            # answers for a mod whose layers will not decode, which is exactly
            # when knowing the mod has two campaigns is worth something.
            return self._json(campfiles.browse(self.registry.describe(name)))

        try:
            cm = self.registry.campaign_map(name)
        except campmap.MapError as exc:
            return self._err(404, str(exc))
        except (ModDataError, OSError) as exc:
            return self._err(404, f"{name}'s campaign map could not be read: {exc}")

        if path == "/api/map":
            return self._json(campmap.view(cm, name))

        if path == "/api/map/palette":
            # Everything the brush may write, in one call: eight small tables
            # and the three sea colours measured off this mod's own map. Read
            # once when the paint panel opens, like /api/map itself.
            return self._json(campaint.palettes(cm))

        if path == "/api/map/legend":
            code = (q.get("code") or [""])[0]
            if code not in campmap.LAYER_BY_CODE:
                return self._err(404, f"no such layer {code!r}")
            try:
                return self._json(campmap.layer_legend(cm, code))
            except campmap.MapError as exc:
                return self._err(400, str(exc))

        if path == "/api/map/probe":
            # One tile, named by every layer at once. It is a click rather than
            # a hover - the browser answers the hover itself off the region
            # layer it already has - so one small request per pick is the right
            # trade for having the vocabularies stay on this side.
            try:
                x = int((q.get("x") or ["-1"])[0])
                y = int((q.get("y") or ["-1"])[0])
            except ValueError:
                return self._err(400, "x and y must be whole numbers")
            out = cm.probe_pixel(x, y)
            if not out:
                return self._err(404, f"{x},{y} is off the {cm.terrain.width}x"
                                      f"{cm.terrain.height} tile grid")
            return self._json(out)

        if path == "/api/map/region":
            try:
                out = campmap.region_detail(cm, (q.get("name") or [""])[0])
            except campmap.MapError as exc:
                return self._err(404, str(exc))
            # 18a, G3. The mercenary pool is a campaign fact and the record is
            # not, so it rides along rather than going into campmap.py: the
            # region panel is one screen and this is one more picker on it. A
            # campaign with no descr_mercenaries.txt comes back `have:false`
            # with the reason, which is what the picker shows instead of itself.
            camp = (q.get("campaign") or [""])[0] or campstrat.DEFAULT_CAMPAIGN
            out["campaign"] = camp
            out["mercenaries"] = campfiles.mercs_view(cm.mod, camp, out["name"])
            # 19a, D4. The two words the player reads for this province, out of
            # the file campmap has parsed since 16f and never written. It rides
            # along for the same reason the pool above does - one more thing the
            # panel shows about this region - and saves on its own, because it
            # is one more file.
            try:
                out["names"] = namekeys.region_names(cm.mod, out["name"])
            except namekeys.NameKeyError as exc:
                out["names"] = {"have": False, "problem": str(exc), "rows": []}
            return self._json(out)

        if path in ("/api/map/query/vocab", "/api/map/colouring"):
            # 16g. Both go through the fact table, which is where every filter,
            # theme and information map reads from; building it is the whole
            # cost and it is cached per (mod, campaign) on the registry.
            try:
                facts = self.registry.map_facts(name, (q.get("campaign") or [""])[0])
            except (campmap.MapError, ModDataError, OSError) as exc:
                return self._err(404, str(exc))
            if path == "/api/map/query/vocab":
                return self._json(mapquery.vocab(facts))
            code = (q.get("code") or [""])[0]
            try:
                return self._json(mapquery.colouring(facts, code).payload(facts))
            except campmap.MapError as exc:
                return self._err(404, str(exc))

        if path == "/api/map/settlement":
            # 16h. Through the fact table like the query panel, because the
            # form's pickers are the same joined sentences the filters are:
            # who owns this province, what is standing in it, and which
            # export_descr_buildings.txt line each of those belongs to.
            try:
                facts = self.registry.map_facts(name, (q.get("campaign") or [""])[0])
                return self._json(stratedit.settlement_detail(
                    facts, (q.get("region") or [""])[0]))
            except (campmap.MapError, ModDataError, OSError) as exc:
                return self._err(404, str(exc))

        if path == "/api/map/faction":
            # 16i. Through the fact table for the same reason 16h's settlement
            # form is: the parse of descr_strat.txt is already done and cached,
            # so opening a faction's people costs nothing.
            try:
                facts = self.registry.map_facts(name, (q.get("campaign") or [""])[0])
                return self._json(stratchar.faction_detail(
                    facts, (q.get("faction") or [""])[0]))
            except (campmap.MapError, ModDataError, OSError) as exc:
                return self._err(404, str(exc))

        if path == "/api/map/markers":
            # 17d. Everything in descr_strat.txt that stands on a tile, in one
            # call, through the same fact table - 855 markers on Third Age
            # Reforged and about 110 KB of JSON, fetched when the layer is first
            # turned on and never per frame.
            try:
                facts = self.registry.map_facts(name, (q.get("campaign") or [""])[0])
                return self._json(mapquery.marker_view(facts))
            except (campmap.MapError, ModDataError, OSError) as exc:
                return self._err(404, str(exc))

        if path == "/api/map/campaign":
            # 16j. Through the fact table for the reason 16h and 16i are: the
            # parse of descr_strat.txt is already done and cached, so opening
            # the campaign's settings costs nothing.
            try:
                facts = self.registry.map_facts(name, (q.get("campaign") or [""])[0])
                return self._json(stratcamp.campaign_detail(facts))
            except (campmap.MapError, ModDataError, OSError) as exc:
                return self._err(404, str(exc))

        if path == "/api/map/wins":
            # 16j-2. Off the disk rather than out of the fact table, unlike
            # every other detail route here: `facts` carries the parsed
            # conditions but not the file's own lines, and this panel edits
            # lines.
            try:
                facts = self.registry.map_facts(name, (q.get("campaign") or [""])[0])
                return self._json(winconds.win_detail(facts))
            except (campmap.MapError, ModDataError, OSError) as exc:
                return self._err(404, str(exc))

        if path == "/api/map/check":
            # Run against `cm`, which is the object the paint session has been
            # painting, so an unsaved stroke is checked rather than the file it
            # has not been written to yet. That is the whole reason the
            # validator takes a map instead of a mod.
            mod = self.registry.describe(name)
            rep = mapcheck.run(mod, cm, (q.get("campaign") or [""])[0])
            return self._json(rep.payload(cm))

        if path != "/api/map/layer":
            return self._err(404, f"no such map route {path}")

        code = (q.get("code") or [""])[0]
        fit = (q.get("fit") or ["tile"])[0]
        if code not in campmap.LAYER_BY_CODE:
            return self._err(404, f"no such layer {code!r}")
        src = cm.path(code)
        if not src.exists():
            return self._err(404, f"{name} has no {campmap.LAYER_BY_CODE[code]['file']}")
        # The mtime is in the cache key, so a layer repainted underneath us -
        # by 16e, or by the user in Photoshop - is a miss rather than a stale
        # picture that outlives the edit.
        token = f"maplayer|{src}|{_stat_sig(src)}|{fit}"
        try:
            data = self.registry.icons.cached_png(
                token, lambda: campmap.layer_png(cm, code, fit))
        except campmap.MapError as exc:
            return self._err(400, str(exc))
        except Exception as exc:
            # Said out loud rather than served as a blank: a layer is the
            # picture, and a silently empty one reads as a map with nothing on
            # it. /icon's never-raise rule is for the dozens of small pictures
            # in a grid, which is a different problem.
            log.debug("map layer failed", exc_info=True)
            return self._err(500, f"{campmap.LAYER_BY_CODE[code]['file']} "
                                  f"could not be decoded: {exc}")
        return self._send(200, data, "image/png",
                          {"X-Map-Fit": fit, "X-Map-Layer": code})

    def _icon(self, q):
        # Icons must NEVER 500: a failed response paints a broken-image glyph in
        # the grid. On any trouble, fall back to a blank PNG with 200 instead.
        try:
            name = (q.get("mod") or [None])[0]
            utype = (q.get("type") or [None])[0]
            kind = (q.get("kind") or ["card"])[0]
            src = None
            if kind == "ancillary" and name and name in self.registry.names():
                # An ancillary names a file under data/ui/ancillaries rather than
                # a unit, so it is looked up by image name; a mod that keeps a
                # stock picture without shipping it falls through to vanilla's.
                src = ancillaries.image_path(self.registry.get(name),
                                             (q.get("image") or [""])[0])
                self._send(200, self.registry.icons.png_bytes(src), "image/png")
                return
            if kind in ("faction", "modfile") and name and name in self.registry.names():
                # A picture the page already knows the path of: a faction symbol
                # (named by convention, not by any field) or one of a unit's card
                # variants. `picture_path` is what keeps `rel` inside data/.
                src = factions.picture_path(self.registry.get(name),
                                            (q.get("rel") or [""])[0])
                self._send(200, self.registry.icons.png_bytes(src), "image/png")
                return
            if name and utype and name in self.registry.names():
                m = self.registry.get(name)
                unit = m.edu.by_type().get(utype)
                if unit is not None:
                    src = m.find_unit_info(unit) if kind == "info" else m.find_unit_card(unit)
                    if src is None:
                        # Said here rather than in the icon cache, which only ever
                        # sees a path: a blank card is normal (the mod ships no art
                        # and the game falls back to its own), and the log has to
                        # tell that apart from a conversion that failed.
                        log.debug("ICON   %s has no %s art in %s", utype, kind, name)
            self._send(200, self.registry.icons.png_bytes(src), "image/png")
        except Exception:
            try:
                self._send(200, self.registry.icons.png_bytes(None), "image/png")
            except Exception:
                pass


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    # A freshly rendered page fires dozens of icon requests at once; a bigger
    # listen backlog stops the OS from dropping bursts (which the browser would
    # surface as broken images).
    request_queue_size = 128
    # HTTPServer defaults this to 1, but on Windows SO_REUSEADDR lets a SECOND
    # instance bind a port that is already serving - the two then fight over
    # requests. Off on Windows so a duplicate launch fails loudly instead.
    allow_reuse_address = (os.name != "nt")


def serve(cache_dir: Path, host="127.0.0.1", port=8756, on_ready=None, verbose=False):
    setup_logging(verbose)
    logutil.banner(port)
    Handler.registry = Registry(cache_dir)
    httpd = _Server((host, port), Handler)     # socket is bound + listening here
    log.info("Unit Transfer UI  ->  http://%s:%d/", host, port)
    log.info("MED2 root: %s", config.get_med2_root() or "(not set - choose it in the UI)")
    log.info("Mods found: %s", ", ".join(Handler.registry.names()) or "(none yet)")
    log.info("Ctrl+C to stop (or use Quit in the UI's settings, or close the browser tab).")
    threading.Thread(target=_liveness_watchdog, args=(httpd,), daemon=True).start()
    if on_ready:                               # e.g. open the browser now that we're up
        try:
            on_ready()
        except Exception:
            log.debug("on_ready failed", exc_info=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("interrupted - stopping")
        httpd.shutdown()
    log.info("server stopped")
    return httpd
