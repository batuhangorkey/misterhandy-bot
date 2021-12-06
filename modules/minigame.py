import random
import discord
from discord.ext import commands

'''
    FINISHED
'''

class Scene:
    def __init__(self, filtered_list, difficulty):
        self.list = filtered_list
        self.attempts = 5
        self.difficulty = difficulty
        self.state = 0
        self.reward = difficulty * 10


class Minigame(commands.Cog):
    def __init__(self, bot, user_table):
        self.bot = bot
        self.user_table = user_table
        self.messages = []

    @staticmethod
    def get_raw_word_list():
        global f
        _raw_word_list = []
        try:
            f = open('modules/words.txt', 'r')
            word = ''
            for var in f.readline():
                if var != ' ':
                    word += var
                else:
                    _raw_word_list.append(word)
                    word = ''
        finally:
            f.close()
        return _raw_word_list

    @staticmethod
    def initialize(word_length):
        raw_word_list = Minigame.get_raw_word_list()
        words = []
        final_list = []
        for word in raw_word_list:
            if len(word) == word_length:
                words.append(word)
        if word_length < 15:
            word_list = random.sample(words, 10)
            correct_word = random.choice(word_list)
            for var in word_list:
                counter = 0
                k = 0
                for char in var:
                    if char == correct_word[k]:
                        counter += 1
                    k += 1
                final_list.append((var, counter))
            return final_list
        else:
            return None

    @commands.command(help='Starts the mini game.')
    async def start(self, ctx, difficulty: int):
        global scene
        game_list = Minigame.initialize(difficulty)
        self.messages.append(ctx.message)
        if game_list is not None:
            scene = Scene(game_list, difficulty)
            words = [f'{i + 1} -  {scene.list[i][0]}' for i in range(0, 9)]
            words.append(f'10 - {scene.list[9][0]}')
            if len(self.messages) > 0:
                if type(ctx.channel) != discord.DMChannel:
                    await ctx.channel.delete_messages(self.messages)
                self.messages.clear()
            self.messages.append(await ctx.send('```Terminal: \n ' + '\n '.join(words) + '```'))
        else:
            self.messages.append(await ctx.send('Hoppala bir daha dene uşağım.'))

    @commands.command(help='Enter key to the terminal.')
    async def enter(self, ctx, index: int):
        user = ctx.message.author
        self.messages.append(ctx.message)
        if scene.list[index - 1][1] == scene.difficulty and scene.state == 0 and scene.attempts > 0:
            scene.state = 1

            conn = self.bot.get_pymysql_connection()
            try:
                with conn.cursor() as cursor:
                    if user.id in self.user_table:
                        self.user_table[user.id] += scene.reward
                        cursor.execute(f"UPDATE main SET Unit = Unit + {scene.reward} WHERE UserID = {user.id}")
                    else:
                        self.user_table.update({user.id: scene.reward})
                        cursor.execute(f"INSERT INTO main VALUES ('{user.id}', '{scene.reward}')")
                    conn.commit()
            finally:
                conn.close()

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            await ctx.send(f'Sistemin içindeyiz. {user.name} +{scene.reward} Lirabit ({self.user_table.get(user.id)})')
            if len(self.messages) > 0:
                if type(ctx.channel) != discord.DMChannel:
                    await ctx.channel.delete_messages(self.messages)
                self.messages.clear()
        elif scene.state == 1:
            self.messages.append(await ctx.send('Sistem hacklendi.'))
        else:
            scene.attempts -= 1
            if scene.attempts > 0:
                await ctx.message.add_reaction('\N{CROSS MARK}')
                self.messages.append(await ctx.send('Benzerlik: ' + str(scene.list[index - 1][1]) +
                                                    '\nKalan deneme sayısı: ' + str(scene.attempts)))
            else:
                await ctx.message.add_reaction('\N{CROSS MARK}')
                self.messages.append(await ctx.send('Sistem kitlendi.'))

    @commands.command(help='Get another attempt. Cost: 50 * difficulty / 4')
    async def rebank(self, ctx):
        if scene.state == 1:
            cost = 50 * scene.difficulty / 4
            user = ctx.message.author.id
            if user in self.user_table:
                if self.user_table.get(user) > 50:
                    self.user_table[user] -= cost
                    scene.attempts += 1

                    conn = self.bot.get_pymysql_connection()
                    with conn.cursor() as cursor:
                        cursor.execute(f"UPDATE main SET Unit = Unit - {cost} WHERE UserID = {user}")
                    conn.commit()
                    conn.close()

                    await ctx.send(f'Kalan deneme sayısı: {scene.attempts}')
                else:
                    await ctx.send('Yeterli lirabitin yok.')
            else:
                await ctx.send('Hiç lirabitin yok.')
        else:
            await ctx.send('Mevcutta oyun yok.')

    @commands.command(help='Shows your bits.')
    async def mybit(self, ctx):
        user = ctx.message.author
        if user.id in self.user_table:
            await ctx.send(f'Tecrüben: {self.user_table.get(user.id)} Lirabit')
        else:
            await ctx.send('Daha oynamamışsın.')
