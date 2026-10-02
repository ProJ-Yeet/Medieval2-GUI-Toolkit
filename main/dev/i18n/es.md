# Spanish (`es`) - how the catalogue is written

Read before translating a batch. The rules of Phase 88 (ROADMAP.md) come first;
this is what they mean for Spanish, and the choices made once so every batch
makes them the same way. The workflow is German's (`dev/i18n/de.md`).

## Workflow

```bash
python dev/checks/i18n_todo.py es                          # what is left, by namespace
python dev/checks/i18n_todo.py es --batch NS... --out B.json   # export strings to translate
python dev/checks/i18n_todo.py es --merge A.json           # A.json = {id: Spanish}, checked, merged
python dev/checks/i18n_todo.py es --promote                # only when the report is empty
```

A refused string prints why. Fix it and merge it again; never merge around the
checker. The answer file holds only `{id: translation}` (and `_exempt` if a
sentence is truly worded around a term; say why in the review notes, below).

## Which Spanish

**Spain Spanish (castellano)**, as the Spanish release of Medieval II: Total
War, but in words a Latin American modder reads without stopping: *archivo*,
never *fichero*; *ordenador* is avoided (say *equipo* or nothing); *Añadir*.

## Voice

- **tú**, as Windows and Microsoft's Spanish style do, but address the reader
  as little as possible: an infinitive or an impersonal sentence first
  (*Se guardará una copia*, *Hay que elegir una carpeta*). Never *usted*,
  never *vosotros*.
- Buttons and menu items are **infinitives**: *Guardar*, *Añadir unidad*,
  *Descartar cambios*. Not imperatives (*Guarda*, *Añade*).
- Headings and tab names are **nouns**: *Edificios*, *Mercenarios*,
  *Configuración*. Sentence case: only the first word and proper names
  capitalised (*Archivos menores*, not *Archivos Menores*).
- Status lines are short: *Leyendo…*, *Guardado.*, *Nada seleccionado*.
- Keep the English register: plain, dry, exact. No exclamation marks the
  English does not have. No *por favor* unless the English says please.
- Sentences that explain (tooltips, notes, findings) are full Spanish
  sentences, reordered as Spanish needs; never word for word.

## Typography

- Quotes: «…» (and “…” inside). Keep `'` and `"` that are part of code or HTML.
- Opening ¿ and ¡ always: *¿Sobrescribir el archivo?*
- Ellipsis `…` stays the one character. Arrows, emoji and symbols (`→`, `🕑`,
  `⚙`, `＋`, `✕`, `·`) stay exactly where the English puts them.
- An English compound becomes a phrase: *battle model* is *modelo de
  batalla*, *unit file* is *archivo de unidades*. A code name is never glued
  into a word: *la entrada EDU*, *la entrada de modeldb*, *el archivo
  descr_strat.txt*.
- Gender and number agree with the noun, including around a `{placeholder}`
  whose gender is unknown: word it so the placeholder stands alone
  (*Unidad: {name}*, not *La {name} …*).
- Number and date formats come from the code (`Intl`), never typed in a string.

## What is never translated

Everything the checker calls rule 1: whatever is inside `<code>`, any file name,
any `snake_case` name, `{placeholders}`, HTML tags and attributes, and the
`keep` list (EDU, EDB, BMDB, IWTE, M2EX, OpenStreetMap...). Product names stay:
*Medieval 2 GUI Toolkit*, *Medieval II: Total War*, *Divide and Conquer*.
The toolkit's module names that are proper names (*Unit Transfer*) are
translated as what they do: *Transferir unidades*.

## Terms

The termbase column is the source (`web/i18n/termbase.json`, `es`). The batch
lists every term a string uses, with the rendering and its stem. The ones that
need care:

