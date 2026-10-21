# Kittur fort georeferencing pipeline (v3)

Code and data for the manuscript "Open-data georeferencing of 1924 maps and CORONA imagery at Kittur fort, India, with a cross-validated error budget" by Praveen D Chougale (Koita Centre for Digital Health, IIT Bombay; ORCID 0000-0002-5262-4726), prepared for the Journal of Archaeological Science: Reports.

Code: https://github.com/praveenmaths89/kittur-corona-archaeology (tag v1.0-jasr-submission); archived on Zenodo with a DOI at acceptance.

The pipeline georeferences 1924 Survey of India sheets and 1967-68 CORONA KH-4A frames against open reference data (OpenStreetMap, Sentinel-2, GLO-30), validates each transform with independent tie points (check split, leave-one-out, block cross-validation, bootstrap), carries the positional error through every reported measurement by Monte Carlo, and grades each reading of the imagery against a written evidence rule. Transfer tests at Srirangapatna and Hampi are included.

## Contents
- `code/` - pipeline (`run.py`, stages 00-14), library `code/kittur/`, parameters `code/params/`, `config.yaml`, `requirements.txt`, `environment.yml`, `Dockerfile`. See `code/README.md` for the full stage table.
- `data/results/` - stage outputs: `validation.json`, `propagation.json`, `evidence_table.csv`, `validation_sensitivity.csv`, run logs and the other result tables.
- `data/results/validation/` - QA tie sheets for every source: per-tie residuals (`*_ties.csv`), rejected ties (`*_blunders.csv`) and a visual QA sheet (`*_qa.png`).
- `data/vectors/` - digitised 1968 features (GeoPackage).
- `data/blind_grading/`, `data/benchmark_candidates.csv` - blind second-grader sheet and the candidate points from the attempted independent benchmark.
- `data/legacy_v1/` - outputs of the first (exploratory) release, kept for the record; superseded by `data/results/`.
- `manuscript/figures/`, `manuscript/tables/` - the figures and LaTeX tables used in the manuscript.
- `sources/` - transcriptions and the 1884 Gazetteer text; `PROVENANCE.csv` - every input with source, licence and sha256; `LOG.md`, `findings.md`.

## Stages
`python run.py all` runs, in this order: 00 provenance, 01 fetch, 02 preprocess, 03 georeference, 04 dem, 05 metrics, 06 landscape, 07 montecarlo, 12 validation, 13 propagation, 14 evidence, 08 figures, 09 tables, 10 map, 11 lite. Stage numbers are kept stable, so 12-14 run before 08-11. Stage 07 is superseded by stage 13 for the manuscript and kept for the regression record.

## How to rerun
1. Get the inputs: raw CORONA scans from USGS EarthExplorer by entity ID (`M2M_USERNAME` and `M2M_TOKEN` in the environment, then `python code/stages/s01_fetch.py --download corona`), Survey of India sheets from Zenodo 10.5281/zenodo.18133392, OSM with `code/tools/fetch_osm.py`. `PROVENANCE.csv` lists every file with its checksum.
2. Arrange them in a project folder and set `project_root` in `code/config.yaml` to that folder.
3. Install: `pip install -r code/requirements.txt` (Python 3.13) or `conda env create -f code/environment.yml`, or build the container: `docker build -t kittur-pipeline code/`.
4. Run, writing outputs to a scratch folder:
   ```
   cd code
   python run.py --out /tmp/kittur_out all
   python run.py --out /tmp/kittur_out validation     # one stage
   ```
   With Docker: `docker run --rm -v /path/to/project:/data:ro -v /tmp/kittur_out:/out kittur-pipeline python run.py --out /out all`.
5. Compare with `data/results/` (each stage writes its status, timings and checks to `results/run_log.json`). A full run takes about 9 minutes on 8 vCPUs.

## Raw imagery
Raw scans (about 26.5 GB) are not in git. They are listed with checksums in `ZENODO_MANIFEST.csv` and `PROVENANCE.csv` and can be re-downloaded from USGS by scene ID.

## Branches and tags
- `main` - v3 pipeline; tag `v1.0-jasr-submission` marks the state described in the submitted manuscript.
- `pre-v3` - the repository as it was before the v3 update.
- `backup-20261021` - working-folder backup of 21 Oct 2026.

## Licence
- Code: MIT (`LICENSE`).
- Data, figures and tables: CC BY 4.0. OpenStreetMap-derived files: ODbL 1.0.
- CORONA imagery: public domain, courtesy of the U.S. Geological Survey. Survey of India 1924 sheets via Zenodo 10.5281/zenodo.18133392 (CC BY 4.0).

## Citation
See `CITATION.cff`.
