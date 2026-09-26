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
| 77-81 | The packs read; the 687 slots named; transfer held against the destination's pack; every packed animation in the Models viewer, with its weapons, its mount, `.cas` models and another mod's side by side; a port appended to a pack and taken back | uncut |
| 87 | The real world, whole: Mylae's New Map Editor, 87a-87h | uncut, beta line |

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

| # | Phase | Stars | Size | Line |
|---|---|---|---|---|
| 82 | In-game proof: what the engine accepts, rebuilds and prefers | - | S | both |
| 83 | Port the animations with a unit | - | L | both |
| 84 | Keep a ported mod rebuildable: loose `.cas` and `descr_skeleton.txt` for what was ported | - | M | both |
| 85 | Pack housekeeping: duplicates, orphans, and a compacted pack | - | M | both |
| 86 | Animations on their own: a skeleton or one animation from another mod, and an edit saved into the pack | - | M | both |
| 88 | Every major language: the interface translated, with each language's correct technical terms (a termbase, right-to-left, CJK) | - | L, split 88a-88f | both |

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

**77 to 81 are done**; each one's scoping and write-up are in
`ROADMAP_ARCHIVE.md`.

**82 - In-game proof (S, needs the user to run the game).** 81 builds the test
kits into a copy of ROCSS; the user plays a custom battle and reports. The
questions, each with its kit:
1. Does the game load a pack with appended entries and the counts updated?
2. Does the `.dat` header's count matter, or only the `.idx`'s?
3. Does a renamed skeleton (`<name>_<tag>`) and a namespaced animation path
   (no such file on disk) work?
4. When does the engine regenerate the packs from `descr_skeleton.txt`
   (packs deleted? the text file newer?), and does a regeneration drop entries
   that have no loose `.cas`? This decides whether 84 is needed by default.
5. Which of two duplicate entries wins, the first or the last?
6. Does a loose `.cas` at an entry's path override the packed one?

The answers are written into the format notes, and into this phase's archive entry. Done when all six are answered.

**83 - Port the animations with a unit (L).** Unit Transfer gains a fourth
answer beside "port as is", "port with the base's animations" and "use the
base's": **"bring its animations"**, per model group (soldier, officer, mount,
crew, armour upgrades), the default when the destination lacks a skeleton the
unit needs. The plan screen shows, per skeleton: added, reused, renamed; the
animation counts; the MB appended after dedup; weapon skeletons listed
separately. The modeldb entry is written with any renamed skeleton or weapon
names. A batch shares its skeletons (two units on `MTW2_2HSwordsman` move it
once), the way `dest_by_content` already shares models. `descr_skeleton.txt`
gains a `type` block for each added skeleton, from 78's slot names, so the
text file stays in step for what we added. One Undo covers the transfer, the
pack appends included. Done when: a DaC unit on a skeleton ROCSS lacks
transfers into ROCSS, plays in the viewer, passes `verify`, and plays in game
(82's kit, repeated through the real transfer); undo restores ROCSS byte for
byte.

**84 - Keep a ported mod rebuildable (M).** If 82 shows the engine
regenerates the packs and drops what has no loose file, or as an option
otherwise: write each ported animation as a loose `.cas` (packed to `.cas` by
the format notes, through `casanim.write_anim`) at its path, beside the
`descr_skeleton.txt` block 83 already writes, so a regeneration rebuilds what
we ported too. This is the route Wilddog described, done only for what we
added. Done when: a
ported unit survives a pack regeneration in game (82's question 4).

**85 - Pack housekeeping (M).** The "cleanup" asked about on Discord. A report
first: duplicate paths (same bytes or not), entries no skeleton slot uses,
skeletons no modeldb entry names, skeleton names listed twice. Then, as its own
plan and Undo, a compacted pack: only what is referenced, one copy of each
duplicate (the one 82 says the engine plays). Compaction does rewrite the
whole `.dat`, written beside the old one and swapped, so it needs the free
space of the pack and is never automatic. Done when: the report runs on all
three installs, and a compacted ROCSS plays every unit (viewer and `verify`)
and undoes.

**86 - Animations on their own (M).** The same engine without a unit: bring a
named skeleton (with its animations) or one animation into a chosen slot from
another mod; and **the animation editor saves straight into the pack**,
replacing `animedit.REPACK_NOTE`'s "rebuild with xidx" step. A saved edit is
appended under its path, which makes the old entry an orphan (85's report
finds it), so no 352 MB rewrite. Done when: an edit made in 57's editor plays
in game without any outside tool.

**Not in these phases**: exporting a unit with an animation for Blender (the
user's other Discord goal; 80 builds exactly the posed, animated unit an
exporter would need, and `modelexport.py` would carry it), and Rome/RR packs (a
half-frame layout; nothing here is measured on it).

# Phase 88 - every major language, scheduled 2026-09-25

**Asked for by the user on 2026-09-25**: "add a phase to add support for all
major languages. Make sure the words are correct technical words fitting for
the contexts". Unrated, both lines (it is not map work, and every screen
changes), after 87 in the table.

**What is there now.** No internationalisation at all: `index.html` is
`<html lang="en">` and every string a person reads is an English literal in
one of the ~70 modules under `web/js/` or in a message the engine raises. A
crude count finds at least ~380 prose literals in `web/js/` and ~350 raised
messages in `unittransfer/` that can reach the screen; 88a measures the real
number before anything is moved.

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

**88b - every string externalised.** Every module under `web/js/`,
`index.html` and the engine's user-facing messages moved into `en.json` under
stable, namespaced IDs (`map.paint.brush_size`, not the English text as the
key). A lint suite fails on any prose literal outside the catalogue, with an
allowlist for rule 1's code names. Done when: the lint is clean, and every
screen in English is the same text as before, checked against a snapshot
taken first.

**88c - the termbase.** Every technical term in `en.json` extracted and
classified under the four rules, with a rendering and its source per target
language. The checker enforces it: an English string containing a termbase
term must contain that term's rendering in each translation, a rule-1 term
must appear untranslated, and placeholders and plural categories must match
the source. Done when: every term has a rendering and a source in every
language, and the checker passes on the pseudo-locales.

**88d - the European and Cyrillic languages.** `de`, `fr`, `es`, `it`,
`pt-BR`, `pl`, `cs`, `hu`, `tr`, `ru`, `uk`, translated against the
termbase. German, the longest, sets the layout: panels, toolbar and tabs
wrap or truncate with a tooltip, never clip. Done when: the checker passes
for all eleven, and every screen is looked at in German at desktop width and
375 px with nothing clipped or overlapping.

**88e - Chinese, Japanese and Korean.** The four catalogues, a font fallback
stack of Windows system fonts per language (Microsoft YaHei, Microsoft
JhengHei, Yu Gothic UI, Malgun Gothic), line breaking set for CJK
(`line-break: strict` for Japanese), and no synthetic italics or letter
spacing on CJK text. Done when: the checker passes, and every screen renders
with no missing-glyph boxes and no line broken inside a word.

**88f - Arabic and right-to-left.** The Arabic catalogue, and the layout
mirrored with `dir="rtl"`: `index.html` and the modules moved to CSS logical
properties (`margin-inline-start`, `inset-inline-end`, `text-align: start`),
panels and toolbars mirrored. What must **not** mirror stays left-to-right:
the campaign map, the 3D viewer and every canvas, Code View's raw pane, file
paths, coordinates and code names. Done when: every screen is walked in
Arabic, and on the map a click, the tile pin and a drag land on the same tile
as in English.

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
