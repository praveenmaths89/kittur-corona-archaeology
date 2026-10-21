"""Desk validation of georeferencing: independent tie points, transform comparison, uncertainty ensembles.

Workflow (used by stages/s12_validation.py):
  1. `osm_candidates` picks stable, spatially spread features from OpenStreetMap (road junctions, road/river
     bridges, tank centroids, places of worship). OSM only proposes WHERE to look; the reference position of
     each point is its position on Sentinel-2 (CORONA) or on the OSM road/water raster (SoI 1924 maps).
  2. `match_chip` finds the same feature on the historical image by normalised cross-correlation of a
     500 m chip, searched +-search_m around the position predicted by the current (initial) transform.
     Points are accepted only with a high, unambiguous correlation peak away from the search edge.
  3. Each accepted point gives a tie (scan/map pixel u,v) <-> (UTM E,N).
  4. `Model` fits scan->UTM transforms (affine, 2nd/3rd-order polynomial, thin-plate spline); `evaluate`
     scores them on a held-out check set, by leave-one-out, by leave-spatial-block-out and by bootstrap,
     and tests residuals for spatial autocorrelation (Moran's I).
Nothing here edits raw data; all outputs go to results/ and derived/.
"""
from __future__ import annotations
import json
import numpy as np
import cv2
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiPoint
from scipy.interpolate import RBFInterpolator

# ----------------------------------------------------------------------------------------------- candidates
PRIORITY = {'junction': 0, 'bridge': 1, 'tank': 2, 'village': 3, 'worship': 4}


def osm_candidates(osm_path, bbox, min_sep=600.0, crs='EPSG:32643'):
    """Stable-feature candidates inside bbox (xmin, ymin, xmax, ymax, UTM m).

    junction: a vertex shared by >= 2 distinct road ways that is not just a continuation (end of one way meeting
              the end of exactly one other); bridge: a road crossing a waterway (OSM bridge=yes ways or
              road x waterway intersections); tank: centroid of a pond/reservoir polygon of 1-40 ha (large
              reservoirs postdate 1968 and have mobile shorelines); worship: temple/mosque/church points.
    Candidates are thinned greedily by PRIORITY so that no two are closer than min_sep metres.
    """
    g = gpd.read_file(osm_path).to_crs(crs)
    xmin, ymin, xmax, ymax = bbox
    g = g.cx[xmin:xmax, ymin:ymax]
    cand = []
    roads = g[g.category == 'road']
    # vertex -> set of ways and whether it is an endpoint
    vert = {}
    for wi, geom in enumerate(roads.geometry):
        cs = list(geom.coords)
        for k, c in enumerate(cs):
            key = (round(c[0], 1), round(c[1], 1))
            d = vert.setdefault(key, [set(), 0])
            d[0].add(wi); d[1] += int(k in (0, len(cs) - 1))
    for (x, y), (ways, nend) in vert.items():
        if len(ways) >= 3 or (len(ways) == 2 and nend < 2):
            cand.append(('junction', x, y, ''))
    wat = g[g.category == 'waterway'].geometry.union_all() if (g.category == 'waterway').any() else None
    for _, r in roads.iterrows():
        t = json.loads(r.tags)
        if wat is not None and r.geometry.intersects(wat):
            ip = r.geometry.intersection(wat)
            pts = [ip] if ip.geom_type == 'Point' else [p for p in getattr(ip, 'geoms', []) if p.geom_type == 'Point']
            for p in pts:
                cand.append(('bridge', p.x, p.y, t.get('name', '')))
    for _, r in g[g.category == 'water'].iterrows():
        if r.geometry.geom_type == 'Polygon' and 1e4 <= r.geometry.area <= 4e5:
            c = r.geometry.centroid; cand.append(('tank', c.x, c.y, r['name'] or ''))
    for _, r in g[(g.category == 'place') & (g.geom_type == 'Point')].iterrows():
        cand.append(('village', r.geometry.x, r.geometry.y, r['name'] or ''))    # settlement nucleus (OSM place node)
    for _, r in g[(g.category == 'worship') & (g.geom_type == 'Point')].iterrows():
        cand.append(('worship', r.geometry.x, r.geometry.y, r['name'] or ''))
    cand = [c for c in cand if xmin <= c[1] <= xmax and ymin <= c[2] <= ymax]
    cand.sort(key=lambda c: PRIORITY[c[0]])
    keep = []
    for c in cand:
        if all(np.hypot(c[1] - k[1], c[2] - k[2]) >= min_sep for k in keep):
            keep.append(c)
    return [dict(id=f'{c[0][:2].upper()}{i:03d}', kind=c[0], E=float(c[1]), N=float(c[2]), name=c[3]) for i, c in enumerate(keep)]


