"""Numerical and UI regressions for final integration fixes."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
from dataclasses import replace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QMessageBox

from soniccraft.desktop.analysis import make_spectrum, make_spectrogram
from soniccraft.desktop.audio_engine import Microphone
from soniccraft.desktop.document import AudioData
from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.processing import mask_spectrum, process
from soniccraft.dsp.noise_reduction import estimate_noise_profile, spectral_subtraction
from soniccraft.dsp.transforms import fft_spectrum, magnitude_to_db


@pytest.fixture
def window():
    app = create_application([])
    view = MainWindow()
    view.errors = []
    view.error = view.errors.append
    yield view
    wait_jobs(view)
    if view.document.audio:
        view.document.saved_samples = view.document.audio.samples
    view.close()
    view.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def wait_jobs(view):
    deadline = time.monotonic() + 20
    while any(getattr(view, key) is not None for key in ("job", "spectrum_job", "preview_job", "live_job")):
        assert time.monotonic() < deadline, "DSP worker did not finish"
        QCoreApplication.processEvents()
        time.sleep(.005)
    QCoreApplication.processEvents()


def test_long_spectrum_preserves_hz_and_includes_late_sound():
    rate = 32768
    samples = np.zeros(rate * 12)
    samples[-rate * 4:] = .4 * np.sin(2 * np.pi * 10000 * np.arange(rate * 4) / rate)
    spectrum = make_spectrum(samples, rate)
    assert spectrum.frequencies[-1] == rate / 2
    assert spectrum.frequencies[np.argmax(spectrum.magnitude)] == 10000
    assert spectrum.magnitude.max() > .1


def test_bounded_spectrogram_keeps_brief_events_between_old_hops():
    samples = np.zeros(400000)
    samples[2000:2512] = .5 * np.sin(2 * np.pi * 1000 * np.arange(512) / 8000)
    data = make_spectrogram(samples, 8000, 512, max_frames=40)
    assert data.values.shape[1] <= 40
    assert data.magnitude[64].max() > .45


def test_opposite_phase_stereo_remains_visible_in_spectrogram():
    tone = .5 * np.sin(2 * np.pi * 1000 * np.arange(8000) / 8000)
    mono = make_spectrogram(tone, 8000, 512)
    stereo = make_spectrogram(np.column_stack((tone, -tone)), 8000, 512)
    np.testing.assert_allclose(stereo.magnitude, mono.magnitude)


def test_spectrum_display_peak_agrees_with_both_scales(window):
    rate = 8000
    t = np.arange(rate) / rate
    samples = np.column_stack((.8 * np.sin(2*np.pi*500*t), .1*np.sin(2*np.pi*1500*t)))
    spectrum = fft_spectrum(samples, rate)
    window.spectrum_widget.set_spectrum(spectrum)
    x, y = window.spectrum_widget.plot_curve.getData()
    assert x[np.argmax(y)] == 500
    np.testing.assert_allclose(y, magnitude_to_db(spectrum.magnitude.mean(axis=1)))
    window.spectrum_widget.scale_combo.setCurrentIndex(1)
    x, y = window.spectrum_widget.plot_curve.getData()
    assert x[np.argmax(y)] == 500
    assert '500.0 Hz' in window.spectrum_widget.info_label.text()


def test_stale_long_analysis_cannot_replace_new_document(window):
    rate = 8000
    window._loaded(AudioData(np.sin(2*np.pi*1000*np.arange(300000)/rate)*.2, rate))
    window._loaded(AudioData(np.sin(2*np.pi*500*np.arange(rate)/rate)*.2, rate))
    wait_jobs(window)
    assert '500.0 Hz' in window.spectrum_widget.info_label.text()


def test_channel_selection_drives_fft_and_spectral_mask(window):
    rate = 8192
    t = np.arange(rate) / rate
    samples = np.column_stack((.4*np.sin(2*np.pi*512*t), .3*np.sin(2*np.pi*1024*t)))
    audio = AudioData(samples, rate)
    window._loaded(audio)
    window.target_channel_combo.setCurrentIndex(2)
    assert '1024.0 Hz' in window.spectrum_widget.info_label.text()
    output = mask_spectrum(audio, (0, rate), (0, 1, 480, 544), n_fft=1024, target_channel=0)
    np.testing.assert_array_equal(output[:, 1], samples[:, 1])
    assert np.sqrt(np.mean(output[1024:-1024, 0]**2)) < .01
    with pytest.raises(ValueError, match='overlap'):
        mask_spectrum(audio, (0, rate), (2, 3, 0, 1000))


def test_selected_noise_channel_uses_its_own_profile():
    rng = np.random.default_rng(12)
    noise = rng.normal(0, [.01, .2], (8192, 2))
    profile = estimate_noise_profile(noise[:4096], 8192, n_fft=512)
    audio = AudioData(noise, 8192)
    result = process(audio, (0, 8192), 'subtraction', dict(profile=profile, target_channel=0))
    expected = spectral_subtraction(noise[:, 0], 8192, replace(profile, magnitude=profile.magnitude[:, 0]))
    np.testing.assert_allclose(result[:, 0], expected)
    np.testing.assert_array_equal(result[:, 1], noise[:, 1])


def test_mixdown_preserves_unsaved_work_and_marks_result_unsaved(window):
    window._loaded(AudioData(np.ones(80)*.1, 8000, 'original.wav'))
    window.document.commit(np.ones(80)*.2)
    current = window.document.audio
    tracks = [dict(samples=np.ones(80)*.3, sample_rate=8000)]
    with patch.object(window, 'confirm_discard', return_value=False):
        window._perform_mixdown(tracks, 8000)
    assert window.document.audio is current
    with patch.object(window, 'confirm_discard', return_value=True):
        window._perform_mixdown(tracks, 8000)
    wait_jobs(window)
    assert window.document.dirty
    assert window.document.audio.filename == 'Master Mixdown'
    assert not window.errors


def test_mixer_tracks_can_be_removed_and_icon_is_packaged(window):
    window.mixer._add_track(AudioData(np.zeros(32), 8000, 'first.wav'))
    window.mixer._add_track(AudioData(np.zeros(32), 16000, 'second.wav'))
    window.mixer._remove_track(window.mixer.tracks[1])
    assert len(window.mixer.tracks) == 1
    window.mixer._remove_track(window.mixer.tracks[0])
    assert not window.mixer.mixdown_button.isEnabled()
    assert not window.windowIcon().isNull()


def test_recording_keeps_final_queued_block_and_is_unsaved(window):
    driver = MagicMock()
    driver.query_devices.return_value = {"default_samplerate": 8000}
    driver.InputStream.return_value.active = True
    window.microphone = Microphone(driver)
    window.sidebar.record_live.setChecked(True)
    window.start_live()
    window.live_timer.stop()
    samples = np.linspace(-.2, .2, 80)
    window.microphone._callback(samples[:, None], len(samples), None, None)
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
        window.stop_live()
    np.testing.assert_allclose(window.document.audio.samples, samples)
    assert window.document.dirty
    assert not window.live_recording_blocks


def test_recording_budget_stops_growth(window):
    window.sidebar.record_live.setChecked(True)
    with patch('soniccraft.desktop.main_window.RECORDING_BYTE_LIMIT', 80):
        assert window._capture_recording([np.arange(20)])
        assert window.live_recording_frames == 10
        assert window._capture_recording([np.arange(20)])
        assert sum(len(block) for block in window.live_recording_blocks) == 10
    window.sidebar.record_live.setChecked(False)


def test_region_starts_inside_selected_time_range(window):
    data = make_spectrogram(np.zeros(8000), 8000, offset=5)
    window.spectrogram_widget.set_data(data)
    assert window.spectrogram_widget.mask_roi.pos().x() == 5
    assert window.spectrogram_widget.mask_button.isEnabled()
    window.spectrogram_widget.clear()
    assert not window.spectrogram_widget.mask_button.isEnabled()
