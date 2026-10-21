"""Stage 14 - evidence table for the CORONA 1967-68 feature readings.

Reads params/evidence.yaml (lines of evidence per feature; by-eye readings of the 1924 SoI sheets and the
Landsat/Sentinel-2 epochs on the stage-12 re-georeferenced crops), adds automatic quantities from results/
(OSM overlap and positional stability from stage 13), applies the grading rule stated in the YAML header and
writes results/evidence_table.csv and manuscript/tables/Table8_evidence.csv. Also draws the evidence panels
previews/evidence_kittur.png and previews/evidence_old_sangoli.png (SoI 1924 v2 | CORONA 1968 v2 |
Landsat 1990 | Sentinel-2 2026, v2 feature outlines) for the supplement.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import cv2
import yaml
import pandas as pd
import geopandas as gpd
from rasterio.transform import from_origin
from rasterio.features import rasterize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage
from kittur import geo

POSITIONAL = {'soi1924', 'landsat1990', 'sentinel2026', 'dem', 'osm'}


GRADES = ('confirmed', 'plausible', 'unsupported', 'contradicted')


def grade(ev):
    """Grading rule (see params/evidence.yaml), applied in code:
    contradicted = at least one independent POSITIONAL source contradicts the reading;
    confirmed    = >= 2 positional supporting sources and no contradiction;
    plausible    = exactly 1 positional supporting source and no contradiction;
    unsupported  = no positional support (CORONA and/or text only), or a non-positional contradiction.
    'confirmed' means a feature exists at this place in 1967-68 and in an independent source; it does not
    date the feature to the 1824 siege."""
    if any(e['verdict'] == 'contradict' and e['source'] in POSITIONAL for e in ev):
        return 'contradicted'
    pos = [e for e in ev if e['verdict'] == 'support' and e['source'] in POSITIONAL]
    if any(e['verdict'] == 'contradict' for e in ev) or not pos:
        return 'unsupported'
    return 'confirmed' if len(pos) >= 2 else 'plausible'


def panel(C, centre, half, res, layers, outlines, path):
    """Side-by-side panels on one UTM grid; outlines (shapely) drawn in yellow on all but the first panel."""
    n = int(2 * half / res); tr = from_origin(centre[0] - half, centre[1] + half, res, res)
    def st(a):
        a = np.nan_to_num(a); v = a[a > 0]
        if v.size == 0:
            return np.zeros(a.shape, np.uint8)
        lo, hi = np.percentile(v, [2, 98]); return np.clip((a - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    L = np.zeros((n, n), np.uint8)
    for g in outlines:
        L |= rasterize([(g.boundary if g.geom_type == 'Polygon' else g, 1)], out_shape=(n, n), transform=tr, all_touched=True).astype(np.uint8)
    ims = []
    for k, (p, bands, raw) in enumerate(layers):
        a = geo.resample(C.f(p), bands, tr, n)
        im = np.dstack([np.nan_to_num(a[i]).astype(np.uint8) if raw else st(a[i]) for i in range(len(bands))])
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR) if im.shape[2] == 1 else im[:, :, ::-1].copy()
        if k > 0:
            im[L > 0] = (0, 255, 255)
        ims.append(np.pad(im, ((4, 4), (4, 4), (0, 0)), constant_values=255))
    cv2.imwrite(str(path), np.hstack(ims))


def main(argv=None):
    C = load()
    with Stage(C, 'evidence') as st:
        spec = yaml.safe_load(open(C.code('params/evidence.yaml')))
        prop = json.load(open(C.p('results') / 'propagation.json'))
        auto = {'lower_fort': f"IoU with OSM fort outline {prop['metrics']['iou_fort_osm']['v2']:.2f} (v1 {prop['metrics']['iou_fort_osm']['v1']:.2f}); centroid {prop['metrics']['fort_centroid_to_osm_m']['v2']:.0f} m from OSM centroid",
                'citadel_hill': f"fort-citadel {prop['metrics']['fort_citadel_m']['v2']:.0f} m (95%: {prop['metrics']['fort_citadel_m']['lo95']:.0f}-{prop['metrics']['fort_citadel_m']['hi95']:.0f}); bearing {prop['metrics']['citadel_bearing_deg']['v2']:.0f} deg",
                'old_sangoli': f"v2 shift {prop['old_sangoli']['shift_m']:.0f} m; {prop['old_sangoli']['v2_dist_to_shore_m']:.0f} m from OSM shore; inside outline in {100 * prop['old_sangoli']['frac_inside_reservoir']:.0f}% of realisations, within 100 m of shore in {100 * prop['old_sangoli']['frac_within_100m_of_osm_shore']:.0f}%"}
        rows = []
        for f in spec['features']:
            ev = f['evidence']; g = grade(ev)
            cell = lambda src: next((f"{e['verdict']}: {e['note']}" for e in ev if e['source'] == src), '')
            rows.append(dict(id=f['id'], reading=f['reading'], grade=g, placement=f.get('placement', 'results'),
                             n_positional_support=sum(e['verdict'] == 'support' and e['source'] in POSITIONAL for e in ev), n_contradict=sum(e['verdict'] == 'contradict' for e in ev),
                             gazetteer_1884=cell('gazetteer'), soi_1924=cell('soi1924'), landsat_1990=cell('landsat1990'),
                             sentinel2_2026=cell('sentinel2026'), dem=cell('dem'), osm=cell('osm'), automatic=auto.get(f['id'], '')))
        df = pd.DataFrame(rows)
        df.to_csv(C.out('results', 'evidence_table.csv'), index=False)
        df[['id', 'reading', 'grade', 'placement', 'n_positional_support', 'n_contradict', 'gazetteer_1884', 'soi_1924', 'sentinel2_2026', 'dem', 'osm', 'automatic']].to_csv(
            C.out('tables', 'Table8_evidence.csv'), index=False)
        st.note('grades: ' + ', '.join(f'{k} {v}' for k, v in df.grade.value_counts().items()))
        for r in rows:
            st.note(f"{r['id']}: {r['grade']}")
        # panels
        F = gpd.read_file(C.p('derived') / 'vectors' / 'corona1968_features_v2.gpkg')
        c = F[F.id == 'lower_fort'].geometry.iloc[0].centroid
        soi = 'derived/soi/' + C['validation']['targets']['soi_48I14']['v2_crop']['out']
        panel(C, (c.x, c.y - 250), 900, 2, [(soi, [1, 2, 3], True), ('derived/corona/corona_1968_kittur_v2.tif', [1], False),
                                            (C['inputs']['epochs']['L1990'] + '.tif', [3, 2, 1], False), (C['inputs']['epochs']['S2026'] + '.tif', [3, 2, 1], False)],
              list(F.geometry), C.out('previews', 'evidence_kittur.png'))
        x, y = prop['old_sangoli']['v2_utm']
        osm = gpd.read_file(C.f(C['inputs']['osm'])).to_crs(C['crs'])
        resv = osm[osm.osm_id == 'way/57897786'].geometry.iloc[0]
        from shapely.geometry import Point
        panel(C, (x, y), 1400, 4, [(soi, [1, 2, 3], True), ('derived/corona/corona_1968_sangolli_v2.tif', [1], False),
                                   (C['inputs']['epochs']['S2026'] + '.tif', [3, 2, 1], False)],
              [resv.exterior, Point(x, y).buffer(60)], C.out('previews', 'evidence_old_sangoli.png'))
        st.note('panels: previews/evidence_kittur.png, previews/evidence_old_sangoli.png')


if __name__ == '__main__':
    main()
