# Medieval 2 GUI Toolkit - an introduction for a new assistant

You are being given this file so you can get used to the project before helping
with it. Read it whole. It describes what the project is, how the code is laid
out, the rules it is built by, and how the work is organised. It is a snapshot
from 2026-10-22; where it disagrees with the files named below, the files win.

## What it is

The **Medieval 2 GUI Toolkit** (formerly "Unit Transfer") is a free tool for
modding *Medieval II: Total War* without hand-editing its text and binary data
files. It is written by one developer (GitHub: ProJ-Yeet) with a few outside
contributors, and released at
<https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit>.

It runs as a **local web server** (Python) with the interface in the user's
browser (plain JavaScript). It only ever writes to the mod the user points it
at, and every write is backed up and undoable.

What it does, by module:

| Module | In short |
|---|---|
| Home | every installed mod, what each is ready for, launch checks, animation pack housekeeping |
| Unit Transfer | copy a unit from one mod into another with everything it depends on (models, textures, cards, sounds, animations, banners, recruitment) |
| Unit Editor | change, clone or delete a mod's units |
| Models Editor | the `battle_models.modeldb` entries, sprites, campaign-map models and unit cards; a 3D viewer that plays the mod's own animations; **Armory Studio**, a kitbash workbench (import parts, rig, recolour, bake textures, export into a mod) |
| Buildings | `export_descr_buildings.txt` as a tree with recruitment, checks, and building lines brought from another mod |
| Campaign Map (beta only) | the ten map layers, regions, `descr_strat.txt`, painting, settlements, new campaigns, real-world generators, a 3D view |
| Unit Sounds | voice banks, sound banks and the `descr_sounds_*.txt` scripts |
| Sprites, Strings | far-LOD sprites; compiled `.strings.bin` text files |
| Traits / Ancillaries, Guilds | full editors, including what M2TWEOP Lua scripts do with them |
| Factions | faction definitions, add/clone/rename a faction across every file that names it, a whole faction from another mod |
| Minor Files | rebels, religions, resources, names, cultures, campaign constants, walls, agents and more |
| Raw text | any file as plain text, with the same backup and undo |
| My changes | a record of everything changed in a mod, portable onto a new version of that mod |
| Health | every check the toolkit has, over one mod, in one list |

The README at the repository root describes every module and screen in detail.

## The stack and the size

- **Python 3.9+**, standard library plus **Pillow** (and numpy, bundled in the
  release). The server is `http.server`-based, in `unittransfer/server.py`.
- **Plain JavaScript, no build step, no framework, no npm.** WebGL for the 3D
  viewers.
- About **148 Python modules** in `main/unittransfer/` (~115,000 lines) and
  about **100 JS files** in `main/web/js/` (~58,000 lines).
- **193 test suites**, `main/tests/test_*.py`, one per area, each runnable on
  its own.
- Interface in English, German and Spanish (`main/web/i18n/*.json`); more
  languages are scheduled last.
- Windows is the target platform (the users are Windows players).

## Repository layout

Only the two `.bat` files and the README sit at the root. Everything else is
under `main/`, which is the code root.

```
Install-Dependencies.bat          installs Python and Pillow if missing
Launch-Medieval2-GUI-Toolkit.bat  starts the tool
README.md                         the user-facing manual
main/
  app.py                          starts the local server (port 8756)
  transfer_cli.py                 the unit transfer from a command line
  unittransfer/                   ALL parsing, writing and disk I/O, the
                                  transfer and edit engines, the HTTP server
  web/                            index.html, js/ (one file per screen), i18n/
  tests/                          one suite per area
  docs/                           STATE, ROADMAP, RELEASE and their archives,
                                  releases/ (one notes file per version)
  dev/                            tools for working ON the toolkit, never
                                  shipped: release/ (build the zip),
                                  checks/ (run_suites.py, i18n and prose
                                  checks), diagnose/, docs/, i18n/
  vendor/nvtt/                    NVIDIA Texture Tools, for TGA to DXT5
  config/                         settings, backups, undo log (not in git)
  dist/                           build output (not in git)
```

A few modules worth knowing by name, as a way in:

- `edu.py` - `export_descr_unit.txt`, the unit roster
- `modeldb.py` - `battle_models.modeldb`, a length-prefixed archive
- `transfer.py` - the unit transfer engine
- `edit.py` - the in-mod edit engine (plans, splices, undo)
- `mod.py` - finding and describing a mod on disk
- `gamepack.py`, `pack.py`, `animpack.py` - reading the game's `.pack` files
  and animation packs without unpacking
- `mesh.py`, `meshwrite.py`, `cas.py` - 3D model formats
- `campmap.py`, `stratmap.py`, `mapcheck.py` - the campaign map
- `server.py` - every `/api/...` route
- `web/js/core.js` - the shared front end: the module list (`MODES`), helpers

