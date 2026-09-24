"""Phase 75: a .cas model placed by its skeleton, not piled on the origin.

    python -m tests.test_caspose

1. The chain: a node's place is its pivots summed from the root; a parent
   table that loops is cut rather than followed.
2. Characters stand: a strat general, a diplomat and an assassin from each
   installed mod go from a pile to a figure, feet below the pelvis and the
   head above it, and every skinned model in both mods is at least 1.2 tall.
3. Settlements do not move: every static model in both mods is handed to the
   viewer byte for byte as it was before.
4. A model whose bones carry no pivots is drawn as stored and says so; given
   the skeleton .cas beside it, it is placed exactly as the original.
5. The routes: /api/map/model says which pose, and /api/map/model/geometry
   serves the placed figure, from a skeleton beside it when it needs one.
"""
import json
import shutil
import sys
import threading
import urllib.request
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import cas, config, mesh  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


print("1) the chain")
s = cas.CasScene(source="chain.cas", nodes=["Scene Root", "a", "b", "c"],
                 parents=[-1, 0, 1, 1],
                 pivots=array("f", [0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3]))
w = cas.bind_world(s)
check("each node is its pivots summed from the root",
      w == [(0, 0, 0), (1, 0, 0), (1, 2, 0), (1, 0, 3)])
loop = cas.CasScene(source="loop.cas", nodes=["r", "x", "y"], parents=[-1, 2, 1],
                    pivots=array("f", [0, 0, 0, 1, 0, 0, 0, 1, 0]))
check("a parent table that loops is cut, not followed", len(cas.bind_world(loop)) == 3)
o = cas.CasObject(name="o", skinned=True, positions=array("f", [0, 0, 0, 1, 1, 1]),
                  bones=array("I", [2, 3]))
check("a skinned vertex moves by its own bone",
      list(cas.posed_positions(o, w)) == [1, 2, 0, 2, 1, 4])
st = cas.CasObject(name="s", positions=array("f", [5, 5, 5]))
check("a static object is left as it is", cas.posed_positions(st, w) is st.positions)

installed = [m for m in ("ROCSS", "Divide_and_Conquer_EUR")
             if (MODS / m / "data" / cas.STRAT_MODELS).is_dir()]
if not installed:
    print("SKIPPED - no mod with loose strat models is installed")
    sys.exit(0)


def extent(a: array, k: int) -> float:
    v = a[k::3]
    return max(v) - min(v) if v else 0.0


print("\n2) characters stand")
WANT = {"ROCSS": ("assassin", "diplomat", "general"),
        "Divide_and_Conquer_EUR": ("assassin", "diplomat", "general")}
for m in installed:
    folder = MODS / m / "data" / cas.STRAT_MODELS
    loose = sorted(folder.glob("*.cas"))
    for kind in WANT[m]:
        f = next((p for p in loose if kind in p.stem.lower()), None)
        if f is None:
            check(f"{m}: a {kind} model is installed", False)
            continue
        sc = cas.read_cas(f)
        raw = cas.as_mesh(sc, pose=False).positions
        put = cas.as_mesh(sc).positions
        world = cas.bind_world(sc)
        idx = {n.lower(): i for i, n in enumerate(sc.nodes)}
        pelvis = world[idx["bone_pelvis"]] if "bone_pelvis" in idx else (0, 0, 0)
        feet = [world[i] for n, i in idx.items() if "foot" in n]
        head = [world[i] for n, i in idx.items() if "head" in n]
        check(f"{m} {f.name}: {extent(raw, 1):.2f} of pile becomes a figure "
              f"{extent(put, 1):.2f} tall",
              extent(put, 1) > 1.4 and extent(put, 1) > extent(raw, 1) + 0.3)
        check(f"{m} {f.name}: its feet below the pelvis and its head above",
              feet and head and all(p[1] < pelvis[1] for p in feet)
              and all(p[1] > pelvis[1] for p in head))

print("\n3) settlements do not move, and no character is left a pile")
for m in installed:
    static = changed = skinned = short = 0
    for f in (MODS / m / "data" / cas.STRAT_MODELS).rglob("*.cas"):
        try:
            sc = cas.read_cas(f)
            a, b = cas.as_mesh(sc), cas.as_mesh(sc, pose=False)
        except cas.CasError:
            continue
        if cas.is_skinned(sc):
            skinned += 1
            short += extent(a.positions, 1) < 1.2
        else:
            static += 1
            changed += a.positions.tobytes() != b.positions.tobytes()
    check(f"{m}: all {static} static models are handed over exactly as before",
          static and not changed)
    check(f"{m}: all {skinned} skinned models stand at least 1.2 tall ({short} do not)",
          skinned and not short)

