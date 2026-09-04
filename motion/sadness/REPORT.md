# Sadness motion for Microduck: report

## 0. DECIDED (Remi, 2026-09-04): two sad emotions

- **`sad`** = standing, `stand_headdown_shake` unchanged: `/Users/remi/microduck/notes/emotions/motion/sadness/sad.mp4`
  (`sad_sound.mp4`, `sad_sheet.png`, `sad_beats.png`, `sad.json`). 9.3 s in the video; the expression itself is 6.5 s.
- **`devastated`** = with the sit, `sit_headdown_slowshake` with the two yaw shakes starting when the droop is half done
  (they overlap the second half of the droop, which shortens the whole thing by 1 s): `devastated.mp4`
  (`devastated_sound.mp4`, `devastated_sheet.png`, `devastated_beats.png`, `devastated.json`). 10.6 s in the video, 9.5 s
  from the button press to the head back level. Stronger, because the duck has to sit first.
- **`devastated_quick`** = the same with a 1.5 s droop, to compare: `devastated_quick.mp4` etc. 10.35 s in the video.
- **Finding on `sad`**: with body pitch +0.10 the stand net turns the head only ONE way during the shake (yaw joint
  ~0 at the + extremes, -0.41 at the - extremes): it reads as "look aside, back, aside, back" rather than "no". With body
  pitch +0.05 (everything else identical) the shake is two-sided (+0.38 / -0.43 rad) and the head is still deep
  (head_pitch +57 deg, neck -24 deg, vs +70 / -16 at 0.10). Rendered as the option **`sad_twosided`**
  (`sad_twosided.mp4`, `_beats.png`, `.json`); `sad` itself is unchanged, Remi's call.
- None of the three falls. Head angles reached are the same as before (sad: head_pitch joint +70 deg with the trunk level;
  devastated: neck -53 deg + head_pitch +31 deg, beak 9.8 cm lower). In `devastated` the first shake extreme comes at
  3.3 s, when the droop ramp is at 85%: the head is still visibly going down as it starts to shake (see `devastated_beats.png`).

Beat times, seconds on the video clock (sit button pressed at 0.3 s; for `sad` the expression starts at 0.0):

| beat | sad | devastated | devastated_quick |
|---|---|---|---|
| sit button | - | 0.30 | 0.30 |
| seat reached | - | ~1.1 | ~1.1 |
| droop start / end | 0.00 / 2.00 | 1.80 / 3.80 | 1.80 / 3.30 |
| shake window | 2.00 - 6.00 | 2.80 - 6.80 | 2.55 - 6.55 |
| yaw extremes (+, -, +, -) | 2.5, 3.5, 4.5, 5.5 | 3.3, 4.3, 5.3, 6.3 | 3.05, 4.05, 5.05, 6.05 |
| hold | 6.0 - 6.5 | 6.8 - 7.8 | 6.55 - 7.55 |
| rise start / head level | 6.50 / 8.50 | 7.80 / 9.80 | 7.55 / 9.55 |
| video ends | 9.3 | 10.6 | 10.35 |

Exact expression numbers, t in seconds since the button press, `ramp(x, L)` = half-cosine 0..1 over L seconds
(clamped, same as `expressions.rs::ramp`), head_pitch POSITIVE = beak down:

```
sad   (no sit; body pitch +0.10 on robot.pose along the same envelope; duration 6.5 s)
  down(t) = ramp(t, 2.0) * (1 - ramp(t - 4.5, 2.0))
  yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 2.0)) * ramp(t - 2.0, 0.5) * ramp(6.0 - t, 0.5)    for 2.0 <= t < 6.0, else 0
  neck_pitch = -1.5*down(t)   head_pitch = +1.0*down(t)   head_yaw = yaw(t)   head_roll = 0   body_pitch = 0.10*down(t)

sad_twosided   (option: same as sad with body_pitch = 0.05*down(t))

devastated   (robot.do sit_toggle at t = 0; head starts at 1.5 s; stays seated; duration 9.5 s)
  down(t) = ramp(t - 1.5, 2.0) * (1 - ramp(t - 7.5, 2.0))
  yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 2.5)) * ramp(t - 2.5, 0.5) * ramp(6.5 - t, 0.5)    for 2.5 <= t < 6.5, else 0
  neck_pitch = -1.5*down(t)   head_pitch = +1.0*down(t)   head_yaw = yaw(t)   head_roll = 0   body_pitch = 0

devastated_quick   (duration 9.25 s)
  down(t) = ramp(t - 1.5, 1.5) * (1 - ramp(t - 7.25, 2.0))
  yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 2.25)) * ramp(t - 2.25, 0.5) * ramp(6.25 - t, 0.5)  for 2.25 <= t < 6.25, else 0
```

