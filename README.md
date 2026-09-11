# SonicCraft

SonicCraft is a local PyQt6 desktop audio editor for a university Signals & Systems
course. The desktop interface reuses the existing `soniccraft` NumPy/SciPy DSP
package. Running the desktop app does not start a web server, use a database, or
contact an external service.

## Current milestone: Phase 2 — Audio I/O

The desktop window, menus, transport toolbar, PyQtGraph waveform, audio file I/O,
metadata, playback controls, selection, editing, effects, and startup/shutdown
are implemented and tested.

Audio can be opened, inspected, played, edited, processed, and saved locally.
The next implementation phase is described in
[the implementation plan](docs/implementation-plan.md).

The existing DSP core already implements editing primitives, gain/fades, filters,
parametric EQ, noise reduction, FFT/STFT, reconstruction, convolution, and
resampling. It is retained in place rather than copied into GUI code. A Wiener
denoising edge case on silent audio was fixed and tested during this migration.

## Installation and running

Python 3.11 or newer is required. The current Windows environment was verified
with Python 3.14, PyQt6 6.11.0, and PyQtGraph 0.14.0.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

On macOS/Linux, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.
Once the environment is activated, `soniccraft` is also available as a desktop
entry point.

The install adds only the libraries used by the foundation: PyQt6, PyQtGraph,
NumPy, SciPy, and SoundFile, plus their dependencies. Sounddevice, Librosa, and
wavelet libraries will be added only when their functionality is implemented.
Runtime operation is offline; initial dependency installation needs packages
available locally or through a package index.

## Structure

```text
main.py                            Desktop launcher
requirements.txt                   Desktop installation entry point
backend/src/soniccraft/
  desktop/
    main.py                        QApplication and lifecycle
    main_window.py                 Window, actions, menus, toolbar, status
    waveform_widget.py             Empty time/amplitude plotting surface
  audio_io.py                      Existing SoundFile decoding and encoding
  dsp/                             Existing independent DSP implementation
backend/tests/                     DSP and desktop tests
docs/implementation-plan.md        Authoritative phased desktop plan
```

The `backend/` directory name is retained to preserve the existing package layout.
The desktop imports the Python DSP package directly; there is no frontend/backend
HTTP boundary in the new application.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m compileall -q main.py backend/src/soniccraft/desktop
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py --smoke-test
```

The smoke test runs the real Qt event loop, shows the main window, and closes it
automatically. For an automated environment without a display, set
`QT_QPA_PLATFORM=offscreen`.

Desktop tests cover initial rendering, empty signal data, menu/action states,
view toggles, About, exit, and a separate-process startup/shutdown check. DSP tests
check known signals and numerical results.

## DSP course connections

These functions exist in the shared core; their desktop controls are later phases.

| Course concept | Existing DSP implementation |
| --- | --- |
| Discrete-time signals | Mono/stereo NumPy samples and sample rates |
| Amplitude scaling | `apply_gain`: y[n] = 10^(G_dB/20) x[n] |
| Time-domain editing | `trim_audio`, `split_audio`, concatenation |
| LTI systems and frequency response | Butterworth/notch filters and SOS parametric EQ |
| Convolution | Direct and FFT convolution |
| Fourier analysis | FFT, Fourier series, and calibrated magnitude spectra |
| Sampling and aliasing | Polyphase resampling and alias-frequency calculation |
| Time-frequency analysis | STFT and spectrogram |
| Reconstruction | Weighted overlap-add inverse STFT; Griffin-Lim for missing phase |
| Noise estimation | Spectral subtraction, spectral gating, local Wiener filtering |

Magnitude-only spectrograms lose phase and cannot generally reconstruct the
original waveform exactly. Full STFT round trips are tested with numerical
tolerances.

## Known limits

- Desktop foundation and local audio I/O phases are complete.
- No audio device is opened and no microphone permission is requested yet.
- Live microphone recording and spectrogram features are not implemented yet.
- Multi-track project management and advanced waveform editing remain future work.
