import type { AudioTrack } from '../../shared/types/editor';
import { audibleTracks, projectDuration } from '../editor/state/editorReducer';

/** Owns browser resources. Audio buffers are immutable and shared across history. */
export class AudioEngine {
  private context?: AudioContext;
  private master?: GainNode;
  private analyser?: AnalyserNode;
  private sources: Array<{ source: AudioBufferSourceNode; gain: GainNode }> = [];
  private startedAt = 0;
  private offset = 0;
  private end = 0;
  private generation = 0;
  private volumeDb = 0;
  playing = false;

  private initialize() {
    if (!this.context || this.context.state === 'closed') {
      this.context = new AudioContext();
      this.master = this.context.createGain();
      this.master.gain.value = 10 ** (this.volumeDb / 20);
      this.analyser = this.context.createAnalyser();
      this.analyser.fftSize = 2048;
      this.master.connect(this.analyser);
      this.analyser.connect(this.context.destination);
    }
    return this.context;
  }

  async decode(blob: Blob) {
    const context = this.initialize();
    try {
      return await context.decodeAudioData(await blob.arrayBuffer());
    } catch {
      throw new Error('This browser cannot play this audio format. Convert the file to WAV and retry.');
    }
  }

  get position() {
    if (!this.playing || !this.context) return this.offset;
    return Math.min(this.end, this.offset + this.context.currentTime - this.startedAt);
  }

  pause() {
    this.offset = this.position;
    this.playing = false;
    this.generation++;
    for (const { source, gain } of this.sources) {
      source.stop();
      source.disconnect();
      gain.disconnect();
    }
    this.sources = [];
  }

  seek(seconds: number) {
    this.pause();
    this.offset = Math.max(0, seconds);
  }

  async play(tracks: AudioTrack[], seconds = this.position) {
    this.pause();
    const version = this.generation;
    const context = this.initialize();
    await context.resume();
    if (version !== this.generation) return;
    this.end = projectDuration(tracks);
    if (!this.end) return;
    this.offset = seconds >= this.end ? 0 : Math.max(0, seconds);
    this.startedAt = context.currentTime;
    for (const track of audibleTracks(tracks)) {
      if (this.offset >= track.asset.buffer.duration) continue;
      const source = context.createBufferSource();
      const gain = context.createGain();
      source.buffer = track.asset.buffer;
      gain.gain.value = 10 ** (track.gainDb / 20);
      source.connect(gain);
      gain.connect(this.master!);
      source.start(this.startedAt, this.offset);
      this.sources.push({ source, gain });
    }
    this.playing = true;
  }

  setVolume(db: number) {
    this.volumeDb = db;
    if (this.context && this.master) this.master.gain.setTargetAtTime(10 ** (db / 20), this.context.currentTime, 0.01);
  }

  meter() {
    if (!this.analyser || !this.playing) return 0;
    const samples = new Float32Array(this.analyser.fftSize);
    this.analyser.getFloatTimeDomainData(samples);
    let peak = 0;
    for (const value of samples) peak = Math.max(peak, Math.abs(value));
    return peak;
  }

  dispose() {
    this.pause();
    this.master?.disconnect();
    this.analyser?.disconnect();
    const context = this.context;
    this.context = undefined;
    this.master = undefined;
    this.analyser = undefined;
    if (context && context.state !== 'closed') void context.close();
  }
}
