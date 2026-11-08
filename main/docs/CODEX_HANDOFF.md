# Codex change handoff

Newest entries first. This records Codex's work for Claude; project status and
release rules remain in STATE.md and RELEASE.md. Do not assume the working tree's
other changes belong to Codex.

## 2026-11-08 - Phase 104: guided designer and editable presets

Exit checklist against Phase 104's own exit line:

- DONE in Node VM interactions and fixture-only Python service tests: infantry,
  missile, cavalry and two-handed designs recalculate and show base stats,
  costs, contribution explanations, engine upgrade notes and read-only EDU.
  Real browser interaction and layout have not been verified.
- DONE: preset and grade changes retain explicit input overrides, false/zero
  values, final native pins and edited snapshots. Reset affects only the chosen
  preset. Role eligibility is explained without silently changing the design.
- DONE: shared Ctrl+Z/Ctrl+Y and visible Undo/Redo restore design packets.
  Saving/reopening preserves the packet for an exact existing unit or a detached
  New unit draft. Native values do not acquire a balance profile automatically.
- DONE: previews and saves do not stage stats or write installed mod files.
  There is no designer Apply route. Phase 106 remains responsible for Apply.

Changes and why:

- The Unit Editor has a Guided designer tab; New unit offers the same designer.
  It uses the existing modal, form patterns, translation helpers and undo scopes.
  Opening shows donor values and requires an explicit native or Combat Reforged
  profile choice when no design exists. Existing editor edits remain separate.
- Controls cover archetypes/subtypes, quality/grade, both weapons, armor
  ensembles/base/layers, offhand/legacy shields, mounts, grouped unit/weapon/
  terrain attributes, hiding/formation, manual inputs and final stat pins.
  Editable profile rows retain their original defaults separately from patches.
  Loadout arrangements select base/layer profiles; edit their numbers through
  those families. Non-calculated preset properties remain design data.
- Every text oninput updates only dependent results/status, eligibility or
  filtered preset choices/fields. It never replaces that text control or the
  form. A request sequence rejects stale previews. Error replies are checked
  explicitly because this app's api.post returns server error objects.
- POST /api/builder/load, /preview and /save reuse the Phase 102 packet, 103
  calculator, shared sheet field mapper and EDU editor. Saves use the sheet
  project lock, revision/source checks and atomic config writer. Attachments
  use units[exact_id].builder_design; builder_new_design holds one detached
  draft per mod. No fictional sheet row or separate project store is created.
- EDU is a projection of supported base columns, not a complete new-unit plan.
  Donor comments and untouched tuple members remain; missing fields and detached
  designs use preview placeholders. Weapon runtime tuple members, models,
  localization and prerequisites still require Phase 106's reviewed planner.
  Upgrade previews remain metadata, with the existing unit-card +1 caveat beside
  values and configuration sources. Guards and grade rules are unchanged.
- Malformed/stale saves leave config intact. Failed previews clear old results;
  failed saves retain the working design. A save response does not replace the
  current packet, preserving edits made while it was in flight. Unknown snapshot
  keys remain data and cannot create inline preset-editor handlers.
- Closing the modal deactivates the designer undo scope and invalidates pending
  preview replies. Card-coverage warning rendering was not changed.

Affected files:

- `unittransfer/builder_designer.py`
- `unittransfer/server.py`
- `web/js/builder.js`
- `web/js/editor.js`
- `web/js/settings.js`
- `web/js/undo.js`
- `web/js/core.js`
- `web/index.html`
- `web/i18n/en.json`
- `tests/test_builder_designer.py`
- `tests/test_builder_designer_ui.js`
- `docs/CODEX_HANDOFF.md`

Tests first and checks actually run:

- Initial Python run, before implementation: all 6 new tests ERROR with missing
  builder_designer ImportError. Initial Node run failed ENOENT for builder.js.
- Additional tests before their fixes: the first assertion failure was false
  hiding after redraw; tightening the grip assertion then exposed the inherited
  two-handed grip failure. The same pre-fix group also covered automatic
  formation, blank-category inheritance and editing overridden selections;
  those assertions were reached and passed after the fixes, not separately
  recorded as initial failures. Sparse donor preview failed on a missing shared
  tuple member. The preset-filter test first failed because visible selection
  and edited row disagreed. All now pass.
- Harness corrections: used shared field extraction instead of a nonexistent
  Unit.attack property; tightened the checkbox assertion so this.checked in a
  handler cannot masquerade as a checked HTML attribute. Sandbox Windows temp
  folders denied child writes; the untracked .tmp/run_phase104.py runner supplies
  workspace scratch directories with mode 0777 through tempfile.mkdtemp. It
  changes no production code or existing test assertions. UT_NO_BROWSER=1.
- `python .tmp/run_phase104.py unittest tests.test_builder_designer
  tests.test_builder_calculator tests.test_builder_contract
  tests.test_card_coverage tests.test_unit_sheets`: 89 tests PASS (8 new service
  tests, including HTTP route/error checks). Synthetic fixtures only.
- `python .tmp/run_phase104.py tests.test_web_modules`: 130/130 PASS.
- `python .tmp/run_phase104.py tests.test_i18n`: 45/45 PASS.
  Initial catalogue/lint failures were missing Back, technical enum literals,
  attribute-only markup fragments and one generated unused label; corrected.
- `node tests/test_builder_designer_ui.js`: PASS. Uses rendered handlers and the
  real shared undo stack. Tests four roles, defaults, overrides/reset, filter
  identity, false/zero, save/reopen, exact editor ID, stale previews, rejected
  replies, escaping and no Apply/stage request.
- `node tests/test_card_coverage_ui.js`: PASS after generating its existing
  .tmp/cards_strings.json prerequisite from en.json. First attempt failed
  ENOENT for that scratch fixture; the test itself was not changed.
- `node tests/test_unit_sheets_ui.js`: PASS, including request queues/history.
- `git diff --check`: PASS. No new em dash, dependency, other catalogue edit,
  STATE/ROADMAP/ROADMAP_ARCHIVE edit, commit, tag, build or release.

Human browser checks still needed:

- Walk all four examples from Unit Editor and New unit; inspect narrow layout,
  keyboard navigation, details sections, caret/selection/IME and scroll behavior
  during numeric, attribute, preset and filter typing. VM tests do not model
  native focus, accessibility, rendering or the editor's WebGL column.
- Save, close and reopen both draft targets; try Ctrl+Z/Ctrl+Y, explicit zero and
  hiding false, suppressed offhand/layers, slow/failed requests and a second
  window changing the project. A stale save keeps local edits but requires
  resolving the project conflict before saving. No conflict merge UI is added.
- Verify displayed vanilla, EOP and M2EX upgrade sources against the chosen mod
  read only. No installed mod or engine execution was tested in this run.

Open questions and limits:

- No new mod-writing decision was made or reopened. sp remains quarantined;
  no calculator, rule data, engine formula or shared output vocabulary changed.
- Existing identity/source classification, Apply, portable import/export and
  donor creation remain Phases 105/106. Draft saves are config-only; undo/redo
  is the existing in-session snapshot history, not the transfer Log's disk Undo.
- One detached draft is stored per mod. Unsaved edits survive a return to the
  same designer in this browser session; switching to a different target can
  replace that unsaved working copy. Save before switching targets or reloading.
- Usage checks: first telemetry was 46% five-hour used, then 51% used at
  2026-11-08 06:28:44 UTC. Repeated direct account requests failed with URLError;
  later telemetry reads still returned that timestamp. Current live remaining
  usage is unavailable, so the 90%-used cutoff cannot be claimed continuously.
  No credits, resets or other runs were started.
- Work is uncommitted. Existing TWCenter index deletions, Reference.lnk,
  .tmp, dev/report-relay/.wrangler and docs/CHATGPT_INTRO.md predate this task
  and were not treated as task changes. Scratch logs/runner were added in .tmp.

New English catalogue IDs (451, en.json only):

<details>
<summary>Full Phase 104 ID list</summary>

```text
builder.title
builder.preview_only
builder.choose_profile
builder.native_profile
builder.reforged_profile
builder.undo
builder.redo
builder.save_draft
builder.inherited
builder.inherit
builder.final_pins
builder.pin_help
builder.identity
builder.weapons
builder.equipment
builder.mounted
builder.attributes
builder.overrides
builder.edit_presets
builder.preset_family
builder.filter_presets
builder.reset_preset
builder.reset_help
builder.grade_help
builder.subtype_help
builder.weapon_help
builder.layer_help
builder.mount_help
builder.attribute_help
builder.role_ineligible
builder.mounted_ineligible
builder.engineer_ineligible
builder.hybrid_help
builder.royal_help
builder.invalid
builder.save_failed
builder.saved
builder.unsaved
builder.calculated
builder.contributions
builder.upgrades
builder.design_metadata
builder.edu_view
builder.edu_help
builder.pinned_result
builder.entry
builder.entry_help
builder.label_africa
builder.label_anatolia
builder.label_average
builder.label_byzantine
builder.label_career_soldiers
builder.label_cuman_mongol
builder.label_eastern_european
builder.label_emergency_levies
builder.label_exceptional
builder.label_household_soldiers
builder.label_iberia
builder.label_inferior
builder.label_ireland_highlands
builder.label_italian
builder.label_martial_nobility
builder.label_middle_east_persia
builder.label_outstanding
builder.label_royal_retinue
builder.label_rural_militia
builder.label_scandinavian
builder.label_superior
builder.label_urban_militia
builder.label_wales
builder.label_warrior_levies
builder.label_western_european
builder.label_aggressive
builder.label_agi
builder.label_ammo
builder.label_applicable
builder.label_arbalest
builder.label_archetype
builder.label_archetype_training
builder.label_archetypes
builder.label_arm
builder.label_arm_agi
builder.label_arm_heat
builder.label_arming_doublet
builder.label_arming_sword
builder.label_armor
builder.label_armor_upgrade_cost
builder.label_armour
builder.label_armourbonus
builder.label_armour_base
builder.label_armour_layer1
builder.label_armour_layer2
builder.label_armour_layer3
builder.label_armour_sound
builder.label_armour_upgrade_armour
builder.label_armour_upgrade_level
builder.label_armour_upgrade_points
builder.label_armour_weight
builder.label_artisan
builder.label_atk
builder.label_atk_tr
builder.label_attack
builder.label_attack_delay
builder.label_attr
builder.label_attributes
builder.label_attrs
builder.label_automatic
builder.label_axe
builder.label_back_strapped
builder.label_barding
builder.label_base
builder.label_baseline
builder.label_bible_formation_auto
builder.label_bill
builder.label_bonus
builder.label_bow
builder.label_brawler
builder.label_breast_plate
builder.label_breed
builder.label_brigandine
builder.label_brigandine_late
builder.label_buckler
builder.label_camel
builder.label_can_sap
builder.label_cataphract
builder.label_category
builder.label_cav_style
builder.label_cavalry
builder.label_cavalry_style
builder.label_cdist
builder.label_chain
builder.label_charge
builder.label_charge_mounted
builder.label_charger
builder.label_class
builder.label_climate
builder.label_close_front
builder.label_close_side
builder.label_coat_cloth
builder.label_coat_of_plates
builder.label_common
builder.label_composite_bow
builder.label_core
builder.label_core_defense_skill
builder.label_cost_construct
builder.label_cost_custom
builder.label_cost_upkeep
builder.label_couched_lance
builder.label_courser
builder.label_crossbow
builder.label_culture
builder.label_custom_cost
builder.label_custom_limit
builder.label_custom_stacking
builder.label_dagger
builder.label_def
builder.label_def_tr
builder.label_default
builder.label_defense
builder.label_delay
builder.label_delay_mounted
builder.label_destrier
builder.label_discipline
builder.label_dmg
builder.label_double_mail
builder.label_eastern_europe
builder.label_elephant
builder.label_empty
builder.label_engine_rules
builder.label_equipment_grade
builder.label_estoc
builder.label_extra_attrs
builder.label_f_cf
builder.label_f_cs
builder.label_f_lf
builder.label_f_ls
builder.label_f_ranks
builder.label_f_types
builder.label_falchion
builder.label_false
builder.label_fanatic
builder.label_fighting_spear
builder.label_firearm
builder.label_floor
builder.label_foot_quality
builder.label_foot_spear
builder.label_forest
builder.label_formation
builder.label_formation_types
builder.label_full_plate
builder.label_gaelic
builder.label_gambeson
builder.label_glaive
builder.label_gothic_plate
builder.label_grade
builder.label_grade_multiplier
builder.label_grades
builder.label_great_sword
builder.label_greatsword
builder.label_guards
builder.label_halberd
builder.label_half_mail
builder.label_half_plate
builder.label_handling
builder.label_heat
builder.label_heat_mounted
builder.label_heater
builder.label_heavy
builder.label_heavy_couched_lance
builder.label_heavy_lamellar
builder.label_heavy_scale
builder.label_height
builder.label_held
builder.label_hide_forest_override
builder.label_high
builder.label_hobby
builder.label_horse
builder.label_horse_barding
builder.label_horse_origin
builder.label_horse_type
builder.label_horseman_axe
builder.label_horseman_mace
builder.label_horseman_sword
builder.label_hybrid
builder.label_hybrid_divisor
builder.label_hybrid_rounded
builder.label_iberian
builder.label_id
builder.label_infantry
builder.label_inherit
builder.label_input
builder.label_italian_plate
builder.label_javelin
builder.label_kataphract
builder.label_kite
builder.label_knife
builder.label_lamellar
builder.label_lamellar_light
builder.label_lamellar_med
builder.label_lance
builder.label_lancer
builder.label_large
builder.label_late_full_plate
builder.label_layers
builder.label_leather
builder.label_leather_jerkin
builder.label_legacy
builder.label_leine_croine
builder.label_light
builder.label_light_couched_lance
builder.label_light_crossbow
builder.label_loadouts
builder.label_lock_morale
builder.label_long_axe
builder.label_long_bow
builder.label_long_sword
builder.label_longaxe
builder.label_longsword
builder.label_loose_front
builder.label_loose_side
builder.label_mace
builder.label_mail_haubergon
builder.label_mail_lamellar
builder.label_mail_light
builder.label_mail_med
builder.label_mail_surcoat
builder.label_mail_voiders
builder.label_mass
builder.label_medium
builder.label_metal
builder.label_middle_east
builder.label_missile
builder.label_mongol
builder.label_moor
builder.label_morale
builder.label_morale_baseline
builder.label_mount
builder.label_mountclass
builder.label_mount_effect
builder.label_mountedatkpenalty
builder.label_mounted_crossbow
builder.label_mounted_heavy_recurve_bow
builder.label_mounted_javelin
builder.label_mounted_quality
builder.label_mounted_recurve_bow
builder.label_mounted_short_bow
builder.label_mounted_spear
builder.label_movement
builder.label_munition
builder.label_name
builder.label_nomount
builder.label_none
builder.label_offhand
builder.label_offhands
builder.label_origin
builder.label_origin_weight
builder.label_override
builder.label_padded
builder.label_params
builder.label_pavise
builder.label_pick
builder.label_pike
builder.label_plate
builder.label_plate_lamellar
builder.label_pole_axe
builder.label_poleaxe
builder.label_pony
builder.label_poor
builder.label_pre_grade
builder.label_pri
builder.label_pri_ammo
builder.label_pri_attr
builder.label_pri_attributes
builder.label_pri_base_atk
builder.label_pri_base_charge
builder.label_pri_category
builder.label_pri_delay
builder.label_pri_handling
builder.label_pri_heat
builder.label_pri_missile
builder.label_pri_preset
builder.label_pri_range
builder.label_pri_twohand
builder.label_primary
builder.label_profile
builder.label_projectile_accuracy
builder.label_puffed_cloth
builder.label_quality
builder.label_radius
builder.label_range
builder.label_ranks
builder.label_reckless
builder.label_recruit
builder.label_recruit_cost
builder.label_recruit_priority
builder.label_recruit_turns
builder.label_reinforced
builder.label_reinforcing
builder.label_ren_3q_plate
builder.label_ren_half_plate
builder.label_result
builder.label_roles
builder.label_rouncy
builder.label_round
builder.label_sand
builder.label_scale_light
builder.label_scale_med
builder.label_scandinavia
builder.label_scrub
builder.label_sec
builder.label_sec_ammo
builder.label_sec_attack
builder.label_sec_attr
builder.label_sec_attributes
builder.label_sec_base_atk
builder.label_sec_base_charge
builder.label_sec_category
builder.label_sec_charge
builder.label_sec_delay
builder.label_sec_handling
builder.label_sec_heat
builder.label_sec_missile
builder.label_sec_preset
builder.label_sec_range
builder.label_sec_twohand
builder.label_secondary
builder.label_selection
builder.label_self_bow
builder.label_shield
builder.label_shield_mat
builder.label_shield_material
builder.label_shield_type
builder.label_short_sword
builder.label_siege
builder.label_size_cav
builder.label_size_inf
builder.label_skirmish
builder.label_small
builder.label_snow
builder.label_soldier_count
builder.label_soldier_quality
builder.label_sound
builder.label_source
builder.label_spear
builder.label_spearmen
builder.label_specialty
builder.label_speed
builder.label_staff
builder.label_stallion
builder.label_stamina
builder.label_stat
builder.label_status
builder.label_subtype
builder.label_subtypes
builder.label_surcoat
builder.label_sword_cut
builder.label_sword_thrust
builder.label_tech
builder.label_terms
builder.label_terrain
builder.label_terrain_choice
builder.label_terrain_heavy
builder.label_terrain_light
builder.label_terrain_med
builder.label_terrain_specialty
builder.label_third_layer
builder.label_thrown
builder.label_training
builder.label_trait_aggressive
builder.label_trait_bloc
builder.label_trait_command
builder.label_trait_engineer
builder.label_trait_fanatic
builder.label_trait_garrison
builder.label_trait_guards
builder.label_trait_hybrid
builder.label_trait_mercenary
builder.label_trait_mounted
builder.label_trait_raider
builder.label_trait_reckless
builder.label_transitional
builder.label_true
builder.label_twohand
builder.label_unarmored
builder.label_unit_category
builder.label_unit_custom_attrs
builder.label_unit_size
builder.label_unit_tag_desert_raider
builder.label_unit_tag_forest_ambusher
builder.label_upkeep
builder.label_value
builder.label_verified
builder.label_war_bow
builder.label_war_knife
builder.label_weapon
builder.label_weapon_categories
builder.label_weapon_category
builder.label_weapon_handling
builder.label_weapon_upgrade_attack
builder.label_weapon_upgrade_cost
builder.label_weapon_upgrade_level
builder.label_weapon_upgrade_points
builder.label_weight
builder.label_western_europe
builder.label_wooden
builder.label_wtype
builder.back
builder.label_armour_preset
builder.load_failed
builder.loadout_help
builder.no_presets
```

