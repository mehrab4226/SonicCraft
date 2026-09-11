# SonicCraft — PyQt6 DSP Audio Editor

## Verified execution status — 2026-09-11

The desktop direction is confirmed. Phases 1 and 2 are implemented in this pass.
The existing `soniccraft` DSP package is reused in place under `backend/src`.
Retired React/FastAPI source was archived outside the repository before cleanup.
The working tree now contains the desktop application and shared DSP package only.

- [x] Inspected the existing repository and preserved its changes.
- [x] Added the desktop dependency extra and root `main.py` launcher.
- [x] Implemented a PyQt6 main window, menus, toolbar, status bar, and About.
- [x] Added an empty PyQtGraph waveform with real time/amplitude axes.
- [x] Verified native window rendering and automated startup/shutdown.
- [x] Ran DSP, desktop, and installed legacy API tests before cleanup: 26 passing.
- [x] Removed retired web source, HTTP-only dependencies/tests, and generated caches.
- [x] Verified the remaining DSP and desktop suite after cleanup: 19 tests passing.
- [x] Checked Python compilation and installed dependency consistency.
- [x] Fixed and regression-tested Wiener denoising on silence in the reused core.
- [x] Phase 2: connect and verify local open, metadata, playback, stop, and save.
- [ ] Later phases: waveform interaction, editing, effects, analysis, and live audio.

**Desktop audio I/O is wired and covered by workflow tests.** The next implementation
phase can focus on richer waveform interaction, editing, effects, and analysis.

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

Suggested main layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ SonicCraft                                                   │
├──────────────────────────────────────────────────────────────┤
│ File   Edit   Effects   Analysis   Tools                    │
├──────────────────────────────────────────────────────────────┤
│ Open  Save  Undo  Redo  Play  Pause  Stop                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                     WAVEFORM                                 │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Time / Selection                                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│             Current analysis / effect panel                 │
│                                                              │
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

Follow this exact broad order unless repository conditions require a small adjustment.

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

Do not implement DSP effects yet.

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

## Phase 8 — FFT

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

Implement:

* STFT
* spectrogram visualization
* controls
* zoom/selection

---

## Phase 10 — Spectrogram Editing / Reconstruction

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

Implement:

* microphone input
* real-time FFT
* scrolling spectrogram
* start/stop
* thread-safe audio processing

---

## Phase 12 — Optional DSP Lab

Only after everything above works:

* sampling
* aliasing
* convolution
* LTI demonstrations

---

## Phase 13 — Final Integration

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

# 38. First Task

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

**Start by inspecting the repository and implementing only Phase 1. Do not jump ahead.**
