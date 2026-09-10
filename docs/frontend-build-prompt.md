# Codex prompt: build the SonicCraft frontend

You are working in the existing SonicCraft repository. Build the production-quality
frontend for a signals-and-systems course project: a browser-based audio editor that
makes signal-processing concepts visible and interactive.

## First, understand the repository

- Inspect the full repository before editing.
- Preserve the Python signal-processing package under `backend/src/soniccraft/` and its tests.
- Work primarily inside `frontend/`, which is a React + TypeScript + Vite application.
- Follow the existing feature-based structure and shared design tokens. Refactor it
  only when doing so clearly improves maintainability.
- Treat the existing editor screen as the visual direction, not as disposable code.

## Product direction

SonicCraft should feel like a focused, modern audio workstation that is approachable
to students. It should look polished enough for a course demonstration without
imitating a specific commercial product. Use a restrained dark interface by default,
violet as the main accent, clear waveform colors, compact professional controls, and
excellent spacing. Keep the existing light theme fully usable. Avoid excessive glow,
gradients, glass effects, oversized text, or generic dashboard cards.

The interface must visibly connect editing operations to signals-and-systems ideas.
Use concise educational labels or optional help affordances for concepts such as
time shift, amplitude scaling, convolution, frequency response, sampling rate,
aliasing, Fourier transform, Laplace transform, and Z-transform where relevant.
Do not turn the editor into a textbook or clutter the primary workflow.

## Required frontend features

1. Project and audio import
   - Import WAV, MP3, OGG, and FLAC where browser support permits.
   - Show file metadata: duration, channels, sample rate, bit depth when available.
   - Support multiple tracks and clear empty, loading, decoding-error, and unsupported-file states.

2. Basic audio editing
   - Interactive waveform timeline with zoom, pan, playhead, selection, trim, cut,
     copy, paste, split, delete, undo, and redo.
   - Track mute, solo, rename, reorder, and per-track color.
   - Keyboard shortcuts, tooltips, and visible focus states.

3. Volume and fades
   - Master and per-track gain controls with decibel values and meters.
   - Fade-in and fade-out handles or controls with linear and equal-power curves.
   - Prevent clipping or clearly warn when peaks exceed 0 dBFS.

4. Equalizer
   - A responsive multiband EQ with draggable control points.
   - Frequency axis in Hz/kHz, gain in dB, Q/bandwidth, bypass, reset, and presets.
   - Overlay the resulting frequency-response curve and allow before/after auditioning.

5. Noise remover with multiple algorithms
   - Provide a clear algorithm selector for spectral gating, noise-profile subtraction,
     and at least one simple filtering option such as high-pass/low-pass cleanup.
   - Each algorithm needs appropriate parameters, sensible defaults, preview,
     processing progress, cancel, bypass, and before/after comparison.
   - Explain tradeoffs briefly in the UI without claiming the algorithms are AI.

6. FFT spectrum
   - Plot magnitude versus frequency with linear/log-frequency options, window-function
     choice, FFT-size choice, channel choice, smoothing, peak frequency, and cursor readout.
   - Include Hann, Hamming, Blackman, and rectangular windows.

7. Spectrogram and audio conversion
   - Render an audio-to-spectrogram view with selectable FFT size, hop size, window,
     color map, magnitude range, and linear/log scale.
   - Provide an explicit spectrogram-image-to-audio workflow with image upload,
     parameter validation, preview, progress, and clear limitations. Label phase
     reconstruction honestly (for example, Griffin-Lim when that is the chosen method).
   - Allow spectrogram export as PNG and processed audio export as WAV.

8. Live spectrogram
   - Request microphone permission only after a user action.
   - Display live spectrogram, input level, device selector, pause/resume, freeze,
     time window, FFT size, and frequency scale.
   - Handle denied permissions, unavailable devices, device changes, and cleanup of
     media tracks when leaving the view.

## Architecture and engineering constraints

- Keep feature-specific components, hooks, state, types, and services within their
  corresponding `src/features/<feature>/` directory.
- Put truly reusable controls in `src/shared/components`, reusable hooks in
  `src/shared/hooks`, domain-neutral utilities in `src/shared/lib`, and application
  composition in `src/app`.
- Create typed audio-domain models. Avoid `any`.
- Separate presentation from audio/DSP operations behind typed service interfaces,
  so browser Web Audio implementations can later be swapped for Python API calls.
- Use the Web Audio API and AudioWorklet where appropriate. Never block the main UI
  thread with large transforms; use workers for expensive FFT/spectrogram work.
- Choose a lightweight, well-maintained state approach. Do not introduce a large
  dependency when React state and reducers are sufficient.
- Do not fabricate backend endpoints. The framework-independent DSP functions live
  under `backend/src/soniccraft/`; if an HTTP API is not yet present, implement a
  typed local adapter and document the future API boundary.
- Persist only safe preferences such as theme and panel layout in local storage.
  Do not silently persist imported audio.
- Make destructive edits reversible through history and confirm only actions that
  discard an entire project or irreversible work.

## UX, responsiveness, and accessibility

- Optimize the full editor for desktop widths of 1280 px and above, provide a useful
  tablet layout, and provide a simplified but functional narrow-screen experience.
- Use semantic HTML, accessible names, logical tab order, keyboard operation, visible
  focus, adequate contrast, reduced-motion support, and screen-reader announcements
  for processing status.
- Never rely on color alone to communicate track state, clipping, selection, or errors.
- Use skeletons only for real asynchronous waits; otherwise prefer direct rendering.
- Every button must either work, be explicitly disabled with a reason, or be labeled
  as a planned/demo control. Do not leave misleading dead controls.

## Implementation sequence

1. Audit the starter, write a short implementation plan, and identify reusable shell code.
2. Establish typed project/audio state and Web Audio lifecycle management.
3. Implement import, waveform timeline, transport, selection, and basic editing.
4. Add volume/fades and EQ.
5. Add noise removal and offline analysis views.
6. Add spectrogram conversion flows and the live microphone spectrogram.
7. Add export, error handling, keyboard shortcuts, responsive states, and accessibility.
8. Add tests and polish only after the core flows work end to end.

## Verification and deliverables

- Run type checking and a production build after significant milestones.
- Add focused tests for reducers, audio math helpers, history behavior, parameter
  validation, and important user flows. Mock browser audio/media APIs intentionally.
- Verify that object URLs, AudioContexts, workers, and MediaStream tracks are cleaned up.
- Verify both themes and representative desktop, tablet, and mobile widths.
- Keep a concise `frontend/README.md` with setup, architecture, scripts, browser
  requirements, known limitations, and the planned Python integration boundary.
- At completion, report what works, what is intentionally mocked or deferred, tests
  run, and any technical risks. Do not claim a feature works unless you exercised it.

Start by inspecting the current files. Then implement the application in coherent,
testable milestones without replacing working code unnecessarily.
