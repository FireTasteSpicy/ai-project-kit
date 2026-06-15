# Session Handoff — "Teresa and Ijooz" ballad (real vocals)

> Pick this up in a **fresh** Claude Code session. Everything needed is here or in
> the environment settings. **No secret is stored in this file by design** — see
> "Credentials" below.

## Goal
Produce a finished song from the committed lyrics: a mellow, tear-stained ballad
titled **"Teresa and Ijooz"**, with **real sung vocals** (not TTS narration),
generated via the **ElevenLabs Music API**. Deliver to the user:
1. the audio file, and
2. a time-synced **`.lrc`** lyric file.

## Where things are
- Branch: **`claude/sweet-fermat-tj1af0`** (develop + push here only).
- Lyrics + full style/production direction: **`teresa_and_ijooz_lyrics.txt`**.
- Style summary: mellow melancholic indie folk-pop ballad; soft, breathy female
  lead on the verge of tears; fingerpicked acoustic guitar + felt piano; warm
  sustained strings; light brushed percussion entering late; **~68 BPM, D minor**;
  tender verses, a small swell in the final chorus, then settle soft.

## Credentials (read carefully)
- The ElevenLabs API key is **NOT** in this repo and must never be committed.
- Expected location: environment variable **`ELEVENLABS_API_KEY`** (set in the
  environment's settings / secrets, which persists across sessions).
- First thing to do: `test -n "$ELEVENLABS_API_KEY" && echo present || echo MISSING`.
  - If `MISSING`, ask the user to paste the key once (then export it for the
    session); do not write it to a tracked file.

## Network
- Egress was switched to **full ("All domains")**, so `api.elevenlabs.io` (and the
  ElevenLabs docs) should now be reachable **in a new session**. Egress rule changes
  do **not** apply to an already-running session — that was the whole blocker before.
- Sanity check: `curl -s -o /dev/null -w '%{http_code}\n' https://api.elevenlabs.io`.

## Steps for the new session
1. Verify key present (above) and reachability:
   `curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/user/subscription`
   → expect HTTP 200 with subscription JSON.
2. **Confirm the current Music API shape from the official docs first** (the Eleven
   Music API is newer and may have changed) — likely a `POST` to a
   `/v1/music`-style compose endpoint that accepts a prompt + the lyrics and
   returns audio (and possibly word/section timing). Don't hard-code an endpoint
   from memory without checking.
3. Compose the track: feed the **style direction** as the prompt and the **lyrics**
   (verses/chorus/bridge structure) so the model actually *sings* them. Request a
   vocal mix, slow tempo, D minor, full song length.
4. Save audio to the repo (e.g. `teresa_and_ijooz.mp3`).
5. Produce **`teresa_and_ijooz.lrc`**: if the API returns alignment/timestamps, use
   them; otherwise derive timings from the returned duration + section structure.
6. **Deliver** both files to the user with `SendUserFile`, and commit them to the
   branch. Keep the key out of every commit.

## Status at handoff
- ✅ Lyrics + style committed (`5393ede`).
- ✅ Egress set to full (takes effect on the *next* session).
- ⏳ Pending: key available as `ELEVENLABS_API_KEY` in a fresh session → then generate.
