# adapters/

Thin **pointer files**. Each redirects one assistant to the root `AGENTS.md` so you
write your rules once and every tool obeys them. They contain no project rules
themselves — that's the whole point.

`scripts/install.sh` copies these into the paths each tool expects:

| File here | Installs to | Read by |
| --- | --- | --- |
| `CLAUDE.md` | `<repo>/CLAUDE.md` | Claude Code |
| `github/copilot-instructions.md` | `<repo>/.github/copilot-instructions.md` | GitHub Copilot |
| `cursor/rules/00-agents.mdc` | `<repo>/.cursor/rules/00-agents.mdc` | Cursor |
| `windsurf/rules/agents.md` | `<repo>/.windsurf/rules/agents.md` | Windsurf |

Tools that read `AGENTS.md` natively (Cursor, OpenAI Codex, Zed, Aider, and others)
need no pointer — they're covered by the root file directly. Pointers exist for the
tools that look for their own filename. Tool support changes fast; if an assistant
ignores `AGENTS.md`, add a one-line pointer for it here rather than splitting content.

**Pointer, not copy:** keep these one line of "read AGENTS.md." If you ever feel the
urge to put a real rule in a pointer file, put it in `AGENTS.md` instead.
