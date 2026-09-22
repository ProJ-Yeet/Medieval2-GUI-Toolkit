# Medieval 2 GUI Toolkit - Roadmap (present and future)

**This file is what is left to do.** Everything already built has been moved to
[ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md), verbatim, so a session no longer
reads 3,000 lines of finished work to find the next step. What stays here is
what a session still has to act on: the locked decisions, the phase index, the
map-format reference the map modules are built on, and the backlog.

**Where to look**

| You want | Read |
|---|---|
| the next thing to do | this file, **Backlog** below, then `STATE.md` |
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
**23a to 39 are not here** - 23a, 23b, 24 and 29 are finished and archived
with the rest, and everything else in that range is unbuilt and lives in the
Backlog below with its own index.

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

# Backlog

Everything below is work still to do, in the order it will be done.

The forty open items in `docs/upstream/REFERENCE_GAPS.md` were classified by the user on
2026-09-05: **20 Now, 7 Next, 13 Later, none skipped.** The Now set is Phases
18-21 and cuts as **3.1.0**; the Next set is Phases 22-24 and cuts as **3.2.0**;
the Later set is a table at the bottom of this file and is not phased until it
is scheduled. Each phase below names the audit ids it closes, so the two
documents can be checked against each other.

### The version numbers moved, and this is the reason

Until now the three future releases were named `V3.1`, `V3.2` and `V3.3` after
the *features* in them - the OSM backdrop, the map resize, the layer generators.
None of those three is in the Now or Next set, so all three would have shipped
after work that had no number at all.

**Future work gets a phase number, and a version number is assigned only when
something is cut.** That is how Phases 0 to 16 worked and it is what stops this
happening again. So the OSM backdrop is **Phase 25**, the map resize **Phase
26**, the layer generators **Phase 27**, and their old `V3.x` labels are retired.
The `notes` fields in `docs/upstream/PORT_MANIFEST.json` that said "deferred to V3.1" and
"deferred to V3.3" are updated to the phase numbers in the same commit as this
change, so no cross-reference dangles.

### What ships when

| Version | Phases | What it is |
|---|---|---|
| **3.0.0** | 16a-16k, plus 17 | The campaign map editor, and the correction pass over it. Feature-complete and uncut. |
| **3.1.0** | 18-21 | The twenty Now items: the campaign files that had no editor, the names nothing could follow, and the map screen's second pass. |
| **3.2.0** | 22-24 | The seven Next items: placing things on the map, a map that looks like the campaign map, and making or unmaking a region or a campaign. |
| next, block one | ~~29~~, ~~40~~, ~~31~~, ~~42~~, ~~41~~, ~~43~~, ~~28a~~, ~~28b~~, ~~33~~, ~~30~~, ~~34~~, ~~35~~, ~~36~~, ~~37a~~, ~~37b~~, ~~38~~ | **The campaign map. Finished.** 29 landed on 2026-09-12; 43, 28a, 28b, 33, 30 and 34 on 2026-09-15; 35, 36, 37a and 37b on 2026-09-16; 38 on 2026-09-17. Beta except 40, 42, 41 and 38, which were subreleases on both lines. |
| next, block two | ~~32a~~, ~~32b~~, ~~32c~~, ~~39~~ | **The mercenaries. Finished**, all four on 2026-09-17. Beta except 39, which was both lines. |
| after block two | ~~44~~, 45, 46, 47a, 47b, 48 | **The reference-tool pass of 2026-09-13.** Five sessions left, every one a subrelease on both lines. Outside both blocks, and scheduled only because the user named the work. **44 landed on 2026-09-20**; 45 leads. |
| after that | the Future roadmap list | Rated and unscheduled. Three five-star items lead it: M17, M12 and M16. |
| later | 25-27, and the Later table | Not scheduled. |

### The whole plan on one screen

**Fourteen sessions left of the fifteen.** Phase 17 (2026-09-06), all of
Phase 18 (2026-09-07), all of Phase 19 (2026-09-09), 20a (2026-09-10), 20b,
B1, 20c, 21, 22a, 22b and 22c (2026-09-11), 23a, 23b and 24 (2026-09-12) and
**29 with B4 inside it (2026-09-12)** are done and their write-ups are in
`ROADMAP_ARCHIVE.md`; nothing in the Later table is counted, and neither are
B2-B3 below.

**Nothing was released until it was done**, and then it was: Phase 24 closed
on 2026-09-12 and the whole backlog went out the same day as v2.3.0 and beta
2026-09-12, the held v2.2.4 and beta 2026-09-11b notes folded into it. That
discharged the instruction of 2026-09-11, and the cut-as-it-lands rule came
back for exactly one session: Phase 29 went out on 2026-09-12 as v2.3.2 and
beta 2026-09-12c. **It is suspended again from that same day** - work is
committed to master and the user says when it is cut. `STATE.md` carries the
current standing.

---
# Reported from the beta - not phased

Four items off beta users between 2026-09-09 and 2026-09-11. They are not from
the reference audit, so they have no `D`/`T`/`M` id; they are numbered `B` and
they are **not** scheduled into the phases above. All three open ones were
rated on 2026-09-12 at four stars each and live in *Future roadmap* with the
rest of that rating; the detail stays here because it is longer than a table
row. **B1, the crash, is done** (2026-09-11) and **B4 is done** (2026-09-12,
taken inside Phase 29 as planned); both write-ups are in `ROADMAP_ARCHIVE.md`.
B2 and B3 wait.

| id | Item | Size | Note |
|---|---|---|---|
| B2 | Delete a settlement, and move one between mods | M | Half of what was asked for already exists - see below before building anything. B1 added the create. |
| B3 | Insert and export one file at a time, the way Mylae's tool does | M | The user's own words: "that isnt really needed tbh". Lowest of the three. |
| ~~B4~~ | ~~`Rename slot` is refused on a mod that keeps `descr_sm_factions.txt` packed~~ | S | **Done 2026-09-12**, inside Phase 29. `factions.no_file_note` is the one sentence, and the rename screen and the Factions screen both use it. |

## B2 - delete a settlement, and move one between mods

Read this before building: **assigning a settlement and its buildings to a
faction already works.** The settlement panel (16h, `stratedit.plan_settlement`)
takes an `owner` and a `place`, and an owner change is one slice of lines moved
from between one faction block and another - with the capital rule attached,
because the first settlement in a faction block *is* that faction's capital. The
buildings list on the same panel adds, removes and reorders. What is missing:

* **delete a settlement block** - the panel edits and moves, and there is no
  delete. The shape is `stratcamp._delete_splice`'s, which already unmakes a
  whole faction entry.
* **create one** - **the writer exists since B1**: `stratedit.new_block` and
  `plan_new_settlement` add a village last in an owner's block, guarded the way
  16h's edits are. What is missing is a button on the settlement panel for a
  province that has none, and that is all.
* **move one between mods** - `transfer.py` is the model, and `pack.py` already
  does the import-and-conflict-report shape for units. Bigger than the other
  two; probably its own session.

Phase 24's warning applies to the delete: a settlement that goes has characters,
armies and a capital flag hanging off it, and Phase 22 is what makes those
movable.

## B3 - insert and export one file at a time

Mylae's tool lets a file be pushed into, or pulled out of, a mod on its own.
Some of this exists in pieces - `POST /api/map/export` writes Geomod's batch and
a query as a TGA, 16g exports a per-faction TGA, and `pack.py` imports a unit -
and none of it is a general "take this file out" or "put this file in". The user
asked for it and then said it is not needed, so it sits at the bottom.

---
# 3.1.0 - the Now set (Phases 18-21)

Twenty items. Fifteen are S, five are M and none is L, which is what makes
this a release rather than a slog: it is almost entirely files that are already read
and screens that already exist. The common shape is **we know a file well enough
to validate it and not well enough to edit it**, and that asymmetry is what
3.1.0 removes.

**The whole Now set is done**: 18a and 18b on 2026-09-07, 19a and 19b on
2026-09-09, 20a on 2026-09-10, and 20b, 20c and 21 on 2026-09-11. Phase
18's six files are the five nothing wrote and the one the building side could
only refuse against; Phase 19 is the four names nothing could follow; 20a is the
three layers the map screen could draw and not read; 20b is the three ways of
getting to the thing you want, one of which turned out to be three whole
campaigns nothing had ever offered; 20c is the names on the map and the pin;
21 is the faction audit and the raw text editor. All eight write-ups are in
`ROADMAP_ARCHIVE.md`, and 3.1.0 is feature-complete and uncut.

---

## Phase 19 - The names nothing could follow - done

**All four items are closed.** 19a took D4 and D5 on 2026-09-09 and 19b took D2
and D3 the same day; both write-ups are in `ROADMAP_ARCHIVE.md`. What they left
behind and a later phase will use:

- **`unittransfer/namekeys.py`** - every write into a `{key}value` file goes
  through `_write_loc`, which recompiles the `.strings.bin` beside it and joins
  the caller's own backup set. A localisation edit that skips it leaves the game
  reading the old words.
- **`unittransfer/renames.py`** - three subjects on one engine, position-aware
  everywhere because these three namespaces are not clean enough for a token
  walk, and `campaign_dirs`, which finds a campaign folder at any depth where
  `campstrat.campaigns` finds only the top level.
- **two corrections to things that were nearly true** - `descr_names.txt` has a
  fourth section (`surnames`), and `descr_strat.txt` does **not** name a
  settlement. Both were stated confidently in code that had never been measured
  against the second installed mod.

**D1 is in the Later set and is the one this cluster did not make cheaper.**
Changing a region's colour is the same "the identity of a thing is spread across
files" problem with pixels instead of text, and the extra cost is real: region
IDs are first-appearance order in a row-major scan, so a recolour can renumber
every region after it. A rename does not, which is why 19b could be done first.

**G4 is still in Later, and is cheaper than it was.** The legion label is D4 in
miniature and the write it needs is the one 19a added; what is missing is the
paired display name. Flagged, not moved - the user put G4 in Later and that
stands unless they say otherwise.

---

## Phase 20 - The map screen's second pass - done

**All eight items are closed**, across three sessions: 20a (2026-09-10), 20b
and 20c (2026-09-11). The write-ups are in `ROADMAP_ARCHIVE.md`. What the phase
leaves behind for 21 and 22:

- **`cpinButton(what, fn, args)` is the one way a field takes a tile** (20c,
  `web/js/mappin.js`). Phase 22's object dialogs add a pin with that one line,
  and are handed the tile already flipped into the coordinates
  `descr_strat.txt` writes. A second "use the picked tile" button is the thing
  not to write: it selects a province on the way.
- **`clnLayout` is pure and already measured in node** (20c,
  `web/js/maplabels.js`). A fort or a watchtower name placed in 22 goes through
  the same layout as another obstacle rather than a second collision pass.
- **The layer stack is the ten files and stays that way** (20a), and a way of
  looking at the map that is not a layer - the names - is a toolbar switch in
  `cmapLayerState`, so a saved view keeps it.
- **`cmapGoTile` is the one way of arriving somewhere** (20b), and the pin is
  the one way of asking the map for a tile. Between them, no panel needs to
  move the view or read `state.cmap.pick` itself.

---

## Phase 21 - Two screens over data we already hold - done

**Both items are closed** (2026-09-11); the write-up is in
`ROADMAP_ARCHIVE.md`. What it leaves behind for later phases:

- **`factionaudit.Census` is the whole mod's faction census in one pass.** A
  later check about factions - D13's horde start, M12's bulk duplicate - asks it
  rather than re-reading the dozen files, and a new file that should name a
  faction is one reader and one `Check` row.
- **Gap or note is measured per file**, on every installed mod: a gap is a file
  every real faction has, a note one that working factions go without. A row
  added later is classified the same way, never by copying a reference's
  opinion.
- **`factionclone.clone_file` runs one cloner over one file.** The clone and the
  repair share it, so a fix to a cloner fixes both.
- **The raw editor is the escape hatch, and it is always there.** A screen that
  meets a line its parser does not model can offer "open the file as text" with
  `rtOpen(rel, line)` - the audit's file names already do - rather than growing
  a special case.

---

# 3.2.0 - the Next set (Phases 22-24)

Seven items, three of them L. This is where the campaign map stops being a data
layer you can edit and starts being a map you work on.

---

## Phase 22 - Placing things on the map - done

**Both sessions are closed** (2026-09-11), and with them D9, D10 and G5, and
22c followed in the same sitting; the write-ups are in `ROADMAP_ARCHIVE.md`. What it leaves behind for later phases:

- **`stratobj.py` writes every one-line thing that stands on a tile.** A fort,
  a watchtower and a resource are one `plan` with a `kind`. Anything later that
  is one line with two numbers on it is a new `KINDS` entry and a "where it
  goes", not a new module, and its guard is the one to keep.
- **`mapsnap.nearest` is the search, and every rule keeps its own predicate.**
  A new placement rule gets D10 for the price of a lambda, and the finding
  carries `near`. 24's reallocation of a deleted region's tiles and 26's
  resize both need "the nearest tile that...", and this is it.
- **The map a campaign reads is asked, file by file, everywhere (22c).**
  `Registry.map_for` is the object a campaign is drawn and judged on,
  `campmap.layer_map` the one a single layer is drawn from, and
  `campmap.rel_of` the file a finding names and a fix writes. 23a's textures
  ask `layer_map` which ground and climate layer to composite, and a texture
  built for one campaign is not another's.
- **17d's drag drops now.** The pointer's travel was counted only for a pan, so
  every marker drag since 17d ended as a click. 22b found it by dragging with
  the pointer rather than calling the drop.
- **Localize is `cmapLocate(tile)`,** called by `cmapGoTile`, so anything that
  goes to a tile gets the ring without asking for it.

---

## Phase 23 - A map that looks like the campaign map - done

**Closed 2026-09-12, both sessions, and with them D7, T1 and T12.** It was the
most expensive work in this document and the most visible. The write-ups are in
`ROADMAP_ARCHIVE.md`; what it leaves behind is below.

D7 and T1 are the same feature with two implementations to compare, and
TWMapReader's is the better specification of the two.

### 23a - The texture composite

**Closed 2026-09-12**, and the write-up is in `ROADMAP_ARCHIVE.md`. The map is
drawn with the mod's own aerial-map ground textures, one per (climate, ground
type) pair, and TWMapReader's rules were taken as they stand - the pink missing
texture, the default-block inheritance, the wilderness substitution and the two
winter fallbacks. What it leaves behind for 23b:

- **`unittransfer/mapterrain.py` owns the whole of it.** `Vocabulary.texture`
  is the one place the engine's four rules are applied, and it already takes a
  `season`; `plan`, `composite`, `png` and `view` all do. **23b is a switch on
  the panel and nothing in Python**, unless the tint needs one.
- **`plan` is the cheap half and `composite` the expensive one**, kept apart
  because the ✓ Check panel's `terrain.texture` rule needs the first and not the
  second. A plan is kept per (mod, campaign, season) under a key that hashes the
  pixels rather than the files, so an unsaved stroke is a different picture.
- **`mapterrain._index` is exact and in Pillow's C**, by ranking each band and
  packing the three ranks into a byte. Anything later that needs "this layer's
  colours as one byte a tile" should use it rather than a dictionary pass; it is
  16x quicker and the suite checks it byte for byte against the slow one.
- **T12's tint goes over the composite, not into it.** The composite is under
  the whole stack and the region layer is already drawn over it at 55%, which is
  the arrangement a tint has to keep: 16g's colourings *replace* the region
  layer, and on a textured backdrop replacing it is exactly wrong.

### 23b - Winter, and the tint

**Closed 2026-09-12.** The winter set did double 23a for nothing: the season was
already parsed, routed and keyed, so it was a switch. T12's tint is the canvas
`color` blend, which is his grayscale-then-HSB filter chain in one step. What it
leaves behind:

- **The colouring is drawn on the screen, not into the layer composite.** A tint
  takes the luminosity of what is under it and the terrain is four pixels a tile,
  so anything that wants to blend against the map goes in `cmapThemeDraw`
  alongside it. The fill and the frontiers are two canvases, because a line must
  never blend.
- **`Colouring.payload` sends `bands` as well as `colours`.** The group index per
  province, `-1` for one the colouring says nothing about. A colour cannot answer
  that question - a presence map's "none" group is painted the same grey a
  province in no group is - and anything later that needs to know which group a
  tile is in reads this, never the colour.
- **The screen's pixel passes and the server's are checked against each other.**
  `cqGroups` and `cqBorders` are pure and `tests/test_mapquery.py` runs them in
  node against `_draw_borders` over one map. Two real faults came out of writing
  that, both of them years old. Any later pair of "the browser draws it and
  Python exports it" should be tested the same way.

---

## Phase 24 - Make and unmake - done

**Closed 2026-09-12, and with it G1, M15 and the roadmap.** Two operations on a
thing that had a create or a delete but not both. The write-up is in
`ROADMAP_ARCHIVE.md`; what it leaves behind is below.

- **`unittransfer/regiondel.py` - before anything else has to follow a province
  name.** A delete is a rename to nothing, so it walks 19b's
  `renames.REGION_SITES` rather than a list of its own, and it refuses to edit
  the campaign script for the reason a rename does. `renames.mentions` is that
  scan, public now because two callers share it.
- **`unittransfer/campnew.py` - before anything makes a folder the engine
  reads.** The three things a plain copy gets wrong: the compiled map must not
  travel, the `campaign <name>` header names the copy, and 18a's menu keys are
  built from the folder name so a copy inherits none of them.
- **What a delete does not have to move.** Resources, forts, watchtowers and
  characters are placed by tile, so their coordinates survive a province going:
  what changes is whose province they stand in. `mapsnap.nearest` was expected
  here and was not needed, and that is worth knowing before the next feature
  reaches for it.

### What it was, as scoped

- **G1 - delete a region.** Geomod's manual: "click the name of the region, then
  click Delete, and all work on that region including itself will be gone. The
  area of the former region will automatically be allocated to an existing
  region, usually an adjacent one." **We create regions and cannot delete one** -
  verified: nothing in `campaint.py` or `campmap.py` deletes a record or
  reallocates its tiles. 16e's wizard is the whole other half of this and its
  rules apply unchanged, including the one that refuses to leave any region with
  no tiles at all and the warning that a change here renumbers every region the
  engine scans after it.

  **Improve on the arbiter here rather than copying it.** The manual's own
  caveat is that "resources, forts and characters will remain", which is a
  dangling-reference bug the tool ships. 16f already has every rule needed to
  find them, and Phase 22 has just made every one of them movable, so ours names
  what is about to be orphaned and offers to move it.

- **M15 - create a new campaign.** Make a new campaign folder from an existing
  one. Every file in that folder now has a writer here - 16h, 16i, 16j-1, 16j-2
  and `winconds.py`, plus 18a's campaign descriptions - so what is missing is
  the folder-level operation and the plan that says what a new campaign
  inherits and what it must be given.

---

# The Now and Next sets are finished, and a new set opens

**Every phase in the Now and Next sets is done**, the last of them on
2026-09-12, and the cut they were held for went out the same day as **v2.3.0
and beta 2026-09-12**. That closed the backlog this document was written round.

**Phases 28 to 43 below are what reopened it.** They come from one review on
2026-09-12: three things a beta user reported, one tool cross-reference, a
measurement pass over the four references and the TWCenter archive, and then a
rating pass in which the user gave 38 of the 39 candidates one to five stars.

## The order, and the rule that produced it

**Two blocks, and the user set them: the campaign map first, then the
mercenaries. Everything else waits.** What is not in one of those two blocks
lives in *Future roadmap* below, rated and unscheduled, to be started when the
two main tasks are finished.

**Inside each block the order is: a defect, then the thing later work stands
on, then stars, then size.** That is four rules and each one earns its place.

1. **Phase 29 led because it was the only defect.** Somebody was hitting it
   and it was the only new phase reaching both release lines. Done 2026-09-12;
   **28 is now first**.
2. **Phase 28 is second because every later panel lands on it.** Phase 32's
   screen goes onto the right-hand column, and building it in the old
   sixteen-panel stack is work done twice.
3. **Then five stars before four, and inside a rating, small before large.**
   Phase 33 is three separate five-star **S** items in one session, which is
   why it is third: it is the cheapest five-star work on the list.
4. **A phase that makes another one legible comes first.** Phase 30 is before
   Phase 34 because declaring a climate without its textures produces the
   largest field of pink anybody will ever see here, and 30 is what makes that
   readable instead of alarming. Phase 35 is before Phase 32 for the same kind
   of reason: it is the same two-way panel over a file that is already fully
   parsed, so the shape gets settled on the cheap problem first.
5. **Three phases went in front of 28 on 2026-09-12, and rule 1 is why for one
   of them.** (**40, 31, 42 and 41 are done, so 43 now leads the block.**) Diffing Mylae's `2740b0b..187d9ed` re-scoped Phase 31 and produced
   Phase 41, and the user asked for both immediately; reading our own
   region-creation path beside his turned up **Phase 40**, which is a defect in
   shipped work and therefore leads the block the way 29 did. 28 is still the
   enabler and still comes before everything that lands a panel on it - 40, 31
   and 41 land no panel. **42 and 43 joined them later the same day**, both from
   the user: 42 is a second reported defect and sits behind 40, and 43 is a
   three-way toggle over a file `stratedit` already writes.

### Block one - the campaign map

| Order | Phase | Size | Line | Stars |
|---|---|---|---|---|
| ~~1~~ | ~~**29** Strat model viewer~~ | M | **both** | **done 2026-09-12** |
| ~~2~~ | ~~**40** The new province the engine cannot read~~ | S | **both** | **done 2026-09-13** |
| ~~3~~ | ~~**31** Two river rules, and a ford in the sea~~ | S | beta | **done 2026-09-13** |
| ~~4~~ | ~~**42** The art a clone does not get~~ | S | **both** | **done 2026-09-14** |
| ~~5~~ | ~~**41** Merge one faction's name pool into another~~ | S | **both** | **done 2026-09-15** |
| ~~6~~ | ~~**43** Playable, unlockable, not playable~~ | S | beta | **done 2026-09-15** |
| ~~7~~ | ~~**28a** The strip, and the groups behind it~~ | M | beta | **done 2026-09-15** |
| ~~8~~ | ~~**28b** The toolbar over the canvas, and a steady tooltip~~ | M | beta | **done 2026-09-15** |
| ~~9~~ | ~~**33** T10, G2 and G4 in one session~~ | S x3 | beta | **done 2026-09-15** |
| ~~10~~ | ~~**30** A missing texture without the pink~~ | S | beta | **done 2026-09-15** |
| ~~11~~ | ~~**34** Add a climate zone~~ | M | beta | **done 2026-09-15** |
| ~~12~~ | ~~**35** Rebels right in place~~ | M | beta | **done 2026-09-16** |
| ~~13~~ | ~~**36** D1, change a region's colour~~ | M | beta | **done 2026-09-16** |
| ~~14~~ | ~~**37a** T7, the spawn export~~ | M | beta | **done 2026-09-16** |
| ~~15~~ | ~~**37b** T3, an FE zoom~~ | M | beta | **done 2026-09-16** |
| ~~16~~ | ~~**38** `descr_campaign_db.xml`~~ | M | **both** | **done 2026-09-17** |

### Block two - the mercenaries

| Order | Phase | Size | Line | Stars |
|---|---|---|---|---|
| ~~17~~ | ~~**32a** The pool as a record, and one parser for it~~ | M | beta | **done 2026-09-17** |
| ~~18~~ | ~~**32b** The two directions, and the four gates resolved~~ | M | beta | **done 2026-09-17** |
| ~~19~~ | ~~**32c** Five rules, and the repair for the one that has a safe answer~~ | M | beta | **done 2026-09-17** |
| ~~20~~ | ~~**39** The engine ceilings~~ | M | **both** | **done 2026-09-17** |

**Twenty sessions, and six of them are subreleases.** 29, 40, 42, 41, 38 and
39 touch something outside the campaign map, so each is a subrelease on both
lines; the other fourteen are the beta alone. **29 is done** (2026-09-12) and
took B4 with it, **40 and 31 are done** (2026-09-13), **42 is done**
(2026-09-14), **41, 43, 28a, 28b, 33, 30 and 34 are done** (2026-09-15) and
**35, 36, 37a and 37b are done** (2026-09-16) and **38 is done** (2026-09-17); block one is finished, and **block two is finished too: 32a, 32b, 32c and 39 all closed 2026-09-17**. Both blocks the user set are done; **Phases 51, 52 and 53 come next (added 2026-09-21), then 45 to 48**, each by its own table. **43 was nearly all built already** - 16j shipped the
roster writer and the write-up had not checked - so what landed was the one
sentence of it that was true, the refusal. **28a's scoping held in full**, and
what it did not say was that the layer stack has to be capped or it takes the
whole column. **They are committed, not cut** - cut-as-it-lands was
suspended again on 2026-09-12 and a release now happens when the user asks for
one.

**Six more sessions were added on 2026-09-13 and none of them is in either
block.** Phases 44 to 48 come from the user's pass over Mylae's non-map
screens; all six are subreleases on both lines and all six sit after block two
until the user moves them. They have their own order table in *Phases 44-48*
below.

---
# Phases 28-43 - the campaign map, then the mercenaries

## Phase 28 - The right menu becomes a menu

**Split into 28a and 28b on 2026-09-13.** A second read of Mylae's map screen,
asked for by the user, added two things to what this phase was already going to
touch: the brush belongs over the canvas rather than beside it, and the tooltip
moves. Neither is the strip, both are the same screen, and together they are a
second session. 28a is the strip and the groups exactly as scoped; 28b is the
two things that live over the canvas.

### 28a - The strip, and the groups behind it - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. The scoping held - every
line of it - and three things it did not say were found by building it.**

**The six groups, and the layers outside them.** `CMAP_TABS` in `campmap.js` is
the grouping table: Map (Campaigns, Find, Views), Validate (the read's own
findings, then Check), Query, Paint (Paint, Markers, Events), Province (the
picked tile, Settlement, Characters, Forts, Delete) and Campaign (Campaign
settings, Strat models). Sixteen panels behind six tabs, which is the point -
sixteen tabs would have been the column laid on its side. `#cmLayers` is in no
tab and is asserted to be in none, because 20a's ruling is that the stack is the
ten files the map is made of and it is what the number keys tick.

**Grouping cost the fifteen panel modules nothing.** Each group is a `<div>`
that is hidden or not, and every panel div stays in the DOM with the id its own
module already writes into - so `campbrowse.js`, `mapcheck.js`, `stratedit.js`
and the rest were not touched at all. Only `campforts.js` changed, by one line,
and that is the fort click surfacing its own tab.

**The findings banner is behind Validate now, with a count on the tab.** It was
a block pinned above everything; putting it behind a tab would have made the
screen quieter rather than tidier, so `cmapTabBadge` puts the number of read
findings on the tab itself. DaC shows `Validate 1`.

