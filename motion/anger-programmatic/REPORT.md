# Angry foot stomp without training: can the shipped policies fake it?

Written 2026-09-04. Everything here is simulation (CPU MuJoCo proxy with the training servo model: BAM
XL330, 1.75 A firmware limit, 15-30 ms actuator delay, 1-tick joint-velocity lag, the same flags as
`duck-hop`). Nothing was run on the robot. Folder: `/Users/remi/microduck/notes/emotions/motion/anger-programmatic/`
(`index.html` = every clip + contact sheet + the table; `stomp_probe.py` reproduces everything in ~3 min).

Target gesture: lift one foot, slam it down, head snaps LEFT on the first stomp; same foot again, head
snaps RIGHT; ends standing.

## Verdict: yes, a programmatic stomp is usable as a fallback. Use the shipped kick.

`robot.do kick_left` (the `ball_kick_left.onnx` that ships with the runtime, DPad-Left on the film build) is,
without a ball, a real stomp: the left foot rises 68 mm, comes down at 0.81 m/s and is back on the floor 0.36 s
after the trigger; the right foot never leaves the floor; the trunk tilts 6 deg at most; no fall. The standing net
then turns the head 60 deg in 0.3 s. It works twice in a row (B8), with robotd's default 0.5 s kick window, so
**no daemon or config change is needed**: it is a client-side timeline of two skill triggers and four head commands.

What it is NOT: the head snap is not simultaneous with the slam. The kick network owns the head for the whole
kick window (robotd sends it an all-zero command block), so the head can only start turning when the standing
net gets control back, 0.5 s after the trigger: the head reaches 40 deg about 0.3 s after the foot lands, 60 deg at
0.45 s. It reads as "stomp, then glare", not "stomp-and-glare". Also the foot goes forward-and-up (a kick), not
straight up: it reads as a stamp of the foot, which is fine for the gag.

### The exact command timeline (B8, measured in sim; 3.0 s total)

| t (s) | send | what happens (sim) |
|---|---|---|
| 0.00 | `robot.do kick_left` | kick window opens (0.5 s, robotd default `kick_duration`). Foot leaves the floor at +0.16 s, peaks at +0.24 s (68 mm), lands at +0.36 s at 0.81 m/s |
| 0.50 | `robot.head` yaw **+1.0** (left) | standing net is back; head at +40 deg by 0.68 s, +60 deg by 0.80 s, holds |
| 1.10 | `robot.head` yaw **0** | head back near centre in 0.35 s (must be < ~10 deg before the next kick, see rule 1) |
| 1.50 | `robot.do kick_left` | same foot, same kick: 68 mm, 0.81 m/s, lands at 1.86 s |
| 2.00 | `robot.head` yaw **-1.0** (right) | head at -58 deg by 2.30 s |
| 2.60 | `robot.head` yaw **0** | head centred by 2.95 s; standing on two feet, done |

Sound cue: the two "hits" of the angry quack should land at 0.36 s and 1.86 s (foot contact). The head is on
the way to its extreme 0.2-0.4 s after each hit.

Rules learned the hard way:

1. **Never trigger the kick while the head is turned.** With the head still at +56 deg the kick network spends its
   whole window putting the head back and the foot does not move (B1, B2, B3: second kick peak 2 mm). Give the
   head 0.4 s to re-centre before the second trigger (B4/B5/B8 all work).
2. Keep the 0.5 s kick window (or 0.4 s, B5). At 0.3 s (B9) the standing net takes over while the foot is still
   in the air: the slam gets softer (0.69 m/s) and the right foot lifts briefly (planted 93 %).
3. A body-pitch bow (0.25) during the stomp makes the duck fall (A4, C3). Do not add a lean.
4. robotd smooths head intents (EMA, ~0.1 s): expect the head ~0.1 s later on hardware than in the table.

The right foot works as well (B6: 73 mm, 0.93 m/s, other foot planted 93-95 %), so the stomp can be mirrored
if the scene needs it.

## What else was tried (all clips on `index.html`)

| idea | result | usable? |
|---|---|---|
| **Kick skill**, one trigger, head yaw after (B1-B3) | first stomp perfect (68 mm, 0.81 m/s, lands in 0.1 s); second trigger dead because the head was still turned | fixed by B4-B8 |
| **Kick + head re-centre** (B4, B5, **B8**) | two identical stomps, head +-60 deg, no fall, max joint speed 10 rad/s | **yes** |
| Kick, right foot (B6) | 73 mm, 0.93 m/s, twice | yes (mirror) |
| Kick, smaller head yaw 0.6 rad (B7) | same stomp, head +-35 deg | yes, if 60 deg is too much |
| Kick, 0.3 s window (B9) | softer slam, other foot lifts | no |
| **Walking-policy step tricks** (C1-C5): 0.3-0.4 s twist pulses forward / turn / side / backward, head yaw after | a step of 5-20 mm, lowered gently (0.1-0.3 m/s); the two pulses use different feet; the backward pulse with a bow fell | no: not a stomp |
| Happy hop twice (D1) | both feet 40-46 mm up, land at 1.0 m/s, head +-58 deg between hops; drifts forward | a different gesture ("angry jump"), keep as a spare |
| Standing-net body pulses: z bounce (D2), roll shift (D3) | feet stay on the floor (< 4 mm) | no |
| Flamingo cycle r2 lift-and-drop (A1-A6) | **rejected by Remi** (too long, too complex, often falls; the real stomp will be trained like the kick). For the record: the flag-down lowering is gentle (0.36-0.48 m/s over 0.4 s), the policy swings its own head 115 deg during the lift and ignores the head slots; switching to the standing net mid-hold gives a hard 11 cm / 1.05 m/s slam (A5) but the mirrored version fell (A6), and the policy was never run on hardware | no |

Definitions: "peak" = the stomping foot's height above its rest position; "down" = fastest downward speed of that
foot on its way to the floor (free fall from 7 cm would be ~1.2 m/s; a gentle lowering is 0.2-0.5 m/s);
"peak-to-land" = seconds from the top of the lift to floor contact; "other planted" = fraction of the lift window
with the other foot on the floor; head yaw is the measured joint angle, + = the robot's left.

## Files

- `index.html`: all 23 clips (mp4), contact sheets (`*_sheet.png`), the table.
- `B8_kick_recentre_0.5s_robotd.mp4` / `_sheet.png` / `.json`: the recommended timeline.
- `results.json`: the table as data; `<name>.json`: per-tick log (feet heights, contacts, head angles, net).
- `stomp_probe.py`: the probe (`cd /Users/remi/microduck && PYTHONPATH=microduck_rl/src .venv-mjlab/bin/python notes/emotions/motion/anger-programmatic/stomp_probe.py [--only NAME]`); `make_index.py` rebuilds the page.
