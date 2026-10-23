import asyncio
import logging
import sys
import os

import discord
from discord import app_commands
from discord.ext import commands
from concurrent.futures import ThreadPoolExecutor
from cogs.ticket import TicketView, CloseTicketView

from config import (
    BOT_PREFIX,
    DATABASE_PATH,
    DISCORD_TOKEN,
    LOG_DIR,
    TEST_GUILD_ID,
)
from core.database import Database

def setup_logging():
    log_format = (
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    )

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / "famibot.log",
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers,
    )


class FamiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(BOT_PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )

        # Khởi tạo Database và các Executor ngay từ đầu để các Cog có thể gọi được
        self.database = Database(DATABASE_PATH)
        self.fast_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="fast")
        self.media_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="media")
        self.ready_logged = False

    async def setup_hook(self):
        await self.database.initialize()

        # Đăng ký các View tĩnh cho hệ thống Ticket
        self.add_view(TicketView())
        self.add_view(CloseTicketView())

        # Tự động quét và nạp tất cả extension trong thư mục cogs
        cogs_dir = './cogs'
        if os.path.exists(cogs_dir):
            for filename in os.listdir(cogs_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    extension = f"cogs.{filename[:-3]}"
                    try:
                        await self.load_extension(extension)
                        logging.info("Đã tải extension tự động: %s", extension)
                    except Exception:
                        logging.exception(
                            "Không thể tải extension: %s",
                            extension,
                        )
        else:
            logging.error("Không tìm thấy thư mục cogs tại đường dẫn hiện tại!")

        # Đồng bộ Slash Command
        try:
            if TEST_GUILD_ID:
                guild = discord.Object(id=TEST_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)

                logging.info(
                    "Đã đồng bộ %s slash command vào test server.",
                    len(synced),
                )
            else:
                synced = await self.tree.sync()

                logging.info(
                    "Đã đồng bộ %s slash command toàn cục.",
                    len(synced),
                )
        except app_commands.AppCommandError:
            logging.exception("Lỗi đồng bộ slash command.")
        except discord.HTTPException:
            logging.exception(
                "Discord từ chối đồng bộ slash command."
            )

    async def close(self):
        # Dọn dẹp các luồng chạy ngầm khi tắt Bot
        self.fast_executor.shutdown(wait=False)
        self.media_executor.shutdown(wait=False)
        await super().close()

    async def on_ready(self):
        if self.ready_logged:
            return

        self.ready_logged = True

        logging.info("=" * 45)
        logging.info("Bot đã đăng nhập thành công")
        logging.info("Tên bot: %s", self.user)
        logging.info("ID bot: %s", self.user.id)
        logging.info("Số server: %s", len(self.guilds))
        logging.info("=" * 45)


bot = FamiBot()


@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, "on_error"):
        return

    error = getattr(error, "original", error)

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("⚠️ Lệnh này không sử dụng được trong tin nhắn riêng.")
        return

    if isinstance(error, commands.MissingPermissions):
        permissions = ", ".join(error.missing_permissions)

        await ctx.send(
            "⛔ Bạn thiếu quyền để sử dụng lệnh này.\n"
            f"Quyền còn thiếu: `{permissions}`"
        )
        return

    if isinstance(error, commands.BotMissingPermissions):
        permissions = ", ".join(error.missing_permissions)

        await ctx.send(
            "⛔ Bot thiếu quyền để thực hiện thao tác này.\n"
            f"Quyền còn thiếu: `{permissions}`"
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"⚠️ Bạn chưa nhập đủ tham số: `{error.param.name}`."
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(
            "⚠️ Tham số không hợp lệ. "
            "Hãy kiểm tra thành viên, số lượng hoặc cú pháp lệnh."
        )
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"⏳ Hãy thử lại sau {error.retry_after:.1f} giây."
        )
        return

    logging.exception(
        "Lỗi chưa xử lý tại lệnh %s",
        getattr(ctx.command, "qualified_name", "không xác định"),
        exc_info=error,
    )

    await ctx.send(
        "❌ Đã xảy ra lỗi khi xử lý lệnh. "
        "Chi tiết đã được lưu trong `logs/famibot.log`."
    )


async def main():
    setup_logging()

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot đã được dừng.")