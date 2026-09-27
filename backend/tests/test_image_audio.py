"""Image reconstruction checked against signals and SciPy's independent STFT."""
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
import pytest
from PIL import Image
from scipy import signal
from unittest.mock import patch

from soniccraft.dsp.spectrogram_image import image_magnitude
from soniccraft.dsp.transforms import image_to_audio, griffin_lim
from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.analysis import make_spectrogram


def save_image(tmp_path, pixels, name="input.png"):
    path = tmp_path / name
    Image.fromarray(np.asarray(pixels, dtype=np.uint8)).save(path)
    return str(path)


@pytest.mark.parametrize("vertical", [False, True])
def test_known_chirp_pitch_direction_duration_and_level(tmp_path, vertical):
    rate, size, duration = 8000, 256, 1.2
    times = np.arange(round(rate * duration)) / rate
    reference = signal.chirp(times, f0=300, f1=1700, t1=duration)
    frequencies, frame_times, spectrum = signal.stft(reference, rate, nperseg=size, noverlap=192)
    values = abs(spectrum[frequencies <= 2000])
    db = 20 * np.log10(np.maximum(values / values.max(), 1e-4))
    levels = np.rint(np.clip((db + 80) / 80, 0, 1) * 255)
    pixels = levels.T[::-1] if vertical else levels[::-1]
    path = save_image(tmp_path, pixels)
    audio = image_to_audio(path, rate, n_fft=size, iterations=32, duration=duration,
                          max_frequency=2000, magnitude_scale="db", dynamic_range_db=80,
                          time_axis="vertical" if vertical else "horizontal")
    f, t, z = signal.stft(audio, rate, nperseg=size, noverlap=192)
    peaks = f[np.argmax(abs(z), axis=0)]
    valid = (t > .1) & (t < duration - .1)
    assert np.median(abs(peaks[valid] - (300 + 1400 * t[valid] / duration))) < 35
    assert len(audio) == len(reference)
    assert np.max(abs(audio)) == pytest.approx(.95)
    assert peaks[valid][-1] > peaks[valid][0] + 1000


def test_colorbar_recovers_db_intensity_and_ignores_white_border(tmp_path):
    # Brightness is deliberately non-monotonic; matching RGB must recover the scale.
    bar = np.array([[255, 255, 0], [0, 180, 100], [20, 20, 180]], dtype=np.uint8)
    image = np.full((9, 8, 3), 255, dtype=np.uint8)
    image[2:5, 1:5] = bar[:, None, :]
    image[2:5, 6:7] = bar[:, None, :]
    path = save_image(tmp_path, image)
    magnitude, _ = image_magnitude(path, 8000, n_fft=8, duration=.002,
                                  crop=(1, 2, 5, 5), colorbar_crop=(6, 2, 7, 5),
                                  magnitude_scale="db", dynamic_range_db=80)
    assert magnitude[0, 0] == 0
    assert magnitude[2, 0] == pytest.approx(.01)
    assert magnitude[4, 0] == 1
    automatic, _ = image_magnitude(path, 8000, crop=(1, 2, 5, 5))
    assert np.isfinite(automatic).all() and automatic.max() == 1


def test_log_frequency_mapping_and_white_background(tmp_path):
    levels = np.zeros((5, 10), dtype=np.uint8)
    levels[2] = 255  # middle log row: sqrt(250 * 4000) = 1000 Hz
    path = save_image(tmp_path, 255 - levels)
    magnitude, _ = image_magnitude(path, 8000, n_fft=256, duration=.1,
                                  min_frequency=250, max_frequency=4000,
                                  frequency_scale="log", invert=True)
    assert np.fft.rfftfreq(256, 1 / 8000)[np.argmax(magnitude[:, 0])] == 1000


@pytest.mark.parametrize("channel", [0, 1, 2])
def test_tinted_brightness_matches_grayscale_without_colorbar(tmp_path, channel):
    levels = np.zeros((129, 40), dtype=np.uint8)
    levels[95:98] = 160
    levels[63:65] = 255
    tinted = np.zeros((*levels.shape, 3), dtype=np.uint8)
    tinted[:, :, channel] = levels
    gray = save_image(tmp_path, levels, "gray.png")
    path = save_image(tmp_path, tinted, "tinted.png")
    expected, _ = image_magnitude(gray, 8000, n_fft=256, duration=.3)
    result, _ = image_magnitude(path, 8000, n_fft=256, duration=.3)
    np.testing.assert_allclose(result, expected)


