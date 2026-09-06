"""EXCITED emotion (episode 3): many happy quacks, rising, fast, repeated, one per body bounce.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_excited.py

Writes sounds/excited/<motion>__<sound>.wav (full-length tracks from t = 0 = the button press, quacks on the
motion's bounce beats) and motion/excited/spec.json (motions' quack times + the (motion, sound) pairs).
The motions themselves live in motion/excited/excited.py; only their quack beats are declared here.
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

OUT = HERE / "excited"
p = Personality(ROBOT_SEED)
# The happy voice: quacky, snappy attack, a little brighter, small vibrato.
HAPPY = dict(quackiness=0.75, breath=0.03, vibrato_depth=0.12, attack_sharpness=0.65, brightness=0.35)

# Quack onsets (s from the press) for each motion candidate: one quack per bounce / pop / wag extreme.
MOTIONS = {
    # A: z bounces at 2 Hz, beak up, yaw wag at 1 Hz; a quack on every top of the bounce
    "excited_bounce": dict(quacks=[0.35, 0.85, 1.35, 1.85, 2.35], total=3.2,
                           desc="body bobs at 2 Hz (bow pulses 0 -> +0.10, the z slot is dead on the stand net), beak up, head wags left-right at 1 Hz; a quack on every top"),
    # B: bow pulses ('hops') every 0.55 s with the yaw flipping each hop, beak up
    "excited_hops": dict(quacks=[0.45, 1.0, 1.55, 2.1, 2.65], total=3.4,
                         desc="five bow pulses (pitch 0 -> +0.15) every 0.55 s, the head flips left/right on each, beak up; a quack on each pulse"),
    # C: two big crouch-and-pop 'jumps' with the head thrown up, then a fast wag
    "excited_jumps": dict(quacks=[0.5, 1.4, 2.05, 2.35, 2.65], total=3.6,
                          desc="two crouch-then-pop jumps (bow +0.22 released fast) with the head thrown up (beak -0.8) and a quack on each pop, then a fast wag with three chirps"),
    # D: accelerating wag with the body pumping in sync and the beak rising over the sequence
    "excited_wag_pump": dict(quacks=[0.4, 0.95, 1.45, 1.9, 2.3, 2.65], total=3.4,
                             desc="head wag +-0.6 accelerating (6 swings), the body bobs (bow pulse +0.12) on each swing, the beak rises higher and higher, ends with a bow flourish; a quack on each swing"),
}
ST = 2 ** (1 / 12)


def happy_quack(f0, rise, dur=0.2, level=-3.0):
    """One short rising quack: f0 -> f0 * 2^(rise/12), snappy attack, quick decay."""
    sig = quack(p, dur, [(0.0, f0 * 0.93), (0.03, f0), (dur, f0 * ST ** rise)], ("expdecay", 0.008, dur * 0.55), mods=HAPPY)
    return normalise(sig, level)


CHIRPS_UP = ["a", "b", "f", "e", "i", "j", "l", "g"]        # the bank's chirps sorted by pitch (236 -> 410 Hz)


def sounds_for(quacks):
    n = len(quacks)
    out = []
    # 1. synth: rising quacks, each one starts higher, shorter and rises more: the excitement climbs
    parts = [(tq, happy_quack(225 * ST ** (1.5 * i), 5 + i, 0.2 - 0.012 * i)) for i, tq in enumerate(quacks)]
    out.append(("X1_synth_rise_climb", parts, "synth rising quacks, each one higher, shorter and rising more than the last"))
    # 2. the bank's own chirps, picked in rising pitch order
    parts = [(tq, normalise(bank("chirp", CHIRPS_UP[min(i, len(CHIRPS_UP) - 1)]), -3)) for i, tq in enumerate(quacks)]
    out.append(("X2_bank_chirps_up", parts, "the bank's rising chirp blips, one per bounce, in rising pitch order (236 to 410 Hz)"))
    # 3. greet 'wak' shortened and sped up more and more (a wake-up quack getting giddy), synth accents on the last two
    parts = []
    for i, tq in enumerate(quacks):
        g = bank("greet", "e" if i % 2 == 0 else "i")
        rate = 1.05 + 0.08 * i
        parts.append((tq, normalise(fade(varispeed(g, [(0.0, rate), (1.0, rate * 1.1)]), 0.005, 0.05), -3)))
    out.append(("X3_greet_wak_faster", parts, "the bank's 'wak' wake-up quacks, each one faster and higher than the last"))
    # 4. a wheee ride-up start, then chirps on the later beats
    ws = bank("wheee", "start_c")
    parts = [(quacks[0] - 0.35 if quacks[0] > 0.4 else 0.05, normalise(fade(ws, 0.01, 0.15), -3))]
    parts += [(tq, normalise(bank("chirp", CHIRPS_UP[min(i + 2, len(CHIRPS_UP) - 1)]), -3)) for i, tq in enumerate(quacks[1:])]
    out.append(("X4_wheee_start_chirps", parts, "the joy ride's rising 'wheee' start on the first bounce, then rising chirps"))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        for sname, parts, desc in sounds_for(b["quacks"]):
            if sname == "X4_wheee_start_chirps" and mname not in ("excited_jumps", "excited_wag_pump"):
                continue
            tr = Track(b["total"])
            for t, s in parts:
                tr.put(t, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf[: int(b["total"] * SR)], -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    (ROOT / "motion" / "excited").mkdir(parents=True, exist_ok=True)
    json.dump(spec, open(ROOT / "motion" / "excited" / "spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