</details>

## 2026-11-08 - Phase 103: deterministic calculator and explicit rules data

Exit checklist against Phase 103's own exit line:

- DONE: calculator/golden tests pass for implemented rules, including the
  pinned source grade matrix, foot/mounted quality matrix, ranged/Hybrid/culture
  goldens, defending slot, signed offhand, layers and horse-only barding.
- DONE: inputs and selected preset snapshots do not mutate; final pins remain
  separate from calculation. Input and engine-rule copies are returned safely.
- DONE: repeated evaluations, including JSON reopen, agree.
- DONE: unsupported fields cannot leak into EDU. Calculated output and final
  pins use the 102 output boundary and existing shared sheet types/field map.
  Game-invalid sp and spear_bonus_2 stay quarantined; fire is accepted.
- DONE: no game files written. Calculator execution is tested with builtins,
  Path and OS file access forbidden. EOP reading uses a synthetic Lua fixture.
  No installed mod was read or modified. No upstream script was executed.
- DONE: Guards subtype arithmetic resolved by the user's 2026-11-08 decision:
  +2 Defense Skill from builder help, -1 melee Attack and disciplined-only +1
  morale. Final upstream +1 Skill is a documented deliberate difference.
  UI is not required for Phase 103 and was not added.

Changes and files:

- unittransfer/builder_calculator.py: isolated pure calculation, semantic checks,
  selected editable snapshots, effective input overrides, deterministic JS
  rounding, contribution traces, typed native projection and separate metadata.
  Read-only load_engine_rules handles literal EOP settings and mod-local M2EX
  descr_caps_ex.txt integers with source lines; a mod entry selects M2EX via m2ex.
- unittransfer/builder_rules.json: pinned effective literal rule tables and
  attribution, plus vanilla/EOP/M2EX per-engine default records. No dependencies.
- unittransfer/builder_contract.py: existing output quarantine now also excludes
  spear_bonus_2 and accepts fire. sp always remains excluded. Existing native
  editor suggestions/source preservation were not changed.
- tests/test_builder_calculator.py: 22 tests using synthetic designs and manually
  transcribed source regression expectations. Uses real shared field_changes
  and EDU parser for output verification, with no alternate stat pipeline.
- tests/fixtures/builder_eop/eopData/eopScripts/luaPluginScript.lua: synthetic
  1/1 configuration plus inert comment/string lookalikes, read only in tests.
- tests/fixtures/builder_m2ex/{both,one,none,negative}/data/descr_caps_ex.txt:
  synthetic plain-text settings for independent defaults and negative clamps.
- tests/test_i18n.py: recognizes builder reply message descriptors across all
  engine slots, verifies their English catalogue IDs and parameter sets. This
  permits English-only catalogue text without duplicate Python fallback prose.
- web/i18n/en.json: two notes only. No other catalogue or dev/i18n file edited.
- docs/BUILDER_RULES.md: API, input precedence, table/formula provenance, rounding,
  deliberate source differences, upgrade semantics and Guards decision. Historical
  docs/UNIT_BUILDER_CONTRACT.md has a short superseding-decision pointer.
- docs/CODEX_HANDOFF.md: this entry. STATE.md, ROADMAP.md and ROADMAP_ARCHIVE.md
  were not edited. Existing TWCenter index deletions and untracked files predate
  the task and remain untouched.

Rules and sources:

- Source d4ed9368d0db3da2000bc895e96f52a83b93cb67, lupinemaverick, based on MUG
  Unit Builder v1.5 / MUG Unit Creation Guide, Combat Reforged work for King
  Siegfried. User reported author permission; no new license inferred. Verified
  every cached source hash against SSR_BUILDER_AUDIT.json before extracting
  literal tables as data. Never imported/executed upstream scripts or tests.
- Archetypes: generated build.py identities, then audit/r2 fixes. Quality:
  audit_rules.js then combat_rules.js. Independent grade: equipment_grade.js.
  Weapons: base and reforged category tables, audit mounted/sword corrections,
  r2 Attack/handling, preset_filters knife normalization, armor_loadouts lance
  cleanup, weapon_phase_a final bill/greatsword proposal changes. Armor/layers,
  shields, horse data: base plus those effective wrappers. Terrain/formation:
  audit_rules.js; hiding and +2 terrain choices: unit_attribute_controls.js.
  Exact source/value mapping is in BUILDER_RULES.md and literal values in JSON.
- Entered recruit/upkeep inputs are pre-grade, including overrides.inputs.
  Hybrid recruit rounding precedes grade rounding. Native pins remain final.
- weapon_upgrade_attack default 3, armour_upgrade_armour default 2: per-engine
  rules data, source engine_default, matching documented EOP API defaults.
  A single literal setting call in eopData/eopScripts/luaPluginScript.lua
  replaces each value independently and records its relative path and line.
  No Lua execution or expression interpretation. Comments/strings ignored;
  duplicates, nonliteral/invalid arguments retain defaults with status.
  Observed configuration is not proof a conditional branch ran in game.
- M2EX defaults are verified 3/2 using the source findings supplied by the user.
  Its mod-local data/descr_caps_ex.txt keys weapon_upgrade_points and
  armour_upgrade_points override independently; negative integers clamp to 0.
  Each value reports engine_default or the relative file and line, verified true,
  and default/literal_config/clamped_config status. No EOP or parent fallback.
  Vanilla uses fixed 3/2. Vanilla/M2EX missile, thrown and siege-missile attacks
  receive no weapon bonus. EOP behavior is unchanged. Only the M2EX missile
  switch's configuration key remains unverified, so that switch stays off.
  Upgrade levels affect metadata preview only, preserving base EDU. Notes carry
  modifier parameters and the unit card's +1 display caveat. No UI was added.

Tests first and checks actually run:

- Wrote the initial 11 tests before the calculator/data implementation. First
  run: all 11 ERROR with missing builder_calculator ImportError. Additional
  tests were added before their fixes: ranged category/none secondary failed
  with preset_id; eligibility did not reject; compound formations failed typed
  output validation; fire was omitted; descriptor notes were missing; malformed
  selected snapshot data raised AttributeError/TypeError/IndexError instead of
  ContractError; shared wedge vocabulary was rejected. All now pass.
- Corrected test setup/expectations during the first implementation run: default
  unarmored agility and wooden shield Skill contributions were not neutral,
  self_bow is the source ID, preset role needs missile class, mounted Attack
  sum is 7, Iberian medium sand is -2, and parsed EDU fields use fields_of.
  These corrections are not claimed as upstream calculator defects.
- Initial test temporary-directory use hit this sandbox's Windows mode-0700
  ACL issue. Replaced the new test's runtime temporary Lua folder with the
  checked-in synthetic fixture. The first inaccessible empty tmpemasnmt0 under
  the system temp directory was not removed or permission-modified.
- Final Python group: 103/103 pass: calculator 19, builder_contract 6,
  unit_sheets 36, sheet_ops 42. UT_NO_BROWSER=1. Existing fixture-heavy tests
  ran with a process-only os.mkdir 0700-to-0777 workaround and a workspace temp
  root, as in 102, without changing their production code.
- tests.test_web_modules: 130/130 pass, including Node parsing of 110 modules
  and combined load order. tests.test_i18n: 45/45 pass, including Node runtime
  and fixture HTTP checks. Initial i18n run was 44/45 because its scanner did
  not recognize the two message descriptors; coverage now checks the actual
  helper output/parameters. Direct loopback opener avoids the refused proxy.
  No new Node tests were added, and no upstream Node test was run.
- git diff --check passed. Added/changed text checked for trailing whitespace
  and U+2014. Existing en.json contains earlier em dashes; those were left
  untouched and no new text adds one. Test logs/helper scripts are in .tmp;
  they are scratch, not proposed repository files.

New string IDs (English catalogue only):

- builder.upgrade_card_note
- builder.m2ex_missile_unverified (replaces builder.m2ex_unverified)

Resolved Guards question and remaining limitations:

- Guards is a trait_guards subtype Defense Skill contribution in build.py,
  audit_rules.js and the final r2 skill breakdown, not an armor-upgrade value.
  The user resolved the earlier +1/+2 stop on 2026-11-08: use +2 from builder
  help, deliberately differing from final r2 +1. Neutral core4 becomes Skill6.
  Guards subtracts 1 from melee Attack only and adds 1 morale only with final
  disciplined discipline. It does not change discipline or use armor upgrade
  modifiers. The selection stop has been removed; see follow-up below.
- The M2EX missile-switch file key remains unverified; upgrades stay off for
  missile attacks. Installed DaC EUR literal 1/1 was not independently read; only
  fixture 1/1 is verified. Battle behavior, EOP branch execution and
  upstream browser parity are not verified. Heat, armor sound, morale lock and
  compound formation types stay engine-shaped metadata where shared sheets
  lack the appropriate field shape. UI, migration and Apply/Undo remain later
  phases. Unknown proposals and conditional effects have no runtime claim.

Commit/release status: HEAD remains b934e831; no commit, tag, build or release.
Live account-event usage checks: five-hour 13%, 17%, 20%, 22%, 25%, 28%, 29%, 30%, 32%, 34% used,
below this builder track's authorized 90%-used stop. Weekly usage is not the
guard. Final check: 66% remaining. No credits spent or limits reset.

Final checkout observation: changes to unittransfer/edit.py and web/js/editor.js
and untracked tests/test_card_coverage.py / tests/test_card_coverage_ui.js appeared
after the initial status check. This run did not edit those files and leaves
them untouched. Repeated web checks pass 130/130 against the current checkout. The
builder tests also reject malformed armor identity/sound types with ContractError
after first recording their TypeError failures. Final Python group remains
103/103 passing after those fixes.

Final i18n rerun on the externally changed checkout: 43/45, after two earlier
45/45 passing runs. Failures are missing editor.missing_card_fallback,
editor.missing_card_generic, editor.missing_info_card, editor.missing_info_generic
and editor.missing_unit_card, plus the related faction parameter check at
web/js/editor.js:748. Those references came from the editor/card work this run
did not make. Both Phase 103 builder descriptors are present and their parameters
pass. No attempt was made to rewrite or complete another contributor's work.
Thus the final current-checkout i18n result is FAILED, not a claim of 45/45 at
finish. Re-run it when the separate card strings are supplied. All five Phase
103 exit items above remain verified; this unrelated i18n regression is a
remaining checkout limitation.

Follow-up on 2026-11-08: M2EX verification completed within this Phase 103 entry.

