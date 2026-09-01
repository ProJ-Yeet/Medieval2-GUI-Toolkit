# Medieval 2 GUI Toolkit

Edit Medieval II: Total War mods without hand-editing text files. Move units
between mods, edit what is already there, and clean out what nothing uses.

Formerly released as "Unit Transfer".

Runs as a local web server with a UI in your browser. No game files are touched
except the mod you point it at, and every write is backed up and undoable.

Video walkthrough: <https://www.youtube.com/watch?v=NZl8gCqlTE0>

Sponsored by FeatherLeaf.

## Install

Download the latest build from [Releases](../../releases/latest), unzip it, and
run `Medieval 2 GUI Toolkit.bat`. Python and Pillow are bundled.

On first run, open Settings and point it at your Medieval II install folder (the
one containing `mods`).

## Modules

| Module | What it does |
|---|---|
| Home | Every mod it can see, with which modules can work on it and which files are missing |
| Unit Transfer | Copy a unit from one mod into another, with everything it depends on |
| Unit Editor | Change, clone or delete the units of a single mod |
| BMDB + Sprites | Edit any `battle_models.modeldb` entry, view models in 3D, and clean out what nothing references |
| Buildings | Browse and edit `export_descr_buildings.txt`, including recruitment |
| Unit Sounds | Choose which voice bank entry each unit uses |
| Sprites | Generate and wire up the far-LOD unit sprites |
| Strings | Read and write the compiled `data/text/*.txt.strings.bin` files |
| Traits / Ancillaries | Full editors for both, definitions and triggers together |
| Factions | Faction definitions, with map colours edited via a colour picker, and **Add a faction** — a new slot cloned from an existing one across all twelve files that name a faction |
| Minor Files | Rebel factions, religions, cultures, resources and character names |

## Transfers

Pick a unit in one mod and transfer it into another. The toolkit resolves what
the unit depends on and carries it across:

* the EDU entry (stats, attributes, ownership, era, cost, formation)
* the localised name and descriptions
* every battle model it uses (soldier, officers, mount, crew): meshes, textures,
  normal maps and far-LOD sprite sheets
* the mount definition, if mounted
* the projectile definition, if it is a missile unit (and its effect sets too,
  when the destination is marked M2EX — see below)
* for artillery, the full siege engine: the `descr_engines.txt` blocks, each
  model group's animation skeleton, every referenced mesh, bone map, collision
  and reference-points file, and the textures baked into those meshes
* the unit card and info card
* the voice, as a copy of another unit's entry in the destination's voice bank,
  with `accent` and `voice_type` set to match

Name collisions are detected and resolved (reuse identical content, rename, or
overwrite/skip), and every step is shown in a probe before anything is written.

Other transfer options:

* **Batch transfer.** Select several units and transfer them in one pass, each
  with its own options.
* **Use another unit as a stat base.** Port a unit's identity and models but
  inherit combat stats, cost and ownership from a unit in the destination.
* **Replace an existing unit.** Write the transferred unit's models into a
  destination unit of the same kind. No new EDU entry, no new dictionary, no new
  name, so recruitment, scripts and the campaign map are unaffected.
* **Unit packs.** Export selected units as a zip and send it to someone whose
  mod is not on your machine. A pack is a mod, so importing one is an ordinary
  transfer.

## Editing

* **Guided field editor.** An EDU line is a positional tuple with nothing
  indicating which slot is which. The guided view gives every value its own
  labelled field, with dropdowns where the engine accepts a fixed set and lists
  built from your own mod where it does not. A raw one-field-per-line view is
  available on a toggle. Validation reports what the engine will actually do:
  attack above the cap of 63, a missile weapon with no ammunition, a secondary
  missile weapon (never fired), a model nothing defines, and similar.
* **Recruitment, from the unit.** A tab in the unit editor listing every
  building line in the mod that trains it, with all four pool numbers and the
  `requires` clause editable in place — the same `recruit_pool` lines the
  Buildings module writes, saved with the unit in one pass and taken back by one
  undo. A value that disagrees with what most of the other pools use is marked,
  which is usually why you opened it. A building's name opens that line in a new
  browser tab, on the tier the pool is on, with the unit's rows flashed. **＋ Add
  a building** offers every line and every tier — the ones that already train it
  shown as such — so making a unit recruitable somewhere new never leaves the
  unit, and neither does taking it off a building.
* **Code View.** The raw game file beside the form in every editor, with
  hover-to-highlight both ways and live two-way editing. Can hide comment-only
  lines and restore them exactly.
