"""Print a Rust mouth table (0..1 every 0.1 s, ends on a zero) from a keyframes json of lib.render."""
import json, sys
for p in sys.argv[1:]:
    keys = json.load(open(p))["keyframes"]
    vals = [round(k["mouth"], 3) for k in keys]
    while len(vals) > 1 and vals[-1] == 0 and vals[-2] == 0:
        vals.pop()
    if vals[-1] != 0:
        vals.append(0.0)
    print(p.split('/')[-1], len(vals))
    print(", ".join(f"{v:.3f}" for v in vals))
