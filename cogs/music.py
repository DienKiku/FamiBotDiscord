import discord
from discord.ext import commands
import wavelink
import asyncio
import aiohttp
import re
import json
import difflib
import random

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)
C_GOLD = discord.Color.from_rgb(255, 215, 0)

# ==========================================
# GIAO DIỆN TÌM KIẾM & PHÂN TRANG (UI)
# ==========================================
class SearchSelect(discord.ui.Select):
    def __init__(self, ctx, music_cog, results):
        self.ctx = ctx
        self.music_cog = music_cog
        self.results = results
        options = []
        for i, track in enumerate(results[:25]):
            title = track.title[:90]
            duration_sec = track.length // 1000
            duration_str = music_cog.format_time(duration_sec)
            uploader = track.author[:40] if track.author else "Unknown"
            options.append(discord.SelectOption(
                label=f"{i+1}. {title}",
                description=f"⏱️ {duration_str} | 👤 {uploader}",
                value=str(i)
            ))
        super().__init__(placeholder="🎵 Chọn bài hát bạn muốn phát...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Bạn không phải là người tìm kiếm bài hát này!", ephemeral=True)
        selected_idx = int(self.values[0])
        selected_track: wavelink.Playable = self.results[selected_idx]
        await interaction.response.edit_message(content=f"⏳ Đang nạp nhạc: **{selected_track.title}**...", view=None, embed=None)
        player: wavelink.Player = getattr(self.ctx.guild, 'voice_client', None)
        if not player:
            try:
                player = await self.ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
                player.home = self.ctx.channel
                player.inactive_timeout = 300
            except Exception as e:
                return await self.ctx.send(embed=discord.Embed(description=f"❌ Lỗi kết nối Voice: {e}", color=C_ERROR))
        await player.queue.put_wait(selected_track)
        if not player.playing and not player.current:
            await player.play(player.queue.get())
        else:
            color, source_text = self.music_cog.get_platform_ui(selected_track.source, "text_search")
            embed = discord.Embed(
                title="📝 ĐÃ THÊM VÀO HÀNG ĐỢI",
                description=(f"🎵 [{selected_track.title}]({selected_track.uri})\n"
                             f"⏱️ **Thời lượng:** `{self.music_cog.format_time(selected_track.length // 1000)}`\n"
                             f"🔢 **Vị trí trong hàng đợi:** `#{len(player.queue)}`"),
                color=color
            )
            if selected_track.artwork:
                embed.set_thumbnail(url=selected_track.artwork)
            embed.set_footer(text=source_text)
            await self.ctx.send(embed=embed)

class SearchView(discord.ui.View):
    def __init__(self, ctx, music_cog, results):
        super().__init__(timeout=60)
        self.add_item(SearchSelect(ctx, music_cog, results))

