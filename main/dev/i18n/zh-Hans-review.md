# Simplified Chinese review, 2026-10-28

Phase 88o complete as a draft: 9,633 IDs, including 379 plural objects.
No missing, stale or extra IDs; full structural/termbase checker: zero problems.
Native-speaker review remains pending. No release cut.

Home, Settings, Transfer and Campaign Map were inspected in the in-app
browser at desktop width (1280 px) and 375 px. Chinese glyphs render without
replacement boxes in these screens; headings, labels and prose wrap. The
page does not overflow horizontally in the measured narrow views. Mod names,
unit names and literal engine values retain the mod's own language.
This is a representative screen review, not a claim to have exercised every
dialog or every save operation. No mod writes were performed.

Existing CJK rules in web/index.html were verified: Microsoft YaHei UI for
Simplified Chinese, JhengHei for Traditional Chinese, Yu Gothic UI for Japanese,
Malgun Gothic for Korean; strict line breaking, normal word breaking, no
synthetic italics or letter spacing, and monospace code/path styles retained.
Chinese computed font and line-break styles match those rules.

The promoted picker offers 简体中文 (Chinese (Simplified)) - 草稿 once.
The old preview script's missing native label was confined to .cache and
removed for the final picker review. No saved ui_lang preference was changed.

Validation: tests.test_i18n 37/37, tests.test_web_modules 124/124;
termbase 189 terms / 16 languages / zero problems. Source hash stale detection
was checked using an in-memory changed English value.

## Exact glossary exceptions carried by the checked catalogue

Each entry below retains its per-term exception, English source and Chinese
translation for native review. These exemptions are for overloaded meanings,
literal tokens and paths; they do not suppress structural validation.

### app.shared_cards_title

Terms: ['tile']

English: "Grouped by faction: only the tiles whose faction has no card of its own for the unit and borrows another's"

Chinese: "按派系分组时，仅显示该派系缺少部队专属卡片、借用其他派系卡片的项目"

### armory.exp_free_turn_title

Terms: ['turn']

English: "Let a block turn to whatever angle packs it smallest, as well as by quarter turns. A block turned so is resampled and its art softens slightly; off, every texel is copied exactly."

Chinese: "除直角旋转外，允许块转到占用空间最小的任意角度。这种旋转会重采样，使图片略微变软；关闭时会精确复制每个纹素。"

### armory.frame_all

Terms: ['frame']

English: "Frame all"

Chinese: "显示全部"

### armory.head_as_one_title

Terms: ['turn']

English: "Helmet, coif, face, hair and beard move, turn and scale together whichever of them is picked"

Chinese: "选择头盔、头巾、面部、头发或胡须任一项时，整组一起移动、旋转和缩放"

### armory.key_frame_all

Terms: ['frame']

English: "Frame everything"

Chinese: "显示全部内容"

### armory.key_frame_selected

Terms: ['frame']

English: "Frame the selection"

Chinese: "聚焦所选内容"

### armory.look_closer_title

Terms: ['turn']

English: "A closer look: the model in the viewer, to turn, zoom, change its skin and play its animations, before it is pulled in"

Chinese: "放大查看：导入前可在查看器中旋转、缩放模型、更换贴图并播放动画"

### armory.mat_bone

Terms: ['bone']

English: "bone"

Chinese: "骨质"

### armory.stamp_rot

Terms: ['turn']

English: "Turn"

Chinese: "旋转"

### armory.statistics

Terms: ['stats']

English: "Statistics"

Chinese: "统计"

### armory.uv_hint

Terms: ['turn']

English: "Click picks, Shift adds, a drag on nothing draws a box, a drag on the selection moves it. G, R, S move, turn and scale (X or Y holds an axis; click or Enter keeps, Esc or the right button puts back). A selects all. The wheel zooms, the middle button or Alt pans."

Chinese: "点击选择，Shift 追加，空白处拖动框选，拖动选择可移动。G、R、S 分别移动、旋转和缩放（X 或 Y 约束轴向；点击或 Enter 确认，Esc 或右键恢复）。A 全选，滚轮缩放，中键或 Alt 平移。"

### buildings.copied_pool_open_another_building

Terms: ['header']

English: "Copied {unit}'s pool. Open another building and press 📋 Paste in its Recruitment header"

Chinese: "已复制 {unit} 的池。打开其他建筑，在招募标题栏中点击 📋 粘贴"

### buildings.every_rule_over_the_shape_of

Terms: ['upgrade']

English: "Every rule over the shape of this EDB: duplicate names, empty lines, and\nevery upgrades / convert_to / building_present_min_level that names something.\nRecruitment checks are on each building's own page."

Chinese: "检查此 EDB 结构的所有规则：重复名称、空系列，\n以及 upgrades / convert_to / building_present_min_level 的所有引用。\n招募检查位于各建筑自己的页面。"

### buildings.its_battle_model_has_no_texture

Terms: ['turn']

English: "its battle model has no texture for <b>{x}</b>, so their soldiers would turn up untextured"

Chinese: "其战斗模型没有 <b>{x}</b> 的贴图，因此其士兵将显示为无贴图状态"

### buildings.level_3

Terms: ['level']

English: "level:{name}:{x}#{x2}"

Chinese: "level:{name}:{x}#{x2}"

### buildings.level_key

Terms: ['level']

English: "level:{name}"

Chinese: "level:{name}"

### buildings.this_mod_ships_no_file_at

Terms: ['ship']

English: "This mod ships no file at\nthis path, so the game uses the base game's picture. Drop a .tga in to override it."

Chinese: "此模组在该路径没有文件，\n因此游戏使用自带图片。放入 .tga 即可覆盖。"

### buildings.units_without_battle_model_texture

Terms: ['turn']

English: {"one": "<b>{count}</b> has no battle-model texture for some of them, so their soldiers would turn up untextured: {list}", "other": "<b>{count}</b> have no battle-model texture for some of them, so their soldiers would turn up untextured: {list}"}

Chinese: {"other": "<b>{count}</b> 项缺少部分派系的战斗模型贴图，因此其士兵会显示为无贴图状态：{list}"}

### campaint.add_a_province_decide_its_record

Terms: ['port_verb']

English: "Add a province: decide its record, paint it, place its settlement, then its port or skip."

Chinese: "添加行省：设置记录、绘制区域、放置定居点，最后放置港口或跳过。"

### campaint.of_the_oldest_stroke_been_let

Terms: ['level']

English: {"one": "{count} of the oldest strokes has been let go: the stack holds every level there is until it is holding too many pixels to be worth it.", "other": "{count} of the oldest strokes have been let go: the stack holds every level there is until it is holding too many pixels to be worth it."}

Chinese: {"other": "已移除最早的 {count} 个笔画：撤消栈会保留所有层级，直到保存的像素过多、不再适合保留。"}

### campaint.place_the_port_pixel_or_skip

Terms: ['port_verb']

English: "Place the port pixel, or skip it"

Chinese: "放置港口像素，或跳过"

### campaint.writes_layers_at_once_in_the

Terms: ['port_verb']

English: "Writes {n} layers at once, in the colours <b>measured off this map</b>: {layers} · from {sea_tiles} sea tiles. Settlement and port pixels are left alone."

Chinese: "同时写入 {n} 个图层，颜色<b>从此地图测得</b>：{layers} · 来自 {sea_tiles} 个海洋图块。定居点和港口像素保持原样。"

### campaint.written_into_a_settlement_the_music

Terms: ['ship']

English: "Written into {reach}: a settlement, the music\n           type and, where it ships one, the name lookup - each campaign’s own\n           copy of each file."

Chinese: "写入 {reach}：定居点、音乐\n           类型，以及提供名称查找文件时的名称查找项，\n           均写入各战役自己的文件副本。"

### campbrowse.campaigns_read_in_ms

Terms: ['ship']

English: {"one": "{count} campaign read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom.", "other": "{count} campaigns read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom."}

Chinese: {"other": "已在 {ms} 毫秒内读取 {count} 个战役。没有独立副本的战役，其十个地图图层和地区列表均来自 <code>{base}</code>；这些战役的差异是开局位置、拥有的内容及敌对关系。"}

### campbrowse.every_campaign_this_mod_ships_with

Terms: ['ship']

English: "Every campaign this mod ships, with what is in each one, and which of them this screen is reading."

