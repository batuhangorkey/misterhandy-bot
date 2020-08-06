import os
import random
import discord
import pymysql

from minigame import Minigame
from youtube_bot import Music
# from kaiser import Kaiser
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
HOST = os.getenv('HOST')
USER_ID = os.getenv('USER_ID')
PASSWORD = os.getenv('PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')

client = discord.Client()
bot = commands.Bot(command_prefix='!')


def fetch_user_tables():
    user_table = {}
    kaiser_points = {}
    conn = pymysql.connect(str(HOST), str(USER_ID), str(PASSWORD), str(DATABASE_NAME))
    with conn.cursor() as cursor:
        cursor.execute('SELECT VERSION()')
        data = cursor.fetchone()
    print(f'Database version: {data}')
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM main")
        data = cursor.fetchall()
    conn.close()

    for row in data:
        user_table[int(row[0])] = int(row[1])
        kaiser_points[int(row[0])] = int(row[2])
    return user_table, kaiser_points


@bot.event
async def on_ready():
    print('{0.name} with ID: {0.id} has connected to Discord!'.format(bot.user))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                        name='wasteland with sensors offline'))
    bot.add_cog(Minigame(bot, user_table=fetch_user_tables()[0]))
    # bot.add_cog(Kaiser(bot, kaiser_points=fetch_user_tables()[1]))
    bot.add_cog(Music(bot))


@bot.command(help='Roll dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(help='Tries to purge max 50 messages by the bot.')
async def del_bot(ctx):
    def is_me(m):
        return m.author == bot.user

    deleted = await ctx.channel.purge(limit=50, check=is_me, bulk=False)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


@bot.command(help='Tries to purge messages. Max limit 50')
async def delete(ctx):
    deleted = await ctx.channel.purge(limit=50)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


bot.run(TOKEN)
