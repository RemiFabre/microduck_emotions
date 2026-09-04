#!/usr/bin/env python
"""SADNESS body motion for Microduck, programmatic, in simulation (no training).

    PY=/Users/remi/microduck/.venv-mjlab/bin/python
    $PY sadness.py probe                 # do the head slots track while SITTING? (and standing, for comparison)
    $PY sadness.py render [name ...]     # one mp4 + contact sheet + keyframe json per candidate, then index.html
    $PY sadness.py index                 # rebuild index.html from the measured json files

The duck is driven ONLY through what the real robot accepts (twist, head deltas, body pose, the sit skill), via
/Users/remi/microduck/notes/reachy-encounter/duckfilm.py. Every candidate is a pure function of time returning
(neck, head_pitch, head_yaw, head_roll, body_pitch, skill), the same shape as padd/src/expressions.rs::head_at,
plus a sit/stand trigger and a body-pose pitch.

Sign conventions (measured on the shipped policies): head_pitch POSITIVE = beak DOWN; neck only tracks downward
(negative command, about half of it); head_yaw +-1; head_roll +-0.27.
"""
import argparse, json, math, subprocess, sys, wave
from pathlib import Path

import imageio, mujoco, numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/Users/remi/microduck/notes/reachy-encounter")
import duckfilm as F

HERE = Path(__file__).resolve().parent
SIZE = (640, 480)
FPS = 30
SOUND_DIR = Path("/Users/remi/microduck/notes/emotions/sounds/sadness")
REF_SAD2 = Path("/Users/remi/microduck/notes/emotions/reference/sad2.wav")
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
NAMES = ["neck_pitch", "head_pitch", "head_yaw", "head_roll"]


