import discord
from discord import app_commands
from discord.ext import commands

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "general" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng General!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    @commands.hybrid_command(name="ping", description="Kiểm tra độ trễ của bot.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)

        if latency < 120:
            icon, status, color = "🟢", "Kết nối cực kỳ mượt mà!", C_SUCCESS
        elif latency < 250:
            icon, status, color = "🟡", "Kết nối ổn định.", C_WARN
        else:
            icon, status, color = "🔴", "Đường truyền đang hơi lag!", C_ERROR

        embed = discord.Embed(
            title="🏓 Pong! Pong!",
            description=(
                f"{icon} **Trạng thái:** {status}\n"
                f"📶 **Độ trễ:** `{latency} ms`"
            ),
            color=color,
        )
        embed.set_footer(text="✨ FamiBot • Hệ thống phản hồi")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    # ✅ Thêm error handler riêng cho cooldown, tránh hiện lỗi mặc định khó hiểu
    @ping.error
    async def ping_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"⏳ Bạn thao tác quá nhanh! Thử lại sau `{error.retry_after:.1f}s` nhé.",
                color=C_WARN
            )
            try:
                await ctx.send(embed=embed, ephemeral=True)
            except TypeError:
                await ctx.send(embed=embed)

    @commands.hybrid_command(name="hello", description="Chào hỏi FamiBot.")
    async def hello(self, ctx: commands.Context):
        embed = discord.Embed(
            title="👋 Xin chào, mình là FamiBot!",
            description=(
                f"Rất vui được gặp bạn, {ctx.author.mention}! 🥰\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "Mình là trợ thủ quản lý server **đa zi năng**:\n"
                "> 💰 Kiếm tiền • Quay Gacha Genshin\n"
                "> ⚔️ Xếp đội • Săn Boss • Cày cấp\n"
                "> 🎵 Nghe nhạc • Trò chuyện cùng AI\n\n"
                "💡 *Gõ* `f!help` *hoặc* `/help` *để khám phá toàn bộ sức mạnh của mình nhé!*"
            ),
            color=C_BRAND,
        )
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="✨ FamiBot • Luôn sẵn sàng phục vụ bạn")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="Xem ảnh đại diện của một thành viên.")
    @app_commands.describe(member="Thành viên muốn xem ảnh đại diện")
    async def avatar(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        avatar_url = member.display_avatar.url
        color = member.color if member.color.value else C_BRAND

        embed = discord.Embed(
            title=f"🖼️ Ảnh đại diện • {member.display_name}",
            description=f"🔗 [Bấm vào đây để tải ảnh gốc chất lượng cao]({avatar_url})",
            color=color,
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"✨ FamiBot • ID: {member.id}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Xem thông tin server chi tiết.")
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans

        categories = len(guild.categories)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        real_channels = text_channels + voice_channels
        real_roles = len(guild.roles) - 1

        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=C_BRAND,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Chủ sở hữu", value=guild.owner.mention if guild.owner else "Không xác định", inline=True)
        embed.add_field(name="🆔 ID Server", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Ngày thành lập", value=discord.utils.format_dt(guild.created_at, style="D"), inline=True)
        embed.add_field(name=f"👥 Thành viên • {total_members}", value=f"👤 Người dùng: **{humans}**\n🤖 Bot: **{bots}**", inline=True)
        embed.add_field(name=f"📺 Kênh • {real_channels}", value=f"💬 Văn bản: **{text_channels}**\n🔊 Thoại: **{voice_channels}**\n📁 Danh mục: **{categories}**", inline=True)
        embed.add_field(name="🏷️ Vai trò", value=f"**{real_roles}** roles", inline=True)

        embed.set_footer(text="✨ FamiBot • Thông tin máy chủ")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Xem thông tin thành viên.")
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        color = member.color if member.color.value else C_BRAND

        embed = discord.Embed(
            title=f"👤 Hồ Sơ Thành Viên • {member.display_name}",
            description="▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=color,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🪪 Tên tài khoản", value=f"`{member.name}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="🎖️ Vai trò cao nhất", value=member.top_role.mention, inline=True)
        embed.add_field(
            name="📅 Ngày tạo tài khoản",
            value=f"{discord.utils.format_dt(member.created_at, style='D')}\n*({discord.utils.format_dt(member.created_at, style='R')})*",
            inline=True,
        )
        if member.joined_at:
            embed.add_field(
                name="📥 Ngày gia nhập server",
                value=f"{discord.utils.format_dt(member.joined_at, style='D')}\n*({discord.utils.format_dt(member.joined_at, style='R')})*",
                inline=True,
            )

        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        if roles:
            display_roles = roles[:8]
            more = f" *(+{len(roles) - 8} vai trò khác)*" if len(roles) > 8 else ""
            embed.add_field(name=f"🏷️ Vai trò ({len(roles)})", value=" ".join(display_roles) + more, inline=False)

        embed.set_footer(text="✨ FamiBot • Hồ sơ thành viên")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
