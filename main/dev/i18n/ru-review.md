# Russian translation review notes

These notes preserve batch decisions for native-speaker and final UI review.
Automated validation is not native-speaker or visual approval.


## Batch: ru-armory-review

# Russian Armory Studio review

519/519 armory strings merged through i18n_todo.py, in four bounded batches.
No missing, stale or extra IDs in this namespace. No termbase edits.

Exemptions (only different English senses):

- `armory.exp_free_turn_title`, `armory.head_as_one_title`,
  `armory.look_closer_title`, `armory.stamp_rot`, `armory.uv_hint`: `turn`
  means geometric rotation, not a turn of the campaign. Uses поворот,
  вращение or their verbs.
- `armory.frame_all`, `armory.key_frame_all`, `armory.key_frame_selected`:
  `frame` means fit objects into the viewport, not an animation frame.
  Uses «Показать ... целиком».
- `armory.statistics`: `stats` refers to geometry statistics (objects,
  triangles, vertices), not a unit's game characteristics. «Статистика».

Terminology choices for native review:

- Asset / asset library: «ресурс» / «библиотека ресурсов».
- Sheet: «лист»; attachment sheet: «лист креплений», following the existing
  attachment term. Main sheet: «основной лист».
- UV islands: «UV-острова» (short «острова» in context).
- Bake: «запечь» / «запекание»; resample: «пересчитать».
- Kitbash workbench: «мастерская сборки из частей»; Armory Studio stays a
  product name. Preset: «пресет».
- Pull a part into the model: «Добавить»; rig to bones: «Привязать к костям».
- Generic/specialized normal maps: «Общий режим (одна настройка)» /
  «Отдельно для каждого материала».
- Non-manifold geometry: «неманифолдная геометрия»; smooth normals:
  «нормали сглаживания».
- Blend modes use familiar image-editor Russian: Умножение, Перекрытие,
  Экран, Мягкий свет, Жесткий свет; Laid on is «Обычное наложение».
- Skins are rendered «текстура» where they mean the model's chosen skin;
  material skin is «кожа тела» to distinguish it from leather «кожа».

Both exporter warnings about quality loss remain explicit. Weight transfer
retains old-weight replacement, five smoothing passes, 5 cm distance limit,
left/right bone separation, and shield/weapon/body restrictions. Internal
keywords and suffixes (primaryactive0, secondaryactive0, _opt, type__name,
_01, _02, .mesh, .texture) remain literal.

No UI visual validation or promotion. Main agent owns final integration.


## Batch: ru-buildings-review

# Russian buildings batch

Completed all 556 strings using four bounded batches through i18n_todo.py.
All final merges passed. No changes to shared docs or termbase.

## Exemptions

- `buildings.level_3`, `buildings.level_key`: `level:` is a literal internal
  key prefix, not the user-facing label for a level. Retained verbatim;
  exempted `level` only.
- `buildings.its_battle_model_has_no_texture`,
  `buildings.units_without_battle_model_texture`: "turn up" means appear,
  not a campaign turn. Exempted `turn` only.
- `buildings.this_mod_ships_no_file_at`: "ships" means includes, not ships
  as vessels. Exempted `ship` only.

## Terminology

- line = «цепочка» for a building chain, «строка» for an actual file line.
- tier = «ступень», level = «уровень», recruitment = «набор».
- city/castle twin = «парный вариант», half = «вариант».
- mirror = «синхронизировать» for the action copying missing recruits.
- capability = «возможность», hidden resource = «скрытый ресурс».
- Unknown placeholder names are kept separate from inflected prose.

Native-speaker review and visual layout checks are still pending.


## Batch: ru-campaign-small-review

# Russian campaign-small review

177 strings: campbrowse 21, campdb 17, campevents 74, campforts 65.

Exemptions, all for ship (English includes/bundles, not a vessel):
- campbrowse.campaigns_read_in_ms
- campbrowse.every_campaign_this_mod_ships_with
- campbrowse.nothing_in_to_read_a_menu
- campbrowse.ships_map_layers

Choices:
- campdb.s_campaign_constants follows the unknown mod name, so uses a colon.
- campforts.kind placeholders are isolated as object labels to avoid gender
  disagreement between fort, watchtower and resource.
- year counters without plural objects use «годов за ход» or
  «интервал в годах» rather than a suffix that fails for some numbers.
- Literal campaign header, true/false values and script/text keys preserved.
- Distinguish a region's section in the file from its geographic province.

All strings merged through existing checker. No termbase edits, promotion
or visual validation.


## Batch: ru-campmap-review

# Russian campmap review

314 strings, translated in three bounded batches and merged through the
existing termbase, placeholder, tag and plural checker.

## Exemptions

- `campmap.building_the_composite`: building means constructing an image,
  not a settlement building (`building`).
- `campmap.click_a_province_to_inspect_it`: turn on is enable paint mode,
  not a campaign turn (`turn`).
- `campmap.comp_key`: literal internal composite cache key; terrain is a
  key token, preserved verbatim (`terrain`).
- `campmap.has_no_campaign_map_this_tool`,
  `campmap.ships_its_own_so_that_layer`: ships means includes, not vessels
  (`ship`).
- `campmap.port_marker`, `campmap.port_pixel`,
  `campmap.port_pixels_undecided`,
  `campmap.region_id_tiles_settlement_at_game`,
  `campmap.settlement_character_and_port_names_beside`: port is a harbor,
  not transferring data between mods (`port_verb`).
- `campmap.the_campaign_map_as_a_surface`,
  `campmap.the_heights_as_a_surface_with`: turn means rotating the camera,
  not a campaign turn (`turn`).
- `campmap.this_is_a_marker_pixel_and`: orphan means a marker with no
  owning region. «Бесхозный» expresses that fault; «неиспользуемый» would
  conflate it with unused model cleanup (`orphan`).

## Choices

- Fit = «Вписать»; Paint = «Рисование»; front end = «Меню кампании».
- Preserve `campmap.riv` and `campmap.comp_key` verbatim as internal keys.
- Layer names supplied via placeholders are not declined.
- `campmap.no_line_in_the_names_file` is a fragment; ends with colon rather
  than an English article. Check its rendered continuation during UI review.
- Terrain explanation now explicitly says «местность» as well as «грунт».

No termbase edits, shared-document edits, promotion or visual validation.


## Batch: ru-factions-review

# Russian faction batch review

261 strings across factions (172), facaudit (25), factionsites (29), family
(35). All merged through i18n_todo.py; no live catalogue, no promotion.

Exemptions:

- `factions.bring_art`, `factions.bring_frame_units`: `frame` means the base
  faction that supplies the recipient mod's working format, not an animation
  frame. Rendered as «основа» / «фракция-основа».
- `family.on_map`: `character` is the literal descr_strat line keyword,
  preserved as «строка character», not translated into персонаж.
- `facaudit.world_maps_campaign`: the entire string is a literal file path,
  `world/maps/campaign/{camp}/{rel}`, so campaign stays unchanged.

Terminology for native review:

- Faction audit gap: «пробел» (missing faction data); notes: «примечания».
- Faction frame: «основа» / «фракция-основа».
- Head modifier: «Модификатор главы»; triumph value: «Значение триумфа».
- Original banner pattern directions / and backslash are preserved.
- Movie percentages and all side-effect/backup/undo statements retained.

The `factions.banner_where` source says "Written to" in the preview; the
translation says «Будет записано в», confirmed in `factions.js:492`: it is
shown under the plan preview, immediately before the Write banners button.


## Batch: ru-models-review

# Russian models review and checkpoint

2026-10-23: bmdb 121/121 strings merged through i18n_todo.py. No missing,
stale or extra IDs in bmdb. No exemptions used and no termbase edits.

Clone wording uses «создается клонированием» so it preserves the meaning
and satisfies the existing «клониров» stem. The natural «клонируется» was
rejected by that stem and reworded, not bypassed.

