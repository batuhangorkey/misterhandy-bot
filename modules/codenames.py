import discord
import logging
import math
import random

from enum import Enum, auto
from discord.ext import commands


class Color(Enum):
    RED = auto()
    BLUE = auto()
    NEUTRAL = auto()
    BLACK = auto()


class Status(Enum):
    president_choosing_chancellor = 1
    chancellor_voting = 2
    president_eliminating_card = 3
    chancellor_choosing_card = 4
    president_executing = 5
    president_investigating = 6
    finish: 7


class CodeNames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    word_pool = [
        'Dalga', 'Makara', 'Gaz', 'Saz', 'Tesbih', 'Akım', 'Döviz', 'Kolon', 'Darbe', 'Hücre', 'Paraşüt', 'Köstebek',
        'Alay', 'Tıp', 'Nişan', 'Nemrut', 'Etiket', 'Baskı', 'Roma', 'Hayalet', 'Kaş', 'Bomba', 'Pamuk', 'Boğaz',
        'Makas'
    ]

    emojis = {
        'join_red': '\U0001F534',
        'join_red_operator': '1\N{COMBINING ENCLOSING KEYCAP}',
        'join_blue': '\U0001F535',
        'join_blue_operator': '2\N{COMBINING ENCLOSING KEYCAP}',
        'start': u'\u25B6',
    }

    index_emojis = {}
    for _ in range(10):
        index_emojis['{}\N{COMBINING ENCLOSING KEYCAP}'.format(_)] = _

    @commands.command(name='codenames')
    async def code_names(self, ctx):
        new_session = Session(self.bot, ctx.channel)
        self.sessions[ctx.guild.id] = new_session
        message = await ctx.send('Oyuncular toplanıyor')
        for _ in self.emojis:
            await message.add_reaction(_)
        new_session.last_message = message

    @commands.command()
    async def give(self, ctx, *, word, tries: int):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            if self.bot.user.id == payload.user_id:
                return
            emoji_submitted = payload.emoji.name
            if payload.guild_id is not None:
                guild_id = payload.guild_id
                if self.sessions.get(guild_id) is not None:
                    session = self.sessions[guild_id]
                    if payload.message_id == session.last_message.id:
                        message = await session.channel.fetch_message(payload.message_id)
                        if emoji_submitted == self.emojis['start']:
                            players = {}
                            for _ in message.reactions:
                                users = await _.users().flatten()
                                users.remove(self.bot.user)
                                if _.emoji == self.emojis['join_red']:
                                    players['red_team'] = users
                                if _.emoji == self.emojis['join_red_operator']:
                                    players['red_operators'] = users
                                if _.emoji == self.emojis['join_blue']:
                                    players['blue_team'] = users
                                if _.emoji == self.emojis['join_blue_operator']:
                                    players['blue_operators'] = users
                            await session.start(players)
                        if payload.user_id in session.players:
                            if emoji_submitted == self.emojis['yes']:
                                await session.chancellor_vote(payload.user_id, 1)
                            elif emoji_submitted == self.emojis['no']:
                                await session.chancellor_vote(payload.user_id, -1)
                            elif emoji_submitted in self.index_emojis:
                                if session.president == payload.user_id:
                                    if session.status == Status.president_executing:
                                        await session.president_execute(self.index_emojis[emoji_submitted])
                                    elif session.status == Status.president_choosing_chancellor:
                                        await session.chancellor_choose(self.index_emojis[emoji_submitted])
                                    elif session.status == Status.president_investigating:
                                        await session.investigate(self.index_emojis[emoji_submitted])
            else:
                '''
                DM Channel
                '''
        except Exception as e:
            logging.error(e)


class Session:
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel

        self.last_message = None

        self.players = []
        self.words = []

    @staticmethod
    def get_word_table(word_pool):
        word_table = ''
        i = 1
        for k, element in enumerate(word_pool, 1):
            if k == 11 or k == 22:
                i += 1
            word_table += '{}. {}'.format(i, element).ljust(20)
            if not k % 5:
                word_table += '\n'
            i += 1
        return word_table

    async def start(self, **kwargs):
        self.players.extend([Player(_, Color.RED, False) for _ in kwargs['red_team']])
        self.players.extend([Player(_, Color.RED, True) for _ in kwargs['red_operators']])
        self.players.extend([Player(_, Color.BLUE, False) for _ in kwargs['blue_team']])
        self.players.extend([Player(_, Color.BLUE, True) for _ in kwargs['blue_operators']])

        if random.getrandbits(1):
            starting_team = Color.RED
            red_word_count = 9
            blue_word_count = 8
        else:
            starting_team = Color.BLUE
            red_word_count = 8
            blue_word_count = 9

        raw_words = random.sample(CodeNames.word_pool, k=25)
        self.words.extend([Word(_, Color.RED) for _ in raw_words[0:red_word_count]])
        del (raw_words[0:red_word_count])
        self.words.extend([Word(_, Color.BLUE) for _ in raw_words[0:blue_word_count]])
        del (raw_words[0:blue_word_count])
        self.words.extend([Word(_, Color.NEUTRAL) for _ in raw_words[0:7]])
        del (raw_words[0:7])
        self.words.extend(raw_words[0])
        del (raw_words[0])
        random.shuffle(self.words)

        word_list = self.get_word_table(raw_words)

        await self.channel.send('Sıra {} takımda.\n'
                                '```{}```'.format('kırmızı' if starting_team == Color.RED else 'mavi',
                                                  word_list))


class Player:
    def __init__(self, user, team, operator):
        self.user = user
        self.team = team
        self.operator = operator


class Word:
    def __init__(self, word, team):
        self.word = word
        self.team = team

    def __str__(self):
        return self.word
