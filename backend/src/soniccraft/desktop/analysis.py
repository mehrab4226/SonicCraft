"""Bounded display transforms, independent of the Qt interface."""
from dataclasses import dataclass
import numpy as np
from soniccraft.dsp.transforms import Spectrum, fft_spectrum, magnitude_to_db

MAX_SPECTRUM_SIZE = 131072


def make_spectrum(samples, sample_rate):
    """Keep the original frequency axis; average overlapping windows for long audio."""
    audio = np.asarray(samples)
    if len(audio) <= MAX_SPECTRUM_SIZE:
        return fft_spectrum(audio, sample_rate)
    size = MAX_SPECTRUM_SIZE
    starts = list(range(0, len(audio) - size + 1, size // 2))
    if starts[-1] != len(audio) - size:
        starts.append(len(audio) - size)
    power = None
    for start in starts:
        result = fft_spectrum(audio[start:start + size], sample_rate)
        if power is None:
            power = np.square(result.magnitude)
        else:
            power += np.square(result.magnitude)
    magnitude = np.sqrt(power / len(starts))
    return Spectrum(result.frequencies, magnitude, magnitude_to_db(magnitude))


@dataclass(frozen=True)
class SpectrogramData:
    magnitude: np.ndarray
    values: np.ndarray
    duration: float
    sample_rate: int
    n_fft: int
    hop: float
    offset: float


def make_spectrogram(samples, sample_rate, n_fft=2048, window="hann", *, offset=0, max_frames=1200):
    """Calibrated one-sided STFT amplitudes, at most max_frames time columns.

    Every overlapping window is analyzed. Long selections merge adjacent frames
    by peak magnitude so brief events remain visible without gaps or huge images.
    """
    if n_fft not in (512, 1024, 2048, 4096) or max_frames < 2:
        raise ValueError("Choose a supported FFT size and at least two display frames.")
    audio = np.asarray(samples, dtype=float)
    if audio.ndim not in (1, 2) or not len(audio) or sample_rate <= 0 or not np.all(np.isfinite(audio)):
        raise ValueError("Spectrogram requires finite, non-empty audio and a positive sample rate.")
    if audio.ndim == 2 and audio.shape[1] not in (1, 2):
        raise ValueError("Spectrogram supports mono or stereo audio.")
    duration = len(audio) / sample_rate
    # Centers include the beginning and end; zero padding supports short clips.
    analysis_hop = n_fft // 4
    centers = np.arange(0, len(audio) + 1, analysis_hop)
    columns = min(len(centers), max_frames)
    hop = analysis_hop if len(centers) <= max_frames else len(audio) / (columns - 1)
    padding = [(n_fft // 2, n_fft)] + ([(0, 0)] if audio.ndim == 2 else [])
    padded = np.pad(audio, padding)
    magnitude = np.zeros((n_fft // 2 + 1, columns), dtype=np.float32)
    for first in range(0, len(centers), 32):
        starts = centers[first:first + 32]
        frames = np.stack([padded[start:start + n_fft] for start in starts], axis=1)
        if frames.ndim == 3:
            # Average magnitudes, not waveforms: opposite-phase stereo must remain visible.
            frame_magnitude = np.mean([
                fft_spectrum(frames[:, :, ch], sample_rate, n_fft=n_fft, window=window, remove_dc=False).magnitude
                for ch in range(frames.shape[2])
            ], axis=0)
        else:
            frame_magnitude = fft_spectrum(frames, sample_rate, n_fft=n_fft, window=window, remove_dc=False).magnitude
        indices = np.minimum(np.rint(starts / hop).astype(int), columns - 1)
        np.maximum.at(magnitude.T, indices, frame_magnitude.T)
    values = magnitude_to_db(magnitude).astype(np.float32)
    return SpectrogramData(magnitude, values, duration, sample_rate, n_fft, hop, offset)
