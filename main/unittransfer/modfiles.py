"""What one mod actually has on disk, per module - the Home page's readiness matrix.

The reference tool opens with an upload box: you pick a ``data`` folder and it
tells you which files it found. We already know where every mod is, so the same
question is answered the other way round - for each mod the toolkit can see, say
which of the files each module needs are there, how big they are, and whether
they can be read at all.

The point is to answer "why is this greyed out" before it is asked. A mod with no
``export_descr_sounds_units_voice.txt`` is not broken and Unit Sounds is not
broken; there is simply nothing there, and saying so on the landing page is
cheaper than letting someone find out three clicks in.

Everything here is read-only and deliberately shallow: file paths come from
:class:`unittransfer.mod.Mod` (the one place that knows them) and a file is
opened only far enough to sniff its encoding, never parsed. A mod card must not
cost what opening the mod costs.
"""
from __future__ import annotations

from . import i18n as _i18n

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

#: module id -> the label the burger menu shows, so both agree without importing
#: anything from the page
MODULES: Dict[str, str] = {
    "transfer": _i18n.msg("eng.modfiles.unit_transfer", "Unit Transfer"),
    "edit": _i18n.msg("eng.modfiles.unit_editor", "Unit Editor"),
    "bmdb": _i18n.msg("eng.modfiles.bmdb_sprites_editor", "BMDB + Sprites Editor"),
    "sounds": _i18n.msg("eng.modfiles.unit_sounds", "Unit Sounds"),
    "sprites": _i18n.msg("eng.modfiles.sprites", "Sprites"),
    "buildings": _i18n.msg("eng.modfiles.buildings", "Buildings"),
    "traits": _i18n.msg("eng.modfiles.traits", "Traits"),
    "ancillaries": _i18n.msg("eng.modfiles.ancillaries", "Ancillaries"),
    "minor": _i18n.msg("eng.modfiles.minor_files", "Minor Files"),
    "strings": _i18n.msg("eng.modfiles.strings", "Strings"),
    "guilds": _i18n.msg("eng.modfiles.guilds", "Guilds"),
    "campdb": _i18n.msg("eng.modfiles.campaign_constants", "Campaign constants"),
    "settlemech": _i18n.msg("eng.modfiles.settlement_mechanics", "Settlement mechanics"),
    "factionsites": _i18n.msg("eng.modfiles.populace_and_off_map_models", "Populace and off-map models"),
    "sidefiles": _i18n.msg("eng.modfiles.animals_standards_and_advice", "Animals, standards and advice"),
    "banners": _i18n.msg("eng.modfiles.battle_banners", "Battle banners"),
    "heroabilities": _i18n.msg("eng.modfiles.hero_abilities", "Hero abilities"),
    "walls": _i18n.msg("eng.modfiles.walls_gates_and_towers", "Walls, gates and towers"),
    "characters": _i18n.msg("eng.modfiles.agents_and_generals", "Agents and generals"),
    "areaeffects": _i18n.msg("eng.modfiles.area_effects", "Area effects"),
    "campmap": _i18n.msg("eng.modfiles.campaign_map", "Campaign Map"),
    # 21, D11. Reads no file of its own - it opens whichever one it is asked
    # for - so it has no row below and its card is always ready.
    "rawtext": _i18n.msg("eng.modfiles.raw_text", "Raw text"),
    # 52. Reads the toolkit's own record of what it wrote, not a mod file, so
    # like Raw text it has no row below and its card is always ready.
    "changes": _i18n.msg("eng.modfiles.my_changes", "My changes"),
    # 54. Runs the other modules' checks over whatever files the mod has; a
    # missing file is that check's own finding, so it has no row below either.
    "health": _i18n.msg("eng.modfiles.health", "Health"),
}


@dataclass(frozen=True)
class Known:
    """One file (or folder) a module reads, and how much it matters to it."""
    rel: str                       # under the mod's data/
    label: str
    modules: tuple
    required: bool = True          # False = the module works without it, but poorer
    folder: bool = False


