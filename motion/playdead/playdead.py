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
import duckfilm as F  # noqa: E402
sys.path.insert(0, str(HERE))
from pdduck import PDDuck  # noqa: E402
from pdduck3 import PDDuck3, JOINTS  # noqa: E402

ROOT = HERE.parent.parent
SPEC = json.load(open(HERE / "spec.json"))
PAGE = ROOT / "combined" / "playdead"
PICK = ("pd_v3_dead", "D1_alarm_glide_wobble")
PICK_V2 = ("pd_v2_faint", "D1_alarm_glide_wobble")
PICK_V1 = ("pd_faint", "D1_alarm_glide_wobble")
CURRENT_INIT_AT = None      # set before each render: the v2 duck's robot.init time (motion clock)
CURRENT_V3 = None           # set before each render: the v3 motion's beats (robot.pose_joints parameters)


def targets_of(legs):
    """14 joint targets in duckfilm.JOINTS order from a {joint: angle} dict; None = hold where it is (the head)."""
    return [legs.get(n) for n in JOINTS]


def fresh_pd(camera="side", reachy_at=None):
    """lib.fresh with the play-dead duck (relax, then robot.init = 2 s ramp to home, then hold)."""
    m, d = F.build_scene(lib.SIZE, reachy_at=reachy_at)
    du = (PDDuck3 if CURRENT_V3 else PDDuck)(m, d, "duck_")
    du.make_bam()
    du.spawn(0.0, 0.0, 0.0)
    import mujoco
    mujoco.mj_forward(m, d)
    du.bam.last_ts = d.time
    du.init_at = CURRENT_INIT_AT
    if CURRENT_V3:
        b = CURRENT_V3
        du.set_pose_joints(b["cut"], targets_of(b["legs"]), b["off"], b["gain"], b["ramp"])
        if b.get("legs2"):
            du.stage2 = (b["cut2"], targets_of(b["legs2"]), b["ramp2"])
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    c = lib.CAMERAS[camera]
    cam.lookat[:] = c["lookat"]
    cam.distance, cam.azimuth, cam.elevation = c["distance"], c["azimuth"], c["elevation"]
    return m, d, du, cam


lib.fresh = fresh_pd
SHOCK_UP = -0.5          # the startled look up at the press (head_pitch negative = beak up)
HEADBACK = -1.0          # the lever: beak to the sky (tracks to about -0.9 seated)
DEATH_MOUTH = 0.3        # the beak barely open on the death quack
ramp, pulse = lib.ramp, lib.pulse


def make_motion(name):
    b = SPEC["motions"][name]
    y0, y1 = b["yaw"]
    if b["recipe"] == "v2":
        return make_motion_v2(name, b)
    if b["recipe"] == "v3":
        return make_motion_v3(name, b)

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


def make_motion_v2(name, b):
    """v2: yaw hard to the side from the press (with the sit), head back at once, robot.relax, robot.init, death quack."""
    y0, y1 = b["yaw"]
    h0, h1 = b["headback"]
    amp = b.get("headback_amp", HEADBACK)

    def fn(t):
        h = dict(skill="sit" if t < b["relax"] else None, relax=b["relax"] <= t < b["init"], twist=(0.0, 0.0, 0.0))
        s0, s1 = b["shock"]
        h["head_pitch"] = SHOCK_UP * pulse(t, s0, 0.12, s1 - s0 - 0.12 - 0.3, 0.3) + amp * ramp(t - h0, h1 - h0)
        h["head_yaw"] = b["yaw_amp"] * ramp(t - y0, y1 - y0)
        if t >= b["death"] - 0.1:
            h["mouth"] = DEATH_MOUTH * pulse(t, b["death"], 0.15, b["death_len"] - 0.15 - 0.6, 0.6)
        return h

    beats = [(y1, "head to the side"), (h1, "head back"), (b["relax"], "relax (torque off)"), (b["relax"] + 0.6, "tipping"),
             (b["rest"], "at rest"), (b["init"] + 1.0, "init ramp"), (b["init"] + 2.0, "home, held"),
             (b["death"] + 0.4, "death quack"), (b["death"] + b["death_len"], "quack ends")]
    return lib.Motion(name, b["desc"], b["total"], fn, beats=beats, camera="side", quacks=[0.15, b["death"] + 0.3]), b