* **3D model viewer.** Draws the `.mesh` an entry names with its faction skin
  applied, in the browser, with nothing installed. Orbit it, toggle parts off,
  and step through the head, helmet and shield variants the engine picks between
  per soldier. Docks beside the entry list or the editor.
* **Show UVs** in that viewer, for when the skin is the thing you are debugging.
  Paints the UV coordinate instead of the art, in the space the game samples:
  blue is the main sheet, amber the attachment sheet, the dark tiles are the two
  repeating, and a red line marks where the pair starts over. Thirty-two checker
  cells to a sheet, so art stretched over a part shows up as stretched cells.
* **UV layout** beside the model, the way a UV editor shows it: the texture
  sheet — both squares of it where the entry names a pair — with this model's
  islands drawn over the art they sit on, one colour per part and the same
  colour beside that part in the list. Pan, zoom, and click an island to be told
  which part wears it and which pixels of which sheet it covers. Only the parts
  actually on the soldier are drawn, so switching a variant or hiding a slot
  changes the map with it. Where `Show UVs` answers "is this shell stretched",
  this answers "where on the art does this part live" — the view a retexture is
  done against.
* **Drag the bar under the docked canvas** to trade height between the model and
  its controls; double-click for the default. The width of the whole column is
  draggable too, from the bar down its left edge.
* The unit editor's preview offers the models the unit is actually **seen** in:
  when it carries `armour_ug_models` the engine draws those, one per armour
  level, and never the model on its `soldier` line, so that one is not offered.
* **Add a faction.** Copies one that already works into all twelve files that
  name a faction slot — the roster, `expanded.txt`, unit ownership, the
  modeldb's faction skins, every `requires factions { … }` clause in the EDB
  (which is what lets it build and recruit), the voice accent, diplomatic
  standing, agents, strat models, names, populace and off-map navies — and
  copies its symbols, banners, captain cards and unit card folders under the new
  name. Shows exactly what each file would gain before writing, backs every one
  up, and undoes the whole faction in one go.

  It also names what it will **not** touch, rather than letting you find out
  later. Traits named after the faction, an ancillary's `FactionType` condition
  and prebattle speeches are judgements rather than lists, so they are counted
  and reported. So is the campaign start position: two factions cannot begin in
  the same settlement, so there is nothing there to copy that would still be
  right.
* **Replace any picture.** Right-click any image for Replace image and Open file
  location. Warns when resolutions differ, converts `.png` to the `.tga` the
  engine reads, and copies a unit card into every faction folder that holds one.
* **Port a trait or ancillary from another installed mod**, bringing the block,
  its triggers and its text keys together.
* **Ctrl+Z / Ctrl+Y** in every editor, one value at a time.

## Cleanup

* **Clean up BMDB.** Finds battle model entries nothing references and files
  under `unit_models` no entry names, and moves them out of the mod into a
  folder mirroring its layout. References are checked against the EDU, mounts,
  characters, every campaign and battle script in the mod, every `.lua` script
  (M2TWEOP mods reference models by name from Lua), and every `data/descr_*.txt`.
  The last two are deliberately cautious: a false "still used" costs nothing, a
  false "unused" breaks a mod.
* **Recheck past cleanups.** Re-reads the cleanup log and re-tests what earlier
  runs removed against the current reference checks, then restores anything that
  should not have been removed.
* **Clean up the strat map.** The same for `descr_model_strat.txt` and
  `data/models_strat`.
* **Unit cards.** Folds identical per-faction card copies into the folder the
  engine falls back to, and removes art for units that no longer exist. 645 MB
  of Divide and Conquer's 1.2 GB of card art.
* **Clean up the unit file.** Group, tier and reorder `export_descr_unit.txt`
  repeatably. Running it twice produces no further change.
* **Fix ownership.** Adds a faction texture record to a model entry for every
  faction that fields a unit using it.

Nothing is deleted. Everything is moved to a folder you choose, and the removal
is backed up, so Log > Undo restores the mod exactly.

## Buildings

Every building line as a grid, with an editor per line: icons, name and
description, cost, build time, material, settlement size, capabilities, upgrade
path, and recruitment.

* **Requirements without code names.** Every term in a `requires` clause is
  picked from the mod's own data, since a typo is silent in game.
* **Ownership validation.** A `recruit_pool` naming a faction also needs the unit
  to list that faction in `ownership` and its model to have a texture for it.
  Both fail silently otherwise. Selecting a faction checks both.
* **Line checks** for problems only visible across a whole line: a unit that
  stops being recruitable as the building upgrades, a unit the city half trains
  and the castle half does not, and duplicate entries.
