import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest

from src import redaction


class TestRedaction(unittest.TestCase):
    def test_email_removed(self):
        text = "Please email d.ramaswamy@northgate-fm.example instead."
        clean, cats = redaction.redact(text)
        self.assertNotIn("d.ramaswamy@northgate-fm.example", clean)
        self.assertIn("EMAIL", cats)

    def test_phone_removed(self):
        text = "His direct line is 0161 496 0221 if needed."
        clean, cats = redaction.redact(text)
        self.assertNotIn("0161 496 0221", clean)
        self.assertIn("PHONE", cats)

    def test_mobile_removed_different_wording(self):
        # held-out-style variant: different phrasing, same category
        text = "Call the site lead on 07912 345678 before arrival."
        clean, cats = redaction.redact(text)
        self.assertNotIn("07912 345678", clean)
        self.assertIn("PHONE", cats)

    def test_access_code_removed(self):
        text = "Access code for the plant room is 4471."
        clean, cats = redaction.redact(text)
        self.assertNotIn("4471", clean)
        self.assertIn("ACCESS_CODE", cats)

    def test_access_code_different_wording(self):
        text = "The alarm code is 8842 and must be entered within 30 seconds."
        clean, cats = redaction.redact(text)
        self.assertNotIn("8842", clean)
        self.assertIn("ACCESS_CODE", cats)

    def test_address_removed(self):
        text = "Spare key held at 14 Alderman Court, flat 3B."
        clean, cats = redaction.redact(text)
        self.assertNotIn("Alderman Court", clean)
        self.assertNotIn("3B", clean)
        self.assertIn("ADDRESS", cats)

    def test_name_removed_with_context(self):
        text = "Site contact is Margaret Oyelaran, mobile 07700 900412."
        clean, cats = redaction.redact(text)
        self.assertNotIn("Margaret Oyelaran", clean)
        self.assertIn("NAME", cats)

    def test_name_removed_different_context_phrase(self):
        text = "Facilities manager Dev Ramaswamy asked to be emailed instead."
        clean, cats = redaction.redact(text)
        self.assertNotIn("Dev Ramaswamy", clean)
        self.assertIn("NAME", cats)

    def test_asset_name_not_treated_as_person_name(self):
        # Guards against over-eager NAME matching: "Chiller CH-04" must survive.
        text = "Chiller CH-04 was short-cycling before the visit."
        clean, cats = redaction.redact(text)
        self.assertIn("Chiller CH-04", clean)
        self.assertNotIn("NAME", cats)

    def test_all_categories_in_one_string_all_removed(self):
        # This is the "partial redaction is a failure" case from spec.md §4.
        text = (
            "Site contact is Margaret Oyelaran, mobile 07700 900412, email "
            "margaret.o@example.com. Spare key held at 14 Alderman Court, flat 3B. "
            "Access code for the plant room is 4471."
        )
        clean, cats = redaction.redact(text)
        for leaked in [
            "Margaret Oyelaran",
            "07700 900412",
            "margaret.o@example.com",
            "Alderman Court",
            "4471",
        ]:
            self.assertNotIn(leaked, clean, f"{leaked!r} leaked into redacted output")
        self.assertEqual(
            set(cats), {"NAME", "PHONE", "EMAIL", "ADDRESS", "ACCESS_CODE"}
        )

    def test_no_redaction_needed_leaves_text_intact(self):
        text = "Belt within wear tolerance, recommend replacement at next PM visit."
        clean, cats = redaction.redact(text)
        self.assertEqual(clean, text)
        self.assertEqual(cats, [])

    def test_empty_text(self):
        clean, cats = redaction.redact("")
        self.assertEqual(clean, "")
        self.assertEqual(cats, [])


if __name__ == "__main__":
    unittest.main()
