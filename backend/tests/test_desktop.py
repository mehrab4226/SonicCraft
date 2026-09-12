"""Qt foundation tests; no audio device or web server is required."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


if importlib.util.find_spec("PyQt6") is None or importlib.util.find_spec("pyqtgraph") is None:
    raise unittest.SkipTest("Install the desktop extra to run Qt foundation tests.")

# Real Qt widgets on the offscreen platform keep automated tests non-interactive.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QMessageBox

from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow


class DesktopFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = create_application([])

    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        self.application.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.application.processEvents()

    def test_window_and_empty_waveform_are_real_widgets(self):
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.windowTitle(), "SonicCraft — Audio Editor")
        self.assertIs(create_application([]), self.application)
        self.assertEqual(self.window.waveform.getPlotItem().listDataItems(), [])
        self.assertEqual(self.window.waveform.getAxis("bottom").labelText, "Time")
        self.assertEqual(self.window.waveform.getAxis("bottom").labelUnits, "s")
        self.assertEqual(self.window.waveform.getAxis("left").labelText, "Amplitude")
        self.assertFalse(self.window.grab().isNull())
        self.assertIn("no audio loaded", self.window.statusBar().currentMessage())

    def test_actions_require_audio_except_open(self):
        self.assertTrue(self.window.actions_by_name["open"].isEnabled())
        for name in ("save", "undo", "redo", "play", "stop", "reset_audio"):
            with self.subTest(action=name):
                action = self.window.actions_by_name[name]
                self.assertFalse(action.isEnabled())
                self.assertTrue(action.toolTip())
        menu_names = [action.text() for action in self.window.menuBar().actions()]
        self.assertEqual(menu_names, ["&File", "&Edit", "&Effects", "&Analysis", "&View", "&Help"])

    def test_view_actions_and_about_are_connected(self):
        self.window.waveform.setXRange(10, 20, padding=0)
        self.window.actions_by_name["reset_view"].trigger()
        self.assertEqual(self.window.waveform.viewRange()[0], [0, 1])
        self.window.transport_toolbar.toggleViewAction().trigger()
        self.assertFalse(self.window.transport_toolbar.isVisible())
        self.window.transport_toolbar.toggleViewAction().trigger()
        self.assertTrue(self.window.transport_toolbar.isVisible())
        with patch.object(QMessageBox, "about") as about:
            self.window.actions_by_name["about"].trigger()
            about.assert_called_once()
            self.assertIn("DSP changes real samples", about.call_args.args[2])

    def test_exit_closes_the_window(self):
        self.window.actions_by_name["exit"].trigger()
        self.application.processEvents()
        self.assertFalse(self.window.isVisible())

    def test_entrypoint_event_loop_starts_and_exits_without_web_imports(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "main.py", "--smoke-test"],
            cwd=root, capture_output=True, text=True, timeout=30,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("startup/shutdown: OK", result.stdout)
        # A fresh interpreter verifies dependency separation, not test runner state.
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; from soniccraft.desktop.main import create_application; "
             "assert not any(name in sys.modules for name in ('fastapi', 'uvicorn', 'flask', 'soniccraft.api.app'))"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
