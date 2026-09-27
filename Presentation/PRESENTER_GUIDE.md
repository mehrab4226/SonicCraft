# SonicCraft presentation guide

The PDF has **12 slides** for a two-person team. The feature sequence follows the app: Edit & Dynamics, Frequency filter, 9-band equalizer, Noise reduction, Spectrum analyzer, Spectrogram, and Live spectrogram. Slide 11 explains preview, Apply and the two reset scopes. Slide 12 points to the repository. There is no scripted Q&A slide.

## Six-minute run of show

| Slides / action | Presenter | Target |
|---|---|---:|
| 1-3: purpose and design | Mehrab | 45 s |
| 4: editing and dynamics | Mehrab | 30 s |
| 5-6: filter and equalizer | Mehrab | 50 s |
| 7-10: noise and analyzers | Mahi | 100 s |
| 11: preview, Apply and reset | Mahi | 25 s |
| Live demonstration, with no extra slide | Both | 75 s |
| 12: source code | Mahi | 10 s |

Total: **5:35**, leaving 25 seconds within the six-minute presentation and demo limit. The two-minute Q&A follows. Each person should be able to explain the whole application.

## Say only the core idea on each feature slide

- **Edit & Dynamics:** Select part of the waveform. Trim, change its level, or fade its edges.
- **Frequency filter:** Keep one frequency range and reduce another. The graph compares low-pass and high-pass settings.
- **9-band equalizer:** Change specific bands. The graph shows a bass boost and an upper-mid cut; the other bands remain flat.
- **Noise reduction:** Capture a noise-only sample and use it to attenuate similar background noise elsewhere.
- **Spectrum analyzer:** An FFT exposes the strongest frequencies in a selection.
- **Spectrogram:** Bright horizontal bands show when each note occurs and at what frequency.
- **Live spectrogram:** The same analysis refreshes as microphone blocks arrive; the lower graph shows the incoming waveform.

The figures are deterministic examples produced from the same processing code as the app. The noise example uses synthetic noise, and the live graph is an illustration of the rolling view rather than a microphone capture.

## Live demonstration

Use `Presentation/demo/SonicCraft_demo_16k.wav`, a generated six-second stereo clip. Open the application before presenting and rehearse the full run on the evaluation laptop.

1. Open the demo and play it. Show the left and right waveform lanes.
2. Move the 1000 Hz EQ slider during playback, then press **Apply EQ**. Mention that Apply saves this change inside the app.
3. Change a band again, then use **Reset EQ** to clear only those uncommitted settings. Use **Reset audio** to restore the original clip.
4. Select the 0-0.7 second noise-only section, capture a noise profile, select all, and show spectral subtraction preview. Apply it.
5. Open the spectrogram and point out time on the horizontal axis and frequency on the vertical axis. Export WAV if time allows.

Pause playback before switching to a device that is unavailable in the room. The live microphone feature can be explained from slide 10 if the lab PC has no input device.

## Useful Q&A facts

Apply commits an undoable change to the document; Export writes a file. A tool reset clears that tool's parameters and current preview, while Reset audio restores the original recording and all tool defaults. Live preview renders in a worker and playback crossfades between buffers for 10 ms. Long selections use overlapping FFT windows at the original sample rate. Mixdown resamples tracks with different rates. Image synthesis estimates missing phase. The clean reference WAV in `Presentation/demo/` can be used to compare the synthetic noise example.

## Submission and rebuilding

Put the PDF on the teacher's PC before 2:30 PM. Submit the repository link and slides by Tuesday, 29 September 2026, through Moodle.

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Presentation/requirements.txt
.\.venv\Scripts\python.exe Presentation/prepare_presentation_assets.py
.\.venv\Scripts\python.exe Presentation/build_presentation.py
```
