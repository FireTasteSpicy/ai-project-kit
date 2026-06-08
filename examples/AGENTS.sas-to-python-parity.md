# AGENTS.md — worked example: a SAS→Python parity port

> A filled-in `AGENTS.md` for a legacy-migration project, to show the level of
> specificity that pays off. Copy the *shape*, not the contents. The lessons here
> are drawn from a real 115-commit port where most of the churn came from an
> undocumented parity contract and a blind feedback loop — exactly what sections
> 3, 4 and 6 below are designed to prevent.

## 1. What this project is

We are porting `legacy/sas/*.sas` to Python with **byte-for-byte output parity** as
the acceptance test. The Python output must match the SAS reference output exactly;
"looks equivalent" is not done. When in doubt, the SAS source is ground truth.

## 2. Stack & layout

- Python 3.11, polars, pytest.
- `stepN.py` — pipeline stages, run in order by `main.py`; each maps to a section of
  the SAS source (noted at the top of each file).
- `legacy/sas/` — reference implementation (read-only). Cite line numbers when you
  rely on a behavior, e.g. `hdrnb7200d.sas:6320`.
- `compare_outputs.py` — the parity oracle. `tests/fixtures/` — curated edge cases.

## 3. Commands

| Purpose | Command |
| --- | --- |
| Run pipeline | `python main.py <config>.yaml` |
| Compare to SAS | `python compare_outputs.py <out_dir>` |
| Run tests | `pytest -q` |
| Local parity test | `pytest -q tests/test_parity.py` |

Run `pytest -q` and the local parity test before declaring any change done.

## 4. The contract / invariants — what must never break

- **Row order is significant.** Outputs are compared positionally. Match the SAS sort
  keys *including tie-breaks* (e.g. DUPKEY ordering), not just the visible sort.
- **Whitespace & width are significant** — fixed-width fields are space-padded to
  exact widths; trailing spaces count.
- SAS missing values sort low (`.` before any number); replicate that, don't drop.
- Numeric formatting follows the SAS format (`BEST12.` etc.), not Python `repr`.
- A change that fixes one output file must not regress the others — the local parity
  fixtures cover all of them; keep them green.

## 5. Conventions

- Match the style of the stage file you're editing; don't reformat untouched lines.
- FWF schemas live inline in the step module that uses them, not in a shared file.
- Every parity fix cites the SAS line(s) it reproduces, in code comment + CHANGELOG.

## 6. Workflows — "fix a parity diff"

1. Run `compare_outputs.py`; identify the **first** differing stage, not just the
   final diff. Localize against per-stage SAS dumps before editing.
2. Add the failing case to `tests/fixtures/` and a regression test **first**.
3. Read the relevant SAS DATA step; reproduce its exact `BY`/`LAST.`/`MERGE`/`SET`
   semantics. Make the smallest change that passes.
4. Run the full suite + local parity. Then hand off for a prod-data run to confirm.
5. Append a CHANGELOG entry: symptom → SAS root cause (with line refs) → fix → tests.

## 7. Guardrails — do NOT

- Do NOT commit generated artifacts: run logs, `*_compare_logs.txt`, `*.parquet`.
- Do NOT commit anything under `tests/` unless explicitly asked.
- Do NOT invent the contents of a referenced-but-missing SAS include; flag it as an
  external dependency.
- Do NOT guess SAS behavior from the output diff alone when the source can be read —
  cite the source.

## 8. Glossary

| Term | Meaning |
| --- | --- |
| DUPKEY1/2 | SAS within-group de-dup sort keys; load-bearing for output order |
| N01 / N02 | verify-record type codes emitted per relationship |
| vfy16 | the verify-list build stage where in-law identity collapse occurs |
