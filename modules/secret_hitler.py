import discord
import logging
import math
import random

from enum import Enum
from discord.ext import commands


class Card(Enum):
    liberal = 1
    fascist = 0


class Status(Enum):
    president_start = 0
    president_choosing_chancellor = 1
    chancellor_voting = 2
    president_eliminating = 3
    chancellor_choosing = 4
    president_executing = 5


class SecretHitler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    emojis = {
        'join': u'\u2764',
        'start': u'\u25B6',
        'yes': u'\u2705',
        'no': u'\u274C'
    }

    index_emojis = {
        u'\u0031': 0,
        u'\u0032': 1,
        u'\u0033': 2,
        u'\u0034': 3,
        u'\u0035': 4,
        u'\u0036': 5,
        u'\u0037': 6,
        u'\u0038': 7,
        u'\u0039': 8
    }

    card_emojis = {
        Card.liberal: '\U0001F535',
        Card.fascist: '\U0001F534'
    }

    @commands.command(name='secrethitler')
    async def secret_hitler(self, ctx):
        self.sessions[ctx.guild.id] = Session(self.bot, ctx.guild, ctx.channel)
        _ = await ctx.send('Oyuncular toplanıyor')
        await _.add_reaction(SecretHitler.emojis['join'])
        await _.add_reaction(SecretHitler.emojis['start'])
        self.sessions[ctx.guild.id].last_message = _

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
                        if emoji_submitted == SecretHitler.emojis['start']:
                            logging.info(len(session.last_message.reactions))
                            for _ in message.reactions:
                                if _.emoji == SecretHitler.emojis['join']:
                                    users = await _.users().flatten()
                                    users.remove(self.bot.user)
                                    player_count = users.__len__()
                                    logging.info('Attempted to start game with {} players'.format(len(users)))
                                    if player_count < 1 or player_count > 10:
                                        await session.channel.send('Oyuncu sayısı uyumsuz.')
                                    else:
                                        await session.start(users)
                        elif emoji_submitted == SecretHitler.emojis['join']:
                            pass
                        elif emoji_submitted == SecretHitler.emojis['yes']:
                            await session.chancellor_voting(payload.user_id, 1)
                        elif emoji_submitted == SecretHitler.emojis['no']:
                            await session.chancellor_voting(payload.user_id, -1)
                        elif emoji_submitted in self.index_emojis:
                            if session.status is Status.chancellor_voting:
                                await session.chancellor_choose(payload.user_id, self.index_emojis[emoji_submitted])
                            elif session.status is Status.president_executing:
                                await session.president_execute(payload.user_id, self.index_emojis[emoji_submitted])
            else:
                for session in self.sessions.values():
                    if payload.user_id in session.players:
                        if session.status == Status.president_eliminating:
                            if emoji_submitted == SecretHitler.card_emojis[Card.liberal]:
                                await session.chancellor_choose_card(Card.liberal)
                            if emoji_submitted == SecretHitler.card_emojis[Card.fascist]:
                                await session.chancellor_choose_card(Card.fascist)
                        elif session.status == Status.chancellor_choosing:
                            if emoji_submitted == SecretHitler.card_emojis[Card.liberal]:
                                await session.play_card(Card.liberal)
                            if emoji_submitted == SecretHitler.card_emojis[Card.fascist]:
                                await session.play_card(Card.fascist)
                        break
        except Exception as e:
            logging.error(e)

    '''
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return
        guild_id = reaction.message.guild.id
        if self.sessions.get(guild_id) is None:
            return
        if reaction.message.id == self.sessions[guild_id].last_message.id:
            if reaction.emoji == SecretHitler.emojis['join']:
                return self.sessions.get(guild_id).players.remove(user.id)
    '''


