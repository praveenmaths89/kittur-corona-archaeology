# Kittur, Sangolli and the 1824 landscape: findings (v3, 21 Oct 2026)

Status: desk-based, not verified on the ground. Single source of truth: `release/code/run.py all`.
Every number below is read from a pipeline output, shown in brackets:
[VA] `results/validation.json`, [VS] `results/validation_sensitivity.csv`, [PR] `results/propagation.json`,
[EV] `results/evidence_table.csv`, [DEM] `results/dem_stereo.json`, [LS] `results/landscape.json`,
[EM] `results/epoch_metrics.csv`, [TK] `results/osm_tanks_vs_1968.json`, [BF] `results/belgaum_fort.json`,
[T2] `manuscript/tables/Table2_georeferencing_accuracy.csv`, [T3] `manuscript/tables/Table3_dimensions.csv`.
Earlier versions (v1, v2 and every "[untraced]" exploratory figure) are kept only in
`release/backup_pre_v3_20261021/` and are superseded. The manuscript is `manuscript/overleaf/main.tex`.

## 1. Georeferencing (stage 12) [VA; T2]
- Tie points: OSM road junctions, tanks of 1 ha or more and village centres, matched on each source by NCC
  (OSM road raster; Sentinel-2 chip on CORONA). min NCC 0.30 for SoI sheets, 0.20 for all CORONA frames.
- Selection rule (pre-specified, stored in validation.json): simplest of affine, poly2, poly3, regularised TPS
  whose block-CV RMSE is within 10% of the lowest. Headline = block-CV RMSE.
- Before (recorded transform) -> block-CV / LOO (m):
  - Kittur DA224: 120 -> 29.9 / 22.3 (poly2, 25 ties; check 14.1, 95% 6.9-62.7). 20 of 25 ties have NCC < 0.30.
  - Sangolli DF224: 77 -> 29.8 / 20.1 (poly2, 16; check interval 7.7-191.9).
  - Nandagad DA224: 34 -> 36.6 / 13.6 (TPS, 20).
  - Belgaum DA222: 99 -> 19.3 / 10.5 (poly2, 29; 1 blunder). Moran E p = 0.007.
  - SoI 48 I/14: 201 -> 70.6 / 59.9. 48 I/10: 629 -> 55.9 / 57.3. 48 I/09: 159 -> 80.7 / 48.2 (Moran N p = 0.005). All affine.
  - Bonferroni threshold over 18 Moran tests: p < 0.0028. None is significant after correction.
- Transfer, same settings: Srirangapatna DA028 55 -> 13.2 / 12.2 (48 ties, 3 blunders); Hampi DA077 52 -> 11.2 / 5.8
  (69 ties; Moran p 0.003 E, 0.018 N).
- Reference floor: OSM road vs Sentinel-2 position at 44 dual-cue CORONA ties, RMS 10.5 m (median 6.5 m).
- Ties near the fort: 0.27, 0.30, 1.10, 1.59, 1.94 km from the lower fort; next at 3.6 km.

## 2. Sensitivity of the Kittur result [VS]
- min_ncc 0.15: 30 ties, LOO 8.6, block-CV 18.7. 0.25: 9 ties, LOO 32.3. 0.30: 2 ties (not scored).
- agree_m 10 / 20: block-CV 28.3 / 31.0. min_sep 400 / 500: 38.7 / 45.6. Junctions only: 11 ties, LOO 39.5.
- Target errors used by stage 13 (v4): measured block-CV per setting, LOO x 1.344 where block-CV is missing: 18.7-53.1 m, sampled uniformly over the 8 settings [PR error_budget].

## 3. The fort in 1968 (stage 13, 200 realisations, seed 1824) [PR; T3]
- Error budget: bootstrap transform; local error scaled to a target block-CV RMSE drawn from the 8 per-setting values (18.7-53.1 m);
  5 m systematic digitising offset per feature (assumed); 4 m vertex noise.
