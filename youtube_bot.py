# Buildpackler
# https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
# https://github.com/xrisk/heroku-opus.git
import asyncio
import discord
import youtube_dl
from discord.ext import commands

youtube_dl.utils.bug_reports_message = lambda: ''

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
    # Çıkarttım çünkü ne anlamı var?
    # 'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

# Çalışmıyor
# if not discord.opus.is_loaded():
#     discord.opus.load_opus('opus')
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
default_presence = discord.Activity(type=discord.ActivityType.listening, name='wasteland with sensors offline')


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    # Artık çalışıyor ama incelenmesi gerek
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.audio_player_task(self.bot.loop))
        self.queue = asyncio.Queue(loop=self.bot.loop)
        self.play_next = asyncio.Event(loop=self.bot.loop)

    # 'after=' video bitmeden çağrılıyor
    async def audio_player_task(self, loop):
        while True:
            self.play_next.clear()
            current = await self.queue.get()
            ctx = current[0]
            player = current[1]
            ctx.voice_client.play(player, after=lambda e: loop.create_task(self.after_voice(e, ctx, loop=loop)))
            await ctx.send('Now playing: {}'.format(player.title))
            # self.queue.task_done()
            await self.play_next.wait()

    async def after_voice(self, e: Exception, ctx, loop=None):
        if e is not None:
            print('Player error: %s' % e)
        await self.bot.wait_until_ready()
        while ctx.voice_client.is_playing():
            await asyncio.sleep(1)
        await ctx.send('Finished playing.')
        self.toggle_next(loop)

    def toggle_next(self, loop=None):
        loop.call_soon_threadsafe(self.play_next.set)

    @commands.command(help='Joins authors voice channel.')
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    # Nasıl tepki veriyor bilmiyorum
    @commands.command(help="Plays from a url.")
    async def yt(self, ctx, *, url):
        loop = self.bot.loop
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command(help="Streams from a url. Doesn't predownload.")
    async def stream(self, ctx, *, url):
        loop = self.bot.loop
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=loop, stream=True)
            # ctx.voice_client.play(player, after=lambda e: self.toggle_next(ctx, e, loop=loop))
            # sıraya ekle
            await self.queue.put((ctx, player))
            # await self.queue.join()
            if ctx.voice_client.source is not None:
                await ctx.send('Added to queue.')
        # Durumu değiştir
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                 name='{}'.format(player.title)))

    @commands.command(help='Changes volume to the value.')
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send('Ses kanalına bağlı değilim.')

        ctx.voice_client.source.volume = volume / 100
        await ctx.send('Ses seviyesi %{} oldu.'.format(volume))

    @commands.command(help='Disconnects the bot from voice channel.')
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()
        await self.bot.change_presence(activity=default_presence)

    @commands.command(help='Pauses')
    async def pause(self, ctx):
        if ctx.voice_client is not None:
            ctx.voice_client.pause()
            await ctx.send('Video durduruldu.')

    @commands.command(help='Resumes')
    async def resume(self, ctx):
        if ctx.voice_client is not None:
            ctx.voice_client.resume()
            await ctx.send('Videoya devam.')

    @commands.command(help='Skips current video.')
    async def skip(self, ctx):
        if ctx.voice_client is not None:
            ctx.voice_client.stop()

    @skip.before_invoke
    @resume.before_invoke
    @pause.before_invoke
    async def ensure_source(self, ctx):
        if ctx.voice_client is None:
            await ctx.send('Video oynamıyor.')

    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send('Ses kanalında değilsin.')
                raise commands.CommandError('Author not connected to a voice channel.')
        # elif ctx.voice_client.is_playing():
        #     ctx.voice_client.stop()
