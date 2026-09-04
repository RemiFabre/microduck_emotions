#!/usr/bin/env python
"""Sadness v2 / v3 (--v3): fewer, slower head swings, and the beak moves with the sound.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/sadness/v2.py [--only NAME] [--no-open]

Reads v2_spec.json (motion options with their beat times, and (motion, wav) pairs), builds each motion from the
decided `sad` / `devastated` envelopes with the shake window replaced by three yaw extremes at the spec's times,
drives the mouth (the real robot's `robot.mouth` intent, 0..1) from the wav's RMS envelope, renders the silent mp4
into motion/sadness/v2/, muxes the wav with combine.py into combined/v2/, and writes the keyframes json (head channels
+ `mouth`), a beats contact sheet, and combined/v2/index.html.
"""
import argparse, json, math, subprocess, sys, wave
from pathlib import Path

import imageio, mujoco, numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/Users/remi/microduck/notes/reachy-encounter")
import duckfilm as F
import sadness as S

VERSION = "v2"
for _i, _a in enumerate(sys.argv):
    if _a == "--v3":
        VERSION = "v3"
    if _a == "--version" and _i + 1 < len(sys.argv):
        VERSION = sys.argv[_i + 1]
LATER = VERSION != "v2"          # v3 onward: clip cut at the spec total, page opened on the first video, sad only
SPEC = json.load(open(HERE / f"{VERSION}_spec.json"))
# Extra option, not in the spec: the standing `sad` with body pitch +0.05 instead of +0.10. At +0.10 the stand net turns
# the head only one way (yaw joint ~0 at the + extremes), so "three swings" shows as one; at +0.05 it swings both ways.
for _n in [n for n in SPEC["motions"] if n.startswith("sad") and VERSION == "v2"]:
    SPEC["motions"][_n + "_bp05"] = dict(SPEC["motions"][_n], body_pitch=0.05, note="body pitch +0.05 (two-sided swings)")
SPEC["renders"] += [dict(r, motion=r["motion"] + "_bp05") for r in list(SPEC["renders"]) if r["motion"].startswith("sad") and VERSION == "v2"]
OUT_MOTION = HERE / VERSION
OUT_COMBINED = Path("/Users/remi/microduck/notes/emotions/combined") / VERSION
COMBINE = "/Users/remi/microduck/notes/emotions/combine.py"
PY = "/Users/remi/microduck/.venv-mjlab/bin/python"
YAW_AMP = 0.4
NECK, PITCH = -1.5, 1.0
BODY_PITCH = {"sad": 0.10, "devastated": 0.0}
ramp = S.ramp


# ---------------------------------------------------------------------------------------------------------------
# motion from the spec's beats
# ---------------------------------------------------------------------------------------------------------------
def make_motion(name):
    b = SPEC["motions"][name]
    base = b["base"]
    droop_len = b["droop_end"] - b["droop_start"]
    rise_len = b["head_level"] - b["rise_start"]
    ext = list(b["shake_extremes"])
    ss, se = b["shake_start"], b["shake_end"]
    bp = b.get("body_pitch", BODY_PITCH[base])
    # yaw targets at the knots: 0 at shake_start, +A, -A, +A ... at the extremes, 0 at shake_end
    knots = [ss] + ext + [se]
    vals = [0.0] + [YAW_AMP * (1 if i % 2 == 0 else -1) for i in range(len(ext))] + [0.0]

    def fn(t):
        down = ramp(t - b["droop_start"], droop_len) * (1.0 - ramp(t - b["rise_start"], rise_len))
        yaw = 0.0
        for i in range(len(knots) - 1):
            if knots[i] <= t < knots[i + 1]:
                yaw = vals[i] + (vals[i + 1] - vals[i]) * ramp(t - knots[i], knots[i + 1] - knots[i])
                break
        skill = "sit" if (b["sit"] is not None and t >= b["sit"]) else None
        return dict(neck=NECK * down, head_pitch=PITCH * down, head_yaw=yaw, head_roll=0.0, body_pitch=bp * down, skill=skill)
    return fn, b


