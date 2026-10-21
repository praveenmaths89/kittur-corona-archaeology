"""Stage 03 - georeference CORONA scans.

Applies the recorded transforms in params/ to the raw scan pieces and writes 2 m UTM 43N crops to
derived/corona/. The transforms were fitted during exploratory work (see README, 'Georeferencing'):
  * DA224 (31 Jan 1968, aft) Kittur and Nandagad: chained local affines (patch NCC against Sentinel-2,
    17 Feb 2026) with a final manual shift checked on the fort and citadel; stored as 'An' (scan px -> S2 10 m window px).
  * DF224 (31 Jan 1968, forward) Sangolli: affine 'F' (scan px -> UTM) transferred from the DA224 overlap and refined.
  * DA223 (31 Jan 1968, aft): coarse frame placement 'utm2raw'; regional crops are presence/absence only.
  * Srirangapatna DA028 (1967) and Hampi DA077 (1965): RANSAC affine on patch-NCC ties (sites/*/corona/*_fit.json).
Re-fitted automatically here:
  * DA217/DF217 (11 Nov 1967) and DF224 over Kittur: located by multi-scale NCC, then SIFT + RANSAC + 2nd-order
    polynomial co-registration to the 1968 Kittur crop.
Accuracy:
  * Recorded independent checkpoints (Nandagad, Kittur) and an automatic patch-NCC check of every crop against
    Sentinel-2 (median-absolute-deviation filtered shifts) -> results/georef_accuracy.json.
"""
from __future__ import annotations
import sys, json, ast
from pathlib import Path
import numpy as np
import cv2
import rasterio
import yaml
from rasterio.windows import from_bounds, Window
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, corona


def da224(C, st):
    piece = corona.scan_path(C, 'DS1045-1102DA224', C['corona']['frames']['DS1045-1102DA224']['piece'])
    s2 = rasterio.open(C.f(C['inputs']['s2_dry']))
    out = {}
    for site, g in C['corona']['da224_crops'].items():
        An = np.array(json.load(open(C.code(g['params'])))['An'])
        x, y = geo.ll2utm(*g['window_lonlat'])
        w = from_bounds(x - 6000, y - 6000, x + 6000, y + 6000, s2.transform)
        wt = s2.window_transform(w)
        cx, cy = geo.ll2utm(*g['centre_lonlat'])
        res, half = g['res_m'], g['half_m']
        n = int(2 * half / res); X0, Y0 = round(cx - half), round(cy + half)
        jj, ii = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5)
        E, N = X0 + jj * res, Y0 - ii * res
        sx, sy = (E - wt.c) / wt.a, (N - wt.f) / wt.e
        Ai = cv2.invertAffineTransform(An)
        u = Ai[0, 0] * sx + Ai[0, 1] * sy + Ai[0, 2]; v = Ai[1, 0] * sx + Ai[1, 1] * sy + Ai[1, 2]
        img = corona.sample_affine(piece, u, v)
        o = geo.write_tif(C.out('derived', 'corona', f'corona_1968_{site}.tif'), np.clip(img, 0, 255).astype('uint8'),
                          from_origin(X0, Y0, res, res), nodata=0,
                          tags=dict(SOURCE='USGS CORONA KH-4A DS1045-1102DA224 piece b (31 Jan 1968, aft)', TRANSFORM=g['params']))
        gsd = res / np.sqrt(abs(np.linalg.det(Ai[:, :2])) / 100) if False else 10 * np.sqrt(abs(np.linalg.det(An[:, :2])))
        out[site] = str(o)
        st.note(f'DA224 {site}: {o.name}; scan pixel ~{1/np.sqrt(abs(np.linalg.det(An[:, :2]))) * 0 + 10*np.sqrt(abs(np.linalg.det(An[:,:2]))):.2f} m')
    return out


