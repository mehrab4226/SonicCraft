"""PNG graph previews carrying explicitly embedded, lossless source samples."""
import os
from pathlib import Path
import struct
import tempfile
import zlib

import numpy as np
from PIL.PngImagePlugin import PngInfo

CHUNK = b"scAu"
HEADER = struct.Struct(">4sIBBQ")
LIMIT = 256 * 1024 * 1024


def save_audio_png(image, path, samples, sample_rate):
    """Atomically save a viewable PNG plus its source audio, not pixel inversion."""
    samples = np.asarray(samples)
    channels = 1 if samples.ndim == 1 else samples.shape[1]
    if (samples.ndim not in (1, 2) or channels not in (1, 2) or not len(samples)
            or samples.size * 8 > LIMIT or not np.all(np.isfinite(samples))
            or not 0 < sample_rate <= 768000 or int(sample_rate) != sample_rate):
        raise ValueError("Source audio is invalid or exceeds the 256 MiB image export limit.")
    header = HEADER.pack(b"SCA1", int(sample_rate), samples.ndim, channels, len(samples))
    payload = header + zlib.compress(samples.astype("<f8", copy=False).tobytes(), level=1)
    metadata = PngInfo()
    metadata.add_text("Description", "SonicCraft spectrogram with embedded lossless source audio. Import in SonicCraft to restore audio.")
    metadata.add(CHUNK, payload)
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".soniccraft-", suffix=".png", dir=path.parent)
    os.close(fd)
    try:
        image.save(temporary, format="PNG", pnginfo=metadata)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_audio_png(path):
    """Return embedded samples and rate, or None for ordinary image files."""
    with open(path, "rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        while True:
            prefix = stream.read(8)
            if len(prefix) != 8:
                raise ValueError("Incomplete PNG file.")
            length, kind = struct.unpack(">I4s", prefix)
            if kind == CHUNK:
                if not HEADER.size < length <= LIMIT + LIMIT // 100 + HEADER.size:
                    raise ValueError("Invalid embedded audio size.")
                payload = stream.read(length)
                crc = stream.read(4)
                if len(payload) != length or len(crc) != 4 or zlib.crc32(kind + payload) != struct.unpack(">I", crc)[0]:
                    raise ValueError("Embedded audio is damaged.")
                magic, rate, ndim, channels, frames = HEADER.unpack(payload[:HEADER.size])
                count = frames * channels * 8
                if (magic != b"SCA1" or ndim not in (1, 2) or channels not in (1, 2)
                        or (ndim == 1 and channels != 1) or not 0 < rate <= 768000
                        or not 0 < count <= LIMIT):
                    raise ValueError("Unsupported embedded audio format.")
                decoder = zlib.decompressobj()
                try:
                    raw = decoder.decompress(payload[HEADER.size:], count + 1)
                except zlib.error as error:
                    raise ValueError("Embedded audio is damaged.") from error
                if len(raw) != count or not decoder.eof or decoder.unused_data:
                    raise ValueError("Embedded audio length is invalid.")
                samples = np.frombuffer(raw, dtype="<f8")
                if not np.all(np.isfinite(samples)):
                    raise ValueError("Embedded audio contains invalid samples.")
                if ndim == 2:
                    samples = samples.reshape(frames, channels)
                return samples, rate
            if kind == b"IEND":
                return None
            stream.seek(length + 4, 1)
