# variant-medium720p — H1 collision artifact (2026-10-04)

Second dispatch of handoff H1 upgraded NASA sources from ~mobile (320×180) to
~medium (1280×720) before discovering the first dispatch had already delivered
and the C3b GPU lane had consumed it. Kept as a superseding *variant*, not a
replacement — see ../CURATION.md addendum.

- `sources.medium720p.json` — provenance for this variant (NASA URLs = ~medium)
- `MANIFEST.medium720p.json` — determinized clips manifest (21 clips, injective)
- `sources/` + `clips/` — blobs (gitignored; also in the medium720p tarball)

Commons clips are byte-identical to the primary set; the 5 NASA clips differ
(720p sources). Primary set of truth: ../MANIFEST.json (consumed by C3b run
booked in ad59f41).
