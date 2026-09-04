#!/usr/bin/env python
"""Strategy C: emotion sounds built ONLY from the robot's real quack bank (seed 4145077059).

The bank files are cut, reversed, resampled (pitch + speed together, like a tape machine),
varispeed-resampled (the playback rate glides through the file, so the pitch slides), granular
time-stretched (pitch kept, duration changed), saturated, and sequenced. No synthesis: the timbre is
exactly the robot's own voice.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_C_grains.py

Writes sadness/C_*.wav, anger/C_*.wav (48 kHz mono 16-bit, -3 dBFS peak) and manifest_C.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # notes/emotions/quack.py
from quack import SR, mix, normalise, read_wav, seq, silence, write_wav  # noqa: E402

BANK = Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059")
MANIFEST = []


# ----------------------------------------------------------------------------- bank access
_cache: dict[str, np.ndarray] = {}


def bank(tag: str, variant: str) -> np.ndarray:
    """One bank file as float64 at 48 kHz, e.g. bank("coo", "a"), bank("wheee", "start_a")."""
    key = f"{tag}_{variant}"
    if key not in _cache:
        sr, x = read_wav(BANK / tag / f"{key}.wav")
        assert sr == SR, (key, sr)
        _cache[key] = x
    return _cache[key].copy()


# ----------------------------------------------------------------------------- grain tools
def fade(x: np.ndarray, in_s: float = 0.005, out_s: float = 0.02) -> np.ndarray:
    x = x.copy()
    a, b = int(in_s * SR), int(out_s * SR)
    if a > 0:
        x[:a] *= np.linspace(0, 1, a) ** 2
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b) ** 2
    return x


def cut(x: np.ndarray, start_s: float, end_s: float | None = None) -> np.ndarray:
    return x[int(start_s * SR): None if end_s is None else int(end_s * SR)]


def resample(x: np.ndarray, rate: float) -> np.ndarray:
    """Tape-style: rate > 1 = higher pitch and shorter; rate < 1 = lower and longer."""
    n = max(8, int(round(len(x) / rate)))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def varispeed(x: np.ndarray, rate_points) -> np.ndarray:
    """Tape-style playback whose rate glides through the file. `rate_points` = [(u, rate), ...]
    with u = fraction of the SOURCE consumed (0..1); piecewise linear. Pitch and speed move together,
    so a falling rate is a falling pitch that also slows down."""
    n = len(x)
    u = np.arange(n) / max(n - 1, 1)
    rate = np.interp(u, [p[0] for p in rate_points], [p[1] for p in rate_points])
    t_out = np.cumsum(1.0 / rate)  # output sample index at which each source sample plays
    t_out -= t_out[0]
    out_idx = np.arange(0, t_out[-1])
    src_pos = np.interp(out_idx, t_out, np.arange(n))
    return np.interp(src_pos, np.arange(n), x)


def gstretch(x: np.ndarray, factor: float, grain_ms: float = 30.0) -> np.ndarray:
    """Granular overlap-add time stretch: duration x factor, pitch kept. Slightly rough/phasey,
    which is a feature for growls."""
    g = int(grain_ms * SR / 1000)
    hop_out = g // 2
    hop_in = hop_out / factor
    win = np.hanning(g)
    n_out = int(len(x) * factor) + g
    out = np.zeros(n_out)
    k = 0
    while True:
        i = int(k * hop_in)
        o = k * hop_out
        if i + g > len(x) or o + g > n_out:
            break
        out[o:o + g] += x[i:i + g] * win
        k += 1
    return out[: int(len(x) * factor)]


def saturate(x: np.ndarray, drive: float = 4.0, clip: float | None = None) -> np.ndarray:
    """tanh drive (compresses and adds grit), then optional hard clip at `clip` x peak."""
    y = np.tanh(drive * x / (np.abs(x).max() + 1e-9))
    if clip is not None:
        y = np.clip(y, -clip, clip)
    return y


def am(x: np.ndarray, hz: float, depth: float = 0.8, shape: float = 1.0) -> np.ndarray:
    """Amplitude modulation (tremolo). shape > 1 squares off the wave for a rougher 'rrr'."""
    t = np.arange(len(x)) / SR
    m = 0.5 + 0.5 * np.sin(2 * np.pi * hz * t)
    m = m ** shape
    return x * (1.0 - depth * (1.0 - m))


def gain(x: np.ndarray, db: float) -> np.ndarray:
    return x * 10 ** (db / 20)


def emit(emotion: str, idea: str, sig: np.ndarray, desc: str) -> None:
    sig = np.asarray(sig, dtype=np.float64)
    assert len(sig) / SR <= 2.5, (idea, len(sig) / SR)
    path = HERE / emotion / f"C_{idea}_v1.wav"
    write_wav(path, sig, peak_dbfs=-3.0)
    MANIFEST.append({"file": str(path), "emotion": emotion, "desc": desc,
                     "duration_s": round(len(sig) / SR, 3)})
    print(f"{emotion:8s} {path.name:28s} {len(sig) / SR:5.2f} s  {desc}")


# ============================================================================= SADNESS
def sadness():
    # 1. coo, played on a tape that starts fast (higher) and slows down (lower): the flat 125 Hz coo
    #    becomes a call sliding ~280 -> 100 Hz, shaped like sad2 (held, then dropping at the end).
    coo = bank("coo", "a")
    sig = varispeed(coo, [(0.0, 2.2), (0.55, 1.7), (0.85, 1.05), (1.0, 0.8)])
    sig = fade(sig, 0.03, 0.12)
    emit("sadness", "coo_slide", sig,
         "coo_a on a slowing tape: varispeed 2.2x -> 0.8x so the flat coo glides from ~280 Hz down to ~100 Hz, "
         "held then dropping at the end like sad2")

    # 2. greet played backwards and slow: the loud attack becomes a swelling sigh that fades in and
    #    ends on a soft breath; the falling tape makes the whole thing droop.
    g = bank("greet", "b")[::-1]
    sig = varispeed(g, [(0.0, 0.9), (0.6, 0.7), (1.0, 0.5)])
    sig = fade(sig, 0.05, 0.08)
    emit("sadness", "greet_reverse", sig,
         "greet_b reversed and slowed with a falling tape (0.9x -> 0.5x): the greeting's attack becomes a swelling "
         "sigh that sinks from ~220 Hz to ~110 Hz")

    # 3. inquire reversed: the rising question (215 -> 400 Hz) becomes a falling sigh (400 -> 215),
    #    slowed 1.6x so it lands around 250 -> 130 Hz. Two of them: a sigh, then a smaller, lower sob.
    q = bank("inquire", "a")[::-1]
    sigh = fade(varispeed(q, [(0.0, 0.7), (1.0, 0.55)]), 0.04, 0.10)
    sob = fade(varispeed(bank("inquire", "d")[::-1], [(0.0, 0.6), (1.0, 0.45)]), 0.04, 0.10)
    sig = seq([sigh, gain(sob, -5.0)], 0.12)
    emit("sadness", "inquire_sigh", sig,
         "inquire_a and inquire_d reversed (the rising question becomes a falling sigh) and slowed ~1.6x: "
         "one sigh ~250 -> 130 Hz then a quieter, lower second one")

    # 4. three chirp grains stepping down by minor thirds (a sad staircase), each one drooping a
    #    little inside itself, getting slower and quieter.
    ch = bank("chirp", "h")
    steps = []
    for k, rate in enumerate([1.0, 2 ** (-3 / 12), 2 ** (-6 / 12)]):
        gsig = varispeed(ch, [(0.0, rate * 1.02), (1.0, rate * 0.93)])
        gsig = resample(gsig, 1.0 / (1.0 + 0.25 * k))  # each step a bit slower
        steps.append(gain(fade(gsig, 0.005, 0.06), -2.5 * k))
    sig = seq(steps, [0.22, 0.28])
    emit("sadness", "chirp_minor_steps", sig,
         "chirp_h three times, each a minor third lower than the last (resampled 1.0x, 0.84x, 0.71x), each "
         "slower and quieter than the last, with a small droop inside every note")

    # 5. wheee_start reversed: the 210 -> 550 Hz rising glide becomes a 550 -> 210 fall; slowed to
    #    0.6x it is ~330 -> 125 Hz in 1.9 s, which is the sad2 contour almost exactly.
    w = bank("wheee", "start_a")[::-1]
    sig = varispeed(w, [(0.0, 0.62), (0.7, 0.6), (1.0, 0.5)])
    sig = fade(sig, 0.05, 0.15)
    emit("sadness", "wheee_fall", sig,
         "wheee_start_a reversed and slowed to ~0.6x: the rising 'wheee' glide becomes a long fall from ~330 Hz "
         "to ~110 Hz, the sad2 contour in the duck's own voice")


# ============================================================================= ANGER
def anger():
    # 1. two alarm hits back to back, tails chopped so they are hard and dry; the second a touch
    #    lower, like a "QUACK. QUACK."
    a1 = fade(cut(bank("alarm", "a"), 0.0, 0.20), 0.0, 0.03)
    a2 = fade(cut(bank("alarm", "c"), 0.0, 0.22), 0.0, 0.04)
    sig = seq([a1, resample(a2, 0.94)], 0.07)
    emit("anger", "alarm_double", sig,
         "alarm_a then alarm_c, each cut to its first 0.2 s (tail chopped), 70 ms apart, the second 1 semitone "
         "lower: two dry hard hits")

    # 2. rasp: alarm_a granular-stretched to 1.3 s as the growl body (pitch kept, ~550 -> 310 Hz),
    #    with the click of a peck stacked at 11 Hz underneath and a matching 11 Hz tremolo; a short
    #    alarm hit closes it, like irritated2's rise at the end.
    body = gstretch(bank("alarm", "a"), 3.8, grain_ms=28)
    body = am(body, 11.0, depth=0.7, shape=2.0)
    click = fade(cut(bank("peck", "a"), 0.0, 0.012), 0.0, 0.004)
    clicks = mix([(k / 11.0, click) for k in range(int(len(body) / SR * 11))], total=len(body) / SR)
    rasp = mix([(0.0, body), (0.0, gain(clicks, -2.0))])
    end = fade(cut(bank("alarm", "d"), 0.0, 0.18), 0.0, 0.03)
    sig = seq([fade(rasp, 0.01, 0.05), resample(end, 1.06)], 0.02)
    emit("anger", "alarm_peck_rasp", sig,
         "alarm_a time-stretched 3.8x (pitch kept) into a 1.3 s growl, with peck_a's click stacked at 11 Hz "
         "and an 11 Hz tremolo for the rasp, then a chopped alarm_d hit as the snap at the end")

    # 3. bark: greet_e pitched down 5 semitones, tanh-driven and hard-clipped so it barks; twice,
    #    the second one lower still.
    g = bank("greet", "e")
    b1 = saturate(resample(g, 2 ** (-5 / 12)), drive=7.0, clip=0.55)
    b2 = saturate(resample(g, 2 ** (-7 / 12)), drive=8.0, clip=0.5)
    sig = seq([fade(b1, 0.002, 0.03), fade(b2, 0.002, 0.04)], 0.13)
    emit("anger", "greet_bark", sig,
         "greet_e pitched down 5 then 7 semitones, driven through tanh and hard-clipped (intentional): "
         "two barks, the second lower")

    # 4. rising growl: the start of wheee_start (a rising glide) pitched down to ~125 -> 180 Hz,
    #    chopped into a 24 Hz tremolo and saturated, so it snarls upward and stops dead on an alarm hit.
    w = cut(bank("wheee", "start_a"), 0.0, 0.55)
    growl = resample(w, 0.6)
    growl = saturate(am(growl, 24.0, depth=0.85, shape=2.5), drive=3.5)
    growl = fade(growl, 0.02, 0.01)
    snap = fade(cut(bank("alarm", "g"), 0.0, 0.16), 0.0, 0.03)
    sig = seq([growl, snap], 0.0)
    emit("anger", "wheee_growl", sig,
         "first 0.55 s of wheee_start_a pitched down to 0.6x (a rising ~125 -> 180 Hz snarl), 24 Hz tremolo and "
         "tanh saturation, cut dead into a chopped alarm_g hit")

    # 5. reprimand: a run of "tsk" notes made of pecks pitched up 1.7x (short clicky taps) in the
    #    rhythm of reprimand3, ending on a chopped alarm hit that falls, like reprimand3's last note.
    tsk_src = ["a", "h", "i", "e", "j"]
    tsks = [fade(resample(cut(bank("peck", v), 0.0, 0.10), 1.7), 0.0, 0.02) for v in tsk_src]
    times = [0.0, 0.30, 0.48, 0.80, 0.96]
    final = fade(cut(bank("alarm", "b"), 0.0, 0.24), 0.0, 0.05)
    sig = mix([(t, tsk) for t, tsk in zip(times, tsks)] + [(1.40, resample(final, 0.9))])
    emit("anger", "peck_tsk_run", sig,
         "five peck grains (a, h, i, e, j) cut to 0.1 s and pitched up 1.7x as 'tsk' taps in reprimand3's rhythm, "
         "closed by a chopped alarm_b hit pitched down 10%")


def main():
    for d in ("sadness", "anger"):
        (HERE / d).mkdir(parents=True, exist_ok=True)
    sadness()
    anger()
    with open(HERE / "manifest_C.json", "w") as f:
        json.dump(MANIFEST, f, indent=2)
    print(f"wrote {HERE / 'manifest_C.json'} ({len(MANIFEST)} files)")


if __name__ == "__main__":
    main()
