"""Phase 108: the example projects in docs/examples/designer stay valid.

Each one imports through the portable reader, passes the contract, calculates
without an issue, and projects only native columns. The mercenary example's pool
settings pass the Phase 107 checks once a pool is chosen.
"""
import json
import unittest
from pathlib import Path

from unittransfer import builder_calculator as calculator, builder_contract as contract
from unittransfer import builder_mercs, builder_projects

EXAMPLES = Path(__file__).resolve().parents[1] / 'docs' / 'examples' / 'designer'


class ExampleTests(unittest.TestCase):
    def test_there_are_examples(self):
        self.assertGreaterEqual(len(list(EXAMPLES.glob('*.json'))), 3)

    def test_every_example_imports_validates_and_calculates(self):
        for path in sorted(EXAMPLES.glob('*.json')):
            with self.subTest(path.name):
                design = builder_projects.read(path.read_text(encoding='utf-8'))
                contract.validate_design(design)
                result = calculator.calculate(design)
                native = result['native']
                for key in ('attack', 'armor', 'defense', 'morale', 'recruit_cost', 'upkeep'):
                    self.assertGreater(native[key], 0, path.name + ' ' + key)
                out = contract.output_values(design, result['native'])
                self.assertTrue(out['native'])
                self.assertEqual(design['profile']['revision'], contract.SOURCE_REVISION)

    def test_the_mercenary_example_is_ready_for_pools(self):
        raw = json.loads((EXAMPLES / 'mercenary_crossbowmen.json').read_text(encoding='utf-8'))
        raw['design']['inputs']['merc_pools'] = ['any_pool']
        values, pools, errors = builder_mercs.settings(raw['design'])
        self.assertEqual(errors, [])
        self.assertEqual(values, {'exp': 1, 'cost': 650, 'replenish': ['0.08', '0.12'], 'max': 2, 'initial': 1})


if __name__ == '__main__':
    unittest.main()
