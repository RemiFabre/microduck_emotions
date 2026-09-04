"""Mux an emotion sound into a simulated motion video: one gesture, sound + motion.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotions/combine.py \
        MOTION.mp4 SOUND.wav OUT.mp4 [--at 1.2] [--gain 1.0] [--open]

`--at` = second in the video where the sound starts (default 0). Video stream is copied, audio is
AAC. Repeat `--sound SOUND.wav --at T` pairs for several sounds (e.g. one quack per stomp).
"""
import argparse
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("sound")
    ap.add_argument("out")
    ap.add_argument("--at", type=float, default=0.0)
    ap.add_argument("--extra", nargs=2, action="append", metavar=("SOUND", "AT"), default=[],
                    help="another sound and its start time")
    ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    sounds = [(a.sound, a.at)] + [(s, float(t)) for s, t in a.extra]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.video]
    for s, _ in sounds:
        cmd += ["-i", s]
    parts = []
    for i, (_, t) in enumerate(sounds):
        parts.append(f"[{i + 1}:a]adelay={int(t * 1000)}|{int(t * 1000)},volume={a.gain}[s{i}]")
    mixed = "".join(f"[s{i}]" for i in range(len(sounds)))
    parts.append(f"{mixed}amix=inputs={len(sounds)}:normalize=0[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", a.out]
    subprocess.run(cmd, check=True)
    print(a.out)
    if a.open:
        subprocess.run(["open", a.out])


if __name__ == "__main__":
    sys.exit(main())
