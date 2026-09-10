# SonicCraft implementation plan

This document is the implementation handoff for completing SonicCraft and wiring
the existing Python DSP package to the React frontend.

## Current state

- [x] Python DSP package exists with audio I/O, editing, filters/EQ, noise
  reduction, FFT/STFT, spectrograms, Griffin-Lim, convolution, sampling, and
  analysis.
- [x] Backend unit tests exist for 13 DSP behaviors.
- [x] React/Vite editor shell, dark/light themes, and responsive layouts exist.
- [x] Frontend strict TypeScript check passes.
- [ ] No HTTP/API layer connects React to Python.
- [ ] Most frontend data, waveforms, meters, controls, and transport values are
  hard-coded.
- [ ] Backend dependencies are not installed in the current environment, so tests
  stop at the missing `soundfile` dependency.
- [ ] The current `main` working tree contains a large uncommitted migration.
  Preserve it and do not reset or overwrite unrelated changes.

## Architecture

| Responsibility | Implementation |
| --- | --- |
| Timeline state, selections, undo/redo | React reducer and context |
| Playback, real-time preview, meters | Web Audio API |
| Live microphone spectrogram | Web Audio `AnalyserNode` and Canvas |
| Offline DSP and authoritative export | Existing Python `soniccraft` package |
| Frontend/backend connection | Versioned FastAPI REST API |
| Waveform, FFT, and spectrogram rendering | Canvas using backend-generated numeric data |
| Long-running UI operations | `AbortController`, progress states, and cooperative cancellation where practical |

Keep the backend stateless: the frontend owns imported audio blobs and sends audio
plus parameters when processing or analyzing. Processing responses return WAV
blobs; analysis responses return typed JSON.

## Execution checklist

### 1. Protect and prepare the repository

- [ ] Preserve all current uncommitted files and inspect overlaps before editing.
- [ ] Create a `codex/soniccraft-integration` branch if a branch is desired.
- [ ] Install the backend package with development dependencies.
- [ ] Confirm all existing backend tests pass before changing DSP code.
- [ ] Run the frontend typecheck and production build in a normal writable
  environment.
- [ ] Add documented commands for starting the backend and frontend together.

### 2. Add the backend HTTP layer

Create an API package such as:

