import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.Order.BigOperators.Group.LocallyFinite
import Mathlib.Algebra.Ring.Parity
import Mathlib.Data.Fin.SuccPred
import Mathlib.Data.Fintype.Card
import Mathlib.Data.List.OfFn
import Mathlib.Data.Multiset.Sort
import Mathlib.Data.Sym.Card
import Mathlib.Order.Monotone.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import Lean.Elab.Tactic.Omega

/-!
# Mechanized core lemmas for generalized Kaprekar maps

This file is intentionally small.  It formalizes universal algebraic claims used
by the paper rather than certifying only a finite list of `(base, width)` cases.
-/

namespace Kaprekar

open scoped BigOperators

open Finset

/-! ## A general pairing identity -/

/-- An even finite sum can be grouped into terms equidistant from its ends. -/
theorem sum_range_pair_even {R : Type*} [AddCommMonoid R]
    (f : ℕ → R) (m : ℕ) :
    (∑ i ∈ range (2 * m), f i) =
      ∑ i ∈ range m, (f i + f (2 * m - 1 - i)) := by
  rw [show 2 * m = m + m by omega, sum_range_add, sum_add_distrib]
  congr 1
  rw [← sum_range_reflect (fun i ↦ f (m + i)) m]
  apply sum_congr rfl
  intro i hi
  have him : i < m := mem_range.mp hi
  congr 1
  omega

/-- An odd finite sum is the paired sum plus its central term. -/
theorem sum_range_pair_odd {R : Type*} [AddCommMonoid R]
    (f : ℕ → R) (m : ℕ) :
    (∑ i ∈ range (2 * m + 1), f i) =
      (∑ i ∈ range m, (f i + f (2 * m - i))) + f m := by
  rw [show 2 * m + 1 = (m + 1) + m by omega, sum_range_add]
  rw [sum_range_succ, sum_add_distrib]
  have hlast :
      (∑ i ∈ range m, f (m + 1 + i)) =
        ∑ i ∈ range m, f (2 * m - i) := by
    rw [← sum_range_reflect (fun i ↦ f (m + 1 + i)) m]
    apply sum_congr rfl
    intro i hi
    have him : i < m := mem_range.mp hi
    congr 1
    omega
  rw [hlast]
  ac_rfl

/-! ## Factorization through outer digit gaps -/

/-- Positional value with the first supplied digit in the most significant place. -/
def descendingValue (b : ℤ) (n : ℕ) (a : ℕ → ℤ) : ℤ :=
  ∑ i ∈ range n, a i * b ^ (n - 1 - i)

/-- Positional value of the reversed supplied digit sequence. -/
def ascendingValue (b : ℤ) (n : ℕ) (a : ℕ → ℤ) : ℤ :=
  ∑ i ∈ range n, a i * b ^ i

/-- The paper's explicit linear form in the outer-pair gaps. -/
def outerGapForm (b : ℤ) (n : ℕ) (a : ℕ → ℤ) : ℤ :=
  ∑ i ∈ range (n / 2),
    (b ^ (n - 1 - i) - b ^ i) * (a i - a (n - 1 - i))

private theorem value_difference_as_sum (b : ℤ) (n : ℕ) (a : ℕ → ℤ) :
    descendingValue b n a - ascendingValue b n a =
      ∑ i ∈ range n, a i * (b ^ (n - 1 - i) - b ^ i) := by
  simp only [descendingValue, ascendingValue, ← sum_sub_distrib]
  apply sum_congr rfl
  intro i _
  ring

private theorem factorization_even (b : ℤ) (m : ℕ) (a : ℕ → ℤ) :
    descendingValue b (2 * m) a - ascendingValue b (2 * m) a =
      ∑ i ∈ range m,
        (b ^ (2 * m - 1 - i) - b ^ i) *
          (a i - a (2 * m - 1 - i)) := by
  rw [value_difference_as_sum]
  rw [sum_range_pair_even]
  apply sum_congr rfl
  intro i hi
  have him : i < m := mem_range.mp hi
  have hreflect : 2 * m - 1 - (2 * m - 1 - i) = i := by omega
  rw [hreflect]
  ring

