#!/usr/bin/env python
"""EXCITED (episode 3): body-pose bounces, beak up, head wagging, a happy rising quack on every bounce.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/excited/excited.py [--only SUBSTR] [--no-open] [--index]

Standing, twist 0, neck 0 throughout (the real robot steps forward when the head's mass goes forward). The body
rides the pose slot (`robot.pose` z in -0.025..+0.010 m, pitch 0..+0.26 rad, roll never); the head uses head_pitch
(negative = beak up) and head_yaw. The beak follows the wav (0.15 s late). Quack beats are declared in
sounds/make_excited.py (spec.json); this file builds the motions from them, renders motion/excited/ + combined/excited/.
"""
import argparse, json, math, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "episode3"))
import lib  # noqa: E402

ramp, pulse = lib.ramp, lib.pulse
SPEC = json.load(open(HERE / "spec.json"))
PAGE = lib.ROOT / "combined" / "excited"
Z_LO, Z_HI = -0.02, 0.01          # the trained z range is -0.025..+0.010


def _bounce_z(t, t0, period, lo=Z_LO, hi=Z_HI):
    """Sinusoidal height bounce from t0: bottom at t0, top at t0 + period/2."""
    mid, amp = (lo + hi) / 2, (hi - lo) / 2
    return mid - amp * math.cos(2 * math.pi * (t - t0) / period)


def m_bounce(t):
    """z is dead on the stand net (probe: +-0 mm); a 2 Hz train of small bow pulses (pitch 0 -> +0.10) dips the trunk instead."""
    q = SPEC["motions"]["excited_bounce"]["quacks"]
    act = ramp(t, 0.25) * (1.0 - ramp(t - 2.6, 0.5))
    bow = 0.16 * max(0.0, -math.cos(2 * math.pi * (t - 0.1) / 0.5)) * act      # a dip every 0.5 s, bottom at 0.35, 0.85, ...
    wag = 0.5 * math.sin(2 * math.pi * (t - 0.1) / 1.0) * act
    return dict(body_pitch=bow, head_pitch=-0.5 * ramp(t, 0.3) * (1.0 - ramp(t - 2.7, 0.5)), head_yaw=wag)


def m_hops(t):
    q = SPEC["motions"]["excited_hops"]["quacks"]
    bow, yaw = 0.0, 0.0
    for i, tq in enumerate(q):
        t0 = tq - 0.25
        bow += 0.15 * pulse(t, t0, 0.25, 0.0, 0.25)
        side = 0.5 if i % 2 == 0 else -0.5
        if t0 <= t < t0 + 0.55:
            yaw = side
    if t >= q[-1] + 0.3:
        yaw = 0.0
    # yaw as a smoothed step: ease between hops (half-cosine over 0.2 s)
    y = 0.0
    for i, tq in enumerate(q):
        t0 = tq - 0.25
        side = 0.5 if i % 2 == 0 else -0.5
        prev = (-side) if i > 0 else 0.0
        if t >= t0:
            y = prev + (side - prev) * ramp(t - t0, 0.2)
    y *= 1.0 - ramp(t - (q[-1] + 0.3), 0.4)
    return dict(body_pitch=bow, head_yaw=y, head_pitch=-0.4 * ramp(t, 0.3) * (1.0 - ramp(t - 2.9, 0.4)))


def m_jumps(t):
    """Two 'jumps': a quick bow crouch (pitch +0.22 over 0.3 s) released fast with the head thrown up, then a fast wag."""
    q = SPEC["motions"]["excited_jumps"]["quacks"]
    bow, hp = 0.0, 0.0
    for tpop in q[:2]:
        tc = tpop - 0.45
        bow += 0.14 * ramp(t - tc, 0.3) * (1.0 - ramp(t - (tc + 0.3), 0.15))
        hp += -0.8 * pulse(t, tc + 0.25, 0.2, 0.3, 0.35)
    w0 = q[2] - 0.15
    wag = 0.6 * math.sin(2 * math.pi * (t - w0) / 0.6) * ramp(t - w0, 0.15) * (1.0 - ramp(t - (q[-1] + 0.15), 0.4))
    hp += -0.35 * ramp(t - w0, 0.3) * (1.0 - ramp(t - (q[-1] + 0.2), 0.4))
    return dict(body_pitch=bow, head_pitch=max(-1.0, hp), head_yaw=wag)


