"""Slide content, executed by build_presentation.py with its drawing helpers."""

# Restore the original presentation structure. Feature copy is deliberately short.
page('SonicCraft',dark=True,show_title=False)
label('CSE 220  /  Final project evaluation',58,50,size=13)
text('SonicCraft',54,109,76,'SegoeBold')
text('Audio editing through\nSignals & Systems',58,206,31,'SegoeLight',leading=39)
for i in range(135):
    x=510+i*3
    envelope=18+94*(math.sin(i*.053)**2)*(.45+.55*math.sin(i*.117)**2)
    line(x,254-envelope,x,254+envelope,AMBER if i>47 else '#675748',1.7)
line(651,128,651,380,CORAL,1)
text('Md Mehrab Hossain',58,385,20,'SegoeBold')
text('2305108',58,416,17,'Mono',MUTED)
text('Mahbubul Islam Mahi',498,385,20,'SegoeBold')
text('2305115',498,416,17,'Mono',MUTED)
text('Python desktop application',58,462,14,col=MUTED)

page('Why SonicCraft?', 'Make a signal operation visible and audible.',dark=False,
     source='Actual SonicCraft interface. Screenshot uses the included synthetic stereo demo.')
label('The problem',54,173)
text('A noisy recording hides useful sound.',54,203,27,'SegoeBold',w=255,max_lines=3)
label('Our approach',54,329)
text('Inspect the signal.\nAdjust a parameter.\nHear the result.',54,357,21,w=270,leading=31)
image('app-workspace.png',343,162,563,323)

page('How the application works','One audio document connects the controls, DSP and playback.',
     source='Implementation: desktop/main_window.py, document.py, jobs.py, audio_engine.py')
for x,kicker,name,caption in [(54,'INTERFACE','PyQt6 + PyQtGraph','Parameters and selection'),
        (363,'EFFECT WORKER','NumPy + SciPy','Process selected samples'),
        (672,'AUDIO OUTPUT','sounddevice','Play the preview buffer')]:
    rect(x,181,234,120,'#202024')
    label(kicker,x+17,199,size=12)
    text(name,x+17,232,22,'SegoeBold',w=211,max_lines=1)
    text(caption,x+17,271,15,col=MUTED,w=215,max_lines=1)
arrow(294,241,355,241);arrow(603,241,664,241)
rect(363,354,234,100,'#29251f')
label('Audio document',380,370)
text('Original + committed audio',380,399,16,w=207,max_lines=2)
arrow(480,349,480,308)
text('Apply commits one edit.\nUndo restores a snapshot.',54,366,22,w=265,leading=33)
text('Import / export\nSoundFile: WAV and FLAC',672,370,20,w=240,leading=32)

page('Waveform and selection','Choose which part of the audio to edit.',
     source='Implementation: desktop/waveform_widget.py and processing.py; plot is the current app.')
image('stereo-waveform.png',54,155,852,215)
label('Theory connection',54,387)
equation(r'n=\operatorname{round}(tF_s)',54,416,300,44)
text('Time corresponds to sample position.',430,414,23,w=455,max_lines=2)

feature('Gain','Make audio louder or quieter.','Amplitude scaling',
        'Multiply each sample by a constant.',r'y[n]=10^{G/20}\,x[n]',
        'gain','Implementation: dsp/effects.py, apply_gain()')
feature('Frequency filters','Keep some frequencies and reduce others.','LTI systems',
        'The frequency response shapes the sound.',
        r'Y(e^{j\omega})=H(e^{j\omega})X(e^{j\omega})','filter',
        'Implementation: dsp/filters.py; theory: SciPy Butterworth documentation [2].')
feature('9-band equalizer','Adjust bass, midrange and treble.','Cascaded filters',
        'Each band controls part of the spectrum.',r'H(z)=\prod_{b=1}^{B}H_b(z)',
        'eq','Implementation: dsp/filters.py and desktop/processing.py; RBJ biquad theory [3].')