def df224(C, st):
    piece = corona.scan_path(C, 'DS1045-1102DF224', C['corona']['frames']['DS1045-1102DF224']['piece'])
    for site, g in C['corona']['df224_crops'].items():
        F = np.array(json.load(open(C.code(g['params'])))['F']); Fi = cv2.invertAffineTransform(F)
        (X0, Y0), n, res = g['origin'], g['n'], g['res_m']
        jj, ii = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5); E, N = X0 + jj * res, Y0 - ii * res
        u = Fi[0, 0] * E + Fi[0, 1] * N + Fi[0, 2]; v = Fi[1, 0] * E + Fi[1, 1] * N + Fi[1, 2]
        img = corona.sample_affine(piece, u, v)
        o = geo.write_tif(C.out('derived', 'corona', f'corona_1968_{site}.tif'), np.clip(img, 0, 255).astype('uint8'),
                          from_origin(X0, Y0, res, res), nodata=0, tags=dict(SOURCE='USGS CORONA KH-4A DS1045-1102DF224 piece c (31 Jan 1968, forward)', TRANSFORM=g['params']))
        st.note(f'DF224 {site}: {o.name}, scan pixel ~{np.sqrt(abs(np.linalg.det(F[:, :2]))):.2f} m')


def da223(C, st):
    g = C['corona']['da223_sites']
    A = np.array(json.load(open(C.code(g['params'])))['utm2raw'])
    shifts = json.load(open(C.code(g['shifts'])))
    piece = corona.scan_path(C, 'DS1045-1102DA223', 'b')
    half, res = g['half_m'], g['res_m']; N = int(2 * half / res)
    for nm, (la, lo) in g['sites'].items():
        X, Y = geo.ll2utm(lo, la)
        gx, gy = np.meshgrid(X - half + np.arange(N) * res + 1, Y + half - np.arange(N) * res - 1)
        u = A[0, 0] * gx + A[0, 1] * gy + A[0, 2]; v = A[1, 0] * gx + A[1, 1] * gy + A[1, 2]
        img = corona.sample_affine(piece, u, v)
        sh = next((s for k, s in shifts.items() if k.lower() == nm), None)
        applied = bool(sh and abs(sh['ncc']) > 0.25)          # shift accepted only when NCC > 0.25 (none were)
        if applied:
            img = cv2.warpAffine(img, np.float32([[1, 0, sh['dx'] / res], [0, 1, sh['dy'] / res]]), (N, N), flags=cv2.WARP_INVERSE_MAP)
        o = geo.write_tif(C.out('derived', 'corona', f'corona_1968DA223_{nm}.tif'), np.clip(img, 0, 255).astype('uint8'),
                          from_origin(X - half, Y + half, res, res), nodata=0, tags=dict(SOURCE='USGS CORONA KH-4A DS1045-1102DA223 piece b', NOTE='coarse placement, +-100-200 m'))
        st.note(f'DA223 {nm}: {o.name} (refinement shift applied: {applied})')


def comparison_sites(C, st):
    for site, g in C['sites'].items():
        J = json.load(open(C.f(g['fit'])))
        s = rasterio.open(C.f(g['s2'])); T = s.transform
        A = np.vstack([np.array(J['A']), [0, 0, 1]]); Ai = np.linalg.inv(A)
        (X0, Y0), n, res = g['origin'], g['n'], g['res_m']
        X, Y = np.meshgrid(X0 + res / 2 + np.arange(n) * res, Y0 - res / 2 - np.arange(n) * res)
        c, r = ~T * (X, Y)
        u = Ai[0, 0] * c + Ai[0, 1] * r + Ai[0, 2]; v = Ai[1, 0] * c + Ai[1, 1] * r + Ai[1, 2]
        img = corona.sample_affine(C.f(g['piece']), u, v)
        o = geo.write_tif(C.out('derived', 'corona', f'corona_{site}.tif'), np.clip(img, 0, 255).astype('uint8'),
                          from_origin(X0, Y0, res, res), crs=s.crs, nodata=0, tags=dict(SOURCE=g['label'], TRANSFORM=g['fit']))
        st.note(f'{site}: {o.name}; recorded fit: {J["n_inl"]}/{J["n_tie"]} ties, fit RMS {J["rms_fit_m"]:.1f} m, LOO RMS {J["rms_loo_m"]:.1f} m')