- Used the user's supplied M2EX source findings, not an installed mod or game.
  Added fixture tests first. Initial run: 22 tests, 13 assertion failures and
  1 error demonstrating missing M2EX parsing/flag support and missile filtering.
  During implementation, corrected Path.root being mistaken for a mod root;
  fixture paths now stay intact. No source repository citation added to comments.
- Changed this follow-up: unittransfer/builder_calculator.py,
  unittransfer/builder_rules.json, docs/BUILDER_RULES.md,
  tests/test_builder_calculator.py, four tests/fixtures/builder_m2ex files,
  web/i18n/en.json and this existing handoff entry. Other catalogue files,
  Guards behavior, edit.py, editor.js, test_card_coverage* and .tmp/cards_* untouched.
- Final requested checks with UT_NO_BROWSER=1: tests.test_builder_calculator
  22/22 and tests.test_builder_contract 6/6 pass; tests.test_web_modules
  130/130 pass; tests.test_i18n 43/45. The two failed i18n checks concern five
  missing editor IDs (missing_card_fallback, missing_card_generic,
  missing_info_card, missing_info_generic, missing_unit_card) and the related
  faction parameter check at editor.js:738, all in the other run's work.
  Builder note descriptors and parameters pass. Web/i18n used the existing
  process-only temp ACL workaround and direct loopback opener helper. Scratch
  logs: .tmp/phase103-m2ex-web.log and .tmp/phase103-m2ex-i18n.log.
- git diff --check passed. Fixture arithmetic and sources verified; battle
  execution and the missile-switch file key remain unverified. Guards remains
  stopped pending the existing +1/+2 decision, exactly as before.
- Live usage endpoint checks: five-hour 37% then 38% used, 62% remaining at
  the latest checkpoint, below this builder track's authorized 90%-used stop.
  Weekly usage is not the stop threshold. No credits spent or limits reset.
- No commit, tag, build or release performed. Changes remain uncommitted.

Follow-up on 2026-11-08: Guards resolved within this existing Phase 103 entry.

- User decision: "just use what the wiki says". Implemented builder index.html
  help's +2 Defense Skill, deliberately differing from final combat_rules.js +1.
  Added -1 Attack for each melee slot and +1 morale only when final discipline
  is disciplined. Guards leaves discipline unchanged; Reckless still makes it
  impetuous. Removed guards_skill_unresolved. Neighbouring subtype structure
  and contribution traces are retained; armor upgrades remain separate.
- Changed this follow-up only: unittransfer/builder_calculator.py,
  tests/test_builder_calculator.py, docs/BUILDER_RULES.md and this entry.
  No catalogue edits, dependencies, commits, tags, builds or releases. Left
  unittransfer/edit.py, web/js/editor.js and tests/test_card_coverage* untouched.
- Tests first: replaced the unresolved-stop expectation with two golden tests.
  Initial run: both tests failed with seven subcase errors, all the existing
  guards_skill_unresolved ContractError. After implementation, corrected golden
  Attack expectations for Emergency Levies' existing -1 training and ranged
  Average's melee-quality reduction; these were test setup corrections.
- Verified synthetic goldens: neutral core4 becomes Skill6; primary/secondary
  melee Attack drops by 1, missile Attack stays unchanged. Morale matches
  disciplined, normal, low, impetuous and Reckless cases. No game verification
  or upstream browser parity is claimed; existing limitations above remain.
- UT_NO_BROWSER=1: tests.test_builder_calculator 24/24 and
  tests.test_builder_contract 6/6 pass; tests.test_web_modules 130/130 pass.
  git diff --check passed. Changes remain uncommitted.
- Usage: current account events reported five-hour 40% then 41% used at start
  and checkpoint, below the authorized 90%-used stop. Weekly usage is not the
  stop threshold. No credits spent or limits reset.

## 2026-11-08 - Phase 102: source audit, profiles and data contract

- Exit items DONE: reviewed feature/module map, compatibility matrix, six
  synthetic sample projects, executable output contract and representative
  output-boundary golden cases. No app routes, controls, calculation engine or
  mod writes were added. Calculator parity is NOT verified and is Phase 103.
- Read ../AGENTS.md, the 102-108 roadmap block, archived 109-115 write-ups and
  the Phase 116 handoff (the archive has no separately headed 116 write-up),
  SHEET_INTERCHANGE.md and SSR_UNIT_BUILDER.md. Read the pinned upstream sources,
  tests and build.py as text only. GitHub commit metadata confirms revision
  d4ed9368d0db3da2000bc895e96f52a83b93cb67, 2026-10-15T18:36:06Z. The build
  script's replacements and module order matter; also audited its active
  weapon_controls.js and offhand_revision.js, absent from the earlier notes.
  No upstream script, build, test, macro or generated HTML was executed.
- Provenance: lupinemaverick; MUG Unit Builder v1.5 and MUG Unit Creation Guide;
  Combat Reforged work for King Siegfried. User reported author permission to
  reuse. No new license inferred. No upstream implementation/balance tables or
  actual unit/project rows copied. Source hashes are in the audit JSON.

Files and reasons:

- docs/UNIT_BUILDER_CONTRACT.md: effective source layering, complete feature map,
  compatibility matrix, profile/packet/project storage, output/staging ownership,
  override semantics, disagreements and unverified arithmetic for follow-on work.
- docs/upstream/SSR_BUILDER_AUDIT.json: pinned provenance and source hashes,
  machine-checked feature/module coverage and concrete item-level questions.
- unittransfer/builder_contract.py: isolated, pure schema/profile validation,
  input pins, typed output projection, shared field-map reflection and unsaved
  design attachment to an exact live sheet unit. No app imports this module yet.
- tests/test_builder_contract.py and tests/fixtures/builder_contract.json:
  synthetic infantry, missile/secondary-defense, cavalry/barding, two-handed,
  grade/final-zero-pin and hiding-opt-out project/output packets. They verify the
  contract with the real EDU parser, unit_sheets and sheet_ops, not copied
  arithmetic. Fixture EDU is in memory; calculated golden values are supplied
  inputs to this boundary, not a claim that a calculator produced them.
- docs/CODEX_HANDOFF.md: this entry. No other catalogues, STATE, roadmap or
  release files changed. Existing deleted TWCenter indices and untracked files
  predate this task and were left untouched.

Tests first and verification:

- Wrote all six new tests before implementation. First run:
  `UT_NO_BROWSER=1 python -m unittest tests.test_builder_contract`, six errors,
  all ImportError for the missing builder_contract module. Then implemented the
  module and artifacts; all six passed. No earlier passing implementation is
  claimed.
- Final Python run: 116/116 pass: builder_contract 6, unit_sheets 36, sheet_ops
  42, sheet_interchange 32. The first regression attempt had 184 setup/cleanup
  errors from 110 unreadable mode-0700 Windows temp directories. Retried using
  a workspace temp root and a process-only os.mkdir wrapper mapping 0700 to
  0777. No test or application implementation was modified for that workaround.
- tests.test_web_modules: 130/130 pass, including Node parsing of all 110 JS
  modules and their combined load order. It exits at import, so it was verified
  independently; the combined unittest invocation that imported it did not
  run the Python suite and is not counted as Python coverage.
- tests.test_i18n: 45/45 pass, including actual Node runtime and fixture HTTP
  checks. Initial attempts stopped on mode-0700 temp access, then the configured
  proxy's socket refusal. Final run used the same process-only temp workaround
  and urllib ProxyHandler({}) for direct loopback. No new Node test added.
- UT_NO_BROWSER=1 in verification. git diff --check has no whitespace errors;
  untracked new files also checked with git diff --no-index --check against
  /dev/null (ordinary new-file diff exit 1, no whitespace errors). New files
  checked for trailing whitespace and U+2014; none found. No dependency added.
- Successful fixture contents cleaned up; .tmp/phase102-tests is empty.
  Downloaded read-only upstream sources remain in .tmp/phase102-sources, and
  the four phase102 test logs plus empty phase102-source-sqi69245 remain in
  .tmp. Automatic command approval rejected both computed-path and explicit
  literal-path PowerShell cleanup with "blocked by policy"; no more specific
  reason was supplied. No alternate deletion route was attempted afterward.
  Cleanup of 110 empty temp directories from the first
  failed regression run plus two failed i18n directories was refused by Windows
  ACLs. Nonrecursive cleanup only was attempted, confined to their recorded
  creation interval/names under C:/Users/projy/AppData/Local/Temp. No original
  files or real mod folder touched. No ACL changes or approval bypass attempted.

Contract Phase 103 should build on:

- m2-unit-design v1 with explicit profile {id, revision}; native/1 has no
  automatic balance rules; combat-reforged requires the pinned commit. Never
  detect profile from folder name. Profiles do not imply runtime support.
- Original inputs and preset snapshots stay separate from derived values.
  overrides.inputs apply before calculation; overrides.native pin final typed
  sheet-column values afterward, including zero and explicit [] list clearing.
  Remove a pin to resume inheritance. Input semantic validation/calculation is
  still 103 work; unknown input keys remain dormant, never EDU field names.
- Shared m2-unit-sheets v1 project owns units[exact_EDU_type].builder_design,
  annotations, extras, rules, drafts, revision/source checks and history.
  attach_design returns a copy, never saves/stages stats. Future readers must
  validate the inner design explicitly; the existing sheet validator preserves
  the extension. Detached new designs await donor creation in 106. EDU cannot
  reconstruct the original design uniquely.
- output_values accepts only shared sheet_ops.FIELDS and types, then separates
  unverified attribute proposals into metadata.omitted. No hook_drag -> hook
  conversion. The ordinary patcher still owns existing unknown source tags.
  The helper has no target-runtime opt-in. Do not silently discard omission
  reports or overwrite the stored design with calculated output.
- For selected native fields, 106 must use existing preview/revision/source
  checks, sheet_ops.stage_cells/field_changes and EDU planners. Additional
  engine fields without sheet columns need a shared extension or existing
  native editor plan, not a parallel patcher. Classification/Tier and EDB
  balancing remain owned by sheets; 107 uses mercpools for existing pools/gates.

Concrete item-level stops, with both outcomes:

- Custom export inconsistency is resolved at this boundary by the roadmap's
  explicit metadata-only requirement. README/UI claim omission, while pinned
  exportableAttrs allows CUSTOM_TAG/hook and rewrites hook_drag. Older strict
  exporter tests contradict that filter. No upstream pass/runtime claim made.
- sp support: upstream calls it native, toolkit WEAPON_ATTR omits it. Question:
  keep sp metadata until target evidence, or approve shared vocabulary support
  after supplying that evidence? Outcomes: no new sp token, or verified shared
  native emission. Stopped on enabling support; current boundary quarantines it.
- Guards Skill: build.py help/audit_rules use +2, final combat_rules uses +1.
  Question: port final r2 +1, or intentionally use +2? Outcomes change calculated
  Defense Skill by one. Stopped on implementing that formula.
- Upstream entered costs: equipment_grade multiplies explicitly entered costs.
  Question: retain pre-grade meaning in overrides.inputs, or treat the entered
  value as final via overrides.native? Outcomes are grade-adjusted versus fixed
  exported costs. Stopped on adapter interpretation; both forms are representable.

New user-visible string IDs: NONE. ContractError values are internal codes;
future UI exposure must add English strings in web/i18n/en.json only.

Not verified: battle/runtime semantics, formula parity and rounding, 103 engine,
104 browser interactions, 105 upstream migration, 106 Apply/Undo or 107 pools.
No commit, tag, build or release performed. Live five-hour usage at start and
checkpoints: 1%, 5%, 8%, 11%, 12% used; latest 88% remaining, below the user's
Phases-102-108-only 90%-used stop. Weekly usage is not the guard. No credits
spent or limits reset.

## 2026-11-08 - Phase 116 real-data verification and shared builder integration

- Item 1(a): DONE on disposable copies for balance preview/export/reconciliation,
  Apply, idempotence and Undo. Item 1(b): DONE for vanilla packed-data load, each
  stage preview and CSV/XLSX round trips for all seven supported editable views.
  Recruitment is a read-only grid and has no CSV/XLSX mapping route; its separate
  EDB export was verified. Importing recruitment as an editable sheet is NOT done.
- Item 2: DONE to the Node VM/fixture HTTP harness boundary; human browser and
  in-game checks listed below are NOT done. Item 3: DONE, collapsible help and
  examples in Unit sheets plus updated docs/SHEET_INTERCHANGE.md.
- Builder bridge: WAITING ON 106. Phases 102-108 were not built or stubbed here.
  This entry does not mark the whole phase's interactive exit complete.
- Read ../AGENTS.md, Phase 116, archived 109-115, latest handoffs,
  SHEET_INTERCHANGE.md and upstream/EDB_SHEETS_WORKFLOW.md. Copied the complete
  supplied EDB Reader directory into .tmp/phase116/snapshot, then copied EDU/EDB
  again into .tmp/phase116/snapshot_mod/data. Config, backups, logs and all writes
  were redirected under .tmp/phase116. All 29 copied files still hash-identically
  to their originals after Apply/Undo. No real mod folder was written. The five
  external Python sources were read/AST-parsed as data only; their SHA-256 values
  match the workflow document. The BAT, JSON, CSV, text and legacy logs/outputs
  were read, never executed. Original source/workbook scripts and macros did not
  run. No dependency added. UT_NO_BROWSER=1 throughout verification.

### Snapshot counts and reconciliation

846 native units, 846 keyed Fynn EDU objects, 128 building chains and 8,055
recruitment rows in both native EDB and Fynn EDB. Exact unit IDs match; refresh
has no additions/deletions. There are 34 units missing race or tier and 40 BG
annotations. Rule inputs contain 6/80/80 keyed rows. Graphs have 15 branched and
4 multiple-root notes, no invalid graphs. Sources are the named paths in the
upstream workflow document, including References and Output, not a live mod.

| Stage | Legacy OK / skip / total logged | Ours changed / unchanged / skipped / invalid | Numeric differences from legacy in this stage's own field |
| --- | --- | --- | --- |
| Replenish | 7,109 / 945 / 8,054 | 159 / 6,575 / 1,320 / 1 | 224 |
| Experience | 6,975 / 1,079 / 8,054 | 105 / 6,870 / 1,079 / 1 | 5 |
| Pool | 6,608 / 1,446 / 8,054 | 278 / 6,330 / 1,446 / 1 | 5 |

Legacy OK combines our changed/unchanged meanings. Each of our stage logs covers
all 8,055 entries. Counts also reconcile with exported full and skip/error logs
in the required pipeline suite. Numeric comparisons join the same ordered
building/level/unit occurrences, including duplicate recruitments and conditions;
all 8,055 identities match in each output. Initial pools have zero differences.
Replenishment differences persist into later exports, and the five experience
differences persist into the final export. Those are inherited fields, not extra
unclassified differences.

