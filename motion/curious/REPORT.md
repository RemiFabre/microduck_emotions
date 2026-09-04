# Curious (Y button): head forward, tilt, double rising quack

2026-09-04. Spec `spec.json` (three standing motions, 15 motion+wav pairs), rendered by `curious.py`. Outputs: this folder
(silent mp4, `<motion>__<sound>.json` keyframes with `mouth`, `_beats.png`, `.log.json`) and
`/Users/remi/microduck/notes/emotions/combined/curious/` (muxed mp4s, `index.html`). Camera: three-quarter front.
Stand net at rest (twist 0, body 0), mouth from the wav's RMS (50 Hz, 60 ms smoothing, clip(rms / 0.6 max)), delayed 0.15 s.

Measured (joint angles, simulation), the same for every sound of a motion:

| motion | roll joint at the tilt(s) | neck / head_pitch joints | yaw joint | beak forward | fall |
|---|---|---|---|---|---|
| `curious_tilt` | +0.37 rad (21.7 deg) | -0.53 / -0.39 | -0.10 (coupling) | 1.6 cm | no |
| `curious_two_tilts` | +0.37 then -0.17 rad | -0.56 / -0.42 | -0.10 | 1.6 cm | no |
| `curious_tilt_yaw` | +0.38 rad (22 deg) | -0.54 / -0.40 | +0.22 (0.35 asked) | 1.9 cm | no |

- The roll command +0.27 gives +0.37 rad at the joint (the joint's range in the model is +-0.44; the stand net overshoots
  a little), so the tilt is clearly visible. The tilt to the LEFT is weaker: -0.27 asked gives only -0.17 rad (the same
  asymmetry seen seated: -0.3 -> -0.14). For a symmetric two-tilt, ask more on the left (e.g. -0.44) or accept it.
- Head forward: neck -0.8 gives -0.53 rad and the beak travels 1.6-1.9 cm forward while staying level (head_pitch -0.39
  counter-tilt); for a bigger lunge ask neck -1.2 to -1.5 (the peck uses -1.5 for ~3 cm).
- Jaw: 0.91-1.00 at every quack, 0.00-0.03 outside the sound for Q1/Q3/Q5. Q2 (bank inquire) and Q4 keep the jaw open
  between the two quacks because the sound itself is continuous there (Q2 is audible 0.66-1.30 s as one segment): correct
  behaviour, the beak follows the sound.

## v2 (more roll), pick = curious_two_tilts + Q3_bank_chirp_x2

Spec `spec_v2.json`, page `/Users/remi/microduck/notes/emotions/combined/curious_v2/index.html` (the original pick shown first
for comparison). Roll joint reached (right = +, left = -), measured 0.25 s after each tilt ramp ends:

| variant | asked right / left | joint right | joint left |
|---|---|---|---|
| `curious_two_tilts` (original) | +0.27 / -0.27 | +0.37 rad (21 deg) | -0.17 rad (-10 deg) |
| `curious_two_tilts_r35` | +0.35 / -0.35 | +0.43 rad (24 deg) | -0.26 rad (-15 deg) |
| `curious_two_tilts_r35_leftboost` | +0.35 / -0.44 | +0.43 rad (24 deg) | -0.35 rad (-20 deg) |
| `curious_two_tilts_r44` | +0.44 / -0.44 | +0.44 rad (25 deg) | -0.35 rad (-20 deg) |

The right side saturates near the joint range (+0.44); the left side tops out at -0.35 whatever is asked. `r35_leftboost`
is the most symmetric (+0.43 / -0.35) and 30% more than the original on the right. No fall; jaw on the quacks only.
