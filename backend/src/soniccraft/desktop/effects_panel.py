"""Parameter widgets emit requests; processing stays outside Qt."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QComboBox, QTabWidget, QGridLayout, QSpinBox,
)
import pyqtgraph as pg


def number(value, low, high, decimals=3):
    widget = QDoubleSpinBox()
    widget.setDecimals(decimals)
    widget.setRange(low, high)
    widget.setValue(value)
    return widget


def button(layout, title, callback):
    widget = QPushButton(title)
    widget.clicked.connect(callback)
    layout.addWidget(widget)
    return widget


class EffectsPanel(QTabWidget):
    requested = pyqtSignal(str, object)
    preview_requested = pyqtSignal(str, object)
    profile_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Edits and effects apply to the highlighted waveform selection."))
        edits = QHBoxLayout()
        self.edit_buttons = {}
        for name in ("trim", "delete", "reverse", "normalize", "silence"):
            self.edit_buttons[name] = button(edits, name.title(), lambda checked=False, n=name: self.requested.emit(n, {}))
        layout.addLayout(edits)
        gain = QHBoxLayout()
        gain.addWidget(QLabel("Gain (dB)"))
        self.gain = number(0, -60, 24, 1)
        gain.addWidget(self.gain)
        self.gain_button = button(gain, "Apply gain", lambda: self.requested.emit("gain", {"gain_db": self.gain.value()}))
        layout.addLayout(gain)
        fade = QHBoxLayout()
        fade.addWidget(QLabel("Fade duration (s)"))
        self.fade_duration = number(0.1, 0.000001, 36000, 6)
        fade.addWidget(self.fade_duration)
        self.fade_curve = QComboBox()
        self.fade_curve.addItems(["linear", "equal_power", "exponential"])
        fade.addWidget(self.fade_curve)
        for direction in ("fade_in", "fade_out"):
            button(fade, direction.replace("_", " ").title(), lambda checked=False, d=direction: self.requested.emit(
                "fade", {"seconds": self.fade_duration.value(), "direction": d, "curve": self.fade_curve.currentText()}
            ))
        layout.addLayout(fade)
        layout.addStretch()
        self.addTab(page, "Edit / Volume")
        self._filters()
        self._noise()

    def _filters(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.filter_kind = QComboBox()
        self.filter_kind.addItems(["lowpass", "highpass", "bandpass", "bandstop"])
        row.addWidget(self.filter_kind)
        row.addWidget(QLabel("Cutoff / low (Hz)"))
        self.low = number(1000, 0.01, 96000, 2)
        row.addWidget(self.low)
        row.addWidget(QLabel("High (band filters)"))
        self.high = number(3000, 0.01, 96000, 2)
        row.addWidget(self.high)
        self.order = QSpinBox()
        self.order.setRange(1, 10)
        self.order.setValue(4)
        row.addWidget(QLabel("Order"))
        row.addWidget(self.order)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.filter_button = button(row, "Apply filter", lambda: self.requested.emit("filter", self.filter_parameters()))
        button(row, "Filter response", lambda: self.preview_requested.emit("filter", self.filter_parameters()))
        layout.addLayout(row)
        bands = QGridLayout()
        self.eq_bands = {}
        for index, frequency in enumerate((60, 120, 250, 500, 1000, 2000, 4000, 8000, 16000)):
            bands.addWidget(QLabel(f"{frequency} Hz"), 0, index)
            gain = number(0, -18, 18, 1)
            self.eq_bands[frequency] = gain
            bands.addWidget(gain, 1, index)
        layout.addLayout(bands)
        row = QHBoxLayout()
        self.eq_button = button(row, "Apply multiband EQ (dB)", lambda: self.requested.emit("eq", self.eq_parameters()))
        button(row, "EQ response", lambda: self.preview_requested.emit("eq", self.eq_parameters()))
        layout.addLayout(row)
        self.response = pg.PlotWidget(background="#0b0f16")
        self.response.setLabel("bottom", "Frequency", units="Hz")
        self.response.setLabel("left", "Filter response", units="dB")
        self.response.setMinimumHeight(100)
        layout.addWidget(self.response)
        self.addTab(page, "Filters / EQ")

    def filter_parameters(self):
        return {"kind": self.filter_kind.currentText(), "low": self.low.value(), "high": self.high.value(), "order": self.order.value()}

    def eq_parameters(self):
        return {"bands": [(frequency, gain.value()) for frequency, gain in self.eq_bands.items() if gain.isEnabled()]}

    def set_sample_rate(self, rate):
        for control in (self.low, self.high):
            control.setMaximum(rate / 2 - 0.01)
        for frequency, gain in self.eq_bands.items():
            gain.setEnabled(frequency < rate / 2)
            gain.setToolTip("Gain (dB)" if frequency < rate / 2 else "Band is at/above Nyquist for this file")

    def _noise(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Capture a noise-only selection, then select the audio to clean. Profiles remain local."))
        self.profile_label = QLabel("No noise profile captured")
        layout.addWidget(self.profile_label)
        self.profile_button = button(layout, "Capture noise profile from selection", self.profile_requested.emit)
        self.noise_method = QComboBox()
        self.noise_method.addItems(["Frequency filter (use Filters / EQ settings)", "Spectral subtraction", "Wiener", "Spectral gate"])
        layout.addWidget(self.noise_method)
        row = QHBoxLayout()
        row.addWidget(QLabel("Subtraction strength / gate threshold"))
        self.noise_strength = number(1.5, 0.1, 5, 2)
        row.addWidget(self.noise_strength)
        row.addWidget(QLabel("Wiener window (odd samples)"))
        self.wiener_window = QSpinBox()
        self.wiener_window.setRange(3, 999)
        self.wiener_window.setSingleStep(2)
        self.wiener_window.setValue(29)
        row.addWidget(self.wiener_window)
        layout.addLayout(row)
        self.noise_button = button(layout, "Apply noise reduction", self._request_noise)
        layout.addStretch()
        self.addTab(page, "Noise removal")

    def _request_noise(self):
        operation = ("filter", "subtraction", "wiener", "gate")[self.noise_method.currentIndex()]
        params = self.filter_parameters() if operation == "filter" else {
            "strength": self.noise_strength.value(), "window_size": self.wiener_window.value(),
        }
        self.requested.emit(operation, params)
