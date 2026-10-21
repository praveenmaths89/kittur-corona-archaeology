"""Stage 08 - journal figures (main + supplementary), generated only from pipeline outputs.

Each figure is written as <name>.tif (RGB, LZW, 600 dpi) and <name>.pdf (vector text/lines, raster layers
embedded at 600 dpi), Arial 6-9 pt, 90/140/190 mm wide. Maps carry UTM 43N km grids, scale bars, north arrows
and panel labels; colours follow the Okabe-Ito palette or cividis (colour-vision-deficiency safe).
Captions: manuscript/figures/figure_captions.md; specs: manuscript/figures/figure_specs.json.

Run all:   python run.py figures
Run some:  python run.py figures fig03 fig06
"""
from __future__ import annotations
import sys, json, zipfile, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import cv2
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.colors import ListedColormap
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from scipy.ndimage import map_coordinates
from shapely.geometry import box as sbox, Point

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage, save_json
from kittur import geo, features, figstyle as fs
from kittur.figstyle import OKABE as OK

warnings.filterwarnings('ignore')
FEAT_STYLE = {  # id: (colour, linestyle, label)
    'lower_fort': (OK['vermillion'], '-', 'Lower-fort enclosure'),
    'moat_nw': (OK['skyblue'], '-', 'N/W moat (dark band)'),
    'outer_east': (OK['yellow'], '-', 'East outer line'),
    'pond_nw': (OK['blue'], '-', 'Ponds'), 'pond_e': (OK['blue'], '-', None),
    'ring_outer': (OK['orange'], '-', 'Citadel rings (outer, middle)'), 'ring_middle': (OK['orange'], '--', None),
    'ring_core': (OK['purple'], '-', 'Citadel core'),
}


# ----------------------------------------------------------------------------------------------- helpers
def window(path, bands, ext, res, crs=geo.UTM, rs=Resampling.bilinear, nodata=0):
    """Resample raster bands onto the rectangular display window ext=(x0,x1,y0,y1) at `res` m."""
    w, h = int(round((ext[1] - ext[0]) / res)), int(round((ext[3] - ext[2]) / res))
    T = from_origin(ext[0], ext[3], res, res)
    out = np.zeros((len(bands), h, w), 'float32')
    with rasterio.open(path) as s:
        for i, b in enumerate(bands):
            reproject(rasterio.band(s, b), out[i], dst_transform=T, dst_crs=crs, resampling=rs, dst_nodata=nodata)
    return out


def show_gray(ax, path, ext, res=2, clahe=True):
    a = window(path, [1], ext, res)[0]
    ax.imshow(fs.clahe(a) if clahe else a, cmap='gray', extent=ext, vmin=0, vmax=255, interpolation='none')


def show_rgb(ax, path, ext, res=10, bands=(1, 2, 3), lo=1, hi=99, crs=geo.UTM):
    a = window(path, list(bands), ext, res, crs=crs)
    ax.imshow(fs.rgb_stretch(a, lo, hi), extent=ext, interpolation='none')


def plot_geom(ax, g, **kw):
    if g.geom_type == 'Polygon':
        x, y = g.exterior.xy; ax.plot(x, y, **kw)
    elif g.geom_type == 'MultiPolygon':
        for p in g.geoms:
            x, y = p.exterior.xy; ax.plot(x, y, **kw); kw.pop('label', None)
    elif g.geom_type in ('LineString',):
        x, y = g.xy; ax.plot(x, y, **kw)
    elif g.geom_type == 'MultiLineString':
        for p in g.geoms:
            x, y = p.xy; ax.plot(x, y, **kw); kw.pop('label', None)


def draw_features(ax, F, ids=None, lw=0.9, halo=True):
    import matplotlib.patheffects as pe
    eff = [pe.Stroke(linewidth=lw + 1.0, foreground='black'), pe.Normal()] if halo else None
    for i, r in F.iterrows():
        if ids and i not in ids:
            continue
        c, ls, lab = FEAT_STYLE[i]
        plot_geom(ax, r.geometry, color=c, ls=ls, lw=lw, label=lab, path_effects=eff, zorder=8)


def feature_legend(ax, loc='lower left', ncol=1):
    import matplotlib.patheffects as pe
    h = [Line2D([], [], color=c, ls=ls, lw=1.1, label=l, path_effects=[pe.Stroke(linewidth=2, foreground='black'), pe.Normal()])
         for c, ls, l in FEAT_STYLE.values() if l]
    ax.legend(handles=h, loc=loc, ncol=ncol, fontsize=7, handlelength=1.8)


def ext_centre(x, y, w, h=None):
    h = h or w
    return (x - w / 2, x + w / 2, y - h / 2, y + h / 2)


def label_pt(ax, x, y, s, dx=0, dy=0, ha='left', color='k', fs_=7, marker='o', mc='k', ms=3):
    import matplotlib.patheffects as pe
    ax.plot(x, y, marker, ms=ms, mfc=mc, mec='white', mew=0.4, zorder=12)
    ax.text(x + dx, y + dy, s, fontsize=fs_, ha=ha, va='center', color=color, zorder=12,
            path_effects=[pe.withStroke(linewidth=1.6, foreground='white')])


class Ctx:
    def __init__(self, C):
        self.C = C
        self.F = features.build(C)
        self.D = C.p('derived')
        self.R = C.p('results')
        self.out = C.p('figures')
        self.specs, self.captions = [], {}
        self.core = self.F.loc['ring_core'].geometry.centroid
        self.fortc = self.F.loc['lower_fort'].geometry.centroid
        self.K = ((self.core.x + self.fortc.x) / 2, (self.core.y + self.fortc.y) / 2)
        self.osm = gpd.read_file(C.f(C['inputs']['osm'])).to_crs(C['crs'])

    def pt(self, name):
        la, lo = self.C['points'][name]
        return geo.ll2utm(lo, la)

    def save(self, f, name, caption, kind='main'):
        meta = fs.save(f, self.out, name)
        meta['kind'] = kind
        self.specs.append(meta)
        self.captions[name] = (kind, caption)
        print(f'  {name}: {meta["width_mm"]} x {meta["height_mm"]} mm, {meta["px"]} px')


