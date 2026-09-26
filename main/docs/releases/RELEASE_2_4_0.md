# v2.4.0

**Animations travel with a unit, and can be edited where the game plays them.**
Everything since v2.3.9: a mod's animation packs read in place, every action a
model has played in the Models viewer, a transferred unit bringing the
animations the destination lacks, an edit saved straight into the pack, and a
skeleton or one animation brought from another mod. Nothing is unpacked or
repacked: a pack is only ever added to, and one Undo takes each change back.

Every change to a pack was proved in the game on Third Age Reforged with units
from Divide and Conquer: Hobbit Infantry, Suriut Chariots, Trolls, the Moria
Balrog and Steward's Guard all animate after the transfer.

## New

* **Every animation a model has, in the Models viewer.** The actions are the
  filled slots of each of the model's skeletons, read straight out of the mod's
  `pack.dat` (or vanilla's, for a mod that ships none), all 687 slots named and
  grouped: idles, walks, attacks, deaths and the rest. A slot's impact frame
  and its sound and effect cues are marked on the scrubber. The weapon
  skeletons move the weapon, a rider can be shown on his mount, a campaign
  model's `.cas` plays too, and another mod's take on the same action can be
  played beside it.

* **A transfer brings the unit's animations.** A skeleton the destination's
  pack does not have is appended to it with every animation its slots name,
  reusing what the destination has already, byte for byte, under any name.
  DaC's Balrog costs a few MB, not a copy of DaC's 352 MB pack. The copied
  model is pointed at the name the skeleton lands under, and the transfer's
  one Undo cuts the pack back. The loose `.cas` files and a
  `descr_skeleton.txt` block are written too, so a modder who removes the
  packs to have the game rebuild them keeps the unit.

* **An edit saved into the pack.** The animation editor now opens on an action
  played from the pack and saves the edit there, under a new name, with the
  skeleton's slot pointed at it, so the game plays it on every model with that
  skeleton. What the editor previews is exactly what it writes.

* **Another mod's animation in one slot.** Beside the model, *Use it here* puts
  another mod's take on an action into this mod's slot. When the two
  skeletons' bones differ, the animation is carried across bone by bone.

* **A skeleton from another mod.** *Bring a skeleton from another mod…* in the
  animation panel ports one skeleton with all its animations. If this mod
  already has a skeleton of that name, it comes in under a name of its own,
  and the model on screen can be pointed at it.

* **Animation packs on the Home screen.** Each mod card has an *Animation
  packs* line: what the packs hold that nothing plays, and a compaction that
  writes them again without it, the old packs kept until you let them go. All
  three mods measured were already clean.

## Fixed

* **A transfer no longer breaks the destination's unit file** in three ways
  the game rejects outright: an `ownership` or era line naming a faction the
  destination has not got (it is left out, and a unit left with no owner is
  given to the rebels), an engine's shot effect the destination lacks
  (commented out), and a soldier count above what the destination's engine
  takes (DaC's 120 Balrogs become 100 in a mod without M2TWEOP's higher cap).

* **The editor says what a loose file does.** A loose `.cas` does not override
  an animation the pack holds, so the editor no longer tells you a rebuild with
  an outside tool is the way; it saves into the pack instead.

* **Two skeletons whose names differ only in case** (vanilla has a body and a
  weapon skeleton called `MTW2_Halberd_Primary` and `MTW2_Halberd_primary`)
  are told apart.

* **The interface starts with an ad blocker on.** One of its scripts was named
  so that some blockers dropped it, and the page never finished loading.
