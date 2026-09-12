# v2.3.1

One fix, and it is a fix to the thing that decides which toolkit you are looking
at. If you have ever downloaded a new build, launched it, and found the tool
exactly as it was, this is why.

## Fixed

* **Launching a build now opens that build.** The toolkit's server is detached
  on purpose - the console window closes and it keeps running behind you - so a
  copy you opened this morning is still serving on port 8756 this afternoon,
  with nothing on screen to say so. Launching a *second* copy found it there and
  did what it was written to do: reopened the running window instead of starting
  a server that could not bind the port.

  That is right for double-clicking the same launcher twice. It is wrong for two
  different builds, which is what it could not tell apart. Download this
  toolkit's **beta** next to a **2.x** build left running, launch the beta, and
  the browser opened the 2.x one - same address, same tool, same everything
  except the Campaign Map editor, which the 2.x line hides on purpose. Nothing
  looked broken. The build you opened was never the build you were looking at.

  A launch now asks the running server **which build it is and which folder it
  came from**. The same folder at the same version is still reopened, so a
  second double-click behaves as it always has. Anything else stops, names both
  builds and both folders, and starts nothing - the launcher window stays open
  with the two ways out of it: quit the one that is running, or give this one
  its own port.

## New

* **The build is written in the header**, beside the mod count. It has only ever
  been in Credits, three clicks in, which is three clicks too many for what it
  answers: **v2.3.1** and **beta 2026-09-12b** are the same tool with one screen
  different, so "the campaign map is missing" and "this is the 2.x build, which
  hides it" look identical until somebody can say which is on screen. Now a
  screenshot says it. Click it for the credits, as before.

## Where the rest of it went

Nothing on the campaign map changed in this build. **beta 2026-09-12b** is this
same fix with the campaign map editor switched on.
