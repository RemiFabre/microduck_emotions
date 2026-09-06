"""Shared driver for the yes / no / closed pages: render every (motion, sound) pair of a spec.json, write the page
with the pick first, expose pick(). Used by motion/yes/yes.py, motion/no/no.py, motion/closed/closed.py."""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOT = lib.ROOT


def run(emotion, motions, header, intro, pick_stem, pick_note, mouth_mode="wav", sections_by_motion=True):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    out = ROOT / "motion" / emotion
    page = ROOT / "combined" / emotion
    spec = json.load(open(out / "spec.json"))
    if not a.no_render:
        for r in spec["renders"]:
            stem = f"{r['motion']}__{r['sound']}"
            if a.only and a.only not in stem:
                continue
            lib.render(motions[r["motion"]], Path(r["wav"]), out, page, sound=r["sound"], sound_desc=r["desc"], mouth_mode=mouth_mode)
    # page: pick first, then one section per motion
    cards = {}
    for r in spec["renders"]:
        stem = f"{r['motion']}__{r['sound']}"
        cards[stem] = (r, lib.card(out, page, stem, f"{r['motion']} + {r['sound']}"))
    sections = []
    if pick_stem in cards:
        html = cards[pick_stem][1].replace('<div class="card">', '<div class="card pick">', 1)
        sections.append(("Recommended pick", pick_note, [html]))
    for mname, m in motions.items():
        cs = [c for stem, (r, c) in cards.items() if r["motion"] == mname and c]
        if cs:
            sections.append((mname, m.desc, cs))
    lib.write_page(page, header, intro, sections, open_it=not a.no_open)
    return out, page
