"""Default testing workspace blocks DSP entry points while edits stay connected."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch
import numpy as np
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QLabel
from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.document import AudioData
from soniccraft.desktop.processing import process


class LimitedWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.window = MainWindow()
        self.errors = []
        self.window.error = self.errors.append
        self.window.show()
        self.app.processEvents()

    def wait_job(self):
        deadline = time.monotonic() + 15
        while self.window.job is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertIsNone(self.window.job)
        self.assertEqual(self.errors, [])

    def tearDown(self):
        self.wait_job()
        if self.window.document.audio:
            self.window.document.saved_samples = self.window.document.audio.samples
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def load(self):
        samples = .3 * np.sin(2 * np.pi * 440 * np.arange(8000) / 8000)
        self.window._loaded(AudioData(samples, 8000, "test.wav"))

    def test_placeholders_cannot_dispatch_dsp_or_open_microphone(self):
        w = self.window
        with ExitStack() as stack:
            blocked = [stack.enter_context(patch(f"soniccraft.desktop.main_window.{name}"))
                       for name in ("fft_spectrum", "make_spectrogram", "frequency_response", "estimate_noise_profile", "process")]
            blocked.append(stack.enter_context(patch.object(w, "run_job")))
            blocked.append(stack.enter_context(patch.object(w.microphone, "start")))
            # Loading and selection changes used to trigger FFT automatically.
            self.load()
            original = w.document.audio.samples.copy()
            w.waveform.set_selection(.1, .8)
            w.refresh()
            for category in ("noise", "spectrum", "spectrogram", "live"):
                control = w.sidebar.category_buttons[category]
                self.assertFalse(control.isEnabled())
                control.click()
                w.sidebar.navigate(category)
                self.assertEqual(w.sidebar.current_route, "home")
            for name in ("noise_panel", "spectrum", "spectrogram", "live_spectrogram"):
                self.assertFalse(w.actions_by_name[name].isEnabled())
                w.actions_by_name[name].trigger()
            for index in range(4):
                w.analysis_tabs.setCurrentIndex(index)
                page = w.analysis_tabs.widget(index)
                self.assertIsInstance(page, QLabel)
                self.assertIn("Placeholder", page.text())
            for control in (w.effects.profile_button, w.effects.noise_button,
                            w.sidebar.render_button, w.sidebar.live_start,
                            *w.effects.response_buttons):
                self.assertFalse(control.isEnabled())
                control.click()
            # Even emitted signals or direct controller entry cannot bypass it.
            w.effects.profile_requested.emit()
            w.effects.preview_requested.emit("filter", {})
            w.effects.noise_requested.emit("filter", {})
            for method in (w.update_spectrum, w.generate_spectrogram, w.start_live,
                           w._live_tick, w.capture_profile):
                method()
            w.preview_filter("filter", {})
            for operation in ("subtraction", "wiener", "gate"):
                w.apply_operation(operation, {})
            self.app.processEvents()
            for mock in blocked:
                mock.assert_not_called()
            np.testing.assert_array_equal(w.document.audio.samples, original)
            self.assertFalse(w.document.undo_stack)
            self.assertIsNone(w.noise_profile)
            self.assertIsNone(w.spectrum_widget.current_spectrum)
            self.assertFalse(w.live_timer.isActive())

    def test_edit_filter_and_eq_still_process_audio_and_reset(self):
        self.load()
        w = self.window
        original = w.document.audio.samples.copy()
        for category in ("edit", "filters"):
            w.sidebar.category_buttons[category].click()
            self.assertEqual(w.sidebar.current_route, category)
            w.sidebar.back_button.click()
        w.sidebar.navigate("gain")
        w.effects.gain.setValue(-6)
        w.effects.gain_button.click()
        self.wait_job()
        np.testing.assert_allclose(w.document.audio.samples, original * 10 ** (-6 / 20))
        w.sidebar.navigate("filter")
        expected = process(w.document.audio, (0, 8000), "filter", w.effects.filter_parameters())
        w.effects.filter_button.click()
        self.wait_job()
        np.testing.assert_allclose(w.document.audio.samples, expected)
        w.sidebar.navigate("eq")
        w.effects.eq_bands[1000].setValue(6)
        expected = process(w.document.audio, (0, 8000), "eq", w.effects.eq_parameters())
        w.effects.eq_button.click()
        self.wait_job()
        np.testing.assert_allclose(w.document.audio.samples, expected)
        self.assertIsNone(w.spectrum_widget.current_spectrum)
        w.actions_by_name["reset_audio"].trigger()
        np.testing.assert_array_equal(w.document.audio.samples, original)
        w.actions_by_name["undo"].trigger()
        np.testing.assert_allclose(w.document.audio.samples, expected)
        self.assertFalse(w.actions_by_name["spectrum"].isEnabled())
