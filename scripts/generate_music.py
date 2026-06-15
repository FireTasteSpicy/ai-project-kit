#!/usr/bin/env python3
"""Generate the "Teresa and Ijooz" ballad with real sung vocals via the
ElevenLabs Music API, and write a time-synced .lrc alongside the audio.

STATUS / BLOCKER
----------------
The ElevenLabs **Music API requires a paid plan**. Running this on a free-tier
key returns HTTP 402:

    {"detail": {"type": "payment_required", "code": "paid_plan_required",
     "message": "Music API is not available for free users. Please upgrade
     to a paid plan to use the API."}}

The configured key, network egress, and request shape are all verified working
(auth returns 200). The only thing needed to produce the song is a key on a
paid ElevenLabs plan (Starter tier or above includes Music API access).

USAGE
-----
    export ELEVENLABS_API_KEY=...   # must be a PAID-plan key
    python3 scripts/generate_music.py

Outputs (written to the repo root):
    teresa_and_ijooz.mp3
    teresa_and_ijooz.lrc

The script calls POST /v1/music/detailed with with_timestamps=true, which
returns a multipart/mixed body: a JSON part (song_metadata + per-word
timestamps) and the binary audio part. The .lrc is built from those word
timestamps; if alignment can't be established it falls back to linear
interpolation across the song duration.

Requires: requests  (pip install requests)
"""
import os
import re
import sys
import json
import email
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_OUT = REPO_ROOT / "teresa_and_ijooz.mp3"
LRC_OUT = REPO_ROOT / "teresa_and_ijooz.lrc"
META_OUT = Path("/tmp/teresa_music_meta.json")  # raw metadata, for debugging

# ---- Generation settings ---------------------------------------------------
API_BASE = "https://api.elevenlabs.io"
ENDPOINT = "/v1/music/detailed"
OUTPUT_FORMAT = "mp3_44100_128"   # free-tier-allowed; 192k+ needs Creator tier
MODEL_ID = "music_v1"             # or "music_v2"
MUSIC_LENGTH_MS = 175_000         # ~2:55 — fits all lyrics at a slow ballad pace
TITLE = "Teresa and Ijooz"

# Style direction sent as the prompt (<= 4100 chars). Mirrors the production
# notes at the top of teresa_and_ijooz_lyrics.txt.
PROMPT = (
    "Mellow, melancholic indie folk-pop ballad with a real sung female lead vocal. "
    "Soft, intimate, slightly breathy voice on the verge of tears. Gentle fingerpicked "
    "acoustic guitar and felt piano, warm sustained strings, light brushed percussion "
    "entering in the later half. Slow tempo around 68 BPM, key of D minor. Tender and "
    "wistful in the verses, swelling just a little in the final chorus, then settling "
    "soft. Bittersweet and emotionally moving — the kind of song that makes you "
    "want to cry."
)

# Lyrics sent to the model (<= 4000 chars), with [section] tags so it sings the
# structure. The plain display lines used for the .lrc are derived from this.
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


def display_lines(lyrics_text: str) -> list[str]:
    """Lyric lines for the .lrc: drop [section] tags and blank lines."""
    out = []
    for line in lyrics_text.splitlines():
        s = line.strip()
        if not s or (s.startswith("[") and s.endswith("]")):
            continue
        out.append(s)
    return out


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9']", "", word.lower())


def _fmt_ts(ms: int) -> str:
    ms = max(0, int(ms))
    minutes = ms // 60000
    seconds = (ms % 60000) / 1000.0
    return f"[{minutes:02d}:{seconds:05.2f}]"