def coreg_1967(C, st):
    ref_p = C.p('derived') / 'corona' / 'corona_1968_kittur.tif'
    with rasterio.open(ref_p) as r:
        ref = r.read(1); prof = r.profile
    res = {}
    for key, g in C['corona']['coreg_1967'].items():
        piece = corona.scan_path(C, g['entity'], g['piece'])
        if g.get('prior'):        # location predicted from a recorded affine (scan px -> UTM)
            F = np.array(json.load(open(C.code(g['prior'])))['F']); Fi = cv2.invertAffineTransform(F)
            x, y = geo.ll2utm(*C['corona']['da224_crops']['kittur']['centre_lonlat'])
            col, row = [int(v) for v in Fi @ [x, y, 1]]; ncc, rot, gsd = None, None, float(np.sqrt(abs(np.linalg.det(F[:, :2]))))
            how = 'prior affine'
        else:                     # SIFT + RANSAC similarity on 4x reduced images
            col, row, ncc, rot, gsd = corona.locate_sift(piece, ref, 2.0)
            how = f'SIFT locate ({ncc} inliers)'
        gsd = min(max(gsd, 1.6), 2.8)
        R = int(2500 * 2.0 / gsd * 0.75) + 300
        scan = corona.crop(piece, (col - R, row - R, col + R, row + R))
        out, ngcp, rms_px, cov = corona.coregister_sift(scan, ref, ratio=0.8, nfeat=30000)
        p = prof.copy(); p.update(nodata=0)
        o = C.out('derived', 'corona', f"{g['out']}.tif")
        with rasterio.open(o, 'w', **p) as d:
            d.write(out, 1)
            d.update_tags(SOURCE=f"{g['entity']}_{g['piece']}.tif", REF='corona_1968_kittur.tif', GCPS=ngcp, RMS_M_vs_ref=f'{rms_px * 2:.1f}')
        res[key] = dict(entity=g['entity'], piece=g['piece'], locate=how, locate_col=col, locate_row=row, rotation=rot,
                        gsd_m=round(gsd, 2), gcps=ngcp, rms_m=round(rms_px * 2, 2), coverage=round(cov, 3))
        st.note(f'{key}: located at ({col},{row}) by {how}; {ngcp} GCPs, RMS {rms_px * 2:.1f} m vs 1968; coverage {cov:.2f}')
    return res


