#!/usr/bin/env python
"""Can Microduck fake an ANGRY FOOT STOMP with the policies it already has (no training)?

Every candidate is a timeline of what a robotd client could send (twist / head deltas / body pose /
a skill trigger), run on the CPU proxy with the training-matched servo model: BAM XL330, 1.75 A
firmware limit, 15-30 ms actuator delay, 1-tick joint-velocity lag (the `duck-hop` flags).

    cd /Users/remi/microduck && PYTHONPATH=microduck_rl/src .venv-mjlab/bin/python \
        notes/emotions/motion/anger-programmatic/stomp_probe.py [--only NAME ...] [--no-video]

Outputs (this folder): <name>.mp4, <name>_sheet.png, <name>.json, results.json.
"""
import argparse, json, math, sys
from collections import deque
from pathlib import Path

import numpy as np, mujoco, onnxruntime as ort, imageio
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/Users/remi/microduck/notes/tools")
import duck_rollout as R

HERE = Path(__file__).resolve().parent
WS = Path("/Users/remi/microduck")
POLICIES = {
    "stand": WS / "microduck/policies/alpha_stand.onnx",
    "walk": WS / "microduck/policies/alpha_walking.onnx",
    "sitstand": WS / "microduck/policies/alpha_sitstand.onnx",
    "kick_left": WS / "microduck/policies/ball_kick_left.onnx",
    "kick_right": WS / "microduck/policies/ball_kick_right.onnx",
    "flamingo": WS / "notes/policies/flamingo_cycle_r2.onnx",
    "hop": WS / "notes/policies/happy-hop/policy.onnx",
}
KP = {"walk": 200.0, "flamingo": 200.0, "hop": 200.0}          # robotd: gain 200, standing ratio 0.8 -> 160 for stand / kick / rise
KP_DEFAULT = 160.0
DEC = R.DECIMATION
CDT = 0.02
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
YAW_LEFT, YAW_RIGHT = +1.0, -1.0       # head_yaw hinge axis is +z: positive = counter-clockwise from above = the robot's LEFT


def cmd(twist=(0, 0, 0), head=(0, 0, 0, 0), body=(0, 0, 0, 0, 0, 0)):
    c = np.zeros(13, np.float32)
    c[0:3] = twist; c[3:7] = head; c[7:13] = body
    return c


def between(t, a, b):
    return a <= t < b


# ----------------------------------------------------------------------------------------------------------------
# The candidates. plan(t) -> (net, command13). Each also names the stomping foot and the "events" (t_lift, label)
# used for the per-stomp metrics.
# ----------------------------------------------------------------------------------------------------------------
def flamingo_plan(lift_s, hold_s, gap_s, head_on_flamingo=True, side=+1):
    """Flamingo cycle: flag up (lift the LEFT foot when side=+1) for hold_s, then flag down (= foot comes down)
    with a head yaw. Twice, same foot. head_on_flamingo: send the yaw to the flamingo net (its head slots were
    zero in training, so it may ignore them)."""
    t1, t2 = lift_s, lift_s + hold_s + gap_s
    def plan(t):
        flag = 1.0 if (between(t, t1, t1 + hold_s) or between(t, t2, t2 + hold_s)) else 0.0
        yaw = 0.0
        if between(t, t1 + hold_s, t2): yaw = YAW_LEFT
        elif between(t, t2 + hold_s, t2 + hold_s + 2.0): yaw = YAW_RIGHT
        head = (0, 0, yaw, 0) if head_on_flamingo else (0, 0, 0, 0)
        return "flamingo", cmd((flag, side, 0), head)
    events = [(t1 + hold_s, "stomp 1 (head left)", 1.6), (t2 + hold_s, "stomp 2 (head right)", 1.6)]
    return plan, events, ("left" if side > 0 else "right"), t2 + hold_s + 3.0


