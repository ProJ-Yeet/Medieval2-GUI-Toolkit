# Polish draft review, 2026-10-28

Phase 88i is complete as a draft: 9,633/9,633 IDs, including 379 plural objects.
No missing, stale or extra IDs. Promoted with i18n_todo.py and offered as
Polski (Polish) - wersja robocza. Native-speaker review remains pending.

## Translation method and limits

Shared controls, startup, Home, navigation, selected Settings guidance,
Transfer and map labels and many domain/plural strings were authored or
corrected directly. Bulk text was drafted with local NLLB-200 distilled 600M;
remaining refused candidates were redrafted with Google Translate and checked
again. Translation candidates and corrections remain in ignored .cache/pl-*
working files. No translation service or model is used by the application.
A proposed constrained/fragment fallback was not used.

This is machine-assisted coverage completion, not a claim that every sentence
has received a native linguistic review. Bulk explanations, inflected technical
terms, fractional plural forms and runtime joins particularly need native review.
The UI pass corrected misleading meanings of map validation, transfer overwrite,
model rotation and file relocation, as well as awkward Settings guidance.
Literal engine syntax, filenames, paths, examples and product names remain intact.

## Verification

Home, Settings, Transfer (unit drawer and composer) and Campaign Map were
inspected at 1280 px and 375 px in the in-app browser. Polish letters render
correctly; controls and guidance wrap. The measured narrow screens had no
page-wide horizontal overflow. Long dialogs scroll. This was representative
screen QA, not a walkthrough of every dialog or a game-play validation.

The preview used isolated synthetic mods built from repository test fixtures:
a small 8-by-7 map with layers and a campaign, and one EDU/modeldb unit. Missing
sample art is expected. It did not validate an installed real mod. The preview
kept language and beta settings in memory; no mod writes were applied.
Screenshots are local working evidence in .cache/pl-uiqa/. The promoted language
picker was checked against the shipped catalogue.

English can still appear in source-side readiness names, diagnostics and some
viewer/map runtime fragments, or in mod names, field values and paths. These
are not missing Polish catalogue IDs. Broader source localization is outside
this catalogue change. Ko-fi's supplied branded image also retains its own text.

Full catalogue/termbase checker: zero problems. Strict additional audit: zero
placeholder occurrence-count, literal HTML-tag, inline-code or known-path
mismatches, and no leftover translation markers. Source-hash stale detection
was checked using an in-memory changed English value.

The real catalogue also passed 3,790 plural-selection runtime probes across
all 379 plural objects, including 0, 1, 2, 5, 11, 12, 21, 22, 25 and 1.5.
A fixed count substitution isolates form selection from numeric formatting.

Tests: test_termbase 31/31; test_i18n 37/37; test_web_modules 124/124.
Polish glossary stem alternatives were expanded for ordinary inflections and
consonant alternations (for example bitwa/bitew, agent/agenc and slot/sloc),
with positive and negative regression checks. Preferred glossary words remain
unchanged. No application behavior changed and no release was cut.

## Exact glossary exceptions

The exceptions below apply only to the named entry and named terms. They cover
another English sense, literal code/paths/examples or a contextual Polish
rendering. They do not disable markup or placeholder checks. The complete source
and translation are included for contextual review; these exceptions remain
subject to native review. In particular, turn in viewer controls means rotation,
not a campaign turn; port can be a harbour or an import action; mount can mean
attaching data rather than an animal; building can be an action rather than a
structure. A glossary substring inside syntax or an example is preserved literally.

### app.shared_cards_title

Terms: tile

```json
{
  "source": "Grouped by faction: only the tiles whose faction has no card of its own for the unit and borrows another's",
  "pl": "Po pogrupowaniu według frakcji: tylko karty, dla których frakcja nie ma własnej grafiki jednostki i korzysta z grafiki innej frakcji"
}
```

### armory.chk_too_many_vertices

Terms: mesh

```json
{
  "source": "{count} vertices: a .mesh holds at most 65,536.",
  "pl": "Wierzchołki {count}: .mesh mieści maksymalnie 65 536."
}
```

### armory.exp_bake_note

Terms: mesh, texture

```json
{
  "source": "Writes the .mesh, a .texture for each sheet and a normal map beside each, with a .png of every sheet.",
  "pl": "Zapisuje .mesh, .texture dla każdego arkusza i normalną mapę obok każdego z .png każdego arkusza."
}
```

### armory.exp_free_turn_title

Terms: turn

```json
{
  "source": "Let a block turn to whatever angle packs it smallest, as well as by quarter turns. A block turned so is resampled and its art softens slightly; off, every texel is copied exactly.",
  "pl": "Pozwól obracać blok o dowolny kąt zapewniający najciaśniejsze ułożenie, a także o wielokrotności ćwierćobrotu. Przy dowolnym kącie obraz jest ponownie próbkowany i nieco traci ostrość. Po wyłączeniu każdy teksel jest kopiowany dokładnie."
}
```

### armory.file_intro

Terms: mesh

```json
{
  "source": "A .obj, .glb, .gltf, .dae, or a loose .mesh. Its textures are looked for in the same folder and its textures folder; an object with none found asks for one.",
  "pl": ".obj, .glb, .gltf, .dae lub luźny .mesh. Jego tekstury są wyszukiwane w tym samym folderze i folderze tekstur; obiekt, którego nie znaleziono, prosi o jeden."
}
```

### armory.frame_all

Terms: frame

```json
{
  "source": "Frame all",
  "pl": "Dopasuj widok"
}
```

### armory.head_as_one_title

Terms: turn

```json
{
  "source": "Helmet, coif, face, hair and beard move, turn and scale together whichever of them is picked",
  "pl": "Hełm, kapelusz, twarz, włosy i brodę poruszają się, obracają się i rozmiarują się w zależności od tego, który z nich zostanie wybrany"
}
```

### armory.key_frame_all

Terms: frame

```json
{
  "source": "Frame everything",
  "pl": "Dopasuj widok do wszystkiego"
}
```

### armory.key_frame_selected

Terms: frame

```json
{
  "source": "Frame the selection",
  "pl": "Dopasuj widok do zaznaczenia"
}
```

### armory.look_closer_title

Terms: turn

```json
{
  "source": "A closer look: the model in the viewer, to turn, zoom, change its skin and play its animations, before it is pulled in",
  "pl": "Przyjrzyj się bliżej: model w widzie, aby odwrócić, zwiększyć, zmienić skórę i odtworzyć swoje animacje, zanim zostanie wyciągnięty"
}
```

### armory.no_assets_yet

Terms: mesh

```json
{
  "source": "Nothing loaded yet. Import units or model entries from any installed mod, or a .obj, .glb, .dae or .mesh, to take parts from.",
  "pl": "Jeszcze nic nie zostało załadowane. Importuj jednostki lub wpisy modeli z dowolnego zainstalowanego moda lub pliku .obj, .glb, .dae lub .mesh, z którego możesz pobrać części."
}
```

### armory.stamp_rot

Terms: turn

```json
{
  "source": "Turn",
  "pl": "Obrót"
}
```

### armory.uv_hint

Terms: turn

```json
{
  "source": "Click picks, Shift adds, a drag on nothing draws a box, a drag on the selection moves it. G, R, S move, turn and scale (X or Y holds an axis; click or Enter keeps, Esc or the right button puts back). A selects all. The wheel zooms, the middle button or Alt pans.",
  "pl": "G, R, S poruszają się, obracają i rozmiarują (X lub Y utrzymuje osię; kliknij lub Enter utrzymuje, Esc lub przycisk prawny odwraca). A wybiera wszystko. Koło zwiększa się, przycisk środkowy lub Alt panne."
}
```

### buildings.its_battle_model_has_no_texture

Terms: turn

```json
{
  "source": "its battle model has no texture for <b>{x}</b>, so their soldiers would turn up untextured",
  "pl": "Jego model bitewny nie ma tekstury dla <b> {x} </b> , więc ich żołnierze pojawiłyby się bez tekstury ."
}
```

### buildings.this_mod_ships_no_file_at

Terms: ship

```json
{
  "source": "This mod ships no file at\nthis path, so the game uses the base game's picture. Drop a .tga in to override it.",
  "pl": "Mod nie wysyła plików na tę ścieżkę, więc gra używa zdjęcia gry bazowej."
}
```

### buildings.units_without_battle_model_texture

Terms: turn

```json
{
  "source": {
    "one": "<b>{count}</b> has no battle-model texture for some of them, so their soldiers would turn up untextured: {list}",
    "other": "<b>{count}</b> have no battle-model texture for some of them, so their soldiers would turn up untextured: {list}"
  },
  "pl": {
    "one": "<b> {count} </b> nie ma żadnej struktury modelu bitwy dla niektórych z nich, więc ich żołnierze pojawiły się bez tekstury: {list} ",
    "few": "<b> {count} </b> nie mają żadnej struktury modelu bitwy dla niektórych z nich, więc ich żołnierze pojawiły się bez tekstury: {list} ",
    "many": "<b> {count} </b> nie mają dla niektórych tekstury modelu bitwy, więc ich żołnierze pojawiły się bez tekstu: {list} ",
    "other": "<b> {count} </b> nie mają żadnej struktury modelu bitwy dla niektórych z nich, więc ich żołnierze pojawiły się bez tekstury: {list} "
  }
}
```

### campaint.add_a_province_decide_its_record

Terms: port_verb

```json
{
  "source": "Add a province: decide its record, paint it, place its settlement, then its port or skip.",
  "pl": "Dodaj prowincję: ustal jej rekord, pomaluj ją, umieść osadę, a następnie port lub pomiń."
}
```

### campaint.place_the_port_pixel_or_skip

Terms: port_verb

```json
{
  "source": "Place the port pixel, or skip it",
  "pl": "Umieść piksel portu lub przejść"
}
```

### campaint.writes_layers_at_once_in_the

Terms: port_verb

```json
{
  "source": "Writes {n} layers at once, in the colours <b>measured off this map</b>: {layers} · from {sea_tiles} sea tiles. Settlement and port pixels are left alone.",
  "pl": "Zapisuje warstwy {n} na raz, w kolorach <b> odmierzonych na tej mapie </b> : {layers} · z kafelków morskich {sea_tiles}. Osadnictwo i piksele portu pozostają w spokoju."
}
```

### campaint.written_into_a_settlement_the_music

Terms: ship

```json
{
  "source": "Written into {reach}: a settlement, the music\n           type and, where it ships one, the name lookup - each campaign’s own\n           copy of each file.",
  "pl": "Wpisany w języku {reach}: osada, rodzaj muzyki i, jeśli jest to wysyłane, wyszukiwanie nazwy - każda kampania własną kopię każdego pliku."
}
```

