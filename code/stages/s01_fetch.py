"""Stage 01 - fetch / verify raw inputs.

Default: verify every file listed in release/PROVENANCE.csv (sha256) and report missing files.
--download <what>: re-download missing inputs by ID (network). CORONA needs a free USGS M2M
account: set environment variables M2M_USERNAME and M2M_TOKEN (application token). No credentials
are stored in this repository.
--update-provenance: add rows for files present under raw/ (and the SoI scans) that are not yet listed.

Run:  python run.py fetch [--download dem|soi|gazetteer|natural_earth|sentinel|landsat|corona|all] [--update-provenance]
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, urllib.request, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json

CORONA = ['DS1045-1102DA224', 'DS1045-1102DF224', 'DS1045-1102DA223', 'DS1044-2134DA217', 'DS1044-2134DF217']
DEM_URL = 'https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N15_00_E074_00_DEM/Copernicus_DSM_COG_10_N15_00_E074_00_DEM.tif'
SOI_ZENODO = 'https://zenodo.org/api/records/18133392'
GAZ_URL = 'https://archive.org/download/wbsl.17016/wbsl.17016_djvu.txt'
NE = ['https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip',
      'https://naciscdn.org/naturalearth/50m/physical/ne_50m_coastline.zip',
      'https://naciscdn.org/naturalearth/50m/physical/ne_50m_land.zip']
BBOX = (74.45, 15.45, 74.95, 15.90)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def get(url, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        print('GET', url)
        urllib.request.urlretrieve(url, dst)


def dl_dem(C):
    """Copernicus GLO-30 tile -> UTM 43N 30 m subset over BBOX (raw/dem/cop_dem30_elevation.tif)."""
    import numpy as np, rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import reproject, Resampling, calculate_default_transform
    out = C.f(C['inputs']['dem'])
    if out.exists():
        return
    with rasterio.open(DEM_URL) as s:
        w = from_bounds(*BBOX, transform=s.transform).round_offsets().round_lengths()
        a = s.read(1, window=w).astype('float32'); tr = s.window_transform(w); crs = s.crs
    dt, W, H = calculate_default_transform(crs, C['crs'], a.shape[1], a.shape[0], *BBOX, resolution=30)
    d = np.zeros((H, W), 'float32')
    reproject(a, d, src_transform=tr, src_crs=crs, dst_transform=dt, dst_crs=C['crs'], resampling=Resampling.bilinear, dst_nodata=-9999)
    with rasterio.open(out, 'w', driver='GTiff', crs=C['crs'], transform=dt, width=W, height=H, count=1, dtype='float32', nodata=-9999, compress='deflate') as f:
        f.write(d, 1)


def dl_soi(C):
    rec = json.load(urllib.request.urlopen(SOI_ZENODO))
    for f in rec['files']:
        if any(s in f['key'].replace(' ', '_') for s in ['48_I_09', '48_I_10', '48_I_13', '48_I_14']):
            get(f['links']['self'], C.p('soi_scans') / f['key'])


def dl_gazetteer(C):
    get(GAZ_URL, C.p('raw') / 'texts' / 'belgaum1884.txt')


def dl_natural_earth(C):
    for u in NE:
        get(u, C.p('natural_earth') / Path(u).name)


def dl_sentinel(C):
    """Dry-season Sentinel-2 L2A composites (Earth Search) for the epochs and the 17 Feb 2026 reference scene."""
    from stages import _stac
    for ep in ('S2016', 'S2020', 'S2026'):
        _stac.epoch(C, ep)
    _stac.s2_scene(C, 'S2B_43PDT_20260217_0_L2A', 'dry_20260217')


def dl_landsat(C):
    from stages import _stac
    for ep in ('L1990', 'L2000', 'L2010'):
        _stac.epoch(C, ep)


def dl_corona(C):
    api = 'https://m2m.cr.usgs.gov/api/api/json/stable/'
    if not (os.environ.get('M2M_USERNAME') and os.environ.get('M2M_TOKEN')):
        raise SystemExit('Set M2M_USERNAME and M2M_TOKEN (USGS application token) to download CORONA scans.')

    def post(ep, d, key=None):
        r = urllib.request.Request(api + ep, json.dumps(d).encode(), {'Content-Type': 'application/json', **({'X-Auth-Token': key} if key else {})})
        return json.load(urllib.request.urlopen(r))['data']
    key = post('login-token', {'username': os.environ['M2M_USERNAME'], 'token': os.environ['M2M_TOKEN']})
    todo = [e for e in CORONA if not (C.p('raw') / 'corona' / f'{e}.tgz').exists()]
    if not todo:
        return
    opts = post('download-options', {'datasetName': 'corona2', 'entityIds': todo}, key)
    dl = [{'entityId': o['entityId'], 'productId': o['id']} for o in opts if o['available']]
    res = post('download-request', {'downloads': dl, 'label': 'kittur'}, key)
    for d in res.get('availableDownloads', []):
        get(d['url'], C.p('raw') / 'corona' / f"{d.get('entityId', Path(d['url']).stem)}.tgz")


def verify(C, st):
    prov = C.p('provenance')
    rows = list(csv.DictReader(open(prov)))
    ok, bad, missing = 0, [], []
    for r in rows:
        p = C.root / r['file']
        if not p.exists():
            missing.append(r['file']); continue
        if sha(p) == r['sha256']:
            ok += 1
        else:
            bad.append(r['file'])
    st.note(f'provenance: {ok}/{len(rows)} files verified by sha256; {len(bad)} mismatched; {len(missing)} missing')
    for b in bad:
        st.note(f'  sha256 MISMATCH: {b}')
    for m in missing:
        st.note(f'  missing: {m}')
    return dict(n=len(rows), ok=ok, mismatched=bad, missing=missing)


EXTRA = [  # (glob relative to root, source, acquisition, licence, script)
    ('historical_maps/raw/*.jpg', 'Zenodo 10.5281/zenodo.18133392 "Old Survey of India Maps" (scans of SoI one-inch sheets)', 'surveyed 1922-23, publ. 1924', 'CC-BY-4.0 (Zenodo record, checked 2026-10-20)', 'stages/s02_preprocess.py'),
    ('raw/natural_earth/*.zip', 'Natural Earth (naciscdn.org) 1:10m admin-1, 1:50m land and coastline', 'v5', 'Public domain (Natural Earth)', 'stages/s08_figures.py'),
]


def update_provenance(C, st):
    import glob
    prov = C.p('provenance')
    rows = list(csv.DictReader(open(prov)))
    have = {r['file'] for r in rows}
    added = 0
    for pat, src, acq, lic, scr in EXTRA:
        for p in sorted(glob.glob(str(C.root / pat))):
            rel = os.path.relpath(p, C.root)
            if rel in have:
                continue
            rows.append(dict(file=rel, size_MB=round(os.path.getsize(p) / 1e6, 1), source=src, acquisition=acq,
                             download_date=datetime.date.fromtimestamp(os.path.getmtime(p)).isoformat(), license=lic,
                             sha256=sha(p), processing_script=scr, storage='Zenodo/LFS' if os.path.getsize(p) > 100e6 else 'git'))
            added += 1
    with open(prov, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    st.note(f'provenance: {added} rows added')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--download', default=None)
    ap.add_argument('--update-provenance', action='store_true')
    a = ap.parse_args(argv)
    C = load()
    with Stage(C, 'fetch') as st:
        if a.download:
            funcs = dict(dem=dl_dem, soi=dl_soi, gazetteer=dl_gazetteer, natural_earth=dl_natural_earth,
                         sentinel=dl_sentinel, landsat=dl_landsat, corona=dl_corona)
            for k in (funcs if a.download == 'all' else [a.download]):
                funcs[k](C); st.note(f'download {k}: done')
        if a.update_provenance:
            update_provenance(C, st)
        v = verify(C, st)
        save_json(v, C.out('results', 'fetch_verify.json'))


if __name__ == '__main__':
    main()
