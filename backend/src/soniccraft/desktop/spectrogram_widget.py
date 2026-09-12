"""Time-frequency heatmap shared by file and live analysis."""
import pyqtgraph as pg
from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from .theme import label, style_plot
from .effects_panel import button


class SpectrogramWidget(QWidget):
    stop_requested = pyqtSignal()
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
        row.addWidget(label("LEVEL  ·  dBFS", "eyebrow"))
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
        self.colormap = pg.ColorMap(
            [0, 0.25, 0.5, 0.75, 1],
            ["#0d1115", "#28344f", "#5966aa", "#70c5b0", "#f4e6a5"],
        )
        self.colorbar = pg.ColorBarItem(values=(-100, 0), colorMap=self.colormap, interactive=False, width=12)
        self.colorbar.setImageItem(self.image, insert_in=self.plot.getPlotItem())
        layout.addWidget(self.plot, 1)

    def set_data(self, data):
        self.current_data = data
        self.image.setImage(data.values, autoLevels=False, levels=(-100, 0))
        # Pixel centers correspond to actual STFT frame centers and FFT bins.
        step = data.hop / data.sample_rate
        bin_width = data.sample_rate / data.n_fft
        self.image.setRect(QRectF(data.offset - step / 2, -bin_width / 2,
                                 max(step, data.values.shape[1] * step), data.values.shape[0] * bin_width))
        self.plot.setXRange(data.offset, data.offset + max(data.duration, 1 / data.sample_rate), padding=0)
        self.plot.setYRange(0, data.sample_rate / 2, padding=0)
        self.info_label.setText(f"{'MICROPHONE' if self.live else 'MONO MIX'}  ·  {data.n_fft} FFT  ·  {step * 1000:.1f} ms time step  ·  {data.duration:.2f} s")

    def clear(self, message=None):
        self.current_data = None
        self.image.clear()
        self.info_label.setText(message or "Selection changed. Generate a new spectrogram from the sidebar.")
