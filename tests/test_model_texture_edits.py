"""What the editor SENDS for an entry's textures, and what the file gets back.

The modeldb editor offers a texture two ways: one default box per kind ("used by
every faction unless it has its own") and a box per faction. The server writes a
faction's override in preference to the default, so which slots the browser sends
as overrides decides entirely whether editing the default box does anything.

It did not. The rule was "anything that differs from the default is an override",
compared against the default *as just typed* — so typing in the default box made
every faction differ from it by definition, and all of them were sent back pinned
to the value they already had. The new default was written and then overridden
once per faction by the old one. On screen the boxes reverted on save, while the
LOD meshes stayed, because meshes are indexed paths with no override layer. That
is the shape it was reported in: "only the meshes stay as the new one".

So this test has two halves that have to be read together:

  * the **browser** half runs `edModelEdits()` in Node against a stub entry, and
    is the one that catches this. It is where the bug was.
  * the **server** half applies the payloads that come out of it to a throwaway
    mod and reads the modeldb back, so the two halves cannot drift into agreeing
    with each other while disagreeing with the file.

Needs Node for the first half and Third_Age_Reforged for the second; each is
skipped, loudly, if it is not there.

    python -m tests.test_model_texture_edits
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import config, edit
from unittransfer.mod import Mod

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
TATR = MODS / "Third_Age_Reforged"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(tempfile.mkdtemp(prefix="ut_texedit_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"


# --------------------------------------------------------------- browser ----
# An entry shaped like a real one: three factions, two of them sharing the
# default texture and one carrying its own. That third faction is the whole
# point — it must keep what it has when the default moves, and the other two
# must follow.
DEFAULT_TEX = "unit_models/x/textures/base_diff.texture"
DEFAULT_NRM = "unit_models/x/textures/base_norm.texture"
OWN_TEX = "unit_models/x/textures/rome_diff.texture"
NEW_TEX = "unit_models/x/textures/NEW_diff.texture"
PINNED = "unit_models/x/textures/PINNED_diff.texture"

STUB_ENTRY = {
    "name": "test_entry",
    "factions": ["england", "france", "rome"],
    "texture_defaults": {"texture": DEFAULT_TEX, "normal": DEFAULT_NRM},
    "textures": {
        "england": {"texture": DEFAULT_TEX, "normal": DEFAULT_NRM},
        "france": {"texture": DEFAULT_TEX, "normal": DEFAULT_NRM},
        "rome": {"texture": OWN_TEX, "normal": DEFAULT_NRM},
    },
    "paths": [{"i": 0, "faction": "", "group": "lod", "kind": "mesh",
               "value": "unit_models/x/test.mesh"}],
    "lods": [], "slots": [], "used_by": [], "folder": {"base": "unit_models/x"},
    "attach_factions": [], "has_attach": False,
}

DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const ctx = {console, JSON, Object, Array, Math, String, Number, setTimeout,
  document: {querySelectorAll: () => [], getElementById: () => null,
             addEventListener: () => {}}};
ctx.window = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);

const entry = JSON.parse(process.argv[3]);
const cases = JSON.parse(process.argv[4]);
const out = {};
for (const [label, edits] of Object.entries(cases)) {
  ctx.state = {ed: {mod: 'm', unit: '', d: {models: [entry]}, mEdits: {},
                    newModels: [], open: {}, folder: {}, cv: null, mcv: null}};
  const me = ctx.edTouch(entry.name);
  Object.assign(me, JSON.parse(JSON.stringify(edits)));
  out[label] = ctx.edModelEdits()[0];
}
process.stdout.write(JSON.stringify(out));
"""

CASES = {
    # the reported bug: change only the default
    "default_only": {"defaults": {"texture": NEW_TEX}},
    # one faction's own box, default untouched
    "one_faction": {"faction_paths": {"france": {"texture": PINNED}}},
    # both at once
    "both": {"defaults": {"texture": NEW_TEX},
             "faction_paths": {"france": {"texture": PINNED}}},
    # nothing typed at all — opening an entry and saving must change nothing
    "untouched": {},
}

print("what the browser sends")
node = shutil.which("node")
sent = None
if not node:
    print("  (skipped — Node is not installed)")
else:
    drv = cfg / "drive.js"
    drv.write_text(DRIVER, encoding="utf-8")
    res = subprocess.run(
        [node, str(drv), str(ROOT / "web/js/editor.js"),
         json.dumps(STUB_ENTRY), json.dumps(CASES)],
        capture_output=True, text=True)
    if res.returncode != 0:
        check("the editor's payload builder runs", False)
        print(res.stderr[:600])
    else:
        sent = json.loads(res.stdout)

