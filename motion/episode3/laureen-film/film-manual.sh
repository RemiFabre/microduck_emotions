#!/bin/zsh
# Film Laureen's script in HER simulator (the PR 2 tree) with a hand-driven camera, recorded with sound.
#   film-manual.sh [name]        -> combined/episode3/<name>.mp4 (default laureen_manual_<time>)
#   SCRIPT=laureen-film (default; her script with the rendered Reachy lines)  SKIP_BUILD=1 to reuse the last build
# The Chrome window opens; after the entrance a banner asks for Enter: press it, then drag to orbit, scroll to zoom.
# The film is saved and opened when the script ends (about 25 s).
set -e
PR=/Users/remi/microduck/forks/mrs-pr/source
FORK=/Users/remi/microduck/forks/microduck-reachy-simulator
OUTDIR=/Users/remi/microduck/notes/emotions/combined/episode3
NAME="${1:-laureen_manual_$(date +%H%M%S)}"
PORT=4174
cd "$PR"
[ -d node_modules ] || npm ci --no-audit --no-fund
grep -rq "oid sha256" public/robot/reachy/assets 2>/dev/null && { echo "meshes are LFS pointers: git lfs pull upstream"; (cd .. && git lfs pull upstream); }
[ -n "$SKIP_BUILD" ] || npm run build 2>&1 | grep -E "built in|error" || true
pkill -f "vite preview --host 127.0.0.1 --port $PORT" 2>/dev/null || true
npx vite preview --host 127.0.0.1 --port $PORT >/tmp/laureen-preview.log 2>&1 &
PREVIEW=$!
for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/ | grep -q 200 && break; sleep 1; done
cd "$FORK"
node tools/film-manual.mjs http://127.0.0.1:$PORT /tmp/$NAME.webm "$OUTDIR/$NAME.mp4" "${SCRIPT:-laureen-film}" || true
kill $PREVIEW 2>/dev/null || true
[ -f "$OUTDIR/$NAME.mp4" ] && { echo "film: $OUTDIR/$NAME.mp4"; open "$OUTDIR/$NAME.mp4"; }
