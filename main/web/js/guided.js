/* guided.js - the guided field editor: an EDU line's positional slots, named

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================================================================
   GUIDED FIELD EDITOR
   ----------------------------------------------------------------------
   An EDU line is a comma-separated tuple whose meaning is entirely positional:
   `stat_pri 14, 4, no, 0, 0, melee, melee_blade, piercing, spear, 25, 1` is
   eleven different settings and nothing on the line says which is which. The raw
   view (what this tool showed before, and what every other EDU editor shows) asks
   you to know that by heart.

   The guided view gives each slot its own labelled box, a drop-down wherever the
   engine only accepts a fixed set of words, a one-line explanation, and a warning
   when a value would not work - while writing back the very same line, so a unit
   edited here is byte-identical to one edited by hand. Anything it does not
   recognise (a mod's own field, a repeated line, a value count the engine does
   not use) falls back to the raw box for that one field rather than guessing.

   The same code drives both places EDU fields are edited - the transfer composer
   and the unit editor - through a small host object; see gfHostComposer /
   gfHostEditor for what each supplies.
   ====================================================================== */

// Which view the two field editors open in. Guided is the default; the setting is
// remembered like the rest of them.
const gfMode=()=>((state.settings||{}).field_editor_mode==='raw'?'raw':'guided');
function gfSetMode(m){
  state.settings.field_editor_mode=m;
  api.post('/api/settings',{field_editor_mode:m});
  if(state.mode==='edit'&&state.ed)edRenderTab(); else if(state.editing)renderComposer();
}
function gfToggleHtml(){
  const g=gfMode()==='guided';
  return `<div class="gfmode" title="${ttA('guided.guided_every_value_in_its_own')}">
    <button class="${g?'on':''}" onclick="gfSetMode('guided')">${tt('guided.guided')}</button>
    <button class="${g?'':'on'}" onclick="gfSetMode('raw')">${tt('guided.raw_lines')}</button></div>`;
}

/* ---- vocabularies -------------------------------------------------------
   Fetched per mod (/api/edu_vocab): the engine's fixed sets plus everything the
   mod itself defines or already uses, so a drop-down never invites you to throw
   away a mod's own attribute or accent. The page keeps a minimal copy of the
   fixed sets so it is usable before the answer arrives. */
const GF_STATIC={
  category:['infantry','cavalry','siege','ship','handler','non_combatant'],
  'class':['light','heavy','missile','spearmen','skirmish'],
  voice_type:[tt('guided.heavy'),tt('guided.light'),tt('common.general')],
  formation_main:['square','horde'],
  formation_special:['','schiltrom','shield_wall','phalanx','testudo','wedge'],
  discipline:['low','normal','disciplined','impetuous'],
  training:['untrained','trained','highly_trained'],
  weapon_type:['no','melee','thrown','missile','siege_missile'],
  tech_type:['melee_simple','melee_blade','missile_mechanical','missile_gunpowder',
             'artillery_mechanical','artillery_gunpowder'],
  damage_type:['piercing','blunt','slashing','fire'],
  weapon_sound:['none','spear','sword','axe','mace','knife'],
  armour_sound:['flesh','leather','metal'],
  mount_class:['horse','camel','elephant'],
  weapon_attr:['ap','bp','spear','light_spear','long_pike','short_pike','spear_bonus_2',
    'spear_bonus_4','spear_bonus_6','spear_bonus_8','spear_bonus_10','spear_bonus_12',
    'thrown','launching','area','prec'],
  unit_attr:['sea_faring','can_swim','can_withdraw','can_run_amok','can_formed_charge',
    'cannot_skirmish','start_not_skirmishing','fire_by_rank','hardy','very_hardy',
    'hide_forest','hide_improved_forest','hide_long_grass','hide_anywhere','frighten_foot',
    'frighten_mounted','power_charge','knight','general_unit','mercenary_unit',
    'free_upkeep_unit','is_peasant','no_custom','gunpowder_unit','stakes','druid',
    'cantabrian_circle','command','legionary_name'],
  banner_faction:['main_infantry','main_cavalry','main_missile','main_spear'],
  banner_holy:['crusade','jihad'],
  projectile:[],mount:[],engine:[],mounted_engine:[],ship:[],animal:[],model:[],
  accent:[],banner_unit:[],fire_effect:[],defined:{}};
state.vocab={};
function gfVocabFor(mod){
  if(!mod)return GF_STATIC;
  if(state.vocab[mod])return state.vocab[mod];
  if(state.vocab['?'+mod])return GF_STATIC;      // already in flight
  state.vocab['?'+mod]=true;
  api.get('/api/edu_vocab?mod='+enc(mod)).then(v=>{
    state.vocab[mod]=Object.assign({},GF_STATIC,v||{});
    // the boxes that were drawn from the static fallback now have real lists
    if(state.mode==='edit'&&state.ed)edRenderTab(); else if(state.editing)renderAllFields(state.editing);
  }).catch(()=>{});
  return GF_STATIC;
}
const gfV=(host,name)=>((host.vocab||GF_STATIC)[name])||[];
// Names a mod file actually defines, for "this points at nothing" warnings. An
// empty list means the file is missing or unparsed - then we say nothing.
const gfDefined=(host,name)=>((host.vocab||{}).defined||{})[name]||[];
const gfHas=(list,v)=>{const t=(v||'').trim().toLowerCase();
  return !t||list.some(x=>(''+x).toLowerCase()===t);};

/* ---- the field table ----------------------------------------------------
   `parts` is the line, slot by slot. `arity` lists the value counts the engine
   accepts (absent = exactly one per part); a line with any other count is shown
   raw, because guessing which slot is missing is how an editor eats a unit.
   `pad` normalises an accepted short form up to the full part list, `join`
   writes it back in whichever form is still correct. */
const gfP=(pl,type,o)=>Object.assign({pl,type},o||{});
// one DOM id per list box, derived the same way wherever it is needed
const gfAddId=label=>'gfadd-'+label.replace(/\W/g,'_');
/* A number box carries its own limits: `min`/`max` are what the ▴▾ steppers and
   the ↑/↓ keys clamp to, `step` is how far one press moves it and `dec` how many
   decimals to keep. Only ONE of these limits is a real engine cap (attack, 63);
   the rest sit above the highest value found across vanilla, Third Age and DaC,
   so a stepper cannot run away while nothing a real mod does is out of reach.
   Typing is never clamped - an existing value the engine dislikes is reported by
   the checks, not silently rewritten under the cursor. */
const gfN=(pl,o)=>gfP(pl,'num',o);                       // number box
const gfS=(pl,v,o)=>gfP(pl,'sel',Object.assign({v},o));  // closed drop-down
const gfC=(pl,v,o)=>gfP(pl,'combo',Object.assign({v},o));// drop-down you can type into
const gfT=(pl,o)=>gfP(pl,'text',o);

// stat_pri / stat_sec / stat_ter share one shape: 11 values, or 12 when the
// optional "effect played when the weapon fires" (musket_shot_set) is present
// between the hit sound and the delay.
const gfWeaponParts=()=>[
  gfN(tt('guided.attack'),{min:0,max:63,
    help:`${tt('guided.the_weapons_attack_factor_how_much')} `
      +tt('guided.a_higher_number_is_stored_but')}),
  gfN(tt('guided.charge_bonus'),{min:0,max:63,
    help:tt('guided.extra_attack_added_while_the_charge')
      +tt('guided.hitting_a_unit_that_is_not')}),
  gfC(tt('guided.projectile'),'projectile',{w:3,
    help:`${tt('guided.the_ammunition_this_weapon_fires_an')} `
      +tt('guided.speed_arc_damage_model_and_impact')}),
  gfN(tt('guided.range'),{min:0,max:2000,
    help:tt('guided.how_far_the_missile_can_be')
      +tt('guided.artillery_near_250_450')}),
  gfN(tt('guided.ammo'),{min:0,max:999,
    help:tt('guided.shots_carried_per_man_not_per')}),
  gfS(tt('guided.weapon_type'),'weapon_type',{w:2,
    help:`${tt('guided.how_the_weapon_is_used_melee')} `
      +`${tt('guided.siege_missile_a_missile_weapon_has')} `
      +tt('guided.secondary_bow_the_exception_is_artillery')}),
  gfS(tt('guided.tech_type'),'tech_type',{w:3,
    help:`${tt('guided.which_weapon_upgrade_line_a_smith')} `
      +'<code>melee_blade</code>, <code>missile_mechanical</code>, <code>missile_gunpowder</code>, '
      +tt('guided.artillery_mechanical_or_artillery_gunpowder')}),
  gfS(tt('guided.damage_type'),'damage_type',{w:2,
    help:`${tt('guided.piercing_blunt_or_slashing_the_edus')} `
      +tt('guided.no_longer_be_read_by_the')}),
  gfS(tt('guided.hit_sound'),'weapon_sound',{w:2,
    help:`${tt('guided.the_sound_played_when_the_weapon')} `
      +tt('guided.axe_sword_or_spear_cosmetic_only')}),
  gfC(tt('guided.fire_effect'),'fire_effect',{w:3,optional:1,
    help:`${tt('guided.optional_the_effect_played_when_the')} `
      +tt('guided.units_and_essentially_nothing_else_setting')
      +tt('guided.it_turns_it_back')}),
  gfN(tt('guided.delay'),{min:0,max:9999,
    help:tt('guided.minimum_delay_between_attacks_in_tenths')
      +tt('guided.faster_25_is_the_value_nearly')}),
  gfN(tt('guided.skel_factor'),{min:0,max:100,step:0.1,dec:1,
    help:tt('guided.skeleton_compensation_factor_in_melee_the')
      +tt('guided.how_a_mismatched_animation_lands')}),
];
// A doc is a short lead line and then points. Prose that runs for six lines is
// what this editor exists to replace, so it does not get to live in the help.
// The shape is shared with every other note in the UI - see docPoints() in core.js.
const gfDoc=docPoints;

const gfWeaponSpec=(title,doc)=>({t:title,doc,parts:gfWeaponParts(),arity:[11,12],
  syn:tt('guided.attack_charge_projectile_range_ammo_weapon'),
  // 11 values -> no fire effect: open slot 9 so every box keeps its meaning
  pad:p=>p.length>=12?p:p.slice(0,9).concat([''],p.slice(9)),
  join:p=>{const fx=(p[9]||'').trim();
    return p.slice(0,9).concat(fx?[fx]:[],p.slice(10)).map(x=>(''+(x==null?'':x)).trim()).join(', ');}});