if sent:
    d = sent["default_only"]
    check("editing the default box sends the new default",
          d["defaults"]["texture"] == NEW_TEX)
    # THE regression. Every faction sharing the default was sent back pinned to
    # the old value, so the new default reached nobody.
    check("...and does NOT pin the factions that were sharing it",
          "england" not in d["faction_paths"] and "france" not in d["faction_paths"])
    check("...while the faction that had its own texture keeps it",
          d["faction_paths"].get("rome", {}).get("texture") == OWN_TEX)

    o = sent["one_faction"]
    check("editing one faction's box sends that faction",
          o["faction_paths"].get("france", {}).get("texture") == PINNED)
    check("...and leaves the default alone",
          o["defaults"]["texture"] == DEFAULT_TEX)
    check("...and does not invent overrides for the others",
          "england" not in o["faction_paths"])

    b = sent["both"]
    check("both at once: the default moves",
          b["defaults"]["texture"] == NEW_TEX)
    check("...the faction you pinned stays pinned",
          b["faction_paths"].get("france", {}).get("texture") == PINNED)
    check("...the faction that already differed still differs",
          b["faction_paths"].get("rome", {}).get("texture") == OWN_TEX)
    check("...and the one that was sharing the default is free to follow it",
          "england" not in b["faction_paths"])

    u = sent["untouched"]
    check("an entry nobody typed in sends its own values back unchanged",
          u["defaults"]["texture"] == DEFAULT_TEX
          and u["faction_paths"].get("rome", {}).get("texture") == OWN_TEX
          and "england" not in u["faction_paths"])


# ---------------------------------------------------------------- server ----
print("\nand what the file gets back")
if not sent:
    print("  (skipped — no payload to apply)")
elif not TATR.is_dir():
    print("  (skipped — Third_Age_Reforged is not installed)")
else:
    def fresh_mod():
        root = Path(tempfile.mkdtemp(prefix="ut_texmod_"))
        data = root / "data"
        (data / "text").mkdir(parents=True)
        (data / "unit_models").mkdir(parents=True)
        for rel in ("export_descr_unit.txt", "text/export_units.txt",
                    "unit_models/battle_models.modeldb"):
            src = TATR / "data" / rel
            if src.exists():
                shutil.copy2(src, data / rel)
        return root

    root = fresh_mod()
    mod = Mod(root)
    # a real entry with several faction records that all share one texture
    name = tex_kind = None
    for e in mod.modeldb.entries:
        vals = {t.texture for t in e.main_textures}
        if len(e.main_textures) >= 3 and len(vals) == 1 and next(iter(vals)):
            name = e.name
            break
    if not name:
        print("  (skipped — no entry in this mod shares one texture across factions)")
    else:
        facs = [t.faction for t in mod.modeldb.by_name()[name].main_textures]
        print(f"  entry {name!r}: {len(facs)} faction records, all on one texture")
        # exactly what the fixed browser sends for "I changed the default box":
        # the new default, and no faction overrides at all
        plan = edit.plan_bmdb(mod, edit.bmdb_request_from_dict({
            "mod": mod.name,
            "model_edits": [{"entry": name, "defaults": {"texture": NEW_TEX},
                             "faction_paths": {}}]}))
        check("the plan has no errors", not plan.errors)
        edit.apply_edit(plan)

        after = Mod(root).modeldb.by_name()[name]
        check("every faction record now reads the new texture",
              all(t.texture == NEW_TEX for t in after.main_textures))
        check("...all of them, not just the first",
              len(after.main_textures) == len(facs))
        check("the normal maps were not touched",
              all(t.normal for t in after.main_textures))

        # and the other half: one faction pinned, the rest following a new default
        one = facs[1]
        plan = edit.plan_bmdb(mod := Mod(root), edit.bmdb_request_from_dict({
            "mod": mod.name,
            "model_edits": [{"entry": name,
                             "defaults": {"texture": DEFAULT_TEX},
                             "faction_paths": {one: {"texture": PINNED}}}]}))
        check("the second plan has no errors", not plan.errors)
        edit.apply_edit(plan)
        after = Mod(root).modeldb.by_name()[name]
        got = {t.faction: t.texture for t in after.main_textures}
        check("the pinned faction got its own texture", got.get(one) == PINNED)
        check("every other faction got the default",
              all(v == DEFAULT_TEX for f, v in got.items() if f != one))

        shutil.rmtree(root, ignore_errors=True)

shutil.rmtree(cfg, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
