# v2.3.3

Everything since v2.3.2 that is not the campaign map editor. **BMDB + Sprites is
the Models Editor**, a faction's name pool can be merged into another faction's,
cloning a faction now tells you what art it came away without, and three bugs go
with them - one of which took a whole mod's unit list down.

## New

* **BMDB + Sprites is the Models Editor.** That screen has had four tabs for a
  long time - model entries, sprites, strat map, unit cards - and only one of
  them was in the name. The two things that made the old name nearly true have
  been fixed instead.

* **Every campaign-map model in 3D, and you no longer need the campaign map to
  get at them.** Models Editor → Strat map has the same 3D panel the model
  entries have had: it opens beside the list, it keeps the width you drag it
  to, and it does not rebuild itself every time you type in the search box.

  Every entry that ships a `.CAS` gets its own 🧊. On Divide and Conquer that is
  206 of its 237 entries; an entry whose meshes are all inside a `.pack`, or
  simply missing, gets no button rather than a button that fails. A strat
  model's read-only card - the block as the file stores it, and every file it
  names - opens its meshes from there too.

* **And the panel browses the model files themselves, which is where the
  settlements are.** `descr_model_strat.txt` declares the generals, the agents,
  the heroes and the faction symbols - and **not one settlement**. The game
  picks those by level and culture out of the `data/models_strat` folder tree
  with nothing naming the file, which is why Amon Hen and Minas Tirith are on
  the campaign map and in no entry at all.

  So the panel has a second way in: a filter box and every `.cas` the mod ships,
  grouped the way its folders group them. Divide and Conquer declares 237
  entries and ships **926 model files**. This browser existed before, inside the
  campaign map editor - which is not in this build and never has been. It is in
  the Models Editor now, on the menu here for the first time.

* **Merge one faction's name pool into another.** Minor Files → Character names:
  take every first name, surname and settlement name a faction declares and add
  them to another's, with a **Dedupe** that drops the ones the destination
  already has and says how many it skipped. Merging nothing is refused and says
  which button to press instead.

* **Cloning a faction now says what art it came away without, and why.** The
  copier was never at fault; the missing part was a sentence. Nine places a
  faction's art lives, and for each one the clone came back empty-handed, one of
  four reasons: the donor has none either, the destination already has one, a
  longer-named faction owns that name, or the mod has no such folder.

  Measured over 121 donor slots across four mods: **253 empty places, 50 clean
  donors, and every one of the 253 explained.** Not one of Third Age Reforged's
  30 factions fills every place. The old warning - which fired on the whole scan
  and therefore almost never - now fires only when the scan really is empty.

## Fixed

* **58 factions could not be saved at all, because a name with a space in it was
  refused.** The names editor held that a name is one word. It is not:
  **2,513 of 34,923 names across two mods have a space** - 45% of all surnames,
  plus 90 characters and 10 women, `al Adid`, `Arigh Boke`, `Yax Kuk Mo`,
  `Hywel Dda`. Any faction whose pool contained one could not be written back.

  The real constraint is much smaller and is the only one now: a name may not
  **be** one of the file's own section keywords.

* **Camels, elephants and dogs showed no resource name at all.** Those three are
  keyed in the singular in the text files and the tab looked them up in the
  plural, in every mod, so the name column was simply blank for them.

* **A names file saved as anything but UTF-16 took the whole unit list down.**
  From a report on Vanilla Redux: "Couldn't open the transfer", and nothing in
  that mod would open. One `text/export_units.txt` saved out of Notepad as UTF-8
  was enough, because the file is read inside the registry lock on the first
  request the composer makes.

  Text files are now read off their byte-order mark and written back the way
  they were found. The one exception is an 8-bit file given a character 8 bits
  cannot hold: that goes out as UTF-16, and the warning says so rather than
  claiming the file went back as it came.

* **A 3D panel left over from another screen kept drawing to a page that was
  gone.** Leaving the Models Editor with the viewer open left a WebGL context
  and an animation loop running against an element no longer on the page. It is
  let go when you leave now.

## Where the rest of it went

This build is the same tree as **beta 2026-09-16** with the campaign map editor
switched off. Fifteen phases have landed since v2.3.2 and most of them are that
editor: climates, region recolouring, rebel pools, the campaign script's spawns,
the front-end picture, the brush's toolbar, three new map rules, and a rebuilt
panel beside the map. The beta's notes cover all of it.
