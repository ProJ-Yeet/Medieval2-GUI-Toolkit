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
| the strict release rules | `HANDOFF.md` |

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
| `unittransfer/mapcheck.py` | the 30 rules, the baseline and the three auto-fixes (16f) |
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
| next, block one | ~~29~~, 28, 33, 30, 34, 35, 36, 37a, 37b, 31, 38 | **The campaign map.** Ten sessions left, in that order. All beta except 38, which is a subrelease on both lines. 29 landed on 2026-09-12. |
| next, block two | 32a, 32b, 32c, 39 | **The mercenaries.** Four sessions. Beta except 39, which is both lines. |
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
discharged the instruction of 2026-09-11, so **the cut-as-it-lands rule of
2026-09-09 is live again** and each session cuts as it lands - which Phase 29
then did, as a subrelease on both lines.

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

**Phases 28 to 39 below are what reopened it.** They come from one review on
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

### Block one - the campaign map

| Order | Phase | Size | Line | Stars |
|---|---|---|---|---|
| ~~1~~ | ~~**29** Strat model viewer~~ | M | **both** | **done 2026-09-12** |
| 2 | **28** The right menu becomes a menu | M | beta | an enabler |
| 3 | **33** T10, G2 and G4 in one session | S x3 | beta | 5, 5, 5 |
| 4 | **30** A missing texture without the pink | S | beta | reported |
| 5 | **34** Add a climate zone | M | beta | 5 |
| 6 | **35** Rebels right in place | M | beta | 5 |
| 7 | **36** D1, change a region's colour | M | beta | 5 |
| 8 | **37a** T7, the spawn export | M | beta | 5 |
| 9 | **37b** T3, an FE zoom | M | beta | 5 |
| 10 | **31** Four river rules | M | beta | cross-reference |
| 11 | **38** `descr_campaign_db.xml` | M | **both** | 4 |

### Block two - the mercenaries

| Order | Phase | Size | Line | Stars |
|---|---|---|---|---|
| 12 | **32a** The pool as a record, and one parser for it | M | beta | the main task |
| 13 | **32b** The two directions, and the four gates resolved | M | beta | the main task |
| 14 | **32c** Five rules, and the repair for the one that has a safe answer | M | beta | 5 (the repairs) |
| 15 | **39** The engine ceilings | M | **both** | 4 and 3 |

**Fifteen sessions, and three of them are subreleases.** 29, 38 and 39 touch
something outside the campaign map, so each is a subrelease on both lines; the
other twelve are the beta alone. **29 is done** (2026-09-12) and took B4 with
it; fourteen remain. **The cut-as-it-lands rule of 2026-09-09 is
live**, so each one goes out as it lands rather than being held for the end.

---
# Phases 28-39 - the campaign map, then the mercenaries

## Phase 28 - The right menu becomes a menu

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

Exit: the strip on top, the panels grouped behind it, a click that fills a
panel switching to it, the drag, the collapse, and all three habits in
`cmapLayerState` and therefore in a saved view. `tests/test_web_modules.py`
takes the grouping table the way it takes `MODES`.

## Phase 30 - A missing texture without the pink

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

## Phase 31 - The river rules we do not have

**A cross-reference, not a report.** `map_features_checker.py`, a standalone
validator handed over on 2026-09-12, checks six things about
`map_features.tga` and repairs five of them. Ours has three river rules -
`river.diagonal`, `river.isolated` and `river.rejoin` - and `feature.unknown`
for the colours. Four of its checks have no rule here:

| its check | ours |
|---|---|
| a blue tile with more than three river neighbours (a four-way crossing) | nothing |
| a 2x2 block of river tiles | nothing |
| a white source pixel touching no river | nothing |
| a river component with no white source anywhere on it | nothing |

All four are already in this document's own river rules, taken from Geomod and
TWMapReader: *white pixel at the source*, *no rejoins*, *no diagonals*. We
wrote the source rule down and never checked it.

**Measured on both installed maps before scheduling it, and it finds
nothing.** Divide and Conquer: 95 river components, every one with a source,
no crossings, no 2x2 blocks, no orphan whites, no isolated tiles, and the one
`(1,1,1)` pixel this document already records as a live test case. Third Age
Reforged: 86 components, all clean. **So this is not a bug we ship.** It is
four rules for a map being built, and it is worth a session because the
repairs come with them and 16f's three auto-fixes are the shape.

**And the tool it came from cannot read either installed map.** It refuses
anything that is not uncompressed true-colour, and both mods ship
`map_features.tga` as image type 10, RLE: DaC at 32-bit, Third Age Reforged at
24. `maptga.py` reads and re-encodes all ten of DaC's layers byte for byte
with the RLE intact, which is why the four checks could be measured here at
all. Worth passing back.

**One rule needs deciding before it is written.** Geomod also says a river
must *extend two pixels past the coastline*. That is a rule about a river's
mouth against `map_heights.tga` rather than about `map_features.tga` alone,
and it is the only one of the five that needs a second layer. Scope it, and
leave it out rather than half-check it.

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

### What this is not

**Not a mercenary unit editor.** The unit itself is EDU's and the unit editor
already owns it; this edits the *pool entry*, which is a different record with
different fields, and a dead reference is fixed by naming a unit that exists,
not by inventing one. The two screens link to each other and neither grows the
other's fields.

