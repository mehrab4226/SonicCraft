"""The fourteen-slide SonicCraft evaluation presentation."""

page('SonicCraft', show_title=False)
label('CSE 220  /  Final project evaluation', 58, 50, size=13)
text('SonicCraft', 54, 109, 76, 'SegoeBold')
text('Hear the change.\nSee the signal.', 58, 207, 31, 'SegoeLight', leading=39)
for i in range(135):
    x = 510 + i * 3
    envelope = 18 + 94 * (math.sin(i * .053) ** 2) * (.45 + .55 * math.sin(i * .117) ** 2)
    line(x, 254 - envelope, x, 254 + envelope, AMBER if i > 47 else '#c9c0af', 1.7)
line(651, 128, 651, 380, CORAL, 1)
text('Md Mehrab Hossain', 58, 385, 20, 'SegoeBold')
text('2305108', 58, 416, 17, 'Mono', MUTED)
text('Mahbubul Islam Mahi', 498, 385, 20, 'SegoeBold')
text('2305116', 498, 416, 17, 'Mono', MUTED)
text('Python desktop audio editor', 58, 462, 14, col=MUTED)

page('Motivation and problem', 'Connect signal-processing concepts to changes we can hear.', dark=False,
     source='Actual SonicCraft interface with the included stereo demo.')
label('Motivation', 54, 173)
text('Learn DSP by listening and experimenting.', 54, 201, 25, 'SegoeBold', w=263, max_lines=3)
label('Problem addressed', 54, 333)
text('Noise and uneven levels make recordings harder to use.', 54, 365, 23, w=267, leading=31, max_lines=3)
image('app-workspace.png', 343, 162, 563, 323)

page('Overall approach', 'A repeatable workflow: inspect, preview, commit and compare.')
for y, title, detail in [
    (181, 'Inspect', 'Open audio, select a region and examine its signal.'),
    (278, 'Preview', 'Adjust a tool and hear the effect during playback.'),
    (375, 'Commit and compare', 'Apply the edit, compare with the original, then export.'),
]:
    text(title, 54, y, 27, 'SegoeBold', AMBER, w=315, max_lines=2)
    text(detail, 400, y, 24, w=490, max_lines=2, leading=32)

page('Architecture and design', 'One audio document connects editing, processing and playback.',
     source='Implementation: desktop/main_window.py, document.py, jobs.py, audio_engine.py')
for x, kicker, name, caption in [
    (54, 'INTERFACE', 'PyQt6 + PyQtGraph', 'Controls and visualizations'),
    (363, 'SIGNAL PROCESSING', 'NumPy + SciPy', 'Process selected samples'),
    (672, 'AUDIO OUTPUT', 'sounddevice', 'Play the current buffer'),
]:
    rect(x, 181, 234, 120, '#edf0ed')
    label(kicker, x + 17, 199, size=12)
    text(name, x + 17, 232, 22, 'SegoeBold', w=211, max_lines=1)
    text(caption, x + 17, 271, 15, col=MUTED, w=215, max_lines=1)
arrow(294, 241, 355, 241)
arrow(603, 241, 664, 241)
rect(363, 354, 234, 100, '#f0e8d9')
label('Audio document', 380, 370)
text('Original + edit snapshots', 380, 399, 16, w=207, max_lines=2)
arrow(480, 349, 480, 308)
text('Background workers\nkeep controls responsive.', 54, 366, 22, w=265, leading=33)
text('Import / export\nSoundFile: WAV and FLAC', 672, 370, 20, w=240, leading=32)

page('Relevant theory and concepts', 'The same signal can be studied in time and frequency.',
     source='Implemented in dsp/effects.py, filters.py, transforms.py and noise_reduction.py.')
for y, concept, explanation in [
    (185, 'Samples and amplitude', 'Gain scales samples; fades change their level over time.'),
    (284, 'Fourier analysis and filters', 'FFT reveals frequency content; filters and EQ reshape it.'),
    (383, 'Windowed analysis', 'Short FFT windows form a spectrogram and guide noise reduction.'),
]:
    text(concept, 54, y, 25, 'SegoeBold', AMBER, w=315, max_lines=2)
    text(explanation, 400, y, 23, w=490, max_lines=2, leading=31)

feature('Edit & Dynamics', 'Shape the selected part of a recording.', 'EDIT & DYNAMICS', [
    'Select, trim or remove a time range.',
    'Adjust level or normalize the peak.',
    'Fade edges for a smooth entrance or exit.',
], 'editing', 'Implementation: desktop/processing.py and dsp/effects.py.',
    'A real clip: the highlighted interval fades at both ends.')

