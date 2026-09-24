"""Read-only audit accounting. No extraction, semantic decisions, or file writes.

Run `python3 score.py > scores.json` after all original audit jobs finish.
Run `python3 score.py --self-test` for the in-memory synthetic checks.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random

CORE = {'intrinsic_material_mechanism', 'thermodynamics', 'ion_mass_transport',
        'electrode_interface_kinetics'}
VERDICTS = ('supported', 'partial', 'unsupported', 'out_of_scope', 'uncertain')
VALIDITIES = ('valid', 'uncertain', 'out_of_scope')
COVERAGES = ('complete', 'partial', 'missing')
SEED = 20260925


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index_unique(rows, key, label):
    result = {}
    for row in rows:
        value = row[key]
        require(value not in result, f'Duplicate {label}: {value}')
        result[value] = row
    return result


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def interval(values):
    nonnull = sorted(v for v in values if v is not None)
    def quantile(p):
        at = (len(nonnull) - 1) * p
        lo, hi = math.floor(at), math.ceil(at)
        return nonnull[lo] + (nonnull[hi] - nonnull[lo]) * (at - lo)
    return dict(low=quantile(.025) if nonnull else None,
                high=quantile(.975) if nonnull else None,
                usable_replicates=len(nonnull), null_replicates=len(values)-len(nonnull))


def bootstrap(units, statistic, rng, repetitions, stratum=lambda x: 'domain'):
    """Resample paper units within groups, keeping frozen design weights."""
    groups = defaultdict(list)
    for unit in units:
        groups[stratum(unit)].append(unit)
    values = []
    for _ in range(repetitions):
        draw = [rng.choice(group) for group in groups.values() for _ in group]
        values.append(statistic(draw))
    return interval(values)


def validate_weights(rows, label):
    index_unique(rows, 'id', label)
    groups = defaultdict(list)
    for row in rows:
        require(row['domain'] in ('iTE', 'TG'), f'Unknown domain: {row}')
        require(isinstance(row['N'], int) and isinstance(row['n'], int)
                and 0 < row['n'] <= row['N'], f'Invalid stratum sizes: {row}')
        require(math.isfinite(row['weight']) and math.isclose(
            row['weight'], row['N'] / row['n'], rel_tol=1e-12), f'Invalid weight: {row}')
        groups[(row['domain'], row['stratum'])].append(row)
    for key, group in groups.items():
        require(len(group) == group[0]['n'], f'Incomplete {label} stratum {key}')
        require(len({(x['N'], x['n']) for x in group}) == 1,
                f'Inconsistent {label} stratum {key}')


def compute(selection, baseline, reference, judgments, coverage_papers,
            exclusions, repetitions=2000, enforce_sizes=True):
    """Validate complete ID sets, then calculate original-baseline scores."""
    require(repetitions >= 1, 'Bootstrap repetitions must be positive')
    base = index_unique(baseline, 'paper_id', 'baseline paper')
    relations, owners = {}, {}
    for pid, paper in base.items():
        for record in paper['records']:
            rid = record['relation_id']
            require(rid not in relations, f'Duplicate baseline relation: {rid}')
            relations[rid], owners[rid] = record, pid
    validate_weights(selection['precision'], 'precision sample')
    validate_weights(selection['recall'], 'recall sample')
    precision = index_unique(selection['precision'], 'id', 'precision sample')
    recall = index_unique(selection['recall'], 'id', 'recall sample')
    challenges = selection['challenge']
    require(len(challenges) == len(set(challenges)), 'Duplicate challenge ID')
    require(not set(challenges) & precision.keys(), 'Challenge overlaps precision')
    require(set(challenges) <= relations.keys(), 'Unknown challenge ID')
    for rid, item in precision.items():
        require(rid in relations, f'Unknown precision ID: {rid}')
        pid = owners[rid]
        require(pid not in exclusions, f'Historical precision paper: {pid}')
        require(item['domain'] == base[pid]['domain'], f'Precision domain mismatch: {rid}')
    for pid, item in recall.items():
        require(pid in base and pid not in exclusions, f'Invalid recall paper: {pid}')
        require(item['domain'] == base[pid]['domain'], f'Recall domain mismatch: {pid}')
    if enforce_sizes:
        require(len(exclusions) == 428 and selection['excluded_count'] == 428,
                'Historical exclusions must contain exactly 428 unique papers')
        for domain in ('iTE', 'TG'):
            require(sum(x['domain'] == domain for x in precision.values()) == 100,
                    f'{domain}: expected 100 precision relations')
            require(sum(x['domain'] == domain for x in recall.values()) == 30,
                    f'{domain}: expected 30 recall papers')
            require(sum(base[owners[r]]['domain'] == domain for r in challenges) == 25,
                    f'{domain}: expected 25 challenge relations')
    judged = index_unique(judgments, 'relation_id', 'judgment')
    require(judged.keys() == precision.keys() | set(challenges), 'Judgment ID set mismatch')
    for rid, judgment in judged.items():
        require(judgment['verdict'] in VERDICTS, f'Invalid verdict: {rid}')
        require(isinstance(judgment['issues'], list) and all(
            isinstance(x, str) for x in judgment['issues']), f'Invalid issues: {rid}')
    refs = index_unique(reference, 'paper_id', 'reference paper')
    require(refs.keys() == recall.keys(), 'Reference paper ID set mismatch')
    covered = index_unique(coverage_papers, 'paper_id', 'coverage paper')
    require(covered.keys() == recall.keys(), 'Coverage paper ID set mismatch')
    all_reference_ids = set()
    for pid, paper in refs.items():
        if 'domain' in paper:
            require(paper['domain'] == base[pid]['domain'], f'Reference domain mismatch: {pid}')
        by_id = index_unique(paper['records'], 'relation_id', 'reference relation')
        require(not all_reference_ids & by_id.keys(), 'Cross-paper duplicate reference IDs')
        require(all(rid.startswith(pid + ':g') for rid in by_id), f'Wrong reference owner: {pid}')
        all_reference_ids.update(by_id)
        cov = index_unique(covered[pid]['coverage'], 'reference_id', 'coverage reference')
        require(cov.keys() == by_id.keys(), f'Reference coverage ID set mismatch: {pid}')
        for rid, item in cov.items():
            require(item['validity'] in VALIDITIES and item['coverage'] in COVERAGES,
                    f'Invalid coverage label: {rid}')
            matches = item['match_ids']
            require(isinstance(matches, list) and len(matches) == len(set(matches)),
                    f'Duplicate or malformed match IDs: {rid}')
            require(all(m in owners and owners[m] == pid for m in matches),
                    f'Unknown/cross-paper match: {rid}')
            require((item['coverage'] == 'missing') == (len(matches) == 0),
                    f'Coverage/match inconsistency: {rid}')

    results = {}
    for domain_no, domain in enumerate(('iTE', 'TG')):
        rng = random.Random(SEED + domain_no)
        samples = [x for x in precision.values() if x['domain'] == domain]
        counts = Counter(judged[x['id']]['verdict'] for x in samples)
        weighted = {v: sum(x['weight'] for x in samples
                          if judged[x['id']]['verdict'] == v) for v in VERDICTS}
        by_paper = defaultdict(list)
        issue_counts, issue_weights = Counter(), Counter()
        for item in samples:
            by_paper[owners[item['id']]].append(item)
            for issue in set(judged[item['id']]['issues']):
                issue_counts[issue] += 1
                issue_weights[issue] += item['weight']
        def pstat(units):
            rows = [r for unit in units for r in unit]
            return ratio(sum(r['weight'] for r in rows if judged[r['id']]['verdict'] == 'supported'),
                         sum(r['weight'] for r in rows))
        precision_result = dict(strict=pstat(list(by_paper.values())),
            counts={v: counts[v] for v in VERDICTS}, weighted_counts=weighted,
            sample_relations=len(samples), sampled_papers=len(by_paper),
            weighted_denominator=sum(weighted.values()),
            ci95=bootstrap(list(by_paper.values()), pstat, rng, repetitions),
            issues=[dict(issue=k, count=issue_counts[k], weighted_count=issue_weights[k])
                    for k in sorted(issue_counts, key=lambda k: (-issue_counts[k], k))])
        papers = [x for x in recall.values() if x['domain'] == domain]
        recall_results = {}
        for scope in ('core', 'all'):
            units = []
            for paper in papers:
                pid = paper['id']
                kept = {r['relation_id'] for r in refs[pid]['records']
                        if scope == 'all' or r['scope'] in CORE}
                counts = Counter((x['validity'], x['coverage']) for x in covered[pid]['coverage']
                                 if x['reference_id'] in kept)
                units.append(dict(paper=paper, counts=counts))
            raw, weighted = Counter(), Counter()
            for unit in units:
                raw.update(unit['counts'])
                weighted.update({k: v * unit['paper']['weight'] for k, v in unit['counts'].items()})
            def rstat(draw, conservative=False):
                numerator = sum(u['paper']['weight'] * u['counts']['valid', 'complete'] for u in draw)
                denominator = sum(u['paper']['weight'] * sum(
                    n for (validity, _), n in u['counts'].items()
                    if validity == 'valid' or (conservative and validity == 'uncertain')) for u in draw)
                return ratio(numerator, denominator)
            table = lambda c: {v: {coverage: c[v, coverage] for coverage in COVERAGES}
                               for v in VALIDITIES}
            recall_results[scope] = dict(counts=table(raw), weighted_counts=table(weighted),
                papers_without_valid_reference=[u['paper']['id'] for u in units
                    if not sum(n for (v, _), n in u['counts'].items() if v == 'valid')],
                papers_without_any_reference=[u['paper']['id'] for u in units
                    if not sum(u['counts'].values())],
                valid_denominator=sum(weighted['valid', c] for c in COVERAGES),
                conservative_denominator=sum(weighted[v, c] for v in ('valid', 'uncertain') for c in COVERAGES),
                complete_numerator=weighted['valid', 'complete'],
                complete_valid=rstat(units), complete_conservative=rstat(units, True),
                ci95_valid=bootstrap(units, rstat, rng, repetitions, lambda u: u['paper']['stratum']),
                ci95_conservative=bootstrap(units, lambda draw: rstat(draw, True), rng,
                                           repetitions, lambda u: u['paper']['stratum']))
        challenge = [r for r in challenges if base[owners[r]]['domain'] == domain]
        challenge_counts = Counter(judged[r]['verdict'] for r in challenge)
        challenge_issues = Counter(issue for r in challenge for issue in set(judged[r]['issues']))
        eligible = [p for pid, p in base.items() if p['domain'] == domain and pid not in exclusions]
        results[domain] = dict(eligible_papers=len(eligible),
            eligible_relations=sum(len(p['records']) for p in eligible),
            precision=precision_result, recall=dict(sampled_papers=len(papers), **recall_results),
            challenge=dict(n=len(challenge), counts={v: challenge_counts[v] for v in VERDICTS},
                           issues=dict(challenge_issues), probability_estimate=False))
    return dict(validation='PASS', baseline='original frozen extraction; never repaired scores',
        excluded_historical_papers=len(exclusions), inference_population='Eligible papers not used in historical development/acceptance; not all 1,971 papers',
        semantic_authority='Astra model reference and judgments, not human gold standard',
        domains=results, bootstrap=dict(seed=SEED, repetitions=repetitions,
            method='Percentile 95% approximation; precision resamples observed paper clusters independently within domain with frozen relation-stratum N/n weights; recall resamples papers within domain/year strata with frozen paper N/n weights.',
            limitations='Not an exact design-based interval: precision sampling was stratified by relation, but its cluster bootstrap does not reconstruct that design. No finite-population correction. Singleton strata cannot estimate within-stratum variability. Intervals omit reference/judge model error and unobserved omissions. Null-denominator replicates excluded and counted.'),
        accounting='Precision retains partial/unsupported/out_of_scope/uncertain in denominator. Recall valid denominator excludes uncertain/out_of_scope; conservative denominator includes valid+uncertain but numerator only valid complete. Partial is never complete. Reference IDs count once; candidate IDs may legitimately support distinct reference claims. Challenge is separate.')


def load(directory):
    def read(path):
        return json.loads(path.read_text())
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    baseline_path = directory.parent / 'full_extraction_v1/extraction_all.json'
    freeze = read(directory / 'freeze.json')
    require(sha(baseline_path) == freeze['baseline_sha256'], 'Baseline hash mismatch')
    for name, digest in freeze['files'].items():
        require(sha(directory / name) == digest, f'Frozen input hash mismatch: {name}')
    reference_freeze = read(directory / 'reference_freeze.json')
    require(sha(directory / 'reference.json') == reference_freeze['sha256'], 'Reference hash mismatch')
    for jid, digest in reference_freeze['files'].items():
        require(sha(directory / 'runs' / jid / 'response.json') == digest,
                f'Reference response hash mismatch: {jid}')
    responses = {}
    provenance = {}
    for phase, key in (('precision', 'judgments'), ('coverage', 'papers')):
        jobs = read(directory / f'{phase}_jobs.json')
        index_unique(jobs, 'id', phase + ' job')
        responses[phase] = []
        for job in jobs:
            jid = job['id']
            response_path = directory / 'runs' / jid / 'response.json'
            success = read(response_path.parent / 'SUCCESS.json')
            digest = sha(response_path)
            require(digest == success['response_sha256'], f'Response hash mismatch: {jid}')
            require(sha(directory / 'jobs' / phase / (jid + '.json')) == job['input_sha256']
                    == success['input_sha256'], f'Job input hash mismatch: {jid}')
            provenance[jid] = digest
            responses[phase].extend(read(response_path)[key])
    exclusions_list = read(directory / 'historical_exclusions.json')['paper_ids']
    require(len(exclusions_list) == len(set(exclusions_list)), 'Duplicate historical exclusion')
    return (read(directory / 'selection.json'), read(baseline_path), read(directory / 'reference.json'),
            responses['precision'], responses['coverage'], set(exclusions_list)), dict(
                baseline_sha256=sha(baseline_path), reference_sha256=sha(directory / 'reference.json'),
                selection_sha256=sha(directory / 'selection.json'), response_sha256=provenance)


def self_test():
    import copy
    core = sorted(CORE)[0]
    base = [dict(paper_id=f'P{i}', domain='iTE', records=[dict(relation_id=f'P{i}:r1')]) for i in (1, 2)]
    selection = dict(precision=[dict(id=f'P{i}:r1', domain='iTE', stratum=str(i), N=w, n=1, weight=w)
                                for i, w in ((1, 2), (2, 6))],
                     recall=[dict(id=f'P{i}', domain='iTE', stratum='year', N=8, n=2, weight=4) for i in (1, 2)],
                     challenge=[])
    judgments = [dict(relation_id=f'P{i}:r1', verdict=v, issues=[]) for i, v in ((1, 'supported'), (2, 'uncertain'))]
    refs = [dict(paper_id='P1', records=[dict(relation_id='P1:g1', scope=core), dict(relation_id='P1:g2', scope=core)]),
            dict(paper_id='P2', records=[dict(relation_id='P2:g1', scope=core), dict(relation_id='P2:g2', scope='device')])]
    def cov(rid, validity, coverage, matches):
        return dict(reference_id=rid, validity=validity, coverage=coverage, match_ids=matches)
    covered = [dict(paper_id='P1', coverage=[cov('P1:g1', 'valid', 'complete', ['P1:r1']),
                                             cov('P1:g2', 'uncertain', 'complete', ['P1:r1'])]),
               dict(paper_id='P2', coverage=[cov('P2:g1', 'valid', 'partial', ['P2:r1']),
                                             cov('P2:g2', 'out_of_scope', 'missing', [])])]
    def run(c=covered):
        return compute(selection, base, refs, judgments, c, set(), repetitions=200, enforce_sizes=False)
    result = run()
    ite = result['domains']['iTE']
    require(ite['precision']['strict'] == .25, 'Synthetic precision weighting failed')
    require(ite['recall']['core']['complete_valid'] == .5, 'Valid recall denominator failed')
    require(ite['recall']['core']['complete_conservative'] == 1/3, 'Conservative denominator failed')
    require(ite['recall']['all']['weighted_counts']['out_of_scope']['missing'] == 4,
            'Out-of-scope accounting failed')
    require(result['domains']['TG']['recall']['all']['complete_valid'] is None, 'Empty denominator failed')
    require(result == run(), 'Fixed-seed bootstrap is not reproducible')
    weighted_selection = copy.deepcopy(selection)
    for i, row in enumerate(weighted_selection['recall']):
        row.update(stratum=str(i), N=(2, 6)[i], n=1, weight=(2, 6)[i])
    weighted_result = compute(weighted_selection, base, refs, judgments, covered, set(),
                              repetitions=200, enforce_sizes=False)
    weighted_recall = weighted_result['domains']['iTE']['recall']['core']
    require(weighted_recall['complete_valid'] == .25 and
            weighted_recall['complete_conservative'] == .2, 'Paper-weighted recall failed')
    for mutation in ('duplicate', 'cross_paper', 'unknown', 'missing_reference'):
        altered = copy.deepcopy(covered)
        if mutation == 'duplicate':
            altered[0]['coverage'].append(altered[0]['coverage'][0])
        elif mutation == 'cross_paper':
            altered[0]['coverage'][0]['match_ids'] = ['P2:r1']
        elif mutation == 'unknown':
            altered[0]['coverage'][0]['match_ids'] = ['bad']
        else:
            altered[0]['coverage'].pop()
        try:
            run(altered)
        except ValueError:
            pass
        else:
            raise ValueError('Validation failed to reject ' + mutation)
    return dict(self_test='PASS', checks=['weights', 'valid denominator', 'conservative denominator',
        'uncertain-complete excluded from numerator', 'out_of_scope separate', 'empty denominator',
        'paper-weighted recall', 'deterministic cluster bootstrap', 'duplicate reference rejection', 'cross-paper rejection',
        'unknown match rejection', 'missing reference rejection'], writes=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    else:
        data, provenance = load(args.directory)
        result = compute(*data, repetitions=args.bootstrap)
        result['provenance'] = provenance
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
