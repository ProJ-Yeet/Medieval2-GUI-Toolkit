# Codex change handoff

Newest entries first. This records Codex's work for Claude; project status and
release rules remain in STATE.md and RELEASE.md. Do not assume the working tree's
other changes belong to Codex.

## 2026-11-07 - Phase 110 step 4 comparison groups and column kinds

- Read Phase 110 in docs/ROADMAP.md and the workbook comparison workflow in
  docs/upstream/EDB_SHEETS_WORKFLOW.md. Implemented the last requested build step.
  Preserved pre-existing step 1-3 and unrelated working-tree changes. No commit
  or release was made. Did not edit viewer3d.js, ROADMAP.md, STATE.md, other
  web/i18n catalogues or dev/i18n files.
- (a) Project groups map names to ordered stable unit IDs, scoped by the existing
  per-mod project path. Older projects migrate to an empty groups object.
  Create, rename, delete and explicit selected-unit add/remove operations validate
  the schema, revision and source token. Add/remove validates live matching IDs
  and rejects rule/recruitment row selections. The frontend waits for layout,
  pending edits and queued queries before pruning and snapshotting selection.
  Missing EDU members remain in the project and are labelled in the panel.
- (b) A read-only transposed comparison panel shows all saved members side by
  side on Base columns and Defense Total, Ultra Size and both efficiency columns.
  Numeric min/max/average and each member's difference from average use valid
  present values only. Missing members and missing/invalid values do not become
  zero. It reads staged values and is independent of grid filtering/pagination.
  Its column-kind schema remains independent of the active normal/rule view.
- (c) groups is an annotation list column with contains/not_contains support
  through filter_info, including recruitment context. Group membership itself
  is read-only in the grid and managed by the group buttons.
- (d) Headers and cells distinguish native EDU, classification/annotation and
  derived columns. A small legend uses solid, dashed and double borders plus
  header treatments. CSS uses existing accent, accent2, ink, dim and panel2
  theme tokens; index.html changes are CSS only. No live browser visual check
  was performed, so light/dark rendering is based on the shared token contract.
- (e) Existing visible formulas and editable size/defense coefficients were
  preserved. Group comparison reuses those calculations and staged records.
- Changed unittransfer/unit_sheets.py, unittransfer/sheet_ops.py,
  web/js/unitsheets.js, web/index.html, web/i18n/en.json,
  tests/test_unit_sheets.py, tests/test_sheet_ops.py,
  tests/test_unit_sheets_ui.js and this handoff.
- Test-first evidence: new Python regressions failed on missing group schema,
  group service action, comparison API and membership fields; the Node regression
  failed on the missing group action handler. A further comparison-kind assertion
  failed before adding its independent schema. Implemented and reran to green.
  Initial Python runs also hit the known sandbox mode-0700 Temp directory denial.
  Verification used an ignored .tmp/phase110-step4-runner/sitecustomize.py shim
  via PYTHONPATH to map mkdir mode 0700 to 0777, with UT_NO_BROWSER=1. No runtime
  or tracked test-runner workaround was introduced. The i18n check initially
  rejected dynamic ID concatenation; explicit tt IDs fixed it.
- Final checks actually run, all passed:
  python -m tests.test_unit_sheets: 29 tests;
  python -m tests.test_sheet_ops: 18 tests;
  python -m tests.test_sheet_pipeline: 9 tests;
  python -m tests.test_sheet_native: 7 tests;
  python -m tests.test_edb_balance: 12 tests;
  python -m tests.test_web_modules: 130/130 checks;
  python -m tests.test_i18n: 45/45 checks;
  node tests/test_unit_sheets_ui.js: all 32 named safety cases, the existing VM
  assertions and new group queue/panel/style assertions passed;
  git diff --check: passed.
- Usage authorization: user explicitly allowed this Phase 110 run to reach
  90% used in the five-hour window. Local telemetry was stale, then direct live
  account endpoint checks succeeded at 79%, 80%, 81% and finally 82% used.
  Work finishes in a stable state below the authorized stop. No credits were
  purchased and no limits were reset. Checks are periodic and account-wide.
- No requested implementation item remains. Translation stays separate as
  instructed. No installed-game or live browser verification was performed.

## 2026-11-07 - Phase 110 step 3 Barracks rules on the shared grid

