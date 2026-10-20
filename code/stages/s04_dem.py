"""Stage 04 - relative stereo DEM from the 11 Nov 1967 CORONA KH-4A pair (DA217 aft / DF217 forward).

Method (semi-global matching on co-registered images; no rigorous camera model):
  1. Both images are on the same 2 m grid (stage 03: SIFT + 2nd-order polynomial to the 1968 crop), so the
     residual along-track (N-S) parallax is proportional to relief that the polynomial did not absorb.
  2. OpenCV StereoSGBM on CLAHE + high-pass (Gaussian sigma 32 m removed) images, transposed so the N-S axis is the matching axis.
  3. Calibration: on 30 m blocks, parallax = s * h_Copernicus + quadratic trend(x, y) by robust least squares
     (3-sigma rejection). Height = (parallax - trend) / s. Height noise = residual SD / |s|.
  4. Nan-aware 16 m smoothing and hillshade.
The height scale is fitted to Copernicus GLO-30 over the whole 5 x 5 km crop (not on the hill), so the stereo
relief of the citadel mound is semi-independent of Copernicus. A rigorous DEM would require a KH-4A camera model
(e.g. Ames Stereo Pipeline); this was not attempted.
"""
from __future__ import annotations
import sys, warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)
from pathlib import Path
import numpy as np
import cv2
import rasterio
from scipy.ndimage import uniform_filter, map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, features


def nan_smooth(z, size):
    m = np.isfinite(z).astype(np.float32)
    a = uniform_filter(np.nan_to_num(z).astype(np.float32), size)
    b = uniform_filter(m, size)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(b > 0.2, a / b, np.nan)


def hillshade(z, res, az=315, alt=45):
    zf = np.where(np.isfinite(z), z, np.nanmedian(z))
    gy, gx = np.gradient(zf, res)
    slope = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
    a, e = np.radians(az), np.radians(alt)
    return np.clip((np.sin(e) * np.cos(slope) + np.cos(e) * np.sin(slope) * np.cos(a - asp)) * 255, 0, 255).astype(np.uint8)


