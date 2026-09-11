"""Audio document and bounded snapshot history, independent of Qt."""
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

import numpy as np

from soniccraft.audio_io import inspect_audio, load_audio, save_audio

MAX_AUDIO_BYTES = 64 * 1024 * 1024
HISTORY_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class AudioData:
    samples: np.ndarray
    sample_rate: int
    filename: str = ""

    def __post_init__(self):
        data = np.array(self.samples, dtype=np.float64, copy=True)
        if data.ndim not in (1, 2) or len(data) == 0:
            raise ValueError("Audio must contain at least one sample.")
        if data.ndim == 2 and data.shape[1] not in (1, 2):
            raise ValueError("Only mono and stereo files are supported.")
        if data.nbytes > MAX_AUDIO_BYTES:
            raise ValueError("Decoded audio exceeds the 64 MiB editor limit. Open a shorter clip.")
        if not np.all(np.isfinite(data)):
            raise ValueError("Audio contains non-finite samples.")
        if self.sample_rate <= 0 or int(self.sample_rate) != self.sample_rate:
            raise ValueError("Sample rate must be a positive integer.")
        data.setflags(write=False)
        object.__setattr__(self, "samples", data)

    @property
    def channels(self):
        return 1 if self.samples.ndim == 1 else self.samples.shape[1]

    @property
    def duration(self):
        return len(self.samples) / self.sample_rate

    @property
    def peak(self):
        return float(np.max(np.abs(self.samples)))

    @classmethod
    def open(cls, path):
        info = inspect_audio(path)
        if info.channels not in (1, 2) or info.frames * info.channels * 8 > MAX_AUDIO_BYTES:
            raise ValueError("Open a mono/stereo file smaller than 64 MiB when decoded.")
        samples, rate = load_audio(path)
        return cls(samples, rate, str(path))

    def save(self, path, *, scale_to_fit=False):
        """Atomic PCM export. Never silently clip or overwrite a failed encode."""
        output = Path(path)
        formats = {".wav": ("WAV", "PCM_24"), ".flac": ("FLAC", "PCM_24")}
        if output.suffix.lower() not in formats:
            raise ValueError("Save as .wav or .flac.")
        peak = self.peak
        if peak > 1 and not scale_to_fit:
            raise ValueError("Audio exceeds full scale. Normalize it or approve export scaling.")
        samples = self.samples / peak if peak > 1 else self.samples
        fmt, subtype = formats[output.suffix.lower()]
        fd, temporary = tempfile.mkstemp(prefix=".soniccraft-", suffix=output.suffix, dir=output.parent)
        os.close(fd)
        try:
            save_audio(temporary, samples, self.sample_rate, format=fmt, subtype=subtype)
            os.replace(temporary, output)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class Document:
    def __init__(self):
        self.audio = None
        self.saved_samples = None
        self.undo_stack = []
        self.redo_stack = []

    @property
    def dirty(self):
        return self.audio is not None and self.audio.samples is not self.saved_samples

    def load(self, audio):
        self.audio = audio
        self.saved_samples = audio.samples
        self.undo_stack.clear()
        self.redo_stack.clear()

    def commit(self, samples):
        if self.audio is None:
            raise ValueError("Open audio first.")
        updated = AudioData(samples, self.audio.sample_rate, self.audio.filename)
        self.undo_stack.append(self.audio)
        self.redo_stack.clear()
        while len(self.undo_stack) > 20 or sum(x.samples.nbytes for x in self.undo_stack) > HISTORY_BYTES:
            self.undo_stack.pop(0)
        self.audio = updated

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.audio)
            self.audio = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.audio)
            self.audio = self.redo_stack.pop()
