import random
from discord.ext import commands

# class Project1(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot
#
#     @commands.command(help='Generate random text')
#     async def gen(self, ctx):
#         await ctx.send(generate_paragraph())


class Name:
    syllable = ['za', 'ros', 'fir', 'nes', 'be', 'dir', 'nes', 'zar', 'ar', 'çe', 'lik']

    @classmethod
    def settlement(cls):
        return ''.join(random.sample(cls.syllable, random.randint(2, 4))).title()

    @classmethod
    def cooperation(cls):
        return ''.join(random.sample(cls.syllable, random.randint(2, 4))).title()

    @classmethod
    def adjective(cls):
        return random.choice(['', 'değerli', 'zengin', 'nadir', 'az bulunan', 'yeni keşfedilmiş'])


class Settlement:
    def __init__(self):
        self.name = Name.settlement()
        self.founder = Name.cooperation() if random.getrandbits(1) else None

    economic = {
        'source': ['maden', 'gaz', 'enerji'],
        'research': ['vahşi hayvan', 'yeraltı']
    }

    @classmethod
    def income_source(cls):
        category = random.choice([_ for _ in cls.economic.keys()])
        value = random.choice(cls.economic[category])
        if category is 'source':
            return f'{Name.adjective()} {value} kaynakları'.strip()
        else:
            return f'{value} araştırmaları'


class Catastrophe:
    def __repr__(self):
        return random.choice(['yerleşkede yaşayanlar delirdi', 'deprem oldu', 'soykırıldı', 'göçtüler',
                              'yerleşkeyi vahşi hayvanlar ele geçirdi', 'bütün insanlar kayboldu'])


def generate_paragraph():
    new = Settlement()
    foundernotknown = 'kuruldu. Yerleşkeyi kimin başlattığı bilinmiyor'
    return f'{Name.settlement()} yerleşkesi {random.randint(2000, 2200)} yılında ' \
        f'{Name.cooperation() if new.founder else foundernotknown}. Yerleşkede {Settlement.income_source()} ' \
        f'olduğu için hızlıca gelişti. {random.randint(2000, 2200)} yılında {Catastrophe()}.'


print(generate_paragraph())
