#!/usr/bin/env python
"""Build index.html from results.json (+ the mp4 / sheet files next to it)."""
import json, html
from pathlib import Path

HERE = Path(__file__).resolve().parent
res = json.load(open(HERE / "results.json"))

REJECTED = "rejected by Rémi: flamingo (too long, too complex, often falls; the real stomp will be trained like the kick)"
RECOMMENDED = "B8_kick_recentre_0.5s_robotd"
order = [RECOMMENDED] + [n for n in res if n != RECOMMENDED and not n.startswith("A")] + [n for n in res if n.startswith("A")]
rows, cards = [], []
for name in order:
    st = res[name]
    tag = (" <b style='color:#6f6'>RECOMMENDED</b>" if name == RECOMMENDED else "") + (f" <i style='color:#f88'>{REJECTED}</i>" if name.startswith("A") else "")
    for i, s in enumerate(st["stomps"]):
        rows.append(f"<tr{' class=rej' if name.startswith('A') else ''}><td>{(name + (' *' if name == RECOMMENDED else '') + (' (rejected)' if name.startswith('A') else '')) if i == 0 else ''}</td><td>{html.escape(s['label'])}</td><td>{s['foot']}</td>"
                    f"<td>{s['peak_mm']:.0f}</td><td>{s['down_speed_m_s']:.2f}</td><td>{s['peak_to_land_s'] if s['peak_to_land_s'] is not None else '-'}</td>"
                    f"<td>{s['other_foot_planted_frac']*100:.0f} %</td><td>{s['head_yaw_left_deg']:+.0f} / {s['head_yaw_right_deg']:+.0f}</td>"
                    f"<td>{'FELL' if st['fell'] else 'no'} (tilt {st['max_tilt_deg']:.0f}°)</td><td>{st['max_joint_speed_rad_s']}</td></tr>")
    mp4 = HERE / f"{name}.mp4"; sheet = HERE / f"{name}_sheet.png"
    cards.append(f"<div class=card{' rej' if name.startswith('A') else ''}><h3>{name}{tag}</h3><p>{html.escape(st['description'])}</p>"
                 + (f"<video controls muted loop preload=metadata src='{mp4.name}'></video>" if mp4.exists() else "")
                 + (f"<a href='{sheet.name}'><img src='{sheet.name}'></a>" if sheet.exists() else "")
                 + "<pre>" + "\n".join(f"{s['label']}: foot {s['foot']}, peak {s['peak_mm']:.0f} mm, down {s['down_speed_m_s']:.2f} m/s, peak-to-land {s['peak_to_land_s']} s, other foot planted {s['other_foot_planted_frac']*100:.0f} %, head yaw L {s['head_yaw_left_deg']:+.0f}° / R {s['head_yaw_right_deg']:+.0f}°" for s in st["stomps"])
                 + f"\nfell {st['fell']}, max tilt {st['max_tilt_deg']}°, ends upright {st['final_upright']}, max joint speed {st['max_joint_speed_rad_s']} rad/s</pre></div>")

page = f"""<!doctype html><meta charset=utf-8><title>Anger stomp, programmatic probe</title>
<style>body{{font:14px -apple-system,sans-serif;background:#111;color:#eee;margin:20px}}
h1{{font-size:20px}} h3{{margin:4px 0}} .card{{background:#222;padding:10px;border-radius:8px;margin:12px 0}}
video{{width:640px;display:block;margin:6px 0}} img{{max-width:100%;display:block}} pre{{font-size:12px;color:#9c9;white-space:pre-wrap}}
table{{border-collapse:collapse;font-size:13px}} td,th{{border:1px solid #444;padding:3px 8px;text-align:right}} td:first-child,td:nth-child(2),td:nth-child(3){{text-align:left}}
p.note{{color:#bbb;max-width:900px}} tr.rej td{{color:#777}} .card.rej{{opacity:.55}}</style>
<h1>Angry foot stomp with the shipped policies (no training): CPU proxy, BAM XL330 + 1.75 A + 15-30 ms delay</h1>
<p class=note>Target: lift one foot, slam it down, head snaps left on the first stomp; same foot again, head snaps right; ends standing.
"peak" = how high the stomping foot rose above its rest height; "down" = fastest downward speed of that foot on its way back to the floor
(free fall from 7 cm would reach ~1.2 m/s; a gentle lowering is 0.2-0.5 m/s); "peak-to-land" = seconds from the top of the lift to floor contact
(a stomp is &lt; 0.15 s); "other planted" = fraction of the lift window with the other foot on the floor; head yaw = measured joint extremes,
+ is the robot's left. Verdict and the command timeline: <a href='REPORT.md'>REPORT.md</a>.<br>
<b>Verdict:</b> yes, usable as a fallback: the shipped <b>kick</b> skill is a real stomp (left foot 68 mm up, slams at 0.81 m/s, on the floor 0.36 s after the trigger, other foot never leaves the floor, no fall), and the standing net snaps the head ±60° right after. The one rule: <b>re-centre the head before the second kick</b> (a kick triggered with the head turned does nothing: B1-B3). The A-series (flamingo) is kept for the record only: rejected by Rémi.</p>
<table><tr><th>candidate</th><th>event</th><th>foot</th><th>peak (mm)</th><th>down (m/s)</th><th>peak-to-land (s)</th><th>other planted</th><th>head yaw L / R (°)</th><th>fell</th><th>max joint speed (rad/s)</th></tr>
{''.join(rows)}</table>
{''.join(cards)}"""
(HERE / "index.html").write_text(page)
print("wrote", HERE / "index.html", len(res), "candidates")