### campbrowse.campaigns_read_in_ms

Terms: ship

```json
{
  "source": {
    "one": "{count} campaign read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom.",
    "other": "{count} campaigns read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom."
  },
  "pl": {
    "one": "{count} kampania przeczytana w {ms} ms. Dziesięć warstw map i lista regionów znajdują się w <code> {base} </code> dla każdej kampanii, która nie zawiera własnej kopii – pomiędzy nimi zmienia się to, kto zaczyna, gdzie, z czym i przeciwko komu.",
    "few": "{count} kampanie odczytane w {ms} ms. Dziesięć warstw map i lista regionów znajdują się w <code> {base} </code> dla każdej kampanii, która nie zawiera własnej kopii – pomiędzy nimi zmienia się to, kto zaczyna, gdzie, z czym i przeciwko komu.",
    "many": "{count} kampanii odczytanych w {ms} ms. Dziesięć warstw map i lista regionów znajdują się w <code> {base} </code> dla każdej kampanii, która nie zawiera własnej kopii – pomiędzy nimi zmienia się to, kto zaczyna, gdzie, z czym i przeciwko komu.",
    "other": "{count} kampanii odczytanych w {ms} ms. Dziesięć warstw map i lista regionów znajdują się w <code> {base} </code> dla każdej kampanii, która nie zawiera własnej kopii – pomiędzy nimi zmienia się to, kto zaczyna, gdzie, z czym i przeciwko komu."
  }
}
```

### campbrowse.every_campaign_this_mod_ships_with

Terms: ship

```json
{
  "source": "Every campaign this mod ships, with what is in each one, and which of them this screen is reading.",
  "pl": "Każda kampania wysyła mody, z tym, co jest w każdym z nich i który z nich ten ekran czyta."
}
```

### campbrowse.nothing_in_to_read_a_menu

Terms: ship

```json
{
  "source": "Nothing in <code>{file}</code> to read a menu title out of - this mod ships neither it nor the compiled archive beside it - so no campaign below shows one. That is the file missing, not the campaigns being unnamed.",
  "pl": "Nie ma nic w <code> {file} </code> do odczytu tytułu menu - ten mod nie przesyła ani niego, ani kompilizowanego archiwum obok niego - więc żadna kampania poniżej nie pokazuje jednego."
}
```

### campbrowse.ships_map_layers

Terms: ship

```json
{
  "source": {
    "one": "It ships {count} map layer of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those.",
    "other": "It ships {count} map layers of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those."
  },
  "pl": {
    "one": "Zawiera {count} własną warstwę mapy ( {list} {more} ), którą silnik odczytuje zamiast warstwy podstawowej. Otwórz, ten ekran je rysuje.",
    "few": "Zawiera {count} własne warstwy mapy ( {list} {more} ), które silnik odczytuje zamiast warstwy podstawowej. Otwórz, ten ekran je rysuje.",
    "many": "Zawiera {count} własnych warstw map ( {list} {more} ), które silnik odczytuje zamiast bazowych. Otwórz, ten ekran je rysuje.",
    "other": "Dostarcza {count} własnych warstw mapy ( {list} {more} ), które silnik odczytuje zamiast bazowych. Otwórz, ten ekran je rysuje."
  }
}
```

### campcreate.new_region_name_paint_settlement_port

Terms: port_verb

```json
{
  "source": "<b>＋ New region</b><small>Name → paint → settlement → port</small>",
  "pl": "<b> + Nowy region </b> <small> Nazwa → farba → osadnictwo → port </small> "
}
```

### campcreate.port

Terms: port_verb

```json
{
  "source": "Port",
  "pl": "Port"
}
```

### campcreate.port_marker_add_or_move_on

Terms: port_verb

```json
{
  "source": "<b>⚓ Port marker</b><small>Add or move on the selected region</small>",
  "pl": "<b>  Marker portu </b> <small> Dodać lub przenieść wybrany region </small> "
}
```

### campcreate.select_a_region_first_then_choose

Terms: port_verb

```json
{
  "source": "Select a region first, then choose its settlement or port marker.",
  "pl": "Wybierz najpierw region, a następnie wybierz jego osada lub marker portu."
}
```

### campmap.building_the_composite

Terms: building

```json
{
  "source": "building the composite…",
  "pl": "budowanie kompozytu..."
}
```

### campmap.click_a_province_to_inspect_it

Terms: turn

```json
{
  "source": "Click a province to inspect it. Turn on Paint to edit tiles; right or middle drag still pans. Choose a layer and colour on the left.",
  "pl": "Kliknij prowincję, aby go sprawdzić. Włącz farbę, aby edytować kafelki; prawe lub środkowe ciągnąć płyny. Wybierz warstwę i kolor po lewej stronie."
}
```

### campmap.comp_key

Terms: terrain

```json
{
  "source": "{layers}|terrain:{terrain}|fe:{fe}",
  "pl": "{layers}|terrain:{terrain}|fe:{fe}"
}
```

### campmap.draw_the_ground_the_way_the

Terms: terrain

```json
{
  "source": "Draw the ground the way the game does: this mod's own\naerial-map textures, one per climate and ground type, out of\ndata/terrain/aerial_map/ground_types. It is map_ground_types.tga and\nmap_climates.tga read together rather than an eleventh layer, so it goes on this row -\nand it is drawn under the whole stack, because it is the ground.\nA tile whose texture cannot be found is counted and drawn in the colour picked\nbeside this, never skipped.",
  "pl": "Rysuj ziemię w sposób, w jaki robi to gra: jest to własność tego moda\ntekstury map lotniczych, po jednej dla każdego klimatu i rodzaju podłoża, z\n data/terrain/aerial_map/ground_types . Jest to map_ground_types.tga i\n map_climates.tga czyta się razem, a nie jedenastą warstwę, więc idzie w tym wierszu -\ni jest wciągnięty pod cały stos, ponieważ jest ziemią.\nKafelek, której tekstury nie można znaleźć, jest liczona i losowana w wybranym kolorze\npoza tym nigdy nie pomijałem."
}
```

### campmap.has_no_campaign_map_this_tool

Terms: ship

```json
{
  "source": "has no campaign map this tool can read.<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">A mod only has one if it ships <code>data/world/maps/base</code> - the terrain header, the region list and the ten TGA layers. Without them the game uses its own map, and there is nothing here to draw.</span>",
  "pl": "nie ma mapy kampanii, którą to narzędzie mogłoby odczytać. <br> <span class=\"count\"> {why} </span> <br> <br> <span class=\"count\"> Mod ma go tylko jeśli dostarcza <code> data/world/maps/base </code> - nagłówek terenu, lista regionów i dziesięć warstw TGA. Bez nich gra korzysta z własnej mapy i nie ma tu co rysować. </span>"
}
```

### campmap.port_marker

Terms: port_verb

```json
{
  "source": "Port marker",
  "pl": "Znacznik portu"
}
```

### campmap.port_pixel

Terms: port_verb

```json
{
  "source": "port pixel",
  "pl": "piksel portu"
}
```

### campmap.port_pixels_undecided

Terms: port_verb

```json
{
  "source": {
    "one": "{count} port pixel whose owning region cannot be decided",
    "other": "{count} port pixels whose owning region cannot be decided"
  },
  "pl": {
    "one": "{count} piksel portowy, którego regionu będącego właścicielem nie można określić",
    "few": "{count} piksele portowe, których regionu będącego właścicielem nie można określić",
    "many": "{count} portowych pikseli, których regionu będącego właścicielem nie można określić",
    "other": "{count}-portowe piksele, których regionu będącego właścicielem nie można określić"
  }
}
```

### campmap.region_id_tiles_settlement_at_game

Terms: port_verb

```json
{
  "source": "<span>Region ID</span><b>{x}</b> <span>Tiles</span><b>{count}{x2}</b> <span>Settlement at</span><b>{x3} <span class=\"count\">game</span> · {x4} <span class=\"count\">image</span></b> <span>Port at</span><b>{x5}</b> {x6} <span>Bounding box</span><b>{x7}</b>",
  "pl": "<span> Identyfikator regionu </span> <b> {x} </b> <span> Kafelki </span> <b> {count} {x2} </b> <span> Osada w </span> <b> {x3} <span class=\"count\"> gra </span> · {x4} <span class=\"count\"> obraz </span> </b> <span> Port w </span> <b> {x5} </b> {x6} <span> Skrzynka ograniczająca </span> <b> {x7} </b>"
}
```

### campmap.settlement_character_and_port_names_beside

Terms: port_verb

```json
{
  "source": "Settlement, character and port names beside their markers (L), placed so that none covers another.\nA name with no room at this zoom is left off and counted; zoom in for it.",
  "pl": "Nazwy osad, postaci i portów obok ich znaczników (L), rozmieszczone bez nakładania się. Nazwy, dla której nie ma miejsca przy tym powiększeniu, nie widać, ale jest liczona. Przybliż widok, aby ją zobaczyć."
}
```

### campmap.ships_its_own_so_that_layer

Terms: ship

```json
{
  "source": "{campaign} ships its own {own}, so that layer is drawn from <code>{folder}</code>. Everything else is <code>world/maps/base</code>, which is what the brush paints.",
  "pl": "{campaign} ma własny {own} , więc ta warstwa jest rysowana z <code> {folder} </code> . Cała reszta to <code> world/maps/base </code>, czyli to co maluje pędzel."
}
```

### campmap.the_campaign_map_as_a_surface

Terms: turn

```json
{
  "source": "The campaign map as a surface. Drag to turn, right-drag to pan, scroll to zoom.",
  "pl": "Mapę kampanii jako powierzchnię."
}
```

### campmap.the_heights_as_a_surface_with

Terms: turn

```json
{
  "source": "The heights as a surface, with this map's own ground on it, orbited (D).\nDrag to turn, right-drag to pan, wheel to zoom.\nMarkers, labels and the tooltip stay on the flat map.",
  "pl": "Wysokości jako powierzchnia z własnym podłożem tej mapy, z widokiem orbitalnym (D). Przeciągaj, aby obracać; prawym przyciskiem przesuwaj widok, a kółkiem zmieniaj powiększenie. Znaczniki, etykiety i podpowiedź pozostają na płaskiej mapie."
}
```

### campmark.named_character_general_admiral_port_spy

Terms: port_verb

```json
{
  "source": "♚ Named character · ⚔ General · ⚓ Admiral / port<br> ◈ Spy · ¤ Merchant · ⚑ Diplomat · ✝ Priest · † Assassin",
  "pl": " Imię postaci ·  Generał ·  Admiral / port <br>  Szpieg · ¤ Sprzedawca ·  Dyplomat ·  Książę · † morderca"
}
```

