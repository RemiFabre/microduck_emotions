# Microduck emotions: running notes

Started 2026-09-04. Brief: `/Users/remi/microduck/notes/emotions/HANDOFF.md`.
Everything lives under `/Users/remi/microduck/notes/emotions/`.

## Layout

- `reference/` : the four Reachy Mini reference sounds as 48 kHz mono wav (`sad2`, `irritated2`, `frustrated1`, `reprimand3`), extracted from the HF dataset cache.
- `quack.py` : Python port of the robot's Rust voice synth. `Personality(4145077059)` is this robot. The random generator is ported exactly: the six bank files checked (alarm a-c, peck a-c) match the robot's real bank to the sample. Use `.venv-mjlab/bin/python` (needs numpy + scipy).
- `sounds/sadness/`, `sounds/anger/` : candidate wavs. Prefix = strategy: `A_` port of the Reachy sound, `B_` programmatic music theory, `C_` grains cut from the robot's real bank. Each strategy writes a `manifest_<letter>.json` (file, one-line description, duration).
- `sounds/index.html` : audition page (one row per candidate, play button, description).
- `motion/sadness/` : programmatic sadness motion, simulated with `notes/reachy-encounter/duckfilm.py`; one mp4 per candidate + `index.html` + the head-delta timelines as JSON (portable to `padd/src/expressions.rs`).
- `motion/anger-rl/` : the RL stomp: design spec, smoke-test results, videos.
- `motion/anger-programmatic/` : can a stomp be faked with the shipped policies (kick skill, flamingo lift-and-drop)?

## Facts learned

- **Sound tags on the robot are a fixed enum** (`duck_ipc_proto::SoundTag`: alarm, greet, inquire, peck, chirp, coo, wheee). `robotd` plays a random wav from `/var/lib/robot/sounds/<tag>/`. A new emotion sound therefore needs a new enum variant in the runtime build we ship (proto + robotd + padd), or `aplay` over ssh for tests. Not blocking for candidate design.
- **Reference sounds** (crude pitch tracking, 20 ms hops): `sad2` = one ~1 s call, falls from ~350 Hz to ~120 Hz, in 5.7 s of mostly silence. `irritated2` = 1.6 s growl at 420-520 Hz, slight rise at the end. `frustrated1` = 2 s tone falling slowly 630 -> 460 Hz with decaying energy. `reprimand3` = a series of short "tsk" notes over 2.6 s. All are quiet files (peak 0.11-0.20), so the ported versions are normalised to -3 dBFS.
- **Reachy sad2 motion**: head pitches down 22 deg and sinks 18 mm over 2 s, holds ~2.5 s with two slow yaw wobbles (+-8 deg), rises back over 2 s. Antennas droop. Total 7.3 s.
- **This robot's voice** (seed 4145077059): pitch centre 238 Hz, register low, glide bias -0.67 (falls naturally), quackiness 0.63, AM buzz 22.8 Hz, vibrato 6.1 Hz / 0.37 semitones, attack soft (0.19), speed 0.90.

## Log

- 2026-09-04 morning: read the brief, extracted references, ported the synth, launched parallel work: three sound strategies, sadness motion in sim, anger RL env design + smoke, programmatic stomp probe.

## Shipping a new sound to the robot (scoped, not done yet)

