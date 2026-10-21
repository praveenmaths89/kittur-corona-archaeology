"""Stage 13 - carry the EMPIRICAL georeferencing uncertainty (stage 12) through the downstream results.

The digitised 1968 features (params/features_1968.yaml, pixels of the v1 2 m Kittur grid) are mapped back to
CORONA scan pixels through the recorded transform and forward again through
  * the chosen stage-12 model fitted to all ties ('v2' nominal positions), and
  * an ensemble of B models fitted to bootstrap resamples of the ties, plus a per-feature local error whose
    variance tops the bootstrap spread up to the leave-one-out error of the chosen model.
For every realisation the stage recomputes: feature positions and their shift from v1, areas, the fort-citadel
distance, overlap of the lower-fort polygon with the OSM fort outline (way/97204879), the citadel observer and
its commanding-ground test (higher DEM cells within 1.0 and 1.5 km), summit relief, and viewsheds from the
citadel and the lower fort (Copernicus GLO-30, 720 rays, 10 km; the full 2880-ray, 25 km viewshed of stage 06
is the nominal reference). For Old Sangoli the 1968 village point is propagated through the DF224 ensemble and
tested against the OSM reservoir outline (Renuka Sagara, way/57897786) and against open water (MNDWI > 0)
in the dry-season 2026 Sentinel-2 median.
Model uncertainty: the nominal metrics are also given for the affine, poly2 and TPS families fitted to all ties.
Vertical uncertainty: the commanding-ground test is repeated with spatially correlated DSM noise.
Outputs: results/propagation.json (nominal, median, 95 % interval, and the fraction of realisations in which
each qualitative finding holds), derived/vectors/corona1968_features_v2.gpkg.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import cv2
import rasterio
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import features, validate as V, geo


def load_model(C, name):
    J = json.load(open(C.code(f'params/validation_models/{name}.json')))
    uv, en = np.array(J['uv']), np.array(J['en'])
    return J, uv, en


def ensemble(C, J, uv, en, B, target=None):
    """Nominal model, B bootstrap models and the per-axis local sd that tops the bootstrap spread up to the
    target error. v3: the target is the leave-spatial-block-out RMSE (the headline accuracy), not the LOO."""
    nom = V.Model(J['kind'], J['smoothing']).fit(uv, en)
    Ms = V.bootstrap_models(uv, en, J['kind'], J['smoothing'], B, C['seed'])
    spread = np.mean([np.sum(np.var(np.array([M(uv) for M in Ms]), axis=0), axis=1)])   # mean 2-D variance at ties
    target = target or J.get('block_cv_rmse_m', J['loo_rmse_m'])
    loc_sd = np.sqrt(max(target ** 2 - spread, 0) / 2)
    return nom, Ms, float(loc_sd), float(np.sqrt(spread))


def threshold_targets(C, J, B, rng):
    """Per-realisation target RMSE that carries the tie-acceptance sensitivity (stage 12) into the budget.
    v4 (round-2 review): each sensitivity setting with >= 8 ties contributes ONE value, its MEASURED block-CV
    RMSE; only where block-CV could not be computed (too few ties outside a block) is its LOO RMSE scaled by the
    baseline block-CV / LOO ratio. Each realisation draws one setting at random (equal weight per setting), so
    the budget never extends beyond the values actually observed."""
    import pandas as pd
    f = C.p('results') / 'validation_sensitivity.csv'
    if not f.exists():
        return np.full(B, J['block_cv_rmse_m']), None
    d = pd.read_csv(f); d = d[(d.n_ties >= 8) & d.loo_rmse_m.notna()].copy()
    ratio = J['block_cv_rmse_m'] / J['loo_rmse_m']
    d['target_m'] = np.where(d.block_cv_rmse_m.notna(), d.block_cv_rmse_m, d.loo_rmse_m * ratio)
    d['source'] = np.where(d.block_cv_rmse_m.notna(), 'block-CV (measured)', 'LOO x ratio')
    vals = d.target_m.to_numpy()
    return rng.choice(vals, B), dict(per_setting={r.setting: dict(target_m=float(r.target_m), source=r.source, n_ties=int(r.n_ties))
                                                  for r in d.itertuples()},
                                     blockcv_scale=ratio, target_range_m=[float(vals.min()), float(vals.max())],
                                     n_settings=int(len(d)), sampling='uniform over settings')


def main(argv=None):
    C = load(); P = C['propagation']
    with Stage(C, 'propagation') as st:
        rng = np.random.default_rng(C['seed']); B = P['n']
        # ---------------- Kittur features: v1 UTM -> scan -> v2 UTM
        J, uv, en = load_model(C, 'corona_da224_kittur')
        Trec = np.array(J['T_rec'])                                  # UTM -> scan (recorded)
        nom, Ms, loc_sd, boot_sd = ensemble(C, J, uv, en, B)
        st.note(f"Kittur: {J['kind']} on {len(uv)} ties, LOO {J['loo_rmse_m']:.1f} m; bootstrap spread {boot_sd:.1f} m, local sd {loc_sd:.1f} m/axis")
        F = features.build(C)
        to_scan = lambda xy: np.c_[Trec[0, 0] * xy[:, 0] + Trec[0, 1] * xy[:, 1] + Trec[0, 2], Trec[1, 0] * xy[:, 0] + Trec[1, 1] * xy[:, 1] + Trec[1, 2]]
        coords = {i: np.array(g.exterior.coords if g.geom_type == 'Polygon' else g.coords) for i, g in zip(F.index, F.geometry)}
        scan = {i: to_scan(c) for i, c in coords.items()}

        DIG = P.get('digitising_sd_m', 0.0)       # systematic line-placement error per feature (analyst error)

        def geoms(model, shifts=None, vnoise=0.0, dig=0.0):
            """Feature geometries under one transform. vnoise: independent noise per vertex; dig: one random
            offset of the whole traced line per feature (outward/inward for polygons, sideways for lines), the
            dominant term when a wall is traced by eye on 2 m imagery."""
            out = {}
            for i, s in scan.items():
                xy = model(s) + (0 if shifts is None else shifts[i])
                if vnoise:                                   # digitising noise per vertex (as stage 07)
                    xy = xy + rng.normal(0, vnoise, xy.shape)
                    if F.loc[i, 'kind'] != 'line':
                        xy[-1] = xy[0]
                if F.loc[i, 'kind'] != 'line':
                    g = Polygon(xy).buffer(0)
                    out[i] = g.buffer(rng.normal(0, dig), join_style=2) if dig else g
                else:
                    out[i] = LineString(xy + (rng.normal(0, dig, 2) if dig else 0))
            return out
        G0 = geoms(nom)
        gpd.GeoDataFrame(dict(id=list(G0), name=list(F.name), kind=list(F.kind)), geometry=list(G0.values()), crs=C['crs']).to_file(
            C.out('derived', 'vectors', 'corona1968_features_v2.gpkg'), layer='corona1968_features_v2', driver='GPKG')
        osm = gpd.read_file(C.f(C['inputs']['osm'])).to_crs(C['crs'])
        fort_osm = osm[osm.osm_id == 'way/97204879'].geometry.iloc[0]
        resv = osm[osm.osm_id == 'way/57897786'].geometry.iloc[0]
        # DEM and viewshed helpers
        d = rasterio.open(C.f(C['inputs']['dem'])); Z = d.read(1).astype(float); T = d.transform
        cols, rows = np.meshgrid(np.arange(Z.shape[1]), np.arange(Z.shape[0])); X, Y = T * (cols + 0.5, rows + 0.5)
        zat = lambda x, y: map_coordinates(Z, [np.atleast_1d((~T * (x, y))[1]) - 0.5, np.atleast_1d((~T * (x, y))[0]) - 0.5], order=1)

        def viewshed_km2(x0, y0, rmax):
            z0 = zat(x0, y0)[0] + C['viewshed']['eye_height_m']; ds = np.arange(10, rmax, 10.0); k = C['viewshed']['refraction_k']
            vis = np.zeros(Z.shape, bool)
            for a in np.linspace(0, 2 * np.pi, P['rays'], endpoint=False):
                xs, ys = x0 + ds * np.sin(a), y0 + ds * np.cos(a); c_, r_ = ~T * (xs, ys); r_, c_ = r_ - .5, c_ - .5
                zz = map_coordinates(Z, [r_, c_], order=1) - ds ** 2 * (1 - k) / (2 * 6371000)
                ang = (zz - z0) / ds; v = ang >= np.maximum.accumulate(np.r_[-1e9, ang[:-1]])
                ok = v & (r_ >= 0) & (c_ >= 0) & (r_ < Z.shape[0] - 1) & (c_ < Z.shape[1] - 1)
                vis[np.round(r_[ok]).astype(int), np.round(c_[ok]).astype(int)] = True
            D = np.hypot(X - x0, Y - y0)
            return float((vis & (D < 5000)).sum() * 900 / 1e6), float((vis & (D < rmax)).sum() * 900 / 1e6)

        def metrics(G, fast=False):
            ring, core, fort = G['ring_outer'], G['ring_core'], G['lower_fort']
            m = geo.mask(ring, Z.shape, T); i = np.argmax(np.where(m, Z, -1e9)); cx, cy, cz = X.flat[i], Y.flat[i], Z.flat[i]
            D = np.hypot(X - cx, Y - cy)
            a = np.linspace(0, 2 * np.pi, 72, endpoint=False); rr = np.arange(300, 601, 50); Aa, Rr = np.meshgrid(a, rr)
            relief = cz - np.nanmedian(zat(cx + (Rr * np.sin(Aa)).ravel(), cy + (Rr * np.cos(Aa)).ravel()))
            if fast:     # component runs: viewsheds omitted (they carry no horizontal-error signal for the citadel)
                v5c = v10c = v5l = v10l = np.nan
            else:
                v5c, v10c = viewshed_km2(cx, cy, P['viewshed_max_m']); v5l, v10l = viewshed_km2(fort.centroid.x, fort.centroid.y, P['viewshed_max_m'])
            inter = fort.intersection(fort_osm).area
            return dict(fort_area_ha=fort.area / 1e4, ring_outer_ha=ring.area / 1e4, fort_citadel_m=fort.centroid.distance(core.centroid),
                        citadel_bearing_deg=float((np.degrees(np.arctan2(core.centroid.x - fort.centroid.x, core.centroid.y - fort.centroid.y)) + 360) % 360),
                        iou_fort_osm=inter / fort.union(fort_osm).area, frac_osm_fort_covered=inter / fort_osm.area,
                        fort_centroid_to_osm_m=fort.centroid.distance(fort_osm.centroid),
                        summit_z=float(cz), higher_cells_1000m=int(((D < 1000) & (D > 60) & (Z > cz)).sum()),
                        higher_cells_1500m=int(((D < 1500) & (D > 60) & (Z > cz)).sum()), max_excess_1500m=float(np.max(Z[(D < 1500) & (D > 60)]) - cz),
                        relief_300_600m=float(relief), vis5_citadel_km2=v5c, vis10_citadel_km2=v10c, vis5_lower_km2=v5l, vis10_lower_km2=v10l,
                        shift_lower_fort_m=fort.centroid.distance(F.loc['lower_fort'].geometry.centroid),
                        shift_citadel_m=core.centroid.distance(F.loc['ring_core'].geometry.centroid),
                        # every digitised feature: area (ha) of polygons, length (m) of lines (Table 3)
                        **{(f'area_ha_{i}' if g.geom_type != 'LineString' else f'length_m_{i}'): (g.area / 1e4 if g.geom_type != 'LineString' else g.length)
                           for i, g in G.items()})
        v1 = metrics({i: g for i, g in zip(F.index, F.geometry)}); nominal = metrics(G0)
        # error budget per realisation: bootstrap transform + local error topped up to a target RMSE drawn from
        # the tie-threshold sensitivity range + vertex noise + systematic digitising offset
        targ, thr_info = threshold_targets(C, J, B, rng)
        spread2 = boot_sd ** 2
        reps = []
        for b, M in enumerate(Ms):
            sd_b = np.sqrt(max(targ[b] ** 2 - spread2, 0) / 2)
            sh = {i: rng.normal(0, sd_b, 2) for i in scan}
            reps.append(metrics(geoms(M, sh, C['montecarlo']['vertex_noise_m'], DIG)))
        # contribution breakdown (round-2 review M3): one-at-a-time runs, each switching ON a single component
        # with the others at their nominal value; reported as the 95% interval half-width of each metric.
        # r3: the 95% half-widths are percentile estimates, so with few draws a single component can come out wider
        # than the full budget (round 3: digitising 1.51 ha vs full 1.26 ha at n=100/200; both ~1.37 ha analytically).
        # Not a combination bug: config now uses n=1000 for the full run and for every component run.
        NC = P.get('n_components', 1000)
        def halfw(rs):
            out = {}
            for k in ('fort_area_ha', 'ring_outer_ha', 'fort_citadel_m', 'citadel_bearing_deg', 'iou_fort_osm', 'fort_centroid_to_osm_m',
                      'area_ha_ring_middle', 'area_ha_ring_core', 'area_ha_pond_nw', 'area_ha_pond_e', 'length_m_moat_nw'):
                v = np.array([r.get(k, np.nan) for r in rs], float)
                if np.isfinite(v).any():
                    out[k] = float((np.nanpercentile(v, 97.5) - np.nanpercentile(v, 2.5)) / 2)
            return out
        base_sd = np.sqrt(max(J['block_cv_rmse_m'] ** 2 - spread2, 0) / 2)
        comp = {}
        comp['transform (bootstrap + local error at baseline block-CV)'] = halfw(
            [metrics(geoms(M, {i: rng.normal(0, base_sd, 2) for i in scan}), fast=True) for M in Ms[:NC]])
        comp['tie-threshold (target RMSE across settings, nominal transform)'] = halfw(
            [metrics(geoms(nom, {i: rng.normal(0, np.sqrt(max(targ[b] ** 2 - spread2, 0) / 2), 2) for i in scan}), fast=True) for b in range(NC)])
        comp['digitising offset (sd %g m)' % DIG] = halfw([metrics(geoms(nom, None, 0.0, DIG), fast=True) for _ in range(NC)])
        comp['vertex noise (%g m)' % C['montecarlo']['vertex_noise_m']] = halfw(
            [metrics(geoms(nom, None, C['montecarlo']['vertex_noise_m'], 0.0), fast=True) for _ in range(NC)])
        comp['full budget'] = halfw(reps)
        st.note(f'component breakdown (95 pct half-widths) computed with {NC} realisations each')
        st.note(f"error budget: target RMSE {targ.min():.1f}-{targ.max():.1f} m (tie-threshold sensitivity), digitising sd {DIG} m, vertex noise {C['montecarlo']['vertex_noise_m']} m")
        # model uncertainty: nominal metrics under every transform family fitted to all ties
        by_model = {}
        for k in ('affine', 'poly2', 'tps'):
            by_model[k] = {kk: float(v) for kk, v in metrics(geoms(V.Model(k, J['smoothing'] if k == J['kind'] else (1.0 if k == 'tps' else 0.0)).fit(uv, en))).items()}
        # vertical (DSM) uncertainty for the commanding-ground and relief tests: spatially correlated noise
        # (sd vertical_sd_m.copernicus, correlation length dsm_corr_m) added to GLO-30 in a 4 km window
        cx0, cy0 = nominal_obs = (lambda m: (X.flat[m], Y.flat[m]))(int(np.argmax(np.where(geo.mask(G0['ring_outer'], Z.shape, T), Z, -1e9))))
        win = (np.abs(X - cx0) < 2000) & (np.abs(Y - cy0) < 2000)
        r0, r1 = np.where(win.any(1))[0][[0, -1]]; c0, c1 = np.where(win.any(0))[0][[0, -1]]
        Zw, Xw, Yw = Z[r0:r1 + 1, c0:c1 + 1], X[r0:r1 + 1, c0:c1 + 1], Y[r0:r1 + 1, c0:c1 + 1]
        ringm = geo.mask(G0['ring_outer'], Z.shape, T)[r0:r1 + 1, c0:c1 + 1]
        # canopy mask (Sentinel-2 dry-season NDVI) for a one-sided canopy bias: GLO-30 is a surface model, so
        # over trees it reads above the ground by an unknown amount; each realisation removes U(0, max) m there
        from rasterio.warp import reproject, Resampling
        ndvi = np.zeros(Zw.shape, np.float32)
        with rasterio.open(C.f(C['inputs']['s2_dry_ndvi'])) as r:
            reproject(rasterio.band(r, 1), ndvi, src_transform=r.transform, src_crs=r.crs,
                      dst_transform=T * T.translation(c0, r0), dst_crs=d.crs, resampling=Resampling.average)
        canopy = ndvi > P.get('canopy_ndvi', 0.45)
        L = P['dsm_corr_m'] / 30.0

        def vertical_mc(sig, bias_max, n):
            vz = []
            for _ in range(n):
                e = cv2.GaussianBlur(rng.normal(0, 1, Zw.shape).astype(np.float32), (0, 0), L); e = e / e.std() * sig
                Zn = Zw + e - canopy * rng.uniform(0, bias_max)
                i = np.argmax(np.where(ringm, Zn, -1e9)); zc = Zn.flat[i]
                D = np.hypot(Xw - Xw.flat[i], Yw - Yw.flat[i]); far = (D > 60) & (D < 1500)
                vz.append(dict(higher_1500=int((far & (Zn > zc)).sum()), excess=float(Zn[far].max() - zc),
                               higher_1000=int(((D > 60) & (D < 1000) & (Zn > zc)).sum())))
            return vz
        scen = {}
        for sg in P.get('dsm_sd_scenarios_m', [2.0, 3.0, 5.0]):
            for bm in (0.0, P.get('canopy_bias_max_m', 5.0)):
                v = vertical_mc(sg, bm, P['n_vertical'] // 2)
                scen[f'sd{sg:g}_canopy{bm:g}'] = dict(sd_m=sg, canopy_bias_max_m=bm, n=len(v),
                    frac_no_higher_cell_1500m=float(np.mean([q['higher_1500'] == 0 for q in v])),
                    frac_excess_le_1m_1500m=float(np.mean([q['excess'] <= 1 for q in v])),
                    frac_excess_le_3m_1500m=float(np.mean([q['excess'] <= 3 for q in v])),
                    excess_95=[float(x) for x in np.percentile([q['excess'] for q in v], [2.5, 50, 97.5])])
        st.note('DSM scenarios: ' + '; '.join(f"{k}: none higher {100 * v['frac_no_higher_cell_1500m']:.0f}%, <=3 m {100 * v['frac_excess_le_3m_1500m']:.0f}%" for k, v in scen.items()))
        sig = C['montecarlo']['vertical_sd_m']['copernicus']
        vz = vertical_mc(sig, 0.0, P['n_vertical'])
        vertical = dict(n=len(vz), sd_m=sig, corr_m=P['dsm_corr_m'],
                        frac_no_higher_cell_1500m=float(np.mean([v['higher_1500'] == 0 for v in vz])),
                        frac_no_higher_cell_1000m=float(np.mean([v['higher_1000'] == 0 for v in vz])),
                        frac_excess_le_1m_1500m=float(np.mean([v['excess'] <= 1.0 for v in vz])),
                        frac_excess_le_3m_1500m=float(np.mean([v['excess'] <= 3.0 for v in vz])),
                        excess_95=[float(np.percentile([v['excess'] for v in vz], q)) for q in (2.5, 50, 97.5)])
        keys = list(nominal)
        def ci(k):
            v = np.array([r[k] for r in reps], float); return dict(median=float(np.median(v)), lo95=float(np.percentile(v, 2.5)), hi95=float(np.percentile(v, 97.5)))
        R = {k: dict(v1=v1[k], v2=nominal[k], **ci(k)) for k in keys}
        # qualitative findings: fraction of realisations in which each holds
        frac = lambda f: float(np.mean([f(r) for r in reps]))
        claims = {
            'citadel_SSW_of_lower_fort (bearing 180-235 deg)': frac(lambda r: 180 <= r['citadel_bearing_deg'] <= 235),
            'fort_citadel_distance_450_650m': frac(lambda r: 450 <= r['fort_citadel_m'] <= 650),
            'citadel_summit_highest_within_1km (<= 2 higher cells; horizontal error only, see vertical_commanding_ground)': frac(lambda r: r['higher_cells_1000m'] <= 2),
            'citadel_summit_highest_within_1.5km (no cell > +1 m; horizontal error only)': frac(lambda r: r['max_excess_1500m'] <= 1.0),
            'citadel_relief_gt_20m': frac(lambda r: r['relief_300_600m'] > 20),
            'citadel_sees_more_than_lower_fort_within_5km': frac(lambda r: r['vis5_citadel_km2'] > r['vis5_lower_km2']),
            'lower_fort_overlaps_osm_fort_IoU_gt_0.5': frac(lambda r: r['iou_fort_osm'] > 0.5),
        }
        # ---------------- Old Sangoli (DF224)
        Js, uvs, ens = load_model(C, 'corona_df224_sangolli')
        noms, Mss, locs, boots = ensemble(C, Js, uvs, ens, B)
        Fv1 = np.array(json.load(open(C.code(C['corona']['df224_crops']['sangolli']['params'])))['F'])
        x1, y1 = geo.ll2utm(P['old_sangoli_lonlat'][0], P['old_sangoli_lonlat'][1])
        suv = cv2.invertAffineTransform(Fv1) @ np.array([x1, y1, 1.0])
        sx, sy = noms(suv[None])[0]
        sang_now = osm[(osm.category == 'place') & (osm.name == 'Sangolli')].geometry.iloc[0]
        sp = [Point(*(M(suv[None])[0] + rng.normal(0, locs, 2))) for M in Mss]
        # open water in the dry-season 2026 Sentinel-2 median (MNDWI = (green - swir) / (green + swir) > 0)
        with rasterio.open(C.f(C['inputs']['epochs']['S2026'] + '.tif')) as r:      # bands: blue, green, red, nir, swir
            gS = r.read([2, 5]).astype(float); TS = r.transform
        mndwi = (gS[0] - gS[1]) / (gS[0] + gS[1] + 1e-9)
        def wet(p):
            c, r_ = ~TS * (p.x, p.y)
            return bool(mndwi[int(r_), int(c)] > 0)
        old = dict(v1_utm=[x1, y1], v2_utm=[float(sx), float(sy)], shift_m=float(np.hypot(sx - x1, sy - y1)),
                   v1_inside_reservoir=bool(resv.contains(Point(x1, y1))), v2_inside_reservoir=bool(resv.contains(Point(sx, sy))),
                   v2_dist_to_shore_m=float(resv.exterior.distance(Point(sx, sy))), frac_inside_reservoir=float(np.mean([resv.contains(p) for p in sp])),
                   dist_shore_95=[float(np.percentile([resv.exterior.distance(p) for p in sp], q)) for q in (2.5, 50, 97.5)],
                   dist_to_present_sangolli_km=float(Point(sx, sy).distance(sang_now) / 1000),
                   north_of_present_km=float((sy - sang_now.y) / 1000),
                   v1_open_water_2026=wet(Point(x1, y1)), v2_open_water_2026=wet(Point(sx, sy)), frac_open_water_2026=float(np.mean([wet(p) for p in sp])),
                   frac_within_100m_of_osm_shore=float(np.mean([resv.exterior.distance(p) <= 100 for p in sp])), model=Js['kind'], loo_rmse_m=Js['loo_rmse_m'], local_sd_m=locs)
        out = dict(by_model=by_model, vertical_commanding_ground=vertical, vertical_scenarios=scen,
                   error_budget=dict(target='block-CV RMSE', threshold_sensitivity=thr_info, digitising_sd_m=DIG, vertex_noise_m=C['montecarlo']['vertex_noise_m'], canopy_ndvi=P.get('canopy_ndvi', 0.45), canopy_frac_window=float(canopy.mean()), components_halfwidth_95=comp), n=B, seed=C['seed'], kittur_model=dict(kind=J['kind'], n_ties=len(uv), loo_rmse_m=J['loo_rmse_m'], block_cv_rmse_m=J.get('block_cv_rmse_m'), bootstrap_sd_m=boot_sd, local_sd_m=loc_sd),
                   metrics=R, claims_fraction=claims, old_sangoli=old)
        save_json(out, C.out('results', 'propagation.json'))
        for k in keys:
            st.note(f"{k}: v1 {R[k]['v1']:.2f}, v2 {R[k]['v2']:.2f} (95%: {R[k]['lo95']:.2f}-{R[k]['hi95']:.2f})")
        for k, v in claims.items():
            st.note(f'claim {k}: holds in {100 * v:.0f}% of realisations')
        for k, v in by_model.items():
            st.note(f"model {k}: fort {v['fort_area_ha']:.2f} ha, fort-citadel {v['fort_citadel_m']:.0f} m, IoU OSM {v['iou_fort_osm']:.2f}, shift {v['shift_lower_fort_m']:.0f} m")
        st.note(f"DSM noise ({sig} m, {P['dsm_corr_m']} m corr.): no higher cell within 1.5 km in {100 * vertical['frac_no_higher_cell_1500m']:.0f}%, "
                f"excess <= 1 m in {100 * vertical['frac_excess_le_1m_1500m']:.0f}%, <= 3 m in {100 * vertical['frac_excess_le_3m_1500m']:.0f}% of realisations")
        st.note(f"Old Sangoli: shift {old['shift_m']:.0f} m; inside reservoir v1 {old['v1_inside_reservoir']}, v2 {old['v2_inside_reservoir']}, "
                f"{100 * old['frac_inside_reservoir']:.0f}% of realisations; shore distance {old['v2_dist_to_shore_m']:.0f} m; "
                f"open water in Feb 2026 S2 median: v2 {old['v2_open_water_2026']}, {100 * old['frac_open_water_2026']:.0f}% of realisations")


if __name__ == '__main__':
    main()