const gfExSpec=which=>({t:which+tt('guided.weapon_bonuses'),opt:1,
  syn:tt('guided.attack_bonus_vs_mounted_defence_bonus'),
  doc:gfDoc(tt('guided.optional_three_factors_that_apply_only'),[
    tt('guided.the_engine_does_read_the_line'),
    `${tt('guided.most_mods_leave_it_out_and')} `
      +tt('guided.spear_bonus_n_attributes_instead'),
    tt('guided.vanilla_ships_it_commented_out_on')]),
  parts:[gfN(tt('guided.attack_vs_mounted'),{min:-100,max:100,help:tt('guided.added_to_the_attack_factor_when')}),
    gfN(tt('guided.defence_vs_mounted'),{min:-100,max:100,help:tt('guided.added_to_defence_when_the_attacker')}),
    gfN(tt('guided.armour_penetration'),{min:-100,max:100,help:tt('guided.how_much_of_a_mounted_targets')})]});
const gfAttrSpec=which=>({t:which+tt('guided.weapon_attributes'),w:'wattr',
  doc:gfDoc(tt('guided.what_the_weapon_does_beyond_its'),[
    tt('guided.ap_halves_the_targets_armour'),
    tt('guided.bp_a_missile_passes_through_a'),
    `${tt('guided.spear_light_spear_brace_against_a')} `
      +tt('guided.from_the_front_spear_also_carries'),
    tt('guided.long_pike_required_by_phalanx_units'),
    tt('guided.spear_bonus_n_a_flat_attack'),
    tt('guided.thrown_launching_area_change_how_the'),
    tt('guided.prec_a_missile_unit_throws_one'),
    tt('guided.none_of_them_is_written_no')])});

