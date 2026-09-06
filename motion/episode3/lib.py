#!/usr/bin/env python
"""Episode 3 shared renderer: one emotion = a motion (pure function of time on the shipped policies) + a wav.

    import lib
    m = lib.Motion("yes_nod", "one nod", total=1.2, fn=lambda t: dict(head_pitch=...), beats=[(0.3, "down")])
    lib.render(m, wav, out=Path(".../motion/yes"), page=Path(".../combined/yes"), sound="Y1_flat")
    lib.write_page(page, header, cards)

`fn(t)` returns any subset of: neck, head_pitch, head_yaw, head_roll (rad, the real robot's `robot.head`
deltas), body_pitch, body_roll, body_z (`robot.pose`), twist (vx, vy, wz: `robot.move`), skill
(None | 'sit' | 'rise' | 'kick_left' | 'kick_right' | 'roulade' | 'ground_pick'), soften (True from the
moment `robot.soften` is issued: gain 50 at once, to 0 over 1 s, torque off, as robotd does), relax (True =
`robot.relax`, torque off at once), mouth (None = follow the wav; a number overrides, e.g. 0 for a closed
beak). Missing keys are 0 / None / False.

Sign conventions (measured on the shipped policies): head_pitch POSITIVE = beak DOWN; the neck only tracks
downward (negative command, about half of it); head_yaw +-1; head_roll +-0.27 joint range (ask up to 0.44);
body pitch positive = bow; body z negative = crouch (trained range z -0.025..+0.010, pitch +-0.26).
Real-robot rule: keep |neck| <= 0.75 and avoid head-forward poses (the walk policy steps forward).

Outputs per render: <out>/<stem>.mp4 (silent), <out>/<stem>.json (keyframes every 0.1 s with mouth, +
measured), <out>/<stem>.log.json (every tick), <out>/<stem>_beats.png, <page>/<stem>.mp4 (muxed).
"""
import json, math, subprocess, sys, wave
from dataclasses import dataclass, field
from pathlib import Path

import imageio, mujoco, numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/Users/remi/microduck/notes/reachy-encounter")
import duckfilm as F  # noqa: E402

ROOT = Path("/Users/remi/microduck/notes/emotions")
PY = "/Users/remi/microduck/.venv-mjlab/bin/python"
COMBINE = str(ROOT / "combine.py")
BANK = Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059")
SIZE = (640, 480)
FPS = 30
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MOUTH_DELAY = 0.15
PREROLL = 0.6
KP_SOFTEN_FROM, SOFTEN_LEN = 50.0, 1.0        # robotd: gain_limp 50 at once, to zero over 1 s, then torque off
CAMERAS = {
    "front34": dict(lookat=[0.02, 0.0, 0.14], distance=0.55, azimuth=152, elevation=-8),
    "side": dict(lookat=[0.03, 0.0, 0.11], distance=0.60, azimuth=115, elevation=-6),
    "wide": dict(lookat=[0.0, 0.0, 0.10], distance=0.85, azimuth=135, elevation=-10),
}
HEAD_NAMES = ["neck_pitch", "head_pitch", "head_yaw", "head_roll"]


def ramp(t, ln):
    """Smooth 0 -> 1 over ln seconds (half cosine), clamped. Same as expressions.rs::ramp."""
    if ln <= 0:
        return 1.0 if t >= 0 else 0.0
    x = min(1.0, max(0.0, t / ln))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def pulse(t, t0, up, hold, down):
    """0 -> 1 over `up` from t0, hold, back to 0 over `down`."""
    return ramp(t - t0, up) * (1.0 - ramp(t - t0 - up - hold, down))


def swings(t, extremes, amp, fade):
    """Alternating +amp, -amp ... half-cosine swings through `extremes`, fading in/out over `fade` (expressions.rs)."""
    if not extremes:
        return 0.0
    first, last = extremes[0], extremes[-1]
    if t < first - fade:
        return 0.0
    if t < first:
        return amp * ramp(t - (first - fade), fade)
    for i in range(len(extremes) - 1):
        a, b = extremes[i], extremes[i + 1]
        if t < b:
            sign = 1.0 if i % 2 == 0 else -1.0
            return sign * amp * (1.0 - 2.0 * ramp(t - a, b - a))
    sign = 1.0 if len(extremes) % 2 == 1 else -1.0
    return sign * amp * (1.0 - ramp(t - last, fade))