- Lower fort 13.01 ha (median 13.04; 95% 11.66-14.19). N/W moat band 1041 m (1027-1059). East outer line 528 m (515-541).
- Ponds: NW 0.22 ha (0.01-0.63), E 0.46 ha (0.16-0.90).
- Hillock rings: outer 6.73 ha (5.85-7.75), middle 3.67 (2.82-4.46), core 1.61 (1.13-2.19).
- Lower fort to citadel core 535 m (median 539; 464-613), bearing 203 deg (192-211).
- Component 95% half-widths (100 realisations each, viewsheds skipped): lower-fort area digitising 1.51 ha vs full 1.26; east pond digitising 0.23 vs full 0.37; distance transform 55 m, tie threshold 64 m, full 75 m; threshold adds nothing to areas.
- IoU with OSM fort outline 0.78 (median 0.73; 0.54-0.82); centroid offset 24 m (median 34; 6-88).
- Claims: citadel SSW of the lower fort 100%; distance 450-650 m 98.5%; relief > 20 m 100%;
  citadel sees more than the lower fort within 5 km 100%; IoU > 0.5 98.5%.
- 1924 sheet 48 I/14: spot height 2528 ft (770.5 m) on the hillock; GLO-30 summit 769.4 m.
- Lawe's fractions: Belgaum 40.5 ha (Gazetteer), 51.8 ha (OSM), 58.0 ha (DA222 inner wall) [BF] give a lower fort
  of 6.75-9.67 ha and a citadel of 4.05-5.80 ha. Measured lower fort is larger; outer ring within the citadel range.
  Ratio 0.6 (Lawe) vs 0.52 (outer ring / lower fort). Consistency check only.

## 4. Terrain [PR; DEM; LS]
- "Nowhere commanded" under GLO-30 error (share with no higher cell within 1.5 km / nothing > 3 m higher):
  SD 2 m 43% / 87% (canopy 42 / 83); SD 3 m 34 / 68 (39 / 73); SD 5 m 34 / 54 (25 / 44). Not testable at this DSM quality.
- Clearly higher ground: 786.7 m at 1.74 km SW [LS].
- Viewshed within 5 km (720 rays to 10 km, observer 10 m): citadel 33.7 km2, lower fort 22.4 km2 (21.1-22.8).
  Stage 06 values (35.8 and 23.3 km2) use 2880 rays to 25 km and are not comparable.
- 1967 stereo surface (noise 7.7 m): citadel core minus 220-320 m annulus +29.6 m (GLO-30 +25.6 m); lower fort +1.9 m
  (GLO-30 +4.9 m); core centre 2.4 m higher than rim [DEM]. No quarry depression.

## 5. Old Sangoli [PR; EM]
- 1968 village centre moved 44 m after re-georeferencing; now 17 m outside the OSM reservoir outline; inside in 17.5%
  of realisations, within 100 m of the shore in 100%. Dry in the 2026 dry-season median. 3.24 km N of present Sangolli.
- Dry-season open water within 600 m: 0.1 ha (1990-91), 0.5 (2000), 11.4 (2009), 11.7 (2016-17), 99.4 (2020), 47.3 (2026) [EM].

## 6. Other change [EM; TK]
- Hillock NDVI contrast: +0.032 (1990), +0.180 (2020), +0.167 (2026).
- OSM water bodies of 1 ha or more within 15 km: 29; 7 dark in Jan 1968, 3 intermediate, 10 no water signature,
  9 outside coverage; largest (133.9 ha) not water in 1968. Indicative (10 m mosaic, extrapolated affines).

## 7. Evidence grades (stage 14) [EV]
- Rule: confirmed >= 2 positional sources support and none contradicts; plausible 1; unsupported 0;
  contradicted >= 1 contradicts. Gazetteer and archival letters support kind only.
- Confirmed 5: lower fort, hillock, east pond, Old Sangoli village, Belgaum moat.
- Plausible 2: hillock rings, 7 pre-1968 tanks.
- Unsupported 7: N/W moat, east outer line, NW pond, Sangoli fort, Sampgaon trace, Tigadi perimeter, siege positions.
- Contradicted 1: dark core = Lawe's quarry (SoI spot height and GLO-30 summit).
- Siege positions and the quarry are reported in the Discussion only. Single grader; blind sheet in
  `manuscript/blind_grading/`, kappa via `release/code/tools/kappa.py`.

## 8. Open items (need a person or the field)
- Second analyst: >= 20 VHR GCPs and checkpoints, >= 8 within 2 km of the fort.
- GNSS checkpoints; rigorous KH-4A camera model (ASP or Ghuffar et al. 2022).
- Second blind grader and kappa; repeat digitising (n >= 3) to replace the assumed 5 m digitising SD.
- Zenodo deposit (draft metadata in `release/zenodo/`).
