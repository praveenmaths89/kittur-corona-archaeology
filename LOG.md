# Processing log (all times IST, UTC+5:30)
## 2026-10-20
- Base map built: S2 L2A (Earth Search), S1 RTC (Planetary Computer), Landsat 5 1999, Copernicus GLO-30, SoI 1924 sheets 48 I/09,10,13,14 (Zenodo 18133392), OSM (Overpass). Scripts: code/base/.
- ~17:05-17:38 CORONA downloaded from USGS EarthExplorer (DA224, DF224, DA223, DA217, DF217); extracted into corona/.
- DA224 piece b: local affines chained from Nandagad (RMS 21 m) to Kittur (manual final shift); crops at 2 m (corona/coarse.py, g2r.py, pm2.py, rew.py).
- DF224 piece c: affine F2 (df224_F2.json), Sangolli RMS 26 m.
- DA217/DF217 co-registered to the 1968 Kittur crop (SIFT + 2nd-order polynomial, RMS 1.7/2.9 m); SGBM stereo DEM (corona1967_dem_kittur*.tif).
- Epochs 1990-2026 (code/epochs/), metrics.csv, timeline figure.
- ~19:00 Task A battle-landscape GIS (code/analysis/battle.py, figA.py): viewsheds, commanding ground, least-cost paths, tentative siege zones.
- Task B: DA223 coarse frame match (corona/reg223.py, reg223b.py, NCC 0.27) and 4x4 km crops at Sampgaon, Bailhongal, Old Sangoli, Tigadi; 15 km 1968 mosaic (analysis/mosaic15.py); OSM tanks vs 1968 (tanks15.py); regional figure (figB.py). tanks.py = automatic dark-blob test, rejected (false positives).
- Task C: Monte Carlo N=1000 (analysis/montecarlo.py).
- Task D: 3D render + MP4 (analysis/recon3d.py; ffmpeg libx264 12 fps).
- ~19:20 Raw CORONA .tgz copied from ~/Downloads to raw/corona/ (originals kept; sha256 identical, raw/corona/SHA256.txt). Other raw inputs copied into raw/. DS1040-1039DA028.tgz was still being written at 19:20 and was NOT copied.
- ~20:20 Three more sites added under sites/ (see sites/*/LOG.md). Zenodo SoI record licence checked: CC-BY-4.0.
- 2026-10-20 20:44 IST: epoch timelines for 3 sites; Belgaum L2010 (LE07); map rebuilt

## 2026-10-20 21:11 IST — reproducible pipeline (release/code) + journal figures/tables
- Pipeline: release/code/run.py with stages 00 provenance, 01 fetch, 02 preprocess, 03 georeference, 04 dem, 05 metrics, 06 landscape, 07 montecarlo, 08 figures, 09 tables, 10 lite; single config.yaml (project root relative); pinned requirements.txt / environment.yml. results/run_log.json: all 11 stages ok.
- make_provenance fixed (legacy copy resolved release/release/PROVENANCE.csv): now stage 00 → release/PROVENANCE.csv, 104 files incl. raw/epochs and Belgaum/Srirangapatna/Hampi CORONA raws, sha256; 22 cross-checked vs SHA256.txt, 0 mismatches.
- Mission labels corrected: all frames are KH-4A (missions 1001–1052), not KH-4/KH-4B.
- Belgaum added (DA222 fit, fort trace params/belgaum_moat.yaml: inner 58.0 ha, centreline 61.3 ha, outer 64.8 ha; OSM 51.8 ha; Gazetteer "about 100 acres" = 40.5 ha), Fig09 3 rows, Fig10 cross-site timelines, FigS6 per-site strips, Table 7 cross-site; previews/sites_overview.png, sites_timeline.png, timeline_<site>.png regenerated.
- Regression vs legacy: CORONA crops r=1.0; site crops r≥0.999; 1967 DA/DF co-registration re-fitted r 0.93/0.94; epoch metrics and sites_epoch_metrics (42 rows) diff 0; Belgaum digitization diff 0; Monte Carlo areas exact.
- Stereo DEM reimplemented (legacy script missing): SGBM bs 15, high-pass σ16, disparity −16/32, uniqueness 10, scale −0.293 px/m; citadel relief 40.4 m (21.5–60.2) vs legacy 35.8 m; noise 7.7 m; r=0.56 vs legacy DEM.
- Discrepancies with findings.md: tanks 7 dark/3 intermediate/10 none/9 outside (findings "0 dark" wrong); battery zone 0.40 ha vs 0.05 ha; Nandagad checkpoints 106 pts RMS 30.4 m vs 98 pts/21 m; Kittur checkpoints n=3 RMS 28.4 m; auto-NCC RMS Kittur 123 m, Belgaum 74.9 m.
- Not exercised: fetch --download (needs M2M_USERNAME/M2M_TOKEN + network); kittur_basemap.html copied not rebuilt (folium absent).
- Checklist: all figure checks met (600 dpi LZW TIFF, PDF Type42 Arial, 7–9 pt, widths 90/140/190 mm); DOCX/XLSX no vertical rules.
- Lite copy refreshed: ../kittur_map_lite (64 MB), ../kittur_basemap_lite.zip (60 MB), large layers WebP.
- 2026-10-20 21:18 IST: findings.md reconciled to pipeline results/ and tables/ (backup release/findings_pre_reconcile_20261020.md); new stage 10 map (folium 0.20.0), lite -> stage 11; Table 4 Belgaum row fixed (p. 534, oval 52.5 ha); Kittur georef refine attempt -> results/georef_kittur_refine.json (not applied)

## 2026-10-21 (IST) - desk validation (stages 12-14)
- Backup before changes: /workspace/kittur_map_backup_20261021 (full copy). Raw data untouched.
- New: kittur/validate.py; stages s12_validation.py, s13_propagation.py, s14_evidence.py; params/evidence.yaml; params/validation_models/*.json; config blocks `validation`, `propagation`; run.py order 00-07, 12-14, 08-11.
- Outputs: results/validation.json, results/validation/*_ties.csv, *_blunders.csv, *_qa.png, results/validation_sensitivity.csv, results/propagation.json, results/evidence_table.csv, manuscript/tables/Table2b_georeferencing_validation.csv, Table8_evidence.csv, manuscript/figures/FigS8_georef_residuals.png/.pdf, previews/evidence_kittur.png, evidence_old_sangoli.png, derived/corona/corona_1968_kittur_v2.tif, corona_1968_sangolli_v2.tif, derived/soi/SoI_48_I_14_1924_kittur_sangolli_v2.tif, derived/vectors/corona1968_features_v2.gpkg.
- `python run.py all`: all 15 stages ok (log results/run_all_20261021.log).
- Not yet propagated into Tables 3/T4 or main figures (stage 07 / v1 numbers still there); to switch at the writing stage.