def main(argv=None):
    C = load()
    P = C['dem_stereo']
    with Stage(C, 'dem') as st:
        D = C.p('derived') / 'corona'
        with rasterio.open(D / 'corona_1967DA_kittur.tif') as a, rasterio.open(D / 'corona_1967DF_kittur.tif') as b:
            A, B, T, res = a.read(1), b.read(1), a.transform, a.res[0]
        valid = (A > 5) & (B > 5)
        cl = cv2.createCLAHE(2, (8, 8))
        hp = lambda z: cv2.subtract(z, cv2.GaussianBlur(z, (0, 0), P['highpass_sigma_px'])) + 128
        L, R = hp(cl.apply(A)).T.copy(), hp(cl.apply(B)).T.copy()
        s = P['sgbm']; bs = s['block_size']
        sgbm = cv2.StereoSGBM_create(minDisparity=s['min_disparity'], numDisparities=s['num_disparities'], blockSize=bs,
                                     P1=8 * bs * bs, P2=32 * bs * bs, uniquenessRatio=s['uniqueness'],
                                     speckleWindowSize=s['speckle_window'], speckleRange=s['speckle_range'],
                                     mode=cv2.STEREO_SGBM_MODE_HH)
        d = sgbm.compute(L, R).astype(np.float32).T / 16.0
        d[(d <= s['min_disparity']) | ~valid] = np.nan
        st.note(f'SGBM valid fraction {np.isfinite(d).mean():.2f}')
        # calibration on 30 m blocks
        k = int(P['calib_block_m'] / res); n = A.shape[0] // k
        blk = d[:n * k, :n * k].reshape(n, k, n, k).transpose(0, 2, 1, 3).reshape(n, n, -1)
        db = np.nanmedian(blk, 2)
        Tb = T * T.scale(k, k)
        cop = geo.resample(C.f(C['inputs']['dem']), [1], Tb, n, nodata=np.nan)[0]
        cop[cop < 0] = np.nan
        yy, xx = np.mgrid[0:n, 0:n] / n - 0.5
        X = np.c_[cop.ravel(), np.ones(n * n), xx.ravel(), yy.ravel(), xx.ravel() ** 2, (xx * yy).ravel(), yy.ravel() ** 2]
        y = db.ravel(); ok = np.isfinite(y) & np.isfinite(X).all(1)
        for _ in range(3):
            coef = np.linalg.lstsq(X[ok], y[ok], rcond=None)[0]
            r = y - X @ coef; sd = np.nanstd(r[ok]); ok &= np.abs(r) < 3 * sd
        sc = coef[0]; noise = float(np.std(r[ok]) / abs(sc))
        st.note(f'height scale {sc:.4f} px/m; residual noise {noise:.1f} m (1 sigma, 30 m blocks); {ok.sum()} blocks')
        # full-resolution height
        Y2, X2 = (np.mgrid[0:A.shape[0], 0:A.shape[1]] + 0.5) / k / n - 0.5
        trend = coef[1] + coef[2] * X2 + coef[3] * Y2 + coef[4] * X2 ** 2 + coef[5] * X2 * Y2 + coef[6] * Y2 ** 2
        h = (d - trend) / sc
        hs = nan_smooth(h, int(P['smooth_m'] / res))
        out = C.p('derived') / 'dem'
        tags = dict(METHOD='SGBM N-S parallax DA217/DF217 (co-registered 2 m), linear height calibration + quadratic trend fitted to Copernicus GLO-30; relative DEM',
                    PX_PER_M=sc, NOISE_M=noise)
        geo.write_tif(out / 'corona1967_dem_kittur.tif', h.astype('float32'), T, nodata=np.nan, tags=tags)
        geo.write_tif(out / 'corona1967_dem_kittur_smooth16m.tif', hs.astype('float32'), T, nodata=np.nan, tags=tags)
        geo.write_tif(out / 'corona1967_dem_kittur_hillshade.tif', hillshade(hs, res), T, nodata=0)
        # checks reported in the text
        F = features.build(C)
        core, fort = F.loc['ring_core'].geometry, F.loc['lower_fort'].geometry
        cop2 = geo.resample(C.f(C['inputs']['dem']), [1], T, A.shape[0], nodata=np.nan)[0]
        Xc, Yc = T * (np.mgrid[0:A.shape[1]][None, :] + 0.5, np.mgrid[0:A.shape[0]][:, None] + 0.5)

        def stat(z, geom, r0, r1):
            c = geom.centroid; Dd = np.hypot(Xc - c.x, Yc - c.y)
            inner = np.nanmedian(z[geo.mask(geom, z.shape, T)]) if geom is not None else np.nan
            return float(inner - np.nanmedian(z[(Dd >= r0) & (Dd < r1)]))
        chk = dict(scale_px_per_m=float(sc), noise_m=noise,
                   citadel_core_minus_annulus_220_320_m=dict(stereo=stat(hs, core, 220, 320), copernicus=stat(cop2, core, 220, 320)),
                   lower_fort_minus_annulus_220_320_m=dict(stereo=stat(hs, fort, 220, 320), copernicus=stat(cop2, fort, 220, 320)))
        c = core.centroid; Dd = np.hypot(Xc - c.x, Yc - c.y)
        chk['core_centre_minus_rim_m'] = float(np.nanmedian(hs[Dd < 15]) - np.nanmedian(hs[(Dd >= 30) & (Dd < 70)]))
        for k_, v in chk.items():
            st.note(f'{k_}: {v}')
        leg = C.p('legacy_rasters') / 'corona1967_dem_kittur_smooth16m.tif'
        if leg.exists():
            chk['regression_vs_legacy_smooth16m'] = geo.compare(out / 'corona1967_dem_kittur_smooth16m.tif', leg)
            st.note(f"regression vs legacy: {chk['regression_vs_legacy_smooth16m']}")
        save_json(chk, C.out('results', 'dem_stereo.json'))


if __name__ == '__main__':
    main()
