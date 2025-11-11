"""
db.py — слой данных для DailyZodiakBot.

Таблица users:
  - user_id (PK)             — Telegram user id
  - sign                     — знак зодиака (строка из списка)
  - notify_hour INTEGER      — час суток (0..23), когда слать сообщение
  - subscribed INTEGER       — 1/0 — подписка включена/выключена
  - last_sent_date TEXT      — 'YYYY-MM-DD', чтобы не слать повторно за день

Приёмы:
  - отдельное подключение под каждую операцию (with _connect());
  - PRAGMA: WAL + busy_timeout + row_factory=Row (см. Л3) [oai_citation:5‡L3.pdf](file-service://file-TzQZFVK22mksuAGPBby5ME);
  - все SQL — параметризованные через "?" (никаких f-строк).
"""

from __future__ import annotations
import sqlite3
import logging
from typing import Optional

from config2 import DB_PATH, DEFAULT_NOTIFY_HOUR

log = logging.getLogger(__name__)


# ---------- подключение с «правильными» PRAGMA (см. Л3) ----------
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn
# WAL + busy_timeout уменьшают «database is locked», row_factory даёт доступ к полям по имени [oai_citation:6‡L3.pdf](file-service://file-TzQZFVK22mksuAGPBby5ME)


# ---------- инициализация схемы ----------
def init_db() -> None:
    """
    Создаёт таблицу users, если её нет.
    Простейшие разумные дефолты; CHECK-ограничения оставим на стороне логики.
    """
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        user_id        INTEGER PRIMARY KEY,
        sign           TEXT,
        notify_hour    INTEGER NOT NULL DEFAULT 9,
        subscribed     INTEGER NOT NULL DEFAULT 1,
        last_sent_date TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_users_hour ON users(notify_hour);
    CREATE INDEX IF NOT EXISTS idx_users_sent ON users(last_sent_date);

    CREATE TABLE IF NOT EXISTS models (
    
        id              INTEGER PRIMARY KEY,
        key             TEXT NOT NULL UNIQUE,
        lable           TEXT NOT NULL,
        active          INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0,1))

    
    );

    CREATE UNIQUE INDEX IF NOT EXISTS ux_models_single_active ON models(active) WHERE active=1;

    """
    with _connect() as conn:
        conn.executescript(schema)
    log.info("DB initialized: %s", DB_PATH)


# ---------- upsert/получение пользователя ----------
def ensure_user(user_id: int) -> None:
    """Гарантируем наличие строки пользователя с дефолтами."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(user_id, notify_hour, subscribed) VALUES (?, ?, 1)",
            (user_id, DEFAULT_NOTIFY_HOUR)
        )

def get_user(user_id: int) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()


# ---------- настройки профиля ----------
def set_sign(user_id: int, sign: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE users SET sign = ? WHERE user_id = ?", (sign, user_id))

def set_notify_hour(user_id: int, hour: int) -> None:
    hour = max(0, min(int(hour), 23))
    with _connect() as conn:
        conn.execute("UPDATE users SET notify_hour = ? WHERE user_id = ?", (hour, user_id))

def set_subscribed(user_id: int, on: bool) -> None:
    val = 1 if on else 0
    with _connect() as conn:
        conn.execute("UPDATE users SET subscribed = ? WHERE user_id = ?", (val, user_id))


# ---------- рассылка: выборка и отметка отправки ----------
def list_due_users(today_str: str, hour: int) -> list[sqlite3.Row]:
    """
    Вернёт пользователей, кому надо отправить: подписан, час совпал, ещё не отправляли сегодня, знак задан.
    """
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT user_id, sign
            FROM users
            WHERE subscribed = 1
              AND sign IS NOT NULL
              AND notify_hour = ?
              AND (last_sent_date IS NULL OR last_sent_date <> ?)
            """,
            (hour, today_str)
        )
        return cur.fetchall()

def mark_sent_today(user_id: int, today_str: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE users SET last_sent_date = ? WHERE user_id = ?", (today_str, user_id))



def ensure_models() -> None:
    """Добавляет стандартные модели, если таблица пуста."""
    default_models = [
        ("gpt-5", "GPT-5 (OpenAI)"),
        ("gpt-4o-mini", "GPT-4o-mini"),
        ("gpt-4o", "GPT-4o"),
        ("claude-3.5-sonnet", "Claude 3.5 Sonnet"),
        ("gemini-1.5-pro", "Gemini 1.5 Pro"),
        ("mistral-large", "Mistral Large"),
        ("llama-3.1-70b", "LLaMA 3.1 70B"),
        ("qwen-2.5-72b", "Qwen 2.5 72B"),
        ("mixtral-8x22b", "Mixtral 8x22B"),
        ("command-r-plus", "Command-R Plus"),
    ]

    with _connect() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM models")
        count = cur.fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO models (key, lable, active) VALUES (?, ?, 0)",
                default_models,
            )
            # По умолчанию активна первая
            conn.execute("UPDATE models SET active = 1 WHERE key = ?", (default_models[0][0],))
            log.info("Модели добавлены в таблицу: %d шт.", len(default_models))
