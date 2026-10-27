# v2.4.9

**One download from now on.** The Campaign Map editor and Armory Studio are in
this release for everyone who wants them: tick **Opt into beta features** at
the top of Settings. There is no separate beta any more. With it, French as a
draft language, the tester's Armory Studio notes fixed, and all of Major III
so far: factions, units and mod data.

## New

* **Opt into beta features**, the first box in Settings. It puts the Campaign
  Map editor, Armory Studio and the unit card maker on the menu. They write to
  your mod like everything else, backed up and undoable; they have simply had
  less use. Off by default.
* **French**, offered as *Français (French) - brouillon* in Settings, every
  string translated. A native speaker's review is still to come.
* **Report a problem**, in Armory Studio's bar: write what went wrong and save
  it with a log of what the page did (each request, message and error), the
  model if you tick it, and the end of the server's log, as one zip.
* **A whole faction from another mod.** *Add a faction* takes a faction of
  another mod, built on a same-culture faction of this one, with its own
  colours, culture, religion, symbol, texts, names, map figures and art.
* **Scripts and add-ons.** A no-code Module builder (when, if, do, else) with
  nine worked examples, and ready-made add-ons: Sack and Raze Settlement,
  Avoid Growth, Recruitment Order, Player Diplomacy, Upkeep x N and One
  Recruitment Grid.
* **The family tree**, drawn as the game does and edited by clicking a
  person; a portrait of a character's own from one picture.
* **A faction's art.** Recolour its cards, pictures, textures and symbols from
  one pair of colours to another; battle banners painted new on a template of
  the mod's own; a whole emblem set from one picture.
* **Voices.** Hear a unit's name call in every accent and use a `.wav` of your
  own; model swap warns when two units ride different mounts.
* **Health** explains the game's log, lists the mod's contents (and saves
  `mod_files.txt` for a bug report), and rehearses a change set on a copy.
* **Rules** show the base game's own value beside each box, with a Reset.
  **New mod from this one** on a Home card makes a copy of hard links.
* `can_homeless` in the faction form, on M2EX mods only.

## Fixed

* **Armory Studio, from the tester's notes:**
  * A `.mesh` opened from disk could not be pulled into the model, nor taken
    out of Loaded assets with ✕: its Windows path broke every button on it.
  * Recolouring after moving UVs or wearing another sheet dyed the wrong part
    of the wrong sheet. It now dyes what the object shows, as the export does.
  * Grey mail and plate would not take a colour. A new **metal** channel, or
    marking the object as metal, colours them.
  * Transfer weights on a part away from the rest took over a minute; it
    takes a fraction of a second, with the same result.
  * Optimize never writes the file on disk, and now says so; each optimized
    object keeps **Restore the original mesh** for later.
  * Loaded assets opens as a gallery; the import list keeps its place after a
    closer look; the panels keep theirs after Full view.
  * The yellow selection tint stays off while you choose colours, and a 💧
    eyedropper picks a colour from anywhere on screen (Chrome and Edge).
* The Models viewer plays the copy of an animation made for the skeleton's
  own scale, so a soldier no longer comes out short with his legs apart.
* German and Spanish: three broken characters and a few terms corrected.
