# Parity migration playbook

The scaffolding that turns "an agent that sometimes produces a green diff" into "an
agent that reliably produces *correct* translations fast, without risking the data
boundary." Build these **before** scaling autonomy past a supervised loop. Ordered by
leverage; the first three are the ones to do even if you do nothing else.

---

## 1. Harden the oracle — it's the load-bearing wall
A green diff is only as trustworthy as the golden output. Autonomy amplifies a weak
oracle into prod faster.
- [ ] **Pair each golden output with the exact input snapshot that produced it**,
      checksummed, with provenance (legacy code version + run date). A golden output
      means nothing except relative to a frozen input.
- [ ] **Validate the diff tool legacy-vs-legacy first** — diff the golden against a
      re-run of itself; it must report **zero**. Don't debug the ruler and the
      measured thing at once.
- [ ] **Neutralise non-determinism** before comparing — embedded run-dates,
      timestamps, unstable tie-order. Otherwise you chase phantom diffs forever.
- [ ] **Audit golden coverage.** If the golden inputs lack the pathological rows
      (ties, missing values, the known edge cases), parity goes green and prod still
      breaks — a false green is worse than a red. Curate adversarial fixtures in.

## 2. Add a per-stage oracle, not just final-output
The single biggest debugging lever.
- [ ] While the legacy system still runs, **dump intermediate datasets** after each
      major step.
- [ ] Wire them as optional stage-level assertions so the agent localises to the
      **first** divergent stage instead of reverse-engineering a final diff through
      many transforms. 3 iterations to converge instead of 25.

## 3. Make the loop fast AND safe — synthetic fixtures
Resolves the "never put data in a prompt" vs "agent needs to iterate" tension by
construction.
- [ ] **Generate schema-shaped synthetic data** from the data dictionary — fake rows
      exercising the structure + edge cases, safe to keep local and in-prompt.
- [ ] Agent iterates the whole translate-test-fix loop on synthetic data; the **real
      golden diff runs only in-boundary in CI**. Fast unsupervised iteration *and* a
      hard guarantee real data never touches the model.

## 4. A blessed house library — don't let it re-derive
Biggest per-job consistency lever.
- [ ] Pre-build and unit-test the new-stack equivalents of the legacy common
      routines/macros (see the footguns in `sas-to-polars-mapping.md`).
- [ ] Instruct the agent to **import them, never re-implement**. One vetted fix
      propagates to every job instead of each translation re-botching the same
      primitive.

## 5. Loop control + reproducibility — before any unattended/batch run
Brakes and a flight recorder.
- [ ] **Stop conditions:** max-iteration cap, token/cost ceiling, and a *stuck
      detector* (no diff improvement over N iterations → escalate, don't burn budget).
- [ ] **Per-job isolation** — each job in its own branch/worktree so parallel runs
      don't collide.
- [ ] **Reproducibility/audit:** pin and log model version, instruction version,
      corpus version, and the full data-free prompt/response transcript per job — you
      will need to replay and explain anything that reaches prod.

## 6. Verification with teeth — beyond the green check
Green tests ≠ correct.
- [ ] **Mutation testing** — inject deliberate errors into a correct translation and
      confirm the tests/golden catch them. Proves the oracle has teeth.
- [ ] **Statistical/structural checks** as standing assertions — row counts, group
      totals, distributions, null rates — beyond exact match.
- [ ] **Adversarial reviewer pass** — a second agent (or strict rules checklist) that
      critiques the translation against the *business rules*, independent of whether
      tests pass.
- [ ] **Per-job footgun checklist** the agent must tick (the Top 5 in the mapping doc).

## 7. Keep the corpus alive — the learning loop
Stops the system re-litigating the same ambiguities.
- [ ] **Decision log** (`docs/ai/decision-log.md`): every escalation + its SME
      resolution recorded and folded back into the rules doc + AGENTS.md.
- [ ] **Regression growth:** every bug found in review or prod becomes a new golden
      edge-case + test.
- [ ] **Metrics:** iterations-to-green, escalation rate, post-MR human-edit rate, and
      mismatch *categories*. If 40% of mismatches are rounding, fix the mapping once,
      not per job.

## 8. Compliance as a mechanism, not a sentence
In a regulated/boundary context one leak is catastrophic; "the instructions say don't"
is not a control.
- [ ] **Prompt DLP gate** in the agent path that hard-blocks data-shaped payloads
      (UIN/NRIC/value regexes) before any egress.
- [ ] **No-data CI gate** that fails if a data file is staged (see
      `pre-commit-config.example.yaml`).
- [ ] **Audit trail** (from §5) retained for change-management/IM8.

## 9. The real acceptance gate — parallel run, then cutover
Golden parity is **necessary, not sufficient** — it only proves the frozen inputs.
- [ ] Run legacy + new **side-by-side in prod for N cycles**, diff live outputs, before
      decommissioning anything. Keep the legacy job as the rollback path.
- [ ] Define cutover criteria up front (e.g. K consecutive cycles within tolerance).
      That live parallel run, not the golden green, is what lets you retire the legacy.

---

### Autonomy ladder (where these apply)
1. **Assisted authoring** — completions/chat. Low leverage.
2. **Supervised agent loop** *(start here)* — needs §1–4. Agent translates, tests,
   diffs in-boundary, fixes to green; human owns merge.
3. **Batch/unattended translate-test-fix** — additionally needs §5–8 + a triage queue;
   merge/deploy stays human-gated.
4. **Fully autonomous end-to-end** — don't. Self-merge/deploy touches change control,
   and green never fully covers semantic edge cases. Cap at "autonomous translate +
   test, human-gated merge/deploy."
