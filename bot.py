import os
import logging

import discord
from discord.ext import tasks
from mcstatus import JavaServer


# Hiện log của discord.py trên Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# =========================
# CONFIG
# =========================

# Token được lấy từ biến môi trường, không lưu trong GitHub.
# Trên Railway tạo Variable:
# DISCORD_TOKEN = token bot Discord của m
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ID channel Discord mà bot sẽ gửi status vào
CHANNEL_ID = 1540967218509258752

# QUAN TRỌNG:
# Chỉ ghi hostname/IP, KHÔNG ghi :26142 ở cuối.
MC_HOST = "sg-node1.fable.host"
MC_PORT = 26142

UPDATE_INTERVAL = 30

# Banner hiển thị trong embed.
BANNER_URL = (
    "https://i.pinimg.com/originals/86/fd/06/"
    "86fd0613c53ca5a61251791377ea6af7.gif"
)

# Dịch vụ lấy ảnh đầu skin theo tên người chơi.
SKIN_HEAD_URL = "https://mc-heads.net/avatar/{name}/64"


# Message embed do bot tự tạo
status_message = None


# =========================
# DISCORD
# =========================

intents = discord.Intents.default()
bot = discord.Client(intents=intents)


# =========================
# MINECRAFT STATUS
# =========================

async def get_server_status():
    try:
        # Địa chỉ cuối cùng sẽ là:
        # sg-node1.fable.host:26142
        server = JavaServer.lookup(f"{MC_HOST}:{MC_PORT}")
        status = await server.async_status()

        players_online = status.players.online or 0
        players_max = status.players.max or 0

        player_names = []

        if status.players.sample:
            player_names = [
                player.name
                for player in status.players.sample
                if player.name
            ]

        return True, players_online, players_max, player_names

    except Exception as error:
        print(
            f"Không thể kiểm tra Minecraft server "
            f"{MC_HOST}:{MC_PORT}"
        )
        print(f"Lỗi: {type(error).__name__}: {error}")
        return False, 0, 0, []


async def create_embeds():
    online, players, maximum, names = await get_server_status()

    if online:
        if names:
            player_list = "\n".join(
                f"• `{name}`"
                for name in names
            )
        else:
            player_list = "`Không có người chơi`"

        embed = discord.Embed(
            title="🟢 Minecraft Server Online",
            description="Server đang hoạt động!",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👥 Players",
            value=f"`{players}/{maximum}`",
            inline=True
        )

        embed.add_field(
            name="🎮 Người chơi",
            value=player_list,
            inline=False
        )

        embed.add_field(
            name="📌 Skin",
            value=(
                "Avatar của người chơi được hiển thị ở các ô bên dưới."
                if names
                else "Chưa có người chơi online."
            ),
            inline=False
        )

    else:
        embed = discord.Embed(
            title="🔴 Minecraft Server Offline",
            description=(
                "Không thể kết nối tới server để lấy status."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="👥 Players",
            value="`0/0`",
            inline=True
        )

    embed.add_field(
        name="🌐 Server",
        value=f"`{MC_HOST}:{MC_PORT}`",
        inline=False
    )

    embed.set_footer(text="Tự động cập nhật mỗi 30 giây")

    # Banner GIF nằm ở cuối embed chính.
    embed.set_image(url=BANNER_URL)

    embeds = [embed]

    # Discord giới hạn 10 embeds/message.
    # Dành 1 embed cho status nên tối đa 9 skin head.
    for name in names[:9]:
        player_embed = discord.Embed(
            title=f"🎮 {name}",
            description="Đang chơi trên server",
            color=discord.Color.blurple()
        )
        player_embed.set_thumbnail(
            url=SKIN_HEAD_URL.format(name=name)
        )
        embeds.append(player_embed)

    return embeds


# =========================
# UPDATE
# =========================

@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_server_status():
    global status_message

    if status_message is None:
        return

    try:
        embeds = await create_embeds()
        await status_message.edit(embeds=embeds)
        print("Đã cập nhật server status")

    except discord.NotFound:
        print("Message status không còn tồn tại.")
        update_server_status.cancel()

    except discord.HTTPException as error:
        print(f"Không thể cập nhật message Discord: {error}")


# =========================
# BOT START
# =========================

@bot.event
async def on_ready():
    global status_message

    print(f"Đăng nhập: {bot.user}")
    print(f"Đang kiểm tra Minecraft: {MC_HOST}:{MC_PORT}")

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print(
            "Không tìm thấy channel. "
            "Kiểm tra CHANNEL_ID và quyền View Channel/Send Messages."
        )
        return

    # Tạo message status đầu tiên
    embeds = await create_embeds()
    status_message = await channel.send(embeds=embeds)

    print("Đã tạo embed status!")

    if not update_server_status.is_running():
        update_server_status.start()


# =========================
# RUN BOT
# =========================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "Thiếu biến môi trường DISCORD_TOKEN. "
        "Hãy thêm DISCORD_TOKEN trong Railway Variables."
    )

print(
    f"Đã nhận DISCORD_TOKEN (độ dài: {len(DISCORD_TOKEN)} ký tự). "
    "Đang kết nối Discord...",
    flush=True
)

try:
    bot.run(DISCORD_TOKEN)
except discord.LoginFailure:
    print(
        "Token Discord không hợp lệ. Hãy copy lại token mới "
        "từ Discord Developer Portal, không thêm dấu ngoặc kép.",
        flush=True
    )
except Exception as error:
    print(
        f"Bot dừng vì lỗi {type(error).__name__}: {error}",
        flush=True
    )
    raise
