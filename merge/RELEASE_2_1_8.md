# v2.1.8

Adds a faction to a mod by copying one that already works, and adds a way to
look at a model's UVs instead of its art.

## Added

* **Add a faction.** The Factions tab has spent its whole life explaining why it
  would not do this: a faction slot is named in a dozen files at once, and one
  that exists only in `descr_sm_factions.txt` is a mod that will not load. That
  was right about the problem and wrong about what to do with it. **＋ Add a
  faction** writes all twelve.

  It copies rather than invents, which is what makes it safe. Pick a faction
  that already works, give the new slot a code name and a name for the game to
  show, and every one of those files gains the donor's own answer under the new
  name: the roster record, `expanded.txt`, every unit's ownership line, the
  modeldb's faction skins, every `requires factions { … }` clause in
  `export_descr_buildings` — which is what lets a faction build and recruit at
  all — the voice accent, diplomatic standing, agents and generals, campaign map
  models, character names, settlement populace and off-map navies. Its symbols,
  banners, captain cards and unit card folders are copied and renamed with it.
  Nothing is guessed at: the clone is the donor under another name, and you
  change what you want afterwards in the editors already beside it.

  You see what each file would gain, with counts, before anything is written.
  Every file is backed up, and the whole faction — twelve files and every copied
  picture — undoes in one go from the clock icon.

  Three files name a faction as a *judgement* rather than as a list: a trait
  named after it, an ancillary's `and FactionType x` operand, a prebattle
  speech. Appending to those would invent a trait the engine has never heard of
  or quietly rewrite a condition, so they are counted, named, and left to the
  Traits and Ancillaries editors, which already open them.

  The campaign start position is reported and not written, and that is
  deliberate: a `descr_strat` entry is a region, a settlement, a starting army
  and map coordinates, and two factions cannot begin in the same settlement.
  There is no donor answer that would still be right. The clone loads, appears
  in custom battles and owns its units; give it a settlement before expecting it
  in a campaign.

  **Deleting a faction is still refused,** and now for a sharper reason than
  before. A clone copies the donor's answer into every line that names the slot.
  A delete would have to invent one for every line instead, and nothing can work
  that out for you.

* **Show UVs**, in the 3D viewer, for when the skin is the thing you are
  debugging. It paints the UV coordinate instead of the art, in the same space
  the game samples: blue is the main sheet, amber the attachment sheet, the dark
  tiles are those two repeating, and a red line marks where the pair starts over.
  Thirty-two checker cells to a sheet — measured, not picked, because real parts
  span a twentieth to a third of the sheet each and a coarser grid says nothing
  about a head. Art stretched over a part shows up as stretched cells. The
  button is off for a model that carries no UV set, and the key drops the amber
  row for a model drawn from one sheet.

## Changed

* The Factions tab says **twelve files**, everywhere it used to say nine. Nine
  was the number in the phase-11 refusal, and it had never been measured;
  grepping the installed mods for a slot turned up `export_descr_buildings`,
  `descr_sounds_accents` and `descr_faction_standing` on top of it. The cloner
  has always written all twelve — this is the wording catching up with it.
