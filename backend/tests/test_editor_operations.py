import unittest
import numpy as np
from soniccraft.desktop.document import AudioData
from soniccraft.desktop.processing import process, sample_range
from soniccraft.desktop.waveform_widget import envelope
from soniccraft.desktop.processing import filter_sections
from soniccraft.dsp.noise_reduction import estimate_noise_profile
from soniccraft.dsp.filters import frequency_response


class EditingTests(unittest.TestCase):
    def setUp(self):
        self.samples = np.column_stack([np.linspace(-0.8, 0.8, 100), np.ones(100) * 0.2])
        self.audio = AudioData(self.samples, 100)

    def test_edits_change_only_selected_samples_and_keep_channels(self):
        for operation, expected in (
            ("reverse", self.samples[20:60][::-1]),
            ("silence", np.zeros((40, 2))),
            ("gain", self.samples[20:60] * 10 ** (6 / 20)),
        ):
            result = process(self.audio, (20, 60), operation, {"gain_db": 6})
            np.testing.assert_array_equal(result[:20], self.samples[:20])
            np.testing.assert_array_equal(result[60:], self.samples[60:])
            np.testing.assert_allclose(result[20:60], expected)
        np.testing.assert_array_equal(process(self.audio, (20, 60), "trim"), self.samples[20:60])
        np.testing.assert_array_equal(
            process(self.audio, (20, 60), "delete"), np.concatenate([self.samples[:20], self.samples[60:]])
        )
        with self.assertRaises(ValueError):
            process(self.audio, (0, 100), "delete")
        self.assertEqual(sample_range(self.audio, 0.2, 0.6), (20, 60))
        with self.assertRaises(ValueError):
            sample_range(self.audio, 0.2, 0.2)

    def test_gain_fade_normalize_and_preserved_original(self):
        for db in (-6, 0, 6):
            np.testing.assert_allclose(
                process(self.audio, (0, 100), "gain", {"gain_db": db}), self.samples * 10 ** (db / 20)
            )
        result = process(self.audio, (20, 60), "fade", {"seconds": 0.4, "direction": "fade_in"})
        np.testing.assert_allclose(result[20:60], self.samples[20:60] * np.linspace(0, 1, 40)[:, None])
        result = process(self.audio, (0, 100), "normalize")
        self.assertAlmostEqual(np.max(abs(result)), 10 ** (-1 / 20))
        np.testing.assert_array_equal(self.audio.samples, self.samples)

    def test_envelope_is_bounded_and_keeps_impulses(self):
        samples = np.zeros(200000)
        samples[12345] = 1
        times, values = envelope(samples, 48000)
        self.assertLessEqual(len(times), 10000)
        self.assertEqual(values.max(), 1)
        self.assertEqual(np.count_nonzero(samples), 1)

    def test_filter_attenuation_and_eq_response(self):
        rate = 8000
        t = np.arange(rate) / rate
        x = np.column_stack([np.sin(2*np.pi*200*t), np.sin(2*np.pi*2500*t)]) * 0.4
        audio = AudioData(x, rate)
        for kind, pass_channel in (("lowpass", 0), ("highpass", 1), ("bandpass", 0), ("bandstop", 1)):
            params = {"kind": kind, "low": 100 if kind.startswith("band") else 1000, "high": 600}
            result = process(audio, (0, rate), "filter", params)[1000:]
            levels = np.sqrt(np.mean(result**2, axis=0))
            self.assertGreater(levels[pass_channel], 0.2)
            self.assertLess(levels[1-pass_channel], 0.03)
        params = {"bands": [(1000, 6)]}
        response = frequency_response(filter_sections("eq", params, rate), rate)
        self.assertAlmostEqual(response.magnitude_db[np.argmin(abs(response.frequencies-1000))], 6, places=4)
        with self.assertRaises(ValueError):
            filter_sections("filter", {"kind": "lowpass", "low": 4000}, rate)

    def test_noise_methods_are_distinct_and_preserve_channels(self):
        rng = np.random.default_rng(3)
        noise = rng.normal(0, 0.03, (8000, 2))
        x = noise + np.sin(2*np.pi*400*np.arange(8000)/8000)[:, None] * 0.3
        audio = AudioData(x, 8000)
        profile = estimate_noise_profile(noise[:2000], 8000)
        results = [process(audio, (0, 8000), name, {"profile": profile}) for name in ("subtraction", "wiener", "gate")]
        for result in results:
            self.assertEqual(result.shape, x.shape)
            self.assertTrue(np.isfinite(result).all())
            self.assertFalse(np.allclose(result, x))
        self.assertFalse(np.allclose(results[0], results[1]))
