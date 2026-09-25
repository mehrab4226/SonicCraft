"""Desktop controls for assembling a simple multitrack mix."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget, QMessageBox,
)

from .document import AudioData
from .theme import label


class MultitrackMixer(QWidget):
    mixdown_requested = pyqtSignal(list, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        controls = QHBoxLayout()
        add_button = QPushButton("Add Track...")
        add_button.clicked.connect(self._add_track_dialog)
        controls.addWidget(add_button)
        controls.addStretch()
        self.mixdown_button = QPushButton("Mixdown to Document")
        self.mixdown_button.setProperty("primary", True)
        self.mixdown_button.clicked.connect(self._request_mixdown)
        self.mixdown_button.setEnabled(False)
        controls.addWidget(self.mixdown_button)
        layout.addLayout(controls)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.track_container = QWidget()
        self.track_layout = QVBoxLayout(self.track_container)
        self.track_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.track_container)
        layout.addWidget(self.scroll_area, 1)

    def _add_track_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add audio tracks", "", "Audio (*.wav *.flac *.mp3)"
        )
        for path in paths:
            try:
                self._add_track(AudioData.open(path))
            except Exception as error:
                QMessageBox.warning(self, "SonicCraft", str(error))

    def _add_track(self, audio):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 8, 8, 8)
        filename = QLabel(audio.filename)
        filename.setToolTip(audio.filename)
        filename.setMinimumWidth(120)
        row_layout.addWidget(filename, 2)
        offset = QDoubleSpinBox()
        offset.setRange(0.0, 3600.0)
        offset.setDecimals(3)
        offset.setSuffix(" s")
        offset.setAccessibleName("Timeline offset")
        row_layout.addWidget(label("Offset"))
        row_layout.addWidget(offset)
        volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(100)
        volume.setAccessibleName("Volume")
        row_layout.addWidget(label("Volume"))
        row_layout.addWidget(volume, 1)
        mute = QCheckBox("Mute")
        row_layout.addWidget(mute)
        self.track_layout.addWidget(row)
        self.tracks.append({"audio": audio, "row": row, "offset": offset, "volume": volume, "mute": mute})
        self.mixdown_button.setEnabled(True)

    def _request_mixdown(self):
        if not self.tracks:
            return
        rate = self.tracks[0]["audio"].sample_rate
        tracks = [
            {
                "samples": track["audio"].samples,
                "offset": track["offset"].value(),
                "volume": track["volume"].value() / 100.0,
                "mute": track["mute"].isChecked(),
            }
            for track in self.tracks
        ]
        self.mixdown_requested.emit(tracks, rate)