Three small edits in the runtime clone (branch `pad-expressions`), then `notes/reachy-encounter/ship-to-duck.sh`:
- `duck-ipc-proto/src/lib.rs` ~line 1588: add `Sad` and `Angry` to `enum SoundTag` and to `as_str()` (folder names `sad`, `angry`).
- `robotd/src/intents.rs` ~line 321: add them to the `take_sounds()` list (a bitmask by enum index).
- `padd`: bind the emotion buttons to `request_sound` + the expression.
The wavs go to `/var/lib/robot/sounds/sad/*.wav` and `/var/lib/robot/sounds/angry/*.wav` (robotd picks a random wav in the tag folder; extra folders are not part of the seeded bank, so re-copy them after any `sounds ensure-bank --force`). For a quick test without a rebuild: `scp` the wav and `aplay` it over ssh.
- 2026-09-04 late morning: first sound batch on screen: `sounds/index.html` (34 candidates: A port x12, B music theory x12, C bank grains x10). Strategy B's own bets: sadness `B_sigh_glide`, `B_lament_tetrachord`; anger `B_double_bark`, `B_growl_to_bark`, `B_flat_then_chopped`. Its doubt: anger AM buzz at full depth may sound like a helicopter; the knob is `ANG["am_depth"]` in `sounds/make_B_notes.py`.
- Strategy C (grains from the real bank) done: 10 files, `sounds/make_C_grains.py`. Its bets: sadness `C_wheee_fall` (the bank's rising wheee played backwards at 0.6x = sad2's 350->120 Hz fall in real quack timbre), `C_inquire_sigh` (sigh + smaller sob); anger `C_alarm_peck_rasp` (closest to irritated2), `C_greet_bark` (blunt shout). Caveat: several sad tails go below 120 Hz, which the robot's small speaker may not reproduce; if so shift the tape curves up 3-5 semitones.
- Strategy A (port) done: 12 files, `sounds/make_A_port.py` (+ `analyze_ref.py`, plots in `sounds/analysis/`). Finding: sad2 is NOT a smooth glide: it slides 340->235 Hz over 0.35 s, then drops a clean octave to ~118 Hz and fades; the trimmed call is only 0.76 s. `A_port_sad2_v1..v3` reproduce the step, `v5` is the one-glide version, `v4` stretches it to 1.06 s. Anger ports track the flute contours almost exactly; the un-transposed ones (420-630 Hz held growls) may read as kazoo, the down-5/7-semitone ones sit in the duck's register. `A_port_reprimand3_v3_barks` is A's own bet for anger. All three sound strategies are now on the page (34 candidates). Not yet listened to by anyone: Rémi judges.
- 2026-09-04 late morning, sadness motion (sim): the head slots DO track while seated on the sit-stand net (head_pitch/yaw ~0.9x, neck -1.5 -> -0.97, better than standing). 8 candidates rendered in `motion/sadness/` (`index.html`, one mp4 + contact sheet + keyframe json each, `REPORT.md`). Pick: `sit_headdown_slowshake` (sit, 2 s droop with neck -1.5 / head_pitch +1.0, two +-0.4 rad shakes at 0.5 Hz, 2 s rise, stays seated, 11.6 s). Standing version `stand_headdown_shake` (body pitch +0.10). Failed: body pitch +0.3 standing + head down falls; body pitch seated does nothing and steals the neck; a fixed 1 s rise after the seated droop toppled the sim duck (state-based handoff works).
- Sadness motion done (`motion/sadness/index.html`, REPORT.md). Pick: `sit_headdown_slowshake` (sit, 2 s droop, two +-0.4 rad head shakes at 0.5 Hz, hold, 2 s rise; 11.6 s, no fall, beak drops 9.7 cm). Measured: all four head slots track while seated (0.9x), neck reaches -0.97 rad seated; body pitch while seated does nothing; body pitch +0.3 standing with head down falls. The sad part lasts 9 s, so five "L_" long/layered sad sounds were added (`sounds/make_long_sad.py`) and six sound+motion previews are in `combined/` (sound starts at 1.8 s, when the droop begins).
- Rémi (voice, 2026-09-04 midday): the stomp must NOT build on flamingo (too long, too complex, falls). Train from scratch on the kick recipe: a short one-shot. Both the RL agent and the fallback probe were redirected.
- 2026-09-04 midday, programmatic stomp probe (`motion/anger-programmatic/`, 23 sim clips, `REPORT.md`): **the shipped kick is a usable stomp fallback** — `robot.do kick_left` without a ball lifts the left foot 68 mm and slams it at 0.81 m/s (floor contact 0.36 s after the trigger), other foot planted, no fall; the standing net then snaps the head ±60° in 0.3 s. Timeline: kick @0, head +1 @0.5, head 0 @1.1, kick @1.5, head −1 @2.0, head 0 @2.6 (3 s). Rule: the kick net does nothing if triggered with the head turned (re-centre 0.4 s first). Head snap lags the slam by ~0.3 s (kick net owns the head during its 0.5 s window). Walking-policy twist pulses give 5-20 mm gentle steps (no); happy hop = a two-foot slam at 1.0 m/s (spare "angry jump"); flamingo lift-and-drop rejected by Rémi (kept on the page for the record).
- Programmatic stomp probe (`motion/anger-programmatic/`): the shipped `kick_left` skill with no ball IS a stomp (left foot up 68 mm, down at 0.8 m/s, lands 0.36 s after the trigger, other foot planted, no fall, head yaw +-60 deg from the standing net afterwards). BUT the probe's claim that B4/B5/B8 give TWO stomps is false: I scanned the raw logs and those clips have one lift and a dead second trigger; the stats code copied stomp 1 into stomp 2. Only B9 (0.3 s kick window, two left lifts 67/62 mm) and B6 (left then right foot) really double-stomp. The agent was sent back to fix the stats, the page and the report, and to find out why the second trigger dies with the 0.5 s window. Anger sound+motion previews were built on B9 (contacts 1.48 s and 2.66 s) in `combined/index.html`, with two new short anger sounds (`B_single_bark`, `B_growl_bark_short`) sized to land on a foot contact.
- **Decided by Rémi (2026-09-04 midday)**: two sad emotions. `sad` = `stand_headdown_shake` (standing, body pitch +0.10, head down, slow shake). `devastated` = `sit_headdown_slowshake` (the surprise is so strong the duck has to sit), with the shake starting when the head is half lowered, to quicken the whole move. The sadness agent is re-rendering `devastated` (+ a quicker variant) and renaming. Sound choices: Rémi will give input soon.
- **Decided by Rémi (voice, 2026-09-04 early afternoon)**: anger = the RL stomp ONLY. No programmatic fallback ("I want an original movement; even a short foot lift is a balance problem, so it must be trained"). Possibly THREE stomps in short succession on the same foot, head moving with them. The probe agent was stopped; its folder `motion/anger-programmatic/` stays as a record (its two-stomp claims for B4/B5/B8 are wrong, see above); the anger previews were moved to `combined/dropped/`. The RL agent was told to make the stomp count a constant, default three.
- 2026-09-04 midday, sadness DECIDED by Rémi: `sad` = standing (`stand_headdown_shake`), `devastated` = with the sit (`sit_headdown_slowshake`, shakes now start at the droop midpoint: droop 1.8-3.8 s, shakes 2.8-6.8 s, rise 7.8-9.8 s, 10.6 s video / 9.5 s expression), plus `devastated_quick` (1.5 s droop) to compare. Files and exact envelopes: `motion/sadness/REPORT.md` §0 and the "Decided" box on `motion/sadness/index.html`. Finding: in `sad` the yaw shake is one-sided (body pitch +0.10 blocks the + side on the stand net); `sad_twosided` (body pitch +0.05) shakes both ways, offered as an option.
- Decided sad motions rendered (`motion/sadness/`: `sad`, `devastated`, `devastated_quick`, plus option `sad_twosided`; REPORT.md §0 has the beat tables and expression formulas). `devastated` is now 10.6 s of video (9.5 s from the button), shake starts at 2.8 s while the head is 78% down. Finding: in `sad`, body pitch +0.10 makes the stand net shake the head one way only; +0.05 gives a two-sided shake with the head still deep (`sad_twosided`). Rémi to choose. Sound+motion previews rebuilt on the decided motions in `combined/index.html` (8 clips); old ones in `combined/dropped/`.
- Anger RL env DONE up to the smoke test (branch `emotions-stomp` of microduck_rl, commits 4a86aad + 65a0a5e, nothing pushed). Kick recipe, from scratch, groundcontact model, 3 s episode, no clock in the obs, `N_STOMPS = 3` (0.5 s apart, head left/right/left). Spec: `microduck_rl/docs/superpowers/specs/2026-09-04-angry-stomp-design.md`. Report: `motion/anger-rl/REPORT.md`. 14 cfg tests pass; local Warp smoke OK; HF smoke job `6a9a87dee686246ca69a0c64` COMPLETED (private repo `pollen-robotics/stomp-smoke-20260904-1056`, ONNX exported, ≈ $0.04). NOT trained: waiting for Rémi's go on the ≈ $2.2 run (command in REPORT.md). Main risk: with no clock and three stomps, stomps 1 and 3 share the head side, so the policy has less to "count" with; plan B in the spec.
- Rémi (voice, afternoon): sound direction. The best three were `A_port_sad2_v5_glide`, `C_coo_slide_v1`, `C_inquire_sigh_v1`; the others too aggressive (brutal transitions). Wants glides/slides, sounds designed ON the decided motions: devastated = a short shock from the existing bank at the sit, silence while sitting, then a lament oscillating with the head, one slide per head swing. Done: `sounds/make_synced.py` -> 8 devastated + 6 sad soundtracks (wav in `sounds/synced/`, videos + page in `combined/synced/index.html`, opened). Timing verified on the loudness trace (shock 0.2-0.5 s, silence, lament 3.2-7.5 s for devastated).
- Rémi (voice, afternoon): GO for the anger RL training, cost not an issue, iterate without asking. The RL agent is launching `stomp-r1` (4096 envs, 2000 it, ≈ $2.2) and will evaluate in both engines, then iterate up to 4 runs.
- 2026-09-04 11:11: anger RL, run r1 launched (Rémi: go, cost not an issue). `Mjlab-Stomp-Flat-MicroDuck` (three stomps, right foot, 0.5 s apart, head L/R/L, 3 s episode, kick recipe), 4096 envs x 2000 it, rtx-pro-6000, job `6a9a8b35e686246ca69a0cdf`, repo `pollen-robotics/stomp-r1-20260904-1111` (private), ≈ $2.2. Design + smoke history: `motion/anger-rl/REPORT.md`, spec `microduck_rl/docs/superpowers/specs/2026-09-04-angry-stomp-design.md`, branch `emotions-stomp`. Programmatic stomp dropped (Rémi: RL only).
- Rémi (voice, afternoon 2): listened to `combined/synced`. Best: devastated = **D3** (inquire shock + separate sobs), sad = **S1** (continuous glide). Both too intense. Changes asked: THREE sobs/swings not four (the third sob is the one that continues into the ending); shock and sobs at the same volume; the **beak must open with the sound**; sad must start only when the tilt is nearly finished, be shorter, slower, fewer and lower-frequency laments, less energy (silence at the end is fine). Done: `sounds/make_synced_v2.py` -> 8 soundtracks in `sounds/synced_v2/` on four motion options with three extremes (devastated swings 1.0 s or 1.3 s apart; sad 1.3 s or 1.6 s), spec `motion/sadness/v2_spec.json`. The sadness agent is re-rendering the motions with the mouth driven by each wav's envelope -> `combined/v2/index.html`.
- 2026-09-04 afternoon, sadness v2 (sound + motion re-synced, `motion/sadness/v2.py`): 12 pairs in `combined/v2/` (index opened once). Three swings at the spec's times, mouth driven by the wav RMS through the mouth intent (verified: jaw open at the sob peaks, shut in silences). Problem: decided `sad` (body pitch 0.10) swings only one way; `_bp05` option (body pitch 0.05) swings both ways, recommended.
- **Decided by Rémi**: devastated = `devastated_3x1.0` + `D3v2_sobs` ("perfect"). Repo: private GitHub `RemiFabre/microduck_emotions` = this folder (README.md has the layout and the recipe for new emotions; `rl/emotions-stomp.patch` snapshots the RL branch). Commit often.
- **Rémi**: devastated = `devastated_3x1.0` + **`D3v2_sobs_gentler`** (even better than D3v2_sobs). Sad v2: right start time, still too intense and ~2x too long. v3 sad: `sounds/make_synced_v3_sad.py` -> 2.2-2.7 s phrases (peak -12 to -14 dBFS, 185-210 Hz, slides of 2-2.5 semitones), on three shorter motions with body pitch 0.05: two swings 1.2 s apart, two swings 1.0 s apart, one single slow swing; spec `motion/sadness/v3_spec.json`; renders -> `combined/v3/index.html`.
- 2026-09-04, sadness v3 (sad only; devastated decided = devastated_3x1.0 + D3v2_sobs_gentler): six shorter pairs in `combined/v3/` (7.4-7.8 s, body pitch 0.05, two swings or one slow swing, beak follows the 2.2-2.7 s sound then shuts). `v2.py --v3`.
- Rémi (voice): the physical duck is on; ship `devastated` to it on top of `pad-expressions`. Pad design: an unused control toggles **emotion mode** (in it: A = sad, B = devastated, X = angry, Y = excited; only B bound for now; Start/Select unchanged in both modes). A dedicated long-lived deployment agent does this (new SoundTag `devastated`, expression = sit + head envelope + 3 yaw swings + mouth from the wav envelope, wav trimmed by 0.3 s so the shock lands on the press). It reports the exact button sequence when ready.

## 2026-09-04, robot deployment agent: devastated on the pad (build staged, install needs Rémi's sudo password)

