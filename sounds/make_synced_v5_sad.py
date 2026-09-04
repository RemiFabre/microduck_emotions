"""v5 SAD sound: iterate on the coo-based v4 sounds (Rémi: "interesting, but so low pitch they seem like a
different duck"). Keep the coo material and the descent with the head, but put it in THIS duck's register.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced_v5_sad.py

Method: coo (native ~125 Hz) -> tape up to the start pitch, with a gentle falling glide -> granular time
stretch (pitch kept) so it lasts exactly the droop. Writes sounds/synced_v5/*.wav + motion/sadness/v5_spec.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import SR, write_wav  # noqa: E402
from make_synced import bank, varispeed, fade  # noqa: E402
from make_synced_v2 import Track  # noqa: E402
from make_C_grains import gstretch  # noqa: E402
from make_synced_v4_sad import MOTIONS  # noqa: E402

OUT = HERE / "synced_v5"
COO_HZ = 125.0
ST = 2 ** (1 / 12)


def coo_in_register(letter, f_start, f_end, droop_len, grain_ms=40.0):
    x = bank("coo", letter)
    r0, r1 = f_start / COO_HZ, f_end / COO_HZ
    y = varispeed(x, [(0.0, r0), (0.25, r0 * 0.97), (1.0, r1)])  # pitch up, then glide down with the head
    y = gstretch(y, (droop_len + 0.1) / (len(y) / SR), grain_ms)  # fit the droop, pitch kept
    return fade(y, 0.10, 0.30)


VARIANTS = [
    ("S5_coo_hi_260_150", "a", 260.0, 150.0, "coo_a raised to 260 Hz (the duck's own register), falling to 150 Hz with the head"),
    ("S5_coo_mid_235_155", "a", 235.0, 155.0, "coo_a at 235 Hz (the pitch centre), falling to 155 Hz"),
    ("S5_coo_low_210_150", "a", 210.0, 150.0, "coo_a at 210 Hz, a smaller fall to 150 Hz: the darkest that still sounds like this duck"),
    ("S5_coo_c_240_165", "c", 240.0, 165.0, "another coo (coo_c) at 240 Hz falling to 165 Hz: same idea, different grain"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        d0, d1 = b["droop_start"], b["droop_end"]
        for sname, letter, f0, f1, desc in VARIANTS:
            sig = coo_in_register(letter, f0, f1, d1 - d0)
            tr = Track(b["total"]); tr.put(d0 + 0.05, sig)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, -9.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname, f"{len(sig) / SR:.2f} s")
    json.dump(spec, open(ROOT / "motion" / "sadness" / "v5_spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
