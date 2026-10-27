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

Since 2026-10-06 a phase is one major feature, built start to finish (see the
schedule); its lettered pieces are commits, not stopping points. A session doing roadmap work
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
| 89 | Four reports from users: the resource list open on M2EX, a new resource, a watchtower's line of sight, the real-world map | v2.4.1 (a, b); beta 2026-09-30 (c, d) |
| 90 | A layout that fits the window at every interface size | v2.4.1 |
| 91 | A cloned faction's missing faction button, shield and three campaign files | v2.4.1 |
| 92 | Four things another import tool does that Unit Transfer does not | v2.4.1 |
| 93 | Two reports on getting around | v2.4.1 |
| 94 | A recruitment screen that lags, and its turns | v2.4.1 |
| 95 | The Models Editor rebuilt around Armory Studio 3D, 95a-95m | v2.4.6 (a-d); beta 2026-10-15 (e-m) |
| 98 | Six reports: the Spanish wording, Ko-fi, the Strat map panel, building art, texture paths, vanilla out of the packs | v2.4.6 |
| 99 | Armory Studio after its first use, 99a-99o | beta 2026-10-15 |
| 100 | Armory Studio's second round, and faction cards in the Unit Editor, 100a-100n | uncut |

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
the small release zip (50-55 MB then, about 22 MB since 98f) and the disk
headroom on `D:`. Speed comes from four
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
on its own.

