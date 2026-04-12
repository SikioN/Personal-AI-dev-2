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
    df = df[['question', 'expected', 'source_file']].dropna(subset=['question', 'expected'])
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
            top3 = [_clean(r['text']) for r in llm_facts]
            if not top3:
                top3 = [_clean(r['text']) for r in ranked[:10]]
        except Exception as e:
            answer = f'ERROR: {e}'
            confidence = 0.0
            top3 = []

        print(f'       Expected: {expected!r:30s}  Got: {str(answer)!r:30s}  [{confidence:.2f}]')

        results.append({
            'question': q,
            'expected': expected,
            'bot_answer': str(answer),
            'label': '',
            'confidence': round(confidence, 3),
            'source_file': str(row['source_file']),
            'top5_facts': ' | '.join(top3),
        })

    # ── Save CSV ───────────────────────────────────────────────────────────────
    import csv
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f'\nResults saved to {args.out}')


if __name__ == '__main__':
    main()
