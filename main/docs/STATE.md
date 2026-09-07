# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-07 · **v2.2.1 latest and beta 2026-09-06b alongside it, off
the same tree - `master` itself keeps the map on** · after Phase 18b, events and
disasters_

## Next up
**Phase 19a, the keys a new record needs** (`ROADMAP.md`, Backlog). 18b closed on
2026-09-07 and with it all of Phase 18; both write-ups are in
`ROADMAP_ARCHIVE.md`. Nothing is released off 3.1.0 yet; the next cut on either
line is still whatever the user asks for.

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

**18b is entirely on the beta side of that line**, unlike 18a, which was split:
both of its files are edited from a panel on the map screen and drawn on the
map's marker layer, so a 2.x cut with the map hidden ships none of it.

**3.0.0 final** is the beta's feature set with whatever the beta turns up fixed.
**3.1.0** is Phases 18 to 21, and the first of those four is now complete.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 18b - Events and disasters | **done** | M3, M4 closed 2026-09-07, and with them all of Phase 18. New: `campevents.py`, `web/js/campevents.js`, one `mapcheck` rule, two marker categories, one suite (82 checks). Write-up in `ROADMAP_ARCHIVE.md`. |
| 19a - The keys a new record needs | **scoped** | The next session. D4 and D5: the localisation key a new region or settlement needs, and the one a new faction needs. |
| 19b-21 - the rest of the Now set (3.1.0) | **scoped** | Four sessions: rename-and-follow, the map screen's second pass, two screens over data we already hold. |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions: placing forts, watchtowers and resources, the textured terrain render, delete-a-region and create-a-campaign. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-17 | done | The campaign map editor and its correction pass. Fold into 3.0.0, uncut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 89 suites were run after 18b: **85 pass
and the same four do not**, and those four fail identically on a stashed clean
`master` - they are hard-coded Divide and Conquer numbers (77 port pixels,
13,153 newlines, 305 characters, 73,904 sea tiles) and the installed DaC is a
different build. Stash and re-run before believing one of those four:
`test_campmap`, `test_campstrat`, `test_campview`, `test_stratchar`.

**Two one-second timing bars are load-sensitive, and neither is 18b's doing.**
`test_mapcheck`'s rule-set bar failed inside the back-to-back run of all 89 and
passes 86/86 three times in a row idle - the same code measured 653 ms and
1,295 ms in two runs, and 968 ms with 18b's rule stashed out, and that rule
costs 9 ms. `test_mapquery`'s warm fact-table bar is the other: Divide and
Conquer lands anywhere from 98 to 743 ms against a 1,000 ms limit, and 18b
does not touch `Facts` at all. **Re-run either idle before believing it.**

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.
And 18b fixed one thing outside its own files: `dev/reference/upstream_sync.py
status` sorted phase numbers with `int()` and died on a sub-phase letter.

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- `unittransfer/flatrecord.py` - **check here before writing any parser.** 18a
  checked and could use it for one block only; 18b could not use it at all,
  because both of its files repeat their keywords - one event may carry four
  `date` lines and thirty-seven `position` lines. The reason is in
  `campevents.py`'s docstring.
- **The game's own unpacked `data/` is on this machine**, at
  `tests/_realmod.MODS.parent`. Both mods ship `descr_disasters.txt` empty, so
  18b measured against the stock file. Look there before calling a format
  unmeasurable.
- `unittransfer/campmap.py` and `unittransfer/campstrat.py` - the read half of
  the map editor, and the byte-exact round trip every writer is gated on.
- `web/js/core.js` - `MODES` in `wire()`, and `docPoints()`. One global scope, no
  build step; adding a module means a new file, a `<script>` tag and a `MODES`
  entry, all three guarded by `tests/test_web_modules.py`.

## Upstream
Reference tool reviewed SHA **319ae56** (2026-09-07, run before 18b as the rule
asks for a phase touching the map screen; unchanged since 2026-09-05, nothing
new to triage). 18b read the two parsers and two tabs at that SHA and ported
**behaviour knowledge only** - and corrected four things in them, listed in
`ROADMAP_ARCHIVE.md`.

`src/components/map/` is where the reference tool's author is actively working,
so a sub-phase that touches the map screen still runs `sync` first.
`docs/upstream/PORT_MANIFEST.json` is authoritative: 310 files triaged, none
untriaged. `docs/upstream/REFERENCE_GAPS.md` now marks M3, M4, M5, M6, M13 and
G3 done.

## Decisions
- 2026-09-07: **A value can be the thing with no evidence, not just a file.**
  Vanilla writes `region the sea` in two disaster blocks and there is no such
  region in `descr_regions.txt`, so a region rule with a perfectly good
  vocabulary would still have called the shipping game broken.
  `campevents.SEA_REGION` is the exemption; the locked decision has this second
  shape as well as the missing-file one.
- 2026-09-07: **A repeatable key needs two descriptions of one edit** - the
  positional splice for the disk (smallest diff) and the multiset difference for
  the dialog. `campevents._list_changes`. Saying it positionally reads as a
  rename followed by a delete, which is not what happened.
- 2026-09-07: **A file whose definition keyword is also an effect keyword is
  told apart by word count, not by section.** `triggers.DEFINITION_WORDS`.
  Measured rather than assumed, and it is the first thing to check if a third
  trigger-bearing file is ever added.
- 2026-09-07: **One screen over several files means one save per file.** 18a's
  faction tab is four files and four Save buttons, the region panel is two, and
  18b's events panel is two more. Combining the SCREENS must not combine the
  WRITES, or one undo puts back more than the user changed.
- 2026-09-05: **Future work gets a phase number; a version number is assigned
  only when something is cut.**
- 2026-09-05: **A finished phase leaves the roadmap** - write-ups to
  `ROADMAP_ARCHIVE.md`, session logs to `STATE_ARCHIVE.md`, in the same commit
  that marks the phase done.
