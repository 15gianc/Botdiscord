import discord
from discord.ext import commands
import yt_dlp
from discord import FFmpegPCMAudio
import asyncio
from dotenv import load_dotenv
import os

# ────────────────────────────────────────────────
# 1. Carga .env (lo primero)
# ────────────────────────────────────────────────
load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("ERROR: TOKEN no encontrado en .env")

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = (os.getenv("TWITCH_USERNAME") or "").lower().strip()
DISCORD_CHANNEL_ID_STR = os.getenv("DISCORD_NOTIFY_CHANNEL_ID")
WEBHOOK_SECRET_STR = os.getenv("WEBHOOK_SECRET")

if not DISCORD_CHANNEL_ID_STR:
    raise ValueError("ERROR: DISCORD_NOTIFY_CHANNEL_ID no encontrado en .env")
DISCORD_CHANNEL_ID = int(DISCORD_CHANNEL_ID_STR)

if not WEBHOOK_SECRET_STR:
    raise ValueError("ERROR: WEBHOOK_SECRET no encontrado en .env")
WEBHOOK_SECRET = WEBHOOK_SECRET_STR.encode("utf-8")

print("=== VARIABLES CARGADAS ===")
print(f"TOKEN: {TOKEN[:10]}... (ocultado)")
print(f"TWITCH_USERNAME: {TWITCH_USERNAME}")
print(f"DISCORD_CHANNEL_ID: {DISCORD_CHANNEL_ID}")
print("==========================\n")

# ────────────────────────────────────────────────
# 2. Discord Bot
# ────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ────────────────────────────────────────────────
# 3. Música (sin cambios)
# ────────────────────────────────────────────────
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'cookiefile': 'cookies.txt',
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.5"'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

queue = []

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, url: str):
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en un canal de voz!")
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        queue.append(player)

        if not ctx.voice_client.is_playing():
            await play_next(ctx)
        else:
            await ctx.send(f'**Añadido:** {player.title}')

async def play_next(ctx):
    if len(queue) > 0:
        player = queue.pop(0)
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'**Reproduciendo:** {player.title}\n{player.url}')
    else:
        await asyncio.sleep(300)
        if not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()

# Añade aquí skip, stop, queue, pause, resume si los tienes

# ────────────────────────────────────────────────
# 4. Eventos Discord
# ────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'¡Bot conectado! {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_member_join(member):
    welcome_channel_id = 1072214818892824736
    auto_role_name = "Rusticos 🛻"
    banner_url = ""  # pon tu GIF si quieres

    channel = member.guild.get_channel(welcome_channel_id)
    if not channel:
        print("Canal de bienvenida no encontrado")
        return

    role = discord.utils.get(member.guild.roles, name=auto_role_name)
    if role:
        try:
            await member.add_roles(role)
            print(f"Rol '{role.name}' dado a {member.name}")
        except Exception as e:
            print(f"Error dando rol: {e}")

    embed = discord.Embed(
        title="¡BIENVENID@ A RUSTICORD! 🛻",
        description=f"¡Hola {member.mention}! Gracias por unirte a **{member.guild.name}**",
        color=discord.Color.from_rgb(88, 101, 242),
        timestamp=discord.utils.utcnow()
    )

    embed.set_image(url=banner_url)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Ahora somos", value=f"**{len(member.guild.members)}** miembros 🚀", inline=False)
    embed.set_footer(text="¡Diviértete y respeta las reglas!", icon_url=member.guild.icon.url if member.guild.icon else None)

    message = await channel.send(embed=embed)

    member_count = len(member.guild.members)
    for i in range(3, member_count + 1, max(1, (member_count - 3) // 5)):
        embed.set_field_at(0, name="Ahora somos", value=f"**{i}** miembros 🚀", inline=False)
        try:
            await message.edit(embed=embed)
            await asyncio.sleep(0.6)
        except:
            break

    embed.set_field_at(0, name="Ahora somos", value=f"**{member_count}** miembros 🎊", inline=False)
    await message.edit(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send("¡Pong! El bot está funcionando correctamente.")

@bot.command()
async def hola(ctx):
    await ctx.send(f"¡Hola {ctx.author.mention}! ¿Qué tal?")

@bot.command()
async def info(ctx):
    await ctx.send(f"Soy {bot.user.mention}\nCreado por: Giancarlo\nServidores: {len(bot.guilds)}")

# ────────────────────────────────────────────────
# 5. Inicio principal
# ────────────────────────────────────────────────
async def main():
    # Inicia Discord bot
    discord_task = asyncio.create_task(bot.start(TOKEN))

    # Nota: TwitchIO webhook requiere un servidor web, pero como no usas chat, puedes omitirlo o usar un adapter simple
    # Para EventSub puro webhook en v3, TwitchIO maneja el servidor internamente si configuras el adapter
    # Pero para simplicidad, te recomiendo probar primero sin TwitchIO (comenta las líneas de TwitchIO si falla)

    await discord_task

if __name__ == "__main__":
    asyncio.run(main())