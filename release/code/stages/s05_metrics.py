"""Stage 05 - features and change metrics.

* Builds the digitised 1968 feature layer (derived/vectors/corona1968_features.gpkg, UTM 43N + WGS 84 copy).
* Epoch metrics 1990-2026 (dry-season Landsat/Sentinel-2 medians on a common 10 m grid): NDVI, MNDWI > 0.1 water,
  indicative bare/built class (NDBI > -0.05 and NDVI < 0.25, not water) for areas of interest; NDVI contrast of the
  fort enclosure and citadel mound against an 80 m outer buffer.
* Tanks within 15 km of Kittur: OpenStreetMap water polygons >= 1 ha vs the 1968 CORONA mosaic tone (inside / 40-150 m ring).
* Comparison sites (Srirangapatna, Hampi, Belgaum; plus Kittur): 2026 Sentinel-2 classes and crude 1960s tone classes in the 5 x 5 km crop.
* Belgaum fort: moat traced on the 1968 DA222 crop (params/belgaum_moat.yaml) -> areas, perimeter, extents.
* Comparison-site epochs (sites/<name>/raw/epochs): the Kittur index thresholds within 1.5 and 2.5 km of each site centre
  (and inside the Belgaum fort inner line) -> results/sites_epoch_metrics.csv.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import cv2
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, features

YEAR = {'L1990': 1990, 'L2000': 2000, 'L2010': 2009, 'S2016': 2017, 'S2020': 2020, 'S2026': 2026}


def indices(b):
    bl, g, r, n, sw = b
    with np.errstate(invalid='ignore', divide='ignore'):
        ndvi = (n - r) / (n + r + 1e-6); ndbi = (sw - n) / (sw + n + 1e-6); mndwi = (g - sw) / (g + sw + 1e-6)
    water = mndwi > 0.1
    built = (ndbi > -0.05) & (ndvi < 0.25) & ~water
    return ndvi, water, built


def epoch_metrics(C, F, st):
    fort, ring, moat = F.loc['lower_fort'].geometry, F.loc['ring_outer'].geometry, F.loc['moat_nw'].geometry
    pt = lambda k: Point(*geo.ll2utm(C['points'][k][1], C['points'][k][0]))
    oldS, newS = pt('Old Sangoli (1968 village)'), pt('Sangolli (present)')
    aois = {'kittur_1.5km': fort.centroid.buffer(1500), 'fort_enclosure': fort, 'ring_outer': ring, 'moat_15m': moat.buffer(15),
            'oldSangoli_600m': oldS.buffer(600), 'newSangolli_600m': newS.buffer(600), 'sangolli_valley_3km': oldS.buffer(3000)}
    rows = []
    for ep, base in C['inputs']['epochs'].items():
        with rasterio.open(C.f(base + '.tif')) as s:
            b = s.read(); T = s.transform
        meta = json.load(open(C.f(base + '.json')))
        ndvi, water, built = indices(b)
        for k, G in aois.items():
            m = geometry_mask([G], out_shape=ndvi.shape, transform=T, invert=True) & np.isfinite(ndvi)
            rows.append(dict(epoch=ep, year=YEAR[ep], scenes=';'.join(d for _, d, _ in meta), n_scenes=len(meta), aoi=k,
                             built_frac=round(float(built[m].mean()), 3), water_frac=round(float(water[m].mean()), 3),
                             ndvi=round(float(np.nanmean(ndvi[m])), 3), built_ha=round(float(built[m].sum() * 100 / 1e4), 1),
                             water_ha=round(float(water[m].sum() * 100 / 1e4), 1)))
        for k, G in [('ring_outer', ring), ('fort_enclosure', fort)]:
            inn = geometry_mask([G], out_shape=ndvi.shape, transform=T, invert=True)
            out = geometry_mask([G.buffer(80).difference(G)], out_shape=ndvi.shape, transform=T, invert=True)
            rows.append(dict(epoch=ep, year=YEAR[ep], aoi=k + '_contrast', ndvi=round(float(np.nanmean(ndvi[inn]) - np.nanmean(ndvi[out])), 3),
                             built_frac=round(float(built[inn].mean() - built[out].mean()), 3)))
    d = pd.DataFrame(rows)
    d.to_csv(C.out('results', 'epoch_metrics.csv'), index=False)
    st.note(f'epoch metrics: {len(d)} rows -> results/epoch_metrics.csv')
    leg = C.root / 'epochs' / 'metrics.csv'
    if leg.exists():
        L = pd.read_csv(leg)
        m = d.merge(L, on=['epoch', 'aoi'], suffixes=('', '_legacy'))
        dmax = max(float((m[c] - m[c + '_legacy']).abs().max()) for c in ('ndvi', 'built_frac'))
        st.note(f'  regression vs legacy epochs/metrics.csv: max |diff| ndvi/built_frac = {dmax:.4f} over {len(m)} rows')
    return d


def tanks(C, st):
    D = C.p('derived') / 'corona'
    m = rasterio.open(D / 'corona_1968_mosaic15km_10m.tif'); A = m.read(1).astype(float)
    S = rasterio.open(D / 'corona_1968_mosaic15km_source.tif').read(1)
    g = gpd.read_file(C.f(C['inputs']['osm']))
    w = g[(g.category == 'water') & g.geom_type.isin(['Polygon', 'MultiPolygon'])].to_crs(C['crs'])
    k = Point(*geo.ll2utm(C['points']['Kittur fort'][1], C['points']['Kittur fort'][0]))
    k = gpd.GeoSeries([Point(74.785, 15.598)], crs=4326).to_crs(C['crs'])[0]     # mosaic centre used in the original inventory
    w = w[(w.centroid.distance(k) < 15000) & (w.area > 1e4)].copy()
    rows = []
    for _, r in w.iterrows():
        gin = r.geometry; ring = gin.buffer(150).difference(gin.buffer(40))
        mi = ~geometry_mask([gin], A.shape, m.transform); mo = ~geometry_mask([ring], A.shape, m.transform)
        cov = float((S[mi] > 0).mean()) if mi.any() else 0
        lo, la = geo.utm2ll(gin.centroid.x, gin.centroid.y)
        d = dict(osm_id=r.get('osm_id'), name=r.get('name'), lat=round(la, 5), lon=round(lo, 5), area2026_ha=round(gin.area / 1e4, 1),
                 dist_km=round(gin.centroid.distance(k) / 1000, 1), corona_cover=round(cov, 2))
        if cov > 0.8 and (S[mo] > 0).mean() > 0.8:
            ti, to = np.median(A[mi & (S > 0)]), np.median(A[mo & (S > 0)]); d['tone_ratio_in_out'] = round(ti / to, 2)
            d['status_1968'] = 'dark in 1968 (pre-1968 tank)' if ti / to < 0.75 else ('intermediate' if ti / to < 0.9 else 'no water signature in 1968')
        else:
            d['status_1968'] = 'outside 1968 coverage'
        rows.append(d)
    rows.sort(key=lambda d: -d['area2026_ha'])
    save_json(rows, C.out('results', 'osm_tanks_vs_1968.json'))
    import collections
    st.note(f'tanks: {len(rows)} OSM water bodies >= 1 ha within 15 km: {dict(collections.Counter(d["status_1968"] for d in rows))}')
    return rows


def site_metrics(C, st):
    out = {}
    runs = [(site, C.p('derived') / 'corona' / f'corona_{site}.tif', C.f(g['s2'])) for site, g in C['sites'].items()]
    # Kittur, for the cross-site table: the 5 km DA224 crop against the 2026 dry-season Sentinel-2 median (same band order)
    runs.append(('kittur', C.p('derived') / 'corona' / 'corona_1968_kittur.tif', C.f(C['inputs']['epochs']['S2026'] + '.tif')))
    for site, cpath, s2path in runs:
        c = rasterio.open(cpath); Cc = c.read(1).astype(np.float32)
        B = np.zeros((5, Cc.shape[0] // 5, Cc.shape[1] // 5), np.float32); tr = c.transform * c.transform.scale(5, 5)
        with rasterio.open(s2path) as s:
            for k in range(5):
                reproject(s.read(k + 1), B[k], src_transform=s.transform, src_crs=s.crs, dst_transform=tr, dst_crs=c.crs, resampling=Resampling.average)
        bl, gr, rd, nir, sw = B
        ndvi = (nir - rd) / (nir + rd + 1e-6); mndwi = (gr - sw) / (gr + sw + 1e-6); ndbi = (sw - nir) / (sw + nir + 1e-6)
        water26 = mndwi > 0.1; veg26 = (ndvi > 0.4) & ~water26; built26 = (ndbi > 0.0) & (ndvi < 0.25) & ~water26
        C10 = cv2.resize(Cc, (Cc.shape[1] // 5, Cc.shape[0] // 5), interpolation=cv2.INTER_AREA); valid = C10 > 8
        sd = cv2.resize(np.sqrt(np.maximum(cv2.blur(Cc * Cc, (15, 15)) - cv2.blur(Cc, (15, 15)) ** 2, 0)), C10.shape[::-1], interpolation=cv2.INTER_AREA)
        p15 = np.percentile(C10[valid], 15)
        water60 = valid & (C10 < p15) & (sd < np.percentile(sd[valid], 30)); veg60 = valid & (C10 < np.percentile(C10[valid], 30)) & ~water60
        M = dict(site=site, water_1960s_pct=float(100 * water60[valid].mean()), darkveg_1960s_pct=float(100 * veg60[valid].mean()),
                 water_2026_pct=float(100 * water26[valid].mean()), veg_2026_pct=float(100 * veg26[valid].mean()), built_2026_pct=float(100 * built26[valid].mean()))
        out[site] = M
        np.save(C.out('derived', 'sites', f'{site}_classes2026.npy'), (veg26 * 1 + built26 * 2 + water26 * 3).astype(np.uint8))
        st.note(f'{site}: ' + ', '.join(f'{k} {v:.1f}' for k, v in M.items() if k != 'site'))
    save_json(out, C.out('results', 'site_metrics.json'))
    return out


def belgaum_fort(C, st):
    """Belgaum fort outline from the moat trace on the regenerated DA222 crop."""
    import yaml
    from shapely.geometry import Polygon
    from rasterio.transform import xy
    P = yaml.safe_load(open(C.code(C['belgaum_fort']['trace'])))
    with rasterio.open(C.p('derived') / 'corona' / 'corona_belgaum.tif') as r:
        T = r.transform
    oy, ox = P['offset_row'], P['offset_col']
    outer = Polygon([xy(T, y + oy, x + ox) for x, y in P['vertices']])
    hw = P['moat_half_width_m']
    centre, inner, glacis = outer.buffer(-hw), outer.buffer(-2 * hw), outer.buffer(P['glacis_m'])
    osm = gpd.read_file(C.f(C['inputs']['osm'])).to_crs(C['crs'])
    import yaml as _y
    A = _y.safe_load(open(C.code('params/archival.yaml')))
    osm_ha = float(osm[osm.osm_id == A['belgaum_fort_osm']].geometry.area.iloc[0] / 1e4)
    b = centre.bounds
    res = dict(moat_centreline_ha=centre.area / 1e4, inner_wall_line_ha=inner.area / 1e4, moat_outer_edge_ha=outer.area / 1e4,
               with_glacis_ha=glacis.area / 1e4, moat_area_ha=(outer.area - inner.area) / 1e4, perimeter_centreline_m=centre.length,
               osm_way_ha=osm_ha, gazetteer_ha=C['belgaum_fort']['gazetteer_acres'] * 0.404686, ew_m=b[2] - b[0], ns_m=b[3] - b[1])
    g = gpd.GeoDataFrame(dict(name=['moat_outer_edge', 'moat_centreline', 'inner_wall_line', 'glacis_50m']),
                         geometry=[outer, centre, inner, glacis], crs=C['crs'])
    p = C.out('derived', 'vectors', 'belgaum_fort_1968.gpkg')
    g.to_file(p, layer='belgaum_utm43n', driver='GPKG'); g.to_crs(4326).to_file(p, layer='belgaum_wgs84', driver='GPKG')
    save_json(res, C.out('results', 'belgaum_fort.json'))
    leg = C.f(C['belgaum_fort']['legacy'])
    if leg.exists():
        L = json.load(open(leg))['res']
        d = max(abs(L[k] - res[k]) for k in ('moat_centreline_ha', 'inner_wall_line_ha', 'perimeter_centreline_m', 'ew_m', 'ns_m'))
        st.note(f'  regression vs sites/belgaum/analysis/fort_digitized.json: max |diff| = {d:.3f}')
    st.note('belgaum fort: ' + ', '.join(f'{k} {v:.1f}' for k, v in res.items()))
    return res


def site_epochs(C, st):
    """Dry-season epoch metrics around each comparison site (same thresholds as Kittur)."""
    from shapely.geometry import shape
    E = C['site_epochs']; rows = []
    for site, (la, lo) in E['centres_latlon'].items():
        x, y = geo.ll2utm(lo, la)
        aois = {f'r{r}m': Point(x, y).buffer(r) for r in E['radii_m']}
        if site == 'belgaum':
            g = gpd.read_file(C.p('derived') / 'vectors' / 'belgaum_fort_1968.gpkg', layer='belgaum_utm43n')
            aois['fort_inner'] = g[g.name == 'inner_wall_line'].geometry.iloc[0]
        for ep in E['epochs']:
            f = C.p('sites') / site / 'raw' / 'epochs' / f'{ep}.tif'
            if not f.exists():
                st.note(f'  {site} {ep}: missing, skipped'); continue
            with rasterio.open(f) as r:
                b = r.read(); T = r.transform
            ndvi, water, built = indices(b)
            meta = json.load(open(f.with_suffix('.json')))
            dates = [d for _, d, _ in meta['items']]
            yr = int(np.median([int(d[:4]) for d in dates]))
            for k, G in aois.items():
                m = geometry_mask([G], out_shape=ndvi.shape, transform=T, invert=True) & np.isfinite(ndvi)
                rows.append(dict(site=site, epoch=ep, year=yr, aoi=k, scenes=';'.join(dates), n_scenes=len(dates),
                                 built_frac=round(float(built[m].mean()), 3), water_frac=round(float(water[m].mean()), 3),
                                 ndvi=round(float(np.nanmean(ndvi[m])), 3)))
    d = pd.DataFrame(rows); d.to_csv(C.out('results', 'sites_epoch_metrics.csv'), index=False)
    st.note(f'site epochs: {len(d)} rows; ' + ', '.join(f'{s}: {n} epochs' for s, n in d[d.aoi == "r1500m"].groupby("site").size().items()))
    leg = C.f(E['legacy'])
    if leg.exists():
        L = pd.read_csv(leg); L = L[L.epoch != 'CORONA']
        m = d.merge(L, on=['site', 'epoch', 'aoi'], suffixes=('', '_leg'))
        if len(m):
            dm = max((m[c] - m[c + '_leg']).abs().max() for c in ('built_frac', 'water_frac', 'ndvi'))
            st.note(f'  regression vs {E["legacy"]}: max |diff| = {dm:.4f} over {len(m)} rows')
    return d


def main(argv=None):
    C = load()
    with Stage(C, 'metrics') as st:
        F = features.build(C)
        p = C.out('derived', 'vectors', 'corona1968_features.gpkg')
        F.reset_index(drop=True).to_file(p, layer='features_utm43n', driver='GPKG')
        F.reset_index(drop=True).to_crs(4326).to_file(p, layer='features_wgs84', driver='GPKG')
        F.drop(columns='geometry').to_csv(C.out('results', 'features_1968.csv'), index=False)
        st.note('features: ' + '; '.join(f'{i} {a} ha' for i, a in F.area_ha.dropna().items()))
        epoch_metrics(C, F, st)
        tanks(C, st)
        site_metrics(C, st)
        belgaum_fort(C, st)
        site_epochs(C, st)


if __name__ == '__main__':
    main()
