"""Level, quality, and visualization summaries for audio signals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._validation import as_audio_array, to_2d, validate_positive_int, validate_sample_rate


@dataclass(frozen=True, slots=True)
class WaveformEnvelope:
    times: NDArray[np.float64]
    minimum: NDArray[np.float64]
    maximum: NDArray[np.float64]
    rms: NDArray[np.float64]


def _channel_result(values: NDArray[np.float64], mono: bool) -> float | NDArray[np.float64]:
    return float(values[0]) if mono else values


def peak_amplitude(audio: ArrayLike) -> float | NDArray[np.float64]:
    """Return absolute peak amplitude per channel."""

    samples, mono = to_2d(as_audio_array(audio))
    return _channel_result(np.max(np.abs(samples), axis=0), mono)


def rms(audio: ArrayLike) -> float | NDArray[np.float64]:
    """Return root-mean-square amplitude per channel."""

    samples, mono = to_2d(as_audio_array(audio))
    values = np.sqrt(np.mean(np.square(samples), axis=0))
    return _channel_result(values, mono)


def amplitude_to_db(amplitude: ArrayLike, *, floor_db: float = -120.0) -> NDArray[np.float64]:
    """Convert linear amplitude to decibels with a finite noise floor."""

    values = np.asarray(amplitude, dtype=np.float64)
    if floor_db >= 0:
        raise ValueError("floor_db must be negative")
    floor = 10.0 ** (floor_db / 20.0)
    return 20.0 * np.log10(np.maximum(np.abs(values), floor))


def db_to_amplitude(decibels: ArrayLike) -> NDArray[np.float64]:
    return np.power(10.0, np.asarray(decibels, dtype=np.float64) / 20.0)


def dbfs(audio: ArrayLike, *, floor_db: float = -120.0) -> float | NDArray[np.float64]:
    """Return RMS level in dBFS for normalized floating-point audio."""

    values = np.atleast_1d(np.asarray(rms(audio), dtype=np.float64))
    result = amplitude_to_db(values, floor_db=floor_db)
    return float(result[0]) if np.asarray(audio).ndim == 1 else result


def crest_factor_db(audio: ArrayLike, *, floor_db: float = -120.0) -> float | NDArray[np.float64]:
    peak = np.atleast_1d(np.asarray(peak_amplitude(audio), dtype=np.float64))
    level = np.atleast_1d(np.asarray(rms(audio), dtype=np.float64))
    ratio = peak / np.maximum(level, 10.0 ** (floor_db / 20.0))
    result = amplitude_to_db(ratio, floor_db=floor_db)
    return float(result[0]) if np.asarray(audio).ndim == 1 else result


def zero_crossing_rate(audio: ArrayLike) -> float | NDArray[np.float64]:
    samples, mono = to_2d(as_audio_array(audio))
    if samples.shape[0] < 2:
        values = np.zeros(samples.shape[1], dtype=np.float64)
    else:
        signs = np.signbit(samples)
        values = np.mean(signs[1:] != signs[:-1], axis=0)
    return _channel_result(values, mono)


def clipping_mask(audio: ArrayLike, *, threshold: float = 1.0) -> NDArray[np.bool_]:
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    return np.abs(as_audio_array(audio)) >= threshold


def clipping_fraction(audio: ArrayLike, *, threshold: float = 1.0) -> float | NDArray[np.float64]:
    mask, mono = to_2d(clipping_mask(audio, threshold=threshold))
    values = np.mean(mask, axis=0)
    return _channel_result(values, mono)


def waveform_envelope(audio: ArrayLike, sample_rate: float, bins: int = 1000) -> WaveformEnvelope:
    """Downsample audio into min/max/RMS bins suitable for waveform rendering."""

    samples, mono = to_2d(as_audio_array(audio))
    rate = validate_sample_rate(sample_rate)
    count = min(validate_positive_int(bins, name="bins"), samples.shape[0])
    edges = np.linspace(0, samples.shape[0], count + 1, dtype=np.int64)

    minimum = np.empty((count, samples.shape[1]), dtype=np.float64)
    maximum = np.empty_like(minimum)
    rms_values = np.empty_like(minimum)
    for index, (start, end) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        chunk = samples[start:end]
        minimum[index] = np.min(chunk, axis=0)
        maximum[index] = np.max(chunk, axis=0)
        rms_values[index] = np.sqrt(np.mean(np.square(chunk), axis=0))

    times = ((edges[:-1] + edges[1:]) / 2.0) / rate
    if mono:
        minimum = minimum[:, 0]
        maximum = maximum[:, 0]
        rms_values = rms_values[:, 0]
    return WaveformEnvelope(times=times, minimum=minimum, maximum=maximum, rms=rms_values)
