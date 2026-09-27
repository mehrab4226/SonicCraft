"""Sample-rate conversion used by multitrack mixing."""

from __future__ import annotations

from fractions import Fraction

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import signal

from ._validation import as_audio_array, validate_positive_int


def resample_audio(audio: ArrayLike, source_rate: int, target_rate: int) -> NDArray[np.float64]:
    """Band-limited polyphase resampling along the sample axis."""

    samples = as_audio_array(audio)
    source = validate_positive_int(source_rate, name="source_rate")
    target = validate_positive_int(target_rate, name="target_rate")
    if source == target:
        return samples.copy()
    ratio = Fraction(target, source)
    return signal.resample_poly(samples, ratio.numerator, ratio.denominator, axis=0)
