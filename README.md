# SonicCraft

SonicCraft is a local PyQt6 desktop audio editor for a university Signals & Systems
course. The desktop interface reuses the existing `soniccraft` NumPy/SciPy DSP
package. Running the desktop app does not start a web server, use a database, or
contact an external service.

## Current desktop features

**Verified baseline — 2026-09-12: Phase 7 — Noise Reduction is the last
consecutively completed core milestone.** Phases 1–7 provide the desktop lifecycle,
audio I/O, metadata, transport, waveform/selection, sample editing, gain/fades,
undo/redo/reset, four filter types, nine-band EQ and noise reduction. These are
implemented and automated-tested; physical speaker and microphone operation remains
unverified. Optional wavelet denoising is absent.

FFT (Phase 8), file spectrograms (Phase 9) and live spectrograms (Phase 11) are
**partially implemented**, with the limits below. Spectral editing/reconstruction
(Phase 10) and the optional DSP Lab (Phase 12) have **DSP support only**.
Phase 13 final integration remains pending.

The next milestones are explicitly **planned: 7A — Stereo Channel Workspace**
(separate Left/Right lanes, linked/unlinked editing, gain/mute/solo, channel-aware
analysis and channel export), then **7B — Multitrack Mixing** (multiple tracks,
timeline offsets, levels/mute/solo, sample-rate compatibility, combined playback
and protected mixdown export). Then finish **8 → 9 → 10 → 11**, retain **12 as
optional**, and complete **13 acceptance**. See the
[implementation plan](docs/implementation-plan.md) for requirements and implementation/test
evidence, and [architecture](docs/architecture.md) for runtime responsibilities.

## Studio workspace

The native interface uses graphite panels, mint accents, vector transport icons,
and a resizable waveform/analysis workspace. Open a file with **Ctrl+O** or drop a
single local audio file into the window. Signal cards display duration, sample
rate, channel count, and peak level in dBFS; compact windows prioritize the
waveform and keep processing controls available in scrollable panels.

- **Space** plays or pauses; **Ctrl+A** selects all audio; **Ctrl+J** focuses the
  waveform on the selected range. **Fit audio** restores the full view.
- The transport uses one alternating **Play/Pause** button. Pause retains the
  playback position; Play resumes it. Stop or reaching the end returns the button
  to Play.
- **Reset audio**, at the bottom of the sidebar and in the Edit menu, restores
  the original loaded audio and selects its full range. It remains available
  after the ordinary undo history expires, and the reset itself is undoable with
  **Ctrl+Z**. Exported files are not changed by resetting the document.
- Enter exact selection boundaries in seconds, or drag the waveform region.
- The left **Tool Library** uses drill-down navigation: choose a category, then
  a feature. **Back to category** and **All tools** return one level without
  resetting your parameters. Controls remain in the sidebar; the lower workspace
  is reserved for analysis.
- **Edit & Dynamics** contains selection edits, gain, and fades.
  **Filters & Equalizer** contains frequency filtering and nine synchronized
  faders/numeric controls. Bands at or above Nyquist are disabled.
  **Noise Reduction** contains noise-profile capture and restoration methods.
- **Spectrum Analyzer** displays FFT magnitude for up to the first 65,536
  selected samples. **Spectrogram** generates a time-frequency heatmap of the
  complete selection with a configurable FFT size and window. Changing the
  selection or transform settings clears the old map until you regenerate it.
- **Live Spectrogram** opens the chosen microphone only after **Start monitoring**.
  It displays up to eight seconds of recent audio in memory. **Stop monitoring**,
  switching to another analysis view, starting playback/processing, or closing
  the app releases the microphone. It does not record an audio file.
- FFT, file/live spectrograms, and filter-response previews share the lower
  workspace. **Ctrl+Z** undoes an edit; **Ctrl+S** exports WAV or FLAC.
- Playback, processing, unsaved changes, and over-full-scale audio have visible
  status indicators. Dropping a replacement file respects unsaved-change prompts.

The existing DSP core already implements editing primitives, gain/fades, filters,
parametric EQ, noise reduction, FFT/STFT, reconstruction, convolution, resampling
and `mix_audio()`. Mixing is currently a DSP helper, with no desktop multitrack
workspace. The core is retained in place rather than copied into GUI code. A Wiener
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

