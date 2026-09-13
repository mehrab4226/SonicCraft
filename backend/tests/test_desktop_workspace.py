"""Workspace interaction regressions with real Qt widgets and no audio device."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
from PyQt6.QtCore import QCoreApplication, QEvent, QMimeData, QPoint, QPointF, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFontDatabase
from PyQt6.QtTest import QTest

from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.document import AudioData
from soniccraft.desktop.audio_engine import Player


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])
        # Qt's Windows offscreen plugin does not discover installed fonts.
        # Register the same fonts used by the native platform for geometry tests.
        if not QFontDatabase.families():
            for filename in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
                path = Path("C:/Windows/Fonts") / filename
                if path.exists():
                    QFontDatabase.addApplicationFont(str(path))

    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        if self.window.document.audio:
            self.window.document.saved_samples = self.window.document.audio.samples
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def load_audio(self, rate=8000):
        self.window._loaded(AudioData(np.sin(np.arange(rate) * 0.2) * 0.5, rate, "test.wav"))
        self.app.processEvents()

    def test_selection_validation_focus_and_select_all(self):
        self.load_audio()
        self.window.waveform.set_selection(0.1, 0.8)
        self.window.start_time.setValue(0.9)
        self.window.end_time.setValue(0.2)
        with patch.object(self.window, "error") as error:
            self.window.set_selection_from_inputs()
            error.assert_called_once()
        self.assertEqual(self.window.waveform.region.getRegion(), (0.1, 0.8))
        self.window.start_time.setValue(0.2)
        self.window.end_time.setValue(0.6)
        self.window.set_selection_from_inputs()
        self.window.actions_by_name["zoom_selection"].trigger()
        low, high = self.window.waveform.viewRange()[0]
        self.assertLessEqual(low, 0.2)
        self.assertGreaterEqual(high, 0.6)
        self.assertLess(high - low, 0.5)
        self.window.actions_by_name["select_all"].trigger()
        self.assertEqual(self.window.playback_range(), (0, 8000))

    def test_drop_respects_unsaved_changes_and_rejects_non_audio(self):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile("D:/recording.wav")])
        drag = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.window.dragEnterEvent(drag)
        self.assertTrue(drag.isAccepted())
        drop = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        with patch.object(self.window, "confirm_discard", return_value=False), patch.object(self.window, "open_path") as opened:
            self.window.dropEvent(drop)
            opened.assert_not_called()
        with patch.object(self.window, "confirm_discard", return_value=True), patch.object(self.window, "open_path") as opened:
            self.window.dropEvent(drop)
            self.assertTrue(drop.isAccepted())
            opened.assert_called_once_with("D:/recording.wav")
        mime.setUrls([QUrl.fromLocalFile("D:/notes.txt")])
        drag = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.window.dragEnterEvent(drag)
        self.assertFalse(drag.isAccepted())

    def test_eq_faders_parameters_and_nyquist(self):
        self.load_audio()
        effects = self.window.effects
        effects.eq_sliders[1000].setValue(45)
        self.assertEqual(effects.eq_bands[1000].value(), 4.5)
        self.assertIn((1000, 4.5), effects.eq_parameters()["bands"])
        self.assertFalse(effects.eq_sliders[8000].isEnabled())
        self.assertNotIn(8000, dict(effects.eq_parameters()["bands"]))
        effects.eq_bands[1000].setValue(-2.3)
        self.assertEqual(effects.eq_sliders[1000].value(), -23)
        effects.reset_eq()
        self.assertTrue(all(gain.value() == 0 for gain in effects.eq_bands.values()))
        effects.filter_kind.setCurrentIndex(2)
        self.assertTrue(effects.high.isEnabled())
        self.assertEqual(effects.filter_parameters()["kind"], "bandpass")
        effects.filter_kind.setCurrentIndex(0)
        self.assertFalse(effects.high.isEnabled())

    def test_space_shortcut_and_spectrum_toggle(self):
        self.load_audio()
        self.window.activateWindow()
        self.window.waveform.setFocus()
        self.app.processEvents()
        with patch.object(self.window, "play") as play:
            QTest.keyClick(self.window.waveform, Qt.Key.Key_Space)
            play.assert_called_once()
        with patch.object(type(self.window.player), "active", new_callable=unittest.mock.PropertyMock, return_value=True), patch.object(self.window, "pause") as pause:
            QTest.keyClick(self.window.waveform, Qt.Key.Key_Space)
            pause.assert_called_once()
        action = self.window.actions_by_name["spectrum"]
        action.trigger()
        self.assertTrue(action.isChecked())
        self.assertIsNotNone(self.window.spectrum_widget.current_spectrum)
        self.window.show_analysis("spectrogram")
        self.assertFalse(action.isChecked())

    def test_empty_loaded_and_compact_workspace(self):
        self.assertIs(self.window.wave_stack.currentWidget(), self.window.empty_state)
        self.assertFalse(self.window.selection_panel.isEnabled())
        self.load_audio()
        self.assertIs(self.window.wave_stack.currentWidget(), self.window.waveform)
        self.assertEqual(self.window.metric_values["rate"].text(), "8 kHz")
        self.window.resize(1000, 760)
        self.app.processEvents()
        self.assertFalse(self.window.metrics_panel.isVisible())
        self.assertTrue(self.window.waveform.isVisible())
        self.assertLessEqual(self.window.wave_stack.geometry().bottom(), self.window.selection_panel.y())
        for name in ("play", "stop", "open", "save"):
            self.assertTrue(self.window.transport_toolbar.widgetForAction(self.window.actions_by_name[name]).isVisible())
        self.window.resize(1380, 960)
        self.app.processEvents()
        self.assertTrue(self.window.metrics_panel.isVisible())

    def test_single_transport_button_pauses_resumes_and_resets_at_eof(self):
        self.load_audio()
        driver = MagicMock()
        driver.CallbackStop = type("CallbackStop", (Exception,), {})
        streams = []
        def make_stream(**kwargs):
            stream = MagicMock()
            stream.active = False
            stream.start.side_effect = lambda: setattr(stream, "active", True)
            stream.abort.side_effect = lambda: setattr(stream, "active", False)
            streams.append(stream)
            return stream
        driver.OutputStream.side_effect = make_stream
        self.window.player = Player(driver)
        self.window.waveform.set_selection(.1, .8)
        control = self.window.play_button
        self.assertNotIn("pause", [action.objectName() for action in self.window.transport_toolbar.actions()])
        self.assertEqual(control.text(), "Play")
        control.click()
        self.assertTrue(self.window.player.active)
        self.assertEqual(control.text(), "Pause")
        self.window.player._callback(np.zeros((160, 1)), 160, None, None)
        position = self.window.player.position
        control.click()
        self.assertFalse(self.window.player.active)
        self.assertEqual(control.text(), "Play")
        self.assertEqual(self.window.player.position, position)
        control.click()
        self.assertEqual(control.text(), "Pause")
        self.assertEqual(self.window.player.position, position)
        with self.assertRaises(driver.CallbackStop):
            self.window.player._callback(np.zeros((8000, 1)), 8000, None, None)
        streams[-1].active = False  # PortAudio marks the stream inactive at EOF.
        self.window._tick()
        self.assertEqual(control.text(), "Play")
        control.click()
        self.assertEqual(self.window.player.position, 800)
        self.window.actions_by_name["stop"].trigger()
        self.assertEqual(control.text(), "Play")
        self.assertEqual(self.window.player.position, 0)

    def test_transport_failure_keeps_play_available(self):
        self.load_audio()
        driver = MagicMock()
        driver.OutputStream.side_effect = RuntimeError("Output unavailable")
        self.window.player = Player(driver)
        with patch.object(self.window, "error") as error:
            self.window.play_button.click()
            error.assert_called_once()
        self.assertEqual(self.window.play_button.text(), "Play")
        self.assertTrue(self.window.play_button.isEnabled())
        self.assertIsNone(self.window.player.stream)

    def test_reset_audio_is_available_after_edits_and_undoable(self):
        self.load_audio()
        original = self.window.document.audio
        self.assertFalse(self.window.reset_button.isEnabled())
        self.window._edited(original.samples[:4000] * .5)
        edited = self.window.document.audio
        self.window.waveform.set_selection(.1, .4)
        self.assertTrue(self.window.reset_button.isEnabled())
        self.window.reset_button.click()
        self.assertIs(self.window.document.audio, original)
        self.assertEqual(self.window.playback_range(), (0, 8000))
        self.assertFalse(self.window.document.dirty)
        self.assertFalse(self.window.reset_button.isEnabled())
        self.window.actions_by_name["undo"].trigger()
        self.assertIs(self.window.document.audio, edited)
        self.assertTrue(self.window.reset_button.isEnabled())
        self.window.actions_by_name["redo"].trigger()
        self.assertIs(self.window.document.audio, original)
