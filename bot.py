import os
import random
import discord
import pymysql

from minigame import Minigame
from youtube_bot import Music
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


def fetch_user_table():
    user_table = {}
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

    return user_table


@bot.event
async def on_ready():
    print('{0.name} with ID: {0.id} has connected to Discord!'.format(bot.user))


@bot.command(name='d', help='Roll dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@commands.command(name='del_all_own', help='Tries to purge messages sent by the bot.')
async def func3(ctx):
    def is_me(m):
        return m.author == bot.user

    deleted = await ctx.channel.purge(limit=50, check=is_me, bulk=False)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


@commands.command(name='del_all', help='Tries to purge messages. (limit 50)')
async def func4(ctx):
    deleted = await ctx.channel.purge(limit=50)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


bot.add_cog(Minigame(bot, user_table=fetch_user_table()))
bot.add_cog(Music(bot))
bot.run(TOKEN)
