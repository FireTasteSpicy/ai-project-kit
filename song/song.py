import subprocess, tempfile, os, re, numpy as np, soundfile as sf, pyphen
from song_dsp import retune, f0_autocorr, pv_stretch
from arrange import parse_lyrics, line_syllables

SR = 22050
BPM = 68
BEAT = 60.0/BPM
LYR = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","teresa_and_ijooz_lyrics.txt")

# ---- pitch helpers (D natural minor, 0 = D4) ----
SCALE = [0,2,3,5,7,8,10]   # D E F G A Bb C
def deg_to_midi(d):
    o, i = divmod(int(round(d)), 7)
    return 62 + 12*o + SCALE[i]
def midi_hz(m): return 440.0*2**((m-69)/12.0)

CONTOUR = {
    'verse':  [4,3,4,2,3,1,2,0,-1,0],
    'chorus': [4,5,6,6,5,4,5,3,4,2,0],
    'bridge': [2,3,4,5,4,5,6,4,3,4],
}
def section_kind(name):
    n=name.lower()
    if 'chorus' in n: return 'chorus'
    if 'bridge' in n: return 'bridge'
    return 'verse'

def line_notes(n_syl, kind):
    c=np.array(CONTOUR[kind],float)
    xs=np.linspace(0,len(c)-1,n_syl)
    degs=[c[int(round(x))] for x in xs]
    return [deg_to_midi(d) for d in degs]

def line_durs(n_syl, kind):
    cell=[0.5,0.5,1.0,0.5,0.5,1.0]
    d=[cell[i%len(cell)] for i in range(n_syl)]
    d[-1]= 2.0 if kind!='verse' else 1.5     # hold last
    if n_syl>=2: d[0]=1.0                      # land the downbeat
    return d

def espeak_syl(text):
    text=re.sub(r"[^A-Za-z']",'',text)
    if not text: return None
    f=tempfile.mktemp(suffix=".wav")
    subprocess.run(["espeak-ng","-v","en-us+f3","-s","150","-p","45","-w",f,text],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    x,_=sf.read(f); os.remove(f)
    if x.ndim>1: x=x.mean(1)
    # trim leading/trailing near-silence
    amp=np.abs(x); thr=max(1e-3,0.02*amp.max())
    nz=np.where(amp>thr)[0]
    if len(nz): x=x[nz[0]:nz[-1]+1]
    return x.astype(float)

def build_events(sections):
    events=[]; t=2.0*BEAT     # short intro
    for si,sec in enumerate(sections):
        kind=section_kind(sec['name'])
        for ln in sec['lines']:
            syl=[s for s in line_syllables(ln) if re.sub(r"[^A-Za-z']",'',s)]
            if not syl: continue
            notes=line_notes(len(syl),kind); durs=line_durs(len(syl),kind)
            line_start=t
            for s,m,db in zip(syl,notes,durs):
                dur=db*BEAT
                events.append(dict(text=s,midi=m,start=t,dur=dur,
                                   section=sec['name'],line=ln,
                                   line_start=(s is syl[0])))
                t+=dur
            t+=0.5*BEAT                      # breath after line
        t+=1.5*BEAT                          # gap between sections
    return events, t

def render_vocal(events, total):
    buf=np.zeros(int((total+1.0)*SR))
    for e in events:
        x=espeak_syl(e['text'])
        if x is None or len(x)<32: continue
        y=retune(x, SR, midi_hz(e['midi']), e['dur'])
        # soft attack/release envelope
        n=len(y); a=min(int(0.015*SR),n//4)
        env=np.ones(n); env[:a]=np.linspace(0,1,a); env[-a:]=np.linspace(1,0,a)
        y=y*env*0.8
        i=int(e['start']*SR)
        buf[i:i+n]+=y[:max(0,len(buf)-i)]
    return buf

if __name__=="__main__":
    secs=parse_lyrics(LYR)
    chorus=[s for s in secs if s['name']=='Chorus']
    ev,total=build_events(chorus)
    print("chorus events:",len(ev),"total %.1fs"%total)
    buf=render_vocal(ev,total)
    sf.write("/tmp/chorus_vocal.wav",buf,SR)
    # verify pitch accuracy per syllable
    errs=[]
    for e in ev:
        i0=int(e['start']*SR); i1=i0+int(e['dur']*SR)
        seg=buf[i0:i1]
        f=f0_autocorr(seg,SR); tgt=midi_hz(e['midi'])
        if f:
            st=12*np.log2(f/tgt); errs.append(st)
    errs=np.array(errs)
    print("syllables measured:",len(errs))
    print("pitch error semitones: mean=%.2f  median=%.2f  90%%=%.2f"%
          (np.mean(np.abs(errs)), np.median(np.abs(errs)), np.percentile(np.abs(errs),90)))
    print("peak=%.3f  dur=%.1fs  wrote /tmp/chorus_vocal.wav"%(np.max(np.abs(buf)),len(buf)/SR))
