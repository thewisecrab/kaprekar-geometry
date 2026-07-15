# Lean proof certificate

This directory contains machine-checked, universal lemmas behind the generalized
Kaprekar theory. It is pinned to Lean and Mathlib `v4.31.0`. The checked source
proves the even/odd pairing identities, universal outer-gap factorization, and
the stars-and-bars cardinality of the order-free gap multiset type.

```sh
cd proofs/lean
lake exe cache get
lake build
```

`lake build` succeeds only after Lean has elaborated and checked every theorem;
the files do not use `sorry` or add axioms.

From the repository root, `python3 scripts/check_lean_nanoda.py` additionally
exports the complete environment and checks it with an independently pinned
kernel implementation. Its allowlist is limited to `propext`,
`Classical.choice`, `Quot.sound`, and `Lean.trustCompiler`; any declaration that
depends on `sorryAx` or another unlisted axiom fails.

The final identification of the order-free multiset type with weakly decreasing
integer tuples, and the injectivity step needed to turn its cardinality into
the one-step image cardinality, remain paper proofs backed by the independent
executable certificate. They are not yet mechanized here.
