import discord
import logging
import math
import random

from enum import Enum, auto
from discord.ext import commands


class Policy(Enum):
    liberal = 1
    fascist = 0


class Status(Enum):
    president_choosing_chancellor = auto()
    chancellor_voting = auto()
    president_eliminating_card = auto()
    chancellor_choosing_card = auto()
    president_executing = auto()
    president_investigating = auto()
    veto = auto()
    veto_accepted = auto()
    finish = auto()


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

    index_emojis = {}
    for _ in range(9):
        index_emojis['{}\N{COMBINING ENCLOSING KEYCAP}'.format(_ + 1)] = _

    card_emojis = {
        Policy.liberal: '\U0001F535',
        Policy.fascist: '\U0001F534'
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
                                    player_count = len(users)
                                    logging.info('Attempted to start game with {} players'.format(len(users)))
                                    if player_count < 1 or player_count > 10:
                                        await session.channel.send('Oyuncu sayısı uyumsuz.')
                                    else:
                                        await session.start(users)
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
                for session in self.sessions.values():
                    if payload.user_id in session.players:
                        if session.status == Status.president_eliminating_card:
                            if emoji_submitted == SecretHitler.card_emojis[Policy.liberal]:
                                await session.chancellor_choosing_card(Policy.liberal)
                            if emoji_submitted == SecretHitler.card_emojis[Policy.fascist]:
                                await session.chancellor_choosing_card(Policy.fascist)
                        elif session.status == Status.chancellor_choosing_card:
                            if emoji_submitted == SecretHitler.card_emojis[Policy.liberal]:
                                await session.play_card(Policy.liberal)
                            elif emoji_submitted == SecretHitler.card_emojis[Policy.fascist]:
                                await session.play_card(Policy.fascist)
                            elif emoji_submitted == self.emojis['yes']:
                                if session.status == Status.veto:
                                    await session.status_feedback()
                            elif emoji_submitted == self.emojis['no']:
                                session.status = Status.veto
                                await session.status_feedback()
                        break
        except Exception as e:
            logging.error(e)


class Session:
    def __init__(self, bot, guild, channel):
        self.bot = bot
        self.channel = channel
        self.guild = guild
        self.last_message = None

        self.players = []
        self.president = Player()
        self.president_index = 0
        self.chancellor = Player()
        self.hitler = Player()
        self.last_president = Player()
        self.last_chancellor = Player()

        self.president_cards = []
        self.deck = []
        self.vote_box = {}
        self.policy_table = {
            Policy.liberal: 0,
            Policy.fascist: 0,
            'election_tracker': 0
        }
        self.veto_power = False

        self.status = Status.president_choosing_chancellor

    @property
    def eligible_chancellors(self):
        if len(self.players) > 5:
            return [_ for _ in self.players_without_president if _ != self.last_president and _ != self.last_chancellor]
        else:
            return [_ for _ in self.players_without_president if _ != self.last_chancellor]

    @property
    def players_without_president(self):
        return [_ for _ in self.players if _ != self.president]

    @property
    def fascists(self):
        return [_ for _ in self.players if _.identity == 'fascist']

    @staticmethod
    def formatted_players(list_):
        return ' '.join(['{}. {}'.format(i + 1, _) for i, _ in enumerate(list_)])

    def reset_deck(self):
        self.deck = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        random.shuffle(self.deck)

    async def start(self, users):
        self.reset_deck()
        for _ in users:
            self.players.append(Player(_, 'liberal'))
        random.shuffle(self.players)
        num_of_fascists = math.ceil(len(users) * 0.5 - 1)
        for _ in random.choices(self.players, k=num_of_fascists):
            _.identity = 'fascist'
        self.hitler = random.choice(self.fascists)
        self.hitler.identity = 'hitler'
        self.president = self.players[0]
        await self.channel.send('Başkanlık sırası: {}'.format(', '.join([str(_) for _ in self.players])))
        if len(self.players) > 5:
            self.policy_table[Policy.fascist] = 1
        logging.info('Starting game with {} players'.format(len(self.players)))
        self.bot.loop.create_task(self.send_identities())
        await self.status_feedback()

    async def send_identities(self):
        try:
            fascists_ = ', '.join(map(str, self.fascists))
            for _ in self.players:
                if _.identity == 'liberal':
                    await _.user.send('Liberalsin.')
                elif _.identity == 'fascist':
                    await _.user.send('Faşistsin.\n'
                                      'Faşistler: {}, '
                                      'Hitler: {}.'.format(fascists_, self.hitler))
                elif _.identity == 'hitler':
                    await _.user.send('Hitler\'sin.')
                    if len(self.players) < 7:
                        await _.user.send('Faşistler: {}'.format(fascists_))
        except Exception as e:
            logging.error(e)

    async def play_card(self, card):
        if card.value not in self.president_cards:
            return
        if card == Policy.fascist:
            await self.channel.send('Şansolye {}, faşist bir politika yürürlüğe koydu. Kalan kart: {}'
                                    .format(self.chancellor, len(self.deck)))
            self.policy_table[Policy.fascist] += 1
        elif card == Policy.liberal:
            await self.channel.send('Şansolye {}, liberal bir politika yürürlüğe koydu. Kalan kart: {}'
                                    .format(self.chancellor, len(self.deck)))
            self.policy_table[Policy.liberal] += 1
        await self.send_policy_table()
        await self.check_events(card, self.policy_table[card])

    async def play_card_from_top(self):
        card = Policy(self.deck[0])
        await self.channel.send('{} politika yürürlülüğe koyuldu.'
                                .format('Faşist' if card == Policy.fascist else 'Liberal'))
        if card == Policy.fascist:
            self.policy_table[Policy.fascist] += 1
        elif card == Policy.liberal:
            self.policy_table[Policy.liberal] += 1
        del (self.deck[0])
        await self.send_policy_table()
        await self.check_events(card, self.policy_table[card])

    async def send_policy_table(self):
        await self.channel.send('Liberal politikalar: {}\n'
                                'Faşist politikalar: {}'.format(self.policy_table[Policy(1)],
                                                                self.policy_table[Policy(0)]))

    async def next_president(self):
        self.president_index = (self.president_index + 1) % len(self.players)
        self.president = self.players[self.president_index]
        self.status = Status.president_choosing_chancellor
        await self.status_feedback()

    async def check_events(self, policy, value):
        if policy == Policy.fascist and value == 1 and len(self.players) > 5:
            self.status = Status.president_investigating
            await self.status_feedback()
        elif policy == Policy.fascist and value == 2 and len(self.players) > 5:
            self.status = Status.president_investigating
            await self.status_feedback()
        elif policy == Policy.fascist and value == 3:
            await self.policy_peek()
        elif policy == policy.fascist and value == 4:
            self.status = Status.president_executing
            await self.status_feedback()
        elif policy == policy.liberal and value == 5:
            await self.declare_win(Policy.liberal)
        elif policy == policy.fascist and value == 5:
            self.veto_power = True
            self.status = Status.president_executing
            await self.status_feedback()
        elif policy == policy.fascist and value == 6:
            await self.declare_win(Policy.fascist)
        else:
            await self.next_president()

    async def status_feedback(self):
        if self.status is Status.president_choosing_chancellor:
            self.last_message = await self.channel.send('Başkan {}, Şansolyeni seç.\n'
                                                        '{}'.format(self.president,
                                                                    self.formatted_players(self.eligible_chancellors)))
            await self.add_indexed_reaction(self.eligible_chancellors)
            self.status = Status.president_choosing_chancellor
        elif self.status is Status.president_eliminating_card:
            if len(self.deck) < 3:
                self.reset_deck()
                await self.channel.send('Deste karıştırıldı.')
            self.president_cards.clear()
            self.president_cards.extend(self.deck[0:3])
            self.last_message = await self.president.user.send('Bir kartı ele')
            await self.last_message.add_reaction(SecretHitler.card_emojis[Policy.liberal])
            await self.last_message.add_reaction(SecretHitler.card_emojis[Policy.fascist])
            await self.president.user.send(
                'Kartlar: {}'.format(', '.join([Policy(_).name for _ in self.president_cards])))
            del (self.deck[0:3])
        elif self.status is Status.president_investigating:
            self.last_message = await self.channel.send('Başkan {}, inceleyeceğin oyuncuyu seç.\n'
                                                        '{}'.format(self.president,
                                                                    self.formatted_players(
                                                                        self.players_without_president)))
            await self.add_indexed_reaction(self.players_without_president)
        elif self.status is Status.president_executing:
            self.last_message = await self.channel.send('Başkan {} birisini idam edecek.\n'
                                                        '{}'.format(self.president,
                                                                    self.formatted_players(
                                                                        self.players_without_president)))
            await self.add_indexed_reaction(self.players_without_president)
        elif self.status is Status.veto:
            self.last_message = await self.president.send('Veto ediyor musun?')
            await self.last_message.add_reaction(SecretHitler.emojis['yes'])
            await self.last_message.add_reaction(SecretHitler.emojis['no'])
        elif self.status == Status.veto_accepted:
            self.channel.send('Veto {} tarafından kabul edildi.'.format(self.president))
            self.president_cards.clear()
            await self.next_president()

    async def policy_peek(self):
        await self.channel.send('Başkan {} destenin en üstündeki kartlara bakıyor.'.format(self.president))
        await self.president.send(
            'Sonraki üç kart: {}'.format(', '.join([Policy(_).name for _ in self.deck[0:3]])))
        await self.next_president()

    async def investigate(self, player):
        player = self.players_without_president[player]
        identity = 'faşist' if player.identity == 'fascist' or player.identity == 'hitler' else 'liberal'
        await self.president.send('{}: {}.'.format(player, identity))

    async def special_election(self):
        """
                The President chooses any other player at the table to be the next Presidential Candidate by passing
        that player the President placard. Any player can become President—even players that are term-limited. The
        new President nominates an eligible player as Chancellor Candidate and the Election proceeds as usual.
        A Special Election does not skip any players. After a Special Election, the President placard returns to the
        left of the President who enacted the Special Election. If the President passes the
        presidency to the next player in the rotation, that player would get to run for President twice in a row:
        once for the Special Election and once for their normal shift in the Presidential rotation.
        :return:
        """
        pass

    async def declare_win(self, party):
        if party == Policy.fascist:
            await self.channel.send('Faşistler kazandı.')
        elif party == Policy.liberal:
            await self.channel.send('Liberaller kazandı.')
        self.status = Status.finish

    async def president_execute(self, user):
        user = self.players_without_president[user]
        if user.identity == 'hitler':
            await self.channel.send('Hitler öldürüldü.')
            return await self.declare_win(Policy.liberal)
        await self.channel.send('{} öldürüldü.'.format(user))
        self.players.remove(user)
        await self.next_president()

    async def add_indexed_reaction(self, list_):
        for _ in range(len(list_)):
            await self.last_message.add_reaction(list(SecretHitler.index_emojis.keys())[_])

    async def chancellor_choose(self, index):
        user = self.eligible_chancellors[index]
        self.chancellor = user
        self.last_message = await self.channel.send('Şansolye {} için açık oylama:'.format(user))
        await self.last_message.add_reaction(SecretHitler.emojis['yes'])
        await self.last_message.add_reaction(SecretHitler.emojis['no'])
        self.status = Status.chancellor_voting

    async def chancellor_vote(self, user_id, vote):
        self.vote_box[user_id] = vote
        if len(self.vote_box) == len(self.players):
            if sum(self.vote_box.values()) > 0:
                if self.chancellor.identity == 'hitler' and self.policy_table[Policy.fascist] > 2:
                    await self.channel.send('Hitler şansolye seçildi.')
                    await self.declare_win(Policy.fascist)
                else:
                    self.policy_table['election_tracker'] = 0
                    self.last_president = self.president
                    self.last_chancellor = self.chancellor
                    await self.channel.send('Başkan {} ve Şansolye {} seçimi kazandı.'
                                            .format(self.president, self.chancellor))
                    self.status = Status.president_eliminating_card
                    await self.status_feedback()
            else:
                await self.channel.send('Şansolye {} reddedildi.'.format(self.chancellor))
                self.policy_table['election_tracker'] = self.policy_table['election_tracker'] + 1
                if self.policy_table['election_tracker'] == 3:
                    await self.channel.send('Üç kez seçim reddedildi. En tepedeki politika oynanıyor.')
                    await self.play_card_from_top()
                else:
                    await self.next_president()
            self.vote_box.clear()

    async def chancellor_choosing_card(self, card):
        self.president_cards.remove(card.value)
        _ = await self.chancellor.send('Kartı seç')
        await _.add_reaction(SecretHitler.card_emojis[Policy.liberal])
        await _.add_reaction(SecretHitler.card_emojis[Policy.fascist])
        if self.veto_power:
            await _.add_reaction(SecretHitler.emojis['no'])
        await self.chancellor.send('Kartlar: {}'.format(', '.join([Policy(_).name for _ in self.president_cards])))
        self.last_message = _
        self.status = Status.chancellor_choosing_card


class Player:
    def __init__(self, user=None, identity=None, party=None):
        self.user = user
        self.identity = identity
        self.party = party

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
