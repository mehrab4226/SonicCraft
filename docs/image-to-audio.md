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
Choose a location to save a PNG containing the green graph, time/frequency axes
and current colour scale. The selection rectangle is excluded. Export is 1,600
pixels wide and preserves the graph proportions. This is a picture of the graph,
not a lossless audio file or a calibrated format for importing audio again.
