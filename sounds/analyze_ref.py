"""Reference analysis shared by make_A_port.py: f0 track (autocorrelation, 5 ms hops), RMS envelope,
voiced segments. Run directly to print a summary of the four references."""
from __future__ import annotations
import sys
import numpy as np
from pathlib import Path
from scipy.signal import medfilt, butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quack import read_wav

HOP_S = 0.005
WIN_S = 0.030
FMIN, FMAX = 80.0, 900.0


def analyse(path, hop_s=HOP_S, win_s=WIN_S, fmin=FMIN, fmax=FMAX, rms_gate_db=-30.0, clarity=0.5):
    """Return dict(t, f0, rms, voiced, sr, x). f0 is NaN where unvoiced. t is frame centre time."""
    sr, x = read_wav(path)
    x = x - x.mean()
    # band-limit before pitch tracking (kills rumble / hiss)
    sos = butter(4, [60.0, 3000.0], btype="band", fs=sr, output="sos")
    xb = sosfiltfilt(sos, x)
    hop, win = int(hop_s * sr), int(win_s * sr)
    n_frames = max(1, (len(x) - win) // hop + 1)
    t = (np.arange(n_frames) * hop + win / 2) / sr
    rms = np.zeros(n_frames)
    f0 = np.full(n_frames, np.nan)
    clar = np.zeros(n_frames)
    lag_min, lag_max = int(sr / fmax), int(sr / fmin)
    w = np.hanning(win)
    for i in range(n_frames):
        fr = xb[i * hop:i * hop + win]
        rms[i] = np.sqrt(np.mean(fr * fr) + 1e-20)
        fw = (fr - fr.mean()) * w
        # normalised autocorrelation via FFT
        n = 1 << int(np.ceil(np.log2(2 * win)))
        spec = np.fft.rfft(fw, n)
        ac = np.fft.irfft(spec * np.conj(spec), n)[:win]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        seg = ac[lag_min:lag_max]
        k = int(np.argmax(seg))
        clar[i] = seg[k]
        lag = lag_min + k
        # parabolic interpolation around the peak
        if 0 < k < len(seg) - 1:
            a, b, c = seg[k - 1], seg[k], seg[k + 1]
            den = a - 2 * b + c
            if den != 0:
                lag = lag + 0.5 * (a - c) / den
        f0[i] = sr / lag
    peak = rms.max() + 1e-12
    rms_db = 20 * np.log10(rms / peak + 1e-12)
    voiced = (rms_db > rms_gate_db) & (clar > clarity)
    # remove isolated frames (median over 5 frames = 25 ms)
    voiced = medfilt(voiced.astype(float), 5) > 0.5
    f0m = np.where(voiced, f0, np.nan)
    # median filter f0 inside voiced runs (7 frames = 35 ms)
    f0s = f0m.copy()
    for s, e in segments(t, voiced):
        i0, i1 = int(round((s - win / 2 / sr) / hop_s)), int(round((e - win / 2 / sr) / hop_s)) + 1
        run = f0m[i0:i1]
        if len(run) >= 7:
            f0s[i0:i1] = medfilt(run, 7)
    return dict(t=t, f0=f0s, f0_raw=f0, rms=rms, rms_db=rms_db, voiced=voiced, clarity=clar, sr=sr, x=x, hop_s=hop_s)


def segments(t, voiced, min_len_s=0.03):
    """[(start_s, end_s)] of contiguous voiced frames."""
    out = []
    on = False
    for i, v in enumerate(voiced):
        if v and not on:
            on, s = True, t[i]
        elif not v and on:
            on = False
            if t[i] - s >= min_len_s:
                out.append((s, t[i]))
    if on and t[-1] - s >= min_len_s:
        out.append((s, t[-1]))
    return out


def summary(name, a):
    segs = segments(a["t"], a["voiced"])
    print(f"== {name}: {len(a['x'])/a['sr']:.2f} s, peak {np.abs(a['x']).max():.3f}, {len(segs)} voiced segments")
    for s, e in segs:
        m = (a["t"] >= s) & (a["t"] <= e) & np.isfinite(a["f0"])
        f = a["f0"][m]
        r = a["rms_db"][m]
        if len(f):
            print(f"   {s:6.3f}-{e:6.3f} ({e-s:.2f}s)  f0 start {f[0]:5.0f} med {np.median(f):5.0f} min {f.min():5.0f} max {f.max():5.0f} end {f[-1]:5.0f}   rms max {r.max():5.1f} dB")


if __name__ == "__main__":
    ref = Path(__file__).resolve().parents[1] / "reference"
    for n in ["sad2", "irritated2", "frustrated1", "reprimand3"]:
        a = analyse(ref / f"{n}.wav")
        summary(n, a)
        # coarse contour print every 50 ms in voiced parts
        t, f, r = a["t"], a["f0"], a["rms_db"]
        line = []
        for i in range(0, len(t), 10):
            if a["voiced"][i]:
                line.append(f"{t[i]:.2f}:{f[i]:.0f}/{r[i]:.0f}")
        print("   ", " ".join(line))