# ---------------------------------------------------------------------------------------------------------------
# mouth from the wav: RMS envelope at 50 Hz (20 ms windows), ~60 ms smoothing, open = clip(rms / (0.6 max), 0, 1)
# ---------------------------------------------------------------------------------------------------------------
def mouth_envelope(wav_path):
    with wave.open(str(wav_path)) as w:
        sr, nch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, {2: np.int16, 4: np.int32}[sw]).astype(np.float32) / float(2 ** (8 * sw - 1))
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    win = int(round(sr * F.CDT))                       # 20 ms = one control tick
    n = len(x) // win
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1))
    rms = np.convolve(rms, np.ones(3) / 3, mode="same")   # 3 ticks = 60 ms
    open_ = np.clip(rms / (0.6 * rms.max()), 0.0, 1.0) if rms.max() > 0 else rms * 0
    return open_                                        # index k = tick k = t = k * CDT on the video clock


# ---------------------------------------------------------------------------------------------------------------
def render_pair(motion, sound, wav, desc, with_open=False):
    fn, b = make_motion(motion)
    env = mouth_envelope(wav)
    total = b["total"] if LATER else max(b["total"], len(env) * F.CDT)   # v3: the clip ends at the spec's total (the wav's tail is silence)
    m, d, du = S.fresh()
    r = mujoco.Renderer(m, S.SIZE[1], S.SIZE[0])
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0.03, 0.0, 0.11]
    cam.distance, cam.azimuth, cam.elevation = 0.60, 115, -6
    font = ImageFont.truetype(S.FONT, 15)
    frames, keys, log = [], [], []
    next_frame = 0.0
    n = int(round(total / F.CDT))
    for k in range(n):
        t = k * F.CDT
        h = fn(t)
        mouth = float(env[k]) if k < len(env) else 0.0
        du.head[:] = (h["neck"], h["head_pitch"], h["head_yaw"], h["head_roll"])
        du.body[:] = 0
        du.body[2] = h["body_pitch"]
        du.twist[:] = 0
        du.skill = h["skill"]
        du.mouth = mouth
        S.step(m, d, du, t)
        q = du.q()
        jd = {nm: float(q[F.HEAD_IDX[i]] - F.HOME[F.HEAD_IDX[i]]) for i, nm in enumerate(S.NAMES)}
        log.append(dict(t=round(t, 3), net=du.net, mouth=mouth, jaw=float(du.jaw_open / F.JAW_MAX), beak_z=float(du.beak_pos()[2]), **jd))
        if k % 5 == 0:
            keys.append(dict(t=round(t, 2), neck=round(h["neck"], 3), head_pitch=round(h["head_pitch"], 3), head_yaw=round(h["head_yaw"], 3),
                             head_roll=0.0, body_pitch=round(h["body_pitch"], 3), mouth=round(mouth, 3), skill=h["skill"]))
        if t >= next_frame - 1e-9:
            r.update_scene(d, camera=cam)
            img = Image.fromarray(r.render())
            dr = ImageDraw.Draw(img)
            txt = (f"{motion} + {sound}   t={t:4.1f}s   net={du.net}\n"
                   f"cmd  neck {h['neck']:+.2f}  pitch {h['head_pitch']:+.2f}  yaw {h['head_yaw']:+.2f}  body_pitch {h['body_pitch']:+.2f}  mouth {mouth:.2f}\n"
                   f"joint neck {jd['neck_pitch']:+.2f}  pitch {jd['head_pitch']:+.2f}  yaw {jd['head_yaw']:+.2f}  jaw {du.jaw_open / F.JAW_MAX:.2f}")
            dr.multiline_text((8, 6), txt, font=font, fill="white", stroke_width=2, stroke_fill="black", spacing=2)
            # a little mouth meter, bottom left
            dr.rectangle([8, S.SIZE[1] - 18, 8 + 120, S.SIZE[1] - 8], outline="white")
            dr.rectangle([8, S.SIZE[1] - 18, 8 + int(120 * mouth), S.SIZE[1] - 8], fill=(255, 200, 60))
            dr.text((134, S.SIZE[1] - 22), "mouth", font=font, fill="white", stroke_width=2, stroke_fill="black")
            if du.fell_at is not None:
                dr.text((8, S.SIZE[1] - 44), "FELL", font=font, fill=(255, 60, 60), stroke_width=2, stroke_fill="black")
            frames.append(np.asarray(img))
            next_frame += 1.0 / S.FPS
    OUT_MOTION.mkdir(exist_ok=True)
    OUT_COMBINED.mkdir(parents=True, exist_ok=True)
    stem = f"{motion}__{sound}"
    silent = OUT_MOTION / f"{stem}.mp4"
    imageio.mimwrite(str(silent), frames, fps=S.FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=8,
                     output_params=["-crf", "20", "-movflags", "+faststart"])
    combined = OUT_COMBINED / f"{stem}.mp4"
    subprocess.run([PY, COMBINE, str(silent), str(wav), str(combined), "--at", "0"], check=True)
    # measurements
    hp = np.array([l["head_pitch"] for l in log]); nk = np.array([l["neck_pitch"] for l in log]); yw = np.array([l["head_yaw"] for l in log])
    jaw = np.array([l["jaw"] for l in log]); mo = np.array([l["mouth"] for l in log])
    at = lambda t: min(log, key=lambda l: abs(l["t"] - t))
    ext = [at(e)["head_yaw"] for e in b["shake_extremes"]]
    # count the yaw swings actually made (sign changes of the joint beyond 0.1 rad)
    sgn = np.sign(np.where(np.abs(yw) > 0.15, yw, 0))
    sgn = sgn[sgn != 0]
    swings = int(1 + np.sum(sgn[1:] != sgn[:-1])) if len(sgn) else 0
    silent_ticks = mo < 0.05
    meas = dict(motion=motion, sound=sound, wav=str(wav), desc=desc, duration_s=round(total, 2), fell=du.fell_at is not None, fell_at=du.fell_at,
                head_pitch_joint_max_deg=round(math.degrees(hp.max()), 1), neck_joint_min_deg=round(math.degrees(nk.min()), 1),
                yaw_joint_at_extremes=[round(float(v), 2) for v in ext], yaw_swings_measured=swings,
                head_down_fraction_at_first_extreme=round(float(at(b["shake_extremes"][0])["head_pitch"] / hp.max()), 2),
                mouth_open_max=round(float(mo.max()), 2), mouth_open_ticks=int((mo > 0.3).sum()),
                jaw_open_max=round(float(jaw.max()), 2), jaw_in_silence_max=round(float(jaw[silent_ticks].max()), 2) if silent_ticks.any() else None,
                sound_first_open_s=round(float(np.argmax(mo > 0.3) * F.CDT), 2), beats=b)
    json.dump(dict(keyframes=keys, measured=meas, fps=S.FPS), open(OUT_MOTION / f"{stem}.json", "w"), indent=1)
    json.dump(log, open(OUT_MOTION / f"{stem}.log.json", "w"))
    beats_sheet(stem, frames, b, log, mo)
    print(f"{stem}: {total:.1f} s fell={meas['fell']} swings={swings} yaw@extremes={meas['yaw_joint_at_extremes']} head down at e1 {meas['head_down_fraction_at_first_extreme']:.0%} "
          f"mouth first opens {meas['sound_first_open_s']} s, jaw max {meas['jaw_open_max']:.2f}, jaw in silence max {meas['jaw_in_silence_max']}")
    return meas


