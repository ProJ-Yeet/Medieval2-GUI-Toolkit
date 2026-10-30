"""M2EX's text battle models - Phase 92a.

    1  the reader and the two writers against M2EX's own descr_model_battle.txt
       (701 models): text -> .modeldb form -> text is the same 701 models, and
       each .modeldb-form entry parses back to itself; a distance is squared
    2  which file a mod reads: its own descr_caps_ex.txt, `model_battle_source`
    3  a unit transferred INTO a text-model mod lands in descr_model_battle.txt
       (and no .modeldb is made), reads back through Mod.modeldb, and Undo
       takes it out
    4  a unit taken OUT of a text-model mod lands in a .modeldb mod, with its
       distances squared back

The M2EX files are the user's install (EUREXV1); the two mods are Tsardoms
3.0 and Third Age Reforged, copied to temp folders with a config of their own.

    python -m tests.test_modeltext
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from tests._realmod import MODS  # noqa: E402
from unittransfer import config  # noqa: E402
from unittransfer import keyblock as kb, modeldb as mdb, modeltext as mt  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


M2EX = Path(r"C:/Users/projy/Downloads/EUREXV1/M2EX/data")
TSAR, TATR = MODS / "Tsardoms-3.0", MODS / "Third_Age_Reforged"


def sig(e, text=False):
    return (e.name, [(m, round(d)) for m, d in e.lods],
            [((a.mount_type if not text else ""), a.primary_skeleton, a.secondary_skeleton,
              a.pri_weapons, a.sec_weapons) for a in e.animations],
            [(x.faction, x.texture, x.normal, x.sprite) for x in e.main_textures],
            [(x.faction, x.texture, x.normal) for x in e.attach_textures],
            e.torch_index, [round(x, 4) for x in e.torch], round(e.scale, 4))


print("\n1) M2EX's own file")
if not (M2EX / mt.TEXT_REL).is_file():
    print("  [skip] needs M2EX's data folder")
else:
    text = (M2EX / mt.TEXT_REL).read_text(encoding=mt.ENCODING)
    es = mt.parse(text)
    check(f"701 models read ({len(es)})", len(es) == 701)
    pony = es[0]
    check("mount_pony: scale 1.12, three meshes at 11, 35, 100, 24 textures",
          pony.scale == 1.12 and [d for _, d in pony.lods] == [11, 35, 100]
          and len(pony.main_textures) == 24 and pony.main_textures[0].sprite.endswith(".spr"))
    kn = next(e for e in es if e.name == "mailed_knights_ug1")
    check("a knight: two body skeletons, two weapons each, a torch",
          kn.animations[0].primary_skeleton == "MTW2_HR_Lance"
          and kn.animations[0].secondary_skeleton == "MTW2_HR_Sword"
          and kn.animations[0].pri_weapons == ["MTW2_HR_Lance_Primary", "fs_test_shield"]
          and kn.torch_index == 16 and kn.torch[0] == -0.09)
    mace = next(e for e in es if any(k in e.raw for k in ("skeleton_elephant",)))
    check("skeleton_horse / _elephant are mount types of their own, the first unwritten",
          [a.mount_type for a in mace.animations][:1] == [""]
          and "horse" in [a.mount_type for a in mace.animations]
          and "elephant" in [a.mount_type for a in mace.animations])

    class M: data = M2EX
    db = mt.read_db(M, mounts=lambda: {})
    check("read as a ModelDb: distances squared (11, 35, 100 -> 121, 1225, 10000)",
          [d for _, d in db.entries[0].lods] == [121, 1225, 10000])
    check("the first block of a model with others is `none`",
          db.get(mace.name).animations[0].mount_type == "none")
    same = sum(1 for e in db.entries if sig(mdb.parse_entry_text(e.raw)) == sig(e))
    check(f"every .modeldb-form entry parses back to itself ({same}/701)", same == 701)
    back = mt.parse("\r\n".join(mt.render(mt.from_modeldb(e)) for e in db.entries))
    same = sum(1 for a, b in zip(back, es) if sig(a, True) == sig(b, True))
    check(f"text -> .modeldb form -> text is the same models ({same}/701)", same == 701)
    kn2 = mt.read_db(M, mounts=lambda: {"mailed_knights_ug1": "horse"}).get("mailed_knights_ug1")
    check("a model only mounted units wear gets `horse` from them",
          kn2.animations[0].mount_type == "horse")

print("\n2) which file a mod reads")
tmp = Path(_tmp.mkdtemp(prefix="ut_mt_"))
for body, want in (("model_battle_source  text\n", True), ("model_battle_source modeldb\n", False),
                   ("; model_battle_source text\n", False), ("", False)):
    d = tmp / "caps" / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / mt.CAPS_REL).write_text(body, encoding="latin-1")

    class C: data = d
    check(f"{body.strip() or '(no line)'!r} -> {'text' if want else 'modeldb'}",
          mt.reads_text(C) == want)

print("\n2b) Health: the file the game does not read, changed after the one it does")
import os  # noqa: E402
from unittransfer import health  # noqa: E402
hd = tmp / "hmod" / "data"
(hd / "unit_models").mkdir(parents=True)
(hd / mt.CAPS_REL).write_text("model_battle_source text\n", encoding="latin-1")
(hd / mt.TEXT_REL).write_text("type\t\t\t\tx\r\n", encoding="latin-1")
(hd / "unit_models" / "battle_models.modeldb").write_text("22 serialization::archive", encoding="latin-1")


class H: data = hd


src = next(s for s in health.SOURCES if s.id == "modelsource")
t0 = (hd / mt.TEXT_REL).stat().st_mtime
os.utime(hd / "unit_models" / "battle_models.modeldb", (t0 + 60, t0 + 60))
f = src.run(H, None)
check("a text-model mod whose .modeldb is newer: warned, and the dead file named",
      len(f) == 1 and f[0].file == "unit_models/battle_models.modeldb"
      and "nothing loads" in f[0].message)
os.utime(hd / "unit_models" / "battle_models.modeldb", (t0 - 60, t0 - 60))
check("  older than the text it is not", src.run(H, None) == [])

print("\n3-4) transfers")
if not (TSAR.is_dir() and TATR.is_dir()):
    print("  [skip] needs Tsardoms-3.0 and Third_Age_Reforged")
else:
    from unittransfer.transfer import TransferOptions, apply_transfer, plan_transfer, undo
    cfg = tmp / "cfg"
    cfg.mkdir()
    config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

    def copy_mod(src: Path, name: str, text_models: bool) -> Path:
        root = tmp / name
        data = root / "data"
        (data / "text").mkdir(parents=True)
        (data / "unit_models").mkdir(parents=True)
        for rel in ("export_descr_unit.txt", "text/export_units.txt"):
            shutil.copy2(src / "data" / rel, data / rel)
        if text_models:
            db = mdb.parse_file(src / "data" / "unit_models" / "battle_models.modeldb")
            (data / mt.TEXT_REL).write_text(
                "; descr_model_battle.txt - generated for the test\r\n\r\n"
                + "\r\n".join(mt.render(mt.from_modeldb(e)) for e in db.entries),
                encoding=mt.ENCODING, newline="")
            (data / mt.CAPS_REL).write_text("model_battle_source text\r\n", encoding="latin-1")
        else:
            shutil.copy2(src / "data" / "unit_models" / "battle_models.modeldb",
                         data / "unit_models" / "battle_models.modeldb")
        return root

    ref_txt = copy_mod(TATR, "RefText", True)
    dst = Mod(ref_txt)
    check("the text-model copy of Reforged reads its models from text",
          dst.text_models and len(dst.modeldb.entries) > 100)
    src = Mod(TSAR)
    have = {e.name for e in dst.modeldb.entries}
    unit = next(u for u in src.edu.units if u.soldier_model and not u.mount
                and u.soldier_model.lower() not in have
                and src.modeldb.get(u.soldier_model) is not None)
    before = (ref_txt / "data" / mt.TEXT_REL).read_bytes()
    plan = plan_transfer(src, unit.type, dst, TransferOptions())
    names = [n for n, _e in plan.add_entries]
    rec = apply_transfer(plan)
    after = (ref_txt / "data" / mt.TEXT_REL).read_text(encoding=mt.ENCODING)
    check(f"into a text mod: {unit.type}'s models are appended to descr_model_battle.txt ({names})",
          names and all(f"type\t\t\t\t{n}" in after for n in names))
    check("  and no battle_models.modeldb is made",
          not (ref_txt / "data" / "unit_models" / "battle_models.modeldb").exists())
    back = Mod(ref_txt).modeldb.get(names[0])
    orig = src.modeldb.get(unit.soldier_model)
    check("  it reads back through Mod.modeldb, distances as they were",
          back is not None and [d for _, d in back.lods]
          == [int(round(b ** 0.5)) ** 2 for _, b in orig.lods])
    raw = (ref_txt / "data" / mt.TEXT_REL).read_bytes()
    check("  the file keeps its CRLF, every line", raw.count(b"\n") == raw.count(b"\r\n"))
    undo(rec["id"])
    check("  and Undo puts the file back byte for byte",
          (ref_txt / "data" / mt.TEXT_REL).read_bytes() == before)

    tsar_db = copy_mod(TSAR, "TsarDb", False)
    txt_src = Mod(ref_txt)
    tgt = Mod(tsar_db)
    have = {e.name for e in tgt.modeldb.entries}
    unit = next(u for u in txt_src.edu.units if u.soldier_model and not u.mount
                and u.soldier_model.lower() not in have
                and txt_src.modeldb.get(u.soldier_model) is not None)
    plan = plan_transfer(txt_src, unit.type, tgt, TransferOptions())
    names = [n for n, _e in plan.add_entries]
    apply_transfer(plan)
    got = mdb.parse_file(tsar_db / "data" / "unit_models" / "battle_models.modeldb").get(names[0])
    was = mt.parse((ref_txt / "data" / mt.TEXT_REL).read_text(encoding=mt.ENCODING))
    was = next(e for e in was if e.name == unit.soldier_model.lower())
    check(f"out of a text mod: {unit.type}'s model lands in the .modeldb ({names[0]})",
          got is not None and len(got.main_textures) == len(was.main_textures))
    check("  its distances squared back",
          [d for _, d in got.lods] == [int(round(d)) ** 2 for _, d in was.lods])

print("\n5) every editor's .modeldb write lands in the text file (redirect)")
# the shapes two EX mods' own files have: a `blank` first, comments inside and
# between entries, a name in mixed case, a name twice, mounted skeletons
TEXT5 = "\r\n".join([
    "; descr_model_battle.txt - generated from battle_models.modelDB", "",
    "type\t\t\t\tblank", "scale\t\t\t\t0", "skeleton\t\t\t, ", "mesh\t\t\t\t, 0",
    "texture\t\t\t\tall, , ", "torch\t\t\t\t0, 0, 0, 0, 0, 0, 0", "",
    "type\t\t\t\tMount_Pony", "scale\t\t\t\t1.12", "skeleton\t\t\tfs_horse, ",
    "mesh\t\t\t\tunit_models/m/pony_lod0.mesh, 11",
    "texture\t\t\t\tengland, m/t.texture, m/n.texture, unit_sprites/p.spr", "",
    "; a comment between entries", "type\t\t\t\tspearmen",
    "skeleton\t\t\tMTW2_Spear, MTW2_Sword", "skeleton_attachment_primary\tMTW2_Spear_Primary",
    "skeleton_horse\t\t\tMTW2_HR_Spear, ", "; a comment inside one",
    "mesh\t\t\t\tunit_models/u/spear_lod0.mesh, 80",
    "texture\t\t\t\tengland, u/s.texture, u/sn.texture, unit_sprites/s.spr",
    "texture_attachments\t\tengland, u/a.texture, u/an.texture",
    "torch\t\t\t\t2, 0, 0.1, 0, 0, 0, 0", "",
    "type\t\t\t\tspearmen", "skeleton\t\t\tMTW2_Spear, ", "mesh\t\t\t\tu/twice.mesh, 30",
    "texture\t\t\t\tengland, u/s.texture, u/sn.texture", ""])


class TextMod:
    text_models = True

    def __init__(self, data):
        self.data = data


d5 = tmp / "five"
d5.mkdir(parents=True, exist_ok=True)
kb.write_text(d5 / mt.TEXT_REL, TEXT5, mt.ENCODING)
tm = TextMod(d5)
db5 = mt.read_db(tm, mounts=lambda: {})
check("the text's blank is the archive's sentinel, not a model (3 models)",
      [e.name for e in db5.entries] == ["mount_pony", "spearmen", "spearmen"])
check("read as a list, it writes back as a .modeldb the reader takes",
      len(mdb.parse_text(db5.to_text()).entries) == 3)
check("a write that changes nothing gives the file back byte for byte",
      mt.text_from_modeldb(tm, db5.to_text()) == TEXT5)
e = db5.entries[1]
e.main_textures.append(mdb.Texture("wales", "u/w.texture", "u/wn.texture", "unit_sprites/w.spr"))
e.raw = mt.entry_raw(e)
db5.entries.pop(0)
new5 = mt.text_from_modeldb(tm, db5.to_text())
check("a changed entry gets the new line, and its comment-free form",
      "texture\t\t\t\twales, u/w.texture, u/wn.texture, unit_sprites/w.spr" in new5)
check("an entry dropped by the edit is gone, the untouched ones byte for byte",
      "Mount_Pony" not in new5 and "type\t\t\t\tspearmen\r\nskeleton\t\t\tMTW2_Spear, \r\nmesh\t\t\t\tu/twice.mesh, 30" in new5
      and new5.startswith("; descr_model_battle.txt") and "texture\t\t\t\tall, , " in new5)
check("the file keeps its CRLF", new5.count("\r\n") == new5.count("\n"))
db5 = mt.read_db(tm, mounts=lambda: {})
rel5, t5, enc5 = mt.redirect(tm, "unit_models/battle_models.modeldb", db5.to_text(), "latin-1")
check("redirect sends the .modeldb write to descr_model_battle.txt", rel5 == mt.TEXT_REL)
(d5 / "written.txt").write_text(t5, encoding=enc5)   # text mode, as the editors write
check("written in text mode as the editors do, the file is byte for byte as it was",
      (d5 / "written.txt").read_bytes() == TEXT5.replace("\r\n", __import__("os").linesep).encode("latin-1"))
plain = TextMod(d5)
plain.text_models = False
check("and leaves a .modeldb mod, and any other file, alone",
      mt.redirect(plain, "unit_models/battle_models.modeldb", "x", "latin-1")[0] == "unit_models/battle_models.modeldb"
      and mt.redirect(tm, "export_descr_unit.txt", "x", "latin-1")[0] == "export_descr_unit.txt")
from unittransfer import factionclone as _fc  # noqa: E402
cl, n5 = _fc.clone_text_models(kb.to_newline(TEXT5, "\n"), "england", "wales")
check(f"a faction clone copies both kinds of texture line ({n5})",
      n5 == 4 and "texture_attachments\t\twales, u/a.texture, u/an.texture" in cl
      and _fc.clone_text_models(cl, "england", "wales")[1] == 0)

print("\n6) a .modeldb mod switched to text models (modeltext.convert)")
d6 = tmp / "six"
(d6 / "unit_models").mkdir(parents=True, exist_ok=True)
db6 = mt.read_db(tm, mounts=lambda: {"mount_pony": "horse"})
db6_text = db6.to_text()
kb.write_text(d6 / "unit_models" / "battle_models.modeldb", db6_text, mdb.ENCODING)
kb.write_text(d6 / mt.CAPS_REL, "; caps\r\nvegetation_source text\r\n", mt.ENCODING)


class DbMod:
    name = "six"
    text_models = False

    def __init__(self, data):
        self.data = data
        self.root = data.parent


cfg6 = tmp / "cfg6"
cfg6.mkdir(exist_ok=True)
_was = (config.CONFIG_DIR, config.BACKUP_DIR, config.SETTINGS_PATH, config.LOG_PATH)
config.CONFIG_DIR = cfg6; config.BACKUP_DIR = cfg6 / "backups"
config.SETTINGS_PATH = cfg6 / "settings.json"; config.LOG_PATH = cfg6 / "transfers.json"
try:
    got6 = mt.convert(DbMod(d6))
    out6 = kb.read_text(d6 / mt.TEXT_REL, mt.ENCODING)
    check(f"every model of the .modeldb written, the blank left out ({got6['models']})",
          got6["models"] == 3 and [e.name for e in mt.parse(out6)] == ["mount_pony", "spearmen", "spearmen"])
    check("as M2EX's dumper writes it: its two comment lines, CRLF, distances as roots",
          out6.startswith(mt.TEXT_HEAD) and out6.count("\r\n") == out6.count("\n")
          and "mesh\t\t\t\tunit_models/m/pony_lod0.mesh, 11\r\n" in out6)
    check("a mounted model's second skeleton block is written skeleton_horse",
          "skeleton_horse\t\t\tMTW2_HR_Spear, \r\n" in out6)
    caps6 = kb.read_text(d6 / mt.CAPS_REL, mt.ENCODING)
    check("descr_caps_ex.txt gains model_battle_source text, its other lines kept",
          caps6 == "; caps\r\nvegetation_source text\r\nmodel_battle_source text\r\n" and mt.reads_text(DbMod(d6)))
    check("the .modeldb is left where it is", (d6 / "unit_models" / "battle_models.modeldb").is_file())
    check("and the record backs up the caps file and lists the text as made",
          got6["record"]["manifest"] == {"backed_up": [mt.CAPS_REL], "created": [mt.TEXT_REL]})
    check("an existing model_battle_source line is switched, not doubled",
          mt.caps_with_text("model_battle_source db ; x\r\n") == "model_battle_source text ; x\r\n")
finally:
    config.CONFIG_DIR, config.BACKUP_DIR, config.SETTINGS_PATH, config.LOG_PATH = _was

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
