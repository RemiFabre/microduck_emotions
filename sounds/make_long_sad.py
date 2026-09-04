"""Longer sadness sounds, to fit the 9 s sad motion (droop at 1.5 s, shakes 3.5-7.5 s, rise 8.5-10.5 s).

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_long_sad.py

Writes L_* files into sounds/sadness/ and manifest_L.json. "L" = long / layered versions of the best bets.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from quack import ROBOT_SEED, SR, Personality, mix, normalise, quack, read_wav, seq, silence, write_wav  # noqa: E402

OUT = HERE / "sadness"
BANK = Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059")
p = Personality(ROBOT_SEED)
SAD = dict(quackiness=0.45, breath=0.16, vibrato_rate_hz=3.8, vibrato_depth=0.55, attack_sharpness=0.0, tilt=2.2, am_depth=0.2)


def varispeed(x, rate_start, rate_end, curve=1.0):
    """Play x at a playback rate gliding from rate_start to rate_end (1.0 = original). Rate < 1 = slower and lower."""
    n_out = int(len(x) / ((rate_start + rate_end) / 2))
    u = np.linspace(0, 1, n_out) ** curve
    rate = rate_start + (rate_end - rate_start) * u
    pos = np.cumsum(rate)
    pos = pos / pos[-1] * (len(x) - 1)
    return np.interp(pos, np.arange(len(x)), x)


def fade(x, a=0.02, r=0.15):
    x = x.copy()
    na, nr = int(a * SR), int(r * SR)
    x[:na] *= np.linspace(0, 1, na)
    x[-nr:] *= np.linspace(1, 0, nr)
    return x


items = []


def add(name, sig, desc):
    path = write_wav(OUT / f"{name}.wav", sig)
    items.append({"file": str(path), "emotion": "sadness", "desc": desc, "duration_s": len(sig) / SR})
    print(f"{name}: {len(sig) / SR:.2f} s")


# 1. Long sigh: in-breath lift, then one 3.5 s slide 300 -> 115 Hz with a sob-catch, dying away
dur = 3.6
t = np.arange(int(dur * SR)) / SR
contour = [(0.0, 250), (0.35, 305), (1.2, 230), (2.2, 165), (3.6, 112)]
env = np.exp(-np.maximum(t - 0.4, 0) / 1.6) * np.clip(t / 0.35, 0, 1)
env *= 1 - 0.6 * np.exp(-((t - 1.55) / 0.04) ** 2)  # one sob catch
add("L_long_sigh_v1", quack(p, dur, contour, env, mods=SAD), "3.6 s sigh: small lift, one continuous slide 305 -> 112 Hz with one sob-catch, dying away (long version of B_sigh_glide)")

# 2. Wheee reversed at 0.35x: the bank's own rising glide played backwards, slower and lower (long C_wheee_fall)
_, wh = read_wav(BANK / "wheee" / "wheee_start_a.wav")
rev = wh[::-1]
long_fall = fade(varispeed(rev, 0.5, 0.3, curve=1.3), 0.05, 0.3)
add("L_wheee_fall_slow_v1", long_fall, f"wheee_start_a reversed on a slowing tape (0.5x -> 0.3x): a {len(long_fall) / SR:.1f} s fall in the robot's real timbre (long version of C_wheee_fall)")

# 3. Two calls: the sad2 port at the droop, a lower quieter sob 3.5 s later on the first shake
_, a4 = read_wav(OUT / "A_port_sad2_v4_slow.wav")
sob = quack(p, 1.3, [(0.0, 190), (0.5, 160), (1.3, 105)], ("expdecay", 0.06, 0.6), mods=SAD)
sob = normalise(sob, -9.0)
two = mix([(0.0, a4), (3.5, sob)])
add("L_two_calls_v1", two, "Two calls: A_port_sad2_v4_slow at t=0 (the droop), then a quieter lower sob at t=3.5 s (the first shake). 4.8 s total, fits the motion")

# 4. Three descending calls spaced like the motion: droop, shake 1, shake 2
calls = []
for i, (f_hi, f_lo, d) in enumerate([(300, 150, 1.1), (240, 125, 1.0), (200, 105, 1.2)]):
    c = quack(p, d, [(0.0, f_hi * 0.9), (0.15 * d, f_hi), (0.5 * d, f_hi * 0.75), (d, f_lo)], ("expdecay", 0.05, 0.5 * d), mods=SAD)
    calls.append(normalise(c, -3.0 - 3.0 * i))
three = mix([(0.0, calls[0]), (2.2, calls[1]), (4.4, calls[2])])
add("L_three_calls_v1", three, "Three falling calls 2.2 s apart, each lower and quieter (300->150, 240->125, 200->105 Hz): one per motion beat (droop, shake, shake)")

# 5. Long two-part port: sad2 v5 glide stretched 2.5x then the octave-drop tail held
_, v5 = read_wav(OUT / "A_port_sad2_v5_glide.wav")
stretched = fade(varispeed(v5, 0.5, 0.33, curve=0.8), 0.03, 0.4)
add("L_port_sad2_stretch_v1", stretched, f"A_port_sad2_v5_glide on a slowing tape (0.5x -> 0.33x): the Reachy contour stretched to {len(stretched) / SR:.1f} s and an octave lower at the end")

json.dump(items, open(HERE / "manifest_L.json", "w"), indent=1)
print(HERE / "manifest_L.json")
