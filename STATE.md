# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-06 · **two lines now: beta 2026-09-06 with the campaign map,
and v2.2.0 with it hidden** · Phase 17 done, plus ten unit-editor faults the user
raised after it_

## Next up
**Phase 18a, four files nobody could edit** (`ROADMAP.md`, Backlog). Phase 17
closed on 2026-09-06 and its write-up is in `ROADMAP_ARCHIVE.md`.

## THE TWO RELEASE LINES - read this before cutting anything
The project ships on **two lines off this one `master`**, and which line a change
belongs to is decided by whether it touches the campaign map:

* **Not campaign-map** (unit editor, transfer, buildings, BMDB, sprites, sounds,
  minor files, strings) → a **2.x subrelease with the map hidden**, uploaded
  `--latest`. First one is **v2.2.0**, 2026-09-06.
* **Campaign-map** → committed here and shipped on the **beta line**, uploaded
  as a **pre-release**. First one is **beta 2026-09-06**.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`. `menuModes()` and `modeOffered()` in the same file are what the
burger menu, Home's readiness cards, the resume button and Minor Files' Factions
tab all read, so hiding the mode is that single edit and nothing else drifts.
With the map off, the Factions tab falls back to the standalone `factions` mode,
which is where a mod with no map has always landed. `tests/test_web_modules.py`
asserts the flag's handling and that fallback.

**`master` currently carries `off:true` and `__version__ = "2.2.0"`.** To cut the
next beta: clear the flag, bump to the beta version, build, upload as a
pre-release. To cut the next 2.x: leave the flag set and bump the 2.x number.

**Betas are named by the DATE they were released, not by a version.** There is no
`v3.0.1-beta`; the beta cut today is `beta 2026-09-06`. Everything about a beta
carries that date:

| | |
|---|---|
| git tag | `beta-2026-09-06` |
| GitHub title | `M2 GUI-Kit beta 2026-09-06` |
| `__version__` | `beta-2026-09-06` |
| notes | `merge/RELEASE_BETA_2026_09_06.md` |
| zip | `python build_release.py --version beta-2026-09-06` |

The 2.x line keeps its numbers - `v2.2.0`, `v2.2.1` - because those are the
releases people are meant to compare. A beta is a snapshot of the map work on the
day it was taken, and the date says everything the number was pretending to.

The GitHub **title** is `M2 GUI-Kit V<X.Y.Z>` - hyphenated **GUI-Kit**, capital
**V** - and has been for every release since V2.0.0; see `ROADMAP.md` under
Versioning. V2.2.0 and the first beta both went up as "M2 GUIkit" and had to be
renamed. Run `gh release list --limit 3` and copy the newest title's shape rather
than typing it from memory.

## The releases
**v2.2.0, 2026-09-06** - the ten unit-editor fixes below, campaign map off the
menu. Notes in `merge/RELEASE_2_2_0.md`. This is the `--latest` release.

**beta 2026-09-06** - the same toolkit with the campaign map switched on. It was
cut from this tree before the flag went in; the notes are
`merge/RELEASE_BETA_2026_09_06.md` and the zip is on GitHub as a pre-release. Its
git tag is still `v3.0.0-beta`, because a published download link is not worth
breaking for a rename; every beta after it is tagged by date. It is a beta because it
is the first build in anyone's hands that writes to a campaign; the known limits
are listed at the bottom of the notes (forts, watchtowers and resources are read
and drawn but not placed, the terrain render is flat, delete-a-region and
create-a-campaign are not in it). A **3.0.0 final** is the same feature set with
whatever the beta turns up fixed.

**Ten unit-editor faults, fixed 2026-09-06**, all reported by the user against
Phase 13-15 code and all verified in a running browser on Third_Age_Reforged.
They are what v2.2.0 exists to ship, and they are in the beta too. The first six:

- a new bmdb entry could not be given its own attachment texture / normal map -
  `NewModel.attach_texture_src` / `attach_normal_src`, and no sprite is written
  into an attachment record any more
- a staged entry read as "not an entry in this mod's battle_models.modeldb" -
  `gfHostEditor.creates` returned `[]` while `state.ed.newModels` held it
- the model picker and the field vocabulary are read once per mod and kept, so a
  new entry stayed invisible - `edDropModCaches` on save, plus pending entries
  offered by both
- "Point EDU slot at it" replaced an armour tier instead of adding one -
  `edAssignSlots` says what each choice replaces and ends with the next tier,
  `edNextTierSlot` is the default, and `edu.sync_armour_levels` keeps
  `armour_ug_levels` in step with an appended tier
- an imported unit card never saved: `edDirty` did not count `cardSrc` /
  `infoSrc`, so Save said "Nothing to save"
- "Replace for every faction" now asks WHERE (a tick box per owning faction
  folder plus the merc fallback, `card_folders` / `info_folders` on the request)
  and WHICH (the pictures on disk, but only when the folders really hold more
  than one); `edit._resolve_icon_src` reads a mod-relative source and will not
  climb out of `data/`

**And two more the user raised while the release was being cut:**

- the card you replaced went on being the card you saw. `shutil.copy2` carries
  the SOURCE's timestamps onto the copy and a mod's files share an mtime to the
  second, so `IconCache._key` (path + mtime) never changed. `logutil.stamp_written`
  is the fix, with the file size added to the key as a backstop; the page half is
  `state.iconV` through `iconBust()`, because `imgBust` only ever patched the
  `<img>` tags that were on screen and a save re-renders the whole grid.
- renaming a staged entry left `armour_ug_models` on the old name -
  `edRenamePending` / `edPendingRefs`, with the form saying which lines follow.

`tests/test_new_entry_and_cards.py`, 34 checks.

The plan after this needs no decisions: the audit's forty open
items were classified on 2026-09-05 (20 Now, 7 Next, 13 Later, none skipped) and
ROADMAP.md's Backlog turns that into fourteen sessions - Phases 18-21 as
**3.1.0**, Phases 22-24 as **3.2.0**, the Later set unphased. Its "whole plan on
one screen" table is the index.

Run `python tools/upstream_sync.py sync` first, as before every sub-phase.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 17 - Campaign map correction pass | **done** | All eight items plus 17i's exit, 2026-09-06, five commits. Write-up in `ROADMAP_ARCHIVE.md`. Folds into 3.0.0. |
| 16 - Campaign Map Editor (V3.0.0) | **done** | 16a-16k all landed 2026-09-03 to 2026-09-05: `campmap`, `maptga`, `mapvocab`, `campstrat`, `campaint`, `mapcheck`, `mapquery`, `stratedit`, `stratchar`, `stratcamp`, `winconds`, `cas`, and their seven web modules. Feature-complete and **not yet released**. Write-ups in ROADMAP_ARCHIVE.md, session detail in STATE_ARCHIVE.md. |
| 18-21 - the Now set (3.1.0) | **scoped** | Eight sessions closing the twenty items marked Now. 18 is the five campaign files nothing could edit, 19 is the names nothing could follow, 20 is the map screen's second pass, 21 is two screens over data we already hold. Fifteen of the twenty are S-sized, five are M and none is L. |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions closing the seven Next items: placing forts, watchtowers and resources on the map (the largest single hole - 105, 295 and 1,131 of them read on DaC and nothing writes any), the textured terrain render, and delete-a-region / create-a-campaign. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. **Renumbered from V3.1/V3.2/V3.3 on 2026-09-05**; the manifest's `notes` were updated to match. |
| 0-15j | done | shipped through v2.1.11. Exit criteria and write-ups in ROADMAP_ARCHIVE.md. |

## In-progress detail
**Clean.** Nothing is mid-flight. Phase 17 is complete, the ten unit-editor
faults above are fixed and tested, and both builds are uploaded: beta 2026-09-06
as a pre-release and v2.2.0 as latest.

`unittransfer/__init__.py` says `2.2.0` and `campmap` carries `off:true`, so this
tree is the 2.x line as it stands. The next cut off the beta line is 3.0.0 final;
see **THE TWO RELEASE LINES** at the top for the one flag that switches between
them.

What Phase 17 changed, in one line each (numbers and reasoning in
`ROADMAP_ARCHIVE.md`):

- `unittransfer/modfiles.py` - `campmap` on the readiness matrix with its
  fourteen files; `test_web_modules` asserts every menu module has an entry.
- `web/js/campmap.js` - dirty rectangles snapped to whole device pixels (the
  hover trail), the marker click resolved to its region, and the hover tooltip.
- `unittransfer/campmap.py` - `_vocab_view` in the manifest, so the tooltip
  names every layer without a round trip.
- `web/js/campmark.js` (new), `campstrat.markers`, `mapquery.marker_view`,
  `GET /api/map/markers` - the markers layer, off by default, drag-to-plan.
- `web/js/stratcamp.js` + `web/js/factions.js` - one faction screen over two
  files, two saves; Minor Files' tab routes to it.
- `web/js/core.js`, `web/index.html`, `tools/prose_check.py` - the menu hints as
  sentences, the rule that catches the next one, and the new credits.

Two standing traps, neither of them mid-flight but both worth reading before a
suite run: the installed mod here is **Third Age Reforged, not DaC**, so the DaC
numbers quoted throughout the archive cannot be re-run on this machine (tests
run via `python -m tests.test_X` and cold-start timing checks fail on a cold
cache), and the suite leaks `ut_*` temp directories into `%TEMP%`.

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. It is 600 lines now, not 3,000; read all of it.
- `unittransfer/flatrecord.py` - **check here before writing any parser.** Phase
  11 needed no code at all, which is why it exists.
- `unittransfer/campmap.py` and `unittransfer/campstrat.py` - the read half of
  the map editor. Everything in Phase 16 above 16b is built on these two, and
  the byte-exact round trip in `campstrat` is the gate on all four writers.
- `web/js/core.js` - `MODES` in `wire()`, and `docPoints()`, which every note in
  the UI is written through. One global scope, no build step; adding a module
  means a new file, a `<script>` tag and a `MODES` entry, all three guarded by
  `tests/test_web_modules.py`.

## Upstream
Reference tool reviewed SHA **319ae56** (2026-09-06), run before Phase 17 as the
rule asks. The one commit since `ac503ac` changed two files and both triage as
`skip` - boilerplate we own outright - so nothing was ported, and Phase 17's two
borrowings (`StratOverlay.jsx` for the markers layer, `MapPixelTooltip.jsx` for
the tooltip) were read at that SHA. The log entry is the newest in
`merge/SYNC_LOG.md`; the detail from the sync before it (what
`factionBlockOps.js` taught 16b, the five `phases` lists written as numbers that
crashed `sync --accept`, the phase renumbering) is in `STATE_ARCHIVE.md`.

`src/components/map/` is where the reference tool's author is actively
working, so a sub-phase that
touches the map screen still runs `sync` first.

`merge/PORT_MANIFEST.json` is authoritative. It triages all 310 upstream files:
128 port-concept, 90 skip, 71 out-of-scope, 21 audit, none untriaged. The
port-concept set is what `merge/REFERENCE_GAPS.md` measures against.

## Open questions for the user
- ~~`merge/REFERENCE_GAPS.md` needs prioritising.~~ **Answered 2026-09-05:**
  all forty open items classified, 20 Now / 7 Next / 13 Later / none skipped,
  and written up as Phases 18-24. Two Later items are flagged in the roadmap as
  cheap to take early if the user changes their mind - **G4** during 19a and
  **D1** during 19b - and neither was moved.
- `descr_sounds_*.txt` (32 files in DaC) is a real coverage gap the Phase 13
  audit measured and did not close - the engine's sound scripts, a grammar of
  its own. Its own phase later, or permanently out of scope?
- ~~`OsmBackground.jsx` / `OsmRegionSearch.jsx` - port or drop?~~ **Answered
  2026-09-03: ported, deferred to Phase 25**, opt-in and off by default,
  together with `CoastlineTracer`. The generators are Phase 27.

## Decisions
- 2026-09-05: **Future work gets a phase number; a version number is assigned
  only when something is cut.** The three future releases were named `V3.1`,
  `V3.2` and `V3.3` after the features in them, and none of those features is in
  the Now or Next set - so all three would have shipped after work carrying no
  number at all. They are Phases 25, 26 and 27 now. This is how Phases 0 to 16
  worked, and `merge/PORT_MANIFEST.json`'s `notes` were updated in the same
  commit so no cross-reference dangles.
- 2026-09-05: **A finished phase leaves the roadmap.** `ROADMAP.md` had reached
  3,031 lines and `STATE.md` 2,094, and every session was reading both in full
  to find one sentence. Finished write-ups now move to `ROADMAP_ARCHIVE.md` and
  session logs to `STATE_ARCHIVE.md`, in the same commit that marks the phase
  done. The contract is at the bottom of `ROADMAP.md`.