| Difference class | Concrete scope | Legacy | Ours / explanation |
| --- | --- | --- | --- |
| Intentional fix: stale saved artifacts, fractional-pool rule | 215 replenishment numbers: 8 avari_retraining, 3 guild_horse_breeders_guild, 204 professional_military | Recalculates rates for maximum < 1 | Preserve original rates as the documented rule requires. The supplied current script explicitly skips these pools, so the saved output is not reproducible from that script. Historical generation/version is unverified; no new policy was chosen. Exact value groups below. |
| Intentional fix: stale JSON and regex context | 5 replenish, 5 experience, 5 pool values in hinterland_farms and breed | Saved structure gives every +N child depth 1; legacy regex recognizes only the word before + and carries its earlier context | Native graph reads full level IDs and follows actual upgrade edges. Exact values below. hinterland_mines also has corrected depths 0/1/2 instead of 0/1/1 but contains zero recruitment rows. |
| Approved Phase 112 per-level settlement rule | 4 replenish values in hinterland_unique4 | First chain header is city, applies x0.9 to unspecified later headers | Later levels have unspecified headers and use x1. Exact values below. No new city/castle decision needed. |
| Intentional fix: comment stripping | Legacy replaces comments on 8,054 recruit lines in r and exp; 6,235 differ from source comments in new | Strips semicolon suffix and inserts generated notes | Preserve original notes verbatim, including any already-stale generated notes; explanations belong to logs. All 8,179 comment-bearing source lines survive. No nonnumeric/noncomment line differences remain after normalization against each legacy output. |
| Intentional fix: complete logs / malformed input | One Muhad Berserkers line has no space after closing unit quote | Retained in output but missing from every 8,054-entry legacy log | Unchanged bytes plus explicit malformed_recruit_pool outcome in all three 8,055-entry logs. Existing malformed-input tests pass. |
| Intentional fix: complete skip reasons | Replenish log counts | Saved legacy log treats 375 fractional entries as OK, 218 as SKIP; current script also contains early skip branches without log_entry | Ours records all 593 as fractional_pool_preserved. 215 differ numerically; the other 160 formerly OK entries already have the preserved value. Missing race 216, BG tier 511 account for the other 727 skips. |
| Bugs found in toolkit | Vanilla interchange only, described below | Gunpowder delay offset; implicit list deduplication | Both fixed after failing tests. No unexplained balance number remains. |

The fractional-pool value groups below enumerate all 215 differences. Their
maximum pools remain unchanged and below 1. Column values are rates, not turns.

| Building | Legacy rate | Ours (original rate) | Rows | Class |
| --- | --- | --- | --- | --- |
| avari_retraining | 0.0625 | 0.1 | 2 | Intentional stale-artifact/fractional-rule fix |
| avari_retraining | 0.05 | 0.1 | 1 | Intentional stale-artifact/fractional-rule fix |
| avari_retraining | 0.053334 | 0.1 | 2 | Intentional stale-artifact/fractional-rule fix |
| avari_retraining | 0.066667 | 0.1 | 3 | Intentional stale-artifact/fractional-rule fix |
| guild_horse_breeders_guild | 0.08 | 0.025 | 1 | Intentional stale-artifact/fractional-rule fix |
| guild_horse_breeders_guild | 0.106666 | 0.025 | 1 | Intentional stale-artifact/fractional-rule fix |
| guild_horse_breeders_guild | 0.16 | 0.025 | 1 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.076923 | 0.1 | 21 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.083333 | 0.1 | 14 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.066667 | 0.1 | 6 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.0625 | 0.1 | 10 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.061538 | 0.1 | 2 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.071429 | 0.1 | 26 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.058824 | 0.1 | 24 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.057143 | 0.1 | 7 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.047059 | 0.1 | 12 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.052632 | 0.1 | 18 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.042106 | 0.1 | 3 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.032 | 0.1 | 15 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.053334 | 0.1 | 2 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.05 | 0.1 | 3 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.04 | 0.1 | 20 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.044445 | 0.1 | 3 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.055556 | 0.1 | 6 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.08 | 0.1 | 6 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.166667 | 0.1 | 2 | Intentional stale-artifact/fractional-rule fix |
| professional_military | 0.066666 | 0.1 | 4 | Intentional stale-artifact/fractional-rule fix |

The remaining stage-specific numeric differences are all enumerated here.

| Stage | Building / level / unit | Legacy | Ours | Class |
| --- | --- | --- | --- | --- |
| replenish | hinterland_farms / farms+1 / Faolan Borderguard | 0.166667 | 0.2 | Intentional stale-JSON/level-context fix |
| replenish | hinterland_farms / farms+2 / Faolan Borderguard | 0.166667 | 0.25 | Intentional stale-JSON/level-context fix |
| replenish | hinterland_farms / farms+3 / Faolan Borderguard | 0.166667 | 0.333333 | Intentional stale-JSON/level-context fix |
| replenish | breed / breed+1 / Fylani Herders | 0.08 | 0.106666 | Intentional stale-JSON/level-context fix |
| replenish | breed / breed+2 / Fylani Herders | 0.08 | 0.16 | Intentional stale-JSON/level-context fix |
| replenish | hinterland_unique4 / gundabad_gate / Snow Trolls | 0.065454 | 0.072727 | Approved Phase 112 per-level rule |
| replenish | hinterland_unique4 / gundabad_gate / Wulfguard Axemen | 0.069231 | 0.076923 | Approved Phase 112 per-level rule |
| replenish | hinterland_unique4 / gundabad_gate / Wulfguard Pikes | 0.069231 | 0.076923 | Approved Phase 112 per-level rule |
| replenish | hinterland_unique4 / durin_hall_rebuilt / Hammers of Gundabad | 0.05 | 0.055556 | Approved Phase 112 per-level rule |
| experience | hinterland_farms / farms+1 / Faolan Borderguard | 0 | 1 | Intentional stale-JSON/level-context fix |
| experience | hinterland_farms / farms+2 / Faolan Borderguard | 0 | 2 | Intentional stale-JSON/level-context fix |
| experience | hinterland_farms / farms+3 / Faolan Borderguard | 0 | 2 | Intentional stale-JSON/level-context fix |
| experience | breed / breed+1 / Fylani Herders | 0 | 1 | Intentional stale-JSON/level-context fix |
| experience | breed / breed+2 / Fylani Herders | 0 | 2 | Intentional stale-JSON/level-context fix |
| pool | hinterland_farms / farms+1 / Faolan Borderguard | 3 | 4 | Intentional stale-JSON/level-context fix |
| pool | hinterland_farms / farms+2 / Faolan Borderguard | 3 | 5 | Intentional stale-JSON/level-context fix |
| pool | hinterland_farms / farms+3 / Faolan Borderguard | 3 | 6 | Intentional stale-JSON/level-context fix |
| pool | breed / breed+1 / Fylani Herders | 1 | 2 | Intentional stale-JSON/level-context fix |
| pool | breed / breed+2 / Fylani Herders | 1 | 3 | Intentional stale-JSON/level-context fix |

- For all three generated outputs, line-by-line assertions mask only the four
  numeric tokens and require the entire remaining source text, comments,
  requirements, whitespace, CRLF and unrelated capabilities to remain identical.
  All pass. Native Apply writes exactly the preview's final bytes: 542 changed
  fields (159 + 105 + 278). Repeat preview gives zero changes; Log Undo restores
  the original EDB bytes. Measured full pipeline preview: 14.095 s cold and
  7.430 s later; Apply including revalidation: 7.548 s. These are local elapsed
  samples, not a general throughput guarantee.
- No legacy/spec question requiring a new user policy decision was found.
  Fractional preservation and per-level settlement were already specified;
  parser-backed depths supersede stale JSON. Historical script/output provenance
  cannot be established beyond the explicit non-reproducibility described above.

### Vanilla packed data and workbook results

- Selected the installed toolkit entry Medieval II Total War at the root in
  config/settings.json. Read EDU (513,960 bytes, 0.355 s) and EDB (274,393 bytes,
  0.281 s) from its packs with gamepack.read_bytes, copied the bytes into
  .tmp/phase116/vanilla/data, then used Mod and the sheet service on that copy.
  No packs were modified or real-game extraction performed. Final load took
  0.507 s: 413 units, 1,475 recruitments, all 413 units in the missing queue.
- Used the supplied editable rule tables as an explicit profile, without
  assigning Middle-earth races or tiers to vanilla units. Each stage preview
  correctly has 1,475 skips and zero changes: replenish/pool have 1,375 missing
  race and 100 fractional-pool reasons; experience has 1,475 missing race.
  This verifies named missing-data behavior, not a playable vanilla balance.
  replenish preview: 1.169 s.
  experience preview: 0.563 s.
  pool preview: 0.569 s.
- All 14 exports were inspected, explicitly mapped, previewed and imported
  through the validated service. The row counts below are full identities, not
  the inspector's 12-row display sample. Each unit view has 413 IDs; rules have
  6/80/80 complete keys. Imports were staged sequentially in one disposable
  project, so later timing includes accumulated saved layouts. Import timing
  includes inspect, preview and validated stage. Preview changes include
  same-value field assignments and are not counts of actual native differences.
  After both fixes, native review of all accumulated round trips has ZERO changed
  units and ZERO output files. Reopen uses the persisted project successfully.

| View | IDs/rows | CSV export / import (s) | XLSX export / import (s) |
| --- | --- | --- | --- |
| classification | 413 | 0.221 / 0.791 | 0.252 / 1.126 |
| base | 413 | 0.449 / 3.342 | 1.364 / 7.595 |
| attributes | 413 | 1.163 / 6.001 | 1.764 / 4.359 |
| soft | 413 | 1.202 / 4.946 | 1.403 / 10.194 |
| rules:replenish | 6 | 1.222 / 5.932 | 0.770 / 5.558 |
| rules:experience | 80 | 0.820 / 5.102 | 0.698 / 4.387 |
| rules:pool | 80 | 0.674 / 4.644 | 0.727 / 5.975 |

- Read copied workbook (20) in 1.080 s and archived (17) in 1.373 s with the
  standard-library adapter. Populated Base stats/Attributes/Soft stats rows:
  (20) 1,231/929/904; (17) 1,228/926/897. Group rows are included in these counts,
  not asserted to be live units. Also read both converter Python sources and
  both archived EDU text outputs as data. The copy of rebuilt2.xlsx is refused
  in 0.048 s at archive_size because its aggregate uncompressed data exceeds
  80 MB. This documented bound remains a known limitation, not an untested
  claim of successful real rebuilt2 import. No Excel/macros/recalculation ran.

### Fixes, automation and limits

- Tests FIRST: test_gunpowder_optional_effect_keeps_delay_and_other_members
  failed with 'musket_shot_set' != 25. Added a shared tuple-member resolver for
  reading AND patching minimum delay in 12-member stat_pri/stat_sec tuples.
  It preserves optional firing effect, lethality and all unedited members.
  Added CSV/XLSX test_gunpowder_delay_round_trip_and_native_patch as a second
  end-to-end check. A new test initially omitted required formulas='values';
  its fixture request was corrected, with no runtime bypass added.
- Tests FIRST: test_list_round_trip_preserves_duplicate_native_members failed
  with ['hardy','stakes'] instead of ['hardy','stakes','stakes']. Typed list
  parsing now preserves duplicates during set/paste/import/patch. The explicit
  append/remove/deduplicate operation semantics and existing dedup test pass.
  This removed the unwanted changes to 18 vanilla units after unchanged import.
- Help regression failed first on missing sheets.help_title, then passed after
  adding a collapsible section in the window using only English catalogue text.
  It covers selected vs matching scope, filter/edit/review example, keyboard and
  paste, staging/Apply/Undo, mapped IDs, blanks/zero/clear and known limitations.
- New Node cases cover help, a 75-row page with total 1,000,000 in <2 s and
  <300,000 HTML characters, refresh addition/deletion/missing counts and BG,
  plus branched structure/fractional/BG/missing outcome rendering and escaped
  special requirements. The page test uses a mocked API; it does not pretend to
  load a million-unit mod. Its first assertion used a nonexistent DOM attribute;
  corrected to count actual row checkbox handlers, no production change needed.
- New backend sparse test reads 50,000 formatted empty rows plus actual data,
  requires exactly Guard, no phantom/ignored records and <10 s. It passes.
  Existing tests cover nested AND/OR/NOT filters, real keyboard/paste handlers,
  mixed typed mass edits and Cancel/Confirm, stable IDs through sorting, saved
  views, project undo/redo, new/deleted refresh, branched/merged graph policies,
  fractional pools, special conditions and native byte preservation. Both
  Node suites pass. Required pipeline and interchange suites also run actual
  unitsheets.js and HTTP routes on self-cleaning mods for export, native/EDB
  Apply and existing Log Undo; those are stronger than mocked response checks.
- Human browser checks NOT done: native file picker/downloads; actual clipboard
  permissions and OS keyboard/focus/selection behavior; frozen headers/identity
  columns while scrolling; visual layout and responsiveness on real workbooks;
  interactive reload/reopen, mass review, Apply confirmation and Log navigation;
  opening XLSX in Excel/LibreOffice and recalculation; installed-game gameplay.
  Snapshot Apply/Undo above is service-level and existing fixture HTTP tests
  exercise UI handlers, not a claim of human browser acceptance.
- Required final tests with UT_NO_BROWSER=1: unit_sheets 36, sheet_ops 42,
  sheet_pipeline 23, sheet_native 8, edb_balance 35, sheet_interchange 32 PASS;
  web_modules 130/130 and i18n 45/45 PASS; both Node sheet suites PASS.
  Final git diff --check: PASS (exit 0). Added-line em dash scan: zero;
  pre-existing catalogue text is preserved. All five new IDs confirmed by
  comparison with HEAD, no IDs removed.
  Existing .tmp/phase110-step4-runner/sitecustomize.py is unchanged and supplied
  via PYTHONPATH for the previously documented sandbox mkdir mode limitation.
  Disposable real-data copies/logs remain in ignored .tmp/phase116 for review.
- Changed files: unittransfer/sheet_ops.py; web/js/unitsheets.js;
  web/i18n/en.json; tests/test_sheet_ops.py; tests/test_sheet_interchange.py;
  tests/test_unit_sheets_ui.js; docs/SHEET_INTERCHANGE.md; docs/CODEX_HANDOFF.md.
  New IDs: sheets.help_title, sheets.help_edits, sheets.help_example,
  sheets.help_interchange, sheets.help_limits. New catalogue lines unindented,
  English ONLY. Claude translates; no other catalogue or dev/i18n edit.