### campmark.port

Terms: port_verb

```json
{
  "source": "Port · {x}",
  "pl": "Port · {x}"
}
```

### campmark.this_mod_ships_its_own_picture

Terms: ship

```json
{
  "source": "This mod ships its own picture for {art} of the\n        {n} trade resources here; the rest draw a glyph,\n        because the stock art is inside a .pack archive.",
  "pl": "Mod ten przesyła swój własny obraz {art} z surowców handlowych {n} tutaj; reszta rysuje glyf, ponieważ artystyka jest w archiwum .pack."
}
```

### campnew.map_layers_note

Terms: ship

```json
{
  "source": {
    "one": "It ships {count} map layer of its own, so the copy gets a copy of those too and the two are then two maps to keep in step.",
    "other": "It ships {count} map layers of its own, so the copy gets a copy of those too and the two are then two maps to keep in step."
  },
  "pl": {
    "one": "Zawiera {count} własną warstwę mapy, więc kopia również otrzymuje kopię tej warstwy i wtedy obie mapy muszą być na bieżąco.",
    "few": "Zawiera {count} własne warstwy map, więc kopia również otrzymuje kopię tych dwóch, a następnie są to dwie mapy, które należy dotrzymać kroku.",
    "many": "Zawiera {count} własnych warstw map, więc kopia również otrzymuje kopię tych dwóch, a zatem są to dwie mapy, które należy dotrzymać kroku.",
    "other": "Zawiera {count} własnej warstwy mapy, więc kopia również otrzymuje kopię tych dwóch, a zatem są to dwie mapy, które należy dotrzymać kroku."
  }
}
```

### campnew.this_mod_ships_only_the_compiled

Terms: ship

```json
{
  "source": "This mod ships only the compiled archive of <code>{descriptions}</code>, which is where the keys would go.",
  "pl": "Mod ten przesyła tylko złożony archiwum <code> {descriptions} </code> , gdzie klucze pójdą."
}
```

### cards.and_more_written_into_the_merc

Terms: mercenary

```json
{
  "source": "…and {copy_count} more written into the merc folder",
  "pl": "…i kolejne {copy_count} zapisane w folderze merc"
}
```

### cards.copying_file_s_out_writing_into

Terms: mercenary

```json
{
  "source": "Copying {export_count} file(s) out, writing {copy_count} into the merc folder,\n     then taking {delete_count} out of {mod}. Everything is backed up as it goes.",
  "pl": "Kopiowanie {export_count} plików na zewnątrz, zapisywanie {copy_count} w folderze merc, a następnie usuwanie {delete_count} z {mod}. Wszystkie zmiany są na bieżąco zabezpieczane kopiami zapasowymi."
}
```

### cards.data_ui_units_data_ui_unit

Terms: unit

```json
{
  "source": "data/ui/units · data/ui/unit_info",
  "pl": "data/ui/units · data/ui/unit_info"
}
```

### cards.gen_place_reset

Terms: frame

```json
{
  "source": "Put the model and the frame back",
  "pl": "Przywróć położenie modelu i kadru"
}
```

### cards.gen_rig_hint

Terms: turn

```json
{
  "source": "Drag the dots in the HD view: hands, feet, the pelvis and the torso move, the diamonds point the elbows and knees, the head turns.",
  "pl": "Pociągnij kropki w widoku HD: ręce, stopy, miednica i ruch ciała, diamenty wskazują łokcie i kolana, głowa obraca się."
}
```

### cards.gen_turn

Terms: turn

```json
{
  "source": "Turn",
  "pl": "Obrót"
}
```

### cards.gen_view_hint

Terms: turn

```json
{
  "source": "In the HD view: middle drag turns the camera, Shift pans, the wheel zooms; G moves and R turns the model, X, Y or Z holds it to an axis, a click or Enter keeps it, Esc puts it back.",
  "pl": "W widoku HD: środkowy przeciąg obraca aparat, schody Shift, koło zwiększa; G porusza się i R obraca model, X, Y lub Z trzyma go na osi, kliknięcie lub Enter utrzymuje go, Esc umieści go z powrotem."
}
```

### cards.merc

Terms: mercenary

```json
{
  "source": " ·&nbsp;merc",
  "pl": " ·&nbsp;merc"
}
```

### cards.one_is_the_merc_copy

Terms: mercenary

```json
{
  "source": " - one of them is already the merc copy",
  "pl": " - jedna z nich jest już kopią merc"
}
```

### changes.record_every_tracked_file_as_it_wrong_after_update

Terms: record

```json
{
  "source": "Record every tracked file as it is on disk now, as your version?\n\nRight after hand edits made outside the toolkit. WRONG after a mod update: your changes would be replaced by the update. Port instead.",
  "pl": "Zarejestrować każdy śledzony plik w jego obecnej postaci na dysku jako twoją wersję?\n\nUżywaj po ręcznych zmianach poza narzędziem. NIE używaj po aktualizacji moda: twoje zmiany zostałyby zastąpione aktualizacją. Zamiast tego portuj zmiany."
}
```

### changes.turn_off

Terms: turn

```json
{
  "source": "Turn off",
  "pl": "Wyłącz"
}
```

### changes.turn_off_putting_the_original_records

Terms: turn

```json
{
  "source": "Turn \"{off}\" off, putting the original records back?",
  "pl": "Wyłączyć „{off}” i przywrócić oryginalne rekordy?"
}
```

### changes.turn_on

Terms: turn

```json
{
  "source": "Turn \"{on}\" on?",
  "pl": "Włącz \"{on}\"?"
}
```

### climates.append_a_name_the_engine_does

Terms: ship

```json
{
  "source": "Append a name the engine does not ship. The strat map draws it; the\nbattle map reads climates by name, which is what the warning is about.",
  "pl": "Dołącz nazwę, której wyszukiwarka nie dostarcza. Rysuje to mapa kampanii; the\nmapa bitewna czyta klimaty po nazwie i o to chodzi w ostrzeżeniu."
}
```

### climates.taking_over_one_of_the_twelve

Terms: ship

```json
{
  "source": "{problem} Taking over one of the twelve the engine ships needs no such check.",
  "pl": "{problem} Przejęcie jednego z dwunastu statków silnikowych nie wymaga takiej kontroli."
}
```

### codeview.every_string_here_is_stored_as

Terms: character

```json
{
  "source": "Every string here is stored as its own length\nfollowed by that many characters. Change a path and the number beside it has to\nchange too. This does that, and you can see it happen.",
  "pl": "Każdy ciąg jest przechowywany jako jego własna długość, a następnie przez tyle znaków. Zmienić ścieżkę i liczba obok musi się zmienić."
}
```

### core.every_model_a_mod_ships_the

Terms: ship

```json
{
  "source": "Every model a mod ships: the battle entries, their sprites, the strat map’s, and the cards",
  "pl": "Każdy model zawarty w modzie: wpisy bitewne, ich sprite’y, modele mapy kampanii i karty"
}
```

### core.merc

Terms: mercenary

```json
{
  "source": "merc",
  "pl": "merc"
}
```

### core.the_tool_did_not_finish_loading

Terms: turn

```json
{
  "source": "The tool did not finish loading.<br> <span class=\"count\">The server is running - it answered for the rest of this page - but the browser never received {names}. Reloading fetches it again. If it fails every time, an ad blocker or privacy extension is the usual cause: turn it off for 127.0.0.1.</span>",
  "pl": "Narzędzie nie zakończyło ładowania. <br> <span class=\"count\"> Serwer działa - odpowiedział na resztę tej strony - ale przeglądarka nigdy nie otrzymała {names} . Przeładowanie go ponownie przybiera. Jeśli za każdym razem się nie uda, zwykłą przyczyną jest blokownik ogłoszeń lub rozszerzenie prywatności: wyłącz go na 127.0.0.1. </span> "
}
```

### core.the_two_pictures_per_unit_deduplicated

Terms: mercenary

```json
{
  "source": "The two pictures per unit, deduplicated into the merc folder",
  "pl": "Dwie obrazy na jednostkę, odtworzone w folderze Merc"
}
```

### editor.draw_this_model_its_parts_its

Terms: mesh

```json
{
  "source": "Draw this model - its parts, its variants and the skin each\nfaction gets. Reads the .mesh the entry names.",
  "pl": "Narysuj ten model - jego części, warianty i skórę\nfrakcja dostaje. Odczytuje .mesh nazwy wpisów."
}
```

### editor.merc

Terms: mercenary

```json
{
  "source": " · merc",
  "pl": " · merc"
}
```

### edusort.gondor_tier_2_infantry

Terms: infantry, tier

```json
{
  "source": "GONDOR TIER 2 INFANTRY",
  "pl": "GONDOR TIER 2 INFANTRY"
}
```

### edusort.line_character

Terms: character

```json
{
  "source": "Line character",
  "pl": "Znak linii"
}
```

### eng.animloose.turns_bones_and_its_skeleton_has

Terms: turn

```json
{
  "source": "{x} turns {nq} bones and its skeleton has {bones_n}",
  "pl": "{x} obraca kości {nq} i jego szkielet ma {bones_n} "
}
```

### eng.animpack.the_source_ships_no_packs_of

Terms: ship

```json
{
  "source": "the source ships no packs of its own, so it plays vanilla's and they are what is ported",
  "pl": "źródło nie zawiera własnych pakietów, więc używa pakietów oryginalnej gry; to one są portowane"
}
```

### eng.animslot.this_mod_ships_no_animation_packs

Terms: ship

```json
{
  "source": "this mod ships no animation packs of its own (the game plays vanilla's), so there is no pack of its own to save into",
  "pl": "ten mod nie zawiera własnych pakietów animacji (gra odtwarza pakiety oryginalnej gry), więc nie ma własnego pakietu do zapisania zmian"
}
```

### eng.armory.not_a_model_file

Terms: mesh

```json
{
  "source": "{name} is not a .obj, .glb, .gltf, .dae or .mesh",
  "pl": "{name} nie jest plikiem .obj, .glb, .gltf, .dae ani .mesh"
}
```

### eng.armory.sheet_format

Terms: texture

```json
{
  "source": "{name}: write .png, .tga, .jpg, .bmp, .dds or .texture",
  "pl": "{name}: zapis .png, .tga, .jpg, .bmp, .dds lub .texture"
}
```

### eng.armory.too_many_vertices

Terms: mesh

```json
{
  "source": "{n:,} vertices: a .mesh indexes at most 65,536",
  "pl": "Wierzchołki {n:,}: a .mesh indeksuje maksymalnie 65 536"
}
```

