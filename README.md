# SonicCraft

SonicCraft is a signals-and-systems course project that turns core DSP concepts
into an approachable browser-based audio editor.

## Repository layout

```text
frontend/              React + TypeScript web interface
backend/               Python audio-processing package and tests
docs/                  Product and implementation prompts
```

## Frontend quick start

```bash
cd frontend
npm install
npm run dev
```

The frontend is dark by default and includes a light-theme toggle. The current
screen is a responsive editor shell ready to be connected to Web Audio or the
Python DSP backend.

## Backend quick start

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ./backend
python -m unittest discover -s backend/tests
```

The reusable DSP package is `soniccraft`. Its public modules cover audio I/O,
analysis, editing/effects, convolution, Fourier transforms, filters, sampling,
noise reduction, and spectrogram reconstruction.

See [`docs/frontend-build-prompt.md`](docs/frontend-build-prompt.md) for the
implementation brief to use in a follow-up Codex task.
