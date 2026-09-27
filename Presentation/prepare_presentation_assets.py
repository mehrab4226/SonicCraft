"""Build clear, reproducible plots and the stereo demo for the slide deck."""

from pathlib import Path
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / '.cache/presentation-deps'))
sys.path.insert(0, str(ROOT / 'backend/src'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from scipy import signal
import soundfile as sf

from soniccraft.dsp.effects import apply_fade
from soniccraft.dsp.filters import butterworth, frequency_response, peaking_eq_sections, ParametricEQBand
from soniccraft.dsp.noise_reduction import estimate_noise_profile, spectral_subtraction
from soniccraft.dsp.transforms import fft_spectrum, stft

ASSETS = ROOT / 'Presentation/assets'
DEMO = ROOT / 'Presentation/demo'
ASSETS.mkdir(parents=True, exist_ok=True)
DEMO.mkdir(parents=True, exist_ok=True)
for filename in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf'):
    font_manager.fontManager.addfont('C:/Windows/Fonts/' + filename)
plt.rcParams.update({
    'font.family': 'Segoe UI', 'font.size': 14, 'axes.labelsize': 14,
    'xtick.labelsize': 12, 'ytick.labelsize': 12, 'svg.fonttype': 'path',
    'axes.spines.top': False, 'axes.spines.right': False,
})
BG = '#faf8f3'
FG = '#202c35'
MUTED = '#52616b'
AMBER = '#966016'
CORAL = '#b04b3c'
GRID = '#c9d0cf'
CMAP = LinearSegmentedColormap.from_list(
    'soniccraft', ['#faf8f3', '#dcebdc', '#9bc59d', '#4e8d65', '#18533c']
)


def axes(rows=1, height=3.65):
    fig, grid = plt.subplots(rows, 1, figsize=(7.4, height), layout='constrained', squeeze=False)
    fig.patch.set_facecolor(BG)
    for ax in grid.flat:
        ax.set_facecolor(BG)
        ax.tick_params(colors=MUTED)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        for spine in ax.spines.values():
            spine.set_color(GRID)
        ax.grid(alpha=.14, color=MUTED)
    return fig, grid[:, 0]


def save(fig, name):
    path = ASSETS / f'{name}.svg'
    fig.savefig(path, facecolor=BG)
    path.write_text(re.sub(r'[ \t]+(?=\r?$)', '', path.read_text(encoding='utf-8'), flags=re.MULTILINE), encoding='utf-8')
    plt.close(fig)


RATE = 16000
rng = np.random.default_rng(220)
t = np.arange(6 * RATE) / RATE
envelope = np.where((t >= .8) & (t <= 5.6), .4 + .6 * np.sin(2 * np.pi * t) ** 2, 0)
clean = envelope * (
    .16 * np.sin(2 * np.pi * 220 * t)
    + .09 * np.sin(2 * np.pi * 1000 * t)
    + .045 * np.sin(2 * np.pi * 2000 * t)
)
noise = .018 * rng.standard_normal(len(t)) + .012 * np.sin(2 * np.pi * 60 * t)
demo = np.column_stack([
    clean + noise,
    .8 * clean + .018 * rng.standard_normal(len(t)) + .012 * np.sin(2 * np.pi * 60 * t),
])
sf.write(DEMO / 'SonicCraft_demo_16k.wav', demo, RATE, subtype='PCM_24')
sf.write(DEMO / 'Clean_reference_16k.wav', np.column_stack([clean, .8 * clean]), RATE, subtype='PCM_24')


def peak_envelope(samples, bins=420):
    edges = np.linspace(0, len(samples), bins + 1, dtype=int)
    times = (edges[:-1] + edges[1:]) / (2 * RATE)
    peaks = np.array([np.max(np.abs(samples[a:b])) for a, b in zip(edges[:-1], edges[1:])])
    return times, peaks


# The same six-second source, with a selected region faded at its edges.
first, last = int(1.4 * RATE), int(4.3 * RATE)
edited = clean.copy()
edited[first:last] = apply_fade(
    clean[first:last], RATE, fade_in_seconds=.55, fade_out_seconds=.55, curve='linear'
)
fig, plots = axes(2, 3.9)
for ax, samples, name in (
    (plots[0], clean, 'Original recording'),
    (plots[1], edited, 'After fading the selection'),
):
    times, peaks = peak_envelope(samples)
    selected = (times >= 1.4) & (times <= 4.3)
    ax.fill_between(times, -peaks, peaks, color=MUTED)
    ax.fill_between(times, -peaks, peaks, where=selected, color=AMBER, interpolate=True)
    for boundary in (1.4, 4.3):
        ax.axvline(boundary, color=CORAL, lw=1, ls='--')
    ax.text(.02, .82, name, transform=ax.transAxes, color=FG, fontsize=13)
    ax.set(xlim=(0, 6), ylim=(-.38, .38), ylabel='Level')
plots[0].set_xticklabels([])
plots[1].set_xlabel('Time (s)')
save(fig, 'editing')

# Two common filter choices reveal which side of the cutoff is retained.
fig, (ax,) = axes()
for kind, color, name in (
    ('lowpass', AMBER, 'Low-pass: keeps low tones'),
    ('highpass', CORAL, 'High-pass: keeps high tones'),
):
    response = frequency_response(butterworth(1000, RATE, kind=kind, order=4), RATE, points=8192)
    ax.plot(response.frequencies, response.magnitude_db, color=color, lw=2.6, label=name)
ax.axvline(1000, color=MUTED, lw=1, ls='--')
ax.text(1050, -58, '1000 Hz cutoff', color=MUTED, fontsize=12)
ax.set(xlabel='Frequency (Hz)', ylabel='Level change (dB)', xlim=(0, 5000), ylim=(-65, 5))
ax.legend(frameon=False, labelcolor=FG, fontsize=12, loc='lower right')
save(fig, 'filter')

# Only two of nine bands are moved. The rest remain at zero.
sections = np.vstack([
    peaking_eq_sections(ParametricEQBand(120, 5, 1.2), 44100),
    peaking_eq_sections(ParametricEQBand(4000, -4, 1.2), 44100),
])
response = frequency_response(sections, 44100, points=16384)
fig, (ax,) = axes()
ax.axhline(0, color=MUTED, lw=1.2, ls='--', label='Flat')
ax.semilogx(response.frequencies[1:], response.magnitude_db[1:], color=AMBER, lw=2.8, label='Adjusted')
ax.axvline(120, color=AMBER, lw=.9, ls=':')
ax.axvline(4000, color=CORAL, lw=.9, ls=':')
ax.text(78, 5.8, 'Bass boost', color=AMBER, fontsize=12)
ax.text(2700, -5.7, 'Upper-mid cut', color=CORAL, fontsize=12)
ax.set(xlabel='Frequency (Hz)', ylabel='Level change (dB)', xlim=(40, 20000), ylim=(-7, 7))
ax.set_xticks([60, 120, 500, 1000, 4000, 16000], ['60', '120', '500', '1k', '4k', '16k'])
ax.legend(frameon=False, labelcolor=FG, fontsize=12, loc='upper right')
save(fig, 'eq')

# A known clean two-tone signal plus independent white noise and a noise-only profile.
tt = np.arange(2 * RATE) / RATE
reference = .22 * np.sin(2 * np.pi * 500 * tt) + .09 * np.sin(2 * np.pi * 1500 * tt)
noisy = reference + rng.normal(0, .055, len(tt))
profile = estimate_noise_profile(rng.normal(0, .055, RATE), RATE, n_fft=2048, hop_length=512)
denoised = spectral_subtraction(noisy, RATE, profile, strength=1.5)
fig, (ax,) = axes()
for samples, color, name in ((noisy, MUTED, 'Before'), (denoised, AMBER, 'After reduction')):
    frequency, power = signal.welch(samples, RATE, nperseg=2048)
    ax.plot(frequency, 10 * np.log10(np.maximum(power, 1e-15)), color=color, lw=1.9, label=name)
ax.text(540, -28, 'Signal', color=FG, fontsize=12)
ax.text(2450, -65, 'Noise floor', color=MUTED, fontsize=12)
ax.set(xlabel='Frequency (Hz)', ylabel='Power (dB/Hz)', xlim=(0, 3500), ylim=(-90, -20))
ax.legend(frameon=False, labelcolor=FG, fontsize=12, loc='upper right')
save(fig, 'noise')

# The FFT plot uses a known two-tone test, so peaks have unambiguous meanings.
tt = np.arange(4096) / RATE
two_tone = .4 * np.sin(2 * np.pi * 500 * tt) + .2 * np.sin(2 * np.pi * 1500 * tt)
spectrum = fft_spectrum(two_tone, RATE, window='hann')
fig, (ax,) = axes()
ax.plot(spectrum.frequencies, spectrum.magnitude_db, color=CORAL, lw=2.3)
for frequency, level in ((500, .4), (1500, .2)):
    ax.axvline(frequency, color=AMBER, lw=.8, alpha=.45)
    ax.text(frequency + 35, 20 * np.log10(level) + 3, f'{frequency} Hz', color=FG, fontsize=12)
ax.set(xlabel='Frequency (Hz)', ylabel='Magnitude (dBFS)', xlim=(0, 2200), ylim=(-90, 0))
save(fig, 'fft')

# Three distinct notes make the meaning of each bright horizontal band obvious.
note_audio = np.zeros(3 * RATE)
for index, (frequency, level) in enumerate(((300, .30), (600, .40), (900, .25))):
    local_time = np.arange(RATE) / RATE
    fade = np.minimum(np.minimum(local_time / .05, (1 - local_time) / .05), 1).clip(0, 1)
    note_audio[index * RATE:(index + 1) * RATE] = fade * level * np.sin(2 * np.pi * frequency * local_time)
spec = stft(note_audio, RATE, n_fft=1024, hop_length=256)
magnitudes = np.abs(spec.spectrum)
db = 20 * np.log10(np.maximum(magnitudes, 1e-8) / magnitudes.max())
fig, (ax,) = axes()
ax.pcolormesh(spec.times, spec.frequencies, db, cmap=CMAP, vmin=-65, vmax=0, shading='auto', rasterized=True)
ax.grid(False)
for boundary in (1, 2):
    ax.axvline(boundary, color=FG, alpha=.36, lw=.9, ls='--')
for x, name in ((.22, '300 Hz'), (1.22, '600 Hz'), (2.22, '900 Hz')):
    ax.text(x, 1910, name, color=FG, fontsize=13)
ax.set(xlabel='Time (s)', ylabel='Frequency (Hz)', xlim=(0, 3), ylim=(0, 2200), yticks=[0, 300, 600, 900, 1500, 2100])
save(fig, 'spectrogram')

# Illustrate the same analysis in a rolling view with a current-time edge.
fig, plots = axes(2, 3.9)
plots[0].pcolormesh(spec.times - 3, spec.frequencies, db, cmap=CMAP, vmin=-65, vmax=0, shading='auto', rasterized=True)
plots[0].grid(False)
plots[0].set(xlim=(-3, 0), ylim=(0, 2200), ylabel='Hz', yticks=[300, 900, 1500, 2100])
plots[0].text(-2.9, 1850, 'Rolling frequency view', color=FG, fontsize=12)
times, peaks = peak_envelope(note_audio)
plots[1].fill_between(times - 3, -peaks, peaks, color=CORAL)
plots[1].set(xlim=(-3, 0), ylim=(-.55, .55), xlabel='Seconds before now', ylabel='Level')
plots[1].text(-2.9, .35, 'Incoming audio', color=FG, fontsize=12)
for ax in plots:
    ax.axvline(0, color=AMBER, lw=2)
save(fig, 'live')

# The screenshot is from the real interface with the included deterministic clip.
from PyQt6.QtGui import QFontDatabase
from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.document import AudioData

app = create_application([])
for filename in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + filename)
window = MainWindow()
window._loaded(AudioData(demo, RATE, 'SonicCraft demo.wav'))
window.resize(1440, 960)
window.sidebar.navigate('eq')
window.show()
app.processEvents()
window.player.position = 2 * RATE
window._tick()
app.processEvents()
window.grab().save(str(ASSETS / 'app-workspace.png'))
window.document.saved_samples = window.document.audio.samples
window.close()
