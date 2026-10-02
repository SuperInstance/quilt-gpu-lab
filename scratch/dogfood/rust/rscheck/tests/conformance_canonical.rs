//! CANONICAL control test (lane-authored) — asserts the real slackwater-rust
//! EisensteinPoint against hand-computed Z[ω] vectors. Ground truth for the
//! granite conformance attempt in tests/conformance.rs.
//!
//! Every expected value here is derived by hand from ω² = -1 - ω:
//!   mul: (a+bω)(c+dω) = (ac-bd) + (ad+bc-bd)ω
//!   norm: a² - ab + b² ; conj: (a-b, -b) ; rotate by ω: (-b, a-b)
use lattice_core::EisensteinPoint as E;

#[test]
fn add_sub_componentwise() {
    assert_eq!(E::new(1, 2).add(&E::new(3, -1)), E::new(4, 1));
    assert_eq!(E::new(0, 0).add(&E::new(-5, 7)), E::new(-5, 7));
    assert_eq!(E::new(3, 3).add(&E::new(3, -3)), E::new(6, 0));
    assert_eq!(E::new(1, 2).sub(&E::new(3, -1)), E::new(-2, 3));
    assert_eq!(E::new(-4, 5).sub(&E::new(-1, -2)), E::new(-3, 7));
    // operator forms
    assert_eq!(E::new(1, 2) + E::new(3, -1), E::new(4, 1));
    assert_eq!(E::new(1, 2) - E::new(3, -1), E::new(-2, 3));
}

#[test]
fn norm_values() {
    assert_eq!(E::new(3, -2).norm(), 19); // 9 + 6 + 4
    assert_eq!(E::new(0, 0).norm(), 0);
    assert_eq!(E::new(2, 3).norm(), 7); // 4 - 6 + 9
    assert_eq!(E::new(-1, -1).norm(), 1); // unit ω²
}

#[test]
fn conjugate_values() {
    assert_eq!(E::new(3, -2).conjugate(), E::new(5, 2));
    assert_eq!(E::new(1, 1).conjugate(), E::new(0, -1)); // conj(1+ω) = -ω
    assert_eq!(E::new(-2, 5).conjugate(), E::new(-7, -5));
}

#[test]
fn hexdist_values() {
    assert_eq!(E::new(0, 0).lattice_distance(&E::new(2, 1)), 2);
    assert_eq!(E::new(0, 0).lattice_distance(&E::new(2, -1)), 3);
    assert_eq!(E::new(1, 1).lattice_distance(&E::new(4, 4)), 3);
    assert_eq!(E::new(0, 0).lattice_distance(&E::new(0, 5)), 5);
}

#[test]
fn norm_is_multiplicative_identity_check() {
    // We cannot call mul (slackwater EisensteinPoint has none — GAP), but we can
    // assert the identity on the reference: (3-2ω)(1+ω) = 5+3ω, and
    // norm(5+3ω) = 25-15+9 = 19 = 19*1.
    assert_eq!(E::new(5, 3).norm(), E::new(3, -2).norm() * E::new(1, 1).norm());
}

/// GAP-1: slackwater-rust EisensteinPoint has NO multiplication, NO div_rem,
/// NO gcd — so the ring structure is only partially implemented. This test is
/// #[ignore]d as documentation; the canonical mul/div vectors live in
/// canonical_vectors.json and must be run against a type that has them.
#[test]
#[ignore = "GAP-1: EisensteinPoint lacks mul/div_rem/gcd"]
fn ring_ops_missing() {}

/// BUG-1: rotate_60 claims to be "multiplication by ω" but returns (a-b, a),
/// while true ω-multiplication is (-b, a-b). This test documents the divergence.
#[test]
fn bug1_rotate_60_is_not_omega_multiplication() {
    let z = E::new(1, 0);
    // ω-mult of 1 is ω = (0,1); slackwater returns (1,1).
    assert_eq!(z.rotate_60(), E::new(0, 1), "rotate_60(1,0) should be ω=(0,1)");
}
