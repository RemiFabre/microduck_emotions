# Play dead, v3 (Rémi's second feedback, 2026-09-06 evening): head servos off, legs to a dead pose, no re-init

Rémi on v2: "when you re-enable the torque you call a function that also sets all the motors to their default positions;
the pose of the robot on the ground completely changes." His design: once the head is to the side and thrown back, cut the
torque of the HEAD servos only (three: neck_pitch, head_pitch, head_yaw; the roll, the jaw and the legs stay powered); the
legs go to a "dead animal" pose (zero angles = straight, then up); the beak stays powered for the death quack; the robot
holds that pose until his Start (the full init) gets it out. Page: `/Users/remi/microduck/notes/emotions/combined/playdead/index.html`
(v3 pick first, v3 alternatives, then the v2 and v1 picks). Code: `pdduck3.py` (the coming `robot.pose_joints` in
simulation: per-joint torque off = the actuator control zeroed after BAM computes it; the other joints ramped to targets
at one gain, no policy; a second call = `stage2`), `probe3.py` (the v3 probe, `probe3.json`), `playdead.py` (`pd_v3_*`,
`pick()`), `../../sounds/make_playdead.py` (v3 beats -> wavs).

## v3 probe (probe3.py, no video)

Every recipe: sit at 0, head yaw 1.0 over 0-0.5 s, head back -1.0 over 0.4-1.0 s; at `cut` the head servos (the three;
`off4` = the roll too) lose their torque and the legs are ramped over `ramp` s at gain `g` to: `zero` = every leg joint
at 0 (straight), `seated` = the seat's own angles (measured just before the cut: hips -0.51 / +0.54, knees +1.30 / -1.27,
ankles +0.15 / -0.12), `home` = the standing pose, `legsupA` = hips -1.0 / knees +1.5 (mirrored on the right), `E` = hips
-0.8 / knees 1.2 / ankles 0.3, `F` = hips -1.3 / knees 1.5 / ankles -0.3, `B` / `D` = the hips the other way (the legs
fold under: the duck ends tilted past vertical), `two_` = zero first, then legs up once it lies there (a second call).
"gap" = closest head-shell / trunk approach before / after the cut (0 after = the unpowered head rests on the trunk).
"feet z" = the ankles' height at the end (legs up = 7-8 cm; flat on the floor = 1.9 cm).

