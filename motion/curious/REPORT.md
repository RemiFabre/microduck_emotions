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