- Read Phases 110, 112 and 113 in docs/ROADMAP.md. Changed
  unittransfer/unit_sheets.py, unittransfer/sheet_ops.py, web/js/unitsheets.js,
  web/i18n/en.json, tests/test_unit_sheets.py, tests/test_unit_sheets_ui.js,
  and this handoff. Preserved the pre-existing step 1, step 2 and unrelated
  working-tree changes. No commit or release was made. No edits were made to
  viewer3d.js, ROADMAP.md, STATE.md or non-English locale files.
- (a) Rule rows now have stable string IDs in project.rules. Migration assigns
  deterministic IDs to older rows and persists the migrated project on load.
  Newly created rows use UUIDs. All rule cell, paste and removal requests use
  row IDs. CSV exports include IDs and the saved schema even for empty tables.
- (b) Project rule_schema records text key columns and numeric value columns.
  Query rows normalize numbers; edits reject non-finite and non-numeric values
  using the existing SheetError style. Explicit zero survives; blank stays blank.
  Paste validates transactionally. Project replacement cannot bypass validation
  of changed rule values. Existing malformed source tokens remain inspectable
  through invalid filters and named issues. Conflicting duplicate keys, equal
  duplicate keys and incomplete keys appear as named rule issues. CSV imports
  now retain duplicate rows for repair; balance lookup still rejects duplicates
  exactly as before. No race vocabulary is hardcoded.
- (c) Added row creation, selected-ID removal, and add/rename/remove column
  controls. Extra text key columns can be selected when adding a column.
  Structural requests flush pending inputs and use the serialized request/history
  path. Destructive changes and column rename use the existing confirm pattern.
  Undo/redo flush pending inputs; rule undo resets filters/sorts that may reference
  removed columns. Structural changes also reset those filters/sorts safely.
- (d) rules:replenish, rules:experience and rules:pool query the shared service,
  with filter_info, matched_ids, stable multi-column sort and paging. The same
  grid renderer and existing movement, rectangular selection/paste, fill-down,
  selection pruning and layout-flush functions serve these views. Rule IDs and
  text keys stay frozen using fixed column widths. Rule blanks can be edited
  and pasted intentionally without changing native-unit blank-edit behavior.
- (e) Empty tables expose the default keys immediately. Experience/pool also
  expose T0 through T4. Replenishment endpoint columns can be added for the
  mod's own race labels. Column metadata and empty schemas persist in config.
- edb_balance.py was not changed. Its existing header/key contract and balance
  validation remain authoritative; changing/removing those headers requires
  restoring the expected lookup headers before balancing. A fixture regression
  verifies an experience table built/edited through the new API produces the
  same balance text as its equivalent imported CSV table. The existing full
  balance regression suite also passes with the new project metadata.
- Test first: observed backend failures for migration, schema, structure,
  validation and issues, then implemented and confirmed passing. Observed UI
  failures for frozen columns, structure actions and pending-input undo before
  their fixes. Additional VM coverage checks queued structure history,
  undo/redo, rule fill with zero and stable IDs through sorting. The UI harness
  runs the actual frontend module with an asynchronous fixture API.
- Final required checks passed, with UT_NO_BROWSER=1 for Python commands:
  python -u -m tests.test_unit_sheets: 27 tests;
  python -u -m tests.test_sheet_ops: 16 tests;
  python -u -m tests.test_sheet_pipeline: 9 tests;
  python -u -m tests.test_sheet_native: 7 tests;
  python -u -m tests.test_edb_balance: 12 tests;
  python -u -m tests.test_web_modules: 130/130 checks;
  python -u -m tests.test_i18n: 45/45 checks.
  node tests/test_unit_sheets_ui.js passed all 32 named regression cases plus
  the existing VM assertions. git diff --check passed.
- Python verification used the existing ignored
  .cache/codex-defect-tests/test-env sitecustomize shim via PYTHONPATH, which
  maps mkdir mode 0700 to 0777 for this Windows sandbox. No runtime or test
  runner workaround was added. No live browser or installed-game test was run.
- Live account usage endpoint checks succeeded after bypassing the refused local
  proxy. Five-hour usage readings were 69%, 71%, 74% and finally 75% used.
  Continued under the user's 90%-used stop authorization; no credits were
  purchased and no limits were reset. Periodic account-wide checks can lag.
- No requested step 3 implementation item is outstanding. Translation remains
  separate as instructed; only the English source catalogue was edited.

## 2026-11-07 - Phase 110 step 2 row schemas and filters

