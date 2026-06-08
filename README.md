# AI Project Kit

A reusable, **vendor-neutral** starter for giving AI coding assistants a single,
consistent set of project instructions — so you write your rules **once** and Cursor,
GitHub Copilot, Claude Code, Windsurf, OpenAI Codex, Zed, Aider and others all follow
them.

## The idea

```
        ┌─────────────┐
        │  AGENTS.md  │   ← the ONE file you edit (vendor-neutral, open standard)
        └──────┬──────┘
   ┌───────────┼───────────────┬──────────────┐
   ▼           ▼               ▼              ▼
 CLAUDE.md  .github/        .cursor/      .windsurf/      ← one-line pointer files
            copilot-…       rules/…       rules/…           ("read AGENTS.md")
```

`AGENTS.md` ([agents.md](https://agents.md)) is an emerging open standard read
natively by a growing list of tools. The assistants that still look for their own
filename get a **thin pointer file** that just says "read AGENTS.md." No rule is ever
written twice, so the tools can't drift out of sync.

## What's inside

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | The canonical instruction template. **The only file you fill in.** 10 sections incl. the contract/invariants, stop-and-escalate, and definition-of-done. |
| `adapters/` | One-line pointer files per tool (see `adapters/README.md`). |
| `templates/` | Reusable, vendor-neutral artifacts: a safety-first `.gitignore`, PR/MR template, decision log, pre-commit guardrails. |
| `profiles/` | Opt-in specialisations for a project *type* (see below). |
| `examples/` | A filled-in `AGENTS.md` for a real migration, for reference. |
| `scripts/install.sh` | Drops the kit (and an optional profile) into a target repo. |
| `.editorconfig` | Tool-agnostic whitespace/encoding baseline (stops AI diffs churning). |

## Use it on a new project

```bash
# generic
scripts/install.sh /path/to/your-repo

# with a specialisation
scripts/install.sh /path/to/your-repo --profile legacy-parity-migration
```

Then open `your-repo/AGENTS.md`, fill in the `<!-- TODO -->` sections, and follow the
printed next-steps. The pointer files already redirect every assistant to `AGENTS.md`.
Re-run with `--force` to overwrite. Prefer doing it by hand? Copy `AGENTS.md` to your
repo root and copy each file in `adapters/` to the path listed in `adapters/README.md`.

## Profiles

A profile layers project-type-specific guidance on top of the generic core, installed
into `docs/ai/`.

| Profile | For |
| --- | --- |
| `legacy-parity-migration` | Porting a legacy system to a new stack where a known-good output is the oracle (SAS→Polars, COBOL→Java, …). Ships an AGENTS overlay, a SAS→Polars footgun mapping, and an operational playbook (oracle hardening, synthetic fixtures, loop control, verification-with-teeth, compliance, parallel-run cutover). |

Add your own under `profiles/<name>/`; any `*.md` (except its `README.md`) installs
into the target's `docs/ai/`.

## Which tools need a pointer?

| Tool | How it finds instructions |
| --- | --- |
| Cursor, OpenAI Codex, Zed, Aider | Read `AGENTS.md` natively — no pointer needed |
| GitHub Copilot | `.github/copilot-instructions.md` pointer |
| Claude Code | `CLAUDE.md` pointer |
| Windsurf | `.windsurf/rules/agents.md` pointer |

Native `AGENTS.md` support is spreading, so this list ages in your favour. If a tool
ignores `AGENTS.md`, add a one-line pointer under `adapters/` — never split your rules.

> **Alternative — symlinks.** You could `ln -s AGENTS.md CLAUDE.md` etc. More DRY, but
> symlinks are fragile across the Windows↔WSL boundary and some tools don't follow
> them, so this kit uses small pointer files, which work everywhere.

## How to write a good AGENTS.md

1. **Keep it skimmable.** Under ~150 lines. Push depth into `docs/ai/*.md` and link.
2. **Lead with the contract** (§4) — the invariants that define "correct." Most wasted
   AI iterations come from a rule the assistant had to discover by trial.
3. **Make commands runnable** (§3) so the assistant self-verifies instead of guessing.
4. **Say when to stop** (§8) — autonomy is only safe when the agent escalates on
   ambiguity instead of inventing an answer.
5. **Prefer mechanical enforcement** for guardrails — a pre-commit hook or CI gate
   beats a sentence. Use AGENTS.md for the *why*, hooks/CI for the *can't*.
6. **Only write non-obvious rules.** Every line should earn its place or it dilutes
   the rest.
