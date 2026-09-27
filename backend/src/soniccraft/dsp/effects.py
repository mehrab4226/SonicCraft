"""Non-destructive-style editing primitives, gain, fades, and mixing."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._validation import as_audio_array, broadcast_channels, restore_channels, validate_sample_rate, validate_positive_int
from .sampling import resample_audio

FadeCurve = Literal["linear", "equal_power", "exponential"]


def apply_gain(audio: ArrayLike, gain_db: float) -> NDArray[np.float64]:
    """Apply amplitude gain expressed in decibels."""

    if not np.isfinite(gain_db):
        raise ValueError("gain_db must be finite")
    return as_audio_array(audio) * (10.0 ** (float(gain_db) / 20.0))


def normalize_peak(audio: ArrayLike, target_dbfs: float = -1.0) -> NDArray[np.float64]:
    """Scale audio so its absolute peak reaches ``target_dbfs``."""

    if target_dbfs > 0 or not np.isfinite(target_dbfs):
        raise ValueError("target_dbfs must be finite and no greater than 0")
    samples = as_audio_array(audio)
    peak = float(np.max(np.abs(samples)))
    if peak == 0:
        return samples.copy()
    target = 10.0 ** (target_dbfs / 20.0)
    return samples * (target / peak)


def _fade_curve(length: int, curve: FadeCurve, *, fade_in: bool) -> NDArray[np.float64]:
    if curve not in {"linear", "equal_power", "exponential"}:
        raise ValueError("curve must be 'linear', 'equal_power', or 'exponential'")
    values = np.linspace(0.0, 1.0, length, endpoint=True)
    if curve == "equal_power":
        values = np.sin(values * np.pi / 2.0)
    elif curve == "exponential":
        values = np.square(values)
    return values if fade_in else values[::-1]


def apply_fade(
    audio: ArrayLike,
    sample_rate: float,
    *,
    fade_in_seconds: float = 0.0,
    fade_out_seconds: float = 0.0,
    curve: FadeCurve = "equal_power",
) -> NDArray[np.float64]:
    """Apply independent fade-in and fade-out envelopes."""

    samples = as_audio_array(audio)
    rate = validate_sample_rate(sample_rate)
    if fade_in_seconds < 0 or fade_out_seconds < 0:
        raise ValueError("fade durations cannot be negative")
    fade_in_samples = min(samples.shape[0], int(round(fade_in_seconds * rate)))
    fade_out_samples = min(samples.shape[0], int(round(fade_out_seconds * rate)))
    envelope = np.ones(samples.shape[0], dtype=np.float64)
    if fade_in_samples:
        envelope[:fade_in_samples] *= _fade_curve(fade_in_samples, curve, fade_in=True)
    if fade_out_samples:
        envelope[-fade_out_samples:] *= _fade_curve(fade_out_samples, curve, fade_in=False)
    if samples.ndim == 2:
        envelope = envelope[:, None]
    return samples * envelope


def trim_audio(audio: ArrayLike, start_sample: int, end_sample: int) -> NDArray[np.float64]:
    samples = as_audio_array(audio)
    if not 0 <= start_sample < end_sample <= samples.shape[0]:
        raise ValueError("trim range must satisfy 0 <= start < end <= sample count")
    return samples[start_sample:end_sample].copy()


def mix_audio(tracks: Sequence[dict], target_rate: int) -> NDArray[np.float64]:
    """Resample, offset and mix unmuted timeline tracks; protect the output peak."""
    rate = validate_positive_int(target_rate, name="target_rate")
    active = [track for track in tracks if not track.get("mute", False)]
    if not active:
        raise ValueError("At least one track must be unmuted.")
    converted, offsets, volumes = [], [], []
    for track in active:
        offset, volume = float(track.get("offset", 0)), float(track.get("volume", 1))
        if not np.isfinite(offset) or offset < 0 or not np.isfinite(volume) or volume < 0:
            raise ValueError("Track offsets and volumes must be finite and non-negative.")
        samples = as_audio_array(track["samples"], name="track samples")
        source_rate = validate_positive_int(track["sample_rate"], name="track sample_rate")
        channels = 1 if samples.ndim == 1 else samples.shape[1]
        if (round(offset * rate) + int(np.ceil(len(samples) * rate / source_rate))) * channels * 8 > 256 * 1024 * 1024:
            raise ValueError("Mix exceeds the 256 MiB audio budget. Reduce track lengths or offsets.")
        if source_rate != rate:
            samples = resample_audio(samples, source_rate, rate)
        converted.append(samples)
        offsets.append(round(offset * rate))
        volumes.append(volume)
    arrays, channels = broadcast_channels(converted)
    length = max(offset + len(samples) for offset, samples in zip(offsets, arrays, strict=True))
    if length * channels * 8 > 256 * 1024 * 1024:
        raise ValueError("Mix exceeds the 256 MiB audio budget. Reduce track lengths or offsets.")
    output = np.zeros((length, channels), dtype=np.float64)
    for samples, offset, volume in zip(arrays, offsets, volumes, strict=True):
        output[offset:offset + len(samples)] += samples * volume
    peak = float(np.max(np.abs(output)))
    if peak > 1:
        output /= peak
    return restore_channels(output, channels == 1)
