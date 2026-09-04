"""Sounds designed ON the decided sad motions, beat by beat (Rémi, 2026-09-04 afternoon):
smooth glides only (no brutal transitions), a short shock from the existing bank at the sit, silence
while sitting down, then a lament whose slides follow the head swings one to one, dying in the hold.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced.py [--no-open]

Writes full-length wavs to sounds/synced/, muxes each into the motion video under combined/synced/, and
builds combined/synced/index.html. Materials = the three Rémi liked: the smooth sad2 glide (quack synth),
the coo slide and the reversed-inquire sigh (bank tape tricks).
"""
import html
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from quack import ROBOT_SEED, SR, Personality, bell, normalise, quack, read_wav, t_axis, write_wav  # noqa: E402

BANK = Path("/Users/remi/microduck/notes/reachy-encounter/voices/seed_4145077059")
OUT_WAV = HERE / "synced"
OUT_MP4 = ROOT / "combined" / "synced"
p = Personality(ROBOT_SEED)
# The lament voice: soft, breathy, slow vibrato, no attack snap, less buzz (the sad2 v5 recipe family)
SAD = dict(quackiness=0.45, breath=0.14, vibrato_rate_hz=3.8, vibrato_depth=0.5, attack_sharpness=0.0, tilt=2.1, am_depth=0.2)
ST = 2 ** (1 / 12)


def semis(hz, n):
    return hz * ST ** n


def bank(tag, letter):
    return read_wav(BANK / tag / f"{tag}_{letter}.wav")[1]


def varispeed(x, rate_points):
    n = len(x)
    u = np.arange(n) / max(n - 1, 1)
    rate = np.interp(u, [q[0] for q in rate_points], [q[1] for q in rate_points])
    t_out = np.cumsum(1.0 / rate)
    t_out -= t_out[0]
    out_idx = np.arange(0, t_out[-1])
    return np.interp(np.interp(out_idx, t_out, np.arange(n)), np.arange(n), x)


def fade(x, a=0.03, r=0.12):
    x = x.copy()
    na, nr = int(a * SR), int(r * SR)
    x[:na] *= np.linspace(0, 1, na)
    x[-nr:] *= np.linspace(1, 0, nr)
    return x


def db(x, d):
    return x * 10 ** (d / 20)


class Track:
    def __init__(self, total_s):
        self.buf = np.zeros(int(total_s * SR) + SR)

    def put(self, t, sig):
        i = int(t * SR)
        n = min(len(sig), len(self.buf) - i)
        self.buf[i:i + n] += sig[:n]

    def done(self, path):
        return write_wav(path, self.buf, -3.0)


# ----------------------------------------------------------------------------- lament builders
# All take the beat list `ex` (times of the head-yaw extremes, 1 s apart) and `hold_end` (when the
# sound must have died), plus a start frequency. Each swing = extreme i -> extreme i+1.

def lament_continuous(ex, hold_end, f_hi=260.0, drop_semis=4.0, step_semis=1.5, lead=None):
    """ONE unbroken tone: during each swing the pitch slides down `drop_semis`, then over the last 0.15 s
    of the swing it eases back up to the next (slightly lower) start. No gap, no attack: the smoothest
    version. `lead` = (t_start, f_start): an optional slide into the first extreme (the droop)."""
    pts = []
    t0 = ex[0]
    if lead:
        pts.append((lead[0], lead[1]))
    for i, te in enumerate(ex):
        hi = semis(f_hi, -step_semis * i)
        lo = semis(hi, -drop_semis)
        t_next = ex[i + 1] if i + 1 < len(ex) else hold_end
        pts.append((te, hi))
        if i + 1 < len(ex):
            pts.append((t_next - 0.15, lo))
        else:
            pts.append((hold_end, semis(lo, -3)))
    start = pts[0][0]
    dur = hold_end - start
    t = t_axis(dur)
    freq = np.interp(t + start, [q[0] for q in pts], [q[1] for q in pts])
    # loudness: swells in, breathes a little with each swing, dies over the last swing/hold
    env = bell(t, 0.35, hold_end - ex[-1])
    swing = 1.0 - 0.25 * (0.5 + 0.5 * np.cos(2 * np.pi * (t + start - ex[0]) / 1.0)) ** 2
    env = env * np.where(t + start > ex[0], swing, 1.0)
    return start, quack(p, dur, freq, env, mods=SAD)


