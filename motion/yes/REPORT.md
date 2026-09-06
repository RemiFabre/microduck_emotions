# YES (episode 3): one nod, one affirmative quack

Page: `/Users/remi/microduck/notes/emotions/combined/yes/index.html` (12 pairs: 3 motions x 4 sounds).
Renderer `motion/yes/yes.py` (shared `motion/episode3/lib.py`), sounds `sounds/make_yes.py` -> `sounds/yes/`.

## Pick: `yes_single` + `Y2_synth_fall`

Standing on the stand net, twist 0, body pose 0, neck 0, yaw 0, roll 0. Only `head_pitch` moves
(positive = beak down). `ramp(t, len)` = half-cosine 0 -> 1 as in `expressions.rs`.

```
NOD = 0.7
head_pitch(t) = NOD * ramp(t - 0.05, 0.25) * (1 - ramp(t - 0.40, 0.35))      # = pulse(t, 0.05, up 0.25, hold 0.10, down 0.35)
length 1.5 s (the command is level by 0.75 s; the joint by ~1.1 s)
sound at t = 0.45 s: one quack, 250 Hz falling 3 semitones over 0.30 s   (robot wav sounds/robot/yes_a.wav, 0.80 s, quack at 0.45)
mouth: from the wav's envelope (open 0.45-0.75 s), as a 0.1 s table
```

| t (s) | command | joint (sim) |
|---|---|---|
| 0.05 | nod starts | rest pose head_pitch +0.08 |
| 0.30 | +0.7 reached, hold | +0.29 |
| 0.45 | **quack** (beak opens 0.15 s later) | +0.59, the bottom |
| 0.75 | command back to 0 | +0.57 (the policies follow ~0.4 s late) |
| 1.10 | | +0.16, level |

Measured: no fall, drift 0.1 cm, joint head_pitch +0.08..+0.67 (38 deg of nod), jaw 0.99 on the quack.

## Alternatives on the page

- `yes_double`: two +0.55 nods 0.55 s apart (0.2 s down, 0.05 hold, 0.3 up), one quack on the first; reads as "yes yes" (eager). Joint 0.51.
- `yes_lift`: lift to -0.5 over 0.3 s, then down to +0.7 over 0.35 s, hold 0.1, back over 0.35 s; quack at 0.8 s. A wound-up, bigger nod (joint -0.25..+0.68). First version's 0.2 s / -0.3 lift did not show at all in the joint (-0.02): pulses that short do nothing on these policies.
- Sounds: `Y1_synth_flat` (238 Hz, plain), `Y3_synth_wak` (0.18 s snappy, falls a fourth: curt), `Y4_bank_greet` (the bank's greet_e quickened, the real voice; its decay is long so the beak stays open 0.3 s longer).

## Robot notes

Nothing moves the head forward (neck 0), the head only tips down and back: safe for the walking-forward problem.
Sticks can stay locked for 1.5 s. Questions for Rémi: one nod or two? Flat or falling quack?
