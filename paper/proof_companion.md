# Proof companion

**Scope:** universal mathematics, exact finite certificates, and explicit
non-provable empirical claims for *From Kaprekar Dynamics to Logit Geometry*
**Proof cut-off:** 13 July 2026

This companion separates three kinds of evidence that must not be conflated:

1. a **universal proof**, valid for every parameter in its stated domain;
2. an **exact finite certificate**, which proves a particular finite instance
   once its checker and inputs are trusted; and
3. an **empirical hypothesis**, which cannot be established without external
   observations.

Testing can falsify a universal theorem but cannot prove it over an infinite
domain. The algebra below supplies the universal arguments; the independent
checker and release suite test their implementation.

## 1. Complete factorization and image theorem

Fix \(b\geq2\), \(n\geq1\), and \(m=\lfloor n/2\rfloor\). Let

\[
a_1\geq a_2\geq\cdots\geq a_n
\]

be the sorted digits of a fixed-width input. Define

\[
\Delta_j=a_j-a_{n+1-j},
\qquad
c_j=b^{n-j}-b^{j-1},
\qquad 1\leq j\leq m.
\]

### Theorem 1.1

For every fixed-width base-\(b\) input,

\[
K_{b,n}(x)=\sum_{j=1}^{m}c_j\Delta_j.
\]

#### Proof

The descending and ascending digit values are

\[
A=\sum_{i=1}^{n}a_i b^{n-i},
\qquad
B=\sum_{i=1}^{n}a_i b^{i-1}.
\]

Therefore

\[
A-B=\sum_{i=1}^{n}a_i(b^{n-i}-b^{i-1}).
\]

Pair term \(i=j\) with term \(i=n+1-j\). Their coefficients are opposites, so
the pair contributes

\[
(a_j-a_{n+1-j})(b^{n-j}-b^{j-1})=c_j\Delta_j.
\]

If \(n\) is odd, the middle coefficient is zero. Summing the \(m\) pairs proves
the identity. \(\square\)

Let

\[
S_{b,n}=\{(\Delta_1,\ldots,\Delta_m):
b-1\geq\Delta_1\geq\cdots\geq\Delta_m\geq0\}.
\]

Every actual spectrum lies in this set: \(0\leq\Delta_j\leq b-1\), and for
\(j<m\),

\[
\Delta_j-\Delta_{j+1}
=(a_j-a_{j+1})+(a_{n-j}-a_{n+1-j})\geq0.
\]

Every element of \(S_{b,n}\) is realized by the sorted digit string

\[
(\Delta_1,\ldots,\Delta_m,0,\ldots,0).
\]

Its outer differences are exactly the prescribed \(\Delta_j\). Hence the
spectrum map is surjective onto \(S_{b,n}\), including the empty spectrum when
\(n=1\).

### Lemma 1.2

The coefficients \(c_j\) are superincreasing at digit range \(0,\ldots,b-1\):

\[
c_j>(b-1)\sum_{k=j+1}^{m}c_k.
\]

#### Proof

Finite geometric summation gives

\[
c_j-(b-1)\sum_{k=j+1}^{m}c_k
=b^{n-m}+b^m-b^j-b^{j-1}.
\]

Because \(n-m\geq m\) and \(j\leq m\), the right-hand side is minimized at
\(n=2m\) and \(j=m\), where it equals

\[
b^m-b^{m-1}>0.
\]

Thus the inequality is strict. \(\square\)

### Theorem 1.3

The linear reconstruction

\[
\Lambda(\Delta)=\sum_{j=1}^{m}c_j\Delta_j
\]

is injective on \(S_{b,n}\), and

\[
|\operatorname{Im}K_{b,n}|
=|S_{b,n}|
=\binom{m+b-1}{b-1}.
\]

#### Proof

