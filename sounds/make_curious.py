"""CURIOUS ("what? what?") emotion, for the Y button. Rémi (voice, 2026-09-04): head slightly forward, then
tilting to the side in a curious manner, and a short double quack that goes UP like a question.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_curious.py

Writes sounds/curious/*.wav (full-length soundtracks on the motion beats) and motion/curious/spec.json.
Three motion options x five sounds. Beats: the two quacks land on the tilt(s).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, bell, normalise, quack, read_wav, seq, write_wav  # noqa: E402
from make_synced import bank, fade, varispeed  # noqa: E402
from make_synced_v2 import Track  # noqa: E402

OUT = HERE / "curious"
p = Personality(ROBOT_SEED)
ASK = dict(quackiness=0.7, breath=0.04, vibrato_depth=0.15, attack_sharpness=0.5)

# Motion options (standing, walking policy in charge, like LB/RB). Head deltas in radians on the shipped
# policies: neck negative = down/forward (the whole forward travel is ~3 cm), head_pitch negative = beak UP,
# head_roll range +-0.27, head_yaw +-1. "forward" = neck -0.8 with head_pitch -0.35 (beak stays level).
MOTIONS = {
    # one tilt: forward, tilt right, hold, back. Quacks on the tilt.
    "curious_tilt": dict(forward=[0.0, 0.4], tilt=[(0.4, 0.8, +0.27)], hold_end=1.9, back=[1.9, 2.4], total=2.8,
                         yaw=0.0, quacks=[0.65, 0.95],
                         desc="head forward (0.4 s), tilt to the right (0.4 s), hold, back; two quacks on the tilt"),
    # two tilts: right on quack 1, left on quack 2 ("what? what?")
    "curious_two_tilts": dict(forward=[0.0, 0.4], tilt=[(0.4, 0.75, +0.27), (1.0, 1.35, -0.27)], hold_end=2.1, back=[2.1, 2.6], total=3.0,
                              yaw=0.0, quacks=[0.6, 1.2],
                              desc="head forward, tilt right on the first quack, tilt left on the second, hold, back"),
    # tilt with a small yaw toward the camera side, slower
    "curious_tilt_yaw": dict(forward=[0.0, 0.5], tilt=[(0.5, 1.0, +0.27)], hold_end=2.2, back=[2.2, 2.8], total=3.2,
                             yaw=0.35, quacks=[0.8, 1.15],
                             desc="slower: forward, tilt right with a 0.35 rad yaw to the right, hold, back"),
}


def ask_quack(f0, rise, dur=0.22, level=-3.0):
    """One short rising quack: f0 -> f0 * 2^(rise/12), soft-ish attack, quick decay."""
    sig = quack(p, dur, [(0.0, f0 * 0.95), (0.05, f0), (dur, f0 * 2 ** (rise / 12))], ("expdecay", 0.015, dur * 0.6), mods=ASK)
    return normalise(sig, level)


def sounds_for(quack_times):
    q1, q2 = quack_times
    out = []
    # 1. synth double rising quack, second higher
    out.append(("Q1_synth_rise_x2", [(q1, ask_quack(230, 5)), (q2, ask_quack(250, 7))], "two short synth quacks, each rising (a fifth, then more), the second higher: 'what? what?'"))
    # 2. bank inquire x2 (real rising question quacks), shortened
    ia = fade(varispeed(bank("inquire", "a"), [(0.0, 1.25), (1.0, 1.1)]), 0.01, 0.04)
    ib = fade(varispeed(bank("inquire", "d"), [(0.0, 1.35), (1.0, 1.2)]), 0.01, 0.04)
    out.append(("Q2_bank_inquire_x2", [(q1, normalise(ia, -3)), (q2, normalise(ib, -3))], "the bank's own rising 'inquire' quacks, two of them, slightly faster"))
    # 3. chirp rising blips x2 (small, cute)
    ca = bank("chirp", "a"); ce = bank("chirp", "e")
    out.append(("Q3_bank_chirp_x2", [(q1, normalise(ca, -4)), (q2, normalise(ce, -3))], "two of the bank's rising chirp blips: smaller, cuter"))
    # 4. synth 'wek-wek?' : first flat-ish short, second a real rising question
    out.append(("Q4_synth_wek_then_rise", [(q1, ask_quack(220, 1.5, 0.16)), (q2, ask_quack(235, 9, 0.3))], "'wek' then a longer rising 'wek?': the question is on the second one"))
    # 5. one longer rising quack then a short echo
    out.append(("Q5_synth_long_rise_echo", [(q1, ask_quack(225, 8, 0.32)), (q2 + 0.05, ask_quack(260, 4, 0.14, -7))], "one longer rising question quack, then a short quieter echo"))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        for sname, parts, desc in sounds_for(b["quacks"]):
            tr = Track(b["total"])
            for t, s in parts:
                tr.put(t, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    (ROOT / "motion" / "curious").mkdir(parents=True, exist_ok=True)
    json.dump(spec, open(ROOT / "motion" / "curious" / "spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
