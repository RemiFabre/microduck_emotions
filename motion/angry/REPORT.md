# ANGRY (programmatic, X button), episode 3

Rémi's brief: no RL; body-pose control (pitch, height) plus small head moves, aggressive but stable; the beak
must open wide so a held leash drops; angry quacks: hard, short, repeated, on the motion's beats.
Page: `/Users/remi/microduck/notes/emotions/combined/angry/index.html` (12 pairs, the pick first).
Code: `motion/angry/angry.py` (motions, `pick()`), `sounds/make_angry.py` (sounds -> `sounds/angry_v3/`, beats -> `spec.json`).
Renderer: `motion/episode3/lib.py`.

## Pick: `bow_snaps` + `S1_hard_barks` (2.6 s)

Standing on the stand net, twist 0, neck 0 throughout (no head-forward: the real robot would step). Four
barks, one per snap. Each snap = a head-yaw snap (+0.7 / -0.7 / +0.7 / centre) + a short head jab (the beak
goes from up to just below level and back) + a small fast bow on the pose slot. The beak is forced wide open
for 0.4 s at the first bark (the leash release), then follows the wav's loudness.

| t (s) | what | cmd yaw | cmd head_pitch (peak) | cmd body pitch (peak) | joint reached |
|---|---|---|---|---|---|
| 0.15 | snap 1 starts (LEAD 0.15 s before the bark), beak-up baseline ramps in | -> +0.7 | jab to +0.10 | +0.14 | |
| **0.30** | **bark 1**, beak forced wide 0.30-0.70 | +0.7 | | | yaw +0.2 -> +0.6 by 0.8, head_pitch +0.52 at 0.6 |
| 0.75 | snap 2 starts | -> -0.7 | jab to +0.10 | +0.14 | |
| **0.90** | **bark 2** | -0.7 | | | yaw -0.66 by 1.2, head_pitch +0.51 at 1.2 |
| 1.35 | snap 3 starts | -> +0.7 | jab to +0.10 | +0.14 | |
| **1.50** | **bark 3** | +0.7 | | | yaw +0.49 by 2.0, head_pitch +0.57 at 1.8 |
| 1.85 | snap 4 (to centre) starts | -> 0 | jab to +0.10 | 0 | |
| **2.00** | **bark 4** (held, chopped dead at 2.30) | 0 | | | head_pitch -0.04 (beak just up) |
| 2.1-2.5 | beak-up baseline fades out; level at 2.6 | 0 | 0 | 0 | neck -0.21, pitch -0.01, yaw +0.03 |

Between the jabs the head sits at the beak-up baseline (cmd -0.35; joint -0.17..-0.05).

### Formulas (port to `padd/src/expressions.rs`; `ramp` = the same half-cosine, `pulse(t, t0, up, hold, down) = ramp(t - t0, up) * (1 - ramp(t - t0 - up - hold, down))`)

```
LEAD = 0.15; BARKS = [0.30, 0.90, 1.50, 2.00]; ANGRY_LEN = 2.6
up(t)    = -0.35 * ramp(t, 0.3) * (1 - ramp(t - 2.1, 0.4))                      # beak-up baseline
jab(t)   = sum over b in BARKS of 0.45 * pulse(t, b - LEAD, 0.12, 0.05, 0.30)
head_pitch(t) = up(t) + jab(t)          # range -0.35 .. +0.10 (positive = beak down)
head_yaw(t)   = knots(t, [(0.15, +0.7), (0.75, -0.7), (1.35, +0.7), (1.85, 0.0)], 0.12)
                # at each (time, target): half-cosine ramp from the previous target to this one over 0.12 s
neck_pitch = 0, head_roll = 0
pose_at(t) = PoseParams{ pitch: sum over b in BARKS[0..3] of 0.14 * pulse(t, b - LEAD, 0.15, 0.05, 0.25), z: 0, roll: 0, active: true }
             for t < ANGRY_LEN, then one `active: false` (has_pose = true, like Sad)
twist_at(t) = zero (sticks locked) for t < ANGRY_LEN
sound_at_start = SoundTag::Angry (wavs: /var/lib/robot/sounds/angry/angry_a.wav (S1), angry_b.wav (S3 growl + barks, same beats))
skill_at_start = None
```

Mouth table, 0..1 every 0.1 s from the press (the simulation's `mouth` channel: the wav envelope 0.15 s late,
plus the forced wide window 0.30-0.70 s); zero after the table:
```
ANGRY_MOUTH: [27] = [0.000, 0.000, 0.000, 1.000, 1.000, 1.000, 1.000, 0.000, 0.000, 0.000, 0.000, 1.000, 0.423,
                     0.000, 0.000, 0.000, 0.000, 1.000, 0.459, 0.000, 0.000, 0.000, 1.000, 1.000, 1.000, 0.000, 0.000]
```
(0.1 s sampling is coarse for 0.17 s barks: barks 2 and 3 show as one 1.0 sample plus a tail. If the shipped
table can use 0.05 s steps, resample the json's `mouth` instead; the `mouth: 1.0` override for the first
0.4 s matters most: it is the leash release.)

