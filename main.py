"""
TINA — бот вакансий v3
Команды: /start, /categories, /status, /key, /stop, /check, /help
Монетизация: лицензионные ключи (оплата убрана)
Админ: только для ADMIN_ID
"""

import asyncio, logging, json, httpx, random, string, secrets
from datetime import datetime, date, timedelta
from pyrogram import Client

import db
from config import (
    API_ID, API_HASH, BOT_TOKEN, SESSION_STRING,
    CHECK_INTERVAL, CATEGORIES,
)
from monitor import check_channels

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

TG                = f"https://api.telegram.org/bot{BOT_TOKEN}"
ADMIN_ID          = 8447718762   # единственный администратор
KEY_LENGTH        = 22           # длина лицензионного ключа
KEY_DAYS          = 30           # срок действия ключа
DAILY_CHECK_LIMIT = 2
EXPIRY_WARN_DAYS  = 3            # за сколько дней предупреждать об истечении


# ═══════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ═══════════════════════════════════════════════════════════

def is_admin(chat_id: int) -> bool:
    return chat_id == ADMIN_ID

def generate_key() -> str:
    """
    Криптографически стойкий ключ из букв и цифр, 22 символа.
    secrets.choice гарантирует непредсказуемость — random.choices не подходит
    для задач безопасности, secrets — да.
    """
    alphabet = string.ascii_letters + string.digits  # 62 символа
    return "".join(secrets.choice(alphabet) for _ in range(KEY_LENGTH))
    # 62^22 ≈ 2.7 × 10^39 вариантов — перебор невозможен


# ═══════════════════════════════════════════════════════════
#  HTTP HELPERS
# ═══════════════════════════════════════════════════════════

async def send(chat_id: int, text: str, buttons: list = None, parse_mode: str = None):
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(f"{TG}/sendMessage", json=payload)
            if resp.status_code == 403:
                logger.info(f"Бот заблокирован: {chat_id}")
        except Exception as e:
            logger.error(f"send() error {chat_id}: {e}")

async def edit_msg(chat_id: int, message_id: int, text: str, buttons: list = None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TG}/editMessageText", json=payload)

async def answer_callback(callback_query_id: str, text: str = ""):
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(f"{TG}/answerCallbackQuery",
                          json={"callback_query_id": callback_query_id, "text": text})

async def set_reply_keyboard(chat_id: int, text: str, keyboard: list, parse_mode: str = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "keyboard": keyboard,
            "resize_keyboard": True,
            "one_time_keyboard": False,
        },
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TG}/sendMessage", json=payload)


# ═══════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════

def user_keyboard() -> list:
    return [
        [{"text": "📊 Мой статус"},   {"text": "🔑 Ввести ключ"}],
        [{"text": "📂 Категории"},    {"text": "🔍 Проверить сейчас"}],
        [{"text": "🆘 Поддержка"},    {"text": "❓ Помощь"}],
    ]

def admin_keyboard() -> list:
    return [
        [{"text": "🔑 Сгенерировать ключ"}, {"text": "📊 Статистика"}],
        [{"text": "🗝 Все ключи"},           {"text": "👥 Пользователи"}],
        [{"text": "📂 Категории"},           {"text": "🔍 Проверить сейчас"}],
        [{"text": "❓ Помощь"}],
    ]

async def send_main_menu(chat_id: int, text: str, parse_mode: str = None):
    kb = admin_keyboard() if is_admin(chat_id) else user_keyboard()
    await set_reply_keyboard(chat_id, text, kb, parse_mode)


# ═══════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════

async def cmd_start(chat_id: int, username: str):
    db.upsert_user(chat_id, username)

    if is_admin(chat_id):
        await send_main_menu(chat_id,
            "👑 Добро пожаловать в админ-панель TINA!\n\n"
            "Выбери действие в меню ниже.")
        return

    cats = db.get_categories(chat_id)
    info = db.get_sub_info(chat_id)

    if not cats:
        await send_main_menu(chat_id,
            "👋 Привет! Я TINA — бот, который находит свежие вакансии "
            "в Telegram каналах и сразу присылает тебе.\n\n"
            "🆓 У тебя есть 2 дня бесплатного доступа.\n\n"
            "Сначала выбери категории вакансий 👇")
        await cmd_categories(chat_id)
        return

    if not info["active"]:
        await send_main_menu(chat_id,
            "⚠️ Твой бесплатный период закончился.\n\n"
            "Чтобы продолжить получать вакансии — купи ключ у администратора "
            f"и введи его кнопкой «🔑 Ввести ключ».\n\n"
            f"Написать админу: tg://user?id={ADMIN_ID}")
        return

    await show_status(chat_id)


