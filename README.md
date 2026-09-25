# Medieval 2 GUI Toolkit

Edit Medieval II: Total War mods without hand-editing text files. Move units
between mods, edit what is already there, and clean out what nothing uses.

Formerly released as "Unit Transfer".

Runs as a local web server with a UI in your browser. No game files are touched
except the mod you point it at, and every write is backed up and undoable.

Video walkthrough: <https://www.youtube.com/watch?v=NZl8gCqlTE0>

Sponsored by FeatherLeaf.

![The Unit Editor: every unit in a mod, grouped by the faction that fields it](main/docs/images/unit-editor.png)

## Install

Download the latest build from [Releases](../../releases/latest) and unzip it.
Then, in this order:

1. **Run `Install-Dependencies.bat`.** It checks for Python and Pillow and
   installs whatever is missing, for your user only, with no administrator
   prompt. It asks before downloading anything. On the portable build both are
   already inside the folder, so it will usually just say there is nothing to
   do - run it anyway, because that is the answer you want to have seen before
   the next step rather than after it.
2. **Run `Launch-Medieval2-GUI-Toolkit.bat`.** This is the one you use from then on.

On first run, open Settings and point it at your Medieval II install folder (the
one containing `mods`).

## Modules

| Module | What it does |
|---|---|
| Home | Every mod it can see, with which modules can work on it and which files are missing, and a **Launch** row: every way the mod folder offers to start the game, and whether each one would (its `.cfg` names this folder, sets `file_first`, and starts an executable that is there and Large Address Aware) |
| Unit Transfer | Copy a unit from one mod into another, with everything it depends on |
| Unit Editor | Change, clone or delete the units of a single mod |
| Models Editor | Every model a mod ships: edit any `battle_models.modeldb` entry, its sprites and its unit cards, list what `descr_model_strat.txt` declares, view any battle or campaign-map model in 3D (a skinned campaign model stood in its pose by its skeleton), play a battle model's animations (loose, or out of a pack unpacked in place) and edit one (trim, speed, a bone turned) saved beside the original, export a model as `.glb` or `.obj`, and clean out what nothing references |
| Buildings | Browse and edit `export_descr_buildings.txt`, including recruitment, and check the shape of the tree; **From another mod** brings whole building lines across with their text and cards, mapping or leaving out what this mod lacks |
| Campaign Map _(beta only)_ | The ten map layers under `world/maps/base`, the regions painted on them, and `descr_strat.txt`: paint a province, place and move what stands on the map, add or delete a province across every campaign, edit the people, events, disasters and menu text a campaign carries, draw the ground with the game's own aerial-map textures in either season, delete, create or copy a settlement between mods, resize the map with every coordinate in the mod moved to match, start a new campaign on a map made from nothing, generate heights, ground types, climates and rivers from the real world or from each other, bring in a campaign from another mod, find anything by the name the player reads or the one the files use, and check the whole map against what the game will accept. Set out under [the screen](#campaign-map) below. **Not on the menu in a 2.x release** - it is the first thing this toolkit does that writes to a campaign, so it ships on the dated **beta** pre-release instead (betas are named for the day they were cut, e.g. `beta 2026-09-06`). Running from a clone of the repo, it is on the menu |
| Unit Sounds | Choose which voice bank entry each unit uses; and **Sound banks** beside it: soldier and strat map voices, battle events, pre-battle speech, advice and narration, each block's events editable and any block duplicated, renamed or removed; and **Sound scripts**, the 31 `descr_sounds_*.txt` files: every event, DEFAULT: line and setting, with the attributes checked against what the mod's own scripts write |
| Sprites | Generate and wire up the far-LOD unit sprites |
| Strings | Read and write the compiled `data/text/*.txt.strings.bin` files: edit an entry, add a new one or remove one |
| Traits / Ancillaries | Full editors for both, definitions and triggers together, and what an M2TWEOP mod's Lua scripts in `eopData` do with each one: a trait a script gives is not "given by nothing" |
| Guilds | `export_descr_guilds.txt`: what each guild grants, the point thresholds its tiers sit at, and every trigger that earns it points |
| Factions | Faction definitions, with map colours edited via a colour picker. **Add a faction** clones new slots out of one that already works, several at once, across all thirteen files that name a faction; **⇩ Faction files** downloads every one of those files, and the faction's art, as a zip laid out under `data/`; **Rename slot** follows the name through about twenty files, the length-prefixed texture records in the modeldb and the art the engine finds from the slot itself, and reports every line of campaign script naming it rather than editing one; **Is it complete?** checks one faction against every file that should name it, and copies what it is missing from a faction that has it |
| Minor Files | Rebel factions, religions (a new one given a share in every region's religions line, the lines kept at 100), resources and character names; **Cultures** on a screen of its own, with each culture's settlements, fort, port ladder, watchtower and agents on four tabs, and **Duplicate** to make a new culture from one that works, and **Import** to put a settlement model from another mod or disk on a culture's level; and **Campaign constants**: `descr_campaign_db.xml` as a form typed off the file itself, with what the archive's tutorials say about the forts, piety and ransom settings. Beside them, a tab each for **settlement mechanics** (growth, order, income, mines), **populace and off-map models**, **animals, standards and advice**, **battle banners**, **hero abilities** (a character's battle ability, its button and its effects), **area effects** (what a shot does where it lands), **walls, gates and towers** (`descr_walls.txt`, per wall level) and **agents and generals** (`descr_character.txt`) |
| Raw text | Any text file the toolkit reads, opened as plain text and saved with the same backup and undo as every other screen - for the line no editor here models. It also downloads the open file, replaces it from disk, or puts any file at any path under `data/`, each as a plan with one Undo |
| My changes | Everything you changed in a mod, recorded as you go with nothing to switch on. When an update overwrites the mod, port your changes back onto it change by change: each one says whether it applies cleanly, merges with the update, conflicts with it, or names something the update removed. Keep several versions of one mod and switch between them in place, or turn every version off to play the mod as it shipped. Export the record as one file, and import one. **Export changed files** gives just the files you changed, in their `data/` folders, and any `data/` zip loads back in as a plan with one Undo |
| Health | Every check the toolkit has, over one mod, in one list: fatal first, grouped by when it bites (starting the game, loading a campaign, a panel, battle, play), each row opening the screen that owns it. Adds five checks from the TWCenter crash guides that nothing else ran |

## The screens

All shot from the running tool against Third Age Reforged. Re-taken with
`python main/dev/docs/screenshots.py`, so they are never a version out of date.

### Home

Every mod it can see, what each one is ready for, and where you left off.

![Home](main/docs/images/home.png)

### Unit Transfer

Pick a unit in one mod, pick the mod to put it in, and the toolkit works out
what has to come with it.

![Unit Transfer](main/docs/images/unit-transfer.png)

### Models Editor

Every model a mod ships, on four tabs: the `battle_models.modeldb` entries, the
far-LOD sprites, the campaign map's own models, and the two cards per unit.

Every `battle_models.modeldb` entry, what names it, and what it draws with.

![The BMDB entry list](main/docs/images/bmdb.png)

Any entry opens in a 3D viewer: the LODs it ships, the skin each faction gets,
the parts the game picks between per soldier, and its UV layout. **HD textures**
draws the sheet at the size the mod ships it, which is the size the game draws.

![The model viewer](main/docs/images/bmdb-3d.png)

Names the file carries more than once get a screen of their own. M2TW reads the
first block with a name and ignores every later one, so the rest are models the
mod is carrying and cannot reach: rename one to make it reachable, or remove it.

![Duplicate entries](main/docs/images/bmdb-duplicates.png)

The **Strat map** tab is the other tree: everything `descr_model_strat.txt`
declares - the generals, agents, heroes and faction symbols - with who uses each
one and what it would free to remove it. Every entry that ships a `.CAS` has its
own 🧊, and the panel beside the list also browses every model file under
`data/models_strat`, which is where the settlements are: the game picks those by
level and culture out of the folder tree with nothing naming the file, so Amon
Hen and Minas Tirith are on the campaign map and in no entry at all.

### Buildings

`export_descr_buildings.txt` as a tree, with the recruitment each level unlocks.

**✓ Check the tree** runs nine rules over the file's shape rather than its
recruitment: a building name used twice, a line with no levels, and every
`upgrades`, `convert_to` and `building_present_min_level` that names a line or
a level which does not exist. Three more are worth knowing rather than wrong -
a level that costs nothing, one that finishes the turn it is started, one no
faction can build. Each finding names its rule and its line and opens the
building it is about. Three rules the reference tool has are deliberately not
here, and the panel says which and why: two are level-count ceilings a shipping
mod is already over, and the third assumes every line is an upgrade chain when
42 of the ones measured are sets of alternatives.

**◈ Hidden resources** edits the `hidden_resources` line itself: add a name,
or take one off. Taking one off first lists every province that carries it and
every clause that gates on it, because all of them stop working the moment it
is gone, and it waits until you say you have read that.

Recruit pools and capabilities keep the order you give them: drag a row by its
grip or step it with ▲ ▼, and the file is written in that order, which is the
order the game lists units in. `＋` on a row adds units or a capability directly
under it. Beside each `requires` clause, **📍 N regions pass** names the regions
that carry every resource the clause asks for, each with its starting owner,
and `∅ no region passes every gate` marks a pool nobody can ever recruit from.

![Buildings](main/docs/images/buildings.png)

### Campaign Map

The ten map layers, the regions painted on them, and what `descr_strat.txt` puts
on top. Ships on the dated beta pre-release; see the module table above.

* **Arriving somewhere.** **Find** takes a province, a settlement or a region ID,
  matching the words the player reads as well as the code name the files use, out
  of the map already on screen. **Views** saves what the map looks like - which
  layers, in what order, at what opacity, the colours punched out of each and the
  colouring over the top - under a name, on any mod. **Campaign** lists every
  campaign the mod ships, the ones in subfolders that the engine's own new-game
  menu never offers included, and opens it; a campaign with its own map files is
  drawn and checked from those, and the brush stays off there.
* **How it is drawn.** **Terrain textures** paints the ground with the mod's own
  aerial-map art, **summer or winter**, built once a season and laid under the
  whole stack so the provinces, markers and names still read over it. A tile
  whose texture cannot be found is drawn pink and counted, never quietly skipped,
  and ✓ Check names the file and a tile to go and look at. A colouring goes
  **over** the map or **tints into** it, so the terrain's hills, forests and
  rivers still read under a faction map, and frontiers sit on the edge between
  two provinces or inside them, between the colouring's groups or round every
  province. **Labels** (`L`) puts every settlement's name beside it without one
  name covering another, and the names and the textures are both on when the map
  opens. The ten layers are a button at the foot of the map (`S`) and a panel
  over it, and the bare number keys tick one whether that is open or not. All of
  it exports to a TGA exactly as it is on screen,
  and **↺ Reset** puts every one of these readings back to how the map first
  opens, keeping saved views, the campaign you are reading and unsaved painting.
* **The same map in 3D** (`⛰ 3D`, or `D`): the heights as a surface with the
  ground drawn on it, dragged to orbit, right-dragged to pan and zoomed with the
  wheel. It is a **mode over the map you already have**, not a second one - the
  layers, their opacities, the season and any colouring are the flat map's, so
  changing one there changes the surface here. One vertex per tile with nothing
  thinned out, and the sea read from `map_heights.tga` rather than guessed from
  the ground types. A slider for how tall the land stands and a switch for the
  water surface; markers, names and the tooltip stay on the flat map.
* **Putting things on it.** **🏰 Forts and resources** places a fort, a
  watchtower or a trade resource on the tile you click and files it where the
  campaign keeps its own; drag one to move it, or pick a province to list its own
  and change a fort's type or culture, a resource's name, or which province it is
  filed under. Every x, y on the people and events panels has a **⌖** that
  fills it from a click on the map. Each save is one line of `descr_strat.txt`,
  shown before it is written, backed up, and undone from the Log.
* **Provinces.** **New region** adds one that arrives in every campaign reading
  the map: a start settlement in each, the record, a music type and both of the
  names the player reads, which are required because the game will not start a
  province without them. **Delete** is the other half of it: the land goes whole
  to a neighbour it shares a border with, longest border first, and everything
  that named the province goes with it. What the panel says before you commit is
  the point - the whole list of files, what stands on the land and whose province
  it becomes, and every line of campaign script naming it, which is reported and
  never edited.
* **+ New campaign** makes a whole new campaign out of one that already works:
  the folder copied, the `campaign` line set to the new name, every menu title
  and blurb written again under the new key, and the compiled `map.rwm`
  deliberately left behind so the game rebuilds it.
* **Size and generate.** **Size** grows or shrinks the map by tiles on each
  edge, new ground the map's own sea, and moves every coordinate the strat, the
  events, the battles and the campaign scripts hold; a shrink that would leave
  anything standing nowhere is refused with the file and line of each. **New
  map** starts a campaign in its own folder on an island of provinces, or on
  the real ground under a box picked on the world map with a province round
  each city picked there; one province and a leader per faction picked. **Generate** makes heights from the
  real ground under the map's box at the game's own scale, ground types from the
  heights, climates from the ground types, and rivers, cliffs and volcanoes from
  OpenStreetMap drawn the way the game can build a river. **Real world** draws
  the real world over the map (OpenStreetMap, OpenTopoMap, a relief, or the
  historical borders of any year from OpenHistoricalMap), traces the real coastline, finds places by
  name, and marks castles, forts, monasteries and other historic sites, any of
  which can be made a fort, a watchtower or a new region. What it asks
  OpenStreetMap is shown chunk by chunk, and a chunk that got no answer can be
  asked again. Its world map is where the map's box is found: drawn, moved,
  turned, or fitted round a place, in the map's own shape. The two that use the internet are off until Settings turns them on.
* **A refusal says what would work instead.** A culture or a resource name the
  mod does not declare is refused outright; a tile that is wrong for what you put
  on it is told where the nearest tile that would do is, and **⌖ Move it to**
  puts it there. Going to anything on the map draws a ring that closes onto the
  tile.

![Campaign Map](main/docs/images/campaign-map.png)

### Factions and Traits

![Factions](main/docs/images/factions.png)

![Traits](main/docs/images/traits.png)

## Transfers

Pick a unit in one mod and transfer it into another. The toolkit resolves what
the unit depends on and carries it across:

* the EDU entry (stats, attributes, ownership, era, cost, formation)
* the localised name and descriptions
* every battle model it uses (soldier, officers, mount, crew): meshes, textures,
  normal maps and far-LOD sprite sheets
* the mount definition, if mounted
* the projectile definition, if it is a missile unit (and its effect sets too,
  when the destination is marked M2EX - see below)
* for artillery, the full siege engine: the `descr_engines.txt` blocks, each
  model group's animation skeleton, every referenced mesh, bone map, collision
  and reference-points file, and the textures baked into those meshes
* the unit card and info card
* the voice, as a copy of another unit's entry in the destination's voice bank,
  with `accent` and `voice_type` set to match

Name collisions are detected and resolved (reuse identical content, rename, or
overwrite/skip), and every step is shown in a probe before anything is written.

Other transfer options:

* **Batch transfer.** Select several units and transfer them in one pass, each
  with its own options.
* **Use another unit as a stat base.** Port a unit's identity and models but
  inherit combat stats, cost and ownership from a unit in the destination.
* **Replace an existing unit.** Write the transferred unit's models into a
  destination unit of the same kind. No new EDU entry, no new dictionary, no new
  name, so recruitment, scripts and the campaign map are unaffected.
* **Unit packs.** Export selected units as a zip and send it to someone whose
  mod is not on your machine. A pack is a mod, so importing one is an ordinary
  transfer.
* **The model, beside the transfer.** The 3D viewer docks into the composer and
  draws both sides: the source unit's battle-model entries, and - once a base or
  replaced unit is picked - that unit's own entries out of the destination mod,
  grouped by which mod each comes from. Which soldier crosses, and which
  destination unit is the right one to replace, stop being decisions taken off a
  name in a dropdown.

## Editing

* **Guided field editor.** An EDU line is a positional tuple with nothing
  indicating which slot is which. The guided view gives every value its own
  labelled field, with dropdowns where the engine accepts a fixed set and lists
  built from your own mod where it does not. A raw one-field-per-line view is
  available on a toggle. Validation reports what the engine will actually do:
  attack above the cap of 63, a missile weapon with no ammunition, a secondary
  missile weapon (never fired), a model nothing defines, and similar.
* **The engine's ceilings.** A unit past what Medieval II accepts - 4 to 100
  men, attack 63, hit points 15, three officers, three mount effects, two
  formations, 500 units in the file - carries a note on its fields tab naming
  the document the number comes from, and a save that crosses one says so.
  Nothing is refused, and a mod marked for M2EX is not held to the 500.
* **Recruitment, from the unit.** A tab in the unit editor listing every
  building line in the mod that trains it, with all four pool numbers and the
  `requires` clause editable in place - the same `recruit_pool` lines the
  Buildings module writes, saved with the unit in one pass and taken back by one
  undo. A value that disagrees with what most of the other pools use is marked,
  which is usually why you opened it. A building's name opens that line in a new
  browser tab, on the tier the pool is on, with the unit's rows flashed. **＋ Add
  a building** offers every line and every tier - the ones that already train it
  shown as such - so making a unit recruitable somewhere new never leaves the
  unit, and neither does taking it off a building.

  Every row carries the tier's own picture, and so does the ＋ picker; nineteen
  rows that all say "Barracks" are told apart by their art. The art follows the
  pool's own `requires`, so a pool gated to a set of factions wears the buildings
  those factions build.
* **Code View.** The raw game file beside the form in every editor, with
  hover-to-highlight both ways and live two-way editing. Can hide comment-only
  lines and restore them exactly. The text only scrolls when you click a box,
  so it stays put while the mouse crosses the form; `⇕ Follow hover` brings
  back scrolling on hover.
* **3D model viewer.** Draws the `.mesh` an entry names with its faction skin
  applied, in the browser, with nothing installed. Orbit it, toggle parts off,
  and step through the head, helmet and shield variants the engine picks between
  per soldier. Docks beside the entry list or the editor.
* **Show UVs** in that viewer, for when the skin is the thing you are debugging.
  Paints the UV coordinate instead of the art, in the space the game samples:
  blue is the main sheet, amber the attachment sheet, the dark tiles are the two
  repeating, and a red line marks where the pair starts over. Thirty-two checker
  cells to a sheet, so art stretched over a part shows up as stretched cells.
* **UV layout** beside the model, the way a UV editor shows it: the texture
  sheet - both squares of it where the entry names a pair - with this model's
  islands drawn over the art they sit on, one colour per part and the same
  colour beside that part in the list. Pan, zoom, and click an island to be told
  which part wears it and which pixels of which sheet it covers. Only the parts
  actually on the soldier are drawn, so switching a variant or hiding a slot
  changes the map with it. Where `Show UVs` answers "is this shell stretched",
  this answers "where on the art does this part live" - the view a retexture is
  done against.
* **Drag the bar under the docked canvas** to trade height between the model and
  its controls; double-click for the default. The width of the whole column is
  draggable too, from the bar down its left edge.
* The unit editor's and the composer's previews offer the models the unit is
  actually **seen** in:
  when it carries `armour_ug_models` the engine draws those, one per armour
  level, and never the model on its `soldier` line, so that one is not offered.
* **Add a faction.** Copies one that already works into all twelve files that
  name a faction slot - the roster, `expanded.txt`, unit ownership, the modeldb's
  faction skins, every `requires factions { … }` clause in the EDB, the voice
  accent, diplomatic standing, agents, strat models, names, populace and off-map
  navies - along with its symbols, banners, captain cards and unit card folders.
  Shows what each file would gain before writing, backs every one up, and undoes
  the whole faction in one go. What it will **not** touch is named rather than
  left to be found later: traits called after the faction, an ancillary's
  `FactionType` condition, prebattle speeches and the campaign start position are
  judgements rather than lists, so they are counted and reported.
* **Is this faction complete?** One row for every file that should name the
  faction - the roster and its text, names, agents, units, buildings, the voice
  accent, strat models, battle skins, populace, off-map navy, diplomacy, and in
  the campaign its start and its win conditions - each saying what it found. A
  **gap** is something every faction in the mods this was measured on has; a
  **note** is something real, working factions go without, shown and not counted,
  so a mod that plays does not read as broken. The faction picker counts each
  faction's gaps. **Copy from** fills one out of another faction, the one of the
  same culture that has it offered first, with one backup and one undo for the
  lot. The two campaign rows open the tab that makes them instead, because a
  start position is not something to copy.
* **Raw text.** Pick any text file the toolkit reads - the mod's own, the map's,
  the text folder, or any campaign's, nested ones included - and edit it as
  text. Every other screen here edits a file record by record and keeps what it
  does not understand; this is for the line none of them models. A save shows
  the lines it changes with their numbers, and what the toolkit's own reader
  makes of the result (remove a character's age from `descr_strat.txt` and it
  says so before anything is written). The file keeps its own encoding and its
  own line endings, a line you did not touch is written back byte for byte, a
  save over a file something else changed since you opened it is refused, and a
  `text/` file's `.strings.bin` is rebuilt with it. Backed up first, undone from
  the Log. Tab types a tab, and Ctrl+S saves.
* **Replace any picture.** Right-click any image for Replace image and Open file
  location. Warns when resolutions differ, converts `.png` to the `.tga` the
  engine reads, and copies a unit card into every faction folder that holds one.
* **Port a trait or ancillary from another installed mod**, bringing the block,
  its triggers and its text keys together.
* **Guilds.** `export_descr_guilds.txt` is two things in one file: what each
  guild grants and the point thresholds its tiers sit at, then hundreds of lines
  below, the triggers that earn those points. Both halves on one screen, with
  every point line listed against the trigger it comes from and what its scope
  letter actually means. It also answers the question the Buildings module could
  only ask: a `guild_` requirement it refuses can now be fixed where it is, and
  the reverse fault is reported too - Divide and Conquer awards guild points to
  two guilds it never declares, and those points go nowhere.
* **What a campaign calls a faction.** The title and the blurb the new-game menu
  shows, edited on the faction screen beside the faction itself. A faction the
  campaign has never named shows its code name in game and nothing on disk says
  so, so the form is offered whether the text exists or not, and saving creates
  it. The four faction movies are on the same screen, and so is the mercenary
  pool a province hires from, over on the region panel.
* **Who can hire which mercenary, and where.** Province → Mercenaries lists what
  a province's pool sells with each unit's card, price and pool size and a
  verdict for the faction you pick - can hire, not yet, never, or depends on a
  script - with the reason: the unit missing from the EDU, the faction's
  religion, a `factions { }` list, `crusading`, an event traced to the line that
  sets it, or years outside the campaign. The other direction picks a mercenary
  and lights every province selling it. A pool entry is edited in place, and six
  Validate rules report dead unit names, provinces in two pools and the rest.
* **The words the player actually reads.** A province, a settlement and a
  character are each named twice in a mod: a code name the files point at, and a
  line in a text file the game shows. Miss the second and the campaign map reads
  `Anorien_Province`. Both are editable now - the province and its settlement on
  the region panel, a character's name straight from the warning that says it is
  in no pool - and a province created with the paint tool is named as you create
  it. Every one of these writes rebuilds the compiled `.strings.bin` beside the
  text file, because that is the file the game reads and a stale one is why
  "delete the .bin" is folklore.
* **Ctrl+Z / Ctrl+Y** in every editor, one value at a time.

## Cleanup

* **Clean up BMDB.** Finds battle model entries nothing references and files
  under `unit_models` no entry names, and moves them out of the mod into a
  folder mirroring its layout. References are checked against the EDU, mounts,
  characters, every campaign and battle script in the mod, every `.lua` script
  (M2TWEOP mods reference models by name from Lua), and every `data/descr_*.txt`.
  The last two are deliberately cautious: a false "still used" costs nothing, a
  false "unused" breaks a mod.
* **Recheck past cleanups.** Re-reads the cleanup log and re-tests what earlier
  runs removed against the current reference checks, then restores anything that
  should not have been removed.
* **Clean up the strat map.** The same for `descr_model_strat.txt` and
  `data/models_strat`.
* **Unit cards.** Folds identical per-faction card copies into the folder the
  engine falls back to, and removes art for units that no longer exist. 645 MB
  of Divide and Conquer's 1.2 GB of card art.
* **Clean up the unit file.** Group, tier and reorder `export_descr_unit.txt`
  repeatably. Running it twice produces no further change.
* **Fix ownership.** Adds a faction texture record to a model entry for every
  faction that fields a unit using it.

Nothing is deleted. Everything is moved to a folder you choose, and the removal
is backed up, so Log > Undo restores the mod exactly.

## Buildings

Every building line as a grid, with an editor per line: icons, name and
description, cost, build time, material, settlement size, capabilities, upgrade
path, and recruitment.

* **Requirements without code names.** Every term in a `requires` clause is
  picked from the mod's own data, since a typo is silent in game.
* **Ownership validation.** A `recruit_pool` naming a faction also needs the unit
  to list that faction in `ownership` and its model to have a texture for it.
  Both fail silently otherwise. Selecting a faction checks both.
* **Line checks** for problems only visible across a whole line: a unit that
  stops being recruitable as the building upgrades, a unit the city half trains
  and the castle half does not, and duplicate entries.
* **City and castle, side by side**, with controls to copy a pool across.
* **Bulk editing** of recruitment pools: one requires clause, pool numbers, or
  removal, applied to a selection built from several searches.
* The same pools are editable from the **other end** - the unit editor's
  Recruitment tab, above - for when the question is "where can this unit be
  hired" rather than "what does this building train".

## Safety

* Files are held as verbatim lines and every edit is a splice, so saving changes
  only the lines you changed. Comments, mixed indentation and line endings are
  preserved.
* Every write is backed up first and recorded in the log. Log > Undo restores
  byte-exact. That includes a whole file saved from Raw text.
* Parsers round-trip real mod files byte for byte, which is verified by the test
  suite against whatever mods are installed.

## M2TWEOP

Units defined in the extender's own folder rather than `export_descr_unit.txt`
are read as part of the mod's roster, badged EOP, and can be transferred,
edited, renamed, deleted and given a voice. Edits are written back to their own
file. A transfer can choose which file a unit is written to, which is how a unit
is kept outside the 500-unit cap.

A mod can be marked as M2EX on its Home card. That stops the toolkit reporting
the five engine limits M2EX removes, and it changes one thing about transfers
into that mod: a projectile's effect sets are carried across with it, rather than
being replaced by `invisible_placeholder_set`.

Effects are normally not imported because they live in files shared by every
projectile in the mod, and how many the engine will load is another of the
hardcoded tables - what sits past the end is dropped without a message. M2EX
replaces that table, so for a mod marked for it the toolkit copies each effect
set the source actually defines, the effects that set lists, and the models and
textures those name. A set the source does not define itself is left as a
placeholder as before: it comes from vanilla, and vanilla's copy is not the
toolkit's to move.

## Running from source

Same two files, same order: **`Install-Dependencies.bat` first**, then
**`Launch-Medieval2-GUI-Toolkit.bat`**. The first one installs Python 3.9+ and
Pillow if they are not already there (official installer from python.org, your
user only, no administrator prompt, added to PATH); the second one starts the
tool and steps into `main/` on its own.

By hand, if you would rather:

```bash
pip install pillow
python main/app.py
```

```bash
python main/app.py --check        # startup checks only, no server
python main/app.py --port 9000    # different port
python main/app.py --no-browser   # serve without opening a browser tab
```

## Building a release

```bash
python main/dev/release/build_release.py --version v2.2.0
```

Produces `main/dist/Medieval2-GUI-Toolkit-v2.2.0.zip`: the tool, a bundled
Python runtime, Pillow, and the packed vanilla building art. `--no-runtime`
builds a code-only zip for a machine that already has Python.

The vanilla building art ships by default and the build verifies the finished
archive contains it. A release archive is approximately 50 to 55 MB.

## Command-line transfer

```bash
python main/transfer_cli.py --from "<source mod>" --to "<dest mod>" --unit "Unit Name" --out transfers/out
```

`--list` shows the source mod's unit types. `--dry-run` plans without writing.

## Tests

```bash
python main/tests/test_parsers.py
python main/tests/test_transfer_v2.py
# one module per main/tests/test_*.py
```

Each suite is self-contained and safe to run against real mod installs. All
writes happen in temp directories or through the backup and undo path.

## Troubleshooting

Every run is logged to `config/server.log`, or to
`%LOCALAPPDATA%\UnitTransfer\server.log` if that folder is not writable.

**If something went wrong, send the log.** Settings > Something went wrong? >
Save diagnostic log downloads it. It records the build, Python version and OS;
each mod's file state before modification; what the job detected and decided;
and every file written, backed up, copied, exported or deleted, with paths and
sizes. It rotates at 4 MB.

**A mod the toolkit lists but cannot read** reports which file and why:

* `data/export_descr_unit.txt is not there`. The folder has a `data/` but no
  loose unit roster. Every stock install has four of these: `americas`,
  `british_isles`, `crusades` and `teutonic`, the Kingdoms campaigns, which keep
  their files inside `data/packs/*.pack`. Unpack the mod and it becomes an
  ordinary one.
* `battle_models.modeldb could not be read`. The file is length-prefixed, so a
  count that disagrees with what follows it desynchronises the reader and the
  read fails further down on a valid line. The message names the entry, the line
  holding the count, and the value to check.

**If the launcher window opens and closes with nothing visible**, the tool
usually started but your browser did not open. Go to `http://127.0.0.1:8756/`
manually.

**If the page says "The tool did not finish loading"** and names a file, the
server is fine but your browser never asked it for that file. An ad blocker or
privacy extension (uBlock Origin, AdBlock, Brave Shields) is the usual cause.
Turn it off for `127.0.0.1` and reload.

## Project layout

Only the three things a person actually opens sit at the top: the two `.bat`
files you run, and this README. Everything else is under `main/`.

```
Install-Dependencies.bat        run this first
Launch-Medieval2-GUI-Toolkit.bat  then this
README.md
main/
├── app.py                      starts the local server
├── transfer_cli.py             the same transfer, from a command line
├── unittransfer/               parsers and writers for each file format, the
│                               transfer engine, the in-mod edit engine and the
│                               HTTP server
├── web/                        the browser UI: plain JavaScript, no build step
├── vanilla_ui/                 packed vanilla building art, the fallback for
│                               any icon a mod does not ship
├── vendor/nvtt/                NVIDIA Texture Tools 2.0, driven headless by
│                               Sprites mode for TGA -> DXT5
├── tests/                      one module per area, each runnable on its own
├── docs/                       ROADMAP, STATE and their archives
│   ├── releases/               the release notes, one file per version
│   └── upstream/               the reference-tool audits, the port manifest
│                               and the sync log
└── dev/                        scripts for working ON the toolkit, never
    ├── release/                shipped with it: build the zip, pack the art
    ├── reference/              index and sync the reference material, and
    │                           generate the trigger vocabulary from it
    ├── checks/                 prose and documentation checks over the repo
    └── diagnose/               decode one file and print what is in it
```

`main/config/` (settings, backups, the undo log) and `main/dist/` (build output)
are created as they are needed and are not in the repository.

## Credits

**Developed by** ProJYeet

**Co-developed by** Demir

**Built on the work of, and thanking them for permission to take reference from
their code**

* [M2TW Editor](https://github.com/Machiavello-1441/m2tw-editor) by Mylae
* [Medieval II Total War Modding Tool](https://www.twcenter.net/ubs/medieval-2-total-war-modding-tool.26/) by Fynn
* [Bare Geomod](https://www.moddb.com/mods/bare-geomod-and-tools) by Sinople and Gigantus
* [TWMapReader](https://www.twcenter.net/threads/tw-map-reader-v2-24-1-jul-2015-update.438278/) by Withwnar

**Sponsored by** FeatherLeaf

**Special thanks** Gigantus and the TWCenter community, for the guides that
taught everyone, this tool included, how these files actually work.

**Testing** Jayzinski, TheHolyPilgrim, Espartan, Anhlego, Lupinemaverick and empire3376

## Changelog

See [Releases](../../releases).
