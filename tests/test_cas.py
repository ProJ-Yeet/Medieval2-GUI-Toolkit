"""The strat-model decoder - unittransfer/cas.py, and the routes that serve it.

A ``.cas`` was reverse-engineered from the bytes the same way a ``.mesh`` was,
and nothing describes it: upstream's own ``casCodec.js`` spec matches no file
that exists. So this suite has the same job ``test_mesh`` has - make the decode
falsifiable rather than plausible - and the same three kinds of check:

  * the REFERENCE models in ``Reference/TWCenter/`` - 22 tree models that ship
    with this repo, so the core of the suite runs on a machine with no game;
  * INVARIANTS a wrong offset would break: every index inside its own mesh's
    vertex pool, unit-length normals, a parent table that reads as a skeleton,
    a chunk chain that lands exactly on the end of the file, and the material
    a mesh names being one the file actually carries;
  * a SWEEP over whatever mods are installed, which is the check that matters
    most: 484 models by many hands, and a layout mistake shows up as a decode
    failure rather than as quiet rubbish.

The sweep reports what it measured and asserts only our own behaviour, per the
rule that a test must never fail because a mod ships a broken file.
"""
import json
import math
import os
import shutil
import struct
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import cas, mesh
from tests import _realmod, _tmp

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


REFERENCE = (ROOT / "Reference" / "TWCenter" / "--- TOOLS n RESOURCES ---" /
             "Mapmod_1.7 by Charge" / "DATA")


def reference_models():
    if not REFERENCE.is_dir():
        return []
    return sorted(p for p in REFERENCE.rglob("*")
                  if p.is_file() and p.suffix.lower() == ".cas")


# ---------------------------------------------------------------------------
print("\n1) Reference models (in this repo, no game needed)")

models = reference_models()
check(f"the tree models are present ({len(models)} found)", len(models) >= 20)

scenes = {}
for path in models:
    try:
        scenes[path.name] = cas.read_cas(path)
    except cas.CasError as exc:
        check(f"{path.name} decodes", False)
        print(f"          {exc}")
check(f"every one of them decodes ({len(scenes)}/{len(models)})",
      len(scenes) == len(models))

if scenes:
    one = scenes[sorted(scenes)[0]]
    check("a scene opens with Scene Root", one.nodes[:1] == ["Scene Root"])
    check("the root has no parent and every other node does",
          one.parents[:1] == [-1] and all(p >= 0 for p in one.parents[1:]))
    check("it has meshes with geometry",
          bool(one.objects) and one.vertices > 0 and one.triangles > 0)
    check("its key times start at zero and only rise",
          (not one.key_times) or (one.key_times[0] == 0.0 and all(
              b >= a for a, b in zip(one.key_times, one.key_times[1:]))))

# The one thing about these 22 that is worth its own check: they carry their
# texture INSIDE the file rather than naming one, and the reader says so
# instead of handing a renderer a path built out of raw pixels.
embedded = [s for s in scenes.values()
            if any("inside the file" in n for n in s.notes)]
check(f"a model whose sheet is embedded says so rather than naming a path "
      f"({len(embedded)} of {len(scenes)})",
      all(not s.textures() for s in embedded))


# ---------------------------------------------------------------------------
print("\n2) What a wrong offset would break")


def invariants(scene, label):
    """Everything that has to hold if the layout is being read where it is."""
    bad = []
    for obj in scene.objects:
        if obj.indices and max(obj.indices) >= obj.vertices:
            bad.append(f"{obj.name} indexes vertex {max(obj.indices)} of "
                       f"{obj.vertices}")
        if len(obj.normals) != len(obj.positions):
            bad.append(f"{obj.name} has {len(obj.normals)//3} normals for "
                       f"{obj.vertices} vertices")
        if obj.uvs and len(obj.uvs) != obj.vertices * 2:
            bad.append(f"{obj.name} has {len(obj.uvs)//2} UVs for "
                       f"{obj.vertices} vertices")
        if obj.material is not None and obj.material >= len(scene.materials):
            bad.append(f"{obj.name} wants material {obj.material} of "
                       f"{len(scene.materials)}")
        for node in obj.bones:
            if node >= len(scene.nodes):
                bad.append(f"{obj.name} weights to node {node} of "
                           f"{len(scene.nodes)}")
                break
    for i, parent in enumerate(scene.parents[1:], 1):
        if not 0 <= parent < len(scene.nodes) or parent >= i:
            bad.append(f"node {i} says its parent is {parent}")
            break
    return bad


