import { Pause, Play, Repeat2, SkipBack, SkipForward, Volume2 } from 'lucide-react';
import { IconButton } from '../../../shared/components/IconButton';
import { formatDb, formatTime } from '../../../shared/lib/format';
import type { EditorController } from '../../editor/hooks/useEditor';

export function TransportBar({ editor }: { editor: EditorController }) {
  const disabled = !editor.tracks.length || !!editor.busy;
  return <footer className="transport">
    <div className="transport-time"><strong>{formatTime(editor.position)}</strong><span>/ {formatTime(editor.duration)}</span></div>
    <div className="transport-controls">
      <IconButton label="Loop playback (planned)" disabled><Repeat2 /></IconButton>
      <IconButton label="Go to start" disabled={disabled} onClick={() => void editor.seek(0)}><SkipBack /></IconButton>
      <button type="button" className="play-button" aria-label={editor.playing ? 'Pause' : 'Play'} disabled={disabled} onClick={() => void editor.togglePlayback()}>{editor.playing ? <Pause /> : <Play />}</button>
      <IconButton label="Go to end" disabled={disabled} onClick={() => void editor.seek(editor.duration)}><SkipForward /></IconButton>
    </div>
    <div className="transport-volume"><Volume2 /><input aria-label="Master volume dB" type="range" min="-60" max="6" step="1" value={editor.masterDb} onChange={event => editor.setMasterDb(Number(event.target.value))} /><span>{editor.masterDb} dB</span></div>
    <input className="transport-seek" aria-label="Playback position" type="range" min="0" max={editor.duration || 1} step="0.01" value={editor.position} disabled={disabled} onChange={event => void editor.seek(Number(event.target.value))} />
    <div className="output-readout" aria-label="Master output peak"><span>Output {formatDb(editor.peak)}</span>{editor.peak >= 1 && <strong>Clipping</strong>}</div>
  </footer>;
}
