# German (`de`) - how the catalogue is written

Read before translating a batch. The rules of Phase 88 (ROADMAP.md) come first;
this is what they mean for German, and the choices made once so every batch
makes them the same way.

## Workflow

```bash
python dev/checks/i18n_todo.py de                          # what is left, by namespace
python dev/checks/i18n_todo.py de --batch NS... --out B.json   # export strings to translate
python dev/checks/i18n_todo.py de --merge A.json           # A.json = {id: German}, checked, merged
python dev/checks/i18n_todo.py de --promote                # only when the report is empty
```

A refused string prints why. Fix it and merge it again; never merge around the
checker. The answer file holds only `{id: translation}` (and `_exempt` if a
sentence is truly worded around a term; say why in the review notes, below).

## Voice

- **Sie**, formal, as Windows and the German release of the game do. Never du.
- Buttons and menu items are **infinitives**: *Speichern*, *Einheit hinzufügen*,
  *Änderungen verwerfen*. Not imperatives (*Speichere*, *Füge hinzu*).
- Headings and tab names are **nouns**: *Gebäude*, *Söldner*, *Einstellungen*.
- Status lines are short and passive or nominal: *Wird gelesen…*, *Gespeichert.*,
  *Nichts ausgewählt*.
- Keep the English text's register: plain, dry, exact. No exclamation marks the
  English does not have. No "Bitte" unless the English says "please".
- Sentences that explain (tooltips, notes, findings) are full German sentences,
  reordered as German needs; never word-for-word.

## Typography

- Quotes: „…“ (and ‚…‘ inside). Keep `'` and `"` that are part of code or HTML.
- Ellipsis `…` stays the one character. Arrows, emoji and symbols (`→`, `🕑`,
  `⚙`, `＋`, `✕`, `·`) stay exactly where the English puts them.
- A hyphen-joined English compound becomes one German word where German writes
  one (*Schlachtmodell*, *Einheitendatei*), with a hyphen only where a code name
  or an acronym joins it: *EDU-Eintrag*, *modeldb-Eintrag*, *BMDB-Datei*.
- Nouns capitalised, as always; a code name inside a German compound keeps its
  own case (*descr_strat.txt-Datei* is wrong, write *die Datei descr_strat.txt*).
- Number and date formats come from the code (`Intl`), never typed in a string.

## What is never translated

Everything the checker calls rule 1: whatever is inside `<code>`, any file name,
any `snake_case` name, `{placeholders}`, HTML tags and attributes, and the
`keep` list (EDU, EDB, BMDB, IWTE, M2EX, OpenStreetMap...). Product names stay:
*Medieval 2 GUI Toolkit*, *Medieval II: Total War*, *Divide and Conquer*.
The toolkit's module names that are proper names (*Unit Transfer*) are
translated as what they do: *Einheiten übertragen*.

## Terms

The termbase column is the source (`web/i18n/termbase.json`, `de`). The batch
lists every term a string uses, with the rendering and its stem. The ones that
need care:

