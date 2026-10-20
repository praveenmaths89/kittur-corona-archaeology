"""STAC helpers used by stage 01 (network). Dry-season (Jan-Mar) multi-scene medians on a common 10 m UTM grid."""
from __future__ import annotations
import json
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin

BBOX = (74.74, 15.56, 74.88, 15.76)
X0, Y0, W, H = 470500, 1743000, 1500, 2200
T = from_origin(X0, Y0, 10, 10)
EPOCHS = {  # epoch: (catalogue, collection, years, platforms)
    'L1990': ('pc', 'landsat-c2-l2', [1990, 1991], ['landsat-5']),
    'L2000': ('pc', 'landsat-c2-l2', [1999, 2000, 2001], ['landsat-5', 'landsat-7']),
    'L2010': ('pc', 'landsat-c2-l2', [2009], ['landsat-7']),
    'S2016': ('pc', 'sentinel-2-l2a', [2016, 2017], None),
    'S2020': ('pc', 'sentinel-2-l2a', [2020], None),
    'S2026': ('es', 'sentinel-2-l2a', [2026], None),
}


def _client(cat):
    from pystac_client import Client
    if cat == 'pc':
        import planetary_computer as pc
        return Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=pc.sign_inplace)
    return Client.open('https://earth-search.aws.element84.com/v1')


def epoch(C, ep, n_items=4):
    out = C.f(C['inputs']['epochs'][ep] + '.tif')
    if out.exists():
        return
    from shapely.geometry import shape, box
    cat, coll, yrs, plat = EPOCHS[ep]
    c = _client(cat)
    items = []
    for y in yrs:
        q = {'eo:cloud_cover': {'lt': 15}}
        if plat:
            q['platform'] = {'in': plat}
        items += list(c.search(collections=[coll], bbox=BBOX, datetime=f'{y}-01-01/{y}-03-31', query=q, max_items=60).items())
    items = [i for i in items if shape(i.geometry).contains(box(*BBOX))]
    items.sort(key=lambda i: i.properties['eo:cloud_cover'])
    items = items[:n_items]
    if coll == 'landsat-c2-l2':
        B = {'blue': 'blue', 'green': 'green', 'red': 'red', 'nir': 'nir08', 'swir': 'swir16'}
    elif cat == 'pc':
        B = {'blue': 'B02', 'green': 'B03', 'red': 'B04', 'nir': 'B08', 'swir': 'B11'}
    else:
        B = {'blue': 'blue', 'green': 'green', 'red': 'red', 'nir': 'nir', 'swir': 'swir16'}
    stk = {k: [] for k in B}; used = []
    for i in items:
        for k, a in B.items():
            d = np.full((H, W), np.nan, 'float32')
            with rasterio.open(i.assets[a].href) as s:
                reproject(rasterio.band(s, 1), d, dst_transform=T, dst_crs='EPSG:32643', resampling=Resampling.bilinear, src_nodata=0, dst_nodata=np.nan)
            if coll == 'landsat-c2-l2':
                d = d * 0.0000275 - 0.2
            else:
                off = -0.1 if (cat == 'pc' and i.properties.get('s2:processing_baseline', '0') >= '04.00') else 0
                d = d / 10000 + off
            stk[k].append(d)
        used.append((i.id, i.datetime.strftime('%Y-%m-%d'), round(i.properties['eo:cloud_cover'], 1)))
    M = {k: np.nanmedian(np.stack(v), 0) for k, v in stk.items()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, 'w', driver='GTiff', width=W, height=H, count=5, dtype='float32', crs='EPSG:32643', transform=T, compress='deflate') as d:
        for j, k in enumerate(B):
            d.write(M[k].astype('float32'), j + 1); d.set_band_description(j + 1, k)
    json.dump(used, open(str(out)[:-4] + '.json', 'w'))


def s2_scene(C, item_id, tag, bbox=(74.45, 15.45, 74.95, 15.90)):
    """Single Sentinel-2 scene subset -> stretched true/false colour + NDVI (raw/sentinel/s2_<tag>_*.tif)."""
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    dst = C.p('raw') / 'sentinel'
    if (dst / f's2_{tag}_truecolour.tif').exists():
        return
    item = _client('es').get_collection('sentinel-2-l2a').get_item(item_id)
    arr = {}
    for b in ['blue', 'green', 'red', 'nir']:
        with rasterio.open(item.assets[b].href) as src:
            bb = transform_bounds('EPSG:4326', src.crs, *bbox)
            w = from_bounds(*bb, transform=src.transform).round_offsets().round_lengths()
            arr[b] = src.read(1, window=w, boundless=True, fill_value=0).astype('float32')
            prof = src.profile.copy(); tr = src.window_transform(w)
    prof.update(driver='GTiff', transform=tr, width=arr['red'].shape[1], height=arr['red'].shape[0], compress='deflate', tiled=True, blockxsize=512, blockysize=512)

    def st(a, lo=2, hi=98):
        v = a[a > 0]; p1, p2 = np.percentile(v, [lo, hi]); return (np.clip((a - p1) / (p2 - p1), 0, 1) * 255).astype('uint8')
    for nm, ks in [('truecolour', ['red', 'green', 'blue']), ('falsecolour', ['nir', 'red', 'green'])]:
        p = prof.copy(); p.update(count=3, dtype='uint8', nodata=None, photometric='RGB')
        with rasterio.open(dst / f's2_{tag}_{nm}.tif', 'w', **p) as d:
            d.write(np.stack([st(arr[k]) for k in ks]))
    nd = (arr['nir'] - arr['red']) / (arr['nir'] + arr['red'] + 1e-6)
    p = prof.copy(); p.update(count=1, dtype='float32', nodata=-9999)
    with rasterio.open(dst / f's2_{tag}_ndvi.tif', 'w', **p) as d:
        d.write(np.where(arr['red'] > 0, nd, -9999).astype('float32'), 1)