Chinese: "此模组包含的每个战役、各战役内容，以及此界面当前读取的战役。"

### campbrowse.nothing_in_to_read_a_menu

Terms: ['ship']

English: "Nothing in <code>{file}</code> to read a menu title out of - this mod ships neither it nor the compiled archive beside it - so no campaign below shows one. That is the file missing, not the campaigns being unnamed."

Chinese: "<code>{file}</code> 中没有可读取的菜单标题，此模组既未提供此文件，也未提供旁边的编译归档，因此下方战役均无菜单标题。这是文件缺失，并非战役未命名。"

### campbrowse.ships_map_layers

Terms: ['ship']

English: {"one": "It ships {count} map layer of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those.", "other": "It ships {count} map layers of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those."}

Chinese: {"other": "此战役有 {count} 个独立地图图层（{list}{more}），引擎会读取它们而非基础图层。打开后此界面会绘制这些图层。"}

### campcreate.new_region_name_paint_settlement_port

Terms: ['port_verb']

English: "<b>＋ New region</b><small>Name → paint → settlement → port</small>"

Chinese: "<b>＋ 新建地区</b><small>名称 → 绘制 → 定居点 → 港口</small>"

### campcreate.port

Terms: ['port_verb']

English: "Port"

Chinese: "港口"

### campcreate.port_marker_add_or_move_on

Terms: ['port_verb']

English: "<b>⚓ Port marker</b><small>Add or move on the selected region</small>"

Chinese: "<b>⚓ 港口标记</b><small>在所选地区添加或移动</small>"

### campcreate.select_a_region_first_then_choose

Terms: ['port_verb']

English: "Select a region first, then choose its settlement or port marker."

Chinese: "请先选择地区，再选择其定居点或港口标记。"

### campmap.building_the_composite

Terms: ['building']

English: "building the composite…"

Chinese: "正在生成合成图…"

### campmap.click_a_province_to_inspect_it

Terms: ['turn']

English: "Click a province to inspect it. Turn on Paint to edit tiles; right or middle drag still pans. Choose a layer and colour on the left."

Chinese: "点击行省查看。启用绘制可编辑图块；右键或中键拖动仍用于平移。在左侧选择图层和颜色。"

### campmap.comp_key

Terms: ['terrain']

English: "{layers}|terrain:{terrain}|fe:{fe}"

Chinese: "{layers}|terrain:{terrain}|fe:{fe}"

### campmap.has_no_campaign_map_this_tool

Terms: ['ship']

English: "has no campaign map this tool can read.<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">A mod only has one if it ships <code>data/world/maps/base</code> - the terrain header, the region list and the ten TGA layers. Without them the game uses its own map, and there is nothing here to draw.</span>"

Chinese: "没有此工具可读取的战役地图。<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">模组只有提供 <code>data/world/maps/base</code> 时才拥有自己的地图，其中包含地形文件头、地区列表和十个 TGA 图层。否则游戏使用自身地图，此处没有可绘制的内容。</span>"

### campmap.port_marker

Terms: ['port_verb']

English: "Port marker"

Chinese: "港口标记"

### campmap.port_pixel

Terms: ['port_verb']

English: "port pixel"

Chinese: "港口像素"

### campmap.port_pixels_undecided

Terms: ['port_verb']

English: {"one": "{count} port pixel whose owning region cannot be decided", "other": "{count} port pixels whose owning region cannot be decided"}

Chinese: {"other": "{count} 个港口像素无法确定所属地区"}

### campmap.region_id_tiles_settlement_at_game

Terms: ['port_verb']

English: "<span>Region ID</span><b>{x}</b> <span>Tiles</span><b>{count}{x2}</b> <span>Settlement at</span><b>{x3} <span class=\"count\">game</span> · {x4} <span class=\"count\">image</span></b> <span>Port at</span><b>{x5}</b> {x6} <span>Bounding box</span><b>{x7}</b>"

Chinese: "<span>地区 ID</span><b>{x}</b> <span>图块</span><b>{count}{x2}</b> <span>定居点位置</span><b>{x3} <span class=\"count\">游戏</span> · {x4} <span class=\"count\">图像</span></b> <span>港口位置</span><b>{x5}</b> {x6} <span>边界框</span><b>{x7}</b>"

### campmap.settlement_character_and_port_names_beside

Terms: ['port_verb']

English: "Settlement, character and port names beside their markers (L), placed so that none covers another.\nA name with no room at this zoom is left off and counted; zoom in for it."

Chinese: "在标记旁显示定居点、人物和港口名称（L），并避免相互遮挡。\n当前缩放下没有空间的名称会省略并计数；放大即可查看。"

### campmap.ships_its_own_so_that_layer

Terms: ['ship']

English: "{campaign} ships its own {own}, so that layer is drawn from <code>{folder}</code>. Everything else is <code>world/maps/base</code>, which is what the brush paints."

Chinese: "{campaign} 提供自己的 {own}，因此该图层从 <code>{folder}</code> 绘制。其余内容均来自画笔绘制的 <code>world/maps/base</code>。"

### campmap.the_campaign_map_as_a_surface

Terms: ['turn']

English: "The campaign map as a surface. Drag to turn, right-drag to pan, scroll to zoom."

Chinese: "以曲面显示战役地图。拖动旋转，右键拖动平移，滚动缩放。"

### campmap.the_heights_as_a_surface_with

Terms: ['turn']

English: "The heights as a surface, with this map's own ground on it, orbited (D).\nDrag to turn, right-drag to pan, wheel to zoom.\nMarkers, labels and the tooltip stay on the flat map."

Chinese: "将高度显示为曲面，应用此地图自身的地面并环绕查看（D）。\n拖动旋转，右键拖动平移，滚轮缩放。\n标记、标签和提示仍显示在平面地图上。"

### campmark.named_character_general_admiral_port_spy

Terms: ['port_verb']

English: "♚ Named character · ⚔ General · ⚓ Admiral / port<br> ◈ Spy · ¤ Merchant · ⚑ Diplomat · ✝ Priest · † Assassin"

Chinese: "♚ 具名人物 · ⚔ 将军 · ⚓ 海军将领 / 港口<br> ◈ 间谍 · ¤ 商人 · ⚑ 外交官 · ✝ 牧师 · † 刺客"

### campmark.port

Terms: ['port_verb']

English: "Port · {x}"

Chinese: "港口 · {x}"

### campmark.this_mod_ships_its_own_picture

Terms: ['ship']

English: "This mod ships its own picture for {art} of the\n        {n} trade resources here; the rest draw a glyph,\n        because the stock art is inside a .pack archive."

Chinese: "此处 {n} 种贸易资源中，此模组有 {art} 种专属图片；\n        其余显示符号，\n        因为原始图片位于 .pack 归档中。"

### campnew.map_layers_note

Terms: ['ship']

English: {"one": "It ships {count} map layer of its own, so the copy gets a copy of those too and the two are then two maps to keep in step.", "other": "It ships {count} map layers of its own, so the copy gets a copy of those too and the two are then two maps to keep in step."}

Chinese: {"other": "此战役有 {count} 个独立地图图层，也会复制它们，之后需分别维护两张地图的一致性。"}

### campnew.this_mod_ships_only_the_compiled

Terms: ['ship']

English: "This mod ships only the compiled archive of <code>{descriptions}</code>, which is where the keys would go."

Chinese: "此模组仅包含 <code>{descriptions}</code> 的编译归档，文本键本应写入该文件。"

### cards.and_more_written_into_the_merc

Terms: ['mercenary']

English: "…and {copy_count} more written into the merc folder"

Chinese: "…另有 {copy_count} 项写入 merc 文件夹"

### cards.confirm_move_folded

Terms: ['mercenary']

English: "Move {delete_count} card file(s) out of “{mod}”, freeing {freed} MB?\n\nThey are copied to:\n{target}\n\n{consolidated} card(s) are folded into the merc folder, which is where the game looks when a faction's own folder has nothing.\n\nEverything touched is backed up first. 🕑 Log → Undo puts it all back."

Chinese: "从“{mod}”移出 {delete_count} 个卡片文件，释放 {freed} MB？\n\n文件会复制到：\n{target}\n\n{consolidated} 张卡片会合并到 merc 文件夹，派系自身文件夹为空时，游戏会在此查找。\n\n所有受影响内容均会先备份。🕑 日志 → 撤消可全部还原。"