* **City and castle, side by side**, with controls to copy a pool across.
* **Bulk editing** of recruitment pools: one requires clause, pool numbers, or
  removal, applied to a selection built from several searches.
* The same pools are editable from the **other end** — the unit editor's
  Recruitment tab, above — for when the question is "where can this unit be
  hired" rather than "what does this building train".

## Safety

* Files are held as verbatim lines and every edit is a splice, so saving changes
  only the lines you changed. Comments, mixed indentation and line endings are
  preserved.
* Every write is backed up first and recorded in the log. Log > Undo restores
  byte-exact.
* Parsers round-trip real mod files byte for byte, which is verified by the test
  suite against whatever mods are installed.

## M2TWEOP

Units defined in the extender's own folder rather than `export_descr_unit.txt`
are read as part of the mod's roster, badged EOP, and can be transferred,
edited, renamed, deleted and given a voice. Edits are written back to their own
file. A transfer can choose which file a unit is written to, which is how a unit
is kept outside the 500-unit cap.

A mod can be marked as M2EX on its Home card. That stops the toolkit reporting
the five engine limits M2EX removes, and it changes one thing about transfers
into that mod: a projectile's effect sets are carried across with it, rather than
being replaced by `invisible_placeholder_set`.

Effects are normally not imported because they live in files shared by every
projectile in the mod, and how many the engine will load is another of the
hardcoded tables — what sits past the end is dropped without a message. M2EX
replaces that table, so for a mod marked for it the toolkit copies each effect
set the source actually defines, the effects that set lists, and the models and
textures those name. A set the source does not define itself is left as a
placeholder as before: it comes from vanilla, and vanilla's copy is not the
toolkit's to move.

## Running from source

Requires Python 3.9+ and Pillow.

```bash
pip install pillow
python app.py
```

Or run `Launch-Medieval2-GUI-Toolkit.bat`, which checks for both first. If
Python is missing entirely, `Install-Dependencies.bat` will download the
official installer, install it for the current user with no administrator
prompt, add it to PATH, and then install Pillow. It prompts before downloading.

```bash
python app.py --check        # startup checks only, no server
python app.py --port 9000    # different port
python app.py --no-browser   # serve without opening a browser tab
```

## Building a release

```bash
python build_release.py --version v2.1.7
```

Produces `dist/Medieval2-GUI-Toolkit-v2.1.7.zip`: the tool, a bundled Python
runtime, Pillow, and the packed vanilla building art. `--no-runtime` builds a
code-only zip for a machine that already has Python.

The vanilla building art ships by default and the build verifies the finished
archive contains it. A release archive is approximately 50 to 55 MB.

## Command-line transfer

```bash
python transfer_cli.py --from "<source mod>" --to "<dest mod>" --unit "Unit Name" --out transfers/out
```

`--list` shows the source mod's unit types. `--dry-run` plans without writing.

## Tests

```bash
python tests/test_parsers.py
python tests/test_transfer_v2.py
# one module per tests/test_*.py
```

Each suite is self-contained and safe to run against real mod installs. All
writes happen in temp directories or through the backup and undo path.

## Troubleshooting

Every run is logged to `config/server.log`, or to
`%LOCALAPPDATA%\UnitTransfer\server.log` if that folder is not writable.

**If something went wrong, send the log.** Settings > Something went wrong? >
Save diagnostic log downloads it. It records the build, Python version and OS;
each mod's file state before modification; what the job detected and decided;
and every file written, backed up, copied, exported or deleted, with paths and
sizes. It rotates at 4 MB.

**A mod the toolkit lists but cannot read** reports which file and why:

* `data/export_descr_unit.txt is not there`. The folder has a `data/` but no
  loose unit roster. Every stock install has four of these: `americas`,
  `british_isles`, `crusades` and `teutonic`, the Kingdoms campaigns, which keep
  their files inside `data/packs/*.pack`. Unpack the mod and it becomes an
  ordinary one.
* `battle_models.modeldb could not be read`. The file is length-prefixed, so a
  count that disagrees with what follows it desynchronises the reader and the
  read fails further down on a valid line. The message names the entry, the line
  holding the count, and the value to check.

**If the launcher window opens and closes with nothing visible**, the tool
usually started but your browser did not open. Go to `http://127.0.0.1:8756/`
manually.

## Project layout

* `unittransfer/`: parsers and writers for each file format, the transfer
  engine, the in-mod edit engine, and the local HTTP server
* `web/`: the browser UI, plain JavaScript with no build step
* `tools/nvtt/`: NVIDIA Texture Tools 2.0, driven headless by Sprites mode
* `tests/`: one module per area, runnable individually

## Changelog

See [Releases](../../releases).