| recipe | ends (trunk pitch) | leaves upright | at rest | peak trunk rot (rad/s) | peak head v (m/s) | gap before / after cut (mm) | head joints at end (yaw / pitch / neck / roll) | feet z at end (cm) |
|---|---|---|---|---|---|---|---|---|
| v3_zero_cut1.2_ramp0.5_g160 | ON BACK (+91) | 1.64 | 2.1 | 9.64 | 1.11 | 33.0 / 0.0 | 1.12 / -1.65 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.2_ramp1.0_g160 | ON BACK (+91) | 1.76 | 2.36 | 9.03 | 1.01 | 33.0 / 0.0 | 1.23 / -1.6 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.2_ramp1.5_g160 | ON BACK (+91) | 1.88 | 2.72 | 8.54 | 0.95 | 33.0 / 0.0 | 1.27 / -1.55 / -0.31 / 0.05 | [1.9, 1.9] |
| v3_zero_cut1.4_ramp0.5_g160 | ON BACK (+91) | 1.82 | 2.36 | 9.38 | 1.18 | 29.4 / 0.0 | 1.11 / -1.65 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.4_ramp1.0_g160 | ON BACK (+91) | 1.96 | 2.56 | 8.82 | 0.98 | 29.4 / 0.0 | 1.23 / -1.6 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.4_ramp1.5_g160 | ON BACK (+91) | 2.04 | 2.96 | 7.45 | 0.98 | 29.4 / 0.0 | 1.27 / -1.55 / -0.31 / 0.05 | [1.9, 1.9] |
| v3_zero_cut1.7_ramp0.5_g160 | ON BACK (+91) | 2.14 | 2.68 | 9.33 | 1.17 | 29.2 / 0.0 | 1.12 / -1.65 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.7_ramp1.0_g160 | ON BACK (+91) | 2.28 | 2.92 | 7.56 | 1.0 | 29.2 / 0.0 | 1.19 / -1.6 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.7_ramp1.5_g160 | ON BACK (+91) | 2.36 | 3.28 | 7.96 | 0.91 | 29.2 / 0.0 | 1.28 / -1.55 / -0.31 / 0.05 | [1.9, 1.9] |
| v3_zero_cut1.4_ramp1.0_g100 | ON BACK (+91) | 2.0 | 2.66 | 8.71 | 0.96 | 29.4 / 0.0 | 1.22 / -1.59 / -0.31 / 0.05 | [1.9, 1.8] |
| v3_zero_cut1.4_ramp1.0_g200 | ON BACK (+91) | 1.94 | 2.54 | 8.86 | 0.99 | 29.4 / 0.0 | 1.23 / -1.6 / -0.31 / 0.04 | [1.9, 1.9] |
| v3_zero_cut1.4_ramp1.0_g160_off4 | ON BACK (+91) | 1.96 | 2.54 | 8.8 | 0.98 | 29.4 / 0.0 | 1.37 / -1.31 / -0.23 / 0.43 | [1.9, 1.9] |
| v3_seated_cut1.4_ramp1.0_g160 | ON BACK (+72) | 2.5 | 4.18 | 8.44 | 0.83 | 29.4 / 0.0 | 1.42 / -0.56 / 0.54 / 0.03 | [6.6, 6.2] |
| v3_home_cut1.4_ramp1.0_g160 | ON BACK (+81) | 2.0 | 2.74 | 8.0 | 1.01 | 29.4 / 0.0 | 1.38 / -1.05 / 0.11 / 0.04 | [2.8, 2.7] |
| v3_legsupA_cut1.4_ramp1.0_g160 | ON BACK (+90) | 2.5 | 6.06 | 8.35 | 0.91 | 29.4 / 0.0 | 1.35 / -1.54 / -0.31 / 0.05 | [7.8, 7.7] |
| v3_legsupB_cut1.4_ramp1.0_g160 | tilted (+162) | 1.86 | 2.52 | 8.97 | 1.07 | 29.4 / 0.0 | 1.33 / -1.39 / -1.92 / 0.03 | [2.7, 2.9] |
| v3_legsupC_cut1.4_ramp1.0_g160 | ON BACK (+81) | 2.04 | 2.48 | 8.01 | 0.91 | 29.4 / 0.0 | 0.93 / -0.9 / 0.18 / 0.03 | [5.9, 9.8] |
| v3_legsupD_cut1.4_ramp1.0_g160 | tilted (+136) | 1.88 | 2.6 | 8.11 | 1.01 | 29.4 / 0.0 | 1.15 / -1.92 / -1.52 / 0.09 | [2.2, 2.2] |
| v3_zero_cut1.4_ramp1.0_g160_headrollhold | ON BACK (+91) | 1.96 | 2.56 | 8.82 | 0.98 | 29.4 / 0.0 | 1.23 / -1.6 / -0.31 / 0.03 | [1.9, 1.9] |
| v3_legsupA_cut1.4_ramp1.5_g160 | ON BACK (+69) | 2.62 | 5.4 | 8.85 | 0.84 | 29.4 / 0.0 | 1.41 / -0.52 / 0.63 / 0.01 | [7.3, 7.3] |
| v3_legsupA_cut1.7_ramp1.5_g160 | ON BACK (+90) | 2.68 | 4.4 | 8.22 | 0.91 | 29.2 / 0.0 | 1.34 / -1.54 / -0.31 / 0.05 | [7.8, 7.7] |
| v3_legsupE_cut1.4_ramp1.0_g160 | ON BACK (+69) | 2.58 | 3.66 | 8.24 | 0.86 | 29.4 / 0.0 | 1.39 / -0.53 / 0.62 / 0.01 | [6.8, 6.8] |
| v3_legsupF_cut1.4_ramp1.0_g160 | ON BACK (+85) | 2.44 | 2.7 | 7.91 | 1.0 | 29.4 / 0.0 | 0.88 / -0.85 / 0.06 / 0.05 | [5.7, 11.0] |
| v3_two_zero1.4_then_legsupA3.2 | ON BACK (+90) | 1.96 | 2.56 | 8.82 | 0.98 | 29.4 / 0.0 | 1.22 / -1.6 / -0.3 / 0.05 | [7.8, 7.8] |
| v3_two_zero1.4r1.5_then_legsupA3.6 | ON BACK (+90) | 2.04 | 2.96 | 7.45 | 0.98 | 29.4 / 0.0 | 1.28 / -1.55 / -0.3 / 0.07 | [7.8, 7.7] |
| v3_two_zero1.4_then_legsupE3.2 | ON BACK (+90) | 1.96 | 2.56 | 8.82 | 0.98 | 29.4 / 0.0 | 1.22 / -1.6 / -0.3 / 0.05 | [7.5, 7.4] |

Verdict:
- **Every zero-legs recipe rolls the duck flat onto its back (+90 deg)** by 2.1-3.3 s: the straightening legs push the seated
  duck over, the loose head pulls it. The slower the leg ramp the softer: 1.5 s = 7.5 rad/s (the v2 relax gave 7.0, v1's
  soften 6.6), 0.5 s = 9.6. The gain hardly matters (100 / 160 / 200 alike); a later cut (1.7 s) buys nothing.
