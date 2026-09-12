# beta 2026-09-12b

**Everything in v2.3.1 with the campaign map switched on**, and everything on
beta 2026-09-12 before it. There is no new map work in this build: it is here
because the fix in v2.3.1 is the one that decides which of the two builds you
end up looking at, and this line is the one that loses by it.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## Fixed

* **Launching this build now opens this build.** The symptom was reported from
  the map side and it could only ever be seen from there: the beta was
  downloaded, launched, and came up without the Campaign Map in its menu.

  The server is detached, so a 2.x build opened earlier keeps running unseen on
  port 8756. The beta's launcher found a toolkit already answering there and
  reopened its window, which is correct for a second double-click of the same
  launcher and wrong for a different build. The two are identical apart from
  that one mode, so there was nothing on screen to catch it.

  A launch now asks the running server which build it is and where it came from,
  and reuses only its own. Anything else is reported, both builds named, and
  nothing is started. See the v2.3.1 note for the whole of it.

* **The build is written in the header**, beside the mod count, so a screenshot
  of this screen says whether the Campaign Map is absent because this is a 2.x
  build or absent because something is wrong. Click it for the credits.

## Still worth knowing before you use it

Unchanged from beta 2026-09-12: a save on the map screen writes to files the
game reads at campaign start, and some of what it writes shows up turns later
rather than at load. Everything is backed up into one set per save and 🕑 Log
undoes the whole set in one go.
