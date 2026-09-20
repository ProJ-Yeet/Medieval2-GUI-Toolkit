# v2.3.5

Everything since v2.3.4 that is not the campaign map editor. **The buildings
file gets its second validator** - the one that reads the shape of the tree
rather than what each level recruits - and three things that stopped people
using the tool at all are fixed: a launcher the zip did not contain, a port
Windows refuses, and a strings archive that would not open.

## New

* **Check the tree, on the Buildings screen.** Nine rules over the shape of
  `export_descr_buildings.txt`, on the button beside the gallery. Until now
  every EDB check here was about recruitment - a unit that stops being
  trainable further up the chain, the same unit twice in one level, a line that
  has drifted from its city or castle twin. None of them looked at whether the
  file hangs together.

  Five of the nine are references that either resolve or do not, and each one
  is a fault the game would meet before you did: a **building name used twice**,
  a **line with no levels in it**, an **`upgrades` entry naming a level that is
  not on that line**, a **`convert_to` naming a building that does not exist**,
  and a **`building_present_min_level` naming a line, or a level on it, that
  does not exist**. That last one is the condition in the EDB that can dangle
  two ways, and the only one that has never had anything checking it.

  Three more are worth knowing rather than wrong: a level that **costs
  nothing**, one that **finishes the turn it is started**, and one **no faction
  is named as able to build**.

  Every finding names its rule and the line of the EDB it is on, and opens the
  building it is about. The same findings are on each building's own page,
  under its recruitment checks, narrowed to that line.

* **The rules say who says they are rules.** Each of the nine carries its
  source, and the panel lists all nine whether they found anything or not - a
  validator that is silent should not look like one that did not run.

## Fixed

* **The launcher the instructions name is now the launcher in the zip.** The
  build wrote `Launch-Medieval2-GUI-Toolkit.bat` into the release as
  `Launch-Medieval 2 GUI Toolkit.bat`, so every instruction that named the
  hyphenated file - including the one in this README - pointed at something the
  download did not contain. One name now, and the build refuses to package at
  all if the documentation names a `.bat` that is not in it.

* **A port Windows will not give up no longer stops the tool.** The startup
  check only tried to *connect* to the port, so one that was bound but not
  listening, held exclusively, reserved or firewalled looked free - and the
  server then died on its own bind with `WinError 10013`. It binds to check
  now, and when the port cannot be had and nothing on it answers as a toolkit,
  **startup moves to the next free port and tells you where the window
  opened** instead of handing you an error code to solve.

* **Strings archives that ended early now open.** Some game-written
  `.strings.bin` files end an empty tag index with a lone `u16` zero, or with
  nothing at all, and the codec refused them outright with "file ends before
  its tag index" - Wrath of the Norsemen ships several. Both forms decode now,
  and the ending is remembered so a save or a recompile is byte-exact. Ported
  from a pull request by **WalhallaZ**.

## Changed

* **Three rules the reference tool has are deliberately not here, and the panel
  says so.** Under *The 9 rules, and the three that are deliberately not here*:

  * **"a line may not have more than 9 levels."** Divide and Conquer ships two
    lines over it, at 13 and 12 levels, and the mod plays. A ceiling a shipping
    mod is over is not a ceiling.
  * **"warn as a line approaches 50 levels."** The largest line on any mod
    installed here is 13, so there is nothing to check the claim against.
  * **"a level nothing upgrades into is unreachable."** This one assumes every
    building line is a chain, and **42 lines across the two mods measured are
    not**: their levels are alternatives picked by a hidden resource, so
    "reachable" means nothing on them. `hinterland_enedwaith_clan_halls` is
    nine mutually exclusive clan halls. Reported as *worth knowing* instead,
    and only on a line that really is a chain.

* **`RELEASE.md` and `CLAUDE.md` are in the repo now.** Both were ignored, and
  both describe how the project works rather than how one machine is set up -
  so anyone cloning it got instructions pointing at a file the clone did not
  contain.

## Notes

Both mods installed here come out of the new rules clean of anything fatal:
Divide and Conquer has three *worth knowing*, ROCSS five *worth a look*, and
all 336 `building_present_min_level` references across the two of them resolve.
