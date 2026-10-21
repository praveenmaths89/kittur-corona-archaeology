"""Single-analyst benchmark, step 1: candidate features and paired viewing chips.

    python tools/benchmark_chips.py

Candidates are OSM road junctions and road/stream crossings on the Kittur CORONA frame (DA224) that lie at least
250 m from every automatic tie, so the benchmark shares no point with the fitted ties. For each candidate two chips
are written side by side: Sentinel-2 (17 Feb 2026, modern position) and the CORONA scan sampled through the
RECORDED transform (not the fitted one, so the chosen model does not steer where the analyst looks). Both carry a
50 m grid labelled in metres east/north of the chip centre. The analyst reads the feature position on each chip
by eye and enters it in benchmark/picks.csv (step 2: tools/benchmark_eval.py).
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'stages'))
from kittur.config import load
from kittur import validate as V, geo
import s12_validation as S12

OUT = Path('/workspace/kittur_map/benchmark'); HALF = 400; RES = 2.0


def main():
    C = load(); t = C['validation']['targets']['corona_da224_kittur']
    S = S12.corona_source(C, t['entity'], t['piece'], S12.recorded_T(C, t), t['bbox_utm'])
    ties = pd.read_csv(C.f('results/validation/corona_da224_kittur_ties.csv'))
    fE, fN = geo.ll2utm(np.array([74.79107]), np.array([15.60044])); fE, fN = float(fE[0]), float(fN[0])
    cand = V.osm_candidates(C.f(C['inputs']['osm']), t['bbox_utm'], 250.0)
    cand = [c for c in cand if c['kind'] in ('junction', 'bridge')
            and np.hypot(ties.E - c['E'], ties.N - c['N']).min() >= 250
            and t['bbox_utm'][0] + 600 < c['E'] < t['bbox_utm'][2] - 600 and t['bbox_utm'][1] + 600 < c['N'] < t['bbox_utm'][3] - 600]
    for c in cand:
        c['d_fort_km'] = float(np.hypot(c['E'] - fE, c['N'] - fN) / 1000)
    near = sorted([c for c in cand if c['d_fort_km'] <= 2.0], key=lambda c: c['d_fort_km'])
    far = [c for c in cand if c['d_fort_km'] > 2.0]
    rng = np.random.default_rng(1824); far = [far[i] for i in rng.permutation(len(far))[:24]]
    sel = near + far
    pd.DataFrame(sel).to_csv(OUT / 'candidates.csv', index=False)
    n = int(2 * HALF / RES) + 1
    for c in sel:
        s2 = S12.s2_chip(C, c['E'], c['N'], n, RES); co = S.chip(c['E'], c['N'], n, RES)
        fig, ax = plt.subplots(1, 2, figsize=(14, 7.2))
        for a, img, ttl in ((ax[0], s2, 'Sentinel-2 2026'), (ax[1], co, 'CORONA 1968 (recorded transform)')):
            v = img[img > 0]; lo, hi = (np.percentile(v, 1), np.percentile(v, 99)) if v.size else (0, 1)
            a.imshow(img, cmap='gray', vmin=lo, vmax=hi, extent=(-HALF, HALF, -HALF, HALF))
            for g in range(-HALF, HALF + 1, 50):
                a.axvline(g, color='yellow', lw=0.3 if g % 100 else 0.7, alpha=0.7); a.axhline(g, color='yellow', lw=0.3 if g % 100 else 0.7, alpha=0.7)
            a.set_xticks(range(-HALF, HALF + 1, 100)); a.set_yticks(range(-HALF, HALF + 1, 100)); a.tick_params(labelsize=8)
            a.set_title(f"{c['id']} {ttl}", fontsize=10)
        fig.tight_layout(); fig.savefig(OUT / f"chip_{c['id']}.png", dpi=80); plt.close(fig)
    print(len(near), 'near,', len(far), 'far; chips in', OUT)


if __name__ == '__main__':
    main()
