# SonicCraft architecture

The active application is a local PyQt6 desktop window. It reuses the existing
`soniccraft` package under `backend/src` through ordinary Python imports.

```text
main.py
  -> soniccraft.desktop.main
       -> QApplication
       -> MainWindow
            -> menus / toolbar / status
            -> WaveformWidget (PyQtGraph)

soniccraft.audio_io          SoundFile I/O for the next desktop phase
soniccraft.dsp               Independent NumPy/SciPy signal processing
```

Phase 1 creates no audio stream, worker, server, database, or network request.
The waveform is an empty plotting surface; audio loading and GUI-to-DSP processing
are explicitly pending.

Audio in the existing DSP core has time on axis 0. Mono is `(samples,)`; stereo is
`(samples, 2)`. Floating-point values preserve headroom so clipping can be
detected before encoding. GUI classes must call DSP functions rather than embed
the mathematics in event handlers.

The retired React frontend and HTTP adapter have been removed from the working
tree. `requirements.txt` installs the `desktop` extra; no web stack is required.

The existing package layout is retained to preserve working DSP code and tests.
Follow `implementation-plan.md` one phase at a time; Phase 2 will connect local
loading, metadata, playback, stop, and saving to this foundation.
