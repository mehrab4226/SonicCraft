import { useEffect, useRef } from 'react';
import type { AudioInspection } from '../../../shared/types/editor';

export function Waveform({ color, waveform, muted = false }: {
  color: string; waveform: AudioInspection['waveform']; muted?: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const draw = () => {
      const { width, height } = element.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      element.width = Math.round(width * ratio);
      element.height = Math.round(height * ratio);
      const context = element.getContext('2d');
      if (!context) return;
      context.scale(ratio, ratio);
      context.clearRect(0, 0, width, height);
      context.strokeStyle = color;
      context.lineWidth = 1;
      const channels = waveform.minimum.length;
      const bins = waveform.times.length;
      for (let channel = 0; channel < channels; channel++) {
        const laneHeight = height / channels;
        const center = channel * laneHeight + laneHeight / 2;
        const scale = laneHeight * 0.42;
        context.globalAlpha = 0.25;
        context.beginPath(); context.moveTo(0, center); context.lineTo(width, center); context.stroke();
        context.globalAlpha = 0.9;
        context.beginPath();
        for (let i = 0; i < bins; i++) {
          const x = (i + 0.5) / bins * width;
          const low = Math.max(-1, waveform.minimum[channel][i]);
          const high = Math.min(1, waveform.maximum[channel][i]);
          context.moveTo(x, center - high * scale);
          context.lineTo(x, center - low * scale);
        }
        context.stroke();
      }
    };
    const observer = new ResizeObserver(draw);
    observer.observe(element); draw();
    return () => observer.disconnect();
  }, [color, waveform]);
  return <canvas ref={canvas} className={`waveform ${muted ? 'is-muted' : ''}`} aria-label="Audio waveform" />;
}
