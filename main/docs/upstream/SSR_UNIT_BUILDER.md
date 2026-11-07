# Stainless Steel: Reforged Unit Builder - integration source notes

Reviewed 2026-11-06 for roadmap planning only. No application code imported or
changed, no upstream tests run, and no installed mod modified.

## Source and permission

- Repository: https://github.com/lupinemaverick/stainless-steel-reforged-unit-builder
- Reviewed `main` commit: `d4ed9368d0db3da2000bc895e96f52a83b93cb67`.
- Commit date: 2026-10-15T18:36:06Z; subject: "Export selected custom weapon
  attributes in EDU and rename Hook label".
- The user explicitly reported full permission from the author to copy code as
  needed, then asked for phased roadmap work rather than an all-at-once port.
- Upstream README credits the MUG Unit Builder v1.5 and MUG Unit Creation Guide,
  with Combat Reforged work developed for King Siegfried. Preserve original
  attribution and record provenance alongside any future copied code/data.
  No new distribution license is declared in that README; do not invent one.
- Pinned source link:
  https://github.com/lupinemaverick/stainless-steel-reforged-unit-builder/tree/d4ed9368d0db3da2000bc895e96f52a83b93cb67

## What was inspected

Unauthenticated GitHub API metadata and selected raw source files were read;
source snapshots are local scratch files under
`.cache/upstream/ssr-unit-builder/d4ed9368d0db3da2000bc895e96f52a83b93cb67/`.
The repository is a standalone browser builder assembled by `build.py` from
`src/base_v1.5.html` and plain JavaScript/CSS modules into `index.html`.
The README describes EDU/CSV output, portable project JSON and browser-local
preset edits. Its test harness uses Node and Playwright. These are source
observations, not claims that its browser behavior or battle effects were tested.

| Upstream area | Inspected evidence | Planned toolkit destination |
|---|---|---|
| Base inputs, archetypes, presets, totals, EDU/CSV | `src/base_v1.5.html` | Python rule data/calculator + Unit Editor designer; existing EDU parser/export paths |
| Subtypes, weapon categories, offhands, metadata, project JSON, mercenary snippets | `src/reforged.js` | Profile/schema and adapter; existing unit/edit and mercenary planners |
| Revised combat arithmetic, defending slot, migration | `src/combat_rules.js` | Calculator rules and golden tests |
| Further rule corrections and manual overrides | `src/audit_rules.js` | Explicit rule mapping and fixture cases; resolve conflicts before porting |
| Equipment grade independent of training | `src/equipment_grade.js` | Profile data, calculator and UI controls |
| Armor layers/loadouts | `src/armor_loadouts.js` | Presets and calculator contributions |
| Grouped unit attributes and terrain modifiers | `src/unit_attribute_controls.js`, `src/attribute_reference.js` | Existing vocabulary + grouped designer controls; native versus custom classification |
| Weapon defaults and profile revisions | `src/weapon_phase_a.js` | Revision-aware data and project migration review |
| Category-filtered preset lists | `src/preset_filters.js` | Designer preset filtering |
| Regression examples | `tests/test_builder.cjs`, `tests/run.cjs`, README | Future golden cases and independent regression coverage |

## Findings that shape the roadmap

1. Combat Reforged is a balance profile, not universal Medieval II ground truth.
   Its equipment grades, revised attack/handling values, armor/skill terms and
   costs must remain an explicit choice. Do not overwrite another mod's rules
   merely because the user opened its Unit Editor.
2. Custom effects are not implemented battle runtime. The README says so. The
   inspected `exportableAttrs` nevertheless allows `CUSTOM_TAG` weapon entries
   and translates `hook_drag` to `hook`, while notices still describe omitted
   design-only tags. Phase 102 must reconcile this drift before setting an
   export contract; copying its filter wholesale is not compatibility evidence.
3. The upstream project is `schema: combat-reforged-builder`, `version: 1`, with
   form fields, presets and computed unit data. The adapter needs the original
   design inputs and overrides; an EDU block alone cannot recover them uniquely.
4. Horse barding, quality versus equipment grade, two-handed offhand suppression,
   defending-slot skill, terrain choices and explicit hiding opt-outs have special
   handling. They need representative fixtures, not just a translated formula.
5. Mercenary output is a snippet intended to be merged into an existing pool.
   Our integration should call the current pool parser/planner, preserving its
   regions and gates, rather than appending the upstream text into a game file.
6. Existing toolkit integration points include `unittransfer/edu.py`, `edit.py`,
   `transfer.py`, `unittypical.py`, `mercpools.py`, and `web/js/editor.js` plus
   the existing New unit picker and Code View. Exact APIs and new module names
   remain for Phase 102; this review did not implement a second pipeline.

## Scope and next step

The seven independent phases and their exit criteria live only in ROADMAP.md,
Phases 102-108. The next implementation increment is Phase 102's detailed audit
and schema/examples, when the user resumes that work. Do not chain all phases
into a single port. Update CODEX_HANDOFF.md with each completed increment.