### cards.copying_file_s_out_writing_into

Terms: ['mercenary']

English: "Copying {export_count} file(s) out, writing {copy_count} into the merc folder,\n     then taking {delete_count} out of {mod}. Everything is backed up as it goes."

Chinese: "正在向外复制 {export_count} 个文件，向 merc 文件夹写入 {copy_count} 个文件，\n     随后从 {mod} 移除 {delete_count} 个文件。每步均会备份。"

### cards.data_ui_units_data_ui_unit

Terms: ['unit']

English: "data/ui/units · data/ui/unit_info"

Chinese: "data/ui/units · data/ui/unit_info"

### cards.gen_place_reset

Terms: ['frame']

English: "Put the model and the frame back"

Chinese: "恢复模型与取景框位置"

### cards.gen_rig_hint

Terms: ['turn']

English: "Drag the dots in the HD view: hands, feet, the pelvis and the torso move, the diamonds point the elbows and knees, the head turns."

Chinese: "拖动高清视图中的圆点可移动手、脚、骨盆及躯干；菱形用于指定肘部和膝盖方向，头部也可转动。"

### cards.gen_turn

Terms: ['turn']

English: "Turn"

Chinese: "旋转"

### cards.gen_view_hint

Terms: ['turn']

English: "In the HD view: middle drag turns the camera, Shift pans, the wheel zooms; G moves and R turns the model, X, Y or Z holds it to an axis, a click or Enter keeps it, Esc puts it back."

Chinese: "高清视图中：按中键拖动旋转相机，按 Shift 平移，滚轮缩放；G 移动模型，R 旋转模型，X、Y 或 Z 约束轴向，点击或按 Enter 确认，Esc 恢复。"

### cards.merc

Terms: ['mercenary']

English: " ·&nbsp;merc"

Chinese: " ·&nbsp;merc"

### cards.one_is_the_merc_copy

Terms: ['mercenary']

English: " - one of them is already the merc copy"

Chinese: "，其中一个已是 merc 副本"

### changes.turn_off

Terms: ['turn']

English: "Turn off"

Chinese: "关闭"

### changes.turn_off_putting_the_original_records

Terms: ['turn']

English: "Turn \"{off}\" off, putting the original records back?"

Chinese: "关闭“{off}”，恢复原始记录？"

### changes.turn_on

Terms: ['turn']

English: "Turn \"{on}\" on?"

Chinese: "启用“{on}”？"

### climates.append_a_name_the_engine_does

Terms: ['ship']

English: "Append a name the engine does not ship. The strat map draws it; the\nbattle map reads climates by name, which is what the warning is about."

Chinese: "追加引擎自带列表以外的名称。战略地图可绘制此气候，\n战斗地图则按名称读取气候，警告针对后者。"

### climates.taking_over_one_of_the_twelve

Terms: ['ship']

English: "{problem} Taking over one of the twelve the engine ships needs no such check."

Chinese: "{problem} 接管引擎自带的十二种气候之一无需此检查。"

### codeview.every_string_here_is_stored_as

Terms: ['character']

English: "Every string here is stored as its own length\nfollowed by that many characters. Change a path and the number beside it has to\nchange too. This does that, and you can see it happen."

Chinese: "此处每个字符串先存储长度，\n再存储对应数量的字符。修改路径时，旁边的长度也必须改变。\n此功能会自动更新，你可以实时看到变化。"

### core.every_model_a_mod_ships_the

Terms: ['ship']

English: "Every model a mod ships: the battle entries, their sprites, the strat map’s, and the cards"

Chinese: "模组包含的所有模型：战斗条目及其精灵图、战略地图模型和卡片"

### core.the_tool_did_not_finish_loading

Terms: ['turn']

English: "The tool did not finish loading.<br> <span class=\"count\">The server is running - it answered for the rest of this page - but the browser never received {names}. Reloading fetches it again. If it fails every time, an ad blocker or privacy extension is the usual cause: turn it off for 127.0.0.1.</span>"

Chinese: "工具未能完成加载。<br> <span class=\"count\">服务器正在运行，也已响应此页面的其余请求，但浏览器未收到 {names}。重新加载会再次获取文件。如果每次都失败，通常是广告拦截器或隐私扩展导致的：请为 127.0.0.1 停用它。</span>"

### core.the_two_pictures_per_unit_deduplicated

Terms: ['mercenary']

English: "The two pictures per unit, deduplicated into the merc folder"

Chinese: "每个部队的两张图片，去重后存入 merc 文件夹"

### edusort.a_banner_like_gondor_tier_2

Terms: ['banner', 'infantry']

English: "A banner like ;--- GONDOR TIER 2 INFANTRY --- already says the tier"

Chinese: "类似 ;--- GONDOR TIER 2 INFANTRY --- 的标题注释已表明层级"

### edusort.a_comment_in_this_file_starts

Terms: ['banner']

English: "A comment in this file starts with a semicolon, so a banner has to as well."

Chinese: "此文件的注释以分号开头，标题注释也必须如此。"

### edusort.a_tier_read_from_a_banner_is

Terms: ['banner']

English: "A tier read from a banner is written onto the unit as <code>;@m2gt tier=2</code>, so the next run does not have to read it again."

Chinese: "从标题注释读取的层级会以 <code>;@m2gt tier=2</code> 写入部队，下次运行时无需再次解析标题。"

### edusort.a_unit_with_no_tier_sorts_after

Terms: ['banner']

English: "A unit with no <b>tier</b> sorts after every tiered unit in its group. Tiers read from the file’s own banners are already filled in."

Chinese: "没有<b>层级</b>的部队排在同组所有具有层级的部队之后。从文件自身标题注释读取的层级已填入。"

### edusort.gondor_tier_2_infantry

Terms: ['tier', 'infantry']

English: "GONDOR TIER 2 INFANTRY"

Chinese: "GONDOR TIER 2 INFANTRY"

### edusort.gondor_tier_2_infantry_2

Terms: ['tier', 'infantry']

English: "Gondor Tier 2 Infantry"

Chinese: "Gondor Tier 2 Infantry"

### edusort.line_character

Terms: ['character']

English: "Line character"

Chinese: "线条字符"

### edusort.read_tiers_from_the_files_own

Terms: ['banner']

English: "Read tiers from the file’s own banners"

Chinese: "从文件自身的标题注释读取层级"

### edusort.section_banners

Terms: ['banner']

English: "Section banners"

Chinese: "区段标题注释"

### edusort.the_shape_is_fixed_so_the_next

Terms: ['banner']

English: "The shape is fixed so the next run can read the section back out of it. A banner your mod wrote by hand is recognised too, and left alone."

Chinese: "格式固定，便于下次运行时读取区段。模组中手写的标题注释也会被识别，并保留原样。"

### edusort.write_a_banner_above_each_section

Terms: ['banner']

English: "Write a banner above each section"

Chinese: "在每个区段上方写入标题注释"

### eng.animloose.turns_bones_and_its_skeleton_has

Terms: ['turn']

English: "{x} turns {nq} bones and its skeleton has {bones_n}"

Chinese: "{x} 旋转 {nq} 根骨骼，而其骨架有 {bones_n} 根骨骼"

### eng.animpack.the_source_ships_no_packs_of

Terms: ['ship']

English: "the source ships no packs of its own, so it plays vanilla's and they are what is ported"

Chinese: "来源没有提供自己的包，因此使用原版包，移植的也将是原版包"

### eng.animslot.this_mod_ships_no_animation_packs

Terms: ['ship']

English: "this mod ships no animation packs of its own (the game plays vanilla's), so there is no pack of its own to save into"

Chinese: "此模组未提供自己的动画包（游戏使用原版动画包），因此没有可保存到的自有包"

### eng.buildings.hidden_ceiling_note

Terms: ['ship']

English: "TWCenter's List of Hardcoded Limits puts the ceiling at 63 or 64 and says more crash the game. Divide and Conquer ships 75 and ROCSS 74, and both play, so it is not enforced here."

Chinese: "TWCenter 的硬编码限制列表称上限为 63 或 64，超出会导致游戏崩溃。但 Divide and Conquer 提供 75 个，ROCSS 提供 74 个，且均可运行，因此此处不强制执行该限制。"

### eng.campaint.is_a_marker_colour_black_is

Terms: ['port_verb']

