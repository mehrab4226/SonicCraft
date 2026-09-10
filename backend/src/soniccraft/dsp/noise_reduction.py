"""Deterministic noise-reduction algorithms with reusable noise profiles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import ndimage, signal

from ._validation import as_audio_array, validate_positive_int, validate_probability, validate_sample_rate
from .transforms import STFTResult, inverse_stft, stft


@dataclass(frozen=True, slots=True)
class NoiseProfile:
    magnitude: NDArray[np.float64]
    sample_rate: float
    n_fft: int
    hop_length: int
    window: str


def estimate_noise_profile(
    noise_audio: ArrayLike,
    sample_rate: float,
    *,
    n_fft: int = 2048,
    hop_length: int | None = None,
    window: str = "hann",
    statistic: str = "median",
) -> NoiseProfile:
    """Estimate typical per-frequency noise magnitude from a noise-only region."""

    transform = stft(noise_audio, sample_rate, n_fft=n_fft, hop_length=hop_length, window=window)
    magnitudes = np.abs(transform.spectrum)
    if statistic == "median":
        profile = np.median(magnitudes, axis=1)
    elif statistic == "mean":
        profile = np.mean(magnitudes, axis=1)
    else:
        raise ValueError("statistic must be 'median' or 'mean'")
    return NoiseProfile(profile, transform.sample_rate, transform.n_fft, transform.hop_length, transform.window)


def _validate_profile(profile: NoiseProfile, transform: STFTResult) -> NDArray[np.float64]:
    if profile.sample_rate != transform.sample_rate or profile.n_fft != transform.n_fft or profile.hop_length != transform.hop_length:
        raise ValueError("noise profile and target STFT parameters must match")
    noise = np.asarray(profile.magnitude, dtype=np.float64)
    expected_frequency_bins = transform.spectrum.shape[0]
    if noise.shape[0] != expected_frequency_bins:
        raise ValueError("noise profile frequency-bin count does not match target")
    if transform.spectrum.ndim == 2:
        if noise.ndim == 2:
            noise = np.mean(noise, axis=1)
        return noise[:, None]
    if noise.ndim == 1:
        noise = noise[:, None]
    if noise.shape[1] not in (1, transform.spectrum.shape[2]):
        raise ValueError("noise profile channel count does not match target")
    return noise[:, None, :]


def spectral_subtraction(
    audio: ArrayLike,
    sample_rate: float,
    profile: NoiseProfile,
    *,
    strength: float = 1.0,
    floor: float = 0.02,
) -> NDArray[np.float64]:
    """Subtract a stationary noise magnitude estimate while preserving phase."""

    if not np.isfinite(strength) or strength < 0:
        raise ValueError("strength must be finite and non-negative")
    residual_floor = validate_probability(floor, name="floor")
    samples = as_audio_array(audio)
    transform = stft(samples, sample_rate, n_fft=profile.n_fft, hop_length=profile.hop_length, window=profile.window)
    noise = _validate_profile(profile, transform)
    magnitude = np.abs(transform.spectrum)
    phase = transform.spectrum / np.maximum(magnitude, np.finfo(np.float64).eps)
    cleaned = np.maximum(magnitude - strength * noise, residual_floor * magnitude)
    updated = STFTResult(
        transform.frequencies, transform.times, cleaned * phase, transform.sample_rate,
        transform.n_fft, transform.hop_length, transform.window,
        transform.original_length, transform.centered,
    )
    return inverse_stft(updated)


def spectral_gate(
    audio: ArrayLike,
    sample_rate: float,
    profile: NoiseProfile,
    *,
    threshold: float = 1.5,
    reduction: float = 0.85,
    frequency_smoothing: int = 3,
    time_smoothing: int = 3,
) -> NDArray[np.float64]:
    """Attenuate time-frequency bins below a multiple of the noise profile."""

    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive")
    amount = validate_probability(reduction, name="reduction")
    frequency_width = validate_positive_int(frequency_smoothing, name="frequency_smoothing")
    time_width = validate_positive_int(time_smoothing, name="time_smoothing")
    samples = as_audio_array(audio)
    transform = stft(samples, sample_rate, n_fft=profile.n_fft, hop_length=profile.hop_length, window=profile.window)
    noise = _validate_profile(profile, transform)
    magnitude = np.abs(transform.spectrum)
    mask = (magnitude >= threshold * noise).astype(np.float64)
    mask = ndimage.uniform_filter1d(mask, size=frequency_width, axis=0, mode="nearest")
    mask = ndimage.uniform_filter1d(mask, size=time_width, axis=1, mode="nearest")
    gain = (1.0 - amount) + amount * mask
    updated = STFTResult(
        transform.frequencies, transform.times, transform.spectrum * gain,
        transform.sample_rate, transform.n_fft, transform.hop_length,
        transform.window, transform.original_length, transform.centered,
    )
    return inverse_stft(updated)


def wiener_denoise(audio: ArrayLike, *, window_size: int = 29, noise_power: float | None = None) -> NDArray[np.float64]:
    """Apply a local Wiener filter independently to each channel."""

    samples = as_audio_array(audio)
    size = validate_positive_int(window_size, name="window_size")
    if size % 2 == 0:
        raise ValueError("window_size must be odd")
    if noise_power is not None and (not np.isfinite(noise_power) or noise_power < 0):
        raise ValueError("noise_power must be finite and non-negative")
    if samples.ndim == 1:
        return np.asarray(signal.wiener(samples, mysize=size, noise=noise_power), dtype=np.float64)
    return np.column_stack([signal.wiener(samples[:, channel], mysize=size, noise=noise_power) for channel in range(samples.shape[1])])
