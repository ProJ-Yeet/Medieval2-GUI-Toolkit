# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-11 · v2.2.3 is still the latest 2.x and beta 2026-09-11 the
latest beta · after 22a, forts and watchtowers, the first session of the Next
set (3.2.0) · **nothing is released until the roadmap is finished**_

## Next up
**Phase 22b, resources and the snap** (`ROADMAP.md`): the 1,131 resources
through 22a's writer (`stratobj.KINDS` gains `resource`; a resource is written
at the top of the file, not in a section, so where it goes is the new part),
`mapcheck`'s duplicate and position rules reused rather than rewritten, and D10's
spiral search over `mapcheck.marker_faults` turning "no" into "no, but here".
Then 23a, 23b and 24 - **four sessions left in all**, B2-B4 not counted. 22a's
write-up is in `ROADMAP_ARCHIVE.md`.

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
**22a is map work** and belongs to the beta line only.

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**Written and held: v2.2.4 + beta 2026-09-11b.** The notes are in
`docs/releases/` (`RELEASE_2_2_4.md`, `RELEASE_BETA_2026_09_11B.md`) and the
two fixes are committed. **Fold them into the end-of-roadmap cut** - and B1 has
to be added to both notes, since the beta note's "Not fixed" section describes
exactly what B1 fixed. 20b, 20c, B1, 21, the map hover fix and 22a are not in
any note yet either.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 22a - Forts and watchtowers | **done** | Closed 2026-09-11, committed, **not released**. First half of D9 (and G5). New: `unittransfer/stratobj.py` (`plan`, `apply`, `view`, `Vocabulary`, `render_line`, `new_section`), `web/js/campforts.js` (the 🏰 Forts panel), `GET /api/map/objects`, `POST /api/map/object_plan\|_apply`. 17d's drag takes forts and watchtowers (`CMK_DRAGGABLE`). `tests/test_stratobj.py` (65). |
| 21 - Two screens over data we hold | done | Closed 2026-09-11, committed, **not released**. Closes D6, D11 (= M14) and the Now set. New: `unittransfer/factionaudit.py` (`Census`, `evaluate`, `audit`, `repair_plan`), `unittransfer/rawtext.py` (`files`, `read`, `splice`, `plan`, `apply`), `web/js/facaudit.js`, `web/js/rawtext.js`, the `rawtext` mode, `GET /api/factions/audit`, `POST /api/factions/repair_plan\|repair_apply`, `GET /api/raw/files\|file`, `POST /api/raw/plan\|apply`. `factionclone.clone_file` and `ClonePlan.action` (refactor, clone suites unchanged). `tests/test_factionaudit.py` (48), `tests/test_rawtext.py` (57). |
| 22b-24 - the rest of the Next set (3.2.0) | **scoped** | Four sessions: resources and the snap, the textured terrain render, delete-a-region and create-a-campaign. |
| B2-B4 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export; `Rename slot` on a packed mod. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-21 | done | 16-20a published on the beta line; 20b onward committed and uncut. The 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 97 suites were run after 22a: **93 pass
and the same four do not**, the DaC four below, each on its documented number.

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
  `cpinButton(what, fn, args)` is the whole of it; 22a's form and its two
  Place buttons use it, and 22b's resource form is next.
- `campaint.map_campaigns` - **before writing anything to the base map** (B1).
  A write to `world/maps/base` reaches only the campaigns that do not ship
  their own copy.
- `unittransfer/factionaudit.py` - **before adding any check about a faction.**
  `Census` already counts every slot in every file; gap or note is measured on
  the installed mods, never copied from a reference.
- `unittransfer/stratobj.py` - **before writing 22b.** One writer for every
  one-line thing on the map; a resource is a new `KINDS` entry and a new "where
  it goes", not a new module. Its guard is the one to keep.
- `unittransfer/rawtext.py` - `rtOpen(rel, line)` is how any screen offers
  "open this file as text"; a parser that meets a line it does not model points
  there rather than growing a special case.

## Upstream
Reference tool reviewed SHA **2740b0b**. `sync` was run on 2026-09-11 at the
start of 22a and was up to date. `docs/upstream/PORT_MANIFEST.json` is authoritative: 310
files triaged, none untriaged; `src/pages/TextEditor.jsx` notes it done in 21.
`REFERENCE_GAPS.md` marks D6, D11 and M14 done and G2 half done. 22b ports the
rest of Demir's object dialog and Geomod's Localize; run `sync` first.

## Decisions
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