**"Switched to, once" is once per map, not once per manual pick.** The first
draft re-armed the automatic switch every time a tab was picked by hand, which
reads as the obvious meaning and is the wrong behaviour: somebody who goes to
Paint and then clicks province after province is painting, and being dragged to
Province on every click is the annoyance rather than the help. So `cmapSurface`
switches once and marks the tab with a dot every time after. The dot is real
work rather than decoration - under the first draft it was almost unreachable.

**A collapsed column is never opened by a click on the map.** Collapsing is a
decision and a map click is not a reason to overrule it, so the rail carries the
mark and nothing moves.

**The layer stack had to be capped, which the write-up did not foresee.** Pinned
at its natural height it is **794px on DaC** - ten layers with their legends and
20a's two readings - in an 842px column, so the tab body got nothing and the
strip was the old stack with extra steps. `.cmside > .cmlayers` is
`flex:0 1 auto` with `max-height:45%` and its own scroller; `.cmbody` scrolls
between the strip and it. Two scroll regions in one column is the honest cost of
"the layers stay visible whichever tab is up".

**`.cmside.wide` and the drag cannot both size the column**, and that is
`edPrevMin`'s problem in `editor.js` a second time: an inline flex beats a
class. `cmapWireSplit` takes the inline width off while 16d's Code View is up
or the rail is showing, and puts it back - with the saved width - when either
ends. The drag itself is `splitInstall`'s, a third caller beside the 3D dock and
the BMDB browser.

**Two CSS faults found by looking at it rather than by reasoning about it.**
`.cmgroup{display:flex}` beats the UA sheet's `[hidden]`, so all six groups
showed at once until `.cmgroup[hidden]{display:none}` was added. And six tabs
wrap to two rows at 336px, which is fine, but the collapse control was on the
end of the strip and landed wherever the wrap left it - it is on the header line
now.

**Verified in the browser against DaC**, not only in the suite: the first click
surfaces Province and the second marks it, the collapse leaves a 40px rail of
six icons that opens again from itself, a pointer drag on the bar moves 336 to
426 and saves it, a reload opens collapsed-and-426 when that is what was left,
`cmapResetView` puts back the first tab at 336 with the column open, and a named
view carries the tab and the width through `cvwSnapshot` / `cvwPlan` / `cvwLoad`
while a preset saved before 28a names neither and leaves both alone.

`tests/test_web_modules.py` is **34/34** against 22/22: the grouping table is
read the way `MODES` is, and the checks are the ones that catch the class of bug
rather than an instance - no panel in two tabs, every panel in the table one a
module writes into, Validate holding Check, the layer stack in no tab, every
`cmapSurface()` call naming a panel the table knows, and the three habits in
`cmapLayerState`.

The original scoping follows.

`#cmSide` is a flat stack of sixteen panels: the mod header, the findings
banner, and then Campaign, Find, Views, Check, Query, Paint, Markers, Events,
Layers, the picked tile, Delete, Settlement, Forts, Characters, Campaign
settings and Strat models. Every one of them was added where the last one
ended, and the result is a column you scroll rather than a menu you use. On a
1600 px window the Strat models panel is four screens below the fold.

**It becomes a tab strip over a switchable body, and the strip goes on top.**
The shape already exists and is not to be written twice: `MINOR_TABS` and
`minorTabsHtml` in `core.js` are the Minor Files strip, and the campaign map's
strip is the same widget with a different table. A tab is a **group** of
panels, not one panel, because sixteen tabs is the column again laid on its
side.

**Validate is one of those tabs, and the user asked for it by name.** Mylae's
map screen is `Strat`, `Validate` and `3D` across the top of the right column
with the whole of his validation behind the middle one, and that placement is
plainly better than ours: `#cmCheck` is a section in a stack of sixteen. So the
grouping table gives the validator a tab of its own rather than a slot in a
group, and the findings, the baseline stamp and the four filters go behind it
together.

**What goes behind that tab is already the larger half.** `mapcheck.py` has 32
rules with a severity, a baseline and an auto-fix on some; his `mapValidator.jsx`
and `mapFeaturesChecks.js` have eight checks between them, of which Phase 31 has
measured the two we lack and taken them. So the thing worth copying here is
where his validator sits on the screen, and not what is in it.

**Three things have to be right or the strip is worse than the stack.**

- **A panel that fills on a click has to surface.** Clicking a province fills
  `#cmPick`, `#cmSettle` and `#cmChars`; clicking a fort fills `#cmForts`. If
  the strip is on another tab that click does nothing visible, which is a
  worse screen than the one being replaced. The tab holding a panel that has
  just gained content is switched to, once, and the strip marks it.
- **The layers are not a tab.** 20a's ruling stands: the stack is the ten
  files the map is made of, and it is what the number keys tick. It stays
  visible whichever tab is up, because ticking a layer while reading a finding
  is the ordinary errand on this screen.
- **What a tab is, is saved.** `cmapLayerState` is the one snapshot of a map
  habit and named views copy it rather than re-deriving it, so the open tab,
  the column width and whether the column is collapsed go in there, and are
  then carried by every preset and put back by `cmapResetView` for nothing.

**The border drags, and the column collapses.** `splitInstall` / `splitWidth`
in `core.js` is already a left-edge drag on a right-hand panel with a saved
width, a minimum on both sides and a double-click back to the default; the
unit editor and the BMDB browser both use it. This is a third caller, not a
second implementation. Collapse is a separate control from the drag and has to
be reversible from the collapsed state, so the handle survives the collapse as
a rail with the tab icons on it.

Exit: the strip on top with Validate one of its tabs, the panels grouped behind
it, a click that fills a panel switching to it, the drag, the collapse, and all
three habits in `cmapLayerState` and therefore in a saved view.
`tests/test_web_modules.py` takes the grouping table the way it takes `MODES`.

### 28b - The toolbar over the canvas, and a tooltip that holds still - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. Both halves as scoped, and
the frame is exact rather than nearly right - measured on the running screen.**

**The brush is over the map.** `.cmbar` is two rows now: the view controls it has
carried since 16c, and `#cmPaintBar`, which `cpaintBarHtml` fills with the arm
button, the five tools, the size and shape and the target layer. The panel keeps
what is read rather than reached for - the palette, the wizard, undo and redo,
the save and the count of what is unsaved - and 28a has just given all of it a
tab. `cpaintToolsHtml` was split into three (`cpaintToolsHtml`, `cpaintSizeHtml`,
`cpaintWaterHtml`) so the bar can take the buttons and the panel keeps the four
sentences about the water brush's measured sea colours.

**One wiring function, handed a box.** `cpaintWire()` became `cpaintWireIn(box)`
and both places call it, so the same five controls behave the same in both and
neither knows where the other put them. `cpaintPaint()` paints both. The size
slider is still the one control that does not repaint on input - it has the
pointer - and it now writes both copies of its number.

**Whether the row is open is a habit; arming the brush is not.**
`cmapLayerState` carries `paint_row` and a named view puts it back; `p.on` stays
out of both, and the suite checks that the snapshot reads the settings and never
the paint session. A view that armed the brush would be a view that starts
editing a map.

**Three layout faults, each a real rule about this toolbar.** The panel's tools
are a five-column grid with the glyph over the word, which is how they fit a
336px column - on a strip that made the bar 107px of covered map, so the word
goes beside the glyph. `.cptg` is `flex:1 1 100%`, which is what makes the layer
picker its own row in the panel and what pushed it onto a second line here with
350px of stage to spare. And an absolutely positioned flex column with wrapping
rows picks a narrower width and wraps inside it, so the bar needed
`width:max-content` for `max-width` to be the only thing that ever wraps it. The
bar is **two rows, 73px, 844 of 1202px** on DaC at 1600 wide.

**The tooltip's frame does not move, and all four causes were removed.** A head
of two lines whether or not there is anything to put on them; one row per layer
the manifest names, a layer with no value saying so rather than writing nothing;
a markers block of `CMAP_TIP_MARKS` lines from the moment that layer is ticked,
empty ones included; and a width rather than a maximum, with everything clipped
on its own line because a name that wraps is a box that changed height.

**A fifth cause the write-up did not have, and it was the last pixel.**
`.count` is 11px against the panel's 11.5 and the rows are `align-items:baseline`,
so a row carrying a code in `.count` moved every row below it by one pixel. With
`.cmtip .count{font-size:inherit}` and a fixed `height:1.5em` on the row, six
probes - a settlement marker, the tile beside it, a far province, the sea, the
map's last tile and a mid-map tile - give **the same 320px width, the same 246px
height and the same ten row positions to the pixel**. With the markers layer on
it is 306px and identical across a tile carrying three things, its neighbour and
the open sea; a tile carrying six shows two and "…and 4 more" in the same box.

`tests/test_web_modules.py` is **54/54** against 34/34, twenty checks added for
the two halves. `tests/test_maplayers.py` 51/51.

The original scoping follows.

**The brush belongs over the map.** `cpaintHtml` builds the whole paint panel
into `#cmPaint`, a section of the side stack: the arm button, the five tools,
the size and the shape, the target-layer `<select>`, the palette and the
new-region wizard. Mylae's `MapPaintToolbar` is the same controls as a strip
across the top of his canvas, and the reason that reads better survives the
difference in stack: **a stroke is made with the eyes on the map**, and a
control you look away from to reach is a control you lose the stroke to.

**`.cmbar` is already that strip**, and it already carries Fit, 1:1, the two
zooms, Names, Labels and Reset over `#cmStage`. So this is a second row on an
existing toolbar rather than a new piece of furniture. What moves up is the arm
button, the tool row, the size and shape, and the target layer. What stays in
the panel is the palette, the wizard and the unsaved-stroke count, because a
palette is a list you read and 28a is giving it a tab.

**Two of our five tools have no counterpart in his row** and neither is worth
losing to a copy of it: the water brush, which writes regions, heights and
ground types together in the sea colours measured off this map, and a pipette
that selects the region on the region layer instead of only taking a colour.
His row is pencil, bucket and pipette, plus a heights mode that is our palette
one level down.

**The tooltip's rows already hold still; the box round them does not.** 17e's
`.cmtiprow` is `grid-template-columns:11px 88px 1fr`, so the label column never
shifts. Four other things do. `cmapTipHtml` writes a head of none, one or two
lines depending on whether the tile is a marker, a province or the sea; `cmkAt`
adds up to seven more lines for what stands on it; `cmapTipRow` returns nothing
at all for a layer with no value at that tile, so the row count changes as the
pointer crosses a layer's edge; and the box is `max-width:290px` with the value
column on `1fr`, so a long province name widens it. The box then follows the
cursor, so every one of those changes is a jump.

**Every one of them is information his tooltip does not carry**, which is why
the answer is a fixed frame and not a shorter readout. His is one header line
and one row per loaded layer at `min-w-[180px]`, and it is steady because it
says less. Ours keeps what it says and stops it moving: a head slot that
reserves its height whether or not it has a line, a row written for every layer
the manifest names (a layer with no value at this tile saying so, the way an
unaligned one already does), the markers block capped at a fixed number of
lines, and a fixed width in place of the maximum.

Exit: the paint controls on `.cmbar` with the palette still in the panel, and a
tooltip whose rows sit on the same pixel across two adjacent tiles that differ
in what they carry. Whether the paint row is open goes in `cmapLayerState` with
the rest, so a saved view puts it back.

## Phase 30 - A missing texture without the pink - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. The feature is as scoped; the
premise underneath it is now wrong, and the mod that makes it wrong is almost
certainly what the report was looking at.**

**"This is not the installed mods at rest. It is the paint tool." That was true
when it was written and it is not true now.** The write-up measured DaC at 15
pink tiles and Third Age Reforged at none, and the installed set has changed
since. **`vanilla_kingdoms_uncompromised` has 159,855 pink tiles - every land
tile it has, 57.6% of its whole map** - because it ships **no
`terrain/aerial_map/ground_types` folder at all**. Its aerial textures are
inside the packed data, the way the stock game's are, and nothing here reads a
`.pack`. Turn the terrain on and the entire land mass is magenta. That is what
"the pink is too jarring on the campaign map" is, and it is a mod at rest.

**One sentence instead of thirty.** The old reading emitted a gap row per
texture filename - thirty rows on that mod, each one saying
`descr_aerial_map_ground_types.txt draws N tiles with X.tga, and it is not in
terrain/aerial_map/ground_types`, which blames the aerial file for a folder that
is simply absent. `plan` now checks the folder first and says it once, naming
the folder and the count and the reason a packed mod looks like this. Ten rows
on that mod against thirty-nine, and **the pink total is unchanged at 159,855**,
which is the invariant.

**The colour, as scoped.** `GAP_FILLS` is magenta (TWMapReader's, and the
default), a neutral dark grey that reads as "nothing here", and the sea, which
is the honest answer for the case every gap on DaC is - fifteen tiles that
`map_ground_types.tga` calls ocean or sea_deep and `map_heights.tga` calls land,
where the sea is what the engine draws. `composite` takes it, `png` passes it
through, and an unknown name falls to the default rather than raising, because
this is the drawing and a query string is not worth a 500.

**A choice of how a gap is drawn and never a choice to hide one.** The count
stays on the layer row - it says "drawn neutral" or "drawn sea" now rather than
always "drawn pink" - and the `terrain.texture` rule stays in the Check panel
whichever is picked. The suite checks both halves: that the three kinds of gap
change colour together, and that the count, the gap rows and every tile that
*did* draw are identical whichever fill is asked for.

**It is in both caches or it is in neither.** The colour is baked into the PNG,
so `/api/map/terrain` takes `&gap=`, the server's disk-cache token is
`mapterrain|<plan key>|gap|<name>`, and the browser's own `shot` is keyed
`mod|campaign|season|gap`. Without either, two colours share one picture and you
get whichever was asked for first. Verified over HTTP: the three fills are three
different PNGs (29,501, 29,309 and 16,218 bytes on that mod - `sea` compresses
hardest because land and sea become one colour), each with its own
`X-Map-Gap` header, and `&gap=chartreuse` answers 200 in magenta.

**A habit, so it rides with the season.** `terrain_gap` is in
`cmapLayerState`, therefore in every named view, and `cmapResetView` puts it
back to magenta. A preset saved before 30 names no fill and opens pink, which is
what that view looked like when it was saved.

**And one pre-existing red turned out to be this.** `test_mapterrain`'s "every
texture it draws with is really in `terrain/aerial_map/ground_types`" has been
failing on `vanilla_kingdoms_uncompromised` - it was asserting a fact about the
mod rather than about the tool. With no folder there is nothing for it to be
true of, so the check now says what it is measuring instead. **84/84 against
72/73.**

`tests/test_web_modules.py` **75/75** against 66.

The original scoping follows.

**Reported from the beta: the pink is too jarring on the campaign map.**
TWMapReader draws a texture it cannot find magenta and 23a took that rule as
it stands, widened by one case. It is the right default and it is not always
the right picture to work against.

**Measured first, because the number changes what this is.** Divide and
Conquer has **15 pink tiles** and Third Age Reforged **none**, in both
seasons. So this is not the installed mods at rest. It is the paint tool: a
stroke that lays down a ground type the aerial file does not declare turns
those tiles pink the moment the composite is rebuilt, and a map being built is
exactly where somebody is when this screen is open.

**A choice of how a gap is drawn, and never a choice to hide it.** The locked
rule is that a baseline shows and stops blocking but never hides, and 23a's
own decision is that a picture of the terrain says what it could not draw. So
the count stays on the panel and the `terrain.texture` rule stays in the
Check panel whatever is chosen; what changes is only the colour under the gap.
Magenta as now, a neutral that reads as "nothing here", or the sea colour,
which is the honest answer for the fifteen tiles DaC has, because all fifteen
are tiles `map_ground_types.tga` calls sea and `map_heights.tga` calls land.

**The colour is baked in Python, so it is a parameter and not a CSS rule.**
`composite` fills with `MISSING_RGB` and pastes over it, and the browser is
served a PNG. The choice therefore has to reach `mapterrain.plan`'s key and
`signature`, or two colours share one cached picture and the one you get is
whichever was asked for first. It goes in `cmapLayerState` beside the season,
so a saved view carries it.

## Phase 31 - Two river rules, and a ford in the sea - DONE 2026-09-13

**Closed 2026-09-13, beta line, committed and not cut. Three rules, one repair,
and no web change - which is what the scoping said, and this time the scoping
held.** Everything the write-up measured was re-measured and every number came
back: Divide and Conquer's 95 river components and Third Age Reforged's 86 are
exactly right, and the three new rules find **nothing on any installed map**.

| rule | what it catches | on the five maps here |
|---|---|---|
| `river.fourway` | a river tile with river on all four sides | **0** |
| `river.no_source` | a four-connected component with no white source on it | **0** |
| `feature.ford_in_sea` | a crossing whose own altitude is sea and whose four neighbours are | **0** |

