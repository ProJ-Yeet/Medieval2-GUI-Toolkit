# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-12 · v2.2.3 is still the latest 2.x and beta 2026-09-11 the
latest beta · after 23b, winter and the tint, which closes Phase 23 ·
**nothing is released until the roadmap is finished**_

## Next up
**Phase 24, make and unmake** (`ROADMAP.md`), and it is the **last session of
the roadmap**; B2-B4 are not counted. Two operations on a thing that has a
create or a delete but not both:

- **G1, delete a region.** We create regions and cannot delete one - verified,
  nothing in `campaint.py` or `campmap.py` deletes a record or reallocates its
  tiles. 16e's wizard is the other half and its rules apply unchanged, including
  the refusal to leave any region with no tiles and the warning that a change
  here renumbers every region the engine scans after it. **Improve on the
  arbiter rather than copying it**: Geomod's own manual admits "resources, forts
  and characters will remain", which is a dangling-reference bug it ships. 16f
  has every rule needed to find them and Phase 22 made every one of them
  movable, so ours names what is about to be orphaned and offers to move it -
  `mapsnap.nearest` is the search and it takes the caller's own predicate.
- **M15, create a campaign.** See the roadmap.

The 23a and 23b write-ups are in `ROADMAP_ARCHIVE.md`. **When 24 closes, the
whole backlog goes out as one cut** - see below, and `HANDOFF.md`.

**Do not release anything at the end of a session.** On 2026-09-11 the user
said: "we wont publish until we finish all the sessions of our roadmap now".
Commit, update these files, and stop. When the last session closes, the whole
backlog goes out as ONE cut, and `HANDOFF.md` rule 1 applies to that cut
unchanged. The cut-as-it-lands rule of 2026-09-09 is suspended until then.
**No Discord post per session either**: the user wants one all-in-one post
with that cut, covering everything since v2.2.3 / beta 2026-09-11.

## WHERE THINGS ARE - the tree moved on 2026-09-06
Only the two `.bat` files and `README.md` are at the top of the repository.
**Everything else is under `main/`, and `main/` is the code root** - what
`config.PROJECT_ROOT` resolves to, what a test's `parents[1]` is, and what every
path in this file and in the source is relative to. `main/dev/` never ships.

