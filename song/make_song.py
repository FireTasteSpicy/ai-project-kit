import os, numpy as np, soundfile as sf, subprocess, re
from scipy.signal import fftconvolve
from song import (SR, BEAT, BPM, LYR, midi_hz, deg_to_midi, section_kind,
                  espeak_syl, render_vocal)
from song import line_notes, line_durs
from arrange import parse_lyrics, line_syllables
from song_dsp import retune, f0_autocorr

rng = np.random.default_rng(7)

# ---------- build full event/timeline ----------
def build_all(sections):
    events=[]; lines=[]; spans=[]; t=2.0*BEAT
    for sec in sections:
        kind=section_kind(sec['name']); s_start=t
        for ln in sec['lines']:
            syl=[s for s in line_syllables(ln) if re.sub(r"[^A-Za-z']",'',s)]
            if not syl: continue
            notes=line_notes(len(syl),kind); durs=line_durs(len(syl),kind)
            lines.append(dict(text=ln,start=t,section=sec['name']))
            for s,m,db in zip(syl,notes,durs):
                dur=db*BEAT
                events.append(dict(text=s,midi=m,start=t,dur=dur)); t+=dur
            t+=0.5*BEAT
        spans.append(dict(name=sec['name'],kind=kind,start=s_start,end=t))
        t+=1.5*BEAT
    return events,lines,spans,t+2.0   # +outro tail

# ---------- instrument synths ----------
def env_ad(n,sr,a,d):
    t=np.arange(n)/sr
    return (1-np.exp(-t/max(a,1e-4)))*np.exp(-t/max(d,1e-4))

def piano_note(freq,dur,gain):
    n=int(dur*SR); t=np.arange(n)/SR; y=np.zeros(n)
    for p,a in [(1,1.0),(2,0.4),(3,0.18),(4,0.08)]:
        y+=a*np.sin(2*np.pi*freq*p*t+rng.random())
    env=np.exp(-t*1.8)*(1-np.exp(-t*250))
    return y*env*gain

def pad_note(freq,dur,gain):
    n=int(dur*SR); t=np.arange(n)/SR; y=np.zeros(n)
    for det in (-0.12,0.0,0.1):
        f=freq*2**(det/12.0)
        for k in range(1,7): y+=(1.0/k)*np.sin(2*np.pi*f*k*t)
    rel=np.ones(n); r=int(0.3*SR); rel[-r:]=np.linspace(1,0,r)
    env=(1-np.exp(-t/0.4))*rel
    return y*env*gain/9.0

def bass_note(freq,dur,gain):
    n=int(dur*SR); t=np.arange(n)/SR
    y=np.sin(2*np.pi*freq*t)+0.25*np.sin(2*np.pi*2*freq*t)
    return y*env_ad(n,SR,0.02,dur*0.9)*gain

def brush(dur,gain):
    n=int(dur*SR); y=rng.standard_normal(n)*np.exp(-np.arange(n)/SR/0.06)
    y=np.convolve(y,np.hanning(25),'same')
    return y*gain

CHORDS={  # midi note sets (mid register)
 'Dm':[50,53,57,62],'Bb':[46,50,53,58],'F':[41,45,48,53],'C':[48,52,55,60],
 'Gm':[43,46,50,55],'A':[45,49,52,57],'Am':[45,48,52,57]}
PROG={'verse':['Dm','Bb','F','C'],'chorus':['Bb','F','Dm','C'],
      'bridge':['Gm','C','F','A']}

def add(buf,sig,start):
    i=int(start*SR); n=min(len(sig),len(buf)-i)
    if n>0: buf[i:i+n]+=sig[:n]

def build_backing(spans,total):
    N=int(total*SR)
    piano=np.zeros(N); pad=np.zeros(N); bass=np.zeros(N); perc=np.zeros(N)
    bar=4*BEAT
    first_chorus_end=min((s['end'] for s in spans if s['kind']=='chorus'),default=total)
    for sp in spans:
        prog=PROG[sp['kind']]; t=sp['start']; ci=0
        while t < sp['end']-1e-3:
            ch=CHORDS[prog[ci%len(prog)]]; ci+=1
            d=min(bar,sp['end']-t)
            # pad: full bar sustained
            for m in ch: add(pad,pad_note(midi_hz(m),d+0.3,0.5),t)
            # piano: gentle broken chord
            for j,m in enumerate(ch):
                add(piano,piano_note(midi_hz(m),d,0.16),t+j*0.06)
            # re-strike mid-bar
            for m in ch[1:]:
                add(piano,piano_note(midi_hz(m),d/2,0.10),t+bar/2)
            # bass: root (down an octave) per bar + half
            add(bass,bass_note(midi_hz(ch[0]-12),d,0.5),t)
            add(bass,bass_note(midi_hz(ch[0]-12),d/2,0.3),t+bar/2)
            # brushed perc on beats 2&4, only later in the song
            if t>first_chorus_end-1e-3:
                for b in (1,3):
                    add(perc,brush(0.18,0.12),t+b*BEAT)
            t+=bar
    return piano,pad,bass,perc

def reverb_stereo(dry,decay=1.6,wet=0.22):
    n=int(decay*SR); t=np.arange(n)/SR
    irL=rng.standard_normal(n)*np.exp(-t*4.5); irL[0]=1.0
    irR=rng.standard_normal(n)*np.exp(-t*4.5); irR[0]=1.0
    L=fftconvolve(dry,irL)[:len(dry)]; R=fftconvolve(dry,irR)[:len(dry)]
    return wet*L, wet*R

