# Buildpack'ler
# https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
# https://github.com/xrisk/heroku-opus.git
import asyncio
import discord
import youtube_dl
import random
import itertools
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
    'next_track': u'\u23ED',
    'backward': u'\u21AA',
    'forward': u'\u21A9'
}

playlist_emojis = {
    'dislike': u'\U0001F44E',
    'like': u'\U0001F44D'
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
            cursor.execute("SELECT url, dislike, like_count FROM playlist")
            data = cursor.fetchall()
    finally:
        conn.close()
    db_playlist = [t for t in data]
    db_playlist = [(url, int(like / dislike)) for url, dislike, like in db_playlist]
    return db_playlist


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')
        self.duration = data.get('duration')
        self.start_time = data.get('start_time')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, start_time=0):
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
        data['start_time'] = start_time
        data['duration'] = time.strftime('%M:%S', time.gmtime(data.get('duration')))
        if start_time != 0:
            ffmpeg_options['options'] = '-vn -ss {}'.format(time.strftime('%M:%S', time.gmtime(start_time)))
        else:
            ffmpeg_options['options'] = '-vn'
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

        self.source_start_tme = None
        self.time_cursor = None
        self.time_setting = 30

        # self.bot.loop.create_task(self.audio_player())
        self.task = None
        self.search_list = []
        self._random_playlist = None
        self.random_playlist = None
        self.refresh_playlist()

    def refresh_playlist(self):
        self._random_playlist = get_random_playlist()
        self.random_playlist = self._random_playlist.copy()

    def get_song_from_rnd_playlist(self):
        if len(self.random_playlist) == 0:
            self.refresh_playlist()
        cum_weights = list(itertools.accumulate([rating for url, rating in self.random_playlist]))
        song = random.choices(self.random_playlist, cum_weights=cum_weights, k=1)[0]
        self.random_playlist.remove(song)
        return song[0]

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next.set)

    async def send_player_embed(self, source):
        if source.start_time != 0:
            description = 'Şimdi oynatılıyor - {} dan başladı'.format(time.strftime('%M:%S',
                                                                                    time.gmtime(source.start_time)))
        else:
            description = 'Şimdi oynatılıyor'
        embed = discord.Embed(title='{0.title} ({0.duration}) by {0.uploader}'.format(source),
                              url=source.url,
                              description=description,
                              colour=0x8B0000)
        embed.set_thumbnail(url=source.thumbnail)
        footer = 'Ozan: Yerli ve Milli İlk Video Oynatıcısı - Rastgele çalma {} - {}'
        embed.set_footer(text=footer.format('açık' if self.play_random else 'kapalı', self.bot.version_name))
        if self.last_message:
            _embed = self.last_message.embeds[0]
            if len(_embed.fields) > 1:
                _embed.remove_field(0)
                for _ in _embed.fields:
                    embed.add_field(name=str(self.queue.qsize()),
                                    value=_.value)
        await self.manage_last(await _ctx.send(embed=embed))
        await asyncio.gather([await self.last_message.add_reaction(_) for _ in player_emojis.values()])
        # for _ in player_emojis.values():
        #     await self.last_message.add_reaction(_)
        if not self.play_random:
            return
        for _ in playlist_emojis.values():
            await self.last_message.add_reaction(_)

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
                self.time_cursor = 0

                try:
                    if self.queue.qsize() == 0:
                        if self.play_random and _ctx.voice_client is not None:
                            async with _ctx.typing():
                                player = await YTDLSource.from_url(self.get_song_from_rnd_playlist(),
                                                                   loop=self.bot.loop)
                                if player:
                                    await self.queue.put((_ctx, player))
                                else:
                                    await _ctx.invoke(self.bot.get_command('play_random'))
                                    await _ctx.send('Birşeyler kırıldı.')
                        elif self.last_message:
                            await self.bot.change_presence(activity=self.default_presence)
                            embed = self.last_message.embeds[0]
                            embed.description = 'Video bitti'
                            await self.last_message.edit(embed=embed)
                except NameError:
                    pass

                current = await self.queue.get()
                _ctx, player = current
                self._ctx = _ctx
                _ctx.voice_client.play(player,
                                       after=lambda e: print('Player error: %s' % e) if e else self.toggle_next())
                self.source_start_tme = time.time()
                async with _ctx.typing():
                    await self.send_player_embed(player)
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                         name=format(player.title)))
                await self.play_next.wait()
        except AttributeError as error:
            print(error)
        except discord.errors.HTTPException as error:
            print(error)
        except asyncio.CancelledError as error:
            print(error)

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
        async with ctx.typing():
            if not ctx.voice_client.is_playing() or not ctx.voice_client.is_paused():
                if not self.play_random:
                        player = await YTDLSource.from_url(self.get_song_from_rnd_playlist(), loop=self.bot.loop)
                        if player is None:
                            return await ctx.send('Bir şeyler yanlış. Bir daha dene')
                        await self.queue.put((ctx, player))
            self.play_random = not self.play_random
            if self.last_message:
                _embed = self.last_message.embeds[0]
                footer = 'Ozan: Yerli ve Milli İlk Video Oynatıcısı - Rastgele çalma {}'
                _embed.set_footer(text=footer.format('açık' if self.play_random else 'kapalı'))
                await self.last_message.edit(embed=_embed)

    @yt.before_invoke
    @stream.before_invoke
    @play.before_invoke
    @search.before_invoke
    @playrandom.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                self.task = self.bot.loop.create_task(self.audio_player())
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
        if ctx.voice_client and ctx.voice_client.source:
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
        if ctx.voice_client.source:
            ctx.voice_client.stop()

    @commands.command(help='Disconnects the bot from voice channel.')
    async def stop(self, ctx):
        self.play_random = False
        self.refresh_playlist()
        for _ in range(self.queue.qsize()):
            self.queue.get_nowait()
            self.queue.task_done()
        try:
            await ctx.voice_client.disconnect()
        except AttributeError as error:
            print(error)
        if self.task:
            self.task.cancel()
        await self.bot.change_presence(activity=self.default_presence)

    @commands.command(help='Adds song to bot playlist')
    async def add_link(self, ctx, url: str):
        if len(url) != 43 or not url.startswith('https://www.youtube.com/watch?v='):
            return await ctx.send('Linkini kontrol et. Tam link atmalısın')
        conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)
        try:
            with conn.cursor() as cursor:
                if url in self._random_playlist:
                    return await ctx.send('Bu şarkı listede var.')

                cursor.execute('INSERT INTO playlist (url, skip_count) VALUES ("{}", 1)'.format(url))
                conn.commit()

                cursor.execute('SELECT url FROM playlist where url="{}"'.format(url))
                data = cursor.fetchone()

            if data:
                self.refresh_playlist()
                await ctx.send('Şarkı eklendi. Teşekkürler')
            else:
                await ctx.send('Şarkı eklenemedi.')
        finally:
            conn.close()

    @commands.command(help='Go to the time on the video')
    async def goto(self, ctx, target_time: int):
        async with ctx.typing():
            self.time_cursor = target_time
            ctx.voice_client.pause()
            player = await YTDLSource.from_url(url=ctx.voice_client.source.url,
                                               loop=self.bot.loop,
                                               start_time=target_time)
            ctx.voice_client.source = player
            self.source_start_tme = time.time()
            await self.send_player_embed(player)
            for _ in range(self.queue.qsize() - 1):
                a = self.queue.get_nowait()
                self.queue.task_done()
                self.queue.put_nowait(a)

    @goto.before_invoke
    async def ensure_source(self, ctx):
        if ctx.voice_client.source is None:
            await ctx.send('Ortada ileri alınacak video yok.')
            raise commands.CommandError('Audio source empty.')

    @commands.command(help='Set backward forward time value')
    async def set_skip_time(self, ctx, time_set: int):
        async with ctx.typing():
            self.time_setting = time_set

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
            if reaction.emoji == player_emojis['backward']:
                delta_time = time.time() - self.source_start_tme
                target_time = self.time_cursor + delta_time - self.time_setting
                return await self._ctx.invoke(self.bot.get_command('goto'), target_time=target_time)
            if reaction.emoji == player_emojis['forward']:
                delta_time = time.time() - self.source_start_tme
                target_time = self.time_cursor + delta_time + self.time_setting
                return await self._ctx.invoke(self.bot.get_command('goto'), target_time=target_time)
            if reaction.emoji == playlist_emojis['dislike']:
                self.dislike()
                return await self._ctx.invoke(self.bot.get_command('skip'))
            if reaction.emoji == playlist_emojis['like']:
                await self.like()
                return await self._ctx.invoke(self.bot.get_command('skip'))

    def dislike(self):
        if _ctx.voice_client.source is None:
            return
        url = _ctx.voice_client.source.url
        if url not in [url for url, s in self._random_playlist]:
            return _ctx.voice_client.stop()
        conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)
        try:
            with conn.cursor() as cursor:
                cursor.execute('UPDATE playlist SET dislike = dislike + 1 WHERE url = "{}"'.format(url))
            conn.commit()
        finally:
            conn.close()
            return

    async def like(self):
        if _ctx.voice_client.source is None:
            return
        url = _ctx.voice_client.source.url
        if url not in [url for url, s in self._random_playlist]:
            return await self._ctx.send('Sadece şarkı listesindeki şarkılar beğenilebilir.')
        conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)
        try:
            with conn.cursor() as cursor:
                cursor.execute('UPDATE playlist SET like = like + 1 WHERE url = "{}"'.format(url))
            conn.commit()
        finally:
            conn.close()
            return

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
