"""Add-ons: ready-made scripts that bring the game something new, put in with their settings chosen in the tool.

An add-on is a Squirrel module (script/modules/<name>.nut - REX (Rome) and M2EX (Medieval II) both require() every
file there once the campaign is up, whatever mod runs). Besides the built-in ones, anyone's .nut can be added
(Add an add-on...): it is kept in the tool's own folder (addons/), its settings found by themselves, and Share...
packs it as a zip for others. Its settings are the 'local NAME = value' lines at the top of the file; the tool writes
the chosen values into those lines and nothing else, so a later version of the add-on keeps the same shape.
Installing and removing go through a Plan like every write: a backup, and Restore undoes it."""

import os
import re
import sys

from .scriptcompat import _ci
from . import i18n as _i18n


def assets_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "addons")


class Setting:
    """One setting: the variable in the script, how it is shown and what it takes.
    kind: 'bool', 'int', 'float', 'text', 'choice' (choices = [(value, label)]), 'list' (Squirrel array of strings),
    'set' (Squirrel table of names = true, written one per line)."""

    def __init__(self, var, kind, label, help, choices=None, when=None, signed=False):
        self.var, self.kind, self.label, self.help = var, kind, label, help
        self.choices = choices or []
        self.when = when            # (other var, [values]) - shown only then
        self.signed = signed        # an 'int' that may be below 0 (a move left / up)


WHO = [("player", "Only the player (the human)"),
       ("everyone", "Everyone - the player and every computer faction"),
       ("homeless", "Only factions without a town of their own (hordes, homeless) - player or computer"),
       ("player_and_homeless", "The player, and computer factions without a town (hordes)"),
       ("ai", "Only the computer's factions"),
       ("list", "Only the factions I pick")]


# Sack / Raze Settlement: the people a sacked town keeps at least (the scripts' RAZE_MIN_PEOPLE; the games' own level
# minimum is 400 - a town is never emptied), and what the kept chains mean (the scripts never tear down core_*)
MIN_PEOPLE = 600
KEEP_HELP = ("the governor's chain (core) always stays, listed or not - without it the town can never be built up "
             "again; %s by default, take them out if you like. Any building of the mod is read in the game, also "
             "one added or brought from another mod")


class Addon:
    """game: 'rome', 'medieval2' or 'both'; path: the script of an add-on someone added (else a built-in one in
    assets/addons); picks {var: 'chains' | 'units' | 'factions'}: settings picked from the mod's own names."""

    def __init__(self, key, title, game, file, summary, settings, needs, picks=None, path=None):
        self.key, self.title, self.game, self.file = key, title, game, file
        self.summary, self.settings, self.needs = summary, settings, needs
        self.picks, self.path = dict(picks or {}), path

    @property
    def own(self):
        """Added by the user (kept in the tool's addons/ folder), not built in."""
        return self.path is not None

    def fits(self, game):
        return self.game in ("both", game)

    def template(self):
        with open(self.path or os.path.join(assets_dir(), self.file), "rb") as f:
            return f.read().decode("utf-8")


class FileAddon(Addon):
    """An add-on that changes the mod's own files instead of putting a script in (no engine needed): its module has
    installed(mod), plan_install(plan, **values), plan_remove(plan). Its settings live in a short stand-in text, so
    the Add-ons page shows, previews and fills them as it does a script's."""
    files = True

    def __init__(self, key, title, module, summary, settings, defaults, game="both"):
        super().__init__(key, title, game, key + ".files", summary, settings,
                         "nothing - no engine: it changes the mod's own files, on any mod of %s" % (
                             "both games" if game == "both" else "Medieval II" if game == "medieval2" else "Rome"))
        self.module, self.defaults = module, defaults

    def template(self):
        return "".join("local %s = %s\n" % (k, v) for k, v in self.defaults.items())

    def code(self):
        from . import scriptfiles
        return getattr(scriptfiles, self.module)


def is_files(addon):
    return getattr(addon, "files", False)


