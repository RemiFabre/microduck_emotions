# Laugh (episode 3): report

Rémi: after Reachy's "Yes. Like that. I still hear you, in my mind." the duck laughs: beak up, head moving left to
right, positive energy, movements of the body. Page: `/Users/remi/microduck/notes/emotions/combined/laugh/index.html`
(9 videos: 3 motions x 3 sounds). Renderer `laugh.py` (shared `../episode3/lib.py`), sounds `../../sounds/make_laugh.py`
-> `sounds/laugh/`, beats in `spec.json`. Standing on the stand net, twist 0, neck 0, no roll on the body pose.

## Recommended pick: `laugh_wag` + `L1_synth_haha` (2.6 s)

Beak up, the head wagging on every other "ha", the body dipping on every "ha", a staccato quack laugh
"ha-ha-ha-ha, (breath) ha-ha-ha". No fall, drift 0.3 cm, trunk pitch within +-2 deg, jaw >= 0.86 on all seven ha's,
shut in between. Runner-up motion: `laugh_roll` (same, with the head rolling side to side instead of yawing: softer,
cuter). Runner-up sound: `L3_giggle_run_haaa` (a rising giggle glide in, the last ha stretched into a falling "haaa").

### Beats (s from the press)

| t | what |
|---|---|
| 0.00 | beak starts up (head_pitch -> -0.55 over 0.3 s) |
| 0.35 | **ha 1**; yaw extreme +0.45; bob 1 (bow pulse +0.10, 0.20-0.55) |
| 0.57 | **ha 2**; bob 2 |
| 0.79 | **ha 3**; yaw -0.45; bob 3 |
| 1.01 | **ha 4**; bob 4 |
| 1.01-1.45 | breath: the body comes back up, the yaw crosses to +0.45 |
| 1.45 | **ha 5**; yaw +0.45; bob 5 |
| 1.67 | **ha 6**; bob 6 |
| 1.89 | **ha 7**; yaw -0.45; bob 7 |
| 2.10-2.50 | beak back to level, yaw back to centre (0.3 s fade after the last swing) |
| 2.60 | end |

### Formulas to port to `padd/src/expressions.rs` (`Kind::Laugh`)

`HAS = [0.35, 0.57, 0.79, 1.01, 1.45, 1.67, 1.89]`, `SWINGS = [0.35, 0.79, 1.45, 1.89]`, `LAUGH_LEN = 2.6`,
`ramp` = the half-cosine 0..1, `pulse(t, t0, up, hold, down)`, `swings(t, extremes, amp, fade)` as in expressions.rs.

- `gate(t) = ramp(t, 0.3) * (1 - ramp(t - 2.1, 0.4))`
- `head_pitch(t) = -0.55 * gate(t)` (beak up); `head_yaw(t) = swings(t, SWINGS, 0.45, 0.3)` (+, -, +, -); `neck = 0`, `head_roll = 0`
- `pose.pitch(t) = min(0.26, sum over h in HAS of 0.10 * pulse(t, h - 0.15, 0.15, 0.0, 0.2))`, `z = roll = 0`, `active: true` every
  tick, released with `active: false` at 2.6 s (`has_pose = true`)
- `twist = 0` for the 2.6 s (sticks locked); no skill; sound at start `SoundTag::Laugh` -> `sounds/robot/laugh_a.wav` (2.11 s from t = 0, peak -3 dBFS)
- mouth table, 0..1 every 0.1 s from the press (23 samples, the simulation's mouth channel = the wav 0.15 s late; zero after):
  `0.000, 0.000, 0.000, 0.000, 0.000, 1.000, 0.529, 0.382, 0.689, 0.000, 1.000, 0.000, 1.000, 0.089, 0.000, 0.000, 0.754, 0.372, 0.265, 0.481, 0.000, 0.737, 0.000`
  (0.1 s sampling is coarse for 0.12 s ha's every 0.22 s; resample the json's `mouth` if 0.05 s steps are possible)
- keyframes: `laugh_wag__L1_synth_haha.json` (every 0.1 s, with mouth).

### Measured (simulation, stand net)

| motion | fell | drift cm | trunk pitch deg | head_pitch joint min | yaw joint | roll joint | trunk dips |
|---|---|---|---|---|---|---|---|
| laugh_wag | no | 0.3 | -2..+2 | -0.52 | +0.33 / -0.55 | 0.06 | 15-17 mm per phrase |
| laugh_bob | no | 0.4 | -2..+2 | -0.33 | +0.18 / -0.44 | 0.08 | 22-24 mm |
| laugh_roll | no | 0.3 | -2..+2 | -0.50 | 0.22 | +0.27 / -0.28 | 15-17 mm |

The ha's are 0.22 s apart, faster than the pose slot resolves (0.2 EMA + the net), so the seven bow pulses merge into
one dip per phrase (the body sinks 15-17 mm for the four ha's, comes up in the breath, sinks again): the body "shakes"
as two dips, not seven. The yaw wag at 0.44 s spacing tracks one-sided (+0.33 / -0.55, the known stand-net asymmetry).
The beak-up baseline holds at -0.5 (30 deg) through the laugh. `laugh_bob`'s head pumps (0.12 s pulses, 0.22 s apart)
are too fast: the joint never goes past -0.33, so it reads as a smaller beak-up with bigger dips.

### Sounds

- `L1_synth_haha` (pick, `sounds/robot/laugh_a.wav`, 2.11 s): seven staccato synth quacks (0.12 s, sharp attack, a click,
  very quacky, 45 % buzz), each 0.7 semitone lower than the last from 300 Hz, the second phrase 1.5 dB softer.
- `L2_bank_chirps_chopped`: the bank's chirps (l, j, i, e, f, b, a: high to low) chopped to 0.12 s and sped up 1.15-1.3x:
  the real voice, but chirps are rising blips, so it reads more as a fast "wek-wek-wek" than a laugh.
- `L3_giggle_run_haaa`: a rising 0.32 s giggle glide (220 -> 330 Hz) 0.3 s before the run, the run, the last ha stretched
  into a 0.45 s falling "haaa". The giggle keeps the beak open 0.6 between ha 1 and 2 (the glide's tail).

### Questions for Rémi

- Wag (pick) or roll (`laugh_roll`, cuter)? Plain staccato (L1) or with the giggle in / "haaa" out (L3)?
- 2.6 s with seven ha's; a longer laugh = repeat the phrase (add 1.1 s per phrase).
- The bow pulses put the head's mass forward a little (+0.10 for 0.35 s, like excited's bobs): if the real duck steps,
  halve them or drop them (head + beak only).
