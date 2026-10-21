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


class Config(dict):
    """dict of the YAML content plus path helpers."""

    @property
    def root(self) -> Path:
        return self['_root']

    def p(self, key: str) -> Path:
        """Absolute path for an entry of `paths:`."""
        return self.root / self['paths'][key]

    def f(self, rel: str) -> Path:
        """Absolute path for a project-relative string (e.g. inputs.dem)."""
        return self.root / rel

    def code(self, rel: str) -> Path:
        """Absolute path for a file relative to release/code (e.g. params/*.json)."""
        return CODE_DIR / rel

    def out(self, key: str, *parts: str) -> Path:
        """Output path under paths[key]; parent directories are created."""
        q = self.p(key).joinpath(*parts)
        q.parent.mkdir(parents=True, exist_ok=True)
        return q


def load(path: str | os.PathLike | None = None) -> Config:
    path = Path(path or os.environ.get('KITTUR_CONFIG', CODE_DIR / 'config.yaml')).resolve()
    with open(path) as fh:
        c = Config(yaml.safe_load(fh))
    c['_root'] = (path.parent / c['project_root']).resolve()
    c['_config_path'] = path
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
