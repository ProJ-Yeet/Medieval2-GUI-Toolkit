# French review notes

Complete model-written catalogue: 9,605 IDs, including 378 plural objects.
Status remains draft. No native-speaker or in-game approval is claimed.

## Terminology for a French-speaking Medieval II modder

- Animation frame is retained as frame, following the current termbase.
- Settlement is colonie; building line is chaîne de bâtiments; tier is palier.
- Texture sheet is planche; bake is précalculer; kitbash workbench is atelier d’assemblage.
- Ancillary is accessoire; populace is foule; pip is marqueur.
- Please review rasage/raser for the raze module, annonces de nom for voice calls, and the 3D terminology.
- Generic noun placeholders use labels or élément de type to avoid invented plural endings.
- Commands, filenames, enum values and proper names remain literal. French cognates also legitimately match English.

## Scope and UI verification

Home, Settings, Transfer, Unit Editor, Buildings, Models Editor, Armory Studio,
Unit Sounds, Secondary Files, Raw Text, Diagnostics, My Changes and Credits were
inspected in the local French preview at desktop and/or 375 px. Home, Settings,
Transfer and the campaign map were inspected at both widths. Secondary-editor
routes were opened and responsive measurements collected; screenshot captures
containing loading states are not treated as visual approval. Detailed modal
and data-dependent screen coverage remains a future native-review task.
Three responsive fixes keep Home rows, Armory transform controls and My Changes
selectors usable at narrow widths. No mod-data writes were performed for QA.

Existing localization gaps outside en.json remain: server-provided rule titles,
some diagnostic prose and terrain/layer labels, plus generic nouns supplied by code.
Those are already noted in the Phase 88f roadmap and are not missing French IDs.

## Exact glossary exceptions

Each row records the source, the accepted French and the alternate sense/literal
token behind the exact-ID exception. These are review evidence, not blanket waivers.

### app.shared_cards_title

Terms: tile

English: "Grouped by faction: only the tiles whose faction has no card of its own for the unit and borrows another's"

French: "Par faction : uniquement les cartes dont la faction n’a pas d’image propre pour l’unité et utilise celle d’une autre faction"

- tile: Unit/image card rather than a map tile.

### armory.exp_free_turn_title

Terms: turn

English: "Let a block turn to whatever angle packs it smallest, as well as by quarter turns. A block turned so is resampled and its art softens slightly; off, every texel is copied exactly."

French: "Autoriser la rotation d’un bloc à l’angle qui minimise son encombrement, en plus des quarts de tour. Un bloc ainsi tourné est rééchantillonné et son dessin perd légèrement en netteté ; sinon, chaque texel est copié exactement."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### armory.frame_all

Terms: frame

English: "Frame all"

French: "Tout cadrer"

- frame: Camera/image framing or the base faction; not an animation frame.

### armory.head_as_one_title

Terms: turn

English: "Helmet, coif, face, hair and beard move, turn and scale together whichever of them is picked"

French: "Le casque, la coiffe, le visage, les cheveux et la barbe se déplacent, tournent et se redimensionnent ensemble, quel que soit l’élément sélectionné"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### armory.key_frame_all

Terms: frame

English: "Frame everything"

French: "Tout cadrer"

- frame: Camera/image framing or the base faction; not an animation frame.

### armory.key_frame_selected

Terms: frame

English: "Frame the selection"

French: "Cadrer la sélection"

- frame: Camera/image framing or the base faction; not an animation frame.

### armory.look_closer_title

Terms: turn

English: "A closer look: the model in the viewer, to turn, zoom, change its skin and play its animations, before it is pulled in"

French: "Examiner le modèle dans la visionneuse : tourner, zoomer, changer sa texture et lire ses animations avant de l’intégrer"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### armory.mat_skin

Terms: skin

English: "skin"

French: "peau"

- skin: Human skin as a material (peau), rather than a model texture.

### armory.opt_outside_title

Terms: turn

English: "Faces wound the wrong way are turned, so every connected part faces out the way the model does"

French: "Les faces orientées dans le mauvais sens sont retournées pour que chaque partie connectée soit orientée vers l’extérieur comme le modèle"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### armory.stamp_rot

Terms: turn

English: "Turn"

French: "Rotation"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### armory.uv_hint

Terms: turn

English: "Click picks, Shift adds, a drag on nothing draws a box, a drag on the selection moves it. G, R, S move, turn and scale (X or Y holds an axis; click or Enter keeps, Esc or the right button puts back). A selects all. The wheel zooms, the middle button or Alt pans."

French: "Cliquer sélectionne, Maj ajoute, glisser dans le vide dessine un cadre et glisser la sélection la déplace. G, R et S déplacent, tournent et redimensionnent (X ou Y contraint à un axe ; clic ou Entrée valide, Échap ou clic droit rétablit). A sélectionne tout. La molette zoome, le bouton du milieu ou Alt déplace la vue."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### buildings.its_battle_model_has_no_texture

Terms: turn

English: "its battle model has no texture for <b>{x}</b>, so their soldiers would turn up untextured"

French: "son modèle de bataille n’a aucune texture pour <b>{x}</b> ; leurs soldats apparaîtraient donc sans texture"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### buildings.level_3

Terms: level

English: "level:{name}:{x}#{x2}"

French: "level:{name}:{x}#{x2}"

- level: Literal level key/path or numeric field identifier is retained.

### buildings.level_key

Terms: level

English: "level:{name}"

French: "level:{name}"

- level: Literal level key/path or numeric field identifier is retained.

### buildings.this_mod_ships_no_file_at

Terms: ship

English: "This mod ships no file at\nthis path, so the game uses the base game's picture. Drop a .tga in to override it."

French: "Ce mod ne fournit aucun fichier à\nce chemin ; le jeu utilise l’image du jeu de base. Déposez un .tga pour la remplacer."

- ship: Supply/distribute files or content, rather than a naval vessel.

### buildings.units_without_battle_model_texture

Terms: turn

English: {"one": "<b>{count}</b> has no battle-model texture for some of them, so their soldiers would turn up untextured: {list}", "other": "<b>{count}</b> have no battle-model texture for some of them, so their soldiers would turn up untextured: {list}"}

French: {"one": "<b>{count}</b> n’a pas de texture de modèle de bataille pour certaines factions ; leurs soldats apparaîtraient sans texture : {list}", "many": "<b>{count}</b> n’ont pas de texture de modèle de bataille pour certaines factions ; leurs soldats apparaîtraient sans texture : {list}", "other": "<b>{count}</b> n’ont pas de texture de modèle de bataille pour certaines factions ; leurs soldats apparaîtraient sans texture : {list}"}

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### campaint.add_a_province_decide_its_record

Terms: port

English: "Add a province: decide its record, paint it, place its settlement, then its port or skip."

French: "Ajouter une province : définir son enregistrement, la peindre, placer sa colonie, puis son port ou ignorer cette étape."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campaint.place_the_port_pixel_or_skip

Terms: port

English: "Place the port pixel, or skip it"

French: "Placer le pixel de port ou ignorer"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campaint.writes_layers_at_once_in_the

Terms: port

English: "Writes {n} layers at once, in the colours <b>measured off this map</b>: {layers} · from {sea_tiles} sea tiles. Settlement and port pixels are left alone."

French: "Écrit {n} couches en une fois, avec les couleurs <b>mesurées sur cette carte</b> : {layers} · depuis {sea_tiles} tuiles de mer. Les pixels de colonie et de port restent inchangés."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campaint.written_into_a_settlement_the_music

Terms: ship

English: "Written into {reach}: a settlement, the music\n           type and, where it ships one, the name lookup - each campaign’s own\n           copy of each file."

French: "Écrit dans {reach} : une colonie, le type de musique\n           et, si fourni, le fichier de correspondance des noms, dans la copie\n           propre à chaque campagne."

- ship: Supply/distribute files or content, rather than a naval vessel.

### campbrowse.campaigns_read_in_ms

Terms: ship

English: {"one": "{count} campaign read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom.", "other": "{count} campaigns read in {ms} ms. The ten map layers and the region list are in <code>{base}</code> for every campaign that ships no copy of its own - what changes between those is who starts where, with what, and against whom."}

French: {"one": "{count} campagne lue en {ms} ms. Les dix couches de carte et la liste des régions proviennent de <code>{base}</code> pour toute campagne sans copie propre. Ce qui change entre ces campagnes : qui commence où, avec quoi et contre qui.", "many": "{count} campagnes lues en {ms} ms. Les dix couches de carte et la liste des régions proviennent de <code>{base}</code> pour toute campagne sans copie propre. Ce qui change entre ces campagnes : qui commence où, avec quoi et contre qui.", "other": "{count} campagnes lues en {ms} ms. Les dix couches de carte et la liste des régions proviennent de <code>{base}</code> pour toute campagne sans copie propre. Ce qui change entre ces campagnes : qui commence où, avec quoi et contre qui."}

- ship: Supply/distribute files or content, rather than a naval vessel.

### campbrowse.every_campaign_this_mod_ships_with

Terms: ship

English: "Every campaign this mod ships, with what is in each one, and which of them this screen is reading."

French: "Toutes les campagnes fournies par ce mod, leur contenu et celle que cet écran lit actuellement."

- ship: Supply/distribute files or content, rather than a naval vessel.

### campbrowse.nothing_in_to_read_a_menu

Terms: ship

English: "Nothing in <code>{file}</code> to read a menu title out of - this mod ships neither it nor the compiled archive beside it - so no campaign below shows one. That is the file missing, not the campaigns being unnamed."

French: "Impossible de lire un titre de menu dans <code>{file}</code> : ce mod ne fournit ni ce fichier ni l’archive compilée adjacente. Aucune campagne ci-dessous n’affiche donc de titre. C’est le fichier qui manque, pas le nom des campagnes."

- ship: Supply/distribute files or content, rather than a naval vessel.

