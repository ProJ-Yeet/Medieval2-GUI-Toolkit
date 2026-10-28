# Turkish draft review, 2026-10-28

Phase 88l is complete as a draft: 9,633/9,633 IDs, including 379 plural objects.
No missing, stale or extra IDs. Full structural/termbase checker: zero problems.
Promoted through i18n_todo.py, offered as Türkçe (Turkish) - taslak.

## Translation method and limits

This is a machine-assisted draft, not a native-speaker-reviewed translation.
The first shared controls, Home, startup text, Settings, main navigation,
repair guidance and selected map/animation text were authored or corrected
directly. Bulk text was drafted with Google Translate, preserving source
tokens, then compared across candidates and held to the checked merger.
Translation memories, candidate provenance and manual corrections remain in
.cache/tr-*.json and .cache/tr-*.py. No translation service is used by the app.

The review corrected technical senses of ship (supply files), turn (rotate or
enable), mount (attach an archive), port (harbour versus bring content across),
charge (price versus combat) and building (create versus a structure).
Literal syntax, filenames, paths, products and example names stay as written.
Turkish nouns following numeric counts are singular in the manually reviewed
labels. All plural objects retain one/other, and explicit zero where supplied.

Native review is still required, especially for the bulk explanatory text,
technical word choices, agglutinative suffixes and fragments joined at runtime.
No claim is made that every sentence has received a native linguistic review.
The catalogue's draft status remains visible in Settings.

## Verification

Home, Settings, Transfer (including a unit detail drawer) and Campaign Map
were walked in the in-app browser at desktop width (1280 px); Home, Settings,
Transfer and Campaign Map were also inspected at 375 px. Accented letters and
dotted/dotless I render correctly. Labels and guidance wrap. No page-wide
horizontal overflow was found in the measured narrow views.
This is a representative screen review, not a test of every dialog or save.
No mod files were written. The temporary preview keeps settings in memory,
so the user's saved language and beta preference are not changed by this QA.

The UI review corrected an M2TWEOP count fragment, Fit/Names/Paint labels,
port counts, map redraw descriptions and the no-region-ID-moves guidance.
The promoted picker was checked against the real shipped catalogue.

tests.test_termbase: 29/29; tests.test_i18n: 37/37;
tests.test_web_modules: 124/124. Full catalogue checker: zero problems.
No translation markers remain; placeholder occurrence counts match every
corresponding English form. Source-hash stale detection was checked with an
in-memory changed source value. No source English was changed for that check.

The checker now handles Turkish dotted/dotless I for term comparisons, with
positive and negative regression cases. Nine Turkish glossary stems were
expanded for ordinary consonant softening (e.g. başlık/başlığı and blok/bloğu).
Preferred glossary words are unchanged. The code graph was updated from the
repository root. No release was cut.

## Exact glossary exceptions

Exceptions below are confined to the named entry and listed terms. They
cover another sense, literal engine syntax, paths or illustrative values;
they do not disable structural checking. Source and translation are retained
here so a Turkish reviewer can assess them in context.

### app.shared_cards_title

Terms: tile

English: "Grouped by faction: only the tiles whose faction has no card of its own for the unit and borrows another's"

Turkish: "Fraksiyona göre gruplandırıldığında: yalnızca fraksiyonun birim için kendi kartına sahip olmayıp başka bir fraksiyondan ödünç aldığı kartları göster"

### armory.exp_free_turn_title

Terms: turn

English: "Let a block turn to whatever angle packs it smallest, as well as by quarter turns. A block turned so is resampled and its art softens slightly; off, every texel is copied exactly."

Turkish: "Bir bloğun en küçük olduğu açıya ve çeyrek dönüşe dönmesine izin verin. Bu şekilde döndürülen bir blok yeniden örneklenir ve sanatı biraz yumuşar; kapalı, her doku tam olarak kopyalanır."

### armory.head_as_one_title

Terms: turn

English: "Helmet, coif, face, hair and beard move, turn and scale together whichever of them is picked"

Turkish: "Kask, saç modeli, yüz, saç ve sakal, hangisi seçilirse seçilsin birlikte hareket eder, döner ve ölçeklenir"

### armory.look_closer_title

Terms: turn

English: "A closer look: the model in the viewer, to turn, zoom, change its skin and play its animations, before it is pulled in"

Turkish: "Daha yakından bakış: izleyicideki model, içeri çekilmeden önce döndürülebilir, yakınlaştırılabilir, dış görünümü değiştirilebilir ve animasyonları oynatılabilir"

### armory.stamp_rot

Terms: turn

English: "Turn"

Turkish: "Dönüş"

### armory.uv_hint

Terms: turn

English: "Click picks, Shift adds, a drag on nothing draws a box, a drag on the selection moves it. G, R, S move, turn and scale (X or Y holds an axis; click or Enter keeps, Esc or the right button puts back). A selects all. The wheel zooms, the middle button or Alt pans."

Turkish: "Tıklama seçer, Shift ekler, hiçbir şeyin üzerine sürüklendiğinde bir kutu çizilir, seçim üzerinde sürüklendiğinde kutu hareket eder. G, R, S hareket eder, döner ve ölçeklendirir (X veya Y bir ekseni tutar; tıklama veya Enter tutar, Esc veya sağ düğme geri koyar). A hepsini seçer. Tekerlek yakınlaştırır, orta düğme veya Alt kaydırma yapar."

### buildings.its_battle_model_has_no_texture

Terms: turn

English: "its battle model has no texture for <b>{x}</b>, so their soldiers would turn up untextured"

Turkish: "savaş modelinin <b> {x} </b> için dokusu yok, dolayısıyla askerleri dokusuz olarak ortaya çıkacak"

### buildings.level_3

Terms: level

English: "level:{name}:{x}#{x2}"

Turkish: "level:{name}:{x}#{x2}"

### buildings.level_key

Terms: level

English: "level:{name}"

Turkish: "level:{name}"

### buildings.this_mod_ships_no_file_at

Terms: ship

English: "This mod ships no file at\nthis path, so the game uses the base game's picture. Drop a .tga in to override it."

Turkish: "Bu mod hiçbir dosya göndermiyor\nBu yol, oyun temel oyunun resmini kullanır. Geçersiz kılmak için bir .tga bırakın."

### buildings.units_without_battle_model_texture

Terms: turn

English: {"one": "<b>{count}</b> has no battle-model texture for some of them, so their soldiers would turn up untextured: {list}", "other": "<b>{count}</b> have no battle-model texture for some of them, so their soldiers would turn up untextured: {list}"}

Turkish: {"one": "<b> {count} </b>'nin bazıları için savaş modeli dokusu yoktur, dolayısıyla askerleri dokusuz olarak ortaya çıkar: {list}", "other": "<b> {count} </b>'nin bazılarının savaş modeli dokusu yok, dolayısıyla askerleri dokusuz olarak ortaya çıkıyor: {list}"}

### campaint.add_a_province_decide_its_record

Terms: port_verb

English: "Add a province: decide its record, paint it, place its settlement, then its port or skip."

