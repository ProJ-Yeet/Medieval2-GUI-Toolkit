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

**Which files.** The executables name two effect files in their own bytes,
``descr_effects.txt`` and ``descr_oil_effect.txt``; every other one loads
because that manifest lists it. The index read four fixed files, and 11 of
ROCSS's projectile effect sets and 21 of DaC's live in the other fourteen, so a
transfer blanked them as missing. Checked here: the list the engine loads, a
listed file the mod leaves to the base game (read from the install when it is
on disk, reported unread when it is packed), a ROCSS unit into a copy of DaC
keeping its real sets, an import refused where it would create a file that
replaces the base game's, and a name nothing can check said apart.

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
ROC = MODS / "ROCSS"

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
for mod_root in (TATR, ROC, DAC):
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


# ------------------------------------------------- the files the engine loads ----
print("\n== which effect files: the manifest, the base game, the fallback ==")
inst = Path(_tmp.mkdtemp(prefix="ut_effinst_"))
mdata, bdata = inst / "mods" / "M" / "data", inst / "data"
mdata.mkdir(parents=True)
bdata.mkdir(parents=True)
SET = "effect_set {n}\n{{\n\tlod 1000\n\t{{\n\t\tsome_effect\n\t}}\n}}\n"
(mdata / "descr_effects.txt").write_text("; listed\na.txt\nb.txt\nc.txt ; comment\n", encoding="latin-1")
(mdata / "a.txt").write_text(SET.format(n="in_the_mod"), encoding="latin-1")
(bdata / "b.txt").write_text(SET.format(n="in_the_base_game"), encoding="latin-1")
(mdata / "not_listed.txt").write_text(SET.format(n="never_loaded"), encoding="latin-1")
(mdata / "descr_oil_effect.txt").write_text(SET.format(n="oil_set"), encoding="latin-1")
f = effects.effect_files(mdata)
check("the mod's manifest is the list, and descr_oil_effect.txt is always loaded",
      f.source == "mod" and f.listed == ["a.txt", "b.txt", "c.txt", "descr_oil_effect.txt"])
check("a listed file the mod ships is its own; one it does not is read from the install",
      f.shipped == ["a.txt", "descr_oil_effect.txt"] and f.from_base == ["b.txt"])
check("a listed file neither has on disk is unread, not empty", f.unread == ["c.txt"])
got = projectiles.effect_sets(mdata)
check("the sets are the mod's, the base game's for what it leaves, and the oil file's",
      got == {"in_the_mod", "in_the_base_game", "oil_set"})
check("a file the manifest does not list is never read", "never_loaded" not in got)
check("the index and the name list agree", set(effects.index(mdata).sets) == got)
(mdata / "descr_effects.txt").unlink()
(bdata / "descr_effects.txt").write_text("b.txt\n", encoding="latin-1")
f = effects.effect_files(mdata)
check("no manifest in the mod: the base game's is the list",
      f.source == "base" and f.listed == ["b.txt", "descr_oil_effect.txt"])
(bdata / "descr_effects.txt").unlink()
f = effects.effect_files(mdata)
check("no manifest anywhere: the four files this read before, and nothing called unread",
      f.source == "default" and f.listed[:4] == list(effects.FILES) and not f.unread)
lone = Path(_tmp.mkdtemp(prefix="ut_efflone_")) / "data"
lone.mkdir()
check("a mod that is not under an install's mods folder has no base game to read",
      effects.base_data(lone) is None)


def old_four(data):
    out = set()
    for rel in effects.FILES:
        if (data / rel).is_file():
            out |= {b.name.lower() for b in effects.parse_file(data / rel, rel) if b.kind == effects.SET}
    return out


