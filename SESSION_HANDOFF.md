# Session Handoff — "Teresa and Ijooz" ballad (real vocals)

> Pick this up in a **fresh** Claude Code session. **No secret is stored in this
> file by design.** Two generation paths are wired up and ready; each is blocked
> on one external/account action described below.

## Goal
Produce a finished song from the committed lyrics: a mellow, tear-stained ballad
titled **"Teresa and Ijooz"**, with **real sung vocals** (not TTS narration).
Deliver to the user:
1. the audio file (`teresa_and_ijooz.mp3`), and
2. a time-synced **`.lrc`** lyric file (`teresa_and_ijooz.lrc`).

## ✅ Egress update (2026-06-15, new session): `api.mureka.ai` now allowed
As of this session, `api.mureka.ai` **is reachable** (`GET https://api.mureka.ai`
→ HTTP 200; `GET /v1/account/billing` → HTTP 200 with the API key). The earlier
egress blocker for Mureka is **resolved**. Network egress is still a **host
allowlist** (not "full"): `api.elevenlabs.io` and `api.mureka.ai` are allowed;
arbitrary hosts still return `Host not in allowlist: <host>`. `WebSearch`/
`WebFetch` route through the harness and are unaffected. Egress changes typically
take effect only in a **new** session.

## Two ready-to-run paths

### Path A — Mureka (currently the active plan; egress now OK, but NEEDS PAID CREDITS)
- Key: **`MUREKA_API_KEY`** is present in the environment (verified, len 36) and
  authenticates fine (`/v1/account/billing` → 200).
- Script: **`scripts/generate_music_mureka.py`** — contract VERIFIED live. It calls
  `POST /v1/song/generate {lyrics, model, prompt}`, polls `GET /v1/song/query/{id}`
  until done, downloads the audio, and writes the `.lrc` (duration-based, since
  Mureka returns no word timestamps).
- ⛔ **Blocker (new): the Mureka account has no usable credits.**
  `POST /v1/song/generate` → **HTTP 429** `{"error":{"message":"You exceeded your
  current quota, please check your plan and billing details"}}`. The earlier
  "free-tier, no card" assumption was wrong: the Mureka **API** is a paid credit
  system (~$48 / 1600 credits, balance valid ~12 months). To unblock, add API
  credits to the account behind `MUREKA_API_KEY` at platform.mureka.ai, then run
  `python3 scripts/generate_music_mureka.py`.
- API contract (confirmed from Mureka docs/examples):
  - base `https://api.mureka.ai` (override via `MUREKA_API_URL`)
  - auth `Authorization: Bearer $MUREKA_API_KEY`
  - generate body: `{ "lyrics": "[Verse]\n…", "model": "auto", "prompt": "<style>" }`
  - async task → poll → `choices[]` holds the finished audio URL (+ usually duration).

### Path B — ElevenLabs (highest quality + exact lyric sync; needs paid plan)
- Key: **`ELEVENLABS_API_KEY`** present and valid (`/v1/user/subscription` → 200,
  `tier: free`). `api.elevenlabs.io` is already allowlisted.
- Script: **`scripts/generate_music.py`** (ready; produces mp3 **and** an exact
  `.lrc` from per-word timestamps in one run).
- ⛔ **Blocker: the Music API is paid-only.** A real call to `POST /v1/music/detailed`
  returns **HTTP 402** `{"code":"paid_plan_required","message":"Music API is not
  available for free users."}`. Nothing is charged on a 402. Put the key on a paid
  plan (Starter+ includes Music API), then run `python3 scripts/generate_music.py`.
- Contract confirmed from the live OpenAPI spec: `POST /v1/music/detailed?output_format=mp3_44100_128`,
  body `{prompt, lyrics_text, music_length_ms, model_id, with_timestamps:true}`,
  response `multipart/mixed` (JSON `song_metadata`+`words_timestamps` + binary audio).

## Final steps (either path, once unblocked)
1. Run the relevant script (above).
2. **Deliver** `teresa_and_ijooz.mp3` + `teresa_and_ijooz.lrc` with `SendUserFile`.
3. Commit both to the branch. Keep every key out of every commit.

## Where things are
- Active feature branch: **`claude/epic-carson-ded5q6`** (develop + push here;
  contains all prior work). The older `claude/busy-einstein-wv0fby` is superseded.
- Lyrics + full style/production direction: **`teresa_and_ijooz_lyrics.txt`**.
- Generators: **`scripts/generate_music_mureka.py`** (A), **`scripts/generate_music.py`** (B).
- Style summary: mellow melancholic indie folk-pop ballad; soft, breathy female
  lead on the verge of tears; fingerpicked acoustic guitar + felt piano; warm
  sustained strings; light brushed percussion entering late; **~68 BPM, D minor**;
  tender verses, a small swell in the final chorus, then settle soft.

## Other free music APIs considered (2026-06-15)
Real *web apps* are free everywhere; free *APIs that sing custom lyrics* are rare.
- **Mureka** — first-party API + free trial credits, no card → chosen (Path A).
- **Suno** — no official API; free web tier is non-commercial; third-party
  resellers offer small trial credits.
- **Udio** — official API waitlist-only; free web tier non-commercial.
- **MusicGen / Stable Audio** (open source) — free but **instrumental**; won't
  sing the lyrics, so they don't meet the goal.

## Status at handoff
- ✅ Lyrics + style committed; both generator scripts committed and validated.
- ✅ Keys present: `MUREKA_API_KEY`, `ELEVENLABS_API_KEY`.
- ✅ Mureka egress resolved; Mureka API contract verified live (auth + endpoints OK).
- ⛔ Path A (Mureka) now blocked on **paid API credits** (HTTP 429 quota exceeded).
- ⛔ Path B (ElevenLabs) blocked on a **paid plan** (HTTP 402 paid_plan_required).
- ➡️ Both ready paths now require a paid account action — awaiting user decision.
