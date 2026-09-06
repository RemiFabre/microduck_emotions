# Episode 3: brief for a fresh agent

Written 2026-09-06 from Rémi's spoken brief. Work autonomously. Show results early and often
(pages with videos, sounds folders opened on screen), keep `NOTES.md` up to date, ask Rémi when a
choice is his or when you want to push back. Absolute paths, plain English, define terms.

Read first: `README.md` (what exists, the recipe), `NOTES.md` (the episode 2 log, every attempt
and decision), then the theater repo `https://github.com/RemiFabre/agentic_robot_theater`
(`README.md`, `microduck/README.md`, `microduck/EMOTIONS.md`, `scenes/lake/`). The robot facts
(ssh, pad, ship script, volume) are in those two microduck pages. Hard rules from episode 2:

- **Never make the real duck move from a script or an agent.** Read-only diagnosis and installs
  only; Rémi triggers every motion with the pad. (An agent once drove it unasked; it could have
  fallen off the table.) The Reachy Mini may be run when Rémi says so for that run.
- Never push to `pollen-robotics/*`. `RemiFabre/*` repos are ours; commit often.
- On the real duck, anything that moves the head's mass forward (neck forward/down, deep head
  pitch) makes the walking policy step forward. The simulation does not show it. Keep programmatic
  head motions shallow (|neck| <= ~0.75), prefer roll and yaw. Test on the robot early.
- Sound is paramount; design it on the motion's beats; the beak opens with the sound.
- Rémi's veto on RL: physically plausible for XL330 servos, no thrashing, low amplitude.

## What an emotion is (write this into README.md too)

An emotion = **a motion + a sound designed together**, bound to a pad button in emotion mode
(`DPad-Up tap`; A sad, B devastated, Y curious so far; X free). The motion is one of three kinds:

1. a **program**: head deltas, body pose and mouth as a pure function of time on top of the
   shipped standing / walking policy (`Kind::Sad`, `Kind::CuriousQuacks`);
2. a **policy**: a trained network started as a skill (`sit_toggle`, `ground_pick`, kicks,
   roulade, and later the RL stomp);
3. a **combination**: a skill trigger plus a program on top, while the skill's policy holds the
   pose (`Kind::Devastated` = sit_toggle then head program; head slots track while seated).

Future emotions will mostly be kinds 1 and 3. The pattern in `padd/src/expressions.rs`:
`skill_at_start`, `sound_at_start`, `head_at(t)`, `pose_at(t)`, `mouth_at(t)`, `twist_at(t)`,
a `Kind`, a length, a keyframe test against the simulation JSON.

## New emotions to create (in this order; each = sim page, Rémi picks, ship, Rémi tests)

| emotion | button | motion | sound |
|---|---|---|---|
| **yes** | free one (propose) | one clear nod: head pitch down and back, maybe twice, short (< 1 s) | ONE quack, affirmative (flat or slightly falling) |
| **no** | free one | head shake left-right, short | two sounds, like "no-ah" (a first quack then a lower second one; Rémi: "the transcription is hard, two sounds"); make several |
| **angry (programmatic)** | X | no RL: use the body-pose control (`robot.pose`: pitch is a bow, roll makes it fall, so pitch and height only) plus small head moves (yaw snaps, maybe a beak-up), aggressive but stable; this must open the beak so a held leash falls | angry quacks: hard, short, repeated (episode 2 anger candidates in `sounds/anger/` are a start; Rémi found stabs/gates too brutal for SAD, anger may take them) |
| **play dead** | free one | combination: a surprise quack, sit (`sit_toggle`), then a SOFT fall backwards: keep the head forward, straighten the legs softly, head rotated to the side, then the head straightens; end fully on the back with the head on the side; then the beak opens a little and a last "death" quack. Prototype in sim first; the robot will likely tip backwards on its own once the legs straighten while seated: find the gentlest way (a slow body-pitch ramp, or `robot.soften`-like gain reduction if the runtime exposes it; check what the sit policy does when legs are commanded). Getting up afterwards = Start / sitstand rise, piloted by Rémi | surprise quack (a bank alarm/inquire), silence, then the death quack: a long falling quack with a wobble that dies, beak barely open |
| **excited** | free one | body language: body-pose bounces (height / pitch pulses), beak up, head yaw left-right, lively; must stay stable | many happy quacks, rising, fast, repeated |
| **angry stomp (RL)** | later | retry the RL stomp with the small-stomp redesign (see `motion/anger-rl/REPORT.md`, r3 was in progress; `rl/` has the branch patch). Rémi will retry; not blocking the episode | barks on the foot contacts |

Also needed for the scene: **quack with the beak closed** (a leash is held): a sound-only
emotion variant where `mouth_at` stays 0 (curious/irritated quacks without opening the beak).

