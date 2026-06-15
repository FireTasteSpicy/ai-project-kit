import numpy as np
from scipy.signal import resample

# ---------- STFT / ISTFT ----------
def _stft(x, n_fft, hop, win):
    pad = n_fft // 2
    x = np.pad(x, pad)
    frames = 1 + (len(x) - n_fft) // hop
    S = np.empty((n_fft // 2 + 1, frames), complex)
    for i in range(frames):
        S[:, i] = np.fft.rfft(x[i*hop:i*hop+n_fft] * win)
    return S

def _istft(S, n_fft, hop, win):
    frames = S.shape[1]
    length = n_fft + hop * (frames - 1)
    x = np.zeros(length); wsum = np.zeros(length)
    for i in range(frames):
        seg = np.fft.irfft(S[:, i], n_fft) * win
        x[i*hop:i*hop+n_fft] += seg
        wsum[i*hop:i*hop+n_fft] += win**2
    pad = n_fft // 2
    x, wsum = x[pad:], wsum[pad:]
    nz = wsum > 1e-8
    x[nz] /= wsum[nz]
    return x

def pv_stretch(x, stretch, n_fft=2048, hop=512):
    """Time-stretch by `stretch` (output length ~ len*stretch), pitch preserved."""
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    win = np.hanning(n_fft)
    D = _stft(x, n_fft, hop, win)
    mag, phase = np.abs(D), np.angle(D)
    bins, T = D.shape
    omega = 2*np.pi*hop*np.arange(bins)/n_fft
    t = np.arange(0, T, 1.0/stretch)
    out = np.zeros((bins, len(t)), complex)
    acc = phase[:, 0].copy()
    for i, tt in enumerate(t):
        k = int(np.floor(tt)); frac = tt - k; k2 = min(k+1, T-1)
        m = (1-frac)*mag[:, k] + frac*mag[:, k2]
        dphi = phase[:, k2] - phase[:, k] - omega
        dphi -= 2*np.pi*np.round(dphi/(2*np.pi))
        out[:, i] = m*np.exp(1j*acc)
        acc = acc + omega + dphi
    return _istft(out, n_fft, hop, win)

def f0_autocorr(x, sr, fmin=70, fmax=600):
    x = x - np.mean(x)
    if len(x) < sr//50: return None
    w = int(0.04*sr)
    if len(x) > w:
        e = np.convolve(x**2, np.ones(w), 'same')
        c = int(np.argmax(e)); seg = x[max(0,c-w//2):c+w//2]
    else:
        seg = x
    if len(seg) < 64: return None
    seg = seg*np.hanning(len(seg))
    corr = np.correlate(seg, seg, 'full')[len(seg)-1:]
    lo, hi = int(sr/fmax), min(int(sr/fmin), len(corr)-1)
    if hi <= lo+1: return None
    peak = lo + int(np.argmax(corr[lo:hi]))
    if corr[peak] < 0.2*corr[0]: return None   # weak periodicity -> unvoiced
    return sr/peak

def retune(x, sr, target_f0, target_dur, src_f0=None):
    """Resample to set pitch -> target_f0, then PV-stretch to exactly target_dur."""
    if src_f0 is None:
        src_f0 = f0_autocorr(x, sr)
    n_tgt = max(1, int(round(target_dur*sr)))
    if src_f0 and target_f0:
        pr = target_f0/src_f0
        y = resample(x, max(1, int(round(len(x)/pr))))   # pitch shift by pr
    else:
        y = x.copy()
    if len(y) < 8:
        y = np.pad(y, (0, 8))
    stretch = n_tgt/len(y)
    y = pv_stretch(y, stretch)
    if len(y) >= n_tgt: y = y[:n_tgt]
    else: y = np.pad(y, (0, n_tgt-len(y)))
    return y

if __name__ == "__main__":
    sr = 22050
    # TEST 1: 200 Hz tone -> retune to 440 Hz, 0.5 s
    t = np.arange(int(0.7*sr))/sr
    tone = 0.5*np.sin(2*np.pi*200*t)
    y = retune(tone, sr, 440.0, 0.5, src_f0=200.0)
    print("TEST tone: out_dur=%.3fs (want 0.5)  out_f0=%.1fHz (want 440)  peak=%.3f"
          % (len(y)/sr, f0_autocorr(y, sr), np.max(np.abs(y))))
    # TEST 2: chord of two tones stretch only
    s2 = pv_stretch(tone, 2.0)
    print("TEST stretch x2: %.3fs -> %.3fs  f0=%.1f (pitch should stay 200)"
          % (len(tone)/sr, len(s2)/sr, f0_autocorr(s2, sr)))
