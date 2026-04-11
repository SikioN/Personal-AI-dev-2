"""
Benchmark QA pipeline on simple_questions_39_final_2025.xlsx

Usage:
    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --excel path/to/file.xlsx --top-k 12
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--excel', default='simple_questions_39_final_2025.xlsx')
    parser.add_argument('--top-k', type=int, default=12)
    parser.add_argument('--out', default='benchmark_results.csv')
    args = parser.parse_args()

    # ── Load engine ────────────────────────────────────────────────────────────
    print('Loading QA engine...')
    from src.bot.engine_loader import load_engine
    engine, _, _ = load_engine()
    print(f'Engine loaded: {type(engine).__name__}\n')

    # ── Load dataset ───────────────────────────────────────────────────────────
    try:
        import openpyxl
        import pandas as pd
        df = pd.read_excel(args.excel, engine='openpyxl')
    except ImportError:
        # Fallback: use csv if openpyxl not available
        import csv, pandas as pd
        print('[WARN] openpyxl not found, trying csv fallback...')
        df = pd.read_csv(args.excel)

    df.columns = ['question', 'expected', 'source_file',
                  'context_location', 'context', 'bot_answer_old', 'correct_old']
    df = df[['question', 'expected', 'source_file', 'correct_old']].dropna(subset=['question', 'expected'])
    df = df.reset_index(drop=True)
    print(f'Loaded {len(df)} questions from {args.excel}\n')

    # ── Run benchmark ──────────────────────────────────────────────────────────
    results = []
    n = len(df)

    for i, row in df.iterrows():
        q = str(row['question'])
        expected = str(row['expected'])
        print(f'[{i+1:2d}/{n}] {q[:70]}')

        try:
            answer, ranked = engine.ask_full(q, top_k=args.top_k)
            confidence = ranked[0]['confidence'] if ranked else 0.0
            top3 = [r['text'] for r in ranked[:3] if r.get('_used_by_llm')]
            if not top3:
                top3 = [r['text'] for r in ranked[:3]]
        except Exception as e:
            answer = f'ERROR: {e}'
            confidence = 0.0
            top3 = []

        # Auto-label
        exp_l = expected.strip().lower()
        got_l = str(answer).strip().lower()
        if got_l in ('unknown', 'null', 'none', ''):
            label = 'unknown'
        elif exp_l in got_l or got_l in exp_l:
            label = 'correct'
        else:
            exp_num = exp_l.replace(' ', '').replace(',', '.')
            got_num = got_l.replace(' ', '').replace(',', '.')
            label = 'correct' if exp_num and exp_num in got_num else 'wrong'

        icon = '✓' if label == 'correct' else ('?' if label == 'unknown' else '✗')
        print(f'       {icon} Expected: {expected!r:30s}  Got: {str(answer)!r:30s}  [{confidence:.2f}]')

        results.append({
            'question': q,
            'expected': expected,
            'bot_answer': str(answer),
            'label': label,
            'confidence': round(confidence, 3),
            'source_file': str(row['source_file']),
            'correct_old': str(row.get('correct_old', '')),
            'top3_facts': ' | '.join(top3),
        })

    # ── Summary ────────────────────────────────────────────────────────────────
    print('\n' + '=' * 70)
    n_correct = sum(1 for r in results if r['label'] == 'correct')
    n_unknown = sum(1 for r in results if r['label'] == 'unknown')
    n_wrong   = sum(1 for r in results if r['label'] == 'wrong')

    print(f'Total     : {n}')
    print(f'Correct   : {n_correct} ({n_correct/n*100:.1f}%)')
    print(f'Unknown   : {n_unknown} ({n_unknown/n*100:.1f}%)')
    print(f'Wrong     : {n_wrong   } ({n_wrong/n*100:.1f}%)')
    print(f'Baseline  : 34.2%')
    print(f'Delta     : {n_correct/n*100 - 34.2:+.1f}%')

    conf_correct = [r['confidence'] for r in results if r['label'] == 'correct']
    conf_wrong   = [r['confidence'] for r in results if r['label'] == 'wrong']
    if conf_correct and conf_wrong:
        avg_c = sum(conf_correct) / len(conf_correct)
        avg_w = sum(conf_wrong)   / len(conf_wrong)
        print(f'\nMean confidence — Correct: {avg_c:.3f}  |  Wrong: {avg_w:.3f}')
        if avg_w > avg_c:
            print('⚠ Miscalibration: higher confidence on wrong answers')
        else:
            print('✓ Calibration OK')

    print('\n=== Unknown answers ===')
    for r in results:
        if r['label'] == 'unknown':
            print(f"  Q: {r['question'][:70]}")
            print(f"     Expected: {r['expected']}  |  {r['source_file'][:40]}")

    print('\n=== Wrong answers ===')
    for r in results:
        if r['label'] == 'wrong':
            print(f"  Q: {r['question'][:70]}")
            print(f"     Expected: {r['expected']!r}  Got: {r['bot_answer']!r}  [{r['confidence']}]")

    # ── Save CSV ───────────────────────────────────────────────────────────────
    import csv
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f'\nResults saved to {args.out}')
    print('=' * 70)


if __name__ == '__main__':
    main()
