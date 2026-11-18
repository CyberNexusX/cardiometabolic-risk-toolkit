import copy
import unittest

from risk_study import build_cohort, generate


class CohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle, cls.metadata = generate(42)
        cls.rows = build_cohort(cls.bundle, cls.metadata)

    def test_no_overlap_and_no_incomplete_followup(self):
        self.assertEqual(len(self.rows), len({row["patient_id"] for row in self.rows}))
        for row in self.rows:
            self.assertEqual(row["site"] == "coastal", row["split"] == "held_out_site")
            if row["split"] == "train":
                self.assertTrue(row["index_date"].startswith("2022"))
        self.assertLess(len(self.rows), len(self.metadata))

    def test_future_lab_values_do_not_change_features(self):
        modified = copy.deepcopy(self.bundle)
        for entry in modified["entry"]:
            resource = entry["resource"]
            if resource["id"].endswith("-future"):
                resource["valueQuantity"]["value"] = 99
        self.assertEqual(self.rows, build_cohort(modified, self.metadata))

    def test_delayed_lab_result_is_excluded(self):
        patient_id = self.rows[0]["patient_id"]
        modified = copy.deepcopy(self.bundle)
        for entry in modified["entry"]:
            resource = entry["resource"]
            if resource["id"] == f"{patient_id}-latest":
                resource["issued"] = "2023-01-01T12:00:00Z"
        row = next(row for row in build_cohort(modified, self.metadata)
                   if row["patient_id"] == patient_id)
        self.assertNotEqual(row["latest_a1c_record"], f"{patient_id}-latest")


if __name__ == "__main__":
    unittest.main()