def flamingo_switch_plan(lift_s, hold_s, gap_s, side=+1, pitch=0.0, yaw_after=(YAW_LEFT, YAW_RIGHT)):
    """Flamingo lifts the foot, then the client zeroes the twist: robotd picks the STAND net (|twist| <= 0.3),
    which slams the foot back to HOME while tracking the head yaw. On the robot: walk = flamingo, stand = alpha_stand."""
    t1, t2 = lift_s, lift_s + hold_s + gap_s
    def plan(t):
        if between(t, t1, t1 + hold_s) or between(t, t2, t2 + hold_s):
            return "flamingo", cmd((1, side, 0))
        if t < t1 or between(t, t2 - 0.6, t2):          # settle on the flamingo net at flag 0 before the lift
            return "flamingo", cmd((0, side, 0))
        yaw = yaw_after[0] if t < t2 else (yaw_after[1] if t < t2 + hold_s + 2.0 else 0.0)
        body = (0, 0, pitch if (t < t1 + hold_s + 0.6 or between(t, t2 + hold_s, t2 + hold_s + 0.6)) else 0.0, 0, 0, 0)
        return "stand", cmd((0, 0, 0), (0, 0, yaw, 0), body)
    events = [(t1 + hold_s, "stomp 1 (head left)", 1.6), (t2 + hold_s, "stomp 2 (head right)", 1.6)]
    return plan, events, ("left" if side > 0 else "right"), t2 + hold_s + 3.0


def kick_plan(window_s, foot="left", gap_s=2.5, t_first=1.0, base="stand"):
    """robot.do kick_left twice from the standing net; the head yaw is sent to the standing net between kicks
    (the kick nets were trained with every command slot at zero, robotd sends them zeros)."""
    net = f"kick_{foot}"
    t1, t2 = t_first, t_first + window_s + gap_s
    def plan(t):
        if between(t, t1, t1 + window_s) or between(t, t2, t2 + window_s):
            return net, cmd()
        yaw = YAW_LEFT if between(t, t1 + window_s, t2) else (YAW_RIGHT if between(t, t2 + window_s, t2 + window_s + 2.0) else 0.0)
        return base, cmd((0, 0, 0), (0, 0, yaw, 0))
    events = [(t1, "kick 1 (head left after)"), (t2, "kick 2 (head right after)")]
    return plan, events, foot, t2 + window_s + 3.0


def kick_recentre_plan(window_s=0.4, foot="left", yaw_s=0.9, centre_s=0.6, t_first=1.0, yaw_amp=1.0, foot2=None, head=True):
    """kick (window_s) -> head yaw LEFT for yaw_s -> head back to centre for centre_s -> kick again -> head yaw RIGHT
    -> centre. The kick net needs the head at HOME to kick (B1: it spends its window re-centring a yawed head)."""
    net = f"kick_{foot}"; net2 = f"kick_{foot2 or foot}"
    t1 = t_first
    t2 = t1 + window_s + yaw_s + centre_s
    end = t2 + window_s + yaw_s + centre_s
    def plan(t):
        if between(t, t1, t1 + window_s): return net, cmd()
        if between(t, t2, t2 + window_s): return net2, cmd()
        yaw = 0.0
        if not head: return "stand", cmd()
        if between(t, t1 + window_s, t1 + window_s + yaw_s): yaw = yaw_amp * YAW_LEFT
        elif between(t, t2 + window_s, t2 + window_s + yaw_s): yaw = yaw_amp * YAW_RIGHT
        return "stand", cmd((0, 0, 0), (0, 0, yaw, 0))
    events = [(t1, "kick 1 (head left after)"), (t2, "kick 2 (head right after)")]
    return plan, events, ("auto" if foot2 and foot2 != foot else foot), end + 2.0


