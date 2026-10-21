"""Configuration loader. One YAML file (release/code/config.yaml) defines every path.

Usage:
    from kittur.config import load
    C = load()               # or load('/path/to/config.yaml'); env KITTUR_CONFIG also honoured
    C.p('derived') / 'corona'
"""
from __future__ import annotations
import os, json, time, datetime
from pathlib import Path
import yaml

CODE_DIR = Path(__file__).resolve().parent.parent
# paths: entries that stages write to; redirected by --out / KITTUR_OUT so a reviewer's run never overwrites
# the deposited results. Inputs (raw/, historical_maps/, sites/) are always read from project_root.
OUTPUT_KEYS = {'derived', 'results', 'previews', 'figures', 'tables', 'log', 'lite', 'lite_zip'}


class Config(dict):
    """dict of the YAML content plus path helpers."""

    @property
    def root(self) -> Path:
        return self['_root']

    @property
    def out_root(self) -> Path:
        """Where pipeline OUTPUTS go: env KITTUR_OUT (set by `run.py --out DIR`) or, by default, project_root."""
        return self.get('_out') or self.root

    def p(self, key: str) -> Path:
        """Absolute path for an entry of `paths:`. For output folders under --out, the scratch copy is used once
        it exists; otherwise the original tree is read (so a single stage can run on top of earlier results)."""
        if self.get('_out') and key in OUTPUT_KEYS:
            q = self['_out'] / self['paths'][key]
            if q.exists():
                return q
        return self.root / self['paths'][key]

    def f(self, rel: str) -> Path:
        """Absolute path for a project-relative string (e.g. inputs.dem)."""
        return self.root / rel

    def code(self, rel: str) -> Path:
        """Absolute path for a file relative to release/code (e.g. params/*.json). Fitted models
        (params/validation_models/) are pipeline outputs and follow --out like the other outputs."""
        if self.get('_out') and rel.startswith('params/validation_models'):
            q = self['_out'] / 'release' / 'code' / rel
            if q.exists() or not (CODE_DIR / rel).exists():
                return q
        return CODE_DIR / rel

    def code_out(self, rel: str) -> Path:
        """Write location for a fitted-model file under params/ (follows --out)."""
        q = (self['_out'] / 'release' / 'code' / rel) if self.get('_out') else CODE_DIR / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        return q

    def out(self, key: str, *parts: str) -> Path:
        """Output path under paths[key]; parent directories are created."""
        base = self.out_root / self['paths'][key] if key in OUTPUT_KEYS else self.p(key)
        q = base.joinpath(*parts)
        q.parent.mkdir(parents=True, exist_ok=True)
        return q


def load(path: str | os.PathLike | None = None) -> Config:
    path = Path(path or os.environ.get('KITTUR_CONFIG', CODE_DIR / 'config.yaml')).resolve()
    with open(path) as fh:
        c = Config(yaml.safe_load(fh))
    c['_root'] = (path.parent / c['project_root']).resolve()
    c['_config_path'] = path
    if os.environ.get('KITTUR_OUT'):
        c['_out'] = Path(os.environ['KITTUR_OUT']).resolve()
    return c


def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as fh:
        json.dump(obj, fh, indent=1, default=float)


class Stage:
    """Context manager that times a stage and records status in results/run_log.json."""

    def __init__(self, C: Config, name: str):
        self.C, self.name, self.notes = C, name, []

    def note(self, msg: str):
        print(f'[{self.name}] {msg}', flush=True)
        self.notes.append(msg)

    def __enter__(self):
        self.t0 = time.time()
        print(f'=== stage {self.name} ===', flush=True)
        return self

    def __exit__(self, et, ev, tb):
        status = 'ok' if et is None else f'FAILED: {et.__name__}: {ev}'
        log = self.C.out('results', 'run_log.json')
        d = json.load(open(log)) if log.exists() else {}
        d[self.name] = dict(status=status, seconds=round(time.time() - self.t0, 1),
                            finished=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
                            notes=self.notes)
        save_json(d, log)
        print(f'=== {self.name}: {status} ({d[self.name]["seconds"]} s) ===', flush=True)
        return False
