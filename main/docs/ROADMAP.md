# Medieval 2 GUI Toolkit - Roadmap (present and future)

**This file is what is left to do.** Everything already built has been moved to
[ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md), verbatim, so a session no longer
reads 3,000 lines of finished work to find the next step. What stays here is
what a session still has to act on: the locked decisions, the phase index, the
map-format reference the map modules are built on, and the schedule of what is
left. **When a phase finishes, its write-up goes to the archive and its row here
moves up into the phase index, in the same commit** - the rule in *The four documents*
below, restored on 2026-09-23 after this file had grown back to 5,000 lines.

**Where to look**

| You want | Read |
|---|---|
| the next thing to do | this file, the **schedule** below, then `STATE.md` |
| what shipped and why a rule is a rule | `ROADMAP_ARCHIVE.md` |
| what the last few sessions did | `STATE_ARCHIVE.md` |
| the reasoning behind a backlog item | `docs/upstream/REFERENCE_GAPS.md` |
| the strict release rules | `RELEASE.md` |

**Reference tool:** [Mylae's M2TW Editor](https://github.com/Machiavello-1441/m2tw-editor)
(React/Base44, ~59.6k LOC, works directly on `main`, no releases - used with the
author's permission). We port **behaviour and format knowledge**, never JSX.

**Ground truth when a format is unclear:** the TWCenter tutorial archive in
`Reference/TWCenter/` (indexed in Phase 1), then the Blender M2TW addon in
`Reference/Medieval-2-Toolkit/` for 3D formats.

Every phase is session-sized or explicitly split. A session doing roadmap work
**must** end by updating `STATE.md` (contract at the bottom of this file),
running the test suite, and running `graphify update .`.

---

## Locked decisions

- **One engine.** `unittransfer/` (Python) is the sole owner of parsing and
  disk I/O. No second parser for the same format anywhere, ever.
- **Vanilla UI only.** Reference modules are rewritten in our stack (plain JS
  served by the Python server, zero build step). No React, no npm.
- **Code View everywhere, built once.** A shared two-pane widget (GUI ⇄ raw
  code, hover-highlight, two-way live edits, server-side parsing with a
  field→line span map). Built in Phase 4, adopted by every editor after it.
- **No AI / autogenerate features. Hard no.** Excludes porting their
  `LuaAiAssistant`, `ScriptAIAssistant` and symbol generator. **Amended
  2026-09-03:** the OSM / Köppen / land-cover fetchers were swept in here by the
  same rule and are now *deferred, not excluded* - they land in Phases 25 and 27
  (see below), opt-in and off by default, because a map editor is the one module
  where a real-world backdrop is worth the network call. The three AI assistants
  above stay a permanent no.
- **V3 is the Campaign Map Editor** (Phase 16, sessions 16a-16k). It goes as
  deep as the reference tools do - map layers, regions, painting, validation,
  and the whole `descr_strat.txt` campaign database including characters,
  family trees, diplomacy and faction creation.
- **Pillow only, for the map too.** Measured on DaC's real map: all ten TGA
  layers decode in under 100 ms, the unique-colour census is 6 ms, the region
  label image 5 ms. The reference tool's lag is repeated work, not a slow
  language, so no numpy and no C extension - see the campaign map
  reference below.
- **A rule with no evidence reports nothing.** A check that needs a vocabulary
  asks for that file first and, when it is not on disk, names the file that
  would let it run. It never reads "no climate is declared" as "every climate
  colour is undeclared". Graduated out of `STATE.md` 2026-09-05; measured in
  16f, and it is why the stock game's packed `data/` does not produce 11 faults
  and 55,755 bad tiles against a map that ships with the game and works.
- **A baseline shows and stops blocking; it never hides.** A mod is somebody
  else's work with somebody else's bugs in it - vanilla's own map has 63
  findings - so an inherited fault stays visible and counted but does not refuse
  a save. A tool that blocks on 40 of them is one nobody uses twice; a tool that
  hides them is one nobody believes. Graduated 2026-09-05.
- **Localised names first** everywhere in the UI, code name in brackets -
  `Town Hall (core_building)`.
- **Self-hosted local app.** Never a hosted browser app; file access stays
  server-side with backup/undo on every write.
- **Don't vendor their `dist/`** or any bulk assets from the reference repo.
- **Versioning:** **2.0.0 shipped at the end of Phase 14** (2026-08-19), with
  every V2 editor module complete. Release titles are "M2 GUI-Kit
  VX.Y.Z - …".
  *This supersedes the original rule, which was "stay on 1.x until the Campaign
  Map Editor lands".* The reason it changed: 1.9.9 shipped a unit-transfer tool,
  and what is in 2.0.0 is a different program - a rebrand, six new editor
  modules, a shared Code View, and a whole polish pass over them. Holding the
  major number back for one unbuilt feature would have meant shipping all of
  that as a point release. **The Campaign Map Editor is now 3.0.0** (Phase 16).

---

## Phase index

Every phase in this table is finished. The write-up for each one is in
`ROADMAP_ARCHIVE.md` under the same heading; the table is here so the numbers in
commit messages, `docs/upstream/PORT_MANIFEST.json` and `STATE.md` still resolve.
A phase from the schedule further down moves up into this table when it
finishes; the schedule holds only what is left.

| # | Phase | Shipped in |
|---|---|---|
| 0-3 | V2 kickoff, TWCenter index, upstream tracking, UI split | 2.0.0 |
| 4-5 | Code View widget + line-map API; Home module | 2.0.0 |
| 6-9 | Strings editor; trigger/condition core; Traits; Ancillaries | 2.0.0 |
| 10-12 | Minor Files; Factions editor; EDB upgrades | 2.0.0 |
| 13 | EDU + Sounds audit | 2.0.0 |
| 14a-14i | Bug-fix and polish pass | 2.0.0 |
| 14j | Replace any picture | 2.0.1 |
| 15-15d | 3D model viewer: decoder, viewer, addon audit | 2.1.0 |
| 15e-15f | Port between mods, M2EX flag, docked viewer; two cleaners | 2.1.2, 2.1.3 |
| 15g-15h | Add a faction (twelve files); recruitment on the unit; UV mode | 2.1.8, 2.1.9 |
| 15i-15j | Model beside a transfer; resizable panels; no em dashes | 2.1.10, 2.1.11 |
| 16a-16k | **Campaign Map Editor** - read, render, paint, validate, query, write, preview | 3.0.0 (uncut) |
| 17a-17i | Campaign map correction pass - Home's card, the hover trail, the marker click, the markers layer, the tooltip, one faction screen, the prose and the credits | 3.0.0 (uncut) |
| 18a | Four files nobody could edit - guilds, campaign descriptions, faction movies, the region's mercenary pool | 3.1.0 (uncut) |
| 18b | Events and disasters - `descr_events.txt`, `descr_disasters.txt`, and their positions on the marker layer | 3.1.0 (uncut) |
| 19a | The keys a new record needs - the province and settlement names, and the pool a character's name comes out of | 3.1.0 (uncut) |
| 19b | Rename, and follow it - a province, a settlement and a faction slot, position-aware over twenty-four files | 3.1.0 (uncut) |
| 20a | Three layers read properly - the river overlay, the heights as transparency, and a number key per layer | 3.1.0 (uncut) |
| 20b | Getting to the thing you want - the campaign browser and the three campaigns nothing offered, the find box, named view presets | 3.1.0 (uncut) |
| 20c | Labels, and picking a tile - settlement names placed so none covers another, and one pin that writes a clicked tile into any coordinate field | 3.1.0 (uncut) |
| B1 | A new province reaches every campaign that reads the map - a settlement, a music type, the lookup pair, a campaign's own record file and compiled map; the creator is a picker and the shown names are required | 3.1.0 (uncut) |
| 21 | Two screens over data we hold - is this faction complete, with each gap copied from a template, and a raw text editor for any file the toolkit reads | 3.1.0 (uncut) |
| 22a | Forts and watchtowers - placed on a clicked tile, dragged, changed and deleted, one line each, filed under the province they stand in | 3.2.0 (uncut) |
| 22b | Resources through the same writer, the nearest tile that would do for every placement rule, the Localize ring, and 17d's drag made to drop | 3.2.0 (uncut) |
| 22c | A campaign that ships its own map files is drawn, probed, checked and fixed on them, and the brush is refused where it would paint a map nobody can see | 3.2.0 (uncut) |
| 23a-24 | The map in the game's own ground textures, winter and the tint; delete a province, make a campaign | 3.2.0 / v2.3.0 |
| 28-31, 33-36 | The map screen's menu and toolbar; missing textures; river rules; three map wins; add a climate; rebels in place; a region's colour | uncut, beta |
| 29 + B4 | The strat model viewer | v2.3.2 |
| 32a-32c | The mercenary pools: one parser, both directions, six rules and a repair | uncut, beta |
| 37-43 | The spawn export and FE zoom; campaign constants; the engine ceilings; the new province the engine cannot read; merge a name pool; a clone's missing art; playable and unlockable | uncut |
| 44-49 | The EDB tree checked; hidden resources; the Cultures screen; the sound scripts; two strings rows; the strips and one place for models | v2.3.5 onward |
| 50-53 | The map's defaults; the EDB editor's order and insert; change sets recorded and switched | uncut |
| 54 | Health - one door to every check (M17) | v2.3.7 |
| 55 | A battle model that moves (M16, playback) | uncut |
| M18 | The map in 3D | beta |
| 56-60, 62-69, 74-76 | Several factions and the faction zip; the animation editor and converter; will this mod launch; settlement mechanics; add a religion; one file in or out; the minor files (populace and off-map models, animals, standards, advice, battle banners, hero abilities, area effects, walls, agents and generals); a settlement model imported; the `.cas` view placed by its skeleton; a building tree from another mod; and 71's `data/` zip loaded back | v2.3.9 at the latest |
| 61, 70-73 | Delete, create and copy a settlement; every tile as text; a campaign as a zip; a horde start; a campaign from another mod | beta 2026-09-25 at the latest |
| 25-27 | The OSM backdrop and coastline; map resize and a map from scratch; the layer generators | beta 2026-09-25 |
| 77-81 | The packs read; the 687 slots named; transfer held against the destination's pack; every packed animation in the Models viewer, with its weapons, its mount, `.cas` models and another mod's side by side; a port appended to a pack and taken back | v2.4.0 |
| 83 | Unit Transfer brings a unit's missing animations into the destination's packs | v2.4.0 |
| 84 | A ported unit kept rebuildable: a loose `.cas` for each animation, its cues, and a `descr_skeleton.txt` block | v2.4.0 |
| 85 | Pack housekeeping: what a mod's packs hold that nothing plays, and a compacted pack with Undo | v2.4.0 |
| 82 | In-game proof: an appended pack loads, the two counts must agree, the first duplicate plays, a loose file does not override the pack | - (answers) |
| 86 | Animations on their own: an edit saved into the pack, another mod's animation in one slot, a skeleton ported alone | v2.4.0 |
| 87 | The real world, whole: Mylae's New Map Editor, 87a-87h | beta 2026-09-26 |

Nothing below Phase 16 gates anything still to be built - the dependency rules
that mattered while V2 was being built are recorded in the archive. What *does*
gate later work is stated where it applies: 17d's markers layer is what 18b (done),
20c (done) and part of 22 build on, and Phase 22 gates the orphan-handling half of 24.

`unittransfer/flatrecord.py` (extracted in Phase 11) is the shared engine for
every file that is a run of `<head> <name>` records with `keyword value` lines -
rebel factions, resources and factions today. Check for it before writing a
parser: Phase 11 needed none at all.

---
## Campaign map reference (living - read before touching a map module)

Phase 16 built the campaign map editor across eleven sessions, 16a to 16k, and
they are all done; the write-ups are in `ROADMAP_ARCHIVE.md`. **This section is
not history.** It is the reference every map module was built on and is still
built on: which of the four tools is the arbiter for what, why this is Pillow
and not C++, the format knowledge that was banked before a line was written,
and which module owns which file. A session changing `campmap.py`, `maptga.py`,
`campaint.py`, `mapcheck.py`, `mapquery.py`, `stratedit.py`, `stratchar.py`,
`stratcamp.py`, `winconds.py` or `cas.py` reads this first.

### The four references, and what each one is for

`Reference/Map/` holds three of them; the fourth is mirrored in this repo at
`refs/upstream/editor/main` and tracked by `dev/reference/upstream_sync.py`.

- **`Reference/Map/Demir.html`** ("StratMap Forge v0.4", 350 KB, one `<script>`)
  - the deepest **validation rule set** in the folder and the only **campaign
  database editor**. Its rules are the most valuable artifact in it. It is also
  the one that lags; the anatomy is below.
- **Mylae's `src/components/map/`** - the **paint tool**: layer picker,
  pencil/bucket/pipette, per-layer colour presets (`paintPresets.jsx`), the
  three-step new-region wizard, and the one performance fix he already found
  (debounced bitmap rebuild, per-layer async `toBlob` encode).
- **`Reference/Map/TWMapReader_source/`** (Java, ~25k lines) - the
  **reverse-engineered engine behaviour** nobody else has: region ID derivation,
  port ownership, the three coordinate systems, adjacency across land bridges
  and river crossings.
- **`Reference/Map/Geomod_Tool_and_Manual/`** plus
  `Reference/TWCenter/Creating a World – Basic mapping from scratch` - the
  **format arbiter**: layer sizes, the full colour tables, the river rules, the
  200-region cap and the crash list.

### Why this is Python and not C++

Measured with Pillow against DaC's real map (`map_regions.tga` 510x487, the
2x+1 layers 1021x975):

| operation | time |
|---|---|
| decode one RLE 32-bit `map_heights.tga` | 13 ms |
| decode all ten layers | 117 ms |
| unique region colours (`Image.getcolors`) | 202 colours, 13 ms |
| region-id label image, exact | 61 ms |
| per-region count, bbox and centroid, one pass | 180 ms |
| sea mask (`ImageChops`, in C) | ~5 ms |
| centre-sample a 2W+1 layer (`Image.transform`, affine) | 3 ms |
| `map_regions.tga` to PNG for the browser | 74 ms, 22 KB |
| worst case: exact per-pixel scan in pure Python | 106 ms |

**Two of those numbers were wrong when this phase was scoped, and 16a corrected
them by measuring.** `Image.quantize` with a fixed palette builds a label image
in 3 ms and is *approximate*: its nearest-colour matching put 1,320 of DaC's
248,370 pixels on the wrong region even with every colour in the image present
in the palette exactly. An index that is 99.5% right is not an index, so the
label image is an exact dictionary pass over the raw bytes at 61 ms. The whole
read of DaC's map, index included, is about 450 ms, once, at load.

`descr_terrain.txt` caps width and height at 510, so the largest layer any mod
can have is about a megapixel. **The reference tool does not lag because the
work is large - it lags because it repeats it.** In `Demir.html`: `paintAt`
(1224) nulls the layer canvas, so the next `render()` allocates a fresh
`<canvas>` and `putImageData`s the *whole* image, and `paintLine` (1723) calls
it per Bresenham pixel, so one 40 px drag is 40 full-image uploads inside a
single input event. The water brush (1235) invalidates the terrain composite,
which then rebuilds over ~820k pixels calling `sampleMapLayer` seven times per
pixel, each call allocating a three-element array and a `join(',')` string for a
Map lookup - about **5.7 M array and 1.6 M string allocations per painted
pixel**. `validate()` (1403) runs after every edit and is O(descr_strat lines x
army objects), 30 to 180 million iterations on a real mod. `commitStratLines`
re-parses the entire file after every edit, eight to ten times to save one
faction detail. Colour keys are template-literal strings allocated per pixel in
three separate builders.

None of that is a language problem. **Decision: Pillow only** - no numpy, no C
extension - which keeps the vanilla-UI, zero-build-step, one-dependency rule,
the 50-55 MB release zip and the disk headroom on `D:`. Speed comes from four
architectural rules instead:

1. **A label image, built once.** Borders, selection masks, thematic recolour,
   hit tests, unknown-colour audits and per-region counts all read a
   `region_id` byte array, never RGB triples. Packed integer keys
   (`r<<16|g<<8|b`), never strings.
2. **Dirty rectangles.** An edit touches at most `brush^2` pixels; only that
   sub-rect is re-encoded and re-sent.
3. **Parse once, splice after.** The line-index-preserving edit model is the one
   thing Demir gets right - it keeps comments, tabs and unknown directives
   intact. Keep it, add a block interval index, never re-parse the world.
4. **Nothing O(pixels) on the interaction path.** Validation, adjacency and
   region IDs run on demand, never per stroke.

### Format knowledge banked before a line is written

Every item below is either measured on DaC or sourced to the arbiter, and each
one is a rule at least one reference tool gets wrong.

- **DaC's `descr_regions.txt` uses a `legion:` line**, making the record ten
  lines, not nine. Mylae's parser hard-codes RGB at offset 4 and its resync
  guard then skips **every DaC region** silently. Demir and TWMapReader both
  handle it.
- **A wasteland short form** exists (three lines, no settlement), and a
  wasteland province must be the **last entry in the file**.
- **The two bare numbers are triumph value then base farming level.** Confirmed
  twice over: the 2026-08-20 sync measured vanilla's 112 regions, and Geomod's
  manual says "Victory ... leave it at 5, other numbers may cause a crash" and
  "Agriculture ... 4 is approximately average, 6-7 highly fertile".
- **Religion percentages must sum to 100** or the game crashes.
- **A tile is sea iff its `map_heights.tga` pixel is not greyscale, or is pure
  black**, not from ground types. River crossings are force-excluded from the
  test. Measured at tile centres on DaC, where the rule is actually applied:
  74,317 tiles come out sea and 74,247 of those are also sea by ground type, so
  the two agree to 99.9%; the 70 that disagree are the underwater-land tiles the
  region-id scan has to skip. (An earlier note here said 165 of DaC's 420 height
  colours are `(0,0,B)` blues. 165 of them are non-greyscale; only 19 are blue,
  and the rest are near-greys like `(65,64,63)` living between the tile centres.)
- **The 2x+1 layers sample the block centre**: tile `(tx,ty)` reads pixel
  `(2*tx+1, 2*ty+1)`. Corner sampling is wrong.
- **Layer sizes**: `map_regions`, `map_features`, `map_trade_routes` at `W x H`;
  `map_roughness` at `2W x 2H`; `map_heights`, `map_fog`, `map_ground_types`,
  `map_climates` at `2W+1 x 2H+1`; `water_surface` nominally 256x256, but DaC
  ships 1021x975, so that one is advisory.
- **Three coordinate systems**: image (y down), game/`descr_strat` (y up,
  `game_y = H - 1 - image_y`), and double-size. Every accessor names which.
- **The TGA descriptor byte matters.** TWMapReader's `Utils.writeTGA` carries a
  field note that M2TW *crashed* on descriptor `0x18` and `0x20`, and that
  `0x08` is what works; every real DaC layer is `0x08` or `0x00`. Demir's writer
  flattens everything to uncompressed 24-bit `0x00`. Ours preserves type, depth,
  origin, any ID field and any 26-byte v2.0 footer, and all ten of DaC's layers
  re-encode **byte for byte identically** through it, RLE included. One trap
  found in 16a: `water_surface.tga` carries a 495-byte v2.0 extension area whose
  position is an *absolute file offset* stored in the footer, so a layer that
  re-encodes to a different length has to have that offset moved or the file is
  quietly broken.
- **200 regions maximum, sea colours included.** DaC has 202 unique colours in
  `map_regions.tga`, two of them the black/white markers - it is on the cap.
- **Rivers**: no diagonal connections, no rejoins, extend two pixels past the
  coastline, white pixel at the source, `0,255,255` for a ford.
- **A settlement or port pixel may not touch another region's pixel**, not even
  at a corner, and must not sit on a river/ford/source/volcano feature pixel
  (back-to-menu crash) or on impassable ground.
- **Port ownership** is decided by the four cardinal neighbours: a direction is
  a "dock" if it is sea and the opposite neighbour is on-map and not sea. Three
  docks picks the middle, two picks the most northerly, one picks itself, zero
  or four is undeterminable.
- **Region IDs** are the order of first appearance scanning row-major over
  `map_regions.tga`, skipping settlement and port pixels, and skipping tiles
  that `map_regions` calls land but `map_heights` calls sea.
- DaC's `map_features.tga` holds one stray `(1,1,1)` pixel - a live test case.

### Module layout

**Not `unittransfer/stratmap.py`.** That name is taken by the
`descr_model_strat.txt` cleaner (1046 lines, a different concern); the earlier
draft of this phase pointed 16a at it by mistake, and 16a corrects the line.

| module | owns |
|---|---|
| `unittransfer/campmap.py` | `descr_terrain.txt`, the ten TGA layers, `descr_regions.txt`, the region index, the coordinate transforms |
| `unittransfer/maptga.py` | TGA read/write preserving type, depth, origin and footer (Pillow decodes; the header is ours) |
| `unittransfer/mapvocab.py` | ground/climate/feature/height colour tables with localised names, in `edbvocab.py`'s shape - **and `RIVER_CODES`**, which `mapcheck`'s river rules and the map screen's river overlay both read (20a) |
| `unittransfer/campstrat.py` | `descr_strat.txt` as a line-preserving block model with an interval index |
| `unittransfer/campaint.py` | strokes, the undo stack, the palettes and the paint save (16e) |
| `unittransfer/mapcheck.py` | the 35 rules, the baseline and the four auto-fixes (16f, 31) |
| `web/js/mapcheck.js` | the validator panel, its filters and jump-to-pixel (16f) |
| `unittransfer/mapquery.py` | the fact table, the 24 filters, the themes, Geomod's information maps and the TGA export (16g) |
| `web/js/mapquery.js` | the query panel, the legends and the recolour of the region layer (16g) |
| `unittransfer/stratedit.py` | the settlement block written back: its fields, its buildings, the move between faction blocks (16h) |
| `web/js/stratedit.js` | the settlement panel, its building rows and the live plan under them (16h) |
| `unittransfer/stratchar.py` | the character block written back: the line, the traits, the army, the family rules, the move between factions (16i) |
| `web/js/stratchar.js` | the people panel, its trait and regiment rows and the family tab (16i) |
| `web/js/campmap.js` | viewer, layers, legend, inspector (16c, 16d) |
| `cmapMask` / `cmapModeKey` | the one pixel pass: the hide set, the river whitelist, the height ramp. Anything that changes what a layer looks like without changing where it is drawn goes here, and the composite's cache key reads `cmapModeKey` (16d, 20a) |
| `campmap.HOTKEYS` | which number key ticks which layer, sent out with the manifest so the panel and the handler cannot drift (20a) |
| `campmap.view` / `layer_png` | the manifest and the PNG the browser is served (16c) |
| `campmap.layer_legend` / `probe_pixel` | what a colour means, and what one tile is (16d) |
| `campmap.render_block` / `plan_region` | one region's record, spliced and saved (16d) |
| `web/js/campaint.js` | the paint tool and its undo |
| `unittransfer/stratcamp.py` | the campaign header, the three rosters, the diplomacy section, a faction's scalars, and creating or deleting a faction entry (16j-1, 16j-2) |
| `web/js/stratcamp.js` | the campaign settings tabs, the diplomacy matrix and the win conditions (16j) |
| `unittransfer/winconds.py` | `descr_win_conditions.txt` as lines plus an index over them (16j-2) |
| `unittransfer/cas.py` | the `.cas` chunk list: meshes, materials, the node table and the skeleton, handed to Phase 15's viewer as a `MeshFile` (16k) |
| `web/js/stratview.js` | the strat-model picker beside the map (16k) |
| `web/js/campmark.js` | the markers layer: everything with a coordinate, drawn and grouped per tile (17d, extended by 18b) |
| `unittransfer/campfiles.py` | the campaign folder's small files: menu text, faction movies, the region's mercenary pool (18a) |
| `unittransfer/campevents.py` | `descr_events.txt` and `descr_disasters.txt`, both spliced, and the positions the marker layer draws (18b) |
| `web/js/campevents.js` | the events and disasters panel, and `＋ from the picked tile` (18b) |
| `campstrat.campaign_paths` / `campaign_rel` | every campaign the mod ships at any depth, and the one conversion from a campaign name to a path under `world/maps/campaign` - every module that builds one goes through it (20b) |
| `campfiles.browse` | D14's payload: each campaign's dates, rosters, contents, which of the folder's files it has and whether it ships map layers of its own (20b) |
| `web/js/campbrowse.js` | the campaign browser, and the pick (20b) |
| `web/js/mapfind.js` | the find box: `cfdSearch` is pure and searches the manifest, not the server (20b) |
| `web/js/mapviews.js` | named view presets: `cvwPlan` reconciles a saved one against this manifest, and is pure (20b) |
| `campaint.map_campaigns` | which copy of each map file every campaign reads - its own when it is in the folder, `world/maps/base` when not. **The engine takes each file separately**, so anything written to the base map has to ask this which campaigns see it (B1) |
| `stratedit.new_block` / `plan_new_settlement` | a new settlement block in the shape its own file writes them, last in the owner's block, guarded like 16h's edits - B1's writer, and the one B2's create is to share |
| `web/js/maplabels.js` | settlement names on the map: `clnLayout` is the pure placement - TWMapReader's candidates, biggest province first, markers as obstacles, a name with no room left off and counted - and `clnDraw` draws the cached layout for the zoom on screen (20c) |
| `web/js/mappin.js` | the pin: `cpinButton` beside any coordinate, `cpinTake` the click that answers it, flipped once into game coordinates (20c) |
| `mapquery.add_music_region` | the one write `descr_sounds_music_types.txt` gets: a name on the end of one `regions` line (B1) |
| `unittransfer/factionaudit.py` | D6: every faction against every file that should name it, one pass a file for all of them (`Census`); gap or note per row, measured on the installed mods; the repair is `factionclone.clone_file` per gap (21) |
| `web/js/facaudit.js` | the "Is it complete?" panel on the faction screen, the picker's gap counts, and the Copy-from repair (21) |
| `unittransfer/rawtext.py` | D11: any text file the toolkit reads, as text - its own encoding and line endings kept (`splice`), a stale save refused, the readers' before-and-after as warnings (21) |
| `web/js/rawtext.js` | the Raw text mode: the list, the box that is never redrawn, the plan under it (21) |
| `unittransfer/stratobj.py` | D9: a fort, a watchtower or a resource, one line, edited, added, deleted or moved; a fort between region sections, a resource between the province headings a file groups them under; where a new one goes read off the file; the rules measured on the 800 forts and 2,813 resources installed (22a, 22b) |
| `unittransfer/mapsnap.py` | D10: the nearest tile a caller's own rule accepts, nearest first, within 40 tiles. The rules stay where they are - `stratobj`, `stratchar` and `mapcheck.marker_faults` each hand theirs over (22b) |
| `web/js/campforts.js` | the forts and resources panel: place with the pin, the province's list, the form, D10's ⌖ Move button, and the drop 17d's drag hands it (22a, 22b) |
| `unittransfer/mapterrain.py` | D7 and T1: `descr_aerial_map_ground_types.txt`, and the map drawn with the mod's own aerial-map textures. `Vocabulary.texture` is the one place the engine's four rules are applied, `plan` the cheap half the validator reads, `composite` the picture, and `_index` an exact colour-to-index pass in Pillow's C (23a) |
| `cmapTerrainOn` / `cmapTerrainDraw` | whether the backdrop is being drawn, and the one blit of it - under the whole stack, at its own several pixels a tile, addressed in tiles like everything else on the screen (23a) |
| `cmapThemeDraw` | 16g's colouring over the terrain and the stack both: the fill, blended for T12's tint or laid on for a solid, and the frontiers, which are never blended. It is on the screen canvas rather than in the composite because that is one pixel a tile and the terrain is not (23b) |
| `Colouring.payload`'s `bands` / `cqGroups` | which group each province is in, `-1` for none, absent for anything that is not a province. What a border is worked out from on both sides; the colour cannot answer it, because a "none" group and no group are painted the same grey (23b) |
| `regiondel.heirs` / `regiondel.campaigns_reading` | who can inherit a province's land, ordered by shared border, and which campaigns a change to this map reaches. The first is `campaint.neighbours` with the record joined on; the second is 22c's ruling as a list (24) |
| `renames.mentions` | every line in the mod naming a thing, split into the scripts (listed, never written) and everything else (counted per file). A rename's scan, shared with the delete (24) |
| `cmapLayerState` / `cmapCampQ` / `cmapGoTile` | the one snapshot of the layer stack, the one place a request appends a campaign, and the one way of arriving at a tile (20b) |

Reuse: `keyblock.py` for the splice discipline (`flatrecord.py` does **not**
fit - `descr_regions.txt` is positional, not `keyword value`);
`IconCache.png_bytes` for the disk-cached never-raises PNG route;
`triggers.split_lines` so a line number means the same thing in every editor;
`v3UvEdDraw` / `v3UvPointers` / `v3UvAt` (`web/js/viewer3d.js:1013-1219`) for
pan, zoom, DPR and the "a press that moved under 4 px is a pick" rule.

**The browser never parses a TGA.** Python decodes, serves PNG and owns the
canonical pixel buffer; the browser paints a local RGBA preview and posts stroke
operations. That is the "one engine" rule, and it is what makes undo, backups
and server-side validation possible at all.

**The browser's own arithmetic is tested in node**, not reimplemented in Python
to be tested there. `tests/test_maplayers.py` loads the real `campmap.js` into a
bare V8 context with a stubbed canvas - the file has no top-level side effects,
so `vm.runInContext` is enough and there is no DOM library - and hands it pixels
the suite wrote and real layers projected through `campmap.tile_view`. 20a's
mask pass is measured that way, and so is 20c's label placement
(`tests/test_maplabels.py`, over every installed map at six zooms).


---

# The schedule - what is left

Set on 2026-09-23 on the user's word ("finish all phases remaining in
roadmap"), with 87 and 88 added on 2026-09-25. A finished row moves up into
the phase index. The schedule as it stood, with how it was ordered and the
notes on 74-76, is in `ROADMAP_ARCHIVE.md` under *The 2026-09-23 schedule*.

On 2026-09-30 the user moved the translations to the end ("skip the languages
phases for now and group them move it to later and do the other stages
first"): 88a-88c are done, and the catalogues themselves (several million
tokens of output) wait until 89-94 are built. On 2026-10-01 the user had them
split one language per phase, 88d-88t, so each can be done and stopped after
on its own. The order is now:

| # | Phase | Stars | Size | Line |
|---|---|---|---|---|
| 89 | Four reports from users: the resource list open on M2EX, a new resource, a watchtower's line of sight, the real-world map | - | M, split 89a-89d | a, b both; c, d beta |
| 90 | A layout that fits the window at every interface size | - | M, split 90a-90c | both |
| 91c | A cloned faction's three campaign files | - | S | both |
| 92 | Four things another import tool does that Unit Transfer does not | - | M, split 92a-92d | both |
| 93 | Two reports on getting around | - | S, split 93a-93b | both |
| 94 | A recruitment screen that lags, and its turns | - | M, split 94a-94b | both |
| 88d | German, and the per-language workflow (done 2026-10-01) | - | M | both |
| 88e, 88f | French, Spanish: one phase each | - | M each | both |
| 88i | Polish | - | M | both |
| 88m | Russian | - | M | both |
| 88o | Simplified Chinese, and the CJK fonts and line breaking | - | M | both |
| 88p | Traditional Chinese | - | M | both |

**Postponed indefinitely** on 2026-10-01 (the user: "Postpone italian,
portugese, polish, czech, hungarian, turkish, arabic indefinitely for now"):
88g Italian, 88h Portuguese (Brazil), 88j Czech, 88k Hungarian, 88l Turkish,
and 88t Arabic with 88s, the right-to-left layout, which only
Arabic needs. Their write-ups below stay as the plan for when they come back;
their termbase columns stay, and nothing offers them while they have no
catalogue.
Polish (88i) was brought back the same day ("bring back polish to
roadmap"), and 88n Ukrainian postponed with the rest ("postpone ukranian
too"), then 88q Japanese and 88r Korean ("postpone japanese and korean
too").

Releasing stays on request: each phase is committed to master as it lands.

# Phases 77-86 - animations that travel with a unit, scheduled 2026-09-23

**Asked for by the user on 2026-09-23**: "the main thing I want to do now is to
be able to port animations when transferring units ... without complete
unpacking or repacking if that's possible; if not, packing and unpacking is
fine too. Plan it out and turn it into phases, to do after all the remaining
phases are done". So these go **after 25-27**, unrated, in this order.

**The answer to "without unpacking": yes.** Nothing has to be unpacked or
repacked. A pack is a plain concatenation (verified on 21 195 animations and
730 skeletons), so porting a unit's animations is: read the few entries it
needs straight out of the source's `.dat` by offset, **append** them to the
end of the destination's `.dat`, and rewrite the destination's small `.idx`.
DaC's `pack.dat` is 352 MB and is never rewritten; the append for one soldier
skeleton is a median **1.6 MB** once animations the destination already has
(byte for byte, under any path) are reused. Undo is a truncate back to the
recorded length plus the old `.idx`, so the 352 MB file is never backed up
whole. The engine-rebuild route IWTE uses (loose `.cas` + `descr_skeleton.txt`,
the game regenerates the packs) is kept as Phase 84, a second safety net, not
the main path.

## Where the knowledge comes from

- **The pack format notes**, `Reference/PackFormats/` (untracked, on this
  machine): the container, a packed animation and a packed skeleton, byte by
  byte, with `tools/m2tw_packs.py verify` re-measuring every claim on vanilla
  DE, ROCSS and DaC in 5 s. Called "the format notes" below.
- **Discord with Wilddog and Makanyane** (IWTE's author and tester, June to
  September 2026). The facts that shape this design:
  1. IWTE gets a unit's skeleton **without unpacking**: it reads the modeldb
     for the skeleton name, then reads the skeleton pack and indexes it by
     name. (27/08)
  2. The packs are "a continuous list of unpacked skeletons or animations",
     no compression. (27/08; confirmed byte for byte.)
  3. IWTE writes loose `.cas` files and `descr_skeleton.txt` and **lets the
     engine regenerate** both packs, because of the tables at the end of a
     skeleton that nobody knows how to build. Older tools instead copied an
     existing packed skeleton and replaced its bones and animation list,
     keeping those tables. (27/08, 23/09) Phase 81 does the second thing:
     it moves whole skeletons, tables included, and never builds a table.
  4. **Many mods appended to their packs, so `descr_skeleton.txt` is often out
     of sync with them. The packs are the truth**, not the text file. (09/06,
     23/09)
  5. Duplicates in a pack come from that appending and "are often not
     actually exact duplicates". (23/09; DaC has 916 paths twice, vanilla 3,
     and vanilla lists the `MTW2_Halberd_primary` skeleton twice with
     different data.)
  6. A skeleton's animation list is a fixed sequence, "either a zero or an
     animation reference". (07/06, 23/09; measured: 687 slots, the last is
     `default`.)
  7. Each model has one skeleton, named in the modeldb (which holds one set
     per mount type), **plus weapon skeletons** for the primary and secondary
     weapon. They matter to the
     animation only when the mesh has vertices weighted to the weapon bones,
     but modders copy modeldb entries wholesale, so most entries carry them.
     (07/06, Makanyane; TWCenter thread "Understanding M2TW weapon skeletons
     and animations")
  8. Siege engines are different: a standard `.cas`, a mesh and an XML that
     aligns bones. Not in the packs. (23/09) Transfer already handles them
     (`descr_engine_skeleton.txt`); these phases do not touch them.
  9. A unit's `.cas` mesh has to be parented to its skeleton to be placed;
     buildings have no skeleton. (23/09) Relevant to Phase 80.
  10. Robust modeldb reading: IWTE reads every value into one list first and
      checks afterwards, so missing or extra CR/LF does not matter; a wrong
      count or an extra 0 still throws it. (23/09) An aside for `bmdb.py`, not
      part of these phases.

## Measured before a line is written (2026-09-23)

| fact | number | why it matters |
|---|---|---|
| every modeldb primary/secondary skeleton is in `skeletons.idx` | ROCSS 3 303/3 303, DaC 2 761/2 761 | the pack is the list to check a transfer against |
| **the modeldb weapon lists are skeleton names too** | ROCSS 5 372/5 375 found in `skeletons.idx`, DaC 3 780/3 780 | transfer's missing-skeleton check ignores them today (`ModelEntry.skeletons()` returns only primary/secondary) |
| ROCSS modeldb weapon skeletons not in its own pack | 3 (`MTW2_axe_Primary` ×2, `MTW2_HR_mace_Primary`) | a Health finding waiting to be reported |
| DaC and ROCSS share no animation path string | 0 of 45 784 | paths carry the mod they were built in (`mods/Third_Age_3/...`, `mods/americas/...`), so matching by path finds nothing |
| DaC animations already in ROCSS **byte for byte** under another path | 9 736 of 45 784 slot references (**11 133**, re-measured two ways in Phase 81); 166 of the 215 of DaC's `MTW2_2HSwordsman` | content dedup halves the append |
| DaC skeleton names ROCSS already has, with different data | **134 of 410** | renaming a ported skeleton is the common case, not an edge case |
| animations per soldier skeleton | median 145, max 219 | the unit of work |
| bytes appended per skeleton | median 3.3 MB, 1.6 MB after content dedup; max 5.1 MB | small against 70-352 MB packs |

## The design, in one place

- **One engine module, `unittransfer/animpack.py`**, owns every read and write
  of the four pack files (locked decision: one parser per format). `casanim.py`
  keeps loose `.cas`; `animpack` hands it arrays.
- **The packs are the truth.** `descr_skeleton.txt` is read, reported against
  the packs and kept in step for what we add, but never trusted over them.
- **Whole entries move, byte for byte**, with two exceptions that are
  rewrites of names, not of data: a skeleton's slot paths (when an animation
  path is renamed or deduplicated onto the destination's path) and nothing
  else. The combat tables at the end of a skeleton are carried as opaque
  bytes; the serializer is proven by round-tripping all 730 installed
  skeletons byte for byte before it writes anything.
- **Dedup order for an animation**: same path and same bytes in the
  destination, reuse; same bytes under another path, point the skeleton's
  slot at that path and append nothing; otherwise append, under the source's
  path, or under a namespaced path (`mods/<dest>/data/animations/ported/<source>/...`)
  when the destination has that path with different bytes.
- **Dedup order for a skeleton**: same name and same bytes, reuse; same bytes
  under another name, point the modeldb at that name; otherwise add, renamed
  `<name>_<source tag>` when the name is taken (the modeldb entry's skeleton
  and weapon names follow, through the `model_renames` machinery transfer
  already has).
- **Write order, for a crash midway**: append to `.dat`, write the new `.idx`
  to a temp file and swap it in, then update the `.dat` header's count. A
  crash leaves at worst unindexed bytes at the end of the `.dat`, which undo
  truncates.
- **Undo** records `(file, length before, sha of the header and last 64 KB
  before)` for each `.dat` and a normal backup of each `.idx`. It refuses,
  and says why, if the `.dat` is no longer the file it appended to (the game
  rebuilt it, or another tool wrote it). A new manifest kind next to
  `backed_up`/`created`, so `revert_to` still undoes newest first.
- **Never while the game runs** (the `.dat` is open), and never without the
  free space checked first (`D:` has been full before).

## The phases

**77 to 86 are done**, 2026-09-26 (84's in-game check waits on a mod that can rebuild, and 86's on the user's game); each one's scoping and write-up are in
`ROADMAP_ARCHIVE.md`, 82's six answers with them.

**Not in these phases**: exporting a unit with an animation for Blender (the
user's other Discord goal; 80 builds exactly the posed, animated unit an
exporter would need, and `modelexport.py` would carry it), and Rome/RR packs (a
half-frame layout; nothing here is measured on it).

# Phase 88 - every major language, scheduled 2026-09-25

**Asked for by the user on 2026-09-25**: "add a phase to add support for all
major languages. Make sure the words are correct technical words fitting for
the contexts". Unrated, both lines (it is not map work, and every screen
changes), after 87 in the table.

**What was there.** No internationalisation at all: `index.html` was
`<html lang="en">` and every string a person reads was an English literal in
one of the ~80 modules under `web/js/` or in a message the engine raises. The
crude count of ~380 and ~350 was an order of magnitude short.

**Measured by 88a, 2026-09-27** (`dev/checks/i18n_scan.py`, a lexer and the
rules for what is text): **6,927 runs of text in `web/js/` and `index.html`**
(3,280 in markup, 516 tooltips and placeholders, 3,131 plain literals, about
68,000 words before repeats), and **1,826 engine messages** in 94 of the 116
modules under `unittransfer/`, plus 159 built with `+` or `%`. After repeats
were merged the catalogue holds **8,027 strings, about 60,000 words**: 6,289
for the interface (41,000 words; 91 shared under `common.`, 64 of
index.html's under `app.`) and 1,738 engine messages (19,000 words).

**Two languages, never confused.** The *interface language* is the toolkit's
own buttons, headings and messages, and it is what this phase adds. The *mod's
language* is whatever its `data/text` files hold, and the locked decision
*Localised names first* already shows it: `Town Hall (core_building)` stays the
mod's own string whatever the interface language is. **Choosing an interface
language never changes a byte written to a mod.**

## The languages

English stays the source locale and the fallback. The targets, by BCP 47 tag:

| Group | Languages |
|---|---|
| Western and central European | German `de`, French `fr`, Spanish `es`, Italian `it`, Portuguese (Brazil) `pt-BR`, Polish `pl`, Czech `cs`, Hungarian `hu`, Turkish `tr` |
| Cyrillic | Russian `ru`, Ukrainian `uk` |
| CJK | Chinese (Simplified) `zh-Hans`, Chinese (Traditional) `zh-Hant`, Japanese `ja`, Korean `ko` |
| Right-to-left | Arabic `ar` |

Any language after these is one catalogue file and one termbase column, with
no code change; that is the test that the plumbing is right.

## The correct word, not the literal one

A literal translation is the failure this phase is built against: a mod tool
that calls a *trait* by the word for a personality quirk, or translates the
file keyword `hidden_resource`, is worse than English. So every string is
translated against a **termbase** (`web/i18n/termbase.json`), and each entry
records which of four rules it falls under and where its rendering comes from:

1. **Never translated.** File names, file-format keywords, script commands,
   condition names, attributes, code names, file extensions and product
   names (OpenStreetMap, Overpass, IWTE):
   `descr_strat.txt`, `recruit_pool`, `hidden_resource`, `export_units.txt`,
   `.cas`, `pack.dat`, EDU, EDB, modeldb. They are read exactly as written,
   by the engine or by the person searching for them, so they stay as they
   are, in the monospace style, isolated with `<bdi>` so right-to-left text cannot reorder
   them.
2. **The game's own term.** A concept the player sees in the game (faction,
   settlement, province, general, trait, ancillary, agent, building, unit,
   recruitment, mercenary, climate) takes the word the game's official release
   in that language uses, so the toolkit and the game name one thing the same
   way. The termbase cites the source string for each.
3. **The modding community's term.** A concept with no in-game name (skeleton,
   animation pack, heights map, ground types, bone weights, pivot, mesh,
   texture, UV map, strat model, the campaign map's layers) takes the
   established 3D and modding term in that language, which is often the
   English one kept as a loanword; the termbase says so rather than inventing
   a word nobody searches for.
4. **The platform's standard term.** Generic interface words (Save, Undo,
   Redo, Cancel, Settings, Import, Export, Browse, Preview, Apply) take the
   standard Windows term for that language (the Microsoft terminology
   collection), so a button reads the way it does in every other program on
   the machine.

A term with no source for its rendering is marked *unsourced* and the checker
reports it. Each catalogue carries a review status; a language no native
speaker who mods the game has read is shown as **draft** in the language
picker, never presented as finished.

## Rules the code keeps

- **Display is localised, file values are not.** Numbers, sizes and dates on
  screen go through `Intl.NumberFormat` and `Intl.DateTimeFormat`; a value
  typed into a field that is written to a file is parsed and written in the
  file's own format, ASCII digits and a `.` decimal separator, in every
  locale. A German decimal comma or Arabic-Indic digits never reach a mod.
- **Plurals by CLDR, not by `+ "s"`.** `Intl.PluralRules` picks the form
  (Polish, Russian, Ukrainian and Czech have three or four; Arabic six;
  Chinese, Japanese and Korean one), and the catalogue holds every category
  its locale needs.
- **Named placeholders only** (`{count} tiles in {region}`), never string
  concatenation, because word order changes between languages.
- **Sorting by `Intl.Collator`** in the interface language wherever a list is
  sorted by its shown name; lists sorted by code name keep code order.
- **The engine speaks message IDs.** A message the engine raises keeps its
  English text for the log and the command line, and carries an ID and its
  parameters; the interface shows the catalogue's string for that ID, or the
  English text when there is none. Logs, `server.log` and `transfer_cli.py`
  stay English, so a bug report is readable by whoever fixes it.
- **Vanilla stack.** `web/js/i18n.js` and one JSON catalogue per locale under
  `web/i18n/`, served by the Python server; no npm, no build step, no web
  fonts.

## The pieces

**88a - the plumbing and the pseudo-locales.** `i18n.js` (`t(id, params)`,
plural selection, the formatters, fallback to English per string),
`unittransfer/i18n.py` (message IDs and parameters on the engine's errors),
the interface language in Settings (defaulting to the first supported entry of
`navigator.languages`, else English), and `<html lang dir>` set from it. Two
pseudo-locales for testing: `en-XA` (accented, lengthened by about 35%,
bracketed, so a hard-coded string and a clipped button are both visible) and
`ar-XB` (English mirrored right-to-left). The real string count is measured and
recorded here. Done when: Home and Settings run fully under both
pseudo-locales, and English is unchanged.

*Done 2026-09-27.* The names the code calls are `tt(id, params)`,
`ttA` (inside an attribute) and `ttN(id, n, params)` (a plural): `t` is a
local variable in 294 places across `web/js/`, and a global of that name would
be shadowed in each. The server writes `i18n/catalogue.js` (English, the
chosen locale's catalogue and the offered list), loaded with `i18n.js` before
every other module, so a string is there when a module's first line asks for
it; the interface language is `ui_lang` in Settings, else the first entry of
`Accept-Language` with a catalogue (the server's view of
`navigator.languages`), else English, never a pseudo-locale. Choosing one
saves and reloads. The engine side is `unittransfer/i18n.py`: `msg(id,
template, **params)` is a `str` holding the English, exactly as the f-string
made it (`format(v, spec)`), and remembers its ID; `Handler._json` adds an
`_i18n` map of `{text: [id, params]}` to a reply holding one, and
`i18nFromServer` in `api.get` and `api.post` swaps each for the catalogue's
string in any language but English. index.html's own text is marked
`data-i18n` / `data-i18n-title` and so on, the English kept in the page.
`tests/test_i18n` (34).

**88b - every string externalised.** Every module under `web/js/`,
`index.html` and the engine's user-facing messages moved into `en.json` under
stable, namespaced IDs (`map.paint.brush_size`, not the English text as the
key). A lint suite fails on any prose literal outside the catalogue, with an
allowlist for rule 1's code names. Done when: the lint is clean, and every
screen in English is the same text as before, checked against a snapshot
taken first.

*Done 2026-09-27*, by two codemods rather than by hand, each proved rather
than trusted. `dev/checks/i18n_extract.py` rewrites a module's literals: a
run of text in markup becomes `${tt('id',{name:expr})}` (a quoted literal
holding markup becomes a template literal to take it), a tooltip
`${ttA('id')}`, a plain literal `tt('id')`. Every rewritten literal (5,411)
is evaluated twice in Node, old and new, with its expressions replaced by
markers and the real `i18n.js` loaded on the new catalogue, and must come out
the same string; then `node --check` on every file. A line break and its
indent inside HTML text is stored as one space (it draws as one; `<pre>`,
`<textarea>`, `<style>` and `<script>` are left out). IDs are
`<module>.<first words>`, `common.<words>` for a string three or more modules
share, `app.` for index.html, `eng.<module>.` for the engine.
`dev/checks/i18n_extract_py.py` does the engine's 1,826 messages: the first
argument of a `raise`, the arguments of a call named like a report
(`finding`, `Finding`, `fail`, any `...Error`), an `.append` onto a list
named like one (`notes`, `errors`, `warnings`...), and a report key in a dict
(`error`, `why`...), never `log.*`. The 47 literals that are code shaped like
words (`/icon?...` addresses, `onclick` handler strings, `translate()`,
`hsla()`, a media query) were found in the catalogue and put back as they
were; the rule that caught them is now in the extractor. **The lint is the
extractors' own rules**, so what one moves and the other checks cannot
disagree: `test_i18n` runs both over the tree and finds nothing left. The
before-and-after walk: every module's screen and the Settings dialog read
from a worktree of `2c5d589b` and from the result, text compared line for
line: identical but for two timings. Tests that read a module's words go
through `tests/_webtext.py`, which puts each call's English back (94.5% of
lines come back identical to the old source, the rest folded HTML text).

**Left for 88c** (done, see below), before a word is translated: 714 entries are fragments of a
sentence the code still joins with `+` (`tt('home.reading') + path + '…'`),
130 places make a plural with `+ 's'`, and 159 engine messages are built with
`+` or `%` and are still English only. Each needs its sentence whole, with
named placeholders, and its plural through `ttN`, or no translation of it can
be right.

**88c - whole sentences, then the termbase.** First what 88b left: the 714
fragments joined into sentences with named placeholders, the 130 `+ 's'`
plurals through `ttN` with a form per CLDR category, and the 159 engine
messages built with `+` or `%` given IDs. Then every technical term in `en.json` extracted and
classified under the four rules, with a rendering and its source per target
language. The checker enforces it: an English string containing a termbase
term must contain that term's rendering in each translation, a rule-1 term
must appear untranslated, and placeholders and plural categories must match
the source. Done when: every term has a rendering and a source in every
language, and the checker passes on the pseudo-locales.

*Done 2026-09-29.* **Whole sentences.** `dev/checks/i18n_joins.py` finds three
kinds of site: a `tt()` joined to other text with `+` (641 in `web/js` when it
first ran), an English plural made in code, `n===1?'':'s'` and its kin (226),
and a catalogue string that is half a sentence joined inside a template where
no `+` shows (`' after {delay}s'`, `'Could not read '`: one that opens with a
space and a lower-case word, or stops on a word and a space). With `--py` it
lists the engine's messages built with `+`, `%` or `.format` (159) and those
that make a plural in a parameter, `x='s' if n == 1 else ''` (33). All four
are at zero. A sentence is now one string with named placeholders; a clause
that was dropped in or left empty (`' and the record for {region}'`) is two
strings, one with it and one without, since a translator cannot inflect a
clause apart from its verb; a count is `ttN(id, n)` in the page and
`_i18n.msgN(id, n, one, other)` in the engine, whose `{count}` the page fills
with the right CLDR form. en.json holds **8,074 strings, 324 of them plurals**
(there was one). A site that is not a sentence at all keeps its shape with an
`// i18n-ok: <why>` on the line (14, twelve of them `undo.js`'s stack keys).
`dev/checks/i18n_params.py` holds each call to its string: every `{name}` the
string uses is passed, and every name passed is used, in the page and in the
engine, so a sentence that lost a piece on the way shows as a failure and not
as `{x}` on the screen; the few strings that show braces as text (a tile
address's `{z}/{x}/{y}`, the `{tag}text` form) are listed there by ID.

**What changed on the screen, on purpose.** English is otherwise the text it
was. A count of 1,000 or more now has its thousands separator (`ttN` formats
`{count}` for the screen). The singular now reads right where the code had only
one wording: "1 level", "1 region follows it", "1 guild gets points", "1
faction declares", "1 entry block shares", "1 tile has no texture". 88b had
moved some code into the catalogue as if it were text, and it is code again:
key prefixes (`'minor:' + tab`, a findings box's open state), and attributes
whose values are expressions (` aria-label="${...}"`, `data-vc="..."`); the
scanner now knows both shapes. About 300 strings still hedge with `file(s)`:
they are whole sentences, so each translation writes its language's own
neutral form, and turning them into plurals is left for when a count is at
hand.

**The termbase**, `web/i18n/termbase.json`: **189 terms** (80 of the game's,
43 of the modding community's, 66 of the platform's), each with the English
forms it is matched by and a gloss that says what it means here ("port" is the
verb, "tile" a square of the campaign map), and in each of the 16 languages a
rendering, a stem that every inflected form contains, its source kind (`game`,
`community`, `loan`, `ms`) and a confidence. Rule 1 has no entries: what is
inside a `<code>`, a file name, a `snake_case` name and the `keep` list (EDU,
EDB, IWTE...) are carried verbatim. **The renderings are a language model's
draft from memory, checked against nothing**: 1,835 are marked high, 922
medium, 267 low, and the file is marked draft; a native speaker who mods the
game reviews each language before 88d leans on it. `dev/checks/i18n_termbase.py`
is the checker: a translated catalogue has English's IDs and shapes, its
placeholders (a plural form may leave one out, as English's own forms do, but
uses none English does not), the CLDR categories of its language, the same
HTML tags, every rule-1 token as written, and each rule-2 and rule-3 term's
stem, a rule-4 word checked only where a string is that word alone (a button),
with an `_exempt` list per ID for a sentence worded around a term.
`tests/test_termbase` (27), and `tests/test_i18n` (37) runs the join, fragment
and parameter checks over the tree. `tests/_webtext.py` now puts English back
for a plural (the form chosen when it runs) and for an ID chosen by a ternary.
Full suite: 14 of 167 red, each failing the same way on a worktree of the
commit before (the 13 of 88b, and `modeldb_header`, which reads a mod file
with a hand edit in it).

**88d onward - one language per phase.** Split on 2026-10-01 on the user's
word ("split apart the next phases into different languages so that i can
safely do one at a time and start with one language"). Each phase is one
catalogue, about 8,000 strings and 60,000 English words, and stands alone:
stopping after any of them leaves a working toolkit with one more language in
it, and nothing in a later phase depends on an earlier one's words. The
order puts the one that tests the layout hardest first, and keeps the CJK
groundwork and the right-to-left layout in their own first phases, so a
translation phase is only ever translation.

**How a language is done safely**, set up in 88d and used by every phase
after it:

- **Work in progress is never offered.** Settings offers a locale as soon as
  `web/i18n/<tag>.json` exists (`i18n.available`), and `web/` ships whole,
  so a catalogue is built in `dev/i18n/<tag>.json`, which never ships and
  nothing serves, and moved to `web/i18n/<tag>.json` only when the checker
  passes on it whole. A half
  translated language never reaches a user, and a session that stops in the
  middle leaves nothing broken.
- **Resumable by namespace.** `dev/checks/i18n_todo.py <tag>` lists, for one
  language, the IDs still missing, the ones whose English changed since they
  were translated (`dev/i18n/<tag>.source.json` keeps a hash of the English
  each string was made from, out of the catalogue the page loads whole), and any the English no longer has, grouped by
  namespace (`map.`, `transfer.`, `eng.buildings.`...). A language is written
  a namespace at a time, so a session ends at a namespace boundary and the
  next one starts from the list. The same report is what keeps a finished
  language current after later phases add or reword text.
- **Never the whole catalogue in context.** A batch is the report's slice of
  `en.json` and the termbase's column for that language, and only the new
  strings come back.
- **Draft until reviewed.** Every language lands as `draft` in the picker
  (the termbase it leans on is a model's draft); a native speaker who mods
  the game reading it is what makes it `reviewed`.

**88d - German, and the workflow.** `i18n_todo.py`, the `dev/i18n/` work
catalogue and its promotion step, the source hashes, a style guide per
language (`dev/i18n/de.md`), and the German catalogue. German is
first because it is the longest of the sixteen (often 30% past English), so
it sets the layout: panels, toolbar and tabs wrap or truncate with a
tooltip, never clip. Done when: the checker passes on `de`, `i18n_todo.py de`
lists nothing, every screen is looked at in German at desktop width and
375 px with nothing clipped or overlapping, and a reworded English string
shows as stale in the report.

*Done 2026-10-01.* **The workflow.** `dev/checks/i18n_todo.py <tag>` reports
missing, stale and extra IDs by namespace; `--batch` writes the next strings
with the termbase renderings they use, `--merge` holds each string to the
checker on its own and merges only those that pass (under a lock, so several
batches go in at once), and `--promote` checks the whole catalogue and moves
it from `dev/i18n/` to `web/i18n/`, after which a merge writes there. The
English each string was made from is hashed in `dev/i18n/<tag>.source.json`;
a reworded English string shows as stale (checked). `dev/i18n/de.md` is
German's style guide (Sie, infinitive buttons, „…“, the terms that need
care) and holds the review notes: every `_exempt` taken, with why, and every
coined word. **German**: 8,112 strings, 0 problems, written in nine batches
(148 by hand to set the voice, the rest by helpers held to the guide and the
checker), offered in Settings as *Deutsch (German) - Entwurf*.

**What translating turned up**, fixed on the way: eight sites still made an
English plural in code (`'y':'ies'`, `' is'`/`'s are'`), now `ttN` plurals
that `i18n_joins.py` catches; eight HTML comments 88b had moved into the
catalogue as text are comments again, and both scanners pass over comments;
the checker read `<code>&lt;key&gt;</code>` two ways at once (no translation
could pass) and refused English's explicit `zero` form in other languages;
a stem may list alternatives for a vowel change (`stadt|städt`). The German
termbase column: ancillary is *Gefolge* and turn *Runde* as in the German
game, tier *Ausbaustufe*; shield, gate, ground types, sprite sheet, heights
map, UV map and checkbox now match their whole term, not the bare common
word that also means something else here.

**The layout.** Every module measured for text clipped by a box that hides
overflow, in German at the pane's desktop width and at 375 px: none from the
translation (the cards' clipped names are the mod's own unit names, as in
English). One squeeze at 375 px, the Buildings view toggle, fixed with
`flex:none`; the page never scrolls sideways. The Settings dialog read at
375 px.

**Left for a native speaker**: the review notes in `dev/i18n/de.md`, the
coined words there (*Gegenstück*, *Schmiede*, *Befund*, *Zuruf*...), and the
`{noun}s` strings, which take an English word from the code and are worded
around it. About 40 strings stay English on purpose: the unit file's own
syntax (field orders, keyword values) as the file spells it.

**88e to 88n - the other European and Cyrillic languages, one each:** 88e
French `fr`, 88f Spanish `es`, 88g Italian `it`, 88h Portuguese (Brazil)
`pt-BR`, 88i Polish `pl`, 88j Czech `cs`, 88k Hungarian `hu`, 88l Turkish
`tr`, 88m Russian `ru`, 88n Ukrainian `uk`. **88g, 88h, 88j to 88l and 88n
are postponed indefinitely** (2026-10-01, see the schedule). Each is the catalogue only,
through 88d's workflow. Polish, Czech, Russian and Ukrainian carry three or
four plural forms each, and the checker holds every `ttN` string to them.
Done when, for each: the checker passes, the report is empty, and Home,
Settings, Transfer and the map are walked in it at desktop width.

**88o - Simplified Chinese, and the CJK groundwork.** The `zh-Hans`
catalogue, plus what all four CJK languages share: a font fallback stack of
Windows system fonts per language (Microsoft YaHei, Microsoft JhengHei, Yu
Gothic UI, Malgun Gothic), line breaking set for CJK, and no synthetic
italics or letter spacing on CJK text. Done when: the checker passes, and
every screen renders with no missing-glyph boxes and no line broken inside a
word.

**88p to 88r - the other CJK languages, one each** (*88q and 88r postponed
indefinitely, 2026-10-01*): 88p Chinese
(Traditional) `zh-Hant`, 88q Japanese `ja` (with `line-break: strict`), 88r
Korean `ko`. Done when, for each: the checker passes, the report is empty,
and the screens show no missing-glyph boxes.

**88s - the right-to-left layout, no translation.** *Postponed indefinitely
with Arabic (2026-10-01).* Done under the `ar-XB`
pseudo-locale (English mirrored), so the layout work is separate from any
Arabic words: `index.html` and the modules moved to CSS logical properties
(`margin-inline-start`, `inset-inline-end`, `text-align: start`), panels and
toolbars mirrored. What must **not** mirror stays left-to-right: the campaign
map, the 3D viewer and every canvas, Code View's raw pane, file paths,
coordinates and code names. Done when: every screen is walked in `ar-XB`, and
on the map a click, the tile pin and a drag land on the same tile as in
English.

**88t - Arabic.** *Postponed indefinitely (2026-10-01).* The `ar` catalogue, with its six plural forms, on 88s's
layout. Done when: the checker passes, the report is empty, and every screen
is walked in Arabic.

# Phase 89 - four reports from users, scheduled 2026-09-26

**Passed on by the user on 2026-09-26**, from users of the toolkit, with "add
these into the roadmap at the end". Two suggestions, one bug report against
beta 2026-09-25, and one report on the real-world map. Unrated. 89a and 89b
are not map work and go on both lines; 89c and 89d are map work and go on the
beta.

## What was reported

1. *A button for creating new resources*, like the one the Religions tab
   already has.
2. *Remove the warning in Minor Files > Resources*: with **Runs on M2EX - no
   engine limits** ticked, a 29th resource (`citrus`) is flagged on line 149
   as "not one of the 28 resources the engine knows - the line is read and then
   ignored", yet in the game it shows and it trades.
3. *A watchtower's line of sight drawn on the map* when one is placed, with a
   switch to show or hide it. Two looks were sent: a filled, see-through disc
   that tints the tiles it covers, and an outline circle only.
4. *The real-world map*, from someone who built a campaign on it: renaming a
   region takes a long time on a map with many provinces; after painting a
   province and setting its capital they could not go back to painting it, and
   did not find how to redraw a province at all; and they still need a way to
   get the correct province names.

## The pieces

**89a - the resource list is open on M2EX (the bug, 2).** Resources are
edit-only today on a stated decision (`minorfiles.py`, `ACTIONS` and
`REFUSED`): "the engine's list is closed", so a 29th name is a line nothing
reads. That was measured on mods that do not run M2EX, and the report shows it
is not true under M2EX. Every place that holds a name against
`KNOWN_RESOURCES` asks `modflags.is_m2ex(mod)` first, the way the faction
limit already does (`factions.py`, `factionclone.py`):

- the `unknown-resource` finding in `minorfiles.py` is not raised on an M2EX
  mod;
- the row's `known` flag, and the "not an engine resource" note it drives in
  `minorfiles.js`, treat every declared name as known;
- the map's resource name box (`stratobj.resource_names`) offers the file's
  own names as it already does, and is checked to not fall back to the 28.

What M2EX's own ceiling is, if it has one, is found out, not assumed: the
finding becomes "resource N of M2EX's M" if there is a number, and nothing if
there is not. On a mod without M2EX the warning stays exactly as it is, since
there it is still true. Done when: a 29th resource on an M2EX mod shows no
finding and no note, the same file with the flag off shows both, and the
suite covers both.

**89b - a new resource (the suggestion, 1).** Built on 89a: `add` joins
`resources` in `ACTIONS` **only on an M2EX mod**. Without the flag the button
is not offered and `REFUSED` says why, as today. The button is the Religions
tab's (`+ New ...` in the list, `mfNew`), and a copy of the open resource
through the existing clone (`mfClone`), since a resource is a model, an icon
and a trade value that are usually taken from one that works. A new resource
brings:

- its record in `descr_sm_resources.txt` (name, trade value, model, icon, the
  mine flag);
- its shown name in `text/strat.txt`, with the missing-key rule the Religions
  tab already follows;
- its icon, copied from a picked `.tga` or from the resource it was cloned
  from, the way a new religion's pip is.

It is then placed on the map with 22b's resource tool, which must offer the
new name. Deleting a resource stays refused on every mod, for the reason
`REFUSED` gives (`descr_regions.txt` places resources by name). Done when: a
resource made in the tab, placed on the map and saved loads in the game on an
M2EX mod, and the tab offers no add on one without it.

*89a and 89b done 2026-09-30, uncut; the in-game check waits on someone with
M2EX.* **M2EX's ceiling, found out:** its release notes say trade goods "are no
longer a hardcoded list", are "fully data-driven from descr_sm_resources.txt",
and "you can add as many new ones as you want". A new one is named by
`SMT_RESOURCE_<NAME>` in `text/strat.txt` and `TMT_<NAME>_TOOLTIP` in
`text/tooltips.txt` (`localised_name` still overrides). With no number given,
nothing is counted: on a mod marked as running on M2EX, the
`unknown-resource` finding is not raised and every row is `known`
(`minorfiles.is_m2ex`). The same file with the flag off gets the vanilla
warning as before, and `REFUSED` now says the flag opens the list.
`actions_for` / `refused_for` replace the fixed `ACTIONS` / `REFUSED` lookups:
on M2EX, resources are `edit` and `add`, and delete stays refused, with its
reason. The map's resource box already offers the file's own names, and falls
back to the 28 only when a mod has no `descr_sm_resources.txt`.

A new resource, from **+ New resource** or **Clone**, brings:

- its record, laid out the way the file is. `flatrecord.new_record` now copies
  a neighbouring record's indent and value column. It had written every new
  rebel faction and resource indented with a space before the value, and no
  real file does that.
- its name as a new key at the end of `strat.txt`. This is the one `strat.txt`
  write the tool makes. It is only a key the file lacks, and it goes after
  every other key, so no entry moves. Every installed mod's compiled
  `strat.txt.strings.bin` and `tooltips.txt.strings.bin` is read by position
  (style 1, 1307 and 382 entries), so the tool can't rebuild it. It is backed
  up and removed instead, and the game builds it again from the text. The
  name, if none is typed, is the resource's own in words (`dried_fish` → "Dried
  Fish"), never its key. A mod with only the compiled file gets a warning and
  no name. An existing resource's name is still the Strings module's.
- its tooltip in `tooltips.txt`, the same way, defaulting to the name.
- its icon, copied from the resource picked in *Icon from* (a clone picks its
  donor) to `data/ui/resources/resource_<name>.tga`. When the donor's icon is
  not a loose file (it is in the packs), the new resource uses the donor's path
  instead, which draws, and nothing is copied. The model is the donor's. There
  is no "pick a .tga from disk": a new religion's pip has none either.

One save, one Undo. `test_minorfiles` 89a/89b (19): the flag off and on, the
refusal, a new resource planned and applied with its icon, both keys and both
caches, the layout, the pack-held icon, and Undo byte for byte. The page was
checked against Third_Age_Reforged with the flag switched on for the check and
off again after (a clone of `amber` plans the icon copy and the file's own
layout). Nothing was written to the mod.

**89c - a watchtower's line of sight (the suggestion, 3).** First the number:
how far a watchtower sees, in tiles, and whether a mod file sets it or the
engine does. It is found in a file or measured in the game, and recorded with
where it came from, never guessed; if it depends on something (the culture's
tower, the owner's traits) that is recorded too. Then the drawing, on the
markers layer 17d built: every watchtower gets its radius, shown as either
look from the report (**filled** tints the covered tiles, **outline** draws
only the circle), picked in the layer's options, with a switch in the layer
list and a number key like the other layers. It is on while a watchtower is
being placed or dragged (22a), so the spot can be chosen by what it covers,
and it follows the drag. Done when: both looks draw at the right size against
a tower measured in the game, the switch hides them, and the radius moves with
a dragged tower.

*89c done 2026-09-30, uncut; one step is left, the in-game measurement.*
**The number: 10 tiles**, the engine's own, the same for every tower. No file
sets it: the installed mods were searched, and `descr_campaign_db.xml` holds
only `spy_watchtower_modifier`, which is a spy's odds, not a range. A tower has
no culture's or owner's figure either. What it covers is the tiles within 10 of
the tower: a disc of 317 tiles, not the 441 of a 21 × 21 square. In game a hill
or a forest can hide part of it, so the drawing shows the furthest a tower
reaches, and its hint says so. **Still to do:** confirm the 10 against a tower
in the game.

Built in `campmark.js` on 17d's markers layer (`cmkSight*`), drawn from
`cmapOverlay` under the markers. **Filled** tints each covered tile (one
rectangle per row of the disc, so 21 per tower). **Outline** draws one circle,
10.5 tiles out from the tower's tile centre. The switch and the look are in the
markers panel under the categories, and both are remembered in Settings
(`map_sight`). The switch starts off. The key is **`w`**, a letter like the
other view switches because the ten digits are the ten image layers. The sight
is drawn whatever the switch says while a watchtower is being placed (under the
pointer, whichever of the create buttons armed the pin) or dragged (where it is
now, not where it was). The hover repaints the whole map while placing, since
the disc is not the one cell a hover redraws. Measured on Divide and Conquer's
295 towers, all drawn: about 2 ms a frame. `tests/test_mapsight` (20, in Node
on the real `campmark.js`).

**89d - the real-world map report (4).** Three problems and one question, each
reproduced on a map with as many provinces as the reporter's before anything
is changed:

- **Renaming a region is slow.** 19b's rename follows the name through
  twenty-four files. Time it on a large real-world campaign, find where the
  time goes (re-reading files per region, re-drawing the map, re-running the
  checks), and fix that. Done when: a rename on that map finishes in a
  measured, stated time, and the numbers before and after are recorded here.
- **Painting stops after the capital is set.** Reproduce the order the report
  gives: paint a province, set its capital, go back to the brush. Find what
  holds the brush (a mode left on, a pin not released, a guard on a province
  that now has a settlement) and fix it. Done when: paint, set capital, paint
  again works in that order on a real-world map, with a test for it.
- **How to redraw a province was not found.** Whatever the painting fix turns out to be, the way
  to repaint a province's tiles is made visible where someone looking for it
  would look: in the region's own panel, not only on the toolbar.
- **The correct province names.** 87e names each province after its city
  (`<City>_Province`, with the campaign's name in front when the key is
  taken). Ask the reporter what "correct" means for their map: real
  administrative regions from the same OpenStreetMap data (boundaries at a
  chosen `admin_level`), historical names, or only an easier way to rename
  many at once. Build that answer, and nothing until it is known.

*89d done 2026-09-30 but for the question, uncut.* No real-world campaign is
installed here, so the first two were measured and reproduced on the two that
are.

- **Renaming a region is slow: the time was not in the provinces.** On a fresh
  load of the mod, the first rename plan took **11.3 s** on DaC and 6.4 s on
  Reforged, and the second 0.4 s. Of the first, 6.2 s was
  `luascan.mod_files`, the one walk of the mod folder that also feeds the
  mentions scan, and 4.7 s of that was a `stat` per entry (49,544 on DaC),
  from `Path.is_dir()`. Every save invalidates the mod, so every rename paid it
  again. The walk is now `os.scandir`, whose entries already know whether they
  are a folder: DaC 5.6 s to 0.5 s, Reforged 3.1 s to 0.4 s, and the same lists
  byte for byte on both. **After:** a rename on a copy of DaC's campaign files
  plans in 1.0 s the first time (0.4 s after) and applies in 0.1 s. The walk
  grows with the mod's files and not with its provinces, so a real-world map
  with more provinces pays about the same. The reporter's own number is still
  to hear.
- **Painting stops after the capital is set: the unsaved painting was thrown
  away.** Reproduced on a scratch copy of Reforged, through the page's own
  calls: a stroke onto Pinnath-Gelin, then Anfalas made its faction's capital
  in the Settlement panel. The save invalidated the mod, and the registry read
  the map again. The paint session belonged to the old map object, so the next
  request dropped it: the stroke was gone, with only a toast
  ("the map was re-read from disk"), and the side panel was left on the
  Province tab. Now `PaintSession.rebase` carries a session onto the map read
  again, and it does so where the map is read (`Registry.campaign_map`), so the
  page's own reload after the save already shows the strokes. The one
  condition is that every layer it holds pixels for is still, on disk, the
  file it read (size and mtime taken when the layer was first painted), so a
  layer saved from Photoshop under it still ends the session, and says so. A
  session with nothing in it no longer reports a reset either. The same run
  after the fix: the stroke survives the save, one Undo away, and the next
  stroke is the second.
- **How to redraw a province was not found:** the region's own panel now has
  **Paint its tiles** beside *Change colour…*. It opens the Paint tab's brush
  with that province as its colour, armed, and says Save is on the Paint tab.
- **The correct province names: asked, not built.** The question for the
  reporter stands as written above: real administrative regions from
  OpenStreetMap at a chosen `admin_level`, historical names, or an easier way
  to rename many at once.

`test_campaint` 89d (5): a re-read keeps the session and its pixels, Undo is
byte for byte, a layer changed on disk still resets, an empty session follows
silently. The walk: `test_eop_and_lua`, `test_cleaner`,
`test_unit_rename_refs`, `test_renames` green.

# Phase 90 - a layout that fits the window at every interface size, scheduled 2026-09-26

**Reported by a user on 2026-09-26**, passed on by the user: "UI scaling seems
to work but the elements are not responsive. Can you make the ui properly
responsive". Unrated, both lines (every screen changes). The screenshot is
Minor Files > Ancillaries on a 1600 px window: the tab strip breaks into
two-line tabs of uneven width with the file path squeezed in after the last
one, **+ New ancillary** and **Port from another mod** are bars the whole width
of the page with their labels pushed to the right, and the page scrolls
sideways.

**Why the size setting and the layout disagree.** Settings' interface size
(`core.js`, `uiScaleApply`) draws the page with CSS `zoom` on the root and
corrects the `vh`/`vw` units by `--uiz`. The `@media (max-width: ...)`
breakpoints in `index.html` (about a dozen, each written for one screen) are
**not** corrected: they measure the window, not the zoomed page. At 125% on a
1280 px window the page lays out in 1024 px of room while every breakpoint
still sees 1280, and at 60% the reverse. So a breakpoint fires at the wrong
size, or never, depending on the setting. This is checked first, in the
browser, before it is treated as the cause.

**90a - measured.** Every screen at the three window widths people use (1280,
1600, 1920) times the interface sizes (60, 80, 100, 125%), plus 375 px at
100%: horizontal page scroll, clipped or overlapping controls, and a tab strip
or toolbar that breaks badly. A list of what fails where, recorded here.

**90b - breakpoints that see the page.** The layout decides on the room the
page actually has. Either container queries (measured in the zoomed page, so
the interface size is taken into account by construction) or one class set on
`<html>` from `innerWidth / zoom`, whichever fixes the most screens with the
least change; chosen in 90a, not in advance. Done when: each existing
breakpoint fires at the same *page* width at 60% and 125%.

**90c - the shared pieces, fixed once.**

- **Tab strips** (Minor Files, the editors' sub-tabs) are one row that
  scrolls sideways inside itself, with the file path on its own line under
  it, rather than wrapping into tabs of different heights.
- **Action buttons** such as *+ New ...* and *Port from another mod* are the
  size of their label, in a row, and not a full-width bar with right-aligned
  text.
- **List and form panes** (the list, the record, Code View beside it) go from
  side by side to stacked at one shared width, not one per screen.
- **No horizontal page scroll** anywhere: anything wide (a table, a path, a
  canvas) scrolls inside its own box.

Done when: 90a's list is walked again at every size and width and nothing
is left on it, with a screenshot of Minor Files at 60% and 125% to show it.

*Done 2026-09-30, uncut.* **90a, measured.** A script in the page opened
each of the 30 screens (the campaign map apart, checked on its own) at 1280,
1600 and 1920 px times 60, 80, 100 and 125%, and at 375 px at 100%. It
recorded how far `#main` or the page scrolls sideways, a record pane squeezed
under 200 px, and a tab strip whose tabs are not all one height. The
cause was checked first, in the browser: at 125% on a 1280 px window the body
lays out in 1024 px while `(max-width:1100px)` does not match. What failed:

- **The Minor Files tab strip, on all 16 screens under it.** Nineteen tabs in
  a row that does not wrap, shrunk into tabs one, two and three lines tall at
  every size, even 60%. Past its minimum width it pushed `#main` sideways:
  at 1280 px by 46-209 px at 80%, 359-519 at 100% and 607-767 at 125%; at
  1600 px by 39-199 at 100% and 351-511 at 125%; at 1920 px by 95-255 at 125%;
  at 375 px by about 1,300. Most of the report is this one strip: with the
  page scrolling, the list column is laid out wider than 280 px, its buttons
  are bars with the label pushed right, and at 375 px the record pane is 0
  to 49 px wide.
- At 1280 px and 125%: two tables wider than their pane (Banners, Agents and
  generals, `.smxtab`, 768 and 795 px).
- At 375 px, besides the strip: the unit editor, Unit Transfer and Buildings
  (the 210 px filter column beside cards 165 px wide, Buildings' faction header
  not wrapping its buttons), Unit Sounds (a six-column grid, 468 px over), My
  changes (a long path in `<code>`, 368 over), Hero abilities (a long `<code>`,
  24 over).

**90b, chosen: container queries.** `body{container:page/inline-size}`, and
all twelve `@media (max-width)` rules became `@container page (max-width)`.
It is one declaration and a search-and-replace, where a class set from
`innerWidth / zoom` would need every rule rewritten and a script kept in step.
A container query measures the body as laid out, zoom included. Proven with a
probe `.edsplit` (breakpoint 1100): at 1280 px it now fires at 125% (page 1024)
and not at 100%, 80% or 60%. At a 1000 px window it fires at 100% and not at
60% (page 1667), where the media query had fired at both.

**90c, the shared pieces.** The tab strip is one row that scrolls in itself
(`overflow-x:auto`, tabs `flex:0 0 auto; white-space:nowrap`), with the open
tab scrolled into view (`mfTabsReveal`), and the file path is a line of its
own under it (`.mfpath`). **+ New ...** and **Port from another mod** sit in a
`.trnewrow`, the size of their labels (Traits, Ancillaries, Guilds, Minor
Files). The list and the record stack at one width, 760 px of page, for every
screen built on `.trwrap`. The unit list's filters go above the cards at 600 px.
Nothing wide moves the page: `.smxtab` and `.sndlist` scroll in their own box,
a long `<code>` breaks where it has to, and Buildings' faction header wraps.
**The walk again: nothing is left** at any of the fifteen combinations, and
the campaign map scrolls at none (it stacks at 375 px, its 1000 px rule now
seeing the page). Screenshots: Ancillaries at 1280 px, 125% (the strip one
row with its scrollbar, the path under it, the two buttons in a row) and 60%
(all nineteen tabs in the row). `tests/test_layout` (14) holds the source to
it.

# Phase 91 - a cloned faction's missing faction button, scheduled 2026-09-26

**Reported by a user on 2026-09-26** against the beta: a faction added with
*Add a faction* (a copy of one they already had) works in the game, "it all
works perfectly and took just 15-20 minutes", **except** that the faction
button on the campaign map's settlement bar (circled in their screenshot, left
of the settlement's name plate) is missing for that faction. The screen it
opens still comes up with the hotkey **O** (`faction_button` in
`descr_shortcuts.txt`), so the button's action is there and only its picture
is not. Factions they added by hand never had this. They sent the tutorial
they used by hand (Imperial forum, "Сичевые Свитки", *adding a new faction to
M2TW from scratch*, two posts, from 2014 and 2007) and asked whether the
toolkit does the same thing. Unrated, both lines.

**The comparison with that tutorial.** Its first post lists fourteen places,
the second walks through them with an example (Aragon):

| the tutorial | what *Add a faction* does |
|---|---|
| `descr_sm_factions.txt`, "the main file" | copied from the donor, re-headed; every value kept, `logo_index` and `small_logo_index` included |
| `descr_character.txt` | joins the donor's lists |
| `export_descr_unit.txt` | joins every `ownership` line the donor is in |
| `export_descr_buildings.txt` | joins every `requires factions { }` the donor is in |
| `text/expanded.txt` (+ `.strings.bin`) | the name and the `EMT_*` keys copied; the `.bin` refreshed |
| `descr_names.txt` | the donor's section copied |
| `descr_banners_new.xml` | a row in every banner the donor has one in |
| `descr_offmap_models.txt` | the donor's block copied |
| `descr_lbc_db.txt` | the donor's paragraph copied |
| `descr_model_strat.txt` | every `texture <donor>, ...` line duplicated |
| `descr_sounds_accents.txt` (second post) | joins the donor's accent |
| `menu/symbols` (`fe_buttons_24`, `fe_buttons_48`, `fe_symbols_80`, `fe_faction_units`) | found by the donor's name and copied under the new one, with `ui/faction_symbols`, captain cards, unit cards and banners |
| `descr_strat.txt` | **not done, on purpose**, and the plan says so: two factions cannot start in one settlement |
| `descr_win_conditions.txt` | **reported, not copied** (`REVIEW_FILES`) |
| `campaign_descriptions.txt` (+ `.strings.bin`) | **not done** |
| delete `map.rwm` | not needed by the clone itself, since it does not change `descr_strat.txt` or the map |

The toolkit also does two the tutorial does not name:
`battle_models.modeldb` (the donor's skins) and `descr_faction_standing.txt`.
**So the method is the same one**, a copy of an existing faction under a new
name, and the gaps are the three files the campaign needs, not the button.

**Where the button's picture comes from.** The tutorial names it: `logo_index`
is the identifier of "the strat icon, the shields", and `small_logo_index` the
small one. The value is a sprite **name** in the interface's sprite sheets
(`strategy.sd` for `logo_index`, `shared.sd` for the small one, under each
culture's `ui/` folder), not a file the clone could copy. If the name is not
in the sheet the engine is reading, the button has no picture and nothing to
click, which is what the screenshot shows. A clone keeps the donor's value,
which is in the donor's sheet, so a plain clone should show the donor's
shield. Something differs for this faction, and 91a finds what.

**91a - the reporter's files.** Ask for the new faction's and the donor's
`descr_sm_factions.txt` blocks, and whether the new faction's `logo_index`,
`small_logo_index` or `culture` was changed after the copy (the Factions
editor offers those as free fields), and whether the mod runs M2EX or another
engine patch. The hypotheses,
in order: a `logo_index` value changed to a name the sheet does not have (the
tutorial's own `FACTION_LOGO_ARAGON` is that kind of name, and the tutorial
never says how to add it to the sheet); a culture changed so the sheet read is
a different culture's; the faction's position in the list against a patched
engine's limit. Done when: the cause is known and written here.

**91a, found 2026-09-27, from the reporter's two sheets.** The user's friend
sent the mod's `data/ui/strategy.sd` and `data/ui/shared.sd` (a Gothic mod,
Khorinis and the clans), saying these were the files that "didn't generate
right" because the new factions' entries were not in them. What they hold:

- **Both sheets are sound.** Version 6, read to the last byte (317 sprites on
  6 pages, 351 on 4); no name twice; all 36 shields and 42 small shields have
  a non-empty hit mask (the button is a shaped one, clickable only where the
  mask is set). Twelve factions were added by hand, on `stratpage_06.tga` and
  `sharedpage_02.tga`, each as `FACTION_LOGO_<NAME>` and
  `SMALL_FACTION_LOGO_<NAME>`.
- **There is one sheet of each for every culture.** The sheet is
  `data/ui/strategy.sd`; only its `.tga` pages are per culture
  (`ui/<culture>/interface/`). So the culture hypothesis is out: a culture
  change moves which pages are drawn from, not which names exist.
- **The value is a name, resolved to a position when the roster loads.** A
  name not in the sheet does not stop the game; sprite 0 is drawn in the
  shield's place (in this sheet `BUILD_BUTTON_IMAGE`, in DaC and Reforged
  some other button too), never the faction's shield.
- **The clone never writes a name that is not in the sheet.** It copies the
  donor's `logo_index` and `small_logo_index` as they are, so a plain clone
  shows the donor's shield. Nothing in the toolkit wrote a logo name at all.

**So the cause is the first hypothesis**: the new factions' records name
shields the sheets do not have, most likely `FACTION_LOGO_<new name>` typed
into the Factions editor's free box after the clone, as the tutorial does,
expecting the entry to exist. The friend's own words fit it exactly. Their
`descr_sm_factions.txt` blocks for the new factions would confirm the value;
91b's check now names it on screen either way.

**91b - the fix, and a check so it cannot happen quietly.** Whatever 91a
finds is fixed where it lives (the clone, the Factions editor or the
documentation). Then the check: `logo_index` and `small_logo_index` are held
against the sprite names in the sheets the faction's culture uses, in *Is
this faction complete* (Phase 21), in the Factions editor (a name not in the
sheet is a finding, and the box offers only names that are), and in Health.
Reading sprite names out of an `.sd` is new: the interface skins are the
unrated row in *Unrated, and the rating is not the reason*, and this needs
only the names, not an editor for them. Done when: a faction whose logo name
is not in its sheet is reported in all three places, and the reporter's
faction shows its button.

**91b, built 2026-09-27, uncut; the in-game check waits on the reporter.**
`unittransfer/spritesheet.py` reads a sheet's pages and sprite names and
writes one thing, `add_alias`: another name for a picture the sheet already
has, appended so every sprite keeps its position (a roster using numbers keeps
its meaning). Every sheet in both installed mods and the reporter's two read
to their last byte.

- **The check**, only where the mod ships the sheet loose (a packed one is no
  evidence): `factions.check_file` reports `logo-not-in-sheet` with the line
  (a name not there, a name that differs only in case, a number past the end).
  That is the Factions editor's finding and Health's, once. The audit (Phase 21)
  has a **Faction shield** row, a gap. Baseline: all 61 factions in DaC and
  Reforged are clean.
- **The editor's box** offers only the shields in the sheet when the mod ships
  it, and a value not in it reads "(not in the sheet - no shield)".
- **The repair**: the audit's Copy from on that row adds the faction's own
  name to the sheet, drawn as the template's shield, and leaves the roster
  alone. One undo takes it back. This is what fixes the reporter's factions.
- **The clone** now gives a new faction shields of its own name,
  `FACTION_LOGO_<NEW>` and `SMALL_FACTION_LOGO_<NEW>`, drawn as the donor's
  until someone paints them, and points its record at them. A name already in
  the sheet is used as it is (someone drew it); packed sheets keep the donor's
  value, as before. A batch lands every row's names in one sheet.
- `tests/test_spritesheet` (44). Painting a new shield into a page, and its
  hit mask, is still the modder's job; the name is now where they expect it.

**91c - the three campaign files the clone leaves to the modder.** With the
tutorial side by side, the plan already names `descr_strat.txt`; it also
names `descr_win_conditions.txt` and `campaign_descriptions.txt` as things
still to do before the faction is playable, with a link to the editors that
write them (the campaign descriptions editor from 18a). Whether the clone
should copy the donor's `descr_win_conditions.txt` block and
`campaign_descriptions` keys outright, like it copies `expanded.txt`, is
decided here: both are per-faction blocks with no settlement in them, so the
reason `descr_strat.txt` is not copied does not apply to them.

*91c done 2026-09-30, uncut.* **Decided: both are copied, and not blindly.**
Measured first on the two installed mods. The premise above is half right:
`descr_win_conditions.txt` has no settlement in it, but it does name places.
`hold_regions` lists the donor's provinces (Reforged's `sicily` holds Anorien,
Umbar and five more), and `outlive` names other factions. So
`clone_win_conditions` copies the donor's block under the new name in every
campaign that has the file (Reforged's imperial and Fellowship, each its own),
with **both `hold_regions` lines left empty**, the form Divide and Conquer
writes for all its factions. `take_regions`, `outlive` and `short_campaign`
are copied as they are. `clone_campaign_descriptions` adds
`{<CAMPAIGN>_<NEW>_TITLE}` and `_DESCR` for every campaign that has the
donor's: the title is the clone's shown name, the description is the donor's
text to start from. The compiled `.strings.bin` is tagged in both mods and is
rebuilt. The plan says what was left:
the provinces to hold, once the faction has a place in `descr_strat.txt`, and
the text to rewrite. `descr_win_conditions.txt` leaves `REVIEW_FILES`.
`descr_strat.txt` stays as it was: not copied, and said so.
`test_factionclone` 91c (17): both cloners on text, the real plan on Reforged,
and an apply on a copy (the compiled title is there, every campaign has the
block, one Undo puts all of it back byte for byte).

# Phase 92 - four things another import tool does that Unit Transfer does not, scheduled 2026-09-28

**Passed on by the user on 2026-09-28**: a friend wrote an import tool of
their own (about 1,500 lines of Python, one window: pick a game, a mod and
the units, Check, Import, Undo) and the user asked what in it is worth having
here. Everything it does, Unit Transfer already does or does better (the dry
run and undo, renames on a clash, relocated assets, sprite sheets, mounts,
projectiles, cards, `strings.bin`, packs read directly, the missing
animations ported by 83), except the four below. Reported on 2026-09-28,
"sounds good" to adding them. Unrated, not map work, both lines. Their code
is not copied: the ideas are.

**92a - an M2EX mod that reads its battle models as text.** The friend's
tool is written for M2EX games that read their battle models from
`data/descr_model_battle.txt` instead of `unit_models/battle_models.modeldb`,
switched on by `model_battle_source text` in `data/descr_caps_ex.txt`. Unit
Transfer only ever writes the `.modeldb`, and the M2EX flag
(`modflags.is_m2ex`) only lifts ceilings and lets effects travel. On such a
mod a transfer writes models the game never reads. Neither installed mod runs
this way, so **measured before a line is written**: a real
`descr_caps_ex.txt` and `descr_model_battle.txt` are asked for (the friend
has them), and what the file holds is recorded here: the keys (`type`,
`scale`, `skeleton`, `skeleton_<mount>`, `skeleton_attachment_primary` and
`_secondary`, `mesh <path>, <distance>`, `texture`, `texture_attachments`,
`torch`), whether a mesh distance is the square root of the `.modeldb`'s
figure, whether the first entry is special, comments and encoding. Then:

- a mod is known to read text models from its `descr_caps_ex.txt`, not from
  the M2EX tick alone, and says so on its Home card;
- a reader and writer for the text file beside `modeldb.py`, answering the
  same questions a `ModelEntry` does (names, skeletons, files, texture
  records), so transfer, the 79 skeleton check and the Models viewer read
  either;
- transfer, as source or destination, reads and writes whichever file the mod
  reads, and a transfer between one of each converts the entry;
- Health warns when a mod reads text models and has a `.modeldb` that has
  moved on since (or the other way round), since one of the two is dead.

Done when: a unit transferred into a text-model M2EX mod loads in the game
with its own model, one taken out of such a mod lands in a `.modeldb` mod,
and the suite covers both directions against the sample files.

*92a done 2026-09-30, uncut; not yet loaded in game.* **Measured** on the
M2EX install the user pointed to (`EUREXV1/M2EX`): the base game's
`data/descr_caps_ex.txt` says `model_battle_source text` ("modeldb ... default
for mods"; each of its four campaigns has its own caps file), and its
`descr_model_battle.txt` is 701 models, 11,250 CRLF lines, "generated from
battle_models.modelDB". The M2EX build of EUR installed in the mods folder
still reads its `.modeldb` (no caps file). What the file holds, per model:
`type`, `scale` (7 of 701; 1 when absent), `skeleton <pri>, <sec>` with a
`skeleton_attachment_primary` / `_secondary` line per weapon skeleton, the same
as `skeleton_horse`, `_camel`, `_elephant` for the other mount types,
`mesh <path>, <distance>`, `texture <faction>, <diff>, <norm>, <sprite>`,
`texture_attachments <faction>, <diff>, <norm>`, `torch <bone>, <6 offsets>`
(677 of 701). **A distance is the square root of the `.modeldb`'s**: Tsardoms
holds 953 of its 1,015 as perfect squares (6400, 121, 900) and the text's are
80, 11, 30; a non-square (1200) is rounded, the one thing a trip through text
changes. The first skeleton block is written `skeleton` whatever its mount
type, so going back to a `.modeldb` its type comes from the units that wear the
model (`horse` for a mounted unit, else `none`). No first entry is special.

Built: `unittransfer/modeltext.py` reads the file, writes an entry as text and
as a `.modeldb` entry, and `Mod.text_models` (the mod's own caps file) makes
`Mod.modeldb` read the text, so transfer, the 79 skeleton check and the Models
viewer read either. Transfer writes whichever file the destination reads,
appending in its own line endings, and a transfer between one of each converts
the entry. The Home card says **Battle models from descr_model_battle.txt**,
and Health's **Battle models: which file the game reads** warns when the file
the game does not read was changed after the one it does. Found on the way:
Reforged's `.modeldb` holds a weapon skeleton name with a newline inside its
length-prefixed string, which a line of text cannot, so every value is
stripped as it is written. **Not covered:** the Models editor's own saves still
write the `.modeldb`, and on a text-model mod they should be refused or moved
to the text; that is left for when such a mod is installed here.
`tests/test_modeltext` (23): all 701 models round trip both ways, the caps
switch, the Health rule, and a transfer in each direction (Tsardoms into a
text copy of Reforged, then out of it into a copy of Tsardoms), with Undo.

**92b - recruitment set up by the transfer.** Today a transferred unit is
recruitable nowhere until someone adds it in the Recruitment tab. The
friend's tool does it in the same step, behind a tick (*Let the faction
recruit them*), and so should this, through the Recruitment tab's own writer
(`buildings.py`, the plan and apply road), never a second one:

- **a renamed copy of a unit the destination already has** (the collision
  rename) gets a copy of every `recruit_pool` line the original has there
  that the destination faction can use, its `factions { }` narrowed to the
  destination faction;
- **a new unit** goes into the building and level that recruited it in the
  source mod, for the source faction, when the destination has a building
  and level of that name; the plan lists each one;
- anything left over is "not recruitable" in the report, with a link to the
  unit's Recruitment tab, as today.

Done when: the plan shows every pool it will add, the unit trains there in
the game, one Undo takes the pools back with the transfer, and the suite
covers both kinds and the leftover.

*92b done 2026-09-30, uncut; not seen in game.* A **Recruitment** box on the
transfer page, *Let the faction recruit them* (`set_recruitment`, off by
default). `transfer._plan_recruitment` works on the final block's owners:

- **a renamed copy** (the unit type is the destination's own, written under a
  new one) gets a copy of each of the original's pools in the destination
  whose `factions { }` names an owner, the list held to those owners
  (`_narrow_factions`);
- **a new unit** gets each pool that recruits it in the source, in the
  destination's line and level of the same name, its factions list held to the
  owners (or made of them when the source's names none of them), and a clause
  with no list is given one.

The pools go through `buildings.plan_edit`, the Recruitment tab's own writer,
and the EDB text it plans is written in the transfer's job, so one Undo takes
both back. The box lists each pool (line, level, clause), and a unit left with
none says **NOT RECRUITABLE** and why. Not in replace or models-only mode.
`tests/test_transfer_recruit` (13): the narrowing rule, Reforged's Gondor
Spearmen as a renamed copy (6 pools, applied, 6 places in the EDB, one Undo
byte for byte), the same unit as a new one into a copy without it (6 pools),
and a Tsardoms unit whose levels Reforged has none of (not recruitable).
**Phase 92 is done**: a, b, c and d.

**92c - one faction's look only.** Transfer copies every texture the model
names, so a DaC unit with a dozen faction skins brings a dozen sets of
`.texture` files for a faction that wears one. The friend's tool copies only
the source faction's and writes it as the destination faction's and as
`default`. Here it is an option on the transfer (*Copy only the skins the
new owners wear*), off by default: the copied entry keeps the texture
records for the factions in its final ownership and `default` (and `slave`
where the unit is a rebel or mercenary), the rest are dropped from the entry
and their files are not copied. That needs a writer that removes a texture
record and lowers the group's count, the opposite of
`modeldb.add_texture_factions`. The plan states the saving in files and MB.
Done when: a DaC unit taken with the option on shows the right skin in the
game for its owner, the copy is measurably smaller, and the entry's counts
agree with its records (the suite reads the result back).

*92c done 2026-09-30, uncut; not seen in game.* The writer already existed:
`modeldb.set_texture_factions` (the model card's faction checklist) keeps
exactly a list of factions in each texture group, clones a record for one it
lacks and rewrites each count. The option is `own_skins_only` (off by default,
a **Skins** box on the transfer page). `transfer._plan_own_skins` gives each
copied entry its final block's owners (`all` left out, `slave` added for a
mercenary or a rebel's unit, `default` kept where an entry has one). It drops
from the copy list the files only the left-out records named, a sprite's
sheets with it, and says how many records, files and MB. Measured on Tsardoms'
*Hungarian Peasants* (32 skins) into a copy of Reforged: 6 owners kept, 104
records across its entries left out, but only 2 files, 0.1 MB, saved, because
Tsardoms points most factions' records at shared textures. A mod with a file
per faction saves far more. `tests/test_transfer_skins` (6): off by default,
the owners only, the saving, and the applied `.modeldb` reading back with
counts that agree and every kept texture copied. **The suites that copy DaC's
files cannot run** until the hand edit in the M2EX EUR's `.modeldb` is fixed
(see Phase 94's note).

**92d - a banner the destination does not have.** A unit whose `banner
faction` names a banner missing from the destination's
`descr_banners_new.xml` (a Hospitaller or Templar banner, say) is copied as
it is today, and Health finds it afterwards. The transfer does it first:
the plan names the banner and offers to port it with 65's banner writer
(`banners.py`) or to swap it for `main_cavalry` or `main_infantry` by the
unit's category, which is what the friend's tool always does. `banner holy`
and `banner unit` get the same treatment. Done when: neither choice leaves a
Health finding on the destination, and the suite covers both.

*92d done 2026-09-30, uncut; not seen in game.* Measured first: between the
two installed mods only one unit carries a banner the other has not got,
Reforged's *Bomb Platforms* (`banner faction main_none`), and Reforged does
not declare `main_none` either. The transfer plan now reads the final block's
`banner` lines against the destination's `descr_banners_new.xml`
(`transfer._plan_banners`), and the transfer page shows a **Banners ... has
not got** box with the choice (`options.banner_mode`):

- **Bring the banner across** (the default): `banners.port_banner` puts the
  source's `<Banner>` at the end of the destination's list of that kind. Its
  rows are cut to the destination's factions, and each faction that will own
  the unit and has no row gets one, copied from the banner's first row. So the
  destination's own check has nothing to say about it: the coverage rule is a
  row for every owner. The loose files it names that the source ships are
  copied with the unit. A banner the source does not declare either (the one
  real case) falls back to the swap, and says why.
- **Use main_cavalry or main_infantry instead** (`banners.swap_for`): a
  faction banner becomes one of those by the unit's category, a holy banner
  becomes `crusade`, and a unit banner's line goes, so the unit carries its
  faction's banner.

Written in the same job as the unit, one Undo. `tests/test_transfer_banners`
(16): the port on text (the list, the rows, the files, no finding afterwards),
the swaps, and the real plan in both modes. **92a is not started**: it waits
on the friend's `descr_caps_ex.txt` and `descr_model_battle.txt`, as written.

**Left out, and why.** Two smaller things in the friend's tool are recorded
so they are not rediscovered: when a skeleton cannot be ported and there is
no base unit to borrow from, it guesses one by trimming words off the name
(`MTW2_Spear_new` to `MTW2_Spear`), and it swaps a missing effect for a close
one (`bolt_impact_ground_set` to `arrow_impact_ground_set`) where this tool
uses the invisible placeholder. Either can be a last fallback here later.
Writing into the base game's own `data` folder, which it also does, is not
taken: the mods folder is there so that is never needed.

# Phase 93 - two reports on getting around, scheduled 2026-09-29

**Reported by the user on 2026-09-29**, with a screenshot of each. Unrated, not
map work, both lines.

**93a - Restart now to apply it comes back without its console.** Settings →
Launcher, *Keep the console window open* ticked, *Restart now to apply it*:
the tool comes back on the same address, but no console window stays open. The
restart road is `restartServer()` (`web/js/transfer.js`) posting
`/api/restart` with `console: true`, `_restart_into` (`unittransfer/server.py`)
and `startup.spawn_server(..., console=True)`. The likely cause, to be
confirmed before it is fixed: a server started by the normal launch is the
detached child, and that child runs on `pythonw.exe` (`startup._pythonw`). So
in the server doing the restart `sys.executable` is already `pythonw.exe`, and
`spawn_server`'s `exe = sys.executable` for the console case hands a new
console to the windowless interpreter, which never shows one or writes
nothing to it. The fix picks the console interpreter (`python.exe` beside
`pythonw.exe`) explicitly, and falls back to the setting being applied at the
next launch, said so in the modal, when there is none. Worth checking on the
way: the replacement's log still reaches the new console (`logutil`'s
`StreamHandler` is bound to `sys.stdout` at setup), and unticking the box and
restarting closes it again. Done when: from a normal launch with the box
ticked, a restart leaves a console showing every request, one without the box
leaves none, and the suite covers the interpreter choice for both starting
points (`python.exe` and `pythonw.exe`).

**93b - a middle click opens the screen in a new tab.** The Home card's
buttons (Unit Editor, Unit Transfer, Buildings, Campaign Map, Models Editor,
Unit Sounds, Minor Files, Raw text, Health, My changes) are `<button
onclick="homeGo(...)">`, so a middle click does nothing and a right click has
no *Open in new tab*. The route already exists: `navUrl(r, mod)` in
`web/js/core.js` builds `/?mod=&go=<mode>`, and the startup code reads it back
for that tab only, without changing the remembered mod. So each of those
buttons becomes a real link to its `navUrl`, looking exactly as it does now,
whose plain left click still runs `homeGo` in place (default prevented) and
whose middle click, Ctrl+click and context menu are the browser's own. The
same treatment for the other places that switch screen by name where it is
cheap: the mode bar at the top and the trail's crumbs. Done when: a middle
click on each Home button opens that screen for that mod in a new tab, the
first tab stays where it was, a left click behaves as before, and a
keyboard user reaches and presses each one as before.

*Phase 93 done 2026-09-30, uncut.* **93a, confirmed by reading and fixed:**
`spawn_server` ran a console restart on `sys.executable`, and in a server from
the normal launch that is `pythonw.exe` (started by `_pythonw`), so the new
console had nothing writing to it. `startup._python_console` now picks
`python.exe` beside `pythonw.exe`. When there is none, the server does not
restart (it would come back exactly as it is) and says `console_later`, and the
page says the console comes at the next launch. `test_startup` covers both
starting points: from `pythonw.exe` the command is `python.exe`, and a
`pythonw.exe` with no `python.exe` beside it has no console interpreter
(76/76). **Not checked here:** a restart from a normal `.bat` launch leaving a
console on screen, which needs the user's launch.

**93b.** The Home card's ten screen buttons, the "Last time you were in"
button and the side menu's items are links to their `navUrl` (the Home ones
carry their card's mod), styled as they were (`a.btn`, `a.navitem`). A plain
left click still runs `homeGo` / `setAppMode` in place with the default
prevented. A middle click, Ctrl+click and the context menu's *Open in new tab*
are the browser's own, and Space presses them as it pressed the buttons
(`navPlain`, `navLinkKey` in `core.js`). The menu's links are re-pointed at
the mod on show each time it opens. The trail's crumbs were links already.
Checked in the page: 30 Home links (`/?mod=Tsardoms-3.0&go=sounds`...), a
plain click on one switched mod and screen in the same page with no load, and
`/?mod=Third_Age_Reforged&go=buildings` opened in a second tab lands on
Reforged's Buildings.

# Phase 94 - a recruitment screen that lags, and its turns, scheduled 2026-09-29

**Passed on by the user on 2026-09-29**, from a user on Tsardoms 3.0, with three
screenshots. One performance report and one suggestion. Unrated, not map work,
both lines.

## What was reported

1. *The Buildings editor is laggy on a level's recruit pools.* A ▲▼ on a pool's
   numbers "takes a while to register" and the next click cannot follow
   straight away; Chrome then shows *These pages aren't responding* for the
   Buildings tab and two Unit Editor tabs, and they have to press **Wait**. The
   level in the screenshots is Tsardoms' Barracks, where the recruitment-limit
   banner counts 40 to 50 pools per faction for 19 to 24 factions. A build
   from the week before is just as slow, and clearing the cache did not help.
2. *The turns beside a replenish rate on the Unit Editor's Recruitment tab.*
   The Buildings editor already prints "= 8.9 turns" beside the rate, but the
   Unit Editor's table of every pool the unit has (Kruje Castle, Barracks 4/5,
   Armoury 5/5...) shows only 0.112, 0.084, 0.125. "I have difficulties
   remembering how many turns 0.084 for example is."

## The pieces

**94a - measure the lag, then remove it.** Not reproduced yet: Tsardoms is
not installed here, so the first step is either the user's mod or the
largest EDB on this machine with a level padded to Tsardoms' size, and a
profile of one ▲ click. The hang takes the Unit Editor tabs down with it
because Chrome runs same-origin tabs in one renderer, so every open tab of the
toolkit freezes while one is busy; that is a symptom, not a second bug. The
suspects, read from the code but not timed, all run on every click and all
cost the size of the whole building, not of the one box:

- `undoTick` (`web/js/undo.js`) fires twice per ▲, once on the button's click
  and once on the `input` it dispatches, and each `undoCapture` does a
  `JSON.stringify` of the whole scope.
- `paintDirty` runs from both `undoTick` and `bldDirtyNote`, and its
  `bldDirty()` (`web/js/buildings.js`) stringifies all of `b.work` to compare
  it with `b.orig`.
- `bldDirtyNote` also calls `bldLevelDirty`, which does `JSON.parse(b.orig)`
  of the whole building and two more stringifies, for one level's chip.
- `bldCvFollow` hands the change to `cvFromGui`, which is debounced but then
  reserializes the whole `building ... { ... }` block into the text pane.

The fix follows the profile, not this list: likely a cached parse of
`b.orig`, one dirty check per event instead of three, and the undo snapshot
and the text pane pushed off the click's own frame. The recruitment-limit
banner (`bldRecruitPressure`) is worth timing too, if anything redraws it.
Done when: on a level of Tsardoms' size a ▲ updates its box and the "= N turns"
beside it within a frame, ten fast clicks land as ten steps, no tab reports
not responding, and undo still steps back one click at a time.

**94b - the turns in the Unit Editor's pool table.** `edRecRowHtml` and
`edRecAddRowHtml` (`web/js/edrecruit.js`) pass the `per_turn` box to `numBox`
with no readout, while the Buildings editor and the tab's own "numbers each
new pool gets" block pass `<span class="turns">= ...</span>`. Pass the same
readout on both row kinds; `wireNumBoxes` already keeps any `.turns` beside a
box in step with what is typed. It has to fit the row without pushing the
delete button off at the narrow widths Phase 90 set. On the way: `poolTurns`
(`web/js/buildings.js`) still builds "N turns" and "never" in English, which
Phase 88c's plurals by count should cover. Done when: every pool row on the
Recruitment tab, existing and new, shows "= N turns" beside its rate, it
follows ▲▼ and typing, and it reads correctly in every shipped language.

*Phase 94 done 2026-09-30, uncut.* **94a, measured on Tsardoms 3.0 itself**
(installed by the user for this). Its `militia_barracks` level holds **1,131
recruit pools**; the largest in DaC is 343 (`militia_drill_square`) and in
Reforged 166 (`barracks_2`). So the lag is general and Tsardoms is where it
shows: every cost below grows with the level. The building's working copy is 5
MB as JSON and the dialog 265,454 elements. Ten fast ▲ clicks took **4.2 s**,
each a long task of 300-440 ms, of which the click itself was about 50 ms.
Where the rest went, found by timing every timer callback, not by reading the
list above:

- **240-290 ms: the page-wide resize observer** (`rszInit` in `core.js`). It
  takes any added node for "a box may have appeared", and the "= N turns" text
  swapped on every click is an added text node, so each click re-queried the
  whole page. Now only an added element counts. This was none of the four
  suspects.
- **about 100 ms: the dirty checks.** `bldDirty` stringified the whole building
  twice per click, and `bldLevelDirty` parsed the 5 MB original on every call,
  once per level on opening. The original is now parsed once per `b.orig`
  (each level's string kept), and `paintDirty` and the level chip follow a
  burst, 120 ms after its last edit.
- **74-100 ms of layout** on a value change: pool rows off screen now skip it
  (`content-visibility:auto` on `#bldBody [data-cap]`).

**After:** ten fast clicks in **189 ms**, 12-40 ms each, the "= N turns"
beside the box following each, ten undo steps, and Undo stepping back one click
at a time (0.5, 0.333, 0.25, 0.2). **Left:** an undo on that level redraws all
1,131 rows, about 2 s, and opening the level still takes about 2 s. Both are
one-off and not per click.

**94b.** Every pool row on the Unit Editor's Recruitment tab, existing and new,
shows "= N turns" under its rate box (under, so the column keeps its 90 px and
the delete button its place), following ▲▼ and typing. `poolTurns` takes "never"
and a plural "N turns" (`buildings.turns_count`) from the catalogue. Checked on
Reforged's Arnor Militia: six rows, "= 5 turns" going to "= 4 turns" on a ▲.
`tests/test_bigbuilding` (9); `test_unit_recruitment` green. `test_buildings`
cannot run for now: the M2EX EUR the user installed has a hand edit in its
`battle_models.modeldb` (a stray `v` after a `0` in entry #88,
`cardolan_sharpshooters`), which the modeldb reader refuses.

# What else is open

Every rated item is built: the five- and four-star rows, and the three-star
rows, which became Phases 56-73 and 25-27. Their write-ups are in
`ROADMAP_ARCHIVE.md`, with how the ratings were reconciled with the 2026-09-05
triage board.

## Unrated, and the rating is not the reason

**`battle.sd`, `strategy.sd`, `shared.sd`** - the interface skins, 23 archive
documents between them and a dedicated editor already in the archive
(`m2_sd_editor`). It was left unrated and it is the one row on the ballot that
argued against itself: this is GUI skinning rather than mod data. It stays here
so the decision is recorded rather than rediscovered.

---

# How this file is kept

## The audit itself

`docs/upstream/REFERENCE_GAPS.md` holds the full write-up of all fifty-one items - what
each one is, where the reference implements it, what was verified against this
repo, and what it would cost. Every phase above names the ids it closes; the
audit is where the reasoning behind each id lives.

The classification is also live at the triage board published 2026-09-05, which
holds the priority per item in its own store. If the audit and this file ever
disagree, this file is the plan and the audit is the evidence.

---
## Explicitly out of scope for V2 and V3 (future expansion only)

Script editor (eventual Scratch-style block UI for faction events), Animations,
Unit Card Generator, Goat Tools, LUA Scripts, New Map Editor, Export/validation
dashboard. Tracked in `docs/upstream/PORT_MANIFEST.json` as `out-of-scope`; nothing in
V2 or V3.0.0 may depend on them.

**Reclassified 2026-09-03.** These were in the same bucket and are now scheduled
rather than excluded: `OsmBackground`, `OsmRegionSearch` and
`CoastlineTracer` move to **Phase 25**; `OverlayMapGenerator`,
`BboxLayerGenerator`, `FeaturesLayerGenerator`, `autoGroundTypes` and the
Köppen / land-cover fetchers move to **Phase 27**. Re-triage them in
`docs/upstream/PORT_MANIFEST.json` when Phase 25 starts. `LuaAiAssistant`,
`ScriptAIAssistant` and `SymbolGenerator` are **not** reclassified - they are
the AI/autogenerate rule and stay a permanent no.

**Reclassified again.** *Animations* became Phases 77-86 (2026-09-23), and the
*New Map Editor* became Phase 87 (2026-09-25, done).

---
## The four documents, and what goes where

Four files, and each one has exactly one job. This split was made on 2026-09-05
because `ROADMAP.md` had reached 3,031 lines and `STATE.md` 2,094, and a fresh
session was reading both in full to find one sentence.

| File | Holds | Grows |
|---|---|---|
| `ROADMAP.md` | locked decisions, phase index, the map-format reference, the schedule of what is left | only when work is added or a decision is locked |
| `ROADMAP_ARCHIVE.md` | the write-up of every finished phase | when a phase finishes and is moved out of the backlog |
| `STATE.md` | where the project is **right now**, under ~60 lines | rewritten, never appended to |
| `STATE_ARCHIVE.md` | the dated session log, newest first | one section per session |

The rule that keeps this working: **when a phase is finished, its write-up moves
to `ROADMAP_ARCHIVE.md` and its entry leaves the backlog in the same commit.** A
phase marked done but still sitting in the roadmap is how the old file got to
3,000 lines.

---

## STATE.md contract

`STATE.md` (repo root) is the first thing a fresh session reads and the last
thing a working session writes. Format - exactly these sections, in order,
**total length under ~100 lines**. (That number was ~60 until 2026-09-05, when
Phases 18-27 were scoped and the Phase status table gained a row per scoped-but-
unbuilt group. The bound is one screenful of scrolling, not a line count for its
own sake; if it is being fought, the thing to cut is duplication of ROADMAP.md,
which is what the Next up section is for.)

```markdown
# STATE - Medieval 2 GUI Toolkit
_Updated: YYYY-MM-DD · vX.Y.Z · after <what this session did>_

## Next up
One imperative sentence: the exact next action (phase + step).

## Phase status
| Phase | Status | Note |
|---|---|---|
Only phases that are in-progress, blocked, scoped-but-unstarted, or the newest
done one. Status ∈ {done, in-progress, blocked, scoped}. One row per phase or
per contiguous group of them, one short note. Finished phases live in
ROADMAP_ARCHIVE.md, not here.

## In-progress detail
Exact stopping point when a phase is mid-flight: files half-edited, failing
tests, the next concrete step. "Clean." when nothing is mid-flight.

## Read first
2–5 paths a fresh session must read before acting (ROADMAP.md is implied).

## Upstream
reference-tool reviewed SHA + date; "sync overdue" flag if >2 weeks old.

## Decisions
Append-only, dated, one line each. Prune into ROADMAP's Locked decisions when
a decision graduates, and into STATE_ARCHIVE.md when the list passes ~10.
```

Rules: update it even for partial sessions (that is its whole point); never let
it exceed a screen - the session write-up goes in `STATE_ARCHIVE.md`, the
reasoning goes in `docs/upstream/` notes or the roadmap, not here; phase exit criteria
live in `ROADMAP.md` only, `STATE.md` just points at them.

**Writing a session up.** At the end of a session, put the "what this session
did" section at the **top** of `STATE_ARCHIVE.md`, dated, and leave `STATE.md`
holding only the six sections above. The old habit of prepending each session's
section to `STATE.md` itself is what took it to 2,094 lines.