- Preserved pre-existing TWCenter INDEX deletions and all unrelated untracked
  paths. No STATE/ROADMAP/ROADMAP_ARCHIVE edit. No commit, tag, build or release.
  Live usage checks succeeded at 53, 56, 59, 60, 63 and 65 percent used in the
  five-hour window, with final checkpoint 68 percent used, under the active
  continuation's 90-percent-used stop. Weekly
  usage is not the threshold. No credits spent or limits reset.
## 2026-11-08 - Phase 101j implemented and fixture-verified, ready for Claude review

- Continued the original checkpoint in place, under the user's 2026-11-08
  Phase 101j-only override: stop at 90% used in the five-hour window. Live
  session rate_limits checks: 71%, 73%, 76%, 78%, 79%, 80%, 81%, 83% and 85% used.
  No credits spent or limits reset. GitHub report check explicitly skipped.
- Added unittransfer/charmodels.py, a read-only join: EDCT Effect Level effects
  (family -> named character), zero-based slots, preserved comment labels,
  named generals/captains/agents, campaign named-character battle overrides,
  active/commented script changes, faction symbols and strat texture entries.
  Nested campaigns are included. Missing battle entries/no horse animations
  warn; slots above zero without matching traits are notes. Shared faction
  blocks retain all owners, and the dialog identifies those shared edits.
- Added GET /api/charmodels (roster without faction, details with faction),
  characters/horse metadata on /api/bmdb/entry, and levels/traits on
  /api/stratmap/entry. Removed the invalid three-slot minimum warning from
  characters.check and corrected its module docstring and existing assertion.
- Added the Faction models dialog from both Models Editor tabs and entry
  cards. Named/captain/agent strat and battle fields and campaign-character
  battle fields use model-name datalists. Probe shows the existing plans'
  changes, warnings and errors; Apply requires an unchanged successful preview,
  calls the existing apply routes and reloads. Each save keeps its existing
  backup, My Changes/Log record and Undo. Multiple saves are separate records,
  not an atomic transaction; partial failure reloads completed saves and reports
  the error. No new writer, file format or dependency.
- Model entry cards show character uses/roles and no-horse warnings. Strat
  entry character rows show actual level, matching traits and comment together.
  Links open the Characters block, raw script line or the campaign character.
  Campaign/faction survive navigation URLs, including nested campaigns; the
  map link selects the person by name and line and surfaces the People panel.
- Read-only measurements before drawing UI confirmed vanilla packs vs DaC:
  24/31 faction rosters, 78/237 strat entries, vanilla named slots 23 x one
  plus Pope x two, DaC named slots 3-11. Both use only dictionary, strat_model,
  battle_model and battle_equip within descr_character faction blocks.
  Sicily ownership was inspected explicitly. All 48 vanilla and 62 DaC
  named/captain battle_model lines exist and have horse animations; no false
  warning on either set. Script join found six DaC changes, zero vanilla.
  Sicily detail joins were read on both: correct symbols and 21/22 texture
  entries, one/eleven named slots, zero findings. Real mods/game unchanged.
- Tests FIRST: five Python fixture tests initially failed ImportError on the
  absent charmodels module; Node initially failed ENOENT on the absent dialog.
  The later HTTP join test first failed 404 before adding the route. Python's
  first attempt hit the sandbox temp-directory mode issue before assertions;
  a local runner made mkdir use 0777, after which the missing-module failures
  were observed. Corrected two fixture assumptions: valid models_strat path
  syntax, and signatures from raw disk line endings rather than LF literals.
- Final new tests: tests.test_charmodels 7/7, Node test_charmodels_ui.js PASS.
  Synthetic fixtures cover vanilla one-slot/Pope, DaC heir/leader/hero traits,
  priest levels, misleading labels, duplicate trait effects, shared blocks,
  missing/foot-only battle entries, active/commented scripts, nested campaigns,
  roster/entry HTTP joins and both existing plan/apply routes plus Log Undo.
  Save assertions verify only the requested token changes and Undo restores
  exact bytes; stale descr_character signature is refused. JS exercises real
  handlers/cards, preview invalidation/refusal, partial save reload and map
  character selection, with fixture API responses.
- Required regression commands used UT_NO_BROWSER=1 and were run separately
  via python -m unittest (these legacy modules call sys.exit during import, so
  a combined invocation stops at the first). web_modules 130/130;
  characters 24/24; i18n initially 43/45 on a dynamic role ID, fixed with
  explicit IDs, then 45/45. stratchar 88/89: installed DaC has 302/307 spans
  ending on separating blanks. bmdb and bmdb_http fail on missing expected
  Third_Age_Reforged fixture inputs (battle_models.modeldb and EDU respectively).
  All three failures reproduced on unchanged HEAD sources extracted under the
  workspace with the same settings and runner. No installed-data failures
  have been attributed to this change. Baseline scratch remains under
  .tmp/101j-baseline (HEAD sources/settings copy), with .tmp/101j-*.log,
  .tmp/101j-baseline.zip and the test runner. Automatic command approval rejected
  both scoped PowerShell cleanup attempts as blocked by policy; no more specific
  reason was supplied. Scratch is untracked and not part of the implementation.
- git diff --check passed. New-line/new-file em dash scan: zero. English-only
  strings added to web/i18n/en.json, including three matching Python defaults;
  removed the obsolete three-slot-warning English ID. Other catalogues and
  dev/i18n untouched. No graphify-out/graph.json exists at the workspace parent,
  so no existing graph was available to query/update. No commit or release.
- Changed files: unittransfer/charmodels.py, unittransfer/characters.py,
  unittransfer/server.py, web/js/charmodels.js, web/js/bmdb.js,
  web/js/stratmap.js, web/js/core.js, web/index.html, web/i18n/en.json,
  tests/test_charmodels.py, tests/test_charmodels_ui.js,
  tests/test_characters.py and this handoff. Previous handoff entries preserved.
- Limits: browser layout and installed-game behavior were not interactively
  verified. Scripts, symbols and strat texture ownership are read only.
  EDU general_unit bodyguards remain outside this phase's scope. The three
  baseline regression failures above remain unresolved as unrelated inputs.
- Claude's review, same day, before the commit: a level's trait list is
  shown four names deep with "+N more" and the rest on hover (DaC gives
  level 3 to 22 traits), and `levels_of` puts the heir and leader traits
  first (named Factionheir/Factionleader, or given by a BecomesFactionHeir/
  BecomesFactionLeader trigger), with a test written first; the model boxes
  are wider; "General" in the role list is "Family general"; the help and
  applied strings reworded. Translated into de, es, fr, pl, ru, tr and
  zh-Hans (0 missing, 0 stale each), and the obsolete three-slot warning ID
  removed from every catalogue. The .tmp scratch was deleted. Checked in the
  app on DaC with previews only (a descr_character battle_model and a
  descr_strat leader); nothing applied.

## 2026-11-08 - Phase 115 completed and fixture-verified, ready for Claude review

- Exit items 1-6: DONE in automated fixtures. In-app CSV and standard-library
  XLSX import/export cover classifications, Base stats, Attributes, Soft stats
  and all three rule tables. Keyed Fynn EDU JSON uses the same mapping/preview.
  No dependency added. docs/SHEET_INTERCHANGE.md documents choices and limits.
- New isolated adapter reads relationships, shared/inline strings and actual
  populated cells with zipfile/XML, without extraction, executing links/macros,
  or trusting declared dimensions. Formatted and empty inline/CSV cells do not
  create records. Compressed/uncompressed/cell/XML bounds are documented.
- Explicit per-worksheet view/header/column mapping distinguishes duplicates by
  source index. Arrays explicitly combine split list columns. Preview exposes
  validated IDs, fields, before/after changes, ignored rows and formula issues.
  Its token binds source/mappings/project/native source. Mapping changes clear
  the UI preview. Only live EDU IDs match; joins and rule merges use identity,
  never position. Duplicate identities/targets/keys and invalid cells refuse
  the entire import. The old direct CSV/rule/Fynn EDU HTTP import now refuses
  preview bypass. Pure legacy adapter helpers remain for offline compatibility.
- Import validates a private project copy, including the resulting response
  filter, before saving. Staged work, omitted fields/rule rows and existing rule
  IDs survive. Empty native cells mean unchanged, explicit zero remains zero,
  blank annotations/rule cells remain blank and [] clears a list. Explicit no
  also clears a split list with no other entries. Absent lists do not create
  defaults. Unknown unit/rule columns survive either export layout with
  collision-safe labels. Imported-layout list overflow refuses truncation;
  native editing/native-header export continue to accept the full list.
- Imported layouts retain headers, source positions, presentation rows and
  header-row gaps. CSV has no worksheet title, so its layout is named CSV.
  The existing native patcher still owns omitted tuple members, unknown fields,
  comments and Apply/backup/Undo; no converter defaults rebuild game fields.
- Documented formula subset: finite numeric constants, parentheses, unary +/-
  and binary + - * /, same-sheet A1 references with optional $ anchors.
  Limits: 1024 characters, 64 AST nodes and dependency depth 64. Functions,
  ranges, cross-sheet/named/structured/shared/array formulas and other syntax
  are unsupported. Cycles, missing inputs, division by zero and nonfinite
  results are unavailable, never zero. Missing caches and differing supported
  caches are named; unsupported caches are never trusted. EDU AND rule formula
  extras recalculate against current staged mapped values, remain read-only
  derived columns and expose issues on preview/reopen/export.
- Export choices: computed values for CSV/XLSX; supported formulas with current
  caches only when XLSX plus imported layout is explicitly selected. Native
  header/formula requests are refused rather than moving references. Unsupported
  formulas export blank plus named issues. Macros/styles/tables/links are not
  copied. This is data interchange, not a formatting/Excel-feature round trip.
- Read original workbook headers and converter text only, never their scripts
  or macros as executable code. The fixture JSON copies ONLY the actual 40
  Base stats headings from (20)/(17) and Attributes/Soft stats header shapes;
  data rows are synthetic. (17) also uses A although the converter expects type.
  Column 3/925 are mapped explicitly. Original workbooks and real mods unchanged.
- Tests FIRST: initial backend run had 10 errors on the absent interchange API
  or module: all_views_csv_and_xlsx_round_trip;
  current_archived_shapes_and_sparse_formatted_rows;
  inspect_duplicate_headings_and_reject_ambiguous_mapping;
  mapping_preview_required_and_atomic_with_zero;
  keyed_cross_sheet_join_and_explicit_list_clear;
  formulas_are_derived_named_and_never_native_updates;
  formula_export_choice_and_recalculation_after_native_edit;
  rule_import_merges_by_key_preserving_omitted_values;
  fynn_mapping_validates_ids_and_does_not_substitute_native_stats;
  preview_token_binds_source_mapping_and_project. Duplicate-refusal assertions
  initially passed on the old unknown-action refusal and now pass on actual
  implemented routes. The new Node suite first failed on absent XLSX input.
- Later tests FIRST failed for absent-list reconstruction, missing canonical
  unknown columns/formula issues, duplicate/native header collisions, split
  lists, old list-capacity blocking native edits, save-before-filter-validation,
  CSV title/header gaps, empty inline/CSV rows, legacy HTTP preview bypass,
  derived-kind metadata and rule formula recalculation. These now pass. A test
  assertion was corrected to inspect the worksheet title after CSV import,
  which necessarily uses CSV. The HTTP/UI acceptance test passed when added:
  actual unitsheets.js handlers map/preview/stage, project undo/redo, XLSX
  download and native Apply against a self-cleaning fixture mod/server. Exact
  bytes change only the requested size tokens; backup Undo restores the original.
- Files changed by THIS run: unittransfer/sheet_interchange.py,
  unittransfer/unit_sheets.py, unittransfer/sheet_ops.py, web/js/unitsheets.js,
  web/i18n/en.json, tests/test_sheet_interchange.py,
  tests/test_sheet_interchange_ui.js, tests/test_sheet_pipeline.py,
  tests/fixtures/sheet_workbook_headers.json,
  docs/SHEET_INTERCHANGE.md and this handoff. NO server.py/protected Armory file
  or test/.tmp/armory_* edit. Concurrent changes/commits and pre-existing
  TWCenter deletions/untracked files preserved. No STATE/ROADMAP/ARCHIVE edit.
  No commit, tag, build or release by this run.
- New IDs (English ONLY, new catalogue lines unindented):
  sheets.interchange_invalid, sheets.interchange_file, sheets.interchange_csv,
  sheets.interchange_xlsx, sheets.interchange_values,
  sheets.interchange_formulas, sheets.interchange_canonical,
  sheets.interchange_imported, sheets.interchange_export,
  sheets.interchange_help, sheets.interchange_skip, sheets.interchange_header,
  sheets.interchange_extra, sheets.interchange_preview,
  sheets.interchange_stage, sheets.interchange_formula_issues. Claude translates.
  Removed six unused English IDs for replaced controls: sheets.column_mapping,
  sheets.mapping_example, sheets.import_csv, sheets.import_replenish,
  sheets.import_experience, sheets.import_pool. No other catalogue/dev/i18n edit.
- Final verification with UT_NO_BROWSER=1: unit_sheets 36, sheet_ops 41,
  sheet_pipeline 23, sheet_native 8, edb_balance 35, sheet_interchange 29 passed;
  web_modules 130/130; both Node sheet suites passed; diff check exit 0.
  First i18n run failed 43/45 due to our obsolete IDs/uncatalogued labels;
  fixed, subsequent and final runs passed 45/45 including current Armory IDs.
  The final required run's first pipeline pass found one existing custom-key
  test still calling the intentionally retired direct import action. Migrated
  it to explicit preview/import and selected-row editing, additionally verifying
  that pre-existing rule rows survive. Rerun: 23/23 pipeline tests pass. All
  required checks now pass. No unrelated i18n failure is being hidden. Added
  em dash scan: zero. Neither server.py nor any protected file was edited.
- Python uses the existing ignored .tmp/phase110-step4-runner/sitecustomize.py
  through PYTHONPATH for the documented sandbox TemporaryDirectory mode issue;
  runner unchanged. Fixtures clean up with TemporaryDirectory; HTTP servers
  shut down/join. No task scratch fixture folder/downloaded workbook left.
- Live usage succeeded at 31%, 36%, 42%, 44%, 48% and finally 50% used in the five-hour window,
  below this continuation's authorized 90%-used stop. Weekly usage is not the
  stop threshold. No credits spent/reset. No unresolved policy question.
- NOT verified: interactive browser/file picker, Excel/LibreOffice opening or
  recalculation, original user-data round trips, installed-game behavior or
  Phase 116 real-data/non-EUR/builder integration. Unsupported-cache freshness
  cannot be verified. Formula/list/layout limits above are explicit, not guesses.

