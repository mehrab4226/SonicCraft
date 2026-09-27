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
from soniccraft.desktop.audio_engine import Microphone, Player
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

    def test_live_spectrogram_follows_playback_and_pauses(self):
        driver = MagicMock()
        driver.OutputStream.return_value.active = True
        self.window.player = Player(driver)
        self.load()
        self.window.sidebar.navigate("live")
        self.window.sidebar.live_start.click()
        self.window.live_timer.stop()
        driver.OutputStream.assert_called_once()
        self.assertTrue(self.window.sidebar.live_stop.isEnabled())
        self.window.player.position = 4000
        self.window._live_tick()
        self.wait_jobs()
        self.assertIsNotNone(self.window.live_spectrogram.current_data)
        self.assertEqual(len(self.window.live_samples), 4000)
        self.assertEqual(self.window.live_spectrogram.current_data.duration, .5)
        self.assertEqual(self.window.live_spectrogram.current_data.offset, 0)
        self.assertEqual(self.window.live_spectrogram.live_playhead.value(), .5)
        self.assertEqual(self.window.live_spectrogram.plot.viewRange()[0], [0, 2])
        self.window.sidebar.live_stop.click()
        self.assertFalse(self.window.live_timer.isActive())
        self.assertEqual(self.window.player.position, 4000)
        self.window.player.position = 6000
        self.window._live_tick()
        self.assertEqual(len(self.window.live_samples), 4000)
        self.window.sidebar.live_start.click()
        self.window.live_timer.stop()
        self.assertEqual(driver.OutputStream.call_count, 2)
        self.window.player.position = 5000
        self.window._live_tick()
        self.wait_jobs()
        self.assertEqual(len(self.window.live_samples), 5000)
        self.window.sidebar.navigate("spectrum")
        self.assertIsNone(self.window.microphone.stream)
        self.assertFalse(self.window.live_timer.isActive())
        driver.OutputStream.return_value.close.assert_called()

    def test_live_start_without_audio_keeps_controls_recoverable(self):
        self.window.sidebar.navigate("live")
        self.window.sidebar.live_start.click()
        self.assertTrue(self.window.sidebar.live_start.isEnabled())
        self.assertFalse(self.window.sidebar.live_stop.isEnabled())
        self.assertIn("Load audio", self.window.sidebar.live_status.text())
        self.assertIsNone(self.window.microphone.stream)
