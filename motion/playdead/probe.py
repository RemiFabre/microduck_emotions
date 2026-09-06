#!/usr/bin/env python
"""PLAY DEAD probe: which fall recipe (client API only: sit / rise / head / pose / twist / soften / relax) ends the duck
ON ITS BACK, and how softly? No video: a table (printed + probe.json).

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/playdead/probe.py

Orientation: g = gravity in the trunk frame (duckfilm grav()). Standing g = (0,0,-1). Trunk x is forward, so on the
BACK gx -> -1 (pitch_deg = atan2(-gx,-gz) -> +90), face DOWN gx -> +1 (pitch -90), on a SIDE |gy| -> 1.
"""
import json, math, sys
from pathlib import Path

import mujoco, numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "episode3"))
import lib
import duckfilm as F
from pdduck import PDDuck

SIT = 0.0           # the sit is requested at t = 0 (skill_at_start); seat lands ~0.8-2 s later


def recipe(name, fn, total=7.0):
    return lib.Motion(name, name, total, fn)


def r_soften(hold):
    # sit, hold, soften
    return lambda t: dict(skill="sit" if t < SIT + hold else None, soften=t >= SIT + hold)


def r_headback_soften(hold=1.5, yaw=0.6):
    return lambda t: dict(skill="sit" if t < hold + 0.5 else None,
                          head_pitch=-1.0 if t >= hold else 0.0, head_yaw=yaw if t >= hold else 0.0,
                          soften=t >= hold + 0.5)


def r_rise_soften(rise_at, dt):
    def fn(t):
        if t < rise_at:
            return dict(skill="sit")
        if t < rise_at + dt:
            return dict(skill="rise")
        return dict(soften=True)
    return fn


def r_pose_back(hold, pitch):
    return lambda t: dict(skill="sit" if t < hold + 1.0 else None, body_pitch=pitch if t >= hold else 0.0, soften=t >= hold + 1.0)


def r_relax(hold):
    return lambda t: dict(skill="sit" if t < hold else None, relax=t >= hold)


def r_crouch_soften():
    return lambda t: dict(body_z=-0.025 if 0.0 <= t < 1.5 else 0.0, head_pitch=-1.0 if 0.5 <= t < 1.5 else 0.0, soften=t >= 1.5)


def r_backstep_soften():
    return lambda t: dict(head_pitch=-1.0 if 0.3 <= t < 1.1 else 0.0, twist=(-0.35, 0, 0) if 0.5 <= t < 0.8 else (0, 0, 0), soften=t >= 0.8)


# ---- v2 (Rémi's feedback): the head yaws hard to the side FROM THE PRESS (with the sit), then tilts back at once;
# the torque is cut with robot.relax (at once) instead of soften; robot.init (2 s ramp to home) once the fall is over.
def r_v2(yaw_amp=1.0, yaw=(0.0, 0.5), back=(0.4, 1.0), relax_at=1.4, init_at=None, pitch_amp=-1.0):
    def fn(t):
        h = dict(skill="sit" if t < relax_at else None, relax=t >= relax_at and (init_at is None or t < init_at),
                 head_yaw=yaw_amp * lib.ramp(t - yaw[0], yaw[1] - yaw[0]),
                 head_pitch=pitch_amp * lib.ramp(t - back[0], back[1] - back[0]))
        return h
    fn.init_at = init_at
    return fn


