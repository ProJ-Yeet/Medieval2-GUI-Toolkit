# Medieval 2 GUI Toolkit - Roadmap (present and future)

**This file is what is left to do.** Everything already built has been moved to
[ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md), verbatim, so a session no longer
reads 3,000 lines of finished work to find the next step. What stays here is
what a session still has to act on: the locked decisions, the phase index, the
map-format reference the map modules are built on, and the schedule of what is
left. **When a phase finishes, its write-up goes to the archive and its row here
is struck through, in the same commit** - the rule in *The four documents*
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
Phases 56 onward are in the schedule table further down, struck through as
they finish, beside the ones still to build.

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

# Phases 56-76, then 25-27 - the rest of the roadmap, scheduled 2026-09-23

**Asked for by the user on 2026-09-23: "finish all phases remaining in
roadmap".** With 55 done nothing was scheduled, so everything still open in
this file became a phase, in the order the file already gave it: the *Future
roadmap* list by stars, then by size within a rating (small first, as the
three-star table says), with the two beta items where their four stars put
them. The three numbered campaign-map phases, 25-27, keep their numbers and go
last: they are the largest, and 25 and 27 are the only work here that touches
the network (opt-in, off by default, under the 2026-09-03 amendment).

**Two rows are not phases, and why.** *M17, the crash and validation
dashboard*, is done: it is Phase 54's Health screen, one door to every check.
*The `.sd` interface skins* were left unrated on the ballot because the row
argued against itself - GUI skinning rather than mod data, with a dedicated
editor already in the archive - and "finish the roadmap" does not rate it.
It stays recorded rather than rediscovered.

| # | Phase | Stars | Size | Line |
|---|---|---|---|---|
| ~~56~~ | ~~M12 - several factions at once, and the faction files as a zip~~ | 5 | M | both - **done 2026-09-23** |
| ~~57~~ | ~~M16's editor half - the animation editor and asset converter~~ | 5 | L | both - **done 2026-09-23** |
| ~~58~~ | ~~Will this mod even launch - a readiness row on Home~~ | 4 | S | both - **done 2026-09-23** |
| ~~59~~ | ~~The rest of *Mines and hidden resources*: `descr_settlement_mechanics.xml` and its ceiling~~ | 4 | S | both - **done 2026-09-23** |
| ~~60~~ | ~~Add a religion~~ | 4 | M | both - **done 2026-09-23** |
| ~~61~~ | ~~B2 - delete a settlement, create one where none is, move one between mods~~ | 4 | M | beta - **done 2026-09-23** |
| ~~62~~ | ~~B3 - insert and export one file at a time~~ | 4 | M | both - **done 2026-09-23** |
| ~~63~~ | ~~`descr_lbc_db.txt` and `descr_offmap_models.txt`~~ | 3 | S | both - **done 2026-09-23** |
| ~~64~~ | ~~`descr_animals.txt`, `descr_standards.txt`, `export_descr_advice.txt`~~ | 3 | S | both - **done 2026-09-23** |
| ~~65~~ | ~~`descr_banners_new.xml`~~ | 3 | M | both - **done 2026-09-23** |
| 66 | `descr_hero_abilities.xml` | 3 | M | both |
| 67 | `descr_area_effects.xml` | 3 | M | both |
| 68 | `descr_walls.txt` | 3 | M | both |
| 69 | `descr_character.txt` | 3 | M | both |
| 70 | T6 - every tile as text | 3 | M | beta |
| 71 | D12 - the project as a zip, and loaded back | 3 | M | both |
| 72 | D13 - a horde start for a new faction | 3 | M | beta |
| 73 | M7 - import a campaign from another mod | 3 | L | beta |
| 74 | Import a settlement `.cas` from another mod or disk, and assign it to a culture's level | - | M | both |
| 75 | Fix the Strat models 3D view | - | S | both |
| 76 | Import a building tree from another mod | - | L | both |
| 25 | OSM backdrop and coastline tracer | 3 | L | beta |
| 26 | Map resize, and create from scratch | 3 | L | beta |
| 27 | Overlay and layer generators | 3 | L | beta |

Releasing stays on request: each phase is committed to master as it lands.

**74 to 76 were added on the user's word on 2026-09-23**, after the table
was set, and checked against the code first so none of them repeats work
already done. They are unrated; they go after 73 and before 25-27 until the
user orders them otherwise.

* **74 - a settlement model, imported and assigned.** What exists: the map
  screen lists and draws every strat `.cas` (`/api/map/models`), the Cultures
  screen edits a level's model path as text (`minorfiles.py`), and B3 puts any
  file under `data/` (`fileswap.py`). Missing is the one step joining them:
  pick a model in another mod (or on disk), copy it with the textures it names,
  and write it onto a culture and level in one plan and one Undo.
