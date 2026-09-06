"""ANGRY (programmatic, X button), episode 3. Rémi: no RL; body-pose bows and head snaps, hard short repeated
angry quacks on the snaps; the beak must open wide (a held leash has to drop).

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_angry.py

Writes sounds/angry_v3/<motion>__<sound>.wav (full-length soundtracks, t = 0 = the button press, one bark
per motion beat) and motion/angry/spec.json (the motions' beats + the (motion, sound) pairs).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, bell, lerp, normalise, quack, read_wav, t_axis, write_wav  # noqa: E402
from make_synced import bank, fade  # noqa: E402
from make_synced_v2 import Track  # noqa: E402

OUT = HERE / "angry_v3"
P = Personality(ROBOT_SEED)
# Hard timbre: strong upper harmonics, full-depth rasp buzz, snappy attack, no vibrato (a wobble pleads).
ANG = dict(tilt=1.25, brightness=0.55, vibrato_rate_hz=0.0, vibrato_depth=0.0, attack_sharpness=1.0,
           breath=0.03, quackiness=1.0, am_depth=1.0, am_rate_hz=28.0, jitter_depth=0.12)


def rng(i):
    return P.variant_rng("angry3", i)


def hit(hz, dur=0.16, gain=1.0, i=0, am_rate=28.0, crackle=0.10, click=0.5, decay=None, fall=0.90):
    """One short hard bark: instant attack with a click, crackle, slight fall, short decay."""
    m = dict(ANG, am_rate_hz=am_rate)
    return gain * quack(P, dur, [(0.0, hz), (0.03, hz * 1.04), (dur, hz * fall)], ("expdecay", 0.004, decay or dur * 0.55),
                        mods=m, rng=rng(i), click_gain=click, crackle=crackle)


def chopped(hz, dur, gain=1.0, i=0, am_rate=32.0):
    """A held rasp cut dead (no tail): the 'and that is final' bark."""
    t = t_axis(dur)
    env = bell(t, 0.004, 0.02)
    return gain * quack(P, dur, [(0.0, hz * 1.02), (0.03, hz), (dur, hz * 0.985)], env, mods=dict(ANG, am_rate_hz=am_rate),
                        rng=rng(i), click_gain=0.5, crackle=0.12)


def growl(t0, t1, hz0=140, hz1=230, i=80):
    """A low rasp swelling and rising from t0 to t1 (into the first bark)."""
    dur = t1 - t0
    t = t_axis(dur)
    contour = lerp(t, [(0.0, hz0), (0.6 * dur, hz0 * 1.15), (dur, hz1)])
    env = lerp(t, [(0, 0.0), (0.15 * dur, 0.45), (0.7 * dur, 0.7), (dur, 1.0)])
    return 0.5 * quack(P, dur, contour, env, mods=dict(ANG, am_rate_hz=24.0, tilt=1.15, jitter_depth=0.2), rng=rng(i), crackle=0.18)


def alarm_grain(letter, cut=0.2, rate=1.0):
    x = bank("alarm", letter)[: int(cut * SR)]
    if rate != 1.0:
        x = np.interp(np.arange(0, len(x), rate), np.arange(len(x)), x)
    return fade(x, 0.003, 0.03)


# ----------------------------------------------------------------------------- motions (beats only; the geometry is in motion/angry/angry.py)
# `barks` = the times of the snaps the barks land on; `growl` = an optional (t0, t1) menace window before the first bark.
MOTIONS = {
    "bow_snaps": dict(total=2.6, barks=[0.30, 0.90, 1.50, 2.00], growl=None,
                      desc="beak up (-0.35); on each bark a head-yaw snap (+0.7 / -0.7 / +0.7 / centre), a short head jab (beak from up to level, +0.45 over 0.12 s) "
                           "and a small fast bow (body pitch +0.14, 0.15 s in, 0.25 s out)"),
    "crouch_shake_lunge": dict(total=3.0, barks=[1.70, 2.10], growl=(0.35, 1.65),
                               desc="beak up (-0.6) with a slow menacing yaw sweep right-to-left (the growl), then a jab (beak up to level, +0.7) with a small "
                                    "bow (+0.14) and a second smaller jab"),
    "beakup_triple_bow": dict(total=2.8, barks=[0.90, 1.30, 1.70], growl=None,
                              desc="slow menacing beak-up (head_pitch -0.6 over 0.6 s), then three fast jabs (beak up to almost level, +0.5) with small bows (+0.14) "
                                   "and alternating yaw +-0.5, a bark on each"),
    "double_lunge": dict(total=2.9, barks=[0.50, 1.70, 2.25], growl=(0.85, 1.65),
                         desc="beak up (-0.5), a lunge (head jab +0.6 with a small bow +0.14) on a bark, a look left-right while re-arming, a "
                              "second lunge and a third smaller one with barks, back to centre"),
}


def sounds_for(b):
    barks, gw = b["barks"], b["growl"]
    n = len(barks)
    out = []
    # 1. triple/quad hard barks: rising a little each time, the last one longer and chopped
    parts = []
    for k, tb in enumerate(barks):
        hz = 300 * 2 ** (1.5 * k / 12)
        if k == n - 1:
            parts.append((tb, normalise(chopped(hz, 0.30, i=10 + k), -3)))
        else:
            parts.append((tb, normalise(hit(hz, 0.17, i=10 + k), -3.5 + 0.5 * k)))
    if gw:
        parts.append((gw[0], normalise(growl(*gw), -8)))
    out.append(("S1_hard_barks", parts, f"{n} short hard barks (300 Hz rising 1.5 semitones each, click on the attack, 28 Hz rasp), one per snap, "
                                        "the last held and chopped dead" + ("; a low growl swells before the first" if gw else "")))
    # 2. bank alarm grains: the duck's own scream chopped to its first 0.2 s, one per snap, down 3 semitones, the last two rapid
    letters = ["a", "c", "d", "b", "e"]
    parts = [(tb, normalise(alarm_grain(letters[k % 5], 0.2, 2 ** (-3 / 12) * (1 + 0.02 * k)), -3)) for k, tb in enumerate(barks)]
    parts.append((barks[-1] + 0.12, normalise(alarm_grain("g", 0.16, 2 ** (-4 / 12)), -4)))
    if gw:
        parts.append((gw[0], normalise(growl(*gw), -9)))
    out.append(("S2_alarm_grains", parts, "the bank's own alarm honk chopped to its first 0.2 s, one per snap, down 3 semitones, the last one doubled: "
                                          "dry hard hits in the real voice" + ("; growl before" if gw else "")))
    # 3. growl into barks: the menace is in the sound even when the motion has no growl window
    g0 = gw if gw else (max(0.0, barks[0] - 0.6), barks[0] - 0.02)
    parts = [(g0[0], normalise(growl(*g0, hz0=150, hz1=260, i=90), -6))]
    for k, tb in enumerate(barks):
        parts.append((tb, normalise(hit(330 * 2 ** (k / 12), 0.20, i=30 + k, am_rate=30, decay=0.09), -3)))
    out.append(("S3_growl_barks", parts, "a low 150 Hz growl swelling and rising into the first bark, then one loud 330 Hz bark per snap (longer, 0.2 s)"))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        for sname, parts, desc in sounds_for(b):
            tr = Track(b["total"])
            for t, s in parts:
                tr.put(t, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf[: int(b["total"] * SR)], -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    (ROOT / "motion" / "angry").mkdir(parents=True, exist_ok=True)
    json.dump(spec, open(ROOT / "motion" / "angry" / "spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
