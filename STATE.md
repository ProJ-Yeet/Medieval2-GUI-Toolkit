# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-06 · **v2.1.11 released**, V3.0.0 feature-complete and uncut ·
six of Phase 17's eight items landed (17a, 17b, 17c, 17d, 17e, 17f); paused
mid-phase at the user's word with the tree clean_

## Next up
**Phase 17's last two items, 17g and 17h**, both small and both prose:

- **17g** - capitalise the hint under every module name in the burger menu
  (`MODES`, `web/js/core.js`), the nav brand's subtitle and the Credits hint in
  `web/index.html`. Then add a rule to `tools/prose_check.py` for a sentence
  that starts lower-case, which is why this survived a whole phase.
- **17h** - rewrite the Credits dialog body (`openCredits`, `web/js/core.js`).
  The new shape, contributor by contributor, is written out in ROADMAP.md's
  Phase 17 section; take it from there verbatim.

Then **17i, the exit**: every item verified in a running browser on both
installed maps. 17a-17f were verified that way as they landed (Third Age
Reforged throughout, and the marker layer's fort and watchtower path is the one
thing only DaC can exercise - it has 105 and 295 of them, Reforged has none, so
open DaC's map once with Markers on before calling 17 done).

After 17 the plan is written and needs no decisions: the audit's forty open
items were classified on 2026-09-05 (20 Now, 7 Next, 13 Later, none skipped) and
ROADMAP.md's Backlog turns that into fourteen sessions - Phases 18-21 as
**3.1.0**, Phases 22-24 as **3.2.0**, the Later set unphased. Its "whole plan on
one screen" table is the index.

**Cutting V3.0.0** is still outstanding and unscheduled. Phase 17 fixes bugs in
unreleased code, so it folds into 3.0.0 on either side of the cut.

Run `python tools/upstream_sync.py sync` first, as before every sub-phase.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 17 - Campaign map correction pass | **6 of 8 done** | 17a, 17b, 17c, 17d, 17e and 17f landed 2026-09-06 in four commits. 17g (capitalise the menu hints) and 17h (the credits, rewritten) are left, and then 17i's exit pass. |
| 16 - Campaign Map Editor (V3.0.0) | **done** | 16a-16k all landed 2026-09-03 to 2026-09-05: `campmap`, `maptga`, `mapvocab`, `campstrat`, `campaint`, `mapcheck`, `mapquery`, `stratedit`, `stratchar`, `stratcamp`, `winconds`, `cas`, and their seven web modules. Feature-complete and **not yet released**. Write-ups in ROADMAP_ARCHIVE.md, session detail in STATE_ARCHIVE.md. |
| 18-21 - the Now set (3.1.0) | **scoped** | Eight sessions closing the twenty items marked Now. 18 is the five campaign files nothing could edit, 19 is the names nothing could follow, 20 is the map screen's second pass, 21 is two screens over data we already hold. Fifteen of the twenty are S-sized, five are M and none is L. |
| 22-24 - the Next set (3.2.0) | **scoped** | Five sessions closing the seven Next items: placing forts, watchtowers and resources on the map (the largest single hole - 105, 295 and 1,131 of them read on DaC and nothing writes any), the textured terrain render, and delete-a-region / create-a-campaign. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. **Renumbered from V3.1/V3.2/V3.3 on 2026-09-05**; the manifest's `notes` were updated to match. |
| 0-15j | done | shipped through v2.1.11. Exit criteria and write-ups in ROADMAP_ARCHIVE.md. |

## In-progress detail
**Clean, mid-phase.** Six of Phase 17's eight items are committed and the
working tree is clean at `e330b00`. Nothing is half-written; 17g and 17h have
not been started.

What landed, and the number that proves each one:

- **17a** - `campmap` is in `modfiles.MODULES` with its fourteen files in
  `KNOWN`, the ten layers carrying the same `required` flags `campmap.LAYERS`
  gives them. Both installed mods report the Campaign Map card ready; a mod with
  no `world/maps/base` reports it blocked and names the seven files.
  `test_web_modules` now asserts every non-`sub` entry in `MODES` has a
  `MODULES` entry, which is the class of bug rather than the instance.
- **17b** - the hover trail was fractional devicePixelRatio: a dirty rectangle
  in CSS pixels lands half way through a device pixel at 150% Windows scaling,
  and the antialiased clip keeps half the frame before it. Measured by diffing a
  dirty-rect frame against a full repaint: **1,330 residue pixels over two
  pointer sweeps, and 0 after** the rectangle is snapped outwards to whole
  device pixels.
- **17c** - 199 of Reforged's 200 settlements and all 65 of its ports answered
  nothing when clicked, because a marker pixel is black or white and belongs to
  no region by colour. The marker now answers with the region that owns it, out
  of the manifest's own pairing. All 200 region anchors already resolved and
  still do; the one 2-tile province (`Edhellond_Province`) is reachable through
  Query's Go rather than by clicking.
- **17d** - the markers layer, `web/js/campmark.js` (`cmk` prefix, new),
  `campstrat.markers` and `mapquery.marker_view` behind
  `GET /api/map/markers`. 855 markers on Reforged in ~110 KB, 197 tiles carrying
  two. Off by default. Full-map frame: 0.5 ms layer off, 1.7 ms with
  settlements and characters, 2.2 ms with the 413 resources as well.
- **17e** - the hover tooltip, answered in the browser off `_vocab_view` in the
  manifest (2.9 KB: ground types, features and this mod's climates). 0.65 ms per
  tile change, 0.17 ms per pointer event inside one tile, all eight aligned
  layers named. ⓘ Names or `T` turns it off.
- **17f** - one faction screen, two files, two saves. Minor Files' Factions tab
  routes to it, and falls back to the old `factions` mode for a mod with no map.

V3.0.0 is feature-complete but **uncut** - the version in
`unittransfer/__init__.py` is still 2.1.11 and there is no
`merge/RELEASE_3_0_0.md`. Phase 17 is UI work on top of it, so it can land
before the release or after it; if it lands first, the release note covers both.

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
Reference tool reviewed SHA **ac503ac** (2026-09-03), 27 commits and 31 files on
from `e6e6982`. The write-up is the newest entry in `merge/SYNC_LOG.md`, and the
detail from that sync (what `factionBlockOps.js` taught 16b, the five `phases`
lists written as numbers that crashed `sync --accept`, the phase renumbering)
is in `STATE_ARCHIVE.md`.

**Two days old at the time of writing, and every sub-phase it was run for is
finished.** Run `python tools/upstream_sync.py sync` before Phase 17 anyway:
Phase 17 ports `StratOverlay.jsx` and `MapPixelTooltip.jsx`, which are files in
`src/components/map/`, and that is where he is actively working.

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