For two distinct spectra, let \(j\) be the first differing coordinate and
orient them so that \(\Delta_j-\Delta'_j\geq1\). Later coordinate differences
have magnitude at most \(b-1\). Lemma 1.2 gives

\[
\Lambda(\Delta)-\Lambda(\Delta')
\geq c_j-(b-1)\sum_{k>j}c_k>0,
\]

so \(\Lambda\) is injective.

Theorem 1.1 and spectrum surjectivity show
\(\operatorname{Im}K=\Lambda(S_{b,n})\). Finally, a weakly decreasing spectrum
is uniquely determined by the \(b\) multiplicities

\[
q_r=|\{j:\Delta_j=r\}|,\qquad
\sum_{r=0}^{b-1}q_r=m.
\]

Stars and bars counts these weak compositions as
\(\binom{m+b-1}{b-1}\). For \(m=0\), the same formula gives one empty spectrum.
\(\square\)

## 2. Exact conjugacy and the full functional graph

Define

\[
\Sigma:X_{b,n}\to S_{b,n},\qquad
R=\Sigma\Lambda,\qquad
I=\operatorname{Im}K.
\]

### Theorem 2.1

\(\Lambda:S_{b,n}\to I\) is a bijection and

\[
K|_I\circ\Lambda=\Lambda\circ R.
\]

Thus \(K|_I\) and \(R\) are conjugate, and for every \(t\geq1\),

\[
K^t(x)=\Lambda R^{t-1}\Sigma(x).
\]

#### Proof

Theorem 1.3 makes \(\Lambda\) a bijection onto \(I\). Direct composition gives

\[
K\Lambda=\Lambda\Sigma\Lambda=\Lambda R.
\]

The iterate formula follows by induction. A bijective conjugacy preserves
least periods, cycles, and post-first-step transient depths. \(\square\)

For \(\Delta\in S_{b,n}\), set

\[
w(\Delta)=|\Sigma^{-1}(\Delta)|.
\]

### Theorem 2.2

\[
\operatorname{indeg}_K(\Lambda\Delta)=w(\Delta).
\]

The complete raw graph is isomorphic to the reduced graph after relabeling
\(\Delta\mapsto\Lambda\Delta\) and attaching

\[
w(\Delta)-\operatorname{indeg}_R(\Delta)
\]

new indegree-zero source leaves at \(\Lambda\Delta\).

#### Proof

Injectivity of \(\Lambda\) gives

\[
K(x)=\Lambda\Delta
\iff
\Lambda\Sigma(x)=\Lambda\Delta
\iff
\Sigma(x)=\Delta.
\]

Therefore the full indegree is \(w(\Delta)\). A preimage already in \(I\) has
the form \(\Lambda\Delta'\), and it maps to \(\Lambda\Delta\) exactly when
\(R(\Delta')=\Delta\). Those account for
\(\operatorname{indeg}_R(\Delta)\) preimages. Every remaining preimage is
outside \(I\), and no state outside \(I=\operatorname{Im}K\) can itself have a
preimage. \(\square\)

The isomorphism recovers graph structure and multiplicities, not the original
integer labels of all anonymous leaves without enumerating their fibers.

## 3. Exact fiber weights, basins, and entropy

For a sorted digit multiset \(a\), let \(c_d(a)\) be the multiplicity of digit
\(d\). Its number of fixed-width permutations is

\[
\operatorname{mult}(a)=\frac{n!}{\prod_{d=0}^{b-1}c_d(a)!}.
\]

Consequently,

\[
w(\Delta)=
\sum_{\substack{a\text{ sorted}\\\Sigma(a)=\Delta}}
\operatorname{mult}(a).
\]

### Theorem 3.1

For a reduced attractor cycle \(C\),

\[
|\operatorname{Basin}_K(\Lambda C)|
=\sum_{\Delta\in\operatorname{Basin}_R(C)}w(\Delta).
\]

#### Proof

The spectrum fibers are a disjoint partition of the raw state space. By
Theorem 2.1, a raw state reaches \(\Lambda C\) exactly when its spectrum reaches
\(C\). Summing precisely those fiber sizes proves the formula. \(\square\)

If a noncycle spectrum is at reduced depth \(d\), every raw state in its fiber
has raw depth \(d+1\). There is no time-zero exception: if
\(x=\Lambda\gamma\) is on the raw cycle, then
\(\Sigma x=R\gamma\) lies on the reduced cycle, contradicting a noncycle
spectrum. If a spectrum lies on a reduced cycle, exactly one state
in its fiber is already on the corresponding raw cycle; all remaining states
enter it after one step. This proves the implemented hitting-time histogram.

### Theorem 3.2

For any raw input law \(\mu\), with \(\nu=\Sigma_*\mu\), and every \(t\geq1\),

\[
(K^t)_*\mu=\Lambda_*(R^{t-1})_*\nu
\]

and

\[
H(K^t(X))=H(R^{t-1}(\Sigma X)).
\]

#### Proof

The pushforward identity is the random-variable form of Theorem 2.1. Atoms and
their probabilities are unchanged by the injective relabeling \(\Lambda\), so
discrete Shannon entropy is unchanged. \(\square\)

Under a uniform raw input,

\[
\Pr(\Sigma X=\Delta)=\frac{w(\Delta)}{b^n},
\]

so the one-step conditional information loss is exactly

\[
H(X\mid K(X))
=\sum_{\Delta}\frac{w(\Delta)}{b^n}\log_2 w(\Delta).
\]

The support-size expression

\[
n\log_2b-\log_2|\operatorname{Im}K|
\]

is a lower bound on that Shannon loss, not generally the exact value.

For fixed \(b\),

\[
|S_{b,n}|
=\binom{m+b-1}{b-1}
=\frac{m^{b-1}}{(b-1)!}+O(m^{b-2}).
\]

This follows by expanding the \(b-1\) factors in the binomial coefficient.
Since \(m=\lfloor n/2\rfloor\), the reduced state count and sorted-multiset
count are polynomial in \(n\), while \(b^n\) is exponential. Therefore the
image ratio tends to zero exponentially, and the support-based information
loss grows as

\[
n\log_2 b-(b-1)\log_2n+O(1).
\]

## 4. Logit geometry: what is proved

Let \(k\geq2\), \(s_1\geq\cdots\geq s_k\), \(D=s_1-s_k>0\), and

\[
u_j=\frac{s_j-s_{j+1}}{D}.
\]

### Theorem 4.1

\[
s_i-s_k=D\sum_{j=i}^{k-1}u_j.
\]

Hence \(u\) determines sorted top-\(k\) logits modulo positive scale and
translation, while \((D,u)\) determines them modulo translation.

#### Proof

The sum telescopes:

\[
D\sum_{j=i}^{k-1}u_j
=\sum_{j=i}^{k-1}(s_j-s_{j+1})
=s_i-s_k.
\]

Reconstruction proves injectivity and the definition proves surjectivity.
\(\square\)

Define

\[
r(s)=(s_1-s_k,\ldots,s_{k-1}-s_k,0).
\]

Then \(r(s)\) and \((D,u)\) are bijectively related, so they generate the same
sigma-algebra and have identical Bayes-optimal risk for every target and loss.
The unrestricted sorted vector can be strictly more informative because it
also retains the common offset \(s_k\). Equality for every decision problem is
guaranteed by a sufficiency assumption such as
\(Y\perp s_k\mid r(s)\); a particular loss may tie accidentally without it.
Thus KGS creates no
information relative to the translation-quotiented vector; any gain over that
information-matched baseline must come from inductive bias, regularization, or
finite-sample effects.

### Theorem 4.2

For \(k\geq3\), \(u\) has no continuous extension to \(D=0\).

#### Proof

Choose distinct simplex points \(u\neq v\). Reconstruct top-\(k\) vectors with
bottom logit zero and spread \(\varepsilon\). Both families converge to the
same flat vector as \(\varepsilon\downarrow0\), while their normalized
coordinates remain \(u\) and \(v\). A continuous extension would assign two
different limits to the same point. \(\square\)

### Theorem 4.3

If two sorted spectra \(s,t\) have spreads at least \(d>0\) and
\(\|s-t\|_\infty\leq\varepsilon\), then

\[
\|u(s)-u(t)\|_\infty\leq\frac{4\varepsilon}{d}.
\]

#### Proof

Each adjacent gap changes by at most \(2\varepsilon\), and each spread changes
by at most \(2\varepsilon\). For corresponding gaps \(g,g'\),

\[
\left|\frac{g}{D_s}-\frac{g'}{D_t}\right|
\leq
\frac{|g-g'|}{D_s}
+
\frac{g'|D_t-D_s|}{D_sD_t}
\leq\frac{4\varepsilon}{d},
\]

because \(0\leq g'\leq D_t\). \(\square\)

### Theorem 4.4

Let \(V\geq k\), set \(r_i=s_i-s_k\), and

\[
A=\sum_{i=1}^{k}e^{r_i}.
\]

With no tail information beyond omitted logits being at most \(s_k\),

\[
\frac{A}{A+V-k}\leq M_k\leq1,
\qquad
\frac{e^D}{A+V-k}\leq p_1\leq\frac{e^D}{A}.
\]

#### Proof

Writing the omitted softmax partition relative to \(e^{s_k}\) as \(T\), each
of its \(V-k\) terms lies in \((0,1]\). Thus

\[
0\leq T\leq V-k,
\qquad
M_k=\frac{A}{A+T},
\qquad
p_1=\frac{e^D}{A+T}.
\]

Both expressions decrease monotonically in \(T\), which gives the bounds. The
lower bounds are attained when all omitted logits equal \(s_k\); for a
nonempty finite tail the upper bounds are suprema as its logits tend to
\(-\infty\). \(\square\)

If \(V=k\), then \(T=0\) and KGS determines the complete softmax distribution.
If \(V>k\), different admissible tail logits produce different \(T\), so KGS
alone cannot determine full entropy, top-token probability, or tail mass. For
a nonempty finite tail the upper bounds are strict, sharp suprema.

For entropy, let \(P\) denote the top-k-conditional law and give one omitted
token relative weight \(t\in(0,1]\). With \(q=t/(A+t)\), and with any other omitted
weights tending to zero, the limiting entropy is

\[
h_2(q)+(1-q)H(P).
\]

Here \(h_2\) is binary entropy in the same logarithm base as \(H\). This is
nonconstant in \(q\). Continuity therefore supplies two finite
admissible tails with identical \((D,u)\) and different entropy. When at least
two tail tokens exist, redistributing a fixed tail mass gives a second direct
construction by changing the within-tail entropy.

### Theorem 4.5

Extending a nondegenerate top-\(k\) spectrum by \(s_{k+1}\leq s_k\) gives

\[
u_j^{(k+1)}=\frac{D_k}{D_{k+1}}u_j^{(k)}
\quad(1\leq j<k),
\qquad
u_k^{(k+1)}=\frac{s_k-s_{k+1}}{D_{k+1}}.
\]

#### Proof

The old adjacent gaps are unchanged and only their normalizing denominator
changes from \(D_k=s_1-s_k\) to \(D_{k+1}=s_1-s_{k+1}\). The final coordinate
is the new adjacent gap divided by that denominator. \(\square\)

### Corollary 4.6

For \(1\leq r\leq k\), full-softmax probabilities satisfy

\[
\frac{p_r}{p_1}
=\exp(s_r-s_1)
=\exp\left(-D\sum_{j=1}^{r-1}u_j\right).
\]

The softmax partition cancels in the ratio, and Theorem 4.1 supplies the
telescoping logit difference. This is a target-distribution identity, not a
correctness guarantee.

### Theorem 4.7

No fixed logit-only function can be a distribution-free correctness
probability over every possible joint law.

#### Proof

Fix any \(q:\mathbb R^V\to[0,1]\) and any logit vector \(z_0\). Consider two
laws with the same deterministic observation \(Z=z_0\), but set correctness
\(Y=1\) almost surely in one law and \(Y=0\) almost surely in the other. The
same value \(q(z_0)\) cannot equal both conditional correctness probabilities.
Moreover, the worse of the two Brier risks is

\[
\max\{(1-q(z_0))^2,q(z_0)^2\}\geq\frac14.
\]

The inequality holds because either \(q(z_0)\geq1/2\) or
\(1-q(z_0)\geq1/2\). This proves only a distribution-free impossibility; it
does not prove that logits fail within a fixed process or that hidden features
must perform better. \(\square\)

## 5. Exact speculative-sampling condition

Let \(q\) propose a token, \(a(x)\) be its acceptance probability, and \(h\) be
the replacement distribution after rejection. Set

\[
r=1-\sum_xq(x)a(x).
\]

### Theorem 5.1

The final output follows a target distribution \(p\) if and only if

\[
q(x)a(x)+rh(x)=p(x)
\quad\text{for every }x.
\]

When \(r>0\), such an \(h\) exists exactly when \(q(x)a(x)\leq p(x)\) for all
\(x\), and then

\[
h(x)=\frac{p(x)-q(x)a(x)}{r}.
\]

When \(r=0\), rejection never occurs and exactness holds exactly when
\(q(x)a(x)=p(x)\) for every \(x\), equivalently \(q=p\) with full acceptance on
the support of \(q\). Acceptance values where \(q(x)=0\) are immaterial.

#### Proof

The first identity is the law of total probability over acceptance and
rejection. For \(r>0\), solving for \(h\) gives the formula. Componentwise
nonnegativity is equivalent to \(qa\leq p\), and the numerator sums to

\[
1-\sum_xq(x)a(x)=r,
\]

so \(h\) is normalized. For \(r=0\), the residual term vanishes and the stated
componentwise equality follows directly. \(\square\)

For \(q(x)>0\), the maximal standard choice
\(a(x)=\min\{1,p(x)/q(x)\}\) gives accepted mass
\(\min\{q(x),p(x)\}\); for \(q(x)=0\), acceptance is arbitrary. Therefore the
maximum total accepted mass is

\[
\sum_x\min\{q(x),p(x)\}=1-\operatorname{TV}(p,q),
\]

and this is genuinely maximal: exactness requires \(qa\leq p\), while
\(a\leq1\) gives \(qa\leq q\), hence \(qa\leq\min(p,q)\) componentwise. The
standard choice attains every componentwise upper bound.

The residual restores the rest. A target-only rank or margin rule omits \(q\),
so it is not distribution-preserving in general.

## 6. Selective-risk calibration theorem

Let \((S_i,E_i)_{i=1}^N\) be IID score/error pairs from the deployment law, and
fix a finite threshold grid \(T\) before observing them. For threshold \(t\),
let

\[
r_t=\Pr(E=1\mid S\geq t).
\]

### Theorem 6.1

Apply a one-sided Clopper--Pearson bound at level
\(\alpha/|T|\) to every threshold with at least the declared minimum accepted
count. With probability at least \(1-\alpha\), all reported upper bounds cover
their corresponding \(r_t\) simultaneously. Therefore any threshold selected
because its bound is at most a target risk \(\rho\) has \(r_t\leq\rho\) on the
same simultaneous event.

#### Proof

For a fixed threshold, conditional on \(N_t=n\) accepted examples, their errors
are IID Bernoulli with parameter \(r_t\). The exact Clopper--Pearson upper bound
fails with probability at most \(\alpha/|T|\). A union bound over the
predeclared grid shows that any bound fails with probability at most
\(\alpha\). On the complementary event, data-dependent selection among those
simultaneously valid bounds preserves validity. \(\square\)

Generic exchangeability, calibration-set reuse, and arbitrary distribution
shift do not satisfy this theorem's assumptions.

## 7. Proof ledger

| Claim | Strongest available status |
|---|---|
| Factorization \(K=\Lambda\Sigma\) | Universal proof, Theorem 1.1; machine-checked in `proofs/lean/KaprekarProofs.lean` |
| Exact image cardinality | Universal proof, Theorem 1.3 |
| Cycle and transient correspondence | Universal conjugacy proof, Theorem 2.1 |
| Complete weighted graph and basins | Universal proofs, Theorems 2.2 and 3.1 |
| Decimal cycle identities and basin counts | Exact finite certificates |
| Odd-base four-digit projective-doubling classification | External theorem with a published Lean artifact; not re-proved by this repository |
| Entropy pushforward identity | Universal proof, Theorem 3.2 |
| KGS reconstruction and invariances | Universal proof, Theorem 4.1 |
| Flat singularity and sensitivity | Universal proofs, Theorems 4.2--4.3 |
| Tail ambiguity | Universal proof, Theorem 4.4 |
| Change of \(k\) and rank probability ratio | Universal identities, Theorem 4.5 and Corollary 4.6 |
| Distribution-free correctness calibration | Universal impossibility, Theorem 4.7 |
| Exact speculative target preservation | Universal proof, Theorem 5.1 |
| IID selective-risk bound | Universal conditional proof, Theorem 6.1 |
| KGS improves correctness/calibration | Unproved empirical hypothesis |
| KGS improves decoding speed at matched quality | Unproved empirical hypothesis |
| Broad production or educational impact | Unproved external claim |

The last three rows cannot be converted into theorems by more local testing.
They require preregistered external experiments and must remain labeled as
hypotheses.

The external odd-base result is independently available as the
[2026 paper](https://arxiv.org/abs/2606.20439) and its
[Lean development](https://github.com/AxiomMath/kaprekar4).

The repository's own Lean project is pinned by `lean-toolchain` and
`lake-manifest.json`. It proves the universal even/odd pairing identities,
factorization theorem, and the cardinality of the order-free gap multiset type,
not merely the finite certificate grid. The explicit equivalence from that
multiset type to weakly decreasing integer spectra, the injectivity bridge to
the image count, and the remaining universal results are currently hand proofs
backed by independent executable stress tests; they should not be described as
fully formalized.
