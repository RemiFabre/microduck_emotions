# NO (episode 3): a short head shake, "no-ah"

Page: `/Users/remi/microduck/notes/emotions/combined/no/index.html` (18 pairs: 3 motions x 6 sounds).
Renderer `motion/no/no.py`, sounds `sounds/make_no.py` -> `sounds/no/`.

## Pick: `no_one` + `N2_synth_m5`

Standing, stand net, twist 0, body pose 0, neck 0, pitch 0, roll 0. Only `head_yaw` moves, through
`swings()` of `expressions.rs` (half-cosine between extremes, fade in / out):

```
YAW = 0.55
head_yaw(t) = swings(t, extremes=[0.35, 0.85], amp=YAW, fade=0.25)
   = 0 before 0.10 s; +0.55 at 0.35 s; -0.55 at 0.85 s; back to 0 at 1.10 s
length 1.8 s
sounds: "no" at 0.60 s (250 Hz, 0.20 s, nearly flat), "ah" at 1.10 s (a fourth lower, 187 Hz, 0.32 s, falling 3 more semitones, -1 dB)
robot wav sounds/robot/no_a.wav (1.45 s; sounds at 0.60 / 1.10 s from the press)
mouth: from the wav's envelope (two openings), as a 0.1 s table
```

| t (s) | command | joint (sim) |
|---|---|---|
| 0.10 | yaw fades in | -0.05 (rest) |
| 0.35 | +0.55 (right) | +0.09 |
| 0.60 | **"no"** | +0.35, right extreme |
| 0.85 | -0.55 (left) | -0.14 |
| 1.10 | **"ah"** | -0.39, left extreme |
| 1.40 | centre | -0.07 |

Measured: no fall, drift 0.1 cm, joint |yaw| max 0.43 (25 deg), jaw 0.98 / 0.99 on the two sounds, 0.30 between.
The joint lags the command by ~0.25 s, which is why the sounds sit 0.25 s after the command extremes.

## Alternatives

- `no_two`: four extremes (+0.5/-0.5/+0.5/-0.5 at 0.3/0.7/1.1/1.5 s), sounds on the first two: emphatic, 2.2 s. Joint 0.37 (faster swings track less).
- `no_beakup`: `no_one` + head_pitch -0.35 held through the shake (joint -0.23): a haughty no; the head's mass goes back, not forward.
- Sounds: `N1_synth_m3` (second a minor third down: barely a second syllable), `N3_synth_m7` (a fifth: the "ah" sinks, close to a growl),
  `N4_nasal_m5` (nasal, buzzy: sulky; robot wav `no_b.wav`), `N5_bank_inquire_greet` (the bank's own inquire quickened then greet slowed: real voice, but the
  greet's tail keeps the beak open ~0.7), `N6_synth_m5_long` (a 0.45 s drawn-out "aaah" sliding 5 more semitones; robot wav `no_c.wav`).
- Rejected before rendering: a shake at yaw 1.0 (the sad/devastated swings use 0.4; 1.0 in 0.5 s would be a thrash).

## Robot notes

Yaw only: nothing moves the head's mass forward. Rémi's choices: interval of the second sound (-3 / -5 / -7), synth vs bank, one or two shakes.
