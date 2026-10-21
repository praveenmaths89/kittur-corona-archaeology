"""Try to improve the DA224 Kittur georeference: dense patch-NCC ties on gradient images (roads, tank bunds, field
edges) between corona_1968_kittur.tif and Sentinel-2 17 Feb 2026, RANSAC affine correction, leave-one-out RMS.
Writes results/georef_kittur_refine.json. Run from project root."""
import json, numpy as np, cv2, rasterio
from rasterio.warp import reproject, Resampling
R = 'qgis/rasters/'
s = rasterio.open(R + 's2_dry_20260217_truecolour.tif'); S = s.read().astype('float32').mean(0)
c = rasterio.open(R + 'corona_1968_kittur.tif')
C = np.zeros_like(S)
reproject(rasterio.band(c, 1), C, dst_transform=s.transform, dst_crs=s.crs, resampling=Resampling.average, dst_nodata=0)
def grad(z):
    z = cv2.GaussianBlur(z, (0, 0), 1.0); gx = cv2.Sobel(z, cv2.CV_32F, 1, 0); gy = cv2.Sobel(z, cv2.CV_32F, 0, 1)
    g = np.hypot(gx, gy); return (g / (np.percentile(g, 99) + 1e-6)).clip(0, 1).astype('float32')
res = {}
for mode in ['tone', 'gradient']:
    A = grad(C) if mode == 'gradient' else C / (C[C > 0].mean() + 1e-6)
    B = grad(S) if mode == 'gradient' else S / (S.mean() + 1e-6)
    P, Q = 30, 10  # 300 m patch, +-100 m search (10 m px)
    ties = []
    for y in range(P + Q, S.shape[0] - P - Q, 20):
        for x in range(P + Q, S.shape[1] - P - Q, 20):
            t = A[y - P // 2:y + P // 2, x - P // 2:x + P // 2]
            if (C[y - P // 2:y + P // 2, x - P // 2:x + P // 2] == 0).any() or t.std() < 1e-3: continue
            w = B[y - P // 2 - Q:y + P // 2 + Q, x - P // 2 - Q:x + P // 2 + Q]
            r = cv2.matchTemplate(w, t, cv2.TM_CCOEFF_NORMED); _, mx, _, l = cv2.minMaxLoc(r)
            r2 = r.copy(); r2[max(0, l[1] - 2):l[1] + 3, max(0, l[0] - 2):l[0] + 3] = -1
            if mx > 0.35 and mx - r2.max() > 0.05:
                ties.append((x, y, l[0] - Q, l[1] - Q, mx))
    T = np.array(ties, float)
    out = dict(n_ties=len(T))
    if len(T) >= 6:
        src = T[:, :2].astype('float32'); dst = (T[:, :2] + T[:, 2:4]).astype('float32')
        M, inl = cv2.estimateAffine2D(src, dst, ransacReprojThreshold=2.0, maxIters=5000, confidence=0.999)
        k = inl.ravel().astype(bool); out['inliers'] = int(k.sum())
        if k.sum() >= 6:
            si, di = src[k], dst[k]; e = []
            for i in range(len(si)):
                m = np.ones(len(si), bool); m[i] = False
                Mi, _ = cv2.estimateAffine2D(si[m], di[m], method=cv2.LMEDS)
                p = Mi @ np.r_[si[i], 1]; e.append(np.hypot(*(p - di[i])) * 10)
            fit = np.hypot(*((np.c_[si, np.ones(len(si))] @ M.T) - di).T) * 10
            sh = (np.c_[si, np.ones(len(si))] @ M.T) - si
            out.update(rms_fit_m=round(float(np.sqrt((fit ** 2).mean())), 1), rms_loo_m=round(float(np.sqrt((np.array(e) ** 2).mean())), 1),
                       median_shift_m=round(float(np.median(np.hypot(*sh.T)) * 10), 1), affine=M.tolist())
            # zero-correction LOO-equivalent: how far are the raw ties from identity
        out['raw_tie_rms_m'] = round(float(np.sqrt(((T[:, 2:4] * 10) ** 2).sum(1).mean())), 1)
    res[mode] = out
res['soi_1924_roads'] = 'not used as control: 4-corner georeference with errors of the order of 100 m (Table 2), coarser than the 28 m target'
json.dump(res, open('results/georef_kittur_refine.json', 'w'), indent=1); print(json.dumps({k: {a: b for a, b in v.items() if a != 'affine'} if isinstance(v, dict) else v for k, v in res.items()}, indent=1))
