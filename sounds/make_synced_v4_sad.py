"""v4 SAD sound: Rémi's new direction (voice, 2026-09-04 late afternoon): ONE continuous sound from the
start to the end of the head going down, descending with the head ("the pain felt as the head lowers"),
then the side-to-side shakes stay SILENT. Try a bunch.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced_v4_sad.py

Writes sounds/synced_v4/*.wav and motion/sadness/v4_spec.json. The pitch follows the head: f(t) = f_hi *
2^(-drop * down(t) / 12) with down(t) the same half-cosine ramp the motion uses, so pitch and head angle
move together.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import SR, bell, normalise, quack, t_axis, write_wav  # noqa: E402
from make_synced import bank, varispeed, fade  # noqa: E402
from make_synced_v2 import GENTLE, GENTLER, Track, p  # noqa: E402

OUT = HERE / "synced_v4"
ST = 2 ** (1 / 12)
SOFTEST = dict(GENTLER, breath=0.08, vibrato_depth=0.25, vibrato_rate_hz=2.4, quackiness=0.25)

# Two motions: the normal 2 s droop (v3's sad_2x1.2 beats) and a slower 2.5 s droop. Body pitch 0.05.
MOTIONS = {
    "sad_droop2.0": dict(base="sad", body_pitch=0.05, sit=None, droop_start=0.0, droop_end=2.0, shake_start=2.0,
                         shake_extremes=[2.6, 3.8], shake_end=4.4, hold_end=5.0, rise_start=5.0, head_level=7.0, total=7.8),
    "sad_droop2.5": dict(base="sad", body_pitch=0.05, sit=None, droop_start=0.0, droop_end=2.5, shake_start=2.5,
                         shake_extremes=[3.1, 4.3], shake_end=4.9, hold_end=5.5, rise_start=5.5, head_level=7.5, total=8.3),
}


def ramp(x, L):
    """Half-cosine 0 -> 1 over L seconds (the motion's droop envelope)."""
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(x / L, 0, 1))


def synth_droop(d0, d1, f_hi, drop, mods, attack=0.25, release=0.35, lead=0.05):
    """A tone from d0 to d1 + release whose pitch follows the droop ramp."""
    start = d0 + lead
    dur = (d1 - start) + release
    t = t_axis(dur)
    down = ramp(t + start - d0, d1 - d0)
    freq = f_hi * ST ** (-drop * down)
    env = bell(t, attack, release + 0.15)
    return start, quack(p, dur, freq, env, mods=mods)


def tape_to_droop(x, d0, d1, r_start, r_end, curve=1.0):
    """Play a bank sound on a falling tape so it lasts exactly the droop (d1 - d0), rate r_start -> r_end."""
    target = d1 - d0
    y = varispeed(x, [(0.0, r_start), (1.0, r_end)])
    # adjust the mean rate so the length matches the droop (varispeed keeps the rate shape)
    k = (len(y) / SR) / target
    y = varispeed(x, [(0.0, r_start * k), (1.0, r_end * k)])
    return fade(y, 0.08, 0.25)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        d0, d1 = b["droop_start"], b["droop_end"]
        L = d1 - d0
        tracks = []

        def add(name, t, sig, peak, desc):
            tr = Track(b["total"]); tr.put(t, sig)
            tracks.append((name, tr, peak, desc))

        # 1. synth glide, an octave down with the head
        t, s = synth_droop(d0, d1, 260.0, 12.0, GENTLER)
        add("S4_glide_octave", t, s, -10.0, f"synth glide 260 -> 130 Hz following the head over the {L:.1f} s droop, soft voice, silent shakes")
        # 2. synth glide, a fifth down, lower and softest
        t, s = synth_droop(d0, d1, 225.0, 7.0, SOFTEST, attack=0.35)
        add("S4_glide_fifth_soft", t, s, -12.0, f"synth glide 225 -> 150 Hz (a fifth) with the head, softest voice, quieter")
        # 3. sad2-style: slide then an octave drop in the last third of the droop (the A_port_sad2 shape)
        start = d0 + 0.05; dur = L - 0.05 + 0.4
        tt = t_axis(dur)
        down = ramp(tt + start - d0, L)
        freq = np.where(down < 0.62, 330.0 * ST ** (-5.0 * down / 0.62), 330.0 * ST ** (-5.0) * ST ** (-12.0 * np.clip((down - 0.62) / 0.3, 0, 1)))
        env = bell(tt, 0.2, 0.55)
        add("S4_sad2_slide_drop", start, quack(p, dur, freq, env, mods=GENTLE), -9.0, "the Reachy sad2 shape mapped on the droop: a slide 330 -> 245 Hz, then the octave drop to 123 Hz as the head reaches the bottom")
        # 4. coo on a falling tape stretched to the droop
        coo = bank("coo", "a")
        add("S4_coo_tape", d0 + 0.05, tape_to_droop(coo, d0, d1, 1.9, 0.75), -9.0, "the robot's own coo on a falling tape stretched to the droop (about 250 -> 100 Hz)")
        # 5. reversed inquire (question -> sigh) stretched to the droop
        inq = bank("inquire", "a")[::-1]
        add("S4_inquire_sigh_tape", d0 + 0.05, tape_to_droop(inq, d0, d1, 0.62, 0.42), -9.0, "reversed inquire (a falling sigh) stretched to the droop")
        # 6. reversed wheee start (the bank's own big glide) stretched to the droop
        wh = bank("wheee", "wheee_start_a".split("_")[-1]) if False else None
        from quack import read_wav
        wh = read_wav(Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059/wheee/wheee_start_a.wav"))[1][::-1]
        add("S4_wheee_fall_tape", d0 + 0.05, tape_to_droop(wh, d0, d1, 0.55, 0.32), -9.0, "the bank's rising wheee reversed and slowed to the droop: a long fall in the real timbre (the C_wheee_fall idea)")
        for sname, tr, peak, desc in tracks:
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, peak)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    json.dump(spec, open(ROOT / "motion" / "sadness" / "v4_spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
