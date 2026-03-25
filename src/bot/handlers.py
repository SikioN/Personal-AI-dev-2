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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)

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
    "*Что умеет бот:*\n\n"
    "*Задать вопрос* — введите любой вопрос, бот найдёт ответ в базе знаний\\.\n\n"
    "*Загрузить документ* — прикрепите файл \\(PDF, DOCX, PPTX, TXT\\), "
    "бот автоматически извлечёт факты и добавит их в базу\\.\n\n"
    "*Обновить модель* — после загрузки новых документов запустите обновление, "
    "чтобы бот учёл новые данные при ответах\\.\n\n"
    "_Для просмотра статуса системы используйте_ /status\\.\n"
    "_Для полного списка команд используйте_ /commands\\."
)

COMMANDS_TEXT = (
    "*Все доступные команды:*\n\n"
    "*Основные*\n"
    "*/ask* `<вопрос>` — ответ по базе знаний\n"
    "*/graph* `<вопрос>` — визуализация связей в виде графа \\(PNG\\)\n"
    "*/facts* `<вопрос>` — подробная трассировка: какие факты нашёл и почему\n"
    "*/status* — состояние системы и базы знаний\n\n"
    "*Документы и обучение*\n"
    "*/ingest* — обработать документы из папки new\\_docs\n"
    "*/ingest force* — переобработать уже загруженные документы\n"
    "*/retrain* — обновить модель вручную\n"
    "*/clear_kg* — полная очистка базы знаний \\(требует подтверждения\\)\n\n"
    "*Настройки*\n"
    "*/settings* — текущие параметры поиска\n"
    "*/set top\\_k N* — количество результатов \\(1–15, по умолчанию 5\\)\n"
    "*/set confidence X* — минимальный порог уверенности \\(0\\.0–1\\.0\\)\n\n"
    "*Отладка*\n"
    "*/dbg* `<вопрос>` — расширенный отладочный вывод\n"
    "*/help* — краткая справка"
)

WELCOME_TEXT = (
    "Добро пожаловать\\!\n\n"
    "Я корпоративный ассистент по базе знаний\\. "
    "Отвечаю на вопросы по загруженным документам и данным компании\\.\n\n"
    "Как начать:\n"
    "— Нажмите *Задать вопрос* и введите интересующий вас вопрос\\.\n"
    "— Чтобы добавить новые материалы — нажмите *Загрузить документ* "
    "или просто прикрепите файл в чат\\.\n"
    "— После загрузки документов нажмите *Обновить модель*, "
    "чтобы бот начал использовать новые данные\\.\n\n"
    + HELP_TEXT
)


class BotStates(StatesGroup):
    waiting_for_question = State()


# Labels used for reply keyboard buttons (must match exactly in text handlers below)
_BTN_ASK     = "Задать вопрос"
_BTN_HELP    = "Помощь"
_BTN_UPLOAD  = "Загрузить документ"
_BTN_RETRAIN = "Обновить модель"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_BTN_ASK),     KeyboardButton(text=_BTN_HELP)],
            [KeyboardButton(text=_BTN_UPLOAD),  KeyboardButton(text=_BTN_RETRAIN)],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def retrain_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да, начать", callback_data="menu_retrain"),
        InlineKeyboardButton(text="Отмена",     callback_data="menu_cancel"),
    ]])


def clear_kg_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да, очистить всё", callback_data="menu_clear_kg", style="danger"),
        InlineKeyboardButton(text="Отмена",            callback_data="menu_clear_cancel"),
    ]])


def _get_settings(chat_id: int) -> dict:
    if chat_id not in _chat_settings:
        _chat_settings[chat_id] = {'top_k': 5, 'min_confidence': 0.3}
    return _chat_settings[chat_id]


def _get_engine_and_navigator():
    """Import here to avoid circular imports at module load time."""
    from src.bot.engine_loader import load_engine
    return load_engine()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, parse_mode="MarkdownV2",
                         reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(HELP_TEXT, parse_mode="MarkdownV2",
                         reply_markup=main_menu_keyboard())


@router.message(Command("commands"))
async def cmd_commands(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(COMMANDS_TEXT, parse_mode="MarkdownV2")


# ── Reply keyboard menu handlers ──────────────────────────────────────────────

@router.message(F.text == _BTN_HELP)
async def menu_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(HELP_TEXT, parse_mode="MarkdownV2")


@router.message(F.text == _BTN_UPLOAD)
async def menu_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Прикрепите файл \\(PDF, DOCX, PPTX, TXT\\) прямо в этот чат\\. "
        "Факты извлекутся автоматически\\.",
        parse_mode="MarkdownV2",
    )