def test_single_column_silence_and_invalid_inputs(tmp_path):
    path = save_image(tmp_path, np.zeros((16, 1)))
    output = image_to_audio(path, 8000, n_fft=128, iterations=2)
    assert len(output) > 0 and np.all(output == 0)
    for options in (dict(duration=0), dict(duration=1e5), dict(min_frequency=3000, max_frequency=2000),
                    dict(max_frequency=5000), dict(crop=(-1, 0, 1, 10)), dict(frequency_scale="log")):
        with pytest.raises(ValueError):
            image_magnitude(path, 8000, **options)
    with pytest.raises(ValueError, match="two centered frames"):
        griffin_lim(np.ones((65, 1)), 8000, n_fft=128)


def test_phase_reconstruction_reduces_independent_spectral_error():
    rate, size = 8000, 256
    t = np.arange(4000) / rate
    reference = .4 * np.sin(2 * np.pi * 500 * t) + .2 * np.sin(2 * np.pi * 1200 * t)
    _, _, z = signal.stft(reference, rate, nperseg=size, noverlap=192)
    target = abs(z) * signal.get_window("hann", size).sum()
    errors = []
    for count in (1, 48):
        audio = griffin_lim(target, rate, n_fft=size, iterations=count)
        _, _, rebuilt = signal.stft(audio, rate, nperseg=size, noverlap=192)
        errors.append(np.linalg.norm(abs(rebuilt) * (size / 2) - target) / np.linalg.norm(target))
    assert errors[1] < errors[0] * .6


def test_wikimedia_chirp_matches_independent_expected_frequency():
    path = Path(__file__).parent / "fixtures/chirp_spectrogram.png"
    audio = image_to_audio(path, 44100, duration=2, max_frequency=2250,
                          time_axis="vertical", magnitude_scale="db", dynamic_range_db=102,
                          crop=(160, 64, 1093, 738), colorbar_crop=(1110, 64, 1130, 738), iterations=64)
    f, t, z = signal.stft(audio, 44100, nperseg=2048, noverlap=1536)
    valid = (t > .15) & (t < 1.85)
    peaks = f[np.argmax(abs(z), axis=0)]
    assert len(audio) == 88200
    assert np.median(abs(peaks[valid] - (100 + 950 * t[valid]))) < 40
    assert np.corrcoef(peaks[valid], t[valid])[0, 1] > .99


def test_import_converts_selected_image_without_setup(tmp_path):
    app = create_application([])
    pixels = np.zeros((32, 20, 3), dtype=np.uint8)
    pixels[12, :, 1] = 255
    pixels[20, :, 0] = 180
    path = save_image(tmp_path, pixels)
    view = MainWindow()
    def run_now(label, work, done):
        done(work())
    with patch("soniccraft.desktop.main_window.QFileDialog.getOpenFileName", return_value=(path, "")), \
         patch.object(view, "run_job", side_effect=run_now) as job:
        view.import_image_dialog()
        job.assert_called_once()
    assert view.document.dirty
    assert np.max(abs(view.document.audio.samples)) == pytest.approx(.95)
    assert view.spectrogram_widget.current_data is not None
    view.document.saved_samples = view.document.audio.samples
    with patch("soniccraft.desktop.main_window.QFileDialog.getOpenFileName", return_value=("", "")), \
         patch.object(view, "run_job") as job:
        view.import_image_dialog()
        job.assert_not_called()
    view.close()
    app.processEvents()


def test_wide_image_automatically_bounds_duration(tmp_path):
    path = save_image(tmp_path, np.zeros((4, 5000)))
    magnitude, length = image_magnitude(path, 44100)
    assert magnitude.shape[1] == 2048
    assert length == 2047 * 512


def test_image_load_displays_green_spectrogram_with_time_horizontal(tmp_path):
    app = create_application([])
    path = save_image(tmp_path, np.zeros((20, 20)))
    view = MainWindow()
    audio = view._load_image_audio(path, duration=.1, max_frequency=2000)
    view._image_loaded((audio, make_spectrogram(audio.samples, audio.sample_rate)))
    assert view.document.dirty
    graph = view.spectrogram_widget
    assert graph.plot.getAxis("bottom").labelText == "Time"
    assert graph.plot.getAxis("left").labelText == "Frequency"
    assert graph._frequency_max is None
    assert graph.current_data is not None
    for widget in (graph, view.live_spectrogram):
        _, colors = widget.colormap.getStops()
        assert all(color[1] > color[0] and color[1] > color[2] for color in colors)
    view.document.saved_samples = view.document.audio.samples
    view.close()
    app.processEvents()


