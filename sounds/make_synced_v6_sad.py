"""v6 SAD sound. Rémi on v5 (coo raised + granular stretch): "they feel like two sounds mixed together or
very robotic; the previous version was better". The granular stretch is the culprit. v6 keeps the coo
CHARACTER but synthesizes it: the robot's own `coo` recipe (sounds/src/voices.rs) applied to a glide of
any length and pitch, so there is no stretching at all. Plus one tape-only variant from the wheee loop,
the only bank sound long enough to cover the droop in register without stretching.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced_v6_sad.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, bell, quack, read_wav, t_axis, write_wav  # noqa: E402
from make_synced import varispeed, fade  # noqa: E402
from make_synced_v2 import Track  # noqa: E402
from make_synced_v4_sad import MOTIONS, ramp  # noqa: E402

OUT = HERE / "synced_v6"
p = Personality(ROBOT_SEED)
ST = 2 ** (1 / 12)
# The robot's coo recipe, exactly as voices.rs softens the personality for `coo`:
COO = dict(breath=max(p.breath, 0.12) + 0.10, quackiness=p.quackiness * 0.25, am_rate_hz=p.am_rate_hz * 0.30,
           vibrato_rate_hz=p.vibrato_rate_hz * 0.45, vibrato_depth=p.vibrato_depth * 0.7)
BANK = Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059")


def coo_glide(d0, d1, f_start, f_end, drift=0.05):
    """A coo-voice tone over the droop: pitch follows the head's half-cosine ramp from f_start to f_end,
    with the coo's small upward drift in the first part (the recipe's `drift_a`)."""
    start = d0 + 0.05
    dur = (d1 - start) + 0.45
    t = t_axis(dur)
    down = ramp(t + start - d0, d1 - d0)
    semis_fall = 12 * np.log2(f_end / f_start)
    freq = f_start * ST ** (semis_fall * down) * (1 + drift * np.sin(np.pi * np.clip(down, 0, 0.5) * 2) ** 2)
    env = bell(t, 0.26 * dur, 0.30 * dur)  # the coo's own soft envelope proportions
    return start, quack(p, dur, freq, env, mods=COO)


def wheee_loop_tape(d0, d1, r_start, r_end):
    """The wheee LOOP segment (a long held tone with a gentle wobble) on a falling tape, cut to the droop."""
    x = read_wav(BANK / "wheee" / "wheee_loop_a.wav")[1]
    y = varispeed(x, [(0.0, r_start), (1.0, r_end)])
    n = int((d1 - d0 + 0.3) * SR)
    y = y[:n]
    t = np.arange(len(y)) / SR
    env = bell(t, 0.4, 0.5)
    return fade(y * env, 0.05, 0.2)


VARIANTS = [
    ("S6_coo_voice_240_150", lambda d0, d1: coo_glide(d0, d1, 240.0, 150.0), "synthesized coo voice (the robot's coo recipe, breathy, slow vibrato) gliding 240 -> 150 Hz with the head"),
    ("S6_coo_voice_225_160", lambda d0, d1: coo_glide(d0, d1, 225.0, 160.0), "coo voice 225 -> 160 Hz, a smaller fall"),
    ("S6_coo_voice_260_130", lambda d0, d1: coo_glide(d0, d1, 260.0, 130.0), "coo voice 260 -> 130 Hz, an octave: the deepest"),
    ("S6_coo_voice_200_140", lambda d0, d1: coo_glide(d0, d1, 200.0, 140.0), "coo voice 200 -> 140 Hz, low but still this duck"),
    ("S6_wheee_loop_tape", lambda d0, d1: (d0 + 0.05, wheee_loop_tape(d0, d1, 0.62, 0.42)), "tape only, no stretching: the bank's long wheee loop on a falling tape (about 340 -> 290 Hz, higher than the coo voices), real timbre"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        d0, d1 = b["droop_start"], b["droop_end"]
        for sname, fn, desc in VARIANTS:
            t, sig = fn(d0, d1)
            tr = Track(b["total"]); tr.put(t, sig)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, -9.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname, f"{len(sig) / SR:.2f} s")
    json.dump(spec, open(ROOT / "motion" / "sadness" / "v6_spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
