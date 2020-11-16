import random
from discord.ext import commands


# class Project2(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot
#         self.storyteller = storyteller
#
#     @commands.command(help='Generate random text')
#     async def bar(self, ctx, input_text=None):
#         if input_text is None:
#             await ctx.send(self.storyteller.view_room())
#         else:
#             self.storyteller.progress(input_text.lower())
#             await ctx.send(self.storyteller.view_room())
#
#     @commands.command(help='Start anew')
#     async def reset(self, ctx):
#         self.storyteller = StoryTeller(rooms[0])


class StoryTeller:
    def __init__(self, starting_room):
        self.current_room = starting_room
        self.gender = 0

    def progress(self, input_text):
        for _ in self.current_room.exits:
            for key in _.keys:
                if input_text == key:
                    self.current_room = _.room
                    return True
        return False

    def view_room(self):
        return self.current_room.description


class Exit:
    def __init__(self, keys, room=None, action=None):
        self.keys = keys
        self.room = room
        self.action = action


class Room:
    def __init__(self, description, *exits):
        self.description = description
        self.exits = exits


rooms = [
    Room("Barda beğendiğin güzel bir hanımefendi ve bir beyefendi var. Hangisine yaklaşıyorsun?"),
    Room("Hanımefendi evine davet etti. Evine gidiyor musun?"),
    Room("Evdesiniz. Trans olduğunu öğreniyorsun. Devam ediyor musun?"),
    Room("Ağzına almanı istiyor. Devam ediyor musun?"),
    Room("Sana arkadan girmek istiyor. Devam ediyor musun?"),
    Room("Ağzına boşalmak istiyor. Devam ediyor musun?"),
    Room("Davet eder gibi arkasını dönüp yatağa uzanıyor. Devam ediyor musun?"),
    Room("Güzel bir geceydi.")
]

rooms[0].exits = Exit(["kadın", "erkek"], rooms[1], True)
rooms[1].exits = Exit("evet", rooms[2])

storyteller = StoryTeller(rooms[0])

print(storyteller.view_room())
storyteller.progress("kadın")
print(storyteller.view_room())
