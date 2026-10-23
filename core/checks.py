import discord
from discord.ext import commands


def validate_moderation_target(
    ctx: commands.Context,
    member: discord.Member,
):
    if ctx.guild is None:
        return False, "⚠️ Lệnh này chỉ sử dụng được trong server."

    if member == ctx.author:
        return False, "⚠️ Bạn không thể thực hiện lệnh này với chính mình."

    if member == ctx.guild.owner:
        return False, "⚠️ Không thể thực hiện lệnh này với chủ server."

    if member == ctx.guild.me:
        return False, "⚠️ Bạn không thể dùng lệnh này với bot."

    if (
        ctx.author != ctx.guild.owner
        and member.top_role >= ctx.author.top_role
    ):
        return (
            False,
            "⚠️ Bạn không thể quản lý thành viên có role "
            "bằng hoặc cao hơn role của mình.",
        )

    if member.top_role >= ctx.guild.me.top_role:
        return (
            False,
            "⚠️ Role của bot phải nằm cao hơn role của thành viên mục tiêu.",
        )

    return True, None