def walk_pulse_plan(twist, pulse_s, gap_s=2.5, t_first=1.0, lean=0.0):
    """Walking net: a short twist pulse to trigger a step, then zero twist -> standing net with the head yaw
    (and an optional body-pitch lean = bow, on the standing net just before the pulse)."""
    t1, t2 = t_first, t_first + pulse_s + gap_s
    def plan(t):
        if between(t, t1, t1 + pulse_s) or between(t, t2, t2 + pulse_s):
            return "walk", cmd(twist)
        yaw = YAW_LEFT if between(t, t1 + pulse_s, t2) else (YAW_RIGHT if between(t, t2 + pulse_s, t2 + pulse_s + 2.0) else 0.0)
        body = (0, 0, lean, 0, 0, 0) if (between(t, t1 - 0.5, t1) or between(t, t2 - 0.5, t2)) else (0,) * 6
        return "stand", cmd((0, 0, 0), (0, 0, yaw, 0), body)
    events = [(t1, "pulse 1 (head left after)"), (t2, "pulse 2 (head right after)")]
    return plan, events, "auto", t2 + pulse_s + 3.0


def hop_plan(t_first=1.0, gap_s=2.5, window_s=3.0):
    """Happy-hop one-shot twice (both feet leave the floor: an angry two-foot jump), head yaw between."""
    t1, t2 = t_first, t_first + window_s + gap_s
    def plan(t):
        if between(t, t1, t1 + window_s) or between(t, t2, t2 + window_s):
            return "hop", cmd()
        yaw = YAW_LEFT if between(t, t1 + window_s, t2) else (YAW_RIGHT if between(t, t2 + window_s, t2 + window_s + 2.0) else 0.0)
        return "stand", cmd((0, 0, 0), (0, 0, yaw, 0))
    events = [(t1, "hop 1"), (t2, "hop 2")]
    return plan, events, "auto", t2 + window_s + 3.0


def body_pulse_plan(body_vec, pulse_s=0.3, gap_s=2.0, t_first=1.0):
    """Standing net body-pose pulse (z drop = bounce, roll = weight shift) with the head yaw at the same time."""
    t1, t2 = t_first, t_first + pulse_s + gap_s
    def plan(t):
        body = body_vec if (between(t, t1, t1 + pulse_s) or between(t, t2, t2 + pulse_s)) else (0,) * 6
        yaw = YAW_LEFT if between(t, t1, t2) else (YAW_RIGHT if between(t, t2, t2 + pulse_s + 2.0) else 0.0)
        return "stand", cmd((0, 0, 0), (0, 0, yaw, 0), body)
    events = [(t1, "pulse 1 (head left)"), (t2, "pulse 2 (head right)")]
    return plan, events, "auto", t2 + pulse_s + 3.0


