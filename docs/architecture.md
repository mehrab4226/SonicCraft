# SonicCraft architecture

```text
SonicCraft/
├── backend/
│   ├── pyproject.toml
│   ├── src/soniccraft/
│   │   ├── audio_io.py
│   │   └── dsp/
│   │       ├── _validation.py
│   │       ├── analysis.py
│   │       ├── convolution.py
│   │       ├── effects.py
│   │       ├── filters.py
│   │       ├── noise_reduction.py
│   │       ├── sampling.py
│   │       └── transforms.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/
│       ├── features/
│       ├── shared/
│       └── styles/
└── docs/
```

The frontend owns interaction, visualization, browser audio lifecycle, and typed
API adapters. The backend package owns deterministic audio math and file encoding.
An HTTP layer can be added later without moving DSP functions or importing web
framework objects into them.

Audio crosses the boundary as an uploaded file or encoded byte stream. Inside the
backend, audio is a NumPy array with time on axis 0. Mono is `(samples,)`; multiple
channels are `(samples, channels)`.
