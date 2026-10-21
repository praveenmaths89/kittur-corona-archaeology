"""Stage 07 - Monte Carlo propagation of georeferencing, digitising and DEM error (N = 1000, seed 1824).

Per realisation, each digitised 1968 feature is perturbed by:
  * a common translation (25 m RMS, i.e. 25/sqrt(2) per axis) about the lower-fort centroid;
  * a random linear (affine) term whose magnitude reaches 50-100 m RMS at 2.5 km from the fort (crop edge);
  * an independent local residual per feature (10 m per axis);
  * vertex digitising noise (4 m per axis).
Heights: citadel relief = maximum within 30 m of the ring core minus the median on 300-600 m circles;
lower-fort relief = median of 200 random points (sd 80 m) about the centroid minus the median on a 450 m circle;
vertical noise 2 m (Copernicus GLO-30) or 10 m (1967 stereo DEM) on the citadel and half that on the lower fort.
Outputs: results/montecarlo.json (median and 2.5-97.5 percentiles), results/montecarlo_samples.npz.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import rasterio
from shapely.affinity import affine_transform
from shapely.geometry import Polygon, LineString
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import features

NAMES = {'lower_fort': 'Lower-fort enclosure', 'moat_nw': 'N/W moat line', 'outer_east': 'East outer line', 'pond_nw': 'NW pond',
         'pond_e': 'E pond', 'ring_outer': 'Citadel outer ring', 'ring_middle': 'Citadel middle ring', 'ring_core': 'Citadel core'}


def main(argv=None):
    C = load(); M = C['montecarlo']
    with Stage(C, 'montecarlo') as st:
        rng = np.random.default_rng(C['seed']); N = M['n']
        F = features.build(C); ids = list(F.index); feats = list(F.geometry)
        x0, y0 = feats[0].centroid.x, feats[0].centroid.y
        dems = {'Copernicus GLO-30': C.f(C['inputs']['dem']), 'CORONA 1967 stereo': C.p('derived') / 'dem' / 'corona1967_dem_kittur_smooth16m.tif'}
        DZ = {}
        for k, p in dems.items():
            with rasterio.open(p) as r:
                z = r.read(1).astype(float); z[(z == -9999)] = np.nan; DZ[k] = (z, r.transform)

        def zs(k, xs, ys):
            Z, T = DZ[k]; c, r = ~T * (np.asarray(xs), np.asarray(ys))
            return map_coordinates(Z, [r - 0.5, c - 0.5], order=1, cval=np.nan)

        def relief(k, core, cx, cy):
            b = core.bounds; xs, ys = np.meshgrid(np.arange(b[0], b[2], 5), np.arange(b[1], b[3], 5))
            top = np.nanmax(zs(k, xs.ravel(), ys.ravel()))
            a = np.linspace(0, 2 * np.pi, 72, endpoint=False); rr = np.arange(300, 601, 50)
            Aa, Rr = np.meshgrid(a, rr)
            return top - np.nanmedian(zs(k, cx + Rr * np.sin(Aa), cy + Rr * np.cos(Aa)))
        res = {i: [] for i in ids}; dist = []; hts = {k: {'citadel': [], 'lower': []} for k in DZ}
        lo_e, hi_e = M['edge_rms_range_m']
        for _ in range(N):
            edge = rng.uniform(lo_e, hi_e); se = np.sqrt(max(edge ** 2 - M['translation_rms_m'] ** 2, 0) / (2 * M['edge_dist_m'] ** 2))
            E = rng.normal(0, se, (2, 2)); t = rng.normal(0, M['translation_rms_m'] / np.sqrt(2), 2)

            def g(geom, loc):
                a, b, c, d = 1 + E[0, 0], E[0, 1], E[1, 0], 1 + E[1, 1]
                G = affine_transform(geom, [a, b, c, d, x0 - (a * x0 + b * y0) + t[0] + loc[0], y0 - (c * x0 + d * y0) + t[1] + loc[1]])
                if G.geom_type == 'Polygon':
                    co = np.array(G.exterior.coords); co[:-1] += rng.normal(0, M['vertex_noise_m'], (len(co) - 1, 2)); co[-1] = co[0]
                    return Polygon(co).buffer(0)
                return LineString(np.array(G.coords) + rng.normal(0, M['vertex_noise_m'], (len(G.coords), 2)))
            locs = [rng.normal(0, M['local_residual_m'], 2) for _ in feats]
            gs = [g(f, l) for f, l in zip(feats, locs)]
            for i, G in zip(ids, gs):
                res[i].append(G.area / 1e4 if G.geom_type in ('Polygon', 'MultiPolygon') else G.length)
            dist.append(gs[0].centroid.distance(gs[7].centroid))
            for k in DZ:
                sv = M['vertical_sd_m']['copernicus'] if k.startswith('Cop') else M['vertical_sd_m']['stereo']
                hts[k]['citadel'].append(relief(k, gs[7].buffer(30), gs[7].centroid.x, gs[7].centroid.y) + rng.normal(0, sv))
                c = gs[0].centroid
                inner = np.nanmedian(zs(k, c.x + rng.normal(0, 80, 200), c.y + rng.normal(0, 80, 200)))
                a = np.linspace(0, 2 * np.pi, 72, endpoint=False)
                hts[k]['lower'].append(inner - np.nanmedian(zs(k, c.x + 450 * np.sin(a), c.y + 450 * np.cos(a))) + rng.normal(0, sv / 2))

        def ci(v):
            v = np.array(v, float); v = v[np.isfinite(v)]
            return dict(median=float(np.median(v)), lo95=float(np.percentile(v, 2.5)), hi95=float(np.percentile(v, 97.5)), n=int(v.size))
        out = dict(N=N, seed=C['seed'], model=M,
                   nominal={i: (float(F.loc[i, 'area_ha']) if F.loc[i, 'kind'] != 'line' else float(F.loc[i, 'length_m'])) for i in ids},
                   areas_ha_or_length_m={i: dict(label=NAMES[i], unit='m' if F.loc[i, 'kind'] == 'line' else 'ha', **ci(v)) for i, v in res.items()},
                   fort_citadel_distance_m=ci(dist), heights_m={k: {kk: ci(vv) for kk, vv in v.items()} for k, v in hts.items()})
        save_json(out, C.out('results', 'montecarlo.json'))
        np.savez_compressed(C.out('results', 'montecarlo_samples.npz'), **{i: np.array(v) for i, v in res.items()}, distance=np.array(dist),
                            **{f'h_{k[:3]}_{kk}': np.array(vv) for k, v in hts.items() for kk, vv in v.items()})
        for i, v in out['areas_ha_or_length_m'].items():
            st.note(f"{v['label']}: {v['median']:.2f} {v['unit']} (95%: {v['lo95']:.2f}-{v['hi95']:.2f})")
        st.note(f"fort-citadel distance {out['fort_citadel_distance_m']['median']:.0f} m (95%: {out['fort_citadel_distance_m']['lo95']:.0f}-{out['fort_citadel_distance_m']['hi95']:.0f})")
        for k, v in out['heights_m'].items():
            for kk, s in v.items():
                st.note(f"height {kk} ({k}): {s['median']:.1f} m (95%: {s['lo95']:.1f}-{s['hi95']:.1f})")


if __name__ == '__main__':
    main()
