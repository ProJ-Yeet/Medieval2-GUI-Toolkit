"""Phase 74: a settlement model brought in and put on a culture's level.

    python -m tests.test_settlemodel

Divide and Conquer's dwarf village and dwarven fort, onto the northern
European culture of a copy of ROCSS's descr_cultures.txt and residences.

1. The lists: ROCSS's cultures with each model line, DaC's settlement models.
2. A model from another mod: it and every texture it names, relative to it;
   the packer's empty .tga stub with its .tga.dds; one line of the culture file
   changed and its settlement plan kept; a plan writes nothing.
3. Applied and undone, byte for byte.
4. Nothing written over: a texture already there with other bytes sends the
   set to a folder of its own; with the same bytes it is used as it is.
5. A fort line (the tail shape), a model from disk, a texture the files lack.
6. Refusals: a culture, a line, a file that is not a model, the same model.
7. The routes.
"""
import base64
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import cas, config, minorfiles, settlemodel as sm, transfer  # noqa: E402
from unittransfer.keyblock import read_text  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


roc, dac = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
VILLAGE = "models_strat/residences/dwarf_t1_village.CAS"
FORT = "models_strat/residences/forts/fort_dwarven.CAS"
if not ((roc / "data" / minorfiles.CULTURES_REL).is_file()
        and (dac / "data" / VILLAGE).is_file()):
    print("SKIPPED - needs ROCSS's descr_cultures.txt and DaC's dwarf village")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

med2 = Path(_tmp.mkdtemp(prefix="ut_smod_"))
data = med2 / "mods" / "ModelInto" / "data"
(data / sm.RESIDENCES / "textures").mkdir(parents=True)
shutil.copy2(roc / "data" / minorfiles.CULTURES_REL, data / minorfiles.CULTURES_REL)
for n in ("northern_european_village.CAS",):
    if (roc / "data" / sm.RESIDENCES / n).is_file():
        shutil.copy2(roc / "data" / sm.RESIDENCES / n, data / sm.RESIDENCES / n)
D = Mod(data.parent)
S = Mod(dac)


def snapshot():
    return {p.relative_to(data).as_posix(): p.read_bytes()
            for p in data.rglob("*") if p.is_file()}


print("1) the lists")
v = sm.view(D)
ne = next((c for c in v["cultures"] if c["culture"] == "northern_european"), None)
check("ROCSS's northern_european culture is listed with its village line",
      ne and any(t["target"] == "village" for t in ne["targets"]))
check("and its fort line, in the tail shape",
      ne and any(t["target"] == "fort" and t.get("tail") for t in ne["targets"]))
check("a model on disk is said to be",
      ne and next(t for t in ne["targets"] if t["target"] == "village")["on_disk"])
srcs = sm.sources(S)
check(f"DaC ships {len(srcs)} settlement models, the dwarf village among them",
      any(m["rel"].lower() == VILLAGE.lower() for m in srcs))

print("\n2) a model from another mod")
before = snapshot()
body = {"from": S.name, "model": VILLAGE, "culture": "northern_european", "target": "village"}
p = sm.plan(D, S, body)
check(f"it plans ({'; '.join(p.errors)})", not p.errors and p.payload()["ok"])
check("and a plan writes nothing", snapshot() == before)
scene = cas.read_cas(dac / "data" / VILLAGE)
names = {m.texture for m in scene.materials if m.texture}
check(f"all {len(names)} textures it names are found",
      names and all(t["found"] for t in p.textures))
rels = [r for _, r in p.writes]
check("each lands beside the model as the model names it",
      all(any(r.lower().startswith((sm.RESIDENCES + "/" + t.replace("\\", "/")).lower())
              for r in rels) for t in names))
check("with the packer's empty stub alongside its .tga.dds",
      any(r.lower().endswith(".tga") and b == b"" for b, r in p.writes)
      == any((dac / "data" / sm.RESIDENCES / t.replace("\\", "/")).is_file()
             and (dac / "data" / sm.RESIDENCES / t.replace("\\", "/")).stat().st_size == 0
             for t in names))
old = read_text(data / minorfiles.CULTURES_REL, minorfiles.ENCODING).splitlines()
new = p.text.splitlines()
diff = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
check("one line of descr_cultures.txt changes", len(old) == len(new) and len(diff) == 1)
cf = minorfiles.parse_cultures(p.text)
lvl = cf.get("northern_european").level("village")
was = minorfiles.parse_cultures("\n".join(old)).get("northern_european").level("village")
check("it names the new model and keeps its settlement plan",
      lvl.model == "data/" + p.rel and lvl.plan == was.plan)

