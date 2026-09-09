# v2.2.3

Renaming a faction. Not the block in `descr_sm_factions.txt` - a slot is what
about twenty other files point at, and until now the toolkit refused to touch it
and told you why. The campaign map editor is not in this build's menu; it is a
beta, and it lives on the dated **beta** pre-release, which is where the other
half of this work went.

## New

* **Rename a faction slot, everywhere it is named.** The Factions screen has a
  `Rename slot` button. It rewrites the roster, every unit's `ownership` line,
  every `requires factions { … }` clause that lets the faction build or recruit,
  the diplomatic standing rules, the agents, the accent, the strat-map models,
  the name pool, the settlement populace, the off-map navy, the guilds, the
  traits, the ancillaries, the prebattle speeches, the missions, the campaign
  music, the campaign start position, the win conditions and the ~30 `EMT_*`
  keys the event messages are read through. On Divide and Conquer that is
  **twenty-four files and about four thousand lines**.

  It also does the two things that are not lines. `battle_models.modeldb` stores
  a faction's name with its **length written in front of it**, so the count is
  rewritten with the name - 3,160 texture records on that mod. And the art the
  engine finds from the slot itself, with nothing pointing at it
  (`ui/units/sicily/`, `symbol24_sicily_roll.tga`, the banners), **moves** to the
  new name rather than being left behind under the old one.

* **You see the list before there is a button.** The dialog shows every file and
  how many lines of it change, every art folder that moves, and every line of
  campaign script that names the faction. `confirm()` with a sentence in it is
  not consent to rewriting a mod.

* **The campaign script is reported and never edited.** It is a scripting
  grammar this toolkit does not parse, and a wrong edit to one is a campaign
  that fails to start. Every occurrence comes back with its file and line number
  so it can be changed by hand - 423 of them for one faction on Divide and
  Conquer. Silently leaving the script pointing at a name that no longer exists
  would be worse than not renaming at all.

* **One backup set for the whole thing, and one Undo.** A rename half applied is
  a mod that will not load, so an undo that put back some of these files would
  be worse than one that put back none.

* **Refused before anything is written:** a slot the mod has not got, the name it
  already has, a slot with a capital letter in it (the engine reads a slot as a
  lower-case word, and every file that names one spells it that way), a name
  already in use, and either end of a rename being `slave`, `merc`, `mercs` or
  `all`, which the engine means something specific by.

## Fixed

* **The Code View's refusal now says where to go.** Renaming a slot in the text
  pane is still refused, for the same reason it always was, but the message
  names the button that does it properly instead of stopping at "you cannot".

## Where the rest of it went

The other half of this work is the same engine over a province and its
settlement, and it is reached from the campaign map screen, so it is on **beta
2026-09-09b** and not in this build's menu. That half also corrected something
this toolkit had been saying confidently and wrongly: `descr_strat.txt` does not
point at a settlement's name.