ADDONS = [
    Addon("sack_settlement", "Sack Settlement (Rome)", "rome", "sack_settlement.nut",
          "A 4th choice on the capture scroll, under Occupy / Enslave / Exterminate: Sack Settlement. The town is "
          "exterminated the game's own way, every building but the kept ones is torn down, you get a reward, and "
          "the ruins go to the rebels (with a rebel garrison the game raises itself) - land you do not want to hold "
          "is burned and left to regrow. The computer's factions allowed below sack when they exterminate.",
          [Setting("RAZE_ENABLED", "bool", "Sacking on", "off keeps the file but does nothing"),
           Setting("RAZE_WHO", "choice", "Who may sack", "the player picks it on the capture scroll; a computer "
                   "faction allowed here sacks whenever it exterminates a town", WHO),
           Setting("RAZE_FACTIONS", "list", "The factions", "for 'Only the factions I pick'",
                   when=("RAZE_WHO", ["list"])),
           Setting("RAZE_GIVE_TO_REBELS", "bool", "Ruins go to the rebels", "off: the sacked town stays yours"),
           Setting("RAZE_REBEL_GARRISON", "bool", "Rebels get a garrison", "the game raises it from the region's "
                   "rebel type (descr_rebel_factions.txt)"),
           Setting("RAZE_GOLD_PER_BUILDING", "int", "Money per building torn down", "added to the extermination's"),
           Setting("RAZE_GOLD_PER_CITIZEN", "int", "Money per inhabitant", "for each person the sack removes"),
           Setting("RAZE_PEOPLE_LEFT", "int", "People left in the ruins", "%d at least - a town cannot be wiped "
                   "off the map" % MIN_PEOPLE),
           Setting("RAZE_KEEP_CHAINS", "set", "Building chains never torn down", KEEP_HELP % "walls and roads"),
           Setting("RAZE_DEFAULT_REBEL_UNITS", "list", "Rebel units if the game raises none", "unit types of this "
                   "mod's export_descr_unit.txt; empty = none"),
           Setting("RAZE_BUTTON", "bool", "The 4th button", "off: Exterminate asks Yes / No to sack instead"),
           Setting("RAZE_BUTTON_LABEL", "text", "Button text", "the words on the button"),
           Setting("RAZE_BUTTON_TIP", "text", "Button tooltip", "shown when the mouse is over it; {gold}, "
                   "{buildings}, {people} = what this sack brings, filled for the town just taken")],
          "REX (Rome: Total War). Vanilla Rome has no scripts - the add-on then does nothing.",
          picks={"RAZE_KEEP_CHAINS": "chains", "RAZE_DEFAULT_REBEL_UNITS": "units", "RAZE_FACTIONS": "factions"}),
    Addon("raze_settlement", "Sack Settlement (Medieval II)", "medieval2", "raze_settlement.nut",
          "A 4th choice on the capture scroll, under Occupy / Sack / Exterminate - its button says Raze Settlement "
          "(the game's own second button is already called Sack Settlement; change the words below), drawn from the "
          "game's own button pieces like the three above it. The town is exterminated the game's own way, "
          "every building but the kept ones is torn down, most people are gone, you get a reward, and the ruins go "
          "to the rebels with a fresh rebel garrison M2EX raises itself - the Medieval II brother of Rome's Sack "
          "Settlement, the same script engine. The computer's factions allowed below raze when they exterminate.",
          [Setting("RAZE_ENABLED", "bool", "Razing on", "off keeps the file but does nothing"),
           Setting("RAZE_WHO", "choice", "Who may raze", "the player picks it on the capture scroll; a computer "
                   "faction allowed here razes whenever it exterminates a town", WHO),
           Setting("RAZE_FACTIONS", "list", "The factions", "for 'Only the factions I pick'",
                   when=("RAZE_WHO", ["list"])),
           Setting("RAZE_GIVE_TO_REBELS", "bool", "Ruins go to the rebels", "off: the razed town stays yours"),
           Setting("RAZE_REBEL_GARRISON", "bool", "Rebels get a garrison", "the game raises it from the region's "
                   "rebel type (descr_rebel_factions.txt)"),
           Setting("RAZE_GOLD_PER_BUILDING", "int", "Money per building torn down", "added to the extermination's"),
           Setting("RAZE_GOLD_PER_CITIZEN", "int", "Money per inhabitant", "for each person the raze removes"),
           Setting("RAZE_PEOPLE_LEFT", "int", "People left in the ruins", "%d at least - a town cannot be wiped "
                   "off the map" % MIN_PEOPLE),
           Setting("RAZE_KEEP_CHAINS", "set", "Building chains never torn down", KEEP_HELP % "roads (the walls are "
                   "levels of the core chains in Medieval II)"),
           Setting("RAZE_DEFAULT_REBEL_UNITS", "list", "Rebel units if the game raises none", "unit types of this "
                   "mod's export_descr_unit.txt; empty = none"),
           Setting("RAZE_BUTTON", "bool", "The 4th button", "off: Exterminate asks Yes / No to raze instead"),
           Setting("RAZE_BUTTON_LABEL", "text", "Button text", "the words on the button"),
           Setting("RAZE_BUTTON_TIP", "text", "Button tooltip", "shown when the mouse is over it, as the game's "
                   "own three buttons have; {gold}, {buildings}, {people} = what this raze brings; empty = none")],
          "M2EX (Medieval II: Total War) - its own scripts (script/main.nut) load every .nut of the game's "
          "script/modules, whatever mod runs. Vanilla Medieval II runs no scripts - the add-on then does nothing.",
          picks={"RAZE_KEEP_CHAINS": "chains", "RAZE_DEFAULT_REBEL_UNITS": "units", "RAZE_FACTIONS": "factions"}),
    Addon("avoid_growth", "Avoid Growth", "both", "avoid_growth.nut",
          "A tick box on the settlement scroll of each of your towns, drawn with the game's own small box and tick "
          "(in Medieval II in the row of its own ticks, right of Recruitment). Tick "
          "it and the people the town has now become its ceiling: it never grows past it, still loses people the "
          "usual way (recruiting, battles, plague) and grows back - but only up to the ceiling. A border town stays "
          "the village, town or city it is: put it on auto-manage and forget it. Untick to let it grow again. The "
          "ceilings are kept in the saved game; a town lost to another faction drops its tick. Console: "
          "sq ::avoid_growth_list().",
          [Setting("AG_ENABLED", "bool", "Avoid Growth on", "off keeps the file but does nothing"),
           Setting("AG_LABEL", "text", "Words beside the tick", "what the scroll says"),
           Setting("AG_TIP", "text", "Tooltip", "shown when the mouse is over it, unticked"),
           Setting("AG_TIP_ON", "text", "Tooltip while ticked", "{cap} = the ceiling (the people it keeps at most)"),
           Setting("AG_SHOW_CAP", "bool", "Show the ceiling beside the words too",
                   "'(at most 5000)' beside the words while ticked - the tooltip says it anyway"),
           Setting("AG_OFFSET_X", "int", "Move the tick right", "in the game's 1024 x 768 units; below 0 = left",
                   signed=True),
           Setting("AG_OFFSET_Y", "int", "Move the tick down", "below 0 = up", signed=True)],
          "REX (Rome: Total War) or M2EX (Medieval II: Total War) - their own scripts (script/main.nut) load every "
          ".nut of the game's script/modules, whatever mod runs. The original exes run no scripts - the add-on then "
          "does nothing."),
    Addon("recruit_order", "Recruitment Order", "both", "recruit_order.nut",
          "A town's recruitment panel in a fixed order: infantry, then archers / slingers / skirmishers, cavalry, "
          "horse archers, chariots, elephants, war dogs and pigs, siege, ships - in each kind the dearest first (or the cheapest). The game sorts the "
          "panel itself by each unit's custom-battle price (stat_cost's 6th number); during your turn the add-on "
          "gives every unit that number in the order above and puts the real numbers back before every battle and "
          "at the end of your turn, so the computer's turns, battles and autoresolve keep the real values. Nothing "
          "is written into the mod's files or the saved game. Ships always stand after the land units and agents "
          "last - the game keeps them apart; in Medieval II the game's own kind blocks are switched off (a setting). "
          "Console: sq ::recruit_order_list(), sq ::recruit_order_off().",
          [Setting("RO_ENABLED", "bool", "Recruitment Order on", "off keeps the file but does nothing"),
           Setting("RO_ORDER", "choice", "In each kind", "which units stand first among the same kind",
                   choices=[("dearest", "The dearest first (the strongest top left)"),
                            ("cheapest", "The cheapest first")]),
           Setting("RO_ONE_PANEL", "bool", "Medieval II: one panel for every kind",
                   "the game's own kind blocks off (recruitment_sort_simple), so the whole panel follows the order; "
                   "Rome has no blocks")],
          "REX (Rome: Total War) or M2EX (Medieval II: Total War) - their own scripts (script/main.nut) load every "
          ".nut of the game's script/modules, whatever mod runs. The original exes run no scripts - the add-on then "
          "does nothing."),
    Addon("player_diplomacy", "Player Diplomacy", "rome", "player_diplomacy.nut",
          "The computer's factions stop attacking you when it makes no sense: after a ceasefire they keep the peace "
          "for some turns (a war they declare in that time is undone), your client kingdoms never plan to invade "
          "you, and a faction far weaker than you does not either (its allies already at war with you count on its "
          "side, so a big alliance still comes). Only how the computer treats YOU changes; its wars with each other "
          "stay as they are. The console: sq ::truce_status(), sq ::truce_set(\"egypt\", 10), sq ::power(\"egypt\").",
          [Setting("TRUCE_TURNS", "int", "Turns a ceasefire holds", "your turns; 0 = no truce rule"),
           Setting("TRUCE_STEER_AI", "bool", "The computer plans no invasion of you in a truce", "the main rule"),
           Setting("TRUCE_RESTORE_PEACE", "bool", "A war declared in a truce is undone", "peace put back at once"),
           Setting("CLIENT_NEVER_ATTACK", "bool", "Client kingdoms never attack you", "while they are your "
                   "protectorates"),
           Setting("DETER_ENABLED", "bool", "Far weaker factions do not attack you", "by strength below"),
           Setting("DETER_RATIO", "float", "You this many times stronger", "units in all armies and garrisons, "
                   "plus the settlements below; 3.0 = three times"),
           Setting("STRENGTH_PER_SETTLEMENT", "int", "A settlement counts as units", "in that strength"),
           Setting("COALITIONS_COUNT", "bool", "Allies at war with you add their strength", "so small factions "
                   "still join a big alliance against you")],
          "REX (Rome: Total War), its campaign AI hook (calculateLtgd). Vanilla Rome has no scripts - the add-on "
          "then does nothing."),
    FileAddon("upkeep_x2", "Upkeep x 2 (no huge armies)", "upkeep",
              "Every unit's upkeep multiplied (x 2 by default), on any mod of both games - no engine needed. Big "
              "armies cost what they should: only a big income keeps them. The game reads the upkeep from "
              "export_descr_unit.txt, so it shows the real, higher numbers everywhere. Take it out puts back exactly "
              "the old numbers (kept in toolkit_upkeep.json beside that file).",
              [Setting("FACTOR", "float", "Upkeep x", "2 doubles it, 1.5 adds half, 3 triples it")],
              {"FACTOR": "2.0"}),
    FileAddon("one_recruit_grid", "One Recruitment Grid (Medieval II)", "onegrid",
              "A town's recruitment panel as one grid read row by row, as in Rome, instead of the game's blocks by "
              "kind (infantry, missiles, cavalry ... each in its own columns). Any Medieval II, no engine needed: "
              "it sets recruitment_sort_simple in descr_campaign_db.xml; Take it out puts the line back as it was. "
              "In that grid the game itself shows the agents first, then the ships, then the land units - only an "
              "engine change can move them.",
              [], {}, game="medieval2"),
]