## 2026-11-07 - Armory requests (a), (b), (c) implemented, ready for Claude review

- (c) Done: default remains soldier. The Armory panel reads the selected unit's
  editor fields and offers soldier, each existing officer, add officer, replace
  each armour model tier and append the next tier. Add and New unit send
  assign_to. Baked entries use the existing edit assignment step, including
  sync_armour_levels. Existing imported entries use the same slot helper and
  level synchronization. A soldier replacement also updates the first armour
  tier only when it names the former soldier model; distinct tiers stay intact.
  The existing bmdb.js caller requires no payload change. Fixed officer append
  ordering in edu.set_model_slot so adding #2 does not replace the effective #1.
- (a) Done: the same panel offers optional General, Faction leader and Faction
  heir targets, selected by campaign, faction, then an eligible named character.
  Officer assignment uses the unit slot picker. Plans include the character's
  battle_model change. Apply creates the model first, then uses the existing
  stratchar plan/apply writer and its backups, My Changes and Log Undo record.
  Fresh name, line and rank checks reject stale selections before writes.
  Tests verify the battle_model-only write preserves all other character values,
  traits, ancillaries, army lines and surrounding characters, and Undo restores
  original CRLF bytes. A baked model plus character target has separate undo
  records; undo the character first, then the model. No new character writer.
- (b) Done: selected animation actions have a uniform scale and expandable X/Y/Z
  controls. Preview uses /api/model/anim/preview; save plans and applies use
  /api/model/anim/save_plan and save_apply with animedit's scale key. A target=pack
  request delegates to existing pack preview/plan/apply handlers. Loose saves use
  animedit unchanged. The destination/name is explicit and the plan is reviewed
  before apply. Scale 1 omits scale and makes no save request. No new animation
  writer. Bind data remains the original skeleton's, matching the Models viewer.
  A late preview cannot restore an action after Rest or after source changes.
- Additional Tests FIRST: the late-preview test failed because Rest could be
  undone by an in-flight response, then passed after source invalidation. The
  session test failed because unitData was persisted, then passed after excluding
  that API cache. The new-unit fixture initially used identical model records,
  which the transfer engine correctly deduplicated; its mesh paths were made
  distinct so the test actually represents different armour tiers.
- Changed runtime files: unittransfer/armunit.py, unittransfer/edu.py,
  unittransfer/server.py (Armory routes, optional facts resolver and animation
  dispatch only), web/js/armexport.js, web/js/armanim.js, web/js/armsess.js.
  The concurrent run also has server.py changes; they were preserved.
- New tests: tests/test_armory_install.py, tests/test_armory_anim_routes.py,
  tests/test_armory_install_ui.js, tests/test_armory_anim_ui.js. String staging:
  .tmp/armory_strings.json. Change record: this file. Test logs and a process-local
  Windows test hook are under .tmp/armory_*; no shared test helper was changed.
- Checks actually run with UT_NO_BROWSER=1:
  - python -m tests.test_armory: PASS, 99/99.
  - python -m tests.test_folderimport: PASS, 33/33.
  - python -m tests.test_new_entry_and_cards: SKIPPED, Third_Age_Reforged absent.
  - python -m tests.test_edit: FAILED while loading the absent hard-coded
    Third_Age_Reforged modeldb; no feature assertions reached.
  - python -m tests.test_edit_http: FAILED copying that absent mod's files;
    no HTTP feature assertions reached.
  - python -m tests.test_stratchar: 88/89. The installed Divide_and_Conquer_EUR
    campaign has 302/307 character spans ending on blank lines, below the suite's
    expected >=306. Character rendering and file round-trips pass. campstrat.py,
    stratchar.py and this test are unchanged, confirmed by git diff --exit-code.
  - python -m tests.test_animedit: PASS, 28/28; installed unpacked-pack save
    section skipped by the existing suite because no unpacked pack.dat exists.
  - python -m tests.test_web_modules: PASS, 130/130, repeated after session edit.
  - python -m tests.test_armory_install: PASS, 9 tests, including add/new,
    baked/existing slots, matching/distinct base tiers, rank selection, partial
    character edits, separate model/character records and byte-exact Undo.
  - python -m tests.test_armory_anim_routes: PASS, 1 test covering all three
    packed dispatch operations without invoking another writer.
  - python -m tests.test_armory_workflow: PASS, 8 tests.
  - node tests/test_armory_install_ui.js and test_armory_anim_ui.js: PASS.
  - Existing Node UV/session/folder suite: PASS, run from repository parent as
    node main/tests/test_armory_uv.js because it uses main/ relative paths.
  - git diff --check: PASS. No added em dash in the six runtime diffs or new
    tests/string staging. No dependency added.
  - python -m tests.test_i18n: 42/45, exactly the expected missing page IDs,
    missing engine IDs and engine-template mismatch for staged strings. No
    catalogue was edited. The test truncates its missing-page list to ten.
- New string IDs, all awaiting Claude's merge of .tmp/armory_strings.json:
  armory.anim_scale, armory.anim_scale_axes, armory.anim_scale_confirm,
  armory.anim_scale_invalid, armory.anim_scale_loose, armory.anim_scale_name,
  armory.anim_scale_no_plan, armory.anim_scale_note, armory.anim_scale_pack,
  armory.anim_scale_save, armory.anim_scale_saved, armory.anim_scale_target,
  armory.assign_slot, armory.character_general, armory.character_heir,
  armory.character_leader, armory.character_none, armory.character_note,
  armory.character_target, armory.choose_target, armory.exp_step_character,
  armory.slot_add_officer, armory.slot_replace, armory.target_campaign,
  armory.target_character, armory.target_faction, eng.armunit.character_changed,
  eng.armunit.choose_character, eng.armunit.invalid_slot. Total: 29.
- Verified behavior versus limits: fixture writes, backups and Undo are verified;
  no real mod folder was written. Native visual rendering and in-game playback
  were not exercised. Packed animation support retains the existing writer's
  restrictions, including refusal when a writable mod-owned pack is unavailable;
  this change does not manufacture packs for mods inheriting vanilla animations.
  Character validation retains the existing campaign-map/vocabulary requirements.
  Multi-step installs keep the existing independent records and are not atomic.
  All successful test fixtures cleaned up. Initial failed tempfile setup left
  inaccessible empty directories in system TEMP and .tmp/armory_test_tmp; the
  attempted empty-directory cleanup command was rejected as blocked by policy.
  That rejection supplied no more specific reason. No cleanup bypass attempted.
- Remaining: Claude merges the 29 staged strings; rerun editor suites with the
  required installed fixture if desired. No ambiguous mod-write decision remains.
  No reserved EDB/sheets file, catalogue, dev/i18n, STATE.md, ROADMAP file or shared
  docs/CODEX_HANDOFF.md was edited by this run. Latest usage checkpoint: 29% used,
  71% remaining in the five-hour window. No credits/reset requested.
- Commit/release status: no commit, tag, build or release. Changes are uncommitted.

## 2026-11-07 - Armory assignment and scale implementation checkpoint

- Scope: user requests (c) unit/officer/tier assignment, (a) optional character
  battle models, and (b) animation scale. Concurrent EDB/sheets files and all
  catalogues are reserved for the other run. Strings are staged separately in
  .tmp/armory_strings.json. This entry replaces the normal shared handoff write
  for this task, as explicitly requested.
- Tests FIRST: after resolving a Windows tempfile permission problem in the
  local runner and correcting the synthetic modeldb header, the assignment
  regression suite failed eight assertions: stale base tier, ignored officer
  and tier selections, including the baked-model path. A further officer-order
  regression failed because officer #2 was inserted before officer #1. Character
  tests first failed with missing character_targets / facts_of support (eight
  errors). Node installation tests first failed on missing armExpAssignSlots.
  Node animation tests first failed on missing armAnimScaleEdits; the Python
  packed-route test first failed because the loose handler tried to use a
  registry instead of dispatching to the existing pack handler.
- Reference investigation finding (recorded here only): the armour upgrade
  models list replaces the visible tier model array when present. The soldier
  model remains the skeleton source. Changing soldier alone therefore leaves
  visible tier models unchanged. Base-tier synchronization is deliberately
  limited to a first tier that names the previous soldier model.
- Implemented so far: Armory slot payloads and picker, soldier/base-tier sync,
  existing-entry level sync, baked-entry assignments through edit.plan_edit,
  officer append order; optional campaign/faction/character selection with fresh
  rank/line validation, stratchar plan/apply and independent undo records; uniform
  and expanded axis scale controls using animedit and the existing packed writer.
- Verification so far: seven synthetic Python install tests, one packed-route
  test, and the two new Node VM tests pass. Broader required suites and final
  review remain. No real mod was written. Fixture config and logs are isolated.
- Local runner limitation: Python 3.12's tempfile mode 0700 creates directories
  this Windows sandbox cannot reopen. .tmp/armory_run_test.py uses inherited
  directory permissions under .tmp/armory_test_tmp, then executes the original
  test modules; no production or shared test helper was changed for this.
- Usage: latest checkpoint showed 15% used in the five-hour window. Normal 50%
  remaining stop applies to this run. No credits/reset requested.
- Commit/release status: no commit, tag, build or release. Work is uncommitted.
- Claude's merge, 2026-11-07: the 29 staged strings were added to en.json beside
  the other armory keys and translated into de, es, fr, pl, ru, tr and zh-Hans
  through i18n_todo.py --merge (two Russian strings reworded to the termbase's
  "модель битвы"). Checked on DaC EUR in the app: the templates route lists each
  faction's leader, heir and named characters, the slot picker on Mirkwood
  Bodyguard offers both armour tiers plus a new one, and an install plan (no
  apply) to armour_ug_models#3 came back clean. No apply was made to a real mod.

## 2026-11-07 - Phase 114 implemented and fixture-verified; shared i18n check blocked by concurrent Armory work

- Read root ../AGENTS.md, Phases 109-116/114, archived 112/113 and Finished
  notes, their handoffs and the 2026-11-06 checkpoint, engine/service/UI,
  buildings planner/atomic writer and existing tests. No roadmap/status edits.
- Exit items 1-7: DONE in automated fixtures. Canonical numeric stage order
  follows a read-only reference refresh/classification pass. Existing Refresh
  and classification controls remain independent; numeric stages can run alone
  or together, with pipeline_order in preview/UI and pipeline.json in the ZIP.
  Each later stage consumes the preceding stage's numeric tokens in one staged
  document. Refresh validates a deep copy and never mutates caller project data.
- Added cooperative cancellation at calculation/stage/row/export-file boundaries,
  using the existing HTTP progress cancellation endpoint independently of the
  sheet service lock. UI shows Cancel during preview/export, suppresses late
  cancelled results/downloads, waits for pending edits, and preserves previous
  staged state. Cancelled/failed balance requests do not persist legacy project
  migrations. HTTP tests cancel actual running preview AND export requests.
- Default export remains export_descr_buildings_new.txt; optional _r.txt and
  _exp.txt, building_structure_log.json, profile/rules and both logs per stage
  remain. Every outcome now has field, nonempty reason and rule (null when no
  rule could be selected), plus existing source line and before/after. Malformed
  early branches retain an invalid entry. pipeline.json records order, refresh,
  changed_fields and per-stage counts. Tests reconcile these with preview,
  complete/skip-error logs and the exact exported/applied bytes.
- Preview groups ALL entries by status/unit/building/level/field, including rows
  beyond the compact audit's 100-entry limit. Group entries carry concise
  line/before/after/reason/rule details; full explanations stay in the capped
  audit and complete ZIP logs. Node verifies all four statuses and escaping.
- Apply flushes pending edits and exposes the existing Log + undo UI. Actual
  unitsheets.js handlers plus settings.js doUndo run against real fixture HTTP
  routes for preview/export/one Apply/Undo; EDB bytes are restored exactly.
  Existing BuildingPlan/apply_edit owns backups, manifests and Log records.
  My Changes capture and clearing after Undo are verified. A failed log write
  now refreshes My Changes after rolling back the EDB, avoiding a phantom edit.
- Tests FIRST: initial new engine/service run had 1 failure and 6 errors across
  50 tests: empty successful-entry reasons, missing cancellation parameters,
  pipeline_order and pipeline.json. Both initial new Node checks failed on the
  absent Cancel control and pending-edit/Log behavior. Later tests FIRST failed
  for phantom My Changes after failed Apply, persisted legacy migration after
  cancelled preview, and full audit duplication in large grouped previews.
  Each now passes. Mid-write interruption, sibling/section/mixed-newline byte
  preservation, HTTP cancellation and actual frontend Apply/Log Undo passed
  when first added; existing atomic writing needed no modification.
- Files changed by THIS run: unittransfer/edb_balance.py,
  unittransfer/unit_sheets.py, unittransfer/server.py (only unit_sheets dispatch),
  web/js/unitsheets.js, web/i18n/en.json, tests/test_edb_balance.py,
  tests/test_sheet_pipeline.py, tests/test_unit_sheets_ui.js, this handoff.
  Concurrent Armory hunks in server.py and all protected Armory files/tests were
  left untouched, as were pre-existing TWCenter index deletions/untracked files.
- New string IDs, English ONLY: sheets.balance_cancelled,
  sheets.pipeline_order, sheets.balance_groups. New catalogue lines have no
  indentation. No other web/i18n catalogue or dev/i18n file was edited. Claude
  translates these strings. No new dependencies or added em dash characters.
- Required checks with UT_NO_BROWSER=1: python -m tests.test_edb_balance
  (35 passed), tests.test_sheet_pipeline (23 passed), tests.test_sheet_ops
  (41 passed), tests.test_unit_sheets (36 passed), tests.test_sheet_native
  (8 passed), tests.test_web_modules (130/130 passed),
  node tests/test_unit_sheets_ui.js (all checks passed), git diff --check
  (exit 0). tests.test_i18n ran twice and FAILED 42/45: missing concurrent
  armory.* UI IDs and eng.armunit.* IDs/templates, including invalid_slot,
  choose_character and character_changed. The later run also sees the new
  armory.anim_scale* family. No Phase 114 ID is missing or drifting. This shared
  checkout-wide gate still needs rerunning after the other run's catalogue
  work is reconciled; no passing global i18n result is claimed.
- Python used the existing ignored .tmp/phase110-step4-runner/sitecustomize.py
  via PYTHONPATH for the documented sandbox temporary-directory mode issue;
  no runner changes. Only self-cleaning TemporaryDirectory fixtures and local
  fixture HTTP servers were used; servers were shut down and joined. No real
  mod, original reference, browser or installed-game verification was used.
