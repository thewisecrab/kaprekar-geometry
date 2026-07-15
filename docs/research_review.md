# Expert research and implementation review

**Review date:** 11 July 2026
**Scope:** original 14-page PDF, supplementary verifier, mathematical novelty, current literature, implementation readiness, and operational consequences

## Executive verdict

The manuscript contains a correct and useful exact image theorem, but the original version needs major revision before scholarly submission. Its strongest defensible contribution is not the discovery of outer-gap reduction—the 1981 literature states that dependence explicitly—but the combination of an explicit linear reconstruction, injectivity, exact image size, and the new full-graph/weighted-basin consequences developed in this repository.

The normalized logit coordinates are mathematically valid. They are also an invertible reparameterization of relative sorted top-k logits, not evidence of a new reliability method. The original LLM claims are hypotheses. The speculative ratio lemma is correct algebra but is not a distribution-preserving verification theorem and overlaps directly with existing margin-aware work.

The workspace is now a real research-software project: strict APIs, exact functional graphs, weighted raw basins, verification modes, logit diagnostics, a leakage-resistant benchmark runner, tests, package metadata, and machine-readable results. It still does not contain a multi-model LLM experiment, so no performance or production-impact claim is made.

## Artifact-level audit

| Artifact | Original state | Current state |
|---|---|---|
| Paper | Clean 14-page compiled PDF; no source | Preserved unchanged; theorem addendum and review added |
| Digit verifier | Compact unchecked exhaustive script | Backward-compatible wrapper over validated package |
| Core arithmetic | Implicit assumptions | Strict base, width, digit, number, and spectrum contracts |
| Dynamics | Fixed points only | Complete reduced graph, cycles, depths, exact raw weights and basins |
| LLM/KGS code | None | Safe KGS/tie/tail/margin diagnostic implementation |
| Benchmark | Protocol prose only | Group-disjoint train/calibration/test runner with matched baselines and dependency-group bootstrap |
| Reproducibility | No metadata/tests/package | `pyproject.toml`, CLI, unit/slow tests, JSON reports |

## Claim audit

| Claim | Finding | Required wording |
|---|---|---|
| Exact factorization | Correct, but direct outer-difference prior art exists | “Explicit reformulation and linear reconstruction” |
| Exact image cardinality | Correct for \(n\ge2\); original proof misses \(n=1\) | Handle \(n=1\) separately or use gap histograms |
| Cycle correspondence | True, but not proved by the displayed semiconjugacy | State exact conjugacy after injectivity |
| Polynomial fixed-base state space | Correct | Give \(\Theta(n^{b-1})\) asymptotic and histogram encoding |
| Decimal fixed-point table | Entries correct | Add terminal cycles and weighted basin shares |
| KGS quotient | Correct on \(D>0\) | Call it a \((k-2)\)-simplex; handle ties and \(D=0\) |
| KGS predictive value | Unvalidated | Falsifiable empirical hypothesis only |
| Logit no-free-lunch | Construction is valid but conclusion is overstated | It rules out a universal distribution-free calibrator, not logits within one process |
| Hybrid probes are necessary | Not proved | Empirical design choice supported by current studies |
| Probability-ratio bound | Correct but elementary | Exact local logit-regret identity, not correctness or quality |
| Relaxed verification | Distribution-changing and draft-agnostic | Diagnostic/gating proposal; retain exact \(p/q\) correction for lossless mode |
| Conformal wrapping | Too underspecified | Name target, score, calibration rule, guarantee, and shift assumptions |
| “Benchmark-ready” | False in the original workspace | Now implementation-ready; still no reported LLM benchmark result |

## New and newly important primary literature

### Kaprekar dynamics