# add-ons made one per game shown as ONE row, the part for the loaded game put in (the user, 2026-10-16, #310: 'one
# module that knows the game and puts in only the part that game needs - one name, as Sack Settlement')
FAMILIES = {"sack_settlement": "Sack Settlement", "raze_settlement": "Sack Settlement",
            "recruit_order": "Recruitment Order", "one_recruit_grid": "Recruitment Order"}
# what each part is called on its family's page when two parts fit one game
PART_WORDS = {"recruit_order": "the order of the cards (REX / M2EX)",
              "one_recruit_grid": "one grid as in Rome (no engine needed)"}


def rows(addons):
    """[(title, [addon, ...])]: the add-ons of one family in one row (first place kept), the others alone."""
    out, at = [], {}
    for a in addons:
        fam = FAMILIES.get(a.key)
        if fam is None:
            out.append((a.title, [a]))
        elif fam in at:
            out[at[fam]][1].append(a)
        else:
            at[fam] = len(out)
            out.append((fam, [a]))
    return out


def by_key(key):
    return next(a for a in library() if a.key == key)


# ---------------------------------------------------------------------------
# Anyone's add-on: its settings read from the script itself
# ---------------------------------------------------------------------------
RE_LOCAL = re.compile(r"^local\s+([A-Z][A-Z0-9_]*)\s*=", re.M)
RE_TAG = re.compile(r"^//[ \t]*@(\w+)[ \t]*(.*?)[ \t]*$", re.M)      # one line each (an empty tag took the next line)
NAME_KINDS = ("chains", "units", "factions")
SCRIPT_CAP = 1 << 20


