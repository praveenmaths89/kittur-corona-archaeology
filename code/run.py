"""Pipeline entry point.

    python run.py all                 # all stages in order (00-07, 12-14, 08-11)
    python run.py --out DIR all       # write every output under DIR (results/, derived/, manuscript/...) instead of
                                      # the project tree; inputs are still read from project_root
    python run.py <stage> [args...]   # one stage: provenance, fetch, preprocess, georeference, dem, metrics,
                                      # landscape, montecarlo, validation, propagation, evidence, figures, tables, map, lite

Configuration: config.yaml (or env KITTUR_CONFIG). Stage status: results/run_log.json.
"""
import sys, os, importlib, json, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Order of 'all'. Stages 12-14 (desk validation) run after the Monte Carlo stage and before figures/tables;
# module numbers are kept stable, so the mapping is explicit.
STAGES = ['provenance', 'fetch', 'preprocess', 'georeference', 'dem', 'metrics', 'landscape', 'montecarlo',
          'validation', 'propagation', 'evidence', 'figures', 'tables', 'map', 'lite']
NUM = {'provenance': 0, 'fetch': 1, 'preprocess': 2, 'georeference': 3, 'dem': 4, 'metrics': 5, 'landscape': 6, 'montecarlo': 7,
       'figures': 8, 'tables': 9, 'map': 10, 'lite': 11, 'validation': 12, 'propagation': 13, 'evidence': 14}
MOD = {s: f'stages.s{NUM[s]:02d}_{s}' for s in STAGES}

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--out':        # scratch output directory
        os.environ['KITTUR_OUT'] = str(Path(sys.argv[2]).resolve()); del sys.argv[1:3]
    if len(sys.argv) < 2 or sys.argv[1] not in STAGES + ['all']:
        print(__doc__); sys.exit(1)
    todo = STAGES if sys.argv[1] == 'all' else [sys.argv[1]]
    for s in todo:
        importlib.import_module(MOD[s]).main(sys.argv[2:] if s == sys.argv[1] else [])
