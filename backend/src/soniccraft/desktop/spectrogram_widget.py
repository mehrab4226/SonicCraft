"""Time-frequency heatmap shared by file and live analysis."""
import pyqtgraph as pg
import numpy as np
from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox
from .theme import label, style_plot
from .effects_panel import button


class SpectrogramWidget(QWidget):
    stop_requested = pyqtSignal()
    mask_requested = pyqtSignal(float, float, float, float)

    def __init__(self, live=False, parent=None):
        super().__init__(parent)
        self.live = live
        self.current_data = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        row = QHBoxLayout()
        self.info_label = label("Start monitoring to see microphone audio." if live else "Select audio, then generate a spectrogram from the sidebar.")
        self.info_label.setWordWrap(True)
        row.addWidget(self.info_label, 1)
        row.addWidget(label("LEVEL", "eyebrow"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Decibels (dBFS)", "Linear normalized"])
        self.scale_combo.currentIndexChanged.connect(self._replot)
        row.addWidget(self.scale_combo)
        self.mask_button = button(row, "Mute Region", self._request_mask)
        if live:
            self.stop_button = button(row, "Stop monitoring", self.stop_requested.emit)
            self.stop_button.setEnabled(False)
        layout.addLayout(row)
        self.plot = pg.PlotWidget()
        style_plot(self.plot)
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "Frequency", units="Hz")
        self.plot.setMenuEnabled(False)
        self.plot.setMinimumHeight(100)
        self.image = pg.ImageItem(axisOrder="row-major")
        self.plot.addItem(self.image)
        self.mask_roi = pg.RectROI([0, 0], [0.5, 1000], pen=pg.mkPen("#ffaca6", width=2))
        self.plot.addItem(self.mask_roi)
        self.colormap = pg.ColorMap(
            [0, 0.25, 0.5, 0.75, 1],
            ["#0d1115", "#28344f", "#5966aa", "#70c5b0", "#f4e6a5"],
        )
        self.colorbar = pg.ColorBarItem(values=(-100, 0), colorMap=self.colormap, interactive=False, width=12)
        self.colorbar.setImageItem(self.image, insert_in=self.plot.getPlotItem())
        layout.addWidget(self.plot, 1)
        self._frequency_min = 0.0
        self._frequency_max = None

    def _request_mask(self):
        position = self.mask_roi.pos()
        size = self.mask_roi.size()
        t_start = float(position.x())
        t_end = t_start + float(size.x())
        f_start = float(position.y())
        f_end = f_start + float(size.y())
        self.mask_requested.emit(t_start, t_end, f_start, f_end)

    def set_data(self, data):
        self.current_data = data
        self._replot()
        # Pixel centers correspond to actual STFT frame centers and FFT bins.
        step = data.hop / data.sample_rate
        bin_width = data.sample_rate / data.n_fft
        self.image.setRect(QRectF(data.offset - step / 2, -bin_width / 2,
                                 max(step, data.values.shape[1] * step), data.values.shape[0] * bin_width))
        self.plot.setXRange(data.offset, data.offset + max(data.duration, 1 / data.sample_rate), padding=0)
        self._apply_frequency_range(data.sample_rate / 2)
        self.info_label.setText(f"{'MICROPHONE' if self.live else 'MONO MIX'}  ·  {data.n_fft} FFT  ·  {step * 1000:.1f} ms time step  ·  {data.duration:.2f} s")

    def set_frequency_range(self, minimum=0.0, maximum=None):
        """Set optional frequency bounds in Hz for the spectrogram view."""
        minimum = float(minimum)
        maximum = None if maximum is None else float(maximum)
        if not np.isfinite(minimum) or minimum < 0:
            raise ValueError("minimum frequency must be finite and non-negative")
        if maximum is not None and (not np.isfinite(maximum) or maximum <= minimum):
            raise ValueError("maximum frequency must be greater than minimum frequency")
        self._frequency_min = minimum
        self._frequency_max = maximum
        if self.current_data is not None:
            self._apply_frequency_range(self.current_data.sample_rate / 2)

    def _apply_frequency_range(self, nyquist):
        minimum = min(self._frequency_min, nyquist)
        maximum = nyquist if self._frequency_max is None else min(self._frequency_max, nyquist)
        if maximum <= minimum:
            minimum, maximum = 0.0, nyquist
        self.plot.setYRange(minimum, maximum, padding=0)

    def _replot(self):
        if self.current_data is None:
            return
        if self.scale_combo.currentIndex() == 0:
            values = self.current_data.values
            levels = (-100, 0)
        else:
            peak = float(np.max(self.current_data.magnitude))
            values = self.current_data.magnitude / peak if peak > 0 else np.zeros_like(self.current_data.magnitude)
            levels = (0, 1)
        self.image.setImage(values, autoLevels=False, levels=levels)
        self.colorbar.setLevels(levels)

    def clear(self, message=None):
        self.current_data = None
        self.image.clear()
        self.info_label.setText(message or "Selection changed. Generate a new spectrogram from the sidebar.")
