#!/usr/bin/env python
"""ANGRY (programmatic, X button), episode 3: bows on the body-pose slot + head-yaw snaps + beak up, standing,
hard barks on the snaps, the beak wide open so a held leash drops.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/angry/angry.py [--only SUBSTR] [--no-open] [--page-only]

Reads spec.json (from sounds/make_angry.py). Every motion is a pure function of time on the shipped stand net:
head deltas (neck stays 0: no head-forward on the real robot), body pose pitch / z, mouth override (1.0 for
0.4 s at the first bark so the leash drops even before the sound's own envelope opens the beak). Renders into
motion/angry/ and combined/angry/ through motion/episode3/lib.py.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "episode3"))
import lib  # noqa: E402
from lib import ramp, pulse  # noqa: E402

SPEC = json.load(open(HERE / "spec.json"))
PAGE = lib.ROOT / "combined" / "angry"
PICK = ("bow_snaps", "S1_hard_barks")
MOUTH_WIDE = 0.4          # seconds of forced wide-open beak from the first bark (the leash release)


def knots(t, targets, length):
    """Piecewise targets: at each (time, value) start a half-cosine ramp to `value` over `length`. Starts at 0."""
    v = 0.0
    prev = 0.0
    for t0, val in targets:
        if t >= t0:
            v = prev + (val - prev) * ramp(t - t0, length)
            prev = val if t >= t0 + length else v
    return v


def with_mouth(fn, first_bark):
    def g(t):
        h = fn(t)
        if first_bark <= t < first_bark + MOUTH_WIDE:
            h["mouth"] = 1.0
        return h
    return g


LEAD = 0.15               # the policies answer a head step about 0.3-0.5 s late: command the jabs a little before the bark


def bow_snaps(t):
    """Probe (REPORT.md): the stand net turns a body-pitch pulse >= 0.22 into a deep folded lunge (trunk -20..-37 deg,
    5-14 cm drift); 0.14 over 0.15 s is a clean small push with the trunk still (-3 deg, 0.7 cm). So: small fast bows,
    the snap is in the yaw and in a short head jab from the beak-up baseline to level."""
    b = [0.30, 0.90, 1.50, 2.00]
    pitch = sum(0.14 * pulse(t, tb - LEAD, 0.15, 0.05, 0.25) for tb in b[:3])
    jab = sum(0.45 * pulse(t, tb - LEAD, 0.12, 0.05, 0.30) for tb in b)
    yaw = knots(t, [(0.30 - LEAD, 0.7), (0.90 - LEAD, -0.7), (1.50 - LEAD, 0.7), (2.00 - LEAD, 0.0)], 0.12)
    up = -0.35 * ramp(t, 0.3) * (1.0 - ramp(t - 2.1, 0.4))
    return dict(body_pitch=pitch, head_yaw=yaw, head_pitch=up + jab)


def crouch_shake_lunge(t):
    """Beak up with a slow menacing yaw sweep (the growl window; 3-4 Hz shivers do not move the head, the net is too
    slow), then two jabs with small bows."""
    on = ramp(t, 0.35) * (1.0 - ramp(t - 2.5, 0.4))
    up = -0.6 * on
    sweep = 0.5 * ramp(t - 0.35, 0.3) - 1.0 * ramp(t - 0.8, 0.7) + 0.5 * ramp(t - 1.5 - LEAD, 0.15)
    jab = 0.7 * pulse(t, 1.70 - LEAD, 0.12, 0.10, 0.30) + 0.6 * pulse(t, 2.10 - LEAD, 0.12, 0.05, 0.30)
    pitch = 0.14 * pulse(t, 1.70 - LEAD, 0.15, 0.10, 0.30) + 0.10 * pulse(t, 2.10 - LEAD, 0.15, 0.05, 0.30)
    return dict(body_pitch=pitch, head_pitch=up + jab, head_yaw=sweep * on)


def beakup_triple_bow(t):
    up = -0.6 * ramp(t, 0.6) * (1.0 - ramp(t - 2.2, 0.5))
    b = [0.90, 1.30, 1.70]
    pitch = sum(0.14 * pulse(t, tb - LEAD, 0.15, 0.03, 0.2) for tb in b)
    jab = sum(0.5 * pulse(t, tb - LEAD, 0.12, 0.03, 0.25) for tb in b)
    yaw = knots(t, [(0.90 - LEAD, 0.5), (1.30 - LEAD, -0.5), (1.70 - LEAD, 0.5), (2.2, 0.0)], 0.12)
    return dict(head_pitch=up + jab, body_pitch=pitch, head_yaw=yaw)


def double_lunge(t):
    up = -0.5 * ramp(t, 0.35) * (1.0 - ramp(t - 2.4, 0.4))
    jab = 0.6 * pulse(t, 0.50 - LEAD, 0.12, 0.25, 0.30) + 0.6 * pulse(t, 1.70 - LEAD, 0.12, 0.20, 0.25) + 0.5 * pulse(t, 2.25 - LEAD, 0.10, 0.10, 0.30)
    pitch = 0.14 * pulse(t, 0.50 - LEAD, 0.15, 0.25, 0.30) + 0.14 * pulse(t, 1.70 - LEAD, 0.15, 0.20, 0.25) + 0.10 * pulse(t, 2.25 - LEAD, 0.12, 0.10, 0.30)
    sweep = -0.45 * ramp(t - 0.85, 0.3) + 0.9 * ramp(t - 1.2, 0.3) - 0.45 * ramp(t - 1.7 - LEAD, 0.15)     # re-arming: look left, right, centre
    return dict(head_pitch=up + jab, body_pitch=pitch, head_yaw=sweep)


FNS = dict(bow_snaps=bow_snaps, crouch_shake_lunge=crouch_shake_lunge, beakup_triple_bow=beakup_triple_bow, double_lunge=double_lunge)
BEATS = {
    "bow_snaps": [(0.45, "bow+snap right, bark 1"), (1.05, "bow+snap left, bark 2"), (1.65, "bow+snap right, bark 3"), (2.10, "centre, bark 4"), (2.5, "level")],
    "crouch_shake_lunge": [(0.4, "beak up"), (0.9, "slow sweep (growl)"), (1.4, "sweep"), (1.8, "jab + bow, bark 1"), (2.2, "second jab, bark 2"), (2.9, "level")],
    "beakup_triple_bow": [(0.6, "beak up (menace)"), (1.0, "bow 1, bark 1"), (1.4, "bow 2, bark 2"), (1.8, "bow 3, bark 3"), (2.7, "level")],
    "double_lunge": [(0.35, "beak up"), (0.62, "lunge 1, bark 1"), (1.2, "re-arming sweep"), (1.8, "lunge 2, bark 2"), (2.35, "third jab, bark 3"), (2.8, "level")],
}
MOTIONS = {n: lib.Motion(n, SPEC["motions"][n]["desc"], SPEC["motions"][n]["total"],
                          with_mouth(FNS[n], SPEC["motions"][n]["barks"][0]), beats=BEATS[n], quacks=SPEC["motions"][n]["barks"])
           for n in SPEC["motions"]}


def pick():
    mo, so = PICK
    r = next(r for r in SPEC["renders"] if r["motion"] == mo and r["sound"] == so)
    return MOTIONS[mo], Path(r["wav"]), so


def page(open_it):
    mo, so = PICK
    pick_stem = f"{mo}__{so}"
    sections = []
    first = lib.card(HERE, PAGE, pick_stem, f"PICK: {mo} + {so}",
                     note="recommended: the clearest 'angry' read, every bark on a snap, beak wide on all four, no fall")
    first = first.replace('class="card"', 'class="card pick"', 1)
    sections.append(("Recommended", "The one to ship on X (see REPORT.md for the formulas).", [first]))
    for n in SPEC["motions"]:
        cards = [lib.card(HERE, PAGE, f"{r['motion']}__{r['sound']}", f"{r['motion']} + {r['sound']}")
                 for r in SPEC["renders"] if r["motion"] == n]
        sections.append((n, SPEC["motions"][n]["desc"], cards))
    lib.write_page(PAGE, "angry (X, programmatic): bows, yaw snaps, beak up, hard barks",
                   "Standing on the stand net, twist 0. Body pose pitch (a bow, +) and z (crouch, -) on the pose slot; head yaw snaps and a "
                   "beak-up (head_pitch negative) on the head slot; the neck stays 0 (on the real robot a forward head makes it walk). "
                   "The beak follows the wav's loudness (0.15 s late) and is forced wide open for 0.4 s at the first bark so a held leash drops. "
                   "Simulation 640x480, 30 fps, three-quarter front camera. Files: <code>/Users/remi/microduck/notes/emotions/motion/angry/</code>, "
                   "sounds <code>sounds/angry_v3/</code> (<code>sounds/make_angry.py</code>).", sections, open_it=open_it)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--page-only", action="store_true")
    a = ap.parse_args()
    if not a.page_only:
        for r in SPEC["renders"]:
            stem = f"{r['motion']}__{r['sound']}"
            if a.only and a.only not in stem:
                continue
            lib.render(MOTIONS[r["motion"]], Path(r["wav"]), HERE, PAGE, sound=r["sound"], sound_desc=r["desc"])
    page(not a.no_open)