def ramp(t, ln):
    """Smooth 0 -> 1 over ln seconds (half cosine), clamped. Same as expressions.rs::ramp."""
    x = min(1.0, max(0.0, t / ln)) if ln > 0 else (1.0 if t >= 0 else 0.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def fresh():
    m, d = F.build_scene(SIZE, reachy_at=None)
    du = F.Duck(m, d, "duck_")
    du.make_bam()
    du.spawn(0.0, 0.0, 0.0)
    mujoco.mj_forward(m, d)
    du.bam.last_ts = d.time
    return m, d, du


def step(m, d, du, t):
    du.control_tick(t)
    for _ in range(F.DECIMATION):
        du.physics_substep()
        mujoco.mj_step(m, d)
    du.after_step(t)


# ---------------------------------------------------------------------------------------------------------------
# 1. probe: do the head command slots track while sitting on the sit-stand net?
# ---------------------------------------------------------------------------------------------------------------
def probe():
    print("== head slots: commanded delta -> measured joint delta (rad), SITTING (sitstand net, posture flag 1) vs STANDING (stand net) ==")
    print("   step sent 3 s after the sit starts (the seat is reached in ~2 s), averaged over the last 0.8 s of a 2 s hold")
    rows = []
    for mode in ("sitting", "standing"):
        for i, nm in enumerate(NAMES):
            row = []
            for amp in (-1.5, -1.0, -0.5, 0.5, 1.0):
                if nm == "head_roll" and abs(amp) > 0.5:
                    continue
                if nm == "head_roll":
                    amp = amp * 0.6      # +-0.3 (its range is 0.27)
                m, d, du = fresh()
                du.limp_fall = False
                meas, zs = [], []
                for k in range(int(6.0 / F.CDT)):
                    t = k * F.CDT
                    du.skill = "sit" if (mode == "sitting" and t > 0.5) else None
                    du.head[:] = 0
                    if t > 3.5:
                        du.head[i] = amp
                    step(m, d, du, t)
                    if t > 4.7:
                        meas.append(du.q()[F.HEAD_IDX[i]] - F.HOME[F.HEAD_IDX[i]])
                        zs.append(du.pos()[2])
                row.append(f"{amp:+.2f}->{np.mean(meas):+.2f}{' FALL' if du.fell_at is not None else ''}")
                rows.append(dict(mode=mode, slot=nm, cmd=amp, measured=round(float(np.mean(meas)), 3), trunk_z=round(float(np.mean(zs)), 3), fell=du.fell_at is not None))
            print(f"  {mode:9s} {nm:11s} " + "  ".join(row))
    # trunk height while sitting, body pitch while sitting and standing
    print("\n== body-pose pitch slot: commanded -> trunk pitch (deg, + = nose down?) and trunk height, sitting vs standing ==")
    for mode in ("sitting", "standing"):
        row = []
        for amp in (-0.3, -0.15, 0.15, 0.3):
            m, d, du = fresh()
            du.limp_fall = False
            meas = []
            for k in range(int(6.0 / F.CDT)):
                t = k * F.CDT
                du.skill = "sit" if (mode == "sitting" and t > 0.5) else None
                du.body[:] = 0
                if t > 3.5:
                    du.body[2] = amp
                step(m, d, du, t)
                if t > 4.7:
                    g = du.grav()
                    meas.append((du.pos()[2], math.degrees(math.atan2(-g[0], -g[2])), du.beak_pos()[2]))
            z, p, bz = np.mean(meas, axis=0)
            row.append(f"{amp:+.2f}->pitch{p:+.0f}deg z{z:.3f} beak_z{bz:.3f}{' FALL' if du.fell_at is not None else ''}")
            rows.append(dict(mode=mode, slot="body_pitch", cmd=amp, trunk_pitch_deg=round(float(p), 1), trunk_z=round(float(z), 3), beak_z=round(float(bz), 3), fell=du.fell_at is not None))
        print(f"  {mode:9s} " + "  ".join(row))
    # how long does the sit take?
    m, d, du = fresh()
    du.limp_fall = False
    zs = []
    for k in range(int(5.0 / F.CDT)):
        t = k * F.CDT
        du.skill = "sit" if t > 0.5 else None
        step(m, d, du, t)
        zs.append((round(t, 2), round(float(du.pos()[2]), 3), round(float(du.beak_pos()[2]), 3)))
    z_end = zs[-1][1]
    settled = next(t for t, z, _ in zs if t > 0.5 and abs(z - z_end) < 0.005)
    print(f"\n== sit timing: trunk z {zs[0][1]:.3f} standing -> {z_end:.3f} seated; within 5 mm of the seat {settled - 0.5:.2f} s after the sit command; beak z standing {zs[0][2]:.3f} seated {zs[-1][2]:.3f}")
    rows.append(dict(mode="sit_timing", trunk_z_stand=zs[0][1], trunk_z_seat=z_end, settle_s=round(settled - 0.5, 2), beak_z_stand=zs[0][2], beak_z_seat=zs[-1][2]))
    json.dump(rows, open(HERE / "probe.json", "w"), indent=1)
    print("wrote", HERE / "probe.json")


# ---------------------------------------------------------------------------------------------------------------
# 2. the candidates: pure functions of time -> dict(neck, head_pitch, head_yaw, head_roll, body_pitch, skill)
#    skill: "sit" while the sit-stand net must hold the seat, "stand" while it rises, None otherwise.
# ---------------------------------------------------------------------------------------------------------------
NECK_CMD = -1.5        # tracks to about -0.85 rad (the neck only follows downward, about half the command)
PITCH_DOWN = 1.0       # head_pitch, positive = beak down (seated, the sitstand net trades it against the neck: ~+0.6 rad reached with neck -1.5)
YAW_AMP = 0.4          # the slow "no" shake, rad (+-23 deg; Reachy sad2 uses +-8 deg on a much bigger head)


def _droop_shake(t, sit_start, sit_len, droop_len, shake_n, shake_hz, hold_len, rise_len, yaw_amp=YAW_AMP,
                 pitch=PITCH_DOWN, neck=NECK_CMD, body_pitch=0.0, roll=0.0, stay_down=False, stand_up=False, shake_start_frac=1.0):
    """The shared skeleton: [sit] -> droop (neck + head pitch down) -> slow yaw shakes -> hold -> rise (or stay).
    shake_start_frac: where in the droop ramp the shake window opens (1.0 = after the droop, 0.5 = at its midpoint,
    overlapping the rest of the droop; Remi's choice for 'devastated')."""
    t_droop = sit_start + sit_len                 # head starts down once the seat is reached (or at once when standing)
    t_shake = t_droop + droop_len * shake_start_frac
    shake_len = shake_n / shake_hz if shake_n else 0.0
    t_hold = t_shake + shake_len
    t_rise = t_hold + hold_len
    t_end = t_rise + (0.0 if stay_down else rise_len)
    want_beats = t is None
    if want_beats:
        t = -1.0
    down = ramp(t - t_droop, droop_len)
    if not stay_down:
        down *= 1.0 - ramp(t - t_rise, rise_len)
    yaw = 0.0
    if shake_n and t_shake <= t < t_hold:
        ph = (t - t_shake) * shake_hz
        yaw = yaw_amp * math.sin(2 * math.pi * ph) * ramp(t - t_shake, 0.5) * ramp(t_hold - t, 0.5)
    skill = None
    if sit_len > 0:
        if t >= sit_start:
            skill = "sit"
        if stand_up and t >= t_end:
            skill = "stand"
    total = t_end + (4.0 if stand_up else 0.8)
    if want_beats:     # beat times, for the report
        ext = [round(t_shake + (k + 0.5) / (2 * shake_hz), 2) for k in range(2 * shake_n)]   # yaw extremes: +, -, +, - ...
        return dict(sit=sit_start if sit_len > 0 else None, droop_start=t_droop, droop_end=t_droop + droop_len, shake_start=t_shake,
                    shake_extremes=ext, shake_end=t_hold, rise_start=t_rise, head_level=t_end, total=round(total, 2))
    return dict(neck=neck * down, head_pitch=pitch * down, head_yaw=yaw, head_roll=roll * down,
                body_pitch=body_pitch * down, skill=skill), total


DECIDED = {
    "sad": dict(
        desc="SAD (decided): standing. Body pitch +0.10 (trunk stays level) and neck/head droop over 2 s, two slow shakes (+-0.4 rad, 0.5 Hz), 0.5 s hold, head back up over 2 s. Same as stand_headdown_shake.",
        fn=lambda t: _droop_shake(t, sit_start=0.0, sit_len=0.0, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=0.5, rise_len=2.0, body_pitch=0.10)),
    "devastated": dict(
        desc="DEVASTATED (decided): sit, then the 2 s droop; the two slow shakes start when the droop is half done (overlapping the rest of it), 1 s hold, head back up over 2 s, stays seated. sit_headdown_slowshake with the shake moved earlier.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=1.0, rise_len=2.0, shake_start_frac=0.5)),
    "sad_twosided": dict(
        desc="SAD, option (not decided): identical to sad but body pitch +0.05 instead of +0.10. Finding: at +0.10 the stand net only turns the head one way (yaw +0.4 -> ~0, -0.4 -> -0.41), so the shake in `sad` is one-sided; at +0.05 it turns both ways (+0.38 / -0.43) with the head still deep (head_pitch +57 deg, neck -24 deg).",
        fn=lambda t: _droop_shake(t, sit_start=0.0, sit_len=0.0, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=0.5, rise_len=2.0, body_pitch=0.05)),
    "devastated_quick": dict(
        desc="DEVASTATED, quicker variant to compare: droop 1.5 s, shakes from half droop, otherwise identical.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=1.5, shake_n=2, shake_hz=0.5, hold_len=1.0, rise_len=2.0, shake_start_frac=0.5)),
}

CANDIDATES = {
    "sit_headdown_slowshake": dict(
        desc="THE PICK. Sit (~1.5 s), then over 2 s the neck and head droop; two slow 'no' shakes of the head (+-0.4 rad at 0.5 Hz, 4 s), a 1 s hold, then the head rises back over 2 s. Stays seated.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=1.0, rise_len=2.0)),
    "sit_only_droop": dict(
        desc="Sit, then the head droops over 2.5 s and stays down (no shake): the quiet version. Ends seated, head down.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=2.5, shake_n=0, shake_hz=1, hold_len=3.5, rise_len=0, stay_down=True)),
    "sit_headdown_tilt_fast": dict(
        desc="Faster, with a head tilt: sit, droop in 1.2 s with the head rolled 0.25 rad to one side, three shakes at 0.8 Hz, rise in 1.2 s. The 'sulky' variant.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=1.2, shake_n=3, shake_hz=0.8, hold_len=0.6, rise_len=1.2, roll=0.25, yaw_amp=0.3)),
    "sit_headdown_slower_standup": dict(
        desc="Slowest: droop over 3 s, two very slow shakes (0.35 Hz), rise over 3 s, then the duck stands back up (sit-stand rise net, then stand). The long version for a long quack.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=3.0, shake_n=2, shake_hz=0.35, hold_len=1.0, rise_len=3.0, stand_up=True)),
    "stand_headdown_shake": dict(
        desc="No sit: standing, a tiny body-pitch command (+0.10, the trunk stays level) makes the stand net drop the head much further than the head slots alone; two slow shakes; rises back over 2 s. 7.5 s, Reachy sad2's timing.",
        fn=lambda t: _droop_shake(t, sit_start=0.0, sit_len=0.0, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=0.5, rise_len=2.0, body_pitch=0.10)),
    "stand_bow015_headdown_shake": dict(
        desc="Standing with a real bow: body pitch +0.15 tilts the trunk ~29 deg nose-down (the stand net crouches into it), neck and head droop, two slow shakes, rise. Does not fall and does not trip the runtime's fall detector.",
        fn=lambda t: _droop_shake(t, sit_start=0.0, sit_len=0.0, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=0.5, rise_len=2.0, body_pitch=0.15)),
    "stand_bow030_headdown_shake": dict(
        desc="FAILED, kept for the record: body pitch +0.30 (the README's 'bow' limit) plus the head droop topples the duck forward at 1.3 s; the runtime's limp-fall fires and it lies on its face.",
        fn=lambda t: _droop_shake(t, sit_start=0.0, sit_len=0.0, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=0.5, rise_len=2.0, body_pitch=0.30)),
    "sit_bow_headdown_shake": dict(
        desc="FAILED (soft), kept for the record: a body-pitch bow (+0.3) while seated does nothing to the trunk (-7 deg) and blocks the neck (only -20 deg instead of -53): the seated net ignores the bow and the head droops less. Do not add a bow to the seated version.",
        fn=lambda t: _droop_shake(t, sit_start=0.3, sit_len=1.5, droop_len=2.0, shake_n=2, shake_hz=0.5, hold_len=1.0, rise_len=2.0, body_pitch=0.3)),
}


# ---------------------------------------------------------------------------------------------------------------
# 3. render: mp4, contact sheet, keyframe json, measurements
# ---------------------------------------------------------------------------------------------------------------
def render(name, with_sound=True):
    cand = {**CANDIDATES, **DECIDED}[name]
    fn = cand["fn"]
    _, total = fn(0.0)
    m, d, du = fresh()
    r = mujoco.Renderer(m, SIZE[1], SIZE[0])
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0.03, 0.0, 0.11]
    cam.distance, cam.azimuth, cam.elevation = 0.60, 115, -6      # fixed three-quarter front-right, the head pitch reads best here
    font = ImageFont.truetype(FONT, 15)
    frames, keys, log = [], [], []
    next_frame = 0.0
    rise_state = None
    n = int(round(total / F.CDT))
    for k in range(n):
        t = k * F.CDT
        h, _ = fn(t)
        du.head[:] = (h["neck"], h["head_pitch"], h["head_yaw"], h["head_roll"])
        du.body[:] = 0
        du.body[2] = h["body_pitch"]
        du.twist[:] = 0
        if h["skill"] == "sit":
            du.skill = "sit"
            rise_state = None
        elif h["skill"] == "stand":
            # the rise: sitstand net with posture flag 0 until the duck has been upright for 0.35 s, then the stand net
            # (the Madison recipe; robotd's fixed 1.0 s rise topples this sim duck, 1.5 s or the state-based handoff do not)
            if rise_state is None:
                rise_state = [t, None, None]          # started, upright since, handed over at
            if rise_state[2] is None:
                if du.upright():
                    rise_state[1] = rise_state[1] if rise_state[1] is not None else t
                    if t - rise_state[1] >= 0.35:
                        rise_state[2] = t
                else:
                    rise_state[1] = None
            du.skill = "rise" if rise_state[2] is None else None
        else:
            du.skill = None
        step(m, d, du, t)
        q = du.q()
        jd = {nm: float(q[F.HEAD_IDX[i]] - F.HOME[F.HEAD_IDX[i]]) for i, nm in enumerate(NAMES)}
        g = du.grav()
        log.append(dict(t=round(t, 3), net=du.net, trunk_z=float(du.pos()[2]), beak_z=float(du.beak_pos()[2]),
                        trunk_pitch_deg=math.degrees(math.atan2(-g[0], -g[2])), **jd))
        if k % 5 == 0:      # keyframes every 0.1 s
            keys.append(dict(t=round(t, 2), neck=round(h["neck"], 3), head_pitch=round(h["head_pitch"], 3), head_yaw=round(h["head_yaw"], 3),
                             head_roll=round(h["head_roll"], 3), body_pitch=round(h["body_pitch"], 3), skill=h["skill"]))
        if t >= next_frame - 1e-9:
            r.update_scene(d, camera=cam)
            img = Image.fromarray(r.render())
            dr = ImageDraw.Draw(img)
            txt = (f"{name}   t={t:4.1f}s   net={du.net}\n"
                   f"cmd  neck {h['neck']:+.2f}  pitch {h['head_pitch']:+.2f}  yaw {h['head_yaw']:+.2f}  roll {h['head_roll']:+.2f}  body_pitch {h['body_pitch']:+.2f}\n"
                   f"joint neck {jd['neck_pitch']:+.2f}  pitch {jd['head_pitch']:+.2f}  yaw {jd['head_yaw']:+.2f}  roll {jd['head_roll']:+.2f}")
            dr.multiline_text((8, 6), txt, font=font, fill="white", stroke_width=2, stroke_fill="black", spacing=2)
            if du.fell_at is not None:
                dr.text((8, SIZE[1] - 24), "FELL", font=font, fill=(255, 60, 60), stroke_width=2, stroke_fill="black")
            frames.append(np.asarray(img))
            next_frame += 1.0 / FPS
    # measurements
    hp = np.array([l["head_pitch"] for l in log])
    nk = np.array([l["neck_pitch"] for l in log])
    yw = np.array([l["head_yaw"] for l in log])
    bz = np.array([l["beak_z"] for l in log])
    tz = np.array([l["trunk_z"] for l in log])
    meas = dict(
        name=name, description=cand["desc"], duration_s=round(total, 2), fell=du.fell_at is not None, fell_at=du.fell_at,
        head_pitch_joint_max_rad=round(float(hp.max()), 3), head_pitch_joint_max_deg=round(math.degrees(hp.max()), 1),
        neck_joint_min_rad=round(float(nk.min()), 3), neck_joint_min_deg=round(math.degrees(nk.min()), 1),
        head_yaw_joint_amp_rad=round(float(np.abs(yw).max()), 3),
        beak_z_start_m=round(float(bz[10]), 3), beak_z_min_m=round(float(bz.min()), 3), beak_drop_m=round(float(bz[10] - bz.min()), 3),
        trunk_z_start_m=round(float(tz[10]), 3), trunk_z_min_m=round(float(tz.min()), 3), trunk_z_end_m=round(float(tz[-1]), 3),
        trunk_pitch_max_deg=round(float(max(l["trunk_pitch_deg"] for l in log)), 1),
        nets=sorted(set(l["net"] for l in log)), upright_at_end=bool(du.upright()),
        head_cmd=dict(neck=NECK_CMD, head_pitch=PITCH_DOWN, yaw_amp=YAW_AMP),
    )
    # write mp4 (silent) + contact sheet + json
    base = HERE / f"{name}.mp4"
    imageio.mimwrite(str(base), frames, fps=FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=8,
                     output_params=["-crf", "20", "-movflags", "+faststart"])
    sheet(name, frames, total, meas)
    beats_sheet(name, frames, fn(None), log)
    beats = fn(None)
    json.dump(dict(keyframes=keys, measured=meas, beats=beats, fps=FPS), open(HERE / f"{name}.json", "w"), indent=1)
    json.dump(log, open(HERE / f"{name}.log.json", "w"))
    print(f"{name}: {total:.1f} s, fell={meas['fell']}, head_pitch joint max {meas['head_pitch_joint_max_deg']:+.0f} deg, "
          f"neck min {meas['neck_joint_min_deg']:+.0f} deg, beak drop {meas['beak_drop_m']*100:.1f} cm, trunk z {meas['trunk_z_start_m']:.3f}->{meas['trunk_z_min_m']:.3f}")
    if with_sound:
        add_sound(name, base, fn, total)
    return meas


def beats_sheet(name, frames, b, log):
    """Frames at the beats: seated/start, droop, shake start, each yaw extreme, rising, level; with the measured joints."""
    times = [(b["sit"] + 0.9 if b["sit"] is not None else 0.0, "seated" if b["sit"] is not None else "start"),
             (b["droop_start"] + 0.4, "droop"), (b["shake_start"] + 0.15, "shake starts")]
    times += [(x, f"shake extreme {i + 1}") for i, x in enumerate(b["shake_extremes"])]
    times += [(b["rise_start"] + 1.0, "rising"), (b["head_level"], "level")]
    W, H = SIZE
    cols, rows = 5, 2
    out = Image.new("RGB", (cols * W // 2 + 8 * (cols + 1), rows * H // 2 + 8 * (rows + 1) + 24), (30, 30, 34))
    dr = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT, 14)
    for k, (t, lab) in enumerate(times[:cols * rows]):
        i = min(len(frames) - 1, int(round(t * FPS)))
        l = min(log, key=lambda r: abs(r["t"] - t))
        im = Image.fromarray(frames[i]).resize((W // 2, H // 2))
        x = 8 + (k % cols) * (W // 2 + 8)
        y = 8 + (k // cols) * (H // 2 + 8)
        out.paste(im, (x, y))
        dr.text((x + 4, y + H // 2 - 34), f"t = {t:.2f} s  {lab}", font=font, fill="white", stroke_width=2, stroke_fill="black")
        dr.text((x + 4, y + H // 2 - 18), f"joint pitch {l['head_pitch']:+.2f} neck {l['neck_pitch']:+.2f} yaw {l['head_yaw']:+.2f}", font=font,
                fill=(255, 230, 120), stroke_width=2, stroke_fill="black")
    dr.text((8, out.height - 20), f"{name}: frames at the beats", font=font, fill="white")
    out.save(HERE / f"{name}_beats.png")


def sheet(name, frames, total, meas, n=8):
    idx = np.linspace(0, len(frames) - 1, n).astype(int)
    W, H = SIZE
    cols, rows = 4, 2
    out = Image.new("RGB", (cols * W // 2 + 8 * (cols + 1), rows * H // 2 + 8 * (rows + 1) + 24), (30, 30, 34))
    dr = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT, 14)
    for j, i in enumerate(idx):
        im = Image.fromarray(frames[i]).resize((W // 2, H // 2))
        x = 8 + (j % cols) * (W // 2 + 8)
        y = 8 + (j // cols) * (H // 2 + 8)
        out.paste(im, (x, y))
        dr.text((x + 4, y + H // 2 - 18), f"t = {i / FPS:.1f} s", font=font, fill="white", stroke_width=2, stroke_fill="black")
    dr.text((8, out.height - 20), f"{name}   {total:.1f} s   fell: {meas['fell']}   head_pitch max {meas['head_pitch_joint_max_deg']:+.0f} deg   neck {meas['neck_joint_min_deg']:+.0f} deg",
            font=font, fill="white")
    out.save(HERE / f"{name}_sheet.png")


# ---------------------------------------------------------------------------------------------------------------
# 4. placeholder sound: the first sad candidate wav in sounds/sadness, else the Reachy sad2 reference; starts when the head begins to droop
# ---------------------------------------------------------------------------------------------------------------
def load_wav(path, sr=22050):
    with wave.open(str(path)) as w:
        fr, nch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
    x = np.frombuffer(raw, dt).astype(np.float32) / float(2 ** (8 * sw - 1))
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    if fr != sr:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * sr / fr)), np.arange(len(x)), x).astype(np.float32)
    # trim leading/trailing silence
    a = np.abs(x)
    thr = max(1e-4, a.max() * 0.02)
    nz = np.nonzero(a > thr)[0]
    if len(nz):
        x = x[max(0, nz[0] - sr // 20): nz[-1] + sr // 5]
    peak = np.abs(x).max()
    if peak > 0:
        x = x * (0.7 / peak)
    return x, sr


def placeholder_sound():
    # the other agents' port of Reachy's sad2 (the reference Remi confirmed), slow variant; else any candidate; else the Reachy original
    pref = [SOUND_DIR / "A_port_sad2_v4_slow.wav"] + (sorted(SOUND_DIR.glob("*.wav")) if SOUND_DIR.exists() else [])
    src = next((p for p in pref if p.exists()), REF_SAD2)
    return src, load_wav(src)


def add_sound(name, base, fn, total):
    src, (x, sr) = placeholder_sound()
    # sound starts when the head starts going down (first tick with a non-zero head_pitch command)
    t_droop = next((k * F.CDT for k in range(int(total / F.CDT)) if fn(k * F.CDT)[0]["head_pitch"] > 1e-3), 0.0)
    mix = np.zeros(int((total + 0.5) * sr), np.float32)
    i = int(t_droop * sr)
    n = min(len(x), len(mix) - i)
    mix[i:i + n] += x[:n]
    wavp = HERE / f"{name}_sound.wav"
    with wave.open(str(wavp), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    out = HERE / f"{name}_sound.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-i", str(wavp), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(out)], check=True)
    wavp.unlink()
    print(f"  + sound version {out.name} (placeholder {src.name}, {len(x)/sr:.1f} s, starts at t={t_droop:.1f} s)")


# ---------------------------------------------------------------------------------------------------------------
# 5. index page
# ---------------------------------------------------------------------------------------------------------------
def _section(name):
        p = HERE / f"{name}.json"
        if not p.exists():
            return ""
        j = json.load(open(p))
        m = j["measured"]
        b = j.get("beats")
        beats = ""
        if b:
            beats = (f"<tr><th>beats</th><td>sit {b['sit']} s &middot; droop {b['droop_start']}-{b['droop_end']} s &middot; shake {b['shake_start']}-{b['shake_end']} s "
                     f"(extremes {', '.join(str(x) for x in b['shake_extremes'])}) &middot; rise {b['rise_start']}-{b['head_level']} s</td></tr>")
        snd = f'<p><a href="{name}_sound.mp4">with placeholder sound</a></p>' if (HERE / f"{name}_sound.mp4").exists() else ""
        return f"""
<section>
  <h2>{name}</h2>
  <p class="desc">{m['description']}</p>
  <div class="row">
    <video src="{name}.mp4" controls loop muted playsinline width="640" height="480"></video>
    <div class="facts">
      <table>
        <tr><th>duration</th><td>{m['duration_s']} s</td></tr>
        <tr><th>fell</th><td class="{'bad' if m['fell'] else 'ok'}">{'YES at %.1f s' % m['fell_at'] if m['fell'] else 'no'}</td></tr>
        {beats}
        <tr><th>head_pitch joint reached</th><td>{m['head_pitch_joint_max_deg']:+.0f} deg ({m['head_pitch_joint_max_rad']:+.2f} rad, beak down)</td></tr>
        <tr><th>neck joint reached</th><td>{m['neck_joint_min_deg']:+.0f} deg ({m['neck_joint_min_rad']:+.2f} rad)</td></tr>
        <tr><th>head yaw shake, joint</th><td>+-{math.degrees(m['head_yaw_joint_amp_rad']):.0f} deg</td></tr>
        <tr><th>beak tip drop</th><td>{m['beak_drop_m']*100:.1f} cm (from {m['beak_z_start_m']*100:.1f} cm to {m['beak_z_min_m']*100:.1f} cm above the floor)</td></tr>
        <tr><th>trunk height</th><td>{m['trunk_z_start_m']*100:.1f} cm -> {m['trunk_z_min_m']*100:.1f} cm (end {m['trunk_z_end_m']*100:.1f} cm)</td></tr>
        <tr><th>nets used</th><td>{', '.join(m['nets'])}</td></tr>
        <tr><th>head command</th><td>neck {m['head_cmd']['neck']}, head_pitch {m['head_cmd']['head_pitch']}, yaw +-{m['head_cmd']['yaw_amp']}</td></tr>
      </table>
      {snd}
      <p><a href="{name}.json">keyframes json</a> &middot; <a href="{name}_sheet.png">contact sheet</a></p>
    </div>
  </div>
  {'<img class="sheet" src="%s_beats.png">' % name if (HERE / f"{name}_beats.png").exists() else ''}
  <img class="sheet" src="{name}_sheet.png">
</section>"""


EXPRESSION_NOTES = """
<section class="decided">
<h2>Decided (Remi, 2026-09-04): two sad emotions</h2>
<p><b>sad</b> = standing (<code>stand_headdown_shake</code>). <b>devastated</b> = with the sit (<code>sit_headdown_slowshake</code>, shakes moved to the middle of the droop). <code>devastated_quick</code> is a quicker variant to compare.</p>
<p>Expression numbers (head deltas as functions of t in seconds since the button press; <code>ramp(x, L)</code> = half-cosine 0..1 over L seconds, clamped; head_pitch positive = beak down):</p>
<pre>
sad          (standing, no sit; body pitch +0.10 on robot.pose along the same envelope)
  down(t) = ramp(t, 2.0) * (1 - ramp(t - 4.5, 2.0))                      head up at 2.0, starts rising 4.5, level at 6.5
  yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 2.0)) * ramp(t - 2.0, 0.5) * ramp(6.0 - t, 0.5)   for 2.0 <= t < 6.0, else 0
  neck = -1.5*down   head_pitch = +1.0*down   head_yaw = yaw   head_roll = 0   body_pitch = 0.10*down   duration 6.5 s

devastated   (robot.do sit_toggle at t = 0, head starts at 1.5 s; stays seated at the end)
  down(t) = ramp(t - 1.5, 2.0) * (1 - ramp(t - 7.5, 2.0))                head down at 3.5, starts rising 7.5, level at 9.5
  yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 2.5)) * ramp(t - 2.5, 0.5) * ramp(6.5 - t, 0.5)   for 2.5 <= t < 6.5, else 0
  neck = -1.5*down   head_pitch = +1.0*down   head_yaw = yaw   head_roll = 0   body_pitch = 0   duration 9.5 s

devastated_quick
  down(t) = ramp(t - 1.5, 1.5) * (1 - ramp(t - 7.25, 2.0))               head down at 3.0, starts rising 7.25, level at 9.25
  yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 2.25)) * ramp(t - 2.25, 0.5) * ramp(6.25 - t, 0.5)   for 2.25 <= t < 6.25, else 0
  duration 9.25 s
</pre>
<p><b>Finding on <code>sad</code>:</b> with body pitch +0.10 the stand net turns the head only one way during the shake (yaw joint ~0 / -0.41), so it reads as "look aside, back, aside, back". <code>sad_twosided</code> (body pitch +0.05, everything else identical) shakes both ways (+0.38 / -0.43) with the head still deep (+57 deg). Offered as an option; <code>sad</code> is unchanged.</p>
<p>(In the videos the sit button is pressed at t = 0.3 s and the sad expression starts at t = 0.0 s, so add 0.3 s to the devastated numbers to match the video clocks.)</p>
</section>
"""


def index():
    rows = [EXPRESSION_NOTES] + [_section(n) for n in DECIDED] + ["<h2 class=\"earlier\">Earlier candidates</h2>"] + [_section(n) for n in CANDIDATES]
    html = f"""<!doctype html><meta charset="utf-8"><title>Microduck sadness motion candidates</title>
<style>
body{{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:24px;background:#f6f4ef;color:#222;max-width:1400px}}
h1{{margin-bottom:4px}} .sub{{color:#666;margin-top:0}}
section{{background:#fff;border-radius:10px;padding:16px 20px;margin:18px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.row{{display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start}}
table{{border-collapse:collapse;font-size:14px}} th{{text-align:left;padding:3px 10px 3px 0;color:#555;font-weight:600}} td{{padding:3px 0}}
.bad{{color:#c00;font-weight:700}} .ok{{color:#080}}
.sheet{{width:100%;max-width:1320px;margin-top:12px;border-radius:6px}}
.desc{{font-size:15px}}
.decided{{background:#fff8e6;border:2px solid #e9b949}} .earlier{{margin-top:36px;color:#666}} pre{{font-size:13px;overflow-x:auto}}
video{{background:#000;border-radius:6px}}
</style>
<h1>Microduck: sadness motion candidates (simulation)</h1>
<p class="sub">Programmatic, no training. The duck is driven only through the real robot's command block: the sit skill, the four head deltas, body-pose pitch.
Camera: fixed three-quarter front. Sign: head_pitch positive = beak down. Rendered {SIZE[0]}x{SIZE[1]} at {FPS} fps. Report: <a href="REPORT.md">REPORT.md</a>. Probe numbers: <a href="probe.json">probe.json</a>.</p>
{''.join(rows)}
"""
    (HERE / "index.html").write_text(html)
    print("wrote", HERE / "index.html")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "render", "index"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--no-sound", action="store_true")
    a = ap.parse_args()
    if a.cmd == "probe":
        probe()
    elif a.cmd == "render":
        for nm in (a.names or list(CANDIDATES)):
            render(nm, with_sound=not a.no_sound)
        index()
    else:
        index()
