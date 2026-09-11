"""Desktop integration uses real Qt, files and DSP; audio hardware is injected."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import soundfile as sf
from PyQt6.QtCore import QCoreApplication, QEvent

from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.document import AudioData, Document
from soniccraft.desktop.audio_engine import Player


class DocumentTests(unittest.TestCase):
    def test_mono_stereo_save_reload_and_clipping_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            for channels in (1, 2):
                x = np.linspace(-0.8, 0.8, 800)
                if channels == 2:
                    x = np.column_stack([x, -x])
                audio = AudioData(x, 8000)
                for ext in ("wav", "flac"):
                    path = Path(folder) / f"audio{channels}.{ext}"
                    audio.save(path)
                    actual = AudioData.open(path)
                    self.assertEqual(actual.channels, channels)
                    self.assertEqual(actual.sample_rate, 8000)
                    np.testing.assert_allclose(actual.samples, x, atol=2e-7)
            audio = AudioData(np.ones(20) * 2, 8000)
            path = Path(folder) / "clipped.wav"
            with self.assertRaises(ValueError):
                audio.save(path)
            self.assertFalse(path.exists())
            audio.save(path, scale_to_fit=True)
            self.assertLessEqual(AudioData.open(path).peak, 1)
            self.assertEqual(audio.peak, 2)

    def test_history_and_invalid_audio(self):
        doc = Document()
        doc.load(AudioData(np.arange(10) / 10, 8000))
        self.assertFalse(doc.dirty)
        doc.commit(doc.audio.samples[::-1])
        self.assertTrue(doc.dirty)
        doc.undo()
        self.assertFalse(doc.dirty)
        doc.redo()
        self.assertTrue(doc.dirty)
        with self.assertRaises(ValueError):
            AudioData(np.zeros((10, 3)), 8000)
        with self.assertRaises(ValueError):
            AudioData(np.array([np.nan]), 8000)

    def test_atomic_failed_save_preserves_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audio.wav"
            AudioData(np.zeros(50), 8000).save(path)
            before = path.read_bytes()
            with patch("soniccraft.desktop.document.save_audio", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    AudioData(np.ones(50), 8000).save(path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)


class PlayerTests(unittest.TestCase):
    def test_callback_pause_stop_and_eof(self):
        driver = MagicMock()
        driver.CallbackStop = type("CallbackStop", (Exception,), {})
        driver.OutputStream.return_value.active = True
        player = Player(driver)
        audio = AudioData(np.arange(10) / 10, 8000)
        player.play(audio, 2, 8)
        out = np.zeros((4, 1))
        player._callback(out, 4, None, None)
        np.testing.assert_allclose(out[:, 0], audio.samples[2:6])
        player.pause()
        self.assertEqual(player.position, 6)
        driver.OutputStream.return_value.close.assert_called()
        player.play(audio, 6, 8)
        with self.assertRaises(driver.CallbackStop):
            player._callback(out, 4, None, None)
        np.testing.assert_allclose(out[:, 0], [0.6, 0.7, 0, 0])
        player.stop()
        self.assertEqual(player.position, 0)

    def test_failed_start_closes_stream(self):
        driver = MagicMock()
        driver.OutputStream.return_value.start.side_effect = RuntimeError("missing device")
        player = Player(driver)
        with self.assertRaises(RuntimeError):
            player.play(AudioData(np.zeros(10), 8000))
        self.assertIsNone(player.stream)
        driver.OutputStream.return_value.close.assert_called_once()


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        self.folder = tempfile.TemporaryDirectory()
        self.errors = []
        self.window.error = self.errors.append

    def wait_job(self):
        deadline = time.monotonic() + 15
        while self.window.job is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertIsNone(self.window.job, "background operation did not finish")

    def tearDown(self):
        self.wait_job()
        self.window.document.saved_samples = (
            self.window.document.audio.samples if self.window.document.audio else None
        )
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.folder.cleanup()

    def test_open_metadata_transport_and_save_actions(self):
        source = Path(self.folder.name) / "stereo.wav"
        x = np.column_stack([np.sin(np.arange(800) * 0.2) * 0.5, np.zeros(800)])
        sf.write(source, x, 8000, subtype="FLOAT")
        with patch("soniccraft.desktop.main_window.QFileDialog.getOpenFileName", return_value=(str(source), "")):
            self.window.actions_by_name["open"].trigger()
        self.wait_job()
        self.assertEqual(self.errors, [])
        self.assertIn("8000 Hz", self.window.metadata.text())
        self.assertIn("2 channel", self.window.metadata.text())
        self.assertTrue(self.window.actions_by_name["play"].isEnabled())
        with patch.object(self.window.player, "play") as play:
            self.window.actions_by_name["play"].trigger()
            self.assertIs(play.call_args.args[0], self.window.document.audio)
        target = Path(self.folder.name) / "saved.flac"
        with patch("soniccraft.desktop.main_window.QFileDialog.getSaveFileName", return_value=(str(target), "FLAC (*.flac)")):
            self.window.actions_by_name["save"].trigger()
        self.wait_job()
        np.testing.assert_allclose(AudioData.open(target).samples, x, atol=2e-7)
        self.assertEqual(self.errors, [])

    def test_invalid_open_preserves_current_document(self):
        original = AudioData(np.zeros(100), 8000)
        self.window._loaded(original)
        self.window.open_path(Path(self.folder.name) / "missing.wav")
        self.wait_job()
        self.assertIs(self.window.document.audio, original)
        self.assertEqual(len(self.errors), 1)

    def test_selection_edit_buttons_history_and_export(self):
        x = np.linspace(-0.5, 0.5, 100)
        self.window._loaded(AudioData(x, 100))
        self.window.waveform.set_selection(0.2, 0.6)
        self.assertEqual(self.window.playback_range(), (20, 60))
        self.window.effects.edit_buttons["reverse"].click()
        self.wait_job()
        expected = x.copy()
        expected[20:60] = x[20:60][::-1]
        np.testing.assert_allclose(self.window.document.audio.samples, expected)
        self.window.actions_by_name["undo"].trigger()
        np.testing.assert_allclose(self.window.document.audio.samples, x)
        self.window.actions_by_name["redo"].trigger()
        np.testing.assert_allclose(self.window.document.audio.samples, expected)
        self.window.effects.gain.setValue(-6)
        self.window.effects.gain_button.click()
        self.wait_job()
        np.testing.assert_allclose(self.window.document.audio.samples, expected * 10 ** (-6 / 20))
        self.assertEqual(self.errors, [])

    def test_filter_eq_profile_and_noise_ui(self):
        t = np.arange(8000) / 8000
        self.window._loaded(AudioData(np.sin(2*np.pi*440*t)*0.3, 8000))
        self.assertFalse(self.window.effects.eq_bands[8000].isEnabled())
        self.window.effects.filter_button.click()
        self.wait_job()
        self.window.preview_filter("filter", self.window.effects.filter_parameters())
        self.wait_job()
        self.assertEqual(len(self.window.effects.response.listDataItems()), 1)
        self.window.effects.eq_bands[1000].setValue(3)
        self.window.effects.eq_button.click()
        self.wait_job()
        self.window.waveform.set_selection(0, 0.2)
        self.window.effects.profile_button.click()
        self.wait_job()
        self.assertIsNotNone(self.window.noise_profile)
        self.window.waveform.set_selection(0, 1)
        for index in (1, 2, 3):
            self.window.effects.noise_method.setCurrentIndex(index)
            self.window.effects.noise_button.click()
            self.wait_job()
        self.assertEqual(self.errors, [])
