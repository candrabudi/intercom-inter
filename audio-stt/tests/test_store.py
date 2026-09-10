import json
import tempfile
import unittest
from pathlib import Path

from app.store import SessionStore


class SessionStoreTests(unittest.TestCase):
    def test_keeps_device_metadata_and_exports_ordered_txt(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = SessionStore(Path(temporary_directory))
            store.create("ses_test", {"mic_a": 1, "speaker_a": 2, "mic_b": 3, "speaker_b": 4})
            store.add(
                "ses_test",
                {"type": "transcript.final", "speaker": "B", "text": "Kedua", "started_at_ms": 200},
            )
            store.add(
                "ses_test",
                {"type": "transcript.final", "speaker": "A", "text": "Pertama", "started_at_ms": 100},
            )
            output = store.finish("ses_test")

            data = json.loads((Path(temporary_directory) / "ses_test.json").read_text(encoding="utf-8"))
            self.assertEqual(data["devices"]["mic_a"], 1)
            self.assertEqual(output.read_text(encoding="utf-8"), "[A] Pertama\n[B] Kedua\n")


if __name__ == "__main__":
    unittest.main()
