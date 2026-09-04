# Anger motion by RL: the angry stomp (three stomps, same foot) — status report

Date: 2026-09-04. Everything below is in simulation; the real robot was not touched and no
full training was launched (Rémi asked to be asked the first time).

## What was built (one paragraph)

A new reinforcement-learning environment, `Mjlab-Stomp-Flat-MicroDuck`, in which the duck
starts from a normal stand, lifts its RIGHT foot a little and bangs it down THREE times in
short succession (0.5 s apart), snaps its head LEFT / RIGHT / LEFT with the stomps, and ends
standing, all in 3.0 s with the 13-D command block at zero (the same "one-shot trick" contract as the kicks
and the happy hop: the runtime swaps this policy in from the stand policy, plays it, swaps
back). Per Rémi's direction the template is the **ball kick** env (a short one-shot foot
swing from a stand), trained from scratch; nothing is inherited from the flamingo work.
The stomp count is one constant (`N_STOMPS`, default 3; 2 gives the earlier double stomp);
the whole timeline is generated from it. Rémi also dropped the programmatic-stomp fallback:
RL only, because even a short foot lift is a balance problem.

Files (all on the local git branch `emotions-stomp` of `/Users/remi/microduck/microduck_rl`,
commits `4a86aad` (double stomp) and the follow-up (three stomps); nothing pushed):

| what | where |
|---|---|
| design spec (reward table, timeline, success metric, plan B) | `/Users/remi/microduck/microduck_rl/docs/superpowers/specs/2026-09-04-angry-stomp-design.md` |
| environment | `/Users/remi/microduck/microduck_rl/src/mjlab_microduck/tasks/microduck_stomp_env_cfg.py` |
| new reward functions (block `# --- stomp` at the end) | `/Users/remi/microduck/microduck_rl/src/mjlab_microduck/tasks/mdp.py` |
| registration (`Mjlab-Stomp-Flat-MicroDuck` + play variant) | `/Users/remi/microduck/microduck_rl/src/mjlab_microduck/tasks/__init__.py` |
| cfg tests (14, all pass) | `/Users/remi/microduck/microduck_rl/tests/test_stomp_cfg.py` |
| this report | `/Users/remi/microduck/notes/emotions/motion/anger-rl/REPORT.md` |

## Design summary (plain English)

Terms: *env* = the simulated task (robot, rewards, resets); *reward term* = one line of the
score the policy maximises; *DR* = domain randomisation, random small changes to masses,
frictions, delays and sensor noise so the policy does not overfit the simulator; *obs* = the
61 numbers the policy sees every 20 ms; *BAM* = the voltage-level model of the XL330 servo
used in all training here.

- **Robot model**: `robot_groundcontact.xml`, the model every shipped policy (walk, stand,
  sit, kicks, standup) was trained on and the kick env's model. BAM servos, with the
  actuator delay randomised over 0–45 ms (wider than the kick's 15–30 ms: a one-shot
  gesture must not depend on the exact latency; the happy hop only works at the delay it
  was trained with). One constant (`ACTUATOR_DELAY_LAGS`) flips it back to the kick's exact robot.
- **Start**: standing at HOME with small joint noise (±0.05 rad) and tilt (±5°), the kick
  env's spawn. Checked in CPU MuJoCo first: with an ideal stiff servo the stand holds 3 s
  from noisy starts with 0.1° tilt and the centre of mass 5 mm inside the two-foot support
  polygon (trunk height 116.6 mm, used as the height target). With the real servo stiffness
  nothing stands passively (known since August): standing is what the policy does.
