#!/usr/bin/env python
"""PLAY DEAD (episode 3): a shock quack, the duck sits at once, keels over backwards softly, lies on its back with the
head to the side, then a last death quack with the beak barely open.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/playdead/playdead.py [--only SUBSTR] [--no-open]

Reads spec.json (written by sounds/make_playdead.py: motion beats + (motion, wav) pairs). Every motion is a pure function of
time on the client API (sit skill held, head deltas, body pose, soften), rendered with motion/episode3/lib.py. The fall
recipes were measured first by probe.py (probe.json, table in REPORT.md). Outputs: motion/playdead/ (silent mp4, keyframes
json with mouth, beats sheet, log), combined/playdead/ (muxed mp4 + index.html), PICK.json, sounds/robot/playdead_a.wav.
"""
import argparse, json, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "episode3"))
import lib  # noqa: E402

ROOT = HERE.parent.parent
SPEC = json.load(open(HERE / "spec.json"))
PAGE = ROOT / "combined" / "playdead"
PICK = ("pd_faint", "D1_alarm_glide_wobble")
SHOCK_UP = -0.5          # the startled look up at the press (head_pitch negative = beak up)
HEADBACK = -1.0          # the lever: beak to the sky (tracks to about -0.9 seated)
DEATH_MOUTH = 0.3        # the beak barely open on the death quack
ramp, pulse = lib.ramp, lib.pulse


def make_motion(name):
    b = SPEC["motions"][name]
    y0, y1 = b["yaw"]

    def fn(t):
        h = dict(skill="sit" if t < b["soften"] else None, soften=t >= b["soften"], twist=(0.0, 0.0, 0.0))
        # the shock: a quick look up on the press, back to level while the seat lands
        s0, s1 = b["shock"]
        head_pitch = SHOCK_UP * pulse(t, s0, 0.12, s1 - s0 - 0.12 - 0.3, 0.3)
        yaw = b["yaw_amp"] * ramp(t - y0, y1 - y0)
        if b["recipe"] == "headback":
            h0, h1 = b["headback"]
            head_pitch += HEADBACK * ramp(t - h0, h1 - h0)
        elif b["recipe"] == "lean":
            l0, l1 = b["lean"]
            h["body_pitch"] = b["lean_pitch"] * ramp(t - l0, l1 - l0)
        elif b["recipe"] == "rise":
            if b["rise"] <= t < b["soften"]:
                h["skill"] = "rise"
        h["head_pitch"], h["head_yaw"] = head_pitch, yaw
        # the beak: the wav drives it for the shock; on the death quack it opens only a little
        if t >= b["death"] - 0.1:
            h["mouth"] = DEATH_MOUTH * pulse(t, b["death"], 0.15, b["death_len"] - 0.15 - 0.6, 0.6)
        return h

    beats = [(b["shock"][1], "shock, seat"), (b["soften"], "soften"), (b["soften"] + 1.0, "torque off"),
             (b["rest"], "at rest"), (b["death"] + 0.4, "death quack"), (b["death"] + b["death_len"], "quack ends")]
    if b["recipe"] == "headback":
        beats.insert(1, (b["headback"][1], "head back + side"))
    elif b["recipe"] == "lean":
        beats.insert(1, (b["lean"][1], "lean back"))
    else:
        beats.insert(1, (b["rise"] + 0.2, "legs straighten"))
    return lib.Motion(name, b["desc"], b["total"], fn, beats=beats, camera="side", quacks=[0.15, b["death"] + 0.3]), b


MOTIONS = {n: make_motion(n)[0] for n in SPEC["motions"]}


def pick():
    """The recommended pair: (lib.Motion, wav Path, sound stem)."""
    r = next(r for r in SPEC["renders"] if (r["motion"], r["sound"]) == PICK)
    return MOTIONS[PICK[0]], Path(r["wav"]), PICK[1]