def make_motion_v3(name, b):
    """v3: the same head choreography as v2; at `cut` robot.pose_joints (head servos off, legs to zero, ramp) and at `cut2`
    a second one (legs up); no relax, no init; the death quack once it lies still; the pose is held to the end."""
    y0, y1 = b["yaw"]
    h0, h1 = b["headback"]

    def fn(t):
        h = dict(skill="sit" if t < b["cut"] else None, twist=(0.0, 0.0, 0.0))
        s0, s1 = b["shock"]
        h["head_pitch"] = SHOCK_UP * pulse(t, s0, 0.12, s1 - s0 - 0.12 - 0.3, 0.3) + HEADBACK * ramp(t - h0, h1 - h0)
        h["head_yaw"] = b["yaw_amp"] * ramp(t - y0, y1 - y0)
        if t >= b["death"] - 0.1:
            h["mouth"] = DEATH_MOUTH * pulse(t, b["death"], 0.15, b["death_len"] - 0.15 - 0.6, 0.6)
        return h

    beats = [(y1, "head to the side"), (h1, "head back"), (b["cut"], "head servos off, legs straighten"), (b["cut"] + 0.7, "rolling over"),
             (b["rest"], "at rest, flat"), (b["death"] + 0.4, "death quack"), (b["death"] + b["death_len"], "quack ends")]
    if b.get("legs2"):
        beats.insert(5, (b["cut2"] + b["ramp2"], "legs up (the last twitch)"))
    return lib.Motion(name, b["desc"], b["total"], fn, beats=beats, camera="side", quacks=[0.15, b["death"] + 0.3]), b


MOTIONS = {n: make_motion(n)[0] for n in SPEC["motions"]}


def pick():
    """The recommended pair: (lib.Motion, wav Path, sound stem)."""
    r = next(r for r in SPEC["renders"] if (r["motion"], r["sound"]) == PICK)
    return MOTIONS[PICK[0]], Path(r["wav"]), PICK[1]


def probe_table3():
    p = HERE / "probe3.json"
    if not p.exists():
        return ""
    rows = json.load(open(p))["rows"]
    tr = "".join(f"<tr><td>{r['recipe']}</td><td><b>{r['end']}</b> {r['trunk_pitch_end_deg']:+.0f}&deg;</td><td>{r['left_upright_at']}</td><td>{r['rest_at']}</td>"
                 f"<td>{r['peak_trunk_w_rad_s']}</td><td>{r['peak_head_speed_m_s']}</td><td>{r['gap_before_cut_mm']} / {r['gap_after_cut_mm']}</td>"
                 f"<td>{r['head_end']}</td><td>{r['feet_z_end_cm']} (trunk {r['trunk_z_end_cm']})</td></tr>" for r in rows)
    return f"""<h2>Fall probe v3 (probe3.py, no video): head servos off + legs driven to a pose (robot.pose_joints)</h2>
<p>Every recipe: sit at t = 0, yaw 1.0 over 0-0.5 s, head back (-1.0) over 0.4-1.0 s; at <code>cut</code> the head servos (neck_pitch, head_pitch, head_yaw; <code>off4</code> = the roll too)
lose their torque and the legs are ramped to the pose over <code>ramp</code> s at gain <code>g</code>: <code>zero</code> = every leg joint at 0 (straight), <code>seated</code> = the seat's own angles
(hold), <code>home</code> = the standing pose, <code>legsupA</code> = hips -1.0 / knees 1.5, <code>E</code> = hips -0.8 / knees 1.2 / ankles 0.3, <code>F</code> = hips -1.3 / knees 1.5 / ankles -0.3,
<code>two_</code> = zero first, then legs up once it lies there (a second call). "gap" = closest head-shell / trunk approach before / after the cut (0 after = the unpowered head rests on the trunk).
"feet z" = the ankles' height at the end (the legs up = 7-8 cm; flat = 1.9 cm).</p>
<table><tr><th>recipe</th><th>ends</th><th>leaves upright (s)</th><th>at rest (s)</th><th>peak trunk rot (rad/s)</th><th>peak head speed (m/s)</th><th>gap before / after (mm)</th><th>head joints at the end</th><th>feet z at the end (cm)</th></tr>{tr}</table>
<p>Verdict: every zero-legs recipe rolls the duck flat onto its back (+90&deg;) by 2.1-3.3 s; the slower the leg ramp the softer (1.5 s: 7.5 rad/s, vs 9.6 with 0.5 s), the gain hardly matters
(100 / 160 / 200 alike); straight to the legs-up pose is possible but the duck rocks for seconds (rest 4.4-6.1 s) and a 1.4 s cut ends propped at +69&deg;; the seated hold tips slowly and ends propped
at +72&deg;. Best: zero legs at 1.4 s over 1.5 s (7.45 rad/s, flat by 3.0 s), then the legs up at 3.6 s (feet 7.8 cm): the two-stage pick. The unpowered head ends folded back (pitch -1.55, yaw 1.3)
resting on the trunk; with the roll servo off too it hangs at roll 0.43.</p>"""