The write-up measured three maps; this measured five, adding
`vanilla_kingdoms_uncompromised` (73 components) and `Vanilla_Redux` (46, the
same as vanilla's own). Zero everywhere, which is the point: **these are rules
for a map being drawn, not faults anything ships.** The whole rule set still
runs on DaC in about 650 ms against the 659 measured before it, so the
one-second bar has lost nothing.

### `feature.ford_in_sea` needed both halves, and the write-up only had one

The scoping said "a cyan tile whose four neighbours are all sea". That is the
half that separates a ford in the ocean from a legitimate coastal crossing, and
on its own it is not the defect. The defect is that
:func:`campmap.sea_mask` subtracts **every** cyan pixel unconditionally, so the
hole in the ocean only exists where the tile's **own** altitude reads sea. A
ford on a land tile with water round it is odd and is not a hole.

So the rule asks both, and the message and the repair are true because it does:
the tile's own height reads sea by `mapvocab.is_sea_height`, **and** all four
cardinal neighbours are sea, **and** all four are on the grid - a ford against
the edge of the map is a different question and this one does not answer it.

### One repair, and the other two are worth saying no to

`ford_none` clears the crossing to no feature at all. That is the one safe
answer of the three, and the reasoning is in `FIXES` beside it:

* **`river.fourway`** is repaired by removing one arm, and which arm is the map
  author's intent rather than ours.
* **`river.no_source`** is repaired by painting a source at the head of the
  course, and which end is the head needs `map_heights.tga` - the same second
  layer that put Geomod's "two pixels past the coastline" rule out of scope.
* **`feature.ford_in_sea`** has one thing the tile can be, because the heights
  already say so and only the crossing colour was overriding them. Clearing it
  closes the hole, and the suite asserts exactly that: the sea mask reads that
  tile as sea again afterwards.

`map_features.tga` is a `W x H` layer - one pixel **is** one tile - so
`_plan_fords` has no block to fill and no corner to keep consistent, which is
the one way it is simpler than `_plan_heights`.

### The new rule found a flaw in the old fixtures

All three existing river fixtures - `river.diagonal`, `river.isolated` and
`river.rejoin` - painted courses with **no source pixel anywhere on them**, so
each started reporting two findings and tripped `broken(...)`'s "did breaking
one thing report only that thing" check. Each now paints its source, which
makes it a river the engine could build, broken in exactly the one way its rule
is about. White is one of `RIVER_CODES`, so every rule under test sees what it
saw before. `river.isolated` is better for it: it is now a lone **source**
pixel, which is literally Mylae's check 4 and the vanilla `(175,14)` case the
rule was measured against in the first place.

### Still to pass back to Mylae

Both from the original scoping and both still true:

* **vanilla trips his orphan-source check at image (175,14)**, and his port
  makes it an `error`, so his validator calls vanilla broken. Ours is a `warn`
  for that reason.
* **the tool he ported from cannot open either installed map.** It refuses
  anything that is not uncompressed true-colour, and both mods ship
  `map_features.tga` as image type 10, RLE - DaC at 32-bit, Third Age Reforged
  at 24. `maptga.py` reads and re-encodes all ten of DaC's layers byte for byte
  with the RLE intact, which is why any of this could be measured here at all.

**One rule stayed out**, as scoped: Geomod's "a river must extend two pixels
past the coastline" is a rule about a river's mouth against `map_heights.tga`
rather than about `map_features.tga` alone, and it is the only one of the five
that needs a second layer. Scoped out rather than half-checked.

**Beta only.** `map_features.tga` is the campaign map.

## Phase 32 - Who can hire what, and where - the mercenary pools

**The next big feature, asked for on 2026-09-12, and the campaign map is where
it lives.** Click a province and see the mercenaries it can raise, filtered by
faction, by event, by year and by religion; and the other way round, take a
mercenary and see every province it comes from. Three sessions.

### What exists, and it is less than it looks

`descr_mercenaries.txt` is already read, and by exactly one parser, which is
the rule to keep. What that parser keeps is the problem:

- **`mapquery.parse_mercenaries` returns a pool's name, its regions and its
  unit NAMES and nothing else.** Every gate on a unit line is thrown away:
  `exp`, `cost`, `replenish A - B`, `max`, `initial`, `start_year`,
  `end_year`, `religions { }`, `crusading` and `events { }`.
- `RegionFacts.merc_pools` says which pools a province is in, there is a
  `mercenary_pool` filter, and `info_mercenaries` is Geomod's pool map.
- 18a's G3 can **move a province between pools** and warns when a province is
  in no pool at all. That is the whole of the writing.

So today the toolkit can say *which pool* a province belongs to and cannot say
*which mercenaries* that gets you, which is the question actually being asked.

### Measured first, on both installed mods

| | DaC `imperial_campaign` | TAR `imperial_campaign` | TAR `Fellowship_Campaign` |
|---|---|---|---|
| pools | 57 | 27 | 28 |
| province slots | 193 | 148 | 81, **80 distinct** |
| distinct units | 113 | 25 | 29 |
| **unit names with no EDU type** | **2** | **5** | **28 of 29** |

**Three findings fall out of the counts alone, and none of them is reachable
today.**

- **Dead mercenary references.** DaC names `Clan Axemen` and `Framsguard
  Dismounted Axemen`, neither of which is a `type` in its 924-unit EDU. Third
  Age Reforged's Fellowship campaign names 29 units and **28 of them do not
  exist**: `Beorning Mercs` and its siblings appear nowhere in the mod but
  that one file, and the mod ships exactly one `export_descr_unit.txt`, so
  there is no second roster they could be coming from.
- **A province in two pools.** `Mt-Gram_Province` is in two of Fellowship's
  pools. The file's own header says a region "can only be present once in the
  whole file", so this is the file breaking its own documented rule.
- **Most provinces have no pool.** DaC declares 193 of about 400. That is
  probably deliberate and it is worth being able to see on a map.

### 32a - The pool as a record, and one parser for it

**`unittransfer/mercpools.py`** takes over the format, and
`mapquery.parse_mercenaries` becomes a thin call into it rather than a second
reader. That is the one-engine rule and it is not negotiable here: two readers
of a unit line is how the gates get dropped a second time.

The record is the whole line. A name is everything in front of `exp`, which is
how the existing parser already does it and the reason is worth keeping: a
mercenary's name is one to four words and real files write a trailing comma
after it, so a word count is wrong on both installed mods. Then `exp`, `cost`,
`replenish` as its two bounds, `max`, `initial`, and the five optionals.

Writing is `keyblock`'s splice discipline, the same as everywhere else:
comments, tabs and the RATE_H style notes DaC keeps at the top of the file
survive an edit untouched. Add a unit to a pool, remove one, change any field,
move a province between pools (G3's existing operation, now going through
this), and add or delete a pool.

**The file is per campaign.** Third Age Reforged ships a different
`descr_mercenaries.txt` for Fellowship than for `imperial_campaign`, with a
different unit list and a different set of faults, so 22c's ruling applies
unchanged: `Registry.map_for` picks the campaign, and a pool read for one
campaign is not another's.

### 32a done 2026-09-17 - the whole line, and the old reader is a call into it

**`unittransfer/mercpools.py` owns the file.** `mapquery.parse_mercenaries` is
five lines that call it and keep their old shape, and `campfiles.parse_mercs`,
`MercFile`, `set_regions` and `move_region` are its names now, so G3, the
province delete and the rename sweep go through it without changing a caller.
Every campaign on this machine reads the same pools, name for name, as the old
reader did.

**The counts above held exactly**: 57 pools over 193 slots and 113 distinct
units on DaC, 27/148/25 and 28/81/29 on Reforged's two. 363 unit lines in all,
**every one with the five fixed fields in the documented order and not one
fault**.

**One thing the write-up did not have, and 32b needs it.** There is a sixth
optional the file's own header does not document: **`factions { }`, on 41 of
Fellowship's 51 lines**, always after an `events { }`. So "a faction hires a
mercenary through its religion" is not the whole gate on that campaign - a line
can name the factions outright, and 32b's table of four gates is five.
Otherwise seen: `religions` 317, `events` 105, `crusading` 28, `start_year` 2
(Reforged's imperial campaign), `end_year` none.

**Writing is a splice at character positions**, not a re-render: a value is
replaced between its own offsets, an added option goes on the end of the code
part, a removed one takes its leading space. **A value set to itself is not an
edit even when it is spelled differently** - the first sweep found DaC's
`0.10` coming back as `0.1` - and every field of every real line set to itself
leaves the line alone. A new unit copies the pool's last line's indent and the
gap after its name. Six actions behind one plan: `unit_edit`, `unit_add`,
`unit_delete`, `pool_add`, `pool_delete`, `region_move`. **The plan re-reads
its own output and refuses any save in which a record it did not name
changed**, or in which the set of pools is not exactly the one asked for.

**No screen yet, by the write-up's split**: the reading is 32b's. New:
`unittransfer/mercpools.py` (`parse_unit`, `parse_text`, `set_field`,
`unit_line`, `edit_unit`, `add_unit`, `delete_unit`, `add_pool`,
`delete_pool`, `move_region`, `overview`, `plan`, `apply`, `MercUnit`,
`MercPool`, `MercFile`, `MercPlan`), `GET /api/mercpools`,
`POST /api/mercpools/plan|apply`. `tests/test_mercpools.py` 73/73, new;
`test_campfiles` 92/92, `test_mapquery` 109/109, `test_regiondel`,
`test_campnew` and `test_renames` green. `test_campfiles` was 101 and is 92 on
the old code too - the mod set, not this.

### 32b - The two directions, and the four gates resolved

This is the session the feature is actually about, and it is a join, not a
parser.

**From a province:** its pool, and every mercenary in it, each with its cost,
its replenish rate, its pool size, and **why it is or is not available**. That
last part is the whole value, and it needs four lookups we already own:

| gate on the line | resolved against | we already have it in |
|---|---|---|
| `religions { a b c }` | each faction's religion | `factions.py` / `factionaudit.Census` |
| `events { A B }` | the mod's real event list | `campevents.py` |
| `start_year` / `end_year` | the campaign's start and end | `stratcamp.py` |
| the unit name | the EDU roster | `edu.py` |

So "filter by faction" is not a field on the line. **A faction hires a
mercenary if the faction's religion is in the unit's `religions` list, or the
list is absent**, which the file header states outright, and `crusading`
narrows it further to a crusade or jihad army. Picking a faction in the panel
therefore resolves through its religion, and the panel says so rather than
implying the file names factions.

**From a mercenary:** every pool that offers it, every province in those
pools, its cost in each (mods really do price the same unit differently in two
pools), and a button that lights those provinces on the map. `cmapGoTile` is
the one way of arriving at a tile and `cmapLocate` gives the ring for free.

**On the map:** the pool map already exists as `info_mercenaries`. What it
gains is three more colourings off the same facts, which is `_by_value` and
`_by_band` and no new machinery: how many mercenaries a province can raise,
whether it can raise any at all, and which provinces a chosen unit is
available in. Every one of them is a colouring, so the TGA export and 23b's
tint come with them.

**Where it sits is Phase 28's first real test.** This is one more panel on a
column that is already sixteen deep, and it belongs on the same tab as the
picked province. Take 28 first.

### 32b done 2026-09-17 - five gates, a verdict with its reason, and the map

**The join is `mercpools.hire_view`, one call per campaign and faction**, and
the page decides nothing: every unit line comes back with `hire` (`yes`,
`later`, `no` or `unknown`) and the gates behind it in words. **Five gates,
not four** - 32a found `factions { }` - and two kinds of result the table above
did not have: **`unknown`**, for an event nothing in the campaign's own
descr_events.txt or scripts sets (a script elsewhere, EOP's say, may), and
**`info`**, for a faction gate when no faction is picked, which says what the
line needs and decides nothing.

**Events are traced, not only listed.** DaC's `ND_BOH` is in no
descr_events.txt; it is `set_event_counter ND_BOH 1` at `campaign_script.txt`
line 10765, and the gate says so. 1,146 names are set across that script. Three
of DaC's events are set by nothing in its campaign folder - `lanc_cleared`,
`turn_25`, `turn_50` - on four lines. The first draft of the scan took four
seconds on that 10 MB script by recounting lines from the top for every match;
it is 0.06 s.

**Measured, the whole picture:**

- **DaC**, no faction picked: 190 lines hireable from turn one, 74 waiting (57
  on an event, 17 on a crusade), 4 on an untraced event. **Both units the
  scoping called dead - `Clan Axemen` and `Framsguard Dismounted Axemen` - are
  in DaC's EDU as installed now**, so there are none. A catholic faction can
  hire 89 of the 268 lines at once, an elven one 98.
- **Reforged's imperial campaign has two lines no faction will ever hire**:
  `Anduin Bodyguard` and `Angmar Rhudaur Axemen` both carry `start_year 2986`
  in a campaign that ends in 2984.
- **Fellowship** is 28 of 29 names not in the EDU, as scoped, so 49 of its 51
  lines are `no` for everybody; `Mt-Gram_Province` in two pools is confirmed.

**One defect of the join's own, caught by the numbers**: DaC's `egypt` came
back with no religion and could hire nothing, because its record is written
`faction egypt, spawned_on_event` and the name kept the suffix. Every faction
on every campaign now has its religion, and a test says so.

**The map gains three colourings** off the same facts, as scoped:
`merc_count` (bands of lines on sale), `merc_any` (sells anything or not) and
`merc:<unit>` (every province selling one unit), the last listed in the
catalogue per unit like the per-resource maps. The panel's ◉ lights one
through the query panel, so the legend, the tint and the TGA export all come
with it.

**The panel** is the Province tab's sixth sub-tab, `Mercenaries`: a faction
picker; *This province* (following the map's pick), *A mercenary* (every pool
selling it, its price and pool size there, its provinces as chips) and
*Pools*. **32a's writer has its screen here** - edit a line's fields, remove
it, or sell another unit in the pool with the EDU's names offered - and a save
reopens the region record, whose pool box reads the same file.

New: `mercpools.hire_view`, `gates`, `event_sources`, `faction_rows`,
`campaign_years`; `mapquery.info_merc_count`, `info_merc_any`, `merc_units`,
`MERC_BANDS` and the `merc:` code; `GET /api/map/mercs`; `web/js/mercs.js`
(`mcp*`), `#cmMercs`, the `.mcp*` styles. `tests/test_mercpools.py` 102/102
(was 73), `tests/test_web_modules.py` 112/112 (was 105), `test_mapquery`
109/109. Checked live on DaC: the panel on Nan_Curunir for France, the
Raider Warband map lighting 27 provinces, an edit planned and not written.

### 32c - The rules, and the repairs

Five new `mapcheck` rules, each one measurable on the installed mods today:

| code | what | found now |
|---|---|---|
| `merc.unit_unknown` | a unit line naming no EDU type | 2 in DaC, 33 in TAR |
| `merc.region_twice` | a province in more than one pool | 1 in TAR Fellowship |
| `merc.region_unknown` | a regions line naming no province | to be measured |
| `merc.religion_unknown` | a `religions { }` entry nothing declares | to be measured |
| `merc.event_unknown` | an `events { }` entry `descr_events.txt` does not have | to be measured |

**The baseline rule applies and matters more than usual here.** 33 dead
references in Third Age Reforged is somebody else's mod with somebody else's
bugs in it, so all of it shows, is counted, and refuses nothing. A tool that
blocks on 33 inherited faults is one nobody opens twice.

**`merc.region_twice` gets a repair and the others do not.** Which of two
pools a province should be in is a choice, so the fix offers both and the user
picks; there is no safe automatic answer to "which mercenary did you mean" or
"which unit did you mean to name". 16f's three auto-fixes are the shape for
the one, and `rtOpen(rel, line)` is the escape hatch for the rest.

### 32c done 2026-09-17 - six rules, and the repair is a choice

**Six rules, not five**, every one a warning. The sixth is
`merc.year_outside`, because 32b's join found the fault and it had no rule:
a line whose `start_year` is after the campaign ends, or `end_year` before it
starts. `merc.religion_unknown` covers `factions { }` names too.

**Measured on every campaign here, and the table above did not hold:**

| code | DaC | Reforged imperial | Fellowship |
|---|---|---|---|
| `merc.unit_unknown` | 0 | 0 | **49 lines** (28 names) |
| `merc.region_twice` | 0 | 0 | 1 (`Mt-Gram_Province`) |
| `merc.region_unknown` | 0 | 0 | 0 |
| `merc.religion_unknown` | 0 | 0 | 0 |
| `merc.event_unknown` | **4** | 0 | 0 |
| `merc.year_outside` | 0 | **2** | 0 |

"2 in DaC, 33 in TAR" was names measured against an older install; DaC's two
are in its EDU now, and Reforged's imperial campaign has none. **The event rule
reads 32b's `event_sources`, not descr_events.txt alone** - read the way the
scoping wrote it, every one of DaC's 61 event gates would be a finding, because
its events are set by `set_event_counter` in the script.

**The repair is not an auto-fix.** `FIXES` acts on a rule's findings without
asking anything, and which pool a province stays in has no safe answer. So the
Mercenaries panel lists each province in two pools with a **Keep in X** button
per pool, and that is 32a's `region_move`, backed up and undoable like every
other move. The finding's message says where to go.

**A rule with nothing to read is silent.** The first draft reported a skip for
the EDU and the religions on `test_mapcheck`'s fixture mod, which has neither
and no mercenary file either; the four rules that need them now look for a
line to check first. `test_mapcheck`'s timing bar was already red on the old
code (1,144 ms) and reads 1,048 and 1,888 ms with the six rules added; the EDU
read is most of what they cost.

New: `mapcheck._r_merc_*` and `_merc_file`/`_merc_lines`, `mcpKeepIn` and
`mcpRegionName`; the Rules sub-tab's title counts 41 rules. `test_mercpools`
109/109, `test_web_modules` 114/114, `test_mapcheck` 95/97 (the timing bar).

### What this is not

**Not a mercenary unit editor.** The unit itself is EDU's and the unit editor
already owns it; this edits the *pool entry*, which is a different record with
different fields, and a dead reference is fixed by naming a unit that exists,
not by inventing one. The two screens link to each other and neither grows the
other's fields.

## Phase 33 - Three small map wins in one session - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. All three, and each of the
three turned up a fact about the installed mods that the write-up did not have.**

**T10 - the tile on the clipboard.** `c` copies what is under the pointer, or
the tile at the centre of the view when the pointer is off the map, which is the
"copy the view, or what is under the cursor" of the scoping said as one key.
There is a button on the picked tile's own heading as well. The form is
`x 109, y 147`, **measured off vanilla's own `descr_strat.txt`** rather than
chosen: every `character` line in it ends that way. It copies the **game** y and
not the image one, and that is the whole of the arithmetic - the two differ by
counting from the bottom, and a copy that handed over the image y would put a
general on the wrong side of the map.

*The write-up's "the shift-X detail is the model" has no referent.* There is no
shift-X in this tool or anywhere in its history. Taken as `c` for copy, beside
`t` for the tooltip and `f` for find, which is the pattern this screen's letters
already follow.

**G2 - the province's music type.** `mapquery.set_music_region` is the third and
last call against `descr_sounds_music_types.txt`, and it is the other two in
order: the drop takes the name off **every** `regions` line that holds it, the
add puts it on the end of the wanted block's last one. Written as the pair
because a move is exactly that, and because one of the two rules belongs to
each. The block is checked before anything is removed, so a name asked into a
type the file has not got cannot come off its own line and land nowhere.

`campfiles` has a fourth `what` and `_plan_music` is it, which makes this the
third picker on the region panel that saves its own file with its own undo -
17f's ruling, after the mercenary pool and the names boxes. It is the odd one of
the four in `campfiles`: the file lives beside the map layers rather than in the
campaign folder, so **no campaign is sent and switching campaign does not change
the answer**. `map.rwm` is not deleted either - this file is read at load rather
than compiled into the map - and the confirm says so.

*Measured: a move changes exactly two lines and the line count does not.* The
one the name leaves and the one it joins. Moving it back does not restore the
file byte for byte and that is honest rather than a gap, for the mercenary
pool's reason one file over: a `regions` line is a set and the format records no
position for a province within it.

*Two states of the same shape, both real on this machine, and both reported
rather than tidied away quietly.* **58 provinces of
`vanilla_kingdoms_uncompromised` are under two music types**, and **2 of Vanilla
Redux are named twice inside one type**. The engine plays one of them either
way. The panel says which it is, saving resolves it, and the plan names that as
a change before it does.

**G4 - the legion's display name.** `namekeys.region_names` returns a third row
and the panel draws it, which is all that was owed: 19a's writer already handled
any key in that file.

*And the legion is the only one of the three keys that need not name this
province.* Divide and Conquer is the one installed mod that writes the line at
all - **199 of its 200 records** - and only **80** of those point at the
record's own name. The rest point at another province's key
(`Rhudaur_Province` reads `legion: Eregion_Province`) or at a settlement's
(`Imladris`, `East_Moria`). So the row follows whatever the line says and the
label tells you when the key is somebody else's, rather than letting it read as
this province's third name. The other three mods write no `legion:` line and the
row is simply absent, the same rule the settlement half already follows.

*It found a real defect on the first province it was pointed at.* **115 of DaC's
116 distinct legion values already have a line in the names file.** The one that
does not is `Thorenhad_Province`, on `Suduri_Province`, and the panel now says
"no line in this file yet" against it.

`tests/test_web_modules.py` **66/66** against 54, `tests/test_campfiles.py`
**101/101** against 92 with the music save and its undo run against a throwaway
copy of a real mod, `tests/test_namekeys.py` 64/68 against a clean tree's 63/67 -
two checks added, the four failures unchanged and none of them this - and
`tests/test_mapquery.py` 118/118.

The original scoping follows.

Three items that were separately rated five stars, are separately marked **S**,
and share a session because none of them is big enough to hold one on its own.
All three are on the map screen and all three are beta line.

- **T10 - copy the view, or what is under the cursor.** The detail is already
  under the pointer; this puts it on the clipboard as `x 23, y 284`, which is
  the exact form `descr_strat.txt` wants. The shift-X detail is the model.
- **G2 - change an existing province's music type.** B1 already gives a *new*
  province one, through `mapquery.add_music_region`, and `drop_music_region`
  came with 24. Changing an existing province's is the third call against a
  writer that is otherwise finished, plus a picker on the region form.
- **G4 - the legion label, with its name dialog.** D4 in miniature. The write
  it needs is the one 19a added to `namekeys.py`; what is missing is the paired
  display name, which is why 19b flagged it as nearly free and did not take it.

**Take it early and the reason is scheduling, not importance.** Three S items
banked in one sitting is the cheapest five-star work on the whole list, and it
clears three rows out of the future list for good.

## Phase 34 - Add a climate zone - **done 2026-09-15**

**The scoping was right about the files and wrong about the operation.** Every
file was already parsed and the brush already painted the layer, and what was
missing was indeed the operation; the archive tutorial it names -
Bella's *How-To: Add a New Climate Zone*, 2007 - does name exactly
`map_climates.tga`, `descr_climates.txt`, `descr_aerial_map_ground_types.txt`
and `map_ground_types.tga`. What the write-up did not have is that **the
tutorial's own thread withdraws its central claim**, and that the installed mods
agree with the thread rather than with the how-to.

**A climate is a slot, not a thirteenth name.** Eighteen posts and two years
after the tutorial, wilddog writes that a climate the engine does not already
know by name is not read by `descr_geography_new.txt`, that the exe looks to be
hard coded to those names, and that the answer is to amend an existing one
"including the unused1 and unused2 names". Measured here, that is not one
modder's opinion:

* **All four installed mods declare exactly twelve climates, and they are the
  same twelve in the same order** - `mediterranean`, `sandy_desert`,
  `rocky_desert`, `unused1`, `steppe`, `temperate_deciduous_forest`,
  `temperate_coniferous_forest`, `unused2`, `highland`, `alpine`, `tropical`,
  `semi_arid`. Not one added a thirteenth.
* **Divide and Conquer took a slot over rather than adding a name.** It has a
  wholly custom 248,370-tile map, and it paints `unused1` on **18,970 tiles**
  and `unused2` on **192**, calling them Harondor and Lorien in
  `text/climates.txt`. Reforged did the same: 5,466 and 182. So the operation
  this phase adds is the one both big mods performed by hand.
* **`descr_geography_new.txt` gives a block to the twelve and to nothing else.**
  Vanilla Redux is the one mod here that ships the text file rather than only
  the compiled `.db`, and it has fifteen top-level blocks: three settings
  sections and the twelve climates, four as a bare name and eight as
  `<name> modifies <base>`. That file is the ceiling, and it is why the battle
  map is where a new name stops.

So **taking a slot over is the offered operation and adding a name is offered
second**, with the geography file named as the reason it is second. Both are
real - the strat map draws a new name perfectly well, which is why the tutorial
worked for its author - and the refusal is a warning rather than an error,
because this cannot see inside a `.pack` and three of the four mods ship only
the compiled geography.

**Four writes that have to agree, and `map_climates.tga` is not one of them.**
`descr_climates.txt` (the list fixes the index, the block carries colour, heat
and winter), `descr_aerial_map_ground_types.txt` (a texture for every ground
type in **both** seasons), `text/climates.txt` (UTF-16, or the `.strings.bin`
when a mod ships only the compiled copy - two of the four do), and
`descr_climates_lookup.txt` when the mod has one. **Painting is the brush's**:
28b's ruling is that a control which is not the brush does not start a paint
session, so this writes the colour and the brush writes the pixels.

**A take-over keeps its place in the list and an add goes on the end of both.**
The list is the index the engine reads, so moving a name in it renumbers every
climate after the move - 36's lesson about region colours, arriving a file
early. A take-over therefore rewrites its block where it stands and touches the
list not at all.

**Three things the scoping did not have.**

**One: the lookup file is already wrong in the wild, and it is the tutorial's
fault.** Its step 4 prints a lookup list containing `volcanic` while its step 3
prints a `climates { }` block that does not, and **Third Age Reforged and
Vanilla Redux both ship exactly that** - thirteen names in the lookup, twelve
declared, the extra one `volcanic`. Divide and Conquer's twelve match;
`vanilla_kingdoms_uncompromised` has no lookup file at all. All four states are
reported and none is repaired, because a name the engine may be indexing by is
not something to tidy silently.

**Two: a take-over strands the tiles its old colour is on, and the number is
worth saying.** Change `unused2`'s colour on Divide and Conquer and 192 tiles
are still painted the old one, which nothing declares any more, so they fall
through to the `default` block until they are repainted. `claimed_tiles` and
`orphan_tiles` are two counts because they answer two questions, and the plan
says both.

**Three: the ground types in a new block are the mod's own, not a constant.**
Every installed mod is internally consistent - one key set across all of its
blocks - and the set is **not the same everywhere**: three mods name sixteen
ground types and Vanilla Redux names seventeen, the extra one
`impassable_shrouded`. A block written to a table here would be a line short on
one mod in four.

**And one defect found on the way, in `mapvocab` rather than in this.** Its
climate-block regex was `climate <name>` followed by whitespace and a brace, so
**a comment after the header dropped the whole block** and a declared climate
read as undeclared. No installed mod annotates `descr_climates.txt` - but every
one of Divide and Conquer's thirteen blocks in
`descr_aerial_map_ground_types.txt` is annotated exactly that way, so the habit
is real and the two files are edited together. It mattered here and not before
because `climatenew`'s own block finder *does* skip the comment: the panel would
have offered to add a climate that was already there and then overwritten it.
Fixed in `mapvocab.climates`; all four mods read identically before and after.

**New:** `unittransfer/climatenew.py` (`lookup_names`, `lookup_state`,
`geography`, `climate_tiles`, `slots`, `ground_keys`, `donors`,
`climate_block`, `write_climates`, `aerial_block`, `write_aerial`,
`write_lookup`, `ClimatePlan`, `plan`, `apply`, `view`, `VANILLA_ORDER`,
`SPARE`, `GEOG_SETTINGS`), `GET /api/map/climates`,
`POST /api/map/climate_plan|_apply`, `web/js/climates.js`, `#cmClim` in the
Paint tab, the `.cclslots` grid. `tests/test_climatenew.py` (110).

**The route is ahead of the map read**, beside `/api/map/campaigns` and for the
same reason: a climate is declared in four text files under `data/` and not one
of them is a map layer. The layer is read for the tile counts alone, so it is
asked for and never required - which is also the only reason the suite's little
mod, which has no layers at all, can exercise the route end to end.

## Phase 35 - Rebels right in place: province and rebel faction, both ways - DONE 2026-09-16

**The scoping was right that this is a join and a screen, and wrong about how
much of it was missing.** Three of the four things it names already existed, and
finding that out is most of the phase.

| the write-up's "missing" | what was really there |
|---|---|
| see what a rebel faction can field | the Minor Files rebel form, `mfRebelForm`, which lists the `unit` lines and resolves each against the EDU already |
| change the assignment from the province end | the `rebels` box on `cmPick`, editable since 16d and validated against the declared list since then |
| light its provinces on the map | `info_rebels` runs through `_by_value`, which builds one group per rebel faction; the group filter is the highlight. Measured: 38 groups on DaC, one per named faction |
| **take a rebel faction and see its provinces** | **nothing, anywhere** |

So what was built is the reverse list and the one operation the rebel end has
that the province end does not: **assigning many provinces at once**. And the
phase gets its "what this is not" from the same measurement, in 32c's shape:
**not a rebel faction editor**. That record is Minor Files' and works there.

### There is no rule here, and the measurement is why

The archive tutorial this was scoped from is Errabundi's *Rebels Right in
Place*, whose complaint is Bulgarian rebels spawning in Serbia. Measured on both
installed mods:

* **not one province names a rebel faction that is not declared.** DaC's 200
  records name 38 of its 42 blocks; Reforged's 199 name 27 of its 30.
* **not one of the 248 `unit` lines across the two mods names a unit the EDU
  does not have**, in any case.

There is nothing for a validator to find. A wrong assignment is a *valid*
assignment somebody did not mean, and no rule separates the two, which is what
the write-up itself says: it is invisible unless you colour the map and look.
**So this ships no `mapcheck` rule and no repair**, and saying so is better than
inventing a rule that fires on a correct file.

### What the measurement did turn up is `chance`, and it is in the other file

* **Third Age Reforged sets `chance 0` on every one of the 27 blocks its
  provinces name.** All 199 of its provinces point at a rebel faction that will
  never spawn: province-driven rebels are switched off across the whole mod,
  uniformly. Only `brigands`, `pirates` and `gladiator_uprising` are non-zero,
  and no province names those.
* **DaC spreads it**: 2 on 29 blocks, 4 on 7, 6 on one, 10 on one, and
  `No_Rebels` at 0 on the 9 provinces meant to have none.

So `chance 0` is an idiom and a rule flagging it would be wrong 208 times. What
it earns is a **note**: the chance is on every row, because picking a block
without it is the one way to make this edit and have it do nothing.

### Three blocks that no province names are not orphans

Each mod declares exactly one block per non-`peasant_revolt` category, named
after the category itself, and the engine spawns those by category rather than
off a region record. `BY_CATEGORY` is that exemption; without it the reverse
list calls three correct blocks dead on every mod there is. What survives the
exemption is a real orphan: **two on DaC**, `Ent_Rebels` and `Saralainn_Rebels`,
declared with units and named by nothing, and **none on Reforged**.

### The defect it led with, which is in shipped work and not in this

Rule 1 of the order, applied on the way in. **The region record editor wrote the
base `descr_regions.txt` whatever campaign was on the screen.** A campaign that
ships its own copy is drawn and judged on that copy - `CampaignMap` reads it and
sets `regions.path` to it, which is 22c's rule, and `_region_delete` beside it
has always honoured it - but `plan_region` read `read_regions(mod)` and
`apply_region` wrote the `REGIONS_REL` constant. **Reforged's Fellowship
campaign ships its own and the two files differ in eleven records**, so this was
not latent: a save made on Fellowship wrote a file that campaign does not read,
and the screen went on showing the old value.

**The stale compiled map was the same defect's other half.** `apply_region`
deleted `base/map.rwm` alone, and Reforged ships a `map.rwm` in its Fellowship
folder too - a different file, 14 KB apart - so an edit there left the stale one
exactly where the engine looks first.

Fixed at four levels: `plan_region` takes the map, `apply_region` writes the
path the plan carries, `stale_rwm` names the compiled maps a write really makes
stale, and `campmap.js` sends the campaign it was never sending. New:
`campmap.RWM_NAME`, `campmap.regions_rel`, `campmap.stale_rwm`, a third argument
on `plan_region`.

### Verified

`tests/test_rebelpools.py` **68/68**, new. Eleven suites re-run and all green -
`test_web_modules` 75/75, `test_campedit` 107/107, `test_campaint` 169/169,
`test_regiondel` 62/62, `test_codeview` 141/141, `test_namekeys` 56/56,
`test_campnew` 52/52, `test_minorfiles` 185/185, `test_mapquery` 109/109,
`test_climatenew` 98/98. `test_campmap` is 108/112 and **a stashed tree gives
the same 108/112 with the same four failures by name**, all of them DaC-number
checks against a mod build that has moved.

Driven in the real app against both mods: the panel lists 42 factions on DaC
with the localised names resolved, the orphan warning fires on `Ent_Rebels`, a
chip jumps to the province on the map, and `GET /api/map/rebels` with
`campaign=custom/Fellowship_Campaign` answers with that campaign's own file.

## Phase 36 - D1: change a region's colour - DONE 2026-09-16

**The write-up's premise is withdrawn: a recolour does not renumber.** It was
scoped on "changing one colour can renumber every region after it", and that is
the one thing a recolour cannot do.

A region ID is the order a colour is **first met** in a row-major scan of
`map_regions.tga`. That is a fact about **where a province's pixels are**, and a
recolour moves no pixel: it changes what colour they carry, and the scan meets
the same province at the same tile as before. Measured by renumbering both
installed maps with one province recoloured, the first in the scan order and one
in the middle: **not one ID moved, in any of the four cases.** Then measured
again off disk after a real save, with a freshly read map: still zero.

So the panel's job turned out to be the opposite of the one scoped for it. It
does not show which regions move; **it says that none of them do**, and that is
the reason to press the button. The create wizard warns that a new province
renumbers and the delete warns that removing one does, both correctly, because
both of those really do move pixels between colours. Somebody who has read those
two will assume this one does too.

### The one case that does renumber is refused, not warned about

Painting a province in a colour another province already uses is not a recolour,
it is a **merge**: two colours become one and a province leaves the map.
Measured on DaC, that moves **51 region IDs** and takes `Celebrant_Province` off
the map entirely. So it is a refusal, and the refusal says why.

The other three refusals are the ones `start_region` already makes for a new
province, because a colour is a key and the ways a key can be wrong do not
depend on whether the record holding it is new: a marker colour (black is a
settlement, white is a port), the colour it already has, and a colour that is
painted on the map but declared by no record.

### It is every tile of the colour, not a bucket fill

`campaint` had a bucket and no whole-colour replace, and the bucket will not do:
**8 of DaC's 200 declared regions and 10 of Reforged's 199 are not one connected
blob.** A bucket from `Forodwaith_Province`'s anchor reaches 27,083 of its
40,995 tiles and would leave **13,912 behind in the old colour**, which is then
a colour no record declares - Phase 40's undeclared-province fault, manufactured
on purpose. `region_tiles` is the whole colour wherever it is.

**The marker guard cannot fire here**, which is worth knowing rather than
assuming: the tiles are chosen *by* carrying the region's colour, and a
settlement pixel is black. The settlement inside a province survives because it
was never in the list.

### The two halves are one save, and the existing guard refused its own

The pixels and the record's `rgb` line have to move together: a record naming a
colour nothing carries is a province with no tiles, which is legal to write and
fatal to play. The stroke goes onto the paint session's undo stack and
`plan_paint` writes both in one backup set.

**That is where the one real defect of the session turned up.** `_emptied`
compares every declared colour against what is painted, and during a recolour
the pixels are already the new colour while `descr_regions.txt` still names the
old one - which is exactly the shape of the fault it looks for. So the save
refused itself, correctly and uselessly. It now reads the pending record change
for that one province and judges every other one exactly as before, so a
recolour that painted over a neighbour still empties the neighbour and still
refuses.

The mirror case is refused too: undoing the stroke and then saving would write
the record alone, and that is caught by name rather than half-written.

### What actually reads a region ID, measured

The renumbering warning that 16e and 24 both ship ends "no file needs editing -
but a script that names a region by number now names a different one". **That
script exists and nobody had counted it.** Measured across every `.txt` under
`data/`, uncommented lines only:

| mod | live numeric region references | where |
|---|---|---|
| Divide and Conquer | **141** | 76 in `export_descr_ancillaries.txt`, 62 in `export_descr_character_traits.txt`, 3 in `campaign_script.txt` |
| Third Age Reforged | 3 | `custom_script.txt` (a further 9 are commented out) |

`IsRegionOneOf` and `IsTargetRegionOneOf` take regions "by label or number", and
DaC uses the number 141 times, each with a comment naming the province. So the
create and delete warnings matter more than their wording suggests, and this
phase's "nothing moves" is a measured reassurance rather than a politeness.

*(Whether DaC's 141 numbers are still correct was not established: the comments
are informal - some name a settlement, some a list of provinces - and a
string-match against the scan order produced disagreements that were the
matcher's fault, not the mod's. Counting them is honest; auditing them is a
different job and is not claimed here.)*

### Built

`campaint.region_tiles`, `recolour_faults`, `recolour`, `cancel_recolour`,
`_plan_recolour`, `_emptied(recolour=)`, `sess.recolour`, and `_stroke_over`
lifted whole out of `paint` so the recolour is the same stroke the brush makes
rather than a second writer with its own opinion about markers and its own undo.
`campmap.render_block` gains the `rgb` slot - `plan_region` goes on refusing that
edit, because the hand-edited form still has no way to move the pixels, and the
recolour is the only caller that passes it. `POST /api/map/recolour` and
`/api/map/recolour_cancel`, `web/js/recolour.js`, `#cmRecolour`, and a **Change
colour…** button on the record's Colour row.

### Verified

`tests/test_recolour.py` **47/47**, new, on a 12x8 map written for it with a
province in two disconnected pieces and a settlement pixel inside another.
Eight suites re-run green - `test_campaint` 169/169, `test_campedit` 107/107,
`test_codeview` 141/141, `test_web_modules` 75/75, `test_regiondel` 62/62,
`test_rebelpools` 68/68, `test_campnew` 52/52, `test_mapquery` 109/109.
`test_campmap` is 108/112 with its four pre-existing DaC-number failures.
`test_mapcheck` fails only *the whole rule set runs under one second*, which
a stashed tree fails harder on the same machine (1,522 and 1,840 ms against
1,214 and 1,227), so it is the load and not the change.

Driven in the real app against DaC: the dialog opens off the Colour row,
Repaint stays disabled until the colour changes, another province's colour is
refused with the merge reason, and a free colour repaints 221 tiles of
`Celebrant_Province` with a clean plan naming both files. The session was
discarded afterwards and the mod's own `descr_regions.txt` re-read to confirm it
is untouched.

## Phase 37 - The two exports the map screen cannot do

Both five stars, both **M**, both a reader over facts we hold. Two sessions.

### 37a - T7, the spawn export - DONE 2026-09-16

The scoping held in full, and the distinction it rests on is the reason the
phase works: 19b refused to WRITE the campaign script because its grammar is
nothing this toolkit models, 24 kept the refusal, and reading coordinates out of
one is not writing it. The refusal is untouched.

**What was invisible, measured.** The markers layer has shown seven kinds since
18b, every one of them out of `descr_strat.txt` and the two event files:

| campaign | script spawns | against descr_strat |
|---|---|---|
| DaC, imperial_campaign | **1,324** (1,317 armies, 3,822 units) | 305 characters |
| DaC, Shattered_Alliances | **1,131** (1,129 armies, 3,340 units) | - |
| Reforged, Fellowship | 98 (64 armies, 431 units) | 150 characters |

**Four fifths of what DaC's imperial campaign puts on the map was not on this
screen.** The layer's counts now read settlement 200, character 305, fort 105,
watchtower 295, resource 1,131 and **spawn 1,324**, which is why the category is
the only one that opens OFF: switching it on quadruples what is drawn, and a
layer that opens unreadable is one nobody opens twice.

**Every spawn carries a coordinate.** 2,510 `spawn_army` blocks over the three
campaigns and not one without an `x`/`y` on its `character` line, so the reading
is complete rather than a sample, and there is no silent remainder behind the
export.

### The reading is validated, and that matters more than the feature

A report nobody believes is worth nothing, so the resolution was checked against
the one thing that can check it - `stratobj.Vocabulary.province_at`, the same
call every other reader of a game coordinate uses:

* **DaC imperial: 1,322 of 1,324 land in a named province, and both misses are
  admirals**, which is correct because an admiral is a fleet.
* **Shattered Alliances: 1,127 of 1,131**, the four being two admirals at sea
  and two standing on the ocean's own colour while `map_heights.tga` calls the
  tile land.
* **DaC's 3,822 unit names are every one in its EDU.** That is what finally
  proved the parse (see below).

A reading that agreed with the map 99.8% of the time by accident is not a thing
that happens.

### The parse trap the real files set

A `character` line inside a spawn is comma-separated and **the `unit` line
beside it is not**. Measured: 4,253 unit lines across both mods, not one with a
comma, every one carrying `exp`, `armour` and `weapon_lvl`. Splitting both the
same way gives units called `Clan Heralds exp 3 armour 0 weapon_lvl 0`.

`soldiers` is in the attribute list because **six of DaC's 3,822 lines carry
it** - `unit Moria Balrog soldiers 1 exp 9 armour 3 weapon_lvl 2` - and stopping
only at `exp` made those six "Moria Balrog soldiers 1", which were exactly the
six dead EDU references the join then reported. With it, DaC is clean on all
3,822. **The six false findings were what found the bug.**

### Three states a coordinate can be in, not one

Resolution has to account for every spawn or the misses look like a hole in the
reader. There are exactly three ways not to be in a province and all three are
real on the installed mods: **at sea** (by `map_heights.tga`), **on a colour no
record declares** (two of Shattered Alliances'), and **off the map** (none
found). The suite checks that the unresolved count never exceeds the three
together, on every installed campaign.

**And a spawn with no coordinate is not resolved at all**, which a test caught:
resolving one resolved the `(0,0)` its fields default to, which on a real map is
the bottom-left corner and usually ocean, so a missing field was being counted
as a spawn at sea. It is `no_coordinate` now and nothing else.

### What Reforged's Fellowship campaign says, reported and not judged

That campaign puts **45 of its 98 spawns on sea tiles carrying a land
character** - 20 named characters, 16 witches, 9 generals - and names **247 of
its 431 units** in a form its own EDU does not have, the commonest being "Mordor
Orcs Super" 40 times against a roster that has "Mordor Orcs". Its
`descr_strat.txt` does the same with 72 of its 150 characters. All of it is
counted and none of it is a verdict: it is somebody else's campaign, the reason
is not established here, and 32c's baseline rule says a tool that blocks on
another mod's state is one nobody opens twice.

### Built

`unittransfer/spawns.py` (`Spawn`, `script_paths`, `scan_text`, `scan`,
`resolve`, `positions`, `view`, `dead_units`, `export_text`, `export`,
`region_tiles`'s opposite number `_unit_name`, `XY`, `AFLOAT`, `COLUMNS`), a
`spawn` category in `marker_view`, `GET /api/map/spawns`, `POST
/api/map/spawn_export`, and in `campmark.js` the category, the hollow ring that
says "not there at turn one", and the tooltip line that ends in the file line -
because the script is read and never written, so the answer to "this one is
wrong" is the file and an editor.

**The export is a CSV, and that is the point of calling it one.** The map
screen's only export until now is 16g's per-faction TGA, which is right for a
picture and useless for 1,324 rows. It goes to the cache folder beside the query
exports; the mod is not touched.

### Verified

`tests/test_spawns.py` **41/41**, new, on a little script carrying every shape
the real ones have. Eight suites re-run green - `test_mapquery` 109/109,
`test_web_modules` 75/75, `test_campaint` 169/169, `test_recolour` 47/47,
`test_rebelpools` 68/68, `test_stratobj` 65/65, `test_campevents` 82/82.
`test_campmap` 108/112 and `test_campstrat` 96/100 are the DaC-build numbers,
**both identical on a stashed tree**.

Driven in the real app: the route answers for both mods, the markers layer
reports `spawn: 1324` beside its six other categories, the browser's own y flip
is checked correct against the index, the tooltip reads *"random_name · named
character · 6 units · Dol Guldur (poland) · line 4051"*, an admiral at sea reads
*"at sea (a fleet)"*, and the export wrote 1,324 rows and 176 KB of CSV into the
cache folder.

### 37b - T3, an FE zoom for authoring map_FE.tga - DONE 2026-09-16

**Closed 2026-09-16, beta line, committed and not cut.** The scoping named the
three things it needed - "the frame, the scale and the export at the size
`map_FE.tga` actually wants" - and was right that the frame comes first. What it
did not know is that there is no such thing as *the* size, and that the screen
had a defect in it that this phase turns out to be the fix for.

### There is no size map_FE.tga wants, and that is the measurement

**Eight files, six of them distinct, four distinct sizes, three mods, and not
one of them is its own map's shape.**

| file | pixels | aspect | its grid's aspect |
|---|---|---|---|
| DaC `imperial_campaign` | 768x768 | 1.000 | 1.047 (510x487) |
| Third Age Reforged, all three | 320x275 | 1.164 | 1.047 |
| DaC base, and Shattered Alliances | 245x170 | 1.441 | 1.047 |
| BCBuff, both | 384x275 | 1.396 | 1.448 (420x290) |

The closest, BCBuff's, is still 3.6% out. Reforged ships one file in three
places byte for byte; DaC's two 245x170 files are a different picture each; and
BCBuff's prologue spells it `map_fe.tga` in lower case.

**Two of the eight are not maps at all.** DaC's base picture is the "DAC EUR"
logo, mountains and lettering, and its Shattered Alliances one is four faction
emblems over the word "DaC". Neither has any geography in it. **And one of the
six that are maps does not fill its own frame**: BCBuff's is a map inside a
painted ornamental border, so the geography stops short of the edge on all four
sides. Nothing here detects any of that and nothing here should - 32c's
baseline rule again, and "is this a map" is not a question pixels answer.

### So the frame is the whole phase, and it is what makes one zoom enough

A front-end picture is a picture of **some rectangle of the map at some
scale**, and until that rectangle is named "native size" names nothing. The
frame is that rectangle, and it carries the **picture's** aspect rather than
the map's. That is not a detail: `cmapX(tx) = ox + tx * zoom` is a single
scalar, it stays a single scalar, and a frame shaped like the picture is
exactly what lets one number draw the picture at one image pixel per screen
pixel and leave the map under it undistorted. An anisotropic stretch would have
needed two.

**The default frame is not a guess - it is what the artists used.** Registering
each real picture against its own `map_regions.tga` by the moments of the two
land masks gives the scale that mod's author actually drew at. Against the
proposed frame: DaC `imperial_campaign` **1.506 px per tile proposed against
1.524 measured, 1.2% apart**; Reforged **0.565 against 0.566, 0.2% apart**.

One axis of each is quoted and that is deliberate. The land mask is taken from
colour; DaC's picture has a pale blue-green sea against tan land and separates
cleanly, Reforged's is a sepia painting whose sea and land are the same
parchment and the mask there reads 98.2% land. **A picture cannot be registered
from its own pixels in general**, which is the reason the frame is proposed and
then dragged rather than derived. The corner drag holds the aspect and holds
the opposite corner still, because a frame that stopped being the picture's
shape would quietly start lying about "native size".

### The defect it was really about, found by building it

T3's words are "no loss of quality due to scaling up and then scaling down
again", and that loss was **in this toolkit, every frame**. `cmapCompose` draws
every ticked layer into one canvas that is width-by-height *tiles* - 510x487 on
both big mods - and the view then scales that canvas onto the stage.
`map_FE.tga` has no relationship to the tile grid, so DaC's 768x768 was being
squeezed into 510x487 and scaled back up, and Reforged's 320x275 stretched up
and scaled back down.

The picture is out of the composite now and drawn on the canvas itself, one
`drawImage` onto the frame's rectangle. **Measured on the real screen: 100 of
100 sampled pixels of DaC's front-end map reach the canvas byte for byte
identical to the file, zero difference.**

### The second defect, which the browser found and the suite now holds

Lifting the picture out of the composite exposed one. The composite fills
itself with an opaque backdrop when no terrain layer is on - "a map with every
layer off is not a blank screen" - and that fill is drawn *over* the picture,
which is now underneath it rather than in it. With every other layer off the
front-end picture did not appear at all. The guard is two halves and the suite
checks both, because the skip without the cache key is a composite that never
rebuilds when the layer is ticked and the bug comes straight back.

### The export is the mod's own header

`mapquery._write_tga`'s rule, followed: the depth, the origin, the run-length
flag and the trailer are the file's own, so what comes out drops straight over
what went in - measured, DaC's writes RLE 32-bit and Shattered Alliances' raw
32-bit, each matching its source. A mod that ships no `map_FE.tga` has no
header to borrow, so a plain 24-bit one is made and the export says so, rather
than refusing an author their first one. It lands in the export cache, never in
the mod.

### Built

- `unittransfer/mapfe.py`, new: `Frame`, `frame` (the proposal), `check_frame`,
  `render` (composes at the picture's own size, cropping before it scales so
  the intermediate is bounded by the result and not by the zoom), `compare`,
  `view`, `header_for` and `export`.
- `web/js/mapfe.js`, new: the `cmFE` panel, the FE zoom, the frame's outline
  and grips, the drag that holds the aspect, and the export.
- `unittransfer/server.py`: `/api/map/fe_view` and `/api/map/fe_export`.
- `web/js/campmap.js`: the picture out of the composite, the backdrop guard and
  its cache key, `cfeDraw` under the stack, `cfeDrawFrame` over it, and four
  pointer hooks so a press on the frame takes the button off the pan - behind
  the brush, the pin and a character, which are all things somebody armed.

### Verified

`tests/test_mapfe.py` **75/75**, new. Six suites re-run green - `test_mapquery`
118/118, `test_web_modules` 75/75, `test_campaint` 177/177, `test_recolour`
50/50, `test_campaignmap` 32/32.

**Twelve suites fail on this tree and all twelve fail identically on a stashed
one**, with the same counts: `test_campmap` 125/130, `test_campstrat` 115/119,
`test_campview` 67/70, `test_mapterrain` 78/79, `test_rebelpools` 74/75,
`test_stratchar` 117/118, `test_stratobj` 73/75, plus `test_edbvocab`,
`test_guided_fields`, `test_mapcheck`, `test_renames` and `test_spawns`.
**A third mod is installed now** - BCBuff - and its `map_regions.tga` is 295x189
against a `descr_terrain.txt` that says 420x290, which is what raises
`test_spawns`' `MapError`. The numbers moved from the figures 37a recorded
because the mod set changed, not because anything here did.

Driven in the real app on DaC: the panel reads *768x768, 32-bit*, names the
file, says *"768x768 squeezed into 510x487 and scaled again"* about what the
screen used to do, proposes *510.0x510.0 tiles at 0.0,-11.5, 1.506 px per
tile*, and the FE zoom puts that frame on screen at **767.99982 px** - 1:1 to
two ten-thousandths of a pixel. Hit testing answers `move` inside, `se` on the
corner and nothing outside; a 50-pixel drag moves the frame 33.20 tiles at that
zoom; a corner drag grows both axes by 66.41, holds the aspect at exactly
1.000000 and holds the opposite corner at 0.000. The picture sits under the
stack and shows through in the overhang above the grid. The export wrote
`map_FE_imperial_campaign.tga`, 768x768, 32-bit, 545,779 bytes, through the
mod's own header.

## Phase 38 - descr_campaign_db.xml

304 lines, **281 distinct tags**, six documents in the archive, and nothing in
`unittransfer/` has ever named it. It holds every campaign-wide constant the
engine reads: piety mode, prisoner treatment, ageing, the settlement upgrade
thresholds, and **fort and watchtower cost and permanence**, which is the half
of permanent stone forts that 22a could not reach - `stratobj.py` places a fort
and cannot make it permanent.

**A generated form over the tree, not 281 hand-written fields.** The file is
small enough to hold whole and regular enough to render from its own shape, and
a hand-written form over a file this wide would be wrong for the first mod that
ships a tag we did not type. What it needs from us is the vocabulary: which
tags are numbers, which are booleans, which are enumerations, and what each one
does, and that is what the six archive documents are for.

**Subrelease, both lines.** This is a data file rather than a map file, so it is
a mode of its own and goes out on the 2.x line as well.

### Done 2026-09-17 - a tab of Minor Files, typed by the file

**The generated form held, and the file made it easier than the write-up
thought.** Every value is one attribute and the attribute's name is the type:
`uint`, `int`, `float`, `bool` and `string`, and nothing else on either
installed mod. So there is no vocabulary to supply for the *boxes* at all - a
tick for a bool, a checked text box for the rest - and a tag nobody here has
seen gets the right one. The vocabulary the write-up asked for is only needed
for what a tag *does*, and that is the part the archive can answer for a
handful and no more.

**Measured on the two mods now installed**, which are not the set the scoping
counted: Divide and Conquer is 303 lines and 262 tags, Reforged 256 lines and
217. The same 18 sections in the same order, no tag written twice, no element
text, no tag with two attributes. **25 tags are in DaC and not in Reforged**,
and one tag changes type between them (`crusade_called_start_turn`, `int` in
DaC and `float` in Reforged). DaC writes `float = "1.0"` with spaces round the
`=` on 19 lines; Reforged ends in CRLF. **There is no vanilla copy on this
machine**, loose or packed, so nothing can say "back to the game's value".

**ElementTree is the gate and not the parser.** It reads both files and would
write back neither: comments, the spaces round `=`, a tab before a comment and
the line endings would all be its own. The scan is line by line, a save
replaces the characters between two quotes, and **a save whose text
ElementTree cannot parse is refused**. Both real files round-trip byte for
byte with no findings.

**What the archive explains is fourteen tags, and those are the only ones with
words under them.** The forts tutorial gives `can_build_forts`,
`destroy_empty_forts` and `fort_fortification_level` - the permanence switch
22a could not reach is `destroy_empty_forts false`, and **both installed mods
already have it and have `can_build_forts false`**. The piety tutorial gives
the Britannia mode, `alternative_religious_unrest` and its three `alt_rel_`
values, printed whole; the ransom tutorial gives the captor and captive
chances, printed in a quote box too mangled to trust for a default. **A
documented tag the file does not write is offered as an add** only where a
document prints its line whole, which is seven of the fourteen: **Reforged
lacks all four piety tags**, DaC has them on. Nothing else is addable, because
a default nobody documented is a guess written into somebody's mod.

**Where it went.** A tab on the Minor Files strip, after Guilds, as a mode of
its own the way Guilds is, rather than a Campaign Map panel: it is not a map
file and it ships on the 2.x line. A section list on the left with changed
counts, the search box across every tag and note, the mod's own comment beside
its tag, and one Save that previews every change before it writes. Raw text
picks the file up with no change, because it reads `modfiles.KNOWN`.

**One shipped defect found beside it, by reading and not reproduced**: switching
mod inside Guilds cleared every other mode's state and not `state.gu`, so the
previous mod's guilds could still be on screen under the new mod's name. It is
cleared with the rest now.

New: `unittransfer/campdb.py` (`parse_text`, `check_value`, `check_file`,
`overview`, `plan`, `apply`, `VOCAB`, `CampDbPlan`), `GET /api/campdb`,
`POST /api/campdb/plan|apply`, the `campdb` entry in `modfiles.MODULES` and
`KNOWN`, `web/js/campdb.js`, the `campdb` mode and tab in `core.js`, the `.cdb*`
styles. `tests/test_campdb.py` 50/50, new; `tests/test_web_modules.py` 105/105.

## Phase 39 - The engine ceilings, on the screens that write them

TWCenter's *List of Hardcoded Limits* is **already harvested in five places**
and cited in the source each time: the 32-unit recruit limit and nine levels per
tree in `buildings.py`, three excluded ancillaries and eight effects in
`ancillaries.py`, 31 factions in `factions.py`, the trait thresholds in
`traits.py`, 200 regions in `mapcheck.py`. Two sets were never taken.

- **Every EDU ceiling, and `edu.py` has no value check of any kind.** 500 units
  in a mod, 100 per faction, 6 to 60 men and 31 for a general, HP 15, attack,
  charge, armour and defence 63, shield 31, three officers, three mount
  effects, two formations, 244 turns to build. The unit editor writes all of
  them and checks none, which makes this the largest unguarded surface left in
  the toolkit.
- **20,000 faces on a campaign-map model.** `cas.as_mesh` already counts the
  triangles, so this is a line on the Strat models panel, which Phase 29 got
  drawing again on 2026-09-12 - the dependency is discharged.

**A ceiling shows and never blocks**, the same rule the map baseline follows. A
mod already over one of these is somebody else's mod with somebody else's bug in
it, and several of these limits are ones M2TWEOP raises - `modflags.py` already
knows which mods are marked for it, and a limit that EOP replaces is reported as
replaced rather than as broken.

**Subrelease, both lines**, because the EDU half is the unit editor's.

### Done 2026-09-17 - the list was Rome's, and Medieval II's is shorter

**The document this phase was scoped from is the Rome: Total War thread.** Its
title is *[Modding] RTW: List of Hardcoded Limits*, its faction limit is 21 and
its hidden resources mention Rome and the Marian reforms. Built as scoped, its
"men per unit, max 60" flagged **300 of DaC's units and 113 of Reforged's**,
on two mods that play. The five places that harvested it before had adapted
their numbers (31 factions, not 21); the EDU half never was.

**So every number now has a Medieval II source in the archive, and the rest are
not checked.**

| ceiling | source |
|---|---|
| 500 units in the file (M2EX lifts it) | *A Beginner's Guide to the Export_Descr_Unit* |
| 4 to 100 men | the same guide ("the smallest possible is 4, the largest 100") |
| attack capped at 63, either weapon | the same guide |
| up to three officers, three mount effects | the same guide |
| two formations, one square or horde and one shield_wall, phalanx, schiltrom or wedge | the same guide |
| stat_health 0 to 15, both values | *M2TW Ultimate Docudemons 5.3*, Character Attributes |

**Not checked, because only Rome's list says so:** charge, armour and defence
63, shield 31, 244 turns to build, 100 units a faction, 31 men in a bodyguard.

**Measured with the Medieval II set:** DaC 29 of 924 units (20 over 100 men,
8 secondary attacks over 63, 2 HP), and its 924-unit file is lifted because it
is marked M2EX; Reforged 6 of 427 - the Mumakil at 30 and 25 HP, Stone Giants
at attack 100 and 20 HP, a ballista at attack 100, and two units whose
formations are `square, horde`.

**The 20,000-face campaign model limit is dropped too.** It is the same RTW
list, and DaC ships three strat models at 30,252 faces - its evil Minas Tirith
among them. The count itself was already there: the 3D viewer prints vertices
and triangles for every model it opens, strat ones included, so that half
needed no code.

**Where it shows.** The unit editor's EDU fields tab carries a *Past the
engine's ceiling* note naming each document, and a save's preview warns about
a ceiling **the edit crosses** and not one the unit was already past. Nothing
is refused. `too-many-units` joined `modflags.CAP_FINDINGS`.

New: `unittransfer/educeil.py` (`unit_findings`, `mod_findings`, `report`),
`ceilings` and `roster_ceilings` on `edit.unit_detail`, the warning in
`edit.plan_edit`, `edCeilHtml` in `editor.js`. `tests/test_educeil.py` 24/24,
new; `test_edit` 60/60, `test_modflags` 22/22, `test_codeview` 141/141.

## Phase 40 - The new province the engine cannot read - DONE 2026-09-13

**Closed 2026-09-13, both lines, committed and not cut. It was four defects,
and the scoped one was the smallest of them.** The write-up below is kept with
its three wrong premises corrected in place, because what it got wrong is the
useful part of the record: every one of the three was an inference the repo
could not check, and the mod on this machine could.

**The scoped fix, and it is one line.** `campaint.new_record_lines` wrote the
resources line only when the user picked a resource, so a province created
without any reached `descr_regions.txt` as an eight-line record in a file of
nine-line records, and the engine reads that file by position. It always writes
the line now, `none` when the list is empty.

**Wrong premise 1: "not one of the 510 records uses the literal `none`".**
Measured over the five `descr_regions.txt` installed here, `none` is the
ordinary way to write the empty case: **vanilla 18 of 112, Vanilla Redux 78 of
252, `vanilla_kingdoms_uncompromised` 853 of 853**. So `none` was never a
choice this repo had to make - it is what the files this writes beside already
do, and the fix is smaller than the write-up thought.

**Wrong premise 2: "not one of the 510 records leaves the resources line
out".** Divide and Conquer's last record, `lol`, has **662 painted tiles** and
no resources line. It is a real short record in the wild, in the mod the user
plays.

**Wrong premise 3, and the important one: the engine crash.** It was inferred
from the format being positional and from the records agreeing, and the write-
up asked for a run in the game before the fix. **That run is not owed: DaC
ships the short record and the mod plays.** The claim is withdrawn. This does
not weaken the fix - writing the record in the shape the rest of the file is
written in is the same rule `new_record_lines` already followed for the indent
and the `legion:` line - but nothing here says it is a crash any more.

**Which settles the severity of the new check.** `campmap.check_record` takes a
third argument now, `campmap.file_shape(rf)`, and reports a record missing a
positional line its neighbours write. It is a **warning**, for two measured
reasons: DaC ships such a record and plays, and `plan_region` turns a fatal
finding into a refusal, so fatal would have trapped the one person able to fix
it - **the save is what rewrites the record**. It fires once across the 1,616
records installed here.

**The shape of a record is not its line count**, and that is the distinction
the phase turns on. `legion:` is keyed rather than positional and half the mods
write one; comments and blank lines sit inside a record's span; DaC's records
run to ten lines where vanilla's run to nine. `file_shape` counts which of the
unkeyed lines each record has, because that is what the engine reads off
position. `SHAPE_FIELDS` has one member and that is measured rather than an
oversight: the parser already puts a `problems` entry on a record missing its
religions line or its two bare numbers, a record with no settlement is the
wasteland form and has its own rule, and `legion:` shifts nothing. The
resources line is the only one that goes missing in silence.

### The three the write-up did not have

**The same eight-line record was reachable from the panel.**
`campmap.render_block` **dropped** the resources line when the last resource was
cleared off a record. Same defect, other direction, and `tests/test_campedit.py`
had a check asserting it as correct behaviour. It writes `none` now.

**`none` was read as a resource named `none`.** That is "neither a hidden
resource the EDB declares nor a trade resource descr_sm_resources.txt names" on
**931 records** - all 853 of `vanilla_kingdoms_uncompromised` and 78 of Vanilla
Redux - and `none` listed among a province's hidden resources in the query
table. A lone `none` is the empty list now; `none, gold` is still two
resources. The line on disk is untouched, so every installed file still
round-trips byte for byte, and `web/js/campmap.js` already drew the word "none"
under an empty chip list.

**And the largest: Divide and Conquer has 200 regions and this read 199.** DaC
writes one name line with a stray leading space, ` Erebor_Province`. The indent
is the whole of the first reading, so that line was body, `Withered_Province`
swallowed Erebor whole as a twenty-line record, and **it reported no
problems**. Erebor's **517 painted tiles** came out of here as land declared
nowhere: no name in the hover, nothing to click, a fatal `region.undeclared`,
and its settlement marker counted as an orphan. That orphan had been **written
down as a fact about DaC** in `RegionIndex.orphan_settlements` ("a province
painted on the map and never written down") and asserted in
`tests/test_campmap.py` as `== [(339, 65)]`. It was a fact about this module's
reader, and it had been sitting in the source as evidence for the opposite
conclusion.

`campmap._resplit_runs` re-splits any record holding **two colour lines**,
which is a signal no well-formed record can give - a record's other lines are
words, single numbers or braces, and only `R G B` is three numbers - so the
re-split is per record and a file the indent reads correctly passes through
untouched. `parse_block` gained a second reading for the one record whose own
name line is indented, since `record_text` hands out the file's own bytes; a
block that has genuinely lost its name line is still refused, because its
settlement would be the line read as the name and the retry is rejected unless
the result is a whole record.

### Verified

All **1,504** records of the four installed mods go `record_text` ->
`parse_block` -> `render_block` unchanged, and all five files round-trip byte
for byte. `tests/test_campaint.py` has sections 4c and 4d (**185/185**, was
168), `tests/test_campmap.py` section 1 has the run-on record (**143/148**
against 136/141 stashed - the same five DaC-build failures), and
`tests/test_campedit.py` is **139/139** against 138. **Eighteen suites were run
against a clean checkout of the last commit as well as against this tree and
every failing check name is identical in both.**

**One check left as it is, deliberately.** `test_campview` asserts "the other
undeclared colour is the 517-tile province - the hole 16a found, now measured".
That is Erebor, and it is declared now, so the sentence describes a bug that is
gone. The check fails on this DaC build either way, for the hard-coded numbers
beside it, so rewriting it would not turn it green: it belongs with the other
DaC-number checks and wants the build sorted out, not a new assertion.

**Both lines.** It is a defect in a shipped feature, so it is a 2.x subrelease
as well as a beta when a cut happens.

## Phase 41 - Merge one faction's name pool into another - DONE 2026-09-15

**From Mylae's `187d9ed`, and the one genuinely new idea in that push.** His
`MergeNamesModal.jsx` takes any number of source factions and merges their
`descr_names.txt` lists into the selected one, previewing per section what is
new, what is already there and what the total becomes.

**We had the reporting and none of the action.** `minorfiles.check_names`
already finds a name repeated inside a section and names both lines, which is
better than his bare count; `factionclone.clone_names` copies a whole donor
block verbatim as part of cloning a faction, with no dedupe and no merge. There
was no way to pull one faction's surnames into another's without retyping them,
and no way to clear the **153 duplicate-name findings** the four installed mods
produce.

### The engine, and it is the size the scoping said

`merge_section(target, sources, dedupe, sort)` returns the merged list plus the
counts that **are** the preview, and it sits in `minorfiles.py` beside
`check_names`, behind that module's existing `plan`/`apply` pair - so a merge is
previewed, backed up and undone like every other write there. Above it,
`merge_names` does all four sections against any number of donors, and
`merge_block` writes the faction's block back.

**Four sections, not three.** `NAME_SECTIONS` is `settlements`, `characters`,
`surnames`, `women`. Mylae's serializer writes only the last three and silently
drops `settlements`; none of the installed mods uses that section, which is why
he has not noticed. Ours carries it through untouched.

**Three things of his deliberately not copied**, and each is a check in the
suite:

* his preview labels source duplicates "skipped" even when dedupe is off, and
  with dedupe off they are in fact **appended**. `present` here is zero whenever
  nothing was skipped, because a count that is not true of the write is worse
  than no count at all.
* his Merge button is live with no source selected, where the only thing it can
  do is dedupe in place. That is a real action, so it is its own button and its
  own `action="dedupe"`; merging nothing is refused and the refusal names the
  button that does do it.
* his serializer drops `settlements`, as above.

**A section only the donor has is created rather than dropped.** `render_names`
refuses a section the faction has not got, which is right for an edit - the form
cannot show a box that is not there - and wrong for a merge, where the whole
point can be that the donor keeps a `surnames` list and the target keeps none.
`merge_block` writes the heading at the end of the block, indented to match the
sections the target already has and with the blank line every real file puts
between sections. It is appended rather than spliced into canonical order,
because moving lines past comments and blank lines a mod put there buys nothing:
the engine does not care what order the sections come in.

### The defect this turned up, which is bigger than the phase

**Phase 41's own suite could not run.** `test_minorfiles` died in the real-mod
sweep on `Owaib Cyfeiliog`, and had been dying there since the two vanilla mods
were installed. Nobody had seen it because **stderr and buffered stdout
interleave**: the traceback landed in the middle of the output and the suite
merely looked like it had one failing check. That is also why the 2026-09-14
sweep listed `test_minorfiles` as failing with no check count.

`render_names` refused any name with a space in it. Measured over the four
installed mods:

| section | entries | multi-word | share |
|---|---|---|---|
| `characters` | 18,794 | 90 | 0.5% |
| `surnames` | 5,363 | **2,413** | **45.0%** |
| `women` | 10,766 | 10 | 0.1% |
| **total** | **34,923** | **2,513** | |

`surnames` is where it is normal - `de Avena`, `of Anglesey` - because the
engine joins a forename to one of these and `de Medici` is a surname rather than
two names. But `characters` and `women` have them too and they are not mistakes:
`al Adid`, `Imad ad Din`, `Arigh Boke`, `Yax Kuk Mo`, `Hywel Dda`,
`Sorghaghtani Beki` - Arabic, Mongol, Mayan and Welsh names that are two words
in the histories they come from.

**What it cost while it stood: 58 factions across Vanilla Redux and
`vanilla_kingdoms_uncompromised` could not be saved at all.** `render_names`
refused the very list the form had just handed it, unchanged. And `parse_names`
raised 2,513 warnings about files that are perfectly correct. All 121 factions
of all four mods save now.

**The rule is replaced by the one real constraint.** A name may not BE a section
keyword, because `parse_names` tells a heading from a name by those four words
and would read it back as a heading, moving everything under it into the wrong
section. No installed mod has one, over all 34,923 entries. It lives in one
function, `name_fault`, because the old rule was enforced in three places and
was wrong in all three.

**The first draft of this fix relaxed the rule for `surnames` alone**, on a
sample that happened to be all surnames. That was the same mistake one size
smaller, and the per-section count above is what caught it. The comment in the
source says so, because the next person to read that table should know it was
read wrong once already.

`test_minorfiles` had `a name with a space in it is refused` asserted as an
expectation - the defect written down, the same shape as the `test_campedit`
check Phase 40 found.

### Verified

* `tests/test_minorfiles.py` **221/224** against 153 green with a crash before.
  The three counts are measured in both dedupe modes; the dedupe-off case is
  checked **first**, because it is the one his preview gets wrong. The plan's
  four refusals are checked. A merge is applied to the fixture mod and undone,
  with every faction it did not name byte for byte on both sides.
* Measured on the real mods, written nowhere: dedupe of DaC's `russia` is 78 ->
  72 characters and its 6 duplicate findings become 0, with the other 30
  factions untouched. Merging Vanilla Redux's `papal_states` into `slave`, which
  has no `surnames` section, writes the heading and 116 names. Merging the same
  source twice reports every name present and writes nothing.
* Driven end to end through the running server on Vanilla Redux: `egypt` merging
  `turks` and `moors` previews `characters 80 -> 207 (127 new, 3 already
  there)`, `surnames 55 -> 246`, `women 36 -> 116`; turning Remove duplicates
  off reports 130 added and **0** already there, which is the correction to his
  preview shown in the app; unticking every source disables Merge and says what
  to do.

### Three findings handed on, all in `descr_sm_resources.txt` - CLOSED 2026-09-15

The crash was hiding the end of the sweep, and behind it were three failures
with nothing to do with names. They were handed on as their own job and done the
same day; **`test_minorfiles` is 225/225**, green for the first time.

**`localised_name` turned out to be the answer to a bug rather than a keyword to
tolerate.** Neither it nor `is_slave` appears anywhere in `Reference/`, so both
were measured off the mods instead. `is_slave` is a bare flag on the `slaves`
record, the same shape as `has_mine`. `localised_name` takes a text tag, and the
two mods that write it use it for **exactly the three resources whose tag
`resource_tag` was deriving wrongly**: `camels`, `elephants` and `dogs` are
keyed `SMT_RESOURCE_CAMEL`, `_ELEPHANT`, `_DOG` - **singular**, where every other
resource including `slaves` matches its own plural name.

So the Resources tab had been showing **no name at all for those three in every
installed mod**, while reporting nothing wrong: "The Carrock", "Beacon of
Gondor" and "Horses" in Divide and Conquer, "Mumakils" in Reforged, plain
"Camels" / "Elephants" / "Dogs" in the vanilla one. `resource_tag_of(rec)` takes
the file's own answer first and falls back to the derivation, which now knows
its three exceptions; `SINGULAR_RESOURCE_TAGS` carries the measurement.

**And the 31-resource mod strengthens the edit-only refusal rather than
disproving it.** `vanilla_kingdoms_uncompromised` ships the 28 plus `glass`,
`honey` and `salt`, and the premise the refusal was written on - *all three mods
measured ship the same 28* - is indeed now three of four. But the reasoning
under it held: those three names appear in **exactly one file in the whole mod,
their own definition**. Nothing places them on the map, no other file in `data/`
mentions them, and `strat.txt` gives them no name. A `type` the engine does not
know is read and ignored, and a mod has now demonstrated it. The behaviour
stands; the sentence was what needed fixing.

The suite's `every real resource name is one of the 28` asserted that no mod
would ever add one, which is not the fact worth guarding. It now asserts the two
that are: all 28 are defined by the installed mods, and every name beyond them
is dead.

**Both lines.** `descr_names.txt` is a minor file rather than the campaign map.

## Phase 42 - The art a clone does not get, and is not told about - DONE 2026-09-14

**Reported by a beta user on 2026-09-12: cloning a faction leaves its symbols
missing under `data/menu/symbols/fe_buttons_24`, `fe_buttons_48` and
`fe_symbols_80`.** The report is real. The cause is not the one it sounds like.

**The copier is not at fault, and that is measured.** `menu` is already one of
`factionclone.ART_ROOTS`, and `_asset_hits` was run over **all 31 Divide and
Conquer faction slots**: it finds every symbol file in all three folders for
every slot, misses none, and correctly resolves the longest-slot rivalry (no two
DaC slots contain each other, so nothing is being eaten). `want_art` defaults to
`True` in `plan` and the dialog's checkbox ships checked. `apply` copies each
file and lists it in the undo manifest. **Re-measured on 2026-09-14 and all of
that held.**

**What is actually wrong: the clone gets only what the donor has, and says
nothing about the rest.** The scoping's four-folder table came back exactly:

| folder | Divide and Conquer | Third Age Reforged |
|---|---|---|
| `fe_buttons_24` | 29 of 31 slots | 30 of 30 |
| `fe_buttons_48` | 29 of 31 slots | 30 of 30 |
| `fe_symbols_80` | **17 of 31 slots** | **0 of 30 slots** |
| `fe_faction_units` | 28 of 31 slots | 28 of 30 |

**One fact under it was wrong, and the conclusion survives it.** The scoping
said Reforged's `fe_symbols_80` holds 17 files named for vanilla slots it no
longer uses. It does not: **Reforged's copy of that folder is empty.** The 17
vanilla-named files - `egypt`, `england`, `france.TGA`, `hre`, `ireland`,
`milan` - are **Divide and Conquer's**, and they are 17 of DaC's own 31 because
DaC keeps the vanilla slot names and puts LOTR factions in them. Same
conclusion either way: cloning any Reforged faction copies nothing into
`fe_symbols_80`, because the donor has nothing there to copy.

**The tool's one warning cannot fire here.** `plan` warns only when the whole
scan comes back empty:

```python
p.warnings.append(f"no art was found carrying `{src}` in its name - ...")
```

Banners, captain cards and unit-card folders are always found, so the list is
never empty and the warning never fires, however many individual locations came
back with nothing.

### What was built: the per-location report

`ART_PLACES` is the nine places a faction's art lives, each with a label, a
sentence saying where it shows up in the game, and whether the slot is in the
file's own name (`symbol24_sicily_roll.tga`) or is itself the folder
(`ui/units/sicily/`). `art_gaps` names every one of them the clone came away
from empty-handed, with **which of four reasons** it was:

* `donor` - the donor has nothing here either. Nobody can copy it and the art
  has to be drawn. **This is the reported case.**
* `exists` - the mod already ships a file of the new name here, so it was left
  alone. Never overwriting is the right call; saying nothing about it was not.
* `rival` - the only files here carrying the donor's name belong to a
  longer-named faction, so none of them is the donor's.
* `absent` - the mod has no such folder at all.

None of the four is a copier bug, which is why this is a report. `_asset_hits`
grew an optional `skips` list so the two decisions it used to make silently -
the rivalry skip and the `dst_path.exists()` skip - can be read back.

### Nine places, four mods, and the report is far wider than the report was

The scoping measured four folders on two mods. Measured across nine places on
all four installed mods, sweeping **every one of the 121 faction slots** as a
donor: **253 places come back empty**, and only **50 of the 121 donors** get
art everywhere.

| mod | slots | donors with every place filled | empty places |
|---|---|---|---|
| Divide and Conquer | 31 | 16 | 33 |
| Third Age Reforged | 30 | **0** | 63 |
| Vanilla Redux | 25 | 21 | 11 |
| vanilla_kingdoms_uncompromised | 35 | 13 | **146** |

**Not one of Reforged's thirty factions is a donor that fills every place.**
All 30 miss the 80px symbol, 16 miss the captain card, 9 miss the battle
banners, 5 the unit information cards. And `vanilla_kingdoms_uncompromised` is
worse than any of them: 22 of its 35 donors miss the 24px button, the 80px
symbol, the in-game faction symbol and the battle banners, each.

**Every one of the 253 is the `donor` reason.** Not one real mod produces
`exists`, `rival` or `absent` from a clone - which is worth knowing rather than
worth hiding, so all three get a fixture instead of a claim. `exists` is the
leftover-art case: a mod that still ships a file named for a faction it no
longer has, cloned into under that same name.

**And one thing measured on the way past that is worth writing down: the repair
path copies no art at all.** `factionaudit.repair_plan` (21's D6) builds its
`ClonePlan` by hand and never calls `_asset_hits`, so a repaired faction gets
the records it was missing and none of its symbols - and therefore has no gaps
to report either. That is correct rather than a defect, because repair is about
the records a faction is missing and not its pictures, but it is not what the
module's shape suggests at a glance.

### Verified

* `tests/test_factionclone.py` **74/74** against 64 before. The report has to be
  *exact*, so both directions are checked against the real mod: no place is
  reported empty that the clone got art in, and no place the clone got nothing
  in is left unreported. Each reason is then checked against the disk rather
  than taken on trust - a place reported `absent` really is not in the mod, a
  place reported `donor` really has no file carrying the donor's name.
* `tests/test_factionclone_apply.py` **39/39** against 30. A second synthetic
  mod produces all four reasons at once, and proves the `exists` skip does what
  the new sentence says: the file that was already there is byte for byte
  untouched after the write, and it is **not** in the undo manifest, so undoing
  the clone cannot delete a file the mod owned before it.
* One thing the fixture taught: a new name that **carries the donor's token**
  (`sicily` -> `sicily_two`) is picked up by the scan as if it were the donor's
  own art. It is unreachable through the app - `_validate` refuses a name
  already in the roster, and the repair path has the name in the roster where it
  wins the longest-slot rivalry and is skipped - so it is a note, not a fix. The
  fixture clones to `norman` for exactly that reason.
* Driven end to end through the running server on Third Age Reforged: cloning
  `aztecs` names four places with their reasons in the dialog, the header reads
  `11 file(s), 54 art file(s), 5.4 MB - 4 art place(s) empty`, and no console
  error anywhere.

### Two smaller things found in the same measurement

Both were in the scoping and both are still true, and both are left alone
deliberately. DaC ships a nested
`menu/symbols/fe_buttons_24/fe_buttons_24/` whose four files are picked up as
separate items and copied into an equally nested destination - faithful to the
mod, and a place still counts as filled when its hits came from inside the
nest, so inventing a rule to flatten it would be this module guessing at a
mod's own layout. And `fe_symbols_80/france.TGA` has an upper-case extension,
which the rename handles because `swap` only touches the matched slot token.

### Still open: the reporter's own mod

**The end-to-end reproduction against the mod in the report was not done, and
the user does not have the detail.** Everything above is measured against the
four mods installed here and driven through the running app on one of them.
The report may still turn out to be a different mod, an older build, or a
second cause on top of this one - and if a second cause exists, this report is
what will show it, because a clone that comes back with **no** empty places and
still has a blank button is a different bug from the one closed here.

**Both lines.** The faction clone is not the campaign map.

## Phase 43 - Playable, unlockable, not playable - DONE 2026-09-15

**Almost all of this was already built, and the write-up did not check.** 16j
shipped the roster writer: `stratcamp.plan_campaign` has taken `what="rosters"`
since it landed, `_roster_splice` replaces each of the three lists where it
stands, `roster_block` keeps the indent the block's own entries use, and the
Who plays tab in `web/js/stratcamp.js` has been a three-way radio per faction -
`cjRoster` - not three editable text lists. Order, indentation, the per-campaign
rule and the backup-and-undo ride were all done and all under test: part 4 of
`tests/test_stratcamp.py` moves a faction between two lists and part 5 saves
and undoes one on a real mod byte-exact.

**"Missing four times over" misread four guards as four refusals.** The line
*"this would change the playable, unlockable or nonplayable lists"* in
`stratcamp.py`, `stratchar.py`, `stratedit.py` and `regiondel.py` is each
writer refusing to touch a roster it was not asked about - a settlement edit,
a character edit, a delete - and every one of them is correct as it stands.
`stratcamp._guard` already exempts the three saves that may move a name:
`rosters`, `create` and `delete`. There was no writer owed.

**One thing was genuinely missing, and it is the sentence about the refusal.**
`camp.no_playable` was a warning, so a save that moved every faction into
`nonplayable` went through with a note. It is fatal now - but only when the
save is what empties the list. `check_rosters` takes the lists the save started
from as a third argument and reads nothing else from them: passed nothing, which
is what the campaign panel does, an empty `playable` list is still reported and
no more, because reporting is all a read can do.

**That split is 40's ruling applied a second time.** A flat fatal would refuse
the save of a campaign that already had no playable faction, and that is the one
file where this screen *is* the repair - moving a faction back is the same radio
button - so it would have trapped the only person who could fix it.

**Measured, not assumed.** All six campaigns on this machine write at least one
playable faction: the four installed mods' imperial campaigns at 26, 27, 31 and
18, vanilla's at 5, and the Norman prologue at exactly one. The prologue also
writes an `unlockable` block with nothing in it at all, which is why an empty
list is a shape the writer keeps rather than a state it refuses.

`tests/test_stratcamp.py` is **114/115** against 112/113 before, three checks
added for the three severities. The one failure is not this: Vanilla Redux
writes `random_persona_weights 15 42 25 18` on its campaign header, `stratcamp`
does not know the word, and the header-words check has been red on that mod
before this phase. The line survives a round trip - `serialise` hands back the
file's own bytes - so it is a gap in what is *reported*, the same shape as
`marian_reforms_activated`, and it is not scoped here.

The original scoping follows.


**Asked for by the user on 2026-09-12.** `descr_strat.txt` opens with three
rosters that decide which factions the campaign offers, and the toolkit reads
all three and will not write any of them.

What is already here: `campstrat.ROSTERS` is
`("playable", "unlockable", "nonplayable")` and the parser keeps each block's
line span; `campbrowse.js` prints the three counts on every campaign card;
`stratcamp.py` has a `camp.no_playable` finding for a campaign that offers
nobody; and `renames.py` follows a faction through all three when its slot is
renamed. So the data, the display and the rename are done.

What is missing is the edit, and it is missing **four times over**, in the same
words - `stratcamp.py`, `stratchar.py`, `stratedit.py` and `regiondel.py` each
refuse with *"this would change the playable, unlockable or nonplayable
lists"*. Four refusals of the same shape is the signal that one writer is owed,
not four.

**The shape.** A faction is in exactly one of the three, so this is a
three-way toggle per faction rather than three lists to edit - the writer moves
a name out of the block it is in and into the one asked for, keeps each block's
existing order and indentation, and refuses the one state the engine cannot
take: no faction playable at all, which is `camp.no_playable` already written
down. It rides `stratedit`'s existing plan/apply and backup set like every other
`descr_strat.txt` write, and the four refusals above become calls into it.

**Per campaign, not per mod.** Each campaign has its own `descr_strat.txt`, and
a faction playable in the imperial campaign need not be playable in another.

**Mylae has this** - `repBlock('playable' | 'unlockable' | 'nonplayable', …)` in
his `serializeDescrStrat` - and his version rewrites the whole block from an
array. Ours should move one name and leave every other byte alone, which is the
difference between the two tools everywhere else in `descr_strat.txt`.

**Beta only.** `descr_strat.txt` is campaign-map work.

## Mylae pushed on 2026-09-12, and this is what came

**Superseded: the block of 2026-09-12 is lifted.** That entry said his improved
validation and coloured overlays were not on GitHub and that
`Machiavello-1441/m2tw-editor` was still at `2740b0b`. He pushed three commits
the same day and `upstream_sync.py sync` has them: `2740b0b..187d9ed`, 7 files.

* `11e3eb9` - base44 vite plugin 1.0.35 to 1.0.36. Cloud plumbing, `skip`.
* `920841a` - the `map_features.tga` rewrite. **Phase 31**, and it changed that
  phase's scope rather than adding to it.
* `187d9ed` - the names merge. **Phase 41**.

**What he described is still not here.** The settlement-position validation and
the coloured overlay exports for religion, creator and owner are in neither
commit. Ours already judges a settlement position on four rules -
`marker.ground`, `marker.feature`, `marker.sea` and `marker.orphan` - and since
22b a refusal also names the nearest tile that would do, through
`mapsnap.nearest`, which is more than an alert. His overlays are 16g's
colourings and the per-faction TGA export. Ask for those files rather than
scoping from the sentence; re-run `sync` before scoping anything else.

**Two things to pass back to him**, both found while diffing this push: his new
orphan-white-source check is an `error` and vanilla trips it at image (175,14),
and the standalone `map_features_checker.py` he ported from cannot open either
installed map because both ship RLE TGAs.

---

# Phase 54 - M17, one door to every check - DONE 2026-09-22

First in the five-star queue. The complaint is ours and it is still true: we
have more validators than any of the four reference tools and no single place
that runs them. Somebody whose mod crashes has to know that the map screen,
the faction audit, the buildings screen, the battle-models screen and three
file editors each hold part of the answer.

### What exists, measured

Eighteen validators, in three shapes:

- **The rule shape.** `mapcheck.Finding` (86 `@rule`s, the six `merc.` rules
  among them) and `buildings.EdbFinding` (nine `@edb_rule`s, Phase 44): a code,
  `fatal`/`warn`/`note`, a message, and a `what` that never holds a line number.
- **The file checkers.** `check_file` in traits, ancillaries, guilds, campdb,
  factions and winconds, `minorfiles.check_any` and `educeil.mod_findings`.
  Close to the rule shape but not on it: some say `fatal: bool` through a
  local `finding()` helper, some say `kind` and nothing about severity.
- **The cleanup audits.** bmdb, dupes, stratmap and cards. These return buckets
  (unused, orphans, twins, strays), not findings. They are about a tidy mod,
  not a mod that starts.

**Cost, cold, on the two installed mods** (DaC, ROCSS): mapcheck 0.9s / 2.8s,
the faction audit 1.3s / 1.2s, the EDB checks 0.2s / 0.2s. Then bmdb 10.5s /
27s, dupes 7s / 19s, stratmap 7s / 16s, and **cards 24s / 95s**. That split
decides the screen: the first group runs when it opens, the second is a tile
that says what it would look for and starts on a click.

### The two crash guides are the checklist

`Reference/TWCenter/GUIDE - Crashes and how to fix them.pdf` and `Crash to
Desktop - TWC Wiki.pdf` list about forty causes between them, and almost every
one names a file and can be read off it. What they add that no validator here
has is **when** it bites: at launch, at campaign load, at the first turn, in
battle, when a panel is opened. That is how somebody arrives with a crash, so
it is how the screen is grouped.

### 54a - the door

- `unittransfer/health.py`: a registry of **sources**, each an adapter from one
  validator's own answer to one finding shape: `source`, `code`, `severity`
  (`fatal`/`warn`/`note`), `message`, `file`, `line`, `what`, `when`, and where
  to open it. A source that throws is reported as a source that failed, never
  as an empty one and never as the whole screen failing.
- `GET /api/health?mod=&campaign=` runs the fast sources. The slow ones are
  listed as doors into their own screens.
- A **Health** screen: fatal first, grouped by when it crashes, every row
  opening the screen that owns the finding. The existing screens keep their
  panels; this is a door, not a second copy of any rule.
- A test that runs every source over both installed mods and holds each
  adapter to the shape.

### 54a done 2026-09-22 - ten sources, one list, and a door into each screen

Built as scoped except one line: the cleanup audits keep no session result to
show. They are listed with what they cost and open their own screens, which
already show progress; a cached answer from twenty minutes ago would be the
one number on the page nobody could trust.

**Ten sources**: the map rules (off where the map screen is), the faction
audit, the EDB tree and recruitment checks, the EDU ceilings, traits,
ancillaries, `descr_sm_factions.txt`, guilds, campaign constants and the five
Minor Files tabs. DaC reads 5 fatal, 158 warnings and 95 notes in about 3s;
ROCSS 2 fatal, 120 warnings in about 5.5s, nearly all of it the map rules.

**Severity from the checker's own sentence.** Traits, ancillaries and factions
give a `kind` and no severity. A table here would be a second list to forget;
their messages already say "crashes the game", "the game stops loading the
file", "will not load this ancillary", and `health.severity_of` reads that.
`tests/test_health.py` holds it to sentences the checkers really write.

**One measurement changed the shape.** DaC's recruitment checks are 2 151
notes unit by unit, which buried the five fatals under them. They fold to one
note per building line with a count (95), and notes start hidden.

**Two defects found by building it.** My changes (52) never hid the unit
editor's filter sidebar, and neither did Health until it was added to the same
list. And a Health row for a guild that exists only in triggers lands on the
Guilds screen without a record picked - which is right, there is none, and the
row says so.

Exit: `unittransfer/health.py`, `GET /api/health`, `web/js/health.js`, a
Health entry in the menu, `tests/test_health.py` (40 checks).

### 54b - what the guides name and nothing checks

Measured on both mods before any of it is written, on Phase 12's rule that a
count from a wiki is not a fact about a mod. The candidates: an event a script
or the EDB fires that `historic_events.txt` does not declare; an `ai_label` in
`descr_strat.txt` missing from `descr_campaign_ai_db.xml`; a trait culture-
excluded while its antitrait is not; absolute paths in `descr_banners_new.xml`
and the projectile and standard files; runs of spaces in the modeldb; a
faction a building's early level omits and a later level names.

### 54b done 2026-09-22 - five rules, and two of the guides' claims refused

All six measured on DaC and ROCSS first. Five ship in `unittransfer/crashrules.py`
on `mapcheck`'s `@rule` shape, as an eleventh Health source; the finding rows
open the file at the line in Raw text, or the trait.

- **`ai.label_unknown`, fatal.** DaC's only undeclared label is `papal_faction`,
  in both campaigns, and DaC plays: it is the engine's own and is exempt.
  ROCSS ships no `descr_campaign_ai_db.xml`, so the game's is used and the rule
  does not run.
- **`event.no_text`, a warning, matched case-blind.** The guide says the match
  is case-sensitive; **631 of DaC's 633 script events differ from their key only
  by case, and DaC plays.** Read through `campevents.event_text_pairs`, which
  takes the `.bin` too, four are left, all on Shattered Alliances, one of them
  called `crash_game`. DaC ships them, so not the guide's CTD.
- **`trait.antitrait_cultures`, fatal.** None in 6 pairs on DaC or 323 on
  ROCSS: a crash rule that finds nothing on a shipping mod, as it should.
- **`path.absolute` and `modeldb.spaces`, warnings.** None on either mod.

**Refused: a faction a later building level names and an earlier one omits.**
DaC has 24 such levels in 14 lines and ROCSS 6 in 4, and both play. It and the
case-sensitivity claim are `crashrules.REFUSED`, and Health shows them in a
folded section so they are looked up, not rediscovered.

One defect of the building: counting newlines up to every script match made the
event rule 10.7s on ROCSS's eight campaigns. It counts only for a finding now
(1.6s). Exit: `tests/test_health.py` section 6, a fixture per rule and both
mods held to no crash-rule fatal (51 checks).

**Phase 54 is done.**

---

# Phase 55 - M16's playback half: a battle model that moves - 55a DONE 2026-09-22

Asked for by a tester ("the bmdb editor does not show the animation for the
model"). It is the backlog row *M16, the playback half*, rated M on the belief
that `cas.py` already reads the container. **Measuring said otherwise, twice:**

- **`cas.py` does not read an animation file.** It reads model `.cas` files;
  the first of DaC's animation files it was given
  (`animations/engine/ballista/ballista_stand_to_crank.cas`) fails at byte 680,
  a zero-length chunk, because an animation is a different layout. No document
  in `Reference/` describes it, so the reader is reverse-engineered from the
  files: per-bone keys, the time base and whatever quantisation it uses.
- **Where the files are depends on the mod.** DaC ships 1 753 unpacked
  animation `.cas` files; ROCSS ships 10; the base game none - vanilla's live
  in `animations/pack.dat` and `skeletons.dat`, a packed format nothing here
  reads. So a model plays only when its mod ships the animations loose.
- **DaC's `descr_skeleton.txt` names another mod's folder** for every file
  (`mods/Third_Age_3/data/animations/...`, 410 skeleton types). The game plays
  because the same relative path exists under DaC's own `data/`, so a path
  resolves by dropping `mods/<any>/data/` and reading it in this mod.

The chain it needs: a modeldb entry names its skeleton(s); `descr_skeleton.txt`
names that skeleton's files per action (`stand_a_idle`, `walk`, `run`...); the
animation file gives each bone's rotation over time; the viewer skins the mesh
it already draws (it already knows the bones, "rigged to N bones") and plays
it, with a picker for the action.

**Size: L, with a research step first.** 55a is the reader alone, held to
every loose file on DaC; nothing on screen moves until it reads all 1 753.
55b is the chain and the playback.

### 55a done 2026-09-22 - the animation reader, 1 751 of 1 763 files

`unittransfer/casanim.py`. The header is the model header; what an animation
adds is each node record's five integers - rotation and position key counts,
their byte offsets into one key block after the pivots, a zero - and a
properties string. **That string is why cas.py saw "25 bytes"**: empty in a
soldier's file (length 1 and its NUL), 3ds Max's physics notes in a siege
engine's, and read as a fixed 25 it sank every node after the first one that
had any. Rotations are 16 bytes a key, positions 12, then the model's chunk
list, which must land on the last byte; the offsets are checked as a running
sequence, so a misread fails instead of playing something plausible.

**Four node-table layouts, not one.** Soldiers (3.16 on) are cas.py's; the
3.02 engines write one pad byte after the node count and no properties string,
and 3.05 to 3.12 the other two combinations. The version number does not pick
one reliably, so each is tried in turn and the first that passes every check
wins.

**Read: all 10 of ROCSS's, 1 741 of DaC's 1 753.** The twelve are one siege
engine, the Isengard ballista, six files and a `convertedfiles` copy of the
same six, **every one cut short** - the node table ends 12 to 48 bytes before
its own pivots. Two are played by `descr_engine_skeleton.txt`. Every file
`descr_skeleton.txt` names that the mod ships loose reads (1 625 on DaC).

**Three things 55b inherits, measured here:**

- **Most animations a mod plays are not loose.** DaC's `descr_skeleton.txt`
  names 14 715 distinct files and ships 1 625 of them; ROCSS names 3 111 and
  ships none. The rest are in `animations/pack.dat`, which nothing reads. 55b
  plays what is loose and says so for the rest; a `pack.dat` reader is its own
  question.
- **The exporter does not normalise.** 99.52% of DaC's 1.23 M soldier
  rotations are within 0.5 to 1.5 of unit length; they are normalised when
  sampled.
- **Which component is w is not settled by counting**: `(1,0,0,0)` and
  `(0,0,0,1)` are both common exact still keys. Drawing the skeleton settles
  it; 55b's first job.

Exit: `tests/test_casanim.py`, 27 checks - fixtures in both main layouts, a
short track, three kinds of refusal, sampling, `resolve()`, and both mods.

---

# Phases 51-53 - a user's feedback on the EDB editor, 2026-09-21

**Asked for by the user on 2026-09-21**, passing on feedback from someone
editing AGO's EDB with the toolkit, with a screenshot of a recruit pool list
marked *insert below me*. Five complaints about the Buildings screen and the
codeview, and one idea that is a feature of its own. The user set the order:
**the five are the immediate next phase, ahead of 45**, and the idea comes
straight after, because it is the tricky one. Three questions were settled with
the user before this was written, and the answers are in the write-ups below.

| Order | Phase | Size | Line | Why |
|---|---|---|---|---|
| ~~22~~ | ~~**51** Order, insert below, a still codeview, and every gate at once~~ | M | **both** | **done 2026-09-21** |
| ~~23~~ | ~~**52** Change sets: record your edits, port them to the next version~~ | L | **both** | **done 2026-09-21** |
| ~~24~~ | ~~**53** Change sets, switched in place~~ | M | **both** | **done 2026-09-21** |

45, 46, 47a, 47b and 48 keep their order behind these three.

## Phase 51 - Order, insert below, a still codeview, and every gate at once - DONE 2026-09-21

**Done 2026-09-21, both lines, cut on request as v2.3.6 and beta 2026-09-21. All four parts shipped as
scoped, and building them found two things the scoping did not: a defect in
shipped work, and a second one the first was hiding.**

### What building it found

**Trade resources were never in any region.** The all-gates summary's first
run over the two installed mods said 24 real clauses could be met nowhere, and
most of them were `requires resource gold` or `sulfur` or `ivory`. A trade
resource is placed on the map by `descr_strat.txt` (`resource sulfur, 344,
333`) and belongs to the province that tile is in; `edbvocab.regions` read only
`descr_regions.txt`, whose resource line carries the hidden ones. So the
per-term "📍 N settlements" marker the clause picker has shipped since Phase 12
said **∅ nowhere for every trade resource in every mod**. ROCSS places sulfur
three times, DaC places chocolate twice. `edbvocab.placed_trade` now joins them
in through `mapquery.Facts`, which already put every placed resource in its
province, so there is still one reader of that file. It costs about 0.7 s per
mod on a vocabulary that is cached on the mod, and a map that will not load
leaves the regions file's line standing rather than failing the vocabulary.

**What is left is real.** With the join, 674 clauses across the two mods have a
resource gate and three can be met nowhere, all on DaC: two Snow Troll pools
gated on `Rhudaur` (4 regions) and `ResD` (13), and one pool on `Cardolan` and
`ResF`, with no region carrying both. Those are the finding the feedback asked
for, and the row now says `∅ no region passes every gate`.

**The code view lit the wrong line after a move.** Rows named their span by
the file line they came from (`capline#N`), which was safe while a row could
never move. A moved row sits on a different line of the re-rendered text, so
hovering it lit its old neighbour. The rows now name their span by written
position, `level:X:cap#N`, which the server already emitted and which is right
either way. Checking that turned up the second defect: **adding units through
the picker never re-rendered the code view**, so the pane went on showing the
level without them until the next keystroke. `bldAddPicked` now follows the
edit like every other path.

### What shipped

- **Order.** A grip to drag and ▲ ▼ for one step, on every recruit pool and
  every other capability, inside its own block (`capability` and
  `faction_capability` do not trade rows). `_plan_capabilities` writes the
  list's order: a save that moves nothing, or only adds at the end, takes the
  old one-splice-per-line path byte for byte; a moved row or a row inserted
  mid-list re-lays the block's inside in one splice, copying every untouched
  line as the file has it, with the comment and blank lines above each line
  travelling with it and a closing remark staying at the bottom. A deleted
  line's place in the list is not an order change.
- **New units land where they are written.** They used to be shown at the top
  and written at the bottom, which is the complaint as the feedback put it.
  They now go at the end, the picker scrolls to them and flashes the first,
  and `＋` on any row opens the picker to put them directly under it. `＋` on a
  plain capability adds a row under it.
- **`code_view_follow`**, click-only by default: a hover lights the line and
  never scrolls, a click anywhere on a box scrolls to it, and `⇕ Follow hover`
  on the pane's bar brings back the old way. One widget, so every editor.
- **Every gate at once**, on each row and in the clause dialog: the regions
  that pass the clause's `hidden_resource` and `resource` terms, left to right
  as the engine reads them, each with its starting owner and a ★ on the ones a
  named faction starts with, and the terms that do not narrow it listed as
  assumptions.

`tests/test_buildings.py` section 13 is the writer (a swap, the append path
unchanged, an insert under the first line, comments travelling), and 13b runs
the page's own evaluator in node: seven synthetic clauses including one where
precedence would answer differently, and every one of the 674 real and-only
resource clauses against a plain set intersection.

### The scoping, as written before it was built

**Measured against the code on 2026-09-21. All five are real, and none of them
is half-built.**

**1. Recruit pools cannot be reordered.** `bldAddCap` pushes onto the end of
`lv.caps`, and nothing in `buildings.js` moves a row: no drag, no up or down.
The order matters in game, because the recruitment panel lists units in the
order the EDB gives them. The writer is why this is a phase and not a button:
`_plan_capabilities` in `buildings.py` edits existing lines *in place* so the
trailing comments DaC's EDB is full of stay byte-exact, and it appends new
lines just above the block's closing brace. A move has to become a splice that
lifts a line **with its trailing comment** and drops it at the new position,
and a new row has to carry an anchor ("after line N") instead of always going
to the bottom.

**2. Insert below.** A `＋ below` on every capability and recruit row, in both
`capability` and `faction_capability`, that opens the new row directly under
the one it was pressed on. The feedback asked for this so a long list does not
have to be scrolled to drag a line into place, which assumes (1) is dragging.
It is: drag by a handle on the row, plus move up and move down for keyboard
use and for the list that does not fit the screen. Bulk edit holds its
selection by object, not index (see the comment over `bldBulk`), so a move does
not slide it onto the neighbours.

**3. The codeview moves under the pointer.** `cvBindHover` in `codeview.js`
paints the hovered row's line on every `mouseover`, and `cvPaintSpans` calls
`cvReveal`, which scrolls. So running the mouse down the GUI drags the file
around, and hovering the space between rows resolves to the whole record and
throws the pane back to the top of the snippet. **Settled with the user: a
setting, defaulting to click-only.** `code_view_follow` beside
`code_view_tidy` and `code_view_comments`, saved through `cvSetSetting`. In
click-only mode a hover still lights the line and never scrolls; a click on a
row scrolls to it, the way a click on a row's name already does. `hover` keeps
today's behaviour for whoever likes it. It is one change in the shared
component, so every editor that uses the codeview gets it, not only Buildings.

**4. Every gate at once.** Each `hidden_resource` and `resource` term already
has its "📍 N settlements" marker (`condWhereHtml`, fed by `edbvocab.regions`),
but nothing combines them, so a recruit gated on
`hidden: GondorEast AND hidden: ResF` means working the intersection out by
hand. The summary evaluates the clause over every region, left to right with
and/or and `not`, the way the engine reads it (no precedence), and shows the
regions that pass. **Settled with the user: factions are shown, not
filtered.** Who owns a region changes during play, so a `factions` term does
not narrow the list; each region carries its starting owner, and the ones a
named faction starts with are marked. Terms that cannot be decided per region
from the files (`event_counter`, `region_religion`, `building_present`) are
listed under the summary as *not narrowed by*, so the number is never read as
more certain than it is. It shows in two places: the clause dialog, and the
`REQUIRES` strip on each recruit row, where `∅ no region passes every gate` is
the finding worth having, because a pool nobody can recruit from is the same
silent failure as a missing hidden resource.

**Exit:** drag, move up and move down on recruit pools and on every other
capability, written as moves that keep trailing comments; `＋ below` on every
row; the new rows land where they were inserted; `code_view_follow` with
click-only as the default and hover-scroll as the option; the all-gates summary
in the dialog and on the row, with the owner marks and the *not narrowed by*
list; `tests/test_buildings.py` asserting that a move and an insert round-trip
every other line byte for byte, and that the gate evaluation follows the
engine's left-to-right order on a clause where precedence would give a
different answer.

## Phase 52 - Change sets: record your edits, port them to the next version - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** A **My changes** screen,
`unittransfer/changesets.py`, and `tests/test_changesets.py` (45 checks). The
scoping below held in its shape; four things were decided or found by building
it, and they are the part worth reading.

### What building it decided

**The hook is `logutil.file_op`, not the forty `backup_and`s.** The scoping
named the `backup_and` copies as the capture point, and there are forty modules
with their own. All of them log `BACKUP` before a write and `WRITE` (or `COPY`,
`MOVE`, `RESTORE`) after it through `file_op`, whose docstring already promised
that nothing reaches the disk without passing it. So `changesets.capture` hangs
off that one function: the first `BACKUP` of a file keeps its original as the
baseline, every later write refreshes *mine*. It never raises, it records only
files under `<Medieval II>/mods/<mod>/data/`, and a file over 64 MB is skipped.
Undo restores files without a write helper, so `transfer.undo` tells the set
directly.

**Mine is kept too, not only the baseline.** The scoping had the change list as
baseline against the current file. That is wrong in exactly the case the
feature is for: once an update has overwritten the mod, the current file is
*theirs*, and your version exists nowhere. So the set keeps both copies, and
the screen says when the disk has moved under them ("changed on disk since your
last save here"), which is how an update announces itself.

**Records touching counts as a conflict.** The first merge let an insert
directly under a line the other side rewrote merge cleanly, which in an EDB is
a pool added under a pool upstream re-tuned: related edits, silently combined.
Neighbouring lines now conflict, git's rule for the same reason, and the test
fixture was moved so its "merges" case has a line between the two edits.

**Undoing a port must put the set back.** A port onto the same mod moves the
set's baseline to the version ported onto, which is what the next update must
be compared against. Undoing it first re-read the files, which left baseline
and mine both saying the new version: every edit forgotten. The port now copies
the set beside its backups and `changesets.undone` restores it, so an undone
port can be ported again.

### What shipped

- **Recording, with nothing to switch on.** Every save to a mod from any
  screen, baseline and mine under `config/changesets/<mod>/`, outside the mod.
- **The change list**, record by record: an EDU unit by `type`, an EDB building
  by name, a region by name, a text key by key; any other file as one record,
  line by line; a binary file whole. Each file says whether the disk still
  matches your last save.
- **Port**, onto the same mod as it is now or onto another installed folder,
  from this mod's set or an imported one: each record `clean`, `already`,
  `merged` (both sides, lines apart), `conflict` or `gone`, with the original,
  yours and the new version side by side, and a `dangling` warning on a
  recruit pool naming a unit the resulting EDU does not have. Clean and merged
  start ticked, conflicts and removals start unticked. A new record goes where
  it sits in yours. One backup, one log entry (`🔀 My changes` in the Log),
  one Undo.
- **Export and import** as one `.m2changes` file (a zip of the set). An
  imported set is never trusted to stay inside `data/`: every path is checked.
- **Take the files on disk as mine** for hand edits made outside the toolkit,
  and **Forget this record**, both behind a confirmation that says when not to.

### What is not in it

`descr_strat.txt`, the modeldb and the EOP files have no record shape here yet,
so each is one record: a port of them is clean, already, merged by lines or a
conflict, never per character or per entry. The dangling check covers recruit
pools against the EDU and nothing else. Neither was measured against a real
AGO or EUR update, because only one version of each installed mod is on this
machine; the fixture is a synthetic update in both tests and the demo.

### The scoping, as written before it was built

**The problem, as the feedback put it:** edits made to AGO are lost when the
next AGO release overwrites the files, and big mods like AGO or EUR cannot
simply be copied into a new mod folder to keep them. Old edits also collide
with how a new release is organised, for example units the new version adds to
EOP recruitment from the EDU. He asked whether it could be done without a
duplicate, and suggested a file listing every change that can be exported and
**ported** onto another version of the same mod, with a checklist of what to
port and warnings where a unit was removed, a record was edited upstream too,
or a building or region no longer exists.

**Settled with the user: this phase records and ports, switching in place is
Phase 53.**

**No duplicate: the baseline is only the files the toolkit touched.** Every
write already goes through a `backup_and(rel)` that copies a file before its
first change (`edit.py`, `transfer.py`, `bmdb.py`, `stratmap.py`, `cards.py`).
A change set keeps the **first** of those copies, per mod, outside the mod
folder, so an update that overwrites the mod cannot overwrite the baseline.
That is a few files out of thousands, not a copy of the mod.

**The change list is derived, not logged.** Diffing the baseline against the
current file, record by record, with the parsers the toolkit already has (EDU
by `type`, EDB by building, level and capability, `descr_regions` by region,
`descr_strat` by faction, settlement and character, EOP recruitment, strings by
key, modeldb by entry), means an edit made by hand outside the toolkit is in
the set too, and nothing depends on a log that could miss a write. A file with
no record parser falls back to a line diff and says so.

**Export is one file**: the list, plus each changed record's before and after,
so it can be ported from another machine.

**Port is a three-way merge by record**: the baseline (old version, untouched),
mine (old version, edited) and theirs (the new version). Each change comes out
as one of:

- **clean**: theirs still equals the baseline, so mine applies as it is
- **already there**: theirs already equals mine
- **changed upstream too**: both sides changed the same record; show all three
  and let the user pick, never merge fields silently
- **gone upstream**: the unit, building, level or region no longer exists
- **dangling**: mine applies, but names something the new version dropped (a
  recruit pool for a unit no longer in the EDU, a region's hidden resource
  nobody declares)

The user ticks what to port, the writes go through backup and undo like every
other write, the existing validators (`mapcheck`, `tree_check`, the unit
reference checks) run on the result, and the new version's files become the
set's new baseline.

**What to measure first.** Only one version of each installed mod is on this
machine, so the session builds its test fixture from an installed mod plus a
synthetic upstream (records removed, reordered, edited on both sides, EOP
recruitment added) before any UI. If AGO or EUR can be installed in two
versions, that is the real test and it goes in `tests/`.

**Exit:** a change set per mod with a baseline of touched files only; the
derived record-level change list; export and import of one file; port with the
five outcomes, a checklist, and backup and undo; the validators run after a
port; tests over the synthetic upstream for every outcome.

## Phase 53 - Change sets, switched in place - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** *Versions of this mod* on
the My changes screen, `plan_switch` / `apply_switch` in `changesets.py`, and
20 more checks in `tests/test_changesets.py` (section 7).

**Turning a set off is not "write the baseline back".** That was the scoping's
sentence, and it is right only while the disk still says exactly what the set
last wrote. After any other change - an update, a hand edit - writing the
baseline back would throw that change away with yours. So off is the port run
backwards: yours as the base, the original as the change, the disk as theirs,
record by record. On is an ordinary port of the set onto what that leaves. A
switch between two sets is both, as one job.

**A switch is mechanical or it does not happen.** A port can stop and ask; a
switch is a button, so any record that comes out `conflict` or `gone` in
either half refuses the whole switch, and the refusal names the set, the file,
the record and the outcome. The way through is a port, which is the screen that
asks. On a mod an update has overwritten, that is exactly what should happen.

**What a set is, now.** A mod carries any number of sets; one is on (its
records are what the files say), and the rest hold both their copies, ready to
go back in. The recording hook writes into the ON set. With every set off, the
next save starts a new one, whose original is the mod as it shipped, so "the
vanilla mod plus a second set of edits" is just what turning the first off and
saving leaves. A set predating this phase counts as on; an imported set is off
until switched on here. Sets can be renamed.

**A switch's own writes are not recorded.** They go through the same helpers
as every write and would otherwise land in the set as fresh edits,
overwriting the copy being switched to. `_quiet` holds the hook off while a
switch writes; the set switched on is then rebased onto what it was put into,
as a port rebases. Undo restores every set the switch touched as well as the
files.

**The unsaved-edits refusal is the page's**, because only the page knows about
them: `chgUnsaved` asks Buildings, the unit editor and its tabs, the two
campaign panels, and every screen that keeps a `dirty` flag.

### The scoping, as written before it was built

The other half of the feedback: *instantly revert back to the vanilla mod* and
keep several versions of the same mod to test. Once 52 has a baseline and a
derived change list, turning a set **off** is writing the baseline records
back, and turning it **on** is 52's port onto the mod's own current files.
Several named sets per mod, one active at a time, and the switch refused while
the toolkit has unsaved edits open. Written up now so 52 is built with it in
mind; scoped properly when 52 is done.

---
# Phases 44-48 - the pass over his non-map screens, 2026-09-13

**Asked for by the user on 2026-09-13**, in seven parts: his validation and
where it sits, his hidden-resource editor, whether our traits and ancillaries
are still level with his, his map side panel and paint mode and tooltip, his
cultures and factions panels, his strings editor, and his sound files.

**Two of the seven produced no phase, and both for a reason worth keeping.**
Traits and ancillaries have not moved on his side since March; the strings
codec is wrong in his tool and right in ours. Both are written up under *The
2026-09-13 pass, and the two parts of it that produced a measurement* below.
The map side panel is **28a and 28b**, because that is the phase already going
to touch the screen. The remaining four are here.

**These four are outside both blocks.** The locked order is the campaign map,
then the mercenaries, and nothing here is either: 44, 45 and 48 are the
Buildings and Strings modules, 46 is Minor Files and Factions, 47 is a file
family nothing in the toolkit opens. They are written up rather than rated
because the user named them, and they sit after block two until the user says
otherwise. All of them are **subreleases on both lines** - none touches the
campaign map, so none is beta-only.

| Order | Phase | Size | Line | Why |
|---|---|---|---|---|
| ~~21~~ | ~~**44** The EDB's tree, checked~~ | M | **both** | **done 2026-09-20** |
| ~~25~~ | ~~**45** The hidden resources line~~ | S | **both** | **done 2026-09-21** |
| ~~26~~ | ~~**46** Cultures gets a screen, and two forms get a strip~~ | M | **both** | **done 2026-09-21** |
| ~~27~~ | ~~**47a** The six export sound files~~ | M | **both** | **done 2026-09-21** |
| ~~28~~ | ~~**47b** The thirty-two sound scripts~~ | L | **both** | **done 2026-09-21** |
| ~~29~~ | ~~**48** The two rows the strings screen cannot add~~ | S | **both** | **done 2026-09-21** |

**Renumbered 2026-09-21:** Phases 51, 52 and 53 took orders 22 to 24 ahead of
these, on the user's word. Their table is under *Phases 51-53*.

## Phase 44 - The EDB's tree, checked - DONE 2026-09-20

**Nine rules ship, three are refused, and the refusals are the phase.** The
scoping said six go in as stated and four get measured first. What measuring
found is that **one of the six could not go in as stated either**, and that is
the result worth having: his validator, run over the two installed mods as
written, would report 42 lines as broken that are working exactly as their
authors meant.

### What the measurement said

Run over Divide and Conquer (136 lines, 499 levels) and ROCSS (107 lines, 290
levels), 789 levels in all:

| his rule | measured | shipped as |
|---|---|---|
| duplicate building name | 0 | `tree.name_twice`, fatal |
| a line with no levels | 0 | `tree.no_levels`, fatal |
| an `upgrades` entry naming nothing | 0 | `tree.upgrade_unknown`, fatal |
| a `convert_to` naming nothing | 0 | `tree.convert_unknown`, fatal |
| a `building_present_min_level` naming nothing | 0 of **336** references | `tree.min_level_unknown`, fatal |
| **a level no `upgrades` entry reaches** | **42 lines** | **reshaped** - see below |
| a level with `cost 0` | 4 (1.4%) | `tree.free_level`, warn |
| a level with `construction 0` | 1 (0.3%) | `tree.instant_level`, warn |
| a level with no `factions` clause | 0 | `tree.no_factions`, warn |
| a line with more than 9 levels | **2, on a mod that plays** | **refused** |
| a line approaching 50 levels | nothing to measure | **refused** |

**The five reference rules find nothing on either installed mod, and that is
what they are for.** Phase 31's river rules set the precedent: a rule that
finds nothing on five real maps is not a wasted rule, it is a rule that has
been checked against reality and passed. The 336 `building_present_min_level`
references all resolving - both the line they name and the level on it - is the
single most reassuring number in this phase, because that is the one condition
in the EDB that can dangle twice.

### The rule that could not be stated his way

"A level no `upgrades` entry reaches is unreachable" assumes every building
line is a chain. **Forty-two are not.** Eighteen lines on DaC and twenty-four
on ROCSS have no `upgrades` entries anywhere in them: their levels are
**alternatives**, picked by `hidden_resource`, and "reachable" means nothing on
such a line. `hinterland_enedwaith_clan_halls` is nine mutually exclusive clan
halls; `mumakil`, `mithril_mines` and `trade_centre` are the same shape.

Excluding those leaves **three real chains on Divide and Conquer with a second
entry point** - `hinterland_unique2` (`hornburg` climbs to `wulf_hall_edoras`,
and `gilraen` starts a second chain to `teeth`), `hinterland_tharbad_bridge`
and `hinterland_palantir`. DaC ships and plays. So it is not an error either.

It ships as **`tree.second_entry`, at `note`**, excluding alternative-lines
entirely: worth saying, because a second way into a chain is usually not what
somebody drawing one meant, and not worth calling wrong.

### The two ceilings, refused, on Phase 12's own ruling

His "the vanilla limit is 9 levels" would fire on `hinterland_unique1` (13
levels) and `hinterland_unique2` (12) - **on a mod that runs**. A ceiling a
shipping mod is over is not a ceiling. His "approaching the M2TWEOP limit of
50" has nothing to check itself against: the largest line on either installed
mod is 13, so the rule has never seen its own subject.

This is Phase 12's ruling applied again, and it is worth writing down twice
because it keeps coming up: **a count from a wiki is not a fact about a mod.**
12 kept `guild_` at three levels as a hint because 19 of 19 real guild lines
have exactly three, and refused "the engine refuses a fourth" because that is a
different claim with no measurement behind it. Both refusals are in
`buildings.RULES_REFUSED`, in the module rather than only here, because the
next person to read his validator will find them in it and wonder why we do
not have them. They travel out to the panel too, under *The 9 rules, and the
three that are deliberately not here*.

### The shape, and why it is `mapcheck.py`'s

A code, a label, a severity, a **source** naming who says it is a rule, and a
function yielding findings. Copied down to the decorator, because M17 - the
five-star dashboard that is the complaint that we have more validators than any
reference tool and no single door to them - is only cheap if the validators
already agree about what a finding is. `EdbFinding.what` never carries a line
number, for `mapcheck.Finding`'s reason: adding a building at the top of the
file must not make every finding below it a different finding.

**One request, not two.** The tree findings ride in the answer
`/api/buildings/checks` already gives, because the screen asks that question
once per mod and once per line; a route of its own would have been a second
request on both paths and the two halves of "what is wrong with this EDB" would
have arrived at different times. On the mod's screen it is a shut button that
fetches on first open - most visits are to look at a building, not to audit
one - and every finding row opens the building it is about.

### Two defects found while building it, both mine

`TREE_REFUSED` already existed in `buildings.py` - the new-tree form's
"what this module will not do to a whole line" - and the new constant shadowed
it, which took `overview()` down with a `ValueError` on every buildings screen.
Renamed to `RULES_REFUSED`. And `bldTreeToggle` already existed in
`buildings.js`, folding a row open in the tree browser; the new one silently
replaced it. **`test_web_modules` caught the second one and the first suite run
caught the first**, which is the whole argument for both of those tests
existing in a project with one global JS scope and a 3,000-line module.

Exit: nine rules in `buildings.py` on the `@rule` shape with a source each,
`tree_check(edb, line="")`, `RULES_REFUSED`, the findings on both the mod's
screen and each building's, and `tests/test_buildings.py` section 12 - a
fixture per rule, plus 12b running all nine over every installed EDB and
asserting a shipping mod has no fatal.

## Phase 44 - the scoping it was built from

**Our EDB checks are about recruitment and nothing else.**
`buildings.line_checks` finds three things per building line: a unit that stops
being recruitable further up the chain, the same unit twice in one level, and a
divergence between a line and its city/castle twin. That is the half of the
file the unit editor cares about. Nothing checks the **tree**: that a building
name is unique, that a line has levels at all, that each level is reachable
from the one below it, that an `upgrades` entry names a level that exists, that
`convert_to` names a building that exists, that a
`requires building_present_min_level` names a level that exists.

**He has both halves of that and we have neither.** `edb/EDBValidator.jsx` is
fifteen messages over the parsed tree and `export/ModValidator.jsx` is ten more
of the same shape; together they are the one place in his tool that does
something ours does not, which is the opposite of the finding every other audit
of his has produced.

**Six rules go in as stated, because each one is a reference that either
resolves or does not.** Duplicate building name, a line with no levels, a level
no `upgrades` entry reaches, an `upgrades` entry naming nothing, a `convert_to`
naming nothing, a `building_present_min_level` naming nothing. Phase 12 already
measured the ground under three of them: **all 601 current upgrade entries
point forward at a level on their own line**, none backwards, none at itself,
and `test_edb_tree` asserts `upgrade_name()` against every one. So the data a
finding needs is computed already, and what is missing is the finding.

**Four of his rules are measured first and probably do not ship as errors.**
A level with `cost 0`, a level with `construction 0`, a level with no
`factions` clause, and his three level-count ceilings. The rule this file keeps
making is that a count from a wiki is not a fact about a mod: Phase 12 kept
`guild_` at three levels as a hint because **19 of 19 real guild lines have
exactly three**, and refused "the engine refuses a fourth" because that is a
different claim. His "vanilla limit is 9" and "approaching the M2TWEOP limit at
50" are the same shape. Measure all four across the four installed mods first;
a rule that fires on a quarter of a shipped file is noise, and this validator
has a baseline for the findings that are somebody else's.

**It goes where the other checks go, not into a second engine.** `mapcheck.py`
is the model down to the decorator: a `@rule` with a code, a label, a severity
and a sentence, and a panel that lists what came back and offers a jump. The
Buildings module already has the Code View to jump into. No rule is written
twice in the browser.

**And it is the first half of M17.** The five-star *crash and validation
dashboard* is the complaint that we have more validators than any of the four
reference tools and no single door to them. This adds one more validator; it
also makes the EDB's entry in that door a real one rather than a recruitment
rollup.

Exit: six rules over the tree, four measured and then decided, in
`buildings.py` on the `@rule` shape, on the Buildings screen with a jump into
Code View, and a fixture per rule in `tests/test_buildings.py`.

## Phase 45 - The hidden resources line - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut. The scoping held.** A
**◈ Hidden resources** panel beside *Check the tree* on the Buildings screen,
`buildings.plan_hidden` / `hidden_impact` / `hidden_usage`, a route pair
`/api/buildings/hidden/plan|apply`, and section 14 of `tests/test_buildings.py`.

**What a removal shows is measured, not estimated.** On Divide and Conquer,
taking `Rhudaur` off names its 4 provinces and 162 clause lines; the busiest
name, `Eregion`, is carried by 10 provinces and gated on by **636 lines**. The
test asserts the impact list, the per-name count and a raw scan of the file
agree. A clause is counted by line, because a line naming the resource twice is
still one gate. The clauses come from the parse (a level's own `requires`,
every capability and faction_capability) and then a scan of every other line,
so a clause somewhere the parser does not model is still named.

**The ceiling, with the corrected number.** The scoping said Divide and
Conquer ships 74; it ships **75**, all unique, and ROCSS 74. The panel states
the count, TWCenter's 63-or-64, and that both mods pass it, and a line over 64
carries a warning on the plan. Nothing is refused for it.

**The write is the one line.** The keyword's own indent and gap (DaC writes
two spaces), the separator between names and a trailing comment all survive;
the test checks that every other line of the file is byte-identical and that
Undo restores it exactly. A name must be one word of letters, digits and
underscores, as all 149 on the two installed lines are, and a duplicate is
refused whatever its case. An EDB with no line gets one above the first
building.

### The scoping, as written before it was built

**We read the line and nothing writes it.** `buildings.py` holds
`hidden_resources` and `hidden_resources_line`, and `hidden_resources_line` has
exactly one reference in the whole tree: the assignment that sets it. The list
is already read four ways round - the `requires hidden_resource` clause
picker's vocabulary, `edbvocab.regions`, the province panel's resource chips on
the campaign map, and a `mapquery` fact - and a name can be added to none of
them.

**Phase 12 refused his editor and said what would make it worth having.**
`HiddenResourceEditor.jsx` is add and remove with no check either way, and a
hidden resource is named in two other places: `descr_regions.txt` says which
province carries it, and `requires hidden_resource X` clauses throughout the
EDB say what it gates. Removing one breaks both in silence, which is the
hardest kind of EDB bug to see, because the building simply never becomes
available.

**The check that refusal asked for is already computed.** `edbvocab` builds the
region rows per hidden resource, and the clause picker already has a *where
does this bite* panel over them. So a removal can name every province that
carries the resource and every clause that gates on it before it happens, which
is the whole difference between his feature and one worth shipping.

**The ceiling is reported with both numbers, and neither as a refusal.**
TWCenter's *List of Hardcoded Limits* puts it at 63 or 64 and says extras
crash; **Divide and Conquer ships 74**. Phase 12 deferred the feature partly on
that, because warning about a limit three of three mods disprove is worse than
saying nothing. The panel says the count, says what the note claims, and says
that the installed mods pass it. It does not stop a save.

**The write is one line.** A splice at `hidden_resources_line`, the way every
other write in this module is a splice, so the 7,203 comment lines in the three
EDBs stay where they are.

Exit: add and remove on the `hidden_resources` line; a removal naming every
province and every clause it would darken, and refused until that is
acknowledged; the count and the two ceiling claims stated; backup and undo like
every other write; `tests/test_buildings.py` asserting that everything outside
the line round-trips byte for byte. This closes the hidden-resource half of the
four-star *Mines and hidden resources* row, which keeps
`descr_settlement_mechanics.xml`.

## Phase 46 - Cultures gets a screen, and two record forms get a strip - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** All four parts shipped as
scoped, and one sentence of the scoping was wrong about the files.

**The culture's text keys are not "the {CULTURE} key and three
EMT_<CULTURE>_PRIEST keys".** Measured in the two installed mods'
`text/expanded.txt`: every culture has its `{CULTURE}` key and **between one
and five** `EMT_<CULTURE>_PRIEST` keys, the suffixed ones being the priest's
ranks (ROCSS's eastern European has `_1` to `_4`: Bishop, Cardinal, Patriarch,
High Priest). And the `EMT_*_PRIEST` keys that are most common are named after
**factions** (`EMT_VENICE_PRIEST`), which override the culture's where they
exist. So a duplicate lists the keys the SOURCE culture actually has, each with
the new name and the source's text beside it, rather than a fixed four.

**What shipped:**

- **Cultures is a mode.** A `sub:true` entry in `MODES` and a `{mode:...}` row
  in `MINOR_TABS`, like Traits and Guilds. It is still the Minor Files screen
  underneath, locked to the cultures tab - `renderCultures` and a `mfMode()`
  that every "is this screen still up" check asks - so the list, the pane, the
  code view and the save are the ones that were already tested.
- **Four tabs**: General, Settlements, Infrastructure, Agents, drawn by one
  shared `recTabsHtml`. **The port ladder is editable** on Infrastructure,
  value by value in the file's order, which `render_culture` now writes one
  splice per line; the ladder's shape (how many levels) stays in the code view
  and the form says so, because a level is a pair of lines placed in the file's
  order.
- **Duplicate a culture**: action `duplicate`, the source's whole record -
  brace, tail and agents - under a new name, inserted after the last culture
  (one insertion; a trailing banner stays last). The preview names what it
  still needs and does not write: the text keys above, the factions on the
  source that could move onto it (a culture no faction names is used by
  nobody), and that every model, card and agent picture still points at the
  source's files. A name must be lower case letters, digits and underscores,
  because it becomes a text key and a folder name.
- **The faction form on five tabs**: General, Art and banners, What it can do,
  Movies, Horde - the sections it already had, no parser work.

Neither of the two things the scoping refused was taken: no `descr_offmap_models`
generation (no installed mod has an `offmap` line), and no claim about how many
cultures the engine allows. Promoting Factions and the other sub modes to the
burger menu is still the user's call.

### The scoping, as written before it was built

**The parser is not the gap.** `minorfiles.parse_cultures` already reads
everything his `culturesParser.jsx` reads and two things it does not: the
settlement plan beside the model and the card on every level, and the port
ladder in the file's own order rather than as three fixed slots. Phase 10a took
his `SETTLEMENT_TYPES` and `AGENT_TYPES` and his reading of the agent line as
seven columns, all three measured correct, and refused his record split (he
splits the file on `;;;;` banner lines, which merges two cultures on a file
that has none) and his `offmapSettlement` / `offmapPort` defaults, which are
invented vanilla paths never parsed from the file and written on every save.

**The gap is the screen, and it is three things.**

**One: cultures leaves the strip for a mode of its own.** Traits, Ancillaries,
Guilds, Factions and Strings each have a `sub:true` entry in `MODES` and a
`{mode:...}` row in `MINOR_TABS`, so their tab in the Minor Files strip
switches mode rather than tab. Cultures is the one `{id:'cultures'}` row left
that does not. Phase 10a made it a tab on the ground that `descr_cultures.txt`
is "the same size of job" as rebels and religions; that stops being true the
moment the form has four sections, which is what the rest of this phase does.
Two lines in `core.js`, and a `loadCultures` that is `mfCultureForm` moved.

**Two: the form gets the strip every other record form here has.** General,
Settlements, Infrastructure, Agents. Ours is one scrolling form of three
sections, and the ports are pushed into Code View with a note saying why:
`port_land` and `port_sea` are a pair of lines per level, which is a section
rather than a field, and a section is exactly what a tab is for. Infrastructure
is where the fort, `fort_cost`, `fort_wall`, the fishing village, the three
port levels and the watchtower go, and it is the tab that makes the port ladder
editable at last.

**Three: add a culture, by duplicating the one on screen.** His
`handleAddCulture` deep-copies, renames and stops. Ours writes the record and
then says what else a culture needs, because we can name it: the `{CULTURE}`
key and the three `EMT_<CULTURE>_PRIEST` keys in the compiled text archive,
which Phase 6 already writes; the factions in `descr_sm_factions.txt` that have
to be moved onto it; and the settlement and agent art, which the form already
shows and already says when it is missing. `factionclone.py` is the shape of a
record that arrives in more than one file.

**The faction form gets the same strip, and that is the whole of its half.**
`facFormHtml` is one long form too, with its sections already separated: the
record, the pictures, the movies, the horde, the findings. His `FactionsEditor`
is five tabs over the same ground. Same widget, same argument, no parser work,
so it belongs in this session rather than a fifth of its own. **Factions is
already its own mode** and has been since Phase 11, reached from the strip the
way Traits and Guilds are; what it is not is an entry in the burger menu, and
neither are Traits, Ancillaries, Guilds or Strings. Promoting any of them is
one decision about all five and it is the user's, not this phase's.

**Two things are not taken.** His Extras tab generates
`descr_offmap_models.txt` blocks out of the invented defaults above, and **no
installed mod has an `offmap` line at all**; that file is a three-star row of
its own and it will be parsed before it is written. And his note that the
engine allows one new culture beyond vanilla's seven is an engine claim with no
measurement here, so it goes to Phase 39 with the other ceilings or it is not
said.

Exit: cultures as a mode with a four-tab form, the port ladder editable,
duplicate-a-culture writing the record and naming the four keys and the faction
moves that go with it, the faction form on the same strip, and
`tests/test_minorfiles.py` holding the byte-exact round trip it already holds.

## Phase 47 - The sound scripts, which nothing here opens

**Measured on the four installed mods, 2026-09-13.** Divide and Conquer ships
**40 sound script files and 120,981 lines**; Third Age Reforged 40 and 117,194;
Vanilla Redux 39 and 92,473; `vanilla_kingdoms_uncompromised` 40 and 131,200.
They split three ways: **32** `descr_sounds_*.txt`, one `descr_sounds_db.xml`,
and **seven** `export_descr_sounds_*.txt`. Every one of them is in `data/`, and
all of them are plain text with CRLF. Nothing here opens any of them except
`export_descr_sounds_units_voice.txt`, which is `sounds.py`.

**His editor is not a port, and Phase 13 measured why.** His
`KNOWN_SOUND_FILES` names fourteen files in `data/sounds/`; **four of the
fourteen exist** (`_music`, `_units`, `_units_voice`, `_weapons`) and they are
in `data/`, while the other ten are RTW-era or invented. Run over Divide and
Conquer's 32 his parser round-trips **0 of 32** and loses 2,975 lines, because
it takes any column-0 line without a space in it as a block label; in
`descr_sounds_weapons.txt`, 3,855 lines, the only block it finds is the word
`end`. The one thing worth carrying from that screen is its empty state, which
says where the base sound files are, because M2TW ships them packed.

**Two grammars, so two sessions.**

### 47a - The six export files, on a parser we already have - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** A screen of its own,
**Sound banks**, beside Unit Sounds on one strip, over a new
`unittransfer/soundbanks.py`. Measured again before a line was written, and
the scoping was wrong about the parser.

**`sounds.py` does not already read these, and cannot be taught to.** Three
things in the six files break its grammar, all measured on both installed
mods:

- **Indentation says nothing.** `_prebattle` mixes tabs and runs of spaces in
  one block, and a `pri 9` sits deeper than the `VnV` it belongs to. So a
  header's depth comes from its keyword, per file, from a table:
  `accent > class > vocal` (soldier voices), `accent > type > vocal` (strat
  map), `accent > notification` (battle events), `accent > element > relationship
  | trait | condition | situation | pri` (pre-battle), `text` (advice), and none
  at all for narration, whose `event <NAME>` lines stand at the top.
- **`VnV` is not a level.** It is a line of its own that qualifies the `trait`
  or `pri` under it, so it is carried as the first line of that block, and a
  copy takes it along.
- **Attributes are on more than the event line.** `_soldier_voice`'s events
  carry `mindist 0.75 priority 120 volume -10 probability .4` and
  `_stratmap_voice`'s `delay 0 pref SFX`, and a sample line can carry its own
  (`willhelm.wav probability .001`). So a body line is text, never split into
  a path.

It is still a splice over verbatim lines, `sounds.py`'s own rule. **All twelve
files (six banks on two mods) come back byte for byte, every event lands in a
block, and not one warning is raised**; DaC's `_narration` is three comment
lines and ROCSS's `_advice` one entry, and both read.

**What shipped:**

- The six banks on tabs, each a tree of its blocks on the left, folded by
  default (DaC's strat map voices are 2,570 blocks). Search reaches block
  names and sample lines.
- A block's events on the right: the attributes on a line, the folder and
  sample lines in a box. A line that did not change keeps its bytes; a new one
  takes the indent of its kind's first line in that event, so a block keeps
  whatever mix of tabs and spaces it had.
- **Duplicate as…**, **Rename…** and **Remove** on any block, an accent
  included: duplicating DaC's `accent Arabic` in the strat map bank is one
  insertion of 1,619 lines and nothing else changed. A new accent is said to be
  used by nothing until something names it.
- Refused: a copy under its own name or one already beside it, an event whose
  first line is not a folder, an `end` or `event` line inside an event, a
  narration name that is not letters, digits and underscores, and any op whose
  line no longer says what it said when read. An attribute no event in any of
  the mod's six banks uses is a warning, not a refusal.
- One backup and 🕑 Log undo per save, mode `soundbanks`. The `units_voice`
  bank stays in Unit Sounds and `factionclone.py` keeps writing `_prebattle`.

**Not taken:** checking that a sample exists. The base game's sounds are packed
(`data/sounds/*.idx` and `*.dat`), so the screen says where they are and does
not pretend to know.

#### The scoping, as written before it was built

`export_descr_sounds_*.txt` is the indented `BANK:` / `accent` / `class` or
`type` / `vocal` / `event` … `end` / `folder` tree that `sounds.py` already
reads verbatim and splices. Six more files take it:
`export_descr_sounds_soldier_voice.txt` (16,144 lines in DaC),
`_stratmap_voice.txt` (16,155), `_units_battle_events.txt` (7,328),
`_prebattle.txt` (8,400), `_advice.txt` (3,980) and `_narration.txt` (3). Two
differences from the voice bank have to be read before anything is written:
`_stratmap_voice` keys on `type Admiral` where the voice bank keys on
`class General`, and an `event` line there can carry attributes
(`mindist 0.75 priority 120 volume -20 probability .4`) that the voice bank's
never does.

**This is the three-star *three voice files* row, and it is cheaper than it was
rated.** That row was an L on the size of the files alone. The parser exists,
the splice exists, and `export_descr_sounds_prebattle.txt` is already written
by `factionclone.py` as a per-faction block, so this is a session and a bit
rather than more than one.

### 47b - The thirty-two scripts, on a grammar nothing here has read - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** A third tab on the sound
strip, **Sound scripts**, over a new `unittransfer/soundscripts.py`, drawn by
the same list and pane as 47a's banks.

**Measured before it was written** (both installed mods, 52,091 lines): 31
scripts in `data/` on each and `descr_sounds_music_types.txt` beside them;
4,239 events, 980 of them named. A script is five kinds of line, and the
parser tells them apart by their first word and nothing else: `DEFAULT:`,
`BANK:`, `source`, a **setting** (a key and only numbers: `grid_cell_size 40`,
`river_max_dist_apart 250 ; comment`), and a **selector** (about forty
keywords: `unit`, `hit`, `season`, `terrain`, `climates`, `type`, `state`,
`looped`, `arrived` ...), with `event [NAME] attrs` … `end` blocks under them.
An event's first word is its name unless it is a number or an attribute.
**All 64 files (32 on each mod) come back byte for byte, every event is in a
block, and not one warning is raised.**

**The arguments are typed, and the types are measured rather than guessed.**
An attribute is a number key (twenty of them: `volume`, `mindist`, `lod`,
`priority` ...), a flag (`1d`, `2d`, `3d`, `streamed`, `looped`, `ducking`) or
`pref` and a word, and those lists are every one the two mods write. A number
key with no number after it is refused; an attribute no script writes, a
`pref` the mod does not use, and a selector value no script in the mod names
are warnings. The pane lists each number key with the range this mod's
scripts already use (volume -80 to 0 on both), said to be usage and not a
limit. `factions` in `descr_sounds_accents.txt` is checked against the mod's
factions, and a faction put under a second accent is named.

**What shipped:** every event's attributes and samples; every `DEFAULT:` line
and setting, a trailing comment kept (`_with_value` in 47a's module keeps
comments now, for both); a selector's values changed in place; a named event
copied under a new name, renamed or removed, each saying that the engine or a
script plays it by name. One backup and 🕑 Log undo per save, mode
`soundscripts`.

**Not taken, and why.** **A selector's block is never copied or removed.**
Selectors nest by indentation and these files keep to it only as a habit:
`looped` sits a tab shallower than the event it wraps, and a setting can sit
level with the selector above it. The tree drawn from indentation is right
for showing where an event is and not certain enough to cut by, so the edits
are all to lines whose extent is certain (one line, or `event` to `end`) and
the screen says so beside the button that is not there. **A bank is not
renamed**: the engine asks for it by name. **`descr_sounds_music_types.txt` is
shown, not edited**: it is written from the campaign map a province at a time,
and 19b renames through it. The four faction-clone sites keep their writers.

The exit named `tests/test_sounds.py`; the round trip is in a suite of its own,
`tests/test_soundscripts.py`, because `test_sounds` is pinned to Third Age
Reforged and fails without it.

#### The scoping, as written before it was built

`descr_sounds_*.txt` is a different shape: `DEFAULT:` directives with key and
value attributes, named `event` blocks, `BANK:` sections, `unit <name>:<type>`
selectors, `hit <type>` conditionals, and `folder` lines with samples under
them. It is a grammar of its own and it deserves what Phase 7 gave triggers,
which is a vocabulary and typed arguments, not a raw-line box. Phase 13
recorded that and did not schedule it; this is the schedule.

**Four of the thirty-two already have writers and keep them.**
`descr_sounds_accents.txt` and `descr_sounds_music.txt` are faction-clone
sites, `export_descr_sounds_prebattle.txt` is another, and
`world/maps/base/descr_sounds_music_types.txt` is the campaign map's music type
and one of 19b's rename sites. Those writers stay where they are; this phase
reads the family and adds an editor beside them, it does not take them over.

Exit for both: every file read and re-rendered byte for byte on all four
installed mods, an editor over the blocks rather than the lines, backup and
undo as everywhere else, and `tests/test_sounds.py` extended with the round
trip per file.

## Phase 48 - The two rows the strings screen cannot add - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** The last of the
2026-09-13 pass. As scoped, and one refusal added after measuring.

- **＋ New entry** on a tagged archive puts a tag box and a text box at the top
  of the table; several can be staged at once. **✕** on a row stages its
  removal, struck through and undoable with ↺. Both go in the one save with
  the edits, through the `adds` and `removes` the plan has taken since Phase 6,
  and Ctrl+Z covers all three.
- **Where the count changes, the page says so:** "10 entries now, 11 after
  saving", with the trailing tag index named beside it when there is one, and
  the plan's own warning repeated in the confirmation.
- **An archive addressed by position** (battle, shared, strat, tooltips) says
  why it takes neither, in the backend's two sentences. They are constants in
  `strings.py` now, `NO_ADD` and `NO_REMOVE`, sent on the entries payload as
  `refused` so the page shows what the plan would say without a copy of it.
- **Added: a new tag with a space or a brace is refused.** Measured over all
  36,219 tags in the installed mods' archives: not one has either, and a brace
  would break the `{tag}text` line of the `.txt` beside the archive. The page
  paints the box red early; the plan is what refuses.
- After a save the screen reopens the archive that was saved rather than the
  list.

`tests/test_strings.py` drives the page's calls through the HTTP layer: the
refusals as served, an add and a remove planned, applied, served back and
undone byte for byte, each bad tag refused, and both refusals on an archive
addressed by position with nothing written.

### The scoping, as written before it was built

**The backend already does it and the screen does not ask.** `strings.plan`
takes `{edits, adds, removes}` and has since Phase 6, with both refusals
already written: an untagged archive cannot take an add ("this archive's
entries have no tags - nothing to add") and cannot take a remove ("removing one
would renumber every entry after it"). `web/js/strings.js` posts `edits` and
nothing else. So a key can be changed and never created or deleted, from a
screen whose whole subject is the keys.

**That is the one thing his `StringsBinEditor` does that ours does not**, and
it is an afternoon: a new-row form on the list, a remove on a row, and the
plan's own warning about the trailing tag index being carried through unchanged
shown where the count changes.

**His reorder is not taken.** `move up` and `move down` on an entry: a tagged
`.strings.bin` stores its entries sorted and the game addresses them by tag, so
there is no order to edit; an untagged one addresses by position, where a move
renumbers every row after it, which is the reason our backend already refuses
the remove on those four archives.

**And the codec is not a port in either direction.** `stringsbin.py` records
two faults in his that cost real files, both confirmed byte for byte against
all 81 archives the test mods ship: he reads `count` as a `u16` plus a padding
word where it is a `u32`, which reads half of any file past 65,536 entries and
Third Age's `names.txt` already carries 20,757; and he writes a single zero
word where the trailing tag index goes, which truncates a file that has one,
and Third Age's `export_buildings` has 480 entries and 13,482 index strings.
Worth passing back with the Phase 31 findings.

Exit: add and remove on the strings screen over the plan that already accepts
them, the two refusals surfaced as the sentences the backend already writes,
and `tests/test_strings.py` covering both through the HTTP layer.

## Phase 49 - Two strips, the colours on the left, and one place for models - DONE 2026-09-16

Asked for directly, with a screenshot of Mylae's map screen attached: `Strat` /
`Validate` / `3D` across the top, `Overview` / `Settlements` / `Factions` /
`Characters` under whichever of those is up, and a third row under that. *"This
looks way cleaner. Where each section when clicked shows the subsections below
and they can also be switched as needed."* Three more things came with it: a
toggle for the layer the brush is writing, the colours it can write on the left
of the map, and the Models Editor.

### The strip 28a built was half the shape

28a is what put the six tabs there, and its own note says why: sixteen panels in
one column meant the strat models sat four screens below the fold. It grouped
them - **six tabs over sixteen panels** - and then **stacked every panel of a
group down one scroll**, which is the same column laid on its side once a group
has seven of them. Province was `cmPick`, `cmRebels`, `cmSettle`, `cmChars`,
`cmForts`, `cmDel` and `cmRecolour`, one under the other.

So a tab is a **group of sub-tabs** and a sub-tab is what is shown, one at a
time. `CMAP_TABS` is two levels deep now and every reader goes through
`cmapTabPanels` (a group's panels, its subs' put end to end) or `cmapSubs`.
Nothing else changed about the DOM: **every panel of every group is still in the
DOM and still keeps its own state**, which is the property 28a's grouping was
built on and the reason moving to two levels cost the sixteen panel modules
nothing.

**Choosing a sub-tab presses the panel's own toggle.** Nine of these read
nothing until somebody clicks their own button, which was right when they were
stacked - a column of sixteen panels that each fetched on sight is a screen that
fetches sixteen times on load - and is wrong behind a tab: clicking `Forts` and
getting a button that says `Forts` is one click the screen owes you. `open: {fn,
at}` on the sub names the toggle and the key its module keeps `open` on, so it
is pressed **once and only when the panel is not already open**. Nothing is read
until the tab is *chosen*, which is the half of the old rule worth keeping - a
restored tab on load still opens closed, and the validator still does not run
itself.

The sub each group is on rides in `cmapLayerState` beside the tab 28a put there,
so it is in every named view for nothing and `cmapResetView` puts it back.
`cmapSurface` - the one thing that keeps the strip from being worse than the
stack - now names a group **and a sub**, because a click on a province that
fills `#cmPick` has to reach a panel that is hidden twice over.

### The colours are beside the tiles they go on

The palette was in the right-hand column behind the Paint tab. A palette is a
thing you reach for on **every stroke**, and that put it two clicks from the map
and took the column away from whatever else it was showing - the region record,
the validator - every time.

It is a column on the **other side of the stage** now, present only while the
brush is armed, holding the three things a stroke needs and nothing else: which
layer, which colour, and what is about to be written. It is wired by
`cpaintWireIn`, the same function that wires the panel and 28b's toolbar row, so
the same controls behave the same in all three and none of them knows where the
others put them.

**The layer is a toggle rather than a dropdown**, which is the user's second
request and is also the one control on this screen you could not read without
opening it: the thing a stroke was about to change was a word behind a click.
Eight buttons, one per paintable layer, and a layer the server could not read is
disabled with its reason on the title rather than left out.

### One editor for a mod's models

"BMDB + Sprites Editor" was already the wrong name for what its strip held -
model entries, sprites, **strat map** and unit cards - and it is **Models
Editor** now. Two things moved to make the name true.

**The strat map's entries get a 3D panel**, the BMDB browser's own: the same
split, the same saved width, the same detach-and-reattach so a keystroke in the
search box does not rebuild the canvas and refetch the mesh. A row's 🧊 draws the
`.CAS` that entry names - `entries` now carries `meshes`, the meshes the mod
**actually ships**, so a row with all of its files in a `.pack` gets no button
rather than a button that opens a 404. **206 of Divide and Conquer's 237 entries
have one.**

**And 16k's model browser came here from the campaign map.** It was a panel in
that screen's side column, where it edited nothing and sat beside nothing else
about models; the same list is now inside this panel, above the canvas. It is
the half that matters most, because **most of what the campaign map draws is in
no entry at all**: the game picks a settlement by level and culture out of
`data/models_strat` with nothing naming the file, which is why Amon Hen and
Minas Tirith are on the map and in `descr_model_strat.txt` nowhere. DaC declares
237 entries and ships **926 model files**.

Still one viewer on the page - `v3MountCas` drops whatever was showing - so this
panel and the BMDB one cannot both be drawing.

## M18 - The map in 3D - DONE 2026-09-20

Asked for directly, the day the contributor's campaign-map commit landed:
*"fully import the 3d map from mylaes tool and add it as a mode in the campaign
map view."* M18 was filed unrated on 2026-09-17 out of the `187d9ed..439aa9b`
review and was the largest of the four; the ask is what turned it into work,
and the "as a mode" in it is the whole of the design decision below.

### A mode, not a screen, and that is what made it small

His 3D is a second map. It carries its own ground-texture loader, its own
feature overlay with its own opacity, its own region overlay with its own two
display modes, a tile-size slider and a matched-pair count - and every one of
those is a second copy of a control the 2D map already has. The two pictures
drift apart the moment either is touched.

**Ours is the same picture, lit and tilted.** `cm3Texture` composes the mesh's
colour map in `cmapPaint`'s own order - 23a's ground, then the one-pixel-a-tile
composite of every ticked layer at its own opacity, then 16g's colouring last
because a tint has to be read against what is under it. So the 3D has **no
layer controls at all**: ticking a layer, dragging an opacity, flipping the
season, changing the gap colour or applying a query colouring all change the
surface, because they change the thing the surface is painted with. The card
over the map carries two switches, a Fit, and two sentences saying so.

That leaves **one hook**, at the top of `cmapPaint`, which is the funnel every
one of those ends in. Keyed on what was last uploaded, so the pans, the hovers
and the resizes that also land there cost a string compare. A list of callers
kept in `map3d.js` would have been a list to forget to add to.

### Three things we did not have to solve, and one we had to correct

| his | ours |
|---|---|
| the ground is sampled one texel to a tile in the browser, which is what the tile-size slider and the "none matched" warning manage | `mapterrain.composite` has drawn it at `SCALE` pixels a tile, supersampled, once a season, since 23a. `c.terrain.img` is that picture already decoded, so the mesh is textured with a blit. No tile cache, no per-pixel loop, no folder to pick |
| the mesh caps at 2048 steps, and the 512 it capped at before dropped one-pixel islands and thin isthmuses | `descr_terrain.txt` caps a map at 510x510 and the heights layer arrives at `fit=tile`. **One vertex per tile, no cap, no resampling** - 248,370 vertices on DaC, 260,100 at the engine's ceiling |
| sea is "the heights pixel is blue **or** the ground type is one of the four water colours" - two rules, because the first alone left sea at land elevation | `mapvocab.is_sea_height`: not greyscale, or black. **One rule**, and `tests/test_map3d.py` runs it against Python's on the installed maps and agrees tile for tile - 74,365 on DaC and 71,968 on ROCSS |

The fourth is not a correction but it is worth writing down: **the vertex
normals are a central difference over the height field**, not an accumulation
over the faces. One pass rather than two, no per-vertex face list, and on a
regular grid it is the same answer. The test checks every normal is a unit
vector, which is the one thing a bad difference would silently not be.

His numbers we did take, because they are right and measured: the sea floor at
`-0.12` of the height scale and the water surface at `-0.04`, so the two cannot
z-fight and a coastline is still a coastline; near and far off the map's own
diagonal, because a `0.1..100000` range on a map this size spends the depth
buffer on distances nothing occupies and gives back z-fighting in bands; and a
fog density tied to that diagonal, because a fixed one swallows a large map
whole.

### Two faults found by testing it, both now guarded by the suite

1. **A bare `requestAnimationFrame` hangs the build.** The mount yields one
   frame so the "Building the mesh" line is on screen before a quarter of a
   million vertices are built on the thread. A browser stops servicing rAF for
   a tab that is not being rendered, so switching tab between the press and the
   build left the promise unresolved **forever**, with the message up, no scene
   and no error. Found exactly that way. `cm3Yield` races the frame against a
   120 ms timer; a hidden tab takes the timer and paints nothing, which is the
   right answer because there was nothing to see.
2. **`loseContext()` does not free a canvas to be drawn on again.** The element
   keeps that context for good and hands the same LOST one to the next
   `getContext`, so turning the mode off and straight back on built a scene
   that never drew - the shader "failed to compile" with a null info log, which
   is what a lost context reports. `cm3Stop` gives the context up properly and
   then swaps the element for a clean `cloneNode(false)` of itself. Three
   off/on cycles and two with no wait between them now come back live and
   unlost.

### What is deliberately not in it

Markers, labels, the selected outline and the hover tooltip. All four are
screen-space drawing over a flat canvas (`cmapOverlay`, `maplabels.js`) and
none of them has a position in a scene. They stay on the 2D map, the card says
so, and `D` puts you back. His does not put them in 3D either.

The mode is **not remembered between sessions**, alone among this screen's
switches. The rest are ways of reading a flat map and cost nothing to open
into; this one opens a WebGL context and builds a mesh, and somebody who looked
at one map in 3D should not find the next mod opening that way. The height
scale and the water plane **are** remembered, and ride in `cmapLayerState`, so
a named view carries them - which is the contract that comment states for any
switch added to this screen.

Exit: `web/js/map3d.js`, a `⛰ 3D` button on the map toolbar and a `D` key, the
card, `cm3DropOrphan` beside `v3DropOrphan` in `applyMode`, and
`tests/test_map3d.py` - 34 checks, the mesh run for real in node against both
installed maps.

---

## The contributor's campaign map editor, 2026-09-20, and what it did not close

`865c22f`, one commit, 18 files and 870 insertions, on the campaign map
workspace only. Merged; our two port commits rebased on top of it with no
conflict, and nothing of ours was overwritten - it never touches `app.py`,
`startup.py` or `build_release.py`.

**It closes no open item on this roadmap, and that is the finding rather than a
complaint.** What it does is extend seven that are already done: 17d's markers
(character-type symbols, faction colours, port anchors, a highlight ring, a
chooser for a tile holding several), 17e's hover (the terrain list off the
ordinary card, the detail kept in the clicked-tile inspector), 20b's find box
(an alphabetical browse list when the query is empty, and the rows are buttons
with an `aria-pressed` now), 20c's labels and pin (character names, army unit
counts, port names in the same collision-avoiding layout), 22a/22b's placement
(a `+ Create` panel over the existing guided workflow), and 28a/28b/49/50's
workspace (the bar at the bottom, a compact toolbar, a help panel, focus
indicators).

**Two things to be clear about.** The searchable region browser is **not**
M10's region search arriving: M10 is an OSM backdrop and a region search
together, three stars, and it is `Phase 25` in the Future list, off by default
because it is the first thing in the toolkit that touches the network. Our own
find box has existed since 20b, and what landed is a browse list on it. And
**character editing on the map is genuinely new and was never tracked** - the
character form, traits, ancillaries, army composition and upgrade controls
brought into the map workflow, with roster data in the marker response so a
hover needs no second request. It is not on this roadmap because nobody put it
there.

---

## The 2026-09-13 pass, and the two parts of it that produced a measurement

**Traits and ancillaries are still level, and the way to know is the date.**
`src/components/traits/` and `src/components/ancillaries/` were last touched
upstream at `4323ef9` on **2026-03-27**, and `src/components/shared/` - the
trigger and condition half both of his editors use - at `ef523e3` on
**2026-03-25**. `docs/upstream/audit-traits.md` and `audit-ancillaries.md` were
both written against code newer than that, and both verdicts stand as written:
every field he exposes we expose, his serialiser rewrites the whole file and is
refused, his `Type` and `ExcludeCultures` dropdowns are hardcoded lists that
337 of the installed mods' 350 real `Type` values fall outside, and his trigger
half keeps each condition as a raw string so it has no vocabulary and no
never-fires check. Nothing new to compare against. Re-check with
`dev/reference/upstream_sync.py sync` before believing this a second time.

**The strings codec goes the other way, and so does the map validator.** Three
things are now worth passing back to him in one message rather than three: the
`u16` count and the missing tag index in `stringsBinCodec.jsx` (Phase 48), the
orphan-white-source severity that makes his own validator call vanilla broken
at image (175,14), and that the standalone `map_features_checker.py` he ported
from cannot open either installed map because both ship RLE TGAs (both
Phase 31).

---

## The 2026-09-17 pass: his model reader is ours, and four things are ours to build

`187d9ed..439aa9b`, **34 commits and 49 files**, the largest sync since the
mirror was set up, and the manifest is at **342 files with none untriaged**. Two
halves, and they point in opposite directions.

### The asset half is our own code, come back as JavaScript

`src/lib/m2CasCodec.js` and `src/lib/m2MeshCodec.js` are **`unittransfer/cas.py`
and `unittransfer/mesh.py` transliterated**. Not the same knowledge arrived at
twice - the same names, the same numbers and the same comments:

| ours | his | value |
|---|---|---|
| `NODE_COUNT_AT` | `NODE_COUNT_AT` | `0x32` |
| `NODE_TRAILER` | `NODE_TRAILER` | `25` |
| `OBJECT_HEADER` | `OBJECT_HEADER` | `{1: 37, 2: 28}` |
| `CHUNK_TRAILER` / `_OLD` | `CHUNK_TRAILER` / `_OLD` | `{1:6, 2:4}` / `{1:3, 2:4}` |
| `TRAILER_VERSION` | `TRAILER_VERSION` | `3.17` |
| `NO_MATERIAL` | `NO_MATERIAL` | `0xFFFFFFFF` |
| `MATERIAL_TAIL` | `MATERIAL_TAIL` | `29` |
| `BOOST_SIGNATURE`, `STREAM_STRIDE`, `STREAM_GAP`, `MAX_TRAILER` | the same four | `serialization::archive`, the same stride table, `96`, `64 * 1024` |

`cas.py:378` carries the comment `# over the two RGB triples` on the line that
seeks to `NODE_COUNT_AT`; `m2CasCodec.js:166` carries `// over the two RGB
triples` on the same line. **The dates line up with the direction**: `cas.py`
has been public here since 2026-09-06 and Phase 29 landed on 2026-09-12, his
file first appears on 2026-09-14, and the header of the `casCodec.js` he deleted
to make room says in his own words that the spec it had was invented and
"matches no real game file".

**Nothing to do about it and nothing to take from it.** The README credits his
tool as a reference and this is the same traffic in the other direction. What it
changes is the manifest: `m2CasCodec.js`, `m2MeshCodec.js`, `boostArchive.js`
and `m2ModelGeometry.js` are **`skip` - something we own outright**, and the
asset half of the port-concept set is closed. Reading his `.cas` work for format
knowledge from here on is reading our own back.

### Four candidates, filed as M18 to M21, and none of them rated yet

Full write-ups in `docs/upstream/REFERENCE_GAPS.md`. They are unrated on purpose:
the user rates, and a rating is what turns one of these into a phase.

**M18 is done, and it was asked for rather than rated** - on 2026-09-20, three
days after being filed. That is the other way one of these becomes work, and
the row below is struck through rather than removed so the ballot still reads
as it stood. M19, M20 and M21 are still unrated.

| Item | Size | What it is | Why it is worth a star |
|---|---|---|---|
| **M16, the playback half** | M | Sample an animation file onto the skeleton the viewer already draws. Joints are matched by name, the pose is a delta from the bind quaternion, slerped between key times, 25 fps when the file carries no ticks. | `cas.py` already reads the container and already names `data/animations`' 305 files as future expansion. The editor half of M16 stays out of scope; this is the half that is a session. |
| ~~**M18 - the map in 3D**~~ | L | The heightmap as a mesh with the ground textures on it, orbited. | **DONE 2026-09-20**, asked for directly rather than rated, and it came in well under L for the reason the last column predicted: `mapterrain.composite` already solved the textures, so it is a mode over the stack the screen was holding and not a second map. Write-up above under *M18 - The map in 3D*. |
| **M19 - climates past the twelfth** | M | His four generated files are Phase 34's four. What is new is the claim that **M2EX** lifts the twelve-name wall Phase 34 stopped at. | Verify first. If it holds, appending a name becomes the first option on an M2EX mod and `too-many-climates` joins `modflags.CAP_FINDINGS`. |
| **M20 - a scatter brush** | S | A sixth tool that scatters `round(pi * r^2 * 0.12)` pixels in the brush radius. | His own use for it is `forest_sparse`, the ground type a pencil cannot make look right. The toolbar and the palette column are already there. |
| **M21 - `texture_density`** | S | A root-level directive in `descr_aerial_map_ground_types.txt`, `span = max(1, 8 / density)`. | **`mapterrain.parse` drops the line today.** Measure the installed mods: nobody declares it and this is one read and a scale, somebody declares it and 23a has been tiling at the wrong rate. |

**The Koppen tool is not a new item.** One climate per Koppen-Geiger zone in one
press, seeded from a static table of 30 codes and their legend colours with no
network call in it, which is `koppenZones.js` and the bulk-add in
`CustomClimateForm.jsx`. That is Phase 27's bucket since the 2026-09-03
reclassification, and it is already rated three stars there. The table itself is
portable as it stands.

### Three things to send back to him, in one message

1. **The pixelated textures.** Draw the ground at several pixels a tile and
   supersample the tiling, once per season, rather than sampling one texel per
   tile at draw time - 23a's `SCALE`, and 37b's finding that a picture scaled
   into a per-tile composite and back out is the artefact.
2. **`texture_density` cuts both ways.** If we are dropping the line, he should
   check that `spanForDensity` is reading it from the root and not from a
   climate block.
3. The three from 2026-09-13 that have not been sent yet: the `u16` count and
   the missing tag index in `stringsBinCodec.jsx`, the orphan-white severity
   that makes his validator call vanilla broken at image (175,14), and the RLE
   TGAs that stop `map_features_checker.py` opening either installed map.

---

---

# Future roadmap - rated, and waiting on the two main tasks

**This is one list and it replaces two.** The Later table of 2026-09-05 and the
TWCenter candidate tables of 2026-09-12 said different things about the same
work in two places, which is how the old `ROADMAP.md` reached three thousand
lines. They are merged here.

**Where the ratings came from.** The user rated 38 of 39 candidates one to five
stars on 2026-09-12. Everything rated **four or five stars that is campaign-map
or mercenary work became a phase** above; everything else is below, ordered by
stars and then by size. The one unrated row is at the foot.

**The 2026-09-05 triage board is gone and nothing was lost with it.** It was
published as an artifact and is no longer in the gallery, but its output was
copied into this file at the time as the Later table, all thirteen items: D1,
D12, D13, G2, G4, M7, M12, M16, M17, T3, T6, T7 and T10. Every one of those
thirteen was on the 2026-09-12 ballot and every one now carries a rating, so the
two selections are already reconciled. Six of them were promoted - **D1, G2, G4,
T3, T7 and T10 all rated five stars** and are Phases 33, 36 and 37 - and the
other seven are below.

**Two items were promoted out of their own rating**, and both deserve saying:

- **The mercenary repairs (five stars, S)** are not a phase of their own. They
  are 32c, because a rule and the repair for it are one piece of work and
  splitting them is how a validator ends up with findings nobody can act on.
- **The EDU ceilings (three stars, M)** were pulled up into Phase 39 by the
  20,000-face model ceiling beside them, which rated four. Both come out of one
  document and neither is a session on its own.

## Five stars, and first in the queue when the two main tasks land

| Item | Size | What it is |
|---|---|---|
| **M17 - a crash and validation dashboard** | M | We have more validators than any of the four reference tools and no single door to them: 32 map rules, the faction audit, the EDB checks, the BMDB audit, the sounds audit, and after Phase 32 five mercenary rules as well. The archive's two crash guides, *GUIDE - Crashes and how to fix them* and *Crash to Desktop*, are the checklist that would give them one front page. |
| **M12 - bulk faction duplicate, and faction zip export** | M | One plan over `factionclone.py` repeated, plus `pack.py`. Mylae shipped his version in September 2026 and it is in the mirror at `DuplicateFactionModal.jsx`, `FactionZipExport.jsx` and `factionBulkDuplicate.js`, all three triaged port-concept. |
| **M16 - animation editor and asset converter** | L | Excluded originally because we could not read `.mesh` or `.cas`. **15a and 16k both now can**, so the exclusion no longer holds on its own terms and the item is live again on the merits. |

## Four stars

| Item | Size | What it is |
|---|---|---|
| **Will this mod even launch** | S | A readiness row on the Home card, not an editor. Home already says what each mod is ready for and cannot say whether `configuration.cfg`, `mymod.cfg` and the registry entry will actually start it. Eleven archive documents including the Steam install and registry tutorials. |
| **B2 - delete a settlement, and move one between mods** | M | Assigning a settlement to a faction already works and B1 added the create. Missing: the delete, whose shape is `stratcamp._delete_splice`; a button on the panel for a province that has none; and the between-mods move, which is probably its own session. Phase 24's warning applies - a settlement that goes has characters, armies and a capital flag hanging off it. |
| **B3 - insert and export one file at a time** | M | Mylae's tool pushes a file into, or pulls one out of, a mod on its own. Pieces exist - `POST /api/map/export`, 16g's per-faction TGA, `pack.py`'s unit import - and none of it is a general take-this-file-out. The user's own earlier words were "that isnt really needed tbh"; the four-star rating supersedes that. |
| **Add a religion** | M | We edit the religion list in Minor Files, the EDB conditions and the religion columns on the region form. Missing: `descr_religions_lookup.txt`, and the must-sum-to-100 rule as a guard at **creation** rather than only as a validation afterwards. |
| **Mines and hidden resources** | S | **Halved on 2026-09-13: the hidden-resources half is Phase 45, done 2026-09-21**, which adds and removes on the EDB's own line with the two joins that make a removal safe. What is left here is `descr_settlement_mechanics.xml` and the ceiling of 63, which Divide and Conquer's 75 disproves as written and which belongs with Phase 39's other ceilings if that session has room. |

## Three stars

Ordered small to large, because at this rating size is what decides whether one
is worth picking up.

| Item | Size | Note |
|---|---|---|
| `descr_settlement_mechanics.xml` | S | 187 lines, 10 tags. Named by the Mines tutorial, so it may arrive with that item instead. |
| `descr_lbc_db.txt` | S | 122 lines. Read by three modules as a faction site and never parsed. |
| `descr_offmap_models.txt` | S | 619 lines. Same shape: a faction site the audit counts mentions in. Cheap as a `flatrecord` if the audit ever wants the contents. |
| `descr_animals.txt`, `descr_standards.txt`, `export_descr_advice.txt` | S | 41, 23 and 6 lines. Third Age Reforged ships no `descr_standards.txt` at all and DaC's advice file is six lines, so this is one small session for all three or none. |
| `descr_banners_new.xml` | M | 405 lines, 25 tags. Every *add a faction* tutorial names it and the faction audit has a row-shaped hole where it should be. |
| `descr_hero_abilities.xml` | M | 1,187 lines, 26 tags. Hangs off the people panel, which already edits the character. |
| `descr_area_effects.xml` | M | 555 lines, 34 tags. Interdict, excommunication and the rest. |
| `descr_walls.txt` | M | 514 lines. Wall definitions per culture and level; pairs with the settlement panel. |
| `descr_character.txt` | M | 1,708 lines, twelve archive documents, **read by six modules and written by none**. It is the missing join: `stratmap.py`'s audit names a `.cas`, the Strat models panel draws one, and nothing connects either to the character that uses it. The lowest-rated item on this page that the measurement argues hardest for. |
| **T6 - export every tile as text** | M | Campaign-map work that did not rate high enough to schedule. We export pictures and never numbers; `mapquery`'s fact table is the join it needs. |
| **D12 - export the project as a zip, and load one back** | M | `pack.py` already does this shape for a unit, import and conflict report included. |
| **D13 - generate a horde start for a new faction** | M | 16j-2 already creates a faction with no settlement and no character, which is the shape vanilla's Mongols already are. This is the other half. |
| ~~The three voice files~~ | M | **Became Phase 47a on 2026-09-13**, with three more export files beside them and at M rather than L: `sounds.py` already reads that grammar, so the cost was the size and the size is not the parser. |
| **M7 - import a campaign from another mod** | L | Unit Transfer's problem at campaign scale; `transfer.py` is the model. |
| **Phase 25 - OSM backdrop and coastline tracer** | L | Campaign-map work at three stars. The write-up below stands; it is the first thing in the toolkit that touches the network, so it is opt-in and off by default. |
| **Phase 26 - map resize, and create from scratch** | L | Campaign-map work at three stars. Phases 22 and 24 removed most of the original objection, so it is cheaper than when it was deferred. |
| **Phase 27 - overlay and layer generators** | L | Campaign-map work at three stars. Same opt-in rule as 25. |

## Unrated, and the rating is not the reason

**`battle.sd`, `strategy.sd`, `shared.sd`** - the interface skins, 23 archive
documents between them and a dedicated editor already in the archive
(`m2_sd_editor`). It was left unrated and it is the one row on the ballot that
argued against itself: this is GUI skinning rather than mod data. It stays here
so the decision is recorded rather than rediscovered.

---

# Not scheduled, and previously mis-numbered

These three were called `V3.1`, `V3.2` and `V3.3`. They are phases now, with no
version attached, and none of them is in either block above. **All three were
rated three stars on 2026-09-12** and are listed in *Future roadmap* with
everything else at that rating; the write-ups stay here because they are longer
than a table row.

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
| `ROADMAP.md` | locked decisions, phase index, the map-format reference, the backlog | only when work is added or a decision is locked |
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
