"""Format QAEngine outputs as Telegram-compatible Markdown."""
from typing import List, Dict


def format_facts(query: str, results: List[Dict], top_n: int = 5) -> str:
    """Format get_ranked_results() output as a numbered fact list."""
    if not results:
        return f"По запросу *{_esc(query)}* ничего не найдено в графе."

    lines = [f"Топ\\-{min(len(results), top_n)} фактов по запросу: _{_esc(query)}_\n"]
    for i, res in enumerate(results[:top_n], 1):
        q = res['quadruplet']
        subj = _esc(q.start_node.name)
        rel = _esc(q.relation.name)
        obj = _esc(q.end_node.name)
        time_str = _format_time(q)
        conf = res.get('confidence', 0.0)
        lines.append(f"{i}\\. \\[{conf:.2f}\\] {subj} → {rel} → {obj}{time_str}")

    return "\n".join(lines)


def format_answer(answer: str) -> str:
    """Wrap a plain-text QA answer for Telegram."""
    return f"*Ответ:*\n{_esc(answer)}"


def format_status(neo4j_ok: bool, chroma_ok: bool, llm_backend: str,
                  device: str, nodes: int, quads: int) -> str:
    neo4j_icon = "✅" if neo4j_ok else "❌"
    chroma_icon = "✅" if chroma_ok else "❌"
    return (
        f"*Статус системы*\n\n"
        f"{neo4j_icon} Neo4j\n"
        f"{chroma_icon} ChromaDB\n"
        f"🤖 LLM: `{_esc(llm_backend)}`\n"
        f"⚙️ Device: `{_esc(device)}`\n"
        f"📊 Узлов: `{nodes}` \\| Квадруплетов: `{quads}`"
    )


def format_settings(top_k: int, min_confidence: float) -> str:
    return (
        f"*Текущие настройки*\n\n"
        f"top\\_k: `{top_k}`\n"
        f"min\\_confidence: `{min_confidence:.2f}`"
    )


def _format_time(q) -> str:
    if q.time is None or q.time.name in ("Always", "", None):
        return ""
    return f" \\({_esc(q.time.name)}\\)"


def _esc(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    if not text:
        return ""
    text = str(text)
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text