* **75 - the Strat models 3D view.** Phase 29's viewer (`viewer3d.js`,
  `/api/map/model/geometry`, `tests/test_stratart.py`) has no open defect on
  record; the one fixed on 2026-09-12 was the zero-byte `.tga` taken over its
  DDS. So the first step is reproducing what the user sees, on both mods,
  with the pane visible (a hidden tab never draws WebGL).
* **76 - a building tree from another mod.** Missing entirely: `transfer.py`
  moves units only and the buildings screen edits in place. The shape is
  Unit Transfer's own at EDB scale - the building and its levels, their
  `text/export_buildings.txt` strings, the pictures, and a report of what the
  destination lacks (units a level recruits, resources, factions and cultures
  it names), with one Undo.

# What each open phase is

The user rated the candidates one to five stars on 2026-09-12. Every five- and
four-star item is built (M17, M12, M16, B2, B3, *Will this mod launch*, *Add a
religion*, *Mines and hidden resources*), and so are the finished three-star
rows; their write-ups are in `ROADMAP_ARCHIVE.md`. What is left is the open
three-star rows below, each a numbered phase in the schedule above, and 74-76,
which are described under the schedule. How the ratings were reconciled with the 2026-09-05 triage board is
archived with the rest.

## Three stars

Ordered small to large, because at this rating size is what decides whether one
is worth picking up.

| # | Item | Size | Note |
|---|---|---|---|
| 66 | `descr_hero_abilities.xml` | M | 1,187 lines, 26 tags. Hangs off the people panel, which already edits the character. |
| 67 | `descr_area_effects.xml` | M | 555 lines, 34 tags. Interdict, excommunication and the rest. |
| 68 | `descr_walls.txt` | M | 514 lines. Wall definitions per culture and level; pairs with the settlement panel. |
| 69 | `descr_character.txt` | M | 1,708 lines, twelve archive documents, **read by six modules and written by none**. It is the missing join: `stratmap.py`'s audit names a `.cas`, the Strat models panel draws one, and nothing connects either to the character that uses it. The lowest-rated item on this page that the measurement argues hardest for. |
| 70 | **T6 - export every tile as text** | M | Campaign-map work that did not rate high enough to schedule. We export pictures and never numbers; `mapquery`'s fact table is the join it needs. |
| 71 | **D12 - export the project as a zip, and load one back** | M | `pack.py` already does this shape for a unit, import and conflict report included. |
| 72 | **D13 - generate a horde start for a new faction** | M | 16j-2 already creates a faction with no settlement and no character, which is the shape vanilla's Mongols already are. This is the other half. |
| 73 | **M7 - import a campaign from another mod** | L | Unit Transfer's problem at campaign scale; `transfer.py` is the model. |
| 25 | **Phase 25 - OSM backdrop and coastline tracer** | L | Campaign-map work at three stars. The write-up below stands; it is the first thing in the toolkit that touches the network, so it is opt-in and off by default. |
| 26 | **Phase 26 - map resize, and create from scratch** | L | Campaign-map work at three stars. Phases 22 and 24 removed most of the original objection, so it is cheaper than when it was deferred. |
| 27 | **Phase 27 - overlay and layer generators** | L | Campaign-map work at three stars. Same opt-in rule as 25. |

## Unrated, and the rating is not the reason

**`battle.sd`, `strategy.sd`, `shared.sd`** - the interface skins, 23 archive
documents between them and a dedicated editor already in the archive
(`m2_sd_editor`). It was left unrated and it is the one row on the ballot that
argued against itself: this is GUI skinning rather than mod data. It stays here
so the decision is recorded rather than rediscovered.

---

# Phases 25-27, the longer write-ups

Once called `V3.1`, `V3.2` and `V3.3`, rated three stars on 2026-09-12, and
scheduled last because they are the largest. The write-ups are here because
they are longer than a table row.

## Phase 25 - OSM backdrop and coastline tracer

Mylae's `OsmBackground`, `OsmRegionSearch` and `CoastlineTracer`: an
OpenStreetMap backdrop aligned by `bbox_coords.txt`, and Overpass
`natural=coastline` ways chained and Bresenham-projected onto the heights layer
as editable pixels. Needs the Locked-decisions amendment above, and is the first
thing in the toolkit that touches the network, so it is **opt-in and off by
default** with the mirror list visible in settings.

## Phase 26 - Map resize, and create from scratch

Geomod's resize (audit item **G6**) - add surface area on any edge and rewrite
every coordinate in `descr_strat.txt` - plus building a map from nothing against
the TWCenter tutorial's recipe. Deferred because it touches every coordinate in
the mod, and because shrinking requires the affected regions to be emptied by
hand first, which Geomod's own manual calls unfinished. Phase 22 and Phase 24
between them remove most of that objection, so re-read this after 3.2.0.

## Phase 27 - Overlay and layer generators

Mylae's `OverlayMapGenerator`, `BboxLayerGenerator`, `FeaturesLayerGenerator`,
`autoGroundTypes` and the Köppen / land-cover fetchers. Same amendment and the
same opt-in rule as Phase 25.

---

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
