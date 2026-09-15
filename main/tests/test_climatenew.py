"""Declaring a climate, and the slot it really goes in (34).

    python -m tests.test_climatenew

One little mod written here with the four files a climate is declared across,
each in the awkward shape a real one has: ``descr_climates.txt`` with a
``climates { }`` list carrying trailing comments, a ``climate <name>`` header
with a comment after it, CRLF line endings, an aerial file whose blocks are
tab-separated and sometimes one column, a lookup list that is already out of
step with the declared list, and a UTF-16 ``text/climates.txt``.

**The suite is about the two roads and the difference between them.** A
take-over keeps its place in the index and touches the list not at all; an add
goes on the end of both and carries the geography warning. Everything else -
the colour clash, the heat range, the name shape, the donor, the two tile counts
- is checked against the little mod, and then every installed mod is planned
against for real and never applied.

Section 7 is the phase's own finding and the reason it is shaped this way: all
four installed mods declare exactly the twelve climates the engine ships, in the
engine's order.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, climatenew as cn, config, mapterrain, mapvocab
from unittransfer import keyblock as kb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little mod ----------------------------------------------------------

# CRLF throughout, a comment after the header of one block, trailing comments in
# the list, and a block whose closing brace is indented - every shape the real
# files were measured in.
CLIMATES = (
    ";;;;;;;;;;;;;;;;;;;;;;;;;;;\r\n"
    ";\theat\trange 1-4\r\n"
    ";;;;;;;;;;;;;;;;;;;;;;;;;;;\r\n"
    "\r\n"
    "climates\r\n"
    "{\r\n"
    "\tmediterranean\t\t;Various\t2\r\n"
    "\tunused1\t\t\t;spare\t\t0\r\n"
    "\talpine\t\t\t;cold\t\t1\r\n"
    "}\r\n"
    "\r\n"
    "climate mediterranean\r\n"
    "{\r\n"
    "\tcolour\t236 0 140\r\n"
    "\theat\t2\r\n"
    "\r\n"
    "\tstrategy\tsummer\tsparse_tree\tolive_a.cas\t\t10\r\n"
    "\tbattle_vegetation\r\n"
    "\tdense_forest\t\tmedi_dense_forest\r\n"
    "\tenv_map\t\t\tdata/battlefield/envmaps/grass.dds\r\n"
    "}\r\n"
    "\r\n"
    "climate unused1 ;the spare one\r\n"
    "{\r\n"
    "\tcolour\t237 20 91\r\n"
    "\theat\t0\r\n"
    "}\r\n"
    "\r\n"
    "climate alpine\r\n"
    "{\r\n"
    "\tcolour\t57 181 74\r\n"
    "\theat\t1\r\n"
    "\twinter\r\n"
    "\tstrategy\tsummer\tsparse_tree\tconifer_a.cas\t\t7\r\n"
    "\tenv_map\t\t\tdata/battlefield/envmaps/snow.dds\r\n"
    "}\r\n"
)

# one-column and two-column lines, both of which parse
AERIAL = (
    "climate default\r\n"
    "{\r\n"
    "\tfertility_low\t\td_low.tga\t\td_low_w.tga\r\n"
    "\tfertility_medium\td_med.tga\t\td_med_w.tga\r\n"
    "\thills\t\t\td_hills.tga\r\n"
    "\tbeach\t\t\tbeach.tga\t\tbeach.tga\r\n"
    "}\r\n"
    "\r\n"
    "climate alpine\r\n"
    "{\r\n"
    "\tfertility_low\t\tsnow_low.tga\t\tsnow_low_w.tga\r\n"
    "\tfertility_medium\tsnow_med.tga\t\tsnow_med_w.tga\r\n"
    "\thills\t\t\tsnow_hills.tga\t\tsnow_hills_w.tga\r\n"
    "\tbeach\t\t\tbeach.tga\t\tbeach.tga\r\n"
    "}\r\n"
    "\r\n"
    "climate mediterranean\r\n"
    "{\r\n"
    "\tfertility_low\t\tm_low.tga\t\tm_low.tga\r\n"
    "\tfertility_medium\tm_med.tga\t\tm_med.tga\r\n"
    "\thills\t\t\tm_hills.tga\t\tm_hills.tga\r\n"
    "\tbeach\t\t\tbeach.tga\t\tbeach.tga\r\n"
    "}\r\n"
)

# already out of step, the way two installed mods are: it names a climate the
# declared list does not have
LOOKUP = "mediterranean\r\nunused1\r\nalpine\r\nvolcanic\r\n"

NAMES = "{mediterranean}Middle Sea\r\n{alpine}The Peaks\r\n"

GEOG = (
    "generation\n{\n\tsome_setting\t1\n}\n"
    "\n; Climates\n; --------\n\n"
    "mediterranean\n{\n\tseason summer\n\t{\n\t\ttexture rock a.tga\n\t}\n}\n"
    "\nunused1 modifies mediterranean\n{\n\tseason summer\n\t{\n\t}\n}\n"
    "\nalpine \n{\n\tseason summer\n\t{\n\t}\n}\n"
)


def little_mod(lookup=True, names=True, geog=True):
    root = Path(_tmp.mkdtemp(prefix="ut_clim_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    kb.write_text(data / cn.CLIMATES_REL, CLIMATES, cn.ENCODING)
    kb.write_text(data / cn.AERIAL_REL, AERIAL, cn.ENCODING)
    if lookup:
        kb.write_text(data / cn.LOOKUP_REL, LOOKUP, cn.ENCODING)
    if names:
        kb.write_text(data / cn.NAMES_REL, NAMES, cn.LOC_ENCODING)
    if geog:
        kb.write_text(data / cn.GEOG_REL, GEOG, cn.ENCODING)
    return Mod(root)


def reread(plan):
    """The plan's own texts as a mod, so the real parsers judge them."""
    root = Path(_tmp.mkdtemp(prefix="ut_clim_out_"))
    (root / "data" / "text").mkdir(parents=True)
    for rel, text in plan.texts.items():
        t = root / "data" / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        kb.write_text(t, text, cn.ENCODING)
    return Mod(root)


