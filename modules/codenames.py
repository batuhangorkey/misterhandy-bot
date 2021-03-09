import discord
import logging
import random
import itertools

from enum import Enum
from discord.ext import commands


class Color(Enum):
    RED = 'KI'
    BLUE = 'MA'
    NEUTRAL = 'NÖ'
    BLACK = 'SI'


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
        'end': u'\u274C'
    }

    index_emojis = {}
    for _ in range(10):
        index_emojis['{}\N{COMBINING ENCLOSING KEYCAP}'.format(_)] = _

    def get_session(self, guild_id):
        if self.sessions.get(guild_id) is not None:
            return self.sessions.get(guild_id)
        else:
            return None

    @commands.command(name='codenames')
    async def code_names(self, ctx):
        new_session = Session(self.bot, ctx.channel)
        message = await ctx.send('Oyuncular toplanıyor')
        for _ in list(self.emojis.values())[0:5]:
            await message.add_reaction(_)
        new_session.last_message = message
        self.sessions[ctx.guild.id] = new_session

    @commands.command(name='k')
    async def give(self, ctx, tries: int, *, word):
        session = self.get_session(ctx.guild.id)
        logging.info('Word: {} Tries: {}'.format(word, tries))
        await session.add_clue(tries)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            if self.bot.user.id == payload.user_id:
                return
            emoji_submitted = payload.emoji.name
            if payload.guild_id is not None:
                guild_id = payload.guild_id
                if self.sessions.get(guild_id) is not None:
                    session = self.sessions.get(guild_id)
                    if isinstance(session, Session):
                        if payload.message_id == session.last_message.id:
                            message = await session.channel.fetch_message(payload.message_id)
                            if emoji_submitted == self.emojis['start']:
                                players = {}
                                for _ in message.reactions:
                                    users = await _.users().flatten()
                                    users.remove(self.bot.user)
                                    if _.emoji == self.emojis['join_red']:
                                        players['red_team'] = [Player(_, Color.RED, False) for _ in users]
                                    if _.emoji == self.emojis['join_red_operator']:
                                        players['red_operators'] = [Player(_, Color.RED, True) for _ in users]
                                    if _.emoji == self.emojis['join_blue']:
                                        players['blue_team'] = [Player(_, Color.BLUE, False) for _ in users]
                                    if _.emoji == self.emojis['join_blue_operator']:
                                        players['blue_operators'] = [Player(_, Color.BLUE, True) for _ in users]
                                await session.start(**players)
                            '''
                            Session Check
                            '''
                            if emoji_submitted in self.index_emojis:
                                if session.team_turn == Color.RED:
                                    logging.info('Reds turn.')
                                    if payload.user_id in session.players['red_team']:
                                        logging.info('User in red team')
                                        if payload.event_type == 'REACTION_ADD':
                                            await session.add(self.index_emojis[emoji_submitted])
                                        if payload.event_type == 'REACTION_REMOVE':
                                            await session.remove()
                                elif session.team_turn == Color.BLUE:
                                    logging.info('Blues turn.')
                                    if payload.user_id in session.players['blue_team']:
                                        if payload.event_type == 'REACTION_ADD':
                                            await session.add(self.index_emojis[emoji_submitted])
                                        if payload.event_type == 'REACTION_REMOVE':
                                            await session.remove()
            else:
                '''
                DM Channel
                '''
        except Exception as e:
            logging.error(e)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if self.bot.user.id == payload.user_id:
            return
        emoji_submitted = payload.emoji.name
        if payload.guild_id is not None:
            guild_id = payload.guild_id
            if self.sessions.get(guild_id) is not None:
                session = self.sessions.get(guild_id)
                if isinstance(session, Session):
                    if payload.message_id == session.last_message.id:
                        '''
                        Session Check
                        '''
                        if emoji_submitted in self.index_emojis:
                            if session.team_turn == Color.RED:
                                logging.info('Reds turn.')
                                if payload.user_id in session.players['red_team']:
                                    logging.info('User in red team')
                                    if payload.event_type == 'REACTION_ADD':
                                        await session.add(self.index_emojis[emoji_submitted])
                                    if payload.event_type == 'REACTION_REMOVE':
                                        await session.remove()
                            elif session.team_turn == Color.BLUE:
                                logging.info('Blues turn.')
                                if payload.user_id in session.players['blue_team']:
                                    if payload.event_type == 'REACTION_ADD':
                                        await session.add(self.index_emojis[emoji_submitted])
                                    if payload.event_type == 'REACTION_REMOVE':
                                        await session.remove()
        else:
            '''
            DM Channel
            '''


