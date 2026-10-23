# =========================================================
# FamiBot - media_embed.py | v4 "Resilient Edition"
# Vá: URL bị cắt query, icon_url malformed, yt-dlp 404,
#     fallback domain chết, tzinfo sai cú pháp.
# =========================================================
import asyncio
import datetime
import html as html_lib
import json
import os
import re
import uuid
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import aiohttp
import discord
from discord.ext import commands
import yt_dlp

MAX_SIZE_BYTES = int(23.5 * 1024 * 1024)
FB_COOKIE_FILE = "facebook_cookies.txt"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")
UA_BOT = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"

PLATFORM_STYLE = {
    "TikTok":    ("🎵", discord.Color.from_rgb(254, 44, 85)),
    "X":         ("🐦", discord.Color.from_rgb(29, 155, 240)),
    "Facebook":  ("📘", discord.Color.from_rgb(24, 119, 242)),
    "Instagram": ("📸", discord.Color.from_rgb(225, 48, 108)),
}

# Tham số rác cần loại. TUYỆT ĐỐI không đụng vào: id, story_fbid, v, fbid, set...
JUNK_PARAMS = {
    "fbclid", "mibextid", "rdid", "share_url", "_rdr", "refsrc", "extid",
    "paipv", "eav", "checkpoint_src", "notif_t", "notif_id", "ref", "sfnsn",
    "idorvanity", "wtsid", "hr", "is_from_rle", "igsh", "igshid", "img_index",
    "_nc_cat", "is_copy_url", "is_from_webapp", "sender_device", "web_id",
    "s", "locale", "q" # <-- THÊM 3 TỪ KHÓA NÀY VÀO ĐÂY ĐỂ DIỆT LAG
}

SAFE_URL_RE = re.compile(r'^https?://[^\s<>"\\]+$')


# ================= TIỆN ÍCH =================
def safe_url(raw, limit=1024):
    """Chuẩn hoá + kiểm tra URL. Trả None nếu Discord sẽ từ chối.
    ĐÂY LÀ HÀM CHẶN LỖI 50035 'Not a well formed URL'."""
    if not raw:
        return None
    u = str(raw).strip()
    u = u.replace("\\/", "/").replace("\\u0025", "%")
    u = html_lib.unescape(u)
    if u.startswith("//"):
        u = "https:" + u
    if not SAFE_URL_RE.match(u) or len(u) > limit:
        return None
    try:
        p = urlparse(u)
        if not p.netloc or "." not in p.netloc:
            return None
    except Exception:
        return None
    return u


def clean_url(u):
    """Lọc tham số tracking NHƯNG GIỮ tham số định danh (id, story_fbid, v...)."""
    try:
        p = urlparse(u)
        kept = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                if k.lower() not in JUNK_PARAMS
                and not k.lower().startswith(("utm_", "__cft", "__tn", "_nc"))]
        return urlunparse(p._replace(query=urlencode(kept), fragment=""))
    except Exception:
        return u


