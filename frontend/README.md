# SonicCraft frontend

React, TypeScript, and Vite frontend for the SonicCraft audio editor.

## Commands

```bash
npm install
npm run dev
npm run typecheck
npm run build
```

## Structure

- `src/app` — application composition and future providers/router
- `src/features` — isolated audio-editor feature modules
- `src/shared/components` — reusable interface primitives
- `src/shared/hooks` — cross-feature React hooks
- `src/shared/types` — shared domain types
- `src/styles` — design tokens and global layout styles

The current version provides the responsive editor shell and theme system. Audio
decoding, DSP, waveform interaction, persistence, and export are intentionally left
for the next implementation phase described in `../docs/frontend-build-prompt.md`.