Turkish: "Eyalet ekleyin: kaydını belirleyin, boyayın, yerleşim yerini ve ardından limanını yerleştirin; limanı atlayabilirsiniz."

### campaint.place_the_port_pixel_or_skip

Terms: port_verb

English: "Place the port pixel, or skip it"

Turkish: "Bağlantı noktası pikselini yerleştirin veya atlayın"

### campaint.writes_layers_at_once_in_the

Terms: port_verb

English: "Writes {n} layers at once, in the colours <b>measured off this map</b>: {layers} · from {sea_tiles} sea tiles. Settlement and port pixels are left alone."

Turkish: "{n} katman'yi tek seferde, bu haritada ölçülen <b> renklerinde yazar </b> : {layers} · {sea_tiles} deniz karo'den.  yerleşim yeri ve port etmek piksel yalnız kaldı."

### campaint.written_into_a_settlement_the_music

Terms: ship

English: "Written into {reach}: a settlement, the music\n           type and, where it ships one, the name lookup - each campaign’s own\n           copy of each file."

Turkish: "{reach}'ye yazılmıştır: bir yerleşim yeri, müzik\n           yazın ve gönderildiği yerde ad araması - her kampanyanın kendine ait\n           her dosyanın kopyası."

### campbrowse.campaigns_read_in_ms

Terms: ship

English: {"one": "{count} campaign read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom.", "other": "{count} campaigns read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom."}

Turkish: {"one": "{count} kampanyası {ms} ms'de okundu. On harita katmanı ve bölge listesi, kendisine ait bir kopya göndermeyen her kampanya için <code>{base}</code> dosyasında yer alır; bunlar arasında değişen şey kimin nerede, neyle ve kime karşı başladığıdır.", "other": "{count} kampanyaları {ms} ms cinsinden okunur. On harita katmanı ve bölge listesi, kendisine ait bir kopya göndermeyen her kampanya için <code>{base}</code> dosyasında yer alır; bunlar arasında değişen şey kimin nerede, neyle ve kime karşı başladığıdır."}

### campbrowse.every_campaign_this_mod_ships_with

Terms: ship

English: "Every campaign this mod ships, with what is in each one, and which of them this screen is reading."

Turkish: "Bu modun gönderdiği her kampanya, her birinde ne olduğu ve bu ekranın hangisini okuduğuyla birlikte."

### campbrowse.nothing_in_to_read_a_menu

Terms: ship

English: "Nothing in <code>{file}</code> to read a menu title out of - this mod ships neither it nor the compiled archive beside it - so no campaign below shows one. That is the file missing, not the campaigns being unnamed."

Turkish: "<code>{file}</code>'de menü başlığını okuyacak hiçbir şey yok - bu mod ne onu ne de onun yanındaki derlenmiş arşivi gönderiyor - dolayısıyla aşağıdaki kampanyalardan hiçbirinde bir tane gösterilmiyor. Bu, kampanyaların adsız olması değil, dosyanın eksik olmasıdır."

### campbrowse.ships_map_layers

Terms: ship

English: {"one": "It ships {count} map layer of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those.", "other": "It ships {count} map layers of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those."}

Turkish: {"one": "Motorun tabanınki yerine okuduğu kendi {count} harita katmanını ({list} {more}) gönderir. Açık, bu ekran bunları çiziyor.", "other": "Motorun üssünki yerine okuduğu kendi {count} harita katmanlarını ( {list} {more} ) gönderir. Açık, bu ekran bunları çiziyor."}

### campcreate.new_region_name_paint_settlement_port

Terms: port_verb

English: "<b>＋ New region</b><small>Name → paint → settlement → port</small>"

Turkish: "<b> ＋ Yeni bölge </b> <small> Ad → boya → yerleşim → bağlantı noktası </small>"

### campcreate.port

Terms: port_verb

English: "Port"

Turkish: "Liman"

### campcreate.port_marker_add_or_move_on

Terms: port_verb

English: "<b>⚓ Port marker</b><small>Add or move on the selected region</small>"

Turkish: "<b> ⚓ Bağlantı noktası işaretleyici </b> <small> Seçilen bölgeyi ekleyin veya bu bölgede taşıyın </small>"

### campcreate.select_a_region_first_then_choose

Terms: port_verb

English: "Select a region first, then choose its settlement or port marker."

Turkish: "Önce bir bölge seçin, ardından yerleşim yerini veya liman işaretini seçin."

### campmap.building_the_composite

Terms: building

English: "building the composite…"

Turkish: "bileşim oluşturuluyor…"

### campmap.click_a_province_to_inspect_it

Terms: turn

English: "Click a province to inspect it. Turn on Paint to edit tiles; right or middle drag still pans. Choose a layer and colour on the left."

Turkish: "İncelemek için bir eyalete tıklayın. Karoları düzenlemek için Boyama özelliğini açın; sağ veya orta tuşla sürüklemek yine kaydırır. Soldan bir katman ve renk seçin."

### campmap.comp_key

Terms: terrain

English: "{layers}|terrain:{terrain}|fe:{fe}"

Turkish: "{layers}|terrain:{terrain}|fe:{fe}"

### campmap.has_no_campaign_map_this_tool

Terms: ship

English: "has no campaign map this tool can read.<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">A mod only has one if it ships <code>data/world/maps/base</code> - the terrain header, the region list and the ten TGA layers. Without them the game uses its own map, and there is nothing here to draw.</span>"

Turkish: "bu aracın okuyabileceği bir kampanya haritası yok.<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">Bir modun kendi haritası ancak <code>data/world/maps/base</code> içeriyorsa vardır: arazi başlığı, bölge listesi ve on TGA katmanı. Bunlar olmadan oyun kendi haritasını kullanır; burada çizilecek bir şey yoktur.</span>"

### campmap.port_marker

Terms: port_verb

English: "Port marker"

Turkish: "Bağlantı noktası işaretçisi"

### campmap.port_pixel

Terms: port_verb

English: "port pixel"

Turkish: "bağlantı noktası pikseli"

### campmap.port_pixels_undecided

Terms: port_verb

English: {"one": "{count} port pixel whose owning region cannot be decided", "other": "{count} port pixels whose owning region cannot be decided"}

Turkish: {"one": "Sahip olduğu bölgeye karar verilemeyen {count} bağlantı noktası pikseli", "other": "Sahip oldukları bölgeye karar verilemeyen {count} bağlantı noktası pikselleri"}

### campmap.region_id_tiles_settlement_at_game

Terms: port_verb

English: "<span>Region ID</span><b>{x}</b> <span>Tiles</span><b>{count}{x2}</b> <span>Settlement at</span><b>{x3} <span class=\"count\">game</span> · {x4} <span class=\"count\">image</span></b> <span>Port at</span><b>{x5}</b> {x6} <span>Bounding box</span><b>{x7}</b>"

Turkish: "<span> bölge ID </span> <b> {x} </b> <span> karo </span> <b> {count} {x2} </b> <span> yerleşim yeri ve </span> <b> {x3} <span class=\"count\"> oyunu </span> · {x4} <span class=\"count\"> resim </span> </b> <span> port etmek ve </span> <b> {x5} </b> {x6} <span> Sınırlama kutusu </span> <b> {x7} </b>"

