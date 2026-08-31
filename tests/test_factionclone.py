"""Cloning a faction: the nine files, against the real mods, writing nothing.

Run:  python -m tests.test_factionclone

Every cloner is measured on the mod's own bytes and the result is thrown away —
the plan is computed but never applied, so this reads the mods and leaves them
exactly as it found them.

The four things worth proving, because each one was a real bug first:

* **every cloner actually fires.** Three of the nine silently did nothing until
  the CRLF handling went in: the game files are CRLF, ``$`` sits after the
  carriage return, and a pattern ending ``[ \\t]*$`` therefore never reaches the
  end of a line. A cloner that changes nothing and reports no error is the worst
  failure this module could have, so the test asserts a non-zero count per file
  rather than merely "it did not crash".
* **the line endings survive.** The two cloners that *did* fire ate the ``\\r``
  and left the file half CRLF and half LF.
* **the clone is bounded.** ``descr_names.txt`` once cloned 10,000 lines — every
  faction from the donor to the end of the file — because the section-end
  pattern never matched. So the added line count is compared against the
  donor's own section, not just checked for being positive.
* **nothing else moves.** Removing the clone's own added lines has to give back
  the original file, character for character. That is the strongest statement
  available here and it catches any cloner that edits a line it should only
  have read.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests._realmod import pick                                    # noqa: E402
from unittransfer import factionclone as fc                        # noqa: E402
from unittransfer import factions as fa                            # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []

#: which cloner each file gets, so the test can judge it by the right rule
JOB_HOW = {j.rel: j.how for j in fc.JOBS}


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


root = pick("Third_Age_Reforged", "Divide_and_Conquer_EUR",
            need="unit_models/battle_models.modeldb")
mod = Mod(root)
print(f"=== {mod.name} ===")

roster = fa.parse_file(fa.path_for(mod))
slots = [fa.slot_of(r.name) for r in roster.records]
# a donor the mod really leans on, so the counts are worth reading
DONOR = next((s for s in ("sicily", "milan", "england", "france") if s in slots),
             next(s for s in slots if s != "slave"))
NEW = "tk_clone_probe"
check(f"picked a donor that is in the roster ({DONOR})", DONOR in slots)
check(f"the probe name is not already taken ({NEW})", NEW not in slots)


# ---------------------------------------------------------------------------
# the plan over the real mod

plan = fc.plan(mod, {"source": DONOR, "new": NEW})
check("the plan has no errors", not plan.errors)
check("the plan would write something", plan.touched())

written = {e.rel: e for e in plan.written()}
print(f"  {len(written)} file(s) planned, "
      f"{sum(a.files for a in plan.assets)} art file(s)")

# the roster is the one file that is not optional
check("the roster is always written", fa.REL in written)

for edit in plan.edits:
    if edit.skipped and "no such file" in edit.skipped:
        print(f"  [--] {edit.rel}: not in this mod")
        continue
    check(f"{edit.rel}: cloned {edit.count} time(s), not silently zero",
          edit.count > 0 and bool(edit.text))


# ---------------------------------------------------------------------------
# line endings, and that nothing but the clone moved

for rel, edit in written.items():
    path = Path(mod.data) / rel
    before = kb.read_text(path, edit.encoding)
    after = edit.text
    if rel.endswith(".modeldb"):
        # rebuilt by its own writer; the line-ending rules below do not apply
        check(f"{rel}: grew rather than shrank", len(after) > len(before))
        continue
    want = kb.newline_of(before)
    other = "\n" if want == "\r\n" else "\r\n"
    # count the endings the file did NOT use before, and after
    was = before.count(other) - (before.count("\r\n") if other == "\n" else 0)
    now = after.count(other) - (after.count("\r\n") if other == "\n" else 0)
    check(f"{rel}: no line ending changed kind ({was} odd ones before, {now} after)",
          now <= was)

    # Two shapes of clone, and they have to be judged differently.
    #
    # Most files gain WHOLE LINES and no existing line may move — take the new
    # ones out and the original comes back exactly.
    #
    # `ownership` and `descr_character`'s `faction` are the exception by design:
    # the block underneath is shared by everyone named on the line, so the clone
    # JOINS the line. There the rule is that every rewritten line is the old one
    # with nothing but the clone appended — no faction dropped, none reordered.
    import difflib
    b, a = before.split(want), after.split(want)
    ops = difflib.SequenceMatcher(None, b, a, autojunk=False).get_opcodes()
    how = JOB_HOW.get(rel)
    joins = how in ("list", "braced_list")
    lost = [o for o in ops if o[0] == "delete"]
    edited = [o for o in ops if o[0] == "replace"]
    if how == "braced_list":
        # `requires factions { sicily, }` gains the clone INSIDE the braces, so
        # the test is the reverse operation: take the clone back out and the line
        # has to be the one that was there, character for character. That also
        # pins the trailing-comma style, which the two real files disagree on.
        bad = []
        for _, i1, i2, j1, j2 in edited:
            for old, mew in zip(b[i1:i2], a[j1:j2]):
                if not any(mew.replace(form, "", 1) == old
                           for form in (", " + NEW, " " + NEW + ",")):
                    bad.append(old)
        check(f"{rel}: {sum(o[2] - o[1] for o in edited)} clause(s) joined, each "
              f"the old line with `{NEW}` slipped into the braces",
              not lost and not bad and edited)
        continue
    if not joins:
        kept = [ln for tag, i1, i2, _, _ in ops if tag == "equal" for ln in b[i1:i2]]
        check(f"{rel}: only added lines — nothing removed or rewritten "
              f"({len(a) - len(b)} added)", not lost and not edited and kept == b)
        continue
    bad = []
    for _, i1, i2, j1, j2 in edited:
        for old, mew in zip(b[i1:i2], a[j1:j2]):
            # drop the keyword before reading the list, or the first faction
            # comes back as "ownership         sicily"
            value = mew.split(";")[0].split(None, 1)[1]
            names = [t.strip().lower() for t in value.split(",")]
            # the cloner's own rule: the tight `a,b` form only when the line
            # itself demonstrates it, since a one-name line has no style to copy
            value_before = old.split(";")[0].split(None, 1)[1]
            sep = "," if ("," in value_before and ", " not in value_before) else ", "
            if mew != old.rstrip() + sep + NEW \
                    or names[-1] != NEW or DONOR not in names:
                bad.append(old)
    check(f"{rel}: {sum(o[2] - o[1] for o in edited)} line(s) joined, each the "
          f"old line plus `{NEW}` and nothing else", not lost and not bad)


# ---------------------------------------------------------------------------
# the clone is bounded: descr_names copies one section, not the rest of the file

names_rel = "descr_names.txt"
if names_rel in written:
    path = Path(mod.data) / names_rel
    text = kb.to_newline(kb.read_text(path, fc.ENCODING), "\n")
    after = kb.to_newline(written[names_rel].text, "\n")
    grew = len(after.splitlines()) - len(text.splitlines())
    head = f"faction: {DONOR}"
    if head in text:
        own = text.split(head, 1)[1].split("faction:")[0].count("\n")
        check(f"{names_rel}: added {grew} lines, which is the donor's own "
              f"section ({own}) and not the rest of the file", abs(grew - own) <= 2)


# ---------------------------------------------------------------------------
# the modeldb stays parseable, and the clone really got skins

if "unit_models/battle_models.modeldb" in written:
    from unittransfer import modeldb as mdb
    db = mdb.parse_text(written["unit_models/battle_models.modeldb"].text)
    have = [e for e in db.entries
            if any(t.faction.lower() == NEW for t in e.main_textures)]
    donor = [e for e in db.entries
             if any(t.faction.lower() == DONOR for t in e.main_textures)]
    check(f"the modeldb still parses after the clone ({len(db.entries)} entries)",
          len(db.entries) > 100)
    check(f"the clone has a skin in every entry the donor does "
          f"({len(have)} vs {len(donor)})", len(have) == len(donor) and have)
    # and the skin it got is the donor's, not whichever record came first
    same = 0
    for e in have:
        by = {t.faction.lower(): t for t in e.main_textures}
        if by[NEW].texture == by[DONOR].texture:
            same += 1
    check(f"every cloned skin points at the donor's own texture ({same}/{len(have)})",
          same == len(have))


# ---------------------------------------------------------------------------
# the text keys: the whole EMT_ family, not just the bare name

exp_rel = "text/expanded.txt"
if exp_rel in written:
    added = written[exp_rel].count
    check(f"{exp_rel}: cloned the whole key family, not just the name "
          f"({added} keys)", added > 5)
    body = written[exp_rel].text
    check(f"{exp_rel}: the faction's own name key is there",
          "{" + NEW.upper() + "}" in body)
    check(f"{exp_rel}: an EMT_ key came with it",
          f"EMT_{NEW.upper()}_" in body)


# ---------------------------------------------------------------------------
# what it refuses, which is as much of the contract as what it writes

for body, why in (
        ({"source": DONOR, "new": DONOR}, "cloning onto itself"),
        ({"source": DONOR, "new": slots[0]}, "a name already in the roster"),
        ({"source": DONOR, "new": "Not A Slot"}, "spaces and capitals"),
        ({"source": DONOR, "new": "9lives"}, "starting with a digit"),
        ({"source": DONOR, "new": ""}, "an empty name"),
        ({"source": "no_such_faction", "new": NEW}, "a donor that does not exist")):
    p = fc.plan(mod, body)
    check(f"refuses {why}", bool(p.errors) and not p.touched())

# the donor's slot must never be confused with a longer one containing it
check("a slot is matched whole, so `sicily` never matches `sicily_clone`",
      fc.clone_list_lines("ownership sicily_clone\n", "sicily", "x", "ownership")[1] == 0)
check("...but it IS matched inside a text key, where `_` separates words",
      fc.clone_expanded("{EMT_SICILY_SPY}\tSpy\n", "sicily", "x")[1] == 1)

# a re-run must not double anything
again = fc.plan(mod, {"source": DONOR, "new": NEW})
check("planning twice gives the same answer (nothing is stateful)",
      [e.count for e in again.edits] == [e.count for e in plan.edits])

check("the campaign gap is reported rather than guessed at",
      any("descr_strat" in n for n in plan.notes))

# The EDB clauses are what let a faction build and recruit, so a clone that
# misses them is a faction that can do neither — worth its own check rather than
# being one row among twelve.
edb = written.get("export_descr_buildings.txt")
if edb:
    check(f"the clone joined the donor's `requires factions` clauses "
          f"({edb.count})", edb.count > 0)
    check("and every one of them still names the donor too",
          edb.text.count("{ " + DONOR + ", " + NEW) + edb.text.count(DONOR + ", " + NEW)
          >= edb.count)

# What is NOT cloned has to be named, or it is a silent gap rather than a
# reported one — the whole difference this module claims to make.
check(f"the files that name the donor as a judgement are listed "
      f"({len(plan.review)})",
      all(set(r) == {"rel", "hits"} and r["hits"] > 0 for r in plan.review))
check("none of them is a file the cloner also writes",
      not ({r["rel"] for r in plan.review} & set(written)))
if plan.review:
    # The division of labour: `review` carries the files, a note explains why
    # they are left out. The note must NOT re-list them — the dialog draws both
    # and saying it twice reads as noise.
    check("a note explains why they are left out",
          any("decision rather than a list" in n for n in plan.notes))
    check("...without re-listing what `review` already carries",
          not any(r["rel"] in n for n in plan.notes for r in plan.review))

# the review scan is cached, so the dialog re-planning on every keystroke does
# not re-read a dozen multi-megabyte files each time
first = fc.review_mentions(mod, DONOR)
check("the review scan is cached rather than repeated",
      fc.review_mentions(mod, DONOR) is first)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
