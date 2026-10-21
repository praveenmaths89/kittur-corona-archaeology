"""Stage 10 - rebuild the interactive base map kittur_basemap.html (folium) from qgis/rasters, vectors and sites/.

Runs stages/_basemap_build.py (a copy of the project-root build.py) with cwd = project root, so the map is
reproducible from the pipeline. Writes kittur_basemap.html and web/*.png. Run:  python run.py map
"""
import sys, runpy, os, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage

def main(argv=None):
    C = load()
    with Stage(C, 'map') as st:
        import folium; st.note(f'folium {folium.__version__}')
        cwd = os.getcwd(); os.chdir(C.root)
        try:
            runpy.run_path(str(Path(__file__).with_name('_basemap_build.py')), run_name='__main__')
        finally:
            os.chdir(cwd)
        h = C.root / 'kittur_basemap.html'
        st.note(f'kittur_basemap.html {h.stat().st_size} B sha256 {hashlib.sha256(h.read_bytes()).hexdigest()[:12]}')

if __name__ == '__main__':
    main(sys.argv[1:])