@router.message(F.text == _BTN_RETRAIN)
async def menu_retrain(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Обновление модели позволит боту учитывать недавно загруженные документы при ответах\\.\n\n"
        "Процесс может занять несколько минут\\. Продолжить?",
        parse_mode="MarkdownV2",
        reply_markup=retrain_confirm_keyboard(),
    )


@router.message(F.text == _BTN_ASK)
async def menu_ask(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_question)
    await message.answer("Введите ваш вопрос:")


@router.message(BotStates.waiting_for_question)
async def handle_question_input(message: Message, state: FSMContext):
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer("Вопрос не может быть пустым\\.", parse_mode="MarkdownV2")
        return

    now = time.monotonic()
    if now - _last_ask.get(message.chat.id, 0) < _ASK_COOLDOWN_SEC:
        await message.answer("Слишком быстро. Подождите несколько секунд.")
        return
    _last_ask[message.chat.id] = now

    await message.answer("Анализирую граф, подождите...")
    s = _get_settings(message.chat.id)
    async with _get_semaphore():
        try:
            engine, _, _ = await asyncio.to_thread(_get_engine_and_navigator)
            results = await asyncio.to_thread(engine.get_ranked_results, query, s['top_k'])
            answer = await asyncio.to_thread(engine.ask, query, s['top_k'])
        except Exception as e:
            logger.exception("Error in question input handler")
            await message.answer(f"Ошибка: {_esc(str(e))}", parse_mode="MarkdownV2")
            return

    if answer is None:
        await message.answer("Произошла ошибка при обращении к LLM\\. Попробуйте позже\\.",
                             parse_mode="MarkdownV2")
        return

    await message.answer(format_ask_with_ranked(answer, results, s['top_k']),
                         parse_mode="MarkdownV2")


# ─────────────────────────────────────────────────────────────────────────────

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
    graph_backend = os.environ.get("GRAPH_BACKEND", "kuzu")

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
    logger.info("[/ingest] received from chat_id=%s text=%r", message.chat.id, message.text)
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
            logger.info("[/ingest] semaphore acquired, loading engine...")
            engine, _, kg_model = await asyncio.to_thread(_get_engine_and_navigator)
            logger.info("[/ingest] engine ready, kg_model=%s", type(kg_model).__name__ if kg_model else None)
            from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
            # Use production KG path when kg_model is available (even in USE_INMEMORY mode
            # the engine may have a real InMemoryGraph/Kuzu connector under the hood).
            # Fall back to simple raw_quads path only when kg_model is None (SimpleInMemoryEngine).
            service = DocIngestionService(
                kg_model=kg_model,
                inmemory_engine=engine if kg_model is None else None,
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
    added = getattr(stats, "added", 0) if hasattr(stats, "added") else (stats or {}).get("added", 0)
    retrain_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Обновить модель", callback_data="menu_retrain_confirm")
    ]]) if added > 0 else None
    await status_msg.edit_text(
        format_ingest_result(stats, use_inmemory),
        parse_mode="MarkdownV2",
        reply_markup=retrain_kb,
    )


async def _do_retrain(message: Message) -> None:
    """Shared retrain logic used by /retrain command and inline button."""
    use_inmemory = os.environ.get("USE_INMEMORY", "true").lower() in ("1", "true", "yes")
    if use_inmemory:
        await message.answer(
            "TComplEx недоступен в режиме in\\-memory\\.", parse_mode="MarkdownV2"
        )
        return
    tkbc_dir = os.environ.get("TKBC_DIR") or os.environ.get("TCOMPLEX_DATA_PATH", "")
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
        "Модель обновлена\\. Бот теперь учитывает новые данные при ответах\\.",
        parse_mode="MarkdownV2",
    )


@router.message(Command("retrain"))
async def cmd_retrain(message: Message):
    await _do_retrain(message)


@router.message(Command("clear_kg"))
async def cmd_clear_kg(message: Message):
    warn_text = (
        "⚠️ *ВНИМАНИЕ: ПОЛНАЯ ОЧИСТКА*\n\n"
        "База знаний будет полностью очищена\\. Вы не сможете получать ответы на вопросы, "
        "пока не загрузите новые документы и не восстановите граф\\.\n\n"
        "Вы уверены, что хотите продолжить?"
    )
    await message.answer(
        warn_text,
        parse_mode="MarkdownV2",
        reply_markup=clear_kg_confirm_keyboard()
    )