Keyframes every 0.1 s (video clock) are in `sad.json`, `devastated.json`, `devastated_quick.json` (`keyframes`), with the
beat times under `beats`. The sound versions carry the 1.1 s placeholder `A_port_sad2_v4_slow.wav` starting at the droop.

---

# Earlier candidates (the exploration that led to the decision)

Written 2026-09-04. Everything here is simulation (`/Users/remi/microduck/notes/reachy-encounter/duckfilm.py`: the shipped
ONNX policies, the BAM servo model, the duck driven only through the command block the real robot accepts). Nothing was
sent to the real robot. Page with the videos: `/Users/remi/microduck/notes/emotions/motion/sadness/index.html`. Script that
produced everything: `/Users/remi/microduck/notes/emotions/motion/sadness/sadness.py` (`probe`, `render`, `index`).

Terms: **head deltas** = the four numbers a client sends with `robot.head` (neck_pitch, head_pitch, head_yaw, head_roll,
radians, offsets from the home pose) that the policy is asked to track. **Sit-stand net** = the `alpha_sitstand` policy,
which holds the seat while `robot.do sit_toggle` is engaged. **Body pitch** = the pitch slot of `robot.pose`.

## 1. Do the head slots track while the duck is SITTING? Yes, all four

Step sent 3 s after the sit command, measured joint offset after a 1.2 s settle (`probe.json`):

| slot | sitting (sit-stand net) | standing (stand net) |
|---|---|---|
| neck_pitch | -1.50 -> -0.97, -1.00 -> -0.70, -0.50 -> -0.37, +0.50 -> +0.29, +1.00 -> +0.55 | -1.50 -> -0.70, -1.00 -> -0.53, -0.50 -> -0.34, +0.50 -> -0.03, +1.00 -> -0.06 |
| head_pitch | -1.50 -> -1.03, -1.00 -> -0.78, -0.50 -> -0.45, +0.50 -> +0.47, +1.00 -> +0.89 | -1.50 -> -1.37, -1.00 -> -0.96, -0.50 -> -0.41, +0.50 -> +0.58, +1.00 -> +0.98 |
| head_yaw | -1.50 -> -1.18, -1.00 -> -0.87, -0.50 -> -0.49, +0.50 -> +0.47, +1.00 -> +0.88 | -1.50 -> -1.43, -1.00 -> -0.98, -0.50 -> -0.51, +0.50 -> +0.44, +1.00 -> +0.98 |
| head_roll | -0.30 -> -0.14, +0.30 -> +0.26 | -0.30 -> -0.27, +0.30 -> +0.27 |

Plain English:
- **Seated, the head tracks as well as standing, or better.** head_pitch and head_yaw follow about 0.9x the command
  (standing: 1.0x). The neck follows -1.5 -> -0.97 rad seated (standing: -0.70) and, unlike standing, it also goes UP a
  little seated (+1.0 -> +0.55). Roll is asymmetric seated (-0.3 -> -0.14, +0.3 -> +0.26).
- **Seated, neck and head_pitch are traded against each other** when both are commanded: with neck -1.5, head_pitch 0.8
  gives a joint of +23 deg, 1.0 gives +31 deg, 1.5 gives +49 deg, while the neck backs off from -53 to -44 deg. The
  total nose-down angle stays around 80-90 deg. Head_pitch 1.0 with neck -1.5 is a good compromise (used below).
- **Body pitch while seated does nothing useful**: +0.3 tilts the trunk only -7 deg and it steals the neck (only -20 deg
  of neck instead of -53). Do not put a bow in the seated version.
