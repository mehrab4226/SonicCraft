"""Level, quality, and visualization summaries for audio signals."""

from __future__ import annotations


import numpy as np


from .transforms import Spectrum


def get_dominant_frequency(spectrum: Spectrum) -> float:
    """Finds the frequency bin with the highest magnitude."""
    if len(spectrum.magnitude) == 0:
        return 0.0
        
    mag = spectrum.magnitude
    # If stereo, average to mono first to find the true peak
    if mag.ndim > 1:
        mag = np.mean(mag, axis=1)
        
    peak_index = np.argmax(mag)
    return float(spectrum.frequencies[peak_index])
