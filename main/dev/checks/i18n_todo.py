"""One language at a time (Phase 88d): what is left to translate, and the steps
that add to a catalogue without ever offering a half-done one.

    python dev/checks/i18n_todo.py de                      # missing / stale / extra, by namespace
    python dev/checks/i18n_todo.py de --batch [NS ...] [--max N] [--out FILE]
                                                           # the next strings to translate, as JSON
    python dev/checks/i18n_todo.py de --merge FILE         # add a translated batch, checked first
    python dev/checks/i18n_todo.py de --promote            # the whole catalogue checked, then offered

Where things live:

* ``dev/i18n/<tag>.json`` is the catalogue while it is being written. ``dev/``
  never ships and the server never reads it, so a language that is half done
  is not in the picker and not in a release zip.
* ``web/i18n/<tag>.json`` is the catalogue once ``--promote`` has found it
  whole and clean. From then on a merge writes there directly: a string still
  missing shows in English, one a later phase reworded keeps its old wording
  until it is redone, and nothing breaks either way.
* ``dev/i18n/<tag>.source.json`` keeps, per ID, a hash of the English each
  translation was made from, so a string reworded in en.json since shows here
  as *stale*. It stays out of the shipped catalogue, which the page loads whole.

A batch file is ``{"lang", "strings": {id: English}, "terms": {...}}``; the
answer handed to ``--merge`` is ``{id: translation}``, with an optional
``_exempt`` map as the checker reads it. Each string is held to the termbase
checker on its own; those that fail are reported and left out, the rest merged.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n_termbase as tbc  # noqa: E402

ROOT = tbc.ROOT
I18N = tbc.I18N
WORK = ROOT / "dev" / "i18n"


def namespace(k: str) -> str:
    parts = k.split(".")
    return ".".join(parts[:2]) if parts[0] == "eng" else parts[0]


def fingerprint(v) -> str:
    return hashlib.sha1(json.dumps(v, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _write(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def english() -> dict:
    en = _read(I18N / "en.json")
    en.pop("_meta", None)
    return en


def target(tag: str) -> Path:
    """The catalogue a merge writes to: the live one once promoted, else the work one."""
    live = I18N / f"{tag}.json"
    return live if live.is_file() else WORK / f"{tag}.json"


def state(tag: str) -> Dict[str, List[str]]:
    en = english()
    cat = _read(target(tag))
    src = _read(WORK / f"{tag}.source.json")
    out: Dict[str, List[str]] = {"missing": [], "stale": [], "extra": [], "done": []}
    for k, v in en.items():
        if k not in cat:
            out["missing"].append(k)
        elif src.get(k) != fingerprint(v):
            out["stale"].append(k)
        else:
            out["done"].append(k)
    out["extra"] = [k for k in cat if k not in en and not k.startswith("_")]
    return out


def report(tag: str) -> int:
    st = state(tag)
    en = english()
    rows: Dict[str, Dict[str, int]] = {}
    for k in en:
        rows.setdefault(namespace(k), {"total": 0, "missing": 0, "stale": 0})["total"] += 1
    for kind in ("missing", "stale"):
        for k in st[kind]:
            rows[namespace(k)][kind] += 1
    words = sum(len(" ".join(tbc.forms_of(en[k]).values()).split()) for k in st["missing"] + st["stale"])
    print(f"{tag}: {len(st['done'])} of {len(en)} done, {len(st['missing'])} missing, "
          f"{len(st['stale'])} stale, {len(st['extra'])} extra; about {words:,} English words left")
    print(f"catalogue: {target(tag).relative_to(ROOT).as_posix()}")
    todo = [(ns, r) for ns, r in rows.items() if r["missing"] or r["stale"]]
    for ns, r in sorted(todo, key=lambda x: x[0]):
        print(f"  {ns:24} {r['missing']:5} missing {r['stale']:4} stale  of {r['total']}")
    for k in st["extra"][:20]:
        print(f"  extra: {k}")
    return 0


def batch(tag: str, spaces: List[str], limit: int, out: Optional[Path]) -> int:
    en = english()
    st = state(tag)
    pend = set(st["missing"]) | set(st["stale"])
    order = [k for k in en if k in pend]
    if spaces:
        order = [k for k in order if namespace(k) in spaces]
    else:
        # whole namespaces, in en.json's order, until the limit is reached
        picked, seen = [], []
        for k in order:
            ns = namespace(k)
            if ns not in seen:
                if seen and len(picked) >= limit:
                    break
                seen.append(ns)
            picked.append(k)
        order = picked
    order = order[:limit] if spaces else order
    tb = tbc.load()
    cterms = tbc.compile_terms(tb)
    terms: Dict[str, dict] = {}
    cur = _read(target(tag))
    strings, old = {}, {}
    for k in order:
        strings[k] = en[k]
        if k in cur:
            old[k] = cur[k]
        base = en[k] if isinstance(en[k], str) else en[k].get("other", "")
        for t in tbc.terms_in(base, cterms):
            r = (t.get("tr") or {}).get(tag)
            if r:
                terms[t["en"]] = {"use": r["t"], "stem": r["stem"], "means": t["gloss"]}
    doc = {"lang": tag, "plural_forms": list(tbc.CLDR.get(tag, ())), "strings": strings, "terms": terms}
    if old:
        doc["previous"] = old
    out = out or WORK / f"{tag}.batch.json"
    _write(out, doc)
    print(f"{len(strings)} strings from {len({namespace(k) for k in strings})} namespaces "
          f"({', '.join(sorted({namespace(k) for k in strings}))}) -> {out}")
    return 0


def merge(tag: str, path: Path) -> int:
    en = english()
    got = _read(path)
    exempt = got.pop("_exempt", {}) or {}
    got = {k: v for k, v in got.items() if not k.startswith("_")}
    tb = tbc.load()
    bad: Dict[str, List[str]] = {}
    ok = {}
    for k, v in got.items():
        if k not in en:
            bad[k] = ["not an ID in en.json"]
            continue
        cat = {k: v}
        if k in exempt:
            cat["_exempt"] = {k: exempt[k]}
        p = tbc.check_catalogue({k: en[k]}, cat, tb, tag)
        if p:
            bad[k] = p
        else:
            ok[k] = v
    tgt = target(tag)
    cat = _read(tgt) or {"_meta": {"lang": tag, "status": "draft"}}
    cat.update(ok)
    if exempt:
        ex = cat.setdefault("_exempt", {})
        ex.update({k: v for k, v in exempt.items() if k in ok})
    src = _read(WORK / f"{tag}.source.json")
    src.update({k: fingerprint(en[k]) for k in ok})
    _write(tgt, cat)
    _write(WORK / f"{tag}.source.json", dict(sorted(src.items())))
    print(f"merged {len(ok)} into {tgt.relative_to(ROOT).as_posix()}; {len(bad)} refused")
    for k, ps in bad.items():
        for p in ps:
            print("  ", p if p.startswith(k) else f"{k}: {p}")
    return 1 if bad else 0


def promote(tag: str) -> int:
    work = WORK / f"{tag}.json"
    live = I18N / f"{tag}.json"
    if not work.is_file():
        print(f"nothing to promote: {work.relative_to(ROOT).as_posix()} does not exist"
              + (" (already live)" if live.is_file() else ""))
        return 1
    cat = _read(work)
    full = _read(I18N / "en.json")
    problems = tbc.check_catalogue(full, cat, tbc.load(), tag)
    st = state(tag)
    if st["stale"]:
        problems += [f"{k}: stale (the English changed since)" for k in st["stale"]]
    if problems:
        print(f"{tag}: {len(problems)} problems, not promoted")
        for p in problems[:40]:
            print("  ", p)
        return 1
    meta = cat.pop("_meta", {}) or {}
    meta.update({"lang": tag, "status": meta.get("status") or "draft"})
    exempt = cat.pop("_exempt", None)
    out = {"_meta": meta}
    if exempt:
        out["_exempt"] = exempt
    out.update({k: cat[k] for k in full if k in cat})
    _write(live, out)
    work.unlink()
    print(f"{tag}: promoted to {live.relative_to(ROOT).as_posix()} ({len(out) - 1 - bool(exempt)} strings)")
    return 0


def main(argv: List[str]) -> int:
    # a refusal quotes the translation, which a cp1252 console cannot print
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    tag, rest = argv[0], argv[1:]
    if tag not in tbc.CLDR or tag == "en":
        print(f"{tag!r} is not one of the target languages")
        return 2
    if "--merge" in rest:
        return merge(tag, Path(rest[rest.index("--merge") + 1]))
    if "--promote" in rest:
        return promote(tag)
    if "--batch" in rest:
        limit, out, spaces = 200, None, []
        it = iter(rest)
        for a in it:
            if a == "--max":
                limit = int(next(it))
            elif a == "--out":
                out = Path(next(it))
            elif not a.startswith("--"):
                spaces.append(a)
        return batch(tag, spaces, limit, out)
    return report(tag)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
