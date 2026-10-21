"""Cohen's kappa between the first analyst (params/evidence.yaml) and a blind second grader.

    python tools/kappa.py <filled second_grader sheet.csv>

Agreement is reported at two levels:
  * per-source verdicts (support / neutral / contradict / n/a), one item per reading x source row;
  * final grades (confirmed / plausible / unsupported / contradicted), obtained by applying the SAME grading rule
    (stages/s14_evidence.grade) to each analyst's verdicts, keeping the non-positional evidence (gazetteer) of
    the first analyst for both.
"""
import sys
from pathlib import Path
import pandas as pd
import yaml

CODE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE))
from stages.s14_evidence import grade, GRADES   # noqa: E402

VERDICTS = ('support', 'neutral', 'contradict', 'n/a')


def cohen_kappa(a, b, labels):
    """Unweighted Cohen's kappa for two equal-length label sequences."""
    n = len(a)
    if n == 0:
        return float('nan')
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((list(a).count(l) / n) * (list(b).count(l) / n) for l in labels)
    return float('nan') if pe == 1 else (po - pe) / (1 - pe)


def main(sheet):
    spec = yaml.safe_load(open(CODE / 'params' / 'evidence.yaml'))
    first = {f"{f['id']}|{e['source']}": e['verdict'] for f in spec['features'] for e in f['evidence']}
    s = pd.read_csv(sheet)
    s['verdict_second_grader'] = s.verdict_second_grader.astype(str).str.strip().str.lower()
    bad = s[~s.verdict_second_grader.isin(VERDICTS)]
    if len(bad):
        raise SystemExit(f'{len(bad)} rows without a valid verdict (use one of {VERDICTS}): {list(bad.item_id)}')
    s['verdict_first'] = s.item_id.map(first)
    k1 = cohen_kappa(s.verdict_first, s.verdict_second_grader, VERDICTS)
    second = dict(zip(s.item_id, s.verdict_second_grader))
    g1, g2 = [], []
    for f in spec['features']:
        ev2 = [dict(e, verdict=second.get(f"{f['id']}|{e['source']}", e['verdict'])) for e in f['evidence']]
        g1.append(grade(f['evidence'])); g2.append(grade(ev2))
    k2 = cohen_kappa(g1, g2, GRADES)
    print(f'per-source verdicts: n = {len(s)}, agreement {100 * (s.verdict_first == s.verdict_second_grader).mean():.0f}%, kappa = {k1:.2f}')
    print(f'final grades:        n = {len(g1)}, agreement {100 * sum(x == y for x, y in zip(g1, g2)) / len(g1):.0f}%, kappa = {k2:.2f}')
    for f, x, y in zip(spec['features'], g1, g2):
        if x != y:
            print(f"  grade differs: {f['id']}: first {x}, second {y}")
    for _, r in s[s.verdict_first != s.verdict_second_grader].iterrows():
        print(f"  verdict differs: {r.item_id}: first {r.verdict_first}, second {r.verdict_second_grader}")


if __name__ == '__main__':
    main(sys.argv[1])