# ═══════════════════════════════════════════════════════════
#  СТАТУС ПОДПИСКИ
# ═══════════════════════════════════════════════════════════

async def show_status(chat_id: int):
    info = db.get_sub_info(chat_id)
    cats = db.get_categories(chat_id)
    cat_names = [CATEGORIES.get(c, c) for c in cats] if cats else ["не выбраны"]

    if info["active"]:
        if info["type"] == "trial":
            status = f"🆓 Бесплатный период — осталось {info['days_left']} дн."
        else:
            status = f"✅ Подписка активна — осталось {info['days_left']} дн."
    else:
        status = (
            "❌ Подписка неактивна\n\n"
            "Купи ключ у администратора и введи его кнопкой «🔑 Ввести ключ».\n"
            f"Написать админу: tg://user?id={ADMIN_ID}"
        )

    text = (
        f"📊 Твой статус:\n\n"
        f"{status}\n\n"
        f"📂 Категории: {', '.join(cat_names)}"
    )
    await send(chat_id, text)


# ═══════════════════════════════════════════════════════════
#  КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════

_cat_drafts: dict[int, list] = {}

async def _categories_keyboard(selected: list) -> list:
    rows = []
    items = list(CATEGORIES.items())
    for i in range(0, len(items), 2):
        row = []
        for key, label in items[i:i+2]:
            check = "✅ " if key in selected else ""
            row.append({"text": f"{check}{label}", "callback_data": f"cat_toggle:{key}"})
        rows.append(row)
    rows.append([{"text": "✅ Готово", "callback_data": "cat_done"}])
    return rows

async def cmd_categories(chat_id: int):
    current = db.get_categories(chat_id)
    _cat_drafts[chat_id] = list(current)
    kb = await _categories_keyboard(current)
    await send(chat_id,
        "📂 Выбери категории вакансий (✅ — выбрано).\nНажми «Готово» когда закончишь:",
        kb)


# ═══════════════════════════════════════════════════════════
#  ПОДДЕРЖКА
# ═══════════════════════════════════════════════════════════

async def show_support(chat_id: int):
    buttons = [
        [{"text": "🤖 Бот не работает",     "callback_data": "support:bot_broken"}],
        [{"text": "🔑 Ключ не активируется", "callback_data": "support:key_fail"}],
        [{"text": "📭 Нет уведомлений",      "callback_data": "support:no_notif"}],
        [{"text": "❓ Другая проблема",       "callback_data": "support:other"}],
    ]
    await send(chat_id, "🆘 Выбери проблему — я передам её администратору:", buttons)


# ═══════════════════════════════════════════════════════════
#  ВВОД И АКТИВАЦИЯ КЛЮЧА
# ═══════════════════════════════════════════════════════════

_waiting_key: set[int] = set()

async def ask_for_key(chat_id: int):
    _waiting_key.add(chat_id)
    await send(chat_id,
        "🔑 Введи свой лицензионный ключ (22 символа):\n\n"
        "Просто отправь его следующим сообщением.")

