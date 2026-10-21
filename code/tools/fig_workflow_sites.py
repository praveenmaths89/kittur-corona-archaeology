"""Fig. 2: workflow across the four Kittur-region CORONA sites, with each site's result.

    python tools/fig_workflow_sites.py [out_stem] [--repo DIR] [--tag TAG]

Every number and identifier in the figure is read at run time from config.yaml, results/validation.json,
results/propagation.json, results/belgaum_fort.json, results/evidence_table.csv and the git tag of the code
(`git describe --tags --abbrev=0` in --repo, default this repository). Only stage names and the short site roles
(config.yaml: figures.workflow) are text. The figure is drawn at the journal text width (137 mm) so that the font
sizes set here (>= 7 pt) are the printed sizes.
"""
import sys, json, csv, re, argparse, subprocess, textwrap
from collections import Counter
from pathlib import Path
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

CODE = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("out", nargs="?", default="Fig2_workflow")
ap.add_argument("--repo", default=__import__("os").environ.get("KITTUR_REPO", str(CODE)))
ap.add_argument("--tag", default=None)
ap.add_argument("--width-mm", type=float, default=137.0)
A = ap.parse_args()

C = yaml.safe_load(open(CODE / "config.yaml"))
ROOT = (CODE / C["project_root"]).resolve()
RES = ROOT / C["paths"]["results"]
V = json.load(open(RES / "validation.json"))
P = json.load(open(RES / "propagation.json"))
B = json.load(open(RES / "belgaum_fort.json"))
EV = list(csv.DictReader(open(RES / "evidence_table.csv")))
FW = C["figures"]["workflow"]
TAG = A.tag or subprocess.run(["git", "-C", A.repo, "describe", "--tags", "--abbrev=0"],
                              capture_output=True, text=True, check=True).stdout.strip()
assert P["n"] == C["propagation"]["n"], f"propagation.json n={P['n']} differs from config n={C['propagation']['n']}; rerun stage 13"

T = V["targets"]; prm = V["params"]
from decimal import Decimal, ROUND_HALF_UP
def _r(x, q): return str(Decimal(repr(float(x))).quantize(Decimal(q), rounding=ROUND_HALF_UP))
def f0(x): return _r(x, "1")
def f1(x): return _r(x, "0.1")
def best(t): return t["models"][t["chosen"]]
def ent(e): return re.sub(r"^DS\d+-\d+", "", e)
def name(k): return T[k]["label"].split(")")[-1].strip()
MODEL = {"affine": "affine", "poly2": "poly2", "poly3": "poly3", "tps": "reg. TPS"}
def compass(deg):
    pts = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return pts[int((deg % 360) / 22.5 + 0.5) % 16]
def ci(m, fmt): return f"{fmt(m['lo95'])}\u2013{fmt(m['hi95'])}"

# ---------------- content ----------------
soi = [k for k, t in T.items() if t["kind"] == "soi"]
soi_names = ", ".join(T[k]["label"].replace("Survey of India ", "").replace(" (1924)", "") for k in soi)
soi_year = sorted({re.search(r"\((\d{4})\)", T[k]["label"]).group(1) for k in soi})
frames = C["corona"]["frames"]
fr_by_date = {}
import datetime as _dt
seen = {}
for e, d in frames.items(): seen[e] = _dt.date.fromisoformat(str(d["date"]))
for k, t in C["validation"]["targets"].items():   # frames used by the validation targets (e.g. DA222), dated from their labels
    if t["kind"] == "corona" and not t.get("transfer") and t["entity"] not in seen:
        seen[t["entity"]] = _dt.datetime.strptime(re.search(r"\((\d+ \w+ \d{4})\)", t["label"]).group(1), "%d %b %Y").date()
for e, d in sorted(seen.items()): fr_by_date.setdefault(d, []).append(ent(e))
site_k = list(FW["sites"])
s2date = re.search(r"(\d{8})", C["inputs"]["s2_dry"]).group(1)
s2date = _dt.datetime.strptime(s2date, "%Y%m%d"); s2date = f"{s2date.day} {s2date:%b %Y}"
ncc_eff = sorted({T[k]["params_effective"]["min_ncc"] for k in site_k})
kinds = [k for k in T[site_k[0]]["kinds"]]
inputs = [
    ("Survey of India", f"one-inch sheets {soi_names} ({', '.join(soi_year)})"),
    ("CORONA KH-4A", "; ".join(f"{', '.join(v)} ({k.day} {k:%b %Y})" for k, v in sorted(fr_by_date.items(), reverse=True))),
    ("OpenStreetMap", f"{', '.join(kinds)} nodes \u2265{prm['min_sep_m']} m apart; fort outline"),
    ("Sentinel-2 L2A", f"{s2date}; matching cue for CORONA ties"),
    ("Elevation", "Copernicus GLO-30; 1967 CORONA stereo pair"),
    ("Colonial texts", FW["texts"]),
]
models = ", ".join(MODEL[m] for m in prm["models"])
fit = ("Fitting: same settings for every source",
       [f"starting transform (graticule corners or Sentinel-2 patch match)",
        f"OSM candidates \u2265{prm['min_sep_m']} m apart \u2192 NCC match with {2*prm['half_m'][0]:.0f} and {2*prm['half_m'][1]:.0f} m templates "
        f"agreeing \u2264{prm['agree_m']} m (NCC \u2265{'/'.join(str(x) for x in ncc_eff)}), RANSAC, blunder screen {prm['blunder_m']} m",
        f"candidates {models}; scored by check split, LOO and {prm['k_blocks']}-block spatial CV",
        "rule: " + V["selection_rule"].split("Choose ")[1].split(".")[0]])