### campbrowse.ships_map_layers

Terms: ship

English: {"one": "It ships {count} map layer of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those.", "other": "It ships {count} map layers of its own ({list}{more}), which the engine reads instead of the base's. Open, this screen draws those."}

French: {"one": "Cette campagne fournit {count} couche de carte propre ({list}{more}), lue par le moteur à la place de celle de base. Cet écran l’affiche à l’ouverture.", "many": "Cette campagne fournit {count} couches de carte propres ({list}{more}), lues par le moteur à la place de celles de base. Cet écran les affiche à l’ouverture.", "other": "Cette campagne fournit {count} couches de carte propres ({list}{more}), lues par le moteur à la place de celles de base. Cet écran les affiche à l’ouverture."}

- ship: Supply/distribute files or content, rather than a naval vessel.

### campcreate.new_region_name_paint_settlement_port

Terms: port

English: "<b>＋ New region</b><small>Name → paint → settlement → port</small>"

French: "<b>＋ Nouvelle région</b><small>Nom → peinture → colonie → port</small>"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campcreate.port

Terms: port

English: "Port"

French: "Port"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campcreate.port_marker_add_or_move_on

Terms: port

English: "<b>⚓ Port marker</b><small>Add or move on the selected region</small>"

French: "<b>⚓ Marqueur de port</b><small>Ajouter ou déplacer sur la région sélectionnée</small>"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campcreate.select_a_region_first_then_choose

Terms: port

English: "Select a region first, then choose its settlement or port marker."

French: "Sélectionnez d’abord une région, puis son marqueur de colonie ou de port."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.building_the_composite

Terms: building

English: "building the composite…"

French: "création de l’image composite…"

- building: Literal keyword, code/path, or non-building sense is retained.

### campmap.click_a_province_to_inspect_it

Terms: turn

English: "Click a province to inspect it. Turn on Paint to edit tiles; right or middle drag still pans. Choose a layer and colour on the left."

French: "Cliquez sur une province pour l’examiner. Activez Peindre pour modifier les tuiles ; faites glisser avec le bouton droit ou du milieu pour déplacer la vue. Choisissez couche et couleur à gauche."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### campmap.has_no_campaign_map_this_tool

Terms: ship

English: "has no campaign map this tool can read.<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">A mod only has one if it ships <code>data/world/maps/base</code> - the terrain header, the region list and the ten TGA layers. Without them the game uses its own map, and there is nothing here to draw.</span>"

French: "n’a aucune carte de campagne lisible par cet outil.<br> <span class=\"count\">{why}</span><br><br> <span class=\"count\">Un mod doit fournir <code>data/world/maps/base</code> : en-tête de terrain, liste des régions et dix couches TGA. Sans ces fichiers, le jeu utilise sa propre carte et rien ne peut être affiché ici.</span>"

- ship: Supply/distribute files or content, rather than a naval vessel.

### campmap.port_marker

Terms: port

English: "Port marker"

French: "Marqueur de port"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.port_pixel

Terms: port

English: "port pixel"

French: "pixel de port"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.port_pixels_undecided

Terms: port

English: {"one": "{count} port pixel whose owning region cannot be decided", "other": "{count} port pixels whose owning region cannot be decided"}

French: {"one": "{count} pixel de port dont la région propriétaire est indéterminée", "many": "{count} pixels de port dont la région propriétaire est indéterminée", "other": "{count} pixels de port dont la région propriétaire est indéterminée"}

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.region_id_tiles_settlement_at_game

Terms: port

English: "<span>Region ID</span><b>{x}</b> <span>Tiles</span><b>{count}{x2}</b> <span>Settlement at</span><b>{x3} <span class=\"count\">game</span> · {x4} <span class=\"count\">image</span></b> <span>Port at</span><b>{x5}</b> {x6} <span>Bounding box</span><b>{x7}</b>"

French: "<span>Identifiant de région</span><b>{x}</b> <span>Tuiles</span><b>{count}{x2}</b> <span>Colonie à</span><b>{x3} <span class=\"count\">jeu</span> · {x4} <span class=\"count\">image</span></b> <span>Port à</span><b>{x5}</b> {x6} <span>Rectangle englobant</span><b>{x7}</b>"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.settlement_character_and_port_names_beside

Terms: port

English: "Settlement, character and port names beside their markers (L), placed so that none covers another.\nA name with no room at this zoom is left off and counted; zoom in for it."

French: "Noms des colonies, personnages et ports à côté de leurs marqueurs (L), disposés sans se recouvrir.\nUn nom sans place à ce zoom est omis et compté ; zoomez pour le voir."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.ships_its_own_so_that_layer

Terms: ship

English: "{campaign} ships its own {own}, so that layer is drawn from <code>{folder}</code>. Everything else is <code>world/maps/base</code>, which is what the brush paints."

French: "{campaign} fournit ses propres données ({own}) ; cette couche est donc lue dans <code>{folder}</code>. Le reste provient de <code>world/maps/base</code>, où peint le pinceau."

- ship: Supply/distribute files or content, rather than a naval vessel.

### campmap.tab_osm_title

Terms: turn

English: "OpenStreetMap behind the map: the backdrop, the real coastline and places by name. Off until it is turned on in Settings"

French: "OpenStreetMap derrière la carte : fond de carte, côte réelle et recherche de lieux par nom. Désactivé jusqu’à son activation dans Paramètres"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### campmap.the_campaign_map_as_a_surface

Terms: turn

English: "The campaign map as a surface. Drag to turn, right-drag to pan, scroll to zoom."

French: "La carte de campagne en relief. Faites glisser pour tourner, avec le bouton droit pour déplacer la vue ; faites défiler pour zoomer."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### campmap.the_heights_as_a_surface_with

Terms: turn

English: "The heights as a surface, with this map's own ground on it, orbited (D).\nDrag to turn, right-drag to pan, wheel to zoom.\nMarkers, labels and the tooltip stay on the flat map."

French: "Les altitudes en relief avec le sol propre à cette carte, en vue orbitale (D).\nFaites glisser pour tourner, avec le bouton droit pour déplacer la vue ; molette pour zoomer.\nMarqueurs, noms et info-bulle restent sur la carte plane."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### campmap.tiles_regions_settlements_ports

Terms: port

English: "{width}×{height} tiles · {n} regions · {n2} settlements · {n3} ports"

French: "{width}×{height} tuiles · {n} régions · {n2} colonies · {n3} ports"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmap.views

Terms: view

English: "Views"

French: "Vues"

- view: Saved viewpoint (vue), rather than the Affichage display/menu label.

### campmark.named_character_general_admiral_port_spy

Terms: port

English: "♚ Named character · ⚔ General · ⚓ Admiral / port<br> ◈ Spy · ¤ Merchant · ⚑ Diplomat · ✝ Priest · † Assassin"

French: "♚ Personnage nommé · ⚔ Général · ⚓ Amiral / port<br> ◈ Espion · ¤ Marchand · ⚑ Diplomate · ✝ Prêtre · † Assassin"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmark.port

Terms: port

English: "Port · {x}"

French: "Port · {x}"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmark.ports

Terms: port

English: "Ports"

French: "Ports"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmark.show_settlements_ports_and_campaign_objects

Terms: port

English: "Show settlements, ports and campaign objects. Choose which categories appear below."

French: "Afficher colonies, ports et objets de campagne. Choisissez les catégories visibles ci-dessous."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### campmark.this_mod_ships_its_own_picture

Terms: ship

English: "This mod ships its own picture for {art} of the\n        {n} trade resources here; the rest draw a glyph,\n        because the stock art is inside a .pack archive."

French: "Ce mod fournit ses propres images pour {art} des\n        {n} ressources commerciales ici ; les autres utilisent un symbole,\n        car les images d’origine sont dans une archive .pack."

- ship: Supply/distribute files or content, rather than a naval vessel.

### campnew.map_layers_note

Terms: ship

English: {"one": "It ships {count} map layer of its own, so the copy gets a copy of those too and the two are then two maps to keep in step.", "other": "It ships {count} map layers of its own, so the copy gets a copy of those too and the two are then two maps to keep in step."}

French: {"one": "Cette campagne fournit {count} couche de carte propre ; elle est aussi copiée, ce qui produit deux cartes à maintenir en accord.", "many": "Cette campagne fournit {count} couches de carte propres ; elles sont aussi copiées, ce qui produit deux cartes à maintenir en accord.", "other": "Cette campagne fournit {count} couches de carte propres ; elles sont aussi copiées, ce qui produit deux cartes à maintenir en accord."}

- ship: Supply/distribute files or content, rather than a naval vessel.

### campnew.this_mod_ships_only_the_compiled

Terms: ship

English: "This mod ships only the compiled archive of <code>{descriptions}</code>, which is where the keys would go."

French: "Ce mod fournit uniquement l’archive compilée de <code>{descriptions}</code>, où les clés devraient être ajoutées."

- ship: Supply/distribute files or content, rather than a naval vessel.

### cards.and_more_written_into_the_merc

Terms: mercenary

English: "…and {copy_count} more written into the merc folder"

French: "…et {copy_count} autres écrits dans le dossier merc"

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### cards.confirm_move_folded

Terms: mercenary

English: "Move {delete_count} card file(s) out of “{mod}”, freeing {freed} MB?\n\nThey are copied to:\n{target}\n\n{consolidated} card(s) are folded into the merc folder, which is where the game looks when a faction's own folder has nothing.\n\nEverything touched is backed up first. 🕑 Log → Undo puts it all back."

French: "Déplacer {delete_count} fichier(s) de cartes hors de « {mod} » pour libérer {freed} Mo ?\n\nIls sont copiés vers :\n{target}\n\n{consolidated} carte(s) sont regroupées dans le dossier merc, où le jeu cherche quand le dossier de la faction est vide.\n\nTout élément concerné est d’abord sauvegardé. 🕑 Journal → Annuler rétablit l’ensemble."

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### cards.copying_file_s_out_writing_into

