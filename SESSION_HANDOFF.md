# Session Handoff — "Teresa and Ijooz" ballad (real vocals)

> Pick this up in a **fresh** Claude Code session **after the egress fix below**.
> **No secret is stored in this file by design** — see "Credentials".

## Goal
Produce a finished song from the committed lyrics: a mellow, tear-stained ballad
titled **"Teresa and Ijooz"**, with **real sung vocals** (not TTS narration),
generated via the **ElevenLabs Music API**. Deliver to the user:
1. the audio file (`teresa_and_ijooz.mp3`), and
2. a time-synced **`teresa_and_ijooz.lrc`** lyric file.

## ⛔ BLOCKER (must fix before generation is possible)
The previous handoff assumed egress was set to "full" and ElevenLabs would be
reachable. **It is not.** Verified this session:
```
curl https://api.elevenlabs.io        -> 403 "Host not in allowlist: api.elevenlabs.io"
curl https://api.us.elevenlabs.io     -> 403 "Host not in allowlist"
curl https://elevenlabs.io            -> 403 "Host not in allowlist"
curl https://pypi.org                 -> 200   (so PyPI/pip works)
curl https://api.github.com           -> reachable
```
The environment is on a **curated egress allowlist** that excludes every
ElevenLabs domain — not "All domains". Disabling the Bash sandbox does **not**
help: the refusal comes from the upstream environment proxy. Egress is fixed at
environment-creation time and **cannot be changed from inside a running session.**

**To unblock:** edit the environment's network egress policy to allow at least
`api.elevenlabs.io` (and ideally `elevenlabs.io`, `api.us.elevenlabs.io`, and any
ElevenLabs storage/CDN host used for audio delivery) — or select "All domains" —
**then start a NEW session.** Egress changes never apply to an already-running
session. Docs: https://code.claude.com/docs/en/claude-code-on-the-web

## Branch
- Latest work (generator + plan + this handoff) is on **`claude/cool-cannon-d1bnz2`**
  (the active task pinned this branch). The original handoff named
  `claude/sweet-fermat-tj1af0`; if you continue there, cherry-pick these commits.

## What's ready (committed)
- `teresa_and_ijooz_lyrics.txt` — lyrics + full style/production direction.
- `teresa_and_ijooz.plan.json` — **composition plan** built from the lyrics:
  global + per-section styles, durations (~3:22 ballad, ~68 BPM, D minor), and the
  exact `lines` per section so the model **sings** the words. Edit freely.
- `scripts/generate_song.py` — **one-command generator** (offline logic tested;
  the API call path is UNVERIFIED here because egress was blocked).

## Credentials
- ElevenLabs key is **NOT** in the repo and must never be committed.
- Flow: user pastes the key once → export for the session:
  `export ELEVENLABS_API_KEY='sk_...'` (this session also stashed it at
  `~/.elevenlabs_key`, outside the tree; `export ELEVENLABS_API_KEY=$(cat ~/.elevenlabs_key)`).
- `.gitignore` now blocks `.env`, `*.key`, `.elevenlabs_key`, `secrets.*` as a guard.

## Steps for the new session (after egress is fixed)
1. Confirm key + reachability (expect HTTP 200 + subscription JSON):
   `curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/user/subscription`
2. `pip install elevenlabs requests`
3. `python scripts/generate_song.py`
   → writes `teresa_and_ijooz.mp3`, `teresa_and_ijooz.lrc`, `teresa_and_ijooz.metadata.json`.
4. **Listen / verify** vocals are sung (not spoken) and the .lrc lines line up.
   If timing is off, re-run — the script prefers word-level timestamps from the API
   and only falls back to section timing when they're absent.
5. **Deliver** the `.mp3` and `.lrc` with `SendUserFile`, and commit them. Key out
   of every commit.

## Confirmed ElevenLabs Music API shape (from docs research, Jun 2026)
- Auth header: `xi-api-key: <key>`.
- `POST /v1/music` — compose; returns raw audio bytes. Body: `prompt` (≤4100 chars)
  **or** `composition_plan` (not both), `music_length_ms`, `output_format`
  (e.g. `mp3_44100_128`; `mp3_44100_192` needs Creator tier).
- `POST /v1/music/detailed` — returns audio **plus** JSON metadata
  (`composition_plan` + `song_metadata`); supports **word-level timestamps** for the
  vocal (parameter ~`with_timestamps`) → used to build a precise `.lrc`.
- `composition_plan` = `{ positiveGlobalStyles[], negativeGlobalStyles[],
  sections[ { sectionName, positiveLocalStyles[], negativeLocalStyles[], durationMs, lines[] } ] }`.
  The `lines[]` are the sung lyrics. (This is the newer Music API — re-confirm field
  names against the live docs before trusting blindly:
  https://elevenlabs.io/docs/api-reference/music/compose-detailed)

## Status at handoff
- ✅ Lyrics + style committed.
- ✅ Composition plan + turnkey generator committed (offline logic tested).
- ⛔ Egress to ElevenLabs is **blocked in this session** — generation impossible here.
- ⏳ Next: fix egress → fresh session → `python scripts/generate_song.py` → deliver.