# ----------------------------------------------------------------------------------------------- Fig 1
def fig01(X):
    C = X.C
    f = fs.fig('onehalf', 84)   # 140 mm: prints at ~1:1 in the single-column manuscript
    ax0 = f.add_axes([0.075, 0.23, 0.27, 0.75])
    ax1 = f.add_axes([0.43, 0.23, 0.47, 0.75])
    ne = C.p('natural_earth')
    land = gpd.read_file(f"zip://{ne / 'ne_50m_land.zip'}").clip(sbox(66, 5, 92, 25))
    a1 = gpd.read_file(f"zip://{ne / 'ne_10m_admin_1_states_provinces.zip'}")
    ka = a1[a1.iso_3166_2 == 'IN-KA']
    land.plot(ax=ax0, fc='0.88', ec='0.45', lw=0.3)
    ka.plot(ax=ax0, fc=OK['orange'], ec='0.25', lw=0.4, alpha=0.8)
    with rasterio.open(C.f(C['inputs']['dem'])) as d:
        b = d.bounds
    lo, la = geo.utm2ll(np.array([b.left, b.right, b.right, b.left]), np.array([b.bottom, b.bottom, b.top, b.top]))
    ax0.add_patch(Rectangle((lo.min(), la.min()), lo.max() - lo.min(), la.max() - la.min(), fc='none', ec=OK['vermillion'], lw=1.0, zorder=5))
    ax0.annotate('panel b', (lo.max(), la.max()), xytext=(lo.max() + 1.0, la.max() + 0.5), fontsize=7, ha='center',
                 arrowprops=dict(arrowstyle='-', lw=0.5))
    for nm, dx, ha_ in (('Srirangapatna', -0.15, 'right'), ('Hampi', 0.15, 'left')):
        la_, lo_ = C['points'][nm]
        ax0.plot(lo_, la_, '^', ms=3.5, mfc=OK['blue'], mec='k', mew=0.3, zorder=6)
        ax0.text(lo_ + dx, la_, nm, fontsize=7, va='center', ha=ha_)
    # Elsevier map policy: the overview shows only the bounding box of the studied sites (Kittur region,
    # Hampi, Srirangapatna), not a wider country map.
    ax0.text(75.9, 14.3, 'Karnataka', fontsize=7, rotation=0, ha='center', color='0.15')
    ax0.text(74.0, 12.6, 'Arabian\nSea', fontsize=6.5, ha='center', style='italic', color='0.35')
    ax0.set_xlim(73.4, 77.8); ax0.set_ylim(11.8, 16.6); ax0.set_aspect('equal')
    ax0.set_xticks([74, 75, 76, 77]); ax0.set_yticks([12, 13, 14, 15, 16])
    ax0.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}°E'))
    ax0.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}°N'))
    ax0.tick_params(labelsize=7, length=2); ax0.set_facecolor('#e8f1f8'); ax0.set_xlabel(''); ax0.set_ylabel('')
    fs.north_arrow(ax0, x=0.9, y=0.88)
    fs.panel_label(ax0, 'a')
    # panel b
    with rasterio.open(C.f(C['inputs']['dem'])) as d:
        z = d.read(1).astype(float); z[z < 0] = np.nan; T = d.transform; e = (b.left, b.right, b.bottom, b.top)
    with rasterio.open(X.D / 'dem' / 'cop_dem30_hillshade.tif') as h:
        hs = h.read(1)
    ax1.imshow(hs, cmap='gray', extent=e, vmin=0, vmax=255, interpolation='none')
    im = ax1.imshow(z, cmap='cividis', extent=e, alpha=0.55, vmin=600, vmax=950, interpolation='none')
    o = X.osm.cx[e[0]:e[1], e[2]:e[3]]
    for g in o[(o.category == 'road') & o.tags.str.contains('"(?:trunk|primary|motorway)"')].geometry:
        plot_geom(ax1, g, color='0.25', lw=0.45, zorder=3)
    for g in o[(o.category == 'waterway') & o.tags.str.contains('"river"')].geometry:
        plot_geom(ax1, g, color=OK['blue'], lw=0.6, zorder=4)
    wat = o[(o.category == 'water') & (o.geom_type == 'Polygon')]
    wat[wat.area > 2e5].plot(ax=ax1, fc=OK['skyblue'], ec=OK['blue'], lw=0.3, zorder=4)
    # analysed CORONA crops
    for nm, p in [('corona_1968_kittur', 'Kittur'), ('corona_1968_nandagad', 'Nandagad'), ('corona_1968_sangolli', 'Sangolli')] + \
                 [(f'corona_1968DA223_{s}', None) for s in C['corona']['da223_sites']['sites']]:
        with rasterio.open(X.D / 'corona' / f'{nm}.tif') as r:
            bb = r.bounds
        ax1.add_patch(Rectangle((bb.left, bb.bottom), bb.right - bb.left, bb.top - bb.bottom, fc='none',
                                ec=OK['vermillion'] if 'DA223' not in nm else OK['purple'], lw=0.7, ls='-' if 'DA223' not in nm else '--', zorder=6))
    pts = [('Kittur fort', 'Kittur', 900, 0, 'left'), ('Old Sangoli (1968 village)', 'Old Sangoli', 900, 700, 'left'),
           ('Sangolli (present)', 'Sangolli', 900, -500, 'left'), ('Nandagad', 'Nandagad', -900, 0, 'right'),
           ('Bailhongal', 'Bailhongal', 900, -1200, 'left'), ('Belgaum fort', 'Belgaum (Belagavi) fort', 900, 600, 'left'),
           ('Sampgaon', 'Sampgaon', 900, -900, 'left'), ('Tigadi', 'Tigadi', -900, 0, 'right')]
    for k, s, dx, dy, ha in pts:
        x, y = X.pt(k)
        star = k in ('Kittur fort', 'Belgaum fort')
        label_pt(ax1, x, y, s, dx, dy, ha, marker='*' if star else 'o', mc=OK['vermillion'] if star else 'k', ms=6 if star else 3)
    import matplotlib.patheffects as pe
    ax1.text(474500, 1737600, 'Renuka Sagara\n(Malaprabha reservoir)', fontsize=7, color=OK['blue'], style='italic', ha='center', zorder=12,
             path_effects=[pe.withStroke(linewidth=1.5, foreground='white')])
    fs.map_axes(ax1, e, step_m=10000)
    cax = f.add_axes([0.915, 0.40, 0.012, 0.40])
    cb = f.colorbar(im, cax=cax); cb.set_label('Elevation (m)', fontsize=7); cb.ax.tick_params(labelsize=7, length=1.5)
    h = [Line2D([], [], color=OK['blue'], lw=0.8, label='River (OSM)'), Patch(fc=OK['skyblue'], ec=OK['blue'], lw=0.4, label='Reservoir/tank (OSM, 2026)'),
         Line2D([], [], color='0.25', lw=0.6, label='Main road (OSM)'),
         Patch(fc='none', ec=OK['vermillion'], lw=0.8, label='CORONA crop, 2 m (DA224/DF224)'),
         Patch(fc='none', ec=OK['purple'], ls='--', lw=0.8, label='CORONA crop, coarse (DA223)')]
    f.legend(handles=h, loc='lower center', bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=7, frameon=False, columnspacing=1.2, handlelength=1.4)
    fs.panel_label(ax1, 'b')
    X.save(f, 'Fig01_study_area',
           'Study area. (a) Location of the study area (red box) in peninsular India, with Karnataka shaded and the two comparison sites '
           '(Srirangapatna, Hampi). Land and coastline: Natural Earth; map lines delineate study areas and do not necessarily depict '
           'accepted national boundaries. (b) Kittur, Sangolli, Nandagad, Bailhongal and Belgaum on Copernicus GLO-30 elevation over hillshade, '
           'with OpenStreetMap rivers, reservoirs and main roads (2026) and the footprints of the georeferenced CORONA crops. '
           'Grid: UTM zone 43N (km).')


# ----------------------------------------------------------------------------------------------- Fig 2
def fig02(X):
    C = X.C
    f = fs.fig('double', 120)
    gsx = f.add_gridspec(2, 3, height_ratios=[1.25, 1], hspace=0.42, wspace=0.32, left=0.15, right=0.985, top=0.97, bottom=0.08)
    sub = gsx[0, :].subgridspec(1, 2, width_ratios=[1, 2.4], wspace=0.04)
    a1, a2 = f.add_subplot(sub[0]), f.add_subplot(sub[1], sharey=None)
    lanes = ['Military correspondence', 'Engineers / gazetteer', 'Survey of India map', 'CORONA (KH-4/4A/4B)', 'Landsat 5/7', 'Sentinel-2 / -1', 'Copernicus DEM']
    yv = {l: len(lanes) - i for i, l in enumerate(lanes)}
    ev = [('Military correspondence', 1824.8, 1825.0, 'NAI letters, 1824-25'),
          ('Engineers / gazetteer', 1825, 1825, ''), ('Engineers / gazetteer', 1828, 1828, 'Lawe 1825, Welsh 1828'),
          ('Engineers / gazetteer', 1882, 1884, ''),
          ('Survey of India map', 1922, 1924, '1-inch sheets\n(1922-24)'),
          ('CORONA (KH-4/4A/4B)', 1965.78, 1965.78, ''), ('CORONA (KH-4/4A/4B)', 1967.25, 1967.25, ''),
          ('CORONA (KH-4/4A/4B)', 1967.86, 1968.08, '1965-68, c. 2-3 m'),
          ('Landsat 5/7', 1990.1, 1991.2, ''), ('Landsat 5/7', 1999.1, 2000.2, ''), ('Landsat 5/7', 2009.0, 2009.2, '30 m'),
          ('Sentinel-2 / -1', 2016.1, 2017.25, ''), ('Sentinel-2 / -1', 2020.1, 2020.2, ''), ('Sentinel-2 / -1', 2026.1, 2026.8, ''),
          ('Copernicus DEM', 2011, 2015, '30 m')]
    for ax, (x0, x1) in ((a1, (1820, 1890)), (a2, (1918, 2030))):
        for l in lanes:
            ax.axhline(yv[l], color='0.88', lw=0.5, zorder=0)
        for l, s, e_, t in ev:
            if x0 <= s <= x1:
                ax.add_patch(Rectangle((s - 0.4, yv[l] - 0.22), max(e_ - s, 0) + 0.8, 0.44, fc=OK['blue'], ec='none', zorder=3))
                if t:
                    ax.text(e_ + 1.2, yv[l], t, fontsize=7, va='center')
        ax.set_xlim(x0, x1); ax.set_ylim(0.3, len(lanes) + 0.9)
        ax.spines['top'].set_visible(False)
    a1.text(1883, yv['Engineers / gazetteer'] - 0.45, 'Gazetteer 1882-84', fontsize=7, ha='right', va='center')
    a2.text(2021, yv['Sentinel-2 / -1'] - 0.45, '10-20 m', fontsize=7, ha='center', va='center')
    a1.axvspan(1824.8, 1824.95, color=OK['vermillion'], alpha=0.9, zorder=2)
    a1.text(1824.9, len(lanes) + 0.55, 'Siege, Oct-Dec 1824', fontsize=7, color=OK['vermillion'], ha='left')
    a2.axvline(1972, color=OK['vermillion'], ls='--', lw=0.7)
    a2.text(1972.6, len(lanes) + 0.55, 'Malaprabha dam (1972-73)', fontsize=7, color=OK['vermillion'])
    a1.set_yticks([yv[l] for l in lanes]); a1.set_yticklabels(lanes, fontsize=7)
    a2.set_yticks([]); a1.spines['right'].set_visible(False); a2.spines['left'].set_visible(False)
    d = 0.012
    for ax, xx in ((a1, 1), (a2, 0)):
        kw = dict(transform=ax.transAxes, color='k', clip_on=False, lw=0.5)
        ax.plot((xx - d * (2.6 if xx == 0 else 1), xx + d * (2.6 if xx == 0 else 1)), (-d * 2, d * 2), **kw)
    a1.set_xticks([1820, 1840, 1860, 1880]); a2.set_xticks(range(1920, 2031, 10))
    a2.set_xlabel('Year')
    fs.panel_label(a1, 'a', inside=False)
    m = pd.read_csv(X.R / 'epoch_metrics.csv')
    b1, b2, b3 = f.add_subplot(gsx[1, 0]), f.add_subplot(gsx[1, 1]), f.add_subplot(gsx[1, 2])
    for aoi, lab, c, mk in (('oldSangoli_600m', 'within 600 m of Old Sangoli', OK['blue'], 'o'), ('sangolli_valley_3km', 'within 3 km (/10)', OK['skyblue'], 's')):
        q = m[m.aoi == aoi]; sc = 10 if '3km' in aoi else 1
        b1.plot(q.year, q.water_ha / sc, marker=mk, ms=3, color=c, label=lab)
    b1.plot([1968], [0], marker='*', ms=6, color=OK['vermillion'], ls='none', label='1968: river channel only')
    b1.set_ylabel('Dry-season open water (ha)'); b1.legend(loc='upper left', fontsize=7)
    for aoi, lab, c, mk in (('ring_outer_contrast', 'Citadel mound', OK['green'], 'o'), ('fort_enclosure_contrast', 'Lower-fort enclosure', OK['vermillion'], 's')):
        q = m[m.aoi == aoi]; b2.plot(q.year, q.ndvi, marker=mk, ms=3, color=c, label=lab)
    b2.axhline(0, color='k', lw=0.4); b2.set_ylabel('NDVI contrast (inside - 80 m buffer)'); b2.legend(loc='upper left', fontsize=7)
    for aoi, lab, c, mk in (('kittur_1.5km', 'Kittur, 1.5 km radius', OK['black'], 'o'), ('fort_enclosure', 'Lower-fort enclosure', OK['vermillion'], 's'), ('ring_outer', 'Citadel mound', OK['green'], '^')):
        q = m[m.aoi == aoi]; b3.plot(q.year, q.built_frac, marker=mk, ms=3, color=c, label=lab)
    b3.set_ylabel('Bare/built index fraction'); b3.legend(loc='upper left', fontsize=7)
    for ax, lab in ((b1, 'b'), (b2, 'c'), (b3, 'd')):
        ax.axvline(1972, color=OK['vermillion'], ls='--', lw=0.6); ax.set_xlim(1962, 2029); ax.set_xlabel('Year')
        ax.grid(alpha=0.25, lw=0.4); fs.panel_label(ax, lab, inside=False)
    b1.set_ylim(-5, None); b3.set_ylim(0, 0.45)
    X.save(f, 'Fig02_temporal_design',
           'Temporal sampling design and change metrics. (a) Sources by date: colonial correspondence and engineers\' descriptions (1824-1884), '
           'Survey of India one-inch sheets (1922-24), CORONA frames (1965-68), and dry-season (January-March) Landsat and Sentinel-2 medians (1990-2026); '
           'dashed line: completion of the Malaprabha dam. (b) Dry-season open water (MNDWI > 0.1) within 600 m of the 1968 Old Sangoli village and within 3 km '
           '(divided by 10). (c) NDVI contrast between the citadel mound or lower-fort enclosure and an 80 m outer buffer. (d) Fraction of pixels in an '
           'indicative bare/built class (NDBI > -0.05 and NDVI < 0.25); this class confuses bare fallow soil with built surfaces and is shown as a trend only.')


