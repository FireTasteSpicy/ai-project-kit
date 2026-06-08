# AGENTS.md overlay — legacy-parity-migration

Merge these sections into your project's `AGENTS.md` (they refine the generic ones for
an oracle-driven port). Fill every `<!-- TODO -->`; delete this file once merged.

---

## 4. The contract / invariants  (parity port)

The acceptance test is **match the known-good reference output**, not "looks
equivalent." The golden output is ground truth; when in doubt, read the legacy source
— don't guess from the diff.

- **Tolerance is defined, not assumed.** <!-- TODO: e.g. abs 1e-9 / rel 1e-6, per
  column where needed. --> Bit-exactness is NOT the contract unless stated.
- **Row order** is <!-- TODO: significant / not significant -->. If significant,
  reproduce the legacy sort keys *including tie-breaks*, not just the visible sort.
- **Whitespace & field width** are <!-- TODO: significant for fixed-width outputs -->;
  trailing spaces and padding count.
- **Missing values** sort and propagate per legacy semantics (see mapping doc), not the
  new stack's defaults.
- A fix to one output must not regress another — **all** golden fixtures stay green.

## 6. Workflow — the parity loop

1. Run the comparison; find the **first divergent stage** (use per-stage reference
   dumps), don't debug from the final diff alone.
2. Add the failing case as a fixture + regression test **first**.
3. Read the legacy source for that stage and reproduce its exact semantics
   (see `docs/ai/sas-to-polars-mapping.md`). Make the smallest change that passes.
4. Iterate on **synthetic fixtures** (fast, safe to keep local/in-prompt); the real
   golden diff runs **in-boundary in CI** as the gate.
5. Full suite green → handoff note → human opens/approves MR → CI re-validates.

## 7. Guardrails — do NOT  (parity additions)

- Do NOT re-implement a legacy primitive that exists in the blessed house library —
  import it (missing-value handling, date epoch, dedup, rounding, positional merge).
- Do NOT put real data values in a prompt, log, or commit. Work on schema + synthetic
  fixtures; comparisons run in-boundary and surface only pass/fail + structural diffs.
- Do NOT treat a green diff as "correct" — it only proves parity on the frozen inputs
  (see playbook: coverage, mutation testing, statistical checks).
- Do NOT infer legacy behaviour from the diff when the source can be read — cite the line.

## 8. Stop & escalate  (parity additions)

- Rules are silent/contradictory on a case → escalate to the SME; don't invent.
- Golden mismatch persists with no net progress after <!-- TODO: N --> iterations.
- Any request to touch scheduling/deploy, or to access data beyond schema.

## 9. Definition of done  (parity port)

- [ ] Tests + lint green; golden match within tolerance on **all** fixtures.
- [ ] Edge-case fixtures (ties, missing values, the known pathological rows) covered.
- [ ] No data in prompt/log/commit; only structural/aggregate diffs surfaced.
- [ ] Handoff note: legacy line refs, assumptions, rule gaps (→ `docs/ai/decision-log.md`).