CANDIDATES = {
    # (1) flamingo cycle: lift with the flag, drop the flag, head yaw through the head slots of the flamingo net
    "A1_flamingo_lift_drop":      ("Flamingo r2: flag up 1.5 s, flag down (foot lowers), head yaw sent to the flamingo net; twice, left foot", flamingo_plan(1.0, 1.5, 1.5)),
    "A2_flamingo_short_lift":     ("Flamingo r2: flag up only 0.7 s (interrupt the lift early), twice, left foot", flamingo_plan(1.0, 0.7, 1.8)),
    # (1b) flamingo lift, then a hard switch to the standing net (zero twist) which pulls the foot back to HOME and tracks the head
    "A3_flamingo_then_stand":     ("Flamingo lifts the left foot 1.2 s, then twist=0 -> standing net takes over (foot pulled to HOME) + head yaw", flamingo_switch_plan(1.0, 1.2, 1.5)),
    "A4_flamingo_then_stand_bow": ("Same as A3 with a body-pitch bow (0.25) on the standing net during the drop", flamingo_switch_plan(1.0, 1.2, 1.5, pitch=0.25)),
    # (2) the shipped kick skill
    "B1_kick_left_robotd":        ("ball_kick_left, robotd kick window 0.5 s, twice, head yaw on the standing net after each", kick_plan(0.5)),
    "B2_kick_left_full":          ("ball_kick_left, full 3 s window (infer_policy.py style), twice, head yaw after each", kick_plan(3.0)),
    "B3_kick_left_1s":            ("ball_kick_left, 1.0 s window, twice, head yaw after each", kick_plan(1.0)),
    "B4_kick_recentre_0.4s":      ("ball_kick_left, 0.4 s window, head LEFT 0.9 s, head back to centre 0.6 s, kick again, head RIGHT, centre (2.0 s between kicks)", kick_recentre_plan(0.4)),
    "B5_kick_recentre_fast":      ("Same as B4 but faster: head yaw 0.6 s, centre 0.4 s (1.4 s between kicks)", kick_recentre_plan(0.4, yaw_s=0.6, centre_s=0.4)),
    "B6_kick_recentre_right":     ("B4 with the RIGHT foot (ball_kick_right), head left then right", kick_recentre_plan(0.4, foot="right")),
    "B7_kick_recentre_yaw0.6":    ("B4 with a smaller head yaw (0.6 rad = 34 deg) so the recentre is quicker", kick_recentre_plan(0.4, yaw_amp=0.6)),
    "A6_flamingo_mirror_then_stand":("A5 mirrored: RIGHT foot lifted 1.8 s (the flamingo swings the head LEFT by itself), twist=0 -> standing net slams it down and snaps the head RIGHT; twice", flamingo_switch_plan(1.0, 1.8, 1.5, side=-1, yaw_after=(YAW_RIGHT, YAW_RIGHT))),
    "B8_kick_recentre_0.5s_robotd":("B5 timing with robotd's default 0.5 s kick window (no robotd.toml change): kick, head LEFT 0.6 s, centre 0.4 s, kick, head RIGHT, centre", kick_recentre_plan(0.5, yaw_s=0.6, centre_s=0.4)),
    "B9_kick_window_0.3s":        ("B5 with a 0.3 s kick window: the standing net takes over while the foot is still coming down, the head snap starts earlier", kick_recentre_plan(0.3, yaw_s=0.6, centre_s=0.4)),
    "E1_kick_left_x2_nohead_gap1.0": ("kick_left twice, 0.5 s window, NO head command at all, 1.0 s gap", kick_recentre_plan(0.5, yaw_s=0.5, centre_s=0.5, head=False)),
    "E2_kick_left_x2_nohead_gap2.0": ("kick_left twice, 0.5 s window, no head, 2.0 s gap", kick_recentre_plan(0.5, yaw_s=1.0, centre_s=1.0, head=False)),
    "E3_kick_left_x2_nohead_gap3.0": ("kick_left twice, 0.5 s window, no head, 3.0 s gap", kick_recentre_plan(0.5, yaw_s=1.5, centre_s=1.5, head=False)),
    "E4_kick_left_x2_head_gap2.0":   ("B8 head timeline but 2.0 s between kicks (head left 0.6 s, centre 1.4 s)", kick_recentre_plan(0.5, yaw_s=0.6, centre_s=1.4)),
    "E5_kick_left_x2_head_gap3.0":   ("B8 head timeline but 3.0 s between kicks (head left 0.6 s, centre 2.4 s)", kick_recentre_plan(0.5, yaw_s=0.6, centre_s=2.4)),
    "E6_kick_left_then_right":       ("kick_left then kick_right, 0.5 s window, B8 head timing (1.0 s gap)", kick_recentre_plan(0.5, yaw_s=0.6, centre_s=0.4, foot2="right")),
    "E7_kick_right_x2_nohead":       ("kick_right twice, 0.5 s window, no head, 1.0 s gap", kick_recentre_plan(0.5, foot="right", yaw_s=0.5, centre_s=0.5, head=False)),
    "E8_kick_left_x2_nohead_win0.3": ("kick_left twice, 0.3 s window, no head, 1.0 s gap", kick_recentre_plan(0.3, yaw_s=0.5, centre_s=0.5, head=False)),
    "A5_flamingo_hold_then_stand":("Flamingo lifts the left foot for 1.8 s (foot at ~7 cm), then twist=0 -> standing net pulls it down + head yaw", flamingo_switch_plan(1.0, 1.8, 1.5)),
    # (3) walking-policy tricks: a twist pulse to trigger a single step
    "C1_walk_fwd_pulse":          ("alpha_walking: vx=+0.4 for 0.3 s, twice, head yaw on the standing net after", walk_pulse_plan((0.4, 0, 0), 0.3)),
    "C2_walk_turn_pulse":         ("alpha_walking: wz=+1.5 for 0.3 s (turn step), twice, head yaw after", walk_pulse_plan((0, 0, 1.5), 0.3)),
    "C3_walk_back_pulse_bow":     ("alpha_walking: (-0.35,0,0.22) backward pulse 0.3 s with a 0.25 bow before it, twice", walk_pulse_plan((-0.35, 0, 0.22), 0.3, lean=0.25)),
    "C4_walk_side_pulse":         ("alpha_walking: vy=+0.3 for 0.3 s (side step), twice, head yaw after", walk_pulse_plan((0, 0.3, 0), 0.3)),
    "C5_walk_fwd_pulse_strong":   ("alpha_walking: vx=+0.6 for 0.4 s (stronger step), twice, head yaw after", walk_pulse_plan((0.6, 0, 0), 0.4)),
    # (4) anything else cheap
    "D1_hop_twice":               ("happy-hop one-shot twice (both feet: an angry jump), head yaw between", hop_plan()),
    "D2_stand_bounce":            ("alpha_stand: body z -0.03 pulse 0.3 s (crouch-bounce, both feet stay) + head yaw", body_pulse_plan((-0.03, 0, 0, 0, 0, 0))),
    "D3_stand_roll_shift":        ("alpha_stand: body roll +0.2 pulse 0.3 s (weight shift, does a foot unload?) + head yaw", body_pulse_plan((0, 0.2, 0, 0, 0, 0))),
}


