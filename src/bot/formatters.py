"""Format QAEngine outputs as Telegram-compatible Markdown."""
from typing import List, Dict


def format_facts(query: str, results: List[Dict], top_n: int = 5) -> str:
    """Format get_ranked_results() output as a numbered fact list."""
    if not results:
        return f"По запросу *{_esc(query)}* ничего не найдено в графе\\."

    lines = [f"Топ\\-{min(len(results), top_n)} фактов по запросу: _{_esc(query)}_\n"]
    for i, res in enumerate(results[:top_n], 1):
        q = res['quadruplet']
        # In-memory mode returns plain strings, not Quadruplet objects
        if isinstance(q, str):
            conf = res.get('confidence', 0.0)
            conf_str = _esc(f"{conf:.2f}")
            lines.append(f"{i}\\. \\[{conf_str}\\] {_esc(q)}")
            continue
        subj = _esc(q.start_node.name)
        rel = _esc(q.relation.name)
        obj = _esc(q.end_node.name)
        time_str = _format_time(q)
        conf = res.get('confidence', 0.0)
        conf_str = _esc(f"{conf:.2f}")
        lines.append(f"{i}\\. \\[{conf_str}\\] {subj} → {rel} → {obj}{time_str}")

    return "\n".join(lines)


def format_answer(answer: str) -> str:
    """Wrap a plain-text QA answer for Telegram."""
    return f"*Ответ:*\n{_esc(answer)}"


def format_ask_with_ranked(answer: str, results: List[Dict], top_k: int = 5) -> str:
    """Bold answer at top + numbered ranked facts with confidence scores."""
    top_conf = results[0].get('confidence', 0.0) if results else 0.0
    lines = [f"*Ответ:* {_esc(answer)} \\[{_esc(f'{top_conf:.2f}')}\\]\n"]
    if results:
        lines.append(f"_Топ\\-{min(len(results), top_k)} фактов:_")
        for i, res in enumerate(results[:top_k], 1):
            q = res['quadruplet']
            conf = res.get('confidence', 0.0)
            conf_str = _esc(f"{conf:.2f}")
            if isinstance(q, str):
                lines.append(f"{i}\\. \\[{conf_str}\\] {_esc(q)}")
            else:
                subj = _esc(q.start_node.name)
                rel = _esc(q.relation.name)
                obj = _esc(q.end_node.name)
                time_str = _format_time(q)
                lines.append(f"{i}\\. \\[{conf_str}\\] {subj} → {rel} → {obj}{time_str}")
    return "\n".join(lines)


from typing import List, Dict, Optional

def format_status(neo4j_ok: Optional[bool], chroma_ok: Optional[bool], llm_backend: str,
                  device: str, nodes: int, quads: int,
                  ingested: int = 0, mode: str = "production",
                  tcomplex_ok: Optional[bool] = None,
                  graph_backend: str = "neo4j",
                  facts_since_last_retrain: int = 0) -> str:
    neo4j_icon  = "[OK]"  if neo4j_ok  is True  else ("[ERR]" if neo4j_ok  is False else "[N/A]")
    chroma_icon = "[OK]"  if chroma_ok is True  else ("[ERR]" if chroma_ok is False else "[N/A]")
    tc_icon     = "[OK]"  if tcomplex_ok is True else ("[ERR]" if tcomplex_ok is False else "[N/A]")
    if graph_backend == "kuzu":
        neo4j_label = "KuzuDB \\(N/A\\)" if neo4j_ok is None else "KuzuDB"
    else:
        neo4j_label = "Neo4j \\(N/A\\)" if neo4j_ok is None else "Neo4j"
    chroma_label = "ChromaDB \\(N/A\\)" if chroma_ok is None else "ChromaDB"
    tc_label     = "TComplEx \\(N/A\\)" if tcomplex_ok is None else "TComplEx"
    ingested_line = f"\nIngested: `{ingested}`" if ingested > 0 else ""
    retrain_line = ""
    if facts_since_last_retrain > 0:
        retrain_line = (
            f"\n[WARN] С последнего retrain: `{facts_since_last_retrain}` фактов "
            f"\\— рекомендуется /retrain"
        )
    return (
        f"*Статус системы*\n\n"
        f"Mode: `{_esc(mode)}`\n"
        f"{neo4j_icon} {neo4j_label}\n"
        f"{chroma_icon} {chroma_label}\n"
        f"{tc_icon} {tc_label}\n"
        f"LLM: `{_esc(llm_backend)}`\n"
        f"Device: `{_esc(device)}`\n"
        f"Graph: `{nodes}` \\| `{quads}` квадруплетов"
        f"{ingested_line}"
        f"{retrain_line}"
    )


def format_settings(top_k: int, min_confidence: float) -> str:
    conf_str = _esc(f"{min_confidence:.2f}")
    return (
        f"*Текущие настройки*\n\n"
        f"top\\_k: `{top_k}`\n"
        f"min\\_confidence: `{conf_str}`"
    )


def format_ingest_result(stats: dict, use_inmemory: bool) -> str:
    """Format DocIngestionService.ingest_directory() result for Telegram."""
    added = stats.get("added", 0)
    skipped = stats.get("skipped", 0)
    errors = stats.get("errors", 0)
    files_processed = stats.get("files_processed", 0)
    files_skipped = stats.get("files_skipped", 0)
    facts_since_retrain = stats.get("facts_since_last_retrain", 0)
    lines = [
        "*Результат обработки документов*\n",
        f"[OK] Добавлено фактов: `{added}`",
        f"[FILE] Файлов обработано: `{files_processed}` \\(пропущено: `{files_skipped}`\\)",
    ]
    if skipped:
        lines.append(f"[SKIP] Дубликатов пропущено: `{skipped}`")
    if errors:
        lines.append(f"[WARN] Ошибок: `{errors}`")
    if facts_since_retrain > 0:
        lines.append(
            f"\n[WARN] С последнего retrain: `{facts_since_retrain}` фактов "
            f"\\— рекомендуется /retrain"
        )
    if use_inmemory:
        lines.append("\n[INFO] Режим in\\-memory: данные сохранены в памяти \\(не в Neo4j\\)")
    return "\n".join(lines)


def format_ingest_sample(quads: list, max_n: int = 5) -> str:
    """Format a sample of extracted quadruplets for Telegram display."""
    lines = []
    for i, q in enumerate(quads[:max_n], 1):
        s = q.get('s', {}).get('name', '?')
        p = q.get('r', {}).get('name', '?')
        o = q.get('o', {}).get('name', '?')
        t_prop = q.get('t', {}).get('prop', {})
        ts, te = t_prop.get('start', ''), t_prop.get('end', '')
        t_str = f"{ts}–{te}" if ts and te else (ts or te or 'н/д')
        lines.append(f"{i}\\. {_esc(s)} → {_esc(p)} → {_esc(o)} \\({_esc(t_str)}\\)")
    return '\n'.join(lines)


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
