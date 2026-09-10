"""Linear/circular convolution, correlation, and impulse-response processing."""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import signal

from ._validation import as_audio_array, broadcast_channels, restore_channels, to_2d, validate_positive_int, validate_probability

ConvolutionMode = Literal["full", "same", "valid"]
ConvolutionMethod = Literal["auto", "direct", "fft"]


def convolution_sum(x: ArrayLike, h: ArrayLike) -> NDArray[np.float64]:
    """Educational O(NM) discrete-time convolution sum for one-dimensional signals."""

    first = as_audio_array(x, name="x")
    second = as_audio_array(h, name="h")
    if first.ndim != 1 or second.ndim != 1:
        raise ValueError("convolution_sum accepts one-dimensional signals only")
    result = np.zeros(first.size + second.size - 1, dtype=np.float64)
    for n in range(result.size):
        k_min = max(0, n - (second.size - 1))
        k_max = min(n, first.size - 1)
        for k in range(k_min, k_max + 1):
            result[n] += first[k] * second[n - k]
    return result


def linear_convolution(
    audio: ArrayLike,
    kernel: ArrayLike,
    *,
    mode: ConvolutionMode = "full",
    method: ConvolutionMethod = "auto",
) -> NDArray[np.float64]:
    """Convolve audio and a kernel along time, broadcasting mono channels."""

    if mode not in {"full", "same", "valid"}:
        raise ValueError("mode must be 'full', 'same', or 'valid'")
    if method not in {"auto", "direct", "fft"}:
        raise ValueError("method must be 'auto', 'direct', or 'fft'")

    original = as_audio_array(audio)
    impulse = as_audio_array(kernel, name="kernel")
    arrays, channels = broadcast_channels([original, impulse])
    convolved = [signal.convolve(arrays[0][:, channel], arrays[1][:, channel], mode=mode, method=method) for channel in range(channels)]
    output = np.column_stack(convolved)
    return restore_channels(output, original.ndim == 1 and impulse.ndim == 1)


def circular_convolution(x: ArrayLike, h: ArrayLike, *, length: int | None = None) -> NDArray[np.float64]:
    """Compute N-point circular convolution using the DFT."""

    first = as_audio_array(x, name="x")
    second = as_audio_array(h, name="h")
    arrays, channels = broadcast_channels([first, second])
    size = max(arrays[0].shape[0], arrays[1].shape[0]) if length is None else validate_positive_int(length, name="length")
    result = np.empty((size, channels), dtype=np.float64)
    for channel in range(channels):
        spectrum = np.fft.fft(arrays[0][:, channel], n=size) * np.fft.fft(arrays[1][:, channel], n=size)
        result[:, channel] = np.fft.ifft(spectrum).real
    return restore_channels(result, first.ndim == 1 and second.ndim == 1)


def cross_correlation(
    x: ArrayLike,
    y: ArrayLike,
    *,
    mode: ConvolutionMode = "full",
    normalize: bool = False,
) -> NDArray[np.float64]:
    """Cross-correlate signals; optionally normalize to correlation coefficients."""

    first = as_audio_array(x, name="x")
    second = as_audio_array(y, name="y")
    arrays, channels = broadcast_channels([first, second])
    values = []
    for channel in range(channels):
        result = signal.correlate(arrays[0][:, channel], arrays[1][:, channel], mode=mode, method="auto")
        if normalize:
            denominator = np.linalg.norm(arrays[0][:, channel]) * np.linalg.norm(arrays[1][:, channel])
            if denominator > 0:
                result = result / denominator
        values.append(result)
    output = np.column_stack(values)
    return restore_channels(output, first.ndim == 1 and second.ndim == 1)


def apply_impulse_response(
    audio: ArrayLike,
    impulse_response: ArrayLike,
    *,
    wet: float = 1.0,
    normalize: bool = True,
) -> NDArray[np.float64]:
    """Apply an impulse response and mix it with a delay-aligned dry signal."""

    wet_mix = validate_probability(wet, name="wet")
    original = as_audio_array(audio)
    processed = linear_convolution(original, impulse_response, method="fft")
    arrays, _ = broadcast_channels([original, processed])
    dry_padded = np.zeros_like(arrays[1])
    dry_padded[: arrays[0].shape[0]] = arrays[0]
    mixed = (1.0 - wet_mix) * dry_padded + wet_mix * arrays[1]
    if normalize:
        peak = np.max(np.abs(mixed))
        if peak > 1.0:
            mixed /= peak
    return restore_channels(mixed, original.ndim == 1 and np.asarray(impulse_response).ndim == 1)
