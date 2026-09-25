"""A drill-down tool library: category -> feature -> controls, with Back."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QFrame, QWidget, QVBoxLayout, QStackedWidget, QScrollArea, QComboBox
from .effects_panel import button, field
from .theme import label


CATEGORIES = (
    ("edit", "Edit & Dynamics", "Trim, level, and shape your audio"),
    ("filters", "Filters & Equalizer", "Sculpt frequencies and tonal balance"),
    ("noise", "Noise Reduction", "Capture noise and restore clarity"),
    ("spectrum", "Spectrum Analyzer", "Inspect frequency content with FFT"),
    ("spectrogram", "Spectrogram", "Explore frequency changes over time"),
    ("live", "Live Spectrogram", "Monitor your microphone in real time"),
)


class FeatureSidebar(QFrame):
    analysis_requested = pyqtSignal(str)
    spectrogram_requested = pyqtSignal()
    live_start_requested = pyqtSignal()
    live_stop_requested = pyqtSignal()

    def __init__(self, effects, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(290)
        self.setMaximumWidth(360)
        self.routes = {}
        self.parents = {}
        self.category_buttons = {}
        self.feature_buttons = {}
        self.audio_controls = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)
        layout.addWidget(label("TOOL LIBRARY", "eyebrow"))
        self.back_button = button(layout, "‹  All tools", self.back)
        self.title = label("Create. Refine. Explore.", "sectionTitle")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.hint = label("Choose a category to reveal its tools.")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        home = self._page("home", "Create. Refine. Explore.")
        for key, title, subtitle in CATEGORIES:
            control = button(home, title.replace("&", "&&") + "   ›\n" + subtitle, lambda checked=False, k=key: self.navigate(k))
            control.setObjectName("categoryButton")
            control.setAccessibleName(title)
            self.category_buttons[key] = control
        home.addStretch()

        edit = self._page("edit", "Edit & Dynamics", "home")
        edit.addWidget(label("SELECTION EDITS", "eyebrow"))
        for name, control in effects.edit_buttons.items():
            control.setText({"trim": "Trim to selection", "delete": "Delete selection", "reverse": "Reverse", "normalize": "Normalize peak", "silence": "Silence selection"}[name])
            edit.addWidget(control)
            self.audio_controls.append(control)
        self._link(edit, "gain", "Gain / volume", "gain")
        self._link(edit, "fades", "Fade in / fade out", "fades")
        edit.addStretch()
        filters = self._page("filters", "Filters & Equalizer", "home")
        self._link(filters, "filter", "Frequency filter", "filter")
        self._link(filters, "eq", "9-band equalizer", "eq")
        filters.addStretch()
        noise = self._page("noise", "Noise Reduction", "home")
        self._link(noise, "profile", "Capture noise profile", "profile")
        self._link(noise, "reduction", "Reduce noise", "reduction")
        noise.addStretch()

        # Reparent each actual control card; parameters remain stable as the
        # user navigates. The old horizontal Sound shaping panel is gone.
        cards = [[group.itemAt(i).widget() for i in range(group.count())] for group in effects.groups]
        for key, title, parent_key, card in (
            ("gain", "Gain / volume", "edit", cards[0][1]),
            ("fades", "Fades", "edit", cards[0][2]),
            ("filter", "Frequency filter", "filters", cards[1][0]),
            ("eq", "9-band equalizer", "filters", cards[1][1]),
            ("profile", "Capture noise profile", "noise", cards[2][0]),
            ("reduction", "Reduce noise", "noise", cards[2][1]),
        ):
            page = self._page(key, title, parent_key)
            page.addWidget(card)
            page.addStretch()
            self.audio_controls.append(card)

        spectrum = self._page("spectrum", "Spectrum Analyzer", "home")
        hint = label("The lower workspace shows the FFT of your selection. Drag the waveform handles to inspect a different passage.")
        hint.setWordWrap(True)
        spectrum.addWidget(hint)
        self.spectrum_scope = label("Open audio to analyze its frequencies.")
        self.spectrum_scope.setWordWrap(True)
        spectrum.addWidget(self.spectrum_scope)
        spectrum.addStretch()

        spectrogram = self._page("spectrogram", "Spectrogram", "home")
        self.fft_size = QComboBox()
        self.fft_size.addItems(["512", "1024", "2048", "4096"])
        self.fft_size.setCurrentText("2048")
        field(spectrogram, "FFT size · samples", self.fft_size)
        self.window_function = QComboBox()
        self.window_function.addItems(["hann", "hamming", "blackman"])
        field(spectrogram, "Window function", self.window_function)
        hint = label("Shows the selected range as a time-frequency map. Stereo channels are mixed to mono. Long selections use a coarser time step to keep the view responsive.")
        hint.setWordWrap(True)
        spectrogram.addWidget(hint)
        self.render_button = button(spectrogram, "Generate spectrogram", self.spectrogram_requested.emit)
        self.render_button.setProperty("primary", True)
        self.audio_controls.append(self.render_button)
        spectrogram.addStretch()

        live = self._page("live", "Live Spectrogram", "home")
        self.input_device = QComboBox()
        self.input_device.addItem("System default", None)
        field(live, "Microphone input", self.input_device)
        self.live_fft_size = QComboBox()
        self.live_fft_size.addItems(["512", "1024", "2048", "4096"])
        self.live_fft_size.setCurrentText("1024")
        field(live, "Live FFT size · samples", self.live_fft_size)
        hint = label("Monitor the most recent 8 seconds. Your microphone opens only when you start monitoring. Audio is not saved to a file.")
        hint.setWordWrap(True)
        live.addWidget(hint)
        self.live_status = label("Microphone is off.")
        self.live_status.setWordWrap(True)
        live.addWidget(self.live_status)
        self.live_start = button(live, "Start monitoring", self.live_start_requested.emit)
        self.live_start.setProperty("primary", True)
        self.live_stop = button(live, "Stop monitoring", self.live_stop_requested.emit)
        self.record_live = QCheckBox("Record to Document")
        self.record_live.setAccessibleName("Record to Document")
        live.addWidget(self.record_live)
        self.set_monitoring(False)
        live.addStretch()
        self.navigate("home")

    def _page(self, key, title, parent=None):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 3, 0)
        layout.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.routes[key] = (scroll, title)
        self.parents[key] = parent
        self.stack.addWidget(scroll)
        return layout

    def _link(self, layout, key, title, destination):
        self.feature_buttons[key] = button(layout, title + "   ›", lambda: self.navigate(destination))

    def navigate(self, key):
        page, title = self.routes[key]
        self.current_route = key
        self.stack.setCurrentWidget(page)
        self.title.setText(title)
        parent = self.parents[key]
        self.back_button.setVisible(parent is not None)
        self.back_button.setText("‹  All tools" if parent == "home" else "‹  Back to category")
        self.hint.setText("Choose a category to reveal its tools." if key == "home" else "Effects apply to your waveform selection.\nCtrl+Z to undo.")
        if key in ("spectrum", "spectrogram", "live"):
            self.hint.setText("Analysis occupies the lower workspace.")
            self.analysis_requested.emit(key)
        self.stack.setFocus()

    def back(self):
        parent = self.parents[self.current_route]
        if parent:
            self.navigate(parent)

    def set_audio_available(self, available):
        for control in self.audio_controls:
            control.setEnabled(available)

    def set_monitoring(self, active):
        self.live_start.setEnabled(not active)
        self.live_stop.setEnabled(active)
        self.input_device.setEnabled(not active)
        self.live_status.setText("● Monitoring microphone" if active else "Microphone is off.")
