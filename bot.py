import discord
from discord.ext import commands
import yt_dlp
from discord import FFmpegPCMAudio
import asyncio
from dotenv import load_dotenv
import os
# Activar los intents necesarios (MUY importante)
intents = discord.Intents.default()
intents.message_content = True   # Permite leer el contenido de mensajes y comandos con prefijo

# Crear el bot con prefijo "!"
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuración de yt-dlp (para descargar solo audio)
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 can cause issues
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
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
            # Es una playlist → tomamos el primer video
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Cola de canciones (para reproducir una tras otra)
queue = []

# Comando !play <url o búsqueda>
@bot.command(name='play', aliases=['p'])
async def play(ctx, *, url: str):
    """Reproduce una canción o la añade a la cola"""
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en un canal de voz para usar este comando!")
        return

    voice_channel = ctx.author.voice.channel

    # Conectar si no estamos conectados
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
            await ctx.send(f'**Añadido a la cola:** {player.title}')

async def play_next(ctx):
    """Reproduce la siguiente canción de la cola"""
    if len(queue) > 0:
        player = queue.pop(0)
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'**Reproduciendo:** {player.title}\n{player.url}')
    else:
        # Si la cola está vacía, desconectar después de 5 min de inactividad (opcional)
        await asyncio.sleep(300)
        if not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()

# Comando !skip
@bot.command(name='skip')
async def skip(ctx):
    """Salta la canción actual"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("**Canción saltada!**")
        await play_next(ctx)
    else:
        await ctx.send("No hay nada reproduciéndose.")

# Comando !stop
@bot.command(name='stop')
async def stop(ctx):
    """Detiene la música y limpia la cola"""
    if ctx.voice_client:
        queue.clear()
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("**Música detenida y desconectado.**")
    else:
        await ctx.send("No estoy en un canal de voz.")

# Comando !queue o !q (ver cola)
@bot.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    """Muestra la cola de canciones"""
    if len(queue) == 0:
        await ctx.send("La cola está vacía.")
    else:
        msg = "**Cola de reproducción:**\n"
        for i, song in enumerate(queue, 1):
            msg += f"{i}. {song.title}\n"
        await ctx.send(msg)

# Comando !pause y !resume
@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("**Pausado** ⏸️")
    else:
        await ctx.send("Nada reproduciéndose.")

@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("**Reanudado** ▶️")
    else:
        await ctx.send("No está pausado.")


# Evento: cuando el bot se conecta correctamente
@bot.event
async def on_ready():
    print(f'¡Bot conectado! Estoy funcionando como {bot.user} (ID: {bot.user.id})')
    print("¡Listo para recibir comandos! Prueba !ping en un servidor donde esté invitado.")

# Comando de prueba: !ping
@bot.command()
async def ping(ctx):
    await ctx.send("¡Pong! El bot está funcionando correctamente.")

@bot.command()
async def hola(ctx):
    await ctx.send(f"¡Hola {ctx.author.mention}! ¿Qué tal?")

@bot.command()
async def info(ctx):
    await ctx.send(f"Soy {bot.user.mention}\nCreado por: Giancarlo\nServidores: {len(bot.guilds)}")

# ¡NO OLVIDES PONER TU NUEVO TOKEN AQUÍ!
# Primero ve al portal, haz Reset Token y copia el nuevo


# Iniciar el bot
load_dotenv()  # Carga el .env
TOKEN = os.getenv("TOKEN")  # Lee el token de .env

bot.run(TOKEN)