class QueuePagination(discord.ui.View):
    def __init__(self, ctx, player, music_cog):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.player = player
        self.music_cog = music_cog
        self.current_page = 1
        self.all_tracks = []
        for track in player.queue:
            self.all_tracks.append({"type": "loaded", "data": track})
        if hasattr(player, 'lazy_queue') and player.lazy_queue:
            for item in player.lazy_queue:
                self.all_tracks.append({"type": "lazy", "data": item})
        self.total_pages = max(1, (len(self.all_tracks) - 1) // 10 + 1)
        self.update_buttons()

    def update_buttons(self):
        self.btn_prev.disabled = self.current_page <= 1
        self.btn_next.disabled = self.current_page >= self.total_pages

    def get_embed(self):
        embed = discord.Embed(title="📜 HÀNG ĐỢI PHÁT NHẠC", color=C_BRAND)
        q_list = ""
        total_seconds = 0
        if self.player.current:
            total_seconds += self.player.current.length // 1000
            q_list += f"**🎶 Đang phát:** [{self.player.current.title}]({self.player.current.uri})\n\n"
            if self.player.current.artwork:
                embed.set_thumbnail(url=self.player.current.artwork)
        start_idx = (self.current_page - 1) * 10
        end_idx = start_idx + 10
        page_items = self.all_tracks[start_idx:end_idx]
        for i, item in enumerate(page_items):
            idx = start_idx + i + 1
            if item["type"] == "loaded":
                track = item["data"]
                total_seconds += track.length // 1000
                q_list += f"`{idx}.` 🔴 [{track.title}]({track.uri}) • `{self.music_cog.format_time(track.length // 1000)}`\n"
            else:
                lazy_item = item["data"]
                track_name = f"{lazy_item.get('title', '')} {lazy_item.get('artist', '')}".strip() if isinstance(lazy_item, dict) else str(lazy_item)
                if len(track_name) > 55: track_name = track_name[:52] + "..."
                q_list += f"`{idx}.` 👻 {track_name} `(Chờ nạp)`\n"
        embed.description = q_list if q_list else "📭 Hàng đợi hiện tại đang trống rỗng!"
        lazy_count = len(self.player.lazy_queue) if hasattr(self.player, 'lazy_queue') else 0
        loop_map = {wavelink.QueueMode.normal: "Tắt", wavelink.QueueMode.loop: "🔂 Lặp 1 Bài", wavelink.QueueMode.loop_all: "🔁 Lặp Hàng Đợi"}
        loop_status = loop_map.get(self.player.queue.mode, "Tắt")
        autoplay_status = "Bật 🟢" if self.player.autoplay == wavelink.AutoPlayMode.enabled else "Tắt 🔴"
        embed.set_footer(text=f"Trang {self.current_page}/{self.total_pages} • 🔁 Lặp: {loop_status} • 📻 AutoPlay: {autoplay_status} • 🎵 {len(self.all_tracks)} bài")
        return embed

    @discord.ui.button(label="◀ Trước", style=discord.ButtonStyle.primary, custom_id="prev")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Bạn không phải người dùng lệnh này!", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Sau ▶", style=discord.ButtonStyle.primary, custom_id="next")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("❌ Bạn không phải người dùng lệnh này!", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ==========================================
# HỆ THỐNG ÂM NHẠC CHÍNH (WAVELINK COG)
# ==========================================
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "music" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Âm nhạc (Music)!", color=C_ERROR)
                try:
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except:
                    pass
                return False
        return True

    async def cog_load(self):
        nodes = [
            wavelink.Node(uri="https://lava-v4.millohost.my.id:443", password="https://discord.gg/mjS5J2K3ep"),
            wavelink.Node(uri="http://lavalinkv4.serenetia.com:80", password="https://seretia.link/discord"),
            wavelink.Node(uri="http://lavalink.jirayu.net:13592", password="youshallnotpass"),
            wavelink.Node(uri="https://lavalink.jirayu.net:443", password="youshallnotpass"),
            wavelink.Node(uri="https://lavalinkv4.serenetia.com:443", password="https://seretia.link/discord")
        ]
        await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)

    async def safe_voice_connect(self, channel, retries=2):
        for attempt in range(retries):
            try:
                return await channel.connect(cls=wavelink.Player, self_deaf=True, timeout=30.0)
            except asyncio.TimeoutError:
                if attempt < retries - 1:
                    await asyncio.sleep(1.5)
                    continue
                raise
            except Exception:
                if attempt < retries - 1:
                    await asyncio.sleep(1.5)
                    continue
                raise
        return None

    async def advance_queue(self, player: wavelink.Player):
        while hasattr(player, 'lazy_queue') and player.lazy_queue:
            next_item = player.lazy_queue.pop(0)
            if isinstance(next_item, dict):
                search_query = f"{next_item['title']} {next_item['artist']}"
                target_title = next_item['title']
            else:
                search_query = next_item
                target_title = next_item
            try:
                res = await self.smart_search(search_query, target_title)
                if res:
                    track = res[0] if isinstance(res, list) else res
                    await player.play(track)
                    return
            except Exception as e:
                print(f"⚠️ Bỏ qua bài hát lỗi trong Lazy Queue: {e}")
                continue

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Lavalink Node đã kết nối thành công: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player or not hasattr(player, 'home'):
            return
        track = payload.track
        # 🆕 GHI NHỚ BÀI HÁT VÀO LỊCH SỬ (không ghi bài AutoPlay recommend)
        if not track.recommended:
            if not hasattr(player, 'played_history'):
                player.played_history = []
            if not player.played_history or player.played_history[-1].identifier != track.identifier:
                player.played_history.append(track)
                if len(player.played_history) > 100:
                    player.played_history.pop(0)
        color, source_text = self.get_platform_ui(track.source, "youtube")
        if track.recommended:
            embed = discord.Embed(
                title="📻 AutoPlay • Tự động phát liên quan",
                description=(f"🎵 [{track.title}]({track.uri})\n"
                             f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                             f"⏱️ **Thời lượng:** `{self.format_time(track.length // 1000)}`"),
                color=C_GOLD
            )
        else:
            embed = discord.Embed(
                title="🎶 ĐANG PHÁT",
                description=(f"🎵 [{track.title}]({track.uri})\n"
                             f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                             f"⏱️ **Thời lượng:** `{self.format_time(track.length // 1000)}`"),
                color=color
            )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        queue_len = len(player.queue)
        lazy_count = len(player.lazy_queue) if hasattr(player, 'lazy_queue') else 0
        total_in_queue = queue_len + lazy_count
        embed.set_footer(text=f"{source_text} • 📜 Còn {total_in_queue} bài trong hàng đợi")
        await player.home.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return
        if payload.reason == "REPLACED":
            return
        if player.queue.is_empty and hasattr(player, 'lazy_queue') and player.lazy_queue:
            await self.advance_queue(player)
            return
        # 🆕 NẾU HÀNG ĐỢI RỖNG VÀ LOOP_ALL ĐANG BẬT → NẠP LẠI TỪ LỊCH SỬ
        if player.queue.is_empty and hasattr(player, 'played_history') and player.played_history:
            if player.queue.mode == wavelink.QueueMode.loop_all:
                for track in player.played_history:
                    await player.queue.put_wait(track)
                print(f"🔄 [loop_all] Đã refill {len(player.played_history)} bài từ played_history vào queue.")

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        if hasattr(player, 'home'):
            await player.home.send(embed=discord.Embed(description="💤 Đã 5 phút không có nhạc. FamiBot xin phép đi ngủ đây! 👋", color=C_GOLD))
        await player.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        player = payload.player
        if not player or not hasattr(player, 'home'):
            return
        print(f"⚠️ Lavalink Exception: {payload.exception}")
        await player.home.send(embed=discord.Embed(description="⚠️ Bài hát này bị lỗi mạng/bản quyền trên máy chủ hiện tại! Đang thử nạp bài tiếp theo...", color=C_WARN))
        try:
            await player.skip(force=True)
        except Exception as e:
            print(f"⚠️ Không thể skip bài lỗi: {e}")
            if player.queue.is_empty and hasattr(player, 'lazy_queue') and player.lazy_queue:
                await self.advance_queue(player)

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        player = payload.player
        if not player or not hasattr(player, 'home'):
            return
        print(f"⚠️ Lavalink Stuck: {payload.track.title}")
        await player.home.send(embed=discord.Embed(description="⚠️ Máy chủ nhạc đang bị kẹt cứng (Stuck)! Tự động bỏ qua...", color=C_WARN))
        try:
            await player.skip(force=True)
        except Exception as e:
            print(f"⚠️ Không thể skip bài stuck: {e}")

    async def smart_search(self, query: str, target_title: str = None, return_raw: bool = False):
        if not target_title:
            target_title = query
        if "http://" in query or "https://" in query:
            return await wavelink.Playable.search(query)

        def flatten_search(res):
            if not res:
                return []
            if isinstance(res, wavelink.Playlist):
                return list(res.tracks) if hasattr(res, 'tracks') else list(res)
            if isinstance(res, list) or hasattr(res, '__iter__'):
                return list(res)
            return [res]

        def get_best_match(results):
            if return_raw or not results:
                return results
            best_track = results[0]
            best_score = -1
            for track in results:
                score = difflib.SequenceMatcher(None, target_title.lower(), track.title.lower()).ratio()
                track_title_lower = track.title.lower()
                track_author_lower = track.author.lower() if track.author else ""
                if "audio" in track_title_lower or "official" in track_title_lower:
                    score += 0.15
                if "topic" in track_author_lower or "- topic" in track_author_lower:
                    score += 0.2
                if score > best_score:
                    best_score = score
                    best_track = track
            return [best_track]

        combined_results = []
        try:
            res_ytm = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTubeMusic)
            combined_results.extend(flatten_search(res_ytm)[:10])
        except:
            pass
        try:
            res_yt = await wavelink.Playable.search(f"{query} audio", source=wavelink.TrackSource.YouTube)
            combined_results.extend(flatten_search(res_yt)[:10])
        except:
            pass
        if combined_results:
            return combined_results if return_raw else get_best_match(combined_results)
        try:
            res_sc = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
            flat_sc = flatten_search(res_sc)
            if flat_sc:
                return flat_sc if return_raw else get_best_match(flat_sc)
        except:
            pass
        return None

    async def fetch_spotify_bypass(self, url):
        match = re.search(r'(playlist|album)/([a-zA-Z0-9]+)', url)
        if not match:
            return []
        type_str, item_id = match.group(1), match.group(2)
        embed_url = f"https://open.spotify.com/embed/{type_str}/{item_id}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        tracks = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(embed_url, headers=headers, ssl=False) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            try:
                                track_list = data['props']['pageProps']['state']['data']['entity']['trackList']
                                for item in track_list:
                                    title = item.get('title')
                                    subtitle = item.get('subtitle')
                                    if title:
                                        tracks.append({"title": title, "artist": subtitle if subtitle else ""})
                            except KeyError:
                                pass
        except Exception as e:
            print(f"Lỗi móc túi Spotify Embed: {e}")
        return tracks

    def format_time(self, seconds):
        if not seconds:
            return "00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def get_platform_ui(self, audio_source, request_source):
        ui_data = {
            "youtube": {"color": discord.Color.red(), "icon": "🔴", "name": "YouTube"},
            "soundcloud": {"color": discord.Color.orange(), "icon": "🟠", "name": "SoundCloud"},
            "spotify": {"color": discord.Color.green(), "icon": "🟢", "name": "Spotify"}
        }
        source_key = audio_source if audio_source in ui_data else "youtube"
        color = ui_data[source_key]["color"]
        source_text = f"{ui_data[source_key]['icon']} Âm thanh từ: {ui_data[source_key]['name']}"
        if request_source == "spotify":
            color = ui_data["spotify"]["color"]
            source_text += " (Bypass từ 🟢 Spotify)"
        return color, source_text

    @commands.hybrid_command(name="search", description="Tìm kiếm và chọn bài hát từ YouTube Music/Audio.")
    async def search(self, ctx: commands.Context, *, query: str):
        try:
            await ctx.defer()
        except Exception:
            pass
        if not ctx.author.voice:
            return await ctx.send(embed=discord.Embed(description="❌ Bạn phải vào một kênh Voice trước đã nhé!", color=C_ERROR), ephemeral=True)
        tracks = await self.smart_search(query, return_raw=True)
        if not tracks:
            return await ctx.send(embed=discord.Embed(description="❌ Không tìm thấy kết quả nào cho từ khóa này! (Hoặc máy chủ quá tải)", color=C_ERROR))
        results = tracks if isinstance(tracks, list) else [tracks]
        embed = discord.Embed(
            title="🔍 KẾT QUẢ TÌM KIẾM CHUẨN AUDIO",
            description=(f"🎧 Từ khóa: **{query}**\n"
                         f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                         f"Hãy chọn phiên bản bạn ưng ý nhất ở menu bên dưới! 👇"),
            color=C_BRAND
        )
        embed.set_footer(text="✨ FamiBot • Menu tự hủy sau 60 giây")
        view = SearchView(ctx, self, results)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="play", description="Phát nhạc đa nền tảng (YouTube Music chuẩn Audio, Spotify, SoundCloud)...")
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.author.voice:
            return await ctx.send(embed=discord.Embed(description="❌ Bạn phải vào một kênh Voice trước đã nhé!", color=C_ERROR), ephemeral=True)
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            try:
                player = await self.safe_voice_connect(ctx.author.voice.channel)
                player.home = ctx.channel
                player.inactive_timeout = 300
            except Exception as e:
                return await ctx.send(embed=discord.Embed(description=f"❌ Lỗi kết nối Voice: {e}", color=C_ERROR))
        elif player.channel != ctx.author.voice.channel:
            return await ctx.send(embed=discord.Embed(description=f"❌ Bot đang bận phục vụ ở phòng **{player.channel.name}** rồi!", color=C_ERROR))
        try:
            await ctx.defer()
        except Exception:
            pass
        if "spotify.com/playlist" in search or "spotify.com/album" in search:
            track_list = await self.fetch_spotify_bypass(search)
            if not track_list:
                return await ctx.send("❌ Không thể tìm được Playlist này. Có thể nó đang ở chế độ Riêng tư (Private)!")
            if not hasattr(player, 'lazy_queue'):
                player.lazy_queue = []
            embed = discord.Embed(
                title="🟢 SPOTIFY PLAYLIST (TẢI THÔNG MINH)",
                description=(f"✅ Đã trích xuất **{len(track_list)} bài hát** từ Spotify!\n"
                             f"📥 Đang nạp bài đầu tiên để phát ngay, các bài còn lại sẽ được nạp ẩn khi chuyển bài để tránh lỗi hệ thống..."),
                color=C_SUCCESS
            )
            embed.set_thumbnail(url="https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_Green.png")
            await ctx.send(embed=embed)
            if track_list:
                first_item = track_list.pop(0)
                if isinstance(first_item, dict):
                    search_query = f"{first_item['title']} {first_item['artist']}"
                    target_title = first_item['title']
                else:
                    search_query = first_item
                    target_title = first_item
                res = await self.smart_search(search_query, target_title)
                if res:
                    track = res[0] if isinstance(res, list) else res
                    await player.queue.put_wait(track)
                    if not player.playing and not player.current:
                        await player.play(player.queue.get())
            player.lazy_queue.extend(track_list)
            return
        try:
            if "spotify.com/track" in search:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://open.spotify.com/oembed?url={search}", ssl=False) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            search = f"{data.get('title', '')} {data.get('author_name', '')}"
            tracks = await self.smart_search(search)
            if not tracks:
                return await ctx.send(embed=discord.Embed(description="❌ Không tìm thấy bài hát nào (Hoặc Lavalink Public đang quá tải)!", color=C_ERROR))
            if isinstance(tracks, wavelink.Playlist):
                added = await player.queue.put_wait(tracks)
                embed = discord.Embed(
                    title="📃 YOUTUBE PLAYLIST",
                    description=f"✅ Đã thêm **{added} bài hát** từ playlist vào hàng đợi!",
                    color=C_ERROR
                )
                await ctx.send(embed=embed)
            else:
                track: wavelink.Playable = tracks[0]
                await player.queue.put_wait(track)
                if player.playing or player.current:
                    color, source_text = self.get_platform_ui(track.source, "text_search")
                    embed = discord.Embed(
                        title="📝 ĐÃ THÊM VÀO HÀNG ĐỢI",
                        description=(f"🎵 [{track.title}]({track.uri})\n"
                                     f"⏱️ **Thời lượng:** `{self.format_time(track.length // 1000)}`\n"
                                     f"🔢 **Vị trí trong hàng đợi:** `#{len(player.queue)}`"),
                        color=color
                    )
                    if track.artwork:
                        embed.set_thumbnail(url=track.artwork)
                    embed.set_footer(text=source_text)
                    await ctx.send(embed=embed)
            if not player.playing and not player.current:
                await player.play(player.queue.get())
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi truy xuất Lavalink: {e}", color=C_ERROR))

    @commands.hybrid_command(name="queue", description="Xem danh sách hàng chờ và tổng thời gian (Phân trang).")
    async def queue(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        has_lazy = hasattr(player, 'lazy_queue') and player.lazy_queue
        if not player or (not player.queue and not player.current and not has_lazy):
            return await ctx.send(embed=discord.Embed(description="📭 Hàng đợi hiện tại đang trống rỗng! Thêm nhạc bằng `f!play` nhé.", color=C_WARN))
        view = QueuePagination(ctx, player, self)
        await ctx.send(embed=view.get_embed(), view=view)

    @commands.hybrid_command(name="loop", description="Chuyển đổi chế độ lặp (Tắt -> Lặp 1 Bài -> Lặp Hàng Đợi).")
    async def loop(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            return await ctx.send(embed=discord.Embed(description="⚠️ FamiBot không ở trong Voice.", color=C_WARN))
        if player.queue.mode == wavelink.QueueMode.normal:
            player.queue.mode = wavelink.QueueMode.loop
            await ctx.send(embed=discord.Embed(description="🎛️ 🔂 Chế độ lặp: **1 BÀI HÁT**", color=C_SUCCESS))
        elif player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.loop_all
            await ctx.send(embed=discord.Embed(description="🎛️ 🔁 Chế độ lặp: **TOÀN BỘ HÀNG ĐỢI**", color=C_SUCCESS))
        else:
            player.queue.mode = wavelink.QueueMode.normal
            await ctx.send(embed=discord.Embed(description="🎛️ ➡️ Chế độ lặp: **TẮT**", color=C_ERROR))

    @commands.hybrid_command(name="shuffle", description="Xáo trộn ngẫu nhiên các bài hát trong hàng đợi (Bao gồm cả danh sách ẩn).")
    async def shuffle(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            return await ctx.send(embed=discord.Embed(description="⚠️ Bot cần ở trong phòng mới có thể xáo trộn nhạc.", color=C_WARN))
        queue_len = len(player.queue)
        lazy_len = len(player.lazy_queue) if hasattr(player, 'lazy_queue') else 0
        total_tracks = queue_len + lazy_len
        if total_tracks < 2:
            return await ctx.send(embed=discord.Embed(description="⚠️ Cần ít nhất **2 bài hát** trong hệ thống để xáo trộn!", color=C_WARN))
        if queue_len > 1:
            player.queue.shuffle()
        if lazy_len > 1:
            random.shuffle(player.lazy_queue)
        await ctx.send(embed=discord.Embed(description=f"🔀 **Đã xáo trộn tổng cộng {total_tracks} bài hát!** (Bao gồm cả danh sách tải ngầm).", color=C_SUCCESS))

    @commands.hybrid_command(name="autoplay", description="Bật/Tắt chế độ tự động phát nhạc liên quan.")
    async def autoplay(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            return await ctx.send(embed=discord.Embed(description="⚠️ Bot cần ở trong phòng mới bật được AutoPlay.", color=C_WARN))
        if player.autoplay == wavelink.AutoPlayMode.enabled:
            player.autoplay = wavelink.AutoPlayMode.disabled
            await ctx.send(embed=discord.Embed(description="📻 Chế độ AutoPlay: **TẮT 🔴**", color=C_WARN))
        else:
            player.autoplay = wavelink.AutoPlayMode.enabled
            await ctx.send(embed=discord.Embed(description="📻 Chế độ AutoPlay: **BẬT 🟢**", color=C_SUCCESS))

    @commands.hybrid_command(name="nowplaying", description="Xem thông tin bài hát đang phát hiện tại.")
    async def nowplaying(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player or not player.current:
            return await ctx.send(embed=discord.Embed(description="🔇 Hiện tại FamiBot đang không hát bài nào cả.", color=C_WARN))
        track = player.current
        color, source_text = self.get_platform_ui(track.source, "youtube")
        embed = discord.Embed(
            title="🎧 ĐANG PHÁT HIỆN TẠI",
            description=(f"🎵 [{track.title}]({track.uri})\n"
                         f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                         f"⏱️ **Thời lượng:** `{self.format_time(track.length // 1000)}`"),
            color=color
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        embed.set_footer(text=source_text)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skip", description="Bỏ qua bài hát hiện tại.")
    async def skip(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            return await ctx.send(embed=discord.Embed(description="⚠️ Hiện không có bài hát nào đang phát.", color=C_WARN))
        if player.current:
            await player.skip(force=True)
            await ctx.send(embed=discord.Embed(description="⏭️ **Đã skip!** Chuyển sang bài tiếp theo...", color=C_SUCCESS))
        elif not player.queue.is_empty:
            await player.play(player.queue.get())
            await ctx.send(embed=discord.Embed(description="⏭️ **Đang ép phát bài tiếp theo...**", color=C_SUCCESS))
        elif hasattr(player, 'lazy_queue') and player.lazy_queue:
            await self.advance_queue(player)
            await ctx.send(embed=discord.Embed(description="⏭️ **Đang nạp bài tiếp theo từ danh sách ẩn...**", color=C_SUCCESS))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ Hàng đợi trống, không có gì để skip.", color=C_WARN))

    @commands.hybrid_command(name="pause", description="Tạm dừng nhạc.")
    async def pause(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if player and player.playing and not player.paused:
            await player.pause(True)
            await ctx.send(embed=discord.Embed(description="⏸️ **Đã tạm dừng nhạc.** Gõ `/resume` để nghe tiếp nhé!", color=C_WARN))

    @commands.hybrid_command(name="resume", description="Tiếp tục phát nhạc.")
    async def resume(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if player and player.paused:
            await player.pause(False)
            await ctx.send(embed=discord.Embed(description="▶️ **Tiếp tục phát nhạc!**", color=C_SUCCESS))

    @commands.hybrid_command(name="stop", description="Dừng nhạc, xóa hàng đợi và đuổi bot.")
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if player:
            player.queue.clear()
            if hasattr(player, 'lazy_queue'):
                player.lazy_queue.clear()
            if hasattr(player, 'played_history'):
                player.played_history.clear()
            await player.disconnect()
            await ctx.send(embed=discord.Embed(description="🛑 **Đã dừng nhạc!** Đã xóa hàng đợi, tắt lặp, tắt AutoPlay và ngắt kết nối.", color=C_ERROR))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ FamiBot không ở trong kênh Voice nào cả.", color=C_WARN))

    @commands.hybrid_command(name="remove", description="Xóa một bài hát tại vị trí cụ thể trong hàng đợi.")
    async def remove(self, ctx: commands.Context, position: int):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player or player.queue.is_empty:
            return await ctx.send(embed=discord.Embed(description="📭 Hàng đợi hiện đang trống!", color=C_WARN))
        if position < 1 or position > len(player.queue):
            return await ctx.send(embed=discord.Embed(description=f"⚠️ Vị trí không hợp lệ! Vui lòng chọn từ 1 đến {len(player.queue)}.", color=C_ERROR))
        track = player.queue[position - 1]
        del player.queue[position - 1]
        await ctx.send(embed=discord.Embed(description=f"🗑️ Đã xóa bài hát **{track.title}** khỏi hàng đợi.", color=C_SUCCESS))

    @commands.hybrid_command(name="clearqueue", aliases=["cq", "clearq"], description="Xóa sạch toàn bộ hàng đợi nhưng bot không rời phòng.")
    async def clearqueue(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            return await ctx.send(embed=discord.Embed(description="⚠️ FamiBot không ở trong kênh Voice nào cả.", color=C_WARN))
        player.queue.clear()
        if hasattr(player, 'lazy_queue'):
            player.lazy_queue.clear()
        await ctx.send(embed=discord.Embed(description="🧹 **Đã dọn sạch hàng đợi!** Bot vẫn ở đây chờ lệnh tiếp theo.", color=C_SUCCESS))

    @commands.hybrid_command(name="fixlag", description="Đổi máy chủ phát nhạc khác nếu bạn nghe thấy tiếng bị giật/lag/xước.")
    async def fixlag(self, ctx: commands.Context):
        if not ctx.author.voice:
            return await ctx.send(embed=discord.Embed(description="❌ Bạn phải ở trong kênh Voice mới dùng được lệnh này!", color=C_ERROR))
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player:
            return await ctx.send(embed=discord.Embed(description="⚠️ Bot đang không phát nhạc, không có gì để fix!", color=C_WARN))
        if player.channel != ctx.author.voice.channel:
            return await ctx.send(embed=discord.Embed(description="❌ Bạn phải ở cùng phòng Voice với bot!", color=C_ERROR))
        await ctx.send(embed=discord.Embed(description=(f"🔄 **Đang xử lý lag...**\n"
                                                        f"FamiBot đang dọn dẹp luồng âm thanh và tìm máy chủ mới mượt hơn. Xin chờ vài giây!"), color=C_BRAND))
        current_track = player.current
        queue_tracks = list(player.queue)
        lazy_tracks = list(player.lazy_queue) if hasattr(player, 'lazy_queue') else []
        old_loop_mode = player.queue.mode
        old_autoplay = player.autoplay
        played_history = list(player.played_history) if hasattr(player, 'played_history') else []
        player.queue.clear()
        if hasattr(player, 'lazy_queue'):
            player.lazy_queue.clear()
        if player.playing:
            try:
                await player.stop(force=True)
            except Exception as e:
                print(f"⚠️ [fixlag] player.stop() thất bại: {e}")
            await asyncio.sleep(0.5)
        try:
            await player.disconnect()
        except Exception as e:
            print(f"⚠️ [fixlag] player.disconnect() thất bại: {e}")
        await asyncio.sleep(2)
        try:
            new_player = await self.safe_voice_connect(ctx.author.voice.channel)
            new_player.home = ctx.channel
            new_player.inactive_timeout = 300
            new_player.lazy_queue = lazy_tracks
            for t in queue_tracks:
                await new_player.queue.put_wait(t)
            new_player.queue.mode = old_loop_mode
            new_player.autoplay = old_autoplay
            new_player.played_history = played_history
            if current_track:
                await new_player.play(current_track)
            elif not new_player.queue.is_empty:
                await self.advance_queue(new_player)
            await ctx.send(embed=discord.Embed(description="✅ **Đã chuyển đổi máy chủ thành công!** Nhạc sẽ tiếp tục phát mượt mà ngay bây giờ.", color=C_SUCCESS))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi khi cố gắng kết nối lại máy chủ nhạc: {e}", color=C_ERROR))

    @commands.hybrid_command(name="history", aliases=["played", "recent"], description="Xem danh sách các bài hát đã phát gần đây (tối đa 100 bài).")
    async def history(self, ctx: commands.Context):
        player: wavelink.Player = getattr(ctx.guild, 'voice_client', None)
        if not player or not hasattr(player, 'played_history') or not player.played_history:
            return await ctx.send(embed=discord.Embed(description="📭 Chưa có bài hát nào được ghi nhận trong phiên này!", color=C_WARN))
        history_list = player.played_history
        total = len(history_list)
        embed = discord.Embed(title=f"🕐 LỊCH SỬ ĐÃ PHÁT ({total} bài)", color=C_BRAND)
        desc = ""
        for i, track in enumerate(history_list[-15:]):
            idx = len(history_list) - 15 + i + 1 if total > 15 else i + 1
            desc += f"`{idx}.` [{track.title}]({track.uri}) • `{self.format_time(track.length // 1000)}`\n"
        if total > 15:
            desc += f"\n*...và {total - 15} bài khác (tối đa hiển thị 15 bài gần nhất)*"
        embed.description = desc
        embed.set_footer(text="💡 Dùng f!loop 2 lần để bật loop_all - bot sẽ tự động phát lại toàn bộ lịch sử khi hết queue!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))