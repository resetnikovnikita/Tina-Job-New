"""
db.py — SQLite база данных
"""
import sqlite3, json
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = "tina.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id    INTEGER PRIMARY KEY,
            username   TEXT,
            joined_at  TEXT DEFAULT (datetime('now')),
            trial_ends TEXT,
            sub_ends   TEXT,
            plan       TEXT,
            categories TEXT DEFAULT '[]',
            promo_used INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS seen_posts (
            post_id TEXT PRIMARY KEY,
            seen_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS payments (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id  INTEGER,
            plan     TEXT,
            amount   INTEGER,
            paid_at  TEXT DEFAULT (datetime('now')),
            yoo_id   TEXT
        );
        CREATE TABLE IF NOT EXISTS license_keys (
            key          TEXT PRIMARY KEY,
            status       TEXT DEFAULT 'inactive',
            activated_by INTEGER,
            activated_at TEXT,
            expires_at   TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        );
        """)

def get_user(chat_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,)).fetchone()
        return dict(row) if row else None

def upsert_user(chat_id: int, username: str = None):
    with get_conn() as conn:
        existing = conn.execute("SELECT chat_id FROM users WHERE chat_id=?", (chat_id,)).fetchone()
        if not existing:
            trial_ends = (datetime.now() + timedelta(days=2)).isoformat()
            conn.execute(
                "INSERT INTO users (chat_id, username, trial_ends) VALUES (?,?,?)",
                (chat_id, username, trial_ends)
            )
        elif username:
            conn.execute("UPDATE users SET username=? WHERE chat_id=?", (username, chat_id))

def get_categories(chat_id: int) -> list:
    user = get_user(chat_id)
    if not user:
        return []
    try:
        return json.loads(user["categories"] or "[]")
    except Exception:
        return []

def set_categories(chat_id: int, cats: list):
    with get_conn() as conn:
        conn.execute("UPDATE users SET categories=? WHERE chat_id=?", (json.dumps(cats), chat_id))

def is_active(chat_id: int) -> bool:
    user = get_user(chat_id)
    if not user:
        return False
    now = datetime.now()
    t = user.get("trial_ends")
    s = user.get("sub_ends")
    return (bool(t) and datetime.fromisoformat(t) > now) or \
           (bool(s) and datetime.fromisoformat(s) > now)

def has_paid_sub(chat_id: int) -> bool:
    user = get_user(chat_id)
    if not user:
        return False
    s = user.get("sub_ends")
    return bool(s) and datetime.fromisoformat(s) > datetime.now()

def get_sub_info(chat_id: int) -> dict:
    user = get_user(chat_id)
    if not user:
        return {"active": False}
    now = datetime.now()
    trial = user.get("trial_ends")
    sub   = user.get("sub_ends")
    if sub and datetime.fromisoformat(sub) > now:
        delta = datetime.fromisoformat(sub) - now
        return {"active": True, "type": "key", "days_left": delta.days + 1, "plan": user.get("plan")}
    if trial and datetime.fromisoformat(trial) > now:
        delta = datetime.fromisoformat(trial) - now
        return {"active": True, "type": "trial", "days_left": delta.days + 1}
    return {"active": False}

def activate_subscription(chat_id: int, plan_key: str, days: int):
    with get_conn() as conn:
        user = get_user(chat_id)
        if user and user.get("sub_ends"):
            try:
                base = max(datetime.fromisoformat(user["sub_ends"]), datetime.now())
            except Exception:
                base = datetime.now()
        else:
            base = datetime.now()
        new_end = (base + timedelta(days=days)).isoformat()
        conn.execute("UPDATE users SET sub_ends=?, plan=? WHERE chat_id=?", (new_end, plan_key, chat_id))

def save_payment(chat_id: int, plan: str, amount: int, yoo_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO payments (chat_id, plan, amount, yoo_id) VALUES (?,?,?,?)",
            (chat_id, plan, amount, yoo_id)
        )

def get_all_active_users() -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
    now = datetime.now()
    result = []
    for row in rows:
        d = dict(row)
        t = d.get("trial_ends")
        s = d.get("sub_ends")
        if (t and datetime.fromisoformat(t) > now) or (s and datetime.fromisoformat(s) > now):
            result.append(d)
    return result

def is_seen(post_id: str) -> bool:
    with get_conn() as conn:
        return conn.execute("SELECT 1 FROM seen_posts WHERE post_id=?", (post_id,)).fetchone() is not None

def mark_seen(post_id: str):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO seen_posts (post_id) VALUES (?)", (post_id,))

def cleanup_seen(keep: int = 2000):
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM seen_posts").fetchone()[0]
        if count > keep:
            conn.execute("""DELETE FROM seen_posts WHERE post_id NOT IN (
                SELECT post_id FROM seen_posts ORDER BY seen_at DESC LIMIT ?)""", (keep,))

def get_stats() -> dict:
    with get_conn() as conn:
        total       = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        paid        = conn.execute("SELECT COUNT(*) FROM users WHERE sub_ends > datetime('now')").fetchone()[0]
        trial       = conn.execute("SELECT COUNT(*) FROM users WHERE trial_ends > datetime('now') AND (sub_ends IS NULL OR sub_ends <= datetime('now'))").fetchone()[0]
        revenue     = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0]
        keys_total  = conn.execute("SELECT COUNT(*) FROM license_keys").fetchone()[0]
        keys_used   = conn.execute("SELECT COUNT(*) FROM license_keys WHERE status='active'").fetchone()[0]
        keys_free   = conn.execute("SELECT COUNT(*) FROM license_keys WHERE status='inactive'").fetchone()[0]
    return {
        "total": total, "paid": paid, "trial": trial, "revenue": revenue,
        "keys_total": keys_total, "keys_used": keys_used, "keys_free": keys_free,
    }

# ── Ключи лицензии ────────────────────────────────────────

def create_license_key(key: str):
    """Сохранить новый ключ со статусом inactive."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO license_keys (key, status) VALUES (?, 'inactive')",
            (key,)
        )

def get_license_key(key: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM license_keys WHERE key=?", (key,)).fetchone()
        return dict(row) if row else None

def activate_license_key(key: str, chat_id: int, days: int = 30) -> datetime | None:
    """
    Активировать ключ для пользователя.
    Возвращает дату истечения или None если ключ не найден / уже использован.
    """
    now     = datetime.now()
    expires = now + timedelta(days=days)
    with get_conn() as conn:
        conn.execute(
            """UPDATE license_keys
               SET status='active', activated_by=?, activated_at=?, expires_at=?
               WHERE key=? AND status='inactive'""",
            (chat_id, now.isoformat(), expires.isoformat(), key)
        )
        changed = conn.execute("SELECT changes()").fetchone()[0]
    if not changed:
        return None
    activate_subscription(chat_id, "key", days)
    return expires

def get_all_keys() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM license_keys ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