def lament_sobs(ex, hold_end, f_hi=260.0, drop_semis=4.0, step_semis=1.5, attack=0.18):
    """One separate glide per swing, each with a soft 0.18 s swell so nothing clicks, each lower and
    quieter; the last one fades through the hold."""
    parts = []
    for i, te in enumerate(ex):
        hi = semis(f_hi, -step_semis * i)
        lo = semis(hi, -drop_semis)
        last = i + 1 == len(ex)
        dur = (hold_end - te) if last else 0.95
        sig = quack(p, dur, [(0.0, hi), (dur, lo if not last else semis(lo, -3))],
                    ("bell", attack, dur * (0.55 if last else 0.4)), mods=SAD)
        parts.append((te, db(normalise(sig, -3.0), -1.5 * i)))
    return parts


def lament_coo(ex, hold_end, base_rate=1.6, step=0.94):
    """Bank material: coo_a on a falling tape, one per swing (the C_coo_slide recipe, shortened)."""
    coo = bank("coo", "a")
    parts = []
    for i, te in enumerate(ex):
        r = base_rate * step ** i
        last = i + 1 == len(ex)
        sig = varispeed(coo, [(0.0, r * 1.15), (0.45, r), (1.0, r * (0.55 if last else 0.72))])
        sig = fade(sig, 0.06, 0.25 if last else 0.12)
        parts.append((te, db(normalise(sig, -3.0), -1.5 * i)))
    return parts


def lament_inquire(ex, hold_end, base_rate=0.7, step=0.94):
    """Bank material: inquire (a rising question) reversed = a falling sigh, one per swing (C_inquire_sigh)."""
    letters = ["a", "d", "a", "d"]
    parts = []
    for i, te in enumerate(ex):
        q = bank("inquire", letters[i % 4])[::-1]
        r = base_rate * step ** i
        last = i + 1 == len(ex)
        sig = varispeed(q, [(0.0, r), (1.0, r * (0.6 if last else 0.78))])
        sig = fade(sig, 0.05, 0.3 if last else 0.12)
        parts.append((te, db(normalise(sig, -3.0), -1.5 * i)))
    return parts


def lament_wave(ex, hold_end, f_center=210.0, depth_semis=3.0, fall_semis=6.0):
    """The purest 'oscillates with the head': one tone whose pitch is the head yaw itself (a cosine with
    the extremes at the beat times, +-3 semitones) riding a line that falls 6 semitones over the shakes."""
    start = ex[0] - 0.5
    dur = hold_end - start
    t = t_axis(dur)
    tt = t + start
    line = semis(f_center, -fall_semis * np.clip((tt - ex[0]) / (ex[-1] - ex[0]), 0, 1))
    yaw = np.cos(np.pi * (tt - ex[0]))  # +1 at extreme 0, -1 at extreme 1, ...
    freq = line * ST ** (depth_semis * yaw)
    env = bell(t, 0.5, hold_end - ex[-1])
    return start, quack(p, dur, freq, env, mods=dict(SAD, vibrato_depth=0.25))


# ----------------------------------------------------------------------------- shocks (bank, untouched)
SHOCKS = {
    "alarm": ("alarm", "a", "alarm_a: the sharp honk"),
    "inquire": ("inquire", "b", "inquire_b: a rising 'huh?'"),
    "chirp": ("chirp", "a", "chirp_a: a short rising blip"),
    "greet": ("greet", "c", "greet_c: a plain quack"),
}


def shock(name):
    tag, letter, _ = SHOCKS[name]
    return normalise(bank(tag, letter), -3.0)