# ----------------------------------------------------------------------------------------------- Fig 3
def fig03(X):
    C = X.C
    e = ext_centre(X.K[0], X.K[1] + 50, 1500, 1500)
    f = fs.fig('double', 196)
    pos = [[0.07, 0.535, 0.43, 0.45], [0.555, 0.535, 0.43, 0.45], [0.07, 0.055, 0.43, 0.45], [0.555, 0.055, 0.43, 0.45]]
    ax = [f.add_axes(p) for p in pos]
    show_rgb(ax[0], X.D / 'soi' / 'SoI_48_I_14_1924_cornergeoref.tif', e, res=2, lo=0, hi=100)
    show_gray(ax[1], X.D / 'corona' / 'corona_1967DA_kittur.tif', e)
    show_gray(ax[2], X.D / 'corona' / 'corona_1968_kittur.tif', e)
    show_rgb(ax[3], C.f(C['inputs']['s2_dry']), e, res=2, lo=1, hi=99.5)
    draw_features(ax[2], X.F); draw_features(ax[3], X.F, lw=0.8)
    ttl = ['Survey of India 48 I/14, 1924', 'CORONA KH-4A DA217, 11 Nov 1967', 'CORONA KH-4A DA224, 31 Jan 1968', 'Sentinel-2 L2A, 17 Feb 2026']
    for i, a in enumerate(ax):
        fs.map_axes(a, e, step_m=500, labels=(('left',) if i in (0,) else ()) + (('bottom',) if i >= 2 else ()) + (('left',) if i == 2 else ()),
                    axis_titles=True)
        fs.panel_label(a, 'abcd'[i])
        a.text(0.5, 0.985, ttl[i], transform=a.transAxes, ha='center', va='top', fontsize=7,
               bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='none', alpha=0.85), zorder=20)
    feature_legend(ax[2], loc='lower left')
    X.save(f, 'Fig03_kittur_fort_epochs',
           'Kittur fort and the citadel mound, 1924-2026 (same 1.5 km window). (a) Survey of India sheet 48 I/14 (surveyed 1922-23), '
           'four-corner georeference with positional errors of the order of 100 m. (b) CORONA DS1044-2134DA217, 11 November 1967, co-registered '
           'to (c). (c) CORONA DS1045-1102DA224, 31 January 1968, with the digitised features; absolute position about 25 m RMS near the fort. '
           '(d) Sentinel-2 L2A true colour, 17 February 2026 (linear percentile stretch), with the 1968 features. CORONA panels: contrast-limited '
           'adaptive histogram equalisation (CLAHE; a non-linear contrast adjustment). Grid: UTM 43N (km).')


# ----------------------------------------------------------------------------------------------- Fig 4
def fig04(X):
    C = X.C
    c = X.core
    e = ext_centre(c.x, c.y + 250, 1100, 1100)
    f = fs.fig('double', 150)
    a = f.add_axes([0.065, 0.53, 0.40, 0.45]); b = f.add_axes([0.545, 0.53, 0.40, 0.45])
    p1 = f.add_axes([0.075, 0.07, 0.40, 0.36]); p2 = f.add_axes([0.575, 0.07, 0.40, 0.36])
    show_gray(a, X.D / 'corona' / 'corona_1968_kittur.tif', e)
    draw_features(a, X.F, ids=['lower_fort', 'ring_outer', 'ring_middle', 'ring_core'], lw=0.7)
    hsd = window(X.D / 'dem' / 'corona1967_dem_kittur_hillshade.tif', [1], e, 2)[0]
    z = window(X.D / 'dem' / 'corona1967_dem_kittur_smooth16m.tif', [1], e, 2, nodata=np.nan)[0]
    b.imshow(hsd, cmap='gray', extent=e, vmin=0, vmax=255, interpolation='none')
    im = b.imshow(z, cmap='cividis', extent=e, alpha=0.6, vmin=715, vmax=775, interpolation='none')
    draw_features(b, X.F, ids=['lower_fort', 'ring_outer'], lw=0.6)
    fc = X.fortc
    L = 500
    prof = {'citadel W-E': ((c.x - L, c.y), (c.x + L, c.y)), 'citadel N-S': ((c.x, c.y - L), (c.x, c.y + L)),
            'lower fort W-E': ((fc.x - L, fc.y), (fc.x + L, fc.y)), 'lower fort N-S': ((fc.x, fc.y - L), (fc.x, fc.y + L))}
    for ax_ in (a, b):
        for k, ((x0, y0), (x1, y1)) in prof.items():
            ax_.plot([x0, x1], [y0, y1], color='white' if 'W-E' in k else OK['yellow'], lw=0.6, ls='-' if 'citadel' in k else ':', zorder=9)
    for i, ax_ in enumerate((a, b)):
        fs.map_axes(ax_, e, step_m=200, labels=('bottom', 'left'), axis_titles=True)
        fs.panel_label(ax_, 'ab'[i])
    a.text(0.5, 0.985, 'CORONA DA224, 31 Jan 1968', transform=a.transAxes, ha='center', va='top', fontsize=7, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5), zorder=20)
    b.text(0.5, 0.985, 'Stereo DEM from DA217/DF217, 11 Nov 1967', transform=b.transAxes, ha='center', va='top', fontsize=7, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5), zorder=20)
    cax = f.add_axes([0.955, 0.58, 0.012, 0.32]); cb = f.colorbar(im, cax=cax); cb.set_label('Height (m), stereo DEM', fontsize=7); cb.ax.tick_params(labelsize=7)
    dems = {'Copernicus GLO-30 (2011-15)': (C.f(C['inputs']['dem']), OK['blue']), 'CORONA stereo (1967)': (X.D / 'dem' / 'corona1967_dem_kittur_smooth16m.tif', OK['vermillion'])}
    t = np.arange(-L, L + 1, 10.0)

    def sample(path, xs, ys):
        with rasterio.open(path) as r:
            Z = r.read(1).astype(float); Z[Z == -9999] = np.nan; cc, rr = ~r.transform * (xs, ys)
            return map_coordinates(Z, [rr - 0.5, cc - 0.5], order=1, cval=np.nan)
    for ax_, which in ((p1, 'citadel'), (p2, 'lower fort')):
        for dn, (path, col) in dems.items():
            for dirn, ls in (('W-E', '-'), ('N-S', '--')):
                (x0, y0), (x1, y1) = prof[f'{which} {dirn}']
                xs, ys = np.linspace(x0, x1, t.size), np.linspace(y0, y1, t.size)
                ax_.plot(t, sample(path, xs, ys), color=col, ls=ls, lw=0.9, label=f'{dn}, {dirn}')
        ax_.set_xlabel('Distance from centre (m; W or S negative)'); ax_.set_ylabel('Height (m)')
        ax_.grid(alpha=0.25, lw=0.4); ax_.set_xlim(-L, L)
        ax_.set_title('Profiles through the citadel mound' if which == 'citadel' else 'Profiles through the lower-fort centre', fontsize=7)
    p1.legend(fontsize=7, loc='upper left', ncol=1); p1.set_ylim(715, 805); p2.set_ylim(700, 760)
    p1.axvspan(-66, 66, color='0.85', zorder=0); p1.text(0, 717, 'core', ha='center', fontsize=7)
    fs.panel_label(p1, 'c', inside=False); fs.panel_label(p2, 'd', inside=False)
    X.save(f, 'Fig04_citadel_stereo_dem',
           'The citadel mound and the 1967 stereo surface. (a) CORONA DA224 (31 January 1968; CLAHE) with the lower-fort enclosure and the three '
           'concentric rings of the citadel mound; white (W-E) and yellow (N-S) lines mark the profiles in (c) and (d) (solid: citadel; dotted: lower fort). '
           '(b) Relative stereo surface from the 11 November 1967 DA217/DF217 pair (semi-global matching, height scale and trend calibrated to Copernicus '
           'GLO-30 over 5 x 5 km, 16 m smoothing, about 8 m height noise), over its hillshade. (c, d) Profiles from Copernicus GLO-30 and the stereo surface '
           'through the citadel core and through the lower-fort centre; grey band: extent of the core. Grid: UTM 43N (km).')


