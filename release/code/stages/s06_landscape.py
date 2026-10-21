"""Stage 06 - siege-landscape GIS: viewsheds, commanding-ground test, least-cost approaches, candidate zones.

Viewshed: radial line-of-sight on Copernicus GLO-30 (a surface model; trees and buildings included), observer
eye height 10 m, earth curvature with refraction coefficient k = 0.13, 2880 rays, 10 m steps, 25 km limit.
Observers: highest DEM cell inside the citadel mound's outer ring; centroid of the lower-fort enclosure.
Least-cost paths: cost = 1 + (slope / 4 deg)^2; x2 on dark 1968 tone (lowest quartile; trees, wet ground);
50 inside ponds; 25 within 15 m of the N/W moat; 8-connected Dijkstra (skimage.graph.route_through_array).
Targets the point 25 m outside the midpoint of the east face (assumed East Gate). Starts on the Belgaum (NW) and
Dharwad (SE) bearings, clipped to the DEM edge.
Candidate siege zones (illustrative geometry derived from Trewman's letter of 8 Dec 1824; none is located by evidence).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import rasterio
import cv2
import geopandas as gpd
from scipy.ndimage import map_coordinates
from skimage.graph import route_through_array
from shapely.geometry import Point, LineString, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, features


def main(argv=None):
    C = load()
    V, Lc = C['viewshed'], C['lcp']
    with Stage(C, 'landscape') as st:
        d = rasterio.open(C.f(C['inputs']['dem'])); Z = d.read(1).astype(float); T = d.transform
        F = features.build(C)
        fort, ring = F.loc['lower_fort'].geometry, F.loc['ring_outer'].geometry
        rc = lambda x, y: ((~T * (x, y))[1] - 0.5, (~T * (x, y))[0] - 0.5)
        zat = lambda x, y: float(map_coordinates(Z, [[rc(x, y)[0]], [rc(x, y)[1]]], order=1)[0])
        cols, rows = np.meshgrid(np.arange(Z.shape[1]), np.arange(Z.shape[0]))
        X, Y = T * (cols + 0.5, rows + 0.5)
        mring = geo.mask(ring, Z.shape, T)
        i = np.argmax(np.where(mring, Z, -1e9)); cit = (Z.flat[i], X.flat[i], Y.flat[i])
        lowc = fort.centroid

        def viewshed(x0, y0):
            z0 = zat(x0, y0) + V['eye_height_m']; vis = np.zeros(Z.shape, bool)
            ds = np.arange(V['step_m'], V['max_dist_m'], V['step_m']); k = V['refraction_k']; Re = 6371000
            for a in np.linspace(0, 2 * np.pi, V['n_rays'], endpoint=False):
                xs, ys = x0 + ds * np.sin(a), y0 + ds * np.cos(a)
                c_, r_ = ~T * (xs, ys); r_, c_ = r_ - 0.5, c_ - 0.5
                ok = (r_ >= 0) & (c_ >= 0) & (r_ < Z.shape[0] - 1) & (c_ < Z.shape[1] - 1)
                r_, c_, dd = r_[ok], c_[ok], ds[ok]
                zz = map_coordinates(Z, [r_, c_], order=1) - dd ** 2 * (1 - k) / (2 * Re)
                ang = (zz - z0) / dd; mx = np.maximum.accumulate(np.r_[-1e9, ang[:-1]])
                v = ang >= mx
                vis[np.round(r_).astype(int)[v], np.round(c_).astype(int)[v]] = True
            return vis, z0
        res, vis = {}, {}
        for nm, (x, y) in {'citadel': (cit[1], cit[2]), 'lower_fort': (lowc.x, lowc.y)}.items():
            v, z0 = viewshed(x, y); vis[nm] = v
            D = np.hypot(X - x, Y - y); zg = zat(x, y)
            r = dict(obs_x=x, obs_y=y, ground_z=zg, eye_z=z0, visible_km2_25km=v.sum() * 900 / 1e6,
                     visible_km2_5km=(v & (D < 5000)).sum() * 900 / 1e6, frac_5km=float((v & (D < 5000)).sum() / (D < 5000).sum()),
                     frac_10km=float((v & (D < 10000)).sum() / (D < 10000).sum()), max_vis_dist_km=float(D[v].max() / 1000))
            for rr in (1000, 1500):
                m = (D < rr) & (D > 60)
                r[f'higher_cells_within_{rr}m'] = int((m & (Z > zg)).sum()); r[f'max_z_within_{rr}m'] = float(Z[m].max())
            res[nm] = r
            geo.write_tif(C.out('derived', 'landscape', f'viewshed_{nm}.tif'), v.astype('uint8'), T, nodata=255)
            st.note(f'viewshed {nm}: z {zg:.1f} m, {r["visible_km2_5km"]:.1f} km2 within 5 km ({100 * r["frac_5km"]:.0f}%), {r["visible_km2_25km"]:.0f} km2 within 25 km')
        Dc = np.hypot(X - cit[1], Y - cit[2])
        ann = []
        for a, b in [(0, 250), (250, 500), (500, 1000), (1000, 1500), (1500, 2000), (2000, 3000), (3000, 5000)]:
            m = (Dc >= a) & (Dc < b); j = np.argmax(np.where(m, Z, -1e9))
            ann.append(dict(r0=a, r1=b, max_z=float(Z.flat[j]), x=float(X.flat[j]), y=float(Y.flat[j]), dist_m=float(Dc.flat[j])))
        st.note('max z by annulus: ' + '; '.join(f"{a['r0']}-{a['r1']} m: {a['max_z']:.1f} m" for a in ann))
        # least-cost paths
        sl = np.degrees(np.arctan(np.hypot(*np.gradient(Z, 30))))
        cost = 1 + (sl / Lc['slope_ref_deg']) ** 2
        c68 = rasterio.open(C.p('derived') / 'corona' / 'corona_1968_kittur.tif'); A = cv2.GaussianBlur(c68.read(1).astype(float), (0, 0), 5)
        cc, rr = ~c68.transform * (X, Y); inside = (cc >= 0) & (rr >= 0) & (cc < A.shape[1]) & (rr < A.shape[0])
        tone = np.full(Z.shape, np.nan); tone[inside] = A[rr[inside].astype(int), cc[inside].astype(int)]
        dark = inside & (tone < np.nanpercentile(tone, 25)); cost[dark] *= Lc['dark_tone_factor']
        for pid in ('pond_nw', 'pond_e'):
            cost[geo.mask(F.loc[pid].geometry, Z.shape, T)] = Lc['pond_cost']
        cost[geo.mask(F.loc['moat_nw'].geometry.buffer(Lc['moat_buffer_m']), Z.shape, T)] = Lc['moat_cost']
        ex = fort.bounds[2]; gate = (ex + Lc['gate_offset_m'], lowc.y)
        cell = lambda x, y: (int((~T * (x, y))[1]), int((~T * (x, y))[0]))
        paths, lines = {}, {}
        for nm, (lon, lat) in Lc['starts'].items():
            x, y = geo.ll2utm(lon, lat); vx, vy = x - gate[0], y - gate[1]; t = 1.0
            while True:
                px, py = gate[0] + vx * t, gate[1] + vy * t; r_, c_ = cell(px, py)
                if 30 < r_ < Z.shape[0] - 30 and 30 < c_ < Z.shape[1] - 30:
                    break
                t -= 0.01
            pth, cst = route_through_array(cost, cell(px, py), cell(*gate), fully_connected=True, geometric=True)
            pts = [T * (c_ + 0.5, r_ + 0.5) for r_, c_ in pth]; ls = LineString(pts)
            last = [p for p in pts if np.hypot(p[0] - gate[0], p[1] - gate[1]) < 1500][0]
            brg = (np.degrees(np.arctan2(last[0] - gate[0], last[1] - gate[1])) + 360) % 360
            v2 = [vis['citadel'][r_, c_] for (r_, c_), p in zip(pth, pts) if np.hypot(p[0] - gate[0], p[1] - gate[1]) < 2000]
            paths[nm] = dict(start=(px, py), length_km=ls.length / 1000, straight_km=float(np.hypot(px - gate[0], py - gate[1]) / 1000), cost=float(cst),
                             arrival_bearing_deg=float(brg), frac_visible_from_citadel=float(np.mean([vis['citadel'][r_, c_] for r_, c_ in pth])),
                             frac_visible_last2km=float(np.mean(v2)))
            lines[nm] = ls
            st.note(f'LCP {nm}: {ls.length / 1000:.1f} km (straight {paths[nm]["straight_km"]:.1f}), arrives from {brg:.0f} deg, {100 * np.mean(v2):.0f}% of last 2 km visible from citadel')
        east = LineString([(ex, lowc.y - 120), (ex, lowc.y + 120)])
        zones = {'Battery close to gate (12 m)': east.buffer(12).difference(fort),
                 'Crest of glacis (30-100 m)': fort.buffer(100).difference(fort.buffer(30)).intersection(box(ex - 10, lowc.y - 200, ex + 200, lowc.y + 200)),
                 'Advanced post (150 m of gate)': Point(gate).buffer(150).difference(fort.buffer(12)),
                 'Escalade gap lower/upper fort': fort.buffer(170).intersection(ring.buffer(170)).difference(fort).difference(ring)}
        Df = np.hypot(X - lowc.x, Y - lowc.y)
        camp = (Df > 1200) & (Df < 3000) & (sl < 3) & ~vis['citadel'] & ~vis['lower_fort']
        geo.write_tif(C.out('derived', 'landscape', 'candidate_camp_deadground.tif'), camp.astype('uint8'), T, nodata=255)
        g = gpd.GeoDataFrame(dict(name=list(zones) + list(lines), kind=['siege_zone'] * len(zones) + ['least_cost_path'] * len(lines),
                                  area_ha=[z.area / 1e4 for z in zones.values()] + [np.nan] * len(lines)),
                             geometry=list(zones.values()) + list(lines.values()), crs=C['crs'])
        g.to_file(C.out('derived', 'vectors', 'landscape.gpkg'), layer='zones_paths', driver='GPKG')
        gpd.GeoDataFrame(dict(name=['citadel observer', 'lower-fort observer', 'assumed East Gate']),
                         geometry=[Point(cit[1], cit[2]), Point(lowc.x, lowc.y), Point(*gate)], crs=C['crs']).to_file(C.out('derived', 'vectors', 'landscape.gpkg'), layer='points', driver='GPKG')
        out = dict(citadel=res['citadel'], lower_fort=res['lower_fort'], annulus_maxz=ann, gate=gate, paths=paths,
                   zones_ha={k: z.area / 1e4 for k, z in zones.items()}, camp_km2=float(camp.sum() * 900 / 1e6))
        st.note(f"zones (ha): {', '.join(f'{k} {v:.2f}' for k, v in out['zones_ha'].items())}; dead-ground camp cells {out['camp_km2']:.1f} km2")
        save_json(out, C.out('results', 'landscape.json'))


if __name__ == '__main__':
    main()
