# ROADMAP ARCHIVE - what is already built

**This file is history. Nothing here is work to do.** It holds the full write-up
of every phase the toolkit has finished, from the V2 kickoff through V3.0.0's
campaign map editor, kept because each entry records *what was measured* and
*why a rule is a rule* - the reasons a later session needs when it changes one
of these modules and cannot see why the obvious approach was not taken.

Live work lives in [ROADMAP.md](ROADMAP.md): the locked decisions, the phase
index, the map-format reference, and everything still to build. Read this file
only when you need the reasoning behind something that already ships.

Split out of `ROADMAP.md` on 2026-09-05, verbatim.

| Phases here | Where |
|---|---|
| 0-13 - V2 editors, from the nav rebrand to the EDU/Sounds audit | below |
| 14a-14j - the bug-fix and polish pass, and v2.0.1 | below |
| 15-15j - the 3D model viewer and everything on it, to v2.1.11 | below |
| 16a-16k - the campaign map editor, V3.0.0 | below |
| 17a-17i, 18a-18b, 19a-19b, 20a-20b - the correction pass and the Now set | below |
| B1 - the first item off a beta user: a new province in every campaign | below |
| 20c - settlement names on the map, and the pin that fills a coordinate | below |
| 21, 22a-22c - the two screens over data we hold, and placing things on the map | below |
| 23a-23b - the map drawn with the game's own ground textures, winter, and the tint | below |
| 24 - deleting a province, and making a campaign: the last of the roadmap | below |
| 29, with B4 - the strat model viewer, and a stub that beat the art beside it | below |
| 18-24 as planned, B2/B3 as reported, 28-43, 54 - the backlog of 2026-09-05 and the 2026-09-12 review, to Health | below, *Split out on 2026-09-23* |
| 44-53, 55-64, M18, and the upstream passes of 2026-09-13, -17 and -20 | below, *Split out on 2026-09-23* |

---

## Phase 0 - V2 kickoff ✅ (done 2026-08-13)

Burger-menu navigation (module registry in one `MODES` array), full rebrand to
Medieval 2 GUI Toolkit (UI, titles, README, launcher bats with an old-name
forwarder, release naming in `dev/release/build_release.py`), credits screen, this roadmap,
`STATE.md`.

## Phase 1 - TWCenter tutorial index ✅ (done 2026-08-13)

`dev/reference/twc_index.py` → `Reference/TWCenter/INDEX.md` + `INDEX.json`: 206
documents covering all 321 files, 25 tagged `needs-manual-read` (no text layer),
per-phase reading lists, idempotent (`--check`). Both INDEX files are committed
even though `Reference/` is ignored.

<details><summary>original plan</summary>

- **Goal:** Turn `Reference/TWCenter/` into a searchable index so any later
  phase can find the authoritative tutorial for a file format in seconds.
- **Preconditions:** none.
- **Files:** new `dev/reference/twc_index.py`; generated `Reference/TWCenter/INDEX.md`
  + `INDEX.json` (file → title, topic tags, game files covered, 1-line summary).
- **Effort:** M - one session. PDF text extraction (dev-only dependency, e.g.
  pypdf; not shipped in releases).
- **Exit criteria:** every file in the archive has an entry; entries are
  greppable by game filename (`descr_strat`, `export_descr_ancillaries`, …);
  5 spot-checked entries accurately reflect their PDF.
- **Risks:** scanned/image-only PDFs may defeat text extraction - tag those
  `needs-manual-read` rather than guessing.

</details>

## Phase 2 - Reference-tool tracking infra ✅ (done 2026-08-13)

1947 commits mirrored to `refs/upstream/editor/*`; all 298 files triaged in
`docs/upstream/PORT_MANIFEST.json` (124 port-concept, 86 skip, 68 out-of-scope, 20
audit, 0 untriaged); `dev/reference/upstream_sync.py status|triage|sync` verified against
replayed history; baseline in `docs/upstream/SYNC_LOG.md`.

<details><summary>original plan</summary>

- **Goal:** Make Mylae's release-less `main` branch safely consumable: full
  history mirrored in our repo, every file triaged, and a diff-driven sync tool
  for his future changes.
- **Preconditions:** none.
- **Files:** git remote + `refs/upstream/editor/*` fetch; `docs/upstream/PORT_MANIFEST.json`
  (per-file: disposition `port-concept | audit | skip | out-of-scope`, target
  phase, reviewed SHA); `dev/reference/upstream_sync.py`; `docs/upstream/SYNC_LOG.md`.
- **Effort:** S–M - one session (triage at directory granularity, file-level
  only for directories feeding V2 phases).
- **Exit criteria:** sync tool fetches, diffs `reviewed_sha..upstream/main`,
  buckets changes by disposition, flags "format knowledge may have changed" for
  `port-concept` files, appends to SYNC_LOG, bumps the SHA; manifest covers all
  ~298 files; run it clean once.
- **Risks:** his commit messages are all "File changes" - the tool must key on
  diffs only. Run the sync at the start of any phase that ports from a
  directory he's recently touched (he is actively rewriting `map/` right now).

</details>

## Phase 3 - Split the UI monolith ✅ (done 2026-08-13)

`web/index.html` 10 412 → 1 077 lines (shell + CSS + 14 `<script>` tags);
`web/js/*.js` holds the code, split by module, sharing one global scope with no
build step. Server gained `_web_asset` (path-contained) for `/js/*`. Guarded by
`tests/test_web_modules.py`: load order, every file loaded, no duplicate
top-level name (680 checked), each file parses, concatenation parses.

<details><summary>original plan</summary>

- **Goal:** Break `web/index.html` (10.4k lines) into per-module files served
  plainly by the Python server, so each later phase touches one file.
- **Preconditions:** none (do before Phase 4 lands its widget).
- **Files:** `web/index.html` (shell + shared CSS), new `web/js/core.js`
  (state, api, nav/MODES, modal, toast, filters), `web/js/<module>.js` × 6;
  `unittransfer/server.py` static serving (exists); `dev/release/build_release.py` include
  list check.
- **Effort:** M - one session; purely mechanical, no behaviour change.
- **Exit criteria:** all six modules smoke-tested working (transfer plan,
  editor open/save, BMDB audit, sounds stage, sprites list, building open);
  no build step; release build still packages the whole `web/`.
- **Risks:** script-order and shared-global coupling (the `setMode` hoisting
  collision found in Phase 0 is the warning). Keep load order explicit in the
  shell; grep for duplicate top-level names before landing.

</details>

## Phase 4 - Code View widget + line-map API ✅ (done 2026-08-13)

**4b ✅.** Two more kinds in the same registry - `edb` (one `building … { … }`
line) and `bmdb` (one modeldb entry) - and both editors adopted the widget with
no second parser anywhere. `buildings.block_spans/block_fields/render_block`,
`buildings.detail(…, bl=)` so the form can be rebuilt from text that isn't on
disk yet, `modeldb.parse_entry_text/entry_spans`, and hand-edited text reaching
disk verbatim via `part["raw_block"]` (EDB) and `ModelEdit.raw_entry` (BMDB).
`render`'s edits argument is now kind-shaped - whatever that editor's save
request already sends - which is what keeps pane and save on one road.

Two things the shape of these formats forced:
* **The buildings pane owns the parse from the moment it loads.** A capability
  row carries the line it sits on, and `/api/building` counts from the top of
  the EDB while the pane counts from the top of the block. One convention, or
  the first capability edit lands on the wrong line.
* **`repair` (`⟲ Fix lengths`), only on `bmdb`.** Every modeldb string is stored
  `<length> <text>`, so a retyped path desyncs the reader. The pane refuses such
  text, naming the line and the number it should be, and the button puts it
  right - explicitly, with the numbers changing on screen.

**4a ✅.** `unittransfer/codeview.py` (kind registry, `parse` /
`render` / `unit_document`, `CodeViewError`), `edu.block_spans`, three endpoints
(`GET /api/codeview`, `POST /api/codeview/parse|render`), `web/js/codeview.js`,
piloted on the Unit Editor's EDU tab behind a remembered `</> Code view` toggle.
`EditRequest.raw_block` carries a hand-edited block to disk verbatim, with field
overrides applying on top of it. Guarded by `tests/test_codeview.py` (59 checks,
no game install needed). Measured on a 1701-unit EDU: parse 3.7 ms, render
4.5 ms, initial load 6.7 ms - the 50 ms budget holds, so 4b can adopt freely.

<details><summary>original plan</summary>

- **Goal:** One reusable component giving every editor a side-by-side GUI ⇄ raw
  code view: hover a field → its line(s) highlight; edit either side → the
  other updates live.
- **Preconditions:** Phase 3.
- **Files:** `web/js/codeview.js`; `unittransfer/server.py` endpoints
  (`GET /api/codeview` → `{text, spans: field→[line ranges]}`,
  `POST /api/codeview/parse` → re-parsed fields for edited raw text);
  span-map support in `unittransfer/edu.py` first; tests
  `tests/test_codeview.py`.
- **Effort:** L - split: **4a** widget + API + pilot on the Unit Editor's EDU
  entry; **4b** adopt in Buildings and BMDB editors.
- **Exit criteria (4a):** in the Unit Editor, hovering any stat highlights its
  EDU line; typing in the raw pane updates the GUI fields within ~500 ms
  (debounced, server-parsed); GUI edits rewrite the raw pane; a raw edit that
  doesn't parse shows the error inline and never corrupts state; span maps
  round-trip in tests. **(4b):** same behaviour in Buildings + BMDB; no
  client-side parser exists.
- **Risks:** span maps must survive our serializers exactly (comment and
  whitespace preservation); parsing on every debounce means endpoints must stay
  <50 ms on DaC-sized files - measure in 4a before adopting widely.
- **Open question:** for binary-backed editors (BMDB is a text archive - fine;
  strings.bin decodes to text) the "raw" pane shows our canonical decoded text.
  *Answered in 4b:* the BMDB pane shows the archive's own bytes, and the length
  prefixes - the one part of that text nobody can maintain by hand - get an
  explicit repair button rather than a decoded surrogate format.

</details>

## Phase 5 - Home module ✅ (done 2026-08-13)

`unittransfer/modfiles.py` (17 known files → per-module verdict, encoding sniff,
campaign title read through the strings codec), `GET /api/mod_files?mod=`,
`web/js/home.js`, `MODES` entry. A launch lands on Home whatever module you were
in last; the remembered mode is offered as "last time you were in …" rather than
jumped into. Each card carries its own mod, so Home is the one screen with no mod
picker above it. Guarded by `tests/test_stringsbin.py`.

<details><summary>original plan</summary>

- **Goal:** Replace "pick a mode first" with a landing page: detected mods,
  module launcher, and a per-mod file-discovery report - the reference tool's
  upload flow, inverted onto our server-side registry.
- **Preconditions:** Phase 3 (module file layout); their `DataFolderPicker` /
  `Home.jsx` file lists consulted via Phase 2 manifest.
- **Files:** `web/js/home.js`, `MODES` entry, `unittransfer/server.py`
  (`/api/mod_files?mod=` - which known game files exist, size, encoding),
  `unittransfer/mod.py`.
- **Effort:** M - one session.
- **Exit criteria:** launching lands on Home; each mod shows a readiness matrix
  (file present / missing / unreadable per module, localised mod title); every
  module reachable from a mod card; burger menu unchanged.
- **Risks:** none serious; keep discovery read-only and cached.
  *Landed as:* a shallow report (stat + 4-byte encoding sniff, never a parse),
  cached per mod for the session and repainted card by card so one slow mod does
  not restart the others. "Localised mod title" has no real source in M2TW - the
  closest honest one is the campaign's own in-game name
  (`UI_NEW_GAME_IMPERIAL_CAMPAIGN`, then `IMPERIAL_CAMPAIGN_TITLE`), which reads
  through Phase 6's codec: "War of the Ring (Divide_and_Conquer_EUR)".

</details>

## Phase 6 - Strings editor ✅ (done 2026-08-13)

`unittransfer/stringsbin.py` (codec), `unittransfer/strings.py` (the mod-facing
module), `codeview` kind `strings`, `/api/strings` + `/api/strings/entries` +
`/api/strings/plan|apply`, `web/js/strings.js`. **All 81 `.strings.bin` files
shipped by the three installed mods decode and re-encode byte for byte**, which
is what established the format; `tests/test_stringsbin.py` is 58 checks and runs
that sweep whenever mods are present.

The format is NOT what the reference tool's `stringsBinCodec.jsx` says, and both
of its errors destroy files:
* **the entry count is `u32`, not `u16` + padding.** Agrees below 65 536 entries
  and silently reads half a file above it - Third Age's `names.txt` is already at
  20 757.
* **a trailing *tag index* follows the entries, not a single zero word.** It is
  the tags in the source `.txt`'s original order and can dwarf the entry list
  (DaC's `export_buildings`: 480 entries, 13 482 index strings, mostly stale
  vanilla tags). Writing a zero word there truncates two thirds of the file. It
  is carried through an edit verbatim and left empty when compiling from scratch
  - a state plenty of shipped files are already in.

Also confirmed by measurement rather than folklore: the four untagged archives
(`battle`, `shared`, `strat`, `tooltips` - style word 1) hold bare strings with
no index section at all; tags are code-point sorted in all 69 tagged files, so a
new tag is inserted in that order; and the game's own compiler folds continuation
lines, trims tabs and line breaks but **not** spaces, and reads `\n` as a line
break (3393 of 3395 entries reproduced against a `.bin` the game itself wrote).

`cleaner.refresh_strings_bin` now recompiles a cache from the `.txt` a job just
wrote instead of deleting it, falling back to deletion when there is nothing to
compile from. `Mod.loc` / `building_loc` / `faction_names` read through the codec
when the `.txt` is absent, so a mod that ships only compiled text still shows
real names.

<details><summary>original plan</summary>

- **Goal:** Read and write `.txt.strings.bin` natively (keys + UTF-16 values),
  ending the "delete the .bin and let the game rebuild it" workaround.
- **Preconditions:** Phases 3, 4 (ships with Code View from day one).
- **Files:** new `unittransfer/stringsbin.py` (codec, from the BinEditor v3.0
  format their `stringsBinCodec.jsx` cites; verify against TWCenter index),
  `tests/test_stringsbin.py`, `/api/strings/*` (list/entry/plan/apply with
  backup+undo), `web/js/strings.js`.
- **Effort:** M - one session.
- **Exit criteria:** decode→encode of untouched files is byte-identical for
  every `.strings.bin` in the test mods; edit/save/undo works; existing
  `cleaner.py` .bin-deletion path becomes unnecessary for edited files;
  localised-name lookups elsewhere can read through this codec.
- **Risks:** encoding corner cases (odd counts, empty values) - the
  byte-identical round-trip test is the gate.
  *Landed as:* the gate held. The ground truth was alpaca's converter
  (`Reference/TWCenter/--- TOOLS n RESOURCES ---/strings_bin_converter_0_7_2/`),
  which has the 32-bit count the JSX lacks, plus a sweep over the real files for
  everything alpaca's script also stops short of.
- **Open question, answered:** the "raw" pane for a binary-backed editor. A
  strings entry IS one `{tag}text` line of the `.txt` beside it, so the pane
  shows that - the format modders already write, not a decoded stand-in. Untagged
  archives get no pane, because that shape does not exist for them.

</details>

## Phase 7 - Trigger/condition core ✅ (done 2026-08-13)

`unittransfer/triggers.py` (grammar, splice editor, spans),
`dev/reference/trigger_vocab.py` → `unittransfer/data/trigger_vocab.json` (413
conditions, 217 events), `GET /api/triggers/vocab?mod=`, `web/js/triggerui.js`,
`tests/test_triggers.py` (49 checks). **All 4974 triggers / 20 013 conditions in
the six installed EDCT and EDA files parse with zero unknown constructs and the
files come back byte for byte.**

The vocabulary is generated, never written by hand, from the Docudemons
spreadsheet (`Reference/TWCenter/M2TW_Ultimate_Docudemons_5.3.xlsx`) plus a
measurement pass over every trigger file on the machine. The spreadsheet supplies
each condition's description and - the part that pays for itself - which data
types it **requires** and which each event **exports**; the mods supply the
argument *shape* of each term (`Trait` is `name op num`), because the spreadsheet
describes parameters in prose and 20 000 real clauses do not.

That pairing gives `triggers.check`: a condition whose required data type its
event does not export can never be true, and the trigger silently never fires -
invisible when reading the file. It found **2 real cases** in the installed mods
(`SettlementBuildingExists` under `PostBattle` and under `CharacterComesOfAge`).
Getting there needed two corrections to the source data: requirements can be
disjunctive (`Religion` accepts any one of six types) and the spreadsheet spells
two types more than one way - without both, the check cried wolf 104 times.

**Their `conditionDefs.jsx` is not ported** - see `docs/upstream/audit-trigger-vocab.md`.
Of its 78 conditions, 20 exist; of its 82 `WhenToTest` events, 41 exist, and the
misses are not typos but a whole invented `On` prefix (`OnCharacterTurnStart` for
the engine's `CharacterTurnStart`) plus plausible-sounding conditions the engine
has never had (`IsSpy`, `IsHeir`, `SettlementLevel`). A picker built from it
writes triggers that never fire.

`web/js/triggerui.js` is a component with a host contract, not a mode: its hosts
are Phase 8b and Phase 9, exactly as the dependency shape says. It draws one
typed box per token of a term's measured shape, fills `name` boxes from that
mod's own traits / ancillaries / factions / cultures / buildings, and shows the
never-fires warning live as the event changes. Its requirement test is checked
against the Python one under `node`.

<details><summary>original plan</summary>

- **Goal:** One Python grammar + one GUI builder for the `Trigger / WhenToTest /
  Condition / Affects` language shared by traits, ancillaries and (later) the
  script editor.
- **Preconditions:** Phase 3; their `shared/conditionDefs.jsx`,
  `TriggerEditor.jsx`, `WhenToTestSelect.jsx` as the vocabulary reference,
  TWCenter docs as ground truth.
- **Files:** new `unittransfer/triggers.py` + `tests/test_triggers.py`;
  `web/js/triggerui.js` (builder component: event picker, condition rows with
  typed operands, localised labels).
- **Effort:** S–M - one session.
- **Exit criteria:** parses every trigger in both test mods' EDCT + EDA files
  with zero unknown-construct warnings (unknowns are listed, not dropped);
  serializes back byte-identical; vocab served via API.
- **Risks:** condition vocabulary is huge and partly version-specific - store
  it as data (JSON) derived from their defs + TWCenter, not as code.
  *Landed as:* data, but derived from TWCenter and from the mods - their defs
  turned out to be too wrong to derive anything from. "Localised labels" has
  nothing to localise: condition and event names are engine identifiers with no
  text entry anywhere, so the labels are the identifiers, with the Docudemons
  description as the hint and this mod's own usage count beside each one.

</details>

## Phase 8 - Traits editor ✅ (done 2026-08-13)

**8b ✅.** `web/js/traits.js` + `MODES` entry, `GET /api/traits` + `/api/trait`,
`POST /api/traits/plan|apply`, and the traits half of `unittransfer/traits.py`
(`overview`, `detail`, `plan`, `apply`). **`web/js/triggerui.js` has its first
host**: the triggers whose `Affects` names the open trait are listed under it,
each one in the shared builder, and their edits ride in the same save.

A save can touch three things and does them as one job, because they fail
together: the trait block, the triggers hundreds of lines below it in the same
file, and the `export_VnVs.txt` keys its levels name. Backups and undo cover all
of them - `tests/test_traits.py` creates a trait, edits it, builds a trigger for
it in the GUI's shape, deletes it and undoes the lot against a scratch mod.

Four rulings the format forced on the UI:

* **A level is a key and the words the player reads, side by side.** Taken from
  their editor (`docs/upstream/audit-traits.md`) - the key is in the EDCT and the wording
  is in `export_VnVs.txt`, and sending someone to another module to write the
  words would be the tool getting in the way. A key the file has not got is
  created; one whose wording was retyped is rewritten in place, continuation
  lines and all, and the compiled archive is rebuilt in the same save.
* **Deleting a trait takes its triggers with it.** A trigger left `Affects`-ing a
  trait that no longer exists is the guide's "Trait not recognized". A trigger
  that fed *only* this trait is removed whole; one that also feeds others loses
  just that line, so their points survive. The preview says which.
* **Renaming a trait is refused everywhere except at creation** - the name is the
  key its own triggers, other traits' `AntiTraits`, the EDA and `descr_strat` all
  point at. Same ruling as a building line.
* **The form sends every box on save, so an unchanged value must not rewrite its
  line.** A list is compared as a list: `greek,  noldor` and `greek, noldor` are
  the same value, and 128 real traits are written the first way. All 1457 survive
  a full-form save unchanged.

**8a ✅.** `unittransfer/traits.py` - the definition half of
the EDCT, sitting on `triggers.split_lines` so both halves of the file count
lines from the same place. **All 1457 traits / 3021 levels in the three installed
EDCTs parse with zero unknown constructs and the files come back byte for byte**;
`tests/test_traits.py` is 88 checks. Code View kind `traits` registered (spans
per header line, per level, per level field and per `Effect`), with
`codeview.trait_document` and a rename refusal - the trait name is the key its
own triggers' `Affects` lines, other traits' `AntiTraits`, the EDA and
`descr_strat` all point at.

Three things the format forced, all from Squid's EDCT/EDA guide
(`Reference/TWCenter/[Modding] RTW  Guide for Traits and Ancillaries.pdf`) and
confirmed against the real files:

* **The header's line order is load-bearing.** `Characters` must be the line
  under `Trait`, and the optional lines after it have a fixed order. Get it wrong
  and the engine does not report a bad trait - it stops recognising every trait
  defined *after* it and crashes hundreds of lines away. So an added header line
  is inserted at its canonical position, never appended, and `check` reports a
  file that already has it wrong.
* **Absent is not empty.** `Hidden` is a whole line; an optional field edited to
  nothing deletes its line rather than writing a bare keyword. The four required
  lines (`Characters`; `Description` / `EffectsDescription` / `Threshold`) are
  refused when blanked, because the alternative is writing a file that stops the
  game loading.
* **`check` reads both halves at once.** A trait name is what thousands of
  trigger lines point at, so `check_file(tf, trigger_file)` catches an `Affects`
  naming a trait that does not exist. On the installed mods it found **14 real
  findings in 1457 traits**: DaC's `HeroAbility_GALADRIEL` is missing its `Trait`
  line and has been absorbed as a second level of `HeroAbilitySilvanElf` at the
  same threshold, so it can never appear; two DaC triggers write
  `Affects Trait SuppliedBySea …` and the points go nowhere; and 11 traits use a
  comma-separated `Characters` list, where only the first type ever works.

Localised names come from `data/text/export_VnVs.txt` (flat `{tag}text`, read
through Phase 6's codec when a mod ships only the compiled archive) - a trait has
no name of its own, so `traits.label` shows its first level's:
"Race: Decayed Man (Nazgul)".

- **Goal:** Full `export_descr_character_traits.txt` editor - traits, levels,
  effects, triggers - with localised names and Code View.
- **Preconditions:** Phases 4, 7 (and 6 for localised trait names).
- **Files:** **8a:** `unittransfer/traits.py` + tests (parse/serialize, spans).
  **8b:** `web/js/traits.js` + `MODES` entry + `/api/traits/*` plan/apply.
- **Effort:** L - parser and UI are a session each.
- **Exit criteria (8a):** ✅ round-trip byte-identical on both test mods; span
  maps for Code View. **(8b):** ✅ create/edit/delete a trait end-to-end with
  backup+undo; anti-traits and thresholds editable via GUI; their editor's
  field coverage matched or exceeded (`docs/upstream/audit-traits.md` - matched on
  fields, exceeded on checks, Code View, undo and the trigger half);
  `web/js/triggerui.js` gets its first host.
- **Risks:** EDCT files in big mods are enormous - list virtualisation matters
  (we already do this for 1700-entry dropdowns).

## Phase 9 - Ancillaries editor ✅ (done 2026-08-13)

`unittransfer/ancillaries.py`, `web/js/ancillaries.js`, `GET /api/ancillaries` +
`/api/ancillary`, `POST /api/ancillaries/plan|apply`, code view kind
`ancillaries`, and `/icon?kind=ancillary&image=` for the pictures. **All 1134
ancillaries in the three installed EDAs parse with zero unknown constructs, come
back byte for byte, and re-render to themselves under a full-form save**;
`tests/test_ancillaries.py` is 85 checks.

Because EDA and EDCT are one language, the second editor was mostly extraction
rather than new code - and that is the shape the next few phases should keep:

* **`unittransfer/keyblock.py`** now owns "a block of `Keyword value` lines whose
  order the engine cares about, edited by splices": the splice, the
  insert-at-its-place rule, the flag keys, the required-key refusal, the
  list-compared-as-a-list rule and the line-ending-preserving I/O. Traits was
  rewired onto it first, and its 117 checks are what proved the extraction.
* **`triggers.edit_section` / `orphaned_by` / `strip_effect_lines` / `new_block` /
  `append_block`** now own the trigger half of a save, so both editors delete
  their own record's triggers the same way. `Affects` and `AcquireAncillary` are
  the same problem with a different keyword.
* **`stringsbin.upsert_txt`** owns writing `{tag}text` back into a localisation
  file, continuation lines and all - `export_VnVs.txt` for traits,
  `export_ancillaries.txt` for ancillaries.

Four things EDA does that EDCT does not:

* **`Type` and `Transferable` are not in the guide at all** - that guide is RTW's,
  both lines are M2TW's, and both are present in all 1134 real ancillaries as
  lines two and three. `Type` groups them (a character holds one per type) and is
  free-form: the mods use **350 distinct values**, which is why the reference
  tool's 17-value dropdown is not ported (`docs/upstream/audit-ancillaries.md`).
* **Two hardcoded limits, both silent**: more than 3 `ExcludedAncillaries` is an
  errorless crash, more than 8 `Effect` lines makes the ancillary impossible to
  gain from a trigger (TWCenter, *List of Hardcoded Limits*).
* **An ancillary has a picture**, resolved from `data/ui/ancillaries` then the
  vanilla UI and decoded through the existing icon cache. **DaC names two that
  nobody shipped** - a blank slot in game and nothing in any log.
* **Its own name is a text key**, unlike a trait's, so the box beside the name is
  what the player reads.

- **Exit criteria:** ✅ round-trip byte-identical; ✅ edit end-to-end with undo;
  ✅ image references resolved and previewed like unit cards.

## Phase 10 - Minor Files module ✅ (two sessions, done 2026-08-14)

**10b ✅ (done 2026-08-14).** `web/js/minorfiles.js` + a `MODES` entry, `GET
/api/minor` + `/api/minor/record`, `POST /api/minor/plan|apply`, the five code
view kinds wired into `/api/codeview`, and the editor half of
`unittransfer/minorfiles.py` (`overview`, `detail`, `vocab`, `plan`, `apply`).
One tab strip over five files, because the parse layer already made them three
shapes. `tests/test_minorfiles.py` is 160 checks and drives create / edit /
delete / undo against a scratch mod.

Three rulings the files forced, and all three are refusals:

* **Two of the five tabs are edit-only, and the format says so.** The engine's
  resource list is closed - all three installed mods ship the same 28 names and
  a `type` it does not know is read and ignored - so "create a resource" would be
  a button that writes a line nothing reads, and deleting one leaves
  `descr_regions.txt` placing a resource nothing defines. A culture is eleven
  settlement models and cards, a fort, a port ladder, a watchtower and six
  agents; nothing a text editor conjures, and deleting one orphans every faction
  whose `culture` line names it. Both refusals are shown where their buttons
  would be, with the reason.
* **The resources tab shows its name and refuses to write it.** `text/strat.txt`
  compiles to a **style-1 archive: 1307 bare strings with no tags at all**, read
  by position, and identical in length across all three mods. Appending a line
  shifts every index after it. Our own `stringsbin.refresh_from_txt` already
  refuses to rebuild an untagged archive, so the tab points at the Strings
  module, which edits that file by position. The other two localised tabs
  (`rebel_faction_descr.txt`, `religions.txt`) are style 2 and written normally.
* **A religion save is four files or it is nothing.** The block, the
  `religions { … }` list, `descr_religions_lookup.txt` and `text/religions.txt` -
  one job, one backup set, one undo, because a religion that reaches three of
  them half exists. Measured on the lookup: the three mods disagree about its
  *order* (Third Age 3 has islam and orthodox the other way round from its own
  list) and its *contents* (Third Age 6 lists a `wicked` that no longer exists)
  and all three run, so a save keeps it in step **by name only** - appending or
  dropping a line, never reordering one.

Two things fixed on the way, both outside this phase's own code and both real:

* **The Code View widget's GUI→pane arrow was never wired in Traits or
  Ancillaries.** Its own header comment promises "edit a box, the text is
  re-serialised by the server and redrawn", and `cvFromGui` was called only by
  the unit and strings editors. Measured live: typing in an ancillary's Type box
  left the pane showing the old text. All three editors now call it.
* **`config._write_json` was not atomic, and it cost real 404s.**
  `Path.write_text` truncates then writes; the server is threaded; any request
  resolving a mod inside that gap read a truncated `settings.json`, got `{}`, and
  concluded the machine had no Medieval II install - so every mod vanished for
  that instant. Invisible because the page's GET helper retries. Caught as a 404
  on `/api/codeview` the moment an editor saved the `code_view` toggle and opened
  a record in the same breath. Now a temp file plus `os.replace` (with a retry,
  because Windows refuses the rename while a reader has the file open) and an
  mtime-gated read cache, so `get_med2_root` stops opening the file on every mod
  resolution. Stress-tested: 24 000 concurrent reads against 1000 writes, zero
  torn reads and zero failed writes; it was 23 torn reads with the rename alone.

Single source of truth landed as the exit criteria asked: `edbvocab.religions` /
`cultures` / `resources` were three regexes beside the module that edits those
files, and now call `minorfiles.religion_names` / `culture_names` /
`resource_names`. `buildings.RELIGIONS` - a hardcoded vanilla five, and DaC has
ten of which none is `pagan` - is now `VANILLA_RELIGIONS`, used only as the
fallback when a mod has no `descr_religions.txt`. Home's readiness matrix gained
the Minor Files module and, while there, the Traits and Ancillaries rows that
phases 8b and 9 never added.

**10a ✅ (done 2026-08-14).** `unittransfer/minorfiles.py` - five files, and
they turned out to be **three shapes, not five**, which is why they are one
module: flat `keyword value` records on `keyblock` (rebel factions, resources),
brace blocks (religions, cultures), and indented sections of bare words
(`descr_names.txt`). **All 15 real files in the three installed mods parse with
zero unknown constructs, come back byte for byte, and every record re-renders to
itself under a full-form save**; `tests/test_minorfiles.py` is 133 checks. Five
new Code View kinds (`rebels`, `resources`, `religions`, `cultures`, `names`),
all five refusing a rename in the text pane - every one of these names is a key
`descr_regions.txt` or `descr_sm_factions.txt` points at.

Three things the formats forced:

* **A campaign file's gap between keyword and value is data.** These files are
  laid out in tab columns, so `keyblock` gained `head_prefix` / `sub_value` /
  `sub_tokens` and `edit_keys(align=True)`: a rewritten value keeps its column,
  and a new line copies the gap of the line above it. The EDCT/EDA path is
  untouched - those files really do use one space.
* **A culture record does not end at its closing brace.** The forts, ports,
  watchtowers and six agent lines come after it and belong to it, so a record
  ends at the next `culture` line.
* **Art references are not checked.** A pip or a settlement card can live in the
  game's `.pack` archives, which the toolkit cannot read. Checking anyway gave 78
  findings across three mods, 77 of them noise.

**Their four minor-file parsers are not ported** - see
`docs/upstream/audit-minorfiles.md`. This is the first audit where the reference
implementation is not merely lossy but wrong about the format: a religion's key
is `pip_path` inside a brace block, not their `icon` / `pip` / `anti_pip`; a
resource's model line is `item`, not their `model`; and their rebel serialiser
appends `, <exp>, <count>` to every `unit` line, when not one of the 215 real
`unit` lines has a comma and the unit types have spaces in them. Two of their
serialisers write files the engine will not load at all.

What the checks found in real mods: **Third Age 3 disagrees with itself about its
own religions** three ways (a duplicate `heretic` block, a name missing from the
`religions` list, three stale entries in `descr_religions_lookup.txt`); DaC drops
`moot_and_bailey` from 7 of its 10 cultures and `fortress` from one; and there
are 97 duplicate character names across the three `descr_names.txt` files.

- **Goal:** One tabbed module for the small campaign files: rebel factions,
  religions, cultures, resources, character names.
- **Preconditions:** Phase 4; Phase 6 for localised names.
- **Files:** **10a:** ✅ `unittransfer/minorfiles.py` + `tests/test_minorfiles.py`
  + the five Code View kinds. **10b:** `web/js/minorfiles.js` + `MODES` entry +
  `/api/minor/*` + `plan`/`apply` (the backup+undo save, still to write - copy
  `ancillaries.plan/apply`).
- **Effort:** L in total; each session M.
- **Exit criteria:** ✅ every tab round-trips byte-identical; ✅ rebel-faction unit
  pickers use localised unit names (453 of them on Third Age 3, resolved the way
  every other unit picker resolves them); ✅ religions/cultures referenced by
  Buildings mode resolve from here instead of ad-hoc parsing (single source of
  truth - `minorfiles.culture_names` / `religion_names` / `resource_names` are
  that source, and `edbvocab` now calls them).
- **Risks:** `descr_names.txt` is huge and encoding-sensitive; treat as its own
  tab with lazy load. *Landed as:* 25 903 names in Third Age 6, read as sections
  per faction so a pane loads one faction rather than the file. Encoding is
  Latin-1 like every other campaign file, which is what makes the byte-exact
  round trip a promise rather than a hope.

## Phase 11 - Factions editor ✅ (done 2026-08-14)

`unittransfer/factions.py`, `web/js/factions.js` + a `MODES` entry,
`GET /api/factions` + `/api/faction`, `POST /api/factions/plan|apply`, Code View
kind `factions`. **All 90 factions in the three installed mods parse byte-exact,
re-render unchanged under a full-form save, and produce zero findings**;
`tests/test_factions.py` is 83 checks.

**It needed no parser.** `descr_sm_factions.txt` is the fourth file to be a run
of `<head> <name>` records with `keyword value` lines under it, so it is a
`Shape` and nothing else - which is what STATE.md predicted and what made the
first hour of this phase a measurement rather than a parser. That made the
extraction worth doing: the flat-record engine moved out of `minorfiles.py` into
**`unittransfer/flatrecord.py`**, with `minorfiles` re-exporting every name it
published so its 160 checks were untouched. A fourth caller is the point at
which "the shape the minor files share" stops being a fact about the minor files.

What 90 real factions decided:

* **The line order is canonical and nobody disagrees.** Ten distinct orderings
  appear across the three mods, and a topological sort over all of them finds
  **zero conflicts** - so `ORDER` is derived, not guessed, and every observed
  ordering is a subset of it (a test asserts exactly that).
* **`has_family_tree` is not a boolean.** `yes`, `no` or `teutonic`, and **24 of
  the 90 say `teutonic`**. A checkbox - the obvious GUI - would have written
  `no` over every one of them, so it is a three-way picker with the count in the
  hint.
* **The head line can carry a modifier**: `faction egypt, spawned_on_event`, and
  `shadowing` / `shadowed_by` naming another faction (five real cases). The slot
  is the part before the comma, and `slot_of` is why nothing here ever compares
  a whole head line to a faction name.
* **The localised name matters more here than anywhere else in the toolkit.**
  Mods reuse vanilla slots wholesale - DaC's `sicily` is the Kingdom of Gondor,
  Third Age 6's `milan` is Rohan - so a list of slots is a list of the wrong
  countries. Names are written back to `text/expanded.txt`, whose tag is the
  slot in **UPPER CASE** (`{SICILY}`); `Mod.faction_names` lower-cases on read,
  which is right for reading and would have created a dead second entry on write.
* **No create, no delete.** A faction slot lives in eight or nine files at once
  and TWCenter has a step-by-step tutorial for adding one precisely because one
  file is never the job. Same ruling as the cultures tab in Phase 10b.

**The "banner/symbol textures displayed" exit criterion was written on a wrong
premise and is replaced.** This file names no faction texture at all: `symbol`
and `rebel_symbol` are `.CAS` **3D strat models** (Phase 14's business, not an
image), and `loading_logo` names a `.tga` that **not one of the 90 real factions
ships unpacked** - all 90 are inside the game's `.pack` archives, which the
toolkit cannot read. `standard_index` and `logo_index` are indices into banner
and UI sprite sheets, and neither appears in any `data/text/*.txt`. So the paths
are shown, a found one is marked (symbols often are: 59/90), and an unfound one
is never called missing - Phase 10a's ruling about pips and settlement cards.
What IS visual and IS in this file is the two map colours, and those got what
they deserved: a swatch on every row and a colour picker in the form.

One bug found on the way, in the shared machinery rather than here:
**`keyblock.edit_keys(align=True)` put an inserted line in the wrong column.**
It copied the *gap string* of the record's first line, which only lands right
when the two keywords are the same length - inserting `can_build_siege_towers`
with `culture`'s four tabs pushed its value five columns past everything else.
Measured: at a 4-space tab, **1731 of the ~1800 value-bearing lines in the three
real rosters start in column 28**, so the gap is a *column*, not a string. Now
`pad_to_column` tabs to the column the record itself uses, and a keyword too
long to reach it takes a single tab, which is what the real long ones do.

Single source of truth again: `buildings.faction_cultures` was a fifth ad-hoc
reader of this file (it got the head-line comma right by accident) and now calls
`factions.faction_cultures`.

- **Exit criteria:** ✅ faction records fully editable with round-trip fidelity;
  ✅ colours shown and edited, art paths resolved-when-findable and never
  falsely reported missing (replaces "banner/symbol textures displayed", which
  the format does not support - see above); ✅ name edits flow through Phase 6's
  codec into `expanded.txt`.
- **Risks:** faction records cross-reference many files (strat, win conditions)
  - *landed as:* out-of-scope references are shown read-only, and the ones this
  module CAN check (culture, religion, horde units) are checked against the
  mod's own `descr_cultures` / `descr_religions` / EDU.

## Phase 12 - EDB upgrades ✅ (done 2026-08-14)

`buildings.plan_new_tree` / `new_tree_text` / `icon_slots` / `upgrade_name`,
`TREE_PREFIXES` + the `TREE_ACTIONS`/`TREE_REFUSED` pair, a `create` key on
`/api/buildings/plan|apply` (no new endpoint - a create is a building save),
`web/js/buildings.js` gaining the tree list, the new-tree dialog and a grouped
capability picker, and `docs/upstream/audit-edb.md`. `tests/test_edb_tree.py` is 79
checks over **277 real building lines / 1099 levels / 771 upgrade entries**.

Four things the measurement decided:

* **A tree is two files or it is nothing.** The EDB block and three text keys per
  level go in one job with one backup set - a level short of `{x}`, `{x_desc}` or
  `{x_desc_short}` crashes the game at the construction panel, and all 1099 real
  levels have all three. A mod with no `text/export_buildings.txt` is refused
  rather than half served. The cards are the third thing and they are **art**:
  listed with their paths, never written, and a blank one is never called a fault
  (Phase 10a's ruling).
* **The levels chain forward, and that is not a style choice.** All 771 upgrade
  entries in the three mods point at a level listed *after* them on the `levels`
  line - none backwards, none at itself, none at a level its line has not got.
  The reference tool's upgrades picker offers every level except the current one,
  so it will happily write the one shape no real file has.
* **A level name is the EDB's one global namespace.** Two lines cannot share one:
  the text keys, the icon stems and every settlement plan are keyed on it, so a
  new tree reusing one is refused before either file is touched. Same for a line
  named after an existing level.
* **The two limits in TWCenter's hardcoded-limits note are RTW-era.** "Max 64
  building trees" - Third Age 3 has 117 and DaC 136, both running, so no warning.
  "Max 9 levels per tree" - true of vanilla, and Third Age 6's `core_building` is
  **51** deep on M2TWEOP, so passing nine is *said*, with the number, not refused.

Also landed: **an upgrade's own clause is editable.** 41 of the 771 entries are
`wooden_wall requires factions { … }` and ours showed that as a read-only chip;
the row now has the same ✎ picker every other clause has, writing back into the
same string (`detail()` gained `upgrade_paths` beside the strings a save sends,
so nothing else changed shape). And the capability picker is grouped: 60 keywords
in nine `<optgroup>`s with the engine's accepted range beside each, up from 49 in
one flat alphabetical list. Eleven keywords came from the reference tool's
capability sheet and **none of them is used by any installed mod** - which is the
point: a capability keyword is engine vocabulary, not a fact about a mod, so this
is the one place where adopting their hardcoded list is right (the check runs the
other way too - all 48 keywords the real files use were already ours).

<details><summary>original plan</summary>

- **Goal:** Fold the reference tool's good EDB ideas into our Buildings module:
  collapsible building-tree list as an alternative to the gallery, an
  "add new building tree" flow, and any field-layout wins from their editor.
- **Preconditions:** Phase 4 (Buildings already has Code View via 4b).
- **Files:** `web/js/buildings.js`, `unittransfer/buildings.py` (new-tree
  scaffolding: EDB block + levels + `export_buildings.txt` strings + icon
  slots), tests.
- **Effort:** M - one session.
- **Exit criteria:** ✅ list/gallery toggle persisted (`bld_browse`; the gallery
  stays, because a building card is how anyone recognises a building they have
  seen in game and their editor has no art at all); ✅ creating a new tree
  produces a mod that loads - `line_checks` on the created line is clean and a
  whole-mod check run is no worse than before it; ✅ `docs/upstream/audit-edb.md`.
- **Risks:** new-tree creation touches EDB + strings + icons at once - reuse
  the transfer engine's plan→preview→apply pattern. *Landed as:* exactly that,
  and through the existing `/api/buildings/plan|apply` rather than a new pair -
  a create is a building save whose line does not exist yet, so it gets the
  backup, the undo and the `.strings.bin` recompile for free.

</details>

## Phase 13 - EDU + Sounds audit ✅ (done 2026-08-18)

- **Goal:** Systematically compare their EDU fields/dropdowns and SoundEditor
  against ours, adopt the small wins, and write down the verdict.
- **Preconditions:** Phase 2 (manifest points at the files).
- **Files:** `docs/upstream/audit-edu-sounds.md`; small diffs to `unittransfer/vocab.py`
  / `edu.py` / `sounds.py` and editor JS where adopted.
- **Effort:** S - one session.
- **Exit criteria:** the audit document lists every field/dropdown they have,
  ours beside it, verdict (have-better / adopted / rejected-why); adopted items
  landed with tests.
- **Risks:** their vocab lists are hardcoded vanilla - adopt *fields*, derive
  *values* from the mod as we already do.
- **Outcome:** `docs/upstream/audit-edu-sounds.md`, measured over **1756 real units**
  (Kingdoms vanilla + Divide and Conquer EUR + Third Age Reforged). Nothing was
  adopted from their code: they have no field we lack (`card_info_pic_dir` is in
  no real file), and their value lists are RTW-era or invented in nine closed
  slots out of eleven. What the audit *did* produce is ours - banner names now
  come from the mod's own `descr_banners_new.xml` (`vocab.banner_names`, three XML
  sections onto the three EDU lines, and into `defined` so an undeclared banner is
  flagged), and two silent rewrites in the guided editor were fixed
  (`stat_mental`'s fourth token, `formation`'s trailing comma). Their SoundEditor
  is a different file family which its own parser destroys - 0 of 32 round-trip -
  so the `descr_sounds_*.txt` **coverage gap is recorded, not closed**.

## Phase 14 - Bug-fix and polish pass (nine sessions)

One batch of defects and small features from real use of the finished modules,
plus the leftovers `docs/upstream/audit-codebase.md` recorded and did not fix. Nothing
here is new ground: it is the pass that makes Phases 0–13 feel finished before
the two big ones. Reported items are grouped by **where the fix lives**, not by
where they were noticed, and every one is written down - a session may re-scope
an item or find it already fixed, but may not drop one silently.

- **Preconditions:** none beyond the modules themselves. Independent of 15 and 16.
- **Effort:** XL overall; each sub-phase below is one session with its own exit.
- **Ordering:** 14a first - it is the only sub-phase holding a broken core flow.
  The rest can be reordered freely. (14g was 14c's last item until it was measured
  at 115 hits and given a session of its own. 14i came after the release, from
  using it.)

### 14a - Loading, mod switching, and the two Transfer failures ✅ (done 2026-08-18)

- **Goal:** A mod switch is instant and safe, and Unit Transfer works on Third
  Age Reforged.
- **Items:**
  - **Switching mods mid-load does not interrupt the load.** `api.get`
    (`core.js:34`) has no `AbortController` and retries four times with backoff,
    so picking another mod leaves the first mod's requests in flight and the
    screen ends on `TypeError: Failed to fetch`. Give the loader a request
    generation: a response from a superseded generation is dropped rather than
    painted, and the requests behind it are aborted.
  - **DaC to Reforged and back does not switch the units** - the grid keeps the
    old mod's, and Settings cannot be clicked while it is happening. Same area;
    confirm whether it is one bug or two.
  - **Reforged unit cards fail to convert and show black**, and pressing Transfer
    unit greys the screen instead of opening the composer. Find out where:
    `icons._decode_to_png` (`icons.py:127`) swallows a decode failure and returns
    a placeholder, so a card format Pillow reads differently would look exactly
    like this. The grey screen is a second symptom - an exception thrown while
    building the composer leaves the overlay up with no dialog inside it, which
    should never be a reachable end state.
  - **A loading bar at the bottom of every menu** while the module is still
    fetching, showing real progress rather than a spinner. One shared widget in
    `core.js`, driven by the loads the modules already await.
- **Files:** `web/js/core.js`, `web/js/transfer.js`, `unittransfer/icons.py`,
  `web/index.html` (bar styling), tests.
- **Exit criteria:** switching mods during a load never shows a fetch error and
  never paints stale data; every Reforged unit card decodes, as a measured count
  in the test; the composer either opens or says why, never greys out; the bar
  appears in every mode whose load runs longer than about 200 ms.

**Outcome - it was one bug wearing four masks.** Black unit cards, "TypeError:
Failed to fetch", the grey composer and the dead Settings button were all the
same incident: **the server was shutting itself down while it was being used.**

The chain, measured on this machine:

* The icon cache lived in `.cache/icons` **next to the app** - which here means
  inside OneDrive. Reading 400 cached icons back out of it: **137 of them failed
  outright** with `OSError: [Errno 22]` (a dehydrated cloud placeholder), and of
  those that did read, the median was 12.6 ms and **the worst was 79 seconds**.
* An unreadable entry surfaced as a blank PNG, because `_icon` catches everything
  and paints a blank rather than 500ing. A screen of those is a grid of **black
  cards** - indistinguishable from "the conversion failed".
* The slow ones filled the browser's ~6 connections to one origin. The page's
  heartbeat is a `setInterval` sharing those connections, so it stopped getting
  through: the server's own log shows heartbeats every 4 s, then nothing for 150
  seconds, then `browser idle >150s - shutting down`. **The dead-man watchdog
  killed a live session.** Everything after that is what a dead server looks
  like from a page that is still open.

Fixed at each link, with `tests/test_liveness_and_cache.py` (21 checks) on the
two that are ours to promise:

| | before | after |
|---|---|---|
| icon cache | inside the synced app folder | `config.cache_dir()` → `%LOCALAPPDATA%` |
| unreadable cache entry | served as a blank (black card) | treated as a miss, re-decoded from the mod's own TGA |
| proof of life | the heartbeat alone | **any** request (`note_request`), heartbeat still proves the page rendered |
| dead-man window | 150 s | 300 s |
| `Registry.get()` per request | ~4 ms (folder scan + 12 stats, under one lock) | **0.7 µs** on the hot path, disk re-checked at most once a second |
| unit-card lookup | **224,712 globs** to answer one `/api/units` | one listing per folder, keyed on its mtime |
| `/api/units` for DaC (916 units) | 4189 ms | **350–420 ms** |
| 427 Reforged cards, warm | 6.0 s, 137/400 unreadable | 3.3 s, 0 failures |

The client half: `api.get`/`api.post` take an abort signal, every load takes a
generation (`newLoad()` / `loadStale()`), and a response from a superseded load
is dropped instead of painted - a fast DaC→Reforged→DaC now ends on DaC's 916
units every time. `openComposer` no longer raises the overlay before it has
anything to put in it, so a failure there says what failed and offers a retry
instead of greying the screen. And the **loading bar** is driven by the API
client itself (`loadbar` in core.js), so every module has one without a line of
its own code: it appears after 180 ms, names what it is reading, sweeps while a
single request is out and becomes a real fraction once there is more than one.

Also swept up here because it is the message this fix changes: the five places
still naming `Launch-Unit-Transfer.bat` (14c's third item) now name the real
file.


### 14b - The log, and undo/redo ✅ (done 2026-08-18)

**Outcome.** All five items landed, with `tests/test_log_and_activity.py` (26
checks) over the two halves that are ours to promise.

* **The log opens in 51 ms instead of 571** (and instead of minutes on a cold
  `config/`): `/api/log` is now `log_page(mode, offset, limit)`, newest first,
  40 to a page. 1.1 MB of JSON became 29 KB and 600 KB of markup became 40 KB.
  `manifest` is dropped from a listed entry - it is undo's own bookkeeping and
  the page never used it - and a summary over 4000 characters is cut with a note
  saying where the rest is (one real entry is **310 KB** on its own).
  `newer_count` is computed server-side, because "Revert to here (N)" was the
  only reason the page ever needed the whole log.
* **A mode filter**, as tabs with counts over the whole log, showing only the
  modes that have entries: here that is Everything 480, Traits 205, Minor files
  120, Ancillaries 81, Transfers 37, Factions 30, BMDB 6, Buildings 1.
* **"Save diagnostic log" moved into the log panel's footer**; Settings now
  points at the log instead of carrying its own copy of the button.
* **Ctrl+Z / Ctrl+Y were never wired for five of the editors.** The handler was
  live the whole time - `undo.js` had scopes for the building editor, the unit
  and BMDB editors, the transfer composer and Sounds, and nothing for **Traits,
  Ancillaries, Factions, Minor Files or Strings**, all of which were built after
  it. They all keep a deep-cloned working copy at `state.<x>.d.w` and repaint
  from it, which is exactly the shape the snapshot stack wants, so each needed a
  scope and a baseline: `undoReset()` at the point the working copy appears
  (without it the *first* edit becomes the baseline and Ctrl+Z has nothing to go
  back to), plus `undoBaseline()` for Strings, which reloads rows for paging and
  searching without changing what is being edited. Verified one field at a time
  in all five: undo restores the old value, redo puts the new one back.

* **The log records what the person did, next to what the tool did.** Half of
  "what happened" was missing: every file written was in there and not one of the
  clicks that led to it, so reading it back meant inferring intent from effects.
  `POST /api/activity` takes batched UI events - capped at 60 an event, truncated
  to 300 characters, newlines stripped, written as text at DEBUG, never
  interpreted - and `activity()` reports mode opened, mod picked, record opened,
  field changed from X to Y (on `change`, so one line per value settled on rather
  than one per keystroke), and a dialog closed with edits still pending. The old
  value comes from a `focusin` capture, because it is only knowable before it
  changes. A real session now reads:

```
UI  opened           Minor Files (mod: Third_Age_Reforged)
UI  opened record    gladiator_uprising (rebels) in Third_Age_Reforged
UI  changed          chance: “100” -> “42”
UI  picked mod       Third_Age_Reforged (was Divide_and_Conquer_EUR)
UI  reading mod      Third_Age_Reforged
```

* **And the tool narrates its own background work**, which is the other half of
  the same complaint. `PARSE` says which mod is being read and what came out of it
  (`916 units, 89 mounts, 1941 localised names in 0.55s`) - that is what the
  screen is waiting for on a cold mod, and it was previously silent. `UNITS` says
  how long the payload took and **how many units ship no card**, naming them at
  DEBUG: a blank card in the grid is either "this mod has no art for it" or "the
  conversion failed", and those look identical on screen. `ICON` says which file
  was converted and how long it took, and names the unit when there is nothing to
  convert (`Stone Giants has no card art in Third_Age_Reforged`) - the icon cache
  only ever sees a path, so that line had to be written where the unit is known.

Two tests had to change with the endpoint: `test_edit_http` and `test_bmdb_http`
read `/api/log` as a bare array, and now read `["entries"]` (newest first). Both
pass, and `test_edit_http` gained a check that the page reports its own totals.

- **Goal:** The log section is where you go to find out what the tool did, and it
  opens instantly.
- **Items:**
  - **Opening the log takes up to minutes.** `/api/log` returns
    `config/transfers.json` whole - **1,086,991 bytes here** - and `openLog`
    builds HTML for every entry in it. Page it server-side and paint a window of
    it, so open time stops depending on how long the tool has been in use.
  - **Move "Save diagnostic log" out of Settings** (`settings.js`, the "Something
    went wrong?" fieldset) **into the log section**, with the rest of the log.
  - **Filter the log by mode** - transfer, edit, bmdb, sounds, buildings and the
    rest - so "what did I do in the Unit Editor" is one click.
  - **The log does not record enough.** It should read as a transcript: what the
    user did (entered this mode, opened this unit, changed this field from this
    to that, saved it or left it), and what the tool did in the background with
    the same weight (parsing this file, fetching unit data, fetching the unit's
    UI art, this card was not found so it is being converted). `logutil.py`
    already has `block`, `file_op` and `fingerprint` for exactly this shape - the
    gap is the calls, not the plumbing. UI actions have no path to the log at
    all today, so that needs a small endpoint, batched.
  - **Ctrl+Z and Ctrl+Y are broken everywhere.** The handler is live
    (`undo.js:303`) but every scope's `id()` opens with `modalOpen()`, so outside
    a dialog there is nothing to undo and the key silently does nothing. Decide
    per scope what is meant to happen, then fix it - "nothing of ours to undo"
    and "the browser's own undo" must not be confusable.
- **Files:** `web/js/settings.js`, `web/js/undo.js`, `unittransfer/server.py`,
  `unittransfer/config.py`, `unittransfer/logutil.py`, tests.
- **Exit criteria:** the log opens in under a second on a log this size; the mode
  filter and the save button are both in it; a scripted session (open a mod, edit
  a field, save, switch mode) reads end to end in `server.log` with nothing
  important missing; Ctrl+Z and Ctrl+Y take back and restore a value in every
  editor that claims to support them.

### 14c - Launcher, Home, and the prose sweep ⏳ (four of five done 2026-08-18)

- **Goal:** Nothing on the way into or out of the tool tells the user something
  untrue.
- **Items:**
  - **"Pillow is missing" is printed on every failed start**
    (`Launch-Medieval2-GUI-Toolkit.bat:98`), one of three guesses, while
    `startup.preflight` has already worked out the real reason. Print the
    preflight result instead of the guess list.
  - **"Keep the console window open" does nothing for the current session** -
    `app.py:97` reads `show_console` once, at launch. Either apply it live or say
    "from the next launch" at the tick box, not three lines below it.
  - ~~**The old launcher name is still in five places.**~~ ✅ done in 14a, which
    rewrote one of those messages anyway.
  - **Home step 1 gets its own Browse and Auto-detect buttons** instead of a
    Change button that opens Settings (`home.js:61`); both actions already exist
    as `browseRoot()` and `autoDetectRoot()`.
  - **Home gains a step 3, Preferences**, carrying the settings options (console,
    transfer defaults, unit-text cache, ignored limits) so Settings is not the
    only way to reach them.
  - ~~**A second prose sweep.**~~ Split out as **14g** - measured at 115 hits
    across 12 files, which is not a tail-end item.
- **Files:** `Launch-Medieval2-GUI-Toolkit.bat`, `Install-Dependencies.bat`,
  `app.py`, `unittransfer/startup.py`, `web/js/home.js`, `web/js/settings.js`,
  UI strings across `web/js/`, `README.md`.
- **Exit criteria:** forcing each preflight check to fail prints that check's own
  reason and no other; no file in the repo names the old launcher; Home does the
  root folder and the preferences without opening Settings; the UI strings carry
  no clause-joining em dash and no uncapitalised sentence.

**Outcome.** Four items done and verified; the prose sweep is measured and split
out as **14g** below, because it is a session's work of its own.

* **The launcher no longer guesses.** A failed startup check now exits **2**
  (`app.EXIT_PREFLIGHT`), so the .bat can say "the reason is in the list above,
  look for the lines marked FAIL" instead of printing three guesses under it -
  the first of which was "Pillow is missing → pip install pillow", Pillow
  installed or not. A non-zero code that is *not* 2 gets its own message: the
  checks passed, so it is not a missing library or a taken port, and the log has
  the traceback.
* **"Keep the console window open" can be applied now.** It is read once, at
  launch, which is why ticking it appeared to do nothing; the tick box now says
  so where the tick is, and **↻ Restart now to apply it** hands the port to a
  replacement server. The order is the whole trick: the outgoing server cannot
  stop before it has answered the request telling it to stop, so it replies,
  spawns the replacement with `--wait-port`, and only then lets go. Measured
  end to end: pid 22044 → 19632 on the same port in 6.1 s, and the page waits for
  `/api/ping` and reloads itself. A console child runs on `python.exe`, not
  `pythonw.exe`, or its output would have nowhere to go.
* **`startup.port_free` asks by binding, not by connecting.** The first version
  connected, and on this machine that cannot answer the question: with a timeout
  set, `connect_ex` returns `WSAEWOULDBLOCK` both for a closed port and for a
  listener whose accept queue is full, and a *closed* loopback port here times
  out rather than refusing. Binding is exactly the question a starting server
  asks. Four cases now behave: live server held, non-answering listener held,
  closed port free, and free within 1.0 s of a release.
* **Home step 1 has its own Browse and Auto-detect buttons**, and picking a
  folder re-reads the mods and repaints the cards, so the grid below answers
  straight away whether it was the right folder. Auto-detect reports "no install
  found in the registry" here, which is correct: this install has no registry key
  (the success path cannot be exercised on this machine).
* **Home step 3 is Preferences** - console, soldier-from-base, `.strings.bin`
  recompile, Code View and which faction name leads - one row per line, each
  saving on change. Settings keeps the awkward ones (M2TWEOP folders, the
  unit-limit overrides, the cache, Quit) and step 3 links to it.

**Carried in and fixed here:** audit §1.5. `config._read_json` fell back to the
last text it had read whenever a read failed, which is right for the microsecond
a Windows `os.replace` makes a file unopenable and wrong for a file that is
*gone* - a deleted `settings.json` stayed visible for the rest of the run, and
the tool went on reporting a MED2 root that had been removed. Gone and busy are
now told apart. That was also the `test_startup` flake: 48/48, three runs
running, where it was 31/32 with the failing check moving between runs.


### 14d - Unit Editor: a compact guided view, and a Code View that follows - DONE

- **Goal:** The guided editor fits on a screen, and Code View sits beside the
  field you are actually looking at.
- **Items, and what each turned out to be:**
  - **Pair the rows that belong together.** `GF_PAIRS` in `guided.js`, drawn by
    `gfRows`: Internal name | Dictionary · Category | Class | Voice type |
    Accent · Faction banner | Holy-war banner · the three officer entries ·
    Movement modifier | HP · Heat fatigue | Ground modifiers · Charge distance |
    Fire delay. A group is emitted where its first member appears, in the
    **group's** order rather than the file's, so a mod that has moved a line
    does not lose the pairing over it. Both guided hosts get it - the composer
    as well as the editor.
  - **Tidy layout on by default.** `cvAutoTidy` lines the block up as the record
    opens, and the honesty of the pane is kept by what it does NOT do: the
    fields are identical, so the boxes are not rebuilt and nothing pending in
    them is lost, and the result is remembered as `cv.auto` so `edCvUserEdited`
    can tell "the tool did that" from "the user did that". Opening the pane
    therefore does not make the dialog dirty; the moment there IS something to
    save, the tidied text is what gets written. Off is a remembered setting
    (`code_view_tidy`) and turning it off re-reads the record from the file.
  - **Code View sticks now.** The cause was not `position:sticky` at all: every
    adopter wraps `cvHtml()` in a column div, so the pane is a CHILD of the grid
    item, and `.cvsplit`'s `align-items:start` shrink-wrapped that item to the
    pane's own height - a sticky box with nowhere to travel. `stretch` gives it
    the row's height back. Measured: pinned at the modal's top through the whole
    scroll, and a field at the very bottom of the dialog has its line in view.
  - **The comment lines are hidden, and the hiding is a PAIR of functions.**
    `codeview.hide_comments` / `show_comments`: the page is handed the text
    without the comment-only lines plus an opaque `hidden` list, sends both
    back, and the server rebuilds the real bytes before anything parses or
    saves. The page never learns what a comment looks like in this format, which
    is the module's existing rule. A trailing comment stays on its line - it
    belongs to the field in front of it. Each hidden line remembers its index,
    the line it sat above and that line's keyword, tried in that order, so
    typing a new **value** does not move it. `COMMENT_MARKS` carries `#` for the
    EDB, per Phase 13's ruling.
  - **Raw-lines mode is line for line.** Neither pane scrolls: `cvExpand` grows
    the pane to the whole record and `edRawAlign` places each box from the
    **span** the server already sends, not by counting rows - a block has a
    `type` line, hidden comments and repeats, so counting would drift. Measured
    at 1 px over a 38-line block.
  - **"Open file location"** replaces the Browse button under both cards, over a
    new `POST /api/reveal` that takes the mod and a path RELATIVE to that mod's
    data folder, never an absolute one.
  - **The unit card image was clickable and did nothing** - it picked up
    `.card`'s pointer cursor and hover border from the browse grid. It now does
    what the ✎ on it does.
  - **The group-by headings fold**, remembered per group-by on the user's
    settings, and **Era (custom battle)** joins Faction / Category / Class as a
    group-by so all four of the named ones exist to fold.
- **Files:** `web/js/guided.js`, `web/js/editor.js`, `web/js/codeview.js`,
  `web/js/core.js`, `unittransfer/codeview.py`, `unittransfer/server.py`,
  `unittransfer/folder_dialog.py`, `web/index.html`, and the four other Code View
  adopters (`traits.js`, `ancillaries.js`, `factions.js`, `minorfiles.js`), which
  saved `cv.text` and now save `cv.base` - `text` is the view, and saving it
  would have deleted every comment line.
- **Exit criteria - all met:** each paired row lands on one line at the default
  window width (measured: identical `top` for every card of all seven rows);
  Code View's highlighted line is in view at any scroll position; a round-trip
  through the comment-hiding view is byte-exact (`test_codeview`, and end to end
  in a running browser on a DaC trait and a TATR unit); raw-lines mode lines up
  row for row; group headings fold and the state survives a repaint.

### 14e - EDU cleanup, and unit tiers ✅ (done 2026-08-19)

`unittransfer/edusort.py`, the tier marker in `unittransfer/edu.py`, tier and
variant vocabularies in `vocab.py`, `GET /api/edu/order` +
`POST /api/edu/sort/plan|apply`, `web/js/edusort.js` and a tier box on the Unit
Editor's identity tab. `tests/test_edusort.py` is 56 checks over both installed
mods. **The marker is `;@m2gt tier=3 variant=aor`, as proposed and confirmed.**

Four things the measurement decided, and all four went against the plan:

* **A `;@m2gt` line directly above `type` starts that unit's block.** Under the
  old boundary a comment above `type` belongs to the PREVIOUS unit, so the
  marker would have described one unit while living inside another and been
  left behind by every transfer, replace and sort. Safe to change precisely
  because the marker is ours: no real file has one, so every byte-exact
  round-trip is untouched by construction.
* **The file's own banners are read before anything is asked of the user.**
  A tier is in no game file - but a mod that organised its EDU by hand has
  already written one, and **907 of DaC's 916 units sit under a
  `;--- GONDOR TIER 1 INFANTRY ---` banner**. The tier is harvested from there
  and recorded on the unit, which also breaks a circle: this pass rewrites the
  banners, so a tier living only in one would be regenerated from itself.
* **Faction first, kind second - the table of contents is not the layout.**
  DaC's TOC promises a GENERALS block and MERCENARIES / SIEGE / SHIPS blocks,
  and the file does not have them: all 31 generals sit at the head of their own
  faction's run and the 127 mercenaries are spread from unit 11 to unit 891.
  Hoisting either moves ~140 units their author placed. Only the 13 units
  nobody owns fall through to a shared section.
* **A section is the author's own word for it, kept as text.** Only 146 of 916
  banner names match a localised faction name - a modder writes `CRAG` and
  `DORWINION` - and `ownership` cannot stand in, since most units list a dozen
  factions and the line is a set, not a ranking. Resolving banners to faction
  slots, or ordering sections by `descr_sm_factions.txt`, each moved hundreds of
  units for nothing; taking the order from where it is actually expressed (the
  median position of each section's units) took DaC from 44% of the roster
  moving to **15%**.

Also landed: **a hand placement is recorded, not just applied.** The ordering
screen writes `order=N` onto the units it places, so the next cleanup honours
them - a placement the following run undoes is a screen that wasted the user's
time. And the plan **refuses** any text that is not purely a reordering: same
units, same fields, every comment still there, checked before a byte is written.

<details><summary>original plan</summary>

### 14e - EDU cleanup, and unit tiers

- **Goal:** Turn a sprawling `export_descr_unit.txt` into the shape DaC's is in,
  without the tool ever deciding something it cannot justify from the file.
- **Items:**
  - **Tidy the whole file**, not one unit at a time - the layout `cvTidy` already
    applies to a single block.
  - **Group the units into sections.** Work out how DaC's EDU is actually
    organised (generals at the top, then by faction, then by unit type) and
    reproduce that grouping. **Prefer the order already in the file:** a unit
    already in a sensible place does not move.
  - **A per-faction GUI for the order**, so exceptions can be placed by hand
    rather than argued with.
  - **Unit tiers.** A tier is in no game file - it is the tool's own metadata,
    kept in a comment above the unit, and it exists so this sorter has something
    to sort by. Tier 0–5 by default plus special variants of each (AoR, unique
    general, quest unit and so on), and a way to add more. Editable in the Unit
    Editor, labelled there as tool-only so nobody expects the game to read it.
  - **Open question for the user:** the exact comment marker. Proposal -
    `;@m2gt tier=3 variant=aor` on the line above the unit's `type`, one owned
    prefix, invisible to the engine, skipped by our parsers the way Phase 13's
    ruling skips `#` in the EDB. *Confirmed as proposed, 2026-08-19.*
- **Files:** a new sorter module in `unittransfer/` (splice-based: it moves whole
  line blocks and never re-emits a record), `unittransfer/edu.py`,
  `web/js/editor.js`, `web/js/guided.js`, tests over both installed mods.
- **Exit criteria:** ✅ cleaning up either installed mod's EDU produces a file the
  game loads, with the same units, the same fields and every comment still
  present; ✅ running it twice changes nothing the second time; ✅ a tier written in
  the editor survives a cleanup and a save; ✅ the per-faction ordering GUI can
  place a unit the sorter got wrong.
  *Landed as:* the ordering GUI is a tab of the cleanup dialog rather than a
  screen of its own, and it is per **section** rather than per faction, because
  a section turned out to be the author's own banner word and not a faction slot
  (see above). **`web/js/guided.js` is untouched on purpose:** the guided view is
  a view of real EDU field lines, and putting a value the engine never reads
  among them would blur the exact distinction the "toolkit only" badge exists to
  make. The tier lives on the identity tab, where a unit's identity already does.

</details>

### 14f - EDB unit view, twin compare, and the rest ✅ (done 2026-08-19)

**Outcome.** All ten items landed, with `tests/test_unit_view.py` (25 checks)
over the two halves that are ours to promise, measured across **8233 real pool
rows** in the two installed mods.

The unit view was already the screen that gathered every building line training
one unit; what it could not do was any of the things you go there to do. It can
now:

* **The Requires clause is editable from the unit's side**, through the same
  dialog the building editor uses. These rows come from lines that are mostly
  not loaded, so the clause dialog was given a host of its own and the edit is
  kept in `cmp.edits` beside the numbers - which is what makes a requirement
  edited here produce the same plan entry as one edited from the building view.
* **A Twin column**, per TIER rather than per building: a twin that trains the
  unit five levels up is not the same building. **DaC has 239 rows whose facing
  tier does not train the unit and Third Age Reforged has none** - the second
  number is why this is worth showing, because a check that can only ever say
  "diverged" is not measuring anything. Each gap gets a `⇄` that stages the pool
  into the twin through `bldStagePool`, so it refuses a duplicate and rides the
  same Save as everything else.
* **A read-only Code View** (`codeview.pools_document`, kind `pools`). It is the
  one code view in the toolkit that is **not a record** - it gathers
  `recruit_pool` lines from a dozen blocks, so there is nothing for a serialiser
  to write back to, and it is read-only by construction rather than by policy
  (no `parse`/`render` pair is registered at all). Hovering a row lights its
  line; each line is the file's own bytes with its real line number beside it.
* **The three recruitment numbers are named** - Immediate recruitment, Replenish
  rate, Max pool - in the unit view and in the add-units dialog both. "start /
  per turn / max" said what the numbers looked like, not what they do.
* **The `open` badge says what it means**, "add to the tiers above" **names the
  tiers**, and the recruitment faction dropdown **remembers whether it is sorted
  by unit count or A to Z** (`bld_facsort`; count stays the default, because
  "who trains the most here" is the question the list is usually scanned for).
* **The BMDB Editor is the BMDB + Sprites Editor**, in `MODES`, in
  `modfiles.py`'s readiness matrix and in the README.
* **Minor Files shows its art.** A religion's pip, a resource's icon, a
  settlement card and an agent card are all TGAs under the mod's `data/`, and
  the editor showed them as text while the Buildings gallery showed pictures.
  Same server route as a faction symbol (`kind=modfile`, which keeps the path
  inside `data/`). The two files disagree about the prefix and **both are
  right** - a resource icon is written `data/ui/…` and a religion's pip
  `ui/pips/…` - so the redundant half is dropped at the call site rather than in
  either parser. A blank slot is still never called a fault: Phase 10a measured
  that check at 78 findings across three mods, 77 of them noise.

Two bugs found on the way, both ours and both in shared machinery:

* **`bldTouched()` re-rendered a form that was not on screen.** Staging anything
  from the unit view threw `Cannot set properties of null` out of
  `bldRenderBody`, because the building body element does not exist while the
  unit modal is up. It now returns early when the unit view owns the modal, and
  the form is rebuilt from the same working copy on the way back.
* **The clause dialog and the unit view shared one stash slot.** Both saved the
  markup they covered into `b.stash`, and the unit view can open the clause
  dialog *on top of itself* - so the two took turns clearing one slot and the
  building form underneath was lost, wiping the editor on the way back. The
  clause dialog now has its own (`bldClauseStash`/`bldClauseUnstash`) and the
  nesting stops mattering.

**One item resolved as a no-op, and it is recorded rather than quietly
dropped:** "gallery view is already the default, find what set `bld_browse` to
`tree` before changing it." Nothing does. The only writer in the codebase is
`bldSetBrowse`, which is the user's own click on the view toggle, and the saved
setting on this machine reads `gallery`. There was nothing to fix.

<details><summary>original plan</summary>


- **Goal:** Recruitment is editable from the unit's side, and a city/castle pair
  can be brought into line in one click.
- **Items:**
  - **The unit view already exists** (`bldUnitRow`, `buildings.js:2673`) and
    lists every line that trains the unit. Two gaps: **the Requires column is
    read-only** there while the same clause is editable elsewhere, and **the
    `open` badge is unexplained** - it means "the building line you have open"
    and needs a tooltip saying so.
  - **"Mention if the unit is in the TWIN building."** *(Answered 2026-08-19.)*
    The first reading - *is it in this mod's EDU* - was wrong, and checking
    settled it: that is already built and has been since Phase 12
    (`buildings.js:2650` shows a red "not in this mod's EDU" beside the name).
    What was meant is the city/castle counterpart: for each row in the unit
    view, say whether the twin line trains this unit too. It is the same
    question `bldTwin()` already answers for a whole building, asked per unit,
    and it is what makes the **Mirror** item below actionable from this side.
  - **Recruitment numbers in two rows:** the top row renamed to **Immediate
    recruitment** (start), **Replenish rate** (per turn) and **Max pool**
    (maximum); the bottom row the unit's requirements.
  - **Compare the city and castle variants of one building side by side**,
    units included, with a **Mirror** button that resolves one unit or all of
    them. Half of this is built: `bldTwin()` and `bldTwinLevel()` find the twin,
    the add-units dialog can already mirror into it, and the recruitment checks
    already produce `mirror` findings - this is the view that makes them
    actionable.
  - **Sort the recruitment faction dropdown** by A to Z or by unit count.
  - **"Make the code view reach the UNIT VIEW too."** *(Answered 2026-08-19.)*
    The first reading - *Buildings gets Code View like every other module* - was
    also wrong: the building editor has had it since Phase 4b
    (`bldCvToggleHtml` at `buildings.js:488`, `bldCvHost` at `506`). The dialog
    with no pane is the per-unit recruit-pool view, which is what the rest of
    this sub-phase is about. It should show the `recruit_pool` lines it is
    editing, from however many building blocks they come from.
  - **Hovering "add to the tiers above" should name the tiers** it means
    (`buildings.js:2092`).
  - **Gallery view is already the default** (`buildings.js:204`), so the report
    means a remembered `bld_browse` of `tree`. Find what set it before changing
    the default.
  - **Rename the BMDB Editor to "BMDB + Sprites Editor"** - the `MODES` entry at
    `core.js:241` and every label that follows from it.
  - **Minor Files has art it does not show.** Many of those menus have TGAs
    behind them; show them the way the Buildings gallery shows a building.
- **Files:** `web/js/buildings.js`, `unittransfer/buildings.py`,
  `web/js/minorfiles.js`, `web/js/bmdb.js`, `web/js/core.js`, tests.
- **Exit criteria:** ✅ a requirement edited from the unit view saves the same as
  one edited from the building view (verified in a running browser: the plan
  reads `wooden_castle: … requires factions { portugal, } and region_religion
  catholic 15 -> factions { poland, }`); ✅ the twin compare shows both halves of
  a real DaC pair and Mirror closes an inconsistency the checks flagged
  (`core_castle_building · motte_and_bailey` → `core_building ·
  wooden_pallisade`, staged and previewed); ✅ the renamed recruitment fields are
  the ones a save writes; ✅ Minor Files shows art for every menu that has any.

</details>

### 14g - The second prose sweep ✅ (done 2026-08-19)

**Zero clause-joining dashes, down from 21.** Rewritten across `guided.js`,
`transfer.js`, `buildings.js`, `sprites.js`, `editor.js` and `factions.js`: a
dash doing a full stop's work became a full stop, a colon or a conjunction,
whichever the sentence actually wanted.

**Most of the 115 was the measurement, not the writing.** `dev/checks/prose_check.py`
promised in its own docstring to stitch a note's fragments back together before
judging them, and did not - so a continuation was read as a sentence of its own
and reported for starting in lower case, which is what a continuation does. Six
reader defects, each fixed at the source rather than by rewriting 90 sentences
around a quirk of the reader:

| | what it did | hits |
|---|---|---|
| leading `+` | the codebase writes `\n +'…'`; only a TRAILING `+` was stitched | 47 |
| escaped quotes | `\'` ended the literal early, chopping sentences mid-word | 5 |
| `+ (a?'x':'y') +` | a choice spliced into a sentence read as two strings | 10 |
| ternary branches | two literals sharing a line were joined into one sentence nobody wrote | 9 |
| inline CSS | `'flex:0 0 88px'` has spaces and letters, so it read as prose | 5 |
| `${n} unit(s) …` | a sentence opening on a value was judged on the letter after it | 12 |

Two rules were also added to what is *not* a sentence, alongside the existing
"a label is not a sentence": **a list is not** (the `syn:` lines name a record's
value slots - "attack, charge, projectile, range, ammo, …" - every word an EDU
term that is lower case by definition), and **a sentence that opens on an
interpolated value is not judged on the letter after the hole.**

**Four deliberate keeps**, all one class and one reason: a fragment spliced into
a sentence that is assembled at render time, so the reader never sees the whole
of it and the lower-case start is correct on screen.

* `buildings.js:1990` - a `fixes` entry, rendered as "Saving fixes both: the
  ownership line is extended, and the missing textures are copied…".
* `editor.js:1361` - a ternary branch continuing "Editing this entry changes …".
* `sprites.js:482` - an optional clause inside "Writes the voice bank … .".
* `transfer.js:183` - a template branch continuing "Copied: the … block …".

<details><summary>original plan</summary>

### 14g - The second prose sweep

- **Goal:** Finish the writing rules across the whole UI, with a number to hit
  rather than an impression to chase.
- **The work list is measured.** `dev/checks/prose_check.py` (written in 14c) reads
  the visible strings out of `web/js/*.js` and `web/index.html` and applies the
  two rules: **115 hits in 12 files - 21 clause-joining dashes and 94 lower-case
  sentence openings.** Worst first: `guided.js` 37, `transfer.js` 29,
  `buildings.js` 27, `sprites.js` 9, `editor.js` 5.
- **It is a work list, not a linter.** Three heuristics were tried and thrown
  away before the count meant anything: reading line by line reported 589
  lower-case starts, almost all of them the second half of a sentence that began
  correctly on the line above (a long note is several literals joined with `+`);
  scanning after every full stop flagged sentences that legitimately open with a
  code identifier (`no` means a melee weapon); and short labels are not
  sentences - "mercs only" and "per turn" are right as they are. The tool now
  stitches fragments back together and only flags a whole string. **Read every
  hit in context before rewriting it.**
- **Files:** UI strings across `web/js/`, `web/index.html`.
- **Effort:** M - one session.
- **Exit criteria:** ✅ `python dev/checks/prose_check.py` reports zero, or every
  remaining hit is listed in this phase as a deliberate keep with its reason.
  *Landed as:* zero dashes, and the four remaining case hits listed above.

</details>

### Carried in from `docs/upstream/audit-codebase.md`

That audit's own list belongs to this phase rather than to the viewer, and none
of it is done. **Must:** §1.1 - `bmdb.mount_audit` crashes with `TypeError:
string indices must be integers` on a mod shipping only some `descr_*.txt`; a
dead parameter, a namespace confusion and a casing mismatch, fixed in one pass
with the trimmed-mod repro as the test. **Should:** §1.4 (derive `_invalidate`
from `Mod`), §1.5 (narrow `config._read_json`'s staleness window without removing
the fallback) and settling §2's `test_edit_models` question. **Then:** unhardcode
`Third_Age_6` in the three fixtures, so the baseline stops hiding regressions
behind mod-set churn, and take the ~20 lines of §6 safe removals.

- **Risks:** a long list of small changes across every module is exactly the
  shape that breaks something quietly. Two guards: the splice rule - 14d's
  comment hiding and 14e's sorter both touch files that must round-trip
  byte-exact, so assert the round-trip and not just the feature - and
  `test_web_modules`, which is the only thing between a new shared widget and a
  silent name collision in the one global scope.

### 14i - The post-release correction pass ✅ (done 2026-08-20)

The list that came back from actually using v2.0.0. Ten items, no new direction,
**folded into the 2.0.0 release notes rather than given a version of its own** -
the user asked for it that way, so the tag, `__version__` and the release page
all stay 2.0.0 and `docs/releases/RELEASE_2_0_0.md` gained a "The correction pass"
section. A future round asked for as its own version is 2.0.1.

- **Goal:** finish 2.0.0 properly. Two real defects, one freeze, seven pieces of
  polish, a repo rename and a writing sweep.

**Outcome.**

*The repo.* `ProJ-Yeet/medieval2-unit-transfer` → `ProJ-Yeet/medieval2-gui-toolkit`,
description rewritten, `origin` re-pointed. GitHub forwards the old address, so
nothing published breaks. The only in-tree references were STATE.md and
HANDOFF.md; the app itself never linked to its own repo.

*Two defects, one cause each.*

- **"Open file location" opened Documents.** `folder_dialog.reveal` passed
  `["explorer", "/select,<path>"]` as a LIST, and `subprocess.list2cmdline`
  wraps the whole `/select,C:\Some Folder\x.tga` token in quotes as soon as the
  path holds a space. Explorer cannot parse the switch then and falls back to
  the default folder. Every real mod path has a space in it, so it failed 100%
  of the time and looked like "the button does nothing useful". It is one
  command STRING now with the path quoted inside the switch, plus `normpath`
  because Explorer will not follow forward slashes. Verified against a real DaC
  card path: Explorer lands on `…/Divide_and_Conquer_EUR/data/ui`.
- **Ctrl+Z did nothing in the Code View.** undo.js listens on the document and,
  whenever an editor is open, calls `preventDefault` and restores a snapshot of
  that editor's BOXES. Typing in the pane is in no such snapshot, so the
  browser's own textarea undo was suppressed and ours had nothing to give back.
  The pane keeps its own stack now (`cvUndoInit` / `cvUndoNote` / `cvUndoStep`),
  same shape as undo.js's: snapshots, a run of typing coalescing into one step
  after 450 ms of quiet. Two rules keep the stacks from fighting - a text change
  nobody typed re-baselines the pane's stack, and an EMPTY stack means "not
  mine", so the handler returns without touching the event and undo.js runs
  next. Undo therefore walks back through the typing and then out into the form,
  in the order the edits were made. codeview.js loads before undo.js, which is
  what makes the ordering work.

*The freeze.* `bldRenderBody` threw `Cannot set properties of null` whenever a
panel that takes the modal over (Add units, the per-unit comparison, the new
city/castle comparison) was on screen and something changed the working copy.
The throw came out of an onclick, so it killed that click and everything after
it - from the outside, the tool stops responding. `bldTouched` now returns early
for `cmp`, `vc` or any `stash`; `bldRenderBody` returns early with no `#bldBody`
at all. The stale-`state.bld` paths went with it: the settlement filter's
handler reads the live object rather than the one captured when it was wired,
and `bldSetView` / `bldFacSortToggle` / `bldPoolFacPick` / `bldCapList` go
through a guarded `bldRedrawLevel()`.

*Everything else.*

| item | where |
|---|---|
| Folding sidebar groups, persisted, with a ticked-count badge | `core.js` `wireFilterFolds`, read off the markup so a new `<h3>` folds without being wrapped by hand |
| ＋ beside the tier Variant | `editor.js` `edTierVarAdd`; the typed value is kept in the list as `(new)` or the drop-down comes back empty and the staged value looks lost |
| Abilities merged into **Weapons & abilities** | `guided.js` `GF_SECTIONS`; two cards was never a tab |
| Editable comment breakers | `edusort.banner_style` / `banner(title, style)`; width, fill, prefix, capitals, live sample in the dialog. `upper` defaults OFF so the default output is byte for byte what 2.0.0 wrote |
| The ordering screen as a unit LIST with tier / variant / **classification** | `edusort.js` rewritten; `apply_marks` writes them onto `;@m2gt`; `overview` sends `detected_special` so the box arrives filled in |
| **⇄ Compare city / castle** | `buildings.variant_compare` + `GET /api/buildings/variants`; the panel, per-unit ⇄ Mirror and ⇄ Mirror all in `buildings.js` |
| One set of names for the three pool numbers | `POOL_LABEL` / `POOL_SHORT` in `buildings.js`, used by every screen that shows them |
| Two-line recruitment rows | `.poolrow .prtop` / `.prbot`; the `requires` clause is the only thing on that row with no natural width |
| The comparison header lines up | the header cells carried none of the classes that set the column widths |
| The building Code View follows field edits | `bldCvFollow()` from `bldDirtyNote` and `bldTouched`; this editor was the only adopter that never called `cvFromGui` |
| Faction sort as a toggle | it was an entry in the drop-down it sorts, so choosing it closed the list |
| Unit cards on the voice rows | `sprites.js` `sndRowHtml` |
| ~300 clause-joining em dashes → 0 | every `web/js` module and `index.html`; four number ranges kept, and the lower-case keeps are file names, `and`/`or` clause tokens and inline fragments |

**New surface.** `GET /api/buildings/variants?mod=&line=&culture=`;
`marks` and `style` on `POST /api/edu/sort/plan|apply`; the `special=` marker key
on `;@m2gt`, read through `edusort.special_of` and detected by
`edusort.detected_special`.

**Measured.** DaC `barracks` against `castle_barracks`: 3 units on one side only,
411 with different pool numbers across 414 shared units - which is why "differs"
is reported per FIELD and a `requires` mismatch is not counted as a divergence.
A city clause names the city factions and a castle clause names the castle ones,
so a single yes/no would have flagged the whole roster and meant nothing.

**Risk that bit.** The ordering screen repaints ONE row on a drop-down change,
not the roster: 916 units × 3 drop-downs took ~690 ms to rebuild, so the box you
had just used was replaced under the pointer. 11 ms after.

**Two defects the new suite found in the new work**, both in the banner style
and both the same shape - a writer that can draw something its reader cannot
read. `BANNER_RE` only ever matched a rule of HYPHENS, so a banner drawn with
`=` or `#`, or with a prefix of `;;`, was unreadable to the next run: it would
be carried as an ordinary comment AND a fresh one written above it, and the file
would gain a banner every pass. The reader takes the whole `BANNER_FILL` set
now, which also picks up the `;===== GONDOR INFANTRY =====` a mod wrote by hand.
And `width` was off by one against the line it produced (96 in, 95 out) -
inherited from the constant it replaced. `BANNER_WIDTH` is 95 now and the
arithmetic is exact, so the default output is byte for byte what it always was
*and* the number means what it says.

`tests/test_variants_and_marks.py`, 82 checks: the comparison from both sides on
every installed pair, every banner style round-tripping through `BANNER_RE`,
seven nonsense styles falling back rather than raising, and a marked cleanup
reaching disk on both real mods with no unit gaining or losing a field.

### 14j - Replace any picture ✅ (done 2026-08-20, released as v2.0.1)

- **Goal:** every picture the tool draws can be replaced in place and can say
  where it lives, the way the unit card already could - with a warning when the
  resolutions do not match.

**The way in is the `<img>`'s own `src`.** Every picture on every screen is
painted through `/icon` or `/building_icon`, and that URL is a complete
description of the question the server answered. So the page hands the URL
straight back and `unittransfer/images.py` re-resolves it. That is what made
this small: one dialog and one engine cover unit cards, info cards, ancillary
pictures, faction art, the Minor Files pips and settlement cards, and building
icons, instead of five per-screen imports.

**Outcome.**

- New `unittransfer/images.py` (`locate` / `plan` / `apply` / `reveal_target`)
  and `web/js/images.js`; routes `POST /api/image/plan|replace|reveal`. The
  write goes through the same backup + log record as every other job, so it is
  in the log and undoes like a transfer.
- **Two ways in.** A delegated right-click menu on any `<img>` whose src is one
  of the two routes - which is what covers the thumbnails in lists and grids -
  and a ✎ plus a button pair on the screens where the picture is the subject
  (card variants, ancillary, faction art, the building editor's Art pane, and
  the Minor Files pips, where the pip itself is the button).
- **The resolution check**, which is what was actually asked for: the confirm
  dialog puts both pictures side by side at the size each really is and names
  both sizes when they differ. A warning and never a refusal - a mod is free to
  change what size its own art is.
- **A unit card fans out to every faction folder that holds one**, reusing
  `edit._unit_icon_files`, falling back to the ownership fan-out `_plan_icon_import`
  computes when the unit has no card yet. Replacing only the folder the preview
  resolved would leave the rest stale - which is the same fact the card-variant
  list exists to make visible.
- **Borrowed art creates rather than overwrites.** A building icon or ancillary
  picture the mod does not own is served out of the vanilla UI; a replacement
  writes the mod's *first* copy at the path the game looks for, and the dialog
  says so. That is the "drop a .tga in to override it" the building browser had
  been telling people to do by hand.
- **`.png`/`.jpg` → 32-bit `.tga`**, and a same-stem sibling in the other native
  extension is removed so two files cannot answer to one name. Backed up first.
- **`Function(...)` rather than `window[name]`** for the panel re-render hook: a
  top-level `const` in a classic script lands in the global lexical scope, not
  on `window`, so `bldRenderBodyNow` was invisible to a property lookup.
- A bare `addEventListener` at the top level of a module file breaks the two
  node-driven tests, which stub `document`/`window` but not the global. It is
  `document.addEventListener` now.

`tests/test_images.py`, 53 checks - it builds its own folder of pictures rather
than borrowing a mod's, so everything but the unit-card fan-out runs with no
game installed. The last section drives the real server over HTTP with the exact
JSON the page sends.

## v2.1.1 - a fix subrelease ✅ (2026-08-23)

Not a phase. Two failures out of one user's log, both of which presented as
HTTP 500: a mod folder with a `data/` and no roster (every stock install has
four - the Kingdoms campaigns, still packed), and a `battle_models.modeldb`
whose texture count disagreed with the textures under it. Both answer with a
sentence naming the file now, `/api/mod_files` no longer parses the mod it is
reporting on, and the page stops retrying an answer the server chose. Carries
the dropped-`<script>` fix that was already in the tree. Notes:
`docs/releases/RELEASE_2_1_1.md`.

## Phase 15 - 3D model viewer ✅ (done 2026-08-20, released as v2.1.0)

- **Goal:** A working in-browser viewer for unit `.mesh` models (their
  ModelViewer is broken).
- **Preconditions:** Phase 3. **Both "ground truth" references named here were
  wrong, and 15a proved it** - see below; there was nothing to port and the
  format came out of the files themselves.
- **Files:** **15a:** `unittransfer/mesh.py` + `dev/diagnose/meshdump.py` + tests.
  **15b:** `web/js/viewer3d.js` + API endpoint; entry points from BMDB and Unit
  Editor ("view model").
- **Effort:** L.
- **Exit criteria:** any soldier/mount model in the test mods renders with
  diffuse texture, correct origin and orbit controls; wrong-format files fail
  with a message, not a hang; decode covered by tests.
- **Risks:** skinning/skeleton display is out of scope (static pose is enough
  for V2).

**PHASE 15 IS DONE (2026-08-20), RELEASED AS v2.1.0** - 15a the decoder,
15b the viewer, 15c the pass against the Blender addon, 15d the two decode
corrections the user caught by loading the same models in Blender (the halved
`u`, and the packed normals). Notes in `docs/releases/RELEASE_2_1_0.md`.
Two corrections to what this phase assumed:

- **The Blender addon has no loader to port.** It writes an IWTE task file and
  shells out to `IWTE.exe` (`tasks/iwte_run.py`); its only binary code is DDS
  header poking. It is not a format reference for `.mesh` at all.
- **Their `casCodec.js` cannot parse a real file.** It documents `.mesh` as
  "uint32 version, uint32 submesh count, 32-byte vertices". Every real `.mesh`
  opens `16 00 00 00 "serialization::archive"` - it is a **boost::serialization
  binary archive**, and the class-descriptor-on-first-use rule means no
  fixed-stride reader can work. The format is written up in full at the top of
  `unittransfer/mesh.py`; that docstring is the spec now.

4,700 of the 4,702 models in both test mods decode, plus the reference
templates - settlement meshes (no skeleton) and siege engines (a second vertex
format, normals as floats rather than packed bytes) included. The 2 that do not
are sky domes holding several models back to back, refused by name.

**15b** is `web/js/viewer3d.js` (hand-rolled WebGL), `server._model_route`'s
three endpoints, and **View model** on the shared model card. Exit criteria met:
soldier and mount models render with their diffuse texture, correct origin and
orbit controls; a wrong-format or missing file answers with a sentence and the
right status code; the decode is covered by `test_mesh` (34) and the routes by
`test_viewer3d_http` (21). Two facts about the format came out of building it and
are recorded in `mesh.py`: **models are Y-up**, and UVs follow the **Direct3D**
convention (v=0 at the top), not OpenGL's. `.cas` is **not** decoded: it is a
3ds-max scene export, not a `.mesh` variant, and it moves to **16e** with the
reconnaissance recorded in `mesh.py`. **15b uses hand-rolled WebGL, not a
vendored three.js** (user's decision, 2026-08-20): a static textured model needs
little of what three.js offers, and it keeps the no-build-step rule intact.

## v2.1.3 - two more cleaners, faction skins and a resizable viewer ✅ (2026-08-26)

Not a phase: the same shape as 15e, features found by using the tool. BMDB mode
grows from two tabs to four, and the model viewer stops taking the screen over.

- **Strat map** (`unittransfer/stratmap.py`, `web/js/stratmap.js`,
  `tests/test_stratmap.py`, 43 checks). `descr_model_strat.txt` and
  `data/models_strat` audited and cleaned the way `bmdb.py` does the modeldb:
  browse every `type` block with who references it, then a 🧹 dialog for the
  models no `strat_model` line, script or `descr_*.txt` names and the files
  nothing points at. References come from `descr_character.txt`, another block's
  `model_sprite`, `descr_sm_factions.txt`, `descr_sm_resources.txt`,
  `descr_cultures.txt`, every campaign script and every `.lua`.
  **Two rules make it safe rather than catastrophic**, and both were found by
  running it against a real mod before writing the UI: `models_strat/residences`
  is skipped entirely (the game reads a faction's settlement variant out of that
  tree by folder - nothing names the file), and `x.tga`, `x.tga.dds` and `x.dds`
  are ONE texture (M2TW prefers the DDS for a line that says `.tga`; without that
  rule the first scan called 387 MB of Divide and Conquer's live art unnamed).
  With them, DaC's real answer is 4 MB of dead models and 54 MB of unnamed files.
- **Unit cards** (`unittransfer/cards.py`, `web/js/cards.js`,
  `tests/test_cards.py`, 39 checks). Every unit and info card hashed, then sorted
  into three questions: art for a dictionary no unit claims, the same picture
  copied identically into N faction folders, and sets that genuinely differ per
  faction. The first two are facts and are ticked; the third is a question and is
  shown as pictures side by side with "keep all" selected. Consolidation writes
  one copy into `ui/units/mercs` / `ui/unit_info/merc`, the folder the engine
  already falls back to, and moves the rest out. DaC: 645 MB of 1.2 GB. Refuses
  to touch a file that is not shaped like a card (the agent pictures), a unit
  that pins `*_pic_dir`, or a dictionary only a `.lua` script names.
- **🛡 Fix ownership / 🌐 All factions** (`bmdb.ownership_audit` /
  `ownership_edits`, `tests/test_ownership.py`, 41 checks). An entry's faction
  texture records against the `ownership` of the units drawn with it - every
  model slot counts, `slave` counts, an ownership token the roster does not
  define does not and is reported instead. The second button asks the roster
  rather than the units. Records are only ever added, a new one is a clone of an
  existing one, and the dialog states the size cost first: All factions on Third
  Age Reforged is +9.4 MB on a 1.4 MB file. Routed through `edit.plan_bmdb`, the
  same planner the model card's faction checklist uses.
- **A draggable divider** (`core.js` `splitInstall`) on both docked viewers, with
  the width saved per screen; in BMDB mode the panel now opens at half the window
  and already showing.
- **One sheet is one texture.** The viewer used to glue every skin to a second
  sheet, falling back to a copy of the main one when the entry named no
  attachment - a canvas, a second decode and a 2048-wide atlas for a result
  identical to wrapping the single sheet. It now binds the one sheet and scales u
  by 1.0 instead of 0.5 (`uUScale`). Every ordinary mount is that case. Entries
  that really carry two sheets are unchanged.

Notes: `docs/releases/RELEASE_2_1_3.md`. Suite: 65 of 65 modules.

## Phase 15g - Add a faction, and UV mode ✅ (v2.1.8, done 2026-08-31)

Two unrelated asks in one session, both extending a module that already existed.

**Add a faction** (`unittransfer/factionclone.py`, new). Phase 11 shipped the
Factions editor with a written refusal: a slot lives in nine files, so one that
exists only in `descr_sm_factions.txt` is a mod that will not load, therefore no
create and no delete. The refusal was right about the problem and wrong about
the conclusion - the answer is to write them all. **Twelve, as it turned out**,
not nine: grepping the installed mods for a slot found `export_descr_buildings`
(101 and 424 `requires factions { … }` clauses - what lets a faction build and
recruit at all), `descr_sounds_accents` and `descr_faction_standing` on top of
the nine the phase-11 docstring listed. The count in that docstring was a
plausible number nobody had measured, which is exactly the kind this project
does not keep. TWCenter's own step-by-step
(`Reference/TWCenter/Creating a world - adding a new faction/`) is the spec, and
its method is why this is safe: **it never invents a value.** Every step is
"find where the donor is named and name the clone too, with the same value", so
there is no question of what colour or roster the new faction gets. Nine cloners,
not one search-and-replace, because the donor's name is doing something different
in each file - a record to re-head, a section to copy, a braced block, a shared
comma list to join, length-prefixed texture records (straight to
`modeldb.add_texture_factions`, which already fixes the group counts).

Art is **found, not listed**: anything under `ui`, `menu` or `banners` carrying
the slot as a token, copied and renamed. Roots whose art a *line* points at
(`models_strat/textures`, `loading_screen`) are deliberately excluded - the
clone's own copies of those lines already name the donor's file, so copying it
would leave a duplicate nothing refers to.

`descr_strat.txt` is **reported, not written**, and that is the ruling to keep:
a campaign entry is a region, a settlement, a starting army and map coordinates,
and two factions cannot begin in the same settlement. There is no donor answer to
copy, so the plan says so in as many words. Deleting a faction stays refused for
the same reason - it needs a decision, not a copy.

Four bugs found by testing, each worth remembering:
- **The game files are CRLF and `$` sits after the `\r`.** Three of the nine
  cloners silently matched nothing and two more ate the `\r` and left the file
  half CRLF. Cloners now see `\n` throughout and the file gets its own ending
  back on write. A cloner that changes nothing and reports no error was the worst
  failure available here, so the test asserts a per-file non-zero count.
- **`_` is a word character in a data file and a separator in a text key.**
  One boundary found `{SICILY}` and none of the sixty `EMT_` keys. Two helpers
  now, `_tok` and `_key_tok`, and the filename matcher takes the *longest*
  roster slot in a name so cloning `sicily` never steals `sicily_clone`'s art.
- **`add_texture_factions` reads ONE entry's raw text.** Handed the whole
  modeldb it finds no groups and changes nothing - a clone with no skins.
- **A file may spell the same list two ways.** `descr_faction_standing.txt`
  writes both `factions { … }` and `exclude_factions { … }`, and which one it
  prefers is per mod: Reforged has 96 and 20, DaC has 164 and **none**. Matching
  only the second would have cloned nothing at all in one of the two installed
  mods - and the count that revealed it came from grepping both, not from
  reading one.

**What it refuses to guess at, it counts and names.** `REVIEW_FILES` +
`review_mentions`: traits named after the faction (`Trait Fearssicily`, and the
engine effect `Combat_V_Faction_Sicily`), an ancillary's `and FactionType sicily`
- one operand of a boolean, not a list - and prebattle speeches. Appending to
any of those would invent a trait the engine has never heard of or silently
rewrite a condition. So they are reported with hit counts and left to the Traits
and Ancillaries editors, which already open them.

- **Exit:** met. `tests/test_factionclone.py` 64/64 against the real mods,
  read-only; `tests/test_factionclone_apply.py` 30/30 writes a synthetic mod and
  undoes it, proving restore is byte-exact and nothing is left behind. That
  second suite exists because `transfer.undo` deletes a created path with
  `unlink()`, which raises on a directory and is swallowed - so copied art is
  listed in the manifest one file at a time, never as a folder.

**Show UVs** (`web/js/viewer3d.js`). Paints the UV coordinate instead of the art
in the same space the sampler uses, so the tiling the shader comment has always
described is now visible: blue main sheet, amber attachment sheet, dark for the
repeats, red where the pair restarts. 32 checker cells to a sheet is **measured,
not picked** - real parts span 0.07 to 0.33 of u each, so a coarser grid gives a
head less than one whole cell and says nothing about it. Verified in-browser on a
real pair (body main, bow and quiver attachment) and on a lone-sheet mount, which
correctly shows no amber and drops that row from the legend.

Notes: `docs/releases/RELEASE_2_1_8.md`. Suite: 71 of 71 modules.

---

## Phase 15h - Recruitment on the unit, and the UV layout ✅ (v2.1.9, done 2026-09-01)

**Recruitment as a tab on the unit** (`web/js/edrecruit.js`, new). Everything a
unit IS was on four tabs; where it can be HIRED was in another module, reached
by leaving the unit, finding one of the four or five building lines that train
it, and reading its numbers off a row among sixty. The building browser already
had the panel that puts those rows side by side (`bldShowUnit`, phase 14f) -
this is that view from the unit's side, and editing.

**No Python, on purpose.** A `recruit_pool` line already had a reader
(`buildings.unit_instances`) and a writer (`buildings.plan_edit`); the tab is a
second FRONT for them, not a second implementation, so a pool edited from the
unit and one edited from the building cannot drift apart. The one shape that had
never been sent before is the request: this tab reaches into several building
lines at once and belongs to none of them, so **every** edit rides in `also` and
the main body carries a line name with an empty `levels`. That is also the right
way round for `_check_recruit_limit`, which merges the file's existing pools for
an `also` line and would otherwise count a payload of three rows as the whole
level.

**The clause dialog is borrowed, not copied** (`kind:'edrec'` in
`bldClauseApply` / `bldClauseCancel`). It could not take the usual route:
`bldClauseStash` stashes the modal as MARKUP, and the unit editor holds a live
WebGL column inside that modal, so putting the string back would install a dead
copy of the canvas and orphan the real one. The `edrec` branches re-render the
editor from state instead, which hands the column over the way a tab switch
does - same reason the ＋ picker keeps no stash either.

**A recruitment save moves EDB line numbers**, which retires an assumption
`backToBuilding` had written down: "capability line numbers index the EDB, which
a unit edit never touches". A building left open behind the editor now has its
working copy dropped after such a save, so the way back re-reads the line from
disk rather than splicing against numbers that have shifted.

- **Exit:** met. `tests/test_unit_recruitment.py` 42/42 across DaC and Reforged
  - the row payload carries every field the tab keys on, `cap_line` is unique,
  an `also`-only request plans, a rewrite moves no line and leaves the 173
  capability lines it never mentions byte-identical, and rewrite + delete +
  append across three lines come back as three changes with the other two lines
  named. Verified in-browser end to end against DaC: three pools across two
  building lines written in one save, the diff exactly those three lines, and
  one Undo restoring the 1.6 MB EDB byte for byte.

**The UV layout** (`web/js/viewer3d.js`, `.v3uvpane`). `Show UVs` paints the
coordinate onto the MODEL; this is the other half - the SHEET, with the mesh's
islands drawn over the art they sit on, in the **bound image's** own space
rather than the mesh's u. A 2D canvas, not a second WebGL context: the drawing
is one image and a few thousand lines. Chasing its framing of a horse turned up
a bug in the RENDERER - an entry naming **no** attachment texture (every
ordinary mount) has one sheet spanning the whole two-unit space, and u must be
halved for it too; it was not, and that tiled the sheet twice. Measured with
per-triangle texel-space Jacobians: real pairs read 1.21–1.24 at half u, lone
sheets 1.08–1.47 at half and 2.00–2.22 at full.

Notes: `docs/releases/RELEASE_2_1_9.md`. Suite: 72 of 72 modules.

---

## Phase 15i - The model beside a transfer, art beside a pool ✅ (v2.1.10, done 2026-09-02)

**The 3D column, over the transfer composer** (`web/js/transfer.js`, `cmpPrev*`).
The third host for `v3Mount`, after the unit editor's column (15e) and BMDB's.
A transfer is a decision about MODELS - which soldier entry crosses, whether the
officers come with it, which destination unit is the right one to replace - and
all of them were being taken off a name in a dropdown. Written as a copy of the
editor's shape rather than a refactor of the two into one: they differ in what
they list, which mod they draw it from and which setting turns them off, and the
part that is genuinely shared is `v3Mount` itself.

**It lists BOTH MODS**, which nothing else does: the source unit's entries and,
once a base or replaced unit is picked, that unit's own out of the DESTINATION,
each `<optgroup>` labelled and the mod handed to `v3Mount` per entry. The list is
derived from the unit LIST's fields - the composer never loads a unit detail -
with the editor's `armour_ug_models` rule applied on top and men ordered before
officers, since `model_names()` reads the soldier line first and a unit whose
soldier line was dropped would open on its standard bearer.

The column is given up - context, draw loop and node - by `closeModal`, by
`doApply` before the progress card takes the modal, and by `openComposer` before
it rewrites the modal; `v3Open` detaches it before stashing the modal as markup,
for the reason it already detached the editor's.

**Building art on the Recruitment tab**, and the culture problem underneath it.
`/building_icon` is keyed by culture; this tab is not showing one. The row's own
`requires` answers it through `ov.faction_cultures`, and for the rest
`buildings.find_icon` gained an opt-in `any_culture` sweep over the mod's other
culture folders (`&any=1`) - because a mod-invented level like DaC's
`ancestral_dun` is drawn for exactly one culture and every other row would have
been a placeholder. It stays OFF for the building browser, which is showing one
culture on purpose.

**The pool row re-cut as two halves.** The tier moved against the building's
name and art; the `requires` clause moved to the right of its own line, ending
where the numbers and the row's buttons do. `.erb` stopped growing, which is
what had been pushing the tier to the far end of the row's slack, and the header
now reserves the button column so its labels sit over the boxes they name.

- **Exit:** met. `tests/test_buildings.py` §11 - four checks on the sweep against
  a planted two-culture art tree - plus an `&any=1` route check in
  `test_buildings_http`. Verified in-browser against DaC and Reforged: a
  Dunlending unit's tiers all resolve to `mod` art where the browser's culture
  gave placeholders for every one; the composer's column draws entries from both
  mods, survives a re-render without refetching, folds, hides and is dropped
  clean on close.

Notes: `docs/releases/RELEASE_2_1_10.md`. Suite: 72 of 72 modules.

---

## Phase 15j - Resizable panels, the strings warning, no em dashes ✅ (v2.1.11, done 2026-09-03)

**Every panel takes the size you drag it to** (`web/js/core.js`, the `rsz*`
block beside `splitInstall`; `::-webkit-resizer` and `.drawergrip` in
`index.html`). Every scroll box gets `resize:vertical`, the dialog gets
`resize:both`, and the drawer gets a hand-rolled left-edge bar because its right
edge is pinned and the browser's own corner would drag it off the screen. Sizes
live in `pane_sizes` on `/api/settings`, keyed by a box's `id` or its classes
and a dialog's class, and clamped to the window on the way back in.

**The boxes find themselves.** A scroll box in this stylesheet is a rule that
sets `max-height` and `overflow:auto` together and there is no second kind, so
`rszSelectors` reads `document.styleSheets` once at startup and collects the 31
selectors that do - which means a list written next month is resizable the day
it is written. `.wpop` is skipped (a menu that closes on the next click must not
carry a remembered height) and `.modal` is skipped because `rszModal` sizes it
in both directions instead.

**Two things the browser gets wrong on its own, and most of the code is undoing
them.** A `max-height` outranks the `height` a drag writes, so the ceiling is
cleared on `mousedown` in the corner, in the **capture phase** - the last moment
before the browser starts its own drag. Without that, the first drag on any box
did nothing and only the second appeared to work. And these screens rebuild
wholesale (a keystroke in the pool filter replaces every row), so a
`MutationObserver` on `document.body` puts the size back on the element that
replaced the one that was dragged. That observer coalesces on a **`setTimeout`,
not `requestAnimationFrame`**: a window the OS considers occluded is given no
frames at all, and a dialog opened behind another window came up with none of
its boxes wired. Nothing is touched until it is dragged, so an untouched screen
lays out exactly as before.

**"`<name>.txt` is newer"** (`web/js/strings.js`) was a comparison of two file
dates presented as a warning, with no statement of what was wrong. It now reads
"…is newer than this `.bin`" and carries a `qm()` card: the game reads the
`.bin`, the `.txt` was saved after it was built, so what the `.txt` has been
made to say since is not on screen in the game - which is usually how the mod
was written and not a fault at all.

**No em dashes.** 4176 of them across 171 tracked files, swept to plain hyphens
in one pass; every occurrence was ` - `, a dash left at the end of a wrapped
line, or a lone dash standing for "nothing here", and a hyphen is right for all
three. `dev/checks/prose_check.py` grew `ANY_EM`, which scans whole files rather than
UI strings, so one that comes back is a reported hit.

**Also in the build:** battle-model-entries-only transfers (`models_only`,
`GET /api/unit_models`, `transfer.unit_model_index`), a swatch-plus-hex colour
picker on the faction editor that no longer closes the OS picker on every drag
through the gradient, a player-visible name for a newly cloned unit
("`<name>` (new)"), and the OS folder dialog raised to the front from a watcher
thread instead of opening behind the browser.

- **Exit:** met. `test_web_modules` 10/10, and `dev/checks/prose_check.py` reports 0
  em dashes where it had 4176. Verified in-browser: pin a size, save it, survive
  a wholesale re-render, reopen at the saved size, double-click to reset, and a
  dialog opened behind another window comes up with its boxes wired.

Notes: `docs/releases/RELEASE_2_1_11.md`. Suite: 72 of 72 modules.

---

---

## Phase 16 - Campaign Map Editor - V3.0.0 - the eleven sub-phases

Scoped from four reference tools into eleven sessions and finished in eleven,
2026-09-03 to 2026-09-05. The *preamble* to this phase - the four references,
the Pillow-not-C++ measurements, the banked format knowledge and the module
layout - stays in `ROADMAP.md`, because it is reference a session still reads
before touching a map module. What follows is what each sub-phase did.

### Sub-phases, each one session with its own exit

- **16a - The map files, read.** ✅ **done 2026-09-03.** `campmap.py` (990
  lines), `maptga.py` (310) and `mapvocab.py` (259), with `tests/test_campmap.py`
  at 62 checks (16d widened the probe's), all passing on DaC. `descr_terrain.txt`; all ten layers through
  Pillow with the size relationships checked from headers alone; the colour
  vocabularies, with climates read out of the mod because every mod renames
  them; `descr_regions.txt` in every form with each field carrying its source
  line index; the region index; the three coordinate systems.
  Exit, measured: 202 unique region colours, 199 settlement pixels, 77 port
  pixels; `descr_regions.txt` re-serialises byte-exact including CRLF and tabs
  (198 records, 197 of them in the `legion:` form); region IDs contiguous 0-199
  and identical across two independent reads; every port resolves to an owner;
  all ten TGA layers re-encode byte for byte. Reforged is not installed here, so
  the suite runs over every installed mod that has a `world/maps/base` and says
  so; the DaC numbers above are asserted by name.

  **Four things found by measuring, all of them now in this roadmap's preamble:**
  the exact-label-image correction above; the extension-area offset trap in
  `water_surface.tga`; `map_climates.tga` carrying five colours no climate
  declares (10 pixels, all one-channel misses of a real climate, from a lossy
  paint); and a genuine hole in DaC, a 517-pixel region at image (318,54)-(372,68)
  painted `(100,160,100)` - one channel off `Dunland_Province`'s `100 150 100` -
  which `descr_regions.txt` never declares and which has a settlement pixel
  standing in it at image (339,65). All four are 16f test cases and the index
  reports them rather than papering over them.

  **One inference is ours, and is flagged as ours in the source.** DaC's port at
  image (75,107) has its dock west and a *settlement pixel* on the land side, so
  TWMapReader's rule returns black rather than a region colour. The port is
  resolved through that marker to the region the settlement belongs to; no
  source states this, but a port attached to the settlement beside it beats a
  port attached to nothing. Without it, 76 of DaC's 77 ports find an owner.

  Also done here: the `stratmap.py` line in this roadmap is corrected (below),
  and `edbvocab.regions()` now delegates to `campmap.parse_regions` instead of
  keeping a second parser for the same file - its own copy found the resource
  line by looking for the first comma, which is right until a region carries a
  single resource.

- **16b - `descr_strat.txt`, read.** ✅ **done 2026-09-03.** `campstrat.py`
  (895 lines) with `tests/test_campstrat.py` at 75 checks, all passing. Faction
  rosters, faction blocks, settlements with their building lists, characters
  (including DaC's `hero_ability` and `label`, and vanilla's
  `character sub_faction <faction>, <name>, …` prefix), armies and units, forts
  in both forms, watchtowers, resources, `relative` lines, `character_record`,
  `faction_standings`, `faction_relationships`, the regions section and the
  campaign globals. Every node carries its line span and every field the index
  of the line it came from.
  Exit, measured: DaC's file parses **in one pass in 144 ms** into 6,100 nodes -
  31 factions, 199 settlements, 1,044 buildings, 305 characters, 286 armies,
  1,468 units, 161 character_records, 79 relatives, 812 standings, 57
  relationships, 126 regions, 105 forts, 295 watchtowers, 1,131 resources - and
  **round-trips byte-exact**, as do both of vanilla's campaigns. Every
  settlement and every character resolves to a faction: 199 of 199 and 305 of
  305, which is the sidebar bug fixed at the data layer.

  **The interval index needs no sort.** A node is appended the moment its first
  line is read, so `StratFile.nodes` comes out of the parse already in document
  order and a block plus everything inside it is contiguous. `node_at` is a
  bisect and a walk up the parents; `descendants_of` is a bisect and a slice, so
  "every unit in this faction" costs nothing.

  **Three pieces of format knowledge this session added.** `undiscovered` is a
  faction flag, found in vanilla on the Aztecs, who do not exist until somebody
  sails far enough west; `character sub_faction <faction>, <name>, …` is a real
  character form and the reason a positional read of that line fails; and brace
  depth has to be counted on the line **with its comment stripped** - Mylae's
  `factionBlockOps.js` has the depth rule but counts braces on the raw line, so
  a commented-out brace shifts it.

  **Nine lines in DaC do not parse, and all nine are the mod's own defects**:
  a trailing comma (3747), Sauron with no `age` at all (5376), `settlement
  tyuiop` (8464), `named character, general` twice over (9703, 10438), `rmour`
  for `armour` three times (9983, 10947, 10948) and a truncated `weapon_lv`
  (10581). Vanilla's two campaigns have none. Every one is read as far as it can
  be, kept in the tree, and reported by line number for 16f.

  **One caveat, stated rather than hidden.** Neither vanilla campaign contains a
  single `fort`, so the vanilla `fort <x> <y>` form is exercised only by the
  synthetic half of the suite; DaC's 105 forts are all the long form.

- **16c - Renderer core.** ✅ **done 2026-09-04.** `web/js/campmap.js` (834
  lines), the map's view in `campmap.py` (+300) and two routes in `server.py`,
  with `tests/test_campview.py` at **50 checks, all passing** over vanilla's map
  and DaC's. The first sub-phase with any UI in it.

  **The two routes.** `/api/map` is one manifest - the tile grid, all ten layers
  with what is wrong with each, and the region table - and `/api/map/layer` is
  one layer as PNG. Every layer that has a relationship to the tile grid is
  served **at one pixel per tile**, sampled the way the engine samples it
  (`2t+1` for a `2W+1` layer, `2t` for a `2W x 2H` one), so the composite is one
  canvas and a picked pixel is a tile. `water_surface` and `map_FE` have no
  relationship to the grid, so they come back at their own size and the manifest
  says `aligned: false` rather than pretending. PNGs are cached on disk keyed by
  the layer's mtime, through the same never-torn route the icons use, so 16e's
  next stroke is a miss rather than a stale picture.

  **Exit, measured on DaC in the real browser.** A pan frame is **0.02 to 0.18
  ms** from zoom 0.4x to 64x, against a 16.7 ms budget - one drawImage of the
  visible sub-rect out of a composite that pan and zoom never rebuild. A hover
  step, which repaints the cell the cursor left and the cell it entered and
  nothing else, is **0.046 ms**. The whole first read is 588 ms cold and 1.1 ms
  warm. **The picked pixel is exact**: 792 assertions over eleven zooms, four
  origins and both edges of a tile, all passing, and the zoom-about-a-point
  invariant holds in all twenty cases tried - the tile under the cursor does not
  move. Read back off the canvas at 24x, the centre of a settlement tile is
  `(0,0,0)` to the byte and its neighbours are the region's own colour, which is
  the off-pixel-placement anti-goal answered by measurement rather than by eye.

  **The claim the whole picking design rests on is now a test.** The browser
  reads the colour under the cursor off its own copy of `map_regions.tga` and
  looks it up in the manifest by packed key; no round trip, no second parser.
  That is only sound if the served PNG and the Python index agree pixel for
  pixel, so every region on every installed map is checked at its own anchor:
  116 of 116 on vanilla, 200 of 200 on DaC.

  **Vanilla's map is a second real map, and 16a never saw it** - it lives under
  the game root, not under `mods/`, so `_realmod.installed()` misses it. It is
  295x189 to DaC's 510x487, 116 regions to 200, and this suite runs on both.

  **The sea heuristic, measured rather than deferred.** One pass over the label
  image and the sea mask - 6 ms on vanilla, 43 ms on DaC - counts how many of
  each colour's tiles are sea, and it is what tells the ocean from a hole in the
  mod. **Vanilla has four colours `descr_regions.txt` never declares and all
  four are 100% sea**; three of them are one-channel misses of the ocean's own
  `(41,140,233)` - `(41,141,243)`, `(41,140,235)`, `(41,141,237)` - the same
  lossy-paint slips 16a found in `map_climates.tga`. DaC's ocean is 73,904 of
  73,950 tiles sea, and **its undeclared 517-tile province has not one sea tile
  in it**, which turns 16a's inference into a measurement. 16f owns the rule;
  this is the count it will be built on, and it is here because a screen that
  calls the Atlantic an undeclared province is not worth looking at.

  **Two faults found by writing the tests.** A layer the wrong shape used to
  come out of `_owner_of_port` as an `IndexError` and a 500: the sea mask and
  the label image are one byte per tile and index each other, so a 7x5
  `map_features.tga` on a 510x487 map walked off the end. `require_grid` now
  refuses by name and `view` degrades to the layer list, because the manifest is
  the only thing that will say *which* file to fix. And the map was being read
  through `Registry.get`, which warms the unit databases first - so a mod that
  ships only a map, or one whose roster is missing, could not have its map read
  at all. It reads through `describe` now, the same fix Home's readiness report
  got.

  **A dropped layer request is retried before it is believed.** Measured
  happening here: one of three layers asked for at once came back
  `ERR_CONNECTION_REFUSED` and the same URL answered 200 two milliseconds later.
  An `<img>` only ever learns *that* it failed, so after three tries the server
  is asked again for its sentence - and read as JSON only when the status says
  it is an error, because a 200 there means something else entirely.

  **Deferred to 16d, deliberately:** the layer set and opacities are not
  persisted yet, and `map_features.tga` / `map_trade_routes.tga` composite as
  what they are - opaque layers whose "nothing here" colour is black, so ticking
  one at 100% hides the map under it. Making a "nothing here" colour punch
  through is a legend decision, and the legend is 16d's.

- **16d - Layers, legend, inspector.** ✅ **done 2026-09-04.** `campmap.py`
  (+560), `web/js/campmap.js` (834 to 1,455), a `regions` kind in
  `codeview.py`, four routes in `server.py` and `tests/test_campedit.py` at
  **85 checks, all passing** over vanilla's map and DaC's. The screen stops
  being a viewer here.

  **The layer stack is remembered**, in `map_layers` on `/api/settings` - the
  `pane_sizes` road, and per user rather than per mod, because the ten layer
  codes are the engine's own and mean the same thing in every mod. A saved
  order is reconciled with the manifest rather than trusted: codes that are
  still real keep their place, anything new goes where the server put it, and
  nothing is dropped or invented.

  **16c's deferred item, answered by the legend.** `map_features.tga` is 97.7%
  black on DaC and 96.5% on vanilla, and black there means "nothing here", so
  ticking the layer at full opacity hid the map under a black sheet with a few
  rivers on it. `layer_legend` censuses the layer the browser was served, names
  every colour from the vocabularies and flags the one that means nothing;
  the browser punches that colour out of its own copy in one 4.4 ms pass, once
  per change of the hide set, and features and trade routes are overlays. The
  claim and its source live in one table, `BLANK`, and each entry says whether
  a reference states it or whether we measured it: `features` is the arbiter's
  own `none`; `trade_routes` is black because vanilla marks 995 tiles out of
  54,760 and DaC marks none at all; `roughness` is black because the layer is a
  magnitude; `fog` is white because that is 87% of vanilla's layer and 98% of
  DaC's, and **no reference in the folder says which way round the engine reads
  it**, which is said on the screen rather than guessed at. The four layers with
  a real vocabulary have no blank colour at all - black ground is `wilderness`,
  black heights is sea, a black region pixel is a settlement marker - so the
  checkbox is not offered for them.

  **The legend is also the region list.** The cap is 48 colours for a magnitude
  and the engine's own 200 for `map_regions.tga`, so DaC's 202 colours all list,
  each with its province name, its tile count and its share of the map. Any
  colour no table knows is listed as that - DaC's stray `(1,1,1)` feature pixel
  is visible on the screen now, not only in 16f's future report.

  **The probe names one tile on all ten layers**, localised name first and code
  name in brackets, in **0.17 ms on vanilla and 0.80 ms on DaC** warm - one
  small request on the click, not on the pointer, because the hover readout is
  answered in the browser and a round trip there is the thing this phase's rules
  exist to prevent. The two pictures say they have no value at a tile rather
  than being sampled at coordinates that mean nothing in them, and a layer the
  wrong shape says which file to fix.

  **The region record is editable, and an edit is one line.** Legion, creator
  faction, rebel type, resources, triumph value, base farming level and the
  religions, spliced into the line each field came from - asserted, not claimed:
  **all 198 of DaC's records and all 112 of vanilla's re-render byte-exact with
  no edits**, and one field edited changes exactly one line of a 1,990-line
  file, CRLF, tabs and the modder's own trailing comments intact. A missing
  `legion:` or resource line is inserted where the format puts it, at the indent
  its neighbours use. Three fields refuse a rename with the reason, in the form,
  in the text pane and at the plan: the region's name and the settlement's are
  keys `descr_strat.txt`, the win conditions, the campaign script and every
  `legion:` line point at, and the colour is the map's own pixels, which is 16e's.

  **The religion rule is enforced twice**, live in the form and again at the
  plan, because it is the one that crashes the game on load. A set that does not
  total 100 says by how much and is refused before anything is written.
  Warnings are separated from refusals with their sources: Geomod's "leave it at
  5" for the triumph value, "4 is average, 6-7 highly fertile" for farming, and
  16f's rule about a resource that is neither hidden nor a trade resource,
  brought forward to where somebody can fix it.

  Also here: neighbours from the label image (27 ms on DaC, four-connected,
  markers skipped, and the panel says land bridges are 16f's), Code View over
  `descr_regions.txt` with a span per field, Ctrl+Z over the working copy, and a
  save that backs the file up, writes the log entry the Log's Undo reverses, and
  **deletes `map.rwm`** - or the game loads the compiled map and shows none of
  the edit.

  **Two faults found by building it, both 16c's.** `cmapRepanel` re-ran the
  canvas's wiring as well as the panel's, so every layer ticked added another
  set of pointer listeners: measured at eleven, where a 10-pixel drag moved the
  map 110 pixels. 16c ticked rarely enough to hide it and 16d ticks on every
  legend opened. And the probe's row class `cmprow` was already the compare
  screen's, four hundred lines further down the same stylesheet, so its
  four-column grid silently won - the reason CSS names are now checked against
  the sheet the same way top-level JS names are.

- **16e - The paint tool.** ✅ **done 2026-09-04.** `campaint.py` (1,381
  lines), `web/js/campaint.js` (871), nine routes on `server.py`, `repixel` on
  `CampaignMap`, and `tests/test_campaint.py` at **95 checks, all passing** on
  a map the suite writes itself and on vanilla's, with six more per additional
  installed map. The screen stops being a viewer with an editable record and
  starts changing the map.

  **Python owns the bytes, and there is one set of them.** The browser draws a
  provisional trail under the cursor and posts the pointer samples; `campaint`
  expands them, snaps the colour, refuses what must not be written, applies it
  to *the layer image the whole server is already serving from*, and answers
  with the tiles that actually moved. The browser throws its trail away and
  writes that answer into its own copy. So the probe, the legend and the layer
  PNGs all show the unsaved map - there is no second copy of the pixels to
  disagree with the first - and a disagreement between the preview and the file
  cannot outlive one pointer-up. `CampaignMap.repixel` is the other half of
  that: the decoded image and its header stay, everything derived from them
  goes, and the index, the sea mask and the adjacency are dropped only when a
  layer that feeds them moved.

  **Region-colour snapping is a name, not a colour.** A stroke on
  `map_regions.tga` sends the region's NAME; the server writes that record's own
  RGB. Drift is impossible, the palette for that layer is the region list, and
  the two marker colours cannot be produced by a brush at all - they are placed
  one tile at a time by the wizard, and a stroke that would cover one skips it
  and says how many it protected.

  **The block is what a tile owns, and the blocks partition the layer exactly.**
  Three layers are one pixel per tile; the rest are 2W x 2H or 2W+1 x 2H+1, and
  a tile there is a rectangle. `block()` is that rule, asserted pixel by pixel:
  every pixel of an aligned layer belongs to exactly one tile, the `2W+1`
  layers' leading row and column included - otherwise nothing owns them and a
  painted coastline keeps a one-pixel seam of the old map along two edges - and
  the pixel the engine samples is always inside its own tile's block.

  **Unlimited undo, because a stroke is one colour.** Every tool writes a single
  value per layer, so a stroke is a tile list plus one RGB rather than a bitmap,
  and the stack holds pixel deltas in an `array("i")`. Geomod has one level,
  Mylae keeps one snapshot of the layer and Demir has none, and all three are
  paying for a model where a stroke could have been anything. Backwards is not
  "paint the old colour over it": the pixels a stroke covered were not all one
  colour, so the old value is stored per pixel and put back per pixel, which is
  what makes an undo byte-exact rather than merely plausible. The one bound is
  memory (`UNDO_BUDGET`), and the panel says when it bites.

  **The water brush measures rather than assumes.** Demir writes a hard-coded
  triple per layer, which is right for one mod and wrong for the next: the sea
  colour on `map_regions.tga` is declared in no record, so it is whatever the
  author used, and vanilla and DaC do not agree. So it is the commonest colour
  among the tiles the engine calls sea, per layer, with the count beside it on
  screen - vanilla measures `(41,140,233)` / `(0,0,253)` / `(196,0,0)` from
  20,012 sea tiles.

  **The palettes are closed where a table exists and open where a rule does.**
  Regions, ground types, features and climates are held to their vocabulary and
  a colour outside it is refused by name, because an unknown colour on
  `map_ground_types.tga` is precisely what 16f exists to report and a tool that
  can create one manufactures its own bug reports. Heights, roughness, fog and
  trade routes are magnitudes, so their palette is the map's own colours and the
  rule that governs them is said on the screen.

  **The wizard's steps are questions about the pixels, never a counter.** How
  many tiles carry this colour, is there a settlement pixel this region owns, is
  there a port - counted every time, so the panel cannot claim a step is done
  when the map says otherwise. Marker ownership is Gigantus's cardinal rule, the
  same one `_owner_of_marker` gives the index, with the pending region counted
  as a region: proximity would have reported the city next door as this one's.
  The rules enforced: name and settlement name free, colour free and not a
  marker, contiguity, Mylae's touching-a-declared-region rule, the settlement on
  one of its own tiles and not on sea, impassable ground or a
  river/ford/source/volcano, religions totalling 100, a creator faction present.
  A save also refuses to leave any region with no tiles at all, and warns that a
  new province renumbers every region the engine scans after it.

  Also here: `descr_regions.txt` gets the new record spliced in front of a
  wasteland entry rather than after it (the arbiter says a settlement-less
  record must be last), in the file's own indent and `legion:` form; every
  painted layer, the record and `map.rwm` go into ONE backup set, so the Log's
  Undo reverses the whole save; and a plan compares BYTES rather than stroke
  counts, so painting and then undoing back to the start saves nothing.

  **Two things found by building it.** A session holds the `CampaignMap` it
  painted, and the registry drops that object when a file the map was read from
  changes on disk - so a layer edited in Photoshop under unsaved strokes ends
  the session, and every answer from then on carries `reset` saying so rather
  than a fresh session appearing silently under somebody's hand. And vanilla's
  `map_fog.tga` does **not** re-encode byte for byte: whatever packed it wrote a
  five-pixel literal where `maptga._rle_row` starts a run, so ours is 11,327
  bytes against 12,009, pixel for pixel identical and settled on a second pass.
  RLE has more than one legal packing of a row; 16a's claim was byte-for-byte
  and the true one is the shape and the picture, which `maptga`'s docstring and
  `test_campmap` now both say.

- **16f - The validator.** ✅ **done 2026-09-04.** `mapcheck.py` (1,567 lines),
  `web/js/mapcheck.js` (387), four routes on `server.py`, and
  `tests/test_mapcheck.py` at **82 checks, all passing**. **30 rules**, each one
  carrying the tool, manual or measurement that says it is a rule, and each one
  with a deliberately broken map under test that only it may catch. The whole
  set runs on DaC in **609 ms**, on vanilla in 120 ms.

  **A rule with no evidence reports nothing**, and that is the decision the
  phase turns on. The stock game's `data/` is packed: `descr_climates.txt` is
  not on disk, neither is the region and settlement name file. A checker that
  reads "no climate is declared" as "every climate colour is undeclared"
  reports 11 faults, 55,755 tiles and 112 missing name keys against the map
  that ships with the game and works. So a rule that needs a vocabulary asks
  for it first and, when it is not there, puts a line in `skipped` naming the
  file that would let it run. Absence of the evidence is never the finding.

  **A finding is identified by what it is about, never by where it is
  written.** The fingerprint is the rule, the file and the thing - a region's
  name, a tile's coordinates, a resource's name and position - so inserting a
  comment above a finding does not make it a new one. That is what makes the
  baseline real: `take_baseline` stamps what a mod already had, those rows stay
  visible and counted, and only what appears afterwards blocks a save. A mod is
  somebody else's work with somebody else's bugs in it, and vanilla's own map
  has 62 findings.

  **Vanilla is a better exit measurement than the one this phase was scoped
  with, and it found the bug the fix is named after.** `map_heights.tga` has 55
  tiles painted pure black where `map_ground_types.tga` says land, and
  `is_sea_height` has to read black as sea because the engine does. Two of those
  55 have a port standing on them: **Nottingham's, and Ragusa's** - the port bug
  Geomod's manual names its debugger action after, shipped in the stock game and
  reported here by name and coordinate. `heights_black` is Geomod's own fix:
  black becomes `(1,1,1)`, land beyond argument, 77 pixels over 55 tiles, and
  the picture does not change.

  **A rejoin is a loop, not a junction.** Vanilla has 26 river tiles with three
  cardinal neighbours and every one is an ordinary tributary, so degree is not
  the rule. A rejoin is a cycle in the four-connected river graph, found as the
  edge that closes it by one union-find pass. Vanilla has none, which is the
  zero the rule was checked against.

  The rule set: layer shapes and the 200-colour cap; duplicate, reserved and
  zero-pixel region colours; undeclared land with 16c's sea heuristic; every
  field rule 16d's `check_record` already enforces (the religion total, the
  triumph value, unknown rebels, factions and resource tags); a settlement-less
  record that is not last; regions with no settlement pixel, second markers,
  orphaned markers, a marker on blocking ground, on a river-ford-source-volcano
  or on a tile the engine reads as sea; ports with no water beside them;
  colours no feature, ground or climate table names; diagonal-only rivers,
  isolated river tiles and rejoins; ambiguous altitudes; every line
  `descr_strat.txt` will not parse; a faction block after the diplomacy
  section; duplicate resources and resources off the map or in the sea; a
  settlement in a region nobody declares; a region no settlement block claims;
  a port building with no port pixel; and missing localisation keys.

  What it finds on the two real maps, all of it real: **DaC** - the stray
  `(1,1,1)` in `map_features.tga` this phase was scoped to catch, five port
  pixels standing on Sea Deep or Impassable, the orphan settlement at (339,65)
  16a found, the 517-tile province at `rgb(100,160,100)` nobody declares, a
  settlement placed in `Erebor_Province` which `descr_regions.txt` does not
  declare, **63 duplicate `resource` lines**, and the nine unparseable lines 16b
  wrote down. **Vanilla** - the two ambiguous ports, one river tile at (175,14)
  with no course through it, a `timber` at 199,57 sitting in the sea, and
  Durazzo, which no settlement block claims.

  Every fix goes through the same route a paint save does: one backup set, one
  log entry, `map.rwm` deleted when a layer moved, so the Log's Undo puts every
  fixed file back byte-exact. The plan re-runs the rule rather than trusting the
  list on screen, so a fix can never act on a finding that stopped being true
  since the report was drawn. Line deletions are applied bottom-up.

  **The four marker rules exist once**, as this phase's brief required.
  `mapcheck.marker_faults` is the predicate - a marker on blocking ground, on a
  fatal feature, on a tile the engine reads as sea, a port with no water beside
  it - and `campaint._marker_problems` is the new-province wizard's view of the
  same function rather than a second copy of it. Two differences are deliberate
  and written down where they are made: an inland port is a warning while
  somebody can still move the pixel and a fatal once it is on the map, and a
  port on sea GROUND is a warning rather than a crash, because 142 of the 142
  port pixels on the shipped maps measured sit on land ground and DaC ships five
  that do not and runs anyway.

  **The measurement was fixed before the thing it measured, again.**
  `dev/checks/prose_check.py` opened at 49 hits on this module and every one was the
  reader: it stitches `+`-joined continuations because that is what JavaScript
  writes, and Python joins adjacent literals with nothing at all, so every
  second line of a wrapped message was flushed as a sentence of its own. It also
  measured the code inside an f-string hole as prose, reporting
  `{len(tiles) - ROW_MAX:,}` as a clause-joining dash. Both are fixed in the
  checker; the standing JavaScript measurement is unchanged at 29, and this
  module is at 2, both of which are correct as written.

- **16g - Query, highlight and information maps.** ✅ **done 2026-09-04.**
  `mapquery.py` (1,934 lines), `web/js/mapquery.js` (581), four routes on
  `server.py`, and `tests/test_mapquery.py` at **90 checks, all passing**.
  **24 filters** - all fourteen TWMapReader asks for plus religion majority,
  religion share, settlement level, city-or-castle, population, triumph, size in
  tiles, name and "no settlement pixel" - three themes with political borders,
  and **93 colourings on Third Age Reforged**: Geomod's nine fixed information
  maps plus one per hidden resource, religion and trade resource actually on the
  map.

  **One fact table, read by everything.** A filter, a theme, an information map
  and an export are four views of the same handful of sentences about a
  province, so they are joined once - `descr_regions.txt`, the region index,
  `descr_strat.txt` and the three small files nothing else in the toolkit read -
  and nothing below `Facts` opens a file. 199 provinces in **384 ms** on Third
  Age Reforged, 108 ms on vanilla, cached per (mod, campaign) on the registry
  and dropped when a campaign file changes on disk. Every filter after that is a
  dictionary lookup: the whole 199-province map answers a two-filter query in
  **0 ms**.

  **A rule with no evidence reports nothing**, carried straight over from 16f
  and measured on the same map. The stock game keeps `descr_sm_factions.txt` and
  `export_descr_buildings.txt` inside its packed data, so on vanilla the culture
  filter is **off with that file named** rather than empty, and a query holding
  it does not run it at all - under `all` it would empty the result, under `any`
  it would quietly widen it, and neither is an honest answer to a question that
  could not be asked. The building-tree filter survives the same absence,
  because `descr_strat.txt` writes `type <line> <level>` and the line name is
  already in the campaign file: 48 provinces on vanilla with no EDB on disk.

  **A theme and an information map are the same object**, so one `Colouring`
  builds the payload, one function writes the TGA and one draws it. The browser
  recolours the region layer it is already holding through a table keyed by the
  region's map colour - the same operation 16d's `cmapMask` does - and the
  border pass compares the GROUP each region is in rather than its colour, so
  two provinces of one faction get no line between them and the picture on
  screen and the file on disk agree about where a frontier is.

  **Two colour rulings, both measured against a real mod.** A faction keeps the
  colour `descr_sm_factions.txt` gives it, so the map reads the way the
  campaign's own does - unless something else on the map is already using it.
  Third Age Reforged declares `england` as `0 0 0`, which is exactly the
  settlement marker, and `france` as `37 37 37`, which at map size is the border
  line; nine of its twenty-nine factions are swapped for the fallback palette
  and the legend says which and what each clashed with, because a legend that
  quietly recolours a faction is lying about the mod in a quieter way. And every
  magnitude map runs along a **three-stop ramp**, not two: the first version was
  purple to yellow through one midpoint of its own, and Third Age Reforged uses
  farming levels 0 to 2, so the whole picture came out inside a few units of the
  sea behind it.

  Exports land in the cache, never in the mod - it is derived data about
  somebody else's files, and a tool that drops forty TGAs into
  `data/world/maps/base` has changed a mod nobody asked it to change - and each
  one is written in the shape of the mod's own `map_regions.tga`, round-tripping
  pixel for pixel. Geomod's batch writes one file per faction plus the map they
  are all on, in one call from one fact table, because forty exports taken over
  forty minutes are forty pictures of forty slightly different working copies.

  **Two things found by building it.** `values_of` counted occurrences rather
  than provinces, so a province with two vineyards made the count beside
  `trade_resource = vineyard` disagree with the answer the filter gave; it now
  counts each province once. And a resource is allowed to stand **on** a
  settlement or port pixel - the index does not answer for a marker tile,
  because a marker has no region colour of its own - so the region that owns the
  marker answers instead.

- **16h - `descr_strat.txt`, write: settlements and buildings.** ✅ **done
  2026-09-04.** `stratedit.py` (1,083 lines), `web/js/stratedit.js` (462),
  three routes on `server.py`, and `tests/test_stratedit.py` at **85 checks,
  all passing**. The exit criterion is the one 16b was built for and it is
  measured rather than argued: **316 settlement blocks across vanilla's two
  campaigns and Third Age Reforged re-render byte for byte**, with no edits and
  again with their own building lists handed back, and a real edit leaves the
  file identical outside the block it touched.

  **The ladder is one ladder and both kinds of settlement climb it.** `level`
  on a `settlement castle` is written with the same six city words - vanilla
  has 14 castles at `level village` and 21 at `level town` - and the castle's
  own tier is the level of its `core_castle_building` rather than the word on
  the `level` line. So the picker offers the six, and prints the castle tier
  beside them for somebody who thinks in mottes and citadels.

  **The first settlement in a faction block is that faction's capital**, which
  is what makes a change of owner a move rather than a rewrite. Nineteen of
  vanilla's nineteen landed factions have theirs first and nothing before it -
  London, Paris, Frankfurt, Leon, Venice, Palermo, Milan, Edinburgh,
  Constantinople, Novgorod, Cordoba, Iconium, Cairo, Arhus, Lisbon, Cracow,
  Budapest, Rome, Tenochtitlan - and the plan says whose capital moves on both
  sides of a transfer before it is saved rather than after it is played.

  **The EDB's settlement rules gate building, not starting.** Third Age
  Reforged ships **432 of its 1,518 starting buildings below the
  `settlement_min` its own EDB declares** for them, and **248 in the wrong kind
  of settlement altogether** - 27 merchant vaults, 25 conservatoriums and 24
  docklands standing in castles - and the mod loads and plays. Four of its
  settlements carry two or three levels of one building line at once. So
  `settlement_min`, `settlement_max`, the `city`/`castle` pin and the repeated
  line are warnings with that number beside them and never a refusal. What is
  fatal is a value the engine's own vocabulary has no room for: a level off the
  ladder, a settlement kind that is neither `city` nor `castle`, a population
  that is not a whole number, and a `type` line naming a level the EDB does not
  declare - that last one only when there is an EDB on disk to say so, which is
  16f and 16g's ruling carried into a third phase.

  **The plan reads back what it would write.** The block is spliced, the file
  is re-parsed and every check runs against the tree that comes out, so a
  hand-edited block with a brace missing is caught by the parse rather than by
  a rule written to expect it. A guard then compares the two trees: any count
  but the building count that moved, any roster or campaign global that
  changed, any *other* settlement whose text is not what it was, and the save
  is refused naming what it did that nobody asked for.

  **Two objects, and they are not interchangeable.** The form is built out of
  16g's fact table, which is a cache; the file the plan splices is re-read from
  disk inside `plan_settlement`. A writer that writes out of a cache writes
  over whatever changed under it. That division is stated where it is made,
  and it is the reason the panel can ask for a whole plan on a 450 ms debounce
  while somebody is still typing: the findings under the form are the findings
  the save would produce, not a browser's guess at them. A plan is 250 ms on
  the largest campaign installed and there is no copy of any rule on the far
  side.

  **`map.rwm` is not deleted here, and that is a decision.** 16d deletes it
  because it writes `descr_regions.txt`, which the compiled map is built out
  of. The campaign file is not, and it is read fresh every time a campaign
  starts, so deleting the binary would cost a recompile and change nothing.

- **16i - `descr_strat.txt`, write: characters, armies, family tree.**
  ✅ **done 2026-09-05.** `stratchar.py` (1,480 lines), `web/js/stratchar.js`
  (575), three routes on `server.py`, and `tests/test_stratchar.py` at
  **86 checks, all passing**. The gate is 16h's, on a bigger record: **479
  character blocks across vanilla's two campaigns and Third Age Reforged
  re-render byte for byte** with no edits, tabs, trailing spaces and the comment
  somebody left on a regiment included. Edit, add, delete and move are the same
  request with a different `action`, because in the file they are the same edit.

  **It is built on 16h rather than beside it.** Eleven helpers in `stratedit.py`
  were promoted out of the private namespace and are imported here: the line
  rewriter that keeps an indent and a comment, the assembler, the span mover,
  the serialiser, the finding shape. A settlement block and a character block
  are different records with one discipline, and a second copy of that
  discipline is a second chance for one of them to drift.

  **A character block already ends on the blank line after it**, which a
  settlement block does not: 16b closes a character at the next thing that can
  only start something else, so 216 of vanilla's 216 spans and 245 of Third Age
  Reforged's 246 end on their own separator. Moving one is therefore a straight
  slice, and the suite proves it the strong way - same line count, same multiset
  of lines, every other line identical in order, and the block that lands byte
  for byte the block that left.

  **The bodyguard-first rule is vanilla's habit, not the engine's rule.** This
  was going to be a refusal. Third Age Reforged has **213 characters with an
  army and only 14 that hold a unit the EDU marks `general_unit` anywhere at
  all**, never mind first; 199 lead armies with no bodyguard in them, and the
  mod plays. So it is a warning with that number on it, and only when there is
  an EDU on disk. **And the attribute is what is read, never the name**: that
  mod calls 19 units Bodyguard and marks 6, so its Gondor, Arnor, Dunedain,
  Lindon and Mithril Bodyguards are ordinary regiments as far as the engine is
  concerned, and a check that went by the word would clear all of them.

  **The two family constraints are real and real files break them.** A living
  parent should be sixteen years older than a child: vanilla breaks it once, on
  Egypt's Al-Zahir at 60 with Al-Mustansir at 45. Children should be oldest
  first: vanilla breaks it twice, on Philip's four and Heinrich's three. Ages
  are only comparable between the living, because a dead ancestor's `age` is the
  age they died at. Both warn. So does a second leader in one faction, a family
  line naming somebody who is not in it, and two characters of one name - which
  five of Third Age Reforged's factions have, and which matters because a
  `relative` line addresses people by name and nothing else.

  **Fatal is what the engine's own vocabulary has no room for**, 16h's ruling in
  its fourth phase: a type that is not one of the twelve, an age or a coordinate
  that is not a whole number, a tile off the map, and a unit, trait or ancillary
  the mod's own file does not declare, that last only when the file is on disk.

  **A new record is written in the shape of the one beside it.** The three
  campaigns do not agree on their own whitespace - vanilla puts a trailing space
  on 215 of 216 character lines and the prologue on 9 of 17, and the padding
  between a regiment's name and its numbers runs from two tabs to five - so the
  separators are read off the nearest line of the same kind rather than decided
  here, and a regiment is padded like every other copy of that same unit.

  **Two things found by building it.** `character_record` carries a
  `current_heir` that 16b's four leadership words did not cover, so three of
  Third Age Reforged's records came back with no leadership at all; `campstrat`
  now names all six. And `rewrite_line` was trimming trailing whitespace, which
  no settlement field had and 215 of vanilla's 216 character lines do.

- **16j-1 - `descr_strat.txt`, write: the campaign's own settings.**
  ✅ **done 2026-09-05.** `stratcamp.py` (1,303 lines), `web/js/stratcamp.js`
  (467), three routes on `server.py`, and `tests/test_stratcamp.py`. What is
  left at depth zero once 16h has the settlements and 16i the people: the
  campaign header, the three rosters, the diplomacy section, and a faction
  block's own scalars. **Five saves and one endpoint**, because in the file they
  are one file - `globals`, `rosters`, `standings`, `relationships`, `faction`.
  The half that only ever rewrites lines that are already there; creating a
  faction is 16j-2.

  **The gate is the diplomacy matrix: all 99 faction rows across the three
  installed campaigns re-render byte for byte** - the three tabs after `hre,`,
  the five spaces before Third Age Reforged's `1.00`, its habit of restating
  that value in front of every target, and the tab left hanging off the end of
  the line, all included.

  **A standings line is a list of pairs and the value is sticky**, which had a
  bug under it. The grammar is `faction_standings <who>, <value> <faction>[,
  <value> <faction>]…` and a target with no number in front of it takes the last
  number stated. Vanilla never repeats the value - 46 lines of 46 - so the old
  reading, first number then a list of factions, was right there by accident.
  Third Age Reforged repeats it on nearly all of its 204, so Sicily held an
  opinion of a faction called `1.00` and its opinion of Milan was gone.

  **A row's lines are its shape, not just their whitespace.** Grouping the cells
  by value and writing one line each looked right and rewrote 13 rows nobody had
  touched: vanilla puts Egypt's two -0.6 opinions on separate lines and Third
  Age Reforged gives the Aztecs twelve lines all reading -1.00. Each existing
  line keeps the targets it still has, a line that empties leaves its slot for
  whatever moved into that value, and the file's own order of `allied_to` and
  `at_war_with` wins over any order this phase would have picked.

  **The guard is the strongest of the three write phases, because all five edits
  are region-local.** A save declares the runs of the file it may touch and
  every difference between the file that went in and the one that came out has
  to fall inside them, by line number. That check is affordable only because the
  identical head and tail are trimmed before anything is diffed: on 11,063 lines
  that is four milliseconds instead of four seconds.

  **One word in the header was being dropped without a word.** Third Age
  Reforged writes `marian_reforms_activated`, which the engine does not read,
  and the campaign header is the only region of the file where an unrecognised
  line has no open block to record itself on - so it vanished at parse and would
  not have survived an edit. `campstrat` reads it now and `stratcamp` reports it
  as the dead line it is.

- **16j-2 - A faction's campaign entry, and the win conditions.**
  ✅ **done 2026-09-05.** Two more saves on `stratcamp.py` (`create` and
  `delete`, taking it to 1,681 lines), `winconds.py` (781), two more tabs on
  `web/js/stratcamp.js` (753), three more routes on `server.py`, and
  `tests/test_stratcamp.py` at **107 checks, all passing**.

  **The gate is that a faction made and then unmade leaves the file byte for
  byte as it was** - the block, the blank line that separates it, its place in
  a roster, its own diplomacy rows and every other faction's line that named it
  - on all three installed campaigns.

  **The one file `factionclone` would not touch.** Phase 11's cloner does twelve
  files and says in as many words why `descr_strat.txt` is not one of them: a
  faction's campaign entry is a settlement, an army and a family tree, and two
  factions cannot start in the same city. That ruling stands and this is built
  on it rather than against it. **A new faction gets the donor's AI, label,
  purse and diplomacy and nothing else** - no settlement, no character, no
  coordinate - and the plan says so by name: it is the shape vanilla's Mongols
  and Timurids already are, which is why that is a warning and not a refusal.
  16h hands it a city and 16i hands it a general.

  **Deleting refuses while the faction still holds anything**, and names what:
  three settlements and twelve characters for vanilla's England. Taking a block
  out would take them with it, and the two panels that move them already exist.

  **The guard stopped being a diff.** Every run a save declares now carries a
  third number - how many lines it puts back - and the two files are walked side
  by side instead of compared. That is what made a whole-faction save affordable:
  it touches the roster on line 4 and the diplomacy section on line 10,800, so
  there is no small middle to trim to, and `difflib` took **four seconds** over
  it. The walk is linear, it is exact, and it does not have to guess which of
  several equivalent places a blank line was meant to go. **113 ms** on the
  largest campaign installed.

  **`descr_win_conditions.txt` was the last file in the campaign folder nothing
  could edit.** 16g reads it already, to answer which factions a province is in
  the win conditions of; `winconds.py` writes it, as the fourth file in the
  project to be lines plus an index over them. Two things it is built on:
  **`short_campaign` is a switch, not a line** - it prefixes whichever short
  condition comes first, and computing that off the first *stated* slot rather
  than the first *written* one put two of them in one record; and
  **`hold_regions` with nothing after it is a real line**, which 45 of the 74
  real short campaigns write, so the switch stays on it when its provinces go.
  Vanilla's file keeps its 21 comments through an edit, including the
  `;take_regions 35` somebody left commented out mid-record.

  **Name pools needed nothing.** `descr_names.txt` is already read and edited by
  `minorfiles.py` and already cloned per faction by `factionclone.py`; a third
  copy of it here would have been a third chance for one of them to drift.

  Exit: a faction is created on a test mod, lands before the diplomacy section,
  joins a roster and inherits the donor's diplomacy both ways; the
  faction-block-before-diplomacy rule is enforced twice, by `mapcheck` since 16f
  and by this phase's guard on the file it is about to write, before it writes
  it.

- **16k - 3D strat preview and the `.cas` decoder.**
  ✅ **done 2026-09-05.** `unittransfer/cas.py` (752 lines), three routes on
  `server.py`, a strat branch through `web/js/viewer3d.js`, the picker in
  `web/js/stratview.js`, and `tests/test_cas.py` at **45 checks, all passing**.
  Every note 15a left at the bottom of `mesh.py` turned out to be right, and
  none of it was the hard part.

  **A `.cas` is a chunk list, and the meshes are one chunk kind of five.** That
  is the thing the roadmap did not know and the thing everything else follows
  from: there is no single vertex pool and no single object, so a settlement is
  three named meshes with a material each in one file, and vanilla's northern
  castle is its walls, its buildings and a faction banner. Sizes are absolute,
  which is what makes the read checkable - the chain has to land exactly on the
  end of the file, and on **472 of the 484 models installed** it does.

  **Every file has all five chunk kinds, empty ones included**, and that is how
  the rest was pinned down: a static model still carries an empty *skinned*
  chunk and a skinned one an empty *static* chunk, so the two trailer lengths
  are readable off a 16-byte chunk rather than guessed at.

  **The header is two bytes off the 32-bit grid, and two RGB triples are why.**
  Six bytes of colour in the middle of a run of 32-bit fields puts the node
  count at 0x32 rather than 0x30, with two pad bytes after it to put the parent
  table back on the grid. The proof that it is being read where it really is:
  the parent table reads as a skeleton, giving `bone_pelvis` the Scene Root,
  `bone_Rlowerleg` the `bone_RThigh` and the three cloak bones a chain.

  **The material index was nearly missed.** It sits between a mesh's indices
  and its UVs, reads 0 in three quarters of all meshes, and would have passed
  for padding - except that a settlement has three meshes and three materials
  and nothing else in the file says which wall gets which texture. On
  `evil_men_huge_city.cas` it hands four meshes materials 2, 1, 3 and 0.

  **A `.cas` is painted from ONE sheet and its UVs are not doubled**, which is
  the plain difference from a `.mesh` and the thing habit would have got wrong.
  So `v3Apply` asks `v3.cas` first, and the draw loop binds per group instead
  of once for the model.

  **The viewer is Phase 15's, unchanged.** `cas.as_mesh` lays a scene's meshes
  into one pool and hands back a `MeshFile`, so `geometry_payload` serves a
  settlement without knowing what a `.cas` is. What is different is the framing
  - a settlement is wider than it is tall, and the figure's fit put the camera
  inside its own courtyard - and the file itself says which of the two a model
  is, because a person has a skeleton and a building does not.

  **Twelve files do not decode and each says why by name.** Six are stamped
  version 2.19 or 2.23 and lay their header out differently, three are Third
  Age settlements whose own chunk size points past the end of a chunk, two are
  zero bytes long, one is a material chunk a byte short of what it claims. Not
  one is a model read wrongly and kept. A chunk that goes wrong loses that
  chunk and not the file, which is what lets `se_fort.cas` name its problem -
  a `CaozSceneCustomAttribNode`, a 3ds-max attribute holder whose record runs
  to a length nothing states - instead of dying on it.

  Exit met: settlement and character strat models render and orbit correctly,
  checked in the browser on vanilla's northern European castle and fancy
  general and on Third Age's dwarven castle.

---

## Phase 17 - The campaign map correction pass - shipped 2026-09-06

Eight items the user raised after using 16a-16k end to end, all eight done in
five commits (`373590d`, `079c14a`, `7d4b242`, `8f77c30`, and STATE in
`a36330c`). Every one was verified in a running browser on **both** installed
maps - Third Age Reforged and Divide and Conquer - which is what 17i asked for.
The scope as it was written is kept below the write-up, verbatim.

**17a - Home was missing the Campaign Map card.** `modfiles.MODULES` still
listed the ten V2 modules, so `report.modules['campmap']` was undefined and
`home.js:230` dropped the card with no error, on every mod. `campmap` is
declared now with fourteen files in `KNOWN`: `descr_terrain.txt`,
`descr_regions.txt` and the ten layers under `world/maps/base` as the map half,
carrying the same `required` flags `campmap.LAYERS` gives them, and
`descr_strat.txt` and `descr_win_conditions.txt` as the campaign half a map-only
mod may not have. A mod with no `world/maps/base` reports the module blocked and
names the seven files it needs. The rows are spelled out rather than imported so
that drawing a mod card does not cost a Pillow import, and `test_web_modules`
holds the two lists against each other. It also asserts **every non-`sub` entry
in `MODES` has a `MODULES` entry**, which is the class of bug rather than this
instance of it, and is the only reason this one survived a whole phase.

**17b - the hover box left a trail of pixels.** Not the readout box at all: a
dirty rectangle is worked out in CSS pixels and the canvas is backed at
`devicePixelRatio`, which at 150% Windows scaling is 1.5, so every rectangle
edge landed half way through a device pixel and the antialiased clip kept half
of the frame before it. Measured by diffing a dirty-rect frame against a full
repaint of the same view: **1,330 residue pixels over two pointer sweeps, and 0
after** the rectangle is snapped outwards to whole device pixels. Re-measured on
DaC with the markers layer on and off: 0 both ways. The fix costs at most one
pixel of extra repaint per edge and removes the class of fault rather than the
hover box's instance of it.

**17c - not every region was clickable.** Diagnosed rather than guessed: a
settlement pixel is black and a port pixel white, neither is a region colour,
and both are excluded from the region-id scan - so the colour under the pointer
named no region and the panel said "no region record on this tile" while the
pointer was on Minas Tirith. **199 of Reforged's 200 settlements and all 65 of
its ports behaved that way; 198 and 78 on DaC.** The marker now answers with the
region that owns it, out of the manifest's own pairing, and all 200 region
anchors still resolve on both maps. A marker no region claims says so - that is
`findings.orphan_settlements` made visible where somebody is clicking. The
remaining case is a province too small to hit: `Edhellond_Province` is two tiles
on Reforged, and Query's Go is how it is reached.

**17d - the markers layer** (`web/js/campmark.js`, `cmk` prefix;
`campstrat.markers`, `mapquery.marker_view`, `GET /api/map/markers`). Everything
in `descr_strat.txt` that stands on a tile: settlements by level and kind,
characters by type, forts, watchtowers and trade resources. **855 markers on
Reforged in about 110 KB, 2,035 on DaC**; 197 Reforged tiles carry two, which is
the general standing on his own city. Taken from Mylae's `StratOverlay`: the
pixel-grouping rule (one icon with a count badge until the zoom is high enough
to fan them out sideways) and the mod's own resource art with a drawn glyph
where it ships none - the stock pictures are inside a `.pack` archive nothing
here reads, so the fallback is the ordinary case. Changed: the projection is
16c's canvas rather than Mylae's Leaflet bounding box, and **a drag plans**. A
character dropped on a tile calls the same `/api/map/character_plan` the panel
beside it calls, with the same confirmation, warnings and undo; the drag itself
previews only what the browser can answer exactly - on the grid, and sea by the
measured `map_heights` rule with river crossings excluded, which is the test
`stratchar.check_character` applies on the server. The layer is off by default
and its five categories toggle separately: 1,131 resources drawn over the
provinces is not a map any more. Full-map frame on DaC: **2.6 ms with
settlements, characters, 105 forts and 295 watchtowers, 2.8 ms with the 1,131
resources as well**, against 0.5 ms with the layer off.

A finding that changed the payload: **a fort and a watchtower name a region, not
a faction.** DaC writes all 105 and all 295 of them inside the `region` blocks at
the end of the file, where nobody owns them, so that is what they carry.

**17e - the hover tooltip.** Mylae's `MapPixelTooltip`, answered in the browser:
the tile in both coordinate systems, what stands on it, and a swatch and a named
value for every aligned layer. The three tables it cannot derive travel with the
manifest (`campmap._vocab_view`, 2.9 KB: the arbiter's ground types and
features, and this mod's own climates, because DaC renames all twelve); the four
layers that have a rule rather than a table have that rule stated in
`_colour_name` and mirrored in `cmapNameColour`. **Every match is exact.** Mylae
nearest-colour matches a legend within a distance of 30 and regions within 6,
which on a map carrying a one-channel painting slip confidently names the wrong
province; a colour no table claims is reported as one here. **0.65 ms per tile
change and 0.17 ms per pointer event inside one tile**, with all eight aligned
layers named. `ⓘ Names` or `T` turns it off, remembered with the layer settings.

**17f - one faction screen, two files.** `descr_sm_factions.txt` says what a
faction is; `descr_strat.txt` says what it starts the campaign with. They are
one screen now, in the campaign map, with the picker listing every faction
either file knows and saying which of the two is missing a slot. They stay two
engines and two saves: `factions.py` keeps its file and `stratcamp.py` keeps
its, each half has its own Save naming its own file, its own plan and its own
undo entry. What changed in `factions.js` is only where it paints. The campaign
half can be absent and the faction half still draw, which is 16f's evidence rule
again. Minor Files keeps a Factions tab: it lands on the combined screen when
the mod has a map and on the old mode when it has not, because a mod that ships
units and lets the game's own map stand still has factions to edit.

**17g - the menu's hints are sentences.** All fifteen hints under the module
names, the nav brand's subtitle and the Credits hint opened in lower case while
the rest of the toolkit's prose does not. Two were rewritten rather than
capitalised because the word they opened on is a file name and the file really
is lower case. `dev/checks/prose_check.py` gained the rule that would have caught
them: some text is a sentence **by declaration** - a `hint:`, `help:` or `tip:`
whose value is a phrase, and the two lines the nav brand carries in markup - and
is measured as prose at any length, where `lower_starts` asks for a full stop or
sixty characters first so that "mercs only" and "per turn" are left alone. The
value must contain a space, because `note: 'count'` is a severity mapped to a
CSS class in two modules.

**17h - the credits, rewritten.** Developed by ProJYeet, co-developed by Demir,
then the four works this toolkit took reference from with thanks for the
permission - Mylae's M2TW Editor, Fynn's Medieval II Total War Modding Tool
(moved here out of "for the motivation"), Bare Geomod by Sinople and Gigantus,
and Withwnar's TWMapReader - and then the sponsor, the special thanks and the
testers as they were. Gigantus is named twice, once for the guides and once for
Geomod, and that is correct: they are two different contributions.

**17i - exit, met, and it earned its place.** Every item verified in a running
browser on both installed maps - and the pass on DaC found a real fault the
suites could not: 17d asked for resource art at `/api/icon`, and the picture
routes are the one family that predates the `/api` prefix. Every request 404ed,
and because the wrong path never reaches the handler that promises a blank PNG
rather than an error, it 404ed silently and the glyph fallback drew instead. All
seven of DaC's resource pictures and all four of Reforged's load now. That is
the reason 17i is written as "in a browser on both maps" rather than as a test:
nothing asserted here would have caught it. `test_web_modules` is 16 checks and covers the new module wiring;
`test_campstrat` gained five checks over `markers` on every installed campaign.
Three `test_campstrat` DaC-number checks fail on the DaC build installed here
(line count, character count, the nine known-bad lines) and fail identically
with the phase's changes stashed - the mod differs from the one Phase 16 was
measured against, and that is recorded in `STATE.md`.

### The scope as it was written

#### Phase 17 - The campaign map correction pass (as scoped, 2026-09-05)

Eight items the user raised after using 16a-16k end to end. They are UI faults
and UI gaps on a data layer that is already finished and tested, so none of them
needs a new parser and none of them changes a file format. Do them in this
order: the two bugs first, because they are wrong rather than missing.

### 17a - Home is missing the Campaign Map card

**Diagnosed, not just reported.** `web/js/home.js:230` filters `MODES` down to
the non-`sub` modes and then reads `r.modules[d.id]`; a module with no entry in
that report returns `''` and vanishes with no error. `campmap` has no entry
because `unittransfer/modfiles.py:27` `MODULES` still lists the ten V2 modules
and was never given the eleventh. So the Campaign Map card is missing from
**every** mod card on Home, on every mod, and the burger menu is the only way
into the flagship feature of 3.0.0.

The fix is not one dictionary line. `MODULES` is the readiness table: a module
in it also needs its files declared in `KNOWN` with the right `required` flag,
or Home will say a mod is ready for the map editor when it has no
`world/maps/base` at all. Declare `descr_terrain.txt`, the ten layers and
`descr_regions.txt` as the required half, `descr_strat.txt` and
`descr_win_conditions.txt` as the campaign half, and check what `describe`
reports for a mod that ships no map - that path already exists, because 16c had
to stop reading the map through `Registry.get` for the same reason.

While in there: `factions`, `cards` and `stratmap` are `sub` modes and are
correctly filtered out of Home; do not add them by accident.

### 17b - The hover box leaves a trail of pixels behind it

A visual glitch: hovering the map draws the black readout box, and pixels of it
are retained on the canvas after the pointer moves on. 16c's hover step
"repaints the cell the cursor left and the cell it entered and nothing else" at
0.046 ms, and that dirty-rect repaint is almost certainly the cause, because the
box is larger than the two cells being restored. Either lift the readout out of
the canvas into a DOM element positioned beside the cursor (which is what
Mylae's `MapPixelTooltip` does, and see 17e), or widen the restore rect to the
box's own bounds. Measure it afterwards: the point of the dirty-rect repaint was
that a hover step costs nothing, and a full repaint per pointer move would undo
16c.

### 17c - Not every region is clickable

Reported, not yet diagnosed. Start from what 16c already proves: 200 of 200
regions on DaC and 116 of 116 on vanilla agree pixel for pixel between the
served PNG and the Python index, checked at each region's own anchor. So the
index is not the suspect. The likely candidates, in order:

- a **marker** tile at the point clicked. A settlement or port pixel is black or
  white and belongs to no region by colour, which is the same hole `mapquery`
  had to close for a resource standing on a marker; the region that owns the
  marker should answer.
- a colour `descr_regions.txt` never declares, which is a real thing on both
  maps (DaC's 517-tile province, vanilla's four sea colours) and should say so
  rather than doing nothing.
- a region small enough to lose to the hit test.

Reproduce first, name the region and the tile, then fix. A silent dead click is
the failure mode to remove even where the tile really has no region.

### 17d - Settlement, character and resource markers on the map

Mylae's `StratOverlay.jsx` (293 lines), and the thing his map reads best.
Everything in `descr_strat.txt` that has a coordinate gets an icon at that tile:
settlements by level, characters by type (general, admiral, spy, merchant,
diplomat, priest, assassin, princess, heretic, witch, inquisitor), forts,
watchtowers and trade resources. What to take, and what to change:

- **Take** the pixel-grouping rule. Items on the same tile are collected into
  one marker with a count badge and fan out sideways once the zoom is high
  enough, because a general standing on his own city is the normal case and two
  icons on one tile is unreadable.
- **Take** the real resource icons: he falls back to an emoji and uses the mod's
  own `data/ui/resources` TGA when it is there. TWMapReader does the same and
  adds the vanilla fallback for a mod that ships none, which `IconCache` already
  knows how to do.
- **Change** the projection. His converts M2TW tiles to Leaflet lat/lng through
  the OSM bbox; ours has no Leaflet and no bbox, and 16c's canvas already maps a
  tile to a pixel exactly. Use that. This is the "port behaviour, never JSX"
  rule in its plainest form.
- **Change** the drag-to-move. He moves a character by dragging its icon. Our
  writers refuse a move that lands somewhere illegal and
  `mapcheck.marker_faults` is the one copy of those rules, so a drag previews
  against that predicate and the drop plans a save rather than writing on
  pointer-up.
- Category toggles, and the layer off by default on a map carrying 1,131
  resources.

### 17e - A region tooltip on hover

Mylae's `MapPixelTooltip.jsx`. Hovering a tile floats a small panel beside the
cursor: the tile in both coordinate systems, a colour swatch and a named value
for every layer, and for `map_regions.tga` the settlement and region name rather
than an RGB triple. We already have all of that server-side -
`campmap.probe_pixel` names one tile across all ten layers in 0.17 ms on vanilla
and 0.80 ms on DaC - but 16d deliberately put it behind a **click**, because a
round trip on the pointer is what this phase's rules exist to prevent.

So the tooltip is answered in the browser, out of the manifest and the region
table it is already holding, exactly as the current hover readout is. Do not
call the probe route on pointermove. Two things his version gets wrong and ours
should not: he nearest-colour matches a layer's legend within a distance of 30,
which will name a colour that is not in the file at all, and he tolerance-matches
regions within 6, which on a map carrying a one-channel painting slip (both real
maps carry several) will confidently name the wrong province. Exact match, and
say "no table names this colour" when there is none. That is 16d's legend rule
and 16f's evidence rule, and both were measured.

This item and 17b are one piece of work: the tooltip is the DOM element that
replaces the canvas-drawn readout.

### 17f - Move Factions out of Minor Files and into the Campaign Map

`factions` is a `sub` mode reached through the Minor Files tab strip
(`MINOR_TABS` in `web/js/core.js`) and it edits `descr_sm_factions.txt`: the
culture, religion, colours, the horde keys and the art. `stratcamp.js` already
has the campaign-map faction tab, which edits the same faction's entry in
`descr_strat.txt`: its AI label, its purse, its diplomacy and its standings.

Those are two halves of one question, and nobody thinks of them as living in
different modules. Combine them into one faction screen inside Campaign Map
mode, with the `descr_sm_factions.txt` fields and the `descr_strat.txt` fields
on one form. Constraints:

- **One engine.** `factions.py` keeps `descr_sm_factions.txt` and `stratcamp.py`
  keeps `descr_strat.txt`. This is a screen that talks to both, never a third
  module that parses either.
- A faction's `descr_sm_factions.txt` entry exists in a mod with no campaign at
  all, so the screen has to work with the campaign half absent. That is 16f and
  16g's evidence rule again: name the file that is missing, do not blank the
  form.
- `factionclone.py` (15g) creates the twelve-file half and `stratcamp` (16j-2)
  creates the campaign half, and the two are deliberately separate. Combining
  the *screens* must not combine the *saves*.
- Leave a tab in Minor Files that switches mode, the way `MINOR_TABS` already
  does for Traits and Ancillaries, so the old route still lands somewhere.

### 17g - Capitalise the burger menu

Every hint under a module name in the nav is a lower-case fragment: "your mods,
and what each one is ready for", "change, clone or delete one mod's units", and
so on for all fifteen entries in `MODES` (`web/js/core.js:639`). The nav brand's
subtitle ("edit a mod without hand-editing its files") and the Credits hint
("who made this possible", `web/index.html:2238`) are the same. Capitalise the
first letter of each. They are sentences, so they should read as sentences; the
rest of the toolkit's prose already does, which is why these stand out.

Check `dev/checks/prose_check.py` while there. It measures the writing and did not
catch this, so it has no rule for a sentence that starts lower-case. Adding one
is cheap and stops the class of fault coming back.

### 17h - The credits, rewritten

Replace the body of the Credits dialog (`openCredits`, `web/js/core.js:1473`).
The new shape, in the user's words:

- **Developed by** ProJYeet. **Co-developed by** Demir.
- **Built on the work of, and thanking them for permission to take reference
  from their code:**
  - Mylae's tool ([M2TW Editor](https://github.com/Machiavello-1441/m2tw-editor))
  - [Fynn's Medieval II Total War Modding Tool](https://www.twcenter.net/ubs/medieval-2-total-war-modding-tool.26/)
    - **moved here** out of the current "Thanks / for the motivation" line
  - Bare Geomod, by Sinople and Gigantus -
    https://www.moddb.com/mods/bare-geomod-and-tools
  - TWMapReader, by Withwnar -
    https://www.twcenter.net/threads/tw-map-reader-v2-24-1-jul-2015-update.438278/
- Keep **Sponsored by** FeatherLeaf, keep the **Testing** list, and keep the
  Gigantus / TWCenter special thanks. Gigantus is now named twice, once for the
  guides and once for Geomod, and that is correct: they are two different
  contributions.

### 17i - Exit

Every item above verified in a running browser on both installed maps, not only
asserted in a suite. `test_web_modules` covers the new module wiring, and 17a
gets a test that asserts every non-`sub` entry in `MODES` has a `MODULES` entry.
That is the class of bug rather than the instance, and it is the only reason
this one survived a whole phase.

---

## Phase 18a - Four files nobody could edit - done 2026-09-07

**Closes M5, M6, M13, G3.** The first sub-phase of 3.1.0, and the common shape
of all four is the one the release exists to remove: *we know a file well enough
to validate it and not well enough to edit it.*

Two things in the scope were wrong and were corrected by measuring before a line
was written, which is worth recording because both would have been built wrong:

* **M6 is `descr_faction_movies.xml`, not `.txt`**, and it is in the campaign
  folder rather than under `data/`. Both installed mods have one - Third Age
  Reforged declares one faction, Divide and Conquer ships the empty shell - and
  **neither has a trailing newline**, which is exactly why it is a line splice
  and not a serialiser. The reference tool's `serializeFactionMovies` rebuilds
  the file from its own model and would have rewritten both of them on the first
  save of either.
* **`flatrecord.py` does not cover three of the four.** The scope said it did.
  M5 is a UTF-16 localisation file, M6 is XML, and G3 is a word on a `regions`
  line inside a `pool` block. Only M13's *definition* half is a flat record, and
  it is used as one - `guilds.SHAPE` is a real `flatrecord.Shape` and the block
  editor, its span map and its field list are that module's rather than a third
  copy. What could not go through it is the *file*, for the reason below.

**M13 - `export_descr_guilds.txt`, and the bug it uncovered in `triggers.py`.**
The file has two block types and **the keyword that opens a definition is also
the keyword of an effect line inside a trigger**:

    Guild assassins_guild                 <- a definition, 2 words
        Guild assassins_guild s  10       <- an effect, 4 words

`triggers.parse_text` ended a trigger on *any* line whose head word was in
`BLOCK_ENDERS`, so every guild trigger ended at its own first effect: it kept
its `WhenToTest` and its conditions and lost everything it actually did, and all
507 effect lines were collected as definitions. EDCT and EDA never hit this
because `Affects` is not `Trait`. The fix is `triggers.DEFINITION_WORDS = 2` and
it was measured before it was written: **all 1,850 `Trait` and `Ancillary` lines
in both mods' EDCT and EDA are two words**, and `export_descr_guilds.txt` is 21
two-word definitions against 507 four-word effects. So the count separates them
and costs the older two files nothing. `parse_records` still cannot read the
file - it opens a record on every matching head line - which is why
`guilds.parse_text` is the one new file-level parser in the phase.

What the file says, counted rather than assumed:

* **a definition has exactly two body keys.** All 21 records write `building`
  and `levels` and nothing else. The reference parser also reads
  `SettlementMinLevel` and `FactionSupport`; neither is in a single real file,
  so both round-trip through an edit and neither is a form field.
* **`levels` is three ascending thresholds** - 20 of the 21. The one that is not
  is Third Age Reforged's `gwaith_i_mirdain_guild`, `levels 1000000 250`, two
  values and descending. Reported, not refused: it is somebody else's mod and it
  loads today.
* **the scope letter is `s`, `o` or `a`** - 272, 188 and 47 uses. The reference
  tool documents only the first two and defaults to `o`, which would silently
  rewrite all 47 of the third kind.
* **`all` and `this` are engine words, not guild names.** Both mods award points
  to both and declare neither, so the "these points go nowhere" check skips
  them rather than reporting 47 findings about words the engine owns.

And the finding the module exists to make: **Divide and Conquer awards guild
points to `avengers_guild` and `thiefs_guild` and declares neither** - 24 and 8
trigger lines whose points go nowhere. That is the exact shadow `buildings.py`
could see since Phase 12 and could not name.

The mode is `sub:true` beside Traits and Ancillaries, with a Minor Files tab, a
Code View kind, and the Phase 7 trigger builder under the block - because a
guild is the same two-halves-of-one-file shape a trait is, and reading one half
without the other tells you nothing.

**M5, M6 and G3 - `campfiles.py`, one module over three files.** Not tidiness:
all three answer "what does this campaign say about this faction, or this
province", and each on its own is fifty lines and a screen nobody opens twice.

* **M5.** The description keys are **built, not listed**: the campaign folder's
  name upper-cased, then the faction's, then `_TITLE` or `_DESCR`. All 230 keys
  across both mods fit it, and the only two suffixes are those. So a faction the
  file has never mentioned still gets a form and saving creates the key - which
  is the case worth having, because a faction with no description shows its code
  name on the menu and nothing on disk says so. `REFERENCE_GAPS.md` also
  promises "victory text" here; there is none in either mod, and a campaign's
  victory terms are `descr_win_conditions.txt`, which 16j-2 already writes. The
  write takes `traits._write_loc`'s two roads: into the `.txt` and recompile the
  `.strings.bin` beside it, or straight into the archive when the mod ships only
  that.
* **G3.** 16b read the pools and the UI has been deferred ever since; what was
  missing was the write, and the write is one word moved from one `regions` line
  to another. Measured: 57 pools over 193 provinces in Divide and Conquer and 27
  over 148 in Third Age Reforged, and **not one province is in two pools**,
  which is what lets the picker be a single choice rather than a set of tick
  boxes. `keyblock.sub_tokens` could not do the rewrite: it walks the tokens
  already on the line and substitutes into them, so a shorter list leaves every
  province past its end still on it. `campfiles.set_regions` owns the whole tail
  of the line, which is what a variable-length list needs.

All three of M5, M6 and G3 save on their own rather than riding on the region or
the faction save, and that is **17f's ruling rather than a shortcut**: one
screen over several files, one save and one undo per file, each naming the file
it put back. The faction tab is four files and four Save buttons now.

**Exit, all met.** Each of the four round-trips byte-exact on every installed
mod with no edits (`parse(t).text() == t`, and every guild block re-renders to
itself unchanged); one field edited changes one line; and each save goes through
the one backup-and-log route every writer in this toolkit uses.
`tests/test_guilds.py` (62 checks) and `tests/test_campfiles.py` (76) are new;
`test_triggers`, `test_traits` and `test_ancillaries` were re-run against the
`DEFINITION_WORDS` change and are unmoved at 49, 112 and 85. All four screens
were driven in a running browser on Third Age Reforged.

---

## Phase 18b - Events and disasters - done 2026-09-07

**Closes M3, M4**, and with them Phase 18. Two files that are the same sentence
with a different subject: a `descr_events.txt` block is "on this date, this
happens, here", a `descr_disasters.txt` block is "every so many years, this
happens, somewhere that looks like this". Both are a head line, a run of
`keyword value` lines under it, and repeatable `position x, y` lines - which is
what made this a map phase rather than a minor-files one, and made it the first
customer for 17d's marker layer after 17d itself.

**Neither installed mod ships a word of either file.** `descr_disasters.txt` is
**0 bytes** in Divide and Conquer, in Third Age Reforged and in Reforged's
Fellowship campaign; Reforged's `descr_events.txt` is a five-line Geomod comment
banner and Divide and Conquer's is empty. So the arbiter here is the **game's
own unpacked copies**, which are on this machine: `descr_disasters.txt` (1,567
bytes, eight blocks) documents its own format in its own header, and
`descr_events.txt` (6,194 bytes, 35 live blocks) documents the event categories
in its. That is a better arbiter than either mod would have been, and it is the
reason this phase could measure at all.

**Four things the reference tool gets wrong, each shown on its own files.**
`campaignEventsParser.jsx` and `disastersParser.jsx` are 90-line readers with a
serialiser each:

* **both serialisers rebuild the file from a model**, so the first save of
  either drops every comment. The game's `descr_events.txt` is more than half
  commented-out test cases and format documentation, and it ends **without a
  trailing newline**. Every edit here is a splice and `parse_*(t).text() == t`
  is the gate, the same as every editor since Phase 8.
* **their event parser holds one `date`** (`current.date = …`), so the last
  `date` line wins. Reforged's Fellowship campaign writes four for one event -
  `date 7 8` and three `date … turns …` lines - and three would be lost.
* **their event categories are the disaster list.** The game's own header names
  `counter`, `historic`, `volcano`, `plague` and `emergent_faction`, and its own
  live lines also use `earthquake` - measured, a census over every
  `descr_events.txt` on this machine is 26 `historic`, 4 `earthquake`, 5
  `plague` and nothing else. Theirs has neither `counter` nor
  `emergent_faction`, and the second is how a faction enters a campaign at all.
* **their disaster serialiser writes every key.** Vanilla's `plague` block has
  no `warning` line; theirs defaults the value rather than remembering the line
  was absent, so it would add one to a block nobody edited. A slot that is not
  there is a line to add, not a line to blank - 18a's ruling about a movie slot,
  restated.

**And one rule that would have called the shipping game broken.** Vanilla's
`storm` and `horde` both write `region the sea`, and there is no `the sea` in
`descr_regions.txt` - checked. So `campevents.SEA_REGION` is a declared value
and the unknown-region rule passes over it. That is "a rule with no evidence
reports nothing" applied to a **value** rather than to a missing file, which is
the first time that decision has had to stretch that way.

**What the checks will not say without evidence.** The event-picture rule
(a missing `data/ui/<culture>/eventspic/<label>.tga` is a campaign CTD, per the
TWCenter tutorial) runs only over the `eventspic` folders a mod actually ships,
found by glob rather than listed - **neither installed mod ships one**, because
the stock pictures are inside a `.pack`, so on both of them the rule is silent
rather than reporting every event as broken. The text rule is the same shape and
does have evidence: `historic_events.txt` keys are `<LABEL>_TITLE` and
`<LABEL>_BODY`, measured across 1,796 keys in Divide and Conquer and 582 in
Third Age Reforged with **no third suffix in either**. The climate, region and
faction rules each go quiet when their vocabulary is not on disk.

**`mapcheck` learned one rule, `event.position`**, in the resource rule's shape
because it is the same fault about the same kind of number: off the grid is
fatal, on a sea tile is a warning. It found exactly one thing in the game's own
data - `black_death_3` has a position at 102,74, which is sea - so the stock
map's baseline goes from 62 findings to 63, and the "a baseline shows and stops
blocking" decision covers it exactly. The rule costs 9 ms on the game's map and
nothing on a mod with empty files.

**On the map**, an event's and a disaster's positions are two more categories of
17d's one marker layer rather than a layer of their own: two overlays that each
know half of what is standing on a tile is how a tooltip ends up telling half
the truth. They are drawn as bursts - amber six-pointed for an event, red
eight-pointed for a disaster - because a coordinate nothing owns should not be
mistaken for one of the four things a faction does. `marker_view` reads them
outside its `facts.strat` guard on purpose: a mod whose `descr_strat.txt` will
not read still has a map, and its disasters are still painted on it.

**There is no drag**, and that is a decision rather than an omission. 17d's drag
moves a character because a character stands on exactly one tile; an event has a
*list* of positions - the Black Death's third wave has seventeen - so dragging
one is a gesture with no obvious subject. `＋ from the picked tile` is what
replaces it: click the map, click the button, and the coordinate is written in
the file's own convention (y up from the bottom) with nobody doing the
arithmetic. The flip is made in exactly one place in the browser, which is the
same rule `marker_view` follows in the other direction.

**Exit, all met.** Both files round-trip byte-exact including comments - nine
real copies on this machine, from 0 bytes to 6,194, every one of them; a
disaster's and an event's positions appear on the map beside the settlements and
the resources; and a position off the map is refused with its coordinate named,
both by the save (`plan` returns the error and `apply` raises) and by the
validator. Adding a block and deleting it again restores either file exactly.
`tests/test_campevents.py` (82 checks) is new. The panel was driven in a running
browser on Third Age Reforged: both tabs, both add forms, the picked-tile button,
the marker glyphs and a refused off-map save.

One thing outside its own files: **`dev/reference/upstream_sync.py status`
sorted phase numbers with `int()`** and died the moment a manifest entry carried
a sub-phase letter. Phase numbers in this roadmap have had letters since 16a, so
the sort now tolerates one.

---

## Phase 19a - The keys a new record needs - done 2026-09-09

**Closes D4 and D5.** Both are one sentence: a record was created and the text
that names it was not. D4 closed a finding the validator has been reporting
against the toolkit's own output since 16f - 16e's wizard makes a province,
`loc.missing` then says the player will read its code name on the campaign map,
and nothing here could write the line that fixes it.

**`unittransfer/namekeys.py`** is new and owns neither parser. `descr_names.txt`
belongs to `minorfiles.py`, which 16j-2 refused to copy a second time, and both
`{key}value` files belong to `stringsbin.py`. What is in the new module is the
*write* and the rules around it, and every read goes through the module that
already owns the format - `minorfiles._loc` for the txt-or-archive read,
`minorfiles.render_names` for the splice, `stringsbin.upsert_txt` for the line
and `cleaner.refresh_strings_bin` for the cache.

**D4 is one file and D5 turned out to be two.** Every one of Divide and
Conquer's 3,583 pool names and 2,572 of Third Age Reforged's 2,573 has a key in
`data/text/names.txt`; a pool entry without one shows the raw token in game. So
the pool line and the text key are one job with one backup set and one undo -
the ruling `minorfiles.plan` already makes over a religion's four files, which
are worthless written one at a time. The single exception in that measurement is
the word `surnames`, and it is the phase's other finding.

**`descr_names.txt` has four sections, and `NAME_SECTIONS` listed three.** Third
Age Reforged's `dolguldur` writes a `surnames` heading with one name under it,
and the parser was reading both lines as characters - 248 characters instead of
246 plus a surname. Two references settle it independently: Demir's
`parseDescrNamePools` accepts `characters | surnames | women | settlements`, and
TWMapReader's `TwDataReader` tests for `surnames` by name. It is corrected in
`minorfiles.py` rather than worked around in the writer, because a writer that
did not know would have appended a new name underneath a heading that is not the
one it meant. `stratchar.Vocabulary` reads the fourth section into its own list,
kept apart from the pool because a surname is the second half of a name and
never a character on its own.

**A name splits on spaces and never on underscores.** The old `check_pool`
compared the whole `descr_strat` name against a list of first names, with a
`name.replace(" ", "_")` fallback. Demir's rule is the other way round: the last
word is a surname, the rest joins with an underscore, and an underscore is what
a space *inside* one part becomes - Divide and Conquer's pool holds
`The_Dark_Lord` as one entry and its `descr_strat` writes it as one word. All
305 of that mod's characters and all 246 of Third Age Reforged's have a one-word
name and every one of those words is in a pool, so on both installed mods the
two readings agree; the two-part form is supported on the arbiter's word rather
than on a measurement, and it is said so in `name_parts`.

**The wizard names a province at creation, and that is not a departure from
17f.** 18a's rule is that one screen over several files means one save per file,
and the region panel keeps it: the name boxes are a third file, a third Save
button and a third undo entry, exactly as the mercenary pool is a second.
Creating a province is a different thing - one act across the layers, the record
and the name - so `campaint.apply_paint` writes all three into one backup set,
because an undo that took back the record and left the key would leave a mod
pointing at a region that is gone. With the boxes empty the wizard warns in the
words the validator will use rather than refusing: a province deliberately
called by its code name is legal.

**`check_pool` gained a second finding**, `char.name_key`, for the half nothing
here could see: the name is in the pool and has no line in `text/names.txt`. Both
findings carry the part they are about and both get an `Add to pool` button on
the finding itself, which is where somebody meets the problem rather than in a
screen they would have to know to go and find.

**Exit, all met.** A province created by 16e's wizard has a name in game,
checked by reading the compiled `.strings.bin` back rather than the `.txt`
beside it; 16f's `loc.missing` count is zero on a mod whose regions were all
created through the tool; a name added to a pool leaves every other entry
byte-exact - one line more and no other line changed, measured on a copy of
Third Age Reforged's 125 KB file - and one undo puts both files back byte for
byte. `tests/test_namekeys.py` (55 checks) is new, and `tests/test_campaint.py`
gained the wizard's fourth claim and a names file in its fixture. Both panels
and both routes were driven in a running browser on Third Age Reforged.

**G4 stays in Later.** The legion label is D4 in miniature and would have been
nearly free here, and the roadmap says it stays unless the user moves it. It
still would be nearly free: the write it needs is the one this phase added.

## Phase 19b - Rename, and follow it - done 2026-09-09

**Closes D2 and D3.** 16d refused a region rename in three places and 15g
refused a faction one, and both refusals named the cost exactly: the name is a
key, and the files that point at it are files the panel has never opened. They
were right about the problem and wrong about the conclusion, which is the same
shape 15g's own `factionclone.py` had already argued about creating a faction.

**`unittransfer/renames.py`** is new: three subjects, one engine, and every read
through the module that already owns the file - `campmap.parse_regions` for the
region records, `campstrat.parse_strat` for the campaign start position,
`winconds.parse_wins` for the win conditions, `campfiles.parse_mercs` for the
pools, `factions.parse_text` for the roster and `modeldb` for the length-prefixed
texture records. Four files nobody owns - the lookup pairs, the music types, the
custom battle tiles and the `{key}value` names file - get a finder of a dozen
lines each rather than a parser.

**It is position-aware everywhere, and that is measured rather than cautious.**
The obvious implementation is `unitrefs.py`'s (walk the mod and rewrite the token
wherever it stands alone) and over these three namespaces it corrupts real mods.
Divide and Conquer's region `Eregion_Province` has the settlement `Eregion`, and
`Eregion` is **also a hidden resource on the flags line of twenty other regions
in the same file**; a token walk over `descr_regions.txt` renaming that
settlement would have rewritten all twenty. `Dunland` is a settlement, a sound
folder, the first word of eleven unit types, a `custom_location`, a climate
comment and, in Third Age Reforged, a faction slot. Settlement names matched in
**sixty files** across the two installed mods and most of those hits are
coincidences. So a rename asks each file which of its *lines* may hold a name of
this kind and rewrites the token only there; six span rules say where on such a
line it may sit, and only a token equal to the old name is ever rewritten.

**A province is a clean namespace and a settlement is not, and both were
counted.** All 198 of Divide and Conquer's region names and all 199 of Third Age
Reforged's appear in fifteen files and twelve, every one a campaign or base map
file. That closed list is what makes D2 doable at all: the hard half of a region
rename is not finding the references, it is knowing when to stop looking.

**`descr_strat.txt` does not name a settlement, and 16d's refusal said it did.**
A settlement block carries `region <province>` and never its own name; every one
of the 578 and 147 whole-word hits in the two mods' `descr_strat.txt` is a unit
type, a portrait, a character label or a comment. So a settlement lives in
exactly three places (its province's record, the lookup file's pairs, and the
`{key}` it is read through) plus the campaign script. The sentence is corrected
in `campmap.py`, in `codeview.py` and in the panel's own `CMAP_LOCKED`, which is
the same thing 19a did to `NAME_SECTIONS` and for the same reason: a claim that
is nearly true is what a later session builds on.

**`campaign_script.txt` is reported and never edited**, which is the ruling the
plan asked for and the one 15g made about `descr_strat.txt`. Every occurrence
comes back with its file, its line number and its line, and the dialog shows them
in a scroll box under a red heading before there is a button to press. Renaming
Divide and Conquer's `sicily` reports 423 of them.

**A rename follows five files a clone refuses, and the difference is not an
inconsistency.** `factionclone.REVIEW_FILES` are the files where naming the donor
is a *judgement*: adding a clone to `and FactionType sicily` means rewriting a
boolean's logic, and giving it a trait or a prebattle speech means inventing one.
None of that applies to a rename, because the condition, the trait and the speech
already exist and already mean this faction, which is now called something else.
So traits, ancillaries, prebattle speeches, missions and guilds are sites here,
read through an `operand` rule that follows the tail of a condition line and
never a trait named `Fearssicily` or an engine effect called
`Combat_V_Faction_Sicily`, neither of which is a token by the boundary rule
anyway. `descr_strat.txt` is the mirror image: a clone leaves it alone because
there is nothing to copy, and a rename must follow it because the block is
already there.

**The two things a faction rename has that the others do not.** Its texture
records in `battle_models.modeldb` are length-prefixed, so `rename_modeldb`
rewrites the count in front of each name through `modeldb._texture_group_spans`:
3,160 records on Divide and Conquer's file, which still parses to the same entry
count afterwards. And its art is found by convention rather than pointed at
(`ui/units/sicily/`, `symbol24_sicily_roll.tga`), so those files **move**: the
source is backed up file by file and then deleted and the destination recorded as
created, which is exactly the pair `transfer.undo` needs to put a move back.

**One backup set for all of it.** A rename half applied is a mod that will not
load, so an undo that restored some of these files would be worse than one that
restored none. Same ruling as 18a's created record, against 17f's usual one save
per file.

**Refused before a byte is planned:** a name this mod has not got, the name it
already has, a name that is not one word, a faction slot that is not lower case,
either end of a rename being one of the four reserved slots, and, the one worth
saying, **a province renamed to an existing settlement's name**. A province and
its settlement are keyed in one `{key}value` file, so a second `Anorien` would
quietly take over the first one's line on the campaign map, which is a rename
that looks like it worked.

**`campaign_dirs` walks to any depth**, which `campstrat.campaigns` does not.
Divide and Conquer keeps Shattered_Alliances under `custom/` and Third Age
Reforged keeps Fellowship_Campaign there, and both are whole campaigns with their
own `descr_strat`, win conditions, mercenaries and script. Reforged's also ships
its own `descr_regions.txt` with all 199 regions in it, which is why
`region_files` returns a list.

**Exit, all met.** A province renamed on a copy of a real mod leaves the file set
byte-exact except at the occurrences the plan listed; every occurrence in
`campaign_script.txt` is reported with its line number and the script comes back
byte for byte; one undo restores all of it; and a rename to a name already in use
is refused before anything is written. `tests/test_renames.py` (56 checks) is
new. One shared dialog, `web/js/renameui.js`, serves the region panel's two
locked fields and the Factions screen's `Rename slot`, and shows the whole list
before it offers the button, because in a real mod that list is twenty-four files
and four thousand lines.

**What a rename still cannot do, said out loud.** The campaign script, by the
plan's own ruling. `descr_names.txt`'s `settlements` pool, which is a pool of
words rather than a pointer at this settlement. And a mod whose second campaign
names a province its `descr_regions.txt` never declares: both installed mods have
exactly one of those, and it is the mod's own fault rather than something a
rename can invent a record for.

---

## Phase 20a - Three layers, read properly - done 2026-09-10

**Closes D8, T2 and T11.** Three things on a screen that already existed, and
none of them needed a new parser or a new route. What they needed was for the
browser to be allowed to read a layer differently from the way it arrived.

**D8 - the rivers are their own overlay now, in their own colour.** 16d had
already found the fact this stands on: `map_features.tga` is **97.7% black on
Divide and Conquer** and black there means *nothing here*, so the layer at full
opacity is a black sheet with a few rivers under it. 16d's answer was the hide
set - punch the blank colour through and the layer becomes an overlay - and it
left the rivers as they are in the file, which is three colours: `(0,0,255)` for
a river, `(0,255,255)` for a crossing and `(255,255,255)` for a source. Two of
those three are near-invisible against the ground types they are meant to be
read over, and a source is the same white as a port marker. So *Rivers only* is
a **whitelist rather than a hide set**: every colour that is not one of the
three goes, and the three that stay are drawn as one colour of the person's own
choosing. On Divide and Conquer that is **5,466 tiles of 248,370**, and the row
says so.

**One list of what a river is made of.** `mapvocab.RIVER_CODES` owns the three
codes and `mapcheck` now reads that tuple rather than keeping its own copy of
it. That is not tidiness: `mapcheck` walks the four-connected river graph out of
those colours to find a loop, an isolated tile or a diagonal-only join, and the
overlay is the picture somebody looks at when it complains. A second list is how
the picture and the validator come to disagree about where a river is.

**T2 - the heights drawn as transparency, over a ramp that is the map's own.**
TWMapReader's rule is "darker means more transparent" and taken literally -
alpha is the grey - it does not work on a real map, which is the measurement
this item turned on. Land on both installed mods runs the full 1 to 255, but it
is nowhere near evenly spread: **the median land tile is 32 of 255 on Divide and
Conquer and 31 on Third Age Reforged**, and a quarter of the land is under 19.
A linear ramp draws **52% and 53% of the two continents at under 13% alpha** -
a layer you have ticked and cannot see. So a tile's alpha is *how much of the
land is no higher than it*: the mapping is still monotonic, so darker is still
more transparent and no two heights swap places, but the ramp is spread over the
heights the map actually contains. The median tile lands at 50% and 49%. Sea is
not on the ramp at all, by `mapvocab.is_sea_height`'s measured rule - not
greyscale, or black - because sea has no height to be a depth of.

**And the control says what is still drawn over it.** The default stack has the
heights at order 2 and the ground types at 3, so a heights layer drawn as
transparency is a layer nothing can see through, because something opaque is
still painted on top of it. The row names the layer that is doing it and offers
a *Put it on top* button; it does not move the stack by itself, because the draw
order is one of the three things this screen keeps between sessions and a
control that quietly rearranged it would be taking a habit away to make its own
feature look better.

**T11 - the number keys tick a layer, and the pointer never moves.** Ten layers
and ten keys, `1` to `0`, in `campmap.LAYERS`'s declaration order rather than in
the draw order the manifest sorts by - draw order would put the front-end
picture on `1` and the region layer on `7`. The digit travels out **with each
layer in the manifest** (`campmap.HOTKEYS`) and the panel prints it on the row it
ticks, so the screen cannot promise a key the handler does not answer to. The
author's own reason for the item is the whole of the exit criterion, and it was
checked in the browser: with the pointer resting on tile 227,183 of Divide and
Conquer, pressing `3` turned the ground types off and left `c.hover`, the
readout and the tooltip naming that tile on all ten layers byte-identical.

**Two keys had to move to make room, and Shift is where they went.** 16c put
Fit on `0` and 1:1 on `1`, and ten layers leave no digit spare. They are
**Shift+0** and **Shift+1** now, and the toolbar's own tooltips say so. Shift
rather than a letter because the digit is the mnemonic - fit is still zero - and
because Ctrl+1 and Ctrl+0 belong to the browser and a page cannot have them. The
key is read off `e.code`, not `e.key`: shifted, the top row prints `!` and `)` on
a US layout and something else again on AZERTY, and "the number keys" means the
physical row somebody is looking at.

**All three run in the pass 16d already had.** `cmapMask` was one loop over at
most a megapixel that punched named colours through; it is the same one loop,
and it now also whitelists and ramps. Nothing was added to the interaction path,
which is what the exit criterion was about.

**The numbers, measured in the browser on Divide and Conquer with all three on**
(the clock is coarsened to 0.1 ms, so each is a batch of 1,000 timed together
and divided):

    a pan frame        0.0093 to 0.0159 ms across zoom 0.4x to 64x
                       (16c's bar: 0.02 to 0.18 ms)
    a hover step       0.0375 ms          (16c's bar: 0.046 ms)
    the composite      0.021 ms           (16d measured 0.015 ms)
    the river mask     4.76 ms            on a tick, once, cached
    the height ramp    6.99 ms            two passes over 248,370 tiles, on a
                       and its mask       tick, once, cached

**`tests/test_maplayers.py` (36 checks) is new, and half of it runs in node.**
Two of these three items are arithmetic that lives in the browser, and the
suite loads the real `campmap.js` into a bare V8 context with a stubbed canvas
rather than testing a second copy of the maths in Python: the file has no
top-level side effects, so `vm.runInContext` is enough and there is no DOM
library. It checks the overlay against a row of every feature colour there is,
the ramp against an even spread written by hand, and both against **every
installed map's real heights layer**, projected through `campmap.tile_view` so
they are the pixels the browser is actually served. The browser's own count of
the tiles it drew and `campmap.layer_legend`'s census of the same file agree at
5,466.

**What is deliberately not here.** The rivers are not an eleventh layer. The
stack is the ten files the map is made of - it is what the ten keys count, what
the draw order orders and what `check_layers` validates - so a reading of
`map_features.tga` belongs on that layer's row rather than beside it. Same
ruling for the heights. And the three river colours become one, so the overlay
cannot tell a crossing from a source; the tooltip still can, because it reads
the layer's real pixels and not the picture.

## Phase 20b - Getting to the thing you want - done 2026-09-11

**Closes T9, T8 and D14.** Three ways of arriving somewhere, on a screen that
already existed. One of the three turned out not to be the item that was filed.

**D14 was filed as cosmetic and was a hole.** The item reads "a screen listing
every campaign in the mod with what is in each one, before you pick one", and
both this roadmap and `REFERENCE_GAPS.md` said the picker behind it was already
there: "`campstrat.campaigns` already lists every folder that really has a
`descr_strat.txt`". It lists the folders **directly under**
`world/maps/campaign`, and measured over what is installed here:

    Divide and Conquer     imperial_campaign          31 factions, 199 settlements
                           custom/Shattered_Alliances 30 factions, 199 settlements,
                                                      25 playable, 11,686 lines
    Third Age Reforged     imperial_campaign          29 factions, 196 settlements
                           custom/Fellowship_Campaign 16 factions, 129 settlements,
                                                      and ten map layers of its own
    the stock game         imperial_campaign          22 factions, 111 settlements
                           norman_prologue            5 factions, 9 settlements,
                                                      and seven layers of its own

Three of those six were unreachable, and **nothing about the routes was wrong**:
every campaign-fed route on this screen has taken a `&campaign=` since 16g, and
every one of them resolves a name with a slash in it - measured, not assumed.
What was wrong was that the browser had no way to name one, so every request
went out with nothing and the server's own fallback answered. So D14 is the list
*and* the pick, and the deep walk 19b had built for renames
(`renames.campaign_dirs`) moved into `campstrat.campaign_paths`, the module that
owns the file, with `renames` reading it. **This is 19b's lesson twice in a
row: a claim that is nearly true is what the next session builds on.**

**A campaign name is now a word off the page, so there is a choke point.**
`campstrat.campaign_rel` is the single conversion from a campaign name to a path
under `world/maps/campaign`, and `strat_path`, `campfiles.campaign_dir`,
`campevents.events_path`, `winconds.path_for`, `mapquery.Facts` and
`mapcheck.Check` all go through it. A nested campaign IS a name with a
separator in it, so "refuse anything with a slash" was not available; what is
refused is a step that leaves the folder. Until 20b the campaign in every
request was a server-side constant and none of this was reachable.

**What a browser row says, and why each line is on it.** The menu title out of
`campaign_descriptions.txt`, the dates and the timescale, the three rosters
counted, what stands in it, and then three things that are measured facts about
real mods rather than fields in a format:

* **the folder and the header disagree.** DaC's `custom/Shattered_Alliances`
  writes `campaign imperial_campaign` on its first line. Both names are shown,
  because a mod's own files point at one or the other.
* **a campaign with map layers of its own.** Fellowship ships all ten and the
  Norman prologue seven, on the same tile grid as the base map. This screen
  reads `world/maps/base`, always, so those are pixels it is not drawing - said
  on the row rather than discovered later. `map_FE.tga` is deliberately not
  counted: it is the menu picture, all six campaigns here have one, and counting
  it would have reported "one layer of its own" about every campaign in
  existence and meant nothing by it.
* **no file to have a title in.** The stock game keeps
  `campaign_descriptions.txt` inside its packed data, so every row's title is
  empty and not one of them is a campaign nobody named. 16f's rule about a rule
  with no evidence, on the field most likely to be blank.

**And a correction to 18a, found by making a nested campaign reachable.**
`campfiles.descr_token` upper-cased the campaign it was handed, which for
`custom/Shattered_Alliances` would have built keys like
`CUSTOM/SHATTERED_ALLIANCES_TITLE`. Divide and Conquer's own description file
keys that campaign `SHATTERED_ALLIANCES_*` - measured, and checked in the suite
against the file itself - so the token is the campaign's **leaf**, not the path
it is reached through. 18a had no nested campaign to be wrong about because
nothing offered one.

**T8 - one box, and it asks the server nothing.** Every field it searches was
already on its way to the browser: the province's code name, the settlement's
code name and the region ID the engine numbers it with. The two that were not
are the words the player actually reads, and `region_view` carries them now -
two short strings a region, read once for the whole manifest through
`campmap.shown_names`, against a request per keystroke. Searching a map for
`Anorien_Province` when the game and the player both call it Anorien is a box
only somebody who has already read the files can use.

Three tiers, case-blind, and no fuzziness: exact, then starts-with, then
contains. Nothing scores edit distance - a mod's provinces are called
`Gap_of_Rohan_Province`, and a ranking nobody can predict is worse than a short
list they can read. One row a province however many of its four names matched,
and the row says **which** name it was, because "Sauron" being a settlement in
Third Age Reforged and `Sauron_Province` being the region round it is exactly
the ambiguity somebody typing it is trying to resolve. A settlement match goes
to the settlement's own pixel; everything else goes to the province anchor,
which 16c already worked out is a tile genuinely inside it. `f` opens the box
and puts the cursor in it - a letter, because the ten digits are the ten layers.

**And it closed a half-arrival all three jumps had.** `cmapPick` resolves a
province by reading the colour under the tile off the region layer's own pixels,
so with that layer never fetched - one tick from off, and off is an ordinary way
to read a map - a jump centred on the tile and selected nothing, with only the
probe's sentence to say where you were. Every caller already holds the name: a
query row IS a province, a find hit is one. So `cmapGoTile(tile, zoom, region)`
gives the pick a second chance from the manifest rather than turning a layer on
behind somebody's back, which is the call 20a made about controls that rearrange
the stack.

**T9 - the same store, keyed by a name.** 16d already remembered one layer stack
in `map_layers` on `/api/settings` and already did the hard part: a saved draw
order is reconciled against the manifest rather than trusted, so codes that are
still real keep their saved place, anything new goes where the server put it,
and nothing is dropped or invented. A preset is that snapshot with a name on it,
which is why `cmapSaveLayers` was split: `cmapLayerState` is the one description
of what the layer stack is, and adding a switch to this screen now adds it to
both the remembered stack and every preset in one place.

A view is everything that changes what the map **looks** like - the layers,
their order, their opacity, the colours punched out of each, 20a's two readings
and 16g's colouring - and deliberately not the zoom, the pan, the selection or
the tooltip. **A place is not a habit**, which is 16d's own ruling about
`map_layers` applied whole; a preset that jumped the map somewhere is a preset
nobody could use twice on two mods. The colouring is stored as its **code** and
not its colours, because the colours are the server's answer about one mod's
provinces.

`cvwPlan` is pure - a manifest and a saved preset in, what to do about it out,
including what it had to drop and what the manifest has that the preset never
saw. That is what let the reconcile be measured in node against a preset naming
a layer that does not exist, and it is where a settings file somebody hand-edited
stops: three of a preset's fields are tables and one is a list, all four come out
of a file a person can open, and anything that is not the shape it reads is
treated as absent and lands on the manifest's own defaults.

**`tests/test_mapgo.py` (142 checks) is new, and part of it runs in node**, on
20a's harness. The real `cfdSearch` is run over **every installed map's real
region table** - the exact-name tier, case blindness, the tier ordering, the
localised name, the region ID, the settlement's own pixel, one row a province,
and a painted colour the file never declared not being offered as a hit - and
the real `cvwPlan` reconciles a preset written against a map that no longer
exists. The Python half measures the two campaign lists against each other on
whatever is installed and **fails loudly if a build ever puts the shallow list
back in front of the browser**; part 5 serves a mod with two campaigns, one
nested, and no map at all, which is what proves the route is a folder walk
rather than a map read and that a campaign trying to leave the folder is
refused rather than read.

**What is deliberately not here.** The find box does not search characters,
forts or anything else on 17d's marker layer: those are a campaign's contents
and the box is about the map's places. It does not filter, either - that is
16g's twenty-four filters, and a filter panel is a different thing from a box
you reach for when you already know the name. A preset does not carry the zoom.
And picking a campaign does not throw away an unsaved paint session: strokes are
pixels on the base map, and the base map is the same map whichever campaign
reads it.

## B1 - A new province needs a settlement - done 2026-09-11

**Closes B1, the first item filed off a beta user rather than the audit, and
half of G2.** A crash with a log attached: a province made with the New region
wizard, then `ASSERT FAILED: strategy_map.cpp(7234): settlement_owner` and the
campaign stopping inside `between turns`. Filed as "the wizard does not write
`descr_strat.txt`", which it did not. **That was the smaller half.**

**The first line of the log was the one to read.** Before the settlement
complaints, the engine says `cannot find this pixel colour(8,8,8) in the
region_db` - and 8 8 8 is the first colour the wizard suggests. So the game had
the new pixels and not the new record, and a missing settlement block cannot
cause that. What can is a campaign that reads the base `map_regions.tga` through
a `descr_regions.txt` of its own, and the engine does take each map file
separately, measured rather than assumed: vanilla's `norman_prologue` ships its
own `map_regions.tga` and reads the base `descr_regions.txt`; Third Age
Reforged's Fellowship campaign ships all ten layers, its own record file, its
own music types, its own name lookup and its own `map.rwm`. The paint tool
writes `world/maps/base` and nothing else, so on a mod laid out like that a new
province is pixels in one file and a record in another file the campaign never
opens. 20b's closing line - "the base map is the same map whichever campaign
reads it" - is true of the pixels and not of the files around them.

**So the unit is the campaign, not the map.** `campaint.map_campaigns` asks,
per campaign, which copy of each file it reads: its own when it is in the
folder, `world/maps/base` when it is not. A campaign with its own
`map_regions.tga` never sees the new pixels and is left alone, by name, in a
warning. Every other one gets, in whichever copy IT reads:

* **a settlement block** in its `descr_strat.txt` - `stratedit.new_block` and
  `plan_new_settlement`, the writer B2's "create a settlement" is meant to share
* **the record**, when it ships its own `descr_regions.txt`
* **the province under a music type** - `mapquery.add_music_region`, the first
  write that file has had, one name on the end of one `regions` line
* **the name pair** in `descr_regions_and_settlement_name_lookup.txt`, when it
  ships one
* **its own `map.rwm` deleted**, for the reason the base one always was

All of it in the one backup set the layers are in, so the Log's Undo takes back
the whole province: an undo that left a settlement naming a region that is not
there would be the crash in the other direction.

**The settlement is a village with nothing in it, last in its owner's block.**
Measured: every installed campaign already starts some settlements exactly like
that - thirteen in vanilla, four in Third Age Reforged's main campaign - and a
village is the one rung that needs no core building, where every other level
needs the walls its EDB line declares. Last and not first, because the first
settlement in a faction block is that faction's capital. The block is copied
line for line off a real one in the same file, indents and the blank line after
`region` included; only the population is chosen, and it is the median of that
file's own villages. The owner defaults to `slave`, which every campaign here
has - 59 of vanilla's 111 settlements are in it - so a new province moves
nobody's capital and nobody's balance. A picked owner missing from one campaign
falls back to the rebels there, and says so.

**It is guarded the way 16h's edits are.** The new file is parsed back before
it is handed over: exactly one more settlement, every other block the text it
was, every roster and header value unchanged, and the new block inside the
faction it was given to. Run over all 133 faction blocks of all six installed
campaigns, every one passes.

**The three smaller holes, closed with it.**

* **The creator faction is a picker.** It was a free-text box checked only for
  being non-empty, with `slave` as its placeholder. It is checked now against
  `descr_sm_factions.txt`, or - on a mod that keeps that file packed, which is
  B4's ground - against the faction blocks the campaigns declare. Either is a
  list of factions the engine loads. `slave` passes the list, because it is a
  faction, and gets a warning with the number beside it: **0 of the 509
  province records on the three installed maps use it.**
* **The music type.** The engine logs `music_type not found for regions` for a
  province with none. The wizard offers the mod's music types, and left blank
  it takes the type of the neighbour the province shares the longest border
  with, and the plan says whose.
* **The two shown names are required.** 19a made them a warning, because the
  map screen falls back to the code name. The engine does not: the log opens
  with `Couldn't find region name … in stringtable` once for each. A blank box
  now refuses the save and names the box, unless the key is already in the
  names file.

**All three are checked when the record is opened, not only at the save.** A
creator nobody defines, an owner with no block and a music type the file does
not have each refuse before a pixel is painted, because the alternative is ten
minutes of painting and then a refusal.

**What is deliberately not here.** An existing province's music type is not on
the region form - that is the rest of G2, and it stays in Later. The settlement
is not levelled up or given buildings: the settlement panel does that, and it
opens on the new one. And the names are written into
`imperial_campaign_regions_and_settlement_names.txt` only, which is what 19a's
writer and the map screen read; Divide and Conquer ships a second names file
for its nested campaign, and which campaign reads which is the header question
20b found (`Shattered_Alliances` calls itself `imperial_campaign`), not one
this session could settle by measuring.

**`tests/test_campaint.py` grew a part 4b (27 checks) and two real-data checks
in part 5.** A tiny mod with three campaigns - one reading everything from base,
one reading the base pixels through its own record file with its own lookup and
compiled map, one with a map of its own - takes a new province end to end: the
refusals, the plan, every file after the save, the old file recovered byte for
byte by taking the one block back out, the untouched campaign untouched, and one
undo restoring all of it. Part 5 runs the settlement writer over every faction
block and the music writer over every music file installed. Part 6 now saves
through HTTP into the stock game's own `descr_strat.txt` and reads the
settlement back through the 16h panel.

## Phase 20c - Labels, and picking a tile - done 2026-09-11

**Closes T4 and M8, and with them the whole of Phase 20.** Both are arithmetic
in the browser and neither needs the server: `web/js/maplabels.js` and
`web/js/mappin.js` are new, and no Python module changed.

**T4 - the names.** TWMapReader is the only one of the four references that
places names at all, and its `MapView` is plain about how: a name starts to the
right of its marker, is nudged down a pixel at a time and then up, and then the
same on the left - and when every position collides it is drawn anyway, flagged
`overlapping`. His candidates are kept, in his order, with above and below added
as the last two places to try. Three things are changed:

* **a name with no room is left off and counted, not drawn over another.** Two
  names on top of each other are neither readable. The toolbar says "84 of 199
  named", the tooltip still names every settlement, and the next zoom has room.
  What makes that honest rather than lossy is measured: on all three installed
  maps, zooming in never names fewer settlements, and from 8 px a tile every
  one of them is named - 198 of 198 on Divide and Conquer, 199 of 199 on Third
  Age Reforged, 112 of 112 on vanilla.
* **the biggest provinces are placed first.** His walks the file, so a
  zoomed-out map keeps whichever names came first in `descr_regions.txt`.
* **markers are obstacles.** A name may cover nothing - not another name, and
  not somebody else's settlement. His tests names against names only.

The placement is worked out in the map's own pixels at one zoom, so a pan is the
same layout drawn somewhere else and only a zoom asks again - 8 to 42 ms for the
three maps in node, under a millisecond at the higher zooms in the browser. A
dirty-rect frame draws the names whose boxes touch it and no others, so the
hover cell stays the few-dozen-pixel repaint 16c made it. The font is one size
at every zoom, and so is the dot a name sits beside when neither 16c's diamond
nor 17d's icon is drawing the settlement.

**A name is not a layer.** 20a settled that the stack is the ten files, so this
is a switch on the toolbar - `Aa Labels`, `L` - beside 17e's tooltip, and it is
in `cmapLayerState`, so a saved view carries it and a preset saved before 20c
opens without names, which is what that view looked like.

**M8 - the pin.** Every coordinate on this screen was typed, or taken from "the
picked tile" - and picking a tile is a click on the map, which selects the
province under it and replaces the panel being filled in with that province's
own. So the order was: click the map, re-open the form, press the button. The
pin inverts it. `⌖` beside a coordinate arms the map; the cursor changes, a
banner says what is being picked, the corner readout gives the tile under the
pointer in the numbers the field will get, and the next click is taken by the
pin - nothing is selected, no panel moves - and written into the field. Esc or
the banner's button stops it with nothing written; a click off the map is
refused and leaves it armed, because a click that silently did nothing would
look like a click that was ignored.

**One control, any field.** `cpinButton(what, fn, args)` is the whole API: a
sentence for the banner and the name of the caller's own function, which is
handed the tile already flipped into the coordinates `descr_strat.txt` writes.
The flip is made once, in `cpinTake`. The people panel has one beside its x, y;
the events panel has one on every position row and one that adds a new position.
Phase 22's object dialogs need nothing but the same line.

**Found on the way, and fixed before it shipped.** The button's `onclick` first
went out in single quotes, and `esc` does not escape an apostrophe - so "the
pin for Denethor's tile" would have ended the attribute half way through the
name. It is double-quoted now, with the JSON's own quotes escaped, and the suite
parses the attribute back with an apostrophe in it.

**`tests/test_maplabels.py` (42 checks) is new**, on 20b's node harness with
three files in one context. The real `clnLayout` on grids worked by hand, and
then on every installed map at six zooms with the invariant checked box by box:
no name over another name, no name over any marker. The real `cpinTake` against
a stubbed page: the flip, the bounds, the click it takes and the one it refuses,
the caller handed its own arguments, and a caller that has gone away said out
loud rather than thrown. Verified in the running app on Divide and Conquer as
well: the pin wrote Denethor's new tile into the form through real pointer
events on the canvas while the selected province stayed selected, and only
planned - `descr_strat.txt` on disk was not touched.

**What is deliberately not here.** Province names, as opposed to settlement
names: a province is an area, and the name of an area belongs at its centre and
at a size the area can hold, which is a different placement problem and not the
one T4 is. And no label for a fort, a watchtower or a resource - those are
Phase 22's objects, and `clnLayout` takes them as more obstacles when they come.

## Phase 21 - Two screens over data we already hold - done 2026-09-11

**Closes D6 and D11 (and M14, which is D11), and with them the whole Now set -
Phases 18 to 21, the twenty items that cut as 3.1.0.** Neither item reads a file
the toolkit did not already read; both are screens over what was there.

### D6 - is this faction complete?

**Scoped as:** one screen answering "is this faction complete?" across every
file that should mention it, with a repair offered per gap, built on 17f's
combined faction screen.

**Built:** `unittransfer/factionaudit.py` and `web/js/facaudit.js`, a panel on
the campaign map's faction tab (and in the Factions mode, which is where a mod
with no map, and the 2.x build, edits its factions). Fifteen rows: the roster,
the shown name and its `EMT_` keys, the name pool, the character types, the
units it owns and a bodyguard among them, the EDB's `requires factions`
clauses, the voice accent, the strat-map textures, the battle skins, the
settlement populace, the off-map navy, the standing rules, and in the campaign
on screen its start block and its win record.

**Every faction at once.** `Census` reads each file once and counts every slot
it names, so auditing one faction costs what auditing thirty does - 140 to 350
ms a campaign, and 1.2 s on the first call for Divide and Conquer while the
modeldb parses onto the Mod, where it stays. That is what lets the faction
picker carry a gap count on every row and the template be chosen from all of
them.

**Gap or note was measured, not copied from Demir.** His audit blocks on the
off-map navy and calls the accent optional. On the two installed mods, all 61
factions have an accent, a `descr_character.txt` entry, a name section,
strat-map textures and an `{SLOT}` key, and all but a script dummy own units and
are named in the EDB - those are gaps. Third Age Reforged ships three factions
with no navy block, three with no populace and twenty with no standing rule,
and loads - those are notes, shown dim and never counted. One check was dropped
entirely after measuring it: "an owned unit whose model has no skin for the
faction" is seven to seventeen units per faction in Third Age Reforged, which
plays, so it would have been noise on every row. On the installed mods the whole
audit finds four real gaps: Divide and Conquer's `scripts` dummy has no shown
name, no units and no EDB clause, and its `papal_states` no EDB clause.

**The campaign half is per campaign, and absence is ordinary.** Fellowship
Campaign leaves fourteen of Third Age Reforged's thirty factions out, so "not in
this campaign" is a note. The gap is the pairing: every faction with a
`descr_strat.txt` block has a win record, in all four installed campaigns
without exception, so a block with no record is one.

**The repair is the clone, pointed at a slot that exists.** 15g's cloners
already know how to put a faction into each of these files by copying a donor;
`factionclone.clone_file` now runs one of them over one file, `plan` uses it,
and `factionaudit.repair_plan` runs it per gap with the chosen template as the
donor. `ClonePlan` gained an `action`, so the write, the backup set, the undo and
the log entry are the clone's own, marked `repair`. Four rules keep it honest:

* **nothing is written for a row the faction already has**, which is what stops
  the paragraph and block cloners handing it a second section;
* **"Copy N gaps" copies gaps and never notes.** The first draft copied
  everything missing, and on Divide and Conquer's `papal_states` that was 1,614
  skin records into the modeldb because a working faction has none. A note is
  one click away on its own row;
* **the shown name is not copied.** Two factions called "Gondor" is a roster
  nobody can read, so the slot stands in until the form's name box is filled -
  the placeholder factions.py already writes;
* **the two campaign rows are links**, to New faction (with the slot typed in)
  and to Winning's add, because a start position is not a copy.

The template offered first is the faction that has the most of what this one
lacks, then one of the same culture, then the fewest gaps of its own, and never
`slave`. A slot the campaign has and the roster lacks gets the roster gap and a
button to Add a faction with its name filled in.

Found on the way: Add a faction redrew the whole page when it finished, which
was harmless in its own mode and would have taken the map with it once the
audit offered it from the campaign screen. It now redraws only in its own mode,
17f's rule.

### D11 - a raw text editor

**Scoped as:** pick any file the toolkit knows about and edit its text, with our
own backup, log entry and undo around it - the escape hatch for the mod that
does something the parser does not model. The one rule: a raw save goes through
the backup set and the log, so the Log's Undo reverses it.

**Built:** `unittransfer/rawtext.py` and `web/js/rawtext.js`, a menu mode of its
own. The list is every `.txt` and `.xml` in the mod's data folder, the map
folder, the text folder and every campaign folder at any depth - 172 files in
Divide and Conquer, 182 in Third Age Reforged - each marked with the screen that
edits it properly and a link to it. `.modeldb` is left out because its strings
are counted. A file over 4 MB is listed and not opened: `descr_skeleton.txt` is
8 to 9 MB in both mods, and a textarea that size is a tab that stops responding.

**Three things a text box gets wrong, put right on the server:**

* **the encoding.** A file is read in the codec its own bytes name - UTF-16 with
  its mark for `text/`, UTF-8 when the bytes are UTF-8, Latin-1 otherwise - and
  is only offered for saving if decoding and encoding it gives back the same
  bytes. Measured: every file in both mods under the size limit does, across
  four encodings;
* **the line endings.** A textarea folds every ending to LF, and a game file is
  not obliged to be consistent. `splice` diffs the edit against the file's own
  lines after peeling off the common head and tail (a one-line edit in 60,000
  lines is about 200 ms) and gives every untouched line its own ending back. A
  line rewritten in place keeps its ending too; only a new line takes the file's
  norm. Checked the hard way in the running app: an accent line changed by a
  repair and put back by hand in the Raw text box left the file byte-identical
  to Third Age Reforged's original;
* **somebody else's write.** `read` hands out a SHA-1 of the bytes and a save
  whose signature no longer matches the disk is refused, with a Reload button.

**What the toolkit makes of it.** Where the file has a reader here -
`descr_strat.txt`, `descr_regions.txt`, `descr_win_conditions.txt`, the roster,
the EDU - the plan reads it before and after and lists what the reader objects
to now that it did not before: take a character's age out of `descr_strat.txt`
and the plan says "character has no age" before anything is written. A warning,
never a refusal - an escape hatch that refuses when the parser disagrees is not
one. A `text/` save rebuilds the `.strings.bin` beside it, backed up first so
the undo takes both back. The plan is drawn under the box rather than in a
`confirm()`, because the change - up to forty hunks with their line numbers -
is the thing to read before writing.

**The box is never redrawn.** The search box re-renders a mode on every
keystroke, so the list and the editor are two elements and a search repaints the
list only; the caret, the scroll and the browser's own undo survive it. Tab types
a tab, Ctrl+S saves, edits survive a trip to another mode, and switching file or
mod with unsaved edits asks first. After a save every other screen's cached read
of this mod is dropped, the way picking another mod drops it. The Log names both
new entries (a raw save, a repair) and has a Raw text tab.

### Tests and verification

`tests/test_factionaudit.py` (48 checks) and `tests/test_rawtext.py` (57) are
new. The audit's suite builds a mod with a complete faction, one with one gap
and one with eight, checks every row's state and level, repairs, re-audits,
repairs again to prove there is nothing left, and undoes byte for byte; on the
installed mods it checks the one invariant the module promises - the census and
the cloner agree about what a clause and an accent line are, for every faction.
The raw suite runs the splice over seven line-ending shapes and sixty random
edits to a mixed file, four encodings, the path guard, a write and its undo with
the compiled text file, and every text file in both installed mods.

Both screens were driven in the browser against a scratch copy of Third Age
Reforged's text files, served with a scratch config so the installed mods and
the real log were never touched: the audit found the accent gap planted in the
copy, the Copy button planned and wrote it, the Log undid it, the Raw text box
wrote the same line back by hand, and a save over a file changed behind the box
was refused.

## Phase 22a - Forts and watchtowers - done 2026-09-11

**Closes the first half of D9 (and of G5, which is D9).** 16b read 800 forts
and watchtowers on Divide and Conquer and nothing wrote one; now a fort or a
watchtower can be placed on a clicked tile, dragged, changed and deleted, and
every one of those is the same request with a different `action`, as the scope
said, because in the file each is one line.

**Scoped as:** click the map to add one, drag to move one, delete one; both
forms of the fort line; the writer following 16h and 16i exactly.

**Built:** `unittransfer/stratobj.py` and `web/js/campforts.js`, the 🏰 Forts
panel on the map screen, plus two routes (`GET /api/map/objects`,
`POST /api/map/object_plan|_apply`). The plan re-reads the file, splices one
line, parses the result back and refuses it if anything but that line moved -
every other count, the rosters, the header, every settlement, every character,
every section's own fields and the bag of the other forts and watchtowers. The
save is one backup and one Log entry (`campmap` / `fortification`), undone like
any other.

**What the files say, measured before a line was written.**

* **They live in the region sections, never in a faction.** All 800 of DaC's
  sit in the `region <name>` sections after the diplomacy, and every one of the
  241 sections also carries `farming_level 0` and `famine_threat 0`. Twelve of
  the imperial campaign's hold nothing else, so a section stays when its last
  fort goes. Third Age Reforged has no fort, no watchtower and no section, and
  neither do vanilla's two campaigns - so the first one placed there opens a
  section, in DaC's shape (which is also Demir's). Where it goes was measured
  too: both of Reforged's campaigns end on `; >>>> start of regions section <<<<`,
  a blank and `script`, so the section goes under that banner; DaC's
  `;#### Scripts ####` banner is not one, so a section goes in front of it.
* **A section names the province the object stands in, usually.** 393 of the
  imperial campaign's 400 do, and the seven that do not are all in
  `Erebor_Province`, a section naming a province the map never declares.
  Shattered Alliances reads the same map and manages 352 of 400. So a new one
  is filed under the province under its tile, a moved one stays filed where it
  was, and a mismatch is a warning carrying the file's own count - with a
  "File it under X" button when the tile has a province.
* **A fort type is a battle-map folder, and not the culture's.** All 206 of
  DaC's fort lines name a folder under some culture's
  `settlements/*/ambient_settlements`, but `cerin_amroth_fort culture
  middle_eastern` is drawn out of the `mesoamerican` folder. So the type is
  checked against every culture's folders (a warning), the culture against
  `descr_cultures.txt` (fatal, as an unknown trait is), and neither against the
  other. The type box offers the file's own types first, each bringing the
  culture the file pairs it with, then the folders with "fort" in the name.
* **Nothing is on a settlement and nothing shares a tile.** None of the 800 is
  on a settlement or port pixel and no two share one; 51 forts have a general
  standing on them, which is a garrison. One watchtower is on the sea and four
  on impassable land, in mods that load. All of those are warnings; what is
  fatal is a coordinate that is not a whole number, a tile off the map and an
  undeclared culture.

**The short form is written now.** 16b noted that vanilla's `fort <x> <y>`
was exercised only by synthetic tests, because DaC writes the long form and
vanilla has no forts. The writer keeps a short fort short through a move,
lengthens it when given a type, and shortens a long one given neither - each
checked by parsing the result back.

**Byte-exact is checked on every real line.** An edit keeps the line's indent,
the gap after the keyword (DaC's `fort \t326 142` is 145 of 206), the gap
between the numbers, a comment and trailing space, and keeps the type and
culture's own spacing when neither changed. All 800 of DaC's lines render back
unchanged through the writer, and a real edit, delete, add and move each differ
from the file only where the plan names.

**Three ways in, one writer.** `＋ Fort` and `＋ Watchtower` arm 20c's pin, so
the next click is the tile and nothing is selected by it. 17d's drag now takes a
fort or a watchtower as well as a character; its drop hands the tile to the
panel, which plans the same save. And picking a province lists its own - filed
under it or standing in it - and a click that lands on a fort opens that fort.
`⚠ N to look at` lists every one in the campaign with a finding. The form's tile
has 20c's ⌖, and `📝 As text` opens the line in 21's raw editor.

**The map is the base map**, as it is for 16i's characters: a campaign that
ships its own `map_regions.tga` is judged on the base one, and the module says
so. Nothing installed here ships one.

### Tests and verification

`tests/test_stratobj.py` (65 checks) is new: a file written in the suite with
no map (every edit shape, the short form both ways, a section opened after the
last one, under Reforged's banner and in front of DaC's, a move, a stale record
refused, a save and its undo), the vocabulary with and without its two files on
disk, all four installed campaigns (every real line through the writer, the
panel's view with no fatal finding, and four real plans diffed), and the routes
on a copy of DaC's imperial campaign with two saves undone byte for byte.

Driven in the browser against a scratch copy of DaC's data with a scratch
config: a watchtower placed by the pin, dragged a tile, pinned into
Northern Harondor and filed under it with the button, and a DaC fort deleted;
the Log showed four 🏰 entries and undoing them left the file byte-identical to
DaC's own.

## Phase 22b - Resources, and the snap - done 2026-09-11

**Closes D9, D10 and G5.** The second half of placing things on the map: the
trade resources through 22a's writer, D10's "no, but here" for every placement
rule the toolkit has, and Geomod's Localize.

**Scoped as:** resources are the same operation over 1,131 records, with the
marker and duplicate rules reused rather than rewritten; a spiral search over
the predicate we already have; every object type places, moves and deletes,
byte-exact outside the lines the plan named; Localize gets its equivalent.

**Built:** `stratobj.py` gains `resource` in `KINDS`, `Layout`, `layout_of`,
`resource_home`, `filed_under`, `Census` and `Vocabulary.snap`; `mapsnap.py`
is new; `campmap.campaign_map` and `campmap.map_of`; `mapcheck.position_faults`
and `mapcheck.duplicate_message`, which the validator's two resource rules and
18b's event rule now report through; `campaint._marker_near` and
`stratchar._shore`. In the browser, `campforts.js` places, lists and edits
resources and draws D10's button, `stratchar.js` draws it for a character,
`campmark.js` drags a resource, and `campmap.js` has `cmapLocate`.

**What the files say, measured on all four installed campaigns (2,813 lines).**

* **They are written at the top, and each file groups its own.** Every one
  sits between the campaign header and the first faction. Reforged's imperial
  campaign heads each group with the province's name as a comment - 90
  headings, and 410 of its 413 resources stand in the province theirs names -
  so a new one joins its province's group, and a province with none gets a
  heading of its own, the way a fort gets a section. DaC's two and the
  Fellowship campaign keep each name's lines together (25 names, 25 runs), so a
  new one follows the last of its name. That is read off the file every time,
  never configured.
* **What is fatal is the engine's vocabulary.** All 2,813 name a resource their
  mod's `descr_sm_resources.txt` declares, so a name it does not declare is
  refused, with the list; with the file packed, nothing is checked. Off the map
  is fatal. Sea (6, 0, 108 and 0), impassable land (7, 9, 4 and 4), a tile in no
  province and a second one of the same name on a tile (1, 63, 2 and 0) are
  warnings, each quoting this campaign's own count.
* **A resource may stand on a marker.** 16g's rule, and DaC does it once in
  each campaign: the province that owns the settlement pixel owns the resource.
  None of the 2,813 shares a tile with a fort or a watchtower, so either on the
  other's tile is said.
* **The Fellowship campaign's resources are in the sea on both maps.** It ships
  its own full set of map files, the same 510x487; the toolkit now judges it
  on those (`campaign_map`), and 108 of its 222 resources and 72 of its 150
  characters are still on sea tiles. The file was written for another map, and
  the panel says so line by line rather than the toolkit hiding it.

**The snap.** `mapsnap.nearest` walks out from the tile nearest first and hands
each tile to the caller's own rule, giving up at 40 tiles, because a tile
further than that is somewhere else. Four callers: a fort, watchtower or
resource (`Vocabulary.snap`, which looks inside the province it is filed under
first, over raw bytes so DaC's 1,531 records check in about 100 ms), a
character (land, or sea for an admiral), a settlement or port pixel in the
wizard (`marker_faults` unchanged, inside the region's own colour), and the
validator's sea findings for resources and 18b's events. Each says where, how
far and in which province, and the two panels put a **⌖ Move it to** button
on it that fills the form and plans again.

**Localize.** A ring that closes from 90 pixels onto the tile over a second,
drawn over the markers, from `cmapGoTile`, so ✓ Check, ⌕ Query and a fort's ◎
all get it. With reduced motion asked for it is drawn closed and still.

**17d's drag never dropped.** In drag mode the pointer's travel was never
counted, so `pointerup` always read a marker drag as a click. 22b found it by
dragging a resource with the pointer; 22a's browser check had driven the drop
function, which is why it passed. One line, and every drag since 17d works.

### Tests and verification

`tests/test_stratres.py` (67 checks) is new: a file written in the suite with
DaC's and Reforged's shapes (every edit, both grouping rules, a first resource
under a banner and in front of a faction, the name rules with and without the
list on disk), the search, the map a campaign reads, all four installed
campaigns (the panel and the validator agree on the duplicate and sea counts,
every D10 answer is land in a province and free, and real edits, deletes,
adds, a heading move and a new heading each differ only where planned), the
character and marker snaps on a real map, and the routes with two saves undone
byte for byte. `test_stratobj.py` now covers resources in its byte-for-byte
render of every real line.

Driven in the browser against a scratch copy of Reforged's map and imperial
campaign with a scratch config: an iron placed by the pin under the
Talsir_Province heading, dragged by the pointer into South-Umbar_Province,
listed under it with the button, put on a sea tile and moved back with ⌖, and
the Localize ring shown on it. The Log showed four ◆ entries, and undoing
them left `descr_strat.txt` byte-identical to Reforged's own.

## Phase 22c - A campaign's own map - done 2026-09-11

**A follow-up to 22b, taken on the user's word.** 22b made the two writers that
judge a tile read a campaign's own copy of a map file. The map screen, the
validator and its fixes still read `world/maps/base` for every campaign, so a
campaign that ships its own map was drawn and judged on the wrong one.

**Measured first.** Across the base game and both installed mods, five
campaigns ship map files of their own. Every DaC and Reforged campaign ships a
`map_FE.tga` and nothing else a judgement reads. Vanilla's `norman_prologue`
ships eight layers and neither text file. Reforged's Fellowship campaign ships
all twelve: the same 510x487, 2% of its region tiles and 7% of its ground
types different, and one island the base map does not have. On the base map,
✓ Check named `world/maps/base/descr_regions.txt` nine times for it, and
vanilla's prologue had 60 warnings where its own map has 49.

**Built.** `campmap.shipped`, `campaign_home`, `layer_map`, `rel_of`,
`base_readers` and `home_view`, with 22b's `campaign_map` now sharing one cached
object per campaign folder. `Registry.map_for` is what every map read route
and the fact table use; the palette stays on the base map. `mapcheck` names
the file each finding is in through `Check.rel`, the height fix writes that
copy, and the `map.rwm` it deletes is the one beside it. `campaint.paints_for`
refuses a stroke, or the start of a new province, while a campaign that does
not show the base map is on the screen. It names that campaign's files and the
campaigns that do show it. In the browser, the manifest, layer, legend and
probe requests carry the campaign, `cmapRefetchMap` swaps only the layers
whose file changed when the campaign does, `cmapHomeNote` says under 🏰
Campaign where the map comes from, and the Paint button says why it will not
arm.

**Two rules kept apart on purpose.** A campaign whose only copy is
`map_FE.tga` is judged on the base map's own object, the one the brush paints,
so an unsaved stroke is still seen by every campaign that reads it. Only that
one layer is drawn from the campaign's folder. And `base_readers` is stricter
than B1's `reads_base`, which asks about `map_regions.tga` alone because a new
province is a regions question; a stroke on the heights is not.

### Tests and verification

`tests/test_campaignmap.py` (30 checks) is new. It builds a copy of a real mod
with two campaigns: one that ships only `map_FE.tga`, and one whose own
`map_heights.tga` sinks a settlement. It checks which object each is judged
on, which file each layer comes from, what the screen is told and when the
brush is refused. On the validator, the finding names the campaign's file, the
height fix writes it and deletes the campaign's `map.rwm` while the base's
stays. It drives the routes (manifest, layer bytes, probe, check, a refused
stroke, the palette) and covers every installed campaign.

Driven in the browser on a scratch copy of Reforged's map and both its
campaigns. Opening Fellowship swapped the region pixels, and the note and the
Paint refusal showed. An armed brush was put down on the switch, with the
reason. ✓ Check named Fellowship's files, and switching back restored the base
map.

---

## Phase 23a - The texture composite - done 2026-09-12

**The map drawn with the game's own aerial-map ground textures.** Closes half
of D7 and T1, which are the same feature with two implementations to compare;
TWMapReader's is the better specification and it is the one that was taken.

**Its rules, as they stand.** A texture that cannot be found is drawn **pink**
and reported, not skipped and not rounded to a neighbour - which is this
project's "a rule with no evidence reports nothing" applied to a picture,
arrived at independently by somebody else, and the strongest argument in the
audit for his version over Demir's. A climate colour `descr_climates.txt` does
not declare falls back to the `default` block. Every climate inherits that
block for anything it does not name itself. **Wilderness is drawn as
fertility_low**, the substitution nothing else has written down and the reason
wilderness is not a hole in every mod. A missing winter column falls back to
the summer one, and so does a whole climate with no `winter` line. A texture
spans 32 tiles at its own size (`SCALING = 1f/32`), and the repeat is anchored
to the map's origin, so two neighbouring tiles of one texture continue each
other instead of showing two copies of the same square.

**What is ours rather than his.** He reports only a texture the folder does not
hold; a tile can also have no texture because nothing names one for its
(climate, ground type) pair, and both come out pink, so both are counted and
named. The live case of the second is the tile whose height says land and whose
ground type says sea - DaC has fifteen, the 70-tile disagreement 16a measured,
and nothing reported them before. That finding names `map_ground_types.tga` and
`map_heights.tga` rather than the texture table, because the texture table is
not the thing to go and fix.

**Built.** `unittransfer/mapterrain.py`: `parse` and `Vocabulary` for
`descr_aerial_map_ground_types.txt` (the file, then the file plus the four
engine rules, kept apart so a test can say which of the two a wrong texture came
from), `plan` for which texture every tile asks for and every reason one has
none, `composite` for the picture, `check_textures`, `signature` and `view`.
`GET /api/map/terrain` answers the facts, and with `format=png` the picture, out
of `IconCache.cached_png`'s disk cache. `mapcheck`'s `terrain.texture` rule
reports the gaps with a tile to jump to, and skips by name on a mod with no
texture table - the game's own copy is inside a `.pack`, so most mods have none.
In the browser it is a **mode on the ground types row**, not an eleventh layer,
which is 20a's ruling applied again: it is `map_ground_types.tga` and
`map_climates.tga` read the way the engine reads them. That row's own opacity
fades it, its flat colours come out while it is on, and it is drawn under the
whole stack because it is the ground.

**The performance rule held, and it cost a measured optimisation to hold it.**
The picture is built once and neither a pan nor a zoom rebuilds it: the browser
fetches one PNG (DaC 2040x1948, 3.1 MB) and blits it, 0.3 ms a frame at zoom 10.
The plan behind it is kept per map and shared by the panel, the picture and the
validator's rule. The rule still has to fit inside the whole rule set's
one-second bar, and the two exact colour-to-index passes were 160 ms of it. They
are now 10 ms, in Pillow's C and still exact: each band is replaced by the
**rank** of its value among the ones that occur, red and green packed together
and then ranked again over the pairs that really occur, so three ranks fit in one
byte and the lookup is two adds and four `point`s. Rank 0 means "not a value this
layer uses" and every known colour's ranks are 1 or more, so a pixel that misses
in any band lands on a code no known colour has. It falls back to the
tile-at-a-time pass if a layer will not pack, and `UT_TERRAIN_SLOW` forces that
path so the suite can compare the two.

**The sea is flat, deliberately.** The aerial ground-type file has no sea entry
because the engine draws the sea from `terrain/aerial_map/sea` and `water.tga`
by another mechanism entirely, so a flat colour is the honest thing to put where
we do not know. TWMapReader does the same.

**The cache key is the pixels, not the files.** This screen has a paint tool on
it: a stroke on the ground types changes the map object and nothing about the
file until somebody saves, and a composite keyed on timestamps would go on
showing the terrain before the stroke. So the key is a hash of the two layers'
tile-per-pixel bytes and the sea mask, plus stats of the two text files and of
every texture the aerial file names. A stroke marks the picture stale and the
panel offers `↻ Redraw` rather than rebuilding per stroke, which would be
exactly the lag 16c was written against.

### Tests and verification

`tests/test_mapterrain.py` (63 checks) is new. A six-by-four map is written
here with every rule of the feature given a tile of its own, so each is read off
the picture by coordinate rather than inferred from a total: the climate's own
entry, an inherited one, the wilderness substitution, a one-column line, an
undeclared climate colour, a texture named and never written, a pair nothing
names, the sea-ground-on-land tile, and a row of sea. Then the winter column and
its two fallbacks, the composite's phase, the validator's three findings and
the file each names, the two routes including the disk cache, and every
installed mod - where the packed index is checked byte for byte against the
tile-at-a-time one (19x and 24x quicker) and the validator is checked to report
exactly the gaps the plan measured.

`tests/test_mapcheck.py`'s clean map now ships a texture table, so the new rule
runs on it rather than skipping; all 86 of its checks pass and the rule set runs
in 626 ms on DaC, 505 on Reforged and 122 on vanilla.

Driven in the browser on both installed mods and on Reforged's two campaigns:
the composite drew, the panel said 50 textures and 15 pink tiles on DaC and 57
and none on Reforged, the ✓ Check panel carried the five findings with their
tiles, one of them was jumped to and the pink was there under the region layer,
the habit survived a reload, and ticking the ground types layer off while the
terrain was on left the map drawn rather than black.

---

## Phase 23b - Winter, and the tint - done 2026-09-12

**Closes T12, and the winter half of T1.** Phase 23 is finished, and with it D7
and T1 entire.

### Winter

23a built the season in and drew one of them. `descr_aerial_map_ground_types.txt`
writes two texture columns a line, `Vocabulary.texture` has taken a season since
the day it was written, and `plan`, `composite` and `view` all carry it, so the
whole of this half is a switch on the ground types row, one picture kept per
season and one line of cache key. Measured: **99,000 of DaC's tiles and 166,898
of Reforged's are drawn with a different texture in winter**, and the north of
both maps goes under snow.

**The validator judges both seasons, which is TWMapReader's rule and not an
extra.** He collects a tile's summer texture and its winter one before loading
any of them, and his error line says which of the two the example tile came
from. A winter texture that is not on disk is missing whether or not winter is
what is on the screen, and a rule that only judged what happened to be drawn
would pass a map in July and fail it in January. `mapterrain.season_gaps` runs
the plan twice and merges, because most gaps are in both and two identical
findings a season apart is one fault reported twice; the fingerprint is
unchanged, so a baseline stamped before this still covers them. The second
season costs the index pass again and a probe of the textures the first did not
use, which is why `check_textures` now takes a `seen` and reads each file once
across both. The whole rule set: **739 ms on DaC, 534 on Reforged, 122 on
vanilla**, against the one-second bar.

### The tint

**T12's HSB fill, and it is the canvas `color` blend.** His is a grayscale
filter followed by an `HSBAdjustFilter` set to the tint's hue and saturation;
the blend takes the hue and saturation of the source and the luminosity of the
backdrop, which is the same operation in one step and in hardware. His
brightness stretch and its two cutoffs have nothing to port: they exist because
his filter *replaces* the brightness and has to be stopped from crushing the
relief, and the blend never touches it.

**The colouring had to move to do it.** It was drawn last into the layer
composite, which is one pixel a tile; the terrain is four, so it is blitted
straight to the screen. A colouring blended against the composite alone would
have been a tint of the wrong picture. So `cmapThemeDraw` draws it onto the
screen canvas after both, and the composite's cache key lost the two overlay
terms it no longer decides. One thing fell out for free: the opacity slider is
now a repaint rather than a rebuild of a megapixel canvas per pixel of travel.

**Two canvases, not one.** The fill blends; the frontiers never do. A border
colour is a near-black with almost no saturation, and a `color` blend of that is
a grey wash rather than a line - it would delete the borders exactly when the
tint made them most necessary.

### The borders, and the two faults the port found

`edge` is the hairline on the frontier that belongs to neither side, which is
what both ends already drew. `inside` marks every tile of a group that touches a
different one, so both sides carry it: TWMapReader's `borderPosInside`, and the
one that still reads once a hairline has disappeared into the zoom or into a
texture. His third control, `StrokeRenderType` (`PURE`/`NORMALIZE`), is a Java2D
stroke-control hint for the vector outline his "over edge" mode strokes at a
width and a repeat count; there is nothing to port, because this draws tiles and
a tile is either the frontier or it is not. `showBordersAllRegions` is the
`Every province` choice, which is the same pass with each province its own group.
On DaC's faction map: 4,919 border tiles on the edge between groups, 8,480
inside, 10,477 and 17,822 for every province.

**The screen and the export were drawing different frontiers, and had been since
16g.** The panel says they are the same picture. The browser keyed its group ids
on each province's own colour, so it drew a line round every province; the
export keyed on the group's colour, so it drew frontiers between blocs. The
comment above the browser's loop described the export's behaviour. Both are
right now and a suite runs both over one map to keep them that way.

**And a colour cannot say which group a province is in.** Fixing the first fault
uncovered a second: a presence map has a real group whose label is "none" and
whose colour is `NO_GROUP`, which is the same grey a province in *no* group is
painted. Reading the group off the colour puts a frontier round every ungrouped
province. So `Colouring.payload` now sends `bands` beside `colours` - the group
index per province, `-1` for one the colouring says nothing about, absent for
anything that is not a province - and `_every_region` makes the same test.
`cqGroups` reads that and infers nothing.

**The borders tickbox now means what it says.** Each colouring carried its own
yes-or-no and only the three themes said yes, so ticking "political borders" on
an information map did nothing at all. The tickbox is the switch; the
colouring's own flag is the export's default when the panel does not send one.

### Tests and verification

`tests/test_mapquery.py` gains section 3b, 10 checks, and the last four are the
point: **the browser's own border pass, run in node against the server's, over
one map, in all four combinations.** `campmap.js` and `mapquery.js` load into a
bare V8 context as they ship - no DOM, no second copy of the maths - and
`cqGroups` and `cqBorders` are pure so they can be called directly. Both faults
above were found by writing that check, not by reading the code. The suite is
109 checks and passes.

`tests/test_mapterrain.py` (63) and `tests/test_mapcheck.py` (86) both pass with
the two-season rule. Driven in the browser on DaC: the season switch, both
pictures kept, the tint over the textures with the rivers and mountains still
reading through, both border positions, both scopes, the export honouring them
(71 KB inside-and-every against 44 KB edge-and-groups), and a saved view
carrying all of it while one saved before 23b opens solid, on the edge, between
groups.

## Phase 24 - Make and unmake - done 2026-09-12

**Closes G1 and M15, and with them the roadmap.** Two operations on a thing that
had a create or a delete but not both: we could make a province and not unmake
one, and we could edit every file in a campaign folder and not make the folder.

### G1 - deleting a province

`unittransfer/regiondel.py`. Geomod's manual describes this in two sentences and
admits the bug in a third: "resources, forts and characters will remain". That
admission is why this is not a port.

**A delete is a rename to nothing**, so it walks 19b's site list rather than a
new one. `renames.REGION_SITES` is the measured set of every file a province is
named in - fifteen in Divide and Conquer, twelve in Third Age Reforged - and
each site here is the same file found the same way, edited by removal instead of
by substitution: the record out of `descr_regions.txt`, the settlement block out
of each `descr_strat.txt`, the name off both `hold_regions` lists, out of its
mercenary pool, off its music type's `regions` line, out of the lookup pair and
out of the custom battle tiles. The one site a rename refuses to follow is
refused here for the same reason and in the same words: the campaign script is a
grammar nothing parses, so every line of it naming the province is listed with
its number and none of it is written. `renames._scan_mentions` became the public
`renames.mentions` so that both use one scan.

**The land goes whole to one neighbour it touches.** The manual says "usually an
adjacent one" and does not say which; the panel offers every neighbour ordered
by how much border it shares and defaults to the longest, which is the rule B1
already uses to pick a music type. Splitting the area between several neighbours
is what a tile-by-tile nearest search would do and it cannot be made safe: 16e's
own rule is that a province in two pieces is two provinces as far as an army is
concerned, and a piece handed to the nearest neighbour is not provably joined to
it. One adjacent heir is, because the two areas are each contiguous and share an
edge. The plan still counts the tiles of the deleted province that no path of
its own reaches the heir by, and warns in 16e's words when there are any.

**The settlement goes with the land and the port is a question.** A province has
one seat, so the black pixel becomes the heir's ground the moment the tiles do -
a second settlement pixel is not a second city, it is `marker.extra`, where one
of the two is ignored. The white port pixel is the same rule with a different
answer: the heir inherits the coastline, so a port it does not otherwise have is
**kept** and a second one is **removed**, and the default follows the heir and
changes when the heir does.

**Nothing else is orphaned, and saying that is the finding.** The resources,
forts, watchtowers and characters the manual leaves dangling are placed by tile
and not by province: their coordinates do not move, so what changes is whose
province they stand in. The panel counts them per campaign and names the heir.
The single exception is `descr_strat.txt`'s depth-0 `region <name>` section,
which files forts and watchtowers under a province name - that one really is a
dangling reference, and it is moved into the heir's section or, when the heir
has none, renamed to it, which keeps every line of it.

**`mapsnap.nearest` was not needed, and that is a result rather than an
omission.** The brief expected the search; there is nothing to search for. A
delete moves no coordinate, so no rule about where a thing may stand can be
broken by one.

**A delete renumbers and a rename does not.** Region IDs are first-appearance
order in a row-major scan of `map_regions.tga`, so the warning 16e gives when a
province is created is given here read backwards, off the same number.

The refusals: an heir that shares no edge (naming the ones that do), a province
nothing borders at all, the last region in the file, and a name no record
declares. A record with no pixels at all is the opposite case and is allowed
without an heir, because deleting it is the fix for it.

### M15 - making a campaign

`unittransfer/campnew.py`. Every file inside a campaign folder already had a
writer - 16h, 16i, 16j-1, 16j-2, `winconds`, 18a, 18b - and there was no way to
make the folder. It is a copy of a campaign that works, because the engine reads
more than a dozen files out of that folder and a missing one is a load failure
with nothing on screen to explain it. Three things a plain folder copy gets
wrong, and they are the whole feature:

* **`map.rwm` does not travel.** It is the engine's binary cache of the map, and
  a copied one is the source campaign's map, loaded in preference to the new
  campaign's own files. Left behind, and the change line says why.
* **The header is set to the new folder's name.** `descr_strat.txt` opens on
  `campaign <name>`, and a copy that keeps the source's opens claiming to be the
  source. The two are allowed to disagree - DaC's `custom/Shattered_Alliances`
  says `campaign imperial_campaign` and runs - so this is a choice, and it is
  the one that leaves the copy self-consistent. It is the only line of any
  copied file that changes.
* **The new-game menu has to be told.** 18a's keys are built from the folder
  name, so a copy inherits none of them and the menu would show raw keys. Every
  `SOURCE_*` key is written again under the new token - the faction titles and
  blurbs as they stand, because they are the same factions - with the campaign's
  own title and blurb overridable, and an inherited title warned about.

**Where the folder goes is the thing this screen knows and the engine does not
say.** `campstrat.campaigns`' own measured rule is that the new-game menu reads
the folders directly under `world/maps/campaign`; both installed mods keep a
whole second campaign one level down, which this toolkit opens and the menu does
not. So a nested name is offered and warned about rather than refused.

`campfiles._write_descriptions` became the public `write_descriptions(mod,
writes, new, keep, file_op)` so that both the descriptions panel and this write
the two roads - the `.txt` when there is one, the compiled archive when there is
not - from one copy.

### What it costs, measured

A delete's panel opens in 231 ms on DaC and the plan takes 7 s cold and 760 ms
warm, nearly all of it the whole-mod mention scan a rename also pays for; the
panel is two steps for that reason, and the second button says it is going to
think. A campaign copy is planned in 30 to 50 ms and the plan says the size:
DaC's grand campaign is 118 files and 172 MB, its nested one 92 files and 4.9
MB, Reforged's Fellowship campaign 36 files and 59 MB.

### Tests and verification

`tests/test_regiondel.py` (62) builds a six-by-seven map with four provinces
laid out so that every rule has something to be right about - a default heir, a
short border, a neighbour that touches nothing, a settlement pixel, two ports
where one heir has one and the other does not, and the eight files naming one
province - deletes one, and reads the result back off disk. Its water is painted
`41 140 233` and declared by nothing, which is what a real map does: all 73,902
of DaC's sea tiles are that colour and no record claims it.
`tests/test_campnew.py` (52) does the same for a campaign folder with a
subfolder and a stale `map.rwm`. Both suites end on every installed mod,
planning a real delete and a real copy and applying neither.

Driven in the browser on Divide and Conquer: the delete panel over
Pukel_Province (517 tiles, seven possible heirs ordered by shared border, two
campaigns, a fort and two resources standing on it), the seven files its plan
would write, and the new campaign form planning a 118-file copy - with both
saves driven through a stubbed `api.post` so that the installed mod was checked
afterwards and had not been written to.

---

## Phase 29 - The strat model viewer, and the art that is there but unreadable - done 2026-09-12

**Reported from the beta: the strat models viewer flickers and then turns into
a normal cube, or nothing.** Reproduced on 2026-09-12 and traced the whole way
down. The scoping called it four faults in a row and it was five - and the
first one, the one the scoping got wrong, is the whole bug. Every level was
fixed anyway, because each is wrong on its own and the next mod to trip one
will not trip it in this order.

### The root, and the scoping had it backwards

The scoping said the art was inside a `.pack`. It is not. **It is loose, in the
same folder, under a different extension.** A mod's packer converts each
`.tga` to a DDS named `<name>.tga.dds` and **truncates the original to zero
bytes rather than deleting it**. `cas.texture_path` already knew about that
name - its own docstring called it "how the packer leaves them" - but it tried
the candidates in the order the material writes them, took the first that
*existed*, and a zero-byte file exists. So the stub won every time and the real
art, sitting beside it, was never opened.

Measured over both installed mods: Divide and Conquer has **1,172** zero-byte
`.tga` under `data/models_strat` and Third Age Reforged **two**, and **1,171 of
the 1,174 have their real DDS beside them** under exactly that name. The three
that do not are all called `XXXX...`, which is the modders' own mark for a file
they have switched off. Nothing else in either mod is zero bytes: the whole
1,173-file set of empty art in Divide and Conquer is inside `models_strat`.

The fix is one rule: **an empty candidate never wins over a later one that has
bytes in it.** One `stat`, no decode - whether the bytes are a picture is
`icons`'s question, asked once and cached. An empty file is still returned when
it is the *only* thing there, because that is a fault the layers above now
report and collapsing it back into "absent" is the mistake this phase undid.

After it, a sweep over all **926** of Divide and Conquer's `.cas` files finds
**no material at all** that resolves to a file which will not decode.

### The four levels above it, each wrong on its own

1. **`icons._decode_to_png` answered a file it could not read with
   `_BLANK_PNG`**, a 1x1 fully transparent PNG, because it caught every
   exception. `png_bytes` already separated a file that is *not there* - mods
   ship the art they changed and leave the rest to the game, so a missing file
   really is blank - but a file that is there and will not decode came out the
   same. It now returns `None`, and `png_bytes` decides what that means.
2. **`/model_texture` therefore answered 200 with 67 bytes**, the browser's
   `Image` loaded it, and `v3Fetch`'s `onerror` path never ran. It now passes
   `strict=True` and answers **415** carrying the measured sentence.
3. **The viewer believed the sheet**, uploaded it and set `uHasTex = 1`. It now
   refuses a degenerate sheet even on a 200 - 1x1, or transparent everywhere,
   the second sampled through a 32x32 canvas so a 2048 sheet costs a thousand
   pixels to check instead of four million. Our own server no longer serves
   one; the next server to do it will not be ours.
4. **`V3_FRAG` then discarded the model.** `if(base.a < 0.35) discard;` is the
   cut-out rule, and it is right for a unit's `.mesh` - it is what makes a
   plume a plume - but against a 1x1 transparent sheet it discards every
   fragment of every group that names a texture. It is now gated on a
   `uCutout` uniform, set from which format is loaded.

**The cube was the one group with no material at all.** `anduin_city_4.cas`
has 44 groups; 43 name a texture and vanished, and `symbol` names none, so it
drew flat: 36 indices, twelve triangles, a box. **The flicker was the model
drawn correctly** for the frames before the images landed.

### What the person looking at the screen gets

A grey model with no explanation was the fault that was reported, so the panel
says **why**, measured: the failing sheet is named on the facts panel with the
server's own sentence, and the mesh row that uses it says *will not load*
rather than *not in this mod*. Those two were the same label and are not the
same thing. The sentence is fetched once, on the failure path only - an
`Image` cannot read a 415 body, so `v3AskWhy` re-requests the URL and reads it.

### B4, taken in the same session as planned

`Rename slot` refused on a mod with `descr_sm_factions.txt` packed, and the two
really did share a root even though Phase 29's turned out to be a different
one: a file the tool cannot read, and nothing saying so. `renames._names` read
the slot list off disk, got an empty list, and `_validate` refused **every**
faction with *there is no faction slot called X in <mod>* - a claim about the
faction, and untrue. `factions.overview` refused the whole screen with a
different sentence about the same absence, which is how the two came to
disagree.

`factions.no_file_note` is now the one place that sentence is written and both
callers use it. It is measured: `packs_beside` looks in the mod's own `packs/`
and, when the mod sits under a folder called `mods`, in the install's - and an
**empty** `packs` folder is not an archive, which matters because Third Age
Reforged has one. With no archives anywhere the sentence claims nothing about
packs. Verified on this machine: vanilla has no loose copy, Divide and Conquer
and Third Age Reforged both do, and the install ships six archives.

A slot that genuinely is not in a file that *is* there still gets the old
sentence, which is the half that was right.

### Both lines

`png_bytes` is the disk-cached PNG route for unit cards, faction symbols and
model textures, so this reaches the unit editor and the BMDB browser too - and
deliberately does **not** make either noisier: absent stays blank and stays
quiet, `strict` is opt-in, and the only grids that change are the ones that
were lying. The blank served for an unreadable file is no longer cached either,
so replacing the file is enough to fix it.

**Shipped:** `cas.texture_path` + `cas._has_bytes`; `icons.ArtUnreadable`,
`icons.fault`, `png_bytes(strict=)`, `_decode_to_png -> Optional[bytes]`;
`/model_texture` 415; `factions.packs_beside` + `factions.no_file_note`;
`renames._validate`; `web/js/viewer3d.js` - `uCutout`, `v3Degenerate`,
`v3AskWhy`, `v3TexFault`, `v3FaultRows`. `tests/test_stratart.py` (40).

---

# Split out on 2026-09-23

Moved out of `ROADMAP.md` verbatim on the user's word ("shorten our roadmap"), in the
order it stood there: the finished backlog, every phase from 18 to 64 with its
write-up, the upstream passes, and the rated-list preamble and done rows.

# Backlog

Everything below is work still to do, in the order it will be done.

The forty open items in `docs/upstream/REFERENCE_GAPS.md` were classified by the user on
2026-09-05: **20 Now, 7 Next, 13 Later, none skipped.** The Now set is Phases
18-21 and cuts as **3.1.0**; the Next set is Phases 22-24 and cuts as **3.2.0**;
the Later set is a table at the bottom of this file and is not phased until it
is scheduled. Each phase below names the audit ids it closes, so the two
documents can be checked against each other.

### The version numbers moved, and this is the reason

Until now the three future releases were named `V3.1`, `V3.2` and `V3.3` after
the *features* in them - the OSM backdrop, the map resize, the layer generators.
None of those three is in the Now or Next set, so all three would have shipped
after work that had no number at all.

**Future work gets a phase number, and a version number is assigned only when
something is cut.** That is how Phases 0 to 16 worked and it is what stops this
happening again. So the OSM backdrop is **Phase 25**, the map resize **Phase
26**, the layer generators **Phase 27**, and their old `V3.x` labels are retired.
The `notes` fields in `docs/upstream/PORT_MANIFEST.json` that said "deferred to V3.1" and
"deferred to V3.3" are updated to the phase numbers in the same commit as this
change, so no cross-reference dangles.

### What ships when

| Version | Phases | What it is |
|---|---|---|
| **3.0.0** | 16a-16k, plus 17 | The campaign map editor, and the correction pass over it. Feature-complete and uncut. |
| **3.1.0** | 18-21 | The twenty Now items: the campaign files that had no editor, the names nothing could follow, and the map screen's second pass. |
| **3.2.0** | 22-24 | The seven Next items: placing things on the map, a map that looks like the campaign map, and making or unmaking a region or a campaign. |
| next, block one | ~~29~~, ~~40~~, ~~31~~, ~~42~~, ~~41~~, ~~43~~, ~~28a~~, ~~28b~~, ~~33~~, ~~30~~, ~~34~~, ~~35~~, ~~36~~, ~~37a~~, ~~37b~~, ~~38~~ | **The campaign map. Finished.** 29 landed on 2026-09-12; 43, 28a, 28b, 33, 30 and 34 on 2026-09-15; 35, 36, 37a and 37b on 2026-09-16; 38 on 2026-09-17. Beta except 40, 42, 41 and 38, which were subreleases on both lines. |
| next, block two | ~~32a~~, ~~32b~~, ~~32c~~, ~~39~~ | **The mercenaries. Finished**, all four on 2026-09-17. Beta except 39, which was both lines. |
| after block two | ~~44~~, 45, 46, 47a, 47b, 48 | **The reference-tool pass of 2026-09-13.** Five sessions left, every one a subrelease on both lines. Outside both blocks, and scheduled only because the user named the work. **44 landed on 2026-09-20**; 45 leads. |
| after that | the Future roadmap list | Rated and unscheduled. Three five-star items lead it: M17, M12 and M16. |
| later | 25-27, and the Later table | Not scheduled. |

### The whole plan on one screen

**Fourteen sessions left of the fifteen.** Phase 17 (2026-09-06), all of
Phase 18 (2026-09-07), all of Phase 19 (2026-09-09), 20a (2026-09-10), 20b,
B1, 20c, 21, 22a, 22b and 22c (2026-09-11), 23a, 23b and 24 (2026-09-12) and
**29 with B4 inside it (2026-09-12)** are done and their write-ups are in
`ROADMAP_ARCHIVE.md`; nothing in the Later table is counted, and neither are
B2-B3 below.

**Nothing was released until it was done**, and then it was: Phase 24 closed
on 2026-09-12 and the whole backlog went out the same day as v2.3.0 and beta
2026-09-12, the held v2.2.4 and beta 2026-09-11b notes folded into it. That
discharged the instruction of 2026-09-11, and the cut-as-it-lands rule came
back for exactly one session: Phase 29 went out on 2026-09-12 as v2.3.2 and
beta 2026-09-12c. **It is suspended again from that same day** - work is
committed to master and the user says when it is cut. `STATE.md` carries the
current standing.

---
# Reported from the beta - not phased

Four items off beta users between 2026-09-09 and 2026-09-11. They are not from
the reference audit, so they have no `D`/`T`/`M` id; they are numbered `B` and
they are **not** scheduled into the phases above. All three open ones were
rated on 2026-09-12 at four stars each and live in *Future roadmap* with the
rest of that rating; the detail stays here because it is longer than a table
row. **B1, the crash, is done** (2026-09-11) and **B4 is done** (2026-09-12,
taken inside Phase 29 as planned); both write-ups are in `ROADMAP_ARCHIVE.md`.
B2 and B3 wait.

| id | Item | Size | Note |
|---|---|---|---|
| B2 | Delete a settlement, and move one between mods | M | Half of what was asked for already exists - see below before building anything. B1 added the create. |
| B3 | Insert and export one file at a time, the way Mylae's tool does | M | The user's own words: "that isnt really needed tbh". Lowest of the three. |
| ~~B4~~ | ~~`Rename slot` is refused on a mod that keeps `descr_sm_factions.txt` packed~~ | S | **Done 2026-09-12**, inside Phase 29. `factions.no_file_note` is the one sentence, and the rename screen and the Factions screen both use it. |

## B2 - delete a settlement, and move one between mods

Read this before building: **assigning a settlement and its buildings to a
faction already works.** The settlement panel (16h, `stratedit.plan_settlement`)
takes an `owner` and a `place`, and an owner change is one slice of lines moved
from between one faction block and another - with the capital rule attached,
because the first settlement in a faction block *is* that faction's capital. The
buildings list on the same panel adds, removes and reorders. What is missing:

* **delete a settlement block** - the panel edits and moves, and there is no
  delete. The shape is `stratcamp._delete_splice`'s, which already unmakes a
  whole faction entry.
* **create one** - **the writer exists since B1**: `stratedit.new_block` and
  `plan_new_settlement` add a village last in an owner's block, guarded the way
  16h's edits are. What is missing is a button on the settlement panel for a
  province that has none, and that is all.
* **move one between mods** - `transfer.py` is the model, and `pack.py` already
  does the import-and-conflict-report shape for units. Bigger than the other
  two; probably its own session.

Phase 24's warning applies to the delete: a settlement that goes has characters,
armies and a capital flag hanging off it, and Phase 22 is what makes those
movable.

## B3 - insert and export one file at a time

Mylae's tool lets a file be pushed into, or pulled out of, a mod on its own.
Some of this exists in pieces - `POST /api/map/export` writes Geomod's batch and
a query as a TGA, 16g exports a per-faction TGA, and `pack.py` imports a unit -
and none of it is a general "take this file out" or "put this file in". The user
asked for it and then said it is not needed, so it sits at the bottom.

---
# 3.1.0 - the Now set (Phases 18-21)

Twenty items. Fifteen are S, five are M and none is L, which is what makes
this a release rather than a slog: it is almost entirely files that are already read
and screens that already exist. The common shape is **we know a file well enough
to validate it and not well enough to edit it**, and that asymmetry is what
3.1.0 removes.

**The whole Now set is done**: 18a and 18b on 2026-09-07, 19a and 19b on
2026-09-09, 20a on 2026-09-10, and 20b, 20c and 21 on 2026-09-11. Phase
18's six files are the five nothing wrote and the one the building side could
only refuse against; Phase 19 is the four names nothing could follow; 20a is the
three layers the map screen could draw and not read; 20b is the three ways of
getting to the thing you want, one of which turned out to be three whole
campaigns nothing had ever offered; 20c is the names on the map and the pin;
21 is the faction audit and the raw text editor. All eight write-ups are in
`ROADMAP_ARCHIVE.md`, and 3.1.0 is feature-complete and uncut.

---

## Phase 19 - The names nothing could follow - done

**All four items are closed.** 19a took D4 and D5 on 2026-09-09 and 19b took D2
and D3 the same day; both write-ups are in `ROADMAP_ARCHIVE.md`. What they left
behind and a later phase will use:

- **`unittransfer/namekeys.py`** - every write into a `{key}value` file goes
  through `_write_loc`, which recompiles the `.strings.bin` beside it and joins
  the caller's own backup set. A localisation edit that skips it leaves the game
  reading the old words.
- **`unittransfer/renames.py`** - three subjects on one engine, position-aware
  everywhere because these three namespaces are not clean enough for a token
  walk, and `campaign_dirs`, which finds a campaign folder at any depth where
  `campstrat.campaigns` finds only the top level.
- **two corrections to things that were nearly true** - `descr_names.txt` has a
  fourth section (`surnames`), and `descr_strat.txt` does **not** name a
  settlement. Both were stated confidently in code that had never been measured
  against the second installed mod.

**D1 is in the Later set and is the one this cluster did not make cheaper.**
Changing a region's colour is the same "the identity of a thing is spread across
files" problem with pixels instead of text, and the extra cost is real: region
IDs are first-appearance order in a row-major scan, so a recolour can renumber
every region after it. A rename does not, which is why 19b could be done first.

**G4 is still in Later, and is cheaper than it was.** The legion label is D4 in
miniature and the write it needs is the one 19a added; what is missing is the
paired display name. Flagged, not moved - the user put G4 in Later and that
stands unless they say otherwise.

---

## Phase 20 - The map screen's second pass - done

**All eight items are closed**, across three sessions: 20a (2026-09-10), 20b
and 20c (2026-09-11). The write-ups are in `ROADMAP_ARCHIVE.md`. What the phase
leaves behind for 21 and 22:

- **`cpinButton(what, fn, args)` is the one way a field takes a tile** (20c,
  `web/js/mappin.js`). Phase 22's object dialogs add a pin with that one line,
  and are handed the tile already flipped into the coordinates
  `descr_strat.txt` writes. A second "use the picked tile" button is the thing
  not to write: it selects a province on the way.
- **`clnLayout` is pure and already measured in node** (20c,
  `web/js/maplabels.js`). A fort or a watchtower name placed in 22 goes through
  the same layout as another obstacle rather than a second collision pass.
- **The layer stack is the ten files and stays that way** (20a), and a way of
  looking at the map that is not a layer - the names - is a toolbar switch in
  `cmapLayerState`, so a saved view keeps it.
- **`cmapGoTile` is the one way of arriving somewhere** (20b), and the pin is
  the one way of asking the map for a tile. Between them, no panel needs to
  move the view or read `state.cmap.pick` itself.

---

## Phase 21 - Two screens over data we already hold - done

**Both items are closed** (2026-09-11); the write-up is in
`ROADMAP_ARCHIVE.md`. What it leaves behind for later phases:

- **`factionaudit.Census` is the whole mod's faction census in one pass.** A
  later check about factions - D13's horde start, M12's bulk duplicate - asks it
  rather than re-reading the dozen files, and a new file that should name a
  faction is one reader and one `Check` row.
- **Gap or note is measured per file**, on every installed mod: a gap is a file
  every real faction has, a note one that working factions go without. A row
  added later is classified the same way, never by copying a reference's
  opinion.
- **`factionclone.clone_file` runs one cloner over one file.** The clone and the
  repair share it, so a fix to a cloner fixes both.
- **The raw editor is the escape hatch, and it is always there.** A screen that
  meets a line its parser does not model can offer "open the file as text" with
  `rtOpen(rel, line)` - the audit's file names already do - rather than growing
  a special case.

---

# 3.2.0 - the Next set (Phases 22-24)

Seven items, three of them L. This is where the campaign map stops being a data
layer you can edit and starts being a map you work on.

---

## Phase 22 - Placing things on the map - done

**Both sessions are closed** (2026-09-11), and with them D9, D10 and G5, and
22c followed in the same sitting; the write-ups are in `ROADMAP_ARCHIVE.md`. What it leaves behind for later phases:

- **`stratobj.py` writes every one-line thing that stands on a tile.** A fort,
  a watchtower and a resource are one `plan` with a `kind`. Anything later that
  is one line with two numbers on it is a new `KINDS` entry and a "where it
  goes", not a new module, and its guard is the one to keep.
- **`mapsnap.nearest` is the search, and every rule keeps its own predicate.**
  A new placement rule gets D10 for the price of a lambda, and the finding
  carries `near`. 24's reallocation of a deleted region's tiles and 26's
  resize both need "the nearest tile that...", and this is it.
- **The map a campaign reads is asked, file by file, everywhere (22c).**
  `Registry.map_for` is the object a campaign is drawn and judged on,
  `campmap.layer_map` the one a single layer is drawn from, and
  `campmap.rel_of` the file a finding names and a fix writes. 23a's textures
  ask `layer_map` which ground and climate layer to composite, and a texture
  built for one campaign is not another's.
- **17d's drag drops now.** The pointer's travel was counted only for a pan, so
  every marker drag since 17d ended as a click. 22b found it by dragging with
  the pointer rather than calling the drop.
- **Localize is `cmapLocate(tile)`,** called by `cmapGoTile`, so anything that
  goes to a tile gets the ring without asking for it.

---

## Phase 23 - A map that looks like the campaign map - done

**Closed 2026-09-12, both sessions, and with them D7, T1 and T12.** It was the
most expensive work in this document and the most visible. The write-ups are in
`ROADMAP_ARCHIVE.md`; what it leaves behind is below.

D7 and T1 are the same feature with two implementations to compare, and
TWMapReader's is the better specification of the two.

### 23a - The texture composite

**Closed 2026-09-12**, and the write-up is in `ROADMAP_ARCHIVE.md`. The map is
drawn with the mod's own aerial-map ground textures, one per (climate, ground
type) pair, and TWMapReader's rules were taken as they stand - the pink missing
texture, the default-block inheritance, the wilderness substitution and the two
winter fallbacks. What it leaves behind for 23b:

- **`unittransfer/mapterrain.py` owns the whole of it.** `Vocabulary.texture`
  is the one place the engine's four rules are applied, and it already takes a
  `season`; `plan`, `composite`, `png` and `view` all do. **23b is a switch on
  the panel and nothing in Python**, unless the tint needs one.
- **`plan` is the cheap half and `composite` the expensive one**, kept apart
  because the ✓ Check panel's `terrain.texture` rule needs the first and not the
  second. A plan is kept per (mod, campaign, season) under a key that hashes the
  pixels rather than the files, so an unsaved stroke is a different picture.
- **`mapterrain._index` is exact and in Pillow's C**, by ranking each band and
  packing the three ranks into a byte. Anything later that needs "this layer's
  colours as one byte a tile" should use it rather than a dictionary pass; it is
  16x quicker and the suite checks it byte for byte against the slow one.
- **T12's tint goes over the composite, not into it.** The composite is under
  the whole stack and the region layer is already drawn over it at 55%, which is
  the arrangement a tint has to keep: 16g's colourings *replace* the region
  layer, and on a textured backdrop replacing it is exactly wrong.

### 23b - Winter, and the tint

**Closed 2026-09-12.** The winter set did double 23a for nothing: the season was
already parsed, routed and keyed, so it was a switch. T12's tint is the canvas
`color` blend, which is his grayscale-then-HSB filter chain in one step. What it
leaves behind:

- **The colouring is drawn on the screen, not into the layer composite.** A tint
  takes the luminosity of what is under it and the terrain is four pixels a tile,
  so anything that wants to blend against the map goes in `cmapThemeDraw`
  alongside it. The fill and the frontiers are two canvases, because a line must
  never blend.
- **`Colouring.payload` sends `bands` as well as `colours`.** The group index per
  province, `-1` for one the colouring says nothing about. A colour cannot answer
  that question - a presence map's "none" group is painted the same grey a
  province in no group is - and anything later that needs to know which group a
  tile is in reads this, never the colour.
- **The screen's pixel passes and the server's are checked against each other.**
  `cqGroups` and `cqBorders` are pure and `tests/test_mapquery.py` runs them in
  node against `_draw_borders` over one map. Two real faults came out of writing
  that, both of them years old. Any later pair of "the browser draws it and
  Python exports it" should be tested the same way.

---

## Phase 24 - Make and unmake - done

**Closed 2026-09-12, and with it G1, M15 and the roadmap.** Two operations on a
thing that had a create or a delete but not both. The write-up is in
`ROADMAP_ARCHIVE.md`; what it leaves behind is below.

- **`unittransfer/regiondel.py` - before anything else has to follow a province
  name.** A delete is a rename to nothing, so it walks 19b's
  `renames.REGION_SITES` rather than a list of its own, and it refuses to edit
  the campaign script for the reason a rename does. `renames.mentions` is that
  scan, public now because two callers share it.
- **`unittransfer/campnew.py` - before anything makes a folder the engine
  reads.** The three things a plain copy gets wrong: the compiled map must not
  travel, the `campaign <name>` header names the copy, and 18a's menu keys are
  built from the folder name so a copy inherits none of them.
- **What a delete does not have to move.** Resources, forts, watchtowers and
  characters are placed by tile, so their coordinates survive a province going:
  what changes is whose province they stand in. `mapsnap.nearest` was expected
  here and was not needed, and that is worth knowing before the next feature
  reaches for it.

### What it was, as scoped

- **G1 - delete a region.** Geomod's manual: "click the name of the region, then
  click Delete, and all work on that region including itself will be gone. The
  area of the former region will automatically be allocated to an existing
  region, usually an adjacent one." **We create regions and cannot delete one** -
  verified: nothing in `campaint.py` or `campmap.py` deletes a record or
  reallocates its tiles. 16e's wizard is the whole other half of this and its
  rules apply unchanged, including the one that refuses to leave any region with
  no tiles at all and the warning that a change here renumbers every region the
  engine scans after it.

  **Improve on the arbiter here rather than copying it.** The manual's own
  caveat is that "resources, forts and characters will remain", which is a
  dangling-reference bug the tool ships. 16f already has every rule needed to
  find them, and Phase 22 has just made every one of them movable, so ours names
  what is about to be orphaned and offers to move it.

- **M15 - create a new campaign.** Make a new campaign folder from an existing
  one. Every file in that folder now has a writer here - 16h, 16i, 16j-1, 16j-2
  and `winconds.py`, plus 18a's campaign descriptions - so what is missing is
  the folder-level operation and the plan that says what a new campaign
  inherits and what it must be given.

---

# The Now and Next sets are finished, and a new set opens

**Every phase in the Now and Next sets is done**, the last of them on
2026-09-12, and the cut they were held for went out the same day as **v2.3.0
and beta 2026-09-12**. That closed the backlog this document was written round.

**Phases 28 to 43 below are what reopened it.** They come from one review on
2026-09-12: three things a beta user reported, one tool cross-reference, a
measurement pass over the four references and the TWCenter archive, and then a
rating pass in which the user gave 38 of the 39 candidates one to five stars.

## The order, and the rule that produced it

**Two blocks, and the user set them: the campaign map first, then the
mercenaries. Everything else waits.** What is not in one of those two blocks
lives in *Future roadmap* below, rated and unscheduled, to be started when the
two main tasks are finished.

**Inside each block the order is: a defect, then the thing later work stands
on, then stars, then size.** That is four rules and each one earns its place.

1. **Phase 29 led because it was the only defect.** Somebody was hitting it
   and it was the only new phase reaching both release lines. Done 2026-09-12;
   **28 is now first**.
2. **Phase 28 is second because every later panel lands on it.** Phase 32's
   screen goes onto the right-hand column, and building it in the old
   sixteen-panel stack is work done twice.
3. **Then five stars before four, and inside a rating, small before large.**
   Phase 33 is three separate five-star **S** items in one session, which is
   why it is third: it is the cheapest five-star work on the list.
4. **A phase that makes another one legible comes first.** Phase 30 is before
   Phase 34 because declaring a climate without its textures produces the
   largest field of pink anybody will ever see here, and 30 is what makes that
   readable instead of alarming. Phase 35 is before Phase 32 for the same kind
   of reason: it is the same two-way panel over a file that is already fully
   parsed, so the shape gets settled on the cheap problem first.
5. **Three phases went in front of 28 on 2026-09-12, and rule 1 is why for one
   of them.** (**40, 31, 42 and 41 are done, so 43 now leads the block.**) Diffing Mylae's `2740b0b..187d9ed` re-scoped Phase 31 and produced
   Phase 41, and the user asked for both immediately; reading our own
   region-creation path beside his turned up **Phase 40**, which is a defect in
   shipped work and therefore leads the block the way 29 did. 28 is still the
   enabler and still comes before everything that lands a panel on it - 40, 31
   and 41 land no panel. **42 and 43 joined them later the same day**, both from
   the user: 42 is a second reported defect and sits behind 40, and 43 is a
   three-way toggle over a file `stratedit` already writes.

### Block one - the campaign map

| Order | Phase | Size | Line | Stars |
|---|---|---|---|---|
| ~~1~~ | ~~**29** Strat model viewer~~ | M | **both** | **done 2026-09-12** |
| ~~2~~ | ~~**40** The new province the engine cannot read~~ | S | **both** | **done 2026-09-13** |
| ~~3~~ | ~~**31** Two river rules, and a ford in the sea~~ | S | beta | **done 2026-09-13** |
| ~~4~~ | ~~**42** The art a clone does not get~~ | S | **both** | **done 2026-09-14** |
| ~~5~~ | ~~**41** Merge one faction's name pool into another~~ | S | **both** | **done 2026-09-15** |
| ~~6~~ | ~~**43** Playable, unlockable, not playable~~ | S | beta | **done 2026-09-15** |
| ~~7~~ | ~~**28a** The strip, and the groups behind it~~ | M | beta | **done 2026-09-15** |
| ~~8~~ | ~~**28b** The toolbar over the canvas, and a steady tooltip~~ | M | beta | **done 2026-09-15** |
| ~~9~~ | ~~**33** T10, G2 and G4 in one session~~ | S x3 | beta | **done 2026-09-15** |
| ~~10~~ | ~~**30** A missing texture without the pink~~ | S | beta | **done 2026-09-15** |
| ~~11~~ | ~~**34** Add a climate zone~~ | M | beta | **done 2026-09-15** |
| ~~12~~ | ~~**35** Rebels right in place~~ | M | beta | **done 2026-09-16** |
| ~~13~~ | ~~**36** D1, change a region's colour~~ | M | beta | **done 2026-09-16** |
| ~~14~~ | ~~**37a** T7, the spawn export~~ | M | beta | **done 2026-09-16** |
| ~~15~~ | ~~**37b** T3, an FE zoom~~ | M | beta | **done 2026-09-16** |
| ~~16~~ | ~~**38** `descr_campaign_db.xml`~~ | M | **both** | **done 2026-09-17** |

### Block two - the mercenaries

| Order | Phase | Size | Line | Stars |
|---|---|---|---|---|
| ~~17~~ | ~~**32a** The pool as a record, and one parser for it~~ | M | beta | **done 2026-09-17** |
| ~~18~~ | ~~**32b** The two directions, and the four gates resolved~~ | M | beta | **done 2026-09-17** |
| ~~19~~ | ~~**32c** Five rules, and the repair for the one that has a safe answer~~ | M | beta | **done 2026-09-17** |
| ~~20~~ | ~~**39** The engine ceilings~~ | M | **both** | **done 2026-09-17** |

**Twenty sessions, and six of them are subreleases.** 29, 40, 42, 41, 38 and
39 touch something outside the campaign map, so each is a subrelease on both
lines; the other fourteen are the beta alone. **29 is done** (2026-09-12) and
took B4 with it, **40 and 31 are done** (2026-09-13), **42 is done**
(2026-09-14), **41, 43, 28a, 28b, 33, 30 and 34 are done** (2026-09-15) and
**35, 36, 37a and 37b are done** (2026-09-16) and **38 is done** (2026-09-17); block one is finished, and **block two is finished too: 32a, 32b, 32c and 39 all closed 2026-09-17**. Both blocks the user set are done; **Phases 51, 52 and 53 come next (added 2026-09-21), then 45 to 48**, each by its own table. **43 was nearly all built already** - 16j shipped the
roster writer and the write-up had not checked - so what landed was the one
sentence of it that was true, the refusal. **28a's scoping held in full**, and
what it did not say was that the layer stack has to be capped or it takes the
whole column. **They are committed, not cut** - cut-as-it-lands was
suspended again on 2026-09-12 and a release now happens when the user asks for
one.

**Six more sessions were added on 2026-09-13 and none of them is in either
block.** Phases 44 to 48 come from the user's pass over Mylae's non-map
screens; all six are subreleases on both lines and all six sit after block two
until the user moves them. They have their own order table in *Phases 44-48*
below.

---
# Phases 28-43 - the campaign map, then the mercenaries

## Phase 28 - The right menu becomes a menu

**Split into 28a and 28b on 2026-09-13.** A second read of Mylae's map screen,
asked for by the user, added two things to what this phase was already going to
touch: the brush belongs over the canvas rather than beside it, and the tooltip
moves. Neither is the strip, both are the same screen, and together they are a
second session. 28a is the strip and the groups exactly as scoped; 28b is the
two things that live over the canvas.

### 28a - The strip, and the groups behind it - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. The scoping held - every
line of it - and three things it did not say were found by building it.**

**The six groups, and the layers outside them.** `CMAP_TABS` in `campmap.js` is
the grouping table: Map (Campaigns, Find, Views), Validate (the read's own
findings, then Check), Query, Paint (Paint, Markers, Events), Province (the
picked tile, Settlement, Characters, Forts, Delete) and Campaign (Campaign
settings, Strat models). Sixteen panels behind six tabs, which is the point -
sixteen tabs would have been the column laid on its side. `#cmLayers` is in no
tab and is asserted to be in none, because 20a's ruling is that the stack is the
ten files the map is made of and it is what the number keys tick.

**Grouping cost the fifteen panel modules nothing.** Each group is a `<div>`
that is hidden or not, and every panel div stays in the DOM with the id its own
module already writes into - so `campbrowse.js`, `mapcheck.js`, `stratedit.js`
and the rest were not touched at all. Only `campforts.js` changed, by one line,
and that is the fort click surfacing its own tab.

**The findings banner is behind Validate now, with a count on the tab.** It was
a block pinned above everything; putting it behind a tab would have made the
screen quieter rather than tidier, so `cmapTabBadge` puts the number of read
findings on the tab itself. DaC shows `Validate 1`.

**"Switched to, once" is once per map, not once per manual pick.** The first
draft re-armed the automatic switch every time a tab was picked by hand, which
reads as the obvious meaning and is the wrong behaviour: somebody who goes to
Paint and then clicks province after province is painting, and being dragged to
Province on every click is the annoyance rather than the help. So `cmapSurface`
switches once and marks the tab with a dot every time after. The dot is real
work rather than decoration - under the first draft it was almost unreachable.

**A collapsed column is never opened by a click on the map.** Collapsing is a
decision and a map click is not a reason to overrule it, so the rail carries the
mark and nothing moves.

**The layer stack had to be capped, which the write-up did not foresee.** Pinned
at its natural height it is **794px on DaC** - ten layers with their legends and
20a's two readings - in an 842px column, so the tab body got nothing and the
strip was the old stack with extra steps. `.cmside > .cmlayers` is
`flex:0 1 auto` with `max-height:45%` and its own scroller; `.cmbody` scrolls
between the strip and it. Two scroll regions in one column is the honest cost of
"the layers stay visible whichever tab is up".

**`.cmside.wide` and the drag cannot both size the column**, and that is
`edPrevMin`'s problem in `editor.js` a second time: an inline flex beats a
class. `cmapWireSplit` takes the inline width off while 16d's Code View is up
or the rail is showing, and puts it back - with the saved width - when either
ends. The drag itself is `splitInstall`'s, a third caller beside the 3D dock and
the BMDB browser.

**Two CSS faults found by looking at it rather than by reasoning about it.**
`.cmgroup{display:flex}` beats the UA sheet's `[hidden]`, so all six groups
showed at once until `.cmgroup[hidden]{display:none}` was added. And six tabs
wrap to two rows at 336px, which is fine, but the collapse control was on the
end of the strip and landed wherever the wrap left it - it is on the header line
now.

**Verified in the browser against DaC**, not only in the suite: the first click
surfaces Province and the second marks it, the collapse leaves a 40px rail of
six icons that opens again from itself, a pointer drag on the bar moves 336 to
426 and saves it, a reload opens collapsed-and-426 when that is what was left,
`cmapResetView` puts back the first tab at 336 with the column open, and a named
view carries the tab and the width through `cvwSnapshot` / `cvwPlan` / `cvwLoad`
while a preset saved before 28a names neither and leaves both alone.

`tests/test_web_modules.py` is **34/34** against 22/22: the grouping table is
read the way `MODES` is, and the checks are the ones that catch the class of bug
rather than an instance - no panel in two tabs, every panel in the table one a
module writes into, Validate holding Check, the layer stack in no tab, every
`cmapSurface()` call naming a panel the table knows, and the three habits in
`cmapLayerState`.

The original scoping follows.

`#cmSide` is a flat stack of sixteen panels: the mod header, the findings
banner, and then Campaign, Find, Views, Check, Query, Paint, Markers, Events,
Layers, the picked tile, Delete, Settlement, Forts, Characters, Campaign
settings and Strat models. Every one of them was added where the last one
ended, and the result is a column you scroll rather than a menu you use. On a
1600 px window the Strat models panel is four screens below the fold.

**It becomes a tab strip over a switchable body, and the strip goes on top.**
The shape already exists and is not to be written twice: `MINOR_TABS` and
`minorTabsHtml` in `core.js` are the Minor Files strip, and the campaign map's
strip is the same widget with a different table. A tab is a **group** of
panels, not one panel, because sixteen tabs is the column again laid on its
side.

**Validate is one of those tabs, and the user asked for it by name.** Mylae's
map screen is `Strat`, `Validate` and `3D` across the top of the right column
with the whole of his validation behind the middle one, and that placement is
plainly better than ours: `#cmCheck` is a section in a stack of sixteen. So the
grouping table gives the validator a tab of its own rather than a slot in a
group, and the findings, the baseline stamp and the four filters go behind it
together.

**What goes behind that tab is already the larger half.** `mapcheck.py` has 32
rules with a severity, a baseline and an auto-fix on some; his `mapValidator.jsx`
and `mapFeaturesChecks.js` have eight checks between them, of which Phase 31 has
measured the two we lack and taken them. So the thing worth copying here is
where his validator sits on the screen, and not what is in it.

**Three things have to be right or the strip is worse than the stack.**

- **A panel that fills on a click has to surface.** Clicking a province fills
  `#cmPick`, `#cmSettle` and `#cmChars`; clicking a fort fills `#cmForts`. If
  the strip is on another tab that click does nothing visible, which is a
  worse screen than the one being replaced. The tab holding a panel that has
  just gained content is switched to, once, and the strip marks it.
- **The layers are not a tab.** 20a's ruling stands: the stack is the ten
  files the map is made of, and it is what the number keys tick. It stays
  visible whichever tab is up, because ticking a layer while reading a finding
  is the ordinary errand on this screen.
- **What a tab is, is saved.** `cmapLayerState` is the one snapshot of a map
  habit and named views copy it rather than re-deriving it, so the open tab,
  the column width and whether the column is collapsed go in there, and are
  then carried by every preset and put back by `cmapResetView` for nothing.

**The border drags, and the column collapses.** `splitInstall` / `splitWidth`
in `core.js` is already a left-edge drag on a right-hand panel with a saved
width, a minimum on both sides and a double-click back to the default; the
unit editor and the BMDB browser both use it. This is a third caller, not a
second implementation. Collapse is a separate control from the drag and has to
be reversible from the collapsed state, so the handle survives the collapse as
a rail with the tab icons on it.

Exit: the strip on top with Validate one of its tabs, the panels grouped behind
it, a click that fills a panel switching to it, the drag, the collapse, and all
three habits in `cmapLayerState` and therefore in a saved view.
`tests/test_web_modules.py` takes the grouping table the way it takes `MODES`.

### 28b - The toolbar over the canvas, and a tooltip that holds still - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. Both halves as scoped, and
the frame is exact rather than nearly right - measured on the running screen.**

**The brush is over the map.** `.cmbar` is two rows now: the view controls it has
carried since 16c, and `#cmPaintBar`, which `cpaintBarHtml` fills with the arm
button, the five tools, the size and shape and the target layer. The panel keeps
what is read rather than reached for - the palette, the wizard, undo and redo,
the save and the count of what is unsaved - and 28a has just given all of it a
tab. `cpaintToolsHtml` was split into three (`cpaintToolsHtml`, `cpaintSizeHtml`,
`cpaintWaterHtml`) so the bar can take the buttons and the panel keeps the four
sentences about the water brush's measured sea colours.

**One wiring function, handed a box.** `cpaintWire()` became `cpaintWireIn(box)`
and both places call it, so the same five controls behave the same in both and
neither knows where the other put them. `cpaintPaint()` paints both. The size
slider is still the one control that does not repaint on input - it has the
pointer - and it now writes both copies of its number.

**Whether the row is open is a habit; arming the brush is not.**
`cmapLayerState` carries `paint_row` and a named view puts it back; `p.on` stays
out of both, and the suite checks that the snapshot reads the settings and never
the paint session. A view that armed the brush would be a view that starts
editing a map.

**Three layout faults, each a real rule about this toolbar.** The panel's tools
are a five-column grid with the glyph over the word, which is how they fit a
336px column - on a strip that made the bar 107px of covered map, so the word
goes beside the glyph. `.cptg` is `flex:1 1 100%`, which is what makes the layer
picker its own row in the panel and what pushed it onto a second line here with
350px of stage to spare. And an absolutely positioned flex column with wrapping
rows picks a narrower width and wraps inside it, so the bar needed
`width:max-content` for `max-width` to be the only thing that ever wraps it. The
bar is **two rows, 73px, 844 of 1202px** on DaC at 1600 wide.

**The tooltip's frame does not move, and all four causes were removed.** A head
of two lines whether or not there is anything to put on them; one row per layer
the manifest names, a layer with no value saying so rather than writing nothing;
a markers block of `CMAP_TIP_MARKS` lines from the moment that layer is ticked,
empty ones included; and a width rather than a maximum, with everything clipped
on its own line because a name that wraps is a box that changed height.

**A fifth cause the write-up did not have, and it was the last pixel.**
`.count` is 11px against the panel's 11.5 and the rows are `align-items:baseline`,
so a row carrying a code in `.count` moved every row below it by one pixel. With
`.cmtip .count{font-size:inherit}` and a fixed `height:1.5em` on the row, six
probes - a settlement marker, the tile beside it, a far province, the sea, the
map's last tile and a mid-map tile - give **the same 320px width, the same 246px
height and the same ten row positions to the pixel**. With the markers layer on
it is 306px and identical across a tile carrying three things, its neighbour and
the open sea; a tile carrying six shows two and "…and 4 more" in the same box.

`tests/test_web_modules.py` is **54/54** against 34/34, twenty checks added for
the two halves. `tests/test_maplayers.py` 51/51.

The original scoping follows.

**The brush belongs over the map.** `cpaintHtml` builds the whole paint panel
into `#cmPaint`, a section of the side stack: the arm button, the five tools,
the size and the shape, the target-layer `<select>`, the palette and the
new-region wizard. Mylae's `MapPaintToolbar` is the same controls as a strip
across the top of his canvas, and the reason that reads better survives the
difference in stack: **a stroke is made with the eyes on the map**, and a
control you look away from to reach is a control you lose the stroke to.

**`.cmbar` is already that strip**, and it already carries Fit, 1:1, the two
zooms, Names, Labels and Reset over `#cmStage`. So this is a second row on an
existing toolbar rather than a new piece of furniture. What moves up is the arm
button, the tool row, the size and shape, and the target layer. What stays in
the panel is the palette, the wizard and the unsaved-stroke count, because a
palette is a list you read and 28a is giving it a tab.

**Two of our five tools have no counterpart in his row** and neither is worth
losing to a copy of it: the water brush, which writes regions, heights and
ground types together in the sea colours measured off this map, and a pipette
that selects the region on the region layer instead of only taking a colour.
His row is pencil, bucket and pipette, plus a heights mode that is our palette
one level down.

**The tooltip's rows already hold still; the box round them does not.** 17e's
`.cmtiprow` is `grid-template-columns:11px 88px 1fr`, so the label column never
shifts. Four other things do. `cmapTipHtml` writes a head of none, one or two
lines depending on whether the tile is a marker, a province or the sea; `cmkAt`
adds up to seven more lines for what stands on it; `cmapTipRow` returns nothing
at all for a layer with no value at that tile, so the row count changes as the
pointer crosses a layer's edge; and the box is `max-width:290px` with the value
column on `1fr`, so a long province name widens it. The box then follows the
cursor, so every one of those changes is a jump.

**Every one of them is information his tooltip does not carry**, which is why
the answer is a fixed frame and not a shorter readout. His is one header line
and one row per loaded layer at `min-w-[180px]`, and it is steady because it
says less. Ours keeps what it says and stops it moving: a head slot that
reserves its height whether or not it has a line, a row written for every layer
the manifest names (a layer with no value at this tile saying so, the way an
unaligned one already does), the markers block capped at a fixed number of
lines, and a fixed width in place of the maximum.

Exit: the paint controls on `.cmbar` with the palette still in the panel, and a
tooltip whose rows sit on the same pixel across two adjacent tiles that differ
in what they carry. Whether the paint row is open goes in `cmapLayerState` with
the rest, so a saved view puts it back.

## Phase 30 - A missing texture without the pink - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. The feature is as scoped; the
premise underneath it is now wrong, and the mod that makes it wrong is almost
certainly what the report was looking at.**

**"This is not the installed mods at rest. It is the paint tool." That was true
when it was written and it is not true now.** The write-up measured DaC at 15
pink tiles and Third Age Reforged at none, and the installed set has changed
since. **`vanilla_kingdoms_uncompromised` has 159,855 pink tiles - every land
tile it has, 57.6% of its whole map** - because it ships **no
`terrain/aerial_map/ground_types` folder at all**. Its aerial textures are
inside the packed data, the way the stock game's are, and nothing here reads a
`.pack`. Turn the terrain on and the entire land mass is magenta. That is what
"the pink is too jarring on the campaign map" is, and it is a mod at rest.

**One sentence instead of thirty.** The old reading emitted a gap row per
texture filename - thirty rows on that mod, each one saying
`descr_aerial_map_ground_types.txt draws N tiles with X.tga, and it is not in
terrain/aerial_map/ground_types`, which blames the aerial file for a folder that
is simply absent. `plan` now checks the folder first and says it once, naming
the folder and the count and the reason a packed mod looks like this. Ten rows
on that mod against thirty-nine, and **the pink total is unchanged at 159,855**,
which is the invariant.

**The colour, as scoped.** `GAP_FILLS` is magenta (TWMapReader's, and the
default), a neutral dark grey that reads as "nothing here", and the sea, which
is the honest answer for the case every gap on DaC is - fifteen tiles that
`map_ground_types.tga` calls ocean or sea_deep and `map_heights.tga` calls land,
where the sea is what the engine draws. `composite` takes it, `png` passes it
through, and an unknown name falls to the default rather than raising, because
this is the drawing and a query string is not worth a 500.

**A choice of how a gap is drawn and never a choice to hide one.** The count
stays on the layer row - it says "drawn neutral" or "drawn sea" now rather than
always "drawn pink" - and the `terrain.texture` rule stays in the Check panel
whichever is picked. The suite checks both halves: that the three kinds of gap
change colour together, and that the count, the gap rows and every tile that
*did* draw are identical whichever fill is asked for.

**It is in both caches or it is in neither.** The colour is baked into the PNG,
so `/api/map/terrain` takes `&gap=`, the server's disk-cache token is
`mapterrain|<plan key>|gap|<name>`, and the browser's own `shot` is keyed
`mod|campaign|season|gap`. Without either, two colours share one picture and you
get whichever was asked for first. Verified over HTTP: the three fills are three
different PNGs (29,501, 29,309 and 16,218 bytes on that mod - `sea` compresses
hardest because land and sea become one colour), each with its own
`X-Map-Gap` header, and `&gap=chartreuse` answers 200 in magenta.

**A habit, so it rides with the season.** `terrain_gap` is in
`cmapLayerState`, therefore in every named view, and `cmapResetView` puts it
back to magenta. A preset saved before 30 names no fill and opens pink, which is
what that view looked like when it was saved.

**And one pre-existing red turned out to be this.** `test_mapterrain`'s "every
texture it draws with is really in `terrain/aerial_map/ground_types`" has been
failing on `vanilla_kingdoms_uncompromised` - it was asserting a fact about the
mod rather than about the tool. With no folder there is nothing for it to be
true of, so the check now says what it is measuring instead. **84/84 against
72/73.**

`tests/test_web_modules.py` **75/75** against 66.

The original scoping follows.

**Reported from the beta: the pink is too jarring on the campaign map.**
TWMapReader draws a texture it cannot find magenta and 23a took that rule as
it stands, widened by one case. It is the right default and it is not always
the right picture to work against.

**Measured first, because the number changes what this is.** Divide and
Conquer has **15 pink tiles** and Third Age Reforged **none**, in both
seasons. So this is not the installed mods at rest. It is the paint tool: a
stroke that lays down a ground type the aerial file does not declare turns
those tiles pink the moment the composite is rebuilt, and a map being built is
exactly where somebody is when this screen is open.

**A choice of how a gap is drawn, and never a choice to hide it.** The locked
rule is that a baseline shows and stops blocking but never hides, and 23a's
own decision is that a picture of the terrain says what it could not draw. So
the count stays on the panel and the `terrain.texture` rule stays in the
Check panel whatever is chosen; what changes is only the colour under the gap.
Magenta as now, a neutral that reads as "nothing here", or the sea colour,
which is the honest answer for the fifteen tiles DaC has, because all fifteen
are tiles `map_ground_types.tga` calls sea and `map_heights.tga` calls land.

**The colour is baked in Python, so it is a parameter and not a CSS rule.**
`composite` fills with `MISSING_RGB` and pastes over it, and the browser is
served a PNG. The choice therefore has to reach `mapterrain.plan`'s key and
`signature`, or two colours share one cached picture and the one you get is
whichever was asked for first. It goes in `cmapLayerState` beside the season,
so a saved view carries it.

## Phase 31 - Two river rules, and a ford in the sea - DONE 2026-09-13

**Closed 2026-09-13, beta line, committed and not cut. Three rules, one repair,
and no web change - which is what the scoping said, and this time the scoping
held.** Everything the write-up measured was re-measured and every number came
back: Divide and Conquer's 95 river components and Third Age Reforged's 86 are
exactly right, and the three new rules find **nothing on any installed map**.

| rule | what it catches | on the five maps here |
|---|---|---|
| `river.fourway` | a river tile with river on all four sides | **0** |
| `river.no_source` | a four-connected component with no white source on it | **0** |
| `feature.ford_in_sea` | a crossing whose own altitude is sea and whose four neighbours are | **0** |

The write-up measured three maps; this measured five, adding
`vanilla_kingdoms_uncompromised` (73 components) and `Vanilla_Redux` (46, the
same as vanilla's own). Zero everywhere, which is the point: **these are rules
for a map being drawn, not faults anything ships.** The whole rule set still
runs on DaC in about 650 ms against the 659 measured before it, so the
one-second bar has lost nothing.

### `feature.ford_in_sea` needed both halves, and the write-up only had one

The scoping said "a cyan tile whose four neighbours are all sea". That is the
half that separates a ford in the ocean from a legitimate coastal crossing, and
on its own it is not the defect. The defect is that
:func:`campmap.sea_mask` subtracts **every** cyan pixel unconditionally, so the
hole in the ocean only exists where the tile's **own** altitude reads sea. A
ford on a land tile with water round it is odd and is not a hole.

So the rule asks both, and the message and the repair are true because it does:
the tile's own height reads sea by `mapvocab.is_sea_height`, **and** all four
cardinal neighbours are sea, **and** all four are on the grid - a ford against
the edge of the map is a different question and this one does not answer it.

### One repair, and the other two are worth saying no to

`ford_none` clears the crossing to no feature at all. That is the one safe
answer of the three, and the reasoning is in `FIXES` beside it:

* **`river.fourway`** is repaired by removing one arm, and which arm is the map
  author's intent rather than ours.
* **`river.no_source`** is repaired by painting a source at the head of the
  course, and which end is the head needs `map_heights.tga` - the same second
  layer that put Geomod's "two pixels past the coastline" rule out of scope.
* **`feature.ford_in_sea`** has one thing the tile can be, because the heights
  already say so and only the crossing colour was overriding them. Clearing it
  closes the hole, and the suite asserts exactly that: the sea mask reads that
  tile as sea again afterwards.

`map_features.tga` is a `W x H` layer - one pixel **is** one tile - so
`_plan_fords` has no block to fill and no corner to keep consistent, which is
the one way it is simpler than `_plan_heights`.

### The new rule found a flaw in the old fixtures

All three existing river fixtures - `river.diagonal`, `river.isolated` and
`river.rejoin` - painted courses with **no source pixel anywhere on them**, so
each started reporting two findings and tripped `broken(...)`'s "did breaking
one thing report only that thing" check. Each now paints its source, which
makes it a river the engine could build, broken in exactly the one way its rule
is about. White is one of `RIVER_CODES`, so every rule under test sees what it
saw before. `river.isolated` is better for it: it is now a lone **source**
pixel, which is literally Mylae's check 4 and the vanilla `(175,14)` case the
rule was measured against in the first place.

### Still to pass back to Mylae

Both from the original scoping and both still true:

* **vanilla trips his orphan-source check at image (175,14)**, and his port
  makes it an `error`, so his validator calls vanilla broken. Ours is a `warn`
  for that reason.
* **the tool he ported from cannot open either installed map.** It refuses
  anything that is not uncompressed true-colour, and both mods ship
  `map_features.tga` as image type 10, RLE - DaC at 32-bit, Third Age Reforged
  at 24. `maptga.py` reads and re-encodes all ten of DaC's layers byte for byte
  with the RLE intact, which is why any of this could be measured here at all.

**One rule stayed out**, as scoped: Geomod's "a river must extend two pixels
past the coastline" is a rule about a river's mouth against `map_heights.tga`
rather than about `map_features.tga` alone, and it is the only one of the five
that needs a second layer. Scoped out rather than half-checked.

**Beta only.** `map_features.tga` is the campaign map.

## Phase 32 - Who can hire what, and where - the mercenary pools

**The next big feature, asked for on 2026-09-12, and the campaign map is where
it lives.** Click a province and see the mercenaries it can raise, filtered by
faction, by event, by year and by religion; and the other way round, take a
mercenary and see every province it comes from. Three sessions.

### What exists, and it is less than it looks

`descr_mercenaries.txt` is already read, and by exactly one parser, which is
the rule to keep. What that parser keeps is the problem:

- **`mapquery.parse_mercenaries` returns a pool's name, its regions and its
  unit NAMES and nothing else.** Every gate on a unit line is thrown away:
  `exp`, `cost`, `replenish A - B`, `max`, `initial`, `start_year`,
  `end_year`, `religions { }`, `crusading` and `events { }`.
- `RegionFacts.merc_pools` says which pools a province is in, there is a
  `mercenary_pool` filter, and `info_mercenaries` is Geomod's pool map.
- 18a's G3 can **move a province between pools** and warns when a province is
  in no pool at all. That is the whole of the writing.

So today the toolkit can say *which pool* a province belongs to and cannot say
*which mercenaries* that gets you, which is the question actually being asked.

### Measured first, on both installed mods

| | DaC `imperial_campaign` | TAR `imperial_campaign` | TAR `Fellowship_Campaign` |
|---|---|---|---|
| pools | 57 | 27 | 28 |
| province slots | 193 | 148 | 81, **80 distinct** |
| distinct units | 113 | 25 | 29 |
| **unit names with no EDU type** | **2** | **5** | **28 of 29** |

**Three findings fall out of the counts alone, and none of them is reachable
today.**

- **Dead mercenary references.** DaC names `Clan Axemen` and `Framsguard
  Dismounted Axemen`, neither of which is a `type` in its 924-unit EDU. Third
  Age Reforged's Fellowship campaign names 29 units and **28 of them do not
  exist**: `Beorning Mercs` and its siblings appear nowhere in the mod but
  that one file, and the mod ships exactly one `export_descr_unit.txt`, so
  there is no second roster they could be coming from.
- **A province in two pools.** `Mt-Gram_Province` is in two of Fellowship's
  pools. The file's own header says a region "can only be present once in the
  whole file", so this is the file breaking its own documented rule.
- **Most provinces have no pool.** DaC declares 193 of about 400. That is
  probably deliberate and it is worth being able to see on a map.

### 32a - The pool as a record, and one parser for it

**`unittransfer/mercpools.py`** takes over the format, and
`mapquery.parse_mercenaries` becomes a thin call into it rather than a second
reader. That is the one-engine rule and it is not negotiable here: two readers
of a unit line is how the gates get dropped a second time.

The record is the whole line. A name is everything in front of `exp`, which is
how the existing parser already does it and the reason is worth keeping: a
mercenary's name is one to four words and real files write a trailing comma
after it, so a word count is wrong on both installed mods. Then `exp`, `cost`,
`replenish` as its two bounds, `max`, `initial`, and the five optionals.

Writing is `keyblock`'s splice discipline, the same as everywhere else:
comments, tabs and the RATE_H style notes DaC keeps at the top of the file
survive an edit untouched. Add a unit to a pool, remove one, change any field,
move a province between pools (G3's existing operation, now going through
this), and add or delete a pool.

**The file is per campaign.** Third Age Reforged ships a different
`descr_mercenaries.txt` for Fellowship than for `imperial_campaign`, with a
different unit list and a different set of faults, so 22c's ruling applies
unchanged: `Registry.map_for` picks the campaign, and a pool read for one
campaign is not another's.

### 32a done 2026-09-17 - the whole line, and the old reader is a call into it

**`unittransfer/mercpools.py` owns the file.** `mapquery.parse_mercenaries` is
five lines that call it and keep their old shape, and `campfiles.parse_mercs`,
`MercFile`, `set_regions` and `move_region` are its names now, so G3, the
province delete and the rename sweep go through it without changing a caller.
Every campaign on this machine reads the same pools, name for name, as the old
reader did.

**The counts above held exactly**: 57 pools over 193 slots and 113 distinct
units on DaC, 27/148/25 and 28/81/29 on Reforged's two. 363 unit lines in all,
**every one with the five fixed fields in the documented order and not one
fault**.

**One thing the write-up did not have, and 32b needs it.** There is a sixth
optional the file's own header does not document: **`factions { }`, on 41 of
Fellowship's 51 lines**, always after an `events { }`. So "a faction hires a
mercenary through its religion" is not the whole gate on that campaign - a line
can name the factions outright, and 32b's table of four gates is five.
Otherwise seen: `religions` 317, `events` 105, `crusading` 28, `start_year` 2
(Reforged's imperial campaign), `end_year` none.

**Writing is a splice at character positions**, not a re-render: a value is
replaced between its own offsets, an added option goes on the end of the code
part, a removed one takes its leading space. **A value set to itself is not an
edit even when it is spelled differently** - the first sweep found DaC's
`0.10` coming back as `0.1` - and every field of every real line set to itself
leaves the line alone. A new unit copies the pool's last line's indent and the
gap after its name. Six actions behind one plan: `unit_edit`, `unit_add`,
`unit_delete`, `pool_add`, `pool_delete`, `region_move`. **The plan re-reads
its own output and refuses any save in which a record it did not name
changed**, or in which the set of pools is not exactly the one asked for.

**No screen yet, by the write-up's split**: the reading is 32b's. New:
`unittransfer/mercpools.py` (`parse_unit`, `parse_text`, `set_field`,
`unit_line`, `edit_unit`, `add_unit`, `delete_unit`, `add_pool`,
`delete_pool`, `move_region`, `overview`, `plan`, `apply`, `MercUnit`,
`MercPool`, `MercFile`, `MercPlan`), `GET /api/mercpools`,
`POST /api/mercpools/plan|apply`. `tests/test_mercpools.py` 73/73, new;
`test_campfiles` 92/92, `test_mapquery` 109/109, `test_regiondel`,
`test_campnew` and `test_renames` green. `test_campfiles` was 101 and is 92 on
the old code too - the mod set, not this.

### 32b - The two directions, and the four gates resolved

This is the session the feature is actually about, and it is a join, not a
parser.

**From a province:** its pool, and every mercenary in it, each with its cost,
its replenish rate, its pool size, and **why it is or is not available**. That
last part is the whole value, and it needs four lookups we already own:

| gate on the line | resolved against | we already have it in |
|---|---|---|
| `religions { a b c }` | each faction's religion | `factions.py` / `factionaudit.Census` |
| `events { A B }` | the mod's real event list | `campevents.py` |
| `start_year` / `end_year` | the campaign's start and end | `stratcamp.py` |
| the unit name | the EDU roster | `edu.py` |

So "filter by faction" is not a field on the line. **A faction hires a
mercenary if the faction's religion is in the unit's `religions` list, or the
list is absent**, which the file header states outright, and `crusading`
narrows it further to a crusade or jihad army. Picking a faction in the panel
therefore resolves through its religion, and the panel says so rather than
implying the file names factions.

**From a mercenary:** every pool that offers it, every province in those
pools, its cost in each (mods really do price the same unit differently in two
pools), and a button that lights those provinces on the map. `cmapGoTile` is
the one way of arriving at a tile and `cmapLocate` gives the ring for free.

**On the map:** the pool map already exists as `info_mercenaries`. What it
gains is three more colourings off the same facts, which is `_by_value` and
`_by_band` and no new machinery: how many mercenaries a province can raise,
whether it can raise any at all, and which provinces a chosen unit is
available in. Every one of them is a colouring, so the TGA export and 23b's
tint come with them.

**Where it sits is Phase 28's first real test.** This is one more panel on a
column that is already sixteen deep, and it belongs on the same tab as the
picked province. Take 28 first.

### 32b done 2026-09-17 - five gates, a verdict with its reason, and the map

**The join is `mercpools.hire_view`, one call per campaign and faction**, and
the page decides nothing: every unit line comes back with `hire` (`yes`,
`later`, `no` or `unknown`) and the gates behind it in words. **Five gates,
not four** - 32a found `factions { }` - and two kinds of result the table above
did not have: **`unknown`**, for an event nothing in the campaign's own
descr_events.txt or scripts sets (a script elsewhere, EOP's say, may), and
**`info`**, for a faction gate when no faction is picked, which says what the
line needs and decides nothing.

**Events are traced, not only listed.** DaC's `ND_BOH` is in no
descr_events.txt; it is `set_event_counter ND_BOH 1` at `campaign_script.txt`
line 10765, and the gate says so. 1,146 names are set across that script. Three
of DaC's events are set by nothing in its campaign folder - `lanc_cleared`,
`turn_25`, `turn_50` - on four lines. The first draft of the scan took four
seconds on that 10 MB script by recounting lines from the top for every match;
it is 0.06 s.

**Measured, the whole picture:**

- **DaC**, no faction picked: 190 lines hireable from turn one, 74 waiting (57
  on an event, 17 on a crusade), 4 on an untraced event. **Both units the
  scoping called dead - `Clan Axemen` and `Framsguard Dismounted Axemen` - are
  in DaC's EDU as installed now**, so there are none. A catholic faction can
  hire 89 of the 268 lines at once, an elven one 98.
- **Reforged's imperial campaign has two lines no faction will ever hire**:
  `Anduin Bodyguard` and `Angmar Rhudaur Axemen` both carry `start_year 2986`
  in a campaign that ends in 2984.
- **Fellowship** is 28 of 29 names not in the EDU, as scoped, so 49 of its 51
  lines are `no` for everybody; `Mt-Gram_Province` in two pools is confirmed.

**One defect of the join's own, caught by the numbers**: DaC's `egypt` came
back with no religion and could hire nothing, because its record is written
`faction egypt, spawned_on_event` and the name kept the suffix. Every faction
on every campaign now has its religion, and a test says so.

**The map gains three colourings** off the same facts, as scoped:
`merc_count` (bands of lines on sale), `merc_any` (sells anything or not) and
`merc:<unit>` (every province selling one unit), the last listed in the
catalogue per unit like the per-resource maps. The panel's ◉ lights one
through the query panel, so the legend, the tint and the TGA export all come
with it.

**The panel** is the Province tab's sixth sub-tab, `Mercenaries`: a faction
picker; *This province* (following the map's pick), *A mercenary* (every pool
selling it, its price and pool size there, its provinces as chips) and
*Pools*. **32a's writer has its screen here** - edit a line's fields, remove
it, or sell another unit in the pool with the EDU's names offered - and a save
reopens the region record, whose pool box reads the same file.

New: `mercpools.hire_view`, `gates`, `event_sources`, `faction_rows`,
`campaign_years`; `mapquery.info_merc_count`, `info_merc_any`, `merc_units`,
`MERC_BANDS` and the `merc:` code; `GET /api/map/mercs`; `web/js/mercs.js`
(`mcp*`), `#cmMercs`, the `.mcp*` styles. `tests/test_mercpools.py` 102/102
(was 73), `tests/test_web_modules.py` 112/112 (was 105), `test_mapquery`
109/109. Checked live on DaC: the panel on Nan_Curunir for France, the
Raider Warband map lighting 27 provinces, an edit planned and not written.

### 32c - The rules, and the repairs

Five new `mapcheck` rules, each one measurable on the installed mods today:

| code | what | found now |
|---|---|---|
| `merc.unit_unknown` | a unit line naming no EDU type | 2 in DaC, 33 in TAR |
| `merc.region_twice` | a province in more than one pool | 1 in TAR Fellowship |
| `merc.region_unknown` | a regions line naming no province | to be measured |
| `merc.religion_unknown` | a `religions { }` entry nothing declares | to be measured |
| `merc.event_unknown` | an `events { }` entry `descr_events.txt` does not have | to be measured |

**The baseline rule applies and matters more than usual here.** 33 dead
references in Third Age Reforged is somebody else's mod with somebody else's
bugs in it, so all of it shows, is counted, and refuses nothing. A tool that
blocks on 33 inherited faults is one nobody opens twice.

**`merc.region_twice` gets a repair and the others do not.** Which of two
pools a province should be in is a choice, so the fix offers both and the user
picks; there is no safe automatic answer to "which mercenary did you mean" or
"which unit did you mean to name". 16f's three auto-fixes are the shape for
the one, and `rtOpen(rel, line)` is the escape hatch for the rest.

### 32c done 2026-09-17 - six rules, and the repair is a choice

**Six rules, not five**, every one a warning. The sixth is
`merc.year_outside`, because 32b's join found the fault and it had no rule:
a line whose `start_year` is after the campaign ends, or `end_year` before it
starts. `merc.religion_unknown` covers `factions { }` names too.

**Measured on every campaign here, and the table above did not hold:**

| code | DaC | Reforged imperial | Fellowship |
|---|---|---|---|
| `merc.unit_unknown` | 0 | 0 | **49 lines** (28 names) |
| `merc.region_twice` | 0 | 0 | 1 (`Mt-Gram_Province`) |
| `merc.region_unknown` | 0 | 0 | 0 |
| `merc.religion_unknown` | 0 | 0 | 0 |
| `merc.event_unknown` | **4** | 0 | 0 |
| `merc.year_outside` | 0 | **2** | 0 |

"2 in DaC, 33 in TAR" was names measured against an older install; DaC's two
are in its EDU now, and Reforged's imperial campaign has none. **The event rule
reads 32b's `event_sources`, not descr_events.txt alone** - read the way the
scoping wrote it, every one of DaC's 61 event gates would be a finding, because
its events are set by `set_event_counter` in the script.

**The repair is not an auto-fix.** `FIXES` acts on a rule's findings without
asking anything, and which pool a province stays in has no safe answer. So the
Mercenaries panel lists each province in two pools with a **Keep in X** button
per pool, and that is 32a's `region_move`, backed up and undoable like every
other move. The finding's message says where to go.

**A rule with nothing to read is silent.** The first draft reported a skip for
the EDU and the religions on `test_mapcheck`'s fixture mod, which has neither
and no mercenary file either; the four rules that need them now look for a
line to check first. `test_mapcheck`'s timing bar was already red on the old
code (1,144 ms) and reads 1,048 and 1,888 ms with the six rules added; the EDU
read is most of what they cost.

New: `mapcheck._r_merc_*` and `_merc_file`/`_merc_lines`, `mcpKeepIn` and
`mcpRegionName`; the Rules sub-tab's title counts 41 rules. `test_mercpools`
109/109, `test_web_modules` 114/114, `test_mapcheck` 95/97 (the timing bar).

### What this is not

**Not a mercenary unit editor.** The unit itself is EDU's and the unit editor
already owns it; this edits the *pool entry*, which is a different record with
different fields, and a dead reference is fixed by naming a unit that exists,
not by inventing one. The two screens link to each other and neither grows the
other's fields.

## Phase 33 - Three small map wins in one session - DONE 2026-09-15

**Done 2026-09-15, beta line, committed and uncut. All three, and each of the
three turned up a fact about the installed mods that the write-up did not have.**

**T10 - the tile on the clipboard.** `c` copies what is under the pointer, or
the tile at the centre of the view when the pointer is off the map, which is the
"copy the view, or what is under the cursor" of the scoping said as one key.
There is a button on the picked tile's own heading as well. The form is
`x 109, y 147`, **measured off vanilla's own `descr_strat.txt`** rather than
chosen: every `character` line in it ends that way. It copies the **game** y and
not the image one, and that is the whole of the arithmetic - the two differ by
counting from the bottom, and a copy that handed over the image y would put a
general on the wrong side of the map.

*The write-up's "the shift-X detail is the model" has no referent.* There is no
shift-X in this tool or anywhere in its history. Taken as `c` for copy, beside
`t` for the tooltip and `f` for find, which is the pattern this screen's letters
already follow.

**G2 - the province's music type.** `mapquery.set_music_region` is the third and
last call against `descr_sounds_music_types.txt`, and it is the other two in
order: the drop takes the name off **every** `regions` line that holds it, the
add puts it on the end of the wanted block's last one. Written as the pair
because a move is exactly that, and because one of the two rules belongs to
each. The block is checked before anything is removed, so a name asked into a
type the file has not got cannot come off its own line and land nowhere.

`campfiles` has a fourth `what` and `_plan_music` is it, which makes this the
third picker on the region panel that saves its own file with its own undo -
17f's ruling, after the mercenary pool and the names boxes. It is the odd one of
the four in `campfiles`: the file lives beside the map layers rather than in the
campaign folder, so **no campaign is sent and switching campaign does not change
the answer**. `map.rwm` is not deleted either - this file is read at load rather
than compiled into the map - and the confirm says so.

*Measured: a move changes exactly two lines and the line count does not.* The
one the name leaves and the one it joins. Moving it back does not restore the
file byte for byte and that is honest rather than a gap, for the mercenary
pool's reason one file over: a `regions` line is a set and the format records no
position for a province within it.

*Two states of the same shape, both real on this machine, and both reported
rather than tidied away quietly.* **58 provinces of
`vanilla_kingdoms_uncompromised` are under two music types**, and **2 of Vanilla
Redux are named twice inside one type**. The engine plays one of them either
way. The panel says which it is, saving resolves it, and the plan names that as
a change before it does.

**G4 - the legion's display name.** `namekeys.region_names` returns a third row
and the panel draws it, which is all that was owed: 19a's writer already handled
any key in that file.

*And the legion is the only one of the three keys that need not name this
province.* Divide and Conquer is the one installed mod that writes the line at
all - **199 of its 200 records** - and only **80** of those point at the
record's own name. The rest point at another province's key
(`Rhudaur_Province` reads `legion: Eregion_Province`) or at a settlement's
(`Imladris`, `East_Moria`). So the row follows whatever the line says and the
label tells you when the key is somebody else's, rather than letting it read as
this province's third name. The other three mods write no `legion:` line and the
row is simply absent, the same rule the settlement half already follows.

*It found a real defect on the first province it was pointed at.* **115 of DaC's
116 distinct legion values already have a line in the names file.** The one that
does not is `Thorenhad_Province`, on `Suduri_Province`, and the panel now says
"no line in this file yet" against it.

`tests/test_web_modules.py` **66/66** against 54, `tests/test_campfiles.py`
**101/101** against 92 with the music save and its undo run against a throwaway
copy of a real mod, `tests/test_namekeys.py` 64/68 against a clean tree's 63/67 -
two checks added, the four failures unchanged and none of them this - and
`tests/test_mapquery.py` 118/118.

The original scoping follows.

Three items that were separately rated five stars, are separately marked **S**,
and share a session because none of them is big enough to hold one on its own.
All three are on the map screen and all three are beta line.

- **T10 - copy the view, or what is under the cursor.** The detail is already
  under the pointer; this puts it on the clipboard as `x 23, y 284`, which is
  the exact form `descr_strat.txt` wants. The shift-X detail is the model.
- **G2 - change an existing province's music type.** B1 already gives a *new*
  province one, through `mapquery.add_music_region`, and `drop_music_region`
  came with 24. Changing an existing province's is the third call against a
  writer that is otherwise finished, plus a picker on the region form.
- **G4 - the legion label, with its name dialog.** D4 in miniature. The write
  it needs is the one 19a added to `namekeys.py`; what is missing is the paired
  display name, which is why 19b flagged it as nearly free and did not take it.

**Take it early and the reason is scheduling, not importance.** Three S items
banked in one sitting is the cheapest five-star work on the whole list, and it
clears three rows out of the future list for good.

## Phase 34 - Add a climate zone - **done 2026-09-15**

**The scoping was right about the files and wrong about the operation.** Every
file was already parsed and the brush already painted the layer, and what was
missing was indeed the operation; the archive tutorial it names -
Bella's *How-To: Add a New Climate Zone*, 2007 - does name exactly
`map_climates.tga`, `descr_climates.txt`, `descr_aerial_map_ground_types.txt`
and `map_ground_types.tga`. What the write-up did not have is that **the
tutorial's own thread withdraws its central claim**, and that the installed mods
agree with the thread rather than with the how-to.

**A climate is a slot, not a thirteenth name.** Eighteen posts and two years
after the tutorial, wilddog writes that a climate the engine does not already
know by name is not read by `descr_geography_new.txt`, that the exe looks to be
hard coded to those names, and that the answer is to amend an existing one
"including the unused1 and unused2 names". Measured here, that is not one
modder's opinion:

* **All four installed mods declare exactly twelve climates, and they are the
  same twelve in the same order** - `mediterranean`, `sandy_desert`,
  `rocky_desert`, `unused1`, `steppe`, `temperate_deciduous_forest`,
  `temperate_coniferous_forest`, `unused2`, `highland`, `alpine`, `tropical`,
  `semi_arid`. Not one added a thirteenth.
* **Divide and Conquer took a slot over rather than adding a name.** It has a
  wholly custom 248,370-tile map, and it paints `unused1` on **18,970 tiles**
  and `unused2` on **192**, calling them Harondor and Lorien in
  `text/climates.txt`. Reforged did the same: 5,466 and 182. So the operation
  this phase adds is the one both big mods performed by hand.
* **`descr_geography_new.txt` gives a block to the twelve and to nothing else.**
  Vanilla Redux is the one mod here that ships the text file rather than only
  the compiled `.db`, and it has fifteen top-level blocks: three settings
  sections and the twelve climates, four as a bare name and eight as
  `<name> modifies <base>`. That file is the ceiling, and it is why the battle
  map is where a new name stops.

So **taking a slot over is the offered operation and adding a name is offered
second**, with the geography file named as the reason it is second. Both are
real - the strat map draws a new name perfectly well, which is why the tutorial
worked for its author - and the refusal is a warning rather than an error,
because this cannot see inside a `.pack` and three of the four mods ship only
the compiled geography.

**Four writes that have to agree, and `map_climates.tga` is not one of them.**
`descr_climates.txt` (the list fixes the index, the block carries colour, heat
and winter), `descr_aerial_map_ground_types.txt` (a texture for every ground
type in **both** seasons), `text/climates.txt` (UTF-16, or the `.strings.bin`
when a mod ships only the compiled copy - two of the four do), and
`descr_climates_lookup.txt` when the mod has one. **Painting is the brush's**:
28b's ruling is that a control which is not the brush does not start a paint
session, so this writes the colour and the brush writes the pixels.

**A take-over keeps its place in the list and an add goes on the end of both.**
The list is the index the engine reads, so moving a name in it renumbers every
climate after the move - 36's lesson about region colours, arriving a file
early. A take-over therefore rewrites its block where it stands and touches the
list not at all.

**Three things the scoping did not have.**

**One: the lookup file is already wrong in the wild, and it is the tutorial's
fault.** Its step 4 prints a lookup list containing `volcanic` while its step 3
prints a `climates { }` block that does not, and **Third Age Reforged and
Vanilla Redux both ship exactly that** - thirteen names in the lookup, twelve
declared, the extra one `volcanic`. Divide and Conquer's twelve match;
`vanilla_kingdoms_uncompromised` has no lookup file at all. All four states are
reported and none is repaired, because a name the engine may be indexing by is
not something to tidy silently.

**Two: a take-over strands the tiles its old colour is on, and the number is
worth saying.** Change `unused2`'s colour on Divide and Conquer and 192 tiles
are still painted the old one, which nothing declares any more, so they fall
through to the `default` block until they are repainted. `claimed_tiles` and
`orphan_tiles` are two counts because they answer two questions, and the plan
says both.

**Three: the ground types in a new block are the mod's own, not a constant.**
Every installed mod is internally consistent - one key set across all of its
blocks - and the set is **not the same everywhere**: three mods name sixteen
ground types and Vanilla Redux names seventeen, the extra one
`impassable_shrouded`. A block written to a table here would be a line short on
one mod in four.

**And one defect found on the way, in `mapvocab` rather than in this.** Its
climate-block regex was `climate <name>` followed by whitespace and a brace, so
**a comment after the header dropped the whole block** and a declared climate
read as undeclared. No installed mod annotates `descr_climates.txt` - but every
one of Divide and Conquer's thirteen blocks in
`descr_aerial_map_ground_types.txt` is annotated exactly that way, so the habit
is real and the two files are edited together. It mattered here and not before
because `climatenew`'s own block finder *does* skip the comment: the panel would
have offered to add a climate that was already there and then overwritten it.
Fixed in `mapvocab.climates`; all four mods read identically before and after.

**New:** `unittransfer/climatenew.py` (`lookup_names`, `lookup_state`,
`geography`, `climate_tiles`, `slots`, `ground_keys`, `donors`,
`climate_block`, `write_climates`, `aerial_block`, `write_aerial`,
`write_lookup`, `ClimatePlan`, `plan`, `apply`, `view`, `VANILLA_ORDER`,
`SPARE`, `GEOG_SETTINGS`), `GET /api/map/climates`,
`POST /api/map/climate_plan|_apply`, `web/js/climates.js`, `#cmClim` in the
Paint tab, the `.cclslots` grid. `tests/test_climatenew.py` (110).

**The route is ahead of the map read**, beside `/api/map/campaigns` and for the
same reason: a climate is declared in four text files under `data/` and not one
of them is a map layer. The layer is read for the tile counts alone, so it is
asked for and never required - which is also the only reason the suite's little
mod, which has no layers at all, can exercise the route end to end.

## Phase 35 - Rebels right in place: province and rebel faction, both ways - DONE 2026-09-16

**The scoping was right that this is a join and a screen, and wrong about how
much of it was missing.** Three of the four things it names already existed, and
finding that out is most of the phase.

| the write-up's "missing" | what was really there |
|---|---|
| see what a rebel faction can field | the Minor Files rebel form, `mfRebelForm`, which lists the `unit` lines and resolves each against the EDU already |
| change the assignment from the province end | the `rebels` box on `cmPick`, editable since 16d and validated against the declared list since then |
| light its provinces on the map | `info_rebels` runs through `_by_value`, which builds one group per rebel faction; the group filter is the highlight. Measured: 38 groups on DaC, one per named faction |
| **take a rebel faction and see its provinces** | **nothing, anywhere** |

So what was built is the reverse list and the one operation the rebel end has
that the province end does not: **assigning many provinces at once**. And the
phase gets its "what this is not" from the same measurement, in 32c's shape:
**not a rebel faction editor**. That record is Minor Files' and works there.

### There is no rule here, and the measurement is why

The archive tutorial this was scoped from is Errabundi's *Rebels Right in
Place*, whose complaint is Bulgarian rebels spawning in Serbia. Measured on both
installed mods:

* **not one province names a rebel faction that is not declared.** DaC's 200
  records name 38 of its 42 blocks; Reforged's 199 name 27 of its 30.
* **not one of the 248 `unit` lines across the two mods names a unit the EDU
  does not have**, in any case.

There is nothing for a validator to find. A wrong assignment is a *valid*
assignment somebody did not mean, and no rule separates the two, which is what
the write-up itself says: it is invisible unless you colour the map and look.
**So this ships no `mapcheck` rule and no repair**, and saying so is better than
inventing a rule that fires on a correct file.

### What the measurement did turn up is `chance`, and it is in the other file

* **Third Age Reforged sets `chance 0` on every one of the 27 blocks its
  provinces name.** All 199 of its provinces point at a rebel faction that will
  never spawn: province-driven rebels are switched off across the whole mod,
  uniformly. Only `brigands`, `pirates` and `gladiator_uprising` are non-zero,
  and no province names those.
* **DaC spreads it**: 2 on 29 blocks, 4 on 7, 6 on one, 10 on one, and
  `No_Rebels` at 0 on the 9 provinces meant to have none.

So `chance 0` is an idiom and a rule flagging it would be wrong 208 times. What
it earns is a **note**: the chance is on every row, because picking a block
without it is the one way to make this edit and have it do nothing.

### Three blocks that no province names are not orphans

Each mod declares exactly one block per non-`peasant_revolt` category, named
after the category itself, and the engine spawns those by category rather than
off a region record. `BY_CATEGORY` is that exemption; without it the reverse
list calls three correct blocks dead on every mod there is. What survives the
exemption is a real orphan: **two on DaC**, `Ent_Rebels` and `Saralainn_Rebels`,
declared with units and named by nothing, and **none on Reforged**.

### The defect it led with, which is in shipped work and not in this

Rule 1 of the order, applied on the way in. **The region record editor wrote the
base `descr_regions.txt` whatever campaign was on the screen.** A campaign that
ships its own copy is drawn and judged on that copy - `CampaignMap` reads it and
sets `regions.path` to it, which is 22c's rule, and `_region_delete` beside it
has always honoured it - but `plan_region` read `read_regions(mod)` and
`apply_region` wrote the `REGIONS_REL` constant. **Reforged's Fellowship
campaign ships its own and the two files differ in eleven records**, so this was
not latent: a save made on Fellowship wrote a file that campaign does not read,
and the screen went on showing the old value.

**The stale compiled map was the same defect's other half.** `apply_region`
deleted `base/map.rwm` alone, and Reforged ships a `map.rwm` in its Fellowship
folder too - a different file, 14 KB apart - so an edit there left the stale one
exactly where the engine looks first.

Fixed at four levels: `plan_region` takes the map, `apply_region` writes the
path the plan carries, `stale_rwm` names the compiled maps a write really makes
stale, and `campmap.js` sends the campaign it was never sending. New:
`campmap.RWM_NAME`, `campmap.regions_rel`, `campmap.stale_rwm`, a third argument
on `plan_region`.

### Verified

`tests/test_rebelpools.py` **68/68**, new. Eleven suites re-run and all green -
`test_web_modules` 75/75, `test_campedit` 107/107, `test_campaint` 169/169,
`test_regiondel` 62/62, `test_codeview` 141/141, `test_namekeys` 56/56,
`test_campnew` 52/52, `test_minorfiles` 185/185, `test_mapquery` 109/109,
`test_climatenew` 98/98. `test_campmap` is 108/112 and **a stashed tree gives
the same 108/112 with the same four failures by name**, all of them DaC-number
checks against a mod build that has moved.

Driven in the real app against both mods: the panel lists 42 factions on DaC
with the localised names resolved, the orphan warning fires on `Ent_Rebels`, a
chip jumps to the province on the map, and `GET /api/map/rebels` with
`campaign=custom/Fellowship_Campaign` answers with that campaign's own file.

## Phase 36 - D1: change a region's colour - DONE 2026-09-16

**The write-up's premise is withdrawn: a recolour does not renumber.** It was
scoped on "changing one colour can renumber every region after it", and that is
the one thing a recolour cannot do.

A region ID is the order a colour is **first met** in a row-major scan of
`map_regions.tga`. That is a fact about **where a province's pixels are**, and a
recolour moves no pixel: it changes what colour they carry, and the scan meets
the same province at the same tile as before. Measured by renumbering both
installed maps with one province recoloured, the first in the scan order and one
in the middle: **not one ID moved, in any of the four cases.** Then measured
again off disk after a real save, with a freshly read map: still zero.

So the panel's job turned out to be the opposite of the one scoped for it. It
does not show which regions move; **it says that none of them do**, and that is
the reason to press the button. The create wizard warns that a new province
renumbers and the delete warns that removing one does, both correctly, because
both of those really do move pixels between colours. Somebody who has read those
two will assume this one does too.

### The one case that does renumber is refused, not warned about

Painting a province in a colour another province already uses is not a recolour,
it is a **merge**: two colours become one and a province leaves the map.
Measured on DaC, that moves **51 region IDs** and takes `Celebrant_Province` off
the map entirely. So it is a refusal, and the refusal says why.

The other three refusals are the ones `start_region` already makes for a new
province, because a colour is a key and the ways a key can be wrong do not
depend on whether the record holding it is new: a marker colour (black is a
settlement, white is a port), the colour it already has, and a colour that is
painted on the map but declared by no record.

### It is every tile of the colour, not a bucket fill

`campaint` had a bucket and no whole-colour replace, and the bucket will not do:
**8 of DaC's 200 declared regions and 10 of Reforged's 199 are not one connected
blob.** A bucket from `Forodwaith_Province`'s anchor reaches 27,083 of its
40,995 tiles and would leave **13,912 behind in the old colour**, which is then
a colour no record declares - Phase 40's undeclared-province fault, manufactured
on purpose. `region_tiles` is the whole colour wherever it is.

**The marker guard cannot fire here**, which is worth knowing rather than
assuming: the tiles are chosen *by* carrying the region's colour, and a
settlement pixel is black. The settlement inside a province survives because it
was never in the list.

### The two halves are one save, and the existing guard refused its own

The pixels and the record's `rgb` line have to move together: a record naming a
colour nothing carries is a province with no tiles, which is legal to write and
fatal to play. The stroke goes onto the paint session's undo stack and
`plan_paint` writes both in one backup set.

**That is where the one real defect of the session turned up.** `_emptied`
compares every declared colour against what is painted, and during a recolour
the pixels are already the new colour while `descr_regions.txt` still names the
old one - which is exactly the shape of the fault it looks for. So the save
refused itself, correctly and uselessly. It now reads the pending record change
for that one province and judges every other one exactly as before, so a
recolour that painted over a neighbour still empties the neighbour and still
refuses.

The mirror case is refused too: undoing the stroke and then saving would write
the record alone, and that is caught by name rather than half-written.

### What actually reads a region ID, measured

The renumbering warning that 16e and 24 both ship ends "no file needs editing -
but a script that names a region by number now names a different one". **That
script exists and nobody had counted it.** Measured across every `.txt` under
`data/`, uncommented lines only:

| mod | live numeric region references | where |
|---|---|---|
| Divide and Conquer | **141** | 76 in `export_descr_ancillaries.txt`, 62 in `export_descr_character_traits.txt`, 3 in `campaign_script.txt` |
| Third Age Reforged | 3 | `custom_script.txt` (a further 9 are commented out) |

`IsRegionOneOf` and `IsTargetRegionOneOf` take regions "by label or number", and
DaC uses the number 141 times, each with a comment naming the province. So the
create and delete warnings matter more than their wording suggests, and this
phase's "nothing moves" is a measured reassurance rather than a politeness.

*(Whether DaC's 141 numbers are still correct was not established: the comments
are informal - some name a settlement, some a list of provinces - and a
string-match against the scan order produced disagreements that were the
matcher's fault, not the mod's. Counting them is honest; auditing them is a
different job and is not claimed here.)*

### Built

`campaint.region_tiles`, `recolour_faults`, `recolour`, `cancel_recolour`,
`_plan_recolour`, `_emptied(recolour=)`, `sess.recolour`, and `_stroke_over`
lifted whole out of `paint` so the recolour is the same stroke the brush makes
rather than a second writer with its own opinion about markers and its own undo.
`campmap.render_block` gains the `rgb` slot - `plan_region` goes on refusing that
edit, because the hand-edited form still has no way to move the pixels, and the
recolour is the only caller that passes it. `POST /api/map/recolour` and
`/api/map/recolour_cancel`, `web/js/recolour.js`, `#cmRecolour`, and a **Change
colour…** button on the record's Colour row.

### Verified

`tests/test_recolour.py` **47/47**, new, on a 12x8 map written for it with a
province in two disconnected pieces and a settlement pixel inside another.
Eight suites re-run green - `test_campaint` 169/169, `test_campedit` 107/107,
`test_codeview` 141/141, `test_web_modules` 75/75, `test_regiondel` 62/62,
`test_rebelpools` 68/68, `test_campnew` 52/52, `test_mapquery` 109/109.
`test_campmap` is 108/112 with its four pre-existing DaC-number failures.
`test_mapcheck` fails only *the whole rule set runs under one second*, which
a stashed tree fails harder on the same machine (1,522 and 1,840 ms against
1,214 and 1,227), so it is the load and not the change.

Driven in the real app against DaC: the dialog opens off the Colour row,
Repaint stays disabled until the colour changes, another province's colour is
refused with the merge reason, and a free colour repaints 221 tiles of
`Celebrant_Province` with a clean plan naming both files. The session was
discarded afterwards and the mod's own `descr_regions.txt` re-read to confirm it
is untouched.

## Phase 37 - The two exports the map screen cannot do

Both five stars, both **M**, both a reader over facts we hold. Two sessions.

### 37a - T7, the spawn export - DONE 2026-09-16

The scoping held in full, and the distinction it rests on is the reason the
phase works: 19b refused to WRITE the campaign script because its grammar is
nothing this toolkit models, 24 kept the refusal, and reading coordinates out of
one is not writing it. The refusal is untouched.

**What was invisible, measured.** The markers layer has shown seven kinds since
18b, every one of them out of `descr_strat.txt` and the two event files:

| campaign | script spawns | against descr_strat |
|---|---|---|
| DaC, imperial_campaign | **1,324** (1,317 armies, 3,822 units) | 305 characters |
| DaC, Shattered_Alliances | **1,131** (1,129 armies, 3,340 units) | - |
| Reforged, Fellowship | 98 (64 armies, 431 units) | 150 characters |

**Four fifths of what DaC's imperial campaign puts on the map was not on this
screen.** The layer's counts now read settlement 200, character 305, fort 105,
watchtower 295, resource 1,131 and **spawn 1,324**, which is why the category is
the only one that opens OFF: switching it on quadruples what is drawn, and a
layer that opens unreadable is one nobody opens twice.

**Every spawn carries a coordinate.** 2,510 `spawn_army` blocks over the three
campaigns and not one without an `x`/`y` on its `character` line, so the reading
is complete rather than a sample, and there is no silent remainder behind the
export.

### The reading is validated, and that matters more than the feature

A report nobody believes is worth nothing, so the resolution was checked against
the one thing that can check it - `stratobj.Vocabulary.province_at`, the same
call every other reader of a game coordinate uses:

* **DaC imperial: 1,322 of 1,324 land in a named province, and both misses are
  admirals**, which is correct because an admiral is a fleet.
* **Shattered Alliances: 1,127 of 1,131**, the four being two admirals at sea
  and two standing on the ocean's own colour while `map_heights.tga` calls the
  tile land.
* **DaC's 3,822 unit names are every one in its EDU.** That is what finally
  proved the parse (see below).

A reading that agreed with the map 99.8% of the time by accident is not a thing
that happens.

### The parse trap the real files set

A `character` line inside a spawn is comma-separated and **the `unit` line
beside it is not**. Measured: 4,253 unit lines across both mods, not one with a
comma, every one carrying `exp`, `armour` and `weapon_lvl`. Splitting both the
same way gives units called `Clan Heralds exp 3 armour 0 weapon_lvl 0`.

`soldiers` is in the attribute list because **six of DaC's 3,822 lines carry
it** - `unit Moria Balrog soldiers 1 exp 9 armour 3 weapon_lvl 2` - and stopping
only at `exp` made those six "Moria Balrog soldiers 1", which were exactly the
six dead EDU references the join then reported. With it, DaC is clean on all
3,822. **The six false findings were what found the bug.**

### Three states a coordinate can be in, not one

Resolution has to account for every spawn or the misses look like a hole in the
reader. There are exactly three ways not to be in a province and all three are
real on the installed mods: **at sea** (by `map_heights.tga`), **on a colour no
record declares** (two of Shattered Alliances'), and **off the map** (none
found). The suite checks that the unresolved count never exceeds the three
together, on every installed campaign.

**And a spawn with no coordinate is not resolved at all**, which a test caught:
resolving one resolved the `(0,0)` its fields default to, which on a real map is
the bottom-left corner and usually ocean, so a missing field was being counted
as a spawn at sea. It is `no_coordinate` now and nothing else.

### What Reforged's Fellowship campaign says, reported and not judged

That campaign puts **45 of its 98 spawns on sea tiles carrying a land
character** - 20 named characters, 16 witches, 9 generals - and names **247 of
its 431 units** in a form its own EDU does not have, the commonest being "Mordor
Orcs Super" 40 times against a roster that has "Mordor Orcs". Its
`descr_strat.txt` does the same with 72 of its 150 characters. All of it is
counted and none of it is a verdict: it is somebody else's campaign, the reason
is not established here, and 32c's baseline rule says a tool that blocks on
another mod's state is one nobody opens twice.

### Built

`unittransfer/spawns.py` (`Spawn`, `script_paths`, `scan_text`, `scan`,
`resolve`, `positions`, `view`, `dead_units`, `export_text`, `export`,
`region_tiles`'s opposite number `_unit_name`, `XY`, `AFLOAT`, `COLUMNS`), a
`spawn` category in `marker_view`, `GET /api/map/spawns`, `POST
/api/map/spawn_export`, and in `campmark.js` the category, the hollow ring that
says "not there at turn one", and the tooltip line that ends in the file line -
because the script is read and never written, so the answer to "this one is
wrong" is the file and an editor.

**The export is a CSV, and that is the point of calling it one.** The map
screen's only export until now is 16g's per-faction TGA, which is right for a
picture and useless for 1,324 rows. It goes to the cache folder beside the query
exports; the mod is not touched.

### Verified

`tests/test_spawns.py` **41/41**, new, on a little script carrying every shape
the real ones have. Eight suites re-run green - `test_mapquery` 109/109,
`test_web_modules` 75/75, `test_campaint` 169/169, `test_recolour` 47/47,
`test_rebelpools` 68/68, `test_stratobj` 65/65, `test_campevents` 82/82.
`test_campmap` 108/112 and `test_campstrat` 96/100 are the DaC-build numbers,
**both identical on a stashed tree**.

Driven in the real app: the route answers for both mods, the markers layer
reports `spawn: 1324` beside its six other categories, the browser's own y flip
is checked correct against the index, the tooltip reads *"random_name · named
character · 6 units · Dol Guldur (poland) · line 4051"*, an admiral at sea reads
*"at sea (a fleet)"*, and the export wrote 1,324 rows and 176 KB of CSV into the
cache folder.

### 37b - T3, an FE zoom for authoring map_FE.tga - DONE 2026-09-16

**Closed 2026-09-16, beta line, committed and not cut.** The scoping named the
three things it needed - "the frame, the scale and the export at the size
`map_FE.tga` actually wants" - and was right that the frame comes first. What it
did not know is that there is no such thing as *the* size, and that the screen
had a defect in it that this phase turns out to be the fix for.

### There is no size map_FE.tga wants, and that is the measurement

**Eight files, six of them distinct, four distinct sizes, three mods, and not
one of them is its own map's shape.**

| file | pixels | aspect | its grid's aspect |
|---|---|---|---|
| DaC `imperial_campaign` | 768x768 | 1.000 | 1.047 (510x487) |
| Third Age Reforged, all three | 320x275 | 1.164 | 1.047 |
| DaC base, and Shattered Alliances | 245x170 | 1.441 | 1.047 |
| BCBuff, both | 384x275 | 1.396 | 1.448 (420x290) |

The closest, BCBuff's, is still 3.6% out. Reforged ships one file in three
places byte for byte; DaC's two 245x170 files are a different picture each; and
BCBuff's prologue spells it `map_fe.tga` in lower case.

**Two of the eight are not maps at all.** DaC's base picture is the "DAC EUR"
logo, mountains and lettering, and its Shattered Alliances one is four faction
emblems over the word "DaC". Neither has any geography in it. **And one of the
six that are maps does not fill its own frame**: BCBuff's is a map inside a
painted ornamental border, so the geography stops short of the edge on all four
sides. Nothing here detects any of that and nothing here should - 32c's
baseline rule again, and "is this a map" is not a question pixels answer.

### So the frame is the whole phase, and it is what makes one zoom enough

A front-end picture is a picture of **some rectangle of the map at some
scale**, and until that rectangle is named "native size" names nothing. The
frame is that rectangle, and it carries the **picture's** aspect rather than
the map's. That is not a detail: `cmapX(tx) = ox + tx * zoom` is a single
scalar, it stays a single scalar, and a frame shaped like the picture is
exactly what lets one number draw the picture at one image pixel per screen
pixel and leave the map under it undistorted. An anisotropic stretch would have
needed two.

**The default frame is not a guess - it is what the artists used.** Registering
each real picture against its own `map_regions.tga` by the moments of the two
land masks gives the scale that mod's author actually drew at. Against the
proposed frame: DaC `imperial_campaign` **1.506 px per tile proposed against
1.524 measured, 1.2% apart**; Reforged **0.565 against 0.566, 0.2% apart**.

One axis of each is quoted and that is deliberate. The land mask is taken from
colour; DaC's picture has a pale blue-green sea against tan land and separates
cleanly, Reforged's is a sepia painting whose sea and land are the same
parchment and the mask there reads 98.2% land. **A picture cannot be registered
from its own pixels in general**, which is the reason the frame is proposed and
then dragged rather than derived. The corner drag holds the aspect and holds
the opposite corner still, because a frame that stopped being the picture's
shape would quietly start lying about "native size".

### The defect it was really about, found by building it

T3's words are "no loss of quality due to scaling up and then scaling down
again", and that loss was **in this toolkit, every frame**. `cmapCompose` draws
every ticked layer into one canvas that is width-by-height *tiles* - 510x487 on
both big mods - and the view then scales that canvas onto the stage.
`map_FE.tga` has no relationship to the tile grid, so DaC's 768x768 was being
squeezed into 510x487 and scaled back up, and Reforged's 320x275 stretched up
and scaled back down.

The picture is out of the composite now and drawn on the canvas itself, one
`drawImage` onto the frame's rectangle. **Measured on the real screen: 100 of
100 sampled pixels of DaC's front-end map reach the canvas byte for byte
identical to the file, zero difference.**

### The second defect, which the browser found and the suite now holds

Lifting the picture out of the composite exposed one. The composite fills
itself with an opaque backdrop when no terrain layer is on - "a map with every
layer off is not a blank screen" - and that fill is drawn *over* the picture,
which is now underneath it rather than in it. With every other layer off the
front-end picture did not appear at all. The guard is two halves and the suite
checks both, because the skip without the cache key is a composite that never
rebuilds when the layer is ticked and the bug comes straight back.

### The export is the mod's own header

`mapquery._write_tga`'s rule, followed: the depth, the origin, the run-length
flag and the trailer are the file's own, so what comes out drops straight over
what went in - measured, DaC's writes RLE 32-bit and Shattered Alliances' raw
32-bit, each matching its source. A mod that ships no `map_FE.tga` has no
header to borrow, so a plain 24-bit one is made and the export says so, rather
than refusing an author their first one. It lands in the export cache, never in
the mod.

### Built

- `unittransfer/mapfe.py`, new: `Frame`, `frame` (the proposal), `check_frame`,
  `render` (composes at the picture's own size, cropping before it scales so
  the intermediate is bounded by the result and not by the zoom), `compare`,
  `view`, `header_for` and `export`.
- `web/js/mapfe.js`, new: the `cmFE` panel, the FE zoom, the frame's outline
  and grips, the drag that holds the aspect, and the export.
- `unittransfer/server.py`: `/api/map/fe_view` and `/api/map/fe_export`.
- `web/js/campmap.js`: the picture out of the composite, the backdrop guard and
  its cache key, `cfeDraw` under the stack, `cfeDrawFrame` over it, and four
  pointer hooks so a press on the frame takes the button off the pan - behind
  the brush, the pin and a character, which are all things somebody armed.

### Verified

`tests/test_mapfe.py` **75/75**, new. Six suites re-run green - `test_mapquery`
118/118, `test_web_modules` 75/75, `test_campaint` 177/177, `test_recolour`
50/50, `test_campaignmap` 32/32.

**Twelve suites fail on this tree and all twelve fail identically on a stashed
one**, with the same counts: `test_campmap` 125/130, `test_campstrat` 115/119,
`test_campview` 67/70, `test_mapterrain` 78/79, `test_rebelpools` 74/75,
`test_stratchar` 117/118, `test_stratobj` 73/75, plus `test_edbvocab`,
`test_guided_fields`, `test_mapcheck`, `test_renames` and `test_spawns`.
**A third mod is installed now** - BCBuff - and its `map_regions.tga` is 295x189
against a `descr_terrain.txt` that says 420x290, which is what raises
`test_spawns`' `MapError`. The numbers moved from the figures 37a recorded
because the mod set changed, not because anything here did.

Driven in the real app on DaC: the panel reads *768x768, 32-bit*, names the
file, says *"768x768 squeezed into 510x487 and scaled again"* about what the
screen used to do, proposes *510.0x510.0 tiles at 0.0,-11.5, 1.506 px per
tile*, and the FE zoom puts that frame on screen at **767.99982 px** - 1:1 to
two ten-thousandths of a pixel. Hit testing answers `move` inside, `se` on the
corner and nothing outside; a 50-pixel drag moves the frame 33.20 tiles at that
zoom; a corner drag grows both axes by 66.41, holds the aspect at exactly
1.000000 and holds the opposite corner at 0.000. The picture sits under the
stack and shows through in the overhang above the grid. The export wrote
`map_FE_imperial_campaign.tga`, 768x768, 32-bit, 545,779 bytes, through the
mod's own header.

## Phase 38 - descr_campaign_db.xml

304 lines, **281 distinct tags**, six documents in the archive, and nothing in
`unittransfer/` has ever named it. It holds every campaign-wide constant the
engine reads: piety mode, prisoner treatment, ageing, the settlement upgrade
thresholds, and **fort and watchtower cost and permanence**, which is the half
of permanent stone forts that 22a could not reach - `stratobj.py` places a fort
and cannot make it permanent.

**A generated form over the tree, not 281 hand-written fields.** The file is
small enough to hold whole and regular enough to render from its own shape, and
a hand-written form over a file this wide would be wrong for the first mod that
ships a tag we did not type. What it needs from us is the vocabulary: which
tags are numbers, which are booleans, which are enumerations, and what each one
does, and that is what the six archive documents are for.

**Subrelease, both lines.** This is a data file rather than a map file, so it is
a mode of its own and goes out on the 2.x line as well.

### Done 2026-09-17 - a tab of Minor Files, typed by the file

**The generated form held, and the file made it easier than the write-up
thought.** Every value is one attribute and the attribute's name is the type:
`uint`, `int`, `float`, `bool` and `string`, and nothing else on either
installed mod. So there is no vocabulary to supply for the *boxes* at all - a
tick for a bool, a checked text box for the rest - and a tag nobody here has
seen gets the right one. The vocabulary the write-up asked for is only needed
for what a tag *does*, and that is the part the archive can answer for a
handful and no more.

**Measured on the two mods now installed**, which are not the set the scoping
counted: Divide and Conquer is 303 lines and 262 tags, Reforged 256 lines and
217. The same 18 sections in the same order, no tag written twice, no element
text, no tag with two attributes. **25 tags are in DaC and not in Reforged**,
and one tag changes type between them (`crusade_called_start_turn`, `int` in
DaC and `float` in Reforged). DaC writes `float = "1.0"` with spaces round the
`=` on 19 lines; Reforged ends in CRLF. **There is no vanilla copy on this
machine**, loose or packed, so nothing can say "back to the game's value".

**ElementTree is the gate and not the parser.** It reads both files and would
write back neither: comments, the spaces round `=`, a tab before a comment and
the line endings would all be its own. The scan is line by line, a save
replaces the characters between two quotes, and **a save whose text
ElementTree cannot parse is refused**. Both real files round-trip byte for
byte with no findings.

**What the archive explains is fourteen tags, and those are the only ones with
words under them.** The forts tutorial gives `can_build_forts`,
`destroy_empty_forts` and `fort_fortification_level` - the permanence switch
22a could not reach is `destroy_empty_forts false`, and **both installed mods
already have it and have `can_build_forts false`**. The piety tutorial gives
the Britannia mode, `alternative_religious_unrest` and its three `alt_rel_`
values, printed whole; the ransom tutorial gives the captor and captive
chances, printed in a quote box too mangled to trust for a default. **A
documented tag the file does not write is offered as an add** only where a
document prints its line whole, which is seven of the fourteen: **Reforged
lacks all four piety tags**, DaC has them on. Nothing else is addable, because
a default nobody documented is a guess written into somebody's mod.

**Where it went.** A tab on the Minor Files strip, after Guilds, as a mode of
its own the way Guilds is, rather than a Campaign Map panel: it is not a map
file and it ships on the 2.x line. A section list on the left with changed
counts, the search box across every tag and note, the mod's own comment beside
its tag, and one Save that previews every change before it writes. Raw text
picks the file up with no change, because it reads `modfiles.KNOWN`.

**One shipped defect found beside it, by reading and not reproduced**: switching
mod inside Guilds cleared every other mode's state and not `state.gu`, so the
previous mod's guilds could still be on screen under the new mod's name. It is
cleared with the rest now.

New: `unittransfer/campdb.py` (`parse_text`, `check_value`, `check_file`,
`overview`, `plan`, `apply`, `VOCAB`, `CampDbPlan`), `GET /api/campdb`,
`POST /api/campdb/plan|apply`, the `campdb` entry in `modfiles.MODULES` and
`KNOWN`, `web/js/campdb.js`, the `campdb` mode and tab in `core.js`, the `.cdb*`
styles. `tests/test_campdb.py` 50/50, new; `tests/test_web_modules.py` 105/105.

## Phase 39 - The engine ceilings, on the screens that write them

TWCenter's *List of Hardcoded Limits* is **already harvested in five places**
and cited in the source each time: the 32-unit recruit limit and nine levels per
tree in `buildings.py`, three excluded ancillaries and eight effects in
`ancillaries.py`, 31 factions in `factions.py`, the trait thresholds in
`traits.py`, 200 regions in `mapcheck.py`. Two sets were never taken.

- **Every EDU ceiling, and `edu.py` has no value check of any kind.** 500 units
  in a mod, 100 per faction, 6 to 60 men and 31 for a general, HP 15, attack,
  charge, armour and defence 63, shield 31, three officers, three mount
  effects, two formations, 244 turns to build. The unit editor writes all of
  them and checks none, which makes this the largest unguarded surface left in
  the toolkit.
- **20,000 faces on a campaign-map model.** `cas.as_mesh` already counts the
  triangles, so this is a line on the Strat models panel, which Phase 29 got
  drawing again on 2026-09-12 - the dependency is discharged.

**A ceiling shows and never blocks**, the same rule the map baseline follows. A
mod already over one of these is somebody else's mod with somebody else's bug in
it, and several of these limits are ones M2TWEOP raises - `modflags.py` already
knows which mods are marked for it, and a limit that EOP replaces is reported as
replaced rather than as broken.

**Subrelease, both lines**, because the EDU half is the unit editor's.

### Done 2026-09-17 - the list was Rome's, and Medieval II's is shorter

**The document this phase was scoped from is the Rome: Total War thread.** Its
title is *[Modding] RTW: List of Hardcoded Limits*, its faction limit is 21 and
its hidden resources mention Rome and the Marian reforms. Built as scoped, its
"men per unit, max 60" flagged **300 of DaC's units and 113 of Reforged's**,
on two mods that play. The five places that harvested it before had adapted
their numbers (31 factions, not 21); the EDU half never was.

**So every number now has a Medieval II source in the archive, and the rest are
not checked.**

| ceiling | source |
|---|---|
| 500 units in the file (M2EX lifts it) | *A Beginner's Guide to the Export_Descr_Unit* |
| 4 to 100 men | the same guide ("the smallest possible is 4, the largest 100") |
| attack capped at 63, either weapon | the same guide |
| up to three officers, three mount effects | the same guide |
| two formations, one square or horde and one shield_wall, phalanx, schiltrom or wedge | the same guide |
| stat_health 0 to 15, both values | *M2TW Ultimate Docudemons 5.3*, Character Attributes |

**Not checked, because only Rome's list says so:** charge, armour and defence
63, shield 31, 244 turns to build, 100 units a faction, 31 men in a bodyguard.

**Measured with the Medieval II set:** DaC 29 of 924 units (20 over 100 men,
8 secondary attacks over 63, 2 HP), and its 924-unit file is lifted because it
is marked M2EX; Reforged 6 of 427 - the Mumakil at 30 and 25 HP, Stone Giants
at attack 100 and 20 HP, a ballista at attack 100, and two units whose
formations are `square, horde`.

**The 20,000-face campaign model limit is dropped too.** It is the same RTW
list, and DaC ships three strat models at 30,252 faces - its evil Minas Tirith
among them. The count itself was already there: the 3D viewer prints vertices
and triangles for every model it opens, strat ones included, so that half
needed no code.

**Where it shows.** The unit editor's EDU fields tab carries a *Past the
engine's ceiling* note naming each document, and a save's preview warns about
a ceiling **the edit crosses** and not one the unit was already past. Nothing
is refused. `too-many-units` joined `modflags.CAP_FINDINGS`.

New: `unittransfer/educeil.py` (`unit_findings`, `mod_findings`, `report`),
`ceilings` and `roster_ceilings` on `edit.unit_detail`, the warning in
`edit.plan_edit`, `edCeilHtml` in `editor.js`. `tests/test_educeil.py` 24/24,
new; `test_edit` 60/60, `test_modflags` 22/22, `test_codeview` 141/141.

## Phase 40 - The new province the engine cannot read - DONE 2026-09-13

**Closed 2026-09-13, both lines, committed and not cut. It was four defects,
and the scoped one was the smallest of them.** The write-up below is kept with
its three wrong premises corrected in place, because what it got wrong is the
useful part of the record: every one of the three was an inference the repo
could not check, and the mod on this machine could.

**The scoped fix, and it is one line.** `campaint.new_record_lines` wrote the
resources line only when the user picked a resource, so a province created
without any reached `descr_regions.txt` as an eight-line record in a file of
nine-line records, and the engine reads that file by position. It always writes
the line now, `none` when the list is empty.

**Wrong premise 1: "not one of the 510 records uses the literal `none`".**
Measured over the five `descr_regions.txt` installed here, `none` is the
ordinary way to write the empty case: **vanilla 18 of 112, Vanilla Redux 78 of
252, `vanilla_kingdoms_uncompromised` 853 of 853**. So `none` was never a
choice this repo had to make - it is what the files this writes beside already
do, and the fix is smaller than the write-up thought.

**Wrong premise 2: "not one of the 510 records leaves the resources line
out".** Divide and Conquer's last record, `lol`, has **662 painted tiles** and
no resources line. It is a real short record in the wild, in the mod the user
plays.

**Wrong premise 3, and the important one: the engine crash.** It was inferred
from the format being positional and from the records agreeing, and the write-
up asked for a run in the game before the fix. **That run is not owed: DaC
ships the short record and the mod plays.** The claim is withdrawn. This does
not weaken the fix - writing the record in the shape the rest of the file is
written in is the same rule `new_record_lines` already followed for the indent
and the `legion:` line - but nothing here says it is a crash any more.

**Which settles the severity of the new check.** `campmap.check_record` takes a
third argument now, `campmap.file_shape(rf)`, and reports a record missing a
positional line its neighbours write. It is a **warning**, for two measured
reasons: DaC ships such a record and plays, and `plan_region` turns a fatal
finding into a refusal, so fatal would have trapped the one person able to fix
it - **the save is what rewrites the record**. It fires once across the 1,616
records installed here.

**The shape of a record is not its line count**, and that is the distinction
the phase turns on. `legion:` is keyed rather than positional and half the mods
write one; comments and blank lines sit inside a record's span; DaC's records
run to ten lines where vanilla's run to nine. `file_shape` counts which of the
unkeyed lines each record has, because that is what the engine reads off
position. `SHAPE_FIELDS` has one member and that is measured rather than an
oversight: the parser already puts a `problems` entry on a record missing its
religions line or its two bare numbers, a record with no settlement is the
wasteland form and has its own rule, and `legion:` shifts nothing. The
resources line is the only one that goes missing in silence.

### The three the write-up did not have

**The same eight-line record was reachable from the panel.**
`campmap.render_block` **dropped** the resources line when the last resource was
cleared off a record. Same defect, other direction, and `tests/test_campedit.py`
had a check asserting it as correct behaviour. It writes `none` now.

**`none` was read as a resource named `none`.** That is "neither a hidden
resource the EDB declares nor a trade resource descr_sm_resources.txt names" on
**931 records** - all 853 of `vanilla_kingdoms_uncompromised` and 78 of Vanilla
Redux - and `none` listed among a province's hidden resources in the query
table. A lone `none` is the empty list now; `none, gold` is still two
resources. The line on disk is untouched, so every installed file still
round-trips byte for byte, and `web/js/campmap.js` already drew the word "none"
under an empty chip list.

**And the largest: Divide and Conquer has 200 regions and this read 199.** DaC
writes one name line with a stray leading space, ` Erebor_Province`. The indent
is the whole of the first reading, so that line was body, `Withered_Province`
swallowed Erebor whole as a twenty-line record, and **it reported no
problems**. Erebor's **517 painted tiles** came out of here as land declared
nowhere: no name in the hover, nothing to click, a fatal `region.undeclared`,
and its settlement marker counted as an orphan. That orphan had been **written
down as a fact about DaC** in `RegionIndex.orphan_settlements` ("a province
painted on the map and never written down") and asserted in
`tests/test_campmap.py` as `== [(339, 65)]`. It was a fact about this module's
reader, and it had been sitting in the source as evidence for the opposite
conclusion.

`campmap._resplit_runs` re-splits any record holding **two colour lines**,
which is a signal no well-formed record can give - a record's other lines are
words, single numbers or braces, and only `R G B` is three numbers - so the
re-split is per record and a file the indent reads correctly passes through
untouched. `parse_block` gained a second reading for the one record whose own
name line is indented, since `record_text` hands out the file's own bytes; a
block that has genuinely lost its name line is still refused, because its
settlement would be the line read as the name and the retry is rejected unless
the result is a whole record.

### Verified

All **1,504** records of the four installed mods go `record_text` ->
`parse_block` -> `render_block` unchanged, and all five files round-trip byte
for byte. `tests/test_campaint.py` has sections 4c and 4d (**185/185**, was
168), `tests/test_campmap.py` section 1 has the run-on record (**143/148**
against 136/141 stashed - the same five DaC-build failures), and
`tests/test_campedit.py` is **139/139** against 138. **Eighteen suites were run
against a clean checkout of the last commit as well as against this tree and
every failing check name is identical in both.**

**One check left as it is, deliberately.** `test_campview` asserts "the other
undeclared colour is the 517-tile province - the hole 16a found, now measured".
That is Erebor, and it is declared now, so the sentence describes a bug that is
gone. The check fails on this DaC build either way, for the hard-coded numbers
beside it, so rewriting it would not turn it green: it belongs with the other
DaC-number checks and wants the build sorted out, not a new assertion.

**Both lines.** It is a defect in a shipped feature, so it is a 2.x subrelease
as well as a beta when a cut happens.

## Phase 41 - Merge one faction's name pool into another - DONE 2026-09-15

**From Mylae's `187d9ed`, and the one genuinely new idea in that push.** His
`MergeNamesModal.jsx` takes any number of source factions and merges their
`descr_names.txt` lists into the selected one, previewing per section what is
new, what is already there and what the total becomes.

**We had the reporting and none of the action.** `minorfiles.check_names`
already finds a name repeated inside a section and names both lines, which is
better than his bare count; `factionclone.clone_names` copies a whole donor
block verbatim as part of cloning a faction, with no dedupe and no merge. There
was no way to pull one faction's surnames into another's without retyping them,
and no way to clear the **153 duplicate-name findings** the four installed mods
produce.

### The engine, and it is the size the scoping said

`merge_section(target, sources, dedupe, sort)` returns the merged list plus the
counts that **are** the preview, and it sits in `minorfiles.py` beside
`check_names`, behind that module's existing `plan`/`apply` pair - so a merge is
previewed, backed up and undone like every other write there. Above it,
`merge_names` does all four sections against any number of donors, and
`merge_block` writes the faction's block back.

**Four sections, not three.** `NAME_SECTIONS` is `settlements`, `characters`,
`surnames`, `women`. Mylae's serializer writes only the last three and silently
drops `settlements`; none of the installed mods uses that section, which is why
he has not noticed. Ours carries it through untouched.

**Three things of his deliberately not copied**, and each is a check in the
suite:

* his preview labels source duplicates "skipped" even when dedupe is off, and
  with dedupe off they are in fact **appended**. `present` here is zero whenever
  nothing was skipped, because a count that is not true of the write is worse
  than no count at all.
* his Merge button is live with no source selected, where the only thing it can
  do is dedupe in place. That is a real action, so it is its own button and its
  own `action="dedupe"`; merging nothing is refused and the refusal names the
  button that does do it.
* his serializer drops `settlements`, as above.

**A section only the donor has is created rather than dropped.** `render_names`
refuses a section the faction has not got, which is right for an edit - the form
cannot show a box that is not there - and wrong for a merge, where the whole
point can be that the donor keeps a `surnames` list and the target keeps none.
`merge_block` writes the heading at the end of the block, indented to match the
sections the target already has and with the blank line every real file puts
between sections. It is appended rather than spliced into canonical order,
because moving lines past comments and blank lines a mod put there buys nothing:
the engine does not care what order the sections come in.

### The defect this turned up, which is bigger than the phase

**Phase 41's own suite could not run.** `test_minorfiles` died in the real-mod
sweep on `Owaib Cyfeiliog`, and had been dying there since the two vanilla mods
were installed. Nobody had seen it because **stderr and buffered stdout
interleave**: the traceback landed in the middle of the output and the suite
merely looked like it had one failing check. That is also why the 2026-09-14
sweep listed `test_minorfiles` as failing with no check count.

`render_names` refused any name with a space in it. Measured over the four
installed mods:

| section | entries | multi-word | share |
|---|---|---|---|
| `characters` | 18,794 | 90 | 0.5% |
| `surnames` | 5,363 | **2,413** | **45.0%** |
| `women` | 10,766 | 10 | 0.1% |
| **total** | **34,923** | **2,513** | |

`surnames` is where it is normal - `de Avena`, `of Anglesey` - because the
engine joins a forename to one of these and `de Medici` is a surname rather than
two names. But `characters` and `women` have them too and they are not mistakes:
`al Adid`, `Imad ad Din`, `Arigh Boke`, `Yax Kuk Mo`, `Hywel Dda`,
`Sorghaghtani Beki` - Arabic, Mongol, Mayan and Welsh names that are two words
in the histories they come from.

**What it cost while it stood: 58 factions across Vanilla Redux and
`vanilla_kingdoms_uncompromised` could not be saved at all.** `render_names`
refused the very list the form had just handed it, unchanged. And `parse_names`
raised 2,513 warnings about files that are perfectly correct. All 121 factions
of all four mods save now.

**The rule is replaced by the one real constraint.** A name may not BE a section
keyword, because `parse_names` tells a heading from a name by those four words
and would read it back as a heading, moving everything under it into the wrong
section. No installed mod has one, over all 34,923 entries. It lives in one
function, `name_fault`, because the old rule was enforced in three places and
was wrong in all three.

**The first draft of this fix relaxed the rule for `surnames` alone**, on a
sample that happened to be all surnames. That was the same mistake one size
smaller, and the per-section count above is what caught it. The comment in the
source says so, because the next person to read that table should know it was
read wrong once already.

`test_minorfiles` had `a name with a space in it is refused` asserted as an
expectation - the defect written down, the same shape as the `test_campedit`
check Phase 40 found.

### Verified

* `tests/test_minorfiles.py` **221/224** against 153 green with a crash before.
  The three counts are measured in both dedupe modes; the dedupe-off case is
  checked **first**, because it is the one his preview gets wrong. The plan's
  four refusals are checked. A merge is applied to the fixture mod and undone,
  with every faction it did not name byte for byte on both sides.
* Measured on the real mods, written nowhere: dedupe of DaC's `russia` is 78 ->
  72 characters and its 6 duplicate findings become 0, with the other 30
  factions untouched. Merging Vanilla Redux's `papal_states` into `slave`, which
  has no `surnames` section, writes the heading and 116 names. Merging the same
  source twice reports every name present and writes nothing.
* Driven end to end through the running server on Vanilla Redux: `egypt` merging
  `turks` and `moors` previews `characters 80 -> 207 (127 new, 3 already
  there)`, `surnames 55 -> 246`, `women 36 -> 116`; turning Remove duplicates
  off reports 130 added and **0** already there, which is the correction to his
  preview shown in the app; unticking every source disables Merge and says what
  to do.

### Three findings handed on, all in `descr_sm_resources.txt` - CLOSED 2026-09-15

The crash was hiding the end of the sweep, and behind it were three failures
with nothing to do with names. They were handed on as their own job and done the
same day; **`test_minorfiles` is 225/225**, green for the first time.

**`localised_name` turned out to be the answer to a bug rather than a keyword to
tolerate.** Neither it nor `is_slave` appears anywhere in `Reference/`, so both
were measured off the mods instead. `is_slave` is a bare flag on the `slaves`
record, the same shape as `has_mine`. `localised_name` takes a text tag, and the
two mods that write it use it for **exactly the three resources whose tag
`resource_tag` was deriving wrongly**: `camels`, `elephants` and `dogs` are
keyed `SMT_RESOURCE_CAMEL`, `_ELEPHANT`, `_DOG` - **singular**, where every other
resource including `slaves` matches its own plural name.

So the Resources tab had been showing **no name at all for those three in every
installed mod**, while reporting nothing wrong: "The Carrock", "Beacon of
Gondor" and "Horses" in Divide and Conquer, "Mumakils" in Reforged, plain
"Camels" / "Elephants" / "Dogs" in the vanilla one. `resource_tag_of(rec)` takes
the file's own answer first and falls back to the derivation, which now knows
its three exceptions; `SINGULAR_RESOURCE_TAGS` carries the measurement.

**And the 31-resource mod strengthens the edit-only refusal rather than
disproving it.** `vanilla_kingdoms_uncompromised` ships the 28 plus `glass`,
`honey` and `salt`, and the premise the refusal was written on - *all three mods
measured ship the same 28* - is indeed now three of four. But the reasoning
under it held: those three names appear in **exactly one file in the whole mod,
their own definition**. Nothing places them on the map, no other file in `data/`
mentions them, and `strat.txt` gives them no name. A `type` the engine does not
know is read and ignored, and a mod has now demonstrated it. The behaviour
stands; the sentence was what needed fixing.

The suite's `every real resource name is one of the 28` asserted that no mod
would ever add one, which is not the fact worth guarding. It now asserts the two
that are: all 28 are defined by the installed mods, and every name beyond them
is dead.

**Both lines.** `descr_names.txt` is a minor file rather than the campaign map.

## Phase 42 - The art a clone does not get, and is not told about - DONE 2026-09-14

**Reported by a beta user on 2026-09-12: cloning a faction leaves its symbols
missing under `data/menu/symbols/fe_buttons_24`, `fe_buttons_48` and
`fe_symbols_80`.** The report is real. The cause is not the one it sounds like.

**The copier is not at fault, and that is measured.** `menu` is already one of
`factionclone.ART_ROOTS`, and `_asset_hits` was run over **all 31 Divide and
Conquer faction slots**: it finds every symbol file in all three folders for
every slot, misses none, and correctly resolves the longest-slot rivalry (no two
DaC slots contain each other, so nothing is being eaten). `want_art` defaults to
`True` in `plan` and the dialog's checkbox ships checked. `apply` copies each
file and lists it in the undo manifest. **Re-measured on 2026-09-14 and all of
that held.**

**What is actually wrong: the clone gets only what the donor has, and says
nothing about the rest.** The scoping's four-folder table came back exactly:

| folder | Divide and Conquer | Third Age Reforged |
|---|---|---|
| `fe_buttons_24` | 29 of 31 slots | 30 of 30 |
| `fe_buttons_48` | 29 of 31 slots | 30 of 30 |
| `fe_symbols_80` | **17 of 31 slots** | **0 of 30 slots** |
| `fe_faction_units` | 28 of 31 slots | 28 of 30 |

**One fact under it was wrong, and the conclusion survives it.** The scoping
said Reforged's `fe_symbols_80` holds 17 files named for vanilla slots it no
longer uses. It does not: **Reforged's copy of that folder is empty.** The 17
vanilla-named files - `egypt`, `england`, `france.TGA`, `hre`, `ireland`,
`milan` - are **Divide and Conquer's**, and they are 17 of DaC's own 31 because
DaC keeps the vanilla slot names and puts LOTR factions in them. Same
conclusion either way: cloning any Reforged faction copies nothing into
`fe_symbols_80`, because the donor has nothing there to copy.

**The tool's one warning cannot fire here.** `plan` warns only when the whole
scan comes back empty:

```python
p.warnings.append(f"no art was found carrying `{src}` in its name - ...")
```

Banners, captain cards and unit-card folders are always found, so the list is
never empty and the warning never fires, however many individual locations came
back with nothing.

### What was built: the per-location report

`ART_PLACES` is the nine places a faction's art lives, each with a label, a
sentence saying where it shows up in the game, and whether the slot is in the
file's own name (`symbol24_sicily_roll.tga`) or is itself the folder
(`ui/units/sicily/`). `art_gaps` names every one of them the clone came away
from empty-handed, with **which of four reasons** it was:

* `donor` - the donor has nothing here either. Nobody can copy it and the art
  has to be drawn. **This is the reported case.**
* `exists` - the mod already ships a file of the new name here, so it was left
  alone. Never overwriting is the right call; saying nothing about it was not.
* `rival` - the only files here carrying the donor's name belong to a
  longer-named faction, so none of them is the donor's.
* `absent` - the mod has no such folder at all.

None of the four is a copier bug, which is why this is a report. `_asset_hits`
grew an optional `skips` list so the two decisions it used to make silently -
the rivalry skip and the `dst_path.exists()` skip - can be read back.

### Nine places, four mods, and the report is far wider than the report was

The scoping measured four folders on two mods. Measured across nine places on
all four installed mods, sweeping **every one of the 121 faction slots** as a
donor: **253 places come back empty**, and only **50 of the 121 donors** get
art everywhere.

| mod | slots | donors with every place filled | empty places |
|---|---|---|---|
| Divide and Conquer | 31 | 16 | 33 |
| Third Age Reforged | 30 | **0** | 63 |
| Vanilla Redux | 25 | 21 | 11 |
| vanilla_kingdoms_uncompromised | 35 | 13 | **146** |

**Not one of Reforged's thirty factions is a donor that fills every place.**
All 30 miss the 80px symbol, 16 miss the captain card, 9 miss the battle
banners, 5 the unit information cards. And `vanilla_kingdoms_uncompromised` is
worse than any of them: 22 of its 35 donors miss the 24px button, the 80px
symbol, the in-game faction symbol and the battle banners, each.

**Every one of the 253 is the `donor` reason.** Not one real mod produces
`exists`, `rival` or `absent` from a clone - which is worth knowing rather than
worth hiding, so all three get a fixture instead of a claim. `exists` is the
leftover-art case: a mod that still ships a file named for a faction it no
longer has, cloned into under that same name.

**And one thing measured on the way past that is worth writing down: the repair
path copies no art at all.** `factionaudit.repair_plan` (21's D6) builds its
`ClonePlan` by hand and never calls `_asset_hits`, so a repaired faction gets
the records it was missing and none of its symbols - and therefore has no gaps
to report either. That is correct rather than a defect, because repair is about
the records a faction is missing and not its pictures, but it is not what the
module's shape suggests at a glance.

### Verified

* `tests/test_factionclone.py` **74/74** against 64 before. The report has to be
  *exact*, so both directions are checked against the real mod: no place is
  reported empty that the clone got art in, and no place the clone got nothing
  in is left unreported. Each reason is then checked against the disk rather
  than taken on trust - a place reported `absent` really is not in the mod, a
  place reported `donor` really has no file carrying the donor's name.
* `tests/test_factionclone_apply.py` **39/39** against 30. A second synthetic
  mod produces all four reasons at once, and proves the `exists` skip does what
  the new sentence says: the file that was already there is byte for byte
  untouched after the write, and it is **not** in the undo manifest, so undoing
  the clone cannot delete a file the mod owned before it.
* One thing the fixture taught: a new name that **carries the donor's token**
  (`sicily` -> `sicily_two`) is picked up by the scan as if it were the donor's
  own art. It is unreachable through the app - `_validate` refuses a name
  already in the roster, and the repair path has the name in the roster where it
  wins the longest-slot rivalry and is skipped - so it is a note, not a fix. The
  fixture clones to `norman` for exactly that reason.
* Driven end to end through the running server on Third Age Reforged: cloning
  `aztecs` names four places with their reasons in the dialog, the header reads
  `11 file(s), 54 art file(s), 5.4 MB - 4 art place(s) empty`, and no console
  error anywhere.

### Two smaller things found in the same measurement

Both were in the scoping and both are still true, and both are left alone
deliberately. DaC ships a nested
`menu/symbols/fe_buttons_24/fe_buttons_24/` whose four files are picked up as
separate items and copied into an equally nested destination - faithful to the
mod, and a place still counts as filled when its hits came from inside the
nest, so inventing a rule to flatten it would be this module guessing at a
mod's own layout. And `fe_symbols_80/france.TGA` has an upper-case extension,
which the rename handles because `swap` only touches the matched slot token.

### Still open: the reporter's own mod

**The end-to-end reproduction against the mod in the report was not done, and
the user does not have the detail.** Everything above is measured against the
four mods installed here and driven through the running app on one of them.
The report may still turn out to be a different mod, an older build, or a
second cause on top of this one - and if a second cause exists, this report is
what will show it, because a clone that comes back with **no** empty places and
still has a blank button is a different bug from the one closed here.

**Both lines.** The faction clone is not the campaign map.

## Phase 43 - Playable, unlockable, not playable - DONE 2026-09-15

**Almost all of this was already built, and the write-up did not check.** 16j
shipped the roster writer: `stratcamp.plan_campaign` has taken `what="rosters"`
since it landed, `_roster_splice` replaces each of the three lists where it
stands, `roster_block` keeps the indent the block's own entries use, and the
Who plays tab in `web/js/stratcamp.js` has been a three-way radio per faction -
`cjRoster` - not three editable text lists. Order, indentation, the per-campaign
rule and the backup-and-undo ride were all done and all under test: part 4 of
`tests/test_stratcamp.py` moves a faction between two lists and part 5 saves
and undoes one on a real mod byte-exact.

**"Missing four times over" misread four guards as four refusals.** The line
*"this would change the playable, unlockable or nonplayable lists"* in
`stratcamp.py`, `stratchar.py`, `stratedit.py` and `regiondel.py` is each
writer refusing to touch a roster it was not asked about - a settlement edit,
a character edit, a delete - and every one of them is correct as it stands.
`stratcamp._guard` already exempts the three saves that may move a name:
`rosters`, `create` and `delete`. There was no writer owed.

**One thing was genuinely missing, and it is the sentence about the refusal.**
`camp.no_playable` was a warning, so a save that moved every faction into
`nonplayable` went through with a note. It is fatal now - but only when the
save is what empties the list. `check_rosters` takes the lists the save started
from as a third argument and reads nothing else from them: passed nothing, which
is what the campaign panel does, an empty `playable` list is still reported and
no more, because reporting is all a read can do.

**That split is 40's ruling applied a second time.** A flat fatal would refuse
the save of a campaign that already had no playable faction, and that is the one
file where this screen *is* the repair - moving a faction back is the same radio
button - so it would have trapped the only person who could fix it.

**Measured, not assumed.** All six campaigns on this machine write at least one
playable faction: the four installed mods' imperial campaigns at 26, 27, 31 and
18, vanilla's at 5, and the Norman prologue at exactly one. The prologue also
writes an `unlockable` block with nothing in it at all, which is why an empty
list is a shape the writer keeps rather than a state it refuses.

`tests/test_stratcamp.py` is **114/115** against 112/113 before, three checks
added for the three severities. The one failure is not this: Vanilla Redux
writes `random_persona_weights 15 42 25 18` on its campaign header, `stratcamp`
does not know the word, and the header-words check has been red on that mod
before this phase. The line survives a round trip - `serialise` hands back the
file's own bytes - so it is a gap in what is *reported*, the same shape as
`marian_reforms_activated`, and it is not scoped here.

The original scoping follows.


**Asked for by the user on 2026-09-12.** `descr_strat.txt` opens with three
rosters that decide which factions the campaign offers, and the toolkit reads
all three and will not write any of them.

What is already here: `campstrat.ROSTERS` is
`("playable", "unlockable", "nonplayable")` and the parser keeps each block's
line span; `campbrowse.js` prints the three counts on every campaign card;
`stratcamp.py` has a `camp.no_playable` finding for a campaign that offers
nobody; and `renames.py` follows a faction through all three when its slot is
renamed. So the data, the display and the rename are done.

What is missing is the edit, and it is missing **four times over**, in the same
words - `stratcamp.py`, `stratchar.py`, `stratedit.py` and `regiondel.py` each
refuse with *"this would change the playable, unlockable or nonplayable
lists"*. Four refusals of the same shape is the signal that one writer is owed,
not four.

**The shape.** A faction is in exactly one of the three, so this is a
three-way toggle per faction rather than three lists to edit - the writer moves
a name out of the block it is in and into the one asked for, keeps each block's
existing order and indentation, and refuses the one state the engine cannot
take: no faction playable at all, which is `camp.no_playable` already written
down. It rides `stratedit`'s existing plan/apply and backup set like every other
`descr_strat.txt` write, and the four refusals above become calls into it.

**Per campaign, not per mod.** Each campaign has its own `descr_strat.txt`, and
a faction playable in the imperial campaign need not be playable in another.

**Mylae has this** - `repBlock('playable' | 'unlockable' | 'nonplayable', …)` in
his `serializeDescrStrat` - and his version rewrites the whole block from an
array. Ours should move one name and leave every other byte alone, which is the
difference between the two tools everywhere else in `descr_strat.txt`.

**Beta only.** `descr_strat.txt` is campaign-map work.

## Mylae pushed on 2026-09-12, and this is what came

**Superseded: the block of 2026-09-12 is lifted.** That entry said his improved
validation and coloured overlays were not on GitHub and that
`Machiavello-1441/m2tw-editor` was still at `2740b0b`. He pushed three commits
the same day and `upstream_sync.py sync` has them: `2740b0b..187d9ed`, 7 files.

* `11e3eb9` - base44 vite plugin 1.0.35 to 1.0.36. Cloud plumbing, `skip`.
* `920841a` - the `map_features.tga` rewrite. **Phase 31**, and it changed that
  phase's scope rather than adding to it.
* `187d9ed` - the names merge. **Phase 41**.

**What he described is still not here.** The settlement-position validation and
the coloured overlay exports for religion, creator and owner are in neither
commit. Ours already judges a settlement position on four rules -
`marker.ground`, `marker.feature`, `marker.sea` and `marker.orphan` - and since
22b a refusal also names the nearest tile that would do, through
`mapsnap.nearest`, which is more than an alert. His overlays are 16g's
colourings and the per-faction TGA export. Ask for those files rather than
scoping from the sentence; re-run `sync` before scoping anything else.

**Two things to pass back to him**, both found while diffing this push: his new
orphan-white-source check is an `error` and vanilla trips it at image (175,14),
and the standalone `map_features_checker.py` he ported from cannot open either
installed map because both ship RLE TGAs.

---

# Phase 54 - M17, one door to every check - DONE 2026-09-22

First in the five-star queue. The complaint is ours and it is still true: we
have more validators than any of the four reference tools and no single place
that runs them. Somebody whose mod crashes has to know that the map screen,
the faction audit, the buildings screen, the battle-models screen and three
file editors each hold part of the answer.

### What exists, measured

Eighteen validators, in three shapes:

- **The rule shape.** `mapcheck.Finding` (86 `@rule`s, the six `merc.` rules
  among them) and `buildings.EdbFinding` (nine `@edb_rule`s, Phase 44): a code,
  `fatal`/`warn`/`note`, a message, and a `what` that never holds a line number.
- **The file checkers.** `check_file` in traits, ancillaries, guilds, campdb,
  factions and winconds, `minorfiles.check_any` and `educeil.mod_findings`.
  Close to the rule shape but not on it: some say `fatal: bool` through a
  local `finding()` helper, some say `kind` and nothing about severity.
- **The cleanup audits.** bmdb, dupes, stratmap and cards. These return buckets
  (unused, orphans, twins, strays), not findings. They are about a tidy mod,
  not a mod that starts.

**Cost, cold, on the two installed mods** (DaC, ROCSS): mapcheck 0.9s / 2.8s,
the faction audit 1.3s / 1.2s, the EDB checks 0.2s / 0.2s. Then bmdb 10.5s /
27s, dupes 7s / 19s, stratmap 7s / 16s, and **cards 24s / 95s**. That split
decides the screen: the first group runs when it opens, the second is a tile
that says what it would look for and starts on a click.

### The two crash guides are the checklist

`Reference/TWCenter/GUIDE - Crashes and how to fix them.pdf` and `Crash to
Desktop - TWC Wiki.pdf` list about forty causes between them, and almost every
one names a file and can be read off it. What they add that no validator here
has is **when** it bites: at launch, at campaign load, at the first turn, in
battle, when a panel is opened. That is how somebody arrives with a crash, so
it is how the screen is grouped.

### 54a - the door

- `unittransfer/health.py`: a registry of **sources**, each an adapter from one
  validator's own answer to one finding shape: `source`, `code`, `severity`
  (`fatal`/`warn`/`note`), `message`, `file`, `line`, `what`, `when`, and where
  to open it. A source that throws is reported as a source that failed, never
  as an empty one and never as the whole screen failing.
- `GET /api/health?mod=&campaign=` runs the fast sources. The slow ones are
  listed as doors into their own screens.
- A **Health** screen: fatal first, grouped by when it crashes, every row
  opening the screen that owns the finding. The existing screens keep their
  panels; this is a door, not a second copy of any rule.
- A test that runs every source over both installed mods and holds each
  adapter to the shape.

### 54a done 2026-09-22 - ten sources, one list, and a door into each screen

Built as scoped except one line: the cleanup audits keep no session result to
show. They are listed with what they cost and open their own screens, which
already show progress; a cached answer from twenty minutes ago would be the
one number on the page nobody could trust.

**Ten sources**: the map rules (off where the map screen is), the faction
audit, the EDB tree and recruitment checks, the EDU ceilings, traits,
ancillaries, `descr_sm_factions.txt`, guilds, campaign constants and the five
Minor Files tabs. DaC reads 5 fatal, 158 warnings and 95 notes in about 3s;
ROCSS 2 fatal, 120 warnings in about 5.5s, nearly all of it the map rules.

**Severity from the checker's own sentence.** Traits, ancillaries and factions
give a `kind` and no severity. A table here would be a second list to forget;
their messages already say "crashes the game", "the game stops loading the
file", "will not load this ancillary", and `health.severity_of` reads that.
`tests/test_health.py` holds it to sentences the checkers really write.

**One measurement changed the shape.** DaC's recruitment checks are 2 151
notes unit by unit, which buried the five fatals under them. They fold to one
note per building line with a count (95), and notes start hidden.

**Two defects found by building it.** My changes (52) never hid the unit
editor's filter sidebar, and neither did Health until it was added to the same
list. And a Health row for a guild that exists only in triggers lands on the
Guilds screen without a record picked - which is right, there is none, and the
row says so.

Exit: `unittransfer/health.py`, `GET /api/health`, `web/js/health.js`, a
Health entry in the menu, `tests/test_health.py` (40 checks).

### 54b - what the guides name and nothing checks

Measured on both mods before any of it is written, on Phase 12's rule that a
count from a wiki is not a fact about a mod. The candidates: an event a script
or the EDB fires that `historic_events.txt` does not declare; an `ai_label` in
`descr_strat.txt` missing from `descr_campaign_ai_db.xml`; a trait culture-
excluded while its antitrait is not; absolute paths in `descr_banners_new.xml`
and the projectile and standard files; runs of spaces in the modeldb; a
faction a building's early level omits and a later level names.

### 54b done 2026-09-22 - five rules, and two of the guides' claims refused

All six measured on DaC and ROCSS first. Five ship in `unittransfer/crashrules.py`
on `mapcheck`'s `@rule` shape, as an eleventh Health source; the finding rows
open the file at the line in Raw text, or the trait.

- **`ai.label_unknown`, fatal.** DaC's only undeclared label is `papal_faction`,
  in both campaigns, and DaC plays: it is the engine's own and is exempt.
  ROCSS ships no `descr_campaign_ai_db.xml`, so the game's is used and the rule
  does not run.
- **`event.no_text`, a warning, matched case-blind.** The guide says the match
  is case-sensitive; **631 of DaC's 633 script events differ from their key only
  by case, and DaC plays.** Read through `campevents.event_text_pairs`, which
  takes the `.bin` too, four are left, all on Shattered Alliances, one of them
  called `crash_game`. DaC ships them, so not the guide's CTD.
- **`trait.antitrait_cultures`, fatal.** None in 6 pairs on DaC or 323 on
  ROCSS: a crash rule that finds nothing on a shipping mod, as it should.
- **`path.absolute` and `modeldb.spaces`, warnings.** None on either mod.

**Refused: a faction a later building level names and an earlier one omits.**
DaC has 24 such levels in 14 lines and ROCSS 6 in 4, and both play. It and the
case-sensitivity claim are `crashrules.REFUSED`, and Health shows them in a
folded section so they are looked up, not rediscovered.

One defect of the building: counting newlines up to every script match made the
event rule 10.7s on ROCSS's eight campaigns. It counts only for a finding now
(1.6s). Exit: `tests/test_health.py` section 6, a fixture per rule and both
mods held to no crash-rule fatal (51 checks).

**Phase 54 is done.**

---

## Phase 56 - M12: several factions at once, and the faction files as a zip - DONE 2026-09-23

The reference tool's `factionBulkDuplicate.js` and `FactionZipExport.jsx`,
over our own clone (Phase 15g) rather than beside it.

**Several at once.** The *Add a faction* dialog takes more than one row: each
a slot and a shown name, all copied from one donor. A batch is the clones done
one after another - each row is planned against the files as the rows before
it leave them, through an `overlay` threaded into the clone's validation and
every cloner - and it is written as **one job with one backup set and one
Undo**. Because each row validates against the roster the earlier rows leave,
a slot asked for twice is refused naming the row, and so is the row that
passes the engine's 31 slots: ROCSS uses 30, so a batch of three there stops
at row 2 unless the mod is marked M2EX.

**Titles, and the shown name in the text.** Each row folds open onto the five
per-faction keys worth asking for at creation - leader, heir and former leader
titles, strengths, weaknesses (28 and 27 factions carry the titles on DaC and
ROCSS, 31 and 30 the strengths). Blank keeps the donor's. The reference's
*adjective* field is not offered: neither installed mod has an `ADJECTIVE` key
anywhere in its text, so there is nothing for it to write. **A new checkbox
puts the new shown name where the donor's stands in its copied text**: DaC's
Mordor has "Mordor Scout", "Mordor Diplomat" and twenty more, and turning them
into "Rhûn Scout" is a rename, not invented text - the line 15g drew. Whole
word only, in any script, so "Mordorim" stays "Mordorim".

**The zip.** *⇩ Faction files* beside the Add button downloads every file a
faction lives in - the twelve the clone writes, the culture and religion
lists, the banner definitions and the compiled `expanded.txt.strings.bin` -
laid out under `data/` so unpacking it over a mod folder puts each one back,
plus the art of the faction that is open (found the way the clone finds it).
ROCSS: 16 files, about 0.8 MB; with Venice's art, 380.

Exit: `tests/test_factionbulk.py`, 25 checks. It builds its mod by unpacking
the zip of ROCSS's real faction files into a temp folder, so the zip is tested
by being used: three factions in one batch, the ceiling, a doubled slot, one
record, and one Undo restoring every byte and removing every copied picture.

---

## Phase 64 - `descr_animals.txt`, `descr_standards.txt`, `export_descr_advice.txt` - DONE 2026-09-23

An **Animals, standards, advice** tab beside Populace and off-map, one sub-tab
per file (`sidefiles.py`). The three were one session because they are small,
and they are all or none because a mod can lack any of them: Reforged ships no
standards file, so none of the three is required on the mod card.

**Animals** are records a unit's `animal` line names, each with a battle
model. Checked against the EDU and the modeldb, which is what found **ROCSS's
Princess carrying `animal wardogs` where the file declares `wardog`** - a
warning, since ROCSS plays and a princess seldom fights. DaC's `pig` and
`wardog` point at models its modeldb lacks, and no DaC unit has an `animal`
line, so those are notes; the same gap on an animal a unit uses is a warning.
A class other than the header's `wardog` and `pig`, a number that is not one,
a missing key: the rest of the rules.

**Standards** are the flag models and their scales, six rectangles on the
standard's texture (four numbers from 0 to 1, checked for range and for
covering something) and the symbol sheets under `factions` and
`rebels_factions`, added and removed. **One rule the guides give was refused**:
four symbols a sheet would make DaC's `standard_index` 30 over seven faction
sheets a defect, and DaC plays, so the sheets are shown beside the roster's
highest index and never counted against it.

**Advice** is threads of items and the triggers that fire them, read in the
trait-file grammar they share so Phase 8's event and condition checks apply.
ROCSS's one thread is its background-script launcher and is clean; DaC's file
is its header. An item's fields and a trigger's score are edited, and a thread
is removed with any trigger that fires only it.

Line splices with a signature per file, DaC's missing final newline kept, one
backup and Undo, and Health reads all three. Exit: `tests/test_sidefiles.py`,
28 checks.

---

## Phase 63 - `descr_lbc_db.txt` and `descr_offmap_models.txt` - DONE 2026-09-23

A **Populace and off-map** tab beside Settlement mechanics, for the two files
a faction is written into that three modules found and none parsed
(`factionsites.py`).

**The populace** is each faction's townsfolk and their shares. Measured: 30
blocks in each mod, and every one adds up to exactly 100, so the total is
shown as it is typed and anything else is a warning. The nine model names are
the base game's peasants from its packed modeldb, so they are not checked.

**The off-map models** are three sections that nest differently - `navy` by
faction with a `large`, `medium` and `small` row, `settlement` and `port` by
culture then level around one row - so the reader is a tree of braced blocks
rather than a shape per section. The paths point at art the base game packs,
so a missing one is not a finding.

**It found a defect in DaC's own file**: `faction egypt` (line 115) has no
opening brace - 117 `{` to 118 `}` - so its `}` closes the navy section and
the fourteen factions after it are read outside it. A warning naming the line,
not a fatal: DaC plays. Roster mismatches are notes (DaC's populace has no
`gundabad` or `scripts` and still has an `ents`). Edits are line splices, an
off-map edit carries the signature of the copy it was made against, and Health
reads both files.

Exit: `tests/test_factionsites.py`, 18 checks.

---

## Phase 62 - B3: one file out of a mod, or one file into it - DONE 2026-09-23

Mylae's single-file push and pull, general where the pieces here were each
shaped for one job. On the Raw text screen: **⇩ Download** gives the open
file exactly as it is on disk (any file under `data/` through `/api/file`),
**⇧ Replace…** puts a file from disk over it, and **⇧ Put a file into the
mod…** puts one at any path under `data/`, new or over one that is there.
Every put is a plan first and one backup and Undo after (`fileswap.py`).

A put never overwrites by accident (it has to be told to replace), refuses the
same bytes, and refuses any path that leaves `data/` however it is spelled.
What the plan says before writing is what the files prove: **an encoding
change is named** (the old file's own bytes against the new one's, the way a
UTF-16 `text/` file saved back as UTF-8 stops a mod's text loading), a new
`text/` file that is not UTF-16 is named, the five files Raw text already reads
back (`descr_strat`, `descr_regions`, the win conditions, the roster, the EDU)
are **read by their own readers** and anything new they report is listed, a
`text/*.txt` recompiles its `.strings.bin`, and **a DDS put onto a `.texture` is
wrapped** in the game's 48-byte header - or refused with the reason when it is
not the DXT1 or DXT5 the header can hold.

Exit: `tests/test_fileswap.py`, 23 checks.

---

## Phase 61 - B2: delete a settlement, create one where none is, copy one between mods - DONE 2026-09-23

The three halves the B2 write-up named, all on the settlement panel, all one
backup and one Undo, and all under the read-back guard B1's create already had:
exactly one settlement fewer or more, every other block the text it was, the
header and rosters untouched.

**Delete.** Measured first: in both installed mods every province starts with
a settlement (DaC 200 of 200, ROCSS 449 of 449), so a delete makes something no
working mod here has. It is still allowed, on the project's own record: vanilla
ships Durazzo with no settlement block and plays, and the map checker already
calls an unclaimed province a note (`strat.region_unowned`). The plan names
the capital that moves (ROCSS's Venice: *Venice_Province -> Padua_Province*)
and warns when a faction is left holding nothing, in the words the owner move
already used ("opens with it already destroyed unless a script gives it one").

**Create.** A province the map declares and nobody holds used to open the
panel on an error; it now opens on the factions and a *Create a village here*
button, over B1's writer (last in the owner's block, never the capital).

**Copy into another mod**, which the write-up expected to be the big one and
is not, because the pieces were there: the destination province (same name,
declared on the destination's map) gets the source's level, population,
founding year, kind and buildings, written in the destination file's own
shape by `render_block`; it keeps its own owner and place, or, if it has no
settlement, one is created for a named faction first. **A building the
destination's EDB does not declare is left out and named**, since a `type`
line for a building the mod lacks is a campaign that does not start. The two
installed mods share no province name (Middle-earth and Europe), so this is
for mods on one map - a submod and its parent.

Exit: `tests/test_settlement_b2.py`, 20 checks, on two temp copies of ROCSS's
map and campaign.

---

## Phase 60 - Add a religion - DONE 2026-09-23

**The row was half stale.** It said `descr_religions_lookup.txt` was missing;
the Religions tab's add already wrote the block, the `religions` list, the
lookup and the shown name in one save. What it did not do was the rest of
geeko's *How to add a religion* (the archive's tutorial): **step 4, every
region**, and **step 2, the pip**.

**Every region's `religions { … }` line**, in every `descr_regions.txt` the
mod ships (the base map's and any campaign's own copy). Measured first: both
installed mods list every religion on every line and every line sums to
exactly 100 (ROCSS 449 lines with all 6, DaC 199 with all 10). So an add
appends `name 0` and moves no sum. **The guard the row asked for is a
starting share**: a region given one takes it from its other religions in
proportion, rounded by largest remainder so the line is exactly 100 again,
and a delete gives a religion's share back the same way. A line that did not
add up to 100 before is the mod's own, counted and left alone; it cannot be
given a share, and is named. DaC has one: a stray region block called `lol`
whose line is `religions { }`.

**The pip**: optionally copied from an existing religion's to where the new
block points, until one is drawn. Steps 3 and 5 (a faction taking the
religion, its temples) stay on the Factions and Buildings screens, and the
form says so.

Exit: `tests/test_religion_add.py`, 21 checks - the rounding, both mods'
real regions (every line, a share, the unseedable line, add-then-remove byte
for byte), and the whole add on a temp mod with one Undo.

---

## Phase 59 - `descr_settlement_mechanics.xml`, the rest of Mines and hidden resources - DONE 2026-09-23

A **Settlement mechanics** tab beside Campaign constants: the 42 factor
modifiers in their three families - population growth (`SPF_`), public order
(`SOF_`) and income (`SIF_`, where `SIF_MINING` is the mines) - each with its
pip, city and castle modifiers and its min/max clamp, and the city and castle
population ladders. An empty box adds a modifier the factor lacks; clearing
one takes its line out. The half the row named as "the ceiling of 63" was
Phase 45's and is done there: the hidden-resource count is stated beside
TWCenter's 63-or-64, which DaC's 75 passes.

**Measured on both mods**: 42 live factors each, none twice, and DaC keeps a
43rd commented out - so comments are skipped, and anything in one is the mod's
note. Every level's `upgrade` is at most its `max` and equals the next level's
`base`. **DaC shows what is not a rule**: its `large_city` has `upgrade` 4000
below its `base` 16000, and the mod plays - so there is no "upgrade above base"
check. The checks are the ones that follow from the numbers: a value that is
not a number (fatal), `pip_min` over `pip_max`, `min` over `max`, an `upgrade`
over `max` (a threshold the capped population never reaches, so the level is
never outgrown), and, as a **note**, an `upgrade` that is not the next level's
`base`. Both mods have no findings. Health reads the file too.

The file is scanned as text and saved as a splice between quotes, like
`descr_campaign_db.xml`, so its comments, indentation and CRLF are its own.

Exit: `tests/test_settlemech.py`, 21 checks.

---

## Phase 58 - Will this mod even launch - DONE 2026-09-23

A *Launch* row on each Home card: whether the GAME will start the mod, beside
what the toolkit can do with it. Nothing is written; every rule is one a real
mod or the TWCenter archive states, and each finding names its file
(`launchcheck.py`).

**The ways a mod is started, measured on the two installed ones.** A `.bat`
in the mod folder that goes up to the game folder and starts an executable
with `@<its .cfg>` - ROCSS's tries `M2EX.exe` and falls back to
`medieval2.exe`, which is one route whose note says so, not a failure - and
the M2TWEOP launcher, whose `eopData/config/uiCfg.json` names the `.cfg` in
`modCfgFile` (DaC: `TATW.cfg`; ROCSS: `configuration own.cfg`). A mod with
neither is looked at through any `.cfg` carrying `[features] mod =`.

**Per route**: the `.cfg` is there and its `mod =` is this folder (DaC's own
README: "make sure ... the config file has the right folder name"), case-blind
as Windows opens it; `[io] file_first` is set, as a warning (ROCSS's cfg says
what it does: "look up sequence of files: mod, main game, packs"); the
executable is in the game folder; and it is **Large Address Aware**, read from
one bit of its PE header - DaC ships `LAA.txt` and a patcher and ROCSS ships
`4gb_patch.exe` because a big mod outgrows 2 GB. **The launcher's registry
entry is told and never judged**: the archive's *Registry Entries for the
Launcher* says they serve the disk version's launcher and no longer work with
Steam. Both installed mods come out *will start*.

Exit: `tests/test_launchcheck.py`, 18 checks - the PE bit on a header built
byte by byte, a game folder built one fault at a time, and both mods.

---

## Phase 57 - M16's editor half: edit an animation, and get a model out - DONE 2026-09-23

The reference's *AnimationEditor* and *Asset Converter*, over Phase 55's
reader and viewer. Two halves, both in the Models viewer.

### 57a - the animation editor

**A writer first, and it is exact**: `casanim.write_anim` puts every one of
the 1 751 readable loose animation files on both mods back byte for byte. The
parts no edit touches - the header's other bytes, each name and property
string, the chunk list - are kept as read; everything the reader checks
(counts, offsets, the length) is written from the object, so an edit comes out
consistent. It found a fact the reader had let pass: **230 animated files have
no chunk list at all** (220 of DaC's siege engines, all 10 of ROCSS's) and end
at their pivots.

**The edits** (`animedit.py`), each previewed live in the viewer by the
server - one implementation, so what plays is what Save writes: keep a range
of keys; speed; play in place (a cycle's travel taken out of the pelvis keys);
scale every pivot and position key per axis (the reference's "fit a dwarf");
turn one bone by X/Y/Z degrees at every key; and set a bone's rotation
outright at the key under the scrubber. A key set is numbered as the file has
it even when a trim runs with it. Angles are Euler X then Y then Z, and 500
random ones round-trip to 5e-5 degrees.

**Saving** writes a new file beside the old (or over the one opened, never
over a different one), optionally points the skeleton's action at it in
`descr_skeleton.txt` - only the path changes; the flags, the spacing and the
other-mod prefix DaC writes on every line stay - and is one backup and one
Undo. **Every save says the game will not see it yet**: a mod's animations
play from `data/animations/pack.dat`, which DaC, ROCSS and the base game all
ship, and a loose file reaches the game once the pack is rebuilt with the
TWCenter archive's `xidx` (`xidx.exe -caf pack.idx < anim_list.txt`).

### 57b - the converter

**A model to `.glb`**, which Blender imports with nothing installed: the parts
shown, the skin chosen (glued as the viewer glues it), the skeleton, the skin
weights and the skeleton's loose actions. **Stock Blender 5.1 imports it and,
posed in the idle, its man is the viewer's man mirrored, the bounding box
within 0.4 mm.** The mirror is the whole trick: M2TW is left-handed, so x is
negated on every position, normal, pivot and key, every triangle's winding is
reversed, and every rotation becomes `(x, -y, -z, w)`. The DaC soldier with
all 150 of his skeleton's loose files is 8.7 MB and 2.8 s.

**A model to `.obj`**, zipped with its `.mtl` and texture, geometry and UVs
only. **`.texture` to and from `.dds`** for any file from disk, touching no
mod: measured on 45 342 `.texture` files, 45 340 are a 48-byte header and a
DDS (the reference says "typically 4"), and two are bare DDS under that name,
which come back as they are.

**Not done, on purpose**: MilkShape `.ms3d` (a 2008 program; Blender is where
the community's pipeline lives now), and **writing a `.mesh`** - the
reference's encoder writes a layout no real file has, and a real one is a
boost archive with IWTE's class bookkeeping. Models go out; nothing comes
back in.

Exit: `tests/test_animedit.py` 29 (the byte-exact writer on both mods, every
edit, a save and its Undo on a temp mod), `tests/test_modelexport.py` 21 (the
conversions, the `.glb`'s structure, the `.obj`, and the Blender import against
`tests/_skinref.py`'s reference skin).

---

# Phase 55 - M16's playback half: a battle model that moves - DONE 2026-09-23

Asked for by a tester ("the bmdb editor does not show the animation for the
model"). It is the backlog row *M16, the playback half*, rated M on the belief
that `cas.py` already reads the container. **Measuring said otherwise, twice:**

- **`cas.py` does not read an animation file.** It reads model `.cas` files;
  the first of DaC's animation files it was given
  (`animations/engine/ballista/ballista_stand_to_crank.cas`) fails at byte 680,
  a zero-length chunk, because an animation is a different layout. No document
  in `Reference/` describes it, so the reader is reverse-engineered from the
  files: per-bone keys, the time base and whatever quantisation it uses.
- **Where the files are depends on the mod.** DaC ships 1 753 unpacked
  animation `.cas` files; ROCSS ships 10; the base game none - vanilla's live
  in `animations/pack.dat` and `skeletons.dat`, a packed format nothing here
  reads. So a model plays only when its mod ships the animations loose.
- **DaC's `descr_skeleton.txt` names another mod's folder** for every file
  (`mods/Third_Age_3/data/animations/...`, 410 skeleton types). The game plays
  because the same relative path exists under DaC's own `data/`, so a path
  resolves by dropping `mods/<any>/data/` and reading it in this mod.

The chain it needs: a modeldb entry names its skeleton(s); `descr_skeleton.txt`
names that skeleton's files per action (`stand_a_idle`, `walk`, `run`...); the
animation file gives each bone's rotation over time; the viewer skins the mesh
it already draws (it already knows the bones, "rigged to N bones") and plays
it, with a picker for the action.

**Size: L, with a research step first.** 55a is the reader alone, held to
every loose file on DaC; nothing on screen moves until it reads all 1 753.
55b is the chain and the playback.

### 55a done 2026-09-22 - the animation reader, 1 751 of 1 763 files

`unittransfer/casanim.py`. The header is the model header; what an animation
adds is each node record's five integers - rotation and position key counts,
their byte offsets into one key block after the pivots, a zero - and a
properties string. **That string is why cas.py saw "25 bytes"**: empty in a
soldier's file (length 1 and its NUL), 3ds Max's physics notes in a siege
engine's, and read as a fixed 25 it sank every node after the first one that
had any. Rotations are 16 bytes a key, positions 12, then the model's chunk
list, which must land on the last byte; the offsets are checked as a running
sequence, so a misread fails instead of playing something plausible.

**Four node-table layouts, not one.** Soldiers (3.16 on) are cas.py's; the
3.02 engines write one pad byte after the node count and no properties string,
and 3.05 to 3.12 the other two combinations. The version number does not pick
one reliably, so each is tried in turn and the first that passes every check
wins.

**Read: all 10 of ROCSS's, 1 741 of DaC's 1 753.** The twelve are one siege
engine, the Isengard ballista, six files and a `convertedfiles` copy of the
same six, **every one cut short** - the node table ends 12 to 48 bytes before
its own pivots. Two are played by `descr_engine_skeleton.txt`. Every file
`descr_skeleton.txt` names that the mod ships loose reads (1 625 on DaC).

**Three things 55b inherits, measured here** (the last two were a misread,
found and put right in 55b - see below):

- **Most animations a mod plays are not loose.** DaC's `descr_skeleton.txt`
  names 14 715 distinct files and ships 1 625 of them; ROCSS names 3 111 and
  ships none. The rest are in `animations/pack.dat`, which nothing reads. 55b
  plays what is loose and says so for the rest; a `pack.dat` reader is its own
  question.
- **The exporter does not normalise.** 99.52% of DaC's 1.23 M soldier
  rotations are within 0.5 to 1.5 of unit length; they are normalised when
  sampled.
- **Which component is w is not settled by counting**: `(1,0,0,0)` and
  `(0,0,0,1)` are both common exact still keys. Drawing the skeleton settles
  it; 55b's first job.

Exit: `tests/test_casanim.py`, 27 checks - fixtures in both main layouts, a
short track, three kinds of refusal, sampling, `resolve()`, and both mods.

### 55b done 2026-09-23 - the chain, the skin and the playback, and 55a's misread

**The Models screen's viewer plays a model's animations.** An *Animation*
section under the pickers lists every action the entry's skeletons name in
`descr_skeleton.txt`, the ones the mod ships loose playable and the rest marked
*packed*; picking one plays it, with Play/Pause, a scrubber and a speed. On
DaC's `lamedon_clansmen` (MTW2_Mace) that is 156 of 195 actions; on ROCSS
every action is packed and the section says nothing here can play.

**The first job found that 55a read every animated file wrong.** The pivots
come **after** the key block, not before it. Both orders account for every
byte of every file, so all of 55a's checks passed - the offsets as a sequence,
the chunk list landing on the last byte - and a base pose (no keys) cannot tell
the two apart. Drawing gave it away: read before the keys, MTW2_Mace's idle
has the pelvis quaternion repeating through its "pivots", and every key was
read `nodes x 12` bytes late, twelve bytes into a quaternion. That one misread
is both of 55a's open questions:

- **Which component is w**: (1,0,0,0) and (0,0,0,1) were "both common exact
  still keys" because a still key read from its fourth float is `(1,0,0,0)`.
  Read where it is, **w is last**: the idle's first pelvis key is
  `(0.052, 0.002, -0.000, 0.999)`.
- **The exporter normalises.** "99.52% within 0.5 to 1.5" was misaligned
  floats. All 1 231 346 soldier rotations on DaC are unit length to 2e-7.

The pivots read after the keys are the base pose's to the last digit, which
`test_casanim` now holds. The twelve refused Isengard ballista files are
explained exactly: each ends twelve bytes short, the last node's pivot, with
no chunk list.

**A position key is an offset from the pivot.** A soldier's pelvis has pivot 0
and keys its height (0.966 in the idle); every other soldier bone keys zero. A
siege engine's destruction flings its wood chunks a few centimetres from
pivots a metre out, which only reads as an offset.

**The skin, measured on a DaC soldier.** `mesh.py` kept only the bone names;
it now keeps the two weights a vertex and the bone-index stream, whose four
bytes are packed like the normals - the first weight's bone is the THIRD byte,
the second's the second. The model's bind pose is the skeleton's base pose
with the pelvis at the origin: vertices sit around their bones' pivots chained
from zero, arms out in a T. The model's bones meet the skeleton's by name; the
six a soldier has that the skeleton lacks are weapon and shield bones no
vertex is weighted to (weapons are skinned to the hand, the shield to the
forearm).

**How it is drawn.** Skinned on the CPU into the buffers the still model
draws from: 1.7 ms a frame for 30 349 vertices, and the shaders, wireframe and
UV tools untouched. The pose is lowered by the model's own lowest point, so
the man stands where the still model stood. **A cycle travels**: the walk
carries the pelvis 1.62 forward per loop and the charge 2.58, so looped as
written he strides out of frame and snaps back. A cycle is known by closing
(every bone's last rotation key is its first) and is played in place with its
travel taken out evenly; a death or a turn does not close and keeps its
motion. The two routes: `/api/model/anims` (the chain, loose or packed) and
`/api/model/anim` (one file's keys). `descr_skeleton.txt` is 9.5 MB on DaC, so
its parse is kept until it changes, and the loose-file index until one of its
folders does: 0.5 s cold, 19 ms after.

**Not done, and each is its own question:** `animations/pack.dat` (most of
most mods' actions); the skeleton's `scale` line (54 types on DaC), which the
game applies and this does not; a rider on his mount together; and the
`.evt` sound and event files beside the animations.

Exit: `tests/test_v3anim.py`, 28 checks - the payload's skin on a fixture and
a real soldier, the `descr_skeleton.txt` chain and its cache, the page's
`v3aSample` run in node against `casanim.sample` on real files, cycles, and the
whole soldier skinned in node against a reference skin written in Python (every
vertex within 1.3e-6). `test_casanim` 30 (the layout held on a real file),
`test_viewer3d_http` 29 (both routes, the skin in the payload's length).

**Phase 55 is done.**

---

# Phases 51-53 - a user's feedback on the EDB editor, 2026-09-21

**Asked for by the user on 2026-09-21**, passing on feedback from someone
editing AGO's EDB with the toolkit, with a screenshot of a recruit pool list
marked *insert below me*. Five complaints about the Buildings screen and the
codeview, and one idea that is a feature of its own. The user set the order:
**the five are the immediate next phase, ahead of 45**, and the idea comes
straight after, because it is the tricky one. Three questions were settled with
the user before this was written, and the answers are in the write-ups below.

| Order | Phase | Size | Line | Why |
|---|---|---|---|---|
| ~~22~~ | ~~**51** Order, insert below, a still codeview, and every gate at once~~ | M | **both** | **done 2026-09-21** |
| ~~23~~ | ~~**52** Change sets: record your edits, port them to the next version~~ | L | **both** | **done 2026-09-21** |
| ~~24~~ | ~~**53** Change sets, switched in place~~ | M | **both** | **done 2026-09-21** |

45, 46, 47a, 47b and 48 keep their order behind these three.

## Phase 51 - Order, insert below, a still codeview, and every gate at once - DONE 2026-09-21

**Done 2026-09-21, both lines, cut on request as v2.3.6 and beta 2026-09-21. All four parts shipped as
scoped, and building them found two things the scoping did not: a defect in
shipped work, and a second one the first was hiding.**

### What building it found

**Trade resources were never in any region.** The all-gates summary's first
run over the two installed mods said 24 real clauses could be met nowhere, and
most of them were `requires resource gold` or `sulfur` or `ivory`. A trade
resource is placed on the map by `descr_strat.txt` (`resource sulfur, 344,
333`) and belongs to the province that tile is in; `edbvocab.regions` read only
`descr_regions.txt`, whose resource line carries the hidden ones. So the
per-term "📍 N settlements" marker the clause picker has shipped since Phase 12
said **∅ nowhere for every trade resource in every mod**. ROCSS places sulfur
three times, DaC places chocolate twice. `edbvocab.placed_trade` now joins them
in through `mapquery.Facts`, which already put every placed resource in its
province, so there is still one reader of that file. It costs about 0.7 s per
mod on a vocabulary that is cached on the mod, and a map that will not load
leaves the regions file's line standing rather than failing the vocabulary.

**What is left is real.** With the join, 674 clauses across the two mods have a
resource gate and three can be met nowhere, all on DaC: two Snow Troll pools
gated on `Rhudaur` (4 regions) and `ResD` (13), and one pool on `Cardolan` and
`ResF`, with no region carrying both. Those are the finding the feedback asked
for, and the row now says `∅ no region passes every gate`.

**The code view lit the wrong line after a move.** Rows named their span by
the file line they came from (`capline#N`), which was safe while a row could
never move. A moved row sits on a different line of the re-rendered text, so
hovering it lit its old neighbour. The rows now name their span by written
position, `level:X:cap#N`, which the server already emitted and which is right
either way. Checking that turned up the second defect: **adding units through
the picker never re-rendered the code view**, so the pane went on showing the
level without them until the next keystroke. `bldAddPicked` now follows the
edit like every other path.

### What shipped

- **Order.** A grip to drag and ▲ ▼ for one step, on every recruit pool and
  every other capability, inside its own block (`capability` and
  `faction_capability` do not trade rows). `_plan_capabilities` writes the
  list's order: a save that moves nothing, or only adds at the end, takes the
  old one-splice-per-line path byte for byte; a moved row or a row inserted
  mid-list re-lays the block's inside in one splice, copying every untouched
  line as the file has it, with the comment and blank lines above each line
  travelling with it and a closing remark staying at the bottom. A deleted
  line's place in the list is not an order change.
- **New units land where they are written.** They used to be shown at the top
  and written at the bottom, which is the complaint as the feedback put it.
  They now go at the end, the picker scrolls to them and flashes the first,
  and `＋` on any row opens the picker to put them directly under it. `＋` on a
  plain capability adds a row under it.
- **`code_view_follow`**, click-only by default: a hover lights the line and
  never scrolls, a click anywhere on a box scrolls to it, and `⇕ Follow hover`
  on the pane's bar brings back the old way. One widget, so every editor.
- **Every gate at once**, on each row and in the clause dialog: the regions
  that pass the clause's `hidden_resource` and `resource` terms, left to right
  as the engine reads them, each with its starting owner and a ★ on the ones a
  named faction starts with, and the terms that do not narrow it listed as
  assumptions.

`tests/test_buildings.py` section 13 is the writer (a swap, the append path
unchanged, an insert under the first line, comments travelling), and 13b runs
the page's own evaluator in node: seven synthetic clauses including one where
precedence would answer differently, and every one of the 674 real and-only
resource clauses against a plain set intersection.

### The scoping, as written before it was built

**Measured against the code on 2026-09-21. All five are real, and none of them
is half-built.**

**1. Recruit pools cannot be reordered.** `bldAddCap` pushes onto the end of
`lv.caps`, and nothing in `buildings.js` moves a row: no drag, no up or down.
The order matters in game, because the recruitment panel lists units in the
order the EDB gives them. The writer is why this is a phase and not a button:
`_plan_capabilities` in `buildings.py` edits existing lines *in place* so the
trailing comments DaC's EDB is full of stay byte-exact, and it appends new
lines just above the block's closing brace. A move has to become a splice that
lifts a line **with its trailing comment** and drops it at the new position,
and a new row has to carry an anchor ("after line N") instead of always going
to the bottom.

**2. Insert below.** A `＋ below` on every capability and recruit row, in both
`capability` and `faction_capability`, that opens the new row directly under
the one it was pressed on. The feedback asked for this so a long list does not
have to be scrolled to drag a line into place, which assumes (1) is dragging.
It is: drag by a handle on the row, plus move up and move down for keyboard
use and for the list that does not fit the screen. Bulk edit holds its
selection by object, not index (see the comment over `bldBulk`), so a move does
not slide it onto the neighbours.

**3. The codeview moves under the pointer.** `cvBindHover` in `codeview.js`
paints the hovered row's line on every `mouseover`, and `cvPaintSpans` calls
`cvReveal`, which scrolls. So running the mouse down the GUI drags the file
around, and hovering the space between rows resolves to the whole record and
throws the pane back to the top of the snippet. **Settled with the user: a
setting, defaulting to click-only.** `code_view_follow` beside
`code_view_tidy` and `code_view_comments`, saved through `cvSetSetting`. In
click-only mode a hover still lights the line and never scrolls; a click on a
row scrolls to it, the way a click on a row's name already does. `hover` keeps
today's behaviour for whoever likes it. It is one change in the shared
component, so every editor that uses the codeview gets it, not only Buildings.

**4. Every gate at once.** Each `hidden_resource` and `resource` term already
has its "📍 N settlements" marker (`condWhereHtml`, fed by `edbvocab.regions`),
but nothing combines them, so a recruit gated on
`hidden: GondorEast AND hidden: ResF` means working the intersection out by
hand. The summary evaluates the clause over every region, left to right with
and/or and `not`, the way the engine reads it (no precedence), and shows the
regions that pass. **Settled with the user: factions are shown, not
filtered.** Who owns a region changes during play, so a `factions` term does
not narrow the list; each region carries its starting owner, and the ones a
named faction starts with are marked. Terms that cannot be decided per region
from the files (`event_counter`, `region_religion`, `building_present`) are
listed under the summary as *not narrowed by*, so the number is never read as
more certain than it is. It shows in two places: the clause dialog, and the
`REQUIRES` strip on each recruit row, where `∅ no region passes every gate` is
the finding worth having, because a pool nobody can recruit from is the same
silent failure as a missing hidden resource.

**Exit:** drag, move up and move down on recruit pools and on every other
capability, written as moves that keep trailing comments; `＋ below` on every
row; the new rows land where they were inserted; `code_view_follow` with
click-only as the default and hover-scroll as the option; the all-gates summary
in the dialog and on the row, with the owner marks and the *not narrowed by*
list; `tests/test_buildings.py` asserting that a move and an insert round-trip
every other line byte for byte, and that the gate evaluation follows the
engine's left-to-right order on a clause where precedence would give a
different answer.

## Phase 52 - Change sets: record your edits, port them to the next version - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** A **My changes** screen,
`unittransfer/changesets.py`, and `tests/test_changesets.py` (45 checks). The
scoping below held in its shape; four things were decided or found by building
it, and they are the part worth reading.

### What building it decided

**The hook is `logutil.file_op`, not the forty `backup_and`s.** The scoping
named the `backup_and` copies as the capture point, and there are forty modules
with their own. All of them log `BACKUP` before a write and `WRITE` (or `COPY`,
`MOVE`, `RESTORE`) after it through `file_op`, whose docstring already promised
that nothing reaches the disk without passing it. So `changesets.capture` hangs
off that one function: the first `BACKUP` of a file keeps its original as the
baseline, every later write refreshes *mine*. It never raises, it records only
files under `<Medieval II>/mods/<mod>/data/`, and a file over 64 MB is skipped.
Undo restores files without a write helper, so `transfer.undo` tells the set
directly.

**Mine is kept too, not only the baseline.** The scoping had the change list as
baseline against the current file. That is wrong in exactly the case the
feature is for: once an update has overwritten the mod, the current file is
*theirs*, and your version exists nowhere. So the set keeps both copies, and
the screen says when the disk has moved under them ("changed on disk since your
last save here"), which is how an update announces itself.

**Records touching counts as a conflict.** The first merge let an insert
directly under a line the other side rewrote merge cleanly, which in an EDB is
a pool added under a pool upstream re-tuned: related edits, silently combined.
Neighbouring lines now conflict, git's rule for the same reason, and the test
fixture was moved so its "merges" case has a line between the two edits.

**Undoing a port must put the set back.** A port onto the same mod moves the
set's baseline to the version ported onto, which is what the next update must
be compared against. Undoing it first re-read the files, which left baseline
and mine both saying the new version: every edit forgotten. The port now copies
the set beside its backups and `changesets.undone` restores it, so an undone
port can be ported again.

### What shipped

- **Recording, with nothing to switch on.** Every save to a mod from any
  screen, baseline and mine under `config/changesets/<mod>/`, outside the mod.
- **The change list**, record by record: an EDU unit by `type`, an EDB building
  by name, a region by name, a text key by key; any other file as one record,
  line by line; a binary file whole. Each file says whether the disk still
  matches your last save.
- **Port**, onto the same mod as it is now or onto another installed folder,
  from this mod's set or an imported one: each record `clean`, `already`,
  `merged` (both sides, lines apart), `conflict` or `gone`, with the original,
  yours and the new version side by side, and a `dangling` warning on a
  recruit pool naming a unit the resulting EDU does not have. Clean and merged
  start ticked, conflicts and removals start unticked. A new record goes where
  it sits in yours. One backup, one log entry (`🔀 My changes` in the Log),
  one Undo.
- **Export and import** as one `.m2changes` file (a zip of the set). An
  imported set is never trusted to stay inside `data/`: every path is checked.
- **Take the files on disk as mine** for hand edits made outside the toolkit,
  and **Forget this record**, both behind a confirmation that says when not to.

### What is not in it

`descr_strat.txt`, the modeldb and the EOP files have no record shape here yet,
so each is one record: a port of them is clean, already, merged by lines or a
conflict, never per character or per entry. The dangling check covers recruit
pools against the EDU and nothing else. Neither was measured against a real
AGO or EUR update, because only one version of each installed mod is on this
machine; the fixture is a synthetic update in both tests and the demo.

### The scoping, as written before it was built

**The problem, as the feedback put it:** edits made to AGO are lost when the
next AGO release overwrites the files, and big mods like AGO or EUR cannot
simply be copied into a new mod folder to keep them. Old edits also collide
with how a new release is organised, for example units the new version adds to
EOP recruitment from the EDU. He asked whether it could be done without a
duplicate, and suggested a file listing every change that can be exported and
**ported** onto another version of the same mod, with a checklist of what to
port and warnings where a unit was removed, a record was edited upstream too,
or a building or region no longer exists.

**Settled with the user: this phase records and ports, switching in place is
Phase 53.**

**No duplicate: the baseline is only the files the toolkit touched.** Every
write already goes through a `backup_and(rel)` that copies a file before its
first change (`edit.py`, `transfer.py`, `bmdb.py`, `stratmap.py`, `cards.py`).
A change set keeps the **first** of those copies, per mod, outside the mod
folder, so an update that overwrites the mod cannot overwrite the baseline.
That is a few files out of thousands, not a copy of the mod.

**The change list is derived, not logged.** Diffing the baseline against the
current file, record by record, with the parsers the toolkit already has (EDU
by `type`, EDB by building, level and capability, `descr_regions` by region,
`descr_strat` by faction, settlement and character, EOP recruitment, strings by
key, modeldb by entry), means an edit made by hand outside the toolkit is in
the set too, and nothing depends on a log that could miss a write. A file with
no record parser falls back to a line diff and says so.

**Export is one file**: the list, plus each changed record's before and after,
so it can be ported from another machine.

**Port is a three-way merge by record**: the baseline (old version, untouched),
mine (old version, edited) and theirs (the new version). Each change comes out
as one of:

- **clean**: theirs still equals the baseline, so mine applies as it is
- **already there**: theirs already equals mine
- **changed upstream too**: both sides changed the same record; show all three
  and let the user pick, never merge fields silently
- **gone upstream**: the unit, building, level or region no longer exists
- **dangling**: mine applies, but names something the new version dropped (a
  recruit pool for a unit no longer in the EDU, a region's hidden resource
  nobody declares)

The user ticks what to port, the writes go through backup and undo like every
other write, the existing validators (`mapcheck`, `tree_check`, the unit
reference checks) run on the result, and the new version's files become the
set's new baseline.

**What to measure first.** Only one version of each installed mod is on this
machine, so the session builds its test fixture from an installed mod plus a
synthetic upstream (records removed, reordered, edited on both sides, EOP
recruitment added) before any UI. If AGO or EUR can be installed in two
versions, that is the real test and it goes in `tests/`.

**Exit:** a change set per mod with a baseline of touched files only; the
derived record-level change list; export and import of one file; port with the
five outcomes, a checklist, and backup and undo; the validators run after a
port; tests over the synthetic upstream for every outcome.

## Phase 53 - Change sets, switched in place - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** *Versions of this mod* on
the My changes screen, `plan_switch` / `apply_switch` in `changesets.py`, and
20 more checks in `tests/test_changesets.py` (section 7).

**Turning a set off is not "write the baseline back".** That was the scoping's
sentence, and it is right only while the disk still says exactly what the set
last wrote. After any other change - an update, a hand edit - writing the
baseline back would throw that change away with yours. So off is the port run
backwards: yours as the base, the original as the change, the disk as theirs,
record by record. On is an ordinary port of the set onto what that leaves. A
switch between two sets is both, as one job.

**A switch is mechanical or it does not happen.** A port can stop and ask; a
switch is a button, so any record that comes out `conflict` or `gone` in
either half refuses the whole switch, and the refusal names the set, the file,
the record and the outcome. The way through is a port, which is the screen that
asks. On a mod an update has overwritten, that is exactly what should happen.

**What a set is, now.** A mod carries any number of sets; one is on (its
records are what the files say), and the rest hold both their copies, ready to
go back in. The recording hook writes into the ON set. With every set off, the
next save starts a new one, whose original is the mod as it shipped, so "the
vanilla mod plus a second set of edits" is just what turning the first off and
saving leaves. A set predating this phase counts as on; an imported set is off
until switched on here. Sets can be renamed.

**A switch's own writes are not recorded.** They go through the same helpers
as every write and would otherwise land in the set as fresh edits,
overwriting the copy being switched to. `_quiet` holds the hook off while a
switch writes; the set switched on is then rebased onto what it was put into,
as a port rebases. Undo restores every set the switch touched as well as the
files.

**The unsaved-edits refusal is the page's**, because only the page knows about
them: `chgUnsaved` asks Buildings, the unit editor and its tabs, the two
campaign panels, and every screen that keeps a `dirty` flag.

### The scoping, as written before it was built

The other half of the feedback: *instantly revert back to the vanilla mod* and
keep several versions of the same mod to test. Once 52 has a baseline and a
derived change list, turning a set **off** is writing the baseline records
back, and turning it **on** is 52's port onto the mod's own current files.
Several named sets per mod, one active at a time, and the switch refused while
the toolkit has unsaved edits open. Written up now so 52 is built with it in
mind; scoped properly when 52 is done.

---
# Phases 44-48 - the pass over his non-map screens, 2026-09-13

**Asked for by the user on 2026-09-13**, in seven parts: his validation and
where it sits, his hidden-resource editor, whether our traits and ancillaries
are still level with his, his map side panel and paint mode and tooltip, his
cultures and factions panels, his strings editor, and his sound files.

**Two of the seven produced no phase, and both for a reason worth keeping.**
Traits and ancillaries have not moved on his side since March; the strings
codec is wrong in his tool and right in ours. Both are written up under *The
2026-09-13 pass, and the two parts of it that produced a measurement* below.
The map side panel is **28a and 28b**, because that is the phase already going
to touch the screen. The remaining four are here.

**These four are outside both blocks.** The locked order is the campaign map,
then the mercenaries, and nothing here is either: 44, 45 and 48 are the
Buildings and Strings modules, 46 is Minor Files and Factions, 47 is a file
family nothing in the toolkit opens. They are written up rather than rated
because the user named them, and they sit after block two until the user says
otherwise. All of them are **subreleases on both lines** - none touches the
campaign map, so none is beta-only.

| Order | Phase | Size | Line | Why |
|---|---|---|---|---|
| ~~21~~ | ~~**44** The EDB's tree, checked~~ | M | **both** | **done 2026-09-20** |
| ~~25~~ | ~~**45** The hidden resources line~~ | S | **both** | **done 2026-09-21** |
| ~~26~~ | ~~**46** Cultures gets a screen, and two forms get a strip~~ | M | **both** | **done 2026-09-21** |
| ~~27~~ | ~~**47a** The six export sound files~~ | M | **both** | **done 2026-09-21** |
| ~~28~~ | ~~**47b** The thirty-two sound scripts~~ | L | **both** | **done 2026-09-21** |
| ~~29~~ | ~~**48** The two rows the strings screen cannot add~~ | S | **both** | **done 2026-09-21** |

**Renumbered 2026-09-21:** Phases 51, 52 and 53 took orders 22 to 24 ahead of
these, on the user's word. Their table is under *Phases 51-53*.

## Phase 44 - The EDB's tree, checked - DONE 2026-09-20

**Nine rules ship, three are refused, and the refusals are the phase.** The
scoping said six go in as stated and four get measured first. What measuring
found is that **one of the six could not go in as stated either**, and that is
the result worth having: his validator, run over the two installed mods as
written, would report 42 lines as broken that are working exactly as their
authors meant.

### What the measurement said

Run over Divide and Conquer (136 lines, 499 levels) and ROCSS (107 lines, 290
levels), 789 levels in all:

| his rule | measured | shipped as |
|---|---|---|
| duplicate building name | 0 | `tree.name_twice`, fatal |
| a line with no levels | 0 | `tree.no_levels`, fatal |
| an `upgrades` entry naming nothing | 0 | `tree.upgrade_unknown`, fatal |
| a `convert_to` naming nothing | 0 | `tree.convert_unknown`, fatal |
| a `building_present_min_level` naming nothing | 0 of **336** references | `tree.min_level_unknown`, fatal |
| **a level no `upgrades` entry reaches** | **42 lines** | **reshaped** - see below |
| a level with `cost 0` | 4 (1.4%) | `tree.free_level`, warn |
| a level with `construction 0` | 1 (0.3%) | `tree.instant_level`, warn |
| a level with no `factions` clause | 0 | `tree.no_factions`, warn |
| a line with more than 9 levels | **2, on a mod that plays** | **refused** |
| a line approaching 50 levels | nothing to measure | **refused** |

**The five reference rules find nothing on either installed mod, and that is
what they are for.** Phase 31's river rules set the precedent: a rule that
finds nothing on five real maps is not a wasted rule, it is a rule that has
been checked against reality and passed. The 336 `building_present_min_level`
references all resolving - both the line they name and the level on it - is the
single most reassuring number in this phase, because that is the one condition
in the EDB that can dangle twice.

### The rule that could not be stated his way

"A level no `upgrades` entry reaches is unreachable" assumes every building
line is a chain. **Forty-two are not.** Eighteen lines on DaC and twenty-four
on ROCSS have no `upgrades` entries anywhere in them: their levels are
**alternatives**, picked by `hidden_resource`, and "reachable" means nothing on
such a line. `hinterland_enedwaith_clan_halls` is nine mutually exclusive clan
halls; `mumakil`, `mithril_mines` and `trade_centre` are the same shape.

Excluding those leaves **three real chains on Divide and Conquer with a second
entry point** - `hinterland_unique2` (`hornburg` climbs to `wulf_hall_edoras`,
and `gilraen` starts a second chain to `teeth`), `hinterland_tharbad_bridge`
and `hinterland_palantir`. DaC ships and plays. So it is not an error either.

It ships as **`tree.second_entry`, at `note`**, excluding alternative-lines
entirely: worth saying, because a second way into a chain is usually not what
somebody drawing one meant, and not worth calling wrong.

### The two ceilings, refused, on Phase 12's own ruling

His "the vanilla limit is 9 levels" would fire on `hinterland_unique1` (13
levels) and `hinterland_unique2` (12) - **on a mod that runs**. A ceiling a
shipping mod is over is not a ceiling. His "approaching the M2TWEOP limit of
50" has nothing to check itself against: the largest line on either installed
mod is 13, so the rule has never seen its own subject.

This is Phase 12's ruling applied again, and it is worth writing down twice
because it keeps coming up: **a count from a wiki is not a fact about a mod.**
12 kept `guild_` at three levels as a hint because 19 of 19 real guild lines
have exactly three, and refused "the engine refuses a fourth" because that is a
different claim with no measurement behind it. Both refusals are in
`buildings.RULES_REFUSED`, in the module rather than only here, because the
next person to read his validator will find them in it and wonder why we do
not have them. They travel out to the panel too, under *The 9 rules, and the
three that are deliberately not here*.

### The shape, and why it is `mapcheck.py`'s

A code, a label, a severity, a **source** naming who says it is a rule, and a
function yielding findings. Copied down to the decorator, because M17 - the
five-star dashboard that is the complaint that we have more validators than any
reference tool and no single door to them - is only cheap if the validators
already agree about what a finding is. `EdbFinding.what` never carries a line
number, for `mapcheck.Finding`'s reason: adding a building at the top of the
file must not make every finding below it a different finding.

**One request, not two.** The tree findings ride in the answer
`/api/buildings/checks` already gives, because the screen asks that question
once per mod and once per line; a route of its own would have been a second
request on both paths and the two halves of "what is wrong with this EDB" would
have arrived at different times. On the mod's screen it is a shut button that
fetches on first open - most visits are to look at a building, not to audit
one - and every finding row opens the building it is about.

### Two defects found while building it, both mine

`TREE_REFUSED` already existed in `buildings.py` - the new-tree form's
"what this module will not do to a whole line" - and the new constant shadowed
it, which took `overview()` down with a `ValueError` on every buildings screen.
Renamed to `RULES_REFUSED`. And `bldTreeToggle` already existed in
`buildings.js`, folding a row open in the tree browser; the new one silently
replaced it. **`test_web_modules` caught the second one and the first suite run
caught the first**, which is the whole argument for both of those tests
existing in a project with one global JS scope and a 3,000-line module.

Exit: nine rules in `buildings.py` on the `@rule` shape with a source each,
`tree_check(edb, line="")`, `RULES_REFUSED`, the findings on both the mod's
screen and each building's, and `tests/test_buildings.py` section 12 - a
fixture per rule, plus 12b running all nine over every installed EDB and
asserting a shipping mod has no fatal.

## Phase 44 - the scoping it was built from

**Our EDB checks are about recruitment and nothing else.**
`buildings.line_checks` finds three things per building line: a unit that stops
being recruitable further up the chain, the same unit twice in one level, and a
divergence between a line and its city/castle twin. That is the half of the
file the unit editor cares about. Nothing checks the **tree**: that a building
name is unique, that a line has levels at all, that each level is reachable
from the one below it, that an `upgrades` entry names a level that exists, that
`convert_to` names a building that exists, that a
`requires building_present_min_level` names a level that exists.

**He has both halves of that and we have neither.** `edb/EDBValidator.jsx` is
fifteen messages over the parsed tree and `export/ModValidator.jsx` is ten more
of the same shape; together they are the one place in his tool that does
something ours does not, which is the opposite of the finding every other audit
of his has produced.

**Six rules go in as stated, because each one is a reference that either
resolves or does not.** Duplicate building name, a line with no levels, a level
no `upgrades` entry reaches, an `upgrades` entry naming nothing, a `convert_to`
naming nothing, a `building_present_min_level` naming nothing. Phase 12 already
measured the ground under three of them: **all 601 current upgrade entries
point forward at a level on their own line**, none backwards, none at itself,
and `test_edb_tree` asserts `upgrade_name()` against every one. So the data a
finding needs is computed already, and what is missing is the finding.

**Four of his rules are measured first and probably do not ship as errors.**
A level with `cost 0`, a level with `construction 0`, a level with no
`factions` clause, and his three level-count ceilings. The rule this file keeps
making is that a count from a wiki is not a fact about a mod: Phase 12 kept
`guild_` at three levels as a hint because **19 of 19 real guild lines have
exactly three**, and refused "the engine refuses a fourth" because that is a
different claim. His "vanilla limit is 9" and "approaching the M2TWEOP limit at
50" are the same shape. Measure all four across the four installed mods first;
a rule that fires on a quarter of a shipped file is noise, and this validator
has a baseline for the findings that are somebody else's.

**It goes where the other checks go, not into a second engine.** `mapcheck.py`
is the model down to the decorator: a `@rule` with a code, a label, a severity
and a sentence, and a panel that lists what came back and offers a jump. The
Buildings module already has the Code View to jump into. No rule is written
twice in the browser.

**And it is the first half of M17.** The five-star *crash and validation
dashboard* is the complaint that we have more validators than any of the four
reference tools and no single door to them. This adds one more validator; it
also makes the EDB's entry in that door a real one rather than a recruitment
rollup.

Exit: six rules over the tree, four measured and then decided, in
`buildings.py` on the `@rule` shape, on the Buildings screen with a jump into
Code View, and a fixture per rule in `tests/test_buildings.py`.

## Phase 45 - The hidden resources line - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut. The scoping held.** A
**◈ Hidden resources** panel beside *Check the tree* on the Buildings screen,
`buildings.plan_hidden` / `hidden_impact` / `hidden_usage`, a route pair
`/api/buildings/hidden/plan|apply`, and section 14 of `tests/test_buildings.py`.

**What a removal shows is measured, not estimated.** On Divide and Conquer,
taking `Rhudaur` off names its 4 provinces and 162 clause lines; the busiest
name, `Eregion`, is carried by 10 provinces and gated on by **636 lines**. The
test asserts the impact list, the per-name count and a raw scan of the file
agree. A clause is counted by line, because a line naming the resource twice is
still one gate. The clauses come from the parse (a level's own `requires`,
every capability and faction_capability) and then a scan of every other line,
so a clause somewhere the parser does not model is still named.

**The ceiling, with the corrected number.** The scoping said Divide and
Conquer ships 74; it ships **75**, all unique, and ROCSS 74. The panel states
the count, TWCenter's 63-or-64, and that both mods pass it, and a line over 64
carries a warning on the plan. Nothing is refused for it.

**The write is the one line.** The keyword's own indent and gap (DaC writes
two spaces), the separator between names and a trailing comment all survive;
the test checks that every other line of the file is byte-identical and that
Undo restores it exactly. A name must be one word of letters, digits and
underscores, as all 149 on the two installed lines are, and a duplicate is
refused whatever its case. An EDB with no line gets one above the first
building.

### The scoping, as written before it was built

**We read the line and nothing writes it.** `buildings.py` holds
`hidden_resources` and `hidden_resources_line`, and `hidden_resources_line` has
exactly one reference in the whole tree: the assignment that sets it. The list
is already read four ways round - the `requires hidden_resource` clause
picker's vocabulary, `edbvocab.regions`, the province panel's resource chips on
the campaign map, and a `mapquery` fact - and a name can be added to none of
them.

**Phase 12 refused his editor and said what would make it worth having.**
`HiddenResourceEditor.jsx` is add and remove with no check either way, and a
hidden resource is named in two other places: `descr_regions.txt` says which
province carries it, and `requires hidden_resource X` clauses throughout the
EDB say what it gates. Removing one breaks both in silence, which is the
hardest kind of EDB bug to see, because the building simply never becomes
available.

**The check that refusal asked for is already computed.** `edbvocab` builds the
region rows per hidden resource, and the clause picker already has a *where
does this bite* panel over them. So a removal can name every province that
carries the resource and every clause that gates on it before it happens, which
is the whole difference between his feature and one worth shipping.

**The ceiling is reported with both numbers, and neither as a refusal.**
TWCenter's *List of Hardcoded Limits* puts it at 63 or 64 and says extras
crash; **Divide and Conquer ships 74**. Phase 12 deferred the feature partly on
that, because warning about a limit three of three mods disprove is worse than
saying nothing. The panel says the count, says what the note claims, and says
that the installed mods pass it. It does not stop a save.

**The write is one line.** A splice at `hidden_resources_line`, the way every
other write in this module is a splice, so the 7,203 comment lines in the three
EDBs stay where they are.

Exit: add and remove on the `hidden_resources` line; a removal naming every
province and every clause it would darken, and refused until that is
acknowledged; the count and the two ceiling claims stated; backup and undo like
every other write; `tests/test_buildings.py` asserting that everything outside
the line round-trips byte for byte. This closes the hidden-resource half of the
four-star *Mines and hidden resources* row, which keeps
`descr_settlement_mechanics.xml`.

## Phase 46 - Cultures gets a screen, and two record forms get a strip - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** All four parts shipped as
scoped, and one sentence of the scoping was wrong about the files.

**The culture's text keys are not "the {CULTURE} key and three
EMT_<CULTURE>_PRIEST keys".** Measured in the two installed mods'
`text/expanded.txt`: every culture has its `{CULTURE}` key and **between one
and five** `EMT_<CULTURE>_PRIEST` keys, the suffixed ones being the priest's
ranks (ROCSS's eastern European has `_1` to `_4`: Bishop, Cardinal, Patriarch,
High Priest). And the `EMT_*_PRIEST` keys that are most common are named after
**factions** (`EMT_VENICE_PRIEST`), which override the culture's where they
exist. So a duplicate lists the keys the SOURCE culture actually has, each with
the new name and the source's text beside it, rather than a fixed four.

**What shipped:**

- **Cultures is a mode.** A `sub:true` entry in `MODES` and a `{mode:...}` row
  in `MINOR_TABS`, like Traits and Guilds. It is still the Minor Files screen
  underneath, locked to the cultures tab - `renderCultures` and a `mfMode()`
  that every "is this screen still up" check asks - so the list, the pane, the
  code view and the save are the ones that were already tested.
- **Four tabs**: General, Settlements, Infrastructure, Agents, drawn by one
  shared `recTabsHtml`. **The port ladder is editable** on Infrastructure,
  value by value in the file's order, which `render_culture` now writes one
  splice per line; the ladder's shape (how many levels) stays in the code view
  and the form says so, because a level is a pair of lines placed in the file's
  order.
- **Duplicate a culture**: action `duplicate`, the source's whole record -
  brace, tail and agents - under a new name, inserted after the last culture
  (one insertion; a trailing banner stays last). The preview names what it
  still needs and does not write: the text keys above, the factions on the
  source that could move onto it (a culture no faction names is used by
  nobody), and that every model, card and agent picture still points at the
  source's files. A name must be lower case letters, digits and underscores,
  because it becomes a text key and a folder name.
- **The faction form on five tabs**: General, Art and banners, What it can do,
  Movies, Horde - the sections it already had, no parser work.

Neither of the two things the scoping refused was taken: no `descr_offmap_models`
generation (no installed mod has an `offmap` line), and no claim about how many
cultures the engine allows. Promoting Factions and the other sub modes to the
burger menu is still the user's call.

### The scoping, as written before it was built

**The parser is not the gap.** `minorfiles.parse_cultures` already reads
everything his `culturesParser.jsx` reads and two things it does not: the
settlement plan beside the model and the card on every level, and the port
ladder in the file's own order rather than as three fixed slots. Phase 10a took
his `SETTLEMENT_TYPES` and `AGENT_TYPES` and his reading of the agent line as
seven columns, all three measured correct, and refused his record split (he
splits the file on `;;;;` banner lines, which merges two cultures on a file
that has none) and his `offmapSettlement` / `offmapPort` defaults, which are
invented vanilla paths never parsed from the file and written on every save.

**The gap is the screen, and it is three things.**

**One: cultures leaves the strip for a mode of its own.** Traits, Ancillaries,
Guilds, Factions and Strings each have a `sub:true` entry in `MODES` and a
`{mode:...}` row in `MINOR_TABS`, so their tab in the Minor Files strip
switches mode rather than tab. Cultures is the one `{id:'cultures'}` row left
that does not. Phase 10a made it a tab on the ground that `descr_cultures.txt`
is "the same size of job" as rebels and religions; that stops being true the
moment the form has four sections, which is what the rest of this phase does.
Two lines in `core.js`, and a `loadCultures` that is `mfCultureForm` moved.

**Two: the form gets the strip every other record form here has.** General,
Settlements, Infrastructure, Agents. Ours is one scrolling form of three
sections, and the ports are pushed into Code View with a note saying why:
`port_land` and `port_sea` are a pair of lines per level, which is a section
rather than a field, and a section is exactly what a tab is for. Infrastructure
is where the fort, `fort_cost`, `fort_wall`, the fishing village, the three
port levels and the watchtower go, and it is the tab that makes the port ladder
editable at last.

**Three: add a culture, by duplicating the one on screen.** His
`handleAddCulture` deep-copies, renames and stops. Ours writes the record and
then says what else a culture needs, because we can name it: the `{CULTURE}`
key and the three `EMT_<CULTURE>_PRIEST` keys in the compiled text archive,
which Phase 6 already writes; the factions in `descr_sm_factions.txt` that have
to be moved onto it; and the settlement and agent art, which the form already
shows and already says when it is missing. `factionclone.py` is the shape of a
record that arrives in more than one file.

**The faction form gets the same strip, and that is the whole of its half.**
`facFormHtml` is one long form too, with its sections already separated: the
record, the pictures, the movies, the horde, the findings. His `FactionsEditor`
is five tabs over the same ground. Same widget, same argument, no parser work,
so it belongs in this session rather than a fifth of its own. **Factions is
already its own mode** and has been since Phase 11, reached from the strip the
way Traits and Guilds are; what it is not is an entry in the burger menu, and
neither are Traits, Ancillaries, Guilds or Strings. Promoting any of them is
one decision about all five and it is the user's, not this phase's.

**Two things are not taken.** His Extras tab generates
`descr_offmap_models.txt` blocks out of the invented defaults above, and **no
installed mod has an `offmap` line at all**; that file is a three-star row of
its own and it will be parsed before it is written. And his note that the
engine allows one new culture beyond vanilla's seven is an engine claim with no
measurement here, so it goes to Phase 39 with the other ceilings or it is not
said.

Exit: cultures as a mode with a four-tab form, the port ladder editable,
duplicate-a-culture writing the record and naming the four keys and the faction
moves that go with it, the faction form on the same strip, and
`tests/test_minorfiles.py` holding the byte-exact round trip it already holds.

## Phase 47 - The sound scripts, which nothing here opens

**Measured on the four installed mods, 2026-09-13.** Divide and Conquer ships
**40 sound script files and 120,981 lines**; Third Age Reforged 40 and 117,194;
Vanilla Redux 39 and 92,473; `vanilla_kingdoms_uncompromised` 40 and 131,200.
They split three ways: **32** `descr_sounds_*.txt`, one `descr_sounds_db.xml`,
and **seven** `export_descr_sounds_*.txt`. Every one of them is in `data/`, and
all of them are plain text with CRLF. Nothing here opens any of them except
`export_descr_sounds_units_voice.txt`, which is `sounds.py`.

**His editor is not a port, and Phase 13 measured why.** His
`KNOWN_SOUND_FILES` names fourteen files in `data/sounds/`; **four of the
fourteen exist** (`_music`, `_units`, `_units_voice`, `_weapons`) and they are
in `data/`, while the other ten are RTW-era or invented. Run over Divide and
Conquer's 32 his parser round-trips **0 of 32** and loses 2,975 lines, because
it takes any column-0 line without a space in it as a block label; in
`descr_sounds_weapons.txt`, 3,855 lines, the only block it finds is the word
`end`. The one thing worth carrying from that screen is its empty state, which
says where the base sound files are, because M2TW ships them packed.

**Two grammars, so two sessions.**

### 47a - The six export files, on a parser we already have - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** A screen of its own,
**Sound banks**, beside Unit Sounds on one strip, over a new
`unittransfer/soundbanks.py`. Measured again before a line was written, and
the scoping was wrong about the parser.

**`sounds.py` does not already read these, and cannot be taught to.** Three
things in the six files break its grammar, all measured on both installed
mods:

- **Indentation says nothing.** `_prebattle` mixes tabs and runs of spaces in
  one block, and a `pri 9` sits deeper than the `VnV` it belongs to. So a
  header's depth comes from its keyword, per file, from a table:
  `accent > class > vocal` (soldier voices), `accent > type > vocal` (strat
  map), `accent > notification` (battle events), `accent > element > relationship
  | trait | condition | situation | pri` (pre-battle), `text` (advice), and none
  at all for narration, whose `event <NAME>` lines stand at the top.
- **`VnV` is not a level.** It is a line of its own that qualifies the `trait`
  or `pri` under it, so it is carried as the first line of that block, and a
  copy takes it along.
- **Attributes are on more than the event line.** `_soldier_voice`'s events
  carry `mindist 0.75 priority 120 volume -10 probability .4` and
  `_stratmap_voice`'s `delay 0 pref SFX`, and a sample line can carry its own
  (`willhelm.wav probability .001`). So a body line is text, never split into
  a path.

It is still a splice over verbatim lines, `sounds.py`'s own rule. **All twelve
files (six banks on two mods) come back byte for byte, every event lands in a
block, and not one warning is raised**; DaC's `_narration` is three comment
lines and ROCSS's `_advice` one entry, and both read.

**What shipped:**

- The six banks on tabs, each a tree of its blocks on the left, folded by
  default (DaC's strat map voices are 2,570 blocks). Search reaches block
  names and sample lines.
- A block's events on the right: the attributes on a line, the folder and
  sample lines in a box. A line that did not change keeps its bytes; a new one
  takes the indent of its kind's first line in that event, so a block keeps
  whatever mix of tabs and spaces it had.
- **Duplicate as…**, **Rename…** and **Remove** on any block, an accent
  included: duplicating DaC's `accent Arabic` in the strat map bank is one
  insertion of 1,619 lines and nothing else changed. A new accent is said to be
  used by nothing until something names it.
- Refused: a copy under its own name or one already beside it, an event whose
  first line is not a folder, an `end` or `event` line inside an event, a
  narration name that is not letters, digits and underscores, and any op whose
  line no longer says what it said when read. An attribute no event in any of
  the mod's six banks uses is a warning, not a refusal.
- One backup and 🕑 Log undo per save, mode `soundbanks`. The `units_voice`
  bank stays in Unit Sounds and `factionclone.py` keeps writing `_prebattle`.

**Not taken:** checking that a sample exists. The base game's sounds are packed
(`data/sounds/*.idx` and `*.dat`), so the screen says where they are and does
not pretend to know.

#### The scoping, as written before it was built

`export_descr_sounds_*.txt` is the indented `BANK:` / `accent` / `class` or
`type` / `vocal` / `event` … `end` / `folder` tree that `sounds.py` already
reads verbatim and splices. Six more files take it:
`export_descr_sounds_soldier_voice.txt` (16,144 lines in DaC),
`_stratmap_voice.txt` (16,155), `_units_battle_events.txt` (7,328),
`_prebattle.txt` (8,400), `_advice.txt` (3,980) and `_narration.txt` (3). Two
differences from the voice bank have to be read before anything is written:
`_stratmap_voice` keys on `type Admiral` where the voice bank keys on
`class General`, and an `event` line there can carry attributes
(`mindist 0.75 priority 120 volume -20 probability .4`) that the voice bank's
never does.

**This is the three-star *three voice files* row, and it is cheaper than it was
rated.** That row was an L on the size of the files alone. The parser exists,
the splice exists, and `export_descr_sounds_prebattle.txt` is already written
by `factionclone.py` as a per-faction block, so this is a session and a bit
rather than more than one.

### 47b - The thirty-two scripts, on a grammar nothing here has read - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** A third tab on the sound
strip, **Sound scripts**, over a new `unittransfer/soundscripts.py`, drawn by
the same list and pane as 47a's banks.

**Measured before it was written** (both installed mods, 52,091 lines): 31
scripts in `data/` on each and `descr_sounds_music_types.txt` beside them;
4,239 events, 980 of them named. A script is five kinds of line, and the
parser tells them apart by their first word and nothing else: `DEFAULT:`,
`BANK:`, `source`, a **setting** (a key and only numbers: `grid_cell_size 40`,
`river_max_dist_apart 250 ; comment`), and a **selector** (about forty
keywords: `unit`, `hit`, `season`, `terrain`, `climates`, `type`, `state`,
`looped`, `arrived` ...), with `event [NAME] attrs` … `end` blocks under them.
An event's first word is its name unless it is a number or an attribute.
**All 64 files (32 on each mod) come back byte for byte, every event is in a
block, and not one warning is raised.**

**The arguments are typed, and the types are measured rather than guessed.**
An attribute is a number key (twenty of them: `volume`, `mindist`, `lod`,
`priority` ...), a flag (`1d`, `2d`, `3d`, `streamed`, `looped`, `ducking`) or
`pref` and a word, and those lists are every one the two mods write. A number
key with no number after it is refused; an attribute no script writes, a
`pref` the mod does not use, and a selector value no script in the mod names
are warnings. The pane lists each number key with the range this mod's
scripts already use (volume -80 to 0 on both), said to be usage and not a
limit. `factions` in `descr_sounds_accents.txt` is checked against the mod's
factions, and a faction put under a second accent is named.

**What shipped:** every event's attributes and samples; every `DEFAULT:` line
and setting, a trailing comment kept (`_with_value` in 47a's module keeps
comments now, for both); a selector's values changed in place; a named event
copied under a new name, renamed or removed, each saying that the engine or a
script plays it by name. One backup and 🕑 Log undo per save, mode
`soundscripts`.

**Not taken, and why.** **A selector's block is never copied or removed.**
Selectors nest by indentation and these files keep to it only as a habit:
`looped` sits a tab shallower than the event it wraps, and a setting can sit
level with the selector above it. The tree drawn from indentation is right
for showing where an event is and not certain enough to cut by, so the edits
are all to lines whose extent is certain (one line, or `event` to `end`) and
the screen says so beside the button that is not there. **A bank is not
renamed**: the engine asks for it by name. **`descr_sounds_music_types.txt` is
shown, not edited**: it is written from the campaign map a province at a time,
and 19b renames through it. The four faction-clone sites keep their writers.

The exit named `tests/test_sounds.py`; the round trip is in a suite of its own,
`tests/test_soundscripts.py`, because `test_sounds` is pinned to Third Age
Reforged and fails without it.

#### The scoping, as written before it was built

`descr_sounds_*.txt` is a different shape: `DEFAULT:` directives with key and
value attributes, named `event` blocks, `BANK:` sections, `unit <name>:<type>`
selectors, `hit <type>` conditionals, and `folder` lines with samples under
them. It is a grammar of its own and it deserves what Phase 7 gave triggers,
which is a vocabulary and typed arguments, not a raw-line box. Phase 13
recorded that and did not schedule it; this is the schedule.

**Four of the thirty-two already have writers and keep them.**
`descr_sounds_accents.txt` and `descr_sounds_music.txt` are faction-clone
sites, `export_descr_sounds_prebattle.txt` is another, and
`world/maps/base/descr_sounds_music_types.txt` is the campaign map's music type
and one of 19b's rename sites. Those writers stay where they are; this phase
reads the family and adds an editor beside them, it does not take them over.

Exit for both: every file read and re-rendered byte for byte on all four
installed mods, an editor over the blocks rather than the lines, backup and
undo as everywhere else, and `tests/test_sounds.py` extended with the round
trip per file.

## Phase 48 - The two rows the strings screen cannot add - DONE 2026-09-21

**Done 2026-09-21, both lines, committed and uncut.** The last of the
2026-09-13 pass. As scoped, and one refusal added after measuring.

- **＋ New entry** on a tagged archive puts a tag box and a text box at the top
  of the table; several can be staged at once. **✕** on a row stages its
  removal, struck through and undoable with ↺. Both go in the one save with
  the edits, through the `adds` and `removes` the plan has taken since Phase 6,
  and Ctrl+Z covers all three.
- **Where the count changes, the page says so:** "10 entries now, 11 after
  saving", with the trailing tag index named beside it when there is one, and
  the plan's own warning repeated in the confirmation.
- **An archive addressed by position** (battle, shared, strat, tooltips) says
  why it takes neither, in the backend's two sentences. They are constants in
  `strings.py` now, `NO_ADD` and `NO_REMOVE`, sent on the entries payload as
  `refused` so the page shows what the plan would say without a copy of it.
- **Added: a new tag with a space or a brace is refused.** Measured over all
  36,219 tags in the installed mods' archives: not one has either, and a brace
  would break the `{tag}text` line of the `.txt` beside the archive. The page
  paints the box red early; the plan is what refuses.
- After a save the screen reopens the archive that was saved rather than the
  list.

`tests/test_strings.py` drives the page's calls through the HTTP layer: the
refusals as served, an add and a remove planned, applied, served back and
undone byte for byte, each bad tag refused, and both refusals on an archive
addressed by position with nothing written.

### The scoping, as written before it was built

**The backend already does it and the screen does not ask.** `strings.plan`
takes `{edits, adds, removes}` and has since Phase 6, with both refusals
already written: an untagged archive cannot take an add ("this archive's
entries have no tags - nothing to add") and cannot take a remove ("removing one
would renumber every entry after it"). `web/js/strings.js` posts `edits` and
nothing else. So a key can be changed and never created or deleted, from a
screen whose whole subject is the keys.

**That is the one thing his `StringsBinEditor` does that ours does not**, and
it is an afternoon: a new-row form on the list, a remove on a row, and the
plan's own warning about the trailing tag index being carried through unchanged
shown where the count changes.

**His reorder is not taken.** `move up` and `move down` on an entry: a tagged
`.strings.bin` stores its entries sorted and the game addresses them by tag, so
there is no order to edit; an untagged one addresses by position, where a move
renumbers every row after it, which is the reason our backend already refuses
the remove on those four archives.

**And the codec is not a port in either direction.** `stringsbin.py` records
two faults in his that cost real files, both confirmed byte for byte against
all 81 archives the test mods ship: he reads `count` as a `u16` plus a padding
word where it is a `u32`, which reads half of any file past 65,536 entries and
Third Age's `names.txt` already carries 20,757; and he writes a single zero
word where the trailing tag index goes, which truncates a file that has one,
and Third Age's `export_buildings` has 480 entries and 13,482 index strings.
Worth passing back with the Phase 31 findings.

Exit: add and remove on the strings screen over the plan that already accepts
them, the two refusals surfaced as the sentences the backend already writes,
and `tests/test_strings.py` covering both through the HTTP layer.

## Phase 49 - Two strips, the colours on the left, and one place for models - DONE 2026-09-16

Asked for directly, with a screenshot of Mylae's map screen attached: `Strat` /
`Validate` / `3D` across the top, `Overview` / `Settlements` / `Factions` /
`Characters` under whichever of those is up, and a third row under that. *"This
looks way cleaner. Where each section when clicked shows the subsections below
and they can also be switched as needed."* Three more things came with it: a
toggle for the layer the brush is writing, the colours it can write on the left
of the map, and the Models Editor.

### The strip 28a built was half the shape

28a is what put the six tabs there, and its own note says why: sixteen panels in
one column meant the strat models sat four screens below the fold. It grouped
them - **six tabs over sixteen panels** - and then **stacked every panel of a
group down one scroll**, which is the same column laid on its side once a group
has seven of them. Province was `cmPick`, `cmRebels`, `cmSettle`, `cmChars`,
`cmForts`, `cmDel` and `cmRecolour`, one under the other.

So a tab is a **group of sub-tabs** and a sub-tab is what is shown, one at a
time. `CMAP_TABS` is two levels deep now and every reader goes through
`cmapTabPanels` (a group's panels, its subs' put end to end) or `cmapSubs`.
Nothing else changed about the DOM: **every panel of every group is still in the
DOM and still keeps its own state**, which is the property 28a's grouping was
built on and the reason moving to two levels cost the sixteen panel modules
nothing.

**Choosing a sub-tab presses the panel's own toggle.** Nine of these read
nothing until somebody clicks their own button, which was right when they were
stacked - a column of sixteen panels that each fetched on sight is a screen that
fetches sixteen times on load - and is wrong behind a tab: clicking `Forts` and
getting a button that says `Forts` is one click the screen owes you. `open: {fn,
at}` on the sub names the toggle and the key its module keeps `open` on, so it
is pressed **once and only when the panel is not already open**. Nothing is read
until the tab is *chosen*, which is the half of the old rule worth keeping - a
restored tab on load still opens closed, and the validator still does not run
itself.

The sub each group is on rides in `cmapLayerState` beside the tab 28a put there,
so it is in every named view for nothing and `cmapResetView` puts it back.
`cmapSurface` - the one thing that keeps the strip from being worse than the
stack - now names a group **and a sub**, because a click on a province that
fills `#cmPick` has to reach a panel that is hidden twice over.

### The colours are beside the tiles they go on

The palette was in the right-hand column behind the Paint tab. A palette is a
thing you reach for on **every stroke**, and that put it two clicks from the map
and took the column away from whatever else it was showing - the region record,
the validator - every time.

It is a column on the **other side of the stage** now, present only while the
brush is armed, holding the three things a stroke needs and nothing else: which
layer, which colour, and what is about to be written. It is wired by
`cpaintWireIn`, the same function that wires the panel and 28b's toolbar row, so
the same controls behave the same in all three and none of them knows where the
others put them.

**The layer is a toggle rather than a dropdown**, which is the user's second
request and is also the one control on this screen you could not read without
opening it: the thing a stroke was about to change was a word behind a click.
Eight buttons, one per paintable layer, and a layer the server could not read is
disabled with its reason on the title rather than left out.

### One editor for a mod's models

"BMDB + Sprites Editor" was already the wrong name for what its strip held -
model entries, sprites, **strat map** and unit cards - and it is **Models
Editor** now. Two things moved to make the name true.

**The strat map's entries get a 3D panel**, the BMDB browser's own: the same
split, the same saved width, the same detach-and-reattach so a keystroke in the
search box does not rebuild the canvas and refetch the mesh. A row's 🧊 draws the
`.CAS` that entry names - `entries` now carries `meshes`, the meshes the mod
**actually ships**, so a row with all of its files in a `.pack` gets no button
rather than a button that opens a 404. **206 of Divide and Conquer's 237 entries
have one.**

**And 16k's model browser came here from the campaign map.** It was a panel in
that screen's side column, where it edited nothing and sat beside nothing else
about models; the same list is now inside this panel, above the canvas. It is
the half that matters most, because **most of what the campaign map draws is in
no entry at all**: the game picks a settlement by level and culture out of
`data/models_strat` with nothing naming the file, which is why Amon Hen and
Minas Tirith are on the map and in `descr_model_strat.txt` nowhere. DaC declares
237 entries and ships **926 model files**.

Still one viewer on the page - `v3MountCas` drops whatever was showing - so this
panel and the BMDB one cannot both be drawing.

## M18 - The map in 3D - DONE 2026-09-20

Asked for directly, the day the contributor's campaign-map commit landed:
*"fully import the 3d map from mylaes tool and add it as a mode in the campaign
map view."* M18 was filed unrated on 2026-09-17 out of the `187d9ed..439aa9b`
review and was the largest of the four; the ask is what turned it into work,
and the "as a mode" in it is the whole of the design decision below.

### A mode, not a screen, and that is what made it small

His 3D is a second map. It carries its own ground-texture loader, its own
feature overlay with its own opacity, its own region overlay with its own two
display modes, a tile-size slider and a matched-pair count - and every one of
those is a second copy of a control the 2D map already has. The two pictures
drift apart the moment either is touched.

**Ours is the same picture, lit and tilted.** `cm3Texture` composes the mesh's
colour map in `cmapPaint`'s own order - 23a's ground, then the one-pixel-a-tile
composite of every ticked layer at its own opacity, then 16g's colouring last
because a tint has to be read against what is under it. So the 3D has **no
layer controls at all**: ticking a layer, dragging an opacity, flipping the
season, changing the gap colour or applying a query colouring all change the
surface, because they change the thing the surface is painted with. The card
over the map carries two switches, a Fit, and two sentences saying so.

That leaves **one hook**, at the top of `cmapPaint`, which is the funnel every
one of those ends in. Keyed on what was last uploaded, so the pans, the hovers
and the resizes that also land there cost a string compare. A list of callers
kept in `map3d.js` would have been a list to forget to add to.

### Three things we did not have to solve, and one we had to correct

| his | ours |
|---|---|
| the ground is sampled one texel to a tile in the browser, which is what the tile-size slider and the "none matched" warning manage | `mapterrain.composite` has drawn it at `SCALE` pixels a tile, supersampled, once a season, since 23a. `c.terrain.img` is that picture already decoded, so the mesh is textured with a blit. No tile cache, no per-pixel loop, no folder to pick |
| the mesh caps at 2048 steps, and the 512 it capped at before dropped one-pixel islands and thin isthmuses | `descr_terrain.txt` caps a map at 510x510 and the heights layer arrives at `fit=tile`. **One vertex per tile, no cap, no resampling** - 248,370 vertices on DaC, 260,100 at the engine's ceiling |
| sea is "the heights pixel is blue **or** the ground type is one of the four water colours" - two rules, because the first alone left sea at land elevation | `mapvocab.is_sea_height`: not greyscale, or black. **One rule**, and `tests/test_map3d.py` runs it against Python's on the installed maps and agrees tile for tile - 74,365 on DaC and 71,968 on ROCSS |

The fourth is not a correction but it is worth writing down: **the vertex
normals are a central difference over the height field**, not an accumulation
over the faces. One pass rather than two, no per-vertex face list, and on a
regular grid it is the same answer. The test checks every normal is a unit
vector, which is the one thing a bad difference would silently not be.

His numbers we did take, because they are right and measured: the sea floor at
`-0.12` of the height scale and the water surface at `-0.04`, so the two cannot
z-fight and a coastline is still a coastline; near and far off the map's own
diagonal, because a `0.1..100000` range on a map this size spends the depth
buffer on distances nothing occupies and gives back z-fighting in bands; and a
fog density tied to that diagonal, because a fixed one swallows a large map
whole.

### Two faults found by testing it, both now guarded by the suite

1. **A bare `requestAnimationFrame` hangs the build.** The mount yields one
   frame so the "Building the mesh" line is on screen before a quarter of a
   million vertices are built on the thread. A browser stops servicing rAF for
   a tab that is not being rendered, so switching tab between the press and the
   build left the promise unresolved **forever**, with the message up, no scene
   and no error. Found exactly that way. `cm3Yield` races the frame against a
   120 ms timer; a hidden tab takes the timer and paints nothing, which is the
   right answer because there was nothing to see.
2. **`loseContext()` does not free a canvas to be drawn on again.** The element
   keeps that context for good and hands the same LOST one to the next
   `getContext`, so turning the mode off and straight back on built a scene
   that never drew - the shader "failed to compile" with a null info log, which
   is what a lost context reports. `cm3Stop` gives the context up properly and
   then swaps the element for a clean `cloneNode(false)` of itself. Three
   off/on cycles and two with no wait between them now come back live and
   unlost.

### What is deliberately not in it

Markers, labels, the selected outline and the hover tooltip. All four are
screen-space drawing over a flat canvas (`cmapOverlay`, `maplabels.js`) and
none of them has a position in a scene. They stay on the 2D map, the card says
so, and `D` puts you back. His does not put them in 3D either.

The mode is **not remembered between sessions**, alone among this screen's
switches. The rest are ways of reading a flat map and cost nothing to open
into; this one opens a WebGL context and builds a mesh, and somebody who looked
at one map in 3D should not find the next mod opening that way. The height
scale and the water plane **are** remembered, and ride in `cmapLayerState`, so
a named view carries them - which is the contract that comment states for any
switch added to this screen.

Exit: `web/js/map3d.js`, a `⛰ 3D` button on the map toolbar and a `D` key, the
card, `cm3DropOrphan` beside `v3DropOrphan` in `applyMode`, and
`tests/test_map3d.py` - 34 checks, the mesh run for real in node against both
installed maps.

---

## The contributor's campaign map editor, 2026-09-20, and what it did not close

`865c22f`, one commit, 18 files and 870 insertions, on the campaign map
workspace only. Merged; our two port commits rebased on top of it with no
conflict, and nothing of ours was overwritten - it never touches `app.py`,
`startup.py` or `build_release.py`.

**It closes no open item on this roadmap, and that is the finding rather than a
complaint.** What it does is extend seven that are already done: 17d's markers
(character-type symbols, faction colours, port anchors, a highlight ring, a
chooser for a tile holding several), 17e's hover (the terrain list off the
ordinary card, the detail kept in the clicked-tile inspector), 20b's find box
(an alphabetical browse list when the query is empty, and the rows are buttons
with an `aria-pressed` now), 20c's labels and pin (character names, army unit
counts, port names in the same collision-avoiding layout), 22a/22b's placement
(a `+ Create` panel over the existing guided workflow), and 28a/28b/49/50's
workspace (the bar at the bottom, a compact toolbar, a help panel, focus
indicators).

**Two things to be clear about.** The searchable region browser is **not**
M10's region search arriving: M10 is an OSM backdrop and a region search
together, three stars, and it is `Phase 25` in the Future list, off by default
because it is the first thing in the toolkit that touches the network. Our own
find box has existed since 20b, and what landed is a browse list on it. And
**character editing on the map is genuinely new and was never tracked** - the
character form, traits, ancillaries, army composition and upgrade controls
brought into the map workflow, with roster data in the marker response so a
hover needs no second request. It is not on this roadmap because nobody put it
there.

---

## The 2026-09-13 pass, and the two parts of it that produced a measurement

**Traits and ancillaries are still level, and the way to know is the date.**
`src/components/traits/` and `src/components/ancillaries/` were last touched
upstream at `4323ef9` on **2026-03-27**, and `src/components/shared/` - the
trigger and condition half both of his editors use - at `ef523e3` on
**2026-03-25**. `docs/upstream/audit-traits.md` and `audit-ancillaries.md` were
both written against code newer than that, and both verdicts stand as written:
every field he exposes we expose, his serialiser rewrites the whole file and is
refused, his `Type` and `ExcludeCultures` dropdowns are hardcoded lists that
337 of the installed mods' 350 real `Type` values fall outside, and his trigger
half keeps each condition as a raw string so it has no vocabulary and no
never-fires check. Nothing new to compare against. Re-check with
`dev/reference/upstream_sync.py sync` before believing this a second time.

**The strings codec goes the other way, and so does the map validator.** Three
things are now worth passing back to him in one message rather than three: the
`u16` count and the missing tag index in `stringsBinCodec.jsx` (Phase 48), the
orphan-white-source severity that makes his own validator call vanilla broken
at image (175,14), and that the standalone `map_features_checker.py` he ported
from cannot open either installed map because both ship RLE TGAs (both
Phase 31).

---

## The 2026-09-17 pass: his model reader is ours, and four things are ours to build

`187d9ed..439aa9b`, **34 commits and 49 files**, the largest sync since the
mirror was set up, and the manifest is at **342 files with none untriaged**. Two
halves, and they point in opposite directions.

### The asset half is our own code, come back as JavaScript

`src/lib/m2CasCodec.js` and `src/lib/m2MeshCodec.js` are **`unittransfer/cas.py`
and `unittransfer/mesh.py` transliterated**. Not the same knowledge arrived at
twice - the same names, the same numbers and the same comments:

| ours | his | value |
|---|---|---|
| `NODE_COUNT_AT` | `NODE_COUNT_AT` | `0x32` |
| `NODE_TRAILER` | `NODE_TRAILER` | `25` |
| `OBJECT_HEADER` | `OBJECT_HEADER` | `{1: 37, 2: 28}` |
| `CHUNK_TRAILER` / `_OLD` | `CHUNK_TRAILER` / `_OLD` | `{1:6, 2:4}` / `{1:3, 2:4}` |
| `TRAILER_VERSION` | `TRAILER_VERSION` | `3.17` |
| `NO_MATERIAL` | `NO_MATERIAL` | `0xFFFFFFFF` |
| `MATERIAL_TAIL` | `MATERIAL_TAIL` | `29` |
| `BOOST_SIGNATURE`, `STREAM_STRIDE`, `STREAM_GAP`, `MAX_TRAILER` | the same four | `serialization::archive`, the same stride table, `96`, `64 * 1024` |

`cas.py:378` carries the comment `# over the two RGB triples` on the line that
seeks to `NODE_COUNT_AT`; `m2CasCodec.js:166` carries `// over the two RGB
triples` on the same line. **The dates line up with the direction**: `cas.py`
has been public here since 2026-09-06 and Phase 29 landed on 2026-09-12, his
file first appears on 2026-09-14, and the header of the `casCodec.js` he deleted
to make room says in his own words that the spec it had was invented and
"matches no real game file".

**Nothing to do about it and nothing to take from it.** The README credits his
tool as a reference and this is the same traffic in the other direction. What it
changes is the manifest: `m2CasCodec.js`, `m2MeshCodec.js`, `boostArchive.js`
and `m2ModelGeometry.js` are **`skip` - something we own outright**, and the
asset half of the port-concept set is closed. Reading his `.cas` work for format
knowledge from here on is reading our own back.

### Four candidates, filed as M18 to M21, and none of them rated yet

Full write-ups in `docs/upstream/REFERENCE_GAPS.md`. They are unrated on purpose:
the user rates, and a rating is what turns one of these into a phase.

**M18 is done, and it was asked for rather than rated** - on 2026-09-20, three
days after being filed. That is the other way one of these becomes work, and
the row below is struck through rather than removed so the ballot still reads
as it stood. M19, M20 and M21 are still unrated.

| Item | Size | What it is | Why it is worth a star |
|---|---|---|---|
| ~~**M16, the playback half**~~ | M | **DONE 2026-09-23 as Phase 55**, asked for by a tester. Two things the row had wrong: `cas.py` could not read an animation file, and the pose is not a delta from a bind quaternion - the bind rotation is identity, the keys are the rotation, and a position key is an offset from the pivot. Sample an animation file onto the skeleton the viewer already draws. Joints are matched by name, the pose is a delta from the bind quaternion, slerped between key times, 25 fps when the file carries no ticks. | `cas.py` already reads the container and already names `data/animations`' 305 files as future expansion. The editor half of M16 stays out of scope; this is the half that is a session. |
| ~~**M18 - the map in 3D**~~ | L | The heightmap as a mesh with the ground textures on it, orbited. | **DONE 2026-09-20**, asked for directly rather than rated, and it came in well under L for the reason the last column predicted: `mapterrain.composite` already solved the textures, so it is a mode over the stack the screen was holding and not a second map. Write-up above under *M18 - The map in 3D*. |
| **M19 - climates past the twelfth** | M | His four generated files are Phase 34's four. What is new is the claim that **M2EX** lifts the twelve-name wall Phase 34 stopped at. | Verify first. If it holds, appending a name becomes the first option on an M2EX mod and `too-many-climates` joins `modflags.CAP_FINDINGS`. |
| **M20 - a scatter brush** | S | A sixth tool that scatters `round(pi * r^2 * 0.12)` pixels in the brush radius. | His own use for it is `forest_sparse`, the ground type a pencil cannot make look right. The toolbar and the palette column are already there. |
| **M21 - `texture_density`** | S | A root-level directive in `descr_aerial_map_ground_types.txt`, `span = max(1, 8 / density)`. | **`mapterrain.parse` drops the line today.** Measure the installed mods: nobody declares it and this is one read and a scale, somebody declares it and 23a has been tiling at the wrong rate. |

**The Koppen tool is not a new item.** One climate per Koppen-Geiger zone in one
press, seeded from a static table of 30 codes and their legend colours with no
network call in it, which is `koppenZones.js` and the bulk-add in
`CustomClimateForm.jsx`. That is Phase 27's bucket since the 2026-09-03
reclassification, and it is already rated three stars there. The table itself is
portable as it stands.

### Three things to send back to him, in one message

1. **The pixelated textures.** Draw the ground at several pixels a tile and
   supersample the tiling, once per season, rather than sampling one texel per
   tile at draw time - 23a's `SCALE`, and 37b's finding that a picture scaled
   into a per-tile composite and back out is the artefact.
2. **`texture_density` cuts both ways.** If we are dropping the line, he should
   check that `spanForDensity` is reading it from the root and not from a
   climate block.
3. The three from 2026-09-13 that have not been sent yet: the `u16` count and
   the missing tag index in `stringsBinCodec.jsx`, the orphan-white severity
   that makes his validator call vanilla broken at image (175,14), and the RLE
   TGAs that stop `map_features_checker.py` opening either installed map.

---

---

---

# Future roadmap - rated, and waiting on the two main tasks

**This is one list and it replaces two.** The Later table of 2026-09-05 and the
TWCenter candidate tables of 2026-09-12 said different things about the same
work in two places, which is how the old `ROADMAP.md` reached three thousand
lines. They are merged here.

**Where the ratings came from.** The user rated 38 of 39 candidates one to five
stars on 2026-09-12. Everything rated **four or five stars that is campaign-map
or mercenary work became a phase** above; everything else is below, ordered by
stars and then by size. The one unrated row is at the foot.

**The 2026-09-05 triage board is gone and nothing was lost with it.** It was
published as an artifact and is no longer in the gallery, but its output was
copied into this file at the time as the Later table, all thirteen items: D1,
D12, D13, G2, G4, M7, M12, M16, M17, T3, T6, T7 and T10. Every one of those
thirteen was on the 2026-09-12 ballot and every one now carries a rating, so the
two selections are already reconciled. Six of them were promoted - **D1, G2, G4,
T3, T7 and T10 all rated five stars** and are Phases 33, 36 and 37 - and the
other seven are below.

**Two items were promoted out of their own rating**, and both deserve saying:

- **The mercenary repairs (five stars, S)** are not a phase of their own. They
  are 32c, because a rule and the repair for it are one piece of work and
  splitting them is how a validator ends up with findings nobody can act on.
- **The EDU ceilings (three stars, M)** were pulled up into Phase 39 by the
  20,000-face model ceiling beside them, which rated four. Both come out of one
  document and neither is a session on its own.

## Five stars, and first in the queue when the two main tasks land

| Item | Size | What it is |
|---|---|---|
| ~~**M17 - a crash and validation dashboard**~~ | M | **Done as Phase 54, Health, 2026-09-22.** We have more validators than any of the four reference tools and no single door to them: 32 map rules, the faction audit, the EDB checks, the BMDB audit, the sounds audit, and after Phase 32 five mercenary rules as well. The archive's two crash guides, *GUIDE - Crashes and how to fix them* and *Crash to Desktop*, are the checklist that would give them one front page. |
| ~~**M12 - bulk faction duplicate, and faction zip export**~~ | M | **Done as Phase 56, 2026-09-23.** One plan over `factionclone.py` repeated, plus `pack.py`. Mylae shipped his version in September 2026 and it is in the mirror at `DuplicateFactionModal.jsx`, `FactionZipExport.jsx` and `factionBulkDuplicate.js`, all three triaged port-concept. |
| ~~**M16 - animation editor and asset converter**~~ | L | **Done as Phases 55 and 57, 2026-09-23.** Excluded originally because we could not read `.mesh` or `.cas`. **15a and 16k both now can**, so the exclusion no longer holds on its own terms and the item is live again on the merits. |

## Four stars

| Item | Size | What it is |
|---|---|---|
| ~~**Will this mod even launch**~~ | S | **Done as Phase 58, 2026-09-23.** A readiness row on the Home card, not an editor. Home already says what each mod is ready for and cannot say whether `configuration.cfg`, `mymod.cfg` and the registry entry will actually start it. Eleven archive documents including the Steam install and registry tutorials. |
| ~~**B2 - delete a settlement, and move one between mods**~~ | M | **Done as Phase 61, 2026-09-23.** Assigning a settlement to a faction already works and B1 added the create. Missing: the delete, whose shape is `stratcamp._delete_splice`; a button on the panel for a province that has none; and the between-mods move, which is probably its own session. Phase 24's warning applies - a settlement that goes has characters, armies and a capital flag hanging off it. |
| ~~**B3 - insert and export one file at a time**~~ | M | **Done as Phase 62, 2026-09-23.** Mylae's tool pushes a file into, or pulls one out of, a mod on its own. Pieces exist - `POST /api/map/export`, 16g's per-faction TGA, `pack.py`'s unit import - and none of it is a general take-this-file-out. The user's own earlier words were "that isnt really needed tbh"; the four-star rating supersedes that. |
| ~~**Add a religion**~~ | M | **Done as Phase 60, 2026-09-23.** We edit the religion list in Minor Files, the EDB conditions and the religion columns on the region form. Missing: `descr_religions_lookup.txt`, and the must-sum-to-100 rule as a guard at **creation** rather than only as a validation afterwards. |
| ~~**Mines and hidden resources**~~ | S | **Finished as Phase 59, 2026-09-23.** **Halved on 2026-09-13: the hidden-resources half is Phase 45, done 2026-09-21**, which adds and removes on the EDB's own line with the two joins that make a removal safe. What is left here is `descr_settlement_mechanics.xml` and the ceiling of 63, which Divide and Conquer's 75 disproves as written and which belongs with Phase 39's other ceilings if that session has room. |

## Three stars

Ordered small to large, because at this rating size is what decides whether one
is worth picking up.

| Item | Size | Note |
|---|---|---|
| ~~`descr_settlement_mechanics.xml`~~ | S | **Done as Phase 59, 2026-09-23.** |
| ~~`descr_lbc_db.txt`~~ | S | **Done as Phase 63, 2026-09-23.** |
| ~~`descr_offmap_models.txt`~~ | S | **Done as Phase 63, 2026-09-23.** |
| ~~`descr_animals.txt`, `descr_standards.txt`, `export_descr_advice.txt`~~ | S | **Done as Phase 64, 2026-09-23.** 41, 23 and 6 lines. Third Age Reforged ships no `descr_standards.txt` at all and DaC's advice file is six lines, so this is one small session for all three or none. |
| `descr_banners_new.xml` | M | 405 lines, 25 tags. Every *add a faction* tutorial names it and the faction audit has a row-shaped hole where it should be. |
| `descr_hero_abilities.xml` | M | 1,187 lines, 26 tags. Hangs off the people panel, which already edits the character. |
| `descr_area_effects.xml` | M | 555 lines, 34 tags. Interdict, excommunication and the rest. |
| `descr_walls.txt` | M | 514 lines. Wall definitions per culture and level; pairs with the settlement panel. |
| `descr_character.txt` | M | 1,708 lines, twelve archive documents, **read by six modules and written by none**. It is the missing join: `stratmap.py`'s audit names a `.cas`, the Strat models panel draws one, and nothing connects either to the character that uses it. The lowest-rated item on this page that the measurement argues hardest for. |
| **T6 - export every tile as text** | M | Campaign-map work that did not rate high enough to schedule. We export pictures and never numbers; `mapquery`'s fact table is the join it needs. |
| **D12 - export the project as a zip, and load one back** | M | `pack.py` already does this shape for a unit, import and conflict report included. |
| **D13 - generate a horde start for a new faction** | M | 16j-2 already creates a faction with no settlement and no character, which is the shape vanilla's Mongols already are. This is the other half. |
| ~~The three voice files~~ | M | **Became Phase 47a on 2026-09-13**, with three more export files beside them and at M rather than L: `sounds.py` already reads that grammar, so the cost was the size and the size is not the parser. |
| **M7 - import a campaign from another mod** | L | Unit Transfer's problem at campaign scale; `transfer.py` is the model. |
| **Phase 25 - OSM backdrop and coastline tracer** | L | Campaign-map work at three stars. The write-up below stands; it is the first thing in the toolkit that touches the network, so it is opt-in and off by default. |
| **Phase 26 - map resize, and create from scratch** | L | Campaign-map work at three stars. Phases 22 and 24 removed most of the original objection, so it is cheaper than when it was deferred. |
| **Phase 27 - overlay and layer generators** | L | Campaign-map work at three stars. Same opt-in rule as 25. |

---

# Finished after the 2026-09-23 split

From here on a phase's write-up lands in this file the day it finishes, and
its row in `ROADMAP.md`'s schedule is struck through in the same commit.

## Phase 65 - `descr_banners_new.xml` - DONE 2026-09-23

A **Battle banners** tab (`banners.py`), a row on the faction audit, and a
thirteenth file in the faction clone. Every *add a faction* tutorial names
this file, three modules read it and none wrote it.

**Read as text, not by an XML library**, because **DaC's copy is not
well-formed**: its `</Banners>` is on line 391 and thirteen lines of an older,
longer royal banner follow it, saved over and never cut off. The game plays it,
so it stops at the root's close, and so does the reader - tags tokenised by
hand, every offset kept, edits spliced into attribute values and whole lines.
The lines after the root are a warning with a *cut them off on save* button.

**The rule that matters, measured**: a faction that owns a unit carrying banner
X has a row in X. True on both mods without one exception for the faction and
unit banners (`all` in an ownership line is not a faction), so a miss is a
warning; the same rule for the holy banners fails 15 times on DaC, which plays
because a faction that never crusades never raises one, so those are a note per
banner. DaC's royal banner missing three factions is a note. Rows for
`Ally0-5`, `Enemy0-6` and `Rebels` are multiplayer placeholders both mods carry
and are never reported. A missing path is not a finding (DaC names 62 files the
base game packs), but two kinds are, and they found **ROCSS's two broken
textures**: `faction_banner_antioch_trans.texture.texture` (the extension
twice) and `Faction_banner_thospitaller_trans.texture` beside the
`faction_banner_hospitaller_trans.texture` it meant (a missing file within two
letters of one in the same folder).

**The screen** edits every attribute (meshes, offsets, the settings' numbers,
each row's faction and paths), adds a row by copying one and removes one, with a
signature, one backup and one Undo. **The clone** copies every row naming the
donor under it for the new faction; a path swaps the donor's slot for the
clone's only where that file exists or the art copier is about to make it, and
otherwise keeps the donor's, which loads. **The audit's Battle banners row** is
a gap: every faction in both mods has a texture in its faction banners. The
wording "twelve files" became thirteen everywhere it meant the clone's list.

**Not done, and why**: a faction *rename* still does not follow this file. The
rows name art by paths that carry the slot, and a rename that rewrote them would
point at files the rename does not move.

Exit: `tests/test_banners.py`, 25 checks. `test_factionclone`'s one failing
check (an EDB clause join) fails the same way on master and is not this phase's.


## Phase 66 - `descr_hero_abilities.xml` - DONE 2026-09-23

A **Hero abilities** tab (`heroabilities.py`, over a new shared reader,
`leafxml.py`), a Health source, and the people panel joined to it. A
`descr_strat.txt` character line ends `hero_ability IRON_FIST` and this file
says what that is: duration, activations, cooldown, three tooltip labels, three
button sprites, a sound, and the effects on the armies.

**The people panel had no list.** Its own comment said the ability names were
"in `descr_strat.txt` and nowhere else", so the picker offered what the
campaign already wrote. It now offers what this file declares (and what the
campaign uses, so nothing it offered before is gone), a character naming an
ability the file lacks is a warning in its findings, and under the field a
*What it does →* link opens the ability in the new tab (a real link, so middle
click is a new tab).

**One reader for two files.** This file and Phase 67's are the same shape: a
root, one list, records whose values are element text, some grouped. Phase
65's banner file keeps its values in attributes, so its reader stayed its own.
`leafxml.py` tokenises tags by hand like the banner reader (DaC's area effects
carry a `;;;` comment after a closing tag, and both files are thick with
comments), keeps every offset, and takes one edit body for both: `values`,
`attrs`, `copy` (a record under a new name, or a group member into another
group), `remove`, `add_field` (after the record's last value, so a field lands
among its own and not after an ability's effects block).

**Measured before any rule was written** (ROCSS 7 abilities, DaC 32; DaC's
1,187 lines and 26 tags are the roadmap's row):

* Every `hero_ability` any character names, in every campaign and battle of
  both mods, is declared. That is the warning that matters, and it fires on
  neither.
* ROCSS's `The_Heart_of_the_Lion` has `<selected_sprite>` twice: a warning,
  the only one on either mod.
* Both give `army_morale` a `permanent`, which the file's own sample
  documents only for `army_fatigue`; ROCSS has a `kill_chance_modifier` of
  -0.5, below the sample's "0 = no chance to kill". Notes: both mods play.
* A seventh effect the sample does not document, `projectile` with only a
  `projectile_name`, is ROCSS's `Super_Banana_Bomb`, and its projectile exists.
* ROCSS's two unused abilities name `EMT_HERO_SPECIAL_ABILITY_DEFAULT_*`
  labels its `expanded.txt` lacks. A missing label, sprite or sound is a
  warning on an ability a character carries and a note on one nobody does.
* DaC ships `ui/battle.sd`, and all 84 sprite names are in it (a
  length-prefixed name, found as bytes); ROCSS ships none, so the sprite rule
  only runs where the mod has the file. Every `sound_effect` in both is an
  `event` in the mod's `descr_sounds_generic.txt`.

**The screen** lists the abilities with how many character lines give each,
and edits every value (target, morale level and `permanent` as pickers), shows
each label's tooltip text, adds and removes fields and effects, copies an
effect from any ability into this one, copies an ability under a new name and
removes one (warned when characters name it). A signature, one backup, one
Undo.

Exit: `tests/test_heroabilities.py`, 38 checks.

## Phase 67 - `descr_area_effects.xml` - DONE 2026-09-23

An **Area effects** tab (`areaeffects.py`, on `leafxml.py`) and a Health
source.

**The roadmap's row was wrong about what this file is.** It said "interdict,
excommunication and the rest", which are campaign mechanics. An area effect
is a **battle** thing: what a projectile's `area_effect` line (and a holy
cart's in `descr_engines.txt`) does where it lands. Six types, the same 34
tags on both mods (ROCSS 55 effects, DaC 41): `nausea` (the cow carcass),
`holy` (the aura), `fire`, `explosion`, `projectile` (a shot that splits into
more) and `area_effect_set`, whose `<effect delay="0.2">` rows are other area
effects fired one after another. **An `<effect>` in a set names an area
effect; anywhere else it names an effect set**, and the rules keep the two
apart.

**`descr_effects.txt` is a manifest of 18 effect files, and the toolkit read
four.** `effects.FILES` and `projectiles.effect_sets` scan the four a
projectile's own effects live in; area effects name sets from the others
(DaC's `nahptha_fire_set` is in `descr_burning_building.txt`), so this phase
reads the manifest. **The four-file index under-reports for projectiles too**:
11 of ROCSS's projectile effect sets and 21 of DaC's live in files it never
reads (`arrows_fire_new_set`, `greek_fire_set`, ...), and a unit transfer
blanks an effect it thinks the destination lacks. Measured here and left as
its own fix, not widened inside this phase.

**Measured, and what became a rule:**

* Each mod has one projectile whose `area_effect` is declared nowhere:
  ROCSS's `quality_fearcommand_arrow` (`ae_fearcommand_arrow`) and DaC's
  `poison_javelin` (`ae_poison_javelin`). The warning that matters, and the
  only warning on either mod.
* Both mods' `ae_nahptha_shot` names the area effect `ae_medium_fire` where an
  effect set goes. CA's own line, on both: a note.
* An effect set the manifest's files lack is a note while the mod leaves one
  of those files to the base game (ROCSS lacks eight of 18, among them the
  file that declares `nahptha_fire_set`), and a warning, with a near miss
  named, once the mod ships them all.
* The file's comment gives four directions (forward, backward, up, down);
  `horizontal` is written 11 times across the two mods on shots they fire, so
  it is a fifth. Anything else is a note.
* No duplicate, no unknown type, no colour past 255, no projectile type that
  is not a projectile. Many effects are named by nothing a mod ships (20 in
  ROCSS, 15 in DaC); the list shows each one's users and sets, and that is not
  a finding.

**The screen** lists the effects under their six types, with who names each
(projectiles, engines, sets); edits every value (type, direction and
`preserve_momentum` as pickers, the banner colour's three parts), adds a field
the type takes and removes one, copies an effect under a new name (declaring
DaC's `ae_poison_javelin` that way clears its one warning), and edits a set's
members: each one a picker over the file's own effects with its delay, removed
or added with its own delay in the same save. A signature, one backup, one
Undo.

Exit: `tests/test_areaeffects.py`, 37 checks.
