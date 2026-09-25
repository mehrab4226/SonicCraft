"""Testable desktop operations delegating signal mathematics to the DSP core."""
import numpy as np
from soniccraft.dsp.effects import trim_audio, normalize_peak, apply_gain, apply_fade
from soniccraft.dsp.filters import butterworth, peaking_eq_sections, ParametricEQBand, apply_filter
from soniccraft.dsp.noise_reduction import spectral_subtraction, spectral_gate, wiener_denoise


def check_transform_size(samples, n_fft, hop):
    if not 16 <= n_fft <= 8192 or not 0 < hop <= n_fft // 2:
        raise ValueError("FFT size must be 16–8192; hop must be 1–FFT/2 for reliable reconstruction.")
    channels = 1 if samples.ndim == 1 else samples.shape[1]
    frames = int(np.ceil(len(samples) / hop)) + 2
    if frames * n_fft * channels * 48 > 256 * 1024 * 1024:
        raise ValueError("Transform exceeds the 256 MiB working-memory budget. Select a shorter region or increase hop.")


def filter_sections(operation, parameters, rate):
    if operation == "filter":
        kind = parameters["kind"]
        cutoff = (parameters["low"], parameters["high"]) if kind.startswith("band") else parameters["low"]
        return butterworth(cutoff, rate, kind=kind, order=parameters.get("order", 4))
    bands = parameters["bands"]
    sections = [peaking_eq_sections(ParametricEQBand(f, gain, 1.4), rate) for f, gain in bands]
    if not sections:
        raise ValueError("No EQ bands are below this file's Nyquist frequency.")
    return np.vstack(sections)


def sample_range(audio, start, end):
    if not np.isfinite(start) or not np.isfinite(end) or not 0 <= start < end <= audio.duration + 1e-9:
        raise ValueError("Select a non-empty interval inside the waveform.")
    first = max(0, int(round(start * audio.sample_rate)))
    last = min(len(audio.samples), int(round(end * audio.sample_rate)))
    if first >= last:
        raise ValueError("Select at least one sample.")
    return first, last


def process(audio, bounds, operation, parameters=None):
    parameters = parameters or {}
    start, end = bounds
    if not 0 <= start < end <= len(audio.samples):
        raise ValueError("Select a non-empty sample range.")
    source = audio.samples
    target_channel = parameters.get("target_channel")
    if target_channel is not None and operation in ("trim", "delete"):
        raise ValueError(
            "Time-shifting operations (Trim, Delete) must apply to both channels to keep the stereo array synchronized."
        )
    targeted_stereo = source.ndim == 2 and target_channel in (0, 1)
    selected = source[start:end, target_channel] if targeted_stereo else source[start:end]
    if operation == "trim":
        return trim_audio(source, start, end)
    if operation == "delete":
        if end - start == len(source):
            raise ValueError("Cannot delete all samples. Use Silence instead.")
        return np.concatenate([source[:start], source[end:]], axis=0)
    if operation == "reverse":
        changed = selected[::-1]
    elif operation == "silence":
        changed = np.zeros_like(selected)
    elif operation == "normalize":
        changed = normalize_peak(selected, parameters.get("target_dbfs", -1))
    elif operation == "gain":
        changed = apply_gain(selected, parameters["gain_db"])
    elif operation == "fade":
        duration = parameters["seconds"]
        if not np.isfinite(duration) or not 0 < duration <= len(selected) / audio.sample_rate:
            raise ValueError("Fade duration must fit inside the selection.")
        changed = apply_fade(
            selected, audio.sample_rate, curve=parameters.get("curve", "linear"),
            **{parameters["direction"] + "_seconds": duration},
        )
    elif operation in ("filter", "eq"):
        changed = apply_filter(selected, filter_sections(operation, parameters, audio.sample_rate))
    elif operation == "wiener":
        changed = wiener_denoise(selected, window_size=parameters.get("window_size", 29))
    elif operation in ("subtraction", "gate"):
        profile = parameters.get("profile")
        if profile is None:
            raise ValueError("Select a noise-only region and capture its profile first.")
        check_transform_size(selected, profile.n_fft, profile.hop_length)
        if operation == "subtraction":
            changed = spectral_subtraction(selected, audio.sample_rate, profile, strength=parameters.get("strength", 1))
        else:
            changed = spectral_gate(selected, audio.sample_rate, profile, threshold=parameters.get("strength", 1.5))
    else:
        raise ValueError(f"Unknown operation: {operation}")
    output = source.copy()
    if targeted_stereo:
        output[start:end, target_channel] = changed
    else:
        output[start:end] = changed
    return output
