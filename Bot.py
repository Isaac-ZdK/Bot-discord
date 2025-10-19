import discord
from discord.ext import commands
import yt_dlp
import asyncio
import ffmpeg
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

# Configurações yt-dlp e ffmpeg
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'restrictfilenames': True,
    'no_warnings': True,
    
}
ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if "entries" in data:
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


# Eventos e comandos
@bot.event
async def on_ready():
    print(f"🤖 Bot iniciado como {bot.user}")

@bot.command()
async def teste(ctx: commands.Context):
    nome = ctx.author.name
    await ctx.reply(f"Olá, {nome}, tudo bem!")

@bot.command(aliases=["p", "start", "music"])
async def play(ctx, *, url):
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("Você precisa estar em um canal de Voz!!")

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=False)
        fila = get_fila(ctx.guild.id)

        if not ctx.voice_client.is_playing():
            ctx.voice_client.play(
                player,
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            )
            await ctx.send(f"🎶 Tocando agora: **{player.title}**")
        else:
            fila.append(player)
            await ctx.send(f"➕ Adicionado à fila: **{player.title}**")

@bot.command()
async def skip(ctx):
    você = ctx.voice_client
    if você and você.is_playing():
        você.stop()
        await ctx.send("Musica pulada")
    else:
        await ctx.send("não está tocando nenhuma musica no momento")
  
@bot.command()
async def  stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.stop()
        await ctx.send("Musica encerrada e fila limpa")
    else:
        await ctx.send("❌ Não estou em nenhum canal de voz.")


fila = {}

def get_fila(guild_id):
    if guild_id not in fila:
        fila[guild_id] = []
    return fila[guild_id]

async def play_next(ctx):
    fila = get_fila(ctx.guild.id)

    if len(fila) > 0:
        player = fila.pop(0)
        ctx.voice_client.play(
            player,
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )
        await ctx.send(f"Tocando agora: **{player.title}**")
    else:
        await ctx.send("A fila encerrou, nenhuma musica restante.")



bot.run("Teste")
