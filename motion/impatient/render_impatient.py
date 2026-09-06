#!/usr/bin/env python
"""IMPATIENT ("come on!", the duck's answer after "We shouldn't go."): two quick head shakes with a grumbly double
quack, then the beak flicks up with a huff. One-shot design; Rémi mentioned an impatient move in Laureen's simulator
that is not in its published source, so this is our own take."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "sounds")); sys.path.insert(0, str(ROOT / "motion/episode3"))
import lib
from lib import Motion, pulse, ramp, swings
from quack import ROBOT_SEED, SR, Personality, normalise, quack, write_wav, read_wav
from make_synced_v2 import Track

p = Personality(ROBOT_SEED)
SHAKES = [0.35, 0.75, 1.15, 1.55]        # yaw extremes +,-,+,-
HUFF = 1.9                                # beak flicks up
Q = [0.4, 0.8, 1.2, 1.6, 1.95]            # grumbles on the shakes, the huff at the end
TOTAL = 2.6
GRUMBLE = dict(quackiness=0.8, breath=0.05, vibrato_depth=0.2, attack_sharpness=0.6, brightness=0.25, am_depth=0.5, nasal=0.9)


def grumble(f0, dur=0.16, level=-4.0):
    sig = quack(p, dur, [(0.0, f0), (dur, f0 / 2 ** (2 / 12))], ("expdecay", 0.01, dur * 0.5), mods=GRUMBLE, click_gain=0.1)
    return normalise(sig, level)


def huff(level=-3.0):
    sig = quack(p, 0.3, [(0.0, 240), (0.08, 320), (0.3, 250)], ("expdecay", 0.01, 0.16), mods=dict(GRUMBLE, breath=0.15, quackiness=0.6))
    return normalise(sig, level)


def sound():
    tr = Track(TOTAL)
    for i, t in enumerate(Q[:4]):
        tr.put(t, grumble(230 - 6 * i, level=-4.0 + 0.4 * i))
    tr.put(Q[4], huff())
    return tr.buf


def fn(t):
    yaw = swings(t, SHAKES, 0.4, 0.25)
    up = -0.7 * pulse(t, HUFF - 0.15, 0.15, 0.25, 0.4)
    bob = sum(0.08 * pulse(t, s - 0.15, 0.15, 0.0, 0.2) for s in SHAKES)
    return dict(head_yaw=yaw, head_pitch=up, body_pitch=min(0.26, bob))


M = Motion("impatient", "four quick yaw shakes +-0.4 (0.4 s apart) with a body bob on each and a grumble per shake, then the beak flicks up (-0.7) on a huff; level by 2.5 s",
           TOTAL, fn, beats=[(0.4, "grumble 1"), (0.8, "grumble 2"), (1.2, "grumble 3"), (1.6, "grumble 4"), (1.95, "huff, beak up"), (2.5, "back")], quacks=Q)
WAV = ROOT / "sounds/impatient/impatient__I1_grumbles_huff.wav"


def pick():
    return M, WAV, "I1_grumbles_huff"


if __name__ == "__main__":
    write_wav(WAV, sound(), -3.0)
    lib.render(M, WAV, HERE, ROOT / "combined/impatient", sound="I1_grumbles_huff", sound_desc="four short nasal grumbles stepping down, then a rising-falling huff on the beak flick")
    sr, x = read_wav(WAV); idx = np.where(np.abs(x) > 1e-3)[0]; write_wav(ROOT / "sounds/robot/impatient_a.wav", x[:idx[-1] + int(0.05 * SR)], -3.0)
    lib.write_page(ROOT / "combined/impatient", "impatient: 'come on!' (the answer after 'We shouldn't go.')",
                   "Standing, neck 0. head_yaw = swings([0.35, 0.75, 1.15, 1.55], 0.4, fade 0.25); body bob +0.08 on each shake; head_pitch = -0.7 pulse from 1.75 s (0.15 up, 0.25 hold, 0.4 down); grumbles at 0.4 / 0.8 / 1.2 / 1.6 s, the huff at 1.95 s. 2.6 s.",
                   [("pick", "", [lib.card(HERE, ROOT / "combined/impatient", "impatient__I1_grumbles_huff", "impatient + I1_grumbles_huff")])])
