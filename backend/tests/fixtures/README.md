# Image reconstruction fixture

`chirp_spectrogram.png` is the unmodified **LinearChirpMatlab.png** by Mark
Stenglein, released by its author into the public domain.

Source: https://commons.wikimedia.org/wiki/File:LinearChirpMatlab.png
Original: https://upload.wikimedia.org/wikipedia/commons/a/af/LinearChirpMatlab.png

The source describes a 0.1-to-2 kHz linear chirp over two seconds. Its unusual
layout puts time upward on Y and frequency rightward on X. A colour bar encodes
power per frequency in dB/Hz. Tests compare the reconstructed frequency ridge
with 100 + 950*t Hz using SciPy's independent STFT, allowing for pixel resolution,
window blur, omitted edge frames and missing phase.

For this 1276 by 831 pixel image, the test crops plot pixels (160, 64, 1093, 738)
and colour-bar pixels (1110, 64, 1130, 738), using right/bottom exclusive bounds.
Calibration uses 2 seconds, 0-2250 Hz, linear frequency and a 102 dB colour span
(approximately -24 dB at the top to -126 dB at the bottom).
