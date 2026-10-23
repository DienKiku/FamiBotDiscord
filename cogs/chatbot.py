import discord
from discord.ext import commands
from google import genai
from google.genai import types
from openai import AsyncOpenAI
import json
import os
import asyncio
from config import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY

# ==========================================
# 🎨 BẢNG MÀU THƯƠNG HIỆU FAMIBOT
# ==========================================
C_BRAND = discord.Color.from_rgb(88, 101, 242)
C_SUCCESS = discord.Color.from_rgb(87, 242, 135)
C_WARN = discord.Color.from_rgb(254, 231, 92)
C_ERROR = discord.Color.from_rgb(237, 66, 69)

GEMINI_TIMEOUT = 25
GROQ_OPENROUTER_TIMEOUT = 30


class ChatBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.data_dir = "data"
        self.history_file = os.path.join(self.data_dir, "chat_history.json")
        self.max_history = 3
        # ✅ Lock chống race-condition khi nhiều user gửi /ask hoặc /reset cùng lúc
        self._history_lock = asyncio.Lock()

        # ==========================================
        # 🌟 TỪ ĐIỂN MÔ HÌNH (GIỮ NGUYÊN 100% DANH SÁCH)
        # ==========================================
        self.gemini_models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3.1-flash-lite"
        ]

        self.groq_models = [
            "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b", "llama-3.1-8b-instant", "allam-2-7b",
            "groq/compound", "groq/compound-mini",
            "openai/gpt-oss-safeguard-20b", "meta-llama/llama-prompt-guard-2-86m", "meta-llama/llama-prompt-guard-2-22m"
        ]

        self.openrouter_models = [
            "nvidia/nemotron-3-ultra:free",
            "nvidia/nemotron-3-super:free",
            "google/gemma-4-31b:free",
            "google/gemma-4-26b-a4b:free",
            "nvidia/nemotron-3.5-lightning:free",
            "nvidia/nemotron-3-nano-omni:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "nvidia/nemotron-nano-12b-2-vl:free",
            "nvidia/nemotron-nano-9b-v2:free",
            "openai/gpt-oss-20b:free",
            "dots-studio/dots3-note-preview:free",
            "liquid/lfm2.5-2.6b:free",
            "poolside/laguna-s-2.1:free",
            "poolside/laguna-xs-2.1:free",
            "cohere/north-mini-code:free",
            "nvidia/nemotron-3.5-content-safety:free",
            "nvidia/nemotron-3-embed-1b:free",
            "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
            "nvidia/llama-nemotron-embed-vl-1b-v2:free",
            "deepgram/flux-tts:free",
            "fish-audio/s2.1-pro-free:free"
        ]

        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        self.groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        self.openrouter_client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    # =========================================================
    # 🛡️ GÁC CỔNG IGNORE: ÁP DỤNG CHO TOÀN BỘ LỆNH TRONG FILE
    # =========================================================
    async def cog_check(self, ctx: commands.Context):
        if hasattr(self.bot, "get_ignored_channels_cached"):
            ignored = await self.bot.get_ignored_channels_cached()
            cid = str(ctx.channel.id)
            if cid in ignored and ("all" in ignored[cid] or "chat" in ignored[cid]):
                embed = discord.Embed(description="🚫 Kênh này đã bị quản trị viên tắt tính năng Chatbot (Chatbot)!", color=C_ERROR)
                try: 
                    await ctx.send(embed=embed, ephemeral=True, delete_after=5)
                except: 
                    pass
                return False # Trả về False -> Hủy bỏ lệnh lập tức
        return True # Trả về True -> Cho phép lệnh chạy bình thường
    # =========================================================

    def get_executor(self):
        # ✅ Dùng executor riêng (nếu main.py đã khai báo bot.fast_executor) để không chiếm
        # chung thread pool với việc tải video nặng của media_embed.py
        return getattr(self.bot, "fast_executor", None)

    # ---------- Các hàm ĐỌC/GHI file (chạy trong executor) ----------
    def _load_history_sync(self, user_id):
        with open(self.history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get(str(user_id), [])

    def _save_history_sync(self, user_id, history):
        with open(self.history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if len(history) > self.max_history * 2:
            history = history[-(self.max_history * 2):]
        data[str(user_id)] = history
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _delete_history_sync(self, user_id):
        with open(self.history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        existed = user_id in data
        if existed:
            del data[user_id]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        return existed

    # ---------- Wrapper ASYNC an toàn (không block + không race) ----------
    async def load_history(self, user_id):
        async with self._history_lock:
            return await self.bot.loop.run_in_executor(self.get_executor(), self._load_history_sync, user_id)

    async def save_history(self, user_id, history):
        async with self._history_lock:
            await self.bot.loop.run_in_executor(self.get_executor(), self._save_history_sync, user_id, history)

    async def delete_history(self, user_id):
        async with self._history_lock:
            return await self.bot.loop.run_in_executor(self.get_executor(), self._delete_history_sync, user_id)

    @commands.hybrid_command(name="ask", description="Hỏi FamiBot (Quét toàn bộ Tier List AI).")
    async def ask(self, ctx: commands.Context, *, question: str):
        async with ctx.typing():
            user_id = str(ctx.author.id)
            universal_history = await self.load_history(user_id)

            answer = ""
            provider_used = ""
            success = False

            # ==========================================
            # 🟢 TẦNG 1: GEMINI — chạy trong executor để KHÔNG block event loop
            # ==========================================
            gemini_history = []
            for msg in universal_history:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

            for g_model in self.gemini_models:
                try:
                    def _sync_call(model=g_model, history=gemini_history):
                        chat = self.gemini_client.chats.create(
                            model=model,
                            history=history,
                            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                        )
                        return chat.send_message(question)

                    response = await asyncio.wait_for(
                        self.bot.loop.run_in_executor(self.get_executor(), _sync_call),
                        timeout=GEMINI_TIMEOUT
                    )
                    answer = response.text
                    provider_used = f"✨ Gemini ({g_model})"
                    success = True
                    break
                except asyncio.TimeoutError:
                    print(f"⏱️ [Gemini {g_model} quá thời gian chờ] Thử model tiếp theo...")
                    continue
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg:
                        print("⚠️ [API Key Gemini đã hết lượt (429)]. Đang chuyển thẳng sang Groq...")
                        break
                    continue

            # ==========================================
            # 🟡 TẦNG 2: GROQ CLOUD (client async, có thêm timeout an toàn)
            # ==========================================
            if not success:
                groq_messages = [{"role": "system", "content": "Bạn là FamiBot, trợ lý ảo thông minh. Hãy trả lời tiếng Việt."}]
                for msg in universal_history:
                    groq_messages.append({"role": msg["role"], "content": msg["content"]})
                groq_messages.append({"role": "user", "content": question})

                for gr_model in self.groq_models:
                    try:
                        groq_response = await asyncio.wait_for(
                            self.groq_client.chat.completions.create(
                                model=gr_model,
                                messages=groq_messages,
                                max_tokens=2000
                            ),
                            timeout=GROQ_OPENROUTER_TIMEOUT
                        )
                        answer = groq_response.choices[0].message.content
                        provider_used = f"⚡ Groq ({gr_model})"
                        success = True
                        break
                    except Exception:
                        continue

            # ==========================================
            # 🔴 TẦNG 3: OPENROUTER
            # ==========================================
            if not success:
                try:
                    openrouter_messages = [{"role": "system", "content": "Bạn là FamiBot, trợ lý ảo thông minh. Hãy trả lời tiếng Việt."}]
                    for msg in universal_history:
                        openrouter_messages.append({"role": msg["role"], "content": msg["content"]})
                    openrouter_messages.append({"role": "user", "content": question})

                    openrouter_response = await asyncio.wait_for(
                        self.openrouter_client.chat.completions.create(
                            model=self.openrouter_models[0],
                            messages=openrouter_messages,
                            max_tokens=2000,
                            extra_body={
                                "route": "fallback",
                                "models": self.openrouter_models[1:]
                            }
                        ),
                        timeout=GROQ_OPENROUTER_TIMEOUT
                    )
                    answer = openrouter_response.choices[0].message.content
                    used_model = getattr(openrouter_response, "model", "OpenRouter Free")
                    provider_used = f"🌐 OpenRouter ({used_model})"
                    success = True

                except Exception as openrouter_err:
                    print(f"[LỖI NGHIÊM TRỌNG] Toàn bộ hệ thống AI đều sập: {openrouter_err}")
                    await ctx.send(embed=discord.Embed(
                        title="❌ HỆ THỐNG AI QUÁ TẢI",
                        description="Cả 43 mô hình AI đều đang quá tải hoặc mất mạng.\nBạn hãy thử lại sau ít phút nhé! 🙏",
                        color=C_ERROR
                    ))
                    return

            # ==========================================
            # 💾 LƯU LỊCH SỬ (không block, không race)
            # ==========================================
            universal_history.append({"role": "user", "content": question})
            universal_history.append({"role": "assistant", "content": answer})
            await self.save_history(user_id, universal_history)

            if len(answer) <= 3900:
                question_display = question if len(question) <= 200 else question[:197] + "..."
                embed = discord.Embed(description=answer, color=C_BRAND)
                embed.set_author(name=f"❓ {question_display}", icon_url=ctx.author.display_avatar.url)
                embed.set_footer(text=f"🧠 Não bộ: {provider_used}")
                embed.timestamp = discord.utils.utcnow()
                await ctx.send(embed=embed)
            else:
                final_message = f"{answer}\n\n`Mạng lưới: {provider_used}`"
                for i in range(0, len(final_message), 2000):
                    await ctx.send(final_message[i:i + 2000])

    @commands.hybrid_command(name="reset", description="Xóa trí nhớ của bot đối với bạn.")
    async def reset(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        existed = await self.delete_history(user_id)

        if existed:
            await ctx.send(embed=discord.Embed(
                title="🧠 ĐÃ XÓA TRÍ NHỚ",
                description=f"{ctx.author.mention}, toàn bộ ký ức của mình về bạn đã bay màu sạch sẽ! ✨",
                color=C_SUCCESS
            ))
        else:
            await ctx.send(embed=discord.Embed(
                description="🤔 Mình đã lưu ký ức gì về bạn đâu mà xóa!",
                color=C_WARN
            ))


async def setup(bot):
    await bot.add_cog(ChatBot(bot))
