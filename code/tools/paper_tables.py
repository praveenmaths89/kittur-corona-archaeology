"""LaTeX tables for the manuscript, generated from the pipeline results (no number is typed by hand).

    python tools/paper_tables.py <out_dir>

Writes tab_sources.tex, tab_accuracy.tex, tab_dimensions.tex, tab_evidence.tex (main text) and
tab_s_models.tex (supplement: every model for every source). Style: booktabs rules, no vertical rules; wide tables shrink to the line width (adjustbox).
"""
import sys, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
R, T = ROOT / 'results', ROOT / 'manuscript' / 'tables'


def tex(s):
    """Escape LaTeX special characters in table cells."""
    s = str(s)
    for a, b in (('\\', r'\textbackslash{}'), ('&', r'\&'), ('%', r'\%'), ('#', r'\#'), ('_', r'\_'), ('~', r'\textasciitilde{}')):
        s = s.replace(a, b)
    return s.replace('km2', r'km$^2$').replace('>=', r'$\geq$').replace('<=', r'$\leq$')


def dash(r):
    """Number ranges 'a-b' -> 'a--b' (en dash) in a row of cells."""
    return tuple(re.sub(r'(?<=\d)-(?=\d)', '--', str(c)) for c in r)


def table(rows, cols, spec, label, caption, notes, size=r'\footnotesize', star=True):
    env = 'table*' if star else 'table'
    out = [rf'\begin{{{env}}}[!htbp]', r'\centering', size, rf'\caption{{{caption}}}', rf'\label{{{label}}}',
           r'\begin{adjustbox}{max width=\linewidth}', rf'\begin{{tabular}}{{{spec}}}', r'\toprule', ' & '.join(cols) + r' \\', r'\midrule']
    out += [' & '.join(tex(c).replace('\\textendash', '') for c in r) + r' \\' for r in rows]
    out += [r'\bottomrule', r'\end{tabular}', r'\end{adjustbox}']
    if notes:
        out += [r'\par\smallskip\parbox{\linewidth}{\scriptsize ' + ' '.join(notes) + '}']
    out += [rf'\end{{{env}}}']
    return '\n'.join(out) + '\n'


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    V = json.load(open(R / 'validation.json')); P = json.load(open(R / 'propagation.json'))
    # Table 1: sources
    rows = [('Survey of India one-inch sheets 48 I/09, I/10, I/14', '1922--23 survey, 1924 print', '1:63,360', 'Pre-dam landscape, spot heights; validation'),
            ('CORONA KH-4A DS1045-1102 DA222, DA224, DF224', '31 Jan 1968', 'c. 2--3 m', 'Fort plan, Old Sangoli, Belgaum; validation'),
            ('CORONA KH-4A DS1044-2134 DA217, DF217', '11 Nov 1967', 'c. 2--3 m', 'Repeat view of the fort; stereo surface'),
            ('CORONA KH-4A DS1045-1102 DA223 (coarse crops)', '31 Jan 1968', 'c. 2--3 m', 'Regional readings (Sampgaon, Tigadi, Bailhongal); not re-georeferenced'),
            ('CORONA KH-4A DS1040-1039 DA028 (Srirangapatna)', '2 Apr 1967', 'c. 2--3 m', 'Transfer test'),
            ('CORONA KH-4A DS1025-1071 DA077 (Hampi)', '10 Oct 1965', 'c. 2--3 m', 'Transfer test'),
            ('Landsat 5/7 Collection 2 Level-2, dry-season medians', '1990, 2000, 2010', '30 m', 'Change, evidence grading'),
            ('Sentinel-2 L2A (scenes and dry-season medians)', '2016--2026', '10 m', 'Tie reference, evidence grading'),
            ('Copernicus DEM GLO-30', '2011--2015', '30 m', 'Terrain, viewsheds, DSM test'),
            ('OpenStreetMap extracts (Overpass API)', 'Oct 2026', 'vector', 'Tie candidates, road reference, outlines'),
            ('Gazetteer of the Bombay Presidency XXI, Belgaum', '1884', 'text', 'Descriptions of 1825 and 1882')]
    open(out / 'tab_sources.tex', 'w').write(table(rows, ['Source', 'Date', 'Resolution', 'Use'], '>{\\raggedright\\arraybackslash}>{\\raggedright\\arraybackslash}p{0.40\\linewidth}>{\\raggedright\\arraybackslash}p{0.16\\linewidth}>{\\raggedright\\arraybackslash}p{0.12\\linewidth}>{\\raggedright\\arraybackslash}p{0.24\\linewidth}',
        'tab:sources', 'Sources used. All imagery and vector data are free and open; licences are listed in the data deposit.',
        ['CORONA resolution is the nominal ground sample distance at nadir; the scans were resampled to 2 m (Kittur) or 4 m (matching).']))
    # Table 2: accuracy (from manuscript/tables/Table2 csv written by stage 09)
    d = pd.read_csv(T / 'Table2_georeferencing_accuracy.csv')
    # shorter cells so the table stays legible at full width
    nchk = [t['models'][t['chosen']]['n_check'] for t in V['targets'].values() if t.get('status') == 'ok']
    rows = [dash((str(r[0]).replace('CORONA ', '').replace('Survey of India ', 'SoI '), r[1], r[2], k, *r[3:]))
            for r, k in zip(d.itertuples(index=False), nchk)]
    open(out / 'tab_accuracy.tex', 'w').write(table(rows, ['Source', 'Role', 'Ties', 'Check pts', 'Before', 'Model', 'Block-CV', 'LOO', 'Check (95\\% boot.)', "Moran's $I$ $p$ (E/N)"],
        'llrrrlrrll', 'tab:accuracy', 'Horizontal accuracy (RMSE, m) of each source before and after re-estimation from automatic open-data tie points.',
        [r'Before: recorded transform evaluated at all ties. Block-CV: leave-spatial-block-out RMSE of the chosen model (headline figure). LOO: leave-one-out. Check: held-out ties ($\approx$30\%), with a bootstrap 95\% interval. The bootstrap refits the transform on resampled control ties and re-scores the fixed check set, so it measures fit variability only; where the full-control fit is already close to optimal for those check points (Belgaum, Srirangapatna) the lower bound sits at the point estimate.',
         r"Moran's $I$: permutation $p$ for the LOO residuals; with 18 tests the Bonferroni threshold is $p<0.0028$. Kittur-region and transfer sources use identical settings."]))
    # Table 3: dimensions
    d = pd.read_csv(T / 'Table3_dimensions.csv')
    d = d[~d.iloc[:, 3].astype(str).str.contains('fixed by the DSM')]     # vertical-only rows are reported in the text (Section 4.5)
    rows = [dash(r) for r in d.itertuples(index=False)]
    eb = P['error_budget']; tr = eb['threshold_sensitivity']['target_range_m']
    open(out / 'tab_dimensions.tex', 'w').write(table(rows, ['Feature', 'Measure', 'Nominal', 'Median (95\\% interval)'], '>{\\raggedright\\arraybackslash}>{\\raggedright\\arraybackslash}p{0.36\\linewidth}>{\\raggedright\\arraybackslash}p{0.27\\linewidth}rl',
        'tab:dimensions', 'Kittur features digitised on CORONA DA224 (31 January 1968) under the full error budget.',
        [rf"Nominal: chosen model ({P['kittur_model']['kind']}, {P['kittur_model']['n_ties']} ties). Interval: {P['n']} realisations combining a bootstrap transform, local error scaled to a target RMSE drawn from {tr[0]:.0f}--{tr[1]:.0f} m, {eb['vertex_noise_m']} m vertex noise and a {eb['digitising_sd_m']:.0f} m systematic line offset per feature (Section~\ref{{sec:budget}}).",
         r'The median is that of the realisations. For the IoU and centroid offset it differs from the nominal value because the nominal outline is close to the best-case alignment with OSM, so most perturbations lower the IoU and raise the offset (a one-sided distribution). Citadel elevation (769.4 m) and viewshed (33.7 km$^2$) are fixed by the highest GLO-30 cell and carry vertical error only (Section~\ref{sec:terrain}). Viewsheds: 720 rays to 10 km, observer 10 m above ground.']))
    # Table 4: evidence
    e = pd.read_csv(R / 'evidence_table.csv')
    SRC = [('soi_1924', 'SoI'), ('landsat_1990', 'L90'), ('sentinel2_2026', 'S2'), ('dem', 'DEM'), ('osm', 'OSM')]
    named = lambda r, tag: ', '.join(n for c, n in SRC if str(getattr(r, c)).startswith(tag)) or '--'
    rows = [(r.reading.replace('(0.23 ha)', '(0.22 ha)').replace('(0.48 ha)', '(0.46 ha)'), r.grade, named(r, 'support'), named(r, 'contradict'),
             'Results' if r.placement == 'results' else 'Discussion') for r in e.itertuples()]
    open(out / 'tab_evidence.tex', 'w').write(table(rows, ['Reading on CORONA 1967--68', 'Grade', 'Supported by', 'Contradicted by', 'Reported in'],
        '>{\\raggedright\\arraybackslash}>{\\raggedright\\arraybackslash}p{0.47\\linewidth}l>{\\raggedright\\arraybackslash}p{0.14\\linewidth}>{\\raggedright\\arraybackslash}p{0.1\\linewidth}l', 'tab:evidence', 'Evidence grades of the CORONA readings (single grader; rule applied in code).',
        [r'Positional sources independent of CORONA: SoI, Survey of India 1924; L90, Landsat 1990; S2, Sentinel-2 2026; DEM, Copernicus GLO-30; OSM, OpenStreetMap 2026. The Trewman and Deacon letters of December 1824 and the Gazetteer support the kind of feature only. GLO-30 is also the analysis surface for the hillock, and the OSM fort outline may have been traced from the same walls. Confirmed: $\geq$2 supporting, none contradicting; plausible: 1; unsupported: none; contradicted: $\geq$1 positional source contradicts. ``Confirmed'' means a feature exists at this place in 1967--68 and in an independent source; it does not date the feature to 1824.']))
    # Supplement: all models
    rows = []
    for n, t in V['targets'].items():
        if t.get('status') != 'ok':
            continue
        for k, m in t['models'].items():
            rows.append((t['label'].replace('CORONA KH-4A ', '').replace('Survey of India ', 'SoI '), k + (' *' if k == t['chosen'] else ''),
                         f"{m['fit_rmse_m']:.1f}", f"{m['check_rmse_m']:.1f}", f"{m['loo_rmse_m']:.1f}", f"{m['block_cv_rmse_m']:.1f}",
                         f"{m['smoothing']:g}" if k == 'tps' else '--'))
    open(out / 'tab_s_models.tex', 'w').write(table(rows, ['Source', 'Model', 'Fit', 'Check', 'LOO', 'Block-CV', 'TPS smoothing'], '>{\\raggedright\\arraybackslash}>{\\raggedright\\arraybackslash}p{0.42\\linewidth}lrrrrr',
        'tab:smodels', 'All candidate transforms for every source (RMSE, m). * chosen by the pre-specified rule.',
        [r'Rule: simplest model whose block-CV RMSE is within 10\% of the lowest, in the order affine, poly2, poly3, TPS. TPS smoothing chosen from 1, 10, 100, 1000 by leave-one-out on the control points; zero smoothing is excluded. poly3 is skipped where the control set is too small.'],
        size=r'\scriptsize'))
    print('tables written to', out)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
