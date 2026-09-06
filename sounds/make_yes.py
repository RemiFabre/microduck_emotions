"""YES emotion sounds: ONE affirmative quack, flat or slightly falling, on the nod's down-beat.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_yes.py

Writes sounds/yes/<motion>__<sound>.wav (full-length: silence until the quack at the motion's beat) and
motion/yes/spec.json with the (motion, sound) pairs. Peak -3 dBFS, 48 kHz mono.
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

OUT = HERE / "yes"
p = Personality(ROBOT_SEED)
YES = dict(quackiness=0.75, breath=0.03, vibrato_depth=0.12, attack_sharpness=0.6)

# The quack lands on the nod's down-beat (the head joint reaches the bottom ~0.4 s after the command starts).
MOTIONS = {
    "yes_single": dict(quacks=[0.45], total=1.5),
    "yes_double": dict(quacks=[0.45], total=2.0),
    "yes_lift": dict(quacks=[0.8], total=1.9),
}


def q(f0, fall_semis, dur=0.26, level=-3.0, mods=YES, decay=0.55):
    """One short quack: f0, slight rise into the body, then falls `fall_semis` by the end."""
    f_end = f0 * 2 ** (-fall_semis / 12)
    sig = quack(p, dur, [(0.0, f0 * 0.97), (0.04, f0 * 1.03), (0.12, f0), (dur, f_end)], ("expdecay", 0.012, dur * decay), mods=mods)
    return normalise(sig, level)


def sounds(t):
    out = []
    out.append(("Y1_synth_flat", [(t, q(238, 0.5, 0.26))], "one synth quack, flat (238 Hz, the duck's own pitch centre): a plain 'yep'"))
    out.append(("Y2_synth_fall", [(t, q(250, 3.0, 0.30))], "one synth quack falling 3 semitones over 0.3 s: an assertive, settled 'yes'"))
    out.append(("Y3_synth_wak", [(t, q(255, 5.0, 0.18, mods=dict(YES, attack_sharpness=0.9, quackiness=0.9), decay=0.4))],
                "a very short, snappy 'wak' (0.18 s, falls a fourth): curt agreement"))
    g = fade(varispeed(bank("greet", "e"), [(0.0, 1.05), (1.0, 1.15)]), 0.005, 0.05)      # greet_e is a 0.37 s single wake-up quack
    out.append(("Y4_bank_greet", [(t, normalise(g, -3.0))], "the bank's own short 'greet' quack (greet_e), slightly quickened: the real voice, flat-ish"))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        for sname, parts, desc in sounds(b["quacks"][0]):
            tr = Track(b["total"])
            for tt, s in parts:
                tr.put(tt, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf[: int(b["total"] * SR)], -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
    json.dump(spec, open(ROOT / "motion" / "yes" / "spec.json", "w"), indent=1)
    print("wrote", len(spec["renders"]), "wavs")


if __name__ == "__main__":
    main()
