"""Run a Lua script against a mod from the command line (major VI).

Usage:
  python unittransfer/lua_cli.py run <script.lua> --mod <mod folder or saved mod name> [--set key=value ...]
  python unittransfer/lua_cli.py run <script.lua> --mod ... --apply      # write it: one Log entry, one Undo
  python unittransfer/lua_cli.py run <script.lua> --mod ... --diff       # every changed line, not a summary
  python unittransfer/lua_cli.py undo <log id>                            # take a run back
  python unittransfer/lua_cli.py api                                      # what a script can call
  python unittransfer/lua_cli.py annotations <folder>                     # completion in VS Code

Without --apply a run is a preview: the script's edits are made, compared and
undone, and the report shows exactly what --apply would change.

Exit codes: 0 done, 1 the script failed, 2 an edit was refused, 3 bad arguments.

The guide, from a first script to every function: web/lua/guide.html. Examples:
web/lua/examples/.

It lives in unittransfer/ rather than beside app.py because the updater an
installed toolkit already has only accepts the top-level names it knew when it
was released; a new one there makes every update refuse the whole package.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):        # run as a file: the toolkit folder holds unittransfer
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittransfer import config, luaapi, luarun
from unittransfer.mod import Mod


def _mod(arg: str) -> Mod:
    p = Path(arg)
    if (p / "data").is_dir():
        return Mod(p)
    root = config.get_med2_root()
    if root:
        mods = Path(root) / "mods" if (Path(root) / "mods").is_dir() else Path(root)
        for child in (sorted(mods.iterdir()) if mods.is_dir() else []):
            if child.name.lower() == arg.lower() and (child / "data").is_dir():
                return Mod(child)
    raise SystemExit(f"no mod folder, and no mod in the game's mods folder, called '{arg}'")


def _set(pairs):
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--set needs key=value, got '{p}'")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


def cmd_run(a) -> int:
    script = Path(a.script)
    if not script.is_file():
        print(f"no script at {script}", file=sys.stderr)
        return 3
    mod = _mod(a.mod)
    rep = luaapi.run(mod, script, apply=a.apply, args=_set(a.set), time_limit=a.time_limit,
                     on_print=lambda line: print(line, flush=True))
    print()
    for e in rep.edits:
        print(f"  {e}")
    for w in rep.warnings:
        print(f"  ! {w}")
    if not rep.ok:
        print(f"\n{rep.script} failed ({rep.error_kind}): {rep.error}")
        print("nothing was written" + (f" (the {len(rep.edits)} edit(s) before it were undone)"
                                       if rep.edits else ""))
        return 2 if rep.error_kind == "refused" else 1
    if not rep.files:
        print(f"\n{rep.script}: no file would change" if not rep.edits
              else f"\n{rep.script}: the edits leave every file as it was")
        return 0
    print(f"\n{len(rep.files)} file(s) {'changed' if rep.applied else 'would change'}:")
    for fc in rep.files:
        counts = f"+{fc.added} -{fc.removed}" if fc.diff != "(binary file)" else "binary"
        print(f"  {fc.status:8} {fc.rel}  ({counts})")
        if a.diff and fc.diff:
            print(fc.diff)
    if rep.applied:
        print(f"\nwritten, Log entry {rep.log_id}; to take it back: python unittransfer/lua_cli.py undo {rep.log_id}")
    else:
        print("\npreview: every file is back as it was; run again with --apply to write it")
    print(f"({rep.seconds:.1f} s)")
    return 0


def cmd_undo(a) -> int:
    try:
        rec = luaapi.undo(a.id)
    except KeyError as e:
        print(str(e).strip("'\""), file=sys.stderr)
        return 3
    print(f"undone: {rec.get('id')} ({(rec.get('summary') or '').splitlines()[0]})")
    return 0


def cmd_api(a) -> int:
    print(luaapi.api_text())
    return 0


def cmd_annotations(a) -> int:
    for p in luaapi.write_annotations(Path(a.folder)):
        print(f"wrote {p}")
    print("open the folder in VS Code with the Lua extension (sumneko.lua) for completion")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="unittransfer/lua_cli.py",
                                 description="Run a Lua script against a Medieval II mod.",
                                 epilog="The guide: web/lua/guide.html. Examples: web/lua/examples/.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a script (a preview unless --apply)")
    r.add_argument("script")
    r.add_argument("--mod", required=True, help="the mod folder, or a mod saved in the toolkit")
    r.add_argument("--apply", action="store_true", help="write the changes (one Log entry)")
    r.add_argument("--diff", action="store_true", help="print every changed line")
    r.add_argument("--set", action="append", metavar="KEY=VALUE", help="a value for args.KEY")
    r.add_argument("--time-limit", type=float, default=luarun.TIME_LIMIT, help="seconds")
    u = sub.add_parser("undo", help="take a run back by its Log id")
    u.add_argument("id")
    sub.add_parser("api", help="list what a script can call")
    n = sub.add_parser("annotations", help="write toolkit.lua and .luarc.json for VS Code")
    n.add_argument("folder", help="the folder your scripts are in")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 3 if e.code else 0
    if not luarun.available():
        print("Lua scripts need the lupa package: python -m pip install lupa", file=sys.stderr)
        return 3
    return {"run": cmd_run, "undo": cmd_undo, "api": cmd_api,
            "annotations": cmd_annotations}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
