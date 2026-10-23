# FamiBotDiscord 🤖

Một bot Discord đa chức năng hỗ trợ phát nhạc chất lượng cao, tích hợp trí tuệ nhân tạo (AI) và quản lý hệ thống dữ liệu thông qua Firebase. Dự án được xây dựng hoàn toàn bằng ngôn ngữ Python sử dụng thư viện `discord.py`.

## ✨ Tính năng nổi bật

*   **🎵 Hệ thống nhạc chất lượng cao:** Sử dụng **Lavalink Server** và thư viện `wavelink` để mang lại trải nghiệm nghe nhạc mượt mà, hỗ trợ các lệnh cơ bản đến nâng cao (play, stop, skip, queue, fixlag...).
*   **🤖 Tích hợp Trí tuệ nhân tạo (AI):** Hỗ trợ tương tác thông minh và xử lý ngôn ngữ tự nhiên thông qua các mô hình AI tiên tiến từ **Groq** và **OpenRouter**.
*   **🗄️ Lưu trữ dữ liệu mạnh mẽ:** Kết nối và đồng bộ hóa cấu hình, dữ liệu người dùng thời gian thực với **Google Firebase Realtime Database / Firestore**.

## 🛠️ Công nghệ sử dụng

*   **Ngôn ngữ chính:** Python 3.10+
*   **Thư viện Discord:** `discord.py` (v2.x)
*   **Kết nối Nhạc:** `wavelink` & `Lavalink Server`
*   **Xử lý âm thanh:** `ffmpeg`
*   **Database:** `firebase-admin`

---

## 🚀 Hướng dẫn cài đặt và chạy Bot

### 1. Yêu cầu hệ thống
*   Đã cài đặt **Python 3.10** trở lên.
*   Đã cài đặt **Java (JDK 17+)** để chạy môi trường Lavalink Server (nếu sử dụng tính năng nhạc).

### 2. Tải mã nguồn dự án
```bash
git clone https://github.com/DienKiku/FamiBotDiscord.git
cd FamiBotDiscord
```

### 3. Cài đặt môi trường ảo và thư viện
Nên sử dụng môi trường ảo (`venv`) để tránh xung đột thư viện hệ thống:
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Trên Mac/Linux:
source venv/bin/activate

# Cài đặt các thư viện bắt buộc
pip install -r requirements.txt
```

### 4. Cấu hình biến môi trường (Bảo mật)
Dự án sử dụng file `.env` để bảo mật toàn bộ Token và API Key. 

1. Tạo một file tên là `.env` ở thư mục gốc của dự án (dựa trên file mẫu `.env.example`).
2. Điền đầy đủ các thông tin Key thực tế của bạn vào bên trong:

```env
DISCORD_TOKEN=điền_token_bot_discord_của_bạn
GCP_API_KEY=điền_google_cloud_api_key_của_bạn
GROQ_API_KEY=điền_groq_api_key_của_bạn
OPENROUTER_API_KEY=điền_openrouter_api_key_của_bạn
```

> ⚠️ **CẢNH BÁO BẢO MẬT:** Tuyệt đối không bao giờ được chia sẻ hoặc đẩy file `.env` và file cấu hình `firebase_key.json` lên GitHub. Chúng đã được chặn tự động trong file `.gitignore`.

### 5. Khởi chạy Bot
Sau khi cấu hình đầy đủ thông tin bí mật, bạn chạy lệnh sau để khởi động Bot:
```bash
python main.py
```

---

## 📂 Cấu trúc thư mục dự án sơ lược

```text
FamiBotDiscord/
├── cogs/               # Nơi chứa các module tính năng riêng biệt (Music, AI, Admin...)
├── config.py           # File đọc cấu hình hệ thống và quản lý các biến môi trường
├── main.py             # File khởi chạy chính của Bot Discord
├── .gitignore          # Cấu hình bỏ qua các tệp tin rác và tệp tin bảo mật khi đẩy lên GitHub
├── .env.example        # File cấu hình mẫu cấu trúc các API Key
└── requirements.txt    # Danh sách các thư viện Python cần cài đặt
```

## 📝 Bản quyền & Đóng góp
Dự án được phát triển bởi [DienKiku](https://github.com/DienKiku). Mọi ý kiến đóng góp hoặc báo lỗi vui lòng mở mục **Issues** trên kho lưu trữ GitHub của dự án.