# ----------------------------------------------------------------------------------------------- Fig 5
def fig05(X):
    C = X.C
    xo, yo = X.pt('Old Sangoli (1968 village)'); xn, yn = X.pt('Sangolli (present)')
    e = ext_centre((xo + xn) / 2, (yo + yn) / 2 + 300, 5200, 5200)
    f = fs.fig('double', 112)
    w = 0.293
    ax = [f.add_axes([0.055 + i * (w + 0.027), 0.40, w, 0.585]) for i in range(3)]
    show_rgb(ax[0], X.D / 'soi' / 'SoI_48_I_14_1924_cornergeoref.tif', e, res=4, lo=0, hi=100)
    show_gray(ax[1], X.D / 'corona' / 'corona_1968_sangolli.tif', e, res=4)
    show_rgb(ax[2], C.f(C['inputs']['s2_dry']), e, res=10, lo=1, hi=99.5)
    o = X.osm.cx[e[0]:e[1], e[2]:e[3]]
    wat = o[(o.category == 'water') & (o.geom_type == 'Polygon')]
    for i, a in enumerate(ax):
        for g in wat.geometry:
            plot_geom(a, g, color=OK['skyblue'], lw=0.6, zorder=6)
        a.plot(xo, yo, 'o', ms=9, mfc='none', mec=OK['vermillion'], mew=1.1, zorder=10)
        a.plot(xn, yn, 's', ms=7, mfc='none', mec=OK['yellow'], mew=1.1, zorder=10)
        fs.map_axes(a, e, step_m=1000, labels=('bottom',) + (('left',) if i == 0 else ()), axis_titles=(i == 0))
        fs.panel_label(a, 'abc'[i])
        a.text(0.5, 0.985, ['Survey of India 48 I/14, 1924', 'CORONA KH-4A DF224, 31 Jan 1968', 'Sentinel-2 L2A, 17 Feb 2026'][i],
               transform=a.transAxes, ha='center', va='top', fontsize=7, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5), zorder=20)
    ax[1].set_xlabel('Easting (km, UTM 43N)')
    h = [Line2D([], [], marker='o', ms=6, mfc='none', mec=OK['vermillion'], ls='none', label='Village in 1968 ("Sangoli" of 1924)'),
         Line2D([], [], marker='s', ms=5, mfc='none', mec=OK['yellow'], ls='none', label='Present Sangolli (fields in 1968)'),
         Line2D([], [], color=OK['skyblue'], lw=0.8, label='Reservoir outline (OSM, 2026)')]
    f.legend(handles=h, loc='center', ncol=3, fontsize=7, bbox_to_anchor=(0.5, 0.315), frameon=False)
    b = f.add_axes([0.075, 0.08, 0.40, 0.19]); b2 = f.add_axes([0.58, 0.08, 0.40, 0.19])
    m = pd.read_csv(X.R / 'epoch_metrics.csv'); q = m[m.aoi == 'oldSangoli_600m']
    b.bar(q.year, q.water_ha, width=1.6, color=OK['blue'])
    for x_, y_ in zip(q.year, q.water_ha):
        b.text(x_, y_ + 2, f'{y_:.0f}', ha='center', fontsize=7)
    b.plot(1968, 0, marker='*', ms=6, color=OK['vermillion']); b.axvline(1972, color=OK['vermillion'], ls='--', lw=0.6)
    b.set_xlim(1964, 2029); b.set_ylabel('Water within\n600 m (ha)'); b.set_xlabel('Year'); b.set_ylim(0, 120)
    fs.panel_label(b, 'd', inside=False)
    q2 = m[m.aoi == 'oldSangoli_600m']
    b2.plot(q2.year, q2.ndvi, marker='o', ms=3, color=OK['green'], label='NDVI, 600 m of Old Sangoli')
    q3 = m[m.aoi == 'newSangolli_600m']
    b2.plot(q3.year, q3.ndvi, marker='s', ms=3, color=OK['orange'], label='NDVI, 600 m of present Sangolli')
    b2.axhline(0, color='k', lw=0.4); b2.axvline(1972, color=OK['vermillion'], ls='--', lw=0.6)
    b2.set_xlim(1964, 2029); b2.set_ylabel('Mean NDVI'); b2.set_xlabel('Year'); b2.legend(fontsize=7, loc='lower left')
    fs.panel_label(b2, 'e', inside=False)
    X.save(f, 'Fig05_old_sangoli',
           'Old Sangoli before and after the Malaprabha reservoir (5.2 km window). (a) Survey of India 48 I/14 (1924; four-corner georeference, errors of '
           'the order of 100 m), labelling "Sangoli" on the south bank of the Malaprabha. (b) CORONA DS1045-1102DF224, 31 January 1968 (CLAHE): a '
           'nucleated village beside the pre-dam river (circle) and fields at the site of present Sangolli (square). (c) Sentinel-2, 17 February 2026, '
           'with the reservoir outline from OpenStreetMap. (d) Dry-season open water (MNDWI > 0.1) within 600 m of the 1968 village in each epoch. '
           '(e) Mean dry-season NDVI within 600 m of the old and present villages; negative values indicate standing water. Dashed line: dam completion.')


# ----------------------------------------------------------------------------------------------- Fig 6
def fig06(X):
    C = X.C
    L = json.load(open(X.R / 'landscape.json'))
    cx, cy = L['citadel']['obs_x'], L['citadel']['obs_y']
    with rasterio.open(X.D / 'dem' / 'cop_dem30_hillshade.tif') as h:
        HS = h.read(1); T = h.transform; b = h.bounds
    full = (b.left, b.right, b.bottom, b.top)
    f = fs.fig('double', 158)
    top = [f.add_axes([0.05 + i * 0.305, 0.555, 0.28, 0.43]) for i in range(3)]
    d_ = f.add_axes([0.055, 0.055, 0.40, 0.44]); e_ = f.add_axes([0.53, 0.055, 0.44, 0.44])
    e10 = ext_centre(cx, cy, 12000)
    for i, (nm, col) in enumerate((('citadel', OK['vermillion']), ('lower_fort', OK['blue']))):
        a = top[i]
        a.imshow(HS, cmap='gray', extent=full, vmin=0, vmax=255, interpolation='none')
        with rasterio.open(X.D / 'landscape' / f'viewshed_{nm}.tif') as v:
            V = v.read(1).astype(float)
        V[V != 1] = np.nan
        a.imshow(V, cmap=ListedColormap([col]), extent=full, alpha=0.6, interpolation='none')
        for r_ in (1000, 1500, 5000):
            a.add_patch(plt.Circle((L[nm]['obs_x'], L[nm]['obs_y']), r_, fc='none', ec='k', lw=0.4, ls='--'))
        a.plot(L[nm]['obs_x'], L[nm]['obs_y'], '*', ms=6, mfc='white', mec='k', mew=0.4)
        plot_geom(a, X.F.loc['lower_fort'].geometry, color='k', lw=0.4)
        fs.map_axes(a, e10, step_m=2000, labels=('bottom',) + (('left',) if i == 0 else ()), axis_titles=(i == 0))
        fs.panel_label(a, 'ab'[i])
        a.text(0.5, 0.985, f"{'Citadel' if nm == 'citadel' else 'Lower fort'}: {L[nm]['visible_km2_5km']:.1f} km² within 5 km",
               transform=a.transAxes, ha='center', va='top', fontsize=7, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5), zorder=20)
    top[0].set_xlabel('Easting (km, UTM 43N)')
    # c: commanding ground
    a = top[2]; e6 = ext_centre(cx - 800, cy - 800, 6000)
    with rasterio.open(C.f(C['inputs']['dem'])) as dm:
        Z = dm.read(1).astype(float)
    a.imshow(HS, cmap='gray', extent=full, vmin=0, vmax=255, interpolation='none')
    im = a.imshow(Z, cmap='cividis', extent=full, alpha=0.65, vmin=720, vmax=810, interpolation='none')
    for r_ in (1000, 1500):
        a.add_patch(plt.Circle((cx, cy), r_, fc='none', ec='white', lw=0.5, ls='--'))
    a.plot(cx, cy, '*', ms=7, mfc=OK['vermillion'], mec='k', mew=0.4)
    for an in L['annulus_maxz']:
        if an['r0'] >= 500 and an['r1'] <= 3000:
            a.plot(an['x'], an['y'], '^', ms=3.5, mfc='white', mec='k', mew=0.4)
            a.text(an['x'] - 120, an['y'], f"{an['max_z']:.0f} m", fontsize=7, ha='right', va='center', color='white')
    fs.map_axes(a, e6, step_m=2000, labels=('bottom',), axis_titles=False)
    cax = f.add_axes([0.925, 0.60, 0.008, 0.33]); cb = f.colorbar(im, cax=cax); cb.set_label('Elevation (m)', fontsize=7); cb.ax.tick_params(labelsize=7)
    fs.panel_label(a, 'c')
    a.text(0.5, 0.985, 'Highest ground by distance band', transform=a.transAxes, ha='center', va='top', fontsize=7, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5), zorder=20)
    # d: least-cost paths
    lp = gpd.read_file(X.D / 'vectors' / 'landscape.gpkg', layer='zones_paths')
    d_.imshow(HS, cmap='gray', extent=full, vmin=0, vmax=255, interpolation='none')
    for (nm, col) in (('Belgaum_NW', OK['blue']), ('Dharwad_SE', OK['orange'])):
        g = lp[lp.name == nm].geometry.iloc[0]; p = L['paths'][nm]
        plot_geom(d_, g, color=col, lw=1.2, label=f"From {nm.split('_')[0]}: {p['length_km']:.1f} km, arrives from {p['arrival_bearing_deg']:.0f}°")
    d_.plot(*X.fortc.coords[0], '*', ms=7, mfc=OK['vermillion'], mec='k', mew=0.4, label='Kittur fort')
    d_.legend(loc='upper right', fontsize=7, bbox_to_anchor=(1.0, 0.80))
    fs.map_axes(d_, full, step_m=10000)
    fs.panel_label(d_, 'd')
    # e: zones on CORONA
    e2 = ext_centre(X.K[0] + 120, X.K[1] + 60, 1300, 1300)
    show_gray(e_, X.D / 'corona' / 'corona_1968_kittur.tif', e2)
    zc = {'Battery close to gate (12 m)': OK['vermillion'], 'Crest of glacis (30-100 m)': OK['orange'],
          'Advanced post (150 m of gate)': OK['yellow'], 'Escalade gap lower/upper fort': OK['skyblue']}
    for nm, col in zc.items():
        g = lp[lp.name == nm]
        g.plot(ax=e_, fc=col, ec=col, alpha=0.45, lw=0.6, zorder=7)
    for (nm, col) in (('Belgaum_NW', OK['blue']), ('Dharwad_SE', OK['orange'])):
        plot_geom(e_, lp[lp.name == nm].geometry.iloc[0], color=col, lw=1.0, zorder=8)
    draw_features(e_, X.F, ids=['lower_fort', 'ring_outer'], lw=0.6)
    e_.plot(*L['gate'], '^', ms=5, mfc=OK['vermillion'], mec='k', mew=0.4, zorder=9)
    h = [Patch(fc=c, ec=c, alpha=0.6, label=n) for n, c in zc.items()] + [Line2D([], [], marker='^', ls='none', mfc=OK['vermillion'], mec='k', label='Assumed East Gate')]
    e_.legend(handles=h, loc='upper left', fontsize=7, bbox_to_anchor=(0.0, 0.93))
    fs.map_axes(e_, e2, step_m=500)
    fs.panel_label(e_, 'e')
    X.save(f, 'Fig06_viewshed_approaches',
           'Visibility, command and approaches (Copernicus GLO-30, a surface model). (a, b) Viewsheds from the citadel summit and the lower-fort centre '
           '(observer 10 m above ground, refraction coefficient 0.13; circles at 1, 1.5 and 5 km). (c) Elevation around the citadel (star) with the '
           'highest cell in each distance band (triangles); circles at 1 and 1.5 km. (d) Least-cost routes from the Belgaum (NW) and Dharwad (SE) '
           'bearings to an assumed East Gate (slope-based cost with penalties on dark 1968 tone, ponds and moat). (e) Illustrative zones constructed '
           'from Trewman\'s letter of 8 December 1824 on CORONA DA224 (CLAHE); they are geometric constructions, not located positions. Grid: UTM 43N (km).')