### campmap.settlement_character_and_port_names_beside

Terms: port_verb

English: "Settlement, character and port names beside their markers (L), placed so that none covers another.\nA name with no room at this zoom is left off and counted; zoom in for it."

Turkish: "Yerleşim yeri, karakter ve liman adları işaretleyicilerinin (L) yanında, hiçbiri diğerini örtmeyecek şekilde yerleştirilmiştir.\nBu yakınlaştırmada yeri olmayan bir isim bırakılır ve sayılır; bunun için yakınlaştırın."

### campmap.ships_its_own_so_that_layer

Terms: ship

English: "{campaign} ships its own {own}, so that layer is drawn from <code>{folder}</code>. Everything else is <code>world/maps/base</code>, which is what the brush paints."

Turkish: "{campaign} kendine ait {own} içerir; bu katman <code>{folder}</code> içinden çizilir. Diğer tüm içerik, fırçanın boyadığı <code>world/maps/base</code> içinden gelir."

### campmap.the_campaign_map_as_a_surface

Terms: turn

English: "The campaign map as a surface. Drag to turn, right-drag to pan, scroll to zoom."

Turkish: "Bir yüzey olarak kampanya haritası. Döndürmek için sürükleyin, kaydırmak için sağa sürükleyin, yakınlaştırmak için kaydırın."

### campmap.the_heights_as_a_surface_with

Terms: turn

English: "The heights as a surface, with this map's own ground on it, orbited (D).\nDrag to turn, right-drag to pan, wheel to zoom.\nMarkers, labels and the tooltip stay on the flat map."

Turkish: "Üzerinde bu haritanın kendi zemini bulunan bir yüzey olarak yükseklikler yörüngededir (D).\nDöndürmek için sürükleyin, kaydırmak için sağa sürükleyin, yakınlaştırmak için tekerleği sürükleyin.\nİşaretçiler, etiketler ve ipucu düz haritada kalır."

### campmark.named_character_general_admiral_port_spy

Terms: port_verb

English: "♚ Named character · ⚔ General · ⚓ Admiral / port<br> ◈ Spy · ¤ Merchant · ⚑ Diplomat · ✝ Priest · † Assassin"

Turkish: "♚ İsimli karakter · ⚔ general · ⚓ Amiral / port etmek <br> ◈ Casus · ¤ Tüccar · ⚑ Diplomat · ✝ Rahip · † Suikastçı"

### campmark.port

Terms: port_verb

English: "Port · {x}"

Turkish: "Liman · {x}"

### campmark.this_mod_ships_its_own_picture

Terms: ship

English: "This mod ships its own picture for {art} of the\n        {n} trade resources here; the rest draw a glyph,\n        because the stock art is inside a .pack archive."

Turkish: "Bu mod, {art} için kendi resmini gönderir.\n         {n} burada kaynakların ticaretini yapar; geri kalanı bir glif çizer,\n        çünkü stok görsel bir .pack arşivinin içindedir."

### campnew.map_layers_note

Terms: ship

English: {"one": "It ships {count} map layer of its own, so the copy gets a copy of those too and the two are then two maps to keep in step.", "other": "It ships {count} map layers of its own, so the copy gets a copy of those too and the two are then two maps to keep in step."}

Turkish: {"one": "Kendi {count} harita katmanını gönderir, böylece kopya bunların da bir kopyasını alır ve ikisi daha sonra adım atılması gereken iki harita olur.", "other": "{count} harita katmanlarını kendi başına gönderir, böylece kopya bunların da bir kopyasını alır ve ikisi daha sonra adım atılması gereken iki harita olur."}

### campnew.this_mod_ships_only_the_compiled

Terms: ship

English: "This mod ships only the compiled archive of <code>{descriptions}</code>, which is where the keys would go."

Turkish: "Bu mod yalnızca <code>{descriptions}</code> derlenmiş arşivini gönderir; anahtarların gideceği yer burasıdır."

### cards.data_ui_units_data_ui_unit

Terms: unit

English: "data/ui/units · data/ui/unit_info"

Turkish: "data/ui/units · data/ui/unit_info"

### cards.gen_rig_hint

Terms: turn

English: "Drag the dots in the HD view: hands, feet, the pelvis and the torso move, the diamonds point the elbows and knees, the head turns."

Turkish: "HD görünümde noktaları sürükleyin: eller, ayaklar, pelvis ve gövde hareket eder, elmaslar dirsekleri ve dizleri işaret eder, baş döner."

### cards.gen_turn

Terms: turn

English: "Turn"

Turkish: "Dönüş"

### cards.gen_view_hint

Terms: turn

English: "In the HD view: middle drag turns the camera, Shift pans, the wheel zooms; G moves and R turns the model, X, Y or Z holds it to an axis, a click or Enter keeps it, Esc puts it back."

Turkish: "HD görünümünde: ortadaki sürükleme kamerayı döndürür, Shift kaydırma yapar, tekerlek yakınlaştırır; G hareket eder ve R modeli döndürür, X, Y veya Z modeli bir eksende tutar, bir tıklama veya Enter onu tutar, Esc onu geri koyar."

### cards.merc

Terms: mercenary

English: " ·&nbsp;merc"

Turkish: " ·&nbsp;merc"

### changes.turn_off

Terms: turn

English: "Turn off"

Turkish: "Kapat"

### changes.turn_off_putting_the_original_records

Terms: turn

English: "Turn \"{off}\" off, putting the original records back?"

Turkish: "Orijinal kayıtları geri koyarak \"{off}\" kapatılsın mı?"

### changes.turn_on

Terms: turn

English: "Turn \"{on}\" on?"

Turkish: "\"{on}\" açılsın mı?"

### climates.append_a_name_the_engine_does

Terms: ship

English: "Append a name the engine does not ship. The strat map draws it; the\nbattle map reads climates by name, which is what the warning is about."

Turkish: "Motorun içermediği bir ad ekleyin. Strateji haritası bunu çizer; savaş haritası ise iklimleri adlarıyla okur. Uyarı bununla ilgilidir."

### climates.taking_over_one_of_the_twelve

Terms: ship

English: "{problem} Taking over one of the twelve the engine ships needs no such check."

Turkish: "{problem} Motorun içerdiği on iki iklimden birini devralmak böyle bir kontrol gerektirmez."

### codeview.every_string_here_is_stored_as

Terms: character

English: "Every string here is stored as its own length\nfollowed by that many characters. Change a path and the number beside it has to\nchange too. This does that, and you can see it happen."

Turkish: "Buradaki her dize kendi uzunluğu olarak saklanır\nbunu bir sürü karakter takip ediyor. Bir yolu ve yanındaki numarayı değiştirin\nda değiş. Bu bunu yapar ve bunun olduğunu görebilirsiniz."

### core.every_model_a_mod_ships_the

Terms: ship

English: "Every model a mod ships: the battle entries, their sprites, the strat map’s, and the cards"

Turkish: "Modun içerdiği tüm modeller: savaş girdileri, sprite görselleri, strateji haritası modelleri ve kartlar"

### core.the_tool_did_not_finish_loading

