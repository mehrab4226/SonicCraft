import { AudioLines, ScanLine, Sparkles, Waves } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { GainFadeParameters } from '../../../shared/types/editor';
import { formatDb } from '../../../shared/lib/format';
import type { EditorController } from '../../editor/hooks/useEditor';

function TrackProcessing({ editor }: { editor: EditorController }) {
  const track = editor.selected!;
  const { metadata, levels } = track.asset.inspection;
  const [name, setName] = useState(track.name);
  const [gain, setGain] = useState(track.gainDb);
  const [fadeIn, setFadeIn] = useState('0');
  const [fadeOut, setFadeOut] = useState('0');
  const [curve, setCurve] = useState<GainFadeParameters['curve']>('equal_power');
  const [start, setStart] = useState('0');
  const [end, setEnd] = useState(String(metadata.duration_seconds));
  useEffect(() => setGain(track.gainDb), [track.gainDb]);
  useEffect(() => setName(track.name), [track.name]);
  const amplitude = Math.max(...levels.peak) * 10 ** (track.gainDb / 20);
  const fadeValid = fadeIn !== '' && fadeOut !== '' && Number.isFinite(+fadeIn) && Number.isFinite(+fadeOut) && Math.min(+fadeIn, +fadeOut) >= 0 && Math.max(+fadeIn, +fadeOut) <= metadata.duration_seconds;
  const startSample = Math.round(+start * metadata.sample_rate);
  const endSample = Math.min(metadata.frames, Math.round(+end * metadata.sample_rate));
  const trimValid = start !== '' && end !== '' && Number.isFinite(+start) && Number.isFinite(+end) && startSample >= 0 && startSample < endSample && +end <= metadata.duration_seconds;
  const commitGain = (value: number) => { if (value !== track.gainDb) editor.updateTrack(track.id, { gainDb: value }); };

  return <>
    <div className="meter-card">
      <div className="meter-heading"><span>Track peak</span><strong>{formatDb(amplitude)}</strong></div>
      <div className="meter"><i style={{ width: `${Math.max(0, Math.min(100, (20 * Math.log10(amplitude || 1e-6) + 60) / 60 * 100))}%` }} /></div>
      <div className="meter-scale"><span>−60</span><span>−30</span><span>0 dBFS</span></div>
      {amplitude >= 1 && <p className="clipping-warning">At or above full scale. Lower gain before export.</p>}
    </div>
    <dl className="audio-metadata"><dt>Format</dt><dd>{metadata.format} / {metadata.subtype}</dd><dt>Sample rate</dt><dd>{metadata.sample_rate.toLocaleString()} Hz</dd><dt>Channels</dt><dd>{metadata.channels}</dd><dt>RMS</dt><dd>{levels.rms_dbfs.map(value => value.toFixed(1)).join(' / ')} dBFS</dd></dl>
    <fieldset disabled={!!editor.busy} className="processing-fields">
      <legend>Selected track</legend>
      <label>Track name<input aria-label="Track name" value={name} maxLength={120} onChange={event => setName(event.target.value)} onBlur={() => { const next = name.trim(); if (next && next !== track.name) editor.updateTrack(track.id, { name: next }); else setName(track.name); }} /></label>
      <label>Track color<input type="color" aria-label="Track color" value={track.color} onChange={event => editor.updateTrack(track.id, { color: event.target.value })} /></label>
      <label>Track gain · {gain} dB<input aria-label="Track gain dB" type="range" min="-60" max="24" step="1" value={gain} onChange={event => setGain(Number(event.target.value))} onPointerUp={event => commitGain(Number(event.currentTarget.value))} onKeyUp={event => commitGain(Number(event.currentTarget.value))} onBlur={event => commitGain(Number(event.currentTarget.value))} /></label>
      <p className="helper-text">Gain scales amplitude: +6 dB is approximately twice the amplitude. Track changes pause playback.</p>
      <label>Fade in (seconds)<input aria-label="Fade in seconds" type="number" min="0" max={metadata.duration_seconds} step="0.01" value={fadeIn} onChange={event => setFadeIn(event.target.value)} /></label>
      <label>Fade out (seconds)<input aria-label="Fade out seconds" type="number" min="0" max={metadata.duration_seconds} step="0.01" value={fadeOut} onChange={event => setFadeOut(event.target.value)} /></label>
      <label>Fade curve<select value={curve} onChange={event => setCurve(event.target.value as GainFadeParameters['curve'])}><option value="equal_power">Equal power</option><option value="linear">Linear</option><option value="exponential">Exponential</option></select></label>
      <button type="button" className="panel-button" disabled={!fadeValid} onClick={() => void editor.applyGainFade({ gain_db: gain, fade_in_seconds: +fadeIn, fade_out_seconds: +fadeOut, curve })}>Apply gain & fades</button>
      {!fadeValid && <p className="clipping-warning">Each fade must fit within the track duration.</p>}
      <p className="helper-text">Applies to this track; Undo restores its previous audio.</p>
    </fieldset>
    <fieldset disabled={!!editor.busy} className="processing-fields">
      <legend>Trim range</legend>
      <label>Start (seconds)<input aria-label="Trim start seconds" type="number" min="0" max={metadata.duration_seconds} step="0.01" value={start} onChange={event => setStart(event.target.value)} /></label>
      <label>End (seconds)<input aria-label="Trim end seconds" type="number" min="0" max={metadata.duration_seconds} step="0.01" value={end} onChange={event => setEnd(event.target.value)} /></label>
      <button type="button" className="panel-button" disabled={!trimValid} onClick={() => void editor.trim(startSample, endSample)}>Keep range</button>
      {!trimValid && <p className="clipping-warning">Choose a non-empty range inside the track.</p>}
    </fieldset>
    <label className="checkbox-label"><input type="checkbox" checked={editor.normalizeExport} disabled={!!editor.busy} onChange={event => editor.setNormalizeExport(event.target.checked)} /> Normalize export to −1 dBFS</label>
    <p className="helper-text">Export includes selected-track and master gain. Mute/solo affect playback only. Mixdown is planned.</p>
  </>;
}

export function EffectsPanel({ editor }: { editor: EditorController }) {
  return <aside className="inspector panel-surface">
    <div className="panel-heading"><div><span className="eyebrow">Selected track</span><h2>Processing</h2></div></div>
    {editor.selected ? <TrackProcessing key={`${editor.selected.id}:${editor.selected.asset.id}`} editor={editor} /> : <p className="helper-text">Import and select a track to adjust its audio.</p>}
    <div className="analysis-heading"><span className="eyebrow">Next milestones</span></div>
    <div className="analysis-grid">
      <button type="button" disabled title="Equalizer UI is planned"><AudioLines /><span><strong>Equalizer</strong><small>Planned</small></span></button>
      <button type="button" disabled title="Noise removal UI is planned"><Sparkles /><span><strong>Noise remover</strong><small>Planned</small></span></button>
      <button type="button" disabled title="FFT spectrum UI is planned"><Waves /><span><strong>FFT spectrum</strong><small>Planned</small></span></button>
      <button type="button" disabled title="Offline, reconstruction, and live spectrogram UIs are planned"><ScanLine /><span><strong>Spectrograms</strong><small>Offline · reconstruction · live — planned</small></span></button>
    </div>
  </aside>;
}
