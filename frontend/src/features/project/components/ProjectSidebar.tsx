import { AudioWaveform, CirclePlus, Layers3 } from 'lucide-react';
import type { CSSProperties } from 'react';
import type { EditorController } from '../../editor/hooks/useEditor';

export function ProjectSidebar({ editor, onImport }: { editor: EditorController; onImport: () => void }) {
  return (
    <aside className="sidebar panel-surface">
      <div className="panel-heading">
        <div><span className="eyebrow">Project · {editor.tracks.length} / 8</span><h2>Audio layers</h2></div>
        <button type="button" className="small-icon-button" aria-label="Add track" disabled={!!editor.busy} onClick={onImport}><CirclePlus /></button>
      </div>
      <div className="track-list">
        {editor.tracks.map(track => (
          <button type="button" className={`track-item ${track.id === editor.selectedId ? 'is-selected' : ''}`} key={track.id} aria-pressed={track.id === editor.selectedId} onClick={() => editor.select(track.id)} disabled={!!editor.busy}>
            <span className="track-icon" style={{ '--track-color': track.color } as CSSProperties}><AudioWaveform /></span>
            <span><strong>{track.name}</strong><small>{track.asset.inspection.metadata.channels === 1 ? 'Mono' : 'Stereo'} · {track.asset.inspection.metadata.sample_rate / 1000} kHz{track.muted ? ' · Muted' : track.solo ? ' · Solo' : ''}</small></span>
          </button>
        ))}
        {!editor.tracks.length && <p className="helper-text">Your imported audio will appear here.</p>}
      </div>
      <div className="sidebar-spacer" />
      <div className="course-card"><span className="course-icon"><Layers3 /></span><div><span className="eyebrow">Signals & systems</span><strong>Amplitude and time domain</strong></div></div>
    </aside>
  );
}
