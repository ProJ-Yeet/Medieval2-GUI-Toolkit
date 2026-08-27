# v2.1.1

Error handling for mods that cannot be fully read. No new features.

A fresh install pointed at a Medieval II folder lists `americas` first, a
Kingdoms campaign whose files are still inside `.pack` archives. 2.1.0 selected
it automatically, looked for a unit roster that is not on disk, and returned
HTTP 500, then displayed "Loading americas" indefinitely.

## Fixed

* A mod that cannot be read now reports which file is missing, on screen, and
  identifies the Kingdoms campaigns as the usual cause.
* The Home readiness report no longer fails on the same read it is reporting on.
  Packed campaigns now appear as cards listing their missing files instead of
  never finishing loading.
* A `battle_models.modeldb` that fails to parse now reports the entry, the line
  holding the incorrect count, and the expected versus actual value. Previously
  it reported a valid line further down the file, because the format is
  length-prefixed and one bad count desynchronises everything after it.
* Failed requests are no longer retried four times and then reported as the
  string "HTTP 500" with the server's explanation discarded. Network errors and
  502/503/504 still retry.
* A failed load stays on screen instead of being overwritten by "Loading".
* The Log button opens the log rather than an empty one.