| English | German | note |
|---|---|---|
| ancillary | Gefolge (das; ein Gefolgsmitglied) | the game's own word |
| trait | Eigenschaft | |
| turn | Runde | the game's word, not *Zug* |
| settlement / city / castle | Siedlung / Stadt / Burg | |
| unit | Einheit | *Einheitendatei* for the unit file (EDU) |
| entry / record | Eintrag / Datensatz | an entry in a list vs one record of a data file |
| tile | Kachel | a square of the campaign map |
| port (verb) | portieren | move between mods |
| transfer | übertragen, Übertragung | |
| log (the toolkit's) | Protokoll | *🕑 Protokoll kann es rückgängig machen.* |
| strat map | Kampagnenkarte | |
| clear | Leeren (a field), Zurücksetzen (a filter) | stem *leer* is what the checker wants on a bare "Clear" |
| Minor Files (the screen) | Nebendateien | |
| ticked (a count) | markiert | *3/10 markiert*, never *Kontrollkästchen* in a counter |

A term not in the termbase (a new one) is worded the way a German modder on
TWCenter or Mundus Bellicus would say it; note it under *Review notes*.

## Plurals

German has `one` and `other`. A plural entry in the answer is
`{"one": "...", "other": "..."}`; `{count}` is filled by the page.

## Placeholder words that are English

A few strings take an English word as a parameter (`{noun}s`, `{label}s`,
`{what}s`): the code passes English. Do not glue German endings onto them;
write around them, `{noun}: {count}` or `{count} × {noun}`, so the English word
stands alone.

## Review notes

Doubts for the native reviewer, one line each: the ID, the doubt.

- (none yet)
- (g1 exemptions) port: campcreate.new_region_name_paint_settlement_port, campcreate.port, campcreate.port_marker_add_or_move_on, campcreate.select_a_region_first_then_choose, eng.campaint.is_not_a_marker_map_regions, eng.campaint.settlement_or_port_pixels_left_alone, eng.campaint.is_a_marker_colour_black_is, eng.stratobj.is_pixel_none_of_the_800: "port" is the harbour noun (Hafen), not the verb.
- (g1 exemptions) ship: eng.campaint.ships_own_so_it_does_not_see, eng.campevents.is_not_one_of_the_eight, eng.namekeys.this_mod_ships_only_strings_bin, eng.winconds.could_not_be_read_the_stock, core.every_model_a_mod_ships_the, buildings.borrowed_from_the_unpacked_vanilla_ui, buildings.this_mod_ships_no_file_at: "ship" is the verb "to come with/deliver", not a vessel.
- (g1 exemptions) event: eng.campevents.an_event_line_needs_a_*, eng.campevents.line_event_takes_a_category_and, eng.campevents.line_is_before_the_first_event, eng.soundscripts.line_end_with_no_open_event: `event` is a file keyword in backticks, left as written.
- (g1 exemptions) character: codeview.every_string_here_is_stored_as: "characters" means letters of a string (Zeichen).
- (g1 exemptions) gate: buildings.every_gate_at_once_of_regions, buildings.every_resource_gate_at_once_from, buildings.no_region_passes_every_gate, buildings.province_s_carry_it_clause_s, buildings.take_off_the_line_shows_what, buildings.the_hidden_resources_line_at_the, buildings.then_give_it_to_provinces_in, buildings.unconditional_the_rest_need_every_gate, buildings.with_no_ownership_to_gate_to: "gate" is a build condition (Schranke, or "beschränkt auf"), not a siege gate (Tor). The termbase's gate entry should be narrowed or a second entry added.
- (g1 exemptions) upgrade: buildings.every_rule_over_the_shape_of: `upgrades` keyword in code. turn: core.the_tool_did_not_finish_loading, buildings.its_battle_model_has_no_texture, buildings.units_without_battle_model_texture: "turn up/turn it off" are verbs. level: buildings.level_3, buildings.level_key: code keys. hide: buildings.hidden: "hidden" worded verborgen. select: buildings.selected: worded "ausgewählt" (participle misses the stem auswähl).
- eng.cas.*, eng.mesh.*: Vertex plural written "Vertexe"; "chunk" kept as Chunk; "Gegenstück" used for "twin" (buildings.*); "Schranke" for build "gate".
- (g2 exemptions) ship: campbrowse.campaigns_read_in_ms, campbrowse.every_campaign_this_mod_ships_with, campbrowse.nothing_in_to_read_a_menu, campbrowse.ships_map_layers, climates.append_a_name_the_engine_does, climates.taking_over_one_of_the_twelve, eng.climatenew.a_climate_name_the_battle_map, eng.climatenew.all_four_mods_measured_for_this, eng.stratedit.stays_on_the_map_with_no, eng.stratedit.two_levels_of_stand_in_this, guided.vanilla_ships_it_commented_out*, v3anim.played_from_vanillas_pack_this_mod, v3anim.vanillas_skeleton_pack_this_mod_ships: "ships" is the verb (comes with / delivers), not a sea vessel.
- (g2 exemptions) turn: eng.animloose.turns_bones_and_its_skeleton_has, eng.casanim.turns_bones_and_the_skeleton_has, v3anim.turn_every_key, v3anim.turns_to, guided.optional_the_effect_played_when_the_weapon: "turns" is the verb (dreht / macht aus), not a campaign Runde. hide: traits.hidden, traits.hidden_2: worded "verborgen". character: edusort.line_character (a line glyph), eng.stringsbin.* ("characters" of a string, Zeichen). building: v3anim.building_the_glb, v3anim.building_the_obj_zip: "building" the file (erstellen). soldier/castle/settlement/unit/trait/block/culture/faction/port: keyword or code-name mentions in backticks (eng.mercpools.line_is_not_pool_regions_or, eng.dupes.a_renamed_block_is_a_real, eng.stratedit.the_header_says_the_engine_reads, eng.minorfiles.this_cultures_port_ladder_has_lines "port ladder" is a noun, eng.traits.trigger_affects_which_this_file_does quotes the game's English message).
- (g2 exemptions) guided.*: EDU syntax lists and field-name strings kept as the file spells them (armour_0_armour_1_armour_2, attack_charge_projectile_*, melee_attack_missile_attack_defence, banner_faction, banner_unit, faction_faction*, level_level_level, model_*, man_mount_animal, infantry_cavalry_siege_ship_handler, light_heavy_missile_spearmen, turns_recruit_upkeep_*); "mounted" meaning beritten (mount); "charges" the smith's price, "charge" in prec (verb); trigger/wall/close as verbs or adjectives; shield worded Schild, see next line.
- (g2 doubt) termbase `shield` renders "Wappen" (stem wappen); in the EDU it is the equipment, Schild. The termbase entry should read Schild (or lose the match). Also `tier` stem "stufe" collides with `level` (Stufe); both read Stufe here.
- (g2 refused, checker conflict) guided.also_the_filename_of_its_unit, guided.the_list_is_the_lt_factionbanners_gt, guided.the_list_is_the_lt_holybanners_gt, guided.the_list_is_the_lt_unitspecificbanners_gt: English holds `&lt;key&gt;` inside <code>; rule 1 wants the unescaped text and the HTML-tag check then sees a new tag, so no German text passes both. Left unmerged.
- (g4 exemptions) port_verb: campaint.add_a_province_decide_its_record, campaint.place_the_port_pixel_or_skip: "port" is the harbour noun (Hafen), not the verb.
- (g4 exemptions) ground: eng.mapnewreal.climates_is_one_ground_or_koppen, eng.mapnewreal.land_and_sea_from_the_real, eng.mapnewreal.the_highest_ground_peak_0f_m: "ground" is terrain/elevation or a code value (ground), not the ground-type layer. climate: eng.mapnewreal.climates_is_one_ground_or_koppen: code value. level: eng.mapnewreal.land_and_sea_from_the_real: sea level (Meeresspiegel), not a building level. river: eng.mapnewreal.rivers_is_none_or_one_of: code key `rivers`. port_verb: eng.mapnewreal.province_s_grown_from_their_cities: harbour noun (Hafen).
- (g3 exemptions) port_verb: regiondel.already_has_a_port_and_only, regiondel.has_no_port_of_its_own, regiondel.its_port, maplabels.character, maplabels.port, maplabels.port_2, campmark.port, campmark.named_character_general_admiral_port_spy, campmap.port_marker, campmap.port_pixel, campmap.port_pixels_undecided, campmap.region_id_tiles_settlement_at_game, campmap.settlement_character_and_port_names_beside, campmap.tiles_regions_settlements_ports: "port" is the harbour noun (Hafen), not the verb.
- (g3 exemptions) ship: campmark.this_mod_ships_its_own_picture, soundbanks.has_no_data_the_game_uses, eng.buildings.hidden_ceiling_note, sprites.this_mod_ships_m2tweop_so_generation, viewer3d.draw_the_texture_at_the_size, viewer3d.drawn_at_shipped, campmap.ships_its_own_so_that_layer, campmap.has_no_campaign_map_this_tool: "ships" is the verb (liefert mit), not a vessel.
- (g3 exemptions) turn: sprites.flag_turned_off, sprites.turn_the_flag_back_off, sprites.the_bypass_flag_makes_the_next_normal, viewer3d.drag_to_turn_wheel_to_zoom, campmap.click_a_province_to_inspect_it, campmap.the_campaign_map_as_a_surface, campmap.the_heights_as_a_surface_with, campmap.tab_osm_title: "turn" is the verb (drehen / ein- und ausschalten), not a campaign Runde. hide: campmap.hidden: worded "ausgeblendet". building: campmap.building_the_composite: "building" the composite (erstellen). terrain: campmap.comp_key, campmap.draw_the_ground_the_way_the: code key and a path.
- (g3 exemptions) gate: eng.buildings.is_still_used_province_s_carry: "gate on it" is a build condition, not a siege gate. unit/character/battle/campaign/record/upgrade/level/sprite_sheet: cards.data_ui_units_data_ui_unit and eng.heroabilities.not_in_ui_battle_sd_so, facaudit.world_maps_campaign, maplabels.character, mapcheck.records_what_is_wrong_now_as, settlemech.a_levels_upgrade_is_the_population (column name <b>upgrade</b>), settlemech.level: file paths, code keys or verbs. eng.codeview.length_says_but_text_is(_and_more): "characters" are letters of a string (Zeichen).
- (g3 exemptions) sprite_sheet (and shield): the checker's `sprite sheet` entry fires on any "sheet"; in viewer3d a sheet is a texture atlas, kept "Sheet" (viewer3d.sheet, main_sheet, attachment_sheet and 17 more). `shield` (viewer3d.shield*) is the unit's shield, Schild, not the termbase's Wappen.
- (g3 doubt) termbase: `sprite sheet` should not match a bare "sheet"; `uv map` matches any "UV" (worded UV-Map, viewer3d.uv_layout, show_uvs); `heights map` matches "heights" (worded Höhenkarte); `hide` matches "hidden"; `gate` and `shield` as noted. Worded by me: Fatal = schwerwiegend, baseline = Basislinie, finding = Befund, stamp (a baseline) = festhalten, bark = Zuruf, composite = Komposit, hireable = anwerbbar, heir (regiondel) = Erbe.
- (g3 refused, checker conflict) sprites.both_published_methods_stop_here_and: English holds `&lt;faction&gt;_&lt;model&gt;` inside <code>; rule 1 wants the unescaped text and the tag check then sees new tags, so no German text passes both. Left unmerged.
- (g4 exemptions) event: eng.soundbanks.line_end_with_no_open_event: `event` is a file keyword in quotes, left as written. ship: eng.stratcamp.is_not_a_word_the_engine: "ships it" means "comes with it", not a vessel.
- (g4 exemptions) ground: mapgen.the_real_ground_under_the_maps: "ground" is terrain (Gelände). ship: stratview.this_mod_ships_no_data_models: "ships" means "comes with". Termbase doubts: "heights map" stem forces Höhenkarte also for "the heights"; "overwrite" wants Überschreiben (capitalised stem?) so participles fail; "frame" wants Frame (not Rahmen).
- (g4 exemptions) port_verb: campaint.writes_layers_at_once_in_the: harbour noun. ship: campaint.written_into_a_settlement_the_music: "ships one" means "comes with". ground: mapsize.the_map_is_the_real_ground, mapsize.tiles_to_add_on_each_edge: terrain (Gelände), not the ground-type layer. turn: mapsize.turn_the_real_world_switch_on: "turn on" is a verb (einschalten).
- (g4 exemptions) turn: osmworld.drag_to_pan_wheel_to_zoom: "turn it" rotates the box (drehen). ground: osmworld.the_box_would_stretch_the_map: terrain (Gelände).
- (g5 exemptions) ship: campnew.map_layers_note, campnew.this_mod_ships_only_the_compiled, eng.animslot.this_mod_ships_no_animation_packs, eng.campnew.ships_map_layer_s_of_its, eng.campnew.is_not_on_disk_and_ships, eng.campnew.nothing_names_on_the_new_game_menu_archive: "ships" is the verb "comes with", not a vessel. event: eng.sounds.line_end_with_no_open_event: `'event'` is a file keyword. mount: eng.transfer.engine_skeleton_the_mounted_engines_class: "mounted engine" is a siege engine on a mount, not a Reittier. missile: eng.transfer.projectile_model_cas_files_were_copied: only inside the path models_missile. building: mapquery.building_that_map: the verb "is being built". sprite sheet: mapquery.more_than_a_spreadsheet_holds_in: "spreadsheet" is a Tabellenkalkulation. turn: rebels.of_provinces_name_a_rebel_faction: "turns off" is a verb.
- (g5) termbase doubts: "block" has stem "block" so the plural "Blöcke" never passes; worded "Block-Einträge" / "Block-Kopien" instead (stem should be "block|blöck"). "update" forces "Update" on a button where "Aktualisieren" is the German verb. "voice" is worded Sprachausgabe-Eintrag / Sprachausgabe-Bank for the Unit_Select sound bank.
- (g4 exemptions) ship: stratmap.draw_a_campaign_map_model_beside: "ships a .CAS" means "comes with". turn: stratmap.file_named_by_no_model_but: "turns up" means "appears". Termbase doubts: "general" stem forces Generale (plural of the person) where the mode name is "Agents and generals"; "block" stem does not match the plural Blöcke; "ticked" triggers the checkbox term (Kontrollkästchen), clumsy in counters like "3/5 ticked".
- (g6 exemptions) turn: changes.turn_off, changes.turn_on, changes.turn_off_putting_the_original_records, eng.osmmap.openstreetmap_is_off_turn_it_on, osmmap.open_settings_to_turn_it_on: "turn on/off" is einschalten/ausschalten, not a campaign Runde. port_verb: eng.mapcheck.second_port_pixel(_for_owner), eng.mapcheck.starts_with_a_and_map_regions, eng.mapcheck.the_port_pixel_at_has_no, eng.mapcheck.the_port_pixel_at_touches_no, eng.regiondel.already_has_a_port_of_its, osmmap.mylaes_layout_the_maps_layers_as: harbour noun (Hafen). ship: eng.campfiles.this_mod_ships_only_so_the: "ships" means "comes with".
- (g6 exemptions) code keywords in backticks or key names: faction/culture/castle/armour/heir/leader in eng.campstrat.* and eng.characters.has_strat_model_s_a_named; upgrade in eng.settlemech.upgrade_*; animal in eng.sidefiles.units_carry_an_undeclared_animal; faction in eng.sidefiles.line_a_symbol_sheet_before_any. level/ground: eng.mapcheck.the_river_crossing_at_is_at ("levels the ground" is a verb and terrain). character: eng.modeldb.characters_left_over_after_the_entry (letters, Zeichen). mount: home.mounted_pack. building/frame: map3d.building_the_mesh, map3d.frame_the_whole_map_again, eng.mapcheck/osmmap.the_style_above_cut_to_the (verbs or a coordinate frame).
- (g6 doubt) termbase: `record` forced Datensatz for the toolkit's change record in changes.* (reads stiffly, Aufzeichnung would be nicer); `sprite sheet` fired on "symbol sheet" (worded Sprite-Sheet); `heights map` fires on "heights" (osmmap paint confirm); `voice` = Sprachausgabe worded Sprachausgabe-Bank. "Verwender" used for plural-less "user" (areaeffects.user_count). Block plural written "Blocks" in eng.rebelpools.has_chance_0_so_these_provinces to keep the stem.
- (g4 exemptions) port_verb: minorfiles.port_ladder_line_s_in_the, minorfiles.this_culture_has_no_port_lines: harbour noun (Hafen). ship: minorfiles.where_it_starts_every_regions_religions: "this mod ships" means "comes with". Also: "tooltip" worded QuickInfo; {noun} strings worded as "Neu: {noun}" / "{count} × {noun}".
- (g7 exemptions) ship: eng.animpack.the_source_ships_no_packs_of: "ships" means "comes with". mount: packs.battle_model_entr_travel_with_them: "mounts the pack" is a verb (einbinden).
- (g7 exemptions) mount: transfer.mounted_engine: "mounted engine" is a siege engine on a mount, not a Reittier.
- (g8 exemptions) select: editor.selected: participle "ausgewählt" misses the stem auswähl. soldier: editor.soldier_replace, settings.use_the_base_units_soldier_line: the EDU keyword `soldier`, left as written. character: settings.and_more_characters_in_the_diagnostic: "characters" are letters of a string (Zeichen). building: settings.start_the_soldier_row_on_base: "building a new unit" is the verb (aufbauen). faction: stratcamp.faction_bik: a file path. Doubt: "tier" worded Ausbaustufe, so "armour tier" reads Rüstungsstufe; "standings" worded Rangliste, "blurb" Kurztext, "treasury" Schatzkammer, "purse" Kasse.
