"""CORONA scan access and transform application.

Scans are the USGS EarthExplorer 'Declassified Data 1' products: one .tgz per frame with four
TIFF pieces (<entity>_a.tif ... _d.tif) at ~7 microns (~1.8-2.8 m ground sample).
"""
from __future__ import annotations
import tarfile
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def scan_path(C, entity: str, piece: str, extract: bool = True) -> Path:
    """Locate <entity>_<piece>.tif under paths.corona_scans (any depth); extract from raw/corona/<entity>.tgz if absent."""
    base = C.p('corona_scans')
    name = f'{entity}_{piece}.tif'
    hits = sorted(base.rglob(name)) if base.exists() else []
    if hits:
        return hits[0]
    if not extract:
        raise FileNotFoundError(name)
    tgz = C.p('raw') / 'corona' / f'{entity}.tgz'
    dest = base / entity
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz) as t:
        members = [m for m in t.getmembers() if m.name.endswith(name)]
        for m in members:
            m.name = Path(m.name).name
            t.extract(m, dest, filter='data')
    return dest / name


def crop(path: Path, box, reduce: int = 1) -> np.ndarray:
    """Crop (c0, r0, c1, r1) from a (large) scan, clipped to the image, optionally reduced."""
    im = Image.open(path)
    W, H = im.size
    c0, r0, c1, r1 = [int(v) for v in box]
    cc0, rr0, cc1, rr1 = max(0, c0), max(0, r0), min(W, c1), min(H, r1)
    out = np.zeros((r1 - r0, c1 - c0), np.uint8)
    if cc1 > cc0 and rr1 > rr0:
        out[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0] = np.array(im.crop((cc0, rr0, cc1, rr1)))
    if reduce > 1:
        out = cv2.resize(out, (out.shape[1] // reduce, out.shape[0] // reduce), interpolation=cv2.INTER_AREA)
    return out


def sample_affine(path: Path, Ainv_u, Ainv_v, pre_blur: float = 0.0, interp=cv2.INTER_LINEAR) -> np.ndarray:
    """Sample scan at fractional pixel coordinates (u = column, v = row) by bilinear remap."""
    im = Image.open(path)
    W, H = im.size
    c0, r0 = int(np.floor(np.nanmin(Ainv_u))) - 5, int(np.floor(np.nanmin(Ainv_v))) - 5
    c1, r1 = int(np.ceil(np.nanmax(Ainv_u))) + 5, int(np.ceil(np.nanmax(Ainv_v))) + 5
    sub = crop(path, (c0, r0, c1, r1)).astype(np.float32)
    if pre_blur > 0:
        sub = cv2.GaussianBlur(sub, (0, 0), pre_blur)
    return cv2.remap(sub, (Ainv_u - c0).astype(np.float32), (Ainv_v - r0).astype(np.float32), interp, borderValue=0)


def poly2(p):
    """Design matrix of a 2nd-order polynomial in (x, y)."""
    x, y = p[:, 0], p[:, 1]
    return np.c_[np.ones_like(x), x, y, x * x, x * y, y * y]


def coregister_sift(scan: np.ndarray, ref: np.ndarray, ratio=0.8, ransac_px=4.0, poly_tol_px=3.0, nfeat=15000):
    """Co-register a scan crop to a reference grid with SIFT, RANSAC affine and a 2nd-order polynomial.

    Returns (warped image on ref grid, n_gcp, rms_px, coverage)."""
    cl = cv2.createCLAHE(2, (8, 8))
    sift = cv2.SIFT_create(nfeat)

    def feat(x):
        x = cl.apply(x)
        return sift.detectAndCompute(x, (x > 5).astype('uint8'))

    k1, d1 = feat(scan)
    k2, d2 = feat(ref)
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    g = [a for a, b in m if a.distance < ratio * b.distance]
    P = np.float32([k1[x.queryIdx].pt for x in g])
    Q = np.float32([k2[x.trainIdx].pt for x in g])
    M, inl = cv2.estimateAffine2D(P, Q, method=cv2.RANSAC, ransacReprojThreshold=ransac_px, maxIters=50000)
    i = inl.ravel() == 1
    P, Q = P[i], Q[i]
    cx = np.linalg.lstsq(poly2(P), Q[:, 0], rcond=None)[0]
    cy = np.linalg.lstsq(poly2(P), Q[:, 1], rcond=None)[0]
    res = Q - np.c_[poly2(P) @ cx, poly2(P) @ cy]
    ok = np.sqrt((res ** 2).sum(1)) < poly_tol_px
    P, Q = P[ok], Q[ok]
    cx = np.linalg.lstsq(poly2(P), Q[:, 0], rcond=None)[0]
    cy = np.linalg.lstsq(poly2(P), Q[:, 1], rcond=None)[0]
    res = Q - np.c_[poly2(P) @ cx, poly2(P) @ cy]
    rms = float(np.sqrt((res ** 2).sum(1).mean()))
    ci = np.linalg.lstsq(poly2(Q), P[:, 0], rcond=None)[0]
    ri = np.linalg.lstsq(poly2(Q), P[:, 1], rcond=None)[0]
    jj, ii = np.meshgrid(np.arange(ref.shape[1], dtype=np.float64), np.arange(ref.shape[0], dtype=np.float64))
    G = poly2(np.c_[jj.ravel(), ii.ravel()])
    u = (G @ ci).reshape(ref.shape).astype(np.float32)
    v = (G @ ri).reshape(ref.shape).astype(np.float32)
    out = cv2.remap(scan, u, v, cv2.INTER_LINEAR, borderValue=0)
    return out, int(ok.sum()), rms, float((out > 0).mean())


def locate(scan_path: Path, ref: np.ndarray, ref_res: float, scan_gsd_guess=(1.6, 2.8), red=8):
    """Find the approximate scan pixel centre of `ref` (2 m grid image) within a scan piece by multi-scale,
    two-orientation normalised cross-correlation on reduced images. Returns (col, row, ncc, rot180)."""
    im = Image.open(scan_path)
    small = np.array(im.reduce(red)).astype(np.float32)
    cl = cv2.createCLAHE(2, (8, 8))
    pre = lambda z: cv2.GaussianBlur(cl.apply(np.clip(z, 0, 255).astype(np.uint8)).astype(np.float32), (0, 0), 1.0)
    S = pre(small)
    best = (-2, None)
    for gsd in np.arange(scan_gsd_guess[0], scan_gsd_guess[1] + 1e-6, 0.1):
        f = ref_res / (gsd * red)                   # ref px -> reduced scan px
        t = cv2.resize(ref.astype(np.float32), None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        for rot in (0, 180):
          for ang in (-10, -5, 0, 5, 10):
            t0 = t if rot == 0 else t[::-1, ::-1].copy()
            M = cv2.getRotationMatrix2D((t0.shape[1] / 2, t0.shape[0] / 2), ang, 1)
            t0 = cv2.warpAffine(t0, M, (t0.shape[1], t0.shape[0]))
            k = int(t0.shape[0] * 0.15)
            tt = pre(t0[k:-k, k:-k])
            if tt.shape[0] >= S.shape[0] or tt.shape[1] >= S.shape[1]:
                continue
            r = cv2.matchTemplate(S, tt, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            if mx > best[0]:
                best = (mx, ((loc[0] + tt.shape[1] / 2) * red, (loc[1] + tt.shape[0] / 2) * red, rot + ang, gsd))
    mx, (col, row, rot, gsd) = best
    return int(col), int(row), float(mx), rot, float(gsd)


def locate_sift(scan_path: Path, ref: np.ndarray, ref_res: float, gsd_guess=2.2, red=4, nfeat=40000):
    """Locate `ref` in a scan piece with SIFT + RANSAC similarity on reduced images (rotation/scale invariant).
    Returns (col, row, n_inliers, rotation_deg, gsd_m)."""
    im = Image.open(scan_path)
    small = np.array(im.reduce(red))
    cl = cv2.createCLAHE(2, (8, 8))
    f = ref_res / (gsd_guess * red)
    r = cv2.resize(ref, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    sift = cv2.SIFT_create(nfeat)
    k1, d1 = sift.detectAndCompute(cl.apply(r), (r > 5).astype('uint8'))
    k2, d2 = sift.detectAndCompute(cl.apply(small), (small > 5).astype('uint8'))
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    g = [a for a, b in m if a.distance < 0.8 * b.distance]
    P = np.float32([k1[x.queryIdx].pt for x in g]); Q = np.float32([k2[x.trainIdx].pt for x in g])
    M, inl = cv2.estimateAffinePartial2D(P, Q, method=cv2.RANSAC, ransacReprojThreshold=3, maxIters=20000)
    c = np.array([r.shape[1] / 2, r.shape[0] / 2])
    q = M[:, :2] @ c + M[:, 2]
    s = np.hypot(M[0, 0], M[1, 0])
    rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    return int(q[0] * red), int(q[1] * red), int(inl.sum()), rot, float(gsd_guess / s)
