# Excited (episode 3): report

Page: `/Users/remi/microduck/notes/emotions/combined/excited/index.html` (14 videos: 4 motions x 3-4 sounds).
Renderer `excited.py` (shared `../episode3/lib.py`), sounds `../../sounds/make_excited.py` -> `sounds/excited/`.
Standing on the stand net, twist 0, neck 0 throughout, no roll on the body pose.

## Finding first: the pose z slot does nothing on the stand net

Probe (`lib.fresh()`, hold a pose for 1.5 s): z -0.025 -> trunk height 0.1157 m, z +0.010 -> 0.1158 (rest 0.1155):
0.2 mm, nothing. The pose PITCH slot does move the body: +0.15 held = trunk 55 mm lower and 21 deg forward. So the
"bounces" of the brief are BOW PULSES on `robot.pose.pitch`: a 0.5 s pulse of +0.15 dips the trunk ~30 mm (the
knees bend) and comes back; at 2 Hz (+0.16) the 0.2 EMA leaves ~23 mm; 0.3 s pulses of +0.12 give 12-16 mm.
The first round with z bounces (motions A and C) showed no body movement at all and was re-done.

## Recommended pick: `excited_wag_pump` + `X2_bank_chirps_up` (3.4 s)

Six head swings that accelerate, the body bobbing on each, the beak climbing higher and higher, a bow flourish
at the end; a bank chirp on each swing, in rising pitch order. Trunk drift 0.6 cm, trunk pitch within -3..+2 deg,
no fall, jaw opens on all six chirps (>= 0.91), shut in between. Runner-up sound: `X1_synth_rise_climb` (synth
quacks, each higher, shorter, rising more). Runner-up motion: `excited_hops` (five bow hops with the head
flipping left/right, 30 mm dips; drift 2.1 cm).

### Beats (s from the press)

| t | what |
|---|---|
| 0.10 | swing 1 starts (yaw ramps to +0.6), beak starts up |
| 0.40 | quack 1 (chirp_a 236 Hz); yaw extreme +0.6; body bob 1 (bow pulse +0.12, 0.25-0.60) |
| 0.95 | quack 2 (chirp_b); yaw -0.6; bob 2 |
| 1.45 | quack 3 (chirp_f); yaw +0.6; bob 3 |
| 1.90 | quack 4 (chirp_e); yaw -0.6; bob 4 |
| 2.30 | quack 5 (chirp_i); yaw +0.6; bob 5 |
| 2.65 | quack 6 (chirp_j 300 Hz); yaw -0.6; bob 6; beak at its highest (-0.70) |
| 2.80-3.35 | bow flourish (+0.12 over 0.2 s, hold 0.05, back over 0.3 s) while the yaw and the beak come back to 0 |
| 3.40 | end (head level, body nominal) |

### Formulas to port to `padd/src/expressions.rs` (`Kind::Excited`)

`Q = [0.40, 0.95, 1.45, 1.90, 2.30, 2.65]` (the quack / swing-extreme times), `ramp` = the half-cosine 0..1 ramp,
`pulse(t, t0, up, hold, down) = ramp(t - t0, up) * (1 - ramp(t - t0 - up - hold, down))`.

- `head_yaw(t)`: knots `K = [Q0 - 0.3] + Q + [Q5 + 0.3]`, values `V = [0, +0.6, -0.6, +0.6, -0.6, +0.6, -0.6, 0]`;
  between knot i and i+1: `V[i] + (V[i+1] - V[i]) * ramp(t - K[i], K[i+1] - K[i])`; 0 outside. (Same shape as
  `swings()` with variable spacing: extremes at Q, fade 0.3 s.)
- `head_pitch(t) = (-0.15 - 0.55 * ramp(t - Q0, Q5 - Q0)) * ramp(t, 0.25) * (1 - ramp(t - (Q5 + 0.35), 0.45))`
  (beak up, climbing from -0.15 to -0.70, back to 0 by 3.45 s). `neck_pitch = 0`, `head_roll = 0`.