### eng.buildings.every_one_of_the_32_real

Terms: religion

```json
{
  "source": "every one of the 32 real temple_ lines also carries a `religion` line; this one has none.",
  "pl": "Każda z 32 rzeczywistych linii świątyni  ma również linię `religion`; ta nie ma żadnej."
}
```

### eng.buildings.hidden_ceiling_note

Terms: ship

```json
{
  "source": "TWCenter's List of Hardcoded Limits puts the ceiling at 63 or 64 and says more crash the game. Divide and Conquer ships 75 and ROCSS 74, and both play, so it is not enforced here.",
  "pl": "Lista stałych limitów na TWCenter podaje limit 63 lub 64 i ostrzega przed awarią gry po jego przekroczeniu. Divide and Conquer zawiera 75, a ROCSS 74 i oba działają, dlatego ten limit nie jest tutaj egzekwowany."
}
```

### eng.buildings.line_building_has_no_opening_brace

Terms: building

```json
{
  "source": "line {x}: `building {name}` has no opening brace",
  "pl": "linia {x}: `building {name}` nie ma przyczepy otwierającej"
}
```

### eng.campaint.is_a_marker_colour_black_is

Terms: port_verb

```json
{
  "source": "{rgb} {rgb2} {rgb3} is a marker colour - black is where a settlement stands and white is where a port does, so neither can be a province",
  "pl": "{rgb} {rgb2} {rgb3} jest kolorem markerów - czarny to miejsce, w którym stoi osada, a biały to miejsce, w którym stoi port, więc żaden z nich nie może być prowincją"
}
```

### eng.campaint.is_not_a_marker_map_regions

Terms: port_verb

```json
{
  "source": "{marker} is not a marker - map_regions.tga has two, the settlement and the port",
  "pl": "{marker} nie jest markerem - map_regions.tga ma dwa, osada i port"
}
```

### eng.campaint.settlement_or_port_pixels_left_alone

Terms: port_verb

```json
{
  "source": {
    "one": "{count} settlement or port pixel left alone",
    "other": "{count} settlement or port pixels left alone"
  },
  "pl": {
    "one": "Pozostawiono bez zmian {count} piksel osady lub portu",
    "few": "Pozostawiono bez zmian {count} piksele osady lub portu",
    "many": "Pozostawiono bez zmian {count} pikseli osady lub portu",
    "other": "Pozostawiono bez zmian {count} piksela osady lub portu"
  }
}
```

### eng.campaint.ships_own_so_it_does_not_see

Terms: ship

```json
{
  "source": {
    "one": "{skipped} ships its own {REGIONS_TGA}, so it does not see these pixels and {name} does not exist there",
    "other": "{skipped} ship their own {REGIONS_TGA}, so they do not see these pixels and {name} does not exist there"
  },
  "pl": {
    "one": "{skipped} wysyła swój własny {REGIONS_TGA} , więc nie widzi tych pikseli i {name} nie istnieje tam",
    "few": "{skipped} wysyła własny {REGIONS_TGA} , więc nie widzą tych pikseli i {name} nie istnieje tam",
    "many": "{skipped} wysyła własny {REGIONS_TGA} , więc nie widzą tych pikseli i {name} nie istnieje tam",
    "other": "{skipped} wysyła własny {REGIONS_TGA} , więc nie widzą tych pikseli i {name} nie istnieje tam"
  }
}
```

### eng.campevents.is_not_one_of_the_eight

Terms: ship

```json
{
  "source": "`{kind}` is not one of the eight the engine has; the file the engine ships declares {and_list}",
  "pl": "`{kind}` nie jest jednym z ośmiu silników , w pliku statków silników deklaruje {and_list} "
}
```

### eng.campevents.line_event_takes_a_category_and

Terms: event

```json
{
  "source": "line {x}: `event` takes a category and a label; {parts} is a third value",
  "pl": "wiersz {x}: `event` bierze kategorię i etykietę; {parts} jest trzecią wartością"
}
```

### eng.campevents.line_is_before_the_first_event

Terms: event

```json
{
  "source": "line {x}: `{code}` is before the first `event` line, so nothing reads it",
  "pl": "linia {x}: `{code}` jest przed pierwszą linią `event`, więc nic go nie czyta"
}
```

### eng.campfiles.this_mod_ships_only_so_the

Terms: ship

```json
{
  "source": "this mod ships only {name}, so the keys go straight into the compiled archive",
  "pl": "Ten mod wysyła tylko {name} , więc klucze idą prosto do kompilowanego archiwum"
}
```

### eng.campimport.has_no_faction_block_so_name

Terms: faction

```json
{
  "source": "{POOL_REL} has no `faction: {slot}` block, so {sum} name(s) of its characters have no pool to go in",
  "pl": "{POOL_REL} nie ma bloku `faction: {slot}`, więc nazwy {sum} z jego postaci nie mają żadnego puli do wejścia"
}
```

### eng.campnew.is_not_on_disk_and_ships

Terms: ship

```json
{
  "source": "{REGIONS_REL} is not on disk and {source} ships no map of its own, so there is no region list for this campaign to read",
  "pl": "{REGIONS_REL} nie jest na dysku i {source} nie wysyła własnej mapy, więc nie ma listy regionów dla tej kampanii do przeczytania"
}
```

### eng.campnew.nothing_names_on_the_new_game_menu_archive

Terms: ship

```json
{
  "source": "nothing names {name} on the new-game menu, so the engine shows the key {head}TITLE. {descr_rel} is where that lives and the Descriptions panel writes it. This mod ships only the compiled archive, which is where the key would go.",
  "pl": "w menu nowej gry nie ma nazwy {name}, więc silnik wyświetla klucz {head} TITLE.  {descr_rel} to miejsce, w którym to żyje, a panel Opisów to zapisuje. Ten mod dostarcza tylko skompilowane archiwum, czyli miejsce, w którym powinien znajdować się klucz."
}
```

### eng.campnew.ships_map_layer_s_of_its

Terms: ship

```json
{
  "source": "{source} ships {layers_n} map layer(s) of its own ({layers}), so the copy gets a copy of them too and the two campaigns are then two maps to keep in step. The map screen draws whichever one the campaign you have open reads.",
  "pl": "{source} wysyła własną warstwę mapy {layers_n} ({layers} ), więc kopia otrzymuje również kopię z nich, a dwie kampanie są następnie dwiema mapami, aby zachować krok."
}
```

### eng.campstrat.faction_relationships_does_not_read_as

Terms: faction

```json
{
  "source": "faction_relationships does not read as `faction_relationships <faction>, <how> <faction…>`: {s}",
  "pl": "faction_relationships nie czyta się jako `faction_relationships <faction>, <how> <faction…>` : {s} "
}
```

### eng.campstrat.faction_standings_does_not_read_as

Terms: faction

```json
{
  "source": "faction_standings does not read as `faction_standings <faction>, <value> <faction…>`: {s}",
  "pl": "faction_standings nie czyta się jako `faction_standings <faction>, <value> <faction…>` : {s} "
}
```

### eng.campstrat.fort_line_does_not_read_as

Terms: culture

```json
{
  "source": "{word} line does not read as `{word} <x> <y> [<type> culture <culture>]`: {line}",
  "pl": "Linia {word} nie jest czytana jako `{word} <x> <y> [<type> culture <culture>]`: {line} "
}
```

### eng.campstrat.settlement_header_says_the_engine_knows

Terms: castle

```json
{
  "source": "settlement header says {kind}; the engine knows `settlement` and `settlement castle`",
  "pl": "Na nagłówku osady napisano {kind}; silnik zna `settlement` i `settlement castle` "
}
```

### eng.campstrat.unit_line_does_not_read_as

Terms: armour

```json
{
  "source": "unit line does not read as `unit <name> exp N armour N weapon_lvl N`: {s}",
  "pl": "linia jednostkowa nie czyta się jako `unit <name> exp N armour N weapon_lvl N`: {s} "
}
```

### eng.cas.w_text_latin1

Terms: character

```json
{
  "source": "{value} has a character a .cas cannot hold (it is written in Latin-1)",
  "pl": "{value} ma znak a .cas nie może utrzymać (jest napisany w języku łacińskim-1)"
}
```

### eng.cas.w_text_long

Terms: character

```json
{
  "source": "a name of {n:,} characters is longer than the reader takes",
  "pl": "nazwa znaków {n:,} jest dłuższa niż czytelnik bierze"
}
```

### eng.casanim.turns_bones_and_the_skeleton_has

Terms: turn

```json
{
  "source": "{name} turns {nq} bones and the skeleton {x} has {bones_n}: it is another skeleton's animation",
  "pl": "{name} obraca kości {nq} i szkielet {x} ma {bones_n}: to jest animacja innego szkieletu"
}
```

### eng.climatenew.a_climate_name_the_battle_map

Terms: ship

```json
{
  "source": "{problem} A climate name the battle map does not know is a crash when a battle starts in it, so a new name is the half of this operation that cannot be checked against this mod. Taking over one of the twelve the engine ships - {SPARE} are spare by name - needs no such check.",
  "pl": "{problem} Nazwa klimatu, której mapa bitwy nie zna, powoduje awarię, gdy rozpoczyna się w niej bitwa, więc nowa nazwa to połowa tej operacji, której nie można sprawdzić w odniesieniu do tego moda. Przejęcie jednego z dwunastu statków silnikowych – {SPARE} z nazwy są zapasowe – nie wymaga takiej kontroli."
}
```

### eng.climatenew.all_four_mods_measured_for_this

Terms: ship

```json
{
  "source": "all four mods measured for this declare exactly the twelve climates the engine ships, in the engine's order, and not one added a thirteenth. Divide and Conquer has a wholly custom map and took over unused1 rather than adding a name.",
  "pl": "wszystkie cztery sprawdzone mody deklarują dokładnie dwanaście klimatów dostarczanych przez silnik, w jego kolejności; żaden nie dodał trzynastego. Divide and Conquer ma całkowicie własną mapę i przejął unused1, zamiast dodawać nazwę."
}
```

### eng.codeview.length_says_but_text_is

Terms: character

```json
{
  "source": "line {line}'s length says {said} but the text beside it is {should} characters - every modeldb string is written `<length> <text>`",
  "pl": "wiersz {line} długość mówi {said} ale tekst obok niego jest znakami {should} - każda strona modeldb jest napisana `<length> <text>` "
}
```

### eng.codeview.length_says_but_text_is_and_more

Terms: character

