"""Literal code and file-picker patterns must survive translation intact."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dev" / "checks"))
from i18n_integrity import problems


class Integrity(unittest.TestCase):
    def test_translated_prose_is_allowed(self):
        self.assertEqual(problems("Open <code>a.txt</code>: {n}", "Otwórz <code>a.txt</code>: {n}"), [])

    def test_code_spaces_change_the_literal(self):
        self.assertIn("literal code contents", problems("<code>a.txt</code>", "<code> a.txt </code>"))

    def test_code_can_move_with_the_sentence(self):
        self.assertEqual(problems("<code>a</code>, <code>b</code>", "<code>b</code>, <code>a</code>"), [])

    def test_repeated_placeholder_cannot_disappear(self):
        self.assertIn("placeholder occurrences", problems("{x} then {x}", "{x}"))

    def test_file_filter_cannot_lose_its_machine_half(self):
        self.assertIn("file-picker filter patterns", problems(
            "Images (*.png)|*.png|All files (*.*)|*.*", "Obrazy (*.png)"))

    def test_attribute_template_is_not_prose(self):
        self.assertIn("internal syntax", problems('data-i="{x}"', 'dane-i="{x}"'))

    def test_edit_key_cannot_change_language(self):
        self.assertIn("internal syntax", problems("level/{name}/{x}", "poziom/{name}/{x}"))

    def test_event_handler_cannot_change_language(self):
        self.assertIn("internal syntax", problems('onchange="pick(\'{key}\')"', 'onchange="pick(\' {key} \')"'))

    def test_action_tooltip_keeps_its_handler(self):
        self.assertIn("title attribute syntax", problems('onclick="open(\'{x}\')" title="Open"', 'onclick="open(\' {x} \')" title="Otwórz"'))

    def test_keywords_are_not_sentences(self):
        self.assertIn("literal keyword or product name", problems("NoGoingBackLevel", "Nie wracaj"))

    def test_tooltip_value_can_be_translated(self):
        self.assertEqual(problems('disabled title="No UVs"', 'disabled title="Brak UV"'), [])

    def test_inline_native_tooltip_can_be_translated(self):
        self.assertEqual(problems('<b class="a" title="Open">Open</b>', '<b class="a" title="Otwórz">Otwórz</b>'), [])

    def test_inline_tooltip_cannot_change_other_attributes(self):
        self.assertIn('literal HTML tags/attributes', problems('<b class="a" title="Open">Open</b>', '<b class="b" title="Otwórz">Otwórz</b>'))

    def test_tooltip_cannot_translate_the_attribute_name(self):
        self.assertIn("title attribute syntax", problems('title="No UVs"', 'tytuł="Brak UV"'))


if __name__ == "__main__":
    unittest.main()