Terms: turn

English: "The tool did not finish loading.<br> <span class=\"count\">The server is running - it answered for the rest of this page - but the browser never received {names}. Reloading fetches it again. If it fails every time, an ad blocker or privacy extension is the usual cause: turn it off for 127.0.0.1.</span>"

Turkish: "Araç tam olarak yüklenemedi.<br> <span class=\"count\">Sunucu çalışıyor ve sayfanın geri kalanına yanıt verdi; ancak tarayıcı {names} dosyalarını hiç almadı. Yeniden yüklemek onları tekrar getirir. Her seferinde başarısız oluyorsa genellikle reklam engelleyici veya gizlilik eklentisi neden olur: 127.0.0.1 için kapatın.</span>"

### core.the_two_pictures_per_unit_deduplicated

Terms: mercenary

English: "The two pictures per unit, deduplicated into the merc folder"

Turkish: "Her birim için iki resim; yinelenenler birleştirilip merc klasöründe tutulur"

### edusort.gondor_tier_2_infantry

Terms: infantry, tier

English: "GONDOR TIER 2 INFANTRY"

Turkish: "GONDOR TIER 2 INFANTRY"

### edusort.gondor_tier_2_infantry_2

Terms: infantry, tier

English: "Gondor Tier 2 Infantry"

Turkish: "Gondor Tier 2 Infantry"

### edusort.line_character

Terms: character

English: "Line character"

Turkish: "Satır karakteri"

### eng.animloose.turns_bones_and_its_skeleton_has

Terms: turn

English: "{x} turns {nq} bones and its skeleton has {bones_n}"

Turkish: "{x}, {nq} kemiklerini döndürür ve iskeletinde {bones_n} bulunur"

### eng.animpack.the_source_ships_no_packs_of

Terms: ship

English: "the source ships no packs of its own, so it plays vanilla's and they are what is ported"

Turkish: "kaynağın kendine ait bir paketi yok; bu yüzden vanilla paketlerini oynatır ve port edilenler bunlardır"

### eng.animslot.this_mod_ships_no_animation_packs

Terms: ship

English: "this mod ships no animation packs of its own (the game plays vanilla's), so there is no pack of its own to save into"

Turkish: "bu mod kendine ait animasyon paketleri içermez (oyun vanilla paketlerini oynatır); bu yüzden kaydedilecek kendine ait bir paket yok"

### eng.buildings.hidden_ceiling_note

Terms: ship

English: "TWCenter's List of Hardcoded Limits puts the ceiling at 63 or 64 and says more crash the game. Divide and Conquer ships 75 and ROCSS 74, and both play, so it is not enforced here."

Turkish: "TWCenter sabit sınırlar listesi, üst sınırı 63 veya 64 olarak verir ve daha fazlasının oyunu çökerteceğini söyler. Divide and Conquer 75, ROCSS 74 içerir ve ikisi de oynanabilir; bu yüzden bu sınır burada uygulanmaz."

### eng.campaint.is_a_marker_colour_black_is

Terms: port_verb

English: "{rgb} {rgb2} {rgb3} is a marker colour - black is where a settlement stands and white is where a port does, so neither can be a province"

Turkish: "{rgb} {rgb2} {rgb3} bir işaret rengidir - yerleşim yeri'nin durduğu yer siyah, port etmek'nin bulunduğu yerdir; dolayısıyla ikisi de eyalet olamaz"

### eng.campaint.is_not_a_marker_map_regions

Terms: port_verb

English: "{marker} is not a marker - map_regions.tga has two, the settlement and the port"

Turkish: "{marker} bir işaretçi değil - map_regions.tga'da iki tane var; yerleşim yeri ve liman"

### eng.campaint.settlement_or_port_pixels_left_alone

Terms: port_verb

English: {"one": "{count} settlement or port pixel left alone", "other": "{count} settlement or port pixels left alone"}

Turkish: {"one": "{count} yerleşim yeri veya bağlantı noktası pikseli tek başına bırakıldı", "other": "{count} yerleşim veya bağlantı noktası pikselleri tek başına bırakıldı"}

### eng.campaint.ships_own_so_it_does_not_see

Terms: ship

English: {"one": "{skipped} ships its own {REGIONS_TGA}, so it does not see these pixels and {name} does not exist there", "other": "{skipped} ship their own {REGIONS_TGA}, so they do not see these pixels and {name} does not exist there"}

Turkish: {"one": "{skipped} kendi {REGIONS_TGA}'sini gönderir, dolayısıyla bu pikselleri görmez ve {name} orada mevcut değildir", "other": "{skipped} kendi {REGIONS_TGA}'sini gönderir, dolayısıyla bu pikselleri görmezler ve {name} orada mevcut değildir"}

### eng.campevents.is_not_one_of_the_eight

Terms: ship

English: "`{kind}` is not one of the eight the engine has; the file the engine ships declares {and_list}"

Turkish: "'{kind}' motorun sahip olduğu sekiz motordan biri değil; motorun gönderdiği dosya {and_list} olarak bildiriyor"

### eng.campfiles.this_mod_ships_only_so_the

Terms: ship

English: "this mod ships only {name}, so the keys go straight into the compiled archive"

Turkish: "bu mod yalnızca {name} ile gönderilir, böylece anahtarlar doğrudan derlenmiş arşive gider"

### eng.campnew.is_not_on_disk_and_ships

Terms: ship

English: "{REGIONS_REL} is not on disk and {source} ships no map of its own, so there is no region list for this campaign to read"

Turkish: "{REGIONS_REL} diskte değil ve {source} kendine ait bir harita göndermiyor, dolayısıyla bu kampanyanın okunabileceği bir bölge listesi yok"

### eng.campnew.nothing_names_on_the_new_game_menu_archive

Terms: ship

English: "nothing names {name} on the new-game menu, so the engine shows the key {head}TITLE. {descr_rel} is where that lives and the Descriptions panel writes it. This mod ships only the compiled archive, which is where the key would go."

Turkish: "yeni oyun menüsünde hiçbir şey {name} adını vermiyor, dolayısıyla motor {head} TITLE anahtarını gösteriyor.  {descr_rel}, bunun yaşadığı ve Açıklamalar panelinin yazdığı yerdir. Bu mod yalnızca anahtarın gideceği derlenmiş arşivi gönderir."

### eng.campnew.ships_map_layer_s_of_its

Terms: ship

English: "{source} ships {layers_n} map layer(s) of its own ({layers}), so the copy gets a copy of them too and the two campaigns are then two maps to keep in step. The map screen draws whichever one the campaign you have open reads."

Turkish: "{source}, kendi {layers_n} harita katmanını/katmanlarını ({layers}) gönderir, böylece kopya da bunların bir kopyasını alır ve iki kampanya daha sonra adım adım takip edilecek iki harita haline gelir. Harita ekranı açmış olduğunuz kampanyanın hangisini okuyorsa onu çizer."

### eng.cas.w_text_latin1

Terms: character

English: "{value} has a character a .cas cannot hold (it is written in Latin-1)"

Turkish: "{value}, .cas'ın tutamayacağı bir karaktere sahiptir (Latince-1 ile yazılmıştır)"

