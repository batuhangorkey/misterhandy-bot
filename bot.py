import random
import discord
import pymysql
import time
import datetime
import subprocess
import configparser
from discord.ext import commands
from modules.minigame import Minigame
from modules.youtube_bot import Music
from modules.story_teller import Project2

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


def fetch_user_tables():
    user_table = {}
    kaiser_points = {}

    conn = pymysql.connect(database_config['host'],
                           database_config['userid'],
                           database_config['password'],
                           database_config['databasename'])

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


def get_git_version():
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('ascii')


class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!')
        self.version_name = 'v{}'.format(get_git_version())
        self._token = bot_token
        self._database_config = database_config

    @property
    def token(self):
        return self._token

    @property
    def database_config(self):
        return self._database_config

    async def default_presence(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                             name=random.choice(presences)))


bot = CustomBot()

# TODO:
#  Organize all to a single class
#  Add auto moderation function
#  Discord role manupulation


@bot.event
async def on_ready():
    start = time.process_time()
    print('Back online')
    print('Running git hash: {}'.format(get_git_version()))
    print('{0.name} with id: {0.id} has connected to Discord at {time}'.format(bot.user,
                                                                               time=time.ctime(time.time() + 10800)))
    async for guild in bot.fetch_guilds():
        print('Operating on {} with id: {}'.format(guild.name, guild.id))

    await bot.default_presence()
    bot.add_cog(Project2(bot))
    bot.add_cog(Music(bot))
    end = time.process_time() - start
    import inspect
    print('Method: {} | Elapsed time: {}'.format(inspect.currentframe().f_code.co_name, end))


@bot.command(help='Enable minigame')
async def minigame(ctx):
    try:
        if bot.get_cog('Minigame'):
            bot.remove_cog('Minigame')
        bot.add_cog(Minigame(bot, user_table=fetch_user_tables()[0]))
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
async def refresh(ctx):
    await ctx.send("Hoşçakalın")
    print("Going offine")
    exit()


@bot.command(help='Pings bot')
async def ping(ctx):
    delta = datetime.datetime.utcnow() - ctx.message.created_at
    await ctx.send("Elapsed seconds: {}".format(delta.total_seconds()))

bot.run(bot.token)
