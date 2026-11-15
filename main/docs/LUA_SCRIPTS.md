# Lua scripts

A Lua script reads a mod and changes it through the toolkit's own editors,
run from the command line. It is a batch edit written as a program: "give
every English infantry unit two more morale", "copy this battle model under
twenty new names". It is not a script the game runs (that is M2TWEOP's).

```
python lua_cli.py run my_script.lua --mod Divide_and_Conquer_EUR
python lua_cli.py run my_script.lua --mod "C:/.../mods/My_Mod" --set faction=england --apply
python lua_cli.py undo 20261115-101500-ab12cd
python lua_cli.py api
python lua_cli.py annotations my_scripts/
```

`--mod` is a mod folder (one with a `data/` folder in it) or the name of a
mod in the game's `mods` folder that the toolkit is set up with.

## Preview first, then apply

A run without `--apply` is a **preview**. The script's edits are made one by
one, every touched file is compared with what it was, and then everything
is undone. The report lists each file that would change, with a count of
lines (`--diff` prints them all). When the preview ends every file is back,
byte for byte, and checked, and the Log holds nothing from it. The mod's files
are written while the preview runs, so do not run one while the game has the
mod open.

With `--apply` the same run stays written, and the whole run is **one entry
in the Log**. Its Undo, in the app's Log or with `lua_cli.py undo <id>`, takes
every file back to what it was before the script ran.

**All or nothing.** If an edit is refused (a rename onto a name another unit
has, a unit that is not there) or the script stops with an error, every edit
it had already made is undone and nothing is written. The report says which
edit or which line.

Exit codes: 0 done, 1 the script failed, 2 an edit was refused, 3 bad
arguments.

## What a script can call

Everything is in one table, `toolkit`. `lua_cli.py api` prints the full list.

| Call | What it does |
|---|---|
| `toolkit.units()` | every unit, in file order |
| `toolkit.unit(type)` | one unit by its `type` line, or `nil` |
| `toolkit.models()` / `toolkit.model(name)` | battle_models.modeldb entries |
| `toolkit.mounts()` | each mount and its model |
| `toolkit.factions()` | every faction slot with its shown name and culture |
| `toolkit.buildings()` / `toolkit.building(name)` | building lines, their levels, values, capabilities and recruit pools |
| `toolkit.edit_building(line, level, changes)` | a level's settlement, `requires`, values (`scalars`), upgrades or capability lines |
| `toolkit.edit_unit(type, fields, options)` | change EDU fields; `options` can rename the unit, change its dictionary, or its shown name and descriptions |
| `toolkit.clone_unit(source, type, options)` | a new unit copied from another in the same mod; `options` gives its dictionary and shown name |
| `toolkit.delete_unit(type, options)` | delete a unit and the lines elsewhere that name it |
| `toolkit.edit_model(name, changes)` | the entry as text, a new name, or a texture for every faction |
| `toolkit.clone_model(source, name)` | a new entry copied from another |
| `toolkit.mercenaries(campaign)` | a campaign's mercenary pools and their unit lines (default `imperial_campaign`) |
| `toolkit.edit_merc_unit(pool, place, edits, campaign)` | change one unit line, named by its place from 1; `false` takes an option off |
| `toolkit.add_merc_unit(pool, values, campaign)` / `toolkit.delete_merc_unit(pool, place, campaign)` | add a unit line at the end, or take one out |
| `toolkit.traits()` / `toolkit.trait(name)` | character traits and their levels and effects |
| `toolkit.edit_trait(name, changes)` | a trait's header, or its levels by place: `{ levels = { [2] = { threshold = 5 } } }` |
| `toolkit.ancillaries()` / `toolkit.ancillary(name)` / `toolkit.edit_ancillary(name, changes)` | ancillaries, read and changed; `effects`, when given, replace its effect lines |
| `toolkit.strings(file)` / `toolkit.string(file, tag)` | a `data/text` .strings.bin archive's entries (`file` is `expanded`, `expanded.txt` or the whole name) |
| `toolkit.edit_strings(file, changes)` | `{ TAG = "new text", OLD_TAG = false }`: change, add or take out entries; an archive with no tags (battle, shared, strat, tooltips) is keyed by place from 1 |
| `toolkit.settlements(campaign)` / `toolkit.edit_settlement(region, changes, campaign)` | descr_strat.txt's settlements: values, the whole buildings list, or `owner` and `place` to give it to another faction |
| `toolkit.strat_objects(campaign)` | every fort, watchtower and resource with its tile |
| `toolkit.edit_strat_object(kind, x, y, changes, campaign)` / `toolkit.add_strat_object(kind, values, campaign)` | change, move (`x`, `y`, `region`), delete (`delete = true`) or add one; the tile is checked against the map |
| `toolkit.clone_faction(source, new, options)` | the Factions screen's clone; `options` gives its shown name (`label`) and `art = false` copies no pictures |
| `toolkit.triggers(file)` | the triggers of `traits` or `ancillaries` |
| `toolkit.edit_trigger(file, name, changes)` / `toolkit.add_trigger(file, trigger)` / `toolkit.delete_trigger(file, name)` | change, add or take out a trigger; `changes.raw` is the whole block as text |
| `toolkit.recruits()` / `toolkit.edit_recruit(line, changes)` | the recruitment sheet's rows (every recruit_pool line) and their four numbers |
| `toolkit.mod` | `name` and `root` of the mod |
| `args` | the `--set key=value` values, as text |

