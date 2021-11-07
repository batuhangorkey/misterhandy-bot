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

GIT_PATH = 'git'
JAVA_PATH = '/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java'
JAVA_OPTIONS = [JAVA_PATH, '-Xmx6048M', '-Xms1024M', '-jar', 'forge-1.12.2-14.23.5.2854.jar', 'nogui']
conf.get_default().region = 'eu'
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


class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!')
        self.ssh_tunnel: ngrok.NgrokTunnel = None
        self.admin: discord.User = None
        self.minecraft_process: subprocess.Popen = None
        self.minecraft_autosave.start()

    presences = [
        'eternal void',
        'ancient orders',
        'nine mouths',
        'cosmic noise',
        'storms on titan',
        '!play'
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
    heroku_banned_commands = [
        'reset'
    ]

    @property
    def token(self):
        return _bot_token

    @property
    def git_hash(self):
        return self.get_git_version()

    @staticmethod
    def get_git_version():
        if HEROKU:
            return 'heroku'
        else:
            try:
                return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('ascii')
            except WindowsError:
                return 'LocalHost'

    @staticmethod
    def clean_directory():
        for item in os.listdir('./'):
            if item.endswith(('.webm', '.m4a')):
                try:
                    os.remove(item)
                except Exception as error:
                    logging.error(error)
                else:
                    logging.info(f'Successfully deleted {item}')

    @staticmethod
    def save_server():
        process = subprocess.Popen([GIT_PATH, 'add', '-A'], stdin=subprocess.PIPE, stdout=sys.stdout)
        process.wait()
        process = subprocess.Popen([GIT_PATH, 'commit', '-am', 'Update'], stdin=subprocess.PIPE, stdout=sys.stdout)
        process.wait()
        process = subprocess.Popen([GIT_PATH, 'push'], stdin=subprocess.PIPE, stdout=sys.stdout)
        process.wait()

    @staticmethod
    def get_pymysql_connection():
        conn = pymysql.connect(_database_config['host'],
                               _database_config['userid'],
                               _database_config['password'],
                               _database_config['databasename'])
        return conn

    @classmethod
    def fetch_user_tables(cls):
        user_table = {}
        kaiser_points = {}
        conn = cls.get_pymysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM main")
            data = cursor.fetchall()
        conn.close()
        for _, b in data:
            user_table[int(_)] = int(b)
        return user_table, kaiser_points

    @classmethod
    def get_random_playlist(cls):
        conn = cls.get_pymysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT url, dislike, like_count FROM playlist")
                data = cursor.fetchall()
        finally:
            conn.close()
        db_playlist = [t for t in data]
        db_playlist = [(url, int(like / dislike)) for url, dislike, like in db_playlist]
        return db_playlist

    async def default_presence(self):
        try:
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                 name=random.choice(CustomBot.presences)),
                                       status=self.git_hash)
        except Exception as e:
            logging.error(e)

    @tasks.loop(minutes=15)
    async def minecraft_autosave(self):
        self.save_server()


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
