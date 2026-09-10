"""Fourier, short-time Fourier, and spectrogram utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.signal import get_window

from ._validation import as_audio_array, validate_positive_int, validate_sample_rate

ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]
SpectrogramScale = Literal["magnitude", "power", "db"]


@dataclass(frozen=True, slots=True)
class Spectrum:
    frequencies: FloatArray
    complex_values: ComplexArray
    magnitude: FloatArray
    phase: FloatArray
    magnitude_db: FloatArray


@dataclass(frozen=True, slots=True)
class STFTResult:
    frequencies: FloatArray
    times: FloatArray
    spectrum: ComplexArray
    sample_rate: float
    n_fft: int
    hop_length: int
    window: str
    original_length: int
    centered: bool


@dataclass(frozen=True, slots=True)
class Spectrogram:
    frequencies: FloatArray
    times: FloatArray
    values: FloatArray
    scale: SpectrogramScale


@dataclass(frozen=True, slots=True)
class FourierSeries:
    harmonics: NDArray[np.int64]
    coefficients: ComplexArray


def discrete_fourier_transform(signal: ArrayLike) -> ComplexArray:
    """Compute the DFT directly from its definition (O(N²), for teaching/tests)."""

    samples = as_audio_array(signal, name="signal")
    if samples.ndim != 1:
        raise ValueError("discrete_fourier_transform accepts a one-dimensional signal")
    indices = np.arange(samples.size)
    basis = np.exp(-2j * np.pi * np.outer(indices, indices) / samples.size)
    return basis @ samples


def inverse_discrete_fourier_transform(spectrum: ArrayLike) -> ComplexArray:
    """Compute the inverse DFT directly from its definition."""

    values = np.asarray(spectrum, dtype=np.complex128)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("spectrum must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(values)):
        raise ValueError("spectrum contains NaN or infinite values")
    indices = np.arange(values.size)
    basis = np.exp(2j * np.pi * np.outer(indices, indices) / values.size)
    return (basis @ values) / values.size


def fft(signal: ArrayLike, *, n: int | None = None) -> ComplexArray:
    """Compute a fast Fourier transform along the sample axis."""

    samples = as_audio_array(signal, name="signal")
    size = None if n is None else validate_positive_int(n, name="n")
    return np.fft.fft(samples, n=size, axis=0)


def inverse_fft(spectrum: ArrayLike, *, n: int | None = None, real: bool = False) -> NDArray:
    values = np.asarray(spectrum, dtype=np.complex128)
    if values.ndim not in (1, 2) or values.shape[0] == 0 or not np.all(np.isfinite(values)):
        raise ValueError("spectrum must be a finite one- or two-dimensional array")
    size = None if n is None else validate_positive_int(n, name="n")
    result = np.fft.ifft(values, n=size, axis=0)
    return np.real_if_close(result) if real else result


def magnitude_to_db(magnitude: ArrayLike, *, reference: float = 1.0, floor_db: float = -120.0) -> FloatArray:
    """Convert a magnitude spectrum to dB relative to ``reference``."""

    values = np.asarray(magnitude, dtype=np.float64)
    if np.any(values < 0) or not np.all(np.isfinite(values)):
        raise ValueError("magnitude must contain finite non-negative values")
    if reference <= 0 or floor_db >= 0:
        raise ValueError("reference must be positive and floor_db must be negative")
    floor = reference * 10.0 ** (floor_db / 20.0)
    return 20.0 * np.log10(np.maximum(values, floor) / reference)


def db_to_magnitude(decibels: ArrayLike, *, reference: float = 1.0) -> FloatArray:
    if reference <= 0:
        raise ValueError("reference must be positive")
    values = np.asarray(decibels, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("decibels must contain finite values")
    return reference * np.power(10.0, values / 20.0)


def fft_spectrum(
    signal: ArrayLike,
    sample_rate: float,
    *,
    n_fft: int | None = None,
    window: str = "hann",
    remove_dc: bool = True,
    floor_db: float = -120.0,
) -> Spectrum:
    """Return a calibrated one-sided amplitude spectrum for real audio."""

    samples = as_audio_array(signal, name="signal")
    rate = validate_sample_rate(sample_rate)
    size = samples.shape[0] if n_fft is None else validate_positive_int(n_fft, name="n_fft")
    if size < 2:
        raise ValueError("n_fft must be at least 2")
    working = samples[:size]
    if working.shape[0] < size:
        padding = [(0, size - working.shape[0])] + ([(0, 0)] if working.ndim == 2 else [])
        working = np.pad(working, padding)
    if remove_dc:
        working = working - np.mean(working, axis=0, keepdims=True)

    window_values = get_window(window, size, fftbins=True).astype(np.float64)
    windowed = working * (window_values[:, None] if working.ndim == 2 else window_values)
    complex_values = np.fft.rfft(windowed, n=size, axis=0)
    coherent_gain = float(np.sum(window_values))
    if abs(coherent_gain) <= np.finfo(np.float64).eps:
        raise ValueError("window has zero coherent gain")
    magnitude = np.abs(complex_values) / coherent_gain
    if size > 1:
        stop = -1 if size % 2 == 0 else None
        magnitude[1:stop] *= 2.0
    return Spectrum(
        frequencies=np.fft.rfftfreq(size, d=1.0 / rate),
        complex_values=complex_values,
        magnitude=magnitude,
        phase=np.angle(complex_values),
        magnitude_db=magnitude_to_db(magnitude, floor_db=floor_db),
    )


def fourier_series_coefficients(period: ArrayLike, *, harmonics: int | None = None) -> FourierSeries:
    """Estimate complex Fourier-series coefficients from one sampled period."""

    samples = as_audio_array(period, name="period")
    if samples.ndim != 1:
        raise ValueError("period must be one-dimensional")
    maximum = samples.size // 2
    count = maximum if harmonics is None else validate_positive_int(harmonics, name="harmonics")
    if count > maximum:
        raise ValueError(f"harmonics cannot exceed {maximum} for this period")
    shifted = np.fft.fftshift(np.fft.fft(samples) / samples.size)
    negative_count = samples.size // 2
    all_harmonics = np.arange(-negative_count, samples.size - negative_count)
    mask = (all_harmonics >= -count) & (all_harmonics <= count)
    return FourierSeries(harmonics=all_harmonics[mask], coefficients=shifted[mask])


def reconstruct_fourier_series(series: FourierSeries, phase: ArrayLike) -> FloatArray:
    """Evaluate a Fourier series at normalized phase values (one period is 0..1)."""

    positions = np.asarray(phase, dtype=np.float64)
    if not np.all(np.isfinite(positions)):
        raise ValueError("phase must contain finite values")
    values = np.exp(2j * np.pi * np.outer(positions.ravel(), series.harmonics)) @ series.coefficients
    return np.real_if_close(values).real.reshape(positions.shape)


def stft(
    signal: ArrayLike,
    sample_rate: float,
    *,
    n_fft: int = 2048,
    hop_length: int | None = None,
    window: str = "hann",
    center: bool = True,
) -> STFTResult:
    """Compute an STFT with output shape ``(frequency, time[, channel])``."""

    samples = as_audio_array(signal, name="signal")
    rate = validate_sample_rate(sample_rate)
    size = validate_positive_int(n_fft, name="n_fft")
    if size < 2:
        raise ValueError("n_fft must be at least 2")
    hop = size // 4 if hop_length is None else validate_positive_int(hop_length, name="hop_length")
    if hop > size:
        raise ValueError("hop_length cannot exceed n_fft")

    mono = samples.ndim == 1
    working = samples[:, None] if mono else samples
    pad_left = size // 2 if center else 0
    pad_right = size // 2 if center else 0
    working = np.pad(working, ((pad_left, pad_right), (0, 0)))
    frames = max(1, int(np.ceil(max(0, working.shape[0] - size) / hop)) + 1)
    target_length = (frames - 1) * hop + size
    if working.shape[0] < target_length:
        working = np.pad(working, ((0, target_length - working.shape[0]), (0, 0)))

    framed = np.stack([working[index * hop : index * hop + size] for index in range(frames)], axis=0)
    window_values = get_window(window, size, fftbins=True).astype(np.float64)
    transformed = np.fft.rfft(framed * window_values[None, :, None], axis=1)
    spectrum = np.transpose(transformed, (1, 0, 2))
    if mono:
        spectrum = spectrum[:, :, 0]

    return STFTResult(
        frequencies=np.fft.rfftfreq(size, d=1.0 / rate),
        times=np.arange(frames, dtype=np.float64) * hop / rate,
        spectrum=spectrum,
        sample_rate=rate,
        n_fft=size,
        hop_length=hop,
        window=window,
        original_length=samples.shape[0],
        centered=center,
    )


def inverse_stft(transform: STFTResult, *, length: int | None = None) -> FloatArray:
    """Reconstruct audio by weighted overlap-add."""

    spectrum = np.asarray(transform.spectrum, dtype=np.complex128)
    mono = spectrum.ndim == 2
    if spectrum.ndim not in (2, 3):
        raise ValueError("STFT spectrum must have shape (frequency, time[, channel])")
    spectrum_3d = spectrum[:, :, None] if mono else spectrum
    frames = np.transpose(spectrum_3d, (1, 0, 2))
    time_frames = np.fft.irfft(frames, n=transform.n_fft, axis=1)
    window_values = get_window(transform.window, transform.n_fft, fftbins=True).astype(np.float64)
    output_length = (frames.shape[0] - 1) * transform.hop_length + transform.n_fft
    output = np.zeros((output_length, frames.shape[2]), dtype=np.float64)
    normalization = np.zeros(output_length, dtype=np.float64)
    for index, frame in enumerate(time_frames):
        start = index * transform.hop_length
        output[start : start + transform.n_fft] += frame * window_values[:, None]
        normalization[start : start + transform.n_fft] += np.square(window_values)
    valid = normalization > np.finfo(np.float64).eps
    output[valid] /= normalization[valid, None]

    if transform.centered:
        pad = transform.n_fft // 2
        output = output[pad : output.shape[0] - pad]
    desired_length = transform.original_length if length is None else validate_positive_int(length, name="length")
    if output.shape[0] < desired_length:
        output = np.pad(output, ((0, desired_length - output.shape[0]), (0, 0)))
    else:
        output = output[:desired_length]
    return output[:, 0] if mono else output


def spectrogram(
    signal: ArrayLike,
    sample_rate: float,
    *,
    n_fft: int = 2048,
    hop_length: int | None = None,
    window: str = "hann",
    scale: SpectrogramScale = "db",
    floor_db: float = -120.0,
) -> Spectrogram:
    transform = stft(signal, sample_rate, n_fft=n_fft, hop_length=hop_length, window=window)
    magnitude = np.abs(transform.spectrum)
    if scale == "magnitude":
        values = magnitude
    elif scale == "power":
        values = np.square(magnitude)
    elif scale == "db":
        reference = max(float(np.max(magnitude)), np.finfo(np.float64).eps)
        values = magnitude_to_db(magnitude, reference=reference, floor_db=floor_db)
    else:
        raise ValueError("scale must be 'magnitude', 'power', or 'db'")
    return Spectrogram(transform.frequencies, transform.times, values, scale)


def griffin_lim(
    magnitude: ArrayLike,
    sample_rate: float,
    *,
    n_fft: int,
    hop_length: int | None = None,
    window: str = "hann",
    iterations: int = 32,
    center: bool = True,
    random_seed: int | None = 0,
) -> FloatArray:
    """Estimate a mono waveform from a magnitude spectrogram using Griffin-Lim."""

    values = np.asarray(magnitude, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] == 0 or np.any(values < 0) or not np.all(np.isfinite(values)):
        raise ValueError("magnitude must be a finite non-negative (frequency, time) array")
    rate = validate_sample_rate(sample_rate)
    size = validate_positive_int(n_fft, name="n_fft")
    if size < 2:
        raise ValueError("n_fft must be at least 2")
    hop = size // 4 if hop_length is None else validate_positive_int(hop_length, name="hop_length")
    count = validate_positive_int(iterations, name="iterations")
    if values.shape[0] != size // 2 + 1:
        raise ValueError("magnitude frequency bins do not match n_fft")

    rng = np.random.default_rng(random_seed)
    phase = np.exp(2j * np.pi * rng.random(values.shape))
    expected_length = max(1, (
        (values.shape[1] - 1) * hop
        if center
        else (values.shape[1] - 1) * hop + size
    ))
    estimate = np.zeros(expected_length, dtype=np.float64)
    for _ in range(count):
        transform = STFTResult(
            frequencies=np.fft.rfftfreq(size, d=1.0 / rate),
            times=np.arange(values.shape[1]) * hop / rate,
            spectrum=values * phase,
            sample_rate=rate,
            n_fft=size,
            hop_length=hop,
            window=window,
            original_length=expected_length,
            centered=center,
        )
        estimate = inverse_stft(transform)
        rebuilt = stft(estimate, rate, n_fft=size, hop_length=hop, window=window, center=center).spectrum
        phase = rebuilt / np.maximum(np.abs(rebuilt), np.finfo(np.float64).eps)
    peak = float(np.max(np.abs(estimate)))
    return estimate / peak if peak > 1.0 else estimate