# ----------------------------------------------------------------------------------------------------------------
def run(name, desc, plan, events, stomp_foot, duration, video=True, azimuth=200.0, seed=0):
    R.BAM_SPEC_EDITS = True
    model = R.proxy_model("scene_walk.xml")
    data = mujoco.MjData(model)
    bam = R.make_bam(model, data, current_limit=1.75)
    sess = {k: ort.InferenceSession(str(p)) for k, p in POLICIES.items()}
    iname = {k: s.get_inputs()[0].name for k, s in sess.items()}
    n = model.nu
    trunk = R.nid(model, mujoco.mjtObj.mjOBJ_BODY, "trunk_base")
    gyro_adr = int(model.sensor_adr[R.nid(model, mujoco.mjtObj.mjOBJ_SENSOR, "imu_ang_vel")])
    qpos_idx = [int(model.jnt_qposadr[model.actuator_trnid[i, 0]]) for i in range(n)]
    qvel_idx = [int(model.jnt_dofadr[model.actuator_trnid[i, 0]]) for i in range(n)]
    fj = R.free_joint(model); fa = model.jnt_qposadr[fj]
    feet = [R.nid(model, mujoco.mjtObj.mjOBJ_GEOM, f"{s}_foot_collision") for s in ("left", "right")]
    foot_sites = [R.nid(model, mujoco.mjtObj.mjOBJ_SITE, f"{s}_foot") for s in ("left", "right")]
    floor = R.floor_geom(model)
    mujoco.mj_resetData(model, data)
    data.qpos[fa:fa + 3] = [0, 0, 0.125]; data.qpos[fa + 3:fa + 7] = [1, 0, 0, 0]
    data.qpos[qpos_idx] = R.DEFAULT_POSE[:n]; data.ctrl[:] = R.DEFAULT_POSE[:n]
    mujoco.mj_forward(model, data)
    bam.reset(data.qpos); bam.last_ts = data.time
    # training-matched delay (3-6 physics steps) and joint-vel lag (1 tick), as in duck_rollout
    dmin, dmax = 3, 6; drng = np.random.default_rng(seed + 1)
    tbuf = deque([R.DEFAULT_POSE[:n].copy()] * (dmax + 1), maxlen=dmax + 1)
    jvel_hist = deque([np.zeros(n, np.float32)] * 2, maxlen=2)
    last_action = np.zeros(n, np.float32); g = np.array([0, 0, -1], np.float32)
    ticks = int(duration / CDT)
    cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING; cam.trackbodyid = trunk
    cam.distance = 0.62; cam.elevation = -12; cam.azimuth = azimuth
    renderer = mujoco.Renderer(model, height=480, width=640) if video else None
    frames, ftimes, log = [], [], []
    prev_net = None
    for k in range(ticks):
        t = k * CDT
        net, c = plan(t)
        if net != prev_net:
            bam.model.actuator.kp = KP.get(net, KP_DEFAULT)
            prev_net = net
        gyro = data.sensordata[gyro_adr:gyro_adr + 3].astype(np.float32)
        grav = R.qrotinv(data.xquat[trunk].astype(np.float32), g)
        jpos = data.qpos[qpos_idx].astype(np.float32) - R.DEFAULT_POSE[:n]
        jvel_hist.append(data.qvel[qvel_idx].astype(np.float32)); jvel = jvel_hist[0]
        obs = np.concatenate([gyro, grav, jpos, jvel, last_action, c])[None].astype(np.float32)
        act = sess[net].run(None, {iname[net]: obs})[0].reshape(-1).astype(np.float32)
        last_action = act
        target = R.DEFAULT_POSE[:n] + act
        lag = int(drng.integers(dmin, dmax + 1))
        for _ in range(DEC):
            tbuf.append(target); tgt = tbuf[-1 - lag]
            bam.q_target[:] = tgt; bam.update()
            mujoco.mj_step(model, data)
        contact = [0, 0]
        for cc in data.contact[:data.ncon]:
            for i, fg in enumerate(feet):
                if (cc.geom1 == fg and cc.geom2 == floor) or (cc.geom2 == fg and cc.geom1 == floor): contact[i] = 1
        q = data.qpos[qpos_idx]
        log.append(dict(t=round(t, 3), net=net, z=float(data.xpos[trunk][2]), x=float(data.xpos[trunk][0]), y=float(data.xpos[trunk][1]),
                        tilt=float(np.hypot(grav[0], grav[1])), gz=float(grav[2]), lf=contact[0], rf=contact[1],
                        lz=float(data.site_xpos[foot_sites[0]][2]), rz=float(data.site_xpos[foot_sites[1]][2]),
                        yaw=float(q[7]), neck=float(q[5]), hpitch=float(q[6]), amax=float(np.abs(act).max()),
                        jv=float(np.abs(data.qvel[qvel_idx]).max()), cmd=[round(float(v), 2) for v in c]))
        if renderer and k % 2 == 0:
            renderer.update_scene(data, camera=cam)
            img = Image.fromarray(renderer.render()); d = ImageDraw.Draw(img)
            f = ImageFont.truetype(FONT, 18)
            hd = c[3:7]
            d.text((8, 6), f"{name}  t={t:4.1f}s  net={net}", font=f, fill="white", stroke_width=2, stroke_fill="black")
            d.text((8, 28), f"twist {c[0]:+.2f},{c[1]:+.2f},{c[2]:+.2f}  head yaw cmd {hd[2]:+.1f}  meas {math.degrees(q[7]):+4.0f} deg", font=f, fill="white", stroke_width=2, stroke_fill="black")
            frames.append(np.asarray(img)); ftimes.append(t)
    if renderer:
        renderer.close()
        imageio.mimwrite(str(HERE / f"{name}.mp4"), frames, fps=25, codec="libx264", pixelformat="yuv420p",
                         macro_block_size=8, output_params=["-crf", "20", "-movflags", "+faststart"])
    stats = metrics(log, events, stomp_foot)
    stats.update(name=name, description=desc, duration_s=duration)
    json.dump(dict(stats=stats, log=log), open(HERE / f"{name}.json", "w"))
    if frames:
        contact_sheet(name, desc, frames, ftimes, events, stats)
    return stats


