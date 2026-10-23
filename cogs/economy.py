import discord
from discord.ext import commands
import random
import io
import os
import time
import aiosqlite
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN 
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_PATH = os.path.join(BASE_DIR, "assets") 
BG_PATH = os.path.join(ASSETS_PATH, "bgs")
CHAR_PATH = os.path.join(ASSETS_PATH, "chars")
UI_PATH = os.path.join(ASSETS_PATH, "ui")

def find_image(folder, filename):
    base_name = os.path.splitext(filename)[0]
    for ext in ['.png', '.jpg', '.jpeg']:
        path = os.path.join(folder, base_name + ext)
        if os.path.exists(path):
            return path
    return None

C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)
C_GOLD = discord.Color.from_rgb(255, 215, 0)

def make_progress_bar(current, maximum, length=14):
    ratio = 1.0 if maximum <= 0 else max(0.0, min(current / maximum, 1.0))
    filled = int(round(ratio * length))
    return "🟨" * filled + "⬛" * (length - filled), int(ratio * 100)

GACHA_DATA = {
    "5 Sao": {
        "rate": 0.6, "color": (255, 215, 0, 255), "embed_color": discord.Color.gold(),
        "stars": 5, "bg_file": "5star_bg",
        "items": [
            {"name": "Albedo", "file": "Albedo.png", "element": "geo"},
            {"name": "Alhaitham", "file": "Alhaitham.png", "element": "dendro"},
            {"name": "Aloy", "file": "Aloy.png", "element": "cryo"},
            {"name": "Arataki Itto", "file": "Arataki Itto.png", "element": "geo"},
            {"name": "Arlecchino", "file": "Arlecchino.png", "element": "pyro"},
            {"name": "Baizhu", "file": "Baizhu.png", "element": "dendro"},
            {"name": "Chasca", "file": "Chasca.png", "element": "anemo"},
            {"name": "Chiori", "file": "Chiori.png", "element": "geo"},
            {"name": "Citlali", "file": "Citlali.png", "element": "cryo"},
            {"name": "Clorinde", "file": "Clorinde.png", "element": "electro"},
            {"name": "Columbina", "file": "Columbina.png", "element": "cryo"},
            {"name": "Cyno", "file": "Cyno.png", "element": "electro"},
            {"name": "Dehya", "file": "Dehya.png", "element": "pyro"},
            {"name": "Diluc", "file": "Diluc.png", "element": "pyro"},
            {"name": "Emilie", "file": "Emilie.png", "element": "dendro"},
            {"name": "Eula", "file": "Eula.png", "element": "cryo"},
            {"name": "Furina", "file": "Furina.png", "element": "hydro"},
            {"name": "Ganyu", "file": "Ganyu.png", "element": "cryo"},
            {"name": "Hu Tao", "file": "Hu Tao.png", "element": "pyro"},
            {"name": "Jean", "file": "Jean.png", "element": "anemo"},
            {"name": "Kaedehara Kazuha", "file": "Kaedehara Kazuha.png", "element": "anemo"},
            {"name": "Kamisato Ayaka", "file": "Kamisato Ayaka.png", "element": "cryo"},
            {"name": "Kamisato Ayato", "file": "Kamisato Ayato.png", "element": "hydro"},
            {"name": "Keqing", "file": "Keqing.png", "element": "electro"},
            {"name": "Kinich", "file": "Kinich.png", "element": "dendro"},
            {"name": "Klee", "file": "Klee.png", "element": "pyro"},
            {"name": "Lyney", "file": "Lyney.png", "element": "pyro"},
            {"name": "Mavuika", "file": "Mavuika.png", "element": "pyro"},
            {"name": "Mona", "file": "Mona.png", "element": "hydro"},
            {"name": "Mualani", "file": "Mualani.png", "element": "hydro"},
            {"name": "Nahida", "file": "Nahida.png", "element": "dendro"},
            {"name": "Navia", "file": "Navia.png", "element": "geo"},
            {"name": "Neuvillette", "file": "Neuvillette.png", "element": "hydro"},
            {"name": "Nilou", "file": "Nilou.png", "element": "hydro"},
            {"name": "Qiqi", "file": "Qiqi.png", "element": "cryo"},
            {"name": "Raiden Shogun", "file": "Raiden Shogun.png", "element": "electro"},
            {"name": "Sangonomiya Kokomi", "file": "Sangonomiya Kokomi.png", "element": "hydro"},
            {"name": "Shenhe", "file": "Shenhe.png", "element": "cryo"},
            {"name": "Sigewinne", "file": "Sigewinne.png", "element": "hydro"},
            {"name": "Skirk", "file": "Skirk.png", "element": "hydro"},
            {"name": "Tartaglia", "file": "Tartaglia.png", "element": "hydro"},
            {"name": "Tighnari", "file": "Tighnari.png", "element": "dendro"},
            {"name": "Traveler", "file": "Traveler.png", "element": None},
            {"name": "Venti", "file": "Venti.png", "element": "anemo"},
            {"name": "Wanderer", "file": "Wanderer.png", "element": "anemo"},
            {"name": "Wriothesley", "file": "Wriothesley.png", "element": "cryo"},
            {"name": "Xianyun", "file": "Xianyun.png", "element": "anemo"},
            {"name": "Xiao", "file": "Xiao.png", "element": "anemo"},
            {"name": "Xilonen", "file": "Xilonen.png", "element": "geo"},
            {"name": "Yae Miko", "file": "Yae Miko.png", "element": "electro"},
            {"name": "Yelan", "file": "Yelan.png", "element": "hydro"},
            {"name": "Yoimiya", "file": "Yoimiya.png", "element": "pyro"},
            {"name": "Zhongli", "file": "Zhongli.png", "element": "geo"}
        ]
    },
    "4 Sao": {
        "rate": 5.1, "color": (148, 0, 211, 255), "embed_color": discord.Color.purple(),
        "stars": 4, "bg_file": "4star_bg",
        "items": [
            {"name": "Amber", "file": "Amber.png", "element": "pyro"},
            {"name": "Barbara", "file": "Barbara.png", "element": "hydro"},
            {"name": "Beidou", "file": "Beidou.png", "element": "electro"},
            {"name": "Bennett", "file": "Bennett.png", "element": "pyro"},
            {"name": "Candace", "file": "Candace.png", "element": "hydro"},
            {"name": "Charlotte", "file": "Charlotte.png", "element": "cryo"},
            {"name": "Chevreuse", "file": "Chevreuse.png", "element": "pyro"},
            {"name": "Chongyun", "file": "Chongyun.png", "element": "cryo"},
            {"name": "Collei", "file": "Collei.png", "element": "dendro"},
            {"name": "Dahlia", "file": "Dahlia.png", "element": "hydro"},
            {"name": "Diona", "file": "Diona.png", "element": "cryo"},
            {"name": "Dori", "file": "Dori.png", "element": "electro"},
            {"name": "Faruzan", "file": "Faruzan.png", "element": "anemo"},
            {"name": "Fischl", "file": "Fischl.png", "element": "electro"},
            {"name": "Freminet", "file": "Freminet.png", "element": "cryo"},
            {"name": "Gaming", "file": "Gaming.png", "element": "pyro"},
            {"name": "Gorou", "file": "Gorou.png", "element": "geo"},
            {"name": "Iansan", "file": "Iansan.png", "element": "electro"},
            {"name": "Ifa", "file": "Ifa.png", "element": "dendro"},
            {"name": "Kachina", "file": "Kachina.png", "element": "geo"},
            {"name": "Kaeya", "file": "Kaeya.png", "element": "cryo"},
            {"name": "Kaveh", "file": "Kaveh.png", "element": "dendro"},
            {"name": "Kirara", "file": "Kirara.png", "element": "dendro"},
            {"name": "Kujou Sara", "file": "Kujou Sara.png", "element": "electro"},
            {"name": "Kuki Shinobu", "file": "Kuki Shinobu.png", "element": "electro"},
            {"name": "Layla", "file": "Layla.png", "element": "cryo"},
            {"name": "Lisa", "file": "Lisa.png", "element": "electro"},
            {"name": "Lynette", "file": "Lynette.png", "element": "anemo"},
            {"name": "Mika", "file": "Mika.png", "element": "cryo"},
            {"name": "Ningguang", "file": "Ningguang.png", "element": "geo"},
            {"name": "Noelle", "file": "Noelle.png", "element": "geo"},
            {"name": "Ororon", "file": "Ororon.png", "element": "electro"},
            {"name": "Razor", "file": "Razor.png", "element": "electro"},
            {"name": "Rosaria", "file": "Rosaria.png", "element": "cryo"},
            {"name": "Sayu", "file": "Sayu.png", "element": "anemo"},
            {"name": "Sethos", "file": "Sethos.png", "element": "electro"},
            {"name": "Shikanoin Heizou", "file": "Shikanoin Heizou.png", "element": "anemo"},
            {"name": "Sucrose", "file": "Sucrose.png", "element": "anemo"},
            {"name": "Thoma", "file": "Thoma.png", "element": "pyro"},
            {"name": "Xiangling", "file": "Xiangling.png", "element": "pyro"},
            {"name": "Xingqiu", "file": "Xingqiu.png", "element": "hydro"},
            {"name": "Xinyan", "file": "Xinyan.png", "element": "pyro"},
            {"name": "Yanfei", "file": "Yanfei.png", "element": "pyro"},
            {"name": "Yaoyao", "file": "Yaoyao.png", "element": "dendro"},
            {"name": "Yunjin", "file": "Yunjin.png", "element": "geo"}
        ]
    },
    "3 Sao": {
        "rate": 94.3, "color": (120, 120, 120, 255), "embed_color": discord.Color.light_grey(),
        "stars": 3, "bg_file": "3star_bg",
        "items": [
            {"name": "Mẫu Kim Phách", "file": "Weapon_Amber_Catalyst.png", "element": None},
            {"name": "Hắc Anh Thương", "file": "Weapon_Black_Tassel.png", "element": None},
            {"name": "Kiếm Huyết Rồng", "file": "Weapon_Bloodtainted_Greatsword.png", "element": None},
            {"name": "Lãnh Nhẫn", "file": "Weapon_Cool_Steel.png", "element": None},
            {"name": "Kiếm Sắt Đen", "file": "Weapon_Dark_Iron_Sword.png", "element": None},
            {"name": "Thần Kiếm Lê Minh", "file": "Weapon_Harbinger_of_Dawn.png", "element": None},
            {"name": "Tín Sứ", "file": "Weapon_Messenger.png", "element": None},
            {"name": "Tiểu Thuyết Dị Giới", "file": "Weapon_Otherworldly_Story.png", "element": None},
            {"name": "Kiếm Thạch Anh", "file": "Weapon_Quartz.png", "element": None},
            {"name": "Cung Phản Khúc", "file": "Weapon_Recurve_Bow.png", "element": None},
            {"name": "Nỏ Kéo", "file": "Weapon_Slingshot.png", "element": None},
            {"name": "Câu Chuyện Diệt Rồng", "file": "Weapon_Thrilling_Tales_of_Dragon_Slayers.png", "element": None},
            {"name": "Kiếm Lữ Hành", "file": "Weapon_Traveler_Handy_Sword.png", "element": None},
            {"name": "Bạch Anh Thương", "file": "Weapon_White_Tassel.png", "element": None}
        ]
    }
}

