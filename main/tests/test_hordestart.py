"""Phase 72, D13: a horde start for a faction that holds nothing.

    python -m tests.test_hordestart

On a copy of each installed mod's imperial campaign, with a new faction
`hordetest` declared in descr_sm_factions.txt and descr_names.txt off a donor
(ROCSS: its Mongols; DaC: its first faction with a pool) and given a campaign
block by 16j-2's create, which is the empty shape a horde start fills:

1. The view: an empty faction, a province picked, a dry plan of each mode.
2. start: named characters on free land in the province, two tiles apart,
   off every marker and every other character, their names out of the pool,
   the leader and heir with a family line; the file's other factions byte
   for byte; applied, the campaign reads them back; one Undo restores every
   file byte for byte.
3. emerge: dead_until_resurrected in the block, an emergent_faction event in
   descr_events.txt, and on a faction with no horde the seven keys, a roster
   and spawned_on_event in descr_sm_factions.txt; one Undo.
4. Refusals: a faction that holds a settlement, a province that is not one,
   more people than a stack of names, an unknown mode.
5. The routes: GET /api/map/horde and POST /api/map/horde_plan|_apply.
"""
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import (campevents, campmap, campstrat, config, factions,  # noqa: E402
                          hordestart as hs, mapquery, modflags, stratcamp,
                          stratchar, transfer)
from unittransfer.keyblock import read_text  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
CAMP = "imperial_campaign"
EXTRAS = ("export_descr_unit.txt", "descr_names.txt", "descr_sm_factions.txt",
          "export_descr_character_traits.txt", "export_descr_ancillaries.txt")


def copy_mod(src: Path, med2: Path, name: str) -> Path:
    data = med2 / "mods" / name / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for pth in (src / "data" / campmap.BASE_REL).iterdir():
        if pth.is_file() and not pth.name.lower().endswith(".rwm"):
            shutil.copy2(pth, data / campmap.BASE_REL / pth.name)
    home = data / campstrat.CAMPAIGN_DIR_REL / CAMP
    home.mkdir(parents=True)
    for n in (campstrat.STRAT_NAME, campevents.EVENTS_NAME):
        if (src / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP / n).is_file():
            shutil.copy2(src / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP / n, home / n)
    for extra in EXTRAS:
        if (src / "data" / extra).is_file():
            shutil.copy2(src / "data" / extra, data / extra)
    return data.parent


def facts_of(mod):
    return mapquery.Facts(mod, campmap.CampaignMap(mod), CAMP)


def snapshot(mod):
    return {p: p.read_bytes() for p in Path(mod.data).rglob("*.txt")}


def declare(mod, slot: str, donor: str) -> None:
    """The half of a new faction the Factions screen's clone writes: a record in
    descr_sm_factions.txt and a pool in descr_names.txt, copied off the donor."""
    from unittransfer import minorfiles
    smp = factions.path_for(mod)
    text = read_text(smp, factions.ENCODING)
    rf = factions.parse_text(text)
    rec = hs._record(rf, donor)
    block = rf.block_text(rec).replace(rec.name, slot, 1)
    nl = "\r\n" if "\r\n" in text else "\n"
    smp.write_bytes((text.rstrip("\r\n") + nl + nl + block.strip("\r\n") + nl)
                    .encode(factions.ENCODING))
    np_ = Path(mod.data) / minorfiles.NAMES_REL
    text = read_text(np_, campstrat.ENCODING)
    nf = minorfiles.parse_names(text)
    got = next(f for f in nf.factions if f.name.lower() == donor.lower())
    block = nf.block_text(got).replace(got.name, slot, 1)
    nl = "\r\n" if "\r\n" in text else "\n"
    np_.write_bytes((text.rstrip("\r\n") + nl + nl + block + nl)
                    .encode(campstrat.ENCODING))


def make_faction(mod, slot: str, donor: str):
    """16j-2's create: the shape a horde start fills."""
    declare(mod, slot, donor)
    p = stratcamp.plan_campaign(mod, facts_of(mod),
                                {"what": "create", "faction": slot,
                                 "donor": donor, "roster": "nonplayable",
                                 "campaign": CAMP})
    if p.errors:
        return p.errors
    stratcamp.apply_campaign(p)
    return []


med2 = Path(_tmp.mkdtemp(prefix="ut_horde_"))
cases = []
roc = MODS / "ROCSS"
if (roc / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP).is_dir():
    got = copy_mod(roc, med2, "HordeROC")
    # ROCSS declares 449 regions and is read past the 200 ceiling only as M2EX,
    # which is a flag on its Home card and lives in the (redirected) settings
    modflags.set_m2ex(Mod(got), True)
    cases.append((got, "hordetest", "mongols"))
dac = MODS / "Divide_and_Conquer_EUR"
if (dac / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP).is_dir():
    cases.append((copy_mod(dac, med2, "HordeDaC"), "hordetest", None))
