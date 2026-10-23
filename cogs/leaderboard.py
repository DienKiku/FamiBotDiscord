import discord
from discord.ext import commands
import aiosqlite

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_GOLD = discord.Color.from_rgb(255, 215, 0)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "game" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng BXH!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    def resolve_name(self, ctx, user_id: int) -> str:
        member = ctx.guild.get_member(user_id)
        return member.display_name if member else f"Người dùng đã rời server ({user_id})"

    @commands.hybrid_command(name="topcoin", description="Xem bảng xếp hạng 10 đại gia giàu nhất server.")
    async def topcoin(self, ctx: commands.Context):
        try:
            async with aiosqlite.connect(self.bot.database.database_path, timeout=60.0) as db:
                # Đã thêm truy vấn cô lập theo guild_id
                cursor = await db.execute("SELECT user_id, coins FROM economy WHERE guild_id = ? ORDER BY coins DESC LIMIT 10", (ctx.guild.id,))
                rows = await cursor.fetchall()
        except Exception as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi truy vấn dữ liệu: `{e}`", color=C_WARN))

        if not rows:
            return await ctx.send(embed=discord.Embed(
                description="📭 Bảng xếp hạng đang trống. Chưa có ai kiếm được nguyên thạch nào trong Server này!",
                color=C_WARN
            ))

        lines = []
        for index, row in enumerate(rows, start=1):
            user_id, coins = row
            name = self.resolve_name(ctx, user_id)
            medal = MEDALS.get(index, f"`#{index}`")
            lines.append(f"{medal} **{name}**\n> 💰 `{coins:,} nguyên thạch`")

        embed = discord.Embed(
            title="🏆 BẢNG VÀNG ĐẠI GIA SERVER 🏆",
            description=(
                "**Top 10 người sở hữu tài sản khổng lồ nhất**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                + "\n".join(lines)
            ),
            color=C_GOLD
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.set_footer(text=f"✨ FamiBot • Server: {ctx.guild.name}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="toplevel", description="Xem bảng xếp hạng 10 người cấp độ cao nhất.")
    async def toplevel(self, ctx: commands.Context):
        try:
            async with aiosqlite.connect(self.bot.database.database_path, timeout=60.0) as db:
                # Đã thêm truy vấn cô lập theo guild_id
                cursor = await db.execute("SELECT user_id, level, xp FROM leveling WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (ctx.guild.id,))
                rows = await cursor.fetchall()
        except Exception as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi truy vấn dữ liệu: `{e}`", color=C_WARN))

        if not rows:
            return await ctx.send(embed=discord.Embed(
                description="📭 Chưa có ai tham gia trò chuyện trong Server này để nhận Cấp độ!",
                color=C_WARN
            ))

        lines = []
        for index, row in enumerate(rows, start=1):
            user_id, level, xp = row
            name = self.resolve_name(ctx, user_id)
            medal = MEDALS.get(index, f"`#{index}`")
            lines.append(f"{medal} **{name}**\n> ⭐ Cấp `{level}` • ✨ `{xp:,} XP`")

        embed = discord.Embed(
            title="🌟 BẢNG VÀNG CAO THỦ CẤP ĐỘ 🌟",
            description=(
                "**Top 10 thành viên hoạt động tích cực nhất**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                + "\n".join(lines)
            ),
            color=C_SUCCESS
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.set_footer(text=f"✨ FamiBot • Server: {ctx.guild.name}")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))