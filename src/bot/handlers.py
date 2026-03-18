"""aiogram 3.x handlers for Personal-AI KG QA Telegram bot."""
import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BufferedInputFile

from src.bot.formatters import (
    format_facts, format_answer, format_ask_with_ranked, format_status, format_settings,
    format_ingest_result, _esc,
)
from src.bot.graph_renderer import render_subgraph

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router = Router()

# Per-chat settings (in-memory; reset on bot restart)
_chat_settings: dict[int, dict] = {}

# 5.4: per-chat cooldown — prevents a single user from monopolising all semaphore slots
_last_ask: dict[int, float] = {}
_ASK_COOLDOWN_SEC = 5.0

# 5.4: rate-limit — max 3 concurrent heavy-compute requests (ask/facts/graph)
_ask_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _ask_semaphore
    if _ask_semaphore is None:
        _ask_semaphore = asyncio.Semaphore(3)
    return _ask_semaphore


HELP_TEXT = (
    "*Personal\\-AI KG QA Navigator*\n\n"
    "*/ask* `<вопрос>` — полный 7\\-стадийный пайплайн → текстовый ответ\n"
    "*/facts* `<вопрос>` — полная отладочная трассировка пайплайна\n"
    "*/graph* `<вопрос>` — 1\\-hop подграф → PNG\n"
    "*/settings* — текущие настройки\n"
    "*/set top\\_k N* — изменить top\\_k \\(1–15\\)\n"
    "*/set confidence X* — мин\\. confidence \\(0\\.0–1\\.0\\)\n"
    "*/status* — статус системы\n"
    "*/ingest* — извлечь факты из документов в extract/new\\_docs/\n"
    "*/retrain* — переобучить TComplEx \\(только production\\)\n"
    "*/help* — этот список\n\n"
    "Для загрузки документа отправьте файл \\(PDF, DOCX, PPTX, TXT\\)\\."
)

WELCOME_TEXT = (
    "Привет\\! Я KG QA Navigator — отвечаю на вопросы по графу знаний\\.\n\n"
    + HELP_TEXT
)


def _get_settings(chat_id: int) -> dict:
    if chat_id not in _chat_settings:
        _chat_settings[chat_id] = {'top_k': 5, 'min_confidence': 0.3}
    return _chat_settings[chat_id]


def _get_engine_and_navigator():
    """Import here to avoid circular imports at module load time."""
    from src.bot.engine_loader import load_engine
    return load_engine()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, parse_mode="MarkdownV2")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="MarkdownV2")


@router.message(Command("status"))
async def cmd_status(message: Message):
    await message.answer("Проверяю статус системы...")
    try:
        engine, _, kg_model = await asyncio.to_thread(_get_engine_and_navigator)
    except Exception as e:
        await message.answer(f"Ошибка инициализации движка: {_esc(str(e))}",
                             parse_mode="MarkdownV2")
        return

    from src.utils.device_utils import get_device
    device = get_device(verbose=False).upper()
    llm_backend = os.environ.get("LLM_BACKEND", "ollama")

    e_status = {}
    try:
        e_status = engine.status()
    except Exception:
        pass
    ingested = e_status.get("ingested_facts", 0)
    graph_backend = os.environ.get("GRAPH_BACKEND", "neo4j")

    if kg_model is None:
        # In-memory mode — Neo4j/ChromaDB deliberately not used
        nodes = e_status.get("nodes", 0)
        quads = e_status.get("quadruplets", len(getattr(engine, "raw_quads", [])))
        tcomplex_ok = e_status.get("tcomplex_loaded")
        text = format_status(None, None, llm_backend, device, nodes, quads, ingested, "in-memory", tcomplex_ok, graph_backend)
    else:
        neo4j_ok = False
        chroma_ok = False
        nodes = 0
        quads = 0
        try:
            stats = await asyncio.to_thread(kg_model.count_items)
            nodes = stats.get('graph_info', {}).get('nodes', 0)
            quads = stats.get('graph_info', {}).get('quadruplets', 0)
            neo4j_ok = True
        except Exception:
            pass
        try:
            await asyncio.to_thread(kg_model.embeddings_struct.vectordbs['nodes'].count_items)
            chroma_ok = True
        except Exception:
            pass
        tcomplex_ok = e_status.get("tcomplex_loaded")
        text = format_status(neo4j_ok, chroma_ok, llm_backend, device, nodes, quads, ingested, "production", tcomplex_ok, graph_backend)

    await message.answer(text, parse_mode="MarkdownV2")


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    s = _get_settings(message.chat.id)
    await message.answer(
        format_settings(s['top_k'], s['min_confidence']),
        parse_mode="MarkdownV2"
    )


