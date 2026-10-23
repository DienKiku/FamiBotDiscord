import discord
from discord.ext import commands
import asyncio
import aiosqlite
import os

C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)
C_GOLD = discord.Color.from_rgb(255, 215, 0)

DROP_TIMEOUT = 300
TAX_RATE = 0.05
MIN_PAY = 100
MIN_DROP = 500

class DropView(discord.ui.View):
    def __init__(self, cog, guild_id, dropper_id, amount):
        super().__init__(timeout=DROP_TIMEOUT)
        self.cog = cog
        self.guild_id = guild_id
        self.dropper_id = dropper_id
        self.amount = amount
        self.claimed = False
        self._claim_lock = asyncio.Lock()  

    async def on_timeout(self):
        if not self.claimed:
            await self.cog.add_balance(self.guild_id, self.dropper_id, self.amount)
            for item in self.children:
                item.disabled = True

    @discord.ui.button(label="Nhặt Quà 🎁", style=discord.ButtonStyle.success, emoji="✨")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._claim_lock:
            if self.claimed:
                return await interaction.response.send_message("⚠️ Hộp quà này đã có người nhặt rồi!", ephemeral=True)
            if interaction.user.id == self.dropper_id:
                return await interaction.response.send_message("⚠️ Bạn không thể tự nhặt quà của chính mình!", ephemeral=True)

            self.claimed = True
            for item in self.children:
                item.disabled = True

            await self.cog.add_balance(self.guild_id, interaction.user.id, self.amount)
            embed = discord.Embed(
                description=f"🎉 **{interaction.user.display_name}** đã nhặt được 💎 **{self.amount:,}** nguyên thạch!",
                color=C_SUCCESS
            )
            await interaction.response.edit_message(embed=embed, view=self)

class Social(commands.Cog):
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
            if cid in ignored and ("all" in ignored[cid] or "game" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng chuyển tiền!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    async def ensure_table(self, db):
        await db.execute('''CREATE TABLE IF NOT EXISTS economy (
            guild_id INTEGER, user_id INTEGER, coins INTEGER DEFAULT 0, PRIMARY KEY(guild_id, user_id))''')

    async def get_balance(self, guild_id, user_id):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
            await db.commit()
            cur = await db.execute("SELECT coins FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cur.fetchone()
            return row[0] if row else 0

    async def try_deduct_balance(self, guild_id, user_id, amount) -> bool:
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
            cur = await db.execute(
                "UPDATE economy SET coins = coins - ? WHERE guild_id = ? AND user_id = ? AND coins >= ?",
                (amount, guild_id, user_id, amount)
            )
            await db.commit()
            return cur.rowcount > 0

    async def add_balance(self, guild_id, user_id, amount):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
            await db.execute("UPDATE economy SET coins = coins + ? WHERE guild_id = ? AND user_id = ?", (amount, guild_id, user_id))
            await db.commit()

    @commands.hybrid_command(name="pay", description="Chuyển nguyên thạch cho người khác (Phí giao dịch 5%).")
    async def pay(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount < MIN_PAY:
            return await ctx.send(embed=discord.Embed(description=f"⚠️ Số tiền chuyển tối thiểu là **{MIN_PAY} nguyên thạch**!", color=C_WARN))
        if member == ctx.author or member.bot:
            return await ctx.send(embed=discord.Embed(description="⚠️ Đối tượng nhận tiền không hợp lệ!", color=C_WARN))

        success = await self.try_deduct_balance(ctx.guild.id, ctx.author.id, amount)
        if not success:
            balance = await self.get_balance(ctx.guild.id, ctx.author.id)
            return await ctx.send(embed=discord.Embed(
                description=f"❌ Bạn không đủ tiền! Số dư hiện tại tại Server này: **{balance:,} nguyên thạch**", color=C_ERROR
            ))

        fee = int(amount * TAX_RATE)
        received = amount - fee
        await self.add_balance(ctx.guild.id, member.id, received)

        embed = discord.Embed(
            title="💸 GIAO DỊCH THÀNH CÔNG",
            description=(
                f"**{ctx.author.display_name}** ➡️ **{member.display_name}**\n"
                f"💰 Số tiền gửi: `{amount:,}` nguyên thạch\n"
                f"🧾 Phí giao dịch (5%): `{fee:,}` nguyên thạch\n"
                f"✅ Người nhận thực nhận: `{received:,}` nguyên thạch"
            ),
            color=C_SUCCESS
        )
        embed.set_footer(text=f"✨ FamiBot • Giao dịch an toàn tại {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="drop", description="Thả hộp quà nguyên thạch ra kênh cho mọi người tranh giành.")
    async def drop(self, ctx: commands.Context, amount: int):
        if amount < MIN_DROP:
            return await ctx.send(embed=discord.Embed(description=f"⚠️ Số tiền thả tối thiểu là **{MIN_DROP} nguyên thạch**!", color=C_WARN))

        success = await self.try_deduct_balance(ctx.guild.id, ctx.author.id, amount)
        if not success:
            balance = await self.get_balance(ctx.guild.id, ctx.author.id)
            return await ctx.send(embed=discord.Embed(
                description=f"❌ Bạn không đủ tiền để thả! Số dư hiện tại tại Server này: **{balance:,} nguyên thạch**", color=C_ERROR
            ))

        embed = discord.Embed(
            title="🎁 HỘP QUÀ MAY MẮN!",
            description=(
                f"**{ctx.author.display_name}** vừa thả một hộp quà chứa 💎 **{amount:,}** nguyên thạch!\n"
                f"Nhanh tay bấm nút bên dưới để nhặt trước khi hết hạn (5 phút)! ⏳"
            ),
            color=C_GOLD
        )
        embed.set_footer(text="✨ FamiBot • Ai nhanh tay hơn sẽ thắng!")
        view = DropView(self, ctx.guild.id, ctx.author.id, amount)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Social(bot))