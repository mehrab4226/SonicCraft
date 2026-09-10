import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from soniccraft.api.app import app
from soniccraft.audio_io import read_audio_bytes, write_audio_bytes


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.rate = 8000
        cls.samples = 0.25 * np.sin(2 * np.pi * 440 * np.arange(cls.rate) / cls.rate)
        cls.payload = write_audio_bytes(cls.samples, cls.rate, subtype="FLOAT")

    def post_audio(self, path, data=None, payload=None):
        return self.client.post(
            "/api/v1" + path,
            files={"file": ("tone.wav", self.payload if payload is None else payload, "audio/wav")},
            data=data or {},
        )

    def test_health_and_cors(self):
        self.assertEqual(self.client.get("/api/v1/health").json()["status"], "ok")
        response = self.client.options("/api/v1/audio/inspect", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        })
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
        denied = self.client.options("/api/v1/audio/inspect", headers={
            "Origin": "https://unrelated.example", "Access-Control-Request-Method": "POST",
        })
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_inspection_mono_and_stereo_channel_contract(self):
        for samples in (self.samples, np.column_stack((self.samples, self.samples * 0.5))):
            response = self.post_audio("/audio/inspect?bins=32", payload=write_audio_bytes(samples, self.rate, subtype="FLOAT"))
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            channels = 1 if samples.ndim == 1 else 2
            self.assertEqual(result["metadata"]["frames"], self.rate)
            self.assertEqual(result["metadata"]["channels"], channels)
            self.assertEqual(len(result["waveform"]["minimum"]), channels)
            self.assertEqual(len(result["waveform"]["minimum"][0]), 32)
            self.assertAlmostEqual(result["levels"]["peak"][0], 0.25, places=6)
            self.assertEqual(result["levels"]["clipping_fraction"], [0.0] * channels)

    def test_import_gain_fade_trim_export_roundtrip(self):
        changed = self.post_audio("/audio/process/gain-fade", {
            "gain_db": -6.020599913, "fade_in_seconds": 0.1,
            "fade_out_seconds": 0.1, "curve": "linear",
        })
        self.assertEqual(changed.status_code, 200, changed.text[:100])
        audio, rate, metadata = read_audio_bytes(changed.content)
        self.assertEqual(metadata.subtype, "FLOAT")
        self.assertEqual(rate, self.rate)
        self.assertEqual(audio.shape, self.samples.shape)
        np.testing.assert_allclose(audio[1000:-1000], self.samples[1000:-1000] * 0.5, atol=1e-7)
        self.assertAlmostEqual(audio[-1], 0)
        inspected = self.post_audio("/audio/inspect", payload=changed.content)
        self.assertEqual(inspected.status_code, 200)
        trimmed = self.post_audio("/audio/process/trim", {"start_sample": 800, "end_sample": 4000}, changed.content)
        cut, _, _ = read_audio_bytes(trimmed.content)
        np.testing.assert_allclose(cut, audio[800:4000], atol=1e-7)
        exported = self.post_audio("/audio/export", {"gain_db": 0}, trimmed.content)
        decoded, _, metadata = read_audio_bytes(exported.content)
        self.assertEqual(metadata.subtype, "PCM_16")
        self.assertEqual(metadata.frames, 3200)
        np.testing.assert_allclose(decoded, cut, atol=4e-5)
        self.assertTrue(exported.headers["content-type"].startswith("audio/wav"))

    def test_clipping_is_explicit_and_normalization_is_optional(self):
        response = self.post_audio("/audio/export", {"gain_db": 24})
        self.assertEqual(response.status_code, 422)
        self.assertIn("clip", response.json()["detail"])
        normalized = self.post_audio("/audio/export", {"gain_db": 24, "normalize": "true"})
        self.assertEqual(normalized.status_code, 200)
        audio, _, _ = read_audio_bytes(normalized.content)
        self.assertAlmostEqual(np.max(np.abs(audio)), 10 ** (-1 / 20), delta=4e-5)
        revision = self.post_audio("/audio/process/gain-fade", {"gain_db": 24})
        self.assertEqual(revision.status_code, 200)
        audio, _, _ = read_audio_bytes(revision.content)
        self.assertGreater(float(np.max(np.abs(audio))), 1)

    def test_reject_invalid_files_and_parameters_without_server_errors(self):
        for payload in (b"", b"not audio"):
            self.assertEqual(self.post_audio("/audio/inspect", payload=payload).status_code, 422)
        for path, parameters in (
            ("/audio/process/gain-fade", {"gain_db": "NaN"}),
            ("/audio/process/gain-fade", {"gain_db": "inf"}),
            ("/audio/process/gain-fade", {"curve": "unknown"}),
            ("/audio/process/gain-fade", {"fade_in_seconds": -1}),
            ("/audio/process/gain-fade", {"fade_out_seconds": 2}),
            ("/audio/process/trim", {"start_sample": 500, "end_sample": 1}),
            ("/audio/process/trim", {"start_sample": 0, "end_sample": 8001}),
            ("/audio/process/trim", {"start_sample": 0.5, "end_sample": 800}),
            ("/audio/inspect?bins=100000", {}),
        ):
            with self.subTest(path=path, parameters=parameters):
                response = self.post_audio(path, parameters)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIsInstance(response.json()["detail"], str)

    def test_reject_limits_before_full_decode(self):
        with patch("soniccraft.api.services.MAX_UPLOAD_BYTES", 16):
            self.assertEqual(self.post_audio("/audio/inspect").status_code, 413)
        with patch("soniccraft.api.services.MAX_DECODED_SAMPLES", 100):
            self.assertEqual(self.post_audio("/audio/inspect").status_code, 413)
        with patch("soniccraft.api.services.MAX_DURATION_SECONDS", 0.1):
            self.assertEqual(self.post_audio("/audio/inspect").status_code, 413)
        multichannel = write_audio_bytes(np.zeros((800, 3)), self.rate)
        self.assertEqual(self.post_audio("/audio/inspect", payload=multichannel).status_code, 422)
        low_rate = write_audio_bytes(self.samples[:20], 4000)
        self.assertEqual(self.post_audio("/audio/inspect", payload=low_rate).status_code, 422)


if __name__ == "__main__":
    unittest.main()