English: "{rgb} {rgb2} {rgb3} is a marker colour - black is where a settlement stands and white is where a port does, so neither can be a province"

Chinese: "{rgb} {rgb2} {rgb3} 是标记颜色；黑色表示定居点，白色表示港口，因此两者均不能用于行省"

### eng.campaint.is_not_a_marker_map_regions

Terms: ['port_verb']

English: "{marker} is not a marker - map_regions.tga has two, the settlement and the port"

Chinese: "{marker} 不是标记；map_regions.tga 只有定居点和港口两种标记"

### eng.campaint.settlement_or_port_pixels_left_alone

Terms: ['port_verb']

English: {"one": "{count} settlement or port pixel left alone", "other": "{count} settlement or port pixels left alone"}

Chinese: {"other": "{count} 个定居点或港口像素保持原样"}

### eng.campaint.ships_own_so_it_does_not_see

Terms: ['ship']

English: {"one": "{skipped} ships its own {REGIONS_TGA}, so it does not see these pixels and {name} does not exist there", "other": "{skipped} ship their own {REGIONS_TGA}, so they do not see these pixels and {name} does not exist there"}

Chinese: {"other": "{skipped} 提供自己的 {REGIONS_TGA}，因此不会显示这些像素，其中也不存在 {name}"}

### eng.campevents.is_not_one_of_the_eight

Terms: ['ship']

English: "`{kind}` is not one of the eight the engine has; the file the engine ships declares {and_list}"

Chinese: "`{kind}` 不是引擎支持的八种类型之一；引擎提供的文件声明了 {and_list}"

### eng.campfiles.this_mod_ships_only_so_the

Terms: ['ship']

English: "this mod ships only {name}, so the keys go straight into the compiled archive"

Chinese: "此模组仅提供 {name}，因此键会直接写入编译归档"

### eng.campnew.is_not_on_disk_and_ships

Terms: ['ship']

English: "{REGIONS_REL} is not on disk and {source} ships no map of its own, so there is no region list for this campaign to read"

Chinese: "磁盘上没有 {REGIONS_REL}，且 {source} 未提供自己的地图，因此没有可供此战役读取的地区列表"

### eng.campnew.nothing_names_on_the_new_game_menu_archive

Terms: ['ship']

English: "nothing names {name} on the new-game menu, so the engine shows the key {head}TITLE. {descr_rel} is where that lives and the Descriptions panel writes it. This mod ships only the compiled archive, which is where the key would go."

Chinese: "新游戏菜单中没有 {name} 的名称，因此引擎显示键 {head}TITLE。它存放于 {descr_rel}，可通过描述面板写入。此模组仅提供编译归档，键将写入其中。"

### eng.campnew.ships_map_layer_s_of_its

Terms: ['ship']

English: "{source} ships {layers_n} map layer(s) of its own ({layers}), so the copy gets a copy of them too and the two campaigns are then two maps to keep in step. The map screen draws whichever one the campaign you have open reads."

Chinese: "{source} 提供 {layers_n} 个自己的地图图层（{layers}），副本也会复制它们，此后需要同步维护两张战役地图。地图界面显示当前战役读取的那一张。"

### eng.cas.w_text_latin1

Terms: ['character']

English: "{value} has a character a .cas cannot hold (it is written in Latin-1)"

Chinese: "{value} 中有 .cas 无法保存的文本字符（文件使用 Latin-1 编码）"

### eng.cas.w_text_long

Terms: ['character']

English: "a name of {n:,} characters is longer than the reader takes"

Chinese: "名称有 {n:,} 个字符，超过读取器可接受的长度"

### eng.casanim.also_carries_size_bytes_as_some

Terms: ['siege']

English: "also carries {what} ({size:,} bytes), as some siege engine animations do; only the keys are read here"

Chinese: "还包含 {what}（{size:,} 字节），某些攻城器械动画也如此；此处只读取关键帧"

### eng.casanim.turns_bones_and_the_skeleton_has

Terms: ['turn']

English: "{name} turns {nq} bones and the skeleton {x} has {bones_n}: it is another skeleton's animation"

Chinese: "{name} 旋转 {nq} 根骨骼，而骨架 {x} 有 {bones_n} 根，这是另一骨架的动画"

### eng.climatenew.a_climate_name_the_battle_map

Terms: ['ship']

English: "{problem} A climate name the battle map does not know is a crash when a battle starts in it, so a new name is the half of this operation that cannot be checked against this mod. Taking over one of the twelve the engine ships - {SPARE} are spare by name - needs no such check."

Chinese: "{problem} 战斗地图不认识的气候名称，会在该气候中开始战斗时导致崩溃，因此新名称是此操作中无法根据模组验证的部分。接管引擎提供的十二种气候之一（{SPARE} 从名称来看是备用项）则无需此项检查。"

### eng.climatenew.all_four_mods_measured_for_this

Terms: ['ship']

English: "all four mods measured for this declare exactly the twelve climates the engine ships, in the engine's order, and not one added a thirteenth. Divide and Conquer has a wholly custom map and took over unused1 rather than adding a name."

Chinese: "所测四个模组均严格按引擎顺序声明了引擎提供的十二种气候，没有添加第十三种。Divide and Conquer 使用完全自定义的地图，也选择接管 unused1，而非添加名称。"

### eng.codeview.length_says_but_text_is

Terms: ['character']

English: "line {line}'s length says {said} but the text beside it is {should} characters - every modeldb string is written `<length> <text>`"

Chinese: "第 {line} 行声明长度为 {said}，但旁边文本有 {should} 个字符；每个 modeldb 字符串均写为 `<length> <text>`"

### eng.codeview.length_says_but_text_is_and_more

Terms: ['character']

English: "line {line}'s length says {said} but the text beside it is {should} characters (and {more} more like it) - every modeldb string is written `<length> <text>`"

Chinese: "第 {line} 行声明长度为 {said}，但旁边文本有 {should} 个字符（另有 {more} 处相同问题）；每个 modeldb 字符串均写为 `<length> <text>`"

### eng.gamelog.howto

Terms: ['level']

English: "The game writes system.log.txt only while its log is on; M2EX keeps it on. For the original game, put these lines under [log] in the .cfg the mod starts with, start the game again and do what went wrong:\n[log]\nto = logs/system.log.txt\nlevel = * error"

Chinese: "游戏仅在开启日志时写入 system.log.txt；M2EX 始终开启日志。原版游戏请在模组启动使用的 .cfg 中添加以下 [log] 设置，然后重新启动游戏并重现问题：\n[log]\nto = logs/system.log.txt\nlevel = * error"

### eng.gamelog.known_5

Terms: ['turn']

English: "When a {b} of {a} turns into a {c} (a city made a castle or back), its buildings change by their chains' convert_to lines, here into a level {a} may not build. Check those levels' requires lines in Buildings, or the convert_to lines."

Chinese: "当 {a} 的 {b} 转换为 {c}（城市转城堡或反向转换）时，建筑按路线的 convert_to 行转换，此处转换到了 {a} 不可建造的等级。请在建筑界面检查这些等级的 requires 行或 convert_to 行。"

### eng.mapcheck.second_port_pixel

Terms: ['port_verb']

English: "a second port pixel at {x},{y}. Only one of them will ever be a port."

Chinese: "{x},{y} 处有第二个港口像素。只有其中一个会成为港口。"

### eng.mapcheck.second_port_pixel_for_owner

Terms: ['port_verb']

English: "a second port pixel at {x},{y}, for {owner}. Only one of them will ever be a port."

Chinese: "{owner} 在 {x},{y} 处有第二个港口像素。只有其中一个会成为港口。"

### eng.mapcheck.starts_with_a_and_map_regions

Terms: ['port_verb']

English: "{reg} starts with a `{name}` and map_regions.tga has no white port pixel anywhere in it. The building has nowhere to stand."

Chinese: "{reg} 开局有 `{name}`，但 map_regions.tga 中没有任何白色港口像素。该建筑无处放置。"

### eng.mapcheck.the_port_pixel_at_has_no

Terms: ['port_verb']

English: "The port pixel at {x},{y} ({who}) has no sea tile on any of its four sides, so nothing can ever dock there and no province can be given the port."

Chinese: "{x},{y} 处的港口像素（{who}）四周均无海洋图块，因此无法停靠，也无法将此港口分配给任何行省。"

### eng.mapcheck.the_port_pixel_at_touches_no