@dataclass
class Motion:
    name: str
    desc: str
    total: float
    fn: object
    beats: list = field(default_factory=list)      # [(t, label), ...] for the contact sheet
    camera: str = "front34"
    quacks: list = field(default_factory=list)     # sound onsets (s), for the jaw check


DEFAULT = dict(neck=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0, body_pitch=0.0, body_roll=0.0, body_z=0.0,
               twist=(0.0, 0.0, 0.0), skill=None, soften=False, relax=False, mouth=None)


def sample(motion, t):
    h = dict(DEFAULT)
    if t >= 0:
        h.update(motion.fn(t) or {})
    return h


# ---------------------------------------------------------------------------------------------------------------
class Duck3(F.Duck):
    """duckfilm's duck plus `robot.soften` (gain 50 at once, to 0 over 1 s, hold the joints where they were, torque off)."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.soften = False
        self._soften_t0 = None
        self._soften_q = None
        self.limp_fall = False        # the runtime's limp-fall would fight a scripted fall; we watch falls ourselves

    def control_tick(self, t):
        if self.soften and self._soften_t0 is None:
            self._soften_t0, self._soften_q = t, self.q()
        if self._soften_t0 is not None and not self.relax:
            self.t = t
            a = (t - self._soften_t0) / SOFTEN_LEN
            if a >= 1.0:
                self.relax = True
                self.net = "relax"
                self.kp = 0.0
            else:
                self.net = "soften"
                self.kp = KP_SOFTEN_FROM * (1.0 - a)
                self.bam.model.actuator.kp = self.kp
                self.bam.q_target[:] = self._soften_q
            self.jaw_open += 0.5 * (F.JAW_MAX * float(self.mouth) - self.jaw_open)
            return
        super().control_tick(t)


def fresh(camera="front34", reachy_at=None):
    m, d = F.build_scene(SIZE, reachy_at=reachy_at)
    du = Duck3(m, d, "duck_")
    du.make_bam()
    du.spawn(0.0, 0.0, 0.0)
    mujoco.mj_forward(m, d)
    du.bam.last_ts = d.time
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    c = CAMERAS[camera]
    cam.lookat[:] = c["lookat"]
    cam.distance, cam.azimuth, cam.elevation = c["distance"], c["azimuth"], c["elevation"]
    return m, d, du, cam


def step(m, d, du, t):
    du.control_tick(t)
    for _ in range(F.DECIMATION):
        du.physics_substep()
        mujoco.mj_step(m, d)
    du.after_step(t)


def mouth_envelope(wav_path):
    """RMS at 50 Hz (20 ms windows), 60 ms smoothing, open = clip(rms / (0.6 max)). Index k = tick k."""
    with wave.open(str(wav_path)) as w:
        sr, nch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, {2: np.int16, 4: np.int32}[sw]).astype(np.float32) / float(2 ** (8 * sw - 1))
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    win = int(round(sr * F.CDT))
    n = len(x) // win
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1))
    rms = np.convolve(rms, np.ones(3) / 3, mode="same")
    return np.clip(rms / (0.6 * rms.max()), 0.0, 1.0) if rms.max() > 0 else rms * 0


def wav_duration(wav_path):
    with wave.open(str(wav_path)) as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------------------------------------------------------
def render(motion, wav, out, page, sound="", sound_desc="", mouth_mode="wav", extra_frames=None, quiet=False):
    """Simulate + film one (motion, wav) pair. mouth_mode: 'wav' (beak follows the wav, 0.15 s late), 'closed'
    (beak shut whatever the wav: the leash variant), 'motion' (the motion's own mouth key only)."""
    out, page = Path(out), Path(page)
    out.mkdir(parents=True, exist_ok=True)
    page.mkdir(parents=True, exist_ok=True)
    stem = f"{motion.name}__{sound}" if sound else motion.name
    env = mouth_envelope(wav) if wav else np.zeros(1)
    total = motion.total
    m, d, du, cam = fresh(motion.camera)
    r = mujoco.Renderer(m, SIZE[1], SIZE[0])
    font = ImageFont.truetype(FONT, 15)
    frames, keys, log = [], [], []
    next_frame = 0.0
    n_pre = int(round(PREROLL / F.CDT))
    n = int(round(total / F.CDT))
    p0 = None
    for k in range(-n_pre, n):
        t = k * F.CDT
        h = sample(motion, t)
        kd = k - int(round(MOUTH_DELAY / F.CDT))
        wav_mouth = float(env[kd]) if 0 <= kd < len(env) else 0.0
        if mouth_mode == "closed":
            mouth = 0.0
        elif mouth_mode == "motion":
            mouth = float(h["mouth"] or 0.0)
        else:
            mouth = wav_mouth if h["mouth"] is None else float(h["mouth"])
        du.head[:] = (h["neck"], h["head_pitch"], h["head_yaw"], h["head_roll"])
        du.body[:] = 0
        du.body[0] = h["body_z"]
        du.body[1] = h["body_roll"]
        du.body[2] = h["body_pitch"]
        du.twist[:] = h["twist"]
        du.skill = h["skill"]
        du.soften = bool(h["soften"])
        if h["relax"]:
            du.relax = True
        du.mouth = mouth
        step(m, d, du, t + PREROLL)
        if k < 0:
            continue
        if p0 is None:
            p0 = du.pos()
        q = du.q()
        jd = {nm: float(q[F.HEAD_IDX[i]] - F.HOME[F.HEAD_IDX[i]]) for i, nm in enumerate(HEAD_NAMES)}
        pos, g = du.pos(), du.grav()
        log.append(dict(t=round(t, 3), net=du.net, kp=du.kp, mouth=mouth, jaw=float(du.jaw_open / F.JAW_MAX),
                        x=float(pos[0] - p0[0]), y=float(pos[1] - p0[1]), z=float(pos[2]), gz=float(g[2]),
                        pitch_deg=float(math.degrees(math.atan2(-g[0], -g[2]))), roll_deg=float(math.degrees(math.atan2(g[1], -g[2]))),
                        beak_z=float(du.beak_pos()[2]), fallen=bool(du.fallen()), **jd))
        if k % 5 == 0:
            keys.append(dict(t=round(t, 2), neck=round(h["neck"], 3), head_pitch=round(h["head_pitch"], 3), head_yaw=round(h["head_yaw"], 3),
                             head_roll=round(h["head_roll"], 3), body_pitch=round(h["body_pitch"], 3), body_z=round(h["body_z"], 4),
                             twist=[round(v, 3) for v in h["twist"]], skill=h["skill"], soften=bool(h["soften"]), relax=bool(h["relax"]),
                             mouth=round(mouth, 3)))
        if t >= next_frame - 1e-9:
            r.update_scene(d, camera=cam)
            img = Image.fromarray(r.render())
            dr = ImageDraw.Draw(img)
            txt = (f"{stem}   t={t:4.2f}s   net={du.net}\n"
                   f"cmd  neck {h['neck']:+.2f} pitch {h['head_pitch']:+.2f} yaw {h['head_yaw']:+.2f} roll {h['head_roll']:+.2f}  "
                   f"body z {h['body_z']:+.3f} pitch {h['body_pitch']:+.2f}  mouth {mouth:.2f}\n"
                   f"joint neck {jd['neck_pitch']:+.2f} pitch {jd['head_pitch']:+.2f} yaw {jd['head_yaw']:+.2f} roll {jd['head_roll']:+.2f}  "
                   f"trunk pitch {log[-1]['pitch_deg']:+.0f}deg  jaw {du.jaw_open / F.JAW_MAX:.2f}")
            dr.multiline_text((8, 6), txt, font=font, fill="white", stroke_width=2, stroke_fill="black", spacing=2)
            dr.rectangle([8, SIZE[1] - 18, 8 + 120, SIZE[1] - 8], outline="white")
            dr.rectangle([8, SIZE[1] - 18, 8 + int(120 * mouth), SIZE[1] - 8], fill=(255, 200, 60))
            dr.text((134, SIZE[1] - 22), "mouth", font=font, fill="white", stroke_width=2, stroke_fill="black")
            if du.fell_at is not None:
                dr.text((8, SIZE[1] - 44), "FELL", font=font, fill=(255, 60, 60), stroke_width=2, stroke_fill="black")
            if extra_frames:
                extra_frames(dr, t, h, du)
            frames.append(np.asarray(img))
            next_frame += 1.0 / FPS
    silent = out / f"{stem}.mp4"
    imageio.mimwrite(str(silent), frames, fps=FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=8,
                     output_params=["-crf", "20", "-movflags", "+faststart"])
    combined = page / f"{stem}.mp4"
    if wav:
        subprocess.run([PY, COMBINE, str(silent), str(wav), str(combined), "--at", "0"], check=True)
    else:
        subprocess.run(["cp", str(silent), str(combined)], check=True)
    meas = measure(motion, log, sound, wav, sound_desc, mouth_mode)
    json.dump(dict(keyframes=keys, measured=meas, fps=FPS), open(out / f"{stem}.json", "w"), indent=1)
    json.dump(log, open(out / f"{stem}.log.json", "w"))
    beats_sheet(out / f"{stem}_beats.png", stem, frames, motion, log)
    if not quiet:
        print(f"{stem}: {total} s  {'FELL@%.2f' % meas['fell_at'] if meas['fell'] else 'no fall'}  drift {meas['drift_cm']} cm  "
              f"joint max |neck| {meas['neck_min']:+.2f} pitch [{meas['head_pitch_min']:+.2f},{meas['head_pitch_max']:+.2f}] "
              f"yaw {meas['head_yaw_absmax']:.2f} roll {meas['head_roll_absmax']:.2f}  trunk pitch [{meas['trunk_pitch_min']:+.0f},{meas['trunk_pitch_max']:+.0f}]deg  "
              f"jaw@quacks {meas['jaw_at_quacks']} between {meas['jaw_between']}")
    return meas


def measure(motion, log, sound, wav, sound_desc, mouth_mode):
    arr = lambda k: np.array([l[k] for l in log])
    ts = arr("t")
    jaw = arr("jaw")
    quiet = np.ones(len(log), bool)
    q_jaw = []
    for tq in motion.quacks:
        q_jaw.append(round(float(jaw[np.abs(ts - tq) <= 0.35].max()), 2) if (np.abs(ts - tq) <= 0.35).any() else None)
        quiet &= np.abs(ts - tq) > 0.45
    fell_at = next((l["t"] for l in log if l["fallen"]), None)
    return dict(motion=motion.name, motion_desc=motion.desc, sound=sound, sound_desc=sound_desc, wav=str(wav) if wav else None,
                mouth_mode=mouth_mode, duration_s=motion.total, fell=fell_at is not None, fell_at=fell_at,
                drift_cm=round(float(np.hypot(arr("x"), arr("y")).max() * 100), 1),
                neck_min=round(float(arr("neck_pitch").min()), 3),
                head_pitch_min=round(float(arr("head_pitch").min()), 3), head_pitch_max=round(float(arr("head_pitch").max()), 3),
                head_yaw_absmax=round(float(np.abs(arr("head_yaw")).max()), 3), head_roll_absmax=round(float(np.abs(arr("head_roll")).max()), 3),
                trunk_pitch_min=round(float(arr("pitch_deg").min()), 1), trunk_pitch_max=round(float(arr("pitch_deg").max()), 1),
                trunk_z_min=round(float(arr("z").min()), 3), trunk_z_end=round(float(arr("z")[-1]), 3), gz_end=round(float(arr("gz")[-1]), 2),
                jaw_at_quacks=q_jaw, jaw_between=round(float(jaw[quiet].max()), 2) if quiet.any() else None,
                nets=[n for i, n in enumerate(arr("net")) if i == 0 or arr("net")[i - 1] != n][:12],
                beats=motion.beats)


def beats_sheet(path, stem, frames, motion, log):
    times = sorted([(0.0, "start")] + list(motion.beats) + [(motion.total - 0.05, "end")])[:10]
    W, H = SIZE
    cols, rows = 5, 2
    out = Image.new("RGB", (cols * W // 2 + 8 * (cols + 1), rows * H // 2 + 8 * (rows + 1) + 24), (30, 30, 34))
    dr = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT, 14)
    for k, (t, lab) in enumerate(times):
        i = min(len(frames) - 1, max(0, int(round(t * FPS))))
        l = min(log, key=lambda r_: abs(r_["t"] - t))
        im = Image.fromarray(frames[i]).resize((W // 2, H // 2))
        x = 8 + (k % cols) * (W // 2 + 8)
        y = 8 + (k // cols) * (H // 2 + 8)
        out.paste(im, (x, y))
        dr.text((x + 4, y + H // 2 - 34), f"t = {t:.2f} s  {lab}", font=font, fill="white", stroke_width=2, stroke_fill="black")
        dr.text((x + 4, y + H // 2 - 18), f"neck {l['neck_pitch']:+.2f} pitch {l['head_pitch']:+.2f} yaw {l['head_yaw']:+.2f} roll {l['head_roll']:+.2f} jaw {l['jaw']:.2f} trunk {l['pitch_deg']:+.0f}deg",
                font=font, fill=(255, 230, 120), stroke_width=2, stroke_fill="black")
    dr.text((8, out.height - 20), f"{stem}: frames at the beats", font=font, fill="white")
    out.save(path)


# ---------------------------------------------------------------------------------------------------------------
def card(out, page, stem, title, note="", rel="../../motion"):
    """One HTML card for a rendered pair. `out` is the motion folder, `page` the combined folder."""
    p = Path(out) / f"{stem}.json"
    if not p.exists():
        return ""
    m = json.load(open(p))["measured"]
    folder = Path(out).name
    beats = " &middot; ".join(f"{t:.2f} s {lab}" for t, lab in m["beats"])
    fall = f"<b style='color:#c00'>FELL at {m['fell_at']:.2f} s</b>" if m["fell"] else "no fall"
    return f"""
<div class="card">
  <h3>{title}{(' &nbsp;<span class="note">' + note + '</span>') if note else ''}</h3>
  <p class="snd"><b>motion:</b> {m['motion_desc']}</p>
  <video src="{stem}.mp4" controls playsinline width="640" height="480" preload="metadata"></video>
  <p class="beats"><b>beats:</b> {beats}</p>
  <p class="snd"><b>sound:</b> {m['sound_desc'] or '(silent)'}{' &middot; <b>beak closed</b>' if m['mouth_mode'] == 'closed' else ''}</p>
  <p class="meas">measured: {fall} &middot; trunk drift {m['drift_cm']} cm &middot; trunk pitch {m['trunk_pitch_min']:+.0f}..{m['trunk_pitch_max']:+.0f} deg &middot;
     joints: neck {m['neck_min']:+.2f}, head_pitch {m['head_pitch_min']:+.2f}..{m['head_pitch_max']:+.2f}, |yaw| {m['head_yaw_absmax']:.2f}, |roll| {m['head_roll_absmax']:.2f} rad &middot;
     jaw at the quacks {m['jaw_at_quacks']}, between {m['jaw_between']} &middot; nets {' > '.join(m['nets'])}</p>
  <p><a href="{rel}/{folder}/{stem}_beats.png">beats sheet</a> &middot; <a href="{rel}/{folder}/{stem}.json">keyframes json (with mouth)</a> &middot; <a href="{rel}/{folder}/{stem}.mp4">silent mp4</a></p>
  <img class="sheet" src="{rel}/{folder}/{stem}_beats.png" loading="lazy">
</div>"""


def write_page(page, header, intro, sections, open_it=False):
    """sections: [(title, text, [card_html, ...]), ...]."""
    html = f"""<!doctype html><meta charset="utf-8"><title>Microduck {header}</title>
<style>
body{{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:24px;background:#f6f4ef;color:#222;max-width:1400px}}
h1{{margin-bottom:4px}} .sub{{color:#666;margin-top:0}} h2{{margin-top:36px}}
.card{{background:#fff;border-radius:10px;padding:16px 20px;margin:18px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.card h3{{margin:0 0 8px}} .note{{font-size:13px;color:#b06000;font-weight:normal}} .beats,.snd,.meas{{font-size:14px;margin:6px 0}} .meas{{color:#555}}
.sheet{{width:100%;max-width:1360px;margin-top:10px;border-radius:6px}} video{{background:#000;border-radius:6px}}
.pick{{border:3px solid #2a7}} code{{background:#eee;padding:1px 4px;border-radius:3px}}
</style>
<h1>{header}</h1>
<p class="sub">{intro}</p>
"""
    for title, text, cards in sections:
        html += f"<h2>{title}</h2><p>{text}</p>" + "".join(cards)
    Path(page).mkdir(parents=True, exist_ok=True)
    (Path(page) / "index.html").write_text(html)
    print("wrote", Path(page) / "index.html")
    if open_it:
        subprocess.run(["open", str(Path(page) / "index.html")])


def bank(tag, letter):
    """A wav of the robot's own bank (seed 4145077059) as a float array at 48 kHz."""
    sys.path.insert(0, str(ROOT))
    from quack import read_wav
    return read_wav(BANK / tag / f"{tag}_{letter}.wav")[1]