if not cases:
    print("SKIPPED - neither ROCSS nor Divide_and_Conquer_EUR is installed")
    sys.exit(0)

for root, slot, donor in cases:
    mod = Mod(root)
    sf = campstrat.read_strat(mod, CAMP)
    if donor is None:
        from unittransfer import minorfiles
        rf = factions.parse_file(factions.path_for(mod))
        pools = {f.name.lower() for f in minorfiles.parse_names(
            (Path(mod.data) / minorfiles.NAMES_REL).read_text(campstrat.ENCODING)).factions}
        donor = next(n.name for n in sf.of_kind("faction")
                     if n.name != "slave" and hs._record(rf, n.name) is not None
                     and n.name.lower() in pools)
    print(f"\n== {root.name}: {slot}, cloned from {donor}")
    errs = make_faction(mod, slot, donor)
    if not check(f"16j-2 makes {slot} from {donor}, holding nothing", not errs):
        print("   ", errs)
        continue
    facts = facts_of(mod)
    sf = campstrat.read_strat(mod, CAMP)
    # the fixture's faction owns nothing in the EDU (the Factions screen's
    # clone adds it to the donor's units); DaC's donor has no horde roster
    # either, so the start is given the donor's own army
    owned = hs.owned_units(mod, donor)
    army = hs.default_army(owned, hs.land_units(owned)[:9])

    print("1) the view")
    v = hs.view(mod, facts, slot)
    check("the faction is empty, a province is offered and both dry plans are there",
          v["empty"] and v["province"] in v["provinces"]
          and set(v["defaults"]) == set(hs.MODES))
    d = v["defaults"]["start"]
    check("the dry start plan is clean, or refuses for want of an army",
          d["ok"] and len(d["people"]) == d["used"]["count"]
          or d["errors"] == [e for e in d["errors"] if "regiment" in e])

    print("2) start")
    before = snapshot(mod)
    province = v["province"]
    p = hs.plan(mod, facts, {"faction": slot, "mode": "start",
                             "province": province, "count": 4, "army": army})
    if not check(f"four people in {province}", not p.errors and len(p.people) == 4):
        print("   ", p.errors[:4])
        continue
    cm = campmap.map_of(facts)
    tiles = [(q["x"], q["y"]) for q in p.people]
    lands = []
    for x, y in tiles:
        ix, iy = cm.image_xy(x, y)
        r = cm.index.at(ix, iy)
        lands.append(not cm.sea[iy * cm.terrain.width + ix]
                     and r is not None and r.name == province)
    check("every tile is land in that province", all(lands))
    check("no two stand on one tile, and none on another character",
          len(set(tiles)) == len(tiles)
          and not set(tiles) & {(int(n.get("x")), int(n.get("y")))
                                for n in sf.of_kind("character")})
    spaced = all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= hs.SPACING
                 for i, a in enumerate(tiles) for b in tiles[i + 1:])
    check(f"they stand {hs.SPACING} tiles apart where the province has room", spaced)
    markers = {tuple(r.settlement) for r in cm.index.regions if r.settlement}
    check("none on a settlement pixel",
          not any(cm.image_xy(x, y) in markers for x, y in tiles))
    ranks = [q["rank"] for q in p.people]
    check("a leader and an heir, then named characters", ranks[:2] == ["leader", "heir"]
          and not any(ranks[2:]))
    pool = hs._names(mod, slot)
    firsts = set(pool["characters"])
    check("every name's first part is in the faction's pool",
          all(q["name"].split()[0] in firsts for q in p.people) or not firsts)
    rel = f"{campstrat.CAMPAIGN_DIR_REL}/{CAMP}/{campstrat.STRAT_NAME}"
    check("descr_strat.txt is written, and nothing is fatal", rel in p.texts
          and not any(f["fatal"] for f in p.findings))
    done = campstrat.parse_strat(p.texts[rel])
    mine = done.faction(slot)
    check("the campaign reads four characters with armies back",
          len(stratchar.characters_of(done, mine)) == 4
          and all(done.children_of(c, "army") for c in stratchar.characters_of(done, mine)))
    if p.used.get("family"):
        rels = stratchar.relatives_of(done, mine)
        check("one family line: the leader, his wife, the heir",
              len(rels) == 1 and list(rels[0].get("names"))[:3]
              == [p.people[0]["name"], p.used["wife"], p.people[1]["name"]])
    others = [n for n in sf.of_kind("faction") if n.name != slot]
    check("every other faction's block is byte for byte what it was",
          all(sf.lines[n.start:n.end + 1]
              == done.lines[done.faction(n.name).start:done.faction(n.name).end + 1]
              for n in others))
    res = hs.apply(p)
    live = campstrat.read_strat(mod, CAMP)
    check("applied: the file on disk holds them",
          len(stratchar.characters_of(live, live.faction(slot))) == 4)
    again = hs.plan(mod, facts_of(mod), {"faction": slot, "mode": "start",
                                          "province": province, "army": army})
    check("a second start is refused, naming what it holds",
          again.errors and "4 characters" in again.errors[0])
    transfer.undo(res["id"])
    check("one Undo puts every file back byte for byte", snapshot(mod) == before)

    print("3) emerge")
    smp = factions.path_for(mod)
    text = read_text(smp, factions.ENCODING)
    rf = factions.parse_text(text)
    rec = hs._record(rf, slot)
    block = rf.block_text(rec)
    bare = "\n".join(ln for ln in block.split("\n")
                     if not ln.strip().startswith("horde_"))
    bare = bare.replace(f"{rec.name}", factions.slot_of(rec.name), 1)
    smp.write_bytes(rf.replace(rec.start, rec.end, bare).encode(factions.ENCODING))
    before = snapshot(mod)
    body = {"faction": slot, "mode": "emerge", "regions": [province],
            "date": "12 16"}
    if not hs.owned_units(mod, slot) and not hs._horde(hs._record(
            factions.parse_file(smp), slot))[1]:
        r = hs.plan(mod, facts_of(mod), body)
        check("with no roster and no unit owned, the emergent start is refused",
              r.errors and "horde_unit" in r.errors[0])
        body["horde_units"] = [u for u in army
                               if u not in {x["name"] for x in hs.owned_units(mod, donor)
                                            if x["general"]}]
    p = hs.plan(mod, facts_of(mod), body)
    if not check("an emergent start plans", not p.errors):
        print("   ", p.errors[:4])
        continue
    ev_rel = f"{campstrat.CAMPAIGN_DIR_REL}/{CAMP}/{campevents.EVENTS_NAME}"
    check("three files: the campaign, the event and the roster",
          set(p.texts) == {rel, ev_rel, factions.REL})
    done = campstrat.parse_strat(p.texts[rel])
    check(f"{slot} reads {hs.FLAG}", bool(done.faction(slot).get(hs.FLAG)))
    bf = campevents.parse_events(p.texts[ev_rel])
    b = bf.by_name(slot)
    check("descr_events.txt has `event emergent_faction` with the date and province",
          b is not None and b.kind == hs.EVENT_KIND and b.all("date") == ["12 16"]
          and b.all("region") == [province])
    after = factions.parse_text(p.texts[factions.REL])
    now = hs._record(after, slot)
    check("descr_sm_factions: spawned_on_event, all seven keys and a roster",
          factions.modifier_of(now.name) == hs.MODIFIER
          and all(now.get(k) != "" for k in factions.HORDE_KEYS) and now.repeats)
    check(f"the keys are copied from the first complete horde ({p.used['horde_from']})",
          p.used["horde_from"] not in ("", slot))
    check("no finding about the roster is fatal",
          not any(f["fatal"] for f in p.findings))
    res = hs.apply(p)
    transfer.undo(res["id"])
    check("one Undo puts all three files back", snapshot(mod) == before)

    print("4) refusals")
    held = next(n.name for n in sf.of_kind("faction")
                if sf.children_of(n, "settlement"))
    r = hs.plan(mod, facts_of(mod), {"faction": held, "province": province})
    check(f"{held} holds settlements and is refused", r.errors and "settlement" in r.errors[0])
    r = hs.plan(mod, facts_of(mod), {"faction": slot, "province": "Nowhere_Province"})
    check("a province that is not one is refused", r.errors and "not a province" in r.errors[0])
    r = hs.plan(mod, facts_of(mod), {"faction": slot, "province": province,
                                     "count": hs.MAX_PEOPLE + 1})
    check("more people than a start writes is refused", bool(r.errors))
    r = hs.plan(mod, facts_of(mod), {"faction": slot, "mode": "invade"})
    check("an unknown mode is refused", bool(r.errors))
    r = hs.plan(mod, facts_of(mod), {"faction": slot, "province": province,
                                     "army": [f"unit {i}" for i in range(hs.STACK + 1)]})
    check("an army over a stack is refused", bool(r.errors))

print("\n5) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

root, slot, _ = cases[0]
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


name = root.name
if slot:
    v = get(f"/api/map/horde?mod={name}&campaign={CAMP}&faction={slot}")
    check("GET /api/map/horde answers with the empty faction", v.get("empty") is True)
    mod = Mod(root)
    before = snapshot(mod)
    body = {"mod": name, "campaign": CAMP, "faction": slot, "mode": "start",
            "province": v["province"], "count": 2}
    pl = post("/api/map/horde_plan", body)
    check("POST horde_plan previews two people and writes nothing",
          len(pl["plan"]["people"]) == 2 and snapshot(mod) == before)
    res = post("/api/map/horde_apply", body)
    check("POST horde_apply writes them", res.get("id") and not res.get("error"))
    v2 = get(f"/api/map/horde?mod={name}&campaign={CAMP}&faction={slot}")
    check("and the view now says the faction holds two characters",
          v2["holds"]["characters"] == 2 and not v2["empty"])
    transfer.undo(res["id"])
    check("and the Undo takes them back", snapshot(mod) == before)
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
