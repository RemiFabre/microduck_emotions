# Angry stomp (three stomps, same foot) — design

Date: 2026-09-04. Status: designed, env built, cfg tests + local Warp smoke + HF smoke job
(see `/Users/remi/microduck/notes/emotions/motion/anger-rl/REPORT.md`). Real training NOT
launched — Rémi wants to be asked the first time.

## Goal (plain English)

An "anger" display for Microduck: from a normal stand, the duck lifts one foot a little and
bangs it down THREE times in short succession (0.5 s apart), turning its head left / right /
left with the stomps, then ends standing still. (Rémi, 2026-09-04, after the double-stomp
draft: "I want to see a little stomp. It's very expressive with the head movement and such. I
think it could even be three stomps in short succession ... on the same foot." Also: the
programmatic stomp is dropped, only this RL version, because even a short foot lift is a
balance problem.) The stomp count is a top-of-file constant `N_STOMPS` (3; 2 gives the
double stomp) and the whole timeline is generated from it. A one-shot trick like the kicks or the happy hop: the runtime
hot-swaps this ONNX in from the stand policy, the 13-D command block is all zeros, the
policy plays the whole gesture in 3.0 s, then the runtime swaps the stand policy back.

Rémi's hard veto: physically plausible for XL330 servos, no thrashing.

