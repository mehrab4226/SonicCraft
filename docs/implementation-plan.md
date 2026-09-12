# SonicCraft — PyQt6 DSP Audio Editor

## Verified execution status — 2026-09-12

**Phase 7 — Noise Reduction is the last consecutively completed core milestone.**
The current application is a local PyQt6 desktop editor importing the shared
NumPy/SciPy DSP package under `backend/src`. Features from Phases 8, 9, and 11
operate, but do not satisfy their full original requirements.

Here, **completed** means implemented and automated-tested for the core milestone;
**partial** means a desktop workflow exists with requirements still outstanding;
**DSP-only** means reusable processing exists without the required desktop workflow.
**Unverified** physical-device behavior is separate from automated completion.
Optional wavelet denoising is absent and does not block the Phase 7 core baseline.

| Phase | Status | Evidence or remaining work |
| --- | --- | --- |
| 1–3: Foundation, Audio I/O, Waveform | Completed; automated-tested | Desktop lifecycle, open/export, metadata, transport, waveform, zoom, selection. See evidence A. |
| 4–5: Editing, Volume/Fade | Completed; automated-tested | Actual sample edits, gain, fades, undo/redo, undoable reset to original audio. See evidence B. |
| 6–7: Filters/EQ, Noise Reduction | Completed; automated-tested | Four filter types, nine-band EQ, response previews, noise profiles, subtraction, Wiener, spectral gating. Optional wavelets absent. See evidence C. |
| 7A: Stereo Channel Workspace | Planned | Separate channel lanes and independent channel controls; next priority. |
| 7B: Multitrack Mixing | Planned | New desktop milestone after 7A; `mix_audio()` alone is not a desktop mixer. |
| 8: FFT | Partial; correctness issue | Selection analysis truncates at 65,536 samples; stereo dB plotting and dominant-frequency labeling aggregate channels differently. See evidence D. |
| 9: Spectrogram | Partial | File heatmaps, FFT-size/window controls, plot navigation work. Explicit hop, frequency-range, magnitude/dB controls and spectrogram-region selection remain incomplete. See evidence D. |
| 10: Spectral Editing/Reconstruction | DSP-only | Complex STFT/ISTFT and reconstruction tests exist; desktop spectral edits and reconstructed-audio playback/export are absent. See evidence E. |
| 11: Live Spectrogram | Partial; ahead of sequence | Microphone monitoring, rolling history, workers, start/stop exist. FFT size is fixed; planned controls and hardware verification remain. See evidence D. |
| 12: Optional DSP Lab | DSP-only | Sampling, aliasing, convolution and related utilities exist without an interactive lab. See evidence E. |
| 13: Final Integration | Pending | Remaining feature acceptance and physical speaker/microphone verification required. |

### Implementation and verification evidence

- **A — Foundation, I/O, waveform:** [window/controller](../backend/src/soniccraft/desktop/main_window.py),
  [audio engine](../backend/src/soniccraft/desktop/audio_engine.py), and
  [waveform](../backend/src/soniccraft/desktop/waveform_widget.py), covered by
  [desktop lifecycle tests](../backend/tests/test_desktop.py) and
  [workflow tests](../backend/tests/test_desktop_workflow.py).
- **B — Editing, levels, reset:** [document/history](../backend/src/soniccraft/desktop/document.py)
  and [processing](../backend/src/soniccraft/desktop/processing.py), covered by
  [operation tests](../backend/tests/test_editor_operations.py) and
  [workspace tests](../backend/tests/test_desktop_workspace.py).
- **C — Filters and noise:** [filters](../backend/src/soniccraft/dsp/filters.py),
  [noise reduction](../backend/src/soniccraft/dsp/noise_reduction.py), and
  [desktop effect controls](../backend/src/soniccraft/desktop/effects_panel.py), covered by
  [operation tests](../backend/tests/test_editor_operations.py),
  [noise/I/O tests](../backend/tests/test_noise_and_io.py), and workflow tests above.
- **D — Partial analysis workflows:** [FFT widget](../backend/src/soniccraft/desktop/spectrum_widget.py),
  [display transforms](../backend/src/soniccraft/desktop/analysis.py),
  [spectrogram widget](../backend/src/soniccraft/desktop/spectrogram_widget.py), and window/controller;
  [analysis workspace tests](../backend/tests/test_analysis_workspace.py) exercise existing
  file/live views with simulated streams. These tests do not establish completion
  of the outstanding controls or correctness of the FFT cases below.