def generate_banner_ui(banner_chars):
    canvas_w, canvas_h = 900, 450
    img = Image.new('RGB', (canvas_w, canvas_h), (30, 32, 40))
    draw = ImageDraw.Draw(img)
    
    try:
        font_path = "arial.ttf"
        if not os.path.exists("arial.ttf") and os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font_title = ImageFont.truetype(font_path, 40)
        font_char = ImageFont.truetype(font_path, 30)
    except:
        font_title = font_char = ImageFont.load_default()

    bg_path = find_image(BG_PATH, "banner_bg")
    if bg_path:
        try:
            bg = Image.open(bg_path).convert("RGBA").resize((canvas_w, canvas_h))
            img.alpha_composite(bg, (0, 0))
        except: pass

    draw.text((canvas_w//2, 45), "NHÂN VẬT GIỚI HẠN KỲ NÀY", fill=(255, 215, 0), font=font_title, anchor="mm")
    
    centers = [260, 640]
    item_w, item_h = 280, 320
    
    for i, char in enumerate(banner_chars):
        cx = centers[i]
        cy = 100
        
        draw.rectangle([cx - item_w//2, cy, cx + item_w//2, cy + item_h], fill=(50, 50, 65), outline=(255, 215, 0), width=4)
        
        char_path = find_image(CHAR_PATH, char["file"])
        if char_path:
            try:
                c_img = Image.open(char_path).convert("RGBA")
                c_img = ImageOps.fit(c_img, (item_w - 10, item_h - 50), Image.Resampling.LANCZOS)
                img.paste(c_img, (cx - (item_w - 10)//2, cy + 5), c_img)
            except: pass
        
        draw.rectangle([cx - item_w//2, cy + item_h - 40, cx + item_w//2, cy + item_h], fill=(255, 215, 0))
        draw.text((cx, cy + item_h - 20), char["name"], fill="black", font=font_char, anchor="mm")
        
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==========================================
# GIAO DIỆN NÚT BẤM (VIEWS)
# ==========================================
class GachaView(discord.ui.View):
    def __init__(self, cog, author_id):
        super().__init__(timeout=300) # Tăng timeout lên 5 phút để roll thoải mái
        self.cog = cog
        self.author_id = author_id

    # HÀM XỬ LÝ CHUNG: Ẩn ảnh cũ -> Hiện "Đang load" -> Tính toán -> Đè ảnh mới lên
    async def handle_roll(self, interaction: discord.Interaction, num_rolls: int):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Đây không phải là đài cầu nguyện của bạn!", ephemeral=True)
        
        # BƯỚC 1: KIỂM TRA TIỀN TRƯỚC TIÊN ĐỂ KHÔNG BỊ KẸT MÀN HÌNH LOAD
        cost = 160 * num_rolls
        balance = await self.cog.get_balance(interaction.guild.id, interaction.user.id)
        if balance < cost:
            embed = discord.Embed(
                title="❌ KHÔNG ĐỦ NGUYÊN THẠCH!",
                description=(f"Cần **{cost:,} nguyên thạch** để cầu nguyện {num_rolls} lần.\n"
                             f"💳 Số dư của bạn: **{balance:,} nguyên thạch**\n\n"
                             "*💡 Dùng `f!daily` và `f!work` để kiếm thêm!*"),
                color=C_ERROR
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # BƯỚC 2: KHÓA NÚT VÀ HIỆN MÀN HÌNH "ĐANG CẦU NGUYỆN" (Xóa ảnh kết quả cũ đi)
        for item in self.children: item.disabled = True
        
        title_text = "🌠 ĐANG CẦU NGUYỆN..."
        desc_text = "🌟 Mưa sao băng đang giáng xuống...\nXin chờ trong giây lát!" if num_rolls == 10 else "✨ Ngôi sao đang bay qua bầu trời...\nXin chờ trong giây lát!"
        loading_embed = discord.Embed(title=title_text, description=desc_text, color=C_BRAND)
        
        # Quan trọng: attachments=[] sẽ xóa bức ảnh cũ để màn hình load nhìn sạch sẽ
        await interaction.response.edit_message(embed=loading_embed, attachments=[], view=self)
        
        # BƯỚC 3: CHẠY LOGIC TÍNH TOÁN VÀ RENDER ẢNH
        await self.cog.process_gacha(interaction, num_rolls)

    @discord.ui.button(label="Cầu Nguyện 1 Lần", style=discord.ButtonStyle.primary, emoji="✨")
    async def roll_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_roll(interaction, 1)

    @discord.ui.button(label="Cầu Nguyện 10 Lần", style=discord.ButtonStyle.success, emoji="🌟")
    async def roll_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_roll(interaction, 10)


class InventoryView(discord.ui.View):
    def __init__(self, ctx, author_id, inv_items):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.author_id = author_id
        self.inv_items = inv_items
        self.current_page = 1
        self.current_filter = "all"
        self.items_per_page = 15 # Hiển thị 15 vật phẩm mỗi trang để dễ nhìn
        self.update_buttons()

    def get_filtered_items(self):
        if self.current_filter == "all": return self.inv_items
        elif self.current_filter == "5": return [i for i in self.inv_items if i['rarity'] == "5 Sao"]
        elif self.current_filter == "4": return [i for i in self.inv_items if i['rarity'] == "4 Sao"]
        elif self.current_filter == "3": return [i for i in self.inv_items if i['rarity'] == "3 Sao"]

    def get_embed(self):
        filtered = self.get_filtered_items()
        total_pages = max(1, (len(filtered) - 1) // self.items_per_page + 1) if filtered else 1
        if self.current_page > total_pages: self.current_page = total_pages
        if self.current_page < 1: self.current_page = 1

        start = (self.current_page - 1) * self.items_per_page
        end = start + self.items_per_page
        page_items = filtered[start:end]

        embed = discord.Embed(
            title=f"🎒 TÚI ĐỒ CỦA {self.ctx.author.display_name.upper()}",
            description=f"📦 Tổng số vật phẩm: **{sum(i['count'] for i in filtered)}**\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=C_GOLD
        )
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)

        if not page_items:
            embed.description += "\n\n📭 Không có vật phẩm nào trong phân loại này!"
        else:
            s5, s4, s3 = [], [], []
            # ✅ YÊU CẦU 2: ĐÃ ĐƯA MỖI VẬT PHẨM XUỐNG 1 DÒNG RIÊNG BIỆT (Dùng bullet points)
            for item in page_items:
                text = f"> • **{item['name']}** `(x{item['count']})`"
                if item['rarity'] == "5 Sao": s5.append(text)
                elif item['rarity'] == "4 Sao": s4.append(text)
                else: s3.append(text)

            if s5: embed.add_field(name="🌟 Nhân vật 5 Sao", value="\n".join(s5), inline=False)
            if s4: embed.add_field(name="⭐ Nhân vật 4 Sao", value="\n".join(s4), inline=False)
            if s3: embed.add_field(name="🗡️ Vũ khí 3 Sao", value="\n".join(s3), inline=False)

        embed.set_footer(text=f"Trang {self.current_page}/{total_pages} • Dùng f!team_set để xếp đội hình")
        return embed

    def update_buttons(self):
        filtered = self.get_filtered_items()
        total_pages = max(1, (len(filtered) - 1) // self.items_per_page + 1) if filtered else 1
        
        # Quản lý nút chuyển trang (Row 0)
        self.btn_prev.disabled = self.current_page <= 1
        self.btn_next.disabled = self.current_page >= total_pages
        
        # Quản lý nút phân loại (Row 1) - Làm nổi bật nút đang chọn
        self.btn_all.style = discord.ButtonStyle.primary if self.current_filter == "all" else discord.ButtonStyle.secondary
        self.btn_5.style = discord.ButtonStyle.primary if self.current_filter == "5" else discord.ButtonStyle.secondary
        self.btn_4.style = discord.ButtonStyle.primary if self.current_filter == "4" else discord.ButtonStyle.secondary
        self.btn_3.style = discord.ButtonStyle.primary if self.current_filter == "3" else discord.ButtonStyle.secondary

    @discord.ui.button(label="◀ Trước", style=discord.ButtonStyle.secondary, custom_id="prev", row=0)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("❌ Không phải túi đồ của bạn!", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Sau ▶", style=discord.ButtonStyle.secondary, custom_id="next", row=0)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("❌ Không phải túi đồ của bạn!", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Tất cả", style=discord.ButtonStyle.primary, row=1)
    async def btn_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("❌ Không phải túi đồ của bạn!", ephemeral=True)
        self.current_filter = "all"
        self.current_page = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="5 Sao", style=discord.ButtonStyle.secondary, emoji="🌟", row=1)
    async def btn_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("❌ Không phải túi đồ của bạn!", ephemeral=True)
        self.current_filter = "5"
        self.current_page = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="4 Sao", style=discord.ButtonStyle.secondary, emoji="⭐", row=1)
    async def btn_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("❌ Không phải túi đồ của bạn!", ephemeral=True)
        self.current_filter = "4"
        self.current_page = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="3 Sao", style=discord.ButtonStyle.secondary, emoji="🗡️", row=1)
    async def btn_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: return await interaction.response.send_message("❌ Không phải túi đồ của bạn!", ephemeral=True)
        self.current_filter = "3"
        self.current_page = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class EconomyGacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = getattr(self.bot.database, 'database_path', './data/famibot.db')

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "game" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Economy!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False 
        return True 

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("PRAGMA busy_timeout = 60000")
            await self.ensure_tables(db)
            await db.commit()

    # ĐẢM BẢO TẠO BẢNG THEO KHÓA KÉP
    async def ensure_tables(self, db):
        await db.execute('''CREATE TABLE IF NOT EXISTS cooldown_state (
            guild_id INTEGER, user_id INTEGER, last_daily TEXT, last_work TEXT, PRIMARY KEY(guild_id, user_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS gacha_state (
            guild_id INTEGER, user_id INTEGER, pity5 INTEGER DEFAULT 0, guaranteed INTEGER DEFAULT 0, pity4 INTEGER DEFAULT 0, PRIMARY KEY(guild_id, user_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            guild_id INTEGER, user_id INTEGER, item_name TEXT, rarity TEXT)''')
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

    async def get_inventory(self, guild_id, user_id):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            cursor = await db.execute("SELECT item_name, rarity, COUNT(*) FROM inventory WHERE guild_id = ? AND user_id = ? GROUP BY item_name, rarity", (guild_id, user_id))
            rows = await cursor.fetchall()
            return {row[0].lower(): {"name": row[0], "rarity": row[1], "count": row[2]} for row in rows}

    def get_banner_info(self):
        epoch = int(time.time())
        banner_period = epoch // (20 * 86400) 
        
        standard_names = ["Diluc", "Jean", "Keqing", "Mona", "Qiqi", "Tighnari", "Dehya"]
        all_5_stars = GACHA_DATA["5 Sao"]["items"]
        
        limited_pool = [c for c in all_5_stars if c["name"] not in standard_names]
        standard_pool = [c for c in all_5_stars if c["name"] in standard_names]
        
        random.seed(banner_period)
        banner_chars = random.sample(limited_pool, 2)
        random.seed() 
        
        next_period = (banner_period + 1) * 20 * 86400
        time_left = next_period - epoch
        days = time_left // 86400
        hours = (time_left % 86400) // 3600
        
        return banner_chars, standard_pool, days, hours

    @commands.hybrid_command(name="inventory", description="Xem túi đồ và tất cả các nhân vật/vũ khí bạn đã quay được.")
    async def inventory(self, ctx: commands.Context):
        inv_dict = await self.get_inventory(ctx.guild.id, ctx.author.id)
        if not inv_dict:
            return await ctx.send(embed=discord.Embed(
                description="🎒 Túi đồ của bạn tại Server này đang trống! Hãy dùng `f!gacha` để cầu nguyện nhé.",
                color=C_WARN
            ))

        def rarity_weight(r):
            if r == "5 Sao": return 1
            if r == "4 Sao": return 2
            return 3

        inv_items = list(inv_dict.values())
        inv_items.sort(key=lambda x: (rarity_weight(x['rarity']), x['name']))

        # GỌI VIEW VỚI UI MỚI PHÂN TRANG & LỌC
        view = InventoryView(ctx, ctx.author.id, inv_items)
        await ctx.send(embed=view.get_embed(), view=view)

    @commands.hybrid_command(name="banner", description="Xem thông tin Banner Giới Hạn hiện tại.")
    async def banner(self, ctx: commands.Context):
        await ctx.defer()
        banner_chars, _, days, hours = self.get_banner_info()
        char_names = " và ".join([f"**{c['name']}**" for c in banner_chars])
        
        image_buffer = await self.bot.loop.run_in_executor(None, generate_banner_ui, banner_chars)
        file = discord.File(image_buffer, filename="banner.png")
        
        embed = discord.Embed(
            title="🌠 BANNER GIỚI HẠN KỲ NÀY 🌠",
            description=(
                f"✨ Nhân vật rate-up: {char_names}\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"⏳ **Thời gian còn lại:** `{days} ngày {hours} giờ`\n"
                "🍀 *Chúc bạn may mắn nổ vàng sớm nhé!*"
            ),
            color=C_GOLD
        )
        embed.set_image(url="attachment://banner.png")
        embed.set_footer(text="💡 Quay f!gacha để cầu nguyện • Tỷ lệ 55/45 • Có Bảo Hiểm")
        await ctx.send(embed=embed, file=file)

    @commands.hybrid_command(name="pity", description="Xem lịch sử tích lũy (Pity) và Bảo Hiểm Gacha.")
    async def pity(self, ctx: commands.Context):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO gacha_state (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, ctx.author.id))
            await db.commit() 
            c = await db.execute("SELECT pity5, guaranteed, pity4 FROM gacha_state WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
            pity5, guaranteed, pity4 = await c.fetchone()
            
            pity5 = int(pity5) if pity5 is not None else 0
            guaranteed = int(guaranteed) if guaranteed is not None else 0
            pity4 = int(pity4) if pity4 is not None else 0
            
        bar5, _ = make_progress_bar(pity5, 90)
        bar4, _ = make_progress_bar(pity4, 10)
        embed = discord.Embed(title=f"📊 HỒ SƠ CẦU NGUYỆN TẠI {ctx.guild.name}", color=C_BRAND)
        embed.set_author(name=f"Nhà lữ hành {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="🌟 Tích lũy 5 Sao", value=f"{bar5} **{pity5}/90**\n*(Rate tăng vọt từ lượt 74 trở đi)*", inline=False)
        embed.add_field(name="⭐ Tích lũy 4 Sao", value=f"{bar4} **{pity4}/10**", inline=False)
        embed.add_field(
            name="🛡️ Trạng thái Bảo Hiểm",
            value="✅ **Đang kích hoạt!** — Chắc chắn nổ tướng Giới Hạn ở lần nổ vàng tới!" if guaranteed else "🎲 **55/45** — 55% trúng Banner • 45% lệch sang tướng thường",
            inline=False
        )
        embed.set_footer(text="✨ FamiBot • Chúc bạn sớm nổ vàng!")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="balance", description="Xem số dư nguyên thạch hiện tại.")
    async def balance(self, ctx: commands.Context):
        coins = await self.get_balance(ctx.guild.id, ctx.author.id)
        embed = discord.Embed(
            title=f"💳 VÍ NGUYÊN THẠCH TẠI {ctx.guild.name.upper()}",
            description=f"💰 Số dư hiện tại của bạn:\n**{coins:,} nguyên thạch**",
            color=C_GOLD
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="✨ FamiBot • Dùng f!daily và f!work để kiếm thêm!")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Điểm danh nhận tiền thưởng mỗi ngày.")
    async def daily(self, ctx: commands.Context):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO cooldown_state (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, ctx.author.id))
            
            cur = await db.execute("SELECT last_daily FROM cooldown_state WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
            row = await cur.fetchone()
            last_daily = row[0] if row else None

            now = datetime.now(timezone.utc)
            if last_daily:
                last_dt = datetime.fromisoformat(last_daily)
                remaining = (last_dt + __import__("datetime").timedelta(hours=24)) - now
                if remaining.total_seconds() > 0:
                    h, rem = divmod(int(remaining.total_seconds()), 3600)
                    m, _ = divmod(rem, 60)
                    return await ctx.send(embed=discord.Embed(
                        description=f"⏳ Bạn đã điểm danh hôm nay rồi! Thử lại sau `{h}h{m}p` nhé.",
                        color=C_WARN
                    ))

            reward = random.randint(100, 400)
            await db.execute("UPDATE cooldown_state SET last_daily = ? WHERE guild_id = ? AND user_id = ?", (now.isoformat(), ctx.guild.id, ctx.author.id))
            await db.commit()

        await self.add_balance(ctx.guild.id, ctx.author.id, reward)
        new_balance = await self.get_balance(ctx.guild.id, ctx.author.id)

        embed = discord.Embed(
            title="🎁 ĐIỂM DANH THÀNH CÔNG!",
            description=(
                f"{ctx.author.mention} đã nhận quà hàng ngày tại **{ctx.guild.name}**!\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💰 **Phần thưởng:** `+{reward:,} nguyên thạch`\n"
                f"💳 **Số dư mới:** `{new_balance:,} nguyên thạch`"
            ),
            color=C_SUCCESS
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="✨ FamiBot • Hẹn gặp lại bạn vào ngày mai!")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="work", description="Làm việc chăm chỉ để kiếm nguyên thạch (Hồi chiêu 2 tiếng).")
    async def work(self, ctx: commands.Context):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO cooldown_state (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, ctx.author.id))
            
            cur = await db.execute("SELECT last_work FROM cooldown_state WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
            row = await cur.fetchone()
            last_work = row[0] if row else None

            now = datetime.now(timezone.utc)
            if last_work:
                last_dt = datetime.fromisoformat(last_work)
                remaining = (last_dt + __import__("datetime").timedelta(hours=2)) - now
                if remaining.total_seconds() > 0:
                    m, s = divmod(int(remaining.total_seconds()), 60)
                    return await ctx.send(embed=discord.Embed(
                        description=f"😮‍💨 Bạn vừa làm việc xong, hãy nghỉ ngơi thêm `{m}p{s}s` nữa!",
                        color=C_WARN
                    ))

            await db.execute("UPDATE cooldown_state SET last_work = ? WHERE guild_id = ? AND user_id = ?", (now.isoformat(), ctx.guild.id, ctx.author.id))
            await db.commit()

        jobs = [
            "khai thác khoáng sản", "tiêu diệt Hilichurl", "giao hàng ăn", "đóng thế cho Furina", 
            "trông coi quán Wangshu", "quét đền Narukami", "luyện tập kiếm thuật", "trồng nấm trong rừng", 
            "bán đồ cổ ở Liyue", "làm bánh mì cho Mondstadt", "vẽ tranh phong cảnh", "luyện tập bắn cung"
        ]
        job = random.choice(jobs)
        reward = random.randint(100, 900)
        
        await self.add_balance(ctx.guild.id, ctx.author.id, reward)
        new_balance = await self.get_balance(ctx.guild.id, ctx.author.id)

        embed = discord.Embed(
            title="💼 ĐI LÀM KIẾM TIỀN",
            description=(
                f"{ctx.author.mention} vừa đi **{job}** và nhận được lương!\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💰 **Thu nhập:** `+{reward:,} nguyên thạch`\n"
                f"💳 **Số dư mới:** `{new_balance:,} nguyên thạch`"
            ),
            color=C_SUCCESS
        )
        embed.set_footer(text="✨ FamiBot • Nghỉ ngơi 2 tiếng rồi đi làm tiếp nhé!")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="bet", description="Cược nguyên thạch 50-50.")
    async def bet(self, ctx: commands.Context, amount: int):
        if amount < 10:
            return await ctx.send(embed=discord.Embed(description="⚠️ Mức cược tối thiểu là **10 nguyên thạch**!", color=C_WARN))
        
        success = await self.try_deduct_balance(ctx.guild.id, ctx.author.id, amount)
        if not success:
            balance = await self.get_balance(ctx.guild.id, ctx.author.id)
            return await ctx.send(embed=discord.Embed(description=f"❌ Bạn không đủ tiền! Số dư hiện tại: **{balance:,} nguyên thạch**.", color=C_ERROR))

        if random.choice([True, False]):
            await self.add_balance(ctx.guild.id, ctx.author.id, amount * 2)
            balance = await self.get_balance(ctx.guild.id, ctx.author.id)
            embed = discord.Embed(
                title="🎰 THẮNG LỚN!!!",
                description=(
                    f"🎊 {ctx.author.mention} nhận được **{amount:,} nguyên thạch**!\n"
                    f"💳 Số dư mới: `{balance:,} nguyên thạch`"
                ),
                color=C_GOLD
            )
        else:
            balance = await self.get_balance(ctx.guild.id, ctx.author.id)
            embed = discord.Embed(
                title="🎰 CHIA BUỒN...",
                description=(
                    f"💸 {ctx.author.mention} đã mất **{amount:,} nguyên thạch**.\n"
                    f"💳 Số dư còn lại: `{balance:,} nguyên thạch`\n\n"
                    "*Gỡ gạc vào ván sau nhé!*"
                ),
                color=C_ERROR
            )
        embed.set_footer(text="✨ FamiBot • Sòng bạc 50/50")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="gacha", description="Mở giao diện Cầu Nguyện Nhân Vật.")
    async def gacha_menu(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🌠 ĐÀI CẦU NGUYỆN 🌠",
            description=(
                "Chọn số lần cầu nguyện bạn muốn thực hiện:\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "✨ **Cầu 1 lần** — `160 nguyên thạch`\n"
                "🌟 **Cầu 10 lần** — `1.600 nguyên thạch`\n"
                "> 🎁 *Cầu 10 lần đảm bảo ít nhất một vật phẩm 4 Sao!*"
            ),
            color=C_BRAND
        )
        banner_chars, _, _, _ = self.get_banner_info()
        char_names = " & ".join([f"{c['name']}" for c in banner_chars])
        embed.set_footer(text=f"🌠 Banner: {char_names} • Rate Up 55/45 • Có Bảo Hiểm")
        
        view = GachaView(self, ctx.author.id)
        await ctx.send(embed=embed, view=view)

    # ✅ YÊU CẦU 1: HÀM GACHA ĐÃ ĐƯỢC CẢI TIẾN ĐỂ EDIT TIN NHẮN CHỨ KHÔNG GỬI MỚI
    async def process_gacha(self, interaction: discord.Interaction, num_rolls: int):
        cost = 160 * num_rolls
        success = await self.try_deduct_balance(interaction.guild.id, interaction.user.id, cost)
        
        if not success:
            # Nếu hết tiền bất chợt (do vừa bet thua xong quay gacha), báo lỗi thay vì load tiếp
            return await interaction.edit_original_response(content="❌ Giao dịch thất bại (Số dư của bạn đã thay đổi).", embed=None, view=None, attachments=[])

        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO gacha_state (guild_id, user_id) VALUES (?, ?)", (interaction.guild.id, interaction.user.id))
            await db.commit() 
            c = await db.execute("SELECT pity5, guaranteed, pity4 FROM gacha_state WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, interaction.user.id))
            pity5, guaranteed, pity4 = await c.fetchone()
            
            pity5 = int(pity5) if pity5 is not None else 0
            guaranteed = int(guaranteed) if guaranteed is not None else 0
            pity4 = int(pity4) if pity4 is not None else 0

        banner_chars, standard_pool, _, _ = self.get_banner_info()
        all_4_stars = GACHA_DATA["4 Sao"]["items"]
        all_3_stars = GACHA_DATA["3 Sao"]["items"]

        pulled_items = []
        star5_count = 0
        captured_light_triggered = False

        for _ in range(num_rolls):
            pity5 += 1
            pity4 += 1
            
            is_5_star = False
            rate_5 = 0.6
            if pity5 == 90:
                is_5_star = True 
            elif pity5 >= 74:
                rate_5 += (pity5 - 73) * 6.0 

            if not is_5_star and random.uniform(0, 100) <= rate_5:
                is_5_star = True

            if is_5_star:
                pity5 = 0
                pity4 = 0 
                rarity = "5 Sao"
                star5_count += 1
                
                if guaranteed:
                    item = random.choice(banner_chars)
                    guaranteed = 0
                else:
                    if random.uniform(0, 100) <= 55: 
                        item = random.choice(banner_chars)
                        guaranteed = 0
                    else: 
                        if random.uniform(0, 100) <= 10: 
                            item = random.choice(banner_chars)
                            guaranteed = 0
                            captured_light_triggered = True
                        else:
                            item = random.choice(standard_pool)
                            guaranteed = 1 
            else:
                is_4_star = False
                if pity4 >= 10: 
                    is_4_star = True
                elif random.uniform(0, 100) <= GACHA_DATA["4 Sao"]["rate"]:
                    is_4_star = True
                    
                if is_4_star:
                    pity4 = 0
                    rarity = "4 Sao"
                    item = random.choice(all_4_stars)
                else:
                    rarity = "3 Sao"
                    item = random.choice(all_3_stars)

            pulled_items.append({"rarity": rarity, "data": item, "info": GACHA_DATA[rarity]})

        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("UPDATE gacha_state SET pity5 = ?, guaranteed = ?, pity4 = ? WHERE guild_id = ? AND user_id = ?", (pity5, guaranteed, pity4, interaction.guild.id, interaction.user.id))
            for result in pulled_items:
                await db.execute(
                    "INSERT INTO inventory (guild_id, user_id, item_name, rarity) VALUES (?, ?, ?, ?)",
                    (interaction.guild.id, interaction.user.id, result["data"]["name"], result["rarity"])
                )
                if result["rarity"] in ("4 Sao", "5 Sao"):
                    await db.execute(
                        "INSERT OR IGNORE INTO char_stats (guild_id, user_id, char_name, level, xp) VALUES (?, ?, ?, 1, 0)",
                        (interaction.guild.id, interaction.user.id, result["data"]["name"])
                    )
            await db.commit()

        try:
            if num_rolls == 1:
                canvas_w, canvas_h = 600, 700
                cols = 1
                item_w, item_h = 260, 360
                padding_x, padding_y = 0, 0
                start_x = (canvas_w - item_w) // 2
                start_y = 200
            else:
                canvas_w, canvas_h = 1600, 950
                cols = 5
                item_w, item_h = 260, 360
                padding_x, padding_y = 40, 40
                start_x = (canvas_w - (5 * item_w + 4 * padding_x)) // 2
                start_y = 120

            final_img = Image.new("RGBA", (canvas_w, canvas_h), color=(15, 15, 25, 255))
            draw = ImageDraw.Draw(final_img)

            try:
                font_path = os.path.join(UI_PATH, "font.ttf")
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, 35)
                    header_font = ImageFont.truetype(font_path, 80)
                else:
                    font = ImageFont.truetype("arial.ttf", 35)
                    header_font = ImageFont.truetype("arialbd.ttf", 80)
            except:
                font = ImageFont.load_default()
                header_font = ImageFont.load_default()

            header_path = find_image(UI_PATH, "header")
            if header_path:
                header_img = Image.open(header_path).convert("RGBA")
                if header_img.width > canvas_w:
                    ratio = canvas_w / header_img.width
                    header_img = header_img.resize((canvas_w, int(header_img.height * ratio)))
                h_paste_x = (canvas_w - header_img.width) // 2
                final_img.alpha_composite(header_img, (h_paste_x, 10))
            else:
                header_text = "CONGRATULATIONS!"
                try:
                    left, top, right, bottom = draw.textbbox((0, 0), header_text, font=header_font)
                    text_w = right - left
                except AttributeError:
                    text_w, _ = draw.textsize(header_text, font=header_font)
                
                h_paste_x = (canvas_w - text_w) // 2
                for offset_x in [-3, 0, 3]:
                    for offset_y in [-3, 0, 3]:
                        draw.text((h_paste_x + offset_x, 20 + offset_y), header_text, font=header_font, fill="black")
                draw.text((h_paste_x, 20), header_text, font=header_font, fill=(255, 215, 0, 255))

            for i, result in enumerate(pulled_items):
                row = i // cols
                col = i % cols
                x = start_x + col * (item_w + padding_x)
                y = start_y + row * (item_h + padding_y)

                bg_path = find_image(BG_PATH, result["info"]["bg_file"])
                if bg_path:
                    card_bg = Image.open(bg_path).convert("RGBA").resize((item_w, item_h))
                    final_img.alpha_composite(card_bg, (x, y))
                else:
                    draw.rectangle([x, y, x + item_w, y + item_h], fill=result["info"]["color"])

                char_path = find_image(CHAR_PATH, result["data"]["file"])
                if char_path:
                    char_img = Image.open(char_path).convert("RGBA")
                    char_img = char_img.resize((int(item_w * 0.9), int(item_h * 0.8)))
                    paste_x = x + (item_w - char_img.width) // 2
                    paste_y = y + (item_h - char_img.height) // 2
                    final_img.alpha_composite(char_img, (paste_x, paste_y))
                else:
                    fallback_text = result["data"]["name"]
                    try:
                        left, top, right, bottom = draw.textbbox((0, 0), fallback_text, font=font)
                        t_w = right - left
                    except AttributeError:
                        t_w, _ = draw.textsize(fallback_text, font=font)
                    
                    t_x = x + (item_w - t_w) // 2
                    t_y = y + (item_h // 2) - 20
                    for ox in [-2, 0, 2]:
                        for oy in [-2, 0, 2]:
                            draw.text((t_x + ox, t_y + oy), fallback_text, font=font, fill="black")
                    draw.text((t_x, t_y), fallback_text, font=font, fill="white")

                if result["data"]["element"]:
                    el_path = find_image(UI_PATH, result["data"]["element"])
                    if el_path:
                        el_icon = Image.open(el_path).convert("RGBA").resize((50, 50))
                        final_img.alpha_composite(el_icon, (x + 10, y + 10))

                star_path = find_image(UI_PATH, "star")
                if star_path:
                    star_icon = Image.open(star_path).convert("RGBA").resize((25, 25))
                    num_stars = result["info"]["stars"]
                    star_total_width = num_stars * 25
                    star_start_x = x + (item_w - star_total_width) // 2
                    star_start_y = y + item_h - 35
                    for s in range(num_stars):
                        final_img.alpha_composite(star_icon, (star_start_x + (s * 25), star_start_y))

                draw.rectangle([x, y, x + item_w, y + item_h], outline=(255, 255, 255, 100), width=3)

            img_buffer = io.BytesIO()
            final_img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            d_file = discord.File(fp=img_buffer, filename=f"gacha_x{num_rolls}.png")

            e_color = discord.Color.gold() if star5_count > 0 else discord.Color.purple()
            balance = await self.get_balance(interaction.guild.id, interaction.user.id)
            
            desc_text = (
                f"🎊 {interaction.user.mention} vừa dâng **{cost:,} nguyên thạch** lên đài cầu nguyện!\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            )
            if star5_count > 0:
                desc_text += f"🌟 **NỔ VÀNG!** Bạn nhận được **{star5_count} nhân vật 5 Sao**!\n"
            else:
                desc_text += "⭐ *Lần này chưa có vàng, nhưng đừng nản nhé!*\n"

            if captured_light_triggered:
                desc_text += "\n✨ **Bắt Lấy Ánh Sáng đã xuất hiện!** Định mệnh đã bị bẻ cong để mang nhân vật Banner về cho bạn!"

            embed = discord.Embed(
                title=f"🎉 KẾT QUẢ CẦU NGUYỆN x{num_rolls}",
                description=desc_text,
                color=e_color
            )
            embed.set_image(url=f"attachment://gacha_x{num_rolls}.png")
            embed.set_footer(text=f"💳 Số dư còn lại tại Server: {balance:,} NT • Dùng f!pity để xem lịch sử")
            
            # ✅ YÊU CẦU 1: CẤP LẠI NÚT BẤM (GachaView) ĐỂ NGƯỜI DÙNG QUAY TIẾP LIÊN TỤC
            new_view = GachaView(self, interaction.user.id)
            await interaction.edit_original_response(embed=embed, attachments=[d_file], view=new_view)

        except Exception as e:
            print(f"Lỗi ảnh: {e}")
            new_view = GachaView(self, interaction.user.id)
            await interaction.edit_original_response(content="❌ Đã có lỗi xảy ra khi tạo ảnh Gacha.", embed=None, attachments=[], view=new_view)

async def setup(bot):
    await bot.add_cog(EconomyGacha(bot))