**Regrouped by major feature on 2026-10-06**, when the work moved to a new
machine on a larger plan (the user: "no need to partition based on 5 hour
basis but rather partition based on major features"). A row below is one
feature, built start to finish in one go. The old letter splits (89a-89d,
90a-90c, 92a-92d, 93a-93b, 94a-94b) stay in each write-up as the **pieces**
of the feature and the order to build them in, not as places to stop; each
piece is still its own commit. The same day the user put the kitbash
workbench first ("the next major feature i want you to implement is a port
of armorystudio3d") and brought back Japanese, Korean, Turkish and
Portuguese. The order is now:

**Grouped into five major phases on 2026-10-06** (the user: "group all the
existing phases into major phases"). A major phase is the unit of work on the
new machine; the numbered phases inside it keep their numbers and write-ups,
and their lettered pieces are commits. Build the majors in this order.

| Major | Phase | Feature | Pieces | Line |
|---|---|---|---|---|
| **I c. Armory Studio, what is left** | 99p | SimpleBake's two ideas for the packer: holes and side pockets filled, free rotation as an opt-in. **Done 2026-10-20** | one | both |
| **II. Campaign map** | 97 | The map viewer, 2D and 3D: editable and selectable in 3D, floating faction names by default, an icons toggle, agents and settlements as 3D models on their tiles | 97a-97d | beta |
| | 96b-96d | Two layout faults (the green box, the bottom gap), ports and the capital by icon with one port per region, the garrison in the settlement editor | 96b, 96c, 96d | beta |
| | 96e4 | A new region wizard; many towns at once with auto-garrison | one | beta |
| **III. Factions, units and mod data** | 96a | `can_homeless` on M2EX mods | one | both |
| | 96e1-3, 96e5-7 | From the Oogway editor: the script builder and add-ons, checking (log, deep check, report), characters (family tree, portraits), units (model swap, voices), art (emblem, banners, recolouring), rules and mods (vanilla values, hard-link mod folders) | six areas | both |
| **V. Translations** | 88 | The remaining catalogues through 88d's workflow: 88e French, 88h Portuguese (Brazil), 88i Polish, 88l Turkish, 88m Russian, 88o Simplified Chinese with the CJK fonts and line breaking, 88p Traditional Chinese, 88q Japanese, 88r Korean | nine catalogues | both |

**Finished phases archived on 2026-10-20** (the user: "archive the completed phases"): 77-86, 89-95, 98, 99 (but 99p) and 100 moved to `ROADMAP_ARCHIVE.md` verbatim, their rows up into the phase index. The rows this table still held for 89-94 were left over from the 2026-10-06 regroup: all six were finished on 2026-09-30, so major IV, which was 90 and 93, is gone with them.

**Phase 100 put next on 2026-10-19** (the user: "Add all these as immediate
next step to our roadmap"): Armory Studio requests, a weights bug and a
player's Unit Editor suggestion, ahead of 99p and major II.

**Phase 99 put next on 2026-10-15** (the user: "Add these as immediate next
phase"): fifteen requests after the first model out of Armory Studio, ahead
of major II.

**Phase 98 put first on 2026-10-13** (the user: "Add all these into our
roadmap as immediate next phase"): six reports, ahead of major I.

On 2026-10-13 the user first sent 98a to the end with the languages ("move
all languages to the end for now"), then took it back the same day ("i meant
only move the new languages at the end"): **the catalogues already shipped,
German and Spanish, are kept whole as work lands**, every new string
translated in the same commit; only the languages not started yet wait for
major V.

Translations stay last on the user's 2026-09-30 word, so every string the
other majors add is translated once.

Done so far in 88: 88a-88c (the plumbing, every string externalised, the
termbase), 88d German and the per-language workflow (2026-10-01), 88f
Spanish (2026-10-02). In 88, 88o comes before 88p, 88q and 88r because it
lays the CJK groundwork the other three use; the European ones can go in any
order.

**Still postponed indefinitely:** 88g Italian, 88j Czech, 88k Hungarian, 88n
Ukrainian, and 88t Arabic with 88s, the right-to-left layout, which only
Arabic needs. Their write-ups below stay as the plan for when they come back;
their termbase columns stay, and nothing offers them while they have no
catalogue. The history: all of these plus Portuguese, Polish and Turkish were
postponed on 2026-10-01 ("Postpone italian, portugese, polish, czech,
hungarian, turkish, arabic indefinitely for now"), Polish was brought back the
same day, Ukrainian, Japanese and Korean were postponed after it, and on
2026-10-06 Japanese, Korean, Turkish and Portuguese came back ("bring back
Japanese, Korean, Turkish, Portugese").

Releasing stays on request: each piece is committed to master as it lands.

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
`tr`, 88m Russian `ru`, 88n Ukrainian `uk`. **88g, 88j, 88k and 88n are
postponed indefinitely** (2026-10-01; 88h and 88l came back on 2026-10-06,
see the schedule). Each is the catalogue only,
through 88d's workflow. Polish, Czech, Russian and Ukrainian carry three or
four plural forms each, and the checker holds every `ttN` string to them.
Done when, for each: the checker passes, the report is empty, and Home,
Settings, Transfer and the map are walked in it at desktop width.

*88e done 2026-10-26.* **French**: 9,605 strings, including 378 plural
objects with one/many/other, zero missing, stale or extra IDs and zero checker
problems. Offered in Settings as *Français (French) - brouillon*. Polite
vous, infinitive buttons and the French termbase. Home, Settings, Transfer
and the campaign map walked at desktop and 375 px; the wider module review
also found narrow-layout fixes for Home, Armory Studio and My Changes.
`tests.test_i18n` 37/37 and `tests.test_web_modules` 120/120 passed.
Source-hash stale detection checked without changing English on disk.
Native review is pending; terminology, exact exceptions and remaining
source-side localization gaps are in `dev/i18n/fr-review.md`. No release cut.

*88f done 2026-10-02, ahead of 88e on the user's word ("start spanish
next").* **Spanish**: 8,120 strings, 0 problems, offered in Settings as
*Español (Spanish) - borrador*. Spain Spanish as the Spanish release of the
game, *tú* but impersonal where it can be, infinitive buttons, «…».
`dev/i18n/es.md` is the style guide and the review notes. 92 strings by hand
to set the voice, the rest in eight batches by helpers held to the guide and
the checker. The Spanish termbase column narrowed where it collided:
ancillary *séquito*, tier *grado* (level is *nivel*), log *Historial*
(record is *registro*), add *Añadir*, tooltip *descripción emergente*; the
stems of battle model, strat model, mount and view take their plurals and
participles. Every module measured for clipped text at desktop width, and
Home, Transfer, the map, My Changes, the unit editor, Buildings and Settings
at 375 px: nothing clipped but the mod's own unit names, no sideways scroll.

**What translating turned up**, fixed for every language: the trigger
editor's *and*/*or* joiner was read back from its translated label, so a
German user wrote `oder` into the trigger file (the options now carry
`value`); about thirty sites filled a placeholder with English typed in the
code (`' has'`/`'s have'`, `'an'`, `'wider'`, `'summer or winter'`,
`' to '`, `'(nobody)'`...), now whole sentences, plurals or translated
values (42 new IDs, 8,162 in all). **Still English from the server**: the
`noun` in the `eng.minorfiles`, `eng.flatrecord` and `eng.portrecords`
messages, Home's module rows (`_module_rows` in `modfiles.py`), the
`{tail}` clause `mapcheck.py` builds for an unreachable settlement, and the
terrain names in the ground messages; My Changes no longer throws when it is reopened before its first
load lands. German's 8 strings from the 2026-10-01 transfer fixes were
filled.

**88o - Simplified Chinese, and the CJK groundwork.** The `zh-Hans`
catalogue, plus what all four CJK languages share: a font fallback stack of
Windows system fonts per language (Microsoft YaHei, Microsoft JhengHei, Yu
Gothic UI, Malgun Gothic), line breaking set for CJK, and no synthetic
italics or letter spacing on CJK text. Done when: the checker passes, and
every screen renders with no missing-glyph boxes and no line broken inside a
word.

**88p to 88r - the other CJK languages, one each** (88q and 88r were
postponed on 2026-10-01 and brought back on 2026-10-06): 88p Chinese
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

# Phase 96 - five suggestions from the user, scheduled 2026-10-06

Sent by the user on 2026-10-06 with screenshots, to be stored and not acted
on yet ("Store all changes in roadmap dont act rn"). After 95 in the schedule.

**96a - `can_homeless` on a mod that runs on M2EX.** The user: "make this
available to the user when the checkbox for 'Runs on M2EX no Engine Limits'
is checked ... Just be mindful to not allow it to be available to Papal
states and Rebels." A `yes`/`no` line in a `descr_sm_factions.txt` record,
**placed before `can_sap`**, as the user's example shows:

```
custom_battle_availability   yes
can_homeless                 yes
can_sap                      no
prefers_naval_invasions      yes
```

What it does, from the user's reference: a faction with no settlements but a
leader and an army tries to take the nearest settlement, horde-like (Rome 2
style), with no horde units and no sacking, and shows on the minimap as a
horde with a star; it works for any faction except the Senate and the slave
and papal factions. In the faction form it is offered only when
`modflags.is_m2ex(mod)` is true (the Home card's flag), and never for
`papal_states` or `slave`. Where the field order and the yes/no fields live:
`factions.py:85`, `:93` and `YES_NO` at `:103`. A record that already has the
line on a mod not marked M2EX is shown and kept, never removed.

**96b - two layout faults on the campaign map.** A stray green box at the
top middle of the screen, above the `+487 · 403 of 612 named` count in the
user's screenshot (an empty element drawn with a fill; find it, don't
restyle around it); and an unused gap along the bottom of the screen under
the map. Check 90 (the layout at every interface size) before fixing, in case
it already covers the gap.

**96c - ports and the capital, by icon.** In the region editor: add, remove
and move the region's port, and move its capital (the settlement), each as
one easy-to-click icon rather than a form. **A region has at most one port**:
adding a second is refused, and a move replaces the old one. The existing
writers do the saving (`campfiles`, `campaint`, 19a's move); this piece is
the controls and the one-port rule.

**96d - the garrison in the settlement editor.** The settlement-editing
options gain the garrison: the units `descr_strat.txt` places in or with the
settlement, added, removed and changed there.

**96e - what another campaign editor does that this one does not.** The
user's word: "analyze this github and see what sort of features does he
have that we could port over. And once again give me a checklist."
[MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor](https://github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor),
cloned 2026-10-06 into `Reference/oogway-campaign-editor/` (untracked).
**Licence GPLv3**: port behaviour only, never code, as with Mylae's editor. **Lifted 2026-10-20** by the user ("we have permission to take the code directly too if needed so no need to make everything from scratch", then "same for mylaes tool"): code from either editor may be taken where it helps, credited in the module that takes it. The editor has since moved to [Pfadfinder-Adam/RTW-M2TW-Campaign-Editor](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor).
Most of its core is already here (cloning, unit and building editors,
painting, moving towns and ports, placing armies, terrain, events, victory
conditions, diplomacy, imports, 3x scaling). The eighteen things it has that
this toolkit lacks or half has went to the user as a checklist on 2026-10-06:
<https://claude.ai/artifact/WX5ZcGdjgdqinBbgjmwX1q>, answers in its database,
collection `answers` (`verdict`, `note`, `title`), read with `ArtifactData`.
The items: a no-code WHEN/IF/DO script builder (against the out-of-scope line
for a block script editor), ready-made add-ons, the game log explained, a deep
check that rehearses pending edits, a mod contents report, a drawn family
tree, custom portraits, a portrait library, a new region wizard, settlement
names by culture (check M2TW reads it), many towns at once with
auto-garrison, replacing a unit's model from another mod, voice preview and a
custom name call, an emblem set from one picture, a banner maker, recolouring
a faction's pictures, vanilla values with a reset on every rule, and a new
mod folder of hard links.

**The answers, read 2026-10-06: Port on 17 of the 18.** 96e is therefore
split by area, each built from the behaviour described in the checklist:

- **96e1 scripting**: the no-code WHEN / IF / DO script builder (dropdowns,
  searchable engine conditions and commands, player-tickable settings,
  worked examples, the script read back in plain words, shareable as a zip),
  and the ready-made add-ons on it (sack a settlement, avoid growth, player
  diplomacy). This **moves the out-of-scope line** for a block script editor
  (see *Explicitly out of scope*).
- **96e2 checking**: the game's `system.log.txt` explained (crash first,
  errors grouped, meaning and fix each); a deep check that rehearses every
  pending edit on an in-memory copy and writes nothing; a mod contents report
  by category.
- **96e3 characters**: a family tree drawn like the game's (couples side by
  side, children below, leader and heir marked, add any relation, off-map
  family); a custom portrait per character imported from PNG, JPG or TGA; a
  portrait library per culture with bulk add.
- **96e4 campaign map**: a new region wizard (every field of the record in one
  form, added to the owner's towns); many towns at once with auto-garrison to
  a cost limit, beside 96d.
- **96e5 units**: replace a unit's model from this or another mod (files
  carried, a texture for every owning faction, a warning when the mount type
  differs); voice preview by accent and a custom `.wav` name call.
- **96e6 art**: an emblem set from one picture (every size and button state);
  a banner maker (patterns, a symbol on a grid, M2TW's banner sheet recoloured
  per banner); recolouring a faction's pictures from donor to new colours,
  keeping light and shade, with before and after (shares its dye code with
  95).
- **96e7 rules and mods**: the vanilla value and a Reset beside every rule;
  a new mod folder whose unchanged files are hard links.

**Done so far, 2026-10-20** (major III, on the user's word "finish all of Factions, units and mod data phase"):
* **96a** `can_homeless` in the faction form: offered on an M2EX mod only, never to `papal_states` or `slave`
  (by slot or by `special_faction_type`), placed before `can_sap`; a line already there is reported and kept.
* **96e7** the vanilla value and a Reset beside every box of `descr_campaign_db.xml` and
  `descr_settlement_mechanics.xml` (`vanilla.py`, read out of the game's packs); "New mod from this one" on a
  Home card (`modfork.py`, from the editor's `newmod.py`): text files copied, the rest hard links, and a guard on
  `open()` that breaks a link under `mods/` before any in-place write the toolkit makes. There is no
  `descr_diplomacy.xml` editor yet, so diplomacy's vanilla values wait for one.
* **96e2** Health's Game log, Contents and Deep check tabs (`gamelog.py` from the editor's, `modreport.py`,
  `rehearse.py`). The deep check rehearses a change set's port, since this toolkit writes on Save and a change
  set is what it has pending; the copy is junctions and hard links in the temp folder, never written through.

* **96e5** units: a speaker button on each Sounds row hears a unit's name call in every accent and any
  accent's orders, straight from the game's SND.PACK archives (`voices.py`, from the editor's `sounds.py`); a
  `.wav` of your own becomes its name call (own line, split off a shared one, events.dat removed, undoable).
  Model swap is transfer's replace mode, which now warns when the mounts differ (`mount_kind`), works inside
  one mod, and skins reused entries for every owner.
* **96e6, first piece**: the whole emblem set from one picture on a faction's Art and banners tab
  (`emblem.py`, from the editor's): menu buttons 24/48 with their states measured from the mod's own, the
  faction-screen and panel symbols, the loading logos. **Left in 96e6**: the banner maker and recolouring a
  faction's pictures (both large; the editor's `banners_m2.py` and `recolour.py`), with round two's own logos
  and area recolour.
* **96e6 finished the same day**: battle banners painted new (`bannermaker.py`, from the editor's
  `banners_m2.py`: a white template from the median of the mod's banner sheets, the banner meshes' cloth, the
  pennants' other looks, fourteen patterns and a symbol; a shared sheet becomes the faction's own) and
  recolouring a faction's pictures (`artrecolour.py`, the editor's `recolour.py` core verbatim: cards, info
  pictures, battle textures by the modeldb, symbols; a shared texture becomes the faction's own copy, the
  space said first).
* **96e3 done the same day**: the Family tab draws and edits the tree (`stratfamily.py`, `family.js`), a
  portrait of one's own per character, and the culture's portrait library. Surnames (round two) stay in 96f.
* **96e1 done the same day**: a Scripts and add-ons screen (`scripts.py`, `scripts.js`) over the editor's
  `modbuilder.py`, `addons.py` and `enginedocs.py`, taken close to verbatim as `scriptbuilder.py`,
  `scriptaddons.py` and `scriptdocs.py` (`scriptcompat.py` answers what they asked of their own editor, and
  `scriptwords.py`, generated by `dev/checks/scriptwords_gen.py`, puts their labels in the catalogue). The
  builder: WHEN / IF (all, any, none) / DO / ELSE, once or for each town, army or faction, nine worked
  examples, read back in plain words, the Squirrel script shown, saved as an add-on of one's own. The
  add-ons: Sack and Raze Settlement, Avoid Growth, Recruitment Order, Player Diplomacy (scripts, M2EX), and
  Upkeep x N and One Recruitment Grid (file add-ons, no engine, `scriptfiles.py`). A script goes into the
  game's `script/modules`, outside the mod, so the Log's Undo learnt files outside `data/`
  (`outside_backed_up`, `outside_created`). **Known gap**: the plain-words read-back and the problems list
  are composed by the ported code in English; they stay English in German and Spanish until that code is
  moved to catalogue templates. Round two's campaign script by pieces and the blocks view are still 96f.
* **96f, first piece**: `mod_files.txt` from Health's Contents tab.
* **96f, a whole faction from another mod, 2026-10-21**: *Add a faction* has a **From** picker; another mod
  there brings one of its factions (`factionbring.py`, after the editor's own `factionbring.py`). It is made on a
  faction of this mod of the same culture (the frame, changeable), so the clone writes the new slot into every
  file the way this mod writes it; then the brought faction's own is laid over before anything is written: its
  colours, culture and religion where this mod has them, its symbol, loading logo and movies (the files brought),
  every text of its slot, its name lists and their `names.txt` texts, its campaign-map figures' textures, its art
  in place of the frame's, and its units. A unit this mod has line for line is shared; any other comes by Unit
  Transfer, owned by the new faction, once the slot is written (one Log entry each), and the frame's units leave
  the new faction's ownership unless asked for. Not brought, and said: its towns, armies and family, scripts and
  events naming it, traits only it has, its shields on the logo sheets. `tests/test_factionbring` (33). Both
  installed mods are at 31 of 31 slots, so the real-mod check is a plan (Divide and Conquer's Gondor into Heirs
  of Elendil: 63 texts, 588 names, 4 figures, 22 art items laid over, 31 units to transfer), not a write.

**Left in major III**: 96f, round two's major III items. Porting the editor's current files already brought its control blocks (ELSE, all / any / none, for each), its newer WHENs and the Recruitment Order, One Recruitment Grid and Upkeep x N add-ons; the Scratch-style blocks view and the campaign script by pieces are still to do. The thin mod needs every editor to copy a game file in
on its first write (the editor's `ModData.under`), so it is a piece of its own, not a flag on 96e7.

**Round two, 2026-10-20** (the user: "check the oogway editor ... for new commits since our old roadmap"): 513
commits, 0.31.0 to 0.35.1, read; 42 new features went to the user as a second checklist,
<https://claude.ai/artifact/GHEHzKgpRbEQyWyegJ44g6>, answers in its `answers` collection. **Answered the same day: Port on all 43**, and "just port everything and decide whats best to be
incorporated in the list you made". Two notes ask what would differ from ours (the 3D viewer's animations,
the new-unit wizard). Where the toolkit already has a version, only what it lacks is taken. Placed by area:

* **Into major II** (the campaign map, with 97, 96b-d and 96e4): the 3D map with the game's look, carrying
  things on it, its heights brush, the scripts layer, the minimap, merging regions and deleting many towns,
  dragging the map's edges, wasteland regions (M2EX), the coast tools, names under the mouse, a garrison for a
  town given to an empty faction, right click on a garrison's unit, Suggest for garrisons and armies.
* **Into major III as 96f** (after 96e1-7): a whole faction from another mod; a culture change with its
  preview; renaming a faction's slot everywhere; leader and heir titles; surnames from the faction's own list
  (with 96e3); the viewer's animations, riders, crews and armour button where Armory Studio lacks them; a card
  from the 3D model where the card maker lacks it; Transfer carrying voices, name call and a missing building;
  the new-unit wizard's steps the clone flow lacks; the editor's own look (the toolkit's pages); the game's
  menu screens page by page (this moves the out-of-scope line for `.sd` skinning); the art browser where
  Images lacks it; drawing pictures from the map; own logos and the area recolour (with 96e6); the script
  builder's control blocks, more WHENs, the campaign script by pieces and more add-ons (with 96e1);
  mod_files.txt and the new Health checks (with 96e2); the thin mod (with 96e7); keep-for-Apply where change
  sets lack it; hover cards; a religion and a building from nothing; more campaign rules; community
  translation files.

**Later**: settlement names by the owner's culture (under *Deferred to a
later version*; check first whether M2TW reads such a table at all).

# Phase 97 - the map viewer, 2D and 3D, scheduled 2026-10-06

Asked for by the user on 2026-10-06 with a reference picture (a Middle-earth
campaign map with faction names lettered large over their lands: ROHAN in
carved wood, GONDOR in white stone, MORDOR in black rock, each curved along
its territory and standing off the terrain with a shadow): "improve our 3d
viewer ... right now its only view only but i also want it to be editable with
selectable regions. Also if its possible can you make it so that we can have
such types of dynamic floating faction names as the default look of our map
viewer both 2d and 3d. Also add a button to turn on and off the icons. And in
the 3d viewer i want you to be able to also place in the agents and their 3d
models as well as the settlement 3d models in the respective tiles."

Where it starts: the 3D view is M18, a mode of the campaign map (`web/js/map3d.js`,
the `D` key), drawing the flat map's own composed colour map on one vertex
per tile; markers, labels and the tooltip stay on the flat map today. Labels
are 20c's (`web/js/maplabels.js`). Both WebGL traps apply (no
`requestAnimationFrame` in a hidden tab; `loseContext` is final).

**97a - select and edit in 3D.** A click in the 3D view picks the tile under
the cursor (a ray against the height field) and selects its region exactly as
a click on the flat map does, so every panel, the tooltip and the tools work
on it; hover highlights the region. The paint tools and the edits that take a
tile (moving a settlement, a port, an army) work in 3D through the same code
the flat map uses, never a second copy.

**97b - floating faction names, the default look.** Each faction's name
lettered over its territory: laid along the main axis of its largest
connected block of land (fitted to the shape, curving with it), sized to the
territory, coloured from the faction's colours, and drawn with depth and a
shadow. In 2D on the canvas; in 3D standing off the terrain, readable from the
camera's side. The name is the faction's display name from the mod's text.
Recomputed when ownership changes. **On by default** in both views, with a
toggle. Fallbacks: a faction too small or too scattered for a curve gets a
straight label; overlapping names give way by size.

**97c - an icons toggle.** One button that shows or hides every map icon
(settlements, armies, agents, resources, forts and the other marker kinds),
in 2D and 3D, remembered with the view.

**97d - agents and settlements as 3D models.** In the 3D view, each
character and agent drawn as its strat model (`descr_model_strat.txt` and the
`.cas` reader behind the Strat models tab, 95c) and each settlement as its
level's and culture's strat model (`settlemodel.py`), on its tile. Placing an
agent and moving one work in 3D (97a). Many models at once, so share one
loaded model per kind and drop detail with distance.

# Phase 99p - SimpleBake's two ideas for the packer, scheduled 2026-10-15

The rest of Phase 99 is done and archived (`ROADMAP_ARCHIVE.md`, under Phase 99).

**SimpleBake's two ideas for the packer, scheduled 2026-10-15, next.**
The user: "yes both". (1) A placer that fills holes and side pockets: a
full mask search over the sheet's occupancy (a coarse grid, then the exact
texels), not 99l's column profile, which loses every hole under a block.
(2) Free rotation as an opt-in in the UV step: any angle, said to cost a
resample (the bake is a 1:1 texel copy otherwise), quarter turns staying
the default. Measured on the four soldiers 99l was measured on, at 512.

**Done 2026-10-20**, on the user's word ("start working on the next phase").
* **Holes and side pockets.** `_Occupancy` in `armbake.py` keeps the sheet's
  taken texels; every place a block's mask meets none of them is found at
  once on a grid of a 256th of the sheet (the mask correlated with the grid
  through an FFT, a cell taken if any texel is), and the place picked is
  slid up and left texel by texel against the exact texels. 99l's column
  profile stays as the first three ways, since it costs no FFT; three new
  ones follow (top left by area, top left by height, most outline touching).
  A grid of a 128th lost to 99l on three of the four soldiers.
* **Measured at 512**, the scale each needed (99l, then 99p): the Dunedain
  knights 0.542 and 0.548, Mordor's bodyguard 0.690 and 0.709, the peasants
  0.844 and 0.843, the reference horse 0.968 and 1.000. The horse also fits
  512 at a 1% margin now.
* **Free rotation**, `rotate: "free"` and a checkbox in the export dialog: a
  block may take the turn that boxes its convex hull smallest (when that is
  over a degree from square and saves 2% or more), offered before its
  quarter turns; such a block is resampled, bicubic, its UVs turned with it.
  On the four soldiers it gained nothing (0.553, 0.699, 0.842, 1.000).
* **Found on the way**: a block's art could reach the sheet's right edge, so
  a vertex there had u = 1 (or 2), which the game reads on the next sheet;
  art now stops a texel short of the right and bottom edges.
* **Automatic is slower**: 39 s on the knights where 99l took 10 s (the
  scale is found with 99l's ways first, then searched above it with every
  way, a trial stopping at its first block that will not go).

# What else is open

Every rated item is built: the five- and four-star rows, and the three-star
rows, which became Phases 56-73 and 25-27. Their write-ups are in
`ROADMAP_ARCHIVE.md`, with how the ratings were reconciled with the 2026-09-05
triage board.

## Deferred to a later version, by the user

**How automatic "automatic kitbashing" is** (Phase 95). Asked on 2026-10-06
with three answers offered: (A) random within rules the user sets (a recipe
of allowed parts, colours and a count, rolled into variants), (B) matched to
an existing unit's look (find parts of the same kind across every installed
mod and build variants that still read as that unit), or (C) both, B's
match as the default recipe that A then loosens or tightens; and whether the
result is several models or one model with many variants per slot. The user:
"I think this should be something for later versions store this question for
once we finish setting up everything." So 95 builds the workbench by hand
and leaves the one-button kitbash for a later version; ask this question
again when it comes up.

**Settlement names by the owner's culture** (96e, marked Later by the user on
2026-10-06): a per-culture table of town names, shown when ownership changes.
Check first whether M2TW reads such a table or whether it is a Rome feature.

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
*New Map Editor* became Phase 87 (2026-09-25, done). The *Script editor*
became 96e1 (2026-10-06, the user ported the Oogway editor's WHEN / IF / DO
builder).

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
