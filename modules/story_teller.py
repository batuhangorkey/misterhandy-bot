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
