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
**Phases 18 to 27 are not here** - they are unbuilt, and they live in the
Backlog below with their own index.

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

Nothing below Phase 16 gates anything still to be built - the dependency rules
that mattered while V2 was being built are recorded in the archive. What *does*
gate later work is stated where it applies: 17d's markers layer is what 18b (done),
20c and part of 22 build on, and Phase 22 gates the orphan-handling half of 24.

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
mask pass is measured that way; 20c's label placement is the next thing that
should be.


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
| later | 25-27, and the Later table | Not scheduled. |

### The whole plan on one screen

| Phase | Sessions | Closes | Size |
|---|---|---|---|
| 20c - Labels, and picking a tile | 1 | T4 M8 | 1M 1S |
| 21 - Two screens over data we hold | 1 | D6 D11 | 1M 1S |
| 22a-22b - Placing things on the map | 2 | D9 D10 | 1L 1M |
| 23a-23b - A map that looks like the map | 2 | D7 T1 T12 | 2L 1M |
| 24 - Make and unmake | 1 | G1 M15 | 2M |

Eight sessions left, plus **B1 in front of 20c** - see "Reported from the
beta" below, which is four items that came from users rather than from the
audit. Phase 17 (2026-09-06), all of Phase 18 (2026-09-07), all of
Phase 19 (2026-09-09), 20a (2026-09-10) and 20b (2026-09-11) are done and their
write-ups are in `ROADMAP_ARCHIVE.md`; nothing in the Later table is counted.

---
# Reported from the beta - not phased, and B1 jumps the queue

Four items off beta users between 2026-09-09 and 2026-09-11. They are not from
the reference audit, so they have no `D`/`T`/`M` id; they are numbered `B` and
they are **not** scheduled into the phases above. **B1 is a crash and should go
in front of 20c.**

| id | Item | Size | Note |
|---|---|---|---|
| B1 | A new province needs a settlement in `descr_strat.txt` | M | **A crash, reported with a log.** In front of everything else here. |
| B2 | Delete a settlement, and move one between mods | M | Half of what was asked for already exists - see below before building anything. |
| B3 | Insert and export one file at a time, the way Mylae's tool does | M | The user's own words: "that isnt really needed tbh". Lowest of the four. |
| B4 | `Rename slot` is refused on a mod that keeps `descr_sm_factions.txt` packed | S | Same root as the whole Factions screen refusing. |

## B1 - a new province needs a settlement in `descr_strat.txt`

`campaint.apply_paint` writes the painted layers, `descr_regions.txt`, the two
shown names when the wizard's boxes were filled in, and deletes `map.rwm`. That
is all it writes. So a province created with the wizard has a record and pixels
and **no settlement block**, which means no faction starts there, the engine
cannot give the region an owner, and the campaign crashes at the end of a turn.

