"""Digitised 1968 features: build polygons/lines in UTM from pixel vertices on the 2 m Kittur grid."""
from __future__ import annotations
import numpy as np
import yaml
import geopandas as gpd
from shapely.geometry import Polygon, LineString
from rasterio.transform import Affine


def kittur_transform(C) -> Affine:
    """The 2 m Kittur grid (identical to derived/corona/corona_1968_kittur.tif)."""
    from .geo import ll2utm
    g = C['corona']['da224_crops']['kittur']
    cx, cy = ll2utm(*g['centre_lonlat'])
    return Affine(g['res_m'], 0, round(cx - g['half_m']), 0, -g['res_m'], round(cy + g['half_m']))


def build(C) -> gpd.GeoDataFrame:
    spec = yaml.safe_load(open(C.code(C['features']['file'])))
    T = kittur_transform(C)
    P = lambda pts: [T * (c + 0.5, r + 0.5) for c, r in pts]
    rows = []
    for f in spec['features']:
        if f['kind'] == 'ellipse':
            (c, r), (a, b) = f['centre'], f['axes']
            pts = [(c + a * np.cos(t), r + b * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
            g = Polygon(P(pts))
        elif f['kind'] == 'polygon':
            g = Polygon(P(f['vertices']))
        else:
            g = LineString(P(f['vertices']))
        rows.append(dict(id=f['id'], name=f['name'], kind=f['kind'], geometry=g))
    gdf = gpd.GeoDataFrame(rows, crs=C['crs'])
    gdf['area_ha'] = [round(g.area / 1e4, 2) if g.geom_type == 'Polygon' else np.nan for g in gdf.geometry]
    gdf['length_m'] = [round(g.length, 1) for g in gdf.geometry]
    b = gdf.geometry.bounds
    gdf['ew_m'] = (b.maxx - b.minx).round()
    gdf['ns_m'] = (b.maxy - b.miny).round()
    return gdf.set_index('id', drop=False)