# every write in sections 9 and 10 goes into a scratch config, never the real one
cfg = Path(_tmp.mkdtemp(prefix='ut_cfg_'))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / 'backups'
config.SETTINGS_PATH = cfg / 'settings.json'
config.LOG_PATH = cfg / 'transfers.json'
config._cache_dir = cfg / 'cache'


# ---- 1: the mod is read as it stands -----------------------------------------

print("\n1. what the little mod already says")
mod = little_mod()
v = cn.view(mod)
check("three climates are declared, in the list's order",
      [s["code"] for s in v["slots"]] == ["mediterranean", "unused1", "alpine"])
check("unused1 is marked spare and the other two are not",
      [s["spare"] for s in v["slots"]] == [False, True, False])
check("the display names come out of text/climates.txt, UTF-16",
      [s["label"] for s in v["slots"]] == ["Middle Sea", "", "The Peaks"])
check("the ground types are the mod's own, not a constant - 4 of them",
      v["grounds"] == ["beach", "fertility_low", "fertility_medium", "hills"])
check("default is offered as a donor first",
      v["donors"] and v["donors"][0]["code"] == "default")
check("the geography file names its three climates and not its settings block",
      v["geography"]["have"]
      and v["geography"]["names"] == ["alpine", "mediterranean", "unused1"])
check("the lookup drift is reported: volcanic is named and not declared",
      v["lookup"]["extra"] == ["volcanic"] and not v["lookup"]["missing"])
check("with no map passed, every tile count is zero rather than a guess",
      all(s["tiles"] == 0 for s in v["slots"]))
check("unused1 has no texture block and the panel says so",
      [s["aerial"] for s in v["slots"]] == [True, False, True])


# ---- 2: taking a slot over ---------------------------------------------------

print("\n2. taking unused1 over - the slot keeps its place")
p = cn.plan(mod, None, {"code": "unused1", "label": "Harondor",
                        "colour": [12, 90, 200], "heat": 3, "winter": True,
                        "donor": "alpine"})
check("it is a take-over and not an add", p.mode == "take" and not p.errors)
check("three files are written and the lookup is not - unused1 is in it already",
      sorted(p.texts) == [cn.AERIAL_REL, cn.CLIMATES_REL])
