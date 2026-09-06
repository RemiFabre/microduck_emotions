# Microduck gamepad bindings (film build, branch `pad-expressions`)

Kept up to date with every change of `padd/src/main.rs`. Last change: 2026-09-06 (episode 3, second round).

## Always, in both modes

| control | does |
|---|---|
| **Start** (first press) | torque on, 2 s ramp to the home pose (`robot.init`) |
| **Start** (again) | walking / standing policy on; further presses toggle it |
| **Select** | soft release: gain to 50 at once, to 0 over 1 s, torque off (`robot.soften`). The duck folds |
| **Select** held 3 s | sit down and power off |
| left stick | walk / strafe (drive mode); head mode (Y outside emotion mode): head pitch / yaw; body mode (B outside emotion mode): height / lean |
| right stick | turn (drive mode); head mode: neck / roll; body mode: pitch / roll |
| **RT** | mouth open + chirp on the press ("quack") |
| **LT** | mouth open + "wheee" while held |
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

| control | emotion | length |
|---|---|---|
| A | sad | 7.5 s |
| B | devastated (sits, stays seated) | 8.5 s |
| X | angry (the beak opens wide: a held leash drops) | 2.6 s |
| Y | mmh, "what do you mean?" (roll tilt, muffled rising mmh) | 2.0 s |
| LB | yes (one nod, one quack) | 1.5 s |
| RB | no (one head shake, "no-ah") | 1.8 s |
| L3 (left stick click) | yes, fast ("wak": the same nod, a curt quack) | 1.5 s |
| R3 (right stick click) | laugh (a long "haaa" then a dying run) | 3.0 s |
| DPad-Down | excited | 3.4 s |
| DPad-Left | play dead (sits, head hard to the side and back; at 1.4 s the head servos hang free and the legs straighten: it rolls onto its back; legs up at 3.6 s; death quack; holds the dead pose until Start) | 7.5 s |

Not on a button (cue port only, `{"express": ...}`): `mock` ("gnagnagnagna": the laugh's staccato run with the head rolling, after a scolding), `curious` (Y's former job: tilt right / left on two chirps, 3.0 s),
`pick` (the ground pick with the beak opening on the way down), `peck`, `startled`, `curious_silent`.
More emotions than buttons: curious lost its button to mmh (Rémi, 2026-09-06: mmh is the "what do you mean"
answer the scene needs; curious stays as LB outside emotion mode, silent, and as a cue).

## Scripted cues (TCP 7777 on the duck, `robot/duck_cue.py` in the theater repo)

`{"express":"yes"}` (any name above, plus `pick`), `{"skill":"ground_pick"|"sit_toggle"|"kick_left"|"kick_right"|"roulade"}`,
`{"sound":"chirp"|"inquire"|"alarm"|"coo"|"greet"|"peck"}`, `{"move":[vx,vy,wz],"for":1.5}`, `{"init":true}` (= the first
Start), `{"policy":true|false}` (= the second Start, on / off), `{"stop":true}`, `{"ping":true}`. A pad must be connected.

Runtime call behind play dead (robotd, film build): `robot.poseJoints {targets: [15 rad or null, JOINT_NAMES order], off: [joint
names whose torque is cut], gain, ramp_s}`: the named servos hang free, the others ramp to their targets and hold, no policy;
`robot.init` (Start), `robot.relax` (Select's soften too) end it.
