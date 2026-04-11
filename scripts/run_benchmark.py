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
    # Path overrides for sandbox / benchmark DB
    parser.add_argument('--kuzu-path',     default=None, help='Override KUZU_PATH')
    parser.add_argument('--chroma-nodes',  default=None, help='Override CHROMA_NODES_PATH')
    parser.add_argument('--chroma-quads',  default=None, help='Override CHROMA_QUADS_PATH')
    parser.add_argument('--tcomplex-ckpt', default=None, help='Override TCOMPLEX_CHECKPOINT')
    parser.add_argument('--tcomplex-data', default=None, help='Override TCOMPLEX_DATA_PATH')
    parser.add_argument('--max-facts',     type=int, default=None,
                        help='Max facts fed to LLM (overrides QAConfig.max_facts)')
    args = parser.parse_args()

    # ── Apply path overrides BEFORE load_engine() ─────────────────────────────
    # env must be set BEFORE load_engine() — QAConfig uses default_factory lambdas
    if args.kuzu_path:     os.environ['KUZU_PATH']           = args.kuzu_path
    if args.chroma_nodes:  os.environ['CHROMA_NODES_PATH']   = args.chroma_nodes
    if args.chroma_quads:  os.environ['CHROMA_QUADS_PATH']   = args.chroma_quads
    if args.tcomplex_ckpt: os.environ['TCOMPLEX_CHECKPOINT'] = args.tcomplex_ckpt
    if args.tcomplex_data: os.environ['TCOMPLEX_DATA_PATH']  = args.tcomplex_data
    if args.max_facts:     os.environ['QA_MAX_FACTS']        = str(args.max_facts)

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

            def _clean(text: str) -> str:
                """Remove wd_id noise so facts are readable."""
                import re as _re2
                text = _re2.sub(r'\s*\(wd_id:[^)]+\)', '', text)
                text = _re2.sub(r'\s*\(time_name:[^)]+\)', '', text)
                return text.strip()

            llm_facts = [r for r in ranked if r.get('_used_by_llm')]
            top3 = [_clean(r['text']) for r in llm_facts[:5]]
            if not top3:
                top3 = [_clean(r['text']) for r in ranked[:5]]
        except Exception as e:
            answer = f'ERROR: {e}'
            confidence = 0.0
            top3 = []

        # Auto-label
        import re as _re

        def _normalize_number(s: str) -> str:
            """Strip %, spaces (including thousands separators), normalize comma→dot."""
            s = _re.sub(r'[%\s]', '', s.strip().lower())
            return s.replace(',', '.')

        exp_l = expected.strip().lower()
        got_l = str(answer).strip().lower()
        if got_l in ('unknown', 'null', 'none', ''):
            label = 'unknown'
        elif exp_l in got_l or got_l in exp_l:
            label = 'correct'
        else:
            exp_n = _normalize_number(expected)
            got_n = _normalize_number(str(answer))
            label = 'correct' if exp_n and got_n and (exp_n in got_n or got_n in exp_n) else 'wrong'

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
            'top5_facts': ' | '.join(top3),
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