check("the display name is a write of its own, and it is a NEW key - a spare "
      "slot is exactly the one with no entry in text/climates.txt",
      p.loc_writes == {"unused1": "Harondor"} and p.loc_new == ["unused1"])
p2 = cn.plan(mod, None, {"code": "alpine", "label": "The Peaks",
                         "colour": [57, 181, 74], "donor": "alpine"})
check("a slot that already has an entry there is not a new key",
      p2.loc_writes == {"alpine": "The Peaks"} and p2.loc_new == [])
out = reread(p)
cl = mapvocab.climates(out)
check("re-read: still three climates, in the same order",
      [c["code"] for c in cl] == ["mediterranean", "unused1", "alpine"])
hit = [c for c in cl if c["code"] == "unused1"][0]
check("re-read: unused1 is index 1 still - the list was not touched",
      hit["index"] == 1)
check("re-read: the colour, the heat and the winter flag are the new ones",
      hit["rgb"] == (12, 90, 200) and hit["heat"] == 3 and hit["winter"])
check("the other two blocks are untouched, byte for byte",
      all(f"climate {c}" in p.texts[cn.CLIMATES_REL]
          for c in ("mediterranean", "alpine"))
      and "236 0 140" in p.texts[cn.CLIMATES_REL]
      and "57 181 74" in p.texts[cn.CLIMATES_REL])
blocks = mapterrain.parse(p.texts[cn.AERIAL_REL])
check("the aerial file gains a block for unused1, four ground types",
      len(blocks) == 4 and len(blocks["unused1"]) == 4)
check("every pair is the donor's, in both seasons",
      blocks["unused1"] == blocks["alpine"])
check("the file keeps its CRLF line endings",
      "\r\n" in p.texts[cn.CLIMATES_REL]
      and "\n\n" not in p.texts[cn.CLIMATES_REL].replace("\r\n", "\r"))


# ---- 3: a take-over that inherits its own trimmings --------------------------

print("\n3. what a take-over keeps and what it replaces")
p3 = cn.plan(mod, None, {"code": "alpine", "colour": [1, 2, 3], "heat": 0,
                         "winter": False, "donor": "default"})
body = p3.texts[cn.CLIMATES_REL]
check("alpine's own strategy line survives being taken over",
      "conifer_a.cas" in body)
check("its env map survives too", "envmaps/snow.dds" in body)
check("but its winter flag is gone, because the form said summer all year",
      not [c for c in mapvocab.climates(reread(p3))
           if c["code"] == "alpine"][0]["winter"])
check("and the old colour is not still in the block",
      "57 181 74" not in body)
p3b = cn.plan(mod, None, {"code": "new_one", "colour": [1, 2, 3],
                          "donor": "default"})
p3c = cn.plan(mod, None, {"code": "new_one", "colour": [1, 2, 3],
                          "donor": "mediterranean"})
blk = p3c.texts[cn.CLIMATES_REL]
blk = blk[blk.index("climate new_one"):]
check("an ADD inherits the DONOR's trimmings - its strategy line, its battle "
      "vegetation and its env map, which it has no way to invent",
      p3c.mode == "add" and p3c.trimmings and "olive_a.cas" in blk
      and "medi_dense_forest" in blk and "envmaps/grass.dds" in blk)
check("  and not the donor's colour, heat or winter, which the form gave",
      "236 0 140" not in blk and "\tcolour\t1 2 3" in blk)
blk_d = p3b.texts[cn.CLIMATES_REL]
blk_d = blk_d[blk_d.index("climate new_one"):]
check("but `default` is a block of the AERIAL file and NOT a declared climate, "
      "so an add copying from it gets colour, heat and nothing else",
      p3b.mode == "add" and not p3b.trimmings
      and "strategy" not in blk_d and "env_map" not in blk_d)
check("  and that is said out loud, naming what it costs and what to copy "
      "from instead - it is the first donor offered, so it is the likeliest ask",
      any("no trees on it" in w and "mediterranean" in w
          for w in p3b.warnings))
check("  a take-over never raises it: a declared climate has its own",
      p3.trimmings and not any("no trees on it" in w for w in p3.warnings))