def _seq(item, open_, close):
    """A bracketed list of items apart by a comma or by white space, a comma after the last allowed - written so
    that a text can be matched in one way only (the older '\\s*,?\\s*' between items backtracked exponentially
    on a long line of spaces: CodeQL py/redos)."""
    return r"%s\s*(?:%s(?:(?:\s*,\s*|\s+)%s)*(?:\s*,)?\s*)?%s" % (open_, item, item, close)


def _kind(raw):
    """The setting kind a literal value asks for, or None (not a setting the tool can show)."""
    v = raw.strip()
    if v in ("true", "false"):
        return "bool"
    if re.fullmatch(r"-?\d+", v):
        return "int"
    if re.fullmatch(r'"(?:[^"\\]|\\.)*"', v):
        return "text"
    if v.startswith("[") and re.fullmatch(_seq(r'"(?:[^"\\]|\\.)*"', r"\[", r"\]"), v, re.S):
        return "list"
    if v.startswith("{") and re.fullmatch(_seq(r"[A-Za-z_]\w*\s*=\s*true", r"\{", r"\}"),
                                          re.sub(r"//[^\n]*", "", v), re.S):
        return "set"
    return None


def _help(text, start, end):
    """A setting's help: the // comment after its value on the same line, else the // lines right above it."""
    line_end = text.find("\n", end)
    tail = text[end:line_end if line_end >= 0 else len(text)]
    m = re.match(r"\s*,?\s*//\s*(.*)", tail)
    if m and m.group(1).strip():
        return m.group(1).strip()
    above = text[:text.rfind("\n", 0, start) + 1].rstrip("\n").split("\n")
    out = []
    for line in reversed(above):
        s = line.strip()
        if not s.startswith("//") or s.startswith("// @") or s.startswith("//@") or set(s) <= set("/=- "):
            break
        out.append(s[2:].strip())
    return " ".join(reversed(out))


def from_script(text, file, path=None):
    """An Addon made from anyone's script: the title, game, summary, needs and name pickers from optional header
    lines (// @title ..., // @game rome|medieval2|both, // @summary ..., // @needs ..., // @settings A, B,
    // @pick VAR chains|units|factions, // @label VAR words), its settings from the UPPER_CASE `local NAME = value`
    lines at the top level (true / false, a whole number, "text", ["a", "b"], { a = true }) - or only those
    @settings names; // @signed A, B: whole numbers that may be below 0 (the Module builder's money given or taken)."""
    tags = {}
    picks, labels = {}, {}
    for m in RE_TAG.finditer(text):
        key, val = m.group(1).lower(), m.group(2)
        if key == "pick" and len(val.split()) == 2 and val.split()[1] in NAME_KINDS:
            picks[val.split()[0]] = val.split()[1]
        elif key == "label" and len(val.split(None, 1)) == 2:
            labels[val.split(None, 1)[0]] = val.split(None, 1)[1]
        else:
            tags.setdefault(key, val)
    only = [x.strip() for x in tags.get("settings", "").split(",") if x.strip()]
    signed = {x.strip() for x in tags.get("signed", "").split(",") if x.strip()}
    settings = []
    for m in RE_LOCAL.finditer(text):
        var = m.group(1)
        if (only and var not in only) or any(s.var == var for s in settings):
            continue
        sp = _span(text, var)
        if not sp:
            continue
        kind = _kind(text[sp[0]:sp[1]])
        if kind is None:
            continue
        label = labels.get(var) or var.replace("_", " ").strip().capitalize()
        settings.append(Setting(var, kind, label, _help(text, m.start(), sp[1]), signed=var in signed))
    stem = os.path.splitext(os.path.basename(file))[0]
    first = next((l.strip("/ \t=-") for l in text.splitlines()[:12]
                  if l.strip().startswith("//") and l.strip("/ \t=-") and "@" not in l[:4]), "")
    game = tags.get("game", "both").lower()
    if game not in ("rome", "medieval2", "both"):
        game = "both"
    # no @title: the words before ' - ' on the first comment line ("// Border Tolls - a toll at ..."), else the file
    title = tags.get("title") or (first.split(" - ")[0].strip() if " - " in first else "") or \
        stem.replace("_", " ").title()
    return Addon(stem, title, game, os.path.basename(file),
                 tags.get("summary") or first or "An add-on script (%s)." % os.path.basename(file), settings,
                 tags.get("needs") or "REX (Rome) or M2EX (Medieval II): the script goes into script/modules, which "
                                      "they load by themselves. The original exes run no scripts.",
                 picks=picks, path=path)


