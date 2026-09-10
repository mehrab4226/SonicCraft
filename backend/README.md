# SonicCraft DSP backend

Framework-independent Python utilities used by the future SonicCraft web API.
All audio arrays follow one convention:

- mono: `(samples,)`
- multichannel: `(samples, channels)`
- floating-point samples are expected in the nominal range `[-1.0, 1.0]`

## Modules

- `soniccraft.audio_io` — file/byte decoding, encoding, and metadata
- `soniccraft.dsp.analysis` — levels, clipping, and waveform summaries
- `soniccraft.dsp.convolution` — linear/circular convolution and correlation
- `soniccraft.dsp.effects` — editing, mixing, gain, normalization, and fades
- `soniccraft.dsp.filters` — Butterworth, notch, and parametric equalizers
- `soniccraft.dsp.noise_reduction` — spectral gate/subtraction and Wiener filtering
- `soniccraft.dsp.sampling` — resampling, alias calculations, and sinc reconstruction
- `soniccraft.dsp.transforms` — DFT/FFT, Fourier series, STFT, spectrogram, and Griffin-Lim

The package deliberately has no web-framework dependency. A future API layer can
call these functions without coupling the signal-processing code to HTTP.

## Example

```python
from soniccraft import load_audio, save_audio
from soniccraft.dsp.filters import highpass
from soniccraft.dsp.transforms import fft_spectrum

audio, sample_rate = load_audio("recording.wav")
cleaned = highpass(audio, sample_rate, cutoff=80, zero_phase=True)
spectrum = fft_spectrum(cleaned, sample_rate, n_fft=4096)
save_audio("cleaned.wav", cleaned, sample_rate, subtype="PCM_16")

peak_frequency = spectrum.frequencies[spectrum.magnitude.argmax()]
print(f"Strongest frequency: {peak_frequency:.1f} Hz")
```

## Tests

From the repository root:

```bash
python -m unittest discover -s backend/tests -v
```
