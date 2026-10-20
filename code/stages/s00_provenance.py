"""Stage 00 - provenance: sha256 inventory of every raw input -> release/PROVENANCE.csv (path from config.yaml).

Scans the roots in params/provenance_sources.yaml (raw/, historical_maps/raw/, sites/*/raw/ - the comparison-site
CORONA archives, Sentinel-2 scenes and dry-season epoch medians), classifies each file with the first matching rule,
and checks the hashes against any SHA256.txt written at download time. Hashes are cached in
results/sha256_cache.json (keyed by path, size and mtime) so re-runs only hash new or changed files.

Run:  python run.py provenance            (replaces legacy/make_provenance.py)
"""
from __future__ import annotations
import sys, re, json, csv, hashlib, datetime, glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kittur.config import load, Stage
import yaml


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def inventory(C, st):
    R = C.root; S = yaml.safe_load(open(C.code('params/provenance_sources.yaml')))
    rules = [(re.compile(r['re']), r) for r in S['rules']]; skip = [re.compile(x) for x in S['skip']]
    cache_p = C.out('results', 'sha256_cache.json'); cache = json.load(open(cache_p)) if cache_p.exists() else {}
    files = []
    for root in S['scan_roots']:
        for d in sorted(glob.glob(str(R / root))):
            files += [p for p in sorted(Path(d).rglob('*')) if p.is_file()]
    rows, hashed = [], 0
    for p in files:
        rel = p.relative_to(R).as_posix()
        if any(x.search(rel) for x in skip):
            continue
        stt = p.stat(); key = f'{rel}|{stt.st_size}|{int(stt.st_mtime)}'
        if key not in cache:
            cache[key] = sha256(p); hashed += 1
        m, r = next((m, r) for rx, r in rules if (m := rx.search(rel)))
        g = m.groupdict()
        fill = lambda s: s.format(entity=g.get('entity', ''), epoch=g.get('epoch', ''), site=g.get('site', ''),
                                  corona_date=str(S['corona_dates'].get(g.get('entity', ''), 'unknown')))
        rows.append(dict(file=rel, size_MB=round(stt.st_size / 1e6, 1), source=fill(r['source']), acquisition=fill(r['acquisition']),
                         download_date=datetime.date.fromtimestamp(stt.st_mtime).isoformat(), license=r['license'],
                         sha256=cache[key], processing_script=r['script'], storage='Zenodo/LFS' if stt.st_size > 100e6 else 'git'))
    json.dump(cache, open(cache_p, 'w'), indent=0)
    # cross-check against download-time SHA256.txt files
    by = {r['file']: r['sha256'] for r in rows}; checked = bad = 0
    for t in [r['file'] for r in rows if r['file'].endswith('SHA256.txt')]:
        base = Path(t).parent
        for line in open(R / t):
            parts = line.split()
            if len(parts) != 2:
                continue
            h, f = parts; name = Path(f).name
            rel = (base / name).as_posix()
            if rel in by:
                checked += 1
                if by[rel] != h:
                    bad += 1; st.note(f'  SHA MISMATCH {rel}')
    out = C.p('provenance')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    unc = [r['file'] for r in rows if r['source'] == 'unclassified']
    st.note(f'{len(rows)} files -> {out.relative_to(R)} ({hashed} newly hashed); SHA256.txt cross-check: {checked} checked, {bad} mismatches'
            + (f'; unclassified: {unc}' if unc else ''))
    return rows


def main(argv=None):
    C = load()
    with Stage(C, 'provenance') as st:
        inventory(C, st)


if __name__ == '__main__':
    main()