feature('FFT spectrum','See which frequencies are present.','Fourier decomposition',
        'Break a sound into frequency components.',
        r'X[k]=\sum_{n=0}^{N-1}x[n]e^{-j2\pi kn/N}','fft',
        'Implementation: dsp/transforms.py, fft_spectrum(); NumPy FFT reference [4].')
feature('Spectrogram','See how frequencies change over time.','Windowed Fourier analysis',
        'Analyze short sections of the sound.',
        r'\Delta f=\frac{F_s}{N},\quad\Delta t=\frac{R}{F_s}','spectrogram',
        'Implementation: desktop/analysis.py and dsp/transforms.py; STFT theory [5].')
feature('Noise reduction','Reduce unwanted background sound.','Spectral subtraction',
        'Estimate the noise, then reduce its spectrum.',
        r'\widehat A=\max(A-\alpha D,\,\beta A)','noise',
        'Implementation: dsp/noise_reduction.py; example uses synthetic noise. Theory [6].')

page('Preview, commit and recover','Parameter changes are temporary until Apply saves them to the audio.',
     source='Evidence: 77 pytest tests; desktop/audio_engine.py, jobs.py, document.py; measurements.json')
label('Design choices',54,174)
for y,title,body in [(211,'Responsive previews','Worker renders; callback keeps playing.'),
                     (303,'Controlled transitions','10 ms crossfade between audio buffers.'),
                     (395,'Two reset scopes','Tool reset clears settings. Main reset restores audio.')]:
    text(title,54,y,24,'SegoeBold',w=450,max_lines=1)
    text(body,54,y+35,18,col=MUTED,w=443,max_lines=2)
line(544,176,544,466,LINE)
text('77',591,181,72,'SegoeBold',AMBER)
text('automated tests pass',591,267,21,w=300)
label('Numerical checks',591,328)
text('+6.000 dB',591,360,31,'Mono',CORAL)
text('measured at the EQ center frequency',591,404,17,col=MUTED,w=300,max_lines=2)
text('Preview delay includes rendering time.',591,457,13,col=MUTED,w=310,max_lines=1)

page('Live demonstration','One six-second clip. A visible and audible result.',dark=False,
     source='Demo file: Presentation/demo/SonicCraft_demo_16k.wav. Total demo budget: 80 seconds.')
steps=[('00-10 s','Open + play','Hear the stereo signal and background noise.'),
       ('10-25 s','Change EQ','Move 1000 Hz, hear the preview, then Apply EQ.'),
       ('25-40 s','Compare resets','Reset EQ keeps the edit. Reset audio restores the source.'),
       ('40-65 s','Reduce noise','Capture 0-0.7 s. Select all. Preview subtraction and Apply.'),
       ('65-80 s','Inspect + export','Generate the spectrogram, then export the processed WAV.')]
for i,(duration,title,desc) in enumerate(steps):
    yy=162+i*62
    text(duration,54,yy+5,16,'Mono',GREY)
    text(title,183,yy,23,'SegoeBold',w=280,max_lines=1)
    text(desc,483,yy+2,17,col=GREY,w=422,max_lines=2)
    if i<4:line(183,yy+48,906,yy+48,'#d3ccc1',.7)

page('Questions',source='Source code: github.com/mehrab4226/SonicCraft',show_title=False)
text('Questions',54,89,67,'SegoeBold')
text('SonicCraft',56,210,30,'SegoeLight',AMBER)
text('A desktop application built around\nsamples, filters and Fourier analysis.',56,264,27,w=770,leading=39)
text('github.com/mehrab4226/SonicCraft',56,413,21,'Mono',CORAL)
c.linkURL('https://github.com/mehrab4226/SonicCraft',(54,H-446,677,H-409),relative=0,thickness=0)

# Q&A references are outside the timed presentation.
page('Sample editing','Work directly with sample indices and selected intervals.',appendix=True,
     source='Implementation: desktop/processing.py and dsp/effects.py. End index b is exclusive.')
