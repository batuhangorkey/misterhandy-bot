import configparser
import datetime
import logging
import os
import random
import subprocess
import time

import discord
import pymysql
from discord.ext import commands

from modules.minigame import Minigame
from modules.story_teller import Project2
from modules.youtube_bot import Music

FORMAT = '%(asctime)s %(levelname)s %(user)s %(message)s'
logging.root.setLevel(logging.NOTSET)
logging.basicConfig(format=FORMAT, level=logging.NOTSET)
log = logging.getLogger('bot')
log.setLevel(logging.NOTSET)

config = configparser.ConfigParser()
config.read('config.ini')
bot_token = config.get('Bot', 'Token')
database_config = dict(config.items('Database'))

presences = [
    'wasteland with sensors offline',
    'your feelings',
    'psychedelic space rock',
    'eternal void',
    'ancient orders'
]

adj = {
    8: 'Efsane',
    7: 'İnanılmaz',
    6: 'Şahane',
    5: 'Muhteşem',
    4: 'Harika',
    3: 'Baya iyi',
    2: 'İyi',
    1: 'Eh',
    0: 'Düz',
    -1: 'Dandik',
    -2: 'Kötü',
    -3: 'Rezalet',
    -4: 'Felaket'
}


class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!')
        self._token = bot_token
        self._database_config = database_config

    @staticmethod
    def get_git_version():
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('ascii')

    @property
    def token(self):
        return self._token

    @property
    def database_config(self):
        return self._database_config

    @property
    def version_name(self):
        return 'v{}'.format(self.get_git_version())

    def get_pymysql_connection(self):
        conn = pymysql.connect(self.database_config['host'],
                               self.database_config['userid'],
                               self.database_config['password'],
                               self.database_config['databasename'])
        return conn

    def fetch_user_tables(self):
        user_table = {}
        kaiser_points = {}
        conn = self.get_pymysql_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            data = cursor.fetchone()
            print(f'Database version: {data[0]}')
            cursor.execute("SELECT * FROM main")
            data = cursor.fetchall()
        conn.close()
        for _, b, k in data:
            user_table[int(_)] = int(b)
        return user_table, kaiser_points

    def get_random_playlist(self):
        conn = self.get_pymysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT url, dislike, like_count FROM playlist")
                data = cursor.fetchall()
        finally:
            conn.close()
        db_playlist = [t for t in data]
        db_playlist = [(url, int(like / dislike)) for url, dislike, like in db_playlist]
        print('Random playlist length: {}'.format(len(db_playlist)))
        return db_playlist

    async def default_presence(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name=random.choice(presences)))


bot = CustomBot()

# TODO:
#  Organize all to a single class
#  Add auto moderation function
#  Discord role manupulation


@bot.event
async def on_connect():
    pass


@bot.event
async def on_ready():
    try:
        start = time.process_time()
        log.info('Back online')
        log.info('Running git hash: {}'.format(bot.get_git_version()))
        log.info('{0.name} with id: {0.id} is ready on Discord'.format(bot.user))

        async for guild in bot.fetch_guilds():
            log.info('\tOperating on {} with id: {}'.format(guild.name, guild.id))

        await bot.default_presence()
        bot.add_cog(Project2(bot))
        bot.add_cog(Music(bot))

        for item in os.listdir('./'):
            if item.endswith(('.webm', '.m4a')):
                os.remove(item)

        log.info(os.path.abspath(os.path.dirname(__file__)))
        for item in os.listdir('./'):
            log.info('\t{}'.format(item))
        end = time.process_time() - start
        log.info('Method: {} | Elapsed time: {}'.format('on_ready', end))
    except Exception as e:
        log.error(e)


@bot.event
async def on_error(event, *args, **kwargs):
    print(event)
    print(args)
    print(kwargs)
    pass


@bot.command(help='Enable minigame')
async def minigame(ctx):
    try:
        if bot.get_cog('Minigame'):
            bot.remove_cog('Minigame')
        bot.add_cog(Minigame(bot, user_table=bot.fetch_user_tables()[0]))
    finally:
        await ctx.send('Enabled minigame')


@bot.command(help='Roll dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(help='FATE zarı atar')
async def zar(ctx, modifier: int = 0):
    dice = [
        random.choice([-1, -1, 0, 0, 1, 1])
        for _ in range(4)
    ]
    _sum = sum(dice) + modifier
    await ctx.send(', '.join(map(str, dice)) + ' + {} = {}   **{}**'.format(modifier, _sum, adj[_sum]))


@bot.command(help='Tries to purge max 50 messages sent by the bot.')
async def del_bot(ctx):
    def is_me(m):
        return m.author == bot.user

    deleted = await ctx.channel.purge(limit=50, check=is_me, bulk=False)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


@bot.command(help='Tries to purge messages. Max limit 50')
async def delete(ctx, limit: int = None):
    if limit is None:
        limit = 50
    if limit > 50:
        limit = 50
    deleted = await ctx.channel.purge(limit=limit)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


@bot.command(help='Refreshes bot.')
async def reset(ctx):
    await ctx.send("Hoşçakalın")
    log.info("Going offine")
    exit()


@bot.command(help='Pings bot')
async def ping(ctx):
    delta = datetime.datetime.utcnow() - ctx.message.created_at
    await ctx.send("Elapsed seconds: {}".format(delta.total_seconds()))

bot.run(bot.token)
