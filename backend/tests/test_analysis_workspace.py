"""Drill-down navigation, bounded STFT display and microphone lifecycle."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
import unittest
from unittest.mock import MagicMock
import numpy as np
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QDockWidget
from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.audio_engine import Microphone
from soniccraft.desktop.document import AudioData
from soniccraft.desktop.analysis import make_spectrogram


class DisplayTransformTests(unittest.TestCase):
    def test_tone_frequency_and_calibrated_level(self):
        rate = 8192
        samples = .5 * np.sin(2 * np.pi * 512 * np.arange(rate) / rate)
        result = make_spectrogram(samples, rate, 1024, offset=2.5)
        peak_bin = np.argmax(result.values[:, 4])
        self.assertEqual(peak_bin * rate / result.n_fft, 512)
        self.assertAlmostEqual(float(result.values[peak_bin, 4]), -6.0206, places=3)
        self.assertEqual(result.offset, 2.5)
        self.assertEqual(result.duration, 1)

    def test_silence_short_audio_stereo_and_bounded_time_axis(self):
        silence = make_spectrogram(np.zeros(1), 8000)
        self.assertTrue(np.all(silence.values == -120))
        x = np.linspace(-.2, .2, 400000)
        mono = make_spectrogram(x, 8000, max_frames=100)
        stereo = make_spectrogram(np.column_stack((x, x)), 8000, max_frames=100)
        np.testing.assert_allclose(mono.values, stereo.values)
        self.assertLessEqual(mono.values.shape[1], 100)
        self.assertEqual(mono.duration, 50)
        self.assertGreater((mono.values.shape[1] - 1) * mono.hop / 8000, 49)


class AnalysisWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        self.app.processEvents()
        self.errors = []
        self.window.error = self.errors.append

    def wait_jobs(self):
        deadline = time.monotonic() + 15
        while (self.window.job is not None or self.window.live_job is not None) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertIsNone(self.window.job)
        self.assertIsNone(self.window.live_job)

    def tearDown(self):
        self.window.stop_live()
        self.wait_jobs()
        if self.window.document.audio:
            self.window.document.saved_samples = self.window.document.audio.samples
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def load(self):
        samples = np.sin(2 * np.pi * 440 * np.arange(16000) / 8000) * .4
        self.window._loaded(AudioData(samples, 8000, "tone.wav"))
        self.app.processEvents()

    def test_categories_nested_controls_back_and_no_bottom_effects_dock(self):
        sidebar = self.window.sidebar
        self.assertEqual(len(sidebar.category_buttons), 6)
        self.assertEqual(sidebar.current_route, "home")
        self.assertFalse(sidebar.back_button.isVisible())
        sidebar.category_buttons["edit"].click()
        self.assertEqual(sidebar.current_route, "edit")
        self.assertTrue(self.window.effects.edit_buttons["trim"].isVisible())
        self.assertFalse(self.window.effects.edit_buttons["trim"].isEnabled())
        sidebar.feature_buttons["gain"].click()
        self.assertEqual(sidebar.current_route, "gain")
        self.assertTrue(self.window.effects.gain.isVisible())
        sidebar.back_button.click()
        self.assertEqual(sidebar.current_route, "edit")
        sidebar.back_button.click()
        self.assertEqual(sidebar.current_route, "home")
        self.assertEqual(self.window.findChildren(QDockWidget), [])
        self.assertIs(self.window.splitter.widget(1), self.window.analysis_panel)
        self.load()
        sidebar.navigate("gain")
        self.window.effects.gain.setValue(-6)
        before = self.window.document.audio.samples.copy()
        self.window.effects.gain_button.click()
        self.wait_jobs()
        np.testing.assert_allclose(self.window.document.audio.samples, before * 10 ** (-6 / 20))

    def test_file_spectrogram_selection_and_stale_result(self):
        self.load()
        self.window.waveform.set_selection(.25, 1.5)
        self.window.sidebar.category_buttons["spectrogram"].click()
        self.window.sidebar.render_button.click()
        self.wait_jobs()
        data = self.window.spectrogram_widget.current_data
        self.assertIsNotNone(data)
        self.assertEqual(data.offset, .25)
        self.assertEqual(data.duration, 1.25)
        self.assertEqual(self.window.analysis_tabs.currentIndex(), 1)
        self.window.waveform.set_selection(.5, 1)
        self.assertIsNone(self.window.spectrogram_widget.current_data)
        self.assertEqual(self.errors, [])

    def test_live_start_worker_stop_and_navigation_without_audio_document(self):
        driver = MagicMock()
        driver.query_devices.return_value = {"default_samplerate": 8000}
        driver.InputStream.return_value.active = True
        self.window.microphone = Microphone(driver)
        self.window.sidebar.navigate("live")
        driver.InputStream.assert_not_called()
        self.window.sidebar.live_start.click()
        self.window.live_timer.stop()
        driver.InputStream.assert_called_once()
        self.assertIsNone(self.window.document.audio)
        self.assertTrue(self.window.sidebar.live_stop.isEnabled())
        block = .4 * np.sin(2 * np.pi * 500 * np.arange(80000) / 8000)
        self.window.microphone._callback(block[:, None], len(block), None, None)
        self.window._live_tick()
        self.wait_jobs()
        self.assertIsNotNone(self.window.live_spectrogram.current_data)
        self.assertEqual(len(self.window.live_samples), 64000)
        self.assertEqual(self.window.live_spectrogram.current_data.duration, 8)
        self.assertEqual(self.window.live_spectrogram.current_data.offset, 2)
        self.window.sidebar.navigate("spectrum")
        self.assertIsNone(self.window.microphone.stream)
        self.assertFalse(self.window.live_timer.isActive())
        driver.InputStream.return_value.close.assert_called()

    def test_failed_microphone_start_keeps_controls_recoverable(self):
        driver = MagicMock()
        driver.query_devices.side_effect = RuntimeError("No input device")
        self.window.microphone = Microphone(driver)
        self.window.sidebar.navigate("live")
        self.window.sidebar.live_start.click()
        self.assertTrue(self.window.sidebar.live_start.isEnabled())
        self.assertFalse(self.window.sidebar.live_stop.isEnabled())
        self.assertIn("No input device", self.window.sidebar.live_status.text())
        self.assertIsNone(self.window.microphone.stream)
