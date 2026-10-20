"""Coordinate, grid and raster helpers (all analysis in UTM 43N)."""
from __future__ import annotations
import numpy as np
import rasterio
from rasterio.warp import transform as _tr, reproject, Resampling
from rasterio.transform import from_origin
from rasterio.features import geometry_mask

UTM = 'EPSG:32643'


def ll2utm(lon, lat):
    """lon/lat (scalars or arrays) -> UTM 43N x, y."""
    x, y = _tr('EPSG:4326', UTM, np.atleast_1d(lon).tolist(), np.atleast_1d(lat).tolist())
    return (x[0], y[0]) if np.ndim(lon) == 0 else (np.array(x), np.array(y))


def utm2ll(x, y):
    lo, la = _tr(UTM, 'EPSG:4326', np.atleast_1d(x).tolist(), np.atleast_1d(y).tolist())
    return (lo[0], la[0]) if np.ndim(x) == 0 else (np.array(lo), np.array(la))


def grid_centre(lon, lat, half, res):
    """Square grid centred on lon/lat: returns (transform, n, extent[x0,x1,y0,y1])."""
    x, y = ll2utm(lon, lat)
    n = int(round(2 * half / res))
    return from_origin(x - half, y + half, res, res), n, (x - half, x + half, y - half, y + half)


def grid_xy(x, y, half, res):
    n = int(round(2 * half / res))
    return from_origin(x - half, y + half, res, res), n, (x - half, x + half, y - half, y + half)


def resample(path, bands, transform, n, crs=UTM, resampling=Resampling.bilinear, nodata=np.nan):
    """Read `bands` (1-based list) of raster `path` onto an n x n grid."""
    with rasterio.open(path) as s:
        out = np.full((len(bands), n, n), nodata, 'float32')
        for i, b in enumerate(bands):
            reproject(rasterio.band(s, b), out[i], dst_transform=transform, dst_crs=crs,
                      resampling=resampling, dst_nodata=nodata)
    return out


def write_tif(path, arr, transform, crs=UTM, nodata=None, tags=None, dtype=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    a = arr if arr.ndim == 3 else arr[None]
    dtype = dtype or a.dtype
    with rasterio.open(path, 'w', driver='GTiff', width=a.shape[2], height=a.shape[1], count=a.shape[0],
                       dtype=dtype, crs=crs, transform=transform, nodata=nodata, compress='deflate', tiled=True) as d:
        d.write(a.astype(dtype))
        if tags:
            d.update_tags(**{k: str(v) for k, v in tags.items()})
    return path


def mask(geom, shape, transform):
    """Boolean mask, True inside geometry."""
    return geometry_mask([geom], out_shape=shape, transform=transform, invert=True, all_touched=False)


def compare(a_path, b_path):
    """Regression check between two single-band rasters on the same grid: Pearson r, MAD, valid fraction."""
    with rasterio.open(a_path) as A, rasterio.open(b_path) as B:
        if A.shape != B.shape or A.transform != B.transform:
            b = np.zeros(A.shape, 'float32')
            reproject(rasterio.band(B, 1), b, dst_transform=A.transform, dst_crs=A.crs, resampling=Resampling.bilinear)
        else:
            b = B.read(1).astype('float32')
        a = A.read(1).astype('float32')
    nd = lambda z: np.isfinite(z) & (z != 0) & (z != -9999)
    m = nd(a) & nd(b)
    if m.sum() < 100:
        return dict(r=None, mad=None, valid=float(m.mean()))
    return dict(r=round(float(np.corrcoef(a[m], b[m])[0, 1]), 4), mad=round(float(np.mean(np.abs(a[m] - b[m]))), 3),
                valid=round(float(m.mean()), 3))
