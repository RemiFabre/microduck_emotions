#!/usr/bin/env python
"""Showcase renders: each shipped emotion re-filmed by its OWN renderer (same motion, same wav, same physics), with
three patches installed before the renderer runs:

1. a studio look: duckfilm.build_scene rebuilt with the same physics (same floor geom, solref, solimp, timestep) and
   only visual changes (slate background, a quieter floor without the grazing glare, a rim light);
2. an orbit camera: mujoco.Renderer is wrapped so every frame the renderer asks for is drawn at SIZE from a camera that
   circles the duck slowly (constant speed, an arc centred on the duck's three-quarter front) and follows the trunk;
3. no debug overlay: the renderers' text / meters are drawn through a no-op ImageDraw.

    /Users/remi/microduck/.venv-mjlab/bin/python orbit.py <emotion> <out_dir>

writes <out_dir>/<emotion>.mp4 (with sound, muxed by the renderer's own combine.py call). The repo's motion and
combined folders are never written: every output path of the renderers is redirected to a scratch folder.
"""
import json, math, os, shutil, sys, tempfile
from pathlib import Path

import mujoco, numpy as np
from PIL import ImageDraw

ROOT = Path("/Users/remi/microduck/notes/emotions")
MOTION = ROOT / "motion"
sys.path.insert(0, str(MOTION / "episode3"))
sys.path.insert(0, "/Users/remi/microduck/notes/reachy-encounter")
import duckfilm as F  # noqa: E402

SIZE = tuple(int(v) for v in os.environ.get("SHOWCASE_SIZE", "1080x1920").split("x"))   # (width, height)
FPS = 30

# The 14 shipped emotions (the private dataset pollen-robotics/microduck-emotions): which renderer, which pick.
# The camera: CAM below, overridden per emotion by CAMS.
EMOTIONS = {
    "devastated": dict(kind="v2", version="v2", motion="devastated_3x1.0", sound="D3v2_sobs_gentler"),
    "sad": dict(kind="v2", version="v7", motion="sad_v7_halfdown", sound="S6_coo_voice_200_140"),
    "curious": dict(kind="curious", motion="curious_two_tilts_r35_leftboost", sound="Q3_up2", spec="spec_v3.json"),
    "mmh": dict(kind="lib", module="mmh/render_mmh.py", attr="MOTION", src="motion/mmh/mmh__C3_mmh.json"),
    "yes": dict(kind="lib", module="yes/yes.py", attr="MOTIONS", src="motion/yes/yes_single__Y2_synth_fall.json"),
    "yes_fast": dict(kind="lib", module="yes/yes.py", attr="MOTIONS", src="motion/yes/yes_single__Y3_synth_wak.json"),
    "no": dict(kind="lib", module="no/no.py", attr="MOTIONS", src="motion/no/no_one__N2_synth_m5.json"),
    "angry": dict(kind="lib", module="angry/angry.py", attr="MOTIONS", src="motion/angry/bow_snaps__S1_hard_barks.json"),
    "excited": dict(kind="lib", module="excited/excited.py", attr="MOTIONS",
                    src="motion/excited/excited_wag_pump__X1_synth_rise_climb.json"),
    "laugh": dict(kind="lib", module="laugh/laugh_v2.py", attr="LAUGH2", src="motion/laugh/laugh_wag_v2__L4_dying.json"),
    "mock": dict(kind="lib", module="laugh/laugh_v2.py", attr="MOCK", src="motion/laugh/mock__L1_synth_haha.json"),
    "defiant": dict(kind="lib", module="defiant/render_defiant.py", attr="M", src="motion/defiant/defiant__D1_two_waks.json"),
    "impatient": dict(kind="lib", module="impatient/render_impatient.py", attr="M",
                      src="motion/impatient/impatient__I1_grumbles_huff.json"),
    "play_dead": dict(kind="playdead"),
}

# lookat height (m), distance (m), elevation (deg), centre azimuth (deg; 180 = in front of the duck, which faces +x;
# 115 = the side view the sad renders used). The arc swept over a clip grows with its length: SPEED deg/s, clamped.
CAM = dict(z=0.14, dist=0.68, elev=-10, centre=180, dir=1)
SPEED, ARC_MIN, ARC_MAX = 10.0, 22.0, 75.0
CAMS = {
    "devastated": dict(z=0.11, dist=0.66, elev=-12, centre=140),     # from the side (the droop reads) to the face
    "sad": dict(centre=140),
    "play_dead": dict(z=0.09, dist=0.82, elev=-16, centre=125, dir=-1),   # front 3/4 to the side: it ends legs up in profile
}


