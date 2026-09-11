import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from soniccraft.dsp.transforms import Spectrum
from soniccraft.dsp.analysis import get_dominant_frequency

class SpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("spectrumWidget")
        
        # Main layout for the panel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top control bar
        top_bar = QHBoxLayout()
        
        self.info_label = QLabel("Peak Frequency: -- Hz")
        self.info_label.setStyleSheet("font-weight: bold; color: #ffcf70;")
        top_bar.addWidget(self.info_label)
        
        top_bar.addStretch()  # Pushes the dropdown to the right
        
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Decibels (dB)", "Linear Magnitude"])
        self.scale_combo.currentIndexChanged.connect(self._replot)
        top_bar.addWidget(self.scale_combo)
        
        layout.addLayout(top_bar)
        
        # The PyQtGraph Plot
        self.plot_widget = pg.PlotWidget(background="#0b0f16")
        self.plot_widget.setLabel("bottom", "Frequency", units="Hz")
        self.plot_widget.setLabel("left", "Magnitude", units="dB")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        
        # The line drawn on the graph
        self.plot_curve = self.plot_widget.plot(pen="#64d6cd")
        layout.addWidget(self.plot_widget)
        
        self.current_spectrum = None
        
    def set_spectrum(self, spectrum: Spectrum):
        """Called by the main window when new audio is analyzed."""
        self.current_spectrum = spectrum
        
        # Update the text label
        peak = get_dominant_frequency(spectrum)
        self.info_label.setText(f"Peak Frequency: {peak:.1f} Hz")
        
        # Redraw the graph
        self._replot()
        
    def _replot(self):
        """Updates the graph based on the selected scale (dB or Linear)."""
        if self.current_spectrum is None:
            self.plot_curve.setData([], [])
            return
            
        x = self.current_spectrum.frequencies
        
        if self.scale_combo.currentIndex() == 0:
            # dB Scale
            y = self.current_spectrum.magnitude_db
            self.plot_widget.setLabel("left", "Magnitude", units="dB")
        else:
            # Linear Scale
            y = self.current_spectrum.magnitude
            self.plot_widget.setLabel("left", "Magnitude", units="Linear")
            
        # FIX: If the audio is stereo (2D array), average the channels to mono for the plot
        import numpy as np
        if y.ndim > 1:
            y = np.mean(y, axis=1)
            
        self.plot_curve.setData(x, y)

    