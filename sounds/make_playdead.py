"""PLAY DEAD sounds, on the motion beats (episode 3): a surprise quack at the press (t = 0, the sit starts), silence
while the duck keels over, then the death quack once it lies still: a long falling quack with a wobble that dies.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_playdead.py

Writes sounds/playdead/<motion>__<sound>.wav and motion/playdead/spec.json (motion beats + (motion, wav) pairs) for
motion/playdead/playdead.py. Beat times come from the fall probe (motion/playdead/probe.json): the duck is at rest
about 1.3 s after the soften is sent for the head-lever recipe, 1.7 s for the lean recipe.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from quack import ROBOT_SEED, SR, Personality, bell, normalise, quack, read_wav, t_axis, write_wav  # noqa: E402
from make_synced import bank, fade, varispeed, Track, db  # noqa: E402
from make_synced_v6_sad import COO  # noqa: E402

OUT = HERE / "playdead"
p = Personality(ROBOT_SEED)
ST = 2 ** (1 / 12)

# ----------------------------------------------------------------------------- motion beats (seconds from the press)
# Every motion: sit_toggle at 0 (the seat lands ~1 s later), the head choreography, `soften` = robot.soften sent
# (gain 50 at once, to 0 over 1 s, torque off), the duck tips over as the torque dies and is still by `rest`;
# `death` = the death quack starts, `death_len` its length; `total` = the emotion's length.
MOTIONS = {
    # ---- v2 (Rémi's feedback, 2026-09-06): the head yaws hard to the side FROM THE PRESS, with the sit ("like devastated,
    # he just turns his head"), then tilts back at once (beak to the sky); the torque is cut with robot.relax (at once);
    # the duck keels over backwards; 0.6 s after it is at rest, robot.init (torque on + a 2 s ramp to the home pose:
    # the last twitch, the head straightens); then the death quack with the beak open 0.3. Times from probe.py (v2 rows).
    "pd_v2_faint": dict(recipe="v2", shock=[0.0, 0.55], yaw=[0.0, 0.5], yaw_amp=1.0, headback=[0.4, 1.0], relax=1.4, init=3.0,
                        rest=2.4, death=5.5, death_len=1.8, total=7.6,
                        desc="v2: alarm + sit at the press while the head turns hard to the side (yaw 1.0 over 0.5 s), the head goes back at once (0.4-1.0 s), robot.relax at 1.4 s: the duck keels over backwards (tips 2.0 s, still by 2.4 s), robot.init at 3.0 s (2 s ramp: the head straightens, the legs fold to home), death quack at 5.5 s with the beak open 0.3"),
    "pd_v2_faint_late": dict(recipe="v2", shock=[0.0, 0.55], yaw=[0.0, 0.5], yaw_amp=1.0, headback=[0.4, 1.0], relax=1.7, init=3.3,
                             rest=2.7, death=5.8, death_len=1.8, total=7.9,
                             desc="v2, a beat of suspense: same head choreography, robot.relax at 1.7 s (the head hangs back for 0.7 s before the cut), init at 3.3 s, death quack at 5.8 s"),
    "pd_v2_soft": dict(recipe="v2", shock=[0.0, 0.55], yaw=[0.0, 0.5], yaw_amp=1.0, headback=[0.4, 1.2], headback_amp=-0.8, relax=1.5, init=3.1,
                       rest=2.5, death=5.6, death_len=1.8, total=7.7,
                       desc="v2, softer lever: the head goes back only to -0.8 over 0.8 s, robot.relax at 1.5 s (probe: head 0.79 m/s instead of 0.90), init at 3.1 s, death quack at 5.6 s"),
    "pd_v2_slowback": dict(recipe="v2", shock=[0.0, 0.55], yaw=[0.0, 0.5], yaw_amp=1.0, headback=[0.6, 1.4], relax=1.8, init=3.4,
                           rest=2.8, death=5.9, death_len=1.8, total=8.0,
                           desc="v2, slower: the head turns first, then goes back over 0.8 s (0.6-1.4 s), robot.relax at 1.8 s, init at 3.4 s, death quack at 5.9 s"),
    # A. the faint: seated, the head goes up/back (beak to the sky) and to the side, the torque goes, the duck keels
    #    over backwards on its own weight. The head is the lever (probe recipe 2).
    "pd_faint": dict(recipe="headback", shock=[0.0, 0.55], headback=[1.0, 2.0], yaw=[1.2, 2.0], yaw_amp=0.6, soften=2.2,
                     rest=4.5, death=4.8, death_len=1.8, total=7.5,
                     desc="shock (head up, sit at once), the head goes back and to the side over 1 s, soften at 2.2 s: the duck keels over backwards on its own weight as the torque dies (tips ~3.2 s, still by ~4.5 s), death quack at 4.8 s, beak barely open"),
    # B. the same, slower: a longer lean, more silence before the death quack.
    "pd_faint_slow": dict(recipe="headback", shock=[0.0, 0.55], headback=[1.0, 2.5], yaw=[1.3, 2.5], yaw_amp=0.6, soften=2.8,
                          rest=5.1, death=5.6, death_len=2.0, total=8.5,
                          desc="same faint, slower: the head goes back over 1.5 s, soften at 2.8 s, more silence, death quack at 5.6 s"),
    # C. the lean: seated, body pose pitch -0.3 (the sit-stand net trades it into the neck: the head mass moves back),
    #    head to the side, soften; the duck tips over a second after the torque is gone (probe recipe 4).
    "pd_lean": dict(recipe="lean", shock=[0.0, 0.55], lean=[1.2, 2.0], lean_pitch=-0.3, yaw=[1.2, 2.0], yaw_amp=0.6, soften=2.4,
                    rest=4.4, death=5.0, death_len=1.8, total=7.5,
                    desc="shock + sit, a body-pose lean back (-0.3, seated: the net moves the neck back) with the head to the side, soften at 2.4 s; the duck tips over ~1.3 s after the torque is gone (probe: the softest fall, but a marginal balance)"),
    # D. the brief's mechanism: the legs straighten (the sit-stand RISE) and the torque is cut 0.4 s in: the duck is
    #    up on its heels and goes over backwards. Violent in the probe (9 rad/s), kept for comparison.
    "pd_legs": dict(recipe="rise", shock=[0.0, 0.55], yaw=[1.2, 1.9], yaw_amp=0.6, rise=2.0, soften=2.4,
                    rest=3.4, death=4.2, death_len=1.8, total=7.0,
                    desc="shock + sit, head to the side, then the sit-stand RISE for 0.4 s (the legs straighten) and soften: the duck goes over backwards from its heels (the brief's idea; the fastest fall in the probe)"),
}

DEATH = dict(quackiness=0.5, breath=0.10, vibrato_depth=0.0, am_depth=0.18, attack_sharpness=0.0, tilt=2.2)


def death_glide(dur, f0=260.0, f1=120.0, wob_hz=5.0, wob_semis=1.2, mods=DEATH, level=-6.0):
    """A long falling quack: f0 -> f1 (log), a wobble that slows and dies, the level dying with it."""
    t = t_axis(dur)
    u = t / dur
    base = f0 * (f1 / f0) ** (u ** 0.8)
    decay = np.exp(-t / (0.55 * dur))
    wob = wob_semis * np.sin(2 * np.pi * wob_hz * (t - 0.6 * t ** 2 / dur)) * decay
    freq = base * ST ** wob
    env = bell(t, 0.12, 0.55 * dur) * (1.0 - 0.35 * u * np.sin(2 * np.pi * 4.0 * t) ** 2)
    sig = quack(p, dur, freq, env, mods=mods)
    return normalise(sig, level)


def death_coo(dur, f0=230.0, f1=110.0, level=-6.0):
    """The robot's own coo recipe (breathy, slow vibrato) on a long fall with a dying wobble."""
    t = t_axis(dur)
    u = t / dur
    base = f0 * (f1 / f0) ** (u ** 0.9)
    wob = 0.9 * np.sin(2 * np.pi * 4.0 * t) * np.exp(-t / (0.6 * dur))
    freq = base * ST ** wob
    env = bell(t, 0.25, 0.5 * dur)
    return normalise(quack(p, dur, freq, env, mods=COO), level)


