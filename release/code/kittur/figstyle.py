"""Journal figure conventions (Elsevier artwork guidelines).

* Widths: single column 90 mm, 1.5 column 140 mm, double column 190 mm.
* Font: Arial 7-8 pt (panel labels 9 pt bold); fonts embedded (TrueType, Type 42) in PDF.
* Output: TIFF (LZW, 600 dpi for maps/images) + vector PDF of the same figure.
* Colour: Okabe-Ito qualitative palette; cividis/viridis sequential maps (colour-vision-deficiency safe).
* Every map panel: UTM 43N km grid ticks, scale bar, north arrow, panel label (a, b, c ...).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, Polygon as MplPolygon
from matplotlib.ticker import FuncFormatter, MultipleLocator
from PIL import Image

MM = 1 / 25.4
WIDTH = {'single': 90, 'onehalf': 140, 'double': 190}
OKABE = dict(orange='#E69F00', skyblue='#56B4E9', green='#009E73', yellow='#F0E442',
             blue='#0072B2', vermillion='#D55E00', purple='#CC79A7', black='#000000', grey='#999999')


def setup():
    names = {f.name for f in font_manager.fontManager.ttflist}
    family = 'Arial' if 'Arial' in names else ('Liberation Sans' if 'Liberation Sans' in names else 'DejaVu Sans')
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': [family, 'Liberation Sans', 'DejaVu Sans'],
        'font.size': 7, 'axes.titlesize': 7, 'axes.labelsize': 7, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
        'legend.fontsize': 7, 'legend.title_fontsize': 7, 'axes.linewidth': 0.5, 'xtick.major.width': 0.5,
        'ytick.major.width': 0.5, 'xtick.major.size': 2, 'ytick.major.size': 2, 'lines.linewidth': 0.9,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'savefig.dpi': 600, 'figure.dpi': 150,
        'axes.titlepad': 3, 'legend.frameon': True, 'legend.framealpha': 0.85, 'legend.edgecolor': '0.6',
        'legend.borderpad': 0.3, 'legend.handlelength': 1.6, 'image.interpolation': 'none',
        'axes.prop_cycle': matplotlib.cycler(color=[OKABE[k] for k in ('blue', 'vermillion', 'green', 'orange', 'purple', 'skyblue', 'yellow', 'black')]),
    })
    return family


def fig(width='double', height_mm=100):
    w = WIDTH[width] if isinstance(width, str) else width
    return plt.figure(figsize=(w * MM, height_mm * MM))


def panel_label(ax, s, x=0.0, y=1.0, inside=True, color='k', bg='white'):
    """Bold lowercase panel label at the top-left corner."""
    if inside:
        ax.text(0.02, 0.98, s, transform=ax.transAxes, ha='left', va='top', fontsize=9, fontweight='bold', color=color,
                bbox=dict(boxstyle='square,pad=0.15', fc=bg, ec='none', alpha=0.85) if bg else None, zorder=20)
    else:
        ax.text(-0.02, 1.02, s, transform=ax.transAxes, ha='right', va='bottom', fontsize=9, fontweight='bold', zorder=20)


def km_grid(ax, step_m=1000, labels=('bottom', 'left'), fmt=None, show_axis_titles=True):
    """UTM 43N tick labels in km on a map axis whose data units are metres."""
    fmt = fmt or ('{:.0f}' if step_m % 1000 == 0 else '{:.1f}')
    ax.xaxis.set_major_locator(MultipleLocator(step_m))
    ax.yaxis.set_major_locator(MultipleLocator(step_m))
    f = FuncFormatter(lambda v, _: fmt.format(v / 1000))
    ax.xaxis.set_major_formatter(f)
    ax.yaxis.set_major_formatter(f)
    ax.tick_params(direction='out', length=2, pad=1.5, labelsize=7,
                   labelbottom='bottom' in labels, labelleft='left' in labels, labeltop=False, labelright=False)
    for t in ax.get_yticklabels():
        t.set_rotation(90); t.set_va('center')
    if show_axis_titles:
        if 'bottom' in labels:
            ax.set_xlabel('Easting (km, UTM 43N)', labelpad=1, fontsize=7)
        if 'left' in labels:
            ax.set_ylabel('Northing (km)', labelpad=1, fontsize=7)


def nice_length(span):
    for v in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000):
        if v >= span * 0.22:
            return v
    return 50000


def scalebar(ax, length=None, loc='lower right', color='k', bg='white', height_frac=0.012, pad=0.04):
    """Alternating black/white scale bar in map units (metres)."""
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    W, H = x1 - x0, y1 - y0
    L = length or nice_length(W)
    h = H * height_frac
    if 'right' in loc:
        xs = x1 - W * pad - L
    else:
        xs = x0 + W * pad
    ys = y0 + H * (pad + 0.02)
    if bg:
        ax.add_patch(Rectangle((xs - W * 0.015, ys - H * 0.015), L + W * 0.03, h + H * 0.075, fc=bg, ec='none', alpha=0.8, zorder=18))
    n = 2
    for i in range(n):
        ax.add_patch(Rectangle((xs + i * L / n, ys), L / n, h, fc=color if i % 2 == 0 else 'white', ec=color, lw=0.4, zorder=19))
    lab = f'{L / 1000:g} km' if L >= 1000 else f'{L:g} m'
    ax.text(xs + L / 2, ys + h + H * 0.008, lab, ha='center', va='bottom', fontsize=7, color=color, zorder=19)
    for xx, tt in ((xs, '0'),):
        pass


def north_arrow(ax, x=0.93, y=0.86, size=0.07, color='k', bg='white'):
    """Simple north arrow (grid north; UTM grid convergence at 74.8E, 15.6N is < 0.1 deg)."""
    tr = ax.transAxes
    h = size
    w = h * 0.45 * (ax.bbox.height / ax.bbox.width)
    if bg:
        ax.add_patch(Rectangle((x - w * 1.1, y - h * 0.62), 2.2 * w, h * 1.6 + 0.045, transform=tr, fc=bg, ec='none', alpha=0.8, zorder=18))
    ax.add_patch(MplPolygon([[x, y + h / 2], [x - w / 2, y - h / 2], [x, y - h / 4]], closed=True, transform=tr, fc=color, ec=color, lw=0.4, zorder=19))
    ax.add_patch(MplPolygon([[x, y + h / 2], [x + w / 2, y - h / 2], [x, y - h / 4]], closed=True, transform=tr, fc='white', ec=color, lw=0.4, zorder=19))
    ax.text(x, y + h / 2 + 0.005, 'N', transform=tr, ha='center', va='bottom', fontsize=7, fontweight='bold', color=color, zorder=19)


def map_axes(ax, ext, step_m=1000, labels=('bottom', 'left'), sb=True, na=True, sb_loc='lower right', axis_titles=True):
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect('equal')
    km_grid(ax, step_m, labels, show_axis_titles=axis_titles)
    if sb:
        scalebar(ax, loc=sb_loc)
    if na:
        north_arrow(ax)


def save(f, out_dir: Path, name: str, dpi=600, close=True):
    """Save TIFF (LZW, RGB, `dpi`) + vector PDF; returns list of paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f'{name}.pdf'
    png = out_dir / f'.{name}_tmp.png'
    tif = out_dir / f'{name}.tif'
    f.savefig(pdf, dpi=dpi)                      # raster layers embedded at `dpi`, text/lines as vectors
    f.savefig(png, dpi=dpi)
    im = Image.open(png).convert('RGB')
    im.save(tif, compression='tiff_lzw', dpi=(dpi, dpi))
    png.unlink()
    w_mm, h_mm = f.get_size_inches() * 25.4
    import matplotlib.text as mtext
    sizes = [t.get_fontsize() for t in f.findobj(mtext.Text) if t.get_visible() and t.get_text().strip()]
    fams = sorted({t.get_fontname() for t in f.findobj(mtext.Text) if t.get_visible() and t.get_text().strip()})
    if close:
        plt.close(f)
    return dict(name=name, tif=str(tif), pdf=str(pdf), width_mm=round(w_mm, 1), height_mm=round(h_mm, 1),
                px=im.size, dpi=dpi, min_font_pt=min(sizes) if sizes else None, max_font_pt=max(sizes) if sizes else None, fonts=fams)


def clahe(img, clip=2.0, tiles=8):
    import cv2
    a = np.nan_to_num(img).astype(np.float32)
    v = a[a > 0]
    if v.size == 0:
        return a.astype(np.uint8)
    a8 = np.clip(a, 0, 255).astype(np.uint8) if a.max() <= 255 else np.clip(a / np.percentile(v, 99.5) * 255, 0, 255).astype(np.uint8)
    return cv2.createCLAHE(clip, (tiles, tiles)).apply(a8)


def rgb_stretch(d, lo=1, hi=99, gamma=1.0):
    """Percentile stretch of a (3, h, w) or (h, w, 3) array to 0-1 (linear unless gamma != 1)."""
    if d.shape[0] == 3:
        d = np.moveaxis(d, 0, -1)
    d = np.nan_to_num(d.astype(np.float32))
    out = np.zeros_like(d)
    for k in range(3):
        v = d[..., k][d[..., k] > 0]
        if v.size == 0:
            continue
        a, b = np.percentile(v, [lo, hi])
        out[..., k] = np.clip((d[..., k] - a) / (b - a + 1e-9), 0, 1)
    return out ** gamma if gamma != 1 else out
