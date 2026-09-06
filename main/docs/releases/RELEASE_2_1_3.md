# v2.1.3

Disk usage. Together these removed 700 MB from Divide and Conquer.

## Added

* **Strat map tab.** Audits and cleans `descr_model_strat.txt` and
  `data/models_strat` the same way the modeldb was already handled. On Divide
  and Conquer: 4 MB of unreferenced models and 54 MB of unreferenced files.
* **Unit cards tab.** Hashes every unit and info card, removes art for units
  that no longer exist, and folds identical copies into the mercenary folder the
  engine already falls back to. On Divide and Conquer: 645 MB of 1.2 GB of card
  art. Where a mod ships a genuinely different card per faction, both are shown
  side by side and no action is taken automatically.
* **Fix ownership** and **All factions**, beside Clean up BMDB. Adds a texture
  record to a model entry for every faction that fields a unit using it, or for
  every faction in the mod. 212 gaps found in Divide and Conquer, 264 in Third
  Age Reforged.

## Changed

* The 3D viewer divider is draggable on both docks, with the width stored per
  screen. In BMDB mode the panel opens at half the window width, already
  visible.
* Mounts are drawn from a single texture rather than two composited together.
  Half the texture memory and one fewer decode, for an identical result.
