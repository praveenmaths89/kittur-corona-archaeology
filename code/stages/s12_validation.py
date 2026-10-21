"""Stage 12 - desk validation of the georeferencing (independent tie points, transform comparison).

For each historical source listed under `validation.targets` in config.yaml:
  1. Candidate stable features are taken from OSM inside the target's box (kittur.validate.osm_candidates).
  2. Around each candidate, the historical image is resampled to a 4 m (CORONA) or 5 m (SoI) UTM chip through
     the CURRENT transform, and a road-network chip is matched to it:
       * reference: OSM roads rasterised and blurred (trunk ... tertiary);
       * CORONA: bright thin linear features (white top-hat of the CLAHE-normalised scan);
       * SoI 1924: red road/settlement ink (colour threshold).
     Two template sizes (700 m and 1000 m) must agree within `agree_m`, and the correlation peak must stand
     `min_z` standard deviations above the NCC surface.
  3. Coarse-to-fine: pass 1 searches +-search1_m around the recorded transform; a RANSAC affine on the pass-1
     ties updates the prediction; pass 2 searches +-search2_m and gives the final ties.
  4. Ties are split into control (70 %) and held-out check points (30 %), stratified by spatial block
     (seed from config). The model used downstream is the one with the lowest leave-block-out RMSE. Affine, 2nd- and 3rd-order polynomials and a thin-plate spline are fitted on the control
     points only and scored on the check points; leave-one-out, leave-spatial-block-out and bootstrap errors and
     Moran's I of the residuals are also reported.
  5. 'Before' = error of the RECORDED transform (the one used in stages 03-07) at all tie points.
  6. The same matching applied to Sentinel-2 (17 Feb 2026, its own geolocation) against OSM estimates how far
     the OSM reference itself is from the satellite frame.
Outputs (all small): results/validation/<target>_ties.csv (per-point residuals for every model),
results/validation.json (summary), params/validation_models/<target>.json (chosen model, all ties) and, for
the Kittur targets, re-georeferenced crops derived/corona/corona_1968_kittur_v2.tif and
derived/soi/SoI_48_I_14_1924_kittur_v2.tif (compressed, clipped to 5 x 5 km / 10 x 10 km).
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import cv2
import pandas as pd
import rasterio
import geopandas as gpd
from rasterio.windows import from_bounds
from rasterio.features import rasterize
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, corona, validate as V

# Model-selection rule, fixed before the v3 run and applied identically to every source.
SELECTION_RULE = ('Candidates in order of complexity: affine, poly2, poly3, regularised TPS. Score = leave-spatial-block-out '
                  'RMSE. Choose the simplest model whose score is within 10% of the lowest. Headline accuracy = that block-CV '
                  'RMSE; LOO and check-point RMSE are reported as secondary figures.')
TOPHAT = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))


# ------------------------------------------------------------------------------------------ source adapters
class Source:
    """A historical image plus its current transform.

    img: 2-D float32 array (a clipped sub-image of the scan/sheet); off: (col, row) offset of img in the full
    source; T: 2x3 affine UTM -> full-source pixel (updated during coarse-to-fine); T_rec: the recorded one.
    """

    def to_pix(self, E, N, T=None):
        T = self.T if T is None else T
        return T[0, 0] * E + T[0, 1] * N + T[0, 2], T[1, 0] * E + T[1, 1] * N + T[1, 2]

    def chip(self, E, N, n, res):
        """n x n chip centred on (E, N) at res metres, sampled through the current transform."""
        jj, ii = np.meshgrid(np.arange(n) - n // 2, np.arange(n) - n // 2)
        u, v = self.to_pix(E + jj * res, N - ii * res)
        a = cv2.remap(self.img, (u - self.off[0]).astype(np.float32), (v - self.off[1]).astype(np.float32),
                      cv2.INTER_LINEAR, borderValue=0)
        return a


def corona_source(C, entity, piece, T_rec, bbox, path=None):
    """CORONA scan piece clipped to the scan footprint of bbox; feature image = road-like bright lines."""
    S = Source(); S.T = S.T_rec = np.array(T_rec, float)
    path = path or corona.scan_path(C, entity, piece)
    from PIL import Image
    W, H = Image.open(path).size
    xs, ys = np.array([bbox[0], bbox[2], bbox[0], bbox[2]]), np.array([bbox[1], bbox[1], bbox[3], bbox[3]])
    u, v = S.to_pix(xs, ys); m = 600
    c0, r0 = max(int(u.min()) - m, 0), max(int(v.min()) - m, 0); c1, r1 = min(int(u.max()) + m, W), min(int(v.max()) + m, H)
    raw = corona.crop(path, (c0, r0, c1, r1)).astype(np.float32)
    S.img = cv2.GaussianBlur(raw, (0, 0), 0.8); S.off = (c0, r0); S.kind = 'corona'
    return S


def soi_source(C, sheet_tif):
    """Corner-georeferenced SoI sheet (EPSG:4326 GeoTIFF). Pixel grid = that GeoTIFF; feature image = red ink.
    The recorded transform is linearised to a UTM -> pixel affine by least squares on a 20 x 20 grid."""
    S = Source(); S.kind = 'soi'
    with rasterio.open(sheet_tif) as r:
        R, G, B = r.read().astype(np.int16); T = r.transform; h, w = r.shape
    S.img = (((R - G) > 50) & ((R - B) > 40)).astype(np.float32) * 255; S.off = (0, 0)
    cc, rr = np.meshgrid(np.linspace(0, w, 20), np.linspace(0, h, 20))
    lo, la = T * (cc.ravel(), rr.ravel()); E, N = geo.ll2utm(lo, la)
    X = np.c_[E, N, np.ones_like(E)]
    bu, *_ = np.linalg.lstsq(X, cc.ravel(), rcond=None); bv, *_ = np.linalg.lstsq(X, rr.ravel(), rcond=None)
    S.T = S.T_rec = np.vstack([bu, bv]); S.path = sheet_tif
    return S


def feature_image(S, a):
    """Road-like structure image for matching (0-255 float)."""
    if S.kind == 'corona':
        b = V.norm8(a, a > 0)
        return cv2.GaussianBlur(cv2.morphologyEx(b, cv2.MORPH_TOPHAT, TOPHAT), (0, 0), 2)
    return cv2.GaussianBlur(a, (0, 0), 1.5)


# ------------------------------------------------------------------------------------------ tie collection
def s2_chip(C, E, N, n, res, path=None, _cache={}):
    """Sentinel-2 17 Feb 2026 (mean of RGB) resampled to an n x n chip at res metres centred on (E, N)."""
    from rasterio.warp import reproject, Resampling
    key = path or C['inputs']['s2_dry']
    if key not in _cache:
        _cache[key] = rasterio.open(C.f(key))
    s = _cache[key]; tr = from_origin(E - (n // 2 + .5) * res, N + (n // 2 + .5) * res, res, res)
    out = np.zeros((3, n, n), np.float32)
    for b in range(3):
        reproject(rasterio.band(s, b + 1), out[b], dst_transform=tr, dst_crs=s.crs, resampling=Resampling.bilinear)
    return out.mean(0)


def match_one(ref, tgt, hs, P, res, Sx):
    """Two-size template match of ref (template) in tgt; returns (dx_m, dy_m, ncc, z, agree_m) or None."""
    ms = [V.match_chip(ref, tgt, h, Sx) for h in hs]
    if not all(ms):
        return None
    agree = float(np.hypot(ms[0][0] - ms[1][0], ms[0][1] - ms[1][1]) * res)
    m = ms[-1]
    if m[4] < P['min_z'] or agree > P['agree_m'] or m[2] < P['min_ncc']:
        return None
    return m[0] * res, m[1] * res, m[2], m[4], agree


def collect(C, S, cands, roads, P, search_m, cues=('road',)):
    """Match every candidate; returns ties with pixel (u, v) of the feature and reference (E, N).

    cues: 'road' = OSM road raster vs road-like structure of the historical image; 's2' = Sentinel-2 image vs
    CLAHE-normalised CORONA (image-to-image). When both cues match they must agree within 2*agree_m (then
    averaged); otherwise the point is dropped as ambiguous.
    """
    res = P['res_m']; Sx = int(search_m / res); hs = [int(h / res) for h in P['half_m']]
    n = 2 * (max(hs) + Sx) + 1; out = []
    for cd in cands:
        E, N = cd['E'], cd['N']
        a = S.chip(E, N, n, res)
        if S.kind == 'corona' and (a == 0).mean() > 0.02:
            continue                                    # outside the scan
        got = {}
        if 'road' in cues:
            tr = from_origin(E - (n // 2 + .5) * res, N + (n // 2 + .5) * res, res, res)
            ref = rasterize([(g, 1) for g in roads], out_shape=(n, n), transform=tr, all_touched=True).astype(np.float32)
            ref = cv2.GaussianBlur(ref, (0, 0), 2) * 600
            tgt = feature_image(S, a)
            if ref.std() >= 1 and tgt.std() >= 1:
                m = match_one(ref, tgt, hs, P, res, Sx)
                if m:
                    got['road'] = m
        if 's2' in cues:
            ref = V.norm8(s2_chip(C, E, N, n, res, P.get('_s2'))); tgt = V.norm8(a, a > 0)
            m = match_one(ref, tgt, hs, P, res, Sx)
            if m:
                got['s2'] = m
        if not got:
            continue
        cue_diff = None
        if len(got) == 2:
            (a1, b1), (a2, b2) = [(g[0], g[1]) for g in got.values()]
            cue_diff = float(np.hypot(a1 - a2, b1 - b2))   # OSM-road position vs Sentinel-2 image position
            if cue_diff > 2 * P['agree_m']:
                continue
        dx = float(np.mean([g[0] for g in got.values()])); dy = float(np.mean([g[1] for g in got.values()]))
        u, v = S.to_pix(E + dx, N - dy)                 # where the feature sits in the source
        out.append(dict(cd, u=float(u), v=float(v), cue='+'.join(got), ncc=round(max(g[2] for g in got.values()), 3),
                        z=round(max(g[3] for g in got.values()), 2), agree_m=round(min(g[4] for g in got.values()), 1),
                        shift_m=round(float(np.hypot(dx, dy)), 1), cue_diff_m=None if cue_diff is None else round(cue_diff, 1)))
    return out


def ransac_affine(en, uv, thr, seed, iters=2000):
    """RANSAC affine UTM -> pixel; returns (2x3 matrix, inlier mask). thr in metres (via inverse scale)."""
    rng = np.random.default_rng(seed); best = None
    X = np.c_[en, np.ones(len(en))]
    for _ in range(iters):
        j = rng.choice(len(en), 3, replace=False)
        try:
            Bm = np.linalg.solve(X[j], uv[j])
        except np.linalg.LinAlgError:
            continue
        px = np.sqrt(abs(np.linalg.det(Bm[:2].T)))      # pixels per metre
        r = np.hypot(*(X @ Bm - uv).T) / max(px, 1e-9)
        inl = r < thr
        if best is None or inl.sum() > best[1].sum():
            best = (Bm, inl)
    Bm, inl = best
    Bm, *_ = np.linalg.lstsq(X[inl], uv[inl], rcond=None)
    return Bm.T, inl


def run_target(C, st, name, t, P, osm, dry=False):
    """Full validation for one historical source; returns summary dict. dry=True: no files written."""
    bbox = t['bbox_utm']
    P = {**P, **t.get('match', {})}                     # per-target matching overrides
    if t['kind'] == 'corona' and t.get('scan'):
        S = corona_source(C, t['entity'], t['piece'], recorded_T(C, t), bbox, C.f(t['scan']))
    elif t['kind'] == 'corona':
        S = corona_source(C, t['entity'], t['piece'], recorded_T(C, t), bbox)
    else:
        S = soi_source(C, C.f(t['sheet']))
    if t.get('osm'):
        osm = gpd.read_file(C.f(t['osm'])).to_crs(C['crs'])
    P['_s2'] = t.get('s2', C['inputs']['s2_dry'])       # Sentinel-2 reference used by the 's2' cue
    roads = list(osm[osm.category == 'road'].cx[bbox[0] - 2000:bbox[2] + 2000, bbox[1] - 2000:bbox[3] + 2000].geometry)
    osm_path = C.f(t.get('osm', C['inputs']['osm']))   # comparison regions carry their own OSM extract
    cands = V.osm_candidates(osm_path, bbox, P['min_sep_m'])
    excl = set(P.get('exclude_kinds', []))            # e.g. drop tanks/villages (poorly defined points)
    cands = [c for c in cands if c['kind'] not in excl]
    if t.get('inner_bbox_utm'):      # denser candidates close to the site itself (where the findings are)
        extra = [q for q in V.osm_candidates(osm_path, t['inner_bbox_utm'], t['inner_min_sep_m']) if q['kind'] not in excl]
        cands += [dict(q, id='IN' + q['id']) for q in extra
                  if all(np.hypot(q['E'] - c['E'], q['N'] - c['N']) >= t['inner_min_sep_m'] for c in cands)]
    # pass 1: wide search around the recorded transform, robust affine update
    cues = t.get('cues', ['road'])
    t1 = collect(C, S, cands, roads, P, P['search1_m'], cues)
    en1 = np.array([[q['E'], q['N']] for q in t1]); uv1 = np.array([[q['u'], q['v']] for q in t1])
    if len(t1) >= 6:
        T1, inl = ransac_affine(en1, uv1, P['ransac_m'], C['seed'])
        if inl.sum() >= 6:
            S.T = T1
    st.note(f'{name}: {len(cands)} OSM candidates; pass 1 {len(t1)} matches'
            + (f', {int(inl.sum())} RANSAC inliers' if len(t1) >= 6 else ''))
    # pass 2: narrow search around the updated prediction = final ties
    ties = collect(C, S, cands, roads, P, P['search2_m'], cues)
    en = np.array([[q['E'], q['N']] for q in ties]); uv = np.array([[q['u'], q['v']] for q in ties])
    # blunder screen: points > blunder_m from a robust 2nd-order fit are flagged and excluded (reported)
    keep = np.ones(len(ties), bool)
    if len(ties) >= 12:
        for _ in range(3):
            M = V.Model('poly2').fit(uv[keep], en[keep]); r = np.hypot(*(en - M(uv)).T)
            keep = r < max(P['blunder_m'], 3 * 1.4826 * np.median(r[keep]))
    for q, k in zip(ties, keep):
        q['blunder'] = bool(not k)
    tie_all = ties; ties = [q for q in ties if not q['blunder']]
    en, uv = en[keep], uv[keep]
    n = len(ties)
    summ = dict(params_effective={k: P[k] for k in ('min_ncc', 'agree_m', 'min_sep_m', 'min_z', 'res_m', 'half_m', 'search2_m')},
                exclude_kinds=sorted(excl), kind=t['kind'], label=t['label'], n_candidates=len(cands), n_pass1=len(t1), n_ties=n,
                n_blunders=int((~keep).sum()), kinds={k: int(sum(q['kind'] == k for q in ties)) for k in V.PRIORITY})
    if n < 8:
        st.note(f'{name}: only {n} ties; not evaluated'); summ['status'] = 'too few ties'
        return (dict(n_ties=n) if dry else summ), None
    # 'before': recorded transform. Its forward (pixel -> UTM) is the exact inverse of the affine (CORONA)
    # or of the corner georeference (SoI, evaluated through the GeoTIFF transform).
    rec_en = rec_forward(C, S, t, uv)
    before = en - rec_en
    # control / check split stratified by spatial block
    rng = np.random.default_rng(C['seed']); blocks = V.spatial_blocks(en, min(P['k_blocks'], n // 4), C['seed'])
    ctrl = np.ones(n, bool)
    for b in np.unique(blocks):
        idx = np.where(blocks == b)[0]; k = int(round(len(idx) * (1 - P['control_frac'])))
        ctrl[rng.choice(idx, k, replace=False)] = False
    ev = V.evaluate(uv, en, P['models'], ctrl, C['seed'], nboot=P['n_boot'], k_blocks=min(P['k_blocks'], n // 4))
    # model choice: lowest leave-spatial-block-out RMSE (the most demanding test: predicting a whole area with
    # no control points); a simpler model is preferred if within 10 %. The check set (~30 % of points) is too
    # small on its own to rank four models reliably, so it is reported but not used for selection.
    order = [k for k in P['models'] if k in ev]
    bestk = min(order, key=lambda k: ev[k]['block_cv_rmse_m'])
    for k in order:
        if ev[k]['block_cv_rmse_m'] <= 1.10 * ev[bestk]['block_cv_rmse_m']:
            bestk = k; break
    # per-point table
    df = pd.DataFrame(ties)
    df['role'] = np.where(ctrl, 'control', 'check'); df['block'] = blocks
    df['before_dE'], df['before_dN'] = before[:, 0].round(1), before[:, 1].round(1)
    for k in order:
        loo = np.array(ev[k].pop('_loo')); chk = np.array(ev[k].pop('_check_res'))
        df[f'{k}_loo_dE'], df[f'{k}_loo_dN'] = loo[:, 0].round(1), loo[:, 1].round(1)
    df['lon'], df['lat'] = geo.utm2ll(df.E.values, df.N.values)
    blk = pd.DataFrame([q for q in tie_all if q['blunder']])
    if dry:
        m = ev[bestk]
        return dict(n_ties=n, chosen=bestk, before_rmse_m=V.rms(before), loo_rmse_m=m['loo_rmse_m'], block_cv_rmse_m=m['block_cv_rmse_m'],
                    check_rmse_m=m['check_rmse_m'], **{f'{k}_loo_m': ev[k]['loo_rmse_m'] for k in order}), None
    df.to_csv(C.out('results', 'validation', f'{name}_ties.csv'), index=False)
    blk.to_csv(C.out('results', 'validation', f'{name}_blunders.csv'), index=False)   # always written (may be empty)
    bh = np.hypot(*before.T)
    summ.update(status='ok', before=dict(rmse_all_m=V.rms(before), rmse_check_m=V.rms(before[~ctrl]), median_m=float(np.median(bh)),
                                         p90_m=float(np.percentile(bh, 90)), max_m=float(bh.max()),
                                         mean_shift_EN_m=before.mean(0).round(1).tolist()),
                models=ev, chosen=bestk,
                extent_km=[round((en[:, 0].max() - en[:, 0].min()) / 1000, 1), round((en[:, 1].max() - en[:, 1].min()) / 1000, 1)])
    # store the chosen model (refit on ALL ties) for downstream use
    model = dict(kind=bestk, smoothing=ev[bestk]['smoothing'], uv=uv.tolist(), en=en.tolist(), source=t, loo_rmse_m=ev[bestk]['loo_rmse_m'], block_cv_rmse_m=ev[bestk]['block_cv_rmse_m'],
                 T_rec=S.T_rec.tolist())
    p = C.code_out(f'params/validation_models/{name}.json')
    json.dump(model, open(p, 'w'), indent=0)
    st.note(f"{name}: {n} ties ({summ['n_blunders']} blunders excluded), extent {summ['extent_km']} km; before RMSE "
            f"{summ['before']['rmse_all_m']:.0f} m; " + '; '.join(f"{k} check {ev[k]['check_rmse_m']:.0f} / LOO {ev[k]['loo_rmse_m']:.0f} / block {ev[k]['block_cv_rmse_m']:.0f} m" for k in order)
            + f'; chosen {bestk}')
    return summ, (S, model)


def recorded_T(C, t):
    """Recorded UTM -> scan-pixel affine for CORONA targets (as used by stage 03)."""
    if t['transform'] == 'da224_An':
        g = C['corona']['da224_crops'][t['crop']]
        An = np.array(json.load(open(C.code(g['params'])))['An'])
        s2 = rasterio.open(C.f(C['inputs']['s2_dry'])); x, y = geo.ll2utm(*g['window_lonlat'])
        wt = s2.window_transform(from_bounds(x - 6000, y - 6000, x + 6000, y + 6000, s2.transform))
        Ai = cv2.invertAffineTransform(An)                      # S2-window px -> scan px
        W = np.array([[1 / wt.a, 0, -wt.c / wt.a], [0, 1 / wt.e, -wt.f / wt.e], [0, 0, 1]])   # UTM -> window px
        return (np.vstack([Ai, [0, 0, 1]]) @ W)[:2]
    if t['transform'] == 'df224_F':
        F = np.array(json.load(open(C.code(t['params'])))['F'])  # scan px -> UTM
        return cv2.invertAffineTransform(F)
    if t['transform'] == 'site_fit':                             # comparison sites: scan px -> S2 px affine 'A'
        g = C['sites'][t['site']]; A = np.vstack([np.array(json.load(open(C.f(g['fit'])))['A']), [0, 0, 1]])
        with rasterio.open(C.f(g['s2'])) as s:
            T = s.transform
        S2 = np.array([[T.a, T.b, T.c], [T.d, T.e, T.f], [0, 0, 1]])  # S2 px -> UTM
        return np.linalg.inv(S2 @ A)[:2]
    raise ValueError(t['transform'])


def rec_forward(C, S, t, uv):
    """Pixel -> UTM under the recorded transform."""
    if t['kind'] == 'corona':
        Ti = cv2.invertAffineTransform(S.T_rec)
        return uv @ Ti[:, :2].T + Ti[:, 2]
    with rasterio.open(S.path) as r:
        lo, la = r.transform * (uv[:, 0], uv[:, 1])
    return np.c_[geo.ll2utm(lo, la)]


def osm_reference_check(C, st, summary):
    """How consistent are the two references? At CORONA ties matched by BOTH cues, the OSM-road position and the
    Sentinel-2 image position of the same feature are compared (difference of the two matched offsets)."""
    import glob
    d = []
    for f in glob.glob(str(C.p('results') / 'validation' / 'corona_*_ties.csv')):
        t = pd.read_csv(f); d += t.cue_diff_m.dropna().tolist()
    d = np.array(d)
    out = dict(n=int(d.size), rms_m=float(np.sqrt(np.mean(d ** 2))) if d.size else None, median_m=float(np.median(d)) if d.size else None)
    st.note(f"OSM-road vs Sentinel-2 position of the same feature (dual-cue CORONA ties): n={out['n']}, RMS {out['rms_m']} m")
    return out


def qa_montage(C, name, S, model, ncol=6):
    """Per-tie quality-control sheet: historical chip through the CHOSEN model (left) and Sentinel-2 with OSM
    roads (right), 600 m square, cross at the reference position. Written as an 8-bit PNG for visual checking."""
    en, uv = np.array(model['en']), np.array(model['uv'])
    Minv = V.Model(model['kind'], model['smoothing']).fit(en, uv)
    osm = gpd.read_file(C.f(C['inputs']['osm'])).to_crs(C['crs']); roads = list(osm[osm.category == 'road'].geometry)
    res, n = 4.0, 151; tiles = []
    for E, N in en:
        jj, ii = np.meshgrid(np.arange(n) - n // 2, np.arange(n) - n // 2)
        pix = Minv(np.c_[(E + jj * res).ravel(), (N - ii * res).ravel()])
        a = cv2.remap(S.img, (pix[:, 0] - S.off[0]).reshape(n, n).astype(np.float32), (pix[:, 1] - S.off[1]).reshape(n, n).astype(np.float32), cv2.INTER_LINEAR)
        a = V.norm8(a, a > 0) if S.kind == 'corona' else 255 - a
        b = V.norm8(s2_chip(C, E, N, n, res))
        tr = from_origin(E - (n // 2 + .5) * res, N + (n // 2 + .5) * res, res, res)
        rd = rasterize([(g, 1) for g in roads], out_shape=(n, n), transform=tr).astype(bool)
        L = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR); R = cv2.cvtColor(np.clip(b, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        R[rd] = (0, 160, 255)
        for im in (L, R):
            cv2.drawMarker(im, (n // 2, n // 2), (0, 0, 255), cv2.MARKER_CROSS, 15, 1)
        tiles.append(np.hstack([L, np.full((n, 3, 3), 255, np.uint8), R]))
    while len(tiles) % ncol:
        tiles.append(np.full_like(tiles[0], 255))
    rows = [np.hstack([np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=255) for t in tiles[i:i + ncol]]) for i in range(0, len(tiles), ncol)]
    cv2.imwrite(str(C.out('results', 'validation', f'{name}_qa.png')), np.vstack(rows))


def write_v2(C, st, name, S, model):
    """Re-georeferenced crop with the chosen model (inverse fitted UTM -> pixel with the same model kind)."""
    g = C['validation']['targets'][name]['v2_crop']
    en, uv = np.array(model['en']), np.array(model['uv'])
    Minv = V.Model(model['kind'], model['smoothing']).fit(en, uv)
    cx, cy = geo.ll2utm(*g['centre_lonlat']); res, half = g['res_m'], g['half_m']; n = int(2 * half / res)
    X0, Y0 = round(cx - half), round(cy + half)
    jj, ii = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5)
    E, N = X0 + jj * res, Y0 - ii * res
    pix = Minv(np.c_[E.ravel(), N.ravel()])
    u, v = pix[:, 0].reshape(n, n), pix[:, 1].reshape(n, n)
    if S.kind == 'corona':
        t = C['validation']['targets'][name]
        img = corona.sample_affine(C.f(t['scan']) if t.get('scan') else corona.scan_path(C, t['entity'], t['piece']), u, v)
        o = geo.write_tif(C.out('derived', 'corona', g['out']), np.clip(img, 0, 255).astype('uint8'), from_origin(X0, Y0, res, res), nodata=0,
                          tags=dict(SOURCE=t['label'], TRANSFORM=f"{model['kind']} on {len(en)} OSM/road ties (stage 12)"))
    else:
        with rasterio.open(S.path) as r:
            rgb = r.read()
        img = np.stack([cv2.remap(b.astype(np.float32), u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR) for b in rgb])
        o = geo.write_tif(C.out('derived', 'soi', g['out']), np.clip(img, 0, 255).astype('uint8'), from_origin(X0, Y0, res, res),
                          tags=dict(SOURCE=str(S.path.name), TRANSFORM=f"{model['kind']} on {len(en)} road ties (stage 12)"))
    st.note(f'{name}: v2 crop {o.name}')


def sensitivity(C, st, osm):
    """One-at-a-time sensitivity of the Kittur CORONA result to the tie-acceptance settings (were tuned during
    development, so their influence must be shown): results/validation_sensitivity.csv."""
    P0 = C['validation']; t = P0['targets']['corona_da224_kittur']; rows = []
    grid = [('baseline', {})] + [(f'{k}={v}', {k: v}) for k, vs in P0['sensitivity'].items() for v in vs]
    for lab, ov in grid:
        P = {**P0, **t.get('match', {}), **ov}; tt = {**t, 'match': {}}
        r, _ = run_target(C, st, 'corona_da224_kittur', tt, P, osm, dry=True)
        rows.append(dict(setting=lab, **r))
    df = pd.DataFrame(rows); df.to_csv(C.out('results', 'validation_sensitivity.csv'), index=False)
    ok = df.dropna(subset=['loo_rmse_m']) if 'loo_rmse_m' in df else df
    st.note(f"sensitivity (Kittur CORONA): {len(df)} settings; ties {int(df.n_ties.min())}-{int(df.n_ties.max())}; "
            f"chosen-model LOO {ok.loo_rmse_m.min():.0f}-{ok.loo_rmse_m.max():.0f} m; before {ok.before_rmse_m.min():.0f}-{ok.before_rmse_m.max():.0f} m")


def table_and_figure(C, st, summary):
    """Table 2b (before/after accuracy per source and model) and Fig. S8 (residual vectors, before vs chosen)."""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    rows = []
    for name, s in summary['targets'].items():
        if s.get('status') != 'ok':
            continue
        r = dict(source=s['label'], n_ties=s['n_ties'], n_blunders=s['n_blunders'], extent_km=f"{s['extent_km'][0]} x {s['extent_km'][1]}",
                 before_rmse_m=round(s['before']['rmse_all_m'], 1), before_p90_m=round(s['before']['p90_m'], 1), chosen=s['chosen'])
        for k, m in s['models'].items():
            r[f'{k}_check_m'] = round(m['check_rmse_m'], 1); r[f'{k}_loo_m'] = round(m['loo_rmse_m'], 1); r[f'{k}_blockcv_m'] = round(m['block_cv_rmse_m'], 1)
        m = s['models'][s['chosen']]
        r.update(chosen_check_m=round(m['check_rmse_m'], 1), chosen_check_boot95=str([round(v, 1) for v in m['check_rmse_boot95']]) if m['check_rmse_boot95'] else '',
                 chosen_loo_m=round(m['loo_rmse_m'], 1), chosen_loo_p90_m=round(m['loo_p90_m'], 1), chosen_blockcv_m=round(m['block_cv_rmse_m'], 1),
                 moran_I_E=round(m['moran_I_E'][0], 2), moran_p_E=round(m['moran_I_E'][1], 3), moran_I_N=round(m['moran_I_N'][0], 2), moran_p_N=round(m['moran_I_N'][1], 3))
        rows.append(r)
    pd.DataFrame(rows).to_csv(C.out('tables', 'Table2b_georeferencing_validation.csv'), index=False)
    names = [n for n, s in summary['targets'].items() if s.get('status') == 'ok']
    short = lambda lab: (lab.replace('CORONA KH-4A ', '').replace(' (31 Jan 1968)', ', 1968').replace('Survey of India ', 'SoI ')
                         .replace('DS1045-1102', '').replace('DS1040-1039', '').replace('DS1025-1071', ''))
    sc = 20.0                                  # residual exaggeration
    ncol = 3; nrow = int(np.ceil(len(names) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(140 / 25.4, 47 / 25.4 * nrow + 12 / 25.4), squeeze=False)
    for ax, name in zip(axs.ravel(), names):
        t = pd.read_csv(C.p('results') / 'validation' / f'{name}_ties.csv'); k = summary['targets'][name]['chosen']
        E, N = t.E / 1000, t.N / 1000
        kw = dict(angles='xy', scale_units='xy', scale=1000 / sc, width=0.007, headwidth=3, headlength=3.5)
        ax.quiver(E, N, t.before_dE, t.before_dN, color='#D55E00', **kw)
        ax.quiver(E, N, t[f'{k}_loo_dE'], t[f'{k}_loo_dN'], color='#0072B2', **kw)
        ax.plot(E[t.role == 'check'], N[t.role == 'check'], 'k^', ms=2.5, mfc='none', mew=0.5)
        # axis limits include every arrow tip, so no arrow is clipped
        tipx = np.r_[E, E + t.before_dE * sc / 1000, E + t[f'{k}_loo_dE'] * sc / 1000]
        tipy = np.r_[N, N + t.before_dN * sc / 1000, N + t[f'{k}_loo_dN'] * sc / 1000]
        h = 0.56 * max(np.ptp(tipx), np.ptp(tipy))     # square window centred on the arrows
        cx_, cy_ = (tipx.min() + tipx.max()) / 2, (tipy.min() + tipy.max()) / 2
        ax.set_xlim(cx_ - h, cx_ + h); ax.set_ylim(cy_ - h, cy_ + h)
        # reference arrow: 50 m on the ground
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        ax.quiver([x0 + 0.05 * (x1 - x0)], [y0 + 0.05 * (y1 - y0)], [50], [0], color='k', **kw)
        ax.text(x0 + 0.05 * (x1 - x0), y0 + 0.08 * (y1 - y0), '50 m (x20)', fontsize=6)
        ax.set_title(f'{short(summary["targets"][name]["label"])}\nchosen: {k}', fontsize=7, pad=2)
        ax.tick_params(labelsize=6.5, pad=1); ax.set_aspect('equal', adjustable='box')
    for ax in axs.ravel()[len(names):]:
        ax.axis('off')
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color='#D55E00', lw=1.2, label='recorded transform (before)'),
         Line2D([], [], color='#0072B2', lw=1.2, label='chosen model, LOO residual'),
         Line2D([], [], color='k', marker='^', ls='', mfc='none', ms=3, label='held-out check point')]
    fig.legend(handles=h, loc='lower center', ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.0), columnspacing=1.0, handlelength=1.5)
    fig.text(0.5, 0.045, f'UTM 43N easting / northing (km); residual arrows exaggerated x{sc:.0f}', ha='center', fontsize=7)
    fig.tight_layout(rect=(0, 0.07, 1, 1), h_pad=0.6, w_pad=0.4)
    for ext in ('png', 'pdf'):
        fig.savefig(C.out('figures', f'FigS8_georef_residuals.{ext}'), dpi=600 if ext == 'png' else None)
    st.note('Table2b_georeferencing_validation.csv and FigS8_georef_residuals written')


def main(argv=None):
    C = load(); P = C['validation']
    if argv and argv[0] == 'figure':          # redraw Table 2b and Fig. S8 from the saved results only
        with Stage(C, 'validation_figure') as st:
            table_and_figure(C, st, json.load(open(C.p('results') / 'validation.json')))
        return
    with Stage(C, 'validation') as st:
        osm = gpd.read_file(C.f(C['inputs']['osm'])).to_crs(C['crs'])
        summary = dict(params={k: v for k, v in P.items() if k != 'targets'}, targets={},
                       note='params holds the defaults; each target lists the values actually used in params_effective',
                       selection_rule=SELECTION_RULE)
        for name, t in P['targets'].items():
            if argv and name not in argv:
                continue
            s, sm = run_target(C, st, name, t, P, osm)
            summary['targets'][name] = s
            if sm:
                qa_montage(C, name, *sm)
                if t.get('v2_crop'):
                    write_v2(C, st, name, *sm)
        summary['osm_reference'] = osm_reference_check(C, st, summary)
        save_json(summary, C.out('results', 'validation.json'))
        if not argv:
            table_and_figure(C, st, summary)
            sensitivity(C, st, osm)


if __name__ == '__main__':
    main(sys.argv[1:])
