"""Desktop controller: one document shared by views, DSP jobs and local streams."""
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QMessageBox, QToolBar, QVBoxLayout, QWidget,
    QFileDialog, QLabel, QComboBox, QHBoxLayout, QDockWidget
)
import sounddevice as sd

from soniccraft import __version__
from .document import AudioData, Document
from .audio_engine import Player
from .jobs import Job
from .waveform_widget import WaveformWidget
from .effects_panel import EffectsPanel, number, button
from .processing import process, sample_range, filter_sections, check_transform_size
from soniccraft.dsp.filters import frequency_response
from soniccraft.dsp.noise_reduction import estimate_noise_profile
from .waveform_widget import WaveformWidget
from .spectrum_widget import SpectrumWidget
from soniccraft.dsp.transforms import fft_spectrum

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("soniccraftMainWindow")
        self.setWindowTitle("SonicCraft — Audio Editor")
        self.resize(1180, 850)
        self.setMinimumSize(800, 600)
        self.document = Document()
        self.player = Player()
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
        self.refresh_devices()
        self.refresh()

    def _action(self, name, text, callback, shortcut=None):
        action = QAction(text, self)
        action.setObjectName(name)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        self.actions_by_name[name] = action
        return action

    def _build_actions(self):
        self._action("open", "&Open audio…", self.open_dialog, QKeySequence.StandardKey.Open)
        self._action("save", "&Save audio as…", self.save_dialog, QKeySequence.StandardKey.Save)
        self._action("play", "&Play", self.play, "Space")
        self._action("pause", "P&ause", self.pause)
        self._action("stop", "S&top", self.stop)
        self._action("undo", "&Undo", self.undo, QKeySequence.StandardKey.Undo)
        self._action("redo", "&Redo", self.redo, QKeySequence.StandardKey.Redo)
        self._action("exit", "E&xit", self.close, QKeySequence.StandardKey.Quit)
        self._action("reset_view", "&Reset waveform view", lambda: self.waveform.reset_view())
        self._action("about", "&About SonicCraft", self._show_about)
        self._action("devices", "Refresh audio devices", self.refresh_devices)
        self._action("spectrum", "FFT Spectrum Analyzer", self.toggle_spectrum)
        for name, index in (("volume_panel", 0), ("eq_panel", 1), ("noise_panel", 2)):
            self._action(name, name.replace("_panel", "").title() + " controls", lambda checked=False, i=index: self.effects.setCurrentIndex(i))
        for name in ("trim", "delete", "reverse", "normalize", "silence"):
            self._action(name, name.title(), lambda checked=False, n=name: self.apply_operation(n, {}))

    def _build_menus(self):
        self.menus = {}
        for title, names in (
            ("&File", ("open", "save", "exit")),
            ("&Edit", ("undo", "redo", "trim", "delete", "reverse", "silence")),
            ("&Effects", ("normalize", "volume_panel", "eq_panel", "noise_panel")), ("&Analysis", ("spectrum",)),
            ("&View", ("reset_view", "devices")), ("&Help", ("about",)),
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
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        for name in ("open", "save", "undo", "redo", "play", "pause", "stop"):
            toolbar.addAction(self.actions_by_name[name])
        self.addToolBar(toolbar)
        self.view_menu.addAction(toolbar.toggleViewAction())
        self.transport_toolbar = toolbar

    def _build_workspace(self):
        self.workspace = QWidget(self)
        self.layout = QVBoxLayout(self.workspace)
        self.metadata = QLabel("Open a local audio file to begin.")
        self.metadata.setWordWrap(True)
        self.layout.addWidget(self.metadata)
        devices = QHBoxLayout()
        devices.addWidget(QLabel("Output device"))
        self.output_device = QComboBox()
        devices.addWidget(self.output_device, 1)
        self.layout.addLayout(devices)
        self.waveform = WaveformWidget(self)
        self.layout.addWidget(self.waveform, 2)
        self.selection_status = QLabel("Time: 0.000 s")
        self.layout.addWidget(self.selection_status)
        selection = QHBoxLayout()
        selection.addWidget(QLabel("Selection start / end (s)"))
        self.start_time = number(0, 0, 36000, 6)
        self.end_time = number(1, 0, 36000, 6)
        selection.addWidget(self.start_time)
        selection.addWidget(self.end_time)
        button(selection, "Set selection", lambda: self.waveform.set_selection(self.start_time.value(), self.end_time.value()))
        button(selection, "Select all", lambda: self.waveform.set_selection(0, self.document.audio.duration) if self.document.audio else None)
        self.layout.addLayout(selection)
        self.waveform.selection_changed.connect(self._selection_changed)
        self.effects = EffectsPanel()
        self.effects.requested.connect(self.apply_operation)
        self.effects.preview_requested.connect(self.preview_filter)
        self.effects.profile_requested.connect(self.capture_profile)
        self.layout.addWidget(self.effects, 1)
        self.setCentralWidget(self.workspace)

        # --- ADD THESE LINES ---
        self.spectrum_dock = QDockWidget("FFT Spectrum Analyzer", self)
        self.spectrum_dock.setObjectName("spectrumDock")
        self.spectrum_widget = SpectrumWidget(self.spectrum_dock)
        self.spectrum_dock.setWidget(self.spectrum_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.spectrum_dock)
        self.spectrum_dock.hide() # Hidden by default

    def _selection_changed(self, start, end):
        self.start_time.setValue(start)
        self.end_time.setValue(end)
        self.update_spectrum() # <-- Added this line
    # --- ADD THESE TWO NEW METHODS ---
    def toggle_spectrum(self):
        """Shows or hides the analyzer panel."""
        if self.spectrum_dock.isHidden():
            self.spectrum_dock.show()
            self.update_spectrum()
        else:
            self.spectrum_dock.hide()

    def update_spectrum(self):
        """Runs the FFT math and pushes data to the UI widget."""
        if self.document.audio is None or self.spectrum_dock.isHidden():
            return
            
        try:
            start, end = self.playback_range()
            if start >= end:
                return
                
            # Limit the analysis to a chunk of samples so the GUI never freezes.
            # 65536 samples gives ultra-high resolution without lagging the drag-selection.
            samples = self.document.audio.samples[start:end]
            if len(samples) > 65536:
                samples = samples[:65536]
                
            # Run the FFT!
            spectrum = fft_spectrum(samples, self.document.audio.sample_rate)
            self.spectrum_widget.set_spectrum(spectrum)
            
        except Exception as error:
            print(f"Spectrum Analysis Error: {error}")

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
            self.effects.response.plot(response.frequencies, response.magnitude_db, pen="#64d6cd")
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
        self.output_device.clear()
        self.output_device.addItem("System default", None)
        try:
            for index, device in enumerate(sd.query_devices()):
                if device["max_output_channels"] > 0:
                    self.output_device.addItem(device["name"], index)
            match = self.output_device.findData(selected)
            self.output_device.setCurrentIndex(max(0, match))
        except Exception as error:
            self.statusBar().showMessage(f"Audio device discovery failed: {error}")

    def error(self, message):
        QMessageBox.warning(self, "SonicCraft", str(message))

    def run_job(self, title, function, on_success):
        if self.job is not None:
            return
        self.stop()
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
        try:
            start, end = self.playback_range()
            if self.player.samples is audio.samples and start <= self.player.position < end:
                start = self.player.position
            self.player.play(audio, start, end, self.output_device.currentData())
        except Exception as error:
            self.error(f"Playback failed: {error}")
        self.update_actions()

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

    def _tick(self):
        audio = self.document.audio
        if audio:
            position = self.player.position / audio.sample_rate
            self.waveform.playhead.setValue(position)
            self.selection_status.setText(
                f"Time: {position:.3f} s | Selection: {self.start_time.value():.6f}–{self.end_time.value():.6f} s"
            )
        self.update_actions()

    def undo(self):
        self.stop()
        self.document.undo()
        self.refresh()

    def redo(self):
        self.stop()
        self.document.redo()
        self.refresh()

    def refresh(self):
        audio = self.document.audio
        if audio:
            self.start_time.setMaximum(audio.duration)
            self.end_time.setMaximum(audio.duration)
            self.metadata.setText(
                f"{Path(audio.filename).name} | {audio.sample_rate} Hz | {audio.channels} channel(s) | "
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
        for name, action in self.actions_by_name.items():
            action.setEnabled(ready)
        for name in ("save", "play"):
            self.actions_by_name[name].setEnabled(ready and loaded)
        for name in ("trim", "delete", "reverse", "normalize", "silence"):
            self.actions_by_name[name].setEnabled(ready and loaded)
        self.actions_by_name["undo"].setEnabled(ready and bool(self.document.undo_stack))
        self.actions_by_name["redo"].setEnabled(ready and bool(self.document.redo_stack))
        self.actions_by_name["pause"].setEnabled(self.player.active)
        self.actions_by_name["stop"].setEnabled(self.player.stream is not None)
        if hasattr(self, "workspace"):
            self.workspace.setEnabled(ready)
            self.effects.setEnabled(ready and loaded)

    def closeEvent(self, event):
        if self.job is not None:
            self.statusBar().showMessage("Wait for the current operation before closing.")
            event.ignore()
            return
        if not self.confirm_discard():
            event.ignore()
            return
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
