#!/usr/bin/env python
"""CURIOUS (Y button): head forward, tilt to the side, a short double quack rising like a question.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/curious/curious.py [--only SUBSTR] [--no-open]

Reads spec.json (three standing motions + (motion, wav) pairs; the wavs are on the beats). Motion from the spec fields,
all half-cosine ramps: `forward` [t0, t1]: neck 0 -> -0.8 and head_pitch 0 -> -0.35 (beak stays level while the head
comes forward), held until `back`; `tilt` = list of (t_start, t_end, roll): head_roll ramps to that roll and holds;
`yaw` = head_yaw ramped in with the first tilt; `back` [t0, t1]: everything ramps back to 0; `total` = clip length.
Mouth from the wav's RMS envelope (50 Hz, 60 ms smoothing, open = clip(rms / 0.6 max)), delayed 0.15 s, through the
robot's mouth intent. Standing, twist 0, body pose 0 (the stand net is in charge, as on the robot at rest).
Outputs: here (silent mp4, keyframes json with mouth, beats sheet, log) and combined/curious/ (muxed mp4 + index.html).
"""
import argparse, json, math, subprocess, sys
from pathlib import Path

import imageio, mujoco, numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SAD = Path("/Users/remi/microduck/notes/emotions/motion/sadness")
sys.path.insert(0, str(SAD))
sys.path.insert(0, "/Users/remi/microduck/notes/reachy-encounter")
import duckfilm as F
import sadness as S
from v2 import mouth_envelope, COMBINE, PY

def _arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv and sys.argv.index(flag) + 1 < len(sys.argv) else default


SPEC_FILE = HERE / _arg("--spec", "spec.json")
SPEC = json.load(open(SPEC_FILE))
OUT_COMBINED = Path("/Users/remi/microduck/notes/emotions/combined") / _arg("--page", "curious")
HEADER = _arg("--header", "curious (Y): head forward, tilt, double rising quack")
COMPARE = [c for c in _arg("--compare", "").split(",") if c]     # stems of earlier renders to show first, for comparison
FWD_NECK, FWD_PITCH = -0.8, -0.35
MOUTH_DELAY = 0.15
PREROLL = 0.6          # seconds of quiet standing before t = 0 (not in the clip): the duck settles from the spawn
ramp = S.ramp


def make_motion(name):
    b = SPEC["motions"][name]
    f0, f1 = b["forward"]
    k0, k1 = b["back"]
    tilts = b["tilt"]

    def fn(t):
        fwd = ramp(t - f0, f1 - f0)
        roll = 0.0
        for i, (ts, te, r) in enumerate(tilts):
            prev = tilts[i - 1][2] if i > 0 else 0.0
            if t >= ts:
                roll = prev + (r - prev) * ramp(t - ts, te - ts)
        yaw = b["yaw"] * ramp(t - tilts[0][0], tilts[0][1] - tilts[0][0]) if b["yaw"] else 0.0
        back = 1.0 - ramp(t - k0, k1 - k0)          # 1 until `back` starts, 0 when it ends
        return dict(neck=FWD_NECK * fwd * back, head_pitch=FWD_PITCH * fwd * back, head_yaw=yaw * back, head_roll=roll * back,
                    body_pitch=0.0, skill=None)
    return fn, b


