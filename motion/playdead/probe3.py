#!/usr/bin/env python
"""PLAY DEAD v3 probe: from the v2 start (sit at 0, head yaw 1.0 over 0-0.5 s, head back -1.0 over 0.4-1.0 s), at t_cut the
runtime's `robot.pose_joints` takes over: the head servos lose their torque, the legs are driven to a dead pose. No video:
a table (printed, and the v3 rows merged into probe.json).

    /Users/remi/microduck/.venv-mjlab/bin/python probe3.py [SUBSTR ...]
"""
import json, sys
from pathlib import Path

import mujoco, numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "episode3")); sys.path.insert(0, str(HERE))
import lib, duckfilm as F
from pdduck3 import PDDuck3, JOINTS, HEAD3, HEAD4


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

ZERO = [0.0] * 14
def legs(left_hip_pitch, knee, ankle, hip_roll=0.0):
    """A leg pose: hips / knees / ankles mirrored left-right (the right leg's signs are the left's negated in HOME)."""
    t = [None] * 14
    L = dict(left_hip_yaw=0.0, left_hip_roll=hip_roll, left_hip_pitch=left_hip_pitch, left_knee=knee, left_ankle=ankle,
             right_hip_yaw=0.0, right_hip_roll=-hip_roll, right_hip_pitch=-left_hip_pitch, right_knee=-knee, right_ankle=-ankle)
    for n, v in L.items():
        t[JOINTS.index(n)] = v
    return t
def with_head(t, roll=None):
    t = list(t)
    for n in HEAD4:
        t[JOINTS.index(n)] = None
    if roll is not None:
        t[JOINTS.index("head_roll")] = roll
    return t
HOME_LEGS = with_head(list(F.HOME))
SEATED = None   # filled by the first run (the seat's leg angles just before the cut)


def head_fn(t):
    return dict(head_yaw=1.0 * lib.ramp(t, 0.5), head_pitch=-0.5 * lib.pulse(t, 0.0, 0.12, 0.13, 0.30) - 1.0 * lib.ramp(t - 0.4, 0.6),
                skill="sit", twist=(0.0, 0.0, 0.0))


def run(name, cut, ramp_s, gain, targets, off, total=7.0, stage2=None):
    global SEATED
    m, d = F.build_scene(lib.SIZE, reachy_at=None)
    du = PDDuck3(m, d, "duck_"); du.make_bam(); du.spawn(0, 0, 0); mujoco.mj_forward(m, d); du.bam.last_ts = d.time
    tg = SEATED if targets == "seated" else targets
    du.set_pose_joints(cut, tg if tg is not None else ZERO, off, gain, ramp_s)
    if stage2:
        du.stage2 = stage2
    mo = lib.Motion(name, name, total, head_fn)
    n_pre, n = int(round(lib.PREROLL / F.CDT)), int(round(total / F.CDT))
    hist, prev_head, seated_q = [], None, None
    ankle_l = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "duck_ankle_left")
    ankle_r = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "duck_ankle_right")
    for k in range(-n_pre, n):
        t = k * F.CDT
        h = lib.sample(mo, t)
        du.head[:] = (h["neck"], h["head_pitch"], h["head_yaw"], h["head_roll"])
        du.body[:] = 0; du.twist[:] = h["twist"]; du.skill = h["skill"]
        if abs(t - (cut - F.CDT)) < 1e-6 and SEATED is None:
            q = du.q(); SEATED = with_head([float(v) for v in q])
        lib.step(m, d, du, t + lib.PREROLL)
        if k < 0:
            continue
        g = du.grav(); hp = du.head_pos()
        w = float(np.linalg.norm(d.qvel[du.fv + 3:du.fv + 6]))
        hv = 0.0 if prev_head is None else float(np.linalg.norm(hp - prev_head) / F.CDT)
        prev_head = hp
        q = du.q()
        hist.append(dict(t=round(t, 2), g=[float(v) for v in g], z=float(du.pos()[2]), head_z=float(hp[2]), w=w, hv=hv, net=du.net,
                         x=float(du.pos()[0]), gap=float(du.head_trunk_gap()) if k % 2 == 0 else (hist[-1]["gap"] if hist else 1.0),
                         yaw_j=float(q[7] - F.HOME[7]), pitch_j=float(q[6] - F.HOME[6]), neck_j=float(q[5] - F.HOME[5]), roll_j=float(q[8]),
                         feet_z=[float(d.xpos[ankle_l][2]), float(d.xpos[ankle_r][2])]))
    g_end = hist[-1]["g"]
    moving = [h["t"] for h in hist if h["w"] > 0.3]
    rest = moving[-1] if moving else 0.0
    left = next((h["t"] for h in hist if h["g"][2] > -0.7), None)
    after = [h for h in hist if h["t"] >= cut]
    before = [h for h in hist if h["t"] < cut]
    pitch_end = float(np.degrees(np.arctan2(-g_end[0], -g_end[2])))
    row = dict(recipe=name, cut=cut, ramp_s=ramp_s, gain=gain, off=off, end=classify(g_end), trunk_pitch_end_deg=round(pitch_end, 0),
               left_upright_at=left, rest_at=rest, peak_trunk_w_rad_s=round(max(h["w"] for h in after), 2),
               peak_head_speed_m_s=round(max(h["hv"] for h in after), 2), head_z_min=round(min(h["head_z"] for h in hist), 3),
               gap_before_cut_mm=round(min(h["gap"] for h in before) * 1000, 1), gap_after_cut_mm=round(min(h["gap"] for h in after) * 1000, 1),
               head_end=dict(yaw=round(hist[-1]["yaw_j"], 2), pitch=round(hist[-1]["pitch_j"], 2), neck=round(hist[-1]["neck_j"], 2), roll=round(hist[-1]["roll_j"], 2)),
               feet_z_end_cm=[round(v * 100, 1) for v in hist[-1]["feet_z"]], trunk_z_end_cm=round(hist[-1]["z"] * 100, 1),
               legs_end=du.leg_q(), x_end=round(hist[-1]["x"], 3), nets=[n for i, n in enumerate([h["net"] for h in hist]) if i == 0 or hist[i - 1]["net"] != n][:6])
    print(f"{name:34s} {row['end']:9s} pitch {row['trunk_pitch_end_deg']:+.0f}  leaves @{left}  rest @{rest:.2f}  w {row['peak_trunk_w_rad_s']}  hv {row['peak_head_speed_m_s']}  "
          f"head_z {row['head_z_min']}  gap {row['gap_before_cut_mm']}/{row['gap_after_cut_mm']}  head_end {row['head_end']}  feet_z {row['feet_z_end_cm']} trunk_z {row['trunk_z_end_cm']}", flush=True)
    return row


