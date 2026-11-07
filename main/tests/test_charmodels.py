"""Phase 101j joins and existing writers, using synthetic files only."""
import tempfile
import unittest
import json
import threading
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from unittransfer import characters, campstrat, stratmap, config, transfer, stratchar


DC = """type named character
actions moving_normal
faction england
strat_model default ; Default
battle_model mounted
faction papal_states
strat_model default
strat_model pope ; a label only
battle_model mounted
faction sicily
strat_model default ; 0 Default
strat_model heir ; Custom
strat_model leader ; Wrong comment
strat_model hero ; 3 hero
strat_model unreachable
battle_model foot
type general
actions moving_normal
faction sicily, england
strat_model captain
battle_model missing
type priest
actions moving_normal
faction sicily
strat_model priest
strat_model bishop
strat_model cardinal
"""
EDCT = """Trait FactionHeir
Characters family
Level Heir
Effect Level 1
Trait FactionLeader
Characters family
Level Leader
Effect Level 2
Trait Hero
Characters family
Level Hero
Effect Level 3
Level HeroAgain
Effect Level 3
Trait IAmPope
Characters family
Level Pope
Effect Level 1
Trait Bishop
Characters priest
Level Bishop
Effect Level 1
Trait Cardinal
Characters priest
Level Cardinal
Effect Level 2
"""
STRAT = """campaign imperial_campaign
playable
sicily
end
faction sicily, balanced smith
character Test King, named character, male, leader, age 40, x 2, y 3, battle_model mounted
traits Hero 1
character Test Heir, named character, male, heir, age 20, x 3, y 3
character Test Hero, named character, male, age 22, x 4, y 3, battle_model foot
character Test Ordinary, named character, male, age 21, x 5, y 3
"""


class CharacterModelsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ut_charmodels_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        data = self.root / "data"
        data.mkdir()
        self.mod = SimpleNamespace(data=data, root=self.root, name="Fixture",
            edct_path=data / "export_descr_character_traits.txt")
        entries = {n: SimpleNamespace(name=n, animations=[SimpleNamespace(mount_type=m)])
                   for n, m in (("mounted", "horse"), ("foot", "none"))}
        self.mod.modeldb = SimpleNamespace(by_name=lambda: entries)
        self.mod.strat_models = stratmap.parse_text("type default\ntexture sicily, models_strat/x.tga\n"
                                                  "type other\ntexture england, models_strat/y.tga\n")
        (data / characters.REL).write_text(DC, encoding="latin-1")
        self.mod.edct_path.write_text(EDCT, encoding="latin-1")
        (data / "descr_sm_factions.txt").write_text(
            "faction sicily\nsymbol models_strat/s.cas\nrebel_symbol models_strat/r.cas\n", encoding="latin-1")
        for campaign in ("imperial_campaign", "custom/nested"):
            p = data / "world/maps/campaign" / campaign
            p.mkdir(parents=True)
            (p / "descr_strat.txt").write_text(STRAT, encoding="latin-1")
            (p / "campaign_script.txt").write_text(
                "change_battle_model sicily leader mounted; active\n"
                "; change_battle_model sicily heir foot\n"
                "change_battle_model england leader foot\n"
                "; prose change_battle_model sicily leader foot\n", encoding="latin-1")

    def test_levels_come_from_traits_not_comments(self):
        from unittransfer import charmodels as cm
        levels = cm.levels_of(self.mod)
        self.assertEqual(levels["named character"][3], ["Hero"])
        self.assertEqual(levels["priest"][1], ["Bishop"])
        out = cm.faction_models(self.mod, "sicily")
        slots = out["named"][0]["slots"]
        self.assertEqual([s["level"] for s in slots], list(range(5)))
        self.assertEqual(slots[1]["traits"], ["FactionHeir", "IAmPope"])
        self.assertEqual(slots[1]["comment"], "Custom")
        self.assertEqual(slots[2]["traits"], ["FactionLeader"])
        self.assertEqual(out["agents"][0]["slots"][2]["traits"], ["Cardinal"])
        self.assertEqual(out["sig"], characters._sig(characters._read(self.mod)))

    def test_heir_and_leader_traits_are_listed_first(self):
        # A level's traits come from the whole EDCT (DaC gives level 1 to eight
        # traits and level 3 to 22), and the dialog shows the first four. The
        # traits every faction's heir or leader gets go first: those named
        # Factionheir / Factionleader (vanilla, DaC and the TWCenter tutorial
        # all use these names; DaC gives them from EOP Lua, not a trigger), and
        # those a BecomesFactionHeir / BecomesFactionLeader trigger gives.
        from unittransfer import charmodels as cm
        self.mod.edct_path.write_text(
            "Trait AHero\nCharacters family\nLevel A\nEffect Level 1\n"
            "Trait IAmPope\nCharacters family\nLevel Pope\nEffect Level 1\n"
            "Trait HeirByTrigger\nCharacters family\nLevel H\nEffect Level 1\n"
            "Trait Factionheir\nCharacters family\nLevel Heir\nEffect Level 1\n"
            "Trait BHero\nCharacters family\nLevel B\nEffect Level 2\n"
            "Trait FACTIONLEADER\nCharacters family\nLevel Leader\nEffect Level 2\n"
            ";------------------------------------------\n"
            "Trigger becomesheir\n    WhenToTest BecomesFactionHeir\n\n"
            "    Affects HeirByTrigger  1  Chance  100\n", encoding="latin-1")
        levels = cm.levels_of(self.mod)["named character"]
        self.assertEqual(levels[1], ["HeirByTrigger", "Factionheir", "AHero", "IAmPope"])
        self.assertEqual(levels[2], ["FACTIONLEADER", "BHero"])

    def test_vanilla_one_slot_and_pope_are_valid(self):
        from unittransfer import charmodels as cm
        self.mod.edct_path.write_text(EDCT.replace("Effect Level 1\nTrait FactionLeader", "Trait FactionLeader")
                                     .replace("Effect Level 2\nTrait Hero", "Trait Hero"), encoding="latin-1")
        self.assertEqual(len(cm.faction_models(self.mod, "england")["named"][0]["slots"]), 1)
        self.assertEqual(cm.faction_models(self.mod, "papal_states")["named"][0]["slots"][1]["traits"],
                         ["IAmPope"])
        self.assertFalse(any("default, heir and leader" in f["message"]
                             for f in characters.check(characters.parse(DC))))

    def test_battle_warnings_and_read_only_ownership(self):
        from unittransfer import charmodels as cm
        out = cm.faction_models(self.mod, "sicily")
        self.assertTrue(out["named"][0]["battle_model"]["exists"])
        self.assertFalse(out["named"][0]["battle_model"]["horse"])
        self.assertFalse(out["captain"][0]["battle_model"]["exists"])
        self.assertEqual({f["code"] for f in out["findings"]}, {"horse", "battle", "level"})
        self.assertEqual(out["symbols"]["symbol"], "models_strat/s.cas")
        self.assertEqual(out["strat_textures"], ["default"])
        self.assertEqual(len(out["characters"]), 6)
        self.assertEqual(len(out["scripts"]), 4)
        self.assertEqual(sum(s["commented"] for s in out["scripts"]), 2)
        self.assertIn("custom/nested", {c["campaign"] for c in out["characters"]})
        self.assertEqual(set(cm.faction_models(self.mod)["roster"]), {"england", "papal_states", "sicily"})

    def test_entry_users_and_strat_enrichment(self):
        from unittransfer import charmodels as cm
        users = cm.entry_characters(self.mod, "MOUNTED")
        self.assertEqual(sum(u["source"] == "descr_character" for u in users), 2)
        self.assertEqual(sum(u["source"] == "descr_strat" for u in users), 2)
        self.assertEqual(sum(u["source"] == "campaign_script" for u in users), 2)
        self.assertTrue(all(u["role"] == "generals" for u in users if u["source"] == "descr_character"))
        users = cm.strat_characters(self.mod, "heir")
        self.assertEqual(users[0]["level"], 1)
        self.assertIn("FactionHeir", users[0]["traits"])
        self.assertEqual(users[0]["label"], "Custom")

    def test_existing_plan_preserves_comment_and_rejects_stale(self):
        from unittransfer import charmodels as cm
        out = cm.faction_models(self.mod, "sicily")
        slot = out["named"][0]["slots"][1]
        body = {"sig": out["sig"], "values": {str(slot["line"]): "leader"}}
        with patch.object(characters.Refs, "of", return_value=characters.Refs()):
            p = characters.plan(self.mod, body)
            self.assertFalse(p.errors)
            self.assertIn("strat_model leader ; Custom", p.text)
            body["sig"] = "stale"
            self.assertTrue(characters.plan(self.mod, body).errors)

    def test_http_roster_and_entry_joins(self):
        from unittransfer.server import Handler, _Server
        registry = SimpleNamespace(names=lambda: ["Fixture"], get=lambda name: self.mod,
            describe=lambda name: self.mod, invalidate=lambda name: None,
            map_facts=lambda name, campaign: SimpleNamespace(mod=self.mod, campaign=campaign, skipped=[]))
        class FixtureHandler(Handler):
            pass
        FixtureHandler.registry = registry
        server = _Server(("127.0.0.1", 0), FixtureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_address[1])
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def get(path):
                with opener.open(base + path, timeout=10) as response:
                    return json.load(response)
            self.assertIn("sicily", get("/api/charmodels?mod=Fixture")["roster"])
            self.assertEqual(get("/api/charmodels?mod=Fixture&faction=sicily")["named"][0]["slots"][1]["traits"],
                             ["FactionHeir", "IAmPope"])
            with patch("unittransfer.bmdb.entry_detail", return_value={"model": {"name": "mounted"}}):
                self.assertTrue(get("/api/bmdb/entry?mod=Fixture&name=mounted")["characters"])
            with patch("unittransfer.stratmap.entry_detail", return_value={"name": "heir"}):
                self.assertEqual(get("/api/stratmap/entry?mod=Fixture&name=heir")["characters"][0]["level"], 1)
            def post(path, body):
                request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"})
                with opener.open(request, timeout=10) as response:
                    return json.load(response)
            cfg = self.root / "http-config"
            cfg.mkdir()
            with patch.multiple(config, CONFIG_DIR=cfg, BACKUP_DIR=cfg / "backups",
                                SETTINGS_PATH=cfg / "settings.json", LOG_PATH=cfg / "log.json"):
                out = get("/api/charmodels?mod=Fixture&faction=sicily")
                slot = out["named"][0]["slots"][1]
                body = {"mod": "Fixture", "sig": out["sig"], "values": {str(slot["line"]): "leader"}}
                path = self.mod.data / characters.REL
                before = path.read_bytes()
                self.assertFalse(post("/api/characters/plan", body)["plan"]["errors"])
                rec = post("/api/characters/apply", body)["record"]
                self.assertNotEqual(path.read_bytes(), before)
                self.assertTrue(post("/api/characters/apply", body)["plan"]["errors"], "old signature refused")
                post("/api/undo", {"id": rec["id"]})
                self.assertEqual(path.read_bytes(), before)
                person = next(c for c in out["characters"] if c["campaign"] == "imperial_campaign" and c["rank"] == "leader")
                body = {"mod": "Fixture", "campaign": person["campaign"], "faction": "sicily", "character": person["name"],
                        "line": person["line"], "action": "edit", "edits": {"battle_model": "foot"}}
                path = campstrat.strat_path(self.mod, person["campaign"])
                before = path.read_bytes()
                self.assertFalse(post("/api/map/character_plan", body)["plan"]["errors"])
                rec = post("/api/map/character_apply", body)["record"]
                self.assertEqual(path.read_bytes(), before.replace(b"battle_model mounted", b"battle_model foot"))
                post("/api/undo", {"id": rec["id"]})
                self.assertEqual(path.read_bytes(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_existing_writers_apply_and_undo_only_requested_models(self):
        from unittransfer import charmodels as cm
        cfg = self.root / "config"
        cfg.mkdir()
        with patch.multiple(config, CONFIG_DIR=cfg, BACKUP_DIR=cfg / "backups",
                            SETTINGS_PATH=cfg / "settings.json", LOG_PATH=cfg / "log.json"):
            out = cm.faction_models(self.mod, "sicily")
            slot = out["named"][0]["slots"][1]
            path = self.mod.data / characters.REL
            before = path.read_bytes()
            with patch.object(characters.Refs, "of", return_value=characters.Refs()):
                p = characters.plan(self.mod, {"sig": out["sig"], "values": {str(slot["line"]): "leader"}})
            rec = characters.apply(p)["record"]
            self.assertEqual(path.read_bytes(), before.replace(b"strat_model heir ; Custom", b"strat_model leader ; Custom"))
            self.assertTrue((Path(rec["backup_root"]) / "data" / characters.REL).is_file())
            transfer.undo(rec["id"])
            self.assertEqual(path.read_bytes(), before)
            campaign = "imperial_campaign"
            person = next(c for c in out["characters"] if c["campaign"] == campaign and c["rank"] == "leader")
            path = campstrat.strat_path(self.mod, campaign)
            before = path.read_bytes()
            facts = SimpleNamespace(mod=self.mod, campaign=campaign, skipped=[])
            p = stratchar.plan_character(self.mod, facts, {"campaign": campaign, "faction": "sicily",
                "character": person["name"], "line": person["line"], "action": "edit", "edits": {"battle_model": "foot"}})
            self.assertFalse(p.errors)
            rec = stratchar.apply_character(p)["record"]
            self.assertEqual(path.read_bytes(), before.replace(b"battle_model mounted", b"battle_model foot"))
            transfer.undo(rec["id"])
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