Model skins are «текстуры». Attachment sheet stays «лист креплений», as in
the completed Armory Studio namespace. Literal BMDB paths, onclick and
placeholder strings remain unchanged; user-visible title text is translated.

Remaining assigned namespaces: viewer3d (143), v3anim (170), not started.
Draft only; no promotion, commits or visual validation.

Prior armory notes remain in `.cache/ru-armory-review.md`; all 519 armory
strings were completed and validated in the prior work period.


## Batch: ru-traits-review

# Russian traits batch review

190 strings: ancillaries (57), traits (65), triggerui (30), guilds (38).

## Exemption

- `ancillaries.not_found_in_data_ui_ancillaries`: `ancillary` is matched
  inside the literal folder path `data/ui/ancillaries`. The path remains
  unchanged; the message concerns a missing image, not a missing follower.

## Terminology and context

- Ancillary follows the termbase: «приближенный», even though the game also
  uses this record type for items and titles. This remains a draft for a
  native-speaking modder to review.
- Guild tier is «ступень»; trait level is «уровень».
- Trait epithet is «прозвище» (the appended epithet shown with a name).
- `ancillaries.s_ancillaries` and `traits.s_traits` follow a mod name after
  the shared reading label. They start with a colon to avoid inflecting the
  unknown mod name.
- `triggerui.and` and `triggerui.or` are labels, translated «и» and «или».
  The earlier project fix keeps their underlying script values separate.
- `triggerui.from_the_mods_lua_scripts_what` isolates `{noun}` in quotes
  because the supplied noun may still be English.
- File-format field names remain literal: `Unique` and `Transferable`
  human-facing labels are translated, while explicit keys such as
  `ExcludeCultures`, `ExcludedAncillaries`, `AntiTraits`, `LevelName`,
  `TraitName`, `NoGoingBackLevel` and `WhenToTest` remain unchanged.

## Validation

All 190 strings merged through the termbase/placeholder/HTML/plural checker.
All assigned namespaces have zero missing, stale or extra IDs.
No promotion, commit, shared guide edit or termbase change.


## Batch: ru-units-review

# Russian editor and edrecruit batch

Completed 356 strings: all 313 editor and all 43 edrecruit. Merged using the
normal checker and lock. No shared docs or termbase edits.

## Exemptions

- `editor.soldier_replace`: `soldier` is the literal EDU keyword naming the
  row being replaced, not prose about a soldier. Kept `soldier (заменить)`;
  exempted the `soldier` term only.

## Choices for review

- skin = «облик»; appearance variant = «вариант»; attachment follows the
  supplied termbase «крепление»; normal map = «карта нормалей».
- Building line = «цепочка зданий», tier = «ступень», recruitment = «набор».
- Rephrased `editor.first_the_record_new_skins_are` as «запись для
  клонирования новых обликов» so the natural Russian passes the existing
  clone stem without weakening it or taking an exemption.
