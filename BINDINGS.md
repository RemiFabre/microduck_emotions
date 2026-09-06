# Microduck gamepad bindings (film build, branch `pad-expressions`)

Kept up to date with every change of `padd/src/main.rs`. Last change: 2026-09-06 night (episode 3: short / long presses in emotion mode; the triggers and the D-pad keep their jobs).

## Always, in both modes

| control | does |
|---|---|
| **Start** (first press) | torque on, 2 s ramp to the home pose (`robot.init`) |
| **Start** (again) | walking / standing policy on; further presses toggle it |
| **Select** | soft release: gain to 50 at once, to 0 over 1 s, torque off (`robot.soften`). The duck folds |
| **Select** held 3 s | sit down and power off |
| left stick | walk / strafe (drive mode); head mode (Y outside emotion mode): head pitch / yaw; body mode (B outside emotion mode): height / lean |
| right stick | turn (drive mode); head mode: neck / roll; body mode: pitch / roll |
| **RT** | mouth open + chirp on the press ("quack"), in both modes |
| **LT** | mouth open + "wheee" while held, in both modes |
| **DPad-Right** | reboot the servos (after an overload trip), torque off, then Start |
| **DPad-Up** held 3 s | drive mode walk / roller |
| **DPad-Up** tap | **emotion mode on / off** (chirp going in, low tock going out) |

## Emotion mode OFF (the prototype's jobs)

| control | does |
|---|---|
| A | ground pick |
| B | body-pose mode toggle (sticks lean / crouch) |
| X | roulade (held = chained rolls) |
| Y | head mode toggle (sticks pose the head) |
| LB | curious, silent (head tilt right, left, small neck dip, 2 s) |
| RB | peck (head forward twice, 1.7 s) |
| R3 (right stick click) | startled (head up, a step back, 2 s); scream with RT |
| DPad-Left | left kick |
| DPad-Down | sit / stand toggle |

## Emotion mode ON (every emotion = motion + sound; the sticks are locked while one plays)

Each button carries two emotions: a **short press** (released under 0.6 s) and a **long press** (held 0.6 s: it fires at
the threshold, no need to release). RT / LT keep their quack / wheee, the D-pad its jobs (DPad-Down sit / stand: the way
up after devastated), Start / Select / sticks unchanged.

| button | short | long |
|---|---|---|
| A | sad (7.5 s) | devastated (sits, stays seated; 8.5 s) |
| B | excited (3.4 s) | impatient (2.6 s) |
| X | angry (the beak opens wide: a held leash drops; 2.6 s) | mock, "gnagnagnagna" (2.6 s) |
| Y | mmh, "what do you mean?" (2.0 s) | curious (two chirps, tilts; 3.0 s) |
| LB | yes (1.5 s) | yes, fast (1.5 s) |
| RB | no (1.8 s) | defiant (beak up-left quack, up-right quack; 2.2 s) |
| L3 (left stick click) | laugh (3.0 s) | play dead (mat! sits, rolls onto its back, head servos free, legs up; holds until Start; 7.5 s) |
| R3 (right stick click) | free | free |

Not on a button: `pick` (the ground pick with the beak opening on the way down; cue port only).

## Scripted cues (TCP 7777 on the duck, `robot/duck_cue.py` in the theater repo)

`{"express":"yes"}` (any name above, plus `pick`), `{"skill":"ground_pick"|"sit_toggle"|"kick_left"|"kick_right"|"roulade"}`,
`{"sound":"chirp"|"inquire"|"alarm"|"coo"|"greet"|"peck"}` (a cued sound opens the beak for 0.25 s), `{"move":[vx,vy,wz],"for":1.5}`, `{"init":true}` (= the first
Start), `{"policy":true|false}` (= the second Start, on / off), `{"stop":true}`, `{"ping":true}`. A pad must be connected.

Runtime call behind play dead (robotd, film build): `robot.poseJoints {targets: [15 rad or null, JOINT_NAMES order], off: [joint
names whose torque is cut], gain, ramp_s}`: the named servos hang free, the others ramp to their targets and hold, no policy;
`robot.init` (Start), `robot.relax` (Select's soften too) end it.
