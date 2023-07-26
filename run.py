import atexit
import configparser
import datetime
import logging
import os
import random
import subprocess
import sys
import time
import nest_asyncio
import asyncio
import re
import discord
import discord.ext.commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pyngrok import conf, ngrok


pathtogpt = os.path.join(os.getcwd(), "gpt4free")
sys.path.append(pathtogpt)

from gpt4free import g4f
from gpt4free.g4f import Provider

nest_asyncio.apply()
print(g4f.Provider.Ails.params)

from misterhandy import CustomBot

# GIT_PATH = 'git'
# JAVA_PATH = '/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java'
# JAVA_OPTIONS = [JAVA_PATH, '-Xmx6048M', '-Xms1024M', '-jar', 'forge-1.12.2-14.23.5.2854.jar', 'nogui']
# conf.get_default().region = 'eu'
FORMAT = "%(asctime)-15s %(levelname)-5s %(funcName)-10s %(lineno)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO, stream=sys.stdout)

load_dotenv()
_bot_token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

CHUNK_SIZE = 2000

BANNED_WORDS = [
    r"\bmalum\w*\b",
    r"\w*yar*ak",
    r"\bkarı",
    r"\bbayan",
    r"\bobjektif",
    r"\bjahrein",
    r"\btoksik",
    r"\bayak",
    r"\bakp",
]

bot = CustomBot(intents)


@bot.event
async def on_ready():
    start = time.process_time()
    logging.info("{0.name} with id: {0.id} is ready on Discord".format(bot.user))

    async for guild in bot.fetch_guilds():
        logging.info("\tOperating on {} with id: {}".format(guild.name, guild.id))

    end = time.process_time() - start
    logging.info("Elapsed time: {}".format(end))


def split_string(text, chunk_size):
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


async def generate_response(prompt):
    # post = f"Answer the following question acting as Mister Handy from Fallout 4. {prompt}"
    post = f"{prompt}"
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.Model.gpt_4,
            provider=Provider.Bing,
            messages=[{"role": "user", "content": post}],
            stream=False,
        )
        response = response[0:2000]
    except:
        response = None
    if response:
        return response
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.Model.gpt_35_turbo,
            provider=Provider.DeepAi,
            messages=[{"role": "user", "content": post}],
            stream=False,
        )
        response = response[0:2000]
    except:
        response = None

    # split_string(response, CHUNK_SIZE)
    return response


async def generate_response_fast(prompt):
    messages = []
    messages.append({"role": "user", "content": prompt})
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.Model.gpt_35_turbo,
            provider=Provider.DeepAi,
            messages=messages,
            stream=False,
        )
        if response:
            response = response[0:2000]
    except:
        response = None
    # split_string(response, CHUNK_SIZE)
    return response


@bot.command()
async def meme(ctx: commands.Context):
    response = await generate_response_fast(
        f"Write a sarcastic joke against the decision about banning a discord bot \
          that has command that writes jokes from recent conversations because it shares discord messages with third party \
          Write in Turkish"
    )

    return await ctx.send(response)
    message = ctx.message
    if message.mentions:
        for mention in message.mentions:
            message.content = message.content.replace(
                f"<@{mention.id}>", f"{mention.display_name}"
            )
    messages = [message async for message in ctx.channel.history(limit=50)]
    post = []
    for message in messages:
        if message.author == bot.user:
            continue
        post.append(f"{message.author} said: {message.content}")
    post.reverse()
    post = "\n".join(post)
    print(post)

    async with ctx.channel.typing():
        response = await generate_response_fast(
            f"Write a joke in Turkish based on the following conversation on discord. Post only the joke. \n [Conversation] {post}"
        )
    print(response)

    if response is None or not len(response) > 0:
        await ctx.send("Zort")
    else:
        await ctx.send(response, suppress_embeds=True)


@bot.command()
async def chat(ctx: commands.Context, *, prompt: str):
    message = ctx.message
    if message.mentions:
        for mention in message.mentions:
            message.content = message.content.replace(
                f"<@{mention.id}>", f"{mention.display_name}"
            )

    prompt = message.content
    print(prompt)
    async with ctx.channel.typing():
        response = await generate_response(prompt)
    print(response)

    if response is not None:
        await ctx.send(response, suppress_embeds=True)
    else:
        await ctx.send("Zort")


@bot.command()
async def ask(ctx: commands.Context, *, prompt: str):
    message = ctx.message
    if message.mentions:
        for mention in message.mentions:
            message.content = message.content.replace(
                f"<@{mention.id}>", f"{mention.display_name}"
            )

    prompt = message.content
    print(prompt)
    async with ctx.channel.typing():
        response = await generate_response(prompt)
    print(response)

    if response is not None:
        await ctx.send(response, suppress_embeds=True)
    else:
        await ctx.send("Zort")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    # Find matches using regex in the message content
    found_keywords = []
    for keyword in BANNED_WORDS:
        match = re.search(keyword, message.content, re.IGNORECASE)
        if match:
            found_keywords.append(match.group())
    if len(found_keywords) == 1:
        response = (
            f'"{found_keywords[0]}" yasaklı kelime, {message.author.mention} su iç!'
        )
        await message.channel.send(response)
    elif len(found_keywords) > 1:
        response = f' {", ".join(found_keywords)} yasaklı kelimeler, {message.author.mention} su iç!'
        await message.channel.send(response)


bot.run(_bot_token)  # type: ignore