```json
{
  "source": "line {line}'s length says {said} but the text beside it is {should} characters (and {more} more like it) - every modeldb string is written `<length> <text>`",
  "pl": "wiersz {line} długość mówi {said} , ale tekst obok jest znakami {should} (i bardziej podobny do niego {more}) - każdy ciąg modeldb jest napisany `<length> <text>` "
}
```

### eng.dupes.a_renamed_block_is_a_real

Terms: soldier

```json
{
  "source": "a renamed block is a real entry now, but nothing in the mod names it yet. Point a unit's `soldier` line at it, or the next cleanup will offer to remove it as unused",
  "pl": "Zmieniony blok jest teraz prawdziwym wpisem, ale nic w modzie nie nazywa go jeszcze. wskaż linię `soldier` jednostki do niego, albo następne sprzątanie będzie oferować usunąć go jako niewykorzystany"
}
```

### eng.fileswap.this_dds_cannot_go_into_a

Terms: texture

```json
{
  "source": "this DDS cannot go into a .texture: {e}",
  "pl": "ten DDS nie może przejść do .texture: {e}"
}
```

### eng.gamelog.known_5

Terms: turn

```json
{
  "source": "When a {b} of {a} turns into a {c} (a city made a castle or back), its buildings change by their chains' convert_to lines, here into a level {a} may not build. Check those levels' requires lines in Buildings, or the convert_to lines.",
  "pl": "Kiedy {b} z {a} przekształca się w {c} (miasto zrobione z zamku lub z tyłu), jego budynki zmieniają się liniami convert_to swoich łańcuchów, tutaj na poziom, który {a} nie może zbudować. Sprawdź te poziomy \" wymaga linii w Budynkach, lub linii convert_to."
}
```

### eng.guilds.guild_is_declared_twice_the_engine

Terms: guild

```json
{
  "source": "`Guild {name}` is declared twice - the engine reads the first block and ignores this one (line {x})",
  "pl": "`Guild {name}` jest zadeklarowany dwa razy - silnik odczytuje pierwszy blok i ignoruje ten (powieść {x})"
}
```

### eng.guilds.has_no_levels_line_so_no

Terms: level

```json
{
  "source": "{x} has no `levels` line, so no number of guild points ever completes it",
  "pl": "{x} nie ma linii `levels`, więc żadna liczba punktów gildia nigdy go nie kończy"
}
```

### eng.guilds.levels_counts_upward

Terms: level

```json
{
  "source": "`levels` counts upward - {levels} does not, so a later tier is reached before an earlier one",
  "pl": "`levels` liczy się w górę - {levels} nie liczy, więc osiąga się późniejszy tier przed wcześniejszym"
}
```

### eng.guilds.levels_has_threshold_s_20_of

Terms: level

```json
{
  "source": "`levels` has {nums_n} threshold(s); 20 of the 21 guilds in the installed mods write {LEVEL_COUNT}, one per guild tier",
  "pl": "`levels` ma progu {nums_n}(s); 20 z 21 gildii w zainstalowanych modów piszą {LEVEL_COUNT} , jeden na tier gildii"
}
```

### eng.guilds.levels_takes_whole_numbers

Terms: level

```json
{
  "source": "`levels` takes whole numbers of guild points - {bad} is not one",
  "pl": "`levels` pobiera całkowitą liczbę punktów gildii - {bad} nie jest jednym"
}
```

### eng.guilds.the_scope_letter_is

Terms: guild

```json
{
  "source": "`Guild {guild} {scope} {points}` - the scope letter is {scopes} in every one of the 507 real lines measured",
  "pl": "`Guild {guild} {scope} {points}` - litera zakresu jest {scopes} w każdej z 507 realnych linii mierzonych"
}
```

### eng.heroabilities.not_in_ui_battle_sd_so

Terms: battle

```json
{
  "source": "{owner}: {gone} not in ui/battle.sd, so the button has no picture{why}",
  "pl": "{owner}: {gone} nie ma w ui/battle.sd, więc przycisk nie ma obrazu {why}"
}
```

### eng.mapcheck.second_port_pixel

Terms: port_verb

```json
{
  "source": "a second port pixel at {x},{y}. Only one of them will ever be a port.",
  "pl": "drugi piksel portu w {x}, {y}. Tylko jeden z nich będzie kiedykolwiek portem."
}
```

### eng.mapcheck.second_port_pixel_for_owner

Terms: port_verb

```json
{
  "source": "a second port pixel at {x},{y}, for {owner}. Only one of them will ever be a port.",
  "pl": "drugi piksel portu w {x}, {y}, dla {owner}. Tylko jeden z nich będzie kiedykolwiek portem."
}
```

### eng.mapcheck.starts_with_a_and_map_regions

Terms: port_verb

```json
{
  "source": "{reg} starts with a `{name}` and map_regions.tga has no white port pixel anywhere in it. The building has nowhere to stand.",
  "pl": "{reg} zaczyna się od `{name}`, a map_regions.tga nie ma żadnego białego piksela portu. Budynek nie ma gdzie stanąć."
}
```

### eng.mapcheck.the_port_pixel_at_has_no

Terms: port_verb

```json
{
  "source": "The port pixel at {x},{y} ({who}) has no sea tile on any of its four sides, so nothing can ever dock there and no province can be given the port.",
  "pl": "Piksel portu w {x} , {y} ({who}) nie ma kafelki morskiej na żadnej z czterech stron, więc nic nigdy nie może tam przylądować i żadna prowincja nie może otrzymać portu."
}
```

### eng.mapcheck.the_port_pixel_at_touches_no

Terms: port_verb

```json
{
  "source": "The port pixel at {at},{at2} touches no single region the cardinal rule can give it to, so which province gets the port is whatever the engine decides.",
  "pl": "Piksel portu w {at} , {at2} nie dotyka żadnego regionu, który może być podany przez zasadę kardynału, więc prowincja, która otrzymuje port, jest tym, co decyduje silnik."
}
```

### eng.mapfe.the_frame_at_x_g_y

Terms: frame

```json
{
  "source": "the frame at ({x:g},{y:g}) {w:g}x{h:g} does not touch the {gw}x{gh} grid",
  "pl": "ramka w ({x:g} , {y:g}) {w:g} x {h:g} nie dotyka sieci {gw} x {gh}"
}
```

### eng.mapfe.the_frame_is_w_g_x

Terms: frame

```json
{
  "source": "the frame is {w:g}x{h:g} tiles",
  "pl": "ramy: kafelki {w:g} x {h:g}"
}
```

### eng.mapfe.the_frame_is_w_g_x_2

Terms: frame

```json
{
  "source": "the frame is {w:g}x{h:g} tiles, and fewer than {MIN_TILES} a side is not a picture of anything",
  "pl": "Ramka to kafelki {w:g} x {h:g}, a mniej niż {MIN_TILES} strona nie jest obrazem niczego"
}
```

### eng.mapnewreal.province_s_grown_from_their_cities

Terms: port_verb

```json
{
  "source": "{seats_n} province(s) grown from their cities over the land, {ports} with a port on the coast",
  "pl": "Prowincja {seats_n}(s) wyprodukowana z swoich miast nad lądem, {ports} z portem na wybrzeżu"
}
```

### eng.mercpools.line_a_second_regions_line_for

Terms: region

```json
{
  "source": "line {x}: a second `regions` line for pool {name}; the first one is edited",
  "pl": "wiersz {x}: druga wiersz `regions` dla puli {name}; pierwsza jest edytowana"
}
```

### eng.mesh.is_not_a_mesh_expected_a

Terms: mesh

```json
{
  "source": "{name} is not a .mesh (expected a boost archive, found {sig})",
  "pl": "{name} nie jest plikiem .mesh (oczekiwano archiwum boost, znaleziono {sig} )"
}
```

### eng.meshwrite.n_vertices_a_mesh_indexes_at

Terms: mesh

```json
{
  "source": "{n:,} vertices: a .mesh indexes at most 65,536",
  "pl": "Wierzchołki {n:,}: a .mesh indeksuje maksymalnie 65 536"
}
```

### eng.minorfiles.line_before_the_first_culture_line

Terms: culture

```json
{
  "source": "line {x}: `{key}` before the first `culture` line",
  "pl": "linia {x}: `{key}` przed pierwszą linią `culture`"
}
```

### eng.minorfiles.line_religion_has_no_closing_brace

Terms: religion

```json
{
  "source": "line {x}: `religion {value}` has no closing brace",
  "pl": "linia {x}: `religion {value}` nie ma braku zamknięcia"
}
```

### eng.minorfiles.line_religions_has_no_closing_brace

Terms: religion

```json
{
  "source": "line {x}: `religions` has no closing brace",
  "pl": "linia {x}: `religions` nie ma braku zamknięcia"
}
```

### eng.minorfiles.this_cultures_port_ladder_has_lines

Terms: port_verb

```json
{
  "source": "this culture's port ladder has {ports_n} lines and the edit sent {values_n} - adding or removing a port level is done in the code view",
  "pl": "Ławnika portu tej kultury ma linie {ports_n} i edycja przesłana {values_n} - dodawanie lub usunięcie poziomu portu jest wykonywane w widoku kodu"
}
```

### eng.minorfiles.this_text_has_no_faction_line

Terms: faction

```json
{
  "source": "this text has no `faction: <name>` line",
  "pl": "w tym tekście nie ma `faction: <name>` line"
}
```

### eng.modeldb.characters_left_over_after_the_entry

Terms: character

```json
{
  "source": "{x} characters left over after the entry",
  "pl": "{x} znaki pozostałe po wpisie"
}
```

### eng.modeldb.this_does_not_start_like_a

Terms: archive

```json
{
  "source": "this does not start like a battle_models.modeldb: its first token should be the length of 'serialization::archive', and it is {split}. A file re-saved by a text editor in the wrong encoding usually looks like this.",
  "pl": "plik nie zaczyna się jak battle_models.modeldb: pierwszy token powinien określać długość 'serialization::archive', a ma wartość {split}. Tak zwykle wygląda plik zapisany ponownie w edytorze tekstu z niewłaściwym kodowaniem."
}
```

### eng.namekeys.this_mod_ships_only_strings_bin

Terms: ship

```json
{
  "source": "this mod ships only {name}.strings.bin, so the keys go straight into the compiled archive",
  "pl": "Ta mod wysyła tylko {name} . strings.bin , więc klucze idą prosto do złożonego archiwum"
}
```

### eng.osmmap.openstreetmap_is_off_turn_it_on

Terms: turn

```json
{
  "source": "OpenStreetMap is off. Turn it on under Settings, Real-world map, first. Nothing was sent.",
  "pl": "OpenStreetMap jest wyłączony."
}
```

