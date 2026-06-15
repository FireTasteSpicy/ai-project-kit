#!/bin/bash
# SessionStart hook — preflight for the ElevenLabs "Teresa and Ijooz" song generation.
#
# What it does in a fresh Claude Code on the web session:
#   1. Installs the Python deps that scripts/generate_song.py needs (PyPI is in the
#      default Trusted allowlist, so this works even before egress to ElevenLabs).
#   2. Reports whether ELEVENLABS_API_KEY is present, whether api.elevenlabs.io is
#      reachable (i.e. egress is open), and whether the key is valid — so the agent
#      knows instantly whether it can generate the song or is still blocked.
#
# It NEVER contains a secret (reads the key from the env at runtime) and NEVER blocks
# the session (always exits 0). Synchronous by design: deps are guaranteed ready
# before the agent runs. Switch to async (see the skill) if you prefer faster start.
#
# NOTE: the egress allowlist is an ENVIRONMENT setting (Network access = Full, or
# Custom + api.elevenlabs.io) and CANNOT be changed by this hook or any repo file.
set -uo pipefail   # deliberately not -e: a failed preflight must not abort startup

# Web-only; do nothing in a local terminal session.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# 1) Generator dependencies (cached into the container after first run).
if python3 -m pip install --quiet --disable-pip-version-check elevenlabs requests >/dev/null 2>&1; then
  echo "[preflight] python deps ready (elevenlabs, requests)"
else
  echo "[preflight] WARN: pip install failed — check PyPI egress (pypi.org)"
fi

# 2) Key: prefer the persistent env secret. Fall back to ~/.elevenlabs_key if a
#    previous session left one (the container is ephemeral, so usually it won't).
if [ -z "${ELEVENLABS_API_KEY:-}" ] && [ -f "$HOME/.elevenlabs_key" ]; then
  export ELEVENLABS_API_KEY="$(cat "$HOME/.elevenlabs_key")"
  [ -n "${CLAUDE_ENV_FILE:-}" ] && echo "export ELEVENLABS_API_KEY='${ELEVENLABS_API_KEY}'" >> "$CLAUDE_ENV_FILE"
fi

# 3) Preflight: key presence -> reachability/validity.
if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "[preflight] (!) ELEVENLABS_API_KEY not set. Add it as an environment secret (persists"
  echo "[preflight]     across sessions) or paste it once, then re-run scripts/generate_song.py."
  exit 0
fi

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  https://api.elevenlabs.io/v1/user/subscription 2>/dev/null || echo "000")

case "$code" in
  200)
    echo "[preflight] OK ElevenLabs reachable & key valid — run: python scripts/generate_song.py"
    ;;
  401|403)
    if curl -s --max-time 8 -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
         https://api.elevenlabs.io/v1/user/subscription 2>/dev/null | grep -qi "not in allowlist"; then
      echo "[preflight] (!) EGRESS BLOCKED: api.elevenlabs.io is not allowlisted. In the environment's"
      echo "[preflight]     Network access, choose Full, or Custom + add api.elevenlabs.io, then start"
      echo "[preflight]     a NEW session (egress changes don't apply to a running session)."
    else
      echo "[preflight] (!) HTTP $code from ElevenLabs — key may be invalid or expired."
    fi
    ;;
  000)
    echo "[preflight] (!) Could not reach api.elevenlabs.io (timeout/DNS). Set Network access to Full/Custom."
    ;;
  *)
    echo "[preflight] (!) Unexpected HTTP $code from the ElevenLabs subscription endpoint."
    ;;
esac

exit 0
