#!/usr/bin/env python
"""YES: one clear nod (head pitch down and back), one affirmative quack on the down-beat.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/yes/yes.py [--only SUBSTR] [--no-open] [--no-render]

Standing, stand net, twist 0, body pose 0, neck 0 (a forward head makes the real duck step). Sounds from
sounds/make_yes.py (spec.json). Outputs here + combined/yes/index.html.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/remi/microduck/notes/emotions/motion/episode3")
import lib  # noqa: E402
from lib import Motion, pulse, ramp  # noqa: E402

HERE = Path(__file__).resolve().parent
NOD = 0.7           # head_pitch command at the bottom of the nod (joint follows ~0.4 s late, reaches ~0.6)

MOTIONS = {
    "yes_single": Motion("yes_single", "one nod: head_pitch 0 -> +0.7 over 0.25 s from t = 0.05, hold 0.1 s, back over 0.35 s (command level by 0.75 s, joint by ~1.1 s)", 1.5,
                         lambda t: dict(head_pitch=NOD * pulse(t, 0.05, 0.25, 0.10, 0.35)),
                         beats=[(0.3, "cmd down"), (0.45, "quack / bottom"), (0.75, "cmd level"), (1.1, "joint level")], quacks=[0.45]),
    "yes_double": Motion("yes_double", "two nods 0.55 s apart: +0.55 pulses (0.2 s down, 0.05 hold, 0.3 up) at t = 0.05 and 0.6; ONE quack on the first", 2.0,
                         lambda t: dict(head_pitch=0.55 * (pulse(t, 0.05, 0.2, 0.05, 0.3) + pulse(t, 0.6, 0.2, 0.05, 0.3))),
                         beats=[(0.25, "nod 1 cmd"), (0.45, "quack"), (0.8, "nod 2 cmd"), (1.2, "nod 2 bottom"), (1.6, "level")], quacks=[0.45]),
    "yes_lift": Motion("yes_lift", "a preparatory lift (beak up to -0.5 over 0.3 s) then the nod down to +0.7 over 0.35 s, hold 0.1, back over 0.35 s (a bigger, wound-up nod)", 1.9,
                       lambda t: dict(head_pitch=-0.5 * ramp(t, 0.3) + (0.5 + NOD) * ramp(t - 0.3, 0.35) - NOD * ramp(t - 0.75, 0.35)),
                       beats=[(0.3, "lift cmd"), (0.55, "lift joint"), (0.65, "cmd down"), (0.8, "quack"), (1.05, "bottom"), (1.5, "level")], quacks=[0.8]),
}


def pick():
    import json
    pk = json.load(open(HERE / "PICK.json"))
    return MOTIONS[pk["motion"]], Path(pk["wav"]), pk["sound"]


if __name__ == "__main__":
    sys.path.insert(0, "/Users/remi/microduck/notes/emotions/motion/episode3")
    import yesno_common as C
    C.run("yes", MOTIONS,
          header="YES: one nod + one affirmative quack",
          intro="Standing (stand net, twist 0, body pose 0, neck 0). head_pitch positive = beak down; the joint follows the command ~0.4 s late. "
                "The quack lands when the joint reaches the bottom of the nod; the beak follows the wav's loudness 0.15 s late. Simulation 640x480, 30 fps. "
                "Files: <code>/Users/remi/microduck/notes/emotions/motion/yes/</code> (renderer <code>yes.py</code>, sounds <code>sounds/make_yes.py</code>).",
          pick_stem="yes_single__Y2_synth_fall",
          pick_note="One nod, one settled falling quack: the shortest clear 'yes' (motion done in ~1.1 s). yes_double reads as 'yes yes' (eager); yes_lift is a bigger gesture for a farther camera.")
