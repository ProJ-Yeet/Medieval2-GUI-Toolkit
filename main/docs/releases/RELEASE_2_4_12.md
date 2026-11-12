# v2.4.12

**Unit sheets, a guided unit designer, and updates that install themselves.**
Everything since v2.4.11: the editable unit sheets with EDB balancing, the
unit designer built on the Stainless Steel: Reforged Unit Builder, each
faction keeping its own cards on transfer, riders on their horses in Armory
Studio, and the last of Pfadfinder-Adam's code written anew.

**This is the first release with the updater.** Download it by hand once;
from here on a portable install fetches each new release by itself and puts
it in at the next start, with your settings, sessions and backups kept.

![The Unit sheets window](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.12/unit-sheets.png)

## New

* **Automatic updates.** Settings has the switch, the status and *Check
  now*. A file you changed in the app is never overwritten, and a copy run
  from source only checks.
* **Unit sheets**, a button in the Unit Editor: every unit of the mod as rows
  you can edit.
  * Views for classifications, base stats, attributes, soft stats, the
    barracks rules and EDB recruitment, each with its own filters and saved
    columns.
  * **Mass edits** checked by the server and shown field by field, before and
    after, before anything is staged. Recipes save a view, a rule table or a
    balance profile to run again.
  * **CSV and XLSX** in and out of every sheet, the columns mapped and
    previewed first. Simple formulas are worked out; macros never run.
  * **EDB balancing**: replenishment, experience and max pool worked out in
    one ordered run you can cancel, every entry logged with its reason and
    the rule it came from, then Apply and Undo through My Changes.
  * Comparison groups with the min, max and average per mod.
* **The guided unit designer**, a Designer tab in the Unit Editor. Pick a
  rules profile (the mod's own values or Combat Reforged), then archetype,
  quality, class, equipment, weapons, armour, attributes and formation, with
  the EDU block beside it.
  * Upgrade bonuses are read from each mod's engine: vanilla, EOP and M2EX
    each the way the game does them.
  * **Apply to a unit** hands the fields you tick to the Unit Editor, or to
    New unit for a unit of its own, with missing models, projectiles and
    mounts named first.
  * Projects save, import and export, upstream Unit Builder projects
    included.
* **Faction models** in the Models Editor: one faction's strat model levels
  with the traits that reach each one, its generals' and captain's battle
  models, its agents, its leaders and heirs, all editable with a preview and
  an Undo each.
* **Transfer: a Factions section.** Each faction the unit has a skin or card
  for, beside the destination faction it lands as, with a picker and *Leave
  out*. A row is flagged where a code means another faction there, or two
  land on one.
* **Armory Studio (beta):**
  * **Pre-render lighting**: bakes an ambient and a key light, with soft
    shadow, into a copy of each colour texture, from its spec and normal
    maps, set live in the viewport. *Remove* puts the original back.
  * Add a model as the soldier, an officer or an armour tier, give a
    general, faction leader or heir a battle model, and scale an animation.
* **The Unit Editor warns** when a faction that fields the unit would get the
  generic unit card or info picture.
* **Credits** for Lupinemaverick's Stainless Steel: Reforged Unit Builder and
  Pfadfinder-Adam's Campaign Editor.

![The guided unit designer](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.12/unit-designer.png)
![Faction models](https://github.com/ProJ-Yeet/Medieval2-GUI-Toolkit/releases/download/v2.4.12/faction-models.png)

## Fixed

* **A unit carded per faction got one faction's card in every folder** on
  transfer, so France showed England's Arquebusiers. Each faction now gets
  its own.
* **A rider stood beside his horse** in Armory Studio and the card maker,
  and the horse kept its bind pose. He now sits in the saddle and the horse
  plays its own action, whichever skeleton you pick.
* **Shields, helmets, quivers and bows floated** where they were modelled
  while their man moved. They stay on his arm, head or hand.
* **The strat model cleaner called live models unused** when they were named
  only in a switch folder or in the game's packs.
* Closing the model viewer from Edit unit crashed the preview.
* The Unit cards screen showed the Models Editor on its first visit.
* After an update the browser could run the old scripts against the new
  page and stop at start-up until a hard refresh.
* The gunpowder minimum delay was read from the wrong slot.

## Licence

The toolkit is under the GPLv3. Versions up to v2.4.11 used parts of
Pfadfinder-Adam's Campaign Editor; every one of them is written anew in this
one, and four of its add-on scripts (Sack Settlement, Raze Settlement, Avoid
Growth, Player Diplomacy) are gone. See NOTICE.
