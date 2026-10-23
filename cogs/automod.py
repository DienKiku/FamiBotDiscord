import discord
from discord.ext import commands
import re

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_ERROR = discord.Color.from_rgb(237, 66, 69)


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bad_words = []
        
        self.pattern = None
        # Chỉ compile Regex nếu danh sách bad_words có dữ liệu
        if bad_words:
            self.pattern = re.compile(
                "|".join(r"\b" + re.escape(w) + r"\b" for w in bad_words),
                re.IGNORECASE
            )

    async def is_ignored(self, channel_id: int) -> bool:
        # ✅ Đồng bộ với cache RAM của leveling.py/moderation.py (nếu main.py đã khai báo)
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            return channel_id in ignored
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if await self.is_ignored(message.channel.id):
            return

        # Thêm điều kiện này: Bỏ qua kiểm tra nếu không có pattern (danh sách cấm rỗng)
        if not self.pattern:
            return

        if self.pattern.search(message.content):
            try:
                await message.delete()

                embed = discord.Embed(
                    title="🛡️ AutoMod • Đã gỡ một tin nhắn",
                    description=(
                        f"{message.author.mention}, tin nhắn của bạn chứa **từ ngữ vi phạm** "
                        "quy tắc văn hóa của máy chủ nên đã bị xóa tự động.\n"
                        "> 💡 *Hãy cùng nhau giữ gìn môi trường trò chuyện trong sạch nhé!*"
                    ),
                    color=C_ERROR,
                )
                embed.set_footer(text="✨ FamiBot • Tin nhắn này sẽ tự xóa sau 5 giây")

                await message.channel.send(embed=embed, delete_after=5.0)
            except discord.Forbidden:
                pass
            except discord.NotFound:
                # Tin nhắn đã bị xóa bởi cog/mod khác trước đó
                pass


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
