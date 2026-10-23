import discord
from discord.ext import commands
import aiosqlite
import os

C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)

class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = getattr(bot.database, "database_path", os.path.join("data", "famibot.db"))

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            # Vì đây là file tasks.py nên mã tính năng sẽ là "task"
            if cid in ignored and ("all" in ignored[cid] or "task" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Ghi chú (Tasks)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================    

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("PRAGMA busy_timeout = 60000")
            await self.ensure_table(db)
            await db.commit()

    async def ensure_table(self, db):
        # 1. Khởi tạo bảng chuẩn (Dành cho Server mới tinh chưa có Database)
        await db.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            guild_id INTEGER,
            content TEXT,
            done INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # 2. Tự động "vá" lỗi thiếu cột cho các file Database cũ
        try: 
            await db.execute("ALTER TABLE tasks ADD COLUMN done INTEGER DEFAULT 0")
        except: 
            pass # Nếu cột đã tồn tại thì bỏ qua êm đẹp
            
        try: 
            await db.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except: 
            pass
            
        try: 
            await db.execute("ALTER TABLE tasks ADD COLUMN guild_id INTEGER")
        except: 
            pass

    @commands.hybrid_command(name="todo_add", description="Thêm một công việc cần làm.")
    async def todo_add(self, ctx: commands.Context, *, content: str):
        try:
            async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
                await db.execute(
                    "INSERT INTO tasks (user_id, guild_id, content, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", 
                    (ctx.author.id, ctx.guild.id, content)
                )
                await db.commit()
            await ctx.send(embed=discord.Embed(description=f"✅ Đã thêm công việc: `{content}`", color=C_SUCCESS))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi khi thêm công việc: `{e}`", color=C_ERROR))

    @commands.hybrid_command(name="todo_list", description="Xem danh sách công việc của bạn.")
    async def todo_list(self, ctx: commands.Context):
        try:
            async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
                cur = await db.execute(
                    "SELECT id, content, done FROM tasks WHERE user_id = ? AND guild_id = ? ORDER BY id ASC", (ctx.author.id, ctx.guild.id)
                )
                rows = await cur.fetchall()
        except Exception as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi truy vấn dữ liệu: `{e}`", color=C_ERROR))

        if not rows:
            return await ctx.send(embed=discord.Embed(description="📭 Bạn chưa có công việc nào cả!", color=C_WARN))

        lines = []
        for task_id, content, done in rows:
            icon = "✅" if done else "🔲"
            lines.append(f"{icon} `#{task_id}` {content}")

        embed = discord.Embed(
            title=f"📌 Danh Sách Công Việc • {ctx.author.display_name}",
            description="\n".join(lines),
            color=C_BRAND
        )
        embed.set_footer(text="✨ FamiBot • Dùng /todo_done <id> để hoàn thành")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="todo_done", description="Đánh dấu hoàn thành một công việc.")
    async def todo_done(self, ctx: commands.Context, task_id: int):
        try:
            async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
                cur = await db.execute(
                    "UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ? AND guild_id = ?", (task_id, ctx.author.id, ctx.guild.id)
                )
                await db.commit()
                if cur.rowcount == 0:
                    return await ctx.send(embed=discord.Embed(description="⚠️ Không tìm thấy công việc này của bạn!", color=C_WARN))
            await ctx.send(embed=discord.Embed(description=f"🎉 Đã hoàn thành công việc `#{task_id}`!", color=C_SUCCESS))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi khi cập nhật: `{e}`", color=C_ERROR))

    @commands.hybrid_command(name="todo_remove", description="Xóa một công việc khỏi danh sách.")
    async def todo_remove(self, ctx: commands.Context, task_id: int):
        try:
            async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
                cur = await db.execute(
                    "DELETE FROM tasks WHERE id = ? AND user_id = ? AND guild_id = ?", (task_id, ctx.author.id, ctx.guild.id)
                )
                await db.commit()
                if cur.rowcount == 0:
                    return await ctx.send(embed=discord.Embed(description="⚠️ Không tìm thấy công việc này của bạn!", color=C_WARN))
            await ctx.send(embed=discord.Embed(description=f"🗑️ Đã xóa công việc `#{task_id}`!", color=C_SUCCESS))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi khi xóa: `{e}`", color=C_ERROR))

async def setup(bot):
    await bot.add_cog(Tasks(bot))