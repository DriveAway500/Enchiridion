import asyncio
import os
import time
from dataclasses import dataclass

import aiosqlite

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feeds.db")


@dataclass
class FeedSubscription:
    guild_id: int
    channel_id: int
    min_severity: float = 0.0
    allow_unknown: bool = True
    webhook_url: str | None = None


class FeedDatabase:

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_init(self):
        if self._initialized:
            return
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    min_severity REAL NOT NULL DEFAULT 0.0,
                    allow_unknown INTEGER NOT NULL DEFAULT 1,
                    webhook_url TEXT,
                    PRIMARY KEY (guild_id, channel_id)
                )
                """
            )
            try:
                await db.execute("ALTER TABLE subscriptions ADD COLUMN webhook_url TEXT")
            except Exception:
                pass
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_items (
                    item_id TEXT PRIMARY KEY,
                    sent_at INTEGER NOT NULL
                )
                """
            )
            await db.commit()
            self._initialized = True
            print(f"[db] usando banco de dados em: {self.db_path}")

    async def add_subscription(
        self,
        guild_id,
        channel_id,
        min_severity=0.0,
        allow_unknown=True,
        webhook_url=None,
    ):
        await self._ensure_init()
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO subscriptions
                    (guild_id, channel_id, min_severity, allow_unknown, webhook_url)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, channel_id) DO UPDATE SET
                    min_severity=excluded.min_severity,
                    allow_unknown=excluded.allow_unknown,
                    webhook_url=excluded.webhook_url
                """,
                (guild_id, channel_id, min_severity, int(allow_unknown), webhook_url),
            )
            await db.commit()

    async def remove_subscription(self, guild_id, channel_id):
        await self._ensure_init()
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM subscriptions WHERE guild_id = ? AND channel_id = ?",
                (guild_id, channel_id),
            )
            await db.commit()

    async def update_severity_filter(
        self,
        guild_id,
        channel_id,
        min_severity,
        allow_unknown=None,
    ):
        await self._ensure_init()
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            if allow_unknown is None:
                await db.execute(
                    "UPDATE subscriptions SET min_severity = ? WHERE guild_id = ? AND channel_id = ?",
                    (min_severity, guild_id, channel_id),
                )
            else:
                await db.execute(
                    """
                    UPDATE subscriptions
                    SET min_severity = ?, allow_unknown = ?
                    WHERE guild_id = ? AND channel_id = ?
                    """,
                    (min_severity, int(allow_unknown), guild_id, channel_id),
                )
            await db.commit()

    async def list_subscriptions(self):
        await self._ensure_init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT guild_id, channel_id, min_severity, allow_unknown, webhook_url
                FROM subscriptions
                """
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            FeedSubscription(
                guild_id=row["guild_id"],
                channel_id=row["channel_id"],
                min_severity=row["min_severity"],
                allow_unknown=bool(row["allow_unknown"]),
                webhook_url=row["webhook_url"],
            )
            for row in rows
        ]

    async def list_subscriptions_for_guild(self, guild_id):
        subs = await self.list_subscriptions()
        return [s for s in subs if s.guild_id == guild_id]

    async def is_sent(self, item_id):
        await self._ensure_init()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM sent_items WHERE item_id = ?", (item_id,)
            ) as cursor:
                row = await cursor.fetchone()
        return row is not None

    async def mark_sent(self, item_id):
        await self._ensure_init()
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO sent_items (item_id, sent_at) VALUES (?, ?)",
                (item_id, int(time.time())),
            )
            await db.commit()

db = FeedDatabase()