Terms: mercenary

English: "Copying {export_count} file(s) out, writing {copy_count} into the merc folder,\n     then taking {delete_count} out of {mod}. Everything is backed up as it goes."

French: "Copie de {export_count} fichier(s) hors du mod, écriture de {copy_count} dans le dossier merc,\n     puis retrait de {delete_count} de {mod}. Tout est sauvegardé au fur et à mesure."

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### cards.data_ui_units_data_ui_unit

Terms: unit

English: "data/ui/units · data/ui/unit_info"

French: "data/ui/units · data/ui/unit_info"

- unit: Literal unit keyword/path rather than a translated unit label.

### cards.gen_place_reset

Terms: frame

English: "Put the model and the frame back"

French: "Rétablir la position du modèle et le cadrage"

- frame: Camera/image framing or the base faction; not an animation frame.

### cards.gen_turn

Terms: turn

English: "Turn"

French: "Rotation"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### cards.gen_view_hint

Terms: turn

English: "In the HD view: middle drag turns the camera, Shift pans, the wheel zooms; G moves and R turns the model, X, Y or Z holds it to an axis, a click or Enter keeps it, Esc puts it back."

French: "Dans la vue HD : faites glisser avec le bouton du milieu pour tourner la caméra, avec Shift pour déplacer la vue, et utilisez la molette pour zoomer ; G déplace le modèle et R le fait tourner, X, Y ou Z contraint le mouvement à un axe, un clic ou Enter confirme, Esc rétablit la position."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### cards.mod_units_summary

Terms: ship

English: {"one": "{count} unit in the mod · {kinds} · <b>{x}</b> could stop shipping", "other": "{count} units in the mod · {kinds} · <b>{x}</b> could stop shipping"}

French: {"one": "{count} unité dans le mod · {kinds} · <b>{x}</b> pourraient être retirés de la distribution", "many": "{count} unités dans le mod · {kinds} · <b>{x}</b> pourraient être retirés de la distribution", "other": "{count} unités dans le mod · {kinds} · <b>{x}</b> pourraient être retirés de la distribution"}

- ship: Supply/distribute files or content, rather than a naval vessel.

### cards.one_is_the_merc_copy

Terms: mercenary

English: " - one of them is already the merc copy"

French: " ; l’une d’elles est déjà la copie merc"

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### changes.turn_off

Terms: turn

English: "Turn off"

French: "Désactiver"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### changes.turn_off_putting_the_original_records

Terms: turn

English: "Turn \"{off}\" off, putting the original records back?"

French: "Désactiver « {off} » et rétablir les enregistrements d’origine ?"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### changes.turn_on

Terms: turn

English: "Turn \"{on}\" on?"

French: "Activer « {on} » ?"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### climates.append_a_name_the_engine_does

Terms: ship

English: "Append a name the engine does not ship. The strat map draws it; the\nbattle map reads climates by name, which is what the warning is about."

French: "Ajouter un nom absent des noms fournis par le moteur. La carte de campagne l’affiche ; la\ncarte de bataille lit les climats par nom, ce qui explique l’avertissement."

- ship: Supply/distribute files or content, rather than a naval vessel.

### climates.taking_over_one_of_the_twelve

Terms: ship

English: "{problem} Taking over one of the twelve the engine ships needs no such check."

French: "{problem} Réaffecter l’un des douze climats fournis par le moteur ne nécessite pas cette vérification."

- ship: Supply/distribute files or content, rather than a naval vessel.

### codeview.every_string_here_is_stored_as

Terms: character

English: "Every string here is stored as its own length\nfollowed by that many characters. Change a path and the number beside it has to\nchange too. This does that, and you can see it happen."

French: "Chaque chaîne est enregistrée avec sa longueur\nsuivie du nombre correspondant de caractères. Modifier un chemin demande aussi\nde modifier le nombre à côté. Cet outil le fait et vous permet de le voir."

- character: Text character/count or a literal token, rather than a person.

### core.every_model_a_mod_ships_the

Terms: ship

English: "Every model a mod ships: the battle entries, their sprites, the strat map’s, and the cards"

French: "Tous les modèles d’un mod : entrées de bataille, sprites, modèles de la carte de campagne et cartes d’unités"

- ship: Supply/distribute files or content, rather than a naval vessel.

### core.the_tool_did_not_finish_loading

Terms: turn

English: "The tool did not finish loading.<br> <span class=\"count\">The server is running - it answered for the rest of this page - but the browser never received {names}. Reloading fetches it again. If it fails every time, an ad blocker or privacy extension is the usual cause: turn it off for 127.0.0.1.</span>"

French: "Le chargement de l’outil n’est pas terminé.<br> <span class=\"count\">Le serveur fonctionne et a répondu pour le reste de cette page, mais le navigateur n’a jamais reçu {names}. Recharger la page les télécharge à nouveau. Si cela échoue à chaque fois, un bloqueur de publicités ou une extension de confidentialité est généralement en cause : désactivez-le pour 127.0.0.1.</span>"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### core.the_two_pictures_per_unit_deduplicated

Terms: mercenary

English: "The two pictures per unit, deduplicated into the merc folder"

French: "Les deux images par unité, regroupées sans doublons dans le dossier merc"

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### edusort.a_banner_like_gondor_tier_2

Terms: banner, infantry

English: "A banner like ;--- GONDOR TIER 2 INFANTRY --- already says the tier"

French: "Un en-tête tel que ;--- GONDOR TIER 2 INFANTRY --- indique déjà le palier"

- banner: Comment header or literal example/token, rather than a game banner.
- infantry: Literal keyword/example enum is retained.

### edusort.a_comment_in_this_file_starts

Terms: banner

English: "A comment in this file starts with a semicolon, so a banner has to as well."

French: "Un commentaire de ce fichier commence par un point-virgule ; un en-tête doit donc aussi commencer ainsi."

- banner: Comment header or literal example/token, rather than a game banner.

### edusort.a_tier_read_from_a_banner_is

Terms: banner

English: "A tier read from a banner is written onto the unit as <code>;@m2gt tier=2</code>, so the next run does not have to read it again."

French: "Un palier lu dans un en-tête est écrit sur l’unité sous la forme <code>;@m2gt tier=2</code>, pour ne pas devoir le relire au prochain passage."

- banner: Comment header or literal example/token, rather than a game banner.

### edusort.a_unit_with_no_tier_sorts_after

Terms: banner

English: "A unit with no <b>tier</b> sorts after every tiered unit in its group. Tiers read from the file’s own banners are already filled in."

French: "Une unité sans <b>palier</b> est classée après toutes les unités à palier de son groupe. Les paliers lus dans les en-têtes du fichier sont déjà renseignés."

- banner: Comment header or literal example/token, rather than a game banner.

### edusort.line_character

Terms: character

English: "Line character"

French: "Caractère de ligne"

- character: Text character/count or a literal token, rather than a person.

### edusort.read_tiers_from_the_files_own

Terms: banner

English: "Read tiers from the file’s own banners"

French: "Lire les paliers dans les en-têtes du fichier"

- banner: Comment header or literal example/token, rather than a game banner.

### edusort.section_banners

Terms: banner

English: "Section banners"

French: "En-têtes de section"

- banner: Comment header or literal example/token, rather than a game banner.

### edusort.the_shape_is_fixed_so_the_next

Terms: banner

English: "The shape is fixed so the next run can read the section back out of it. A banner your mod wrote by hand is recognised too, and left alone."

French: "Le format est fixe pour que le prochain passage puisse retrouver la section. Un en-tête rédigé manuellement dans votre mod est aussi reconnu et conservé tel quel."

- banner: Comment header or literal example/token, rather than a game banner.

### edusort.write_a_banner_above_each_section

Terms: banner

English: "Write a banner above each section"

French: "Écrire un en-tête au-dessus de chaque section"

- banner: Comment header or literal example/token, rather than a game banner.

### eng.animloose.turns_bones_and_its_skeleton_has

Terms: turn

English: "{x} turns {nq} bones and its skeleton has {bones_n}"

French: "{x} fait tourner {nq} os et son squelette en possède {bones_n}"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### eng.animpack.the_source_ships_no_packs_of

Terms: ship

English: "the source ships no packs of its own, so it plays vanilla's and they are what is ported"

French: "la source ne fournit aucun paquet propre ; elle utilise donc ceux de la version vanilla, qui seront portés"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.animslot.this_mod_ships_no_animation_packs

Terms: ship

English: "this mod ships no animation packs of its own (the game plays vanilla's), so there is no pack of its own to save into"

French: "ce mod ne fournit aucun pack d’animations propre (le jeu utilise ceux de la version vanilla) ; il n’y a donc aucun pack propre dans lequel enregistrer"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.bmdb.still_names_outside_its_soldier_line

Terms: soldier

English: "'{type}' still names {leftovers} outside its soldier line - that entry cannot be merged away"

French: "'{type}' désigne encore {leftovers} hors de sa ligne soldier ; cette entrée ne peut pas être supprimée par fusion"

- soldier: Literal soldier keyword/path is retained.

### eng.buildings.hidden_ceiling_note

Terms: ship

English: "TWCenter's List of Hardcoded Limits puts the ceiling at 63 or 64 and says more crash the game. Divide and Conquer ships 75 and ROCSS 74, and both play, so it is not enforced here."

French: "La liste des limites codées en dur de TWCenter indique un plafond de 63 ou 64, au-delà duquel le jeu plante. Divide and Conquer en fournit 75 et ROCSS 74, tous deux jouables ; cette limite n’est donc pas imposée ici."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.buildings.vanillas_province_wide_lines_roads_farms

Terms: port

English: "Vanilla's province-wide lines (roads, farms, mines, ports) carry it. Nothing restricts it: the mods use it for 66 different things, 75 lines in all."

