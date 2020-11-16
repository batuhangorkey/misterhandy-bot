import random
from discord.ext import commands


class Project2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storyteller = storyteller

    @commands.command(help='Generate random text')
    async def bar(self, ctx, input_text=None):
        if input_text is None:
            await ctx.send(self.storyteller.view_room())
        else:
            self.storyteller.progress(input_text)
            await ctx.send(self.storyteller.view_room())

    @commands.command(help='Start anew')
    async def reset(self, ctx):
        self.storyteller = StoryTeller(room1)


class StoryTeller:
    def __init__(self, starting_room):
        self.current_room = starting_room

    def progress(self, input_text):
        for _ in self.current_room.exits:
            if input_text == _.key:
                self.current_room = _.room
                return True
        return False

    def view_room(self):
        return self.current_room.description


class Exit:
    def __init__(self, key, room):
        self.key = key
        self.room = room


class Room:
    def __init__(self, description, exits=None):
        self.description = description
        self.exits = exits


room1 = Room("Barda güzel bir hanımefendiyle karşılaştın. Eve gidiyor musun?")
room2 = Room("Evdesiniz.")

room1.exits += Exit("evet", room2)


storyteller = StoryTeller(room1)