def build_lrc(words: list[dict], lines: list[str], duration_ms: int) -> str:
    """Build .lrc text by aligning each lyric line's first word to the sung
    word stream. Unmatched lines get a linearly interpolated timestamp."""
    tokens = [(_norm(w["word"]), int(w["start_ms"])) for w in (words or [])
              if _norm(w.get("word", ""))]
    n = len(tokens)

    starts: list[int | None] = []
    pos = 0
    for line in lines:
        lw = [_norm(x) for x in line.split() if _norm(x)]
        if not lw:
            starts.append(None)
            continue
        # find first word of the line at/after pos
        found = None
        scan = pos
        while scan < n:
            if tokens[scan][0] == lw[0]:
                found = scan
                break
            scan += 1
        if found is None:
            starts.append(None)
            continue
        starts.append(tokens[found][1])
        # advance pos past this line's words (best effort)
        consume, li = found, 0
        while consume < n and li < len(lw):
            if tokens[consume][0] == lw[li]:
                li += 1
            consume += 1
        pos = consume

    # Fill gaps by linear interpolation between known anchors (or across the
    # full duration if there are no anchors at all).
    total = duration_ms if duration_ms > 0 else (tokens[-1][1] + 4000 if tokens else 0)
    known = [(i, t) for i, t in enumerate(starts) if t is not None]
    if not known:
        step = total / max(1, len(lines))
        starts = [int(i * step) for i in range(len(lines))]
    else:
        # before first anchor
        first_i, first_t = known[0]
        for i in range(first_i):
            starts[i] = int(first_t * (i + 1) / (first_i + 1))
        # between anchors
        for (ai, at), (bi, bt) in zip(known, known[1:]):
            gap = bi - ai
            for k in range(1, gap):
                starts[ai + k] = int(at + (bt - at) * k / gap)
        # after last anchor
        last_i, last_t = known[-1]
        tail = total if total > last_t else last_t + 3000
        rem = len(lines) - last_i - 1
        for k in range(1, rem + 1):
            starts[last_i + k] = int(last_t + (tail - last_t) * k / (rem + 1))

    header = [f"[ti:{TITLE}]", "[by:ElevenLabs Music]", ""]
    body = [f"{_fmt_ts(t)}{line}" for t, line in zip(starts, lines)]
    return "\n".join(header + body) + "\n"


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        print("ERROR: ELEVENLABS_API_KEY is not set.", file=sys.stderr)
        return 1

    lines = display_lines(LYRICS_TEXT)
    print(f"prompt: {len(PROMPT)}/4100 chars   lyrics: {len(LYRICS_TEXT)}/4000 chars   lines: {len(lines)}")

    body = {
        "prompt": PROMPT,
        "lyrics_text": LYRICS_TEXT,
        "music_length_ms": MUSIC_LENGTH_MS,
        "model_id": MODEL_ID,
        "with_timestamps": True,
    }
    print(f"POST {ENDPOINT}?output_format={OUTPUT_FORMAT}  (model={MODEL_ID}, len={MUSIC_LENGTH_MS}ms)")
    r = requests.post(
        f"{API_BASE}{ENDPOINT}",
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=(15, 600),
    )
    ctype = r.headers.get("Content-Type", "")
    print(f"HTTP {r.status_code}  Content-Type: {ctype}  bytes: {len(r.content)}")

    if r.status_code != 200:
        try:
            print("ERROR BODY:", json.dumps(r.json(), indent=2)[:2000], file=sys.stderr)
        except Exception:
            print("ERROR BODY (raw):", r.content[:2000], file=sys.stderr)
        if r.status_code == 402:
            print("\n>> This is the paid-plan blocker. Use a key on a paid "
                  "ElevenLabs plan (Starter+) to generate.", file=sys.stderr)
        return 2

    if "multipart" not in ctype:
        print("Unexpected non-multipart 200; first 500 bytes:", r.content[:500], file=sys.stderr)
        return 3

    raw = b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + r.content
    msg = email.message_from_bytes(raw)
    meta, audio = None, None
    for part in msg.walk():
        pct = part.get_content_type()
        if pct == "application/json":
            meta = json.loads(part.get_payload(decode=True))
        elif pct.startswith("audio/"):
            audio = part.get_payload(decode=True)

    if not audio:
        print("No audio part in response.", file=sys.stderr)
        return 4

    AUDIO_OUT.write_bytes(audio)
    print(f"Saved {AUDIO_OUT}  ({len(audio)} bytes)")

    words = (meta or {}).get("words_timestamps") or []
    duration_ms = (words[-1]["end_ms"] + 3000) if words else 0
    if meta is not None:
        META_OUT.write_text(json.dumps(meta, indent=2))
        print(f"Saved raw metadata {META_OUT}  (word timestamps: {len(words)})")

    lrc = build_lrc(words, lines, duration_ms)
    LRC_OUT.write_text(lrc)
    print(f"Saved {LRC_OUT}")
    if not words:
        print("NOTE: no word timestamps returned; .lrc uses interpolated timings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
