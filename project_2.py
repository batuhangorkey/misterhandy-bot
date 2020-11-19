import random
from discord.ext import commands


class Project2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storyteller = StoryTeller(rooms[0])

    @commands.command(help='Start anew')
    async def bar(self, ctx):
        self.storyteller = StoryTeller(rooms[0])
        await ctx.send(self.storyteller.view_room())

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author == self.bot.user:
            return
        self.storyteller.progress(msg.content.lower())
        await msg.channel.send(self.storyteller.view_room())


class StoryTeller:
    def __init__(self, starting_room):
        self.current_room = starting_room
        self.gender = 0

    def progress(self, input_text):
        for _ in self.current_room.exits:
            for key in _.keys:
                if input_text == key:
                    self.current_room = _.room
                    if _.action is not None:
                        _.action(self, key)
                    return True
        return False

    def view_room(self):
        if rooms.index(self.current_room) == 1:
            return self.current_room.description.format("Hanımefendi" if self.gender else "Beyefendi")
        penis_desc = " Penisi {} santim.".format(random.randint(10, 25)) if self.gender else ""
        return self.current_room.description.format(penis_desc=penis_desc)


class Exit:
    def __init__(self, keys, room=None, action=None):
        self.keys = keys
        self.room = room
        self.action = action


class Room:
    def __init__(self, description, _format=None):
        self.description = description
        self.exits = []
        self.format = _format


def change_gender(self, text_input):
    if text_input == "erkek":
        self.gender = 0
    else:
        self.gender = 1


rooms = [
    Room("Barda beğendiğin güzel bir hanımefendi ve bir beyefendi var. Hangisine yaklaşıyorsun?"),
    Room("Birbirinizle mükemmel uyuşuyorsunuz. {} evine davet ediyor. Evine gidiyor musun?"),
    Room("Yatak odasına kadar ilerlediniz. Trans olduğunu öğreniyorsun.{penis_desc} Devam ediyor musun?"),
    Room("Ağzına almanı istiyor. Devam ediyor musun?"),
    Room("Sana arkadan girmek istiyor. Devam ediyor musun?"),
    Room("Ağzına boşalmak istiyor. Devam ediyor musun?"),
    Room("Ona arkadan girmeni istiyor. Devam ediyor musun?"),
    Room("Güzel bir geceydi."),
    Room("Evine yalnız dönüyorsun.")
]

rooms[0].exits.append(Exit(["kadın", "erkek"], rooms[1], change_gender))
rooms[1].exits.append(Exit(["evet"], rooms[2]))
rooms[2].exits.append(Exit(["evet"], rooms[3]))
rooms[3].exits.append(Exit(["evet"], rooms[4]))
rooms[4].exits.append(Exit(["evet"], rooms[5]))
rooms[5].exits.append(Exit(["evet"], rooms[6]))
rooms[6].exits.append(Exit(["evet"], rooms[7]))
rooms[1].exits.append(Exit(["hayır"], rooms[8]))

# storyteller = StoryTeller(rooms[0])
#
# print(storyteller.view_room())
# storyteller.progress("kadın")
# print(storyteller.view_room())
# storyteller.progress("evet")
# print(storyteller.view_room())
# storyteller.progress("evet")
# print(storyteller.view_room())
# storyteller.progress("evet")
# print(storyteller.view_room())
# storyteller.progress("evet")
# print(storyteller.view_room())
# storyteller.progress("evet")
# print(storyteller.view_room())
# storyteller.progress("evet")
# print(storyteller.view_room())