# ---- 4: adding a name --------------------------------------------------------

print("\n4. adding a name the engine does not ship")
p4 = cn.plan(mod, None, {"code": "frozen_arctic", "label": "Frozen Arctic",
                         "colour": [207, 132, 255], "heat": 0, "winter": True,
                         "donor": "alpine"})
check("it is an add", p4.mode == "add" and not p4.errors)
check("all three texts are written, the lookup among them",
      sorted(p4.texts) == [cn.AERIAL_REL, cn.CLIMATES_REL, cn.LOOKUP_REL])
check("the display name is a NEW key this time",
      p4.loc_new == ["frozen_arctic"])
out4 = reread(p4)
cl4 = mapvocab.climates(out4)
check("re-read: four climates, the new one last and index 3",
      len(cl4) == 4 and cl4[-1]["code"] == "frozen_arctic"
      and cl4[-1]["index"] == 3)
check("re-read: the twelve-slot order in front of it did not move",
      [c["code"] for c in cl4[:3]] == ["mediterranean", "unused1", "alpine"])
check("the lookup gains it at the end and keeps volcanic where it was",
      cn.lookup_names(out4) == ["mediterranean", "unused1", "alpine",
                                "volcanic", "frozen_arctic"])
geo_warn = [w for w in p4.warnings if cn.GEOG_REL in w]
check("the geography warning fires, names the file and names the count",
      len(geo_warn) == 1 and "3 climate(s)" in geo_warn[0])
check("and it names the two spare slots as the way round it",
      "unused1 or unused2" in geo_warn[0])
check("a take-over of a name the geography DOES know raises no such warning",
      not [w for w in p.warnings if cn.GEOG_REL in w])


# ---- 5: what is refused ------------------------------------------------------

print("\n5. the refusals, and the one that is not a refusal")
bad = cn.plan(mod, None, {"code": "alpine_2", "colour": [57, 181, 74]})
check("a colour another climate already declares is refused, and names it",
      bad.errors and "alpine already declares" in bad.errors[0])
check("the refusal says why, in one sentence about the TGA",
      bad.errors and "Two climates on one colour is one climate" in bad.errors[0])
same = cn.plan(mod, None, {"code": "alpine", "colour": [57, 181, 74]})
check("but a climate keeping its OWN colour is not a clash with itself",
      not same.errors)
for code, why in (("", "no name"), ("2cold", "a digit first"),
                  ("a b", "a space"), ("a.b", "a dot")):
    r = cn.plan(mod, None, {"code": code, "colour": [1, 2, 3]})
    check(f"  {why} is refused as a climate name", bool(r.errors))
check("a bare word with an underscore is not",
      not cn.plan(mod, None, {"code": "frozen_arctic",
                              "colour": [1, 2, 3]}).errors)
for heat in (-1, 5):
    r = cn.plan(mod, None, {"code": "x", "colour": [1, 2, 3], "heat": heat})
    check(f"  heat {heat} is refused", bool(r.errors))
check("heat 0 is not - the file's own comment says zero means no effect",
      not cn.plan(mod, None, {"code": "x", "colour": [1, 2, 3],
                              "heat": 0}).errors)
for colour, why in (([1, 2], "two numbers"), ([1, 2, 300], "300"),
                    ("nope", "a word"), (None, "nothing")):
    r = cn.plan(mod, None, {"code": "x", "colour": colour})
    check(f"  a colour given as {why} is refused", bool(r.errors))
check("a colour given as the string '1 2 3' is read, not refused",
      not cn.plan(mod, None, {"code": "x", "colour": "1 2 3"}).errors)
r = cn.plan(mod, None, {"code": "x", "colour": [1, 2, 3], "donor": "nosuch"})
check("a donor with no block is refused and the real ones are listed",
      r.errors and "default" in r.errors[0] and "alpine" in r.errors[0])


# ---- 6: the files that may not be there --------------------------------------

print("\n6. a mod missing one of the four")
nolk = little_mod(lookup=False)
vl = cn.view(nolk)
check("no lookup file: reported as not there rather than as empty",
      not vl["lookup"]["have"] and "no descr_climates_lookup" in
      vl["lookup"]["note"])