### eng.regiondel.already_has_a_port_of_its

Terms: port_verb

```json
{
  "source": "{heir} already has a port of its own, so keeping this one leaves two port pixels in one province and the engine uses one of them. Check reports that as a second port.",
  "pl": "{heir} ma już własny port, więc utrzymanie tego pozostawia dwa piksele portu w jednej prowincji i silnik używa jednego z nich."
}
```

### eng.regiondel.the_region_section_and_its_fort

Terms: region

```json
{
  "source": "{rel}: the `region {name}` section and its {kept_n} fort or watchtower line(s) go with it, because there is no heir to move them to",
  "pl": "{rel}: sekcja `region {name}` i jej linie fortu lub wieży strażniczej {kept_n} idą z nią, ponieważ nie ma następcy, do którego można by je przenieść"
}
```

### eng.scriptfiles.grid_copy

Terms: recruit

```json
{
  "source": "the copy One Recruitment Grid put in",
  "pl": "kopia umieszczona przez One Recruitment Grid"
}
```

### eng.scriptfiles.grid_in

Terms: recruit

```json
{
  "source": "One Recruitment Grid is in this mod already",
  "pl": "One Recruitment Grid jest już w tym modzie"
}
```

### eng.scriptfiles.grid_not_in

Terms: recruit

```json
{
  "source": "One Recruitment Grid is not in this mod",
  "pl": "One Recruitment Grid nie jest zainstalowany w tym modzie"
}
```

### eng.scriptwords.act_help_console_3820

Terms: battle

```json
{
  "source": "any command of the game's console (Pick... shows them all), like add_money egypt 500 or kill_character \"{general}\" Battle - {town} {faction} {owner} {general} {turn} {people} are filled in",
  "pl": "dowolne polecenie konsoli gry (Wybierz… pokazuje wszystkie), np. add_money egypt 500 lub kill_character \"{general}\" Battle. Wartości {town} {faction} {owner} {general} {turn} {people} są uzupełniane"
}
```

### eng.scriptwords.addon_one_recruit_grid_21e4

Terms: recruit

```json
{
  "source": "One Recruitment Grid (Medieval II)",
  "pl": "One Recruitment Grid (Medieval II)"
}
```

### eng.server.the_frame_is_not_four_numbers

Terms: frame

```json
{
  "source": "the frame is not four numbers",
  "pl": "Ramy nie są cztery liczby."
}
```

### eng.sidefiles.line_a_symbol_sheet_before_any

Terms: faction

```json
{
  "source": "line {x}: a symbol sheet before any `factions` line",
  "pl": "wiersz {x}: arkusz symboli przed każdą wierszą `factions`"
}
```

### eng.sidefiles.units_carry_an_undeclared_animal

Terms: animal

```json
{
  "source": {
    "one": "{units}{and_more} carries `animal {name}`, and this file does not declare it (it declares {have})",
    "other": "{units}{and_more} carry `animal {name}`, and this file does not declare it (it declares {have})"
  },
  "pl": {
    "one": "{units} {and_more} zawiera `animal {name}` , a ten plik nie deklaruje go (oświadcza {have})",
    "few": "{units} {and_more} zawiera `animal {name}` , a ten plik nie deklaruje go (oświadcza {have})",
    "many": "{units} {and_more} zawiera `animal {name}` , a ten plik nie deklaruje go (oświadcza {have})",
    "other": "{units} {and_more} zawiera `animal {name}` , a ten plik nie deklaruje go (oświadcza {have})"
  }
}
```

### eng.sprites.truncated_texture_file

Terms: texture

```json
{
  "source": "truncated .texture file",
  "pl": "niekompletny plik .texture"
}
```

### eng.stratcamp.is_not_a_word_the_engine

Terms: ship

```json
{
  "source": "{name} is not a word the engine reads - the one it reads is marian_reforms_disabled - so this line does nothing. Third Age Reforged ships it too",
  "pl": "{name} nie jest słowem odczytywanym przez silnik. Silnik odczytuje marian_reforms_disabled, więc ten wiersz nic nie robi. Third Age Reforged także go zawiera"
}
```

### eng.stratedit.a_settlement_block_opens_with_the

Terms: castle

```json
{
  "source": "a settlement block opens with the word `settlement`, on its own or followed by `castle`. This one opens with {head}",
  "pl": "blok osady otwiera się słowem `settlement` , samodzielnie lub następnie z `castle` . Ten otwiera się słowem {head} "
}
```

### eng.stratedit.stays_on_the_map_with_no

Terms: ship

```json
{
  "source": "{region} stays on the map with no settlement in it. Vanilla ships one like that (Durazzo); Health lists such a province as a note.",
  "pl": "{region} pozostaje na mapie bez żadnej osady. Oryginalna gra dostarcza taki egzemplarz (Durazzo); Zdrowie wymienia taką prowincję jako notatkę."
}
```

### eng.stratedit.the_header_says_the_engine_reads

Terms: castle, settlement

```json
{
  "source": "The header says {kind}. The engine reads `settlement` and `settlement castle` and nothing else.",
  "pl": "Na nagłówku pisze {kind}, a na silniku `settlement` i `settlement castle`."
}
```

### eng.stratedit.two_levels_of_stand_in_this

Terms: ship

```json
{
  "source": "Two levels of {x} stand in this settlement at once. Third Age Reforged ships four settlements like it, so it is not fatal, but only one of them is the building.",
  "pl": "W tym osiedlu stoją jednocześnie dwa poziomy {x}. Third Age Reforged dostarcza cztery takie osady, więc nie jest to śmiertelne, ale tylko jedna z nich to budynek."
}
```

### eng.stratobj.is_pixel_none_of_the_800_port

Terms: port_verb

```json
{
  "source": "{gx},{gy} is {name}'s port pixel. None of the 800 forts and watchtowers measured stands on a settlement or a port.",
  "pl": "{gx} , {gy} to piksel portu {name}. Żaden z 800 mierzonych fortów i wież strażniczych nie stoi na osadze lub w porcie."
}
```

### eng.stratobj.is_pixel_none_of_the_800_settlement

Terms: port_verb

```json
{
  "source": "{gx},{gy} is {name}'s settlement pixel. None of the 800 forts and watchtowers measured stands on a settlement or a port.",
  "pl": "{gx} , {gy} to piksel osadnictwa {name}. Żaden z 800 mierzonych fortów i wież strażniczych nie stoi na osadnictwie lub w porcie."
}
```

### eng.stringsbin.a_single_string_cannot_exceed_65535

Terms: character

```json
{
  "source": "a single string cannot exceed 65535 characters (this one is {units})",
  "pl": "pojedynczy ciąg nie może przekraczać 65535 znaków (ten jest {units})"
}
```

### eng.stringsbin.a_string_says_it_is_characters

Terms: character

```json
{
  "source": "a string says it is {units} characters long but only {x} are left in the file",
  "pl": "String mówi, że jest to {units} znaki długości, ale tylko {x} pozostają w pliku"
}
```

### eng.transfer.mercenary_icons_card_info_card_go

Terms: unit

```json
{
  "source": "mercenary icons: card/info card go to ui/units/{MERC_CARD_DIR}/ + ui/unit_info/{MERC_INFO_DIR}/ (pinned via card_pic_dir/info_pic_dir).",
  "pl": "ikony najemników: karta/karta informacyjna przejdź do ui/units/{MERC_CARD_DIR}/ + ui/unit_info/{MERC_INFO_DIR}/ (przypięta przez card_pic_dir / info_pic_dir )."
}
```

### eng.transfer.mercenary_to_actually_recruit_it_add

Terms: campaign

```json
{
  "source": "mercenary: to actually recruit it, add a pool entry in data/world/maps/campaign/imperial_campaign/descr_mercenaries.txt - this tool does not write that file.",
  "pl": "najemnik: aby go faktycznie zrekrutować, dodaj wpis puli w data/world/maps/campaign/imperial_campaign/descr_mercenaries.txt - to narzędzie nie zapisuje tego pliku."
}
```

### eng.transfer.projectile_model_cas_files_were_copied

Terms: missile

```json
{
  "source": "projectile model (.cas) files were copied, but their textures under data/models_missile/textures/ are not chased - verify the missile model renders and copy its texture if it's missing in the destination.",
  "pl": "pliki modelu pocisku (.cas) zostały skopiowane, ale tekstury z data/models_missile/textures/ nie są wyszukiwane. Sprawdź wygląd modelu pocisku i skopiuj jego teksturę, jeśli brakuje jej w celu."
}
```

### eng.winconds.could_not_be_read_the_stock

Terms: ship

```json
{
  "source": "{rel} could not be read ({exc}). The stock game ships it on disk and so do both installed mods, so a campaign without one is a campaign nobody can win",
  "pl": "Nie można odczytać {rel} ( {exc} ). Gra standardowa dostarcza ją na dysku, podobnie jak oba zainstalowane mody, zatem kampania bez jednego z nich jest kampanią, której nikt nie może wygrać"
}
```

### facaudit.world_maps_campaign

Terms: campaign

```json
{
  "source": "world/maps/campaign/{camp}/{rel}",
  "pl": "world/maps/campaign/{camp}/{rel}"
}
```

### factions.bring_frame_units

Terms: frame

```json
{
  "source": "Keep the frame faction's units as well",
  "pl": "Zachowaj również jednostki frakcji bazowej"
}
```

### guided.florins_the_smith_charges_to_upgrade

Terms: charge

```json
{
  "source": "Florins the smith charges to upgrade its weapons.",
  "pl": "Koszt ulepszenia broni u kowala, we florinach."
}
```

### guided.florins_the_smith_charges_to_upgrade_2

Terms: charge

```json
{
  "source": "Florins the smith charges to upgrade its armour.",
  "pl": "Koszt ulepszenia pancerza u kowala, we florinach."
}
```

### guided.infantry_cavalry_siege_ship_handler

Terms: ship

```json
{
  "source": "infantry | cavalry | siege | ship | handler",
  "pl": "Piechota , kawaleria , oblężenie statku ."
}
```

### guided.light_heavy_missile_spearmen

Terms: missile

```json
{
  "source": "light | heavy | missile | spearmen",
  "pl": "light | heavy | missile | spearmen"
}
```

### guided.optional_the_effect_played_when_the_weapon

Terms: turn

```json
{
  "source": "Optional. The effect played when the weapon <i>fires</i>: <code>musket_shot_set</code> for gunpowder units, and essentially nothing else. Setting it is what turns this line from 11 values into 12; clearing it turns it back.",
  "pl": "Opcjonalne. Efekt odtwarzany, gdy broń <i>strzela</i>: <code>musket_shot_set</code> dla jednostek prochowych i praktycznie nic innego. Ustawienie tej wartości zwiększa liczbę wartości wiersza z 11 do 12; wyczyszczenie przywraca 11."
}
```