def test_audio_spectrogram_matches_independent_scipy_amplitudes():
    rate, size = 44100, 2048
    t = np.arange(44100) / rate
    # Bin-centred tones make frequency and relative amplitude unambiguous.
    audio = .6 * np.sin(2*np.pi*(40*rate/size)*t) + .2 * np.sin(2*np.pi*(130*rate/size)*t)
    actual = make_spectrogram(audio, rate)
    f, times, z = signal.stft(audio, rate, nperseg=size, noverlap=1536,
                             boundary="zeros", padded=False)
    expected = abs(z) * 2
    expected[[0, -1]] /= 2
    np.testing.assert_allclose(actual.magnitude, expected, rtol=1e-5, atol=1e-7)
    assert np.argmax(actual.magnitude[:, 20]) == 40
    assert actual.magnitude[40, 20] / actual.magnitude[130, 20] == pytest.approx(3, rel=.001)


def test_default_image_import_preserves_pitch_timing_and_relative_strength(tmp_path):
    rate, size, columns = 44100, 2048, 129
    pixels = np.zeros((1025, columns), dtype=np.uint8)
    # Two sequential notes, with the second half as strong and silence between.
    pixels[1024-40, 8:48] = 240
    pixels[1024-100, 80:120] = 120
    path = save_image(tmp_path, pixels)
    audio = MainWindow._load_image_audio(path).samples
    assert len(audio) == 128 * 512
    f, t, z = signal.stft(audio, rate, nperseg=size, noverlap=1536)
    magnitude = abs(z)
    first = (t > .2) & (t < .45)
    second = (t > 1.0) & (t < 1.3)
    gap = (t > .65) & (t < .8)
    peaks = f[np.argmax(magnitude, axis=0)]
    assert np.max(abs(peaks[first] - 40*rate/size)) <= rate/size
    assert np.max(abs(peaks[second] - 100*rate/size)) <= rate/size
    strength = np.sqrt(np.sum(magnitude**2, axis=0))
    assert np.median(strength[second]) / np.median(strength[first]) == pytest.approx(.5, abs=.08)
    assert np.max(strength[gap]) < np.median(strength[first]) * .01
    active = strength > np.max(strength) * .15
    assert abs(t[np.flatnonzero(active)[0]] - 8*512/rate) < 2*512/rate
    assert abs(t[np.flatnonzero(active)[-1]] - 119*512/rate) < 2*512/rate


def test_default_image_import_rising_chirp(tmp_path):
    rate, size, columns = 44100, 2048, 129
    bins = np.rint(np.linspace(20, 100, columns)).astype(int)
    pixels = np.zeros((1025, columns), dtype=np.uint8)
    pixels[1024-bins, np.arange(columns)] = 255
    audio = MainWindow._load_image_audio(save_image(tmp_path, pixels)).samples
    f, t, z = signal.stft(audio, rate, nperseg=size, noverlap=1536)
    peaks = f[np.argmax(abs(z), axis=0)]
    expected = (20 + 80*t/(128*512/rate))*rate/size
    middle = (t > .1) & (t < 1.35)
    assert np.median(abs(peaks[middle] - expected[middle])) < rate/size
    assert np.corrcoef(t[middle], peaks[middle])[0, 1] > .99


def test_default_import_recovers_independently_encoded_audio(tmp_path):
    # Encode a real two-tone signal using SciPy, not SonicCraft's transforms.
    rate, size, count = 44100, 2048, 65536
    t = np.arange(count) / rate
    envelope = np.where(t < .65, .65, .25)
    reference = (envelope * np.sin(2*np.pi*(40*rate/size)*t)
                 + .15*np.sin(2*np.pi*(100*rate/size)*t))
    _, _, z = signal.stft(reference, rate, nperseg=size, noverlap=1536)
    target = abs(z)
    pixels = np.rint(target[::-1] / target.max() * 255).astype(np.uint8)
    recovered = MainWindow._load_image_audio(save_image(tmp_path, pixels)).samples
    _, _, rebuilt = signal.stft(recovered, rate, nperseg=size, noverlap=1536)
    actual = abs(rebuilt)
    # Global loudness is normalized during import; compare spectral shape.
    scale = np.sum(actual*target) / np.sum(actual**2)
    relative_error = np.linalg.norm(actual*scale-target) / np.linalg.norm(target)
    assert len(recovered) == len(reference)
    assert relative_error < .1
    assert np.corrcoef(actual.ravel(), target.ravel())[0, 1] > .99


