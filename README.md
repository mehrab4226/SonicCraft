# SonicCraft

A local audio editor for the CSE 220 Signals & Systems project. SonicCraft uses
PyQt6 and PyQtGraph for its desktop interface, NumPy and SciPy for DSP, and
SoundFile/sounddevice for audio files and playback. It runs without a web server,
database, or network service.

## Install and run

Python 3.11 or newer is required. From the repository root on Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`requirements.txt` installs this checkout, including the desktop and test extras.
It does not download an older SonicCraft revision. You can also run the installed
`soniccraft` command. On Linux/macOS, use `.venv/bin/python` instead.

## Implemented features

| Feature | Behavior |
|---|---|
| File I/O | Open mono/stereo WAV, FLAC, OGG, AIFF and supported MP3 files. Export WAV/FLAC as 24-bit PCM. |
| Transport | Play/pause, resume, stop, device selection, keyboard shortcuts and drag-and-drop opening. |
| Waveform | Separate stereo lanes, dimmed played audio, fitted graphs and exact time selections. |
| Channel editing | Target both channels, left, or right. Trim/delete keep channels synchronized. |
| Editing | Trim, delete, reverse, silence, peak normalization, gain and three fade curves. |
| Filters | Low-pass, high-pass, band-pass and band-stop Butterworth filters. |
| Equalizer | Nine peaking bands with synchronized sliders/numeric controls and Nyquist validation. |
| Noise reduction | Capture a noise profile, then use spectral subtraction or gating; local Wiener filtering also available. |
| Live previews | EQ, filter and noise parameters update playback through background rendering. Apply commits one undoable edit. |
| FFT | Analyze the full selection. Long selections use averaged overlapping windows at the original sample rate. |
| Spectrogram | Configurable FFT/window, dB or normalized magnitude, bounded display, selected-channel analysis. |
| Spectral editing | Mute a time-frequency rectangle using the displayed FFT/window and selected channel. |
| Microphone | Live spectrogram with an eight-second history and optional recording into the document. |
| Mixing | Add/remove tracks, offsets, volume, mute, sample-rate conversion and protected mixdown. |
| Image synthesis | Import a spectrogram image and estimate phase with Griffin-Lim to synthesize audio. |
| Recovery | Undo/redo, per-tool parameter reset and a master reset to the original audio. |

All graphs stay fitted to their workspace. Trackpad gestures do not zoom, pan or
change axis units. Selection handles and the spectral rectangle remain draggable.

### Preview, Apply, Export and Reset

- Changing EQ, filter or noise parameters previews from the committed audio.
  Apply saves the result inside the app. Apply before switching effects to keep
  multiple changes. Preview delay includes rendering time.
- Export writes the committed document to a file. It uses a temporary file and
  atomic replacement. Overloaded audio requires normalization or explicit export
  scaling; the stored samples are not silently clipped.
- A tool's reset restores only its parameters and clears its current preview.
  It preserves edits that were already applied.
- The bottom **Reset audio** restores the original loaded audio, resets all tool
  settings and clears the noise profile. The reset is undoable. Mixer imports
  remain available while their offsets, volumes and mute controls reset.
- Synthesized audio, recordings and mixdowns remain unsaved until exported.
  Replacing a document with unsaved edits requires confirmation.

### Shortcuts

`Ctrl+O`: open. `Ctrl+S`: export. `Space`: play/pause. `Ctrl+Z`: undo.
`Ctrl+Y`: redo. `Ctrl+A`: select all. `Ctrl+J`: fit audio.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -o addopts='' -q
.\.venv\Scripts\python.exe -m compileall -q main.py backend/src/soniccraft
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py --smoke-test
```

For headless startup testing, set `$env:QT_QPA_PLATFORM = 'offscreen'` before the
smoke command. Automated tests use real Qt widgets and simulated audio drivers.
Check physical speakers, microphone and projector before the evaluation.

## Repository map

- `main.py`: repository launcher.
- `backend/pyproject.toml`: package metadata and dependency declarations.
- `backend/src/soniccraft/desktop/`: UI, audio document, workers and stream lifecycle.
- `backend/src/soniccraft/dsp/`: algorithms connected to the implemented features.
- `backend/src/soniccraft/audio_io.py`: file decoding, encoding and metadata.
- `backend/tests/`: numerical, I/O, workflow and UI regression tests.
- `docs/architecture.md`: feature-to-module map and design decisions.
- `Presentation/`: slide source, reproducible figures, rehearsal guide and demo audio.
- `output/pdf/SonicCraft_CSE220_Final_Presentation.pdf`: submission presentation.

The `backend` directory is the Python package, not an HTTP backend. Tests,
documentation, packaging assets and presentation material support the delivered
application. Unconnected DSP exercises and superseded plans/slides have been removed.

## Practical limits

- The app loads audio into memory and supports mono/stereo documents.
- Long FFT selections average window magnitudes, trading frequency resolution for
  bounded transform size. Spectrograms merge adjacent analysis frames by peak
  magnitude into at most 1,200 columns (320 for live input), retaining brief events.
- Spectral processing and mixdown enforce a 256 MiB working/output budget.
  Microphone recording stops at 64 MiB of stored samples. These are limits on those
  buffers, not guarantees of total process memory use.
- Noise profiles work best when they contain only the unwanted sound. Strong
  reduction and abrupt spectral masks can produce artifacts.
- Image brightness contains no original phase. Image-to-audio synthesis is approximate.
- Playback and microphone availability depend on the local audio drivers and OS permissions.

## Presentation

Present the first 13 slides. The remaining slides are Q&A references. The
[rehearsal guide](Presentation/PRESENTER_GUIDE.md) includes the two-person timing
and an 80-second demo. Authoring dependencies are separate from the app:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Presentation/requirements.txt
.\.venv\Scripts\python.exe Presentation/prepare_presentation_assets.py
.\.venv\Scripts\python.exe Presentation/build_presentation.py
```

The presentation builder uses Windows Segoe UI/Consolas fonts. The app itself uses
Qt font fallbacks and is not tied to those font paths.
