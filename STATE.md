# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-06 · **v2.1.11 released**, V3.0.0 feature-complete and uncut ·
**Phase 17 is done** - all eight items, verified in a browser on both installed
maps. The user has said to hold the release for now_

## Next up
**Phase 18a, four files nobody could edit** (`ROADMAP.md`, Backlog). Phase 17
closed on 2026-09-06 and its write-up is in `ROADMAP_ARCHIVE.md`.

**The release is held.** V3.0.0 is feature-complete and correct - Phase 17 was
the correction pass over it - but the user has said to hold. When it is called
for, cutting it is: bump `unittransfer/__init__.py`, write
`merge/RELEASE_3_0_0.md`, build, push and upload, per `HANDOFF.md`. Nothing
about that is blocked; it is waiting on the word.

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
**Clean.** Nothing is mid-flight. Phase 17 is complete, tested and committed;
the working tree is clean apart from the three untracked files the archive split
left (`ROADMAP_ARCHIVE.md`, `STATE_ARCHIVE.md`, `merge/REFERENCE_GAPS.md`).

V3.0.0 is feature-complete and **uncut, deliberately** - the version in
`unittransfer/__init__.py` is still 2.1.11 and there is no
`merge/RELEASE_3_0_0.md`, because the user has said to hold the release.

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
