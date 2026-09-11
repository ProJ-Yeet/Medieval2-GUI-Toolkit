# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-11 · v2.2.3 is still the latest 2.x and beta 2026-09-11 the
latest beta · after 20c, settlement names on the map and the pin, which closes
Phase 20 · **nothing is released until the roadmap is finished**_

## Next up
**Phase 21, two screens over data we already hold** (`ROADMAP.md`): D6, the
faction dependency audit, built on 17f's combined faction screen; and D11, a
raw text editor for the campaign files, whose save goes through the backup set
and the log like every other write. B1 and 20c both closed on 2026-09-11 and
their write-ups are in `ROADMAP_ARCHIVE.md`. After 21 come 22a-22b, 23a-23b
and 24, which makes **six sessions left in all**, B2-B4 not counted. (The
roadmap said eight before 20c, which was one too many; its table never added
up to it.)

**Do not release anything at the end of a session.** On 2026-09-11 the user
said: "we wont publish until we finish all the sessions of our roadmap now".
Commit, update these files, and stop. When the last session closes, the whole
backlog goes out as ONE cut, and `HANDOFF.md` rule 1 applies to that cut
unchanged. The cut-as-it-lands rule of 2026-09-09 is suspended until then.

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

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**Written and held: v2.2.4 + beta 2026-09-11b.** The notes are in
`docs/releases/` (`RELEASE_2_2_4.md`, `RELEASE_BETA_2026_09_11B.md`) and the
two fixes are committed (`descr_regions.txt` read without an indent, and a TGA
RLE decoder for the layers Pillow refuses). Nothing was tagged or uploaded.
**Fold them into the end-of-roadmap cut** rather than cutting them on their
own - and B1 has to be added to both notes, since the beta note's "Not fixed"
section describes exactly what B1 fixed.

## Phase status
| Phase | Status | Note |
|---|---|---|
| B1 - A new province needs a settlement | **done** | Closed 2026-09-11, committed, **not released**. New: `campaint.map_campaigns`, `region_vocab`, `wizard_vocab`, `neighbours`, `creator_problems`, `_plan_region_campaigns`; `PaintPlan.texts` and `.deletes`; `stratedit.new_block` and `plan_new_settlement`; `mapquery.add_music_region`; `POST /api/map/region_vocab`; three pickers and a campaigns line on the wizard. The shown names are required. `tests/test_campaint.py` part 4b (27 checks) and two real-data checks in part 5. Half of G2. Write-up in `ROADMAP_ARCHIVE.md`. |
| 20c - Labels, and picking a tile | **done** | Closed 2026-09-11, committed, **not released**. Closes T4 and M8 and with them Phase 20. New: `web/js/maplabels.js` (`clnLayout`, pure, and `clnDraw`), `web/js/mappin.js` (`cpinButton`, `cpinTake`), `Aa Labels` / `L` on the toolbar and `labels` in `cmapLayerState`, a pin beside every coordinate on the people and events panels. No Python changed. `tests/test_maplabels.py` (42 checks, most of them in node). Write-up in `ROADMAP_ARCHIVE.md`. |
| 20b - Getting to the thing you want | done | T9, T8 and D14, 2026-09-11, on beta 2026-09-11. Write-up in `ROADMAP_ARCHIVE.md`. |
| 21 - the rest of the Now set (3.1.0) | **scoped** | One session: the faction dependency audit (D6) and a raw text editor for the campaign files (D11). |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions: placing forts, watchtowers and resources, the textured terrain render, delete-a-region and create-a-campaign. |
| B2-B4 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export; `Rename slot` on a packed mod. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-20c | done | Published on the beta line; the 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 94 suites were run after 20c: **90 pass and the same four do not**, the DaC four below.

**Four suites fail the same way on a clean `master`** - hard-coded Divide and
Conquer numbers (77 port pixels, 13,153 newlines, 305 characters, 73,904 sea
tiles) against an installed DaC that is a different build: `test_campmap`,
`test_campstrat`, `test_campview`, `test_stratchar`. Stash and re-run before
believing one of them.

**Three suites need node**: `tests/test_maplayers.py` (20a),
`tests/test_mapgo.py` (20b) and `tests/test_maplabels.py` (20c). Without node on PATH each prints a skip line and
its Python half still runs.