### eng.cas.w_text_long

Terms: character

English: "a name of {n:,} characters is longer than the reader takes"

Turkish: "{n:,} karakterlerden oluşan bir ad okuyucunun alabileceğinden daha uzundur"

### eng.casanim.turns_bones_and_the_skeleton_has

Terms: turn

English: "{name} turns {nq} bones and the skeleton {x} has {bones_n}: it is another skeleton's animation"

Turkish: "{name}, {nq} kemiklerini döndürür ve {x} iskeletinde {bones_n} bulunur: bu başka bir iskeletin animasyonudur"

### eng.climatenew.a_climate_name_the_battle_map

Terms: ship

English: "{problem} A climate name the battle map does not know is a crash when a battle starts in it, so a new name is the half of this operation that cannot be checked against this mod. Taking over one of the twelve the engine ships - {SPARE} are spare by name - needs no such check."

Turkish: "{problem} Savaş haritasının tanımadığı bir iklim adı, o iklimde savaş başladığında çökmeye neden olur. Dolayısıyla yeni bir ad eklemek, bu işlemin mod üzerinden doğrulanamayan kısmıdır. Motorun içerdiği on iki iklimden birini devralmak ({SPARE} adları gereği boştadır) böyle bir kontrol gerektirmez."

### eng.climatenew.all_four_mods_measured_for_this

Terms: ship

English: "all four mods measured for this declare exactly the twelve climates the engine ships, in the engine's order, and not one added a thirteenth. Divide and Conquer has a wholly custom map and took over unused1 rather than adding a name."

Turkish: "Bunun için ölçülen dört modun tümü, motor sırasına göre motorun gönderdiği on iki iklimi tam olarak beyan ediyor ve hiçbiri on üçüncüyü eklemedi. Divide and Conquer tamamen özel bir haritaya sahiptir ve bir isim eklemek yerine kullanılmayan1 haritayı devralmıştır."

### eng.codeview.length_says_but_text_is

Terms: character

English: "line {line}'s length says {said} but the text beside it is {should} characters - every modeldb string is written `<length> <text>`"

Turkish: "{line} satırının uzunluğu {said} diyor ancak yanındaki metin {should} karakterlerden oluşuyor - her modeldb dizesi '<length> <text>' olarak yazılır"

### eng.codeview.length_says_but_text_is_and_more

Terms: character

English: "line {line}'s length says {said} but the text beside it is {should} characters (and {more} more like it) - every modeldb string is written `<length> <text>`"

Turkish: "{line} satırının uzunluğu {said} diyor ancak yanındaki metin {should} karakterleri (ve {more} buna daha çok benziyor) - her modeldb dizesi '<length> <text>' olarak yazılır"

### eng.gamelog.known_5

Terms: turn

English: "When a {b} of {a} turns into a {c} (a city made a castle or back), its buildings change by their chains' convert_to lines, here into a level {a} may not build. Check those levels' requires lines in Buildings, or the convert_to lines."

Turkish: "{a}'nin bir {b}'si bir {c}'ye (kale veya sırt yapılmış bir şehir) dönüştüğünde, binaları zincirlerinin convert_to çizgileri ile değişir, burada {a}'nin inşa edilemeyeceği bir seviyeye dönüşür. Binalardaki bu seviyelerin gerektirdiği satırları veya convert_to satırlarını kontrol edin."

### eng.heroabilities.not_in_ui_battle_sd_so

Terms: battle

English: "{owner}: {gone} not in ui/battle.sd, so the button has no picture{why}"

Turkish: "{owner}: {gone}, ui/battle.sd içinde yok; bu yüzden düğmenin resmi yok{why}"

### eng.mapcheck.second_port_pixel

Terms: port_verb

English: "a second port pixel at {x},{y}. Only one of them will ever be a port."

Turkish: "{x} , {y} adresinde ikinci bir bağlantı noktası pikseli. Bunlardan yalnızca biri liman olacak."

### eng.mapcheck.second_port_pixel_for_owner

Terms: port_verb

English: "a second port pixel at {x},{y}, for {owner}. Only one of them will ever be a port."

Turkish: "{owner} için {x}, {y} adresinde ikinci bir bağlantı noktası pikseli. Bunlardan yalnızca biri liman olacak."

### eng.mapcheck.starts_with_a_and_map_regions

Terms: port_verb

English: "{reg} starts with a `{name}` and map_regions.tga has no white port pixel anywhere in it. The building has nowhere to stand."

Turkish: "{reg}, '{name}' ile başlar ve map_regions.tga'nın hiçbir yerinde beyaz bağlantı noktası pikseli yoktur. Binanın ayakta duracak yeri yok."

### eng.mapcheck.the_port_pixel_at_has_no

Terms: port_verb

English: "The port pixel at {x},{y} ({who}) has no sea tile on any of its four sides, so nothing can ever dock there and no province can be given the port."

Turkish: "{x},{y} ({who}) adresindeki portun pikselinin dört yanından herhangi birinde deniz karosu yoktur, dolayısıyla oraya hiçbir şey yanaşamaz ve hiçbir eyalete liman verilemez."

### eng.mapcheck.the_port_pixel_at_touches_no

Terms: port_verb

English: "The port pixel at {at},{at2} touches no single region the cardinal rule can give it to, so which province gets the port is whatever the engine decides."

Turkish: "{at}'deki port etmek piksel, {at2}, ana kuralın sağlayabileceği tek bir bölge'ye dokunmaz, dolayısıyla hangi eyalet, port etmek'yi alırsa, motor ne karar verirse o olur."

### eng.mapnewreal.province_s_grown_from_their_cities

Terms: port_verb

English: "{seats_n} province(s) grown from their cities over the land, {ports} with a port on the coast"

Turkish: "{seats_n} eyalet(ler)i kendi şehirlerinden karada yetişiyor, {ports} bir limanla sahilde"

### eng.minorfiles.this_cultures_port_ladder_has_lines

Terms: port_verb

English: "this culture's port ladder has {ports_n} lines and the edit sent {values_n} - adding or removing a port level is done in the code view"

Turkish: "bu kültür 'nin port etmek merdiveninde {ports_n} satırları var ve düzenleme {values_n} gönderildi - port etmek seviye ekleme veya kaldırma kod görünümünde yapılır"

### eng.modeldb.characters_left_over_after_the_entry

Terms: character

English: "{x} characters left over after the entry"

Turkish: "Girdikten sonra kalan {x} karakteri"

### eng.namekeys.this_mod_ships_only_strings_bin

Terms: ship

English: "this mod ships only {name}.strings.bin, so the keys go straight into the compiled archive"

Turkish: "bu mod yalnızca {name} .strings.bin dosyasını gönderir, böylece anahtarlar doğrudan derlenmiş arşive gider"

### eng.osmmap.openstreetmap_is_off_turn_it_on

Terms: turn

English: "OpenStreetMap is off. Turn it on under Settings, Real-world map, first. Nothing was sent."

Turkish: "OpenStreetMap kapalı. Önce Ayarlar, Gerçek dünya haritası altında açın. Hiçbir şey gönderilmedi."

