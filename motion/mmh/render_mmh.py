#!/usr/bin/env python
"""MMH ("what do you mean?"): Rémi kept `closed_mmh` + C3_mmh from the closed-beak page (2026-09-06) as its own emotion,
with the beak opening normally (the leash falls). Re-render with the beak following the wav."""
import sys
from pathlib import Path
sys.path.insert(0, "/Users/remi/microduck/notes/emotions/motion/episode3")
import lib
from lib import Motion, pulse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WAV = ROOT / "sounds/closed/closed_mmh__C3_mmh.wav"
MOTION = Motion("mmh", "a muffled rising 'mmh?' with a small roll tilt (+0.22 from 0.45 s, held, back by 1.6 s); neck 0, pitch 0",
                2.0, lambda t: dict(head_roll=0.22 * pulse(t, 0.45, 0.3, 0.5, 0.35)),
                beats=[(0.5, "mmh?"), (0.8, "tilt"), (1.3, "hold"), (1.6, "centre")], quacks=[0.5])


def pick():
    return MOTION, WAV, "C3_mmh"


if __name__ == "__main__":
    lib.render(MOTION, WAV, HERE, ROOT / "combined/mmh", sound="C3_mmh", sound_desc="a muffled rising 'mmh?' (205 -> 300 Hz, low-passed 1.1 kHz)")
    lib.write_page(ROOT / "combined/mmh", "mmh: what do you mean? (Rémi's pick from the closed page, beak open)",
                   "Standing, roll tilt only, the beak follows the wav (the leash falls). Formula: head_roll = 0.22 * pulse(t, 0.45, up 0.3, hold 0.5, down 0.35), 2.0 s.",
                   [("pick", "", [lib.card(HERE, ROOT / "combined/mmh", "mmh__C3_mmh", "mmh + C3_mmh")])])