| English | Spanish | note |
|---|---|---|
| ancillary | séquito (el; un miembro del séquito) | the game's own word |
| trait | rasgo | |
| turn | turno | the game's word |
| settlement / city / castle | asentamiento / ciudad / castillo | |
| unit | unidad | *archivo de unidades* for the unit file (EDU) |
| entry / record | entrada / registro | an entry in a list vs one record of a data file |
| log (the toolkit's) | Historial | *🕑 Historial puede deshacerlo.* |
| tile | casilla | a square of the campaign map |
| tier / level | grado / nivel | *grado de armadura*; a building's *nivel* |
| port (verb) | portar | move between mods; the harbour noun is *puerto* |
| transfer | transferir, transferencia | |
| strat map | mapa estratégico | |
| clear | Borrar (a field), Restablecer (a filter) | |
| Minor Files (the screen) | Archivos menores | |
| ticked (a count) | marcadas / marcados | *3/10 marcadas*, never *casilla de verificación* in a counter |
| shield | escudo | both the heraldic shield and the soldier's |
| ship (verb, "this mod ships X") | incluir, traer | *este mod incluye…*; the vessel is *barco* |

A term not in the termbase (a new one) is worded the way a Spanish-speaking
modder on TWCenter or a Spanish Total War forum would say it; note it under
*Review notes*.

## Plurals

Spanish has `one`, `many` and `other` (CLDR's `many` is for a million and up:
*1 000 000 de unidades*). A plural entry in the answer is
`{"one": "...", "many": "...", "other": "..."}`; `many` is `other` with *de*
before a noun where Spanish needs it, and otherwise the same text. `{count}`
is filled by the page.

## Placeholder words that are English

A few strings take an English word as a parameter (`{noun}s`, `{label}s`,
`{what}s`): the code passes English. Do not glue Spanish endings onto them;
write around them, `{noun}: {count}` or `{count} × {noun}`, so the English
word stands alone.

## Review notes

Doubts for the native reviewer, one line each: the ID, the doubt.

- (termbase, 88f) ancillary is *séquito*, tier *grado*, log *Historial*,
  add *Añadir*; *voz* matches *voces*.
- (termbase, 88f) battle model, strat model: the plural (*modelos de batalla*,
  *modelos estratégicos*) now passes; view also matches the noun *vista*.
- (code, 88f) Two strings took an English word from the code and now are whole
  sentences in every language: campaint.of_the_oldest_stroke_been_let (a
  plural by count) and editor.added_as_armour_tier /
  added_as_repeated_armour_tier. German had shown the English in both.
- (88f) The fragments that follow a mod name (ancillaries.s_ancillaries,
  areaeffects.s_area_effects, buildings.s_buildings,
  campdb.s_campaign_constants) read *Leyendo DaC: edificios…*.
- (g1) _exempt ship, "incluye": buildings.borrowed_from_the_unpacked_vanilla_ui, buildings.this_mod_ships_no_file_at, campaint.written_into_a_settlement_the_music, campbrowse.campaigns_read_in_ms, campbrowse.every_campaign_this_mod_ships_with, campbrowse.nothing_in_to_read_a_menu, campbrowse.ships_map_layers.
- (g1) _exempt port_verb, harbour noun puerto: campaint.add_a_province_decide_its_record, campaint.place_the_port_pixel_or_skip, campaint.writes_layers_at_once_in_the, campcreate.new_region_name_paint_settlement_port, campcreate.port, campcreate.port_marker_add_or_move_on, campcreate.select_a_region_first_then_choose.
- (g1) _exempt keywords, keys and paths: ancillary ancillaries.not_found_in_data_ui_ancillaries; upgrade buildings.every_rule_over_the_shape_of; level buildings.level_key, buildings.level_3; faction buildings.rows_marked_faction_live_in_this; banner/faction/unit battleflags.banner_faction, banner_holy, banner_unit; campaign campbrowse.its_folder_is_and_its_first. turn: buildings.its_battle_model_has_no_texture, buildings.units_without_battle_model_texture ("turn up", aparecerían).
- (g1) Coined: restricción (a resource gate), gemelo/a (twin), ficha (card), Reflejar (mirror), hueco (gap), preparado (staged), aspecto (faction skin), reposición (pool replenishment), Cuentagotas (pipette), Bote (bucket), galón (chevron), desplegar (field a unit), elemento que lo usa (areaeffects.user_count), Edición masiva (bulk edit). Kept English: odd, Newtown, `ownership`, the campaint examples "catholic 100" and "gold, wine".
- (g1 doubt) joins to check on screen: bmdb.the_roster_asks_for with bmdb.entries_already_have_every_record; the "’s ancillaries" fragments (ancillaries.s_ancillaries, areaeffects.s_area_effects, buildings.s_buildings, campdb.s_campaign_constants) worded "X de…" with the mod name before them; ancillaries.pool_help_per_turn "▲▼ la mueven".
- (g1 doubt) termbase: open stem abr rejects abierto; ancillary, campaign, level, turn and upgrade fire on file keywords and paths.
- (g2) _exempt settlement, the folder name `settlements`: campforts.no_settlements_folder_here_to_check, campforts.the_folder_under_settlements_ambient_settlements. mercenary, the folder `merc`: cards.and_more_written_into_the_merc, cards.confirm_move_folded, cards.copying_file_s_out_writing_into, cards.merc, cards.one_is_the_merc_copy, core.the_two_pictures_per_unit_deduplicated. unit: cards.data_ui_units_data_ui_unit (a path). terrain: campmap.comp_key, campmap.draw_the_ground_the_way_the (a key and a path).
- (g2) _exempt ship, "incluye": campmap.has_no_campaign_map_this_tool, campmap.ships_its_own_so_that_layer, campmark.this_mod_ships_its_own_picture, campnew.map_layers_note, campnew.this_mod_ships_only_the_compiled, cards.mod_units_summary, changes.every_version_is_off_the_mod, changes.one_is_on_at_a_time, climates.append_a_name_the_engine_does, climates.taking_over_one_of_the_twelve, core.every_model_a_mod_ships_the.
- (g2) _exempt turn, a verb (girar, activar, desactivar): campmap.click_a_province_to_inspect_it, campmap.the_campaign_map_as_a_surface, campmap.the_heights_as_a_surface_with, campmap.tab_osm_title, changes.turn_off, changes.turn_off_putting_the_original_records, changes.turn_on, codeview.line_every_value_up_in_one, core.the_tool_did_not_finish_loading.
- (g2) _exempt port_verb, harbour noun puerto: campmap.port_marker, campmap.port_pixel, campmap.port_pixels_undecided, campmap.region_id_tiles_settlement_at_game, campmap.settlement_character_and_port_names_beside, campmap.tiles_regions_settlements_ports, campmark.named_character_general_admiral_port_spy, campmark.port, campmark.ports, campmark.show_settlements_ports_and_campaign_objects.
- (g2) _exempt building: campmap.building_the_composite (a gerund). view: campmap.views (the noun, Vistas). character: codeview.every_string_here_is_stored_as (letters). battle_model: core.battle_models (plural).
- (g2) Coined: reasignar (take over a climate slot), colores calados (punched through), Menú principal (Front end), calor (heat), Hallazgos (Findings), Temprana/Tardía (eras), Propio (Yours), Pintar (Paint), Mayús (Shift), tarjeta de unidad (unit card), descripción emergente (tooltip). "&amp;" in tab names worded "y".
- (g2 doubt) campmap.this_is_the_short_wasteland_form: "arbiter" worded el árbitro, unclear what it names. core.the_items_and_followers_a_character: "followers" worded seguidores, perhaps séquito. core.added_by_you, core.removed_by_you: "por el usuario", avoiding tú. campmap.rivers_only_is_on_the_three: casillas de verificación beside casilla = tile.
- (g3) _exempt battle_model (plural, before the stem allowed it): editor.adds_the_tier_and_opens_the, editor.battle_models_bmdb, editor.edit_in_the_battle_models_tab, editor.no_unit_is_open_so_nothing. mesh: editor.draw_this_model_its_parts_its (the .mesh file).
- (g3) _exempt banner, a comment heading in the unit file (rótulo), not a standard: edusort.a_banner_like_gondor_tier_2, a_comment_in_this_file_starts, a_tier_read_from_a_banner_is, a_unit_with_no_tier_sorts_after, read_tiers_from_the_files_own, section_banners, the_shape_is_fixed_so_the_next, write_a_banner_above_each_section. tier/infantry: edusort.gondor_tier_2_infantry(_2), a_banner_like_gondor_tier_2 (sample text the sorter parses, English). character: edusort.line_character (a typed character). turn: eng.animloose.turns_bones_and_its_skeleton_has (gira).
- (g3) _exempt ship, "incluye": eng.animpack.the_source_ships_no_packs_of, eng.animslot.this_mod_ships_no_animation_packs, eng.buildings.hidden_ceiling_note, eng.campaint.ships_own_so_it_does_not_see, eng.campevents.is_not_one_of_the_eight, eng.campfiles.this_mod_ships_only_so_the, eng.campnew.is_not_on_disk_and_ships, eng.campnew.nothing_names_on_the_new_game_menu_archive, eng.campnew.ships_map_layer_s_of_its. port_verb, harbour: eng.campaint.is_a_marker_colour_black_is, is_not_a_marker_map_regions, settlement_or_port_pixels_left_alone.
- (g3) _exempt keywords in backticks: event eng.campevents (6: an_event_line_needs_*, line_event_takes_a_category_and, line_is_before_the_first_event); building eng.buildings.line_building_has_no_opening_brace; faction eng.campimport.has_no_faction_block_so_name, eng.campstrat.faction_relationships_does_not_read_as, faction_standings_does_not_read_as; culture eng.campstrat.fort_line_does_not_read_as; resource eng.campstrat.resource_line_does_not_read_as; castle eng.campstrat.settlement_header_says_the_engine_knows; armour/unit eng.campstrat.should_be_armour, unit_line_does_not_read_as.
- (g3) Coined: pertenencia (ownership), identificador (an event's label), Texto sin formato (Raw text tab), Comprobar (Check panel), clasificador (sorter), yermo (wasteland), ruta comercial (trade route), pose base (bind pose), tanda (a faction's run of units), grafías (spellings). "by you" worded "a mano" (editor.added_by_you_drag_to_reorder, removed_by_you_click_to_put).
- (g3 doubt) rótulo for a section banner; animation pack worded singular where the stem would not take the plural.
- (g4) _exempt port_verb, harbour noun puerto: eng.mapcheck.second_port_pixel(_for_owner), eng.mapcheck.starts_with_a_and_map_regions, eng.mapcheck.the_port_pixel_at_has_no, eng.mapcheck.the_port_pixel_at_touches_no, eng.mapnewreal.province_s_grown_from_their_cities, eng.minorfiles.this_cultures_port_ladder_has_lines, eng.regiondel.already_has_a_port_of_its.
- (g4) _exempt ship, "incluye": eng.climatenew.a_climate_name_the_battle_map, eng.climatenew.all_four_mods_measured_for_this, eng.namekeys.this_mod_ships_only_strings_bin. turn, a verb (mover, activar): eng.casanim.turns_bones_and_the_skeleton_has, eng.osmmap.openstreetmap_is_off_turn_it_on. character, letters (caracteres): eng.codeview.length_says_but_text_is(_and_more), eng.modeldb.characters_left_over_after_the_entry.
- (g4) _exempt for file keywords, extensions and paths: heir/leader eng.characters.has_strat_model_s_a_named; soldier eng.dupes.a_renamed_block_is_a_real; populace eng.factionsites (4); guild eng.guilds.guild_is_declared_twice_the_engine, the_scope_letter_is; level eng.guilds (4, `levels`); texture eng.fileswap.this_dds_cannot_go_into_a, eng.modelexport.this_is_not_a_texture_there; mesh/archive eng.mesh.is_not_a_mesh_expected_a, the_archive_header_is_not_a, eng.modeldb.not_a_modeldb_archive_magic, this_does_not_start_like_a; culture eng.minorfiles.line_before_the_first_culture_line; faction eng.minorfiles.this_text_has_no_faction_line, eng.sidefiles.line_a_symbol_sheet_before_any, eng.factionaudit.joins_it_builds_and_recruits_wherever_clauses; river eng.mapnewreal.rivers_is_none_or_one_of; upgrade eng.settlemech.upgrade_is_above_max_which_the, upgrade_is_not_s_base_both; unit/pool eng.mercpools.line_is_not_pool_regions_or; battle eng.heroabilities.not_in_ui_battle_sd_so; banner eng.edusort.unit_s_have_no_tier_yet (section banners, rótulos).
- (g4) _exempt frame, a picture crop (recuadro), not an animation frame: eng.mapfe.the_frame_at_x_g_y, the_frame_is_w_g_x(_2), eng.server.the_frame_is_not_four_numbers.
- (g4) Coined: hilo (AdviceThread), consejero (advisor), hoja de símbolos (symbol sheet), cierre inesperado (crash), mota de tierra (speck of land). Bare "ported" worded around the stem portar: eng.portrecords.has_no_so_no_text_key, eng.changesets.ported_change_s_from. {noun} strings worded "un elemento ({noun})" or "{noun}: …".
- (g4 doubt) termbase: frame needs a picture-crop sense (recuadro); port_verb wants a harbour term (puerto) beside it; archive should not fire on a boost serialization archive; level and culture fire on keywords in backticks.
- (g5) _exempt keywords and paths: event eng.soundbanks/sounds/soundscripts.line_end_with_no_open_event; texture eng.sprites.truncated_texture_file; heir/leader eng.stratchar.is_not_a_rank_a_character; character eng.stratchar.s_family_line_on_line_names; castle/settlement eng.stratedit.a_settlement_block_opens_with_the, the_header_says_the_engine_reads, eng.stratobj.there_is_no_folder_under_any; level/trait/trigger eng.traits.line_an_effect_outside_any_level, line_this_trait_has_no_name, trigger_affects_which_this_file_does, eng.triggers.line_this_trigger_has_no_name; mount eng.transfer.engine_skeleton_the_mounted_engines_class; unit eng.transfer.mercenary_icons_card_info_card_go; campaign eng.transfer.mercenary_to_actually_recruit_it_add, facaudit.world_maps_campaign; missile eng.transfer.projectile_model_cas_files_were_copied, guided.a_projectile_is_set_but_the_weapon_type_is_type, light_heavy_missile_spearmen, missile_infantry_cavalry_and_siege; horde guided.with_two_formations_the_first_must.
- (g5) _exempt other senses: ship ("incluye", "trae") eng.stratcamp.is_not_a_word_the_engine, eng.stratedit.stays_on_the_map_with_no, two_levels_of_stand_in_this, eng.winconds.could_not_be_read_the_stock, guided.vanilla_ships_it_commented_out(_on), guided.men_in_the_unit_at_the_largest; character (letters) stringsbin.a_single_string_cannot_exceed_65535, a_string_says_it_is_characters; port_verb (harbour) eng.stratobj.is_pixel_none_of_the_800; trigger (verb) guided.armour_upgrade_models_outnumber_levels; charge (the smith's price, cobra) guided.florins_the_smith_charges_to_upgrade(_2); turn guided.optional_the_effect_played_when_the_weapon.
- (g5) guided.*: the EDU's syntax lists kept English (faction_faction*, heavy_light_general, infantry_cavalry_siege_ship_handler, level_level_level, model_*, morale_discipline_training_lock_morale, armour_*_hit_sound, attack_*, banner_*, turns_recruit_upkeep_weapon_ug_armour).
- (g5) Coined: Modificador de cabeza (head_modifier, meaning unclear), cuota (share), Vídeos (Movies), Selecciones libres (free picks), Factor esq. (Skel. factor), Máquina con montura (mounted engine), huir en desbandada (rout), Pesada/Ligera, Temprana/Plena/Tardía (custom battle eras), postura (standing), pieza de artillería, Resistencia (stamina), círculo cántabro, muralla de lanzas (spear wall; perhaps formación de lanzas), enemigos con montura, habilidad de defensa.
- (g5 doubt) guided.locked_by_the_voice_panel_whole quotes the button "No importar sonido" (transfer.dont_import_sound): check they match. Engine messages whose {what}, {kind}, {kw}, {which}, {category}, {ground} may be English from the code: eng.stratobj.* (12), eng.transfer.model_needs_animation_s_which_does, the_s_model_uses_animation_s, rename_taken_used_instead, eng.soundbanks.every_unit_or_character_with_this, there_is_already_a_beside_it, guided.which_weapon_attributes, which_weapon_bonuses, spearmen_is_an_infantry_class_on_a_category_unit; each is worded so the value stands alone.
- (g6) _exempt frame, the map's rectangle (marco, encuadrar): map3d.frame_the_whole_map_again, mapfe.before_this_panel*, proposed_frame, put_the_frame_back*, the_frame, the_frame_2, the_frame_is_which_rectangle_of, the_front_end_layer_is_not, osmmap.the_style_above_cut_to_the.
- (g6) _exempt verbs and other senses: building map3d.building_the_mesh, mapquery.building_that_map; record mapcheck.records_what_is_wrong_now_as (Anota); mount home.mounted_pack (paquete montado); turn mapsize.turn_the_real_world_switch_on, mapsize.turned, osmmap.in_the_boxs_corners_off_the, off_this_is_the_one_part, open_settings_to_turn_it_on, where_the_maps_edges_are_in, the_style_above_cut_to_the, osmworld.drag_to_pan_wheel_to_zoom; ship minorfiles.where_it_starts_every_regions_religions; tile osmmap.tiles_are_kept_on_disk_for (map-image tiles, teselas); archive health.every_check_the_toolkit_has_over.
- (g6) _exempt port_verb, harbour or the key port:{region}: maplabels.port, port_2, minorfiles.port_ladder_line_s_in_the, the_culture_the_record_does_not, this_culture_has_no_port_lines, osmmap.make_land_tiles_inside_openstreetmaps_water_confirm, make_land_tiles_on_the_water_coastline, mylaes_layout_the_maps_layers_as.
- (g6) Coined: fragmento (chunk), línea base (baseline), sellar (stamp a baseline), escala de asentamientos / de puertos (ladder), guardia personal (bodyguard), tiempo de recarga (cooldown), linaje familiar, hechos transparentes (punched out), chincheta del mapa (map pin), Pueblo pesquero, d. C. (AD); modelpicker.lod_skin keeps "skin".
- (g6 doubt) home.kept_by_a_compaction_all_the ("una", a copy?); hordestart.descr_sm_factions_txt_already_has / _has_none_source (masculine plural assumed); mapquery.on = activado; "Mylae" read as a person.
- (88f, code) Placeholders filled with English by the code, worded so the value stands alone, but they show English in every language: minorfiles.* {noun} (10 strings), mapfe.before_this_panel_the_picture_was {was}, osmmap.the_box_stretches_the_map_than and osmworld.the_box_would_stretch_the_map {st2} (wider/taller), osmmap.a_planned_on_where_stands_check_it {kind}, osmmap.the_label {label}, home.works_but_this_mod_has_no and home.needs_and_this_mod_has_none {partial}/{missing}, hordestart.files {mode}, osmworld.that_would_put_the_box_past {x}.
- (g7) _exempt verbs and other senses: mount packs.battle_model_entr_travel_with_them (monta); model rawtext.pick_a_file_on_the_left; turn rebels.of_provinces_name_a_rebel_faction, sprites.flag_turned_off, sprites.the_bypass_flag_makes_the_next_normal, stratchar.what_should_the_player_read_for_prompt; ship sprites.this_mod_ships_m2tweop_so_generation, soundbanks.has_no_data_the_game_uses; port_verb (harbour) regiondel.already_has_a_port_and_only, has_no_port_of_its_own, its_port; port_verb ("ported", worded around the stem) portui.ported_n_noun_into_dest_undo_in_log, settings.animations_ported_into, settings.changes_ported_into.
- (g7) _exempt keywords and paths: building settings.start_the_soldier_row_on_base (a verb); soldier settings.use_the_base_units_soldier_line; level settlemech.factor, settlemech.level; upgrade settlemech.a_levels_upgrade_is_the_population; armour sprites.armour_ug; block stratcamp.block_needs_at_least_one_movie; faction stratcamp.faction_bik; character settings.and_more_characters_in_the_diagnostic (letters); settings soundbanks.line_default_settings_sources_count, setting_count_suffix, stratcamp.the_campaigns_own_settings_when_it (ajustes).
- (g7) Coined: omisión (bypass flag), marca (flag), frase de voz (bark), reserva (name pool), posiciones (standings), tramos (runs), sinopsis (blurb), bolsa (purse), Hojas (sheets); billboards and mipmaps kept English.
- (g7 doubt) joins: stratcamp.a_new + <faction> + block_needs_at_least_one_movie; settlemech.castle / city "castillo ×". soundbanks.bank_name and DEFAULT: kept as file syntax. stratcamp.no_settlement_and_nobody_two_factions (timúridas assumed feminine).
- (88f, code) More English from the code: renameui.rename {what}, confirm_rename {x}; portui.* {noun}; stratcamp.write_for_in, write_in {what}, write_wins_confirm {action}; stratcamp.a_year_and_season {seasons} ("summer or winter"); settings.in, resource_in {x}, edit_in {mode}; settlemodel.a_model_for, now_draws {target} (city/castle); soundbanks.numbers (" to " joined in code); stratchar.line ("(nobody)").
- (g8) _exempt ship, "incluye": stratmap.draw_a_campaign_map_model_beside, stratmap.not_shipped, stratview.this_mod_ships_no_data_models, v3anim.played_from_vanillas_pack_this_mod, v3anim.vanillas_skeleton_pack_this_mod_ships, viewer3d.drawn_at_shipped, viewer3d.draw_the_texture_at_the_size. mercenary, the folder `merc`: transfer.merc_icons_off, merc_icons_on, put_the_unit_card_and_info. port_verb: v3anim.ported_a_skeleton (portó). turn (girar): v3anim.turn_every_key, turns_to, viewer3d.drag_to_turn_wheel_to_zoom. texture (.texture): v3anim.a_texture_from_disk_to_dds. building (Generando): v3anim.building_the_glb, building_the_obj_zip. charge (an animation name): v3anim.walk_charge_die_a_file_name. pool (vertex pool): viewer3d.groups_over_pool.
- (g8) Coined: Aspectos (skins), hoja (texture sheet), isla (UV island), Baqueta (ramrod), Virote de balista, Estructura alámbrica (wireframe), Disposición UV, en mano / guardada (weapon drawn / stowed), en el brazo / a la espalda (shield carried / slung), Quieto (Still), Tripulación (crew).
- (g8 doubt) transfer.s_value_click_to_s_own ends on a code word ('import'/'keep'). More English from the code: transfer.mount_help, officer_help {which}; transfer.has_no_skeleton* {x}; v3anim.no_mount_in_descr_mount_txt {x}; v3anim.s_leaves_empty, pack_message {action}; stratedit.confirm_verb {verb}; triggerui.exports 'nothing'; transfer.say 'added'.
- (code, 88f) triggerui.and / triggerui.or are options whose label was read back as the joiner written to the file, so German wrote "oder" into export_descr_*.txt. The options now carry value="and" / "or"; Spanish reads y / o.