@router.message(Command("set"))
async def cmd_set(message: Message):
    """Parse /set top_k N or /set confidence X."""
    args = (message.text or "").split()[1:]  # drop "/set"
    if len(args) < 2:
        await message.answer("Использование: /set top\\_k N  или  /set confidence X",
                             parse_mode="MarkdownV2")
        return

    key, val_str = args[0].lower(), args[1]
    s = _get_settings(message.chat.id)
    try:
        if key in ("top_k", "top-k", "topk"):
            v = int(val_str)
            if not 1 <= v <= 15:
                raise ValueError
            s['top_k'] = v
            await message.answer(f"top\\_k установлен в `{v}`", parse_mode="MarkdownV2")
        elif key in ("confidence", "min_confidence"):
            v = float(val_str)
            if not 0.0 <= v <= 1.0:
                raise ValueError
            s['min_confidence'] = v
            v_esc = _esc(f"{v:.2f}")
            await message.answer(f"min\\_confidence установлен в `{v_esc}`",
                                 parse_mode="MarkdownV2")
        else:
            await message.answer(f"Неизвестный параметр: `{_esc(key)}`",
                                 parse_mode="MarkdownV2")
    except ValueError:
        await message.answer("Неверное значение\\. top\\_k: 1–15, confidence: 0\\.0–1\\.0",
                             parse_mode="MarkdownV2")


@router.message(Command("ask"))
async def cmd_ask(message: Message):
    query = _extract_query(message.text, "/ask")
    if not query:
        await message.answer("Использование: /ask <вопрос>")
        return

    now = time.monotonic()
    if now - _last_ask.get(message.chat.id, 0) < _ASK_COOLDOWN_SEC:
        await message.answer("Слишком быстро. Подождите несколько секунд.")
        return
    _last_ask[message.chat.id] = now

    await message.answer("Анализирую граф, подождите...")
    # 5.4: rate limiting
    s = _get_settings(message.chat.id)
    async with _get_semaphore():
        try:
            engine, _, _ = await asyncio.to_thread(_get_engine_and_navigator)
            results = await asyncio.to_thread(engine.get_ranked_results, query, s['top_k'])
            answer = await asyncio.to_thread(engine.ask, query, s['top_k'])
        except Exception as e:
            logger.exception("Error in /ask")
            await message.answer(f"Ошибка: {_esc(str(e))}", parse_mode="MarkdownV2")
            return

    # 5.1: check for None answer (LLM failure reported from GenerationStage)
    if answer is None:
        await message.answer("Произошла ошибка при обращении к LLM\\. Попробуйте позже\\.",
                             parse_mode="MarkdownV2")
        return

    await message.answer(format_ask_with_ranked(answer, results, s['top_k']), parse_mode="MarkdownV2")


async def _run_debug_trace(message: Message) -> None:
    """Shared logic for /facts and /dbg: captured stdout of ask(debug=True)."""
    import io
    import html

    query = ' '.join(message.text.split()[1:]).strip()
    if not query:
        await message.answer("Использование: /facts <вопрос>")
        return

    now = time.monotonic()
    if now - _last_ask.get(message.chat.id, 0) < _ASK_COOLDOWN_SEC:
        await message.answer("Слишком быстро. Подождите несколько секунд.")
        return
    _last_ask[message.chat.id] = now

    await message.answer("Запускаю отладочную трассировку...")

    def _capture_debug(engine, q):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            engine.ask(q, debug=True)
        finally:
            sys.stdout = old
        return buf.getvalue()

    async with _get_semaphore():
        try:
            engine, _, _ = await asyncio.to_thread(_get_engine_and_navigator)
            out = await asyncio.to_thread(_capture_debug, engine, query)
        except Exception as e:
            logger.exception("Error in debug trace")
            await message.answer(f"Ошибка: {e}")
            return

    if len(out) > 4000:
        out = out[:2000] + "\n\n... [TRUNCATED] ...\n\n" + out[-1500:]
    await message.answer(f"<pre>{html.escape(out)}</pre>", parse_mode="HTML")


@router.message(Command("facts"))
async def cmd_facts(message: Message):
    await _run_debug_trace(message)


@router.message(Command("dbg"))
async def cmd_dbg(message: Message):
    await _run_debug_trace(message)



