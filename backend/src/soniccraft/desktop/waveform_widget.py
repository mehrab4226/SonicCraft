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
        self.setBackground("#141416")
        self.audio = None
        self.region = None
        self.playhead = None
        self.plots = []
        self.region_items = []
        self.playhead_items = []
        self.wave_items = []
        self.played_items = []
        self._bar_times = np.empty(0)
        self._bar_values = None
        self._position = 0
        self._syncing_region = False
        plot = self.addPlot(row=0, col=0)
        self.plots.append(plot)
        style_plot(plot)
        plot.setLabel("bottom", "Time", units="s")
        plot.setLabel("left", "Amplitude")
        self.reset_view()

    def set_audio(self, audio):
        self.audio = audio
        self.clear()
        self.plots = []
        self.region_items = []
        self.playhead_items = []
        self.wave_items = []
        self.played_items = []
        for channel in range(audio.channels):
            plot = self.addPlot(row=channel, col=0)
            self.plots.append(plot)
            style_plot(plot)
            if audio.channels == 2:
                plot.setLabel("left", "Left" if channel == 0 else "Right")
            else:
                plot.setLabel("left", "Amplitude")
            plot.setLabel("bottom", "Time", units="s")
            plot.showGrid(x=False, y=False)
            self.wave_items.append(plot.plot(pen=pg.mkPen(("#e5a093", "#e6bd78")[channel], width=2), connect="pairs"))
            self.played_items.append(plot.plot(pen=pg.mkPen(("#604640", "#60523d")[channel], width=2), connect="pairs"))
        if len(self.plots) == 2:
            self.plots[1].setXLink(self.plots[0])
        for plot in self.plots:
            region = pg.LinearRegionItem(
                (0, audio.duration), bounds=(0, audio.duration), brush=(230, 189, 120, 6),
                pen=pg.mkPen("#796347", width=1), hoverBrush=(230, 189, 120, 18),
                hoverPen=pg.mkPen("#f4d7a4", width=2),
            )
            region.setZValue(5)
            plot.addItem(region)
            region.sigRegionChanged.connect(lambda source=region: self._selection(source))
            self.region_items.append(region)
            playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("#f3ddd2", width=1.5))
            playhead.setZValue(10)
            plot.addItem(playhead)
            self.playhead_items.append(playhead)
        self.region = self.region_items[0]
        self.playhead = self.playhead_items[0]
        self._position = 0
        self._build_bars()
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
        peak = max(0.001, self.audio.peak) if self.audio else 1
        for plot in self.plots:
            plot.setYRange(-peak, peak, padding=0.05)

    def zoom_selection(self):
        # Kept for callers of the old shortcut; graphs always show all audio.
        self.reset_view()

    def _build_bars(self):
        if self.audio is None:
            return
        samples = self.audio.samples
        samples = samples[:, None] if samples.ndim == 1 else samples
        buckets = max(32, int(max(100, self.width() - 80) / 4))
        step = max(1, int(np.ceil(len(samples) / buckets)))
        starts = np.arange(0, len(samples), step)
        low = np.minimum(0, np.minimum.reduceat(samples, starts, axis=0))
        high = np.maximum(0, np.maximum.reduceat(samples, starts, axis=0))
        self._bar_times = np.repeat((starts + np.minimum(step, len(samples) - starts) / 2) / self.audio.sample_rate, 2)
        self._bar_values = np.stack([low, high], axis=1).reshape(-1, self.audio.channels)
        self.set_position(self._position)

    def update_audio(self, audio):
        """Refresh a same-length preview without disturbing selection or axes."""
        self.audio = audio
        self._build_bars()

    def set_position(self, seconds):
        self._position = seconds
        split = int(np.searchsorted(self._bar_times, seconds, side="right"))
        split -= split % 2
        for channel, (upcoming, played) in enumerate(zip(self.wave_items, self.played_items)):
            upcoming.setData(self._bar_times[split:], self._bar_values[split:, channel], connect="pairs")
            played.setData(self._bar_times[:split], self._bar_values[:split, channel], connect="pairs")
        for playhead in self.playhead_items:
            playhead.setValue(seconds)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "audio", None) is not None:
            self._build_bars()
            self.reset_view()

    def getPlotItem(self):
        return self.plots[0] if self.plots else None

    def getAxis(self, edge):
        return self.getPlotItem().getAxis(edge)

    def setXRange(self, start, end, padding=0):
        for plot in self.plots:
            plot.setXRange(start, end, padding=padding)

    def viewRange(self):
        return self.getPlotItem().viewRange()