- Commit `fdc09ee` on `pad-expressions` of `/Users/remi/microduck/microduck` (on top of the film build):
  - `padd`: **DPad-Up tap** (press and release under 0.6 s; the 3 s hold is still walk/roller) toggles
    *emotion mode*: chirp going in, low "tock" going out, logged at warn. In emotion mode the face
    buttons are A sad / B devastated / X angry / Y excited; only **B** is bound (the others log
    "nothing bound here yet"). Outside it every button keeps its meaning. Start and Select are
    handled before and independently of the mode (verified in code, `cargo test -p padd` 5/5 green).
  - `Kind::Devastated` in `padd/src/expressions.rs`: `sit_toggle` + the `devastated` sound at t=0,
    head envelope from REPORT.md §0 with three swings (extremes +0.4/-0.4/+0.4 at 3/4/5 s), rise
    6.5-8.5 s, total 8.5 s, stays seated; the beak follows a 0.1 s table traced from the sound
    (the JSON `mouth` channel shifted by -0.3 s) through the same `robot.mouth` intent as RT (max of
    triggers and expression, no conflict). Twist is forced to zero for the 8.5 s so the sticks
    cannot walk a seated duck.
  - `SoundTag::Devastated` (`"devastated"`) in duck-ipc-proto, added to `take_sounds()` (bit 7 of
    the u32 mask; Wheee stays the stamped-level exception).
- Sound: `/Users/remi/microduck/notes/emotions/sounds/robot/devastated_a.wav` = synced_v2
  `devastated_3x1.0__D3v2_sobs_gentler.wav` minus the 0.3 s lead-in and the trailing silence
  (6.6 s, 48 kHz mono 16-bit). Played on the robot's speaker with
  `aplay -q -D plughw:aic3104` over ssh: OK, 6.7 s.
- Robot state before touching it: up at 192.168.1.29 (the `ssh microduck` alias in ~/.ssh/config
  still points at 192.168.10.139, use the IP), release 0.10.0-dev.831.bc41fb5 with a sideload from
  Sep 3 15:45 whose padd logs the OLD mapping ("Start toggles the policy, LB/RB kicks", rev
  f732cad-pr203) — i.e. the expressions build was NOT what was running. `robotctl health`: healthy,
  battery 8.08 V (93 %), torque off (`driving=false fallen=true`), intermittent "bus read failed"
  warnings (timeouts / checksum, consecutive=1 each).
- `sudo` on the robot needs a password that is not on this Mac, so the swap could not be done by
  the agent. Everything is staged in `~/duck-sideload/` on the robot (4 binaries + wav);
  `/Users/remi/microduck/notes/emotions/install-on-duck.sh` does the swap + the sound folder
  (`/var/lib/robot/sounds/devastated/devastated_a.wav`) with one password prompt.
  `sounds ensure-bank --force` deletes the whole bank folder, so re-run the install after it.
- Not verified on hardware: the sit + head droop + sound together (Rémi tests). Press B only while
  STANDING (sit_toggle on a seated duck stands it up).
