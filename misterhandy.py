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
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pyngrok import conf, ngrok


class CustomBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)
        self.ssh_tunnel: ngrok.NgrokTunnel = None
        self.admin: discord.User = None
        self.minecraft_process: subprocess.Popen = None

    presences = [
        "eternal void",
        "ancient orders",
        "nine mouths",
        "cosmic noise",
        "storms on titan",
        "!play",
    ]
    adj = {
        8: "Efsane",
        7: "İnanılmaz",
        6: "Şahane",
        5: "Muhteşem",
        4: "Harika",
        3: "Baya iyi",
        2: "İyi",
        1: "Eh",
        0: "Düz",
        -1: "Dandik",
        -2: "Kötü",
        -3: "Rezalet",
        -4: "Felaket",
    }
    heroku_banned_commands = ["reset"]

    @staticmethod
    def clean_directory():
        for item in os.listdir("./"):
            if item.endswith((".webm", ".m4a")):
                try:
                    os.remove(item)
                except Exception as error:
                    logging.error(error)
                else:
                    logging.info(f"Successfully deleted {item}")

    async def default_presence(self):
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=random.choice(CustomBot.presences),
                ),
                status=self.git_hash,
            )
        except Exception as e:
            logging.error(e)
