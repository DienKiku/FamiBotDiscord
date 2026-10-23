from datetime import datetime, timezone
from pathlib import Path
import aiosqlite

class Database:
    def __init__(self, database_path: Path):
        self.database_path = str(database_path)

    async def initialize(self):
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA foreign_keys=ON")

            # Bảng quản lý công việc (Tasks)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # ĐÃ SỬA: Thêm guild_id vào Leveling
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS leveling (
                    guild_id INTEGER,
                    user_id INTEGER,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    PRIMARY KEY(guild_id, user_id)
                )
                """
            )

            # Bảng quản lý cảnh cáo (Warnings)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # ĐÃ SỬA: Thêm guild_id vào Economy
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS economy (
                    guild_id INTEGER,
                    user_id INTEGER,
                    coins INTEGER DEFAULT 0,
                    last_daily TEXT,
                    PRIMARY KEY(guild_id, user_id)
                )
                """
            )

            await db.commit()

    # ==========================================
    # CÁC HÀM XỬ LÝ NHÓM CÔNG VIỆC (TASKS)
    # ==========================================
    async def add_task(self, guild_id: int, user_id: int, content: str):
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks (guild_id, user_id, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (guild_id, user_id, content, created_at),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_tasks(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, content, created_at
                FROM tasks
                WHERE guild_id = ? AND user_id = ?
                ORDER BY id ASC
                """,
                (guild_id, user_id),
            )
            return await cursor.fetchall()

    async def complete_task(self, guild_id: int, user_id: int, position: int):
        tasks = await self.get_tasks(guild_id, user_id)
        if position < 1 or position > len(tasks):
            return None
        selected_task = tasks[position - 1]
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                """
                DELETE FROM tasks
                WHERE id = ? AND guild_id = ? AND user_id = ?
                """,
                (selected_task["id"], guild_id, user_id),
            )
            await db.commit()
        return selected_task["content"]

    # ==========================================
    # CÁC HÀM XỬ LÝ QUẢN TRỊ (WARNINGS)
    # ==========================================
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (guild_id, user_id, moderator_id, reason, created_at),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, moderator_id, reason, created_at
                FROM warnings
                WHERE guild_id = ? AND user_id = ?
                ORDER BY id DESC
                """,
                (guild_id, user_id),
            )
            return await cursor.fetchall()

    async def remove_warning(self, guild_id: int, warning_id: int):
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM warnings
                WHERE guild_id = ? AND id = ?
                """,
                (guild_id, warning_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    # ==========================================
    # CÁC HÀM HỆ THỐNG KINH TẾ (ECONOMY) - ĐÃ CẬP NHẬT
    # ==========================================
    async def get_balance(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute("SELECT coins FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                
                await db.execute("INSERT INTO economy (guild_id, user_id, coins) VALUES (?, ?, ?)", (guild_id, user_id, 500))
                await db.commit()
                return 500

    async def update_balance(self, guild_id: int, user_id: int, amount: int):
        current = await self.get_balance(guild_id, user_id)
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute("UPDATE economy SET coins = ? WHERE guild_id = ? AND user_id = ?", (current + amount, guild_id, user_id))
            await db.commit()

    async def check_daily(self, guild_id: int, user_id: int) -> str | None:
        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute("SELECT last_daily FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_daily(self, guild_id: int, user_id: int, date_str: str):
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute("UPDATE economy SET last_daily = ? WHERE guild_id = ? AND user_id = ?", (date_str, guild_id, user_id))
            await db.commit()

    # ==========================================
    # CÁC HÀM HỆ THỐNG CẤP ĐỘ (LEVELING) - ĐÃ CẬP NHẬT
    # ==========================================
    async def get_level_data(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute("SELECT xp, level FROM leveling WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {"xp": row[0], "level": row[1]}
                
                await db.execute("INSERT INTO leveling (guild_id, user_id, xp, level) VALUES (?, ?, 0, 1)", (guild_id, user_id))
                await db.commit()
                return {"xp": 0, "level": 1}

    async def update_level_data(self, guild_id: int, user_id: int, xp: int, level: int):
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                "UPDATE leveling SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?", 
                (xp, level, guild_id, user_id)
            )
            await db.commit()