#!/usr/bin/env python3
"""
generate_song.py — Generate "Teresa and Ijooz" with REAL SUNG VOCALS via the
ElevenLabs Music API, then write a time-synced .lrc lyric file.

Deliverables produced (in the repo root):
  - teresa_and_ijooz.mp3            the finished song
  - teresa_and_ijooz.lrc           time-synced lyrics
  - teresa_and_ijooz.metadata.json raw API metadata (for inspection / debugging)

------------------------------------------------------------------------------
PREREQUISITES (must hold in the session that RUNS this — see SESSION_HANDOFF.md):
  1. ELEVENLABS_API_KEY is exported in the environment.
  2. The environment's egress allowlist permits api.elevenlabs.io.
     Sanity check (expect HTTP 200 + subscription JSON):
       curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" \
            https://api.elevenlabs.io/v1/user/subscription
  3. The SDK is installed (PyPI is reachable):  pip install elevenlabs

HONEST CAVEAT: this script was prepared in a session that could NOT reach
api.elevenlabs.io, so the API call path is UNVERIFIED against the live service.
The Eleven Music API is new and may have shifted. Before fully trusting it,
glance at the live docs (reachable once egress is open):
  https://elevenlabs.io/docs/api-reference/music/compose-detailed
The composition-plan and .lrc logic below are API-version-independent.

Usage:
  python scripts/generate_song.py [--plan teresa_and_ijooz.plan.json]
                                  [--out teresa_and_ijooz]
                                  [--format mp3_44100_128]
------------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = REPO_ROOT / "teresa_and_ijooz.plan.json"
API_BASE = "https://api.elevenlabs.io"


# --------------------------------------------------------------------------- #
# Plan loading
# --------------------------------------------------------------------------- #
def load_plan(path: Path) -> dict:
    """Load the composition plan, dropping any leading underscore-comment keys."""
    raw = json.loads(path.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def plan_total_ms(plan: dict) -> int:
    return sum(int(s.get("durationMs", 0)) for s in plan.get("sections", []))


# --------------------------------------------------------------------------- #
# Generation — SDK path (preferred: can return word-level timestamps)
# --------------------------------------------------------------------------- #
def generate_with_sdk(api_key: str, plan: dict, output_format: str):
    """
    Returns (audio_bytes, metadata_dict). metadata_dict may carry word timestamps.
    Raises ImportError if the SDK is absent, or any SDK error to trigger fallback.
    """
    from elevenlabs.client import ElevenLabs  # type: ignore

    client = ElevenLabs(api_key=api_key)

    # The "detailed" call returns audio + metadata (and word timestamps for the
    # sung vocal when requested). Param/method names per the docs; if a name has
    # drifted, the HTTP fallback still produces both deliverables.
    print("[sdk] calling music.compose_detailed(...) with composition_plan", flush=True)
    result = client.music.compose_detailed(
        composition_plan=plan,
        output_format=output_format,
    )

    audio = _extract_audio_bytes(result)
    meta = _extract_metadata(result)
    return audio, meta


def _extract_audio_bytes(result) -> bytes:
    """Be liberal: the SDK may expose audio as .audio, .audio_bytes, or an iterator."""
    for attr in ("audio", "audio_bytes", "audio_output"):
        val = getattr(result, attr, None)
        if isinstance(val, (bytes, bytearray)):
            return bytes(val)
        if val is not None and hasattr(val, "__iter__") and not isinstance(val, (str, dict)):
            return b"".join(chunk for chunk in val)
    # result itself might be a bytes iterator
    if hasattr(result, "__iter__") and not isinstance(result, (str, bytes, dict)):
        return b"".join(chunk for chunk in result)
    if isinstance(result, (bytes, bytearray)):
        return bytes(result)
    raise RuntimeError("Could not locate audio bytes on the SDK response object.")


def _extract_metadata(result) -> dict:
    """Pull whatever JSON/metadata the SDK attached, for .lrc + the record."""
    for attr in ("json", "metadata", "song_metadata", "model_dump"):
        val = getattr(result, attr, None)
        if callable(val):
            try:
                val = val()
            except Exception:
                continue
        if isinstance(val, dict):
            return val
    return {}


# --------------------------------------------------------------------------- #
# Generation — raw HTTP fallback (reliable audio; .lrc from section timing)
# --------------------------------------------------------------------------- #
def generate_with_http(api_key: str, plan: dict, output_format: str):
    """Plain /v1/music returns raw audio bytes. No word timestamps -> .lrc comes
    from the plan's section durations (still section-synced)."""
    import requests  # stdlib-adjacent; present in most envs, else: pip install requests

    url = f"{API_BASE}/v1/music"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    body = {"composition_plan": plan, "output_format": output_format}
    print(f"[http] POST {url} (composition_plan)", flush=True)
    resp = requests.post(url, headers=headers, json=body, timeout=600)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.content, {}


# --------------------------------------------------------------------------- #
# .lrc construction
# --------------------------------------------------------------------------- #
def _fmt_lrc_time(ms: float) -> str:
    ms = max(0, int(round(ms)))
    minutes = ms // 60000
    seconds = (ms % 60000) / 1000.0
    return f"[{minutes:02d}:{seconds:05.2f}]"