pl = cn.plan(nolk, None, {"code": "frozen_arctic", "colour": [9, 9, 9]})
check("and nothing is written to it", cn.LOOKUP_REL not in pl.texts)
nog = little_mod(geog=False)
vg = cn.view(nog)
check("no geography text: 'cannot be checked' rather than 'no climate has one'",
      not vg["geography"]["have"] and vg["geography"]["problem"])
pg = cn.plan(nog, None, {"code": "frozen_arctic", "colour": [9, 9, 9]})
check("the add warning still fires, and says the check could not be made",
      any("cannot be checked" in w or "spare by name" in w
          for w in pg.warnings))
check("a take-over on that same mod still raises no geography warning",
      not [w for w in cn.plan(nog, None,
                              {"code": "unused1", "colour": [9, 9, 9]}).warnings
           if "battle" in w and "crash" in w])
non = little_mod(names=False)
pn = cn.plan(non, None, {"code": "unused1", "label": "Harondor",
                         "colour": [9, 9, 9]})
check("no text/climates.txt: the key is still planned, as a new one",
      pn.loc_writes == {"unused1": "Harondor"} and pn.loc_new == ["unused1"])
check("no label at all: the file is left alone and the panel says why",
      not cn.plan(mod, None, {"code": "unused1",
                              "colour": [9, 9, 9]}).loc_writes
      and any("shows as its code name" in w for w in
              cn.plan(mod, None, {"code": "unused1",
                                  "colour": [9, 9, 9]}).warnings))


# ---- 7: the twelve, on every installed mod -----------------------------------

print("\n7. every installed mod - the phase's own finding")
seen = False
for root in _realmod.installed():
    rmod = Mod(root)
    cl = mapvocab.climates(rmod)
    if not cl:
        print(f"  (skipped {rmod.name} - no {cn.CLIMATES_REL})")
        continue
    seen = True
    codes = [c["code"] for c in cl]
    check(f"  {rmod.name}: declares exactly the twelve the engine ships, "
          f"in the engine's order", codes == list(cn.VANILLA_ORDER))
    rv = cn.view(rmod)
    check(f"  {rmod.name}: {len(rv['grounds'])} ground types, "
          f"{len(rv['donors'])} donor block(s), "
          f"{'a' if rv['lookup']['have'] else 'no'} lookup"
          + (f" ({len(rv['lookup']['extra'])} extra)"
             if rv["lookup"]["have"] else ""),
          rv["have"] and rv["grounds"] and rv["donors"])
    # a take-over of unused2, planned for real and never applied
    rp = cn.plan(rmod, None, {"code": "unused2", "label": "Toolkit Test",
                              "colour": [3, 7, 11], "heat": 1, "winter": True,
                              "donor": rv["donors"][0]["code"]})
    check(f"  {rmod.name}: unused2 taken over - {len(rp.texts)} file(s), "
          f"{len(rp.grounds)} ground type(s), {len(rp.warnings)} warning(s)",
          not rp.errors and rp.mode == "take" and rp.texts)
    rout = reread(rp)
    rcl = mapvocab.climates(rout)
    check(f"  {rmod.name}: re-read as twelve still, unused2 at index 7 with "
          f"the new colour",
          [c["code"] for c in rcl] == list(cn.VANILLA_ORDER)
          and rcl[7]["code"] == "unused2" and rcl[7]["rgb"] == (3, 7, 11))
    rblocks = mapterrain.parse(rp.texts[cn.AERIAL_REL])
    check(f"  {rmod.name}: its aerial block names every ground type the mod's "
          f"own blocks do, in both seasons",
          sorted(rblocks["unused2"]) == sorted(rp.grounds)
          and all(len(v) == 2 and v[0] and v[1]
                  for v in rblocks["unused2"].values()))
    check(f"  {rmod.name}: no other block moved - "
          f"{len(rblocks)} block(s) before and after",
          len(rblocks) == len(mapterrain.read_vocabulary(rmod).blocks)
          or "unused2" not in mapterrain.read_vocabulary(rmod).blocks)

if not seen:
    print(f"  SKIPPED - no installed mod has a {cn.CLIMATES_REL}")


