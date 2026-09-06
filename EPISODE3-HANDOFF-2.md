# Episode 3, handoff 2: where things stand (written 2026-09-06 night, for a fresh agent)

Read first: `EPISODE3-HANDOFF.md` (the original brief), `README.md` (the emotion table), `NOTES.md` (the day's log,
"episode 3" sections: every attempt, every decision of Rémi's), `BINDINGS.md` (the pad map, keep it updated),
`combined/episode3/index.html` (the summary page: every pick as a video, the two scene previews, Laureen's video).
Hard rules, unchanged: never make the real duck move from a script or an agent (installs and read-only checks only;
Rémi triggers every motion with the pad; the Reachy Mini may be run when he says so); never push to
`pollen-robotics/*` (GitHub pushes are his); absolute paths in every message; plain English; show results as pages
with videos on his screen. Rémi's speech-to-text writes "dog" for "duck" and "Richie / Reach Mini" for Reachy Mini.

## State of the three repos (everything committed locally; nothing pushed to GitHub)

- **Emotions repo** `/Users/remi/microduck/notes/emotions` (GitHub `RemiFabre/microduck_emotions`, 30+ commits ahead
  of origin): every emotion has `motion/<emotion>/` (renderer, `REPORT.md`, `PICK.json`, keyframes JSON with mouth),
  `sounds/<emotion>/`, a page `combined/<emotion>/index.html`, and `sounds/robot/<tag>_<x>.wav` (48 kHz mono, peak
  -3 dBFS). Shared renderer `motion/episode3/lib.py` (Motion = pure function of time; `Duck3` adds soften; the play
  dead sim duck `motion/playdead/pdduck3.py` adds the scripted joint pose). `motion/playdead/SIM-DIFF.md` = why the
  browser sim fell forward (its sit hands over 0.8 s late). `runtime-pad-expressions.patch` = the runtime branch (28
  commits on top of upstream 2c61dcc).
- **Runtime** `/Users/remi/microduck/microduck`, branch `pad-expressions`, HEAD **fc685a3**, all tests green
  (`cargo test -p padd -p robotd -p duck-ipc-proto -p duck-control -p updater`). Installed on the duck (rev fc685a3,
  verified read-only: version, padd's mapping line, sound folders). Contents: 18 expression kinds in
  `padd/src/expressions.rs` (each with a keyframe test against its simulation JSON), the cue port `padd/src/cue.rs`
  (TCP 7777: express / skill / sound / move / init / policy / stop / ping; a pad must be connected), the short / long
  press emotion mode, `robot.poseJoints` (per-servo torque off + scripted joint targets, `duck-control` gained
  `set_torque_ids`; play dead = two stages at 1.8 / 4.0 s), the mouth intent live while the robot holds with torque
  on, a cued sound opens the beak 0.25 s, `padd.service` allows AF_INET (the cue port was sandboxed out: also fixed on
  the robot with a systemd drop-in). Build: the Docker command in `NOTES.md` (or `ship-to-duck.sh` step 1); install:
  `DUCK_SUDO_PASS=microduck /Users/remi/microduck/notes/emotions/install-on-duck.sh` (robotd keeps a standing robot
  standing across the restart; padd then believes the duck is down: the next Start is an init).
- **Theater** `/Users/remi/reachy_mini_apps/agentic_robot_theater` (GitHub `RemiFabre/agentic_robot_theater`, main,
  ~35 commits ahead): `robot/skit.py` (the Reachy player, now with duck cues, `wait: key`, `say_at`, `cap`,
  `body_yaw` = the whole robot turns (head rotated with the body, moves played in the turned frame), `look_yaw`
  (head-only yaw offset), `pre`, timed `duck_cues`, repeated sounds), `robot/duck_cue.py` (the cue client),
  `scenes/episode3/` (scene.json v3 with tight timing, README with the beat table, the wavs of the same voice
  `0m5sA4wKd4nKxBtRAu0n`), `microduck/sim/episode3_preview.py` (the whole scene in MuJoCo, streams frames).
- **Browser simulator fork** `/Users/remi/microduck/forks/microduck-reachy-simulator` (Space
  `RemiFabre/microduck-reachy-simulator`, pushed, HEAD 8691fb8; remotes origin = the fork, upstream = FormaLau's, never
  push upstream): `src/game/microduck/expressions.js` mirrors `expressions.rs`; the official Reachy wobbler ported
  (`src/game/reachy/speechTapper.js`, `headWobbler.js`); `tools/build-episode3.mjs` compiles the theater scene.json;
  `tools/record-episode3.mjs` records with the installed Chrome (headed; headless never gets past the entrance
  ceremony) to a cfr mp4 with sound; `tools/watch-episode3.mjs` = interactive replay on scene.json changes;
  `EMOTIONS-PORT.md` documents it. Branch `pr/official-wobbler` (worktree `/Users/remi/microduck/forks/mrs-pr`) = the PR
  to Laureen: https://huggingface.co/spaces/FormaLau/microduck-reachy-simulator/discussions/1 (wobbler port + silent
  emotion moves, on her `source/src` tree).

## The pad (emotion mode = DPad-Up tap; short press < 0.6 s / long press held 0.6 s)

A sad / devastated, B excited / impatient, X angry / mock, Y mmh / curious, LB yes / fast yes, RB no / defiant,
L3 laugh / play dead (mat!), R3 free. RT quack, LT wheee, D-pad, Start, Select, sticks unchanged. `pick` is a cue.
Rémi tested rev 8880fa6 on the robot before the remap; his only report so far: the D-pad must stay free (fixed).
Not yet reported: whether angry / excited / laugh (bow pulses) make the duck step, and play dead's fall.

## What is next (Rémi's words)

1. **Test the entire scene on the two physical robots at once**: `DUCK_CUE=192.168.1.29:7777
   robot/run_on_robot.sh scenes/episode3 --start-delay 5` (the Reachy at `pollen@reachy-mini.local` or its IP; the
   duck standing, policy on, pad connected; the leash at the tested pick spot; a mat behind the duck). The player
   waits for ENTER at `duck_rises`. First hardware unknowns: the `body_yaw` turn direction (the duck must be on
   Reachy's RIGHT for +1.4 to be "away"; the head is rotated with the body under the daemon's automatic body yaw:
   watch the first turn), whether recorded moves reset the body yaw, the cue port latency, play dead on a real floor.
2. **Laureen's video, again**: Rémi says the script we filmed is not the one she expected. Fetch upstream, find
   her current script (she edits `source/` in her Space: `source/public/scripts/*.json`; compare with the root copy;
   ask Rémi which one if unclear), apply our patches on top of HER current tree (the wobbler port, silent emotion
   moves, the follow cam `?camera=follow`), film it with `tools/record-episode3.mjs <base> out.webm out.mp4 <script>
   follow` to a NEW file name under `combined/episode3/`, add it to the summary page with a cache-busting URL
   (replaced files show a stale first frame in his browser). Update the PR branch if the port moved.
3. Then Rémi's detailed timing pass on the scene (he wants everything tight; see NOTES for what he already cut).

## Known gaps / doubts

- The browser sim: no BAM servo model, its sit-stand hand-over is late (play dead's clock waits for the seat there),
  two unidentified 404s at boot, her `source/` vs root `src/` split makes merges manual.
- The local MuJoCo preview's Reachy is a puppet (gestures by move name, body turn as a head yaw).
- Rémi's "impatient" move from Laureen's simulator was never found in her source; ours is `motion/impatient/`.
- Devastated stays seated; DPad-Down is the way up (that is why the D-pad is free again).
