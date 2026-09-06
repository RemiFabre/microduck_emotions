#!/usr/bin/env python
"""LAUGH (episode 3): beak up, head wagging left-right, the body shaking with every "ha"; a quack laugh.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/laugh/laugh.py [--only SUBSTR] [--no-open] [--index]

Standing, twist 0, neck 0 (the real robot steps forward when the head's mass goes forward). Body on the pose slot
(pitch bow pulses only: +0.10..0.14 over 0.15-0.3 s; z is dead on the stand net, roll falls), head_pitch negative =
beak up, head_yaw / head_roll swings on every other ha, a bow pulse on every ha. Beats from sounds/make_laugh.py
(spec.json). The beak follows the wav 0.15 s late (lib).
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "episode3"))
import lib  # noqa: E402

ramp, pulse, swings = lib.ramp, lib.pulse, lib.swings
SPEC = json.load(open(HERE / "spec.json"))
PAGE = lib.ROOT / "combined" / "laugh"
B = SPEC["motions"]["laugh_wag"]
HAS, SW, TOTAL = B["has"], B["swings"], B["total"]
LEAD = 0.15                      # the body bob starts this long before its ha (the pose slot lags)


def bobs(t, amp=0.10):
    return sum(amp * pulse(t, th - LEAD, 0.15, 0.0, 0.2) for th in HAS)


def gate(t):
    """Beak-up envelope: in over 0.3 s, out over 0.4 s from 2.1 s."""
    return ramp(t, 0.3) * (1.0 - ramp(t - 2.1, 0.4))


def m_wag(t):
    return dict(head_pitch=-0.55 * gate(t), head_yaw=swings(t, SW, 0.45, 0.3), body_pitch=min(0.26, bobs(t)))


def m_bob(t):
    pump = sum(0.3 * pulse(t, th - 0.1, 0.12, 0.0, 0.18) for th in HAS)
    hp = -(0.4 + pump) * gate(t)
    return dict(head_pitch=max(-0.8, hp), head_yaw=swings(t, SW, 0.25, 0.3), body_pitch=min(0.26, bobs(t, 0.12)))


def m_roll(t):
    return dict(head_pitch=-0.55 * gate(t), head_roll=swings(t, SW, 0.35, 0.3), body_pitch=min(0.26, bobs(t)))


def _beats():
    return [(th, f"ha {i + 1}") for i, th in enumerate(HAS)] + [(2.4, "settling")]


MOTIONS = {
    "laugh_wag": lib.Motion("laugh_wag", SPEC["motions"]["laugh_wag"]["desc"], TOTAL, m_wag, _beats(), quacks=HAS),
    "laugh_bob": lib.Motion("laugh_bob", SPEC["motions"]["laugh_bob"]["desc"], TOTAL, m_bob, _beats(), quacks=HAS),
    "laugh_roll": lib.Motion("laugh_roll", SPEC["motions"]["laugh_roll"]["desc"], TOTAL, m_roll, _beats(), quacks=HAS),
}


def pick():
    """(lib.Motion, wav Path, sound stem) of the recommended pair."""
    pk = json.load(open(HERE / "PICK.json"))
    return MOTIONS[pk["motion"]], Path(pk["wav"]), pk["sound"]


def index(open_it=False):
    pk = json.load(open(HERE / "PICK.json")) if (HERE / "PICK.json").exists() else None
    sections = []
    if pk:
        stem = f"{pk['motion']}__{pk['sound']}"
        c = lib.card(HERE, PAGE, stem, f"PICK: {pk['motion']} + {pk['sound']}", note=pk.get("why", ""))
        sections.append(("Recommended pick", pk.get("why", ""), [c.replace('class="card"', 'class="card pick"', 1)]))
    for mname, b in SPEC["motions"].items():
        cards = []
        for r in SPEC["renders"]:
            if r["motion"] != mname:
                continue
            stem = f"{mname}__{r['sound']}"
            if pk and stem == f"{pk['motion']}__{pk['sound']}":
                continue
            cards.append(lib.card(HERE, PAGE, stem, f"{mname} + {r['sound']}"))
        sections.append((mname, b["desc"], cards))
    lib.write_page(PAGE, "laugh (episode 3): beak up, head wagging, the body shaking, 'ha-ha-ha-ha, ha-ha-ha'",
                   "Standing on the stand net, twist 0, neck 0. Seven ha's at 0.35 / 0.57 / 0.79 / 1.01, breath, 1.45 / 1.67 / 1.89 s; a bow pulse "
                   "(+0.10..0.12 on the pose slot) on every ha, a head swing on every other one. head_pitch negative = beak up. The beak follows the "
                   "wav's loudness 0.15 s late. Three-quarter front camera, simulation 640x480 30 fps. Files: "
                   "<code>/Users/remi/microduck/notes/emotions/motion/laugh/</code> (renderer <code>laugh.py</code>, sounds "
                   "<code>sounds/make_laugh.py</code>, report <code>REPORT.md</code>).", sections, open_it=open_it)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--index", action="store_true")
    a = ap.parse_args()
    if not a.index:
        for r in SPEC["renders"]:
            stem = f"{r['motion']}__{r['sound']}"
            if a.only and a.only not in stem:
                continue
            lib.render(MOTIONS[r["motion"]], Path(r["wav"]), HERE, PAGE, sound=r["sound"], sound_desc=r["desc"])
    index(open_it=not a.no_open)