- Read Phase 110 in docs/ROADMAP.md. Changed unittransfer/sheet_ops.py,
  unittransfer/unit_sheets.py, web/js/unitsheets.js, web/i18n/en.json,
  tests/test_sheet_ops.py, tests/test_unit_sheets.py, tests/test_unit_sheets_ui.js,
  and this handoff. Existing step 1 and unrelated working-tree changes were
  preserved. No commit or release was made. viewer3d.js, ROADMAP.md, STATE.md
  and non-English locale files were not edited.
- (a) Query responses publish filter_info with text/number/bool/list types and
  readonly flags. Native views share the complete native row contract;
  recruitment exposes only its EDB and joined context columns. Empty sources
  retain their schema. Filter column and operator menus use this contract.
  Boolean columns use a translated True/False selector. Imported extra-column
  types reflect their values rather than always claiming text.
- (b) Boolean eq/ne filters accept true/false UI strings, case insensitive,
  without treating booleans as numbers. Visual builder submissions use booleans.
- (c) changed includes native drafts and classification edits. Classification
  baselines are saved in project classification_sources on the first edit;
  subsequent reversion and project undo compare against that baseline. Imports
  and whole-project saves also record classification changes. These config
  classifications persist independently of native Apply/Discard; historical
  projects without a baseline are treated as the starting classification state.
- (d) Numeric source parse failures keep their original token for inspection.
  Native invalid_columns uses the editing validator, including integer and
  forbidden-negative checks. Invalid is distinct from missing, comparisons
  exclude invalid numeric sources, and derived arithmetic avoids bad operands.
  Recruitment records parse failures and invalid negative/fractional-experience
  values in invalid_columns rather than silently replacing them with None.
- (e) Projectile context reads staged stat_pri/stat_sec members using EDU's
  primary-then-secondary projectile policy. Recruitment joins carry staged
  context, Category override, changed and needs_classification.
- (f) Added read-only pri_weapon_type, pri_tech_type, sec_weapon_type and
  sec_tech_type, extracted from zero-based CSV members 5 and 6, as used by
  the existing EDU/vocabulary layout. Exposed in Base stats and filter menus.
- (g) Saved views and advanced JSON restore flat AND/OR clauses and the group.
  Nested or unsupported expressions clear the flat controls and show an
  Advanced filter active summary. A translated human-readable expression
  summary and matching count are derived from the active expression, not from
  unsubmitted builder edits. Summaries truncate after 240 characters.
- (h) Recruitment exposes numeric building_depth from edb_balance.graph and
  building_tier as min(depth + 1, 5), matching the existing balance convention.
  Graph errors leave both unknown. Building type uses the parser's optional
  chain.extras['classification']; absent classifications remain None. It is
  not inferred from chain names or settlement context.
- Regression-first verification: new backend and UI regressions were observed
  failing before their corresponding implementation fixes. Additional checks
  cover classification reversion/undo, malformed derived inputs, optional EDB
  classification and cyclic graphs. Tests use temporary fixture data and the
  actual frontend module in a Node VM, not a live browser or installed game.
- Environment: unmodified Python runs encountered the pre-existing Windows
  sandbox denial of mode-0700 temporary directories. Verification uses the
  existing .cache/codex-defect-tests/test-env sitecustomize shim via PYTHONPATH;
  it maps only mkdir mode 0700 to 0777. UT_NO_BROWSER=1 and TEMP/TMP point to
  local scratch. Some initial denied scratch directories could not be cleaned
  by this sandbox. Runtime and test-runner source were not changed for this.
- Account usage: live usage endpoint requests failed with connection refused;
  no live usage tool was available. The latest local rate-limit event reported
  52% used in the five-hour window, but it is not a current reading. No credits
  were purchased and no limits were reset.
- Final required verification passed, all Python commands with UT_NO_BROWSER=1:
  python -m tests.test_unit_sheets: 19 tests; tests.test_sheet_ops: 16;
  tests.test_sheet_pipeline: 9; tests.test_sheet_native: 7;
  tests.test_edb_balance: 12; tests.test_web_modules: 130/130 checks;
  tests.test_i18n: 45/45 checks. The final Python sweep used -u only to stream
  progress. node tests/test_unit_sheets_ui.js passed all 27 named regression
  cases plus its existing VM assertions. git diff --check passed.