@router.message(Command("graph"))
async def cmd_graph(message: Message):
    query = _extract_query(message.text, "/graph")
    if not query:
        await message.answer("Использование: /graph <вопрос>")
        return

    now = time.monotonic()
    if now - _last_ask.get(message.chat.id, 0) < _ASK_COOLDOWN_SEC:
        await message.answer("Слишком быстро. Подождите несколько секунд.")
        return
    _last_ask[message.chat.id] = now

    s = _get_settings(message.chat.id)
    await message.answer("Строю подграф...")
    # 5.4: rate limiting
    async with _get_semaphore():
        try:
            engine, navigator, _ = await asyncio.to_thread(_get_engine_and_navigator)
            results = await asyncio.to_thread(engine.get_ranked_results, query, s['top_k'])
        except Exception as e:
            logger.exception("Error fetching results for /graph")
            await message.answer(f"Ошибка: {_esc(str(e))}", parse_mode="MarkdownV2")
            return

    if not results:
        await message.answer("Нет результатов для построения графа.")
        return

    # results from QAEngine are List[Dict] with 'quadruplet' as Quadruplet object;
    # from SimpleInMemoryEngine they are strings — skip node extraction gracefully
    from collections import Counter
    entity_counts: Counter = Counter()
    for r in results:
        q = r.get('quadruplet')
        if q and hasattr(q, 'start_node') and hasattr(q, 'end_node'):
            entity_counts[q.start_node.id] += 1
            entity_counts[q.end_node.id] += 1

    if not entity_counts:
        await message.answer("Не удалось извлечь узлы из результатов\\.", parse_mode="MarkdownV2")
        return

    center_id = entity_counts.most_common(1)[0][0]

    center_name = None
    for r in results:
        q = r.get('quadruplet')
        if q and hasattr(q, 'start_node') and hasattr(q, 'end_node'):
            if q.start_node.id == center_id:
                center_name = q.start_node.name
                break
            if q.end_node.id == center_id:
                center_name = q.end_node.name
                break

    try:
        quadruplets = await asyncio.to_thread(navigator.get_neighborhood, [center_id], 1)
        png_bytes = await asyncio.to_thread(render_subgraph, quadruplets, center_name)
    except Exception as e:
        logger.exception("Error rendering graph")
        await message.answer(f"Ошибка рендеринга: {_esc(str(e))}", parse_mode="MarkdownV2")
        return

    photo = BufferedInputFile(png_bytes.read(), filename="graph.png")
    await message.answer_photo(photo, caption=f"1-hop подграф для: {query[:100]}")


@router.message(Command("ingest"))
async def cmd_ingest(message: Message):
    now = time.monotonic()
    if now - _last_ask.get(message.chat.id, 0) < _ASK_COOLDOWN_SEC:
        await message.answer("Слишком быстро. Подождите несколько секунд.")
        return
    _last_ask[message.chat.id] = now

    args = (message.text or "").strip().split()
    force_reprocess = len(args) > 1 and args[1].lower() == "force"

    status_msg = await message.answer(
        "Подготовка к извлечению (принудительная переработка)..." if force_reprocess
        else "Подготовка к извлечению..."
    )
    loop = asyncio.get_event_loop()

    def sync_progress(text: str):
        async def _do() -> None:
            await status_msg.edit_text(text)
        asyncio.run_coroutine_threadsafe(_do(), loop)

    async with _get_semaphore():
        try:
            engine, _, kg_model = await asyncio.to_thread(_get_engine_and_navigator)
            use_inmemory = os.environ.get("USE_INMEMORY", "true").lower() in ("1", "true", "yes")
            from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
            service = DocIngestionService(
                kg_model=kg_model if not use_inmemory else None,
                inmemory_engine=engine if use_inmemory else None,
            )
            input_dir = os.path.join(ROOT_DIR, "extract", "new_docs")
            os.makedirs(input_dir, exist_ok=True)
            stats = await asyncio.to_thread(
                service.ingest_directory,
                input_dir,
                False,
                None,
                force_reprocess,
                sync_progress,
            )
        except Exception as e:
            logger.exception("Error in /ingest")
            await status_msg.edit_text(f"Ошибка: {_esc(str(e)[:200])}", parse_mode="MarkdownV2")
            return
    use_inmemory = os.environ.get("USE_INMEMORY", "true").lower() in ("1", "true", "yes")
    await status_msg.edit_text(
        format_ingest_result(stats, use_inmemory), parse_mode="MarkdownV2"
    )


