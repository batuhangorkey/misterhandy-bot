import random
from discord.ext import commands


class Project2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storyteller = None

    @commands.command(help='Start anew')
    async def bar(self, ctx):
        async with ctx.typing():
            self.storyteller = StoryTeller(rooms[1])
            await ctx.send(self.storyteller.view_room())

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author == self.bot.user:
            return
        if self.storyteller is None:
            return
        if self.storyteller.progress(msg.content.lower()):
            await msg.channel.send(self.storyteller.view_room())


class StoryTeller:
    def __init__(self, starting_room):
        self.current_room = starting_room
        self.partner = {
            'body': None,
            'penis': False,
            'penis_size': random.randint(10, 18)
        }

    def progress(self, input_text: str):
        for _ in self.current_room.exits:
            for key in _.keys:
                if input_text.find(key) > -1:
                    self.current_room = _.room
                    if _.action is not None:
                        _.action(self, key)
                    return True
        return False

    def view_room(self):
        if self.current_room.switch is not None:
            for _ in self.current_room.trigger:
                if self.partner[self.current_room.switch] == _:
                    index = self.current_room.trigger.index(_)
                    return self.current_room.description[index].format(**self.partner)
        return self.current_room.description.format(**self.partner)


class Body:
    pass


class Female(Body):
    pass


class Masculine(Body):
    pass


class Exit:
    def __init__(self, keys, room=None, action=None):
        self.keys = keys
        self.room = room
        self.action = action


class Room:
    def __init__(self, description, trigger=None, switch=None):
        self.description = description
        self.exits = []
        self.trigger = trigger
        self.switch = switch


def change_genital(self: StoryTeller, text_input):
    fem = ["kadın", "hanfendi", "hanımefendi", "bayan"]
    men = ["erkek", "beyfendi", "beyefendi", "adam"]
    if text_input in fem:
        self.partner['body'] = Female
    elif text_input in men:
        self.partner['body'] = Masculine


rooms = {
    1: Room("Barda beğendiğin güzel bir hanımefendi ve bir beyefendi var. Hangisine yaklaşıyorsun?"),
    2: Room(["Birbirinizle mükemmel uyuşuyorsunuz. Beyefendi evine davet ediyor. Evine gidiyor musun?",
             "Birbirinizle mükemmel uyuşuyorsunuz. Hanımefendi evine davet ediyor. Evine gidiyor musun?"],
            [0, 1],
            "genital"),
    3: Room(["Yatak odasına kadar ilerlediniz. Trans olduğunu öğreniyorsun. Devam ediyor musun?",
             "Yatak odasına kadar ilerlediniz. Trans olduğunu öğreniyorsun. Penisi {penis_size} santim."
             " Ne yapıyorsun?"],
            [0, 1],
            "genital"),
    4: Room("Ağzına almanı istiyor. Devam ediyor musun?"),
    5: Room(["Sana arkadan straponla girmek istiyor. Devam ediyor musun?",
             "{penis_size} santimlik penisiyle sana arkadan girmek istiyor. Alıyor musun?"],
            [0, 1],
            "genital"),
    6: Room("Ağzına boşalmak istiyor. Devam ediyor musun?"),
    7: Room("Ona arkadan girmeni istiyor. Devam ediyor musun?"),
    8: Room("Güzel bir geceydi."),
    9: Room("Evine yalnız dönüyorsun."),
    10: Room("Kolundan tutup penisini saklayabileceğini, böyle davranmamanı söylüyor."
             " Hala gitmek istediğinden emin misin?"),
    11: Room("Evden hızlıca çıkıyorsun.")
}

rooms[1].exits.append(Exit(["kadın", "hanfendi", "hanımefendi", "bayan", "erkek", "beyfendi", "beyefendi", "adam"],
                           rooms[2], change_genital))
rooms[2].exits.append(Exit(["evet", "gidiyorum"], rooms[3]))
rooms[3].exits.append(Exit(["evet", "sevişiyorum", "sikiyorum", "seks yapıyorum"], rooms[4]))
rooms[3].exits.append(Exit(["kaçıyorum"], rooms[10]))
rooms[10].exits.append(Exit(["evet", "eminim"], rooms[11]))
rooms[4].exits.append(Exit(["evet"], rooms[5]))
rooms[5].exits.append(Exit(["evet"], rooms[6]))
rooms[6].exits.append(Exit(["evet"], rooms[7]))
rooms[7].exits.append(Exit(["evet"], rooms[8]))
rooms[4].exits.append(Exit(["hayır", "etmiyorum", "olmaz"], rooms[5]))
rooms[5].exits.append(Exit(["hayır", "etmiyorum", "olmaz"], rooms[6]))
rooms[6].exits.append(Exit(["hayır", "etmiyorum", "olmaz"], rooms[7]))
rooms[7].exits.append(Exit(["hayır", "etmiyorum", "olmaz"], rooms[8]))

# storyteller = StoryTeller(rooms[1])
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