# ----------------------------------------------------------------------------------------------- Fig 7
def lawe_areas(X):
    """Areas implied by Lawe (1825): lower fort 1/6 and citadel 1/10 of the Belgaum fort (OSM outline)."""
    import yaml
    A = yaml.safe_load(open(X.C.code('params/archival.yaml')))
    B = json.load(open(X.R / 'belgaum_fort.json'))
    bases = {'Gazetteer 1884 (100 acres)': B['gazetteer_ha'], 'OSM outline': B['osm_way_ha'], '1968 inner wall line': B['inner_wall_line_ha']}
    lo_, hi_ = min(bases.values()), max(bases.values())
    return dict(bases=bases, lawe_lower=(lo_ * A['lawe_fraction_lower'], hi_ * A['lawe_fraction_lower']),
                lawe_citadel=(lo_ * A['lawe_fraction_citadel'], hi_ * A['lawe_fraction_citadel']))


def fig07(X):
    M = json.load(open(X.R / 'montecarlo.json')); S = np.load(X.R / 'montecarlo_samples.npz')
    T = lawe_areas(X)
    f = fs.fig('double', 80)
    a = f.add_axes([0.20, 0.13, 0.36, 0.80]); b = f.add_axes([0.66, 0.13, 0.32, 0.80])
    ids = ['lower_fort', 'ring_outer', 'ring_middle', 'ring_core', 'pond_e', 'pond_nw']
    for k, i in enumerate(ids):
        v = M['areas_ha_or_length_m'][i]; y = len(ids) - k
        parts = a.violinplot(S[i], positions=[y], vert=False, widths=0.7, showextrema=False)
        for pc in parts['bodies']:
            pc.set_facecolor(OK['skyblue']); pc.set_edgecolor('none'); pc.set_alpha(0.7)
        a.plot([v['lo95'], v['hi95']], [y, y], color='k', lw=1.0)
        a.plot(v['median'], y, 'o', ms=3, color='k')
        a.text(v['hi95'] * 1.08, y, f"{v['median']:.2f} ({v['lo95']:.2f}-{v['hi95']:.2f})", va='center', fontsize=7)
    a.set_yticks(range(len(ids), 0, -1)); a.set_yticklabels([M['areas_ha_or_length_m'][i]['label'] for i in ids])
    a.set_ylim(0.4, len(ids) + 1.4); a.set_xscale('log'); a.set_xlim(0.15, 40); a.set_xlabel('Area (ha, log scale), median and 95% interval')
    a.set_xticks([0.2, 0.5, 1, 2, 5, 10, 20]); a.set_xticklabels(['0.2', '0.5', '1', '2', '5', '10', '20']); a.minorticks_off()
    if T:
        for nm, (v0, v1), col in (('Lawe: lower fort, 1/6 of Belgaum fort', T['lawe_lower'], OK['vermillion']), ('Lawe: citadel, 1/10', T['lawe_citadel'], OK['green'])):
            a.axvspan(v0, v1, color=col, alpha=0.18, lw=0, label=f'{nm}: {v0:.1f}-{v1:.1f} ha')
        a.legend(loc='upper left', fontsize=7)
    a.grid(axis='x', alpha=0.25, lw=0.4, which='both')
    fs.panel_label(a, 'a', inside=False)
    data, pos, cols, labs = [], [], [], []
    for j, (key, lab) in enumerate((('citadel', 'Citadel mound'), ('lower', 'Lower fort'))):
        for k, (dk, dn, col) in enumerate((('Cop', 'Copernicus', OK['blue']), ('COR', '1967 stereo', OK['vermillion']))):
            data.append(S[f'h_{dk}_{key}']); pos.append(j * 3 + k); cols.append(col)
    parts = b.violinplot(data, positions=pos, widths=0.8, showextrema=False)
    for pc, col in zip(parts['bodies'], cols):
        pc.set_facecolor(col); pc.set_edgecolor('none'); pc.set_alpha(0.55)
    for d, p in zip(data, pos):
        lo, md, hi = np.percentile(d, [2.5, 50, 97.5]); b.plot([p, p], [lo, hi], color='k', lw=0.9); b.plot(p, md, 'o', ms=3, color='k')
    b.set_xticks([0.5, 3.5]); b.set_xticklabels(['Citadel mound', 'Lower fort']); b.axhline(0, color='k', lw=0.4)
    b.set_ylabel('Relief above surroundings (m)')
    b.legend(handles=[Patch(fc=OK['blue'], alpha=0.6, label='Copernicus GLO-30'), Patch(fc=OK['vermillion'], alpha=0.6, label='CORONA 1967 stereo')], fontsize=7, loc='upper right')
    b.grid(axis='y', alpha=0.25, lw=0.4)
    fs.panel_label(b, 'b', inside=False)
    X.save(f, 'Fig07_monte_carlo',
           f"Monte Carlo uncertainty (N = {M['N']}, seed {M['seed']}). (a) Areas of the digitised 1968 features: distributions, medians and 95% intervals "
           "under combined georeferencing (25 m RMS translation plus a linear term reaching 50-100 m at 2.5 km), local (10 m) and vertex (4 m) errors; "
           "shaded bands: areas implied by Lawe's 1825 fractions of Belgaum fort, taking its area as 40.5 ha (Gazetteer 1884), 51.8 ha (OpenStreetMap) or 58.0 ha (inner wall line traced on CORONA DA222, 1968). (b) Relief of the citadel summit (above the 300-600 m "
           "surroundings) and of the lower fort (above a 450 m circle) from Copernicus GLO-30 and the 1967 stereo surface, with vertical noise of 2 m and 10 m.")


# ----------------------------------------------------------------------------------------------- Fig 8
def fig08(X):
    C = X.C
    sites = [('Kittur fort', X.D / 'corona' / 'corona_1968_kittur.tif', X.K, 'DA224'),
             ('Old Sangoli', X.D / 'corona' / 'corona_1968DA223_oldsangoli.tif', X.pt('Old Sangoli (1968 village)'), 'DA223'),
             ('Sampgaon', X.D / 'corona' / 'corona_1968DA223_sampgaon.tif', X.pt('Sampgaon'), 'DA223'),
             ('Bailhongal', X.D / 'corona' / 'corona_1968DA223_bailhongal.tif', X.pt('Bailhongal'), 'DA223'),
             ('Tigadi', X.D / 'corona' / 'corona_1968DA223_tigadi.tif', X.pt('Tigadi'), 'DA223')]
    f = fs.fig('double', 92)
    w, g = 0.180, 0.010
    for j, (nm, p, (x, y), fr) in enumerate(sites):
        e = ext_centre(x, y, 1400)
        a = f.add_axes([0.04 + j * (w + g), 0.515, w, 0.43]); b = f.add_axes([0.04 + j * (w + g), 0.07, w, 0.43])
        show_gray(a, p, e)
        show_rgb(b, C.f(C['inputs']['s2_dry']), e, res=5, lo=1, hi=99.5)
        for k, ax in enumerate((a, b)):
            fs.map_axes(ax, e, step_m=500, labels=(('bottom',) if k == 1 else ()) + (('left',) if j == 0 else ()), sb=(j == 0), na=(j == 0), axis_titles=False)
            fs.panel_label(ax, 'abcdefghij'[j + 5 * k])
        a.set_title(f'{nm} ({fr}, 1968)', fontsize=7, pad=2)
    f.text(0.006, 0.73, '1968', rotation=90, fontsize=7, va='center'); f.text(0.006, 0.29, '2026', rotation=90, fontsize=7, va='center')
    f.text(0.5, 0.005, 'Easting (km, UTM 43N); 1.4 km panels', ha='center', fontsize=7)
    X.save(f, 'Fig08_regional_forts',
           'Forts of the Kittur country named in the 1884 Gazetteer, in 1968 (a-e; CORONA, CLAHE) and 2026 (f-j; Sentinel-2, 17 February 2026, linear '
           'stretch). Kittur is from the 2 m DA224 crop; the other sites are from DS1045-1102DA223 placed by a single coarse frame match (positional '
           'uncertainty about 100-200 m), sufficient for presence/absence only. Panels 1.4 km wide; grid UTM 43N (km).')