def library_dir():
    """The toolkit's own folder for add-ons someone added and modules the builder made."""
    from .scriptcompat import tool_dir
    return str(tool_dir())


def library():
    """Every add-on the tool knows: the built-in ones, then the added ones (by title)."""
    out = list(ADDONS)
    d = library_dir()
    if d and os.path.isdir(d):
        own = []
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if n.lower().endswith(".nut") and os.path.isfile(p) and os.path.getsize(p) <= SCRIPT_CAP:
                try:
                    with open(p, "rb") as f:
                        a = from_script(f.read().decode("utf-8", "replace"), n, p)
                except OSError:
                    continue
                if all(a.key != b.key for b in out):
                    own.append(a)
        out += sorted(own, key=lambda a: a.title.lower())
    return out


def add_to_library(src):
    """Add-ons from a .nut or a .zip (every .nut in it, by file name only - nothing outside addons/ is written).
    Returns [Addon]; raises ValueError in plain words."""
    import zipfile
    d = library_dir()
    if not d:
        raise ValueError(_i18n.msg("eng.scriptaddons.the_tool_has_no_folder_of", "the tool has no folder of its own to keep add-ons in"))
    got = []                                           # (file name, bytes)
    low = src.lower()
    if low.endswith(".nut"):
        if os.path.getsize(src) > SCRIPT_CAP:
            raise ValueError(_i18n.msg("eng.scriptaddons.over_1_mb", "{name} is over 1 MB - not a script", name=os.path.basename(src)))
        with open(src, "rb") as f:
            got.append((os.path.basename(src), f.read()))
    elif low.endswith(".zip"):
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                name = os.path.basename(info.filename.replace("\\", "/"))
                if name.lower().endswith(".nut") and not info.is_dir() and info.file_size <= SCRIPT_CAP:
                    got.append((name, z.read(info)))
    else:
        raise ValueError(_i18n.msg("eng.scriptaddons.an_add_on_is_a_squirrel", "an add-on is a Squirrel script (.nut) or a zip with one - REX and M2EX load those"))
    if not got:
        raise ValueError(_i18n.msg("eng.scriptaddons.no_nut_script", "no .nut script in {name}", name=os.path.basename(src)))
    built = {a.file.lower() for a in ADDONS}
    os.makedirs(d, exist_ok=True)
    out = []
    for name, data in got:
        if not re.fullmatch(r"[\w.-]+\.nut", name, re.I):
            raise ValueError(_i18n.msg("eng.scriptaddons.bad_script_name", "{name}: a script's name is letters, digits, _ - and . only", name=name))
        if name.lower() in built:
            raise ValueError(_i18n.msg("eng.scriptaddons.built_in_already", "{name} is built in already (it is in the list)", name=name))
        dst = os.path.join(d, name)
        with open(dst, "wb") as f:
            f.write(data)
        out.append(from_script(data.decode("utf-8", "replace"), name, dst))
    return out


def remove_from_library(addon):
    """An added add-on off the list (its script in addons/ deleted; one put into a game stays there)."""
    if not addon.own:
        raise ValueError(_i18n.msg("eng.scriptaddons.built_in", "{name} is built in", name=addon.title))
    os.remove(addon.path)


def share(addon, out, values=None):
    """A zip to give others: the script (with the settings picked here, if given) and a README.txt saying what it
    is and where it goes."""
    import zipfile
    text = render(addon, addon.template(), values) if values else addon.template()
    readme = "\n".join([
        addon.title, "", addon.summary, "", "Needs: " + addon.needs, "",
        "Put it in with RTW & M2TW Campaign Editor: Add-ons > Add an add-on... > this zip, pick the settings, "
        "Put it in. By hand: copy %s into <game folder>/script/modules/." % addon.file, ""])
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(addon.file, text)
        z.writestr("README.txt", readme)
    return out


# ---------------------------------------------------------------------------
# The script's setting lines
# ---------------------------------------------------------------------------
def _span(text, var):
    """(start, end) of the value of 'local VAR = value' (a { } or [ ] value may run over lines), or None."""
    m = re.search(r"^local\s+%s\s*=\s*" % re.escape(var), text, re.M)
    if not m:
        return None
    start = m.end()
    if text[start] in "{[":
        close = "}" if text[start] == "{" else "]"
        end = text.index(close, start) + 1
    else:
        end = start
        quoted = False
        while end < len(text) and text[end] != "\n":
            c = text[end]
            if c == '"' and text[end - 1] != "\\":
                quoted = not quoted
            if not quoted and text[end:end + 2] in ("//", "--"):
                break
            end += 1
        while end > start and text[end - 1] in " \t\r":
            end -= 1
    return start, end


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def read_settings(addon, text):
    """{var: value} from a script: bool -> True/False, int -> int, text / choice -> str, list / set -> [str]."""
    out = {}
    for s in addon.settings:
        sp = _span(text, s.var)
        if not sp:
            continue
        raw = text[sp[0]:sp[1]]
        if s.kind == "bool":
            out[s.var] = raw.strip() == "true"
        elif s.kind == "int":
            try:
                out[s.var] = int(raw.strip())
            except ValueError:
                out[s.var] = 0
        elif s.kind == "float":
            try:
                out[s.var] = float(raw.strip())
            except ValueError:
                out[s.var] = 0.0
        elif s.kind == "list":
            out[s.var] = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
        elif s.kind == "set":
            body = re.sub(r"(//|--)[^\n]*", "", raw)
            out[s.var] = re.findall(r"([A-Za-z_][\w]*)\s*=\s*true", body)
        else:
            out[s.var] = _unquote(raw)
    return out


