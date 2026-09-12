# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-12 - **v2.3.2** is the latest 2.x and **beta 2026-09-12c**
the latest beta - after Phase 29, the strat model viewer, which took B4 with it
and cut as it landed on both lines_

## Next up
**Two blocks, set by the user on 2026-09-12 after rating 38 of 39 candidates:
the whole campaign map first, then the mercenaries.** Everything else is in
`ROADMAP.md`'s *Future roadmap*, rated and unscheduled, to be started when both
blocks are done. Fifteen sessions in all; **29 is done**, so fourteen are left
and two of those are subreleases.

**Block one, the campaign map** - ~~29~~, 28, 33, 30, 34, 35, 36, 37a, 37b,
31, 38.

**Start with Phase 28, the right menu as a tab strip.** It is second only
because 29 was a defect, and every later panel lands on it: Phase 32's screen
goes onto the right-hand column, and building it in the old sixteen-panel stack
is work done twice. **Then 33**, three separate five-star S items in one
session (T10, G2, G4), which is the cheapest five-star work on the list. The
rest of block one is in `ROADMAP.md`'s order table, and two of its placements
are deliberate rather than arbitrary: **30 before 34**, because declaring a
climate without its textures is the largest field of pink anybody will ever
produce here, and **35 before 32**, because it is the same two-way panel over a
file that is already fully parsed.

**Block two, the mercenaries** - 32a, 32b, 32c, then 39. The big one.
`mapquery.parse_mercenaries` keeps a pool's name, its regions and its unit names
and throws away every gate on the line, so 32a is a real record in a new
`mercpools.py` that becomes the one parser; 32b is the two directions and the
four joins, all against modules we already own; 32c is five `mapcheck` rules and
the one repair that has a safe answer. Already measured: DaC names 2 mercenaries
absent from its EDU, Third Age Reforged names 33, and `Mt-Gram_Province` is in
two pools in one campaign, which that file's own header forbids.

**The cut-as-it-lands rule of 2026-09-09 is live**, so each phase goes out as
it lands - which 29 did. 38 and 39 touch something outside the campaign map and
are the remaining subreleases on both lines; the other twelve are the beta
alone.

**Mylae's new work is blocked and is not a phase.** He describes an improved
settlement-position validation and coloured overlay exports; none of it is
pushed. `Machiavello-1441/m2tw-editor` is still at `2740b0b` (2026-09-08),
`main` is the only branch and the account has no second repository. Ask for the
files rather than scoping from the sentence.

## WHERE THINGS ARE - the tree moved on 2026-09-06
Only the two `.bat` files and `README.md` are at the top of the repository.
**Everything else is under `main/`, and `main/` is the code root** - what
`config.PROJECT_ROOT` resolves to, what a test's `parents[1]` is, and what every
path in this file and in the source is relative to. `main/dev/` never ships.

## THE TWO RELEASE LINES
Two lines off this one `master`, chosen by whether a change touches the campaign
map. **Not campaign-map** -> a **2.x subrelease with the map hidden**, uploaded
`--latest` (latest **v2.3.2**, 2026-09-12). **Campaign-map** -> the **beta
line**, uploaded as a **pre-release** (latest **beta 2026-09-12c**). A
**subrelease means both**: one job, both zips, same tree.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`, which `menuModes()` and `modeOffered()` are the only readers
of. It is a **release-time edit, not a state of `master`**: set it, bump the 2.x
number, build, upload, then put it straight back off in the next commit.
`master` carries the map ON, and `__version__` says `beta-2026-09-12c`
because the beta was the last thing cut.

Of the finished work, **21 and 29 belong to BOTH lines** (raw text is a menu
mode of its own, the faction audit also draws in the Factions mode, and 29's
`icons.png_bytes` is the unit editor's and the BMDB browser's route as well as
the viewer's) and **22a, 22b, 22c, 23a, 23b and 24 are map work**, beta only.
Of the fourteen sessions left, **two are subreleases**: 38, because
`descr_campaign_db.xml` is a data file and gets a mode of its own; and 39,
because the EDU half of the ceilings is the unit editor's. The other twelve are
the beta alone.

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>`: hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `HANDOFF.md`.