### eng.regiondel.already_has_a_port_of_its

Terms: port_verb

English: "{heir} already has a port of its own, so keeping this one leaves two port pixels in one province and the engine uses one of them. Check reports that as a second port."

Turkish: "{heir}'nin zaten kendine ait bir port etmek'si vardır, bu nedenle bunu tutmak, bir eyalet'de iki port etmek piksel bırakır ve motor bunlardan birini kullanır. Raporları ikinci bir port etmek olarak kontrol edin."

### eng.scriptwords.setting_help_avoid_growth_ag_offset_x_36c9

Terms: unit

English: "in the game's 1024 x 768 units; below 0 = left"

Turkish: "oyunun 1024 x 768 birimlerinde; 0'ın altında = sol"

### eng.stratcamp.is_not_a_word_the_engine

Terms: ship

English: "{name} is not a word the engine reads - the one it reads is marian_reforms_disabled - so this line does nothing. Third Age Reforged ships it too"

Turkish: "{name}, motorun okuduğu bir kelime değildir - okuduğu marian_reforms_disabled'dır - dolayısıyla bu satır hiçbir şey yapmaz. Third Age Reforged da bunu gönderiyor"

### eng.stratedit.stays_on_the_map_with_no

Terms: ship

English: "{region} stays on the map with no settlement in it. Vanilla ships one like that (Durazzo); Health lists such a province as a note."

Turkish: "{region}, içinde yerleşim yeri olmadan haritada kalır. Vanilla içinde böyle bir yer vardır (Durazzo); Sağlık Kontrolü bu tür bir eyaleti bilgi notu olarak listeler."

### eng.stratedit.two_levels_of_stand_in_this

Terms: ship

English: "Two levels of {x} stand in this settlement at once. Third Age Reforged ships four settlements like it, so it is not fatal, but only one of them is the building."

Turkish: "Bu yerleşimde aynı anda iki {x} seviyesi bulunmaktadır. Third Age Reforged buna benzer dört yerleşim yeri gönderiyor, bu yüzden ölümcül değil, ancak bunlardan yalnızca biri bina."

### eng.stratobj.is_pixel_none_of_the_800_port

Terms: port_verb

English: "{gx},{gy} is {name}'s port pixel. None of the 800 forts and watchtowers measured stands on a settlement or a port."

Turkish: "{gx}, {gy}, {name}'nin port etmek piksel'sidir. Ölçülen 800 hisar ve gözetleme kulesi'nin hiçbiri yerleşim yeri veya port etmek üzerinde durmuyor."

### eng.stratobj.is_pixel_none_of_the_800_settlement

Terms: port_verb

English: "{gx},{gy} is {name}'s settlement pixel. None of the 800 forts and watchtowers measured stands on a settlement or a port."

Turkish: "{gx}, {gy}, {name}'nin yerleşim yeri piksel'sidir. Ölçülen 800 hisar ve gözetleme kulesi'nin hiçbiri yerleşim yeri veya port etmek üzerinde durmuyor."

### eng.stringsbin.a_single_string_cannot_exceed_65535

Terms: character

English: "a single string cannot exceed 65535 characters (this one is {units})"

Turkish: "tek bir dize 65535 karakteri aşamaz (bu {units}'dir)"

### eng.stringsbin.a_string_says_it_is_characters

Terms: character

English: "a string says it is {units} characters long but only {x} are left in the file"

Turkish: "bir dize {units} karakter uzunluğunda olduğunu söylüyor ancak dosyada yalnızca {x} kaldı"

### eng.winconds.could_not_be_read_the_stock

Terms: ship

English: "{rel} could not be read ({exc}). The stock game ships it on disk and so do both installed mods, so a campaign without one is a campaign nobody can win"

Turkish: "{rel} okunamadı ( {exc} ). Standart oyun onu diskte gönderir ve her iki yüklü mod da öyle, yani modsuz bir kampanya, kimsenin kazanamayacağı bir kampanyadır"

### facaudit.world_maps_campaign

Terms: campaign

English: "world/maps/campaign/{camp}/{rel}"

Turkish: "world/maps/campaign/{camp}/{rel}"

### guided.florins_the_smith_charges_to_upgrade

Terms: charge

English: "Florins the smith charges to upgrade its weapons."

Turkish: "Demircinin silah yükseltmesi için istediği florin tutarı."

### guided.infantry_cavalry_siege_ship_handler

Terms: cavalry, infantry, ship, siege

English: "infantry | cavalry | siege | ship | handler"

Turkish: "infantry | cavalry | siege | ship | handler"

### guided.light_heavy_missile_spearmen

Terms: missile

English: "light | heavy | missile | spearmen"

Turkish: "light | heavy | missile | spearmen"

### guided.optional_the_effect_played_when_the_weapon

Terms: turn

English: "Optional. The effect played when the weapon <i>fires</i>: <code>musket_shot_set</code> for gunpowder units, and essentially nothing else. Setting it is what turns this line from 11 values into 12; clearing it turns it back."

Turkish: "İsteğe bağlı. Silah <i>ateşlendiğinde</i> oluşan etki: barut birimleri için <code>musket_shot_set</code> ve aslında başka bir şey değil. Bunu ayarlamak, bu satırı 11 değerden 12 değere dönüştüren şeydir; temizlemek onu geri döndürür."

### guided.vanilla_ships_it_commented_out

Terms: ship

English: "Vanilla ships it commented out."

Turkish: "Vanilla içinde yorum satırı olarak bulunur."

### guided.vanilla_ships_it_commented_out_on

Terms: ship

English: "Vanilla ships it commented out on every unit."

Turkish: "Vanilla içinde her birimde yorum satırı olarak bulunur."

### home.mounted_pack

Terms: mount

English: "📦 mounted pack"

Turkish: "📦 bağlı paket"

### home.pick_your_medieval_ii_folder_it

Terms: mod

English: "Pick your Medieval II folder (it contains \"mods\")"

Turkish: "Medieval II klasörünüzü seçin (\"mods\" klasörünü içerir)"

### map3d.building_the_mesh

Terms: building

English: "Building the mesh…"

Turkish: "Mesh oluşturuluyor…"

### maplabels.character

Terms: character

English: "character:{line}"

Turkish: "character:{line}"

### maplabels.port

Terms: port_verb

English: "port:{region}"

Turkish: "port:{region}"

### maplabels.port_2

Terms: port_verb

English: "Port · {x}"

Turkish: "Liman · {x}"

### mapquery.building_that_map

Terms: building

English: "building that map"

Turkish: "o haritayı inşa etmek"

### mapsize.turn_the_real_world_switch_on

Terms: turn

English: "Turn the Real world switch on in Settings first."

Turkish: "Önce Ayarlar'da Gerçek dünya anahtarını açın."

### minorfiles.port_ladder_line_s_in_the

Terms: port_verb

English: "Port ladder <span class=\"count\">{ports_n} line(s), in the file's own order: each port level is a <code>port_land</code> and a <code>port_sea</code> model. Adding or removing a level is a pair of lines placed in that order, so it is done in the code view; what each line points at is here.</span>"

