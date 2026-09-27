"""Reproducible figures and demo clips, using SonicCraft's real DSP functions."""
from pathlib import Path
import sys
import os
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / '.cache/presentation-deps'))
sys.path.insert(0, str(ROOT / 'backend/src'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from scipy import signal
import soundfile as sf
from soniccraft.dsp.filters import butterworth, peaking_eq_sections, ParametricEQBand, frequency_response
from soniccraft.dsp.effects import apply_gain, apply_fade, mix_audio
from soniccraft.dsp.transforms import fft_spectrum, stft, inverse_stft
from soniccraft.dsp.noise_reduction import estimate_noise_profile, spectral_subtraction

ASSETS = ROOT / 'Presentation/assets'
DEMO = ROOT / 'Presentation/demo'
ASSETS.mkdir(parents=True, exist_ok=True)
DEMO.mkdir(parents=True, exist_ok=True)
for file in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf'):
    font_manager.fontManager.addfont('C:/Windows/Fonts/' + file)
plt.rcParams.update({'font.family':'Segoe UI', 'font.size':14, 'axes.labelsize':14,
                     'xtick.labelsize':12, 'ytick.labelsize':12, 'svg.fonttype':'path',
                     'axes.spines.top':False, 'axes.spines.right':False})
BG='#141416'; FG='#f4eee4'; MUTED='#bcb7af'; AMBER='#e6bd78'; CORAL='#e5a093'; GRID='#3b3b40'
CMAP = LinearSegmentedColormap.from_list('soniccraft', ['#141416','#49302f','#96554b','#d99270','#f3d9a0'])

def fig_axes(w=7.4, h=3.4, nrows=1):
    fig, axes=plt.subplots(nrows,1,figsize=(w,h),layout='constrained',squeeze=False)
    fig.patch.set_facecolor(BG)
    for ax in axes.flat:
        ax.set_facecolor(BG)
        ax.tick_params(colors=MUTED)
        ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED)
        for sp in ax.spines.values(): sp.set_color(GRID)
        ax.grid(alpha=.16, color=MUTED)
    return fig, axes[:,0]

def save(fig,name):
    fig.savefig(ASSETS/(name+'.svg'),facecolor=BG)
    plt.close(fig)

rate=16000
rng=np.random.default_rng(220)
t=np.arange(6*rate)/rate
env=np.where((t>=.8)&(t<=5.6), .4+.6*np.sin(np.pi*2*t)**2,0)
clean=env*(.16*np.sin(2*np.pi*220*t)+.09*np.sin(2*np.pi*1000*t)+.045*np.sin(2*np.pi*2000*t))
noise=.018*rng.standard_normal(len(t))+.012*np.sin(2*np.pi*60*t)
left=clean+noise
right=.8*clean+.018*rng.standard_normal(len(t))+.012*np.sin(2*np.pi*60*t)
demo=np.column_stack([left,right])
sf.write(DEMO/'SonicCraft_demo_16k.wav',demo,rate,subtype='PCM_24')
sf.write(DEMO/'Clean_reference_16k.wav',np.column_stack([clean,.8*clean]),rate,subtype='PCM_24')

# Sampling: the plotted points are samples, not invented control points.
fig,(ax,)=fig_axes()
fine=np.linspace(0,.01,1000); tt=np.arange(0,.01,1/4000)
ax.plot(fine*1000,.75*np.sin(2*np.pi*300*fine),color=CORAL,lw=1.5,alpha=.65)
marker,stem,base=ax.stem(tt*1000,.75*np.sin(2*np.pi*300*tt),basefmt=' ')
plt.setp(marker,color=AMBER,markersize=5);plt.setp(stem,color=AMBER,linewidth=1.4)
ax.set(xlabel='Time (ms)',ylabel='Amplitude',ylim=(-1,1),xlim=(0,10))
save(fig,'sampling')

fig,(ax,)=fig_axes()
tt=np.arange(800)/rate; x=.6*np.sin(2*np.pi*80*tt)
ax.plot(tt*1000,x,color=MUTED,lw=1.8,label='Original')
ax.plot(tt*1000,apply_gain(x,-6),color=AMBER,lw=2.5,label='Gain = -6 dB')
ax.set(xlabel='Time (ms)',ylabel='Amplitude',xlim=(0,50),ylim=(-.7,.7))
ax.legend(frameon=False,labelcolor=FG,loc='upper right',fontsize=13)
save(fig,'gain')

fig,(ax,)=fig_axes()
sections=butterworth(1000,rate,kind='lowpass',order=4)
response=frequency_response(sections,rate,points=8192)
ax.plot(response.frequencies,response.magnitude_db,color=AMBER,lw=3)
ax.axvline(1000,color=CORAL,lw=1.1,ls='--');ax.axhline(-3.0103,color=MUTED,lw=.7,ls=':')
ax.scatter([1000],[-3.0103],color=CORAL,s=55,zorder=4)
ax.annotate('Cutoff: 1000 Hz',xy=(1000,-3),xytext=(1650,1),color=FG,fontsize=14)
ax.set(xlabel='Frequency (Hz)',ylabel='Gain (dB)',xlim=(0,5000),ylim=(-75,7))
save(fig,'filter')

eq=peaking_eq_sections(ParametricEQBand(1000,6,1.4),44100)
response=frequency_response(eq,44100,points=16384)
fig,(ax,)=fig_axes()
ax.semilogx(response.frequencies[1:],response.magnitude_db[1:],color=AMBER,lw=3)
ax.fill_between(response.frequencies[1:],response.magnitude_db[1:],color=AMBER,alpha=.10)
ax.scatter([1000],[6],color=CORAL,s=60,zorder=4)
ax.annotate('+6 dB at 1000 Hz',xy=(1000,6),xytext=(1600,6.2),color=FG,fontsize=14)
ax.set(xlabel='Frequency (Hz, logarithmic scale)',ylabel='Gain (dB)',xlim=(40,20000),ylim=(-1,8))
ax.set_xticks([60,250,1000,4000,16000],['60','250','1000','4000','16000'])
save(fig,'eq')

N=4096;tt=np.arange(N)/rate
two_tone=.4*np.sin(2*np.pi*500*tt)+.2*np.sin(2*np.pi*1500*tt)
spectrum=fft_spectrum(two_tone,rate,window='hann')
fig,(ax,)=fig_axes()
ax.plot(spectrum.frequencies,spectrum.magnitude_db,color=CORAL,lw=2)
ax.set(xlabel='Frequency (Hz)',ylabel='Magnitude (dBFS)',xlim=(0,2200),ylim=(-100,0))
for freq,amp in ((500,.4),(1500,.2)):
    ax.annotate(f'{freq} Hz',xy=(freq,20*np.log10(amp)),xytext=(freq+100,-12 if freq==500 else -28),
                color=FG,fontsize=15,arrowprops={'arrowstyle':'-','color':MUTED})
save(fig,'fft')

tt=np.arange(3*rate)/rate
chirp=.3*signal.chirp(tt, f0=250, f1=3500,t1=3,method='linear')
chirp += .16*np.sin(2*np.pi*1800*tt)*(tt>1)*(tt<2)
spec=stft(chirp,rate,n_fft=2048,hop_length=512)
db=20*np.log10(np.maximum(np.abs(spec.spectrum),1e-8)/max(np.abs(spec.spectrum).max(),1e-8))
fig,(ax,)=fig_axes(h=3.7)
im=ax.pcolormesh(spec.times,spec.frequencies,db,cmap=CMAP,vmin=-75,vmax=0,shading='auto',rasterized=True)
ax.grid(False);ax.set(xlabel='Time (s)',ylabel='Frequency (Hz)',ylim=(0,4000),xlim=(0,3))
cb=fig.colorbar(im,ax=ax,pad=.025);cb.set_label('Relative magnitude (dB)',color=MUTED);cb.ax.tick_params(colors=MUTED)
save(fig,'spectrogram')

# Controlled denoising experiment: known clean reference and independent noise-only profile.
tt=np.arange(2*rate)/rate
reference=.22*np.sin(2*np.pi*500*tt)+.09*np.sin(2*np.pi*1500*tt)
noisy=reference+rng.normal(0,.055,len(tt))
profile=estimate_noise_profile(rng.normal(0,.055,rate),rate,n_fft=2048,hop_length=512)
denoised=spectral_subtraction(noisy,rate,profile,strength=1.5)
def snr(y): return 10*np.log10(np.sum(reference**2)/np.sum((y-reference)**2))
fig,(ax,)=fig_axes()
for data,color,label in ((noisy,MUTED,'Noisy input'),(denoised,AMBER,'After subtraction')):
    f,power=signal.welch(data,rate,nperseg=2048)
    ax.plot(f,10*np.log10(np.maximum(power,1e-15)),color=color,lw=1.8,label=label)
ax.set(xlabel='Frequency (Hz)',ylabel='Power density (dB/Hz)',xlim=(0,5000),ylim=(-90,-20))
ax.legend(frameon=False,labelcolor=FG,fontsize=13,loc='upper right')
save(fig,'noise')

fig,(ax,)=fig_axes()
tt=np.arange(rate)/rate; tone=.5*np.sin(2*np.pi*25*tt)
faded=apply_fade(tone,rate,fade_in_seconds=.4,fade_out_seconds=.3,curve='linear')
ax.plot(tt,tone,color=MUTED,lw=1,alpha=.5)
ax.plot(tt,faded,color=CORAL,lw=1.8)
envelope=np.minimum(np.minimum(tt/.4,(1-tt)/.3),1)*.5
ax.plot(tt,envelope,color=AMBER,lw=2,ls='--')
ax.set(xlabel='Time (s)',ylabel='Amplitude',xlim=(0,1),ylim=(-.6,.6))
save(fig,'fade')

fig,axes=fig_axes(h=4,nrows=3)
ta=np.arange(rate)/rate
a=.3*np.sin(2*np.pi*5*ta)*np.sin(np.pi*ta)**2
b=.2*np.sin(2*np.pi*9*ta)*np.sin(np.pi*ta)**2
mixed=mix_audio([dict(samples=a, sample_rate=rate, offset=0), dict(samples=b, sample_rate=rate, offset=0.5)], rate)
for ax,data,offset,name,col in ((axes[0],a,0,'Track 1',CORAL),(axes[1],b,.5,'Track 2',AMBER),(axes[2],mixed,0,'Mix',FG)):
    ax.plot(np.arange(len(data))/rate+offset,data,color=col,lw=2)
    ax.set(xlim=(0,1.5),ylim=(-.48,.48),yticks=[0]);ax.text(.015,.8,name,transform=ax.transAxes,color=col,fontsize=13)
axes[2].set_xlabel('Time (s)')
save(fig,'mix')

fig,axes=fig_axes(h=3.7,nrows=2)
masked=spec.spectrum.copy()
mask=(spec.frequencies[:,None]>1600)&(spec.frequencies[:,None]<2000)&(spec.times[None,:]>.9)&(spec.times[None,:]<2.1)
masked[mask]=0
for ax,data,name in ((axes[0],spec.spectrum,'Original STFT'),(axes[1],masked,'Rectangular spectral mask')):
    values=20*np.log10(np.maximum(np.abs(data),1e-8)/max(np.abs(spec.spectrum).max(),1e-8))
    ax.pcolormesh(spec.times,spec.frequencies,values,cmap=CMAP,vmin=-65,vmax=0,shading='auto',rasterized=True)
    ax.grid(False);ax.set(ylim=(0,4000),xlim=(0,3),ylabel='Hz');ax.text(.02,.82,name,transform=ax.transAxes,color=FG,fontsize=13)
axes[-1].set_xlabel('Time (s)')
save(fig,'mask')

rng2=np.random.default_rng(42)
test=rng2.normal(0,.1,4097)
rebuilt=inverse_stft(stft(test,44100,n_fft=512,hop_length=128))
freqs,h=signal.sosfreqz(sections,worN=np.array([300,1000,3000]),fs=rate)
eq_at_center=frequency_response(peaking_eq_sections(ParametricEQBand(1000,6,1.4),8000),8000)
results={
 'sample_rate':rate,'filter_gain_db':dict(zip(map(str,freqs),map(float,20*np.log10(abs(h))))),
 'eq_center_gain_db':float(eq_at_center.magnitude_db[np.argmin(abs(eq_at_center.frequencies-1000))]),
 'snr_before_db':float(snr(noisy)),'snr_after_db':float(snr(denoised)),
 'stft_max_absolute_error':float(np.max(abs(rebuilt-test))),
 'gain_minus6_ratio':float(10**(-6/20)), 'fft_peak_hz':float(spectrum.frequencies[np.argmax(spectrum.magnitude)]),
 'fft_peak_amplitude':float(np.max(spectrum.magnitude)),
 'demo_frames':len(demo),'demo_channels':2,
}
(ASSETS/'measurements.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))

# Real application capture, with the same deterministic demo clip.
from PyQt6.QtGui import QFontDatabase
from soniccraft.desktop.main import create_application
from soniccraft.desktop.main_window import MainWindow
from soniccraft.desktop.document import AudioData
app=create_application([])
for name in ('segoeui.ttf','segoeuib.ttf','consola.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
w=MainWindow();w._loaded(AudioData(demo,rate,'SonicCraft demo.wav'))
w.resize(1440,960);w.sidebar.navigate('eq');w.show();app.processEvents()
w.player.position=2*rate;w._tick();app.processEvents()
w.grab().save(str(ASSETS/'app-workspace.png'))
w.waveform.grab().save(str(ASSETS/'stereo-waveform.png'))
w.document.saved_samples=w.document.audio.samples
w.close()