def all_lines(plan: dict):
    """Flat list of (line_text) for every sung line, in order."""
    out = []
    for s in plan.get("sections", []):
        out.extend(s.get("lines", []) or [])
    return out


def find_word_timestamps(meta: dict):
    """
    Hunt for a word-timestamp array anywhere in the metadata. Accepts a few shapes:
      [{"text"/"word": "...", "start"/"start_time": <s or ms>, "end": ...}, ...]
    Returns list of (word, start_ms) or None.
    """
    def walk(node):
        if isinstance(node, list):
            if node and isinstance(node[0], dict) and (
                ("start" in node[0] or "start_time" in node[0])
                and ("word" in node[0] or "text" in node[0])
            ):
                return node
            for item in node:
                found = walk(item)
                if found:
                    return found
        elif isinstance(node, dict):
            for v in node.values():
                found = walk(v)
                if found:
                    return found
        return None

    arr = walk(meta)
    if not arr:
        return None

    def to_ms(v):
        v = float(v)
        return v * 1000.0 if v < 1000 else v  # seconds vs ms heuristic

    words = []
    for w in arr:
        text = w.get("word", w.get("text", "")).strip()
        start = w.get("start", w.get("start_time"))
        if text and start is not None:
            words.append((text, to_ms(start)))
    return words or None


def lrc_from_word_timestamps(lines, words) -> list[str]:
    """Greedily assign timestamped words to lyric lines by word count; each line's
    timestamp is its first word's start time."""
    out = []
    wi = 0
    for line in lines:
        n = max(1, len(line.split()))
        if wi < len(words):
            start_ms = words[wi][1]
        elif out:
            start_ms = words[-1][1] if words else 0
        else:
            start_ms = 0
        out.append(f"{_fmt_lrc_time(start_ms)}{line}")
        wi += n
    return out


def lrc_from_sections(plan: dict) -> list[str]:
    """Distribute each section's duration across its lines (weighted by length),
    starting at the section's cumulative offset. Instrumental sections just
    advance the clock."""
    out = []
    cursor = 0.0
    for s in plan.get("sections", []):
        dur = float(s.get("durationMs", 0))
        lines = s.get("lines", []) or []
        if not lines:
            cursor += dur
            continue
        weights = [max(1, len(ln)) for ln in lines]
        total_w = sum(weights)
        t = cursor
        for ln, w in zip(lines, weights):
            out.append(f"{_fmt_lrc_time(t)}{ln}")
            t += dur * (w / total_w)
        cursor += dur
    return out


def build_lrc(plan: dict, meta: dict, title: str) -> str:
    header = [
        "[ti:Teresa and Ijooz]",
        "[ar:ElevenLabs Music]",
        "[al:Teresa and Ijooz (single)]",
        f"[length:{_fmt_lrc_time(plan_total_ms(plan)).strip('[]')}]",
        "[by:generate_song.py]",
    ]
    words = find_word_timestamps(meta)
    if words:
        print(f"[lrc] using {len(words)} word-level timestamps from the API", flush=True)
        body = lrc_from_word_timestamps(all_lines(plan), words)
    else:
        print("[lrc] no word timestamps in response; deriving from section timing", flush=True)
        body = lrc_from_sections(plan)
    return "\n".join(header + body) + "\n"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the 'Teresa and Ijooz' song + .lrc")
    ap.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--out", default="teresa_and_ijooz", help="output basename")
    ap.add_argument("--format", dest="fmt", default="mp3_44100_128",
                    help="output_format, e.g. mp3_44100_128 (192 needs Creator tier)")
    args = ap.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY is not set. Export it first (see SESSION_HANDOFF.md).",
              file=sys.stderr)
        return 2

    if not args.plan.exists():
        print(f"ERROR: plan not found: {args.plan}", file=sys.stderr)
        return 2

    plan = load_plan(args.plan)
    print(f"[plan] {len(plan.get('sections', []))} sections, "
          f"~{plan_total_ms(plan)/1000:.0f}s target", flush=True)

    audio, meta = None, {}
    try:
        audio, meta = generate_with_sdk(api_key, plan, args.fmt)
        print("[ok] generated via SDK", flush=True)
    except ImportError:
        print("[warn] elevenlabs SDK not installed; falling back to raw HTTP", flush=True)
    except Exception as e:  # noqa: BLE001 — fall back on any SDK error
        print(f"[warn] SDK path failed ({e}); falling back to raw HTTP", flush=True)

    if audio is None:
        audio, meta = generate_with_http(api_key, plan, args.fmt)
        print("[ok] generated via raw HTTP", flush=True)

    mp3_path = REPO_ROOT / f"{args.out}.mp3"
    lrc_path = REPO_ROOT / f"{args.out}.lrc"
    meta_path = REPO_ROOT / f"{args.out}.metadata.json"

    mp3_path.write_bytes(audio)
    print(f"[saved] {mp3_path}  ({len(audio)} bytes)", flush=True)

    if meta:
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        print(f"[saved] {meta_path}", flush=True)

    lrc_path.write_text(build_lrc(plan, meta, args.out))
    print(f"[saved] {lrc_path}", flush=True)

    print("\nDone. Deliver the .mp3 and .lrc to the user (SendUserFile) and commit them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