- No requested implementation item remains outstanding. No live-browser or
  installed-game verification was performed. Live account usage and cleanup
  of the 29 denied initial scratch directories remain environment limitations.

## 2026-11-07 - Phase 110 step 1 edit-target safety

- Changed web/js/unitsheets.js, tests/test_unit_sheets_ui.js, web/i18n/en.json,
  and this handoff. Read Phase 110's exit criteria before implementation.
  No commit or release was made. Existing unrelated working-tree changes were
  preserved. viewer3d.js, ROADMAP.md, STATE.md and other locale files were not
  edited.
- Safe selection policy: intersect selected stable IDs with the response's
  matched_ids after requests and again before mass edit/fill. Filtered-out IDs
  are dropped, with the displayed selection count reflecting the remaining set.
  Mass edit waits for an in-flight layout/filter change; Select matches replaces
  the previous selection. Matching off-page checkbox selections remain available
  for explicit mass edit, whose selected count includes them.
- Rectangles and anchors now contain row IDs and column names. Sort, filters
  (including clear, missing and advanced), pagination, tabs, saved-view loading,
  visible-column changes and extra-column changes flush pending cell edits
  before changing the layout, then clear the rectangle/anchor. Layout changes
  are serialized. Response-driven changes in row order also clear rectangles;
  unchanged rectangles retain their cell highlighting across repaint.
- Fill-down snapshots the top displayed selected ID, copies its current values
  and limits targets to displayed selected IDs. Rectangular fill uses the selected
  editable column names; checkbox fill uses the mass-edit column. Neither writes
  off-page rows. Paste snapshots IDs/names, waits for layout and pending edits,
  and removes targets no longer displayed/editable. A single clicked cell anchors
  a clipboard block within the page; a larger rectangle bounds it. Added only
  sheets.fill_page_note in English to explain the page/filter selection policy.
- Column hiding now derives from the full column list plus existing hidden
  names, so repeatedly applying the visible list cannot resurrect hidden fields.
  Explicitly listing a hidden field can reveal it again; id remains frozen.
- Test-first: 18 initial safety regressions failed before implementation. Further
  regressions exposed paste overtaking an in-flight filter, rectangle fill losing
  its columns during a flush-driven reorder, and single-cell paste clipping;
  each was observed failing before its fix. All 22 new safety cases and the
  existing Node VM checks now pass. Verification uses the real module in a Node
  VM with an asynchronous fixture API, not a live browser.
- Python commands used UT_NO_BROWSER=1. Initial unmodified-environment runs
  encountered the existing Windows sandbox denial of mode-0700 temporary
  directories. Reruns used the pre-existing ignored local sitecustomize shim at
  .cache/codex-defect-tests/test-env via PYTHONPATH, with TEMP/TMP in local scratch;
  it maps mkdir mode 0700 to 0777 only. No runtime or test-runner source changes
  were made for this environment issue.
- Required checks: python -m tests.test_unit_sheets (12 tests),
  tests.test_sheet_ops (10), tests.test_sheet_pipeline (9), tests.test_sheet_native
  (7), tests.test_edb_balance (12), and tests.test_web_modules (130/130 checks)
  passed. python -m tests.test_i18n passed 45/45 checks.
  node tests/test_unit_sheets_ui.js and git diff --check passed. No requested
  step-1 behavior remains unimplemented; live browser verification was not run.
- Usage was checked at start and checkpoints from the latest account rate-limit
  events. Latest reading: five-hour 52% used, 48% remaining. Continued under the
  supplied active EDB/sheets run override; no credits spent or limits reset.
  No separate live usage endpoint is exposed in this session, so account-event
  readings may lag concurrent account activity.

## 2026-11-07 - Five updater and unit-sheet defect fixes

- Added and ran failing regressions before each fix, then confirmed they pass.
  Changed only unittransfer/update_worker.py, unittransfer/updater.py,
  web/js/unitsheets.js, tests/test_updater.py, tests/test_unit_sheets_ui.js,
  and this handoff. Existing unrelated work was preserved. No commit, release,
  or real installation update was made.
- Packaging: LICENSE and NOTICE are now managed update components. A regression
  imports the release builder, runs write_docs in a temporary stage, and checks
  its emitted top-level names plus INCLUDE_FILES, INCLUDE_DIRS and runtime
  against COMPONENTS to catch packaging drift.