def copy_mod(src_root, drop=()):
    """A copy of a mod holding what a transfer reads and writes: the EDU, its
    text, the modeldb, the projectiles, the manifest and every effect file it
    ships."""
    root = Path(_tmp.mkdtemp(prefix="ut_effmod_"))
    data = root / "data"
    rels = ["export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
            "descr_projectile.txt", effects.MANIFEST]
    rels += [r for r, _p in effects.effect_files(src_root / "data").paths]
    for rel in rels:
        srcp = src_root / "data" / rel
        if srcp.is_file() and rel not in drop:
            (data / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(srcp, data / rel)
    return root


def first_case(src, want):
    """The first (unit, projectile, set) of ``src`` that ``want(projectile
    name, set)`` accepts."""
    for u in src.edu.units:
        for pn in u.projectiles():
            sp = src.projectile_def(pn)
            if not sp:
                continue
            for v in sp.effects.values():
                if v and want(pn, v):
                    return u.type, pn, v
    return None


if ROC.is_dir() and DAC.is_dir():
    print("\n== the installed mods ==")
    for root, n_sets, n_unread, n_found in ((ROC, 344, 8, 11), (DAC, 218, 7, 21)):
        data = root / "data"
        i = effects.index(data)
        f = i.files
        old = old_four(data)
        pf = projectiles.parse_file(data / "descr_projectile.txt")
        found = {v.lower() for p in pf.projectiles for v in p.effects.values()
                 if v and v.lower() in i.sets and v.lower() not in old}
        check(f"{root.name}: its own 18-file manifest plus the oil file, {n_unread} of them left "
              f"to the base game (packed here, so unread)",
              f.source == "mod" and len(f.listed) == 19 and len(f.unread) == n_unread and not f.from_base)
        check(f"{root.name}: {n_sets} sets, where the four files held {len(old)}", len(i.sets) == n_sets)
        check(f"{root.name}: the {n_found} projectile effect sets outside the four are found",
              len(found) == n_found)

    print("\n== ROCSS into a copy of DaC: real sets are no longer blanked ==")
    roc = Mod(ROC)
    dest = Mod(copy_mod(DAC))
    dold = old_four(dest.data)
    have = {n.lower() for n in dest.projectile_file.by_name()}
    case = first_case(roc, lambda pn, v: pn.lower() not in have and v.lower() in dest.effect_sets
                      and v.lower() not in dold)
    check("a ROCSS missile unit names a set DaC declares outside the four files", case)
    if case:
        plan = plan_transfer(roc, case[0], dest, TransferOptions())
        raw = next(r for r in plan.projectile_raws
                   if projectiles.parse_text(r).projectiles[0].name.lower() == case[1].lower())
        kept = projectiles.parse_text(raw).projectiles[0].effects
        want = {k: v for k, v in roc.projectile_def(case[1]).effects.items()
                if v and v.lower() in dest.effect_sets and v.lower() not in dold}
        check(f"{case[0]} ({case[1]}): {', '.join(sorted(set(want.values())))} kept, not "
              "pointed at the placeholder", all(kept.get(k) == v for k, v in want.items()))

    print("\n== M2EX: never create a file that replaces the base game's ==")
    dac = Mod(DAC)
    sidx = dac.effect_index
    FLAME = "descr_flaming_projectiles.txt"
    rocn = {n.lower() for n in roc.projectile_file.by_name()}
    case = first_case(dac, lambda pn, v: pn.lower() not in rocn and v.lower() not in roc.effect_sets
                      and any(b.rel == FLAME for b in sidx.set_of(v)))
    check(f"a DaC unit names a set of {FLAME} that ROCSS lacks", case)
    if case:
        droot = copy_mod(ROC, drop=(FLAME,))
        modflags.set_m2ex(Mod(droot), True)
        dest = Mod(droot)
        check(f"the copy of ROCSS leaves {FLAME} to the base game",
              dest.m2ex and FLAME in dest.effect_index.files.unread)
        plan = plan_transfer(dac, case[0], dest, TransferOptions())
        acts = {n.lower(): (a, d) for n, a, d in plan.effect_actions}
        check(f"{case[2]} is not imported: the destination leaves the file to the base game",
              acts.get(case[2].lower(), ("", ""))[0] == "blocked"
              and "base game" in acts[case[2].lower()][1])
        check("...and no block is queued for that file", not any(rel == FLAME for rel, _ in plan.effect_blocks))
        rec = apply_transfer(plan)
        check(f"...and the transfer does not create {FLAME}", not (droot / "data" / FLAME).exists())
        undo(rec["id"])
        man = droot / "data" / effects.MANIFEST
        man.write_text("".join(ln for ln in man.read_text(encoding="latin-1").splitlines(True)
                               if FLAME not in ln), encoding="latin-1")
        shutil.copy2(DAC / "data" / FLAME, droot / "data" / FLAME)
        plan = plan_transfer(dac, case[0], Mod(droot), TransferOptions())
        acts = {n.lower(): (a, d) for n, a, d in plan.effect_actions}
        check("a file the destination ships and its manifest does not list is refused too",
              acts.get(case[2].lower(), ("", ""))[0] == "blocked"
              and "does not load" in acts[case[2].lower()][1])

    print("\n== a name nothing can check is said apart ==")
    src_root, dst_root = copy_mod(ROC), copy_mod(DAC)
    s_idx, d_idx = effects.index(src_root / "data"), effects.index(dst_root / "data")
    dn = {n.lower() for n in Mod(dst_root).projectile_file.by_name()}
    case = first_case(roc, lambda pn, v: pn.lower() not in dn and s_idx.set_of(v) and d_idx.set_of(v))
    check("a ROCSS projectile names a set both mods declare", case)
    if case:
        # take the set out of both copies, so neither mod's readable files have it
        for root, idx in ((src_root, s_idx), (dst_root, d_idx)):
            for rel in {b.rel for b in idx.set_of(case[2])}:
                path = root / "data" / rel
                text = kb.read_text(path, effects.ENCODING)
                for b in idx.set_of(case[2]):
                    if b.rel == rel:
                        text = text.replace(b.raw, "")
                kb.write_text(path, text, effects.ENCODING)
        src2, dest = Mod(src_root), Mod(dst_root)
        check(f"{case[2]} is gone from both copies", case[2].lower() not in dest.effect_sets
              and case[2].lower() not in src2.effect_sets)
        plan = plan_transfer(src2, case[0], dest, TransferOptions())
        warn = [w for w in plan.warnings if w.startswith("UNCHECKED EFFECTS")]
        check(f"{case[0]}: {case[2]} is blanked, and named as one that may be in a file the "
              "destination leaves to the base game",
              plan.projectile_effects_blanked > 0 and len(warn) == 1 and case[2] in warn[0]
              and "descr_surface_fire.txt" in warn[0])
        plan = plan_transfer(roc, case[0], Mod(copy_mod(DAC)), TransferOptions())
        check("a set the source declares is not called unchecked",
              not any(w.startswith("UNCHECKED EFFECTS") for w in plan.warnings))

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