- **Body pitch while standing is non-linear**: +0.10 keeps the trunk level but makes the stand net drop the head much
  further (head_pitch joint +68 deg); +0.15 makes it crouch into a real 29 deg bow with the belly near the floor;
  +0.30 with the head down topples it forward (the runtime's limp-fall fires at 1.3 s, on its face by 2.3 s).
- **The sit takes 0.8 s** to settle (trunk 12.6 cm -> 6.1 cm). robotd's sit works the same way (`control.rs`: "Head and
  body slots stay live" while the sit-stand net holds the seat), so this transfers.
- The policies follow the slow ramps used here without lag (the 2 s droops track within a tick or two).

## 2. The candidates

Same skeleton for all: [sit] -> droop (neck + head pitch down, half-cosine ramp) -> slow yaw shakes ("no") -> hold ->
rise back (or stay down). Numbers are joint angles measured in the simulation, not the commands.

| name | s | fell | head_pitch max (deg, beak down) | neck min (deg) | yaw shake (deg) | beak drop (cm) | trunk pitch max, nose-UP (deg; the nose-down bow of `stand_bow015` is -29 deg, of `stand_bow030` -36 deg before the fall) |
|---|---|---|---|---|---|---|---|
| `sit_headdown_slowshake` | 11.6 | no | +31 | -52 | +-20 | 9.7 | +4 |
| `sit_only_droop` | 8.6 | no | +31 | -51 | +-5 | 9.6 | +3 |
| `sit_headdown_tilt_fast` | 9.35 | no | +37 | -57 | +-14 | 9.9 | +6 |
| `sit_headdown_slower_standup` | 18.51 | no | +31 | -52 | +-28 | 9.7 | +8 |
| `stand_headdown_shake` | 9.3 | no | +70 | -17 | +-24 | 6.3 | +1 |
| `stand_bow015_headdown_shake` | 9.3 | no | +70 | -103 | +-36 | 9.2 | +1 |
| `stand_bow030_headdown_shake` | 9.3 | YES at 2.3 s | +71 | -88 | +-50 | 9.2 | +0 |
| `sit_bow_headdown_shake` | 11.6 | no | +28 | -20 | +-10 | 8.7 | +0 |

- **`sit_headdown_slowshake`** (the pick): sit 1.5 s, droop 2 s, two shakes of +-0.4 rad at 0.5 Hz (4 s), hold 1 s,
  head back up over 2 s, stays seated. 11.6 s including the sit; the sad part (droop to rise) is 9 s. Reads clearly:
  the beak goes from pointing forward to pointing at the floor, the top of the head faces the viewer, then a slow "no".
- **`sit_only_droop`**: same droop, no shake, head stays down. Quieter, 8.6 s, ends seated with the head down. Good if
  the quack alone carries the emotion, or as the end pose of a scene.
- **`sit_headdown_tilt_fast`**: droop 1.2 s with a 0.25 rad head roll, three shakes at 0.8 Hz, rise 1.2 s. Reads more
  "sulky" than sad; the tilt is visible but the faster shake loses the heaviness.
- **`sit_headdown_slower_standup`**: droop 3 s, two shakes at 0.35 Hz, rise 3 s, then the duck stands back up. 18.5 s.
  Works, but only with the Madison rise recipe: hold the sit-stand rise net until the duck has been upright for 0.35 s,
  then the stand net. With robotd's fixed 1 s rise the sim duck toppled (first render fell at 16.1 s); on the real
  robot the README says 1 s is enough, so this is a sim-vs-robot difference to check, not a motion problem.
- **`stand_headdown_shake`**: no sit; body pitch +0.10 (trunk stays level), neck -1.5, head_pitch 1.0. The stand net
  tucks the head far down (+70 deg) into the chest; two shakes; back up. 9.3 s. Readable and safe; the best option when
  the duck must stay standing (e.g. mid-scene next to Reachy).
- **`stand_bow015_headdown_shake`**: body pitch +0.15 on top: the stand net crouches until the belly nearly touches the
  floor, head tucked, then rises. Reads as a collapse/slump more than a bow. No fall, no limp-fall, but dramatic; keep
  as an option for "devastated".
- **`stand_bow030_headdown_shake`**: FAILED. +0.30 body pitch plus the head down = falls forward (limp-fall at 1.3 s, on its face at 2.3 s).
- **`sit_bow_headdown_shake`**: FAILED softly. The seated net ignores the bow and the neck droops less (-20 deg).

Placeholder sound: each candidate also has `<name>_sound.mp4` with the other agents' `A_port_sad2_v4_slow.wav`
(1.1 s) starting when the head begins to droop. A longer quack (2 to 4 s, or a short one at the droop plus a
second one on the shake) would fit the 9 s sad part better; the motion is a target for the sound, not a rule.

## 3. What to put in `padd/src/expressions.rs`

Pattern: `head_at(Kind::Sad, t)` returns the four deltas; the sit is a separate `robot.do sit_toggle` fired at t = 0
by the button handler (the expression does not need a twist). Times below start at the button press.

```
SAD_SIT_WAIT   = 1.5   // the sit-stand net reaches the seat in 0.8 s; head starts down at 1.5
SAD_DROOP      = 2.0   // half-cosine ramp down
SAD_SHAKES     = 2     // slow "no"
SAD_SHAKE_HZ   = 0.5
SAD_HOLD       = 1.0
SAD_RISE       = 2.0   // half-cosine ramp back up
NECK           = -1.5  // tracks to about -0.9 rad seated (the neck only follows downward)
HEAD_PITCH     = +1.0  // POSITIVE = beak down; tracks to about +0.55 rad seated when the neck is also down
YAW_AMP        = 0.4   // +-23 deg; seated yaw tracks ~0.9x
ROLL           = 0.0   // (0.25 for the sulky tilt variant)

down(t) = ramp(t - 1.5, 2.0) * (1 - ramp(t - 8.5, 2.0))            // 0..1, up at 3.5, starts rising at 8.5, level at 10.5
yaw(t)  = 0.4 * sin(2*pi*0.5*(t - 3.5)) * ramp(t - 3.5, 0.5) * ramp(7.5 - t, 0.5)   for 3.5 <= t < 7.5, else 0
neck_pitch = NECK * down(t);  head_pitch = HEAD_PITCH * down(t);  head_yaw = yaw(t);  head_roll = 0
duration = 11.5 s (sit_toggle at 0; the duck stays seated at the end; a second press of the sit button stands it up)
```

Exact keyframes every 0.1 s, in the same units, are in `sit_headdown_slowshake.json` (`keyframes`: t, neck,
head_pitch, head_yaw, head_roll, body_pitch, skill), same for every other candidate. For the standing version use
`stand_headdown_shake.json`: body_pitch +0.10 on `robot.pose` along the same `down(t)` envelope, no sit.

## 4. What failed and why (short)

- Body pitch +0.3 standing + head droop: falls forward (the README's "bow up to +-0.3" was measured without the head
  hanging in front). Keep body pitch <= 0.15 standing, and 0 seated.
- Body pitch seated: no effect on the trunk, steals the neck.
- Standing up after the seated droop with a fixed 1 s rise: fell in the sim; state-based handoff (upright 0.35 s ->
  stand net) works every time. On the robot robotd owns the rise; check it once on hardware.
- First attempt used head_pitch 0.8: only +23 deg of head_pitch joint seated because the sit-stand net trades neck
  against head; 1.0 gives +31 deg with the same neck, which is what the videos show.

## 5. Which one I would pick

`sit_headdown_slowshake` for the "Reachy teaches the duck sadness" scene (the sit makes the duck small, the slow
"no" is the readable beat, and it ends seated, ready for a sound). `stand_headdown_shake` when the duck has to stay
on its feet. Next steps: mix a 3-4 s sad quack on the droop + shake, then ship both as pad buttons and check on the robot
that the sit-stand net tracks the head the way the simulation says (numbers in section 1).

---

# v2 (2026-09-04 afternoon): three swings, slower, beak moving with the sound

Remi's notes after listening: three swings not four; `sad` too intense (slower swings, sound only once the tilt is nearly
done); the beak must move with the sound. Spec from the coordinator: `v2_spec.json` (four motion options with beat
times, eight motion+wav pairs). Built by `v2.py`; outputs in `motion/sadness/v2/` (silent mp4, `<motion>__<sound>.json`
keyframes incl. the `mouth` channel, `_beats.png`) and `/Users/remi/microduck/notes/emotions/combined/v2/` (muxed mp4 +
`index.html`).