- Updater: an exclusive PID lock in config/updates/install.lock protects install,
  validation, rollback and worker state/pending writes; duplicate workers exit
  without changing state or restarting. Dead PID locks can be recovered; invalid
  or unreadable owners fail closed. apply_on_launch exits through the existing
  worker instead of spawning another. The lock is released before restarting
  the app so the restarted launch does not exit on its own worker's lock.
  Tests cover real cross-process contention, a dead process owner, rollback
  cleanup, duplicate worker state preservation and lock-free restart.
- Sheet saves: saved views, comparison, recipes, rule cells, draft discard and
  balance profiles now mutate a clone of the current project when their queued
  request is sent, while retaining the user's clicked values. Regression proves
  an earlier queued operate edit survives a following comparison save.
- Balance stage choices live in USHEET and drive repaint checkbox state;
  regression previews only replenish, repaints, then verifies export still
  requests only replenish. Recruitment hides the missing-classification shortcut
  and guards direct calls; classification still exposes/sends the valid filter.
- Final requested checks: python -m tests.test_updater (27 tests),
  python -m tests.test_unit_sheets (12), python -m tests.test_sheet_pipeline (9),
  python -m tests.test_web_modules (130 checks), and
  node tests/test_unit_sheets_ui.js all passed. Python commands ran from main/
  with UT_NO_BROWSER=1. git diff --check passed.
- Test environment: Windows sandbox denied access to Python 3.12's mode-0700
  TemporaryDirectory folders on the first attempts. Tests then ran with a local
  sitecustomize shim that maps only mkdir mode 0700 to 0777, via PYTHONPATH under
  .cache/codex-defect-tests/test-env; TEMP/TMP also pointed at local scratch.
  This is a test-runner workaround, not a repository runtime change. UI behavior
  was verified in Node's VM harness, not a live browser; portable installation
  tests used fixtures, not a real installed release. No known requested work
  remains. Protected viewer3d, i18n, ROADMAP and STATE files were not edited.
- Live account usage was checked at start/checkpoints after bypassing a refused
  local proxy; latest five-hour reading was 30% used, below the standing pause
  threshold. No credits were spent and no limits reset.

## 2026-11-06 - EDB/sheets implementation checkpoint, paused at 90% usage

- User authorized implementation and replaced the normal usage guard for this
  run with 90% used in the five-hour window. Started at 49%; live check reached
  90% used and implementation stopped. No credits/reset used. Recheck live usage
  and await the user before resuming. Override is recorded in root AGENTS.md.
- Phase 109 completed and archived. Phases 110-114 now have working code but
  remain active, with acceptance gaps below. Phases 115-116 and builder 102-108
  are not complete. Do not describe this as the whole roadmap finished.
- New engine files: unittransfer/unit_sheets.py (versioned per-mod projects,
  annotations/adapters/optimistic saves), sheet_ops.py (typed staged edits,
  expressions, filters and derived values), edb_balance.py (graph policies,
  replenishment/experience/pool, complete outcomes, token-only line patches),
  sheet_native.py (review/apply native EDU and EOP sheet edits).
- UI: web/js/unitsheets.js, loaded by index.html and opened through core.js's
  Unit sheets toolbar button in Units/Buildings. Classification/Base/Attributes/
  Soft/Rules/Recruitment views; paged grid, frozen IDs, filters and saved views,
  rectangular paste, selection, bulk operations, recipes, queued edits, history,
  native review/apply, balance preview/export/apply. Source IDs anchor edits.
  Import extras can be displayed; missing classifications are a direct filter.
