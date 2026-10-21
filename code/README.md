# Kittur pipeline (release/code)

Reproducible pipeline for the Kittur fort desk study: CORONA georeferencing, 1967 stereo surface, change metrics,
viewshed/least-cost analysis, Monte Carlo uncertainty, comparison sites (Srirangapatna, Hampi, Belgaum), journal
figures and tables. All paths come from **one file, `config.yaml`** (`project_root: ../..` = the `kittur_map/` folder);
no stage contains absolute or old working-tree paths. No credentials are stored anywhere: the only authenticated
download (USGS M2M, CORONA) reads `M2M_USERNAME` / `M2M_TOKEN` from the environment.

## Install
```
pip install -r requirements.txt          # or: conda env create -f environment.yml
```
Python 3.13 (tested 3.13.5, Linux). Figures need the Arial font (see environment.yml); LibreOffice is optional
(only used to proof the DOCX tables).

## Run order
```
cd release/code
python run.py all                  # 00-07, then 12-14, then 08-11 (see the order below)
python run.py --out /tmp/k all     # same, but every output goes under /tmp/k; the deposited tree is not touched
python run.py <stage> [args]       # one stage
python run.py validation figure    # redraw Table 2b and Fig. S8 from saved results only
```
Order of `all`: provenance (00), fetch (01), preprocess (02), georeference (03), dem (04), metrics (05),
landscape (06), montecarlo (07), validation (12), propagation (13), evidence (14), figures (08), tables (09),
map (10), lite (11). Module numbers are kept stable, so 12-14 run before 08-11.

Runtime (one machine, 8 vCPU Xeon, 15 GB RAM, Linux, Python 3.13): validation 160 s, propagation 65 s, evidence
1 s, tables 1 s; the stage timings in `results/run_log.json` add up to about 9 min for a full `all`. Container: see `Dockerfile`.