RECIPES = {
    "v2_yaw1_back0.4-1.0_relax1.2": r_v2(relax_at=1.2),
    "v2_yaw1_back0.4-1.0_relax1.4": r_v2(relax_at=1.4),
    "v2_yaw1_back0.4-1.0_relax1.7": r_v2(relax_at=1.7),
    "v2_yaw1_back0.4-1.0_relax2.0": r_v2(relax_at=2.0),
    "v2_yaw1_back0.6-1.4_relax1.8": r_v2(back=(0.6, 1.4), relax_at=1.8),
    "v2_yaw1_back0.6-1.4_relax2.2": r_v2(back=(0.6, 1.4), relax_at=2.2),
    "v2_yaw0.6_back0.4-1.0_relax1.4": r_v2(yaw_amp=0.6, relax_at=1.4),
    "v2_yaw1_back0.4-1.0_relax0.8": r_v2(relax_at=0.8),
    "v2_yaw1_back0.4-1.0_relax1.0": r_v2(relax_at=1.0),
    "v2_yaw1_back0.4-1.2_pitch0.8_relax1.5": r_v2(back=(0.4, 1.2), pitch_amp=-0.8, relax_at=1.5),
    "v2_yaw1_back0.4-1.6_relax1.3": r_v2(back=(0.4, 1.6), relax_at=1.3),
    "v2_yaw1_back0.4-1.0_relax1.4_init3.0": r_v2(relax_at=1.4, init_at=3.0),
    "v2_yaw1_back0.4-1.0_relax1.4_init3.5": r_v2(relax_at=1.4, init_at=3.5),
    "v2_yaw1_back0.4-1.0_relax1.4_init4.0": r_v2(relax_at=1.4, init_at=4.0),
    "v1_2_sit_headback_yaw_soften": r_headback_soften(),
    "1_sit_hold1_soften": r_soften(1.0),
    "1b_sit_hold2_soften": r_soften(2.0),
    "2_sit_headback_yaw_soften": r_headback_soften(),
    "3_sit_rise0.2_soften": r_rise_soften(2.0, 0.2),
    "3_sit_rise0.4_soften": r_rise_soften(2.0, 0.4),
    "3_sit_rise0.6_soften": r_rise_soften(2.0, 0.6),
    "3_sit_rise0.8_soften": r_rise_soften(2.0, 0.8),
    "3_sit_rise1.2_soften": r_rise_soften(2.0, 1.2),
    "4_sit_pose-0.2_soften": r_pose_back(1.5, -0.2),
    "4_sit_pose-0.3_soften": r_pose_back(1.5, -0.3),
    "5_sit_relax": r_relax(1.5),
    "6_crouch_headback_soften": r_crouch_soften(),
    "7_headback_backstep_soften": r_backstep_soften(),
}


def classify(g):
    gx, gy, gz = g
    if gz < -0.7:
        return "upright"
    if gx < -0.7:
        return "ON BACK"
    if gx > 0.7:
        return "face down"
    if abs(gy) > 0.7:
        return "on side (%s)" % ("left" if gy > 0 else "right")
    return "tilted"


def fresh_pd(camera="side"):
    m, d = F.build_scene(lib.SIZE, reachy_at=None)
    du = PDDuck(m, d, "duck_")
    du.make_bam()
    du.spawn(0.0, 0.0, 0.0)
    mujoco.mj_forward(m, d)
    du.bam.last_ts = d.time
    return m, d, du


