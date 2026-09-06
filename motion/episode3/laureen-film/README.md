# Filming Laureen's conversation script on her own tree (2026-09-06 night)

What was filmed: Laureen's `source/public/scripts/reachy-microduck-conversation.json` (Space main, commit
70997f0) on HER tree plus the pull request's two commits (branch `pr/official-wobbler`, worktree
`/Users/remi/microduck/forks/mrs-pr`, pushed to `refs/pr/1` of her Space). Result:
`combined/episode3/laureen_conversation_v3_wobbler_followcam.mp4` (22 s).

Why the voice is rendered: the browser's speech synthesis never reaches Web Audio, so the recorder (canvas +
the audio monitor) cannot hear Reachy; the two earlier films only had the duck's sounds. Chrome on macOS
speaks through AVSpeechSynthesizer with `pitchMultiplier = utterance.pitch` and a rate mapped from
`utterance.rate` (Chromium `tts_mac.mm`). `avsay.m` does exactly that to a wav:

```bash
clang -fobjc-arc -framework AVFoundation -framework Foundation -o avsay avsay.m
./avsay out.wav "hello microduck" Arthur 1.28 1.02      # voice, pitch, web rate as in her emotionController.js
ffmpeg -i out.wav -ar 48000 -ac 1 -c:a pcm_s16le -af apad=pad_dur=0.15 line.wav
```

Chrome picks the voice by her regex (first en-GB voice whose name matches david|mark|guy|daniel|alex|arthur|...):
on this Mac that is **Arthur** (Daniel comes after it in the list). `laureen-film.json` = her script with an
`audio` field per Reachy line (the wavs in `lines/`); it lives UNTRACKED in the PR worktree as
`source/public/scripts/laureen-film.json` + `source/public/assets/voices/laureen/` (film only, not in the PR).

Film again (PR worktree, her `source/` tree; `git lfs pull upstream` first, her meshes are LFS):

```bash
cd /Users/remi/microduck/forks/mrs-pr/source && npm ci && npm run build && npx vite preview --host 127.0.0.1 --port 4174 &
cd /Users/remi/microduck/forks/microduck-reachy-simulator && node tools/record-episode3.mjs http://127.0.0.1:4174 /tmp/x.webm \
  /Users/remi/microduck/notes/emotions/combined/episode3/laureen_conversation_vN.mp4 laureen-film follow
```

Always a NEW file name + `?v=<epoch>` on the page (his browser shows a stale first frame otherwise); the recorder
checks the mp4's timestamps are monotonic.

## Filming with a hand-driven camera (Rémi behind the mouse)

```bash
/Users/remi/microduck/notes/emotions/motion/episode3/laureen-film/film-manual.sh [name]
```

Builds the PR tree (skip with `SKIP_BUILD=1`), serves it, opens Chrome maximised on her script with
`autoplay=key`: after the entrance a banner asks for **Enter** (or a click on it). Press it, then drag to orbit and
scroll to zoom while the script plays (about 22 s). The film (canvas + sound, at the window's size) is saved as
`combined/episode3/<name>.mp4` (default `laureen_manual_<time>`) and opened. The driver is the fork's
`tools/film-manual.mjs` (`AUTO_ENTER=1` presses Enter itself, for a test). Keyboard while filming: Enter is only the
start key; Space would reset the duck, C toggles the chase cam, so keep to the mouse.

## Captions + title card (the final cut, 2026-09-06 night)

Same recipe as episodes 1 and 2 (`agentic_robot_theater/video/`): the three rendered lines cross-correlated onto the
film's soundtrack (300-3400 Hz band, normalised), one caption per line (start = line start, end = line end + 0.45 s,
no overlap), PIL overlays in the episode look (Arial Bold 58, white + 3 px black stroke, amber "REACHY MINI" tag 30 px,
black 150-alpha rounded box, 90 px from the bottom). Montage: Laureen's home photo (`source/public/reachy-mini-home.jpg`,
centre-cropped to the film's size) for 2 s, a 0.5 s crossfade, then the captioned film (its clock shifts by 1.5 s).
Output: `combined/episode3/final/laureen_conversation_final.mp4` + `.srt`. Source take: `laureen_manual_223231.mp4`
(Rémi's hand camera).
