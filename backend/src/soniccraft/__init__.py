"""SonicCraft's reusable audio and digital signal processing package."""

from .audio_io import AudioMetadata, load_audio, save_audio

__all__ = [
    "AudioMetadata",
    "load_audio",
    "save_audio",
]

__version__ = "0.1.0"
