"""Digital signal processing building blocks used throughout SonicCraft."""

from .analysis import dbfs, peak_amplitude, rms
from .convolution import circular_convolution, linear_convolution
from .effects import apply_fade, apply_gain, mix_audio, normalize_peak
from .transforms import fft_spectrum, inverse_stft, stft

__all__ = [
    "apply_fade",
    "apply_gain",
    "circular_convolution",
    "dbfs",
    "fft_spectrum",
    "inverse_stft",
    "linear_convolution",
    "mix_audio",
    "normalize_peak",
    "peak_amplitude",
    "rms",
    "stft",
]
