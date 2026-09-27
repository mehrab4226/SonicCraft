# SonicCraft presentation guide

The PDF has **14 light-themed slides** for a two-person team. The required
background topics have dedicated, explicit headings before the feature slides.

## Requirement map

| Requirement | Slide |
|---|---|
| Motivation and problem addressed | 2: Motivation and problem |
| Overall approach | 3: Overall approach |
| Architecture and design | 4: Architecture and design |
| Relevant theory or concepts | 5: Relevant theory and concepts |
| Features and functionality | 6-12: Feature sequence |
| Important implementation decisions | 4 and 13: Workers, snapshots and preview/commit separation |
| Final result | 13: From preview to finished audio, followed by the live demo |

Slide 14 closes with the repository. There is no Q&A slide.

## Six-minute run of show

| Slides / action | Presenter | Target |
|---|---|---:|
| 1-2: introduction, motivation and problem | Mehrab | 30 s |
| 3: overall approach | Mehrab | 15 s |
| 4: architecture and design | Mehrab | 25 s |
| 5: relevant theory and concepts | Mehrab | 25 s |
| 6-8: editing, filter and equalizer | Mehrab | 55 s |
| 9-12: noise reduction and analysis | Mahi | 80 s |
| 13: final workflow and reset scopes | Mahi | 25 s |
| Live demonstration, with no extra slide | Both | 75 s |
| 14: source code | Mahi | 10 s |

Total: **5:40**, leaving 20 seconds within the six-minute presentation and demo
limit. The two-minute Q&A follows. Both members should understand the whole app.

## Opening talking points

- **Slide 2:** We wanted to learn DSP by hearing and seeing its effects. Noise and
  uneven levels make recordings harder to use, so the editor combines analysis
  with practical editing tools.
- **Slide 3:** Inspect a selected region, preview a targeted change, then apply
  and compare it before exporting. This is the overall problem-solving approach.
- **Slide 4:** PyQt6 provides controls and views, NumPy/SciPy process samples, and
  sounddevice plays the buffer. The document keeps the original and edit snapshots.
  Background workers keep processing from blocking the interface.
- **Slide 5:** Gain and fades change sample amplitude. FFT reveals frequency
  components. Filters and EQ reshape those components. Windowed FFT analysis
  tracks changes through time and supports noise reduction. No formulas needed.
- **Slide 13:** Preview remains separate from committed edits. Apply saves an
  undoable snapshot; Export writes a file. Tool reset clears one tool, whereas
  Reset audio restores the original recording.

## Say only the core idea on each feature slide

- **Edit & Dynamics:** Select part of the waveform. Trim, change its level, or fade its edges.
- **Frequency filter:** Keep one frequency range and reduce another. The graph compares low-pass and high-pass settings.
- **9-band equalizer:** Change specific bands. The graph shows a bass boost and an upper-mid cut; the other bands remain flat.
- **Noise reduction:** Capture a noise-only sample and use it to attenuate similar background noise elsewhere.
- **Spectrum analyzer:** An FFT exposes the strongest frequencies in a selection.
- **Spectrogram:** Green horizontal bands show when each note occurs and at what frequency.
- **Live spectrogram:** The same analysis refreshes as microphone blocks arrive; the lower graph shows the incoming waveform.

The figures are deterministic examples produced from the same processing code as the app. The noise example uses synthetic noise, and the live graph is an illustration of the rolling view rather than a microphone capture.

## Live demonstration

Use `Presentation/demo/SonicCraft_demo_16k.wav`, a generated six-second stereo clip. Open the application before presenting and rehearse the full run on the evaluation laptop.

1. Open the demo and play it. Show the left and right waveform lanes.
2. Move the 1000 Hz EQ slider during playback, then press **Apply EQ**. Mention that Apply saves this change inside the app.
3. Change a band again, then use **Reset EQ** to clear only those uncommitted settings. Use **Reset audio** to restore the original clip.
4. Select the 0-0.7 second noise-only section, capture a noise profile, select all, and show spectral subtraction preview. Apply it.
5. Open the spectrogram and point out time on the horizontal axis and frequency on the vertical axis. Export WAV if time allows.

Pause playback before switching to a device that is unavailable in the room. The live microphone feature can be explained from slide 12 if the lab PC has no input device.

## Useful Q&A facts

Apply commits an undoable change to the document; Export writes a file. A tool reset clears that tool's parameters and current preview, while Reset audio restores the original recording and all tool defaults. Live preview renders in a worker and playback crossfades between buffers for 10 ms. Long selections use overlapping FFT windows at the original sample rate. Mixdown resamples tracks with different rates. Ordinary-image synthesis estimates missing phase. Newly exported spectrogram PNGs instead carry source audio and restore it exactly; this is embedded audio, not recovery from graph pixels. The clean reference WAV in `Presentation/demo/` can be used to compare the synthetic noise example.

## Submission and rebuilding

Put the PDF on the teacher's PC before 2:30 PM. Submit the repository link and slides by Tuesday, 29 September 2026, through Moodle.

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Presentation/requirements.txt
.\.venv\Scripts\python.exe Presentation/prepare_presentation_assets.py
.\.venv\Scripts\python.exe Presentation/build_presentation.py
```