# ----------------------------------------------------------------------------- options
def build(motion, beats, total):
    ex = beats["shake_extremes"]
    hold_end = beats["rise_start"] - 0.2
    droop = beats["droop_start"]
    opts = []

    def add(name, desc, place):
        tr = Track(total)
        place(tr)
        opts.append((name, desc, tr))

    if motion == "devastated":
        t_sit = beats["sit"]
        # D1 shock + one unbroken lament from the first extreme
        add("D1_alarm_continuous", "alarm shock at the sit; silence; ONE unbroken lament from the first head extreme: each swing is a 4-semitone slide down, eased into the next; dies in the hold",
            lambda tr: (tr.put(t_sit, shock("alarm")), tr.put(*lament_continuous(ex, hold_end))))
        # D2 shock + long droop glide flowing into the swings (one tone from the droop to the hold)
        add("D2_alarm_droop_glide_continuous", "alarm shock; the lament starts as the head starts to droop (a 1.5 s slide 300 -> 260 Hz) and flows without a break into one slide per swing",
            lambda tr: (tr.put(t_sit, shock("alarm")), tr.put(*lament_continuous(ex, hold_end, f_hi=250.0, lead=(droop, 320.0)))))
        # D3 inquire shock + separate sobs
        add("D3_inquire_sobs", "'huh?' shock (inquire) at the sit; then one separate soft glide per swing (0.18 s swell, no click), each lower and quieter",
            lambda tr: (tr.put(t_sit, shock("inquire")), [tr.put(t, s) for t, s in lament_sobs(ex, hold_end)]))
        # D4 alarm + coo material
        add("D4_alarm_coo_slides", "alarm shock; lament from the robot's own coo on a falling tape, one coo per swing (C_coo_slide material)",
            lambda tr: (tr.put(t_sit, shock("alarm")), [tr.put(t, s) for t, s in lament_coo(ex, hold_end)]))
        # D5 alarm + inquire sigh material
        add("D5_alarm_inquire_sighs", "alarm shock; lament from reversed inquire quacks (falling sighs), one per swing (C_inquire_sigh material)",
            lambda tr: (tr.put(t_sit, shock("alarm")), [tr.put(t, s) for t, s in lament_inquire(ex, hold_end)]))
        # D6 chirp shock + wave
        add("D6_chirp_wave", "short chirp shock; one tone whose pitch IS the head yaw (+-3 semitones, extremes on the beats) on a line falling 6 semitones; the most literal sync",
            lambda tr: (tr.put(t_sit, shock("chirp")), tr.put(*lament_wave(ex, hold_end))))
        # D7 greet shock + continuous, lower and slower drop
        add("D7_greet_continuous_low", "plain quack as the shock; unbroken lament starting lower (220 Hz) with 5-semitone slides: heavier",
            lambda tr: (tr.put(t_sit, shock("greet")), tr.put(*lament_continuous(ex, hold_end, f_hi=220.0, drop_semis=5.0))))
        # D8 no shock: silence then the lament only
        add("D8_noshock_continuous", "no shock at all (the sit is silent); the unbroken lament alone, for comparison",
            lambda tr: tr.put(*lament_continuous(ex, hold_end)))
    else:
        # sad: no shock. Droop glide then the swings.
        add("S1_droop_glide_continuous", "a soft 2 s slide (300 -> 250 Hz) while the head goes down, flowing into one unbroken slide per swing, dying in the hold",
            lambda tr: tr.put(*lament_continuous(ex, hold_end, f_hi=245.0, lead=(droop + 0.2, 300.0))))
        add("S2_sobs", "silence during the droop; one separate soft glide per swing, each lower and quieter",
            lambda tr: [tr.put(t, s) for t, s in lament_sobs(ex, hold_end)])
        add("S3_coo_slides", "silence during the droop; the robot's own coo on a falling tape, one per swing",
            lambda tr: [tr.put(t, s) for t, s in lament_coo(ex, hold_end)])
        add("S4_inquire_sighs", "silence during the droop; reversed inquire sighs, one per swing",
            lambda tr: [tr.put(t, s) for t, s in lament_inquire(ex, hold_end)])
        add("S5_wave", "one tone whose pitch is the head yaw on a falling line, from just before the first extreme",
            lambda tr: tr.put(*lament_wave(ex, hold_end)))
        add("S6_sigh_then_continuous", "a breathy sad2-style glide (330 -> 165 Hz, 1.2 s) as the head droops, a short breath, then the unbroken per-swing lament",
            lambda tr: (tr.put(droop + 0.3, normalise(quack(p, 1.2, [(0, 330), (0.4, 260), (1.2, 165)], ("bell", 0.15, 0.5), mods=SAD), -6.0)),
                        tr.put(*lament_continuous(ex, hold_end, f_hi=235.0))))
    return opts


