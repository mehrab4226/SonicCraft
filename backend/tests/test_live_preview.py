"""Preview audio, commit/history, stale jobs and fitted plots with simulated output."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
import unittest
from threading import Event
from unittest.mock import MagicMock, patch

import numpy as np
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent

from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.document import AudioData
from soniccraft.desktop.audio_engine import Player
from soniccraft.desktop.processing import process


class LivePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.window = MainWindow()
        self.errors = []
        self.window.error = self.errors.append
        t = np.arange(16000) / 8000
        self.original = AudioData(np.column_stack((.1 * np.sin(2 * np.pi * 1000 * t),
                                                   .1 * np.sin(2 * np.pi * 500 * t))), 8000)
        self.window._loaded(self.original)
        self.window.show()
        self.app.processEvents()
        driver = MagicMock()
        driver.CallbackStop = type("CallbackStop", (Exception,), {})
        driver.OutputStream.return_value.active = True
        self.window.player = Player(driver)
        self.driver = driver

    def wait_for(self, predicate):
        deadline = time.monotonic() + 10
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate(), "Background work did not finish")

    def wait_preview(self):
        self.wait_for(lambda: self.window.preview_job is None and not self.window.preview_timer.isActive())

    def tearDown(self):
        self.wait_preview()
        self.wait_for(lambda: self.window.job is None)
        self.window.document.saved_samples = self.window.document.audio.samples
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_eq_is_audible_without_apply_and_commit_does_not_double_process(self):
        w = self.window
        w.play()
        w.player._callback(np.zeros((100, 2)), 100, None, None)
        stream = w.player.stream
        w.effects.eq_bands[1000].setValue(6)
        self.wait_preview()
        expected = process(self.original, (0, 16000), "eq", w.effects.eq_parameters())
        self.assertIs(w.document.audio, self.original)
        self.assertFalse(w.document.dirty)
        self.assertEqual(w.document.undo_stack, [])
        self.assertIs(w.player.stream, stream)
        self.assertEqual(w.player.position, 100)
        out = np.zeros((160, 2))
        w.player._callback(out, 160, None, None)
        np.testing.assert_allclose(out[80:], expected[180:260])
        np.testing.assert_allclose(w.preview_audio.samples, expected)
        w.effects.eq_button.click()
        self.assertIsNone(w.preview_audio)
        np.testing.assert_allclose(w.document.audio.samples, expected)
        self.assertEqual(len(w.document.undo_stack), 1)
        self.assertIs(w.player.stream, stream)
        self.assertEqual(w.player.position, 260)
        self.assertEqual(w.effects.eq_bands[1000].value(), 0)
        w.undo()
        np.testing.assert_array_equal(w.document.audio.samples, self.original.samples)
        w.redo()
        np.testing.assert_allclose(w.document.audio.samples, expected)
        self.assertEqual(self.errors, [])

    def test_immediate_apply_uses_latest_parameters_and_retains_playback(self):
        w = self.window
        w.play()
        stream = w.player.stream
        w.effects.eq_bands[1000].setValue(-4)
        expected = process(self.original, (0, 16000), "eq", w.effects.eq_parameters())
        w.effects.eq_button.click()
        self.wait_for(lambda: w.job is None)
        self.wait_preview()
        np.testing.assert_allclose(w.document.audio.samples, expected)
        self.assertIs(w.player.stream, stream)
        self.assertEqual(len(w.document.undo_stack), 1)

    def test_filter_preview_respects_selection_channel_and_reset(self):
        w = self.window
        w.waveform.set_selection(.25, .75)
        w.target_channel_combo.setCurrentIndex(1)
        w.effects.low.setValue(300)
        self.wait_preview()
        expected = process(self.original, (2000, 6000), "filter",
                           {**w.effects.filter_parameters(), "target_channel": 0})
        np.testing.assert_allclose(w.preview_audio.samples, expected)
        self.assertEqual(w.playback_range(), (2000, 6000))
        w.target_channel_combo.setCurrentIndex(2)
        self.wait_preview()
        np.testing.assert_array_equal(w.preview_audio.samples[:, 0], self.original.samples[:, 0])
        self.assertTrue(w.reset_button.isEnabled())
        w.reset_button.click()
        self.assertIsNone(w.preview_audio)
        self.assertIs(w.waveform.audio, self.original)
        self.assertFalse(w.document.dirty)
        self.assertFalse(w.effects.has_parameter_changes)
        self.assertIsNone(w.target_channel_combo.currentData())
        self.assertEqual(w.playback_range(), (0, 16000))
        self.assertEqual(w.document.undo_stack, [])
        self.assertFalse(w.reset_button.isEnabled())

    def test_unified_reset_cancels_pending_preview_and_restores_applied_edits_undoably(self):
        w = self.window
        w.effects.eq_bands[1000].setValue(4)
        self.wait_preview()
        w.effects.eq_button.click()
        committed = w.document.audio
        w.effects.low.setValue(400)
        self.assertTrue(w.preview_timer.isActive())
        w.reset_button.click()
        self.wait_preview()
        self.assertIs(w.document.audio, self.original)
        self.assertIsNone(w.preview_request)
        self.assertIsNone(w.preview_audio)
        self.assertFalse(w.effects.has_parameter_changes)
        self.assertFalse(w.reset_button.isEnabled())
        w.undo()
        self.assertIs(w.document.audio, committed)

    def test_unified_reset_invalidates_running_preview(self):
        w = self.window
        entered, release = Event(), Event()
        def slow_process(*args):
            entered.set()
            release.wait(5)
            return process(*args)
        with patch("soniccraft.desktop.main_window.process", side_effect=slow_process):
            w.effects.eq_bands[1000].setValue(5)
            self.wait_for(entered.is_set)
            w.reset_button.click()
            release.set()
            self.wait_preview()
        self.assertIsNone(w.preview_request)
        self.assertIsNone(w.preview_audio)
        self.assertIs(w.waveform.audio, self.original)
        self.assertIs(w.player.samples, self.original.samples)
        self.assertFalse(w.effects.has_parameter_changes)
        self.assertFalse(w.document.dirty)

    def test_unified_reset_clears_profile_and_nonpreview_controls(self):
        w = self.window
        w.capture_profile()
        self.wait_for(lambda: w.job is None)
        self.assertIsNotNone(w.noise_profile)
        w.effects.gain.setValue(-6)
        w.effects.fade_duration.setValue(.5)
        w.effects.fade_curve.setCurrentIndex(1)
        w.update_actions()
        self.assertTrue(w.reset_button.isEnabled())
        w.actions_by_name["reset_audio"].trigger()
        self.assertIsNone(w.noise_profile)
        self.assertFalse(w.effects.has_parameter_changes)
        self.assertFalse(w.preview_timer.isActive())
        self.assertFalse(w.reset_button.isEnabled())

    def test_new_file_and_failed_apply_restore_the_correct_playback_buffer(self):
        w = self.window
        w.play()
        w.stop()
        replacement = AudioData(np.sin(np.arange(4000) * .2) * .1, 8000)
        w._loaded(replacement)
        w.effects.eq_bands[1000].setValue(3)
        self.wait_preview()
        self.assertEqual(w.player.samples.shape, (4000,))
        w.play()
        w.apply_operation("filter", {"kind": "bandpass", "low": 3000, "high": 1000, "order": 4})
        self.wait_for(lambda: w.job is None)
        self.assertEqual(len(self.errors), 1)
        self.assertIsNone(w.preview_audio)
        self.assertIs(w.player.samples, replacement.samples)
        self.assertIs(w.waveform.audio, replacement)
        self.assertFalse(w.document.dirty)

    def test_eq_reset_preserves_applied_audio_other_settings_selection_and_playback(self):
        w = self.window
        w._edited(self.original.samples * .5)
        committed = w.document.audio
        w.effects.gain.setValue(-3)
        w.effects.fade_duration.setValue(.5)
        w.effects.low.setValue(300)
        w.effects.eq_bands[1000].setValue(6)
        w.waveform.set_selection(.25, 1.5)
        self.wait_preview()
        w.play()
        w.player._callback(np.zeros((100, 2)), 100, None, None)
        stream, position = w.player.stream, w.player.position
        history_size = len(w.document.undo_stack)
        w.effects.reset_buttons["eq"].click()
        self.wait_preview()
        self.assertTrue(all(gain.value() == 0 for gain in w.effects.eq_bands.values()))
        self.assertTrue(all(slider.value() == 0 for slider in w.effects.eq_sliders.values()))
        self.assertEqual(w.effects.low.value(), 300)
        self.assertEqual(w.effects.gain.value(), -3)
        self.assertEqual(w.effects.fade_duration.value(), .5)
        self.assertEqual(w.playback_range(), (2000, 12000))
        self.assertIs(w.document.audio, committed)
        self.assertIs(w.player.samples, committed.samples)
        self.assertIs(w.player.stream, stream)
        self.assertEqual(w.player.position, position)
        self.assertEqual(len(w.document.undo_stack), history_size)
        self.assertIsNone(w.preview_request)

    def test_other_tool_resets_preserve_active_eq_preview(self):
        w = self.window
        w.effects.gain.setValue(5)
        w.effects.fade_duration.setValue(.5)
        w.effects.low.setValue(500)
        w.effects.noise_method.setCurrentIndex(2)
        w.effects.eq_bands[1000].setValue(4)
        self.wait_preview()
        preview, generation = w.preview_audio, w.preview_generation
        for feature in ("gain", "fades", "filter", "reduction"):
            w.effects.reset_buttons[feature].click()
            self.assertIs(w.preview_audio, preview)
            self.assertEqual(w.preview_generation, generation)
            self.assertEqual(w.effects.eq_bands[1000].value(), 4)
        self.assertEqual(w.effects.gain.value(), 0)
        self.assertEqual(w.effects.fade_duration.value(), .1)
        self.assertEqual(w.effects.low.value(), 1000)
        self.assertEqual(w.effects.noise_method.currentIndex(), 0)

    def test_noise_filter_preview_reset_has_correct_owner(self):
        w = self.window
        w.effects.low.setValue(500)
        self.wait_preview()
        preview = w.preview_audio
        w.effects.reset_buttons["reduction"].click()
        self.assertIs(w.preview_audio, preview)
        self.assertEqual(w.preview_feature, "filter")
        w.effects.noise_strength.setValue(2)
        self.wait_preview()
        self.assertEqual(w.preview_feature, "reduction")
        w.effects.reset_buttons["reduction"].click()
        self.assertIsNone(w.preview_audio)
        self.assertEqual(w.effects.low.value(), 500)
        self.assertEqual(w.effects.noise_strength.value(), 1.5)
        self.assertIs(w.document.audio, self.original)

    def test_local_reset_rejects_running_result_without_resetting_other_controls(self):
        w = self.window
        w.effects.gain.setValue(-5)
        entered, release = Event(), Event()
        def slow_process(*args):
            entered.set()
            release.wait(5)
            return process(*args)
        with patch("soniccraft.desktop.main_window.process", side_effect=slow_process):
            w.effects.eq_bands[1000].setValue(5)
            self.wait_for(entered.is_set)
            w.effects.reset_buttons["eq"].click()
            release.set()
            self.wait_preview()
        self.assertIsNone(w.preview_audio)
        self.assertIsNone(w.preview_request)
        self.assertIs(w.waveform.audio, self.original)
        self.assertEqual(w.effects.gain.value(), -5)
        self.assertEqual(w.effects.eq_bands[1000].value(), 0)

    def test_profile_reset_keeps_other_tool_settings_and_eq_preview(self):
        w = self.window
        w.capture_profile()
        self.wait_for(lambda: w.job is None)
        w.effects.noise_strength.setValue(2)
        w.effects.eq_bands[1000].setValue(3)
        self.wait_preview()
        preview = w.preview_audio
        w.effects.reset_buttons["profile"].click()
        self.assertIsNone(w.noise_profile)
        self.assertEqual(w.effects.noise_strength.value(), 2)
        self.assertEqual(w.effects.eq_bands[1000].value(), 3)
        self.assertIs(w.preview_audio, preview)

    def test_analysis_and_mixer_resets_are_local_and_main_reset_restores_all(self):
        w = self.window
        w.effects.eq_bands[1000].setValue(4)
        self.wait_preview()
        preview = w.preview_audio
        w.sidebar.fft_size.setCurrentText("4096")
        w.sidebar.window_function.setCurrentText("blackman")
        w.sidebar.live_fft_size.setCurrentText("4096")
        w.sidebar.record_live.setChecked(True)
        w.spectrum_widget.scale_combo.setCurrentIndex(1)
        w.spectrogram_widget.scale_combo.setCurrentIndex(1)
        w.live_spectrogram.scale_combo.setCurrentIndex(1)
        w.mixer._add_track(self.original)
        track = w.mixer.tracks[0]
        track["offset"].setValue(2)
        track["volume"].setValue(40)
        track["mute"].setChecked(True)
        w.sidebar.reset_buttons["spectrogram"].click()
        self.assertEqual(w.sidebar.fft_size.currentText(), "2048")
        self.assertEqual(w.sidebar.window_function.currentText(), "hann")
        self.assertEqual(w.spectrogram_widget.scale_combo.currentIndex(), 0)
        self.assertEqual(w.sidebar.live_fft_size.currentText(), "4096")
        self.assertTrue(w.sidebar.record_live.isChecked())
        self.assertTrue(w.mixer.has_parameter_changes)
        self.assertIs(w.preview_audio, preview)
        w.sidebar.reset_buttons["spectrum"].click()
        self.assertEqual(w.spectrum_widget.scale_combo.currentIndex(), 0)
        w.sidebar.reset_buttons["live"].click()
        self.assertFalse(w.sidebar.record_live.isChecked())
        self.assertEqual(w.sidebar.live_fft_size.currentText(), "1024")
        self.assertEqual(w.live_spectrogram.scale_combo.currentIndex(), 0)
        self.assertIs(w.preview_audio, preview)
        w.mixer.reset_button.click()
        self.assertFalse(w.mixer.has_parameter_changes)
        self.assertEqual(len(w.mixer.tracks), 1)
        self.assertIs(w.preview_audio, preview)
        track["volume"].setValue(30)
        w.sidebar.fft_size.setCurrentText("512")
        w.spectrogram_widget.mask_roi.setSize((.2, 300))
        w.waveform.set_selection(.25, 1)
        w.reset_button.click()
        self.wait_preview()
        self.assertFalse(w.sidebar.has_parameter_changes)
        self.assertFalse(w.spectrogram_widget.has_parameter_changes)
        self.assertFalse(w.live_spectrogram.has_parameter_changes)
        self.assertFalse(w.mixer.has_parameter_changes)
        self.assertFalse(w.effects.has_parameter_changes)
        self.assertIs(w.document.audio, self.original)
        self.assertEqual(w.playback_range(), (0, 16000))
        self.assertFalse(w.reset_button.isEnabled())

    def test_spectrogram_uses_preview_without_committing_or_discarding_it(self):
        w = self.window
        w.effects.eq_bands[1000].setValue(4)
        self.wait_preview()
        preview = w.preview_audio
        w.generate_spectrogram()
        self.wait_for(lambda: w.job is None)
        self.assertIs(w.preview_audio, preview)
        self.assertIs(w.document.audio, self.original)
        self.assertIsNotNone(w.spectrogram_widget.current_data)
        self.assertEqual(w.effects.eq_bands[1000].value(), 4)

    def test_noise_preview_and_missing_profile_do_not_modify_document(self):
        w = self.window
        w.effects.noise_method.setCurrentIndex(2)
        w.effects.wiener_window.setValue(31)
        self.wait_preview()
        expected = process(self.original, (0, 16000), "wiener", {"window_size": 31})
        np.testing.assert_allclose(w.preview_audio.samples, expected)
        w.effects.noise_method.setCurrentIndex(1)
        self.wait_preview()
        self.assertIsNone(w.preview_audio)
        self.assertIn("capture", w.statusBar().currentMessage())
        self.assertIs(w.document.audio, self.original)
        self.assertEqual(self.errors, [])
        w.effects.profile_button.click()
        self.wait_for(lambda: w.job is None)
        for index in (1, 3):
            w.effects.noise_method.setCurrentIndex(index)
            w.effects.noise_strength.setValue(2 + index / 10)
            self.wait_preview()
            self.assertIsNotNone(w.preview_audio)
            self.assertTrue(np.isfinite(w.preview_audio.samples).all())
            self.assertIs(w.document.audio, self.original)

    def test_stale_job_cannot_replace_newer_parameters_or_loaded_file(self):
        w = self.window
        entered, release = Event(), Event()
        def slow_process(*args):
            entered.set()
            release.wait(5)
            return process(*args)
        with patch("soniccraft.desktop.main_window.process", side_effect=slow_process):
            w.effects.eq_bands[1000].setValue(3)
            self.wait_for(entered.is_set)
            w.effects.eq_bands[1000].setValue(-6)
            release.set()
            self.wait_preview()
        expected = process(self.original, (0, 16000), "eq", w.effects.eq_parameters())
        np.testing.assert_allclose(w.preview_audio.samples, expected)
        entered.clear()
        release.clear()
        with patch("soniccraft.desktop.main_window.process", side_effect=slow_process):
            w.effects.eq_bands[1000].setValue(4)
            self.wait_for(entered.is_set)
            replacement = AudioData(np.zeros(1000), 8000)
            w._loaded(replacement)
            release.set()
            self.wait_preview()
        self.assertIsNone(w.preview_audio)
        self.assertIs(w.waveform.audio, replacement)

    def test_graph_wheel_gestures_do_not_change_ranges_or_units(self):
        w = self.window
        w.preview_filter("eq", w.effects.eq_parameters())
        plots = [*w.waveform.plots, w.spectrum_widget.plot_widget,
                 w.spectrogram_widget.plot, w.live_spectrogram.plot, w.effects.response]
        for plot in plots:
            item = plot.getPlotItem() if hasattr(plot, "getPlotItem") else plot
            view = item.getViewBox()
            before = view.viewRange()
            self.assertEqual(view.state["mouseEnabled"], [False, False])
            for edge in ("bottom", "left"):
                self.assertFalse(item.getAxis(edge).autoSIPrefix)
            scene_view = view.scene().views()[0]
            pos = scene_view.mapFromScene(view.sceneBoundingRect().center())
            event = QWheelEvent(QPointF(pos), QPointF(scene_view.mapToGlobal(pos)),
                                QPoint(0, 40), QPoint(0, 120), Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.ScrollUpdate, False)
            self.app.sendEvent(scene_view.viewport(), event)
            self.assertEqual(view.viewRange(), before)

    def test_waveform_dimmed_part_tracks_playhead_and_stop(self):
        w = self.window.waveform
        w.set_position(1)
        for upcoming, played in zip(w.wave_items, w.played_items):
            self.assertGreaterEqual(upcoming.xData.min(), 1)
            self.assertLessEqual(played.xData.max(), 1)
        w.set_position(0)
        for played in w.played_items:
            self.assertTrue(played.xData is None or not len(played.xData))
        self.assertEqual(w.viewRange()[0], [0, 2])


class PreviewOutputTests(unittest.TestCase):
    def test_crossfade_and_clipping_protection_do_not_change_committed_samples(self):
        driver = MagicMock()
        driver.CallbackStop = type("CallbackStop", (Exception,), {})
        player = Player(driver)
        source = AudioData(np.zeros(1000), 1000)
        preview = AudioData(np.full(1000, 2.), 1000)
        player.play(source)
        player.replace_audio(preview)
        out = np.zeros((20, 1))
        player._callback(out, 20, None, None)
        self.assertGreater(out[0, 0], 0)
        self.assertLess(out[0, 0], out[4, 0])
        self.assertLessEqual(out.max(), 1)
        np.testing.assert_array_equal(preview.samples, 2)
        player.stop()