## Phase 33 - Three small map wins in one session

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

## Phase 34 - Add a climate zone

Every file is already parsed and the brush already paints the layer:
`map_climates.tga`, `descr_climates.txt` and
`descr_aerial_map_ground_types.txt`. **What is missing is the operation**, and
the archive has a tutorial for it that names exactly those files plus
`map_ground_types.tga`.

Declaring a climate is three writes that have to agree or the map is wrong in a
way nothing reports: a name and its parameters in `descr_climates.txt`, a
colour in `map_climates.tga` that `mapvocab` can then name, and a texture for
every ground type it pairs with, **in both seasons**, in
`descr_aerial_map_ground_types.txt`. 23b's `season_gaps` already judges both
seasons, so the check exists; what does not exist is anything that creates the
three together.

**This is where Phase 30 pays for itself.** A climate declared without its
textures is pink across every tile that uses it, which is the largest pink
anyone will ever produce here, and it is produced by the one operation this
phase adds. Do 30 first so the gap is legible rather than alarming.

## Phase 35 - Rebels right in place: province and rebel faction, both ways

**Phase 32's shape applied to the other per-province pool, and simpler.** A
province names one rebel faction in its `descr_regions.txt` record and
`info_rebels` already colours the map by it. What is missing is everything in
the other direction: take a rebel faction and see its provinces, see what it
can actually field, and change the assignment from either end.

`descr_rebel_factions.txt` is already `flatrecord`'s - Phase 11 needed no
parser for it at all - and the region record is already spliced by 16d. So this
is a join and a screen rather than a format, which is exactly why it is worth
doing **before** Phase 32 rather than after: it is the same two-way pattern over
a file that is already fully read, so the panel shape gets settled on the cheap
problem and 32b inherits it.

The archive has a whole tutorial on getting this wrong (Errabundi's *Rebels
Right in Place*), whose complaint is Bulgarian rebels spawning in Serbia. That
is a fact about which faction a province names, and it is invisible today
unless you colour the whole map and look.

## Phase 36 - D1: change a region's colour

**The one item in 19b's cluster that the rename work did not make cheaper**, and
the cost is real rather than assumed: region IDs are the order of first
appearance in a row-major scan over `map_regions.tga`, so changing one colour
can **renumber every region after it**. A rename does not, which is why 19b
could be done first and this could not.

So the operation is not a recolour, it is a recolour plus the renumbering it
causes, and what the panel has to show before it writes is which regions move
and what reads an ID. 16f already refuses to leave a region with no tiles and
already warns that a change here renumbers; `regiondel` learned the same lesson
from the other side in 24. Both of those are the guard this needs.

`campaint`'s stroke engine writes the pixels and `mapquery.assign_colours`
already knows which colours clash with the reserved ones and with each other,
so the picker is the existing one.

## Phase 37 - The two exports the map screen cannot do

Both five stars, both **M**, both a reader over facts we hold. Two sessions.

### 37a - T7, the spawn export

A read-only scan for spawn coordinates across `descr_strat.txt` and the
campaign script. **Far smaller than a script parser**, and that distinction is
the whole point: 19b had to refuse to write the campaign script because it is a
grammar nothing here models, and 24 kept that refusal. Reading coordinates out
of it is not writing it, so the refusal stands and this still works. It is the
one thing the script holds that the map screen cannot see.

### 37b - T3, an FE zoom for authoring map_FE.tga

The front-end map is the one picture on this screen nothing here helps anyone
author. It pairs with 16g's per-faction TGA export, which already produces a
per-faction picture at map resolution; what is missing is the frame, the scale
and the export at the size `map_FE.tga` actually wants.

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

## Blocked - Mylae's improved validation and his coloured overlays

He reports a settlement-position validation that alerts on an invalid
position, some bug fixes, and coloured overlay export for religion, the
faction creator and faction owners. **None of it is on GitHub.**
`Machiavello-1441/m2tw-editor` is still at `2740b0b` (2026-09-08, "Update
base44 packages"), `main` is the only branch, and the account has no second
repository. `upstream_sync.py sync` reports up to date and it is right.

**So this cannot be diffed yet, and what we already have says it may not need
to be.** Ours judges a settlement position on four rules - `marker.ground`,
`marker.feature`, `marker.sea` and `marker.orphan` - and since 22b a refusal
also names the nearest tile that would do, through `mapsnap.nearest`, which is
more than an alert. His coloured overlays are 16g's colourings and the
per-faction TGA export. Re-run `sync` before scoping anything; if he has not
pushed, ask for the files rather than guessing from the sentence.

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
| **Mines and hidden resources** | M | `descr_sm_resources.txt` is in Minor Files and the EDB conditions are ours. Missing: `descr_settlement_mechanics.xml`, and the hidden-resource ceiling of 63, which is a crash when crossed and belongs with Phase 39's other ceilings if that session has room. |

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
| The three voice files | L | `export_descr_sounds_soldier_voice.txt` (16,145 lines), `..._stratmap_voice.txt` (16,156) and `..._units_battle_events.txt` (7,329). `sounds.py` is the shape; the cost is the size. The accent tutorial names all three together, so they are one job or none. |
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
