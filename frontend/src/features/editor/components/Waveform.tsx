const upperPath = 'M0,64 L8,54 L16,72 L24,41 L32,78 L40,28 L48,69 L56,48 L64,76 L72,35 L80,64 L88,22 L96,83 L104,42 L112,67 L120,30 L128,73 L136,51 L144,60 L152,19 L160,85 L168,40 L176,70 L184,33 L192,76 L200,46 L208,62 L216,25 L224,81 L232,44 L240,68 L248,38 L256,73 L264,49 L272,63 L280,31 L288,78 L296,42 L304,70 L312,36 L320,74 L328,50 L336,62 L344,27 L352,82 L360,43 L368,68 L376,35 L384,76 L392,48 L400,64 L408,30 L416,79 L424,45 L432,68 L440,38 L448,73 L456,52 L464,62 L472,25 L480,84 L488,40 L496,70 L504,32 L512,77 L520,47 L528,63 L536,28 L544,80 L552,44 L560,68 L568,37 L576,74 L584,50 L592,64 L600,31 L608,79 L616,43 L624,69 L632,34 L640,76 L648,47 L656,63 L664,27 L672,82 L680,42 L688,70 L696,36 L704,74 L712,50 L720,62 L728,30 L736,80 L744,44 L752,68 L760,37 L768,75 L776,48 L784,64 L792,32 L800,77';

interface WaveformProps {
  color: string;
  muted?: boolean;
}

export function Waveform({ color, muted = false }: WaveformProps) {
  return (
    <svg className={`waveform ${muted ? 'is-muted' : ''}`} viewBox="0 0 800 128" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={`wave-${color.replace('#', '')}`} x1="0" x2="1">
          <stop stopColor={color} stopOpacity="0.95" />
          <stop offset="1" stopColor={color} stopOpacity="0.45" />
        </linearGradient>
      </defs>
      <path d={upperPath} fill="none" stroke={`url(#wave-${color.replace('#', '')})`} strokeWidth="2" vectorEffect="non-scaling-stroke" />
      <path d={upperPath} transform="translate(0 128) scale(1 -1)" fill="none" stroke={`url(#wave-${color.replace('#', '')})`} strokeWidth="2" vectorEffect="non-scaling-stroke" opacity="0.7" />
    </svg>
  );
}
