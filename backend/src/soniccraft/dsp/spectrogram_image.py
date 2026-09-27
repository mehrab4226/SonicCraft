"""Decode a plot image into a calibrated frequency-by-time magnitude grid."""
import numpy as np
from PIL import Image, ImageOps
from scipy.spatial import cKDTree

from ._validation import validate_positive_int, validate_sample_rate


def reconstruction_layout(duration, sample_rate, n_fft):
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError("Enter the duration shown by the plot's time axis.")
    hop = n_fft // 4
    length = max(1, round(duration * sample_rate))
    columns = max(2, int(np.ceil(length / hop)) + 1)
    max_columns = (256 * 1024 * 1024) // (n_fft * 48)
    if columns > max_columns:
        limit = (max_columns - 1) * hop / sample_rate
        raise ValueError(
            f"This import supports up to {limit:.1f} seconds per reconstruction. "
            "Crop a shorter time interval and enter that interval's actual duration."
        )
    return length, columns


def crop_box(box, width, height):
    if box is None:
        return (0, 0, width, height)
    if len(box) != 4 or any(not np.isfinite(v) or int(v) != v for v in box):
        raise ValueError("Image selection must contain four integer pixel coordinates.")
    left, top, right, bottom = map(int, box)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("Select a non-empty rectangle inside the image.")
    return left, top, right, bottom


def _reduce_peaks(values, positions, targets):
    """Merge oversampled pixels into nearest output bins without losing marks."""
    if len(positions) <= len(targets) or len(targets) < 2:
        return values, positions
    boundaries = (targets[:-1] + targets[1:]) / 2
    indices = np.searchsorted(boundaries, positions)
    reduced = np.zeros((len(targets), values.shape[1]), dtype=values.dtype)
    np.maximum.at(reduced, indices, values)
    return reduced, targets


def image_magnitude(
    image_path, sample_rate, *, n_fft=2048, duration=None,
    min_frequency=0, max_frequency=None, frequency_scale="linear",
    magnitude_scale="linear", dynamic_range_db=80, invert=False,
    time_axis="horizontal", crop=None, colorbar_crop=None,
):
    """Return magnitudes and output sample count.

    Horizontal time runs left to right; frequency rises bottom to top.
    Vertical time runs bottom to top; frequency rises left to right.
    A selected vertical colour bar runs from maximum at top to minimum below.
    dB values are relative to the colour bar's maximum; its absolute offset is
    unnecessary because reconstructed output is peak-normalized.
    """
    rate = validate_sample_rate(sample_rate)
    size = validate_positive_int(n_fft, name="n_fft")
    if size < 4 or size % 2:
        raise ValueError("Image reconstruction needs an even FFT size of at least four.")
    if time_axis not in ("horizontal", "vertical"):
        raise ValueError("Choose horizontal or vertical time.")
    if frequency_scale not in ("linear", "log") or magnitude_scale not in ("linear", "db"):
        raise ValueError("Choose a supported frequency and intensity scale.")
    maximum = rate / 2 if max_frequency is None else float(max_frequency)
    minimum = float(min_frequency)
    if not np.all(np.isfinite([minimum, maximum])) or not 0 <= minimum < maximum <= rate / 2:
        raise ValueError("Frequency limits must increase from zero or above to at most half the sample rate.")
    if frequency_scale == "log" and minimum <= 0:
        raise ValueError("A logarithmic frequency axis needs a minimum greater than zero.")
    if not np.isfinite(dynamic_range_db) or not 0 < dynamic_range_db <= 200:
        raise ValueError("The colour scale range must be between 0 and 200 dB.")
    with Image.open(image_path) as source:
        if source.width * source.height > 20_000_000:
            raise ValueError("Use an image no larger than 20 million pixels.")
        source = ImageOps.exif_transpose(source)
        box = crop_box(crop, source.width, source.height)
        temporal_pixels = box[2] - box[0] if time_axis == "horizontal" else box[3] - box[1]
        hop = size // 4
        if duration is None:
            # Bound automatic synthesis work even for very wide images.
            duration = max(hop, (min(temporal_pixels, 2048) - 1) * hop) / rate
        length, columns = reconstruction_layout(duration, rate, size)
        rgba = source.convert("RGBA")
        backdrop = Image.new("RGBA", source.size, (0, 0, 0, 255))
        rgb = Image.alpha_composite(backdrop, rgba).convert("RGB")
        pixels = np.asarray(rgb.crop(box), dtype=float)
        if colorbar_crop is not None:
            bar_box = crop_box(colorbar_crop, source.width, source.height)
            bar = np.asarray(rgb.crop(bar_box), dtype=float).mean(axis=1)
            if len(bar) < 2 or np.max(np.ptp(bar, axis=0)) < 10:
                raise ValueError("Select the coloured strip of a vertical colour bar, excluding labels and borders.")
            _, indices = cKDTree(bar).query(pixels.reshape(-1, 3))
            levels = (1 - indices / (len(bar) - 1)).reshape(pixels.shape[:2])
        else:
            # Max-channel brightness preserves green/red/blue intensity equally;
            # luminance conversion would arbitrarily attenuate a tinted plot.
            levels = np.max(pixels, axis=2) / 255
    if invert:
        levels = 1 - levels
    if magnitude_scale == "db":
        levels = np.where(levels > 0, 10 ** ((levels - 1) * dynamic_range_db / 20), 0)
    # Canonical order: frequency increasing down the array, time increasing right.
    levels = levels[::-1] if time_axis == "horizontal" else levels[::-1].T
    row_frequencies = (np.linspace(minimum, maximum, levels.shape[0])
                       if frequency_scale == "linear" else np.geomspace(minimum, maximum, levels.shape[0]))
    frequencies = np.fft.rfftfreq(size, 1 / rate)
    # Interpolate time first; preserve the requested duration independently of pixels.
    source_times = np.linspace(0, length / rate, levels.shape[1])
    frame_times = np.minimum(np.arange(columns) * hop / rate, length / rate)
    # Reduce before enlarging either axis: thin notes/transients must not fall
    # between sampled pixels, and tall images must not create huge intermediates.
    reduced, source_times = _reduce_peaks(levels.T, source_times, frame_times)
    levels = reduced.T
    in_range = frequencies[(frequencies >= minimum) & (frequencies <= maximum)]
    levels, row_frequencies = _reduce_peaks(levels, row_frequencies, in_range)
    if len(row_frequencies) == 1:
        # A one-row image has no vertical variation: fill its frequency range.
        levels = np.repeat(levels, 2, axis=0)
        row_frequencies = np.array([minimum, maximum])
    timed = np.array([np.interp(frame_times, source_times, row) for row in levels])
    magnitude = np.array([
        np.interp(frequencies, row_frequencies, timed[:, i], left=0, right=0)
        for i in range(columns)
    ]).T
    return magnitude, length
