# Kittur fort and landscape, 1824-2026: reproducible desk study
All interpretations are tentative (see ../findings.md). No fieldwork.

## Layout (proposed for the public repo; multi-site)
```
sites/kittur/            <- this folder (kittur_map) moves here
  raw/                   inputs exactly as downloaded (large -> Zenodo, not git)
  derived/ (qgis/rasters, epochs/*.tif)   regenerable -> Zenodo or regenerate
  code/                  = release/code (git)
  data/                  small vectors, CSV, JSON results (git)
  previews/, findings.md, web map (git; PNG/JPG < 5 MB each)
  PROVENANCE.csv, LOG.md, README.md (git)
sites/srirangapatna/, sites/belgaum_fort/, sites/hampi/   same structure
common/                  shared code (georeferencing, viewshed, Monte Carlo)
```
- Git: code, README/LOG/PROVENANCE, findings, figures, vectors, CSV/JSON. Files > 100 MB cannot go into plain GitHub.
- Large raw data (CORONA .tgz 0.65-0.88 GB each, the multi-GB extracted scans, S2/S1 subsets): deposit on Zenodo (one versioned record per site, CC0 for USGS public-domain data, with Copernicus attribution) and record its DOI in PROVENANCE.csv. Git LFS works too but is quota-limited, so Zenodo is preferred. `code/fetch_raw.py` re-downloads everything by ID instead.
- Check redistribution rights before depositing SoI 1924 scans: link the Zenodo record 10.5281/zenodo.18133392 rather than re-uploading, unless its licence allows it.

## Reproduce
Config-based pipeline in `code/` (one `config.yaml`, one script per stage): see `code/README.md`.
```
cd release/code && pip install -r requirements.txt && python run.py all
```
Stages: provenance, fetch (sha256 verification; `--download` re-fetches by ID), preprocess, georeference, dem, metrics,
landscape, montecarlo, figures (manuscript/figures), tables (manuscript/tables), lite (../kittur_map_lite).
Run status and regression checks: `results/run_log.json` and `LOG.md`. The exploratory scripts are in `code/legacy/`
(provenance only; they use the original working-tree paths).

## Licences / provenance
| Data | Licence |
|---|---|
| CORONA KH-4A (USGS) | Public domain |
| Landsat C2 (USGS) | Public domain |
| Sentinel-1/2 | Copernicus free & open, attribution: "Contains modified Copernicus Sentinel data 2016-2026" |
| Copernicus DEM GLO-30 | Copernicus DEM licence, attribution required |
| SoI 1924 sheets | Zenodo 10.5281/zenodo.18133392, CC-BY-4.0 (checked 20 Oct 2026) |
| OSM | ODbL 1.0 |
| Gazetteer 1884 | Public domain |
| Esri/Google imagery | viewed only, not redistributed or analysed |
| Project code / derived data | proposed MIT (code) + CC-BY 4.0 (data) |
Per-file sha256: PROVENANCE.csv.

## Figures
| File | Content |
|---|---|
| previews/findings_fort1968.png, findings_ring.png | 1968 fort and citadel interpretation |
| previews/findings_anaglyph_1967_fort.png, findings_dem1967.png | 1967 stereo |
| previews/findings_sangolli.png, compare_sangolli.png | Old Sangoli |
| previews/findings_timeline.png (+_strip, _metrics) | 1924-2026 change |
| previews/findings_viewshed.png | Task A viewsheds / commanding ground |
| previews/findings_approaches.png | least-cost paths, tentative siege zones |
| previews/findings_regional.png | Gazetteer forts, 1968 vs 2026 |
| previews/findings_3d.png, ../kittur_3d_rotate.mp4 | schematic 3D c.1824 |
