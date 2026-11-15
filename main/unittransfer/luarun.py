"""Run a modder's Lua script in a sandbox (Phase 120, major VI).

A script is a program from somebody else's forum post, so it gets a Lua 5.4
state of its own (``lupa``), built fresh for every run, and nothing in it can
reach the disk, the network or Python:

* **The library is trimmed.** The script's environment holds the base
  functions that only work on values (``pairs``, ``type``, ``pcall``...),
  ``string`` without ``string.dump``, ``table``, ``math``, ``utf8``,
  ``coroutine`` and ``os.time`` / ``os.clock`` / ``os.date``. No ``io``, no
  ``os.execute``, no ``debug``, no ``load``, ``loadfile`` or ``dofile``, no
  ``collectgarbage``, and lupa's ``python`` bridge is never registered.
* **``require`` stays in the script's folder.** ``require "a.b"`` reads
  ``<folder>/a/b.lua`` as text (never bytecode) into the same environment; a
  name that climbs out of the folder is refused.
* **Python objects never cross.** What the toolkit hands a script is copied
  into Lua tables and frozen (:func:`Session.to_lua`); the only Python
  objects a script can touch are the functions the toolkit registers, and
  every attribute lookup on any Python object is refused, so
  ``f.__globals__`` and friends are dead ends.
* **Limits.** A memory cap (``lupa``'s allocator) and a time limit (a count
  hook, set on every coroutine too, that raises on every instruction once the
  deadline passes, so a ``pcall`` loop cannot swallow it). A hook only runs
  between Lua instructions: one call into C that runs long by itself (a
  pathological ``string.find`` pattern) finishes before it is stopped.

Errors come back as :class:`ScriptError` with the script's own file and line,
never as a Python traceback.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from . import i18n as _i18n

try:  # the runtime is optional until a script is run
    import lupa.lua54 as _lua
except ImportError:  # pragma: no cover - reported by available()
    _lua = None

#: Defaults: generous for a batch edit over a large mod, small enough that a
#: runaway script stops in seconds rather than hanging the CLI.
TIME_LIMIT = 60.0
MEMORY_LIMIT = 256 * 1024 * 1024
#: Instructions between two looks at the clock.
HOOK_EVERY = 10_000


def available() -> bool:
    return _lua is not None


@dataclass
class ScriptError(Exception):
    """A script failed: the message is the script's, with its file and line."""
    message: str
    traceback: str = ""
    kind: str = "error"  # error | syntax | time | memory | require

    def __str__(self) -> str:
        return self.message


@dataclass
class Result:
    printed: List[str] = field(default_factory=list)
    value: Any = None
    seconds: float = 0.0


def _deny_attributes(obj, name, is_setting):
    raise AttributeError(_i18n.msg("eng.luarun.a_script_cannot_reach_into_python", "a script cannot reach into Python objects"))


