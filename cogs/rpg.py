import discord
from discord.ext import commands
import random
import aiosqlite
import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# 🎨 BẢNG MÀU, THANH TIẾN TRÌNH & ĐƯỜNG DẪN
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_PATH = os.path.join(BASE_DIR, "assets")
BOSS_PATH = os.path.join(ASSETS_PATH, "bosses")
CHAR_PATH = os.path.join(ASSETS_PATH, "chars")
UI_PATH = os.path.join(ASSETS_PATH, "ui")

C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)
C_GOLD = discord.Color.from_rgb(255, 215, 0)
C_ORANGE = discord.Color.from_rgb(255, 159, 67)
C_PURPLE = discord.Color.from_rgb(155, 89, 182)

def make_progress_bar(current, maximum, length=14):
    ratio = 1.0 if maximum <= 0 else max(0.0, min(current / maximum, 1.0))
    filled = int(round(ratio * length))
    return "🟨" * filled + "⬛" * (length - filled), int(ratio * 100)

def find_image(folder, filename):
    base_name = os.path.splitext(filename)[0]
    for ext in ['.png', '.jpg', '.jpeg']:
        path = os.path.join(folder, base_name + ext)
        if os.path.exists(path):
            return path
    return None

def load_fonts(size_normal=30, size_header=60):
    candidates = [
        os.path.join(UI_PATH, "font.ttf"),
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    def _pick(size):
        for path in candidates:
            try:
                if path == "arial.ttf" or os.path.exists(path):
                    return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()
    return _pick(size_normal), _pick(size_header)

# ==========================================
# CƠ SỞ DỮ LIỆU GENSHIN IMPACT
# ==========================================
WEAPONS = [
    "Mẫu Kim Phách", "Hắc Anh Thương", "Kiếm Huyết Rồng", 
    "Lãnh Nhẫn", "Kiếm Sắt Đen", "Thần Kiếm Lê Minh", "Tín Sứ", 
    "Tiểu Thuyết Dị Giới", "Kiếm Thạch Anh", "Cung Phản Khúc", "Nỏ Kéo", 
    "Câu Chuyện Diệt Rồng", "Kiếm Lữ Hành", "Bạch Anh Thương", "Tóm Tắt Ma Pháp"
]

WORLD_BOSSES = [
    {"name": "Phong Nguyên Bản", "hp": 75000, "atk": 100, "reward": 200, "file": "phong_nguyen_ban.png"},
    {"name": "Băng Nguyên Bản", "hp": 80000, "atk": 300, "reward": 800, "file": "bang_nguyen_ban.png"},
    {"name": "Cây Cấp Đông", "hp": 85000, "atk": 350, "reward": 800, "file": "cay_cap_dong.png"},
    {"name": "Lôi Nguyên Bản", "hp": 90000, "atk": 450, "reward": 1000, "file": "loi_nguyen_ban.png"},
    {"name": "Người Canh Gác - Sa Ngã", "hp": 95000, "atk": 500, "reward": 1000, "file": "nguoi_canh_gac_sa_nga.png"},
    {"name": "Nham Nguyên Bản", "hp": 100000, "atk": 600, "reward": 1200, "file": "nham_nguyen_ban.png"},
    {"name": "Tinh Linh Nước Trong", "hp": 105000, "atk": 800, "reward": 1500, "file": "tinh_linh_nuoc_trong.png"},
    {"name": "Rồng Đất Cổ Nham", "hp": 110000, "atk": 950, "reward": 1800, "file": "rong_dat_co_nham.png"},
    {"name": "Cây Nổ", "hp": 115000, "atk": 1100, "reward": 2200, "file": "cay_no.png"},
    {"name": "Mãng Xà Di Tích", "hp": 120000, "atk": 1200, "reward": 2500, "file": "mang_xa_di_tich.png"},
    {"name": "Ẩn Sơn Nghê Thú", "hp": 125000, "atk": 1350, "reward": 2800, "file": "an_son_nghe_thu.png"},
    {"name": "Rồng Biển Sâu", "hp": 130000, "atk": 1400, "reward": 3000, "file": "rong_bien_sau.png"}, 
    {"name": "Vua ‍Thú‍ ‍Hoàng Kim‍", "hp": 135000, "atk": 1450, "reward": 3500, "file": "vua_thu_hoang_kim.png"},
    {"name": "Thủy Nguyên Bản", "hp": 140000, "atk": 1500, "reward": 4000, "file": "thuy_nguyen_ban.png"},
    {"name": "Maguu Kenki", "hp": 145000, "atk": 1600, "reward": 4500, "file": "maguu_kenki.png"},
    {"name": "Mô Hình‍ ‍Động Cơ‍ ‍Vĩnh Cửu", "hp": 150000, "atk": 1700, "reward": 5000, "file": "mo_hinh_dong_co_vinh_cuu.png"},
    {"name": "Hỏa Nguyên Bản", "hp": 155000, "atk": 1800, "reward": 5500, "file": "hoa_nguyen_ban.png"},
    {"name": "Thực Thể Sấm Sét", "hp": 160000, "atk": 2000, "reward": 6000, "file": "thuc_the_sam_set.png"},
    {"name": "Nấm Thúy Linh", "hp": 170000, "atk": 2200, "reward": 6500, "file": "nam_thuy_linh.png"},
    {"name": "Cây Cấp Lôi", "hp": 180000, "atk": 2500, "reward": 7000, "file": "cay_cap_loi.png"},
    {"name": "Rồng Điềm Báo Vạn Kiếp", "hp": 200000, "atk": 2800, "reward": 7500, "file": "rong_diem_bao_van_kiep.png"},
    {"name": "Ma Trận Điều Hành Bán Vĩnh Cửu", "hp": 210000, "atk": 3000, "reward": 8000, "file": "ma_tran_dieu_hanh_ban_vinh_cuu.png"},
    {"name": "Thảo Nguyên Bản", "hp": 222222, "atk": 3500, "reward": 9000, "file": "thao_nguyen_ban.png"},
    {"name": "Setekh Wenut", "hp": 240000, "atk": 4000, "reward": 10000, "file": "setekh_wenut.png"},
    {"name": "Kẻ Rửa Tội Tàn Ác", "hp": 250000, "atk": 4500, "reward": 11000, "file": "ke_rua_toi_tan_ac.png"},
    {"name": "Liên Khúc Gió Băng", "hp": 280000, "atk": 5000, "reward": 12000, "file": "lien_khuc_gio_bang.png"},
    {"name": "Hoàng Đế Thép Lửa", "hp": 300000, "atk": 6000, "reward": 13000, "file": "hoang_de_thep_lua.png"},
    {"name": "Robot Nguyên Mẫu Breguet", "hp": 325000, "atk": 7000, "reward": 14000, "file": "robot_nguyen_mau_breguet.png"},
    {"name": "Cá Ngựa Ngọc Trai Ngàn Năm", "hp": 350000, "atk": 8000, "reward": 15000, "file": "ca_ngua_ngoc_trai_ngan_nam.png"},
    {"name": "Nhân Dạng Nước", "hp": 380000, "atk": 9000, "reward": 16000, "file": "nhan_dang_nuoc.png"},
    {"name": "Đốc Quân Ma Tượng", "hp": 400000, "atk": 10000, "reward": 17000, "file": "doc_quan_ma_tuong.png"},
    {"name": "Bạo Chúa Qucusaur Lửa Vàng", "hp": 420000, "atk": 11000, "reward": 18000, "file": "bao_chua_qucusaur_lua_vang.png"},
    {"name": "Sơn Vương Yumkasaur Tham Ăn", "hp": 444444, "atk": 12000, "reward": 20000, "file": "son_vuong_yumkasaur_tham_an.png"},
    {"name": "Cỗ Máy Bí Ẩn - Thiết Bị Cấu Tạo", "hp": 470000, "atk": 13000, "reward": 22000, "file": "co_may_bi_an_thiet_bi_cau_tao.png"},
    {"name": "Gốc Rễ Mô Phỏng U Ám", "hp": 500000, "atk": 14000, "reward": 25000, "file": "goc_re_mo_phong_u_am.png"},
    {"name": "Kẻ Ẩn Tu Ngoại Cảm Lạc Lối", "hp": 525000, "atk": 15000, "reward": 30000, "file": "ke_an_tu_ngoai_cam_lac_loi.png"},
    {"name": "Tượng Rồng Dung Nham", "hp": 550000, "atk": 16000, "reward": 35000, "file": "tuong_rong_dung_nham.png"},
    {"name": "Cỗ Máy Bí Ẩn - Thiết Bị Giám Sát", "hp": 580000, "atk": 17000, "reward": 40000, "file": "co_may_bi_an_thiet_bi_giam_sat.png"},
    {"name": "Bướm Ánh Trăng Bức Xạ", "hp": 600000, "atk": 18000, "reward": 45000, "file": "buom_anh_trang_buc_xa.png"},
    {"name": "Vịt Nắm Đấm", "hp": 620000, "atk": 19000, "reward": 50000, "file": "vit_nam_dan.png"},
    {"name": "Linh Chủ Đêm Sương", "hp": 666666, "atk": 20000, "reward": 60000, "file": "linh_chu_dem_suong.png"},
    {"name": "Chiến Hạm Lục Chiến Hạng Nặng - Pháo Đài Di Động", "hp": 690000, "atk": 21000, "reward": 70000, "file": "chien_ham_luc_chien_hang_nang_phao_dai_di_dong.png"},
    {"name": "Chúa Tể Ác Mộng U Ám", "hp": 750000, "atk": 22000, "reward": 80000, "file": "chua_te_ac_mong_u_am.png"},
    {"name": "Thằn Lằn Ánh Trăng Bức Xạ", "hp": 800000, "atk": 23000, "reward": 90000, "file": "than_lan_anh_trang_buc_xa.png"},
    {"name": "Sư Tử Cánh Lai Ghép", "hp": 900000, "atk": 24000, "reward": 100000, "file": "su_tu_canh_lai_ghep.png"},
    {"name": "Tạo Vật Phái Sinh Bất Diệt", "hp": 2000000, "atk": 25000, "reward": 120000, "file": "tao_vat_phai_sinh_bat_diet.png"}
]

WEEKLY_BOSSES = [
    {"name": "Phong Ma Long Dvalin", "hp": 2000000, "atk": 1500, "reward": 4000, "file": "dvalin.png"},
    {"name": "Sói Bắc Phong Andrius", "hp": 3000000, "atk": 3000, "reward": 6000, "file": "andrius.png"},
    {"name": "Tartaglia", "hp": 4000000, "atk": 4500, "reward": 9000, "file": "tartaglia.png"},
    {"name": "Azhdaha", "hp": 5000000, "atk": 6000, "reward": 12000, "file": "azhdaha.png"},
    {"name": "La Signora", "hp": 8000000, "atk": 9000, "reward": 18000, "file": "la_signora.png"},
    {"name": "Magatsu Mitake Narukami no Mikoto", "hp": 10000000, "atk": 15000, "reward": 30000, "file": "raiden_puppet.png"},
    {"name": "Shouki no Kami Kẻ Lang Thang", "hp": 15000000, "atk": 25000, "reward": 50000, "file": "scaramouche.png"},
    {"name": "Kẻ Thủ Hộ Của Ốc Đảo Apep", "hp": 20000000, "atk": 40000, "reward": 80000, "file": "apep.png"},
    {"name": "Thôn Tinh Kình Ngư", "hp": 25000000, "atk": 65000, "reward": 120000, "file": "narwhal.png"},
    {"name": "Tro Tàn Của Ngọn Lửa Hai Thế Giới - Arlecchino", "hp": 28000000, "atk": 90000, "reward": 200000, "file": "arlecchino.png"},
    {"name": "Chúa Tể Lửa Nguồn Ăn Mòn", "hp": 30000000, "atk": 220000, "reward": 500000, "file": "chua_te_lua_nguon_an_mon.png"},
    {"name": "Ván Cờ Trước Ngưỡng Cửa", "hp": 35000000, "atk": 400000, "reward": 1500000, "file": "van_co_truoc_nguong_cua.png"},
    {"name": "Kẻ Dị Giáo Của Mặt Trăng Giả", "hp": 4000000, "atk": 400000, "reward": 1500000, "file": "dottore.png"},
    {"name": "Đấng Cao Quý Của Tà Đạo", "hp": 70000000, "atk": 400000, "reward": 1500000, "file": "dottore2.png"}
]

# ==========================================
# CÔNG CỤ RENDER GIAO DIỆN CHUẨN
# ==========================================
def generate_battle_ui(boss_name, boss_file, boss_max_hp, boss_current_hp, boss_atk, boss_def, team_data, damage_dealt):
    canvas_w, canvas_h = 800, 650
    img = Image.new('RGB', (canvas_w, canvas_h), (24, 25, 30)) 
    draw = ImageDraw.Draw(img)
    
    font_normal, font_large = load_fonts(18, 28)
    font_small, _ = load_fonts(14, 14)
    font_dmg, _ = load_fonts(20, 20)

    draw.rounded_rectangle([10, 10, canvas_w - 10, canvas_h - 10], radius=20, outline=(255, 215, 0), width=3)

    boss_img_path = find_image(BOSS_PATH, boss_file)
    if boss_img_path:
        try:
            boss_img = Image.open(boss_img_path).convert("RGBA")
            boss_img = ImageOps.fit(boss_img, (360, 200), Image.Resampling.LANCZOS)
            img.paste(boss_img, (220, 30), boss_img)
        except:
            draw.rectangle([220, 30, 580, 230], fill=(60, 62, 66), outline=(100, 100, 100), width=3)
            draw.text((400, 130), f"Boss:\n{boss_name}", fill="white", font=font_large, anchor="mm", align="center")
    else:
        draw.rectangle([220, 30, 580, 230], fill=(60, 62, 66), outline=(100, 100, 100), width=3)
        draw.text((400, 130), f"{boss_name}", fill="white", font=font_large, anchor="mm", align="center")

    hp_ratio = max(0.0, min(boss_current_hp / boss_max_hp, 1.0))
    draw.rounded_rectangle([200, 248, 600, 277], radius=12, fill=(35, 35, 42), outline=(90, 90, 100), width=2)
    if hp_ratio > 0:
        draw.rounded_rectangle([202, 250, 202 + int(396 * hp_ratio), 275], radius=10, fill=(237, 66, 69))
    draw.text((400, 262), f"{boss_name} | HP: {boss_current_hp:,} / {boss_max_hp:,}", fill="white", font=font_normal, anchor="mm")
    
    draw.text((400, 290), f"ATK: {boss_atk:,}   |   DEF: {boss_def:,}", fill=(200, 200, 200), font=font_small, anchor="mm")

    if damage_dealt > 0:
        draw.text((400, 315), f"Sát thương đợt này: {damage_dealt:,}", fill=(255, 215, 0), font=font_dmg, anchor="mm")

    for i, char in enumerate(team_data):
        x_base = i * 200
        filename = f"{char['name'].title()}.png"
        char_img_path = os.path.join(CHAR_PATH, filename)
        
        y_char = 350
        if os.path.exists(char_img_path):
            try:
                char_img = Image.open(char_img_path).convert("RGBA")
                char_img = ImageOps.fit(char_img, (140, 140), Image.Resampling.LANCZOS)
                img.paste(char_img, (x_base + 30, y_char), char_img)
            except:
                draw.rectangle([x_base + 30, y_char, x_base + 170, y_char + 140], fill=(100, 100, 100))
        else:
            draw.rectangle([x_base + 30, y_char, x_base + 170, y_char + 140], fill=(70, 70, 70))
            draw.text((x_base + 100, y_char + 70), "No Image", fill="white", font=font_small, anchor="mm")
            
        draw.text((x_base + 100, y_char + 160), f"Lv.{char['lvl']} {char['name']}", fill="white", font=font_normal, anchor="mm")
        
        draw.rounded_rectangle([x_base + 20, y_char + 180, x_base + 180, y_char + 195], radius=7, fill=(35, 35, 42), outline=(90, 90, 100), width=1)
        draw.rounded_rectangle([x_base + 22, y_char + 182, x_base + 178, y_char + 193], radius=5, fill=(87, 242, 135))
        draw.text((x_base + 100, y_char + 187), f"HP: {char['max_hp']:,}", fill="black", font=font_small, anchor="mm")

        draw.text((x_base + 100, y_char + 207), f"ATK: {char['atk']:,} | DEF: {char['def_stat']:,}", fill=(200, 200, 200), font=font_small, anchor="mm")

        current_xp, needed_xp = char["xp"], char["lvl"] * char["lvl"] * 20
        xp_ratio = min(current_xp / needed_xp, 1.0) if needed_xp > 0 else 1.0
        draw.rounded_rectangle([x_base + 20, y_char + 225, x_base + 180, y_char + 240], radius=7, fill=(35, 35, 42), outline=(90, 90, 100), width=1)
        if xp_ratio > 0:
            draw.rounded_rectangle([x_base + 22, y_char + 227, x_base + 22 + int(156 * xp_ratio), y_char + 238], radius=5, fill=(88, 101, 242))
        draw.text((x_base + 100, y_char + 232), f"EXP: {current_xp}/{needed_xp}", fill="white", font=font_small, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==========================================
# CẤU TRÚC HỆ THỐNG RPG
# ==========================================
class RPG(commands.Cog):
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
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng RPG (RPG)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("PRAGMA busy_timeout = 60000")
            await db.execute('''CREATE TABLE IF NOT EXISTS inventory (guild_id INTEGER, user_id INTEGER, item_name TEXT, rarity TEXT)''')
            await db.execute('''CREATE INDEX IF NOT EXISTS idx_inventory_guild_user ON inventory (guild_id, user_id)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS char_stats (guild_id INTEGER, user_id INTEGER, char_name TEXT, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, UNIQUE(guild_id, user_id, char_name))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS team_setup (guild_id INTEGER, user_id INTEGER, slot1 TEXT, slot2 TEXT, slot3 TEXT, slot4 TEXT, PRIMARY KEY(guild_id, user_id))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS boss_progress (
                guild_id INTEGER, user_id INTEGER, 
                w_index INTEGER DEFAULT 0, w_hp INTEGER DEFAULT -1, 
                wk_index INTEGER DEFAULT 0, wk_hp INTEGER DEFAULT -1,
                PRIMARY KEY(guild_id, user_id)
            )''')
            # Khởi tạo nhanh char_stats cho các nhân vật trong inventory chưa có trong char_stats bằng 1 lệnh SQL duy nhất
            placeholders = ",".join("?" * len(WEAPONS))
            await db.execute(f'''
                INSERT OR IGNORE INTO char_stats (guild_id, user_id, char_name, level, xp)
                SELECT DISTINCT guild_id, user_id, item_name, 1, 0
                FROM inventory
                WHERE item_name NOT IN ({placeholders})
            ''', WEAPONS)
            await db.commit()

    # XỬ LÝ TIỀN TỆ TRỰC TIẾP TRONG RPG ĐỂ ĐỒNG BỘ MULTI-SERVER
    async def get_balance(self, guild_id, user_id):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
            await db.commit()
            cur = await db.execute("SELECT coins FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cur.fetchone()
            return row[0] if row else 0

    async def add_balance(self, guild_id, user_id, amount):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
            await db.execute("UPDATE economy SET coins = coins + ? WHERE guild_id = ? AND user_id = ?", (amount, guild_id, user_id))
            await db.commit()

    async def try_deduct_balance(self, guild_id, user_id, amount) -> bool:
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO economy (guild_id, user_id, coins) VALUES (?, ?, 0)", (guild_id, user_id))
            cur = await db.execute(
                "UPDATE economy SET coins = coins - ? WHERE guild_id = ? AND user_id = ? AND coins >= ?",
                (amount, guild_id, user_id, amount)
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_inventory(self, guild_id, user_id):
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            cursor = await db.execute("SELECT item_name, rarity, COUNT(*) FROM inventory WHERE guild_id = ? AND user_id = ? GROUP BY item_name, rarity", (guild_id, user_id))
            rows = await cursor.fetchall()
            return {row[0].lower(): {"name": row[0], "rarity": row[1], "count": row[2]} for row in rows}

    async def get_team_stats(self, guild_id, user_id):
        inv = await self.get_inventory(guild_id, user_id)
        team_data, total_hp, total_atk, total_def = [], 0, 0, 0
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            cursor = await db.execute("SELECT slot1, slot2, slot3, slot4 FROM team_setup WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            team_row = await cursor.fetchone()
            if not team_row: return None, 0, 0, 0

            for slot in team_row:
                c = await db.execute("SELECT level, xp FROM char_stats WHERE guild_id = ? AND user_id = ? AND char_name = ?", (guild_id, user_id, slot))
                stat = await c.fetchone()
                lvl, xp = stat if stat else (1, 0)
                info = inv.get(slot.lower(), {"rarity": "4 Sao", "count": 1})
                rarity, cons = info["rarity"], info["count"] - 1
                
                if rarity == "5 Sao":
                    base_hp, hp_per_lvl = 3000, 350
                    base_atk, atk_per_lvl = 1500, 200
                    base_def, def_per_lvl = 200, 25
                else:
                    base_hp, hp_per_lvl = 2000, 250
                    base_atk, atk_per_lvl = 1000, 140
                    base_def, def_per_lvl = 120, 18
                    
                char_hp = base_hp + (hp_per_lvl * lvl)
                char_atk = base_atk + (atk_per_lvl * lvl)
                char_def = base_def + (def_per_lvl * lvl)
                
                cons_mult = 1.0 + (0.20 * cons)
                
                max_hp = int(char_hp * cons_mult)
                atk = int(char_atk * cons_mult)
                def_stat = int(char_def * cons_mult)
                
                total_hp += max_hp
                total_atk += atk
                total_def += def_stat
                team_data.append({"name": slot, "lvl": lvl, "xp": xp, "max_hp": max_hp, "atk": atk, "def_stat": def_stat})
        return team_data, total_hp, total_atk, total_def

    @commands.hybrid_command(name="team_set", description="Cài đặt đội hình 4 người. (Ví dụ: f!team_set Hu Tao, Yelan, Zhongli, Furina)")
    async def team_set(self, ctx: commands.Context, *, characters: str):
        char_list = [c.strip().lower() for c in characters.split(',')]
        if len(char_list) != 4:
            return await ctx.send(embed=discord.Embed(description="❌ Hãy nhập chính xác **4 nhân vật**, cách nhau bằng dấu phẩy `,`", color=C_ERROR))
        if len(set(char_list)) != 4:
            return await ctx.send(embed=discord.Embed(description="❌ Không thể xếp 2 nhân vật giống nhau vào cùng một đội!", color=C_ERROR))
        
        inv = await self.get_inventory(ctx.guild.id, ctx.author.id)
        real_names = []
        for c in char_list:
            if c not in inv:
                return await ctx.send(embed=discord.Embed(description=f"❌ Bạn chưa sở hữu **{c.title()}** tại Server này! Hãy quay `f!gacha` để sưu tầm.", color=C_ERROR))
            if inv[c]["name"] in WEAPONS:
                return await ctx.send(embed=discord.Embed(description=f"❌ **{inv[c]['name']}** là vũ khí, không thể xếp vào đội hình!", color=C_ERROR))
            real_names.append(inv[c]["name"])
            
        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR REPLACE INTO team_setup (guild_id, user_id, slot1, slot2, slot3, slot4) VALUES (?, ?, ?, ?, ?, ?)", (ctx.guild.id, ctx.author.id, *real_names))
            await db.commit()

        embed = discord.Embed(
            title="✅ ĐỘI HÌNH ĐÃ SẴN SÀNG!",
            description=(
                "⚔️ Chiến đội của bạn:\n"
                + "\n".join(f"> {i}. **{name}**" for i, name in enumerate(real_names, start=1))
                + "\n\n*Dùng `f!hunt` để xuất kích săn Boss ngay!*"
            ),
            color=C_SUCCESS
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="team", description="Xem đội hình hiện tại (HP, ATK, DEF).")
    async def team(self, ctx: commands.Context):
        team_data, total_hp, total_atk, total_def = await self.get_team_stats(ctx.guild.id, ctx.author.id)
        if not team_data:
            return await ctx.send(embed=discord.Embed(description="❌ Bạn chưa thiết lập đội hình tại Server này! Dùng `f!team_set` trước nhé.", color=C_ERROR))

        embed = discord.Embed(
            title=f"⚔️ ĐỘI HÌNH CỦA {ctx.author.display_name.upper()}",
            color=C_BRAND
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        for char in team_data:
            lvl_bar, _ = make_progress_bar(char['lvl'], 100, 8)
            xp_needed = char['lvl'] * char['lvl'] * 20
            xp_bar, xp_pct = make_progress_bar(char['xp'], xp_needed, 8)
            embed.add_field(
                name=f"⭐ {char['name']}",
                value=(
                    f"{lvl_bar} **Lv.{char['lvl']}**\n"
                    f"❤️ HP: `{char['max_hp']:,}`\n"
                    f"🗡️ ATK: `{char['atk']:,}` | 🛡️ DEF: `{char['def_stat']:,}`\n"
                    f"✨ EXP: `{char['xp']:,}/{xp_needed:,}` {xp_bar} `{xp_pct}%`"
                ),
                inline=True
            )
        embed.add_field(
            name="▬▬▬▬▬ 🔥 TỔNG LỰC CHIẾN 🔥 ▬▬▬▬▬",
            value=f"❤️ Tổng HP: `{total_hp:,}`  |  🗡️ Tổng ATK: `{total_atk:,}`  |  🛡️ Tổng DEF: `{total_def:,}`",
            inline=False
        )
        embed.set_footer(text="✨ FamiBot • Săn Boss để tích lũy EXP cho đội")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="hunt", description="Đánh Boss Thế Giới (Tốn 40 NT, CD: 30s).")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def hunt(self, ctx: commands.Context):
        success = await self.try_deduct_balance(ctx.guild.id, ctx.author.id, 40)
        if not success:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(embed=discord.Embed(description="❌ Đi săn tốn **40 nguyên thạch**! Bạn không đủ tiền tại Server này.", color=C_ERROR))

        team_data, total_hp, total_atk, total_def = await self.get_team_stats(ctx.guild.id, ctx.author.id)
        if not team_data:
            ctx.command.reset_cooldown(ctx)
            # Hoàn lại tiền nếu chưa có đội hình
            await self.add_balance(ctx.guild.id, ctx.author.id, 40)
            return await ctx.send(embed=discord.Embed(description="❌ Bạn chưa cài đội hình! Dùng `f!team_set` trước nhé.", color=C_ERROR))

        await ctx.defer()

        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO boss_progress (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, ctx.author.id))
            await db.commit()
            
            c = await db.execute("SELECT w_index, w_hp FROM boss_progress WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
            w_idx, w_hp = await c.fetchone()

            if w_idx >= len(WORLD_BOSSES): w_idx = len(WORLD_BOSSES) - 1
            boss = WORLD_BOSSES[w_idx]
            
            current_boss_hp = boss["hp"] if w_hp == -1 else w_hp
            boss_atk = boss["atk"]
            boss_def = int(boss["atk"] * 0.8 + (w_idx * 3000))
            
            boss_dmg_reduction = 2000 / (2000 + boss_def)
            team_dmg_reduction = 2000 / (2000 + total_def)
            
            current_team_hp = total_hp
            damage_dealt = 0
            turns_survived = 0
            max_turns = 10 
            is_dead = False

            for turn in range(max_turns):
                turns_survived += 1
                
                actual_team_atk = total_atk * random.uniform(0.9, 1.1)
                turn_dmg = int(actual_team_atk * boss_dmg_reduction)
                damage_dealt += turn_dmg
                current_boss_hp -= turn_dmg
                
                if current_boss_hp <= 0:
                    is_dead = True
                    break
                    
                enrage_mult = 1.5 if current_boss_hp < boss["hp"] * 0.3 else 1.0
                actual_boss_atk = boss_atk * enrage_mult * random.uniform(0.9, 1.2)
                boss_turn_dmg = int(actual_boss_atk * team_dmg_reduction)
                current_team_hp -= boss_turn_dmg
                
                if current_team_hp <= 0:
                    break 

            if is_dead:
                next_idx = min(w_idx + 1, len(WORLD_BOSSES) - 1)
                await db.execute("UPDATE boss_progress SET w_index = ?, w_hp = -1 WHERE guild_id = ? AND user_id = ?", (next_idx, ctx.guild.id, ctx.author.id))
            else:
                await db.execute("UPDATE boss_progress SET w_hp = ? WHERE guild_id = ? AND user_id = ?", (current_boss_hp, ctx.guild.id, ctx.author.id))
            
            gained_xp = (80 + w_idx * 5) if is_dead else (15 + w_idx * 2)
            for char in team_data:
                new_xp, new_lvl = char["xp"] + gained_xp, char["lvl"]
                while new_lvl < 100 and new_xp >= new_lvl * new_lvl * 20:
                    new_xp -= new_lvl * new_lvl * 20
                    new_lvl += 1
                char["lvl"], char["xp"] = new_lvl, new_xp
                await db.execute("""
                    INSERT INTO char_stats (guild_id, user_id, char_name, level, xp)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id, char_name)
                    DO UPDATE SET level = excluded.level, xp = excluded.xp
                """, (ctx.guild.id, ctx.author.id, char["name"], new_lvl, new_xp))
            
            await db.commit()

        display_hp = max(0, int(current_boss_hp))
        image_buffer = await self.bot.loop.run_in_executor(None, generate_battle_ui, boss["name"], boss["file"], boss["hp"], display_hp, boss_atk, boss_def, team_data, damage_dealt)
        file = discord.File(image_buffer, filename="battle_ui.png")
        
        embed = discord.Embed(title=f"⚔️ BOSS THẾ GIỚI • TẦNG {w_idx + 1}")
        embed.set_image(url="attachment://battle_ui.png")
        if is_dead:
            await self.add_balance(ctx.guild.id, ctx.author.id, boss["reward"])
            embed.color = C_SUCCESS
            embed.description = (
                f"🎉 **HẠ GỤC THÀNH CÔNG {boss['name'].upper()}!**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💰 **Phần thưởng:** `+{boss['reward']:,} nguyên thạch`\n"
                f"✨ **Kinh nghiệm đội:** `+{gained_xp:,} XP`\n\n"
                "*➡️ Tiến trình đã chuyển sang Boss tiếp theo!*"
            )
        else:
            embed.color = C_ORANGE
            embed.description = (
                "💥 **RÚT LUI CHIẾN THUẬT**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"⏱️ **Đội bạn cầm cự:** `{turns_survived} hiệp`\n"
                f"✨ **Kinh nghiệm đội:** `+{gained_xp:,} XP`\n\n"
                "*Dùng `f!hunt` sau 30 giây để bào máu tiếp nhé!*"
            )
        embed.set_footer(text=f"✨ FamiBot • Tầng {w_idx + 1}/{len(WORLD_BOSSES)} • 40 nguyên thạch/lượt")

        await ctx.send(file=file, embed=embed)

    @commands.hybrid_command(name="whunt", description="Đánh Boss Tuần (Tốn 3000 NT, CD: 7 Ngày).")
    @commands.cooldown(1, 604800, commands.BucketType.user) 
    async def whunt(self, ctx: commands.Context):
        success = await self.try_deduct_balance(ctx.guild.id, ctx.author.id, 3000)
        if not success:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(embed=discord.Embed(description="❌ Săn Boss Tuần tốn **3000 nguyên thạch**! Bạn không đủ tiền tại Server này.", color=C_ERROR))

        team_data, total_hp, total_atk, total_def = await self.get_team_stats(ctx.guild.id, ctx.author.id)
        if not team_data:
            ctx.command.reset_cooldown(ctx)
            await self.add_balance(ctx.guild.id, ctx.author.id, 3000)
            return await ctx.send(embed=discord.Embed(description="❌ Bạn chưa cài đội hình! Dùng `f!team_set` trước nhé.", color=C_ERROR))

        await ctx.defer()

        async with aiosqlite.connect(self.db_path, timeout=60.0) as db:
            await db.execute("INSERT OR IGNORE INTO boss_progress (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, ctx.author.id))
            await db.commit()
            
            c = await db.execute("SELECT wk_index, wk_hp FROM boss_progress WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
            wk_idx, wk_hp = await c.fetchone()

            if wk_idx >= len(WEEKLY_BOSSES): wk_idx = len(WEEKLY_BOSSES) - 1
            boss = WEEKLY_BOSSES[wk_idx]
            
            current_boss_hp = boss["hp"] if wk_hp == -1 else wk_hp
            boss_atk = boss["atk"]
            boss_def = int(boss["atk"] * 0.5 + (wk_idx * 1500))
            
            boss_dmg_reduction = 2000 / (2000 + boss_def)
            team_dmg_reduction = 2000 / (2000 + total_def)
            
            current_team_hp = total_hp
            damage_dealt = 0
            turns_survived = 0
            max_turns = 10 
            is_dead = False

            weekly_atk_buff = 3.0

            for turn in range(max_turns):
                turns_survived += 1
                
                actual_team_atk = total_atk * random.uniform(1.0, 1.3) * weekly_atk_buff
                turn_dmg = int(actual_team_atk * boss_dmg_reduction)
                damage_dealt += turn_dmg
                current_boss_hp -= turn_dmg
                
                if current_boss_hp <= 0:
                    is_dead = True
                    break
                    
                enrage_mult = 1.5 if current_boss_hp < boss["hp"] * 0.3 else 1.0
                actual_boss_atk = boss_atk * enrage_mult * random.uniform(0.9, 1.2)
                boss_turn_dmg = int(actual_boss_atk * team_dmg_reduction)
                current_team_hp -= boss_turn_dmg
                
                if current_team_hp <= 0:
                    break

            if is_dead:
                next_idx = min(wk_idx + 1, len(WEEKLY_BOSSES) - 1)
                await db.execute("UPDATE boss_progress SET wk_index = ?, wk_hp = -1 WHERE guild_id = ? AND user_id = ?", (next_idx, ctx.guild.id, ctx.author.id))
            else:
                await db.execute("UPDATE boss_progress SET wk_hp = ? WHERE guild_id = ? AND user_id = ?", (current_boss_hp, ctx.guild.id, ctx.author.id))
            
            gained_xp = (200 + wk_idx * 50) if is_dead else (50 + wk_idx * 20)
            for char in team_data:
                new_xp, new_lvl = char["xp"] + gained_xp, char["lvl"]
                while new_lvl < 100 and new_xp >= new_lvl * new_lvl * 20:
                    new_xp -= new_lvl * new_lvl * 20
                    new_lvl += 1
                char["lvl"], char["xp"] = new_lvl, new_xp
                await db.execute("""
                    INSERT INTO char_stats (guild_id, user_id, char_name, level, xp)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id, char_name)
                    DO UPDATE SET level = excluded.level, xp = excluded.xp
                """, (ctx.guild.id, ctx.author.id, char["name"], new_lvl, new_xp))
            
            await db.commit()

        display_hp = max(0, int(current_boss_hp))
        image_buffer = await self.bot.loop.run_in_executor(None, generate_battle_ui, boss["name"], boss["file"], boss["hp"], display_hp, boss_atk, boss_def, team_data, damage_dealt)
        file = discord.File(image_buffer, filename="battle_ui_weekly.png")
        
        embed = discord.Embed(title=f"🔥 BOSS TUẦN CỰC HẠN • TẦNG {wk_idx + 1}")
        embed.set_image(url="attachment://battle_ui_weekly.png")
        if is_dead:
            await self.add_balance(ctx.guild.id, ctx.author.id, boss["reward"])
            embed.color = C_PURPLE
            embed.description = (
                f"🌟 **KỲ TÍCH! ĐÃ HẠ GỤC {boss['name'].upper()}!**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💰 **Phần thưởng khổng lồ:** `+{boss['reward']:,} nguyên thạch`\n"
                f"✨ **Kinh nghiệm đội:** `+{gained_xp:,} XP`\n\n"
                "*➡️ Tiến trình đã chuyển sang Boss Tuần tiếp theo!*"
            )
        else:
            embed.color = C_ERROR
            embed.description = (
                "💥 **GIAO TRANH KẾT THÚC**\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"⏱️ **Đội bạn cầm cự:** `{turns_survived} hiệp`\n"
                f"✨ **Kinh nghiệm đội:** `+{gained_xp:,} XP`\n\n"
                "*Máu Boss được giữ nguyên — hãy quay lại phục thù vào tuần sau nhé!*"
            )
        embed.set_footer(text=f"✨ FamiBot • Tầng {wk_idx + 1}/{len(WEEKLY_BOSSES)} • Hồi chiêu 7 ngày")

        await ctx.send(file=file, embed=embed)

async def setup(bot):
    await bot.add_cog(RPG(bot))