## Two-robot scripted scene (new tooling, the main technical novelty)

Rémi wants ONE script that plays on BOTH robots at the same time, because piloting the duck
while filming is painful and its walk is not repeatable. Constraints he stated:

- It works when the duck does not have to walk, or walks at a moment where its exact position
  does not matter (e.g. walking off at the end).
- The pad must stay alive during a scripted sequence: after a stand-up the duck's heading is
  random, so Rémi wants to rotate it with the stick while the script continues. So the script
  must not lock the sticks between its cues (only during an expression, as today), and it must
  tolerate Rémi's inputs.
- Design: extend the theater `scene.json` beats with duck cues: `{"duck": "curious"}` (an
  emotion), `{"duck_skill": "ground_pick"}`, `{"duck_sound": "..."}`, `{"duck_move": [vx,vy,wz],
  "for": 1.5}`; the player on the Mac sends them to the duck over ssh JSON-RPC
  (`agentic_robot_theater/microduck/tools/duck_rpc.py` drives robotd; emotions need a new RPC or
  an intent that padd exposes: check `robot.do` skills and whether an "expression" call exists;
  if not, add `robot.express {kind}` to robotd/padd on the film branch, minimal) while the Reachy
  Mini plays its beats as today. Timing: the duck's emotion durations are known (README table),
  so the beat can `hold` for them.
- Prototype the whole scene in simulation first: the encounter film's `duckfilm.py` drives a sim
  duck with the same intents and has a kinematic Reachy Mini puppet
  (`agentic_robot_theater/microduck/sim/`). Rémi's wife is building a simulator with both robots;
  when he shares it, switch to it. Until then, `duckfilm.py` + the Reachy puppet is the tool.

## The scene (Rémi's draft; refine the lines, keep the beats)

Landscape filming this time. Reachy Mini is polite, verbose, over-analytical; the duck answers
in quacks. Short exchanges, reacting to each other, not monologues.

1. Duck: excited quacks, then **picks up a leash** from the ground (`ground_pick`; set the leash
   so the grasp is repeatable: test positions on the robot with Rémi).
2. Reachy: "The lake, the lake. You are obsessed with the lake. But you are not a dog, you are a
   Microduck."
3. Duck: quacks **with the beak closed** (holding the leash).
4. Reachy: "The difference, the difference is your water resistance."
5. Duck: quack (closed beak).
6. Reachy, escalating: "And the sun. Do we even know what the sun does to us? Do we use sun
   cream? That is also a liquid. Will it get into our circuits?" (a few lines that rise in
   intensity; propose them)
7. Duck: **angry** (programmatic; the beak opens, the leash drops).
8. Reachy, searching for words, long pauses, then the worst it can say: "How dare you say that to
   my face. You are... you are a bad dog."
9. Duck: **play dead** (shock quack, falls over backwards, death quack).
10. Reachy loses it: "Microduck? Microduck, are you all right? No. Microduck, no. Did you die?
    Did I kill you with my extremely insensitive comment? Did it overwhelm your emotional
    circuitry?" then an overboard lament looking away: "Oh my dear friend, you were so young,
    you had so much to learn. What have I done. I still remember your first quacks..."
11. Duck stands up (sitstand rise; Rémi rotates it with the stick to face Reachy) and quacks.
    Reachy: "Yes. Like that. I still hear you in my mind." Duck: quack quack. Reachy turns:
    "Microduck! You are alive!" Duck: **excited**. Reachy: "I am so relieved to see you well and
    alive. I will never talk to you like that again. But please, please, be careful. The world is
    dangerous and you are fragile."
12. Duck immediately does the **wheee** (roller / the joy ride) or tries to walk, and very likely
    falls forward (may even lose its battery). Reachy, hesitant: "Did... did you die again?" End.

Ask Rémi: the exact free buttons for yes / no / play dead / excited; whether play dead may end
with the duck relaxed (torque off) or must stay powered; the leash object and where the pick
happens; whether the final fall is a real walk attempt or the wheee.

## Deliverables

- Each emotion: `motion/<emotion>/` (renderer, keyframes JSON with mouth, beats sheet), sounds in
  `sounds/<emotion>/`, a page in `combined/<emotion>/`, ship on the pad, Rémi's test.
- The two-robot player: theater repo (`robot/skit.py` + a duck bridge), documented in
  `agentic_robot_theater/README.md`, with a simulated preview of the scene.
- `scenes/episode3/` in the theater repo (scene.json, audio with the same voice
  `0m5sA4wKd4nKxBtRAu0n`, README with the beat table and the pan cues).
- `README.md` here: the emotion table extended, the three kinds of emotion explained.