# The trusted setup, run once per state with the full library still present.
# It builds the script's environment and returns the helpers Python needs.
# Nothing here is reachable from the script except what `env` is given.
_SETUP = r"""
local host_print, host_read, deadline_now, time_limit = ...
local debug, string, table, math, utf8, coroutine, os = debug, string, table, math, utf8, coroutine, os
local setmetatable, getmetatable, rawget, rawset, rawequal, rawlen = setmetatable, getmetatable, rawget, rawset, rawequal, rawlen
local pairs, ipairs, next, type, tostring, tonumber, select, error, assert, pcall, xpcall, load =
      pairs, ipairs, next, type, tostring, tonumber, select, error, assert, pcall, xpcall, load

local function copy(t)
  local c = {}
  for k, v in pairs(t) do c[k] = v end
  return c
end

local env = {
  assert = assert, error = error, ipairs = ipairs, next = next, pairs = pairs,
  pcall = pcall, select = select, tonumber = tonumber, tostring = tostring,
  type = type, xpcall = xpcall, rawequal = rawequal, rawlen = rawlen,
  rawget = rawget, rawset = rawset, setmetatable = setmetatable,
  getmetatable = getmetatable, _VERSION = _VERSION,
  string = copy(string), table = copy(table), math = copy(math),
  utf8 = copy(utf8), coroutine = copy(coroutine),
  os = { time = os.time, clock = os.clock, date = os.date },
}
env.string.dump = nil
env._G = env
-- ("x"):upper() reads the string metatable: point it at the trimmed copy
getmetatable("").__index = env.string

local function tostr_all(...)
  local n, out = select("#", ...), {}
  for i = 1, n do out[i] = tostring((select(i, ...))) end
  return table.concat(out, "\t")
end
env.print = function(...) host_print(tostr_all(...)) end

-- read-only views: a frozen table answers reads, #, pairs and ipairs, and
-- refuses every write with the same sentence
local READONLY = "this table is the mod as read; change it through toolkit.edit_* functions"
local behind = setmetatable({}, { __mode = "k" })   -- frozen view -> its data
local function freeze(t)
  if type(t) ~= "table" or getmetatable(t) ~= nil then return t end
  for k, v in next, t do
    if type(v) == "table" then t[k] = freeze(v) end
  end
  local view = {}
  behind[view] = t
  return setmetatable(view, {
    __index = t,
    __newindex = function() error(READONLY, 2) end,
    __len = function() return #t end,
    __pairs = function() return next, t, nil end,
    __metatable = "read-only",
  })
end
-- next (and so `next(t) == nil`, the usual "is it empty") reads through a view
env.next = function(t, k) return next(behind[t] or t, k) end

-- a deep copy through pairs, so frozen views come back to Python as data
local function thaw(v, seen)
  if type(v) ~= "table" then return v end
  seen = seen or {}
  if seen[v] then error("a table that contains itself cannot be passed back", 0) end
  seen[v] = true
  local c = {}
  for k, x in pairs(v) do c[thaw(k, seen)] = thaw(x, seen) end
  seen[v] = nil
  return c
end

-- the time limit: once the deadline is passed the hook runs on every
-- instruction and raises each time, so a pcall that swallows one error
-- meets the next on the instruction after it returns (Python decides the
-- verdict, since even the message handler is stopped)
local function hook()
  if deadline_now() then
    debug.sethook(hook, "", 1)
    error("time limit reached (" .. time_limit .. " s)", 0)
  end
end
local function unhook() debug.sethook() end

-- a hook set from Lua belongs to one thread, so every coroutine the script
-- makes gets its own
local co_create, co_resume = coroutine.create, coroutine.resume
env.coroutine.create = function(f)
  local co = co_create(f)
  debug.sethook(co, hook, "", __EVERY__)
  return co
end
env.coroutine.wrap = function(f)
  local co = env.coroutine.create(f)
  return function(...)
    local r = table.pack(co_resume(co, ...))
    if r[1] then return table.unpack(r, 2, r.n) end
    error(r[2], 0)
  end
end

local loaded = {}
env.require = function(name)
  if type(name) ~= "string" then error("require needs a module name", 2) end
  if loaded[name] ~= nil then return loaded[name] end
  local src, chunk = host_read(name)
  if not src then error(chunk, 2) end
  local fn, err = load(src, "@" .. chunk, "t", env)
  if not fn then error(err, 0) end
  local value = fn(name)
  if value == nil then value = true end
  loaded[name] = value
  return value
end

local function run(src, chunk)
  local fn, err = load(src, "@" .. chunk, "t", env)
  if not fn then return false, "syntax", err end
  debug.sethook(hook, "", __EVERY__)
  local ok, res = xpcall(fn, function(e) return {e, debug.traceback(tostring(e), 2)} end)
  debug.sethook()
  if ok then return true, "ok", res end
  if type(res) == "table" then return false, "error", res[1], res[2] end
  return false, "error", res
end

return run, env, freeze, thaw, unhook
"""