Terms: ['port_verb']

English: "The port pixel at {at},{at2} touches no single region the cardinal rule can give it to, so which province gets the port is whatever the engine decides."

Chinese: "{at},{at2} 处的港口像素未接触可按四向规则明确分配的单一地区，因此所属行省由引擎自行决定。"

### eng.mapcheck.the_river_crossing_at_is_at

Terms: ['level']

English: "The river crossing at {x},{y} is at height {h}, and the land in the 5x5 tiles around it averages {mean:.0f}, {x2:.0f} {side} it. A battle here is built on that average, so the bridge does not meet its banks and the battle map can be unplayable. Smooth levels the ground around the crossing and eases it back into the hills."

Chinese: "{x},{y} 处的河流渡口高度为 {h}，周围 5x5 图块的平均陆地高度为 {mean:.0f}，比它{side} {x2:.0f}。战斗按该平均高度生成，因此桥梁无法与两岸衔接，战斗地图可能无法游玩。平滑会整平渡口附近地面，并逐渐过渡到丘陵。"

### eng.mapfe.the_frame_at_x_g_y

Terms: ['frame']

English: "the frame at ({x:g},{y:g}) {w:g}x{h:g} does not touch the {gw}x{gh} grid"

Chinese: "位于 ({x:g},{y:g})、大小为 {w:g}x{h:g} 的取景框未接触 {gw}x{gh} 网格"

### eng.mapfe.the_frame_is_w_g_x

Terms: ['frame']

English: "the frame is {w:g}x{h:g} tiles"

Chinese: "取景框为 {w:g}x{h:g} 个图块"

### eng.mapfe.the_frame_is_w_g_x_2

Terms: ['frame']

English: "the frame is {w:g}x{h:g} tiles, and fewer than {MIN_TILES} a side is not a picture of anything"

Chinese: "取景框为 {w:g}x{h:g} 个图块，每边少于 {MIN_TILES} 个无法形成有意义的图片"

### eng.mapnewreal.land_and_sea_from_the_real

Terms: ['level']

English: "land and sea from the real ground: {sum:,} of {x:,} tiles above sea level"

Chinese: "根据真实地面生成陆地和海洋：{x:,} 个图块中有 {sum:,} 个高于海平面"

### eng.mapnewreal.province_s_grown_from_their_cities

Terms: ['port_verb']

English: "{seats_n} province(s) grown from their cities over the land, {ports} with a port on the coast"

Chinese: "从城市向周围陆地扩展生成 {seats_n} 个行省，其中 {ports} 个在海岸拥有港口"

### eng.minorfiles.this_cultures_port_ladder_has_lines

Terms: ['port_verb']

English: "this culture's port ladder has {ports_n} lines and the edit sent {values_n} - adding or removing a port level is done in the code view"

Chinese: "此文化的港口阶梯有 {ports_n} 行，而编辑提交了 {values_n} 行；请在代码视图添加或移除港口等级"

### eng.modeldb.characters_left_over_after_the_entry

Terms: ['character']

English: "{x} characters left over after the entry"

Chinese: "条目后还剩 {x} 个字符"

### eng.namekeys.this_mod_ships_only_strings_bin

Terms: ['ship']

English: "this mod ships only {name}.strings.bin, so the keys go straight into the compiled archive"

Chinese: "此模组仅提供 {name}.strings.bin，因此键直接写入编译归档"

### eng.osmmap.openstreetmap_is_off_turn_it_on

Terms: ['turn']

English: "OpenStreetMap is off. Turn it on under Settings, Real-world map, first. Nothing was sent."

Chinese: "OpenStreetMap 已关闭。请先在设置的现实世界地图部分开启。未发送任何内容。"

### eng.regiondel.already_has_a_port_of_its

Terms: ['port_verb']

English: "{heir} already has a port of its own, so keeping this one leaves two port pixels in one province and the engine uses one of them. Check reports that as a second port."

Chinese: "{heir} 已有自己的港口，保留此港口会使同一行省有两个港口像素，引擎只使用其中一个。检查面板会将其报告为第二个港口。"

### eng.regiondel.s_go_with_the_section_because

Terms: ['heir']

English: "{rel}: {x} {kind}(s) go with the section, because there was no heir to file them under"

Chinese: "{rel}：{x} 个{kind}随此部分一并移除，因为没有接收行省可供归入"

### eng.regiondel.the_region_section_and_its_fort

Terms: ['heir']

English: "{rel}: the `region {name}` section and its {kept_n} fort or watchtower line(s) go with it, because there is no heir to move them to"

Chinese: "{rel}：`region {name}` 地区部分及其 {kept_n} 行要塞或瞭望塔一并移除，因为没有接收行省可供转移"

### eng.scriptwords.addon_help_recruit_order_a577

Terms: ['siege']

English: "A town's recruitment panel in a fixed order: infantry, then archers / slingers / skirmishers, cavalry, horse archers, chariots, elephants, war dogs and pigs, siege, ships - in each kind the dearest first (or the cheapest). The game sorts the panel itself by each unit's custom-battle price (stat_cost's 6th number); during your turn the add-on gives every unit that number in the order above and puts the real numbers back before every battle and at the end of your turn, so the computer's turns, battles and autoresolve keep the real values. Nothing is written into the mod's files or the saved game. Ships always stand after the land units and agents last - the game keeps them apart; in Medieval II the game's own kind blocks are switched off (a setting). Console: sq ::recruit_order_list(), sq ::recruit_order_off()."

Chinese: "按固定顺序排列城镇招募面板：步兵、弓箭手 / 投石兵 / 散兵、骑兵、骑射手、战车、大象、战犬和猪、攻城器械、船只；同类中最贵在前（或最便宜在前）。游戏本身按部队自定义战斗价格（stat_cost 的第六个数字）排序；附加组件在你的回合中按上述顺序临时赋值，在每场战斗前及你的回合结束时恢复真实数值，因此电脑回合、战斗和自动结算均保留真实数值。不写入模组文件或存档。船只始终排在陆军后，特工最后，因为游戏将它们分开；Medieval II 会关闭游戏自身的类别分块（一项设置）。控制台：sq ::recruit_order_list()、sq ::recruit_order_off()。"

### eng.scriptwords.event_town_rebels_0728

Terms: ['rebel']

English: "a town rebels"

Chinese: "城镇叛乱"

### eng.scriptwords.setting_help_avoid_growth_ag_offset_x_36c9

Terms: ['unit']

English: "in the game's 1024 x 768 units; below 0 = left"

Chinese: "使用游戏的 1024 x 768 坐标单位；小于 0 表示向左"

### eng.server.the_frame_is_not_four_numbers

Terms: ['frame']

English: "the frame is not four numbers"

Chinese: "取景框不是四个数字"

### eng.stratcamp.is_not_a_word_the_engine

Terms: ['ship']

English: "{name} is not a word the engine reads - the one it reads is marian_reforms_disabled - so this line does nothing. Third Age Reforged ships it too"

Chinese: "{name} 不是引擎读取的词；引擎读取 marian_reforms_disabled，因此此行无作用。Third Age Reforged 也包含此行"

### eng.stratedit.stays_on_the_map_with_no

Terms: ['ship']

English: "{region} stays on the map with no settlement in it. Vanilla ships one like that (Durazzo); Health lists such a province as a note."

Chinese: "{region} 保留在地图上，但没有定居点。原版也有此类行省（Durazzo）；健康检查将其列为说明。"

### eng.stratedit.two_levels_of_stand_in_this

Terms: ['ship']

English: "Two levels of {x} stand in this settlement at once. Third Age Reforged ships four settlements like it, so it is not fatal, but only one of them is the building."

Chinese: "此定居点同时有 {x} 的两个等级。Third Age Reforged 有四个定居点如此，因此并非致命问题，但只有其中一个会作为该建筑生效。"

### eng.stratobj.is_pixel_none_of_the_800_port

Terms: ['port_verb']

English: "{gx},{gy} is {name}'s port pixel. None of the 800 forts and watchtowers measured stands on a settlement or a port."

Chinese: "{gx},{gy} 是 {name} 的港口像素。所测 800 个要塞和瞭望塔均未位于定居点或港口上。"

### eng.stratobj.is_pixel_none_of_the_800_settlement

Terms: ['port_verb']

