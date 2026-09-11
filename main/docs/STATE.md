# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-11 · v2.2.3 is still the latest 2.x and beta 2026-09-11 the
latest beta · after 21, the faction audit and the raw text editor, which closes
the Now set (3.1.0) · **nothing is released until the roadmap is finished**_

## Next up
**Phase 22a, forts and watchtowers** (`ROADMAP.md`): click the map to add one,
drag to move one, delete one, following 16h and 16i's writer exactly, with a ⌖
pin (`cpinButton`) beside every coordinate. Then 22b, 23a, 23b and 24 - **five
sessions left in all**, B2-B4 not counted. 21's write-up is in
`ROADMAP_ARCHIVE.md`.

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

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**Written and held: v2.2.4 + beta 2026-09-11b.** The notes are in
`docs/releases/` (`RELEASE_2_2_4.md`, `RELEASE_BETA_2026_09_11B.md`) and the
two fixes are committed. **Fold them into the end-of-roadmap cut** - and B1 has
to be added to both notes, since the beta note's "Not fixed" section describes
exactly what B1 fixed. 20b, 20c, B1, 21 and the map hover fix below are not
in any note yet either.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 21 - Two screens over data we hold | **done** | Closed 2026-09-11, committed, **not released**. Closes D6, D11 (= M14) and the Now set. New: `unittransfer/factionaudit.py` (`Census`, `evaluate`, `audit`, `repair_plan`), `unittransfer/rawtext.py` (`files`, `read`, `splice`, `plan`, `apply`), `web/js/facaudit.js`, `web/js/rawtext.js`, the `rawtext` mode, `GET /api/factions/audit`, `POST /api/factions/repair_plan\|repair_apply`, `GET /api/raw/files\|file`, `POST /api/raw/plan\|apply`. `factionclone.clone_file` and `ClonePlan.action` (refactor, clone suites unchanged). `tests/test_factionaudit.py` (48), `tests/test_rawtext.py` (57). |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions: placing forts, watchtowers and resources, the textured terrain render, delete-a-region and create-a-campaign. |
| B2-B4 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export; `Rename slot` on a packed mod. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-21 | done | 16-20a published on the beta line; 20b onward committed and uncut. The 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 96 suites were run after 21: **92 pass
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
  `cpinButton(what, fn, args)` is the whole of it; 22a's dialogs are the next
  callers.
- `campaint.map_campaigns` - **before writing anything to the base map** (B1).
  A write to `world/maps/base` reaches only the campaigns that do not ship
  their own copy.
- `stratchar.UNTOUCHED` and 16h's `stratedit.plan_settlement` - the guard 22a
  lifts for forts and watchtowers, and the writer shape it copies.
- `unittransfer/factionaudit.py` - **before adding any check about a faction.**
  `Census` already counts every slot in every file; gap or note is measured on
  the installed mods, never copied from a reference.
- `unittransfer/rawtext.py` - `rtOpen(rel, line)` is how any screen offers
  "open this file as text"; a parser that meets a line it does not model points
  there rather than growing a special case.

## Upstream
Reference tool reviewed SHA **2740b0b**. `sync` was run on 2026-09-11 during
21 and was up to date. `docs/upstream/PORT_MANIFEST.json` is authoritative: 310
files triaged, none untriaged; `src/pages/TextEditor.jsx` notes it done in 21.
`REFERENCE_GAPS.md` marks D6, D11 and M14 done and G2 half done. **22a touches
the map screen and ports Demir's object dialogs, so run `sync` first.**

## Decisions
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
- 2026-09-11: **A key built out of a campaign's name is built out of its leaf.**
  Measured on Divide and Conquer, whose `custom/Shattered_Alliances` is keyed
  `SHATTERED_ALLIANCES_*` in `campaign_descriptions.txt` and not by the path it
  is reached through. 18a could not be wrong about this in practice because
  nothing offered a nested campaign; 20b did, so it had to be corrected first.
