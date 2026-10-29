# arXiv submission metadata

## Title

From Kaprekar Dynamics to Logit Geometry: Exact Compression, Weighted Basins, and Limits of a Sorted-Logit Representation

## Author

Siddharth Nilesh Patel

## Suggested categories

- Primary: `math.DS` (Dynamical Systems)
- Initial submission: no cross-list.

The paper contains number-theoretic material, but `math.DS` best matches its
central finite-dynamics contribution. The LLM sections prove representation
limits and define future experiments; they do not report a new trained model
or empirical language-model result, so an initial `cs.LG` or `cs.CL`
cross-list is not recommended. Category choice and any required endorsement
remain decisions for the submitter and arXiv moderators.

## Concise submission abstract

Outer-digit difference coordinates for the Kaprekar routine are classical, and the base-10 same-image criterion is Nuez (2022), equation (14). Starting from that prior art, we give an explicit integer linear reconstruction, prove injectivity for arbitrary base, and derive the exact one-step image size
`binom(b + floor(n/2) - 1, b - 1)`. The restriction of the full map to its one-step image is conjugate to a reduced spectrum map. Exact spectrum-fiber weights then recover the complete functional graph, raw basin sizes, hitting-time histograms, and entropy evolution in polynomial time for each fixed base. Certified decimal computations show cycle-dominated dynamics at widths five through eight. We also analyze normalized adjacent gaps of sorted top-k language-model logits. These coordinates are an invertible reparameterization of relative sorted logits, not a source of new predictive information. We prove reconstruction, flat-spectrum singularity, near-flat sensitivity, change-of-k behavior, omitted-tail bounds, and a distribution-free calibration impossibility. Finally, we derive the exact accept-and-residual condition for distribution-preserving speculative sampling and show why a target-only rank or margin gate is not exact in general. An independent checker exhaustively verifies 49 finite systems comprising 3,816,497 raw states, with partial Lean formalization of the core algebra. No empirical LLM performance claim is made.

## Keywords

Kaprekar routine; finite dynamical systems; functional graphs; exact basin weights; entropy; sorted logits; uncertainty estimation; speculative decoding.

## Comments field

17 pages, 2 tables. Includes universal proofs, exact finite certificates, partial Lean formalization, and an explicit empirical-claims boundary. Code and machine-readable artifacts: https://github.com/thewisecrab/kaprekar-geometry

## Build and source package

- An earlier local build used `tectonic main.tex` from this directory.
- The committed PDF and source tarball under `output/` predate the October 2026 citation revision. This repository has no script that rebuilds them. Regenerate both with `tectonic` before any upload; do not treat the committed PDF as the revised manuscript.
- The source uses standard arXiv-compatible packages and no shell escape.
- Upload `main.tex` and `references.bib`; arXiv can run BibTeX during compilation.
- Do not claim an arXiv identifier until arXiv assigns one.
- The submitter must choose the arXiv distribution license during submission; this manuscript does not invent that legal choice.

## Suggested arXiv announcement note

This is a major revision of an earlier local manuscript. It corrects the novelty claim around classical outer-gap coordinates, adds exact conjugacy and weighted-basin theorems, and narrows the LLM portion to proved representation properties and testable hypotheses.
