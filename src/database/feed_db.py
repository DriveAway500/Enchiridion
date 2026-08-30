import asyncio
import time
from dataclasses import dataclass

import aiosqlite

DEFAULT_DB_PATH = "feeds.db"

@dataclass
class FeedSubscription:
    guild_id: int
    channel_id: int
    min_severity: float = 0.0
    allow_unknown: bool = True
    crosspost_channel_id: int | None = None


class FeedDatabase:

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        """Cria as tabelas necessárias caso ainda não existam."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    min_severity REAL NOT NULL DEFAULT 0.0,
                    allow_unknown INTEGER NOT NULL DEFAULT 1,
                    crosspost_channel_id INTEGER,
                    PRIMARY KEY (guild_id, channel_id)
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_items (
                    item_id TEXT PRIMARY KEY,
                    sent_at INTEGER NOT NULL
                )
                """
            )
            await db.commit()


    async def add_subscription(
        self,
        guild_id: int,
        channel_id: int,
        min_severity: float = 0.0,
        allow_unknown: bool = True,
        crosspost_channel_id: int | None = None,
    ) -> None:
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO subscriptions
                    (guild_id, channel_id, min_severity, allow_unknown, crosspost_channel_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, channel_id) DO UPDATE SET
                    min_severity=excluded.min_severity,
                    allow_unknown=excluded.allow_unknown,
                    crosspost_channel_id=excluded.crosspost_channel_id
                """,
                (guild_id, channel_id, min_severity, int(allow_unknown), crosspost_channel_id),
            )
            await db.commit()

    async def remove_subscription(self, guild_id: int, channel_id: int) -> None:
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM subscriptions WHERE guild_id = ? AND channel_id = ?",
                (guild_id, channel_id),
            )
            await db.commit()

    async def update_severity_filter(
        self,
        guild_id: int,
        channel_id: int,
        min_severity: float,
        allow_unknown: bool | None = None,
    ) -> None:
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

    async def list_subscriptions(self) -> list[FeedSubscription]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT guild_id, channel_id, min_severity, allow_unknown, crosspost_channel_id
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
                crosspost_channel_id=row["crosspost_channel_id"],
            )
            for row in rows
        ]

    async def list_subscriptions_for_guild(self, guild_id: int) -> list[FeedSubscription]:
        subs = await self.list_subscriptions()
        return [s for s in subs if s.guild_id == guild_id]

    async def is_sent(self, item_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM sent_items WHERE item_id = ?", (item_id,)
            ) as cursor:
                row = await cursor.fetchone()
        return row is not None

    async def mark_sent(self, item_id: str) -> None:
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO sent_items (item_id, sent_at) VALUES (?, ?)",
                (item_id, int(time.time())),
            )
            await db.commit()