class Session:
    """One Lua state for one script run."""

    def __init__(self, folder: Optional[Path] = None, *, time_limit: float = TIME_LIMIT,
                 memory_limit: int = MEMORY_LIMIT, on_print: Optional[Callable[[str], None]] = None):
        if _lua is None:
            raise ScriptError(_i18n.msg("eng.luarun.lua_scripts_need_the_lupa_package", "Lua scripts need the lupa package (pip install lupa)"), kind="error")
        self.folder = Path(folder).resolve() if folder else None
        self.printed: List[str] = []
        self._on_print = on_print
        self._time_limit = float(time_limit)
        self._deadline = 0.0
        self.rt = _lua.LuaRuntime(register_eval=False, register_builtins=False,
                                  unpack_returned_tuples=True, max_memory=int(memory_limit),
                                  attribute_filter=_deny_attributes)
        g = self.rt.globals()
        g.python = None  # lupa's bridge table, never part of a script's world
        setup = self.rt.execute(_SETUP.replace("__EVERY__", str(HOOK_EVERY)),
                                self._print, self._read_module,
                                lambda: time.monotonic() > self._deadline,
                                int(self._time_limit) if self._time_limit == int(self._time_limit)
                                else self._time_limit)
        self._run, self.env, self._freeze, self._thaw, self._unhook = setup

    # -- things the script may call -------------------------------------
    def _print(self, line: str) -> None:
        self.printed.append(line)
        if self._on_print:
            self._on_print(line)

    def _read_module(self, name: str):
        """(source, chunk name) for ``require(name)``, or (None, why)."""
        if self.folder is None:
            return None, f"module '{name}' not found: this script has no folder to require from"
        parts = name.replace("\\", "/").split(".") if "/" not in name else name.split("/")
        if not parts or any(p in ("", "..") or ":" in p for p in parts):
            return None, f"module '{name}' is not a name inside the script's folder"
        path = self.folder.joinpath(*parts)
        if path.suffix.lower() != ".lua":
            path = path.with_name(path.name + ".lua")
        try:
            path.resolve().relative_to(self.folder)
        except ValueError:
            return None, f"module '{name}' is outside the script's folder"
        if not path.is_file():
            return None, f"module '{name}' not found (looked for {path.relative_to(self.folder).as_posix()})"
        return path.read_text(encoding="utf-8-sig"), path.relative_to(self.folder).as_posix()

    # -- values across the line ------------------------------------------
    def to_lua(self, value: Any, *, frozen: bool = True):
        """A Python value as Lua data: dicts and lists become tables (frozen
        unless asked otherwise), None inside a dict is left out."""
        raw = self._build(value)
        return self._freeze(raw) if frozen else raw

    def _build(self, value: Any):
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            return self.rt.table_from({str(k): self._build(v) for k, v in value.items() if v is not None})
        if isinstance(value, (list, tuple)):
            return self.rt.table_from([self._build(v) for v in value])
        if callable(value):
            return value
        raise TypeError(_i18n.msg("eng.luarun.cannot_hand_a_to_a_script", "cannot hand a {name__} to a script", name__=type(value).__name__))

    def from_lua(self, value: Any) -> Any:
        """Lua data back as Python: an array (keys 1..n) is a list, any other
        table a dict with string keys; functions are refused."""
        if _lua.lua_type(value) == "table":
            value = self._thaw(value)
            return self._plain(value)
        if _lua.lua_type(value) is not None:
            raise ScriptError(_i18n.msg("eng.luarun.a_script_cannot_pass_a_lua", "a script cannot pass a Lua {lua_type} to the toolkit", lua_type=_lua.lua_type(value)))
        return value

    def _plain(self, t):
        if _lua.lua_type(t) != "table":
            if _lua.lua_type(t) is not None:
                raise ScriptError(_i18n.msg("eng.luarun.a_script_cannot_pass_a_lua", "a script cannot pass a Lua {lua_type} to the toolkit", lua_type=_lua.lua_type(t)))
            return t
        items = list(t.items())
        keys = [k for k, _ in items]
        if keys and all(isinstance(k, int) and not isinstance(k, bool) for k in keys) \
                and sorted(keys) == list(range(1, len(keys) + 1)):
            return [self._plain(v) for _, v in sorted(items, key=lambda kv: kv[0])]
        if not keys:
            return {}
        return {str(k): self._plain(v) for k, v in items}

    def set_global(self, name: str, value: Any) -> None:
        self.env[name] = value

    # -- running -------------------------------------------------------------
    def run(self, source: str, chunk: str = "script.lua") -> Result:
        start = time.monotonic()
        self._deadline = start + self._time_limit
        out, failure = None, None
        try:
            out = self._run(source, chunk)
        except _lua.LuaMemoryError:
            failure = ScriptError(_i18n.msg("eng.luarun.the_script_ran_out_of_memory", "the script ran out of memory ({x} MB limit)", x=self.rt.get_max_memory() // (1024 * 1024)), kind="memory")
        except _lua.LuaError as e:
            failure = ScriptError(str(e))
        finally:
            timed_out = time.monotonic() > self._deadline
            self._deadline = float("inf")
            self._unhook()
        if timed_out:
            raise ScriptError(_i18n.msg("eng.luarun.time_limit_reached_time_limit_g", "time limit reached ({time_limit:g} s)", time_limit=self._time_limit), kind="time")
        if failure:
            raise failure
        ok, kind, value = out[0], out[1], out[2]
        tb = out[3] if len(out) > 3 else ""
        if not ok:
            msg = str(value)
            if "not enough memory" in msg:
                kind, msg = "memory", "the script ran out of memory"
            raise ScriptError(msg, str(tb or ""), kind)
        return Result(printed=list(self.printed), value=value, seconds=time.monotonic() - start)


def run_file(path: Path, globals_: Optional[Dict[str, Any]] = None, **kw) -> Result:
    """Run one script file in a fresh session; ``globals_`` are set first."""
    path = Path(path)
    s = Session(path.parent, **kw)
    for k, v in (globals_ or {}).items():
        s.set_global(k, v)
    return s.run(path.read_text(encoding="utf-8-sig"), path.name)