def _quote(v):
    return '"%s"' % str(v).replace("\\", "\\\\").replace('"', '\\"')


def _render(s, v, old):
    if s.kind == "bool":
        return "true" if v else "false"
    if s.kind == "int":
        return str(int(v))
    if s.kind == "float":
        return repr(float(v))                      # 3.0, never 3 (Squirrel would make it a whole number)
    if s.kind == "list":
        return "[" + ", ".join(_quote(x) for x in v) + "]"
    if s.kind == "set":
        indent = re.search(r"\n([ \t]+)\S", old)
        ind = indent.group(1) if indent else "    "
        return "{\n" + "".join("%s%s = true,\n" % (ind, x) for x in v) + "}"
    return _quote(v)


def mod_names(mod, what):
    """The names a setting picks from, read from the mod: 'chains' (export_descr_buildings.txt), 'units'
    (export_descr_unit.txt). [] when the file is not there."""
    try:
        if what == "chains":
            from .scriptcompat import read_buildings
            return [b.name for b in read_buildings(mod)]
        if what == "units":
            from .scriptcompat import read_units
            return [u.type for u in read_units(mod)]
        if what == "factions":
            return [n for n, _ in mod.factions() if n != "slave"]
    except Exception:
        return []
    return []


def check(addon, values, mod=None):
    """[problem] with the chosen values (empty = fine). With the mod, names are checked against its files: a kept
    chain or a rebel unit the mod does not have would do nothing (the governor's chain would then be torn down);
    and the add-on's own code already pasted into the mod's scripts is refused (it would run twice)."""
    out = []
    if is_files(addon):
        return out
    if mod is not None:
        strays = stray_copies(mod, addon)
        dup = [p for p in already_in_scripts(mod, addon) if p not in strays]
        if dup:
            out.append("this mod's own %s already holds the %s code - it would run twice (two buttons); take it out "
                       "of that file first, or leave the add-on out" % (
                           ", ".join(os.path.relpath(p, os.path.dirname(os.path.abspath(mod.data))) for p in dup),
                           addon.title))
    if mod is not None:
        for var, what in addon.picks.items():
            if what not in ("chains", "units"):
                continue
            have = mod_names(mod, what)
            if have and values.get(var):
                low = {x.lower() for x in have}
                wrong = [x for x in values[var] if x.lower() not in low]
                if wrong:
                    out.append("%s: %s not in this mod's %s" % (
                        next(s.label for s in addon.settings if s.var == var), ", ".join(wrong),
                        "export_descr_buildings.txt" if what == "chains" else "export_descr_unit.txt"))
    name = re.compile(r"^[A-Za-z_][\w]*$")
    for s in addon.settings:
        v = values.get(s.var)
        if v is None:
            continue
        if s.kind == "int" and (not isinstance(v, int) or isinstance(v, bool) or (v < 0 and not s.signed)):
            out.append("%s: a whole number%s" % (s.label, "" if s.signed else ", 0 or more"))
        if s.kind == "float" and (not isinstance(v, (int, float)) or v < 0):
            out.append("%s: a number, 0 or more (like 3.0)" % s.label)
        if s.kind == "set" and any(not name.match(x) for x in v):
            out.append("%s: names of letters, digits and _" % s.label)
        if s.kind == "choice" and v not in [c for c, _ in s.choices]:
            out.append("%s: pick one of the list" % s.label)
    if isinstance(values.get("RAZE_PEOPLE_LEFT"), int) and values["RAZE_PEOPLE_LEFT"] < MIN_PEOPLE:
        out.append("People left in the ruins: %d at least - a town cannot be wiped off the map" % MIN_PEOPLE)
    if values.get("RAZE_WHO") == "list" and not values.get("RAZE_FACTIONS"):
        out.append("%s: pick at least one faction" % next(
            (s.label for s in addon.settings if s.var == "RAZE_WHO"), "Who may"))
    return out


def render(addon, text, values):
    """The script with the chosen values written into their lines (the rest byte for byte)."""
    have = read_settings(addon, text)
    for s in sorted(addon.settings, key=lambda s: -(_span(text, s.var) or (0, 0))[0]):
        if s.var not in values or (s.var in have and have[s.var] == values[s.var]):
            continue                    # an unchanged value keeps its line as it is (comments included)
        sp = _span(text, s.var)
        if not sp:
            raise ValueError(_i18n.msg("eng.scriptaddons.no_var_line", "the add-on's script has no {var} line", var=s.var))
        text = text[:sp[0]] + _render(s, values[s.var], text[sp[0]:sp[1]]) + text[sp[1]:]
    return text


# ---------------------------------------------------------------------------
# Where it goes
# ---------------------------------------------------------------------------
# Up to 0.29.2 the Medieval II Raze Settlement was an EOP-style Lua script in the mod's eopData/eopScripts, loaded by a
# line in luaPluginScript.lua; the native .nut replaces it, and putting it in (or taking it out) takes the Lua copy and
# its line out too - both would draw a button.
OLD_LUA = {"raze_settlement": "raze_settlement.lua"}
OLD_LUA_DIR = ("eopData", "eopScripts")
OLD_LUA_ENTRY = "luaPluginScript.lua"
OLD_LUA_MARK = b"added by RTW & M2TW Campaign Editor: "


def loads_modules(folder):
    """True when <folder>/script/main.nut requires every .nut of its script/modules (REX's own squi plugin does:
    scripting.listModules("modules")). A mod's own script plugin (a manifest.nut and main.nut of its own, like HLR's)
    does not - a module put beside it is never run."""
    sd = _ci(folder, "script") if folder else None
    main = _ci(sd, "main.nut") if sd else None
    if not main:
        return False
    try:
        with open(main, "rb") as fh:
            return b"listModules" in fh.read()
    except OSError:
        return False


