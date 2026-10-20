"""Stage 11 - refresh the lightweight shareable copy (../kittur_map_lite and ../kittur_basemap_lite.zip).

Copies the interactive base map (kittur_basemap.html + only the web/ layers it references; layers > 2 MB re-encoded as
WebP with alpha and the references rewritten), findings.md, gazetteer.csv,
the vector GeoPackages (qgis/kittur_vectors.gpkg and the pipeline's derived/vectors/*.gpkg), quick-look previews
(project previews/ and sites/*/previews/, PNGs > 1.5 MB re-encoded as JPEG), the manuscript figures as JPEG proofs
with their captions, and the manuscript tables. Full-resolution TIFF/PDF figures and rasters are not copied.
The base map itself is rebuilt by stage 10 (map, folium) and copied here.

Run:  python run.py lite
"""
from __future__ import annotations
import sys, re, shutil, zipfile, datetime
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage

Image.MAX_IMAGE_PIXELS = None


def _img(src: Path, dst_dir: Path, max_mb=1.5, max_px=None):
    dst_dir.mkdir(parents=True, exist_ok=True)
    big = src.stat().st_size > max_mb * 1e6 or src.suffix.lower() in ('.tif', '.tiff')
    if not big:
        shutil.copy2(src, dst_dir / src.name); return dst_dir / src.name
    im = Image.open(src).convert('RGB')
    if max_px and max(im.size) > max_px:
        im.thumbnail((max_px, max_px), Image.LANCZOS)
    out = dst_dir / (src.stem + '.jpg'); im.save(out, quality=85, optimize=True)
    stale = dst_dir / src.name
    if stale.exists() and stale != out:
        stale.unlink()
    return out


def main(argv=None):
    C = load(); R = C.root; L = C.p('lite'); L.mkdir(parents=True, exist_ok=True)
    with Stage(C, 'lite') as st:
        n = 0
        html = R / 'kittur_basemap.html'
        if html.exists():
            H = html.read_text(errors='ignore')
            refs = sorted(set(re.findall(r'web/[^"\'\s)]+\.(?:png|jpg)', H)))
            (L / 'web').mkdir(exist_ok=True); keep = set()
            for r in refs:                              # large layers -> lossy WebP with alpha (q 80); refs rewritten
                src = R / r
                if not src.exists():
                    continue
                if src.stat().st_size > 2e6:
                    w = Path(r).with_suffix('.webp').as_posix()
                    Image.open(src).save(L / w, 'WEBP', quality=80, method=4); H = H.replace(r, w); keep.add(Path(w).name)
                else:
                    shutil.copy2(src, L / r); keep.add(Path(r).name)
                n += 1
            (L / html.name).write_text(H); n += 1
            for old in (L / 'web').iterdir():          # drop layers no longer referenced
                if old.name not in keep:
                    old.unlink()
            st.note(f'base map: {len(refs)} web layers ({sum(k.endswith(".webp") for k in keep)} re-encoded as WebP)')
        for f in ('findings.md', 'gazetteer.csv'):
            if (R / f).exists():
                shutil.copy2(R / f, L / f); n += 1
        if (R / 'qgis' / 'kittur_vectors.gpkg').exists():
            shutil.copy2(R / 'qgis' / 'kittur_vectors.gpkg', L / 'kittur_vectors.gpkg'); n += 1
        (L / 'vectors').mkdir(exist_ok=True)
        for g in sorted((C.p('derived') / 'vectors').glob('*.gpkg')):
            shutil.copy2(g, L / 'vectors' / g.name); n += 1
        for p in sorted(C.p('previews').glob('*.png')):
            _img(p, L / 'previews'); n += 1
        for p in sorted(C.p('sites').glob('*/previews/*.png')):
            _img(p, L / 'previews' / 'sites' / p.parent.parent.name); n += 1
        fd = L / 'manuscript' / 'figures'
        for p in sorted(C.p('figures').glob('*.tif')):
            _img(p, fd, max_px=2400); n += 1
        if (C.p('figures') / 'figure_captions.md').exists():
            shutil.copy2(C.p('figures') / 'figure_captions.md', fd / 'figure_captions.md')
        td = L / 'manuscript' / 'tables'; td.mkdir(parents=True, exist_ok=True)
        for p in sorted(C.p('tables').glob('*')):
            if p.is_file() and not p.name.startswith('.'):
                shutil.copy2(p, td / p.name); n += 1
        # README: keep the original text, refresh the dated section
        rd = L / 'README.md'; txt = rd.read_text() if rd.exists() else '# Kittur desk-only base map\n'
        txt = re.sub(r'\n## Refreshed by the pipeline.*', '', txt, flags=re.S)
        txt += (f"\n## Refreshed by the pipeline ({datetime.datetime.now().strftime('%d %b %Y %H:%M')} IST)\n"
                "- `manuscript/figures/`: JPEG proofs of the journal figures (full TIFF/PDF in the project, manuscript/figures) and `figure_captions.md`.\n"
                "- `manuscript/tables/`: tables as CSV, `tables.xlsx` and `tables.docx`.\n"
                "- `vectors/`: pipeline GeoPackages (1968 Kittur features, landscape zones/paths, Belgaum fort 1968 moat trace).\n"
                "- `previews/`: quick-looks incl. `sites_overview` (Srirangapatna, Hampi, Belgaum), `sites_timeline`, `timeline_<site>`; "
                "`previews/sites/<site>/`: per-site comparison panels.\n"
                "- Regenerate with `cd release/code && python run.py lite`.\n")
        rd.write_text(txt)
        z = C.p('lite_zip')
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(L.rglob('*')):
                if p.is_file():
                    zf.write(p, Path(L.name) / p.relative_to(L))
        size = sum(p.stat().st_size for p in L.rglob('*') if p.is_file()) / 1e6
        st.note(f'{n} files refreshed in {L} ({size:.0f} MB); zip {z.name} {z.stat().st_size / 1e6:.0f} MB')


if __name__ == '__main__':
    main()
