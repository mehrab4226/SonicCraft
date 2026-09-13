# SonicCraft architecture

## Verified baseline — 2026-09-12

**Phase 7 — Noise Reduction is the last consecutively completed core milestone.**
Phases 1–7 are implemented and automated-tested; physical speaker and microphone
operation remains unverified. Phases 8 (FFT), 9 (Spectrogram) and 11 (Live
Spectrogram) have partial desktop workflows. Phases 10 (Spectral Editing /
Reconstruction) and 12 (optional DSP Lab) have DSP support only. Phase 13 final
acceptance is pending. Optional wavelet denoising remains absent.

The authoritative [implementation plan](implementation-plan.md) records evidence
and remaining requirements. Next priorities are explicitly **planned: 7A Stereo
Channel Workspace → 7B Multitrack Mixing → finish 8 → 9 → 10 → 11**, retain
**12 as optional**, then **13 acceptance**. Neither channel controls nor desktop
mixing is implemented merely by documenting these phases.

## Runtime and responsibilities

The local PyQt6 application imports the existing `soniccraft` package directly
from `backend/src`. It has no HTTP boundary, web server, database or hosted service.

```text
main.py -> soniccraft.desktop.main -> QApplication -> MainWindow
  ├─ menus / toolbar / status / alternating Play/Pause
  ├─ FeatureSidebar: categories -> features -> controls / Reset audio
  ├─ WaveformWidget: waveform, zoom and time-range selection
  ├─ analysis workspace: FFT / file and live spectrograms / filter response
  ├─ Document: current audio, original audio and undo/redo snapshots
  ├─ Player / Microphone: sounddevice output/input streams
  └─ Job workers: file I/O, processing and analysis -> Qt signals -> UI

soniccraft.audio_io    SoundFile decoding, metadata and encoding
soniccraft.dsp         Independent NumPy/SciPy signal processing
```

The [window/controller](../backend/src/soniccraft/desktop/main_window.py) connects
actions to document updates, stream lifecycle and background jobs. The
[sidebar](../backend/src/soniccraft/desktop/sidebar.py) provides six categories:
Edit & Dynamics, Filters & Equalizer, Noise Reduction, Spectrum Analyzer,
Spectrogram and Live Spectrogram. Back/All tools navigation returns through the
category tree. Editing and effect controls remain on the left; lower panels are
reserved for analysis. [Workspace tests](../backend/tests/test_desktop_workspace.py)
and [analysis tests](../backend/tests/test_analysis_workspace.py) cover navigation,
transport/reset state and existing analysis workflows.

## Audio data, edits and history

Audio uses time on axis 0: mono `(samples,)`, stereo `(samples, 2)`. Floating-point
samples retain headroom for clipping detection before encoding. The
[document](../backend/src/soniccraft/desktop/document.py) keeps the current audio,
original loaded audio and undo/redo snapshots. Reset audio restores the original,
selects its full range and is itself undoable; it does not modify exported files.
Decoded documents have no fixed size cap; audio is held in memory and depends on
available RAM. Ordinary history is bounded to 20 entries and 128 MiB, with the
original snapshot retained separately for reset.

[Processing adapters](../backend/src/soniccraft/desktop/processing.py) apply sample
edits, gain/fades, filters, EQ and noise reduction through the shared DSP core.
[Operation tests](../backend/tests/test_editor_operations.py) verify sample-level
results; [workflow tests](../backend/tests/test_desktop_workflow.py) exercise the
desktop integration, including file I/O and simulated transport.

The [waveform](../backend/src/soniccraft/desktop/waveform_widget.py) bounds rendering
with min/max envelopes without replacing the underlying audio. Stereo channels
are overlaid on the same amplitude axis, and edits currently process both channels.
There is one audio document, with no independent channel controls or multitrack
timeline. The existing [mixing DSP](../backend/src/soniccraft/dsp/effects.py)
supports mixing arrays; Phase 7B must add the desktop track model, routing,
sample-rate compatibility, playback and protected mixdown export.

## Streams and background work

The [audio engine](../backend/src/soniccraft/desktop/audio_engine.py) uses
sounddevice streams. Player streams the current audio and tracks position. The
single Play/Pause action reflects playback state, retains position while paused,
and returns to Play on stop or end of playback.

Microphone capture starts only on Start monitoring. The input callback copies
samples into a bounded queue; the UI drains it on a timer, keeps up to eight
seconds of history and schedules background display transforms. Generation checks
prevent stale worker results from replacing current views. Stop monitoring,
leaving the live analysis view, starting playback/processing or closing the app
releases the microphone. This is monitoring in memory, not recording to a file.

[Job workers](../backend/src/soniccraft/desktop/jobs.py) keep expensive I/O and DSP
off the UI path and deliver results through Qt signals. Existing automated stream
tests inject simulated drivers; they do not verify physical output/capture quality,
device permissions or real-device timing.

## Analysis boundaries

- **Phase 8 — partial:** the window passes at most the first 65,536 selected
  samples to FFT analysis. The [spectrum widget](../backend/src/soniccraft/desktop/spectrum_widget.py)
  averages per-channel dB for dB plotting, while dominant frequency uses mean
  linear magnitude. These can disagree. The plan records reproducible long-signal
  and stereo examples; neither defect is repaired by this documentation update.
- **Phase 9 — partial:** [display transforms](../backend/src/soniccraft/desktop/analysis.py)
  produce bounded dB heatmaps, averaging stereo to mono. File views allow FFT
  size/window selection and plot navigation but lack explicit hop, frequency-range,
  magnitude/dB controls and spectrogram-region selection. At most 1,200 columns
  represent the selection's time extent; adaptive hops can leave gaps between
  analysis windows. Colors span −100 to 0 dBFS.
- **Phase 10 — DSP-only:** [transforms](../backend/src/soniccraft/dsp/transforms.py)
  retain complex STFT phase and support inverse reconstruction, with numerical
  round-trip coverage in [transform tests](../backend/tests/test_transforms.py).
  Desktop heatmap data contains display magnitudes, not the complex representation
  needed for spectral editing/reconstruction. No reconstructed-audio desktop
  editing/playback/export workflow exists.
- **Phase 11 — partial:** live views use a fixed 1,024-point FFT, at most 320
  columns and eight seconds of rolling memory. Planned FFT-size/frequency-range
  controls and sensitivity where practical remain outstanding, as does hardware
  validation.
- **Phase 12 — DSP-only, optional:** sampling, aliasing and convolution utilities
  are covered by [processing tests](../backend/tests/test_processing.py), but have
  no interactive lab workspace.

## Verification

The 2026-09-12 audit passed **48 unittest tests** and **49 pytest tests**, Python
compilation, dependency checks and Qt startup/shutdown smoke testing. Pytest also
discovers the standalone FFT test that unittest skips. See the plan's evidence
index for the completed Phase 1–7 claims and the [README](../README.md) for setup.
With desktop and dev dependencies installed, run from the root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m pytest backend/tests -o addopts='' -q
.\.venv\Scripts\python.exe -m compileall -q main.py backend/src/soniccraft
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py --smoke-test
```

For a headless smoke test, set `$env:QT_QPA_PLATFORM = 'offscreen'` first. Physical
speaker and microphone verification remains a separate, outstanding acceptance
step; passing simulated-stream tests does not close it.