**Nothing is written and held any more.** `RELEASE_2_2_4.md` and
`RELEASE_BETA_2026_09_11B.md` are kept as the record of what was drafted;
neither version was ever cut and both were folded into `RELEASE_2_3_0.md` and
`RELEASE_BETA_2026_09_12.md` on 2026-09-12.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 29 + B4 - the strat model viewer | **done** | Closed 2026-09-12, committed, **released 2026-09-12** as v2.3.2 and beta 2026-09-12c. The scoping was wrong about the root and right about everything above it: the art is not in a `.pack`, it is loose beside the stub as `<name>.tga.dds`, and `cas.texture_path` took the zero-byte `.tga` because it existed. Fixed at all five levels. New: `cas._has_bytes`, `icons.ArtUnreadable`, `icons.fault`, `png_bytes(strict=)`, `/model_texture` 415, `factions.packs_beside`, `factions.no_file_note`, and in `viewer3d.js` `uCutout`, `v3Degenerate`, `v3AskWhy`, `v3TexFault`, `v3FaultRows`. `tests/test_stratart.py` (40). |
| 28, 30-39 - the rest of the 2026-09-12 review | **scoped** | Fourteen sessions in two blocks. **Block one, the campaign map:** 28 the right menu as a tab strip, 33 T10 + G2 + G4 in one session, 30 the pink as a choice, 34 add a climate zone, 35 rebels right in place, 36 D1 region colour, 37a T7 spawn export, 37b T3 FE zoom, 31 four river rules, 38 `descr_campaign_db.xml`. **Block two, the mercenaries:** 32a `mercpools.py` takes the format over from `mapquery.parse_mercenaries`, 32b the two directions with the four gates resolved, 32c five rules and one repair, 39 the engine ceilings. Write-ups and the order table in `ROADMAP.md`. |
| 24 - Make and unmake | done | Closed 2026-09-12, committed, **released 2026-09-12**. Closes G1, M15 and the roadmap. Deleting a province, with its land going whole to a neighbour it borders and its name coming out of every file 19b measured - and the campaign script listed, never written, for the reason a rename gives. Making a campaign, as a copy of one that works minus the compiled map, with its own header and its own menu keys. New: `unittransfer/regiondel.py` (`heirs`, `campaigns_reading`, `standing_on`, `plan`, `apply`, `view`), `unittransfer/campnew.py` (`sources`, `plan`, `apply`, `view`), `mapquery.drop_music_region`, `renames.mentions`, `campfiles.write_descriptions`, `GET /api/map/region_delete`, `POST /api/map/region_delete_plan\|_apply`, `GET /api/campnew`, `POST /api/campnew/plan\|apply`, `web/js/regiondel.js`, `web/js/campnew.js`. `tests/test_regiondel.py` (62), `tests/test_campnew.py` (52). |
| B2-B3 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export. B4 went out inside 29. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-21 | done | 16-20a published on the beta line; 20b onward committed and uncut. The 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |
| 16-23 | done | Every write-up is in `ROADMAP_ARCHIVE.md`. 16-20a published on the beta line; everything from 20b to 24 went out in the 2026-09-12 cut. |
## In-progress detail
**Clean.** Nothing is mid-flight. **All 103 suites were run one at a time
after 29 and 98 passed.** The five that did not are the four documented DaC
suites below, each on its documented number, plus `test_mapcheck`'s timing bar,
which failed at 1,505 and 1,491 ms inside the batch and passes idle at 821, 666
and 165 - exactly the behaviour that section describes. `test_campstrat` was
also re-run against a stashed tree to confirm its three failures are the mod
and not this phase; they are. `tests/test_stratart.py` is new (40) and covers
all five levels of 29 plus B4.

