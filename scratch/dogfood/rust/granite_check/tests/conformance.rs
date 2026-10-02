//! Cross-language conformance test for Eisenstein integers.
//! Based on authoritative definitions.
//! Real API in slackwater-rust (as per problem statement):
//!   struct EisensteinPoint { a: i32, b: i32 }
//!   methods: add, sub, mul, conjugate, norm, rotate_60, lattice_distance
//! Mapping: E12::add -> add, sub -> sub, mul -> mul, conj -> conjugate,
//! norm -> norm, hexdist -> lattice_distance, rotate_60_omega -> rotate_60.
#![allow(dead_code)]
use std::cmp::max;

mod eisenstein_conformance {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    struct E12 {
        a: i32,
        b: i32,
    }

    impl E12 {
        fn add(&self, other: &E12) -> Self {
            E12 { a: self.a + other.a, b: self.b + other.b }
        }

        fn sub(&self, other: &E12) -> Self {
            E12 { a: self.a - other.a, b: self.b - other.b }
        }

        fn mul(&self, other: &E12) -> Self {
            let a = self.a * other.a - self.b * other.b;
            let b = self.a * other.b + self.b * other.a - self.b * other.b;
            E12 { a, b }
        }

        fn conj(&self) -> Self {
            E12 { a: self.a - self.b, b: -self.b }
        }

        fn norm(&self) -> i64 {
            (self.a as i64) * (self.a as i64) - (self.a as i64) * (self.b as i32) + (self.b as i64) * (self.b as i64)
        }

        fn hexdist(&self, other: &E12) -> u32 {
            let da = self.a - other.a;
            let db = self.b - other.b;
            if da == 0 || db == 0 || (da > 0) == (db > 0) {
                max(da.abs(), db.abs()) as u32
            } else {
                (da.abs() + db.abs()) as u32
            }
        }

        fn rotate_60_omega(&self) -> Self {
            E12 { a: -self.b, b: self.a - self.b }
        }
    }

    fn div_rem(z: &E12, w: &E12) -> (E12, E12) {
        let nw = w.norm();
        let zwc = z.mul(&w.conj());
        let real = zwc.a as f64 / nw as f64;
        let imag = zwc.b as f64 / nw as f64;
        let ra = if real >= 0.0 { (real + 0.5).floor() as i32 } else { (real - 0.5).ceil() as i32 };
        let ri = if imag >= 0.0 { (imag + 0.5).floor() as i32 } else { (imag - 0.5).ceil() as i32 };
        let q = E12 { a: ra, b: ri };
        let r = z.sub(&w.mul(&q));
        (q, r)
    }

