"""Figures for the JAS: Reports manuscript (v3), drawn from the pipeline results only.

    python tools/paper_figures.py <out_dir>

Reads results/validation.json, results/validation_sensitivity.csv, results/propagation.json,
results/evidence_table.csv and the stage-14 panels (previews/evidence_*.png), and writes Fig2-Fig6 and
FigS2 as vector PDF plus 600 dpi PNG. Fig. 1 (study area) and Fig. S1 (residual vectors) come from stages 08 and 12.
Style: sans-serif 7 pt, Okabe-Ito colours (colour-blind safe), widths 90 mm (single) or 190 mm (double column).
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / 'results'
MM = 1 / 25.4
OI = dict(orange='#E69F00', sky='#56B4E9', green='#009E73', yellow='#F0E442', blue='#0072B2', red='#D55E00', purple='#CC79A7', grey='#666666')
plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 7, 'axes.linewidth': 0.6, 'xtick.major.width': 0.6,
                     'ytick.major.width': 0.6, 'pdf.fonttype': 42, 'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, out, name):
    for ext in ('pdf', 'png'):
        fig.savefig(out / f'{name}.{ext}', dpi=600, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


def short(lab):
    return (lab.replace('CORONA KH-4A ', '').replace('Survey of India ', 'SoI ').replace('DS1045-1102', '')
            .replace('DS1040-1039', '').replace('DS1025-1071', '').replace(' (31 Jan 1968)', ' 1968')
            .replace(' (2 Apr 1967)', ' 1967').replace(' (10 Oct 1965)', ' 1965'))


def fig2_workflow(out):
    """Fig. 2 is drawn by tools/fig_workflow_sites.py (four sites; every number read from config/results/git tag)."""
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).with_name('fig_workflow_sites.py')), str(out / 'Fig2_workflow')], check=True)


def fig3_accuracy(out):
    """Before/after RMSE per source, with the headline block-CV and the check interval."""
    V = json.load(open(R / 'validation.json'))['targets']
    rows = [(n, t) for n, t in V.items() if t.get('status') == 'ok']
    fig, ax = plt.subplots(figsize=(140 * MM, 72 * MM))
    for i, (n, t) in enumerate(rows):
        m = t['models'][t['chosen']]; y = len(rows) - 1 - i
        tr = n.endswith(('srirangapatna', 'hampi'))
        ax.plot([m['block_cv_rmse_m'], t['before']['rmse_all_m']], [y, y], color='#BBBBBB', lw=0.8, zorder=1)
        ax.scatter(t['before']['rmse_all_m'], y, s=16, color=OI['red'], zorder=3, label='recorded transform' if i == 0 else None)
        ax.scatter(m['block_cv_rmse_m'], y, s=18, color=OI['blue'], marker='D', zorder=3, label='chosen model, block-CV' if i == 0 else None)
        ax.scatter(m['loo_rmse_m'], y, s=14, facecolor='white', edgecolor=OI['blue'], zorder=3, label='chosen model, LOO' if i == 0 else None)
        b = m['check_rmse_boot95']
        ax.plot(b, [y - 0.22, y - 0.22], color=OI['green'], lw=1.4, solid_capstyle='butt', label='check RMSE, bootstrap 95%' if i == 0 else None)
        ax.text(1.05, y, f"{short(t['label'])}  ({t['chosen']}, n={t['n_ties']})" + ('  *' if tr else ''), va='center', ha='right',
                fontsize=6.2, transform=ax.get_yaxis_transform(), color=OI['purple'] if tr else 'k')
    ax.set_xscale('log'); ax.set_xlim(4, 900); ax.set_yticks([]); ax.spines['left'].set_visible(False)
    ax.set_xticks([5, 10, 20, 50, 100, 200, 500]); ax.set_xticklabels(['5', '10', '20', '50', '100', '200', '500'])
    ax.set_xlabel('Horizontal RMSE (m, log scale)')
    ax.legend(loc='upper left', bbox_to_anchor=(1.0 + 0.02, 1.0), frameon=False, fontsize=6.2)
    ax.text(1.05, -1.25, '* transfer region, same settings', ha='right', fontsize=6, color=OI['purple'], transform=ax.get_yaxis_transform())
    plt.subplots_adjust(right=0.62)
    # put labels to the right of the axis: shift by moving the axis left
    pos = ax.get_position(); ax.set_position([0.06, pos.y0, 0.45, pos.height])
    for t_ in ax.texts:
        t_.set_x(1.02); t_.set_ha('left')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=6.2)
    save(fig, out, 'Fig3_accuracy')


def panels(png, n, labels, scale_m, res_m, out, name, width_mm=190):
    """Split a stage-14 panel strip into n images, label them and add a scale bar."""
    im = plt.imread(png); w = im.shape[1] // n
    fig, axs = plt.subplots(1, n, figsize=(width_mm * MM, width_mm / n * MM * 1.08))
    for k, ax in enumerate(axs):
        sub = im[4:-4, k * w + 4:(k + 1) * w - 4]
        ax.imshow(sub); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(True); s.set_linewidth(0.5)
        ax.set_title(labels[k], fontsize=6.5, loc='left', pad=2)
        px = scale_m / res_m; x0 = sub.shape[1] * 0.06; y0 = sub.shape[0] * 0.93
        ax.plot([x0, x0 + px], [y0, y0], color='white', lw=3.2, solid_capstyle='butt')
        ax.plot([x0, x0 + px], [y0, y0], color='black', lw=1.6, solid_capstyle='butt')
        ax.text(x0 + px / 2, y0 - sub.shape[0] * 0.035, f'{scale_m} m', ha='center', fontsize=6, color='black',
                bbox=dict(fc='white', ec='none', pad=0.6, alpha=0.8))
        ax.text(0.93, 0.90, 'N\n\u2191', transform=ax.transAxes, ha='center', va='center', fontsize=6, linespacing=0.9,
                bbox=dict(fc='white', ec='none', pad=0.8, alpha=0.85))
    plt.subplots_adjust(wspace=0.04, left=0.005, right=0.995, top=0.9, bottom=0.01)
    save(fig, out, name)


def fig4_kittur(out):
    """Fig. 4 (round-2 layout): large CORONA 1968 panel with the digitised features, a zoom on the hillock, and the
    1924 / 1990 / 2026 panels (from the stage-14 evidence strip) below. Panel a and b are drawn from the
    re-georeferenced crop corona_1968_kittur_v2.tif at its native 2 m, so the lines stay legible in print."""
    import rasterio, geopandas as gpd
    from matplotlib.patches import Rectangle
    r = rasterio.open(ROOT / 'derived' / 'corona' / 'corona_1968_kittur_v2.tif'); A = r.read(1).astype(float); b0 = r.bounds
    F = gpd.read_file(ROOT / 'derived' / 'vectors' / 'corona1968_features_v2.gpkg')
    fort = F[F.id == 'lower_fort'].geometry.iloc[0]; core = F[F.id == 'ring_outer'].geometry.iloc[0]
    cx, cy = (fort.centroid.x + core.centroid.x) / 2, (fort.centroid.y + core.centroid.y) / 2
    v = A[A > 0]; lo, hi = np.percentile(v, 1), np.percentile(v, 99)
    ext = (b0.left, b0.right, b0.bottom, b0.top)
    fig = plt.figure(figsize=(190 * MM, 190 * MM))
    gs = fig.add_gridspec(2, 3, height_ratios=[2, 1], hspace=0.08, wspace=0.04)
    a = fig.add_subplot(gs[0, :2]); z = fig.add_subplot(gs[0, 2])
    def draw(ax, half, title, scale):
        ax.imshow(A, cmap='gray', vmin=lo, vmax=hi, extent=ext, interpolation='nearest')
        F.plot(ax=ax, facecolor='none', edgecolor='#FFD700', lw=0.9)
        ax.set_xlim(cx - half, cx + half); ax.set_ylim(cy - half, cy + half); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(''); ax.set_ylabel('')
        ax.set_title(title, fontsize=8, loc='left', pad=2)
        x0 = cx - half * 0.9; y0 = cy - half * 0.88
        ax.plot([x0, x0 + scale], [y0, y0], color='white', lw=4, solid_capstyle='butt'); ax.plot([x0, x0 + scale], [y0, y0], color='black', lw=2, solid_capstyle='butt')
        ax.text(x0 + scale / 2, y0 + half * 0.05, f'{scale} m', ha='center', fontsize=7, bbox=dict(fc='white', ec='none', pad=0.8, alpha=0.85))
        ax.text(0.94, 0.92, 'N\n\u2191', transform=ax.transAxes, ha='center', va='center', fontsize=8, linespacing=0.9, bbox=dict(fc='white', ec='none', pad=1, alpha=0.85))
    draw(a, 900, 'a  CORONA DA224, 31 Jan 1968, re-georeferenced, with digitised features', 500)
    zc = core.centroid; zh = 230
    a.add_patch(Rectangle((zc.x - zh, zc.y - zh), 2 * zh, 2 * zh, fill=False, ec='cyan', lw=1))
    cx, cy = zc.x, zc.y; draw(z, zh, 'b  Hillock (zoom of box in a)', 100)
    im = plt.imread(ROOT / 'previews' / 'evidence_kittur.png'); w = im.shape[1] // 4
    for k, (j, lab) in enumerate([(0, 'c  SoI 48 I/14, surveyed 1922-23'), (2, 'd  Landsat, 1990'), (3, 'e  Sentinel-2, 2026')]):
        ax = fig.add_subplot(gs[1, k]); sub = im[4:-4, j * w + 4:(j + 1) * w - 4]
        ax.imshow(sub); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(lab, fontsize=8, loc='left', pad=2)
        px = 500 / 2; x0 = sub.shape[1] * 0.06; y0 = sub.shape[0] * 0.93
        ax.plot([x0, x0 + px], [y0, y0], color='white', lw=4, solid_capstyle='butt'); ax.plot([x0, x0 + px], [y0, y0], color='black', lw=2, solid_capstyle='butt')
        ax.text(x0 + px / 2, y0 - sub.shape[0] * 0.05, '500 m', ha='center', fontsize=7, bbox=dict(fc='white', ec='none', pad=0.8, alpha=0.85))
        ax.text(0.92, 0.9, 'N\n\u2191', transform=ax.transAxes, ha='center', va='center', fontsize=8, linespacing=0.9, bbox=dict(fc='white', ec='none', pad=1, alpha=0.85))
    plt.subplots_adjust(left=0.005, right=0.995, top=0.97, bottom=0.005)
    save(fig, out, 'Fig4_kittur_epochs')


def fig5_budget(out):
    """Fig. 5 (round-2): (a) 95% intervals with nominal AND Monte Carlo median, (b) component breakdown,
    (c) DSM scenarios. Panels stacked at full width so labels print at 7-8 pt."""
    P = json.load(open(R / 'propagation.json')); M = P['metrics']; CB = P['error_budget']['components_halfwidth_95']
    fig = plt.figure(figsize=(190 * MM, 200 * MM)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.45, wspace=0.55)
    a = fig.add_subplot(gs[0, :]); c = fig.add_subplot(gs[1, 0]); b = fig.add_subplot(gs[1, 1])
    items = [('area_ha_lower_fort', 'Lower-fort area', 'ha', 2), ('area_ha_ring_outer', 'Citadel outer ring', 'ha', 2),
             ('area_ha_ring_middle', 'Citadel middle ring', 'ha', 2), ('area_ha_ring_core', 'Citadel core', 'ha', 2),
             ('area_ha_pond_e', 'East pond', 'ha', 2),
             ('fort_citadel_m', 'Fort to citadel distance', 'm', 0), ('citadel_bearing_deg', 'Fort to citadel bearing', 'deg', 0),
             ('iou_fort_osm', 'IoU with OSM fort outline', '', 2), ('fort_centroid_to_osm_m', 'Centroid offset from OSM', 'm', 0)]
    for i, (k, lab, u, nd) in enumerate(items):
        d = M[k]; y = len(items) - 1 - i; nom = d['v2']; pc = lambda v: 100 * (v / nom - 1)
        a.plot([pc(d['lo95']), pc(d['hi95'])], [y, y], color=OI['blue'], lw=3, solid_capstyle='butt')
        a.scatter(0, y, color='k', s=22, zorder=3, label='nominal (chosen model)' if i == 0 else None)
        a.scatter(pc(d['median']), y, color='white', edgecolor='k', marker='D', s=20, zorder=4, label='Monte Carlo median' if i == 0 else None)
        a.text(1.01, y, f"{nom:.{nd}f} {u}; median {d['median']:.{nd}f} ({d['lo95']:.{nd}f}-{d['hi95']:.{nd}f})", va='center', fontsize=7, transform=a.get_yaxis_transform())
    a.axvline(0, color='#BBBBBB', lw=0.6, zorder=0)
    a.set_yticks(range(len(items))); a.set_yticklabels([l for _, l, _, _ in items][::-1], fontsize=8); a.set_xlim(-100, 290)
    a.tick_params(labelsize=7.5); a.set_xlabel('Deviation from nominal (%); bar = 95% interval', fontsize=8)
    a.legend(frameon=False, fontsize=7.5, loc='upper right')
    a.set_title(f"a  Full positional error budget ({P['n']} realisations)", loc='left', fontsize=9)
    a.set_position([0.2, 0.6, 0.47, 0.36])
    # b: component breakdown, 95% half-width as % of nominal
    keys = [('fort_area_ha', 'area_ha_lower_fort', 'Lower fort'), ('ring_outer_ha', 'area_ha_ring_outer', 'Outer ring'),
            ('area_ha_ring_core', 'area_ha_ring_core', 'Core'), ('area_ha_pond_e', 'area_ha_pond_e', 'East pond'),
            ('fort_citadel_m', 'fort_citadel_m', 'Distance')]
    comps = [k for k in CB if k != 'full budget']; cols = [OI['blue'], OI['orange'], OI['green'], OI['grey']]
    short = {comps[0]: 'transform', comps[1]: 'tie threshold', comps[2]: 'digitising', comps[3]: 'vertex noise'}
    x = np.arange(len(keys)); w = 0.2
    for j, cp in enumerate(comps):
        c.bar(x + (j - 1.5) * w, [100 * CB[cp].get(k1, np.nan) / M[k2]['v2'] for k1, k2, _ in keys], w, color=cols[j], label=short[cp])
    c.scatter(x, [100 * CB['full budget'][k1] / M[k2]['v2'] for k1, k2, _ in keys], color='k', marker='_', s=200, zorder=4, label='full budget')
    c.set_xticks(x); c.set_xticklabels([l for *_, l in keys], fontsize=7.5, rotation=20); c.set_ylabel('95% half-width (% of nominal)', fontsize=8)
    c.tick_params(labelsize=7.5); c.legend(frameon=False, fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.22), ncol=3); c.set_yscale('log')
    c.set_title('b  Contribution of each component', loc='left', fontsize=9)
    S = P['vertical_scenarios']; sds = sorted({v['sd_m'] for v in S.values()}); x = np.arange(len(sds)); w = 0.2
    get = lambda sd, cb, key: 100 * next(v[key] for v in S.values() if v['sd_m'] == sd and (v['canopy_bias_max_m'] > 0) == cb)
    for j, (key, cb, col, hatch, lab) in enumerate([
            ('frac_no_higher_cell_1500m', False, OI['sky'], None, 'no higher cell within 1.5 km'),
            ('frac_no_higher_cell_1500m', True, OI['sky'], '////', 'same, with canopy bias'),
            ('frac_excess_le_3m_1500m', False, OI['orange'], None, 'nothing > 3 m higher'),
            ('frac_excess_le_3m_1500m', True, OI['orange'], '////', 'same, with canopy bias')]):
        b.bar(x + (j - 1.5) * w, [get(sd, cb, key) for sd in sds], w, color=col, hatch=hatch, edgecolor='white', lw=0.3, label=lab)
    b.set_xticks(x); b.set_xticklabels([f'{sd:g} m' for sd in sds]); b.set_xlabel('GLO-30 vertical error SD', fontsize=8)
    b.set_ylabel('Realisations in which the claim holds (%)', fontsize=8); b.set_ylim(0, 100); b.tick_params(labelsize=7.5)
    b.legend(frameon=False, fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=2)
    b.set_title("c  'Nowhere commanded' under DSM error", loc='left', fontsize=9)
    save(fig, out, 'Fig5_error_budget')


def figS2_sensitivity(out):
    d = pd.read_csv(R / 'validation_sensitivity.csv')
    fig, ax = plt.subplots(figsize=(120 * MM, 60 * MM))
    plain = {'baseline': 'baseline', 'min_ncc=0.15': 'NCC threshold 0.15', 'min_ncc=0.25': 'NCC threshold 0.25',
             'min_ncc=0.3': 'NCC threshold 0.30', 'agree_m=10': 'size agreement 10 m', 'agree_m=20': 'size agreement 20 m',
             'min_sep_m=400': 'spacing 400 m', 'min_sep_m=500': 'spacing 500 m', "exclude_kinds=['tank', 'village']": 'junctions only'}
    lab = d.setting.map(plain).fillna(d.setting)
    x = np.arange(len(d))
    ax.bar(x - 0.2, d.loo_rmse_m, 0.4, color=OI['sky'], label='LOO RMSE')
    ax.bar(x + 0.2, d.block_cv_rmse_m, 0.4, color=OI['blue'], label='block-CV RMSE')
    for i, n in enumerate(d.n_ties):
        ax.text(i, -4.5, f'n={n}', ha='center', fontsize=5.6, color='k', clip_on=False)
    ax.set_xticks(x); ax.set_xticklabels(lab, rotation=35, ha='right', fontsize=6.5); ax.tick_params(axis='x', pad=9); ax.set_ylabel('RMSE (m)')
    ax.text(len(d) - 1, 47, 'missing bar: too few ties for that test', ha='right', fontsize=5.6, color=OI['grey'])
    ax.legend(frameon=False, fontsize=6); ax.set_title('Kittur DA224: sensitivity to tie-acceptance settings (one changed at a time)', loc='left', fontsize=7)
    save(fig, out, 'FigS2_sensitivity')


if __name__ == '__main__':
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    fig2_workflow(out); fig3_accuracy(out); fig5_budget(out); figS2_sensitivity(out)
    fig4_kittur(out)
    panels(ROOT / 'previews' / 'evidence_old_sangoli.png', 3,
           ['a  SoI 48 I/14, 1922-23', 'b  CORONA DF224, Jan 1968', 'c  Sentinel-2, 2026'], 1000, 4, out, 'Fig6_old_sangoli')
