# Guided unit builder contract (Phase 102)

Reviewed 2026-11-08. This phase adds an offline contract and synthetic examples.
It registers no app route, changes no existing app behavior, runs no upstream
program and writes no mod. Phase 103 owns calculation; 104 owns controls; 105
owns upstream interchange; 106 owns reviewed staging and Apply; 107 owns pools.

The authoritative source for this integration is the pinned
[lupinemaverick revision](https://github.com/lupinemaverick/stainless-steel-reforged-unit-builder/tree/d4ed9368d0db3da2000bc895e96f52a83b93cb67),
not a moving main branch or the hosted page. GitHub commit metadata confirms
`d4ed9368d0db3da2000bc895e96f52a83b93cb67`, 2026-10-15T18:36:06Z,
"Export selected custom weapon attributes in EDU and rename Hook label".
Read-only source hashes, the feature/module map, compatibility classes and
blocked questions are in [the machine-readable audit](upstream/SSR_BUILDER_AUDIT.json).
The user reported full author permission to reuse code. Preserve lupinemaverick,
MUG Unit Builder v1.5, MUG Unit Creation Guide and the Combat Reforged work for
King Siegfried attribution with future copied code/tables. The README declares
no new distribution license. This phase copies no implementation or balance
tables. Source snapshots are read-only task scratch files; their cleanup status
is recorded in CODEX_HANDOFF.md.

## Source layering and feature map

Reading base_v1.5.html alone gives the wrong rules. `build.py` replaces its
archetype and mental resolvers, removes legacy mercenary penalties, changes
ammunition and exporters, renames Standard to Average and injects modules in
this order: reforged, weapon_controls, attribute_reference, audit_rules,
combat_rules, preset_filters, equipment_grade, armor_loadouts,
offhand_revision, weapon_phase_a, unit_attribute_controls. The build script
was read as text, never executed. No generated HTML or upstream assets were
imported. Later wrappers can replace earlier numerical results.

| Feature | Effective upstream behavior and scope | Toolkit destination |
| --- | --- | --- |
| Archetypes | Eight generated identities: Royal Retinue, Martial Nobility, Household Soldiers, Career Soldiers, Urban Militia, Rural Militia, Warrior Levies, Emergency Levies. Training, morale, size and heat are profile balance, not universal engine rules. Equipment module removes archetype equipment bonuses. | Profile tables/calculator in 103. Never infer sheet Race/Tier/Main Faction/AOR from these identities. |
| Subtypes | Guards, Hybrid, Aggressive, Reckless, Fanatic, Bloc, Raider, Mounted, Engineer, Mercenary, Garrison, Command. Reckless wins discipline; Fanatic locks morale; Hybrid requires missile primary, halves base ammo and changes training/cost. Royal Guards, SSR Garrison, mounted-cavalry and non-siege Engineer combinations have eligibility checks. | Calculator eligibility in 103, controls in 104. Native values through shared sheet fields; automation flags stay metadata. |
| Weapons | Nineteen melee categories: knife, sword_cut, sword_thrust, axe, mace, pick, spear, fighting_spear, pike, longaxe, glaive, bill, halberd, poleaxe, longsword, greatsword, estoc, staff, lance. Presets also group bow, crossbow, firearm and thrown; secondary has a distinct none. Role filtering permits custom presets. Revised attack and handling supersede base tables. | Profile data in 103, vocab.py for engine vocabulary, sheet_ops for native tuple values. Filter eligibility in 104; no second parser. |
| Armor | Separate ensemble preset, base component, weight and up to three additional layers. Weight limits slots; base and active layers add once, inactive slots clear. Legacy sound names normalize to flesh/leather/metal. | 103 loadout arithmetic and 104 presets. Shared armor/defense/shield columns; other tuple members use existing edit planner in 106. |
| Offhands | Legacy shield/material or empty, buckler, small, medium, large, dagger. Only the defending slot contributes. A two-handed slot suppresses its held offhand without erasing the saved selection. Later signed tradeoff and migration layers matter. | 103 contributions; retain suppressed inputs. No active-weapon battle runtime is implemented. |
| Mounts | Horse type, origin and barding are separate. Horse-only barding adds once to rider armor; grade applies to worn armor, not barding. Camel/elephant do not use that horse rule. Geometry, movement and stamina descriptions require external configuration. | 103 profile arithmetic; existing vocab/edit/transfer for actual mount IDs in 106; geometry/speed/stamina remain metadata. |
| Grades | artisan, high, common, munition, poor, independent of quality/training. Royal Retinue forces artisan. Stats/cost multipliers are Combat Reforged choices. | Explicit rules profile in 103; no mapping to sheet Tier, barracks depth or EDU sorter metadata. |
| Attributes | Separate overall, active-weapon, terrain and custom proposal controls. Terrain choices affect stat_ground, not attributes. Hiding has absent/true/false states. Conditional matchup descriptions must not add unconditional Attack twice. | Existing vocab.py lists for new output, grouped controls in 104; unverified tags and descriptions remain metadata. |
| Projects | Upstream schema combat-reforged-builder version 1 carries fields, presets, weapon_categories and cached unit. Revision-specific import wrappers migrate recognized defaults and preserve custom values. | Native packet below; explicit 105 adapter, transactional import, raw upstream packet retained in metadata. Cached unit is not authoritative. |
| Exporters | EDU rebuilds a full block, CSV substitutes semicolons for commas, mercenary exporter produces pool snippets. Art commentary is optional. Their output is not a lossless edit of an existing unit. | edu.py, edit.py, transfer.py, sheet_native.py and sheet_interchange.py; mercpools.py in 107. No snippets appended directly, no new stat/recruitment pipeline. |

## Compatibility matrix and unresolved items

| Target capability | Contract |
| --- | --- |
| Native profile | Explicit `{id: native, revision: "1"}`. No automatic recalculation or Combat Reforged defaults. Existing donor/native values remain authoritative. |
| Combat Reforged balance | Explicit `{id: combat-reforged, revision: <pinned commit>}`. No folder-name detection. This is a rules choice, not proof that the mod implements a runtime effect. |
| New native attributes | Accept only exact fixed toolkit vocab.UNIT_ATTR/AI_ATTR or WEAPON_ATTR members. Preserve order and duplicates. Harvesting a tag from a mod does not verify a new builder proposal. |
| Custom weapon/unit effects | hook_drag, hook, rend, stagger, duelist/duel, pikebreaker, batter, crush, hemorrhage, hamstring, cleave, linebreaker, stalwart and unknown proposals remain metadata. No hook alias conversion. No runtime-support switch exists in v1. |
| Existing unknown source tags | Remain owned by normal native patching. Omitted list columns do not edit them. Selecting a full list replacement is explicit; this helper does not merge source lists automatically. |
| sp | Upstream calls it native; toolkit WEAPON_ATTR does not. Stop on supporting new sp output pending the concrete question in the audit/handoff. It is retained as metadata now. |
| Terrain choices | desert_raider/forest_ambusher are inputs for sand/forest calculations, never native attribute tokens. The calculator must consume them before projection. |
| Morale lock, heat, mass, armor sound, health, secondary armor, extra weapon tuple members | Engine-shaped fields exist, but not all have sheet columns. Do not invent sheet targets or put them into arbitrary extras as staged edits. Later integration must extend the shared typed registry or use the existing reviewed native editor path. |
| Runtime proposals | Campaign Mounted, Bloc, Raider, Engineer/Garrison automation, secondary dynamic defense, projectile accuracy, mount movement/geometry, custom effects and mercenary armor/weapon extensions are metadata until independently verified. |
| Recruitment | Sheet classifications and existing balance project/rules remain authoritative. Mercenary planning uses existing pools, regions and gates in 107. Never silently add EDB recruitments or fork edb_balance/sheet_pipeline. |

The README and UI notices say custom effects are metadata; the pinned
`reforged.js:exportableAttrs` nevertheless permits CUSTOM_TAG and hook and
rewrites hook_drag to hook. The commit subject confirms this is revision drift,
not a missing local update. ROADMAP explicitly requires metadata without
verified runtime support. That requirement governs this boundary. The upstream
test runner references older strict-export assertions; those are source
evidence, not a passing test report. Upstream tests were never executed.

Stop on the following formula/export decisions before implementing those items:

- Guards: generated help and audit_rules say +2 Skill, final combat_rules says
  +1. Which profile rule is intended: final +1, or an intentional +2 deviation?
- sp: keep metadata pending runtime evidence, or approve adding it to shared
  vocabulary after that evidence? This phase does not enable it.
- Upstream entered costs: preserve pre-grade inputs, or convert them into final
  native pins? Both are representable below; the 105 adapter must not guess.

These are item-level stops. No disputed arithmetic or new tag support is
implemented in 102. Questions and both outcomes are also recorded as data.

## Native design and project schema

`unittransfer.builder_contract` is a pure Python boundary for future callers.
It is deliberately not imported by the app. ContractError contains internal
codes; a future UI must add localized messages before exposing them.

A complete packet has exactly these keys:

```json
{
  "schema": "m2-unit-design",
  "version": 1,
  "profile": {"id": "native", "revision": "1"},
  "inputs": {"category": "infantry", "hide_forest_override": false},
  "presets": {},
  "overrides": {"inputs": {}, "native": {"attack": 0}},
  "metadata": {}
}
```

- `inputs` holds original design choices, using the upstream form field shapes
  where applicable: unit_category, quality, equipment_grade, category, class,
  trait_* booleans, pri_*/sec_* weapon inputs, armour_base/weight/layer1-3,
  offhand/shield inputs, horse_type/origin/barding, origin/climate_heat,
  terrain_specialty, f_* formation values, bible_formation_auto,
  hide_forest_override and unit_tag_* terrain choices, costs and merc_* settings.
  No engine fields are inferred from the spelling of an input key. Inputs and
  custom preset objects are JSON-only, not yet semantically accepted calculator
  inputs. 103 must validate selected profile IDs/ranges/eligibility before
  evaluating; unknown input keys remain dormant and cannot become output fields.
- `presets` stores edited preset snapshots keyed by family then ID; changed
  presets do not overwrite original baseline inputs or explicit pins.
- `overrides.inputs` is a flat key replacement applied before calculation by
  effective_inputs(). Key presence, including zero/false/empty string, is
  intentional. Remove a key to resume inheritance. Never infer an override by
  comparing its numeric value to the current default.
- `overrides.native` pins final shared column values after calculation. It
  survives recomputation, grade changes, preset changes and JSON round trips.
  Native pins still pass the same type and unsupported-attribute boundary.
  None is refused; omission means no selected output; [] explicitly clears a
  list. A calculator's unavailable result must be an issue, never zero/None.
- `metadata` retains unknown non-executable JSON, original upstream fields and
  cached unit, design-only effects, notes, migration decisions and provenance.
  Unknown top-level keys/new versions are refused, not silently discarded.
  All objects have string keys, finite numbers, maximum depth 32 and packet
  JSON size at most 1,000,000 ASCII-encoded characters. No eval or scripts.

Portable design packets contain no second unit identity or classifications.
For an existing unit, attach_design(mod, project, uid, packet) returns an
unsaved copy at `project.units[uid].builder_design`, using exact live EDU type
ID through unit_sheets.live_units. Case, whitespace and localized-name guesses
are refused. It preserves annotations, extras, drafts, rules, views, recipes,
groups, balance profile and source signatures. The surrounding project remains
`m2-unit-sheets` version 1 and uses its existing per-mod config path, revision,
source-token and undo/redo contracts. No extra store or mod comment is needed.
An attachment alone does not stage stats. The normal sheet project validator
currently preserves this extension but does not validate its inner packet;
future builder readers must call validate_design explicitly.

For a new unsaved design, retain the detached packet until 106 plans a donor
clone and resolves a unique live type/dictionary/localization identity through
the existing creation workflow. Do not fake an existing sheet row. Never
reconstruct original inputs from EDU. When no packet exists, show native donor
values and explicitly initialize a new design only on user request.

## Calculation and output boundary for 103

103 consumes effective_inputs plus explicit profile/preset data and returns
calculated native column values separately from explanation and design metadata.
It must not mutate the design or cache derived values over the input packet.
Pass only its native dictionary to output_values(design, calculated_native).
The return is `{native: <typed columns>, metadata: {omitted: <tags by column>}}`.
Keep omission records with the original design metadata; this result never
replaces the saved design. Repeated projection is deterministic.

native_mapping() reflects sheet_ops.FIELDS directly, not a copied map. It
covers category/class, size/movement, primary attack/charge/projectile/range/
ammo/delay, secondary attack/charge/delay, armor/defense/shield, mental values,
costs, attribute lists, formation, terrain, mount effects and recruit priority.
The shared member_index handles optional gunpowder firing effects. No output
can create classifications, models, arbitrary EDU directives or recruitment
fields by submitting an unknown column name. Whole output field validation
finishes before callers can stage anything.

In 106, selected native values must become cells for sheet_ops.stage_cells,
with the sheet service's current revision/source checks, preview and explicit
confirmation. Use sheet_ops.field_changes and existing EDU edit planners;
retain every unselected tuple member, comment and unknown source field. Save
the packet through the existing project history so reopen/undo retains pins.
No automatic staging is provided by 102. This is a contract test, not an
implementation of 106's UI, Apply, backups or Undo.

Arithmetic audit for 103: preserve the effective wrapper order, positive-term
clamps and the Aggressive exception; only the defending weapon adds handling
and offhand; grade does not create armor/shield from nothing; horse barding is
counted once and not graded; layers add once; ranged quality differs from
melee and Hybrid; hiding false survives save/reopen; terrain and formation
follow the explicit weight and manual-formation state. Costs apply Hybrid
rounding before grade rounding. JS Math.round has different half behavior from
Python round, so test rounding boundaries explicitly. Source explanations of
delay units, accuracy, health/auto-resolve, AP rounding, mounted behavior and
conditional effects are not independent engine verification.

## Checked examples and limits

tests/fixtures/builder_contract.json contains six synthetic complete design
packets and expected output-boundary goldens: infantry, missile with defending
secondary, cavalry barding, suppressed two-handed offhand, grade with pinned
zero attack, and explicit hiding opt-out. All rows, values and custom presets
are invented, not copied upstream designs or user data. Calculated packets
are supplied by the tests; they do not claim an implemented calculation engine.

tests/test_builder_contract.py checks each golden, strict schema/profile/type
failures, durable input and final pins, custom/unknown export filtering, shared
mapping, exact live identity, annotation/extra preservation, JSON reopen and
nonmutating staging through the real sheet_ops and EDU parser. The fixture EDU
exists only in memory. No installed mod, original workbook or upstream script
is opened for execution. Formula parity, upstream project migration, browser
interactions, Apply/Undo and in-game effects remain unverified and outside 102.
