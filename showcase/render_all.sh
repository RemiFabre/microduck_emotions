#!/bin/sh
# Render every shipped emotion with the orbit camera, 3 at a time (each MuJoCo process takes 2-2.6 GB): render_all.sh OUT_DIR [emotion ...]
OUT=$1; shift
mkdir -p "$OUT"
LIST=${*:-"devastated sad play_dead curious mmh yes yes_fast no angry excited laugh mock defiant impatient"}
HERE=$(cd "$(dirname "$0")" && pwd)
echo $LIST | tr ' ' '\n' | xargs -P 3 -n 1 sh -c '/Users/remi/microduck/.venv-mjlab/bin/python "$0/orbit.py" "$2" "$1" > "$1/$2.log" 2>&1 || echo "FAIL $2 (see $1/$2.log)"' "$HERE" "$OUT"
