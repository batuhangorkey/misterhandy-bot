# Buildpack'ler
# https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
# https://github.com/xrisk/heroku-opus.git
import asyncio
import discord
import youtube_dl
import random
import time
import os
import pymysql
from discord.ext import commands
from youtube_search import YoutubeSearch
from dotenv import load_dotenv

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
    # 'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

player_emojis = {
    'stop': u'\u23F9',
    'play_pause': u'\u23EF',
    'next_track': u'\u23ED'
}

# if not discord.opus.is_loaded():
#     discord.opus.load_opus('opus')
# ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

youtube_dl.utils.bug_reports_message = lambda: ''

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
HOST = os.getenv('HOST')
USER_ID = os.getenv('USER_ID')
PASSWORD = os.getenv('PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')


def get_random_playlist():
    conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT url FROM playlist")
            data = cursor.fetchall()
    finally:
        conn.close()
    return [item for _ in data for item in _]


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')
        self.duration = time.strftime('%M:%S', time.gmtime(data.get('duration')))

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            with youtube_dl.YoutubeDL(ytdl_format_options) as ytdl:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except youtube_dl.utils.DownloadError as error:
            print(error)
            return
        if 'entries' in data:
            data = data['entries'][0]
        with youtube_dl.YoutubeDL(ytdl_format_options) as ytdl:
            filename = data['url'] if stream else ytdl.prepare_filename(data)
        # for _, x in data.items():
        #     print(_, x)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_presence = discord.Activity(type=discord.ActivityType.listening,
                                                 name='wasteland with sensors offline')

        self.queue = asyncio.Queue(loop=self.bot.loop)
        self.play_next = asyncio.Event(loop=self.bot.loop)
        self.play_random = False
        self._ctx = None
        self.last_message = None

        self.bot.loop.create_task(self.audio_player())
        self.search_list = []
        self._random_playlist = get_random_playlist()
        self.random_playlist = self._random_playlist.copy()

    def refresh_playlist(self):
        self._random_playlist = get_random_playlist()
        self.random_playlist = self._random_playlist.copy()

    def get_song_from_rnd_playlist(self):
        if len(self.random_playlist) == 0:
            self.random_playlist = self._random_playlist.copy()
        song = random.choice(self.random_playlist)
        self.random_playlist.remove(song)
        return song

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next.set)

    async def manage_last(self, msg):
        try:
            if self.last_message:
                await self.last_message.delete()
        finally:
            self.last_message = msg

    async def audio_player(self):
        try:
            global _ctx
            while True:
                self.play_next.clear()

                try:
                    if self.queue.qsize() == 0:
                        if self.play_random and _ctx.voice_client is not None:
                            async with _ctx.typing():
                                player = await YTDLSource.from_url(self.get_song_from_rnd_playlist(),
                                                                   loop=self.bot.loop)
                                await self.queue.put((_ctx, player))
                        elif self.last_message:
                            await self.bot.change_presence(activity=self.default_presence)
                            embed = self.last_message.embeds[0]
                            embed.description = 'Video bitti'
                            await self.last_message.edit(embed=embed)
                except NameError:
                    pass

                current = await self.queue.get()
                _ctx = current[0]
                self._ctx = _ctx
                player = current[1]
                _ctx.voice_client.play(player,
                                       after=lambda e: print('Player error: %s' % e) if e else self.toggle_next())

                embed = discord.Embed(title='{0.title} ({0.duration}) by {0.uploader}'.format(player),
                                      url=player.url,
                                      description='Şimdi oynatılıyor',
                                      colour=0x8B0000)
                embed.set_thumbnail(url=player.thumbnail).set_footer(text='Ozan: Yerli ve Milli İlk Video Oynatıcısı')
                async with _ctx.typing():
                    if self.last_message:
                        _embed = self.last_message.embeds[0]
                        if len(_embed.fields) > 1:
                            _embed.remove_field(0)
                            for _ in _embed.fields:
                                embed.add_field(name=str(self.queue.qsize()),
                                                value=_.value)
                    await self.manage_last(await _ctx.send(embed=embed))
                    for _ in player_emojis.values():
                        await self.last_message.add_reaction(_)

                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                         name=format(player.title)))
                await self.play_next.wait()
        except AttributeError as error:
            print(error)
        except discord.errors.HTTPException as error:
            print(error)
        except asyncio.CancelledError as error:
            print(error)

    # async def after_voice(self, e: Exception, ctx, loop=None):
    #     if e is not None:
    #         print('Player error: %s' % e)
    #     await self.bot.wait_until_ready()
    #     while ctx.voice_client.is_playing():
    #         await asyncio.sleep(1)
    #     await ctx.send(f'Finished playing: {ctx.voice_client.source.title}')
    #     loop.call_soon_threadsafe(self.play_next.set)

    @commands.command(help='Joins authors voice channel.')
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        if ctx.voice_client:
            return await ctx.voice_client.move_to(channel)
        if channel is None:
            return await ctx.author.voice.channel.connect()
        await channel.connect()

    # Şarkı oynatma komutları
    @commands.command(help="Plays from a url.")
    async def yt(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            if player is None:
                return await ctx.send('Bir şeyler yanlış. Bir daha dene')
            # sıraya ekle
            await self.queue.put((ctx, player))
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                embed = self.last_message.embeds[0]
                embed.add_field(name=str(self.queue.qsize()),
                                value=player.title)
                await self.manage_last(await ctx.send(embed=embed))
                for _ in player_emojis.values():
                    await self.last_message.add_reaction(_)

    @commands.command(help="Streams from a url. Doesn't predownload.")
    async def stream(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            if player is None:
                return await ctx.send('Birşeyler yanlış. Bir daha dene')
            # sıraya ekle
            await self.queue.put((ctx, player))
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                embed = self.last_message.embeds[0]
                embed.add_field(name=str(self.queue.qsize()),
                                value=player.title)
                await self.manage_last(await ctx.send(embed=embed))
                for _ in player_emojis.values():
                    await self.last_message.add_reaction(_)

    @commands.command(help='Plays the first result from a search string.')
    async def play(self, ctx, *, search_string):
        async with ctx.typing():
            result = YoutubeSearch(search_string, max_results=1).to_dict()
            try:
                url = 'https://www.youtube.com' + result[0]['url_suffix']
            except IndexError:
                await ctx.send('Video bulamadım. Bir daha dene')
                return
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            if player is None:
                return await ctx.send('Bir şeyler yanlış. Bir daha dene')
            # sıraya ekle
            await self.queue.put((ctx, player))
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                embed = self.last_message.embeds[0]
                embed.add_field(name=str(self.queue.qsize()),
                                value=player.title)
                await self.manage_last(await ctx.send(embed=embed))
                for _ in player_emojis.values():
                    await self.last_message.add_reaction(_)

    @commands.command(help='Searches youtube. 10 results')
    async def search(self, ctx, *, search_string):
        self.search_list.clear()
        results = YoutubeSearch(search_string, max_results=10).to_dict()
        embed = discord.Embed(colour=0x8B0000)
        i = 1
        for _ in results:
            k = '[{} - {}](https://www.youtube.com{})'
            embed.add_field(name=' - '.join([str(i), _['title']]),
                            value=k.format(_['channel'], _['duration'], _['url_suffix']))
            self.search_list.append('https://www.youtube.com{}'.format(_['url_suffix']))
            i = i + 1
        async with ctx.typing():
            await ctx.send(embed=embed, delete_after=20)
        self.bot.add_cog(Events(self.bot, ctx))

    @commands.command(help='Plays random songs')
    async def playrandom(self, ctx):
        if not ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
            if not self.play_random:
                async with ctx.typing():
                    player = await YTDLSource.from_url(self.get_song_from_rnd_playlist(), loop=self.bot.loop)
                    if player is None:
                        return await ctx.send('Bir şeyler yanlış. Bir daha dene')
                    await self.queue.put((ctx, player))
        self.play_random = not self.play_random
        await ctx.send('Rastgele çalınıyor') if self.play_random else await ctx.send('Rastgele çalma kapatıldı')

    @yt.before_invoke
    @stream.before_invoke
    @play.before_invoke
    @search.before_invoke
    @playrandom.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send('Ses kanalında değilsin.')
                raise commands.CommandError('Author not connected to a voice channel.')

    @commands.command(help='Changes volume to the value.')
    async def volume(self, ctx, volume: int):
        await ctx.message.delete()
        if ctx.voice_client is None:
            return await ctx.send('Ses kanalına bağlı değilim.')

        ctx.voice_client.source.volume = volume / 100
        await ctx.send('Ses seviyesi %{} oldu.'.format(volume))

    @commands.command(help='Pauses')
    async def pause(self, ctx):
        if ctx.voice_client is not None and ctx.voice_client.source:
            ctx.voice_client.pause()
            embed = self.last_message.embeds[0]
            embed.description = 'Durduruldu'
            await self.last_message.edit(embed=embed)

    @commands.command(help='Resumes')
    async def resume(self, ctx):
        if ctx.voice_client is not None and ctx.voice_client.source:
            ctx.voice_client.resume()
            embed = self.last_message.embeds[0]
            embed.description = 'Oynatılıyor'
            await self.last_message.edit(embed=embed)

    @commands.command(help='Skips current video.')
    async def skip(self, ctx):
        if ctx.voice_client is not None:
            ctx.voice_client.stop()

    @commands.command(help='Disconnects the bot from voice channel.')
    async def stop(self, ctx):
        self.play_random = False
        for _ in range(self.queue.qsize()):
            self.queue.get_nowait()
            self.queue.task_done()
        try:
            await ctx.voice_client.disconnect()
        except AttributeError as error:
            print(error)
            pass
        await self.bot.change_presence(activity=self.default_presence)

    @commands.command(help='Adds song to bot playlist')
    async def add_link(self, ctx, *, url):
        conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO playlist (url) VALUES ('{}')".format(url))
            conn.commit()

            with conn.cursor() as cursor:
                cursor.execute('SELECT url FROM playlist where url="{}"'.format(url))
                data = cursor.fetchone()
            if data:
                self.refresh_playlist()
                await ctx.send('Şarkı eklendi. Teşekkürler')
        finally:
            conn.close()

    # Bu şekilde çalışmıyor
    # @commands.command(help='Go to the time on the video')
    # async def goto(self, ctx, time: str):
    #     async with ctx.typing():
    #         player = await YTDLSource.from_url(url=ctx.voice_client.source.url + '&t=' + time,
    #                                            loop=self.bot.loop)
    #     await self.queue.put((ctx, player))
    #     for _ in range(self.queue.qsize() - 1):
    #         a = self.queue.get_nowait()
    #         self.queue.task_done()
    #         self.queue.put_nowait(a)
    #     await self._ctx.invoke(self.bot.get_command('skip'))
    #     await ctx.send('Mevcut şarkıda {}ıncı saniyeye gidiliyor.'.format(time))
    #
    # @goto.before_invoke
    # async def ensure_source(self, ctx):
    #     if ctx.voice_client.source is None:
    #         await ctx.send('Ortada ileri alınacak video yok.')
    #         raise commands.CommandError('Audio source empty.')

    # Yapılmayı bekliyor
    # @commands.command(help='Downloads video')
    # async def download(self, ctx, *, url):
    #     player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
    #     await ctx.send(file=player.url)

    # Player events
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if reaction.message.id == self.last_message.id:
            if reaction.emoji == player_emojis['next_track']:
                return await self._ctx.invoke(self.bot.get_command('skip'))
            if reaction.emoji == player_emojis['play_pause']:
                return await self._ctx.invoke(self.bot.get_command('pause'))
            if reaction.emoji == player_emojis['stop']:
                return await self._ctx.invoke(self.bot.get_command('stop'))

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return
        if reaction.message.id == self.last_message.id:
            if reaction.emoji == player_emojis['play_pause']:
                return await self._ctx.invoke(self.bot.get_command('resume'))


class Events(commands.Cog):
    def __init__(self, bot, ctx):
        self.bot = bot
        self.ctx = ctx

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author == self.bot.user:
            return
        try:
            index = int(msg.content)
        except ValueError:
            return
        if index < 1 or 10 < index:
            return
        music = self.bot.get_cog('Music')
        await self.ctx.invoke(music.bot.get_command('yt'), url=music.search_list[index - 1])
        music.search_list.clear()
        self.bot.remove_cog('Events')