def probe_table():
    p = HERE / "probe.json"
    if not p.exists():
        return ""
    rows = [r for r in json.load(open(p)) if not r["recipe"].startswith("v3_")]
    tr = "".join(f"<tr><td>{r['recipe']}</td><td><b>{r['end']}</b></td><td>{r['left_upright_at']}</td><td>{r['rest_at']}</td>"
                 f"<td>{r['peak_trunk_w_rad_s']}</td><td>{r['peak_head_speed_m_s']}</td><td>{r.get('gap_before_cut_mm', '')}</td>"
                 f"<td>{r.get('joints_at_cut', '')}</td><td>{r.get('init_peak_trunk_w', '')}</td><td>{r.get('joints_end', '')}</td></tr>" for r in rows)
    return f"""<h2>Fall probe v2 (probe.py, no video): the head hard to the side from the press, then back; robot.relax; robot.init</h2>
<p>Every recipe: sit at t = 0 (the seat lands by ~1 s), yaw 1.0 over 0-0.5 s, the head back (-1.0) over the stated window, then <code>relax</code> at the stated time
(torque off at once). "gap before cut" = closest approach between the head shell and the trunk collision meshes before the torque cut (54 mm at the home pose);
the joints at the cut are what the sit-stand net reached (yaw asked 1.0 -> 0.84). Rows with <code>init</code>: robot.init at that time (2 s ramp to home while
lying on the back): its peak trunk rotation and the joints at the end (the head straight = yaw 0, pitch ~0). ON BACK = the trunk's back on the floor.</p>
<table><tr><th>recipe</th><th>ends</th><th>leaves upright (s)</th><th>at rest (s)</th><th>peak trunk rot (rad/s)</th><th>peak head speed (m/s)</th><th>gap before cut (mm)</th><th>joints at cut</th><th>init: peak trunk rot</th><th>joints at end</th></tr>{tr}</table>
<p>Verdict: every v2 recipe lands on the back; relax at 1.4 s (the head just arrived back) is the softest of them (7.0 rad/s, head 0.90 m/s; v1's soften ramp gave
6.6); relax at 0.8 s (head not back yet) does not fall; the -0.8 head-back is a little gentler on the head (0.79 m/s). The init ramp on the lying duck is gentle
(trunk 0.4 rad/s, head 0.03 m/s), no roll, and it straightens the head (yaw 0.02, pitch -0.2). v1 rows (soften, rise, lean) are in REPORT.md.</p>"""


