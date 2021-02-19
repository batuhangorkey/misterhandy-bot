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
        'start': u'\u27A1',
        'yes': u'\u23ED',
        'no': u'\u2714'
    }

    card_emojis = {
        Card.liberal:  '\U0001F535',
        Card.fascist: '\U0001F534'
    }

    @commands.command(name='secrethitler')
    async def secret_hitler(self, ctx):
        self.sessions[ctx.guild.id] = Session(self.bot, ctx.guild, ctx.channel)
        self.sessions[ctx.guild.id].last_message = await ctx.send('Oyuncular toplanıyor')
        await self.sessions[ctx.guild.id].last_message.add_reaction(SecretHitler.emojis['join'])
        await self.sessions[ctx.guild.id].last_message.add_reaction(SecretHitler.emojis['start'])

    @commands.command(name='seç')
    async def choose(self, ctx):
        if len(ctx.message.mentions) > 0:
            await self.sessions.get(ctx.guild.id).chancellor_choose(ctx.message.mentions[0])

    @commands.command(name='ja')
    async def yes(self, ctx):
        await self.sessions[ctx.guild.id].chancellor_voting(ctx.author, 1)

    @commands.command(name='nein')
    async def no(self, ctx):
        await self.sessions[ctx.guild.id].chancellor_voting(ctx.author, -1)

    @commands.command()
    async def shoot(self, ctx, user_id):
        await self.sessions[ctx.guild.id].execution(ctx.author, user_id)

    @choose.before_invoke
    @yes.before_invoke
    @no.before_invoke
    @shoot.before_invoke
    async def ensure_session(self, ctx):
        if self.sessions.get(ctx.guild.id) is None:
            raise commands.CommandError('No session with that guild id.')
        if ctx.author.id not in [_.id for _ in self.sessions.get(ctx.guild.id).players]:
            raise commands.CommandError('User not in session.')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if isinstance(reaction.message.channel, discord.TextChannel):
            logging.info('Reaction in text channel')
            guild_id = reaction.message.guild.id
            if self.sessions.get(guild_id) is not None:
                if reaction.message.id == self.sessions[guild_id].last_message.id:
                    if reaction.emoji == SecretHitler.emojis['start']:
                        for _ in reaction.message.reactions:
                            if _.emoji == SecretHitler.emojis['join']:
                                users = await _.users().flatten()
                                users.remove(self.bot.user)
                                player_count = users.__len__()
                                logging.info('Attempted to start game with {} players'.format(users.__len__()))
                                if player_count < 5 or player_count > 10:
                                    await reaction.message.channel.send('Oyuncu sayısı uyumsuz.')
                                else:
                                    await self.sessions[guild_id].start(users)
                    elif reaction.emoji == SecretHitler.emojis['join']:
                        pass
        else:
            for session in self.sessions:
                if user.id in session.players:
                    session = self.sessions[session.guild.id]
                    if session.status == Status.president_eliminating:
                        if reaction.emoji == SecretHitler.card_emojis[Card.liberal]:
                            session.presdent_cards.remove(Card.liberal.value)
                        if reaction.emoji == SecretHitler.card_emojis[Card.fascist]:
                            session.presdent_cards.remove(Card.fascist.value)
                        session.chancellor_choose_card()
                    elif session.status == Status.chancellor_choosing:
                        if reaction.emoji == SecretHitler.card_emojis[Card.liberal]:
                            session.play_card(Card.liberal)
                        if reaction.emoji == SecretHitler.card_emojis[Card.fascist]:
                            session.play_card(Card.fascist)
                    await reaction.message.delete()
                    break

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
            logging.info(type(_))
            self.players.append(Player(_, 'liberal'))
        num_of_fascists = math.ceil(users.__len__() * 0.5 - 2)
        for _ in random.choices(self.players, k=num_of_fascists):
            _.identity = 'fascist'
        random.choice([_ for _ in self.players if _.identity == 'liberal']).identity = 'hitler'
        self.president_index = random.randrange(0, len(self.players))
        self.president = self.players[self.president_index]

        await self.send_identities()
        await self.president_choosing_chancellor()

    async def send_identities(self):
        for _ in self.players:
            if _.identity == 'liberal':
                await _.user.send('Sen liberalsin.')
            elif _.identity == 'fascist':
                await _.user.send('Sen faşistsin.')
            elif _.identity == 'hitler':
                await _.user.send('Sen Hitler\'sin.')

    async def next_president(self):
        self.president_index = (self.president_index + 1) % len(self.players)
        self.president = self.players[self.president_index]
        await self.president_choosing_chancellor()
        self.status = Status.president_choosing_chancellor

    async def play_card(self, card):
        if card == Card.fascist:
            await self.channel.send('Şansolye {} faşist bir politika yürürlüğe koydu.'.format(self.chancellor.name))
            self.policy_table[Card.fascist] = self.policy_table[Card.fascist] + 1
        elif card == Card.liberal:
            await self.channel.send('Şansolye {} liberal bir politika yürürlüğe koydu'.format(self.chancellor.name))
            self.policy_table[Card.liberal] = self.policy_table[Card.liberal] + 1
        await self.check_events()

    async def play_card_from_top(self):
        _ = self.policy_table[Card(self.deck[0])]
        _ = _ + 1
        self.channel.send('{} politika yürürlülüğe koyuldu.'
                          .format('Faşist' if Card(self.deck[0]) == Card.fascist else 'Liberal'))
        del (self.deck[0])
        await self.check_events()

    async def check_events(self):
        if self.policy_table[Card.fascist] == 6:
            await self.declare_win(Card.fascist)
        elif self.policy_table[Card.liberal] == 5:
            await self.declare_win(Card.liberal)
        elif self.policy_table[Card.fascist] == 3:
            await self.policy_peek()
        elif self.policy_table[Card.fascist] == 4:
            await self.channel.send('Başbakan {} birisini idam edecek. !shoot <user ID>'.format(self.president.name))
            self.status = Status.president_executing
        else:
            await self.next_president()

    async def policy_peek(self):
        await self.president.user.send('Sonraki üç kart: {}'.format(', '.join([Card(_).name for _ in self.deck[0:3]])))
        await self.next_president()

    async def execution(self, user_, user_id):
        if self.status is not Status.president_executing:
            return
        user = self.guild.get_member(user_id)
        if self.president == user_:
            for _ in self.players:
                if _.identity == 'hitler':
                    await self.channel.send('Hitler öldürüldü.')
                    await self.declare_win(Card.fascist)
                elif _.user == user:
                    await self.channel.send('{} öldürüldü.'.format(_.name))
                    self.players.remove(_)

    async def declare_win(self, party):
        if party == Card.fascist:
            await self.channel.send('Faşistler kazandı.')
        elif party == Card.liberal:
            await self.channel.send('Liberaller kazandı.')

    async def chancellor_choose(self, user):
        for _ in self.players:
            if user == _.user:
                self.chancellor = _
                await self.channel.send('Şansolye {} için açık oylama:'
                                        ' !ja !nein'.format(user.name))
        self.status = Status.chancellor_voting

    async def chancellor_voting(self, user, vote):
        if user in self.players:
            logging.info('User in self.players')
        if not self.check_player(user):
            return logging.info('User not in self.players')
        if self.status is not Status.chancellor_voting:
            return logging.info('Status is wrong')
        self.vote_box[user] = vote
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

    async def president_choosing_chancellor(self):
        await self.channel.send('Başbakan {}, Şansolyeni seç: !seç @<isim>'.format(self.president.name))
        self.status = Status.president_choosing_chancellor

    async def president_eliminate_card(self):
        self.president_cards.extend(self.deck[0:3])
        _ = await self.president.user.send('Bir kartı ele')
        await _.add_reaction(SecretHitler.card_emojis[Card.liberal])
        await _.add_reaction(SecretHitler.card_emojis[Card.fascist])
        await self.president.user.send('Kartlar: {}'.format(', '.join([Card(_).name for _ in self.president_cards])))
        del (self.deck[0:3])
        await self.chancellor_choose_card()

    async def chancellor_choose_card(self):
        _ = self.chancellor.user.send('Kartı seç')
        await _.add_reaction(SecretHitler.card_emojis[Card(self.president_cards[0])])
        await _.add_reaction(SecretHitler.card_emojis[Card(self.president_cards[1])])
        self.last_message = _

    def check_player(self, user):
        if user in [_.user for _ in self.players]:
            return True
        else:
            return False


class Player:
    def __init__(self, user, identity):
        self.user = user
        self.identity = identity

    def __eq__(self, other):
        if isinstance(other, discord.User):
            return self.user.id == other.id
        return self.user == other

    @property
    def name(self):
        return self.user.name

    @property
    def id(self):
        return self.user.id


if __name__ == '__main__':
    pass