print("\n3) applied, and undone")
res = sm.apply(p)
check("the model and its textures are there, the source's own bytes",
      all((data / r).read_bytes() == b for b, r in p.writes))
check("the culture file is what was planned",
      read_text(data / minorfiles.CULTURES_REL, minorfiles.ENCODING) == p.text)
transfer.undo(res["id"])
check("one Undo puts every file back byte for byte", snapshot() == before)

print("\n4) nothing written over")
tex = next(r for b, r in p.writes if r.lower().endswith(".dds"))
(data / tex).parent.mkdir(parents=True, exist_ok=True)
(data / tex).write_bytes(b"someone else's texture")
q = sm.plan(D, S, body)
check("a texture of the same name with other bytes sends it to a folder of its own",
      not q.errors and q.rel.lower().startswith(f"{sm.RESIDENCES}/{S.name}".lower())
      and any("folder" in w for w in q.warnings))
same = next(b for b, r in p.writes if r == tex)
(data / tex).write_bytes(same)
q = sm.plan(D, S, body)
check("with the same bytes it is used as it is",
      not q.errors and tex in q.same and tex not in [r for _, r in q.writes])
(data / tex).unlink()

print("\n5) a fort, a model from disk, a missing texture")
f = sm.plan(D, S, {"from": S.name, "model": FORT, "culture": "northern_european",
                   "target": "fort"})
cf = minorfiles.parse_cultures(f.text) if f.text else None
wasf = minorfiles.parse_cultures("\n".join(old)).get("northern_european").values["fort"]
check("the fort line takes the model and keeps what follows its comma",
      not f.errors and cf and sm._model_of(cf.get("northern_european").values["fort"])
      == ("data/" + f.rel, sm._model_of(wasf)[1]))
files = [{"name": Path(VILLAGE).name,
          "data": base64.b64encode((dac / "data" / VILLAGE).read_bytes()).decode()}]
for t in names:
    hit = cas.texture_path(dac / "data" / VILLAGE, t)
    files.append({"name": hit.name, "data": base64.b64encode(hit.read_bytes()).decode()})
d = sm.plan(D, None, {"from": "disk", "files": files, "culture": "northern_european",
                      "target": "town"})
check("a model from disk plans, its textures matched by name",
      not d.errors and all(t["found"] for t in d.textures)
      and d.rel.startswith(sm.RESIDENCES + "/"))
d = sm.plan(D, None, {"from": "disk", "files": files[:1], "culture": "northern_european",
                      "target": "town"})
check("without its textures it is said, and still plans",
      not d.errors and any("texture" in w for w in d.warnings))

print("\n6) refusals")
for label, b in (("a culture the file lacks", dict(body, culture="martian")),
                 ("a line that names no model", dict(body, target="portrait_mapping")),
                 ("a file that is not a model", dict(body, model="descr_cultures.txt")),
                 ("a model that is not there", dict(body, model="models_strat/nope.cas"))):
    check(f"{label} is refused", bool(sm.plan(D, S, b).errors))
res = sm.apply(sm.plan(D, S, body))
check("the same model on the same line again is refused",
      any("already names" in e for e in sm.plan(D, S, body).errors))
transfer.undo(res["id"])
check("and undone again, byte for byte", snapshot() == before)

print("\n7) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, b):
    req = urllib.request.Request(BASE + path, data=json.dumps(b).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


g = get("/api/settlemodel?mod=ModelInto")
check("GET /api/settlemodel lists the cultures",
      any(c["culture"] == "northern_european" for c in g.get("cultures", [])))
m = get("/api/settlemodel/models?mod=ModelInto")
check("GET /api/settlemodel/models answers", "models" in m)
rb = {"mod": "ModelInto", "from": "disk", "files": files, "culture": "northern_european",
      "target": "town"}
pl = post("/api/settlemodel/plan", rb)
check("POST plan works it out and writes nothing",
      pl.get("plan", {}).get("ok") and snapshot() == before)
res = post("/api/settlemodel/apply", rb)
check("POST apply writes it", res.get("id") and not res.get("error")
      and (data / res["rel"]).is_file())
transfer.undo(res["id"])
check("and the Undo takes it back", snapshot() == before)
bad = post("/api/settlemodel/plan", dict(rb, **{"from": "ModelInto"}))
check("the same mod as its own source is refused", bool(bad.get("error")))
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