## The rules it is built by

These are locked decisions. Proposals that break one will be turned down.

1. **One engine.** `unittransfer/` is the only owner of parsing and disk I/O.
   Never a second parser for the same format, and never file access from the
   browser.
2. **Plain JS only.** No React, no npm, no bundler, no build step.
3. **Self-hosted local app.** Never a hosted web app.
4. **Edits are splices.** Files are held as verbatim lines; saving changes only
   the lines that changed. Comments, indentation and line endings survive.
   Parsers must round-trip real mod files byte for byte.
5. **Every write is backed up first and logged**, and Undo restores it byte
   exact. Bigger changes are shown as a **plan** before they are applied.
6. **No AI or autogenerate features.** A permanent no.
7. **A rule with no evidence reports nothing.** A check that needs a file which
   is not there names the missing file instead of reporting false faults.
8. **A baseline shows and stops blocking; it never hides.** A mod's inherited
   bugs stay visible and counted but do not refuse a save.
9. **Localised names first** in the UI, code name in brackets:
   `Town Hall (core_building)`.
10. **Code View**: a shared two-pane widget (form and raw text, linked) used by
    every editor.
11. **German and Spanish are kept complete**: a commit that adds an interface
    string adds it in all three catalogues.

Style rules for anything written for the project (code comments, docs, release
notes, UI text):

- **No em dashes, anywhere.** Use a hyphen, a comma or a new sentence.
- Plain, concrete prose: say what a thing does and what was measured, not
  marketing language. Match the voice of the file you are editing.
- Code should read like the code around it: same naming, idiom and comment
  density. Keep changes surgical.

## How the work is organised

- **`main/docs/STATE.md`** - where the work stands and what is next. Its
  header line is a running log of what was done, newest first.
- **`main/docs/ROADMAP.md`** - the locked decisions, the phase index, the map
  format reference, and **the schedule** of what is left.
- **`main/docs/ROADMAP_ARCHIVE.md`** - write-ups of finished phases, and the
  reasons behind the rules.
- **`main/docs/RELEASE.md`** - the only copy of the release procedure.

Work is split into **numbered phases** (e.g. Phase 96), each a feature built
start to finish; its **lettered pieces** (96a, 96e1, ...) are individual
commits. Phases are grouped into **major phases**:

| Major | What |
|---|---|
| I | Models Editor and Armory Studio (finished) |
| II | Campaign map (Phase 97 and parts of 96) |
| III | Factions, units and mod data (Phase 96, **in progress**) |
| V | Translations (French, Portuguese, Polish, Turkish, Russian, Chinese, Japanese, Korean) |

As of 2026-10-21 the current work is the rest of **96f** in major III, starting
with a culture change and its preview.

## Releases

There are **two release lines off one `master`**:

- **2.x** (latest **v2.4.8**): the stable line, built with the Campaign Map and
  Armory Studio hidden.
- **The beta** (latest **beta 2026-10-20**): a pre-release named by date, with
  both visible.

`master` always keeps both visible. Releasing happens **only when the
developer asks for it**; otherwise work is committed to `master` and stops.
Release titles look like `M2 GUI-Kit V2.4.8`. The full procedure is in
`RELEASE.md`; do not improvise one.

## Testing

```
python main/dev/checks/run_suites.py               every suite, in the background
python main/dev/checks/run_suites.py test_cas      one or more suites
python main/tests/test_edu.py                      a suite by hand
```

Suites run against the mods actually installed on the developer's machine
(Third Age Reforged, Divide and Conquer and others), so some failures come from
which mods are installed rather than from the code. A failure is checked
against a clean tree before it is believed.

## Vocabulary

- **M2TW** - Medieval II: Total War. **Kingdoms** - its expansion.
- **EDU** - `export_descr_unit.txt`, the unit definitions.
- **EDB** - `export_descr_buildings.txt`, the buildings.
- **BMDB / modeldb** - `battle_models.modeldb`, battle model entries.
- **descr_strat** - `descr_strat.txt`, a campaign's starting state.
- **M2TWEOP** - an engine extender with Lua scripting; **M2EX** - an engine
  extender that lifts hardcoded limits.
- **`.mesh`, `.cas`** - battle and campaign/animation model formats.
- **Packs** - the game's `.pack` archives and the animation `pack.dat` files.
- **DaC, TATR / Reforged** - Divide and Conquer and Third Age Reforged, the
  large overhaul mods everything is tested against.
- **Subrelease** - a release on both lines at once.

## How to help well

- Ask for the relevant file before suggesting changes to it; the code base is
  too large to guess at, and the existing helper you need usually exists.
- Respect the locked decisions above, especially one engine, plain JS, no
  build step and no AI features.
- Prefer the smallest change that solves the problem, written in the
  surrounding style.
- When something is uncertain, say so and ask rather than assume.