def scan_lifts(log, thresh_mm=20.0, land_mm=6.0):
    """Raw-log truth: every genuine foot lift = a foot rising above thresh_mm, until it is back under land_mm.
    Independent of the plan's events. Returns [(foot, t_start, t_peak, peak_mm, t_land, down_m_s)]."""
    t = np.array([l["t"] for l in log])
    settled = (t >= 0.5) & (t < 0.9)
    out = []
    for foot, key in (("left", "lz"), ("right", "rz")):
        z = (np.array([l[key] for l in log]) - np.array([l[key] for l in log])[settled].mean()) * 1000
        vz = np.gradient(z / 1000, t)
        i = 0
        while i < len(z):
            if z[i] > thresh_mm:
                a = i
                while a > 0 and z[a - 1] > land_mm: a -= 1
                b = i
                while b < len(z) - 1 and z[b] > land_mm: b += 1
                ip = a + int(np.argmax(z[a:b + 1]))
                out.append((foot, round(float(t[a]), 2), round(float(t[ip]), 2), round(float(z[ip]), 1), round(float(t[b]), 2),
                            round(float(-vz[ip:b + 1].min()) if b > ip else 0.0, 2)))
                i = b + 1
            else:
                i += 1
    return sorted(out, key=lambda x: x[1])


