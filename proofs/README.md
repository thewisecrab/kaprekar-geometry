# Independent proof and certificate layer

This directory is a second, dependency-free implementation of the arithmetic
and dynamics claims. It intentionally never imports `src/kaprekar`. Its role is
to catch correlated implementation mistakes and to produce deterministic,
machine-checkable evidence.

## What the certificate proves

For every declared finite `(base, digits)` case it exhaustively checks:

1. the direct digit-histogram subtraction equals the spectral linear form for
   every one of the `base**digits` raw states;
2. the direct image equals the complete enumerated linear image;
3. the image cardinality is the stars-and-bars count;
4. every superincreasing coefficient slack is positive;
5. the linear map is injective and every spectrum has a raw representative;
6. post-first-step conjugacy on every spectrum state;
7. independent digit-count multinomial weights equal raw exhaustive fibers;
8. the full/reduced indegree and attached-leaf identities; and
9. exact cycle basins and hitting-time partitions.

The artifact hashes the raw transition table, weighted reduced graph, raw
weights, and its complete canonical JSON body. Re-running the verifier
recomputes the complete grid and demands exact object equality.

The mandatory test suite also applies this oracle's separate multinomial and
graph routines to decimal widths 5--8 and requires exact agreement with the
reported cycles, basin populations, and hitting-time histograms. That check
does not enumerate all \(10^8\) eight-digit strings; it relies on the universal
weighted-fiber proof and independently enumerates the polynomial-size spectrum
and digit-multiset spaces.

## What it does not prove

A finite grid is not a proof over all integers `base >= 2` and `digits >= 1`.
The universal proof remains the algebraic argument in
`paper/theory_addendum.md`. The `structural_proof(base, digits)` routine is an
executable proof kernel for any supplied pair, but any run is still finite.

Likewise, SHA-256 detects accidental or uncommitted artifact changes; it is not
a substitute for re-execution or an externally signed attestation.

## Trusted computing base

The executable certificate trusts the Python integer, iteration, JSON, and
SHA-256 implementations, plus this independent oracle and the verifier script.
It does not trust or execute the production package. The cross-implementation
unit tests then compare the two implementations from outside both.

Generate and fully verify the default 49-case artifact:

```bash
python3 scripts/prove.py --write results/independent_proof_certificate.json
python3 scripts/prove.py --verify results/independent_proof_certificate.json
```