### guided.vanilla_ships_it_commented_out

Terms: ship

```json
{
  "source": "Vanilla ships it commented out.",
  "pl": "W oryginalnej grze występuje jako komentarz."
}
```

### guided.vanilla_ships_it_commented_out_on

Terms: ship

```json
{
  "source": "Vanilla ships it commented out on every unit.",
  "pl": "Oryginalna gra wysyła komentarze na każdą jednostkę."
}
```

### home.mounted_pack

Terms: mount

```json
{
  "source": "📦 mounted pack",
  "pl": "📦 podłączony pakiet"
}
```

### home.pick_your_medieval_ii_folder_it

Terms: mod

```json
{
  "source": "Pick your Medieval II folder (it contains \"mods\")",
  "pl": "Wybierz folder Medieval II (zawierający folder \"mods\")"
}
```

### home.start_the_soldier_row_on_base

Terms: soldier

```json
{
  "source": "Start the Soldier row on <b>Base</b>",
  "pl": "Zaczynaj wiersz Soldier od <b>Bazy</b>"
}
```

### map3d.building_the_mesh

Terms: building

```json
{
  "source": "Building the mesh…",
  "pl": "Tworzenie siatki…"
}
```

### map3d.frame_the_whole_map_again

Terms: frame

```json
{
  "source": "Frame the whole map again",
  "pl": "Dopasuj widok do całej mapy"
}
```

### mapcheck.records_what_is_wrong_now_as

Terms: record

```json
{
  "source": "Records what is wrong NOW as inherited. It changes nothing in the mod.",
  "pl": "Zapisuje obecne problemy jako odziedziczone. Nie zmienia niczego w modzie."
}
```

### mapfe.before_this_panel_the_picture_was

Terms: frame

```json
{
  "source": "Before this panel the picture ({was}) was squeezed into {grid} and scaled again to get onto the canvas. It is now drawn at its own size on the frame below, so nothing resamples it.",
  "pl": "Przed otwarciem tego panelu obraz ({was}) był wciskany w {grid}, a następnie ponownie skalowany do płótna. Teraz jest rysowany we własnym rozmiarze na poniższym kadrze, bez ponownego próbkowania."
}
```

### mapfe.proposed_frame

Terms: frame

```json
{
  "source": "↺ Proposed frame",
  "pl": "↺ Proponowany kadr"
}
```

### mapfe.put_the_frame_back_to_the

Terms: frame

```json
{
  "source": "put the frame back to the proposed one",
  "pl": "/Prowadzisz ramę do zaproponowanej."
}
```

### mapfe.the_frame

Terms: frame

```json
{
  "source": "the frame",
  "pl": "kadr"
}
```

### mapfe.the_frame_2

Terms: frame

```json
{
  "source": "<span>The frame</span> <span class=\"count\" id=\"cfeFigs\">{cfeFigureText}</span>",
  "pl": "<span> Ramka </span> <span class=\"count\" id=\"cfeFigs\"> {cfeFigureText} </span> "
}
```

### mapfe.the_frame_is_which_rectangle_of

Terms: frame

```json
{
  "source": "The frame is which rectangle of the map the picture is a picture of. It starts as the smallest one the picture's shape can be and still hold the whole map; drag it or its corners to move it, and the shape is held because that is what lets one zoom draw the picture 1:1. Nothing can work it out from the picture - one installed mod's has a painted border round the map and two are not maps at all.",
  "pl": "Ramka to prostokąt mapy, z której obrazek jest obrazem. Zaczyna się jako najmniejszy, który może być kształtem obrazu i nadal utrzymuje całą mapę; ciągnąć go lub jego kąty, aby je poruszyć, a kształt jest trzymany, ponieważ to umożliwia zwiększenie rysunku 1:1. Nic nie może wyciągnąć go z obrazu - jeden zainstalowany mod ma malowaną granicę wokół mapy, a dwa w ogóle nie są mapami."
}
```

### mapfe.the_front_end_layer_is_not

Terms: frame

```json
{
  "source": "The front-end layer is not ticked, so the picture is not on the canvas - the frame is. Key <b>1</b> ticks it.",
  "pl": "Warstwa front-end nie jest zaznaczona, więc obraz nie znajduje się na płótnie - jest rama. Klucz <b> 1 </b> zaznacza to."
}
```

### maplabels.character

Terms: character

```json
{
  "source": "character:{line}",
  "pl": "znak: {line} "
}
```

### maplabels.port

Terms: port_verb

```json
{
  "source": "port:{region}",
  "pl": "port:{region}"
}
```

### maplabels.port_2

Terms: port_verb

```json
{
  "source": "Port · {x}",
  "pl": "Port · {x}"
}
```

### mapquery.building_that_map

Terms: building

```json
{
  "source": "building that map",
  "pl": "tworzenie tej mapy"
}
```

### mapsize.turn_the_real_world_switch_on

Terms: turn

```json
{
  "source": "Turn the Real world switch on in Settings first.",
  "pl": "Najpierw włącz w ustawieniach rzeczywisty świat."
}
```

### minorfiles.port_ladder_line_s_in_the

Terms: port_verb

```json
{
  "source": "Port ladder <span class=\"count\">{ports_n} line(s), in the file's own order: each port level is a <code>port_land</code> and a <code>port_sea</code> model. Adding or removing a level is a pair of lines placed in that order, so it is done in the code view; what each line points at is here.</span>",
  "pl": "Drabinka portów <span class=\"count\"> {ports_n} linie, w kolejności pliku: każdy poziom portu to model <code> port_land </code> i <code> port_sea </code>. Dodanie lub usunięcie poziomu to para linii ułożonych w tej kolejności, więc odbywa się to w widoku kodu; to, na co wskazuje każda linia, znajduje się tutaj. </span>"
}
```

### minorfiles.this_culture_has_no_port_lines

Terms: port_verb

```json
{
  "source": "This culture has no port lines.",
  "pl": "Ta kultura nie ma linii portu."
}
```

### minorfiles.where_it_starts_every_regions_religions

Terms: ship

```json
{
  "source": "Where it starts <span class=\"count\">Every region's <code>religions { … }</code> line gets <code>{name} 0</code>, in every descr_regions.txt this mod ships. A share given here comes out of the region's other religions in proportion, so each line still adds up to 100.</span>",
  "pl": "Gdzie się zaczyna <span class=\"count\"> Linia <code> religions { … } </code> każdego regionu otrzymuje <code> {name} 0 </code> , w każdym descr_regions.txt ten mod jest dostarczany. Podana tutaj część pochodzi proporcjonalnie z innych religii regionu, więc każda linia nadal daje 100. </span>"
}
```

### osmmap.mylaes_layout_the_maps_layers_as

Terms: port_verb

```json
{
  "source": "Mylae’s layout: the map’s layers as they are on disk, bbox_coords.txt, and reference/ with map_regions.txt (each province’s colour, city and port), the historic sites already fetched for this box, and the picture. Only the picture uses the internet.",
  "pl": "Mapy: warstwy mapy tak, jak są na dysku, bbox_coords.txt i referencje / z map_regions.txt (każdy kolor prowincji, miasto i port), miejsca historyczne już pobierane dla tej skrzynki i obraz."
}
```

### osmmap.open_settings_to_turn_it_on

Terms: turn

```json
{
  "source": "⚙ Open Settings to turn it on",
  "pl": " Otwórz ustawienia do włączenia"
}
```

### osmworld.drag_to_pan_wheel_to_zoom

Terms: turn

```json
{
  "source": "Drag to pan, wheel to zoom. Drag the box's corners to resize it, its middle to move it, the violet handle to turn it.",
  "pl": "Przeciągnij do płytki, koło do zoomu, przeciągnij kąty skrzynki, aby zmienić rozmiar, środek, aby ją przesunąć, wioletowy uchwyt, aby ją obrócić."
}
```

### packs.battle_model_entr_travel_with_them

Terms: mount

```json
{
  "source": {
    "one": "{count} battle-model entry travels with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer.",
    "other": "{count} battle-model entries travel with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer."
  },
  "pl": {
    "one": "Razem z nimi podróżuje {count} wpis dotyczący modelu bitwy. Import powoduje zamontowanie pakietu jako mod źródłowego i przerzucenie do normalnego ekranu przenoszenia, więc tam pojawiają się pytania dotyczące kolizji nazw, jednostki podstawowej, własności i wszystkich innych opcji. Nic nie zostanie zapisane, dopóki nie naciśniesz Przenoszenie.",
    "few": "Razem z nimi podróżują {count} wpisy dotyczące modeli bitewnych. Import powoduje zamontowanie pakietu jako mod źródłowego i przerzucenie do normalnego ekranu przenoszenia, więc tam pojawiają się pytania dotyczące kolizji nazw, jednostki podstawowej, własności i wszystkich innych opcji. Nic nie zostanie zapisane, dopóki nie naciśniesz Przenoszenie.",
    "many": "Razem z nimi podróżuje {count} wpisów z modelami bitewnymi. Import powoduje zamontowanie pakietu jako mod źródłowego i przerzucenie do normalnego ekranu przenoszenia, więc tam pojawiają się pytania dotyczące kolizji nazw, jednostki podstawowej, własności i wszystkich innych opcji. Nic nie zostanie zapisane, dopóki nie naciśniesz Przenoszenie.",
    "other": "Razem z nimi podróżuje {count} modelu bitwy. Import powoduje zamontowanie pakietu jako mod źródłowego i przerzucenie do normalnego ekranu przenoszenia, więc tam pojawiają się pytania dotyczące kolizji nazw, jednostki podstawowej, własności i wszystkich innych opcji. Nic nie zostanie zapisane, dopóki nie naciśniesz Przenoszenie."
  }
}
```

### rebels.of_provinces_name_a_rebel_faction

Terms: turn

```json
{
  "source": "{silent_regions} of {regions} provinces name a rebel faction with <code>chance 0</code>, so they spawn no rebels. That is a real setting rather than a fault - it is how a mod turns province rebels off - but it is what those assignments do.",
  "pl": "{silent_regions} prowincji {regions} nazywa frakcję rebeliantów <code> chance 0 </code> , więc nie spadną rebelianci. To raczej realne ustawienie niż błąd – w ten sposób mod wyłącza rebeliantów z prowincji – ale właśnie do tego służą te zadania."
}
```

### regiondel.already_has_a_port_and_only

Terms: port_verb