def metrics(log, events, stomp_foot):
    """Per stomp event: its OWN window = [te - pre, next event's window start), never reaching into the previous
    event. pre = 1.6 s for the flamingo plans (the event is the drop; the lift started earlier), 0 for triggers.
    Reports the foot's peak height in the window, the fastest downward speed before touch-down, time from peak to
    touch-down, other-foot contact fraction, head yaw extremes. `lifted` says whether a genuine lift (> 20 mm)
    happened in that window at all."""
    t = np.array([l["t"] for l in log]); lz = np.array([l["lz"] for l in log]); rz = np.array([l["rz"] for l in log])
    lf = np.array([l["lf"] for l in log]); rf = np.array([l["rf"] for l in log]); yaw = np.array([l["yaw"] for l in log])
    tilt = np.array([l["tilt"] for l in log])
    settled = (t >= 0.5) & (t < 0.9)                       # rest height AFTER the spawn settle (the duck drops ~6 mm at t=0)
    z0 = dict(left=lz[settled].mean(), right=rz[settled].mean())
    lifts = scan_lifts(log)
    out = dict(fell=bool(tilt.max() > 0.7 or log[-1]["gz"] > -0.7), max_tilt_deg=round(math.degrees(math.asin(min(1.0, tilt.max()))), 1),
               final_upright=bool(log[-1]["gz"] < -0.9), max_joint_speed_rad_s=round(float(max(l["jv"] for l in log)), 1),
               mean_abs_action_max=round(float(np.mean([l["amax"] for l in log])), 2), stomps=[],
               lifts=[dict(foot=f, t_start=a, t_peak=p, peak_mm=z, t_land=b, down_m_s=v) for f, a, p, z, b, v in lifts],
               n_lifts=len(lifts))
    ev = [(te, lab, (pre[0] if pre else 0.0)) for te, lab, *pre in events]
    for i, (te, label, pre) in enumerate(ev):
        start = max(te - pre, 0.5)
        end = te + 2.5
        if i + 1 < len(ev):
            end = min(end, max(ev[i + 1][0] - ev[i + 1][2], start + 0.1))
        w = (t >= start) & (t < end)
        if not w.any(): continue
        if stomp_foot == "auto":
            foot = "left" if (lz[w] - z0["left"]).max() >= (rz[w] - z0["right"]).max() else "right"
        else:
            foot = stomp_foot
        fz = (lz if foot == "left" else rz) - z0[foot]
        fc = lf if foot == "left" else rf
        oc = rf if foot == "left" else lf
        idx = np.where(w)[0]
        ip = idx[np.argmax(fz[idx])]
        peak_mm = float(fz[ip] * 1000)
        after = idx[idx > ip]
        land = next((j for j in after if fc[j]), None)
        vz = np.gradient(fz, t)
        seg = np.arange(ip, (land if land is not None else idx[-1]) + 1)
        v_down = float(-vz[seg].min()) if len(seg) > 1 else 0.0
        t_down = float(t[land] - t[ip]) if land is not None else None
        yw = yaw[w]; ext = yw[np.argmax(np.abs(yw))] if len(yw) else 0.0
        in_win = [L for L in lifts if L[0] == foot and start <= L[2] < end]
        out["stomps"].append(dict(label=label, foot=foot, window=[round(start, 2), round(end, 2)], lifted=bool(in_win),
                                  t_peak=round(float(t[ip]), 2), peak_mm=round(peak_mm, 1),
                                  down_speed_m_s=round(v_down, 3), peak_to_land_s=(round(t_down, 2) if t_down is not None else None),
                                  other_foot_planted_frac=round(float(oc[w].mean()), 3),
                                  head_yaw_deg=round(math.degrees(float(ext)), 1),
                                  head_yaw_left_deg=round(math.degrees(float(yw.max())), 1) if len(yw) else 0.0,
                                  head_yaw_right_deg=round(math.degrees(float(yw.min())), 1) if len(yw) else 0.0))
    return out


