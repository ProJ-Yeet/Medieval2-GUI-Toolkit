"""Armory assignment regressions using disposable synthetic mods only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from unittransfer import armunit, config, edu, modeldb, campstrat, stratchar
from unittransfer.mod import Mod
from unittransfer.transfer import undo


def entry(name):
    s = lambda v: f"{len(v)} {v}"
    return (f"{s(name)}\n1 1\n{s('unit_models/' + name + '.mesh')} 6400\n"
            f"0\n0\n1\n{s('none')}\n{s('MTW2_Spear')} {s('MTW2_Spear_Secondary')}\n"
            "0\n0\n-1\n0 0 0 0 0 0\n")


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ut_armassign_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "mod"
        data = self.root / "data"
        (data / "unit_models").mkdir(parents=True)
        (data / "text").mkdir()
        (data / "export_descr_unit.txt").write_text(
            "type Guard\ndictionary guard\ncategory infantry\nclass heavy\n"
            "soldier old, 40, 0, 1\nofficer old\n"
            "armour_ug_levels 0, 1\narmour_ug_models old, old_t1\nownership england\n",
            encoding="latin-1")
        (data / "text/export_units.txt").write_text("{guard}Guard\n", encoding="utf-16")
        (data / "descr_sm_factions.txt").write_text("faction england\nculture northern_european\n")
        (data / "unit_models/battle_models.modeldb").write_text(
            f"{len(modeldb.ARCHIVE_MAGIC)} {modeldb.ARCHIVE_MAGIC} 3 0 0 0 0 4 0 0\n"
            + "5 blank " + " ".join(["0"] * 39) + "\n"
            + "\n".join(entry(n) for n in ("old", "old_t1", "fresh")), encoding=modeldb.ENCODING)
        cfg = Path(self.tmp.name) / "cfg"
        for key, value in {"CONFIG_DIR": cfg, "BACKUP_DIR": cfg / "backups",
                           "SETTINGS_PATH": cfg / "settings.json", "LOG_PATH": cfg / "transfers.json"}.items():
            p = patch.object(config, key, value)
            p.start()
            self.addCleanup(p.stop)

    def request(self, **kw):
        return dict(choice="add", unit="Guard", entry="fresh", **kw)

    def test_soldier_updates_matching_base_tier_and_undo(self):
        path = self.root / "data/export_descr_unit.txt"
        before = path.read_bytes()
        p = armunit.plan_install(Mod(self.root), self.request())
        self.assertTrue(armunit.payload(p)["ok"])
        self.assertIn("armour_ug_models fresh, old_t1", p["steps"][0]["plan"].edu_block)
        result = armunit.apply_install(lambda _: Mod(self.root), "mod", self.request())
        self.assertEqual(Mod(self.root).edu.by_type()["Guard"].armour_ug_models, ["fresh", "old_t1"])
        undo(result["records"][0]["id"])
        self.assertEqual(path.read_bytes(), before)

    def test_existing_entry_slots(self):
        for slot, expected in (("officer#1", "officer fresh"), ("officer#2", "officer old"),
                               ("armour_ug_models#2", "armour_ug_models old, fresh"),
                               ("armour_ug_models#3", "armour_ug_models old, old_t1, fresh")):
            with self.subTest(slot=slot):
                p = armunit.plan_install(Mod(self.root), self.request(assign_to=slot))
                block = p["steps"][0]["plan"].edu_block
                self.assertIn(expected, block)
                self.assertIn("soldier old, 40, 0, 1", block)
                if slot == "officer#2":
                    self.assertEqual([v for k, v in edu.block_fields(block) if k.startswith("officer")], ["old", "fresh"])
                if slot.endswith("#3"):
                    self.assertIn("0, 1, 2", dict(edu.block_fields(block))["armour_ug_levels"])

    def test_baked_assignment_uses_editor_step(self):
        bake = Path(self.tmp.name) / "bake"
        bake.mkdir()
        (bake / "fresh.mesh").write_bytes(b"fixture")
        for slot in ("soldier", "officer#2", "armour_ug_models#3"):
            with self.subTest(slot=slot):
                req = dict(choice="add", unit="Guard", name="baked", clone_from="old",
                           bake_folder=str(bake), stem="fresh", assign_to=slot)
                p = armunit.plan_install(Mod(self.root), req)
                self.assertTrue(armunit.payload(p)["ok"], armunit.payload(p))
                block = p["steps"][0]["plan"].edu_block
                field = dict(edu.block_fields(block))
                self.assertIn("baked", field[slot if slot.startswith("officer#") else slot.split("#")[0]])
                if slot == "soldier":
                    self.assertEqual(field["armour_ug_models"], "baked, old_t1")
                if slot.endswith("#3"):
                    self.assertEqual(field["armour_ug_levels"], "0, 1, 2")

    def test_soldier_preserves_distinct_base_tier(self):
        mod = Mod(self.root)
        path = self.root / "data/export_descr_unit.txt"
        path.write_text(path.read_text().replace("armour_ug_models old,", "armour_ug_models old_t1,"))
        mod = Mod(self.root)
        p = armunit.plan_install(mod, self.request())
        self.assertIn("armour_ug_models old_t1, old_t1", p["steps"][0]["plan"].edu_block)

    def characters(self):
        path = self.root / "data/world/maps/campaign/imperial_campaign/descr_strat.txt"
        path.parent.mkdir(parents=True)
        path.write_bytes((
            "campaign imperial_campaign\r\nplayable\r\nengland\r\nend\r\n"
            "faction england, balanced smith\r\ndenari 1000\r\n"
            "character William, named character, male, leader, age 50, x 10, y 20, battle_model old ; keep\r\n"
            "traits GoodCommander 1\r\nancillaries mentor\r\narmy\r\nunit Guard exp 1 armour 0 weapon_lvl 0\r\n\r\n"
            "character Henry, named character, male, heir, age 20, x 11, y 21\r\n\r\n"
            "character Robin, named character, male, age 25, x 12, y 22\r\n\r\n"
            "character Spy, spy, male, age 25, x 12, y 22\r\n"
        ).encode('latin-1'))
        return path

    def test_character_target_plan_apply_undo_preserves_other_values(self):
        path = self.characters()
        before = path.read_bytes()
        for kind, name in (("leader", "William"), ("heir", "Henry"), ("general", "Robin")):
            with self.subTest(kind=kind):
                mod = Mod(self.root)
                sf = campstrat.read_strat(mod, "imperial_campaign")
                node = stratchar.find_character(sf, "england", name)
                target = dict(kind=kind, campaign="imperial_campaign", faction="england", character=name, line=node.start+1)
                req = self.request(character_target=target)
                facts = lambda campaign: SimpleNamespace(mod=Mod(self.root), campaign=campaign)
                p = armunit.plan_install(mod, req, facts_of=facts)
                self.assertTrue(armunit.payload(p)["ok"], armunit.payload(p))
                self.assertEqual(p["steps"][-1]["kind"], "character")
                cp = p["steps"][-1]["plan"]
                self.assertIn("battle_model", cp.summary())
                result = armunit.apply_install(lambda _: Mod(self.root), "mod", req, facts_of=facts)
                after = campstrat.read_strat(Mod(self.root), "imperial_campaign")
                changed = stratchar.find_character(after, "england", name)
                expected = stratchar.read_spec(sf, node)
                expected.tail['battle_model'] = 'fresh'
                self.assertEqual(stratchar.read_spec(after, changed), expected)
                self.assertEqual(sf.lines[:node.start], after.lines[:changed.start])
                self.assertEqual(sf.lines[node.start+1:], after.lines[changed.start+1:])
                for rec in reversed(result['records']):
                    undo(rec['id'])
                self.assertEqual(path.read_bytes(), before)

    def test_character_target_rejects_stale_rank_and_missing_selection(self):
        self.characters()
        mod = Mod(self.root)
        facts = lambda campaign: SimpleNamespace(mod=mod, campaign=campaign)
        for target in (dict(kind='leader', campaign='imperial_campaign', faction='england', character='Robin'),
                       dict(kind='general', campaign='imperial_campaign', faction='england', character='Spy'),
                       dict(kind='heir', campaign='imperial_campaign', faction='england', character='Missing'),
                       dict(kind='leader')):
            with self.subTest(target=target), self.assertRaises(armunit.InstallError):
                armunit.plan_install(mod, self.request(character_target=target), facts_of=facts)

    def test_character_picker_lists_ranks_and_lines(self):
        self.characters()
        rows = armunit.character_targets(Mod(self.root))
        chars = rows[0]['factions'][0]['characters']
        self.assertEqual([c['name'] for c in chars], ['William', 'Henry', 'Robin'])
        self.assertEqual(chars[0]['rank'], 'leader')
        self.assertGreater(chars[0]['line'], 0)

    def test_new_unit_tier_is_assigned_to_duplicate(self):
        req = dict(choice='new', unit='Guard', new_type='New Guard', entry='fresh',
                   assign_to='armour_ug_models#3')
        p = armunit.plan_install(Mod(self.root), req)
        self.assertTrue(armunit.payload(p)['ok'], armunit.payload(p))
        result = armunit.apply_install(lambda _: Mod(self.root), 'mod', req)
        units = Mod(self.root).edu.by_type()
        self.assertEqual(units['New Guard'].armour_ug_models, ['old','old_t1','fresh'])
        self.assertEqual(units['Guard'].armour_ug_models, ['old','old_t1'])
        for rec in reversed(result['records']):
            undo(rec['id'])
        self.assertNotIn('New Guard', Mod(self.root).edu.by_type())

    def test_baked_entry_and_character_are_separate_undoable_steps(self):
        path = self.characters()
        before = path.read_bytes()
        bake = Path(self.tmp.name) / 'bake'
        bake.mkdir()
        (bake / 'baked.mesh').write_bytes(b'fixture')
        req = dict(choice='skip', name='baked', clone_from='old', bake_folder=str(bake), stem='baked',
                   character_target=dict(kind='leader', campaign='imperial_campaign', faction='england', character='William'))
        facts = lambda campaign: SimpleNamespace(mod=Mod(self.root), campaign=campaign)
        planned = armunit.plan_install(Mod(self.root), req, facts_of=facts)
        self.assertTrue(armunit.payload(planned)['ok'], armunit.payload(planned))
        self.assertEqual([s['kind'] for s in planned['steps']], ['bmdb','character'])
        result = armunit.apply_install(lambda _: Mod(self.root), 'mod', req, facts_of=facts)
        self.assertEqual(len(result['records']), 2)
        self.assertIn('baked', Mod(self.root).modeldb.by_name())
        self.assertIn('battle_model baked', path.read_text(encoding='latin-1'))
        undo(result['records'][1]['id'])
        self.assertEqual(path.read_bytes(), before)
        self.assertIn('baked', Mod(self.root).modeldb.by_name())
        undo(result['records'][0]['id'])
        self.assertNotIn('baked', Mod(self.root).modeldb.by_name())


if __name__ == "__main__":
    unittest.main()
