# Decision log

The project's memory for judgment calls. Whenever the spec/rules were **silent or
ambiguous** and a decision was made (by a human or escalated to an SME), record it
here — then fold the resolution back into the rules doc and `AGENTS.md` so the same
ambiguity never costs a second escalation. This is the loop that keeps the instruction
corpus alive instead of letting the agent re-litigate the same gaps.

Append-only; newest first.

| Date | Area / job | The gap (rule was silent on…) | Decision | Decided by | Folded back into |
|------|------------|-------------------------------|----------|------------|------------------|
| <!-- YYYY-MM-DD --> | | | | | |

<!--
Example row:
| 2026-06-10 | verify-list dedup | legacy rule didn't state tie-break when two rows share all keys | keep the row with the later effective date; document as a sort tie-break | SME (J. Tan) | AGENTS.md §4 + sas-to-polars-mapping.md |
-->