# ----------------------------------------------------------------------------------------------- matching
def norm8(a, valid=None):
    """Percentile-stretch to 8 bit, CLAHE, light blur: removes radiometric differences between epochs."""
    a = a.astype(np.float32); v = a[(valid if valid is not None else np.isfinite(a)) & np.isfinite(a)]
    if v.size < 10 or v.std() == 0:
        return np.zeros(a.shape, np.float32)
    lo, hi = np.percentile(v, [1, 99])
    b = np.clip((np.nan_to_num(a, nan=lo) - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    b = cv2.createCLAHE(2.0, (4, 4)).apply(b)
    return cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.0)


def match_chip(target, ref, half_px, search_px, valid_t=None, excl_px=10):
    """Locate the centre chip of `target` (2*half_px square) in `ref` (same grid, wider by search_px).

    Returns (dx_px, dy_px, peak, ratio): offset of the feature in `ref` relative to its position in `target`
    (x right, y down), the NCC peak, the ratio of the best peak outside excl_px to the main peak, and the
    peak z-score.
    """
    c = target.shape[0] // 2
    t = target[c - half_px:c + half_px, c - half_px:c + half_px]
    if t.std() < 4 or (valid_t is not None and (~valid_t[c - half_px:c + half_px, c - half_px:c + half_px]).mean() > 0.02):
        return None
    s = ref[c - half_px - search_px:c + half_px + search_px, c - half_px - search_px:c + half_px + search_px]
    r = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    if not (1 <= loc[0] <= 2 * search_px - 1 and 1 <= loc[1] <= 2 * search_px - 1):
        return None                           # peak on the search border: not trustworthy
    # sub-pixel refinement by a parabola through the peak
    def sub(a, b, cc):
        d = a - 2 * cc + b
        return 0.0 if d == 0 else 0.5 * (a - b) / d
    sx = sub(r[loc[1], loc[0] - 1], r[loc[1], loc[0] + 1], mx); sy = sub(r[loc[1] - 1, loc[0]], r[loc[1] + 1, loc[0]], mx)
    rr = r.copy(); cv2.circle(rr, loc, excl_px, -1, -1)
    second = rr.max()
    z = (mx - r.mean()) / (r.std() + 1e-9)          # peak height in standard deviations of the NCC surface
    return (loc[0] + sx - search_px, loc[1] + sy - search_px, float(mx), float(second / mx if mx > 0 else 1), float(z))


# ----------------------------------------------------------------------------------------------- models
class Model:
    """scan/map pixel (u, v) -> UTM (E, N). kind: affine | poly2 | poly3 | tps (thin-plate spline, degree-1 tail)."""
    NPAR = {'affine': 3, 'poly2': 6, 'poly3': 10, 'tps': 3}

    def __init__(self, kind, smoothing=0.0):
        self.kind, self.s = kind, smoothing

    def _X(self, uv):
        z = (uv - self.mu) / self.sd; x, y = z[:, 0], z[:, 1]
        cols = [np.ones_like(x), x, y]
        if self.kind in ('poly2', 'poly3'):
            cols += [x * x, x * y, y * y]
        if self.kind == 'poly3':
            cols += [x ** 3, x * x * y, x * y * y, y ** 3]
        return np.column_stack(cols)

    def fit(self, uv, en):
        uv, en = np.asarray(uv, float), np.asarray(en, float)
        self.mu, self.sd = uv.mean(0), uv.std(0) + 1e-9
        if self.kind == 'tps':
            self.f = RBFInterpolator((uv - self.mu) / self.sd, en, kernel='thin_plate_spline', smoothing=self.s, degree=1)
        else:
            self.b, *_ = np.linalg.lstsq(self._X(uv), en, rcond=None)
        return self

    def __call__(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        return self.f((uv - self.mu) / self.sd) if self.kind == 'tps' else self._X(uv) @ self.b


def rms(r):
    r = np.asarray(r); return float(np.sqrt(np.mean(np.sum(r ** 2, axis=1)))) if len(r) else float('nan')


def morans_i(xy, z, nperm=999, rng=None):
    """Moran's I of scalar z with inverse-distance weights; permutation p-value (two-sided)."""
    rng = rng or np.random.default_rng(0)
    d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1)); W = np.where(d > 0, 1 / np.maximum(d, 1), 0)
    def I(v):
        v = v - v.mean(); return len(v) / W.sum() * (v @ W @ v) / (v @ v)
    i0 = I(z); perm = np.array([I(rng.permutation(z)) for _ in range(nperm)])
    return float(i0), float((np.sum(np.abs(perm - perm.mean()) >= abs(i0 - perm.mean())) + 1) / (nperm + 1))