def render_pair(motion, sound, wav, desc):
    fn, b = make_motion(motion)
    env = mouth_envelope(wav)
    total = b["total"]
    m, d, du = S.fresh()
    r = mujoco.Renderer(m, S.SIZE[1], S.SIZE[0])
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0.02, 0.0, 0.14]
    cam.distance, cam.azimuth, cam.elevation = 0.55, 152, -8       # three-quarter FRONT: the tilt and the beak show
    font = ImageFont.truetype(S.FONT, 15)
    frames, keys, log = [], [], []
    next_frame = 0.0
    n_pre = int(round(PREROLL / F.CDT))
    n = int(round(total / F.CDT))
    for k in range(-n_pre, n):
        t = k * F.CDT
        h = fn(t) if k >= 0 else dict(neck=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0, body_pitch=0.0, skill=None)
        kd = k - int(round(MOUTH_DELAY / F.CDT))
        mouth = float(env[kd]) if 0 <= kd < len(env) else 0.0
        du.head[:] = (h["neck"], h["head_pitch"], h["head_yaw"], h["head_roll"])
        du.body[:] = 0
        du.twist[:] = 0
        du.skill = None
        du.mouth = mouth
        S.step(m, d, du, t + PREROLL)
        if k < 0:
            continue
        q = du.q()
        jd = {nm: float(q[F.HEAD_IDX[i]] - F.HOME[F.HEAD_IDX[i]]) for i, nm in enumerate(S.NAMES)}
        bp = du.beak_pos()
        log.append(dict(t=round(t, 3), net=du.net, mouth=mouth, jaw=float(du.jaw_open / F.JAW_MAX), beak_x=float(bp[0]), beak_z=float(bp[2]), **jd))
        if k % 5 == 0:
            keys.append(dict(t=round(t, 2), neck=round(h["neck"], 3), head_pitch=round(h["head_pitch"], 3), head_yaw=round(h["head_yaw"], 3),
                             head_roll=round(h["head_roll"], 3), body_pitch=0.0, mouth=round(mouth, 3), skill=None))
        if t >= next_frame - 1e-9:
            r.update_scene(d, camera=cam)
            img = Image.fromarray(r.render())
            dr = ImageDraw.Draw(img)
            txt = (f"{motion} + {sound}   t={t:4.2f}s   net={du.net}\n"
                   f"cmd  neck {h['neck']:+.2f}  pitch {h['head_pitch']:+.2f}  yaw {h['head_yaw']:+.2f}  roll {h['head_roll']:+.2f}  mouth {mouth:.2f}\n"
                   f"joint neck {jd['neck_pitch']:+.2f}  pitch {jd['head_pitch']:+.2f}  yaw {jd['head_yaw']:+.2f}  roll {jd['head_roll']:+.2f}  jaw {du.jaw_open / F.JAW_MAX:.2f}")
            dr.multiline_text((8, 6), txt, font=font, fill="white", stroke_width=2, stroke_fill="black", spacing=2)
            dr.rectangle([8, S.SIZE[1] - 18, 8 + 120, S.SIZE[1] - 8], outline="white")
            dr.rectangle([8, S.SIZE[1] - 18, 8 + int(120 * mouth), S.SIZE[1] - 8], fill=(255, 200, 60))
            dr.text((134, S.SIZE[1] - 22), "mouth", font=font, fill="white", stroke_width=2, stroke_fill="black")
            if du.fell_at is not None:
                dr.text((8, S.SIZE[1] - 44), "FELL", font=font, fill=(255, 60, 60), stroke_width=2, stroke_fill="black")
            frames.append(np.asarray(img))
            next_frame += 1.0 / S.FPS
    OUT_COMBINED.mkdir(parents=True, exist_ok=True)
    stem = f"{motion}__{sound}"
    silent = HERE / f"{stem}.mp4"
    imageio.mimwrite(str(silent), frames, fps=S.FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=8,
                     output_params=["-crf", "20", "-movflags", "+faststart"])
    combined = OUT_COMBINED / f"{stem}.mp4"
    subprocess.run([PY, COMBINE, str(silent), str(wav), str(combined), "--at", "0"], check=True)
    # measurements
    at = lambda t: min(log, key=lambda l: abs(l["t"] - t))
    roll = np.array([l["head_roll"] for l in log]); nk = np.array([l["neck_pitch"] for l in log]); hp = np.array([l["head_pitch"] for l in log])
    yw = np.array([l["head_yaw"] for l in log]); jaw = np.array([l["jaw"] for l in log]); mo = np.array([l["mouth"] for l in log])
    bx = np.array([l["beak_x"] for l in log]); bz = np.array([l["beak_z"] for l in log])
    tilt_vals = [round(float(at(te + 0.25)["head_roll"]), 3) for (_, te, _) in b["tilt"]]     # 0.25 s after each tilt ramp ends
    q_jaw = [round(float(max(l["jaw"] for l in log if abs(l["t"] - tq) <= 0.3)), 2) for tq in b["quacks"]]
    quiet = np.ones(len(log), bool)
    for tq in b["quacks"]:
        quiet &= np.abs(np.array([l["t"] for l in log]) - tq) > 0.45
    meas = dict(motion=motion, sound=sound, wav=str(wav), desc=desc, motion_desc=b["desc"], duration_s=total, fell=du.fell_at is not None, fell_at=du.fell_at,
                roll_joint_at_tilts=tilt_vals, roll_joint_max_abs=round(float(np.abs(roll).max()), 3), roll_joint_max_abs_deg=round(math.degrees(np.abs(roll).max()), 1),
                neck_joint_min=round(float(nk.min()), 3), head_pitch_joint_min=round(float(hp.min()), 3), yaw_joint_max=round(float(yw[np.argmax(np.abs(yw))]), 3),
                beak_forward_cm=round(float((bx.max() - bx[0]) * 100), 1), beak_dz_cm=round(float((bz[np.argmax(bx)] - bz[0]) * 100), 1),
                jaw_max_at_quacks=q_jaw, jaw_max_between_quacks=round(float(jaw[quiet].max()), 2) if quiet.any() else None,
                jaw_open_ticks=int((jaw > 0.3).sum()), beats=b)
    json.dump(dict(keyframes=keys, measured=meas, fps=S.FPS), open(HERE / f"{stem}.json", "w"), indent=1)
    json.dump(log, open(HERE / f"{stem}.log.json", "w"))
    beats_sheet(stem, frames, b, log)
    print(f"{stem}: {total} s fell={meas['fell']} roll@tilts={tilt_vals} (max {meas['roll_joint_max_abs_deg']} deg) neck {meas['neck_joint_min']:+.2f} pitch {meas['head_pitch_joint_min']:+.2f} "
          f"yaw {meas['yaw_joint_max']:+.2f} beak fwd {meas['beak_forward_cm']} cm; jaw at quacks {q_jaw}, between {meas['jaw_max_between_quacks']}")
    return meas