def mosaic15(C, st):
    g = C['corona']['mosaic15']
    KX, KY = geo.ll2utm(*g['centre_lonlat']); res, half = g['res_m'], g['half_m']; N = int(2 * half / res)
    X, Y = np.meshgrid(KX - half + res / 2 + np.arange(N) * res, KY + half - res / 2 - np.arange(N) * res)
    out = np.zeros((N, N), np.float32); src = np.zeros((N, N), np.uint8)

    def sample(path, u, v):
        from PIL import Image
        im = Image.open(path); W, H = im.size
        ok = (u >= 0) & (v >= 0) & (u < W - 1) & (v < H - 1)
        c0, r0, c1, r1 = int(u[ok].min()), int(v[ok].min()), int(u[ok].max()) + 2, int(v[ok].max()) + 2
        f = 4; sub = np.array(im.crop((c0, r0, c1, r1)).reduce(f)).astype(np.float32)
        val = cv2.remap(sub, ((u - c0) / f).astype(np.float32), ((v - r0) / f).astype(np.float32), cv2.INTER_LINEAR)
        return ok & (val > 8), val
    F = np.vstack([np.array(json.load(open(C.code(C['corona']['df224_crops']['sangolli']['params'])))['F']), [0, 0, 1]]); Fi = np.linalg.inv(F)
    u = Fi[0, 0] * X + Fi[0, 1] * Y + Fi[0, 2]; v = Fi[1, 0] * X + Fi[1, 1] * Y + Fi[1, 2]
    ok, val = sample(corona.scan_path(C, 'DS1045-1102DF224', 'c'), u, v); ok &= v < g['df224_max_row']
    out[ok] = val[ok]; src[ok] = 2
    k = C['corona']['da224_crops']['kittur']
    J = json.load(open(C.code(k['params']))); An = np.vstack([np.array(J['An']), [0, 0, 1]])
    s2 = rasterio.open(C.f(C['inputs']['s2_dry'])); x, y = geo.ll2utm(*k['window_lonlat'])
    wt = s2.window_transform(from_bounds(x - 6000, y - 6000, x + 6000, y + 6000, s2.transform))
    M = np.linalg.inv(np.array([[wt.a, wt.b, wt.c], [wt.d, wt.e, wt.f], [0, 0, 1]]) @ An)
    u = M[0, 0] * X + M[0, 1] * Y + M[0, 2]; v = M[1, 0] * X + M[1, 1] * Y + M[1, 2]
    ok, val = sample(corona.scan_path(C, 'DS1045-1102DA224', 'b'), u, v)
    fill = ok & (src == 0); out[fill] = val[fill]; src[fill] = 1
    tr = from_origin(KX - half, KY + half, res, res)
    geo.write_tif(C.out('derived', 'corona', 'corona_1968_mosaic15km_10m.tif'), np.clip(out, 0, 255).astype('uint8'), tr, nodata=0)
    geo.write_tif(C.out('derived', 'corona', 'corona_1968_mosaic15km_source.tif'), src, tr, nodata=0, tags=dict(VALUES='1=DA224, 2=DF224'))
    st.note(f'mosaic15: DF224 {100 * (src == 2).mean():.0f}%, DA224 {100 * (src == 1).mean():.0f}% of the 32 x 32 km square')