rows=[('Trim','Keep only samples a through b - 1.',r'y[n]=x[n+a],\quad 0\leq n<b-a'),
      ('Reverse','Reverse time within the selected interval.',r'y[a+m]=x[b-1-m]'),
      ('Silence','Zero the interval without changing its duration.',r'y[n]=0,\quad a\leq n<b'),
      ('Delete','Remove the interval and join the two sides.',r'y=x[:a]\,\Vert\,x[b:]')]
for i,(title,desc,eq) in enumerate(rows):
    yy=161+i*78
    text(title,54,yy,23,'SegoeBold',AMBER)
    text(desc,220,yy+1,18,col=MUTED,w=320,max_lines=2)
    equation(eq,570,yy-1,330,44)
    if i<3:line(54,yy+61,906,yy+61,LINE,.6)

def backup_feature(title,summary,theory,description,expr,plot,source):
    page(title,summary,appendix=True,source=source)
    label('Theory connection',54,174)
    text(theory,54,203,28,'SegoeBold',w=284,max_lines=2)
    text(description,54,303,21,col=MUTED,w=276,max_lines=3)
    equation(expr,54,412,284,43)
    svg(plot,350,170,565,278)

backup_feature('Fades','Make the start or end of audio gradual.','Amplitude envelope',
    'The amplitude changes over time.',r'y[n]=a[n]x[n]','fade',
    'Implementation: dsp/effects.py, apply_fade(). A varying envelope is generally time-varying.')

page('Peak normalization','Set the selection peak to a chosen level.',appendix=True,
     source='Implementation: dsp/effects.py, normalize_peak(); desktop/processing.py uses -1 dBFS.')
label('Theory connection',54,174)
text('Amplitude scaling',54,203,29,'SegoeBold')
text('The input peak determines the gain.',54,265,22,col=MUTED,w=395,max_lines=2)
equation(r'y[n]=\frac{A_{\mathrm{target}}}{\max_m|x[m]|}x[n]',54,354,415,71)
label('App behavior',548,174)
text('-1 dBFS',548,206,52,'Mono',AMBER)
text('Default peak target',550,275,23,'SegoeBold')
text('Adjusts the largest sample.\nSilence remains unchanged.',548,346,23,col=MUTED,w=356,max_lines=3)

backup_feature('Multitrack mixing','Combine several audio tracks.','Superposition\nand time shift',
    'Add signals with different levels and offsets.',r'y[n]=\sum_i g_i x_i[n-d_i]',
    'mix','Implementation: desktop/mixer_widget.py and dsp/effects.py. Inputs are resampled to the mix rate.')
backup_feature('Spectral editing','Mute a time-frequency region.','STFT masking',
    'Remove selected components, then reconstruct.',r'\widehat X[m,k]=M[m,k]X[m,k]',
    'mask','Implementation: desktop/main_window.py, _apply_spectral_mask(); dsp/transforms.py.')

page('Image-to-audio synthesis','Interpret image brightness as a sound spectrum.',appendix=True,
     source='Implementation: dsp/transforms.py, image_to_audio() and griffin_lim(); algorithm reference [7].')
for x,title,desc in [(54,'Image','Grayscale brightness'),(354,'Magnitude','Frequency by time'),(654,'Waveform','Estimated phase')]:
    rect(x,178,252,108,'#242327')
    text(title,x+18,198,26,'SegoeBold',AMBER)
    text(desc,x+18,241,17,col=MUTED,w=220,max_lines=2)
arrow(311,229,346,229);arrow(611,229,646,229)
label('Theory connection',54,324)
text('Phase retrieval',54,351,28,'SegoeBold')
text('Estimate the missing phase to synthesize audio.',354,333,23,w=540,max_lines=2)
equation(r'X^{(r+1)}=A\,e^{j\angle\operatorname{STFT}(x^{(r)})}',54,414,650,46)
text('Synthesis is approximate.',54,473,15,col=MUTED)

