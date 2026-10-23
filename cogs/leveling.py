import discord
from discord.ext import commands
import random
import aiosqlite
import os
import asyncio

C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_GOLD = discord.Color.from_rgb(255, 215, 0)

def make_progress_bar(current, maximum, length=14):
    ratio = 1.0 if maximum <= 0 else max(0.0, min(current / maximum, 1.0))
    filled = int(round(ratio * length))
    return "🟩" * filled + "⬛" * (length - filled), int(ratio * 100)

def xp_needed(level):
    return 50 * (level ** 2) + 100

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = getattr(bot.database, "database_path", os.path.join("data", "famibot.db"))
        self.rng = random.Random()
        self._xp_locks = {} 

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "xp" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Thăng cấp (Level)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    def get_lock(self, user_id):
        if user_id not in self._xp_locks:
            self._xp_locks[user_id] = asyncio.Lock()
        return self._xp_locks[user_id]

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("PRAGMA busy_timeout = 60000")
            await self.ensure_table(db)
            await db.commit()

    async def ensure_table(self, db):
        await db.execute('''CREATE TABLE IF NOT EXISTS leveling (
            guild_id INTEGER, user_id INTEGER, level INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, PRIMARY KEY(guild_id, user_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS economy (
            guild_id INTEGER, user_id INTEGER, coins INTEGER DEFAULT 0, PRIMARY KEY(guild_id, user_id))''')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(message.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "xp" in ignored[cid]):
                return

        guild_id = message.guild.id
        user_id = message.author.id
        lock = self.get_lock(user_id)

        async with lock:
            async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
                await db.execute("INSERT OR IGNORE INTO leveling (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
                cur = await db.execute("SELECT level, xp FROM leveling WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                level, xp = await cur.fetchone()

                gained = self.rng.randint(5, 10)
                xp += gained
                needed = xp_needed(level)
                leveled_up = False
                reward = 0

                while xp >= needed:
                    xp -= needed
                    level += 1
                    leveled_up = True
                    reward += level * 1000
                    needed = xp_needed(level)

                await db.execute("UPDATE leveling SET level = ?, xp = ? WHERE guild_id = ? AND user_id = ?", (level, xp, guild_id, user_id))

                if leveled_up and reward > 0:
                    await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
                    await db.execute("UPDATE economy SET coins = coins + ? WHERE guild_id = ? AND user_id = ?", (reward, guild_id, user_id))

                await db.commit()

        if leveled_up:
            try:
                embed = discord.Embed(
                    title="🎉 LÊN CẤP!",
                    description=f"Chúc mừng {message.author.mention} đã đạt **Cấp {level}** tại {message.guild.name}!\n💎 Nhận thêm **{reward:,}** nguyên thạch!",
                    color=C_GOLD
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                embed.set_footer(text="✨ FamiBot • Tiếp tục chat để lên cấp cao hơn!")
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.hybrid_command(name="rank", description="Xem hồ sơ cấp độ của bạn.")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO leveling (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, member.id))
            await db.commit()
            cur = await db.execute("SELECT level, xp FROM leveling WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, member.id))
            level, xp = await cur.fetchone()

        needed = xp_needed(level)
        bar, pct = make_progress_bar(xp, needed)

        embed = discord.Embed(title=f"⭐ Hồ Sơ Cấp Độ • {member.display_name}", color=C_BRAND)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🎖️ Cấp độ hiện tại", value=f"`{level}`", inline=True)
        embed.add_field(name="✨ Kinh nghiệm", value=f"`{xp}/{needed}` ({pct}%)", inline=True)
        embed.add_field(name="📊 Tiến trình", value=bar, inline=False)
        embed.set_footer(text=f"✨ FamiBot • Server: {ctx.guild.name}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))