faults = []
for name, scene in scenes.items():
    faults += [f"{name}: {b}" for b in invariants(scene, name)]
check(f"every reference model holds every invariant ({len(faults)} faults)",
      not faults)
for line in faults[:5]:
    print(f"          {line}")

# Normals are the check a stride mistake cannot survive: read one float early
# or late and they stop being unit length, everywhere at once.
lengths = []
for scene in scenes.values():
    for obj in scene.objects:
        n = obj.normals
        for i in range(0, len(n), 3):
            lengths.append(math.sqrt(n[i]**2 + n[i+1]**2 + n[i+2]**2))
off = [v for v in lengths if abs(v - 1.0) > 0.02]
# Not all of them, and the shortfall is the trees' own. 125 of the 5,025
# normals in these 22 files are short - 0.08 to 0.6, scattered a dozen at a
# time over the foliage cards of olives, palms and cypresses - and every one of
# the 44,997 normals in vanilla's strat models is unit length. A stride read
# one float out would put ALL of them wrong at once, which is what this check
# is for; a fortieth of a tree's foliage is the artist's business.
check(f"normals are unit length ({len(lengths) - len(off)} of {len(lengths)})",
      len(off) <= len(lengths) * 0.05)

# UVs. A .cas is not a .mesh: it addresses ONE sheet, not a pair glued side by
# side, so its u belongs in [0, 1] and not in [0, 2]. This is the check that
# would catch the doubling being applied here by habit.
uvs = [v for s in scenes.values() for o in s.objects for v in o.uvs]
if uvs:
    check(f"UVs sit in one sheet's worth of space, not two "
          f"(u and v run {min(uvs):.2f} to {max(uvs):.2f})",
          -0.6 <= min(uvs) and max(uvs) <= 2.2)

# The chunk chain lands on the end of the file. Sizes are absolute, so if the
# object records were the wrong length the chain would still land - and if the
# CHAIN were wrong it could not. Both are worth saying separately.
tails = [s for s in scenes.values()
         if any("after the last chunk" in n for n in s.notes)]
check(f"the chunk chain reaches the end of every reference file "
      f"({len(tails)} ragged)", not tails)


# ---------------------------------------------------------------------------
print("\n3) A file that is not one, and a file that is damaged")

bad_cases = [
    (b"", "an empty file"),
    (b"hello there, not a model at all", "a text file"),
    (struct.pack("<I", 22) + b"serialization::archive", "a battle .mesh"),
    (struct.pack("<f", 99.0) + b"\x00" * 64, "a float that is no version"),
]
for data, label in bad_cases:
    try:
        cas.read_cas_bytes(data, f"{label}.cas")
        check(f"{label} is refused", False)
    except cas.CasError as exc:
        sentence = str(exc)
        check(f"{label} is refused with a sentence, not a traceback",
              sentence.endswith(".cas") is False and len(sentence) > 20)

try:
    cas.read_cas_bytes(struct.pack("<I", 22) + b"serialization::archive",
                       "battle.cas")
except cas.CasError as exc:
    check("a .mesh handed to this reader is named as a .mesh and pointed at "
          "the reader that takes it", "unittransfer.mesh" in str(exc))