- **E — Core-only capabilities:** [transforms](../backend/src/soniccraft/dsp/transforms.py),
  [sampling](../backend/src/soniccraft/dsp/sampling.py),
  [convolution](../backend/src/soniccraft/dsp/convolution.py), and
  [mixing/effects](../backend/src/soniccraft/dsp/effects.py), covered by
  [transform tests](../backend/tests/test_transforms.py) and
  [processing tests](../backend/tests/test_processing.py).

The audit passed **48 unittest tests** and **49 pytest tests**. Pytest additionally
discovers the standalone `test_fft_dominant_frequency` function in
`test_transforms.py`, which unittest discovery skips. Python compilation,
dependency consistency, and the Qt startup/shutdown smoke test also passed.
Physical speaker output and microphone capture remain **unverified**: automated
audio-stream tests use simulated drivers.

Run from the repository root in PowerShell (pytest requires the `dev` extra):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m pytest backend/tests -o addopts='' -q
.\.venv\Scripts\python.exe -m compileall -q main.py backend/src/soniccraft
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py --smoke-test
```

For a headless smoke test, set `$env:QT_QPA_PLATFORM = 'offscreen'` first.
See [README](../README.md) for installation and [architecture](architecture.md)
for the current runtime structure.

### Recorded workspace milestone

The [sidebar](../backend/src/soniccraft/desktop/sidebar.py) provides category →
feature drill-down navigation, with Back/All tools navigation. Its six categories
are Edit & Dynamics, Filters & Equalizer, Noise Reduction, Spectrum Analyzer,
Spectrogram, and Live Spectrogram. Processing controls occupy the sidebar;
FFT, file/live spectrograms and filter-response previews share the lower analysis
workspace beneath the waveform. The transport has one alternating Play/Pause
button. Reset audio restores the original loaded samples, selects the full range,
and is itself undoable. Workspace and analysis tests above cover these behaviors.
Stereo traces are currently overlaid; independent channel editing and multitrack
mixing are planned, not completed by this layout milestone.

### Reproduced discrepancies and analysis limits

- **FFT selection coverage:** at 8 kHz, 65,536 silent samples followed by 8,000
  samples of a 1 kHz sine produce a 1 kHz peak when the whole signal is analyzed.
  The desktop examines only the initial 65,536 samples and reports 0 Hz for that
  silent prefix. Whole-selection analysis remains an unmet Phase 8 requirement.
- **Stereo FFT aggregation:** for one second at 8 kHz, let Left contain a 0.8
  amplitude 440 Hz tone plus a 0.1 amplitude 2 kHz tone, and Right a 0.4 amplitude
  1 kHz tone plus the same 0.1 amplitude 2 kHz tone. The label's mean linear
  magnitude peaks at 440 Hz; the mean of channel dB values plotted in dB mode
  peaks at 2 kHz. Channel aggregation and labeling must be made consistent.
- **File spectrogram:** the display averages stereo to mono, uses a fixed
  −100 to 0 dBFS color scale and at most 1,200 time columns. Adaptive hop covers
  the selection's time extent but may skip intervening analysis windows. FFT size
  and window are configurable; explicit hop, frequency range, magnitude/dB mode
  and a selectable spectrogram region remain outstanding. Display magnitudes
  do not retain the complex phase required for reconstruction.
- **Live spectrogram:** eight seconds of rolling memory, at most 320 columns,
  fixed 1,024-point FFT. Planned transform/frequency-range controls and sensitivity
  where practical remain outstanding, along with physical microphone validation.

### Approved next priorities

Implement **7A → 7B → finish 8 → 9 → 10 → 11**, retain **12 as optional**, then
complete **13 acceptance**. The original Phase 1–13 numbers and technical
requirements below are retained. Phases 7A and 7B are explicitly planned desktop
extensions; this dated roadmap update implements neither those features nor the
identified defect repairs. Earlier bootstrap instructions are historical.

---

## Master Development Prompt

You are working on a university **Signals & Systems / Digital Signal Processing** course project called **SonicCraft**.

SonicCraft is a **local desktop audio editor and DSP laboratory**. It must run entirely on the user's computer. There is no web server, no React frontend, no FastAPI backend, no database, and no external/hosted inference.

The goal is not merely to make an attractive audio player. The application must contain **real, mathematically meaningful DSP implementations** that can be demonstrated and explained in a Signals & Systems course.

---

# 1. Core Technology Stack

Use the following stack unless there is a strong technical reason not to:

### GUI

* Python
* PyQt6

### Visualization

* PyQtGraph
* Qt widgets/layouts where appropriate

### DSP

* NumPy
* SciPy
* Librosa where useful
* PyWavelets for optional wavelet denoising

### Audio I/O

* SoundFile
* sounddevice for microphone/live audio
* FFmpeg only when necessary for additional audio-format support

Do NOT introduce:

* React
* Vite
* FastAPI
* Flask
* Node.js
* PostgreSQL
* MongoDB
* cloud APIs
* hosted inference APIs
* unnecessary web technologies

The application should be a normal Python desktop application.

---

# 2. Most Important Development Rule

## DO NOT IMPLEMENT THE WHOLE PROJECT AT ONCE.

Work **slowly, incrementally, and carefully**.

Before implementing anything:

1. Inspect the existing repository.
2. Understand what files already exist.
3. Do not overwrite working code unnecessarily.
4. Determine whether the repository is empty, partially implemented, or already contains a project.
5. Preserve useful existing work.
6. Identify dependencies and environment assumptions.
7. Create a clean architecture before implementing major features.

Then implement the project in **small phases**.

After each phase:

1. Check imports.
2. Check syntax.
3. Run relevant tests.
4. Verify that the application still starts.
5. Fix errors before continuing.
6. Do not silently skip broken functionality.
7. Do not move to the next major feature while the current feature is fundamentally broken.

If something is uncertain, inspect the code and documentation rather than guessing.

---

# 3. Project Goals

SonicCraft should eventually support:

1. Basic Audio Editing
2. Volume and Fade
3. Equalizer
4. Noise Removal with multiple algorithms
5. FFT Spectrum Analysis
6. Spectrogram
7. Spectrogram modification
8. Spectrogram → Audio reconstruction
9. Live Spectrogram
10. Optional Signals & Systems laboratory demonstrations

The project should prioritize **correct DSP implementation and reliability over excessive UI decoration**.

---

# 4. Recommended Project Architecture

Create a modular structure similar to:

```text
SonicCraft/
│
├── main.py
├── requirements.txt
├── README.md
│
├── app/
│   ├── __init__.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── waveform_widget.py
│   │   ├── spectrum_widget.py
│   │   ├── spectrogram_widget.py
│   │   ├── controls.py
│   │   └── dialogs.py
│   │
│   ├── dsp/
│   │   ├── __init__.py
│   │   ├── editing.py
│   │   ├── volume.py
│   │   ├── filters.py
│   │   ├── equalizer.py
│   │   ├── noise_reduction.py
│   │   ├── fft.py
│   │   ├── stft.py
│   │   ├── reconstruction.py
│   │   └── sampling.py
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── writer.py
│   │   └── player.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── audio_data.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── tests/
│   ├── test_editing.py
│   ├── test_volume.py
│   ├── test_filters.py
│   ├── test_fft.py
│   ├── test_stft.py
│   └── test_reconstruction.py
│
└── assets/
```

You may modify this structure if the repository already has a sensible architecture.

Do not create unnecessary layers merely for the sake of abstraction.

---

# 5. Central Audio Representation

Create a clear internal representation for loaded audio.

For example:

```python
class AudioData:
    samples
    sample_rate
    channels
    duration
    filename
