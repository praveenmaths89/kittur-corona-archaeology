# Blind second grading of the CORONA readings

Purpose: an independent check of the evidence grades (Table 8). The second grader must not see
`release/code/params/evidence.yaml`, `results/evidence_table.csv` or the manuscript before finishing.

1. Open `second_grader_sheet.csv`. Each row is one reading (what the first analyst saw on CORONA 1967-68) and
   one independent source to check it against. Rows are in random order.
2. For each row, look at that source only, at the place named, using the panels in `previews/evidence_kittur.png`,
   `previews/evidence_old_sangoli.png` and the re-georeferenced crops in `derived/soi/` and `derived/corona/*_v2.tif`.
3. Fill `verdict_second_grader` with exactly one of: `support`, `neutral`, `contradict`, `n/a`.
   - support: the source shows a feature of that kind at that place;
   - contradict: the source shows something incompatible (for example a summit where the reading says a pit);
   - neutral: the source neither shows nor rules out the feature (not resolved, covered, built over);
   - n/a: the source does not cover the place.
4. Save the file under a new name, for example `second_grader_<initials>.csv`, and run
   `python release/code/tools/kappa.py manuscript/blind_grading/second_grader_<initials>.csv`.

The script reports Cohen's kappa for the per-source verdicts and for the final grades (the same grading
rule applied to both analysts' verdicts), and lists every disagreement.

Repeat digitising (same person or a second analyst): trace the lower-fort inner wall line and the three citadel
rings three times on `derived/corona/corona_1968_kittur_v2.tif`, at least a day apart, without looking at earlier
traces. Save each as a polygon layer in `repeat_digitising/<initials>_<n>.gpkg` (EPSG:32643, field `id` with
the feature ids `lower_fort`, `ring_outer`, `ring_middle`, `ring_core`). The spread of these traces replaces the
assumed 5 m digitising term (`propagation.digitising_sd_m` in config.yaml).