- [Prichett, Ludington, and Lapenta (1981)](https://www.fq.math.ca/Scanned/19-1/prichett.pdf) explicitly define the arbitrary-base outer-difference tuple and state that the transform depends entirely on it. This narrows the novelty claim.
- [Iwasaki (2024)](https://www.fq.math.ca/Papers/62-4/iwasaki06162024-ASrev2.pdf) gives an explicit five-family classification of decimal nonzero fixed points and records a correction to the 1981 Class B conditions.
- [Devlin and Zeng (2020/2021)](https://arxiv.org/abs/2010.11756) determine maximum distances and convergence fractions for four-digit systems. In decimal, every four-digit non-repdigit fixed-width state reaches 6174 within seven steps.
- [Kay and Downes-Ward (2024)](https://arxiv.org/abs/2408.12257) classify major even-base cycle families; completeness is proved only for base 4.
- [Dahl (2026)](https://www.mdpi.com/1099-4300/28/1/92) studies decimal attractor basins and coarse-grained entropy. The exact weighted theorem in the addendum computes full-state entropy, basins, and convergence statistics on finite instances; it does not replace Dahl's intentionally projected drift/Markov analysis.
- [Chen, Ono, Schwartz, and Thakur (June 2026)](https://arxiv.org/abs/2606.20439) show that every four-digit odd-base orbit enters a stable region within three difference-coordinate steps and is then conjugate to projective doubling. The associated [Lean artifact](https://github.com/AxiomMath/kaprekar4) formalizes the main result.

### Logit uncertainty and calibration

- [Entropy Alone is Insufficient for Safe Selective Prediction (2026)](https://arxiv.org/abs/2603.21172) reports model-dependent entropy failures and generally stronger risk-coverage from entropy-plus-correctness probes. It supports testing a hybrid; it does not establish a universal rule.
- [Estimating LLM Uncertainty with Evidence](https://arxiv.org/abs/2502.00290) is the correct title and record for LogTokU; the PDF's reference title/authors/method name need correction.
- [Towards Generation-Efficient Uncertainty Estimation (May 2026)](https://arxiv.org/abs/2605.06053) introduces Logit Magnitude and an input-only distilled estimator. It is a direct cost/performance baseline.
- [Min-k Sampling (ACL 2026)](https://arxiv.org/abs/2604.11012) analyzes local shapes and cliffs in sorted logits with temperature invariance. It is the closest direct logit-shape competitor.
- [Future Confidence Distillation (8 July 2026)](https://arxiv.org/abs/2607.07626) reports stronger post-solution and hidden-state confidence signals and distills them into pre-solution features. It is very recent and should be labeled promising, not established.
- [SCoRE (2026)](https://arxiv.org/abs/2603.24704), [adaptive conformal factuality](https://arxiv.org/abs/2604.13991), and [ORCA](https://arxiv.org/abs/2604.01170) show why “wrap it with conformal” is not a complete method specification.

### Speculative decoding

- Exact distribution-preserving foundations: [Leviathan, Kalman, and Matias](https://arxiv.org/abs/2211.17192) and [Chen et al.](https://arxiv.org/abs/2302.01318).
- [MARS](https://arxiv.org/abs/2601.15498) already proposes margin-aware relaxed verification using target logits and reports large-model experiments. This is a direct novelty collision.
- [When Is a Draft Accepted? (June 2026)](https://arxiv.org/abs/2606.30265) gives exact KL rejection certificates and sharp margin bounds for strict, relaxed, top-m, entropy, and tree criteria. It is much stronger than the manuscript's ratio restatement.
- [LK Losses](https://arxiv.org/abs/2602.23881) directly optimizes acceptance objectives, while [Flatter Tokens](https://arxiv.org/abs/2601.18902) studies the value of low-margin target distributions for draft training.

## Exact consequences now exposed by the implementation

### 6174, stated precisely

On the fixed-width domain `0000` through `9999`, the ten repdigits enter zero and the other 9,990 states enter 6174 within at most seven Kaprekar steps. On the conventional 1000–9999 domain, nine nonzero repdigits are excluded from the 8,991 convergent non-repdigits. Leading-zero policy must always be stated.

### Fixed points are often not the observed story

The exact raw-weighted graph shows:

- five digits: two 4-cycles each capture about 48% of all inputs; the 2-cycle captures 3.19%;
- six digits: a 7-cycle captures 93.552%, while fixed points capture 6.447% combined;
- seven digits: the nonzero 8-cycle captures 99.9999%;
- eight digits: 3- and 7-cycles split about 97.03%, while the two fixed points split about 2.97%.

This is why the new basin engine is substantive rather than cosmetic.

### Security and encoding consequence

The mean fiber size across image states is

\[
\frac{b^n}{\binom{b+\lfloor n/2\rfloor-1}{b-1}}.
\]

For a uniform raw input, the exact Shannon loss is \(n\log_2 b-H(K(X))\), and the displayed support ratio gives a lower bound through \(H(K(X))\leq\log_2|\operatorname{Im}K|\). The map therefore destroys an asymptotically growing amount of information for fixed base. It can be an educational finite-dynamics example or a compressed analysis coordinate; it is not a credible hash, cipher, entropy source, or reversible encoding. Patents or demonstrations do not establish security.

### LLM decision consequence

Sorting drops token identity, top-k truncation drops tail mass, and normalization drops scale. The implementation restores scale and reports tail-aware full-distribution features when full logits are supplied, but no logit-only statistic can be treated as semantic correctness. In a deployed abstention system, false acceptance can expose users to incorrect answers; false rejection adds latency/cost and withholds useful answers. Both must be measured at a declared risk/coverage point.

## Reproducibility and original-April-PDF review

The original script successfully checks 3,816,497 raw states over 49 \((b,n)\) configurations. The new verifier retains that slow release check and adds reduced and seeded-sampled modes that declare exactly what was and was not established.

The release gate now requires the optional NumPy benchmark surface rather than
silently accepting skipped benchmark tests. Reproduction imports the workspace
package explicitly and records a source-tree hash plus artifact hashes.

The observations below concern the preserved anonymous April PDF, not the
authored July revision in `paper/arxiv/`. All 14 pages of that original PDF
render cleanly. Equations and tables are legible; no clipping, overlap, broken
glyphs, or black boxes were found. Its remaining publication defects were:

- the PDF is untagged;
- title, author, subject, and keyword metadata are blank;
- source `.tex` and `.bib` are absent;
- the paper has no explanatory figures; and
- the final page has avoidable unused space.

Recommended figures are a conjugacy diagram, a weighted functional-graph example, a simplex/tie-strata diagram, and an exact basin comparison.

No software license was supplied. Choosing one is an owner/legal decision;
public availability does not itself grant redistribution rights, and the
review does not invent a license.

## Vanity-engineering assessment

### Requirement-to-complexity ratio

- Original verifier: **2/10**. It was admirably small; its problem was missing contracts and evidence, not overengineering.
- Original manuscript's LLM layer: **6/10**. The Kaprekar name, redundant cumulative profiles, and architecture prose create more conceptual surface than the evidence earns.
- Current implementation: **3/10**. The added modules correspond to independently testable research jobs; no service, database, GPU layer, plugin system, or orchestration framework was introduced.

### Top findings

1. **V2 — renamed normalized spacings.** KGS is mathematically clean but cannot be sold as capability by itself. The raw relative top-k comparator is mandatory.
2. **V2 — “benchmark-ready” without a benchmark.** The original prose described experiments but supplied no dataset schema, split discipline, trainer, calibration, or metrics. These now exist, but results still require real data.
3. **V3 if deployed — approximate acceptance presented beside exact speculation.** A target-only margin rule can silently change the model distribution. The implementation labels it a diagnostic and never performs decoding.
4. **V1 — redundant features.** All cumulative profiles are linear combinations of simplex coordinates, and all coordinates plus an intercept are rank-deficient. The benchmark drops one coordinate and uses cumulative profiles only for interpretation.
5. **V2 — analogy outrunning novelty.** The 1981 gap reduction and 2026 Min-k/MARS work sharply reduce the space for broad novelty claims.

Subjective planning estimate: executing the original LLM plan unchanged could
consume roughly **20–40 researcher-hours per benchmark cycle** rediscovering
leakage, tail, calibration, and matched-baseline failures. This is not a
measured result; the current contracts are designed to remove that class of
waste.

### The hard question

If a same-capacity model on raw relative top-k logits matches KGS everywhere, is “Kaprekar” explaining a real inductive bias—or only making ordinary normalized spacings more memorable?

## Precommitted research kill criteria

These are research defaults, not deployment authorization. Production remains blocked until an independent owner who did not build the feature approves the thresholds and owns enforcement.

### Hard invalidation

- Any sample ID shared across train, calibration, and test invalidates the run automatically.
- Any post-hoc change to the primary endpoint after viewing test labels invalidates the claim.
- Any “exact decoding” claim without a target-distribution preservation test is rejected.
- Any high-stakes routing policy whose upper 95% confidence bound exceeds its stated risk limit is disabled.

### Review-to-kill triggers

- Retire the predictive KGS claim if its AUROC gain is below 0.01 **and** its AURC reduction is below 5% against raw relative top-k features across at least three model families.
- Use the raw representation if it wins or is statistically tied in at least 75% of preregistered model-task cells and KGS has no measured latency or sample-efficiency advantage.
- Withdraw any general shift-robustness claim if performance reverses under two or more declared shifts.
- Remove relaxed verification from the project if it cannot improve wall-clock throughput at a matched quality/divergence budget against MARS and exact speculative sampling.

### Continuation criteria

- Four or more model families and four or more task domains, including one long-generation and one high-consequence domain;
- independent question/sequence-level train, calibration, and test partitions;
- matched-capacity raw, scalar, tail-aware, semantic, hidden, and hybrid baselines;
- paired confidence intervals and complete risk-coverage curves; and
- exact and approximate decoding results reported in separate tables.

Until those criteria are met, the correct product label is **implemented research hypothesis**, not state of the art.