@router.callback_query(F.data.startswith("menu_"))
async def handle_menu(query: CallbackQuery):
    await query.answer()
    action = query.data[5:]  # strip "menu_" prefix

    if action == "retrain_confirm":
        await query.message.answer(
            "Обновление модели позволит боту учитывать недавно загруженные документы при ответах\\.\n\n"
            "Процесс может занять несколько минут\\. Продолжить?",
            parse_mode="MarkdownV2",
            reply_markup=retrain_confirm_keyboard(),
        )
    elif action == "retrain":
        await _do_retrain(query.message)
    elif action == "cancel":
        await query.message.edit_text("Переобучение отменено\\.", parse_mode="MarkdownV2")
    elif action == "clear_kg":
        await query.message.edit_text("Выполняю полную очистку баз данных\\.\\.\\.", parse_mode="MarkdownV2")
        async with _get_semaphore():
            try:
                engine, _, kg_model = await asyncio.to_thread(_get_engine_and_navigator)
                if kg_model:
                    await asyncio.to_thread(kg_model.clear)
                    await query.message.edit_text("✅ База знаний полностью очищена\\.", parse_mode="MarkdownV2")
                else:
                    await query.message.edit_text("Очистка доступна только в production режиме\\.", parse_mode="MarkdownV2")
            except Exception as e:
                logger.exception("Error in /clear_kg")
                await query.message.edit_text(f"Ошибка при очистке: `{_esc(str(e)[:200])}`", parse_mode="MarkdownV2")
    elif action == "clear_cancel":
        await query.message.edit_text("Очистка отменена\\.", parse_mode="MarkdownV2")


_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}


@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    logger.info("[document] received from chat_id=%s file=%r", message.chat.id,
                message.document.file_name if message.document else None)
    doc = message.document
    
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        if not os.environ.get("TELEGRAM_API_URL"):
            await message.answer(
                "Файл слишком большой (>20 МБ).\n"
                "Публичный API Telegram не позволяет ботам скачивать такие файлы без ограничения.\n"
                "Настройте TELEGRAM_API_URL для локального сервера."
            )
            return

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

    fname_esc = _esc(doc.file_name)
    status_msg = await message.answer(
        f"Файл *{fname_esc}* принят в очередь\\. Ожидайте обработки\\.\\.\\.",
        parse_mode="MarkdownV2",
    )

    # Run actual downloading and processing in the background to not block Telegram updates
    asyncio.create_task(_process_document_bg(bot, doc, save_path, status_msg))


async def _process_document_bg(bot: Bot, doc, save_path: str, status_msg: Message):
    fname_esc = _esc(doc.file_name)
    loop = asyncio.get_running_loop()
    try:
        await bot.download(doc, destination=save_path)
        await status_msg.edit_text(
            f"Файл *{fname_esc}* загружен\\. Начинаю извлечение фактов\\.\\.\\.",
            parse_mode="MarkdownV2",
        )

        from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
        logger.info("[document] loading engine for %s", save_path)
        engine, _, kg_model = await asyncio.to_thread(_get_engine_and_navigator)
        logger.info("[document] engine ready, kg_model=%s", type(kg_model).__name__ if kg_model else None)
        service = DocIngestionService(
            kg_model=kg_model,
            inmemory_engine=engine if kg_model is None else None,
        )

        def sync_progress(text: str):
            async def _do() -> None:
                await status_msg.edit_text(_esc(text), parse_mode="MarkdownV2")
            asyncio.run_coroutine_threadsafe(_do(), loop)

        logger.info("[document] waiting for semaphore...")
        async with _get_semaphore():
            logger.info("[document] semaphore acquired, starting ingest_single_file")
            res = await asyncio.to_thread(
                service.ingest_single_file, save_path, None, sync_progress
            )
        logger.info("[document] ingest done: added=%s errors=%s", res.get("added"), res.get("errors"))

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

        retrain_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Обновить модель", callback_data="menu_retrain_confirm")
        ]]) if added > 0 else None
        await status_msg.edit_text(summary, parse_mode="MarkdownV2", reply_markup=retrain_kb)
    except Exception as e:
        logger.exception("Error processing document in background")
        await status_msg.edit_text(
            f"Ошибка при обработке файла: `{_esc(str(e)[:200])}`",
            parse_mode="MarkdownV2",
        )


def _extract_query(text: str, command: str) -> str:
    """Strip the command prefix and return the rest, stripped."""
    if not text:
        return ""
    # Handle /command@botname form
    parts = text.split(None, 1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()
