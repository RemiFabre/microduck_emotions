"""The play-dead duck, v3 (Rémi's second feedback): the runtime's coming `robot.pose_joints {targets, off, gain, ramp_s}`
in simulation. From `pose_at` (motion clock), no policy runs: the joints listed in `off` get NO torque (their actuator
control is zeroed after BAM computes it: a servo with torque off, friction and damping stay), every other joint is
driven to `targets` (14 angles in duckfilm.JOINTS order, None = hold where it is) ramped from its current angle over
`ramp_s`, at gain `gain` (one kp for all, as robotd writes it). The jaw keeps following `mouth`. The duck then HOLDS
that pose (Rémi's Start = the full init is the way out, not part of the emotion)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "episode3"))
import lib  # noqa: E402
import duckfilm as F  # noqa: E402
from pdduck import PDDuck  # noqa: E402

JOINTS = list(F.JOINTS)
HEAD3 = ["neck_pitch", "head_pitch", "head_yaw"]
HEAD4 = HEAD3 + ["head_roll"]


class PDDuck3(PDDuck):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.pose_at = None            # motion time of the robot.pose_joints call
        self.targets = [0.0] * 14      # 14 angles or None (hold)
        self.off = HEAD3
        self.gain = F.KP_STAND
        self.ramp_s = 1.0
        self._pose_t0 = None
        self._pose_q0 = None
        self.posing = False
        self.stage2 = None             # (at, targets, ramp_s): a second robot.pose_joints (the legs come up once it lies there)
        self._stage2_done = False

    def set_pose_joints(self, at, targets, off, gain, ramp_s):
        self.pose_at, self.targets, self.off, self.gain, self.ramp_s = at, list(targets), list(off), gain, ramp_s

    def _off_ids(self):
        return [self.act_ids[JOINTS.index(n)] for n in self.off]

    def control_tick(self, t):
        tm = t - self.time_offset
        if self.stage2 is not None and not self._stage2_done and tm >= self.stage2[0]:
            self._stage2_done = True
            self.pose_at, self.targets, self.ramp_s = self.stage2[0], list(self.stage2[1]), self.stage2[2]
            self._pose_t0, self._pose_q0 = t, self.q().copy()
        if self.pose_at is not None and tm >= self.pose_at:
            if self._pose_t0 is None:
                self._pose_t0, self._pose_q0 = t, self.q().copy()
                self.skill, self.relax, self.soften = None, False, False
                self.limp_state, self.ramp = None, None
            self.t = t
            self.posing = True
            a = min(1.0, max(0.0, (t - self._pose_t0) / self.ramp_s)) if self.ramp_s > 0 else 1.0
            a = 0.5 - 0.5 * np.cos(np.pi * a)
            tgt = np.array([self._pose_q0[i] if v is None else v for i, v in enumerate(self.targets)])
            self.net, self.kp = "pose_joints", float(self.gain)
            self.bam.model.actuator.kp = self.kp
            self.bam.q_target[:] = self._pose_q0 + (tgt - self._pose_q0) * a
            self.jaw_open += 0.5 * (F.JAW_MAX * float(self.mouth) - self.jaw_open)
            return
        super().control_tick(t)

    def physics_substep(self):
        super().physics_substep()
        if self.posing and self.off:
            self.d.ctrl[self._off_ids()] = 0.0

    def leg_q(self):
        q = self.q()
        return {n: round(float(q[i]), 3) for i, n in enumerate(JOINTS) if "hip" in n or "knee" in n or "ankle" in n}
