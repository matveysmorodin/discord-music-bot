import discord
from discord import Embed
from discord.ext import commands
import asyncio
import yt_dlp
from dotenv import load_dotenv
import pytube
import urllib.parse, urllib.request, re



def run_bot():
    load_dotenv()
    intents = discord.Intents.default()
    intents.message_content = True
    activity = discord.Activity(type=discord.ActivityType.listening, name=".play")
    client = commands.Bot(command_prefix=".", intents=intents, activity = activity, status = discord.Status.dnd)

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn -filter:a "volume=0.25"'}

    class Menu(discord.ui.View):
        def __init__(self, *, timeout=100):
            super().__init__(timeout=timeout)

        @discord.ui.button(label="Пауза", style=discord.ButtonStyle.primary, custom_id="pause_button")
        async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Напишите .stop для того чтобы остановить воспроизведение ", ephemeral=True)

        @discord.ui.button(label="Следующий трек", style=discord.ButtonStyle.primary, custom_id="skip_button")
        async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Чтобы пропустить трек напишите команду .next", ephemeral=True)

        @discord.ui.button(label="Очередь", style=discord.ButtonStyle.primary, custom_id="resume_button")
        async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Для того чтобы посмотреть очередь напишите .list ", ephemeral=True)

    @client.event
    async def on_ready():
        print(f'{client.user} is online!')

    @client.command(name='next')
    async def play_next(ctx):
        if queues[ctx.guild.id] != []:
            link = queues[ctx.guild.id].pop(0)
            await play(ctx, link=link)

    @client.command(name="play")
    async def play(ctx, *, link):

        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:

            if "www.youtube.com" not in link:
                query_string = urllib.parse.urlencode({
                    'search_query': link
                })

                content = urllib.request.urlopen(
                    youtube_results_url + query_string
                )

                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())

                link = youtube_watch_url + search_results[0]
                await ctx.send('https://www.youtube.com/watch?v=' + search_results[0])

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            player = discord.FFmpegOpusAudio(song, **FFMPEG_OPTIONS)
            view = Menu()

            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx),client.loop))
            embed = Embed(title=f"Сейчас играет", description=f"[**{data['title']}**]({data['url']})")
            embed.set_image(url=data['thumbnail'])

            await ctx.channel.send(embed=embed, view=view)
        except Exception as e:
            print(e)

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Очередь очищенна")
        else:
            await ctx.send("Очищать нечего, очередь пустая")

    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    @client.command(name="queue")
    async def queue(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Добавлено в очередь")

    @client.command(name='list')
    async def list(ctx):
        if queues[ctx.guild.id] != []:
            embed_list = Embed(title=f"Сейчас в очереди", description=f'{'\n'.join(queues[ctx.guild.id])}')
            await ctx.channel.send(embed = embed_list)
        else:
            await ctx.send('Очередь пустая')

    with open("token.txt") as f: #RU: Создайте файл token.txt и вставте туда свой токен ENG: Create a file token.txt and insert your token there
        token = f.read().strip()
    client.run(token)
