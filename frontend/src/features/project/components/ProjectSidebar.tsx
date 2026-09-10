import { AudioWaveform, CirclePlus, Headphones, Layers3, Mic2, Music2 } from 'lucide-react';

const tracks = [
  { name: 'Main recording', detail: 'Stereo · 44.1 kHz', color: '#7c5cff', icon: AudioWaveform },
  { name: 'Room tone', detail: 'Mono · 44.1 kHz', color: '#22c9a7', icon: Mic2 },
  { name: 'Ambient bed', detail: 'Stereo · 48 kHz', color: '#ffb547', icon: Music2 },
];

export function ProjectSidebar() {
  return (
    <aside className="sidebar panel-surface">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Project</span>
          <h2>Audio layers</h2>
        </div>
        <button type="button" className="small-icon-button" aria-label="Add track"><CirclePlus /></button>
      </div>

      <div className="track-list">
        {tracks.map(({ name, detail, color, icon: Icon }, index) => (
          <button type="button" className={`track-item ${index === 0 ? 'is-selected' : ''}`} key={name}>
            <span className="track-icon" style={{ '--track-color': color } as React.CSSProperties}><Icon /></span>
            <span><strong>{name}</strong><small>{detail}</small></span>
          </button>
        ))}
      </div>

      <div className="sidebar-spacer" />
      <div className="course-card">
        <span className="course-icon"><Layers3 /></span>
        <div><span className="eyebrow">Now exploring</span><strong>Frequency domain</strong></div>
        <Headphones />
      </div>
    </aside>
  );
}
