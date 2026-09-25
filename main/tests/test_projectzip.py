"""Phase 71, D12: a campaign as a zip, and any data/ zip loaded back.

    python -m tests.test_projectzip

1. Both installed mods: the campaign export holds the base map, the campaign
   folder and the region names at their data/ paths with a project.json, and
   leaves out the compiled map.rwm and every side copy (ROCSS's 22, DaC's two
   zips, two .bak files and an .xcf); loaded into its own mod, every file is "the same".
2. Loading: into an empty mod every file is new; into a copy with one file
   edited, that one "replaces" with its records named and the rest are "the
   same"; a path out of data/, a map.rwm and files outside data/ are refused
   or skipped; "keep what is there" skips the replace; a stale map.rwm beside
   a loaded map file is deleted. One Undo takes the whole load back.
"""
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import campmap, config  # noqa: E402
from unittransfer import projectzip as pz  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

# Every save and undo here goes to a config of its own, never the real undo log
# and backups: a suite run beside others would race them on transfers.json. It
# starts from a copy of the real settings, so the game root and the M2EX marks
# read the same, and nothing is written back to them.
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROC, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def counts(p):
    return p.payload()["counts"]


print("\n1) the campaign export")
exported = {}
for path, name, n_side in ((ROC, "ROCSS", 22), (DAC, "DaC", 5)):
    if not (path / "data" / campmap.BASE_REL).is_dir():
        continue
    mod = Mod(path)
    raw, man = pz.export_campaign(mod, "imperial_campaign")
    exported[name] = (mod, raw, man)
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = z.namelist()
    check(f"{name}: {len(man['files'])} files at their data/ paths, with project.json and a note",
          pz.MANIFEST in names and pz.NOTE in names
          and all(n.startswith("data/") for n in names if n not in (pz.MANIFEST, pz.NOTE))
          and json.loads(z.read(pz.MANIFEST))["campaign"] == "imperial_campaign")
    check(f"{name}: the base map, the campaign folder and the region names are all in it",
          any(r.startswith(campmap.BASE_REL + "/map_regions.tga") for r in (f["rel"] for f in man["files"]))
          and any(r.endswith("imperial_campaign/descr_strat.txt") for r in (f["rel"] for f in man["files"]))
          and campmap.REGION_NAMES_REL in [f["rel"] for f in man["files"]])
    left = man["left_out"]
    sides = [x for x in left if not x["rel"].lower().endswith("map.rwm")]
    check(f"{name}: no map.rwm in it, and the {n_side} side copies left out and named",
          not any(n.lower().endswith("map.rwm") for n in names) and len(sides) == n_side)
    check(f"{name}: loaded into its own mod, every file is the same",
          counts(pz.plan_load(mod, raw)) == {"same": len(man["files"])})
if "ROCSS" in exported:
    raw_all, man_all = pz.export_campaign(exported["ROCSS"][0], "imperial_campaign", everything=True)
    check("with everything asked for, ROCSS's copies travel too",
          len(man_all["files"]) == len(exported["ROCSS"][2]["files"]) + 22)

print("\n2) loading")
if "ROCSS" not in exported:
    print("  -- ROCSS is not installed; SKIPPED")
else:
    mod, raw, man = exported["ROCSS"]
    empty = Path(_tmp.mkdtemp(prefix="ut_pz_")) / "Empty"
    (empty / "data").mkdir(parents=True)
    p = pz.plan_load(Mod(empty), raw)
    check(f"into an empty mod every file is new ({counts(p)})", counts(p) == {"new": len(man["files"])})

    # a copy of the campaign with one file edited, and a stale compiled map
    root = Path(_tmp.mkdtemp(prefix="ut_pz_")) / "Copy"
    (root / "data").mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        z.extractall(root)
    for extra in (pz.MANIFEST, pz.NOTE):
        (root / extra).unlink()
    regions = root / "data" / campmap.BASE_REL / "descr_regions.txt"
    text = regions.read_bytes()
    first = text.split(b"\n", 1)[0]
    rwm = root / "data" / campmap.BASE_REL / campmap.RWM_NAME
    rwm.write_bytes(b"stale")
    # the zip to load: the original campaign plus three things it must not write
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as src, zipfile.ZipFile(buf, "w") as out:
        for info in src.infolist():
            out.writestr(info, src.read(info))
        out.writestr("data/../outside.txt", b"x")
        out.writestr(f"data/{campmap.BASE_REL}/map.rwm", b"compiled")
        out.writestr("readme_outside_data.txt", b"x")
    loaded = buf.getvalue()
    # edit a region in the copy so loading puts the zip's version back over it
    edited = text.replace(first, first + b" ", 1) if b"\r\n" in text else text + b"\n"
    target_region = None
    from unittransfer import changesets
    for k, v in changesets.split("world/maps/base/descr_regions.txt", text.decode("latin-1")).items():
        if k != changesets.FILE_KEY and not k.startswith("(") and len(v) > 40:
            target_region = k
            edited = text.replace(v.encode("latin-1"), v.encode("latin-1").replace(b"\n", b"\n ", 1), 1)
            break
    regions.write_bytes(edited)
    cmod = Mod(root)
    before = {p_.relative_to(root).as_posix(): p_.read_bytes() for p_ in root.rglob("*") if p_.is_file()}
    p = pz.plan_load(cmod, loaded)
    c = counts(p)
    rep = [f for f in p.files if f.state == "replaces"]
    check(f"one file replaces, the rest are the same ({c})",
          c.get("replaces") == 1 and c.get("same") == len(man["files"]) - 1 and rep[0].rel.endswith("descr_regions.txt"))
    check(f"the replaced file names the record that differs ({rep[0].records[:2]})",
          target_region is not None and any(target_region in r for r in rep[0].records))
    check("a path out of data/ is refused, a map.rwm skipped, a file outside data/ ignored",
          any(f.state == "refused" and "outside" in f.rel for f in p.files)
          and any(f.state == "skipped" and f.rel.endswith("map.rwm") for f in p.files)
          and p.ignored == ["readme_outside_data.txt"])
    check("the stale map.rwm beside the loaded descr_regions.txt is to be deleted",
          f"{campmap.BASE_REL}/{campmap.RWM_NAME}" in p.stale)
    keep = pz.plan_load(cmod, loaded, replace=False)
    check("told to keep what is there, nothing is left to load", keep.errors and not keep.writes())
    res = pz.apply_load(p)
    check("the load puts the zip's descr_regions.txt back, and the stale map.rwm is gone",
          regions.read_bytes() == text and not rwm.exists())
    transfer.undo(res["id"])
    after = {p_.relative_to(root).as_posix(): p_.read_bytes() for p_ in root.rglob("*") if p_.is_file()}
    check("one undo puts the edited file and the map.rwm back, byte for byte", after == before)
    bad = pz.plan_load(cmod, b"not a zip at all")
    check("something that is not a zip is refused", bad.errors and "not a zip" in bad.errors[0])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
