import { AudioWaveform, MousePointer2, Slice, Trash2, ZoomIn, ZoomOut } from 'lucide-react';
import { useState, type CSSProperties } from 'react';
import { IconButton } from '../../../shared/components/IconButton';
import { formatTime } from '../../../shared/lib/format';
import type { EditorController } from '../hooks/useEditor';
import { Waveform } from './Waveform';

export function EditorWorkspace({ editor, onImport }: { editor: EditorController; onImport: () => void }) {
  const [zoom, setZoom] = useState(1);
  return (
    <section className="workspace">
      <div className="workspace-toolbar panel-surface">
        <div className="tool-group">
          <span className="tool-indicator" title="Click a waveform to select and seek"><MousePointer2 size={17} /> Select</span>
          <IconButton label="Split clips (planned)" disabled><Slice /></IconButton>
        </div>
        <div className="tool-group">
          <IconButton label="Zoom out" disabled={zoom === 1} onClick={() => setZoom(value => Math.max(1, value / 2))}><ZoomOut /></IconButton>
          <span className="zoom-value">{zoom * 100}%</span>
          <IconButton label="Zoom in" disabled={zoom === 8 || !editor.tracks.length} onClick={() => setZoom(value => Math.min(8, value * 2))}><ZoomIn /></IconButton>
        </div>
      </div>
      <div className="timeline panel-surface" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (!editor.busy) void editor.importFiles(Array.from(event.dataTransfer.files)); }}>
        {!editor.tracks.length ? <div className="empty-editor">
          <AudioWaveform size={44} /><h1>Shape your sound.</h1>
          <p>Drop an audio file here, or choose a recording to explore its waveform.</p>
          <button type="button" className="export-button" disabled={!!editor.busy} onClick={onImport}>Import audio</button>
          <small>Mono or stereo · WAV, FLAC, OGG, supported MP3 · up to 32 MiB</small>
        </div> : <div className="timeline-content" style={{ width: `${zoom * 100}%` }}>
          <div className="time-ruler">{Array.from({ length: 7 }, (_, i) => <span key={i}>{formatTime(editor.duration * i / 6)}</span>)}</div>
          {editor.tracks.map(track => (
            <div key={track.id} className={`timeline-track ${track.id === editor.selectedId ? 'is-primary' : ''}`}>
              <div className="track-controls">
                <button type="button" className="track-name" onClick={() => editor.select(track.id)} title={track.name} disabled={!!editor.busy}>{track.name}</button>
                <small>{formatTime(track.asset.buffer.duration)}</small>
                <div>
                  <button type="button" aria-label={`Mute ${track.name}`} aria-pressed={track.muted} disabled={!!editor.busy} onClick={() => editor.updateTrack(track.id, { muted: !track.muted })}>M</button>
                  <button type="button" aria-label={`Solo ${track.name}`} aria-pressed={track.solo} disabled={!!editor.busy} onClick={() => editor.updateTrack(track.id, { solo: !track.solo })}>S</button>
                  <button type="button" aria-label={`Remove ${track.name}`} disabled={!!editor.busy} onClick={() => editor.removeTrack(track.id)}><Trash2 /></button>
                </div>
              </div>
              <div className="track-lane">
                <div className="audio-region" role="button" tabIndex={editor.busy ? -1 : 0} aria-label={`Select waveform ${track.name}`} style={{ width: `${track.asset.buffer.duration / editor.duration * 100}%`, '--track-color': track.color } as CSSProperties}
                  onClick={event => {
                    if (editor.busy) return;
                    editor.select(track.id);
                    const rect = event.currentTarget.getBoundingClientRect();
                    void editor.seek((event.clientX - rect.left) / rect.width * track.asset.buffer.duration);
                  }} onKeyDown={event => { if (!editor.busy && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); editor.select(track.id); } }}>
                  <Waveform color={track.color} waveform={track.asset.inspection.waveform} muted={track.muted} />
                </div>
                <div className="playhead" style={{ left: `${editor.position / editor.duration * 100}%` }} />
              </div>
            </div>
          ))}
          <button type="button" className="add-track-button" disabled={!!editor.busy} onClick={onImport}>+ Add audio track</button>
        </div>}
      </div>
    </section>
  );
}
