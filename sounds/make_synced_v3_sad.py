"""v3 of the SAD sound (devastated is decided: devastated_3x1.0 + D3v2_sobs_gentler). Rémi on v2 sad:
"the sound starts at the right moment now, but it's still too intense and waaay too long (like 2x)".
So: about 2 s of sound instead of 4.5, fewer swings (two, or one slow swing), lower, softer, smaller slides.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced_v3_sad.py

Writes sounds/synced_v3/*.wav and motion/sadness/v3_spec.json (beats + pairs) for the renderer.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import SR, bell, quack, t_axis, write_wav  # noqa: E402
from make_synced_v2 import GENTLER, Track, p, semis  # noqa: E402

OUT = HERE / "synced_v3"
SOFTEST = dict(GENTLER, breath=0.08, vibrato_depth=0.25, vibrato_rate_hz=2.4, quackiness=0.25)

# sad motions, body pitch 0.05 (the stand net shakes both ways at 0.05, one way at 0.10), droop 0-2 s,
# sound starts at 1.9 s when the tilt is nearly finished. Everything shorter than v2.
MOTIONS = {
    "sad_2x1.2": dict(base="sad", body_pitch=0.05, sit=None, droop_start=0.0, droop_end=2.0, shake_start=2.0,
                      shake_extremes=[2.6, 3.8], shake_end=4.4, hold_end=5.0, rise_start=5.0, head_level=7.0, total=7.8),
    "sad_2x1.0": dict(base="sad", body_pitch=0.05, sit=None, droop_start=0.0, droop_end=2.0, shake_start=2.0,
                      shake_extremes=[2.5, 3.5], shake_end=4.0, hold_end=4.8, rise_start=4.8, head_level=6.8, total=7.6),
    "sad_1x_slow": dict(base="sad", body_pitch=0.05, sit=None, droop_start=0.0, droop_end=2.0, shake_start=2.0,
                        shake_extremes=[2.8], shake_end=3.8, hold_end=4.6, rise_start=4.6, head_level=6.6, total=7.4),
}


def glide(t_start, t_end, pts, mods, attack=0.35, release=0.7):
    """One soft tone from t_start to t_end following (time, hz) points."""
    dur = t_end - t_start
    t = t_axis(dur)
    freq = np.interp(t + t_start, [q[0] for q in pts], [q[1] for q in pts])
    return t_start, quack(p, dur, freq, bell(t, attack, release), mods=mods)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    t0 = 1.9
    for mname, b in MOTIONS.items():
        ex = b["shake_extremes"]
        tracks = []
        if len(ex) == 2:
            e1, e2 = ex
            end = e2 + 0.8
            # two slides: lead-in, slide 1 from extreme 1, slide 2 from extreme 2 dying
            pts = [(t0, 205), (e1, 200), (e2 - 0.2, semis(200, -2.5)), (e2, semis(200, -1.5)), (end, semis(200, -5))]
            tr = Track(b["total"]); tr.put(*glide(t0, end, pts, GENTLER))
            tracks.append(("S3_two_slides", tr, -12.0, f"{end - t0:.1f} s: soft low glide from the end of the tilt, one small slide per swing (2.5 semitones), dying; peak -12 dBFS"))
            pts = [(t0, 190), (e1, 185), (e2, semis(185, -2)), (end, semis(185, -4.5))]
            tr = Track(b["total"]); tr.put(*glide(t0, end, pts, SOFTEST, attack=0.45, release=0.9))
            tracks.append(("S3_one_sigh", tr, -14.0, f"{end - t0:.1f} s: a single slow sigh (190 -> ~145 Hz) across both swings, softest voice; peak -14 dBFS"))
        else:
            e1 = ex[0]
            end = e1 + 1.3
            pts = [(t0, 200), (e1, 195), (end, semis(195, -4))]
            tr = Track(b["total"]); tr.put(*glide(t0, end, pts, SOFTEST, attack=0.4, release=0.8))
            tracks.append(("S3_one_sigh", tr, -13.0, f"{end - t0:.1f} s: one slow sigh on the single swing; peak -13 dBFS"))
            pts = [(t0, 215), (t0 + 0.5, 210), (e1, semis(210, -2)), (end, semis(210, -5))]
            tr = Track(b["total"]); tr.put(*glide(t0, end, pts, GENTLER, attack=0.3, release=0.7))
            tracks.append(("S3_one_sigh_higher", tr, -12.0, f"{end - t0:.1f} s: same, a little higher (210 Hz) and clearer; peak -12 dBFS"))
        for sname, tr, peak, desc in tracks:
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, peak)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname, desc)
    json.dump(spec, open(ROOT / "motion" / "sadness" / "v3_spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