A beta user's `system.log` has the whole chain, in this order: `Couldn't find
region name … in stringtable` twice, then `cannot find this pixel colour(8,8,8)
in the region_db`, then `we don't appear to have a settlement position in
region(26)` and `invalid tile(0,0) … PLACEMENT_IN_SEA`, then `ASSERT FAILED:
strategy_map.cpp(7234): settlement_owner`, then `AI_REGION_GROUP_ANALYSER: land
region '' (id 26) has no owning faction - skipping. Check your descr_strat.txt`.
The log then stops inside `between turns`.

Three smaller holes travel with it and should close in the same session:

* **the creator faction is not checked.** `campaint.check_new_region` tests it
  for being non-empty and nothing else, and `web/js/campaint.js` offers it as a
  free-text box whose placeholder is `slave` - which is not a legal value for
  that field. The faction list is already loaded for other screens.
* **`descr_sounds_music_types.txt` never gets the region.** The engine says so:
  `music_type not found for regions: <name>`. This is audit item **G2**, sized S
  and parked under Later; it belongs here instead.
* **the two shown names are a warning, not a requirement.** The engine logs a
  fatal assert for each missing one. `_plan_region_names` already writes them
  when the boxes are filled in.

Nothing has to be invented: `stratedit.plan_settlement` already writes settlement
blocks and moves them between faction blocks, and `mapquery` already reads the
music types file. **Nothing in Phases 20-24 covers this** - Phase 24 is *delete*
a region, which is the opposite end of the same gap.

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
* **create one** - which is B1 from the other direction, and the two should
  share a writer rather than grow two.
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

## B4 - `Rename slot` on a mod with its factions packed

`renames._names` reads the slot list from `descr_sm_factions.txt` on disk and
returns an empty list when the file is not there, so `_validate` refuses every
faction with "there is no faction slot called X in <mod>". The stock game keeps
that file inside a `.pack`, and so does any mod that has not unpacked it -
verified on this machine: vanilla has no loose copy, DaC and Third Age Reforged
do. `factions.overview` refuses the whole screen the same way and for the same
reason, so the fix belongs in one place rather than two, and the honest message
names the pack rather than claiming the faction does not exist.

---
# 3.1.0 - the Now set (Phases 18-21)

Twenty items. Fifteen are S, five are M and none is L, which is what makes
this a release rather than a slog: it is almost entirely files that are already read
and screens that already exist. The common shape is **we know a file well enough
to validate it and not well enough to edit it**, and that asymmetry is what
3.1.0 removes.

**Phases 18 and 19 are done** - 18a and 18b on 2026-09-07, 19a and 19b on
2026-09-09 - **and so are 20a and 20b**, on 2026-09-10 and 2026-09-11. Phase
18's six files are the five nothing wrote and the one the building side could
only refuse against; Phase 19 is the four names nothing could follow; 20a is the
three layers the map screen could draw and not read; 20b is the three ways of
getting to the thing you want, one of which turned out to be three whole
campaigns nothing had ever offered. All six write-ups are in
`ROADMAP_ARCHIVE.md`. **What is left of the Now set is 20c and Phase 21.**

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

## Phase 20 - The map screen's second pass

Eight items across three sessions, all of them on a screen that already exists.
Nothing here needs a new parser. **20a is done** (2026-09-10) and **so is 20b**
(2026-09-11); both write-ups are in `ROADMAP_ARCHIVE.md`, and **20c is what is
left.**

Five things the two finished sessions leave for 20c:

- **The layer stack is the ten files and stays that way.** A reading of a layer
  - the river overlay, the heights as transparency - lives on that layer's row.
  The ten number keys count the stack, and an eleventh entry would break the
  one-key-per-layer rule T11 is built on.
- **`cmapMask` is the one pixel pass**, and everything that changes what a layer
  looks like without changing where it is drawn belongs in it. It is keyed by
  `cmapModeKey`, which is also what the composite's cache key reads.
- **`tests/test_maplayers.py` and `tests/test_mapgo.py` run the browser's own
  functions in node**, with a stubbed canvas and no DOM library. 20c's label
  placement is the next thing with real arithmetic in the browser, and either
  suite is where it can be measured - 20b's harness loads three files into one
  context, which is the shape a label pass will need.
- **`cmapGoTile(tile, zoom, region)` is the one way of arriving somewhere**, and
  M8's pick mode is the reverse of it. Three panels call it; a fourth copy of
  those six lines is the thing not to write.
- **The screen reads one campaign, and `state.cmap.campaign` is which** (20b).
  `cmapCampQ()` is the only place a request appends it and `cmapSetCampaign` is
  the only place it changes; a panel added later gets both for free. Anything
  20c or Phase 22 puts on the map that comes out of `descr_strat.txt` belongs to
  a campaign, not to the mod.

### 20c - Labels, and picking a tile, one session

**Closes T4, M8.** Both build on 17d's markers layer (`web/js/campmark.js`),
which shipped 2026-09-06 - so both have what they need.

- **T4 - settlement names on the map, placed to avoid overlap.** Names beside
  the markers, shifted around each other so they do not collide, with font and
  marker size constant across zooms. 17d is the markers and this is the labels,
  which is the harder half - kept separate deliberately so 17d does not wait on
  it. TWMapReader's own verdict on its placement is "fairly limited but better
  than none at all", which is the bar: better than none, and honest about it.
  20b put the words the player reads into the manifest (`region_view`'s `shown`
  and `shown_settlement`), so the label to draw is already in the browser.
- **M8 - pick an X,Y off the map into any form field.** A pin button beside a
  coordinate pair that puts the map into pick mode and writes the clicked tile
  back. Every coordinate in `stratedit`, `stratchar`, 18b's disasters and 22's
  object dialogs is typed by hand today. **One shared control makes all of them
  clickable**, which is why a 49-line component is worth a named item.

---

## Phase 21 - Two screens over data we already hold

**Closes D6, D11.** One session. Neither reads anything new.

- **D6 - the faction dependency audit.** One screen answering "is this faction
  complete?" across every file that should mention it, with a repair offered per
  gap. We have every piece and not the screen: `factionclone.py` knows the twelve
  files, `mapcheck` and `factions.py` both report per-file faults, and Home
  reports per-mod readiness. Build it on 17f's combined faction screen, which is
  where somebody is already standing when they ask the question.
- **D11 - a raw text editor for the campaign files.** Pick any file the toolkit
  knows about and edit its text directly, with our own backup, log entry and
  undo around it. Our Code View is per record and deliberately so; a whole-file
  editor is a different thing and it is **the escape hatch for the case every
  editor here eventually meets - the mod does something the parser does not
  model.** Mylae ships the same feature as a page (`TextEditor.jsx`, audit item
  M14, the same item).

The one rule this session must not break: a raw save still goes through the
backup set and the log, so the Log's Undo reverses it like every other write. An
editor that writes straight to disk is the one thing in this toolkit that could
lose somebody's mod.

---

# 3.2.0 - the Next set (Phases 22-24)

Seven items, three of them L. This is where the campaign map stops being a data
layer you can edit and starts being a map you work on.

---

## Phase 22 - Placing things on the map

**Closes D9, D10.** Two sessions. **The largest single hole in the campaign
editor**, and the one gap all three map tools fill and we do not.

16b reads forts, watchtowers and resources - **105 forts, 295 watchtowers and
1,131 resources on DaC**, each carrying its line span - and nothing writes any
of them. `stratchar.py`'s `UNTOUCHED` tuple names all three as things a
character save may not touch, which is the guard working correctly around a
feature that does not exist.

### 22a - Forts and watchtowers

Click the map to add one, drag to move one, delete one. Both are one-line
records inside a `region` section, both in two forms (16b found DaC's 105 forts
are all the long form and neither vanilla campaign contains a single one, so the
short form is exercised only by the synthetic half of the suite - that gap
closes here). The writer follows 16h and 16i exactly: edit, add, delete and move
are the same request with a different `action`, because in the file they are the
same edit.

### 22b - Resources, and the snap

Resources are the same operation over 1,131 records, plus two rules that already
exist and must be reused rather than rewritten: a resource is allowed to stand
**on** a settlement or port pixel, because the index does not answer for a
marker tile and the region that owns the marker answers instead (16g found
that); and a duplicate resource, or one off the map or in the sea, is already a
`mapcheck` rule with 63 duplicates found on DaC.

**D10 - snap to a legal position** lands here. We have the predicate and not the
search: `mapcheck.marker_faults` is the single copy of the four marker rules and
`campaint` already calls it for the new-province wizard. Turning "no" into "no,
but here" is a spiral search over that predicate, and it serves 22a, 22b, 18b's
disasters and 17d's drag-to-move at once.

Exit: every object type places, moves and deletes; the file is byte-exact
outside the lines the plan named; Geomod's "Localize" gets its equivalent,
because `mapcheck` and `mapquery` both centre the map on a tile already and
neither tells you where your eye should land.

---

## Phase 23 - A map that looks like the campaign map

**Closes D7, T1, T12.** Two sessions. **The most expensive work in this
document and the most visible.**

D7 and T1 are the same feature with two implementations to compare, and
TWMapReader's is the better specification of the two.

### 23a - The texture composite

Draw the map with the game's own aerial-map ground textures, one per (climate,
ground type) pair, read from `data/terrain/aerial_map/ground_types`. `mapvocab`
already cites `descr_aerial_map_ground_types.txt` and `cleaner.py` already walks
the `aerial_map` folder, so the vocabulary is known; what is new is the
compositing and the cost of it.

**Take TWMapReader's missing-texture rule exactly.** A texture it cannot find is
reported in the Errors tab and drawn **pink**, not skipped silently - which is
our own "a rule with no evidence reports nothing" applied to a picture, arrived
at independently by somebody else. That is the strongest argument in the audit
for taking his version over Demir's.

The performance rule from 16c holds: the composite is built once and pan and
zoom never rebuild it. If that cannot be met the feature is wrong, not the rule.

### 23b - Winter, and the tint

The winter texture set doubles 23a for free. **T12 - the HSB tint** lands here
and lands here for a reason: 16g's colourings *replace* the region layer, and on
a textured backdrop replacing it is exactly wrong. A tint colours a region
without painting over it, so the ground underneath still reads. Also from T12: a
border render type with an "inside" option, and borders on all regions rather
than only the highlighted ones. 16g's rule that a border compares the *group*
each region is in, not its colour, stays - it is what gives clean frontiers and
it is right.

---

## Phase 24 - Make and unmake

**Closes G1, M15.** One session. Two operations on a thing that already has a
create or a delete but not both.

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

# Later - classified, not scheduled

Thirteen items the user marked Later on 2026-09-05. They are not phases and
nothing depends on them. Two are flagged above as cheap to take early if the
user changes their mind; the rest are here as written.

| id | Item | Size | Note |
|---|---|---|---|
| D1 | Change a region's colour | M | Same cluster as 19b. Costly part is real: a recolour can renumber every region after it. |
| D12 | Export the project as a zip, and load one back | M | `pack.py` already does this shape for units, import and conflict report included. |
| D13 | Generate a horde start for a new faction | M | 16j-2 creates the faction with no settlement and no character, which is the shape vanilla's Mongols already are. This is the other half. |
| G2 | Region music | S | `mapquery` reads `descr_sounds_music_types.txt` already; the region form does not offer it. **Moved into B1** - the engine reports a region with no music type, so it is part of creating one properly rather than a nicety. |
| G4 | Legion label, with its name dialog | S | **Nearly free during 19a.** Flagged there. |
| M7 | Import a campaign from another mod | L | Unit Transfer's problem at campaign scale; `transfer.py` is the model. |
| M12 | Bulk faction duplicate, and faction zip export | M | A loop over `factionclone.py` with one plan, plus `pack.py`. |
| M16 | Animation editor and asset converter | L | Was excluded because we could not read `.mesh` or `.cas`. **15a and 16k both now can, so the reason has changed.** |
| M17 | Export and validation dashboard | M | We have more validators than the reference and no single door to them. |
| T3 | An FE zoom, for authoring `map_FE.tga` | M | Pairs with 16g's per-faction TGA export. |
| T6 | Export every tile as text | M | We export pictures and never numbers; `mapquery`'s fact table is the join it needs. |
| T7 | Spawn export, including from the campaign script | M | A read-only scan for spawn coordinates is far smaller than the script parser 19b has to refuse. |
| T10 | Copy the view, or what is under the cursor | S | Take the shift-X detail: `x 23, y 284`, the form `descr_strat.txt` wants. |

---

# Not scheduled, and previously mis-numbered

These three were called `V3.1`, `V3.2` and `V3.3`. They are phases now, with no
version attached, and none of them is in the Now or Next set.

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