page('Noise-reduction methods','Different ways to reduce unwanted sound.',appendix=True,
     source='Implementation: dsp/noise_reduction.py. The app implements a local time-domain Wiener estimator.')
items=[('Spectral subtraction','Subtract a noise estimate.',r'\widehat A=\max(A-\alpha D,\,\beta A)'),
       ('Spectral gate','Attenuate bins below a threshold.',r'\widehat X=\left[(1-\rho)+\rho M\right]X'),
       ('Local Wiener','Use local mean and variance.',r'\widehat x=\mu+\max(1-\sigma_v^2/\sigma_x^2,0)(x-\mu)')]
for i,(title,desc,eq) in enumerate(items):
    yy=167+i*103
    text(title,54,yy,22,'SegoeBold',AMBER)
    text(desc,54,yy+36,18,col=MUTED,w=422,max_lines=2)
    equation(eq,497,yy+16,410,49)
    if i<2:line(54,yy+88,906,yy+88,LINE,.6)

page('Live spectrogram','Analyze incoming microphone audio.',appendix=True,
     source='Implementation: desktop/audio_engine.py and main_window.py, start_live() / _live_tick().')
label('Theory connection',54,174)
text('Windowed FFTs',54,203,29,'SegoeBold')
text('Analyze short sections as new audio arrives.',54,304,24,col=MUTED,w=350,max_lines=3)
for x,y,big,small in [(520,179,'1024','input frames per callback'),(520,283,'8 s','rolling display history'),(520,387,'150 ms','analysis timer interval')]:
    text(big,x,y,44,'Mono',AMBER)
    text(small,x,y+57,18,col=MUTED,w=370,max_lines=1)

page('Inside a live effect preview','The callback plays buffers; the background worker computes DSP.',appendix=True,
     source='Implementation: desktop/main_window.py, request_preview() / _start_preview(); audio_engine.py.')
steps=[('1','Control changes','Coalesce parameter updates on an 80 ms timer.'),
       ('2','Worker renders','Process the committed source for the selected range.'),
       ('3','Latest result wins','Ignore a finished job if its generation is stale.'),
       ('4','Buffer changes','Keep the playback position and crossfade for 10 ms.'),
       ('5','Apply commits','Store one undoable edit. Export writes a file.')]
for i,(n,title,desc) in enumerate(steps):
    yy=162+i*62
    text(n,54,yy,27,'Mono',AMBER)
    text(title,103,yy,23,'SegoeBold',w=288,max_lines=1)
    text(desc,418,yy+1,18,col=MUTED,w=486,max_lines=2)
text('Preview latency includes DSP time. This is buffer-based preview, not a hard real-time DSP engine.',54,478,13,col=MUTED,w=852,max_lines=1)

backup_feature('Sampling and Nyquist','Sample rate limits the available frequencies.',
    'Sampling theorem','Sample above twice the highest signal frequency.',
    r'F_s>2f_{\max}','sampling',
    'Implementation: filter cutoff validation and EQ band validation. Example: 300 Hz sampled at 4000 Hz.')

page('Measured results','Deterministic fixtures make the numerical behavior reproducible.',appendix=True,
     source='Reproduce: Presentation/prepare_presentation_assets.py. Raw results: assets/measurements.json.')
rows=[('Experiment','Configuration','Observed result'),
      ('Gain','-6 dB','Amplitude ratio 0.501187'),
      ('Butterworth low-pass','Order 4, fc 1000 Hz, Fs 16000 Hz','-42.10 dB at 3000 Hz'),
      ('Peaking EQ','1000 Hz, +6 dB, Q = 1.4','+6.000 dB at center'),
      ('FFT','4096 samples, Fs 16000 Hz','500 Hz peak, amplitude 0.400'),
      ('STFT / inverse STFT','Hann, N 512, hop 128, seed 42','Max error 1.11 x 10^-16'),
      ('Noise subtraction','Two tones + Gaussian noise','SNR 9.7 dB to 22.1 dB')]
