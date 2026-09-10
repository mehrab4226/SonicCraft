"""Audio decoding, encoding, metadata, and safe file I/O."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import numpy as np
import soundfile as sf
from numpy.typing import ArrayLike, NDArray

from .dsp._validation import as_audio_array, validate_sample_rate


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    sample_rate: int
    frames: int
    channels: int
    duration_seconds: float
    format: str
    subtype: str


def _metadata(info: sf.SoundFile) -> AudioMetadata:
    return AudioMetadata(
        sample_rate=int(info.samplerate),
        frames=int(info.frames),
        channels=int(info.channels),
        duration_seconds=float(info.frames / info.samplerate),
        format=info.format,
        subtype=info.subtype,
    )


def inspect_audio(source: str | Path | BinaryIO) -> AudioMetadata:
    """Read audio metadata without decoding the sample data."""

    return _metadata(sf.info(source))


def load_audio(
    path: str | Path,
    *,
    dtype: str = "float64",
    always_2d: bool = False,
) -> tuple[NDArray[np.floating], int]:
    """Decode an audio file and return ``(samples, sample_rate)``."""

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"audio file does not exist: {file_path}")
    data, sample_rate = sf.read(file_path, dtype=dtype, always_2d=always_2d)
    return np.asarray(data), int(sample_rate)


def save_audio(
    path: str | Path,
    audio: ArrayLike,
    sample_rate: int,
    *,
    subtype: str | None = None,
    format: str | None = None,
) -> None:
    """Encode audio to disk, creating parent directories when necessary."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    samples = as_audio_array(audio)
    rate = int(validate_sample_rate(sample_rate))
    sf.write(output, samples, rate, subtype=subtype, format=format)


def read_audio_bytes(
    payload: bytes,
    *,
    dtype: str = "float64",
    always_2d: bool = False,
) -> tuple[NDArray[np.floating], int, AudioMetadata]:
    """Decode uploaded audio bytes without writing a temporary file."""

    if not payload:
        raise ValueError("payload must not be empty")
    buffer = BytesIO(payload)
    info = sf.info(buffer)
    buffer.seek(0)
    data, sample_rate = sf.read(buffer, dtype=dtype, always_2d=always_2d)
    return np.asarray(data), int(sample_rate), _metadata(info)


def write_audio_bytes(
    audio: ArrayLike,
    sample_rate: int,
    *,
    format: str = "WAV",
    subtype: str = "PCM_16",
) -> bytes:
    """Encode processed audio for an HTTP response or browser download."""

    samples = as_audio_array(audio)
    rate = int(validate_sample_rate(sample_rate))
    buffer = BytesIO()
    sf.write(buffer, samples, rate, format=format, subtype=subtype)
    return buffer.getvalue()