- Live account checks succeeded at 8%, 16%, 21% and 25% used in the five-hour window,
  below the authorized 90%-used stop. Weekly usage is not the stop threshold.
  No credits spent/reset. No commit, tag, build or release. No unresolved legacy
  policy question arose. Cancellation is cooperative, not process termination;
  no power-loss or cross-program final-rename locking guarantee is claimed.

## 2026-11-07 - Phase 113 completed, ready for Claude review

- Finished experience/maximum-pool acceptance with fixture-only golden tests
  and a small audit/outcome fix. Read Phase 113, archived Phase 112, its Finished
  note, the prior handoff/checkpoint, workflow review, both original legacy
  scripts and lookup-table samples. Original scripts were read only, never run.
- Tests FIRST: the first new engine run (26 tests) had 2 failed subcases for
  unsupported categories and 120 explanation subcase errors for missing audit
  fields. Numeric chain/cap/Beast, byte preservation, repeat-run and duplicate
  rejection assertions passed. The first new service run (11 tests) had 2
  errors for missing lookup_column, one per stage. The new Node audit-rendering
  test passed before engine edits. Additional T0-T4 and custom-key import/edit
  tests passed before engine edits. A later conflict-audit test first failed
  with missing override_candidates, then passed after retaining those details.
- Engine now captures race, category, unit tier, known depth or null, capped
  barracks tier, candidate rule key, column, raw cell and row-presence flag
  before skips or overrides. Winning overrides show their exact selector/value;
  conflicting outcomes retain all matching selectors/values. A missing column
  or row has a null cell, not an invented zero. Candidate cells on skipped or
  overridden entries are context, not applied values. Existing numeric behavior
  and token-only patching are retained.
- Unsupported categories now have unsupported_unit_category:<category> when
  absent from the selected project's nonempty table. Available categories come
  from table keys, with no global category/race vocabulary. Empty tables still
  report missing_lookup_row. Tests prove adding ship to the project makes it
  supported, and invented Aurora/levy keys import, edit and reload independently
  for both tables without changing project defaults.
- Verified exit items 1-5: six-level chain selects T1,T2,T3,T4,T5,T5; every
  unit-tier column T0-T4; Beast X maps to X/beast; BG/missing tier, missing row,
  missing column, invalid cell, unsupported category and conflicting duplicate
  keys preserve values or refuse the run with named errors. Unit/building/level
  overrides outrank broader overrides and table/classification/fractional skips.
  Golden tests include literal positive selected cells from the original Elf
  infantry/beast tables, hand-derived at depths 2-5, plus custom fixture tables.
- On the same fractional-pool row, experience changes and pool skips. Each
  independent stage masks only its own numeric token and compares every other
  Latin-1/CRLF byte, including initial pool, replenishment, requirements,
  conditions, comments and the other stage's value. Every skipped/invalid row
  remains byte-identical. Repeated runs produce zero changes. Disposable service
  fixtures verify exact independent-stage ZIP and Apply bytes, complete cell
  audit logs, repeat preview and Log Undo restoring the original bytes.
- Files: unittransfer/edb_balance.py, tests/test_edb_balance.py,
  tests/test_sheet_pipeline.py, tests/test_unit_sheets_ui.js, and this handoff.
  UI renderer changes were unnecessary: Node verifies the existing escaped JSON
  preview exposes both stages' cell/selector details and fractional skip reason.
- New string IDs: none. Added structured audit keys and a machine outcome code
  using the existing audit format, with no new prose labels/messages. No i18n
  catalogue, dev/i18n, STATE.md, ROADMAP.md or ROADMAP_ARCHIVE.md was edited.
- Required checks passed with UT_NO_BROWSER=1:
  python -m tests.test_edb_balance (31), tests.test_sheet_pipeline (12),
  tests.test_sheet_ops (41), tests.test_unit_sheets (36),
  tests.test_sheet_native (8), tests.test_web_modules (130/130);
  node tests/test_unit_sheets_ui.js (all cases, exit 0);
  git diff --check (exit 0). Also ran tests.test_i18n: 45/45 passed.
  Python used the existing ignored .tmp/phase110-step4-runner/sitecustomize.py
  via PYTHONPATH for the previously documented sandbox temp-directory mode
  issue; no runner edits. Test temp directories clean up through existing
  TemporaryDirectory cleanup. No real mod folders were used or changed.
- Live account checks succeeded at 1%, 3% and 4% used in the five-hour window,
  below the active run's 90%-used stop. Weekly usage is not the stop threshold.
  No credits spent or limits reset. No browser/manual installed-game test is
  claimed; UI verification is Node. No unresolved Phase 113 question remains.
  No commit, tag, build or release. Pre-existing TWCenter index deletions and
  unrelated untracked files were preserved. Claude owns review and archiving.

## 2026-11-07 - Phase 112 completed, ready for Claude review

- Updated this existing entry after the user's settlement decision resolved the
  earlier stop. Intentional compatibility exception: use EACH LEVEL'S OWN
  city/castle header, with unspecified levels receiving no city multiplier and
  no inheritance. The legacy script instead uses the first explicit header
  for the entire chain. The named golden test asserts hall-castle gives 0.2,
  not legacy 0.18, after hut-city. Explanations and the translated UI note
  explicitly expose the per_level_header policy.
- Tests FIRST: added the golden, rounding, explanation, profile/API, byte and
  Node acceptance tests before engine/UI edits. Initial test_edb_balance ran
  22 tests with 9 errors across four new methods (six rounding subcases), for
  absent depth/input/policy/rounding fields. Initial test_sheet_pipeline ran
  10 tests with one error for absent profile_rules. Node failed its new
  pre-preview effective-profile visibility check; its explanation rendering
  check already passed because the UI renders escaped audit JSON. Numeric
  golden values already passed. A later export-policy regression failed on
  missing profile_rules.json before that file was added. Corrected a test
  assumption that compact service previews contain full EDB text; they
  intentionally omit it. Export bytes are compared with an independent fixture.
- Engine audit context now survives changed, unchanged, skipped and invalid
  outcomes. It includes original numeric tokens/raw line/annotations, graph
  policy/errors/notes, known depth or null, maximum depth, settlement and
  applicable multipliers. Replenishment includes raw and resolved endpoints,
  fallback direction, rule tier, interval, reciprocal, sequential city/cavalry
  products and both six-decimal rounding inputs/outputs. Empty rounding_steps
  means no calculation was performed, including skips and explicit overrides.
  Existing numeric behavior is retained; no guessed zero depth is introduced.
- Read-only profile_rules describe settlement, Beast/native cavalry, malformed
  Beast reporting, endpoint fallback, single-level, rounding and graph policies.
  They accompany preview/load responses and exports (profile_rules.json).
  The UI shows effective editable multipliers/policy even before a preview and
  keeps compatibility rules separate from editable recipe keys.
- Acceptance verified: single-level E only; three-level E=10, X=7.5, L=5;
  branches, equal/unequal merges, disconnected root, cycle and unknown edge;
  shortest-root and reject-ambiguous; city/castle/unspecified; cavalry and
  infantry; Beast and malformed Beast; pool below 1; either missing endpoint,
  both absent, missing rule and invalid endpoints. Boundary cases include
  1/3, 1/7, exact binary half cases 1/128 and 1/640 and decimal values on either
  side of the six-place boundary. Node checks exact explanation fields/values,
  failure details, effective profile visibility and escaping of supplied input.
- Replenish-only golden output masks only the rate token and compares every
  other Latin-1/CRLF byte, including requirements, conditions, comments, initial
  pool, experience and maximum pool. Repeat runs have zero changes. A disposable
  temp mod also verifies exact ZIP and Apply bytes, repeat preview with zero
  changes, and Log Undo restoring original bytes. Temp fixtures clean up.
- Files: unittransfer/edb_balance.py, unittransfer/unit_sheets.py,
  web/js/unitsheets.js, tests/test_edb_balance.py, tests/test_sheet_pipeline.py,
  tests/test_unit_sheets_ui.js, web/i18n/{en,de,es,fr,pl,ru,tr,zh-Hans}.json,
  docs/ROADMAP.md (only the permitted checkpoint paragraph), and this entry.
  Added two messages with proper translations in all eight catalogues. Polish
  and Russian files were absent, so new draft catalogues contain just these
  messages; other messages retain normal English fallback. Their existence
  also makes these draft locales available through the existing locale list.
- Final required checks passed with UT_NO_BROWSER=1:
  python -m tests.test_edb_balance (22), tests.test_sheet_pipeline (10),
  tests.test_sheet_ops (41), tests.test_unit_sheets (36),
  tests.test_sheet_native (8), tests.test_web_modules (130/130),
  tests.test_i18n (45/45); node tests/test_unit_sheets_ui.js (all named cases
  and VM assertions, exit 0); git diff --check (exit 0). Python used the
  existing ignored .tmp/phase110-step4-runner/sitecustomize.py via PYTHONPATH
  for the previously documented sandbox temp-directory mode issue. No runner
  edits made. Git's LF-to-CRLF notices are not whitespace failures.
- Live account usage succeeded at start/checkpoints: 31%, 34%, 35% used in
  the five-hour window, below this run's authorized 90%-used stop. Weekly
  usage is not the stop threshold. No credits spent or limits reset.
- All five requested exit items are done. No manual browser or installed-game
  verification is claimed; UI verification is the Node VM. Read the original
  legacy script and table samples only; never executed scripts or changed real
  mods/original references. No unresolved Phase 112 question remains. No commit,
  tag, build or release; no STATE.md edit. Other working-tree changes preserved.

## 2026-11-07 - Phase 111 effective balance profile recipe fix

- Profile recipes now resolve the single project profile through
  edb_balance.profile_of. Its saved name is used when set, otherwise the
  effective name is default. Other profile names are refused. Target columns
  come from effective values, including defaults and custom keys, with name
  excluded and boolean, text and numeric types retained. Execution uses the
  effective old value for numeric coercion and creates the overrides object
  if an older project omitted it.
- Sheet service responses now include balance_effective without storing defaults
  in the project. The Balance creator uses those response values for its keys,
  operation choices and profile target. It excludes name, saves default when no
  name is set, and offers only set for non-numeric keys. The frontend retains
  its saved-profile fallback for responses without balance_effective.
- Test first: observed Python failures for the default target, missing effective
  response and missing custom effective keys; observed Node failures for the
  default-profile picker and the formerly offered name key before implementation.
  Passing regressions verify barracks_cap with balance_profile {}, save, dry-run
  preview without disk writes, real run, snapshot undo restoring {}, and refusal
  of another profile name. The cap remains 5 because the compatibility profile
  requires it. Node verifies response keys, default target, numeric operations,
  text/bool set-only choices and exclusion of name. Python also verifies typed
  custom effective keys and numeric execution for a key outside static defaults.
- Files changed in this fix: unittransfer/sheet_ops.py,
  unittransfer/unit_sheets.py, web/js/unitsheets.js,
  tests/test_unit_sheets.py, tests/test_unit_sheets_ui.js and
  docs/CODEX_HANDOFF.md. Existing uncommitted work was preserved. No new
  user-visible strings were needed and no translation files were edited in
  this fix. No commit or release was made.
- Required checks actually run and passed:
  python -m tests.test_unit_sheets: 36 tests;
  python -m tests.test_sheet_ops: 41 tests;
  python -m tests.test_sheet_pipeline: 9 tests;
  python -m tests.test_sheet_native: 8 tests;
  python -m tests.test_edb_balance: 12 tests;
  python -m tests.test_web_modules: 130/130 checks;
  python -m tests.test_i18n: 45/45 checks;
  node tests/test_unit_sheets_ui.js: all named cases and VM assertions passed,
  exit 0; git diff --check: passed. Python used UT_NO_BROWSER=1 and the
  existing ignored .tmp/phase110-step4-runner/sitecustomize.py via PYTHONPATH
  for the previously documented sandbox temporary-directory mode issue. No
  runner edits made. Git reported existing LF-to-CRLF warnings only.
- Live account checks succeeded at 25% and 26% used in the five-hour window,
  below the authorized 90%-used stop. Weekly usage was 55% and is not the stop
  threshold. No credits or reset used.
- No requested implementation remains. No manual browser or installed-game
  check was performed. UI verification uses the Node VM with stub responses
  and reconstructed controls; undo uses the service's saved project snapshot.

## 2026-11-07 - Phase 111 repaint control-state regression fix

- Mass edit now stores its open state, column, operation, value, replacement,
  mode, recipe name and recipe picker in USHEET.controls. Input, change and
  toggle handlers record choices before asynchronous requests rebuild the UI.
  Paint restores those choices through review, Cancel, Confirm, undo/redo and
  query. A missing column falls back to the first currently offered column;
  an unavailable operation falls back to set.
- Balance stores its open state, profile recipe picker and creator name, key,
  operation and value in the same window state. Changing the profile key still
  resets the operation to set. Rendering checks removed keys and keys whose
  value changed from numeric to text/bool. Draft controls remain outside saved
  projects and history snapshots. Loading a recipe also records its values,
  including numeric zero, so later repaints preserve them.
- Test first: added four Node regressions and observed all four fail before
  implementation. The focused harness now reconstructs these controls from
  rendered HTML and dispatches their inline handlers, rather than retaining
  stale mock controls across innerHTML replacement. Verified review and Cancel
  preserve all five Mass edit controls and its open state; the second run sends
  the same column, operation, value, other and matching mode. Also verified
  Confirm, undo, redo, query, closing/reopening sections, recipe picker/name,
  zero loading, escaped input values and missing-column/key fallback.
- Files changed for this fix: web/js/unitsheets.js,
  tests/test_unit_sheets_ui.js and docs/CODEX_HANDOFF.md. Preserved prior
  uncommitted work. Added no user-visible strings or translation edits.
  No commit or release was made. No prohibited files were edited.
- Required checks actually run and passed:
  python -m tests.test_unit_sheets: 33 tests;
  python -m tests.test_sheet_ops: 41 tests;
  python -m tests.test_sheet_pipeline: 9 tests;
  python -m tests.test_sheet_native: 8 tests;
  python -m tests.test_edb_balance: 12 tests;
  python -m tests.test_web_modules: 130/130 checks;
  python -m tests.test_i18n: 45/45 checks;
  node tests/test_unit_sheets_ui.js: all named cases and VM assertions passed;
  git diff --check: passed. Python used UT_NO_BROWSER=1 and the existing ignored
  .tmp/phase110-step4-runner/sitecustomize.py via PYTHONPATH for the previously
  documented sandbox temporary-directory mode issue. No runner edits made.
- Live account usage checks succeeded at 22% and 23% used in the five-hour
  window, below the authorized 90%-used stop. Weekly usage was 55% and is not
  the stop threshold. No credits or reset used.
