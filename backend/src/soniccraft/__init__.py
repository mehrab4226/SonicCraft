"""SonicCraft's reusable audio and digital signal processing package."""

from .audio_io import AudioMetadata, load_audio, read_audio_bytes, save_audio, write_audio_bytes

__all__ = [
    "AudioMetadata",
    "load_audio",
    "read_audio_bytes",
    "save_audio",
    "write_audio_bytes",
]

__version__ = "0.1.0"
