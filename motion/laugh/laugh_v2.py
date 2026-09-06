#!/usr/bin/env python
"""Laugh v2 + mock (Rémi, 2026-09-06 evening, after the laugh page):
- LAUGH: keep `laugh_wag`, the head aimed a bit more up; the SOUND becomes a "dying of laughter": one longer "haaa"
  first, then several short ha's getting shorter and softer.
- MOCK ("gnagnagnagna", after a scolding): `laugh_roll` + the original L1 staccato run, unchanged.

    /Users/remi/microduck/.venv-mjlab/bin/python motion/laugh/laugh_v2.py
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "sounds")); sys.path.insert(0, str(ROOT / "motion/episode3"))
import lib
from lib import pulse, ramp, swings
from quack import ROBOT_SEED, SR, Personality, normalise, quack, write_wav, read_wav
from make_synced_v2 import Track
from make_laugh import ha, HA, ST, p

# --- laugh v2 beats: a long "haaa" then a dying run ----------------------------------------------------------
LONG_AT, LONG_DUR = 0.35, 0.38
SHORTS = [0.90, 1.10, 1.30, 1.50, 1.85, 2.05, 2.30]         # shorter, softer, the gaps opening up: dying of laughter
HAS2 = [LONG_AT] + SHORTS
SW2 = [0.35, 0.90, 1.30, 1.85, 2.30]                        # yaw extremes, alternating
TOTAL2 = 3.0
LEAD = 0.15


def long_ha(f0=305.0, level=-3.0):
    sig = quack(p, LONG_DUR, [(0.0, f0 * 1.04), (0.03, f0), (0.2, f0 / ST ** 0.8), (LONG_DUR, f0 / ST ** 3.5)],
                ("expdecay", 0.006, LONG_DUR * 0.55), mods=dict(HA, vibrato_depth=0.25, vibrato_rate_hz=7.0), click_gain=0.25)
    return normalise(sig, level)


def sound_v2():
    tr = Track(TOTAL2)
    tr.put(LONG_AT, long_ha())
    for i, t in enumerate(SHORTS):
        dur = 0.12 - 0.008 * i
        f0 = 290 / ST ** (0.5 * i)
        tr.put(t, ha(f0, dur=max(0.07, dur), level=-3.5 - 0.9 * i))
    return tr.buf


def bobs2(t, amp=0.10):
    return sum(amp * pulse(t, th - LEAD, 0.15, 0.0, 0.2) for th in HAS2)


def gate2(t):
    return ramp(t, 0.3) * (1.0 - ramp(t - 2.5, 0.4))


def m_wag2(t):
    return dict(head_pitch=-0.7 * gate2(t), head_yaw=swings(t, SW2, 0.45, 0.3), body_pitch=min(0.26, bobs2(t)))


LAUGH2 = lib.Motion("laugh_wag_v2", "beak aimed up (-0.7), yaw swings +-0.45 on the long ha and every other short one, a body bob on every ha; 3.0 s",
                    TOTAL2, m_wag2, [(LONG_AT, "haaa")] + [(t, f"ha {i + 1}") for i, t in enumerate(SHORTS)], quacks=HAS2)

# --- mock: laugh_roll + L1, unchanged ---------------------------------------------------------------------------
sys.path.insert(0, str(HERE))
import laugh as L1mod
MOCK = lib.Motion("mock", "laugh_roll: beak up (-0.55), the head rolling +-0.35 on every other ha, a body bob on every ha; the L1 staccato run: 'gnagnagnagna'",
                  L1mod.TOTAL, L1mod.m_roll, L1mod._beats(), quacks=L1mod.HAS)
MOCK_WAV = ROOT / "sounds/laugh/laugh_roll__L1_synth_haha.wav"


def robot_wav(src, dst, peak=-3.0):
    sr, x = read_wav(src)
    idx = np.where(np.abs(x) > 10 ** (-60 / 20))[0]
    write_wav(dst, x[:idx[-1] + int(0.05 * SR)], peak)


def pick():
    return LAUGH2, ROOT / "sounds/laugh/laugh_wag_v2__L4_dying.wav", "L4_dying"


def pick_mock():
    return MOCK, MOCK_WAV, "L1_synth_haha"


if __name__ == "__main__":
    wav = write_wav(ROOT / "sounds/laugh/laugh_wag_v2__L4_dying.wav", sound_v2(), -3.0)
    lib.render(LAUGH2, wav, HERE, ROOT / "combined/laugh", sound="L4_dying", sound_desc="one longer falling 'haaa', then seven short ha's getting shorter, softer and further apart (dying of laughter)")
    lib.render(MOCK, MOCK_WAV, HERE, ROOT / "combined/laugh", sound="L1_synth_haha", sound_desc="the L1 staccato run (Rémi: a mockery, 'gnagnagnagna')")
    robot_wav(wav, ROOT / "sounds/robot/laugh_a.wav")
    robot_wav(MOCK_WAV, ROOT / "sounds/robot/mock_a.wav")
    page = ROOT / "combined/laugh"
    html = (page / "index.html").read_text()
    extra = lib.card(HERE, page, "laugh_wag_v2__L4_dying", "LAUGH v2: laugh_wag_v2 + L4_dying", note="Rémi's feedback: head aimed up more, a long 'haaa' then a dying run") + \
            lib.card(HERE, page, "mock__L1_synth_haha", "MOCK: laugh_roll + L1_synth_haha", note="Rémi: 'a great move for a mockery, after someone scolds the duck: gnagnagnagna'")
    html = html.replace("<h2>", "<h2>Round 2 (Rémi's feedback)</h2>" + extra + "<h2>", 1)
    (page / "index.html").write_text(html)
    print("page updated")
