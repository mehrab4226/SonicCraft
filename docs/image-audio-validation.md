# Conversion rule verification

Verified on 2026-09-27 against independent SciPy transforms, analytic frequency
positions, and expected image geometry. Tests are in
`backend/tests/test_image_audio.py`.

## Findings fixed

- Tall images could lose a one-pixel frequency line entirely during interpolation.
- Wide images could lose a one-pixel event entirely during time compression.
- A one-row image mapped only to zero frequency instead of a uniform frequency band.
- EXIF orientation was ignored, changing the direction and duration of visible marks.

Downsampling now merges peaks into their nearest output bins before interpolation.
Single-row images fill the frequency range, and saved orientation is respected.
The image chooser remains the only import step.

## Content checks

- Known two-tone audio matches SciPy spectrogram magnitudes within relative 1e-5
  and absolute 1e-7 tolerance, including its 3:1 amplitude ratio.
- Sequential image notes retain pitch within one FFT bin (21.53 Hz), timing within
  two hops (23.22 ms), and a 1:2 relative strength ratio within 0.08. The silent
  interval remains below 1% of the first note's strength.
- An independently encoded two-tone audio/image pair retains its exact 65,536
  sample duration, with approximately 6.0% relative spectral error and 0.9982
  spectral correlation after accounting for global peak normalization.
- Regression checks cover thin marks, single-row and single-column images,
  silence, transparency, RGB tint equivalence, EXIF orientation, duration limits,
  and invalid parameters.

These validate the documented conversion rules. They do not imply lossless
waveform recovery or automatic understanding of arbitrary labelled screenshots.

## PNG audio restoration

Saved spectrogram PNGs now explicitly carry source audio. Tests verify exact
sample equality through the desktop importer for a four-minute stereo signal,
44.1 kHz mono, and 48 kHz stereo. The actual graph export also round-trips exactly.
A damaged audio chunk is rejected. This restoration path is separate from the
approximate pixel conversion measured above. Old graph-only PNGs cannot restore
the song; they must be exported again from the source audio.
