# Deterministic builder rules (Phase 103)

`unittransfer.builder_calculator.calculate(design, engine_rules=...)` consumes
the Phase 102 packet and returns `native`, `explanations` and `metadata`.
`native` goes through `builder_contract.output_values` and the existing typed
`sheet_ops.FIELDS`. There is no alternate EDU parser, stat staging path, save
path, UI, route or writer. Native profile 1 calculates no balance defaults;
only explicit final native pins are projected. Combat Reforged requires its
explicit pinned profile revision, never a folder-name inference.

Rules attribution: lupinemaverick, based on MUG Unit Builder v1.5 / MUG Unit
Creation Guide, with Combat Reforged work for King Siegfried. The user reported
author permission to reuse. No new license is inferred. Read-only snapshots
were verified against every SHA-256 in `upstream/SSR_BUILDER_AUDIT.json`.
No upstream script, generated HTML, test or Lua was executed.

## Data provenance

`unittransfer/builder_rules.json` contains literal data for revision
`d4ed9368d0db3da2000bc895e96f52a83b93cb67`. Preset IDs are internal keys;
display labels belong in the English catalogue when Phase 104 adds controls.
The source audit remains historical. These rules supersede its open formula
decisions only as described below.

| Data / arithmetic | Effective source and values |
| --- | --- |
| Eight archetypes | `build.py` generated CATEGORY_BASE, corrected by `audit_rules.js` and `combat_rules.js`. Royal morale 16, Martial 13, Household 12, Career 10, Urban 9, Rural 7, Warrior 8, Emergency 5. Attack training 2/2/1/1/0/0/0/-1; Skill training 3/2/1/1/0/0/0/0. Equipment grade removes archetype equipment bonuses. |
| Foot/mounted quality | `audit_rules.js`, then r2 `combat_rules.js`. Foot Attack 3/2/1/0/-2; mounted 7/5/3/1/-3; Skill 2/1/1/0/0; delay -30/-20/-10/0/20; heat -3/-2/-1/0/1, in Exceptional through Inferior order. `build.py` renames Standard to Average. |
| Grades | `equipment_grade.js`. Artisan stat +2, recruit +15%, upkeep +10%; high +1/+7.5%/+5%; common 0/0/0; munition -1/-20%/-15%; poor -1/0/+10%. Royal forces artisan. Grade never creates worn armor or held shield from zero, and never grades barding. |
| Weapons | Base PRI_PRESETS/SEC_PRESETS, `reforged.js` category mapping, mounted rows and sword contexts in `audit_rules.js`, revised Attack/handling in `combat_rules.js`, `preset_filters.js` knife normalization, lance tag removal in `armor_loadouts.js`, bill/greatsword proposals in `weapon_phase_a.js`. 33 primary presets, 7 secondary including none, 19 melee categories. Conditional attributes never add unconditional Attack. |
| Armor/layers/loadouts | Base ARMOUR_PRESETS/ARMOUR_LAYERS; positive Skill clamps in `combat_rules.js`; representative ensembles and two support layers from `armor_loadouts.js`. 26 bases/loadouts, 11 layers. Chosen weight activates 1/2/3 additional slots; inactive slots contribute nothing and saved choices stay intact. Base and active layers add once; explicit computed armor/heat/agility inputs take precedence. |
| Offhands | Base shield types/materials and `reforged.js` OFFHANDS, followed by r2 clamps. Empty 0/0, buckler Shield1/Skill2, small 3/1, medium 5/0, large 7/-1, dagger 0/2. Legacy combined Skill is clamped 0..1. Each slot's two-handed grip suppresses its held offhand. Defending secondary contributes for a ranged primary with a secondary present. |
| Horse data | Base HORSE_TYPES, HORSE_ORIGINS, HORSE_BARDING; audit terrain/heat and r2 horse-only barding destination. Six horse types use barding once in rider armor; camel/elephant do not use that horse rule. Infantry retained mount choices add no armor or mount heat. |
| Terrain/formation | Base TERRAIN plus four origins and explicit weight/specialty/weapon adjustments in `audit_rules.js`; terrain choices +2 from `unit_attribute_controls.js`. Automatic spacing follows `bibleFormationValues`; manual f_* spacing and ranks are preserved. Shared vocabulary owns formation tokens. |
| Cost/mental arithmetic | Base compute after `build.py` replacements, then audit and grade wrappers. Automatic recruit 500 + quality*200 + cavalry300 + worn armor*40; upkeep 120 + quality*40 + cavalry80 + worn armor*8; quality cost steps 3/2/1/0/-1. Custom battle cost is computed before Hybrid/grade. Training, discipline, morale clamps and subtype precedence follow those effective wrappers. |
| Upgrade defaults | `engine_profiles` data has vanilla and EOP weapon Attack +3/level, armor +2/level, source `engine_default`. These are the engine defaults documented by `M2TWEOP.setWeaponBonusModifier` and `setArmourUpgradeModifier`. M2EX also defaults to verified 3/2 and reads per-mod overrides from `data/descr_caps_ex.txt`. Vanilla and M2EX weapon bonuses apply to melee attacks only; the M2EX missile-upgrade switch stays off because its configuration key is unverified. |

Preset snapshots merge selected rows over the pinned tables. Effective inputs,
including `overrides.inputs`, then take precedence over preset numbers. Numeric
blank strings inherit defaults, matching the source form; an explicit blank
secondary attack disables that slot. Zero and false remain intentional values.
Unknown input and snapshot keys stay dormant. Selected identities, numbers,
roles and subtype eligibility are validated. Final `overrides.native` pins run
after all calculation and go through the same types and attribute quarantine.
Nothing mutates or overwrites the original design or preset snapshots.