def beats_sheet(stem, frames, b, log, mo):
    times = [(b["sit"] + 0.9 if b["sit"] is not None else 0.0, "seated" if b["sit"] is not None else "start"), (b["droop_start"] + 0.5, "droop")]
    times += [(x, f"swing {i + 1}") for i, x in enumerate(b["shake_extremes"])]
    times += [(b["shake_end"], "shake end"), (b["rise_start"] + 1.0, "rising"), (b["head_level"], "level")]
    # the three loudest moments (local maxima of the mouth envelope, at least 0.6 s apart) and one silence
    peaks = []
    order = np.argsort(-mo)
    for i in order:
        t = i * F.CDT
        if mo[i] < 0.3:
            break
        if all(abs(t - p) > 0.6 for p in peaks):
            peaks.append(t)
        if len(peaks) == 3:
            break
    times += [(p, "sound peak") for p in sorted(peaks)]
    W, H = S.SIZE
    cols, rows = 6, 2
    out = Image.new("RGB", (cols * W // 2 + 8 * (cols + 1), rows * H // 2 + 8 * (rows + 1) + 24), (30, 30, 34))
    dr = ImageDraw.Draw(out)
    font = ImageFont.truetype(S.FONT, 14)
    for k, (t, lab) in enumerate(times[:cols * rows]):
        i = min(len(frames) - 1, int(round(t * S.FPS)))
        l = min(log, key=lambda r_: abs(r_["t"] - t))
        im = Image.fromarray(frames[i]).resize((W // 2, H // 2))
        x = 8 + (k % cols) * (W // 2 + 8)
        y = 8 + (k // cols) * (H // 2 + 8)
        out.paste(im, (x, y))
        dr.text((x + 4, y + H // 2 - 34), f"t = {t:.2f} s  {lab}", font=font, fill="white", stroke_width=2, stroke_fill="black")
        dr.text((x + 4, y + H // 2 - 18), f"pitch {l['head_pitch']:+.2f} neck {l['neck_pitch']:+.2f} yaw {l['head_yaw']:+.2f} jaw {l['jaw']:.2f}", font=font,
                fill=(255, 230, 120), stroke_width=2, stroke_fill="black")
    dr.text((8, out.height - 20), f"{stem}: frames at the beats and at the three loudest moments of the sound", font=font, fill="white")
    out.save(OUT_MOTION / f"{stem}_beats.png")


# ---------------------------------------------------------------------------------------------------------------
def index():
    cards = {"sad": [], "devastated": []}
    for r in SPEC["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        p = OUT_MOTION / f"{stem}.json"
        if not p.exists():
            continue
        m = json.load(open(p))["measured"]
        b = m["beats"]
        emo = b["base"]
        beats = (f"sit {b['sit']} s &middot; " if b["sit"] is not None else "") + \
                f"droop {b['droop_start']}-{b['droop_end']} s &middot; swings at {', '.join(str(x) for x in b['shake_extremes'])} s (shake {b['shake_start']}-{b['shake_end']}) &middot; hold to {b['hold_end']} &middot; rise {b['rise_start']}-{b['head_level']} s &middot; {m['duration_s']} s"
        cards[emo].append(f"""
<div class="card">
  <h3>{r['motion']} + {r['sound']}{' &nbsp;<span class="note">option: ' + b['note'] + '</span>' if b.get('note') else ''}</h3>
  <video src="{stem}.mp4" controls playsinline width="640" height="480"></video>
  <p class="beats"><b>beats:</b> {beats}</p>
  <p class="snd"><b>sound:</b> {r['desc']}</p>
  <p class="meas">measured: {'FELL' if m['fell'] else 'no fall'} &middot; {m['yaw_swings_measured']} swings (yaw joint at the extremes {m['yaw_joint_at_extremes']}) &middot;
     head {m['head_down_fraction_at_first_extreme']:.0%} down at the first swing &middot; head_pitch {m['head_pitch_joint_max_deg']:+.0f} deg, neck {m['neck_joint_min_deg']:+.0f} deg &middot;
     mouth first opens at {m['sound_first_open_s']} s, jaw max {m['jaw_open_max']:.2f}, in silence {m['jaw_in_silence_max']}</p>
  <p><a href="../../motion/sadness/v2/{stem}_beats.png">beats sheet</a> &middot; <a href="../../motion/sadness/v2/{stem}.json">keyframes json (with mouth)</a> &middot; <a href="../../motion/sadness/v2/{stem}.mp4">silent mp4</a></p>
  <img class="sheet" src="../../motion/sadness/v2/{stem}_beats.png">
</div>""")
    if VERSION == "v4":
        intro = {"sad": "Standing, body pitch +0.05. One continuous sound from the start to the end of the head going DOWN, descending with the head "
                        "(as if the pain were felt as the head lowers); the two side-to-side swings are SILENT. Two droop speeds: 2.0 s (swings 2.6 / 3.8 s, 7.8 s) "
                        "and 2.5 s (swings 3.1 / 4.3 s, 8.3 s). The beak follows the sound's loudness, so it opens during the droop and is shut for the swings.",
                 "devastated": ""}
    elif VERSION == "v3":
        intro = {"sad": "Standing, body pitch +0.05 (both swing directions visible). Shorter and softer than v2: two swings 1.2 s or 1.0 s apart, or ONE slow swing; "
                        "everything ends by 6.6-7.0 s. The sound (2.2-2.7 s) starts at the end of the tilt; the beak follows its loudness and shuts after it.",
                 "devastated": ""}
    else:
        intro = {"sad": "Standing. Three slow head swings, the sound starts only once the tilt is nearly finished. Options: 1.3 s or 1.6 s between swings. "
                    "NOTE: with the decided body pitch +0.10 the stand net turns the head only one way (the yaw joint stays near 0 on the + side), so the three "
                    "commanded swings show as ONE visible swing; the <b>_bp05</b> cards (body pitch +0.05, everything else identical) swing both ways and are the ones to compare.",
             "devastated": "With the sit. Three swings starting while the head is still going down. Options: 1.0 s or 1.3 s between swings."}
    html = f"""<!doctype html><meta charset="utf-8"><title>Microduck sadness v2: sound + motion</title>
<style>
body{{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:24px;background:#f6f4ef;color:#222;max-width:1400px}}
h1{{margin-bottom:4px}} .sub{{color:#666;margin-top:0}} h2{{margin-top:36px}}
.card{{background:#fff;border-radius:10px;padding:16px 20px;margin:18px 0;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.card h3{{margin:0 0 8px}} .note{{font-size:13px;color:#b06000;font-weight:normal}} .beats,.snd,.meas{{font-size:14px;margin:6px 0}} .meas{{color:#555}}
.sheet{{width:100%;max-width:1360px;margin-top:10px;border-radius:6px}}
video{{background:#000;border-radius:6px}} .decided{{background:#fff8e6;border:2px solid #e9b949;border-radius:8px;padding:10px 14px}}
</style>
<h1>Microduck sadness {VERSION}: sound + motion, re-synced</h1>
{'<p class="decided"><b>Devastated is decided</b> (devastated_3x1.0 + D3v2_sobs_gentler, see <a href="../v2/index.html">v2</a>). This page is SAD only, v3: shorter (about half of v2) and softer.</p>' if VERSION == "v3" else ''}
{'<p class="decided"><b>sad v4: the sound descends with the head, the shakes are silent.</b> Devastated is decided (devastated_3x1.0 + D3v2_sobs_gentler). Previous round: <a href="../v3/index.html">v3</a>.</p>' if VERSION == "v4" else ''}
<p class="sub">Remi's notes: three swings not four; sad slower and its sound only once the tilt is nearly done; the beak moves with the sound.
The mouth is driven by the wav's loudness (RMS at 50 Hz, 60 ms smoothing, fully open at 60% of the peak) through the same mouth intent the robot accepts.
Simulation (640x480, 30 fps). Motions and json: <code>/Users/remi/microduck/notes/emotions/motion/sadness/v2/</code>. Spec: <code>v2_spec.json</code>.</p>
"""
    for emo in ("devastated", "sad"):
        if cards[emo]:
            html += f"<h2>{emo}</h2><p>{intro[emo]}</p>" + "".join(cards[emo])
    (OUT_COMBINED / "index.html").write_text(html)
    print("wrote", OUT_COMBINED / "index.html")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="substring filter on motion__sound")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--v3", action="store_true", help="shorthand for --version v3")
    ap.add_argument("--version", default="v2", help="vN: use vN_spec.json and the vN output folders (default: v2)")
    a = ap.parse_args()
    opened = a.no_open
    for r in SPEC["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        if a.only and a.only not in stem:
            continue
        render_pair(r["motion"], r["sound"], Path(r["wav"]), r["desc"])
        index()
        if not opened and (r["motion"].startswith("devastated") or LATER):
            subprocess.run(["open", str(OUT_COMBINED / "index.html")])
            opened = True
    index()