def norm(x,peak=0.89):
    m=np.max(np.abs(x))
    return x*(peak/m) if m>0 else x

if __name__=="__main__":
    OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","dist")
    os.makedirs(OUT,exist_ok=True); os.chdir(OUT)
    secs=parse_lyrics(LYR)
    events,lines,spans,total=build_all(secs)
    print("FULL: %d syllables, %d lines, total %.1fs (%.2f min)"%(len(events),len(lines),total,total/60))
    print("rendering vocals (espeak+retune)...")
    vocal=render_vocal(events,total)
    if len(vocal)<int(total*SR): vocal=np.pad(vocal,(0,int(total*SR)-len(vocal)))
    vocal=vocal[:int(total*SR)]
    sf.write("vocal_stem.wav",vocal,SR)
    perr=[]
    for e in events:
        i0=int(e['start']*SR); seg=vocal[i0:i0+int(e['dur']*SR)]
        f=f0_autocorr(seg,SR)
        if f: perr.append(abs(12*np.log2(f/midi_hz(e['midi']))))
    perr=np.array(perr)
    print("VOCAL pitch err (semitones): mean=%.2f median=%.2f 90pct=%.2f voiced=%d/%d"%(
        perr.mean(),np.median(perr),np.percentile(perr,90),len(perr),len(events)))
    print("building backing...")
    piano,pad,bass,perc=build_backing(spans,total)
    # ---- mono dry mix (vocal forward) ----
    vmix=norm(vocal,0.7)
    dry = 1.0*vmix + 0.32*norm(piano,0.5) + 0.22*norm(pad,0.5) + 0.33*norm(bass,0.5) + 0.45*perc
    # ---- stereo: slight instrument panning via Haas, vocal center ----
    pianoS=0.32*norm(piano,0.5); padS=0.22*norm(pad,0.5)
    h=int(0.012*SR)
    L = dry.copy(); R = dry.copy()
    L[h:]+=0.15*padS[:-h]; R[:-h]+=0.15*padS[h:]      # widen pad
    # ---- reverb send ----
    wetL,wetR=reverb_stereo(0.9*vmix+0.6*pianoS+0.5*padS)
    L=L+wetL; R=R+wetR
    # ---- soft limiter + normalize + fades ----
    L=np.tanh(L*0.55); R=np.tanh(R*0.55)
    st=np.stack([norm(L),norm(R)],1)
    fi=int(1.0*SR); fo=int(2.5*SR)
    st[:fi]*=np.linspace(0,1,fi)[:,None]; st[-fo:]*=np.linspace(1,0,fo)[:,None]
    sf.write("master_22k.wav",st,SR)
    # resample to 44.1k stereo wav + mp3 via ffmpeg
    subprocess.run(["ffmpeg","-y","-i","master_22k.wav","-ar","44100",
                    "teresa_and_ijooz.wav"],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg","-y","-i","master_22k.wav","-ar","44100","-b:a","192k",
                    "teresa_and_ijooz.mp3"],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    rms=np.sqrt(np.mean(st**2))
    print("peak=%.3f rms=%.3f (%.1f dBFS)"%(np.max(np.abs(st)),rms,20*np.log10(rms)))
    # ---- LRC ----
    def ts(s): 
        return "[%02d:%05.2f]"%(int(s//60),s%60)
    out=["[ti:Teresa and Ijooz]","[ar:espeak-ng vocaloid]","[al:AI Project Kit]",
         "[by:Claude Code]","[length:%02d:%02d]"%(int(total//60),int(total%60))]
    for ln in lines: out.append(ts(ln['start'])+ln['text'])
    open("teresa_and_ijooz.lrc","w").write("\n".join(out)+"\n")
    import os
    for f in ["teresa_and_ijooz.wav","teresa_and_ijooz.mp3","teresa_and_ijooz.lrc"]:
        print("  %-26s %8.1f KB"%(f,os.path.getsize(""+f)/1024))
    # spectrogram
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from scipy.signal import spectrogram
    mono=st.mean(1); f,tt,Sxx=spectrogram(mono,44100 if False else SR,nperseg=2048,noverlap=1536)
    plt.figure(figsize=(13,5))
    plt.pcolormesh(tt,f,10*np.log10(Sxx+1e-10),shading="gouraud",cmap="magma",vmin=-90,vmax=-25)
    plt.ylim(0,4000); plt.xlabel("time (s)"); plt.ylabel("Hz")
    plt.title("Teresa and Ijooz - vocaloid ballad (espeak-ng + DSP)")
    for sp in spans:
        plt.axvline(sp["start"],color="cyan",lw=0.6,alpha=0.6)
        plt.text(sp["start"]+0.3,3700,sp["name"],color="white",fontsize=7,va="top")
    plt.tight_layout(); plt.savefig("teresa_spectrogram.png",dpi=110); plt.close()
    # 40s preview from first chorus
    fc=min((s["start"] for s in spans if s["kind"]=="chorus"),default=0.0)
    subprocess.run(["ffmpeg","-y","-ss","%.2f"%fc,"-t","42","-i","teresa_and_ijooz.wav",
                    "-b:a","192k","teresa_preview.mp3"],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print("preview from first chorus @ %.1fs"%fc)
    print("spectrogram + preview written")
    print("done")
