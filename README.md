# Kittur CORONA Archaeology

Reconstructing Kittur Fort (Belagavi district, Karnataka) and its 1824 siege landscape by combining declassified CORONA satellite photographs (1967-68), Survey of India sheets (1924), colonial military records (1824-28) and modern Landsat / Sentinel-2 imagery. The same pipeline is applied to comparison sites (Belgaum, Srirangapatna, Hampi and regional forts).

## Contents
- `code/` - 12-stage pipeline (`python code/run.py all`), stages 00 provenance to 11 lite; pinned environment in `code/requirements.txt` / `code/environment.yml`
- `config.yaml` - run configuration
- `data/` - small derived datasets (vector features, metrics, Monte Carlo and viewshed results); `data/results/` holds stage outputs
- `manuscript/figures`, `manuscript/tables` - submission figures (TIFF/PDF) and tables
- `sources/` - transcriptions of 1824 records (automatic handwriting recognition, not yet checked against page images), Belgaum Gazetteer (1884) text, gazetteer
- `findings.md`, `lit_gap.md`, `LOG.md`, `PROVENANCE.csv`
- `ZENODO_MANIFEST.csv` - list of raw scans (path, size, sha256) deposited on Zenodo

## Raw imagery (Zenodo)
Raw CORONA scans and other large inputs (about 26.5 GB, 78 files) are not in git. They are archived at Zenodo: DOI 10.5281/zenodo.XXXXXXX (placeholder).

They can also be re-downloaded from USGS EarthExplorer by scene ID. Create a free USGS account, generate an M2M application token, then:

    export M2M_USERNAME=your_usgs_username
    export M2M_TOKEN=your_application_token
    python code/legacy/fetch_raw.py          # or: python code/stages/s01_fetch.py --download corona

Checksums in `ZENODO_MANIFEST.csv` and `PROVENANCE.csv` verify the files.

## Licence
- Code: MIT (see `LICENSE`)
- Data, figures and tables: CC-BY-4.0
- CORONA imagery: public domain, courtesy of the U.S. Geological Survey. Sentinel-2: Copernicus data terms. Landsat: USGS public domain.
