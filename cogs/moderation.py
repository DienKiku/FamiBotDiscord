import discord
from discord.ext import commands
import json
import os
import aiosqlite
from discord import app_commands

C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)

IGNORED_PATH = os.path.join("data", "ignored_channels.json")


class ConfirmEraseAll(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=30)
        self.cog = cog
        self.confirmed = False

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="XÁC NHẬN XÓA TOÀN SERVER", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Chỉ Admin mới có quyền xác nhận!", ephemeral=True)
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(description="⏳ Đang xóa toàn bộ dữ liệu server...", color=C_WARN), view=self
        )
        await self.cog.do_erase_all(interaction)

    @discord.ui.button(label="Hủy", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(description="✅ Đã hủy thao tác xóa dữ liệu.", color=C_SUCCESS), view=self
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = getattr(bot.database, "database_path", os.path.join("data", "famibot.db"))

        # ✅ Đổi từ set() sang dict {} để lưu chi tiết các tính năng bị chặn
        if not hasattr(bot, "_ignored_channels_cache"):
            bot._ignored_channels_cache = {}

        os.makedirs("data", exist_ok=True)
        if not os.path.exists(IGNORED_PATH):
            with open(IGNORED_PATH, 'w', encoding='utf-8') as f:
                json.dump({}, f) # Khởi tạo là dict rỗng thay vì list []

        if not hasattr(bot, "reload_ignored_channels"):
            async def reload_ignored_channels():
                def _load():
                    if os.path.exists(IGNORED_PATH):
                        with open(IGNORED_PATH, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Tự động chuyển đổi dữ liệu cũ (list) sang dữ liệu mới (dict) để không bị lỗi
                            if isinstance(data, list):
                                return {str(cid): ["all"] for cid in data}
                            return data
                    return {}
                bot._ignored_channels_cache = await bot.loop.run_in_executor(None, _load)
            bot.reload_ignored_channels = reload_ignored_channels

        if not hasattr(bot, "get_ignored_channels_cached"):
            async def get_ignored_channels_cached():
                return bot._ignored_channels_cache
            bot.get_ignored_channels_cached = get_ignored_channels_cached

    async def cog_load(self):
        await self.bot.reload_ignored_channels()

    def save_ignored_sync(self, channels_dict):
        # Lưu dữ liệu dưới dạng dict
        with open(IGNORED_PATH, 'w', encoding='utf-8') as f:
            json.dump(channels_dict, f, indent=4)

    async def check_target(self, ctx: commands.Context, member: discord.Member) -> bool:
        if member == ctx.guild.owner:
            await ctx.send(embed=discord.Embed(description="❌ Không thể xử lý chủ sở hữu server!", color=C_ERROR))
            return False
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send(embed=discord.Embed(description="❌ Bạn không thể xử lý người có vai trò cao hơn hoặc bằng bạn!", color=C_ERROR))
            return False
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send(embed=discord.Embed(description="❌ Bot không có quyền xử lý người có vai trò cao hơn bot!", color=C_ERROR))
            return False
        return True

    # ==========================================
    # 🔇 QUẢN LÝ KÊNH IGNORE ĐA TÍNH NĂNG
    # ==========================================
    @commands.hybrid_command(name="ignore", description="(all, general, help, xp, media, music, game, chat, fun, ticket, task).")
    @app_commands.choices(feature=[
        app_commands.Choice(name="Tất cả (All)", value="all"),
        app_commands.Choice(name="Tổng quan (General)", value="general"),
        app_commands.Choice(name="Trợ giúp (Help)", value="help"),
        app_commands.Choice(name="Kinh nghiệm (XP)", value="xp"),
        app_commands.Choice(name="Nhúng link (Media)", value="media"),
        app_commands.Choice(name="Âm nhạc (Music)", value="music"),
        app_commands.Choice(name="Game & Kinh tế (Gacha, RPG, Boss)", value="game"),
        app_commands.Choice(name="Trò chuyện AI (Ask)", value="chat"),
        app_commands.Choice(name="Giải trí (Hug, Slap...)", value="fun"),
        app_commands.Choice(name="Hỗ trợ (Ticket)", value="ticket"),
        app_commands.Choice(name="Ghi chú (Tasks)", value="task")
    ])
    @commands.has_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context, channel: discord.TextChannel = None, feature: str = "all"):
        channel = channel or ctx.channel
        current = await self.bot.get_ignored_channels_cached()
        cid = str(channel.id)
        
        if cid not in current: current[cid] = []
        if feature not in current[cid]: current[cid].append(feature)
        if feature == "all": current[cid] = ["all"]
            
        await self.bot.loop.run_in_executor(None, self.save_ignored_sync, current)
        await self.bot.reload_ignored_channels()
        await ctx.send(embed=discord.Embed(description=f"🔇 Đã chặn tính năng `{feature}` tại {channel.mention}", color=C_SUCCESS))

    @commands.hybrid_command(name="unignore", description="(all, general, help, xp, media, music, game, chat, fun, ticket, task).")
    @app_commands.choices(feature=[
        app_commands.Choice(name="Tất cả (All)", value="all"),
        app_commands.Choice(name="Tổng quan (General)", value="general"),
        app_commands.Choice(name="Trợ giúp (Help)", value="help"),
        app_commands.Choice(name="Kinh nghiệm (XP)", value="xp"),
        app_commands.Choice(name="Nhúng link (Media)", value="media"),
        app_commands.Choice(name="Âm nhạc (Music)", value="music"),
        app_commands.Choice(name="Game & Kinh tế (Gacha, RPG, Boss)", value="game"),
        app_commands.Choice(name="Trò chuyện AI (Ask)", value="chat"),
        app_commands.Choice(name="Giải trí (Hug, Slap...)", value="fun"),
        app_commands.Choice(name="Hỗ trợ (Ticket)", value="ticket"),
        app_commands.Choice(name="Ghi chú (Tasks)", value="task")
    ])
    @commands.has_permissions(manage_channels=True)
    async def unignore(self, ctx: commands.Context, channel: discord.TextChannel = None, feature: str = "all"):
        channel = channel or ctx.channel
        current = await self.bot.get_ignored_channels_cached()
        cid = str(channel.id)
        
        if cid in current:
            if feature == "all" or "all" in current[cid]:
                if feature == "all":
                    current.pop(cid) 
                else:
                    # Chuyển đổi thành danh sách các tính năng CÒN BỊ CHẶN
                    features_list = ["general", "help", "xp", "media", "music", "game", "chat", "fun", "ticket", "task"]
                    if feature in features_list: features_list.remove(feature)
                    current[cid] = features_list
            elif feature in current[cid]:
                current[cid].remove(feature)
                if not current[cid]: current.pop(cid)
                    
        await self.bot.loop.run_in_executor(None, self.save_ignored_sync, current)
        await self.bot.reload_ignored_channels()
        await ctx.send(embed=discord.Embed(description=f"🔊 Đã mở lại tính năng `{feature}` tại {channel.mention}", color=C_SUCCESS))

    # ==========================================
    # 🧹 KỶ LUẬT THÀNH VIÊN (đã bọc try/except đầy đủ)
    # ==========================================
    @commands.hybrid_command(name="clear", description="Dọn dẹp tin nhắn trong kênh (1-100).")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 10):
        amount = max(1, min(amount, 100))
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            await ctx.send(embed=discord.Embed(description=f"🧹 Đã xóa **{len(deleted) - 1}** tin nhắn!", color=C_SUCCESS), delete_after=5)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="❌ Bot không có quyền `Manage Messages` tại kênh này!", color=C_ERROR))
        except discord.HTTPException as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi khi xóa tin nhắn: `{e}`", color=C_ERROR))

    @commands.hybrid_command(name="timeout", description="Cách ly một thành viên trong X phút.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int = 10, *, reason: str = "Không có"):
        if not await self.check_target(ctx, member):
            return
        try:
            await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason)
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ Bot không có đủ quyền để timeout thành viên này!", color=C_ERROR))
        except discord.HTTPException as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi hệ thống Discord: `{e}`", color=C_ERROR))

        embed = discord.Embed(title="🔇 ĐÃ CÁCH LY THÀNH VIÊN", color=C_WARN)
        embed.add_field(name="👤 Đối tượng", value=member.mention, inline=True)
        embed.add_field(name="⏱️ Thời gian", value=f"{minutes} phút", inline=True)
        embed.add_field(name="📝 Lý do", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="kick", description="Đuổi một thành viên khỏi server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Không có"):
        if not await self.check_target(ctx, member):
            return
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ Bot không có đủ quyền hạn để Kick thành viên này!", color=C_ERROR))
        except discord.HTTPException as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi hệ thống Discord: `{e}`", color=C_ERROR))

        embed = discord.Embed(title="👋 ĐÃ ĐUỔI THÀNH VIÊN", color=C_ERROR)
        embed.add_field(name="👤 Đối tượng", value=f"{member.name} (`{member.id}`)", inline=True)
        embed.add_field(name="📝 Lý do", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ban", description="Cấm vĩnh viễn thành viên khỏi server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Không có"):
        if not await self.check_target(ctx, member):
            return
        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ Bot không có đủ quyền hạn để Ban thành viên này!", color=C_ERROR))
        except discord.HTTPException as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi hệ thống Discord: `{e}`", color=C_ERROR))

        embed = discord.Embed(title="🔨 CẤM VĨNH VIỄN", color=C_ERROR)
        embed.add_field(name="👤 Đối tượng", value=f"{member.name} (`{member.id}`)", inline=True)
        embed.add_field(name="📝 Lý do", value=reason, inline=False)
        await ctx.send(embed=embed)

    # ==========================================
    # 🗑️ XÓA DỮ LIỆU (ERASE)
    # ==========================================
    async def do_erase_personal(self, user_id):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            for table in ["inventory", "char_stats", "team_setup", "gacha_state", "boss_progress", "leveling"]:
                try:
                    await db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                except Exception:
                    pass
            await db.execute("UPDATE economy SET coins = 0 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def do_erase_all(self, interaction: discord.Interaction):
        try:
            async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
                for table in ["inventory", "char_stats", "team_setup", "gacha_state", "boss_progress", "leveling", "economy"]:
                    try:
                        await db.execute(f"DELETE FROM {table}")
                    except Exception:
                        pass
                await db.commit()
            await interaction.followup.send(embed=discord.Embed(
                description="✅ Đã xóa toàn bộ dữ liệu server thành công!", color=C_SUCCESS
            ))
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                description=f"❌ Lỗi khi xóa dữ liệu: `{e}`", color=C_ERROR
            ))

    @commands.hybrid_command(name="erase", description="[ADMIN] Xóa dữ liệu game của 1 người hoặc toàn server.")
    @commands.has_permissions(administrator=True)
    async def erase(self, ctx: commands.Context, member: discord.Member = None):
        if member:
            try:
                await self.do_erase_personal(member.id)
                await ctx.send(embed=discord.Embed(
                    description=f"✅ Đã xóa toàn bộ dữ liệu game (Gacha, Boss, Level) của {member.mention}!",
                    color=C_SUCCESS
                ))
            except Exception as e:
                await ctx.send(embed=discord.Embed(description=f"❌ Lỗi khi xóa dữ liệu: `{e}`", color=C_ERROR))
        else:
            embed = discord.Embed(
                title="⚠️ CẢNH BÁO XÓA TOÀN SERVER",
                description="Hành động này sẽ **xóa vĩnh viễn** dữ liệu Gacha/Boss/Level/Kinh tế của **TẤT CẢ** thành viên!\nBạn có chắc chắn không?",
                color=C_ERROR
            )
            await ctx.send(embed=embed, view=ConfirmEraseAll(self))

    @kick.error
    @ban.error
    @timeout.error
    @clear.error
    async def mod_error_handler(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(description="❌ Bạn không có đủ quyền hạn để dùng lệnh này!", color=C_ERROR))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