# ----------------------------------------------------------------------------------------------- Fig 9
SITE_NAMES = {'kittur': 'Kittur', 'srirangapatna': 'Srirangapatna', 'hampi': 'Hampi', 'belgaum': 'Belgaum'}
SITE_COL = {'kittur': OK['vermillion'], 'srirangapatna': OK['blue'], 'hampi': OK['orange'], 'belgaum': OK['green']}


def fig09(X):
    C = X.C
    sites = list(C['sites'])
    nr = len(sites)
    f = fs.fig('double', 66 * nr + 12)
    cm = ListedColormap(['#ffffff', OK['green'], OK['vermillion'], OK['blue']])
    S_all = json.load(open(X.R / 'site_metrics.json'))
    hgt = 0.85 / nr
    bel = gpd.read_file(X.D / 'vectors' / 'belgaum_fort_1968.gpkg', layer='belgaum_utm43n').set_index('name')
    for i, site in enumerate(sites):
        g = C['sites'][site]
        with rasterio.open(X.D / 'corona' / f'corona_{site}.tif') as r:
            bb = r.bounds; crs = r.crs
        e = (bb.left, bb.right, bb.bottom, bb.top)
        y0 = 0.085 + (nr - 1 - i) * (hgt + 0.010)
        ax = [f.add_axes([0.065 + k * 0.315, y0, 0.29, hgt - 0.02]) for k in range(3)]
        show_gray(ax[0], X.D / 'corona' / f'corona_{site}.tif', e, res=4)
        show_rgb(ax[1], C.f(g['s2']), e, res=10, bands=(3, 2, 1), lo=1, hi=99, crs=crs)
        cls = np.load(X.D / 'sites' / f'{site}_classes2026.npy')
        ax[2].imshow(cls, cmap=cm, vmin=-0.5, vmax=3.5, extent=e, interpolation='none')
        S = S_all[site]
        if site == 'belgaum':
            for a in ax[:2]:
                plot_geom(a, bel.loc['moat_outer_edge'].geometry, color=OK['yellow'], lw=0.7)
                plot_geom(a, bel.loc['inner_wall_line'].geometry, color=OK['skyblue'], lw=0.7, ls='--')
        for k, a in enumerate(ax):
            fs.map_axes(a, e, step_m=1000, labels=(('left',) if k == 0 else ()) + (('bottom',) if i == nr - 1 else ()), axis_titles=(k == 0))
            fs.panel_label(a, 'abcdefghijkl'[k + 3 * i])
        ax[0].set_title(g['label'], fontsize=7, pad=2)
        ax[1].set_title(g['s2_label'], fontsize=7, pad=2)
        ax[2].set_title(f"Built/bare {S['built_2026_pct']:.0f}%, vegetation {S['veg_2026_pct']:.0f}%, water {S['water_2026_pct']:.1f}%", fontsize=7, pad=2)
        f.text(0.004, y0 + hgt / 2, SITE_NAMES[site], rotation=90, fontsize=7, va='center', fontweight='bold')
    h = [Patch(fc=OK['green'], label='Vegetation (NDVI > 0.4)'), Patch(fc=OK['vermillion'], label='Built/bare (NDBI > 0, NDVI < 0.25)'),
         Patch(fc=OK['blue'], label='Water (MNDWI > 0.1)'), Line2D([], [], color=OK['yellow'], lw=0.8, label='Belgaum moat, outer edge (1968)'),
         Line2D([], [], color=OK['skyblue'], lw=0.8, ls='--', label='Belgaum inner wall line (1968)')]
    f.legend(handles=h, loc='lower center', ncol=3, fontsize=7, bbox_to_anchor=(0.5, -0.006), frameon=False, columnspacing=1.2, handlelength=1.5)
    acc = json.load(open(X.R / 'georef_accuracy.json'))
    fit = lambda s_: acc[f'corona_{s_}_recorded_fit']
    X.save(f, 'Fig09_transferability',
           'Transfer of the workflow to three other forts (5 x 5 km; left: CORONA, CLAHE; centre: Sentinel-2, linear stretch; right: 2026 index classes). '
           f"Srirangapatna (a-c): KH-4A DS1040-1039DA028, 2 April 1967, affine to Sentinel-2 from {fit('srirangapatna')['inliers']} of {fit('srirangapatna')['ties']} automatic ties "
           f"(leave-one-out RMS {fit('srirangapatna')['rms_loo_m']:.0f} m). Hampi (d-f): KH-4A DS1025-1071DA077, 10 October 1965, provisional affine from "
           f"{fit('hampi')['inliers']} of {fit('hampi')['ties']} ties (leave-one-out RMS {fit('hampi')['rms_loo_m']:.0f} m); bare granite falls in the built/bare class. "
           f"Belgaum (g-i): KH-4A DS1045-1102DA222, 31 January 1968, affine from {fit('belgaum')['inliers']} of {fit('belgaum')['ties']} ties (leave-one-out RMS "
           f"{fit('belgaum')['rms_loo_m']:.0f} m), with the moat traced on the 1968 frame. Grid: UTM 43N (km).")
    f.savefig(X.C.p('previews') / 'sites_overview.png', dpi=200)


def site_epoch_table(X):
    """Kittur (1.5 km) + comparison sites (1.5 km) epoch metrics in one frame."""
    k = pd.read_csv(X.R / 'epoch_metrics.csv'); k = k[k.aoi == 'kittur_1.5km'].assign(site='kittur')
    s = pd.read_csv(X.R / 'sites_epoch_metrics.csv'); s = s[s.aoi == 'r1500m']
    return pd.concat([k[['site', 'epoch', 'year', 'built_frac', 'water_frac', 'ndvi']], s[['site', 'epoch', 'year', 'built_frac', 'water_frac', 'ndvi']]])


def fig10(X):
    d = site_epoch_table(X)
    f = fs.fig('double', 68)
    ax = [f.add_axes([0.065 + i * 0.33, 0.17, 0.26, 0.76]) for i in range(3)]
    mk = {'kittur': 'o', 'srirangapatna': 's', 'hampi': '^', 'belgaum': 'D'}
    for site in ['kittur', 'srirangapatna', 'hampi', 'belgaum']:
        q = d[d.site == site].sort_values('year')
        for a, v in zip(ax, ['built_frac', 'water_frac', 'ndvi']):
            a.plot(q.year, q[v], marker=mk[site], ms=3, color=SITE_COL[site], label=SITE_NAMES[site], lw=0.9)
    for a, lab, l in zip(ax, ['Bare/built index fraction', 'Open-water fraction (MNDWI > 0.1)', 'Mean NDVI'], 'abc'):
        a.set_ylabel(lab); a.set_xlabel('Year'); a.set_xlim(1987, 2029); a.grid(alpha=0.25, lw=0.4); fs.panel_label(a, l, inside=False)
    ax[0].legend(fontsize=7, loc='upper left', ncol=2)
    X.save(f, 'Fig10_cross_site_timelines',
           'Dry-season (January-March) change metrics within 1.5 km of each fort centre, 1990-2026, from Landsat 5/7 and Sentinel-2 median composites '
           '(Kittur: centre between the lower fort and the citadel). (a) Indicative bare/built class (NDBI > -0.05 and NDVI < 0.25; confuses bare soil and rock '
           'with built surfaces). (b) Open water (MNDWI > 0.1). (c) Mean NDVI. Thresholds are identical at all sites.')
    f.savefig(X.C.p('previews') / 'sites_timeline.png', dpi=200)


EPOCH_LAB = {'L1990': 'Landsat\n1990', 'L2000': 'Landsat\n2000', 'L2010': 'Landsat\n2009-10', 'S2016': 'Sentinel-2\n2016-17', 'S2020': 'Sentinel-2\n2020', 'S2026': 'Sentinel-2\n2026'}


def _site_strip_row(X, f, site, y0, h, w=0.133, x0=0.035, half=1500, label_row=True, row_letter='a'):
    C = X.C
    la, lo = C['site_epochs']['centres_latlon'][site]
    x, y = geo.ll2utm(lo, la); e = ext_centre(x, y, 2 * half)
    cols = ['CORONA'] + C['site_epochs']['epochs']
    for j, ep in enumerate(cols):
        a = f.add_axes([x0 + j * (w + 0.004), y0, w, h])
        if ep == 'CORONA':
            show_gray(a, X.D / 'corona' / f'corona_{site}.tif', e, res=4)
            t = C['sites'][site]['label'].split(' ')[-3:]
            tt = 'CORONA\n' + ' '.join(t)
        else:
            p = C.p('sites') / site / 'raw' / 'epochs' / f'{ep}.tif'
            show_rgb(a, p, e, res=10, bands=(3, 2, 1), lo=1, hi=99)
            tt = EPOCH_LAB[ep]
        a.set_xlim(e[0], e[1]); a.set_ylim(e[2], e[3]); a.set_xticks([]); a.set_yticks([])
        if label_row:
            a.set_title(tt, fontsize=7, pad=2)
        if j == 0:
            a.set_ylabel(SITE_NAMES[site], fontsize=7); fs.scalebar(a); fs.north_arrow(a, x=0.85, y=0.80, size=0.13)
        fs.panel_label(a, f'{row_letter}{j + 1}')