async def process_key(chat_id: int, key_text: str):
    """
    Вся логика проверки ключа. Защита от мошенничества:
    1. Ключ должен быть в БД (нельзя придумать)
    2. Ключ должен быть неиспользованным (один ключ = один человек)
    3. После активации записывается chat_id — другой пользователь не сможет его использовать
    4. Через 30 дней expires_at истекает, is_active() возвращает False, вакансии не приходят
    """
    _waiting_key.discard(chat_id)
    key = key_text.strip()

    # Защита: минимальная валидация формата (не гоняем запрос в БД за явным мусором)
    if len(key) != KEY_LENGTH or not key.isalnum():
        await send(chat_id,
            "❌ Неверный формат ключа.\n\n"
            "Ключ состоит из 22 букв и цифр без пробелов и дефисов.\n"
            "Попробуй скопировать ключ целиком.")
        return

    record = db.get_license_key(key)

    if not record:
        # Ключ не найден в БД — либо опечатка, либо попытка угадать
        await send(chat_id,
            "❌ Ключ не найден.\n\n"
            "Проверь правильность ввода или обратись к администратору.\n"
            f"Написать админу: tg://user?id={ADMIN_ID}")
        # Уведомляем администратора о попытке ввода несуществующего ключа
        await send(ADMIN_ID,
            f"⚠️ Попытка активации несуществующего ключа!\n"
            f"Пользователь: {chat_id}\nКлюч: <code>{key}</code>",
            parse_mode="HTML")
        return

    if record["status"] == "active":
        if record["activated_by"] == chat_id:
            # Этот же пользователь вводит свой ключ повторно
            exp = record["expires_at"][:10] if record["expires_at"] else "?"
            await send(chat_id,
                f"ℹ️ Этот ключ уже активирован тобой.\n\n"
                f"Подписка действует до {exp}.")
        else:
            # Чужой ключ — уже кто-то использовал
            await send(chat_id,
                "❌ Этот ключ уже использован другим пользователем.\n\n"
                "Каждый ключ работает только для одного аккаунта.\n"
                f"Купи свой ключ у администратора: tg://user?id={ADMIN_ID}")
            # Уведомляем админа — возможно, ключ был передан/слит
            await send(ADMIN_ID,
                f"⚠️ Попытка повторного использования ключа!\n"
                f"Ключ: <code>{key}</code>\n"
                f"Ключ принадлежит: {record['activated_by']}\n"
                f"Пытался активировать: {chat_id}",
                parse_mode="HTML")
        return

    # Ключ валиден и свободен — активируем
    expires = db.activate_license_key(key, chat_id, KEY_DAYS)
    if expires is None:
        # Теоретически невозможно (проверили выше), но на всякий случай
        await send(chat_id,
            "❌ Ошибка активации. Обратись в поддержку.\n"
            f"tg://user?id={ADMIN_ID}")
        return

    exp_str = expires.strftime("%d.%m.%Y")
    await send(chat_id,
        f"✅ Ключ успешно активирован!\n\n"
        f"📅 Подписка действует до {exp_str} ({KEY_DAYS} дней)\n\n"
        f"Вакансии по выбранным категориям будут приходить автоматически.\n"
        f"Изменить категории — кнопка «📂 Категории»."
    )
    # Уведомляем администратора об активации
    await send(ADMIN_ID,
        f"✅ Ключ активирован!\n"
        f"Пользователь: {chat_id}\n"
        f"Действует до: {exp_str}")


# ═══════════════════════════════════════════════════════════
#  АДМИН: ГЕНЕРАЦИЯ КЛЮЧА
# ═══════════════════════════════════════════════════════════

