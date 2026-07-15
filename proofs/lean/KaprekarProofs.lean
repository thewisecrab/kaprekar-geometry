import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Algebra.Ring.Parity
import Mathlib.Data.Sym.Card
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

end Kaprekar