- `pose.pitch(t) = min(0.26, sum_i 0.12 * pulse(t, Q_i - 0.15, 0.15, 0, 0.2) + 0.12 * pulse(t, Q5 + 0.15, 0.2, 0.05, 0.3))`,
  `pose.z = 0`, `pose.roll = 0`, `active: true` every tick, released with `active: false` at 3.4 s (`has_pose = true`).
- `twist = (0, 0, 0)` for the whole 3.4 s (sticks locked, like sad / curious).
- sound at start: `SoundTag::Excited` -> `sounds/robot/excited_a.wav` (2.91 s, from t = 0, peak -3 dBFS).
- mouth table, 0..1 every 0.1 s from the press (34 samples, from the keyframes JSON of the pick, zero after):
  `0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 1.000, 0.030, 0.000, 0.000, 0.000, 1.000, 0.445, 0.000, 0.000, 0.000, 1.000, 0.613, 0.000, 0.000, 0.000, 1.000, 0.141, 0.000, 0.000, 1.000, 0.375, 0.000, 1.000, 0.993, 0.318, 0.000, 0.000, 0.000`
- keyframes for the test: `excited_wag_pump__X2_bank_chirps_up.json` (every 0.1 s: neck, head_pitch, head_yaw, head_roll,
  body_pitch, mouth).

### Measured (simulation, stand net)

| motion | fell | drift cm | trunk pitch deg | neck joint min | head_pitch joint | yaw joint max |
|---|---|---|---|---|---|---|
| excited_bounce | no | 1.8 | -4..+1 | -0.45 | -0.48..+0.08 | 0.49 |
| excited_hops | no | 2.1 | -4..+1 | -0.43 | -0.26..+0.25 | 0.57 |
| excited_jumps | no | 1.0 | -3..+1 | -0.56 | -0.82..+0.32 | 0.34 |
| excited_wag_pump | no | 0.6 | -3..+2 | -0.55 | -0.63..+0.14 | 0.62 |

Trunk dips (from the tick logs): bounce 23 mm at 2 Hz, hops 30 mm per hop, jumps 24 mm per crouch, wag_pump 12-16 mm
per swing (+24 mm on the flourish). Head-yaw joint: the stand net follows +-0.6 fully when the swings are 0.45-0.55 s
apart (wag_pump, hops); at 2 Hz (bounce) it only reaches +0.17 on one side and -0.48 on the other (the known
asymmetry). The pose pitch pulls the neck down with it (a +0.14 bow gives neck joint -0.56 and the beak drops
even with head_pitch -0.8 commanded), so the "jumps" read as a wind-up rather than a jump.

### The other candidates and why not

- `excited_bounce` (2 Hz bobs, beak up, 1 Hz wag): lively but the wag is one-sided at that speed; drift 1.8 cm.
- `excited_hops` (5 bow hops, head flipping each hop, beak up): the biggest bobs (30 mm), reads well; drift 2.1 cm,
  just over the 2 cm target; the good alternative if Rémi wants bigger body movement.
- `excited_jumps` (two crouch-and-pop "jumps" with the head thrown up, then a wag): the crouch drops the beak
  (the stand net couples bow and neck) so the "throw up" only shows at the release; the first version with a
  +0.22 bow walked 8 cm. Kept at +0.14 (drift 1.0 cm).
- Sounds: X3 (the bank's "wak" wake-up quacks sped up) is the loudest and quackiest; X4 (wheee start + chirps)
  keeps the beak open through the first 1.1 s (jaw 0.61 between quacks), less "quack quack".

### Questions for Rémi

- Bank chirps (X2) or the synth climb (X1)? Or the giddy "wak" (X3)?
- On the real robot the bow pulses lower the head's mass forward a little (+0.12 for 0.3 s): the sad/curious
  lesson says forward head mass makes the walk policy step. The pulses are short and drift stays 0.6 cm in
  simulation; if the real duck steps, halve the pulse (+0.06) or drop the bobs (head + beak only).
- Is 3.4 s the right length for the scene (beats 1 and 11)? Repeat the swing block for a longer one.