Turkish: "port etmek ladder <span class=\"count\">{ports_n} satır(lar), dosyanın kendi sırasına göre: her port seviyelemek bir <code>port_land</code> ve bir <code>port_sea</code> modelidir. Bir seviyenin eklenmesi veya kaldırılması, bu sıraya göre yerleştirilen bir çift çizgidir, dolayısıyla kod görünümünde yapılır; her satırın neyi işaret ettiği burada.</span>"

### minorfiles.this_culture_has_no_port_lines

Terms: port_verb

English: "This culture has no port lines."

Turkish: "Bu kültürün liman hatları yoktur."

### minorfiles.where_it_starts_every_regions_religions

Terms: ship

English: "Where it starts <span class=\"count\">Every region's <code>religions { … }</code> line gets <code>{name} 0</code>, in every descr_regions.txt this mod ships. A share given here comes out of the region's other religions in proportion, so each line still adds up to 100.</span>"

Turkish: "Başladığı yer <span class=\"count\">Her bölgenin <code>religions { … }</code> satırı, bu modun gönderdiği her descr_regions.txt dosyasında <code>{name} 0</code> alır. Burada verilen pay bölgedeki diğer dinlerden de orantılı olarak çıkıyor, dolayısıyla her satırın toplamı yine 100'e ulaşıyor.</span>"

### osmmap.mylaes_layout_the_maps_layers_as

Terms: port_verb

English: "Mylae’s layout: the map’s layers as they are on disk, bbox_coords.txt, and reference/ with map_regions.txt (each province’s colour, city and port), the historic sites already fetched for this box, and the picture. Only the picture uses the internet."

Turkish: "Mylae'nin düzeni: haritanın diskteki katman'si, bbox_coords.txt ve map_regions.txt ile referans/ (her eyalet'nin rengi, şehir ve port etmek), tarihi yerler bu kutu için zaten getirilmiş ve resim. Sadece resim interneti kullanıyor."

### osmmap.open_settings_to_turn_it_on

Terms: turn

English: "⚙ Open Settings to turn it on"

Turkish: "⚙ Açmak için Ayarlar'ı açın"

### osmworld.drag_to_pan_wheel_to_zoom

Terms: turn

English: "Drag to pan, wheel to zoom. Drag the box's corners to resize it, its middle to move it, the violet handle to turn it."

Turkish: "Kaydırmak için sürükleyin, yakınlaştırmak için döndürün. Yeniden boyutlandırmak için kutunun köşelerini, taşımak için ortasını, döndürmek için mor tutamacı sürükleyin."

### packs.battle_model_entr_travel_with_them

Terms: mount

English: {"one": "{count} battle-model entry travels with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer.", "other": "{count} battle-model entries travel with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer."}

Turkish: {"one": "{count} savaş modeli girdisi de bunlarla taşınır. İçe aktarma, paketi kaynak mod olarak bağlar ve normal aktarım ekranını açar. Ad çakışmaları, temel birim, sahiplik ve diğer tüm seçenekler orada sorulur. Aktar düğmesine basılana kadar hiçbir şey yazılmaz.", "other": "{count} savaş modeli girdisi de bunlarla taşınır. İçe aktarma, paketi kaynak mod olarak bağlar ve normal aktarım ekranını açar. Ad çakışmaları, temel birim, sahiplik ve diğer tüm seçenekler orada sorulur. Aktar düğmesine basılana kadar hiçbir şey yazılmaz."}

### rebels.of_provinces_name_a_rebel_faction

Terms: turn

English: "{silent_regions} of {regions} provinces name a rebel faction with <code>chance 0</code>, so they spawn no rebels. That is a real setting rather than a fault - it is how a mod turns province rebels off - but it is what those assignments do."

Turkish: "{regions} eyalet içinden {silent_regions} tanesi, <code>chance 0</code> ile bir isyancı fraksiyon belirtir; bu yüzden isyancı oluşturmazlar. Bu bir hata değil, geçerli bir ayardır: mod, eyalet isyancılarını böyle kapatır. Ancak bu atamaların sonucu budur."

### regiondel.already_has_a_port_and_only

Terms: port_verb

English: "{heir} already has a port, and only one of two in a province is\n         ever used - so removing this one is the answer that leaves a map the\n         validator does not report."

Turkish: "{heir}'de zaten bir port etmek var ve eyalet'deki ikisinden yalnızca biri\n         şimdiye kadar kullanılmış - yani bunu kaldırmak, haritayı geride bırakan cevaptır\n         doğrulayıcı rapor vermiyor."

### regiondel.has_no_port_of_its_own

Terms: port_verb

English: "{heir} has no port of its own, so keeping this one gives it a\n         harbour on the coast it is about to inherit."

Turkish: "{heir}'nin kendine ait bir bağlantı noktası yoktur, dolayısıyla bunu tutmak ona bir avantaj sağlar.\n         Kıyıdaki limanı miras almak üzeredir."

### regiondel.its_port

Terms: port_verb

English: "<span class=\"cmtnm\">Its port</span> <span class=\"cmseg\">"

Turkish: "<span class=\"cmtnm\">Bağlantı noktası</span> <span class=\"cmseg\">"

### settings.and_more_characters_in_the_diagnostic

Terms: character

English: "…and {summary_cut} more characters, in the diagnostic log."

Turkish: "…ve tanılama günlüğünde {summary_cut} karakter daha."

### settings.point_to_your_medieval_ii_install

Terms: mod

English: "Point to your Medieval II install (contains <b>mods</b>) or a mods folder directly. Remembered next time."

Turkish: "Medieval II kurulumunuzu (<b>mods</b> klasörünü içerir) veya doğrudan bir mod klasörünü belirtin. Sonraki açılışta hatırlanır."

### settings.start_the_soldier_row_on_base

Terms: building

English: "Start the <b>Soldier</b> row on <b>Base</b>, so the destination unit's model and projectile are used instead of the transferred unit's. Applies to both modes that have a base unit: building a new unit on one, and replacing one (there the base <i>is</i> the unit being replaced, so its own model and animations stay). Still switchable per unit."

Turkish: "<b>Asker</b> satırını <b>Temel</b> seçeneğiyle başlatın. Böylece aktarılan birimin yerine hedef birimin modeli ve mermisi kullanılır. Temel birim içeren iki mod için de geçerlidir: bir birimi temel alarak yenisini oluşturma ve bir birimi değiştirme (ikincisinde temel birim, değiştirilen birimin <i>kendisidir</i>; dolayısıyla kendi modeli ve animasyonları korunur). Her birim için ayrıca değiştirilebilir."

### settlemech.level

Terms: level

English: "level/{name}/{x}"

Turkish: "level/{name}/{x}"

### soundbanks.has_no_data_the_game_uses

Terms: ship

English: "{src} has no <code>data/{rel}</code>.<br><span class=\"count\">The game uses its own {label} when a mod does not ship them.</span>"

Turkish: "{src}'de <code>verisi yok/{rel}</code>. <br> <span class=\"count\"> Bir mod onları göndermediğinde oyun kendi {label}'sini kullanır. </span>"

### sprites.the_bypass_flag_makes_the_next_normal

