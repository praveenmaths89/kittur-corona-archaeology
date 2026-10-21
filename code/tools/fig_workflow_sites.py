"""Fig. 2: workflow across the four Kittur-region CORONA sites (plus SoI sheets and transfer sites).
Numbers are taken from results/validation.json and propagation.json as reported in Tables 2-3."""
import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "pdf.fonttype": 42})
out = sys.argv[1] if len(sys.argv) > 1 else "Fig2_workflow"
W, H = 190/25.4, 150/25.4
fig = plt.figure(figsize=(W, H)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 190); ax.set_ylim(0, 150); ax.axis("off")
C = dict(inp="#e8eef7", site="#fff4e0", proc="#e9f5ec", out="#f3e8f5", edge="#444444", hdr="#20406a")
def box(x, y, w, h, txt, fc, fs=6.6, bold_first=True, ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=C["edge"], lw=0.6))
    lines = txt.split("\n")
    tx = x + w/2 if ha == "center" else x + 1.5
    if bold_first:
        ax.text(tx, y + h - 2.2, lines[0], ha=ha, va="top", fontsize=fs+0.4, weight="bold")
        ax.text(tx, y + h - 5.6, "\n".join(lines[1:]), ha=ha, va="top", fontsize=fs, linespacing=1.25)
    else:
        ax.text(tx, y + h/2, txt, ha=ha, va="center", fontsize=fs, linespacing=1.25)
def arrow(x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=0.7, color="#333333", mutation_scale=7))
def band(y, label):
    ax.text(1.5, y, label, rotation=90, ha="left", va="center", fontsize=6.4, weight="bold", color=C["hdr"])
# 1 inputs
band(137, "Inputs")
ins = [("Survey of India", "3 one-inch sheets\n48 I/09, I/10, I/14\n(1922-23, pr. 1924)"),
       ("CORONA KH-4A", "DA222, DA224, DF224\n(31 Jan 1968); checks\nDA217/DF217 (1967)"),
       ("OpenStreetMap", "junctions, tanks\n$\\geq$1 ha, villages;\nfort outline"),
       ("Sentinel-2 L2A", "2026 dry season\n10 m; image cue\nfor CORONA ties"),
       ("Elevation", "Copernicus GLO-30\n(30 m); 1967\nstereo parallax"),
       ("Archival texts", "Gazetteer 1884 (Lawe\n1825, Welsh 1828);\nNAI letters 1824")]
w = 28.5
for i, (a, b) in enumerate(ins):
    box(6 + i*(w+2.4), 127, w, 20, a + "\n" + b, C["inp"])
# 2 common steps
band(112.5, "Fitting")
box(6, 104, 178, 17, "Same settings for every source (frozen before the transfer runs)\n"
    "starting transform (graticule corners or Sentinel-2 patch matching)  >  OSM candidates at 300 m spacing  >\n"
    "NCC match on road or Sentinel-2 cue, two template sizes, RANSAC  >  affine, poly2, poly3, regularised TPS  >\n"
    "scored by fit, held-out checks, LOO and spatial block-CV  >  simplest model within 10% of the best block-CV", C["proc"], fs=6.2)
for i in range(6): arrow(6 + i*(w+2.4) + w/2, 127, 6 + i*(w+2.4) + w/2, 121.6)
# 3 four sites
band(84, "Four sites")
sites = [("Kittur (DA224)", "fort and town; 2 m crop", "25 ties (5 within 2 km)", "120 m > poly2", "block-CV 30 m (LOO 22)"),
         ("Sangolli (DF224)", "old village, Malaprabha", "16 ties", "77 m > poly2", "block-CV 30 m (LOO 20)"),
         ("Nandagad (DA224)", "control area 20 km W", "20 ties", "34 m > reg. TPS", "block-CV 37 m (LOO 14)"),
         ("Belgaum (DA222)", "reference for Lawe's\narea fractions", "29 ties, 1 blunder", "99 m > poly2", "block-CV 19 m (LOO 10)")]
sw = 41.5
for i, (n, r, t, m, a) in enumerate(sites):
    x = 6 + i*(sw + 3)
    box(x, 72, sw, 26, f"{n}\n{r}\n{t}\nrecorded {m}\n{a}", C["site"])
    arrow(x + sw/2, 104, x + sw/2, 98.6)
ax.text(95, 69.2, "Also run: SoI sheets 48 I/09, I/10, I/14 (159-629 m > affine, block-CV 56-81 m);  transfer frames with unchanged settings: "
        "Srirangapatna 13 m, Hampi 11 m (block-CV)", ha="center", va="center", fontsize=6.0, style="italic")
# 4 propagation and grading
band(53, "Uncertainty")
box(6, 44, 87, 21, "Monte Carlo error budget (200 runs)\nbootstrap refit of chosen transform; target error\n18.7-53.1 m from tie-threshold runs; digitising\nSD 5 m; vertex noise 4 m; GLO-30 error SD 2-5 m\n+ canopy bias; one-at-a-time component runs", C["proc"])
box(97, 44, 87, 21, "Evidence grading (15 readings)\n5 positional sources independent of CORONA:\nSoI 1924, Landsat 1990, Sentinel-2 2026, GLO-30,\nOSM. Texts support kind, not position. Grades:\nconfirmed / plausible / unsupported / contradicted", C["proc"])
for i in range(4):
    x = 6 + i*(sw + 3) + sw/2
    arrow(x, 72, 49.5 if i < 2 else 140.5, 65.6) if False else arrow(x, 72, x, 65.6)
arrow(93, 54.5, 97, 54.5)
# 5 outputs per site
band(22, "Key results")
outs = [("Kittur", "lower fort 13.0 ha\n(11.7-14.2); hillock\n535 m SSW (464-613);\nquarry contradicted;\n'nowhere commanded'\nuntestable"),
        ("Sangolli", "1968 village 3.24 km N\nof modern Sangolli;\n17 m outside reservoir,\ninside in 17.5% of runs:\nat the edge, not\nunder the water"),
        ("Nandagad", "rule picks reg. TPS\nwhere polynomials fail\non held-out blocks;\nshows selection must\nbe data-driven, not\na fixed model"),
        ("Belgaum", "fort 58.0 ha to inner\nwall on 1968 frame;\nLawe's 1/6 and 1/10\nimply 6.8-9.7 and\n4.1-5.8 ha: a loose\nconsistency check")]
for i, (n, t) in enumerate(outs):
    x = 6 + i*(sw + 3)
    box(x, 5, sw, 33, n + "\n" + t, C["out"])
    arrow(x + sw/2, 44, x + sw/2, 38.6)
ax.text(95, 1.6, "Outputs: re-georeferenced rasters, digitised vectors, per-tie QA sheets, intervals and grades (code tag v1.1-jasr-submission). block-CV, spatial block cross-validation; LOO, leave-one-out.",
        ha="center", va="center", fontsize=5.6)
fig.savefig(out + ".pdf"); fig.savefig(out + ".png", dpi=600)