The install uses PyQt6, PyQtGraph, NumPy, SciPy, SoundFile, and Sounddevice,
plus their dependencies.
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
    sidebar.py                     Category/feature navigation and controls
    waveform_widget.py             Waveform and selection plotting
    spectrum_widget.py             FFT magnitude display
    spectrogram_widget.py          File/live time-frequency heatmaps
    analysis.py                    Bounded display transforms
  audio_io.py                      Existing SoundFile decoding and encoding
  dsp/                             Existing independent DSP implementation
backend/tests/                     DSP and desktop tests
docs/implementation-plan.md        Authoritative phased desktop plan
```

The `backend/` directory name is retained to preserve the existing package layout.
The desktop imports the Python DSP package directly; there is no frontend/backend
HTTP boundary in the new application.

## Verification

The 2026-09-12 audit passed **48 unittest tests** and **49 pytest tests**.
Pytest also discovers the standalone `test_fft_dominant_frequency` function in
`backend/tests/test_transforms.py`, which unittest skips. Compilation, dependency
checks and startup/shutdown smoke testing passed as well. These results cover
automated behavior; audio-stream tests use simulated drivers, leaving physical
speaker and microphone operation unverified.

Install the development extra to include pytest:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[desktop,dev]"
```

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m pytest backend/tests -o addopts='' -q
.\.venv\Scripts\python.exe -m compileall -q main.py backend/src/soniccraft
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py --smoke-test
```

The smoke test runs the real Qt event loop, shows the main window, and closes it
automatically. For an automated environment without a display, set
`$env:QT_QPA_PLATFORM = 'offscreen'` first in PowerShell.

Desktop tests cover lifecycle, local I/O, edits/effects, selection, sidebar and
analysis navigation, reset, and simulated transport/live streams. DSP tests check
known signals and numerical results. The plan links each completed milestone to
its implementation and test evidence; passing the suite does not close the known
FFT defects or missing analysis requirements.

## DSP course connections

These functions exist in the shared core. Editing, gain/fades, filters/EQ and noise
reduction are connected to desktop controls. FFT and spectrogram controls are
partial; reconstruction, multitrack mixing and interactive DSP Lab workflows
remain planned. Fourier-series and convolution utilities are also core-only.

| Course concept | Existing DSP implementation |
| --- | --- |
| Discrete-time signals | Mono/stereo NumPy samples and sample rates |
| Amplitude scaling | `apply_gain`: y[n] = 10^(G_dB/20) x[n] |
| Time-domain editing | `trim_audio`, `split_audio`, concatenation |
| Signal superposition | `mix_audio()` with offsets and gains; desktop mixing planned |
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

- FFT uses at most the first 65,536 selected samples, so later content may be
  missed. Stereo dB plots average channel dB values, while dominant-frequency
  labeling uses mean linear magnitude; their peaks can disagree. Both reproduced
  discrepancies are recorded in the plan and remain unresolved Phase 8 work.
- Spectrograms show calibrated one-sided amplitude in dBFS, with colors spanning
  −100 to 0 dBFS. Stereo files are mixed to mono for the heatmap.
- File spectrograms provide FFT-size/window controls and plot navigation; explicit
  hop, frequency-range, magnitude/dB controls and spectrogram-region selection
  remain incomplete.
- File spectrograms use at most 1,200 time columns. Longer selections increase
  the displayed time step, potentially leaving gaps between analysis windows;
  the view reports its actual time step. These display maps are not used for reconstruction.
- Live analysis uses background jobs, a fixed 1,024-point FFT, eight seconds of
  rolling history and at most 320 time columns. Planned FFT-size/frequency-range
  controls and sensitivity where practical remain outstanding. Microphone
  availability and operating-system permissions depend on the machine. Automated
  stream tests use an injected driver rather than recording from physical hardware.
- Desktop spectral editing and reconstructed-audio playback/export remain absent,
  despite tested complex STFT/ISTFT support in the core. Saving microphone recordings
  is also not implemented; monitoring does not record a file.
- Stereo waveforms are overlaid, and edits currently affect both channels.
  Independent channel controls/export (7A) and desktop multitrack mixing (7B)
  are planned next. An interactive DSP Lab is optional future work.
- Final integration acceptance awaits the remaining required workflows and
  physical speaker/microphone validation.