def figS6(X):
    sites = list(C_ for C_ in X.C['site_epochs']['centres_latlon'])
    f = fs.fig('double', 36 * len(sites) + 8)
    h = 0.84 / len(sites)
    for i, site in enumerate(sites):
        _site_strip_row(X, f, site, 0.03 + (len(sites) - 1 - i) * (h + 0.03), h - 0.03, label_row=True, row_letter='abc'[i])
    X.save(f, 'FigS6_site_timeline_strips',
           'Image time series for the comparison forts (3 km windows centred on each fort): CORONA (CLAHE) and dry-season Landsat 5/7 and Sentinel-2 median '
           'composites (natural colour, linear percentile stretch) for the epochs in Fig. 10. a: Srirangapatna; b: Hampi; c: Belgaum.', kind='supplementary')


def previews_site_timelines(X):
    """Quick-look PNG per site: image strip + metric curves (previews/timeline_<site>.png)."""
    d = site_epoch_table(X)
    for site in list(X.C['site_epochs']['centres_latlon']) + ['kittur']:
        f = fs.fig('double', 80)
        if site != 'kittur':
            _site_strip_row(X, f, site, 0.52, 0.36, row_letter='')
        q = d[d.site == site].sort_values('year')
        for k, (v, lab) in enumerate((('built_frac', 'Bare/built fraction'), ('water_frac', 'Water fraction'), ('ndvi', 'Mean NDVI'))):
            a = f.add_axes([0.07 + k * 0.33, 0.09 if site != 'kittur' else 0.15, 0.26, 0.32 if site != 'kittur' else 0.75])
            a.plot(q.year, q[v], 'o-', ms=3, color=SITE_COL[site]); a.set_ylabel(lab); a.grid(alpha=0.25, lw=0.4); a.set_xlim(1987, 2029)
        f.suptitle(f'{SITE_NAMES[site]}: dry-season composites, 1.5 km radius', fontsize=8, y=0.995)
        f.savefig(X.C.p('previews') / f'timeline_{site}.png', dpi=150); plt.close(f)


# ----------------------------------------------------------------------------------------------- Supplementary
def figS1(X):
    C = X.C
    eps = ['1924', '1967', '1968', 'L1990', 'L2000', 'L2010', 'S2016', 'S2020', 'S2026']
    lab = {'1924': 'SoI\n1924', '1967': 'CORONA\n1967', '1968': 'CORONA\n1968', 'L1990': 'Landsat\n1990-91', 'L2000': 'Landsat\n1999-2000',
           'L2010': 'Landsat\n2009', 'S2016': 'Sentinel-2\n2016-17', 'S2020': 'Sentinel-2\n2020', 'S2026': 'Sentinel-2\n2026'}
    xo, yo = X.pt('Old Sangoli (1968 village)')
    rows = [('Kittur', ext_centre(X.K[0], X.K[1], 1800), 'corona_1968_kittur', 'corona_1967DA_kittur'),
            ('Old Sangoli', ext_centre(xo, yo - 1500, 5200), 'corona_1968_sangolli', None)]
    f = fs.fig('double', 58)
    w = 0.104
    for i, (nm, e, c68, c67) in enumerate(rows):
        for j, ep in enumerate(eps):
            a = f.add_axes([0.035 + j * (w + 0.003), 0.47 - i * 0.44, w, 0.40])
            res = 4 if i == 0 else 10
            if ep == '1924':
                show_rgb(a, X.D / 'soi' / 'SoI_48_I_14_1924_cornergeoref.tif', e, res=res, lo=0, hi=100)
            elif ep == '1968':
                show_gray(a, X.D / 'corona' / f'{c68}.tif', e, res=res)
            elif ep == '1967':
                if c67:
                    show_gray(a, X.D / 'corona' / f'{c67}.tif', e, res=res)
                else:
                    a.set_facecolor('0.9'); a.text(0.5, 0.5, 'not covered', transform=a.transAxes, ha='center', fontsize=7)
            else:
                show_rgb(a, C.f(C['inputs']['epochs'][ep] + '.tif'), e, res=10 if ep[0] == 'S' else 30, bands=(3, 2, 1), lo=1, hi=99)
            a.set_xlim(e[0], e[1]); a.set_ylim(e[2], e[3]); a.set_xticks([]); a.set_yticks([])
            if i == 0:
                a.set_title(lab[ep], fontsize=7, pad=2)
            if j == 0:
                a.set_ylabel(nm, fontsize=7)
                fs.scalebar(a)
                fs.north_arrow(a, x=0.85, y=0.80, size=0.13)
            fs.panel_label(a, f"{'ab'[i]}{j + 1}")
    X.save(f, 'FigS1_timeline_strip',
           'Image time series, 1924-2026, for Kittur (a1-a9; 1.8 km window) and Old Sangoli (b1-b9; 5.2 km window). Landsat and Sentinel-2 panels are '
           'dry-season (January-March) median composites, natural colour with linear percentile stretch; CORONA panels CLAHE; the 1967 frames do not cover '
           'Sangolli.', kind='supplementary')


def figS2(X):
    """Schematic 3D reconstruction (illustrative only)."""
    C = X.C
    from mpl_toolkits.mplot3d import Axes3D  # noqa
    F = X.F; g = 5.0; cx, cy, half = 477470, 1724470, 850
    xs = np.arange(cx - half, cx + half, g); ys = np.arange(cy + half, cy - half, -g); XX, YY = np.meshgrid(xs, ys)
    with rasterio.open(C.f(C['inputs']['dem'])) as d:
        Z0 = d.read(1).astype(float); c, r = ~d.transform * (XX, YY)
    Z = cv2.GaussianBlur(map_coordinates(Z0, [r - 0.5, c - 0.5], order=3), (0, 0), 2)

    def ras(geom, width):
        m = np.zeros(Z.shape, np.uint8)
        co = geom.exterior.coords if geom.geom_type == 'Polygon' else geom.coords
        p = np.array([[(x - xs[0]) / g, (ys[0] - y) / g] for x, y in co], np.int32)
        cv2.polylines(m, [p], geom.geom_type == 'Polygon', 1, max(1, int(round(width / g))))
        return m.astype(bool)
    H = np.zeros_like(Z)
    H[ras(F.loc['lower_fort'].geometry, 6)] = 6.0
    H[ras(F.loc['outer_east'].geometry, 6)] = 4.2
    for i in ('ring_outer', 'ring_middle', 'ring_core'):
        H[ras(F.loc[i].geometry, 6)] = 4.0
    H[ras(F.loc['moat_nw'].geometry, 10)] = -4.9
    for i in ('pond_nw', 'pond_e'):
        m = np.zeros(Z.shape, np.uint8); p = np.array([[(x - xs[0]) / g, (ys[0] - y) / g] for x, y in F.loc[i].geometry.exterior.coords], np.int32)
        cv2.fillPoly(m, [p], 1); H[m > 0] = -2
    with rasterio.open(X.D / 'corona' / 'corona_1968_kittur.tif') as cr:
        A = cr.read(1).astype(float); cc, rr = ~cr.transform * (XX, YY)
    Tt = map_coordinates(A, [rr - 0.5, cc - 0.5], order=1); Tt = np.clip((Tt - np.percentile(Tt, 1)) / (np.percentile(Tt, 99) - np.percentile(Tt, 1)), 0, 1)
    col = plt.cm.gray(Tt); col[H > 0] = matplotlib_color(OK['orange']); col[H < 0] = matplotlib_color(OK['blue'])
    f = fs.fig('double', 105)
    ax = f.add_axes([-0.12, -0.25, 1.24, 1.5], projection='3d')
    ax.plot_surface(XX - cx, YY - cy, (Z + H - Z.min()) * 2.0, facecolors=col, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    ax.view_init(32, -120); ax.set_box_aspect((1, 1, 0.18), zoom=1.45); ax.set_axis_off()
    X.save(f, 'FigS2_3d_schematic',
           'Schematic three-dimensional view of the lower fort and citadel mound (illustrative only; view from the south-west, vertical exaggeration 2x). '
           'Terrain: Copernicus GLO-30 resampled to 5 m (modern trees and buildings included); drape: CORONA DA224, 31 January 1968. Assumed heights: '
           'lower-fort rampart 6 m, east outer line 4.2 m, each citadel ring 4 m (orange); N/W moat 4.9 m deep (16 ft, Gazetteer 1884) and ponds 2 m (blue). '
           'Gates, bastions and the palace are not modelled.', kind='supplementary')


def matplotlib_color(h):
    from matplotlib.colors import to_rgba
    return to_rgba(h)


def figS3(X):
    C = X.C
    acc = json.load(open(X.R / 'georef_accuracy.json')); fp = pd.read_csv(C.f(C['inputs']['corona_footprints']))
    f = fs.fig('double', 95)
    a = f.add_axes([0.07, 0.25, 0.42, 0.70])
    with rasterio.open(C.f(C['inputs']['dem'])) as d:
        b = d.bounds
    lo, la = geo.utm2ll(np.array([b.left, b.right, b.right, b.left, b.left]), np.array([b.bottom, b.bottom, b.top, b.top, b.bottom]))
    used = {'DS1045-1102DA224': OK['vermillion'], 'DS1045-1102DF224': OK['blue'], 'DS1045-1102DA223': OK['purple'],
            'DS1044-2134DA215': '0.6', 'DS1044-2134DA216': '0.6'}
    for _, r in fp.iterrows():
        xs = [r.lon1, r.lon2, r.lon3, r.lon4, r.lon1]; ys = [r.lat1, r.lat2, r.lat3, r.lat4, r.lat1]
        u = r['id'] in used and used[r['id']] != '0.6'
        a.plot(xs, ys, color=used.get(r['id'], '0.75'), lw=1.0 if u else 0.4, zorder=3 if u else 1, label=r['id'] if u else None)
    a.plot(lo, la, color='k', lw=0.9, label='Study area (DEM extent)')
    for k in ('Kittur fort', 'Belgaum fort', 'Bailhongal', 'Nandagad'):
        la_, lo_ = C['points'][k]; a.plot(lo_, la_, 'o', ms=2.5, color='k'); a.text(lo_ + 0.03, la_ + 0.02, k, fontsize=7)
    a.set_xlim(73.5, 76.2); a.set_ylim(15.2, 16.4); a.set_aspect('equal')
    a.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.1f}°E')); a.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.1f}°N'))
    a.legend(fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2, title='CORONA frames used', title_fontsize=7)
    fs.north_arrow(a, x=0.93, y=0.85); fs.panel_label(a, 'a')
    a.set_title('USGS footprints, 1960s frames near Kittur (grey: other frames)', fontsize=7)
    bx = f.add_axes([0.66, 0.14, 0.32, 0.80])
    NAMES = {'corona_1968_kittur': 'DA224 Kittur', 'corona_1968_nandagad': 'DA224 Nandagad', 'corona_1968_sangolli': 'DF224 Sangolli',
             'corona_1968DA223_sampgaon': 'DA223 Sampgaon', 'corona_1968DA223_bailhongal': 'DA223 Bailhongal',
             'corona_1968DA223_oldsangoli': 'DA223 Old Sangoli', 'corona_1968DA223_tigadi': 'DA223 Tigadi',
             'corona_srirangapatna': 'DA028 Srirangapatna', 'corona_hampi': 'DA077 Hampi'}
    nice = lambda k: NAMES.get(k.replace('_auto_ncc', ''), k)
    rows = [(nice(k), v) for k, v in acc.items() if k.endswith('_auto_ncc') and v.get('rms_m')]
    for i, (k, v) in enumerate(rows):
        bx.barh(i, v['rms_m'], color=OK['skyblue'], height=0.6)
        bx.plot(np.hypot(v['mean_dE'], v['mean_dN']), i, 'o', ms=3, color=OK['vermillion'])
        bx.text(v['rms_m'] + 3, i, f"n = {v['n_kept']}", va='center', fontsize=7)
    bx.set_yticks(range(len(rows))); bx.set_yticklabels([r[0] for r in rows], fontsize=7)
    bx.set_xlabel('Offset to Sentinel-2 (m)'); bx.invert_yaxis(); bx.grid(axis='x', alpha=0.25, lw=0.4)
    bx.legend(handles=[Patch(fc=OK['skyblue'], label='RMS of patch offsets'), Line2D([], [], marker='o', ls='none', color=OK['vermillion'], label='Mean offset (bias)')], fontsize=7, loc='lower right')
    fs.panel_label(bx, 'b', inside=False)
    X.save(f, 'FigS3_corona_coverage_accuracy',
           'CORONA coverage and an automatic positional check. (a) USGS footprints of 1960s CORONA frames around the study area and the three frames used. '
           '(b) Patch normalised cross-correlation of each georeferenced crop against Sentinel-2 (500 m patches, 10 m, NCC > 0.45, 3-MAD filter): RMS and '
           'mean of the accepted offsets. Farmland patches give unstable matches across 60 years, so the RMS includes matching noise as well as georeferencing error.',
           kind='supplementary')


