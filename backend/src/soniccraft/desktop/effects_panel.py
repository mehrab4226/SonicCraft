"""Selection-based effect controls; all signal processing stays outside Qt."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QDoubleSpinBox, QComboBox, QGridLayout, QSpinBox,
    QSlider, QAbstractSpinBox,
)
import pyqtgraph as pg
from .theme import card, label, style_plot


def number(value, low, high, decimals=3):
    widget = QDoubleSpinBox()
    widget.setDecimals(decimals)
    widget.setRange(low, high)
    widget.setValue(value)
    widget.setKeyboardTracking(False)
    return widget


def button(layout, title, callback):
    widget = QPushButton(title)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    layout.addWidget(widget)
    return widget


def field(layout, title, widget):
    column = QVBoxLayout()
    caption = label(title)
    caption.setBuddy(widget)
    widget.setAccessibleName(title)
    column.addWidget(caption)
    column.addWidget(widget)
    layout.addLayout(column)


class EffectsPanel(QWidget):
    """Build reusable control cards; the sidebar owns their visible pages."""
    requested = pyqtSignal(str, object)
    preview_requested = pyqtSignal(str, object)
    profile_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.groups = []
        self._editing()
        self._filters()
        self._noise()

    def _page(self, title):
        page = QWidget(self)
        layout = QHBoxLayout(page)
        self.groups.append(layout)
        page.hide()
        return layout

    def _editing(self):
        layout = self._page("Edit && level")
        edits_card, edits = card("Essential edits", "Refine the selected range. Every edit is undoable.")
        grid = QGridLayout()
        grid.setSpacing(8)
        self.edit_buttons = {}
        hints = {
            "trim": "Keep only the selected audio",
            "delete": "Remove the selected audio and close the gap",
            "reverse": "Reverse the samples in the selection",
            "normalize": "Scale the selection to full scale",
            "silence": "Replace the selection with silence, keeping its duration",
        }
        for index, name in enumerate(hints):
            control = QPushButton(name.title())
            control.setToolTip(hints[name])
            control.clicked.connect(lambda checked=False, n=name: self.requested.emit(n, {}))
            if name == "delete":
                control.setProperty("danger", True)
            self.edit_buttons[name] = control
            grid.addWidget(control, index // 3, index % 3)
        edits.addLayout(grid)
        edits.addStretch()
        layout.addWidget(edits_card, 4)

        gain_card, gain = card("Gain", "Set the level with precise decibel control.")
        self.gain = number(0, -60, 24, 1)
        self.gain.setSuffix(" dB")
        self.gain.setAccessibleName("Gain in decibels")
        gain.addWidget(self.gain)
        self.gain_button = button(gain, "Apply gain", lambda: self.requested.emit("gain", {"gain_db": self.gain.value()}))
        self.gain_button.setProperty("primary", True)
        gain.addStretch()
        layout.addWidget(gain_card, 2)

        fade_card, fade = card("Fades", "Create a smooth entrance or a graceful exit.")
        row = QVBoxLayout()
        self.fade_duration = number(0.1, 0.000001, 36000, 6)
        self.fade_duration.setSuffix(" s")
        field(row, "Duration", self.fade_duration)
        self.fade_curve = QComboBox()
        for text, value in (("Linear", "linear"), ("Equal power", "equal_power"), ("Exponential", "exponential")):
            self.fade_curve.addItem(text, value)
        field(row, "Curve", self.fade_curve)
        fade.addLayout(row)
        row = QHBoxLayout()
        for direction in ("fade_in", "fade_out"):
            button(row, direction.replace("_", " ").title(), lambda checked=False, d=direction: self.requested.emit(
                "fade", {"seconds": self.fade_duration.value(), "direction": d, "curve": self.fade_curve.currentData()}
            ))
        fade.addLayout(row)
        fade.addStretch()
        layout.addWidget(fade_card, 4)

    def _filters(self):
        layout = self._page("Filters && EQ")
        filter_card, filters = card("Frequency filter")
        self.filter_kind = QComboBox()
        for text, value in (("Low-pass", "lowpass"), ("High-pass", "highpass"), ("Band-pass", "bandpass"), ("Band-stop", "bandstop")):
            self.filter_kind.addItem(text, value)
        self.filter_kind.setAccessibleName("Filter type")
        type_row = QHBoxLayout()
        type_row.addWidget(self.filter_kind, 1)
        self.order = QSpinBox()
        self.order.setRange(1, 10)
        self.order.setValue(4)
        self.order.setAccessibleName("Filter order")
        type_row.addWidget(label("Order"))
        type_row.addWidget(self.order)
        filters.addLayout(type_row)
        row = QHBoxLayout()
        self.low = number(1000, 0.01, 96000, 2)
        self.low.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.high = number(3000, 0.01, 96000, 2)
        self.high.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        field(row, "Cutoff / low · Hz", self.low)
        field(row, "High · Hz", self.high)
        filters.addLayout(row)
        row = QHBoxLayout()
        self.filter_button = button(row, "Apply filter", lambda: self.requested.emit("filter", self.filter_parameters()))
        self.filter_button.setProperty("primary", True)
        button(row, "Response", lambda: self.preview_requested.emit("filter", self.filter_parameters()))
        filters.addLayout(row)
        filters.addStretch()
        self.filter_kind.currentIndexChanged.connect(self._update_filter_fields)
        self._update_filter_fields()
        layout.addWidget(filter_card, 3)

        eq_card, equalizer = card("9-band equalizer")
        bands = QVBoxLayout()
        bands.setSpacing(6)
        self.eq_bands = {}
        self.eq_sliders = {}
        for frequency in (60, 120, 250, 500, 1000, 2000, 4000, 8000, 16000):
            band = QHBoxLayout()
            caption = label(f"{frequency // 1000}k" if frequency >= 1000 else str(frequency))
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setFixedWidth(28)
            band.addWidget(caption)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(-180, 180)
            slider.setValue(0)
            slider.setAccessibleName(f"{frequency} Hz gain")
            band.addWidget(slider, 1)
            gain = number(0, -18, 18, 1)
            gain.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            gain.setAlignment(Qt.AlignmentFlag.AlignCenter)
            gain.setMinimumWidth(44)
            gain.setFixedWidth(60)
            gain.setAccessibleName(f"{frequency} Hz gain in decibels")
            slider.valueChanged.connect(lambda value, g=gain: g.setValue(value / 10))
            gain.valueChanged.connect(lambda value, s=slider: s.setValue(round(value * 10)))
            self.eq_bands[frequency] = gain
            self.eq_sliders[frequency] = slider
            band.addWidget(gain)
            bands.addLayout(band, 1)
        equalizer.addLayout(bands, 1)
        row = QVBoxLayout()
        self.eq_button = button(row, "Apply EQ", lambda: self.requested.emit("eq", self.eq_parameters()))
        self.eq_button.setProperty("primary", True)
        button(row, "Response", lambda: self.preview_requested.emit("eq", self.eq_parameters()))
        button(row, "Reset", self.reset_eq)
        equalizer.addLayout(row)
        layout.addWidget(eq_card, 5)

        response_card, response = card("Response", "Preview the filter or EQ before applying.")
        self.response = pg.PlotWidget()
        style_plot(self.response)
        self.response.setLabel("bottom", "Frequency", units="Hz")
        self.response.setLabel("left", "Gain", units="dB")
        self.response.setMinimumSize(190, 100)
        self.response.setYRange(-18, 18)
        self.response.setMenuEnabled(False)
        response.addWidget(self.response, 1)
        layout.addWidget(response_card, 3)

    def _update_filter_fields(self):
        band_filter = self.filter_kind.currentData() in ("bandpass", "bandstop")
        self.high.setEnabled(band_filter)
        self.high.setToolTip("Upper cutoff frequency" if band_filter else "Used only by band-pass and band-stop filters")

    def reset_eq(self):
        for gain in self.eq_bands.values():
            gain.setValue(0)

    def filter_parameters(self):
        return {"kind": self.filter_kind.currentData(), "low": self.low.value(), "high": self.high.value(), "order": self.order.value()}

    def eq_parameters(self):
        return {"bands": [(frequency, gain.value()) for frequency, gain in self.eq_bands.items() if gain.isEnabled()]}

    def set_sample_rate(self, rate):
        for control in (self.low, self.high):
            control.setMaximum(rate / 2 - 0.01)
        for frequency, gain in self.eq_bands.items():
            enabled = frequency < rate / 2
            gain.setEnabled(enabled)
            self.eq_sliders[frequency].setEnabled(enabled)
            hint = f"{frequency} Hz · gain in dB" if enabled else "Band is at/above Nyquist for this file"
            gain.setToolTip(hint)
            self.eq_sliders[frequency].setToolTip(hint)

    def _noise(self):
        layout = self._page("Noise repair")
        profile_card, profile = card("01  Learn the noise", "Select a noise-only passage and capture its profile.")
        self.profile_label = label("No noise profile captured")
        self.profile_label.setWordWrap(True)
        profile.addWidget(self.profile_label)
        self.profile_button = button(profile, "Capture noise profile", self.profile_requested.emit)
        profile.addStretch()
        layout.addWidget(profile_card, 3)
        noise_card, noise = card("02  Restore the signal", "Select the audio to clean, choose a method, then apply.")
        self.noise_method = QComboBox()
        self.noise_method.addItems(["Frequency filter · uses Filters & EQ settings", "Spectral subtraction", "Wiener", "Spectral gate"])
        self.noise_method.setAccessibleName("Noise reduction method")
        noise.addWidget(self.noise_method)
        row = QVBoxLayout()
        self.noise_strength = number(1.5, 0.1, 5, 2)
        field(row, "Strength / gate threshold", self.noise_strength)
        self.wiener_window = QSpinBox()
        self.wiener_window.setRange(3, 999)
        self.wiener_window.setSingleStep(2)
        self.wiener_window.setValue(29)
        field(row, "Wiener window · samples", self.wiener_window)
        noise.addLayout(row)
        self.noise_button = button(noise, "Apply noise reduction", self._request_noise)
        self.noise_button.setProperty("primary", True)
        noise.addStretch()
        layout.addWidget(noise_card, 5)
        self.noise_method.currentIndexChanged.connect(self._update_noise_fields)
        self._update_noise_fields()

    def _update_noise_fields(self):
        index = self.noise_method.currentIndex()
        self.noise_strength.setEnabled(index in (1, 3))
        self.wiener_window.setEnabled(index == 2)

    def _request_noise(self):
        operation = ("filter", "subtraction", "wiener", "gate")[self.noise_method.currentIndex()]
        params = self.filter_parameters() if operation == "filter" else {
            "strength": self.noise_strength.value(), "window_size": self.wiener_window.value(),
        }
        self.requested.emit(operation, params)
