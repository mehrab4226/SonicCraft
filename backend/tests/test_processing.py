import unittest

import numpy as np

from soniccraft.dsp.analysis import clipping_fraction, dbfs, waveform_envelope
from soniccraft.dsp.convolution import circular_convolution, convolution_sum, linear_convolution
from soniccraft.dsp.effects import apply_fade, apply_gain, concatenate_audio, mix_audio, normalize_peak
from soniccraft.dsp.filters import ParametricEQBand, apply_parametric_eq, lowpass, notch_filter
from soniccraft.dsp.sampling import alias_frequency, resample_audio, sinc_interpolate


class ProcessingTests(unittest.TestCase):
    def test_convolution_variants(self):
        x = np.array([1.0, 2.0, 3.0])
        h = np.array([0.5, 0.25])
        expected = np.convolve(x, h)
        np.testing.assert_allclose(convolution_sum(x, h), expected)
        np.testing.assert_allclose(linear_convolution(x, h), expected)
        expected_circular = np.fft.ifft(np.fft.fft(x) * np.fft.fft(h, 3)).real
        np.testing.assert_allclose(circular_convolution(x, h, length=3), expected_circular)

    def test_gain_fade_normalize_and_mix(self):
        samples = np.ones(100)
        np.testing.assert_allclose(apply_gain(samples, -6.020599913), 0.5, atol=1e-9)
        faded = apply_fade(
            samples,
            100,
            fade_in_seconds=0.5,
            fade_out_seconds=0.5,
            curve="linear",
        )
        self.assertEqual(faded[0], 0)
        self.assertEqual(faded[-1], 0)
        normalized = normalize_peak(samples * 0.1, -6.020599913)
        self.assertAlmostEqual(float(np.max(normalized)), 0.5, places=8)
        np.testing.assert_allclose(mix_audio([np.ones(4), np.ones(2)], offsets=[0, 2]), [1, 1, 2, 2])
        np.testing.assert_allclose(concatenate_audio([np.ones(2), np.zeros(2)]), [1, 1, 0, 0])

    def test_analysis_helpers(self):
        samples = np.array([0.0, 0.5, -1.0, 1.2])
        self.assertAlmostEqual(clipping_fraction(samples), 0.5)
        self.assertTrue(np.isfinite(dbfs(samples)))
        envelope = waveform_envelope(samples, 4, bins=2)
        np.testing.assert_allclose(envelope.minimum, [0.0, -1.0])
        np.testing.assert_allclose(envelope.maximum, [0.5, 1.2])

    def test_filters_are_finite_and_preserve_shape(self):
        sample_rate = 8_000
        times = np.arange(sample_rate) / sample_rate
        low = np.sin(2 * np.pi * 200 * times)
        high = np.sin(2 * np.pi * 2_000 * times)
        filtered = lowpass(low + high, sample_rate, 500, zero_phase=True)
        self.assertEqual(filtered.shape, low.shape)
        self.assertLess(np.sqrt(np.mean(np.square(filtered - low))), 0.05)
        self.assertTrue(np.all(np.isfinite(notch_filter(low + high, sample_rate, 200))))
        equalized = apply_parametric_eq(low, sample_rate, [ParametricEQBand(200, 3.0, 1.0)])
        self.assertEqual(equalized.shape, low.shape)

    def test_sampling_and_aliasing(self):
        np.testing.assert_allclose(
            alias_frequency([1_000, 5_000, 9_000], 8_000),
            [1_000, 3_000, 1_000],
        )
        source = np.sin(2 * np.pi * 0.01 * np.arange(100))
        self.assertEqual(resample_audio(source, 10_000, 20_000).shape[0], 200)
        times = np.arange(5) / 10
        np.testing.assert_allclose(
            sinc_interpolate(source[:5], times, times, 10),
            source[:5],
            atol=1e-12,
        )


if __name__ == "__main__":
    unittest.main()
