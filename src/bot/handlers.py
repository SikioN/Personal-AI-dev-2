"""aiogram 3.x handlers for Personal-AI KG QA Telegram bot."""
import asyncio
import logging
import os
import time
from typing import Optional
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BufferedInputFile

from src.bot.formatters import (
    format_facts, format_answer, format_status, format_settings, _esc
)
from src.bot.graph_renderer import render_subgraph

logger = logging.getLogger(__name__)

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
    "*/facts* `<вопрос>` — топ фактов с оценками\n"
    "*/graph* `<вопрос>` — 1\\-hop подграф → PNG\n"
    "*/settings* — текущие настройки\n"
    "*/set top\\_k N* — изменить top\\_k \\(1–15\\)\n"
    "*/set confidence X* — мин\\. confidence \\(0\\.0–1\\.0\\)\n"
    "*/status* — статус системы\n"
    "*/help* — этот список"
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
        # 1.2: wrap synchronous ChromaDB I/O in asyncio.to_thread
        await asyncio.to_thread(kg_model.embeddings_model.nodes_db.count)
        chroma_ok = True
    except Exception:
        pass

    from src.utils.device_utils import get_device
    device = get_device(verbose=False).upper()
    llm_backend = os.environ.get("LLM_BACKEND", "ollama")

    text = format_status(neo4j_ok, chroma_ok, llm_backend, device, nodes, quads)
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
            await message.answer(f"min\\_confidence установлен в `{v:.2f}`",
                                 parse_mode="MarkdownV2")
        else:
            await message.answer(f"Неизвестный параметр: `{_esc(key)}`",
                                 parse_mode="MarkdownV2")
    except ValueError:
        await message.answer("Неверное значение. top\\_k: 1–15, confidence: 0\\.0–1\\.0",
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
    async with _get_semaphore():
        try:
            engine, _, _ = await asyncio.to_thread(_get_engine_and_navigator)
            answer = await asyncio.to_thread(engine.ask, query)
        except Exception as e:
            logger.exception("Error in /ask")
            await message.answer(f"Ошибка: {_esc(str(e))}", parse_mode="MarkdownV2")
            return

    # 5.1: check for None answer (LLM failure reported from GenerationStage)
    if answer is None:
        await message.answer("Произошла ошибка при обращении к LLM\\. Попробуйте позже\\.",
                             parse_mode="MarkdownV2")
        return

    await message.answer(format_answer(answer), parse_mode="MarkdownV2")


@router.message(Command("facts"))
async def cmd_facts(message: Message):
    query = _extract_query(message.text, "/facts")
    if not query:
        await message.answer("Использование: /facts <вопрос>")
        return

    now = time.monotonic()
    if now - _last_ask.get(message.chat.id, 0) < _ASK_COOLDOWN_SEC:
        await message.answer("Слишком быстро. Подождите несколько секунд.")
        return
    _last_ask[message.chat.id] = now

    s = _get_settings(message.chat.id)
    await message.answer("Ищу факты в графе...")
    # 5.4: rate limiting
    async with _get_semaphore():
        try:
            engine, _, _ = await asyncio.to_thread(_get_engine_and_navigator)
            results = await asyncio.to_thread(engine.get_ranked_results, query, s['top_k'])
        except Exception as e:
            logger.exception("Error in /facts")
            await message.answer(f"Ошибка: {_esc(str(e))}", parse_mode="MarkdownV2")
            return

    results = [r for r in results if r.get('confidence', 0) >= s['min_confidence']]
    text = format_facts(query, results, top_n=s['top_k'])
    await message.answer(text, parse_mode="MarkdownV2")


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
    seed_ids = []
    for r in results:
        q = r.get('quadruplet')
        if q and hasattr(q, 'start_node') and hasattr(q, 'end_node'):
            seed_ids.append(q.start_node.id)
            seed_ids.append(q.end_node.id)
    seed_ids = list(set(seed_ids))

    if not seed_ids or navigator is None:
        await message.answer("Граф недоступен в текущем режиме\\.", parse_mode="MarkdownV2")
        return

    try:
        quadruplets = await asyncio.to_thread(navigator.get_neighborhood, seed_ids, 1)
        png_bytes = await asyncio.to_thread(render_subgraph, quadruplets)
    except Exception as e:
        logger.exception("Error rendering graph")
        await message.answer(f"Ошибка рендеринга: {_esc(str(e))}", parse_mode="MarkdownV2")
        return

    photo = BufferedInputFile(png_bytes.read(), filename="graph.png")
    await message.answer_photo(photo, caption=f"1-hop подграф для: {query[:100]}")


def _extract_query(text: str, command: str) -> str:
    """Strip the command prefix and return the rest, stripped."""
    if not text:
        return ""
    # Handle /command@botname form
    parts = text.split(None, 1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()