def m_wag_pump(t):
    q = SPEC["motions"]["excited_wag_pump"]["quacks"]
    # yaw: alternating extremes at the quack times (half-cosine between), amplitude 0.6
    knots = [q[0] - 0.3] + q + [q[-1] + 0.3]
    vals = [0.0] + [0.6 * (1 if i % 2 == 0 else -1) for i in range(len(q))] + [0.0]
    yaw = 0.0
    for i in range(len(knots) - 1):
        if knots[i] <= t < knots[i + 1]:
            yaw = vals[i] + (vals[i + 1] - vals[i]) * ramp(t - knots[i], knots[i + 1] - knots[i])
    # the body pumps on each swing extreme: a 0.3 s bow pulse (z is dead on the stand net, pitch dips the trunk)
    pump = 0.0
    for tq in q:
        pump += 0.12 * pulse(t, tq - 0.15, 0.15, 0.0, 0.2)
    # the beak rises over the sequence, then a bow flourish at the end
    hp = -0.15 - 0.55 * ramp(t - q[0], q[-1] - q[0])
    hp *= ramp(t, 0.25) * (1.0 - ramp(t - (q[-1] + 0.35), 0.45))
    bow = 0.12 * pulse(t, q[-1] + 0.15, 0.2, 0.05, 0.3)
    return dict(body_pitch=min(0.26, pump + bow), head_yaw=yaw, head_pitch=hp)


def _beats(name):
    b = SPEC["motions"][name]
    return [(tq, f"quack {i + 1}") for i, tq in enumerate(b["quacks"])]


MOTIONS = {
    "excited_bounce": lib.Motion("excited_bounce", SPEC["motions"]["excited_bounce"]["desc"], SPEC["motions"]["excited_bounce"]["total"],
                                 m_bounce, _beats("excited_bounce") + [(0.1, "bottom 1"), (2.9, "settling")], quacks=SPEC["motions"]["excited_bounce"]["quacks"]),
    "excited_hops": lib.Motion("excited_hops", SPEC["motions"]["excited_hops"]["desc"], SPEC["motions"]["excited_hops"]["total"],
                               m_hops, _beats("excited_hops") + [(0.2, "hop 1 starts"), (3.2, "settling")], quacks=SPEC["motions"]["excited_hops"]["quacks"]),
    "excited_jumps": lib.Motion("excited_jumps", SPEC["motions"]["excited_jumps"]["desc"], SPEC["motions"]["excited_jumps"]["total"],
                                m_jumps, _beats("excited_jumps") + [(0.3, "crouch 1"), (1.2, "crouch 2"), (3.4, "settling")], quacks=SPEC["motions"]["excited_jumps"]["quacks"]),
    "excited_wag_pump": lib.Motion("excited_wag_pump", SPEC["motions"]["excited_wag_pump"]["desc"], SPEC["motions"]["excited_wag_pump"]["total"],
                                   m_wag_pump, _beats("excited_wag_pump") + [(2.95, "bow flourish"), (3.3, "settling")], quacks=SPEC["motions"]["excited_wag_pump"]["quacks"]),
}
PICK = json.load(open(HERE / "PICK.json")) if (HERE / "PICK.json").exists() else None


def pick():
    """(lib.Motion, wav Path, sound stem) of the recommended pair."""
    pk = json.load(open(HERE / "PICK.json"))
    return MOTIONS[pk["motion"]], Path(pk["wav"]), pk["sound"]


def index(open_it=False):
    pk = json.load(open(HERE / "PICK.json")) if (HERE / "PICK.json").exists() else None
    sections = []
    cards_pick = []
    if pk:
        stem = f"{pk['motion']}__{pk['sound']}"
        c = lib.card(HERE, PAGE, stem, f"PICK: {pk['motion']} + {pk['sound']}", note=pk.get("why", ""))
        cards_pick.append(c.replace('class="card"', 'class="card pick"', 1))
        sections.append(("Recommended pick", pk.get("why", ""), cards_pick))
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
    lib.write_page(PAGE, "excited (episode 3): bounces, beak up, wagging, happy rising quacks",
                   "Standing on the stand net, twist 0, neck 0 (the real duck steps forward when the head's mass goes forward). Body on the pose slot "
                   "(z -0.02..+0.01 m, pitch bows only, no roll), head_pitch negative = beak up, head_yaw wag; the beak follows the wav's loudness 0.15 s late. "
                   "Three-quarter front camera, simulation 640x480 30 fps. Motions and json: <code>/Users/remi/microduck/notes/emotions/motion/excited/</code> "
                   "(renderer <code>excited.py</code>, sounds <code>sounds/make_excited.py</code>, report <code>REPORT.md</code>).", sections, open_it=open_it)


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
