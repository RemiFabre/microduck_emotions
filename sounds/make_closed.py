"""QUACK WITH THE BEAK CLOSED: sound-only emotion variants for when the duck holds a leash in its beak.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_closed.py

A closed beak muffles the voice: the synth sounds are low-passed (2nd-order Butterworth, 900 Hz) with the
brightness lowered and the nasal weight raised. Writes sounds/closed/*.wav and motion/closed/spec.json.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.signal import butter, lfilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, normalise, quack, read_wav, write_wav  # noqa: E402
from make_synced_v2 import Track  # noqa: E402

OUT = HERE / "closed"
p = Personality(ROBOT_SEED)
MUFFLED = dict(brightness=0.05, nasal=1.0, quackiness=0.6, breath=0.02, vibrato_depth=0.25, attack_sharpness=0.2, tilt=2.6, am_depth=0.35)
GRUMBLE = dict(MUFFLED, quackiness=0.95, am_depth=0.55, am_rate_hz=19.0, vibrato_depth=0.3, vibrato_rate_hz=4.5)


def lowpass(x, fc=900.0):
    b, a = butter(2, fc / (SR / 2))
    return lfilter(b, a, x)


def muffled(dur, contour, mods, attack=0.03, decay=0.6, fc=900.0, level=-3.0):
    sig = quack(p, dur, contour, ("expdecay", attack, dur * decay), mods=mods)
    return normalise(lowpass(sig, fc), level)


MOTIONS = {
    "closed_chirps": dict(quacks=[0.6, 1.2], total=2.4, sound="C1_curious_chirps"),
    "closed_grumble": dict(quacks=[0.5, 0.95], total=2.2, sound="C2_grumble"),
    "closed_mmh": dict(quacks=[0.5], total=2.0, sound="C3_mmh"),
    "closed_grumble_still": dict(quacks=[0.5, 0.95], total=2.2, sound="C2_grumble"),
}


def sounds():
    out = {}
    out["C1_curious_chirps"] = ([(0.0, read_wav(ROOT / "sounds" / "robot" / "curious_a.wav")[1])],
                                "the curious two chirps (sounds/robot/curious_a.wav, chirps at 0.6 / 1.2 s), beak kept shut")
    g1 = muffled(0.32, [(0.0, 190), (0.05, 200), (0.32, 175)], GRUMBLE, decay=0.7)
    g2 = muffled(0.42, [(0.0, 185), (0.06, 180), (0.42, 150)], GRUMBLE, decay=0.7, level=-4.0)
    out["C2_grumble"] = ([(0.5, g1), (0.95, g2)], "an irritated muffled grumble, two low nasal buzzes (190 -> 150 Hz, low-passed at 900 Hz): 'mrr-mrrh'")
    m = muffled(0.45, [(0.0, 205), (0.15, 215), (0.45, 300)], MUFFLED, attack=0.05, decay=0.8, fc=1100.0)
    out["C3_mmh"] = ([(0.5, m)], "a muffled rising 'mmh?' (205 -> 300 Hz, low-passed): a question through a shut beak")
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    snd = sounds()
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        parts, desc = snd[b["sound"]]
        tr = Track(b["total"])
        for tt, s in parts:
            tr.put(tt, s)
        wav = write_wav(OUT / f"{mname}__{b['sound']}.wav", tr.buf[: int(b["total"] * SR)], -3.0)
        spec["renders"].append({"motion": mname, "sound": b["sound"], "wav": str(wav), "desc": desc})
    json.dump(spec, open(ROOT / "motion" / "closed" / "spec.json", "w"), indent=1)
    print("wrote", len(spec["renders"]), "wavs")


if __name__ == "__main__":
    main()