def contact_sheet(name, desc, frames, ftimes, events, stats, cols=8, rows=2, w=240):
    """rows x cols frames: for each event, `cols` frames 0.2 s apart from 0.2 s before the event (the slam is 0.2-0.4 s in)."""
    h = int(w * frames[0].shape[0] / frames[0].shape[1])
    sheet = Image.new("RGB", (cols * w, rows * h + 40), "black")
    d = ImageDraw.Draw(sheet); f = ImageFont.truetype(FONT, 16)
    lifts = "; ".join(f"{L['foot']} {L['peak_mm']:.0f} mm @ {L['t_peak']} s" for L in stats["lifts"]) or "NO foot lift > 20 mm"
    d.text((8, 4), f"{name}: {desc}", font=f, fill="white")
    d.text((8, 22), f"raw-log lifts ({stats['n_lifts']}): {lifts}   fell={stats['fell']}", font=f, fill="#9f9")
    ft = np.array(ftimes)
    for r, (te, label) in enumerate(events[:rows]):
        times = te - 0.2 + 0.2 * np.arange(cols)
        for cidx, tt in enumerate(times):
            i = int(np.argmin(np.abs(ft - tt)))
            im = Image.fromarray(frames[i]).resize((w, h))
            sheet.paste(im, (cidx * w, 40 + r * h))
    sheet.save(HERE / f"{name}_sheet.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--azimuth", type=float, default=200.0)
    a = ap.parse_args()
    names = a.only or list(CANDIDATES)
    results = json.load(open(HERE / "results.json")) if (HERE / "results.json").exists() else {}
    for nm in names:
        desc, (plan, events, foot, dur) = CANDIDATES[nm]
        print(f"== {nm}: {desc}", flush=True)
        st = run(nm, desc, plan, events, foot, dur, video=not a.no_video, azimuth=a.azimuth)
        results[nm] = st
        for s in st["stomps"]:
            print(f"   {s['label']:28s} {'LIFT ' if s['lifted'] else 'nolift'} win {s['window']} foot {s['foot']:5s} peak {s['peak_mm']:6.1f} mm  down {s['down_speed_m_s']:.2f} m/s  peak->land {s['peak_to_land_s']}  other planted {s['other_foot_planted_frac']:.2f}  head yaw {s['head_yaw_deg']:+.0f} deg")
        print("   RAW LIFTS: " + ("; ".join(f"{L['foot']} {L['peak_mm']:.0f} mm @ {L['t_peak']} s (lands {L['t_land']} s, {L['down_m_s']} m/s)" for L in st["lifts"]) or "none"))
        print(f"   fell={st['fell']} max_tilt={st['max_tilt_deg']} deg  final_upright={st['final_upright']}  max joint speed {st['max_joint_speed_rad_s']} rad/s", flush=True)
        json.dump(results, open(HERE / "results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
