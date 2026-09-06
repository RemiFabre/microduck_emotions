# Quack with the beak closed (episode 3): sound-only emotion variants

For the scene: the duck holds the leash in its beak and answers Reachy without opening it. The mouth intent is
forced to 0 for the whole emotion (`mouth_mode='closed'` in the renderer; on the robot: `mouth_at` returns 0).
Page: `/Users/remi/microduck/notes/emotions/combined/closed/index.html` (4 cards). Renderer `motion/closed/closed.py`,
sounds `sounds/make_closed.py` -> `sounds/closed/`.

## Pick: `closed_grumble` + `C2_grumble` (robot wav `sounds/robot/closed_a.wav`, 1.4 s)

```
head_yaw(t) = -swings(t, [0.6, 1.05], 0.25, 0.25)     # -0.25 at 0.6 s, +0.25 at 1.05 s, centre by 1.5 s; neck 0, pitch 0, roll 0
length 2.2 s; sounds at 0.50 s (190 -> 175 Hz, 0.32 s) and 0.95 s (185 -> 150 Hz, 0.42 s, -1 dB): two nasal low buzzes,
low-passed at 900 Hz (Butterworth 2nd order), brightness 0.05, nasal 1.0, AM buzz 0.55 at 19 Hz. mouth = 0 throughout.
```

Measured: no fall, drift 0.1 cm, joint |yaw| 0.20, jaw 0.00 everywhere.

## The others

- `closed_chirps` + `C1_curious_chirps`: the shipped curious sound (`sounds/robot/curious_a.wav`, chirps at 0.6 / 1.2 s) with a roll wobble +-0.2
  instead of the tilt, beak shut. Friendly answer. On the robot this is `Kind::CuriousQuacks` with mouth 0 and roll 0.2 (joint 0.21).
- `closed_mmh` + `C3_mmh`: a muffled rising "mmh?" (205 -> 300 Hz, 0.45 s, low-passed 1.1 kHz) with a +0.22 roll tilt: a question through the leash.
- `closed_grumble_still`: the grumble with no head motion at all (if the leash must stay perfectly still).

## Robot notes

No pitch, no neck: the beak's grip on the leash is not disturbed. The muffling is baked into the wav (the robot cannot filter live).
