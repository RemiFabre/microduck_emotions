# Play dead (episode 3): shock, sit, keel over backwards, death quack

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
