# fixwitness mutation benchmark

fixwitness 0.6.0.dev0 · engine sqlite · 27 mutants from 6 queries · 40 random tables per query · seed 7 · 335s

Mutants are generated mechanically, not designed by hand. **Non-equivalent** = output differs from the original on the sample or on any random table. **Likely equivalent** = no difference found; the search cannot prove equivalence, so these are not scored until reviewed by hand.

| Group | Count |
|---|---|
| non-equivalent | 18 |
| likely equivalent | 9 |
| invalid (does not run) | 0 |

## Headline (non-equivalent mutants only)

| Check | Mutants caught |
|---|---|
| sample test (output on today's sample unchanged) | 12/18 (67%) |
| fixwitness | 18/18 (100%) |

## Likely-equivalent mutants that fixwitness rejected (review by hand)

0 of 9.

## By operator (non-equivalent)

| Operator | fixwitness | sample test |
|---|---|---|
| = -> <> | 6/6 (100%) | 6/6 (100%) |
| AVG -> SUM | 1/1 (100%) | 1/1 (100%) |
| SUM -> AVG | 4/4 (100%) | 4/4 (100%) |
| UNION ALL -> UNION | 1/1 (100%) | 0/1 (0%) |
| add DISTINCT | 3/3 (100%) | 0/3 (0%) |
| drop NOT | 1/1 (100%) | 1/1 (100%) |
| join -> left join | 2/2 (100%) | 0/2 (0%) |

## Missed by fixwitness (non-equivalent)

none

## Threats to validity

- Only the 6 hand-written originals in `benchmark/sql/` are mutated, so query style is the author's.
- Ground truth is a random search with a fixed budget; some 'likely equivalent' mutants may truly differ.
- Single-statement SQLite/DuckDB queries only; no dbt, no Jinja, no DataFrames.
