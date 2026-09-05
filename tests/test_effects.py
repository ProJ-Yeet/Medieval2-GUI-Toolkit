"""Effect-set import: the M2EX case where a projectile's effects travel with it.

A projectile names effect-SETS, and every transfer until now pointed those lines
at ``invisible_placeholder_set`` and told you to re-add the real thing by hand.
That is the right default - how many effects the engine will load is one of its
hardcoded tables, and what sits past the end is dropped silently - but it is not
right for a destination running on M2EX, which replaces those tables.

So the import is gated on the DESTINATION's M2EX mark, and on the source actually
declaring the set. Both halves are checked here, along with the two things about
real effect files that a naive reader gets wrong:

  * ``effect_set < 3 4 > fiery_arrow_set`` - a set declared once per graphics
    detail band. The name is the LAST token, and all of the bodies are the set.
    Reading the token straight after the keyword named seven sets "<" per stock
    mod and left the ones they really name out of the registry entirely, so a
    projectile pointing at a set the destination *did* define was blanked anyway.
  * **Braces that do not balance.** Divide and Conquer leaves an ``effect`` block
    open, and a reader that trusted its depth count swallowed the next two sets.

Needs the game install for the round-trip half; the parser half is self-contained.

    python -m tests.test_effects
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, effects, modflags, projectiles
from unittransfer import keyblock as kb
from unittransfer.mod import Mod
from unittransfer.transfer import TransferOptions, apply_transfer, plan_transfer, undo
from unittransfer.projectiles import PLACEHOLDER

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
TATR, DAC = MODS / "Third_Age_Reforged", MODS / "Divide_and_Conquer_EUR"

DEST_FILES = ("export_descr_unit.txt", "text/export_units.txt",
              "unit_models/battle_models.modeldb", "descr_projectile.txt") + effects.FILES

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_eff_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"


# ---------------------------------------------------------------- parser ----
print("== parser ==")

SAMPLE = """; a file like the real ones
effect_set plain_set
{
\tlod 1000
\t{
\t\tone_effect
\t}
}

effect one_effect
{
\ttype ribbon
\t{
\t\ttexture models_effects/textures/t.texture
\t}
}

effect_set < 3 4 > banded_set
{
\tlod 1000
\t{
\t\thigh_effect
\t}
}