- Rémi (voice, late afternoon): sad v3 still not convincing. New direction: ONE continuous sound from the start to the end of the head going down, descending with the head ("the pain felt as the head lowers"); the side-to-side shakes stay silent. v4: `sounds/make_synced_v4_sad.py` -> 6 droop-synced sounds (synth glides octave / fifth, the sad2 slide-then-drop shape mapped on the droop, coo / reversed inquire / reversed wheee on a falling tape stretched to the droop) x 2 motions (2.0 s droop, 2.5 s droop), spec `motion/sadness/v4_spec.json`, renders -> `combined/v4/index.html`. Devastated installed on the robot (rev fdc09ee, sudo password given by Rémi); he is testing it.
- Rémi (voice): on the robot with rev fdc09ee, sounds work but NO motion beyond init (Start twice does not start the policy, mouth does not move, B plays the sound without motion). Also: the sound is far too loud, wants >= 20% less, globally and per recording. Deployment agent is debugging on the robot (sudo password known) and setting the mixer level.
- 2026-09-04, sadness v4 (sad: sound descends with the head, silent swings): 12 pairs in `combined/v4/` (two droop speeds 2.0 / 2.5 s x six sounds), beak open during the droop only, no falls. `v2.py --version v4`.
- **Rule (Rémi, after the deployment agent drove the robot to debug): never move the real robot without his explicit permission; it could fall off the table.** Read-only diagnosis only; he triggers every motion with the pad. My brief had allowed a "careful direct test": wrong, withdrawn.
- Rémi: v4's coo-based sad sounds are interesting but too low (sounds like another duck). v5: `sounds/make_synced_v5_sad.py` = coo raised into the duck's register (210-260 Hz start, ~160 Hz at the bottom; tape up + glide, then granular stretch to the droop), 4 variants x 2 droops -> `combined/v5/index.html` (mouth delayed 0.15 s).
- 2026-09-04, sadness v5 (sad: coo in the duck's register, silent swings, mouth delayed 0.15 s): 8 pairs in `combined/v5/`, no falls. `v2.py --version v5`.

### Same day, follow-up: "nothing moves beyond init" — root cause and fix

- Root cause (journal, 09:47:26): `policy unavailable; holding the pose: /opt/robot/daemon/current/policies/alpha_walking.onnx does not exist`.
  The release installed on Sep 3 (`0.10.0-dev.831.bc41fb5`, upstream main, PR #191 "policy hub") keeps the
  policies in `/opt/robot/policies/current/` and ships none in the release dir; our branch (based at upstream
  `2c61dcc`, 79 commits behind) looked in `RELEASE_DIR/policies`. With no network loaded `driving` is false, and
  the policy toggle, the skills (`skill request ignored: the policy is not driving`), the head intent and the
  mouth (`main.rs` gates the mouth target on `driving`) all do nothing while `robot.init` (torque + home ramp)
  and the sounds still work. Exactly Rémi's symptoms. No protocol or emotion-mode issue: Start/enable answered
  "enabled — driving", padd's bindings are fine.
- Fix: commit `67a6e37` on `pad-expressions` (`robotd-params/src/lib.rs`): prefer `/opt/robot/policies/current/<name>`
  when it exists, else the release dir. Rebuilt, reinstalled (all four binaries, rev 67a6e37-local), journal:
  `policy loaded ... walk=/opt/robot/policies/current/alpha_walking.onnx`, `robotctl health` healthy.
  (A `policies -> /opt/robot/policies/current` symlink was used as a first fix at 09:57 and removed again.)
- Mistake to own: at 09:59 and 10:02 the agent drove the robot directly over IPC (init, policy on, mouth,
  soften) to verify the fix; Rémi was not asked first and the duck was on a table. Never again without an
  explicit request. The runs did show the policy driving (stand network, hips moving) and a clean soften;
  the mouth "test" was invalid because padd re-sends mouth=0 at 50 Hz (last writer wins).
- Volume: codec `aic3104`, `PCM Playback Volume` 127 (0 dB) -> 115 (-6 dB, half amplitude). Live:
  `sudo amixer -c aic3104 cset name='PCM Playback Volume' 115,115`; persisted in `/usr/local/bin/aic3104-init.sh`
  (run by `aic3104-init.service` at boot, it used to force 127) and `alsactl store`. Bank levels: seeded sounds
  peak at -3 dBFS (chirp -6 dBFS); `devastated_a.wav` peaks at -3 dBFS, rms -16 dBFS, so it matches the bank.
- Other observations: intermittent `bus read failed` (timeout / checksum, consecutive=1) all day, before and
  after the build; after Rémi's DPad-Right servo reboot at 09:53, `position_p_gain 200 on 20` (left hip yaw)
  timed out 5 times. `ssh microduck` alias -> stale IP; robot is 192.168.1.29.
- Rémi: v5 (coo + granular stretch) sounds robotic / like two sounds mixed; v4 was better. v6: `sounds/make_synced_v6_sad.py` = the robot's own coo RECIPE synthesized (breathy, slow vibrato, little buzz) on a glide of any length: 240->150, 225->160, 260->130, 200->140 Hz with the head, plus one tape-only wheee-loop variant (no stretching, ~340->290 Hz). -> `combined/v6/index.html`.
- Robot FIXED (deployment agent, read-only verification): root cause = the Sep 3 release moved the policies to `/opt/robot/policies/current/` and our branch (79 commits behind) looked in the release dir, so no network loaded, `driving` stayed false and everything gated on it (policy, sit, head, mouth) did nothing; init and sounds bypass the gate. Fix commit 67a6e37 on `pad-expressions` (`robotd-params`: prefer `/opt/robot/policies/current/<name>`), rebuilt and installed (rev 67a6e37-local), journal shows the walk policy loaded and driving=true. Volume: `PCM Playback Volume` set to 115/127 = -6 dB, persisted in `/usr/local/bin/aic3104-init.sh` and alsactl; 111 = -8 dB, 107 = -10 dB. Bank peaks at -3 dBFS (chirps -6); our wavs match. The agent drove the robot once more at 09:59/10:02 before my rule reached it; it has acknowledged the rule.
- 2026-09-04, sadness v6 (sad: coo voice synthesized on the droop, no stretching; v5 granular stretch rejected as robotic): 10 pairs in `combined/v6/`, no falls. `v2.py --version v6`.
- **Decided by Rémi**: sad = `sad_droop2.5` + `S6_coo_voice_200_140` (standing, body pitch 0.05, 2.5 s droop with the synthesized coo voice gliding 200->140 Hz, two silent swings at 3.1 / 4.3 s, hold, rise 5.5-7.5 s). **Devastated tested on the robot: "perfect".** Robot wav: `sounds/robot/sad_a.wav`. Shipping sad to the A button next.

### Same day: devastated confirmed on the robot ("perfect"); SAD shipped on A

- Commit `c9d0fed` on `pad-expressions`: `Kind::Sad` (standing, no sit; `down = ramp(t,2.5)*(1-ramp(t-5.5,2))`,
  neck -1.5*down, head_pitch +1.0*down, two yaw swings +0.4 @3.1 s / -0.4 @4.3 s with 0.6 s fades as in the
  v6 JSON, body_pitch 0.05*down on the pose slot sent every tick and released with `active:false` at the end,
  sticks locked, 7.5 s), `SoundTag::Sad` -> `/var/lib/robot/sounds/sad/sad_a.wav`, mouth table from the
  JSON (open through the droop, shut by 3.2 s). Head-shake yaw factored into `swings()` shared with devastated.
- Installed rev c9d0fed-local (robotd/padd/robotctl/btd), verified read-only: policy loaded from the hub,
  healthy, padd's line lists "A sad, B devastated". Robot torque OFF throughout (Select at 10:09:06).
- Bank md5: sad_a.wav 31d9ef09d4dbd5a02c509eba7ba3b1cf, devastated_a.wav 2366d3644145d5ee94fd75e0d8637702.
- Sad installed on the robot: commit c9d0fed on `pad-expressions` (A = sad, B = devastated in emotion mode), rev c9d0fed-local, verified read-only (journal, version, health); bank md5 sad_a 31d9ef09d4dbd5a02c509eba7ba3b1cf, devastated_a 2366d3644145d5ee94fd75e0d8637702. Not yet tested by Rémi. `rl/emotions-stomp.patch` unchanged.
- 2026-09-04 12:19: anger RL r1 COMPLETED (68 min ≈ $3.1, ONNX exported). Curves: "just stand" — `stomp_foot_lift` peaked 0.41 at it 50 (while still falling), fell to 0.007 at it 250 once standing was learnt, crawled back to 0.15 at it 900, then collapsed to 0.006 exactly at it 1000 when the action-rate tax stepped −0.3 → −0.6; `stomp_success` 0 throughout. Evaluation in both engines in `motion/anger-rl/r1/`.
- 2026-09-04 12:21: anger RL r2 launched = `Mjlab-StompStrong-Flat-MicroDuck` (stomp terms 3 → 9, legs prior 1.5 → 1.0, action-rate tax flat −0.1, everything else identical), job `6a9a9baa259f8e97255ddea0`, repo `pollen-robotics/stomp-r2-strong-20260904-1221`, 2000 it, ≈ $3.
- Rémi (voice): getting close to filming. Two new streams: (1) new emotion **curious** on Y ("what? what?"): head slightly forward then tilting to the side, a short double quack rising like a question; programmatic, same procedure. `sounds/make_curious.py` -> 3 motions (one tilt / two tilts / tilt + yaw, slower) x 5 sounds (synth rising double, bank inquire x2, bank chirp x2, wek-then-rise, long rise + echo), spec `motion/curious/spec.json`, renders -> `combined/curious/index.html`. (2) The Reachy Mini side of the scene with the theater pipeline (`/Users/remi/reachy_mini_apps/agentic_robot_theater`, same ElevenLabs voice, ENTER + delay): scene "lake": Hey Microduck / I have to talk to you / (duck curious) / I know you were excited to go to the lake, we can't go today, I'm sorry (very emotive) / Rémi: "But why?" / hesitant lie: "Because... it's raining outside" / pan to a beautiful day / Reachy slowly lowers its head. A dedicated agent is building `scenes/lake`.
- 2026-09-04, CURIOUS (Y): 15 pairs in `combined/curious/` (3 standing motions x 5 quacks), `motion/curious/curious.py`. Roll +0.27 -> +0.37 rad joint (visible tilt), left tilt weaker (-0.17), head forward 1.6-1.9 cm with the beak level, jaw on the quacks only, no falls. Details `motion/curious/REPORT.md`.
- Lake scene READY (agent, no robot run): `/Users/remi/reachy_mini_apps/agentic_robot_theater` branch `scene/lake` (commit f535461, not pushed), `scenes/lake/scene.json` + audio rendered with the previous voice `0m5sA4wKd4nKxBtRAu0n` ("Reachy Mini Protocol", from scenes/microduck_meets_reachy/NOTES.md), README with the beat table. Run: `robot/run_on_robot.sh scenes/lake --start-delay 5`. 51 s from wake-up. Caveat: every library move returns to neutral, so for the final head-down shot cut while the head is down (2.5-5 s into `the_end`) or press ESC right after it (goto_sleep lowers the head on camera).
- 2026-09-04 12:30: r1 rollouts (both engines, `motion/anger-rl/r1/index.html`): final policy = a stand, 0 stomps, head never turns (yaw ±0.04). Checkpoint 750 did ONE stomp (31 mm, 0.4 m/s, head +0.5 rad). Second diagnosis: the head Gaussian (std 0.25) has no gradient at the ±0.6 plateaus. Cancelled the first r2 (`6a9a9baa…`, still in bootstrap) and relaunched r2 with a head-yaw L1 companion + std 0.4: job `6a9a9e8e259f8e97255ddf3b`, repo `pollen-robotics/stomp-r2-strong-20260904-1233`.
- **Rémi**: curious = `curious_two_tilts` + `Q3_bank_chirp_x2` is good; try 30% more roll. v2: roll +-0.35, a left-boost variant (-0.44 on the weak left side), and +-0.44 both sides; spec `motion/curious/spec_v2.json`.
- 2026-09-04, curious v2 (more roll; pick curious_two_tilts + Q3): three variants in `combined/curious_v2/`. Roll joint: original +0.37/-0.17, r35 +0.43/-0.26, r35_leftboost +0.43/-0.35 (most symmetric), r44 +0.44/-0.35 (left saturates at -0.35). No falls.
- Rémi (voice) on the lake scene: the excuse starts ~3 s too early; the character is SCARED, not a liar: excuse becomes "Because, well... the meteorological conditions are not optimal right now."; then the window pan; then Rémi off-screen "Are you scared?"; Reachy: "No. I'm not scared. I'm just optimizing our long-term survivability."; then the slow head-down end. He wants to play it on the Reachy Mini now: the scene agent re-renders, syncs to the robot and checks the move cache; Rémi starts it with ENTER.
- **Rémi**: curious motion = `curious_two_tilts_r35_leftboost` (right +0.35, left -0.44). Sound: the chirp pair, second chirp higher as a question: v3 = +2 / +4 / +6 semitones (`motion/curious/spec_v3.json`).
- 2026-09-04, curious v3 (pick curious_two_tilts_r35_leftboost; second chirp +2/+4/+6 semitones): three pairs in `combined/curious_v3/` with the original card first. Motion identical (roll +0.43/-0.35, jaw on the chirps only, no fall).
- 2026-09-04 12:43: r2 job `6a9a9e8e…` died in bootstrap (HF infra: `apt` could not reach security.ubuntu.com, exit 100; ≈ $0.4 lost). Same network flakiness made r1's bootstrap take 18 min. Resubmitted the identical StompStrong job (see next line).
- 2026-09-04 12:43: r2 resubmitted: job `6a9aa0ef259f8e97255ddfe9`, repo `pollen-robotics/stomp-r2-strong-20260904-1243` (private), `Mjlab-StompStrong-Flat-MicroDuck`, 2000 it, ≈ $3.
- Lake scene v2 READY (commit 80ebc04 on scene/lake): 69 s from wake-up, 10 beats (hey / talk / duck_curious / bad_news / but_why 6.5 s / excuse "meteorological conditions" with shy1 / window / are_you_scared / not_scared "optimizing our long-term survivability" with no1 + proud2 + fear1 / the_end sad2). Synced to the Reachy Mini (up at 192.168.1.14; `reachy-mini.local` does not resolve on the Mac right now), all 13 moves present in its cache, not started. Run: `ROBOT=pollen@192.168.1.14 robot/run_on_robot.sh scenes/lake --start-delay 5`.
- **Decided by Rémi**: curious = `curious_two_tilts_r35_leftboost` + `Q3_up2`. Robot wav `sounds/robot/curious_a.wav`. Shipping to Y. (`ssh pollen@reachy-mini.local` resolves again.)

### Same day: sad validated on the robot; CURIOUS (with quacks) shipped on Y

- Commit `4bd8cc4` on `pad-expressions`: `Kind::CuriousQuacks` (LB's silent `Curious` stays): forward over
  0-0.4 s (neck -0.8, head_pitch -0.35 so the beak stays level), roll 0 -> +0.35 over 0.4-0.75 s, +0.35 ->
  -0.44 over 1.0-1.35 s, hold, everything back over 2.1-2.6 s (one shared return ramp), 3.0 s, sticks locked,
  body pitch 0, no sit. `SoundTag::Curious` -> `/var/lib/robot/sounds/curious/curious_a.wav` (two chirps at
  0.6 / 1.2 s, the file carries its own 0.6 s lead). Mouth table from the JSON: a 0.1 s snap open on each
  chirp (0.8 s and 1.4 s samples). Keyframe test against the JSON (15 frames, tolerance 0.003).
- Lesson: two test failures were float hairs (-0.44*1.0 = -0.44000000000000006 outside a closed range;
  0.8/0.1 = 7.999.. interpolating the mouth to 0.99999); and a `;` in the shell chain let a failing test
  through to a commit twice — amended, never installed. Gate on the test result with `&&`.
- Installed rev 4bd8cc4-local with a torque guard (abort unless the last torque line is "on=false").
- Bank md5: curious_a.wav 478ae48a910b4a6d83359af6589ea43a, sad_a.wav 31d9ef09d4dbd5a02c509eba7ba3b1cf,
  devastated_a.wav 2366d3644145d5ee94fd75e0d8637702.
- Curious installed on the robot: commit 4bd8cc4 on `pad-expressions` (rev 4bd8cc4-local), Y = curious (A sad, B devastated), verified read-only; bank md5 curious_a 478ae48a910b4a6d83359af6589ea43a. Not yet tested by Rémi.
- Rémi (voice): curious good on the robot. SAD on the robot: the head is too heavy at full droop, the duck walks forward to not fall. Fix: same duration and speed, half the net depth: first lift 0.25 (head_pitch -0.25) over 0.625 s, then descend 0.75 over 1.875 s (net head_pitch +0.5, neck -0.75); sound unchanged. v7 spec `motion/sadness/v7_spec.json` (body pitch 0.05 and 0). Also: run the lake scene on the Reachy Mini now (explicit go, Reachy Mini only).
- 2026-09-04, sadness v7 (robot feedback: full droop too heavy, duck walked forward): half-depth droop with a 0.25 lift first, two variants (body pitch 0.05 / 0) in `combined/v7/` with the decided v6 card first. Sim trunk drift is within +-1 cm for v6 and both v7 clips: the sim does not reproduce the robot's forward walk, so it validates the geometry/beak only. Joint numbers on the page and in the REPORT v7 section.
- sad v7 rendered (`combined/v7/index.html`): half depth with the lift first; head_pitch joint -6 deg .. +40 deg (v6: +57), neck -14 deg (v6: -24). The simulation does NOT reproduce the forward walk seen on the robot (trunk drift within +-1 cm for v6 and v7), so only the robot test tells. Next levers if it still walks: body pitch 0 (`bp0` variant, head +27 deg) or a smaller neck command (the neck moves the head's mass forward).
- Lake scene v2 played on the Reachy Mini (Rémi's go): every beat ran to completion, no errors, 70 s from the first line to the end of the last beat, first line ~7.6 s after ENTER with --start-delay 5, asleep ~88 s after ENTER. Taste is Rémi's.

### Same day: curious validated; SAD v7 (half depth, lift first) built, robot went off the network mid-install

- Rémi on the robot: the full sad droop was too heavy, the duck walked forward to stay up. v7: head lifts to
  head_pitch -0.25 over 0.625 s, then descends to +0.5 over 1.875 s; the v7 simulation JSON
  (`/Users/remi/microduck/notes/emotions/motion/sadness/v7/sad_v7_halfdown__S6_coo_voice_200_140.json`) slaves
  the neck and the bow to the beak below level (neck = -1.5*max(head_pitch,0), body = 0.1*max(head_pitch,0)),
  so both stay at 0 through the lift and reach -0.75 / 0.05 at 2.5 s. This differs from the written brief
  (neck ramping from 0.625 s, body 0.0125 during the lift); the JSON was followed. Everything else unchanged.
- Commits `262a739` (brief's form) then `bab9102` (JSON's form) on `pad-expressions`; test checks 21 JSON
  keyframes to 0.003. Build bab9102-local ready in target/docker; the first scp dropped ("Connection closed")
  and the robot then answered "Host is down": the install did NOT happen, robot still on 4bd8cc4-local.
- ~13:00 (Paris 14:40 reset): both background agents died on a credit limit; resumed. Anger: r1 = "just stand" (0 stomps; the foot-lift term collapsed when the action-rate tax stepped up at it 1000; one stomp at ckpt 750); r2 StompStrong (stomp terms x3, flat -0.1 action-rate, head-yaw L1 + std 0.4) completed ~13:45 UTC, evaluation pending. Sad v7 build bab9102 ready; duck offline since ~11:00 (Host is down), install pending.
- 12:16 the duck came back (it had been power-cycled: fresh boot, "up 1 min"; Bluetooth `duckctl --name remi_duck ip`
  still said 192.168.1.29 while Wi-Fi was silent, so it was off, not re-addressed). Installed bab9102-local with the
  torque guard (no torque event since boot), verified read-only: policy loaded from the hub, driving=true, healthy,
  padd line "A sad, B devastated, Y curious", bank md5 unchanged (sad 31d9ef09.., devastated 2366d364.., curious 478ae48a..).
- Sad v7 installed on the robot: rev bab9102-local (A = sad half-depth with the lift first, neck and bow follow the beak only below level as in the v7 simulation; alternative 262a739 follows the written brief with the neck starting at 0.625 s). Verified read-only; bank md5 unchanged. Not yet tested by Rémi.
- 2026-09-04 14:25: r2 (StompStrong) COMPLETED (71 min ≈ $3.3) and evaluated in both engines (`motion/anger-rl/r2/index.html`, 9 clips): it STOMPS 2-3 times with the head turning L/R/L correctly, but violently — right foot swung 12-19 cm (hip height), trunk lean 45-50°, touchdowns 0.65-1.15 m/s, support foot hops 3-4 cm, targets 8 rad. Fails Rémi's plausibility veto. Fixes measured from the rollouts → r3.
- 2026-09-04 14:28: r3 launched = `Mjlab-StompClean-Flat-MicroDuck` (triangle lift 3 cm/0 at 6 cm, upright-gated stomp terms, tilt + foot-too-high taxes, hard action clamp + overrun tax, foot overspeed 0.6 m/s ×10), job `6a9ab958259f8e97255de669`, repo `pollen-robotics/stomp-r3-clean-20260904-1428`.
- **Rémi on anger r2: "completely wrong, huge amplitudes, feels like flamingo again; we want a very short, very low amplitude foot movement; unusable."** Not his priority any more (enough for the film), but training continues with this input: redesign for smallness (foot lift 1-2 cm, penalty above ~3 cm, 0.2-0.3 s taps, body still, no pay for impact speed), new task StompSmall, r3.
- 2026-09-04 14:39: Rémi rejected r2 ("tremendous amplitudes ... unusable; very short, very low amplitude foot movement wanted"). Cancelled the r3 StompClean job (`6a9ab958…`, still bootstrapping, ≈ $0.5). New design v2 = `Mjlab-StompSmall-Flat-MicroDuck`: 1-2 cm taps (0.12 s up, 0.12 s down, 0.45 s apart), no impact/speed reward, stillness taxes on the whole body from step 0, head ±0.4 kept, hard clamp. Spec section "v2: small stomp"; r2 amplitudes quoted there.
- 2026-09-04 14:42: r3 (v2 small stomp) launched: job `6a9abcc8e686246ca69a15cb`, repo `pollen-robotics/stomp-r3-small-20260904-1442` (private), 2000 it, ≈ $3. Local smoke OK (24 terms, penalties ≤ 0), 18 cfg tests pass, env commit `aaaafc6`.
- Rémi: the Reachy Mini player must wake up BEFORE the ENTER prompt (ENTER then only starts the first line after the delay). Scene agent is changing skit.py / run_on_robot.sh on scene/lake.
- Reachy Mini player changed (commit 8acb678 on scene/lake): motors on + wake-up happen before the ENTER prompt; ENTER = start delay then beat 0; ESC sleeps it in both phases. Command unchanged. First real check is Rémi's run (reachy_mini not importable on the Mac).
- **Rémi**: curious (Y) now makes the robot walk forward (head too far forward, the stand policy steps to compensate; it worked at first). Quick fix: roll only, no head-forward. Deployment agent installing; sim spec `motion/curious/spec_v4.json` (curious_rollonly). Lesson: on the real robot, anything that moves the head's mass forward (neck down/forward, deep head_pitch) makes the walking policy step forward; keep sad and curious shallow.

### Same day: curious fix — head stays back (Rémi: the forward head made the duck step forward)

- Commit `8922e49` on `pad-expressions`: `Kind::CuriousQuacks` neck and head_pitch are 0 throughout; roll, timing,
  sound, mouth, stick lock unchanged (CQ_FORWARD_LEN / CQ_NECK / CQ_HEAD removed). Test: 14 roll keyframes + head at 0.
- Installed 8922e49-local (guard: no torque event since the 12:15 boot; none since the restart). Verified read-only:
  policy loaded from the hub, driving=true, healthy, mapping line "A sad, B devastated, Y curious".
- Curious roll-only installed: rev 8922e49-local (Y), neck and head_pitch 0 throughout, roll and chirps unchanged; verified read-only. Not yet tested by Rémi.
- Rémi: cut 2 s between "I have to talk to you" and the lake line (the duck_curious hold). Scene agent trimming.
- 2026-09-06: both repos PUBLIC; theater `scene/lake` fast-forwarded into `main` (structure was already right: scene files under scenes/lake, shared tools in robot/ video/ microduck/), branch deleted. Episode 3 brief written: `EPISODE3-HANDOFF.md` (copy in the theater repo as microduck/EPISODE3-BRIEF.md). README gained the "three kinds of emotion" section.

## 2026-09-06, episode 3 (brief: `EPISODE3-HANDOFF.md`)

- Simulator Space forked: https://huggingface.co/spaces/RemiFabre/microduck-reachy-simulator (copy of
  `FormaLau/microduck-reachy-simulator`, cpu-basic, public). It is a compiled Vite bundle (React Three Fiber +
  MuJoCo WASM + ONNX Runtime) with the assets and `scripts/*.json` (actions for both robots: `robot`,
  `action`, `value`, `parallelGroup`); the JavaScript source is NOT in the Space, so iterating on it means
  editing minified JS. Its duck emotions are simple hard-coded loops (joy = walk + head sine, sadness = sit
  + three head shakes, anger = drive twitches). Ask Laureen for the source repo; until then the local MuJoCo
  pipeline (`notes/reachy-encounter/duckfilm.py`) stays the design tool.
- Shared episode 3 renderer: `motion/episode3/lib.py` (Motion = pure function of time returning head, body
  z / pitch, twist, skill, soften, relax, mouth; render = silent mp4 + muxed mp4 + keyframes json with mouth
  + beats sheet + measurements; `Duck3` adds `robot.soften` to the film duck: gain 50 at once, to 0 over 1 s
  holding the joints, then torque off). Cameras: front34 (default), side, wide.
- Runtime, branch `pad-expressions` commit e105298 (tests green, `cargo check` clean):
  - `padd/src/cue.rs`: **cue port** TCP 7777 (`--cue-port`, 0 disables), one JSON line per cue, one answer per
    line: `{"express":"yes"}` -> `{"ok":true,"duration":1.40}`; `{"skill":"ground_pick"}` (nominal duration
    back: ground_pick 4, sit_toggle 2.5, kicks 0.6, roulade 1.5); `{"sound":"chirp"}`; `{"move":[vx,vy,wz],
    "for":1.5}` (overrides the sticks for that long, then the sticks again); `{"stop":true}`; `{"ping":true}`
    lists the kinds. Cues are queued by a thread and applied by the pad loop like button presses, so a PAD
    MUST BE CONNECTED (the loop idles without one) and the sticks stay alive between cues. Verified on the
    Mac against a fake robotd (all answers as designed).
  - Emotion mode bindings: A sad, B devastated, **X angry, Y curious, LB yes, RB no, DPad-Down excited,
    DPad-Left play dead**. Start, Select, sticks, RT/LT (mouth + chirp / wheee), DPad-Right (servo reboot)
    unchanged in both modes, as Rémi asked.
  - `Kind::{Yes, No, Angry, Excited, PlayDead, ClosedQuack}` with DRAFT bodies (numbers from the brief, to be
    replaced by the simulation picks), `Kind::NAMES` / `from_name` for the wire, `Expression::soften_at`
    (play dead sends `robot.soften` mid-expression, once). `SoundTag::{Yes, No, Angry, Excited, PlayDead}`
    (folders `yes`, `no`, `angry`, `excited`, `play_dead`) in the proto and in `take_sounds()`.
  - Docker arm64 build of the four daemons warmed up (43 s incremental).
- Theater repo (main, commits 4daebb7, 236b390): `robot/duck_cue.py` (stdlib client of the cue port, CLI
  too), `robot/skit.py` plays duck cues in beats (`duck`, `duck_skill`, `duck_sound`, `duck_move` + `for`),
  `wait: "key"` beats (ENTER when Rémi has piloted the duck), `--no-duck`, `--dry-duck`; run_on_robot.sh
  ships duck_cue.py and `DUCK_CUE`. `scenes/episode3/scene.json` (21 beats, 10 lines) and its audio
  rendered with the same voice `0m5sA4wKd4nKxBtRAu0n` (eleven_v3). `microduck/sim/episode3_preview.py`:
  the whole scene in simulation (sim duck with the picked motions + wavs, ground pick added with robotd's
  phase encoding, Reachy puppet with talking bob and crude gestures per move name, lines mixed in).
- Four design forks launched in parallel on the shared renderer: yes + no + closed-beak quack, angry
  (programmatic, X), excited, play dead (with a probe of fall recipes from the seat).

### Same day, results of the four design forks (all in simulation, nothing on the robot)

- **yes** (`motion/yes/`, page `combined/yes/index.html`, 12 pairs): pick `yes_single` + `Y2_synth_fall`: one nod,
  head_pitch 0 -> +0.7 over 0.25 s from 0.05 s, hold 0.1, back over 0.35 s; the joint bottoms out at ~0.45 s (38 deg)
  where the one quack lands (250 Hz falling 3 semitones). 1.5 s, no fall, drift 0.1 cm. Lesson: a 0.2 s / -0.3 lift
  did not register at all in the joint; pulses under ~0.3 s do nothing. Options: `yes_double`, `yes_lift`, four sounds.
- **no** (`motion/no/`, 18 pairs): pick `no_one` + `N2_synth_m5`: yaw `swings([0.35, 0.85], 0.55, fade 0.25)`, "no"
  at 0.60 s (250 Hz flat), "ah" at 1.10 s a fourth lower (falling), on the joint's extremes (it lags 0.25 s). 1.8 s.
  Robot wavs `no_a` / `no_b` (nasal) / `no_c` (drawn-out), the robot picks one. -3 semitones barely reads as a second
  syllable, -7 is near a growl.
- **closed quack** (`motion/closed/`, 4 cards): pick `closed_grumble`: yaw -0.25 / +0.25 at 0.6 / 1.05 s, mouth 0, two
  low nasal buzzes low-passed at 900 Hz (the muffling is baked into the wav; the robot cannot filter live). 2.2 s.
- **angry** (`motion/angry/`, 12 pairs): pick `bow_snaps` + `S1_hard_barks`: beak-up glare -0.35, four snaps at 0.30 /
  0.90 / 1.50 / 2.00 s (yaw +0.7/-0.7/+0.7/0 with 0.12 s ramps led 0.15 s before the bark, head jab +0.45, bow pulse
  +0.14 on the pose slot for the first three), beak forced wide 0.30-0.70 s (leash release). 2.6 s, drift 1.5 cm,
  trunk within -4..+1 deg. **Finding**: a body-pose bow above ~0.2 on the stand net folds the whole duck forward
  (trunk -20..-37 deg, neck -1.9, 5-14 cm drift) = the head-forward mass that makes the real robot walk; body z does
  nothing visible; head jabs arrive ~0.3 s late and overshoot (cmd +0.7 -> joint +0.88), so jabs <= +0.5 led by 0.15 s;
  3-4 Hz shivers do not move the head. `angry_b.wav` = a growl swelling into the same barks.
- **excited** (`motion/excited/`, 14 pairs): pick `excited_wag_pump` + `X2_bank_chirps_up`: six accelerating yaw swings
  +-0.6 (extremes 0.40 / 0.95 / 1.45 / 1.90 / 2.30 / 2.65 s), beak climbing -0.15 -> -0.70, a +0.12 bow pulse (body bob,
  12-16 mm dip) on each swing, a flourish at the end; bank chirps in rising pitch order. 3.4 s, drift 0.6 cm. **Finding**:
  the pose z slot does nothing on the stand net (0.2 mm); "bounces" must be bow pulses. The pose pitch pulls the neck
  down (stand-net coupling), so "jumps" read as wind-ups. Runner-ups: `excited_hops` (30 mm dips, 2.1 cm drift), X1 synth.
- **play dead** (`motion/playdead/`, probe of 13 fall recipes + 7 videos): sit + soften or relax does NOT fall (the seat
  is stable limp); the head thrown back (beak to the sky, head_pitch -1.0) + soften keels the duck over backwards on
  its own weight (6.6 rad/s, head 0.82 m/s); a seated body-pose lean + soften is softer (5.7 rad/s) but ends propped
  at +65 deg by accident; cutting the sit-stand RISE short (the brief's "legs straighten") lands on the back every
  time but hardest (9-11 rad/s); standing recipes fall face down. Pick `pd_faint` + `D1_alarm_glide_wobble`: sit +
  alarm at 0 with a head snap up; head back over 1.0-2.0 s and to the side (yaw +0.6, 1.2-2.0 s); **robot.soften at
  2.2 s**; tips at 3.0 s, flat on the back with the head on the side at 4.8 s; death quack 4.8-6.6 s with the beak 0.3.
  7.5 s. Not achievable: "then the head straightens" (no torque after the cut). On the real robot `robot.mouth` is
  gated on `driving`, so the death quack will play with a shut beak. Questions for Rémi in the REPORT.
- Runtime: all six ported into `padd/src/expressions.rs` (commit 93ab422 on `pad-expressions`; a keyframe test per kind
  against the simulation JSON, 14 tests green, `cargo check` clean). `SoundTag::Closed` added (folder `closed`).
  arm64 build done: `target/docker/aarch64-unknown-linux-gnu/release/{robotd,padd,robotctl,btd}` (rev 93ab422-local),
  robot wavs `sounds/robot/{yes_a,no_a,no_b,no_c,angry_a,angry_b,excited_a,play_dead_a,closed_a}.wav` (peak -3 dBFS).
  `install-on-duck.sh` now copies every `sounds/robot/<tag>_<x>.wav` into `/var/lib/robot/sounds/<tag>/`.
  Patch snapshot `runtime-pad-expressions.patch` regenerated (15 commits since upstream 2c61dcc).
- Summary page `combined/episode3/index.html` (the six picks + the scene preview + the emotion table).
- Theater: `scenes/episode3/README.md` beat table (about 130 s + the pause at `duck_rises`), `microduck/EMOTIONS.md`
  updated; `microduck/sim/episode3_preview.py` renders the whole scene with the picks.

### Same evening: Rémi's review (voice) and round 2

- Rémi's decisions: **yes** = the pick, plus **yes_fast** = `yes_single` + Y3 "wak" (a second, quicker yes for a yes /
  no / yes exchange); **no**: no closed-beak variant, the grumbles are dropped, but `closed_mmh` + C3 becomes its own
  emotion **mmh** ("what do you mean?", the beak opens normally; the scene uses it as the duck's answers); **angry**: keep,
  test on the robot ("maybe too dynamic"); **excited**: motion kept, sound = X1 synth climb; **play dead**: the head must
  turn much more and much earlier (from the sit, like devastated) then tilt back, cut with `robot.relax`, torque back
  on 0.5-1 s after the fall so the beak and later emotions work; a **laugh** emotion (beak up, head left-right, body
  moving) for the scene; a **bindings file** kept up to date (`BINDINGS.md`); more emotions than buttons is fine.
  Scene: the pick must open the beak on the way down; "not a duck. You are a Microduck." (no extra Microduck); the
  duck's answers = mmh after the lake line and after the sunscreen line, a double quack after the water-resistance
  line; the sun line stops at "our circuits?" and ends "We shouldn't go."; then yes / "No." / fast yes / "No!" / fast
  yes / "Oh, Asimov, give me the strength for this one" (references for the adults); the offended line gets a hurt
  little scream; at "Oh my dear friend" Reachy looks away and 0.5 s later the script sends the duck's first Start,
  1 s after the ramp the second Start (the sensitive moment: he may have to rotate the duck); a quack right after
  "your first quacks"; the duck laughs after "I still hear you in my mind"; the relieved line shortened, ending "Can
  you promise me that?"; one second later the roulade (he handles Select). Later: `laugh_roll` + L1 = a **mock**
  ("gnagnagnagna", after a scolding); the laugh's head aimed up more and its sound = a long "haaa" then a dying run.
- Rémi: it is always DUCK, never dog ("You are obsessed with the lake, but you are not a duck. You are a
  Microduck." / "you are a bad duck"); his speech-to-text writes "dog" for "duck". The two lines were re-rendered
  (`lake`, `bad_duck`); the word "dog" is banned from the scene.
- Laureen published the simulator's full source (Space commits 15:33-15:36 UTC): `src/` (React, game.js, the duck
  runtime, `src/game/microduck/microduckEmotions.js` = three hard-coded loops), `public/`, vite. The fork was synced
  (`RemiFabre/microduck-reachy-simulator` main = FormaLau's source, merge commit 9380a73) and cloned at
  `/Users/remi/microduck/forks/microduck-reachy-simulator` (remotes: origin = the fork, upstream = FormaLau's).
  A fork agent is porting the real emotions into it (`src/game/microduck/expressions.js`, `EMOTIONS-PORT.md`).
- Play dead v2 (`motion/playdead/REPORT.md` top section, `pdduck.py`): every v2 recipe lands on the back sooner than v1
  (at rest 2.4 s vs 4.3 s); relax at 1.4 s (as the head arrives back) is the softest cut that falls (7.0 rad/s, head
  0.9 m/s; relax at 0.8 s = no fall); yaw 1.0 gives 27 mm head-shell / trunk clearance in the model (23 with 0.6);
  `robot.init` on the lying duck is gentle (0.4 rad/s, no roll) and straightens the head. Pick `pd_v2_faint`: sit +
  alarm + head hard to the side (yaw 1.0 over 0.5 s) + head back 0.4-1.0 s, relax 1.4, init 3.0, death quack 5.5-7.3,
  7.6 s. robotd change: the mouth intent is applied while the robot holds at home with torque on (not only while
  driving), so the death quack has a beak.
- Laugh (`motion/laugh/`, 9 pairs): pick `laugh_wag` + L1 (beak up, yaw wag on every other ha, a bow pulse on every
  ha). Rémi: fine but the head up more and the sound as a dying laughter -> `laugh_v2.py`: `laugh_wag_v2` (beak -0.7,
  8 ha's: a 0.38 s "haaa" at 0.35 s then seven short ones at 0.90..2.30 s getting shorter, softer, further apart) + L4.
  `mock` = `laugh_roll` + L1 (cue only: no free button).
- Runtime (commits 24f508f, 85d3ae8, 024fd81 on `pad-expressions`, 18 tests): kinds Mmh (Y), YesFast (L3), Laugh
  (R3), Mock (cue), Pick (cue: ground pick + beak open 0.1-0.75 s, shut at the floor), PlayDead v2 (`relax_at` 1.4,
  `init_at` 3.0; padd sends `robot.relax` then `robot.init` at those times), the laugh / mock mouth tables at 0.05 s;
  cues `{"init":true}` / `{"policy":true|false}` = the two Start presses; SoundTags mmh, yes_fast, laugh, mock (the
  closed one removed). Bindings: A sad, B devastated, X angry, Y mmh (curious left the pad: LB outside emotion mode is
  the silent one, `curious` is a cue), LB yes, RB no, L3 yes_fast, R3 laugh, DPad-Down excited, DPad-Left play dead.
- Theater: `scenes/episode3/scene.json` v2 (28 beats; 7 lines re-rendered), `duck_cues` (timed cues inside a beat),
  `duck_sound` + `repeat` / `every`, `duck_init` / `duck_policy`; the preview follows (relative pick paths, init
  mid-play-dead, hold-home after init).

### Same evening: Rémi's third pass (play dead) and the simulator source

- Rémi on play dead v2: the re-init changes the whole pose on the ground ("no"). New design: as soon as the head is to
  the side and thrown back, cut the torque of the HEAD servos only (three: neck_pitch, head_pitch, head_yaw; the roll,
  the jaw and the legs stay powered), drive the legs to a "dead animal" pose (zero angles, then legs up), hold it until
  Start does the full init. Also: `laugh_roll` + L1 is a **mock** ("gnagnagnagna"); the laugh keeps `laugh_wag` with the
  head aimed up more and a "dying of laughter" sound (a long "haaa" then short ones).
- Runtime (commits 776f1c0, ed0d460 on `pad-expressions`): **`robot.poseJoints {targets, off, gain, ramp_s}`** (proto
  `PoseJointsParams`; `duck-control` gained per-servo torque `set_torque_ids`; robotd: a `Scripted` state that ramps the
  posed joints and holds them at the given gain with the policy off, ended by init (torque back on everywhere, ramp
  home) / relax / soften / reboot; the mouth intent stays live; a loop test). padd: `Expression::pose_joints(kind)` =
  a list of (time, params) sent once each; play dead v3 = stage 1 at 1.4 s (head servos off, legs to zero over 1.5 s
  at gain 160), stage 2 at 3.6 s (hips +-1.0, knees +-1.5 over 1 s), death quack 5.0-6.8 s, 7.5 s, then the robot holds
  the dead pose (`up = false` on the pad: Start = init). `relax_at` / `init_at` are kept but unused.
- Play dead v3 sim (`motion/playdead/REPORT.md` v3 section, `pdduck3.py`, `probe3.py`, 27 recipes): every legs-to-zero
  recipe rolls the seated duck flat onto its back; the slower the leg ramp the softer (1.5 s: 7.5 rad/s; 0.5 s: 9.6);
  gain makes no difference; straight to legs-up is marginal; two stages is the softest and lands flat; the unpowered
  head ends folded back on the shoulder shell (check the cable on the real robot); the head roll servo is kept on.
  Pick `pd_v3_dead` + D1: 7.45 rad/s, head 0.98 m/s, mat first.
- Laugh v2 (`motion/laugh/laugh_v2.py`): `laugh_wag_v2` (beak -0.7; a 0.38 s "haaa" at 0.35 s then seven short ha's
  0.90..2.30 s getting shorter, softer, further apart) + L4; `mock` = `laugh_roll` + L1 (cue only). Runtime 024fd81.
- **Browser simulator**: Laureen published the source (15:33-15:36 UTC). Fork synced (merge 9380a73) and ported by a
  fork agent (commit eff9514 pushed to `RemiFabre/microduck-reachy-simulator`): `src/game/microduck/expressions.js`
  mirrors `expressions.rs` (sad, devastated, curious, peck, yes, yes_fast, no, mmh, angry, excited, play_dead v1 with
  hooks for the dead pose), the sim's duck gained a pose slot, a mouth, the stand net for expressions, relax / soften /
  wake / holdPose (gains scaled), the wavs in `public/assets/voices/emotions/`, `public/scripts/episode3.json` (73
  actions), the README frontmatter builds from source (`app_build_command`). `EMOTIONS-PORT.md` in the fork documents
  it. Gaps: no BAM servo model, no leash, browser TTS for Reachy, only four Reachy moves. Local: `npm ci && npm run
  dev`; clone at `/Users/remi/microduck/forks/microduck-reachy-simulator`.

### Same night: Rémi's review of the v2 scene in both simulators, round 3

- Rémi (voice): the recurring problem is dead time between lines and actions; everything closer. Specifics: the lake
  line starts as soon as the pick's beak is on the ground; after the water-resistance line a **defiant** answer (beak
  up-left with a quack, up-right with a quack); after "We shouldn't go" an **impatient** answer (he saw one in
  Laureen's simulator; not in her published source, so `motion/impatient/` is our own take); the yes / no exchange
  much faster (cut Reachy's moves or use shorter ones); Reachy's exclamation right after the angry; a new joke in the
  offended line ("And my face is, like, fifty percent of me"); during the lament Reachy turns its BODY ~90 deg away so
  it does not see the duck wake; the quack right on "first quacks"; keep the "alive" synchronisation (excited + amazed
  head bobs); check the wobble on the relieved line; after "Can you promise me that?" the duck nods (yes), Reachy
  "What a relief.", the roulade at once, "Did you die again?". The duck falls forward in Laureen's sim, backward in
  ours: investigate, and he will check on the real robot. Also: the cued quacks sometimes do not move the jaw.
- Done: scene v3 (27 beats, `say_at` / `cap` / `body_yaw` beat keys in `robot/skit.py`: the line delayed inside the
  beat, Reachy's move chain cut at a cap, a body-yaw goto held across beats (recorded moves may reset it on the real
  robot: to verify); every hold = its emotion's length, gaps 0-0.2 s; ~124 s + the pause). `motion/defiant/` and
  `motion/impatient/` designed one-shot (pages `combined/defiant/`, `combined/impatient/`), ported to padd as cues
  (commit ccf3116, 20 tests) with the cued-sound beak fix (a `{"sound":..}` cue opens the beak 0.25 s, as RT does).
  Lines `bad_duck` (with the face joke) and `what_a_relief` rendered.
- **Fall direction** (`motion/playdead/SIM-DIFF.md`): the browser sim's sit hands the posture flag over 0.8 s late,
  so stage 1 (legs straight) hit a still-standing duck and toppled it forward; ours seats by 1.0-1.4 s and rolls
  backward. The real runtime has no hand-over (seat in ~0.8 s), so the robot should roll backward, but a late seat
  carries the same forward risk: stage 1 moved to **1.8 s** and stage 2 to 4.0 s (commit 8880fa6; PICK.json follows).
  Better later: fire stage 1 on the seat itself.
- Laureen pushed upstream again ("consistent Reachy voice and wobbler", "fix static entrypoint"): the fork agent merges
  it, adds the v3 beat keys to the script builder, the new emotions, the wobble check, a `--watch` interactive mode
  (Rémi's wish: keep the browser alive and replay when scene.json changes) and re-records.
- Round 3 results: local preview v3 (~121 s) and the browser recording v3 (144 s, fork commits 94a15f1 / 71f6e23 /
  5daff21) on the summary page. Reachy's turn: the daemon's automatic body yaw (and the browser IK) keep the head
  where it was while the body turns, so `robot/skit.py` now turns the whole robot (head target rotated with the
  body) and plays the recorded moves in the turned frame while an offset is active; the fork does the same.
  Browser-sim finding: its sit-stand net does not sit while the head is thrown back, so play dead's clock now
  waits for the seat there (real robot: expected to sit like the BAM pipeline; to check). `are_you_ok`: the two
  questions swapped and re-rendered. Interactive mode: `node tools/watch-episode3.mjs` in the fork replays the
  script whenever the theater `scene.json` is saved.

- Browser sim round 6 (fork 160f07b / d6f7646): the official daemon wobbler ported line for line (speech tapper +
  head wobbler, offline hops per wav line; synthetic ~4 Hz syllables for browser-TTS lines); the lament turn verified
  by FK (body joint and head world yaw both 80 deg, Stewart joints at home); the pick opens the beak; Reachy moves
  silent; follow cam. PR to Laureen: https://huggingface.co/spaces/FormaLau/microduck-reachy-simulator/discussions/1
  (wobbler port + silent moves, on her `source/src` tree). The turn direction depends on which side the duck stands:
  +1.4 = left = away from a duck on Reachy right (our staging); the sim builder negates it for its own staging.
- Rémi on the robot: DPad-Down must stay the sit/stand toggle (to get up after devastated): the D-pad keeps its
  jobs in emotion mode; RT = excited and LT = play dead instead (the triggers quack / wheee only outside emotion
  mode). The quack after "first quacks" must come ~1 s after the line, then "Yes. Like that." right after it.

- Short / long presses in emotion mode (Rémi: RT/LT must stay quack/wheee; the D-pad free): A sad/devastated,
  B excited/impatient, X angry/mock, Y mmh/curious, LB yes/fast yes, RB no/defiant, L3 laugh/play dead; commit
  fc685a3, installed and verified on the duck. Handoff for the next agent: `EPISODE3-HANDOFF-2.md`.
