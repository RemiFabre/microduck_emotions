"""The play-dead duck: lib.Duck3 plus `robot.relax` (torque off at once), then `robot.init` (torque on + a 2 s ramp
from wherever the joints are to the home pose) at `init_at`, after which the duck HOLDS the home pose at the standing
gain (no policy: on the real robot the policy is not driving after an init until Start is pressed again).
Also measures the closest approach between the head shell and the trunk (the shoulder collision Rémi fears)."""
import sys
from pathlib import Path

import mujoco, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "episode3"))
import lib  # noqa: E402
import duckfilm as F  # noqa: E402

INIT_RAMP = 2.0


class PDDuck(lib.Duck3):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.init_at = None                 # motion time (the renderer's clock: sim time minus PREROLL)
        self.time_offset = lib.PREROLL
        self._init_done = False
        self.holding = False
        m = self.m
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(m.nbody)]
        coll = lambda i: (m.geom_contype[i] | m.geom_conaffinity[i]) != 0
        self.head_geoms = [i for i in range(m.ngeom) if names[m.geom_bodyid[i]] == self.prefix + "jaw_soft" and coll(i)]
        self.trunk_geoms = [i for i in range(m.ngeom) if names[m.geom_bodyid[i]] == self.prefix + "trunk_base" and coll(i)]
        self.pairs = None

    def head_trunk_gap(self):
        """Closest distance (m) between a head collision geom and a trunk collision geom, over the pairs that are at
        least 5 mm apart at the home pose (some meshes overlap by construction near the neck root); 0 = touching."""
        ft = np.zeros(6)
        if self.pairs is None:
            self.pairs = [(g1, g2) for g1 in self.head_geoms for g2 in self.trunk_geoms
                          if mujoco.mj_geomDistance(self.m, self.d, g1, g2, 0.3, ft) > 0.005]
        # mesh-mesh distance is flaky (it returns 0 now and then for well-separated meshes), so a zero only counts
        # when the contact list confirms the touch
        best = 1.0
        for g1, g2 in self.pairs:
            dd = mujoco.mj_geomDistance(self.m, self.d, g1, g2, 0.3, ft)
            if 1e-6 < dd < best:
                best = dd
        return 0.0 if self.head_trunk_touching() else best

    def head_trunk_touching(self):
        d = self.d
        hs, ts = set(self.head_geoms), set(self.trunk_geoms)
        for i in range(d.ncon):
            c = d.contact[i]
            if (c.geom1 in hs and c.geom2 in ts) or (c.geom2 in hs and c.geom1 in ts):
                return True
        return False

    def control_tick(self, t):
        if self._init_done:
            self.relax = False              # the renderer only ever sets relax; after the init it is over
        if self.init_at is not None and not self._init_done and t - self.time_offset >= self.init_at:
            self._init_done = True
            self.relax = False
            self.soften, self._soften_t0 = False, None
            self.limp_state = None
            self.ramp = (t, INIT_RAMP, self.q())
        if self._init_done and self.ramp is None:
            # the ramp is over: hold home at the standing gain, no policy
            self.t = t
            self.holding = True
            self.net, self.kp = "hold", F.KP_STAND
            self.bam.model.actuator.kp = self.kp
            self.bam.q_target[:] = F.HOME
            self.jaw_open += 0.5 * (F.JAW_MAX * float(self.mouth) - self.jaw_open)
            return
        if self._init_done and self.ramp is not None:
            self.net = "init"
        super().control_tick(t)
