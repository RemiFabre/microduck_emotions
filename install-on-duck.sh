#!/usr/bin/env bash
# Install the already-built emotion build on the duck: the four daemons staged by the agent in
# ~/duck-sideload/ on the robot PLUS every emotion sound folder (sounds/robot/<tag>_*.wav ->
# /var/lib/robot/sounds/<tag>/). One sudo password prompt.
#
#   /Users/remi/microduck/notes/emotions/install-on-duck.sh [microduck@192.168.1.29]
#
# What it does on the robot (same swap as notes/reachy-encounter/ship-to-duck.sh, step 3):
#   - stops padd and robotd
#   - copies robotd/padd/robotctl/btd into /opt/robot/daemon/releases/<v>/bin/ (keeps .orig backups
#     if there are none yet)
#   - creates /var/lib/robot/sounds/<tag>/ for every tag in sounds/robot/ (devastated, sad, curious,
#     yes, no, angry, excited, play_dead) and copies the wavs (robotd picks one at random per play)
#     (NB: `sounds ensure-bank --force` wipes the whole bank folder, so re-run this after it)
#   - starts robotd, then padd, restarts btd, prints version / units / padd's mapping line
#
# Undo: /Users/remi/microduck/notes/reachy-encounter/unship-from-duck.sh (the sound folder is
# harmless to leave in place).
set -euo pipefail
BOARD="${1:-microduck@192.168.1.29}"
BINS="robotd padd robotctl btd"

# Re-copy the staged files in case the robot's copy is stale (cheap).
OUT=/Users/remi/microduck/microduck/target/docker/aarch64-unknown-linux-gnu/release
WAVS=/Users/remi/microduck/notes/emotions/sounds/robot
ssh "$BOARD" 'mkdir -p ~/duck-sideload/sounds'
scp -q $(for b in $BINS; do printf '%s ' "$OUT/$b"; done) "$BOARD:duck-sideload/"
scp -q "$WAVS"/*.wav "$BOARD:duck-sideload/sounds/"

ssh -t "$BOARD" 'set -e
REL=$(readlink -f /opt/robot/daemon/current)
SRC=$HOME/duck-sideload
echo "release dir: $REL"
sudo sh -c "set -e
  systemctl stop padd robotd
  for b in '"$BINS"'; do
    [ -f $REL/bin/\$b.orig ] || cp -p $REL/bin/\$b $REL/bin/\$b.orig
    install -m 0755 -o root -g root $SRC/\$b $REL/bin/\$b
  done
  for w in $SRC/sounds/*.wav; do
    tag=\$(basename \$w .wav | sed -E 's/_[a-z]$//')
    mkdir -p /var/lib/robot/sounds/\$tag
    install -m 0644 \$w /var/lib/robot/sounds/\$tag/
  done
  systemctl start robotd
  sleep 2
  systemctl start padd
  systemctl restart btd"
sleep 3
robotctl version | head -3
systemctl is-active robotd padd btd
ls /var/lib/robot/sounds/
journalctl -u padd -b --no-pager | tail -2'
echo "==> done. Start = stand up, Start again = drive, DPad-Up TAP = emotion mode (chirp): A sad, B devastated, X angry, Y curious, LB yes, RB no, DPad-Down excited, DPad-Left play dead. Cue port TCP 7777."
