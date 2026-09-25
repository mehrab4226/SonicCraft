"""Desktop controller: one document shared by views, DSP jobs and local streams."""
from pathlib import Path
import math
import numpy as np
from scipy.signal import resample
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QMessageBox, QToolBar, QVBoxLayout, QWidget,
    QFileDialog, QLabel, QComboBox, QHBoxLayout,
    QFrame, QSplitter, QStackedWidget, QToolButton, QSizePolicy, QProgressBar, QTabWidget
)
import sounddevice as sd

from soniccraft import __version__
from .document import AudioData, Document
from .audio_engine import Player, Microphone
from .jobs import Job
from .waveform_widget import WaveformWidget
from .effects_panel import EffectsPanel, number, button
from .processing import process, sample_range, filter_sections, check_transform_size
from soniccraft.dsp.filters import frequency_response
from soniccraft.dsp.noise_reduction import estimate_noise_profile
from .spectrum_widget import SpectrumWidget
from soniccraft.dsp.transforms import fft_spectrum, image_to_audio, stft, inverse_stft
from .theme import label, icon, FileTitle
from .sidebar import FeatureSidebar
from .spectrogram_widget import SpectrogramWidget
from .analysis import make_spectrogram

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("soniccraftMainWindow")
        self.setWindowTitle("SonicCraft — Audio Editor")
        self.resize(1380, 960)
        self.setMinimumSize(1000, 760)
        self.setAcceptDrops(True)
        self.document = Document()
        self.player = Player()
        self.microphone = Microphone()
        self.live_job = None
        self.live_samples = np.empty(0)
        self.live_sample_count = 0
        self.live_generation = 0
        self.job = None
        self.noise_profile = None
        self.actions_by_name = {}
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_workspace()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(150)
        self.live_timer.timeout.connect(self._live_tick)
        self.refresh_devices()
        self.refresh()

    def _action(self, name, text, callback, shortcut=None):
        action = QAction(text, self)
        action.setObjectName(name)
        if name in ("open", "save", "undo", "redo", "play", "pause", "stop", "spectrum"):
            action.setIcon(icon(name, "#10271f" if name == "play" else "#c9d7d4"))
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        self.actions_by_name[name] = action
        return action

    def _build_actions(self):
        self._action("open", "&Open audio…", self.open_dialog, QKeySequence.StandardKey.Open)
        self._action("import_image", "Import Spectrogram Image...", self.import_image_dialog)
        self._action("save", "&Export audio…", self.save_dialog, QKeySequence.StandardKey.Save)
        self._action("play", "&Play", self.toggle_playback, "Space")
        self.addAction(self.actions_by_name["play"])
        self._action("stop", "S&top", self.stop)
        self._action("undo", "&Undo", self.undo, QKeySequence.StandardKey.Undo)
        self._action("redo", "&Redo", self.redo, QKeySequence.StandardKey.Redo)
        self._action("reset_audio", "Reset audio", self.reset_audio)
        self.actions_by_name["reset_audio"].setToolTip("Restore the original loaded audio and select its full range. Ctrl+Z undoes the reset.")
        self._action("exit", "E&xit", self.close, QKeySequence.StandardKey.Quit)
        self._action("reset_view", "&Reset waveform view", lambda: self.waveform.reset_view())
        self._action("zoom_selection", "Focus selection", lambda: self.waveform.zoom_selection(), "Ctrl+J")
        self._action("select_all", "Select all", lambda: self.waveform.set_selection(0, self.document.audio.duration) if self.document.audio else None, QKeySequence.StandardKey.SelectAll)
        self.addAction(self.actions_by_name["zoom_selection"])
        self.addAction(self.actions_by_name["select_all"])
        self._action("about", "&About SonicCraft", self._show_about)
        self._action("devices", "Refresh audio devices", self.refresh_devices)
        self._action("spectrum", "FFT Spectrum Analyzer", self.toggle_spectrum)
        self.actions_by_name["spectrum"].setCheckable(True)
        self._action("spectrogram", "Spectrogram", lambda: self.sidebar.navigate("spectrogram"))
        self._action("live_spectrogram", "Live Spectrogram", lambda: self.sidebar.navigate("live"))
        for name, route, title in (("volume_panel", "edit", "Edit && Dynamics"), ("eq_panel", "filters", "Filters && Equalizer"), ("noise_panel", "noise", "Noise Reduction")):
            self._action(name, title, lambda checked=False, key=route: self.sidebar.navigate(key))
        for name in ("trim", "delete", "reverse", "normalize", "silence"):
            self._action(name, name.title(), lambda checked=False, n=name: self.apply_operation(n, {}))

    def _build_menus(self):
        self.menus = {}
        for title, names in (
            ("&File", ("open", "import_image", "save", "exit")),
            ("&Edit", ("undo", "redo", "reset_audio", "trim", "delete", "reverse", "silence")),
            ("&Effects", ("normalize", "volume_panel", "eq_panel", "noise_panel")), ("&Analysis", ("spectrum", "spectrogram", "live_spectrogram")),
            ("&View", ("reset_view", "zoom_selection", "devices")), ("&Help", ("about",)),
        ):
            menu = self.menuBar().addMenu(title)
            self.menus[title] = menu
            for name in names:
                menu.addAction(self.actions_by_name[name])
        self.view_menu = self.menus["&View"]

    def _build_toolbar(self):
        toolbar = QToolBar("Transport", self)
        toolbar.setObjectName("transportToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(19, 19))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        mark = QLabel()
        mark.setPixmap(icon("brand", "#91efd0").pixmap(32, 32))
        toolbar.addWidget(mark)
        toolbar.addWidget(label("SonicCraft", "brand"))
        toolbar.addSeparator()
        for name in ("open", "save", "undo", "redo"):
            toolbar.addAction(self.actions_by_name[name])
            if name in ("undo", "redo"):
                toolbar.widgetForAction(self.actions_by_name[name]).setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        self.timecode = label("00:00.000", "timecode")
        toolbar.addWidget(self.timecode)
        for name in ("play", "stop"):
            toolbar.addAction(self.actions_by_name[name])
            control = toolbar.widgetForAction(self.actions_by_name[name])
            control.setObjectName(name + "Button")
            if name != "play":
                control.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            if name == "play":
                self.play_button = control
                control.setMinimumWidth(92)
            else:
                control.setToolTip("Stop and return to the beginning")
        self.addToolBar(toolbar)
        self.view_menu.addAction(toolbar.toggleViewAction())
        self.transport_toolbar = toolbar

    def _build_workspace(self):
        self.workspace = QWidget(self)
        self.workspace.setObjectName("workspace")
        outer = QHBoxLayout(self.workspace)
        outer.setContentsMargins(16, 14, 16, 10)
        outer.setSpacing(16)
        self.effects = EffectsPanel(self)
        self.effects.hide()
        self.sidebar = FeatureSidebar(self.effects)
        self.reset_button = QToolButton()
        self.reset_button.setDefaultAction(self.actions_by_name["reset_audio"])
        self.reset_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.sidebar.layout().addWidget(self.reset_button)
        outer.addWidget(self.sidebar)
        self.editor_workspace = QWidget()
        outer.addWidget(self.editor_workspace, 1)
        self.layout = QVBoxLayout(self.editor_workspace)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        heading = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(label("AUDIO WORKSPACE", "eyebrow"))
        self.file_title = FileTitle("Your next sound starts here.")
        title.addWidget(self.file_title)
        heading.addLayout(title, 1)
        self.document_badge = label("LOCAL SESSION", "badge")
        self.document_badge.setFixedHeight(28)
        heading.addWidget(self.document_badge)
        self.layout.addLayout(heading)
        self.metadata = label("Precision editing. Thoughtful processing. Entirely on your device.")
        self.metadata.setWordWrap(True)
        self.layout.addWidget(self.metadata)

        self.metrics_panel = QWidget()
        metrics = QHBoxLayout(self.metrics_panel)
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(12)
        self.metric_values = {}
        for key, title in (("duration", "DURATION"), ("rate", "SAMPLE RATE"), ("channels", "CHANNELS"), ("peak", "PEAK LEVEL")):
            frame = QFrame()
            frame.setObjectName("metric")
            column = QVBoxLayout(frame)
            column.setContentsMargins(16, 8, 16, 8)
            column.addWidget(label(title, "muted"))
            self.metric_values[key] = label("—", "metricValue")
            column.addWidget(self.metric_values[key])
            metrics.addWidget(frame, 1)
        self.layout.addWidget(self.metrics_panel)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        waveform_panel = QFrame()
        self.waveform_panel = waveform_panel
        waveform_panel.setObjectName("panel")
        waveform_panel.setMinimumHeight(270)
        wave_layout = QVBoxLayout(waveform_panel)
        wave_layout.setContentsMargins(14, 12, 14, 12)
        wave_header = QHBoxLayout()
        wave_header.addWidget(label("01   Waveform", "sectionTitle"))
        self.channel_legend = label("TIME DOMAIN", "eyebrow")
        wave_header.addWidget(self.channel_legend)
        wave_header.addStretch()
        for name, text in (("zoom_selection", "Focus selection"), ("reset_view", "Fit audio"), ("spectrum", "Spectrum")):
            control = QToolButton()
            self.actions_by_name[name].setIconText(text)
            control.setDefaultAction(self.actions_by_name[name])
            control.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            wave_header.addWidget(control)
        wave_layout.addLayout(wave_header)
        self.wave_stack = QStackedWidget()
        self.wave_stack.setMinimumHeight(150)
        self.wave_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.empty_state = QFrame()
        self.empty_state.setObjectName("emptyState")
        empty = QVBoxLayout(self.empty_state)
        empty.setSpacing(6)
        empty.addStretch()
        empty.addWidget(label("Make every detail heard.", "heroTitle"), 0, Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(label("Drop an audio file here to shape, refine, and explore your sound."), 0, Qt.AlignmentFlag.AlignCenter)
        self.import_button = button(empty, "Open audio file  ·  Ctrl+O", self.open_dialog)
        self.import_button.setProperty("primary", True)
        self.import_button.setMinimumHeight(36)
        empty.setAlignment(self.import_button, Qt.AlignmentFlag.AlignCenter)
        self.format_hint = label("WAV  /  FLAC  /  OGG  /  AIFF  /  MP3")
        empty.addWidget(self.format_hint, 0, Qt.AlignmentFlag.AlignCenter)
        empty.addStretch()
        self.wave_stack.addWidget(self.empty_state)
        self.waveform = WaveformWidget(self)
        self.wave_stack.addWidget(self.waveform)
        wave_layout.addWidget(self.wave_stack, 1)
        self.selection_panel = QFrame()
        self.selection_panel.setObjectName("selectionPanel")
        selection = QHBoxLayout(self.selection_panel)
        selection.setContentsMargins(12, 8, 12, 8)
        selection.addWidget(label("In"))
        self.start_time = number(0, 0, 36000, 6)
        self.start_time.setAccessibleName("Selection start in seconds")
        self.start_time.setSuffix(" s")
        self.start_time.setFixedWidth(110)
        self.end_time = number(1, 0, 36000, 6)
        self.end_time.setAccessibleName("Selection end in seconds")
        self.end_time.setSuffix(" s")
        self.end_time.setFixedWidth(110)
        selection.addWidget(self.start_time)
        selection.addWidget(label("Out"))
        selection.addWidget(self.end_time)
        button(selection, "Set range", self.set_selection_from_inputs)
        button(selection, "Select all", self.actions_by_name["select_all"].trigger)
        selection.addStretch()
        self.selection_status = label("No selection")
        selection.addWidget(self.selection_status)
        wave_layout.addWidget(self.selection_panel)
        self.splitter.addWidget(waveform_panel)

        self.analysis_panel = QFrame()
        self.analysis_panel.setObjectName("panel")
        analysis_layout = QVBoxLayout(self.analysis_panel)
        analysis_layout.setContentsMargins(8, 6, 8, 6)
        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setMinimumHeight(190)
        self.spectrum_widget = SpectrumWidget()
        self.spectrogram_widget = SpectrogramWidget()
        self.live_spectrogram = SpectrogramWidget(live=True)
        self.live_spectrogram.stop_requested.connect(self.stop_live)
        self.analysis_tabs.addTab(self.spectrum_widget, "Spectrum Analyzer")
        self.analysis_tabs.addTab(self.spectrogram_widget, "Spectrogram")
        self.analysis_tabs.addTab(self.live_spectrogram, "Live Spectrogram")
        self.analysis_tabs.addTab(self.effects.response, "Filter Response")
        analysis_layout.addWidget(self.analysis_tabs)
        self.analysis_tabs.currentChanged.connect(self._analysis_tab_changed)
        self.sidebar.analysis_requested.connect(self.show_analysis)
        self.sidebar.spectrogram_requested.connect(self.generate_spectrogram)
        self.spectrogram_widget.mask_requested.connect(self._apply_spectral_mask)
        self.sidebar.fft_size.currentIndexChanged.connect(lambda: self.spectrogram_widget.clear("FFT size changed. Generate a new spectrogram."))
        self.sidebar.window_function.currentIndexChanged.connect(lambda: self.spectrogram_widget.clear("Window changed. Generate a new spectrogram."))
        self.sidebar.live_start_requested.connect(self.start_live)
        self.sidebar.live_stop_requested.connect(self.stop_live)
        self.effects.requested.connect(self.apply_operation)
        self.effects.preview_requested.connect(self.preview_filter)
        self.effects.profile_requested.connect(self.capture_profile)
        self.splitter.addWidget(self.analysis_panel)
        self.splitter.setSizes([350, 350])
        self.layout.addWidget(self.splitter, 1)
        devices = QHBoxLayout()
        devices.addWidget(label("OUTPUT", "eyebrow"))
        self.output_device = QComboBox()
        self.output_device.setAccessibleName("Audio output device")
        self.output_device.setMaximumWidth(420)
        devices.addWidget(self.output_device)
        devices.addStretch()
        self.shortcut_hint = label("Space  Play / pause     •     Ctrl+J  Focus selection")
        devices.addWidget(self.shortcut_hint)
        self.layout.addLayout(devices)
        self.waveform.selection_changed.connect(self._selection_changed)
        self.setCentralWidget(self.workspace)
        self.busy_indicator = QProgressBar()
        self.busy_indicator.setRange(0, 0)
        self.busy_indicator.setTextVisible(False)
        self.busy_indicator.setFixedWidth(120)
        self.statusBar().addPermanentWidget(self.busy_indicator)
        self.busy_indicator.hide()
        self.transport_status = label("●  IDLE", "eyebrow")
        self.statusBar().addPermanentWidget(self.transport_status)
        self.actions_by_name["spectrum"].setChecked(True)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_initial_layout_set", False):
            self._initial_layout_set = True
            self.splitter.setSizes([max(270, self.splitter.height() - 340), 330])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "metrics_panel"):
            self._adapt_layout()

    def _adapt_layout(self):
        compact = self.height() < 880
        self.metrics_panel.setVisible(not compact)
        self.metadata.setVisible(not compact)
        self.waveform_panel.setMinimumHeight(240 if compact else 260)
        self.wave_stack.setMinimumHeight(120 if compact else 140)
        self.format_hint.setVisible(not compact)
        self.channel_legend.setVisible(self.width() >= 1200)
        self.shortcut_hint.setVisible(self.width() >= 1200)
        self.selection_status.setVisible(self.width() >= 1200)

    def set_selection_from_inputs(self):
        if self.start_time.value() >= self.end_time.value():
            self.error("The selection end must be after its start.")
            return
        self.waveform.set_selection(self.start_time.value(), self.end_time.value())

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if self.job is None and len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() in {".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3"}:
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if self.job is None and len(urls) == 1 and urls[0].isLocalFile() and self.confirm_discard():
            self.open_path(urls[0].toLocalFile())
            event.acceptProposedAction()

    def _selection_changed(self, start, end):
        self.start_time.setValue(start)
        self.end_time.setValue(end)
        self.selection_status.setText(f"{end - start:.3f} s selected")
        self.spectrogram_widget.clear()
        self.update_spectrum()

    def toggle_spectrum(self):
        self.sidebar.navigate("spectrum")

    def show_analysis(self, mode):
        self.analysis_tabs.setCurrentIndex({"spectrum": 0, "spectrogram": 1, "live": 2, "response": 3}[mode])
        self.actions_by_name["spectrum"].setChecked(mode == "spectrum")
        if mode == "spectrum":
            self.update_spectrum()

    def _analysis_tab_changed(self, index):
        self.actions_by_name["spectrum"].setChecked(index == 0)
        if index != 2:
            self.stop_live()
        if index == 0:
            self.update_spectrum()

    def update_spectrum(self):
        """Runs the FFT math and pushes data to the UI widget."""
        if self.document.audio is None or self.analysis_tabs.currentIndex() != 0:
            return
            
        try:
            start, end = self.playback_range()
            if start >= end:
                return
            if end - start < 2:
                self.spectrum_widget.plot_curve.setData([], [])
                self.spectrum_widget.current_spectrum = None
                self.spectrum_widget.info_label.setText("Select at least two samples for FFT analysis.")
                return

            selection_size = len(self.document.audio.samples[start:end])
            samples = self.document.audio.samples[start:end]
            if len(samples) > 131072:
                samples = resample(samples, 131072, axis=0)

            spectrum = fft_spectrum(samples, self.document.audio.sample_rate)
            self.spectrum_widget.set_spectrum(spectrum)
            detail = f"resampled to {len(samples):,} points for display" if len(samples) != selection_size else "full resolution"
            self.sidebar.spectrum_scope.setText(
                f"Analyzing {selection_size:,} selected samples from "
                f"{start / self.document.audio.sample_rate:.3f} s ({detail})."
            )
            
        except Exception as error:
            self.spectrum_widget.info_label.setText(f"Cannot analyze selection: {error}")

    def generate_spectrogram(self):
        audio = self.document.audio
        if audio is None:
            return
        try:
            start, end = self.playback_range()
        except ValueError as error:
            self.error(error)
            return
        self.show_analysis("spectrogram")
        size = int(self.sidebar.fft_size.currentText())
        window = self.sidebar.window_function.currentText()
        self.run_job("Generating spectrogram", lambda: make_spectrogram(
            audio.samples[start:end], audio.sample_rate, size, window, offset=start / audio.sample_rate
        ), self.spectrogram_widget.set_data)

    def _apply_spectral_mask(self, t_start, t_end, f_start, f_end):
        audio = self.document.audio
        if audio is None:
            return
        try:
            start, end = self.playback_range()
        except ValueError as error:
            self.error(error)
            return

        samples = audio.samples[start:end]
        selection_offset = start / audio.sample_rate

        def worker():
            transform = stft(samples, audio.sample_rate, n_fft=2048)
            time_start = t_start - selection_offset
            time_end = t_end - selection_offset
            time_mask = (transform.times >= time_start) & (transform.times <= time_end)
            frequency_mask = (transform.frequencies >= f_start) & (transform.frequencies <= f_end)
            transform.spectrum[np.ix_(frequency_mask, time_mask)] = 0
            changed = inverse_stft(transform)
            result = audio.samples.copy()
            result[start:end] = changed
            return result

        self.run_job("Applying spectral mask", worker, self._edited)

    def start_live(self):
        self.show_analysis("live")
        self.stop()
        self.stop_live()
        try:
            self.microphone.start(self.sidebar.input_device.currentData())
        except Exception as error:
            self.sidebar.live_status.setText(f"Microphone unavailable: {error}")
            return
        self.live_generation += 1
        self.live_samples = np.empty(0)
        self.live_sample_count = 0
        self.live_spectrogram.clear("Listening for microphone audio…")
        self.sidebar.set_monitoring(True)
        self.live_spectrogram.stop_button.setEnabled(True)
        self.live_timer.start()

    def stop_live(self):
        was_monitoring = self.microphone.stream is not None
        self.live_generation += 1
        if hasattr(self, "live_timer"):
            self.live_timer.stop()
        try:
            self.microphone.stop()
        except Exception as error:
            self.statusBar().showMessage(f"Microphone stop failed: {error}")
        self.sidebar.set_monitoring(False)
        self.live_spectrogram.stop_button.setEnabled(False)
        if was_monitoring and self.live_spectrogram.current_data is not None:
            self.live_spectrogram.info_label.setText("Monitoring stopped · last captured view retained.")

    def _live_tick(self):
        if self.microphone.stream is None:
            return
        if not self.microphone.stream.active:
            self.stop_live()
            self.sidebar.live_status.setText("Microphone stopped. Check the input device and restart.")
            return
        blocks = self.microphone.drain()
        if blocks:
            incoming = np.concatenate(blocks)
            self.live_sample_count += len(incoming)
            self.live_samples = np.concatenate((self.live_samples, incoming))[-int(self.microphone.sample_rate * 8):]
        if self.microphone.dropped or self.microphone.warning:
            self.sidebar.live_status.setText(f"Monitoring · {self.microphone.dropped} dropped blocks. {self.microphone.warning}")
        if not blocks or self.live_job is not None:
            return
        samples = self.live_samples.copy()
        rate = self.microphone.sample_rate
        offset = (self.live_sample_count - len(samples)) / rate
        generation = self.live_generation
        self.live_job = Job(lambda: make_spectrogram(samples, rate, 1024, offset=offset, max_frames=320), self)
        def display(result):
            if generation == self.live_generation:
                self.live_spectrogram.set_data(result)
        def failed(message):
            if generation == self.live_generation:
                self.stop_live()
                self.sidebar.live_status.setText(f"Monitoring stopped: {message}")
        self.live_job.succeeded.connect(display)
        self.live_job.failed.connect(failed)
        self.live_job.finished.connect(self._live_job_finished)
        self.live_job.start()

    def _live_job_finished(self):
        self.live_job.deleteLater()
        self.live_job = None

    def apply_operation(self, operation, parameters):
        audio = self.document.audio
        if audio is None:
            return
        parameters = {**parameters, "profile": self.noise_profile}
        try:
            bounds = self.playback_range()
        except ValueError as error:
            self.error(error)
            return
        self.run_job(operation.title(), lambda: process(audio, bounds, operation, parameters), self._edited)

    def preview_filter(self, operation, parameters):
        audio = self.document.audio
        if audio is None:
            return
        def display(response):
            self.effects.response.clear()
            self.effects.response.plot(response.frequencies, response.magnitude_db, pen="#91efd0")
            self.show_analysis("response")
        self.run_job("Calculating filter response", lambda: frequency_response(
            filter_sections(operation, parameters, audio.sample_rate), audio.sample_rate
        ), display)

    def capture_profile(self):
        audio = self.document.audio
        if audio is None:
            return
        try:
            start, end = self.playback_range()
            check_transform_size(audio.samples[start:end], 2048, 512)
        except ValueError as error:
            self.error(error)
            return
        def captured(profile):
            self.noise_profile = profile
            self.effects.profile_label.setText(f"Captured {start / audio.sample_rate:.3f}–{end / audio.sample_rate:.3f} s, {audio.channels} channel(s)")
        self.run_job("Estimating noise", lambda: estimate_noise_profile(audio.samples[start:end], audio.sample_rate), captured)

    def _edited(self, samples):
        self.document.commit(samples)
        self.refresh()

    def refresh_devices(self):
        if not hasattr(self, "output_device"):
            return
        selected = self.output_device.currentData()
        input_selected = self.sidebar.input_device.currentData()
        self.output_device.clear()
        self.output_device.addItem("System default", None)
        self.sidebar.input_device.clear()
        self.sidebar.input_device.addItem("System default", None)
        try:
            for index, device in enumerate(sd.query_devices()):
                if device["max_output_channels"] > 0:
                    self.output_device.addItem(device["name"], index)
                if device["max_input_channels"] > 0:
                    self.sidebar.input_device.addItem(device["name"], index)
            match = self.output_device.findData(selected)
            self.output_device.setCurrentIndex(max(0, match))
            self.sidebar.input_device.setCurrentIndex(max(0, self.sidebar.input_device.findData(input_selected)))
        except Exception as error:
            self.statusBar().showMessage(f"Audio device discovery failed: {error}")

    def error(self, message):
        QMessageBox.warning(self, "SonicCraft", str(message))

    def run_job(self, title, function, on_success):
        if self.job is not None:
            return
        self.stop()
        self.stop_live()
        self.statusBar().showMessage(title + "…")
        self.job = Job(function, self)
        def complete(result):
            try:
                on_success(result)
            except Exception as error:
                self.error(error)
        self.job.succeeded.connect(complete)
        self.job.failed.connect(self.error)
        self.job.finished.connect(self._job_finished)
        self.update_actions()
        self.job.start()

    def _job_finished(self):
        self.job.deleteLater()
        self.job = None
        self.update_actions()
        self.statusBar().showMessage("Ready")

    def confirm_discard(self):
        return not self.document.dirty or QMessageBox.question(
            self, "Unsaved changes", "Discard unsaved changes?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        ) == QMessageBox.StandardButton.Discard

    def open_dialog(self):
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open audio", "", "Audio (*.wav *.flac *.ogg *.aiff *.aif *.mp3);;All files (*)"
        )
        if path:
            self.open_path(path)

    def import_image_dialog(self):
        if not self.confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import spectrogram image", "", "Images (*.png *.jpg *.bmp)"
        )
        if path:
            self.run_job("Importing spectrogram image", lambda: self._load_image_audio(path), self._loaded)

    @staticmethod
    def _load_image_audio(path):
        sample_rate = 44_100
        samples = image_to_audio(path, sample_rate)
        return AudioData(samples, sample_rate, "Imported Spectrogram")

    def open_path(self, path):
        self.run_job("Opening audio", lambda: AudioData.open(path), self._loaded)

    def _loaded(self, audio):
        self.noise_profile = None
        self.effects.profile_label.setText("No noise profile captured")
        self.effects.response.clear()
        self.document.load(audio)
        self.refresh()

    def save_dialog(self):
        if self.document.audio is None:
            return
        path, selected = QFileDialog.getSaveFileName(
            self, "Save processed audio", "edited.wav", "WAV (*.wav);;FLAC (*.flac)"
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".flac" if selected.startswith("FLAC") else ".wav"
            if Path(path).exists() and QMessageBox.question(
                self, "Replace file?", f"Replace {path}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
        scale = False
        if self.document.audio.peak > 1:
            scale = QMessageBox.question(
                self, "Clipping protection",
                "Scale this export to full scale? The document will stay unchanged.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes
            if not scale:
                return
        self.save_path(path, scale_to_fit=scale)

    def save_path(self, path, *, scale_to_fit=False):
        audio = self.document.audio
        if audio is None:
            return
        def saved(_):
            # Scaled export differs from the document, so retain its dirty state.
            if audio.peak <= 1:
                self.document.saved_samples = audio.samples
            self.refresh()
        self.run_job("Saving audio", lambda: audio.save(path, scale_to_fit=scale_to_fit), saved)

    def playback_range(self):
        return sample_range(self.document.audio, *self.waveform.region.getRegion())

    def play(self):
        audio = self.document.audio
        if audio is None:
            return
        self.stop_live()
        try:
            start, end = self.playback_range()
            if self.player.samples is audio.samples and start <= self.player.position < end:
                start = self.player.position
            self.player.play(audio, start, end, self.output_device.currentData())
        except Exception as error:
            self.error(f"Playback failed: {error}")
        self.update_actions()

    def toggle_playback(self):
        if self.player.active:
            self.pause()
        else:
            self.play()

    def pause(self):
        try:
            self.player.pause()
        except Exception as error:
            self.error(error)
        self.update_actions()

    def stop(self):
        try:
            self.player.stop()
        except Exception as error:
            self.error(error)
        self.update_actions()

    def _tick(self):
        audio = self.document.audio
        if audio:
            position = self.player.position / audio.sample_rate
            self.waveform.playhead.setValue(position)
            self.timecode.setText(self.format_time(position))
        self.update_actions()

    @staticmethod
    def format_time(seconds):
        milliseconds = round(seconds * 1000)
        minutes, remainder = divmod(milliseconds, 60000)
        return f"{minutes:02d}:{remainder // 1000:02d}.{remainder % 1000:03d}"

    def undo(self):
        self.stop()
        self.document.undo()
        self.refresh()

    def redo(self):
        self.stop()
        self.document.redo()
        self.refresh()

    def reset_audio(self):
        if self.job is not None or not self.document.can_reset:
            return
        self.stop()
        self.stop_live()
        self.document.reset_to_original()
        self.noise_profile = None
        self.effects.profile_label.setText("No noise profile captured")
        self.effects.response.clear()
        self.refresh()
        self.statusBar().showMessage("Original audio restored · Ctrl+Z to undo the reset")

    def refresh(self):
        audio = self.document.audio
        if audio:
            self.file_title.setText(Path(audio.filename).name or "Untitled audio")
            self.file_title.setToolTip(audio.filename)
            self.document_badge.setText("OVER FULL SCALE" if audio.peak > 1 else "UNSAVED CHANGES" if self.document.dirty else "LOCAL SESSION")
            self.document_badge.setStyleSheet("color: #ffaca6; background: #3a2425; border-color: #78484b;" if audio.peak > 1 else "")
            self.metric_values["duration"].setText(self.format_time(audio.duration))
            self.metric_values["rate"].setText(f"{audio.sample_rate / 1000:g} kHz")
            self.metric_values["channels"].setText("Stereo / 2" if audio.channels == 2 else "Mono / 1")
            peak_db = f"{20 * math.log10(audio.peak):.1f}" if audio.peak else "−∞"
            self.metric_values["peak"].setText(f"{peak_db} dBFS")
            self.metric_values["peak"].setStyleSheet("color: #ffaca6;" if audio.peak > 1 else "")
            self.channel_legend.setText("L  MINT   /   R  VIOLET" if audio.channels == 2 else "MONO  /  MINT")
            self.wave_stack.setCurrentWidget(self.waveform)
            self.start_time.setMaximum(audio.duration)
            self.end_time.setMaximum(audio.duration)
            self.metadata.setText(
                f"{audio.sample_rate} Hz | {audio.channels} channel(s) | "
                f"{len(audio.samples):,} samples | {audio.duration:.3f} s | peak {audio.peak:.4f}"
                + (" — OVER FULL SCALE: normalize before playback" if audio.peak > 1 else "")
            )
            self.waveform.set_audio(audio)
            self.effects.set_sample_rate(audio.sample_rate)
        self.setWindowTitle("SonicCraft — Audio Editor" + (" *" if self.document.dirty else ""))
        self.statusBar().showMessage("Ready" if audio else "Ready — no audio loaded")
        self.update_actions()

    def update_actions(self):
        loaded = self.document.audio is not None
        ready = self.job is None
        states = dict.fromkeys(self.actions_by_name, ready)
        for name in ("save", "play", "zoom_selection", "select_all", "trim", "delete", "reverse", "normalize", "silence"):
            states[name] = ready and loaded
        states["undo"] = ready and bool(self.document.undo_stack)
        states["redo"] = ready and bool(self.document.redo_stack)
        states["reset_audio"] = ready and self.document.can_reset
        states["stop"] = self.player.stream is not None
        for name, enabled in states.items():
            self.actions_by_name[name].setEnabled(enabled)
        playing = self.player.active
        if playing != getattr(self, "_transport_playing", None):
            self._transport_playing = playing
            action = self.actions_by_name["play"]
            action.setText("&Pause" if playing else "&Play")
            action.setIcon(icon("pause" if playing else "play", "#10271f"))
            action.setToolTip("Pause playback · Space" if playing else "Play / resume selection · Space")
            self.play_button.setAccessibleName("Pause audio" if playing else "Play audio")
        if hasattr(self, "workspace"):
            self.workspace.setEnabled(ready)
            self.sidebar.set_audio_available(ready and loaded)
            self.selection_panel.setEnabled(ready and loaded)
            self.busy_indicator.setVisible(not ready)
            self.transport_status.setText("●  PROCESSING" if not ready else "●  MONITORING" if self.microphone.stream is not None else "●  PLAYING" if self.player.active else "●  READY" if loaded else "●  IDLE")

    def closeEvent(self, event):
        if self.job is not None:
            self.statusBar().showMessage("Wait for the current operation before closing.")
            event.ignore()
            return
        if not self.confirm_discard():
            event.ignore()
            return
        self.stop_live()
        if self.live_job is not None:
            self.live_job.wait()
        self.stop()
        self.timer.stop()
        event.accept()

    def _show_about(self):
        QMessageBox.about(
            self, "About SonicCraft",
            f"SonicCraft {__version__}\nLocal Signals & Systems editor.\n"
            "PyQt6 / PyQtGraph · NumPy / SciPy / SoundFile / Sounddevice\n"
            "DSP changes real samples; no web server or external service.",
        )