effect_set < 0 1 > banded_set
{
\tlod 1000
\t{
\t\tlow_effect
\t}
}
"""

blocks = effects.parse_text(SAMPLE, "descr_effect_impacts.txt")
names = [(b.kind, b.name) for b in blocks]
check("every block found, in file order",
      names == [("effect_set", "plain_set"), ("effect", "one_effect"),
                ("effect_set", "banded_set"), ("effect_set", "banded_set")])
check("blocks are verbatim slices of the file",
      all(b.raw in SAMPLE for b in blocks))
check("a set lists its members", blocks[0].members() == ["one_effect"])
check("...and its own settings are not members", "lod" not in blocks[0].members())
check("an effect lists nothing", blocks[1].members() == [])
check("an effect's files are found",
      blocks[1].assets() == ["models_effects/textures/t.texture"])

sample_idx = effects.EffectIndex()
for b in blocks:
    if b.kind == effects.SET:
        sample_idx.sets.setdefault(b.name.lower(), []).append(b)
    else:
        sample_idx.effects.setdefault(b.name.lower(), b)
check("a detail-banded set keeps ALL of its bodies",
      len(sample_idx.set_of("banded_set")) == 2)
check("...and is named for the token after the brackets, not '<'",
      "<" not in sample_idx.sets)

# a block left open must not swallow the next one
UNBALANCED = """effect broken
{
\ttype particle
\t{
\t\ttexture a.tga
}
effect_set after_the_break
{
\tlod 1000
\t{
\t\tsomething
\t}
}
"""
after = effects.parse_text(UNBALANCED, "x.txt")
check("an unbalanced block does not swallow the block after it",
      [b.name for b in after] == ["broken", "after_the_break"])


print("\n== the two readers agree on real files ==")
for mod_root in (TATR, DAC):
    if not mod_root.is_dir():
        print(f"  (skipped, {mod_root.name} not installed)")
        continue
    data = mod_root / "data"
    i = effects.index(data)
    check(f"{mod_root.name}: index and projectiles.effect_sets name the same sets",
          set(i.sets) == projectiles.effect_sets(data))
    check(f"{mod_root.name}: no set is called '<'", "<" not in i.sets)
    for b in [x for v in i.sets.values() for x in v] + list(i.effects.values()):
        raw_ok = b.raw in kb.read_text(data / b.rel, effects.ENCODING)
        if not raw_ok:
            check(f"{mod_root.name}: {b.name} is a verbatim slice", False)
            break
    else:
        check(f"{mod_root.name}: every block is a verbatim slice of its file", True)


# ------------------------------------------------------------- resolution ----
print("\n== what travels, and what does not ==")
i = effects.EffectIndex()
for b in blocks:
    if b.kind == effects.SET:
        i.sets.setdefault(b.name.lower(), []).append(b)
    else:
        i.effects.setdefault(b.name.lower(), b)

got, missing = effects.resolve(i, ["plain_set"])
check("a set brings itself and the effects it lists",
      [b.name for b in got] == ["plain_set", "one_effect"])
check("nothing reported missing", missing == [])

got, missing = effects.resolve(i, ["banded_set"])
check("a banded set brings every body", len(got) == 2)

got, missing = effects.resolve(i, ["plain_set"], have_sets={"plain_set"})
check("a set the destination already declares is left alone", got == [])

got, missing = effects.resolve(i, ["plain_set"], have_effects={"one_effect"})
check("...and an effect it already has is not re-added",
      [b.name for b in got] == ["plain_set"])

got, missing = effects.resolve(i, ["not_in_this_mod"])
check("a set the SOURCE does not declare is reported missing, not invented",
      got == [] and missing == ["not_in_this_mod"])


# ------------------------------------------------------- the transfer gate ----
if not (TATR.is_dir() and DAC.is_dir()):
    print("\n(transfer half skipped - the mods are not installed)")
    shutil.rmtree(cfg, ignore_errors=True)
    print(f"\n{sum(ok)}/{len(ok)} checks passed")
    sys.exit(0 if all(ok) else 1)


def fresh_dest():
    root = Path(_tmp.mkdtemp(prefix="ut_effdest_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir(parents=True)
    for rel in DEST_FILES:
        srcp = DAC / "data" / rel
        if srcp.exists():
            dstp = data / rel
            dstp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(srcp, dstp)
    return root


src = Mod(TATR)
scratch = Mod(fresh_dest())
src_idx = src.effect_index

# a missile unit whose projectile names a set THIS SOURCE DECLARES and the
# destination does not - the only case the import has anything to do
UNIT = PROJ = SET_NAME = None
for u in src.edu.units:
    for pn in u.projectiles():
        sp = src.projectile_def(pn)
        if not sp or pn.lower() in {n.lower() for n in scratch.projectile_file.by_name()}:
            continue
        for v in sp.effects.values():
            if v and v.lower() not in scratch.effect_sets and src_idx.set_of(v):
                UNIT, PROJ, SET_NAME = u.type, pn, v
                break
        if UNIT:
            break
    if UNIT:
        break

if not UNIT:
    print("\n(no unit in this install exercises the import - skipped)")
else:
    print(f"\n== off by default: unit={UNIT!r} projectile={PROJ!r} set={SET_NAME!r} ==")
    dest = Mod(fresh_dest())
    plan = plan_transfer(src, UNIT, dest, TransferOptions())
    check("an ordinary destination imports no effects", not plan.effect_blocks)
    check("...and still blanks what it lacks", plan.projectile_effects_blanked > 0)
    check("...and still says so", any("NOT imported" in w for w in plan.warnings))
    check("...and points at the mark that would change it",
          any("M2EX" in w for w in plan.warnings))

    print(f"\n== on for an M2EX destination ==")
    dest = Mod(fresh_dest())
    modflags.set_m2ex(dest, True)
    dest = Mod(dest.root)                       # m2ex is a cached_property
    check("the destination is marked", dest.m2ex)

    # `None` for a file this destination does not have. It happens: the set that
    # travels here lives in descr_arrow_trail_custom_effects.txt, which Divide and
    # Conquer does not ship, so the import CREATES it - and undo has to take it
    # away again.
    before = {rel: (kb.read_text(dest.data / rel, effects.ENCODING)
                    if (dest.data / rel).exists() else None)
              for rel in effects.FILES}
    plan = plan_transfer(src, UNIT, dest, TransferOptions())
    added = {n.lower() for n, a, _ in plan.effect_actions if a == "add"}
    check("the set is imported rather than blanked", SET_NAME.lower() in added)
    check("blocks are queued for a real effect file",
          plan.effect_blocks and all(rel in effects.FILES for rel, _ in plan.effect_blocks))
    check("the import is reported as a warning, not silently",
          any("EFFECTS IMPORTED" in w for w in plan.warnings))

    rec = apply_transfer(plan)
    dest_after = Mod(dest.root)
    check("the destination now declares the set",
          SET_NAME.lower() in dest_after.effect_sets)

    idx_after = dest_after.effect_index
    members = [m for b in src_idx.set_of(SET_NAME) for m in b.members()]
    have_all = all(m.lower() in idx_after.effects or m.lower() not in src_idx.effects
                   for m in members)
    check("...and every effect that set lists, where the source had it", have_all)

    written = projectiles.parse_file(dest.data / "descr_projectile.txt").get(PROJ)
    check("the projectile's line points at the real set, not the placeholder",
          written is not None
          and any(v.lower() == SET_NAME.lower() for v in written.effects.values()))

    # The blocks are APPENDED. Whatever a file said before has to still say it,
    # byte for byte, above what was added - these files are shared by every
    # projectile in the mod, so a rewrite here is a rewrite of all of them.
    def now_of(rel):
        p = dest.data / rel
        return kb.read_text(p, effects.ENCODING) if p.exists() else None

    touched = []
    for rel in before:
        now = now_of(rel)
        if now == before[rel]:
            continue
        touched.append(rel)
        if before[rel] is None:
            check(f"{rel}: the destination did not have this file, so it was created",
                  now is not None and now.strip())
        else:
            check(f"{rel}: the mod's own text is untouched, the import sits below it",
                  now.startswith(before[rel].rstrip("\r\n")))
    check("the effect files were actually written", bool(touched))
    check("every imported asset landed in the destination",
          all((dest.data / a).exists() for a in plan.effect_assets))

    print("\n== undo ==")
    undo(rec["id"])
    check("undo restores every effect file byte-exact",
          {rel: now_of(rel) for rel in before} == before)
    check("...including deleting one the import created",
          all((dest.data / rel).exists() == (before[rel] is not None) for rel in before))

shutil.rmtree(cfg, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