- No requested implementation remains. No manual browser or installed-game
  check was performed. UI verification uses Node VM tests with stubbed API
  responses and reconstructed controls, not a full browser DOM.

## 2026-11-07 - Phase 111 follow-up Balance profile recipe creator

- Added a small creator beside the Balance profile recipe picker: name, current
  saved profile key, operation, value and Save. Numeric keys offer set, add,
  subtract, multiply, divide, percent, min, max and round. Text and boolean keys
  offer only set; changing the key resets the operation to set.
- Saves target.profile using the current saved profile name, plus column,
  operation and value, through unitSheetsSave. Server validation and its refusal
  reason use the existing request/error path. A successful save refreshes the
  profile picker. Values remain input strings for server validation.
- Files changed in this follow-up: web/js/unitsheets.js,
  tests/test_unit_sheets_ui.js, web/i18n/en.json and docs/CODEX_HANDOFF.md.
  Added 11 English message IDs only. Preserved all earlier uncommitted work and
  unrelated changes. No commit or release was made. No prohibited files edited.
- Test first: added three Node regressions before implementation. The initial
  run failed on missing creator controls, operation helper and save handler.
  After implementation, all three and all existing Node assertions passed.
  Tests verify the profile-target save payload, picker refresh, numeric/text/bool
  operation choices, key-change reset and visible server refusal reason without
  saving a recipe or adding history.
- Final checks actually run and passed:
  python -m tests.test_unit_sheets: 33 tests;
  python -m tests.test_sheet_ops: 41 tests;
  python -m tests.test_sheet_pipeline: 9 tests;
  python -m tests.test_sheet_native: 8 tests;
  python -m tests.test_edb_balance: 12 tests;
  python -m tests.test_web_modules: 130/130 checks;
  python -m tests.test_i18n: 45/45 checks;
  node tests/test_unit_sheets_ui.js: all named cases and VM assertions passed;
  git diff --check: passed. Python used UT_NO_BROWSER=1 and the existing ignored
  .tmp/phase110-step4-runner/sitecustomize.py via PYTHONPATH for the known sandbox
  temporary-directory mode issue. No runner changes were made.
- Live account usage checks succeeded at 17% and 18% used in the five-hour
  window, below the authorized 90%-used stop. Weekly usage was 54% at both
  checkpoints and does not set the stop threshold. No credits or reset used.
- No requested implementation remains. No manual browser visual check or
  installed-game apply was performed. UI behavior is verified by Node VM tests
  with stubbed API responses; the required Python suites also passed.

## 2026-11-07 - Phase 111 step 2 recipe recovery and mass-edit review

- Completed requested items (a)-(f). No commit or release was made. Preserved
  step 1 changes and unrelated working-tree changes. Did not edit viewer3d.js,
  ROADMAP.md, STATE.md, other web/i18n catalogues or dev/i18n files.
- (a) Removed recipe execution validation from validate_project/load_project.
  save_project compares recipes with the stored project under the project lock
  and validates only new or changed instructions. Invalid legacy recipes remain
  untouched across load, query and unrelated saves. API responses include an
  invalid_recipes name-to-reason map; explicit recipe execution revalidates the
  stored instructions. Regression fixtures include a targetless rule-column
  recipe and a blank set recipe, both surviving successful load and query.
- (b) Mass operations and fill first request dry_run. A separate review displays
  target_count and per-field before/after rows, capped at 100 with a remaining
  count. Confirm submits the captured request without dry_run, retaining the
  revision, source token, filter, mode and targets. Cancel makes no request and
  adds no history. Refusals show the server reason and add no history. Operate
  and paste include selected/matching mode and current where; matching mode is
  captured before pending cell edits can repaint its control.
- (c) Blank native grid sets now reach unitSheetsPost and show the server's
  explicit-clear error, as mass blank sets already did. Clear remains an
  explicit operation choice.
- (d) Saved recipes include target.view, including rules:<kind>. The picker
  sorts current-view recipes first and labels/disables invalid recipes with
  their reported reasons. Loading restores column, operation, value and other
  using nullish fallback so zero survives. Recipe Run uses the shared review.
  The backend executes saved recipe fields and checks the native/rule scope.
- (e) Profile recipes resolve target.profile against balance_profile.name and
  update the matching known profile key, using defaults for absent keys. Numeric
  set/arithmetic and text/bool set validate before staging, including during
  preview. Changes use save_project and normal UI snapshot history. The Balance
  panel has a profile-recipe picker and Run button using the same review.
- (f) Node request-stub tests verify Cancel has no staging request/history,
  Confirm stages once, repeated Confirm cannot duplicate it, and confirmed mass
  and profile operations undo and redo with one project save each.
- Changed unittransfer/sheet_ops.py, unittransfer/unit_sheets.py,
  web/js/unitsheets.js, web/i18n/en.json, tests/test_unit_sheets.py,
  tests/test_unit_sheets_ui.js and this file. Added 11 English message IDs only.
- Test-first evidence: initial Python regressions failed on legacy recipe loads
  and profile execution; initial Node regressions failed on missing review,
  scoped recipe saves/zero loading and the profile picker. Separate regressions
  reproduced silent blank grid sets and mode reset during a pending-cell
  repaint before their fixes. One intermediate i18n check failed on a joined
  invalid-recipe label; using a complete translated template fixed it.
- Final checks actually run, all passed with UT_NO_BROWSER=1 for Python:
  python -m tests.test_unit_sheets: 33 tests;
  python -m tests.test_sheet_ops: 41 tests;
  python -m tests.test_sheet_pipeline: 9 tests;
  python -m tests.test_sheet_native: 8 tests;
  python -m tests.test_edb_balance: 12 tests;
  python -m tests.test_web_modules: 130/130 checks;
  python -m tests.test_i18n: 45/45 checks;
  node tests/test_unit_sheets_ui.js: all named cases and VM assertions passed;
  git diff --check: passed. Python used the existing ignored
  .tmp/phase110-step4-runner/sitecustomize.py via PYTHONPATH for the known
  sandbox temporary-directory mode issue. No tracked runner change was added.
- Live account usage checks succeeded at 12%, 14% and 16% used in the five-hour
  window, below the authorized 90%-used stop. The first proxied request failed;
  direct endpoint requests succeeded. Weekly usage was 54% at the final check
  and is not the stop threshold. No credits were purchased or limits reset.
- No requested implementation remains. No live-browser visual check or
  installed-game apply was run; verified behavior is based on Python service
  regressions and Node VM request-stub tests, not manual browser interaction.

## 2026-11-07 - Phase 111 step 1 backend mass-operation safety

- Completed the authorized backend step. No commit or release was made. Kept
  pre-existing Reference/TWCenter deletions and unrelated untracked files intact.
  Did not change JavaScript, viewer3d.js, ROADMAP.md, STATE.md, other web/i18n
  catalogues or dev/i18n files. Step 2 UI work remains outside this request.
- (a) operate accepts optional mode selected (default) or matching and the
  existing where expression. The server resolves matching IDs from the full
  current native or rule table, independent of pagination and submitted IDs.
  Selected IDs outside that set reject the complete operation before staging.
  Missing where means the unfiltered table. Paste also checks its IDs against
  where. Recruitment rows remain read-only.
- (b) Numeric conversion rejects booleans, including native sets, pasted cells
  and arithmetic operands. Explicit numeric zero remains a value.
- (c) Empty strings, whitespace, None and empty lists cannot set or paste empty
  fields. Non-clear operations cannot produce an empty replacement either.
  Errors direct callers to clear. Explicit clear still refuses required tuple
  members. Rule operations/paste follow the same rule; an older test expecting
  blank set to clear a rule value now verifies refusal then explicit clear.
- (d) operate and paste accept dry_run true. They validate and return the same
  changes and target_count as staging, with the original project/revision and
  prospective table rows. No project save or history entry occurs, including
  when a file is absent or requires legacy schema migration. Tests verify exact
  project bytes and the existing file's mtime remain unchanged.
- (e) Project validation checks recipes on save/import and load. It validates
  operation names, writable columns, types, expression syntax, arithmetic
  operands and optional scope. Native scopes use view; rule scopes accept
  view rules with rule_table or rules:<table>. Profile scope resolves the
  existing singleton balance_profile.name and its known settings, not an
  invented profile collection. Unknown tables/profiles fail. Zero and a null
  optional target round-trip without coercing the saved recipe payload.
- (f) Added individual arithmetic branch tests plus copy, text replace and
  attribute deduplicate coverage. Mixed unit-size, attack, attribute and
  classification operations across Guard/Horse are staged, undone one operation
  at a time through project snapshots, then redone using the existing save API,
  exactly as native sheet UI history does. These are staging undo/redo checks,
  not game-file apply/transfer undo. Unknown attributes and unedited weapon tuple
  members survive. Every fixture mod file is snapshotted for bytes and mtime
  before staging and compared after each dry run, stage, undo and redo.
- Changed unittransfer/sheet_ops.py, unittransfer/unit_sheets.py,
  tests/test_sheet_ops.py, tests/test_unit_sheets.py, tests/test_sheet_native.py,
  web/i18n/en.json and this file. Added four English message IDs using _i18n.msg.
- Test-first evidence: new regressions failed on filtered targets, native
  booleans, blank edits, dry-run writes and unvalidated recipes before fixes.
  Follow-up regressions failed on rule blank paste, invalid recipe container
  values, infinite expression constants and null targets before fixes. Existing
  arithmetic/copy/replace/deduplicate behavior already passed its new coverage.
  Initial i18n run was 44/45 because the old missing-value message became unused;
  keeping that message in the shared validator restored 45/45.
- Final checks actually run, all passed with UT_NO_BROWSER=1 for Python:
  python -m tests.test_unit_sheets: 29 tests;
  python -m tests.test_sheet_ops: 41 tests;
  python -m tests.test_sheet_pipeline: 9 tests;
  python -m tests.test_sheet_native: 8 tests;
  python -m tests.test_edb_balance: 12 tests;
  python -m tests.test_web_modules: 130/130 checks;
  python -m tests.test_i18n: 45/45 checks;
  node tests/test_unit_sheets_ui.js: all named cases and VM assertions passed;
  git diff --check: passed. Python used the existing ignored
  .tmp/phase110-step4-runner/sitecustomize.py via PYTHONPATH for the known sandbox
  mode-0700 temporary-directory issue. No tracked runner workaround was added.
- Live account usage endpoint checks succeeded at 5%, 7% and finally 9% used in
  the five-hour window. Completed below the authorized 90%-used stop. Weekly
  usage was 53% at the last check and is not the stop threshold. No credits were
  purchased or limits reset. No installed-game or live-browser check was run.

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


## 2026-11-08 - Corrected missing-card rules and recruitment cache

This entry supersedes the fallback and catalogue-status claims in the earlier
missing-card entry. The five original IDs have already been merged and translated.

Changed behavior and files:

- `unittransfer/edit.py`: game behavior is mercs/merc only for mercenary units
  outside EOP; an existing pinned card_pic_dir/info_pic_dir covers all factions
  for ordinary units; otherwise check each faction and use generic if absent.
  There is no base-game all-folder fallback. EOP mercenary units prefer faction
  pictures when enabled and then use mercs/merc. Only generic results are warnings.
  A non-EOP mercenary report has at most one warning per picture kind, independent
  of ownership/recruitment. Folder indexes and picture presence are request cached.
- `unittransfer/mod.py`: recruiting_factions is a cached_property mapping every
  unit type to explicit EDB recruiting factions. Existing drop_caches invalidation
  clears it after writes. faction_unit_cards reuses EOP directory detection and
  reads luaPluginScript.lua as text only, defaults on with eopScripts present,
  and recognizes handleUnitCards(false). Comments and quoted examples are ignored.
  Its cached_property uses the same invalidation. No Lua execution is performed.
- `web/js/editor.js`: generic results retain warning styling; real shared-picture
  fallback notes are quiet and grouped into one line listing factions per picture.
  Imports suppress only rows covered by their destination folders, including the
  shared mercs/merc destination. HTML text and paths remain escaped.
- `tests/test_card_coverage.py`, `tests/test_card_coverage_ui.js`: synthetic fixtures
  only, extended for base/EOP mercenaries, disabling/default scripts, pinned and
  missing pinned paths, no all fallback, generic severity, cached folder indexes,
  one EDB scan across different units and cache invalidation, and grouped UI notes.
- `.tmp/cards_strings.json`: full current feature set of seven strings. Four
  original texts/IDs are unchanged. New IDs: editor.missing_mercenary_unit_card,
  editor.missing_mercenary_info_image, editor.shared_mercenary_picture_note.
  Old ID now unused: editor.missing_card_fallback. No catalogue edits made.
- `.tmp/cards_handoff.md` and `docs/CODEX_HANDOFF.md`: change records updated.

Tests first and actual verification:

- Before implementation: tests.test_card_coverage had 5 failures and 2 errors
  across 12 tests. It exposed all fallback, per-faction non-EOP mercenary rows,
  pinned-picture warnings, absent severity, ignored EOP false, and 3 EDB scans
  instead of 1. Node failed because the real fallback retained warning styling.
- An intermediate implementation run failed on a Python regex quoting mistake;
  corrected it. A Node assertion was corrected to retain the note for an import
  destination outside the selected factions (spain). These failures were resolved.
- UT_NO_BROWSER=1 python -m unittest tests.test_card_coverage: 15/15 pass.
- UT_NO_BROWSER=1 node tests/test_card_coverage_ui.js: all assertions pass.
- UT_NO_BROWSER=1 python -m unittest tests.test_web_modules: 130/130 pass.
- git diff --check: pass.
- Synthetic 30,000-pool in-memory fixture benchmark, 12 warm calls: first report
  167.90 ms, warm median 5.69 ms and max 20.49 ms. The previous per-open EDB scan
  alone measured median 177.73 ms. This verifies repeated opens avoid that scan;
  it is not a measurement of total unit-open latency on DaC EUR. Initial map
  construction still costs one EDB walk per mod cache lifetime.

Limits and status:

- No real mod, game, or browser was opened or changed. Total app latency and
  visual layout remain unverified; no claim of an observed DaC EUR 100 ms target.
- Explicit faction clauses are expanded; other recruitment requirements are not
  evaluated. Lua is inspected statically, so runtime control flow is not evaluated.
- Builder files, builder fixtures/tests, test_i18n.py, and existing translation
  changes were left alone. Previous handoff entries are preserved.
- Latest usage checkpoint: five-hour window 55% remaining. Checks are periodic
  and account-wide; the normal 50%-remaining pause applies to this task.
- No commit, tag, build, release, dependency change, or catalogue edit performed.
  Claude still needs to merge and translate the three new staged IDs.