const GF_FIELDS={
  'type':{t:tt('guided.internal_name'),syn:'<name>',
    doc:gfDoc(tt('guided.the_name_every_other_file_uses'),[
      `${tt('guided.read_by_descr_strat_txt_export')} `
        +tt('guided.descr_mercenaries_txt_descr_rebel_factions'),
      tt('guided.spaces_are_allowed'),
      tt('guided.rule_of_thumb_any_file_that')]),
    parts:[gfT('type',{grow:1,help:tt('guided.renaming_it_here_does_not_update')})]},
  'dictionary':{t:tt('guided.dictionary_key'),syn:'<key>  ; <comment>',
    doc:gfDoc(tt('guided.the_units_other_name'),[
      tt('guided.the_key_its_on_screen_text'),
      tt('guided.also_the_filename_of_its_unit'),
      tt('guided.usually_the_type_with_underscores_instead'),
      tt('guided.anything_after_a_is_a_comment')]),
    parts:[gfT('dictionary',{grow:1})]},
  'category':{t:tt('common.category'),syn:tt('guided.infantry_cavalry_siege_ship_handler'),
    doc:gfDoc(tt('guided.the_broad_troop_type_sets_defaults'),[
      tt('guided.wagons_like_the_great_cross_count'),
      tt('guided.handler_is_for_a_unit_whose'),
      tt('guided.non_combatant_is_in_the_file')]),
    parts:[gfS('category','category',{w:2})]},
  'class':{t:tt('guided.class'),syn:tt('guided.light_heavy_missile_spearmen'),
    doc:gfDoc(tt('guided.what_the_unit_is_within_its'),[
      tt('guided.light_heavy_infantry_cavalry_and_ships'),
      tt('guided.missile_infantry_cavalry_and_siege'),
      tt('guided.spearmen_infantry_only'),
      tt('guided.a_wagon_is_the_odd_one')]),
    parts:[gfS('class','class',{w:2})]},
  'voice_type':{t:tt('guided.voice_type'),syn:tt('guided.heavy_light_general'),
    doc:gfDoc(tt('guided.which_set_of_battlefield_barks_the'),[
      tt('guided.light_ships_and_weak_sounding_troops'),
      tt('guided.heavy_regulars'),
      tt('guided.general_a_generals_bodyguard'),
      `${tt('guided.with_accent_this_is_what_points')} `
        +'<code>export_descr_sounds_units_voice.txt</code>.']),
    parts:[gfS('voice_type','voice_type',{w:2})]},
  'accent':{t:tt('guided.accent'),opt:1,syn:'<accent>',
    doc:gfDoc(tt('guided.optional_forces_one_accent_on_the'),[
      tt('guided.without_the_line_it_speaks_with')
        +tt('guided.swiss_pikemen_sound_english'),
      tt('guided.accents_are_declared_in_descr_sounds'),
      tt('guided.vanilla_has_english_scottish_french_german')
        +tt('guided.arabic_and_mongolian_mods_add_their')]),
    parts:[gfC('accent','accent',{w:3})]},
  'banner faction':{t:tt('guided.faction_banner'),syn:'<banner>',
    doc:gfDoc(tt('guided.the_units_big_battlefield_banner_from'),[
      tt('guided.it_also_decides_the_mini_banners'),
      `${tt('guided.the_list_is_the_factionbanners_section')} `
        +tt('guided.mods_own_vanilla_declares_four_all'),
      tt('guided.ships_have_no_line_they_never')]),
    parts:[gfC('banner','banner_faction',{w:3})]},
  'banner holy':{t:tt('guided.holy_war_banner'),opt:1,syn:'<banner>',
    doc:gfDoc(tt('guided.optional_the_second_banner_the_unit'),[
      `${tt('guided.the_list_is_the_holybanners_section')} `
        +`${tt('guided.descr_banners_new_xml_vanilla_declares')} `
        +tt('guided.crusade_cavalry_and_a_mod_may'),
      tt('guided.leave_the_line_out_and_the')]),
    parts:[gfC('banner','banner_holy',{w:3})]},
  'banner unit':{t:tt('guided.unit_banner'),opt:1,syn:'<banner>',
    doc:gfDoc(tt('guided.optional_and_rare_a_per_unit'),[
      `${tt('guided.the_list_is_the_unitspecificbanners_section')} `
        +tt('guided.descr_banners_new_xml_the_crusading'),
      tt('guided.leave_the_line_out_and_the_2')]),
    parts:[gfC('banner','banner_unit',{w:3})]},

  'soldier':{t:tt('guided.soldiers'),syn:tt('guided.model_men_extras_mass_radius_height'),
    doc:gfDoc(tt('guided.who_the_unit_is_made_of'),[
      tt('guided.the_model_name_is_an_entry'),
      tt('guided.that_entry_decides_how_the_man'),
      tt('guided.swapping_it_swaps_the_animation_set')]),
    parts:[gfC(tt('guided.model'),'model',{w:3,
        help:`${tt('guided.a_battle_models_modeldb_entry_it')} `
          +tt('guided.animation_skeleton_so_changing_it_changes')}),
      gfN(tt('guided.men'),{min:1,max:500,
        help:tt('guided.men_in_the_unit_at_the')
          +tt('guided.gives_4_100_as_the_range')}),
      gfN(tt('guided.extras'),{min:0,max:99,
        help:tt('guided.attached_siege_engines_or_animals_2')
          +tt('guided.extras_are_comes_from_the_engine')}),
      gfN(tt('guided.mass'),{min:0,max:200,step:0.1,dec:1,
        help:tt('guided.collision_mass_of_one_man_1')
          +tt('guided.cavalry_because_a_mounted_unit_takes')}),
      gfN(tt('guided.radius'),{optional:1,min:0,max:10,step:0.05,dec:2,
        help:tt('guided.optional_collision_radius_of_one_man')
          +tt('guided.adding_it_lengthens_the_line_and')}),
      gfN(tt('common.height'),{optional:1,min:0,max:10,step:0.1,dec:1,
        help:tt('guided.optional_collision_height_of_one_man')})],
    arity:[4,5,6],
    join:p=>{const q=p.map(x=>(''+(x==null?'':x)).trim());
      while(q.length>4&&!q[q.length-1])q.pop(); return q.join(', ');}},
  'officer':{t:tt('guided.officer'),opt:1,syn:'<model>',
    doc:gfDoc(tt('guided.optional_an_extra_man_riding_along'),[
      tt('guided.taken_from_battle_models_modeldb_like'),
      tt('guided.decoration_only_losing_him_costs_the'),
      tt('guided.up_to_three_officer_lines_directly')]),
    parts:[gfC(tt('guided.model'),'model',{w:3})]},
  'mount':{t:tt('common.mount'),opt:1,syn:'<mount>',
    doc:gfDoc(tt('guided.what_the_unit_rides_named_in'),[
      tt('guided.that_block_holds_the_animals_mass'),
      tt('guided.this_line_only_points_at_it'),
      tt('guided.a_ridden_horse_or_camel_has')]),
    parts:[gfC(tt('common.mount'),'mount',{w:3})]},
  'ship':{t:tt('guided.ship'),opt:1,syn:'<ship type>',
    doc:gfDoc(tt('guided.ships_only_from_descr_ship_txt'),[
      tt('guided.heavy_warship_is_the_type_that'),
      tt('guided.the_line_goes_directly_after_soldier')]),
    parts:[gfC(tt('guided.ship'),'ship',{w:3})]},
  'engine':{t:tt('guided.siege_engine'),opt:1,syn:'<engine>',
    doc:gfDoc(tt('guided.the_siege_engine_this_crew_operates'),[
      tt('guided.catapult_trebuchet_bombard_ram_ladder_siege'),
      `${tt('guided.how_many_the_unit_fields_comes')} `
        +tt('guided.soldier_line')]),
    parts:[gfC(tt('guided.engine'),'engine',{w:3})]},
  'mounted_engine':{t:tt('guided.mounted_engine'),opt:1,syn:'<engine>',
    doc:gfDoc(tt('guided.a_gun_carried_by_the_units'),[
      tt('guided.elephant_serpentine_elephant_rocket_launcher_cam'),
      tt('guided.unlike_a_ground_engine_it_has')]),
    parts:[gfC(tt('guided.engine'),'mounted_engine',{w:3})]},
  'animal':{t:tt('guided.animals'),opt:1,syn:'<animal>',
    doc:gfDoc(tt('guided.non_ridden_animals_that_fight_while')
      +'<code>descr_animals.txt</code>.',[
      tt('guided.war_dogs_pigs'),
      tt('guided.needs_category_handler_or_the_animals'),
      tt('guided.how_many_comes_from_the_extras')]),
    parts:[gfC(tt('guided.animal'),'animal',{w:3})]},
  'mount_effect':{t:tt('guided.bonus_vs_mounts'),opt:1,w:'meffect',
    syn:'<mount> ±N, <mount> ±N, <mount> ±N',
    doc:gfDoc(tt('guided.attack_modifiers_that_apply_only_against'),[
      tt('guided.each_entry_is_a_name_and'),
      `${tt('guided.the_name_is_a_mount_class')} `
        +tt('guided.elephant_or_one_specific_mount_from'),
      `<b>${tt('guided.the_engine_reads_at_most_three')}</b>`,
      tt('guided.this_is_where_camels_frighten_horses')])},
  'attributes':{t:tt('guided.attributes'),w:'attrs',syn:tt('guided.attr_attr_attr'),
    doc:gfDoc(tt('guided.everything_about_the_unit_that_is'),[
      `${tt('guided.abilities_where_it_can_hide_whether')} `
        +tt('guided.it_can_withdraw_its_stamina_whether')
        +tt('guided.stakes_or_form_a_cantabrian_circle'),
      tt('guided.a_unit_may_only_carry_one'),
      `${tt('guided.ai_labels_pike_crossbow_artillery')} `
        +tt('guided.gunmen_change_nothing_about_the_unit'),
      tt('guided.they_only_tell_the_campaign_ai')])},
  'move_speed_mod':{t:tt('guided.movement_modifier'),opt:1,syn:'<multiplier>',
    doc:gfDoc(tt('guided.kingdoms_only_multiplies_the_speed_the'),[
      tt('guided.above_1_is_faster_below_is'),
      tt('guided.without_the_line_the_skeleton_alone')]),
    parts:[gfN('×',{min:0,max:5,step:0.01,dec:2,help:tt('guided.1_leaves_the_skeletons_own_speed')})]},

  'formation':{t:tt('guided.formation'),syn:tt('guided.close_close_loose_loose_ranks_formation'),
    doc:gfDoc(tt('guided.how_tightly_the_men_stand_and'),[
      tt('guided.the_first_four_numbers_are_spacing'),
      tt('guided.side_to_side_then_front_to')]),
    parts:[gfN(tt('guided.close'),{min:0,max:200,step:0.1,dec:1,help:tt('guided.side_to_side_spacing_between_men')}),
      gfN(tt('guided.close_2'),{min:0,max:200,step:0.1,dec:1,help:tt('guided.front_to_back_spacing_between_ranks')}),
      gfN(tt('guided.loose'),{min:0,max:200,step:0.1,dec:1,help:tt('guided.side_to_side_spacing_in_loose')}),
      gfN(tt('guided.loose_2'),{min:0,max:200,step:0.1,dec:1,help:tt('guided.front_to_back_spacing_in_loose')}),
      gfN(tt('guided.ranks'),{min:1,max:50,help:tt('guided.how_many_ranks_deep_the_unit')}),
      gfS(tt('guided.formation'),'formation_main',{w:2,
        help:`${tt('guided.the_formation_the_unit_starts_in')} `
          +tt('guided.square_or_horde_a_circle')}),
      gfS(tt('guided.can_switch_to'),'formation_special',{w:2,optional:1,
        help:`${tt('guided.optional_the_formation_the_unit_can')} `
          +`${tt('guided.long_pike_on_the_primary_weapon')} `
          +tt('guided.testudo_or_wedge')})],
    arity:[6,7],
    join:p=>{const q=p.map(x=>(''+(x==null?'':x)).trim());
      // drop the empty 7th slot unless the file's own line carried it as a
      // trailing comma, which one real unit in Third Age Reforged does
      if(!q[6]&&p.gfSrcLen!==7)q.length=6; return q.join(', ');}},
  'stat_health':{t:tt('guided.hit_points'),syn:tt('guided.man_mount_animal'),
    doc:gfDoc(tt('guided.how_many_killing_blows_it_takes'),[
      tt('guided.almost_every_unit_in_the_game'),
      tt('guided.ridden_horses_and_camels_have_no'),
      tt('guided.the_second_box_is_for_elephants')]),
    parts:[gfN(tt('guided.man'),{min:0,max:999,help:tt('guided.killing_blows_one_man_absorbs_1')}),
      gfN(tt('guided.mount_animal'),{min:0,max:999,
        help:tt('guided.hit_points_of_the_mount_or')})]},
  'stat_stl':{t:tt('guided.soldiers_to_stay_alive'),opt:1,syn:'<men>',
    doc:gfDoc(tt('guided.optional_how_many_men_the_unit'),[
      'Only a handful of units in any mod set it.']),
    parts:[gfN(tt('guided.men'),{min:0,max:999})]},

  'stat_pri':gfWeaponSpec(tt('guided.primary_weapon'),
    gfDoc(tt('guided.the_weapon_the_unit_leads_with'),[
      tt('guided.a_missile_weapon_has_to_be'),
      tt('guided.artillery_is_the_exception_the_crews')
        +tt('guided.shot_is_the_secondary_line')])),
  'stat_pri_ex':gfExSpec(tt('guided.primary')),
  'stat_pri_attr':gfAttrSpec(tt('guided.primary')),
  'stat_sec':gfWeaponSpec(tt('guided.secondary_weapon'),
    gfDoc(tt('guided.the_sidearm'),[
      tt('guided.on_a_mounted_vehicle_or_artillery'),
      tt('guided.a_missile_units_melee_weapon_belongs'),
      `${tt('guided.no_sidearm_is_one_exact_line')} `
        +tt('guided.none_25_1_the_button_in')])),
  'stat_sec_ex':gfExSpec(tt('guided.secondary')),
  'stat_sec_attr':gfAttrSpec(tt('guided.secondary')),
  'stat_ter':gfWeaponSpec(tt('guided.third_weapon'),
    gfDoc(tt('guided.optional_third_weapon_read_exactly_like'),[
      tt('guided.vanilla_uses_it_once_the_trebuchets'),
      tt('guided.either_all_of_the_ternary_lines')])),
  'stat_ter_ex':gfExSpec(tt('guided.third')),
  'stat_ter_attr':gfAttrSpec(tt('guided.third')),

  'stat_pri_armour':{t:tt('guided.defence'),syn:tt('guided.armour_defence_skill_shield_hit_sound'),
    doc:gfDoc(tt('guided.what_protects_the_man_split_three'),[
      tt('guided.armour_counts_against_everything'),
      tt('guided.defence_skill_is_his_parrying_and'),
      tt('guided.shield_only_counts_against_attacks_from')]),
    parts:[gfN(tt('guided.armour'),{min:0,max:255,help:tt('guided.armour_factor_counts_against_every_kind')}),
      gfN(tt('guided.defence_skill'),{min:0,max:255,help:tt('guided.parrying_skill_it_is_ignored_when')}),
      gfN(tt('guided.shield'),{min:0,max:255,help:tt('guided.shield_factor_only_applies_to_attacks')}),
      gfS(tt('guided.hit_sound'),'armour_sound',{w:2,help:tt('guided.what_it_sounds_like_when_the')})]},
  'stat_armour_ex':{t:tt('guided.defence_extended'),opt:1,
    syn:tt('guided.armour_0_armour_1_armour_2'),
    doc:gfDoc(tt('guided.optional_long_form_of_the_line'),[
      tt('guided.gives_armour_its_own_value_at')
        +tt('guided.levels_instead_of_letting_the_engine'),
      tt('guided.splits_the_shield_into_one_value'),
      tt('guided.vanilla_ships_it_commented_out')]),
    parts:[gfN(tt('guided.armour_0'),{min:0,max:255,help:tt('guided.armour_with_no_smith_upgrade')}),
      gfN(tt('guided.armour_1'),{min:0,max:255,help:tt('guided.armour_at_the_first_upgrade_level')}),
      gfN(tt('guided.armour_2'),{min:0,max:255,help:tt('guided.armour_at_the_second_upgrade_level')}),
      gfN(tt('guided.armour_3'),{min:0,max:255,help:tt('guided.armour_at_the_third_upgrade_level')}),
      gfN(tt('guided.defence_skill'),{min:0,max:255,help:tt('guided.as_in_the_normal_line_it')}),
      gfN(tt('guided.shield_melee'),{min:0,max:255,help:tt('guided.shield_factor_against_melee_attacks_from')}),
      gfN(tt('guided.shield_missile'),{min:0,max:255,help:tt('guided.shield_factor_against_missile_fire_this')}),
      gfS(tt('guided.hit_sound'),'armour_sound',{w:2})]},
  'stat_sec_armour':{t:tt('guided.vehicle_animal_defence'),syn:tt('guided.armour_defence_skill_hit_sound'),
    doc:gfDoc(tt('guided.the_defence_of_the_attached_artillery'),[
      tt('guided.there_is_no_shield_slot_here'),
      tt('guided.a_ridden_horse_has_no_separate')
        +'<code>0, 0, flesh</code>.']),
    parts:[gfN(tt('guided.armour'),{min:0,max:255,help:tt('guided.armour_of_the_vehicle_or_animal')}),
      gfN(tt('guided.defence_skill'),{min:0,max:255,help:tt('guided.defence_skill_of_the_vehicle_or')}),
      gfS(tt('guided.hit_sound'),'armour_sound',{w:2})]},
  'stat_mental':{t:tt('guided.morale'),syn:tt('guided.morale_discipline_training_lock_morale'),
    doc:gfDoc(tt('guided.the_units_state_of_mind'),[
      tt('guided.morale_how_much_punishment_it_takes'),
      `${tt('guided.discipline_how_well_it_answers_a')} `
        +tt('guided.or_the_general_dying'),
      tt('guided.training_how_tidily_it_holds_its')]),
    parts:[gfN(tt('guided.morale'),{min:0,max:100,help:tt('guided.base_morale_higher_units_stand_longer')}),
      gfS(tt('guided.discipline'),'discipline',{w:2,
        help:`${tt('guided.low_normal_disciplined_or_impetuous')} `
          +tt('guided.impetuous_units_may_charge_without_being')}),
      gfS(tt('guided.training'),'training',{w:2,
        help:`${tt('guided.untrained_trained_or_highly_trained_how')} `
          +tt('guided.keeps_its_formation_while_it_moves')}),
      gfP(tt('guided.never_routs'),'flag',{on:'lock_morale',
        help:tt('guided.adds_lock_morale_an_optional_fourth')})],
    arity:[3,4],
    join:p=>{const q=p.slice(0,3).map(x=>(''+(x==null?'':x)).trim());
      // the 4th token goes back exactly as the file wrote it: Third Age Reforged
      // spells one `locked`, which does nothing, and turning that into
      // `lock_morale` on save would quietly make the unit unroutable
      const f=(''+(p[3]==null?'':p[3])).trim();
      if(f)q.push(f==='1'?'lock_morale':f); return q.join(', ');}},
  'stat_heat':{t:tt('guided.heat_fatigue'),syn:'<extra fatigue>',
    doc:gfDoc(tt('guided.extra_fatigue_in_hot_climates_on'),[
      tt('guided.higher_tires_sooner_in_the_desert'),
      tt('guided.heavily_armoured_units_carry_the_most')]),
    parts:[gfN(tt('guided.heat'),{min:-100,max:100})]},
  'stat_ground':{t:tt('guided.ground_modifiers'),syn:tt('guided.scrub_sand_forest_snow'),
    doc:gfDoc(tt('guided.combat_modifiers_per_ground_type_wherever'),[
      tt('guided.negative_is_a_penalty'),
      tt('guided.a_desert_unit_has_a_positive')]),
    parts:[gfN(tt('guided.scrub'),{min:-100,max:100,help:tt('guided.modifier_while_fighting_on_scrub')}),
      gfN(tt('guided.sand'),{min:-100,max:100,help:tt('guided.modifier_on_sand_positive_for_desert')}),
      gfN(tt('guided.forest'),{min:-100,max:100,help:tt('guided.modifier_in_forest_positive_for_woodsmen')}),
      gfN(tt('guided.snow'),{min:-100,max:100,help:tt('guided.modifier_in_snow_positive_for_northern')})]},
  'stat_charge_dist':{t:tt('guided.charge_distance'),syn:'<metres>',
    doc:gfDoc(tt('guided.how_far_out_from_the_enemy'),[
      tt('guided.bigger_means_it_starts_running_sooner'),
      tt('guided.that_builds_more_charge_but_also')]),
    parts:[gfN(tt('guided.metres'),{min:0,max:999})]},
  'stat_fire_delay':{t:tt('guided.fire_delay'),opt:1,syn:'<delay>',
    doc:gfDoc(tt('guided.extra_delay_between_volleys_on_top'),[
      tt('guided.modders_report_it_has_no_effect'),
      tt('guided.nearly_every_unit_carries_0')]),
    parts:[gfN(tt('guided.delay'),{min:0,max:999})]},
  'stat_food':{t:tt('guided.food'),opt:1,syn:'<a>, <b>',
    doc:gfDoc(tt('guided.no_longer_used_by_the_engine'),[
      tt('guided.every_unit_in_the_game_carries'),
      tt('guided.no_reason_to_change_it_no')]),
    parts:[gfN(tt('guided.value_1'),{min:0,max:9999}),gfN(tt('guided.value_2'),{min:0,max:9999})]},
  'stat_cost':{t:tt('common.cost'),syn:tt('guided.turns_recruit_upkeep_weapon_ug_armour'),
    doc:gfDoc(tt('guided.everything_the_unit_costs'),[
      tt('guided.the_first_box_is_turns'),
      tt('guided.every_other_box_is_florins')]),
    parts:[gfN(tt('guided.turns'),{min:0,max:99,help:tt('guided.turns_the_unit_takes_to_recruit')}),
      gfN(tt('guided.recruit'),{min:0,max:999999,help:tt('guided.florins_to_recruit_it_in_the')}),
      gfN(tt('guided.upkeep'),{min:0,max:999999,help:tt('guided.florins_per_turn_to_keep_it')}),
      gfN(tt('guided.weapon_ug'),{min:0,max:999999,help:tt('guided.florins_the_smith_charges_to_upgrade')}),
      gfN(tt('guided.armour_ug'),{min:0,max:999999,help:tt('guided.florins_the_smith_charges_to_upgrade_2')}),
      gfN(tt('guided.custom_battle'),{min:0,max:999999,help:tt('guided.what_it_costs_in_a_custom')}),
      gfN(tt('guided.free_picks'),{min:0,max:99,help:tt('guided.how_many_you_may_buy_in')}),
      gfN(tt('guided.price_rise'),{min:0,max:999999,help:tt('guided.how_much_the_custom_battle_price')})]},
  'recruit_priority_offset':{t:tt('guided.ai_recruit_priority'),opt:1,syn:'<offset>',
    doc:gfDoc(tt('guided.kingdoms_only_how_badly_the_ai'),[
      tt('guided.higher_means_it_recruits_it_more'),
      tt('guided.negative_pushes_it_down_the_list'),
      tt('guided.it_goes_at_the_end_of')]),
    parts:[gfN(tt('guided.offset'),{min:-1000,max:1000})]},
  'crusading_upkeep_modifier':{t:tt('guided.crusade_upkeep'),opt:1,syn:'<multiplier>',
    doc:gfDoc(tt('guided.multiplies_the_units_upkeep_while_it'),[
      'Vanilla uses 0.5 (half price) on the units it wants you to take along.']),
    parts:[gfN('×',{min:0,max:10,step:0.1,dec:2})]},
  'armour_ug_levels':{t:tt('guided.armour_upgrade_levels'),w:'uglevels',syn:tt('guided.level_level_level'),
    doc:gfDoc(tt('guided.the_smith_level_each_armour_tier')
      +tt('guided.the_models_below'),[
      tt('guided.the_first_value_is_the_units'),
      tt('guided.the_list_has_to_stay_ascending'),
      tt('guided.more_levels_than_models_is_normal')])},
  'armour_ug_models':{t:tt('guided.armour_upgrade_models'),w:'ugmodels',syn:tt('guided.model_model_model'),
    doc:gfDoc(tt('guided.one_battle_models_modeldb_entry_per'),[
      tt('guided.position_0_is_the_units_normal'),
      tt('guided.naming_the_same_entry_twice_is')
        +tt('guided.armour_upgrade_in_its_stats_without'),
      `${tt('guided.these_entries_do_not_decide_how')} `
        +tt('guided.soldier_line_does')])},
  'ownership':{t:tt('guided.ownership'),w:'factions',syn:tt('guided.faction_faction_culture'),
    doc:gfDoc(tt('guided.the_factions_and_cultures_allowed_to'),[
      `${tt('guided.not_optional_book_keeping_a_faction')} `
        +tt('guided.recruit_it_unless_it_is_listed'),
      tt('guided.it_also_decides_which_faction_folders')])},
  'era 0':{t:tt('guided.custom_battle_early'),w:'factions',opt:1,syn:tt('guided.faction_faction'),
    doc:gfDoc(tt('guided.optional_which_factions_may_pick_this'),[
      tt('guided.nothing_to_do_with_the_campaign'),
      tt('guided.the_campaign_is_ownership_plus_the')])},
  'era 1':{t:tt('guided.custom_battle_high'),w:'factions',opt:1,syn:tt('guided.faction_faction'),
    doc:tt('guided.optional_which_factions_may_pick_this_2')},
  'era 2':{t:tt('guided.custom_battle_late'),w:'factions',opt:1,syn:tt('guided.faction_faction'),
    doc:tt('guided.optional_which_factions_may_pick_this_3')},
  'card_pic_dir':{t:tt('guided.unit_card_folder'),opt:1,syn:'<folder>',
    doc:gfDoc(tt('guided.optional_pins_the_unit_card_to'),[
      tt('guided.without_it_the_game_looks_the'),
      tt('guided.useful_for_a_mercenary_or_a'),
      tt('guided.a_trap_otherwise_it_overrides_every')]),
    parts:[gfT(tt('guided.folder'),{grow:1,mono:1})]},
  'info_pic_dir':{t:tt('guided.info_card_folder'),opt:1,syn:'<folder>',
    doc:tt('guided.optional_the_same_thing_for_the'),
    parts:[gfT(tt('guided.folder'),{grow:1,mono:1})]},
  'unit_info':{t:tt('guided.info_panel_numbers'),opt:1,syn:tt('guided.melee_attack_missile_attack_defence'),
    doc:gfDoc(tt('guided.optional_the_three_summary_numbers_the'),[
      tt('guided.vanilla_keeps_this_line_commented_out'),
      tt('guided.left_out_the_engine_works_them')]),
    parts:[gfN(tt('guided.melee_attack'),{min:0,max:999}),gfN(tt('guided.missile_attack'),{min:0,max:999}),gfN(tt('guided.defence'),{min:0,max:999})]},
};

