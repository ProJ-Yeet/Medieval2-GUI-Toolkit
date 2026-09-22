# beta 2026-09-22

**Everything in v2.3.7 with the campaign map switched on**, plus the map's own
half of the new Health screen.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## On the map

* **Health runs the map rules too.** On this build the Health screen adds the
  campaign map's own checks to the list - regions, markers, rivers, climates,
  resources, the mercenary pools - grouped with everything else by when they
  bite, and a row opens the map's validator on that finding. Findings that were
  already there when the map was stamped can be hidden with one tick.

## Also in this build

Everything in **v2.3.7**: the Health screen, change sets and the changed-files
export, the hidden resources line, Cultures, the sound banks and scripts, new
text entries, traits given from Lua, the interface size setting, the building
editor's folding lists and faction checklist, and the fixes to the code view
and to resource names. See `RELEASE_2_3_7.md`.