# ---- 8: the tile counts, against a real map ----------------------------------

print("\n8. the two tile counts, against a real map")
root = _realmod.pick("Divide_and_Conquer_EUR", need=cn.CLIMATES_REL)
rmod = Mod(root)
try:
    cm = campmap.CampaignMap(rmod)
    tiles = cn.climate_tiles(cm)
except (campmap.MapError, OSError) as exc:
    print(f"  SKIPPED - {rmod.name}'s climates layer will not read: {exc}")
    tiles = None
if tiles:
    cl = mapvocab.climates(rmod)
    check(f"  {rmod.name}: every declared colour is in the census "
          f"({len(tiles)} distinct, {sum(tiles.values()):,} tiles)",
          all(mapvocab.key(c["rgb"]) in tiles for c in cl if c["rgb"]))
    spare = [c for c in cl if c["code"] in cn.SPARE and c["rgb"]]
    for c in spare:
        n = tiles.get(mapvocab.key(c["rgb"]), 0)
        print(f"     {rmod.name}: {c['code']} is painted on {n:,} tile(s)")
    rp = cn.plan(rmod, cm, {"code": "unused2", "colour": [3, 7, 11],
                            "donor": "default"})
    old = [c for c in cl if c["code"] == "unused2"][0]["rgb"]
    check(f"  {rmod.name}: the orphan count is the slot's OLD colour's tiles",
          rp.orphan_rgb == tuple(old)
          and rp.orphan_tiles == tiles.get(mapvocab.key(old), 0))
    check(f"  {rmod.name}: the claimed count is the NEW colour's, which "
          f"nothing paints", rp.claimed_tiles == 0)
    if rp.orphan_tiles:
        check(f"  {rmod.name}: and a warning says so, with the number",
              any(f"{rp.orphan_tiles:,} tile(s) are painted" in w
                  for w in rp.warnings))
    keep = cn.plan(rmod, cm, {"code": "unused2", "colour": list(old),
                              "donor": "default"})
    check(f"  {rmod.name}: keeping the slot's own colour orphans nothing",
          keep.orphan_tiles == 0 and not keep.orphan_rgb
          and keep.claimed_tiles == tiles.get(mapvocab.key(old), 0))
    check(f"  {rmod.name}: a map that will not read is not a refusal - the "
          f"plan is the same minus the counts",
          sorted(cn.plan(rmod, None, {"code": "unused2",
                                      "colour": [3, 7, 11],
                                      "donor": "default"}).texts)
          == sorted(rp.texts))


# ---- 9: applied, and read back off disk --------------------------------------

print("\n9. the save")
import shutil

med2 = Path(_tmp.mkdtemp(prefix="ut_clim_med2_"))
staged = little_mod()
shutil.copytree(staged.root, med2 / "mods" / "Tiny")
live = Mod(med2 / "mods" / "Tiny")

p9 = cn.plan(live, None, {"code": "unused1", "label": "Harondor",
                          "colour": [12, 90, 200], "heat": 3, "winter": True,
                          "donor": "alpine"})
res = cn.apply(p9)
check(f"  one log entry, {len(res['files'])} file(s) written, mode {res['mode']}",
      bool(res["id"]) and res["mode"] == "take"
      and sorted(res["files"]) == [cn.AERIAL_REL, cn.CLIMATES_REL])
man = res["record"]["manifest"]
check(f"  the two texts and the localisation all existed, so they are backed up "
      f"rather than created: {len(man['backed_up'])} backed up, "
      f"{len(man['created'])} created",
      len(man["backed_up"]) == 3 and len(man["created"]) == 1)
check("  and text/climates.txt's compiled copy is in the backup set beside it, "
      "so an undo cannot leave the game reading the new text",
      any(r.endswith(".strings.bin")
          for r in man["backed_up"] + man["created"]))
again = mapvocab.climates(live)
hit = [c for c in again if c["code"] == "unused1"][0]
check("  read off disk: unused1 is index 1 with the new colour, heat and winter",
      hit["index"] == 1 and hit["rgb"] == (12, 90, 200) and hit["heat"] == 3
      and hit["winter"])
check("  read off disk: its display name is Harondor, out of the UTF-16 file",
      hit["name"] == "Harondor")
