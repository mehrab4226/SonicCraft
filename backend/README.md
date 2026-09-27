# SonicCraft Python package

The package contains the desktop editor and its feature-specific DSP code.
See the [project README](../README.md) for setup, features and verification.

Audio uses float64 arrays shaped `(samples,)` for mono or `(samples, channels)`
for stereo. DSP functions return new arrays. `AudioData` owns a read-only snapshot.

| Module | Connected feature |
|---|---|
| `audio_io` | Import/export and metadata |
| `dsp.effects` | Gain, peak normalization, fades, trimming and multitrack mixdown |
| `dsp.filters` | Butterworth filters, peaking EQ and response plots |
| `dsp.noise_reduction` | Noise profiles, subtraction, gating and Wiener filtering |
| `dsp.sampling` | Convert mixer tracks to the output sample rate |
| `dsp.transforms` | FFT, STFT, reconstruction and image synthesis |
| `dsp.analysis` | Spectrum peak frequency |
| `dsp._validation` | Shared signal/rate/channel validation |
| `desktop` | Widgets, document history, processing jobs and audio streams |

Install from the repository root with `python -m pip install -e "./backend[desktop,dev]"`.
Run tests with `python -m pytest backend/tests`.
