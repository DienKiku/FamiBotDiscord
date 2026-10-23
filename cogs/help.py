import discord
from discord.ext import commands

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_ERROR = discord.Color.from_rgb(237, 66, 69)

# Bổ sung key "FirebaseSync" vào từ điển quản lý Meta
CATEGORY_META = {
    "General": ("⚙️", "Cơ Bản"),
    "EconomyGacha": ("💰", "Kinh Tế & Gacha"),
    "RPG": ("⚔️", "Chiến Đấu (RPG)"),
    "Music": ("🎵", "Âm Nhạc"),
    "Leveling": ("⭐", "Cấp Độ"),
    "Leaderboard": ("🏆", "Xếp Hạng"),
    "Social": ("💸", "Tương Tác Xã Hội"),
    "MediaEmbed": ("🎥", "Tiện Ích Media"),
    "ChatBot": ("🤖", "Trợ Lý AI"),
    "Fun": ("🎉", "Giải Trí"),
    "Tasks": ("📌", "Công Việc"),
    "TicketSystem": ("🎫", "Hỗ Trợ"),
    "Moderation": ("🛡️", "Quản Lý (Admin)"),
    "FirebaseSync": ("🔄", "Đồng Bộ Dữ Liệu"), # <--- ĐÃ THÊM MỚI Ở ĐÂY
}


class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        # Khai báo thêm SelectOption "Đồng Bộ Dữ Liệu" tương ứng với module FirebaseSync
        options = [
            discord.SelectOption(label="Cơ Bản", description="Các lệnh tra cứu thông tin", value="General", emoji="⚙️"),
            discord.SelectOption(label="Kinh Tế & Gacha", description="Kiếm nguyên thạch, cờ bạc và quay tướng", value="EconomyGacha", emoji="💰"),
            discord.SelectOption(label="Chiến Đấu (RPG)", description="Xếp Team, cày Cấp Độ và Săn Boss", value="RPG", emoji="⚔️"),
            discord.SelectOption(label="Âm Nhạc", description="Phát nhạc YouTube trong kênh Voice", value="Music", emoji="🎵"),
            discord.SelectOption(label="Cấp Độ", description="Hệ thống cấp độ và kinh nghiệm", value="Leveling", emoji="⭐"),
            discord.SelectOption(label="Xếp Hạng", description="Bảng vàng vinh danh đại gia & cấp độ", value="Leaderboard", emoji="🏆"),
            discord.SelectOption(label="Tương Tác Xã Hội", description="Chuyển tiền, Lì xì, Thả hộp quà (Drop)", value="Social", emoji="💸"),
            discord.SelectOption(label="Tiện Ích Media", description="Tự động nhúng video TikTok, Facebook, X...", value="MediaEmbed", emoji="🎥"),
            discord.SelectOption(label="Trợ Lý AI", description="Trò chuyện và hỏi đáp với AI Gemini", value="ChatBot", emoji="🤖"),
            discord.SelectOption(label="Giải Trí", description="Hành động vui nhộn (Ôm, xoa đầu, tát)", value="Fun", emoji="🎉"),
            discord.SelectOption(label="Công Việc", description="Hệ thống quản lý To-Do List", value="Tasks", emoji="📌"),
            discord.SelectOption(label="Hỗ Trợ", description="Tạo ticket liên hệ quản trị", value="TicketSystem", emoji="🎫"),
            discord.SelectOption(label="Quản Lý (Admin)", description="Các lệnh dọn dẹp, ban, kick", value="Moderation", emoji="🛡️"),
            discord.SelectOption(label="Đồng Bộ Dữ Liệu", description="Đẩy/Kéo CSDL từ Firebase (Admin)", value="FirebaseSync", emoji="🔄"), # <--- ĐÃ THÊM MỚI Ở ĐÂY
        ]
        super().__init__(placeholder="📂 Chọn danh mục lệnh bạn muốn khám phá...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        cog = self.bot.get_cog(cog_name)
        emoji, label = CATEGORY_META.get(cog_name, ("📁", cog_name))

        if not cog:
            embed = discord.Embed(
                description=f"❌ Danh mục **{label}** đang bảo trì hoặc chưa được bật.",
                color=C_ERROR
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title=f"{emoji} Danh Mục • {label}",
            description=(
                "✨ Dưới đây là toàn bộ lệnh trong danh mục này.\n"
                "*(Hỗ trợ cả gõ chữ `f!lệnh` lẫn `/lệnh`)*\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            ),
            color=C_BRAND
        )

        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        if cog_name == "MediaEmbed":
            embed.description = (
                "**Module này hoạt động hoàn toàn TỰ ĐỘNG (chạy ngầm)!** ⚙️\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "Bạn không cần gõ lệnh nào cả. Chỉ cần **dán link video** từ:\n"
                "> 🎵 `TikTok`\n"
                "> 📘 `Facebook`\n"
                "> 🐦 `X (Twitter)`\n\n"
                "FamiBot sẽ tự động tải video kèm theo thông số lượt xem/thích "
                "và gửi thẳng lên Discord giúp bạn! 🎥"
            )
            embed.set_footer(text="✨ FamiBot • Tiện ích tự động")
            return await interaction.response.edit_message(embed=embed)

        cmd_count = 0
        for cmd in cog.get_commands():
            if not cmd.hidden:
                embed.add_field(
                    name=f"🔹 `f!{cmd.name}`",
                    value=cmd.description or "Không có mô tả chi tiết.",
                    inline=False
                )
                cmd_count += 1

        if cmd_count == 0:
            embed.add_field(name="📭 Trống", value="Chưa có lệnh nào khả dụng trong danh mục này.")

        embed.set_footer(text=f"✨ FamiBot • {cmd_count} lệnh khả dụng • Chọn danh mục khác ở menu bên dưới")
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class HelpSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "help" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Trợ giúp (Help)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    @commands.hybrid_command(name="help", description="Hiển thị menu hướng dẫn sử dụng toàn bộ tính năng của bot.")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📚 FamiBot • Trung Tâm Hỗ Trợ",
            description=(
                "Chào mừng bạn đến với **bảng điều khiển** của FamiBot! 🎮\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "🔽 **Cách dùng:** Chọn một danh mục ở menu bên dưới để xem các lệnh chi tiết.\n\n"
                "🌟 **Điểm nhấn của bot:**\n"
                "> 💰 Kinh tế • Quay Gacha Genshin\n"
                "> ⚔️ Xếp đội • Cày cấp • Săn Boss\n"
                "> 🎵 Nghe nhạc đa nền tảng\n"
                "> 🤖 Trò chuyện cùng AI thông minh\n"
                "> 🎉 Tương tác vui nhộn cùng bạn bè"
            ),
            color=C_BRAND
        )
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="💡 Gõ dấu / (Slash Command) để trải nghiệm mượt nhất • Menu hết hạn sau 120 giây")

        await ctx.send(embed=embed, view=HelpView(self.bot))


async def setup(bot):
    await bot.add_cog(HelpSystem(bot))