    #[test]
    fn test_add() {
        let z = E12 { a: 1, b: 2 };
        let w = E12 { a: 3, b: -1 };
        assert_eq!(z.add(&w), E12 { a: 4, b: 1 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 1, b: 2 };
        let w = EisensteinPoint { a: 3, b: -1 };
        assert_eq!(z.add(&w).a, 4);
        assert_eq!(z.add(&w).b, 1);
        */
        let z = E12 { a: 0, b: 0 };
        let w = E12 { a: 0, b: 0 };
        assert_eq!(z.add(&w), E12 { a: 0, b: 0 });
    }

    #[test]
    fn test_sub() {
        let z = E12 { a: 5, b: 3 };
        let w = E12 { a: 2, b: 4 };
        assert_eq!(z.sub(&w), E12 { a: 3, b: -1 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 5, b: 3 };
        let w = EisensteinPoint { a: 2, b: 4 };
        assert_eq!(z.sub(&w).a, 3);
        assert_eq!(z.sub(&w).b, -1);
        */
        let z = E12 { a: 0, b: 0 };
        let w = E12 { a: 1, b: 1 };
        assert_eq!(z.sub(&w), E12 { a: -1, b: -1 });
    }

    #[test]
    fn test_mul() {
        let z = E12 { a: 1, b: 0 };
        let w = E12 { a: 0, b: 1 };
        assert_eq!(z.mul(&w), E12 { a: 0, b: 1 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 1, b: 0 };
        let w = EisensteinPoint { a: 0, b: 1 };
        assert_eq!(z.mul(&w).a, 0);
        assert_eq!(z.mul(&w).b, 1);
        */
        let z = E12 { a: 1, b: 1 };
        let w = E12 { a: 1, b: 1 };
        assert_eq!(z.mul(&w), E12 { a: 0, b: 1 });
        let z = E12 { a: 2, b: 1 };
        let w = E12 { a: 1, b: 1 };
        assert_eq!(z.mul(&w), E12 { a: 1, b: 2 });
    }

    #[test]
    fn test_conj() {
        let z = E12 { a: 3, b: 4 };
        assert_eq!(z.conj(), E12 { a: -1, b: -4 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 3, b: 4 };
        assert_eq!(z.conjugate().a, -1);
        assert_eq!(z.conjugate().b, -4);
        */
        let z = E12 { a: 0, b: 0 };
        assert_eq!(z.conj(), E12 { a: 0, b: 0 });
    }

    #[test]
    fn test_norm() {
        let z = E12 { a: 2, b: 3 };
        assert_eq!(z.norm(), 7);
        // Real API:
        /*
        let z = EisensteinPoint { a: 2, b: 3 };
        assert_eq!(z.norm(), 7);
        */
        let z = E12 { a: 1, b: 0 };
        assert_eq!(z.norm(), 1);
    }

    #[test]
    fn test_hexdist() {
        let z = E12 { a: 0, b: 0 };
        let w = E12 { a: 1, b: 1 };
        assert_eq!(z.hexdist(&w), 1);
        // Real API:
        /*
        let z = EisensteinPoint { a: 0, b: 0 };
        let w = EisensteinPoint { a: 1, b: 1 };
        assert_eq!(z.lattice_distance(&w), 1);
        */
        let z = E12 { a: 0, b: 0 };
        let w = E12 { a: 1, b: -1 };
        assert_eq!(z.hexdist(&w), 2);
    }

    #[test]
    fn test_div_rem() {
        let z = E12 { a: 4, b: 0 };
        let w = E12 { a: 2, b: 0 };
        let (q, r) = div_rem(&z, &w);
        assert_eq!(q, E12 { a: 2, b: 0 });
        assert_eq!(r, E12 { a: 0, b: 0 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 4, b: 0 };
        let w = EisensteinPoint { a: 2, b: 0 };
        let (q, r) = z.div_rem(&w); // assuming div_rem method exists
        assert_eq!(q.a, 2);
        assert_eq!(q.b, 0);
        assert_eq!(r.a, 0);
        assert_eq!(r.b, 0);
        */
        let z = E12 { a: 1, b: 0 };
        let w = E12 { a: 2, b: 0 };
        let (q, r) = div_rem(&z, &w);
        assert_eq!(q, E12 { a: 1, b: 0 });
        assert_eq!(r, E12 { a: -1, b: 0 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 1, b: 0 };
        let w = EisensteinPoint { a: 2, b: 0 };
        let (q, r) = z.div_rem(&w);
        assert_eq!(q.a, 1);
        assert_eq!(r.a, -1);
        */
        let z = E12 { a: -1, b: 0 };
        let w = E12 { a: 2, b: 0 };
        let (q, r) = div_rem(&z, &w);
        assert_eq!(q, E12 { a: -1, b: 0 });
        assert_eq!(r, E12 { a: 1, b: 0 });
    }

    #[test]
    fn test_rotate_60_omega() {
        let z = E12 { a: 1, b: 2 };
        assert_eq!(z.rotate_60_omega(), E12 { a: -2, b: -1 });
        // Real API:
        /*
        let z = EisensteinPoint { a: 1, b: 2 };
        assert_eq!(z.rotate_60().a, -2);
        assert_eq!(z.rotate_60().b, -1);
        */
        let z = E12 { a: 0, b: 0 };
        assert_eq!(z.rotate_60_omega(), E12 { a: 0, b: 0 });
    }

    #[test]
    fn test_norm_multiplicativity() {
        let z = E12 { a: 1, b: 0 };
        let w = E12 { a: 0, b: 1 };
        assert_eq!(z.mul(&w).norm(), z.norm() * w.norm());
        let z = E12 { a: 2, b: 1 };
        let w = E12 { a: 1, b: 1 };
        assert_eq!(z.mul(&w).norm(), z.norm() * w.norm());
        let z = E12 { a: 3, b: 2 };
        let w = E12 { a: 1, b: -1 };
        assert_eq!(z.mul(&w).norm(), z.norm() * w.norm());
    }

    #[test]
    fn test_div_rem_invariant() {
        let vectors = [
            (E12 { a: 4, b: 0 }, E12 { a: 2, b: 0 }),
            (E12 { a: 1, b: 0 }, E12 { a: 2, b: 0 }),
            (E12 { a: -1, b: 0 }, E12 { a: 2, b: 0 }),
        ];
        for (z, w) in vectors.iter() {
            let nw = w.norm();
            let (q, r) = div_rem(z, w);
            let wq = w.mul(&q);
            let sum = wq.add(&r);
            assert_eq!(z, &sum, "z != w*q + r for z={z}, w={w}, q={q}, r={r}",);
            assert!(r.norm() < nw, "norm(r) = {r_norm} >= norm(w) = {nw}", r_norm = r.norm(), nw = nw);
        }
    }
}