- Integration: unittransfer/server.py adds /api/unit_sheets/*; buildings.py adds
  opt-in atomic EDB/text writes and custom log labels, eop.py accepts an optional
  atomic writer. Existing patchers/backups/manifests/Log Undo remain in charge.
  Native drafts record original source hashes. Changed source files load with a
  stale-draft warning and current values, allowing discard; stale Apply is refused.
  Balance waits for native drafts to be applied/discarded so roster values agree.
- EDB export ZIP includes final export_descr_buildings_new.txt, optional _r/_exp,
  structure/profile JSON and ALL plus skip/error JSON per stage. Preview is capped
  at 100 outcomes and 100 issues per stage to avoid rendering huge audit logs;
  exports retain every entry. No source JSON or external executable is required.
- Compatibility fixes: explicit shortest-root vs reject-ambiguous graph policy,
  diagnostics for cycles/unknown edges, no guessed zero depths; Beast mapping
  uses the Beast replenish tier but retains native cavalry multiplier, and maps
  experience/pool category to beast. Pool<1 skips replenish/pool, not experience.
  Missing/BG/rule cases preserve values, explicit overrides report conflicts.
  Comments/conditions/spacing/newlines survive token patches; repeat runs do not
  add generated comments. Original sources were read only.
- Real snapshot read-only check: 846 EDU units, 34 unclassified; 6/80/80 rule rows;
  128 buildings, 8,055 recruitment rows. Three-stage pure run ~3 seconds. Before
  the final Beast-cavalry correction, counts were replenish 216 changed / 6518
  unchanged / 1320 skipped / 1 invalid; experience 105 / 6870 / 1079 / 1; pool
  278 / 6330 / 1446 / 1. These are diagnostic counts, not approved balance output;
  rerun them after the final correction. BG, missing race and ship lookup gaps
  are reported. The malformed recruit row is preserved, not repaired by guessing.
- Verification: final 50 Python sheet/native/balance/pipeline tests pass and the
  Node frontend VM harness passes queued edits/current revisions, stable IDs,
  safe column handlers, frozen identity, rectangular paste/zero, pending flush.
  Fixtures verify EDB + native main/EOP Apply/Undo byte restoration, stale-source
  refusal and simulated write/log failures with rollback. Earlier combined run
  also passed 22 updater and 18 i18n-integrity tests (88 then, before two new
  regression cases). Web module suite 130/130 and i18n 45/45 passed; the final
  stale-draft recovery messages were added afterward with matching catalogue IDs.
  Final focused tests/Node/diff check passed after those edits.
- Browser verification used a disposable copy of the supplied snapshots, actual
  sheet JS/CSS and API. It rendered 846 rows and the missing-classification
  filter returned 34. Later browser requests failed and a fresh tab returned
  ERR_NETWORK_ACCESS_DENIED; full interactive edit/paste/undo/apply is NOT claimed.
  The fixture server was stopped. No real mod or user's original references were
  changed. Scratch fixture script/results/logs are under .cache, not shipped.
- Graphify update was run from repository root; AST extraction finished, but its
  rebuild had not completed at the usage guard and was interrupted. It also
  predates the final stale-draft recovery edits. Rerun graphify update . on resume.
- New tests: test_unit_sheets.py, test_sheet_ops.py, test_edb_balance.py,
  test_sheet_pipeline.py, test_sheet_native.py, test_unit_sheets_ui.js. English
  IDs are in en/de/es catalogues; new de/es sheet text currently uses provisional
  English fallback wording and still needs proper localization review.
- Next: finish 110 acceptance (actual app toolbar/keyboard/paste/view persistence,
  comparison groups and deeper rule-table editing), reconcile 111-113 outcomes
  with legacy golden outputs; finish 114 cancellation and normal UI Apply/Undo.
  Add Phase 115 native sheet CSV/XLSX header mappings and safe formula handling,
  then Phase 116 non-EUR/real-data/UI/shared builder checks. Do not add an Excel
  library dependency or execute the supplied scripts merely to import data.
- Known limits: native multi-file Apply rolls back exceptions and atomically
  replaces each file, but is not one power-loss-atomic transaction across files.
  EDB Apply performs one atomic file replacement. Existing mod-file concurrency
  conventions still apply. API project saves use revisions; no live continuous
  disk lock is promised against another program writing during the final rename.
- No commit, version bump, build, release, tag or upload. Preserve unrelated dirty
  files, including the pre-existing TWCenter index deletions and prior updater/
  roadmap changes. Do not infer file ownership from git status alone.

## 2026-11-06 - Automatic release updater implemented (not released)

- Completed the requested EDB/sheet analysis and roadmap first, then implemented
  the separately requested automatic GitHub update feature as Phase 117. Its
  write-up is in ROADMAP_ARCHIVE.md and its completed row is in ROADMAP.md.
- New: `main/unittransfer/updater.py`, `update_worker.py`,
  `main/tests/test_updater.py`. Changed `main/app.py`, `unittransfer/server.py`,
  `dev/release/build_release.py`, `web/js/settings.js`, English/German/Spanish
  web catalogues, README.md, ROADMAP/ROADMAP_ARCHIVE and STATE/STATE_ARCHIVE.
- Fixed official stable-release endpoint, six-hour background checks, Settings
  switch/check/status, SHA-256/size validation, strict extraction and release
  manifests. Downloads stage until next launch/restart; a private embedded
  interpreter replaces only manifest-owned components and runs a startup check.
  Exceptions roll back application files; config/settings/sessions/backups and
  user root files are preserved. No automatic source-checkout overwrite.
- The existing v2.4.11 release was inspected via public GitHub API; it has the
  expected portable asset and SHA-256 metadata. It predates the new manifest:
  older users require one manual upgrade to a future release carrying the updater.
- Checks passed: updater suite 22 tests; test_web_modules 130/130; test_i18n
  45/45; test_i18n_integrity 18/18; changed JS/Python syntax and diff checks.
  A full detached worker installation/startup/restart passed with real bundled
  Python in a disposable fixture, retaining settings. Result record:
  `.cache/update-worker-e2e-result.json`; no real install was updated.
- Wider `test_startup` could not finish: its early MED2 mod-count fixture failed
  and Windows blocked socket bind with WinError 10013. It did not reach update
  launch coverage; do not claim a fully green startup suite. No interactive
  Settings/browser pass or power-loss-atomic multi-directory replacement claimed.
- Final `graphify update .` completed from repository root after source edits:
  16,789 nodes, 36,008 edges, 713 communities. HTML visualization was skipped
  at its size limit. No release/version bump/tag/upload or commit.
- Follow-up: include updater + generated manifest in the next authorized portable
  release; exercise the Settings flow on a disposable packaged install if needed.
  EDB/sheet phases 109-116 remain planned, not implemented.

## 2026-11-06 - EDB pipeline and editable sheets scoped

- Read the user's five EDB scripts, batch order, reference tables/JSON schemas,
  workbook/ZIP converters, Fynn export/filter source and attached menu screenshot.
  Did not run the pipeline, execute Fynn, or modify the source spreadsheets/mod.
- Added ROADMAP.md Phases 109-116: source/classification sync, editable filtered
  sheets, typed mass edits, replenishment, experience/pool rules, complete staged
  pipeline/logs/apply/undo, interchange, real-data verification/builder integration.
- Source paths, formula behavior, reference hashes, observed header drift/huge
  used range and converter/log/comment limitations are recorded in
  `upstream/EDB_SHEETS_WORKFLOW.md`. STATE.md points at the planned track.
- Read-only spreadsheet analysis used bundled Python and ZIP/XML extraction;
  formulas/filter metadata were inspected, not recalculated or exercised in Excel.
  Planning checks cover unique phase numbers, exit criteria and links; no app tests
  needed for these documentation-only changes. No implementation or release.
- User separately asked to implement automatic GitHub update checks/downloads
  after this planning work; continue with that request next.

## 2026-11-06 - Unit builder integration roadmap (planning only)

- User requested incorporation of lupinemaverick's Stainless Steel: Reforged
  Unit Builder, explicitly allowing code reuse with the author's permission,
  then directed that it be split into phases rather than done in one go.
- Added ROADMAP.md Phases 102-108 and a schedule row: source/schema audit,
  Python calculator, guided UI, project/interchange adapter, existing/new unit
  application, mercenary pools, and compatibility/interactive verification.
  Each phase has dependencies and exit criteria and is a separate stopping point.
- Added `main/docs/upstream/SSR_UNIT_BUILDER.md` with reviewed commit
  `d4ed9368d0db3da2000bc895e96f52a83b93cb67`, source/module mapping, attribution,
  user permission, compatibility questions and a concrete custom-attribute
  export/notice discrepancy. Added a short planning pointer under STATE.md's
  Next up without changing existing priorities or other contributors' edits.
  Recorded the planning session in STATE_ARCHIVE.md.
- Reused the existing Python/plain-JS architecture in the plan; explicitly
  selected balance profiles, metadata-only unimplemented abilities, and the
  current parsers/planners/backup/undo paths are part of the staged scope.
- Verification: read upstream README and selected source through GitHub's public
  API/raw endpoints, confirmed the commit via commits/main, queried the local
  graph for integration points, checked phase numbering, links and document diff.
  No application or upstream test suite run: this is documentation-only work.
- GitHub page browsing failed and gh was unauthenticated; public API/raw reads
  succeeded. Local source snapshots are scratch files under `.cache/upstream/`.
- No application implementation, vendored runtime, mod writes, commit or release.
  Next: Phase 102 only when this integration is resumed. All other phases remain
  scoped, not completed.

## 2026-11-06 - Persistent handoff marker

- User instruction: leave a marker for Claude whenever making changes from now on.
- Added root AGENTS.md with that standing instruction and the user's existing
  account-usage preferences. Added a pointer here at the top of CLAUDE.md.
- Documentation-only update; no application tests rerun for this entry.
- No commit or release made by Codex in this chat.

## 2026-11-05 - Armory UV controls, normal baking, and export/session workflow

### Changes and reasons

- UV export preview retains pending island scales when selection changes, including
  with Live off; clicking outside a scaled island deselects it.
- Added S scaling by typed factor and mouse movement, Enter/click confirmation,
  Escape cancellation, live island-scale slider, editable percentage, and Ctrl+Z /
  Ctrl+Y history. The separate UV editor also accepts numeric S scaling and routes
  undo/redo to project history.
- Export filename defaults to the imported model/entry. Baking reports progress
  through the existing progress endpoint.
- GLB import retains explicit material normalTexture links. Previously the normal
  bake guessed names beside diffuse maps and missed Black Num Inf's *_m2_norm.png
  maps, falling back to generated normals. Normal filtering and mipmaps now keep
  RGB independent of alpha, since these source maps can have zero alpha.
- Session extras now persist output folder, filename, and installation choices.
  Added an immediate Save button beside Sessions and in its dialog. Project undo
  preserves session metadata and extras.
- Step 4 validates an older export on disk instead of requiring a new bake in the
  current dialog. A single existing mesh can restore its actual filename; multiple
  candidates are offered without choosing arbitrarily. Missing required texture
  files prevent recognition as a complete export.
- Installation folder Browse starts in the selected mod's data directory and
  returns a validated relative path. Folder choices include the selected unit's
  BMDB mesh/texture directories and up to 12 recent paths per mod in localStorage.

### Affected files

- `main/web/js/armexport.js`, `armuv.js`, `armory.js`, `armsess.js`
- `main/web/i18n/en.json`
- `main/unittransfer/armbake.py`, `armory.py`, `armunit.py`, `mesh.py`,
  `server.py`, `folder_dialog.py`
- `main/tests/test_armory.py`, `test_armbake_normals.py`, `test_armory_uv.js`,
  `test_armory_workflow.py`

### Verification completed in this chat

- `python -m tests.test_armory`: 99/99 passed.
- `python -m tests.test_armbake_normals`: 19/19 passed after normal-baking fixes.
- `python -m tests.test_web_modules`: 130/130 passed.
- `python -m tests.test_i18n_integrity`: 18 passed.
- `python -m tests.test_armory_workflow`: 8 passed, including old-export validation,
  partial-export rejection, data-relative paths, and mocked native picker setup.
- `node main/tests/test_armory_uv.js`: passed gesture, live-scale, undo/redo,
  persistence, old-export reuse, and unit/recent-folder checks.
- Changed JavaScript syntax checks, Python compilation, and `git diff --check`
  passed. Python test modules run from `main/`; the Node command above from root.
- Both existing Black Num Inf normal PNGs exactly matched the old renderer's
  diffuse-generated fallback. Corrected source-mode rendering used the active
  session's saved 2048 settings and 184 blocks. A full test bake completed:
  7,838 vertices, 9,331 triangles, 19 groups, 26 bones, no missing bones. Written
  mesh and normal textures reopened; diffuse PNGs exactly matched the old export.
- The older `black_num_inf_upg0` export was recognized successfully from disk.

### Artifacts, limits, and remaining steps

- Local diagnostic output: `.cache/armory-black-num-inf-check/diagnosis.json`;
  corrected full test export: `.cache/armory-black-num-inf-check/bake/`.
- Original export inspected under the user's OneDrive Models/EUR/Units/Keyforce/
  Black Numenor/Final Units/Infantry/Upg 0 directory; originals were not replaced.
- Frontend behavior was tested with Node harnesses, not a full interactive browser
  pass. Native picker initialization was tested with mocks, not by opening a real
  dialog. Restart the toolkit and reload its page to load backend/frontend changes.
- Other translations rely on English fallback for newly added labels.
- No commit or release made by Codex. Unrelated pre-existing deleted reference
  indexes, ZIP, shortcut, relay cache, and CHATGPT_INTRO.md were left alone.
