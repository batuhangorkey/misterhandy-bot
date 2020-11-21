import random
import discord
import pymysql
import time
from discord.ext import commands
from minigame import Minigame
from youtube_bot import Music
from project_2 import Project2
from bot_data import bot_data
# from kaiser import Kaiser

TOKEN = bot_data["TOKEN"]
HOST = bot_data["HOST"]
USER_ID = bot_data["USER_ID"]
PASSWORD = bot_data["PASSWORD"]
DATABASE_NAME = bot_data["DATABASE_NAME"]


class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!')
        self.version_name = time.strftime('v%d.%m.%Y', time.gmtime())


bot = CustomBot()

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

    conn = pymysql.connect(str(HOST),
                           str(USER_ID),
                           str(PASSWORD),
                           str(DATABASE_NAME))
    with conn.cursor() as cursor:
        cursor.execute('SELECT VERSION()')
        data = cursor.fetchone()
        print(f'Database version: {data[0]}')
        cursor.execute("SELECT * FROM main")
        data = cursor.fetchall()
    conn.close()

    for _, b, k in data:
        user_table[int(_)] = int(b)
        # kaiser_points[int(_)] = int(k)
    return user_table, kaiser_points


@bot.event
async def on_ready():
    print('{0.name} with id: {0.id} has connected to Discord at {time}'.format(bot.user,
                                                                               time=time.ctime(time.time() + 10800)))
    async for guild in bot.fetch_guilds():
        print('Operating on {} with id: {}'.format(guild.name, guild.id))

    channel = bot.get_channel(717725470954749985)
    await channel.send('Buradayım')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                        name='wasteland with sensors offline'))
    bot.add_cog(Minigame(bot, user_table=fetch_user_tables()[0]))
    # bot.add_cog(Kaiser(bot, kaiser_points=fetch_user_tables()[1]))
    bot.add_cog(Project2(bot))
    bot.add_cog(Music(bot))


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
    exit()

bot.run(TOKEN)