**The one-second bar in `test_mapcheck` has less headroom than it did.** 23a's
rule put it at about 630 ms on DaC and 23b's second season at about 740. Idle on
2026-09-12 it measures **659 ms on DaC and 329 on Reforged**; in the middle of a
102-suite batch with a graph rebuild running it measured **1,484 and 1,215** and
failed both checks. It is the load that moves it, not the rule - re-run it alone
and idle before believing a failure, and expect it to fail inside a full run.

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
  `cpinButton(what, fn, args)` is the whole of it; 22a's and 22b's forms and
  their three Place buttons use it.
- `campaint.map_campaigns` - **before writing anything to the base map** (B1).
  A write to `world/maps/base` reaches only the campaigns that do not ship
  their own copy.
- `unittransfer/factionaudit.py` - **before adding any check about a faction.**
  `Census` already counts every slot in every file; gap or note is measured on
  the installed mods, never copied from a reference.
- `Registry.map_for` and `campmap.layer_map` - **before a module draws a
  layer.** The engine reads a campaign's own copy of a map file where it ships
  one, and so does the screen; a texture built from the base map's ground layer
  is not Fellowship's.
- `unittransfer/mapterrain.py` - **before anything needs a layer's colours as
  one byte a tile.** `Vocabulary.texture` is the one place the engine's four
  texture rules are applied; `_index` is the exact colour-to-index pass, in
  Pillow's C and 16x quicker than a dictionary pass, with the slow one kept
  beside it as the reference.
- `Colouring.payload`'s `bands` - **before working out anything per group.**
  Which group each province is in, `-1` for none, absent for anything that is
  not a province. The colour cannot answer it and reading it off the colour was
  a real bug: a presence map's "none" group is painted the same grey a province
  in no group is.
- `tests/test_mapquery.py` section 3b - **the pattern for anything the browser
  draws and Python exports.** Both passes, over one map, in node. It found two
  faults that had been in the tree since 16g, neither of which reading the code
  had found.
- `unittransfer/renames.py`'s `REGION_SITES` and `mentions` - **before anything
  has to follow a province name anywhere.** The site list is the measured set of
  files a province is named in and `regiondel` walks it rather than keeping a
  second one; `mentions` is the whole-mod scan that separates the scripts (which
  are listed and never written) from everything else. Both are the reason a
  delete and a rename cannot disagree about where a name lives.
- `unittransfer/campnew.py` - **before anything writes a folder the engine
  reads.** What a copy of a campaign gets wrong on its own is three things and
  they are all in one place: the compiled `map.rwm`, the `campaign <name>`
  header, and 18a's menu keys being built from the folder name.
- `unittransfer/mapsnap.py` - before writing any rule about where something may
  stand. The search is there; hand it the rule and put `near` on the finding.
- `unittransfer/stratobj.py` - one writer for every one-line thing on the map.
- `unittransfer/rawtext.py` - `rtOpen(rel, line)` is how any screen offers
  "open this file as text"; a parser that meets a line it does not model points
  there rather than growing a special case.
- `unittransfer/icons.py`'s `fault` and `png_bytes(strict=)` - **before any
  screen shows a picture that might not be there.** Absent and unreadable are
  two answers now and collapsing them is what Phase 29 undid; absent stays
  blank and stays quiet, unreadable is a fault and only a caller that can say
  so asks for it.
- `cas.texture_path` - **before resolving any art path by name.** A mod's
  packer leaves the named `.tga` at zero bytes and the real DDS beside it as
  `<name>.tga.dds`, so "the file exists" is not "the file has a picture in
  it". 1,171 of the 1,174 zero-byte files on the installed mods are that.

## Upstream
Reference tool reviewed SHA **2740b0b**. `sync` was run on 2026-09-12 four
times - at the start of 23a, 23b, 24 and the review - and was up to date every
time. **Confirmed against the remote directly**: `git ls-remote` gives
`2740b0b` for both `HEAD` and `refs/heads/main`, there is no second branch, and
the account has no second repository, so the features Mylae describes are
genuinely unpushed rather than missed by the tool. `docs/upstream/PORT_MANIFEST.json` is authoritative: 310
files triaged, none untriaged; `src/pages/TextEditor.jsx` notes it done in 21.
`REFERENCE_GAPS.md` marks D6, D11 and M14 done and G2 half done; **D7, T1 and
T12 were Phase 23's and G1 and M15 were 24's, and all five are now done.**
Nothing in the audit is scheduled any more. Run `sync` before touching anything
that ports from a directory he has been working in.

