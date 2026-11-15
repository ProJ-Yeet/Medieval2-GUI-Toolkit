"""The Lua sandbox scripts run in (Phase 120).

    python -m tests.test_luarun

1. print is captured, integers stay integers, a value comes back
2. nothing that reaches the disk, the process or Python is in a script's world
3. a Python object's attributes are refused; an error raised in Python reaches
   the script as its message
4. frozen tables read, count and iterate, and refuse every write
5. Lua data comes back as lists and dicts
6. require reads only from the script's folder, as text
7. the time limit stops a plain loop, a pcall loop and a coroutine loop; the
   same session runs again afterwards
8. the memory limit stops a script that grows without end
9. a syntax error names the file and line
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import luarun  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def fails(s, code, chunk="script.lua"):
    try:
        s.run(code, chunk)
    except luarun.ScriptError as e:
        return e
    return None


if not luarun.available():
    print("lupa is not installed: pip install lupa")
    sys.exit(1)

print("1. running")
s = luarun.Session(time_limit=1)
r = s.run('print("hi", 1, 2.5, nil, true); return math.type(3)')
check("print captured with tabs", r.printed == ["hi\t1\t2.5\tnil\ttrue"])
check("Lua 5.4 integers", r.value == "integer")
check("_VERSION is 5.4", s.run("return _VERSION").value == "Lua 5.4")

print("2. the world a script sees")
for name in ["io", "os.execute", "os.remove", "os.getenv", "load", "loadfile", "dofile",
             "string.dump", '("x").dump', "debug", "python", "collectgarbage", "package"]:
    check(f"{name} is nil", s.run(f"return {name}").value is None)
check("os.time, string.format and table.concat are there",
      s.run('return type(os.time()) .. string.format("%d", 3) .. table.concat({"a","b"})').value
      == "number3ab")

print("3. Python objects")


def boom(x):
    raise ValueError("unit 'X' not found")


s.set_global("boom", boom)
e = fails(s, "return boom.__globals__")
check("attribute refused", e and "cannot reach into Python" in e.message)
e = fails(s, "return boom.__class__")
check("__class__ refused", e and "cannot reach into Python" in e.message)
e = fails(s, "boom(1)", "e.lua")
check("Python error message reaches the script", e and "unit 'X' not found" in e.message)
check("a pcall sees the same message",
      "unit 'X' not found" in s.run("local ok, e = pcall(boom, 1); return tostring(e)").value)

print("4. frozen tables")
s.set_global("t", s.to_lua({"a": 1, "b": [1, 2, {"c": "d"}], "n": None}))
check("reads, # and ipairs", s.run(
    "local m=0 for _ in ipairs(t.b) do m=m+1 end return #t.b .. m .. t.b[3].c").value == "33d")
check("pairs sees the fields, not the None", s.run(
    "local n=0 for k in pairs(t) do n=n+1 end return n").value == 2)
e = fails(s, "t.a = 2")
check("a write is refused with the sentence", e and "change it through toolkit.edit_" in e.message)
e = fails(s, "t.b[3].c = 'x'")
check("a nested write is refused", e is not None)
e = fails(s, "rawset(t, 'z', 1); return t.z")
check("rawset lands on the empty proxy, not the data",
      e is None and s.run("return t.z").value == 1 and s.run("return rawget(t, 'a')").value is None)

print("5. back to Python")
v = s.from_lua(s.run("return {x=t.b, y={1,2}, z={}, w=1.5, i=2}").value)
check("arrays to lists, tables to dicts, numbers kept",
      v == {"x": [1, 2, {"c": "d"}], "y": [1, 2], "z": {}, "w": 1.5, "i": 2}
      and isinstance(v["i"], int))
e = None
try:
    s.from_lua(s.run("return {f=print}").value)
except luarun.ScriptError as ex:
    e = ex
check("a function cannot be passed back", e is not None)

print("6. require")
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "lib").mkdir()
    (d / "lib" / "util.lua").write_text("return {twice=function(x) return 2*x end}", encoding="utf-8")
    (d / "main.lua").write_text('local u = require("lib.util"); return u.twice(21)', encoding="utf-8")
    (d.parent / "outside_ut_lua.lua").write_text("return 1", encoding="utf-8")
    try:
        check("a module in the folder", luarun.run_file(d / "main.lua").value == 42)
        s2 = luarun.Session(d)
        for bad in ['require("../outside_ut_lua")', 'require("lib/../../outside_ut_lua")',
                    'require("C:/Windows/win")', 'require("nope")']:
            e = fails(s2, bad)
            check(f"{bad} refused", e is not None)
        (d / "bin.lua").write_bytes(b"\x1bLua\x54\x00")
        e = fails(s2, 'require("bin")')
        check("bytecode refused", e is not None)
    finally:
        (d.parent / "outside_ut_lua.lua").unlink()

print("7. time")
for label, code in [("a plain loop", "while true do end"),
                    ("a pcall loop", "while true do pcall(function() while true do end end) end"),
                    ("a coroutine loop", "coroutine.wrap(function() while true do end end)()")]:
    e = fails(s, code)
    check(f"{label} stopped", e and e.kind == "time")
check("the session runs again", s.run("return 1 + 1").value == 2)

print("8. memory")
s3 = luarun.Session(memory_limit=16 * 1024 * 1024, time_limit=10)
e = fails(s3, 'local t={} for i=1,1e9 do t[i]=string.rep("x",1000)..i end')
check("stopped as memory", e and e.kind == "memory")

print("9. syntax")
e = fails(s, "x = = 1", "bad.lua")
check("syntax error with file and line", e and e.kind == "syntax" and e.message.startswith("bad.lua:1:"))

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