check("  the other two climates are untouched",
      [c["code"] for c in again] == ["mediterranean", "unused1", "alpine"]
      and [c for c in again if c["code"] == "alpine"][0]["rgb"] == (57, 181, 74))
voc9 = mapterrain.read_vocabulary(live)
check("  read off disk: the aerial file now gives unused1 a block, and it is "
      "alpine's",
      voc9.blocks.get("unused1") == voc9.blocks.get("alpine"))
check("  and mapterrain draws with it - a tile of unused1 has its OWN texture "
      "in both seasons now, where before it fell through to the default block",
      voc9.texture("unused1", "fertility_low", "summer") == "snow_low.tga"
      and voc9.texture("unused1", "fertility_low", "winter") == "snow_low_w.tga")
check("  the lookup was not touched - unused1 was already in it",
      cn.lookup_names(live) == ["mediterranean", "unused1", "alpine", "volcanic"])
try:
    cn.apply(cn.plan(live, None, {"code": "x", "colour": [1, 2]}))
    check("  a plan with errors refuses to apply", False)
except ValueError as exc:
    check(f"  a plan with errors refuses to apply: {str(exc)[:38]}...",
          "cannot apply" in str(exc))


# ---- 10: the two routes ------------------------------------------------------

print("\n10. GET /api/map/climates and POST /api/map/climate_plan|_apply")

import json
import threading
import urllib.error
import urllib.request

from unittransfer.server import Handler, Registry, _Server   # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    d = get("/api/map/climates?mod=Tiny")
    check(f"  GET answers with {len(d['slots'])} slot(s), {len(d['donors'])} "
          f"donor(s) and the lookup's own drift",
          d["have"] and len(d["slots"]) == 3 and d["donors"]
          and d["lookup"]["extra"] == ["volcanic"])
    check("  this mod has no map layers at all, and every slot still comes back "
          "with its tile count at zero - the map is read if it can be and is "
          "never required",
          all(s["tiles"] == 0 for s in d["slots"]))
    before = [c for c in mapvocab.climates(live)
              if c["code"] == "alpine"][0]["rgb"]
    r = post("/api/map/climate_plan", {"mod": "Tiny", "code": "alpine",
                                       "colour": [9, 9, 9], "donor": "default"})
    check(f"  POST _plan answers with the plan and writes nothing: "
          f"{len(r['plan']['files'])} file(s), "
          f"{len(r['plan']['changes'])} change(s)",
          r["plan"]["ok"] and r["plan"]["mode"] == "take"
          and [c for c in mapvocab.climates(live)
               if c["code"] == "alpine"][0]["rgb"] == before)
    r = post("/api/map/climate_plan", {"mod": "Tiny", "code": "alpine",
                                       "colour": [12, 90, 200]})
    check("  a plan that clashes comes back as an error rather than a traceback",
          not r["plan"]["ok"] and r.get("error")
          and "unused1 already declares" in r["error"])
    r = post("/api/map/climate_apply", {"mod": "Tiny", "code": "frozen_arctic",
                                        "label": "Frozen Arctic",
                                        "colour": [207, 132, 255], "heat": 0,
                                        "winter": True, "donor": "alpine"})
    check(f"  POST _apply writes it and answers with the log id: "
          f"{len(r.get('files', []))} file(s)",
          bool(r.get("id")) and r.get("mode") == "add"
          and sorted(r["files"]) == [cn.AERIAL_REL, cn.CLIMATES_REL,
                                     cn.LOOKUP_REL])
    after = mapvocab.climates(live)
    check("  read off disk: four climates now, the new one last and named",
          len(after) == 4 and after[-1]["code"] == "frozen_arctic"
          and after[-1]["name"] == "Frozen Arctic")
    check("  the registry was invalidated, so the route's own answer moved with "
          "the file",
          len(get("/api/map/climates?mod=Tiny")["slots"]) == 4)
    try:
        get("/api/map/climates?mod=Nope")
        check("  an unknown mod is refused", False)
    except urllib.error.HTTPError as exc:
        check(f"  an unknown mod is refused with {exc.code}", exc.code == 404)
finally:
    httpd.shutdown()


print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
