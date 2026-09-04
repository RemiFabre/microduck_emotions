"""v2 of the motion-synced sad sounds, after Rémi's listening notes (2026-09-04 afternoon):
- devastated: keep D3 (inquire shock + separate sobs) but THREE sobs, the third one dying into the ending;
  shock and sobs at the same level; gentler overall.
- sad: keep S1 (continuous glide) but start only when the head tilt is (almost) finished, shorter, three
  slower slides, less energy (softer, slower, lower).
- both: three head swings instead of four, so the motion is re-rendered on the beats below, and the beak
  opens with the sound (the renderer reads the wav).

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced_v2.py

Writes sounds/synced_v2/<motion_option>__<sound>.wav and motion/sadness/v2_spec.json (beats + which wav
goes with which motion option), for the motion renderer.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from quack import ROBOT_SEED, SR, Personality, bell, normalise, quack, read_wav, t_axis, write_wav  # noqa: E402

BANK = Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059")
OUT = HERE / "synced_v2"
p = Personality(ROBOT_SEED)
ST = 2 ** (1 / 12)
GENTLE = dict(quackiness=0.35, breath=0.12, vibrato_rate_hz=3.2, vibrato_depth=0.4, attack_sharpness=0.0, tilt=2.3, am_depth=0.15)
GENTLER = dict(quackiness=0.28, breath=0.10, vibrato_rate_hz=2.7, vibrato_depth=0.35, attack_sharpness=0.0, tilt=2.5, am_depth=0.12)

# ----------------------------------------------------------------------------- motion options (beats)
# Three head extremes each. devastated: sit at 0.3, droop 1.8-3.8, shake starts at half droop (2.8).
# sad: droop 0-2.0, shake starts after the droop, sound starts when the tilt is almost finished (1.8).
MOTIONS = {
    "devastated_3x1.0": dict(base="devastated", sit=0.3, droop_start=1.8, droop_end=3.8, shake_start=2.8,
                             shake_extremes=[3.3, 4.3, 5.3], shake_end=5.8, hold_end=6.8, rise_start=6.8, head_level=8.8, total=9.6),
    "devastated_3x1.3": dict(base="devastated", sit=0.3, droop_start=1.8, droop_end=3.8, shake_start=2.8,
                             shake_extremes=[3.45, 4.75, 6.05], shake_end=6.7, hold_end=7.5, rise_start=7.5, head_level=9.5, total=10.3),
    "sad_3x1.3": dict(base="sad", sit=None, droop_start=0.0, droop_end=2.0, shake_start=2.0,
                      shake_extremes=[2.65, 3.95, 5.25], shake_end=5.9, hold_end=6.6, rise_start=6.6, head_level=8.6, total=9.4),
    "sad_3x1.6": dict(base="sad", sit=None, droop_start=0.0, droop_end=2.0, shake_start=2.0,
                      shake_extremes=[2.8, 4.4, 6.0], shake_end=6.8, hold_end=7.5, rise_start=7.5, head_level=9.5, total=10.3),
}


def semis(hz, n):
    return hz * ST ** n


def db(x, d):
    return x * 10 ** (d / 20)


class Track:
    def __init__(self, total_s):
        self.buf = np.zeros(int(total_s * SR) + SR)

    def put(self, t, sig):
        i = int(t * SR)
        n = min(len(sig), len(self.buf) - i)
        self.buf[i:i + n] += sig[:n]


def sobs(ex, hold_end, f_hi, drop, step, attack, mods, level_step=-1.5):
    """Three separate soft glides, one per head extreme; the last one dies through the hold."""
    period = ex[1] - ex[0]
    parts = []
    for i, te in enumerate(ex):
        hi = semis(f_hi, -step * i)
        lo = semis(hi, -drop)
        last = i + 1 == len(ex)
        dur = (hold_end - te) if last else period * 0.9
        contour = [(0.0, hi), (dur, lo)] if not last else [(0.0, hi), (period * 0.9, lo), (dur, semis(lo, -3))]
        sig = quack(p, dur, contour, ("bell", attack, dur * (0.6 if last else 0.45)), mods=mods)
        parts.append((te, db(normalise(sig, -3.0), level_step * i)))
    return parts


def continuous(ex, hold_end, t_start, f_start, f_hi, drop, step, mods):
    """One unbroken tone from t_start: a lead slide into the first extreme, then one eased slide per swing,
    the last dying through the hold."""
    period = ex[1] - ex[0]
    pts = [(t_start, f_start)]
    for i, te in enumerate(ex):
        hi = semis(f_hi, -step * i)
        lo = semis(hi, -drop)
        pts.append((te, hi))
        if i + 1 < len(ex):
            pts.append((ex[i + 1] - 0.2, lo))
        else:
            pts.append((hold_end, semis(lo, -3)))
    dur = hold_end - t_start
    t = t_axis(dur)
    freq = np.interp(t + t_start, [q[0] for q in pts], [q[1] for q in pts])
    env = bell(t, 0.5, hold_end - ex[-1])
    swing = 1.0 - 0.2 * (0.5 + 0.5 * np.cos(2 * np.pi * (t + t_start - ex[0]) / period)) ** 2
    env = env * np.where(t + t_start > ex[0], swing, 1.0)
    return t_start, quack(p, dur, freq, env, mods=mods)


def shock_inquire(level_db=-3.0):
    return normalise(read_wav(BANK / "inquire" / "inquire_b.wav")[1], level_db)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        ex = b["shake_extremes"]
        tracks = []
        if b["base"] == "devastated":
            # D3 lineage: inquire shock at the sit, same peak as the sobs; three sobs; gentler than v1
            tr = Track(b["total"]); tr.put(b["sit"], shock_inquire(-3.0))
            for t, s in sobs(ex, b["hold_end"], 235.0, 3.5, 1.5, 0.25, GENTLE): tr.put(t, s)
            tracks.append(("D3v2_sobs", tr, -3.0, "inquire shock at the sit (same peak as the sobs), three soft sobs, the third dying into the ending; gentler voice than D3"))
            tr = Track(b["total"]); tr.put(b["sit"], shock_inquire(-3.0))
            for t, s in sobs(ex, b["hold_end"], 210.0, 3.0, 1.5, 0.32, GENTLER): tr.put(t, s)
            tracks.append(("D3v2_sobs_gentler", tr, -3.0, "same layout, lower (210 Hz start), smaller slides (3 semitones), slower swell, even less buzz"))
        else:
            # S1 lineage: starts when the tilt is almost finished, three slow slides, soft
            t0 = b["droop_end"] - 0.2
            tr = Track(b["total"]); tr.put(*continuous(ex, b["hold_end"], t0, 235.0, 225.0, 3.0, 1.5, GENTLE))
            tracks.append(("S1v2_glide", tr, -8.0, "one unbroken soft glide starting at the end of the tilt, three slow slides (3 semitones each), dying in the hold; peak -8 dBFS (quieter than devastated)"))
            tr = Track(b["total"]); tr.put(*continuous(ex, b["hold_end"], t0, 215.0, 205.0, 2.5, 1.2, GENTLER))
            tracks.append(("S1v2_glide_gentler", tr, -10.0, "same, lower (205 Hz), smaller slides (2.5 semitones), slowest vibrato, peak -10 dBFS"))
        for sname, tr, peak, desc in tracks:
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, peak)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    json.dump(spec, open(ROOT / "motion" / "sadness" / "v2_spec.json", "w"), indent=1)
    print(ROOT / "motion" / "sadness" / "v2_spec.json")


if __name__ == "__main__":
    main()
