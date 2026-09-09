# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-09 · **v2.2.3 latest and beta 2026-09-09b alongside it, off
the same tree - `master` itself keeps the map on** · after Phase 19b, rename and
follow it, cut on both lines_

## Next up
**Phase 20a, three layers read properly** (`ROADMAP.md`). 19b closed on
2026-09-09 and with it all of Phase 19; the write-up is in `ROADMAP_ARCHIVE.md`.
What is left of the 3.1.0 Now set is Phase 20 (three sessions on the map screen)
and Phase 21 (two screens over data we already hold).

**Cut after every change, from 2026-09-09.** The user's standing instruction:
every change is released as it lands, without being asked. **Which lines depends
on what the change touched** - map-only work is **the beta alone**, and the 2.x
subrelease is cut only when something outside the campaign map changed. 19b was
both, because renaming a faction is reached from the Factions screen.

## WHERE THINGS ARE - the tree moved on 2026-09-06
Only the two `.bat` files and `README.md` are at the top of the repository.
**Everything else is under `main/`, and `main/` is the code root** - what
`config.PROJECT_ROOT` resolves to, what a test's `parents[1]` is, and what every
path in this file and in the source is relative to. `main/dev/` never ships.

## THE TWO RELEASE LINES - read this before cutting anything
Two lines off this one `master`, chosen by whether a change touches the campaign
map. **Not campaign-map** → a **2.x subrelease with the map hidden**, uploaded
`--latest` (latest **v2.2.3**, 2026-09-09). **Campaign-map** → the **beta line**,
uploaded as a **pre-release** (latest **beta 2026-09-09b**). A **subrelease means
both**: one job, both zips, same tree.

**Every change is cut as it lands, and the lines follow the change** (the user's
rule, 2026-09-09). A change that touches **nothing outside the campaign map is
the beta only** - do not cut a 2.x that carries no visible difference. A change
that touches anything else is a subrelease, which is both. Nobody has to ask.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`, which `menuModes()` and `modeOffered()` are the only readers
of. It is a **release-time edit, not a state of `master`** - set it, bump the 2.x
number, build, upload, then put it straight back off in the next commit.
`master` carries the map ON, and `__version__` says `beta-2026-09-09b` because
the beta was the last thing cut, which is honest rather than untidy.

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**What v2.2.3 actually carried**, out of one phase: the Factions screen's
`Rename slot`, which is 19b's engine over a faction and is outside the map, plus
the Code View refusal that now names it. The region and settlement half of the
same engine is reached from the map screen and went to the beta alone.

**3.0.0 final** is the beta's feature set with whatever the beta turns up fixed.
**3.1.0** is Phases 18 to 21, and six of its sub-phases are now complete and
published on the beta line.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 19b - Rename, and follow it | **done** | D2 and D3 closed 2026-09-09. New: `renames.py`, `web/js/renameui.js`, `tests/test_renames.py` (56 checks), one POST pair, `Rename` on the region panel's two locked fields and `Rename slot` on Factions. Corrected the claim that `descr_strat.txt` names a settlement. Write-up in `ROADMAP_ARCHIVE.md`. |
| 19 as a whole | **done** | All four items. 19a on 2026-09-09, 19b the same day. |
| 20-21 - the rest of the Now set (3.1.0) | **scoped** | Four sessions: the map screen's second pass (20a, 20b, 20c) and two screens over data we already hold (21). |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions: placing forts, watchtowers and resources, the textured terrain render, delete-a-region and create-a-campaign. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-18 | done | The campaign map editor, its correction pass, and the six files nothing could edit. Published on the beta line; the 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 91 suites were run after 19b: **87 pass
and the same four do not**, and those four fail identically on a stashed clean
`master` - they are hard-coded Divide and Conquer numbers (77 port pixels,
13,153 newlines, 305 characters, 73,904 sea tiles) and the installed DaC is a
different build. Stash and re-run before believing one of those four:
`test_campmap`, `test_campstrat`, `test_campview`, `test_stratchar`.

**Two one-second timing bars are load-sensitive** and neither is any recent
phase's doing: `test_mapcheck`'s rule-set bar and `test_mapquery`'s warm
fact-table bar both pass idle and can miss inside a back-to-back run of all 91.
**Re-run either idle before believing it.**

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- `unittransfer/renames.py` - **before adding any "follow this name" feature.**
  It is position-aware everywhere and the docstring says why with numbers: over
  these namespaces a token walk corrupts real mods. It also holds
  `campaign_dirs`, which finds a campaign folder at any depth where
  `campstrat.campaigns` finds only the top level, and `region_files`, because a
  campaign may ship its own `descr_regions.txt`.
- `unittransfer/flatrecord.py` - **check here before writing any parser.** 18a
  used it for one block, 18b could not use it at all, and 19a and 19b needed no
  parser of their own: every file they touch was already owned. Check who owns a
  format before writing a second reader of it.
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
untriaged. `docs/upstream/REFERENCE_GAPS.md` now marks D2, D3, D4, D5, M3, M4,
M5, M6, M13 and G3 done.

## Decisions
- 2026-09-09: **A rename is position-aware; a token walk is not good enough
  here.** `unitrefs.py`'s rule - rewrite the token wherever it stands alone -
  works over unit types and corrupts these three namespaces. Divide and Conquer's
  settlement `Eregion` is also a hidden resource on twenty other regions' flags
  line **in the same file**, and settlement names matched in sixty files across
  the two installed mods. Every file is asked which of its *lines* may hold a
  name of this kind, through the module that owns it.
- 2026-09-09: **A clone reports what a rename must follow, and that is not an
  inconsistency.** `factionclone.REVIEW_FILES` are files where naming the donor
  is a judgement - adding a clone to `and FactionType sicily` rewrites a boolean.
  A rename adds nothing: the condition already exists and already means this
  faction. So traits, ancillaries, prebattle speeches, missions and guilds are
  rename sites. `descr_strat.txt` is the mirror: a clone refuses it because there
  is nothing to copy, a rename must follow it because the block is there.
- 2026-09-09: **Cut every change as it lands, and let the change pick the
  lines.** The user's standing instruction: no asking, and no letting phases pile
  up the way 18a, 18b and 19a did. Map-only work is **the beta alone**; anything
  touching the rest of the toolkit is a subrelease, which is both lines.
  `HANDOFF.md` rule 1 carries the steps.
- 2026-09-09: **A round trip is not a proof that a format is understood.**
  `minorfiles.parse_names` reproduced `descr_names.txt` byte for byte while
  reading a `surnames` heading as a character name, because a line it misfiles
  is still a line it writes back. 19b found the same shape in prose rather than
  code: three places said `descr_strat.txt` points at a settlement's name, and
  measured over both installed mods it does not. **A claim that is nearly true is
  what the next session builds on.**
- 2026-09-09: **One save per file, unless one act spans several.** 18a's rule
  stands; the exceptions are a record being created and now a rename, where an
  undo of half of it leaves a mod that will not load.
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
