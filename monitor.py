"""
monitor.py — мониторинг каналов и рассылка
"""
import asyncio, re, logging, json, httpx
from pyrogram import Client
from pyrogram.errors import FloodWait, ChannelInvalid, UsernameNotOccupied
import db
from config import BOT_TOKEN, POSTS_LIMIT, CATEGORIES, CHANNELS_BY_CATEGORY, GLOBAL_CHANNELS, KEYWORDS_BY_CATEGORY

logger = logging.getLogger(__name__)
TG = f"https://api.telegram.org/bot{BOT_TOKEN}"


def normalize(text: str) -> str:
    text = re.sub(r'[(\[{]+(#)', r'\1', text)
    text = re.sub(r'(#\S+?)[)\]}.,:!]+', r'\1', text)
    return text.lower()

def check_category(text: str, cat_key: str) -> tuple:
    rules = KEYWORDS_BY_CATEGORY.get(cat_key, {})
    if not rules:
        return False, "нет правил"
    t = normalize(text)
    for stop in rules.get("stop", []):
        if stop in t:
            return False, f"стоп: «{stop}»"
    for tag in rules.get("hashtags", []):
        if tag.lower() in t:
            return True, f"хэштег {tag}"
    for kw in rules.get("keywords", []):
        if kw in t:
            return True, f"ключ «{kw}»"
    return False, "нет совпадений"

def get_hashtags(text: str) -> str:
    tags = re.findall(r'#[\wа-яёА-ЯЁa-zA-Z0-9_]+', text)
    return " ".join(tags[:5]) if tags else ""

def get_body(text: str, limit: int = 350) -> str:
    lines = text.strip().splitlines()
    body = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        clean = re.sub(r'#[\wа-яёА-ЯЁ]+', '', s).strip('()[]{}* \t')
        if not clean and '#' in s:
            continue
        body.append(s)
    result = " ".join(body)
    if len(result) <= limit:
        return result
    cut = result[:limit]
    return cut[:cut.rfind(" ")] + "…"

def get_contact(message) -> str | None:
    if message.forward_from and message.forward_from.username:
        return message.forward_from.username
    text = message.text or message.caption or ""
    matches = re.findall(r'@([A-Za-z0-9_]{3,32})', text)
    return matches[-1] if matches else None


async def send_vacancy(chat_id: int, text: str, buttons: list):
    async with httpx.AsyncClient(timeout=10) as client:
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": [buttons]}
        try:
            resp = await client.post(f"{TG}/sendMessage", json=payload)
            if resp.status_code == 403:
                logger.info(f"Бот заблокирован пользователем {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки {chat_id}: {e}")


async def check_channels(app: Client) -> int:
    logger.info("🔍 Проверяю каналы...")
    found = 0

    # Собираем все каналы с их категориями
    channel_cats: dict[str, set] = {}
    for cat_key, channels in CHANNELS_BY_CATEGORY.items():
        for ch in channels:
            channel_cats.setdefault(ch, set()).add(cat_key)
    for ch in GLOBAL_CHANNELS:
        for cat_key in CATEGORIES:
            channel_cats.setdefault(ch, set()).add(cat_key)

    active_users = db.get_all_active_users()
    if not active_users:
        logger.info("Нет активных пользователей")
        return 0

    for username, cat_keys in channel_cats.items():
        try:
            async for message in app.get_chat_history(username, limit=POSTS_LIMIT):
                text = message.text or message.caption or ""
                if not text.strip():
                    continue

                post_id = f"{username}_{message.id}"
                if db.is_seen(post_id):
                    continue
                db.mark_seen(post_id)

                matched_cats = [c for c in cat_keys if check_category(text, c)[0]]
                if not matched_cats:
                    continue

                hashtags = get_hashtags(text)
                body     = get_body(text)
                link     = f"https://t.me/{username}/{message.id}"
                contact  = get_contact(message)
                cat_labels = " | ".join(CATEGORIES.get(c, c) for c in matched_cats)

                notification = f"{cat_labels}\n"
                notification += f"{hashtags}\n\n" if hashtags else "\n"
                notification += body

                buttons = []
                if contact:
                    buttons.append({"text": "Контакты", "url": f"https://t.me/{contact}"})
                buttons.append({"text": "Вакансия", "url": link})

                for user in active_users:
                    user_cats = json.loads(user.get("categories") or "[]")
                    if any(c in user_cats for c in matched_cats):
                        await send_vacancy(user["chat_id"], notification, buttons)
                        await asyncio.sleep(0.05)

                found += 1
                logger.info(f"📨 {post_id}: {matched_cats}")
                await asyncio.sleep(0.5)

        except (ChannelInvalid, UsernameNotOccupied):
            logger.warning(f"⚠️ Недоступен: {username}")
        except FloodWait as e:
            logger.warning(f"⏳ FloodWait {e.value}s")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"❌ {username}: {e}")

        await asyncio.sleep(1.5)

    db.cleanup_seen()
    logger.info(f"✅ Готово. Вакансий: {found}")
    return found