English: "{gx},{gy} is {name}'s settlement pixel. None of the 800 forts and watchtowers measured stands on a settlement or a port."

Chinese: "{gx},{gy} 是 {name} 的定居点像素。所测 800 个要塞和瞭望塔均未位于定居点或港口上。"

### eng.stringsbin.a_single_string_cannot_exceed_65535

Terms: ['character']

English: "a single string cannot exceed 65535 characters (this one is {units})"

Chinese: "单个字符串不能超过 65535 个字符（此项为 {units}）"

### eng.stringsbin.a_string_says_it_is_characters

Terms: ['character']

English: "a string says it is {units} characters long but only {x} are left in the file"

Chinese: "字符串声明长度为 {units} 个字符，但文件仅剩 {x} 个"

### eng.transfer.siege_engine_file_s_exist_in_the_destination_keeping

Terms: ['siege']

English: "{diff_engine_n} SIEGE-ENGINE file(s) exist in the destination with different content: {names}. Keeping the destination's versions (the engine may render with the destination's skin) - engine files cannot be relocated because each mesh has its texture paths baked into the binary."

Chinese: "目标中已有 {diff_engine_n} 个内容不同的攻城器械文件：{names}。保留目标版本（器械可能显示目标外观）；器械文件无法迁移，因为每个网格的贴图路径已嵌入二进制文件。"

### eng.transfer.siege_engine_file_s_exist_in_the_destination_overwriting

Terms: ['siege']

English: "{diff_engine_n} SIEGE-ENGINE file(s) exist in the destination with different content: {names}. OVERWRITING them, which also re-skins the destination's OWN engines that share these files."

Chinese: "目标中已有 {diff_engine_n} 个内容不同的攻城器械文件：{names}。将覆盖它们，同时也会更改目标中共用这些文件的现有器械外观。"

### eng.transfer.siege_engine_has_no_entry_in

Terms: ['siege']

English: "siege engine '{name}' ({field_key}) has no entry in the source {filename} - the destination will have a dangling engine reference."

Chinese: "来源 {filename} 中没有攻城器械 '{name}'（{field_key}）的条目，目标将留下悬空的器械引用。"

### eng.winconds.could_not_be_read_the_stock

Terms: ['ship']

English: "{rel} could not be read ({exc}). The stock game ships it on disk and so do both installed mods, so a campaign without one is a campaign nobody can win"

Chinese: "无法读取 {rel}（{exc}）。原版游戏和两个已安装模组均在磁盘提供此文件，没有它的战役将无人能够获胜"

### facaudit.world_maps_campaign

Terms: ['campaign']

English: "world/maps/campaign/{camp}/{rel}"

Chinese: "world/maps/campaign/{camp}/{rel}"

### factions.bring_art

Terms: ['frame']

English: "Bring its art - symbols, banners, captain cards and unit card folders, in place of the frame's"

Chinese: "转入其图片，包括标志、旗帜、队长卡片和部队卡片文件夹，以替换基础派系的对应内容"

### factions.bring_frame_units

Terms: ['frame']

English: "Keep the frame faction's units as well"

Chinese: "同时保留基础派系的部队"

### guided.armour_upgrade_models_outnumber_levels

Terms: ['trigger']

English: "<b>{models}</b> upgrade model(s) but only <b>{levels}</b> level(s). The tiers past the last level have nothing to trigger them."

Chinese: "有 <b>{models}</b> 个升级模型，但只有 <b>{levels}</b> 个等级。最后一个等级之后的层级没有条件可激活。"

### guided.close

Terms: ['close']

English: "Close ↔"

Chinese: "横向密集 ↔"

### guided.close_2

Terms: ['close']

English: "Close ↕"

Chinese: "纵向密集 ↕"

### guided.florins_the_smith_charges_to_upgrade

Terms: ['charge']

English: "Florins the smith charges to upgrade its weapons."

Chinese: "铁匠升级武器收取的弗罗林。"

### guided.florins_the_smith_charges_to_upgrade_2

Terms: ['charge']

English: "Florins the smith charges to upgrade its armour."

Chinese: "铁匠升级盔甲收取的弗罗林。"

### guided.infantry_cavalry_siege_ship_handler

Terms: ['infantry', 'cavalry', 'siege', 'ship']

English: "infantry | cavalry | siege | ship | handler"

Chinese: "infantry | cavalry | siege | ship | handler"

### guided.light_heavy_missile_spearmen

Terms: ['missile']

English: "light | heavy | missile | spearmen"

Chinese: "light | heavy | missile | spearmen"

### guided.no_sidearm_is_one_exact_line_0

Terms: ['header']

English: "\"No sidearm\" is one exact line: <code>0, 0, no, 0, 0, no, melee_simple, blunt, none, 25, 1</code>. The button in this card’s header writes it."

Chinese: "“无副武器”必须使用这一整行：<code>0, 0, no, 0, 0, no, melee_simple, blunt, none, 25, 1</code>。此卡片标题栏中的按钮可写入该行。"

### guided.optional_the_effect_played_when_the_weapon

Terms: ['turn']

English: "Optional. The effect played when the weapon <i>fires</i>: <code>musket_shot_set</code> for gunpowder units, and essentially nothing else. Setting it is what turns this line from 11 values into 12; clearing it turns it back."

Chinese: "可选。武器<i>开火</i>时播放的效果：火药部队使用 <code>musket_shot_set</code>，其他部队基本不使用。设置此项会让这一行从 11 个值变为 12 个；清除后会变回 11 个。"

### guided.optional_the_formation_the_unit_can_toggle

Terms: ['wall']

English: "Optional. The formation the unit can toggle into: <code>phalanx</code> (a spear wall, which needs <code>long_pike</code> on the primary weapon), <code>schiltrom</code>, <code>shield_wall</code>, <code>testudo</code> or <code>wedge</code>."

Chinese: "可选。部队可以切换到的阵型：<code>phalanx</code>（长矛阵，主武器需要带有 <code>long_pike</code>）、<code>schiltrom</code>、<code>shield_wall</code>、<code>testudo</code> 或 <code>wedge</code>。"

### guided.the_defence_of_the_attached_artillery

Terms: ['artillery']

English: "The defence of the attached artillery piece, wagon or animal."

Chinese: "附属火炮、车辆或动物的防御。"

### guided.the_siege_engine_this_crew_operates

Terms: ['siege']

English: "The siege engine this crew operates, from <code>descr_engines.txt</code>."

Chinese: "此操作组使用的攻城器械，取自 <code>descr_engines.txt</code>。"

### guided.vanilla_ships_it_commented_out

Terms: ['ship']

English: "Vanilla ships it commented out."

Chinese: "原版中这一行处于注释状态。"

### guided.vanilla_ships_it_commented_out_on

Terms: ['ship']

English: "Vanilla ships it commented out on every unit."

Chinese: "原版在每个部队中都将这一行注释掉。"

### guided.with_two_formations_the_first_must

Terms: ['horde']

English: "With two formations the first must be <b>square</b> or <b>horde</b>."

Chinese: "设置两种阵型时，第一种必须是 <b>square</b> 或 <b>horde</b>。"

### home.mounted_pack

Terms: ['mount']

English: "📦 mounted pack"

Chinese: "📦 已挂载的数据包"

### home.pick_your_medieval_ii_folder_it

Terms: ['mod']

English: "Pick your Medieval II folder (it contains \"mods\")"

Chinese: "选择你的 Medieval II 文件夹（其中包含 \"mods\"）"

### map3d.building_the_mesh

Terms: ['building']

English: "Building the mesh…"

Chinese: "正在构建网格…"

### map3d.frame_the_whole_map_again

Terms: ['frame']

English: "Frame the whole map again"

Chinese: "重新将整个地图纳入视野"

### mapcheck.clear_the_baseline_confirm

Terms: ['block']

English: "Clear the baseline?\n\nEvery finding already in this mod goes back to being one the toolkit will block a save on."

Chinese: "清除基准？\n\n此模组中所有原有问题将再次作为工具阻止保存的依据。"

### mapcheck.no_baseline_every_fatal_finding_here

Terms: ['block']

English: "No baseline. Every fatal finding here blocks a save, including the ones\n         that came with the mod."

Chinese: "没有基准。此处每个致命问题均会阻止保存，\n         包括模组原有问题。"

### mapcheck.of_these_were_already_in_when

Terms: ['block']