private theorem factorization_odd (b : ℤ) (m : ℕ) (a : ℕ → ℤ) :
    descendingValue b (2 * m + 1) a - ascendingValue b (2 * m + 1) a =
      ∑ i ∈ range m,
        (b ^ (2 * m - i) - b ^ i) * (a i - a (2 * m - i)) := by
  rw [value_difference_as_sum]
  rw [sum_range_pair_odd]
  have hmiddle : 2 * m + 1 - 1 - m = m := by omega
  simp only [hmiddle, sub_self, mul_zero, add_zero]
  apply sum_congr rfl
  intro i hi
  have him : i < m := mem_range.mp hi
  have houter : 2 * m + 1 - 1 - i = 2 * m - i := by omega
  have hreflect : 2 * m + 1 - 1 - (2 * m - i) = i := by omega
  rw [houter, hreflect]
  ring

/--
The universal factorization theorem.  It has no bounded-base or bounded-width
assumption: for every integer base, every width, and every digit vector, the
descending-minus-ascending value depends only on the outer-pair differences.
-/
theorem kaprekar_factorization (b : ℤ) (n : ℕ) (a : ℕ → ℤ) :
    descendingValue b n a - ascendingValue b n a = outerGapForm b n a := by
  obtain ⟨m, rfl | rfl⟩ := Nat.even_or_odd' n
  · simpa [outerGapForm] using factorization_even b m a
  · rw [outerGapForm]
    have hdiv : (2 * m + 1) / 2 = m := by omega
    rw [hdiv]
    simpa using factorization_odd b m a

/-! ## Exact spectrum count -/

/--
An unordered `m`-tuple of values in `Fin b` is the order-free form of a weakly
decreasing length-`m` gap spectrum with entries in `0, …, b-1`.
-/
abbrev GapSpectrum (b m : ℕ) := Sym (Fin b) m

/-- Stars and bars, including the edge cases `b = 0` and `m = 0`. -/
theorem gapSpectrum_card (b m : ℕ) :
    Fintype.card (GapSpectrum b m) = Nat.choose (b + m - 1) m := by
  simpa [GapSpectrum] using (Sym.card_sym_eq_choose (α := Fin b) m)

/-! ## Sorted spectra and the linear image -/