class Session:
    def __init__(self, bot, guild, channel):
        self.bot = bot
        self.channel = channel
        self.guild = guild
        self.last_message = None

        self.players = []
        self.president = None
        self.president_index = 0
        self.chancellor = None
        self.hitler = None

        self.president_cards = []
        self.deck = []
        self.vote_box = {}
        self.policy_table = {
            Card.liberal: 0,
            Card.fascist: 0,
            'election_tracker': 0
        }

        self.status = Status.president_start

    def reset_deck(self):
        self.deck = random.sample([1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 17)

    async def start(self, users):
        self.reset_deck()
        for _ in users:
            self.players.append(Player(_, 'liberal'))
        num_of_fascists = math.ceil(len(users) * 0.5 - 1)
        if num_of_fascists == 0:
            num_of_fascists = 1
        for _ in random.choices(self.players, k=num_of_fascists):
            _.identity = 'fascist'
        self.hitler = random.choice([_ for _ in self.players if _.identity == 'fascist'])
        self.hitler.identity = 'hitler'
        self.president = random.choice(self.players)
        self.players.remove(self.president)
        self.players.insert(0, self.president)
        await self.channel.send('Cumhurbaşkanlığı sırası: {}'.format(', '.join([_.name for _ in self.players])))

        if len(self.players) > 5:
            self.policy_table[Card.fascist] = self.policy_table[Card.fascist] + 1

        await self.send_identities()
        await self.president_choosing_chancellor()

    async def send_identities(self):
        for _ in self.players:
            if _.identity == 'liberal':
                await _.user.send('Liberalsin.')
            elif _.identity == 'fascist':
                await _.user.send('Faşistsin.')
                if len(self.players) < 6:
                    await _.user.send('Hitler {}.'.format(self.hitler.name))
            elif _.identity == 'hitler':
                await _.user.send('Hitler\'sin.')
                await _.user.send('Faşistler: '
                                  .format(', '.join([_.name for _ in self.players if _.identity == 'fascist'])))

    async def next_president(self):
        self.president_index = (self.president_index + 1) % len(self.players)
        self.president = self.players[self.president_index]
        await self.president_choosing_chancellor()
        self.status = Status.president_choosing_chancellor

    async def play_card(self, card):
        if card.value not in self.president_cards:
            return
        if card == Card.fascist:
            await self.channel.send('Başbakan {}, faşist bir politika yürürlüğe koydu.'.format(self.chancellor.name))
            self.policy_table[Card.fascist] = self.policy_table[Card.fascist] + 1
        elif card == Card.liberal:
            await self.channel.send('Başbakan {}, liberal bir politika yürürlüğe koydu.'.format(self.chancellor.name))
            self.policy_table[Card.liberal] = self.policy_table[Card.liberal] + 1
        await self.send_policy_table()
        await self.check_events()

    async def play_card_from_top(self):
        _ = self.policy_table[Card(self.deck[0])]
        _ = _ + 1
        await self.channel.send('{} politika yürürlülüğe koyuldu.'
                                .format('Faşist' if Card(self.deck[0]) == Card.fascist else 'Liberal'))
        del (self.deck[0])
        await self.send_policy_table()
        await self.check_events()

    async def send_policy_table(self):
        await self.channel.send('Liberal politikalar: {}'.format(self.policy_table[Card.liberal]))
        await self.channel.send('Faşist politikalar: {}'.format(self.policy_table[Card.fascist]))

    async def check_events(self):
        if self.policy_table[Card.fascist] == 6:
            await self.declare_win(Card.fascist)
        elif self.policy_table[Card.liberal] == 5:
            await self.declare_win(Card.liberal)
        elif self.policy_table[Card.fascist] == 3:
            await self.policy_peek()
        elif self.policy_table[Card.fascist] == 4:
            await self.president_executing()
        else:
            await self.next_president()

    async def policy_peek(self):
        await self.president.user.send('Sonraki üç kart: {}'.format(', '.join([Card(_).name for _ in self.deck[0:3]])))
        await self.next_president()

    async def declare_win(self, party):
        if party == Card.fascist:
            await self.channel.send('Faşistler kazandı.')
        elif party == Card.liberal:
            await self.channel.send('Liberaller kazandı.')

    async def president_executing(self):
        self.last_message = await self.channel.send('Cumhurbaşkanı {} birisini idam edecek.\n'
                                                    '{}'.format(self.president.name,
                                                                self.players_without_president_formatted))
        await self.add_indexed_reaction()
        self.status = Status.president_executing

    async def president_execute(self, author, user):
        user = self.players[user]
        if self.president == author and self.status is Status.president_executing:
            for _ in self.players:
                if _.identity == 'hitler':
                    await self.channel.send('Hitler öldürüldü.')
                    await self.declare_win(Card.fascist)
                elif _ == user:
                    await self.channel.send('{} öldürüldü.'.format(_.name))
                    self.players.remove(_)

    async def president_choosing_chancellor(self):
        self.last_message = await self.channel.send('Cumhurbaşkanı {}, Şansolyeni seç.\n'
                                                    '{}'.format(self.president.name,
                                                                self.players_without_president_formatted))
        await self.add_indexed_reaction()
        self.status = Status.president_choosing_chancellor

    async def add_indexed_reaction(self):
        for _ in range(len(self.players)):
            await self.last_message.add_reaction(list(SecretHitler.index_emojis.values())[_])

    @property
    def players_without_president(self):
        return [_ for _ in self.players if _ != self.president]

    @property
    def players_without_president_formatted(self):
        return ' '.join(['{} {}'.format(i + 1, _) for i, _ in enumerate(self.players_without_president)])

    async def chancellor_choose(self, author, user):
        user = self.players[user]
        if self.president == author or self.status == Status.president_choosing_chancellor:
            for _ in self.players:
                if _ == user and self.president != user and self.chancellor != user:
                    self.chancellor = _
                    _ = await self.channel.send('Şansolye {} için açık oylama:'
                                                ' !ja !nein'.format(user.name))
                    await _.add_reaction(SecretHitler.emojis['yes'])
                    await _.add_reaction(SecretHitler.emojis['no'])
                    self.last_message = _
                    break
        self.status = Status.chancellor_voting

    async def chancellor_voting(self, user_id, vote):
        if len([_ for _ in self.players if _ == user_id]) == 0:
            return logging.info('User not in self.players')
        if self.status is not Status.chancellor_voting:
            return logging.info('Status is wrong')
        self.vote_box[user_id] = vote
        if len(self.vote_box) == len(self.players):
            if sum(self.vote_box.values()) > 0:
                if self.chancellor.identity == 'hitler' and self.policy_table[Card.fascist] > 2:
                    await self.channel.send('Hitler şansolye seçildi.')
                    await self.declare_win(Card.fascist)
                else:
                    await self.president_eliminate_card()
                    self.policy_table['election_tracker'] = 0
                    self.status = Status.president_eliminating
            else:
                await self.channel.send('Şansolye {} reddedildi.'.format(self.chancellor.user.name))
                self.policy_table['election_tracker'] = self.policy_table['election_tracker'] + 1
                if self.policy_table['election_tracker'] == 3:
                    await self.channel.send('Üç kez seçim reddedildi. En tepedeki politika oynanıyor.')
                    await self.play_card_from_top()
                else:
                    await self.next_president()
            self.vote_box.clear()

    async def president_eliminate_card(self):
        if len(self.deck) < 3:
            self.reset_deck()
            await self.channel.send('Deste karıştırıldı.')
        self.president_cards.clear()
        self.president_cards.extend(self.deck[0:3])
        _ = await self.president.user.send('Bir kartı ele')
        await _.add_reaction(SecretHitler.card_emojis[Card.liberal])
        await _.add_reaction(SecretHitler.card_emojis[Card.fascist])
        await self.president.user.send('Kartlar: {}'.format(', '.join([Card(_).name for _ in self.president_cards])))
        self.last_message = _
        del (self.deck[0:3])

    async def chancellor_choose_card(self, card):
        self.president_cards.remove(card.value)
        _ = await self.chancellor.user.send('Kartı seç')
        await _.add_reaction(SecretHitler.card_emojis[Card.liberal])
        await _.add_reaction(SecretHitler.card_emojis[Card.fascist])
        await self.chancellor.user.send('Kartlar: {}'.format(', '.join([Card(_).name for _ in self.president_cards])))
        self.last_message = _
        self.status = Status.chancellor_choosing


class Player:
    def __init__(self, user, identity):
        self.user = user
        self.identity = identity

    def __eq__(self, other):
        if isinstance(other, discord.User):
            return self.user == other
        elif isinstance(other, discord.Member):
            return self.user == other
        elif isinstance(other, int):
            return self.user.id == other
        else:
            return NotImplemented

    @property
    def name(self):
        return self.user.name

    @property
    def id(self):
        return self.user.id


if __name__ == '__main__':
    pass