A unit has its parsed fields (`type`, `dictionary`, `name`, `category`,
`ownership`, `soldier`, `stat_pri`...) and `fields`, every field line as text,
keyed the way the Unit Editor's fields are (`officer#2` for a second officer
line). `toolkit.edit_unit` takes the same keys: a value is text, a number or a
list (joined with `", "`), and `false` removes the field.

What a script reads is a read-only copy. Change the mod through the
`toolkit.edit_*` calls; a read after an edit sees it.

A building level's capability lines are changed by listing operations, each
naming a line from a read by its `line`; lines not listed stay as they are:

```lua
local b = toolkit.building("barracks")
local lv = b.blocks[1]
toolkit.edit_building(b.name, lv.name, { capabilities = {
  { line = lv.capabilities[1].line, delete = true },                       -- take one out
  { line = lv.capabilities[2].line, args = '"Peasants"  1  0.5  4  0' },   -- change one
  { keyword = "recruit_pool", args = '"Militia"  1  0.5  2  0',            -- add one
    requires = "factions { england, }" },
} })
```

An edit moves the EDB's line numbers, so read the building again before the
next edit to it. The same goes for `toolkit.recruits()` rows after an edit
that adds or takes out a line.

A unit's stats are the unit sheet's columns, so a script changes them with
`toolkit.edit_unit`; the recruitment sheet's numbers with
`toolkit.edit_recruit`.

## What a script cannot do

Scripts run in a sandbox, so a script from a forum post cannot harm your
machine: there is no `io`, no `os` beyond `os.time`, `os.clock` and
`os.date`, no `debug`, no `load` or `dofile`, and no binary modules.
`require "lib.util"` reads `lib/util.lua` from the script's own folder and
nowhere else. A run stops after 60 seconds (`--time-limit` to change it) or
256 MB of memory. The time counts the edits too: on Divide and Conquer's 952
units an edit takes about 0.15 s, so a script that changes more than a few
hundred units needs a longer `--time-limit`.

## From the app

With *Opt into beta features* ticked in Settings, the Scripts screen has a
**Lua** tab: write or open a script (your saved ones, or the examples), give
it arguments one `key=value` a line, then **Dry run** or **Apply**. The editor
highlights Lua, and typing `toolkit.` (or Ctrl+Space) lists what a script
can call. It is the
same run as `lua_cli.py`'s, with the same report, and an applied run is one
entry in the Log. Scripts saved there live in the toolkit's
`config/lua_scripts` folder.

The Lua is 5.4.

## Completion in VS Code

`python lua_cli.py annotations my_scripts/` writes `toolkit.lua` and a
`.luarc.json` into that folder. Open the folder in VS Code with the Lua
extension (sumneko.lua) and `toolkit.` completes, with each call's
parameters and what it returns.

## Examples

In `docs/lua_examples/`:

* `raise_morale.lua`: one faction's infantry get more morale
  (`--set faction=england --set by=2`)
* `units_without_names.lua`: units with no shown name (reads only)
* `clone_entry.lua`: a modeldb entry copied under a new name
  (`--set from=<entry> --set name=<new entry>`)
