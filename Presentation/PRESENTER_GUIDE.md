# SonicCraft: presentation guide

The deck returns to the original structure: **13 main slides and 13 Q&A references**. Feature explanations are now shorter. Present slides 1-13 during the six-minute slot and use the appendix only for questions.

## Timing for two presenters

| Slides | Presenter | Time |
|---|---|---|
| 1-3: introduction, motivation, architecture | Mehrab | 50 seconds |
| 4-6: waveform, gain, filters | Mehrab | 65 seconds |
| 7-10: EQ, FFT, spectrogram, noise reduction | Mahi | 95 seconds |
| 11: preview, commit and results | Mahi | 25 seconds |
| 12: live demonstration | Both | 80 seconds |
| 13: closing | Mahi | 5 seconds |

Total: **5:20**, leaving 40 seconds within the six-minute limit. The two-minute Q&A is separate.

## Short feature explanations

- **Waveform:** Select the part of the audio to edit. Time maps to a sample position.
- **Gain:** Make audio louder or quieter. This is amplitude scaling.
- **Filters:** Keep some frequencies and reduce others. The frequency response shapes the sound.
- **Equalizer:** Adjust bass, midrange and treble. Each filter band controls part of the spectrum.
- **FFT:** See which frequencies are present. Fourier analysis breaks sound into frequency components.
- **Spectrogram:** See how frequencies change over time. We analyze short sections of the sound.
- **Noise reduction:** Estimate the background noise, then reduce it in the spectrum.

The equations are visual theory anchors. Do not read or derive each equation during the timed presentation. Point to the graph and explain the effect in plain language.

## Other slides

**Architecture:** PyQt6 handles controls, NumPy and SciPy perform processing, and sounddevice plays audio. Effect previews run in a worker. Apply creates an undoable edit in the document. SoundFile handles import and export.

**Preview and results:** Parameter changes preview during playback. A 10 ms crossfade reduces discontinuities when buffers switch. The tool reset clears its settings and current preview. The main reset restores the original audio and all tool defaults. The current test suite passes 77 tests.

## Eighty-second demonstration

Use `Presentation/demo/SonicCraft_demo_16k.wav`, a generated six-second stereo clip. Rehearse these steps before the session.

1. **0-10 s, Mehrab:** Open and play the clip.
2. **10-25 s, Mehrab:** Move the 1000 Hz EQ band to about +6 dB while playing, then Apply EQ. Restart playback if needed.
3. **25-40 s, Mehrab:** Change a band, then Reset EQ. Explain that the applied edit remains. Use Reset audio to restore the source.
4. **40-65 s, Mahi:** Select 0-0.7 seconds and capture a noise profile. Select all. Preview spectral subtraction at strength 1.5, then Apply.
5. **65-80 s, Mahi:** Generate the spectrogram and export WAV. Return to the Questions slide.

If time is short, explain export without opening the save dialog. Test speakers and projector beforehand. Both members should know the complete project.

## Q&A references

A1 Sample editing; A2 Fades; A3 Normalization; A4 Mixing; A5 Spectral editing; A6 Image-to-audio; A7 Noise methods; A8 Live spectrogram; A9 Preview internals; A10 Sampling; A11 Measurements; A12 Limitations; A13 Sources.

Important distinctions: Apply commits audio in the app; Export writes a file. A local reset does not undo already-applied effects. Live preview includes background processing delay. Synthetic noise results do not establish general speech quality. Tests simulate audio streams and do not replace a physical hardware check.

Long selections use averaged FFT windows at the original sample rate. Mixer inputs are resampled automatically. Practical limits include in-memory audio, processing delay and possible noise-reduction artifacts; details are in A12. The clean reference WAV in `Presentation/demo/` is available for comparison with the noisy demonstration clip.

## Submission and rebuilding

Put the PDF on the teacher's PC before 2:30 PM. Submit the repository link and slides by Tuesday, 29 September 2026, following the instructor's Moodle link.

Run `.\.venv\Scripts\python.exe Presentation/build_presentation.py` to rebuild the PDF. Slide content lives in `Presentation/presentation_slides.py`. Reproducible plots and demo audio come from `Presentation/prepare_presentation_assets.py`.