def spatial_blocks(xy, k, seed):
    """k spatial blocks by k-means on coordinates (used for leave-block-out cross-validation)."""
    from sklearn.cluster import KMeans
    return KMeans(k, n_init=10, random_state=seed).fit_predict(xy)


def evaluate(uv, en, kinds, ctrl, seed, nboot=500, k_blocks=5, tps_smoothing=(1.0, 10.0, 100.0, 1000.0)):
    """Score each transform kind.

    ctrl: boolean mask of control points (the rest are held-out check points, never used in fitting).
    Returns dict kind -> metrics and per-point residuals (check, LOO). For the TPS the smoothing is chosen by
    leave-one-out on the control points only. Zero smoothing is deliberately NOT a candidate: with noisy ties an
    unsmoothed TPS interpolates every control point exactly (fit RMSE ~ 0), which is overfitting, not accuracy.
    """
    rng = np.random.default_rng(seed); out = {}
    chk = ~ctrl; blocks = spatial_blocks(en, k_blocks, seed)
    for kind in kinds:
        s = 0.0
        if kind == 'tps':      # choose smoothing on control points only
            sc = {}
            for sm in tps_smoothing:
                r = [en[ctrl][i] - Model('tps', sm).fit(np.delete(uv[ctrl], i, 0), np.delete(en[ctrl], i, 0))(uv[ctrl][i:i + 1])[0] for i in range(ctrl.sum())]
                sc[sm] = rms(r)
            s = min(sc, key=sc.get)
        need = Model.NPAR[kind] + 2
        if ctrl.sum() < need:
            continue
        M = Model(kind, s).fit(uv[ctrl], en[ctrl])
        fit_res = en[ctrl] - M(uv[ctrl]); chk_res = en[chk] - M(uv[chk])
        loo = np.array([en[i] - Model(kind, s).fit(np.delete(uv, i, 0), np.delete(en, i, 0))(uv[i:i + 1])[0] for i in range(len(uv))])
        blk = np.zeros_like(en)
        for b in np.unique(blocks):
            m = blocks == b
            if (~m).sum() < need:            # too few points left outside the block for this model
                blk[m] = np.nan; continue
            blk[m] = en[m] - Model(kind, s).fit(uv[~m], en[~m])(uv[m])
        boot = []
        ci = np.where(ctrl)[0]
        for _ in range(nboot):
            j = rng.choice(ci, len(ci), replace=True)
            if kind == 'tps':
                j = np.unique(j)
            if len(np.unique(j)) < need:
                continue
            try:
                boot.append(rms(en[chk] - Model(kind, s).fit(uv[j], en[j])(uv[chk])))
            except Exception:
                pass
        mi_e = morans_i(en, loo[:, 0], rng=rng); mi_n = morans_i(en, loo[:, 1], rng=rng)
        out[kind] = dict(smoothing=s, n_control=int(ctrl.sum()), n_check=int(chk.sum()), fit_rmse_m=rms(fit_res),
                         check_rmse_m=rms(chk_res), check_rmse_boot95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))] if boot else None,
                         check_max_m=float(np.max(np.hypot(*chk_res.T))) if chk.any() else None,
                         loo_rmse_m=rms(loo), loo_p90_m=float(np.percentile(np.hypot(*loo.T), 90)),
                         block_cv_rmse_m=rms(blk), moran_I_E=mi_e, moran_I_N=mi_n,
                         _check_res=chk_res.tolist(), _loo=loo.tolist())
    return out


def bootstrap_models(uv, en, kind, s, nrep, seed):
    """nrep transforms fitted to bootstrap resamples of ALL tie points (for propagation)."""
    rng = np.random.default_rng(seed); Ms = []
    while len(Ms) < nrep:
        j = rng.choice(len(uv), len(uv), replace=True)
        if kind == 'tps':
            j = np.unique(j)              # duplicated points make the interpolation matrix singular
        if len(j) < Model.NPAR[kind] + 3:
            continue
        Ms.append(Model(kind, s).fit(uv[j], en[j]))
    return Ms
