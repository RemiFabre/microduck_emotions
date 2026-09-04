#!/usr/bin/env bash
# Install the already-built emotion build on the duck: the four daemons staged by the agent in
# ~/duck-sideload/ on the robot PLUS the "devastated" sound folder. One sudo password prompt.
#
#   /Users/remi/microduck/notes/emotions/install-on-duck.sh [microduck@192.168.1.29]
#
# What it does on the robot (same swap as notes/reachy-encounter/ship-to-duck.sh, step 3):
#   - stops padd and robotd
#   - copies robotd/padd/robotctl/btd into /opt/robot/daemon/releases/<v>/bin/ (keeps .orig backups
#     if there are none yet)
#   - creates /var/lib/robot/sounds/devastated/ and puts devastated_a.wav in it
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
WAV=/Users/remi/microduck/notes/emotions/sounds/robot/devastated_a.wav
ssh "$BOARD" 'mkdir -p ~/duck-sideload'
scp -q $(for b in $BINS; do printf '%s ' "$OUT/$b"; done) "$WAV" "$BOARD:duck-sideload/"

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
  mkdir -p /var/lib/robot/sounds/devastated
  install -m 0644 $SRC/devastated_a.wav /var/lib/robot/sounds/devastated/devastated_a.wav
  systemctl start robotd
  sleep 2
  systemctl start padd
  systemctl restart btd"
sleep 3
robotctl version | head -3
systemctl is-active robotd padd btd
ls -la /var/lib/robot/sounds/devastated/
journalctl -u padd -b --no-pager | tail -2'
echo "==> done. Start = stand up, Start again = drive, DPad-Up TAP = emotion mode (chirp), B = devastated."
