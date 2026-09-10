/** Deterministic PCM WAV generated in memory; no private audio or remote fixtures. */
export function toneWav(seconds = 2, channels = 2) {
  const rate = 8000;
  const frames = Math.round(seconds * rate);
  const data = Buffer.alloc(44 + frames * channels * 2);
  data.write('RIFF', 0); data.writeUInt32LE(data.length - 8, 4); data.write('WAVEfmt ', 8);
  data.writeUInt32LE(16, 16); data.writeUInt16LE(1, 20); data.writeUInt16LE(channels, 22);
  data.writeUInt32LE(rate, 24); data.writeUInt32LE(rate * channels * 2, 28);
  data.writeUInt16LE(channels * 2, 32); data.writeUInt16LE(16, 34);
  data.write('data', 36); data.writeUInt32LE(data.length - 44, 40);
  for (let frame = 0; frame < frames; frame++) {
    for (let channel = 0; channel < channels; channel++) {
      const sample = Math.sin(2 * Math.PI * 440 * frame / rate) * 0.25 * (channel ? 0.5 : 1);
      data.writeInt16LE(Math.round(sample * 32767), 44 + (frame * channels + channel) * 2);
    }
  }
  return { name: 'test-tone.wav', mimeType: 'audio/wav', buffer: data };
}
