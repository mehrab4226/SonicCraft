"""Bounded display transforms, independent of the Qt interface."""
from dataclasses import dataclass
import numpy as np
from soniccraft.dsp.transforms import fft_spectrum


@dataclass(frozen=True)
class SpectrogramData:
    values: np.ndarray
    duration: float
    sample_rate: int
    n_fft: int
    hop: int
    offset: float


def make_spectrogram(samples, sample_rate, n_fft=2048, window="hann", *, offset=0, max_frames=1200):
    """Calibrated one-sided STFT amplitudes, at most max_frames time columns.

    Long selections increase the hop (possibly leaving gaps between windows).
    Batches keep transform working memory bounded without truncating the time span.
    """
    if n_fft not in (512, 1024, 2048, 4096) or max_frames < 2:
        raise ValueError("Choose a supported FFT size and at least two display frames.")
    audio = np.asarray(samples, dtype=float)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if audio.ndim != 1 or not len(audio) or sample_rate <= 0 or not np.all(np.isfinite(audio)):
        raise ValueError("Spectrogram requires finite, non-empty audio and a positive sample rate.")
    duration = len(audio) / sample_rate
    # Centers include the beginning and end; zero padding supports short clips.
    hop = max(n_fft // 4, int(np.ceil(len(audio) / (max_frames - 1))))
    centers = np.arange(0, len(audio) + 1, hop)
    padded = np.pad(audio, (n_fft // 2, n_fft))
    values = np.empty((n_fft // 2 + 1, len(centers)), dtype=np.float32)
    for first in range(0, len(centers), 32):
        starts = centers[first:first + 32]
        frames = np.stack([padded[start:start + n_fft] for start in starts], axis=1)
        result = fft_spectrum(frames, sample_rate, n_fft=n_fft, window=window, remove_dc=False)
        values[:, first:first + len(starts)] = result.magnitude_db
    return SpectrogramData(values, duration, sample_rate, n_fft, hop, offset)
