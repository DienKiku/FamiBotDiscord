import os
import shutil

# 1. Định nghĩa thư mục nguồn và thư mục clone sạch
SOURCE_DIR = os.getcwd()
CLEAN_DIR = os.path.join(os.path.dirname(SOURCE_DIR), "FamiBotDiscord_Clean")

# Các file/thư mục rác hoặc quá nặng không được phép copy sang
IGNORE_LIST = [
    '.git', '__pycache__', 'venv', '.venv', 'ffmpeg', 
    'ffmpeg.exe', 'ffmpeg-master-latest-win64-gpl', 
    'Lavalink_Server', 'logs', 'data', '.cache', 'firebase_key.json'
]

print(f"🚀 Đang tiến hành tạo bản sao sạch tại: {CLEAN_DIR}")

# 2. Định nghĩa hàm lọc file khi copy
def copy_filter(path, names):
    ignored = []
    for name in names:
        if name in IGNORE_LIST or name.startswith('temp_') or name.endswith('.mp4'):
            ignored.append(name)
    return ignored

# Xóa thư mục clean cũ nếu có
if os.path.exists(CLEAN_DIR):
    shutil.rmtree(CLEAN_DIR)

# Copy toàn bộ dự án sang thư mục mới theo bộ lọc
shutil.copytree(SOURCE_DIR, CLEAN_DIR, ignore=copy_filter)

# 3. Xử lý xóa Key trong file .env.example và config.py ở thư mục mới
def clean_file_content(file_path, replacements):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        with open(file_path, "w", encoding="utf-8") as f:
            for line in lines:
                for target, repo in replacements.items():
                    if target in line:
                        line = repo
                f.write(line)

# Làm sạch file .env.example ở thư mục mới
clean_file_content(
    os.path.join(CLEAN_DIR, ".env.example"), 
    {"DISCORD_TOKEN": "DISCORD_TOKEN=your_discord_token_here\n"}
)

# Làm sạch các dòng chứa Key trong config.py ở thư mục mới
clean_file_content(
    os.path.join(CLEAN_DIR, "config.py"), 
    {
        "GCP_API_KEY": "GCP_API_KEY = 'your_gcp_key_here'\n",
        "GROQ_API_KEY": "GROQ_API_KEY = 'your_groq_key_here'\n",
        "OPENROUTER_API_KEY": "OPENROUTER_API_KEY = 'your_openrouter_key_here'\n"
    }
)

print("✅ Đã tạo xong bản sao sạch hoàn toàn! Bạn có thể vào thư mục 'FamiBotDiscord_Clean' bên ngoài để đẩy lên GitHub.")
