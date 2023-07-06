import atexit
import configparser
import datetime
import logging
import os
import random
import subprocess
import sys
import time

import discord
import pymysql
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pyngrok import conf, ngrok

from modules.codenames import CodeNames
from modules.minigame import Minigame
from modules.secret_hitler import SecretHitler
from modules.youtube_bot import Music

# GIT_PATH = 'git'
# JAVA_PATH = '/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java'
# JAVA_OPTIONS = [JAVA_PATH, '-Xmx6048M', '-Xms1024M', '-jar', 'forge-1.12.2-14.23.5.2854.jar', 'nogui']
# conf.get_default().region = 'eu'
FORMAT = '%(asctime)-15s %(levelname)-5s %(funcName)-10s %(lineno)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, stream=sys.stdout)

if '.heroku' in os.listdir('./'):
    HEROKU = True
    load_dotenv()
    _bot_token = os.getenv('DISCORD_TOKEN')
    _database_config = {
        'host': os.getenv('HOST'),
        'userid': os.getenv('USER_ID'),
        'password': os.getenv('PASSWORD'),
        'databasename': os.getenv('DATABASE_NAME')
    }
else:
    HEROKU = False
    config = configparser.ConfigParser()
    config.read('config.ini')
    _bot_token = config.get('Bot', 'Token')
    _database_config = dict(config.items('Database'))

intents = discord.Intents.default()
intents.message_content = True

bot = CustomBot()


# TODO:
#  Organize all to a single class
#  Add auto moderation functions
#  Discord role manupulation
#  Implement NLP


@bot.event
async def on_connect():
    logging.info('Running git hash: {}'.format(bot.git_hash))


@bot.event
async def on_ready():
    start = time.process_time()
    logging.info('{0.name} with id: {0.id} is ready on Discord'.format(bot.user))
    async for guild in bot.fetch_guilds():
        logging.info('\tOperating on {} with id: {}'.format(guild.name, guild.id))
    # target_guild: discord.Guild = await bot.fetch_guild(757705485356105749)
    #
    # for channel in await target_guild.fetch_channels():
    #     logging.info(f'Channel: {channel.name}, ID: {channel.id}')
    #
    # target_channel: discord.TextChannel = await bot.fetch_channel(758818983028719627)
    #
    # import datetime
    # with open('text_log.txt', 'w', encoding='utf-8') as log:
    #     async for message in target_channel.history(limit=None, after=datetime.datetime(2021, 4, 1)):
    #         log.write(f'{message.created_at}: '
    #                   f'{message.author.display_name.rjust(16)}: {message.clean_content}\n')
    #
    for client in bot.voice_clients:
        client.disconnect()

    await bot.default_presence()

    try:
        bot.add_cog(Minigame(bot, user_table=bot.fetch_user_tables()[0]))
    except Exception as e:
        logging.error(e)

    bot.add_cog(Music(bot))
    bot.add_cog(SecretHitler(bot))
    bot.add_cog(CodeNames(bot))

    bot.clean_directory()

    bot.admin = await bot.fetch_user(301067535581970434)

    logging.info(os.path.abspath(os.path.dirname(__file__)))
    for item in os.listdir('./'):
        logging.info('\t{}'.format(item))

    end = time.process_time() - start
    logging.info('Elapsed time: {}'.format(end))


@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, error: Exception):
    await bot.admin.send(f'{error}, {ctx.message.guild.name}, {ctx.channel}, {ctx.message.content}')


@bot.command(hidden=True)
async def run(ctx, *, command: str):
    output = subprocess.check_output(command.split()).strip().decode('ascii')
    await ctx.send(output)


'''
START OF MINECRAFT COMMANDS
'''


