"""Local audio streams. Callbacks never access Qt widgets."""
from queue import Queue, Empty, Full
import numpy as np
import sounddevice as sd


class Player:
    def __init__(self, driver=sd):
        self.driver = driver
        self.stream = None
        self.position = 0
        self.end = 0
        self.samples = None
        self.warning = ""
        self._rendered_samples = None
        self._fade_from = None
        self._fade_position = 0
        self._fade_frames = 1
        self.protect_output = False

    @property
    def active(self):
        return self.stream is not None and self.stream.active

    def play(self, audio, start=0, end=None, device=None, *, preview=False):
        self.stop()
        self.samples = audio.samples
        self._rendered_samples = self.samples
        self._fade_from = None
        self._fade_frames = max(1, round(audio.sample_rate * 0.01))
        self.protect_output = preview
        self.position = int(start)
        self.end = len(audio.samples) if end is None else int(end)
        if not 0 <= self.position < self.end <= len(audio.samples):
            raise ValueError("Playback range is empty or invalid.")
        if audio.peak > 1 and not preview:
            raise ValueError("Audio exceeds full scale. Normalize before playback to prevent clipping.")
        self.warning = ""
        try:
            self.stream = self.driver.OutputStream(
                samplerate=audio.sample_rate, channels=audio.channels, dtype="float32",
                device=device, callback=self._callback,
            )
            self.stream.start()
        except Exception:
            self.stop()
            raise

    def replace_audio(self, audio):
        """Publish an immutable buffer; the callback owns the crossfade state."""
        if self.samples is not None and audio.samples.shape != self.samples.shape:
            raise ValueError("Live preview must keep the playback buffer shape.")
        self.protect_output = True
        self.samples = audio.samples

    def _callback(self, output, frames, time, status):
        output.fill(0)
        if status:
            self.warning = str(status)
        count = min(frames, self.end - self.position)
        samples = self.samples
        if samples is not self._rendered_samples:
            self._fade_from = self._rendered_samples
            self._rendered_samples = samples
            self._fade_position = 0
        block = samples[self.position:self.position + count]
        output[:count] = block[:, None] if block.ndim == 1 else block
        if self._fade_from is not None:
            fading = min(count, self._fade_frames - self._fade_position)
            old = self._fade_from[self.position:self.position + fading]
            weight = np.minimum(1, (np.arange(fading) + self._fade_position + 1) / self._fade_frames)[:, None]
            output[:fading] = output[:fading] * weight + (old[:, None] if old.ndim == 1 else old) * (1 - weight)
            self._fade_position += fading
            if self._fade_position >= self._fade_frames:
                self._fade_from = None
        if self.protect_output:
            np.clip(output, -1, 1, out=output)
        self.position += count
        if self.position >= self.end:
            raise self.driver.CallbackStop

    def pause(self):
        position, end = self.position, self.end
        self.stop()
        self.position, self.end = position, end

    def stop(self):
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.abort()
            finally:
                stream.close()
        self.position = 0


class Microphone:
    def __init__(self, driver=sd):
        self.driver = driver
        self.stream = None
        self.blocks = Queue(maxsize=32)
        self.sample_rate = 0
        self.dropped = 0
        self.warning = ""

    def start(self, device=None):
        self.stop()
        info = self.driver.query_devices(device, "input")
        self.sample_rate = int(info["default_samplerate"])
        self.dropped = 0
        self.warning = ""
        try:
            self.stream = self.driver.InputStream(
                device=device, samplerate=self.sample_rate, channels=1,
                blocksize=1024, dtype="float32", callback=self._callback,
            )
            self.stream.start()
        except Exception:
            self.stop()
            raise

    def _callback(self, data, frames, time, status):
        if status:
            self.warning = str(status)
        try:
            self.blocks.put_nowait(data[:, 0].copy())
        except Full:
            self.dropped += 1

    def drain(self):
        blocks = []
        while True:
            try:
                blocks.append(self.blocks.get_nowait())
            except Empty:
                return blocks

    def stop(self):
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.abort()
            finally:
                stream.close()
        return self.drain()