English: "of these were already in {mod} when the baseline was stamped on {baseline_at}. They are shown, and they do not block a save."

Chinese: "项在 {baseline_at} 建立基准时已存在于 {mod}。这些问题仍显示，但不会阻止保存。"

### mapfe.before_this_panel_the_picture_was

Terms: ['frame']

English: "Before this panel the picture ({was}) was squeezed into {grid} and scaled again to get onto the canvas. It is now drawn at its own size on the frame below, so nothing resamples it."

Chinese: "使用此面板前，图片（{was}）先压缩到 {grid}，再缩放到画布。现在按原尺寸绘制在下方范围框上，不再进行重采样。"

### mapfe.proposed_frame

Terms: ['frame']

English: "↺ Proposed frame"

Chinese: "↺ 建议范围框"

### mapfe.put_the_frame_back_to_the

Terms: ['frame']

English: "put the frame back to the proposed one"

Chinese: "将范围框恢复为建议位置"

### mapfe.the_frame

Terms: ['frame']

English: "the frame"

Chinese: "范围框"

### mapfe.the_frame_2

Terms: ['frame']

English: "<span>The frame</span> <span class=\"count\" id=\"cfeFigs\">{cfeFigureText}</span>"

Chinese: "<span>范围框</span> <span class=\"count\" id=\"cfeFigs\">{cfeFigureText}</span>"

### mapfe.the_frame_is_which_rectangle_of

Terms: ['frame']

English: "The frame is which rectangle of the map the picture is a picture of. It starts as the smallest one the picture's shape can be and still hold the whole map; drag it or its corners to move it, and the shape is held because that is what lets one zoom draw the picture 1:1. Nothing can work it out from the picture - one installed mod's has a painted border round the map and two are not maps at all."

Chinese: "范围框表示图片对应地图的哪个矩形区域。初始采用符合图片比例且能容纳整个地图的最小矩形，拖动矩形或角点可调整位置，并保持比例，使图片能以 1:1 显示。无法从图片自动推断：一个已安装模组的地图有绘制边框，另有两个图片根本不是地图。"

### mapfe.the_front_end_layer_is_not

Terms: ['frame']

English: "The front-end layer is not ticked, so the picture is not on the canvas - the frame is. Key <b>1</b> ticks it."

Chinese: "未勾选前端图层，因此画布只显示范围框，不显示图片。按 <b>1</b> 勾选。"

### maplabels.character

Terms: ['character']

English: "character:{line}"

Chinese: "character:{line}"

### maplabels.port

Terms: ['port_verb']

English: "port:{region}"

Chinese: "port:{region}"

### maplabels.port_2

Terms: ['port_verb']

English: "Port · {x}"

Chinese: "港口 · {x}"

### mapquery.building_that_map

Terms: ['building']

English: "building that map"

Chinese: "正在构建地图"

### mapsize.turn_the_real_world_switch_on

Terms: ['turn']

English: "Turn the Real world switch on in Settings first."

Chinese: "请先在设置中开启真实世界功能。"

### minorfiles.port_ladder_line_s_in_the

Terms: ['port_verb']

English: "Port ladder <span class=\"count\">{ports_n} line(s), in the file's own order: each port level is a <code>port_land</code> and a <code>port_sea</code> model. Adding or removing a level is a pair of lines placed in that order, so it is done in the code view; what each line points at is here.</span>"

Chinese: "港口等级 <span class=\"count\">{ports_n} 行，保留文件自身顺序：每个港口等级由 <code>port_land</code> 和 <code>port_sea</code> 模型组成。添加或移除等级需按顺序放置一对行，请在代码视图中操作；各行的引用目标可在此编辑。</span>"

### minorfiles.this_culture_has_no_port_lines

Terms: ['port_verb']

English: "This culture has no port lines."

Chinese: "此文化没有港口行。"

### minorfiles.where_it_starts_every_regions_religions

Terms: ['ship']

English: "Where it starts <span class=\"count\">Every region's <code>religions { … }</code> line gets <code>{name} 0</code>, in every descr_regions.txt this mod ships. A share given here comes out of the region's other religions in proportion, so each line still adds up to 100.</span>"

Chinese: "起始分布 <span class=\"count\">此模组包含的每个 descr_regions.txt 中，每个地区的 <code>religions { … }</code> 行均会添加 <code>{name} 0</code>。此处指定的比例会按比例从该地区的其他宗教扣除，使每行总和仍为 100。</span>"

### osmmap.mylaes_layout_the_maps_layers_as

Terms: ['port_verb']

English: "Mylae’s layout: the map’s layers as they are on disk, bbox_coords.txt, and reference/ with map_regions.txt (each province’s colour, city and port), the historic sites already fetched for this box, and the picture. Only the picture uses the internet."

Chinese: "Mylae 的布局：磁盘上的原始地图图层、bbox_coords.txt，以及 reference/ 中的 map_regions.txt（各行省的颜色、城市和港口）、已为此边界框获取的历史地点和图片。只有图片会使用互联网。"

### osmmap.open_settings_to_turn_it_on

Terms: ['turn']

English: "⚙ Open Settings to turn it on"

Chinese: "⚙ 打开设置以启用"

### osmmap.the_style_above_cut_to_the

Terms: ['frame']

English: "The style above, cut to the box and turned with it, in the map’s own frame: a reference to paint from in another program."

Chinese: "采用上方样式，裁切到边界框并随其旋转，使用地图自身的画面范围，可在其他程序中作为绘制参考。"

### osmworld.drag_to_pan_wheel_to_zoom

Terms: ['turn']

English: "Drag to pan, wheel to zoom. Drag the box's corners to resize it, its middle to move it, the violet handle to turn it."

Chinese: "拖动平移，滚轮缩放。拖动边界框角点调整大小，拖动中间移动，拖动紫色手柄旋转。"

### packs.battle_model_entr_travel_with_them

Terms: ['mount']

English: {"one": "{count} battle-model entry travels with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer.", "other": "{count} battle-model entries travel with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer."}

Chinese: {"other": "同时包含 {count} 个战斗模型条目。导入会将包挂载为来源模组，并打开普通转移界面，在那里处理名称冲突、基础部队、归属及其他选项。点击转移前不会写入任何内容。"}

### rawtext.pick_a_file_on_the_left

Terms: ['model']

English: "Pick a file on the left.<br> <span class=\"count\">The screens beside this one edit these files record by record, and each of them keeps what it does not understand. This is for the line none of them models.</span>"

Chinese: "在左侧选择文件。<br> <span class=\"count\">旁边的界面按记录编辑这些文件，各自会保留无法解析的内容。此处用于编辑它们都未提供专门功能的行。</span>"

### rebels.of_provinces_name_a_rebel_faction

Terms: ['turn']

English: "{silent_regions} of {regions} provinces name a rebel faction with <code>chance 0</code>, so they spawn no rebels. That is a real setting rather than a fault - it is how a mod turns province rebels off - but it is what those assignments do."

Chinese: "{regions} 个行省中，有 {silent_regions} 个引用了 <code>chance 0</code> 的叛军派系，因此不会生成叛军。这是模组关闭行省叛军的有效设置，并非问题；此处说明这些分配的实际效果。"

### regiondel.already_has_a_port_and_only

Terms: ['port_verb']

English: "{heir} already has a port, and only one of two in a province is\n         ever used - so removing this one is the answer that leaves a map the\n         validator does not report."

Chinese: "{heir} 已有港口，而同一行省中的两个港口只会使用其中一个，\n         因此移除此港口可使地图\n         不再产生对应验证问题。"

### regiondel.has_no_port_of_its_own

Terms: ['port_verb']

English: "{heir} has no port of its own, so keeping this one gives it a\n         harbour on the coast it is about to inherit."

Chinese: "{heir} 没有自己的港口，保留此港口\n         可使其在即将接收的海岸上获得港口。"

### regiondel.its_port

Terms: ['port_verb']

English: "<span class=\"cmtnm\">Its port</span> <span class=\"cmseg\">"

Chinese: "<span class=\"cmtnm\">其港口</span> <span class=\"cmseg\">"

### regiondel.the_heir

Terms: ['heir']

English: "the heir"

Chinese: "接收行省"

### settings.and_more_characters_in_the_diagnostic

Terms: ['character']

English: "…and {summary_cut} more characters, in the diagnostic log."

