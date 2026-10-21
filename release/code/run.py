"""Pipeline entry point.

    python run.py all                 # stages 00-11 in order
    python run.py <stage> [args...]   # one stage: provenance, fetch, preprocess, georeference, dem, metrics,
                                      # landscape, montecarlo, figures, tables, map, lite

Configuration: config.yaml (or env KITTUR_CONFIG). Stage status: results/run_log.json.
"""
import sys, importlib, json, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
STAGES = ['provenance', 'fetch', 'preprocess', 'georeference', 'dem', 'metrics', 'landscape', 'montecarlo', 'figures', 'tables', 'map', 'lite']
MOD = {s: f'stages.s{i:02d}_{s}' for i, s in enumerate(STAGES)}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in STAGES + ['all']:
        print(__doc__); sys.exit(1)
    todo = STAGES if sys.argv[1] == 'all' else [sys.argv[1]]
    for s in todo:
        importlib.import_module(MOD[s]).main(sys.argv[2:] if s == sys.argv[1] else [])
