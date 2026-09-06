#!/usr/bin/env python
"""QUACK WITH THE BEAK CLOSED: sound-only emotion variants (the duck holds a leash), mouth forced shut.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/closed/closed.py [--only SUBSTR] [--no-open] [--no-render]

Standing, stand net, twist 0, body pose 0, neck 0, head_pitch 0 (the beak must not drop the leash). Only tiny roll /
yaw wobbles so the duck is not dead still. Rendered with mouth_mode='closed'. Sounds from sounds/make_closed.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/remi/microduck/notes/emotions/motion/episode3")
import lib  # noqa: E402
from lib import Motion, pulse, swings  # noqa: E402

HERE = Path(__file__).resolve().parent

MOTIONS = {
    "closed_chirps": Motion("closed_chirps", "the curious chirps with a small roll wobble: +0.2 on the first chirp (0.6 s), -0.2 on the second (1.2 s), centre by 1.9 s; no pitch, no neck",
                            2.4, lambda t: dict(head_roll=swings(t, [0.7, 1.3], 0.2, 0.3)),
                            beats=[(0.6, "chirp 1"), (0.9, "roll right"), (1.2, "chirp 2"), (1.5, "roll left"), (1.9, "centre")], quacks=[0.6, 1.2]),
    "closed_grumble": Motion("closed_grumble", "irritated grumble with a small yaw twitch: -0.25 on the first buzz (0.5 s), +0.25 on the second (0.95 s), centre by 1.5 s",
                             2.2, lambda t: dict(head_yaw=-swings(t, [0.6, 1.05], 0.25, 0.25)),
                             beats=[(0.5, "grumble 1"), (0.8, "yaw"), (0.95, "grumble 2"), (1.3, "yaw"), (1.6, "centre")], quacks=[0.5, 0.95]),
    "closed_mmh": Motion("closed_mmh", "a muffled rising 'mmh?' with a small roll tilt (+0.22 from 0.5 s, held, back by 1.6 s)",
                         2.0, lambda t: dict(head_roll=0.22 * pulse(t, 0.45, 0.3, 0.5, 0.35)),
                         beats=[(0.5, "mmh?"), (0.8, "tilt"), (1.3, "hold"), (1.6, "centre")], quacks=[0.5]),
    "closed_grumble_still": Motion("closed_grumble_still", "the grumble with no head motion at all (the leash stays perfectly still)",
                                   2.2, lambda t: dict(), beats=[(0.5, "grumble 1"), (0.95, "grumble 2")], quacks=[0.5, 0.95]),
}


def pick():
    import json
    pk = json.load(open(HERE / "PICK.json"))
    return MOTIONS[pk["motion"]], Path(pk["wav"]), pk["sound"]


if __name__ == "__main__":
    import yesno_common as C
    C.run("closed", MOTIONS,
          header="Quack with the beak closed (holding the leash)",
          intro="Sound-only emotion variants: the mouth intent stays 0 whatever the sound, so a held leash stays in the beak. Standing, stand net, neck 0, head_pitch 0; "
                "only small roll / yaw wobbles. Synth sounds are low-passed at 900-1100 Hz with a nasal, dull timbre (a shut beak). Simulation 640x480, 30 fps. "
                "Files: <code>/Users/remi/microduck/notes/emotions/motion/closed/</code> (renderer <code>closed.py</code>, sounds <code>sounds/make_closed.py</code>).",
          pick_stem="closed_grumble__C2_grumble", mouth_mode="closed",
          pick_note="For the scene's lines 3 and 5 (the duck answers Reachy through the leash): the muffled grumble with the yaw twitch reads as an irritated, mouth-full answer. "
                    "closed_chirps is the same curious emotion the duck already has, just with the beak shut (use it when the answer should stay friendly); closed_mmh for a question.")
