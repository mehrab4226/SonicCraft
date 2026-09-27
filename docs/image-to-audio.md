# Convert an image to audio

1. Choose **File > Import Spectrogram Image**.
2. Select an image. Conversion starts automatically.
3. Press **Play** to listen, or **Export audio** to save the result.

## Conversion rules

- Time runs left to right; frequency rises from bottom to top, from 0 to
  22,050 Hz. Saved image orientation is applied before conversion.
- Intensity is the strongest red, green or blue channel, divided by 255.
  Transparent pixels are composited onto black. Black produces silence.
- Brighter marks have greater relative strength within the image. Each resulting
  audio clip is normalized to a peak of 0.95; darkening an entire image does not
  lower the final playback volume.
- With W image columns, duration is max(1, min(W, 2048) - 1) * 512 / 44100
  seconds. Wide images are compressed in time, up to about 23.8 seconds.
- Fine frequency lines and brief events are merged by peak strength when the
  image exceeds the output resolution, so they are not skipped. Their position
  is rounded to the nearest output bin. Smaller images are interpolated.
- A single-row image has uniform intensity across frequency. A single-column
  image has constant intensity through its short output duration.
- Phase is estimated, so the reconstructed waveform is approximate. Borders and
  labels also become sound; printed axes and arbitrary colour scales are not read.

The resulting spectrogram is green, with time on the horizontal axis. No setup
or colour-bar selection screen is used.

## Save a generated spectrogram

After generating a spectrogram from audio, click **Save image** above the graph.
The PNG includes the green graph, axes and colour scale, plus the source audio
stored losslessly inside the file. Opening it in SonicCraft restores the stored
samples, sample rate, channels, duration and volume exactly; it does not estimate
this audio from the displayed pixels. A selected time interval or channel saves
only that analyzed audio. Live spectrograms save the currently displayed buffer.

The graph is 1,600 pixels wide and excludes selection handles. The embedded audio
is independent of that display resolution. These PNGs can be much larger than
ordinary screenshots; source samples are limited to 256 MiB before compression.

Older exports contain only the graph and cannot restore the original song.
Open the original audio and save a new PNG to include the audio. Image editors
and messaging services may remove embedded data; keep the original exported file.
Ordinary images without embedded audio still use the brightness conversion rules
above and are not a way to recover an original recording from a screenshot.
