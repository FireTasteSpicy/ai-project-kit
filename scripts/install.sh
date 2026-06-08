#!/usr/bin/env bash
#
# Install the AI project kit into a target repository.
#
# Copies the canonical AGENTS.md, the per-tool pointer files, the .editorconfig, and
# the reusable templates. With --profile, also installs a specialization overlay.
# Idempotent: existing files are skipped unless --force is given.
#
# Usage:
#   scripts/install.sh <target-repo> [--profile <name>] [--force]
#
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  local profiles
  profiles="$(ls "$KIT_DIR/profiles" 2>/dev/null | tr '\n' ' ')"
  cat >&2 <<EOF
Usage: $0 <target-repo> [--profile <name>] [--force]

  --profile <name>   also install profiles/<name>/ into docs/ai/
                     available: ${profiles:-<none>}
  --force            overwrite files that already exist
EOF
}

TARGET="" PROFILE="" FORCE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --force)   FORCE="--force"; shift ;;
    -h|--help) usage; exit 0 ;;
    -*)        echo "unknown option: $1" >&2; usage; exit 1 ;;
    *)         TARGET="$1"; shift ;;
  esac
done

if [[ -z "$TARGET" ]]; then usage; exit 1; fi
if [[ ! -d "$TARGET" ]]; then echo "error: target '$TARGET' is not a directory" >&2; exit 1; fi

place() {
  # place <src-relative-to-kit> <dest-relative-to-target>
  local src="$KIT_DIR/$1" dest="$TARGET/$2"
  if [[ ! -e "$src" ]]; then echo "  MISSING $1 (not in kit)"; return; fi
  mkdir -p "$(dirname "$dest")"
  if [[ -e "$dest" && "$FORCE" != "--force" ]]; then
    echo "  skip   $2 (exists; --force to overwrite)"; return
  fi
  cp "$src" "$dest"
  echo "  place  $2"
}

echo "Installing AI project kit into: $TARGET"
# Core
place "AGENTS.md"                                "AGENTS.md"
place "adapters/CLAUDE.md"                       "CLAUDE.md"
place "adapters/github/copilot-instructions.md"  ".github/copilot-instructions.md"
place "adapters/cursor/rules/00-agents.mdc"      ".cursor/rules/00-agents.mdc"
place "adapters/windsurf/rules/agents.md"        ".windsurf/rules/agents.md"
place ".editorconfig"                            ".editorconfig"
place "templates/gitignore"                      ".gitignore"
# Reusable templates (land in docs/ai/ for you to place/wire)
place "templates/PULL_REQUEST_TEMPLATE.md"       "docs/ai/PULL_REQUEST_TEMPLATE.md"
place "templates/decision-log.md"                "docs/ai/decision-log.md"
place "templates/pre-commit-config.example.yaml" "docs/ai/pre-commit-config.example.yaml"

# Optional profile
if [[ -n "$PROFILE" ]]; then
  PDIR="profiles/$PROFILE"
  if [[ ! -d "$KIT_DIR/$PDIR" ]]; then
    echo "error: unknown profile '$PROFILE' (see $KIT_DIR/profiles/)" >&2; exit 1
  fi
  echo "Applying profile: $PROFILE"
  for f in "$KIT_DIR/$PDIR"/*.md; do
    base="$(basename "$f")"
    [[ "$base" == "README.md" ]] && continue
    place "$PDIR/$base" "docs/ai/$base"
  done
fi

cat <<EOF

Done. Next steps:
  1. Fill in the <!-- TODO --> sections in $TARGET/AGENTS.md  (the only file you edit).
  2. Move docs/ai/PULL_REQUEST_TEMPLATE.md to your host's path
     (GitHub: .github/  GitLab: .gitlab/merge_request_templates/).
  3. Wire docs/ai/pre-commit-config.example.yaml into pre-commit + CI.
  *. If .gitignore already existed it was SKIPPED (not overwritten) — merge the kit's
     entries from templates/gitignore by hand so you don't lose your own.
EOF
if [[ -n "$PROFILE" ]]; then
  cat <<EOF
  4. Merge docs/ai/AGENTS.overlay.md into AGENTS.md, then delete the overlay.
  5. Add docs/ai/*-mapping.md to your assistant's retrieval corpus.
  6. Work through docs/ai/parity-playbook.md before scaling autonomy.
EOF
fi
