# ADR 0001: Exact SIR in O(m·n log n) instead of a pairwise matrix

**Status**: accepted (2026-11-22)

## Context

The spec requires exact SIR scoring, a response time under 3 s for 5 000 models,
and reproducible replay. The literal definition compares every pair of
alternatives on all seven criteria: `O(n²·m)`, which at `n = 5 000` means
25 million pairs per criterion and roughly 1.4 GB for a dense float64 matrix.

## Decision

Compute the flows by per-criterion decomposition. Because the superiority index
is additive over criteria, `Phi+(a) = Σ_j w_j · S_j(v_j(a))` where
`S_j(x) = Σ_b p_j(x − s_b)`. Sorting the criterion column once and keeping its
prefix sums lets each `S_j(x)` be evaluated with two binary searches over the
three regions of the preference function. The inferiority flow is the same
function on the negated column. Total cost: `O(m·n log n)` time, `O(n)` memory.

This is not an approximation: it computes the same quantity as the pairwise
definition. A brute-force reference implementation is kept in
`ranking/domain/sir_reference.py` and compared to the fast engine at `1e-9` in
the test suite.

## Consequences

- Measured: 5 000 models rank in ~220 ms median, 261 ms p95 on this machine.
- The fast engine is the only place NumPy is allowed (constitution, Technology
  & Data Constraints).
- Any future change to the preference function must update both implementations;
  the equivalence test fails otherwise, which is the intended alarm.
