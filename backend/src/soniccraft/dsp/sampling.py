"""Sampling-theorem, resampling, interpolation, and aliasing helpers."""

from __future__ import annotations

from fractions import Fraction

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import signal

from ._validation import as_audio_array, validate_positive_int, validate_sample_rate


def nyquist_frequency(sample_rate: float) -> float:
    return validate_sample_rate(sample_rate) / 2.0


def minimum_sample_rate(maximum_frequency: float) -> float:
    if not np.isfinite(maximum_frequency) or maximum_frequency < 0:
        raise ValueError("maximum_frequency must be finite and non-negative")
    return 2.0 * float(maximum_frequency)


def is_bandlimited(maximum_frequency: float, sample_rate: float, *, inclusive: bool = True) -> bool:
    nyquist = nyquist_frequency(sample_rate)
    return maximum_frequency <= nyquist if inclusive else maximum_frequency < nyquist


def alias_frequency(frequency: ArrayLike, sample_rate: float) -> NDArray[np.float64]:
    """Fold arbitrary frequencies into the observable interval [0, Nyquist]."""

    rate = validate_sample_rate(sample_rate)
    values = np.asarray(frequency, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("frequency must contain only finite values")
    wrapped = np.mod(np.abs(values), rate)
    return np.where(wrapped > rate / 2.0, rate - wrapped, wrapped)


def sample_function(function, sample_rate: float, duration_seconds: float, *, start_seconds: float = 0.0) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Uniformly sample a callable continuous-time signal."""

    rate = validate_sample_rate(sample_rate)
    if not np.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("duration_seconds must be finite and positive")
    count = int(np.floor(duration_seconds * rate))
    if count < 1:
        raise ValueError("duration is shorter than one sample interval")
    times = start_seconds + np.arange(count, dtype=np.float64) / rate
    values = np.asarray(function(times), dtype=np.float64)
    if values.shape[0] != count or not np.all(np.isfinite(values)):
        raise ValueError("function must return one finite value per sample time")
    return times, values


def resample_audio(audio: ArrayLike, source_rate: int, target_rate: int) -> NDArray[np.float64]:
    """Band-limited polyphase resampling along the sample axis."""

    samples = as_audio_array(audio)
    source = int(validate_sample_rate(source_rate))
    target = int(validate_sample_rate(target_rate))
    if source == target:
        return samples.copy()
    ratio = Fraction(target, source)
    return signal.resample_poly(samples, ratio.numerator, ratio.denominator, axis=0)


def downsample(audio: ArrayLike, factor: int, *, anti_alias: bool = True) -> NDArray[np.float64]:
    """Reduce the sample rate by an integer factor, with anti-alias filtering by default."""

    samples = as_audio_array(audio)
    value = validate_positive_int(factor, name="factor")
    if value == 1:
        return samples.copy()
    if anti_alias:
        return signal.resample_poly(samples, 1, value, axis=0)
    return samples[::value].copy()


def upsample(audio: ArrayLike, factor: int) -> NDArray[np.float64]:
    """Increase the sample rate by an integer factor using polyphase interpolation."""

    samples = as_audio_array(audio)
    value = validate_positive_int(factor, name="factor")
    return samples.copy() if value == 1 else signal.resample_poly(samples, value, 1, axis=0)


def sinc_interpolate(samples: ArrayLike, sample_times: ArrayLike, query_times: ArrayLike, sample_rate: float) -> NDArray[np.float64]:
    """Ideal band-limited interpolation for small educational demonstrations."""

    values = as_audio_array(samples, name="samples")
    times = np.asarray(sample_times, dtype=np.float64)
    query = np.asarray(query_times, dtype=np.float64)
    rate = validate_sample_rate(sample_rate)
    if times.ndim != 1 or times.size != values.shape[0] or not np.all(np.isfinite(times)):
        raise ValueError("sample_times must be finite and match the sample count")
    if not np.all(np.isfinite(query)):
        raise ValueError("query_times must be finite")
    kernel = np.sinc((query.ravel()[:, None] - times[None, :]) * rate)
    output = kernel @ values
    return output.reshape(query.shape + values.shape[1:])