| # | Stage | Script | Reads | Writes |
|---|---|---|---|---|
| 00 | provenance | stages/s00_provenance.py | raw/, historical_maps/raw/, sites/*/raw/ | release/PROVENANCE.csv (sha256, source, licence), results/sha256_cache.json |
| 01 | fetch | stages/s01_fetch.py | release/PROVENANCE.csv | results/fetch_verify.json; with `--download <what>` re-fetches inputs by ID |
| 02 | preprocess | stages/s02_preprocess.py | DEM, SoI scans, CORONA archives | derived/dem (hillshade, slope, relief), derived/soi (corner georeference), extracted scan pieces |
| 03 | georeference | stages/s03_georeference.py | scans + params/*.json | derived/corona/*.tif (DA224, DF224, DA223, 1967 DA217/DF217, 15 km mosaic, comparison sites), results/georef_accuracy.json, georef_regression.json |
| 04 | dem | stages/s04_dem.py | 1967 co-registered pair, GLO-30 | derived/dem/corona1967_dem_kittur*.tif, results/dem_stereo.json |
| 05 | metrics | stages/s05_metrics.py | features, epochs, OSM, sites | derived/vectors/*.gpkg, results/features_1968.csv, epoch_metrics.csv, osm_tanks_vs_1968.json, site_metrics.json, belgaum_fort.json, sites_epoch_metrics.csv |
| 06 | landscape | stages/s06_landscape.py | GLO-30, features | derived/landscape/viewshed_*.tif, derived/vectors/landscape.gpkg, results/landscape.json |
| 07 | montecarlo | stages/s07_montecarlo.py | features, DEMs | results/montecarlo.json, montecarlo_samples.npz (N = 1000, seed 1824). Superseded for the manuscript by stage 13 (assumed error model; kept for the regression record) |
| 08 | figures | stages/s08_figures.py | derived/, results/ | manuscript/figures/*.tif + *.pdf, figure_captions.md, figure_specs.json; previews/sites_overview.png, sites_timeline.png, timeline_<site>.png |
| 09 | tables | stages/s09_tables.py | results/, params/archival.yaml | manuscript/tables/*.csv, tables.docx, tables.xlsx, table_captions.md |
| 10 | map | stages/s10_map.py | qgis/rasters, vectors, sites/ (folium) | kittur_basemap.html, web/ |
| 11 | lite | stages/s11_lite.py | base map, previews, manuscript | ../kittur_map_lite/, ../kittur_basemap_lite.zip |

`python run.py figures fig03 fig09` regenerates selected figures; every stage appends its status, timing and notes to
`results/run_log.json`. Each stage that has an earlier (exploratory) counterpart checks itself against it
(`legacy_*` paths in config.yaml) and reports the agreement in the run log.

## Library (`kittur/`)
`config.py` (config loader, `Stage` logger), `geo.py` (UTM 43N helpers, resampling, raster comparison), `corona.py`
(scan pieces, affine sampling, SIFT/RANSAC/polynomial co-registration), `features.py` (1968 feature digitisation from
params/features_1968.yaml), `figstyle.py` (journal figure style: Arial 7-9 pt, Okabe-Ito/cividis, km grids, scale bars,
north arrows, panel labels; 600 dpi LZW TIFF + vector PDF with embedded TrueType fonts).

## Parameters (`params/`)
Recorded transforms and manual inputs, all small text files: `gcp_*.json`, `df224_F2.json`, `da223_*.json` (affines),
`checkpoints_*.{json,yaml}` (independent checkpoints), `features_1968.yaml` (digitised features, scan pixels),
`belgaum_moat.yaml` (Belgaum moat trace), `archival.yaml` (quoted archival statements for Table 4),
`provenance_sources.yaml` (provenance rules). Comparison-site affines are read from `sites/<name>/corona/*_fit.json`.

## Georeferencing provenance
The 1968 DA224/DF224 and DA223 affines and the comparison-site fits were estimated interactively during the
exploratory phase (chained patch matching, manual checks; scripts kept in `legacy/`). The pipeline **re-applies the
recorded transforms** to the raw scans and re-measures their accuracy (checkpoints, automatic patch NCC); it does
not re-estimate them. The 1967 DA217/DF217 co-registration and the stereo surface are re-estimated from scratch
(stage 03/04); see release/LOG.md for the differences from the exploratory results.

## Not exercised automatically
- `fetch --download` (network). The stage verifies all raw inputs by sha256; downloads were tested in the exploratory
  phase only. Comparison-site epochs and scenes are fetched with `sites/common/epoch_fetch.py` and `fetch_s2.py`.
- Locating new CORONA frames for new sites (`sites/common/locate.py`, `refine.py`): interactive, recorded in the fit JSON.
- The interactive base map (`../../build.py`, folium) is copied, not rebuilt, by stage 10.

## Folders
- `legacy/`: exploratory scripts (base/, corona/, analysis/, epochs/, fetch_raw.py, make_provenance.py), kept for
  provenance only; they use the old working-tree paths and are not called by the pipeline.
- `sites/`: per-site acquisition scripts copied from `sites/common` (not pipeline stages).
- `make_provenance.py`: wrapper for `python run.py provenance`.

## Desk validation stages (added 21 Oct 2026)
| No. | Stage | Script | Output |
|---|---|---|---|
| 12 | validation | stages/s12_validation.py (+ kittur/validate.py) | independent OSM/S2 tie points for 4 CORONA and 3 SoI sources; affine/poly2/poly3/TPS with check split, LOO, block CV, bootstrap, Moran's I; results/validation.json, results/validation/, Table2b, FigS8, v2 crops, params/validation_models/, sensitivity csv |
| 13 | propagation | stages/s13_propagation.py | empirical (bootstrap + LOO) positional error, vertex noise, model alternatives and DSM noise carried to areas, distance, OSM overlap, viewsheds, commanding ground, Old Sangoli; results/propagation.json, derived/vectors/corona1968_features_v2.gpkg |
| 14 | evidence | stages/s14_evidence.py (+ params/evidence.yaml) | rule-based grade per CORONA reading; results/evidence_table.csv, Table8_evidence.csv, previews/evidence_*.png |

## v3 changes (21 Oct 2026, after the independent review)
- `--out DIR` / env `KITTUR_OUT`: outputs (derived, results, previews, manuscript figures/tables, fitted models)
  go under DIR; inputs are read from project_root.
- Stage 12: the TPS is regularised (smoothing chosen from 1, 10, 100, 1000 by control-point LOO; zero smoothing is
  no longer a candidate). The selection rule is written to `validation.json → selection_rule`, and each target
  lists the matching parameters actually used (`params_effective`; Kittur-area targets use min_ncc 0.20).
  Two transfer targets (Srirangapatna DA028, Hampi DA077) use their own OSM extract (`tools/fetch_osm.py`) and
  Sentinel-2 scene. The sensitivity run adds a variant without tank and village ties.
- Stage 13: the local error is topped up to the block-CV RMSE (headline), with a per-realisation target drawn
  from the tie-threshold sensitivity range; a 5 m systematic digitising offset per feature; DSM scenarios with
  SD 2, 3 and 5 m, with and without a one-sided canopy bias (NDVI > 0.45).
- Stage 14: fourth grade 'contradicted'; `placement` moves interpretive readings to the Discussion.
- Stage 09: Table 2 and Table 3 come from stages 12 and 13 only (the stage-07 and v1 tables are retired).
- `tools/kappa.py` and `../../manuscript/blind_grading/`: blind second-grader sheet and Cohen's kappa.

## Exploratory scripts
The scripts in the project root (`prev.py`, `prev2.py`, `wd.py`, `s1.py`, `s2.py`, `georef.py`, `georef2.py`,
`build_pre_corona.py`, `ls.py`, `dem.py`, `osm.py`) and `legacy/` are exploratory. They are not called by the
pipeline and are excluded from the Zenodo deposit (`../zenodo/MANIFEST.txt`).
