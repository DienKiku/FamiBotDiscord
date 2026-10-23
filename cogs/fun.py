import discord
from discord.ext import commands
import aiohttp

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_PINK = discord.Color.from_rgb(255, 105, 180)
C_WARN = discord.Color.from_rgb(254, 231, 92)

FOOTER_FUN = "✨ FamiBot • Góc Giải Trí"


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "fun" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Tương tác (Fun)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    async def cog_load(self):
        # ✅ Tạo 1 session duy nhất khi cog khởi động, dùng lại cho mọi lệnh
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_anime_gif(self, action: str):
        headers = {
            "User-Agent": "FamiBot/1.0 (Discord Bot)",
            "Accept": "application/json"
        }

        # 🟢 TẦNG 1: OtakuGIFs
        url_otaku = f"https://api.otakugifs.xyz/gif?reaction={action}"
        try:
            async with self.session.get(url_otaku, headers=headers, ssl=False, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("url")
                else:
                    print(f"[Cảnh báo] OtakuGIFs trả về mã {response.status}")
        except Exception as e:
            print(f"[Cảnh báo] Lỗi OtakuGIFs ({e}). Chuyển sang Nekos.life...")

        # 🟡 TẦNG 2: Nekos.life
        nekos_action = action
        if action in ["bonk", "yeet"]:
            nekos_action = "slap"
        elif action in ["bite", "highfive", "dance", "poke"]:
            nekos_action = "pat"

        url_nekoslife = f"https://nekos.life/api/v2/img/{nekos_action}"
        try:
            async with self.session.get(url_nekoslife, headers=headers, ssl=False, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("url")
                else:
                    print(f"[Cảnh báo] Nekos.life trả về mã {response.status}")
        except Exception as e:
            print(f"[Cảnh báo] Lỗi Nekos.life ({e}). Dùng ảnh mặc định...")

        # 🔴 TẦNG 3: Ảnh dự phòng cuối cùng
        return "https://media.tenor.com/8-l67_Rk0QkAAAAC/anime-confused.gif"

    def make_action_embed(self, title, description, color):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=FOOTER_FUN)
        return embed

    def warn_embed(self, text):
        return discord.Embed(description=text, color=C_WARN)

    # ================= CƠ BẢN =================
    @commands.hybrid_command(name="hug", description="Ôm một ai đó thật chặt.")
    async def hug(self, ctx: commands.Context, member: discord.Member):
        if member == ctx.author:
            return await ctx.send(embed=self.warn_embed("🤗 Làm sao bạn có thể tự ôm chính mình được? Để FamiBot ôm bạn nhé!"))
        gif_url = await self.fetch_anime_gif("hug")
        embed = self.make_action_embed(
            "💖 Cái Ôm Nồng Ấm!",
            f"**{ctx.author.display_name}** vừa ôm chầm lấy **{member.display_name}**!",
            discord.Color.pink()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pat", description="Xoa đầu một ai đó.")
    async def pat(self, ctx: commands.Context, member: discord.Member):
        gif_url = await self.fetch_anime_gif("pat")
        embed = self.make_action_embed(
            "🌸 Xoa Đầu Ngoan Ngoãn!",
            f"**{ctx.author.display_name}** đang xoa đầu **{member.display_name}**. Ngoan nào!",
            discord.Color.teal()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="slap", description="Tát một đứa bạn cho bõ ghét.")
    async def slap(self, ctx: commands.Context, member: discord.Member):
        if member == self.bot.user:
            return await ctx.send(embed=self.warn_embed("😡 Bạn dám tát mình sao? FamiBot né được rồi nhé!"))
        gif_url = await self.fetch_anime_gif("slap")
        embed = self.make_action_embed(
            "💥 Một Tát Trời Giáng!",
            f"Chát! **{ctx.author.display_name}** vừa vả cho **{member.display_name}** một phát nổ đom đóm mắt!",
            discord.Color.red()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    # ================= TÌNH CẢM =================
    @commands.hybrid_command(name="kiss", description="Hôn một ai đó để thể hiện tình cảm.")
    async def kiss(self, ctx: commands.Context, member: discord.Member):
        if member == ctx.author:
            return await ctx.send(embed=self.warn_embed("🪞 Bạn đang cố tự hôn vào gương đấy à?"))
        gif_url = await self.fetch_anime_gif("kiss")
        embed = self.make_action_embed(
            "💋 Nụ Hôn Ngọt Ngào!",
            f"Ngọt ngào quá! **{ctx.author.display_name}** vừa đặt một nụ hôn lên môi **{member.display_name}**!",
            discord.Color.purple()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="cuddle", description="Rúc vào lòng ai đó âu yếm.")
    async def cuddle(self, ctx: commands.Context, member: discord.Member):
        if member == ctx.author:
            return await ctx.send(embed=self.warn_embed("🥺 Đừng tự kỷ thế chứ, kiếm ai đó để ôm ấp đi nào!"))
        gif_url = await self.fetch_anime_gif("cuddle")
        embed = self.make_action_embed(
            "🛌 Ôm Ấp Âu Yếm!",
            f"Ấm áp quá~ **{ctx.author.display_name}** đang rúc vào lòng âu yếm **{member.display_name}**!",
            discord.Color.blue()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    # ================= TROLL =================
    @commands.hybrid_command(name="bonk", description="Gõ đầu một ai đó vì tội hư đốn.")
    async def bonk(self, ctx: commands.Context, member: discord.Member):
        gif_url = await self.fetch_anime_gif("bonk")
        embed = self.make_action_embed(
            "🔨 Bốp! Đội Nốt Luôn!",
            f"**{ctx.author.display_name}** vừa gõ cho **{member.display_name}** một cục u to đùng trên đầu!",
            discord.Color.gold()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="bite", description="Cắn một ai đó thật đau.")
    async def bite(self, ctx: commands.Context, member: discord.Member):
        gif_url = await self.fetch_anime_gif("bite")
        embed = self.make_action_embed(
            "🦷 Cắn Một Phát Đau Điếng!",
            f"Ngấu nghiến! **{ctx.author.display_name}** vừa cắn **{member.display_name}** một cái đau điếng!",
            discord.Color.dark_red()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="yeet", description="Ném bay một ai đó lên trời.")
    async def yeet(self, ctx: commands.Context, member: discord.Member):
        if member == self.bot.user:
            return await ctx.send(embed=self.warn_embed("😭 Đừng ném mình! Mình còn phải ở lại phát nhạc cho mọi người!"))
        gif_url = await self.fetch_anime_gif("yeet")
        embed = self.make_action_embed(
            "🚀 Bay Màu Khỏi Trái Đất!",
            f"Vút! **{ctx.author.display_name}** vừa ném **{member.display_name}** bay thẳng vào vũ trụ không thương tiếc!",
            discord.Color.dark_gray()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="poke", description="Chọc ngoáy một ai đó.")
    async def poke(self, ctx: commands.Context, member: discord.Member):
        gif_url = await self.fetch_anime_gif("poke")
        embed = self.make_action_embed(
            "👉 Chọt Chọt!",
            f"**{ctx.author.display_name}** đang chọc phá **{member.display_name}** nè!",
            discord.Color.orange()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    # ================= VUI VẺ =================
    @commands.hybrid_command(name="highfive", description="Đập tay ăn mừng cùng ai đó.")
    async def highfive(self, ctx: commands.Context, member: discord.Member):
        gif_url = await self.fetch_anime_gif("highfive")
        embed = self.make_action_embed(
            "✋ Đập Tay Ăn Ý!",
            f"Bốp! **{ctx.author.display_name}** và **{member.display_name}** vừa đập tay cực kỳ ăn ý!",
            discord.Color.green()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="dance", description="Rủ ai đó nhảy múa tưng bừng.")
    async def dance(self, ctx: commands.Context, member: discord.Member = None):
        gif_url = await self.fetch_anime_gif("dance")

        if member and member != ctx.author:
            title = "💃 Quẩy Tung Nóc!"
            desc = f"🕺 **{ctx.author.display_name}** đang kéo **{member.display_name}** vào điệu nhảy sôi động!"
        else:
            title = "🎶 Nhảy Một Mình Cũng Vui!"
            desc = f"**{ctx.author.display_name}** đang nhảy múa tưng bừng một mình. Có ai muốn tham gia không?"

        embed = self.make_action_embed(title, desc, discord.Color.magenta())
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))