**Two suites bind a socket and can collide inside a back-to-back run**
(`test_buildings_http`, `test_viewer3d_http`, `WinError 10013`), and **two
one-second timing bars are load-sensitive** (`test_mapcheck`'s rule-set bar,
`test_mapquery`'s warm fact-table bar). Re-run any of the four alone and idle
before believing it.

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- `campaint.map_campaigns` - **before writing anything to the base map** (B1).
  The engine reads each map file from the campaign's own folder when it is
  there, so a write to `world/maps/base` reaches only the campaigns that do not
  ship their own copy, and each of those may read its own copy of the files
  around it.
- `unittransfer/renames.py` - **before adding any "follow this name" feature.**
  Position-aware everywhere, and the docstring says why with numbers.
- `unittransfer/campstrat.py`'s **two campaign lists** (20b): `campaigns` is the
  top level the engine's menu reads, `campaign_paths` is every campaign at any
  depth and is what anything offering a campaign must use. `campaign_rel` is the
  ONE conversion from a campaign name to a path.
- `unittransfer/flatrecord.py` - **check here before writing any parser.**
- **The game's own unpacked `data/` is on this machine**, at
  `tests/_realmod.MODS.parent`. Look there before calling a format unmeasurable.
- `web/js/campmap.js` - `cmapMask`, the one pixel pass, and `cmapLayerState`,
  the one description of the layer stack. `cmapGoTile` is the one arrival.
- `web/js/mappin.js` - **before adding a coordinate field anywhere** (20c).
  `cpinButton(what, fn, args)` is the whole of it, and it hands your function
  the tile already in game coordinates. Phase 22's dialogs are the next callers.
- `web/js/core.js` - `MODES` in `wire()`. One global scope, no build step; a new
  module is a file, a `<script>` tag and a `MODES` entry, all three guarded by
  `tests/test_web_modules.py`.

## Upstream
Reference tool reviewed SHA **2740b0b**. `sync` was last run on 2026-09-11,
before 20b, and was up to date. B1 touched no screen the reference covers
beyond the wizard it already had, so it did not re-run it; **20c touches the
map screen, so run `sync` first.** `docs/upstream/PORT_MANIFEST.json` is
authoritative: 310 files triaged, none untriaged. `REFERENCE_GAPS.md` marks
G2 half done.

## Decisions
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
- 2026-09-11: **The first line of a crash log is the one to read.** B1 was filed
  as "no settlement block", and the log's own first line - the game finding the
  new pixel colour and not the record - named the bigger half.
- 2026-09-11: **A list something is picked from is part of the feature, and
  "the picker already exists" is a claim to measure.** D14 was filed as a
  cosmetic browser over a picker two documents said was already there. There was
  no picker - every route took a campaign and nothing ever sent one - and the
  list it would have been built on read only the top level of
  `world/maps/campaign`, hiding a whole second campaign in all three installs
  here. **This is 19b's lesson twice running: a claim that is nearly true is
  what the next session builds on.**
- 2026-09-11: **The moment a name can come off the page it needs one choke
  point.** `campstrat.campaign_rel` is the only conversion from a campaign name
  to a path under `world/maps/campaign`, and `strat_path`,
  `campfiles.campaign_dir`, `campevents.events_path`, `winconds.path_for`,
  `mapquery.Facts` and `mapcheck.Check` all go through it. A nested campaign IS
  a name with a separator in it, so the rule is not "no separators" - it is
  "no step that leaves the folder".
- 2026-09-11: **A key built out of a campaign's name is built out of its leaf.**
  Measured on Divide and Conquer, whose `custom/Shattered_Alliances` is keyed
  `SHATTERED_ALLIANCES_*` in `campaign_descriptions.txt` and not by the path it
  is reached through. 18a could not be wrong about this in practice because
  nothing offered a nested campaign; 20b did, so it had to be corrected first.
- 2026-09-11: **A search box is not a filter panel, and it answers out of what
  the screen already has.** 16g's twenty-four filters are for a question; T8 is
  for a name you already know, so it is one box, three tiers, no fuzziness, and
  no request per keystroke. What that cost was two short strings a region on the
  manifest - the words the player reads - because a box that only matches
  `Anorien_Province` is a box only somebody who has read the files can use.
- 2026-09-11: **A preset is a place-free copy of the layer stack.** 16d's ruling
  about what `map_layers` keeps applies whole: the layers, their order, their
  opacity, the punched colours and the colouring are habits; the zoom, the pan
  and the selection are a place. So `cmapSaveLayers` was split and
  `cmapLayerState` is the one snapshot both the remembered stack and every
  preset are copies of.
- 2026-09-10: **A different way of reading a layer is not another layer.** The
  stack is the ten files the map is made of: it is what T11's ten number keys
  count, what the draw order orders and what `check_layers` validates. So 20a's
  river overlay and its height transparency are controls on the row of the layer
  they are a reading of, not entries beside it. `cmapMask` is where such a
  reading is implemented, and `cmapModeKey` is what both it and the composite
  cache on.
- 2026-09-10: **"Darker means more transparent" is a rule about order, not about
  the number.** Alpha = the grey itself draws half of both installed maps'
  land at under 13%, because the median land tile is 32 of 255. The ramp T2
  ships is the land's own distribution - monotonic, so darker is still more
  transparent, but spread over the heights the map actually has. A reference's
  rule can be right about the direction and useless about the scale, and that is
  found by measuring rather than by implementing it.
- 2026-09-10: **A key a screen prints has to be a key the server assigned.**
  `campmap.HOTKEYS` travels out with each layer in the manifest and the panel
  prints what it was given, so a layer added or reordered cannot leave the badge
  and the handler disagreeing.