class Session:
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel

        self.last_message = None
        self.turn_message = None

        self.players = {}
        self.words = []

        self.input = Input()
        self.tries = 0
        self.team_turn = None
        self.team_word_count = {
            Color.RED: 0,
            Color.BLUE: 0
        }

    index_table = {}
    i = 1
    for k in range(1, 26):
        while i in [10, 11, 20, 22]:
            i += 1
        index_table[k] = i
        i += 1
    del i
    rev_index_table = dict((k, v) for v, k in index_table.items())

    team_names = {
        Color.RED: 'kırmızı',
        Color.BLUE: 'mavi'
    }

    @property
    def operator_table(self):
        return self.get_word_table(self.words, True)

    @property
    def agent_table(self):
        return self.get_word_table(self.words)

    @staticmethod
    def get_word_table(word_pool, operator=False):
        word_table = ''
        for k, element in enumerate(word_pool, 1):
            if operator:
                word_table += '{}. {} ({})'.format(str(Session.index_table[k]).rjust(2),
                                                   str(element).ljust(10),
                                                   element.team.value).ljust(20)
            else:
                revealed_str = '{}'.format(' ({})'.format(element.team.value) if element.revealed else '')
                word_table += '{}. {}{}'.format(str(Session.index_table[k]).rjust(2),
                                                str(element).ljust(10), revealed_str).ljust(20)
            if not k % 5:
                word_table += '\n'
        logging.info('Requested table: {}'.format(word_table))
        return word_table

    async def start(self, **kwargs):
        self.players.update(**kwargs)
        self.team_turn = Color.RED if random.getrandbits(1) else Color.BLUE
        if self.team_turn == Color.RED:
            self.team_word_count[Color.RED] = 9
            self.team_word_count[Color.BLUE] = 8
        else:
            self.team_word_count[Color.RED] = 8
            self.team_word_count[Color.BLUE] = 9

        raw_words = random.sample(CodeNames.word_pool, k=25)
        self.words.extend([Word(_, Color.RED) for _ in raw_words[0:self.team_word_count[Color.RED]]])
        del (raw_words[0:self.team_word_count[Color.RED]])
        self.words.extend([Word(_, Color.BLUE) for _ in raw_words[0:self.team_word_count[Color.BLUE]]])
        del (raw_words[0:self.team_word_count[Color.BLUE]])
        self.words.extend([Word(_, Color.NEUTRAL) for _ in raw_words[0:7]])
        del (raw_words[0:7])
        self.words.extend([Word(raw_words[0], Color.BLACK)])
        del raw_words
        random.shuffle(self.words)
        self.turn_message = await self.channel.send('Sıra {} takımda.'.format(self.team_names[self.team_turn]))
        self.last_message = await self.channel.send('```{}```'.format(self.agent_table))
        for operator in itertools.chain(self.players['red_operators'], self.players['blue_operators']):
            await operator.send('```fix\n{}\n```'.format(self.operator_table))

    async def end_turn(self):
        if self.team_turn == Color.RED:
            self.team_turn = Color.BLUE
        else:
            self.team_turn = Color.RED
        await self.turn_message.edit(content='Sıra {} takımda.'.format(self.team_names[self.team_turn]))

    async def add(self, i):
        self.input += i
        logging.info('Input: {}'.format(self.input))
        if self.input:
            await self.reveal(int(self.input))

    async def remove(self):
        self.input.remove()

    async def add_clue(self, tries):
        self.tries = tries
        for emoji in CodeNames.index_emojis.keys():
            await self.last_message.add_reaction(emoji)
        await self.last_message.add_reaction(CodeNames.emojis['end'])

    async def reveal(self, i):
        try:
            logging.info('Revealing word at index: {}'.format(i))
            revealed_word = self.words[self.rev_index_table[i] - 1]
            revealed_word.revealed = True
            if self.last_message is not None:
                await self.last_message.edit(content='```{}```'.format(self.agent_table))
            if revealed_word.team == Color.BLACK:
                if self.team_turn == Color.RED:
                    await self.declare_win(Color.BLUE)
                else:
                    await self.declare_win(Color.RED)
            if self.team_word_count[self.team_turn] == 0:
                await self.declare_win(Color.BLUE)
            if self.team_word_count[self.team_turn] == 0:
                await self.declare_win(Color.RED)
            if revealed_word.team == self.team_turn and self.tries != -2:
                self.tries -= 1
                self.team_word_count[self.team_turn] -= 1
            else:
                await self.end_turn()
        except Exception as e:
            logging.error(e)

    async def declare_win(self, team):
            await self.channel.send('{} takım kazandı.'.format(self.team_names[team].title()))


class Player:
    def __init__(self, user, team, operator):
        self.user = user
        self.team = team
        self.operator = operator

    def __eq__(self, other):
        if isinstance(other, discord.User):
            return self.user == other
        elif isinstance(other, discord.Member):
            return self.user == other
        elif isinstance(other, int):
            return self.user.id == other
        else:
            return NotImplemented

    def __str__(self):
        return self.user.name

    @property
    def send(self):
        return self.user.send


class Word:
    def __init__(self, word, team):
        self.word = word
        self.team = team
        self.revealed = False

    def __str__(self):
        return self.word


class Input:
    def __init__(self, k1=None, k2=None):
        self.k1 = k1
        self.k2 = k2

    def __add__(self, other):
        if self.k1 is not None:
            return Input(k1=self.k1, k2=other)
        else:
            return Input(k1=other * 10)

    def remove(self):
        if self.k1 is not None:
            self.k2 = None
        else:
            self.k1 = None

    def __int__(self):
        return self.k1 + self.k2 if self.k2 else 0

    def __bool__(self):
        return bool(self.k2)
