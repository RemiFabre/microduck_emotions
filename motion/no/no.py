#!/usr/bin/env python
"""NO: a short head shake left-right, two sounds "no-ah" (the second lower) on the two yaw extremes.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/motion/no/no.py [--only SUBSTR] [--no-open] [--no-render]

Standing, stand net, twist 0, body pose 0, neck 0. Yaw swings are expressions.rs::swings (half-cosine through the
extremes, fade in/out). Sounds from sounds/make_no.py (spec.json). Outputs here + combined/no/index.html.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/remi/microduck/notes/emotions/motion/episode3")
import lib  # noqa: E402
from lib import Motion, pulse, swings  # noqa: E402

HERE = Path(__file__).resolve().parent
YAW = 0.55          # yaw command at the extremes (joint tracks ~1:1 with ~0.25 s lag)

MOTIONS = {
    "no_one": Motion("no_one", "one shake: yaw fades in from 0.1 s, +0.55 at 0.35 s, -0.55 at 0.85 s, back to centre by 1.15 s (command); joint ~0.25 s behind", 1.8,
                     lambda t: dict(head_yaw=swings(t, [0.35, 0.85], YAW, 0.25)),
                     beats=[(0.35, "cmd right"), (0.6, "quack 1 / right"), (0.85, "cmd left"), (1.1, "quack 2 / left"), (1.4, "centre")], quacks=[0.6, 1.1]),
    "no_two": Motion("no_two", "two shakes: extremes +0.5 / -0.5 / +0.5 / -0.5 at 0.3, 0.7, 1.1, 1.5 s, centre by 1.8 s; the two sounds on the first two extremes, the rest silent", 2.2,
                     lambda t: dict(head_yaw=swings(t, [0.3, 0.7, 1.1, 1.5], 0.5, 0.25)),
                     beats=[(0.3, "cmd right"), (0.55, "quack 1"), (0.7, "cmd left"), (0.95, "quack 2"), (1.1, "right"), (1.5, "left"), (1.85, "centre")], quacks=[0.55, 0.95]),
    "no_beakup": Motion("no_beakup", "no_one's shake with the beak lifted (head_pitch -0.35 over 0.3 s, held through the shake, back over 0.4 s): a haughty no", 1.9,
                        lambda t: dict(head_yaw=swings(t, [0.35, 0.85], YAW, 0.25), head_pitch=-0.35 * pulse(t, 0.0, 0.3, 0.85, 0.4)),
                        beats=[(0.3, "beak up"), (0.6, "quack 1 / right"), (1.1, "quack 2 / left"), (1.4, "centre"), (1.6, "beak level")], quacks=[0.6, 1.1]),
}


def pick():
    import json
    pk = json.load(open(HERE / "PICK.json"))
    return MOTIONS[pk["motion"]], Path(pk["wav"]), pk["sound"]


if __name__ == "__main__":
    import yesno_common as C
    C.run("no", MOTIONS,
          header="NO: a short head shake + two sounds, 'no-ah'",
          intro="Standing (stand net, twist 0, body pose 0, neck 0). head_yaw +-0.55 rad command (joint about 1:1, ~0.25 s late). The first sound lands on the "
                "right extreme, the lower second one on the left extreme; the beak follows the wav's loudness 0.15 s late. Simulation 640x480, 30 fps. "
                "Files: <code>/Users/remi/microduck/notes/emotions/motion/no/</code> (renderer <code>no.py</code>, sounds <code>sounds/make_no.py</code>).",
          pick_stem="no_one__N2_synth_m5",
          pick_note="One shake, 'no' then 'ah' a fourth lower: the drop is clear without sounding like a different duck (-7 is close to a growl, -3 is barely a second syllable). "
                    "no_two is the emphatic version; no_beakup adds attitude but lifts the head's mass a little (fine on the real robot: the mass goes back, not forward).")
