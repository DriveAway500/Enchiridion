import asyncio
import os
from dataclasses import dataclass

import aiosqlite

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "language.db"
)


@dataclass
class GuildLanguage:
    guild_id: int
    language: str


class LanguageDatabase:

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
                CREATE TABLE IF NOT EXISTS guild_languages (
                    guild_id INTEGER PRIMARY KEY,
                    language TEXT NOT NULL
                )
                """
            )
            await db.commit()
            self._initialized = True
            print(f"[db] usando banco de dados em: {self.db_path}")

    async def get_language(self, guild_id, default="pt_BR"):
        await self._ensure_init()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT language FROM guild_languages WHERE guild_id = ?",
                (guild_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if row:
            return row[0]
        return default

    async def set_language(self, guild_id, language):
        await self._ensure_init()
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO guild_languages (guild_id, language)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    language=excluded.language
                """,
                (guild_id, language),
            )
            await db.commit()


lang_db = LanguageDatabase()