"""Strategy B: emotion sounds designed PROGRAMMATICALLY from music theory and prosody.

No reference recording is used. Each candidate is a different musical idea rendered with the
robot's own voice (`Personality(4145077059)`, pitch centre 238 Hz ~ Bb3), so it stays a quack:
the harmonic timbre and the AM "buzz" are kept, only the contour, rhythm, envelope and a few
per-sound traits (vibrato, rasp depth, attack, breath) change.

Tonal space: G minor around the robot's centre (G3 196, Bb3 233, D4 294, F3 175...).

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_B_notes.py

Outputs: sounds/sadness/B_*_v1.wav, sounds/anger/B_*_v1.wav, sounds/manifest_B.json,
sounds/analysis/B_*.png (spectrogram + crude f0 track).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from quack import (SR, TAU, Personality, ROBOT_SEED, bell, expdecay, lerp, mix, normalise, note,  # noqa: E402
                   quack, read_wav, semitones, seq, silence, t_axis, write_wav)

P = Personality(ROBOT_SEED)
OUT_SAD = HERE / "sadness"
OUT_ANG = HERE / "anger"
OUT_ANA = HERE / "analysis"

# Named pitches (G minor around the robot's 238 Hz centre)
F3, G3, Ab3, A3, Bb3, C4, D4, Eb4, E4, F4, Gb4 = (note(n) for n in
                                                  ("F3", "G3", "Ab3", "A3", "Bb3", "C4", "D4", "Eb4", "E4", "F4", "Gb4"))

# --------------------------------------------------------------------------- shared per-emotion traits
# Sadness: darker timbre (higher tilt = weaker upper harmonics), slower and wider vibrato, no
# attack snap, more breath, buzz kept but softened (quackiness 0.5 keeps it a duck).
SAD = dict(tilt=2.1, brightness=0.25, vibrato_rate_hz=4.2, vibrato_depth=0.55, attack_sharpness=0.0,
           breath=0.16, quackiness=0.5, am_depth=0.22, jitter_depth=0.05)
# Anger: harsher timbre (lower tilt = stronger upper harmonics), full-depth AM buzz at a rasp
# rate, snappy attack, no vibrato (a wobble reads as pleading, not anger), heavier jitter.
ANG = dict(tilt=1.25, brightness=0.55, vibrato_rate_hz=0.0, vibrato_depth=0.0, attack_sharpness=1.0,
           breath=0.03, quackiness=1.0, am_depth=1.0, am_rate_hz=28.0, jitter_depth=0.12)


def rng(i: int):
    """A different random stream per note so vibrato phase / jitter differ between notes."""
    return P.variant_rng("emotionB", i)


def sad_note(hz_start, hz_end, dur, attack, decay, gain=1.0, i=0, mods=None, breath_scale=1.0):
    m = dict(SAD)
    if mods:
        m.update(mods)
    return gain * quack(P, dur, [(0.0, hz_start), (dur, hz_end)], ("expdecay", attack, decay),
                        mods=m, rng=rng(i), breath_scale=breath_scale)


def hit(hz_start, hz_end, dur, gain=1.0, i=0, mods=None, crackle=0.10, click=0.5, decay=None,
        am_rate=None):
    """One short hard anger hit: instant attack, click transient, crackle, short decay."""
    m = dict(ANG)
    if am_rate:
        m["am_rate_hz"] = am_rate
    if mods:
        m.update(mods)
    return gain * quack(P, dur, [(0.0, hz_start), (0.03, hz_start * 1.04), (dur, hz_end)],
                        ("expdecay", 0.004, decay or dur * 0.55), mods=m, rng=rng(i),
                        click_gain=click, crackle=crackle)


# =========================================================================== SADNESS
def sad_minor_third_fall():
    """Two notes, Bb3 -> G3: the descending minor third, the classic 'sigh' interval. The second
    note is longer, softer and dies away with slow wide vibrato."""
    a = sad_note(Bb3, semitones(Bb3, -0.5), 0.55, 0.08, 0.35, gain=1.0, i=1)
    b = sad_note(G3, semitones(G3, -1.5), 1.3, 0.12, 0.55, gain=0.75, i=2,
                 mods=dict(vibrato_depth=0.7, vibrato_rate_hz=3.8), breath_scale=1.5)
    return seq([a, b], 0.12)


def sad_sigh_glide():
    """One long sigh: a small lift (the in-breath), then a continuous slide down more than an
    octave, 300 -> 115 Hz, breathy, wide slow vibrato, amplitude dying away."""
    dur = 2.0
    t = t_axis(dur)
    contour = lerp(t, [(0.0, 270), (0.18, 305), (0.6, 240), (1.3, 160), (dur, 115)])
    env = expdecay(t, 0.15, 0.7) * lerp(t, [(0, 1), (0.5, 1), (dur, 0.35)])
    m = dict(SAD, vibrato_rate_hz=3.6, vibrato_depth=0.65, breath=0.22, tilt=2.3)
    return quack(P, dur, contour, env, mods=m, rng=rng(3), breath_scale=1.6)


def sad_lament_tetrachord():
    """The lament bass: four steps down the minor scale, Bb3 Ab3 Gb3 F3 (1, b7, b6, 5 in Bb
    minor), each note softer and slower than the last, the final note held and fading."""
    pitches = [Bb3, Ab3, semitones(Bb3, -4), F3]
    durs = [0.40, 0.42, 0.46, 0.92]
    gains = [1.0, 0.85, 0.72, 0.62]
    notes = []
    for i, (hz, d, g) in enumerate(zip(pitches, durs, gains)):
        last = i == len(pitches) - 1
        notes.append(sad_note(hz, semitones(hz, -0.7 if not last else -1.2), d, 0.07, d * (0.6 if last else 0.5),
                              gain=g, i=10 + i,
                              mods=dict(vibrato_depth=0.7 if last else 0.45), breath_scale=1.6 if last else 1.0))
    return seq(notes, [0.05, 0.07, 0.09])


def sad_minor_sixth_reach():
    """Reach and collapse: a leap UP a minor sixth (Bb3 -> Gb4, the 'yearning' interval), held a
    moment with trembling vibrato, then one slow slide down past the start to F3."""
    a = sad_note(Bb3, Bb3 * 1.01, 0.32, 0.08, 0.5, gain=0.8, i=20)
    dur = 1.7
    t = t_axis(dur)
    contour = lerp(t, [(0.0, semitones(Gb4, -1)), (0.08, Gb4), (0.45, Gb4), (1.2, G3 * 1.05), (dur, F3 * 0.97)])
    env = expdecay(t, 0.09, 0.75) * lerp(t, [(0, 1), (0.5, 1), (dur, 0.4)])
    m = dict(SAD, vibrato_rate_hz=4.6, vibrato_depth=0.6, breath=0.18)
    b = quack(P, dur, contour, env, mods=m, rng=rng(21), breath_scale=1.4)
    return seq([a, b], 0.05)


def sad_whimper_sobs():
    """A whimper: one low note (G3) drifting downward, with two sob-catches (short dips in the
    loudness like a caught breath) and a tremor that widens and slows as the sound dies."""
    dur = 1.9
    t = t_axis(dur)
    base = lerp(t, [(0.0, G3 * 1.03), (0.4, G3), (1.2, semitones(G3, -2)), (dur, semitones(G3, -4))])
    # hand-made tremor: rate slows 6.5 -> 3.5 Hz, depth widens 0.3 -> 0.9 semitones
    rate = lerp(t, [(0, 6.5), (dur, 3.5)])
    depth = lerp(t, [(0, 0.3), (dur, 0.9)])
    phase = TAU * np.cumsum(rate) / SR
    contour = base * 2.0 ** (depth * np.sin(phase) / 12.0)
    env = expdecay(t, 0.10, 0.9)
    for t0 in (0.55, 0.95):  # two sob-catches: quick 70 ms dips to 15 %
        env *= 1.0 - 0.85 * np.exp(-((t - t0) / 0.035) ** 2)
    m = dict(SAD, vibrato_depth=0.0, breath=0.2, tilt=2.2)
    return quack(P, dur, contour, env, mods=m, rng=rng(30), breath_scale=1.7)


def sad_minor_triad_ritardando():
    """Three notes falling down a G minor triad, D4 Bb3 G3, each one slower and quieter
    (ritardando + diminuendo): a phrase that runs out of energy."""
    pitches = [D4, Bb3, G3]
    durs = [0.40, 0.55, 1.0]
    gains = [1.0, 0.8, 0.6]
    notes = [sad_note(hz, semitones(hz, -0.8), d, 0.06, d * 0.5, gain=g, i=40 + i,
                      mods=dict(vibrato_depth=0.35 + 0.15 * i), breath_scale=1 + 0.3 * i)
             for i, (hz, d, g) in enumerate(zip(pitches, durs, gains))]
    return seq(notes, [0.10, 0.20])


# =========================================================================== ANGER
def ang_double_bark():
    """QUACK QUACK: two short hard hits at 320 Hz (above the centre), instant attack with a click,
    rasp AM at 28 Hz, crackle; the second hit is louder and a touch higher."""
    a = hit(320, 290, 0.17, gain=0.85, i=50)
    b = hit(340, 300, 0.20, gain=1.0, i=51)
    return seq([a, b], 0.09)


def ang_triple_chromatic():
    """Three accelerating stabs climbing a minor second each time (D4 Eb4 E4): the tightest,
    most dissonant step in the scale, repeated, faster and louder each time."""
    pitches = [D4, Eb4, E4]
    gains = [0.8, 0.9, 1.0]
    notes = [hit(hz, hz * 0.92, 0.14, gain=g, i=60 + i, am_rate=30) for i, (hz, g) in enumerate(zip(pitches, gains))]
    return seq(notes, [0.11, 0.07])


def ang_tritone_stabs():
    """Tritone stabs: Bb3 up to E4 (the tritone, the 'devil's interval'), back to Bb3. Three hits,
    the last one held longer and chopped off flat, no decay tail."""
    a = hit(Bb3, Bb3 * 0.95, 0.15, gain=0.85, i=70)
    b = hit(E4, E4 * 0.96, 0.15, gain=1.0, i=71)
    dur = 0.32
    t = t_axis(dur)
    env = bell(t, 0.004, 0.02)  # flat and cut dead
    m = dict(ANG, am_rate_hz=32.0)
    c = quack(P, dur, [(0.0, Bb3 * 1.02), (0.03, Bb3), (dur, Bb3 * 0.985)], env, mods=m, rng=rng(72),
              click_gain=0.5, crackle=0.12)
    return seq([a, b, c], [0.08, 0.08])


def ang_growl_to_bark():
    """A low growl (150 Hz, full-depth rasp at 24 Hz, crackle) swelling and rising over 0.8 s
    into one loud bark at 360 Hz that stops dead."""
    dur_g = 0.85
    t = t_axis(dur_g)
    contour = lerp(t, [(0.0, 140), (0.5, 160), (dur_g, 230)])
    env = lerp(t, [(0, 0.0), (0.12, 0.45), (0.6, 0.7), (dur_g, 1.0)])
    m = dict(ANG, am_rate_hz=24.0, tilt=1.15, jitter_depth=0.2)
    growl = quack(P, dur_g, contour, env, mods=m, rng=rng(80), crackle=0.18)
    dur_b = 0.26
    tb = t_axis(dur_b)
    env_b = bell(tb, 0.003, 0.03)
    bark = quack(P, dur_b, [(0.0, 300), (0.02, 380), (0.15, 360), (dur_b, 330)], env_b,
                 mods=dict(ANG, am_rate_hz=30.0), rng=rng(81), click_gain=0.7, crackle=0.10)
    return seq([0.55 * growl, 1.0 * bark], 0.0)


def ang_flat_then_chopped():
    """Flat-then-chopped: a held rasp at 300 Hz for 0.4 s, then the same note chopped by a hard
    8 Hz gate into a machine-gun 'ka-ka-ka-ka-ka' that rises slightly and ends on the loudest chop."""
    dur = 1.35
    t = t_axis(dur)
    contour = lerp(t, [(0.0, 290), (0.4, 300), (dur, 340)])
    env = bell(t, 0.005, 0.02)
    gate_start = 0.42
    gate = np.ones_like(t)
    g_t = t[t >= gate_start] - gate_start
    period = 1 / 8.0
    ph = (g_t % period) / period
    g = np.where(ph < 0.55, 1.0, 0.0)
    # 3 ms edges so the chops click rather than pop
    from scipy.ndimage import uniform_filter1d
    g = uniform_filter1d(g, int(0.003 * SR))
    ramp = np.linspace(0.8, 1.0, len(g_t))
    gate[t >= gate_start] = g * ramp
    m = dict(ANG, am_rate_hz=33.0, tilt=1.2)
    return quack(P, dur, contour, env * gate, mods=m, rng=rng(90), crackle=0.12)


def ang_snarl_trill():
    """A snarl: fast trill between E4 and F4 (a minor second, 12 alternations per second) over a
    full-depth rasp, then one hard bark a tritone below (Bb3) that cuts off."""
    dur = 0.75
    t = t_axis(dur)
    sq = np.sign(np.sin(TAU * 12.0 * t))
    from scipy.ndimage import uniform_filter1d
    sq = uniform_filter1d(sq, int(0.006 * SR))
    contour = E4 * 2.0 ** (0.5 * (sq + 1) / 12.0) * lerp(t, [(0, 0.97), (dur, 1.06)])
    env = bell(t, 0.02, 0.03) * lerp(t, [(0, 0.7), (dur, 1.0)])
    trill = quack(P, dur, contour, env, mods=dict(ANG, am_rate_hz=26.0), rng=rng(100), crackle=0.14)
    dur_b = 0.28
    tb = t_axis(dur_b)
    bark = quack(P, dur_b, [(0.0, Bb3 * 1.1), (0.02, Bb3), (dur_b, Bb3 * 0.9)], bell(tb, 0.003, 0.05),
                 mods=dict(ANG, am_rate_hz=30.0), rng=rng(101), click_gain=0.7, crackle=0.10)
    return seq([0.8 * trill, bark], 0.04)


# =========================================================================== render + check
CANDIDATES = [
    ("sadness", "minor_third_fall", sad_minor_third_fall),
    ("sadness", "sigh_glide", sad_sigh_glide),
    ("sadness", "lament_tetrachord", sad_lament_tetrachord),
    ("sadness", "minor_sixth_reach", sad_minor_sixth_reach),
    ("sadness", "whimper_sobs", sad_whimper_sobs),
    ("sadness", "minor_triad_ritardando", sad_minor_triad_ritardando),
    ("anger", "double_bark", ang_double_bark),
    ("anger", "triple_chromatic", ang_triple_chromatic),
    ("anger", "tritone_stabs", ang_tritone_stabs),
    ("anger", "growl_to_bark", ang_growl_to_bark),
    ("anger", "flat_then_chopped", ang_flat_then_chopped),
    ("anger", "snarl_trill", ang_snarl_trill),
]


def crude_f0(x, hop=0.02, win=0.04, fmin=80, fmax=800):
    """Autocorrelation pitch track, one value per hop (nan when quiet / unvoiced)."""
    n_hop, n_win = int(hop * SR), int(win * SR)
    lo, hi = int(SR / fmax), int(SR / fmin)
    ts, f0s = [], []
    thresh = 0.02 * np.abs(x).max()
    for start in range(0, len(x) - n_win, n_hop):
        seg = x[start:start + n_win]
        ts.append((start + n_win / 2) / SR)
        if np.sqrt(np.mean(seg ** 2)) < thresh:
            f0s.append(np.nan)
            continue
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[n_win - 1:]
        ac = ac / (ac[0] + 1e-12)
        lag = lo + int(np.argmax(ac[lo:hi]))
        f0s.append(SR / lag if ac[lag] > 0.3 else np.nan)
    return np.array(ts), np.array(f0s)


def analyse(path: Path, emotion: str, idea: str, desc: str):
    sr, x = read_wav(path)
    dur = len(x) / sr
    peak = np.abs(x).max()
    clipped = int(np.sum(np.abs(x) >= 32767 / 32768))
    ok = (sr == SR and np.isfinite(x).all() and clipped == 0 and 0.69 < peak < 0.72 and dur <= 2.5)
    print(f"  {path.name:38s} {dur:5.2f} s  peak {20 * np.log10(peak):6.2f} dBFS  clipped {clipped}  {'OK' if ok else 'CHECK'}")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy.signal import spectrogram

        f, tt, S = spectrogram(x, SR, nperseg=2048, noverlap=1536)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True,
                                       gridspec_kw={"height_ratios": [3, 1]})
        keep = f <= 2000
        ax1.pcolormesh(tt, f[keep], 10 * np.log10(S[keep] + 1e-12), shading="auto", cmap="magma", vmin=-110, vmax=-20)
        ft, f0 = crude_f0(x)
        ax1.plot(ft, f0, "c.", ms=3, label="f0 (autocorr)")
        ax1.axhline(238, color="w", lw=0.5, ls="--", alpha=0.5)
        ax1.set_ylabel("Hz")
        ax1.set_ylim(0, 2000)
        ax1.legend(loc="upper right", fontsize=8)
        ax1.set_title(f"B_{idea}  ({emotion})  {dur:.2f} s\n{desc}", fontsize=9)
        ax2.plot(np.arange(len(x)) / SR, x, lw=0.3, color="k")
        ax2.set_ylim(-1, 1)
        ax2.set_xlabel("s")
        fig.tight_layout()
        OUT_ANA.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUT_ANA / f"B_{emotion}_{idea}.png", dpi=90)
        plt.close(fig)
    except ImportError:
        pass
    return dur, ok


def main():
    manifest = []
    all_ok = True
    for emotion, idea, fn in CANDIDATES:
        out_dir = OUT_SAD if emotion == "sadness" else OUT_ANG
        sig = fn()
        path = write_wav(out_dir / f"B_{idea}_v1.wav", sig, peak_dbfs=-3.0)
        desc = " ".join(fn.__doc__.split())
        dur, ok = analyse(path, emotion, idea, desc)
        all_ok &= ok
        manifest.append({"file": str(path), "emotion": emotion, "desc": desc, "duration_s": round(dur, 3)})
    (HERE / "manifest_B.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {HERE / 'manifest_B.json'}  ({len(manifest)} files, {'all OK' if all_ok else 'SOME NEED CHECKING'})")


if __name__ == "__main__":
    main()