sites = []
for k in site_k:
    t = T[k]; m = best(t)
    bl = f", {t['n_blunders']} blunder{'s' if t['n_blunders'] != 1 else ''}" if t["n_blunders"] else ""
    sites.append((f"{name(k)} ({ent(C['validation']['targets'][k]['entity'])})",
                  [FW["sites"][k], f"{t['n_ties']} ties{bl}", f"recorded {f0(t['before']['rmse_all_m'])} m \u2192 {MODEL[t['chosen']]}",
                   f"block-CV {f1(m['block_cv_rmse_m'])} m", f"LOO {f1(m['loo_rmse_m'])} m"]))
sb = [best(T[k])["block_cv_rmse_m"] for k in soi]
tr = [k for k, t in C["validation"]["targets"].items() if t.get("transfer")]
also = (f"Same steps, unchanged settings: SoI sheets ({MODEL[T[soi[0]]['chosen']]}, block-CV {f0(min(sb))}\u2013{f0(max(sb))} m); "
        + "transfer frames " + ", ".join(f"{name(k)} {f1(best(T[k])['block_cv_rmse_m'])} m" for k in tr) + " (block-CV)")
eb = P["error_budget"]; cp = C["propagation"]
unc = ("Monte Carlo error budget",
       [f"{P['n']} runs (seed {P['seed']})", f"bootstrap refit of chosen transform", f"target error {f1(eb['threshold_sensitivity']['target_range_m'][0])}\u2013{f1(eb['threshold_sensitivity']['target_range_m'][1])} m over {eb['threshold_sensitivity']['n_settings']} tie settings",
        f"digitising SD {f0(eb['digitising_sd_m'])} m; vertex noise {f0(eb['vertex_noise_m'])} m",
        f"GLO-30 SD {'/'.join(f0(x) for x in cp['dsm_sd_scenarios_m'])} m + canopy bias \u2264{f0(cp['canopy_bias_max_m'])} m",
        "one-at-a-time component runs"])
src_cols = [c for c in EV[0] if re.match(r"(soi|landsat|sentinel|dem|osm)", c)]
pos = [c for c in src_cols if any(r[c].startswith(("support", "contradict")) for r in EV)]
lab = lambda c: c.replace("soi", "SoI").replace("sentinel2", "Sentinel-2").replace("landsat", "Landsat").replace("dem", "GLO-30/DSM").replace("osm", "OSM").replace("_", " ")
g = Counter(r["grade"] for r in EV)
grades = ["confirmed", "plausible", "unsupported", "contradicted"]
evid = (f"Evidence grading ({len(EV)} readings)",
        [f"positional sources independent of CORONA: {', '.join(lab(c) for c in pos)}",
         "texts support kind, not position",
         ", ".join(f"{g[x]} {x}" for x in grades)])
M = P["metrics"]; vc = P["vertical_scenarios"]; osg = P["old_sangoli"]
quarry = next(r["grade"] for r in EV if "quarry" in r["id"])
nc = [s["frac_no_higher_cell_1500m"] for s in vc.values()]
nd = T[site_k[2]]; poly_bcv = min(nd["models"][m]["block_cv_rmse_m"] for m in nd["models"] if m.startswith(("affine", "poly")))
fr = FW["lawe_fractions"]; bel = [round(B["gazetteer_ha"], 1), round(B["osm_way_ha"], 1), round(B["inner_wall_line_ha"], 1)]
results = [
    [f"lower fort {f1(M['fort_area_ha']['v2'])} ha ({ci(M['fort_area_ha'], f1)})",
     f"hillock {f0(M['fort_citadel_m']['v2'])} m {compass(M['citadel_bearing_deg']['v2'])} ({ci(M['fort_citadel_m'], f0)} m)",
     f"quarry reading {quarry}",
     f"'nowhere commanded' untestable: no higher cell in {f0(100*min(nc))}\u2013{f0(100*max(nc))}% of DSM runs"],
    [f"1968 village {osg['dist_to_present_sangolli_km']:.2f} km N of modern Sangolli",
     f"{f0(osg['v2_dist_to_shore_m'])} m outside the reservoir; inside in {f0(100*osg['frac_inside_reservoir'])}% of runs",
     "at the shore, not under the water"],
    [f"rule picks {MODEL[nd['chosen']]} ({f1(best(nd)['block_cv_rmse_m'])} m) where polynomials fail on held-out blocks (best {f1(poly_bcv)} m)",
     "model choice must be data-driven"],
    [f"fort {f1(B['inner_wall_line_ha'])} ha to inner wall on {ent(C['validation']['targets'][site_k[3]]['entity'])}",
     f"Lawe's 1/{fr[0]} and 1/{fr[1]} imply {f1(min(bel)/fr[0])}\u2013{f1(max(bel)/fr[0])} and {f1(min(bel)/fr[1])}\u2013{f1(max(bel)/fr[1])} ha",
     "a loose consistency check only"],
]
footer = (f"Code and outputs (rasters, vectors, per-tie QA sheets, intervals, grades): tag {TAG}. "
          "LOO, leave-one-out; reg. TPS, regularised thin-plate spline.")

