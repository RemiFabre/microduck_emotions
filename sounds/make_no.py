"""NO emotion sounds: two sounds, "no-ah": a first quack then a LOWER second one, on the two yaw extremes.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_no.py

Writes sounds/no/<motion>__<sound>.wav and motion/no/spec.json. Peak -3 dBFS, 48 kHz mono.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, normalise, quack, write_wav  # noqa: E402
from make_synced import bank, fade, varispeed  # noqa: E402
from make_synced_v2 import Track  # noqa: E402

OUT = HERE / "no"
p = Personality(ROBOT_SEED)
NO = dict(quackiness=0.7, breath=0.04, vibrato_depth=0.15, attack_sharpness=0.5)
NASAL = dict(quackiness=0.95, breath=0.02, vibrato_depth=0.2, attack_sharpness=0.3, nasal=1.0, am_depth=0.5, tilt=1.6)

# Two sounds on the two yaw extremes (command extremes + the ~0.25 s the joint lags behind).
MOTIONS = {
    "no_one": dict(quacks=[0.6, 1.1], total=1.8),
    "no_two": dict(quacks=[0.55, 0.95], total=2.2),
    "no_beakup": dict(quacks=[0.6, 1.1], total=1.9),
}


def syl(f0, f1, dur, mods=NO, attack=0.012, decay=0.5, level=-3.0):
    sig = quack(p, dur, [(0.0, f0 * 0.97), (0.03, f0), (dur, f1)], ("expdecay", attack, dur * decay), mods=mods)
    return normalise(sig, level)


def pair(t1, t2, f0, semis, d1=0.2, d2=0.32, mods=NO, tail=3.0, level2=-1.0):
    """'no' at f0 (short, nearly flat) then 'ah' `semis` below (longer, falling `tail` more)."""
    f2 = f0 * 2 ** (semis / 12)
    return [(t1, syl(f0, f0 * 2 ** (-0.5 / 12), d1, mods)), (t2, syl(f2, f2 * 2 ** (-tail / 12), d2, mods, level=-3.0 + level2))]


def sounds(qs):
    t1, t2 = qs
    out = []
    out.append(("N1_synth_m3", pair(t1, t2, 250, -3), "synth 'no-ah': second quack a minor third (3 semitones) lower, falling at the end"))
    out.append(("N2_synth_m5", pair(t1, t2, 250, -5), "synth 'no-ah': second quack a fourth (5 semitones) lower: clearer drop"))
    out.append(("N3_synth_m7", pair(t1, t2, 255, -7), "synth 'no-ah': second quack a fifth (7 semitones) lower, the 'ah' sinks"))
    out.append(("N4_nasal_m5", pair(t1, t2, 235, -5, 0.22, 0.36, mods=NASAL, tail=4.0), "nasal grumbly 'no-ah' (heavy buzz, nasal timbre), fourth down: a sulky no"))
    i1 = fade(varispeed(bank("inquire", "j"), [(0.0, 1.3), (1.0, 1.3)]), 0.005, 0.04)          # inquire_j 0.47 s, sped up, flat-ish start
    g2 = fade(varispeed(bank("greet", "i"), [(0.0, 0.8), (1.0, 0.7)]), 0.005, 0.08)              # greet_i 0.37 s, slowed = lower
    out.append(("N5_bank_inquire_greet", [(t1, normalise(i1, -3.0)), (t2, normalise(g2, -4.0))], "the bank's own voice: a quickened 'inquire' then a slowed (lower) 'greet' quack"))
    out.append(("N6_synth_m5_long", pair(t1, t2, 250, -5, 0.18, 0.45, tail=5.0), "'no' short, then a longer 'aaah' (0.45 s) sliding down 5 more semitones: a drawn-out refusal"))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        for sname, parts, desc in sounds(b["quacks"]):
            tr = Track(b["total"])
            for tt, s in parts:
                tr.put(tt, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf[: int(b["total"] * SR)], -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
    json.dump(spec, open(ROOT / "motion" / "no" / "spec.json", "w"), indent=1)
    print("wrote", len(spec["renders"]), "wavs")


if __name__ == "__main__":
    main()
