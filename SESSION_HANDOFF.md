# Session Handoff — "Teresa and Ijooz" ballad (real vocals)

> Pick this up in a **fresh** Claude Code session. Everything needed is here or in
> the environment settings. **No secret is stored in this file by design** — see
> "Credentials" below.

## Goal
Produce a finished song from the committed lyrics: a mellow, tear-stained ballad
titled **"Teresa and Ijooz"**, with **real sung vocals** (not TTS narration),
generated via the **ElevenLabs Music API**. Deliver to the user:
1. the audio file (`teresa_and_ijooz.mp3`), and
2. a time-synced **`.lrc`** lyric file (`teresa_and_ijooz.lrc`).

## ⛔ Current blocker (READ FIRST) — paid plan required
The ElevenLabs **Music API is not available on the free tier**. A real call to
`POST /v1/music/detailed` returns **HTTP 402**:

```json
{"detail": {"type": "payment_required", "code": "paid_plan_required",
 "message": "Music API is not available for free users. Please upgrade to a
 paid plan to use the API."}}
```

Nothing is charged on a 402. The previous handoff assumed the key/egress were the
blockers — those are now **resolved**; the *only* remaining blocker is the account
plan. To finish: put the configured key on a **paid ElevenLabs plan** (Starter tier
or above includes Music API access + commercial rights), then re-run the script
below — it will generate the audio **and** the `.lrc` in one shot.

## ✅ Verified working (so generation is one command away)
- `ELEVENLABS_API_KEY` is present and valid — `GET /v1/user/subscription` → HTTP 200
  (currently `tier: free`, `0 / 10000` credits used).
- Network egress to `api.elevenlabs.io` is open (full egress).
- Correct, current API shape confirmed from the live OpenAPI spec:
  - `POST /v1/music/detailed?output_format=mp3_44100_128`
  - body: `prompt`, `lyrics_text`, `music_length_ms`, `model_id` (`music_v1`/`music_v2`),
    `with_timestamps: true`
  - response: `multipart/mixed` → a JSON part (`song_metadata`, `composition_plan`,
    `words_timestamps` = per-word `{word, start_ms, end_ms}`) + a binary audio part.
- **Ready-to-run generator: `scripts/generate_music.py`** — builds the request from
  the lyrics/style, parses the multipart response, writes `teresa_and_ijooz.mp3`, and
  builds `teresa_and_ijooz.lrc` from the word timestamps (with interpolation fallback).

## Steps for the new session (once on a paid plan)
1. `test -n "$ELEVENLABS_API_KEY" && echo present || echo MISSING`
2. Confirm the plan is paid: `curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" \
   https://api.elevenlabs.io/v1/user/subscription` → `tier` should NOT be `free`.
3. `pip install requests` (if needed), then `python3 scripts/generate_music.py`.
4. **Deliver** both files to the user with `SendUserFile`, and commit them to the
   branch. Keep the key out of every commit.

## Credentials (read carefully)
- The ElevenLabs API key is **NOT** in this repo and must never be committed.
- Expected location: environment variable **`ELEVENLABS_API_KEY`** (set in the
  environment's settings / secrets, which persists across sessions).
- If `MISSING`, ask the user to paste the key once (then export it for the
  session); do not write it to a tracked file.

## Where things are
- Active feature branch: **`claude/busy-einstein-wv0fby`** (develop + push here).
- Lyrics + full style/production direction: **`teresa_and_ijooz_lyrics.txt`**.
- Generator script: **`scripts/generate_music.py`**.
- Style summary: mellow melancholic indie folk-pop ballad; soft, breathy female
  lead on the verge of tears; fingerpicked acoustic guitar + felt piano; warm
  sustained strings; light brushed percussion entering late; **~68 BPM, D minor**;
  tender verses, a small swell in the final chorus, then settle soft.

## Free-tier alternatives (researched 2026-06-15)
If the user prefers not to pay for ElevenLabs, here is the honest state of free
**music-generation APIs** that actually **sing custom lyrics**. Caveat throughout:
a free *web app* is not the same as a free *API*, and any alternative needs the
user to sign up and provide a new key (I can't accept terms on their behalf).

- **Suno** — best-known quality. *No official API*; the free web tier (~50
  credits/day) is non-commercial. API only via **third-party resellers**, some of
  which grant small **free trial credits** (e.g. Apiframe ~300), then paid.
- **Udio** — official API is **waitlist-only**; free web tier is non-commercial.
  Reachable via third-party aggregators (some advertise a free tier / no card).
- **Mureka** (`platform.mureka.ai`) — has a **first-party developer API** and a
  **free trial with limited credits, no credit card**; sings user-provided lyrics.
  Strongest "actual free API" candidate, but trial credits are limited.
- **Aggregators** (musicapi.ai, aimlapi, apiframe, …) — single REST endpoint
  wrapping Suno/Udio; a few offer trial credits with no card.
- **Open-source / self-host** (MusicGen, Stable Audio) — free but **instrumental**;
  they do not sing custom lyrics, so they don't meet the "real sung vocals" goal.

Common catches on any free path: non-commercial license, watermarks, limited
credits/length, sign-up required, variable quality, and (unlike ElevenLabs
`with_timestamps`) usually **no word-level timing**, so the `.lrc` would need to be
derived from section structure / total duration instead of exact word timestamps.

## Status at handoff
- ✅ Lyrics + style committed.
- ✅ Key valid, egress full, API shape confirmed.
- ✅ `scripts/generate_music.py` ready (produces mp3 + lrc in one run).
- ⛔ Blocked on **paid ElevenLabs plan** (Music API is paid-only). Either upgrade
  the plan, supply a paid-plan key, or pursue a free alternative (see above).
