# Lean proof certificate

This directory contains machine-checked lemmas behind the generalized Kaprekar
theory. It is pinned to Lean and Mathlib `v4.31.0`. The checked source proves:

- the even/odd pairing identities;
- universal outer-gap factorization for an arbitrary integer digit vector;
- the stars-and-bars cardinality of the order-free gap multiset `Sym (Fin b) m`;
- an equivalence between that multiset type and weakly decreasing spectra
  (`Antitone (Fin m → Fin b)`);
- injectivity of the linear reconstruction on those spectra for every base
  `b ≥ 2` and every width; and
- the resulting image cardinality, by `Finset.card_image_of_injOn` together
  with `gapSpectrum_card`.

```sh
cd proofs/lean
lake exe cache get
lake build
```

`lake build` succeeds only after Lean has elaborated and checked every theorem;
the files do not use `sorry`, `admit`, `native_decide`, or added axioms.

From the repository root, `python3 scripts/check_lean_nanoda.py` additionally
exports the complete environment and checks it with an independently pinned
kernel implementation. Its allowlist is limited to `propext`,
`Classical.choice`, `Quot.sound`, and `Lean.trustCompiler`; any declaration that
depends on `sorryAx` or another unlisted axiom fails.

The following are not mechanized here, and must not be described as
machine-checked: the bridge from raw fixed-width integers to spectra, weighted
graph reconstruction, basin and entropy theorems, the logit theorems, and the
speculative residual theorem. Those remain paper proofs, with the finite grid
backed by the independent executable certificate.
