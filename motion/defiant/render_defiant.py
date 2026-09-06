#!/usr/bin/env python
"""DEFIANT (Rémi, 2026-09-06 evening, for the answer after the water-resistance line): the beak goes UP and to the LEFT
with a quack, then up and to the RIGHT with another quack. One-shot design on the shared renderer."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "sounds")); sys.path.insert(0, str(ROOT / "motion/episode3"))
import lib
from lib import Motion, pulse, ramp
from quack import ROBOT_SEED, SR, Personality, normalise, quack, write_wav, read_wav
from make_synced_v2 import Track

p = Personality(ROBOT_SEED)
Q = [0.45, 1.15]                 # the two quacks (the head arrives ~0.3 s after the command)
TOTAL = 2.2
CURT = dict(quackiness=0.9, breath=0.02, vibrato_depth=0.1, attack_sharpness=0.8, brightness=0.35, am_depth=0.4)


def wak(f0, dur=0.2, level=-3.0):
    sig = quack(p, dur, [(0.0, f0 * 1.05), (0.03, f0), (dur, f0 / 2 ** (4 / 12))], ("expdecay", 0.006, dur * 0.5), mods=CURT, click_gain=0.2)
    return normalise(sig, level)


def sound():
    tr = Track(TOTAL)
    tr.put(Q[0], wak(270)); tr.put(Q[1], wak(285, level=-2.5))
    return tr.buf


def fn(t):
    up = -0.6 * ramp(t, 0.3) * (1.0 - ramp(t - 1.6, 0.4))                     # beak up throughout
    yaw = 0.6 * ramp(t - 0.15, 0.25) if t < 0.85 else 0.6 + (-0.6 - 0.6) * ramp(t - 0.85, 0.3)   # left, then right
    yaw *= 1.0 - ramp(t - 1.6, 0.4)
    return dict(head_pitch=up, head_yaw=yaw)


M = Motion("defiant", "beak up (-0.6) and to the LEFT (yaw +0.6) with a quack, then to the RIGHT (yaw -0.6) with a second quack; level again by 2.0 s",
           TOTAL, fn, beats=[(0.45, "quack, up-left"), (1.15, "quack, up-right"), (2.0, "back")], quacks=Q)
WAV = ROOT / "sounds/defiant/defiant__D1_two_waks.wav"


def pick():
    return M, WAV, "D1_two_waks"


if __name__ == "__main__":
    write_wav(WAV, sound(), -3.0)
    lib.render(M, WAV, HERE, ROOT / "combined/defiant", sound="D1_two_waks", sound_desc="two curt 'wak's (270 / 285 Hz, falling a third), one per head turn")
    sr, x = read_wav(WAV); idx = np.where(np.abs(x) > 1e-3)[0]; write_wav(ROOT / "sounds/robot/defiant_a.wav", x[:idx[-1] + int(0.05 * SR)], -3.0)
    lib.write_page(ROOT / "combined/defiant", "defiant: 'says who?' (the answer after the water-resistance line)",
                   "Standing, neck 0. head_pitch = -0.6 gate (in 0.3 s, out from 1.6 s); head_yaw +0.6 from 0.15 s, over to -0.6 from 0.85 s (0.3 s ramps), back from 1.6 s; quacks at 0.45 / 1.15 s. 2.2 s.",
                   [("pick", "", [lib.card(HERE, ROOT / "combined/defiant", "defiant__D1_two_waks", "defiant + D1_two_waks")])])
