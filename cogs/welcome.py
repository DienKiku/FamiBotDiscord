import logging

import discord
from discord.ext import commands

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)   # Xanh lá


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(
            member.guild.text_channels,
            name="welcome",
        )

        if channel is None:
            logging.info(
                "Server %s chưa có kênh welcome.",
                member.guild.id,
            )
            return

        if not channel.permissions_for(
            member.guild.me
        ).send_messages:
            logging.warning(
                "Bot không có quyền gửi tin nhắn trong kênh %s.",
                channel.id,
            )
            return

        embed = discord.Embed(
            title="🎊 CHÀO MỪNG THÀNH VIÊN MỚI 🎊",
            description=(
                f"Xin chào {member.mention}, rất vui vì bạn đã ghé thăm "
                f"**{member.guild.name}**! 🥳\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"🌟 Bạn chính là thành viên thứ **{member.guild.member_count}** của gia đình!\n"
                "📜 Đừng quên đọc nội quy để giữ server luôn vui vẻ nhé!\n"
                "💬 Hãy chào hỏi và làm quen với mọi người nào~"
            ),
            color=C_SUCCESS,
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        if member.guild.icon:
            embed.set_footer(
                text=f"✨ {member.guild.name} • Chào mừng bạn!",
                icon_url=member.guild.icon.url,
            )
        else:
            embed.set_footer(text=f"✨ {member.guild.name} • Chào mừng bạn!")

        embed.timestamp = discord.utils.utcnow()

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            logging.exception(
                "Không thể gửi welcome cho thành viên %s.",
                member.id,
            )


async def setup(bot):
    await bot.add_cog(Welcome(bot))