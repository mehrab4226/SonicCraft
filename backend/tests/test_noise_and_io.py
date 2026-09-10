import tempfile
import unittest
from pathlib import Path

import numpy as np

from soniccraft.audio_io import inspect_audio, load_audio, read_audio_bytes, save_audio, write_audio_bytes
from soniccraft.dsp.noise_reduction import estimate_noise_profile, spectral_gate, spectral_subtraction, wiener_denoise


class NoiseAndIOTests(unittest.TestCase):
    def test_audio_file_and_byte_round_trips(self):
        sample_rate = 8_000
        samples = 0.25 * np.sin(2 * np.pi * 440 * np.arange(sample_rate) / sample_rate)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            save_audio(path, samples, sample_rate, subtype="PCM_16")
            decoded, decoded_rate = load_audio(path)
            metadata = inspect_audio(path)
            self.assertEqual(decoded_rate, sample_rate)
            self.assertEqual(decoded.shape, samples.shape)
            self.assertEqual(metadata.frames, sample_rate)
            self.assertEqual(metadata.channels, 1)

        payload = write_audio_bytes(samples, sample_rate)
        from_bytes, byte_rate, byte_metadata = read_audio_bytes(payload)
        self.assertEqual(byte_rate, sample_rate)
        self.assertEqual(byte_metadata.frames, sample_rate)
        np.testing.assert_allclose(from_bytes, samples, atol=4e-5)

    def test_noise_algorithms_preserve_shape_and_finite_values(self):
        sample_rate = 8_000
        rng = np.random.default_rng(7)
        noise_only = rng.normal(0, 0.02, 2_000)
        times = np.arange(4_000) / sample_rate
        noisy = 0.2 * np.sin(2 * np.pi * 440 * times) + rng.normal(0, 0.02, times.size)
        profile = estimate_noise_profile(noise_only, sample_rate, n_fft=256, hop_length=64)
        for cleaned in (
            spectral_subtraction(noisy, sample_rate, profile),
            spectral_gate(noisy, sample_rate, profile),
            wiener_denoise(noisy, window_size=15),
        ):
            self.assertEqual(cleaned.shape, noisy.shape)
            self.assertTrue(np.all(np.isfinite(cleaned)))


if __name__ == "__main__":
    unittest.main()
