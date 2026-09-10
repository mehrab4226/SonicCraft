export type Theme = 'dark' | 'light';

export type EditorTool = 'select' | 'trim' | 'split' | 'fade';

export interface AudioTrack {
  id: string;
  name: string;
  color: string;
  muted: boolean;
  solo: boolean;
  gainDb: number;
  asset: AudioAsset;
}

export interface AudioInspection {
  metadata: {
    sample_rate: number;
    frames: number;
    channels: number;
    duration_seconds: number;
    format: string;
    subtype: string;
  };
  levels: { peak: number[]; rms_dbfs: number[]; clipping_fraction: number[] };
  waveform: { times: number[]; minimum: number[][]; maximum: number[][] };
}

export interface AudioAsset {
  id: string;
  blob: Blob;
  buffer: AudioBuffer;
  inspection: AudioInspection;
}

export interface GainFadeParameters {
  gain_db: number;
  fade_in_seconds: number;
  fade_out_seconds: number;
  curve: 'linear' | 'equal_power' | 'exponential';
}