French: "Les chaînes vanilla à l’échelle de la province (routes, fermes, mines, ports) le possèdent. Rien ne le restreint : les mods l’utilisent pour 66 usages différents, dans 75 chaînes au total."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### eng.campaint.ships_own_so_it_does_not_see

Terms: ship

English: {"one": "{skipped} ships its own {REGIONS_TGA}, so it does not see these pixels and {name} does not exist there", "other": "{skipped} ship their own {REGIONS_TGA}, so they do not see these pixels and {name} does not exist there"}

French: {"one": "{skipped} fournit son propre {REGIONS_TGA} et ne voit donc pas ces pixels ; {name} n’y existe pas", "many": "{skipped} fournissent leur propre {REGIONS_TGA} et ne voient donc pas ces pixels ; {name} n’y existe pas", "other": "{skipped} fournissent leur propre {REGIONS_TGA} et ne voient donc pas ces pixels ; {name} n’y existe pas"}

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.campevents.is_not_one_of_the_eight

Terms: ship

English: "`{kind}` is not one of the eight the engine has; the file the engine ships declares {and_list}"

French: "`{kind}` ne fait pas partie des huit types du moteur ; le fichier fourni avec le moteur déclare {and_list}"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.campfiles.this_mod_ships_only_so_the

Terms: ship

English: "this mod ships only {name}, so the keys go straight into the compiled archive"

French: "ce mod fournit uniquement {name} ; les clés sont donc écrites directement dans l’archive compilée"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.campnew.is_not_on_disk_and_ships

Terms: ship

English: "{REGIONS_REL} is not on disk and {source} ships no map of its own, so there is no region list for this campaign to read"

French: "{REGIONS_REL} est absent du disque et {source} ne fournit aucune carte propre ; aucune liste de régions à lire pour cette campagne"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.campnew.nothing_names_on_the_new_game_menu_archive

Terms: ship

English: "nothing names {name} on the new-game menu, so the engine shows the key {head}TITLE. {descr_rel} is where that lives and the Descriptions panel writes it. This mod ships only the compiled archive, which is where the key would go."

French: "rien ne nomme {name} dans le menu de nouvelle partie ; le moteur affiche donc la clé {head}TITLE. Elle se trouve dans {descr_rel} et le panneau Descriptions permet de l’écrire. Ce mod fournit uniquement l’archive compilée, où la clé serait écrite."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.campnew.ships_map_layer_s_of_its

Terms: ship

English: "{source} ships {layers_n} map layer(s) of its own ({layers}), so the copy gets a copy of them too and the two campaigns are then two maps to keep in step. The map screen draws whichever one the campaign you have open reads."

French: "{source} fournit {layers_n} couche(s) de carte propres ({layers}) ; elles sont copiées aussi, et les deux campagnes deviennent deux cartes à maintenir en parallèle. L’écran de carte affiche celle que lit la campagne ouverte."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.campstrat.character_has_no_type_named_character

Terms: general

English: "character has no type (named character, general, spy, …)"

French: "le personnage n’a pas de type (named character, general, spy, …)"

- general: Generic/general setting or literal General token, rather than a commander.

### eng.campstrat.settlement_header_says_the_engine_knows

Terms: castle

English: "settlement header says {kind}; the engine knows `settlement` and `settlement castle`"

French: "l’en-tête de colonie indique {kind} ; le moteur reconnaît `settlement` et `settlement castle`"

- castle: Literal settlement castle keyword is retained.

### eng.cas.w_text_latin1

Terms: character

English: "{value} has a character a .cas cannot hold (it is written in Latin-1)"

French: "{value} contient un caractère incompatible avec un .cas (écrit en Latin-1)"

- character: Text character/count or a literal token, rather than a person.

### eng.cas.w_text_long

Terms: character

English: "a name of {n:,} characters is longer than the reader takes"

French: "un nom de {n:,} caractères dépasse la capacité du lecteur"

- character: Text character/count or a literal token, rather than a person.

### eng.casanim.turns_bones_and_the_skeleton_has

Terms: turn

English: "{name} turns {nq} bones and the skeleton {x} has {bones_n}: it is another skeleton's animation"

French: "{name} fait tourner {nq} os et le squelette {x} en possède {bones_n} : cette animation appartient à un autre squelette"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### eng.climatenew.a_climate_name_the_battle_map

Terms: ship

English: "{problem} A climate name the battle map does not know is a crash when a battle starts in it, so a new name is the half of this operation that cannot be checked against this mod. Taking over one of the twelve the engine ships - {SPARE} are spare by name - needs no such check."

French: "{problem} Un nom de climat inconnu de la carte de bataille provoque un plantage au début d’une bataille ; le nouveau nom est donc la partie de cette opération impossible à vérifier dans ce mod. Réutiliser l’un des douze climats fournis par le moteur ({SPARE} sont libres d’après leur nom) évite cette vérification."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.climatenew.all_four_mods_measured_for_this

Terms: ship

English: "all four mods measured for this declare exactly the twelve climates the engine ships, in the engine's order, and not one added a thirteenth. Divide and Conquer has a wholly custom map and took over unused1 rather than adding a name."

French: "les quatre mods mesurés déclarent exactement les douze climats fournis par le moteur, dans son ordre, sans en ajouter de treizième. Divide and Conquer possède une carte entièrement personnalisée et a réutilisé unused1 au lieu d’ajouter un nom."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.codeview.length_says_but_text_is

Terms: character

English: "line {line}'s length says {said} but the text beside it is {should} characters - every modeldb string is written `<length> <text>`"

French: "la longueur à la ligne {line} indique {said}, mais le texte à côté contient {should} caractères ; chaque chaîne modeldb s’écrit `<length> <text>`"

- character: Text character/count or a literal token, rather than a person.

### eng.codeview.length_says_but_text_is_and_more

Terms: character

English: "line {line}'s length says {said} but the text beside it is {should} characters (and {more} more like it) - every modeldb string is written `<length> <text>`"

French: "la longueur à la ligne {line} indique {said}, mais le texte à côté contient {should} caractères ({more} autres cas semblables) ; chaque chaîne modeldb s’écrit `<length> <text>`"

- character: Text character/count or a literal token, rather than a person.

### eng.dupes.a_renamed_block_is_a_real

Terms: soldier

English: "a renamed block is a real entry now, but nothing in the mod names it yet. Point a unit's `soldier` line at it, or the next cleanup will offer to remove it as unused"

French: "un bloc renommé est désormais une véritable entrée, mais aucun élément du mod ne le désigne encore. Dirigez vers lui la ligne `soldier` d’une unité, sinon le prochain nettoyage proposera de le supprimer comme inutilisé"

- soldier: Literal soldier keyword/path is retained.

### eng.edusort.unit_s_have_no_tier_yet

Terms: banner

English: "{untiered_n} unit(s) have no tier yet, so they sort after the tiered ones in their group - read the file's own banners in to give them one"

French: "{untiered_n} unité(s) n’ont pas encore de palier et sont donc triées après celles qui en possèdent un dans leur groupe ; lisez les en-têtes du fichier pour leur en attribuer un"

- banner: Comment header or literal example/token, rather than a game banner.

### eng.gamelog.known_5

Terms: turn

English: "When a {b} of {a} turns into a {c} (a city made a castle or back), its buildings change by their chains' convert_to lines, here into a level {a} may not build. Check those levels' requires lines in Buildings, or the convert_to lines."

French: "Lorsqu’un élément {b} de {a} est converti en {c} (ville en château ou inversement), ses bâtiments changent selon les lignes convert_to de leurs chaînes, ici vers un niveau interdit à {a}. Vérifiez les lignes requires de ces niveaux dans Bâtiments ou les lignes convert_to."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### eng.guilds.names_no_building_line_so_nothing

Terms: building

English: "{x} names no `building` line, so nothing in {GUILDS_REL} says which building tree it grants"

French: "{x} ne désigne aucune ligne `building` ; rien dans {GUILDS_REL} n’indique donc l’arbre de bâtiments accordé"

- building: Literal keyword, code/path, or non-building sense is retained.

### eng.heroabilities.not_in_ui_battle_sd_so

Terms: battle

English: "{owner}: {gone} not in ui/battle.sd, so the button has no picture{why}"

French: "{owner} : {gone} est absent de ui/battle.sd ; le bouton n’a donc aucune image{why}"

- battle: Literal Battle console argument or battle filename is retained.

### eng.mapfe.the_frame_at_x_g_y

Terms: frame

English: "the frame at ({x:g},{y:g}) {w:g}x{h:g} does not touch the {gw}x{gh} grid"

French: "le cadre en ({x:g},{y:g}) de {w:g}x{h:g} ne touche pas la grille {gw}x{gh}"

- frame: Camera/image framing or the base faction; not an animation frame.

### eng.mapfe.the_frame_is_w_g_x

Terms: frame

English: "the frame is {w:g}x{h:g} tiles"

French: "le cadre mesure {w:g}x{h:g} tuiles"

- frame: Camera/image framing or the base faction; not an animation frame.

### eng.mapfe.the_frame_is_w_g_x_2

Terms: frame

English: "the frame is {w:g}x{h:g} tiles, and fewer than {MIN_TILES} a side is not a picture of anything"

French: "le cadre mesure {w:g}x{h:g} tuiles ; avec moins de {MIN_TILES} par côté, aucune image exploitable n’est possible"

- frame: Camera/image framing or the base faction; not an animation frame.

### eng.modeldb.characters_left_over_after_the_entry

Terms: character

English: "{x} characters left over after the entry"

French: "{x} caractères restants après l’entrée"

- character: Text character/count or a literal token, rather than a person.

### eng.namekeys.this_mod_ships_only_strings_bin

Terms: ship

English: "this mod ships only {name}.strings.bin, so the keys go straight into the compiled archive"

French: "ce mod fournit uniquement {name}.strings.bin ; les clés sont donc écrites directement dans l’archive compilée"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.osmmap.openstreetmap_is_off_turn_it_on

