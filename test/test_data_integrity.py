import os
import tempfile
import json
import unittest
from src.validation import DataValidator


class TestDataIntegrity(unittest.TestCase):
    def _create_sample_folder(self, tmp_dir):
        os.makedirs(tmp_dir, exist_ok=True)
        # create steamspy_data.jsonl
        with open(os.path.join(tmp_dir, "steamspy_data.jsonl"), "w", encoding="utf-8") as f:
            json.dump({"appid": 1, "name": "Game A"}, f)
            f.write("\n")
        # create scraped_appids.txt
        with open(os.path.join(tmp_dir, "scraped_appids.txt"), "w", encoding="utf-8") as f:
            f.write("1\n")
        # create metadata.json
        with open(os.path.join(tmp_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"start_time": "2025-01-01", "end_time": "2025-01-01", "apps_scraped": 1}, f)

    def test_check_folder_valid(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._create_sample_folder(tmp_dir)
            validator = DataValidator(tmp_dir)
            result = validator.validate()
            self.assertTrue(result.is_valid, f"Expected valid, got errors: {result.errors}")

    def test_check_folder_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # don't create files
            validator = DataValidator(tmp_dir)
            result = validator.validate()
            self.assertFalse(result.is_valid, "Expected invalid due to missing files")


if __name__ == "__main__":
    unittest.main()