def ncc_check(corona_tif, s2_tif, patch_m=500, step_m=500, search_m=150, thr=0.45, s2_bands=(1, 2, 3)):
    """Automatic accuracy check: patch NCC between the CORONA crop (resampled to 10 m) and Sentinel-2.
    Returns shifts (m) of accepted patches after a 3-MAD outlier filter."""
    with rasterio.open(corona_tif) as c:
        tr10 = c.transform * c.transform.scale(10 / c.res[0], 10 / c.res[1])
        n = int(c.width * c.res[0] / 10)
        A = np.zeros((n, n), np.float32)
        reproject(rasterio.band(c, 1), A, dst_transform=tr10, dst_crs=c.crs, resampling=Resampling.average, src_nodata=0, dst_nodata=0)
        crs = c.crs
    B = np.zeros((len(s2_bands), n, n), np.float32)
    with rasterio.open(s2_tif) as s:
        for i, b in enumerate(s2_bands):
            reproject(rasterio.band(s, b), B[i], dst_transform=tr10, dst_crs=crs, resampling=Resampling.average)
    B = B.mean(0)
    cl = cv2.createCLAHE(2, (8, 8))
    pre = lambda z: cv2.GaussianBlur(cl.apply(np.clip(z / max(np.percentile(z[z > 0], 99.5), 1e-6) * 255, 0, 255).astype(np.uint8)).astype(np.float32), (0, 0), 1.0) if (z > 0).any() else z
    Ap, Bp = pre(A), pre(B)
    P, S, st_ = patch_m // 20, search_m // 10, step_m // 10
    sh = []
    for yy in range(P + S, n - P - S, st_):
        for xx in range(P + S, n - P - S, st_):
            t = Ap[yy - P:yy + P, xx - P:xx + P]
            if (A[yy - P:yy + P, xx - P:xx + P] == 0).mean() > 0.02 or t.std() < 5:
                continue
            r = cv2.matchTemplate(Bp[yy - P - S:yy + P + S, xx - P - S:xx + P + S], t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, l = cv2.minMaxLoc(r)
            if mx > thr and 0 < l[0] < 2 * S and 0 < l[1] < 2 * S:
                sh.append(((l[0] - S) * 10, -(l[1] - S) * 10, mx))
    sh = np.array(sh)
    if len(sh) < 3:
        return dict(n_patches=int(len(sh)), rms_m=None)
    d = sh[:, :2]; med = np.median(d, 0); mad = np.median(np.abs(d - med), 0) * 1.4826 + 5
    keep = (np.abs(d - med) <= 3 * mad).all(1)
    d = d[keep]
    return dict(n_patches=int(len(sh)), n_kept=int(keep.sum()), mean_dE=round(float(d[:, 0].mean()), 1), mean_dN=round(float(d[:, 1].mean()), 1),
                rms_m=round(float(np.sqrt((d ** 2).sum(1).mean())), 1), median_ncc=round(float(np.median(sh[keep, 2])), 2))


def accuracy(C, st, co67):
    acc = {}
    P = json.load(open(C.code('params/checkpoints_nandagad.json')))
    ev = lambda z: np.array(ast.literal_eval(z) if isinstance(z, str) else z, float)
    p, q = ev(P['P']), ev(P['Q'])
    r = (q - p) * 10
    acc['nandagad_recorded_checkpoints'] = dict(n=len(r), rms_m=round(float(np.sqrt((r ** 2).sum(1).mean())), 1),
                                                mean_dE=round(float(r[:, 0].mean()), 1), mean_dN=round(float(-r[:, 1].mean()), 1))
    K = yaml.safe_load(open(C.code('params/checkpoints_kittur.yaml')))
    d = np.array([[k['dE'], k['dN']] for k in K])
    acc['kittur_recorded_checkpoints'] = dict(n=len(d), rms_m=round(float(np.sqrt((d ** 2).sum(1).mean())), 1), points=K)
    s2 = C.f(C['inputs']['s2_dry'])
    D = C.p('derived') / 'corona'
    for nm in ['corona_1968_kittur', 'corona_1968_nandagad', 'corona_1968_sangolli'] + [f'corona_1968DA223_{s}' for s in C['corona']['da223_sites']['sites']]:
        acc[f'{nm}_auto_ncc'] = ncc_check(D / f'{nm}.tif', s2)
    for site, g in C['sites'].items():
        acc[f'corona_{site}_auto_ncc'] = ncc_check(D / f'corona_{site}.tif', C.f(g['s2']), s2_bands=(3, 2, 1))
        J = json.load(open(C.f(g['fit'])))
        acc[f'corona_{site}_recorded_fit'] = dict(ties=J['n_tie'], inliers=J['n_inl'], rms_fit_m=round(J['rms_fit_m'], 1), rms_loo_m=round(J['rms_loo_m'], 1))
    acc['coreg_1967'] = co67
    for k, v in acc.items():
        st.note(f'accuracy {k}: {v}')
    return acc


def regression(C, st):
    D = C.p('derived') / 'corona'; L = C.p('legacy_rasters'); out = {}
    for f in sorted(D.glob('*.tif')):
        leg = L / f.name
        alt = {'corona_srirangapatna.tif': 'corona_1967_DA028_srirangapatna.tif', 'corona_hampi.tif': 'corona_1965_DA077_hampi.tif',
               'corona_1968DA223_oldsangoli.tif': 'corona_1968DA223_oldsangoli.tif'}
        if not leg.exists() and f.name in alt:
            leg = L / alt[f.name]
        site = f.stem.replace('corona_', '')
        if not leg.exists() and site in C['sites'] and C['sites'][site].get('legacy'):
            leg = C.f(C['sites'][site]['legacy'])
        if leg.exists():
            out[f.name] = geo.compare(f, leg)
            st.note(f'regression {f.name} vs legacy: {out[f.name]}')
    return out


def main(argv=None):
    C = load()
    with Stage(C, 'georeference') as st:
        da224(C, st); df224(C, st); da223(C, st); comparison_sites(C, st)
        co67 = coreg_1967(C, st)
        mosaic15(C, st)
        acc = accuracy(C, st, co67)
        save_json(acc, C.out('results', 'georef_accuracy.json'))
        save_json(regression(C, st), C.out('results', 'georef_regression.json'))


if __name__ == '__main__':
    main()