```

Use NumPy arrays internally.

Prefer:

```text
float32
```

or

```text
float64
```

for DSP processing.

Do not repeatedly convert between incompatible representations.

Support:

* mono
* stereo

Do not silently destroy stereo information.

If a DSP operation requires mono, explicitly handle that conversion and document it.

Always preserve the sample rate unless the operation intentionally changes it.

---

# 6. Audio Loading and Saving

Implement audio loading before implementing complicated DSP.

The application should be able to:

* Open an audio file
* Display filename
* Display duration
* Display sample rate
* Display number of channels
* Display number of samples
* Play the audio
* Stop playback
* Save processed audio

Use SoundFile where appropriate.

Avoid loading huge files into unnecessarily duplicated arrays.

When saving:

* prevent clipping
* use an appropriate numeric range
* preserve sample rate
* preserve channel structure when possible

---

# 7. Waveform Editor

Create a waveform visualization using PyQtGraph.

The waveform should:

* display the audio amplitude over time
* have a time axis
* support zooming where practical
* allow the user to select a region
* visually distinguish the selected region

Do not render an enormous number of points if unnecessary.

For long audio files, create a downsampled representation for visualization while keeping the original audio data untouched.

The waveform display is a visualization layer. It must not modify the underlying signal.

---

# 8. Basic Audio Editing

Implement these operations as actual sample-domain operations.

## Trim

Given:

```text
start_time
end_time
```

convert time to samples:

$$
n = t f_s
$$

Then retain only the selected sample range.

## Cut/Delete

Remove a selected region from the signal.

## Reverse

Implement:

$$
y[n] = x[N-1-n]
$$

## Normalize

Normalize the signal without introducing clipping.

## Silence

Replace a selected region with zeros.

For example:

$$
y[n] = 0
$$

for the selected interval.

These must operate on the actual NumPy audio array.

Do NOT simulate editing by merely changing the waveform display.

---

# 9. Volume and Fade

Implement volume scaling:

$$
y[n] = A x[n]
$$

where `A` is controlled by the user.

Provide a sensible UI such as:

* percentage
* multiplier
* dB

If dB is supported:

$$
A = 10^{G_{dB}/20}
$$

Implement:

### Fade In

$$
y[n] = a[n]x[n]
$$

where:

$$
a[n]:0\rightarrow1
$$

### Fade Out

$$
a[n]:1\rightarrow0
$$

Allow the user to choose the fade duration.

Prevent clipping where appropriate.

---

# 10. Equalizer

This is an important feature.

Implement real digital filters rather than simply changing FFT visualization.

Support at minimum:

* Low-pass
* High-pass
* Band-pass
* Band-stop

Prefer SciPy's stable second-order-section implementation:

```python
scipy.signal.butter()
scipy.signal.sosfilt()
```

Avoid unstable filter implementations when SOS is appropriate.

The UI should allow the user to specify relevant frequencies.

Also provide a **frequency-response visualization**.

Use:

```python
scipy.signal.sosfreqz()
```

where appropriate.

The project should be able to explain the relationship:

$$
y[n] = x[n] * h[n]
$$

and:

$$
Y(e^{j\omega})
=
X(e^{j\omega})H(e^{j\omega})
$$

The UI should make this relationship demonstrable.

---

# 11. Multi-Band Equalizer

After the basic filters work correctly, implement a practical multi-band EQ.

Possible bands:

```text
60 Hz
120 Hz
250 Hz
500 Hz
1 kHz
2 kHz
4 kHz
8 kHz
16 kHz
```

Do not blindly stack filters if that creates poor numerical behavior.

Use an appropriate design.

The user should be able to increase/decrease the gain of selected frequency bands.

Display the resulting frequency response.

---

# 12. Noise Removal

Noise removal must contain **multiple actual algorithms**.

Do not create buttons that all call the same function.

At minimum implement:

### Algorithm 1 — Frequency Filtering

Use:

* low-pass
* high-pass
* band-pass

depending on the noise characteristics.

### Algorithm 2 — Spectral Subtraction

Pipeline:

```text
Noisy audio
    ↓
