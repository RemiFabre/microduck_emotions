"""LAUGH emotion (episode 3): "ha-ha-ha-ha, ha-ha" quack laughs, one "ha" per body bob, two per head swing.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_laugh.py

Writes sounds/laugh/<motion>__<sound>.wav (from t = 0 = the press) and motion/laugh/spec.json (the beats shared by
the motions in motion/laugh/laugh.py: `has` = the laugh onsets, `swings` = the head-swing extremes, one every two ha's).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, normalise, quack, write_wav  # noqa: E402
from make_synced import bank, fade, varispeed  # noqa: E402
from make_synced_v2 import Track  # noqa: E402

OUT = HERE / "laugh"
p = Personality(ROBOT_SEED)
ST = 2 ** (1 / 12)
# The laughing voice: very quacky, sharp attack, bright, a little buzz.
HA = dict(quackiness=0.95, breath=0.02, vibrato_depth=0.05, attack_sharpness=0.9, brightness=0.4, am_depth=0.45)

# One beat list for every motion: four ha's, a breath, three more. The swings sit on every other ha.
HAS = [0.35, 0.57, 0.79, 1.01, 1.45, 1.67, 1.89]
SWINGS = [0.35, 0.79, 1.45, 1.89]
TOTAL = 2.6
MOTIONS = {
    "laugh_wag": dict(has=HAS, swings=SWINGS, total=TOTAL,
                      desc="beak up (-0.55 held), the head wags +-0.45 on every other ha, a small bow pulse (+0.10) on every ha shakes the body"),
    "laugh_bob": dict(has=HAS, swings=SWINGS, total=TOTAL,
                      desc="beak up, small wag (+-0.25); the body bobs on every ha and the head pumps back further on each ha (head_pitch -0.4 -> -0.7)"),
    "laugh_roll": dict(has=HAS, swings=SWINGS, total=TOTAL,
                       desc="beak up (-0.55), the head rolls side to side (+-0.35 asked) on every other ha, the body bobs on every ha"),
}


def ha(f0, fall=1.5, dur=0.12, level=-3.0):
    """One staccato 'ha': a short quack falling `fall` semitones, sharp attack, fast decay."""
    sig = quack(p, dur, [(0.0, f0 * 1.04), (0.02, f0), (dur, f0 / ST ** fall)], ("expdecay", 0.006, dur * 0.45), mods=HA, click_gain=0.25)
    return normalise(sig, level)


def sounds_for(has):
    out = []
    # L1: synth staccato run, pitch stepping down 0.7 semitone per ha, the second phrase a little lower and softer
    parts = []
    for i, t in enumerate(has):
        f0 = 300 / ST ** (0.7 * i)
        lvl = -3.0 - (0.4 * i) - (1.5 if i >= 4 else 0.0)
        parts.append((t, ha(f0, level=lvl)))
    out.append(("L1_synth_haha", parts, "seven short staccato synth quacks, each a little lower: 'ha-ha-ha-ha, ha-ha-ha'"))
    # L2: the bank's chirps chopped to 0.12 s and slowed step by step (a descending staccato run in the real voice)
    letters = ["l", "j", "i", "e", "f", "b", "a"]          # bank chirps from high to low
    parts = []
    for i, t in enumerate(has):
        c = bank("chirp", letters[i])
        c = varispeed(c, [(0.0, 1.3), (1.0, 1.15)])[: int(0.12 * SR)]
        parts.append((t, normalise(fade(c, 0.004, 0.03), -3.0 - 0.4 * i)))
    out.append(("L2_bank_chirps_chopped", parts, "the bank's own chirps, chopped to 0.12 s, from the highest to the lowest: a staccato run in the real voice"))
    # L3: a rising giggle glide into the run, the last ha stretched into a falling 'haaa'
    parts = [(has[0] - 0.3, normalise(quack(p, 0.32, [(0.0, 220), (0.32, 330)], ("bell", 0.03, 0.08), mods=HA), -5.0))]
    for i, t in enumerate(has[:-1]):
        parts.append((t, ha(300 / ST ** (0.7 * i), level=-3.0 - 0.4 * i - (1.5 if i >= 4 else 0.0))))
    last = quack(p, 0.45, [(0.0, 285), (0.05, 280), (0.45, 200)], ("expdecay", 0.006, 0.28), mods=HA, click_gain=0.25)
    parts.append((has[-1], normalise(last, -4.5)))
    out.append(("L3_giggle_run_haaa", parts, "a short rising giggle glide, the staccato run, then the last ha stretched into a falling 'haaa'"))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        for sname, parts, desc in sounds_for(b["has"]):
            tr = Track(b["total"])
            for t, s in parts:
                tr.put(t, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf[: int(b["total"] * SR)], -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    (ROOT / "motion" / "laugh").mkdir(parents=True, exist_ok=True)
    json.dump(spec, open(ROOT / "motion" / "laugh" / "spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
