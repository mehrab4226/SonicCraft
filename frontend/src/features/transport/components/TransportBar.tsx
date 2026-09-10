import { Circle, Pause, Play, Repeat2, SkipBack, SkipForward, Volume2 } from 'lucide-react';
import { useState } from 'react';
import { IconButton } from '../../../shared/components/IconButton';

export function TransportBar() {
  const [playing, setPlaying] = useState(false);

  return (
    <footer className="transport">
      <div className="transport-time"><strong>00:34.620</strong><span>/ 01:42.908</span></div>
      <div className="transport-controls">
        <IconButton label="Loop"><Repeat2 /></IconButton>
        <IconButton label="Previous"><SkipBack /></IconButton>
        <button type="button" className="play-button" aria-label={playing ? 'Pause' : 'Play'} onClick={() => setPlaying(!playing)}>
          {playing ? <Pause /> : <Play />}
        </button>
        <IconButton label="Next"><SkipForward /></IconButton>
        <IconButton label="Record" className="record-button"><Circle /></IconButton>
      </div>
      <div className="transport-volume"><Volume2 /><input aria-label="Master volume" type="range" min="0" max="100" defaultValue="72" /><span>72%</span></div>
    </footer>
  );
}