def run(name, fn, total=7.0):
    m, d, du = fresh_pd()
    du.init_at = getattr(fn, "init_at", None)
    mo = recipe(name, fn, total)
    n_pre = int(round(lib.PREROLL / F.CDT))
    n = int(round(total / F.CDT))
    hist = []
    prev_head = None
    for k in range(-n_pre, n):
        t = k * F.CDT
        h = lib.sample(mo, t)
        du.head[:] = (h["neck"], h["head_pitch"], h["head_yaw"], h["head_roll"])
        du.body[:] = 0
        du.body[0], du.body[1], du.body[2] = h["body_z"], h["body_roll"], h["body_pitch"]
        du.twist[:] = h["twist"]
        du.skill = h["skill"]
        du.soften = bool(h["soften"])
        if h["relax"]:
            du.relax = True
        lib.step(m, d, du, t + lib.PREROLL)
        if k < 0:
            continue
        g = du.grav()
        hp = du.head_pos()
        w = np.linalg.norm(d.qvel[du.fv + 3:du.fv + 6])
        hv = 0.0 if prev_head is None else float(np.linalg.norm(hp - prev_head) / F.CDT)
        prev_head = hp
        gap = du.head_trunk_gap() if (k % 2 == 0) else hist[-1]["gap"]
        q = du.q()
        hist.append(dict(t=round(t, 2), gx=float(g[0]), gy=float(g[1]), gz=float(g[2]), z=float(du.pos()[2]), head_z=float(hp[2]),
                         w=float(w), hv=hv, net=du.net, x=float(du.pos()[0]), gap=float(gap),
                         yaw_j=float(q[7] - F.HOME[7]), pitch_j=float(q[6] - F.HOME[6]), neck_j=float(q[5] - F.HOME[5])))
    g_end = (hist[-1]["gx"], hist[-1]["gy"], hist[-1]["gz"])
    # time to rest: last time the trunk angular speed exceeds 0.3 rad/s
    moving = [h["t"] for h in hist if h["w"] > 0.3]
    rest = moving[-1] if moving else 0.0
    # when did it leave upright (gz > -0.7)?
    left = next((h["t"] for h in hist if h["gz"] > -0.7), None)
    peak_w = max(h["w"] for h in hist)
    peak_hv = max(h["hv"] for h in hist)
    head_lo = min(h["head_z"] for h in hist)
    nets = [n for i, n in enumerate([h["net"] for h in hist]) if i == 0 or hist[i - 1]["net"] != n]
    # the head-trunk gap: before the torque cut (the head choreography) and during the fall
    cut = next((h["t"] for h in hist if h["net"] in ("relax", "soften")), None)
    before = [h for h in hist if cut is None or h["t"] < cut]
    after = [h for h in hist if cut is not None and h["t"] >= cut]
    gap_before = min(h["gap"] for h in before) if before else None
    gap_after = min(h["gap"] for h in after) if after else None
    at_cut = next((h for h in hist if cut is not None and h["t"] >= cut), hist[-1])
    # the init ramp (if any): trunk rotation / head speed during it, head straightness at the end
    init_at = getattr(fn, "init_at", None)
    ramp_rows = [h for h in hist if init_at is not None and h["t"] >= init_at]
    ramp_w = round(max(h["w"] for h in ramp_rows), 2) if ramp_rows else None
    ramp_hv = round(max(h["hv"] for h in ramp_rows), 2) if ramp_rows else None
    row = dict(recipe=name, end=classify(g_end), g_end=[round(v, 2) for v in g_end], left_upright_at=left, rest_at=rest,
               peak_trunk_w_rad_s=round(peak_w, 2), peak_head_speed_m_s=round(peak_hv, 2), head_z_min=round(head_lo, 3),
               trunk_z_end=round(hist[-1]["z"], 3), x_end=round(hist[-1]["x"], 3), nets=nets[:8],
               cut_at=cut, gap_before_cut_mm=None if gap_before is None else round(gap_before * 1000, 1),
               gap_after_cut_mm=None if gap_after is None else round(gap_after * 1000, 1),
               joints_at_cut=dict(yaw=round(at_cut["yaw_j"], 2), pitch=round(at_cut["pitch_j"], 2), neck=round(at_cut["neck_j"], 2)),
               init_at=init_at, init_peak_trunk_w=ramp_w, init_peak_head_v=ramp_hv,
               joints_end=dict(yaw=round(hist[-1]["yaw_j"], 2), pitch=round(hist[-1]["pitch_j"], 2), neck=round(hist[-1]["neck_j"], 2)),
               end_pos=[round(hist[-1]["x"], 3), round(hist[-1]["z"], 3)])
    print(f"{name:38s} end={row['end']:12s} leaves upright @{left}  rest @{rest:.2f}  peak w {peak_w:.2f}  head v {peak_hv:.2f}  "
          f"gap before/after cut {row['gap_before_cut_mm']}/{row['gap_after_cut_mm']} mm  joints@cut {row['joints_at_cut']}  "
          f"init w/hv {ramp_w}/{ramp_hv} joints@end {row['joints_end']}  nets {nets[:7]}", flush=True)
    return row


if __name__ == "__main__":
    only = sys.argv[1:]
    rows = []
    for name, fn in RECIPES.items():
        if only and not any(o in name for o in only):
            continue
        rows.append(run(name, fn, total=8.0 if getattr(fn, "init_at", None) else 7.0))
    json.dump(rows, open(HERE / "probe.json", "w"), indent=1)
    print("wrote", HERE / "probe.json")