Terms: turn

English: "OpenStreetMap is off. Turn it on under Settings, Real-world map, first. Nothing was sent."

French: "OpenStreetMap est désactivé. Activez-le d’abord dans Paramètres, Carte du monde réel. Rien n’a été envoyé."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### eng.regiondel.already_has_a_port_of_its

Terms: heir

English: "{heir} already has a port of its own, so keeping this one leaves two port pixels in one province and the engine uses one of them. Check reports that as a second port."

French: "{heir} possède déjà son propre port ; conserver celui-ci laisse deux pixels de port dans une province, et le moteur en utilise un. Vérification le signale comme second port."

- heir: Province receiving deleted land/records, rather than a royal heir.

### eng.regiondel.s_go_with_the_section_because

Terms: heir

English: "{rel}: {x} {kind}(s) go with the section, because there was no heir to file them under"

French: "{rel} : {x} élément(s) de type {kind} sont supprimés avec la section, sans province bénéficiaire à laquelle les attribuer"

- heir: Province receiving deleted land/records, rather than a royal heir.

### eng.regiondel.the_region_section_and_its_fort

Terms: heir

English: "{rel}: the `region {name}` section and its {kept_n} fort or watchtower line(s) go with it, because there is no heir to move them to"

French: "{rel} : la section de région `region {name}` et ses {kept_n} ligne(s) de fort ou de tour de guet sont supprimées ensemble, sans province bénéficiaire où les déplacer"

- heir: Province receiving deleted land/records, rather than a royal heir.

### eng.scriptwords.act_help_console_3820

Terms: battle

English: "any command of the game's console (Pick... shows them all), like add_money egypt 500 or kill_character \"{general}\" Battle - {town} {faction} {owner} {general} {turn} {people} are filled in"

French: "toute commande de la console du jeu (« Choisir… » les affiche toutes), par exemple add_money egypt 500 ou kill_character \"{general}\" Battle ; {town} {faction} {owner} {general} {turn} {people} sont remplacés"

- battle: Literal Battle console argument or battle filename is retained.

### eng.scriptwords.cond_help_game_d1e6

Terms: turn

English: "any condition of the engines' own list (Pick... shows them all), checked against what just happened - like I_TurnNumber > 5, FactionType england, SettlementName London, Trait GoodCommander > 0; 'not' in front turns it round; {town} {faction} {owner} {general} {turn} {people} are filled in"

French: "toute condition de la liste des moteurs (« Choisir… » les affiche toutes), vérifiée par rapport à l’événement qui vient de se produire ; par exemple I_TurnNumber > 5, FactionType england, SettlementName London, Trait GoodCommander > 0. Le préfixe « not » l’inverse ; {town} {faction} {owner} {general} {turn} {people} sont remplacés"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### eng.server.the_frame_is_not_four_numbers

Terms: frame

English: "the frame is not four numbers"

French: "le cadre n’est pas composé de quatre nombres"

- frame: Camera/image framing or the base faction; not an animation frame.

### eng.soundbanks.line_end_with_no_open_event

Terms: event

English: "line {x}: 'end' with no open 'event'"

French: "ligne {x} : 'end' sans 'event' ouvert"

- event: Literal event keyword or events file/path is retained.

### eng.stratcamp.is_not_a_word_the_engine

Terms: ship

English: "{name} is not a word the engine reads - the one it reads is marian_reforms_disabled - so this line does nothing. Third Age Reforged ships it too"

French: "{name} n’est pas un mot lu par le moteur, qui attend marian_reforms_disabled ; cette ligne ne fait donc rien. Third Age Reforged la fournit aussi"

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.stratedit.a_settlement_block_opens_with_the

Terms: castle

English: "a settlement block opens with the word `settlement`, on its own or followed by `castle`. This one opens with {head}"

French: "un bloc de colonie commence par `settlement`, seul ou suivi de `castle`. Celui-ci commence par {head}"

- castle: Literal settlement castle keyword is retained.

### eng.stratedit.stays_on_the_map_with_no

Terms: ship

English: "{region} stays on the map with no settlement in it. Vanilla ships one like that (Durazzo); Health lists such a province as a note."

French: "{region} reste sur la carte sans colonie. La version vanilla en fournit une ainsi (Durazzo) ; Diagnostic signale une telle province comme remarque."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.stratedit.the_header_says_the_engine_reads

Terms: castle

English: "The header says {kind}. The engine reads `settlement` and `settlement castle` and nothing else."

French: "L’en-tête indique {kind}. Le moteur lit uniquement les formes de colonie `settlement` et `settlement castle`."

- castle: Literal settlement castle keyword is retained.

### eng.stratedit.two_levels_of_stand_in_this

Terms: ship

English: "Two levels of {x} stand in this settlement at once. Third Age Reforged ships four settlements like it, so it is not fatal, but only one of them is the building."

French: "Deux niveaux de {x} existent simultanément dans cette colonie. Third Age Reforged fournit quatre colonies ainsi ; ce n’est donc pas fatal, mais un seul niveau constitue le bâtiment."

- ship: Supply/distribute files or content, rather than a naval vessel.

### eng.stringsbin.a_single_string_cannot_exceed_65535

Terms: character

English: "a single string cannot exceed 65535 characters (this one is {units})"

French: "une chaîne ne peut pas dépasser 65535 caractères (celle-ci en contient {units})"

- character: Text character/count or a literal token, rather than a person.

### eng.stringsbin.a_string_says_it_is_characters

Terms: character

English: "a string says it is {units} characters long but only {x} are left in the file"

French: "une chaîne annonce {units} caractères, mais seuls {x} restent dans le fichier"

- character: Text character/count or a literal token, rather than a person.

### eng.transfer.mercenary_to_actually_recruit_it_add

Terms: campaign

English: "mercenary: to actually recruit it, add a pool entry in data/world/maps/campaign/imperial_campaign/descr_mercenaries.txt - this tool does not write that file."

French: "mercenaire : pour permettre son recrutement, ajoutez une entrée de réserve dans data/world/maps/campaign/imperial_campaign/descr_mercenaries.txt ; cet outil n’écrit pas ce fichier."

- campaign: Literal campaign directory/path rather than translated prose.

### eng.transfer.projectile_model_cas_files_were_copied

Terms: missile

English: "projectile model (.cas) files were copied, but their textures under data/models_missile/textures/ are not chased - verify the missile model renders and copy its texture if it's missing in the destination."

French: "les modèles de projectile (.cas) ont été copiés, mais leurs textures sous data/models_missile/textures/ ne sont pas recherchées ; vérifiez l’affichage du modèle de projectile et copiez sa texture si elle manque dans la destination."

- missile: Literal enum/token or projectile sense, rather than the weapon label.

### eng.winconds.could_not_be_read_the_stock

Terms: ship

English: "{rel} could not be read ({exc}). The stock game ships it on disk and so do both installed mods, so a campaign without one is a campaign nobody can win"

French: "lecture de {rel} impossible ({exc}). Le jeu de base et les deux mods installés le fournissent sur disque ; une campagne sans ce fichier ne peut donc être gagnée par personne"

- ship: Supply/distribute files or content, rather than a naval vessel.

### facaudit.world_maps_campaign

Terms: campaign

English: "world/maps/campaign/{camp}/{rel}"

French: "world/maps/campaign/{camp}/{rel}"

- campaign: Literal campaign directory/path rather than translated prose.

### factions.bring_art

Terms: frame

English: "Bring its art - symbols, banners, captain cards and unit card folders, in place of the frame's"

French: "Apporter ses images : symboles, bannières, cartes de capitaines et dossiers de cartes d’unités, à la place de ceux de la faction de base"

- frame: Camera/image framing or the base faction; not an animation frame.

### factions.bring_confirm

Terms: frame

English: "Bring {faction} from {mod} as {name}, made on {frame}?\n\n{files} file(s) are written in one job, then {units} unit(s) come by Unit Transfer, each its own entry in the Log.\n\n{notes}"

French: "Apporter {faction} depuis {mod} sous le nom {name}, à partir de {frame} ?\n\n{files} fichier(s) sont écrits en une opération, puis {units} unité(s) sont apportées par Transférer des unités, chacune avec sa propre entrée dans le journal.\n\n{notes}"

- frame: Camera/image framing or the base faction; not an animation frame.

### factions.bring_frame_units

Terms: frame

English: "Keep the frame faction's units as well"

French: "Conserver aussi les unités de la faction de base"

- frame: Camera/image framing or the base faction; not an animation frame.

### guided.a_unit_can_only_use_one_of

Terms: ship

English: "A unit can only use one of <code>ship</code>, <code>engine</code>, <code>mounted_engine</code> and <code>animal</code>. This one has <b>{extras}</b>."

French: "Une unité ne peut utiliser qu’un seul élément parmi <code>ship</code>, <code>engine</code>, <code>mounted_engine</code> et <code>animal</code>. Celle-ci possède <b>{extras}</b>."

- ship: Supply/distribute files or content, rather than a naval vessel.

### guided.close

Terms: close

English: "Close ↔"

French: "Serré ↔"

- close: Close order or closing a data/XML structure, rather than a Close action.

### guided.close_2

Terms: close

English: "Close ↕"

French: "Serré ↕"

- close: Close order or closing a data/XML structure, rather than a Close action.

### guided.florins_the_smith_charges_to_upgrade

Terms: charge

English: "Florins the smith charges to upgrade its weapons."

French: "Florins demandés par le forgeron pour améliorer ses armes."

- charge: Price charged by a smith, rather than a cavalry charge.

### guided.florins_the_smith_charges_to_upgrade_2

Terms: charge

English: "Florins the smith charges to upgrade its armour."

French: "Florins demandés par le forgeron pour améliorer son armure."

- charge: Price charged by a smith, rather than a cavalry charge.

### guided.heavy_light_general