- Generic unknown counts use neutral labels (e.g. «также используют:") to
  avoid assuming the gender or number of the supplied noun. Counted known
  nouns carry all four CLDR forms.
- Literal file filters, paths, internal attributes and EDU keywords retained.

Validation: each merged batch has zero final refusals; assigned namespaces
have zero missing/stale/extra IDs. All strings remain in the work catalogue.


## Engine editor follow-up

- The `orphan` exemptions in eng.ancillaries, eng.codeview, eng.guilds and
  eng.traits refer to renaming breaking references, rendered «нарушит ссылки».
  They do not describe unused records.
- eng.codeview.length_says_but_text_is and its _and_more variant refer to
  text symbols, not people (`character`).
- Four eng.guilds diagnostics beginning has_no_levels_line_so_no,
  levels_counts_upward, levels_has_threshold_s_20_of and
  levels_takes_whole_numbers preserve the literal `levels` keyword (`level`).

## Engine gameplay follow-up

128 strings in eng.areaeffects, eng.characters, eng.heroabilities,
eng.mercpools, eng.rebelpools and eng.settlemech passed the merge checker.

Literal-keyword/path exemptions:
- eng.heroabilities.not_in_ui_battle_sd_so: `battle` belongs to ui/battle.sd.
- eng.mercpools.line_a_second_regions_line_for: `regions` is a file keyword.
- eng.mercpools.line_is_not_pool_regions_or: preserve pool, regions and unit
  as the accepted file keywords (`pool`, `region`, `unit`).
- eng.settlemech.upgrade_is_above_max_which_the and
  eng.settlemech.upgrade_is_not_s_base_both: `upgrade` is a population
  threshold field, not an equipment improvement.

Rebel warnings retain chance 0 meaning no rebels, the two installed-mod
examples, and the missing-block consequence. Effect diagnostics retain
packed-file uncertainty and the requirement to repair malformed XML first.

## Batch: ru-guided-review

# Russian guided checkpoint

First 130 strings translated. Work stopped at the account pause threshold;
307 of 437 remain. Resume using:

```text
python main/dev/checks/i18n_todo.py ru --batch guided --max 100 --out .cache/ru-guided-2.json
```

Batch files: `.cache/ru-guided-1.json`, `ru-guided-1-answer.json`, and
`ru-guided-1-fix.json`. No shared docs or termbase edits; no promotion.

## Exemptions and source evidence

- `guided.banner_faction`, `guided.banner_holy`, `guided.banner_unit`:
  literal EDU keys, used as lookup keys in guided.js around lines 498, 533,
  799. Preserve English; exemptions `banner`, plus `faction` or `unit`
  where present.
- `guided.era_0`, `guided.era_1`, `guided.era_2`: literal lookup keys in
  guided.js around lines 513 and 699. Preserve English; exempt `era`.
- `guided.close`, `guided.close_2`: close means tight formation spacing,
  not closing a dialog. Translate «Плотный строй»; exempt `close`.
- `guided.armour_upgrade_models_outnumber_levels`: trigger means activate,
  not a script trigger. Translate «условие активации»; exempt `trigger`.
- `guided.find_an_entry_by_skeleton_by`: `soldier` is the literal EDU line
  keyword. Preserve it; exempt `soldier`.
- `guided.a_projectile_is_set_but_the_weapon_type_is_type`: missile is one
  of the three literal weapon type values; retain `missile`, `thrown`,
  `siege_missile` and exempt `missile`.

`guided.0_0_no_0_0_no` is used as GF_NO_WEAPON at guided.js:971 and is
preserved verbatim. Field-order syntax descriptions are reader-facing
hints, so translated labels in those are appropriate.

Native-speaker review is still needed for terminology; no visual QA done.

## Batch: ru-models-review

# Russian models review and checkpoint

2026-10-23: bmdb 121/121 strings merged through i18n_todo.py. No missing,
stale or extra IDs in bmdb. No exemptions used and no termbase edits.

Clone wording uses «создается клонированием» so it preserves the meaning
and satisfies the existing «клониров» stem. The natural «клонируется» was
rejected by that stem and reworded, not bypassed.

Model skins are «текстуры». Attachment sheet stays «лист креплений», as in
the completed Armory Studio namespace. Literal BMDB paths, onclick and
placeholder strings remain unchanged; user-visible title text is translated.

Remaining assigned namespaces: viewer3d (143), v3anim (170), not started.
Draft only; no promotion, commits or visual validation.

Prior armory notes remain in `.cache/ru-armory-review.md`; all 519 armory
strings were completed and validated in the prior work period.

## Batch: ru-campaign-next-review

# Russian campaign next checkpoint

Assigned namespaces: campaint, campmark, campcreate, campnew, campimport (284 strings total).

Completed: campaint, 131 strings merged through i18n_todo.py, zero refused. Source batch .cache/ru-campaint-batch.json; answer .cache/ru-campaint-answer.json.

Reviewed term exemptions:
- campaint.add_a_province_decide_its_record: port_verb; source refers to a harbor noun.
- campaint.place_the_port_pixel_or_skip: port_verb; source refers to a harbor noun.
- campaint.writes_layers_at_once_in_the: port_verb; source refers to a harbor noun.
- campaint.written_into_a_settlement_the_music: ship; source means includes, not a vessel.

Preserved literal data examples catholic 100 and gold, wine. campaint.nothing_picked_a is a sentence fragment rendered as nothing selected followed by a colon in Russian. campaint.newtown was translated as a display name (Новый город); check its UI context during final review if it might instead be a required internal token.

Remaining untranslated: campcreate36, campnew28, campmark52, campimport37, 153 total. Exported together in .cache/ru-campaign-next-batch.json. No answer file or partial translations created for these remaining IDs; no refused IDs pending from campaint. Resume by exporting current missing IDs from those four namespaces, translating in bounded batches, and merging with checker. Read main/dev/i18n/ru.md first. Do not merge source English as translations.

Paused at parent's checkpoint request and standing 50% five-hour threshold. Last live account check: 79% used, 21% remaining, reset timestamp1792742769. No promotion, commits, shared documentation edits, or termbase edits made by this task.

## Engine utility, audio and map-check continuation

52 messages completed in eng.dupes, eng.edusort, eng.modreport and
eng.projectzip. Exemptions: eng.dupes.a_renamed_block_is_a_real preserves
literal `soldier`; eng.edusort.unit_s_have_no_tier_yet uses banners in the
sense of divider headings within the file, not battlefield flags.

63 messages completed in eng.soundbanks, eng.sounds, eng.triggers and
eng.voices with no exemptions. Voice name calls retain «представление»
for native review. Warnings retain missing-reference consequences and
original audio format values.

57 messages completed in eng.mapcheck. Exemptions `port_verb` apply to
second_port_pixel, second_port_pixel_for_owner,
starts_with_a_and_map_regions, the_port_pixel_at_has_no and
the_port_pixel_at_touches_no: all refer to harbors. The `level` exemption
in the_river_crossing_at_is_at refers to leveling ground, not ranks or
building levels. River diagnostics retain topology, elevation and battle
consequences. Placement fragments need visual review with their runtime
continuations, particularly label_is_placed_tail and s_pixel_at.

## Latest continuation: ru-guided-review

# Russian guided checkpoint

First 130 strings translated. Work stopped at the account pause threshold;
307 of 437 remain. Resume using:

```text
python main/dev/checks/i18n_todo.py ru --batch guided --max 100 --out .cache/ru-guided-2.json
```

Batch files: `.cache/ru-guided-1.json`, `ru-guided-1-answer.json`, and
`ru-guided-1-fix.json`. No shared docs or termbase edits; no promotion.

## Exemptions and source evidence

- `guided.banner_faction`, `guided.banner_holy`, `guided.banner_unit`:
  literal EDU keys, used as lookup keys in guided.js around lines 498, 533,
  799. Preserve English; exemptions `banner`, plus `faction` or `unit`
  where present.
- `guided.era_0`, `guided.era_1`, `guided.era_2`: literal lookup keys in
  guided.js around lines 513 and 699. Preserve English; exempt `era`.
- `guided.close`, `guided.close_2`: close means tight formation spacing,
  not closing a dialog. Translate «Плотный строй»; exempt `close`.
- `guided.armour_upgrade_models_outnumber_levels`: trigger means activate,
  not a script trigger. Translate «условие активации»; exempt `trigger`.
- `guided.find_an_entry_by_skeleton_by`: `soldier` is the literal EDU line
  keyword. Preserve it; exempt `soldier`.
- `guided.a_projectile_is_set_but_the_weapon_type_is_type`: missile is one
  of the three literal weapon type values; retain `missile`, `thrown`,
  `siege_missile` and exempt `missile`.

`guided.0_0_no_0_0_no` is used as GF_NO_WEAPON at guided.js:971 and is
preserved verbatim. Field-order syntax descriptions are reader-facing
hints, so translated labels in those are appropriate.

Native-speaker review is still needed for terminology; no visual QA done.

## Resumed batch 2 checkpoint (2026-10-23)

Merged 100 more strings from ru-guided-2-answer.json and ru-guided-2-fix.json.
Guided now has 230 translated, 207 missing, 0 stale. Subset catalogue checker
reports 0 problems. No unmerged translations or outstanding refusals.
Changed shared files: main/dev/i18n/ru.json and ru.source.json via locked merge.
Stopped per parent checkpoint instruction; last five-hour usage was 49% used.
Resume with a fresh bounded guided export (e.g. --max 100 --out .cache/ru-guided-3.json).

Batch 2 exemptions, all preserve meaning rather than bypassing terminology:
- guided.florins_the_smith_charges_to_upgrade and _2: charge means payment,
  not battle charge; exempt charge.
- guided.heavy_light_general: literal voice_type choices (guided.js:206);
  exempt general.
- guided.infantry_cavalry_siege_ship_handler: literal category choices
  (guided.js:193); exempt infantry, cavalry, siege, ship.
- guided.light_heavy_missile_spearmen: literal class choices (guided.js:199);
  exempt missile.
- guided.how_many_comes_from_the_extras and
  guided.how_many_the_unit_fields_comes_from: literal soldier line keyword;
  exempt soldier.
- guided.how_the_weapon_is_used_melee_thrown: melee occurs only as a literal
  code value; exempt melee.
- guided.men_in_the_unit_at_the_largest: shipped means supplied, not vessel;
  exempt ship.
- guided.mercenary_unit_the_unit_card_is: mercenary appears in a literal
  attribute keyword; exempt mercenary.
- guided.missile_infantry_cavalry_and_siege: literal class value missile;
  exempt missile.
- guided.most_mods_leave_it_out_and_use: mount is part of literal mount_effect;
  exempt mount.

Terminology: guided mode «По полям»; raw lines «Исходные строки»;
free picks «Выборов без наценки»; loose formation «Свободный строй».
guided.line_s_in_this_unit is an English string, not plural object; translated
as count-neutral «Строк в этом отряде: {n}.» and verified by merge.

## Latest continuation: ru-models-review

# Russian models review and checkpoint

2026-10-23: bmdb 121/121 strings merged through i18n_todo.py. No missing,
stale or extra IDs in bmdb. No exemptions used and no termbase edits.

Clone wording uses «создается клонированием» so it preserves the meaning
and satisfies the existing «клониров» stem. The natural «клонируется» was
rejected by that stem and reworded, not bypassed.

Model skins are «текстуры». Attachment sheet stays «лист креплений», as in
the completed Armory Studio namespace. Literal BMDB paths, onclick and
placeholder strings remain unchanged; user-visible title text is translated.

Resumed: viewer3d 143/143 and the first 100/170 v3anim strings now merged.
Remaining assigned work: v3anim 70 strings, starting after
`v3anim.put_s_animation_in_this_slot`. Export with i18n_todo.py to get the
authoritative next batch. Stopped at 55% five-hour remaining per parent
instruction to stop starting batches below 60%.
Draft only; no promotion, commits or visual validation.

Prior armory notes remain in `.cache/ru-armory-review.md`; all 519 armory
strings were completed and validated in the prior work period.

## Viewer and animation review

Viewer3d exemptions:

- `viewer3d.art_starts_over_second`, `viewer3d.art_starts_over_unit`,
  `viewer3d.in_game_units`: `unit` means a measurement unit, not a regiment.
- `viewer3d.drag_to_turn_wheel_to_zoom`: `turn` is view rotation.
- `viewer3d.draw_the_texture_at_the_size`, `viewer3d.drawn_at_shipped`:
  `ship` means distributed with a mod, not a vessel.

V3anim exemptions:

- `v3anim.building_the_glb`, `v3anim.building_the_obj_zip`: `building`
  means generating an export file, not a settlement building.
- `v3anim.not_in_the_skeleton_pack_only_loose`,
  `v3anim.played_from_vanillas_pack_this_mod`: `ship` means distributed.

UV measurement u and numerical wrapping at 1 or 2 stay literal. Viewer
skins remain «текстуры» and UV layout is «UV-развертка». Skinned model is
«модель с привязкой к скелету» in the animation message, not merely a
model with a texture. Drawn/stowed weapons are «в руках» / «убрано»;
carried/slung shields are «в руке» / «за спиной». Native review should
check these distinctions in the displayed models.

All merges passed with no refused strings. No termbase or shared-doc edits.

## Latest continuation: ru-campaign-next-review

# Russian campaign next checkpoint

Assigned namespaces: campaint, campmark, campcreate, campnew, campimport (284 strings total).

Completed: campaint, 131 strings merged through i18n_todo.py, zero refused. Source batch .cache/ru-campaint-batch.json; answer .cache/ru-campaint-answer.json.

Reviewed term exemptions:
- campaint.add_a_province_decide_its_record: port_verb; source refers to a harbor noun.
- campaint.place_the_port_pixel_or_skip: port_verb; source refers to a harbor noun.
- campaint.writes_layers_at_once_in_the: port_verb; source refers to a harbor noun.
- campaint.written_into_a_settlement_the_music: ship; source means includes, not a vessel.

Preserved literal data examples catholic 100 and gold, wine. campaint.nothing_picked_a is a sentence fragment rendered as nothing selected followed by a colon in Russian. campaint.newtown was translated as a display name (Новый город); check its UI context during final review if it might instead be a required internal token.

Remaining untranslated: campcreate36, campnew28, campmark52, campimport37, 153 total. Exported together in .cache/ru-campaign-next-batch.json. No answer file or partial translations created for these remaining IDs; no refused IDs pending from campaint. Resume by exporting current missing IDs from those four namespaces, translating in bounded batches, and merging with checker. Read main/dev/i18n/ru.md first. Do not merge source English as translations.

Paused at parent's checkpoint request and standing 50% five-hour threshold. Last live account check: 79% used, 21% remaining, reset timestamp1792742769. No promotion, commits, shared documentation edits, or termbase edits made by this task.


## Resumed completion
All remaining153 merged: campcreate36, campnew28, campmark52, campimport37. Checked merges accepted65 (including one correction) and89, zero refused. Answers: .cache/ru-campaign-resume1-answer.json and .cache/ru-campaign-resume2-answer.json. All284 assigned strings now complete. No further work started; last five-hour usage39% used /61% remaining.

campaint.newtown corrected to literal Newtown. main/web/js/campaint.js:846 uses it as the placeholder for internal settlement key with no-spaces guidance; line849 reuses it for settlement display name. Keeping the shared example literal is necessary.

Additional reviewed exemptions:
- campcreate.new_region_name_paint_settlement_port, campcreate.port, campcreate.port_marker_add_or_move_on, campcreate.select_a_region_first_then_choose: port_verb; harbor nouns.
- campnew.map_layers_note, campnew.this_mod_ships_only_the_compiled: ship; means includes.
- campmark.named_character_general_admiral_port_spy, campmark.port, campmark.ports, campmark.show_settlements_ports_and_campaign_objects: port_verb; harbor nouns.
- campmark.this_mod_ships_its_own_picture: ship; means includes.

No term stem blockers. All new plurals include one/few/many/other. Unit Transfer in campimport.type_one_of_s_units_to is the module and translated by function as Перенос отрядов.

## 2026-10-24 engine continuation

Completed eng.mapfe/mapquery/maptga (30), eng.settlemodel/walls (55),
eng.animedit/animloose/animview/casanim (50), eng.edbimport (23), and
eng.mapresize (15). All checked merges accepted without refusals.

Exemptions: eng.mapfe.the_frame_at_x_g_y, the_frame_is_w_g_x and
its _2 variant use frame as a crop rectangle, rendered «рамка».
eng.animloose.turns_bones_and_its_skeleton_has and
eng.casanim.turns_bones_and_the_skeleton_has use turn as bone rotation.
Other batches used no exemptions.

Warnings retain texture collision isolation, missing-texture consequences,
read-back verification, malformed structure safeguards, unavailable culture
and religion requirements, resize save incompatibility, and M2EX limits.
Native review: animation cues rendered «сигналы»; crop frame «рамка».

## 2026-10-24 batch: ru-packs-review

# Russian packs review

All146 packs strings merged with zero refusals. Fresh missing export returned0. Source .cache/ru-packs-batch.json; answer .cache/ru-packs-answer.json. All plurals provide one/few/many/other; longer notices use neutral counted labels to avoid conflicting agreement with independent counts.

Reviewed exemptions:
- packs.battle_model_entr_travel_with_them: mount means attaching an archive as a source, not a riding animal; translated подключается.
- packs.soldier_of_lods_files, packs.soldier_only_entries_with_an_identical, packs.unit_soldier_line_s_are_repointed: soldier is the literal EDU field name, preserved.

Terminology: battle-model uses модель битвы to honor battle/model stems; footer is заключительная часть; identical twin is идентичный аналог; skin is облик. Native review should confirm these technical phrasings. Filenames, paths, code blocks, HTML attributes and placeholders retained. No stem blockers or remaining refusals. No shared docs/termbase edits or promotion.

## 2026-10-24 batch: ru-models-next-review

# Russian models resume review

- Completed remaining v3anim batch: 70 strings merged, 0 refused. Namespace now complete (170 total, first100 in prior review).
- Batch: .cache/ru-v3anim-batch2.json; answers: .cache/ru-v3anim-answer2.json.
- Preserved placeholders, markup, paths, rider_offset, descr_mount.txt, descr_skeleton.txt, .glb, and literal animation search examples walk/charge/die.
- Russian one/few/many/other forms supplied for ridden_by_units and with_all_loose_actions_of.
- Exemptions: v3anim.turn_every_key and v3anim.turns_to: turn means physical rotation, not campaign turn. v3anim.vanillas_skeleton_pack_this_mod_ships: ships means includes/distributes, not a vessel. v3anim.walk_charge_die_a_file_name: charge is a literal animation name in search examples.
- Terminology: action = действие; pack = пакет; loose = отдельный файл; bone = кость; skeleton = скелет; mount = верховое животное; animation = анимация; log = журнал.
- Checkpoint requested by parent at30% remaining. Sprites151 not started. Resume by exporting bounded sprites batch, read terms/source, translate and merge through checker.

## 2026-10-24 batch: ru-guided-review

# Russian guided checkpoint

First 130 strings translated. Work stopped at the account pause threshold;
307 of 437 remain. Resume using:

```text
python main/dev/checks/i18n_todo.py ru --batch guided --max 100 --out .cache/ru-guided-2.json
```

Batch files: `.cache/ru-guided-1.json`, `ru-guided-1-answer.json`, and
`ru-guided-1-fix.json`. No shared docs or termbase edits; no promotion.

## Exemptions and source evidence

- `guided.banner_faction`, `guided.banner_holy`, `guided.banner_unit`:
  literal EDU keys, used as lookup keys in guided.js around lines 498, 533,
  799. Preserve English; exemptions `banner`, plus `faction` or `unit`
  where present.
- `guided.era_0`, `guided.era_1`, `guided.era_2`: literal lookup keys in
  guided.js around lines 513 and 699. Preserve English; exempt `era`.
- `guided.close`, `guided.close_2`: close means tight formation spacing,
  not closing a dialog. Translate «Плотный строй»; exempt `close`.
- `guided.armour_upgrade_models_outnumber_levels`: trigger means activate,
  not a script trigger. Translate «условие активации»; exempt `trigger`.
- `guided.find_an_entry_by_skeleton_by`: `soldier` is the literal EDU line
  keyword. Preserve it; exempt `soldier`.
- `guided.a_projectile_is_set_but_the_weapon_type_is_type`: missile is one
  of the three literal weapon type values; retain `missile`, `thrown`,
  `siege_missile` and exempt `missile`.

`guided.0_0_no_0_0_no` is used as GF_NO_WEAPON at guided.js:971 and is
preserved verbatim. Field-order syntax descriptions are reader-facing
hints, so translated labels in those are appropriate.

Native-speaker review is still needed for terminology; no visual QA done.

## Resumed batch 2 checkpoint (2026-10-23)

Merged 100 more strings from ru-guided-2-answer.json and ru-guided-2-fix.json.
Guided now has 230 translated, 207 missing, 0 stale. Subset catalogue checker
reports 0 problems. No unmerged translations or outstanding refusals.
Changed shared files: main/dev/i18n/ru.json and ru.source.json via locked merge.
Stopped per parent checkpoint instruction; last five-hour usage was 49% used.
Resume with a fresh bounded guided export (e.g. --max 100 --out .cache/ru-guided-3.json).

Batch 2 exemptions, all preserve meaning rather than bypassing terminology:
- guided.florins_the_smith_charges_to_upgrade and _2: charge means payment,
  not battle charge; exempt charge.
- guided.heavy_light_general: literal voice_type choices (guided.js:206);
  exempt general.
- guided.infantry_cavalry_siege_ship_handler: literal category choices
  (guided.js:193); exempt infantry, cavalry, siege, ship.
- guided.light_heavy_missile_spearmen: literal class choices (guided.js:199);
  exempt missile.
- guided.how_many_comes_from_the_extras and
  guided.how_many_the_unit_fields_comes_from: literal soldier line keyword;
  exempt soldier.
- guided.how_the_weapon_is_used_melee_thrown: melee occurs only as a literal
  code value; exempt melee.
- guided.men_in_the_unit_at_the_largest: shipped means supplied, not vessel;
  exempt ship.
- guided.mercenary_unit_the_unit_card_is: mercenary appears in a literal
  attribute keyword; exempt mercenary.
- guided.missile_infantry_cavalry_and_siege: literal class value missile;
  exempt missile.
- guided.most_mods_leave_it_out_and_use: mount is part of literal mount_effect;
  exempt mount.

Terminology: guided mode «По полям»; raw lines «Исходные строки»;
free picks «Выборов без наценки»; loose formation «Свободный строй».
guided.line_s_in_this_unit is an English string, not plural object; translated
as count-neutral «Строк в этом отряде: {n}.» and verified by merge.

## Completion checkpoint (2026-10-24)

Completed remaining 207 strings in batches 3 (100) and 4 (107); both merged
without refusals. Also refined mounted_engine to «Орудие на верховом животном»
after inspecting guided.js:278 and removed its provisional mount exemption.
All 437 guided strings are now translated, 0 missing/stale/extra. Full guided
subset terminology/structure checker passes with 0 problems. No pending files
or refusals. Answer files are .cache/ru-guided-3-answer.json and
.cache/ru-guided-4-answer.json. Shared modifications are ru.json/ru.source.json
through checked locked merges only. No promotion or visual QA performed.
Latest usage: 85% five-hour used (15% remaining). Assignment boundary reached.

Additional exact exemptions:
- guided.optional_the_effect_played_when_the_weapon: turn means transform the
  number of fields, not a campaign turn; exempt turn.
- guided.the_line_goes_directly_after_soldier,
  guided.these_entries_do_not_decide_how_the,
  guided.up_to_three_officer_lines_directly: soldier is the literal EDU row
  keyword; exempt soldier.
- guided.the_list_is_the_lt_holybanners_gt: crusade and cavalry occur only
  in literal banner identifiers crusade/crusade_cavalry; exempt crusade,cavalry.
- guided.vanilla_ships_it_commented_out and
  guided.vanilla_ships_it_commented_out_on: ships means supplies, not vessels;
  exempt ship.
- guided.wagons_like_the_great_cross_count: siege is a literal category name;
  exempt siege.
- guided.with_two_formations_the_first_must: horde is a literal formation
  keyword, not a nomadic faction; exempt horde.

Terminology: sidearm/secondary weapon «дополнительное оружие»; ranks «шеренги»;
upkeep «содержание»; shield missile «щит против стрелкового оружия».
Accent identifiers (English, Scottish, etc.) preserved, as are all code tags.
Count-bearing English strings use neutral Russian constructions, preserving
their string shape rather than introducing unsupported plural objects.

## Map creation and campaign engine continuation

Completed eng.mapbundle/mapnew19 and eng.campdb/campfiles/campnew52.
Ship exemptions refer to includes/distributes in this_mod_ships_only_so_the,
is_not_on_disk_and_ships, nothing_names_on_the_new_game_menu_archive
and ships_map_layer_s_of_its. The region exemption in
eng.campfiles.now_has_no_music_type_and preserves a literal engine error.
Missing music defaults, campaign copying limitations and XML safeguards
remain explicit. No termbase edits.

## Latest batch: ru-art-next-review

# Russian sprites/cards checkpoint

- sprites151/151 merged, zero refusals. Source .cache/ru-sprites-batch.json, answers .cache/ru-sprites-answer.json.
- cards75/132 merged, zero refusals;57 remain. Source .cache/ru-cards-batch.json, answers .cache/ru-cards-answer1.json. Re-export missing cards on resume; original batch contains now-merged keys too.
- Latest five-hour usage53% used,47% remaining. Stopped at completed-batch boundary after parent restored50% guard. Parent checkpoint message arrived while cards subset was executing. No further translation started.
- Terms: sprite спрайт; sheet лист; mipmaps mip-уровни; voice bank банк голосов; accent акцент; card карточка; rig риг; billboard плоское изображение.
- Source inspected sprites.js for armour_ug (display label, translated) and fragments. Preserved bypass, sprite_script, CFG, all file paths, EOP/M2TWEOP and markup/placeholders. Cards Pole and Switch are literal rig controls/bone names and retained.
- Exemptions sprites.this_mod_ships_m2tweop_so_generation: ship is distribute/include, not a vessel. sprites.turn_the_flag_back_off and sprites.the_bypass_flag_makes_the_next_normal: turn off is disable, not campaign turn.
- Exemptions cards.gen_place_reset: frame means framing rectangle, not animation frame. cards.gen_rig_hint, cards.gen_turn, cards.gen_view_hint: turn means physical rotation, not campaign turn.
- No shared docs/termbase edits, commits or promotion.

## Latest batch: ru-minor-review

# Russian minor files checkpoint

2026-10-24: minorfiles namespace127 translated via ru-minor-1-answer.json
and ru-minor-1-fix.json. Initial two refusals were harbor sense of port;
corrected exact exemptions to include current port_verb term ID. No pending
refusals or unmerged answers. Full namespace checker passes,0 problems.

Changed shared files: main/dev/i18n/ru.json and ru.source.json through locked
checked merges. No promotion, shared docs, termbase edits, or visual QA.

Remaining assigned work: eng.minorfiles86, not started. Resume with bounded
export using i18n_todo.py ru --batch eng.minorfiles --max86 (space before86).
User restored50% five-hour guard; stopped starting work near60% remaining
to reserve shared-account checkpoint capacity. Last measured63% remaining.

Exact exemptions:
- minorfiles.port_ladder_line_s_in_the and
  minorfiles.this_culture_has_no_port_lines: port refers to harbor buildings,
  not porting content; exempt port and port_verb.
- minorfiles.the_culture_the_record_does_not: ports means harbors; exempt port.
- minorfiles.where_it_starts_every_regions_religions: ships means distributes
  files, not vessels; exempt ship.

Terminology: pip «маркер»; card «карточка»; info card «информационная карточка»;
settlement ladder «цепочка поселений»; infrastructure «инфраструктура».
Unknown noun placeholders use parenthetical labels or colon constructions
to avoid requiring grammatical gender/case. All plural objects have Russian
one/few/many/other. Count-bearing simple strings use neutral count wording.
Native-speaker review remains necessary before marking reviewed.

## Latest batch: ru-map-next-review

# Russian map next review

Completed osmmap120 and stratcamp109 (229 total). Checked merges:120 accepted,108 accepted plus1 corrected. Fresh missing export0. No pending refusals. Answers .cache/ru-osmmap-answer.json and .cache/ru-stratcamp-answer.json.

Reviewed exemptions:
- osmmap.mylaes_layout_the_maps_layers_as: port_verb; harbor noun.
- osmmap.open_settings_to_turn_it_on: turn; enable, not a campaign turn.
- osmmap.the_style_above_cut_to_the: frame; spatial bounds, not animation frame.
- stratcamp.faction_bik: faction; literal path faction/{x}.bik.

Kept stratcamp.burgundy as internal faction code; osmmap.reference as filename reference.{x}; preserved literal backslash-n in stratcamp.press_enter_for_a_line_break code tag. All plural forms provided. years_per_turn uses Число годов за ход to satisfy год stem without an exemption. Native review may prefer Число лет за ход if accepted stem support later expands to irregular Russian plurals. OSM chunk=фрагмент, geographic box=рамка, backdrop=подложка; standings=оценки отношений.

No termbase/shared documentation edits or promotion. Stopped after assignments; last live check47% used /53% remaining, restored guard honored; no further batches.

## Engine climate, family, objects and campaign-start continuation

Completed eng.climatenew24, eng.stratfamily19, eng.winconds18,
eng.stratmap10, eng.stratobj35, eng.campstrat26, eng.hordestart23,
eng.campimport32 and eng.mapgen19. All checked merges accepted.

Exemptions: ship in eng.climatenew.a_climate_name_the_battle_map,
all_four_mods_measured_for_this and eng.winconds.could_not_be_read_the_stock
means includes. Port in the two eng.stratobj.is_pixel_none_of_the_800
messages means harbor. Settlement in there_is_no_folder_under_any is a
literal path component. eng.campstrat exemptions preserve syntax examples:
faction in faction_relationships_does_not_read_as and
faction_standings_does_not_read_as; culture in fort_line_does_not_read_as;
castle in settlement_header_says_the_engine_knows; armour in
should_be_armour and unit_line_does_not_read_as.

Kept climate crash warnings, unknown-name uncertainty, map incompatibility,
XML/file syntax, horde minimum/pool behavior and import omissions explicit.
Plural counts without known inflection use neutral count labels.

## Latest completed batch: ru-art-map-review

# Russian cards/mapquery/stratmap review

Completed remaining cards57 (namespace132), mapquery76 and stratmap76. All final merges zero refusals. Answers: .cache/ru-cards-answer2.json, .cache/ru-mapquery-answer.json, .cache/ru-stratmap-answer.json. Original bounded batches retained. All plural entries have one/few/many/other; generic placeholders use count labels when inflection cannot be known. Code, paths, placeholders, HTML retained.

New exemptions:
- cards.already_live_only_in_merc, cards.and_more_written_into_the_merc, cards.confirm_move_folded, cards.copying_file_s_out_writing_into, cards.merc, cards.one_is_the_merc_copy: mercenary term is literal merc directory name, preserved.
- cards.data_ui_units_data_ui_unit: unit occurs in literal data/ui/units and data/ui/unit_info paths.
- mapquery.building_that_map: building means constructing the map, not a building object.
- stratmap.draw_a_campaign_map_model_beside: ships means includes/distributes a CAS file, not a ship.
- stratmap.file_named_by_no_model_but: turns up means occurs/is mentioned, not a campaign turn.

Fixed initial cards.units_pin_to_folder refusal by retaining explicit mod wording. No termbase changes. Terms: tile тайл, province провинция, layer слой, tint тонирование, solid сплошная заливка, strat map стратегическая карта, strat model стратегическая модель. Cards dictionary values described as names in the dictionary; merc literal retained. Prior review remains .cache/ru-art-next-review.md.

No promotion, commits or shared docs edits. Assignment complete; no next namespace started.

## Latest completed batch: ru-records-next-review

# Russian record sections completion

Completed eng.minorfiles86, stratchar81, mercs78:245 new strings.
Checked merges reported0 refusals. Combined namespace checker reports
245 translated,0 problems; each namespace has0 missing/stale/extra.
Answer files: ru-records-1-answer.json, ru-records-2-answer.json,
ru-records-3-answer.json, ru-records-3-fix.json (all in .cache).
Last five-hour usage63% used,37% remaining. Stopped at assignment boundary.

Shared changes only main/dev/i18n/ru.json and ru.source.json, via locked
merge. No shared documents/termbase/promotion changes. No visual QA;
native-speaker review required before marking reviewed.

Exact exemptions in eng.minorfiles:
- line_before_the_first_culture_line: culture is literal row keyword.
- line_religion_has_no_closing_brace and line_religions_has_no_closing_brace:
  religion/religions are literal row keywords; exempt religion.
- this_cultures_port_ladder_has_lines: harbor, not porting content;
  exempt port and port_verb.
- this_is_renaming_it_here_would: orphan means break incoming references,
  not merely unused; translated «нарушит ссылки», exempt orphan.
- this_text_has_no_faction_line: faction appears in literal syntax;
  exempt faction.
No exemptions in stratchar or mercs.

Terminology: pip remains «маркер»; pool «пул»; regiment «полк»;
mercenary sales expressed naturally as availability for hire.
All plural objects have one/few/many/other; fractional pool counts use
neutral labels to avoid incorrect prepositional inflection.
Literal relative, character_record(s), code tags and syntax preserved.
Unknown noun placeholders use labels/parentheses to avoid grammatical gender.

## Latest completed batch: ru-small-next-review

# Russian small namespaces review

Completed230: mapgen59, mapsize57, climates56, soundbanks58. Checked merges accepted116 and114, zero refused. Fresh missing export0. Answers .cache/ru-small-next1-answer.json and .cache/ru-small-next2-answer.json.

Reviewed exemptions:
- mapsize.turn_the_real_world_switch_on: turn means enable, not a game turn.
- climates.append_a_name_the_engine_does, climates.taking_over_one_of_the_twelve, soundbanks.has_no_data_the_game_uses: ship means includes, not a vessel.
- soundbanks.event_line_sample_count: event is a literal sound-script keyword before its identifier; retained exactly.

Terrain corners translated вершины, climate take-over замена, sound sample сэмпл, sound bank звуковой банк, raw text Исходный текст. Proper names, WMS, ESA WorldCover, OpenStreetMap, Mylae, code paths, literal keywords and HTML preserved. All plural entries contain four required forms; multi-count climate notices use counted labels to avoid agreement ambiguity.

Second merge briefly failed with Windows OSError22 while writing ru.source.json. Immediate retry via the same checker succeeded114, restoring source hashes. No direct catalogue/hash edits. No termbase or shared document edits. Stopped after assigned namespaces; latest usage39% used /61% remaining.

## Latest completed batch: ru-edusort-review

# Russian edusort review

All53 strings merged, zero refused. Answer .cache/ru-edusort-answer.json. No shared docs/termbase edits or promotion. Latest usage65% used /35% remaining. Stopped after assigned namespace.

Exemptions:
- banner means textual section heading, not battlefield flag: edusort.a_banner_like_gondor_tier_2, edusort.a_comment_in_this_file_starts, edusort.a_tier_read_from_a_banner_is, edusort.a_unit_with_no_tier_sorts_after, edusort.read_tiers_from_the_files_own, edusort.section_banners, edusort.the_shape_is_fixed_so_the_next, edusort.write_a_banner_above_each_section.
- edusort.a_banner_like_gondor_tier_2: infantry appears only in literal example ;--- GONDOR TIER 2 INFANTRY ---.
- edusort.gondor_tier_2_infantry and edusort.gondor_tier_2_infantry_2: tier and infantry are part of literal case-format examples; retained English to match the file/banner parser example.
- edusort.line_character: character means text symbol, not person.

Terminology: classification классификация, banner заголовок, tier ступень. Ordinary count placeholders use counted labels. No plurals in this namespace; code ;@m2gt tier=2 preserved.

## Latest shared-engine continuation

Completed eng.fileswap/flatrecord/keyblock/leafxml43;
eng.gamepack/mod/modfork/pack/packhouse24;
eng.artrecolour/bannermaker/emblem/images/sprites/spritesheet38;
eng.mapnewreal/mapreal42; eng.changesets/cleaner/crashrules/educeil/health/
launchcheck/rehearse25; eng.namekeys/renames34; eng.gamelog22;
eng.scriptaddons/scriptbuilder/scriptcompat/scriptfiles/scripts36;
eng.cards/portrecords25; eng.mesh/meshfolder/modeldb/modelexport27.
All final checked merges accepted without remaining refusals.

Exact exemptions: eng.fileswap.this_dds_cannot_go_into_a preserves the
.texture extension (texture). eng.mapnewreal.climates_is_one_ground_or_koppen
and rivers_is_none_or_one_of preserve literal setting names (climate/river).
eng.mapnewreal.province_s_grown_from_their_cities uses harbor port_verb.
eng.namekeys.this_mod_ships_only_strings_bin means includes (ship).
eng.gamelog.known_5 means transformation (turn); howto preserves log level
configuration syntax (level). eng.modeldb.characters_left_over_after_the_entry
means text symbols (character); this_does_not_start_like_a preserves literal
serialization::archive (archive).

Russian update stem changed from обновл to обнов so both noun обновление
and button infinitive Обновить validate. Termbase suite27/27 passes.
Other earlier stems general and port_verb remain as previously documented.

## Latest completed batch: ru-strategy-final-review

# Russian strategy sections completion

Completed stratedit52, eng.stratedit38, eng.stratchar42, eng.stratcamp49,
hordestart46, rebels43:270 strings. All six namespaces now have0 missing,
stale or extra; combined checker270 strings,0 problems. One refusal for clone
stem corrected by natural «выполняет клонирование»; no pending refusals.
Answer files .cache/ru-strategy-{1..6}-answer.json plus ru-strategy-4-fix.json.
Shared files changed only main/dev/i18n/ru.json and ru.source.json, checked
locked merges. No promotion, shared docs/termbase edits, or visual QA.
Stopped at assignment boundary. Native-speaker review remains required.

Exact exemptions:
- eng.stratedit.a_settlement_block_opens_with_the: castle literal keyword.
- eng.stratedit.the_header_says_the_engine_reads: settlement,castle literal
  accepted syntax, not descriptive nouns.
- eng.stratedit.stays_on_the_map_with_no and
  eng.stratedit.two_levels_of_stand_in_this: ship means supply, not vessel.
- eng.stratchar.is_not_a_rank_a_character: leader,heir literal rank values.
- eng.stratchar.s_family_line_on_line_names: character literal row keyword.
- eng.stratcamp.is_not_a_word_the_engine: ship means supply, not vessel.
- rebels.of_provinces_name_a_rebel_faction: turn means switch off, not turn.
- rebels.this_faction_lists_no_unit_line: unit is literal row keyword.
No exemptions in stratedit or hordestart.

Term choices: horde start «старт ордой»; plan set «набор планов»;
leader «лидер»; named characters «именные персонажи»; regiment «полк».
Count-bearing simple strings use neutral labels. All plural objects have
Russian one/few/many/other, preserving placeholders and HTML structure.
Historical names Al-Zahir/Philip/Heinrich localized as Аль-Захир/Филипп/Генрих;
game keyword values and file paths remain literal.

## Latest completed batch: ru-model-final-review

# Russian model final namespaces review

Completed eng.animpack32, eng.animslot37, eng.armory21, eng.bmdb23, eng.cas55, modelpicker52 =220 strings. Batches .cache/ru-model-engine-batch.json and .cache/ru-modelpicker-batch.json; answer files .cache/ru-model-engine-answer1.json, .cache/ru-model-engine-answer2.json, .cache/ru-modelpicker-answer.json. Final checked merges all zero refusals.

Exemptions:
- eng.animpack.the_source_ships_no_packs_of and eng.animslot.this_mod_ships_no_animation_packs: ship means distribute/include, not vessel.
- eng.bmdb.still_names_outside_its_soldier_line: soldier is the literal EDU field keyword.
- eng.cas.w_text_latin1 and eng.cas.w_text_long: character means text symbol, not person.
- eng.armory.not_a_model_file: mesh is literal .mesh suffix in an accepted-format list.
- eng.armory.sheet_format: texture is literal .texture suffix in accepted-format list.

Other initial refusals fixed by natural mesh terminology, not exemptions. Code/path literals preserved including .CAS, .mesh, .texture, pack.idx, descr_skeleton.txt, soldier, ownership, gfdl and format specifiers. modelpicker.js source confirmed data attributes are literal markup fragments: only title/aria-label user-visible values translated. user_count occurs on a model entry with e.used_by, rendered as number of units using model. All four Russian plural forms supplied. Terms: bind pose поза привязки, compaction уплотнение, mesh меш, node узел, pivot точка вращения, rig привязка.

No commits, promotion, shared docs or termbase edits. Assigned work complete.

## Latest completed batch: ru-ui-final-review

# Russian UI final review

Completed247: areaeffects40, heroabilities28, characters25, battleflags26, settlemech21, settlemodel20, walls21, dupes34, edbimport32. Checked merges119 and127 plus1 corrected, zero pending refusals. Fresh missing export0. Answers .cache/ru-ui-final1-answer.json and .cache/ru-ui-final2-answer.json.

Exemptions:
- battleflags.banner_faction: banner/faction; literal EDU keyword pair.
- battleflags.banner_holy: banner; literal EDU keyword pair.
- battleflags.banner_unit: banner/unit; literal EDU keyword pair.
- settlemech.level: level; literal internal path level/{name}/{x}.

All placeholders/markup/code paths preserved, plural entries include four required forms and source zero where present. Suffix fragments rendered colon plus label to avoid inflecting unknown preceding mod names. areaeffects user_count counts references, rendered ссылка. Building line=цепочка зданий; gateway=проезд; firing level=уровень стрельбы; skin=облик. Corrected башен to singular башни in walls.no_edb_building_gives_this_wall to match source singular and accepted stem. No shared-doc/termbase edits or promotion. Latest usage31% used /69% remaining. Assignment complete.

## Latest completed batch: ru-ui-extra-review

# Russian extra UI review

Completed114: portui34, projectzip20, renameui33, scripts27. Checked merge114 accepted, zero refused; one follow-up plural phrasing improvement accepted. Fresh missing export0. Answer .cache/ru-ui-extra-answer.json.

No terminology exemptions or stem changes needed. All plural forms present; noun/nouns placeholder differences preserved per source form. Unknown noun placeholders separated with counted labels where possible. Renaming file count uses a label to avoid case disagreements with fractions. Script builder WHEN/IF/DO/ELSE translated as visible labels; M2EX and code paths preserved. Record=запись, log entry=элемент журнала, port=портировать per termbase.

No shared documentation/termbase edits or promotion. Stopped after assigned namespaces. Latest usage59% used /41% remaining under explicit user override.

## Latest completed batch: ru-map-ui-final-review

# Russian map UI final review

Translated map3d15, mapfe18, mapfind17, mapviews30, stratview7 =87. Batch .cache/ru-map-ui-final-batch.json and answers .cache/ru-map-ui-final-answer.json. Initial merge86 accepted; mapviews.update (Обновить) rejected by update stem обновл; requested genuine stem fix from parent. Re-merge answer after parent fixes termbase. No exemption for this.

Exemptions:
- map3d.building_the_mesh: building means generating geometry, not a building.
- map3d.frame_the_whole_map_again: frame means fitting viewport, not animation frame.
- mapfe.before_this_panel_the_picture_was, mapfe.proposed_frame, mapfe.put_the_frame_back_to_the, mapfe.the_frame, mapfe.the_frame_2, mapfe.the_frame_is_which_rectangle_of, mapfe.the_front_end_layer_is_not: frame means image framing rectangle, translated рамка.
- stratview.this_mod_ships_no_data_models: ships means includes/distributes, not vessel.

Terms: view вид; front-end map карта меню; punched-out colours цвета, сделанные прозрачными. Four Russian plural forms supplied. Preserved map_FE.tga, map_heights.tga, data/models_strat, markup and placeholders. No shared docs/termbase/promotion edits. Stop after final checked merge.

Final: parent corrected update stem to обнов. Re-merge accepted all87, zero refusals. Scoped checker zero problems; all five namespaces missing/stale/extra0. Assignment complete; stopped.

## Near-limit continuation

Completed arm export helpers10, map terrain/sites9, server29. No exemptions
except eng.server.the_frame_is_not_four_numbers: crop rectangle, not animation.

## ru-faction-engine-final-review

# Russian faction engine final review

Completed eng.factions16 and eng.factionsites25:41 merged, zero refusals. Source .cache/ru-faction-engine-final-batch.json, answer .cache/ru-faction-engine-final-answer.json. Preserved can_homeless, yes/no, descr_strat, ownership, requires factions { … }, format and path placeholders, backticks and #rrggbb.

Exemption eng.factions.this_faction_is_renaming_a_slot / orphan: the verb means breaking references by renaming, translated нарушит ссылки, rather than unused orphaned asset. All source consequences retained (descr_strat, unit ownership, requires clause and faction text entry).

Terminology: populace население, share доля, slot слот. No shared docs, termbase or promotion edits. Assignment complete; stopped after41.

## ru-engine-buildings-final-review

# Russian engine building diagnostics

eng.buildings:52 strings merged,0 refusals. Namespace checker passed with
0 problems;0 missing/stale/extra. Answer .cache/ru-engine-buildings-final-answer.json.
Shared changes only main/dev/i18n/ru.json and ru.source.json via checked merge.
No promotion/shared docs/termbase edits. No visual QA; native review required.

Exemptions: eng.buildings.every_one_of_the_32_real religion is literal row
keyword; eng.buildings.hidden_ceiling_note ship means supply, not vessel;
eng.buildings.line_building_has_no_opening_brace building is literal keyword.

Building line «линейка зданий», upgrade chain «цепочка улучшений»;
hidden resource plural includes Russian one/few/many/other (fractional
«скрытого ресурса»). Preserved code names, placeholders, numbers and meanings.
Assignment finished; no pending work/refusals.

## Final Russian translation batches, 2026-10-25

Root completed eng.campevents44/soundscripts28, eng.campmap37,
eng.campaint54. Exact exemptions: ship in campevents.is_not_one_of_the_eight
and campaint.ships_own_so_it_does_not_see means distributes; port_verb in
campaint.is_a_marker_colour_black_is/is_not_a_marker_map_regions/
settlement_or_port_pixels_left_alone means harbor; orphan in
campmap.this_region_is_renaming_it_here means breaking references.

All9,605 strings validate, no stale/extra. Suites i18n37/37, termbase27/27.
All378 plural entries pass nine representative Russian counts.
Local preview at8758 forced draft Russian without exposing a live catalogue.
Home/Settings/Transfer/campaign map inspected at available605px browser
width; visible controls wrap and tooltips retain explanations. No mod writes.
Map layer names supplied by backend remain English (Fog, Regions, etc.);
unit names/categories are mod data. Full all-screen desktop and375px QA
remains pending. No promotion or native-speaker review claim.

## Final batch: ru-assets-last-review

# Russian assets last review

Completed eng.banners31, eng.meshwrite24, eng.factionbring16, eng.factionclone24, eng.sidefiles59, sidefiles49 =203 strings. Answer files .cache/ru-assets-last-answer1.json and answer2.json, bounded source files .cache/ru-assets-last-batch1.json and batch2.json. Final merges zero refusals.

Exemption eng.sidefiles.line_a_symbol_sheet_before_any / faction: factions is a literal file section keyword, retained in backticks. No other exemptions needed. All file paths, XML tags/attributes and config keys preserved, including Faction, factions, GameArea, On_display, Item, AdviceThread, Trigger, standard_index, hold_regions, FactionType and banner. Russian four plural forms supplied; save_changes retains explicit zero too.

Terms: banner знамя, standard штандарт, advice thread цепочка советов (short цепочка), sheet лист, score оценка; clone rendered with клонирование forms consistent with required stem. Faction frame placeholders denote base faction and remain unchanged. No shared docs/termbase/promotion edits; assigned work complete.

## Final batch: ru-map-last-review

# Russian final map namespaces

Completed194: mapcheck46, osmworld49, regiondel38, eng.regiondel34, eng.osmmap27. Checked merges121 plus73, zero remaining refusals. Answers .cache/ru-map-last1-answer.json and .cache/ru-map-last2-answer.json. Fresh missing export0.

Exemptions:
- eng.osmmap.openstreetmap_is_off_turn_it_on: turn means enable.
- osmworld.drag_to_pan_wheel_to_zoom: turn means rotate.
- mapcheck.records_what_is_wrong_now_as: record is the verb mark, not a data record; rendered Отмечает.
- eng.regiondel.already_has_a_port_of_its, regiondel.already_has_a_port_and_only, regiondel.has_no_port_of_its_own, regiondel.its_port: port_verb; harbor noun.
- regiondel.the_heir, eng.regiondel.s_go_with_the_section_because, eng.regiondel.the_region_section_and_its_fort: heir means region receiving deleted land, not faction succession; rendered регион-получатель.

Baseline=исходный список (existing problems tolerated on saves), finding=проблема, geographic box=рамка, backdrop=подложка. Preserved code region {name}, playable/unlockable/nonplayable and all code filenames/HTML. Four plural forms, source placeholder differences retained for taken_out_of_campaigns. No shared docs/termbase edits or promotion. Latest45% used /55% remaining; stopped after assignment.

## Final batch: ru-scriptwords-final-review

# Russian script descriptions completion

eng.scriptwords264 completed in90/90/84 batches. Final namespace checker:
264 strings,0 problems;0 missing/stale/extra. One refusal corrected with
semantic unit exemption (coordinate measurement, not a troop).
Answers .cache/ru-scriptwords-{1..3}-answer.json and ru-scriptwords-3-fix.json.
Shared changes main/dev/i18n/ru.json and ru.source.json via checked locked
merges only; no promotion/shared documents/termbase edits. Native review
still required, no visual QA. Last five-hour usage63% used,37% remaining.

Exact exemptions:
- eng.scriptwords.cond_help_game_d1e6: trait appears in literal command
  Trait GoodCommander > 0; turn either I_TurnNumber or the verb invert,
  not campaign turn. Exempt trait,turn. Placeholder names remain literal.
- eng.scriptwords.act_help_console_3820: Battle is literal console argument
  of kill_character; exempt battle.
- eng.scriptwords.setting_help_avoid_growth_ag_offset_x_36c9: unit means
  coordinate unit of measurement; exempt unit.

Terminology: sack «разграбить/разграбление»; raze «разорить/разорение»;
Avoid Growth «Избегать роста»; Recruitment Order «Порядок набора»;
remembered number «запомненное число»; client kingdoms «зависимые королевства».
Preserved exact command examples, console functions, argument spelling,
file paths and placeholders. Add-on display names translated by function.
No pending refusals or unmerged translations; stopped at assignment boundary.
