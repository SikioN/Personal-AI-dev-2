#!/usr/bin/env python3
"""
diagnose_unknown.py — Check whether expected answers exist in KuzuDB.

For each question labeled 'unknown' or 'wrong' in benchmark_results.csv,
searches KuzuDB directly for key terms from the expected answer.

Result: prints a table showing FOUND / NOT FOUND for each expected answer.
This determines whether the problem is ingestion (facts missing from KG)
or retrieval (facts exist but aren't found by the QA pipeline).

Usage:
    python scripts/diagnose_unknown.py
    python scripts/diagnose_unknown.py --csv benchmark_results.csv --kuzu-path data/kuzu_db/graph.db
"""
import argparse
import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()


def extract_key_terms(text: str) -> list[str]:
    """Extract numbers and long words from expected answer for KuzuDB search."""
    text = text.strip()
    terms = []
    # All numbers (including decimals and ranges)
    terms += re.findall(r'\d+(?:[.,]\d+)?', text)
    # Long words (5+ chars) excluding common stopwords
    _STOP = {'процентов', 'которых', 'миллионов', 'миллиардов', 'триллионов',
              'долларов', 'рублей', 'около', 'более', 'менее', 'свыше',
              'billion', 'million', 'percent', 'dollars', 'увеличение',
              'снижение', 'является', 'составляет', 'составил'}
    words = re.findall(r'[а-яёА-ЯЁa-zA-Z]{5,}', text)
    terms += [w.lower() for w in words if w.lower() not in _STOP]
    return terms[:5]  # top-5 most specific terms


def search_kuzu(conn, term: str, limit: int = 3) -> list[str]:
    """Search all node tables for a term."""
    results = []
    for table in ('object', 'hyper', 'episodic'):
        try:
            res = conn.execute(
                f"MATCH (n:{table}) WHERE n.name CONTAINS $term RETURN n.name LIMIT {limit}",
                parameters={'term': term}
            )
            while res.has_next():
                row = res.get_next()
                results.append(row[0])
        except Exception:
            pass
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='benchmark_results.csv')
    parser.add_argument('--kuzu-path', default=os.environ.get('KUZU_PATH', 'data/kuzu_db/graph.db'))
    parser.add_argument('--labels', default='unknown,wrong', help='Labels to diagnose')
    args = parser.parse_args()

    import kuzu

    print(f'Opening KuzuDB: {args.kuzu_path}')
    db = kuzu.Database(args.kuzu_path)
    conn = kuzu.Connection(db)

    rows = list(csv.DictReader(open(args.csv, encoding='utf-8')))
    target_labels = set(args.labels.split(','))
    target_rows = [r for r in rows if r['label'] in target_labels]

    print(f'\nDiagnosing {len(target_rows)} rows (labels: {args.labels})\n')
    print(f'{"#":<4} {"Label":<8} {"Expected":<45} {"Found in KG?":<14} {"Matched nodes"}')
    print('-' * 120)

    found_count = 0
    not_found_count = 0
    results_table = []

    for i, row in enumerate(target_rows):
        expected = row['expected'].strip()
        question = row['question'][:60]
        label = row['label']

        terms = extract_key_terms(expected)
        if not terms:
            status = 'NO_TERMS'
            matches = []
        else:
            matches = []
            for term in terms:
                hits = search_kuzu(conn, term)
                if hits:
                    matches.extend(hits)
                    break  # one term found is enough

            if matches:
                status = 'FOUND'
                found_count += 1
            else:
                status = 'NOT_FOUND'
                not_found_count += 1

        match_str = ' | '.join(m[:40] for m in matches[:2]) if matches else '—'
        print(f'{i+1:<4} {label:<8} {expected[:44]:<45} {status:<14} {match_str}')
        results_table.append({
            'question': question,
            'expected': expected,
            'label': label,
            'status': status,
            'search_terms': ', '.join(terms),
            'matched_nodes': ' | '.join(matches[:2]),
        })

    total = found_count + not_found_count
    print('\n' + '=' * 70)
    print(f'FOUND in KG    : {found_count}/{total} ({found_count/max(total,1)*100:.1f}%)')
    print(f'NOT FOUND in KG: {not_found_count}/{total} ({not_found_count/max(total,1)*100:.1f}%)')
    print()
    if not_found_count / max(total, 1) > 0.6:
        print('DIAGNOSIS: >60% facts MISSING from KG.')
        print('  → Fix ingestion: re-extract source documents with better LLM prompt.')
    else:
        print('DIAGNOSIS: Most facts ARE in KG but retrieval fails to surface them.')
        print('  → Fix retrieval: increase search_k_floor, top_k, and ctx window.')
    print('=' * 70)

    # Save detailed CSV
    out_path = 'diagnose_results.csv'
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results_table[0].keys())
        writer.writeheader()
        writer.writerows(results_table)
    print(f'\nDetailed results saved to {out_path}')


if __name__ == '__main__':
    main()
