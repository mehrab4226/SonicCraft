import { ChevronDown, Crosshair, MousePointer2, Scissors, Slice, Sparkles, ZoomIn, ZoomOut } from 'lucide-react';
import type { EditorTool } from '../../../shared/types/editor';
import { IconButton } from '../../../shared/components/IconButton';
import { Waveform } from './Waveform';

interface EditorWorkspaceProps {
  activeTool: EditorTool;
  onToolChange: (tool: EditorTool) => void;
}

const tools: Array<{ id: EditorTool; label: string; icon: typeof MousePointer2 }> = [
  { id: 'select', label: 'Select', icon: MousePointer2 },
  { id: 'trim', label: 'Trim', icon: Scissors },
  { id: 'split', label: 'Split', icon: Slice },
  { id: 'fade', label: 'Fade', icon: Sparkles },
];

export function EditorWorkspace({ activeTool, onToolChange }: EditorWorkspaceProps) {
  return (
    <section className="workspace">
      <div className="workspace-toolbar panel-surface">
        <div className="tool-group">
          {tools.map(({ id, label, icon: Icon }) => (
            <IconButton key={id} label={label} active={activeTool === id} onClick={() => onToolChange(id)}><Icon /></IconButton>
          ))}
        </div>
        <div className="toolbar-center"><Crosshair /><span>Snap</span><kbd>⌘ G</kbd></div>
        <div className="tool-group">
          <IconButton label="Zoom out"><ZoomOut /></IconButton>
          <span className="zoom-value">100%</span>
          <IconButton label="Zoom in"><ZoomIn /></IconButton>
        </div>
      </div>

      <div className="timeline panel-surface">
        <div className="time-ruler">
          {['0:00', '0:15', '0:30', '0:45', '1:00', '1:15', '1:30'].map((time) => <span key={time}>{time}</span>)}
        </div>
        <div className="playhead"><span>0:34.6</span></div>

        <div className="timeline-track is-primary">
          <div className="track-controls">
            <strong>Main recording</strong>
            <small>VOCAL</small>
            <div><button type="button">M</button><button type="button">S</button><button type="button"><ChevronDown /></button></div>
          </div>
          <div className="audio-region main-region"><Waveform color="#8b70ff" /><span className="region-label">Midnight Signal.wav</span></div>
        </div>

        <div className="timeline-track">
          <div className="track-controls">
            <strong>Room tone</strong>
            <small>NOISE FLOOR</small>
            <div><button type="button">M</button><button type="button">S</button><button type="button"><ChevronDown /></button></div>
          </div>
          <div className="audio-region room-region"><Waveform color="#22c9a7" /></div>
        </div>

        <div className="timeline-track">
          <div className="track-controls">
            <strong>Ambient bed</strong>
            <small>MUSIC</small>
            <div><button type="button">M</button><button type="button">S</button><button type="button"><ChevronDown /></button></div>
          </div>
          <div className="audio-region ambient-region"><Waveform color="#ffb547" muted /></div>
        </div>

        <button type="button" className="add-track-button">+ Add audio track</button>
      </div>
    </section>
  );
}