RECIPES = {}
for cut in (1.2, 1.4, 1.7):
    for rs in (0.5, 1.0, 1.5):
        RECIPES[f"v3_zero_cut{cut}_ramp{rs}_g160"] = dict(cut=cut, ramp_s=rs, gain=160, targets=with_head(ZERO), off=HEAD3)
RECIPES["v3_zero_cut1.4_ramp1.0_g100"] = dict(cut=1.4, ramp_s=1.0, gain=100, targets=with_head(ZERO), off=HEAD3)
RECIPES["v3_zero_cut1.4_ramp1.0_g200"] = dict(cut=1.4, ramp_s=1.0, gain=200, targets=with_head(ZERO), off=HEAD3)
RECIPES["v3_zero_cut1.4_ramp1.0_g160_off4"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(ZERO), off=HEAD4)
RECIPES["v3_seated_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets="seated", off=HEAD3)
RECIPES["v3_home_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=HOME_LEGS, off=HEAD3)
RECIPES["v3_legsupA_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(legs(-1.0, 1.5, 0.0)), off=HEAD3)
RECIPES["v3_legsupB_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(legs(1.0, -1.5, 0.0)), off=HEAD3)
RECIPES["v3_legsupC_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(legs(-1.2, 0.0, 0.0)), off=HEAD3)
RECIPES["v3_legsupD_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(legs(1.2, 0.0, 0.0)), off=HEAD3)
RECIPES["v3_legsupA_cut1.4_ramp1.5_g160"] = dict(cut=1.4, ramp_s=1.5, gain=160, targets=with_head(legs(-1.0, 1.5, 0.0)), off=HEAD3)
RECIPES["v3_legsupA_cut1.7_ramp1.5_g160"] = dict(cut=1.7, ramp_s=1.5, gain=160, targets=with_head(legs(-1.0, 1.5, 0.0)), off=HEAD3)
RECIPES["v3_legsupE_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(legs(-0.8, 1.2, 0.3)), off=HEAD3)
RECIPES["v3_legsupF_cut1.4_ramp1.0_g160"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(legs(-1.3, 1.5, -0.3)), off=HEAD3)
RECIPES["v3_two_zero1.4_then_legsupA3.2"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(ZERO), off=HEAD3, stage2=(3.2, with_head(legs(-1.0, 1.5, 0.0)), 1.0), total=8.0)
RECIPES["v3_two_zero1.4r1.5_then_legsupA3.6"] = dict(cut=1.4, ramp_s=1.5, gain=160, targets=with_head(ZERO), off=HEAD3, stage2=(3.6, with_head(legs(-1.0, 1.5, 0.0)), 1.0), total=8.0)
RECIPES["v3_two_zero1.4_then_legsupE3.2"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(ZERO), off=HEAD3, stage2=(3.2, with_head(legs(-0.8, 1.2, 0.3)), 1.0), total=8.0)
RECIPES["v3_zero_cut1.4_ramp1.0_g160_headrollhold"] = dict(cut=1.4, ramp_s=1.0, gain=160, targets=with_head(ZERO, roll=0.0), off=HEAD3)

if __name__ == "__main__":
    only = sys.argv[1:]
    rows = []
    # the seated leg angles come from the first run (measured just before the cut)
    for name, kw in RECIPES.items():
        if only and not any(o in name for o in only):
            continue
        rows.append(run(name, **kw))
    print("seated leg angles (just before the cut):", {n: round(SEATED[JOINTS.index(n)], 3) for n in JOINTS if SEATED and "head" not in n and "neck" not in n})
    done = {r["recipe"] for r in rows}
    old = [r for r in json.load(open(HERE / "probe.json")) if r["recipe"] not in done] if (HERE / "probe.json").exists() else []
    json.dump(old + rows, open(HERE / "probe.json", "w"), indent=1)
    old3 = json.load(open(HERE / "probe3.json"))["rows"] if (HERE / "probe3.json").exists() else []
    old3 = [r for r in old3 if r["recipe"] not in done]
    json.dump(dict(seated=SEATED, rows=old3 + rows), open(HERE / "probe3.json", "w"), indent=1)
    print("wrote probe.json / probe3.json")
