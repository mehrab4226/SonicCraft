"""Regression checks for the timeline mixer and its sample-rate conversion."""
import unittest

import numpy as np

from soniccraft.dsp.effects import mix_audio
from soniccraft.dsp.sampling import resample_audio
from soniccraft.dsp.transforms import fft_spectrum


class MixingTests(unittest.TestCase):
    def test_different_rates_keep_pitch_duration_and_timeline_offset(self):
        rate = 16000
        tone = .2 * np.sin(2 * np.pi * 1000 * np.arange(8000) / 8000)
        tracks = [dict(samples=np.zeros(rate), sample_rate=rate),
                  dict(samples=tone, sample_rate=8000, offset=.5, volume=.5)]
        output = mix_audio(tracks, rate)
        self.assertEqual(len(output), 24000)
        np.testing.assert_array_equal(output[:8000], 0)
        spectrum = fft_spectrum(output[8000:], rate)
        self.assertEqual(spectrum.frequencies[np.argmax(spectrum.magnitude)], 1000)
        self.assertAlmostEqual(float(spectrum.magnitude.max()), .1, places=3)

    def test_stereo_mono_mute_and_peak_protection(self):
        tracks = [dict(samples=np.column_stack((np.ones(8), np.zeros(8))), sample_rate=8),
                  dict(samples=np.ones((4, 1)), sample_rate=8, offset=.5),
                  dict(samples=np.ones(100), sample_rate=8, mute=True)]
        output = mix_audio(tracks, 8)
        self.assertEqual(output.shape, (8, 2))
        np.testing.assert_allclose(output[:4], np.tile([.5, 0], (4, 1)))
        np.testing.assert_allclose(output[4:], np.tile([1, .5], (4, 1)))

    def test_invalid_tracks_and_huge_offsets_fail_before_allocation(self):
        for overrides in [dict(offset=-1), dict(offset=np.inf), dict(volume=np.nan),
                          dict(sample_rate=0), dict(sample_rate=8000.5), dict(offset=1e9)]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                mix_audio([dict(samples=np.ones(10), sample_rate=8000, **{}) | overrides], 8000)
        with self.assertRaises(ValueError):
            mix_audio([dict(samples=np.ones(10), sample_rate=8000, mute=True)], 8000)

    def test_resampling_preserves_channels_and_rejects_fractional_rates(self):
        samples = np.column_stack((np.ones(100), np.zeros(100)))
        result = resample_audio(samples, 10000, 20000)
        self.assertEqual(result.shape, (200, 2))
        np.testing.assert_array_equal(result[:, 1], 0)
        with self.assertRaises(ValueError):
            resample_audio(samples, 10000.5, 20000)