## THE TWO RELEASE LINES - for the one cut at the end
Two lines off this one `master`, chosen by whether a change touches the campaign
map. **Not campaign-map** -> a **2.x subrelease with the map hidden**, uploaded
`--latest` (latest **v2.2.3**, 2026-09-09). **Campaign-map** -> the **beta line**,
uploaded as a **pre-release** (latest **beta 2026-09-11**). A **subrelease means
both**: one job, both zips, same tree. The end-of-roadmap cut will be both.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`, which `menuModes()` and `modeOffered()` are the only readers
of. It is a **release-time edit, not a state of `master`** - set it, bump the 2.x
number, build, upload, then put it straight back off in the next commit.
`master` carries the map ON, and `__version__` says `beta-2026-09-11` because
the beta was the last thing cut.

**21 belongs to BOTH lines.** Raw text is a menu mode of its own and the faction
audit also draws in the Factions mode, so both are in the 2.x build with the map
hidden; the audit's two campaign-row buttons appear only on the map screen.
**22a, 22b, 22c, 23a and 23b are map work** and belong to the beta line only.

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**Written and held: v2.2.4 + beta 2026-09-11b.** The notes are in
`docs/releases/` (`RELEASE_2_2_4.md`, `RELEASE_BETA_2026_09_11B.md`) and the
two fixes are committed. **Fold them into the end-of-roadmap cut** - and B1 has
to be added to both notes, since the beta note's "Not fixed" section describes
exactly what B1 fixed. 20b, 20c, B1, 21, the map hover fix, 22a, 22b and 22c are
not in any note yet either, and neither are 23a and 23b - and 22b's drag fix is
worth a line of its own, since 17d's drag never dropped in any cut.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 23b - Winter, and the tint | **done** | Closed 2026-09-12, committed, **not released**. Closes T12 and the winter half of T1, and with it Phase 23. The season switch on the ground types row, one picture kept per season, and the validator judging **both** seasons (`mapterrain.season_gaps`) because a missing winter texture is missing whichever season is drawn. T12's tint is the canvas `color` blend, which is his grayscale-then-HSB chain in one step; the colouring moved out of the layer composite to `cmapThemeDraw` so it can blend against the terrain. Border position (edge/inside) and scope (groups/every province), on the screen and in the export both. New: `Colouring.payload`'s `bands`, `mapquery._every_region`, `BORDER_POSITIONS`; `cmapThemeDraw`, `cmapTerrainSeason`, `cqFill`, `cqGroups`, `cqBorders`, `cqDraw`. `tests/test_mapquery.py` section 3b (10, node against Python). |
| 23a - The texture composite | **done** | Closed 2026-09-12, committed, **not released**. Closes D7 and T1. The map drawn with the mod's own aerial-map textures, TWMapReader's rules taken as they stand: pink for a texture that cannot be found, the `default` block inherited, wilderness drawn as fertility_low, and the two winter fallbacks. New: `unittransfer/mapterrain.py` (`parse`, `Vocabulary`, `plan`, `composite`, `check_textures`, `signature`, `view`, `_index`), `GET /api/map/terrain[&format=png]`, `mapcheck`'s `terrain.texture` rule, and a Terrain textures mode on the ground types row (`cmapTerrainOn` / `cmapTerrainDraw`). `tests/test_mapterrain.py` (63). |
| 22c - A campaign's own map | **done** | Closed 2026-09-11, committed, **not released**. The follow-up 22b left: the map screen, ✓ Check and its fixes read a campaign's own map files. New: `Registry.map_for`, `campmap.shipped` / `layer_map` / `rel_of` / `base_readers` / `home_view`, `mapcheck.Check.rel`, `campaint.paints_for`; `cmapRefetchMap` / `cmapHomeNote` in `campmap.js`. `tests/test_campaignmap.py` (30). |
| 22b - Resources, and the snap | done | Closed 2026-09-11, committed, **not released**. Closes D9, D10, G5 and Phase 22. New: `unittransfer/mapsnap.py`, `campmap.campaign_map` / `map_of`, `mapcheck.position_faults` / `duplicate_message`; `stratobj` takes `resource` (`Layout`, `resource_home`, `Census`, `Vocabulary.snap`); `stratchar._shore`, `campaint._marker_near`; `cmapLocate` in `campmap.js`, and 17d's drag counts the pointer's travel. `tests/test_stratres.py` (67). |
| 22a - Forts and watchtowers | done | Closed 2026-09-11, committed, **not released**. First half of D9 (and G5). New: `unittransfer/stratobj.py` (`plan`, `apply`, `view`, `Vocabulary`, `render_line`, `new_section`), `web/js/campforts.js` (the 🏰 Forts panel), `GET /api/map/objects`, `POST /api/map/object_plan\|_apply`. 17d's drag takes forts and watchtowers (`CMK_DRAGGABLE`). `tests/test_stratobj.py` (65). |
| 21 - Two screens over data we hold | done | Closed 2026-09-11, committed, **not released**. Closes D6, D11 (= M14) and the Now set. New: `unittransfer/factionaudit.py` (`Census`, `evaluate`, `audit`, `repair_plan`), `unittransfer/rawtext.py` (`files`, `read`, `splice`, `plan`, `apply`), `web/js/facaudit.js`, `web/js/rawtext.js`, the `rawtext` mode, `GET /api/factions/audit`, `POST /api/factions/repair_plan\|repair_apply`, `GET /api/raw/files\|file`, `POST /api/raw/plan\|apply`. `factionclone.clone_file` and `ClonePlan.action` (refactor, clone suites unchanged). `tests/test_factionaudit.py` (48), `tests/test_rawtext.py` (57). |
| 24 - the last of the Next set (3.2.0) | **scoped** | One session: delete a region and create a campaign. The last of the roadmap. |
| B2-B4 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export; `Rename slot` on a packed mod. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-21 | done | 16-20a published on the beta line; 20b onward committed and uncut. The 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |

## In-progress detail
**Clean.** Nothing is mid-flight. There are 100 suites. After 23b the map set
was re-run - `test_mapquery` (109), `test_mapcheck` (86), `test_mapterrain`
(63), `test_maplayers`, `test_web_modules`, `test_campmap`, `test_campaignmap`,
`test_campedit`, `test_campaint`, `test_campview`, `test_stratobj`,
`test_mapgo` - and everything passes except the DaC four below, each on its
documented number.

**The one-second bar in `test_mapcheck` has less headroom than it did.** 23a's
rule put it at about 630 ms on DaC and 23b's second season at about 740. It is a
load-sensitive bar and it has flaked once here under contention with another
suite; re-run it alone and idle before believing a failure.

**Four suites fail the same way on a clean `master`** - hard-coded Divide and
Conquer numbers (77 port pixels, 13,153 newlines, 305 characters, 73,904 sea
tiles) against an installed DaC that is a different build: `test_campmap`,
`test_campstrat`, `test_campview`, `test_stratchar`. Stash and re-run before
believing one of them.

**Three suites need node**: `tests/test_maplayers.py` (20a),
`tests/test_mapgo.py` (20b) and `tests/test_maplabels.py` (20c). Without node on
PATH each prints a skip line and its Python half still runs.

**Two suites bind a socket and can collide inside a back-to-back run**
(`test_buildings_http`, `test_viewer3d_http`, `WinError 10013`), and **two
one-second timing bars are load-sensitive** (`test_mapcheck`'s rule-set bar,
`test_mapquery`'s warm fact-table bar). Re-run any of the four alone and idle
before believing it.

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.
And **never `git stash` while a suite is running in the background** - it pulls
the edits out from under it (21 did it once; see the archive).

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- `web/js/mappin.js` - **before adding a coordinate field anywhere** (20c).
  `cpinButton(what, fn, args)` is the whole of it; 22a's and 22b's forms and
  their three Place buttons use it.
- `campaint.map_campaigns` - **before writing anything to the base map** (B1).
  A write to `world/maps/base` reaches only the campaigns that do not ship
  their own copy.
- `unittransfer/factionaudit.py` - **before adding any check about a faction.**
  `Census` already counts every slot in every file; gap or note is measured on
  the installed mods, never copied from a reference.
- `Registry.map_for` and `campmap.layer_map` - **before a module draws a
  layer.** The engine reads a campaign's own copy of a map file where it ships
  one, and so does the screen; a texture built from the base map's ground layer
  is not Fellowship's.
- `unittransfer/mapterrain.py` - **before anything needs a layer's colours as
  one byte a tile.** `Vocabulary.texture` is the one place the engine's four
  texture rules are applied; `_index` is the exact colour-to-index pass, in
  Pillow's C and 16x quicker than a dictionary pass, with the slow one kept
  beside it as the reference.
- `Colouring.payload`'s `bands` - **before working out anything per group.**
  Which group each province is in, `-1` for none, absent for anything that is
  not a province. The colour cannot answer it and reading it off the colour was
  a real bug: a presence map's "none" group is painted the same grey a province
  in no group is.
- `tests/test_mapquery.py` section 3b - **the pattern for anything the browser
  draws and Python exports.** Both passes, over one map, in node. It found two
  faults that had been in the tree since 16g, neither of which reading the code
  had found.
- `unittransfer/mapsnap.py` - before writing any rule about where something may
  stand. The search is there; hand it the rule and put `near` on the finding.
- `unittransfer/stratobj.py` - one writer for every one-line thing on the map.
- `unittransfer/rawtext.py` - `rtOpen(rel, line)` is how any screen offers
  "open this file as text"; a parser that meets a line it does not model points
  there rather than growing a special case.

## Upstream
Reference tool reviewed SHA **2740b0b**. `sync` was run on 2026-09-12 at the
start of 23a and again at the start of 23b, and was up to date both times -
nothing new since 2026-09-09. `docs/upstream/PORT_MANIFEST.json` is authoritative: 310
files triaged, none untriaged; `src/pages/TextEditor.jsx` notes it done in 21.
`REFERENCE_GAPS.md` marks D6, D11 and M14 done and G2 half done; **D7, T1 and
T12 are Phase 23's and are now done.** 24 takes G1 and M15; run `sync` first.

## Decisions
- 2026-09-12: **A tint is the canvas `color` blend, and nothing else.**
  TWMapReader greyscales a region's pixels and then applies an HSB filter set to
  the tint's hue and saturation; the blend takes the source's hue and saturation
  and the backdrop's luminosity, which is the same operation in one step and in
  hardware. His brightness stretch and its two cutoffs do not port, and the
  reason is worth keeping: they exist to stop a filter that *replaces* the
  brightness from crushing the relief, and the blend never touches it. Reading
  what a reference does is not the same as copying how it does it.
- 2026-09-12: **Anything that blends against the map is drawn on the screen, not
  into the composite.** The layer composite is one pixel a tile and 23a's
  terrain is four, so a colouring blended into the composite would be a tint of
  the wrong picture. The fill and the frontiers went out as two canvases at the
  same time, because a border colour has almost no saturation and a `color`
  blend of it is a grey wash rather than a line.
- 2026-09-12: **A colour cannot say which group a province is in, so the server
  says.** A presence map has a real group labelled "none" painted `NO_GROUP`,
  which is the same grey a province in *no* group is painted. Inferring the
  group from the fill put a frontier round every ungrouped province. The payload
  carries `bands` now, and the browser infers nothing.
- 2026-09-12: **Two implementations of one picture get one test that runs both.**
  The panel has said since 16g that what is on screen and what an export writes
  are the same picture, and for borders it was not true: the browser grouped by
  each province's own colour and the export by the group's. Running `cqGroups`
  and `cqBorders` in node against `_draw_borders` over one map found that and a
  second fault in an afternoon; neither had been found by reading the code in
  three phases of looking at it.
- 2026-09-12: **A picture of the terrain says what it could not draw.**
  TWMapReader draws a texture it cannot find pink and reports it, and 23a took
  that rule and widened it by one case: a tile can have no texture because the
  file names one that is missing *or* because nothing names one at all, and both
  are pink and both are counted. The second found the fifteen DaC tiles whose
  height says land and whose ground type says sea, which 16a had measured and
  nothing had ever reported. A picture that is mostly right is the hardest kind
  to check, so it has to say where it is not.
- 2026-09-12: **The terrain is a reading of two layers, so it lives on one of
  their rows.** 20a's ruling, applied to something four times the resolution of
  the composite: the stack stays the ten files the map is made of. What is new
  is that it cannot go *into* the composite - that is one pixel a tile - so it
  is blitted under it, and one function answers "is the backdrop being drawn"
  for the blit, the composite's opaque background and the composite's cache key.
  Two of those three disagreeing is a black map.
- 2026-09-12: **A composite of the map on the screen is keyed on the pixels, not
  on the files.** There is a paint tool on this screen; a stroke changes the map
  object and nothing about the file until somebody saves. Hashing the two layers
  is four milliseconds against a second to rebuild, and it is the difference
  between a picture of what will load and a picture of what did.
- 2026-09-12: **An exact colour-to-index pass belongs in Pillow's C, and it
  fits.** `Image.quantize` with a fixed palette is the obvious C route and 16a
  measured what it costs: 1,320 tiles on the wrong region. Ranking each band
  among the values that occur, packing red and green and ranking the pairs that
  really occur, puts three ranks in a byte exactly - 160 ms of Python becomes
  10 ms, and the suite checks the two byte for byte on every installed map.
- 2026-09-11: **The screen draws the map the campaign reads, and the brush
  stays where it paints.** A campaign that ships its own map files is drawn and
  judged on them, and the brush, which only ever paints world/maps/base, is
  refused there with the campaigns that do show it. Painting a map nobody can
  see would be the one stroke a paint tool must never make.
- 2026-09-11: **A check of an interaction drives the interaction.** 22a's
  browser check called the drop and passed; 17d's drag had never dropped,
  because the pointer's travel was counted only for a pan. 22b dragged with the
  pointer and it failed at once. Calling the function a gesture ends in proves
  the function, not the gesture.
- 2026-09-11: **A refusal names the nearest tile that would do, and the rule
  it came from stays the only copy.** D10 is one search over four predicates -
  the marker rules, the shore rule, the object rules and the sea rule - each
  still living where it did. "No" with no way forward leaves somebody clicking
  round the coast one tile at a time.
- 2026-09-11: **Where a new record goes is derived from the map and the file,
  never typed.** Demir's dialog has a region box; here a new fort is filed under
  the province under its tile, because 393 of DaC's 400 are, and a new section
  goes where the file says sections go - under Third Age Reforged's own
  `start of regions section` banner, in front of DaC's scripts banner. The
  exceptions stay visible, counted on the file being edited, with one button to
  refile. A box somebody has to fill in correctly is a box that will be filled
  in wrong.
- 2026-09-11: **The map screen never reads a canvas back.** A user's browser
  said "no region" over most of Third Age Reforged and read dense forest,
  0,64,0, as 0,65,1: canvas anti-fingerprinting (Brave's shields, Firefox's
  resist-fingerprinting, privacy extensions) noises every getImageData, and our
  in-app browser does not, which is why no test here saw it. Layers now arrive
  as raw bytes (`layer?format=rgb`), `cmapRawOf` is the one read, and canvases
  are only written. The node harness's canvas throws on a read.
- 2026-09-11: **A raw save refuses only on the bytes, never on the parser.** It
  refuses a stale signature, a character the file's encoding cannot hold, and a
  file that does not survive a read and a write unchanged; what the toolkit's
  own reader objects to is a warning. An escape hatch that closes when the
  parser disagrees is not one.
- 2026-09-11: **Gap or note is measured per file on the installed mods.** A gap
  is a record every real faction has; a note is one working factions go without,
  shown and never counted. It moved three of Demir's calls and dropped one check
  outright, and "copy what is missing" copies gaps only.
- 2026-09-11: **A label with no room is left off and counted, never drawn over
  another.** TWMapReader draws it anyway; two names on top of each other are
  neither readable. It is honest because it is measured: zooming in never names
  fewer, and from 8 px a tile every settlement on all three maps is named.
- 2026-09-11: **Nothing is released until the roadmap is finished.** The
  user's instruction, and it suspends the cut-as-it-lands rule of 2026-09-09:
  commit each session and stop, then one cut of the whole backlog at the end.
- 2026-09-11: **The engine takes each map file separately, so the unit a map
  write reaches is the campaign.** Vanilla's `norman_prologue` ships its own
  `map_regions.tga` and reads the base `descr_regions.txt`. Anything written to
  `world/maps/base` asks `campaint.map_campaigns` which campaigns see it and
  which copy of each file each one reads. B1's crash was the base record
  written and a campaign's own copy not.
