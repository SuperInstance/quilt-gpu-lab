//! Standalone harness: includes the REAL slackwater-rust eisenstein.rs verbatim
//! (via #[path]) so a cross-language conformance test can be compiled+run without
//! touching the source repo. DO NOT COMMIT; scratch/dogfood only.
#[path = "/home/eileen/projects/slackwater-rust/crates/lattice-core/src/eisenstein.rs"]
pub mod eisenstein;
pub use eisenstein::EisensteinPoint;
