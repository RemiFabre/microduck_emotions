# Play dead v3: why the browser simulator falls FORWARD and ours rolls BACKWARD (2026-09-06)

Facts (measured, not guessed):

| | our MuJoCo pipeline (`pdduck3.py`, BAM servos) | Laureen's browser sim (fork, `game.js`) |
|---|---|---|
| sit after the press | posture flag = 1 at once; trunk z 11.6 -> 7.0 cm at 1.0 s, **seated (6.2 cm) at 1.4 s** | `setMode("sit")` holds the stand under the sit-stand net for **0.8 s** before the flag; at 1.5 s the trunk is still at **11.4 cm (standing)**, pitch -9 deg |
| stage 1 at 1.4 s (head servos off, legs to zero over 1.5 s) | hits a SEATED duck with the head back (joint pitch -0.76, yaw +0.80): the straightening legs push the seat backwards, trunk pitch +36 deg at 2.0 s, **+90 deg (on the back) at 3.0 s** | hits a STANDING duck: hip pitch -0.46 -> 0 tips the trunk forward, pitch -48 deg at 2.0 s, **-97 deg (nose down) at 2.5 s**, ends propped at -113 deg |
| servos | BAM XL330 model, kp 160 (standing gain) | MuJoCo position actuators `chosen_actuator` kp 0.55 N.m/rad, forcerange +-0.96 N.m ("200 kp" calibration); torque off = gains scaled to 0 |
| model | mjlab `robot_allcollisions.xml` (2026-09 export): 70 collision geoms, neck/jaw contact exclude | an older export of the same file: **11 collision geoms** (no trunk_base / shell / xl330 / bearing collision meshes), no contact exclude; masses identical (trunk 0.199 kg, head 0.189 kg), joint ranges identical |
| head tracking while seated | yaw 0.84 / pitch -0.73 of 1.0 / -1.0 asked | not measured (the duck never sat before the cut) |
| policy during the dead pose | none (pose_joints holds) | none (`torque.state !== "on"` skips the policy) |

Ranked causes:
1. **The sit hand-over.** The browser sim delays the posture flag by 0.8 s (a hand-over the real runtime does not have: `robotd/src/control.rs` sets `Sit::Sitting` on the request), so the seat has not even started when stage 1 fires at 1.4 s, and straightening the legs from the standing pose topples the duck forward. This alone explains the direction. Our sim and the real robot land the seat by ~0.8-1.0 s (episode 2 measured the real sit at ~0.8 s), so stage 1 finds a seated duck and the roll goes backwards.
2. The missing collision meshes on the browser model (trunk, shells): they change how it rests once down (propped at -113 deg), not the direction.
3. The servo model (position actuators vs BAM): stiffer, no back-EMF/voltage sag; affects how hard the legs push, not the direction.

What the real robot will most likely do: roll BACKWARD like our pipeline, provided the seat has landed when the head servos cut and the legs straighten. Our pipeline is the closer one on the three points that decide it (sit timing = robotd's, BAM servos, measured head tracking). The risk on the robot is the same as in the browser: if the seat is late (a slow sit, a stumble), the straight legs tip it forward.

Recommendation for the emotion: make stage 1 conditional on the seat rather than on a clock. Cheapest: move `PD_DEAD1_AT` from 1.4 s to 1.8 s (0.4 s of margin over the measured 0.8-1.0 s seat; the head is fully back by 1.0 s so nothing else moves) and keep the 1.5 s leg ramp (slower = softer, 7.5 rad/s at 1.5 s vs 9.6 at 0.5 s). Better: in padd, fire stage 1 when the robot reports seated (the sit-stand state is in `robot.state`) or after 1.8 s, whichever comes first. For the browser sim: send the sit flag at once for play dead (skip the 0.8 s hand-over), or gate stage 1 on trunk z < 7 cm.