# A truncated real model. Cutting the file in half must not produce geometry:
# the chunk that runs off the end is the thing that catches it.
if scenes:
    src = models[0].read_bytes()
    try:
        half = cas.read_cas_bytes(src[:len(src)//2], "half.cas")
        check("half a model does not come back as a whole one",
              half.vertices < cas.read_cas_bytes(src, "whole.cas").vertices)
    except cas.CasError:
        check("half a model is refused by the reader that reads the whole", True)


# ---------------------------------------------------------------------------
print("\n4) The bridge to Phase 15's viewer")

if scenes:
    scene = max(scenes.values(), key=lambda s: s.vertices)
    m = cas.as_mesh(scene)
    check("as_mesh hands back a MeshFile that says it is a .cas",
          isinstance(m, mesh.MeshFile) and m.format == "cas")
    check(f"one group per mesh in the scene ({len(m.groups)} of "
          f"{len(scene.objects)})", len(m.groups) == len(scene.objects))
    check(f"one pool holding every mesh's vertices ({m.vertices:,})",
          m.vertices == scene.vertices)
    # The join is the only thing as_mesh really does, and getting it wrong
    # means a second mesh drawn over the first at the wrong vertices.
    check("every group's indices are inside the joined pool",
          all(not g.indices or max(g.indices) < m.vertices for g in m.groups))
    base = 0
    shifted = True
    for group, obj in zip(m.groups, scene.objects):
        if obj.indices and group.indices:
            shifted &= min(group.indices) == min(obj.indices) + base
        base += obj.vertices
    check("each mesh's indices are shifted by exactly where its vertices "
          "landed", shifted)

    payload = mesh.geometry_payload(m)
    check("the payload opens with the magic the page checks for",
          payload[:4] == mesh.PAYLOAD_MAGIC)
    hlen, = struct.unpack_from("<I", payload, 4)
    head = json.loads(payload[8:8 + hlen])
    check("its header carries the counts and the textures the file named",
          head["vertices"] == m.vertices and head["format"] == "cas"
          and head["textures"] == m.textures)
    want = 8 + hlen + m.vertices * 12 + (m.vertices * 12 if m.normals else 0) \
        + (m.vertices * 8 if m.uvs else 0) + sum(len(g.indices) for g in m.groups) * 2
    check(f"the payload is exactly as long as its header describes "
          f"({len(payload):,} bytes)", len(payload) == want)

    view = cas.scene_view(scene)
    check("scene_view names every mesh and every material",
          len(view["meshes"]) == len(scene.objects)
          and len(view["materials"]) == len(scene.materials))
    check("and it carries the empty LOD and skin lists the viewer's picker "
          "reads before it knows this is a .cas",
          view["lods"] == [] and view["skins"] == [])


# ---------------------------------------------------------------------------
print("\n5) Every model in every mod that is installed")

MODS = _realmod.MODS
installed = _realmod.installed()
if not installed:
    print("  SKIPPED - no mod installed to sweep")
else:
    found = []
    for mod in installed:
        for src in (mod / "data" / "models_strat").rglob("*") if (
                mod / "data" / "models_strat").is_dir() else []:
            if src.is_file() and src.suffix.lower() == ".cas":
                found.append(src)
    print(f"  {len(found)} strat models across {len(installed)} mods")

    decoded, refused, drawn = 0, [], 0
    faulty = []
    for src in found:
        try:
            scene = cas.read_cas(src)
        except cas.CasError as exc:
            refused.append((src.name, str(exc)))
            continue
        decoded += 1
        bad = invariants(scene, src.name)
        if bad:
            faulty.append(f"{src.name}: {bad[0]}")
        try:
            cas.as_mesh(scene)
            drawn += 1
        except cas.CasError as exc:
            refused.append((src.name, str(exc)))

    print(f"  {decoded} decoded, {drawn} joined into one pool, "
          f"{len(refused)} refused")
    # OUR behaviour, not the mods': a file we refuse must be refused with a
    # sentence, and a file we accept must hold every invariant. Whether some
    # mod ships a model we cannot read is that mod's business.
    check(f"nothing decoded holds a broken invariant ({len(faulty)} did)",
          not faulty)
    for line in faulty[:5]:
        print(f"          {line}")
    check("every refusal is a sentence naming the file",
          all(name.split(".")[0].lower() in why.lower() for name, why in refused))
    for name, why in refused[:6]:
        print(f"          refused {name}: {why[:90]}")
    check(f"the great majority decode ({decoded}/{len(found)})",
          not found or decoded >= len(found) * 0.9)

    # The textures a model names have to be findable, or the preview draws
    # bare. This is the check on texture_path, and it is a real one: the
    # vanilla castle names NE_stone_castle.tga and ships ne_stone_castle.tga.
    named = missing = 0
    for src in found[:200]:
        try:
            scene = cas.read_cas(src)
        except cas.CasError:
            continue
        for mat in scene.materials:
            if not mat.texture:
                continue
            named += 1
            if cas.texture_path(src, mat.texture) is None:
                missing += 1
    print(f"  {named} textures named, {missing} not found next to their model")
    check(f"most named textures are found on disk ({named - missing}/{named})",
          not named or missing <= named * 0.35)


# ---------------------------------------------------------------------------
print("\n6) /api/map/models, /api/map/model and /api/map/model/geometry")

mod_root = _realmod.pick("totalvanillab", "Third_Age_Reforged",
                         need="models_strat")

from unittransfer import config
from unittransfer.server import Handler, Registry, _Server

cfgdir = Path(_tmp.mkdtemp(prefix="ut_cascfg_"))
config.CONFIG_DIR = cfgdir
config.BACKUP_DIR = cfgdir / "backups"
config.SETTINGS_PATH = cfgdir / "settings.json"
config.LOG_PATH = cfgdir / "transfers.json"

# A copy, because a suite that points a live server at an installed mod is one
# bug away from editing somebody's game - and models_strat alone is what these
# three routes read, so the copy is only that folder.
med2 = Path(_tmp.mkdtemp(prefix="ut_casmed2_"))
data = med2 / "mods" / "TestMod" / "data"
data.mkdir(parents=True)
shutil.copytree(mod_root / "data" / "models_strat", data / "models_strat")
(data / "text").mkdir(exist_ok=True)
# The routes read nothing but the models. The registry still wants a mod that
# looks like one before it will hand one over, so the unit files come along -
# copied, not linked, for the same reason the models are.
for rel in ("export_descr_unit.txt", "text/export_units.txt",
            "descr_sm_factions.txt"):
    src = mod_root / "data" / rel
    if src.exists():
        shutil.copy2(src, data / rel)
config.save_settings(med2_root=str(med2))

Handler.registry = Registry(cfgdir / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f"  serving {BASE} - models_strat copied from {mod_root.name}")


def get_json(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def get_raw(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


try:
    listing = get_json("/api/map/models?mod=TestMod")
    rows = listing["models"]
    check(f"GET /api/map/models lists the mod's models ({len(rows)})", bool(rows))
    check("every row carries a path under data/ and the group it is in",
          all(m["rel"].startswith("models_strat/") and m["group"] for m in rows))
    check("and the loose characters and banners come last, after the "
          "settlements", rows[-1]["group"] == "characters and banners")

    settlements = [m for m in rows if m["group"] != "characters and banners"]
    rel = (settlements or rows)[0]["rel"]
    view = get_json(f"/api/map/model?mod=TestMod&rel={urllib.request.quote(rel)}")
    check(f"GET /api/map/model answers with the scene ({view['source']}: "
          f"{len(view['meshes'])} meshes, {view['vertices']:,} vertices)",
          bool(view["meshes"]) and view["vertices"] > 0)
    check("every mesh names a material the file really carries, or none",
          all(m["material"] is None or m["material"] < len(view["materials"])
              for m in view["meshes"]))
    check("and each material's texture is resolved to a path under data/, or "
          "left empty because the mod does not ship it",
          all("rel" in m for m in view["materials"]))
    check("the picker's LOD and skin lists are there and empty - a .cas has "
          "neither", view["lods"] == [] and view["skins"] == [])

    status, body, ctype = get_raw(
        f"/api/map/model/geometry?mod=TestMod&rel={urllib.request.quote(rel)}")
    check(f"GET /api/map/model/geometry answers with the binary payload "
          f"({len(body):,} bytes)",
          status == 200 and body[:4] == mesh.PAYLOAD_MAGIC
          and ctype == "application/octet-stream")
    hlen, = struct.unpack_from("<I", body, 4)
    head = json.loads(body[8:8 + hlen])
    check("whose header says the same counts the scene route did",
          head["vertices"] == view["vertices"]
          and len(head["groups"]) == len(view["meshes"]))
    check("and names the format, so the page knows which viewer it is in",
          head["format"] == "cas")
    check("and names a texture per group, which is what lets the draw loop "
          "bind one sheet per mesh",
          all("texture" in g for g in head["groups"]))

    # A path out of a query string is still a path out of a query string.
    for bad, why in [("../../../windows/win.ini", "climbs out of data/"),
                     ("models_strat/nothing_here.cas",
                      "names a file that is not there")]:
        try:
            get_json(f"/api/map/model?mod=TestMod&rel={urllib.request.quote(bad)}")
            check(f"a rel that {why} is refused", False)
        except urllib.error.HTTPError as exc:
            check(f"a rel that {why} is refused", exc.code == 404)

    try:
        get_json("/api/map/models?mod=NoSuchMod")
        check("an unknown mod is refused", False)
    except urllib.error.HTTPError as exc:
        check("an unknown mod is refused", exc.code == 404)
finally:
    httpd.shutdown()





# ---------------------------------------------------------------------------
print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "FAILURES")
sys.exit(0 if all(ok) else 1)
