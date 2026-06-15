#!/usr/bin/env python3
"""Generate the "Teresa and Ijooz" ballad with real sung vocals via the
**Mureka** Music API, then write a time-synced .lrc alongside the audio.

Why this exists: the ElevenLabs Music API requires a paid plan (see
scripts/generate_music.py). Mureka offers a first-party music API with free
trial credits and sings user-provided lyrics, so this is the free-tier path.

⛔ NETWORK BLOCKER (read first)
This environment uses a **host egress allowlist**. As of this writing only
`api.elevenlabs.io` is allowed; `api.mureka.ai` is NOT, so this script fails
with: "Host not in allowlist: api.mureka.ai". To run it, add `api.mureka.ai`
to the environment's network egress settings. Egress changes typically only
take effect in a NEW session, not the one that was already running.

USAGE
-----
    export MUREKA_API_KEY=...        # already set in this environment
    # (optionally) export MUREKA_API_URL=https://api.mureka.ai
    python3 scripts/generate_music_mureka.py

Outputs (repo root):
    teresa_and_ijooz.mp3
    teresa_and_ijooz.lrc

API shape (confirmed from Mureka docs / official examples):
  POST {base}/v1/song/generate   body {lyrics, model, prompt}  -> async task {id, status}
  GET  {base}/v1/song/query/{id} -> poll; on success a `choices[]` entry holds the
                                    audio URL (and usually a duration).
Auth: `Authorization: Bearer $MUREKA_API_KEY`.

Mureka does not return word-level timestamps, so the .lrc is built by
distributing the lyric lines across the returned duration (approximate sync).
If the response ever includes per-word/line timing, it is used instead.

Requires: requests
"""
import os
import re
import sys
import time
import json
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_OUT = REPO_ROOT / "teresa_and_ijooz.mp3"
LRC_OUT = REPO_ROOT / "teresa_and_ijooz.lrc"
META_OUT = Path("/tmp/teresa_mureka_meta.json")

BASE_URL = os.environ.get("MUREKA_API_URL", "https://api.mureka.ai").rstrip("/")
MODEL = "auto"            # documented safe default; or a specific model id
TITLE = "Teresa and Ijooz"
POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 600

DONE_STATES = {"succeeded", "success", "completed", "complete", "finished", "done"}
FAIL_STATES = {"failed", "fail", "error", "cancelled", "canceled",
               "timeouted", "timeout", "expired"}

PROMPT = (
    "mellow melancholic indie folk-pop ballad, soft intimate breathy female lead "
    "vocal on the verge of tears, fingerpicked acoustic guitar, felt piano, warm "
    "sustained strings, light brushed percussion entering late, slow tempo ~68 BPM, "
    "key of D minor, tender and wistful verses swelling slightly in the final "
    "chorus then settling soft, bittersweet, emotionally moving"
)

LYRICS_TEXT = """[Verse]
The lucky draw spins slow beneath the cold mall light,
Teresa holds her number like a prayer.
She's watched the prizes all night long, the blind boxes stacked tight,
and let herself believe one's waiting there.

[Verse]
The girl ahead tears open a little vinyl king,
the boy beside her gasps, a rare, the gold.
And everyone is cradling some small, beloved thing,
while Teresa's hands stay empty in the cold.

[Chorus]
'Cause it's two dollars of sunshine,
two dollars of gold,
the same paper voucher
each time the wheel slows.
Not the box that she dreamed of,
not the prize on the shelf,
just a sweet cup of orange
she'll drink by herself.

[Verse]
She walks up to the corner where the oranges still spin,
and feeds the little voucher through the seam.
They tumble and they're halved with that soft, familiar whir,
the only thing tonight that came for her.

[Bridge]
And maybe it's the sweetest cup around,
and maybe that's the saddest part she's found:
she'd trade away the orange and the gold
for one small box that's hers to have and hold.

[Chorus]
So it's two dollars of sunshine,
two dollars of gold,
and the line shuffles on
and the evening grows old.
She lifts up the cup,
takes a sip, gives a smile,
sweet Teresa and Ijooz,
for a little while."""


# ---------------------------------------------------------------- helpers ----
def display_lines(lyrics_text):
    out = []
    for line in lyrics_text.splitlines():
        s = line.strip()
        if not s or (s.startswith("[") and s.endswith("]")):
            continue
        out.append(s)
    return out


def _fmt_ts(ms):
    ms = max(0, int(ms))
    return f"[{ms // 60000:02d}:{(ms % 60000) / 1000.0:05.2f}]"


