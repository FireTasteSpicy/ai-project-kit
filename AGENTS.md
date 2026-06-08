# AGENTS.md

> **This is the single source of truth for AI coding assistants in this repo.**
> It is vendor-neutral. Cursor, OpenAI Codex, Zed, Aider and others read this file
> directly. GitHub Copilot, Claude Code and Windsurf read thin pointer files that
> redirect here (see `adapters/`). **Edit this file only — never duplicate rules into
> the pointer files.**
>
> Fill in every `<!-- TODO -->`. Delete sections that don't apply. Keep it short:
> an instruction file that is skimmable gets followed; a 500-line one gets ignored.

---

## 1. What this project is

<!-- TODO: 2-4 sentences. What does this codebase do, and for whom? What is the
     single most important thing an assistant should understand before touching it? -->

## 2. Stack & layout

<!-- TODO: languages, frameworks, package manager, and the 5-10 directories/files
     that matter. Point at the entry points. Example:
     - Python 3.11, polars, pytest. Package manager: uv.
     - `src/pipeline/` — the N processing stages, run in order by `main.py`.
     - `legacy/` — the reference implementation we are porting from (read-only).
     - `tests/` — fixtures + regression tests. -->

## 3. Commands

> Assistants should run these themselves to self-verify. Keep them copy-pasteable.

| Purpose | Command |
| --- | --- |
| Install deps | <!-- TODO --> |
| Run the app | <!-- TODO --> |
| Run tests | <!-- TODO --> |
| Lint / typecheck | <!-- TODO --> |
| Format | <!-- TODO --> |

**Always run tests (and lint) before declaring a change done.**

## 4. The contract / invariants — what must never break

<!-- TODO: This is the highest-value section. State the properties that define
     "correct" so the assistant validates against them instead of discovering them
     by trial and error. Be explicit about anything that is easy to get subtly wrong.
     Examples:
     - Output parity: row order is significant; floats compared to 1e-9; trailing
       whitespace is significant.
     - Public API in `src/api/` is frozen; changing a signature is a breaking change.
     - Migrations are append-only; never edit an applied migration.
     If you don't know the contract yet, writing it down is your first task. -->

## 5. Conventions

<!-- TODO: only the rules that are NON-obvious or that you keep having to repeat.
     Don't restate language defaults. Examples:
     - Match the style of the file you're editing; don't reformat untouched lines.
     - Schemas live inline in the module that uses them, not in a shared file.
     - Use the project's blessed/shared helpers; don't re-derive a primitive that
       already exists (one vetted fix should propagate, not be re-botched per file).
     - Prefer pure functions; side effects only in `main.py`. -->

## 6. Workflows — repeated rituals

<!-- TODO: describe the loops the assistant will run many times, as numbered steps,
     so they're done consistently. Example "fix a failing case":
     1. Reproduce locally with `<command>`.
     2. Localize the failing stage against the reference output before editing.
     3. Add/extend a regression test that captures the case FIRST.
     4. Make the smallest change that passes; run the full suite.
     5. Record the change in CHANGELOG.md using the existing entry format. -->

## 7. Guardrails — do NOT

<!-- TODO: hard "don't"s. Make these mechanical where possible (a pre-commit hook is
     stronger than a sentence). Examples:
     - Do NOT commit generated artifacts (logs, build output, `*.parquet`).
     - Do NOT commit anything under `tests/` unless explicitly asked.
     - Do NOT invent an implementation for a referenced-but-missing file; flag it as
       an external dependency instead.
     - Do NOT push, deploy, or run destructive commands without explicit approval. -->

## 8. Stop & escalate — when NOT to guess

<!-- TODO: the conditions under which the assistant must STOP and ask a human rather
     than guess, and where to route. Autonomy is only safe when the agent escalates
     on ambiguity instead of inventing an answer. Examples:
     - The spec/rules are silent or self-contradictory on a case you hit.
     - Output still mismatches the reference after N attempts with no net progress.
     - A change would touch deploy, scheduling, migrations, secrets, or prod data.
     - Anything that would send real data outside the trust boundary.
     Route via: MR/PR comment or tracked issue to a named owner — never external email. -->

## 9. Definition of done

<!-- TODO: the explicit checklist that means "finished", so the agent self-verifies
     before handoff. Example:
     - [ ] Tests + lint + typecheck green (commands in §3).
     - [ ] Output matches the reference within the agreed tolerance (§4).
     - [ ] No guardrail violation (§7); nothing data-bearing committed or prompted.
     - [ ] Handoff note: what changed, assumptions made, rules that were silent. -->

## 10. Glossary

<!-- TODO: domain terms / acronyms an assistant won't know from the code alone.
     A 6-line table here prevents a lot of misread code. -->

---

<!-- Keep deeper material in `docs/ai/*.md` and link to it from here rather than
     inlining, once this file grows past ~150 lines. -->
