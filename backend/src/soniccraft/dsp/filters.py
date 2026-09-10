"""Reusable IIR filters and parametric/graphic equalizer processing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import signal

from ._validation import as_audio_array, validate_positive_int, validate_sample_rate

FilterKind = Literal["lowpass", "highpass", "bandpass", "bandstop"]


@dataclass(frozen=True, slots=True)
class FilterResponse:
    frequencies: NDArray[np.float64]
    magnitude_db: NDArray[np.float64]
    phase_radians: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class ParametricEQBand:
    frequency: float
    gain_db: float
    q: float = 1.0


def butterworth(
    cutoff: float | tuple[float, float],
    sample_rate: float,
    *,
    kind: FilterKind,
    order: int = 4,
) -> NDArray[np.float64]:
    """Design a Butterworth filter as numerically stable second-order sections."""

    rate = validate_sample_rate(sample_rate)
    filter_order = validate_positive_int(order, name="order")
    if kind not in {"lowpass", "highpass", "bandpass", "bandstop"}:
        raise ValueError("invalid Butterworth filter kind")
    frequencies = np.atleast_1d(np.asarray(cutoff, dtype=np.float64))
    expected = 2 if kind in {"bandpass", "bandstop"} else 1
    if frequencies.size != expected or not np.all(np.isfinite(frequencies)):
        raise ValueError(f"{kind} requires {expected} finite cutoff frequency value(s)")
    if np.any(frequencies <= 0) or np.any(frequencies >= rate / 2):
        raise ValueError("cutoff frequencies must be between 0 and the Nyquist frequency")
    if frequencies.size == 2 and frequencies[0] >= frequencies[1]:
        raise ValueError("lower cutoff must be below upper cutoff")
    wn: float | NDArray[np.float64] = float(frequencies[0]) if frequencies.size == 1 else frequencies
    return signal.butter(filter_order, wn, btype=kind, fs=rate, output="sos")


def apply_filter(audio: ArrayLike, sections: ArrayLike, *, zero_phase: bool = False) -> NDArray[np.float64]:
    """Apply second-order sections along the sample axis."""

    samples = as_audio_array(audio)
    sos = np.asarray(sections, dtype=np.float64)
    if sos.ndim != 2 or sos.shape[1] != 6 or not np.all(np.isfinite(sos)):
        raise ValueError("sections must be a finite array with shape (n, 6)")
    if zero_phase:
        try:
            return signal.sosfiltfilt(sos, samples, axis=0)
        except ValueError as error:
            raise ValueError("audio is too short for zero-phase filtering") from error
    return signal.sosfilt(sos, samples, axis=0)


def lowpass(audio: ArrayLike, sample_rate: float, cutoff: float, *, order: int = 4, zero_phase: bool = False) -> NDArray[np.float64]:
    return apply_filter(audio, butterworth(cutoff, sample_rate, kind="lowpass", order=order), zero_phase=zero_phase)


def highpass(audio: ArrayLike, sample_rate: float, cutoff: float, *, order: int = 4, zero_phase: bool = False) -> NDArray[np.float64]:
    return apply_filter(audio, butterworth(cutoff, sample_rate, kind="highpass", order=order), zero_phase=zero_phase)


def bandpass(audio: ArrayLike, sample_rate: float, low_cutoff: float, high_cutoff: float, *, order: int = 4, zero_phase: bool = False) -> NDArray[np.float64]:
    sections = butterworth((low_cutoff, high_cutoff), sample_rate, kind="bandpass", order=order)
    return apply_filter(audio, sections, zero_phase=zero_phase)


def bandstop(audio: ArrayLike, sample_rate: float, low_cutoff: float, high_cutoff: float, *, order: int = 4, zero_phase: bool = False) -> NDArray[np.float64]:
    sections = butterworth((low_cutoff, high_cutoff), sample_rate, kind="bandstop", order=order)
    return apply_filter(audio, sections, zero_phase=zero_phase)


def notch_filter(audio: ArrayLike, sample_rate: float, frequency: float, *, q: float = 30.0, zero_phase: bool = False) -> NDArray[np.float64]:
    """Remove a narrow tonal component such as 50/60 Hz mains hum."""

    rate = validate_sample_rate(sample_rate)
    if not 0 < frequency < rate / 2:
        raise ValueError("frequency must be between 0 and the Nyquist frequency")
    if not np.isfinite(q) or q <= 0:
        raise ValueError("q must be finite and positive")
    numerator, denominator = signal.iirnotch(frequency, q, fs=rate)
    return apply_filter(audio, signal.tf2sos(numerator, denominator), zero_phase=zero_phase)


def peaking_eq_sections(band: ParametricEQBand, sample_rate: float) -> NDArray[np.float64]:
    """Create an RBJ peaking-EQ biquad in SOS representation."""

    rate = validate_sample_rate(sample_rate)
    if not 0 < band.frequency < rate / 2:
        raise ValueError("EQ frequency must be between 0 and the Nyquist frequency")
    if not np.isfinite(band.gain_db):
        raise ValueError("EQ gain must be finite")
    if not np.isfinite(band.q) or band.q <= 0:
        raise ValueError("EQ Q must be finite and positive")

    amplitude = 10.0 ** (band.gain_db / 40.0)
    omega = 2.0 * np.pi * band.frequency / rate
    alpha = np.sin(omega) / (2.0 * band.q)
    cosine = np.cos(omega)
    numerator = np.array([1 + alpha * amplitude, -2 * cosine, 1 - alpha * amplitude])
    denominator = np.array([1 + alpha / amplitude, -2 * cosine, 1 - alpha / amplitude])
    numerator /= denominator[0]
    denominator /= denominator[0]
    return signal.tf2sos(numerator, denominator)


def apply_parametric_eq(
    audio: ArrayLike,
    sample_rate: float,
    bands: Sequence[ParametricEQBand],
    *,
    zero_phase: bool = False,
) -> NDArray[np.float64]:
    """Apply a cascade of parametric peaking filters."""

    samples = as_audio_array(audio)
    if not bands:
        return samples.copy()
    sections = np.vstack([peaking_eq_sections(band, sample_rate) for band in bands])
    return apply_filter(samples, sections, zero_phase=zero_phase)


def graphic_equalizer(
    audio: ArrayLike,
    sample_rate: float,
    center_frequencies: Sequence[float],
    gains_db: Sequence[float],
    *,
    q: float = 1.4,
    zero_phase: bool = False,
) -> NDArray[np.float64]:
    if len(center_frequencies) != len(gains_db):
        raise ValueError("center_frequencies and gains_db must have equal length")
    bands = [ParametricEQBand(float(frequency), float(gain), q) for frequency, gain in zip(center_frequencies, gains_db, strict=True)]
    return apply_parametric_eq(audio, sample_rate, bands, zero_phase=zero_phase)


def frequency_response(sections: ArrayLike, sample_rate: float, *, points: int = 2048) -> FilterResponse:
    """Return the frequency response used to draw EQ/filter curves."""

    sos = np.asarray(sections, dtype=np.float64)
    rate = validate_sample_rate(sample_rate)
    count = validate_positive_int(points, name="points")
    frequencies, response = signal.sosfreqz(sos, worN=count, fs=rate)
    magnitude = 20.0 * np.log10(np.maximum(np.abs(response), np.finfo(np.float64).eps))
    return FilterResponse(frequencies, magnitude, np.unwrap(np.angle(response)))