STFT
    ↓
Estimate noise spectrum
    ↓
Subtract estimated noise
    ↓
Apply magnitude floor
    ↓
Restore phase
    ↓
Inverse STFT
    ↓
Cleaned audio
```

A noise-only section should ideally be selectable by the user.

For example:

```text
Noise profile: first 2 seconds
```

The implementation should estimate the noise spectrum from that region.

### Algorithm 3 — Wiener Filtering

Implement a real Wiener-style approach using appropriate signal/noise power estimates.

### Optional Algorithm 4 — Wavelet Denoising

If time permits, use PyWavelets.

Do not prioritize this over the first three algorithms.

---

# 13. FFT Spectrum Analyzer

Implement real FFT analysis.

Use:

```python
numpy.fft.rfft
```

or:

```python
scipy.fft.rfft
```

with the corresponding frequency bins.

For a signal sampled at:

$$
f_s
$$

calculate frequency bins correctly.

Display:

* frequency
* magnitude
* dB magnitude
* dominant frequency

The user should be able to analyze either:

* the complete signal
* or a selected waveform region

Prefer a logarithmic frequency axis when useful, while retaining a sensible linear option.

---

# 14. FFT Verification

Create automated tests using known signals.

For example, generate:

$$
x[n] = \sin(2\pi f_0 n/f_s)
$$

and verify that the FFT peak occurs near:

$$
f_0
$$

Test several frequencies.

Do not consider FFT complete until this test passes.

---

# 15. Spectrogram

Implement a real Short-Time Fourier Transform.

Use:

```python
scipy.signal.stft
```

or an equivalent well-tested implementation.

Provide controls for:

* FFT size
* hop size
* window
* frequency range
* magnitude/dB display

A reasonable initial configuration is:

```text
window = Hann
n_fft = 2048
hop = 512
```

but make these configurable where practical.

Display:

```text
Time →
Frequency ↑
Magnitude / dB
```

Use PyQtGraph or another appropriate Qt-compatible plotting method.

---

# 16. Spectrogram Modification

Allow the user to modify the time-frequency representation.

Possible operations:

* frequency masking
* time masking
* frequency-band attenuation
* frequency-band amplification
* thresholding

Example:

```text
Remove 4–6 kHz
```

should actually modify the STFT magnitude rather than merely changing the displayed image.

Keep the complex STFT internally:

```text
Z = magnitude × phase
```

Do not discard phase unnecessarily.

---

# 17. Spectrogram → Audio Reconstruction

This is a major feature.

Pipeline:

```text
Audio
  ↓