- **Straight to the legs-up pose** works from a 1.7 s cut (+90 deg) but the duck rocks on its round back for seconds (at rest
  4.4-6.1 s), and from a 1.4 s cut it ends propped at +69 deg; in the rendered candidate (`pd_v3_legsup`, the jaw moving on
  the alarm) it did not even go over: **marginal, rejected**. The seated hold tips slowly and ends propped at +72 deg.
- **Two stages** (zero legs at 1.4 s over 1.5 s, then legs up at 3.6 s over 1 s): the softest fall of the family (7.45 rad/s,
  head 0.98 m/s), flat and still by 3.0 s, then the legs rise to 7.8 cm without moving the body: the pick.
- The unpowered head ends folded back (pitch -1.55, yaw +1.3) resting on the trunk / shoulder (gap 0 after the cut: it is
  the head's own weight, no servo force). With the roll servo off too the head hangs at roll 0.43 (crooked); with it on
  (the pick) roll stays ~0.05.
- Gap BEFORE the cut 29-33 mm (the servos are driving the head then), as in v2.

## The v3 pick: `pd_v3_dead` + `D1_alarm_glide_wobble` (7.5 s from the press)

| t (s) | what | how |
|---|---|---|
| 0.00 | press: sit_toggle fired, alarm played; the head snaps up (shock) AND turns hard to the side | `skill_at_start = SitToggle`, `sound_at_start = PlayDead`; head_pitch -0.5 over 0.12 s; head_yaw 0 -> +1.0 over 0-0.5 s |
| 0.40 -> 1.00 | the head goes back: beak to the sky, still to the side (joint yaw 0.80, pitch -0.73 at 1.4 s) | head_pitch += -1.0 * ramp(t - 0.4, 0.6) |
| **1.40** | **robot.pose_joints #1**: neck_pitch / head_pitch / head_yaw torque OFF; every leg joint ramped to 0 over 1.5 s at gain 160 (head_roll: hold) | `pose_joints(at=1.4, targets=legs 0, off=[neck_pitch, head_pitch, head_yaw], gain=160, ramp_s=1.5)` |
| 2.04 | the duck leaves upright, rolls over backwards (trunk +36 deg at 2.0, +80 at 2.5) | nothing sent |
| 3.00 | flat on the back (+91 deg), still; the head folded back and to the side (yaw 1.33, pitch -1.52), legs flat | |
| **3.60** | **robot.pose_joints #2**: the legs come up over 1 s (hips -1.0 / +1.0, knees +1.5 / -1.5, ankles 0), same off list and gain | `pose_joints(at=3.6, targets=legs up, off=same, gain=160, ramp_s=1.0)`; feet at 7.8 cm by 4.6 s |
| 5.00 -> 6.80 | the death quack; the beak opens to 0.3 (the jaw is powered) | mouth = 0.3 x pulse(t, 5.0, 0.15, 1.05, 0.6) |
| 7.50 | end of the expression: the robot HOLDS the dead pose (no policy) until Rémi's Start (robot.init, all torque on, home) | |

Formulas (padd/src/expressions.rs, `t` from the press; `ramp` = half cosine, `pulse(t, t0, up, hold, down)`):
- `head_pitch(t) = -0.5 * pulse(t, 0.0, 0.12, 0.13, 0.30) - 1.0 * ramp(t - 0.4, 0.6)`; `head_yaw(t) = 1.0 * ramp(t, 0.5)`;
  `neck_pitch = head_roll = 0`; no pose slot; twist forced to zero (sticks locked); the sit skill is over at 1.4 s (the head
  intents after 1.4 s are irrelevant: those servos are off).
- events: sit_toggle + sound at 0.0; **pose_joints at 1.4 s** and **at 3.6 s** with the parameters above (`PICK.json`
  `pose_joints`, targets in `joints_order` = duckfilm.JOINTS: left_hip_yaw, left_hip_roll, left_hip_pitch, left_knee,
  left_ankle, neck_pitch, head_pitch, head_yaw, head_roll, right_hip_yaw, right_hip_roll, right_hip_pitch, right_knee,
  right_ankle; null = hold). No relax, no init.
- mouth table, 0..1 every 0.1 s from the press (69 samples, zero after): `0.000, 0.000, 1.000, 1.000, 0.611, 0.208, 0 x 45 (0.6-5.0 s), 0.225, 0.300 x 11, 0.280, 0.225, 0.150, 0.075, 0.020, 0.000` (exact list: `pd_v3_dead__D1_alarm_glide_wobble.json`
  `mouth` channel, or `../episode3/mouth_table.py` on it).

Measured (sim): tips at 2.04 s, flat at 3.0 s, 16 cm backward travel, peak trunk rotation 7.45 rad/s, head 0.98 m/s, head z
min 2.7 cm; trunk z 4.6 cm at the end (flat), feet 7.8 cm up after stage 2, the body does not move during the leg raise
(trunk pitch 91 -> 90 deg); jaw 1.0 on the alarm, 0.30 on the death quack, shut in between. Robot wav
`sounds/robot/play_dead_a.wav` (6.90 s, -3 dBFS): alarm at 0, death quack 5.0-6.8 s.

Alternatives on the page: `pd_v3_flat` (one stage, legs stay flat, death quack at 3.8 s, 6.2 s: quicker, less of a corpse),
`pd_v3_dead_off4` (the roll servo off too: the head hangs crooked, roll 0.43), `pd_v3_legsup` (straight to the legs-up
pose: did not go over in the render), the pick with D2 (inquire shock + coo sigh).

## Questions for Rémi (v3)

1. The legs-up "twitch" at 3.6 s (two `pose_joints` calls) or the legs left flat (`pd_v3_flat`)? The raise is the "dead
   animal" you described; flat is the quieter corpse.
2. Three head servos off (roll held: the head hangs straight-ish) or all four (crooked, roll 0.43)?
3. On the real robot the unpowered head rests on the shoulder shell (gap 0 in the model): no force, but check the cable.
4. Softness: 7.45 rad/s, head 0.98 m/s onto the back shell, a little harder than v2's relax (7.0). A slower leg ramp
   (2 s) would be softer still; mat first.
5. Gain 160 for the legs while lying (they push against nothing): fine in the model; 100 works the same.

# Play dead, v2 (Rémi's feedback, 2026-09-06 evening)

Rémi on the v1 pick (`pd_faint`): the idea (the head as the lever) is right, but on the real robot the back of the head
would hit the shoulders with only 0.6 of yaw; the head must turn MUCH more and MUCH earlier (from the press, with the sit,
"like devastated, he just turns his head"), then tilt back at once; cut the torque with `robot.relax` (not soften); once the
fall is over, torque back ON (so the beak works and further emotions are possible); the death quack after that.
Page: `/Users/remi/microduck/notes/emotions/combined/playdead/index.html` (v2 pick first, three v2 alternatives, v1 for comparison).
Code: `pdduck.py` (the play-dead duck: relax, then `robot.init` = 2 s ramp to home, then hold; head-shell / trunk gap),
`probe.py` (v2 rows), `playdead.py` (`pd_v2_*`, `pick()`), `../../sounds/make_playdead.py` (v2 beats -> wavs).

## v2 probe (probe.json, v2 rows; no video)

Sit at 0, head yaw 1.0 over 0-0.5 s, head back (-1.0) over the window, `relax` at the time; ON BACK = trunk's back on the floor.
"gap" = closest approach between the head shell and the trunk collision meshes BEFORE the cut (54 mm at the home pose).

| recipe (head back window, relax) | ends | leaves upright | at rest | peak trunk rot (rad/s) | peak head v (m/s) | gap before cut | joints at cut (yaw / pitch) |
|---|---|---|---|---|---|---|---|
| 0.4-1.0, **relax 1.4** (pick) | ON BACK | 2.04 | 2.40 | **7.03** | 0.90 | **27 mm** | 0.84 / -0.73 |
| 0.4-1.0, relax 1.2 | ON BACK | 1.84 | 2.22 | 7.45 | 0.90 | 28 mm | 0.84 / -0.72 |
| 0.4-1.0, relax 1.7 | ON BACK | 2.34 | 2.70 | 7.43 | 0.85 | 27 mm | 0.84 / -0.73 |
| 0.4-1.0, relax 2.0 | ON BACK | 2.64 | 3.34 | 7.65 | 0.85 | 27 mm | 0.83 / -0.73 |
| 0.4-1.0, relax 1.0 (head not back yet) | ON BACK | 1.58 | 2.14 | 8.42 | 0.90 | 36 mm | 0.85 / -0.62 |
| 0.4-1.0, relax 0.8 | **upright** (no fall) | - | - | 2.2 | 0.38 | 48 mm | 0.65 / -0.21 |
| 0.6-1.4, relax 1.8 | ON BACK | 2.48 | 2.82 | 7.66 | 0.89 | 24 mm | 0.85 / -0.72 |
| 0.6-1.4, relax 2.2 | ON BACK | 2.86 | 3.22 | 8.37 | 0.90 | 24 mm | 0.84 / -0.73 |
| 0.4-1.2 to -0.8 only, relax 1.5 | ON BACK | 2.12 | 2.46 | 7.46 | **0.79** | 32 mm | 0.86 / -0.60 |
| 0.4-1.6, relax 1.3 (cut mid-ramp) | ON BACK | 1.90 | 2.58 | 7.89 | 0.86 | 35 mm | 0.88 / -0.53 |
| yaw 0.6 only, 0.4-1.0, relax 1.4 | ON BACK | 2.08 | 4.26 | 7.88 | 0.83 | 23 mm | 0.52 / -0.75 |
| v1: yaw 0.6 late + soften | ON BACK | 2.98 | 4.28 | 6.61 | 0.82 | 23 mm | 0.48 / -0.75 |
| pick + init at 3.0 / 3.5 / 4.0 | ON BACK | 2.04 | 2.40 (+ the ramp) | 7.03 | 0.90 | | init ramp: trunk 0.4 rad/s, head 0.03 m/s; joints at the end yaw 0.02, pitch -0.22..-0.28, neck +0.2 |

Verdict:
- Every v2 recipe lands on the back, sooner than v1 (at rest 2.4 s vs 4.3 s). The torque must be cut once the head is
  back (relax at 0.8 s = no fall; at 1.0 s the head is still travelling and the fall is harder, 8.4 rad/s).
- Softest v2: **relax at 1.4 s** (7.0 rad/s, head 0.90 m/s). The instant cut is a little harder than v1's soften ramp
  (6.6 rad/s), which is the price of Rémi's `relax`. The -0.8 head-back is gentler on the head (0.79 m/s) but the duck
  ends propped at +76 deg instead of flat (the head does not go far enough back to roll it fully): kept as `pd_v2_soft`.
- The sit-stand net tracks the yaw to 0.84 (asked 1.0) and the head back to -0.73 (asked -1.0) while seated. Yaw 1.0
  buys 4 mm of head-shell / trunk clearance in the model (27 mm vs 23 mm): the simulated meshes never touch before the
  cut with either yaw. Whether that is true of the real shells is Rémi's call: the yaw is at the joint's range anyway.
- `robot.init` while lying on the back is gentle: the legs fold to the standing pose and the head straightens (yaw 1.2
  -> 0.02, pitch -0.9 -> -0.25 over the 2 s ramp plus the hold) with 0.4 rad/s of trunk rotation, no roll, no thrash.
  The duck stays where it lies (trunk +78-80 deg, the head shell on the floor, beak 12 cm up).

## The v2 pick: `pd_v2_faint` + `D1_alarm_glide_wobble` (7.6 s from the press)

| t (s) | what | how |
|---|---|---|
| 0.00 | press: sit_toggle fired, alarm played; the head snaps up (shock) AND starts turning hard to the side | `skill_at_start = SitToggle`, `sound_at_start = PlayDead`; head_pitch -0.5 over 0.12 s; head_yaw 0 -> +1.0 over 0-0.5 s |
| 0.50 | head fully to the side (joint +0.51, still turning to +0.84) | |
| 0.40 -> 1.00 | the head goes back: beak to the sky, still to the side (joint pitch -0.59 at 1.0, -0.73 at 1.4) | head_pitch += -1.0 * ramp(t - 0.4, 0.6) (the shock pulse is over by 0.55) |
| **1.40** | **robot.relax sent** (torque off at once) | `relax_at = 1.4`; the sit skill is over |
| 2.04 | the duck leaves upright, keels over backwards on the weight of its head | nothing sent |
| 2.40 | at rest, flat on the back (trunk +80 deg), head on the side (yaw joint 0.9 -> 1.2 as it flops) | |
| **3.00** | **robot.init sent** (torque on, 2 s ramp from where the joints are to the home pose) | `init_at = 3.0` = rest + 0.6 s |
| 3.0 -> 5.0 | the last twitch: the legs fold to the standing pose, the head straightens (yaw -> 0.15 at 5.0, -> 0.04 at 5.5) | the robot holds the home pose afterwards (policy not driving) |
| 5.50 -> 7.30 | the death quack; the beak opens to 0.3 | mouth = 0.3 x pulse(t, 5.5, 0.15, 1.05, 0.6) |
| 7.60 | end | |

Formulas (padd/src/expressions.rs, `t` from the press; `ramp` = half cosine, `pulse(t, t0, up, hold, down)`):
- `head_pitch(t) = -0.5 * pulse(t, 0.0, 0.12, 0.13, 0.30) - 1.0 * ramp(t - 0.4, 0.6)`
- `head_yaw(t) = 1.0 * ramp(t, 0.5)`; `neck_pitch = head_roll = 0`; no pose slot; twist forced to zero (sticks locked)
- events: sit_toggle + sound at 0.0; **relax at 1.4 s** (`robot.relax`, torque off at once); **init at 3.0 s** (`robot.init`:
  torque on + the runtime's 2 s home ramp); after the init the robot holds home (the policy is NOT driving until Start),
  so the runtime must let the mouth intent through while holding (parent's change to robotd). The head/yaw commands
  after 1.4 s are irrelevant (no torque) and after 3.0 s the init owns the joints: the expression may keep sending them.
- mouth table, 0..1 every 0.1 s from the press (74 samples, zero after): the alarm 0.2-0.5 s (from the wav's envelope),
  shut through the fall and the ramp, 0.3 for the death quack 5.5-7.3 s:
  `0.000, 0.000, 1.000, 1.000, 0.611, 0.208, 0 x 50 (0.6-5.5 s), 0.225, 0.300 x 11, 0.280, 0.225, 0.150, 0.075, 0.020, 0.000`
  (exact list: `pd_v2_faint__D1_alarm_glide_wobble.json`, `mouth` channel, or `../episode3/mouth_table.py` on it)
- keyframes: `pd_v2_faint__D1_alarm_glide_wobble.json`; PICK.json has the event times (relax_at, init_at, death_at, rest_at).

Measured (sim, side camera): tips at 2.04 s, at rest 2.40 s, 14 cm of backward travel, peak trunk rotation 7.0 rad/s,
head 0.90 m/s; end trunk pitch +80 deg (flat on the back), beak 12 cm above the floor; head joints at the end yaw +0.02,
pitch -0.27, neck +0.21 (straight); jaw 1.0 on the alarm, 0.30 on the death quack, shut otherwise. No forward drift before
the fall. Robot wav `sounds/robot/play_dead_a.wav` (7.40 s, peak -3 dBFS, 48 kHz mono 16-bit): alarm at 0, death quack 5.5-7.3 s.

### v2 alternatives on the page

- `pd_v2_faint_late`: relax at 1.7 s (the head hangs back 0.7 s before the cut: a beat of suspense), init 3.3, quack 5.8; 7.9 s.
- `pd_v2_soft`: head back to -0.8 only (0.4-1.2 s), relax 1.5: head 0.79 m/s but ends propped at +76 deg, not flat; 7.7 s.
- `pd_v2_slowback`: head back over 0.8 s (0.6-1.4), relax 1.8, init 3.4, quack 5.9; 8.0 s. Flat (+90 deg), 7.7 rad/s.
- `pd_v2_faint` + `D2_inquire_coo_fall`: the coo-voice death sigh on the pick (the inquire shock keeps the beak open longer).

### Questions for Rémi (v2)

1. 7.0 rad/s of trunk rotation and a 0.9 m/s head onto the back shell: test on a mat. If too hard: `pd_v2_faint_late`
   is the same fall (the timing only), `pd_v2_soft` is gentler on the head but ends propped; a soften ramp (v1) was 6.6.
2. The init ramp folds the legs to the standing pose while lying (the "twitch"); on the real robot the legs push against
   the floor for a moment (sim: 0.4 rad/s, no roll). Acceptable? Otherwise a shorter hold: relax again after the quack.
3. The mouth after the init: the runtime gates the jaw on "driving" today (parent is changing it so the jaw answers while
   the robot holds home). Until then the death quack plays with the beak shut.
4. Head side: yaw +1.0 = the duck's left. Flip the sign for the camera.

---

# Play dead v1 (episode 3, first round): shock, sit, keel over backwards, death quack

Written 2026-09-06 by the play-dead fork. Simulation only (nothing was sent to the robot). Page:
`/Users/remi/microduck/notes/emotions/combined/playdead/index.html`. Code: `probe.py` (fall recipes, no video),
`playdead.py` (candidates, page, PICK.json, robot wav), `../../sounds/make_playdead.py` (wavs + `spec.json`).

Brief (Rémi): a combination emotion: surprise quack, sit, then a SOFT fall backwards, head to the side, end fully on the
back with the head on the side, then the beak opens a little and a last death quack. Getting up is Rémi's (Start / rise).

## 1. Fall probe (`probe.py`, `probe.json`): which client-API recipe puts a seated duck on its back, and how hard

The client API has no leg control, so the fall has to come from sit / rise / head / body pose / soften / relax. Every
recipe: sit at t = 0 (seat by ~1 s), then the recipe. `soften` = `robot.soften` (gain 50 at once, to 0 over 1 s while
holding the joints where they were, then torque off; `lib.Duck3` reproduces it). The sit itself peaks at 2.2 rad/s of
trunk rotation and 0.55 m/s of head speed: that is the floor. Orientation: trunk pitch +90 deg = on the BACK.

| recipe | ends | leaves upright (s) | at rest (s) | peak trunk rot (rad/s) | peak head speed (m/s) | head z min (m) |
|---|---|---|---|---|---|---|
| 1_sit_hold1_soften | **upright** | None | 2.5 | 2.2 | 0.59 | 0.048 |
| 1b_sit_hold2_soften | **upright** | None | 3.48 | 2.2 | 0.56 | 0.054 |
| 2_sit_headback_yaw_soften | **ON BACK** | 2.98 | 4.28 | 6.61 | 0.82 | 0.029 |
| 3_sit_rise0.2_soften | **upright** | 2.68 | 4.54 | 4.59 | 0.75 | 0.088 |
| 3_sit_rise0.4_soften | **ON BACK** | 2.9 | 3.12 | 9.08 | 1.39 | 0.028 |
| 3_sit_rise0.6_soften | **ON BACK** | 2.94 | 3.18 | 10.85 | 1.45 | 0.023 |
| 3_sit_rise0.8_soften | **ON BACK** | 3.0 | 3.18 | 9.18 | 1.45 | 0.028 |
| 3_sit_rise1.2_soften | **upright** | None | 4.46 | 3.84 | 0.66 | 0.056 |
| 4_sit_pose-0.2_soften | **ON BACK** | 3.78 | 4.02 | 5.69 | 0.57 | 0.031 |
| 4_sit_pose-0.3_soften | **ON BACK** | 3.94 | 4.18 | 6.27 | 0.55 | 0.031 |
| 5_sit_relax | **upright** | None | 3.96 | 2.2 | 0.55 | 0.067 |
| 6_crouch_headback_soften | **face down** | 2.0 | 2.96 | 6.82 | 1.28 | 0.048 |
| 7_headback_backstep_soften | **face down** | 1.62 | 2.18 | 8.0 | 1.26 | 0.052 |

Verdict:
- **Sit + soften or relax does not fall**: the seated duck just slumps in its seat (recipes 1, 1b, 5). The seat is stable
  without torque.
- **The head thrown back (beak to the sky) + soften** (2) tips the duck backwards as the torque dies: on the back, 6.6 rad/s,
  head 0.82 m/s. The head is the lever: deterministic, and the head slots track seated on the real robot (0.9x).
- **A seated body-pose lean (-0.2 / -0.3) + soften** (4) is the softest that lands on the back (5.7-6.3 rad/s, the head no
  faster than during the sit itself) but works by accident: the sit-stand net trades the pose pitch into the neck (+0.36
  rad backwards), which leaves the duck balanced on the edge of its seat once the torque is gone; it tips 1.3 s after the
  cut and ends propped at +65 deg (feet in the air), not flat. Fragile on the real robot (the seated pose slot "steals the
  neck", episode 2).
- **The sit-stand RISE cut short by a soften** (3, the brief's "straighten the legs" idea): 0.4-0.8 s into the rise the
  duck is up on its heels and goes over backwards every time, but hardest of all (9-11 rad/s, head 1.4 m/s: the net pushes).
  0.2 s is too early (stays up), 1.2 s too late (it stands).
- Standing recipes (6, 7) fall FORWARD (face down): no.

## 2. Candidates (7 videos, side camera)

| motion | recipe | tips (s) | at rest (s) | peak trunk rot (rad/s) | ends |
|---|---|---|---|---|---|
| **pd_faint** (pick) | head back + side, soften 2.2 | 3.02 | 4.78 | 6.5 | on the back (+90 deg), head on the side |
| pd_faint_slow | same, head back over 1.5 s, soften 2.8 | 3.64 | 5.46 | 6.2 | same |
| pd_lean | body pose -0.3 seated + head side, soften 2.4 | 3.46 | 3.80 | 5.5 | propped at +65 deg, feet up |
| pd_legs | rise 0.4 s then soften | 2.74 | 3.06 | 8.5 | on the back (+90 deg) |

Sounds (`sounds/playdead/`): D1 = bank alarm at the press + synth death glide 260 -> 120 Hz with a 5 Hz wobble that
slows and dies (-6 dB); D2 = bank inquire shock + the robot's coo voice falling 230 -> 110 Hz with a dying wobble;
D3 = alarm + the bank's wheee loop backwards on a slowing tape. All three on pd_faint; D1 (+ D2) on the others.

## 3. The pick: `pd_faint` + `D1_alarm_glide_wobble` (7.5 s from the press)

Why: the head is the lever, so the fall does not depend on a balance accident or on the rise net's push; the fall happens
as the torque dies (it cannot be fought by a policy); the alarm is the shock and the wobble dies with the duck.

| t (s) | what | how |
|---|---|---|
| 0.00 | press: sit_toggle fired, alarm played; the head snaps up (shock) | `skill_at_start = SitToggle`, `sound_at_start = PlayDead`; head_pitch -0.5 over 0.12 s |
| 0.55 | the shock releases, the seat lands (~1 s) | head_pitch back to 0 over 0.3 s (0.25-0.55) |
| 1.00 -> 2.00 | the head goes back: beak to the sky | head_pitch 0 -> -1.0, half-cosine ramp |
| 1.20 -> 2.00 | ... and turns to the side | head_yaw 0 -> +0.6, half-cosine ramp |
| 2.20 | **robot.soften sent** (joints held where they are, gain 50 -> 0 over 1 s) | `soften_at = 2.2`; the sit skill is no longer relevant |
| 3.02 | the duck tips backwards on its own weight (torque gone at 3.2) | nothing sent |
| 4.78 | at rest, flat on the back, head on the side (yaw joint ~+1.1 after the flop) | |
| 4.80 -> 6.60 | the death quack; the beak opens to 0.3 at most | mouth = 0.3 x pulse(0.15 s up, hold, 0.6 s down) |
| 7.50 | end of the expression | |

Formulas (padd/src/expressions.rs, `t` from the press), `ramp` = the usual half cosine, `pulse(t, t0, up, hold, down)`:
- `head_pitch(t) = -0.5 * pulse(t, 0.0, 0.12, 0.13, 0.30) - 1.0 * ramp(t - 1.0, 1.0)`
- `head_yaw(t) = 0.6 * ramp(t - 1.2, 0.8)`; `neck_pitch = head_roll = 0`; no pose slot; twist forced to zero (sticks locked)
- `mouth(t)`: the wav envelope for the shock (0.0-0.55 s: 0.0, 1.0, 1.0, 1.0, 0.5, 0.2, 0.0 at 0.1 s steps from
  `pd_faint__D1_alarm_glide_wobble.json`), then `0.3 * pulse(t, 4.8, 0.15, 1.05, 0.6)` (4.8-6.6 s), zero elsewhere
- events: sit_toggle + sound at 0.0; **soften at 2.2 s** (a new thing for an expression: padd must send `robot.soften`
  once at that instant, and stop sending head / mouth intents that the robot would refuse anyway; the head keeps its
  last command until then). After the soften the robot is limp: Start (robot.init) is the way up, Rémi's call.
- keyframes: `pd_faint__D1_alarm_glide_wobble.json` (every 0.1 s, with mouth); `PICK.json` has the event times.

Measured (sim): no forward drift before the fall (the seat), 14 cm backwards during the fall; joints before the cut
neck -0.06, head_pitch -0.75 (the seated net tracks the -1.0 command to about 0.75-0.9), yaw +0.48; peak trunk rotation
6.5 rad/s; head z min 0.03 m; end trunk pitch +90 deg (flat on the back), beak 8.7 cm above the floor (head resting on
its side / the crest). The jaw opens to 1.0 on the alarm and 0.30 on the death quack, shut in between.

Robot wav: `sounds/robot/playdead_a.wav` = the pick's wav from t = 0, trailing silence trimmed (6.70 s), peak -3 dBFS,
48 kHz mono 16-bit, so the shock lands on the press like devastated.

## 4. What the brief asked that is NOT in the pick, and why

- "keep the head forward, straighten the legs softly": the legs can only straighten through the sit-stand RISE net, and it
  pushes hard (pd_legs, 8.5-11 rad/s). The pick uses the head as the lever instead (beak to the sky), which reads as a faint.
- "then the head straightens": impossible after the torque cut, and the fall needs the torque cut (with the sit-stand net
  still driving, a fallen robot triggers robotd's limp-fall + re-home ramp = thrashing on its back). So the head goes to
  its side BEFORE the soften and stays there. The only torque-on alternative is to straighten the head while still
  seated and then fall with a straight head, which loses "head on the side" at the end. Rémi's choice.
- "the beak opens a little and a last death quack": done through the jaw servo alone, 0.3 open. Whether the jaw servo
  still answers `robot.mouth` after `robot.soften` (torque off) on the real robot is unknown to me: if torque off
  includes the jaw, the last quack plays with the beak shut (the sound still plays; sounds bypass the driving gate).

## 5. Questions for Rémi

1. Torque: may play dead END with the duck limp (torque off, as here), with Start as the way back up? A powered variant
   that lies still on its back is not available (the policies fight the floor).
2. Does the jaw (`robot.mouth`) still move after `robot.soften`? If not, accept a shut-beak death quack, or move the
   death quack to before the cut (then the duck quacks while still seated, which is a different gag).
3. The fall's softness on the real robot: sim says 6.5 rad/s, head 0.8 m/s from a 10 cm seat onto the back shell / head.
   Test on a mat first. If it is too hard, pd_faint_slow (same recipe, 6.2 rad/s) or pd_lean (5.5 rad/s, but marginal and
   ends propped at 65 deg) are the softer options on the page.
4. Which side for the head (yaw +0.6 = the duck's left)? Cosmetic; flip the sign for the camera side.
5. Death sound: D1 (synth glide + wobble), D2 (coo voice) or D3 (wheee tape)? All three are on pd_faint.