@bot.group(hidden=True)
async def minecraft(ctx):
    if ctx.invoked_subcommand:
        return
    if bot.minecraft_process and bot.minecraft_process.returncode != 0:
        await ctx.send('Server running...')
    else:
        await ctx.send('Starting server...')
        try:
            bot.minecraft_process = subprocess.Popen(JAVA_OPTIONS,
                                                     stdin=subprocess.PIPE,
                                                     stdout=sys.stdout,
                                                     stderr=sys.stdout,
                                                     cwd='minecraft01')
        except Exception as e:
            print(e)
        bot.ssh_tunnel = ngrok.connect(25565, 'tcp')
        await ctx.send(f'Server address: {bot.ssh_tunnel}')


@minecraft.command()
async def status(ctx):
    if bot.minecraft_process and bot.minecraft_process.returncode != 0:
        await ctx.send('Server running...')
    else:
        await ctx.send('Server offline')


@minecraft.command()
async def connect(ctx):
    if bot.ssh_tunnel is None:
        bot.ssh_tunnel = ngrok.connect(25565, 'tcp')
    await ctx.send(f'Server address: {bot.ssh_tunnel.public_url}')


@minecraft.command()
async def disconnect(ctx):
    if bot.ssh_tunnel:
        ngrok.disconnect(bot.ssh_tunnel.public_url)
        bot.ssh_tunnel = None
        await ctx.send('Tunnel closed')
    else:
        await ctx.send('No tunnel open')


@minecraft.command()
async def address(ctx):
    if bot.ssh_tunnel:
        await ctx.send(f'Server address: {bot.ssh_tunnel.public_url}')
    else:
        await ctx.send('No tunnel open')


@minecraft.command()
async def stop(ctx):
    await ctx.send('Stopping now...')
    bot.minecraft_process.communicate(input=b'stop')
    bot.minecraft_process.wait()
    await ctx.send('Stopped')
    bot.save_server()
    await ctx.send('World saved')
    ngrok.disconnect(bot.ssh_tunnel.public_url)


@minecraft.command()
async def save(ctx):
    await ctx.send('Manual save started...')
    bot.save_server()
    await ctx.send('World saved')


'''
END OF MINECRAFT COMMANDS
'''


@bot.command(help='Rolls dice. <number of dice> <number of sides>')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(help='FATE dice')
async def fate(ctx, modifier: int = 0):
    dice = [
        random.choice([-1, -1, 0, 0, 1, 1])
        for _ in range(4)
    ]
    sum_ = sum(dice) + modifier
    if sum_ > 8:
        sum_ = 8
    elif sum_ < -4:
        sum_ = -4
    modifier = '{}'.format('+{}'.format(modifier) if modifier > 0 else modifier) if modifier != 0 else ''
    await ctx.send('{} {} = {} **{}**'.format(', '.join(map(str, dice)), modifier, sum_, CustomBot.adj[sum_]))


@bot.command(hidden=True)
async def del_bot(ctx, limit=50):
    def is_me(m):
        return m.author == bot.user

    deleted = await ctx.channel.purge(limit=limit, check=is_me, bulk=False)
    await ctx.send(f'Deleted my {len(deleted)} message(s).', delete_after=5.0)


@bot.command(hidden=True)
@commands.has_permissions(administrator=True)
async def delete(ctx, limit: int = None):
    if limit is None:
        limit = 50
    if limit > 50:
        limit = 50
    deleted = await ctx.channel.purge(limit=limit)
    await ctx.send(f'Deleted {len(deleted)} message(s).', delete_after=5.0)


@bot.command(hidden=True)
async def ping(ctx):
    delta = datetime.datetime.utcnow() - ctx.message.created_at
    await ctx.send("Elapsed seconds: {} | v{}".format(delta.total_seconds(), bot.git_hash), delete_after=3.0)


@bot.check
def check_heroku_availability(ctx):
    if HEROKU:
        return ctx.command.qualified_name not in CustomBot.heroku_banned_commands
    return True


def exit_handler():
    if bot.minecraft_process:
        bot.minecraft_process.communicate(input=b'stop')
        bot.minecraft_process.wait()
    if bot.ssh_tunnel:
        ngrok.disconnect(bot.ssh_tunnel.public_url)
    bot.save_server()


atexit.register(exit_handler)
bot.run(bot.token)
