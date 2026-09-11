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
