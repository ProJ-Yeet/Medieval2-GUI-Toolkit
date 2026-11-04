# v2.4.10

**The campaign map in 3D you can work in, the base game as a source, and a
Report button that reaches us.** Everything since v2.4.9: the rest of Major III
(factions, units and mod data), Major II (the campaign map), and the fixes from
a user's failed transfer. Two more languages as drafts, Turkish and Simplified
Chinese.

![The campaign map in 3D, faction names over their lands](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.10/campaign-map-3d.png)

## New

* **🐞 Report**, on the top bar of every screen. Say what went wrong or what
  the toolkit should do, add or paste screenshots, and Send. The report carries
  your words, the page's and the toolkit's logs, the game's `system.log` and
  your newest transfers. Your Windows name, the computer's name, e-mail
  addresses, Steam IDs and IP addresses are taken out first, and *Show what is
  sent* shows every line. *Answers to my reports* shows our replies.
* **The base game as a source.** *Medieval II Total War (base game)* is listed
  beside your mods, read straight out of its packs: its units, buildings,
  cultures and names. Look at it, or take units from it in Transfer. It is
  never written to; *New mod folder from the plain game* makes a mod of it
  first.
* **A failed transfer puts everything back.** If a transfer fails halfway,
  every file it already wrote is restored and the box says what went wrong,
  with *Report this*.
* **Projectile effects with the unit.** *Bring the effects anyway* copies a
  unit's missile effects to a mod not marked as M2EX, with the files the base
  game left in its packs.
* **The campaign map (beta):**
  * **Select and edit in 3D.** Click a region, paint, drag a port or a
    settlement on the 3D map just as on the flat one.
  * **Faction names over their lands**, lettered along each realm in its own
    colour, in 2D and 3D.
  * **Characters, settlements, forts and towers as models** on the 3D map.
  * **Icons**, one switch that hides every icon on the map.
  * **The garrison** in the settlement editor: the armies in the town, edit or
    remove them, or add one.
  * **Port and settlement by icon**: move the settlement, add, move or remove
    the port.
  * **Many towns at once**, each with a garrison, and the whole region record
    in the new region wizard.
* **Menu sheets**: the game's menu pictures (`strategy.sd`, `shared.sd`,
  `battle.sd`, `radar.sd`) page by page and culture by culture, every sprite
  named. Find one, save it as PNG, or paint your own picture into its box.
* **The unit preview draws the crew with its siege engine**, and an *Armour*
  button steps through the unit's armour upgrades.
* **Blender exports into a mod.** Point the Models Editor at an export folder
  and import its models with their textures, as written by its `_bmdb.txt` or
  cloned from an entry you pick, then put them on a unit with its cards.
* **M2EX text battle models** are written by every editor, not only Transfer.
  *Use text battle models* turns an M2EX mod's `.modeldb` into
  `descr_model_battle.txt`, and *Write vegetation as text* does the same for
  vegetation.
* **Factions:** preview a culture change (the units gained and lost, the
  buildings its towns can no longer build) before you save it; leader and heir
  titles, strengths and weaknesses; surnames from the faction's own list.
* **Religions from nothing:** a pip drawn for you, and a temple chain built
  from the mod's usual temple numbers, with plain cards.
* **Transfer brings more:** the unit's own voice, and the buildings that train
  it when the destination lacks them.
* **Scripts:** the Module builder as Scratch-style blocks, and the campaign
  script split into its pieces.
* **New unit from what is usual** in the mod for spearmen, archers, horsemen
  and the rest.
* **Every picture** in a mod by kind, **hover cards** that show any small
  unit or building picture big, and **an area of like colour** recoloured in
  one click.
* **A faction's select-screen map** drawn from the campaign map.
* **The card maker** makes *Bigger* cards and a *Painted look*.
* **The toolkit's own look**: your own colours and font, and any button, tab
  or label renamed or hidden.
* **Community translations**: drop a `<language>.json` in
  `config/translations/`, and *Words to translate* in Settings gives a
  translator every string.
* **Health** warns of a town that starts with two guild buildings.
* **Türkçe (Turkish)** and **简体中文 (Simplified Chinese)**, offered as
  drafts in Settings. French, German and Spanish cover every new string.

## Fixed

* **"No such file or directory ... export_units.txt"** on a transfer. A mod
  without its own `export_units.txt` (one that keeps only the
  `.strings.bin`, or none, leaving the game to use its own) stopped the
  transfer after the unit's EDU block was written, leaving a unit with nothing
  behind it. The text is now read from wherever the game reads it: the mod's
  `.strings.bin`, its packs, or the base game. The `.txt` written keeps every
  unit's name, not only the new one. The Unit Editor does the same.
* The campaign map's stray green box and the empty band under it are gone.
* The last few English labels in the other languages are translated.

## Screenshots

![The campaign map, flat](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.10/campaign-map.png)
![Menu sheets](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.10/menu-sheets.png)
![The Module builder as blocks](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.10/module-blocks.png)
![Report a problem](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.10/report.png)
![The base game on Home](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.10/base-game.png)