Terms: general

English: "Heavy | Light | General"

French: "Heavy | Light | General"

- general: Generic/general setting or literal General token, rather than a commander.

### guided.infantry_cavalry_siege_ship_handler

Terms: infantry, cavalry, siege, ship

English: "infantry | cavalry | siege | ship | handler"

French: "infantry | cavalry | siege | ship | handler"

- infantry: Literal keyword/example enum is retained.
- cavalry: Literal category enum is retained.
- siege: Literal category enum is retained.
- ship: Supply/distribute files or content, rather than a naval vessel.

### guided.light_heavy_missile_spearmen

Terms: missile

English: "light | heavy | missile | spearmen"

French: "light | heavy | missile | spearmen"

- missile: Literal enum/token or projectile sense, rather than the weapon label.

### guided.missile_infantry_cavalry_and_siege

Terms: missile

English: "<code>missile</code>: infantry, cavalry and siege."

French: "<code>missile</code> : infanterie, cavalerie et siège."

- missile: Literal enum/token or projectile sense, rather than the weapon label.

### guided.modifier_in_forest_positive_for_woodsmen

Terms: close

English: "Modifier in forest. Positive for woodsmen, negative for close formations."

French: "Modificateur en forêt. Positif pour les troupes forestières, négatif pour les formations serrées."

- close: Close order or closing a data/XML structure, rather than a Close action.

### guided.optional_the_effect_played_when_the_weapon

Terms: turn

English: "Optional. The effect played when the weapon <i>fires</i>: <code>musket_shot_set</code> for gunpowder units, and essentially nothing else. Setting it is what turns this line from 11 values into 12; clearing it turns it back."

French: "Facultatif. Effet joué lorsque l’arme <i>tire</i> : <code>musket_shot_set</code> pour les unités à poudre, et pratiquement rien d’autre. Le définir fait passer cette ligne de 11 à 12 valeurs ; l’effacer rétablit la forme courte."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### guided.side_to_side_spacing_between_men

Terms: close

English: "Side-to-side spacing between men in metres, close order."

French: "Espacement latéral entre soldats en mètres, en ordre serré."

- close: Close order or closing a data/XML structure, rather than a Close action.

### guided.side_to_side_spacing_in_loose

Terms: close

English: "Side-to-side spacing in loose order. It is always wider than close order."

French: "Espacement latéral en ordre dispersé. Toujours plus large qu’en ordre serré."

- close: Close order or closing a data/XML structure, rather than a Close action.

### guided.side_to_side_then_front_to

Terms: close

English: "Side-to-side then front-to-back, in close order then in loose order."

French: "Espacement latéral puis avant-arrière, en ordre serré puis dispersé."

- close: Close order or closing a data/XML structure, rather than a Close action.

### guided.the_line_goes_directly_after_soldier

Terms: soldier

English: "The line goes directly after <code>soldier</code>."

French: "La ligne se place directement après <code>soldier</code>."

- soldier: Literal soldier keyword/path is retained.

### guided.these_entries_do_not_decide_how_the

Terms: soldier

English: "These entries do <b>not</b> decide how the unit animates. The <code>soldier</code> line does."

French: "Ces entrées ne déterminent <b>pas</b> les animations de l’unité. C’est la ligne <code>soldier</code> qui les détermine."

- soldier: Literal soldier keyword/path is retained.

### guided.up_to_three_officer_lines_directly

Terms: soldier

English: "Up to three <code>officer</code> lines, directly after <code>soldier</code>."

French: "Jusqu’à trois lignes <code>officer</code>, directement après <code>soldier</code>."

- soldier: Literal soldier keyword/path is retained.

### guided.vanilla_ships_it_commented_out

Terms: ship

English: "Vanilla ships it commented out."

French: "La version vanilla la fournit en commentaire."

- ship: Supply/distribute files or content, rather than a naval vessel.

### guided.vanilla_ships_it_commented_out_on

Terms: ship

English: "Vanilla ships it commented out on every unit."

French: "La version vanilla la fournit en commentaire sur toutes les unités."

- ship: Supply/distribute files or content, rather than a naval vessel.

### home.mounted_pack

Terms: mount

English: "📦 mounted pack"

French: "📦 paquet connecté"

- mount: Literal keyword/path rather than a translated mount label.

### map3d.building_the_mesh

Terms: building

English: "Building the mesh…"

French: "Création du maillage…"

- building: Literal keyword, code/path, or non-building sense is retained.

### map3d.frame_the_whole_map_again

Terms: frame

English: "Frame the whole map again"

French: "Recadrer sur toute la carte"

- frame: Camera/image framing or the base faction; not an animation frame.

### mapcheck.clear_the_baseline_confirm

Terms: block

English: "Clear the baseline?\n\nEvery finding already in this mod goes back to being one the toolkit will block a save on."

French: "Effacer l’état de référence ?\n\nTous les problèmes déjà présents dans ce mod bloqueront à nouveau l’enregistrement dans l’outil."

- block: Verb prevent/block, rather than a record block.

### mapcheck.no_baseline_every_fatal_finding_here

Terms: block

English: "No baseline. Every fatal finding here blocks a save, including the ones\n         that came with the mod."

French: "Aucun état de référence. Tout problème fatal bloque l’enregistrement, y compris ceux\n         déjà présents dans le mod."

- block: Verb prevent/block, rather than a record block.

### mapcheck.of_these_were_already_in_when

Terms: block

English: "of these were already in {mod} when the baseline was stamped on {baseline_at}. They are shown, and they do not block a save."

French: "étaient déjà présents dans {mod} lors de la création de l’état de référence le {baseline_at}. Ils sont affichés sans bloquer l’enregistrement."

- block: Verb prevent/block, rather than a record block.

### mapfe.before_this_panel_the_picture_was

Terms: frame

English: "Before this panel the picture ({was}) was squeezed into {grid} and scaled again to get onto the canvas. It is now drawn at its own size on the frame below, so nothing resamples it."

French: "Avant ce panneau, l’image ({was}) était comprimée dans {grid}, puis redimensionnée pour le canevas. Elle est maintenant affichée à sa taille propre dans le cadre ci-dessous, sans rééchantillonnage."

- frame: Camera/image framing or the base faction; not an animation frame.

### mapfe.proposed_frame

Terms: frame

English: "↺ Proposed frame"

French: "↺ Cadre proposé"

- frame: Camera/image framing or the base faction; not an animation frame.

### mapfe.put_the_frame_back_to_the

Terms: frame

English: "put the frame back to the proposed one"

French: "rétablir le cadre proposé"

- frame: Camera/image framing or the base faction; not an animation frame.

### mapfe.the_frame

Terms: frame

English: "the frame"

French: "le cadre"

- frame: Camera/image framing or the base faction; not an animation frame.

### mapfe.the_frame_2

Terms: frame

English: "<span>The frame</span> <span class=\"count\" id=\"cfeFigs\">{cfeFigureText}</span>"

French: "<span>Le cadre</span> <span class=\"count\" id=\"cfeFigs\">{cfeFigureText}</span>"

- frame: Camera/image framing or the base faction; not an animation frame.

### mapfe.the_frame_is_which_rectangle_of

Terms: frame

English: "The frame is which rectangle of the map the picture is a picture of. It starts as the smallest one the picture's shape can be and still hold the whole map; drag it or its corners to move it, and the shape is held because that is what lets one zoom draw the picture 1:1. Nothing can work it out from the picture - one installed mod's has a painted border round the map and two are not maps at all."

French: "Le cadre définit le rectangle de carte représenté par l’image. Il commence comme le plus petit rectangle de même proportion pouvant contenir toute la carte. Faites glisser le cadre ou ses coins pour le déplacer ; les proportions sont conservées afin de permettre un affichage 1:1. Impossible de le déduire de l’image : un mod installé possède une bordure peinte autour de la carte et deux images ne sont même pas des cartes."

- frame: Camera/image framing or the base faction; not an animation frame.

### mapfe.the_front_end_layer_is_not

Terms: frame

English: "The front-end layer is not ticked, so the picture is not on the canvas - the frame is. Key <b>1</b> ticks it."

French: "La couche du menu n’est pas cochée ; seul son cadre apparaît sur le canevas, pas l’image. La touche <b>1</b> l’active."

- frame: Camera/image framing or the base faction; not an animation frame.

### maplabels.character

Terms: character

English: "character:{line}"

French: "character:{line}"

- character: Text character/count or a literal token, rather than a person.

### maplabels.port

Terms: port

English: "port:{region}"

French: "port:{region}"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### maplabels.port_2

Terms: port

English: "Port · {x}"

French: "Port · {x}"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### mapquery.building_that_map

Terms: building

English: "building that map"

French: "création de cette carte"

- building: Literal keyword, code/path, or non-building sense is retained.

### mapsize.turn_the_real_world_switch_on

Terms: turn

English: "Turn the Real world switch on in Settings first."

French: "Activez d’abord Monde réel dans Paramètres."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### mapsize.turned

Terms: turn

English: ", turned {rotation}°"

French: ", rotation de {rotation}°"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### mapviews.views

Terms: view

English: "📐 Views{open}"

French: "📐 Vues{open}"

- view: Saved viewpoint (vue), rather than the Affichage display/menu label.

### minorfiles.port_ladder_line_s_in_the

Terms: port

English: "Port ladder <span class=\"count\">{ports_n} line(s), in the file's own order: each port level is a <code>port_land</code> and a <code>port_sea</code> model. Adding or removing a level is a pair of lines placed in that order, so it is done in the code view; what each line points at is here.</span>"

French: "Progression des ports <span class=\"count\">{ports_n} ligne(s), dans l’ordre du fichier : chaque niveau de port comprend un modèle <code>port_land</code> et un <code>port_sea</code>. Ajouter ou retirer un niveau demande une paire de lignes dans cet ordre ; faites-le dans la vue du code. Les cibles de chaque ligne se règlent ici.</span>"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### minorfiles.this_culture_has_no_port_lines