## Rounding, explanations and deliberate differences

- JS half rounding is `floor(x + 0.5)`, including negative halves. Hybrid
  recruit cost is rounded first, then equipment grade is multiplied and rounded.
  Hand-entered costs retain their pre-grade meaning. Native cost pins are final.
  Grade does not affect quality, Skill, charge, delay or training.
- Defense contributions are core4, nonnegative training/quality/armor/handling,
  signed offhand, positive cavalry style and the Aggressive -1 exception. Only
  the defending slot contributes handling/offhand. The other slot's hypothetical
  defense stays metadata, not an invented dynamic-defense EDU directive.
- `explanations` records inputs/contributions, clamping/rounding context, final
  pins and omitted attributes. Each native field has a final result. Heat is
  calculated with an explanation but remains outside native columns, alongside
  armor sound and morale lock. Multiple formation types remain engine-shaped
  metadata because the current shared sheet field covers only member 5. Phase
  106 must use a shared extension or the reviewed native editor planner for
  those fields. This phase does not silently invent columns.
- The game accepts only spear, light_spear, prec, ap, bp, area, fire, launching,
  thrown, short_pike, long_pike, spear_bonus_12/10/8/6/4 and no as weapon
  attributes. Other attributes cause the game to refuse the unit. The builder
  always quarantines sp, spear_bonus_2 and custom proposals, including final
  pins. Fire is accepted at the builder boundary. The ordinary source-preserving
  editor vocabulary and patcher are unchanged. No hook_drag alias conversion.
- The upstream hiding wrapper can retain a manually supplied hide_forest even
  with its opt-out false. Here false removes it consistently. Upstream negative
  Attack can fall outside the shared typed contract; report an invalid design
  rather than silently emit or clamp it. Eligibility failures likewise produce
  internal ContractError codes rather than rewriting the input choices.

## Per-mod engine settings and UI notes

`load_engine_rules(mod_root, profile='eop')` reads
`eopData/eopScripts/luaPluginScript.lua`. It strips Lua comments and quoted/long
strings while preserving line offsets, then accepts a single literal integer
argument (0..1000) for each exact M2TWEOP setting call. It does not evaluate
expressions, imports, branches or Lua. Multiple calls, expressions, absent,
unreadable or invalid scripts retain engine defaults; ambiguous calls have an
explicit status. Each modifier has value, source, verified and status. A source
such as `eopData/eopScripts/luaPluginScript.lua:4` identifies the observed literal,
not proof that a conditional branch executed in game. M2EX never borrows an
EOP setting as a claim of M2EX support.

For a toolkit mod entry, its `m2ex` flag selects M2EX and its `root` supplies the
folder. For a folder path, pass `profile='M2EX'` explicitly. M2EX reads only the
mod's plain-text `data/descr_caps_ex.txt`, accepting `weapon_upgrade_points <int>`
and `armour_upgrade_points <int>` independently. Negative values clamp to zero.
Each observed value records `data/descr_caps_ex.txt:<line>` and `literal_config`
(or `clamped_config`); absent keys or an absent/unreadable file retain verified
3/2 with source `engine_default`. No parent, game-folder or EOP fallback is read.
Vanilla keeps fixed 3/2 without reading mod settings. These M2EX defaults, keys
and formulas use the source findings supplied by the user, tested with fixtures.

The read-only helper and calculator take separate arguments so repeated pure
evaluation cannot depend on changes to an installed mod. Engine rules are copied
into the result. Upgrade levels calculate a separate metadata preview from the
final base stats; they never bake upgrades into EDU and count them twice later.
For vanilla and M2EX, missile, thrown and siege-missile primary attacks receive
no weapon bonus. M2EX's missile-upgrade switch stays off; its file key has not
been verified. EOP preview behavior is unchanged.

The helper returns `notes: [{id, params}]`. English text exists only in
`web/i18n/en.json`, IDs `builder.upgrade_card_note` and
`builder.m2ex_missile_unverified`. A UI displaying upgrade values must render these
notes: the game's unit card shows +1 per level while vanilla applies weapon +3,
armor +2, with vanilla weapon bonuses applying only to melee; mod settings can
change the actual values. The parameters use the observed values, including 1/1. Phase 103 adds no UI. Installed DaC EUR was not
read or modified in this run; its reported 1/1 settings are exercised with a
synthetic Lua fixture, not claimed as an installed-mod verification.

## Guards subtype decision (2026-11-08)

`build.py` and `audit_rules.js` add trait_guards to Defense Skill; the final
`combat_rules.js` breakdown has `guards: checked('trait_guards') ? 1 : 0`.
There is no upgrade-level input or call to either armour-upgrade modifier in
this contribution. It is a builder subtype bonus, separate from armor upgrades.
The user decided on 2026-11-08: "just use what the wiki says". Use +2 Defense
Skill following the upstream builder's own index.html help text:
"Guards: -1 melee Attack / +2 Defense Skill." This deliberately differs from
the upstream final combat_rules.js breakdown's +1. With core4 and all other
Skill terms zero, Guards produces Skill6. No engine modifier enters this term.

Guards subtracts 1 Attack from each melee slot; missile Attack is unchanged.
It adds 1 morale only when final discipline is disciplined, matching upstream
`guardMorale = checked("trait_guards") && discipline === "disciplined" ? 1 : 0`.
Guards does not change discipline; Reckless still makes it impetuous and prevents
that morale bonus. The Guards selection stop has been removed.

Not verified: battle execution, actual execution of EOP settings, the M2EX
missile-switch configuration key, upstream browser parity, imported-project
migration, Phase 104 controls or Phase
106 Apply/Undo. The source tests were read as regression evidence only. Toolkit
tests use synthetic designs and fixture data; no game files are written.
