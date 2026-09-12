"""Desktop lifecycle and command-line startup verification."""

from __future__ import annotations

import argparse
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow
from .theme import STYLESHEET


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create the single Qt application and configure its local UI palette."""
    existing = QApplication.instance()
    if existing is not None:
        if not isinstance(existing, QApplication):
            raise RuntimeError("A QApplication is required for the desktop interface.")
        return existing
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("SonicCraft")
    app.setOrganizationName("SonicCraft")
    app.setApplicationVersion("0.1.0")
    app.setStyle("Fusion")
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#0d1115",
        QPalette.ColorRole.WindowText: "#eef1f8",
        QPalette.ColorRole.Base: "#10171c",
        QPalette.ColorRole.AlternateBase: "#192229",
        QPalette.ColorRole.Text: "#eef1f8",
        QPalette.ColorRole.Button: "#202931",
        QPalette.ColorRole.ButtonText: "#eef1f8",
        QPalette.ColorRole.Highlight: "#91efd0",
        QPalette.ColorRole.HighlightedText: "#10271f",
        QPalette.ColorRole.ToolTipBase: "#263630",
        QPalette.ColorRole.ToolTipText: "#eef1f8",
    }
    for role, value in colors.items():
        palette.setColor(role, QColor(value))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#798399"))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
    app.setQuitOnLastWindowClosed(True)
    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SonicCraft local desktop audio editor")
    parser.add_argument("--smoke-test", action="store_true", help="Show the main window, then close it to verify startup/shutdown.")
    args = parser.parse_args(argv)
    app = create_application([sys.argv[0]])
    window = MainWindow()
    window.show()
    if args.smoke_test:
        QTimer.singleShot(300, window.close)
    result = app.exec()
    if args.smoke_test and result == 0:
        print("SonicCraft desktop startup/shutdown: OK")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
