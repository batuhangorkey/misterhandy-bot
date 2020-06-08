import os
import random
import discord
import pymysql

from dotenv import load_dotenv
from discord.ext import commands
from minigame import initialize

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
HOST = os.getenv('HOST')
USER_ID = os.getenv('USER_ID')
PASSWORD = os.getenv('PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')

client = discord.Client()
bot = commands.Bot(command_prefix='!')
messages = []

conn = pymysql.connect(str(HOST), str(USER_ID), str(PASSWORD), str(DATABASE_NAME))
cursor = conn.cursor()


class Scene:
    def __init__(self, filtered_list, difficulty):
        self.list = filtered_list
        self.attempts = 5
        self.diff = difficulty
        self.state = 0
        self.reward = difficulty * 10


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

    global user_table
    user_table = {}
    global data

    cursor.execute('SELECT VERSION()')
    data = cursor.fetchone()
    print(f'Database version: {data}')

    cursor.execute("SELECT * FROM main")
    data = cursor.fetchall()
    for a, b in data:
        user_table[a] = b


@bot.command(name='d', help='Roll dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(name='start', help='Starts the mini game.')
async def start_scene(ctx, difficulty: int):
    global scene
    words = ""
    game_list = initialize(difficulty)
    if type(game_list) == list:
        scene = Scene(game_list, difficulty)
        for i in range(0, 10):
            words += f'\n  {i + 1} - {scene.list[i][0]}'
        if len(messages) > 0:
            await ctx.channel.delete_messages(messages)
            messages.clear()
        messages.append(await ctx.send(f'Terminal: {words}'))
    else:
        messages.append(await ctx.send('Hoppala bir daha dene uşağım'))


@bot.command(name='enter', help='Enter key to the terminal.')
async def func(ctx, index: int):
    user = ctx.message.author
    if scene.list[index - 1][1] == scene.diff and scene.state == 0 and scene.attempts > 0:
        scene.state = 1
        if user.id in user_table:
            user_table[user.id] += scene.reward
            cursor.execute(f"UPDATE main SET Unit = Unit + {scene.reward} WHERE UserID = {user.id}")
        else:
            user_table.update({user.id: scene.reward})
            cursor.execute(f"INSERT INTO main VALUES ('{user.id}', '{scene.reward}')")
        conn.commit()
        await ctx.send(f'Sistemin içindeyiz. {user.name} +{scene.reward} Lirabit ({user_table.get(user.id)})')
        if len(messages) > 0:
            await ctx.channel.delete_messages(messages)
            messages.clear()
    elif scene.state == 1:
        messages.append(await ctx.send('Sistem hacklendi.'))
    else:
        scene.attempts -= 1
        if scene.attempts > 0:
            messages.append(await ctx.send('Benzerlik: ' + str(scene.list[index - 1][1]) +
                                           '\nKalan deneme sayısı: ' + str(scene.attempts)))
        else:
            messages.append(await ctx.send('Sistem kitlendi.'))


@bot.command(name='myxp', help='Shows your xp.')
async def func2(ctx):
    user = ctx.message.author
    if user.id in user_table:
        await ctx.send(f'Tecrüben: {user_table.get(user.id)} Lirabit')
    else:
        await ctx.send('Daha oynamamışsın.')


@bot.command(name='del_all_own', help='Tries to purge messages sent by the bot.')
async def func3(ctx):
    def is_me(m):
        return m.author == bot.user

    deleted = await ctx.channel.purge(limit=50, check=is_me, bulk=False)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


@bot.command(name='del_all', help='Tries to purge messages. (limit 50)')
async def func4(ctx):
    deleted = await ctx.channel.purge(limit=50)
    await ctx.send(f'Deleted {len(deleted)} message(s).')


bot.run(TOKEN)
