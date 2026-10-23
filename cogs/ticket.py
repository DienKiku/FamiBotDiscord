import discord
from discord.ext import commands
import asyncio

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Đóng Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("🔒 Phòng hỗ trợ sẽ tự động đóng sau **5 giây**... 👋")
            await asyncio.sleep(5)
            try:
                await interaction.channel.delete()
            except discord.Forbidden:
                await interaction.followup.send("❌ Bot không có quyền xóa kênh này!")
            except discord.NotFound:
                pass
        else:
            await interaction.response.send_message("❌ Chỉ có Ban Quản Trị mới có quyền dọn dẹp phòng ticket này.", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tạo Kênh Trợ Giúp", style=discord.ButtonStyle.success, emoji="🎫", custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        channel_name = f"🎫-ticket-{interaction.user.name}".lower()

        # ✅ Chống spam: kiểm tra user đã có ticket mở chưa
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            return await interaction.response.send_message(
                f"⚠️ Bạn đã có một phòng hỗ trợ đang mở tại {existing.mention} rồi!", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # ✅ Thêm quyền xem cho các role Staff/Mod (có manage_channels), không chỉ riêng Admin
        for role in guild.roles:
            if role.permissions.manage_channels or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Yêu cầu trợ giúp từ người dùng {interaction.user.name}"
            )
        except discord.Forbidden:
            return await interaction.followup.send("❌ Bot không có đủ quyền để tạo kênh! Vui lòng báo Admin cấp quyền `Manage Channels`.", ephemeral=True)

        await interaction.followup.send(f"✅ Đã chuẩn bị phòng chat hỗ trợ riêng cho bạn tại {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title="📞 PHIÊN TRỢ GIÚP KỸ THUẬT",
            description=(
                f"Xin chào {interaction.user.mention}! 👋\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "📝 Hãy **mô tả chi tiết** thắc mắc, lỗi kỹ thuật hoặc báo cáo "
                "thành viên vi phạm tại đây.\n"
                "🛡️ Đội ngũ Quản trị sẽ vào giải quyết trong thời gian sớm nhất.\n\n"
                "🔒 *Khi hoàn tất, Admin có thể ấn nút **Đóng Ticket** phía dưới.*"
            ),
            color=C_SUCCESS
        )
        embed.set_footer(text="✨ FamiBot • Hỗ trợ tận tâm")
        embed.timestamp = discord.utils.utcnow()
        await ticket_channel.send(embed=embed, view=CloseTicketView())


class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "ticket" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Hỗ trợ Ticket", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    @commands.hybrid_command(name="setup_ticket", description="Khởi tạo bảng tạo tin nhắn đăng ký Ticket hỗ trợ.")
    @commands.has_permissions(administrator=True)
    async def setup_ticket(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📞 TRUNG TÂM TRỢ GIÚP CỘNG ĐỒNG",
            description=(
                "Bạn đang gặp khó khăn, sự cố phân quyền hoặc cần khiếu nại vấn đề? 🛠️\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "**📋 Hướng dẫn mở Ticket:**\n"
                "> 1️⃣ Bấm nút **🎫 Tạo Kênh Trợ Giúp** bên dưới\n"
                "> 2️⃣ Một kênh chat **riêng tư** sẽ được tạo cho bạn\n"
                "> 3️⃣ Mô tả chi tiết vấn đề, Ban Quản Trị sẽ vào hỗ trợ\n\n"
                "🔒 *Mọi cuộc trò chuyện đều được bảo mật tuyệt đối.*"
            ),
            color=C_BRAND
        )
        embed.set_footer(text="✨ FamiBot • Luôn lắng nghe bạn 24/7")
        await ctx.send(embed=embed, view=TicketView())

    @setup_ticket.error
    async def setup_ticket_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(
                description="❌ Chỉ **Administrator** mới có quyền khởi tạo hệ thống Ticket!",
                color=C_ERROR
            ))


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
