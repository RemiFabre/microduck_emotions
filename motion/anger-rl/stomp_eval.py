#!/usr/bin/env python
"""Angry-stomp evaluation: CPU-proxy battery + stomp analysis of any rollout log (CPU proxy or Warp gt_eval) + page.

  # CPU proxy (exact training model via mjlab, BAM servo, 1.75 A, delay 3-6, jvel lag 1), N seeds:
  stomp_eval.py proxy --onnx policy.onnx --out DIR [--seeds 0 1 2 3 4] [--delay 3 6] [--push 0,0.1@1.6]
  # analyse every <name>.json in DIR (proxy or Warp logs) -> <name>.stomp.json + <name>_sheet.png + index.html
  stomp_eval.py analyze DIR [--title T] [--open]

Stomp = the right-foot site rises >= LIFT_MIN above its rest height and then touches the floor again.
Per stomp: lift height (mm), down-speed just before touchdown (m/s, from the site z at 50 Hz), head yaw at
touchdown (rad, + = left), time. Per rollout: stomps, max joint speed (rad/s, 50 Hz finite difference of q),
support-foot lifted fraction, fall, end state (upright, both feet down, head centred, |q - HOME| max).
Run under /Users/remi/microduck/.venv-mjlab with PYTHONPATH=/Users/remi/microduck/microduck_rl/src.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path
import numpy as np

TOOLS = Path("/Users/remi/microduck/notes/tools"); sys.path.insert(0, str(TOOLS))
HOME = np.array([0.0, -0.0873, -0.4579, -0.0049, 0.4530, 0.3491, 0.3491, 0.0, 0.0, 0.0, 0.0873, 0.4579, 0.0049, -0.4530])
LIFT_MIN = 0.02      # m: success threshold of the design
TASK = "Mjlab-Stomp-Flat-MicroDuck"
BASE = Path("/Users/remi/microduck/microduck/policies/alpha_stand.onnx")


def analyze_log(log, foot="right", trick_only=True):
    # Warp logs carry the episode reset tick (done=1) -> cut there, or joint "speeds" read the qpos jump
    dones = [i for i, l in enumerate(log) if l.get("done")]
    if dones: log = log[:dones[0]]          # the done tick already holds the NEXT spawn (mjlab resets inside step)
    dt = log[1]["t"] - log[0]["t"]
    zk, fk = ("rz", "rf") if foot == "right" else ("lz", "lf")
    ok, of = ("lz", "lf") if foot == "right" else ("rz", "rf")
    win = [l for l in log if l.get("trick", 1)] if trick_only else log
    if not win: win = log
    t = np.array([l["t"] for l in win]); z = np.array([l[zk] for l in win]); f = np.array([l[fk] for l in win])
    q = np.array([l["q"] for l in win]); yaw = q[:, 7]
    z0 = float(np.median(np.array([l[zk] for l in log[:5]])))
    zr = z - z0
    stomps, i, n = [], 0, len(win)
    while i < n:
        if zr[i] >= LIFT_MIN:
            j = i
            while j < n and zr[j] > 0.005: j += 1           # back near the floor
            k = j
            while k < n and not f[k]: k += 1                # touchdown (contact)
            seg = slice(i, min(k + 1, n))
            peak = int(i + np.argmax(zr[seg]))
            down = -(np.diff(z[peak:min(k + 1, n)]) / dt) if k > peak else np.array([0.0])
            td = min(k, n - 1)
            stomps.append(dict(t_lift=round(float(t[i]), 2), t_touch=round(float(t[td]), 2),
                               lift_mm=round(float(zr[peak]) * 1000, 1),
                               down_speed=round(float(down.max()) if len(down) else 0.0, 2),
                               yaw_at_touch=round(float(yaw[td]), 2),
                               yaw_peak=round(float(yaw[max(0, td - 8):td + 8][np.argmax(np.abs(yaw[max(0, td - 8):td + 8]))]), 2),
                               touched=bool(k < n)))
            i = k + 1
        else:
            i += 1
    qd = np.abs(np.diff(np.array([l["q"] for l in log]), axis=0) / dt)
    gz = np.array([l["gz"] for l in log]); tilt = np.array([l["tilt"] for l in log])
    fell = bool((gz > -0.5).any() or (tilt > 0.85).any())
    end = log[-1]
    out = dict(n_stomps=len(stomps), stomps=stomps,
               max_joint_speed=round(float(qd.max()), 2), max_joint_speed_joint=int(np.unravel_index(qd.argmax(), qd.shape)[1]),
               support_lifted_frac=round(float(np.mean([1 - l[of] for l in win])), 3),
               support_lift_mm=round(float((max(l[ok] for l in win) - np.median([l[ok] for l in log[:5]])) * 1000), 1),
               max_tilt=round(float(tilt.max()), 3), fell=fell,
               end_upright=bool(end["gz"] < -0.9), end_two_feet=bool(end["lf"] and end["rf"]),
               end_head_yaw=round(float(end["q"][7]), 2), end_pose_dev=round(float(np.abs(np.array(end["q"]) - HOME).max()), 2),
               end_z=round(float(end["z"]), 3),
               yaw_range=[round(float(yaw.min()), 2), round(float(yaw.max()), 2)],
               window=[round(float(t[0]), 2), round(float(t[-1]), 2)])
    out["verdict"] = ("FELL" if fell else f"{len(stomps)} stomp(s)" +
                      (", hop" if out["support_lifted_frac"] > 0.1 else "") +
                      ("" if out["end_upright"] and out["end_two_feet"] else ", bad end"))
    return out


def contact_sheet(mp4, times, duration, out_png, cols=None):
    import imageio
    from PIL import Image, ImageDraw
    rd = imageio.get_reader(str(mp4)); frames = [fr for fr in rd]; rd.close()
    if not frames: return None
    fps = len(frames) / duration
    picks = [frames[min(len(frames) - 1, max(0, int(round(tt * fps))))] for tt in times]
    h, w = picks[0].shape[:2]; cols = cols or len(picks); rows = int(np.ceil(len(picks) / cols))
    sheet = Image.new("RGB", (cols * w, rows * h), "white"); dr = ImageDraw.Draw(sheet)
    for i, (fr, tt) in enumerate(zip(picks, times)):
        im = Image.fromarray(fr); sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        dr.text(((i % cols) * w + 8, (i // cols) * h + 8), f"t={tt:.2f}s", fill=(255, 40, 40))
    sheet.save(out_png); return out_png


def cmd_proxy(a):
    import duck_rollout as dr
    dr.MJLAB_TASK = a.task; dr.BAM_SPEC_EDITS = True; dr.RENDER_SIZE = (640, 480)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pushes = []
    for pu in a.push:
        v, tt = pu.split("@"); vx, vy = (float(x) for x in v.split(",")); pushes.append((float(tt), vx, vy))
    for s in a.seeds:
        name = f"proxy_seed{s}" + ("_push" if pushes else "")
        t0 = time.perf_counter()
        st, log = dr.rollout(a.onnx if a.direct else BASE, out / f"{name}.mp4", scene="scene.xml", duration=a.seconds,
                             actuator="bam", current_limit=a.current_limit, delay=tuple(a.delay), jvel_lag=1,
                             trick=None if a.direct else (Path(a.onnx), a.t_start, a.t_dur), init_joint_noise=a.joint_noise,
                             seed=s, pushes=pushes, azimuth=a.azimuth, elevation=-12.0)
        if a.direct:
            for l in log: l["trick"] = int(l["t"] < a.t_dur)
        st["wall_s"] = round(time.perf_counter() - t0, 1)
        json.dump({"engine": "cpu-proxy", "task": a.task, "onnx": str(a.onnx), "seed": s, "delay": list(a.delay),
                   "current_limit": a.current_limit, "pushes": pushes, "trick_t": [a.t_start, a.t_dur], "stats": st, "log": log},
                  open(out / f"{name}.json", "w"))
        an = analyze_log(log); print(f"{name:18s} {an['verdict']:22s} stomps={[(x['lift_mm'], x['down_speed'], x['yaw_at_touch']) for x in an['stomps']]} maxqd={an['max_joint_speed']}", flush=True)


HTML = """<!doctype html><meta charset=utf-8><title>{title}</title>
<style>body{{font:14px -apple-system,Helvetica,sans-serif;margin:16px;background:#fafafa}} .card{{display:inline-block;vertical-align:top;margin:8px;padding:8px;background:#fff;border:1px solid #ddd;border-radius:6px;width:660px}}
video{{width:640px;display:block}} img{{max-width:640px;display:block;margin-top:4px}} pre{{font-size:11px;white-space:pre-wrap;background:#f4f4f4;padding:6px}} h1{{font-size:18px}} .v{{font-weight:bold;color:#a33}} .ok{{color:#282}}</style>
<h1>{title}</h1><p>{intro}</p>{cards}"""


def cmd_analyze(a):
    d = Path(a.dir).resolve(); cards = []; summary = []
    for js in sorted(d.glob("*.json")):
        if js.name.endswith(".stomp.json") or not (d / (js.stem + ".mp4")).exists(): continue
        doc = json.load(open(js)); log = doc["log"]
        if "trick" not in log[0]:
            for l in log: l["trick"] = 1
        an = analyze_log(log); json.dump(an, open(d / f"{js.stem}.stomp.json", "w"), indent=1)
        dur = log[-1]["t"] + (log[1]["t"] - log[0]["t"])
        times = [s["t_touch"] for s in an["stomps"]] or []
        base_t = [l["t"] for l in log if l.get("trick")][0] if any(l.get("trick") for l in log) else 0.0
        sheet_times = sorted(set([round(base_t, 2)] + [round(s["t_lift"] + (s["t_touch"] - s["t_lift"]) / 2, 2) for s in an["stomps"]] + times + [round(log[-1]["t"], 2)]))[:8]
        png = contact_sheet(d / (js.stem + ".mp4"), sheet_times, dur, d / f"{js.stem}_sheet.png", cols=4)
        meta = {k: doc[k] for k in doc if k not in ("stats", "log")}
        cls = "ok" if (an["n_stomps"] >= 3 and not an["fell"] and an["end_upright"]) else "v"
        cards.append(f"<div class=card><b>{js.stem}</b> <span class={cls}>{an['verdict']}</span><br><small>{json.dumps(meta)}</small>"
                     f"<video src='{js.stem}.mp4' controls autoplay loop muted></video>" + (f"<img src='{png.name}'>" if png else "") +
                     f"<pre>{json.dumps({k: v for k, v in an.items()}, indent=1)}</pre></div>")
        summary.append((js.stem, an["verdict"], [(s['lift_mm'], s['down_speed'], s['yaw_at_touch']) for s in an['stomps']], an["max_joint_speed"], an["fell"]))
    page = d / "index.html"
    page.write_text(HTML.format(title=a.title or f"angry stomp · {d.name}", intro=a.intro, cards="".join(cards)))
    for s in summary: print(*s)
    print(f"{page}: {len(cards)} cards")
    if a.open: subprocess.run(["open", str(page)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("proxy"); p.add_argument("--onnx", required=True); p.add_argument("--out", required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4]); p.add_argument("--task", default=TASK)
    p.add_argument("--delay", type=int, nargs=2, default=(3, 6)); p.add_argument("--current-limit", type=float, default=1.75)
    p.add_argument("--seconds", type=float, default=5.0); p.add_argument("--t-start", type=float, default=1.0); p.add_argument("--t-dur", type=float, default=3.0)
    p.add_argument("--joint-noise", type=float, default=0.03); p.add_argument("--push", action="append", default=[])
    p.add_argument("--direct", action="store_true", help="run the stomp ONNX from t=0 (no stand policy entry)")
    p.add_argument("--azimuth", type=float, default=150.0)
    p.set_defaults(fn=cmd_proxy)
    p = sub.add_parser("analyze"); p.add_argument("dir"); p.add_argument("--title", default=None); p.add_argument("--intro", default="")
    p.add_argument("--open", action="store_true"); p.set_defaults(fn=cmd_analyze)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
