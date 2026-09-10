"""Shared validation and audio-array normalization helpers."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def as_audio_array(audio: ArrayLike, *, name: str = "audio", copy: bool = False) -> FloatArray:
    """Return finite float64 audio with shape ``(samples,)`` or ``(samples, channels)``.

    Integer PCM arrays are normalized using their dtype range. Floating-point
    values are preserved rather than clipped so callers can detect overloads.
    """

    raw = np.asarray(audio)
    if raw.ndim not in (1, 2):
        raise ValueError(f"{name} must be one- or two-dimensional; got shape {raw.shape}")
    if raw.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one sample")
    if raw.ndim == 2 and raw.shape[1] == 0:
        raise ValueError(f"{name} must contain at least one channel")

    if np.issubdtype(raw.dtype, np.integer):
        info = np.iinfo(raw.dtype)
        scale = float(max(abs(info.min), info.max))
        result = raw.astype(np.float64) / scale
    else:
        result = raw.astype(np.float64, copy=copy)

    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} contains NaN or infinite samples")
    return result


def validate_sample_rate(sample_rate: float) -> float:
    value = float(sample_rate)
    if not np.isfinite(value) or value <= 0:
        raise ValueError("sample_rate must be a finite positive number")
    return value


def validate_positive_int(value: int, *, name: str) -> int:
    if isinstance(value, bool) or int(value) != value or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def validate_probability(value: float, *, name: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return number


def to_2d(audio: FloatArray) -> tuple[FloatArray, bool]:
    """Return ``(samples, channels)`` audio and whether the input was mono."""

    if audio.ndim == 1:
        return audio[:, None], True
    return audio, False


def restore_channels(audio: FloatArray, was_mono: bool) -> FloatArray:
    return audio[:, 0] if was_mono else audio


def broadcast_channels(arrays: Sequence[FloatArray]) -> tuple[list[FloatArray], int]:
    """Convert audio arrays to 2-D and broadcast mono inputs to channel count."""

    two_dimensional = [to_2d(item)[0] for item in arrays]
    channels = max(item.shape[1] for item in two_dimensional)
    if any(item.shape[1] not in (1, channels) for item in two_dimensional):
        raise ValueError("channel counts must match, except mono may be broadcast")
    result = [
        np.repeat(item, channels, axis=1)
        if item.shape[1] == 1 and channels > 1
        else item
        for item in two_dimensional
    ]
    return result, channels
