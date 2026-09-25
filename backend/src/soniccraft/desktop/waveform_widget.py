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


class WaveformWidget(pg.GraphicsLayoutWidget):
    selection_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("waveform")
        self.setBackground("#0b0f16")
        self.audio = None
        self.region = None
        self.playhead = None
        self.plots = []
        self.region_items = []
        self.playhead_items = []
        self._syncing_region = False
        plot = self.addPlot(row=0, col=0)
        self.plots.append(plot)
        style_plot(plot)
        plot.setLabel("bottom", "Time", units="s")
        plot.setLabel("left", "Amplitude")
        plot.setMouseEnabled(x=True, y=False)
        self.reset_view()

    def set_audio(self, audio):
        self.audio = audio
        self.clear()
        self.plots = []
        self.region_items = []
        self.playhead_items = []
        samples = audio.samples[:, None] if audio.samples.ndim == 1 else audio.samples
        times, values = envelope(samples, audio.sample_rate)
        for channel in range(audio.channels):
            plot = self.addPlot(row=channel, col=0)
            self.plots.append(plot)
            style_plot(plot)
            if audio.channels == 2:
                plot.setLabel("left", "Left" if channel == 0 else "Right")
            else:
                plot.setLabel("left", "Amplitude")
            plot.setLabel("bottom", "Time", units="s")
            plot.setMouseEnabled(x=True, y=False)
            plot.plot(times, values[:, channel], pen=pg.mkPen(("#91efd0", "#b6a4f5")[channel], width=1),
                      fillLevel=0, brush=pg.mkBrush(145, 239, 208, 12) if channel == 0 else None)
        if len(self.plots) == 2:
            self.plots[1].setXLink(self.plots[0])
        for plot in self.plots:
            region = pg.LinearRegionItem(
                (0, audio.duration), bounds=(0, audio.duration), brush=(145, 239, 208, 16),
                pen=pg.mkPen("#77bfa6", width=1), hoverBrush=(145, 239, 208, 30),
                hoverPen=pg.mkPen("#bcffe7", width=2),
            )
            region.setZValue(5)
            plot.addItem(region)
            region.sigRegionChanged.connect(lambda source=region: self._selection(source))
            self.region_items.append(region)
            playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("#ffcf70"))
            playhead.setZValue(10)
            plot.addItem(playhead)
            self.playhead_items.append(playhead)
        self.region = self.region_items[0]
        self.playhead = self.playhead_items[0]
        self.reset_view()
        self._selection()

    def _selection(self, source=None):
        if self._syncing_region or self.region is None:
            return
        self._syncing_region = True
        try:
            region = (source or self.region).getRegion()
            for item in self.region_items:
                if item is not source:
                    item.setRegion(region)
        finally:
            self._syncing_region = False
        self.selection_changed.emit(*self.region.getRegion())

    def set_selection(self, start, end):
        if self.region:
            self.region.setRegion((start, end))

    def reset_view(self):
        duration = self.audio.duration if self.audio else 1
        for plot in self.plots:
            plot.setXRange(0, duration, padding=0)
        if not self.plots:
            return
        peak = max(1, self.audio.peak) if self.audio else 1
        for plot in self.plots:
            plot.setYRange(-peak, peak, padding=0.05)

    def zoom_selection(self):
        if self.region is not None:
            start, end = self.region.getRegion()
            if end > start:
                for plot in self.plots:
                    plot.setXRange(start, end, padding=0.02)

    def getPlotItem(self):
        return self.plots[0] if self.plots else None

    def getAxis(self, edge):
        return self.getPlotItem().getAxis(edge)

    def setXRange(self, start, end, padding=0):
        for plot in self.plots:
            plot.setXRange(start, end, padding=padding)

    def viewRange(self):
        return self.getPlotItem().viewRange()