for i,row in enumerate(rows):
    yy=162+i*40
    if i==0:rect(54,yy-5,852,34,'#28251f')
    for xx,ww,value in zip((64,304,631),(227,313,261),row):
        text(value,xx,yy,16 if i else 15,'SegoeBold' if i==0 else 'Segoe',AMBER if i==0 else FG,w=ww,max_lines=1)
    if i:line(54,yy+30,906,yy+30,LINE,.5)
text('Noise test: Fs 16000 Hz, 2 s, noise SD 0.055, independent 1 s profile, N 2048, hop 512, strength 1.5.',54,461,12,col=MUTED,w=852,max_lines=2)
text('SNR compares each output against the known clean signal. This is not a speech-quality benchmark.',54,479,12,col=MUTED,w=852,max_lines=1)

page('Current boundaries','The implementation has clear limits and a practical next-step list.',appendix=True,
     source='Code audit: desktop/main_window.py, spectrum_widget.py, mixer_widget.py and analysis.py.')
items=[('In-memory audio','Mono and stereo files are loaded into memory. Long selections take more time to process and preview.'),
       ('Long FFT selections','Overlapping windows preserve the original frequency scale. Averaging summarizes the selection; use the spectrogram for timing.'),
       ('Memory budgets','Spectral processing and mixing have 256 MiB buffer budgets. Recording stops at 64 MiB of stored samples.'),
       ('Signal artifacts','Strong noise reduction or abrupt spectral masks can affect sound quality. Image synthesis estimates missing phase.'),
       ('Hardware validation','Tests simulate audio streams. Rehearse speakers, microphone and projector on the actual lab setup.')]
for i,(title,desc) in enumerate(items):
    yy=161+i*62
    text(title,54,yy,21,'SegoeBold',CORAL,w=253,max_lines=1)
    text(desc,334,yy+1,16,col=MUTED,w=570,max_lines=3,leading=20)

page('Sources and implementation','Theory references support the concepts. Repository code defines the delivered behavior.',appendix=True,
     source='Source files inspected locally. External references checked 27 September 2026.')
refs=[
 ('[1] SonicCraft source code','github.com/mehrab4226/SonicCraft','https://github.com/mehrab4226/SonicCraft'),
 ('[2] SciPy: Butterworth design and SOS filtering','docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html','https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html'),
 ('[3] W3C: Audio EQ Cookbook, Robert Bristow-Johnson formulae','w3.org/TR/audio-eq-cookbook/','https://www.w3.org/TR/audio-eq-cookbook/'),
 ('[4] NumPy: real-input discrete Fourier transform','numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html','https://numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html'),
 ('[5] SciPy: Short-Time Fourier Transform tutorial','docs.scipy.org/doc/scipy/tutorial/signal.html','https://docs.scipy.org/doc/scipy/tutorial/signal.html'),
 ('[6] Aalto University: Introduction to Speech Processing','speechprocessingbook.aalto.fi/enhancement/noise-attenuation/','https://speechprocessingbook.aalto.fi/enhancement/noise-attenuation/'),
 ('[7] Griffin-Lim algorithm reference and original 1984 paper citation','librosa.org/doc/main/api/generated/librosa.griffinlim.html','https://librosa.org/doc/main/api/generated/librosa.griffinlim.html'),
]
for i,(name,url,link) in enumerate(refs):
    yy=160+i*43
    text(name,54,yy,17,'SegoeBold',w=852,max_lines=1)
    text(url,54,yy+24,11.5,'Mono',MUTED,w=852,max_lines=1)
    c.linkURL(link,(54,H-yy-40,906,H-yy),relative=0,thickness=0)
text('Local DSP: effects.py, filters.py, transforms.py, noise_reduction.py. UI and playback: desktop/.',54,474,12,col=MUTED,w=852,max_lines=1)