def cam_for(emotion, total):
    """The camera of a clip. SHOWCASE_CAM (json) overrides it, e.g. {"start": 180, "end": 210, "orbit_s": 3.0, "push": 0}
    for the compilation, where each clip starts at the azimuth the previous one ended on."""
    c = dict(CAM, push=0.06, **CAMS.get(emotion, {}))
    c["arc"] = min(ARC_MAX, max(ARC_MIN, SPEED * total))
    c.update(json.loads(os.environ.get("SHOWCASE_CAM", "{}")))
    return c


# ---------------------------------------------------------------------------------------------------------------
# 1. studio look (visual only; the physics part is a copy of duckfilm.build_scene)
# ---------------------------------------------------------------------------------------------------------------
BG_TOP = [0.10, 0.13, 0.19]
BG_HORIZON = [0.24, 0.30, 0.38]
FLOOR_A = [0.30, 0.36, 0.44]
FLOOR_B = [0.26, 0.32, 0.40]


def studio_build_scene(size=(1280, 720), reachy_at=(0.0, 0.0, 0.0), reachy_mobile=True):
    spec = mujoco.MjSpec()
    spec.compiler.degree = False
    spec.visual.global_.offwidth, spec.visual.global_.offheight = max(size[0], SIZE[0]), max(size[1], SIZE[1])
    spec.visual.headlight.diffuse, spec.visual.headlight.ambient = [0.42, 0.42, 0.42], [0.33, 0.33, 0.35]
    spec.visual.headlight.specular = [0.0, 0.0, 0.0]
    spec.visual.quality.shadowsize = 8192
    spec.visual.quality.offsamples = 8
    spec.visual.map.shadowclip = 1.0
    spec.visual.map.haze = 0.6                                            # the horizon melts into the background
    spec.visual.rgba.haze = BG_HORIZON + [1.0]
    spec.add_texture(name="sky", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                     rgb1=BG_TOP, rgb2=BG_HORIZON, width=512, height=3072)
    spec.worldbody.add_light(name="sun", pos=[0.5, -1.0, 3.5], dir=[-0.15, 0.3, -1],
                             type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL, castshadow=True)
    spec.worldbody.add_light(name="rim", pos=[-1.5, 0.6, 1.2], dir=[1.0, -0.3, -0.5], diffuse=[0.35, 0.38, 0.45],
                             specular=[0.15, 0.15, 0.15], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL, castshadow=False)
    spec.add_texture(name="groundplane", type=mujoco.mjtTexture.mjTEXTURE_2D, builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                     rgb1=FLOOR_A, rgb2=FLOOR_B, mark=mujoco.mjtMark.mjMARK_EDGE, markrgb=[0.38, 0.44, 0.52],
                     width=300, height=300)
    spec.add_material(name="groundplane", texrepeat=[5, 5], texuniform=True, reflectance=0.06,
                      specular=0.12, shininess=0.3).textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "groundplane"
    spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05], material="groundplane",
                            solref=[0.04, 1.0], solimp=[0.85, 0.95, 0.001, 0.5, 2.0])
    F.add_duck(spec, "duck_")
    if reachy_at is not None:
        F.add_reachy(spec, *reachy_at, mobile=reachy_mobile)
    m = spec.compile()
    m.opt.timestep = F.DT
    m.stat.center = np.array([0.0, 0.0, 0.15])
    m.stat.extent = 2.5
    return m, mujoco.MjData(m)


# ---------------------------------------------------------------------------------------------------------------
# 2. orbit camera, 3. no overlay
# ---------------------------------------------------------------------------------------------------------------
_RealRenderer = mujoco.Renderer
CUR = None              # this emotion's camera (cam_for)
TOTAL = None            # clip length (s), for the arc


class OrbitRenderer:
    """Stands in for mujoco.Renderer(m, h, w): ignores the size and the camera it is given; frame i of n is drawn at
    SIZE from an orbit at azimuth centre + dir * arc * (i / n - 0.5), looking at the trunk (smoothed, fixed height)."""

    def __init__(self, m, height=None, width=None):
        self.m = m
        self.r = _RealRenderer(m, SIZE[1], SIZE[0])
        self.trunk = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "duck_trunk_base")
        self.i = 0
        self.look = None

    def update_scene(self, d, camera=None, scene_option=None):
        c = CUR
        n = max(1, int(round(TOTAL * FPS)) - 1)
        p = np.array(d.xpos[self.trunk], float)
        tgt = np.array([p[0], p[1], c["z"]])
        if self.look is None:
            self.look = tgt
        else:
            k = 1 - math.exp(-(1.0 / FPS) / 0.6)
            self.look = self.look + (tgt - self.look) * k
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = self.look
        u = min(1.0, self.i / n)
        if "start" in c:                                          # an explicit path: start -> end over orbit_s, then hold
            v = min(1.0, self.i / max(1.0, c.get("orbit_s", TOTAL) * FPS))
            cam.azimuth = c["start"] + (c["end"] - c["start"]) * v
        else:
            cam.azimuth = c["centre"] + c["dir"] * c["arc"] * (u - 0.5)
        cam.elevation = c["elev"]
        cam.distance = c["dist"] * (1.0 - c["push"] * u)          # a slow push-in (6 % over the clip by default)
        self.i += 1
        self.r.update_scene(d, camera=cam)

    def render(self):
        return self.r.render()

    def close(self):
        self.r.close()