#: The two folders the campaign map lives in. Spelled out rather than imported
#: from campmap/campstrat, which pull in Pillow: a mod card must not cost what
#: opening the mod costs, and this module is the one that says so.
_MAP = "world/maps/base"
_CAMP = "world/maps/campaign/imperial_campaign"

#: Every game file the toolkit reads today. Ordered as a person would look for
#: them: the roster first, then what a unit points at, then the rest.
KNOWN: List[Known] = [
    Known("export_descr_unit.txt", _i18n.msg("eng.modfiles.unit_roster_edu", "Unit roster (EDU)"), ("transfer", "edit", "sprites")),
    Known("text/export_units.txt", _i18n.msg("eng.modfiles.unit_names_and_descriptions", "Unit names and descriptions"),
          ("transfer", "edit"), required=False),
    Known("unit_models/battle_models.modeldb", _i18n.msg("eng.modfiles.battle_models_bmdb", "Battle models (BMDB)"),
          ("transfer", "edit", "bmdb", "sprites")),
    Known("descr_mount.txt", _i18n.msg("eng.modfiles.mounts", "Mounts"), ("transfer", "edit"), required=False),
    Known("descr_projectile.txt", _i18n.msg("eng.modfiles.projectiles", "Projectiles"), ("transfer",), required=False),
    Known("descr_engines.txt", _i18n.msg("eng.modfiles.siege_engines", "Siege engines"), ("transfer",), required=False),
    Known("descr_mounted_engines.txt", _i18n.msg("eng.modfiles.mounted_engines", "Mounted engines"), ("transfer",), required=False),
    Known("descr_engine_skeleton.txt", _i18n.msg("eng.modfiles.engine_skeletons", "Engine skeletons"), ("transfer",), required=False),
    Known("export_descr_sounds_units_voice.txt", _i18n.msg("eng.modfiles.unit_voice_bank", "Unit voice bank"), ("sounds",)),
    Known("export_descr_buildings.txt", _i18n.msg("eng.modfiles.buildings_edb", "Buildings (EDB)"), ("buildings", "guilds")),
    Known("text/export_buildings.txt", _i18n.msg("eng.modfiles.building_names_and_descriptions", "Building names and descriptions"),
          ("buildings",), required=False),
    Known("descr_sm_factions.txt", _i18n.msg("eng.modfiles.factions_and_cultures", "Factions and cultures"),
          ("buildings", "minor"), required=False),
    Known("text/expanded.txt", _i18n.msg("eng.modfiles.faction_names", "Faction names"),
          ("transfer", "edit", "buildings"), required=False),
    Known("export_descr_character_traits.txt", _i18n.msg("eng.modfiles.character_traits_edct", "Character traits (EDCT)"), ("traits",)),
    Known("text/export_VnVs.txt", _i18n.msg("eng.modfiles.trait_names_and_descriptions", "Trait names and descriptions"),
          ("traits",), required=False),
    Known("export_descr_ancillaries.txt", _i18n.msg("eng.modfiles.ancillaries_eda", "Ancillaries (EDA)"), ("ancillaries",)),
    Known("text/export_ancillaries.txt", _i18n.msg("eng.modfiles.ancillary_names_and_descriptions", "Ancillary names and descriptions"),
          ("ancillaries",), required=False),
    Known("ui/ancillaries", _i18n.msg("eng.modfiles.ancillary_pictures", "Ancillary pictures"), ("ancillaries",),
          required=False, folder=True),
    # 18a. The guild file is required by its own module and optional to the
    # buildings one, which is the asymmetry that module closes: the EDB reads
    # perfectly well without it and every `guild_` requirement in it is then
    # unverifiable.
    Known("export_descr_guilds.txt", _i18n.msg("eng.modfiles.guilds", "Guilds"), ("guilds",)),
    # 38. Every campaign-wide constant, one small XML file.
    Known("descr_campaign_db.xml", _i18n.msg("eng.modfiles.campaign_constants", "Campaign constants"), ("campdb",)),
    # 59. How a settlement grows, keeps order and pays - and the mines.
    Known("descr_settlement_mechanics.xml", _i18n.msg("eng.modfiles.settlement_mechanics", "Settlement mechanics"), ("settlemech",)),
    # 63. Who walks a faction's streets, and its fleets and towns off the map.
    Known("descr_lbc_db.txt", _i18n.msg("eng.modfiles.settlement_populace", "Settlement populace"), ("factionsites",)),
    Known("descr_offmap_models.txt", _i18n.msg("eng.modfiles.off_map_models", "Off-map models"), ("factionsites",)),
    # 64. Three small files: war animals, the strat-map standard, the advisor.
    Known("descr_animals.txt", _i18n.msg("eng.modfiles.war_animals", "War animals"), ("sidefiles",), required=False),
    Known("descr_standards.txt", _i18n.msg("eng.modfiles.campaign_map_standards", "Campaign map standards"), ("sidefiles",), required=False),
    Known("export_descr_advice.txt", _i18n.msg("eng.modfiles.advisor_threads", "Advisor threads"), ("sidefiles",), required=False),
    # 65. The banners a unit carries in battle, one texture per faction.
    Known("descr_banners_new.xml", _i18n.msg("eng.modfiles.battle_banners", "Battle banners"), ("banners",)),
    # 68. A settlement's walls, gates and towers in battle, by wall level.
    Known("descr_walls.txt", _i18n.msg("eng.modfiles.walls_gates_and_towers", "Walls, gates and towers"), ("walls",)),
    # 69. What each agent is, and the models it stands and fights with.
    Known("descr_character.txt", _i18n.msg("eng.modfiles.agents_and_generals", "Agents and generals"), ("characters",)),
    # 66. A named character's battle ability, which descr_strat.txt names.
    Known("descr_hero_abilities.xml", _i18n.msg("eng.modfiles.hero_abilities", "Hero abilities"), ("heroabilities",)),
    # 67. What a projectile does where it lands: nausea, fire, explosions, sets.
    Known("descr_area_effects.xml", _i18n.msg("eng.modfiles.area_effects", "Area effects"), ("areaeffects",)),
    # The five small campaign files behind one module. All five are required
    # because each one IS a tab: a mod without descr_cultures.txt has no
    # settlements to draw, and saying so on the card is the point of the card.
    Known("descr_rebel_factions.txt", _i18n.msg("eng.modfiles.rebel_factions", "Rebel factions"), ("minor",)),
    Known("descr_religions.txt", _i18n.msg("eng.modfiles.religions", "Religions"), ("minor",)),
    Known("descr_religions_lookup.txt", _i18n.msg("eng.modfiles.religion_lookup", "Religion lookup"), ("minor",), required=False),
    Known("descr_sm_resources.txt", _i18n.msg("eng.modfiles.trade_resources", "Trade resources"), ("minor",)),
    Known("descr_cultures.txt", _i18n.msg("eng.modfiles.cultures_and_settlements", "Cultures and settlements"), ("minor",)),
    Known("descr_names.txt", _i18n.msg("eng.modfiles.character_names", "Character names"), ("minor",)),
    # The campaign map, in two halves. The map half is the ten TGA layers and
    # the two text files beside them under world/maps/base; the campaign half is
    # descr_strat.txt and descr_win_conditions.txt in the campaign folder, which
    # a map-only mod legitimately does not have. `required` mirrors
    # campmap.LAYERS exactly - five layers the engine will not start without and
    # five it treats as optional - and test_modfiles asserts the two agree, so
    # this list cannot drift from the module that reads them.
    Known(f"{_MAP}/descr_terrain.txt", _i18n.msg("eng.modfiles.map_tile_grid_descr_terrain", "Map tile grid (descr_terrain)"), ("campmap",)),
    Known(f"{_MAP}/descr_regions.txt", _i18n.msg("eng.modfiles.map_regions", "Map regions"), ("campmap",)),
    Known(f"{_MAP}/map_regions.tga", _i18n.msg("eng.modfiles.regions_layer", "Regions layer"), ("campmap",)),
    Known(f"{_MAP}/map_heights.tga", _i18n.msg("eng.modfiles.heights_layer", "Heights layer"), ("campmap",)),
    Known(f"{_MAP}/map_ground_types.tga", _i18n.msg("eng.modfiles.ground_types_layer", "Ground types layer"), ("campmap",)),
    Known(f"{_MAP}/map_climates.tga", _i18n.msg("eng.modfiles.climates_layer", "Climates layer"), ("campmap",)),
    Known(f"{_MAP}/map_features.tga", _i18n.msg("eng.modfiles.features_layer", "Features layer"), ("campmap",)),
    Known(f"{_MAP}/map_fog.tga", _i18n.msg("eng.modfiles.fog_layer", "Fog layer"), ("campmap",), required=False),
    Known(f"{_MAP}/map_trade_routes.tga", _i18n.msg("eng.modfiles.trade_routes_layer", "Trade routes layer"), ("campmap",),
          required=False),
    Known(f"{_MAP}/map_roughness.tga", _i18n.msg("eng.modfiles.roughness_layer", "Roughness layer"), ("campmap",), required=False),
    Known(f"{_MAP}/water_surface.tga", _i18n.msg("eng.modfiles.water_surface_layer", "Water surface layer"), ("campmap",),
          required=False),
    Known(f"{_MAP}/map_FE.tga", _i18n.msg("eng.modfiles.front_end_map_layer", "Front-end map layer"), ("campmap",), required=False),
    Known(f"{_CAMP}/descr_strat.txt", _i18n.msg("eng.modfiles.campaign_setup_descr_strat", "Campaign setup (descr_strat)"), ("campmap",),
          required=False),
    Known(f"{_CAMP}/descr_win_conditions.txt", _i18n.msg("eng.modfiles.victory_conditions", "Victory conditions"), ("campmap",),
          required=False),
    # 18a. The campaign folder's three small files. All three are optional: a
    # campaign runs without any of them - a faction with no description shows
    # its code name, a faction with no movie block plays none, and a province
    # in no mercenary pool sells nothing.
    Known(f"{_CAMP}/descr_mercenaries.txt", _i18n.msg("eng.modfiles.mercenary_pools", "Mercenary pools"), ("campmap",),
          required=False),
    Known(f"{_CAMP}/descr_faction_movies.xml", _i18n.msg("eng.modfiles.faction_movies", "Faction movies"), ("campmap",),
          required=False),
    Known("text/campaign_descriptions.txt", _i18n.msg("eng.modfiles.campaign_menu_text", "Campaign menu text"), ("campmap",),
          required=False),
    # 18b. Optional for the same reason, and more so: both installed mods ship
    # an EMPTY descr_disasters.txt and an empty or comment-only
    # descr_events.txt, so "not there" and "there and says nothing" are both the
    # ordinary case rather than a fault. The disaster file sits under
    # world/maps/base with the layers, not in the campaign folder.
    Known(f"{_CAMP}/descr_events.txt", _i18n.msg("eng.modfiles.historical_events", "Historical events"), ("campmap",),
          required=False),
    Known(f"{_MAP}/descr_disasters.txt", _i18n.msg("eng.modfiles.natural_disasters", "Natural disasters"), ("campmap",),
          required=False),
    Known("text", _i18n.msg("eng.modfiles.localisation_folder", "Localisation folder"), ("strings",), folder=True),
    Known("ui/units", _i18n.msg("eng.modfiles.unit_cards", "Unit cards"), ("transfer", "edit"), required=False, folder=True),
    Known("ui/unit_info", _i18n.msg("eng.modfiles.unit_info_cards", "Unit info cards"), ("transfer", "edit"),
          required=False, folder=True),
    Known("unit_models", _i18n.msg("eng.modfiles.model_and_texture_files", "Model and texture files"), ("bmdb", "sprites"), folder=True),
]


