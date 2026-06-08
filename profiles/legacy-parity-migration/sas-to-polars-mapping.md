# SAS → Polars mapping reference

The translation cheatsheet **and** the footgun list. Most parity mismatches come from
the rows marked ⚠ — a naive translation compiles and looks right but diverges on edge
cases. Feed this into the assistant's retrieval corpus and keep it current: every new
mismatch class found in review becomes a new row here.

## Constructs

| SAS | Polars | Notes / footgun |
|---|---|---|
| DATA step (implicit row loop) | expressions over a `DataFrame` | Don't port row-by-row. Re-express as columnar ops; reserve `map_*` for the rare genuinely-sequential case. |
| `PROC SQL` join | `.join(...)` | Straightforward — but see MERGE below; they are not the same thing. |
| ⚠ `MERGE A B; BY k;` | `A.join(B, on="k", how=...)` | SAS **many-to-many MERGE is positional** (it pads the shorter group, row-aligned), NOT a SQL/Cartesian join. If both sides have dups within a BY group, a join gives different rows. Flag it, confirm the intent, reproduce explicitly. |
| ⚠ `BY k; FIRST.k / LAST.k` | sort then `.unique(subset="k", keep="first"/"last", maintain_order=True)`, or `.group_by("k").agg(...)`, or `pl.first()/pl.last().over("k")` | Requires the **same sort order** SAS had — BY needs sorted input. Which physical row is "first/last" depends on it. |
| ⚠ `RETAIN` / accumulators | `cum_sum()`, `cum_*().over(group)`, `shift()` | Reset at group boundaries with `.over(group)`. A bare cumulative leaks across groups. |
| ⚠ `PROC SORT NODUPKEY` | `.sort(...).unique(subset=keys, keep="first", maintain_order=True)` | SAS keeps the **first by BY-order**. Match the keep-rule and stability, or you keep the wrong duplicate. `NODUP` (whole-row) ≠ `NODUPKEY` (key-only). |
| ⚠ `PROC SORT` (general) | `.sort(by=[...], descending=[...], nulls_last=...)` | SAS **missing sorts LOW** (first, ascending) → `nulls_last=False` ascending. If downstream depends on input order within ties, add an explicit tie-break key — don't rely on stability. |
| `IF/THEN/ELSE` row logic | `pl.when(...).then(...).otherwise(...)` | Watch comparison semantics with missing (next row). |
| `PROC TRANSPOSE` | `.pivot(...)` / `.unpivot(...)` | Name/dtype of generated columns. |
| `PROC SUMMARY` / `MEANS` | `.group_by(...).agg(...)` | Missing handling in aggregates (below). |
| `_N_` | `.with_row_index()` | 0-based in Polars vs 1-based `_N_`. |
| `FORMAT` / `PUT` / `INPUT` | explicit `.cast(...)`, `.dt.*`, `.str.*` | SAS does silent numeric↔char conversion; make every cast explicit. |

## Value-level semantics (the precision footguns)

| Topic | SAS | Polars / fix |
|---|---|---|
| ⚠ Missing values | numeric `.`, char `' '`; `.` **sorts low**, `. < 0` is TRUE; `SUM` **ignores** missing | map to `null`; replicate sort with `nulls_last=False`; check each aggregate's null rule (`sum` skips nulls — usually matches; `mean`/counts may not). |
| ⚠ Dates | days since **1960-01-01**; datetimes = seconds since 1960-01-01 | NOT the Unix 1970 epoch. Convert with the 1960 offset (10957 days) or build via `pl.date`. |
| ⚠ `ROUND(x, u)` | rounds **half away from zero** | Polars/Python default is **banker's rounding** (half-to-even). Implement SAS rounding explicitly; this is the #1 silent mismatch. |
| ⚠ Numeric type | all numerics are 8-byte float; `BEST12.` display | compare with **tolerance**, not `==`; reproduce display formatting separately from the stored value. |
| ⚠ Character width `$w.` | char vars padded with trailing spaces to defined length | fixed-width outputs need exact padding/truncation; trailing spaces are significant. |
| String case / trim | `UPCASE`, `TRIM`, `STRIP`, `CATX` | `.str.to_uppercase()`, `.str.strip_chars()`, `.str.concat`; mind SAS auto-trim in concatenation. |

## Top 5 to check on every job
1. **Rounding** — SAS half-up vs banker's.
2. **Date epoch** — 1960, not 1970.
3. **MERGE** — positional many-to-many, not a join.
4. **Missing values** — sort-low + aggregate rules.
5. **Sort tie-breaks** — reproduce order downstream code depends on.

> When a translation has any of these and you can't prove the legacy behaviour from
> the source, **escalate** rather than guess (AGENTS.md §8).