def beats_sheet(stem, frames, b, log):
    times = [(0.0, "start"), (b["forward"][1], "forward")]
    times += [(te, f"tilt {i + 1}") for i, (_, te, _) in enumerate(b["tilt"])]
    times += [(tq + MOUTH_DELAY + 0.06, f"quack {i + 1}") for i, tq in enumerate(b["quacks"])]
    times += [(b["hold_end"], "hold end"), (b["back"][1], "back"), (b["total"] - 0.05, "end")]
    times = sorted(times)[:10]
    W, H = S.SIZE
    cols, rows = 5, 2
    out = Image.new("RGB", (cols * W // 2 + 8 * (cols + 1), rows * H // 2 + 8 * (rows + 1) + 24), (30, 30, 34))
    dr = ImageDraw.Draw(out)
    font = ImageFont.truetype(S.FONT, 14)
    for k, (t, lab) in enumerate(times):
        i = min(len(frames) - 1, int(round(t * S.FPS)))
        l = min(log, key=lambda r_: abs(r_["t"] - t))
        im = Image.fromarray(frames[i]).resize((W // 2, H // 2))
        x = 8 + (k % cols) * (W // 2 + 8)
        y = 8 + (k // cols) * (H // 2 + 8)
        out.paste(im, (x, y))
        dr.text((x + 4, y + H // 2 - 34), f"t = {t:.2f} s  {lab}", font=font, fill="white", stroke_width=2, stroke_fill="black")
        dr.text((x + 4, y + H // 2 - 18), f"roll {l['head_roll']:+.2f} neck {l['neck_pitch']:+.2f} pitch {l['head_pitch']:+.2f} yaw {l['head_yaw']:+.2f} jaw {l['jaw']:.2f}",
                font=font, fill=(255, 230, 120), stroke_width=2, stroke_fill="black")
    dr.text((8, out.height - 20), f"{stem}: frames at the beats (quack frames 0.2 s after the quack onset, where the jaw is open)", font=font, fill="white")
    out.save(HERE / f"{stem}_beats.png")


def card(stem, motion, sound, sound_desc, label=""):
        p = HERE / f"{stem}.json"
        if not p.exists():
            return ""
        m = json.load(open(p))["measured"]
        b = m["beats"]
        r = dict(motion=motion, sound=sound, desc=sound_desc)
        beats = (f"forward {b['forward'][0]}-{b['forward'][1]} s &middot; tilt " + ", ".join(f"{ts}-{te} s to {rr:+.2f}" for ts, te, rr in b["tilt"]) +
                 (f" &middot; yaw {b['yaw']}" if b["yaw"] else "") + f" &middot; quacks at {', '.join(str(q) for q in b['quacks'])} s &middot; hold to {b['hold_end']} &middot; back {b['back'][0]}-{b['back'][1]} s &middot; {b['total']} s")
        return f"""
<div class="card">
  <h3>{r['motion']} + {r['sound']}{label}</h3>
  <p class="snd"><b>motion:</b> {m['motion_desc']}</p>
  <video src="{stem}.mp4" controls playsinline width="640" height="480"></video>
  <p class="beats"><b>beats:</b> {beats}</p>
  <p class="snd"><b>sound:</b> {r['desc']}</p>
  <p class="meas">measured: {'FELL' if m['fell'] else 'no fall'} &middot; roll joint at the tilt(s) {m['roll_joint_at_tilts']} rad (max {m['roll_joint_max_abs_deg']} deg, range +-0.27) &middot;
     neck {m['neck_joint_min']:+.2f}, head_pitch {m['head_pitch_joint_min']:+.2f}, yaw {m['yaw_joint_max']:+.2f} rad &middot; beak forward {m['beak_forward_cm']} cm (dz {m['beak_dz_cm']} cm) &middot;
     jaw at the quacks {m['jaw_max_at_quacks']}, between them {m['jaw_max_between_quacks']}</p>
  <p><a href="../../motion/curious/{stem}_beats.png">beats sheet</a> &middot; <a href="../../motion/curious/{stem}.json">keyframes json (with mouth)</a> &middot; <a href="../../motion/curious/{stem}.mp4">silent mp4</a></p>
  <img class="sheet" src="../../motion/curious/{stem}_beats.png">
</div>"""


def index():
    cards = {n: [] for n in SPEC["motions"]}
    for r in SPEC["renders"]:
        cards[r["motion"]].append(card(f"{r['motion']}__{r['sound']}", r["motion"], r["sound"], r["desc"]))
    compare = ""
    for stem in COMPARE:
        mo, so = stem.split("__", 1)
        j = json.load(open(HERE / f"{stem}.json"))["measured"]
        compare += card(stem, mo, so, j["desc"], label=' &nbsp;<span class="note">for comparison: the pick from the first round</span>')
    html = f"""<!doctype html><meta charset="utf-8"><title>Microduck {HEADER}</title>
<style>
body{{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:24px;background:#f6f4ef;color:#222;max-width:1400px}}
h1{{margin-bottom:4px}} .sub{{color:#666;margin-top:0}} h2{{margin-top:36px}}
.card{{background:#fff;border-radius:10px;padding:16px 20px;margin:18px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.card h3{{margin:0 0 8px}} .note{{font-size:13px;color:#b06000;font-weight:normal}} .beats,.snd,.meas{{font-size:14px;margin:6px 0}} .meas{{color:#555}}
.sheet{{width:100%;max-width:1360px;margin-top:10px;border-radius:6px}}
video{{background:#000;border-radius:6px}}
</style>
<h1>{HEADER}</h1>
<p class="sub">Standing (stand net at rest, no sit, body pose 0). Head deltas: neck -0.8 and head_pitch -0.35 bring the head forward with the beak level;
head_roll +-0.27 is the tilt (the joint's full range); the mouth follows the wav's loudness with a 0.15 s delay. Three-quarter front camera. Simulation, 640x480, 30 fps.
Motions and json: <code>/Users/remi/microduck/notes/emotions/motion/curious/</code> (spec: <code>{SPEC_FILE.name}</code>, renderer: <code>curious.py</code>).</p>
{compare}
"""
    for n in SPEC["motions"]:
        if cards[n]:
            html += f"<h2>{n}</h2><p>{SPEC['motions'][n]['desc']}</p>" + "".join(cards[n])
    (OUT_COMBINED / "index.html").write_text(html)
    print("wrote", OUT_COMBINED / "index.html")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--spec", default="spec.json"); ap.add_argument("--page", default="curious"); ap.add_argument("--header", default=None); ap.add_argument("--compare", default="")
    a = ap.parse_args()
    opened = a.no_open
    for r in SPEC["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        if a.only and a.only not in stem:
            continue
        render_pair(r["motion"], r["sound"], Path(r["wav"]), r["desc"])
        index()
        if not opened:
            subprocess.run(["open", str(OUT_COMBINED / "index.html")])
            opened = True
    index()