def page(open_it):
    cards_by = {}
    for r in SPEC["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        is_pick = (r["motion"], r["sound"]) == PICK
        is_v1 = (r["motion"], r["sound"]) == PICK_V1
        note = ""
        if is_pick:
            note = ("v3 pick (Rémi's second feedback): no relax, no re-init. At 1.4 s robot.pose_joints: the three head servos lose their torque (the head "
                    "flops back and to the side, resting on the shoulders), the legs are driven straight (zero angles, gain 160, 1.5 s ramp): the duck rolls "
                    "onto its back (flat and still by 3.0 s); at 3.6 s a second pose_joints raises the legs (hips -1.0, knees 1.5: the last twitch); "
                    "the death quack at 5.0 s with the beak open 0.3 (the jaw is powered); the pose is held until Start")
        elif (r["motion"], r["sound"]) == PICK_V2:
            note = "v2 pick, for comparison (relax at 1.4 s, robot.init at 3.0 s: rejected, the init re-poses the whole duck)"
        elif is_v1:
            note = "v1 pick, for comparison (yaw 0.6 only, late; soften; no torque afterwards)"
        c = lib.card(HERE, PAGE, stem, f"{r['motion']} + {r['sound']}", note=note)
        if is_pick:
            c = c.replace('class="card"', 'class="card pick"', 1)
        cards_by.setdefault(r["motion"], []).append(c)
    pick_cards = cards_by.pop(PICK[0])
    sections = [("The v3 pick: " + PICK[0], SPEC["motions"][PICK[0]]["desc"], pick_cards)]
    for n in [n for n in cards_by if n.startswith("pd_v3")]:
        sections.append((n + " (v3 alternative)", SPEC["motions"][n]["desc"], cards_by.pop(n)))
    sections.append(("v2 pick, for comparison: " + PICK_V2[0] + " (relax, then init: rejected, the init re-poses the whole duck)", SPEC["motions"][PICK_V2[0]]["desc"], cards_by.pop(PICK_V2[0])))
    for n in [n for n in cards_by if n.startswith("pd_v2")]:
        sections.append((n + " (v2 alternative)", SPEC["motions"][n]["desc"], cards_by.pop(n)))
    v1_cards = cards_by.pop(PICK_V1[0])
    sections.append(("v1 pick, for comparison: " + PICK_V1[0], SPEC["motions"][PICK_V1[0]]["desc"], v1_cards))
    for n, cs in cards_by.items():
        sections.append((n + " (v1 alternative)", SPEC["motions"][n]["desc"], cs))
    intro = ("<b>v3 (2026-09-06 evening, Rémi's second feedback)</b>: combination emotion = sit_toggle + a head program + <code>robot.pose_joints</code> "
             "(a new runtime call: the three head servos torque OFF, every other joint driven to given angles at a given gain over a ramp; no policy) twice: "
             "the legs straightened so the duck rolls onto its back, then the legs raised like a dead animal's; the jaw stays powered for the death quack; "
             "the robot HOLDS the dead pose until Rémi's Start (the full init). No relax, no re-init inside the emotion (v2's init re-posed the whole duck). "
             "Probe table (v3 rows) below, then the v2 and v1 picks for comparison.<br><b>v2 (earlier the same day)</b>: combination emotion = sit_toggle + a head program + <code>robot.relax</code> (torque off at once) + "
             "<code>robot.init</code> once the fall is over (torque on, 2 s ramp to the home pose: the head straightens, the last twitch) + the death quack "
             "with the beak open 0.3 (the runtime is being changed so the mouth works while the robot holds after an init). The head turns hard to the side "
             "(yaw 1.0) from the press, with the sit, and goes back at once, so the back of the head clears the shoulders (sim: 27 mm gap vs 23 mm with yaw 0.6). "
             "Simulation, side camera, 640x480, 30 fps. v1 (soften, head yaw 0.6 late, no torque afterwards) is kept below for comparison. "
             "Files: <code>/Users/remi/microduck/notes/emotions/motion/playdead/</code> (spec.json, playdead.py, pdduck.py, probe.py, REPORT.md), sounds in <code>sounds/playdead/</code>.") + probe_table()
    intro = intro.replace(probe_table(), probe_table3() + probe_table())
    lib.write_page(PAGE, "play dead (episode 3): shock, sit, keel over backwards, death quack", intro, sections, open_it=open_it)


def robot_wav():
    """The pick's wav from t = 0, trailing silence trimmed, peak -3 dBFS, 48 kHz mono 16-bit."""
    sys.path.insert(0, str(ROOT))
    from quack import read_wav, write_wav
    _, wav, _ = pick()
    sr, x = read_wav(wav)
    loud = np.where(np.abs(x) > 10 ** (-60 / 20))[0]
    end = min(len(x), loud[-1] + int(0.1 * sr))
    out = write_wav(ROOT / "sounds" / "robot" / "play_dead_a.wav", x[:end], -3.0)
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
        b = SPEC["motions"][r["motion"]]
        CURRENT_INIT_AT = b.get("init") if b["recipe"] == "v2" else None
        CURRENT_V3 = b if b["recipe"] == "v3" else None
        lib.render(MOTIONS[r["motion"]], Path(r["wav"]), HERE, PAGE, sound=r["sound"], sound_desc=r["desc"])
        page(open_it=False)
    page(open_it=not a.no_open)
    m, wav, s = pick()
    b = SPEC["motions"][PICK[0]]
    pj = [dict(at=b["cut"], targets=targets_of(b["legs"]), off=b["off"], gain=b["gain"], ramp_s=b["ramp"])]
    if b.get("legs2"):
        pj.append(dict(at=b["cut2"], targets=targets_of(b["legs2"]), off=b["off"], gain=b["gain"], ramp_s=b["ramp2"]))
    json.dump(dict(motion=PICK[0], sound=s, wav=str(wav), duration=b["total"], keyframes_json=str(HERE / f"{PICK[0]}__{s}.json"),
                   joints_order=JOINTS, pose_joints=pj, death_at=b["death"], death_len=b["death_len"], rest_at=b["rest"],
                   skill_at_start="sit_toggle", robot_wav=str(ROOT / "sounds" / "robot" / "play_dead_a.wav")),
              open(HERE / "PICK.json", "w"), indent=1)
    robot_wav()
