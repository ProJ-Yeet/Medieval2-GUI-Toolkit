# v2.3.8

**Models that move, eight files that had no screen, and a way back.**
Everything since v2.3.7: battle-model animation played, edited and exported;
several factions added at once; a readiness check for whether a mod will even
start; screens for settlement mechanics, religions across every region, the
populace and off-map models, war animals and standards, the advisor, battle
banners, hero abilities and area effects; one file in or out of a mod at a
time; and addresses for every screen, so a finding opens in a new tab.

## New

* **The Models viewer plays a battle model's animations.** A new *Animation*
  section lists every action the entry's skeletons name, plays the ones the
  mod ships loose (Divide and Conquer's MTW2_Mace: 156 of 195) and marks the
  rest packed (ROCSS packs all of its own, and says so). Play, pause, scrub,
  speed; a cycle is played in place.

* **Edit an animation, and get a model out.** The Animation section's *Edit*
  fold trims, changes speed, plays in place, scales, turns a bone, or sets a
  bone at one key, and saves beside the original with an optional
  `descr_skeleton.txt` repoint and one Undo. A loose file only reaches the game
  once the mod's `pack.dat` is rebuilt, and every save says so. *Export* gives
  a `.glb` (skeleton, skin, texture and actions, which stock Blender imports),
  an `.obj` zip, and `.texture` to `.dds` and back.

* **Several factions at once, and the faction files as a zip.** *Add a
  faction* takes several rows from one donor, each with its own titles and
  strengths, planned together and written as one job with one Undo. A checkbox
  turns the donor's name in its copied text into the new one ("Mordor Scout"
  becomes "Rhun Scout"). *⇩ Faction files* downloads every file naming a
  faction, and the open faction's art, as a zip laid out under `data/`.

* **Will this mod even launch?** Each Home card has a *Launch* row: every way
  the mod folder offers to start the game (a `.bat`, the M2TWEOP launcher, a
  bare `.cfg`) and, for each, whether its `.cfg` names this folder, sets
  `file_first`, and starts an executable that is there and Large Address Aware.

* **Settlement mechanics.** A tab beside Campaign constants edits
  `descr_settlement_mechanics.xml`: the growth, public order and income
  factors (`SIF_MINING` is the mines) and the two population ladders.

* **Add a religion, properly.** Adding a religion now gives every region's
  religions line a share of 0 in every `descr_regions.txt`, can start it with
  a share in the regions you pick (taken from the others in proportion, so
  every line still sums to 100), hands the share back on a delete, and can copy
  another religion's pip.

* **One file in or out.** Raw text downloads the open file, replaces it from
  disk, or puts any file at any path under `data/`. Each is a plan first (an
  encoding change, the file's own reader, a `.strings.bin`, a DDS wrapped onto
  a `.texture`) and one Undo.

* **Populace and off-map models.** `descr_lbc_db.txt` (who walks each
  faction's streets, the shares totalled to 100) and `descr_offmap_models.txt`
  (the navy, settlement and port models off the map). It found DaC's
  `faction egypt` with no opening brace, which ends DaC's navy section fourteen
  factions early.

* **Animals, standards and advice.** One tab, three files: the war animals,
  checked against the units that use them (it found ROCSS's Princess carrying
  `animal wardogs` where the file declares `wardog`), the strat-map standard's
  flag models and symbol sheets, and the advisor's threads and the triggers
  that fire them.

* **Battle banners.** `descr_banners_new.xml`: every banner, a texture per
  faction, rows added by copy and removed. A faction owning a unit whose banner
  has no row for it is the warning. It found DaC's thirteen stale lines after
  `</Banners>` (a *cut them off* button) and ROCSS's two broken texture paths.
  The faction audit has a Battle banners row, and *Add a faction* now writes
  thirteen files.

* **Hero abilities.** `descr_hero_abilities.xml`: a named character's battle
  ability, its duration, uses, cooldown, button, tooltip text and sound, and
  its effects on the armies, with effects copied between abilities and an
  ability copied under a new name. It shows how many character lines give each
  one.

* **Area effects.** `descr_area_effects.xml`, which is what a shot does where
  it lands: the sickening cloud, the fire on the ground, the explosion, the
  shot that splits into more, the holy aura, and sets of them fired one after
  another. Each shows the projectiles and engines that name it. On each
  installed mod the one warning is a projectile naming an area effect that is
  never declared.

* **Every screen has an address.** A Health finding, or any link to a record,
  is a real link: middle click opens it in a new tab. Under the header, a
  trail of where you have been, with back and forward, keeps each screen's
  scroll, so coming back from a fix puts the row you left under the cursor.
  The browser's own Back button walks it.

## Changed

* **Campaign constants say what they mean.** `bool="true "` was called "not
  true or false"; blank space inside the quotes is now named as blank space,
  as a warning. `int="100.0"` is a hundred and is taken, as a note. A Health
  finding here opens on the tag rather than the top of the screen.

## Fixed

* **A unit transfer blanked projectile effects the destination had.** The
  toolkit read four of the 18 effect files a mod's `descr_effects.txt` lists,
  so a set in any of the others was "missing" and the projectile's line was
  pointed at the placeholder: 165 lines for ROCSS units going into Divide and
  Conquer. It reads the whole list now. A name nothing can check (the base
  game's files are packed) is still blanked, and the plan says which ones and
  why. With M2EX on, an imported effect is never written into an effect file
  the destination leaves to the base game, which would have replaced that
  whole file.
* **A texture imported in the same save as a folder move** landed in the old
  folder while the model pointed at the new one. It follows the entry now.
* **Health crashed** when a tab was opened straight onto it.
* **A dialog stayed open over the next screen** after a mode switch.
