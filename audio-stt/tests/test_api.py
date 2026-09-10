import unittest

from fastapi.testclient import TestClient

from stt_local.main import app


class ApiTests(unittest.TestCase):
    def test_status_is_available_without_an_audio_session(self):
        with TestClient(app) as client:
            response = client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["running"])

    def test_devices_report_a_kind(self):
        with TestClient(app) as client:
            response = client.get("/api/devices")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(all("kind" in device and "selectable" in device for device in payload["devices"]))
        self.assertIn("headset_pairs", payload)


if __name__ == "__main__":
    unittest.main()