Terms: port

English: "This culture has no port lines."

French: "Cette culture n’a aucune ligne de port."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### minorfiles.where_it_starts_every_regions_religions

Terms: ship

English: "Where it starts <span class=\"count\">Every region's <code>religions { … }</code> line gets <code>{name} 0</code>, in every descr_regions.txt this mod ships. A share given here comes out of the region's other religions in proportion, so each line still adds up to 100.</span>"

French: "Répartition initiale <span class=\"count\">La ligne <code>religions { … }</code> de chaque région reçoit <code>{name} 0</code> dans chaque descr_regions.txt fourni par ce mod. Une part attribuée ici est prélevée proportionnellement sur les autres religions de la région pour maintenir un total de 100.</span>"

- ship: Supply/distribute files or content, rather than a naval vessel.

### osmmap.in_the_boxs_corners_off_the

Terms: turn

English: "; {off_map} in the box’s corners, off the turned map"

French: " ; {off_map} dans les coins de la zone, hors de la carte tournée"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### osmmap.make_land_tiles_inside_openstreetmaps_water_confirm

Terms: port

English: "Make {to_sea} land tiles inside OpenStreetMap’s water sea?\n\nIt is one stroke of the paint tool, like the coastline: regions, heights and ground types together, in this map’s own sea colours, islands kept dry, settlements and ports left alone. The Paint tab’s Undo takes it back, and nothing is written until you save there."

French: "Transformer en mer les {to_sea} tuiles terrestres situées dans les eaux d’OpenStreetMap ?\n\nUn seul trait de peinture, comme pour la côte : régions, altitudes et types de sol ensemble, avec les couleurs de mer de cette carte. Les îles restent sèches, colonies et ports inchangés. Annuler dans l’onglet Peindre rétablit l’état précédent ; rien n’est écrit avant d’y enregistrer."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### osmmap.make_land_tiles_on_the_water_coastline

Terms: port

English: "Make {to_sea} land tiles on the water side of the coastline sea?\n\nIt is one stroke of the paint tool: regions, heights and ground types together, in this map’s own sea colours, settlements and ports left alone. The Paint tab’s Undo takes it back, and nothing is written until you save there."

French: "Transformer en mer les {to_sea} tuiles terrestres du côté eau de la côte ?\n\nUn seul trait de peinture : régions, altitudes et types de sol ensemble, avec les couleurs de mer de cette carte. Colonies et ports restent inchangés. Annuler dans l’onglet Peindre rétablit l’état précédent ; rien n’est écrit avant d’y enregistrer."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### osmmap.mylaes_layout_the_maps_layers_as

Terms: port

English: "Mylae’s layout: the map’s layers as they are on disk, bbox_coords.txt, and reference/ with map_regions.txt (each province’s colour, city and port), the historic sites already fetched for this box, and the picture. Only the picture uses the internet."

French: "Organisation de Mylae : couches de carte telles que sur disque, bbox_coords.txt et reference/ avec map_regions.txt (couleur, ville et port de chaque province), sites historiques déjà récupérés pour cette zone et image. Seule l’image utilise internet."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### osmmap.off_this_is_the_one_part

Terms: turn

English: "Off. This is the one part of the toolkit that uses the internet, so it waits to be turned on."

French: "Désactivé. Seule cette partie de l’outil utilise internet ; elle attend donc son activation."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### osmmap.open_settings_to_turn_it_on

Terms: turn

English: "⚙ Open Settings to turn it on"

French: "⚙ Ouvrir Paramètres pour activer"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### osmmap.the_style_above_cut_to_the

Terms: turn, frame

English: "The style above, cut to the box and turned with it, in the map’s own frame: a reference to paint from in another program."

French: "Le style ci-dessus, découpé et tourné selon la zone, dans le cadre propre à la carte : référence à utiliser dans un autre logiciel de peinture."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.
- frame: Camera/image framing or the base faction; not an animation frame.

### osmmap.where_the_maps_edges_are_in

Terms: turn

English: "Where the map’s edges are in the real world, and how far the map is turned (degrees, clockwise). Change a number and the backdrop moves at once; Keep saves it in the toolkit, not in the mod."

French: "Position réelle des bords de la carte et rotation en degrés, sens horaire. Changer un nombre déplace immédiatement le fond de carte ; Conserver enregistre dans l’outil, pas dans le mod."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### osmworld.drag_to_pan_wheel_to_zoom

Terms: turn

English: "Drag to pan, wheel to zoom. Drag the box's corners to resize it, its middle to move it, the violet handle to turn it."

French: "Faites glisser pour déplacer la vue, molette pour zoomer. Faites glisser les coins de la zone pour la redimensionner, son centre pour la déplacer et sa poignée violette pour la tourner."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### packs.battle_model_entr_travel_with_them

Terms: mount

English: {"one": "{count} battle-model entry travels with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer.", "other": "{count} battle-model entries travel with them. Importing mounts the pack as a source mod and drops you in the normal transfer screen, so name clashes, the base unit, ownership and every other option are asked there. Nothing is written until you press Transfer."}

French: {"one": "{count} entrée de modèle de bataille les accompagne. L’importation monte le pack comme mod source et ouvre l’écran de transfert habituel : conflits de noms, unité de base, appartenance et toutes les autres options s’y règlent. Rien n’est écrit avant de cliquer sur Transférer.", "many": "{count} entrées de modèles de bataille les accompagnent. L’importation monte le pack comme mod source et ouvre l’écran de transfert habituel : conflits de noms, unité de base, appartenance et toutes les autres options s’y règlent. Rien n’est écrit avant de cliquer sur Transférer.", "other": "{count} entrées de modèles de bataille les accompagnent. L’importation monte le pack comme mod source et ouvre l’écran de transfert habituel : conflits de noms, unité de base, appartenance et toutes les autres options s’y règlent. Rien n’est écrit avant de cliquer sur Transférer."}

- mount: Literal keyword/path rather than a translated mount label.

### rebels.of_provinces_name_a_rebel_faction

Terms: turn

English: "{silent_regions} of {regions} provinces name a rebel faction with <code>chance 0</code>, so they spawn no rebels. That is a real setting rather than a fault - it is how a mod turns province rebels off - but it is what those assignments do."

French: "{silent_regions} provinces sur {regions} référencent une faction rebelle avec <code>chance 0</code> ; aucun rebelle n’y apparaît donc. Ce réglage est valide : il permet de désactiver les rebelles de province dans un mod. C’est l’effet de ces attributions."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### regiondel.already_has_a_port_and_only

Terms: port

English: "{heir} already has a port, and only one of two in a province is\n         ever used - so removing this one is the answer that leaves a map the\n         validator does not report."

French: "{heir} possède déjà un port, et un seul des deux ports d’une province est\n         utilisé. Retirer celui-ci permet donc de conserver une carte sans problème\n         signalé par le validateur."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### regiondel.has_no_port_of_its_own

Terms: port

English: "{heir} has no port of its own, so keeping this one gives it a\n         harbour on the coast it is about to inherit."

French: "{heir} ne possède pas de port ; conserver celui-ci lui donne donc\n         un port sur la côte qu’il va recevoir."

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### regiondel.its_port

Terms: port

English: "<span class=\"cmtnm\">Its port</span> <span class=\"cmseg\">"

French: "<span class=\"cmtnm\">Son port</span> <span class=\"cmseg\">"

- port: Harbour or literal file/API/path token; not the transfer verb porter.

### regiondel.the_heir

Terms: heir

English: "the heir"

French: "le bénéficiaire"

- heir: Province receiving deleted land/records, rather than a royal heir.

### settings.and_more_characters_in_the_diagnostic

Terms: character

English: "…and {summary_cut} more characters, in the diagnostic log."

French: "…et {summary_cut} caractères supplémentaires dans le journal de diagnostic."

- character: Text character/count or a literal token, rather than a person.

### settings.start_the_soldier_row_on_base

Terms: building

English: "Start the <b>Soldier</b> row on <b>Base</b>, so the destination unit's model and projectile are used instead of the transferred unit's. Applies to both modes that have a base unit: building a new unit on one, and replacing one (there the base <i>is</i> the unit being replaced, so its own model and animations stay). Still switchable per unit."

French: "Régler la ligne <b>Soldat</b> sur <b>Base</b> au départ, pour utiliser le modèle et le projectile de l’unité de destination plutôt que ceux de l’unité transférée. Cela s’applique aux deux modes utilisant une unité de base : créer une unité à partir d’une autre et remplacer une unité (dans ce cas, la base <i>est</i> l’unité remplacée, qui conserve donc son modèle et ses animations). Ce choix reste modifiable pour chaque unité."

- building: Literal keyword, code/path, or non-building sense is retained.

### settlemech.level

Terms: level

English: "level/{name}/{x}"

French: "level/{name}/{x}"

- level: Literal level key/path or numeric field identifier is retained.

### soundbanks.event_line_sample_count

Terms: event

English: {"one": "<b>event{x}</b>{of} <span class=\"count\">line {line} · {count} sample</span>", "other": "<b>event{x}</b>{of} <span class=\"count\">line {line} · {count} samples</span>"}

French: {"one": "<b>event{x}</b>{of} <span class=\"count\">ligne {line} · {count} échantillon</span>", "many": "<b>event{x}</b>{of} <span class=\"count\">ligne {line} · {count} échantillons</span>", "other": "<b>event{x}</b>{of} <span class=\"count\">ligne {line} · {count} échantillons</span>"}

- event: Literal event keyword or events file/path is retained.

### soundbanks.has_no_data_the_game_uses

Terms: ship

English: "{src} has no <code>data/{rel}</code>.<br><span class=\"count\">The game uses its own {label} when a mod does not ship them.</span>"

