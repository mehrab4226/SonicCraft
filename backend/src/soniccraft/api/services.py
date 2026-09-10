"""Bounded decoding and serialization at the browser/DSP boundary."""

from dataclasses import asdict
from io import BytesIO

import numpy as np
import soundfile as sf
from fastapi import HTTPException, UploadFile

from soniccraft.audio_io import inspect_audio, read_audio_bytes, write_audio_bytes
from soniccraft.dsp.analysis import clipping_fraction, dbfs, peak_amplitude, waveform_envelope

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_DURATION_SECONDS = 300
MAX_DECODED_SAMPLES = 16_000_000


def decode_upload(file: UploadFile):
    # Read at most the file limit even if Content-Length was absent or incorrect.
    payload = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Audio file exceeds the 32 MiB limit.")
    if not payload:
        raise HTTPException(422, "Choose a non-empty audio file.")
    try:
        metadata = inspect_audio(BytesIO(payload))
        if metadata.channels not in (1, 2):
            raise HTTPException(422, "Only mono and stereo audio are supported in this milestone.")
        if not 8_000 <= metadata.sample_rate <= 192_000:
            raise HTTPException(422, "Sample rate must be between 8 and 192 kHz.")
        if metadata.frames == 0:
            raise HTTPException(422, "Audio contains no samples.")
        if (metadata.duration_seconds > MAX_DURATION_SECONDS
                or metadata.frames * metadata.channels > MAX_DECODED_SAMPLES):
            raise HTTPException(413, "Audio exceeds the 5-minute or 16-million-sample limit.")
        samples, rate, metadata = read_audio_bytes(payload)
    except (sf.LibsndfileError, RuntimeError) as error:
        raise HTTPException(422, "Cannot decode this file. Try a WAV, FLAC, or OGG audio file.") from error
    if not np.all(np.isfinite(samples)):
        raise HTTPException(422, "Audio contains non-finite samples.")
    return samples, rate, metadata


def inspect_upload(file: UploadFile, bins: int):
    samples, rate, metadata = decode_upload(file)
    envelope = waveform_envelope(samples, rate, bins=bins)

    def channels_first(values):
        array = np.asarray(values)
        return array[None, :].tolist() if array.ndim == 1 else array.T.tolist()

    return {
        "metadata": asdict(metadata),
        "levels": {
            "peak": np.atleast_1d(peak_amplitude(samples)).tolist(),
            "rms_dbfs": np.atleast_1d(dbfs(samples)).tolist(),
            "clipping_fraction": np.atleast_1d(clipping_fraction(samples)).tolist(),
        },
        "waveform": {
            "times": envelope.times.tolist(),
            "minimum": channels_first(envelope.minimum),
            "maximum": channels_first(envelope.maximum),
        },
    }


def encode_wav(samples, rate: int, *, floating: bool = False):
    # Floating point revisions preserve headroom; integer export is explicit.
    return write_audio_bytes(samples, rate, subtype="FLOAT" if floating else "PCM_16")
