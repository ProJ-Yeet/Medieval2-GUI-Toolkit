# Medieval 2 GUI Toolkit v2.1.1

Point a fresh install at your Medieval II folder and the first mod in the list
is `americas` — a Kingdoms campaign, whose files are still inside
`data/packs/*.pack`. 2.1.0 picked it automatically, went looking for a unit
roster that is not on disk, and answered **HTTP 500**. Four times, because the
page retried. Then it sat on "Loading americas…" and never said anything else.

A mod's own missing or damaged file is not a fault in the toolkit, and it should
never have looked like one. This release makes every one of them answer in
words: which file, and — for a `battle_models.modeldb` that will not parse —
which entry, which line, and which number is wrong.

A subrelease: no new features, and it also carries the dropped-`<script>` fix
that was already in the tree.

---

## The short list

- **A mod that cannot be read says why, on screen.** "`data/export_descr_unit.txt`
  is not there" beats "HTTP 500", and it names the Kingdoms campaigns as what
  that usually means.
- **The Home card can explain it too.** `/api/mod_files` — the report whose whole
  job is to say which of a mod's files are missing — used to die on the same
  read it was reporting about. It parses nothing now, so the four packed
  campaigns show up as cards with every module greyed out and the missing files
  listed, instead of a card that never finished loading.
- **A modeldb that will not parse names the number to fix.** The file is
  length-prefixed, so one count that disagrees with what follows it puts the
  reader a field out of step and the read dies further down, on a word that is
  perfectly fine where it sits. 2.1.0 reported that word. 2.1.1 reports the
  entry, the line the *count* is on, and what it says versus what is really
  there.
- **A refusal is not retried four times.** Every non-OK reply was asked for four
  times, 200 ms apart, and then shown as the string "HTTP 500" — with the
  server's own explanation thrown away unread. Network drops and 502/503/504
  still retry, because those are the ones retrying fixes.
- **A failed load stays on screen.** The reason was drawn and then immediately
  painted over with "Loading …", so a mod that could not be read presented as
  one that was taking a long time.
- **The 🕑 Log button opens the log, not an empty one.** It was wired straight to
  the handler, so the click event arrived as the mode to filter by and
  `[object PointerEvent]` matched nothing.

---

## Everything in this release

### A mod file that is missing or damaged

`unittransfer/mod.py` gains `ModDataError`: a file this mod cannot be opened
without is either absent or unreadable, and both come back as one sentence
naming the file. It subclasses **both `OSError` and `ValueError`**, deliberately
— the code that copes with an incomplete mod already guards with `except
(OSError, AttributeError, ValueError)`, and a fresh `Exception` subclass would
have walked past every one of those guards and turned a tolerated absence into a
crash.

The server answers it with **409 and the sentence**. One `WARNING` line in the
log instead of a twenty-line traceback per attempt.

Two routes stopped parsing anything at all, because neither ever needed to:

- `/api/mod_files`, the Home page's readiness matrix
- `/api/eop_dirs`, the M2TWEOP folder panel — it still lists the folders for a
  mod whose roster cannot be read, and puts the reason where its two unit counts
  would have been

`Registry.describe()` is that: the `Mod` object, having read nothing. It
deliberately does not stamp the revalidation clock, so the next real `get()`
still warms the parsed databases inside the lock.

### Where a modeldb stopped making sense

`battle_models.modeldb` stores every name as `<length> <name>` and every list as
a count followed by that many records. Nothing in it is found by looking; it is
all counted from the field before. So the first wrong number does not fail — it
shifts everything after it by one field, and the read dies somewhere else
entirely.

The reader now carries where it was and what it had just read, and turns a
failure into a sentence with a place in it:

> Reading model entry #703 ('warg') it stopped making sense at line 27402,
> column 3: expected the length of a name here and found 'france'. … This
> entry's main texture list says it holds 2 (line 27396, column 1) and only 1
> read cleanly, so that count is the first number to check: a texture removed
> without lowering it reads exactly like this.

That is a real file. Two numbers on two lines, and the other 947 entries were
fine.

Where the count is not the culprit, the trail is searched for the length that
is: a name whose slice ends in the middle of the next token, or swallowed a line
break, is named with its line and column. Nothing about the parse itself
changed — a file that read cleanly before reads identically now.

### The page, when a request fails

- `api.get` reads the server's `{error}` body and puts *that* on the screen. A
  reply the server chose — a 404, a 409, a 500 — is an answer, not a blip, so it
  is not asked for three more times.
- `render()` distinguishes "still loading" from "the load failed", which it
  could not do before: both were "Loading …".
- The 14 places that printed `''+e` print the sentence without the `Error:` in
  front of it.

### Also in this release: the page that half-arrived

Already in the tree, and shipping here. `index.html` asks for two dozen scripts
at once, and the page loads whether or not they all arrive — a dropped one
leaves its module's functions simply absent, and the first call into it throws a
`ReferenceError` far from the cause. The startup screen read that as "the server
isn't running", while the server's log showed every request of that same second
answered.

- The server says `Connection: close`, because it does close. Left unsaid, the
  browser may write its next request into a socket about to be closed, and a
  socket closed with unread bytes in it is **reset** — throwing away a reply that
  was logged as a clean 200.
- The page notices a `<script>` that failed, refetches it in the order
  `index.html` lists them, and only gives up out loud, naming the file.
- If `core.js` itself is the file that never came, `boot.js` says so in plain
  DOM, since there is nothing else left to say it with.

### Under the hood

**Tests:** `tests/test_broken_mod_files.py`, 22 checks — the parser's located
message, `ModDataError` still being catchable by the guards that already existed,
and over HTTP: the 409 and its sentence, the readiness report answering for a
mod it cannot parse, the EOP panel's note, a damaged modeldb that still lists its
units, and the editor's refusal naming the file and the entry. It builds its own
mods, so it needs nothing installed.

`tests/test_modeldb_header.py`'s real-file sample now reports a file that will
not parse as a failed check and its sentence, rather than a traceback that takes
the rest of the run down with it.

**59 test modules.** The one machine-local check in the suite —
`test_modeldb_header`'s optional sample, read from a fixed path outside the
repo — reports whatever file is sitting there, which is the point of it.

---

**Next:** Phase 16, the Campaign Map Editor — 3.0.0.