const GF_SECTIONS=[
  {id:'basics',t:tt('guided.basics'),keys:['type','dictionary','category','class','voice_type','accent',
    tt('guided.banner_faction'),tt('guided.banner_holy'),tt('guided.banner_unit')]},
  {id:'men',t:tt('guided.men_mounts'),keys:['soldier','officer','mount','ship','engine','mounted_engine',
    'animal','stat_health','stat_stl','move_speed_mod','armour_ug_levels','armour_ug_models']},
  /* Abilities used to be a group of its own, holding two lines: `attributes` and
     `mount_effect`. Two cards is not a tab - it sat there half empty while the
     Weapons tab beside it carried nine - and the two are read together anyway,
     because what a unit can DO and what it does it WITH are the same question.
     They lead the group: `attributes` is the widest-reaching line on the unit
     and belongs at the top of whatever tab it is on. */
  {id:'weapons',t:tt('guided.weapons_abilities'),
   keys:['attributes','mount_effect','stat_pri','stat_pri_attr','stat_pri_ex',
    'stat_sec','stat_sec_attr','stat_sec_ex','stat_ter','stat_ter_attr','stat_ter_ex']},
  {id:'defence',t:tt('guided.defence_morale'),keys:['stat_pri_armour','stat_armour_ex','stat_sec_armour',
    'stat_mental','formation','stat_charge_dist','stat_fire_delay','stat_heat','stat_ground']},
  {id:'cost',t:tt('guided.recruitment'),keys:['stat_cost','recruit_priority_offset','crusading_upkeep_modifier',
    'ownership',tt('guided.era_0'),tt('guided.era_1'),tt('guided.era_2')]},
  {id:'ui',t:tt('guided.cards_misc'),keys:['card_pic_dir','info_pic_dir','unit_info','stat_food']},
  {id:'other',t:tt('guided.other_lines'),keys:[]},
];
const GF_SECTION_OF=(()=>{const m={};GF_SECTIONS.forEach(s=>s.keys.forEach(k=>m[k]=s.id));return m;})();
const gfKey=label=>label.replace(/#\d+$/,'');

/* ---- lines that read as one thought share a row --------------------------
   A card per EDU line is right for `stat_pri`, which is eleven settings. It is
   wrong for `banner faction`, which is one drop-down: a full-width card for it
   pushes the next one off the screen, and a guided unit is forty cards long.

   These groups sit side by side instead. A group is emitted where its FIRST
   member appears, in the group's own order rather than the file's - the pairs
   below are next to each other in a normal EDU, but a mod that has moved a line
   should not lose the pairing over it. Repeats come along: `officer`,
   `officer#2` and `officer#3` are one key and land on one row. */
const GF_PAIRS=[
  ['type','dictionary'],
  ['category','class','voice_type','accent'],
  [tt('guided.banner_faction'),tt('guided.banner_holy')],
  ['officer'],
  ['move_speed_mod','stat_health'],
  ['stat_heat','stat_ground'],
  ['stat_charge_dist','stat_fire_delay'],
];
const GF_PAIR_OF=(()=>{const m={};
  GF_PAIRS.forEach((g,i)=>g.forEach(k=>m[k]=i));return m;})();
// The cards of one section, with the paired ones wrapped in a row of their own.
function gfRows(host,shown,warns){
  const used=new Set(),out=[];
  shown.forEach(l=>{
    if(used.has(l))return;
    const g=GF_PAIR_OF[gfKey(l)];
    if(g==null){out.push(gfCard(host,l,warns)); return;}
    const run=[];
    GF_PAIRS[g].forEach(k=>shown.forEach(x=>{
      if(gfKey(x)===k&&!used.has(x)){run.push(x); used.add(x);}}));
    out.push(run.length>1
      ? `<div class="gfpair" style="--gfn:${run.length}">${
          run.map(x=>gfCard(host,x,warns)).join('')}</div>`
      : gfCard(host,run[0],warns));
  });
  return out.join('');
}

/* ---- splitting a line into its slots, and putting it back together ---- */
function gfParse(spec,val){
  const raw=(val==null?'':''+val);
  const n=(spec.parts||[]).length;
  if(!n)return {parts:[],ok:true};
  if(!raw.trim())return {parts:new Array(n).fill(''),ok:true,empty:true};
  let p=raw.split(',').map(s=>s.trim());
  const allow=spec.arity||[n];
  if(allow.indexOf(p.length)<0)return {parts:p,ok:false};
  const srcLen=p.length;   // BEFORE pad: how many fields the file's own line had
  if(spec.pad)p=spec.pad(p);
  while(p.length<n)p.push('');
  // A trailing comma is a field, and an optional field the file left empty is
  // NOT the same as a field the file does not have. `join` needs to tell them
  // apart to give the line back byte for byte; a named property on the array
  // rides along through every caller (they all mutate p.parts in place) and is
  // invisible to map/join/JSON. Absent = built fresh from the GUI, so normalise.
  p.gfSrcLen=srcLen;
  return {parts:p,ok:true};
}
function gfBuild(spec,parts){
  if(spec.join)return spec.join(parts);
  return parts.map(x=>(''+(x==null?'':x)).trim()).join(', ');
}

/* ---- host adapters ------------------------------------------------------
   The unit editor and the transfer composer keep their edits in different
   places (`state.ed.ov` + a removal set vs a per-unit `field_overrides`), have
   different extras (a real delete vs the base-unit B switches) and read
   different mods. Everything the renderer needs comes through here. */
function gfHostEditor(){
  const e=state.ed;
  return {
    id:'ed', key:tt('guided.ed')+e.mod+':'+e.unit, mod:e.mod,
    vocab:gfVocabFor(e.mod),
    fields:()=>e.d.fields,
    known:new Set(e.d.known_fields||[]),
    get:edFieldVal,
    orig:l=>{const f=e.d.fields.find(x=>x[0]===l);return f?f[1]:'';},
    set:(l,v)=>edSetField(l,v),
    changed:l=>(l in e.ov)&&e.ov[l]!==((e.d.fields.find(x=>x[0]===l)||['',''])[1]),
    removed:l=>e.rm.has(l),
    canRemove:true,
    protectedKeys:new Set(['type','dictionary','soldier']),
    toggleRemove:l=>{if(e.rm.has(l))e.rm.delete(l);else{e.rm.add(l);delete e.ov[l];}edRenderTab();},
    badge:()=>'',
    lock:()=>null,
    factions:()=>edFactionList(),
    facLabel:edFacLabel,
    missing:()=>{const present=new Set(e.d.fields.map(([l])=>gfKey(l)));
      return (e.d.known_fields||[]).filter(k=>!present.has(k));},
    add:k=>{e.d.fields=e.d.fields.concat([[k,'']]);e.added.add(k);e.ov[k]='';edRenderTab();},
    addLabel:(k,l)=>{e.d.fields=e.d.fields.concat([[l,'']]);e.added.add(l);e.ov[l]='';edRenderTab();},
    richArmour:true,          // the editor's ＋ tier menu and ✎ jump-to-model
    // The entries this save is about to WRITE. The editor creates modeldb
    // entries too - the Battle models tab's "＋ New entry from this" and the
    // armour-tier menu both stage one - and without them here a line pointed at
    // a staged entry was flagged "not an entry in this mod's
    // battle_models.modeldb": true of the mod as it stands, false of the mod
    // this same save leaves behind.
    creates:()=>(e.newModels||[]).map(n=>n.name),
    rerender:()=>edRenderTab(),
    count:()=>edCount(),
    stale:()=>edStale(),
  };
}
function gfHostComposer(){
  const c=cfgFor(state.editing);
  const inh=new Set(c.base_type?(c._inherited||[]):[]);
  const lockFor=gfComposerLock(c);
  return {
    id:'cm', key:tt('guided.cm')+state.dst+':'+state.editing, mod:state.dst,
    vocab:gfVocabFor(state.dst),
    fields:()=>gfComposerFields(c),
    known:new Set(Object.keys(GF_FIELDS)),
    get:l=>{const lk=lockFor(gfKey(l)); if(lk)return lk.val;
      return (l in c.field_overrides)?c.field_overrides[l]:c._orig[l];},
    orig:l=>c._orig[l],
    set:(l,v)=>{if(v!==c._orig[l])c.field_overrides[l]=v; else delete c.field_overrides[l];},
    changed:l=>(l in c.field_overrides)&&c.field_overrides[l]!==c._orig[l],
    removed:()=>false,
    canRemove:false,
    protectedKeys:new Set(),
    toggleRemove:()=>{},
    badge:(l,cur)=>inh.has(gfKey(l))&&!/#\d+$/.test(l)?baseBadge(c,l,cur):'',
    lock:l=>/#\d+$/.test(l)?null:lockFor(gfKey(l)),
    factions:()=>gfComposerFactions(c),
    facLabel:facLabel,
    missing:()=>{const present=new Set(gfComposerFields(c).map(([l])=>gfKey(l)));
      return (state.ed&&state.ed.d.known_fields||Object.keys(GF_FIELDS)).filter(k=>!present.has(k));},
    add:k=>{c._fields=c._fields.concat([[k,'']]);c.field_overrides[k]='';renderAllFields(state.editing);},
    addLabel:(k,l)=>{c._fields=c._fields.concat([[l,'']]);c.field_overrides[l]='';renderAllFields(state.editing);},
    richArmour:false,
    creates:()=>gfComposerCreates(),
    rerender:()=>renderAllFields(state.editing),
    count:()=>updateFieldChanged(),
    stale:()=>{},
  };
}
// Same two locks the raw view applies: a copied voice owns accent + voice_type,
// and replacing a unit keeps the replaced unit's type + dictionary.
function gfComposerLock(c){
  const snd=soundDonor(c);
  const sndLock=snd.accent?{vals:{accent:snd.accent,voice_type:snd.cls},
    why:tt('guided.locked_by_the_voice_panel_s',{name:snd.name,accent:snd.accent,cls:snd.cls})
       +tt('guided.and_these_two_fields_are_what')}:null;
  const rb=baseUnitOf(c);
  const idLock=(isReplace(c)&&rb)?{vals:{type:rb.type,dictionary:rb.dictionary},
    why:tt('guided.locked_this_transfer_rewrites_in_place',{type:rb.type})}:null;
  return key=>(idLock&&(key in idLock.vals))?{val:idLock.vals[key],why:idLock.why}
             :(sndLock&&(key in sndLock.vals))?{val:sndLock.vals[key],why:sndLock.why}:null;
}
function gfComposerFields(c){
  const snd=soundDonor(c);
  let fields=c._fields||[];
  if(snd.accent){        // a copied voice ADDS these two lines if the unit lacks them
    fields=fields.slice();
    for(const k of ['voice_type','accent']){
      if(fields.some(([l])=>l===k))continue;
      const after=fields.findIndex(([l])=>l==='voice_type'||l==='class');
      fields.splice(after<0?0:after+1,0,[k,k==='accent'?snd.accent:snd.cls]);
    }
  }
  return fields;
}
/* The modeldb entries this transfer is about to CREATE in the destination.
   `/api/edu_vocab` lists what the destination has today, so without this every
   new unit's own soldier and armour-upgrade models were flagged "not an entry in
   this mod's battle_models.modeldb" - true of the mod as it stands, false of the
   mod the moment the transfer lands, and it is the same job that writes both. */
function gfComposerCreates(){
  const u=(state.data&&state.data.units||[]).find(x=>x.type===state.editing);
  if(!u)return [];
  // model_names() already covers soldier + officers + armour_ug_models
  return (u.models||[]).concat(u.mount?[u.mount]:[]).filter(Boolean);
}
// The composer has no per-unit faction list of its own: use the destination mod's,
// widened by whatever the unit's own ownership/era lines already name.
function gfComposerFactions(c){
  const all=Object.keys(state.factionNames||{}).slice();
  (state.destData&&state.destData.factions||[]).forEach(f=>all.push(f.name||f));
  ['ownership',tt('guided.era_0'),tt('guided.era_1'),tt('guided.era_2')].forEach(l=>{
    const v=(l in c.field_overrides)?c.field_overrides[l]:c._orig[l];
    csv(v||'').forEach(f=>all.push(f));
  });
  const seen=new Set();
  return all.filter(f=>f&&!seen.has(f)&&seen.add(f)).sort((a,b)=>facLabel(a).localeCompare(facLabel(b)));
}

/* ---- per-dialog view state (which section, the search box, which cards have
        their raw line or help opened) ---- */
function gfState(host){
  if(!state.gf||state.gf.key!==host.key)
    state.gf={key:host.key,tab:'basics',q:'',raw:new Set(),help:new Set()};
  return state.gf;
}

/* ---- warnings ------------------------------------------------------------
   Things the engine will not do, or will do differently from what the numbers
   suggest. They never block a save - a mod may know better - but the point of a
   guided editor is that you find out here rather than at the loading screen. */
function gfWarnings(host){
  const out={},add=(l,h,k)=>{(out[l]||(out[l]=[])).push({h,k:k||'warn'});};
  const val=l=>host.get(l)||'';
  const has=l=>host.fields().some(([x])=>x===l)&&!host.removed(l);
  const parts=l=>val(l).split(',').map(s=>s.trim());
  const num=x=>{const n=parseFloat(x);return isNaN(n)?null:n;};

  const cat=(val('category')||'').toLowerCase();
  const cls=(val('class')||'').toLowerCase();
  if(has('class')&&cat==='infantry'&&cls==='spearmen'){/* fine */}
  if(has('class')&&cat!=='infantry'&&cls==='spearmen')
    add('class',`${tt('guided.spearmen_is_an_infantry_class_so')} `+esc(cat)+tt('guided.unit_the_engine_falls_back_to'));
  if(has('animal')&&cat!=='handler')
    add('animal',tt('guided.an_animal_line_needs_category_handler'));
  // a unit carries ONE kind of attachment; the engine reads whichever it finds
  // first and the others are dead weight
  const extras=['ship','engine','mounted_engine','animal'].filter(has);
  if(extras.length>1)extras.forEach(k=>add(k,
    `${tt('guided.a_unit_can_only_use_one')} `
    +tt('guided.animal_this_one_has')+extras.join('</b>, <b>')+'</b>.','bad'));

  ['stat_pri','stat_sec','stat_ter'].forEach(k=>{
    if(!has(k))return;
    const p=parts(k); if(p.length<11)return;
    const atk=num(p[0]),proj=(p[2]||'').toLowerCase(),rng=num(p[3]),ammo=num(p[4]),wt=(p[5]||'').toLowerCase();
    if(atk!==null&&atk>63)add(k,`${tt('guided.attack')} <b>`+esc(p[0])+`</b> ${tt('guided.is_above_the_engines_cap_of')}`);
    const missile=(wt==='missile'||wt==='thrown'||wt==='siege_missile');
    if(missile&&proj==='no')add(k,`${tt('guided.weapon_type_is')} <b>`+esc(wt)+`</b> ${tt('guided.but_the_projectile_is_no_so')}`);
    if(!missile&&proj!=='no'&&proj)add(k,`${tt('guided.a_projectile_is_set_but_the')} <b>`+esc(wt||'none')+`</b>${tt('guided.only_missile_thrown_and_siege_missile')}`);
    if(missile&&!rng)add(k,tt('guided.missile_weapon_with_range_0_so'));
    if(missile&&!ammo)add(k,tt('guided.missile_weapon_with_0_ammunition_so'));
    if(proj&&proj!=='no'&&!gfHas(gfDefined(host,'projectile'),p[2])&&gfDefined(host,'projectile').length)
      add(k,`${tt('guided.projectile')} <code>`+esc(p[2])+`</code> ${tt('guided.is_not_defined_in_this_mods')}`,'bad');
    if(p.length>=12&&(p[9]||'').trim()&&!/^[A-Za-z_][\w]*$/.test(p[9].trim()))
      add(k,`${tt('guided.the_12_value_form_puts_the')} <code>`+esc(p[9])+`</code> ${tt('guided.does_not_look_like_an_effect')}`);
  });
  if(has('stat_pri')&&has('stat_sec')){
    const w=x=>((parts(x)[5])||'').toLowerCase();
    const missileSec=['missile','thrown'].indexOf(w('stat_sec'))>=0;
    if(missileSec&&['missile','thrown','siege_missile'].indexOf(w('stat_pri'))<0)
      add('stat_sec',tt('guided.a_missile_weapon_has_to_be_2'));
  }
  if(has('stat_ter')!==has('stat_ter_attr'))
    add(has('stat_ter')?'stat_ter':'stat_ter_attr',tt('guided.a_third_weapon_needs_all_of'));

  if(has('formation')){
    const p=parts('formation');
    if(p.length>=7){
      const a=(p[5]||'').toLowerCase(),b=(p[6]||'').toLowerCase();
      if(b&&['square','horde'].indexOf(a)<0)
        add('formation',tt('guided.with_two_formations_the_first_must'));
      if(b&&['schiltrom','shield_wall','phalanx','testudo','wedge'].indexOf(b)<0)
        add('formation','<b>'+esc(b)+`</b> ${tt('guided.is_not_one_of_the_switchable')}`);
      if(b==='phalanx'&&csv(val('stat_pri_attr')).indexOf('long_pike')<0)
        add('formation',tt('guided.a_phalanx_unit_normally_needs_long'));
    }
  }
  const lv=csv(val('armour_ug_levels')),md=csv(val('armour_ug_models'));
  if(has('armour_ug_models')&&lv.length&&md.length&&md.length>lv.length)
    add('armour_ug_models',`<b>${md.length}</b> ${tt('guided.upgrade_model_s_but_only_level',{lv_n:lv.length})} `
      +tt('guided.the_tiers_past_the_last_level'));
  else if(has('armour_ug_models')&&lv.length&&md.length&&lv.length>md.length)
    add('armour_ug_models',`<b>${lv.length}</b> ${tt('guided.armour_levels_share_model_s_so',{md_n:md.length})} `
      +tt('guided.model_carries_the_levels_above_it'),'info');
  const defModels=gfDefined(host,'model');
  // plus whatever this job is about to write into the modeldb - see host.creates
  const coming=new Set((host.creates?host.creates():[]).map(x=>(''+x).trim().toLowerCase()));
  const knownModel=m=>gfHas(defModels,m)||coming.has((m||'').trim().toLowerCase());
  if(defModels.length){
    md.forEach(m=>{if(!knownModel(m))add('armour_ug_models','<code>'+esc(m)+`</code> ${tt('guided.is_not_an_entry_in_this')}`,'bad');});
    const sm=(parts('soldier')[0]||'');
    if(has('soldier')&&sm&&!knownModel(sm))
      add('soldier','<code>'+esc(sm)+`</code> ${tt('guided.is_not_an_entry_in_this')}`,'bad');
  }
  [['mount','mount'],['engine','engine'],['mounted_engine','mounted_engine'],
   ['ship','ship'],['animal','animal']].forEach(([k,v])=>{
    const list=gfDefined(host,v);
    if(has(k)&&list.length&&!gfHas(list,val(k))&&!coming.has((val(k)||'').trim().toLowerCase()))
      add(k,'<code>'+esc(val(k))+`</code> ${tt('guided.is_not_defined_in_this_mods_2')}`+
        (k==='mounted_engine'?'mounted_engines':k==='engine'?'engines':k==='animal'?'animals':k)+tt('guided.txt'),'bad');
  });
  // The three banner lines name banners declared by descr_banners_new.xml, one
  // XML section per line. `defined` only carries them when the mod HAS that file.
  [[tt('guided.banner_faction'),'banner_faction','FactionBanners'],
   [tt('guided.banner_holy'),'banner_holy','HolyBanners'],
   [tt('guided.banner_unit'),'banner_unit','UnitSpecificBanners']].forEach(([k,v,section])=>{
    const list=gfDefined(host,v);
    if(has(k)&&list.length&&!gfHas(list,val(k)))
      add(k,'<code>'+esc(val(k))+`</code> ${tt('guided.is_not_declared_in_this_mods')} `
        +'<code>descr_banners_new.xml</code> (<code>&lt;'+section+'&gt;</code>).','bad');
  });
  if(has('soldier')){
    // NB: not "fewer than 4". The guide gives 4 as the minimum, but shipped mods
    // field 2-man scout and monster units that work perfectly well - only a unit
    // with no men at all is definitely wrong.
    const men=num(parts('soldier')[1]);
    if(men!==null&&men<1)add('soldier',tt('guided.a_unit_with_no_men_so'),'bad');
  }
  if(has('ownership')&&!csv(val('ownership')).length)
    add('ownership',tt('guided.no_owner_no_faction_can_recruit'),'bad');
  const attrs=csv(val('attributes'));
  if(attrs.indexOf('mercenary_unit')>=0&&!has('card_pic_dir'))
    add('attributes',tt('guided.mercenary_unit_the_unit_card_is'),'info');
  if(attrs.indexOf('can_run_amok')>=0&&!has('mount'))
    add('attributes',tt('guided.can_run_amok_only_does_anything'));
  if(has('stat_mental')){
    const p=parts('stat_mental');
    if(p.length>3&&(p[3]||'').toLowerCase()!=='lock_morale')
      add('stat_mental',tt('guided.the_optional_fourth_value_can_only'),'bad');
  }
  return out;
}

/* ---- rendering ---------------------------------------------------------- */
function gfRender(host){
  const gf=gfState(host);
  const warns=gfWarnings(host);
  const groups={};GF_SECTIONS.forEach(s=>groups[s.id]=[]);
  host.fields().forEach(([label])=>{
    const k=gfKey(label);
    let sec=GF_SECTION_OF[k];
    // a repeated line only has a guided shape when the field itself is repeatable
    if(sec&&/#\d+$/.test(label)&&k!=='officer')sec=null;
    (groups[sec||'other']).push(label);
  });
  const q=(gf.q||'').trim().toLowerCase();
  let shown,heading='';
  if(q){
    shown=host.fields().map(([l])=>l).filter(l=>{
      const sp=GF_FIELDS[gfKey(l)]||{};
      return (l+' '+(sp.t||'')+' '+(sp.doc||'')).toLowerCase().indexOf(q)>=0;});
    heading=`<div class="gfintro">${tt('guided.field_s_matching',{shown_n:shown.length,gf:esc(gf.q)})}</div>`;
  }else{
    if(!groups[gf.tab]||(!groups[gf.tab].length&&gf.tab!=='other'))
      gf.tab=(GF_SECTIONS.find(s=>groups[s.id].length)||GF_SECTIONS[0]).id;
    shown=groups[gf.tab];
  }
  const nWarn=Object.keys(warns).length;
  const nav=GF_SECTIONS.map(s=>{
    const n=groups[s.id].length;
    if(!n&&s.id==='other')return '';
    const hits=groups[s.id].filter(l=>gfReal(warns[l]).length);
    // the badge names the fields, not just how many - a bare "3 things to look
    // at" makes you open all three sections to find out which
    const why=hits.length?hits.join(', ')+tt('guided.hover_or_click_the_section_to'):'';
    return `<button class="${!q&&gf.tab===s.id?'on':''}" onclick="gfTab('${s.id}')">${esc(s.t)}
      <span class="n">${n}</span>${hits.length?`<span class="bad" title="${esc(why)}">▲ ${hits.length}</span>`:''}</button>`;
  }).join('');
  return `<div class="gfwrap">
    <div class="gfnav" id="gfNav">${nav}</div>
    <div class="gfbody" id="gfBody">
      <div class="gfsum" id="gfSum">${gfSumHtml(host,warns)}</div>
      ${heading}
      ${shown.length?gfRows(host,shown,warns)
        :`<div class="gfempty">${tt('guided.nothing_in_this_group_the_unit')}</div>`}
      ${gfAddHtml(host)}
    </div>
    ${gfDatalists(host)}</div>`;
}
function gfTab(id){const gf=state.gf; if(!gf)return; gf.tab=id; gf.q='';
  const f=document.getElementById('fieldFilter'); if(f)f.value='';
  gfRerenderBody();}
// Re-draw just the guided body, so switching a section or opening a raw line
// does not throw away the rest of the dialog (or its scroll position).
function gfRerenderBody(){
  const box=document.getElementById('allFields'); if(!box)return;
  if(!((state.mode==='edit'&&state.ed)||state.editing))return;
  const host=gfHost();
  const b=document.getElementById('gfBody'),was=b?b.scrollTop:0;
  box.innerHTML=gfRender(host); gfWire(host);
  const now=document.getElementById('gfBody'); if(now&&was)now.scrollTop=was;
}
const gfReal=list=>(list||[]).filter(x=>x.k!=='info');
function gfSumHtml(host,warns){
  const n=Object.values(warns).reduce((a,b)=>a+gfReal(b).length,0);
  const bad=Object.values(warns).reduce((a,b)=>a+b.filter(x=>x.k==='bad').length,0);
  return `<span class="count">${tt('guided.line_s_in_this_unit',{n:host.fields().length})}</span>`
    +(n?`<span class="pill warn" onclick="gfShowWarnings()" title="${ttA('guided.jump_to_the_first_one')}">
        ${bad?'✖ '+bad+' broken':''}${bad&&n-bad?' · ':''}${n-bad?'▲ '+(n-bad)+tt('guided.to_check'):''}</span>`
      :`<span class="pill" style="border-color:var(--good);color:var(--good)">${tt('guided.nothing_looks_wrong')}</span>`);
}
function gfShowWarnings(){
  const el=document.querySelector('#gfBody .gfnote.bad,#gfBody .gfnote.warn');
  if(el){el.scrollIntoView({block:'center'});return;}
  // the first problem is in another section - find it and switch there
  const w=gfWarnings(gfHost()),first=Object.keys(w).find(k=>gfReal(w[k]).length); if(!first)return;
  gfTab(GF_SECTION_OF[gfKey(first)]||'other');
  setTimeout(()=>{const e2=document.querySelector('#gfBody .gfnote.bad,#gfBody .gfnote.warn');
    if(e2)e2.scrollIntoView({block:'center'});},0);
}

// One <datalist> per open drop-down, emitted once for the whole body.
// The model list carries what this job is about to create as well as what the
// mod has: a staged entry you cannot pick from the box that names entries is a
// box lying about the save it is part of.
function gfDatalists(host){
  const want=new Set();
  Object.values(GF_FIELDS).forEach(sp=>(sp.parts||[]).forEach(p=>{if(p.type==='combo')want.add(p.v);}));
  const coming=(host.creates?host.creates():[]).map(x=>(''+x).trim().toLowerCase()).filter(Boolean);
  return [...want].map(v=>{
    let list=gfV(host,v);
    if(v==='model'&&coming.length)
      list=list.concat(coming.filter(n=>!gfHas(list,n)));
    return `<datalist id="gfdl-${esc(v)}">${
      list.map(x=>`<option value="${esc(x)}">`).join('')}</datalist>`;}).join('');
}

function gfCard(host,label,warns){
  const key=gfKey(label);
  const spec=GF_FIELDS[key];
  const gone=host.removed(label);
  const lk=host.lock(label);
  const cur=host.get(label);
  const changed=host.changed(label);
  const gf=gfState(host);
  const rawOpen=gf.raw.has(label)||!spec;
  const parsed=spec&&spec.parts?gfParse(spec,cur):null;
  const title=spec?spec.t:label;
  const canRm=host.canRemove&&!host.protectedKeys.has(key);
  const head=`<div class="gfhead">
    ${spec?qmSpec(key,null):''}
    <span class="t">${esc(title)}</span>
    <span class="k">${esc(label)}</span>
    ${spec&&spec.opt?`<span class="count" title="${ttA('guided.the_engine_works_without_this_line')}">${tt('guided.optional')}</span>`:''}
    ${lk?`<span class="ibadge" title="${esc(lk.why)}">🔒</span>`:host.badge(label,cur)}
    <span class="sp"></span>
    ${(!gone&&!lk&&GF_ACTIONS[key])?GF_ACTIONS[key](label,cur):''}
    ${spec?`<button class="${gf.help.has(label)?'on':''}" title="${ttA('guided.what_this_line_does')}"
        onclick="gfHelp('${q1(esc(label))}')">?</button>`:''}
    ${lk?'':`<button class="${rawOpen?'on':''}" title="${ttA('guided.show_the_line_exactly_as_the')}"
        onclick="gfRaw('${q1(esc(label))}')">&lt;/&gt;</button>`}
    ${canRm?`<button class="rm" title="${gone?tt('guided.keep_this_line'):tt('guided.delete_this_line_from_the_unit')}"
        onclick="gfRemove('${q1(esc(label))}')">${gone?'↺':'✕'}</button>`:''}
  </div>`;
  let body='';
  if(gone)body=`<div class="gfnote">${tt('guided.this_line_will_be_removed_from')}</div>`;
  else if(lk)body=`<div class="gfrow"><div class="gfpart grow"><span class="pl">${tt('common.value')}</span>
      <input value="${esc(lk.val)}" disabled title="${esc(lk.why)}"></div></div>
    <div class="gfnote">${esc(lk.why)}</div>`;
  else if(spec&&spec.w)body=gfWidget(host,label,spec,cur);
  else if(spec&&parsed&&parsed.ok)body=gfParts(host,label,spec,parsed);
  else if(spec)body=`<div class="gfnote warn">${tt('guided.this_line_has_value_s_the',{parts_n:parsed.parts.length,x:(spec.arity||[spec.parts.length]).join(' or ')})}</div>`;
  const raw=(rawOpen&&!gone&&!lk)?`<div class="gfraw">
      <span class="pl">${esc(key)}</span>
      <input data-gfraw="${esc(label)}" value="${esc(cur)}" spellcheck="false"
        class="${changed?'changed':''}"></div>`:'';
  const doc=(spec&&gf.help.has(label))?`<div class="gfdoc">${spec.doc||''}</div>`:'';
  const empty=(parsed&&parsed.empty&&!gone)?`<div class="gfnote">${tt('guided.this_line_is_empty_fill_it')}</div>`:'';
  return `<div class="gfcard${changed?' changed':''}${gone?' gone':''}" data-card="${esc(label)}">
    ${head}${doc}${body}${empty}${raw}
    <div data-warn="${esc(label)}">${gfNotes(warns[label])}</div></div>`;
}
/* Quick actions in a card's header. "No secondary weapon" is not a cosmetic
   shortcut: the engine recognises one exact line as "this unit has no sidearm"
   (`0, 0, no, 0, 0, no, melee_simple, blunt, none, 25, 1`), and typing eleven
   values by hand to say nothing is how the reference editor makes people do it. */
const GF_NO_WEAPON=tt('guided.0_0_no_0_0_no');
const gfIsNoWeapon=v=>{const p=(v||'').split(',').map(x=>x.trim());
  return p.length>=9&&p[0]==='0'&&p[2]==='no'&&(p[5]==='no'||p[5]==='');};
const GF_ACTIONS={
  stat_sec:(label,cur)=>gfIsNoWeapon(cur)?'':`<button title="${ttA('guided.write_the_line_the_engine_reads')}"
    onclick="gfNoWeapon('${q1(esc(label))}')">${tt('guided.no_secondary_weapon')}</button>`,
  stat_ter:(label,cur)=>gfIsNoWeapon(cur)?'':`<button title="${ttA('guided.write_the_empty_weapon_line_and')}"
    onclick="gfNoWeapon('${q1(esc(label))}')">${tt('guided.no_third_weapon')}</button>`,
};
function gfNoWeapon(label){
  const host=gfHost();
  host.set(label,GF_NO_WEAPON);
  const attr=label+'_attr';
  if(host.fields().some(([l])=>l===attr))host.set(attr,'no');
  host.stale(); gfRerenderBody();
}
const gfNotes=list=>(list||[]).map(m=>`<div class="gfnote ${m.k||'warn'}">${m.h}</div>`).join('');

// Which PART of a multi-value line differs from what the file said. A whole-line
// "changed" flag is no help on `stat_pri 7, 3, no, 0, 0, melee, …`: you want the
// one number you touched lit up, not all thirteen.
function gfPartChanged(host,label,spec,parsed){
  const was=gfParse(spec,(host.orig?host.orig(label):'')||'');
  const whole=host.changed(label);
  const norm=v=>(v==null?'':''+v).trim();
  return i=>{
    if(!was||!was.ok||!parsed.ok)return whole;   // can't line them up, so mark the lot
    return norm(parsed.parts[i])!==norm(was.parts[i]);
  };
}
function gfParts(host,label,spec,parsed){
  const key=gfKey(label);
  const partChanged=gfPartChanged(host,label,spec,parsed);
  const cells=spec.parts.map((p,i)=>{
    const v=parsed.parts[i]==null?'':parsed.parts[i];
    const ch=partChanged(i);
    const cls='gfpart'+(p.grow?' grow':p.w===3?' w3':p.w===2?' w2':'')+(ch?' changed':'');
    const attr=tt('guided.data_gfp_data_i',{label:esc(label),x:i});
    const chc=ch?' changed':'';                  // the amber "you changed this"
    // the explanation hangs off the ? beside the part's name; the control keeps
    // an accessible name of its own, since the label is not a <label for=…>
    const aria=tt('guided.aria_label',{pl:esc(p.pl)});
    let ctl;
    if(p.type==='flag'){
      ctl=`<label class="chk" style="height:26px"><input type="checkbox" ${attr}${aria}
        class="${chc.trim()}" ${v?'checked':''}> ${esc(p.on||'on')}</label>`;
    }else if(p.type==='sel'){
      const opts=gfV(host,p.v);
      const list=opts.indexOf(v)<0?[v].concat(opts):opts;
      ctl=`<select ${attr}${aria} class="${chc.trim()}">${list.map(o=>`<option value="${esc(o)}"${
        o===v?' selected':''}>${o===''?(p.optional?tt('common.none_2'):'(unset)'):esc(o)}</option>`).join('')}</select>`;
    }else if(p.type==='combo'){
      // A model name is the one combo where the datalist is not enough: it is
      // 2000-odd entries and the thing you actually know is how the man should
      // MOVE, which lives in the entry's skeleton. ⌕ opens the picker.
      const box=`<input ${attr}${aria} class="${chc.trim()}" list="gfdl-${esc(p.v)}"
        value="${esc(v)}" spellcheck="false">`;
      ctl=p.v!=='model'?box:`<span class="gfcombo">${box}<button type="button" class="gfbrowse"
        tabindex="-1" title="${ttA('guided.find_an_entry_by_skeleton_by')}"
        onclick="mpOpen('${q1(esc(label))}',${i})">⌕</button></span>`;
    }else if(p.type==='num'){
      ctl=gfSpin(attr+aria,v,chc);
    }else{
      ctl=`<input ${attr}${aria} class="${chc.trim()}" value="${esc(v)}" spellcheck="false"
        ${p.mono?' style="font-family:ui-monospace,Consolas,monospace"':''}>`;
    }
    // the wrapper carries the part index too (but NOT data-gfp, which is the
    // "this is an editable control" marker) so hovering the part's NAME lights
    // the same one value in the code view - see cvPartOf
    return `<div class="${cls}" data-i="${i}"><span class="pl">${qmSpec(key,i)}${esc(p.pl)}${
      p.optional?' <span style="opacity:.6">(opt)</span>':''}</span>${ctl}</div>`;
  }).join('');
  return `<div class="gfgrid">${cells}</div>`;
}
/* A number box with its own ▴▾. The browser's own <input type=number> is not
   used on purpose: EDU values are decimals, negatives and occasionally blanks,
   and a number input quietly refuses or reformats those. This keeps a plain text
   box - so any value in the file survives being looked at - and puts the
   stepping in buttons and the ↑/↓ keys, which are the only things that clamp. */
const gfSpin=(attr,v,cls)=>`<span class="gfspin"><input ${attr} class="gfnum${cls||''}" value="${esc(v)}"
    spellcheck="false" inputmode="decimal"><span class="gfsp">
    <button type="button" tabindex="-1" data-spin="1" aria-label="${ttA('guided.increase')}">▴</button>
    <button type="button" tabindex="-1" data-spin="-1" aria-label="${ttA('guided.decrease')}">▾</button>
  </span></span>`;

/* ---- the ? marker -------------------------------------------------------
   Explanations are ASKED FOR, not sprung: a field's help hangs off a small ?
   at its top-left rather than off the field itself, so moving the pointer
   across a form does not set off a trail of cards, and a box you are trying to
   read is never covered by a tip about the box next to it.

   `qm(text)` is the plain form. `qmSpec(key, i)` is the one the guided editor
   uses, which pulls a full card out of GF_FIELDS instead of a line of text.
   Both are read by the same delegated handler below. */
// The markers are deliberately NOT tab stops: there is one per field, and a
// guided unit has four hundred of them - putting each in the tab order would
// double the keystrokes to cross a form. Keyboard users get the same card when
// they focus the field itself (see the focusin handler), and the marker keeps a
// plain `title` so it still has an accessible name of its own.
const qm=(text,title)=>!text?'':`<span class="qm" tabindex="-1"
  title="${esc(text)}"${title?tt('guided.data_tiptitle',{title:esc(title)}):''}
  data-tiptext="${esc(text)}">?</span>`;
const qmSpec=(key,i)=>`<span class="qm" tabindex="-1" title="${ttA('guided.what_is_this')}"
  data-tip="${esc(key)}"${i==null?'':tt('guided.data_tipi',{x:i})}>?</span>`;
// A field's documentation as plain text, for the raw view - GF_FIELDS writes its
// `doc` as HTML, and a ? marker carries text.
function gfPlainDoc(key){
  const spec=GF_FIELDS[key];
  if(!spec||!spec.doc)return '';
  return spec.doc.replace(/<[^>]*>/g,'').replace(/\s+/g,' ').trim();
}

/* ---- the hover card -----------------------------------------------------
   One floating element driven by delegation, so it survives the guided body
   being redrawn (which happens on nearly every edit) without rebinding
   anything. */
function gfTipHtml(key,i){
  const spec=GF_FIELDS[key]; if(!spec)return '';
  if(i==null||i===''){
    return `<div class="tt">${esc(spec.t)}</div>
      <div class="tk">${esc(key)}${spec.syn?'  '+esc(spec.syn):''}</div>
      <div class="tb">${spec.doc||''}</div>
      ${spec.opt?`<div class="tf">${tt('guided.optional_the_engine_works_without_this')}</div>`:''}`;
  }
  const p=(spec.parts||[])[+i]; if(!p)return '';
  const range=[];
  if(p.type==='num'){
    if(p.min!=null&&p.max!=null)range.push(`${p.min} to ${p.max}`);
    else if(p.min!=null)range.push(tt('guided.or_more',{x:p.min}));
    else if(p.max!=null)range.push(tt('guided.up_to',{x:p.max}));
    if(p.step&&p.step!==1)range.push(tt('guided.steps_of',{step:p.step}));
  }
  return `<div class="tt">${esc(p.pl)}${p.optional?` <span class="topt">${tt('common.optional')}</span>`:''}</div>
    <div class="tk">${tt('guided.value_of',{key:esc(key),x:(+i)+1,parts_n:spec.parts.length})}</div>
    <div class="tb">${p.help||spec.doc||''}</div>
    ${range.length?`<div class="tf">${tt('guided.and_the_keys_step_within_hold',{range:range.join(', ')})}</div>`:''}`;
}
let gfTipEl=null;
function gfTipShow(el){
  let html;
  if(el.dataset.tiptext!==undefined){
    // a plain explanation moved off a field's own title attribute
    html=(el.dataset.tiptitle?`<div class="tt">${esc(el.dataset.tiptitle)}</div>`:'')
        +`<div class="tb">${esc(el.dataset.tiptext)}</div>`;
  }else{
    const key=el.dataset.tip,i=el.dataset.tipi;
    html=gfTipHtml(key,i===undefined?null:i);
  }
  if(!html)return;
  if(!gfTipEl){gfTipEl=document.createElement('div');gfTipEl.className='gftip';document.body.appendChild(gfTipEl);}
  gfTipEl.innerHTML=html; gfTipEl.style.display='block';
  gfTipEl.style.left='0px'; gfTipEl.style.top='0px';         // measure unconstrained
  const r=el.getBoundingClientRect(),t=gfTipEl.getBoundingClientRect();
  let x=r.left, y=r.bottom+7;
  if(x+t.width>window.innerWidth-10)x=Math.max(10,window.innerWidth-10-t.width);
  if(y+t.height>window.innerHeight-10)y=Math.max(10,r.top-7-t.height);
  gfTipEl.style.left=x+'px'; gfTipEl.style.top=y+'px';
}
function gfTipHide(){if(gfTipEl)gfTipEl.style.display='none';}
// bound once, on the document - the guided body is replaced wholesale on edits
const TIP_SEL='[data-tip],[data-tiptext]';
document.addEventListener('mouseover',ev=>{
  const el=ev.target&&ev.target.closest&&ev.target.closest(TIP_SEL);
  if(!el){gfTipHide();return;}
  if(el===gfTipEl)return;
  gfTipShow(el);
});
document.addEventListener('mouseleave',gfTipHide,true);
window.addEventListener('scroll',gfTipHide,true);
/* Focusing a field shows its ? card, so the help is reachable without a mouse
   even though the markers themselves are out of the tab order - but only when
   the focus came from the KEYBOARD. Clicking into a box to type in it was
   dropping a help card over the row you were about to edit, which reads as the ?
   button opening itself. `:focus-visible` can't tell these apart: browsers match
   it on text inputs however they were focused. */
let _tipByPointer=false;
document.addEventListener('pointerdown',()=>{_tipByPointer=true;},true);
document.addEventListener('keydown',()=>{_tipByPointer=false;},true);
document.addEventListener('focusin',ev=>{
  const byPointer=_tipByPointer; _tipByPointer=false;
  if(_tipQuiet)return;                     // a re-draw putting the caret back
  const t=ev.target;
  if(!t||!t.closest){gfTipHide();return;}
  let el=t.closest(TIP_SEL);
  if(!el&&/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName||'')){
    if(byPointer){gfTipHide();return;}     // clicked into, not tabbed into
    const cell=t.closest('.gfpart,.afrow,.brow,.condrow,.gfcard');
    el=cell?cell.querySelector('.qm'):null;
  }
  if(el)gfTipShow(el); else gfTipHide();
});
document.addEventListener('keydown',ev=>{if(ev.key==='Escape')gfTipHide();});