**Template = the ball kick, not the flamingo (Rémi's call, 2026-09-04):** "Using flamingo for
the stomp is a bad idea. I need a training from scratch for a much shorter movement (we're
closer to the kick policy here!). Flamingo is way too long, way too complex and often falls."
So the env copies `microduck_ball_kick_env_cfg.py` (a short one-shot foot swing from a stand,
all-zero command): same standing spawn, same support-foot anchor, same loose leg-pose /
upright / height terms, same DR block and action-rate ramp, trained from scratch. No
single-support hold, no slewed posture blend, no flamingo rewards, terminations or curricula.
The only flamingo *lessons* kept are two facts, not code: a foot-height Gaussian has no
gradient at z = 0 (use a ramp), and a policy trained at one actuator latency overfits it (use
the wide delay DR).

### Which foot, and why one fixed foot is fine

The RIGHT foot stomps, the LEFT foot is the support (planted) foot. An emotion display does
not need to be ambidextrous: nobody watching cares which foot the duck stamps, and a fixed
foot removes a whole branch of the problem (no side flag in the command, no mirror-symmetry
loss, no "which foot is free" decision). The right foot was chosen because the shipped
kick env is right-footed by default and the flamingo v2 pose captured on the real robot
lifts the right leg, so the tooling (foot sensors, sites, batteries) already assumes it.
A left-footed twin is one flag away (`STOMP_FOOT = "left"`), exactly like the kicks.

## What was checked in sim first (AGENTS.md §2)

Measured 2026-09-04 in plain CPU MuJoCo on `scene.xml` (= `robot_groundcontact.xml`, the
model the shipped stand/sit/kick/standup policies were trained on),
script `/private/tmp/claude-501/.../scratchpad/stand_check.py` (results copied here):

| test | result |
|---|---|
| HOME (STAND keyframe) held 3 s with an ideal stiff servo (kp 10) from 8 noisy inits (±3° roll/pitch) | tilt ≤ 0.1°, trunk z 116.6 mm, robot CoM 5.1 mm inside the two-foot contact hull, 6 contacts |
| same with the MJCF PD (kp 0.55 ≈ firmware kP 200) | falls (81° tilt): no pose is passively stable at the real servo stiffness (known since 2026-08-28) — standing is a control task, which is exactly what the stand policy does and what every trick env spawns from |
| foot sites `left_foot` / `right_foot` at the settled stand | z = −0.3 mm (site is at the sole) → foot-lift dead zone 5 mm is safe |
| `head_yaw` sign | +0.6 rad moves the beak 34 mm to +y = the robot's LEFT. Range ±2.97 rad |

So: `STAND_Z = 0.116` (the kick env's 0.115 was measured on the previous model revision; 1.6 mm apart, both inside the std 0.04), spawn z ∈ [0.11, 0.12], HOME + ±0.05 rad joint noise, ±5° tilt — the kick env's proven standing spawn (`set_random_ground_state`, standing bucket only).

## Decisions

| question | decision | why |
|---|---|---|
| Robot model | `robot_groundcontact.xml` (the `MICRODUCK_STANDUP_ROBOT_CFG` spec) with a local `STOMP_ROBOT_CFG` | The model every shipped robot policy (walk/stand/sit/kick/standup) was trained on, and the model the template (ball kick) uses. The true all-collisions model of flamingo v2 buys nothing here (no leg-trunk contact in a 4 cm foot lift) and adds the Warp-vs-CPU hull-margin ambiguity the flamingo notes document. |
| Actuators | BAM XL330 (`FrictionDRBamActuatorCfg`, kp_fw 200, 6.5–8.2 V DR) with **delay DR 0–9 physics steps (0–45 ms)** | BAM is the invariant. The wide delay range is the ONE deliberate deviation from the kick's robot cfg (3–6): the happy hop trained at 3–6 only works WITH the delay, and a policy trained at one latency overfits it. A one-shot gesture must not depend on the exact latency. `ACTUATOR_DELAY_LAGS = (3, 6)` gives the exact kick robot. |
| Command slots | twist tiny ranges (±0.01 m/s, ±0.05 rad/s), head_pose tiny ranges (±0.05/0.05/0.07/0.015), body_pose tiny ranges (±5 mm, ±0.02 rad); all three observed raw; deployment sends all zeros | 61-D contract; every slot samples a small non-zero range so no input weight is dead (AGENTS.md). Nothing in the reward reads the commands. |
| Time in the obs | **none** | Same contract as the happy hop: the policy sees only proprioception + last action. See "How the policy keeps time" below. |
| Episode | 3.0 s, `time_out` termination | Rémi: 2–3 s. Gesture 2.2 s + 0.8 s of stand to prove it ends standing. The manifest `duration_s` will be 3.0. |
| Spawn | `set_random_ground_state` standing_prob 1.0, z 0.11–0.12, ±5° tilt, HOME ± 0.05 rad joints, qvel 0 | Kick env recipe: the runtime hands off from the stand policy whose settled stand is not exactly HOME. |
| Terminations | `fell_over` (trunk tilt > 70°), `nan_state`, `time_out` | Standing task; a fall ends it. |
| Pushes | 0 → 0.08 m/s (it 500) → 0.15 m/s (it 1000), interval 3–6 s (≤ 1 per episode) | The kick's push ramp and timing (after skill discovery), capped at 0.15 instead of the kick's 0.3: a one-shot 3 s trick is never pushed on purpose, robustness margin only. |
| DR | the velocity/kick block: trunk CoM ±3→15 mm, head CoM ±3→10 mm, mass/inertia ±5 %, armature ±10 %, BAM friction ±10 %, foot friction 0.7–1.3, IMU misalignment 6°, encoder bias ±0.015 rad, obs noise + delays, joint_vel 1-tick lag | The recipe that transferred. |
| Symmetry loss | OFF | One-sided task. |

## Timeline (seconds from the episode start; the env knows the time, the policy does not)

Generated by `_stomp_timeline(N_STOMPS)` in the env: settle `SETTLE_END = 0.3`, then per stomp
a lift of `LIFT_DUR = 0.25` s and an impact of `IMPACT_DUR = 0.20` s, every `STOMP_PERIOD = 0.5`
s; the head-yaw target arrives at ±0.6 rad exactly when each impact window opens (3 rad/s
ramps); 0.2 s after the last impact it ramps back to 0 and the end-stand window opens.

```
0.0     0.3    0.55  0.75 0.8   1.05  1.25 1.3   1.55  1.75    1.95 2.15 2.2        3.0
|settle |lift1 |imp1 |   |lift2 |imp2 |   |lift3 |imp3 |  hold  | →0 |  end stand   |
head:   0 → +0.6 at 0.55 (left) → −0.6 at 1.05 (right) → +0.6 at 1.55 (left) → 0 at 2.15
```

- `LIFT = [(0.3, 0.55), (0.8, 1.05), (1.3, 1.55)]`, `IMPACT = [(0.55, 0.75), (1.05, 1.25), (1.55, 1.75)]`,
  `END_STAND = [2.2, 3.0]`.
- Head yaw keyframes `(0,0) (0.35,0) (0.55,+0.6) (0.65,+0.6) (1.05,−0.6) (1.15,−0.6) (1.55,+0.6) (1.95,+0.6) (2.15,0) (3.0,0)`;
  every ramp is 3 rad/s (a ±0.6 → ∓0.6 swing takes 0.4 s), inside an XL330's ~5 rad/s no-load
  speed. +yaw = left (measured above). The ramps are a fixed-rate target for the reward
  (AGENTS.md "no jackpots": arriving early pays nothing), not a posture blend the policy
  tracks through a command.
- The same foot (right) does all three stomps; the lifts are small (3 cm target, 2 cm
  success threshold).
- Head-yaw success windows: `[impact − 0.1, impact + 0.2)` per stomp with the alternating sign.

### How the policy keeps time without a clock in the obs

The observation is 61-D: 3 gyro + 3 gravity + 14 joint positions + 14 joint velocities +
14 **last actions** + 13 command slots (all ≈ 0). There is no phase or elapsed time, exactly
like the happy hop. The policy still knows where it is in the gesture because the gesture
itself is a state machine written in the body:

1. At t = 0 the robot is in the stand pose with zero last-action → "start".
2. Once the head is turned left (head_yaw ≈ +0.6 in joint_pos AND in last-action) → "stomp 1
   is done, waiting for / doing stomp 2".
3. Once the head is turned right → "stomp 2 is done, come back to the stand".
4. Head centred again and the last-action ≈ HOME → "finished, stay still".

So the head yaw is both the visible emotion and the policy's memory register. With three
stomps the register is left / right / left: stomps 1 and 3 both happen with the head left,
so what tells them apart is the direction the head is MOVING (joint velocity is in the obs)
and the 0.5 s stomp rhythm itself; if the video shows a fourth stomp or a missed third one,
plan B's post-last-stomp latch or a head amplitude that grows with the stomp index
(0.4 / 0.6 / 0.8 rad) makes the register unambiguous. The
sub-second timing inside each stage (how long to lift before slamming) is learnt as a
feed-forward trajectory driven by the foot's own joint positions/velocities, the way the hop's
crouch → extend sequence is. The reward windows below are what make the learnt tempo match
the intended one: reward only pays during the windows, so a policy that is early or late
collects nothing.

Risk (open): with no clock, a policy could loop the gesture (stomp a third time) or start
before the settle window. Both are taxed (foot must be planted outside the lift/impact
windows; end-stand window pays for stillness), and the episode is cut at 3.0 s. Also a
3 s episode at 0.5 s per stomp leaves no room for a fourth before the end-stand window. If the video
shows re-triggering, plan B adds a hidden one-dimensional "progress" state to the reward gates
(a latch: after stomp 2 the foot-lift reward is zero for the rest of the episode) — cheap, and
it does not touch the obs contract.

## Reward table

Sign convention (AGENTS.md): mjlab-base cost functions return ≥ 0 → negative weight;
self-negating microduck functions (return ≤ 0) → POSITIVE weight. On every run every
`Episode_Reward/<penalty>` in wandb must read ≤ 0. Bounded per step, no one-shot bounties
(no jackpots): every task term pays at most `weight × 1` per step and only inside its window.
Every non-stomp row is the kick env's term with the kick env's weight unless noted.

| term | fn (`tasks/mdp.py`) | weight | what it pays for | notes |
|---|---|---|---|---|
| `stomp_foot_lift` | `stomp_foot_lift` (new) | +3.0 | right-foot site height ramp: `clamp((z − 0.005)/(0.03 − 0.005), 0, 1)`, only inside the LIFT windows, gated on the left foot being in contact | dense from the first mm (a Gaussian pays no gradient at z = 0); saturates at 3 cm ("small lifts") — no bonus for kicking higher. ≤ 12 steps × 3 per stomp |
| `stomp_foot_impact` | `stomp_foot_impact` (new) | +3.0 | DOWNWARD right-foot velocity `clamp(−v_z / 0.3, 0, 1)` inside the IMPACT windows, gated on the left foot in contact | this is the stomp: a fast descent onto the floor. CAPPED at 0.3 m/s so it is a stomp, not a slam; 0.3 m/s is what a 3 cm drop in 0.1 s needs. ≤ 10 steps × 3 per stomp |
| `stomp_foot_planted` | `foot_contact_outside_windows` (new) | +1.0 | right foot in contact whenever NOT in a lift/impact window | says "the foot is down between stomps and at the end"; kills a third stomp / hovering |
| `support_foot_grounded` | `foot_contact_reward` (slot 0 = left) | +2.0 | left foot always in contact | anti-hop (kick env recipe) |
| `head_yaw_track` | `head_yaw_schedule_track` (new) | +3.0 | `exp(−((q_head_yaw − target(t)) / 0.25)²)` against the SLEWED keyframe target | the target moves at a fixed rate → being early pays nothing (no jackpot). std 0.25 = the error we still care about at ±0.6 |
| `pose_stand_legs` | `pose_target_match`, legs, std 0.5 | +1.5 | legs near HOME | loose on purpose: the stomp is a transient leg deviation and must stay affordable (kick env) |
| `pose_head_level` | `pose_target_match`, joints 5, 6, 8, std 0.3 | +1.0 | neck pitch, head pitch, head roll at HOME | the head yaws, it does not dive or tilt |
| `end_stand` | `pose_match_in_windows` (new), all 14 joints, std 0.25, window [2.2, 3.0] | +2.0 | ends in the stand pose | "ends standing near the stand pose" |
| `upright` | mjlab `upright`, std² 0.05 | +2.0 | trunk vertical | velocity/kick recipe |
| `height_stand` | `height_target_gaussian`, 0.116, std 0.04 | +1.0 | trunk at standing height | discourages a crouch as stomp prep |
| `trunk_az` | `trunk_vertical_accel_penalty` (≤ 0) | **+0.005** | −|a_z| of the trunk | the impact must stay in the foot, not shake the body; standup's magnitude (a bigger weight is a motion-blocker) |
| `foot_overspeed` | `foot_overspeed_penalty` (new, ≤ 0) | **+1.0** | −max(0, ‖v_right_foot‖ − 0.8)² always | the "no thrashing" guard on the moving foot: 0.8 m/s is well above the rewarded impact speed |
| `dof_pos_limits` | mjlab (≥ 0), inherited from the base like the kick | −1.0 | off the mechanical limits | the stomp never approaches a limit; if a run parks a joint on one, add `joint_pos_limit_proximity` (AGENTS.md) |
| `action_rate_l2` | mjlab (≥ 0) | −0.1 → −0.3 (it 500) → −0.6 (it 1000) | smoothness | the kick's ramp, introduced AFTER discovery; stops at −0.6, not −1.0: the stomp is a fast one-shot (the kick's own note) |
| `body_ang_vel` | mjlab (≥ 0) | −0.05 | motion-blocker, kept low | |
| `angular_momentum` | mjlab (≥ 0) | −0.02 | | |
| `self_collisions` | mjlab (≥ 0) | −1.0 | | |
| `stomp_success` | `stomp_success` (new, diagnostic) | 1e-3 | 1 on the last step of an episode that met the success metric | mjlab drops weight-0 terms; 1e-3 keeps it in the log (flamingo idiom): `Episode_Reward/stomp_success × 1000` = success rate |

Task reward mass ≈ 18.5/step at full (kick env ≈ 18), so the shared regularizer weights act at
the same relative strength.

Penalty-sign check, done in `tests/test_stomp_cfg.py`: `trunk_az`, `foot_overspeed` have
POSITIVE weights (self-negating functions); `action_rate_l2`, `body_ang_vel`,
`angular_momentum`, `self_collisions`, `dof_pos_limits` have NEGATIVE weights (≥ 0 costs).
Every task term is ≥ 0 with a positive weight. Verified on the local Warp smoke: every
`Episode_Reward/<penalty>` read ≤ 0.

Reward-hacking audit (each positive term against the cheapest way to farm it):
- lift without impact: the impact term is 3/step for 10 steps, the lift term pays only 12 steps → dropping the foot is worth it.
- Going from 2 to 3 stomps did NOT change the reward table (same terms, weights and functions); only the generated windows, the lift target (4 → 3 cm), the impact cap (0.4 → 0.3 m/s) and the success latches (N per stomp) changed.
- impact without lift: `−v_z` needs height to come from; the ramp gate (dead zone 5 mm) pays nothing for a scrape.
- hop instead of stomp: `support_foot_grounded` (+2 every step) plus the `stomp_foot_lift/impact` gate on the LEFT foot's contact make a hop pay nothing.
- stomp at the wrong time: windows only.
- slam as hard as possible: the impact reward is capped at 0.4 m/s, foot speed above 0.8 m/s is taxed quadratically, trunk |a_z| is taxed.
- head turned by the trunk instead of the neck: `upright` and `head_yaw_track` measure the joint, not the world heading; `body_ang_vel` taxes trunk spinning.
- never stomp, just stand: collects ≈ 9.5/step out of 18.5 — the stomp terms are the main task term and must be seen to GROW in wandb (`Episode_Reward/stomp_foot_lift`, `stomp_foot_impact`), not just the total.

## Success metric (logged as `stomp_success`, evaluated per episode)

All of: (1) right-foot clearance ≥ 2 cm at some step of EACH stomp's lift ∪ impact window
(three of them); (2) head yaw ≥ +0.5 rad in [0.45, 0.75), ≤ −0.5 rad in [0.95, 1.25), ≥ +0.5
rad in [1.45, 1.75); (3) upright at the end (projected gravity z < −0.9, i.e. tilt < 26°) and
not terminated by a fall. Target for the first run: > 80 % of episodes at push 0.15 m/s.

## What to look at in the video (`duck-video ... --actuator bam --delay 0 9 --jvel-lag 1`, CPU proxy, then Warp `gt_eval.py`)

1. Three clear stomps of the SAME (right) foot, 0.5 s apart: the foot visibly leaves the floor (≥ 2 cm), comes down fast, stops on the floor (no bounce, no fourth stomp).
2. Head snaps left / right / left with the stomps, level (no dive), then re-centres.
3. The left foot never leaves the floor; the trunk stays upright and at height (no crouch, no lean as a counterweight).
4. Servo plausibility: joint speeds (the json reports them) well under the XL330 no-load ~5 rad/s; commanded targets not parked on limits; no jitter in the stand windows.
5. It ends standing still within 3.0 s, in a pose the stand policy can take over from.
Report honestly: "stomps twice but the second is a scrape", "falls 1 in 5", etc.

## Plan B (in order)

1. Foot never lifts (the "just stand" attractor): raise `stomp_foot_lift` to 5.0 and/or shrink the settle window; add a reverse-curriculum spawn with the foot already lifted at t = 0.4.
2. Lifts but no stomp (foot lowered gently): raise the impact weight / lower `v_cap` to 0.3 so the cap is reached, and make sure `Episode_Reward/stomp_foot_impact` is the term that is flat.
3. Head lags the schedule: widen the ramps (0.3 s) or stretch the whole timeline to 3.5 s before touching the weight (the episode may grow to 3.5 s; Rémi asked for 2–3 s as the target, not a hard cap).
4. Re-triggering / a fourth stomp, or stomps 1 and 3 merging: add the post-last-stomp latch to the gates, or make the head amplitude grow with the stomp index (see "How the policy keeps time").
5. Thrashing: move `action_rate_l2` stages earlier, raise `foot_overspeed` to 2.0, add `leg_joint_vel_l2`.
6. If nothing stomps at all in 1000 iterations: the timed windows may be too tight for a policy without a clock — plan C is a one-slot phase clock in the twist vx slot (GroundPick idiom); it changes the runtime contract (the runtime would have to write a ramp), so only with Rémi's OK.

## Out of scope

Left-foot mirror, sound sync, the runtime button, the real robot, the programmatic stomp (dropped by Rémi: RL only).

## History

- 2026-09-04 morning: double-stomp draft (2 stomps 0.8 s apart, 3.5 s episode), first on a
  mixed kick/flamingo recipe → reworked onto the pure kick recipe at Rémi's request, 3.0 s.
  Local Warp smoke OK; HF smoke job `6a9a87dee686246ca69a0c64` (`pollen-robotics/stomp-smoke-20260904-1056`,
  private) COMPLETED: 5 iterations, ONNX exported, ≈ $0.04. That job validated the pipeline
  for the 2-stomp windows; the reward code is unchanged since.
- 2026-09-04 midday: three stomps in short succession (this version), `N_STOMPS = 3`.