def target(mod, addon):
    if is_files(addon):
        try:
            return addon.code().mark_path(mod)
        except ValueError:
            return os.path.join(mod.data, "export_descr_unit.txt")
    return _script_target(mod, addon)


def _script_target(mod, addon):
    """Where the add-on goes: <game>/script/modules/<file> - REX's own scripts (script/main.nut, the squi plugin)
    require every .nut there for whatever mod runs (a tester's HLR has a script plugin of its own whose main.nut
    loads no modules: an add-on in the mod's script/modules never ran). The mod's own script/modules only when the
    mod's main.nut loads them, or the game folder is not known. M2EX's script/main.nut does the same for Medieval II."""
    root = os.path.dirname(os.path.abspath(mod.data))
    game = None
    try:
        from .scriptcompat import game_of
        game = game_of(mod.data)
    except Exception:
        pass
    if loads_modules(root):
        return os.path.join(root, "script", "modules", addon.file)
    if game and (loads_modules(game) or _ci(game, "script")):
        return os.path.join(game, "script", "modules", addon.file)
    return os.path.join(root, "script", "modules", addon.file)


def marker(addon):
    """A line only this add-on's code has (its log prefix, 'local PREFIX = "[SACK] "'), or None."""
    m = re.search(r'^\s*local\s+PREFIX\s*=\s*"([^"]+)"', addon.template(), re.M)
    return m.group(1).strip() if m else None


def already_in_scripts(mod, addon):
    """[the mod's own script files (not its modules folder) that already hold this add-on's code] - pasted into a
    mod's main.nut, a second copy as an add-on would run it twice (two buttons on the capture scroll)."""
    mk = marker(addon)
    # its settings' own lines too ('local RAZE_BUTTON_LABEL = ...'): code pasted into a mod's main.nut keeps them
    # while it logs under the mod's prefix
    decl = [re.compile(r"^\s*local\s+%s\s*=" % re.escape(x.var), re.M) for x in addon.settings]
    root = os.path.dirname(os.path.abspath(mod.data))
    sd = _ci(root, "script")
    if not (mk or decl) or not sd:
        return []
    out = []
    for dirpath, dirs, files in os.walk(sd):
        dirs[:] = [d for d in dirs if d.lower() != "modules"]
        for f in files:
            if not f.lower().endswith(".nut"):
                continue
            p = os.path.join(dirpath, f)
            try:
                with open(p, "rb") as fh:
                    text = fh.read().decode("utf-8", "replace")
            except OSError:
                continue
            if (mk and mk in text) or sum(1 for r in decl if r.search(text)) >= min(2, len(decl)):
                out.append(p)
    return out


def stray_copies(mod, addon):
    """[the add-on's own file (its file name) lying in the scripts folder outside script/modules] - an older copy put
    there by hand. Put it in moves it where the engine runs add-ons, Take it out takes it away, and the Add-ons page
    says it is in the game (a tester: 'it is in my game, the page says not put in, and there is no button to take it
    out' - the install was refused: it would run twice)."""
    if is_files(addon):
        return []
    name = addon.file.lower()
    return [p for p in already_in_scripts(mod, addon) if os.path.basename(p).lower() == name]


def plan_mod(mod, addon):
    """The ModData whose folder holds the add-on's place (backups live beside it): the mod itself, or the game's own
    data when the add-on goes into the game's script folder (a mod without scripts of its own)."""
    from .moddata import ModData
    root = os.path.dirname(os.path.abspath(mod.data))
    dst = os.path.abspath(target(mod, addon))
    if dst.startswith(os.path.join(root, "")):
        return mod
    game_root = os.path.dirname(os.path.dirname(os.path.dirname(dst)))
    try:
        return ModData(os.path.join(game_root, "data"))
    except (FileNotFoundError, OSError):
        # Medieval II keeps most of its data in packs: the game's data folder has no descr_sm_factions.txt (a tester:
        # 'D:\Medieval II Total War\data holds only the files this mod changes' - nothing put in). The mod's own
        # backup holds the game-folder file too (plan.stored), so the mod carries the write.
        return mod


def installed(mod, addon):
    """{var: value} of the add-on as it is installed (also an older copy outside script/modules - stray_copies),
    or None."""
    if is_files(addon):
        return addon.code().installed(mod)
    p = target(mod, addon)
    if not os.path.isfile(p):
        strays = stray_copies(mod, addon)
        if not strays:
            return None
        p = strays[0]
    with open(p, "rb") as f:
        return read_settings(addon, f.read().decode("utf-8", "replace"))


GAME_LINE = re.compile(r'(local\s+CE_GAME\s*=\s*")auto(")')


def with_game(text, mod):
    """A script for both games that asks which one runs it (`local CE_GAME = "auto"`) told the game it is put in:
    "rome" (Rome and Barbarian Invasion share the settlement scroll) or "medieval2" - its own guess took Barbarian
    Invasion for Medieval II (Avoid Growth's tick in the wrong place)."""
    if mod is None or not GAME_LINE.search(text):
        return text
    from .scriptcompat import game_kind
    return GAME_LINE.sub(lambda m: m.group(1) + ("medieval2" if game_kind(mod) == "medieval2" else "rome") + m.group(2),
                         text, count=1)