# ---------------- drawing (mm coordinates, true print size) ----------------
plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})
FS, FSH = 7.0, 7.5          # body and heading pt
PT = 25.4 / 72              # mm per pt
LH = FS * 1.17 * PT         # line height mm
W = A.width_mm; M_ = 0.6; GAP = 2.0; PAD = 1.2
CW = 0.585 * FS * PT          # approx char width (DejaVu) mm
COL = dict(inp="#e8eef7", proc="#e9f5ec", site="#fff1d6", out="#f3e8f5", hdr="#20406a", edge="#555555")
items = []   # (x, ytop, w, h, head, lines, fc)
def wrap(lines, w):
    n = max(8, int((w - 2 * PAD) / CW))
    out = []
    for l in lines: out += textwrap.wrap(l, n) or [""]
    return out
def hgt(nl): return PAD + FSH * 1.2 * PT + nl * LH + PAD * 0.8
def row(boxes, y, x0=M_, x1=None, fc="inp", band=None, equal=True):
    x1 = x1 or W - M_; n = len(boxes); w = (x1 - x0 - GAP * (n - 1)) / n
    wr = [wrap(l, w) for _, l in boxes]; h = max(hgt(len(a)) for a in wr)
    for i, ((hd, _), lines) in enumerate(zip(boxes, wr)):
        items.append((x0 + i * (w + GAP), y, w, h, hd, lines, COL[fc]))
    return y - h, [(x0 + i * (w + GAP) + w / 2) for i in range(n)], h
arrows = []; y = 0.0; texts = []
yb, cx_in, _ = row([(h, [b]) for h, b in inputs[:3]], y); y = yb - GAP
yb, cx_in2, _ = row([(h, [b]) for h, b in inputs[3:]], y); y_in_bot = yb; y = yb - GAP * 1.7
y_fit = y; yb, _, _ = row([(fit[0], fit[1])], y, fc="proc"); arrows += [(W / 2, y_in_bot, W / 2, y_fit)]; y = yb - GAP * 1.7
y_site = y; yb, cx, _ = row(sites, y, fc="site")
for c in cx: arrows.append((c, y_site + GAP * 1.7, c, y_site))
y = yb - 1.0
also_l = wrap([also], W - 2 * M_); texts.append((M_ + PAD, y - 0.6, also_l, "italic")); y = y - 0.6 - len(also_l) * LH - GAP * 1.4
y_unc = y; yb1, cu, h1 = row([unc, evid], y, fc="proc")
for c in cu: arrows.append((c, y_unc + GAP * 1.4, c, y_unc))
y = yb1 - GAP * 1.7
y_res = y; yb, cr, _ = row([(name(k) + ": result", r) for k, r in zip(site_k, results)], y, fc="out")
for c in cr: arrows.append((c, y_res + GAP * 1.7, c, y_res))
y = yb - 1.2
foot_l = wrap([footer], W - 2 * M_); texts.append((M_ + PAD, y, foot_l, "normal")); y -= len(foot_l) * LH + 0.6
H = -y
fig = plt.figure(figsize=(W / 25.4, H / 25.4)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(-H, 0); ax.axis("off")
for x, yt, w, h, hd, lines, fc in items:
    ax.add_patch(FancyBboxPatch((x, yt - h), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=COL["edge"], lw=0.6))
    ax.text(x + PAD, yt - PAD, hd, ha="left", va="top", fontsize=FSH, weight="bold", color=COL["hdr"])
    ax.text(x + PAD, yt - PAD - FSH * 1.2 * PT, "\n".join(lines), ha="left", va="top", fontsize=FS, linespacing=1.17)
for x0, y0, x1, y1 in arrows:
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#333333", mutation_scale=8, shrinkA=0, shrinkB=0))
for x, yt, lines, st in texts:
    ax.text(x, yt, "\n".join(lines), ha="left", va="top", fontsize=FS, style=st, linespacing=1.17)
fig.savefig(A.out + ".pdf"); fig.savefig(A.out + ".png", dpi=600)
print(f"{A.out}: {W:.0f} x {H:.0f} mm, body {FS} pt, tag {TAG}, MC n={P['n']}")
