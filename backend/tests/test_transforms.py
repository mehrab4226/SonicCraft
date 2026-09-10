import unittest

import numpy as np

from soniccraft.dsp.transforms import (
    discrete_fourier_transform,
    fft_spectrum,
    fourier_series_coefficients,
    griffin_lim,
    inverse_discrete_fourier_transform,
    inverse_stft,
    reconstruct_fourier_series,
    spectrogram,
    stft,
)


class TransformTests(unittest.TestCase):
    def test_direct_dft_matches_numpy_and_inverts(self):
        samples = np.array([1.0, -0.5, 0.25, 0.75])
        transformed = discrete_fourier_transform(samples)
        np.testing.assert_allclose(transformed, np.fft.fft(samples), atol=1e-12)
        np.testing.assert_allclose(
            inverse_discrete_fourier_transform(transformed).real,
            samples,
            atol=1e-12,
        )

    def test_fft_spectrum_finds_tone_and_amplitude(self):
        sample_rate = 8_000
        frequency = 1_000
        times = np.arange(sample_rate) / sample_rate
        samples = 0.5 * np.sin(2 * np.pi * frequency * times)
        result = fft_spectrum(samples, sample_rate, window="hann")
        peak_index = int(np.argmax(result.magnitude))
        self.assertAlmostEqual(result.frequencies[peak_index], frequency)
        self.assertAlmostEqual(result.magnitude[peak_index], 0.5, places=5)

    def test_stft_round_trip_mono_and_stereo(self):
        rng = np.random.default_rng(42)
        mono = rng.normal(0, 0.1, 4_097)
        stereo = np.column_stack((mono, mono * 0.5))
        for samples in (mono, stereo):
            transformed = stft(samples, 44_100, n_fft=512, hop_length=128)
            reconstructed = inverse_stft(transformed)
            self.assertEqual(reconstructed.shape, samples.shape)
            np.testing.assert_allclose(reconstructed, samples, atol=1e-9)

    def test_spectrogram_dimensions_and_scale(self):
        samples = np.ones(2_000)
        result = spectrogram(samples, 8_000, n_fft=256, scale="db")
        self.assertEqual(result.values.shape[0], 129)
        self.assertEqual(result.values.shape[1], result.times.size)
        self.assertTrue(np.all(np.isfinite(result.values)))

    def test_fourier_series_reconstructs_sampled_period(self):
        phase = np.arange(15) / 15
        period = np.cos(2 * np.pi * phase) + 0.25 * np.sin(4 * np.pi * phase)
        series = fourier_series_coefficients(period, harmonics=7)
        reconstructed = reconstruct_fourier_series(series, phase)
        np.testing.assert_allclose(reconstructed, period, atol=1e-12)

    def test_griffin_lim_reconstruction_is_finite_and_bounded(self):
        sample_rate = 8_000
        samples = np.sin(2 * np.pi * 440 * np.arange(1_024) / sample_rate)
        transformed = stft(samples, sample_rate, n_fft=128, hop_length=32)
        reconstructed = griffin_lim(
            np.abs(transformed.spectrum),
            sample_rate,
            n_fft=128,
            hop_length=32,
            iterations=4,
        )
        self.assertEqual(reconstructed.shape, samples.shape)
        self.assertTrue(np.all(np.isfinite(reconstructed)))
        self.assertLessEqual(float(np.max(np.abs(reconstructed))), 1.0)


if __name__ == "__main__":
    unittest.main()