class _NoDraw:
    def __getattr__(self, name):
        return lambda *a, **k: None


def install(emotion, total):
    global CUR, TOTAL
    CUR, TOTAL = cam_for(emotion, total), total
    F.build_scene = studio_build_scene
    mujoco.Renderer = OrbitRenderer
    ImageDraw.Draw = lambda *a, **k: _NoDraw()


# ---------------------------------------------------------------------------------------------------------------
def load(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def render(emotion, out_dir):
    e = EMOTIONS[emotion]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=f"showcase_{emotion}_", dir=out_dir))
    kind = e["kind"]
    if kind == "lib":
        src = json.load(open(ROOT / e["src"]))["measured"]
        mod_path = MOTION / e["module"]
        sys.path.insert(0, str(mod_path.parent))
        import lib
        lib.beats_sheet = lambda *a, **k: None
        mod = load(mod_path, "emo_" + emotion)
        obj = getattr(mod, e["attr"])
        motion = obj[src["motion"]] if isinstance(obj, dict) else obj
        assert motion.name == src["motion"], (motion.name, src["motion"])
        install(emotion, motion.total)
        wav = Path(src["wav"]) if Path(src["wav"]).is_absolute() else ROOT / src["wav"]
        lib.render(motion, wav, scratch / "motion", scratch / "page", sound=src["sound"],
                   sound_desc=src.get("sound_desc", ""), mouth_mode=src.get("mouth_mode", "wav"), quiet=True)
        made = scratch / "page" / f"{motion.name}__{src['sound']}.mp4"
    elif kind == "playdead":
        sys.argv = [sys.argv[0]]
        import lib
        lib.beats_sheet = lambda *a, **k: None
        sys.path.insert(0, str(MOTION / "playdead"))
        pd = load(MOTION / "playdead" / "playdead.py", "emo_playdead")
        motion, wav, sound = pd.pick()
        pd.CURRENT_V3 = pd.SPEC["motions"][pd.PICK[0]]
        pd.CURRENT_INIT_AT = None
        assert pd.CURRENT_V3["recipe"] == "v3"
        install(emotion, motion.total)
        lib.render(motion, wav, scratch / "motion", scratch / "page", sound=sound, quiet=True)
        made = scratch / "page" / f"{motion.name}__{sound}.mp4"
    elif kind == "v2":
        sys.argv = [sys.argv[0], "--version", e["version"]]
        sys.path.insert(0, str(MOTION / "sadness"))
        v2 = load(MOTION / "sadness" / "v2.py", "emo_v2")
        v2.OUT_MOTION, v2.OUT_COMBINED = scratch / "motion", scratch / "page"
        v2.beats_sheet = lambda *a, **k: None
        r = next(r for r in v2.SPEC["renders"] if r["motion"] == e["motion"] and r["sound"] == e["sound"])
        b = v2.SPEC["motions"][e["motion"]]
        total = b["total"] if v2.LATER else None
        if total is None:
            env = v2.mouth_envelope(Path(r["wav"]))
            total = max(b["total"], len(env) * F.CDT)
        install(emotion, total)
        v2.render_pair(r["motion"], r["sound"], Path(r["wav"]), r["desc"])
        made = scratch / "page" / f"{e['motion']}__{e['sound']}.mp4"
    elif kind == "curious":
        sys.argv = [sys.argv[0], "--spec", e["spec"]]
        sys.path.insert(0, str(MOTION / "curious"))
        cu = load(MOTION / "curious" / "curious.py", "emo_curious")
        cu.HERE, cu.OUT_COMBINED = scratch, scratch / "page"
        cu.beats_sheet = lambda *a, **k: None
        r = next(r for r in cu.SPEC["renders"] if r["motion"] == e["motion"] and r["sound"] == e["sound"])
        install(emotion, cu.SPEC["motions"][e["motion"]]["total"])
        cu.render_pair(r["motion"], r["sound"], Path(r["wav"]), r["desc"])
        made = scratch / "page" / f"{e['motion']}__{e['sound']}.mp4"
    else:
        raise ValueError(kind)
    final = out_dir / f"{emotion}.mp4"
    shutil.move(str(made), final)
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"{emotion}: {final}")
    return final


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