@router.message(Command("retrain"))
async def cmd_retrain(message: Message):
    use_inmemory = os.environ.get("USE_INMEMORY", "true").lower() in ("1", "true", "yes")
    if use_inmemory:
        await message.answer(
            "TComplEx недоступен в режиме in\\-memory\\.", parse_mode="MarkdownV2"
        )
        return
    tkbc_dir = os.environ.get("TKBC_DIR", "")
    if not tkbc_dir or not os.path.isdir(tkbc_dir):
        await message.answer(
            "TKBC\\_DIR не задан или не существует\\.", parse_mode="MarkdownV2"
        )
        return

    status_msg = await message.answer("Запускаю переобучение TComplEx...")
    async with _get_semaphore():
        try:
            checkpoint_out = os.path.join(tkbc_dir, "tcomplex_retrained.ckpt")
            await asyncio.to_thread(
                subprocess.run,
                [
                    sys.executable,
                    os.path.join(ROOT_DIR, "scripts", "retrain_tcomplex.py"),
                    "--tkbc-dir", tkbc_dir,
                    "--checkpoint-out", checkpoint_out,
                ],
                check=True,
            )
            engine, _, _ = await asyncio.to_thread(_get_engine_and_navigator)
            if hasattr(engine, "hot_reload_scorer"):
                await asyncio.to_thread(engine.hot_reload_scorer, checkpoint_out)
        except Exception as e:
            logger.exception("Error in /retrain")
            await status_msg.edit_text(f"Ошибка переобучения: {_esc(str(e)[:200])}")
            return
    await status_msg.edit_text(
        "TComplEx переобучен и перезагружен\\.", parse_mode="MarkdownV2"
    )


_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}


@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    doc = message.document
    ext = Path(doc.file_name or "").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        await message.answer(
            f"Формат не поддерживается\\. Допустимы: PDF, DOCX, PPTX, TXT\\.",
            parse_mode="MarkdownV2",
        )
        return

    save_dir = os.path.join(ROOT_DIR, "extract", "new_docs")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, doc.file_name)

    try:
        await bot.download(doc, destination=save_path)
        fname_esc = _esc(doc.file_name)
        loop = asyncio.get_running_loop()  # capture before entering thread

        status_msg = await message.answer(
            f"Файл *{fname_esc}* загружен\\. Начинаю извлечение фактов\\.\\.\\.",
            parse_mode="MarkdownV2",
        )

        try:
            from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
            engine, _, kg_model = await asyncio.to_thread(_get_engine_and_navigator)
            use_inmemory = os.environ.get("USE_INMEMORY", "true").lower() in ("1", "true", "yes")

            service = DocIngestionService(
                kg_model=kg_model if not use_inmemory else None,
                inmemory_engine=engine if use_inmemory else None,
            )

            def sync_progress(text: str):
                asyncio.run_coroutine_threadsafe(
                    status_msg.edit_text(_esc(text), parse_mode="MarkdownV2"),
                    loop,
                )

            async with _get_semaphore():
                res = await asyncio.to_thread(
                    service.ingest_single_file, save_path, None, sync_progress
                )

            added = res["added"]
            sample_quads = res.get("quadruplets", [])

            if added == 0 and res["errors"] == 0:
                await status_msg.edit_text(
                    f"В файле *{fname_esc}* не найдено новых фактов\\.",
                    parse_mode="MarkdownV2",
                )
                return

            summary = (
                f"Обработка *{fname_esc}* завершена\\!\n\n"
                f"Добавлено фактов: `{added}`\n"
                f"Ошибок: `{res['errors']}`"
            )
            if sample_quads:
                from src.bot.formatters import format_ingest_sample
                sample_text = format_ingest_sample(sample_quads, max_n=5)
                total_str = f" \\(показаны 5 из {len(sample_quads)}\\)" if len(sample_quads) > 5 else ""
                summary += f"\n\n*Примеры извлечённых фактов*{total_str}:\n{sample_text}"

            await status_msg.edit_text(summary, parse_mode="MarkdownV2")
        except Exception as ingest_err:
            logger.exception("In-flight ingestion failed")
            await status_msg.edit_text(
                f"Ошибка при обработке файла: `{_esc(str(ingest_err)[:100])}`",
                parse_mode="MarkdownV2",
            )

    except Exception as e:
        logger.exception("Error downloading document")
        await message.answer(f"Ошибка загрузки файла: {_esc(str(e)[:200])}")


def _extract_query(text: str, command: str) -> str:
    """Strip the command prefix and return the rest, stripped."""
    if not text:
        return ""
    # Handle /command@botname form
    parts = text.split(None, 1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()
