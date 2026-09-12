"""Bounded min/max envelope plotting with sample-accurate region selection."""
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal
from .theme import style_plot


def envelope(samples, sample_rate, max_buckets=5000):
    """Retain extrema, including isolated transients; never modify source data."""
    step = max(1, int(np.ceil(len(samples) / max_buckets)))
    starts = np.arange(0, len(samples), step)
    if step == 1:
        return starts / sample_rate, samples
    low = np.minimum.reduceat(samples, starts, axis=0)
    high = np.maximum.reduceat(samples, starts, axis=0)
    values = np.stack([low, high], axis=1).reshape((-1,) + samples.shape[1:])
    # Each vertical pair covers one bucket, keeping the plot bounded.
    return np.repeat(starts / sample_rate, 2), values


class WaveformWidget(pg.PlotWidget):
    selection_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent=parent, background="#0b0f16")
        self.setObjectName("waveform")
        style_plot(self)
        self.setLabel("bottom", "Time", units="s")
        self.setLabel("left", "Amplitude")
        self.setMenuEnabled(False)
        self.setMouseEnabled(x=True, y=False)
        self.audio = None
        self.region = None
        self.playhead = None
        self.reset_view()

    def set_audio(self, audio):
        self.audio = audio
        self.clear()
        samples = audio.samples[:, None] if audio.samples.ndim == 1 else audio.samples
        times, values = envelope(samples, audio.sample_rate)
        for channel in range(audio.channels):
            self.plot(times, values[:, channel], pen=pg.mkPen(("#91efd0", "#b6a4f5")[channel], width=1),
                      fillLevel=0, brush=pg.mkBrush(145, 239, 208, 12) if channel == 0 else None)
        self.region = pg.LinearRegionItem(
            (0, audio.duration), bounds=(0, audio.duration), brush=(145, 239, 208, 16),
            pen=pg.mkPen("#77bfa6", width=1), hoverBrush=(145, 239, 208, 30),
            hoverPen=pg.mkPen("#bcffe7", width=2),
        )
        self.region.setZValue(5)
        self.addItem(self.region)
        self.region.sigRegionChanged.connect(self._selection)
        self.playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("#ffcf70"))
        self.playhead.setZValue(10)
        self.addItem(self.playhead)
        self.reset_view()
        self._selection()

    def _selection(self):
        self.selection_changed.emit(*self.region.getRegion())

    def set_selection(self, start, end):
        if self.region:
            self.region.setRegion((start, end))

    def reset_view(self):
        self.setXRange(0, self.audio.duration if self.audio else 1, padding=0)
        peak = max(1, self.audio.peak) if self.audio else 1
        self.setYRange(-peak, peak, padding=0.05)

    def zoom_selection(self):
        if self.region is not None:
            start, end = self.region.getRegion()
            if end > start:
                self.setXRange(start, end, padding=0.02)