Keyframes with mouth: `motion/angry/bow_snaps__S1_hard_barks.json` (every 0.1 s; `.log.json` every tick).

### Measured (simulation, BAM servos, all-collisions model)

no fall; trunk drift 1.5 cm; trunk pitch -4..+1 deg; joints: neck min -0.35, head_pitch -0.20..+0.57, |yaw| max
0.71, |roll| 0.09; jaw at the barks [1.0, 1.0, 0.96, 1.0]; the head is level again at 2.6 s (neck -0.21 = the
rest value, pitch -0.01).

### Sound `S1_hard_barks` (`sounds/robot/angry_a.wav`, 2.35 s, peak -3 dBFS, rms -22 dBFS)

Four hard barks at 0.30 / 0.90 / 1.50 / 2.00 s: 300 Hz rising 1.5 semitones each, click on the attack, 28 Hz
rasp buzz at full depth, no vibrato, crackle; 0.17 s each, the last one 0.30 s held and chopped dead (no tail).
Alternative shipped as `angry_b.wav`: `S3_growl_barks` = a low 150 -> 260 Hz growl swelling from t = 0 into
the first bark, then one loud 330 Hz bark per snap. Both fit the same beats, so the robot can pick either.
`S2_alarm_grains` (the bank's own alarm honk chopped to 0.2 s) is the "real voice" option; kept on the page.

## What the stand net does with the pose slot (probe, 2026-09-06)

Single body-pitch pulse at t = 0.5 (amp, up time, down = 1.5 x up), standing, head 0:

| amp | up (s) | trunk pitch | drift | neck joint min | head_pitch joint max |
|---|---|---|---|---|---|
| 0.15 | 0.15 | -3 deg | 0.7 cm | -0.28 | +0.63 |
| 0.15 | 0.30 | -3 deg | 1.6 cm | -0.93 | +1.21 |
| 0.15 | 0.50 | -5 deg | 2.0 cm | -1.38 | +1.23 |
| 0.22 | 0.15 | **-21 deg** | **10.9 cm** | -1.48 | +1.24 |
| 0.22 | 0.30 | -27 deg | 4.9 cm | -1.95 | +1.24 |
| 0.30 | 0.15..0.50 | -8..-32 deg | 5-8 cm | -1.15..-1.98 | +1.25 |

So the "bow" of the pose slot is not a polite bow: from ~0.2 the stand net folds the whole duck forward
(trunk -20..-37 deg, neck -1.9, head down +1.2, body drops 6 cm, several cm of drift), which is exactly the
head-forward mass that makes the real robot walk. A small fast pulse (0.14-0.15 over 0.15 s) is a clean push
with the trunk still. Body z (crouch) does nothing visible on the stand net (trunk z unchanged at -0.01..-0.025).
Beak-up (head_pitch -0.3..-1.0) is clean (drift 0.3 cm). Yaw snaps (+-0.6, 0.12 s ramps, every 0.5 s) are
clean and reach +-0.5. Head shivers at 3-4 Hz do NOT move the head (the net answers a step in ~0.3-0.5 s):
use snaps >= 0.5 s apart or slow sweeps. Head jabs (a 0.12 s pulse on head_pitch) come out ~0.3 s late and
overshoot (cmd +0.7 -> joint +0.88): keep them <= +0.5 and lead the bark by 0.15 s.

## Rejected / kept as options

- `crouch_shake_lunge`: beak up with a slow menacing yaw sweep (the growl), then two jabs. Stable (0.7 cm) but the
  jabs reach head_pitch +0.88 (head deep down = the walk risk on the robot) and the barks land while the head is
  still passing level. Good "menace" option if a growl is wanted; would need jab 0.45.
- `beakup_triple_bow`: 0.6 s beak-up then three jabs with yaw +-0.5. Stable (1.1 cm), subtler than the pick (the
  jabs only bring the beak to level); the head returns to the glare after the last bark, then levels at 2.7.
- `double_lunge`: two lunges with a look left-right between. The jabs overshoot to +1.18 (too deep for the robot).
- First round (before the probe): bows of +0.22..0.28 folded the duck (trunk -38..-42 deg, 15 cm drift). Dropped.

## Questions for Rémi

1. Is the 0.4 s forced-wide beak at the first bark enough for the leash to drop, or should the whole first
   second be wide (the wav's own envelope closes between barks)?
2. Menace or scold: the pick is a four-snap scold. If a growl before the barks is wanted, `angry_b.wav` has one
   on the same beats, and `crouch_shake_lunge` has a slow glare sweep.
3. On the robot, the jabs bring head_pitch to +0.5 for ~0.3 s (sad v7 holds +0.5 for seconds and was fine); if
   it still steps, reduce the jab to 0.3 (it stays angry: the yaw snaps and the barks carry it).
