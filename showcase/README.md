# Showcase: the shipped emotions as clean, orbiting clips + a compilation for social media

Brief: `notes/SHOWCASE-BRIEF-2026-10-01.md` (Rémi, 2026-10-01). Outputs: `combined/showcase/` (page `index.html`,
`clips/<emotion>.mp4`, `posters/`, `microduck_emotions_compilation.mp4` 1080x1920 + `_720.mp4` for the page).
Published page: https://claude.ai/artifact/8f1DruNGYPgkEWzThm5zCk (private until Rémi shares it).

## How the clips are made

`orbit.py <emotion> <out_dir>` re-films one of the 14 shipped emotions (the list of the private dataset
`pollen-robotics/microduck-emotions`) with **its own renderer** (`motion/<x>/*.py`, `motion/sadness/v2.py`,
`motion/curious/curious.py`, `motion/playdead/playdead.py`), so the motion, the wav, the mouth envelope and the physics
are exactly the picked ones. Three patches are installed before the renderer runs:

1. `duckfilm.build_scene` -> `studio_build_scene`: same physics (floor geom, solref, solimp, timestep, the duck), only
   visuals change (slate background, haze at the horizon, a quieter floor without the grazing glare, a rim light).
   MuJoCo fog was tried and rejected: it washes the duck and paints the reflections.
2. `mujoco.Renderer` -> `OrbitRenderer`: frames at 1080x1920 (vertical) from a camera that circles slowly (10 deg/s,
   arc 22-75 deg) across the duck's front, following the trunk. Per-emotion overrides in `CAMS` (devastated and sad
   from the side to the front, play dead from the front to the side so it ends legs up in profile). `SHOWCASE_CAM`
   (json) forces an explicit path `{"start", "end", "orbit_s", "push"}`.
3. `ImageDraw.Draw` -> a no-op: no debug overlay.

All renderer outputs go to a scratch folder inside `out_dir`; the repo's `motion/` and `combined/` are never written.
Check: the measurements the renderers print match the originals (devastated yaw at extremes [0.19, -0.32, 0.19],
sad [0.28, -0.46], curious roll at tilts [0.425, -0.353]).

`render_all.sh OUT_DIR [emotion ...]` renders all 14, **3 at a time** (each MuJoCo process takes 2 to 2.6 GB; 8 at once
pushed the Mac into swap on 2026-10-01). About 45 s per batch of 3.

## The compilation

`compile.py OUT_DIR` renders the 14 again with a camera that continues across the cuts (each shot starts at the
azimuth where the previous one ended, swinging back and forth between 150 and 210 deg), trims, captions each shot
("k / 14" + the name, Avenir Next), freezes the last frame of play dead under a 2.6 s end card, normalises to -14 LUFS
(two-pass loudnorm, true peak -1 dB) and writes the 1080x1920 H.264 High / AAC 48 kHz file plus a 720x1280 copy.
`--no-render` reuses `OUT_DIR/raw`. Captions are drawn with PIL (this ffmpeg has no drawtext).

The order (`ORDER` in `compile.py`, 47.9 s):

| time | shot | trim | why |
|---|---|---|---|
| 0:00 | devastated | 0.1-7.0 s | the hook: shock call and collapse in the first second, three sobs; cut before it rises |
| 0:07 | curious, mmh | full | the snap: from tragedy to "what? what?" |
| 0:12 | yes, no, yes! | 1.25 / 1.6 / 1.25 s | quick-fire answers, the cutting speeds up |
| 0:16 | defiant, impatient, angry | full | irritation that climbs to barking |
| 0:23 | mock, laugh, excited | full | release: teasing, laughter, the highest energy |
| 0:32 | sad | 0-5.4 s | the come-down, a new angle; cut before it rises |
| 0:38 | play dead | full + 2.6 s end card | the punchline: legs up, the title card holds on it |

Not published anywhere. The socials session (`agentic-socials-ab`, repo `~/agentic_socials`) was given the file path to
propose it; nothing goes out without Rémi's go.