Chinese: "…另有 {summary_cut} 个字符，详见诊断日志。"

### settings.start_the_soldier_row_on_base

Terms: ['building']

English: "Start the <b>Soldier</b> row on <b>Base</b>, so the destination unit's model and projectile are used instead of the transferred unit's. Applies to both modes that have a base unit: building a new unit on one, and replacing one (there the base <i>is</i> the unit being replaced, so its own model and animations stay). Still switchable per unit."

Chinese: "<b>士兵</b>行默认选择 <b>基础</b>，以使用目标部队的模型和投射物，替代转移来的部队的对应内容。适用于两种使用基础部队的模式：基于现有部队创建新部队，以及替换部队（后一种模式中，基础部队<i>就是</i>被替换的部队，因此会保留其模型和动画）。仍可为每个部队单独切换。"

### settlemech.level

Terms: ['level']

English: "level/{name}/{x}"

Chinese: "level/{name}/{x}"

### soundbanks.has_no_data_the_game_uses

Terms: ['ship']

English: "{src} has no <code>data/{rel}</code>.<br><span class=\"count\">The game uses its own {label} when a mod does not ship them.</span>"

Chinese: "{src} 没有 <code>data/{rel}</code>。<br><span class=\"count\">模组未提供时，游戏使用自带的{label}。</span>"

### sprites.the_bypass_flag_makes_the_next_normal

Terms: ['turn']

English: "The bypass flag makes the next normal launch re-render instead of starting, which reads as a crash. Turn it back off when you are done."

Chinese: "绕过标志会使下次正常启动改为重新渲染，表现得像崩溃。完成后请将其关闭。"

### sprites.this_mod_ships_m2tweop_so_generation

Terms: ['ship']

English: "This mod ships M2TWEOP, so generation goes through its console."

Chinese: "此模组包含 M2TWEOP，生成将使用其控制台。"

### sprites.turn_the_flag_back_off

Terms: ['turn']

English: "Turn the flag back off"

Chinese: "重新关闭标志"

### stratcamp.faction_bik

Terms: ['faction']

English: "faction/{x}.bik"

Chinese: "faction/{x}.bik"

### stratmap.draw_a_campaign_map_model_beside

Terms: ['ship']

English: "Draw a campaign-map model beside the list, without leaving it. Every entry\nthat ships a .CAS gets its own 🧊 button once this is open, and the panel also browses\nevery model file under data/models_strat - including the settlements, which no entry names."

Chinese: "在列表旁显示战役地图模型，无需离开列表。打开后，\n每个包含 .CAS 的条目都会显示 🧊 按钮，面板也可浏览\ndata/models_strat 下的所有模型文件，包括未被条目引用的定居点。"

### stratmap.file_named_by_no_model_but

Terms: ['turn']

English: {"one": "{count} file is named by no model, but its bare filename turns up in a <code>descr_*.txt</code> or a script - so it is not offered above either.", "other": "{count} files are named by no model, but their bare filename turns up in a <code>descr_*.txt</code> or a script - so they are not offered above either."}

Chinese: {"other": "{count} 个文件未被模型引用，但其文件名出现在 <code>descr_*.txt</code> 或脚本中，因此也不在上方提供移除选项。"}

### stratview.this_mod_ships_no_data_models

Terms: ['ship']

English: "this mod ships no <code>data/models_strat</code>, so it uses the game's own strat models"

Chinese: "此模组没有 <code>data/models_strat</code>，因此使用游戏自带的战略模型"

### transfer.merc_icons_off

Terms: ['mercenary']

English: "<b>Off (default):</b> a copy in every faction folder the unit is owned by, plus the merc folders as a fallback. No pinning needed."

Chinese: "<b>关闭（默认）：</b>在部队所属的每个派系文件夹中保存一份，并在 merc 文件夹中保存备用副本。无需固定路径。"

### transfer.merc_icons_on

Terms: ['mercenary']

English: "<b>On:</b> cards go to the merc folders only, pinned with <code>card_pic_dir</code> / <code>info_pic_dir</code>."

Chinese: "<b>开启：</b>卡片仅存入 merc 文件夹，使用 <code>card_pic_dir</code> / <code>info_pic_dir</code> 固定路径。"

### transfer.put_the_unit_card_and_info

Terms: ['mercenary']

English: "Put the unit card and info card in the merc folders ONLY"

Chinese: "部队卡片和信息卡片仅存入 merc 文件夹"

### v3anim.building_the_glb

Terms: ['building']

English: "Building the .glb…"

Chinese: "正在生成 .glb…"

### v3anim.building_the_obj_zip

Terms: ['building']

English: "Building the .obj zip…"

Chinese: "正在生成 .obj 压缩包…"

### v3anim.played_from_vanillas_pack_this_mod

Terms: ['ship']

English: "Played from vanilla’s pack: this mod ships none of its own to save an edit into."

Chinese: "从原版包播放：此模组没有自己的包，无法将编辑保存其中。"

### v3anim.turn_every_key

Terms: ['turn']

English: "<span>Turn, every key</span> {x}°"

Chinese: "<span>旋转所有关键帧</span> {x}°"

### v3anim.turns_to

Terms: ['turn']

English: " · turns {turn}° to {turn2}°"

Chinese: " · 从 {turn}° 旋转到 {turn2}°"

### v3anim.vanillas_skeleton_pack_this_mod_ships

Terms: ['ship']

English: "vanilla’s skeleton pack (this mod ships none, so the game plays vanilla’s)"

Chinese: "原版骨架包（此模组未提供自己的骨架包，因此游戏使用原版包）"

### viewer3d.art_starts_over_second

Terms: ['unit']

English: "where the art starts over - every second unit of u"

Chinese: "图案重新开始的位置，每隔 2 个 u 单位重复"

### viewer3d.art_starts_over_unit

Terms: ['unit']

English: "where the art starts over - every unit of u"

Chinese: "图案重新开始的位置，每隔 1 个 u 单位重复"

### viewer3d.drag_to_turn_wheel_to_zoom

Terms: ['turn']

English: "drag to turn · wheel to zoom · right-drag to pan"

Chinese: "拖动旋转 · 滚轮缩放 · 右键拖动平移"

### viewer3d.draw_the_texture_at_the_size

Terms: ['ship']

English: "Draw the texture at the size the mod ships it, instead of halving anything over\n1024. That is the size the game draws, so it is the one to check a skin's own detail\nagainst. Off by default: a 2048 sheet is four times the bytes and the video memory\nfor a soldier on screen a few hundred pixels tall."

Chinese: "按模组提供的原始尺寸绘制贴图，不再将超过\n1024 的贴图缩小一半。这与游戏的绘制尺寸一致，可据此检查外观本身的细节。\n默认关闭：屏幕上只有几百像素高的士兵，使用 2048 贴图时，\n数据量和显存占用会变为四倍。"

### viewer3d.drawn_at_shipped

Terms: ['ship']

English: "drawn at <b>{w} × {h}</b> - the size the mod ships, as the game draws it"

Chinese: "以 <b>{w} × {h}</b> 绘制，与模组提供和游戏绘制的尺寸一致"

### viewer3d.in_game_units

Terms: ['unit']

English: "{x} × {x2} × {x3} in game units"

Chinese: "{x} × {x2} × {x3}（游戏单位）"

### voices.no_name_call

Terms: ['general']

English: "No name call of its own in the voice bank; it says its class's general line."

Chinese: "语音库中没有专属名称喊声，使用此类别的通用语音。"

### voices.own_compiled

Terms: ['event']

English: "The mod's compiled data/sounds/events.dat and events.idx are removed (backed up); the game builds them again on its next start."

Chinese: "将移除模组编译后的 data/sounds/events.dat 和 events.idx（会备份），游戏下次启动时会重新生成。"

### voices.own_note

Terms: ['event']

English: "Pick the accent and class it is for and one or more .wav files (the game's own are 22050 Hz, 16-bit, mono). They go in as loose files under new names, the unit gets its own line for that accent and class, and the compiled events.dat and events.idx are removed so the game rebuilds them."

Chinese: "选择适用口音和类别，以及一个或多个 .wav 文件（游戏原文件为 22050 Hz、16 位、单声道）。文件将以新名称作为散装文件写入，部队会获得此口音和类别的专属行，并移除编译后的 events.dat 与 events.idx，让游戏重新生成。"