async def admin_generate_key(chat_id: int):
    key = generate_key()
    db.create_license_key(key)
    # Форматируем для удобного копирования — без дефисов, одной строкой
    await send(chat_id,
        f"🔑 Новый ключ создан:\n\n"
        f"<code>{key}</code>\n\n"
        f"Скопируй и отправь покупателю. Ключ одноразовый, действует {KEY_DAYS} дней после активации.",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════
#  АДМИН: СТАТИСТИКА
# ═══════════════════════════════════════════════════════════

async def admin_stats(chat_id: int):
    stats = db.get_stats()
    await send(chat_id,
        f"📊 Статистика TINA:\n\n"
        f"👥 Всего пользователей: {stats['total']}\n"
        f"✅ Активных подписок (ключ): {stats['paid']}\n"
        f"🆓 На пробном периоде: {stats['trial']}\n\n"
        f"🗝 Ключей выдано всего: {stats['keys_total']}\n"
        f"🟢 Активировано: {stats['keys_used']}\n"
        f"⏳ Не использовано: {stats['keys_free']}"
    )


# ═══════════════════════════════════════════════════════════
#  АДМИН: СПИСОК КЛЮЧЕЙ
# ═══════════════════════════════════════════════════════════

async def admin_list_keys(chat_id: int):
    keys = db.get_all_keys()
    if not keys:
        await send(chat_id, "🗝 Ключей пока нет.")
        return

    # Разбиваем на 2 группы для наглядности
    unused  = [k for k in keys if k["status"] == "inactive"]
    active  = [k for k in keys if k["status"] == "active"]

    lines = [f"🗝 Ключи ({len(keys)} всего):\n"]

    if unused:
        lines.append(f"⏳ Не активированные ({len(unused)}):")
        for k in unused[:10]:
            lines.append(f"  <code>{k['key']}</code>")

    if active:
        lines.append(f"\n🟢 Активные ({len(active)}):")
        for k in active[:15]:
            exp = k["expires_at"][:10] if k.get("expires_at") else "?"
            by  = str(k["activated_by"]) if k.get("activated_by") else "?"
            lines.append(f"  <code>{k['key'][:10]}…</code> | до {exp} | user {by}")

    await send(chat_id, "\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════
#  АДМИН: СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ═══════════════════════════════════════════════════════════

async def admin_list_users(chat_id: int):
    users = db.get_all_active_users()
    if not users:
        await send(chat_id, "👥 Нет активных пользователей.")
        return
    lines = [f"👥 Активных пользователей: {len(users)}\n"]
    for u in users[:30]:
        name  = u.get("username") or str(u["chat_id"])
        sub   = u.get("sub_ends",   "")[:10] if u.get("sub_ends")   else "—"
        trial = u.get("trial_ends", "")[:10] if u.get("trial_ends") else "—"
        lines.append(f"• @{name} | ключ до {sub} | триал до {trial}")
    await send(chat_id, "\n".join(lines))


# ═══════════════════════════════════════════════════════════
#  /check — ручная проверка каналов
# ═══════════════════════════════════════════════════════════

_check_counter: dict[int, tuple] = {}

async def cmd_check(chat_id: int, app: Client):
    if not db.is_active(chat_id):
        await send(chat_id,
            "❌ Нет активной подписки.\n\n"
            f"Купи ключ у администратора: tg://user?id={ADMIN_ID}")
        return
    today = date.today()
    last_date, count = _check_counter.get(chat_id, (None, 0))
    if last_date == today:
        if count >= DAILY_CHECK_LIMIT:
            await send(chat_id,
                f"⏳ Лимит исчерпан. Ручная проверка доступна {DAILY_CHECK_LIMIT} раза в день.\n"
                f"Следующая — завтра.")
            return
        _check_counter[chat_id] = (today, count + 1)
    else:
        _check_counter[chat_id] = (today, 1)
    remaining = DAILY_CHECK_LIMIT - _check_counter[chat_id][1]
    await send(chat_id, f"🔍 Запускаю проверку каналов...\nОсталось проверок сегодня: {remaining}")
    await check_channels(app)


# ═══════════════════════════════════════════════════════════
#  ФОНОВАЯ ЗАДАЧА: уведомления об истечении подписки
# ═══════════════════════════════════════════════════════════

async def expiry_notification_loop():
    """
    Каждые 12 часов проверяет всех пользователей:
    - За EXPIRY_WARN_DAYS дней до истечения — предупреждает
    - Если подписка только что истекла (< 1 часа назад) — сообщает об окончании
    Флаг _notified хранится в памяти, чтобы не спамить.
    """
    warned:  set[int] = set()   # уже получили предупреждение
    expired: set[int] = set()   # уже получили уведомление об истечении

    while True:
        await asyncio.sleep(60 * 60 * 12)  # каждые 12 часов
        try:
            with db.get_conn() as conn:
                rows = conn.execute("SELECT * FROM users").fetchall()
            now = datetime.now()

            for row in rows:
                u       = dict(row)
                cid     = u["chat_id"]
                sub_end = u.get("sub_ends")
                if not sub_end:
                    continue
                try:
                    end_dt = datetime.fromisoformat(sub_end)
                except Exception:
                    continue

                delta = end_dt - now

                # Предупреждение за EXPIRY_WARN_DAYS дней
                if timedelta(0) < delta <= timedelta(days=EXPIRY_WARN_DAYS):
                    if cid not in warned:
                        warned.add(cid)
                        await send(cid,
                            f"⏰ Напоминание: твоя подписка истекает через {delta.days + 1} дн. "
                            f"({end_dt.strftime('%d.%m.%Y')}).\n\n"
                            f"Чтобы продлить — купи новый ключ у администратора:\n"
                            f"tg://user?id={ADMIN_ID}"
                        )

                # Уведомление об истечении (окно 0–12 часов после окончания)
                elif timedelta(hours=-12) <= delta <= timedelta(0):
                    if cid not in expired:
                        expired.add(cid)
                        warned.discard(cid)  # сбрасываем флаг предупреждения
                        await send(cid,
                            f"🔴 Твоя подписка закончилась.\n\n"
                            f"Вакансии больше не будут приходить.\n\n"
                            f"Чтобы возобновить доступ — купи новый ключ у администратора:\n"
                            f"tg://user?id={ADMIN_ID}"
                        )

                # Если подписка продлена — сбрасываем флаги
                elif delta > timedelta(days=EXPIRY_WARN_DAYS):
                    warned.discard(cid)
                    expired.discard(cid)

        except Exception as e:
            logger.error(f"expiry_notification_loop error: {e}")


# ═══════════════════════════════════════════════════════════
#  ОБРАБОТКА CALLBACK КНОПОК
# ═══════════════════════════════════════════════════════════

async def handle_callback(update: dict, app: Client):
    cq      = update.get("callback_query", {})
    cq_id   = cq.get("id")
    chat_id = cq.get("from", {}).get("id")
    msg_id  = cq.get("message", {}).get("message_id")
    data    = cq.get("data", "")

    if not chat_id:
        return

    if data.startswith("cat_toggle:"):
        cat   = data.split(":")[1]
        draft = _cat_drafts.get(chat_id, list(db.get_categories(chat_id)))
        if cat in draft:
            draft.remove(cat)
        else:
            draft.append(cat)
        _cat_drafts[chat_id] = draft
        await answer_callback(cq_id)
        kb = await _categories_keyboard(draft)
        await edit_msg(chat_id, msg_id,
            "📂 Выбери категории (✅ — выбрано). Нажми «Готово» когда закончишь:", kb)

    elif data == "cat_done":
        draft = _cat_drafts.pop(chat_id, [])
        if not draft:
            await answer_callback(cq_id, "⚠️ Выбери хотя бы одну категорию!")
            return
        db.set_categories(chat_id, draft)
        await answer_callback(cq_id, "✅ Категории сохранены!")
        await edit_msg(chat_id, msg_id,
            "✅ Категории сохранены!\n\n"
            "Введи лицензионный ключ кнопкой «🔑 Ввести ключ» чтобы начать получать вакансии.")

    elif data.startswith("support:"):
        problem_map = {
            "support:bot_broken": "🤖 Бот не работает",
            "support:key_fail":   "🔑 Ключ не активируется",
            "support:no_notif":   "📭 Нет уведомлений",
            "support:other":      "❓ Другая проблема",
        }
        problem  = problem_map.get(data, data)
        user_info = cq.get("from", {})
        username  = user_info.get("username", "")
        name      = user_info.get("first_name", "")
        user_tag  = f"@{username}" if username else f"ID {chat_id}"

        await send(ADMIN_ID,
            f"🆘 Обращение в поддержку!\n\n"
            f"От: {user_tag} ({name})\n"
            f"ID: <code>{chat_id}</code>\n"
            f"Проблема: {problem}",
            parse_mode="HTML"
        )
        await answer_callback(cq_id, "Отправлено!")
        await edit_msg(chat_id, msg_id,
            f"✅ Обращение отправлено администратору.\n\n"
            f"Проблема: {problem}\n\n"
            f"Ожидай ответа — обычно отвечаем быстро.")

    else:
        await answer_callback(cq_id)


# ═══════════════════════════════════════════════════════════
#  ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# ═══════════════════════════════════════════════════════════

async def handle_message(update: dict, app: Client):
    msg      = update.get("message", {})
    text     = (msg.get("text") or "").strip()
    chat_id  = msg.get("chat", {}).get("id")
    user     = msg.get("from", {})
    username = user.get("username") or user.get("first_name", "")

    if not chat_id or not text:
        return

    db.upsert_user(chat_id, username)

    # Приоритет 1: ожидаем ввод ключа от этого пользователя
    if chat_id in _waiting_key and not text.startswith("/"):
        await process_key(chat_id, text)
        return

    # Приоритет 2: любое 22-символьное alnum сообщение — пробуем как ключ
    if len(text) == KEY_LENGTH and text.isalnum() and not text.startswith("/"):
        await process_key(chat_id, text)
        return

    # ── Команды и кнопки ──────────────────────────────────

    if text in ("/start", "/menu"):
        await cmd_start(chat_id, username)

    elif text in ("📊 Мой статус", "/status"):
        await show_status(chat_id)

    elif text in ("🔑 Ввести ключ", "/key"):
        await ask_for_key(chat_id)

    elif text in ("📂 Категории", "/categories"):
        await cmd_categories(chat_id)

    elif text in ("🔍 Проверить сейчас", "/check"):
        await cmd_check(chat_id, app)

    elif text in ("🆘 Поддержка", "/support"):
        await show_support(chat_id)

    elif text in ("❓ Помощь", "/help"):
        if is_admin(chat_id):
            await send(chat_id,
                "📋 Команды администратора:\n\n"
                "🔑 Сгенерировать ключ — создать уникальный 22-значный ключ\n"
                "📊 Статистика — пользователи, ключи\n"
                "🗝 Все ключи — список выданных ключей\n"
                "👥 Пользователи — активные пользователи\n"
                "📂 Категории — выбор категорий для себя\n"
                "🔍 Проверить сейчас — ручной запуск мониторинга\n\n"
                "При попытке ввода чужого/несуществующего ключа — тебе приходит уведомление."
            )
        else:
            await send(chat_id,
                "📋 Как пользоваться TINA:\n\n"
                "🔑 Ввести ключ — активировать лицензионный ключ (30 дней)\n"
                "📊 Мой статус — статус подписки и категории\n"
                "📂 Категории — выбрать категории вакансий\n"
                "🔍 Проверить сейчас — ручная проверка (2 раза в день)\n"
                "🆘 Поддержка — написать администратору\n\n"
                "Вакансии приходят автоматически каждые ~25 минут."
            )

    elif text in ("🔕 Отключить", "/stop"):
        db.set_categories(chat_id, [])
        await send(chat_id,
            "🔕 Уведомления отключены.\n"
            "Нажми «📂 Категории» чтобы включить снова.")

    # ── Админские кнопки (защита: проверяем is_admin) ──

    elif text == "🔑 Сгенерировать ключ":
        if is_admin(chat_id):
            await admin_generate_key(chat_id)
        else:
            await send(chat_id, "⛔ Нет доступа.")

    elif text == "📊 Статистика":
        if is_admin(chat_id):
            await admin_stats(chat_id)
        else:
            await send(chat_id, "⛔ Нет доступа.")

    elif text == "🗝 Все ключи":
        if is_admin(chat_id):
            await admin_list_keys(chat_id)
        else:
            await send(chat_id, "⛔ Нет доступа.")

    elif text == "👥 Пользователи":
        if is_admin(chat_id):
            await admin_list_users(chat_id)
        else:
            await send(chat_id, "⛔ Нет доступа.")

    else:
        await send_main_menu(chat_id, "Используй кнопки меню 👇")


# ═══════════════════════════════════════════════════════════
#  POLLING
# ═══════════════════════════════════════════════════════════

async def poll_updates(app: Client):
    url    = f"{TG}/getUpdates"
    offset = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.get(url, params={"timeout": 30, "offset": offset})
                if not resp.text.strip():
                    await asyncio.sleep(3)
                    continue
                try:
                    data = resp.json()
                except Exception:
                    await asyncio.sleep(3)
                    continue
                if not data.get("ok"):
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        if "message" in update:
                            await handle_message(update, app)
                        if "callback_query" in update:
                            await handle_callback(update, app)
                    except Exception as e:
                        logger.error(f"Ошибка обработки update: {e}")

        except Exception as e:
            logger.error(f"Polling ошибка: {e}")
        await asyncio.sleep(1)


# ═══════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════

async def channel_loop(app: Client):
    while True:
        await check_channels(app)
        logger.info("⏳ Следующая проверка через 25 минут")
        await asyncio.sleep(CHECK_INTERVAL)


async def main():
    db.init_db()
    logger.info("🚀 TINA запускается...")

    async with Client(
        name="tina_monitor",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING
    ) as app:
        logger.info("✅ Аккаунт подключён")
        await asyncio.gather(
            poll_updates(app),
            channel_loop(app),
            expiry_notification_loop(),   # фоновые уведомления об истечении
        )

if __name__ == "__main__":
    asyncio.run(main())