```json
{
  "source": "{heir} already has a port, and only one of two in a province is\n         ever used - so removing this one is the answer that leaves a map the\n         validator does not report.",
  "pl": "{heir} ma już port, a tylko jeden z dwóch w prowincji jest używany - więc usunięcie tego jest odpowiedzią, która pozostawia mapę, której weryfikujący nie zgłasza."
}
```

### regiondel.has_no_port_of_its_own

Terms: port_verb

```json
{
  "source": "{heir} has no port of its own, so keeping this one gives it a\n         harbour on the coast it is about to inherit.",
  "pl": "{heir} nie ma własnego portu, więc utrzymanie tego daje mu port na wybrzeżu, który ma odziedziczyć."
}
```

### regiondel.its_port

Terms: port_verb

```json
{
  "source": "<span class=\"cmtnm\">Its port</span> <span class=\"cmseg\">",
  "pl": "<span class=\"cmtnm\"> Jego port </span> <span class=\"cmseg\"> "
}
```

### settings.and_more_characters_in_the_diagnostic

Terms: character

```json
{
  "source": "…and {summary_cut} more characters, in the diagnostic log.",
  "pl": "...i {summary_cut} więcej znaków, w dzienniku diagnostycznym."
}
```

### settings.merc

Terms: mercenary

```json
{
  "source": " · merc",
  "pl": " · merc"
}
```

### settings.point_to_your_medieval_ii_install

Terms: mod

```json
{
  "source": "Point to your Medieval II install (contains <b>mods</b>) or a mods folder directly. Remembered next time.",
  "pl": "Wskaż instalację Medieval II (zawiera folder <b>mods</b>) albo bezpośrednio folder modów. Ustawienie zostanie zapamiętane."
}
```

### settings.start_the_soldier_row_on_base

Terms: soldier, building

```json
{
  "source": "Start the <b>Soldier</b> row on <b>Base</b>, so the destination unit's model and projectile are used instead of the transferred unit's. Applies to both modes that have a base unit: building a new unit on one, and replacing one (there the base <i>is</i> the unit being replaced, so its own model and animations stay). Still switchable per unit.",
  "pl": "Rozpoczynaj wiersz <b>Soldier</b> od opcji <b>Base</b>, aby używać modelu i pocisku jednostki docelowej zamiast przenoszonej. Dotyczy obu trybów z jednostką bazową: tworzenia nowej na jej podstawie i zastępowania istniejącej. W drugim trybie bazą <i>jest</i> zastępowana jednostka, więc zachowuje własny model i animacje. Nadal można zmienić ten wybór dla każdej jednostki."
}
```

### settings.use_the_base_units_soldier_line

Terms: soldier

```json
{
  "source": "Use the base unit's <b>soldier</b> line by default",
  "pl": "Domyślnie używaj wiersza <b>soldier</b> jednostki bazowej"
}
```

### soundbanks.has_no_data_the_game_uses

Terms: ship

```json
{
  "source": "{src} has no <code>data/{rel}</code>.<br><span class=\"count\">The game uses its own {label} when a mod does not ship them.</span>",
  "pl": "{src} nie ma <code> data/{rel} </code> . <br> <span class=\"count\"> Gra używa własnego {label}, jeśli mod ich nie dostarcza. </span>"
}
```

### sprites.the_bypass_flag_makes_the_next_normal

Terms: turn

```json
{
  "source": "The bypass flag makes the next normal launch re-render instead of starting, which reads as a crash. Turn it back off when you are done.",
  "pl": "Flaga bypass odtwarza następny normalny start zamiast startu, czytając jako awarię."
}
```

### sprites.this_mod_ships_m2tweop_so_generation

Terms: ship

```json
{
  "source": "This mod ships M2TWEOP, so generation goes through its console.",
  "pl": "Mod ten przesyła M2TWEOP, więc pokolenie przechodzi przez konsołę."
}
```

### sprites.turn_the_flag_back_off

Terms: turn

```json
{
  "source": "Turn the flag back off",
  "pl": "Odwróć flagę."
}
```

### stratmap.draw_a_campaign_map_model_beside

Terms: ship

```json
{
  "source": "Draw a campaign-map model beside the list, without leaving it. Every entry\nthat ships a .CAS gets its own 🧊 button once this is open, and the panel also browses\nevery model file under data/models_strat - including the settlements, which no entry names.",
  "pl": "Narysuj model mapy kampanii obok listy, nie opuszczając jej. Każdy wpis\nktóry wysyła . CAS otrzymuje własny przycisk 🧊 po otwarciu, a panel również przegląda\nkażdy plik modelu pod data/models_strat - łącznie z osadami, w których nie ma wpisów nazw."
}
```

### stratmap.file_named_by_no_model_but

Terms: turn

```json
{
  "source": {
    "one": "{count} file is named by no model, but its bare filename turns up in a <code>descr_*.txt</code> or a script - so it is not offered above either.",
    "other": "{count} files are named by no model, but their bare filename turns up in a <code>descr_*.txt</code> or a script - so they are not offered above either."
  },
  "pl": {
    "one": "{count} plik nie ma nazwy żadnego modelu, ale jego sama nazwa pliku pojawia się w <code> descr_*.txt </code> lub skrypcie - więc nie jest ona również oferowana powyżej.",
    "few": "{count} pliki nie mają nazw bez modelu, ale ich sama nazwa pliku pojawia się w <code> descr_*.txt </code> lub w skrypcie - więc nie są one również oferowane powyżej.",
    "many": "{count} plików nie ma nazw bez modelu, ale ich sama nazwa pliku pojawia się w <code> descr_*.txt </code> lub w skrypcie - więc nie są one również oferowane powyżej.",
    "other": "Pliki {count} nie mają nazw według modelu, ale ich sama nazwa pliku pojawia się w <code> descr_*.txt </code> lub w skrypcie - więc nie są one również oferowane powyżej."
  }
}
```

### stratview.this_mod_ships_no_data_models

Terms: ship

```json
{
  "source": "this mod ships no <code>data/models_strat</code>, so it uses the game's own strat models",
  "pl": "ten mod nie zawiera <code> data/models_strat </code>, więc wykorzystuje własne modele strategiczne gry"
}
```

### transfer.merc_icons_on

Terms: mercenary

```json
{
  "source": "<b>On:</b> cards go to the merc folders only, pinned with <code>card_pic_dir</code> / <code>info_pic_dir</code>.",
  "pl": "<b>Włączone:</b> karty trafiają tylko do folderów merc, z wymuszoną ścieżką przez <code>card_pic_dir</code> / <code>info_pic_dir</code>."
}
```

### v3anim.building_the_glb

Terms: building

```json
{
  "source": "Building the .glb…",
  "pl": "Tworzenie pliku .glb…"
}
```

### v3anim.building_the_obj_zip

Terms: building

```json
{
  "source": "Building the .obj zip…",
  "pl": "Zbudowanie obj zip..."
}
```

### v3anim.played_from_vanillas_pack_this_mod

Terms: ship

```json
{
  "source": "Played from vanilla’s pack: this mod ships none of its own to save an edit into.",
  "pl": "Odtwarzane z pakietu Oryginalna gra: ten mod nie zawiera żadnego własnego, w którym można by zapisać edycję."
}
```

### v3anim.turn_every_key

Terms: turn

```json
{
  "source": "<span>Turn, every key</span> {x}°",
  "pl": "<span> Zwrot, każdy klucz </span> {x} °"
}
```

### v3anim.turns_to

Terms: turn

```json
{
  "source": " · turns {turn}° to {turn2}°",
  "pl": "· obróci {turn} ° do {turn2} °"
}
```

### v3anim.vanillas_skeleton_pack_this_mod_ships

Terms: ship

```json
{
  "source": "vanilla’s skeleton pack (this mod ships none, so the game plays vanilla’s)",
  "pl": "pakiet szkieletu oryginalnej gry (ten mod nie zawiera żadnego pakietu, więc gra odtwarza pakiet oryginalnej gry)"
}
```

### viewer3d.drag_to_turn_wheel_to_zoom

Terms: turn

```json
{
  "source": "drag to turn · wheel to zoom · right-drag to pan",
  "pl": "przeciągnij, aby obrócić · kółko, aby przybliżyć · prawy przycisk, aby przesunąć"
}
```

### viewer3d.draw_the_texture_at_the_size

Terms: ship

```json
{
  "source": "Draw the texture at the size the mod ships it, instead of halving anything over\n1024. That is the size the game draws, so it is the one to check a skin's own detail\nagainst. Off by default: a 2048 sheet is four times the bytes and the video memory\nfor a soldier on screen a few hundred pixels tall.",
  "pl": "Narysuj teksturę w rozmiarze, w jakim mod ją dostarcza, zamiast zmniejszać wszystko o połowę\n1024. Taki rozmiar rysuje gra, więc to on sprawdza szczegóły skórki\nprzeciw. Domyślnie wyłączone: arkusz 2048 to cztery razy więcej bajtów i pamięci wideo\ndla żołnierza na ekranie o wysokości kilkuset pikseli."
}
```

### viewer3d.drawn_at_shipped

Terms: ship

```json
{
  "source": "drawn at <b>{w} × {h}</b> - the size the mod ships, as the game draws it",
  "pl": "narysowany w <b> {w} × {h} </b> - rozmiar dostarczany przez mod, tak jak rysuje go gra"
}
```

### voices.no_name_call

Terms: general

```json
{
  "source": "No name call of its own in the voice bank; it says its class's general line.",
  "pl": "Nie ma własnego nazwiska w banku głosowym; mówi ogólną linię swojej klasy."
}
```

### voices.own_compiled

Terms: event

```json
{
  "source": "The mod's compiled data/sounds/events.dat and events.idx are removed (backed up); the game builds them again on its next start.",
  "pl": "Kompilizowane mody data/sounds/events.dat i events.idx są usunięte (na zapasowy); gra buduje je ponownie na następnym starcie."
}
```

### voices.own_note

Terms: event

```json
{
  "source": "Pick the accent and class it is for and one or more .wav files (the game's own are 22050 Hz, 16-bit, mono). They go in as loose files under new names, the unit gets its own line for that accent and class, and the compiled events.dat and events.idx are removed so the game rebuilds them.",
  "pl": "Wybierz akcent i klasę, dla której jest i jeden lub więcej plików .wav (w grze własne są 22050 Hz, 16-bitowe, mono). Wchodzą one jako luźne pliki pod nowymi nazwami, jednostka otrzymuje swoją własną linię dla tego akcentu i klasy, a skompilowane events.dat i events.idx są usunięte, więc gra je odbudowuje."
}
```

