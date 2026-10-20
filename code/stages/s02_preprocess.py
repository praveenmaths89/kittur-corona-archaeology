"""Stage 02 - preprocess base layers.

* Copernicus GLO-30 (UTM 43N, 30 m): hillshade (az 315, alt 45), slope, local relief (500 m window).
* Survey of India 1924 one-inch sheets 48 I/09, 10, 13, 14: four-corner (15' graticule) affine georeference
  of the scans (EPSG:4326). Positional error is of the order of 100s of m; used for qualitative comparison only.
* CORONA: make sure every scan piece listed in config.corona.frames is available (extracts from raw/corona/*.tgz).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_gcps
from rasterio.control import GroundControlPoint as G
from scipy.ndimage import uniform_filter
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, corona

Image.MAX_IMAGE_PIXELS = None


def dem_derivatives(C, st):
    with rasterio.open(C.f(C['inputs']['dem'])) as s:
        d = s.read(1).astype('float32'); T = s.transform
    z = np.where(d == -9999, np.nan, d)
    zf = np.where(np.isnan(z), np.nanmean(z), z)
    gy, gx = np.gradient(zf, 30)
    slope = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
    az, alt = np.radians(315), np.radians(45)
    hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - asp)
    out = C.p('derived') / 'dem'
    geo.write_tif(out / 'cop_dem30_hillshade.tif', np.clip(hs * 255, 0, 255).astype('uint8'), T, nodata=0)
    geo.write_tif(out / 'cop_dem30_slope_deg.tif', np.degrees(slope).astype('float32'), T, nodata=-9999)
    geo.write_tif(out / 'cop_dem30_localrelief_500m.tif', (zf - uniform_filter(zf, size=17)).astype('float32'), T, nodata=-9999)
    st.note(f'DEM {d.shape}, z {np.nanmin(z):.1f}-{np.nanmax(z):.1f} m; hillshade, slope, local relief written')
    leg = C.p('legacy_rasters') / 'cop_dem30_hillshade.tif'
    if leg.exists():
        st.note(f'  hillshade vs legacy: {geo.compare(out / "cop_dem30_hillshade.tif", leg)}')


def soi_georef(C, st):
    res = {}
    for sheet, s in C['inputs']['soi_sheets'].items():
        im = Image.open(C.p('soi_scans') / s['file']).convert('RGB')
        sc = im.size[0] / s['ref_width']
        a = np.array(im).transpose(2, 0, 1)
        X0, Y0, X1, Y1 = [v * sc for v in s['corners']]
        lon0, lat1 = s['nw']
        t = from_gcps([G(Y0, X0, lon0, lat1), G(Y0, X1, lon0 + .25, lat1), G(Y1, X0, lon0, lat1 - .25), G(Y1, X1, lon0 + .25, lat1 - .25)])
        o = C.out('derived', 'soi', f'SoI_{sheet}_1924_cornergeoref.tif')
        with rasterio.open(o, 'w', driver='GTiff', width=a.shape[2], height=a.shape[1], count=3, dtype='uint8', crs='EPSG:4326',
                           transform=t, compress='jpeg', photometric='YCBCR', tiled=True) as d:
            d.write(a)
        leg = sorted((C.p('raw') / 'soi').glob(f'SoI_{sheet}_*roughgeoref.tif'))
        if leg:
            with rasterio.open(leg[0]) as L:
                dt = max(abs(a_ - b_) for a_, b_ in zip(L.transform, t))
            res[sheet] = dict(max_transform_diff=dt)
        st.note(f'SoI {sheet}: {a.shape[2]}x{a.shape[1]} px, {o.name}; transform diff vs raw/soi: {res.get(sheet)}')
    return res


def corona_pieces(C, st):
    need = {(e, f['piece']) for e, f in C['corona']['frames'].items()}
    need |= {(v['entity'], v['piece']) for v in C['corona']['coreg_1967'].values()}
    for e, p in sorted(need):
        path = corona.scan_path(C, e, p)
        st.note(f'CORONA {e}_{p}: {path.relative_to(C.root)} ({path.stat().st_size / 1e6:.0f} MB)')


def main(argv=None):
    C = load()
    with Stage(C, 'preprocess') as st:
        dem_derivatives(C, st)
        r = soi_georef(C, st)
        corona_pieces(C, st)
        save_json(r, C.out('results', 'preprocess.json'))


if __name__ == '__main__':
    main()
