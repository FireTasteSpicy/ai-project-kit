# "Teresa and Ijooz" — local vocaloid-style ballad generator

This generates a sung rendition of the lyrics in
[`../teresa_and_ijooz_lyrics.txt`](../teresa_and_ijooz_lyrics.txt) **entirely
offline**, using only tools reachable from PyPI + Ubuntu apt.

> ⚠️ **Honest expectation:** the voice is **espeak-ng** (a robotic formant TTS)
> pitch-shifted onto a composed melody — a "vocaloid"-style robotic singer. It
> carries the words and the tune and is in key, but it does **not** sound like a
> real human artist. (The real-vocal path via ElevenLabs was unavailable in this
> environment, so this is the best fully-local result.)

## How it works
1. **Syllabify** the lyrics (`pyphen`) — one note per syllable.
2. **Compose a melody** in **D natural minor, ~68 BPM**: per-section melodic
   contours (verse / chorus / bridge) instantiated to each line's syllable count.
3. **Synthesize** each syllable with `espeak-ng` (soft female variant `en-us+f3`).
4. **Retune** each syllable to its target note: resample for pitch, then a
   hand-written **phase vocoder** stretches it to the exact note duration.
   Measured tuning error across the full song: **~0.43 semitone mean**.
5. **Backing**: synthesized felt piano, warm pad/strings, bass, and late brushed
   percussion over a D-minor progression, plus convolution reverb and a stereo mix.
6. **Export** `teresa_and_ijooz.{wav,mp3}`, a synced **`.lrc`**, a spectrogram,
   and a short preview clip.

## Requirements
System packages:
```bash
sudo apt-get install -y espeak-ng ffmpeg
```
Python packages:
```bash
pip install -r requirements.txt
```

## Run
```bash
cd song
python make_song.py        # writes everything into ../dist/
```

## Files
| file | role |
|------|------|
| `song_dsp.py`  | STFT/ISTFT, phase-vocoder time-stretch, autocorrelation pitch detection, `retune()` |
| `arrange.py`   | parse lyric sections, syllabify |
| `song.py`      | melody/contours, timing, espeak synthesis, vocal-track render |
| `make_song.py` | backing instruments, reverb, stereo mix, export, `.lrc`, spectrogram, preview |

## Tweaking
- **Tempo / key:** `BPM` and the `SCALE` / `deg_to_midi` in `song.py`.
- **Melody:** the `CONTOUR` dict (scale degrees) in `song.py`.
- **Voice:** the `espeak-ng -v` voice in `song.py:espeak_syl` (e.g. `en-us+f4`).
- **Mix balance:** the gain coefficients in `make_song.py` (`dry = ...`).