STFT
  ↓
Complex spectrogram
  ↓
Modify magnitude
  ↓
Preserve phase
  ↓
Inverse STFT
  ↓
Audio
```

Use:

```python
scipy.signal.istft()
```

or an equivalent reliable method.

The reconstructed audio should be playable and savable.

Explain in code comments and documentation that a magnitude-only spectrogram does not generally contain enough information for exact reconstruction.

If phase has been discarded, optionally support Griffin-Lim reconstruction.

Do not claim perfect reconstruction when phase information has been lost.

---

# 18. Reconstruction Testing

Create a test:

```text
original audio
    ↓
STFT
    ↓
ISTFT
    ↓
reconstructed audio
```

Compare original and reconstructed signals.

Use an appropriate numerical tolerance.

Account for:

* boundary effects
* padding
* length differences of a few samples

Do not require exact bit-for-bit equality.

---

# 19. Live Spectrogram

Implement real-time microphone input.

Use a suitable local audio library such as:

```text
sounddevice
```

or Qt's audio facilities if they provide a cleaner implementation.

Architecture:

```text
Microphone
    ↓
Audio callback / input stream
    ↓
Audio buffer
    ↓
FFT / STFT
    ↓
Spectrogram history
    ↓
PyQtGraph
```

The spectrogram should scroll continuously.

Provide:

* Start
* Stop
* FFT size
* frequency range where practical
* sensitivity/scale where practical

Do not send microphone data through a web server.

Everything must remain local.

Pay attention to thread safety.

The audio callback must not perform expensive GUI operations directly.

Use an appropriate buffer/queue mechanism between the audio thread and GUI thread.

---

# 20. Optional Signals & Systems Laboratory

After the core audio editor is stable, optionally create a DSP Lab section.

Possible demonstrations:

### Sampling

Show:

$$
f_s > 2f_{max}
$$

and what happens when the sampling rate is too low.

### Aliasing

Generate a sinusoid above the Nyquist frequency and demonstrate its apparent aliased frequency.

### Convolution

Allow the user to generate two discrete signals and calculate:

$$
y[n] = x[n] * h[n]
$$

Display:

* x[n]
* h[n]
* y[n]

### LTI System

Demonstrate an input signal passing through an impulse response.

This section is optional and must NOT delay the core audio editor.

---

# 21. Undo / Redo

If practical, implement a simple non-destructive operation history.

For example:

```python
operations = [
    {"type": "trim", ...},
    {"type": "volume", ...},
    {"type": "lowpass", ...}
]
```

However, do not over-engineer this.

If a simple snapshot-based undo system is more reliable for the project, use that.

Correctness is more important than architectural sophistication.

---

# 22. GUI Design

Create a professional but simple desktop UI.

Current desktop layout (implemented; see the dated audit for evidence):

```text
┌──────────────────────────────────────────────────────────────┐
│ SonicCraft                                                   │
├──────────────────────────────────────────────────────────────┤
│ File   Edit   Effects   Analysis   View   Help                 │
├──────────────────────────────────────────────────────────────┤
│ Open  Export  Undo  Redo          Play/Pause  Stop             │
├──────────────────────────────────────────────────────────────┤
│ Tool Library        │              WAVEFORM                   │
│ Category → Feature  │                                        │
│ Back / All tools    ├────────────────────────────────────────┤
│                     │ Time / Selection                       │
│ Editing and effect  ├────────────────────────────────────────┤
│ controls            │ FFT / Spectrogram / Live Spectrogram    │
│                     │ / Filter response                      │
│ Reset audio         │                                        │
├──────────────────────────────────────────────────────────────┤
│ Status: filename | sample rate | channels | duration        │
└──────────────────────────────────────────────────────────────┘
```

Do not make the UI excessively complicated.

Every major feature should be reachable without navigating through unnecessary dialogs.

---

# 23. Keep DSP Separate From GUI

This is extremely important.

Do NOT put DSP mathematics directly inside button-click handlers.

Bad:

```python
def on_fft_button_clicked():
    # 100 lines of FFT processing here
