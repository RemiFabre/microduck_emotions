"""Strategy A (PORT): recreate the Reachy Mini reference sounds (flute) out of Microduck quack material.

For each reference we extract the f0 contour (autocorrelation, 5 ms hops, median-filtered) and the
RMS envelope, trim the silence, then drive `quack()` (this robot's voice, seed 4145077059) with the
per-sample contour and envelope. Personality mods vary per candidate (rasp for anger, breath for
sadness); anger references sit at 420-630 Hz so we also try them transposed down 5-7 semitones
towards the duck's 238 Hz centre.

Run:  /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_A_port.py
Writes sounds/sadness/A_port_*.wav, sounds/anger/A_port_*.wav, sounds/manifest_A.json and
sounds/analysis/*.png (reference analysis + per-candidate f0 overlay).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EMO = HERE.parent
sys.path.insert(0, str(EMO))
sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, attack_time, expdecay, normalise, quack, seq, t_axis, write_wav  # noqa: E402
from analyze_ref import analyse, segments  # noqa: E402

REF = EMO / "reference"
OUT_SAD = HERE / "sadness"
OUT_ANG = HERE / "anger"
ANALYSIS = HERE / "analysis"
P = Personality(ROBOT_SEED)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None


# ----------------------------------------------------------------------------- contour extraction
def st(x, n):
    """Transpose by n semitones."""
    return x * 2.0 ** (n / 12.0)


def port_contour(a, t0, t1, *, transpose=0.0, stretch=1.0, env_gate_db=-35.0, smooth_s=0.012, fade_s=0.02):
    """Cut [t0, t1] out of an analysis and return (dur, freq_per_sample, env_per_sample).

    f0: voiced frames only, linearly interpolated across unvoiced gaps, held at the edges.
    env: RMS (linear, normalised to 1), gated below `env_gate_db`, smoothed, with short fades.
    `stretch` > 1 slows the whole thing down (time only, pitch untouched)."""
    t, f0, rms_db = a["t"], a["f0"], a["rms_db"]
    m = (t >= t0) & (t <= t1)
    tt = t[m] - t0
    ok = np.isfinite(f0[m])
    if ok.sum() < 2:
        raise ValueError("no voiced frames in window")
    fpts_t, fpts_f = tt[ok], f0[m][ok]
    env_frames = 10 ** (rms_db[m] / 20)
    env_frames = np.where(rms_db[m] > env_gate_db, env_frames, 0.0)
    env_frames /= env_frames.max() + 1e-12
    dur = (t1 - t0) * stretch
    ts = t_axis(dur) / stretch
    freq = np.interp(ts, fpts_t, fpts_f)
    env = np.interp(ts, tt, env_frames)
    k = max(1, int(smooth_s * SR))
    env = np.convolve(env, np.ones(k) / k, mode="same")
    n_fade = int(fade_s * SR)
    if n_fade > 0 and len(env) > 2 * n_fade:
        ramp = np.linspace(0, 1, n_fade)
        env[:n_fade] *= ramp
        env[-n_fade:] *= ramp[::-1]
    return dur, st(freq, transpose), env


def window(a, lo, hi, gate_db=-30.0):
    """First and last voiced time between lo and hi (the main call), from the analysis."""
    segs = [(s, e) for s, e in segments(a["t"], a["voiced"]) if e > lo and s < hi]
    return max(segs[0][0], lo), min(segs[-1][1], hi)


# ----------------------------------------------------------------------------- candidate recipes
SAD_MODS = {  # softer, breathier, slower vibrato, soft attack
    "quackiness": 0.35, "am_depth": 0.18, "vibrato_rate_hz": 4.2, "vibrato_depth": 0.45,
    "attack_sharpness": 0.0, "breath": 0.12,
}
ANGER_MODS = {  # rasp: strong AM buzz at 25-35 Hz, more jitter, brighter, sharp attack
    "quackiness": 1.0, "am_depth": 0.6, "am_rate_hz": 30.0, "jitter_depth": 0.18,
    "brightness": 0.75, "attack_sharpness": 0.9, "breath": 0.03,
}


def make_sadness(a_sad):
    t0, t1 = window(a_sad, 1.0, 2.2)  # the ~1 s call; ignore the faint 700 Hz breath noises later
    print(f"sad2 window {t0:.3f}-{t1:.3f} s")
    out = []

    # v1: faithful port, robot personality untouched, extracted contour + extracted envelope
    dur, f, e = port_contour(a_sad, t0, t1)
    out.append(("A_port_sad2_v1.wav", quack(P, dur, f, e),
                "Faithful port of sad2: extracted flute pitch contour (340 Hz sliding to 235, then an octave drop to ~118 Hz) and its energy envelope, plain robot voice."))

    # v2: breathy and soft (less quack buzz, more breath, slow vibrato)
    dur, f, e = port_contour(a_sad, t0, t1)
    out.append(("A_port_sad2_v2_breathy.wav", quack(P, dur, f, e, mods=SAD_MODS, breath_scale=2.5, am_scale=0.5),
                "Same contour as v1 but breathy and soft: quack buzz halved, pink-noise breath added, slow 4 Hz vibrato, no attack."))

    # v3: transposed down 3 semitones so the start sits nearer the duck's 238 Hz centre, soft
    dur, f, e = port_contour(a_sad, t0, t1, transpose=-3)
    out.append(("A_port_sad2_v3_low.wav", quack(P, dur, f, e, mods=SAD_MODS, breath_scale=1.5, am_scale=0.7),
                "v2 transposed down 3 semitones (285 -> 100 Hz), closer to the duck's own register; darker, heavier."))

    # v4: slowed down 1.4x, a long sigh, with a fitted decaying envelope instead of the raw one
    dur, f, _ = port_contour(a_sad, t0, t1, stretch=1.4)
    t = t_axis(dur)
    e = expdecay(t, 0.06, 0.55 * dur)
    out.append(("A_port_sad2_v4_slow.wav", quack(P, dur, f, e, mods=SAD_MODS, breath_scale=2.0, am_scale=0.6),
                "sad2 contour stretched 1.4x in time (a 1.1 s sigh) with a smooth exponential decay instead of the flute's envelope; breathy."))

    # v5: smoothed contour, the octave step turned into a continuous slide (log-linear), soft
    dur, f, e = port_contour(a_sad, t0, t1)
    fs, fe = float(np.median(f[: int(0.05 * SR)])), float(np.median(f[-int(0.15 * SR):]))
    t = t_axis(dur)
    fsm = fs * (fe / fs) ** np.clip(t / (0.8 * dur), 0, 1)
    out.append(("A_port_sad2_v5_glide.wav", quack(P, dur, fsm, e, mods=SAD_MODS, breath_scale=1.5, am_scale=0.6),
                f"sad2 with the octave step smoothed into one continuous downward glide ({fs:.0f} -> {fe:.0f} Hz over 80% of the call), flute envelope kept; breathy."))
    return out, (t0, t1)


def make_anger(a_irr, a_fru, a_rep):
    out = []
    # --- irritated2: 1.7 s growl 480 -> 420 plateau -> swell to 520 -> 420
    t0, t1 = window(a_irr, 1.4, 3.3)
    print(f"irritated2 window {t0:.3f}-{t1:.3f} s")
    dur, f, e = port_contour(a_irr, t0, t1)
    out.append(("A_port_irritated2_v1.wav", quack(P, dur, f, e, mods=ANGER_MODS, crackle=0.04, click_gain=0.3),
                "Port of irritated2 at the original height (420-520 Hz growl with a swell near the end), raspy: full quack buzz at 30 Hz, crackle, sharp attack.", "irritated2"))
    dur, f, e = port_contour(a_irr, t0, t1, transpose=-6)
    out.append(("A_port_irritated2_v2_down6.wav", quack(P, dur, f, e, mods={**ANGER_MODS, "am_rate_hz": 26.0}, crackle=0.05, click_gain=0.3),
                "irritated2 transposed down 6 semitones (300-370 Hz, in the duck's register), slower 26 Hz rasp, a little more crackle.", "irritated2"))

    # --- frustrated1: 2 s tone, 630 Hz plateau then falling to 460 with wobbles
    t0, t1 = window(a_fru, 0.2, 2.4)
    print(f"frustrated1 window {t0:.3f}-{t1:.3f} s")
    dur, f, e = port_contour(a_fru, t0, t1)
    out.append(("A_port_frustrated1_v1.wav", quack(P, dur, f, e, mods=ANGER_MODS, crackle=0.04, click_gain=0.2),
                "Port of frustrated1 at the original height (630 Hz plateau sagging to 460 Hz over 2 s), raspy quack.", "frustrated1"))
    dur, f, e = port_contour(a_fru, t0, t1, transpose=-5)
    out.append(("A_port_frustrated1_v2_down5.wav", quack(P, dur, f, e, mods={**ANGER_MODS, "am_rate_hz": 34.0, "am_depth": 0.7}, crackle=0.06, click_gain=0.2),
                "frustrated1 transposed down 5 semitones (470 -> 345 Hz), harsher: 34 Hz buzz at full depth, more crackle.", "frustrated1"))

    # --- reprimand3: a rhythm of short notes -> a sequence of quacks with the same timing and pitches
    notes = reprimand_notes(a_rep)
    print("reprimand3 notes:", [(round(n['t0'], 2), round(n['dur'], 2), round(n['f_med'])) for n in notes])
    for name, transpose, bark, desc in [
        ("A_port_reprimand3_v1.wav", 0.0, False,
         "Port of reprimand3: the flute's 'tsk tsk' rhythm as quacks with the same note timing, pitches (290-540 Hz) and levels, raspy voice."),
        ("A_port_reprimand3_v2_down7.wav", -7.0, False,
         "reprimand3 rhythm transposed down 7 semitones (190-360 Hz) so the scolding sits in the duck's register."),
        ("A_port_reprimand3_v3_barks.wav", -5.0, True,
         "reprimand3 rhythm with every note replaced by a short hard bark (<= 120 ms, click on the attack), down 5 semitones: the most 'angry duck' of the three."),
    ]:
        out.append((name, reprimand_sequence(notes, transpose, bark), desc, "reprimand3"))
    return out


def reprimand_notes(a, gate_db=-16.0, min_len=0.04):
    """Split reprimand3 into notes with a stricter energy gate; keep t0, duration, contour, level."""
    a2 = analyse(REF / "reprimand3.wav", rms_gate_db=gate_db)
    notes = []
    for s, e in segments(a2["t"], a2["voiced"], min_len_s=min_len):
        if s < 1.0 or s > 4.5:  # ignore the faint click at 0 s and the tail noise
            continue
        m = (a2["t"] >= s) & (a2["t"] <= e)
        f = a2["f0"][m]
        ok = np.isfinite(f)
        f_med = float(np.median(f[ok]))
        # contour: 5 samples across the note, clipped to a plausible band around the median
        f = np.where(ok, f, f_med)
        f = np.clip(f, 0.7 * f_med, 1.4 * f_med)
        tt = a2["t"][m] - s
        env = 10 ** (a2["rms_db"][m] / 20)
        notes.append(dict(t0=s, dur=e - s, tt=tt, f=f, f_med=f_med, env=env / (env.max() + 1e-12),
                          level=float(env.max())))
    return notes


def reprimand_sequence(notes, transpose, bark):
    parts, gaps = [], []
    mods = {**ANGER_MODS, "am_rate_hz": 32.0}
    for i, n in enumerate(notes):
        dur = min(n["dur"], 0.12) if bark else n["dur"]
        t = t_axis(dur)
        f = st(np.interp(t, n["tt"], n["f"]), transpose)
        if bark or dur < 0.35:
            e = expdecay(t, attack_time(P.with_(**mods), dur, 1.0), dur * (0.35 if bark else 0.6))
        else:  # long stuttering notes keep their own energy shape
            e = np.interp(t, n["tt"], n["env"])
            k = int(0.01 * SR)
            e = np.convolve(e, np.ones(k) / k, mode="same")
            e[: int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))
        s = quack(P, dur, f, e, mods=mods, crackle=0.05, click_gain=0.6 if bark else 0.35)
        s = normalise(s, 0.0) * n["level"]
        parts.append(s)
        if i < len(notes) - 1:
            gaps.append(max(notes[i + 1]["t0"] - (n["t0"] + dur), 0.0))
    return seq(parts, gaps)


# ----------------------------------------------------------------------------- plots and checks
def plot_reference(name, a, win=None):
    if plt is None:
        return
    fig, ax = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    tx = np.arange(len(a["x"])) / a["sr"]
    ax[0].plot(tx, a["x"], lw=0.3, color="0.4")
    ax[0].set_ylabel("waveform")
    ax[1].plot(a["t"], a["rms_db"], color="tab:orange")
    ax[1].set_ylabel("RMS (dB re peak)")
    ax[1].set_ylim(-60, 2)
    ax[2].plot(a["t"], a["f0_raw"], ".", ms=2, color="0.75", label="raw f0")
    ax[2].plot(a["t"], a["f0"], ".", ms=4, color="tab:blue", label="voiced, median-filtered")
    ax[2].set_ylabel("f0 (Hz)")
    ax[2].set_xlabel("time (s)")
    ax[2].set_ylim(0, 900)
    ax[2].legend(loc="upper right")
    for s, e in segments(a["t"], a["voiced"]):
        ax[2].axvspan(s, e, color="tab:blue", alpha=0.08)
    if win:
        for axx in ax:
            axx.axvline(win[0], color="tab:red", lw=0.8)
            axx.axvline(win[1], color="tab:red", lw=0.8)
    fig.suptitle(f"reference {name}: waveform, RMS envelope, f0 track (red = ported window)")
    fig.tight_layout()
    fig.savefig(ANALYSIS / f"ref_{name}.png", dpi=110)
    plt.close(fig)


def plot_candidate(fname, ref_name, a_ref, ref_win, a_out):
    if plt is None:
        return
    fig, ax = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    tr = a_ref["t"] - ref_win[0]
    m = (tr >= -0.05) & (tr <= a_out["t"][-1] + 0.3)
    ax[0].plot(tr[m], a_ref["f0"][m], ".", ms=4, color="0.6", label=f"reference {ref_name}")
    ax[0].plot(a_out["t"], a_out["f0"], ".", ms=4, color="tab:green", label="ported quack")
    ax[0].set_ylabel("f0 (Hz)")
    ax[0].set_ylim(0, 900)
    ax[0].legend(loc="upper right")
    ax[1].plot(tr[m], a_ref["rms_db"][m], color="0.6", label="reference")
    ax[1].plot(a_out["t"], a_out["rms_db"], color="tab:green", label="ported quack")
    ax[1].set_ylabel("RMS (dB re peak)")
    ax[1].set_ylim(-50, 2)
    ax[1].set_xlabel("time from trimmed start (s)")
    ax[1].legend(loc="upper right")
    fig.suptitle(f"{fname} vs {ref_name} (time aligned at the trimmed start)")
    fig.tight_layout()
    fig.savefig(ANALYSIS / f"cand_{Path(fname).stem}.png", dpi=110)
    plt.close(fig)


def f0_stats(a):
    f = a["f0"][np.isfinite(a["f0"])]
    if len(f) == 0:
        return (float("nan"),) * 3
    return float(np.percentile(f, 5)), float(np.median(f)), float(np.percentile(f, 95))


def main():
    for d in (OUT_SAD, OUT_ANG, ANALYSIS):
        d.mkdir(parents=True, exist_ok=True)
    refs = {n: analyse(REF / f"{n}.wav") for n in ["sad2", "irritated2", "frustrated1", "reprimand3"]}

    sad, sad_win = make_sadness(refs["sad2"])
    anger = make_anger(refs["irritated2"], refs["frustrated1"], refs["reprimand3"])
    wins = {"sad2": sad_win, "irritated2": window(refs["irritated2"], 1.4, 3.3),
            "frustrated1": window(refs["frustrated1"], 0.2, 2.4), "reprimand3": (1.35, 3.95)}
    for n, a in refs.items():
        plot_reference(n, a, wins[n])

    manifest = []
    rows = []
    for emotion, folder, items in (("sadness", OUT_SAD, [(*x, "sad2") for x in sad]), ("anger", OUT_ANG, anger)):
        for fname, sig, desc, src in items:
            path = write_wav(folder / fname, sig, peak_dbfs=-3.0)
            a_out = analyse(path)
            a_ref = refs[src]
            w = wins[src]
            plot_candidate(fname, src, a_ref, w, a_out)
            # reference f0 stats inside its ported window only
            mref = (a_ref["t"] >= w[0]) & (a_ref["t"] <= w[1])
            a_ref_w = dict(f0=a_ref["f0"][mref])
            dur = len(sig) / SR
            manifest.append(dict(file=str(path), emotion=emotion, desc=desc, duration_s=round(dur, 3), source=src))
            rows.append((fname, dur, float(np.abs(normalise(sig, -3.0)).max()), f0_stats(a_out), f0_stats(a_ref_w), w[1] - w[0]))
    (HERE / "manifest_A.json").write_text(json.dumps(manifest, indent=2))

    print("\nfile                                dur   peak   out f0 p5/med/p95      ref f0 p5/med/p95   ref dur")
    for fname, dur, peak, fo, fr, rdur in rows:
        print(f"{fname:34s} {dur:5.2f}  {peak:.3f}  {fo[0]:5.0f}/{fo[1]:5.0f}/{fo[2]:5.0f}      {fr[0]:5.0f}/{fr[1]:5.0f}/{fr[2]:5.0f}   {rdur:5.2f}")
    print(f"\nwrote {len(manifest)} files, manifest {HERE / 'manifest_A.json'}, plots in {ANALYSIS}")


if __name__ == "__main__":
    main()
