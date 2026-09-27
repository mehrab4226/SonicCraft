"""Time-frequency heatmap shared by file and live analysis."""
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import numpy as np
from io import BytesIO
from PIL import Image
from soniccraft.dsp.spectrogram_archive import save_audio_png
from PyQt6.QtCore import QRectF, pyqtSignal, QBuffer, QIODevice
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QFileDialog, QMessageBox
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
        self.info_label = label("Start playback analysis to see the live spectrogram." if live else "Select audio, then generate a spectrogram from the sidebar.")
        self.info_label.setWordWrap(True)
        row.addWidget(self.info_label, 1)
        row.addWidget(label("LEVEL", "eyebrow"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Decibels (dBFS)", "Linear normalized"])
        self.scale_combo.currentIndexChanged.connect(self._replot)
        row.addWidget(self.scale_combo)
        self.save_button = button(row, "Save image", self._save_image_dialog)
        self.save_button.setToolTip("Save a PNG graph with source audio included for exact restoration in SonicCraft.")
        self.save_button.setEnabled(False)
        self.mask_button = button(row, "Mute Region", self._request_mask)
        self.mask_button.setVisible(not live)
        self.mask_button.setEnabled(False)
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
        self.live_playhead = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("#f3ddd2", width=1.5))
        self.live_playhead.setZValue(10)
        self.live_playhead.setVisible(False)
        self.plot.addItem(self.live_playhead)
        self.mask_roi = pg.RectROI([0, 0], [0.5, 1000], pen=pg.mkPen("#ffaca6", width=2))
        self.plot.addItem(self.mask_roi)
        self.mask_roi.setVisible(False)
        self.colormap = pg.ColorMap(
            [0, 0.25, 0.5, 0.75, 1],
            ["#101713", "#163e29", "#237a45", "#53b96d", "#c5f5bc"],
        )
        self.colorbar = pg.ColorBarItem(values=(-100, 0), colorMap=self.colormap, interactive=False, width=12)
        self.colorbar.setImageItem(self.image, insert_in=self.plot.getPlotItem())
        layout.addWidget(self.plot, 1)
        self._frequency_min = 0.0
        self._frequency_max = None
        self._live_duration = None

    @property
    def has_parameter_changes(self):
        return (self.scale_combo.currentIndex() != 0 or self._frequency_min != 0
                or self._frequency_max is not None
                or tuple(self.mask_roi.pos()) != (0, 0)
                or tuple(self.mask_roi.size()) != (.5, 1000))

    def reset_parameters(self):
        self.scale_combo.setCurrentIndex(0)
        self.set_frequency_range()
        self.mask_roi.setPos((0, 0))
        self.mask_roi.setSize((.5, 1000))

    def _request_mask(self):
        position = self.mask_roi.pos()
        size = self.mask_roi.size()
        t_start = float(position.x())
        t_end = t_start + float(size.x())
        f_start = float(position.y())
        f_end = f_start + float(size.y())
        self.mask_requested.emit(t_start, t_end, f_start, f_end)

    def set_live_duration(self, duration):
        self._live_duration = max(0.0, float(duration))
        if self.live and self.current_data is not None:
            self.plot.setXRange(0, max(self._live_duration, self.current_data.duration), padding=0)

    def set_data(self, data):
        self.current_data = data
        self.save_button.setEnabled(True)
        self.mask_button.setEnabled(not self.live)
        self.mask_roi.setVisible(not self.live)
        position, size = self.mask_roi.pos(), self.mask_roi.size()
        if (position.x() < data.offset or position.x() + size.x() > data.offset + data.duration
                or position.y() < 0 or position.y() + size.y() > data.sample_rate / 2):
            self.mask_roi.setPos((data.offset, 0))
            self.mask_roi.setSize((min(.5, data.duration), min(1000, data.sample_rate / 2)))
        self._replot()
        # Pixel centers correspond to actual STFT frame centers and FFT bins.
        step = data.hop / data.sample_rate
        bin_width = data.sample_rate / data.n_fft
        self.image.setRect(QRectF(data.offset - step / 2, -bin_width / 2,
                                 max(step, data.values.shape[1] * step), data.values.shape[0] * bin_width))
        if self.live:
            x_end = max(self._live_duration or 0, data.duration, 1 / data.sample_rate)
            self.plot.setXRange(0, x_end, padding=0)
        else:
            self.plot.setXRange(data.offset, data.offset + max(data.duration, 1 / data.sample_rate), padding=0)
        self._apply_frequency_range(data.sample_rate / 2)
        self.live_playhead.setVisible(self.live)
        self.live_playhead.setValue(data.offset + data.duration)
        self.info_label.setText(f"{'PLAYBACK' if self.live else 'SELECTION'}  ·  {data.n_fft} FFT  ·  {step * 1000:.1f} ms time step  ·  {data.duration:.2f} s")

    def _save_image_dialog(self):
        if self.current_data is None:
            return
        dialog = QFileDialog(self, "Save spectrogram image")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("PNG image with source audio (*.png)")
        dialog.setDefaultSuffix("png")
        dialog.selectFile("spectrogram.png")
        if dialog.exec():
            try:
                self.save_image(dialog.selectedFiles()[0])
            except (OSError, RuntimeError, ValueError) as error:
                QMessageBox.warning(self, "Could not save image", str(error))

    def save_image(self, path):
        """Export the graph and its lossless source audio, without edit handles."""
        if self.current_data is None:
            raise ValueError("Generate a spectrogram before saving an image.")
        visible = self.mask_roi.isVisible()
        self.mask_roi.hide()
        try:
            exporter = ImageExporter(self.plot.getPlotItem())
            exporter.parameters()["width"] = 1600
            image = exporter.export(toBytes=True)
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if not image.save(buffer, "PNG"):
                raise OSError("The graph could not be rendered.")
            with Image.open(BytesIO(bytes(buffer.data()))) as preview:
                save_audio_png(preview, path, self.current_data.source_samples,
                               self.current_data.sample_rate)
        finally:
            self.mask_roi.setVisible(visible)

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
        self.save_button.setEnabled(False)
        self.mask_button.setEnabled(False)
        self.mask_roi.setVisible(False)
        self.live_playhead.setVisible(False)
        self.image.clear()
        self.info_label.setText(message or "Selection changed. Generate a new spectrogram from the sidebar.")
