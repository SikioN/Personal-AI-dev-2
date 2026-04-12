"""
Interactive QA console — ask questions against the same KG used in benchmarks.

Usage:
    python scripts/qa_chat.py
    python scripts/qa_chat.py --kuzu-path /path/to/kuzu_db \\
        --chroma-nodes /path/to/chroma/nodes/default \\
        --chroma-quads /path/to/chroma/quads/default \\
        --tcomplex-ckpt /path/to/tcomplex.ckpt \\
        --tcomplex-data /path/to/tcomplex

Type 'exit' / 'quit' / 'q' to stop.
"""
import sys
import os
import re
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# ── ANSI colors ────────────────────────────────────────────────────────────────
RESET        = '\033[0m'
BOLD         = '\033[1m'
DIM          = '\033[2m'
CYAN         = '\033[36m'
BRIGHT_CYAN  = '\033[96m'
GREEN        = '\033[32m'
BRIGHT_GREEN = '\033[92m'
YELLOW       = '\033[33m'
GREY         = '\033[90m'
RED          = '\033[31m'
WHITE        = '\033[97m'
BRIGHT_BLUE  = '\033[94m'
MAGENTA      = '\033[35m'

_W = 72
SEP  = GREY + '─' * _W + RESET
DSEP = GREY + '═' * _W + RESET


def _clean(text: str) -> str:
    """Strip internal KG noise from a fact string."""
    text = re.sub(r'\s*\(wd_id:[^)]+\)', '', text)
    text = re.sub(r'\s*\(time_name:[^)]+\)', '', text)
    return text.strip()


def _conf_color(conf: float) -> str:
    if conf >= 0.80:
        return BRIGHT_GREEN
    if conf >= 0.55:
        return YELLOW
    return GREY


def print_header(engine_name: str) -> None:
    print()
    print(DSEP)
    print(BOLD + BRIGHT_CYAN + '  KG QA Console' + RESET)
    print(GREY + f'  Engine: {engine_name}' + RESET)
    print(DSEP)
    print()
    print(GREY + "  Type your question and press Enter." + RESET)
    print(GREY + "  Type 'exit' / 'quit' / 'q' to stop." + RESET)
    print()


def ask_and_print(engine, question: str, top_k: int) -> None:
    print()
    print(SEP)

    try:
        answer, ranked = engine.ask_full(question, top_k=top_k)
    except Exception as exc:
        print(RED + f'  Error: {exc}' + RESET)
        print(SEP)
        return

    # ── Answer ─────────────────────────────────────────────────────────────────
    print()
    print(BOLD + BRIGHT_GREEN + '  Answer' + RESET)
    answer_str = str(answer) if answer else 'Unknown'
    for line in answer_str.splitlines():
        print(BOLD + WHITE + f'    {line}' + RESET)
    print()

    # ── Facts passed to LLM ───────────────────────────────────────────────────
    llm_facts = [r for r in ranked if r.get('_used_by_llm')]
    fallback = False
    if not llm_facts:
        llm_facts = ranked[:10]
        fallback = True

    label = (
        f'  Top-{len(llm_facts)} retrieved facts (LLM flag not set):'
        if fallback
        else f'  Facts passed to LLM  ({len(llm_facts)} facts):'
    )
    print(BOLD + CYAN + label + RESET)
    print()

    for idx, r in enumerate(llm_facts, 1):
        conf = r.get('confidence', 0.0)
        text = _clean(r.get('text', ''))
        cc = _conf_color(conf)
        print(
            f'  {GREY}{idx:2d}.{RESET}  '
            f'{GREY}[{cc}{conf:.2f}{GREY}]{RESET}  '
            f'{DIM}{text}{RESET}'
        )

    print()
    print(SEP)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Interactive KG QA console',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('--top-k',         type=int, default=20)
    parser.add_argument('--max-facts',     type=int, default=20,
                        help='Max facts fed to LLM (overrides QAConfig.max_facts)')
    parser.add_argument('--kuzu-path',     default=None, help='Override KUZU_PATH')
    parser.add_argument('--chroma-nodes',  default=None, help='Override CHROMA_NODES_PATH')
    parser.add_argument('--chroma-quads',  default=None, help='Override CHROMA_QUADS_PATH')
    parser.add_argument('--tcomplex-ckpt', default=None, help='Override TCOMPLEX_CHECKPOINT')
    parser.add_argument('--tcomplex-data', default=None, help='Override TCOMPLEX_DATA_PATH')
    args = parser.parse_args()

    # Apply path overrides before load_engine() reads env vars
    if args.kuzu_path:     os.environ['KUZU_PATH']           = args.kuzu_path
    if args.chroma_nodes:  os.environ['CHROMA_NODES_PATH']   = args.chroma_nodes
    if args.chroma_quads:  os.environ['CHROMA_QUADS_PATH']   = args.chroma_quads
    if args.tcomplex_ckpt: os.environ['TCOMPLEX_CHECKPOINT'] = args.tcomplex_ckpt
    if args.tcomplex_data: os.environ['TCOMPLEX_DATA_PATH']  = args.tcomplex_data
    if args.max_facts:     os.environ['QA_MAX_FACTS']        = str(args.max_facts)

    print(GREY + '\nLoading QA engine...' + RESET)
    from src.bot.engine_loader import load_engine
    engine, _, _ = load_engine()

    print_header(type(engine).__name__)

    while True:
        try:
            raw = input(BOLD + BRIGHT_BLUE + 'Question: ' + RESET)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        question = raw.strip()
        if not question:
            continue
        if question.lower() in ('exit', 'quit', 'q', 'выход'):
            break

        ask_and_print(engine, question, top_k=args.top_k)


if __name__ == '__main__':
    main()