```text
backend/src/soniccraft/api/
|-- app.py
|-- routes/
|-- schemas.py
|-- serialization.py
|-- services.py
`-- errors.py
```

- [ ] Add FastAPI, Uvicorn, multipart-upload support, and Pillow to
  `backend/pyproject.toml`.
- [ ] Configure development CORS for the Vite origin only.
- [ ] Add upload-size, duration, channel-count, FFT-size, and parameter limits.
- [ ] Convert DSP `ValueError` exceptions into consistent `422` JSON responses.
- [ ] Run CPU-heavy functions outside the asynchronous event loop.
- [ ] Add `/api/v1/health`.
- [ ] Add API tests using generated tone/noise fixtures.

Recommended endpoints:

- [ ] `POST /api/v1/audio/inspect`
  - Use `read_audio_bytes`, `waveform_envelope`, `dbfs`, peak, and clipping
    helpers.
- [ ] `POST /api/v1/audio/process/gain-fade`
  - Use `apply_gain`, `apply_fade`, normalization, and WAV encoding.
- [ ] `POST /api/v1/audio/process/equalizer`
  - Use `ParametricEQBand`, `apply_parametric_eq`, filter helpers, and
    `frequency_response`.
- [ ] `POST /api/v1/audio/process/noise-reduction`
  - Support spectral gate, spectral subtraction, Wiener filtering, high-pass,
    low-pass, and notch cleanup.
- [ ] `POST /api/v1/analysis/spectrum`
  - Use `fft_spectrum`; support selection, channel, FFT size, window, DC
    removal, and dB floor.
- [ ] `POST /api/v1/analysis/spectrogram`
  - Use `spectrogram`; select or mix channels and cap/downsample the returned
    matrix for safe browser rendering.
- [ ] `POST /api/v1/spectrogram/reconstruct`
  - Convert an uploaded spectrogram image into a magnitude matrix, call
    `griffin_lim`, and return WAV.
- [ ] `POST /api/v1/audio/mixdown`
  - Resample tracks when necessary, apply offsets/gains/fades, call
    `mix_audio`, and return a WAV download.

### 3. Establish frontend domain state

- [ ] Replace the minimal `AudioTrack` type with typed project, asset, clip,
  selection, effect, analysis, transport, and processing models.
- [ ] Add an `EditorProvider` using `useReducer`; avoid a large state dependency.
- [ ] Keep decoded `AudioBuffer`, `Blob`, and object URLs in an in-memory asset
  registry.
- [ ] Implement immutable history for undo/redo.
- [ ] Revoke object URLs and release buffers when revisions are discarded.
- [ ] Add a typed API client using `VITE_API_BASE_URL`.
- [ ] Add loading, success, validation-error, server-error, and cancellation
  states.

### 4. Implement import and waveform rendering

- [ ] Make both Open audio and Add track import actual files.
- [ ] Decode supported audio through Web Audio for playback.
- [ ] Send imported files to `/audio/inspect`.
- [ ] Display real duration, sample rate, channel count, format, subtype/bit
  depth, peak, and clipping information.
- [ ] Replace the fixed SVG waveform with a Canvas waveform built from backend
  envelope data.
- [ ] Support multiple tracks, selection, rename, reorder, color, mute, solo,
  and removal.
- [ ] Provide empty, decoding, unsupported-format, and backend-unavailable
  states.
- [ ] Where the browser can decode a format the backend cannot, convert it to WAV
  in a worker before backend processing.

### 5. Implement transport and editing

- [ ] Build one shared Web Audio engine with synchronized track playback.
- [ ] Wire play, pause, seek, previous/next boundary, loop, playhead, and master
  volume.
- [ ] Make the time ruler derive from project duration and zoom.
- [ ] Implement zoom, horizontal pan, snapping, pointer selection, and keyboard
  navigation.
- [ ] Implement trim, split, cut, copy, paste, and delete using non-destructive
  clip boundaries.
- [ ] Wire undo/redo buttons and keyboard shortcuts.
- [ ] Disable unavailable actions with an explanatory tooltip.
- [ ] Add fade handles and linear, equal-power, and exponential curve selection.

### 6. Wire volume, EQ, and noise removal

- [ ] Convert `EffectsPanel` from fixed rows into a selected-effect editor or
  drawer.
- [ ] Add per-track and master gain in dB with live meters and clipping warnings.
- [ ] Use Web Audio gain/EQ nodes for responsive preview.
- [ ] Use the Python endpoints when committing effects and during final export.
- [ ] Build a draggable multiband EQ with frequency, gain, Q, presets, bypass,
  reset, response curve, and A/B audition.
- [ ] Add noise-profile selection from the waveform.
- [ ] Support spectral gate, spectral subtraction, Wiener, high-pass/low-pass,
  and notch cleanup.
- [ ] Add sensible defaults, parameter validation, preview, apply, bypass,
  before/after, progress state, and cancel/discard.
- [ ] Clearly describe algorithm tradeoffs without calling them AI.

### 7. Implement FFT and audio spectrogram

- [ ] Make the inspector analysis buttons switch the central workspace between
  editor, FFT, spectrogram, and live views.
- [ ] Build the FFT Canvas with linear/log frequency, FFT size, window, channel,
  smoothing, peak frequency, and cursor readout.
- [ ] Support Hann, Hamming, Blackman, and rectangular windows.
- [ ] Build the offline spectrogram Canvas with FFT size, hop length, window,
  color map, dB range, channel, and linear/log frequency controls.
- [ ] Recalculate analyses for the selected track or selected time range.
- [ ] Debounce parameter changes and cancel stale requests.
- [ ] Export the rendered spectrogram as PNG.

### 8. Implement spectrogram-to-audio

- [ ] Export SonicCraft spectrogram PNGs with embedded reconstruction metadata:
  sample rate, FFT size, hop length, window, scale, and dB range.
- [ ] Accept compatible PNG uploads and allow manual parameters when metadata is
  absent.
- [ ] Validate image height against `n_fft / 2 + 1`.
- [ ] Invert the known color map or grayscale mapping into magnitude values.
- [ ] Reconstruct phase with Griffin-Lim and return a previewable WAV.
- [ ] Display progress by Griffin-Lim iteration and support cooperative
  cancellation.
- [ ] Explain that phase information was lost and reconstruction will not
  perfectly match the original.

### 9. Implement live spectrogram

- [ ] Request microphone access only after the user presses Start.
- [ ] Add device selection, input level, pause/resume, freeze, FFT size, time
  window, and frequency scale.
- [ ] Render a scrolling Canvas spectrogram from `AnalyserNode`.
- [ ] Handle denied permission, missing devices, disconnected devices, and
  device changes.
- [ ] Stop every `MediaStreamTrack`, cancel animation frames, and close audio
  nodes when leaving the view.

### 10. Export, testing, and polish

- [ ] Export selected tracks or the complete mix as PCM WAV through the backend.
- [ ] Respect mute, solo, offsets, clip boundaries, gain, fades, and committed
  effects.
- [ ] Warn about clipping and optionally normalize the mix.
- [ ] Add Vitest, React Testing Library, and intentional Web Audio/media-device
  mocks.
- [ ] Test reducers, history, parameter validation, API adapters, cleanup,
  import, processing, and export.
- [ ] Add backend API tests for every endpoint and invalid-input path.
- [ ] Verify dark/light themes and desktop, tablet, and narrow layouts.
- [ ] Verify keyboard access, focus visibility, screen-reader status
  announcements, and reduced motion.
- [ ] Remove all hard-coded demo tracks and values.
- [ ] Ensure every visible control works, is disabled with a reason, or is
  explicitly identified as planned.
- [ ] Update both READMEs with setup, architecture, supported formats,
  limitations, and verification commands.

### 11. Connect course concepts to the interface

- [ ] Explain amplitude scaling beside gain and normalization controls.
- [ ] Explain time shifting and superposition in timeline and mix controls.
- [ ] Explain LTI systems and convolution beside filters and impulse responses.
- [ ] Explain sampling rate, Nyquist frequency, and aliasing near import and
  resampling controls.
- [ ] Explain the Fourier transform and STFT in the FFT and spectrogram views.
- [ ] Relate EQ/filter frequency response to the Z-domain without claiming that
  the UI performs a separate Z-transform operation.
- [ ] Present Laplace-transform context as the continuous-time analogue of the
  implemented filter concepts, without presenting it as a feature that does not
  exist.
- [ ] Keep educational explanations concise and optional so they do not obstruct
  the editing workflow.

## Existing backend-to-feature mapping

| Product feature | Existing backend functions to reuse |
| --- | --- |
| Import and metadata | `read_audio_bytes`, `inspect_audio`, `write_audio_bytes` |
| Waveform and meters | `waveform_envelope`, `peak_amplitude`, `rms`, `dbfs`, `clipping_fraction` |
| Basic editing | `trim_audio`, `split_audio`, `concatenate_audio`, `mix_audio` |
| Volume and fades | `apply_gain`, `apply_fade`, `normalize_peak`, `normalize_rms` |
| Equalizer and cleanup filters | `apply_parametric_eq`, `graphic_equalizer`, `frequency_response`, Butterworth and notch helpers |
| Noise removal | `estimate_noise_profile`, `spectral_gate`, `spectral_subtraction`, `wiener_denoise` |
| FFT spectrum | `fft_spectrum`, `magnitude_to_db` |
| Audio-to-spectrogram | `stft`, `spectrogram` |
| Spectrogram-to-audio | `db_to_magnitude`, `griffin_lim`, `write_audio_bytes` |
| Mixdown/export | `resample_audio`, `mix_audio`, `write_audio_bytes` |
| Live spectrogram | Browser Web Audio API; no backend round trip |

## Final completion gate

Mark the project complete only when all of these pass:

- [ ] Existing DSP unit tests pass.
- [ ] New backend API tests pass.
- [ ] Frontend typecheck and production build pass.
- [ ] Frontend component and integration tests pass.
- [ ] A real file can be imported, edited, processed, played, analyzed, and
  exported.
- [ ] All required noise-removal algorithms work end to end.
- [ ] FFT and offline/live spectrograms work with real audio.
- [ ] A SonicCraft-exported spectrogram can be reconstructed into playable WAV
  audio.
- [ ] Audio contexts, workers, object URLs, requests, animation frames, and
  microphone tracks are cleaned up.
- [ ] No misleading dead controls or fabricated backend behavior remain.

Only change an item from `[ ]` to `[x]` after its implementation has been tested
or manually exercised. The final implementation report should list the exact
commands run, what passed, what remains intentionally limited, and any known
technical risks.
