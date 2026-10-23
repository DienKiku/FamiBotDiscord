import discord
from discord.ext import commands, tasks
import aiosqlite
import firebase_admin
from firebase_admin import credentials, db
import os
import logging
import json
import time

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_ERROR = discord.Color.from_rgb(237, 66, 69)

class FirebaseSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = getattr(bot.database, "database_path", os.path.join("data", "famibot.db"))
        
        self.cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebase_key.json")
        self.firebase_url = "https://weather-station-504bc-default-rtdb.asia-southeast1.firebasedatabase.app"
        
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(self.cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.firebase_url
                })
                logging.info("🔥 Đã kết nối thành công tới Firebase Realtime Database!")
            except Exception as e:
                logging.error(f"❌ Lỗi khởi tạo Firebase: {e}")

    async def cog_load(self):
        # Thiết lập bảng Metadata và cấy Triggers trước khi chạy chu kỳ đồng bộ
        await self.setup_db_and_triggers()
        self.sync_to_firebase.start()

    async def cog_unload(self):
        self.sync_to_firebase.cancel()

    # ==========================================
    # LOGIC XỬ LÝ METADATA & TRIGGERS (VERSIONING)
    # ==========================================
    async def setup_db_and_triggers(self):
        """Khởi tạo bảng metadata và tạo Trigger tự động cập nhật thời gian cho mọi bảng"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        async with aiosqlite.connect(self.db_path, timeout=60.0) as sqlite_db:
            await sqlite_db.execute("PRAGMA busy_timeout = 60000")
            # 1. Tạo bảng lưu metadata và set mặc định
            await sqlite_db.execute("CREATE TABLE IF NOT EXISTS sync_metadata (id INTEGER PRIMARY KEY, last_updated REAL)")
            await sqlite_db.execute("INSERT OR IGNORE INTO sync_metadata (id, last_updated) VALUES (1, 0)")
            
            # 2. Quét tất cả các bảng hiện có (Bỏ qua bảng hệ thống và bảng metadata)
            cur = await sqlite_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'sync_metadata'")
            tables = [row[0] for row in await cur.fetchall()]
            
            # 3. Tạo trigger chặn mọi biến động dữ liệu để tự động nhảy timestamp
            for table in tables:
                for action in ['INSERT', 'UPDATE', 'DELETE']:
                    trigger_name = f"trg_update_time_{table}_{action}"
                    await sqlite_db.execute(f"""
                        CREATE TRIGGER IF NOT EXISTS {trigger_name}
                        AFTER {action} ON "{table}"
                        BEGIN
                            UPDATE sync_metadata 
                            SET last_updated = (julianday('now') - 2440587.5)*86400.0 
                            WHERE id = 1;
                        END;
                    """)
            await sqlite_db.commit()

    async def remove_all_triggers(self):
        """Xóa toàn bộ trigger trước khi Pull Data để tránh bị kích hoạt timestamp ảo khi Insert"""
        if not os.path.exists(self.db_path): 
            return
            
        async with aiosqlite.connect(self.db_path, timeout=60.0) as sqlite_db:
            cur = await sqlite_db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_update_time_%'")
            triggers = [row[0] for row in await cur.fetchall()]
            for trg in triggers:
                await sqlite_db.execute(f"DROP TRIGGER IF EXISTS {trg}")
            await sqlite_db.commit()

    async def get_local_time(self):
        """Đọc thời gian cập nhật nội bộ thực sự của CSDL"""
        if not os.path.exists(self.db_path): return 0.0
        async with aiosqlite.connect(self.db_path, timeout=60.0) as sqlite_db:
            cur = await sqlite_db.execute("SELECT last_updated FROM sync_metadata WHERE id = 1")
            row = await cur.fetchone()
            return row[0] if row else 0.0

    async def set_local_time(self, timestamp):
        """Ép thời gian cập nhật nội bộ (Dùng khi forcesync hoặc sau khi khôi phục)"""
        async with aiosqlite.connect(self.db_path, timeout=60.0) as sqlite_db:
            await sqlite_db.execute("UPDATE sync_metadata SET last_updated = ? WHERE id = 1", (timestamp,))
            await sqlite_db.commit()


    # ==========================================
    # CÁC HÀM XỬ LÝ LÕI
    # ==========================================
    async def fetch_all_data(self):
        """Hàm quét và đóng gói bảng (Loại trừ sync_metadata để không đẩy rác lên Cloud)"""
        backup_data = {}
        if not os.path.exists(self.db_path):
            return backup_data

        async with aiosqlite.connect(self.db_path, timeout=60.0) as sqlite_db:
            cur = await sqlite_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'sync_metadata'")
            tables = [row[0] for row in await cur.fetchall()]

            for table in tables:
                sqlite_db.row_factory = aiosqlite.Row
                cursor = await sqlite_db.execute(f"SELECT * FROM {table}")
                rows = await cursor.fetchall()
                backup_data[table] = [dict(row) for row in rows]
                
        return backup_data

    async def restore_from_firebase(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        ref = db.reference('famibot_data')
        data = await self.bot.loop.run_in_executor(None, ref.get)

        if not data or not isinstance(data, dict):
            logging.warning("⚠️ Không tìm thấy dữ liệu hợp lệ trên Firebase.")
            return False, "Không có dữ liệu trên Firebase để khôi phục."

        # CỰC KỲ QUAN TRỌNG: Gỡ bỏ Trigger tự động nhảy giờ trước khi ghi đè data
        await self.remove_all_triggers()

        async with aiosqlite.connect(self.db_path, timeout=60.0) as sqlite_db:
            for table_name, rows in data.items():
                if not rows: continue

                if isinstance(rows, dict): row_list = list(rows.values())
                else: row_list = rows

                row_list = [r for r in row_list if r and isinstance(r, dict)]
                if not row_list: continue

                columns = list(row_list[0].keys())

                cur = await sqlite_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                table_exists = await cur.fetchone()

                if not table_exists:
                    cols_def = ", ".join([f'"{col}" TEXT' for col in columns])
                    await sqlite_db.execute(f'CREATE TABLE "{table_name}" ({cols_def})')
                    logging.info(f"🛠️ Đã tạo bảng mới: {table_name}")
                else:
                    cur = await sqlite_db.execute(f'PRAGMA table_info("{table_name}")')
                    existing_cols_info = await cur.fetchall()
                    existing_cols = [col[1] for col in existing_cols_info]
                    for col in columns:
                        if col not in existing_cols:
                            await sqlite_db.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT')
                            logging.info(f"🛠️ Đã thêm cột '{col}' vào bảng '{table_name}'")

                cols_str = ", ".join(f'"{col}"' for col in columns)
                placeholders = ", ".join(["?"] * len(columns))
                query = f'INSERT OR REPLACE INTO "{table_name}" ({cols_str}) VALUES ({placeholders})'

                for row in row_list:
                    values = [row.get(col) for col in columns]
                    await sqlite_db.execute(query, values)

            await sqlite_db.commit()

        # --- KHÔI PHỤC FILE JSON TỪ FIREBASE ---
        json_ref = db.reference('famibot_json')
        json_data = await self.bot.loop.run_in_executor(None, json_ref.get)
        if json_data and isinstance(json_data, dict):
            ignored_channels = json_data.get("ignored_channels")
            if ignored_channels is not None:
                os.makedirs("data", exist_ok=True)
                with open(os.path.join("data", "ignored_channels.json"), 'w', encoding='utf-8') as f:
                    json.dump(ignored_channels, f, indent=4)
                if hasattr(self.bot, "reload_ignored_channels"):
                    await self.bot.reload_ignored_channels()
        # ---------------------------------------    

        # 1. Kéo thời gian thực từ Cloud xuống
        meta_ref = db.reference('famibot_metadata/last_updated')
        cloud_time = await self.bot.loop.run_in_executor(None, meta_ref.get) or time.time()
        
        # 2. Cập nhật lại thời gian local khớp hoàn toàn với Cloud (đồng bộ 2 chiều)
        await self.set_local_time(cloud_time)
        
        # 3. Kích hoạt lại Trigger theo dõi biến động data
        await self.setup_db_and_triggers()

        logging.info("✅ Đã khôi phục dữ liệu từ Firebase về SQLite thành công!")
        return True, "Khôi phục dữ liệu và cấu trúc bảng thành công!"

    # ==========================================
    # CHU KỲ ĐỒNG BỘ: TỰ ĐỘNG CHẠY MỖI 2 GIỜ
    # ==========================================
    @tasks.loop(hours=2)
    async def sync_to_firebase(self):
        logging.info("⏳ Bắt đầu tiến trình kiểm tra và đồng bộ dữ liệu...")
        try:
            if not os.path.exists(self.db_path):
                logging.info("⚠️ Không có DB cục bộ, tiến hành khôi phục từ Cloud...")
                await self.restore_from_firebase()
                return

            # LOẠI BỎ os.path.getmtime - SỬ DỤNG VERION TỪ DB
            local_time = await self.get_local_time()
            
            meta_ref = db.reference('famibot_metadata/last_updated')
            cloud_time = await self.bot.loop.run_in_executor(None, meta_ref.get) or 0

            if cloud_time > local_time + 5:
                logging.info("☁️ Dữ liệu Cloud mới hơn! Tự động kéo về máy (Pull)...")
                await self.restore_from_firebase()

            else:
                logging.info("💻 Dữ liệu Local mới hơn. Tự động đẩy lên Cloud (Push)...")
                backup_data = await self.fetch_all_data()
                if not backup_data: return
                
                ref = db.reference('famibot_data')
                await self.bot.loop.run_in_executor(None, ref.set, backup_data)

                # ĐẨY FILE JSON
                ignored_path = os.path.join("data", "ignored_channels.json")
                if os.path.exists(ignored_path):
                    with open(ignored_path, 'r', encoding='utf-8') as f:
                        ignored_data = json.load(f)
                    json_ref = db.reference('famibot_json')
                    await self.bot.loop.run_in_executor(None, json_ref.set, {"ignored_channels": ignored_data})
                
                # Chốt timestamp: Local vừa đẩy lên nên sẽ lấy thời gian nội bộ hiện tại đắp lên Cloud
                new_local_time = await self.get_local_time()
                if new_local_time == 0: new_local_time = time.time()
                await self.bot.loop.run_in_executor(None, meta_ref.set, new_local_time)
                
                logging.info("✅ Đã đẩy (Upload) xong toàn bộ dữ liệu lên Firebase!")

        except Exception as e:
            logging.error(f"❌ Lỗi tiến trình đồng bộ: {e}")

    @sync_to_firebase.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()

    # ==========================================
    # CÁC LỆNH ĐIỀU KHIỂN THỦ CÔNG
    # ==========================================
    @commands.hybrid_command(name="forcesync", description="[Admin] Ép đồng bộ (đẩy) CSDL lên Firebase ngay lập tức.")
    @commands.is_owner()
    async def forcesync(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        try:
            backup_data = await self.fetch_all_data()
            if not backup_data:
                return await ctx.send(embed=discord.Embed(description="❌ Không tìm thấy file dữ liệu CSDL để đồng bộ.", color=C_ERROR))
            
            ref = db.reference('famibot_data')
            await self.bot.loop.run_in_executor(None, ref.set, backup_data)
            
            ignored_path = os.path.join("data", "ignored_channels.json")
            if os.path.exists(ignored_path):
                with open(ignored_path, 'r', encoding='utf-8') as f:
                    ignored_data = json.load(f)
                json_ref = db.reference('famibot_json')
                await self.bot.loop.run_in_executor(None, json_ref.set, {"ignored_channels": ignored_data})

            # Ép cập nhật giờ cho cả máy tính và Firebase
            new_ts = time.time()
            await self.set_local_time(new_ts)
            meta_ref = db.reference('famibot_metadata/last_updated')
            await self.bot.loop.run_in_executor(None, meta_ref.set, new_ts)
            
            await ctx.send(embed=discord.Embed(description="✅ Đã đẩy (Upload) toàn bộ dữ liệu lên Firebase thành công!", color=C_SUCCESS))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi đồng bộ: {e}", color=C_ERROR))

    @commands.hybrid_command(name="pullsync", description="[Admin] Tải (kéo) và khôi phục CSDL từ Firebase về máy.")
    @commands.is_owner()
    async def pullsync(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        try:
            success, message = await self.restore_from_firebase()
            if success:
                await ctx.send(embed=discord.Embed(description=f"✅ {message}", color=C_SUCCESS))
            else:
                await ctx.send(embed=discord.Embed(description=f"⚠️ {message}", color=C_ERROR))
        except Exception as e:
            logging.error(f"❌ Lỗi khi kéo dữ liệu Firebase: {e}")
            await ctx.send(embed=discord.Embed(description=f"❌ Lỗi: {e}", color=C_ERROR))

async def setup(bot):
    await bot.add_cog(FirebaseSync(bot))