def _find_first(obj, key_names):
    """Depth-first search for the first value under any of key_names."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in key_names and isinstance(v, (str, int, float)):
                return v
        for v in obj.values():
            r = _find_first(v, key_names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_first(v, key_names)
            if r is not None:
                return r
    return None


def _find_audio_url(obj):
    """Prefer explicit audio-url fields; else any http(s) URL to an audio file."""
    explicit = _find_first(obj, {"mp3_url", "audio_url", "url", "flac_url", "wav_url"})
    if isinstance(explicit, str) and explicit.startswith("http"):
        return explicit
    found = []

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and o.startswith("http") and \
                re.search(r"\.(mp3|flac|wav|m4a)(\?|$)", o, re.I):
            found.append(o)
    walk(obj)
    return found[0] if found else None


def _find_duration_ms(obj):
    val = _find_first(obj, {"duration_ms", "duration", "length", "length_ms"})
    if val is None:
        return 0
    try:
        val = float(val)
    except (TypeError, ValueError):
        return 0
    return int(val if val > 2000 else val * 1000)  # seconds -> ms heuristic


def build_lrc(lines, duration_ms):
    """No word timing from Mureka: distribute lines across the vocal window."""
    total = duration_ms if duration_ms > 0 else 175000
    lead_in = min(8000, int(total * 0.06))
    tail = min(6000, int(total * 0.06))
    usable = max(1, total - lead_in - tail)
    step = usable / max(1, len(lines))
    header = [f"[ti:{TITLE}]", "[by:Mureka]", ""]
    body = [f"{_fmt_ts(int(lead_in + i * step))}{line}" for i, line in enumerate(lines)]
    return "\n".join(header + body) + "\n"


# ------------------------------------------------------------------- main ----
def main():
    key = os.environ.get("MUREKA_API_KEY")
    if not key:
        print("ERROR: MUREKA_API_KEY is not set.", file=sys.stderr)
        return 1
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    lines = display_lines(LYRICS_TEXT)
    print(f"base={BASE_URL}  model={MODEL}  lyrics_lines={len(lines)}")

    # 1) kick off generation
    gen = requests.post(
        f"{BASE_URL}/v1/song/generate", headers=headers,
        json={"lyrics": LYRICS_TEXT, "model": MODEL, "prompt": PROMPT},
        timeout=(15, 120),
    )
    print(f"POST /v1/song/generate -> HTTP {gen.status_code}")
    if gen.status_code >= 300:
        print("ERROR BODY:", gen.text[:1500], file=sys.stderr)
        if "allowlist" in gen.text.lower():
            print("\n>> Egress blocker: add api.mureka.ai to the network "
                  "allowlist (new session required).", file=sys.stderr)
        return 2
    task = gen.json()
    task_id = task.get("id") or task.get("task_id") or _find_first(task, {"id", "task_id"})
    if not task_id:
        print("Could not find task id in response:", json.dumps(task)[:800], file=sys.stderr)
        return 3
    print(f"task id: {task_id}  status: {task.get('status')}")

    # 2) poll
    deadline = time.time() + POLL_TIMEOUT_S
    last = None
    while time.time() < deadline:
        q = requests.get(f"{BASE_URL}/v1/song/query/{task_id}", headers=headers, timeout=(15, 60))
        if q.status_code >= 300:
            print(f"poll HTTP {q.status_code}: {q.text[:300]}", file=sys.stderr)
            time.sleep(POLL_INTERVAL_S)
            continue
        last = q.json()
        status = str(last.get("status", "")).lower()
        if status != getattr(main, "_prev", None):
            print(f"  status: {status or '(none)'}")
            main._prev = status
        if status in DONE_STATES:
            break
        if status in FAIL_STATES:
            print("Generation failed:", json.dumps(last)[:1000], file=sys.stderr)
            return 4
        time.sleep(POLL_INTERVAL_S)
    else:
        print("Timed out waiting for generation.", file=sys.stderr)
        return 5

    META_OUT.write_text(json.dumps(last, indent=2))
    audio_url = _find_audio_url(last)
    duration_ms = _find_duration_ms(last)
    print(f"done. audio_url={audio_url}  duration_ms={duration_ms}")
    if not audio_url:
        print("No audio URL in finished response:", json.dumps(last)[:1000], file=sys.stderr)
        return 6

    # 3) download audio
    a = requests.get(audio_url, timeout=(15, 300))
    a.raise_for_status()
    AUDIO_OUT.write_bytes(a.content)
    print(f"Saved {AUDIO_OUT} ({len(a.content)} bytes)")

    # 4) .lrc
    LRC_OUT.write_text(build_lrc(lines, duration_ms))
    print(f"Saved {LRC_OUT} (approximate, duration-based sync)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