```

Prefer:

```python
def on_fft_button_clicked():
    result = calculate_fft(audio)
    self.spectrum_widget.set_data(result)
```

with:

```python
# app/dsp/fft.py
def calculate_fft(audio, sample_rate):
    ...
```

This allows:

* testing
* debugging
* reuse
* clearer course demonstration

---

# 24. Error Handling

Handle common errors gracefully:

* no audio loaded
* invalid audio file
* unsupported format
* empty selection
* invalid time range
* invalid frequency
* frequency above Nyquist
* microphone unavailable
* playback failure
* save failure
* malformed parameters

Never let ordinary user mistakes crash the application.

Show useful error messages.

---

# 25. Nyquist Validation

Whenever the user specifies a frequency, validate:

$$
0 < f < \frac{f_s}{2}
$$

For example, if:

```text
sample_rate = 44100 Hz
```

then Nyquist frequency is:

```text
22050 Hz
```

The UI should prevent invalid filter frequencies.

---

# 26. Clipping Protection

After DSP operations, monitor amplitude.

If:

```text
abs(sample) > 1
```

do not blindly allow the output to clip.

Use an appropriate normalization or scaling strategy.

Do not normalize every operation automatically if that would destroy the intended gain effect.

Make the behavior deliberate.

---

# 27. Stereo Processing

For stereo audio:

```text
Left  → process
Right → process
```

where appropriate.

Do not accidentally flatten stereo into mono.

For FFT/spectrogram visualization, provide a sensible option such as:

```text
Left
Right
Mono mix
```

if practical.

---

# 28. Performance

Do not optimize prematurely.

First make the DSP correct.

Then improve performance where necessary.

Avoid:

* unnecessary copies of huge NumPy arrays
* recalculating STFT repeatedly when parameters have not changed
* blocking the GUI during long operations

For expensive processing, consider a Qt worker thread after the basic implementation works.

The GUI should remain responsive during:

* long audio processing
* large FFTs
* STFT
* noise reduction
* file conversion

---

# 29. Testing Strategy

Create unit tests for DSP functions.

At minimum test:

### Editing

* reverse
* trim
* silence
* normalize

### Volume

* unity gain
* amplification
* attenuation

### Filters

Generate known sinusoidal signals and verify expected attenuation/pass behavior.

### FFT

Generate a known sinusoid and verify the dominant frequency.

### STFT

Verify dimensions and frequency/time axes.

### Reconstruction

Verify approximate STFT → ISTFT reconstruction.

Do not rely only on manually opening the GUI.

---

# 30. Course Concept Mapping

Create documentation explaining how SonicCraft demonstrates Signals & Systems concepts.

Include:

| Course Concept              | SonicCraft Feature        |
| --------------------------- | ------------------------- |
| Discrete-time signals       | Digital audio samples     |
| Signal scaling              | Volume                    |
| Time shifting/selection     | Editing                   |
| Time reversal               | Reverse                   |
| LTI systems                 | Digital filters           |
| Convolution                 | Filtering / DSP Lab       |
| Difference equations        | Digital filters           |
| Fourier Transform           | FFT                       |
| Frequency response          | Equalizer                 |
| Sampling theorem            | Sampling Lab              |
| Aliasing                    | Aliasing Lab              |
| STFT                        | Spectrogram               |
| Inverse STFT                | Spectrogram → Audio       |
| Frequency-domain processing | EQ / spectral subtraction |

The README should explain these connections clearly enough for a course presentation.

---

# 31. Documentation

Maintain a useful README containing:

1. Project overview
2. Features
3. Technology stack
4. Installation
5. Running the application
6. Project structure
7. DSP algorithms
8. Signals & Systems concepts demonstrated
9. Testing
10. Known limitations

Also document important mathematical equations.

Do not write meaningless generic documentation.

---

# 32. Dependency Management

Create:

```text
requirements.txt
```

with only dependencies actually used.

Do not add libraries just because they might be useful later.

At minimum, likely dependencies are:

```text
PyQt6
pyqtgraph
numpy
scipy
soundfile
sounddevice
librosa
```

Add:

```text
PyWavelets
```

only when wavelet denoising is implemented.

---

# 33. Implementation Order

Phases 1–7 form the completed core baseline established by the dated audit above.
The approved next order is **7A → 7B → finish 8 → 9 → 10 → 11**, with **12
optional**, followed by **13 acceptance**. Requirements below remain acceptance
targets; their presence alone is not a completion claim. Early-phase restrictions
describe the original bootstrap sequence and do not reset the current project.

## Phase 1 — Foundation

Implement:

* project structure
* requirements
* application entry point
* main window
* basic menu/toolbars
* empty waveform area
* clean startup/shutdown

Test that the application launches.

---

## Phase 2 — Audio I/O

Implement:

* open audio
* metadata
* save audio
* playback
* stop

Test with several audio files.

---

## Phase 3 — Waveform

Implement:

* waveform rendering
* zoom
* selection

Historical Phase 3 sequencing rule: DSP effects were deferred until Phase 4.

---

## Phase 4 — Basic Editing

Implement:

* trim
* cut/delete
* reverse
* normalize
* silence

Test every operation independently.

---

## Phase 5 — Volume/Fade

Implement:

* volume
* fade in
* fade out

Test mathematically.

---

## Phase 6 — Filters / Equalizer

Implement:

* low-pass
* high-pass
* band-pass
* band-stop
* frequency response
* multi-band EQ

Test against known signals.

---

## Phase 7 — Noise Reduction

Implement:

1. filter-based noise reduction
2. spectral subtraction
3. Wiener filtering
4. optional wavelet denoising

Do not start with the complicated algorithms.

---

## Phase 7A — Stereo Channel Workspace

**Planned; next desktop milestone.** Current stereo traces share a waveform
axis, edits process both channels, and there are no independent channel controls.

Implement:

* separate Left and Right waveform lanes with clear labels and shared timing
* linked editing by default and explicit unlinked channel selection/editing
* per-channel gain, mute and solo with visible state
* channel-aware FFT and spectrogram analysis with explicit Left/Right/combined mode
* channel export with an explicit choice of source channel and output format

Acceptance:

* Use distinct known signals in Left/Right to prove unlinked edits change only
  the targeted channel and linked edits affect both as specified.
* Define alignment rules for duration-changing edits so channel lengths remain
  valid and timing is predictable; test mono compatibility and undo/redo/reset.
* Verify gain/mute/solo routing, channel-aware analysis and exported samples
  against the chosen channel; include physical stereo-output validation.

The existing stereo array shape and colored traces are not completion evidence
for this milestone. Phase 8 correctness requirements remain outstanding even
when analysis routing is added here.

---

## Phase 7B — Multitrack Mixing

**Planned; follows 7A.** This is a new desktop milestone. The existing
`mix_audio()` helper is DSP support, not an implemented multitrack workspace.

Implement:

* multiple imported tracks with persistent identity in the working session
* timeline offsets and a clear shared time ruler
* per-track levels, mute and solo
* an explicit common sample-rate policy, with compatible channel layouts and
  validated resampling when needed
* combined playback of the audible tracks with consistent transport position
* protected mixdown export using the existing mixing DSP, with visible clipping
  detection and an explicit headroom/normalization choice before encoding

Acceptance:

* Test known tones/impulses on multiple tracks for accurate offsets, levels,
  mute/solo behavior and output duration, including unequal track lengths.
* Test mismatched sample rates/channel layouts against the documented conversion
  policy; maintain alignment and show actionable errors for unsupported input.
* Verify combined playback and export use the same routing and mix settings;
  check clipping protection, exported sample rate/channels and source preservation.
* Exercise desktop import-to-mixdown flow and physical combined playback before
  calling the milestone fully accepted.

---

## Phase 8 — FFT

**Partial.** Existing plots and known-tone tests do not close the full-selection
truncation and stereo dB/peak-label discrepancies reproduced in the audit above.
Complete whole-signal/selection coverage and consistent channel-aware magnitude,
dB and peak reporting, with regression tests for both reproduced cases.

Implement:

* FFT calculation
* magnitude
* dB
* frequency axis
* dominant frequency
* waveform-region FFT

Add automated tests.

---

## Phase 9 — Spectrogram

**Partial.** File heatmaps, FFT-size/window controls and plot navigation exist.
Finish explicit hop, frequency-range, magnitude/dB controls and spectrogram-region
selection. The bounded display map is not a reconstruction representation.

Implement:

* STFT
* spectrogram visualization
* controls
* zoom/selection

---

## Phase 10 — Spectrogram Editing / Reconstruction

**DSP-only.** Complex STFT/ISTFT and numerical round-trip tests exist. Build the
desktop masking/editing workflow, retain phase, and connect reconstructed audio
to document history, playback and export before accepting this phase.

Implement:

* magnitude modification
* frequency masking
* time masking
* inverse STFT
* audio playback
* audio saving

Test reconstruction.

---

## Phase 11 — Live Spectrogram

**Partial; implemented ahead of sequence.** Start/stop, input buffering, rolling
history and background display transforms exist. Finish planned FFT-size and
frequency-range controls (sensitivity where practical), then validate real
microphone operation and lifecycle behavior on physical devices.

Implement:

* microphone input
* real-time FFT
* scrolling spectrogram
* start/stop
* thread-safe audio processing

---

## Phase 12 — Optional DSP Lab

**DSP-only; optional.** Sampling, aliasing and convolution utilities/tests exist;
the interactive educational workspace remains unimplemented.

Only after everything above works:

* sampling
* aliasing
* convolution
* LTI demonstrations

---

## Phase 13 — Final Integration

**Pending.** Accept the completed 7A/7B desktop workflows and remaining required
Phases 8–11, run integration/regression checks, and verify physical speaker and
microphone operation. Record hardware results separately from simulated-stream
tests. Optional Phase 12 does not block core acceptance.

Check:

* all menus
* all buttons
* file handling
* error handling
* undo/redo if implemented
* playback
* saving
* DSP accuracy
* live spectrogram
* GUI responsiveness

---

# 34. Important Anti-Patterns

Do NOT:

* create fake DSP effects
* generate random FFT data
* display a spectrogram without actually calculating STFT
* make an "equalizer" that only changes colors on the graph
* make noise removal simply reduce volume
* use placeholder buttons and claim the feature is implemented
* hard-code demo audio
* require internet access
* use external APIs
* put the DSP code directly into GUI classes
* rewrite the entire project unnecessarily
* install huge numbers of dependencies
* add a database
* create a web backend

Every implemented feature must actually work.

---

# 35. Code Quality

Prefer simple, readable Python.

Use:

* clear function names
* meaningful variable names
* type hints where useful
* short functions
* comments explaining DSP mathematics
* docstrings for important DSP functions

Do not over-engineer.

Do not introduce complex design patterns unless genuinely useful.

A university student should be able to understand and explain the code.

---

# 36. Mathematical Correctness

This project is being evaluated partly as a Signals & Systems/DSP project.

Therefore, prioritize mathematical correctness over visual appearance.

For each DSP algorithm, ask:

1. What signal is entering the algorithm?
2. What mathematical operation is being performed?
3. What signal comes out?
4. What assumptions are being made?
5. Can the result be verified with a known signal?

If an implementation makes an approximation, document it.

---

# 37. Working Method

For every phase:

```text
Inspect
  ↓