- **Timeline** (the env knows the time; the policy does not): settle 0–0.3 s; then every
  0.5 s a stomp = 0.25 s lift + 0.2 s impact: lifts at 0.3 / 0.8 / 1.3 s, impacts at 0.55 /
  1.05 / 1.55 s; head-yaw target arrives at +0.6 rad (left) / −0.6 (right) / +0.6 (left)
  exactly with each impact (3 rad/s ramps, inside the servo's speed), back to 0 by 2.15 s;
  end-stand window 2.2–3.0 s.
- **How the policy keeps time with no clock in the obs**: the obs contains the last action,
  the joint positions and the joint velocities, so the head is a memory register: centred =
  start, moving/held left = stomp 1, right = stomp 2, left again = stomp 3, centred again =
  finished; stomps 1 and 3 are told apart by which way the head is moving and by the 0.5 s
  rhythm. Same idea as the happy hop, whose crouch → extend sequence is read off its own leg
  joints. If a run confuses stomps 1 and 3, the spec's plan B grows the head amplitude with
  the stomp index.
- **Rewards** (weights in the spec; unchanged between the 2- and 3-stomp versions): right-foot
  height ramp in the lift windows (+3, saturates at 3 cm: small lifts); DOWNWARD right-foot
  speed in the impact windows (+3, capped at 0.3 m/s = a stomp, not a slam); right foot on the floor outside the stomp windows (+1); left foot
  always on the floor (+2, anti-hop); head yaw tracking the ramped target (+3); legs near
  HOME (loose, +1.5), head level (+1), whole body in the stand pose at the end (+2), upright
  (+2), trunk at height (+1). Anti-violence: foot speed above 0.8 m/s taxed, trunk vertical
  acceleration taxed, plus the kick's action-rate ramp (introduced after skill discovery),
  body angular velocity, self-collision and joint-limit costs. Every reward pays at most its
  weight per tick and only inside its window: no jackpots.
- **Success metric** (logged as `stomp_success`; × 1000 = success rate): all three stomps
  with ≥ 2 cm foot clearance, head yaw ≥ 0.5 rad left / right / left around each impact,
  upright at the end, no fall.
- **Which foot**: the right, fixed. An emotion display needs no left/right choice; a fixed
  foot removes a side flag and a symmetry loss. A left-footed twin is one flag away.

## What the smoke tests showed

1. **cfg tests** (`UV_PROJECT_ENVIRONMENT=/Users/remi/microduck/.venv-mjlab uv run --with pytest pytest tests/test_stomp_cfg.py`): 14 passed. They lock in: groundcontact model + BAM + delay 0–9; joint indices and foot sites/geoms resolve on the actual model (`head_yaw` = servo 7, `+yaw` = left); every reward weight has the intended sign (self-negating penalties positive, costs negative); the actor keeps the 61-D `[twist, head, body]` slot layout with tiny live command ranges and the same actor term list as the kick env; three non-overlapping stomp windows 0.5 s apart, the time-window gates open exactly on the timeline (boundary steps included), the head-yaw schedule arrives at ±0.6 rad with each impact, alternating left / right / left, at ≤ 3 rad/s, and returns home; nothing flamingo-shaped is in the env (Rémi's call).
2. **Local Warp smoke on this Mac's CPU** (16 envs × 2 iterations: `CUDA_VISIBLE_DEVICES= UV_PROJECT_ENVIRONMENT=/Users/remi/microduck/.venv-mjlab uv run train Mjlab-Stomp-Flat-MicroDuck --env.scene.num-envs 16 --agent.max_iterations 2 --agent.logger tensorboard`), run three times (double stomp, kick rework, three stomps): builds, actor input 61, critic 74, all 19 reward terms compute, every penalty reads ≤ 0, no NaN, ≈ 1.2 s/iteration, exit 0. Three-stomp run, iteration 1: mean reward 1.58, `stomp_foot_lift 0.027`, `stomp_foot_impact 0.012`, `head_yaw_track 0.23`, penalties `body_ang_vel −0.16`, `action_rate_l2 −0.59`, `dof_pos_limits −0.006`, `trunk_az −0.004`, `foot_overspeed −0.0009`, `self_collisions −0.004`. Task terms are near zero, as expected from a random policy.
3. **HF smoke job** (64 envs × 5 iterations, t4-small: `duck-train Mjlab-Stomp-Flat-MicroDuck --env.scene.num-envs 64 --agent.max_iterations 5 --flavor t4-small --timeout 20m --run-name stomp-smoke-20260904-1056 --detach`): job `6a9a87dee686246ca69a0c64`, https://huggingface.co/jobs/pollen-robotics/6a9a87dee686246ca69a0c64, checkpoints/ONNX at https://huggingface.co/pollen-robotics/stomp-smoke-20260904-1056. COMPLETED (submitted 08:57 UTC, ran 08:58:25 → 09:02:32, ≈ 5.5 min billed at $0.40/h ≈ **$0.04**); 5 iterations logged (mean reward 1.67 → 2.04, episode length 18 → 35 ticks), `exported/policy.onnx` + `model_0/4.pt` uploaded; the repo is private. This job ran the double-stomp windows (submitted before Rémi's three-stomp request); the reward code is unchanged since, only the generated constants, so the pipeline it validated is the one the three-stomp env uses (confirmed again by the local Warp smoke above).

## The real run: exact command and cost (NOT launched, asking first)

```bash
workon duck
hf jobs ls --namespace pollen-robotics     # nothing of ours running first
duck-train Mjlab-Stomp-Flat-MicroDuck --env.scene.num-envs 4096 --agent.max_iterations 2000 --flavor rtx-pro-6000 --timeout 75m --run-name stomp-r1-$(date +%Y%m%d-%H%M) --detach
duck-curves <job_id>                        # afterwards, non-blocking
```

Cost: rtx-pro-6000 is $2.75/h; 4096 envs run at ≈ 1.3 s/iteration on it (flamingo stage-1
measurement), so 2000 iterations ≈ 43 min + ≈ 5 min bootstrap ≈ 48 min ≈ **$2.2**; the
75 min timeout caps it at $3.4. AGENTS.md budgets ≈ 1000 iterations for a simple episodic
trick; 2000 leaves room for the action-rate ramp (it 500 / 1000) and the push ramp to land
after the skill exists. Checkpoints every 250 iterations, `exported/policy.onnx` at the end.
This is the three-stomp env (`N_STOMPS = 3`, the default in the file). What to watch in wandb (`pollen-robotics/mjlab_microduck`, experiment `stomp_right`):
`Episode_Reward/stomp_foot_lift` and `stomp_foot_impact` must GROW (they are the task; the
total can rise on the stand terms alone), every penalty ≤ 0, `stomp_success × 1000` = success
rate, mean episode length → 150 ticks (3 s, no falls).

After the run, the evaluation plan is in the spec: `duck-video <policy.onnx> --actuator bam
--delay 0 9 --jvel-lag 1 --seconds 3` on the CPU proxy and the Warp ground truth
(`scripts/hf/gt_eval.py`), one clip per checkpoint, joint speeds and falls reported, a page
opened for Rémi.

## Open risks

- **No clock in the obs** is the biggest design bet. It is the happy-hop contract, so it is
  known to work for ONE crouch-and-hop; three timed stomps 0.5 s apart plus a head schedule
  is more to keep in body state, and stomps 1 and 3 share the same head side. The windows are what makes the tempo learnable; if the policy is
  systematically early/late, plan B in the spec is to widen ramps or stretch the timeline
  (up to 3.5 s) or grow the head amplitude per stomp, and plan C (last resort, needs Rémi's OK because it changes the runtime
  contract) is a phase ramp in the twist vx slot.
- **"Just stand" attractor**: standing collects about half the reward mass. The task terms
  are weighted to beat it once the foot lifts at all, but the first run must be judged on
  the stomp terms growing, not the total.
- **Stomp vs slam**: the impact reward is capped and over-speed is taxed, but RL will find
  the cheapest violent thing left. The video and the joint-speed json are the judges;
  Rémi's veto stands.
- **Sim-to-sim**: this env uses the groundcontact model, not the true all-collisions one.
  A 4 cm foot lift does not touch the trunk, so it should not matter; the Warp-vs-CPU
  proxy comparison after the run will tell.
- Pushes are capped at 0.15 m/s (the kick goes to 0.3); a bump mid-stomp on hardware may
  topple it, acceptable for a 3 s display but worth saying.

## Runs (one entry per training run: what changed, why, what the rollouts show)

Evaluation recipe for every run (both engines, house rule): Warp ground truth =
`scripts/hf/gt_eval.py Mjlab-Stomp-Flat-MicroDuck --checkpoint-file model_N.pt --steps 160 --no-push --yaw 0 --seed S`
(the exact training engine and model, on this Mac's CPU); CPU proxy = `motion/anger-rl/stomp_eval.py proxy`
(plain MuJoCo on the exact training model via mjlab, BAM servo, 1.75 A current limit, actuator delay 3–6 steps,
joint-velocity lag 1, entered from the shipped `alpha_stand.onnx` at t = 1 s like the runtime does, several seeds
with ±0.03 rad joint noise). `stomp_eval.py analyze DIR` counts the stomps (right-foot site ≥ 2 cm up, then contact),
lift height, touchdown speed, head yaw at touchdown, max joint speed (50 Hz finite difference), support-foot lifts,
falls and the end state, and builds the contact sheets + `index.html`.

### r1 — `stomp-r1-20260904-1111` (job `6a9a8b35e686246ca69a0cdf`), launched 11:11

- What: the three-stomp design as specified (env commit `65a0a5e`), 4096 envs × 2000 it, rtx-pro-6000, 75 min cap, ≈ $2.2.
- Why: first run of the design; Rémi's go ("the plan is good, let's see what it does").
- Curves (wandb `stomp_right`, `Episode_Reward/*` = weight × mean value per second; the lift term's ceiling is 0.72, the impact term's 0.6):

  | it | mean reward | stomp_foot_lift | stomp_foot_impact | head_yaw_track | action_rate_l2 | fell_over/ep |
  |---|---|---|---|---|---|---|
  | 0 | 1.6 | 0.002 | 0.001 | 0.15 | −0.23 | 16.1 |
  | 50 | 14.7 | **0.41** | 0.067 | 1.55 | −1.41 | 0.75 |
  | 250 | 24.7 | 0.007 | 0.023 | 1.58 | −0.80 | 0.21 |
  | 500 | 25.4 | 0.087 | 0.034 | 1.60 | −0.64 (tax → −0.3) | 0.08 |
  | 900 | 25.1 | 0.13 | 0.049 | 1.72 | −0.70 | 0.04 |
  | 1000 | 27.2 | **0.006** | 0.009 | 1.62 | −0.71 (tax → −0.6) | 0.08 |
  | 1500 | 24.6 | 0.005 | 0.012 | 1.62 | −0.86 | 0.17 |
  | 1999 | 23.4 | 0.011 | 0.016 | 1.61 | −0.88 | 0.08 |

  `stomp_success` = 0 throughout; every penalty ≤ 0 throughout. Reading: at it 50 the policy
  lifted the foot a lot (57 % of the lift ceiling) but fell in most episodes; once it learnt to
  stand (it 250) the lifting vanished — the "just stand" attractor named in the spec's risks —
  and crawled back to 21 % of the ceiling by it 900; then the action-rate tax step to −0.6 at
  it 1000 wiped it out for good (a metric stepping DOWN exactly at a curriculum boundary is the
  AGENTS.md signature of a tax introduced before the skill exists). Cost: 18 min bootstrap +
  50 min training ≈ 68 min ≈ $3.1 (slow package downloads that day).
- Rollouts (both engines, `/Users/remi/microduck/notes/emotions/motion/anger-rl/r1/index.html`, 9 clips + contact sheets):
  - Final policy (exported ONNX in the CPU proxy, 5 seeds; checkpoint 1999 in Warp, 2 seeds): **0 stomps in 7/7
    rollouts**, head yaw range ±0.04 rad (never turns), stands still, upright, both feet down, max joint speed
    2–8 rad/s. It is a stand policy. Honest verdict: r1 learnt nothing of the gesture.
  - Checkpoint 750 in Warp (where the lift term peaked): ONE stomp per rollout — right foot up 30–31 mm at
    t ≈ 0.45 s, down at 0.39 m/s, head turned to +0.53 / +0.69 rad (left) around it; seed 1 then kept the foot
    hovering until the end (a "lift without the slam" hover). So the skill existed in embryo at it 750, on the
    first stomp only, and was wiped out at it 1000.
  - Two diagnoses, both reward-side (measured, not guessed): (a) the head term had no gradient — with std 0.25 a
    ±0.6 rad plateau pays exp(−5.8) ≈ 0 when the head stays at 0, and staying at 0 still collects 60 % of the
    term from the ramps and the zero segments, so the head never learnt to move (yaw range ±0.04); (b) the
    stomp terms are worth ~13 % of the return (short windows) and the action-rate step at it 1000 out-priced them.
- Cost: ≈ $3.1 (68 min on rtx-pro-6000, 18 min of it bootstrap).

### r2 — `stomp-r2-strong-20260904-1243` (job `6a9aa0ef259f8e97255ddfe9`), launched 12:43, task `Mjlab-StompStrong-Flat-MicroDuck`

- What changed vs r1 (nothing else): `stomp_foot_lift` and `stomp_foot_impact` weights 3 → 9 (the stomps become
  ~35 % of the return instead of ~13 %); `pose_stand_legs` 1.5 → 1.0; action-rate weight flat at −0.1 (no ramp: the
  it-1000 step killed the skill in r1; anti-thrash pressure stays on the physics terms `foot_overspeed`, `trunk_az`,
  `body_ang_vel`); head yaw Gaussian std 0.25 → 0.4 plus a new L1 companion `head_yaw_l1` (weight 2, self-negating:
  −1.2/step at the full 0.6 rad error), a constant pull toward the head schedule.
- Why: the two r1 diagnoses above (AGENTS.md: taxes after skill discovery; Gaussian + L1 for a target the policy
  is far from).
- A first r2 without the head fix (job `6a9a9baa259f8e97255ddea0`, 12:21) was cancelled by me 8 min later, in
  bootstrap, once the r1 rollouts showed the dead head term (≈ $0.3 lost, 70 min saved).
- The 12:33 submission of this exact job (`6a9a9e8e259f8e97255ddf3b`) died in bootstrap on HF infrastructure
  (`apt` could not reach security.ubuntu.com, exit 100, ≈ $0.4); resubmitted unchanged at 12:43.
- Curves (ceilings: lift 2.16, impact 1.8, head Gaussian 3.0):

  | it | mean reward | ep. length | stomp_foot_lift | stomp_foot_impact | head_yaw_track | head_yaw_l1 | action_rate_l2 | foot_overspeed | fell_over/it |
  |---|---|---|---|---|---|---|---|---|---|
  | 50 | 15.9 | — | 1.72 | 0.28 | 1.95 | −0.49 | −1.62 | −0.005 | 1.0 |
  | 300 | 21.4 | 149 | 1.85 | 0.82 | 2.15 | −0.44 | −1.31 | −0.04 | 0.6 |
  | 1000 | 21.3 | 149 | 1.98 | 0.93 | 2.03 | −0.48 | −1.66 | −0.02 | 0.8 |
  | 1999 | 25.3 | 149 | **2.01** (93 %) | **1.01** (56 %) | **2.44** (81 %) | −0.31 (mean head error ≈ 0.15 rad) | −1.64 | −0.02 | 0.5 |

  Every penalty ≤ 0 throughout. The stomp terms are now most of what the policy earns and they hold
  for the whole run (no collapse, no tax step); `stomp_success` stayed 0 (the all-or-nothing
  metric: three ≥ 2 cm lifts + head ≥ 0.5 rad each way + upright at the last tick). Falls: ≈ 0.5–1
  `fell_over` per iteration of 4096 envs, i.e. rare. Cost: 71 min running (18 min bootstrap) ≈ $3.3.
- Rollouts (both engines, `/Users/remi/microduck/notes/emotions/motion/anger-rl/r2/index.html`, 9 clips + contact sheets):
  **it stomps, but it is not a little stomp.** Per rollout (CPU proxy 5 seeds / Warp ck 1999 3 seeds + ck 1000):
  1–3 counted stomps (the analyser merges lifts that touch down for a single tick), right foot lifted
  **12–19 cm** (the whole leg swung up to hip height; the design asked for 3 cm), touchdown speed
  **0.65–1.15 m/s** (cap for reward was 0.3 m/s; overspeed tax at 0.8 barely bit), trunk tilt up to
  **0.70–0.80** (≈ 44–53°: the body is thrown sideways over the left foot for each swing), the LEFT
  (support) foot also leaves the floor by 32–40 mm at moments (a hop component), max joint speed
  15–17 rad/s, commanded targets up to 8 rad beyond HOME. The head part WORKS: yaw goes
  +0.7 → −0.6 → +0.7 with the stomps and re-centres, in every rollout. Ends upright in 8/9 (Warp ck 1999
  seed 1 falls at the end; ck 1000 ends standing but 1 rad off the stand pose). Verdict against Rémi's
  veto: violent (leg to hip height, 45° lean, 1 m/s slams, 8 rad targets) — fails "physically
  plausible, no thrashing", although it is recognisably three angry foot slams with head turns.
  Cause (reward-side, measured): the lift ramp saturates at 3 cm and never says "lower"; a huge
  swing buys a long fast descent through the impact window; the upright Gaussian (std² 0.05) is
  already ≈ 0 at 25° so a 45° lean costs nothing more; nothing taxed foot height, tilt or targets
  beyond the joint range.
- Cost: ≈ $3.3 (+ $0.3 for the cancelled 12:21 job, + $0.4 for the 12:33 infra failure).

### r3 — `stomp-r3-clean-20260904-1428` (job `6a9ab958259f8e97255de669`), launched 14:28, task `Mjlab-StompClean-Flat-MicroDuck`

- What changed vs r2 (`clean=True`, env commit `10ed505`): the lift reward is a TRIANGLE (0 at 5 mm, full at 3 cm,
  back to 0 at 6 cm) and a `foot_too_high` tax (self-negating, weight 2; 10 cm over 6 cm costs 1/step) so higher is
  worse, not neutral; both stomp terms are gated on the trunk being upright (projected gravity z < −0.94 ≈ tilt < 20°:
  a stomp with the body thrown sideways does not count) and the impact term only counts in the last 4 cm of the descent
  (a drop from hip height pays nothing); a `trunk_tilt` tax (weight 10, quadratic above 20°); `foot_overspeed` limit
  0.8 → 0.6 m/s and weight 1 → 10 (1 m/s now costs −1.6/step); commanded targets HARD-clamped to 98 % of the joint
  ranges (Rémi's 2026-09-02 rule, the robot's safety.rs does the same) plus an `action_overrun` cost (−0.5). Head
  terms, weights 9/9, flat action-rate, everything else identical to r2.
- Why: each item answers one measured excess of r2 (18 cm lift, 45° lean, 1 m/s slam, 8 rad targets). Same weights
  on the stomp terms so the stomping itself is not discouraged; the gates and taxes shape HOW.
- Risk: the upright gate + tilt tax may push the policy back toward "just stand" (r1). Watch `stomp_foot_lift`
  staying near its 2.16 ceiling and `trunk_tilt` shrinking together.
- Result: (pending)