def main():
    open_page = "--no-open" not in sys.argv
    OUT_WAV.mkdir(parents=True, exist_ok=True)
    OUT_MP4.mkdir(parents=True, exist_ok=True)
    manifest = []
    sections = []
    for motion in ("devastated", "sad"):
        beats = json.load(open(ROOT / "motion" / "sadness" / f"{motion}.json"))["beats"]
        total = beats["total"]
        rows = []
        for name, desc, tr in build(motion, beats, total):
            wav = tr.done(OUT_WAV / f"{motion}__{name}.wav")
            mp4 = OUT_MP4 / f"{motion}__{name}.mp4"
            subprocess.run([sys.executable, str(ROOT / "combine.py"), str(ROOT / "motion" / "sadness" / f"{motion}.mp4"),
                            str(wav), str(mp4), "--at", "0"], check=True, capture_output=True)
            manifest.append({"motion": motion, "name": name, "wav": str(wav), "mp4": str(mp4), "desc": desc})
            rows.append(f'<div class="card"><video controls preload="metadata" src="{mp4.name}" width="480"></video>'
                        f'<div><code>{html.escape(name)}</code><br>{html.escape(desc)}<br>'
                        f'<audio controls preload="none" src="../../sounds/synced/{wav.name}"></audio></div></div>')
            print(f"{motion} {name}")
        b = beats
        info = (f"sit {b['sit']} s, " if b.get("sit") else "") + f"droop {b['droop_start']}-{b['droop_end']} s, head extremes at {', '.join(str(x) for x in b['shake_extremes'])} s, hold until {b['rise_start']} s, head level at {b['head_level']} s"
        sections.append(f"<h2>{motion}</h2><p>Beats: {html.escape(info)}. Every lament slide starts on a head extreme and lasts one swing (1 s); the last one dies during the hold.</p>{''.join(rows)}")
    json.dump(manifest, open(OUT_WAV / "manifest.json", "w"), indent=1)
    page = f"""<!doctype html><meta charset="utf-8"><title>Sad sounds designed on the motions</title>
<style>body{{font:15px/1.4 -apple-system,Helvetica,sans-serif;margin:24px}}.card{{display:inline-block;vertical-align:top;width:490px;margin:0 16px 24px 0}}code{{font-size:12px}}p{{max-width:1000px}}audio{{width:300px;margin-top:4px}}</style>
<h1>Sad sounds designed on the decided motions (simulation)</h1>
<p>Rémi's brief: smooth glides only; for devastated a short shock from the existing bank at the sit, silence while sitting, then a lament that oscillates with the head, one slide per head swing. Materials: the sad2-style glide (synth), the coo slide and the reversed-inquire sigh (bank). Files: <code>/Users/remi/microduck/notes/emotions/sounds/synced/</code> (wav) and <code>/Users/remi/microduck/notes/emotions/combined/synced/</code> (mp4). Regenerate: <code>/Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_synced.py</code></p>
{''.join(sections)}"""
    (OUT_MP4 / "index.html").write_text(page)
    print(OUT_MP4 / "index.html")
    if open_page:
        subprocess.run(["open", str(OUT_MP4 / "index.html")])


if __name__ == "__main__":
    main()