- Motions: `devastated_3x1.0`, `devastated_3x1.3` (swings 1.0 / 1.3 s apart, starting while the head is still going
  down: 79% / 86% down at the first swing), `sad_3x1.3`, `sad_3x1.6`. Yaw = three half-cosine swings 0 -> +0.4 -> -0.4
  -> +0.4 -> 0 at exactly the spec's extreme times; everything else the decided envelopes.
- Mouth: the wav's RMS at 50 Hz (20 ms windows), 60 ms smoothing, open = clip(rms / (0.6 max), 0, 1), sent as the
  `robot.mouth` intent (duckfilm's `du.mouth`, the real jaw servo). Verified on close-ups: jaw fully open at the sound
  peaks, shut (<= 0.05) in the silences; the devastated sound also opens it on the "inquire shock" at the sit (0.3 s).
- No falls in any of the 12 renders.
- **Problem found**: the decided `sad` (body pitch +0.10) turns the head only one way on the stand net, so its three
  commanded swings show as ONE visible swing (yaw joint +0.01 / -0.39 / 0.00). The extra `sad_3x1.3_bp05` and
  `sad_3x1.6_bp05` pairs (body pitch +0.05, everything else identical) swing both ways (+0.29 / -0.39 / +0.35) with the
  head still deep (head_pitch +58 deg). Recommendation: make `sad` use body pitch 0.05.

---

# v3 (2026-09-04): sad, shorter and softer. Devastated is decided (devastated_3x1.0 + D3v2_sobs_gentler)

Spec `v3_spec.json`, rendered by `v2.py --v3`. Outputs: `motion/sadness/v3/` (silent mp4, keyframes json with `mouth`,
`_beats.png`) and `/Users/remi/microduck/notes/emotions/combined/v3/` (muxed mp4s, `index.html`). All three motions use
body pitch +0.05 so both swing directions show. Clips are cut at the spec's total (7.8 / 7.6 / 7.4 s).

- `sad_2x1.2`: two swings at 2.6 / 3.8 s (yaw joint +0.28 / -0.38), shake ends 4.4, rise 5.0-7.0.
- `sad_2x1.0`: two swings at 2.5 / 3.5 s (+0.24 / -0.36), shake ends 4.0, rise 4.8-6.8.
- `sad_1x_slow`: one slow swing to +0.33 at 2.8 s (0.8 s out, 1.0 s back), rise 4.6-6.6.
- Beak: opens at 1.96-1.98 s (the sound starts at the end of the tilt), fully open during the 2.2-2.7 s phrase, shut
  (<= 0.08) afterwards. No fall in the six renders. Head 98-99% down at the first swing.

---

# v4 (2026-09-04): sad, the sound descends with the head, the swings are silent

Spec `v4_spec.json`, rendered by `v2.py --version v4`. Outputs: `motion/sadness/v4/` (silent mp4, keyframes json with
`mouth`, `_beats.png`) and `/Users/remi/microduck/notes/emotions/combined/v4/` (12 muxed mp4s, `index.html`). Two motions,
body pitch +0.05, two swings: `sad_droop2.0` (droop 0-2.0 s, swings 2.6 / 3.8 s, rise 5.0-7.0, 7.8 s) and
`sad_droop2.5` (droop 0-2.5 s with the same half-cosine stretched, swings 3.1 / 4.3 s, rise 5.5-7.5, 8.3 s). Six sounds
each, all audible only during the droop. Verified: the jaw opens from 0.06-0.18 s and stays open through the droop, is
shut (0.00) at both swings and after (max 0.06-0.13 in the silences, the EMA tail); yaw joint +0.28 / -0.38 on every
pair; no fall in the 12 renders.