def figS4(X):
    e = ext_centre(X.K[0], X.K[1] + 50, 1500)
    f = fs.fig('double', 72)
    ax = [f.add_axes([0.05 + i * 0.30, 0.12, 0.28, 0.84]) for i in range(3)]
    show_gray(ax[0], X.D / 'corona' / 'corona_1967DA_kittur.tif', e)
    show_gray(ax[1], X.D / 'corona' / 'corona_1967DF_kittur.tif', e)
    z = window(X.D / 'dem' / 'corona1967_dem_kittur.tif', [1], e, 2, nodata=np.nan)[0]
    with rasterio.open(X.C.f(X.C['inputs']['dem'])) as d:
        pass
    im = ax[2].imshow(z, cmap='cividis', vmin=700, vmax=790, extent=e, interpolation='none')
    for i, a in enumerate(ax):
        fs.map_axes(a, e, step_m=500, labels=('bottom',) + (('left',) if i == 0 else ()), axis_titles=(i == 0))
        fs.panel_label(a, 'abc'[i])
        a.text(0.5, 0.985, ['DA217 (aft), 11 Nov 1967', 'DF217 (forward), 11 Nov 1967', 'Stereo height, unsmoothed'][i], transform=a.transAxes, ha='center', va='top',
               fontsize=7, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5), zorder=20)
    cax = f.add_axes([0.94, 0.25, 0.01, 0.5]); cb = f.colorbar(im, cax=cax); cb.ax.tick_params(labelsize=7); cb.set_label('Height (m)', fontsize=7)
    X.save(f, 'FigS4_stereo_pair',
           'The 11 November 1967 stereo pair over Kittur after co-registration to the 1968 crop (SIFT, RANSAC and second-order polynomial). (a) Aft frame '
           'DS1044-2134DA217; (b) forward frame DS1044-2134DF217 (CLAHE); (c) unsmoothed semi-global-matching heights (gaps: failed matches).', kind='supplementary')


def figS5(X):
    C = X.C
    T = json.load(open(X.R / 'osm_tanks_vs_1968.json'))
    with rasterio.open(X.D / 'corona' / 'corona_1968_mosaic15km_10m.tif') as r:
        A = r.read(1); b = r.bounds
    e = (b.left, b.right, b.bottom, b.top)
    f = fs.fig('onehalf', 135)
    a = f.add_axes([0.10, 0.08, 0.85, 0.88])
    a.imshow(np.where(A > 0, fs.clahe(A), np.nan), cmap='gray', extent=e, interpolation='none')
    o = X.osm[(X.osm.category == 'water') & (X.osm.geom_type == 'Polygon')]
    st = {'dark in 1968 (pre-1968 tank)': OK['blue'], 'intermediate': OK['green'], 'no water signature in 1968': OK['vermillion'], 'outside 1968 coverage': '0.6'}
    for t in T:
        g = o[o.osm_id == t['osm_id']]
        if len(g):
            g.plot(ax=a, fc=st[t['status_1968']], ec='k', lw=0.3, alpha=0.8, zorder=5)
    a.plot(*X.fortc.coords[0], '*', ms=7, mfc='white', mec='k', mew=0.4)
    a.legend(handles=[Patch(fc=c, ec='k', lw=0.3, label=f"{k} ({sum(t['status_1968'] == k for t in T)})") for k, c in st.items()], fontsize=7, loc='lower left',
             title='OSM water bodies ≥ 1 ha (2026)', title_fontsize=7)
    fs.map_axes(a, e, step_m=5000)
    X.save(f, 'FigS5_tanks_1968_2026',
           'Tanks within 15 km of Kittur: OpenStreetMap water polygons of at least 1 ha (2026) classified by their tone in the 1968 CORONA mosaic '
           '(DF224 north, DA224 south, 10 m, extrapolated affines; 100-300 m error at the margins; the dark band near 1726 km northing is the film edge of DF224). Tanks dry in January 1968 resemble fields, so "no water '
           'signature" does not prove a tank post-dates 1968. Star: Kittur fort. CORONA: CLAHE. Grid: UTM 43N (km).', kind='supplementary')


FIGS = dict(fig01=fig01, fig02=fig02, fig03=fig03, fig04=fig04, fig05=fig05, fig06=fig06, fig07=fig07, fig08=fig08, fig09=fig09,
            fig10=fig10, figS1=figS1, figS2=figS2, figS3=figS3, figS4=figS4, figS5=figS5, figS6=figS6, previews=previews_site_timelines)


def write_captions(X):
    spec_p = X.out / 'figure_specs.json'
    old = {s['name']: s for s in json.load(open(spec_p))} if spec_p.exists() else {}
    old.update({s['name']: s for s in X.specs})
    json.dump(list(old.values()), open(spec_p, 'w'), indent=1)
    cap_p = X.out / '.captions.json'
    caps = json.load(open(cap_p)) if cap_p.exists() else {}
    caps.update(X.captions); json.dump(caps, open(cap_p, 'w'), indent=1)
    lines = ['# Figure captions', '', 'Files: `<name>.tif` (RGB, LZW, 600 dpi) and `<name>.pdf` (vector, fonts embedded). Generated by `release/code/stages/s08_figures.py`.', '']
    for kind, head in (('main', '## Main figures'), ('supplementary', '## Supplementary figures')):
        lines += [head, '']
        for n, (k, cap) in sorted(caps.items(), key=lambda kv: (kv[0].startswith('FigS'), kv[0])):
            if k != kind:
                continue
            s = old.get(n, {})
            num = n.split('_')[0].replace('Fig0', 'Fig. ').replace('FigS', 'Fig. S').replace('Fig1', 'Fig. 1')
            lines += [f'**{num}.** {cap}', '', f'*File:* `{n}.tif` / `{n}.pdf` ({s.get("width_mm")} x {s.get("height_mm")} mm)', '']
    (X.out / 'figure_captions.md').write_text('\n'.join(lines))


def main(argv=None):
    C = load()
    fs.setup()
    want = [a for a in (argv or []) if a in FIGS] or list(FIGS)
    with Stage(C, 'figures') as st:
        X = Ctx(C)
        for k in want:
            FIGS[k](X)
        write_captions(X)
        st.note(f'{len(X.specs)} figures written to {C.p("figures")}')


if __name__ == '__main__':
    main()
