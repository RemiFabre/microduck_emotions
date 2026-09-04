# microduck_emotions

Body language and quack sounds for Microduck, designed so that Reachy Mini and Microduck can act emotional scenes
together. Working copy: `/Users/remi/microduck/notes/emotions/` (this repo). Started 2026-09-04.

The rule that guides everything: **sound is paramount**. An emotion is a motion plus a quack designed together,
synchronized beat by beat, and the beak opens with the sound.

## Decided so far

| emotion | motion | sound | status |
|---|---|---|---|
| **devastated** | `motion/sadness/v2/devastated_3x1.0__D3v2_sobs.mp4`: sit (surprise), head droops, three slow head shakes starting while the head is still going down, hold, rise. Beats in `motion/sadness/v2_spec.json` | `sounds/synced_v2/devastated_3x1.0__D3v2_sobs.wav`: inquire shock at the sit, silence, three soft sobs on the head extremes, the third dying into the ending | **Rémi: "perfect"** (2026-09-04) |
| **sad** | standing, head down, three slower shakes (`sad_3x1.3` or `sad_3x1.6`) | `S1v2_glide`: one soft glide starting when the tilt is nearly done, three slow slides | in review (`combined/v2/index.html`) |
| **angry** | RL stomp: three quick stomps on the same foot, head left / right / left (`Mjlab-Stomp-Flat-MicroDuck`, branch `emotions-stomp` of `microduck_rl`, patch in `rl/`) | to design on the trained motion's beats (barks on the foot contacts) | training runs in progress (`motion/anger-rl/REPORT.md`) |

Later: excited, scared (see `HANDOFF.md`).

## Layout

- `HANDOFF.md` the original brief; `NOTES.md` the running log (what was tried, what failed, why; Rémi's decisions).
- `quack.py` Python port of the robot's Rust voice synth (`microduck/sounds`). `Personality(4145077059)` = this robot;
  the random generator is ported exactly (verified sample-exact against the robot's bank). `quack()` renders one
  vocalisation from a pitch contour + envelope + per-sound personality mods.
- `combine.py` muxes one or more wavs into a motion mp4 at given times.
- `reference/` the four Reachy Mini reference sounds as wav (dataset `pollen-robotics/reachy-mini-emotions-library`).
- `sounds/` candidates and generators: `make_A_port.py` (port of the Reachy flute sounds), `make_B_notes.py` (music
  theory), `make_C_grains.py` (bank grains), `make_long_sad.py`, `make_synced.py` / `make_synced_v2.py` (soundtracks
  designed on the motion beats), `make_index.py` (audition page `sounds/index.html`), `analysis/` plots.
- `motion/sadness/` the programmatic sad motions: `sadness.py` (simulation renderer built on
  `notes/reachy-encounter/duckfilm.py`: the duck is driven only through what the real robot accepts), per candidate
  mp4 + contact sheet + keyframe JSON (t, neck, head_pitch, head_yaw, head_roll, body_pitch, skill, mouth), `REPORT.md`
  §0 with the expression formulas, `v2/` the three-swing versions with the beak following the sound.
- `motion/anger-rl/` the RL stomp: report, curves, evaluation videos. `rl/` = patch of the `emotions-stomp` branch
  (env, mdp functions, tests, spec) so it can be re-applied on `microduck_rl`.
- `motion/anger-programmatic/` a rejected probe (kept as a record; its two-stomp claims for B4/B5/B8 are wrong).
- `combined/` sound + motion preview pages: `synced/` v1, `v2/` current.

## How to make a new emotion (the recipe that worked)

1. **Motion first, in simulation**, as a pure function of time on the shipped policies (head deltas, body pitch, a
   skill trigger, mouth). Render candidates with `motion/sadness/sadness.py` as the pattern, contact sheets, a page.
   Rémi picks. Write the beats (droop start/end, extremes, hold, rise) in a spec JSON.
2. **Sound on the beats.** Smooth glides, soft attacks, no brutal transitions for sad emotions (hard hits are fine for
   anger). Shock from the existing bank at a surprise beat, silence where nothing happens, one slide per head movement,
   the last one dying away. Normalise the shock and the phrase to the same level. `make_synced_v2.py` is the pattern.
3. **Beak follows the sound**: RMS envelope at 50 Hz -> mouth open in [0, 1]. Render, mux (`combine.py`), page, open it.
4. **Ship**: expression in `padd/src/expressions.rs` (branch `pad-expressions` of the runtime), new `SoundTag` variants
   in `duck-ipc-proto` + `robotd/src/intents.rs`, wav folder under `/var/lib/robot/sounds/<tag>/`,
   `notes/reachy-encounter/ship-to-duck.sh`.

Environment: `/Users/remi/microduck/.venv-mjlab/bin/python` (numpy, scipy, mujoco, imageio); ffmpeg on PATH.