Plan
  ↓
Implement
  ↓
Run
  ↓
Test
  ↓
Fix
  ↓
Verify
  ↓
Continue
```

Do not rush.

If a feature becomes complicated, break it into smaller pieces.

For example:

```text
Spectrogram
    ↓
STFT calculation
    ↓
STFT data validation
    ↓
basic visualization
    ↓
controls
    ↓
modification
    ↓
ISTFT
    ↓
audio output
```

Do not attempt all of these in one giant implementation.

---

# 38. First Task — Historical Bootstrap Instructions

This section records the original empty-repository bootstrap procedure. It has
already been superseded by the dated audit and approved priorities in Section 33;
it is not an instruction to restart the existing project at Phase 1.

Your FIRST response/action should NOT attempt to implement all SonicCraft features.

First:

1. Inspect the repository.
2. Identify existing files.
3. Identify existing code.
4. Determine the current state of the project.
5. Propose the smallest first implementation phase.
6. Implement only that phase.
7. Run tests/checks.
8. Report exactly what was changed.

If the repository is empty, start with:

```text
Phase 1:
- Python project structure
- PyQt6 application
- main window
- menu bar
- toolbar skeleton
- central waveform placeholder
- status bar
- requirements.txt
- README
```

Do NOT implement FFT, EQ, spectrogram, noise reduction, or live microphone input during the first phase.

The goal is to establish a stable foundation first.

---

# 39. Final Principle

Build SonicCraft as a **real DSP application**, not as a UI mockup.

The final project should allow a student to demonstrate:

```text
Audio signal
    ↓
Time-domain operations
    ↓
Filtering / LTI systems
    ↓
Frequency-domain analysis
    ↓
FFT
    ↓
STFT / Spectrogram
    ↓
Frequency-domain modification
    ↓
Inverse STFT
    ↓
Audio
```

and separately:

```text
Microphone
    ↓
Sampling
    ↓
FFT/STFT
    ↓
Live Spectrogram
```

The application should be stable, understandable, mathematically defensible, and easy to demonstrate in a university Signals & Systems presentation.

**Continue from the verified Phase 7 baseline using the approved order in
Section 33, beginning with planned Phase 7A.**