/-- A weakly decreasing length-`m` tuple with entries in `Fin b`. -/
abbrev SortedSpectrum (b m : ℕ) := {g : Fin m → Fin b // Antitone g}

/-- The descending list of a digit multiset. -/
def descendingList {b m : ℕ} (s : GapSpectrum b m) : List (Fin b) :=
  (Multiset.sort s.1).reverse

lemma descendingList_length {b m : ℕ} (s : GapSpectrum b m) :
    (descendingList s).length = m := by
  rw [descendingList, List.length_reverse, Multiset.length_sort, s.2]

lemma descendingList_sortedGE {b m : ℕ} (s : GapSpectrum b m) :
    (descendingList s).SortedGE := by
  simpa [descendingList, List.sortedGE_reverse] using
    (Multiset.pairwise_sort (s := s.1) (r := (· ≤ ·))).sortedLE

/-- Read a digit multiset as a weakly decreasing tuple. -/
def sortedOfGap {b m : ℕ} (s : GapSpectrum b m) : SortedSpectrum b m :=
  ⟨fun i => (descendingList s).get (Fin.cast (descendingList_length s).symm i), by
    intro i j hij
    exact (descendingList_sortedGE s).antitone_get
      ((Fin.cast_le_cast (descendingList_length s).symm).2 hij)⟩

/-- Forget the order of a weakly decreasing tuple. -/
def gapOfSorted {b m : ℕ} (g : SortedSpectrum b m) : GapSpectrum b m :=
  ⟨(List.ofFn g.1 : Multiset (Fin b)), by rw [Multiset.coe_card, List.length_ofFn]⟩

private lemma list_get_cast_eq {α : Type*} {n : ℕ} (l₁ l₂ : List α) (h : l₁ = l₂)
    (i : Fin n) (hlen : l₁.length = n) :
    l₁.get (Fin.cast hlen.symm i) =
      l₂.get (Fin.cast ((congrArg List.length h).symm.trans hlen).symm i) := by
  subst h
  rfl

/-- Digit multisets are exactly the weakly decreasing spectra. -/
def gapSpectrumEquivSorted (b m : ℕ) : GapSpectrum b m ≃ SortedSpectrum b m where
  toFun := sortedOfGap
  invFun := gapOfSorted
  left_inv s := by
    let l := descendingList s
    have hofn :
        List.ofFn (fun i => l.get (Fin.cast (descendingList_length s).symm i)) = l := by
      have hget : List.ofFn (List.get l) = l := List.ofFn_get l
      simpa using (List.ofFn_congr (descendingList_length s) (List.get l)).symm.trans hget
    apply Subtype.ext
    change (List.ofFn (sortedOfGap s).1 : Multiset (Fin b)) = s.1
    have hfun : (sortedOfGap s).1 =
        fun i => l.get (Fin.cast (descendingList_length s).symm i) := rfl
    rw [hfun, hofn]
    simp [l, descendingList, Multiset.coe_reverse, Multiset.sort_eq]
  right_inv g := by
    let l0 : List (Fin b) := List.ofFn g.1
    have hl0 : l0.SortedGE := g.2.sortedGE_ofFn
    have hdesc : ((l0 : Multiset (Fin b)).sort (· ≤ ·)).reverse.SortedGE := by
      simpa [List.sortedGE_reverse] using
        (Multiset.pairwise_sort (s := (l0 : Multiset (Fin b))) (r := (· ≤ ·))).sortedLE
    have hperm : List.Perm (((l0 : Multiset (Fin b)).sort (· ≤ ·)).reverse) l0 :=
      Multiset.coe_eq_coe.mp (by rw [Multiset.coe_reverse, Multiset.sort_eq])
    have heqlist : ((l0 : Multiset (Fin b)).sort (· ≤ ·)).reverse = l0 :=
      List.Perm.eq_of_sortedGE hdesc hl0 hperm
    have hlist : descendingList (gapOfSorted g) = List.ofFn g.1 := by
      simpa [descendingList, gapOfSorted, l0] using heqlist
    apply Subtype.ext
    funext i
    have htransport :=
      list_get_cast_eq (descendingList (gapOfSorted g)) (List.ofFn g.1) hlist i
        (descendingList_length (gapOfSorted g))
    have hright :
        (List.ofFn g.1).get
            (Fin.cast ((congrArg List.length hlist).symm.trans
              (descendingList_length (gapOfSorted g))).symm i) =
          g.1 i := by
      simp
    exact htransport.trans hright

theorem sortedSpectrum_card (b m : ℕ) :
    Fintype.card (SortedSpectrum b m) = Nat.choose (b + m - 1) m := by
  rw [Fintype.card_congr (gapSpectrumEquivSorted b m).symm]
  exact gapSpectrum_card b m

/-- The paper's outer-pair coefficient, as an integer. -/
def outerCoeffZ (b n j : ℕ) : ℤ :=
  (b : ℤ) ^ (n - 1 - j) - (b : ℤ) ^ j

/-- Digit `k` of a length-`m` tuple, or zero past the end. -/
def tupleDigit {b m : ℕ} (g : Fin m → Fin b) (k : ℕ) : ℤ :=
  if h : k < m then (g ⟨k, h⟩).val else 0

lemma outerCoeffZ_pos {b n i : ℕ} (hb : 2 ≤ b) (hi : i < n / 2) :
    0 < outerCoeffZ b n i := by
  have hdiv : 2 * (n / 2) ≤ n := by
    simpa [Nat.mul_comm] using Nat.div_mul_le_self n 2
  have hi1 : i + 1 ≤ n / 2 := Nat.succ_le_of_lt hi
  have htwo : 2 * (i + 1) ≤ n :=
    le_trans (Nat.mul_le_mul_left 2 hi1) hdiv
  have hexp : i < n - 1 - i := by omega
  have hpow : b ^ i < b ^ (n - 1 - i) :=
    Nat.pow_lt_pow_right (by omega) hexp
  have hpowZ : (b : ℤ) ^ i < (b : ℤ) ^ (n - 1 - i) := by
    simpa [Int.natCast_pow] using (Int.ofNat_lt.mpr hpow)
  exact sub_pos.mpr hpowZ

lemma coeff_recurrence {b n i : ℕ} (hi : i + 1 < n / 2) :
    outerCoeffZ b n i =
      (b : ℤ) * outerCoeffZ b n (i + 1) +
        (b : ℤ) ^ i * ((b : ℤ) ^ 2 - 1) := by
  unfold outerCoeffZ
  have hn : n - 1 - i = (n - 2 - i) + 1 := by omega
  have hi2 : i + 2 = (i + 1) + 1 := by omega
  have hpow1 :
      (b : ℤ) ^ (n - 1 - i) = (b : ℤ) * (b : ℤ) ^ (n - 2 - i) := by
    rw [hn, pow_succ, mul_comm]
  have hpow2 : (b : ℤ) ^ (i + 2) = (b : ℤ) * (b : ℤ) ^ (i + 1) := by
    rw [hi2, pow_succ, mul_comm]
  have hpow3 : (b : ℤ) ^ (i + 2) = (b : ℤ) ^ i * (b : ℤ) ^ 2 := by
    rw [pow_add]
  have hexp : n - 2 - i = n - 1 - (i + 1) := by omega
  calc
    (b : ℤ) ^ (n - 1 - i) - (b : ℤ) ^ i
        = (b : ℤ) * (b : ℤ) ^ (n - 2 - i) - (b : ℤ) ^ i := by rw [hpow1]
    _ = (b : ℤ) * ((b : ℤ) ^ (n - 2 - i) - (b : ℤ) ^ (i + 1)) +
          (b : ℤ) * (b : ℤ) ^ (i + 1) - (b : ℤ) ^ i := by ring
    _ = (b : ℤ) * ((b : ℤ) ^ (n - 2 - i) - (b : ℤ) ^ (i + 1)) +
          (b : ℤ) ^ (i + 2) - (b : ℤ) ^ i := by rw [hpow2]
    _ = (b : ℤ) * ((b : ℤ) ^ (n - 1 - (i + 1)) - (b : ℤ) ^ (i + 1)) +
          (b : ℤ) ^ i * ((b : ℤ) ^ 2 - 1) := by rw [hexp, hpow3]; ring

lemma coeff_dominates_aux (b n : ℕ) (hb : 2 ≤ b) :
    ∀ d i, i + d + 1 = n / 2 →
      outerCoeffZ b n i >
        ((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i + 1) (n / 2), outerCoeffZ b n k := by
  intro d
  induction d with
  | zero =>
      intro i hi
      have hm : n / 2 = i + 1 := by omega
      simp only [hm, Finset.Ico_self, Finset.sum_empty, mul_zero]
      exact outerCoeffZ_pos hb (by omega)
  | succ d ih =>
      intro i hi
      have hi1 : (i + 1) + d + 1 = n / 2 := by omega
      have hc := ih (i + 1) hi1
      have hsplit :=
        Finset.sum_eq_sum_Ico_succ_bot (a := i + 1) (b := n / 2) (by omega)
          (fun k => outerCoeffZ b n k)
      have hi_lt : i + 1 < n / 2 := by
        have hposd : 0 < d + 1 := Nat.succ_pos d
        have hsum : i + 1 + (d + 1) = n / 2 := by
          rw [show i + 1 + (d + 1) = i + (d + 1) + 1 by ring]
          exact hi
        exact lt_of_lt_of_eq (Nat.lt_add_of_pos_right hposd) hsum
      have hpos : 0 < (b : ℤ) ^ i * ((b : ℤ) ^ 2 - 1) := by
        have hbz : (2 : ℤ) ≤ b := by exact_mod_cast hb
        have hsq : (2 : ℤ) * 2 ≤ b * b :=
          mul_le_mul hbz hbz (by omega) (by omega)
        have hone : (1 : ℤ) < (b : ℤ) ^ 2 := by
          have : (4 : ℤ) ≤ (b : ℤ) ^ 2 := by simpa [pow_two] using hsq
          omega
        exact mul_pos (pow_pos (by omega) i) (sub_pos.mpr hone)
      have hstep :
          (b : ℤ) * outerCoeffZ b n (i + 1) < outerCoeffZ b n i := by
        rw [coeff_recurrence hi_lt]
        linarith
      have hrest :
          ((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i + 2) (n / 2), outerCoeffZ b n k <
            outerCoeffZ b n (i + 1) := by
        simpa using hc
      have hsum :
          ((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i + 1) (n / 2), outerCoeffZ b n k <
            (b : ℤ) * outerCoeffZ b n (i + 1) := by
        rw [hsplit]
        have :
            ((b : ℤ) - 1) *
                (outerCoeffZ b n (i + 1) +
                  ∑ k ∈ Finset.Ico (i + 2) (n / 2), outerCoeffZ b n k) =
              ((b : ℤ) - 1) * outerCoeffZ b n (i + 1) +
                ((b : ℤ) - 1) *
                  ∑ k ∈ Finset.Ico (i + 2) (n / 2), outerCoeffZ b n k := by
          ring
        linarith
      exact lt_trans hsum hstep

lemma coeff_dominates {b n i : ℕ} (hb : 2 ≤ b) (hi : i < n / 2) :
    outerCoeffZ b n i >
      ((b : ℤ) - 1) *
        ∑ k ∈ Finset.Ico (i + 1) (n / 2), outerCoeffZ b n k :=
  coeff_dominates_aux b n hb (n / 2 - i - 1) i (by omega)

/-- The linear reconstruction `Λ`, summed in the outer-gap order. -/
def spectrumValue (b n : ℕ) (g : Fin (n / 2) → Fin b) : ℤ :=
  ∑ k ∈ Finset.range (n / 2), outerCoeffZ b n k * tupleDigit g k

lemma tupleDigit_sub_ge {b m : ℕ} (hb : 1 ≤ b) (g h : Fin m → Fin b) (k : ℕ) :
    -((b : ℤ) - 1) ≤ tupleDigit g k - tupleDigit h k := by
  have hbz : (1 : ℤ) ≤ b := by exact_mod_cast hb
  by_cases hk : k < m
  · have hg : (0 : ℤ) ≤ (g ⟨k, hk⟩).val := by
      exact_mod_cast Nat.zero_le (g ⟨k, hk⟩).val
    have hh : ((h ⟨k, hk⟩).val : ℤ) ≤ ((b - 1 : ℕ) : ℤ) := by
      exact_mod_cast Nat.le_sub_one_of_lt (h ⟨k, hk⟩).isLt
    have hbsub : ((b - 1 : ℕ) : ℤ) = (b : ℤ) - 1 := by omega
    simp only [tupleDigit, hk, dite_true]
    linarith
  · simp only [tupleDigit, hk, dite_false, sub_self]
    omega

lemma sum_range_split {M : Type*} [AddCommMonoid M] {m i0 : ℕ} (hi0 : i0 < m) (f : ℕ → M) :
    ∑ k ∈ Finset.range m, f k =
      ∑ k ∈ Finset.Ico 0 i0, f k + f i0 +
        ∑ k ∈ Finset.Ico (i0 + 1) m, f k := by
  have hunion : Finset.range m = Finset.Ico 0 i0 ∪ Finset.Ico i0 m := by
    ext k
    simp only [Finset.mem_range, Finset.mem_union, Finset.mem_Ico, Nat.zero_le, true_and]
    omega
  have hdisj : Disjoint (Finset.Ico 0 i0) (Finset.Ico i0 m) := by
    rw [Finset.disjoint_left]
    intro k hk hk'
    simp only [Finset.mem_Ico] at hk hk'
    omega
  rw [hunion, Finset.sum_union hdisj, Finset.sum_eq_sum_Ico_succ_bot hi0, add_assoc]

lemma spectrumValue_sub {b n : ℕ} (g h : Fin (n / 2) → Fin b) :
    spectrumValue b n g - spectrumValue b n h =
      ∑ k ∈ Finset.range (n / 2),
        outerCoeffZ b n k * (tupleDigit g k - tupleDigit h k) := by
  simp only [spectrumValue, ← Finset.sum_sub_distrib]
  refine Finset.sum_congr rfl fun k _ => ?_
  ring

lemma spectrumValue_gt_of_first_gap {b n : ℕ} (hb : 2 ≤ b)
    {g h : Fin (n / 2) → Fin b} {i0 : ℕ} (hi0 : i0 < n / 2)
    (hagree : ∀ k, k < i0 → tupleDigit g k = tupleDigit h k)
    (hgt : tupleDigit h i0 < tupleDigit g i0) :
    spectrumValue b n h < spectrumValue b n g := by
  let m := n / 2
  let c := outerCoeffZ b n
  let δ := fun k => tupleDigit g k - tupleDigit h k
  have hsub := spectrumValue_sub (b := b) (n := n) g h
  have hsplit := sum_range_split (m := m) (i0 := i0) hi0 fun k => c k * δ k
  have hhead : ∑ k ∈ Finset.Ico 0 i0, c k * δ k = 0 := by
    refine Finset.sum_eq_zero fun k hk => ?_
    have hk0 : k < i0 := by
      simpa [Finset.mem_Ico] using hk
    simp [δ, hagree k hk0]
  have htail :
      ∑ k ∈ Finset.Ico (i0 + 1) m, c k * (-((b : ℤ) - 1)) ≤
        ∑ k ∈ Finset.Ico (i0 + 1) m, c k * δ k := by
    refine Finset.sum_le_sum fun k hk => ?_
    have hkm : k < m := (Finset.mem_Ico.mp hk).2
    have hc : 0 ≤ c k := le_of_lt (outerCoeffZ_pos hb hkm)
    exact mul_le_mul_of_nonneg_left (tupleDigit_sub_ge (by omega) g h k) hc
  have htail' :
      -((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i0 + 1) m, c k ≤
        ∑ k ∈ Finset.Ico (i0 + 1) m, c k * δ k := by
    have hL :
        ∑ k ∈ Finset.Ico (i0 + 1) m, c k * (-((b : ℤ) - 1)) =
          -((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i0 + 1) m, c k := by
      simp_rw [mul_comm (c _) (-((b : ℤ) - 1))]
      rw [← mul_sum]
    exact hL ▸ htail
  have hδ : (1 : ℤ) ≤ δ i0 := by
    simp only [δ]
    omega
  have hc0 : 0 < c i0 := outerCoeffZ_pos hb hi0
  have hdom : ((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i0 + 1) m, c k < c i0 :=
    coeff_dominates hb hi0
  have hdiff :
      c i0 - ((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i0 + 1) m, c k ≤
        spectrumValue b n g - spectrumValue b n h := by
    rw [hsub, hsplit, hhead, zero_add]
    have hmain : c i0 ≤ c i0 * δ i0 := by
      have : (1 : ℤ) * c i0 ≤ δ i0 * c i0 :=
        mul_le_mul_of_nonneg_right hδ (le_of_lt hc0)
      simpa [mul_comm, one_mul] using this
    linarith
  have hpos :
      0 < c i0 - ((b : ℤ) - 1) * ∑ k ∈ Finset.Ico (i0 + 1) m, c k := by
    linarith
  exact lt_of_sub_pos (lt_of_lt_of_le hpos hdiff)

theorem spectrumValue_injective {b n : ℕ} (hb : 2 ≤ b) :
    Function.Injective fun g : Fin (n / 2) → Fin b => spectrumValue b n g := by
  intro g h heq
  by_contra hne
  have hex : ∃ k, k < n / 2 ∧ tupleDigit g k ≠ tupleDigit h k := by
    by_contra hnot
    push Not at hnot
    apply hne
    funext i
    have hdig : tupleDigit g i.1 = tupleDigit h i.1 := hnot i.1 i.isLt
    apply Fin.ext
    exact Nat.cast_injective (R := ℤ) (by simpa [tupleDigit, i.isLt] using hdig)
  let i0 := Nat.find hex
  have hi0 := Nat.find_spec hex
  have hagree : ∀ k, k < i0 → tupleDigit g k = tupleDigit h k := by
    intro k hk
    have hnot := Nat.find_min hex hk
    rw [not_and] at hnot
    exact not_not.mp (hnot (lt_trans hk hi0.1))
  have hne0 : tupleDigit g i0 ≠ tupleDigit h i0 := hi0.2
  rcases lt_or_gt_of_ne hne0 with hlt | hgt
  · have hdis : spectrumValue b n g < spectrumValue b n h :=
      spectrumValue_gt_of_first_gap (g := h) (h := g) hb hi0.1
        (fun k hk => (hagree k hk).symm) hlt
    exact (ne_of_lt hdis) heq
  · have hdis : spectrumValue b n h < spectrumValue b n g :=
      spectrumValue_gt_of_first_gap hb hi0.1 hagree hgt
    exact (ne_of_lt hdis) heq.symm

theorem spectrumValue_injective_sorted {b n : ℕ} (hb : 2 ≤ b) :
    Function.Injective fun g : SortedSpectrum b (n / 2) => spectrumValue b n g.1 := by
  intro g h heq
  have hfun : g.1 = h.1 := spectrumValue_injective hb heq
  exact Subtype.ext hfun

/--
The one-step image of the linear reconstruction has the stars-and-bars count.
`Finset.card_image_of_injOn` supplies the injective image, and
`gapSpectrumEquivSorted` identifies that domain with `GapSpectrum`.
-/
theorem kaprekarImage_card (b n : ℕ) (hb : 2 ≤ b) :
    Finset.card
        ((Finset.univ : Finset (SortedSpectrum b (n / 2))).image
          fun g => spectrumValue b n g.1) =
      Nat.choose (b + n / 2 - 1) (n / 2) := by
  rw [Finset.card_image_of_injOn (f := fun g => spectrumValue b n g.1)
    (s := (Finset.univ : Finset (SortedSpectrum b (n / 2)))) (by
      intro g _ h _ heq
      exact spectrumValue_injective_sorted hb heq)]
  rw [Finset.card_univ, sortedSpectrum_card]

end Kaprekar
