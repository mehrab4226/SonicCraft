# SonicCraft architecture

## Runtime

`main.py` calls `desktop.main.main()`, creates the Qt application and opens
`MainWindow`. The installed `soniccraft` entrypoint calls the same function.
The icon ships as package data in `desktop/assets/`. There is no server process.

## Feature map

| UI feature | Controller / widget | Signal implementation |
|---|---|---|
| Open/export | `main_window.py`, `document.py` | `audio_io.py` |
| Playback | `audio_engine.Player` | Immutable sample buffer, 10 ms transition crossfade |
| Stereo waveform/selection | `waveform_widget.py` | Bounded min/max envelopes |
| Edit/gain/fade | `effects_panel.py`, `processing.py` | `dsp/effects.py` |
| Filter/EQ | `effects_panel.py`, `processing.py` | `dsp/filters.py` |
| Noise reduction | `effects_panel.py`, `processing.py` | `dsp/noise_reduction.py` |
| FFT | `desktop/analysis.py`, `spectrum_widget.py` | `dsp/transforms.py`, `dsp/analysis.py` |
| Spectrogram | `desktop/analysis.py`, `spectrogram_widget.py` | Windowed FFT amplitudes |
| Spectral mute | `spectrogram_widget.py`, `processing.mask_spectrum` | STFT coefficient mask and inverse STFT |
| Live input/recording | `audio_engine.Microphone`, `main_window.py` | Queued input blocks and display worker |
| Mixer | `mixer_widget.py` | `dsp/effects.mix_audio`, `dsp/sampling.resample_audio` |
| Image synthesis | `main_window.import_image_dialog`, `main_window._load_image_audio` | `dsp/spectrogram_image.py`, `transforms.image_to_audio`, Griffin-Lim |
| Reset/history | `document.py`, feature reset handlers | Snapshot replacement and parameter defaults |

## Document ownership

`AudioData` copies finite mono/stereo samples, validates the sample rate, and
marks its array read-only. `Document` keeps the original, committed and saved
snapshots plus undo/redo stacks. History is bounded by 20 entries and 128 MiB.
The original snapshot remains available even when old undo entries expire.

Apply commits one edit. Export writes the committed snapshot atomically and only
marks it saved if the output did not require scaling. A new mixdown, recording or
synthesized clip starts unsaved. Replacement paths protect existing unsaved edits.

Tool reset restores that feature's defaults and invalidates its owned preview.
Master reset restores the original audio, clears previews/profile, and resets
all parameters. It preserves mixer track imports and exported files.

## Background work and playback

`jobs.Job` executes a callable in QThread and reports completion/errors to Qt.
Opening, saving, effects, spectral edits, mixdown and image synthesis use the main
job slot. Busy controls prevent conflicting document mutations.

Live effect requests coalesce on an 80 ms timer. Workers process committed samples
rather than accumulating previews. A generation check rejects stale results.
The audio callback reads the published immutable buffer, preserving playback
position and applying a 10 ms crossfade. It never reads Qt controls. Preview
output clips to full scale while leaving document samples intact.

Short FFT selections run immediately. Long selections use an independent worker,
with generation checks and one pending latest request. The 131072-sample maximum
window retains the original sample rate and Nyquist limit. Overlapping windows
cover the whole selection and their squared amplitudes average before taking the
square root. The plotted channel average is computed before converting to dB,
matching dominant-frequency detection.

File/live spectrograms analyze all windows at a quarter-window hop. If the image
would exceed its column limit, peak magnitudes from nearby frames share a display
column. Display compression does not skip input windows. Spectral reconstruction
uses its own complete STFT, with a memory guard, and honors the displayed FFT size,
window and selected channel. Selection changes clear stale maps.

## Recording and mixing

Image import sends the chosen file directly to a background worker without a
settings dialog. Maximum RGB-channel brightness maps to magnitude, time runs
left to right, and frequency runs bottom to top from zero to Nyquist. Image
width determines duration at a 512-sample hop, capped at 2,048 time columns.
The worker reconstructs phase with 64 Griffin-Lim iterations, peak-normalizes to
0.95, and generates the display. Output is mono and unsaved. Both file and live
spectrograms use green intensity scales with time on X and frequency on Y.
The DSP helper retains optional calibration arguments for numerical tests;
the desktop flow uses automatic defaults. Source phase and absolute loudness
are unavailable in ordinary plot images.

The microphone callback queues blocks with a bounded queue. A timer consumes them
for an eight-second display history. Optional recording appends blocks without
repeatedly copying the growing recording and stops at 64 MiB of stored samples.
Loading the recording requires the user's choice and protects unsaved edits.

Each mixer track retains its source rate. Mixdown converts tracks to the first
track's rate with polyphase resampling, then applies offsets, volume and mute.
Mono tracks broadcast to stereo when required. Output is peak-scaled only if the
sum exceeds full scale. Oversized timelines fail before output allocation.
Removing a mixer row releases its track reference.

## Tests

Tests use known signals for frequency, amplitude, reconstruction, channel isolation,
noise-profile selection, resampling and transient visibility. Qt tests exercise
navigation, live preview/reset behavior, stale jobs, document replacement, export
and lifecycle. Audio stream tests inject simulated drivers. Actual device behavior
must be checked on the evaluation laptop.

## Spectrogram PNG export and restoration

SpectrogramData retains the analyzed source samples independently of the bounded
display grid. PNG exports include a private ancillary scAu chunk containing a
versioned header and zlib-compressed little-endian float64 audio. Import checks
for this data before pixel synthesis and restores it without normalization or
resampling. CRC, dimensions, finite samples and decompression size are checked;
damaged embedded audio fails instead of silently producing pixel-derived noise.
Writes replace the destination atomically. This is an audio-carrying PNG archive,
not an inverse transform of the graph screenshot. Source audio is capped at
256 MiB. Selection/channel scope matches the generated spectrogram.
