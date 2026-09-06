# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-07 · **v2.2.1 latest and beta 2026-09-06b alongside it, off
the same tree - `master` itself keeps the map on** · after Phase 18a, the four
files nobody could edit_

## Next up
**Phase 18b, events and disasters** (`ROADMAP.md`, Backlog). 18a closed on
2026-09-07 and its write-up is in `ROADMAP_ARCHIVE.md`. Nothing is released off
3.1.0 yet; the next cut on either line is still whatever the user asks for.

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

**18a is on the 2.x side of that line** for one of its four screens and not the
other three: Guilds is a mode of its own, and the campaign descriptions, the
faction movies and the mercenary pool hang off the campaign map's faction and
region panels, so a cut with the map hidden ships Guilds alone. That is correct,
and it is the shape 17f's faction screen already has.

**3.0.0 final** is the beta's feature set with whatever the beta turns up fixed.
**3.1.0** is Phases 18-21 and is one sub-phase in.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 18a - Four files nobody could edit | **done** | M5, M6, M13, G3 closed 2026-09-07. New: `guilds.py`, `campfiles.py`, `web/js/guilds.js`, two suites (62 + 76 checks). Write-up in `ROADMAP_ARCHIVE.md`. |
| 18b - Events and disasters | **scoped** | The next session. `descr_events.txt` and `descr_disasters.txt`; the disaster's `position x, y` lines make it 17d's marker layer's second customer. |
| 19-21 - the rest of the Now set (3.1.0) | **scoped** | Five sessions: the names nothing could follow, the map screen's second pass, two screens over data we already hold. |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions: placing forts, watchtowers and resources, the textured terrain render, delete-a-region and create-a-campaign. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-17 | done | The campaign map editor and its correction pass. Fold into 3.0.0, uncut. |

## In-progress detail
**Clean.** Nothing is mid-flight. All 88 suites were run after 18a; **84 pass and
the four that do not fail identically on a stashed clean `master`** - they are
hard-coded Divide and Conquer numbers (77 port pixels, 13,153 newlines, 305
characters, 73,904 sea tiles) and the installed DaC is a different build.
Stash and re-run before believing one of those four: `test_campmap`,
`test_campstrat`, `test_campview`, `test_stratchar`.

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.

One change in 18a reaches outside its own files and is worth knowing about:
**`triggers.DEFINITION_WORDS`**. A `BLOCK_ENDERS` line now ends a trigger only
when it is exactly two words, because `export_descr_guilds.txt` writes `Guild x`
as a definition and `Guild x s 25` as an effect. Without it every guild trigger
ended at its own first effect. Measured before it was written: all 1,850 `Trait`
and `Ancillary` lines in both mods are two words, so the EDCT and the EDA are
unaffected, and their suites are unmoved at 112 and 85.

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- `unittransfer/flatrecord.py` - **check here before writing any parser.** 18a
  checked, used it for one guild *block*, and could not use it for the guild
  *file*; the reason is in `guilds.py`'s docstring and is worth reading before
  the next file that has two block types.
- `unittransfer/campmap.py` and `unittransfer/campstrat.py` - the read half of
  the map editor, and the byte-exact round trip every writer is gated on.
- `web/js/core.js` - `MODES` in `wire()`, and `docPoints()`. One global scope, no
  build step; adding a module means a new file, a `<script>` tag and a `MODES`
  entry, all three guarded by `tests/test_web_modules.py`.

## Upstream
Reference tool reviewed SHA **319ae56** (2026-09-07, run before 18a as the rule
asks; unchanged since 2026-09-05, nothing new to triage). 18a read
`GuildsParser.jsx`, `GuildEditor.jsx`, `factionMoviesParser.jsx` and
`CampaignDescriptionsStrings.jsx` at that SHA and ported **behaviour knowledge
only**, as the rule says - and corrected three of the four along the way (their
guild serialiser reformats the whole file, their movie serialiser rebuilds it
from a model, and their scope letter set is missing `a`, which is 47 real lines).

`src/components/map/` is where the reference tool's author is actively working,
so a sub-phase that touches the map screen still runs `sync` first.
`docs/upstream/PORT_MANIFEST.json` is authoritative: 310 files triaged, none
untriaged. `docs/upstream/REFERENCE_GAPS.md` now marks M5, M6, M13 and G3 done.

## Open questions for the user
- `descr_sounds_*.txt` (32 files in DaC) is a real coverage gap the Phase 13
  audit measured and did not close - the engine's sound scripts, a grammar of
  its own. Its own phase later, or permanently out of scope?

## Decisions
- 2026-09-07: **A file whose definition keyword is also an effect keyword is
  told apart by word count, not by section.** `triggers.DEFINITION_WORDS`.
  Measured rather than assumed, and it is the first thing to check if a third
  trigger-bearing file is ever added.
- 2026-09-07: **One screen over several files means one save per file.** 18a's
  faction tab is four files and four Save buttons and the region panel is two.
  This is 17f's ruling restated because 18a is where it stopped being about one
  screen: combining the SCREENS must not combine the WRITES, or one undo puts
  back more than the user changed.
- 2026-09-05: **Future work gets a phase number; a version number is assigned
  only when something is cut.**
- 2026-09-05: **A finished phase leaves the roadmap** - write-ups to
  `ROADMAP_ARCHIVE.md`, session logs to `STATE_ARCHIVE.md`, in the same commit
  that marks the phase done.