def _sniff(path: Path) -> str:
    """The file's text encoding, from its first bytes. Never parses."""
    try:
        with path.open("rb") as fh:
            head = fh.read(4)
    except OSError:
        return ""
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    if head[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    try:
        path.open("rb").read(4096).decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return "latin-1"
    return "utf-8"


def _entry(mod, k: Known) -> Dict:
    path = mod.data / k.rel
    row = {"rel": k.rel, "label": k.label, "modules": list(k.modules),
           "required": k.required, "folder": k.folder,
           "state": "missing", "size": 0, "encoding": "", "note": ""}
    try:
        st = path.stat()
    except OSError:
        # A missing file the module can live without is not worth a red mark, and
        # a compiled .strings.bin standing in for a missing .txt is not missing at
        # all - the game reads the compiled one.
        if not k.folder and (mod.data / (k.rel + ".strings.bin")).exists():
            row["state"] = "compiled"
            row["note"] = _i18n.msg("eng.modfiles.only_the_compiled_strings_bin_is_here_the_game_reads_that", "only the compiled .strings.bin is here - the game reads that")
        return row
    if k.folder:
        if not path.is_dir():
            row["note"] = _i18n.msg("eng.modfiles.expected_a_folder_found_a_file", "expected a folder, found a file")
            row["state"] = "unreadable"
            return row
        try:
            row["size"] = sum(1 for _ in path.iterdir())
        except OSError as e:
            row["state"] = "unreadable"
            row["note"] = str(e)
            return row
        row["state"] = "present" if row["size"] else "empty"
        return row
    row["size"] = st.st_size
    row["encoding"] = _sniff(path)
    if not row["encoding"]:
        row["state"] = "unreadable"
        row["note"] = _i18n.msg("eng.modfiles.the_file_is_there_but_could_not_be_opened", "the file is there but could not be opened")
    elif st.st_size == 0:
        row["state"] = "empty"
    else:
        row["state"] = "present"
    return row


def _module_rows(files: List[Dict]) -> Dict[str, Dict]:
    """Roll the file list up into one verdict per module."""
    out: Dict[str, Dict] = {}
    for mid, label in MODULES.items():
        mine = [f for f in files if mid in f["modules"]]
        bad = [f for f in mine if f["required"] and f["state"] in ("missing", "unreadable")]
        thin = [f for f in mine
                if not f["required"] and f["state"] in ("missing", "unreadable")]
        out[mid] = {
            "id": mid, "label": label,
            "ready": not bad,
            "missing": [f["label"] for f in bad],
            "partial": [f["label"] for f in thin],
            "files": len(mine),
        }
    return out


def campaign_title(mod) -> str:
    """The mod's campaign as it is named in game, or ``''``.

    Read through the compiled ``.strings.bin`` when the ``.txt`` is absent, which
    for a released mod is the normal case - see :mod:`unittransfer.stringsbin`.
    """
    from . import stringsbin
    for name, keys in (("menu_english.txt", ("UI_NEW_GAME_IMPERIAL_CAMPAIGN",)),
                       ("campaign_descriptions.txt", ("IMPERIAL_CAMPAIGN_TITLE",))):
        txt = mod.data / "text" / name
        pairs: Dict[str, str] = {}
        if txt.exists():
            try:
                pairs = dict(stringsbin.from_txt(
                    txt.read_text(encoding=stringsbin.TXT_ENCODING)))
            except (OSError, UnicodeError):
                pairs = {}
        if not pairs:
            pairs = stringsbin.load_pairs(stringsbin.bin_path_for(txt))
        for key in keys:
            value = (pairs.get(key) or "").strip()
            if value:
                return value
    return ""


def report(mod) -> Dict:
    """The whole readiness matrix for one mod."""
    files = [_entry(mod, k) for k in KNOWN]
    title = campaign_title(mod)
    return {
        "mod": mod.name,
        "root": str(mod.root),
        "title": title,
        # localised name first, code name in brackets - the rule the whole UI uses
        "label": f"{title} ({mod.name})" if title else mod.name,
        "files": files,
        "modules": _module_rows(files),
    }


def summary(mod) -> Dict:
    """The short form a mod card shows before anything is clicked."""
    r = report(mod)
    mods = r["modules"]
    return {"mod": r["mod"], "root": r["root"], "title": r["title"],
            "label": r["label"],
            "ready": [m for m in mods if mods[m]["ready"]],
            "blocked": [m for m in mods if not mods[m]["ready"]]}