def probe_table():
    p = HERE / "probe.json"
    if not p.exists():
        return ""
    rows = json.load(open(p))
    tr = "".join(f"<tr><td>{r['recipe']}</td><td><b>{r['end']}</b></td><td>{r['left_upright_at']}</td><td>{r['rest_at']}</td>"
                 f"<td>{r['peak_trunk_w_rad_s']}</td><td>{r['peak_head_speed_m_s']}</td><td>{r['head_z_min']}</td></tr>" for r in rows)
    return f"""<h2>Fall probe (probe.py, no video): which client-API recipe puts a seated duck on its back, and how hard</h2>
<p>Every recipe: sit at t = 0 (the seat lands by ~1 s). "soften" = robot.soften (gain 50 at once, to 0 over 1 s, torque off). The sit itself
peaks at 2.2 rad/s of trunk rotation and 0.55 m/s of head speed, so those are the floor. ON BACK = the trunk's back on the floor.</p>
<table><tr><th>recipe</th><th>ends</th><th>leaves upright (s)</th><th>at rest (s)</th><th>peak trunk rot (rad/s)</th><th>peak head speed (m/s)</th><th>head z min (m)</th></tr>{tr}</table>
<p>Verdict: the sit-stand RISE cut short (3_) always lands on the back but hardest (9-11 rad/s, head 1.4 m/s); the head thrown back + soften (2_) lands on the
back at 6.6 rad/s / 0.82 m/s (the head goes first); the seated body-pose lean + soften (4_) is the softest (5.7-6.3 rad/s, the head no faster than the sit itself)
but relies on the net's neck trade-off leaving the duck on the edge of balance once the torque is gone; plain sit + soften/relax (1_, 5_) just slumps in the seat.</p>"""


def page(open_it):
    cards_by = {}
    for r in SPEC["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        is_pick = (r["motion"], r["sound"]) == PICK
        c = lib.card(HERE, PAGE, stem, f"{r['motion']} + {r['sound']}",
                     note="recommended: the head is the lever (deterministic on the robot: the head slots track seated), the fall happens as the torque dies, the alarm is the surprise and the wobble dies with the duck" if is_pick else "")
        if is_pick:
            c = c.replace('class="card"', 'class="card pick"', 1)
        cards_by.setdefault(r["motion"], []).append(c)
    pick_cards = cards_by.pop(PICK[0])
    sections = [("The pick: " + PICK[0], SPEC["motions"][PICK[0]]["desc"], pick_cards)]
    for n, cs in cards_by.items():
        sections.append((n, SPEC["motions"][n]["desc"], cs))
    intro = ("Combination emotion: sit_toggle + a head program + robot.soften. The duck is driven only through what the real robot accepts (sit skill, head deltas, "
             "body pose, soften). Simulation, side camera, 640x480, 30 fps. The beak follows the wav for the shock; on the death quack it opens to 0.3 at most. "
             "<b>After the torque cut the head cannot move any more</b>, so the head goes to its side BEFORE the soften and stays there (the brief's 'then the head "
             "straightens' is not achievable without torque, see REPORT.md). Files: <code>/Users/remi/microduck/notes/emotions/motion/playdead/</code> "
             "(spec.json, playdead.py, probe.py, REPORT.md), sounds in <code>sounds/playdead/</code>.") + probe_table()
    lib.write_page(PAGE, "play dead (episode 3): shock, sit, keel over backwards, death quack", intro, sections, open_it=open_it)


def robot_wav():
    """The pick's wav from t = 0, trailing silence trimmed, peak -3 dBFS, 48 kHz mono 16-bit."""
    sys.path.insert(0, str(ROOT))
    from quack import read_wav, write_wav
    _, wav, _ = pick()
    sr, x = read_wav(wav)
    loud = np.where(np.abs(x) > 10 ** (-60 / 20))[0]
    end = min(len(x), loud[-1] + int(0.1 * sr))
    out = write_wav(ROOT / "sounds" / "robot" / "playdead_a.wav", x[:end], -3.0)
    print("robot wav", out, f"{end / sr:.2f} s")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    for r in SPEC["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        if a.only and a.only not in stem:
            continue
        lib.render(MOTIONS[r["motion"]], Path(r["wav"]), HERE, PAGE, sound=r["sound"], sound_desc=r["desc"])
        page(open_it=False)
    page(open_it=not a.no_open)
    m, wav, s = pick()
    b = SPEC["motions"][PICK[0]]
    json.dump(dict(motion=PICK[0], sound=s, wav=str(wav), duration=b["total"], keyframes_json=str(HERE / f"{PICK[0]}__{s}.json"),
                   soften_at=b["soften"], death_at=b["death"], skill_at_start="sit_toggle", robot_wav=str(ROOT / "sounds" / "robot" / "playdead_a.wav")),
              open(HERE / "PICK.json", "w"), indent=1)
    robot_wav()