feature('Frequency filter', 'Keep wanted frequencies and reduce others.', 'FILTERS & EQUALIZER', [
    'Choose low-pass, high-pass or band filters.',
    'Set the cutoff to shape what passes.',
    'Hear the result while adjusting.',
], 'filter', 'Implementation: dsp/filters.py and desktop/effects_panel.py.',
    'Two filter settings at the same cutoff frequency.')

feature('9-band equalizer', 'Change the tonal balance of the recording.', 'FILTERS & EQUALIZER', [
    'Move a band to boost or reduce its range.',
    'Combine bands across bass, mids and treble.',
    'Apply EQ to save what you hear.',
], 'eq', 'Implementation: dsp/filters.py and desktop/processing.py.',
    'Example: bass boost and upper-mid cut; other bands stay flat.')

feature('Noise reduction', 'Reduce steady background sound.', 'NOISE REDUCTION', [
    'Capture a section containing only noise.',
    'Estimate its frequency pattern.',
    'Reduce matching noise in the selection.',
], 'noise', 'Implementation: dsp/noise_reduction.py; graph uses a synthetic reference.',
    'The noise floor drops while two signal peaks remain.')

feature('Spectrum analyzer', 'See which frequencies exist in the selection.', 'SPECTRUM ANALYZER', [
    'Select audio and calculate its FFT.',
    'Read the strongest frequency peaks.',
    'Compare the spectrum before and after edits.',
], 'fft', 'Implementation: dsp/transforms.py and desktop/analysis.py.',
    'A two-tone example produces peaks at 500 Hz and 1500 Hz.')

feature('Spectrogram', 'See how frequency content changes with time.', 'SPECTROGRAM', [
    'Time runs left to right; frequency runs upward.',
    'Green bands show strong components.',
    'Find when a tone or sound occurs.',
], 'spectrogram', 'Implementation: desktop/analysis.py; three-note example uses the app STFT.',
    'Three notes played in sequence: 300, 600 and 900 Hz.')

feature('Live spectrogram', 'Monitor microphone sound as it arrives.', 'LIVE SPECTROGRAM', [
    'Capture microphone audio in short blocks.',
    'Refresh a rolling time-frequency view.',
    'Optionally record the input for editing.',
], 'live', 'Implementation: desktop/audio_engine.py and main_window.py.',
    'Illustration with generated notes; the live view uses microphone input.')

page('From preview to finished audio', 'Final result: inspect, edit, hear and export in one desktop application.',
     source='Implementation: desktop/main_window.py, effects_panel.py, document.py.')
steps = [
    ('Change', 'Adjust a control'),
    ('Hear', 'Preview during playback'),
    ('Apply', 'Save an undoable snapshot'),
    ('Export', 'Write the audio file'),
]
for i, (title, caption) in enumerate(steps):
    x = 54 + i * 218
    rect(x, 176, 197, 132, '#edf0ed', r=8)
    c.setFillColor(color(AMBER))
    c.circle(x + 27, H - 204, 8, stroke=0, fill=1)
    text(title, x + 17, 221, 25, 'SegoeBold', w=170, max_lines=1)
    text(caption, x + 17, 261, 16, col=MUTED, w=175, max_lines=2)
    if i < 3: arrow(x + 199, 234, x + 215, 234)
label('Two reset scopes', 54, 341)
rect(54, 374, 411, 92, '#f0e8d9', r=8)
rect(495, 374, 411, 92, '#f0e8d9', r=8)
text('Tool reset', 74, 392, 24, 'SegoeBold', AMBER)
text('Clears this tool\'s settings and preview.', 74, 428, 17, col=MUTED, w=365, max_lines=2)
text('Reset audio', 515, 392, 24, 'SegoeBold', AMBER)
text('Restores the original audio and all settings.', 515, 428, 17, col=MUTED, w=365, max_lines=2)

page('Explore the project in code', show_title=False, footer=False)
label('SonicCraft', 58, 72, size=14)
text('Explore the project\nin code.', 54, 165, 59, 'SegoeBold', w=835, leading=70, max_lines=2)
text('Source, documentation and a reproducible demo', 58, 339, 22, col=MUTED, w=838, max_lines=1)
text('github.com/mehrab4226/SonicCraft', 58, 405, 24, 'Mono', CORAL)
c.linkURL('https://github.com/mehrab4226/SonicCraft', (54, H - 445, 780, H - 393), relative=0, thickness=0)