print("\n4) a model with no pivots, and the skeleton beside it")
m = installed[0]
src = next(p for p in sorted((MODS / m / "data" / cas.STRAT_MODELS).glob("*.cas"))
           if "assassin" in p.stem.lower())
raw = src.read_bytes()
sc = cas.read_cas_bytes(raw, str(src))
at = raw.find(sc.pivots.tobytes())
check("the pivots are found in the file, once", at > 0 and raw.count(sc.pivots.tobytes()) == 1)
flat = raw[:at] + bytes(len(sc.pivots) * 4) + raw[at + len(sc.pivots) * 4:]
zero = cas.read_cas_bytes(flat, "flat.cas")
check("the flattened copy reads with every pivot at zero",
      not cas.has_pivots(zero) and cas.is_skinned(zero))
g = cas.as_mesh(zero)
check("drawn with nothing to place it by, it is the pile, and says so",
      g.positions.tobytes() == cas.as_mesh(zero, pose=False).positions.tobytes()
      and any("origin" in n for n in g.notes))
check("given the original as its skeleton, it is placed exactly as the original",
      cas.as_mesh(zero, sc).positions.tobytes() == cas.as_mesh(sc).positions.tobytes())

med2 = Path(_tmp.mkdtemp(prefix="ut_cpose_"))
data = med2 / "mods" / "PoseMod" / "data"
home = data / cas.STRAT_MODELS
home.mkdir(parents=True)
# the strat model routes warm the mod, which reads its roster and battle models
for rel in ("export_descr_unit.txt", "unit_models/battle_models.modeldb"):
    (data / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MODS / m / "data" / rel, data / rel)
shutil.copy2(src, home / "figure.cas")
(home / "figure_flat.cas").write_bytes(flat)
got = cas.find_skeleton(home / "figure_flat.cas", zero)
check("the skeleton beside it is found by its bones", got and got[0].name == "figure.cas")
alone = med2 / "alone"
alone.mkdir()
(alone / "figure_flat.cas").write_bytes(flat)
check("with nothing beside it, none is found",
      cas.find_skeleton(alone / "figure_flat.cas", zero) is None)
town = next((p for p in (MODS / m / "data" / cas.STRAT_MODELS / "residences").glob("*.cas")
             if not cas.is_skinned(cas.read_cas(p))), None)
if town is not None:
    shutil.copy2(town, home / "town.cas")

print("\n5) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return r.read()


def drawn(payload: bytes):
    """What a payload draws: its bounds and its arrays, not the file's name."""
    import struct
    n, = struct.unpack_from("<I", payload, 4)
    head = json.loads(payload[8:8 + n])
    return head["min"], head["max"], payload[8 + n:]


rel = f"{cas.STRAT_MODELS}/figure.cas"
v = json.loads(fetch(f"/api/map/model?mod=PoseMod&rel={rel}"))
check("a character is placed by its own bones", v.get("pose") == "bones")
vf = json.loads(fetch(f"/api/map/model?mod=PoseMod&rel={cas.STRAT_MODELS}/figure_flat.cas"))
check("the flattened one by the skeleton beside it, and it says which",
      vf.get("pose") == "skeleton" and any("figure.cas" in n for n in vf.get("notes", [])))
a = fetch(f"/api/map/model/geometry?mod=PoseMod&rel={rel}")
b = fetch(f"/api/map/model/geometry?mod=PoseMod&rel={cas.STRAT_MODELS}/figure_flat.cas")
check("and both serve the same placed figure",
      drawn(a) == drawn(b) == drawn(mesh.geometry_payload(cas.as_mesh(sc))))
if town is not None:
    vt = json.loads(fetch(f"/api/map/model?mod=PoseMod&rel={cas.STRAT_MODELS}/town.cas"))
    t = fetch(f"/api/map/model/geometry?mod=PoseMod&rel={cas.STRAT_MODELS}/town.cas")
    check("a settlement is static and served as it always was",
          vt.get("pose") == "static"
          and drawn(t) == drawn(mesh.geometry_payload(
              cas.as_mesh(cas.read_cas(town), pose=False))))
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