def parse_count(raw):
    """'1.2K' / '3,4 N' / '15.234' / 15234 -> int. None nếu không đọc được."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).strip().lower().replace("\xa0", " ")
    s = re.sub(r'[^\d.,kmnbt ]', '', s).strip()
    if not s:
        return None
    mult = 1
    for suf, m in (("tr", 1_000_000), ("k", 1_000), ("n", 1_000),
                   ("m", 1_000_000), ("b", 1_000_000_000), ("t", 1_000)):
        if s.endswith(suf):
            mult, s = m, s[: -len(suf)].strip()
            break
    s = s.replace(" ", "")
    if mult == 1:                       # '15.234' / '15,234' là dấu phân nhóm
        s = s.replace(".", "").replace(",", "")
    else:                               # '1.2k' -> phần thập phân
        s = s.replace(",", ".")
    try:
        return int(float(s) * mult)
    except (ValueError, TypeError):
        return None


def fmt_num(n):
    n = parse_count(n)
    return f"{n:,}".replace(",", ".") if n is not None else None


def to_dt(ts):
    try:
        v = int(ts)
    except (TypeError, ValueError):
        return None
    if v > 10_000_000_000:              # mili giây
        v //= 1000
    if v < 946_684_800 or v > 4_102_444_800:   # ngoài 2000-2100 => rác
        return None
    return datetime.datetime.fromtimestamp(v, tz=datetime.timezone.utc)


def unescape_json_str(s):
    if not s:
        return ""
    try:
        return json.loads(f'"{s}"')
    except Exception:
        return s.replace("\\/", "/").replace('\\"', '"').replace("\\n", "\n")


def strip_tags(h):
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
    h = re.sub(r'<[^>]+>', ' ', h)
    return html_lib.unescape(re.sub(r'\s+', ' ', h))


def clip(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def new_post(platform):
    return {
        "platform": platform, "author": None, "author_url": None, "avatar": None,
        "created_at": None, "text": "", "media": [], "source_url": None,
        "stats": {"views": None, "likes": None, "comments": None,
                  "shares": None, "bookmarks": None},
    }


def load_cookie_header(path=FB_COOKIE_FILE):
    if not os.path.exists(path):
        return None
    jar = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7 and parts[5]:
                jar.append(f"{parts[5]}={parts[6]}")
    return "; ".join(jar) if jar else None


class MediaEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url_pattern = re.compile(
            r'(https?://[a-zA-Z0-9.\-]*'
            r'(?:tiktok\.com|twitter\.com|x\.com|facebook\.com|fb\.watch|fb\.com'
            r'|instagram\.com|ig\.me)[^\s<>]+)'
        )
        self.fb_cookie = load_cookie_header()
        if not self.fb_cookie:
            print("[MediaEmbed] ⚠️ Thiếu facebook_cookies.txt -> FB chỉ lấy được OpenGraph.")

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "media" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Nhúng (Embedded)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================  

    # ============ RESOLVE LINK RÚT GỌN / SHARE ============
    async def resolve_url(self, session, url):
        if not re.search(r'(vt|vm)\.tiktok\.com|fb\.watch|/share/|ig\.me|/t/|l\.facebook', url):
            return url
        headers = {"User-Agent": UA, "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"}
        if "facebook" in url and self.fb_cookie: headers["Cookie"] = self.fb_cookie
        try:
            async with session.get(url, headers=headers, allow_redirects=True, ssl=False, timeout=10) as r:
                final = str(r.url)
                body = await r.text() if ("facebook" in final and r.status == 200) else ""
                if body:
                    m = (re.search(r'<link rel="canonical" href="([^"]+)"', body)
                         or re.search(r'location\.replace\("([^"]+)"', body)
                         or re.search(r'window\.location\.href\s*=\s*"([^"]+)"', body))
                    if m:
                        cand = unescape_json_str(html_lib.unescape(m.group(1).replace("\\/", "/")))
                        if "login" not in cand and safe_url(cand): final = cand
                
                # CHỐT HẠ: MÓC LINK GỐC TỪ TRANG LOGIN
                if re.search(r'/login|/checkpoint', final):
                    from urllib.parse import urlparse, parse_qsl
                    qs = dict(parse_qsl(urlparse(final).query))
                    if 'next' in qs: return clean_url(qs['next'])
                    return url
                return clean_url(final)
        except Exception: return url

    # ============ 1. TIKTOK ============
    async def fetch_tiktok(self, session, url):
        try:
            async with session.post("https://www.tikwm.com/api/",
                                    data={"url": url, "hd": 1},
                                    headers={"User-Agent": UA}, ssl=False,
                                    timeout=aiohttp.ClientTimeout(total=20)) as resp:
                data = await resp.json(content_type=None)
        except Exception as e:
            print(f"[TikTok] {e}")
            return None
        if not data or data.get("code") != 0:
            return None
        d = data.get("data") or {}
        a = d.get("author") or {}
        post = new_post("TikTok")
        post["author"] = a.get("nickname") or a.get("unique_id") or "Unknown"
        post["author_url"] = f"https://www.tiktok.com/@{a['unique_id']}" if a.get("unique_id") else None
        post["avatar"] = a.get("avatar")
        post["created_at"] = to_dt(d.get("create_time"))
        post["text"] = d.get("title") or ""
        post["stats"] = {"views": d.get("play_count"), "likes": d.get("digg_count"),
                         "comments": d.get("comment_count"), "shares": d.get("share_count"),
                         "bookmarks": d.get("collect_count")}
        if d.get("play"):
            post["media"].append({"type": "video", "url": d["play"], "thumb": d.get("cover")})
        elif d.get("images"):
            for img in d["images"][:10]:
                post["media"].append({"type": "image", "url": img})
        return post

    # ============ 2. X / TWITTER ============
    async def fetch_x(self, session, url):
        m = re.search(r'status/(\d+)', url)
        if not m:
            return None
        tid = m.group(1)
        try:
            async with session.get(f"https://api.fxtwitter.com/status/{tid}",
                                   headers={"User-Agent": UA}, ssl=False,
                                   timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    j = await r.json(content_type=None)
                    if j.get("tweet"):
                        return self._map_fx(j["tweet"], url)
        except Exception as e:
            print(f"[X] FxTwitter lỗi: {e}")
        try:
            async with session.get(f"https://api.vxtwitter.com/i/status/{tid}",
                                   headers={"User-Agent": UA}, ssl=False,
                                   timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    return self._map_vx(await r.json(content_type=None), url)
        except Exception as e:
            print(f"[X] vxTwitter lỗi: {e}")
        return None

    def _map_fx(self, t, url):
        post = new_post("X")
        a = t.get("author") or {}
        post["author"] = f"{a.get('name', 'Unknown')} (@{a.get('screen_name', '?')})"
        post["author_url"] = a.get("url")
        post["avatar"] = a.get("avatar_url")
        post["created_at"] = to_dt(t.get("created_timestamp"))
        post["text"] = t.get("text") or ""
        post["stats"] = {"views": t.get("views"), "likes": t.get("likes"),
                         "comments": t.get("replies"), "shares": t.get("retweets"),
                         "bookmarks": t.get("bookmarks")}
        media = t.get("media") or {}
        for v in (media.get("videos") or []):
            post["media"].append({"type": "gif" if v.get("type") == "gif" else "video",
                                  "url": v.get("url"), "thumb": v.get("thumbnail_url")})
        for p in (media.get("photos") or []):
            post["media"].append({"type": "image", "url": p.get("url")})
        post["source_url"] = url
        return post

    def _map_vx(self, d, url):
        post = new_post("X")
        post["author"] = f"{d.get('user_name', 'Unknown')} (@{d.get('user_screen_name', '?')})"
        post["author_url"] = f"https://x.com/{d.get('user_screen_name')}" if d.get("user_screen_name") else None
        post["avatar"] = d.get("user_profile_image_url")
        post["created_at"] = to_dt(d.get("date_epoch"))
        post["text"] = d.get("text") or ""
        post["stats"] = {"views": None, "likes": d.get("likes"),
                         "comments": d.get("replies"), "shares": d.get("retweets"),
                         "bookmarks": None}
        for mm in (d.get("media_extended") or []):
            typ = mm.get("type")
            post["media"].append({
                "type": "image" if typ == "image" else ("gif" if typ == "gif" else "video"),
                "url": mm.get("url"), "thumb": mm.get("thumbnail_url")})
        post["source_url"] = url
        return post

    # ============ 3. FACEBOOK / INSTAGRAM ============
    async def fetch_facebook_embed(self, session, url):
        """Bí thuật: Dùng cổng Video Plugin của Facebook (Sạch bóng Captcha, Không cần Cookie)"""
        import urllib.parse
        embed_url = f"https://www.facebook.com/plugins/video.php?href={urllib.parse.quote(url)}&show_text=false"
        try:
            async with session.get(embed_url, headers={"User-Agent": UA}, ssl=False, timeout=5) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    for p in [r'"hd_src":"([^"]+)"', r'"sd_src":"([^"]+)"', r'"video_url":"([^"]+)"']:
                        m = re.search(p, html)
                        if m: return safe_url(html_lib.unescape(unescape_json_str(m.group(1)).replace("\\/", "/")))
        except Exception: pass
        return None

    async def fetch_meta(self, session, url):
        platform = "Instagram" if ("instagram" in url or "ig.me" in url) else "Facebook"
        post = await asyncio.get_running_loop().run_in_executor(None, self._ytdlp_extract, url, platform)
        
        scraped = await self.scrape_meta_html(session, url, platform)
        post = self.merge_post(post, scraped)

        has_video = post and post.get("media") and any(m.get("type") in ("video", "gif") for m in post["media"])
        if not has_video and platform == "Facebook":
            plugin_vid = await self.fetch_facebook_embed(session, url)
            if plugin_vid:
                if post is None: post = new_post(platform)
                post["media"].insert(0, {"type": "video", "url": plugin_vid})

        if post is None or (not post["text"] and not post["media"]):
            post = self.merge_post(post, await self.fetch_og(session, url, platform))
        return post

    @staticmethod
    def merge_post(base, extra):
        """Trộn 2 nguồn: ưu tiên giá trị nào có thật."""
        if base is None:
            return extra
        if extra is None:
            return base
        for k, v in extra["stats"].items():
            if base["stats"].get(k) is None and v is not None:
                base["stats"][k] = v
        for k in ("author", "author_url", "avatar", "created_at"):
            if not base.get(k) and extra.get(k):
                base[k] = extra[k]
        if extra["text"] and len(extra["text"]) > len(base["text"]):
            base["text"] = extra["text"]
        if not base["media"] and extra["media"]:
            base["media"] = extra["media"]
        return base

    def _ytdlp_extract(self, url, platform):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "ignoreerrors": True,
            "extractor_retries": 0,
            "socket_timeout": 7,
            "http_headers": {"User-Agent": UA},
            # Ép yt-dlp tìm luồng mp4 tốt nhất dưới ngưỡng dung lượng Discord
            "format": "best[ext=mp4][filesize<23M]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        }
        if os.path.exists(FB_COOKIE_FILE):
            opts["cookiefile"] = FB_COOKIE_FILE
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"[{platform}] yt-dlp bỏ qua: {str(e)[:120]}")
            return None
            
        if not info:
            return None
        if info.get("_type") == "playlist" and info.get("entries"):
            entries = [e for e in info["entries"] if e]
            if not entries:
                return None
            info = entries[0]

        post = new_post(platform)
        post["author"] = (info.get("uploader") or info.get("channel")
                          or info.get("creator") or None)
        post["author_url"] = info.get("uploader_url") or info.get("channel_url")
        post["created_at"] = to_dt(info.get("timestamp"))
        if not post["created_at"] and info.get("upload_date"):
            try:
                post["created_at"] = datetime.datetime.strptime(
                    info["upload_date"], "%Y%m%d"
                ).replace(tzinfo=datetime.timezone.utc)
            except Exception:
                pass
        post["text"] = info.get("description") or info.get("title") or ""
        post["stats"] = {
            "views": info.get("view_count"),
            "likes": info.get("like_count"),
            "comments": info.get("comment_count"),
            "shares": info.get("repost_count"),
            "bookmarks": None
        }
        
        # Lấy link video trực tiếp
        best_vid_url = self._pick_format(info) or info.get("url")
        if best_vid_url:
            post["media"].append({"type": "video", "url": best_vid_url, "thumb": info.get("thumbnail")})
        elif info.get("thumbnail"):
            post["media"].append({"type": "image", "url": info["thumbnail"]})
            
        return post

    @staticmethod
    def _pick_format(info):
        fmts = [f for f in (info.get("formats") or [])
                if f.get("url") and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")]
        if not fmts:
            return info.get("url")
        under = [f for f in fmts
                 if (f.get("filesize") or f.get("filesize_approx") or 0) < MAX_SIZE_BYTES]
        pool = under or fmts
        pool.sort(key=lambda f: (f.get("height") or 0), reverse=bool(under))
        return pool[0].get("url")

    async def _get_html(self, session, url, ua, cookie=True):
        headers = {"User-Agent": ua, "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"}
        if cookie and self.fb_cookie and "facebook" in url:
            headers["Cookie"] = self.fb_cookie
        try:
            async with session.get(url, headers=headers, ssl=False,
                                   timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    return None
                return await r.text()
        except Exception as e:
            print(f"[HTML] {url[:60]} -> {e}")
            return None

    async def scrape_meta_html(self, session, url, platform):
        """Thử lần lượt: bản desktop (cookie) -> bản mbasic (nhẹ, dễ parse)."""
        candidates = [(url, UA)]
        if platform == "Facebook":
            candidates.append((re.sub(r'://(www\.|m\.|web\.)?facebook\.com',
                                      '://mbasic.facebook.com', url), UA_MOBILE))
        for cand, ua in candidates:
            raw = await self._get_html(session, cand, ua)
            if not raw or "login" in (raw[:2000].lower()) and "reaction" not in raw:
                continue
            post = self._parse_meta_html(raw, platform)
            if post:
                return post
        return None

    def _parse_meta_html(self, raw, platform):
        def grab(patterns, src=raw):
            for p in patterns:
                m = re.search(p, src)
                if m:
                    return m.group(1)
            return None

        post = new_post(platform)
        post["stats"]["likes"] = parse_count(grab([
            r'"reaction_count":\{"count":(\d+)',
            r'"i18n_reaction_count":"([^"]+)"',
            r'"top_reactions":\{[^}]*"count":(\d+)',
            r'"likers":\{"count":(\d+)',
            r'"edge_liked_by":\{"count":(\d+)',
            r'"edge_media_preview_like":\{"count":(\d+)']))
        post["stats"]["comments"] = parse_count(grab([
            r'"comment_rendering_instance":\{"comments":\{"total_count":(\d+)',
            r'"comment_count":\{"total_count":(\d+)',
            r'"i18n_comment_count":"([^"]+)"',
            r'"comments":\{"total_count":(\d+)',
            r'"edge_media_to_(?:parent_)?comment":\{"count":(\d+)']))
        post["stats"]["shares"] = parse_count(grab([
            r'"share_count":\{"count":(\d+)',
            r'"reshare_count":(\d+)',
            r'"i18n_share_count":"([^"]+)"']))
        post["stats"]["views"] = parse_count(grab([
            r'"video_view_count":(\d+)', r'"play_count":(\d+)',
            r'"feedback_video_view_count":(\d+)',
            r'"video_play_count":(\d+)']))
        post["created_at"] = to_dt(grab([
            r'"creation_time":(\d{10})', r'"publish_time":(\d{10})',
            r'"created_time":(\d{10})', r'data-utime="(\d{10})"',
            r'"taken_at_timestamp":(\d{10})']))
        post["author"] = unescape_json_str(grab([
            r'"owning_profile":\{"__typename":"[^"]+","id":"\d+","name":"([^"]+)"',
            r'"actors":\[\{"__typename":"[^"]+","name":"([^"]+)"',
            r'"owner":\{"__typename":"[^"]+","id":"\d+","name":"([^"]+)"',
            r'"page_name":"([^"]+)"', r'"username":"([^"]+)"'])) or None
        post["avatar"] = safe_url(unescape_json_str(grab([
            r'"profile_picture":\{"uri":"([^"]+)"',
            r'"profile_pic_url[^"]*":"([^"]+)"'])))
        post["author_url"] = safe_url(unescape_json_str(grab([
            r'"profile_url":"([^"]+)"'])))
        post["text"] = html_lib.unescape(unescape_json_str(grab([
            r'"message":\{[^}]*?"text":"([^"]{5,}?)"',
            r'"post_text":"([^"]{5,}?)"',
            r'"edit_history":[^}]*?"text":"([^"]{5,}?)"',
            r'<meta property="og:description" content="([^"]+)"'])) or "")

        # Bản mbasic: số liệu nằm ở dạng chữ "12 lượt thích", "3 bình luận"
        if all(v is None for v in post["stats"].values()):
            plain = strip_tags(raw)[:20000]
            post["stats"]["likes"] = parse_count(grab(
                [r'([\d.,]+(?:\s?[KMN])?)\s*(?:lượt thích|người khác|likes?|reactions?)'], plain))
            post["stats"]["comments"] = parse_count(grab(
                [r'([\d.,]+(?:\s?[KMN])?)\s*(?:bình luận|comments?)'], plain))
            post["stats"]["shares"] = parse_count(grab(
                [r'([\d.,]+(?:\s?[KMN])?)\s*(?:lượt chia sẻ|chia sẻ|shares?)'], plain))

        # Giải mã link MP4 ẩn sâu trong HTML
        vid_candidates = [
            r'"browser_native_hd_url":"([^"]+)"',
            r'"browser_native_sd_url":"([^"]+)"',
            r'"playable_url_quality_hd":"([^"]+)"',
            r'"playable_url":"([^"]+)"',
            r'<a href="/video/redirect/\?src=([^"&]+)' # Bắt link video từ mbasic
        ]
        direct_vid = grab(vid_candidates)
        if direct_vid:
            from urllib.parse import unquote
            direct_vid = html_lib.unescape(unescape_json_str(direct_vid))
            # Nếu link bị mã hóa dạng %3A%2F%2F (https://), giải mã nó ra!
            if "%3A%2F%2F" in direct_vid or "%3a%2f%2f" in direct_vid.lower():
                direct_vid = unquote(direct_vid)
            direct_vid = safe_url(direct_vid)
            if direct_vid:
                post["media"].insert(0, {"type": "video", "url": direct_vid})

        imgs, seen = [], set()
        for m in re.finditer(
                r'"(?:full_image|photo_image|image|display_url|src)":?\s*\{?"?(?:uri":")?'
                r'(https:[^"]+?\.(?:jpg|png|webp)[^"]*)"', raw):
            u = safe_url(unescape_json_str(m.group(1)))
            if u and u not in seen:
                seen.add(u)
                imgs.append({"type": "image", "url": u})
            if len(imgs) >= 4:
                break
        if not imgs:
            og = safe_url(grab([r'<meta property="og:image" content="([^"]+)"']))
            if og:
                imgs.append({"type": "image", "url": og})
        post["media"] = imgs

        has_any = (any(v is not None for v in post["stats"].values())
                   or post["text"] or imgs or post["author"])
        return post if has_any else None

    async def fetch_og(self, session, url, platform):
        """Phao cứu sinh: đóng giả crawler của Facebook để lấy thẻ og:*"""
        raw = await self._get_html(session, url, UA_BOT, cookie=False)
        if not raw:
            raw = await self._get_html(session, url, UA_BOT, cookie=True)
        if not raw:
            return None

        def og(name):
            m = re.search(rf'<meta[^>]+(?:property|name)="{name}"[^>]+content="([^"]*)"', raw)
            if not m:
                m = re.search(rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{name}"', raw)
            return html_lib.unescape(m.group(1)) if m else None

        title, desc = og("og:title"), og("og:description")
        if not title and not desc:
            return None
        post = new_post(platform)
        post["author"] = (title or "").split(" | ")[0].strip() or None
        post["text"] = desc or title or ""
        img = safe_url(og("og:image"))
        if img:
            post["media"].append({"type": "image", "url": img})
        vid = safe_url(og("og:video:url") or og("og:video:secure_url"))
        if vid:
            post["media"].insert(0, {"type": "video", "url": vid, "thumb": img})
        return post

    # ============ TẢI FILE ============
    async def download_media(self, session, url, suffix=".mp4"):
        url = safe_url(url)
        if not url:
            return None
        fname = f"temp_{uuid.uuid4().hex[:8]}{suffix}"
        size = 0
        try:
            async with session.get(url, ssl=False, headers={"User-Agent": UA},
                                   timeout=aiohttp.ClientTimeout(total=180)) as resp:
                if resp.status != 200:
                    return None
                cl = resp.headers.get("Content-Length")
                if cl and int(cl) > MAX_SIZE_BYTES:
                    return "TOO_LARGE"
                with open(fname, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 512):
                        size += len(chunk)
                        if size > MAX_SIZE_BYTES:
                            break
                        f.write(chunk)
            if size > MAX_SIZE_BYTES:
                os.remove(fname)
                return "TOO_LARGE"
            return fname
        except Exception as e:
            print(f"[Download] {e}")
            if os.path.exists(fname):
                os.remove(fname)
            return None

    # ============ RENDER (mọi URL đều đi qua safe_url) ============
    def build_embeds(self, post, sharer, url, note=None):
        icon, color = PLATFORM_STYLE.get(post["platform"], ("🌐", discord.Color.blurple()))
        page_url = safe_url(url)
        main = discord.Embed(color=color)
        if page_url:
            main.url = page_url

        body = clip(post.get("text"), 3800)
        if note:
            body = f"{body}\n\n{note}".strip()
        if body:
            main.description = body

        author_name = clip(post.get("author") or "Không rõ người đăng", 240)
        
        # XỬ LÝ AN TOÀN TUYỆT ĐỐI: Lọc URL hợp lệ, không dùng MISSING
        author_url = safe_url(post.get("author_url")) or page_url
        avatar_url = safe_url(post.get("avatar"))

        if avatar_url and author_url:
            main.set_author(name=f"{icon} {author_name}", url=author_url, icon_url=avatar_url)
        elif author_url:
            main.set_author(name=f"{icon} {author_name}", url=author_url)
        elif avatar_url:
            main.set_author(name=f"{icon} {author_name}", icon_url=avatar_url)
        else:
            main.set_author(name=f"{icon} {author_name}")

        s = post["stats"]
        rows = [("👁️ Lượt xem", s.get("views")), ("❤️ Lượt thích", s.get("likes")),
                ("💬 Bình luận", s.get("comments")), ("🔁 Chia sẻ", s.get("shares")),
                ("🔖 Đã lưu", s.get("bookmarks"))]
        shown = 0
        for label, val in rows:
            v = fmt_num(val)
            if v is not None:
                main.add_field(name=label, value=f"**{v}**", inline=True)
                shown += 1
        if shown == 0:
            main.add_field(name="📊 Thông số",
                           value="*Bài đăng ẩn tương tác hoặc nền tảng không công bố*",
                           inline=False)

        if post.get("created_at"):
            main.timestamp = post["created_at"]
            main.set_footer(text=f"{post['platform']} • Chia sẻ bởi {sharer}")
        else:
            main.set_footer(text=f"{post['platform']} • Chia sẻ bởi {sharer} • Không rõ ngày đăng")

        images = [safe_url(m.get("url")) for m in post["media"] if m.get("type") == "image"]
        images = [i for i in images if i]
        embeds = [main]
        if images:
            main.set_image(url=images[0])
            for extra in images[1:4]:
                e = discord.Embed(color=color)
                if page_url:
                    e.url = page_url
                e.set_image(url=extra)
                embeds.append(e)
        return embeds

    @staticmethod
    def build_view(url, media_url=None):
        view = discord.ui.View()
        u = safe_url(url)
        if u:
            view.add_item(discord.ui.Button(label="Xem bài gốc", url=u, emoji="🔗"))
        m = safe_url(media_url)
        if m and m != u:
            view.add_item(discord.ui.Button(label="Mở media", url=m, emoji="🎬"))
        return view if view.children else None

    # ============ LUỒNG CHÍNH ============
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(message.channel.id)
            if cid in ignored:
                # Ngừng hoạt động nếu kênh bị chặn "all" hoặc "media"
                if "all" in ignored[cid] or "media" in ignored[cid]:
                    return

        match = self.url_pattern.search(message.content)
        if not match:
            return

        url = clean_url(match.group(1).rstrip('.,;)]}"\''))

        # =========================================================
        # 1. BỘ LỌC CHẶN LINK RÁC GÂY LAG (Link Feed Facebook)
        # =========================================================
        parsed_url = urlparse(url)
        if "facebook.com" in parsed_url.netloc:
            path = parsed_url.path.strip("/")
            if path in ["reel", "watch", "shorts", ""] and "v=" not in parsed_url.query:
                try: await message.delete()
                except: pass
                return await message.channel.send(
                    f"⚠️ **{message.author.display_name} ơi, link bị sai rồi!**\n"
                    f"Bạn đang copy đường link của *cả trang lướt Video (Feed)* chứ không phải link của một video cụ thể.\n\n"
                    f"💡 **Cách sửa:** Hãy bấm vào nút **Chia sẻ (Share)** trên video đó ➡️ Chọn **Sao chép liên kết (Copy Link)** rồi gửi lại vào đây nhé!"
                )

        # =========================================================
        # 2. XỬ LÝ SIÊU TỐC CHO FACEBOOK, TIKTOK, X (KHÔNG CHỜ ĐỢI)
        # =========================================================
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                
                # Lột vỏ link rút gọn (VD: /share/ -> /reel/)
                resolved_url = await self.resolve_url(session, url)
                
                # Gọi hàm tạo Proxy (Facebed cho Facebook, Fixupx cho X, Tnktok cho TikTok)
                fallback_url = self.get_fallback_url(resolved_url)
                
                if fallback_url:
                    try: await message.delete()
                    except: pass
                    # Ném thẳng link Facebed ra để Discord tự nạp khung Video mượt mà
                    await message.channel.send(f"📤 **{message.author.display_name}** đã chia sẻ:\n{fallback_url}")
                    return

        except Exception as e:
            print(f"[FastProxy Error]: {e}")

        # =========================================================
        # 3. PHÁO CỨU SINH CUỐI CÙNG (Dành cho bài viết ảnh / không có proxy)
        # =========================================================
        status = await message.channel.send("⏳ **FamiBot** đang trích xuất dữ liệu bài đăng...")
        file_path = None

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                post = await self.fetch_meta(session, url)

                if not post:
                    raise RuntimeError("Không lấy được dữ liệu bài đăng.")
                post["source_url"] = url

                embeds = self.build_embeds(post, message.author.display_name, url)
                view = self.build_view(url)

                sent = await message.channel.send(embeds=embeds, view=view)
                if sent:
                    try: await message.delete()
                    except Exception: pass
                await status.delete()

        except Exception as e:
            print(f"[MediaEmbed Fallback] {type(e).__name__}: {e}")
            await status.edit(content=f"❌ Không trích xuất được bài đăng này. Link gốc:\n{url}")

    # ============ TẠO PROXY CHUẨN XÁC ============
    def get_fallback_url(self, url):
        # 1. GIỮ NGUYÊN TIKTOK VÀ X NHƯ CŨ
        if "twitter.com" in url or "x.com" in url:
            return re.sub(r'https?://[a-z0-9.\-]*(twitter|x)\.com', 'https://fixupx.com', url)
        if "tiktok.com" in url:
            return re.sub(r'https?://[a-z0-9.\-]*tiktok\.com', 'https://tnktok.com', url)
        if "instagram.com" in url or "ig.me" in url:
            return re.sub(r'https?://[a-z0-9.\-]*(instagram\.com|ig\.me)', 'https://ddinstagram.com', url)
            
        # 2. SỬ DỤNG FACEBED CHO FACEBOOK
        if "facebook.com" in url or "fb.watch" in url:
            # Xóa các tham số rác đuôi ? (như ?fs=e) để Facebed dễ xử lý hơn
            clean_fb_url = url.split('?')[0]
            # Thay đổi trực tiếp tên miền sang facebed.com theo đúng hướng dẫn
            return re.sub(r'https?://[a-z0-9.\-]*(facebook\.com|fb\.watch)', 'https://facebed.com', clean_fb_url)
            
        return None

    # ============ LỆNH CHẨN ĐOÁN ============
    @commands.command(name="mdebug")
    @commands.has_permissions(manage_messages=True)
    async def mdebug(self, ctx, link: str):
        """Xem chính xác bot moi được gì: !mdebug <link>"""
        url = clean_url(link)
        async with aiohttp.ClientSession() as s:
            url = await self.resolve_url(s, url)
            if "tiktok.com" in url:
                post = await self.fetch_tiktok(s, url)
            elif "x.com" in url or "twitter.com" in url:
                post = await self.fetch_x(s, url)
            else:
                post = await self.fetch_meta(s, url)
        if not post:
            return await ctx.send(f"❌ Không trích xuất được.\nURL sau resolve: `{url}`")
        dump = {"url_final": url, "author": post["author"],
                "avatar_hop_le": bool(safe_url(post["avatar"])),
                "created_at": str(post["created_at"]),
                "text_len": len(post["text"]), "stats": post["stats"],
                "media": [(m.get("type"), (m.get("url") or "")[:60]) for m in post["media"]]}
        await ctx.send(f"```json\n{clip(json.dumps(dump, ensure_ascii=False, indent=2), 1900)}\n```")


async def setup(bot):
    await bot.add_cog(MediaEmbed(bot))