French: "{src} ne possède pas de <code>data/{rel}</code>.<br><span class=\"count\">Le jeu utilise ses propres données ({label}) quand le mod n’en fournit pas.</span>"

- ship: Supply/distribute files or content, rather than a naval vessel.

### sprites.flag_turned_off

Terms: turn

English: "Flag turned off."

French: "Indicateur désactivé."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### sprites.the_bypass_flag_makes_the_next_normal

Terms: turn

English: "The bypass flag makes the next normal launch re-render instead of starting, which reads as a crash. Turn it back off when you are done."

French: "L’indicateur de contournement fait recalculer les rendus au prochain lancement normal au lieu de démarrer le jeu, ce qui ressemble à un plantage. Désactivez-le une fois terminé."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### sprites.this_mod_ships_m2tweop_so_generation

Terms: ship

English: "This mod ships M2TWEOP, so generation goes through its console."

French: "Ce mod inclut M2TWEOP ; la génération passe donc par sa console."

- ship: Supply/distribute files or content, rather than a naval vessel.

### sprites.turn_the_flag_back_off

Terms: turn

English: "Turn the flag back off"

French: "Désactiver l’indicateur"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### stratchar.no_export_descr_character_traits_txt

Terms: character, trait

English: " · no export_descr_character_traits.txt on disk"

French: " · aucun export_descr_character_traits.txt sur le disque"

- character: Text character/count or a literal token, rather than a person.
- trait: Literal Trait syntax/example is retained.

### stratchar.what_should_the_player_read_for_prompt

Terms: turn

English: "What should the player read for \"{part}\"?\n\nThis is the value of its key in text/names.txt. Leave it as it is to use the token with its underscores turned into spaces."

French: "Quel texte le joueur doit-il lire pour « {part} » ?\n\nC’est la valeur de sa clé dans text/names.txt. Conservez-la telle quelle pour utiliser le nom avec ses traits de soulignement remplacés par des espaces."

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### stratmap.draw_a_campaign_map_model_beside

Terms: ship

English: "Draw a campaign-map model beside the list, without leaving it. Every entry\nthat ships a .CAS gets its own 🧊 button once this is open, and the panel also browses\nevery model file under data/models_strat - including the settlements, which no entry names."

French: "Afficher un modèle de carte de campagne à côté de la liste, sans la quitter. Chaque entrée\nfournissant un .CAS reçoit son bouton 🧊 à l’ouverture. Le panneau permet aussi de parcourir\ntous les fichiers de modèles sous data/models_strat, colonies comprises, bien qu’aucune entrée ne les référence."

- ship: Supply/distribute files or content, rather than a naval vessel.

### stratmap.file_named_by_no_model_but

Terms: turn

English: {"one": "{count} file is named by no model, but its bare filename turns up in a <code>descr_*.txt</code> or a script - so it is not offered above either.", "other": "{count} files are named by no model, but their bare filename turns up in a <code>descr_*.txt</code> or a script - so they are not offered above either."}

French: {"one": "{count} fichier n’est référencé par aucun modèle, mais son nom apparaît dans un <code>descr_*.txt</code> ou un script ; son retrait n’est donc pas non plus proposé.", "many": "{count} fichiers ne sont référencés par aucun modèle, mais leurs noms apparaissent dans un <code>descr_*.txt</code> ou un script ; leur retrait n’est donc pas non plus proposé.", "other": "{count} fichiers ne sont référencés par aucun modèle, mais leurs noms apparaissent dans un <code>descr_*.txt</code> ou un script ; leur retrait n’est donc pas non plus proposé."}

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### stratmap.not_shipped

Terms: ship

English: "· <span class=\"w-warn\">{missing_n} not shipped</span>"

French: "· <span class=\"w-warn\">{missing_n} non fournis</span>"

- ship: Supply/distribute files or content, rather than a naval vessel.

### stratview.this_mod_ships_no_data_models

Terms: ship

English: "this mod ships no <code>data/models_strat</code>, so it uses the game's own strat models"

French: "ce mod ne fournit pas de <code>data/models_strat</code> et utilise donc les modèles de campagne du jeu"

- ship: Supply/distribute files or content, rather than a naval vessel.

### transfer.merc_icons_off

Terms: mercenary

English: "<b>Off (default):</b> a copy in every faction folder the unit is owned by, plus the merc folders as a fallback. No pinning needed."

French: "<b>Désactivé (par défaut) :</b> une copie dans le dossier de chaque faction possédant l’unité, ainsi que dans les dossiers merc en secours. Aucun chemin explicite nécessaire."

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### transfer.merc_icons_on

Terms: mercenary

English: "<b>On:</b> cards go to the merc folders only, pinned with <code>card_pic_dir</code> / <code>info_pic_dir</code>."

French: "<b>Activé :</b> les cartes vont uniquement dans les dossiers merc, avec les chemins fixés par <code>card_pic_dir</code> / <code>info_pic_dir</code>."

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### transfer.put_the_unit_card_and_info

Terms: mercenary

English: "Put the unit card and info card in the merc folders ONLY"

French: "Placer la carte d’unité et la carte d’information UNIQUEMENT dans les dossiers merc"

- mercenary: Literal merc/mercs path or fallback-directory name is retained.

### v3anim.building_the_glb

Terms: building

English: "Building the .glb…"

French: "Création du .glb…"

- building: Literal keyword, code/path, or non-building sense is retained.

### v3anim.building_the_obj_zip

Terms: building

English: "Building the .obj zip…"

French: "Création de l’archive zip .obj…"

- building: Literal keyword, code/path, or non-building sense is retained.

### v3anim.not_in_the_skeleton_pack_only_loose

Terms: ship

English: "Not in the skeleton pack; these are <code>descr_skeleton.txt</code>’s actions, and only the ones shipped loose play."

French: "Absent du pack de squelettes ; ces actions proviennent de <code>descr_skeleton.txt</code>, et seules celles fournies comme fichiers non archivés sont lues."

- ship: Supply/distribute files or content, rather than a naval vessel.

### v3anim.played_from_vanillas_pack_this_mod

Terms: ship

English: "Played from vanilla’s pack: this mod ships none of its own to save an edit into."

French: "Lue depuis le pack vanilla : ce mod n’a pas de pack propre où enregistrer une modification."

- ship: Supply/distribute files or content, rather than a naval vessel.

### v3anim.turn_every_key

Terms: turn

English: "<span>Turn, every key</span> {x}°"

French: "<span>Rotation à chaque clé</span> {x}°"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### v3anim.turns_to

Terms: turn

English: " · turns {turn}° to {turn2}°"

French: " · rotation de {turn}° à {turn2}°"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### v3anim.vanillas_skeleton_pack_this_mod_ships

Terms: ship

English: "vanilla’s skeleton pack (this mod ships none, so the game plays vanilla’s)"

French: "pack de squelettes vanilla (ce mod n’en fournit aucun ; le jeu utilise donc celui de vanilla)"

- ship: Supply/distribute files or content, rather than a naval vessel.

### viewer3d.drag_to_turn_wheel_to_zoom

Terms: turn

English: "drag to turn · wheel to zoom · right-drag to pan"

French: "faites glisser pour tourner · molette pour zoomer · bouton droit et glisser pour déplacer la vue"

- turn: Rotate, enable/disable, invert, or transform, rather than a campaign turn.

### viewer3d.draw_the_texture_at_the_size

Terms: ship

English: "Draw the texture at the size the mod ships it, instead of halving anything over\n1024. That is the size the game draws, so it is the one to check a skin's own detail\nagainst. Off by default: a 2048 sheet is four times the bytes and the video memory\nfor a soldier on screen a few hundred pixels tall."

French: "Afficher la texture à la taille fournie par le mod, au lieu de diviser par deux celles dépassant\n1024. C’est la taille utilisée par le jeu, donc celle à examiner pour vérifier les détails\nde la texture. Désactivé par défaut : une planche 2048 demande quatre fois plus d’octets et de mémoire vidéo\npour un soldat affiché sur quelques centaines de pixels de hauteur."

- ship: Supply/distribute files or content, rather than a naval vessel.

### viewer3d.drawn_at_shipped

Terms: ship

English: "drawn at <b>{w} × {h}</b> - the size the mod ships, as the game draws it"

French: "affichée en <b>{w} × {h}</b>, taille fournie par le mod et utilisée par le jeu"

- ship: Supply/distribute files or content, rather than a naval vessel.

### viewer3d.in_game_units

Terms: unit

English: "{x} × {x2} × {x3} in game units"

French: "{x} × {x2} × {x3} en unités du jeu"

- unit: Literal unit keyword/path rather than a translated unit label.

### voices.no_name_call

Terms: general

English: "No name call of its own in the voice bank; it says its class's general line."

French: "Aucune annonce propre dans la banque de voix ; l’unité utilise la réplique générique de sa classe."

- general: Generic/general setting or literal General token, rather than a commander.

### voices.own_compiled

Terms: event

English: "The mod's compiled data/sounds/events.dat and events.idx are removed (backed up); the game builds them again on its next start."

French: "Les fichiers compilés data/sounds/events.dat et events.idx du mod sont retirés après sauvegarde ; le jeu les recrée au prochain démarrage."

- event: Literal event keyword or events file/path is retained.

### voices.own_note

Terms: event

English: "Pick the accent and class it is for and one or more .wav files (the game's own are 22050 Hz, 16-bit, mono). They go in as loose files under new names, the unit gets its own line for that accent and class, and the compiled events.dat and events.idx are removed so the game rebuilds them."

French: "Choisissez l’accent et la classe concernés, puis un ou plusieurs fichiers .wav (ceux du jeu sont en 22050 Hz, 16 bits, mono). Ils sont ajoutés hors archive sous de nouveaux noms ; l’unité reçoit sa propre ligne pour cet accent et cette classe. Les fichiers compilés events.dat et events.idx sont retirés pour que le jeu les reconstruise."

- event: Literal event keyword or events file/path is retained.