def death_wheee_tape(dur, level=-6.0):
    """The bank's wheee loop played backwards on a slowing tape: real timbre, a fall that dies."""
    x = bank("wheee", "loop_a")[::-1]
    y = varispeed(x, [(0.0, 0.85), (1.0, 0.45)])
    n = int(dur * SR)
    y = y[:n] if len(y) >= n else np.concatenate([y, np.zeros(n - len(y))])
    t = np.arange(len(y)) / SR
    env = bell(t, 0.15, 0.5 * dur)
    return normalise(fade(y * env, 0.05, 0.25), level)


def sounds_for(b):
    d, dl = b["death"], b["death_len"]
    shock_alarm = normalise(bank("alarm", "a"), -3.0)
    shock_inq = normalise(bank("inquire", "b"), -3.0)
    return [
        ("D1_alarm_glide_wobble", [(0.0, shock_alarm), (d, death_glide(dl))],
         "the bank's alarm scream at the press, silence, then a synth death quack 260 -> 120 Hz with a 5 Hz wobble that slows and dies (-6 dB)"),
        ("D2_inquire_coo_fall", [(0.0, shock_inq), (d, death_coo(dl + 0.2))],
         "the bank's inquire shock (as devastated), silence, then the robot's coo voice falling 230 -> 110 Hz with a dying wobble: a breathy last sigh"),
        ("D3_alarm_wheee_tape", [(0.0, shock_alarm), (d, death_wheee_tape(dl))],
         "alarm at the press, silence, then the bank's wheee loop backwards on a slowing tape: a real-timbre fall that dies"),
    ]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"motions": MOTIONS, "renders": []}
    for mname, b in MOTIONS.items():
        variants = sounds_for(b)
        # every motion gets D1; the two faint motions get all three
        for sname, parts, desc in variants:
            if mname == "pd_v2_faint" and sname == "D3_alarm_wheee_tape":
                continue
            if mname.startswith("pd_v2") and mname != "pd_v2_faint" and sname != "D1_alarm_glide_wobble":
                continue
            if not mname.startswith(("pd_faint", "pd_v2")) and sname != "D1_alarm_glide_wobble":
                continue
            if mname == "pd_faint_slow" and sname == "D3_alarm_wheee_tape":
                continue
            tr = Track(b["total"])
            for t, s in parts:
                tr.put(t, s)
            wav = write_wav(OUT / f"{mname}__{sname}.wav", tr.buf, -3.0)
            spec["renders"].append({"motion": mname, "sound": sname, "wav": str(wav), "desc": desc})
            print(mname, sname)
    (ROOT / "motion" / "playdead").mkdir(parents=True, exist_ok=True)
    json.dump(spec, open(ROOT / "motion" / "playdead" / "spec.json", "w"), indent=1)


if __name__ == "__main__":
    main()
