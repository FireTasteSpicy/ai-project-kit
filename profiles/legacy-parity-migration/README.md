# Profile: legacy-parity-migration

For porting a legacy system to a new stack where a **known-good output is the oracle**
— SAS → Python/Polars, COBOL → Java, a stored-proc → service rewrite — validated
against golden outputs. Optimised for an agent running a
**translate → test → diff-against-golden → fix** loop, with humans owning semantic
judgment and the merge/deploy gate.

The SAS→Polars specifics are a concrete fill; the structure (oracle playbook + mapping
reference + footgun checklist + decision log) generalises to any parity port.

## What it adds

| File (installs to `docs/ai/`) | Role |
|---|---|
| `AGENTS.overlay.md` | parity-specific sections — **merge into your AGENTS.md, then delete** |
| `sas-to-polars-mapping.md` | the footgun mapping reference — also feed to your RAG corpus |
| `parity-playbook.md` | how to stand up the oracle, fixtures, loop control, and cutover |

## Apply it

```bash
scripts/install.sh /path/to/repo --profile legacy-parity-migration
```

Then:
1. Merge `docs/ai/AGENTS.overlay.md` into `AGENTS.md`; fill the `<!-- TODO -->`s; delete the overlay.
2. Add `docs/ai/sas-to-polars-mapping.md` to the assistant's retrieval corpus.
3. Work through `docs/ai/parity-playbook.md` to build the scaffolding before scaling autonomy.

## The one idea

A green golden-diff is only trustworthy if the **oracle** is trustworthy and the
**boundary** is enforced by mechanism, not policy. This profile front-loads both, so
the agent can iterate fast on synthetic data while real data never moves and a false
green can't reach prod. See the playbook.
