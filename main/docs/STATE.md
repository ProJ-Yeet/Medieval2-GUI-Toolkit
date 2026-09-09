# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-09 · **v2.2.1 latest and beta 2026-09-06b alongside it, off
the same tree - `master` itself keeps the map on** · after Phase 19a, the keys a
new record needs_

## Next up
**Phase 19b, rename and follow it** (`ROADMAP.md`, Backlog). 19a closed on
2026-09-09; the write-up is in `ROADMAP_ARCHIVE.md`. It left
`unittransfer/namekeys.py` behind, which is where 19b writes its text keys.
Nothing is released off 3.1.0 yet; the next cut on either line is still whatever
the user asks for.

## WHERE THINGS ARE - the tree moved on 2026-09-06
Only the two `.bat` files and `README.md` are at the top of the repository.
**Everything else is under `main/`, and `main/` is the code root** - what
`config.PROJECT_ROOT` resolves to, what a test's `parents[1]` is, and what every
path in this file and in the source is relative to. `main/dev/` never ships.

## THE TWO RELEASE LINES - read this before cutting anything
Two lines off this one `master`, chosen by whether a change touches the campaign
map. **Not campaign-map** → a **2.x subrelease with the map hidden**, uploaded
`--latest` (latest **v2.2.1**, 2026-09-06). **Campaign-map** → the **beta line**,
uploaded as a **pre-release** (latest **beta 2026-09-06b**). A **subrelease means
both**: one job, both zips, same tree.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`, which `menuModes()` and `modeOffered()` are the only readers
of. It is a **release-time edit, not a state of `master`** - set it, bump the 2.x
number, build, upload, then put it straight back off in the next commit.
`master` carries the map ON, and `__version__` says `beta-2026-09-06b` because
the beta was the last thing cut, which is honest rather than untidy.

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**19a is split across that line, unlike 18b.** D4 is the map screen and the
paint wizard, so a 2.x cut with the map hidden ships none of it. D5's two writes
are reached from the map's character panel and so go the same way - but the
`surnames` correction to `minorfiles.NAME_SECTIONS` is in the Minor Files
module, which is on the menu in both lines, and it is the one piece of this
phase a 2.x subrelease would carry.

**3.0.0 final** is the beta's feature set with whatever the beta turns up fixed.
**3.1.0** is Phases 18 to 21, and five of its sub-phases are now complete.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 19a - The keys a new record needs | **done** | D4 and D5 closed 2026-09-09. New: `namekeys.py`, `tests/test_namekeys.py` (55 checks), one POST pair, a names block on `/api/map/region`, three panels. Corrected `minorfiles.NAME_SECTIONS` and `stratchar.check_pool`. Write-up in `ROADMAP_ARCHIVE.md`. |
| 19b - Rename, and follow it | **scoped** | The next session. D2 and D3: one rename engine over a region, a settlement and a faction, refusing to edit `campaign_script.txt` and reporting every line of it instead. |
| 20-21 - the rest of the Now set (3.1.0) | **scoped** | Three sessions: the map screen's second pass, two screens over data we already hold. |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions: placing forts, watchtowers and resources, the textured terrain render, delete-a-region and create-a-campaign. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-18 | done | The campaign map editor, its correction pass, and the six files nothing could edit. Fold into 3.0.0 and 3.1.0, both uncut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 90 suites were run after 19a: **86 pass
and the same four do not**, and those four fail identically on a stashed clean
`master` - they are hard-coded Divide and Conquer numbers (77 port pixels,
13,153 newlines, 305 characters, 73,904 sea tiles) and the installed DaC is a
different build. Stash and re-run before believing one of those four:
`test_campmap`, `test_campstrat`, `test_campview`, `test_stratchar`.

**Two one-second timing bars are load-sensitive** and neither is any recent
phase's doing: `test_mapcheck`'s rule-set bar and `test_mapquery`'s warm
fact-table bar both pass idle and can miss inside a back-to-back run of all 90.
**Re-run either idle before believing it.**

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- `unittransfer/flatrecord.py` - **check here before writing any parser.** 18a
  used it for one block, 18b could not use it at all, and 19a needed no parser
  of its own: both of its files were already owned, by `minorfiles.py` and
  `stringsbin.py`. Check who owns a format before writing a second reader of it.
- **The game's own unpacked `data/` is on this machine**, at
  `tests/_realmod.MODS.parent`. Look there before calling a format unmeasurable.
- `unittransfer/campmap.py` and `unittransfer/campstrat.py` - the read half of
  the map editor, and the byte-exact round trip every writer is gated on.
- `unittransfer/namekeys.py` - every write into a `{key}value` file goes through
  `_write_loc`, which recompiles the `.strings.bin` beside it and takes the
  caller's own backup closure. A localisation edit that skips it leaves the game
  reading the old words.
- `web/js/core.js` - `MODES` in `wire()`, and `docPoints()`. One global scope, no
  build step; adding a module means a new file, a `<script>` tag and a `MODES`
  entry, all three guarded by `tests/test_web_modules.py`.

## Upstream
Reference tool reviewed SHA **2740b0b** (2026-09-09, run before 19a as the rule
asks for a phase touching the map screen). One commit since 2740b0b's
predecessor, two files, both `skip` disposition - nothing to port.

`src/components/map/` is where the reference tool's author is actively working,
so a sub-phase that touches the map screen still runs `sync` first.
`docs/upstream/PORT_MANIFEST.json` is authoritative: 310 files triaged, none
untriaged. `docs/upstream/REFERENCE_GAPS.md` now marks D4, D5, M3, M4, M5, M6,
M13 and G3 done.

## Decisions
- 2026-09-09: **A round trip is not a proof that a format is understood.**
  `minorfiles.parse_names` reproduced `descr_names.txt` byte for byte while
  reading a `surnames` heading as a character name, because a line it misfiles
  is still a line it writes back. What caught it was a coverage measurement
  against a *different* file. A parser with one section too few passes every
  test the project owns.
- 2026-09-09: **One save per file, unless one act spans several.** 18a's rule
  stands; the exception is a record being created, where an undo of half of it
  leaves the mod in a state nobody asked for. The region panel's name boxes are
  a third save; the wizard's are part of its one save.
- 2026-09-07: **A value can be the thing with no evidence, not just a file.**
  Vanilla writes `region the sea` in two disaster blocks and there is no such
  region in `descr_regions.txt`. `campevents.SEA_REGION` is the exemption.
- 2026-09-07: **A repeatable key needs two descriptions of one edit** - the
  positional splice for the disk (smallest diff) and the multiset difference for
  the dialog. `campevents._list_changes`.
- 2026-09-07: **A file whose definition keyword is also an effect keyword is
  told apart by word count, not by section.** `triggers.DEFINITION_WORDS`.
- 2026-09-05: **Future work gets a phase number; a version number is assigned
  only when something is cut.**
- 2026-09-05: **A finished phase leaves the roadmap** - write-ups to
  `ROADMAP_ARCHIVE.md`, session logs to `STATE_ARCHIVE.md`, in the same commit
  that marks the phase done.
