"""Build the audition page /Users/remi/microduck/notes/emotions/sounds/index.html from manifest_*.json.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_index.py

One row per candidate: play button, name, strategy, description, duration. References on top.
"""
import html
import json
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE.parent / "reference"
STRATEGY = {"L": "L: long / layered versions of the best sad bets, sized for the 9 s motion", "A": "A: port of the Reachy Mini sound", "B": "B: programmatic (music theory)", "C": "C: grains from the real bank"}
REF_DESC = {
    "sad2": "Reachy Mini sadness reference (flute). One ~1 s descending call inside 5.7 s.",
    "irritated2": "Reachy Mini anger reference 1: 1.6 s growl, 420-520 Hz, scandalised.",
    "frustrated1": "Reachy Mini anger reference 2: 2 s slowly falling tone, cannot-do-it.",
    "reprimand3": "Reachy Mini anger reference 3: a run of short tsk-tsk notes, funny scolding.",
}


def duration(path):
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return 0.0


def rows(entries):
    out = []
    for e in entries:
        p = Path(e["file"])
        rel = p.relative_to(HERE) if p.is_relative_to(HERE) else p
        out.append(
            f'<tr><td><audio controls preload="none" src="{html.escape(str(rel))}"></audio></td>'
            f'<td><code>{html.escape(p.name)}</code></td><td>{html.escape(e.get("strategy", ""))}</td>'
            f'<td>{html.escape(e.get("desc", ""))}</td><td>{e.get("duration_s", duration(p)):.2f} s</td></tr>'
        )
    return "\n".join(out)


def main():
    entries = []
    for m in sorted(HERE.glob("manifest_*.json")):
        letter = m.stem.split("_")[1][:1].upper()
        for e in json.load(open(m)):
            e = dict(e)
            e["strategy"] = STRATEGY.get(letter, letter)
            if not Path(e["file"]).exists():
                continue
            e["duration_s"] = e.get("duration_s") or duration(e["file"])
            entries.append(e)
    # also pick up wavs that no manifest lists
    listed = {Path(e["file"]).resolve() for e in entries}
    for emo in ("sadness", "anger"):
        for w in sorted((HERE / emo).glob("*.wav")):
            if w.resolve() not in listed:
                entries.append({"file": str(w), "emotion": emo, "desc": "(no manifest entry)", "strategy": STRATEGY.get(w.name[0], w.name[0]), "duration_s": duration(w)})
    refs = [{"file": str(REF / f"{n}.wav"), "desc": d, "strategy": "reference", "duration_s": duration(REF / f"{n}.wav")} for n, d in REF_DESC.items() if (REF / f"{n}.wav").exists()]
    sections = []
    for emo, title in (("sadness", "Sadness candidates"), ("anger", "Anger candidates")):
        sub = sorted([e for e in entries if e.get("emotion") == emo], key=lambda e: Path(e["file"]).name)
        sections.append(f"<h2>{title} ({len(sub)})</h2><table><tr><th>play</th><th>file</th><th>strategy</th><th>what it is</th><th>length</th></tr>{rows(sub)}</table>")
    page = f"""<!doctype html><meta charset="utf-8"><title>Microduck emotion sounds</title>
<style>body{{font:15px/1.4 -apple-system,Helvetica,sans-serif;margin:24px;max-width:1200px}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:middle}}th{{background:#f3f3f3}}audio{{width:230px}}code{{font-size:13px}}h2{{margin-top:32px}}
.note{{color:#555}}</style>
<h1>Microduck emotion sounds: candidates</h1>
<p class="note">Folder: <code>/Users/remi/microduck/notes/emotions/sounds/</code>. Strategy A ports the Reachy Mini flute sound into quack material (same contour, rhythm, energy). B designs the contour from music theory. C cuts and bends the robot's real bank files. Every file is 48 kHz mono, peak -3 dBFS, made with this robot's voice seed 4145077059. The references are quiet; turn up.</p>
<h2>References (Reachy Mini, flute)</h2><table><tr><th>play</th><th>file</th><th></th><th>what it is</th><th>length</th></tr>{rows(refs)}</table>
{"".join(sections)}
<p class="note">Regenerate this page: <code>/Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/sounds/make_index.py</code></p>
"""
    (HERE / "index.html").write_text(page)
    print(f"{len(entries)} candidates -> {HERE / 'index.html'}")


if __name__ == "__main__":
    main()