Terms: turn

English: "The bypass flag makes the next normal launch re-render instead of starting, which reads as a crash. Turn it back off when you are done."

Turkish: "Baypas bayrağı, bir sonraki normal başlatmanın başlatılması yerine yeniden oluşturulmasını sağlar, bu da bir çökme olarak okunur. İşiniz bittiğinde tekrar kapatın."

### sprites.this_mod_ships_m2tweop_so_generation

Terms: ship

English: "This mod ships M2TWEOP, so generation goes through its console."

Turkish: "Bu mod M2TWEOP'u gönderir, böylece nesil konsolundan geçer."

### sprites.turn_the_flag_back_off

Terms: turn

English: "Turn the flag back off"

Turkish: "Bayrağı tekrar kapat"

### stratcamp.faction_bik

Terms: faction

English: "faction/{x}.bik"

Turkish: "faction/{x}.bik"

### stratmap.draw_a_campaign_map_model_beside

Terms: ship

English: "Draw a campaign-map model beside the list, without leaving it. Every entry\nthat ships a .CAS gets its own 🧊 button once this is open, and the panel also browses\nevery model file under data/models_strat - including the settlements, which no entry names."

Turkish: "Listeden ayrılmadan yanında bir kampanya haritası modeli çizin. Bu panel açıldığında .CAS içeren her girdi kendi 🧊 düğmesini alır. Panel, hiçbir girdinin adlandırmadığı yerleşim yerleri dahil data/models_strat altındaki tüm model dosyalarını da gösterir."

### stratmap.file_named_by_no_model_but

Terms: turn

English: {"one": "{count} file is named by no model, but its bare filename turns up in a <code>descr_*.txt</code> or a script - so it is not offered above either.", "other": "{count} files are named by no model, but their bare filename turns up in a <code>descr_*.txt</code> or a script - so they are not offered above either."}

Turkish: {"one": "{count} dosyayı hiçbir model adlandırmıyor; ancak dosyanın yalın adı bir <code>descr_*.txt</code> dosyasında veya script içinde geçiyor. Bu yüzden yukarıda da sunulmaz.", "other": "{count} dosyayı hiçbir model adlandırmıyor; ancak dosyanın yalın adı bir <code>descr_*.txt</code> dosyasında veya script içinde geçiyor. Bu yüzden yukarıda da sunulmaz."}

### stratview.this_mod_ships_no_data_models

Terms: ship

English: "this mod ships no <code>data/models_strat</code>, so it uses the game's own strat models"

Turkish: "Bu mod <code>data/models_strat</code> içermez; bu yüzden oyunun kendi strateji modellerini kullanır"

### v3anim.building_the_glb

Terms: building

English: "Building the .glb…"

Turkish: ".glb oluşturuluyor…"

### v3anim.building_the_obj_zip

Terms: building

English: "Building the .obj zip…"

Turkish: ".obj zip dosyası oluşturuluyor…"

### v3anim.played_from_vanillas_pack_this_mod

Terms: ship

English: "Played from vanilla’s pack: this mod ships none of its own to save an edit into."

Turkish: "Vanilla paketinden oynatılıyor: bu modun, düzenlemeyi kaydedebileceğiniz kendine ait bir paketi yok."

### v3anim.turn_every_key

Terms: turn

English: "<span>Turn, every key</span> {x}°"

Turkish: "<span> Her tuşu çevirin </span> {x} °"

### v3anim.turns_to

Terms: turn

English: " · turns {turn}° to {turn2}°"

Turkish: "· {turn}°'yi {turn2}°'ye çevirir"

### v3anim.vanillas_skeleton_pack_this_mod_ships

Terms: ship

English: "vanilla’s skeleton pack (this mod ships none, so the game plays vanilla’s)"

Turkish: "Vanilla iskelet paketi (bu mod kendine ait paket içermez; oyun vanilla paketini oynatır)"

### viewer3d.art_starts_over_second

Terms: unit

English: "where the art starts over - every second unit of u"

Turkish: "sanatın yeniden başladığı yer - her saniyeniz"

### viewer3d.art_starts_over_unit

Terms: unit

English: "where the art starts over - every unit of u"

Turkish: "sanatın yeniden başladığı yer - her biriniz"

### viewer3d.drag_to_turn_wheel_to_zoom

Terms: turn

English: "drag to turn · wheel to zoom · right-drag to pan"

Turkish: "döndürmek için sürükleyin · yakınlaştırmak için tekerlek · kaydırmak için sağa sürükleyin"

### viewer3d.draw_the_texture_at_the_size

Terms: ship

English: "Draw the texture at the size the mod ships it, instead of halving anything over\n1024. That is the size the game draws, so it is the one to check a skin's own detail\nagainst. Off by default: a 2048 sheet is four times the bytes and the video memory\nfor a soldier on screen a few hundred pixels tall."

Turkish: "Herhangi bir şeyi yarıya indirmek yerine, dokuyu modun gönderdiği boyutta çizin\n1024. Bu, oyunun çizdiği boyuttur, yani cildin kendi ayrıntılarını kontrol eden kişidir.\nkarşı. Varsayılan olarak kapalı: 2048 sayfa, baytın ve video belleğinin dört katıdır\nekranda bir asker için birkaç yüz piksel uzunluğunda."

### viewer3d.drawn_at_shipped

Terms: ship

English: "drawn at <b>{w} × {h}</b> - the size the mod ships, as the game draws it"

Turkish: "<b> {w} × {h} </b>'de çizilmiştir - oyunun çizdiği şekliyle modun gönderdiği boyut"

### viewer3d.in_game_units

Terms: unit

English: "{x} × {x2} × {x3} in game units"

Turkish: "{x} × {x2} × {x3} oyun birimlerinde"

### viewer3d.lod

Terms: lod

English: "LOD {index}{distance}{exists}"

Turkish: "LOD {index}{distance}{exists}"

### voices.no_name_call

Terms: general

English: "No name call of its own in the voice bank; it says its class's general line."

Turkish: "seslendirme bankasında kendine ait bir isim yok; kendi sınıfının general serisi olduğunu söylüyor."

### voices.own_compiled

Terms: event

English: "The mod's compiled data/sounds/events.dat and events.idx are removed (backed up); the game builds them again on its next start."

Turkish: "Modun derlenmiş verileri/sesleri/events.dat ve events.idx'i kaldırılır (yedeklenir); oyun onları bir sonraki başlangıcında yeniden oluşturur."

### voices.own_note

Terms: event

English: "Pick the accent and class it is for and one or more .wav files (the game's own are 22050 Hz, 16-bit, mono). They go in as loose files under new names, the unit gets its own line for that accent and class, and the compiled events.dat and events.idx are removed so the game rebuilds them."

Turkish: "Aksanı ve sınıfını ve bir veya daha fazla .wav dosyasını seçin (oyununki 22050 Hz, 16 bit, mono). Bunlar yeni isimler altında gevşek dosyalar olarak giriyor, birim bu aksan ve sınıf için kendi çizgisini alıyor ve derlenmiş events.dat ve events.idx kaldırılıyor, böylece oyun onları yeniden oluşturuyor."