@pytest.mark.parametrize("kind", ["tall", "wide"])
def test_downsampling_preserves_thin_marks(tmp_path, kind):
    if kind == "tall":
        pixels = np.zeros((2049, 33), dtype=np.uint8)
        pixels[1001] = 255  # Between original interpolation samples.
    else:
        pixels = np.zeros((33, 4095), dtype=np.uint8)
        pixels[:, 1001] = 255
    magnitude, _ = image_magnitude(save_image(tmp_path, pixels), 44100)
    assert magnitude.max() == 1
    if kind == "tall":
        actual = np.argmax(magnitude[:, 10]) * 44100 / 2048
        expected = (1 - 1001/2048) * 22050
        assert abs(actual-expected) <= 44100/2048
    else:
        actual = np.argmax(magnitude[100])
        expected = 1001/4094 * 2047
        assert abs(actual-expected) <= 1


def test_single_row_covers_frequency_range(tmp_path):
    magnitude, _ = image_magnitude(save_image(tmp_path, np.full((1, 33), 255)), 44100)
    np.testing.assert_allclose(magnitude, 1)


def test_transparency_controls_intensity(tmp_path):
    pixels = np.full((33, 33, 4), 255, dtype=np.uint8)
    pixels[:, :, 3] = 0
    pixels[16, :, 3] = 128
    magnitude, _ = image_magnitude(save_image(tmp_path, pixels), 44100)
    assert magnitude.max() == pytest.approx(128/255)
    assert np.all(magnitude[0] == 0) and np.all(magnitude[-1] == 0)


def test_exif_orientation_matches_visible_pixels(tmp_path):
    pixels = np.zeros((33, 65), dtype=np.uint8)
    pixels[8, 10:40] = 255
    image = Image.fromarray(pixels)
    exif = Image.Exif()
    exif[274] = 6
    path = tmp_path / "oriented.png"
    image.save(path, exif=exif)
    expected_path = tmp_path / "visible.png"
    image.transpose(Image.Transpose.ROTATE_270).save(expected_path)
    actual, length = image_magnitude(path, 44100)
    expected, expected_length = image_magnitude(expected_path, 44100)
    assert length == expected_length
    np.testing.assert_allclose(actual, expected)


def test_save_spectrogram_png_and_restore_selection_on_failure(tmp_path):
    from soniccraft.desktop.spectrogram_widget import SpectrogramWidget
    app = create_application([])
    widget = SpectrogramWidget()
    widget.resize(1000, 500)
    widget.show()
    app.processEvents()
    assert not widget.save_button.isEnabled()
    with pytest.raises(ValueError, match="Generate"):
        widget.save_image(tmp_path / "empty.png")
    rate = 44100
    t = np.arange(rate) / rate
    widget.set_data(make_spectrogram(.5*np.sin(2*np.pi*1000*t), rate))
    app.processEvents()
    assert widget.save_button.isEnabled()
    path = tmp_path / "spectrogram.png"
    widget.save_image(path)
    with Image.open(path) as result:
        assert result.format == "PNG" and result.width == 1600
        assert result.height > 200
        rgb = np.asarray(result.convert("RGB")).astype(int)
        assert np.count_nonzero((rgb[:,:,1] > rgb[:,:,0]+15) & (rgb[:,:,1] > rgb[:,:,2]+15)) > 100
        # Pink selection handles are excluded from the saved graph.
        assert not np.any(np.all(rgb == [255, 172, 166], axis=2))
    assert widget.mask_roi.isVisible()
    with pytest.raises(OSError):
        widget.save_image(tmp_path / "missing" / "image.png")
    assert widget.mask_roi.isVisible()
    widget.clear()
    assert not widget.save_button.isEnabled()
    widget.close()
