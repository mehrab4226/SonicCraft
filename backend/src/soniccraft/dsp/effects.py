"""Non-destructive-style editing primitives, gain, fades, and mixing."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._validation import as_audio_array, broadcast_channels, restore_channels, to_2d, validate_probability, validate_sample_rate

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


def normalize_rms(audio: ArrayLike, target_dbfs: float = -18.0, *, prevent_clipping: bool = True) -> NDArray[np.float64]:
    """Normalize overall RMS level, optionally limiting the result to 0 dBFS."""

    if target_dbfs > 0 or not np.isfinite(target_dbfs):
        raise ValueError("target_dbfs must be finite and no greater than 0")
    samples = as_audio_array(audio)
    current = float(np.sqrt(np.mean(np.square(samples))))
    if current == 0:
        return samples.copy()
    output = samples * ((10.0 ** (target_dbfs / 20.0)) / current)
    peak = float(np.max(np.abs(output)))
    if prevent_clipping and peak > 1.0:
        output /= peak
    return output


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


def split_audio(audio: ArrayLike, sample_index: int) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    samples = as_audio_array(audio)
    if not 0 < sample_index < samples.shape[0]:
        raise ValueError("sample_index must be inside the signal")
    return samples[:sample_index].copy(), samples[sample_index:].copy()


def concatenate_audio(clips: Sequence[ArrayLike]) -> NDArray[np.float64]:
    if not clips:
        raise ValueError("clips must contain at least one audio array")
    converted = [as_audio_array(clip, name=f"clips[{index}]") for index, clip in enumerate(clips)]
    arrays, channels = broadcast_channels(converted)
    output = np.concatenate(arrays, axis=0)
    return restore_channels(output, channels == 1 and all(item.ndim == 1 for item in converted))


def mix_audio(
    tracks: Sequence[ArrayLike],
    *,
    offsets: Sequence[int] | None = None,
    gains_db: Sequence[float] | None = None,
    normalize: bool = False,
) -> NDArray[np.float64]:
    """Mix tracks at sample offsets, with mono-to-multichannel broadcasting."""

    if not tracks:
        raise ValueError("tracks must contain at least one audio array")
    converted = [as_audio_array(track, name=f"tracks[{index}]") for index, track in enumerate(tracks)]
    arrays, channels = broadcast_channels(converted)
    track_offsets = list(offsets) if offsets is not None else [0] * len(arrays)
    gains = list(gains_db) if gains_db is not None else [0.0] * len(arrays)
    if len(track_offsets) != len(arrays) or len(gains) != len(arrays):
        raise ValueError("offsets and gains_db must match the number of tracks")
    if any(isinstance(value, bool) or int(value) != value or value < 0 for value in track_offsets):
        raise ValueError("offsets must be non-negative integers")
    if not np.all(np.isfinite(gains)):
        raise ValueError("gains_db must contain only finite values")

    output_length = max(int(offset) + track.shape[0] for offset, track in zip(track_offsets, arrays, strict=True))
    output = np.zeros((output_length, channels), dtype=np.float64)
    for track, offset, gain in zip(arrays, track_offsets, gains, strict=True):
        start = int(offset)
        output[start : start + track.shape[0]] += track * (10.0 ** (float(gain) / 20.0))

    if normalize:
        peak = float(np.max(np.abs(output)))
        if peak > 1.0:
            output /= peak
    return restore_channels(output, channels == 1 and all(item.ndim == 1 for item in converted))


def hard_clip(audio: ArrayLike, threshold: float = 1.0) -> NDArray[np.float64]:
    if not 0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")
    return np.clip(as_audio_array(audio), -threshold, threshold)


def soft_clip(audio: ArrayLike, drive: float = 1.0) -> NDArray[np.float64]:
    """Apply normalized tanh saturation without exceeding full scale."""

    if drive <= 0 or not np.isfinite(drive):
        raise ValueError("drive must be finite and positive")
    samples = as_audio_array(audio)
    return np.tanh(samples * drive) / np.tanh(drive)
