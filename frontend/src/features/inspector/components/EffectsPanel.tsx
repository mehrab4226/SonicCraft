import { AudioLines, ChevronRight, CirclePower, ScanLine, SlidersHorizontal, Sparkles, Waves } from 'lucide-react';

const effects = [
  { name: 'Volume & fade', detail: '-2.4 dB', icon: SlidersHorizontal, active: true },
  { name: 'Equalizer', detail: 'Vocal clarity', icon: AudioLines, active: true },
  { name: 'Noise remover', detail: 'Spectral gate', icon: Sparkles, active: false },
];

export function EffectsPanel() {
  return (
    <aside className="inspector panel-surface">
      <div className="panel-heading"><div><span className="eyebrow">Selected track</span><h2>Processing</h2></div></div>

      <div className="meter-card">
        <div className="meter-heading"><span>Output</span><strong>-6.2 dB</strong></div>
        <div className="meter"><i style={{ width: '74%' }} /><span className="meter-peak" /></div>
        <div className="meter-scale"><span>-48</span><span>-24</span><span>-12</span><span>0</span></div>
      </div>

      <div className="effect-list">
        {effects.map(({ name, detail, icon: Icon, active }) => (
          <button type="button" className="effect-row" key={name}>
            <span className="effect-icon"><Icon /></span>
            <span><strong>{name}</strong><small>{detail}</small></span>
            <CirclePower className={active ? 'power-active' : ''} />
            <ChevronRight />
          </button>
        ))}
      </div>

      <div className="analysis-heading"><span className="eyebrow">Analysis</span></div>
      <div className="analysis-grid">
        <button type="button"><Waves /><span><strong>FFT spectrum</strong><small>Frequency view</small></span></button>
        <button type="button"><ScanLine /><span><strong>Spectrogram</strong><small>Time-frequency</small></span></button>
      </div>

      <button type="button" className="add-effect-button">+ Add effect</button>
    </aside>
  );
}