def _same_script(have, want):
    """The two scripts alike but for line ends, trailing spaces and the test mod's mark line."""
    def norm(t):
        return "\n".join(l.rstrip() for l in t.replace("\r\n", "\n").split("\n")
                         if "@put_in_by CE_Test" not in l).strip()
    return norm(have) == norm(want)


def outdated(mod):
    """[{'addon', 'path', 'values', 'mark'}]: the built-in add-ons in the game (where the engine runs them, or an
    older copy beside) whose file is not what this version of the editor writes with the same settings - an older
    version. The user (2026-10-09): 'still the same error in the console' - an older Avoid Growth drew the script
    console in its own font and wrote 'font autoscale: game font ...' there; Update it fixed one add-on at a time,
    and nothing said which ones were old. Offered on Load (gamefix 'old_addons') and named in the Add-ons window."""
    from .scriptcompat import game_kind
    from .scriptcompat import TEST_MARK
    try:
        kind = game_kind(mod)
    except Exception:
        return []
    out = []
    for a in ADDONS:
        if not a.fits(kind) or is_files(a):
            continue
        p = target(mod, a)
        if not os.path.isfile(p):
            strays = stray_copies(mod, a)
            if not strays:
                continue
            p = strays[0]
        try:
            with open(p, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
            values = read_settings(a, text)
            want = with_game(render(a, a.template(), values), mod)
        except (OSError, ValueError):
            continue
        if _same_script(text, want) and p == target(mod, a):
            continue
        out.append({"addon": a, "path": p, "values": values,
                    "mark": TEST_MARK if TEST_MARK.split(" - ")[0] in text else None})
    return out


def plan_update(plan, found, mod=None):
    """Every older add-on of outdated() put in again in this version, its settings kept (a setting this version no
    longer takes falls back to its default - said in the notes); the test mod's mark kept on its own copies."""
    for o in found:
        a = o["addon"]
        try:
            plan_install(plan, a, o["values"], mod, mark=o["mark"])
        except ValueError as e:
            plan_install(plan, a, read_settings(a, a.template()), mod, mark=o["mark"])
            plan.note(None, _i18n.msg("eng.scriptaddons.settings_not_kept", "{name}: its settings could not be kept ({why}) - put in with this version's defaults", name=a.title, why=e))


def plan_install(plan, addon, values, mod=None, mark=None):
    """The add-on put into the script/modules folder the engine runs (target). mark: one comment line written at
    its end (the test mod's scriptmods.TEST_MARK, so Scripts in the game can find and take out what it put in)."""
    if is_files(addon):
        addon.code().plan_install(plan, **{k.lower(): v for k, v in values.items()})
        return target(plan.mod, addon)
    problems = check(addon, values, mod)
    if problems:
        raise ValueError("; ".join(problems))
    template = addon.template()
    text = render(addon, template, values)
    text = with_game(text, mod or plan.mod)
    if mark:
        nl = "\r\n" if "\r\n" in text else "\n"
        text = text + ("" if text.endswith("\n") else nl) + mark + nl
    dst = target(plan.mod, addon)
    plan.binary(dst, text.encode("utf-8"))
    for p in stray_copies(mod or plan.mod, addon):
        plan.delete(p, "an older copy of %s outside script/modules - it would run twice; the add-on is in %s now"
                    % (addon.title, os.path.relpath(dst, os.path.dirname(p))))
    _old_lua(plan, mod or plan.mod, addon)
    from . import scriptbuilder as MB
    recipe = MB.recipe_of(template)
    if recipe is not None:                      # a module of the Module builder: its messages into the mod's texts
        MB.plan_messages(plan, mod or plan.mod, recipe, values)
    where = os.path.relpath(dst, os.path.dirname(os.path.abspath(plan.mod.data)))
    if os.path.isfile(dst):
        plan.note(None, _i18n.msg("eng.scriptaddons.updated", "updated {name}: {where}", name=addon.title, where=where))
    else:
        plan.note(None, _i18n.msg("eng.scriptaddons.put_in", "put in {name}: {where}", name=addon.title, where=where))
    return dst


def plan_remove(plan, addon, mod=None):
    if is_files(addon):
        addon.code().plan_remove(plan)
        return target(plan.mod, addon)
    dst = target(plan.mod, addon)
    plan.delete(dst, "the %s add-on taken out" % addon.title)
    for p in stray_copies(mod or plan.mod, addon):
        plan.delete(p, "an older copy of the %s add-on taken out" % addon.title)
    _old_lua(plan, mod or plan.mod, addon)
    return dst


def _old_lua(plan, mod, addon):
    """An older version's Lua copy of the add-on in the mod (OLD_LUA) deleted, and its loader line taken out of
    luaPluginScript.lua - every other byte of that file kept."""
    old = OLD_LUA.get(addon.key)
    if not old:
        return
    folder = os.path.join(os.path.dirname(os.path.abspath(mod.data)), *OLD_LUA_DIR)
    lua = _ci(folder, old) if os.path.isdir(folder) else None
    if lua:
        plan.delete(lua, "the older Lua %s - the native script replaces it" % addon.title)
    entry = _ci(folder, OLD_LUA_ENTRY) if os.path.isdir(folder) else None
    if not entry:
        return
    with open(entry, "rb") as fh:
        data = fh.read()
    lines = data.split(b"\n")
    keep = [l for l in lines if (OLD_LUA_MARK + old.encode()) not in l]
    if len(keep) != len(lines):
        plan.binary(entry, b"\n".join(keep))
        plan.note(None, _i18n.msg("eng.scriptaddons.no_older_lua", "{entry}: no longer loads the older Lua {old}", entry=OLD_LUA_ENTRY, old=old))