## Decisions
- 2026-09-12: **A file that will not decode is not a file that is missing** -
  now true rather than scoped. `png_bytes` answered both with a 1x1
  transparent PNG, and that conflation is what let the strat model bug through
  four layers. Absent stays blank and stays quiet; present and unreadable is a
  fault, `strict=True` is how a caller asks to be told, and the blank served
  for one is no longer cached so replacing the file is enough to fix it.
- 2026-09-12: **The scoping said the art was packed and it is loose beside the
  stub.** Phase 29's own write-up blamed a `.pack`; the measurement says a
  mod's packer converts each `.tga` to `<name>.tga.dds` and truncates the
  original, and 1,171 of the 1,174 zero-byte files on the two installed mods
  are exactly that pair. `cas.texture_path` took the stub because it *existed*.
  A candidate list ordered by name alone cannot tell a file from a placeholder
  - it has to prefer one with bytes in it. **Reproduce before scoping**: four
  correct diagnoses above a wrong one still leave the bug in place.
- 2026-09-12: **Say what was measured, not what it is blamed on.** The
  temptation was to have the panel announce "this mod keeps its strat textures
  in a `.pack`", which is the sentence the scoping asked for and is not true.
  Nothing here reads a `.pack` index, so nothing here may claim what is inside
  one: `icons.fault` reports the size and the partner file it can see, and
  `factions.no_file_note` counts the archives it can list and says the file is
  not loose. An empty `packs` folder is not an archive - Third Age Reforged
  has one.
- 2026-09-12: **A cut-out rule belongs to the format it was measured on.**
  `if(base.a < 0.35) discard;` is what makes a plume a plume on a unit's
  `.mesh`. Applied to a `.cas` whose sheet came back degenerate it deletes the
  model, and the survivor is whichever mesh had no material at all. A shader
  constant shared between two decoders is a decision about both.
- 2026-09-12: **A delete is a rename to nothing.** 19b measured where a province
  is named - fifteen files in Divide and Conquer, twelve in Third Age Reforged -
  and G1 walks that list rather than one of its own, removing the name where a
  rename would substitute it. The two agree about the campaign script for the
  same reason: it is a grammar nothing here parses, so it is listed line by line
  and never written. A second list of "where a province is named" would have
  been a second list to keep right.
- 2026-09-12: **Land goes whole to one neighbour it touches, and the reason is
  16e's own rule.** Geomod says "usually an adjacent one" and does not say
  which. A tile-by-tile share-out between several neighbours is the obvious
  generalisation and cannot be proved to leave anybody in one piece; one
  adjacent heir can, because two contiguous areas that share an edge make one.
  Offering every neighbour ordered by shared border is the part that is better
  than the arbiter, not the splitting.
- 2026-09-12: **Placed by tile means not orphaned.** Geomod's manual warns that
  "resources, forts and characters will remain" when a region goes, and that
  warning is half wrong: all three carry coordinates, the coordinates do not
  move, and what changes is whose province they stand in. The panel counts them
  and names the heir. The one thing genuinely filed under a province NAME is
  `descr_strat.txt`'s `region <name>` section, and that is the one thing moved.
  `mapsnap.nearest` was expected here by the brief and was not needed - a delete
  moves no coordinate, so no placement rule can be broken by one.
- 2026-09-12: **A new campaign is a copy of one that runs.** The engine reads
  more than a dozen files out of a campaign folder and a missing one is a load
  failure with nothing on screen to explain it, so a template or a skeleton
  would be a way of shipping that failure. What a copy alone gets wrong is three
  things, all of them in `campnew.py`: the compiled `map.rwm` must not travel,
  the `campaign <name>` header must name the copy, and 18a's menu keys are built
  from the folder name so a copy inherits none of them.

Older decisions are pruned into `STATE_ARCHIVE.md` at the ten this file's
contract allows.
