from server_data import ServerData
import discord
import asyncio
import sys
import os
import json
import math

class BotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super(BotClient, self).__init__(*args, **kwargs)
        self.get_server = lambda x: [d for d in self.data if d.id == x.id][0]

        self.data = []

        self.commands = {
            'ping' : self.ping,
            'help' : self.help,
            'prefix' : self.change_prefix,
            'set' : self.set_questions,
            'start' : self.submit_response,
            'questions' : self.view_questions,
            'log' : self.view_responses
        }

        try:
            with open('data.json', 'r') as f:
                for d in json.load(f):
                    self.data.append(ServerData(**d))
        except IOError:
            pass

    async def on_ready(self):
        print('Online now!')
        await client.change_presence(game=discord.Game(name='%help'))

    async def on_guild_join(self, guild):
        self.data.append(ServerData(**{
            'id' : guild.id,
            'prefix' : '%',
            'questions' : [],
            'responses' : []
            }
        ))

    async def on_guild_remove(self, guild):
        self.data = [d for d in self.data if d.id != guild.id]

    async def on_message(self, message):
        if len([d for d in self.data if d.id == message.guild.id]) == 0:
            self.data.append(ServerData(**{
                'id' : message.guild.id,
                'prefix' : '%',
                'questions' : [],
                'responses' : []
                }
            ))

        if await self.get_cmd(message):
            with open('data.json', 'w') as f:
                json.dump([d.__dict__ for d in self.data], f)

    async def get_cmd(self, message):
        if isinstance(message.channel, discord.DMChannel) or message.author.bot or message.content == None:
            return False

        server = self.get_server(message.guild)
        prefix = server.prefix

        if message.content[0:len(prefix)] == prefix:
            command = (message.content + ' ')[len(prefix):message.content.find(' ')]
            if command in self.commands:
                stripped = (message.content + ' ')[message.content.find(' '):].strip()
                await self.commands[command](message, stripped)
                return True

        elif self.user.id in map(lambda x: x.id, message.mentions) and len(message.content.split(' ')) > 1:
            if message.content.split(' ')[1] in self.commands.keys():
                stripped = (message.content + ' ').split(' ', 2)[-1].strip()
                await self.commands[message.content.split(' ')[1]](message, stripped)
                return True

        return False

    async def change_prefix(self, message, stripped):
        server = self.get_server(message.guild)

        if stripped:
            stripped += ' '
            server.prefix = stripped[:stripped.find(' ')]
            await message.channel.send('Prefix changed to {}'.format(server.prefix))

        else:
            await message.channel.send('Please use this command as `prefix <prefix>`')

    async def ping(self, message, stripped):
        t = message.created_at.timestamp()
        e = await message.channel.send('pong')
        delta = e.created_at.timestamp() - t
        await e.edit(content='Pong! {}ms round trip'.format(round(delta * 1000)))

    async def help(self, message, stripped):
        await message.channel.send(embed=discord.Embed(
            description='''
`help` : Show this page
`ping` : Pong
`prefix` : Change the prefix
            '''
        ))

    async def set_questions(self, message, stripped):
        if message.author.guild_permissions.administrator:
            server = self.get_server(message.guild)

            await message.channel.send('Please enter your questions (max 6) on separate lines and then send them to this channel (use SHIFT and ENTER to get a new line)')
            m = await client.wait_for('message', check=lambda m: m.channel is message.channel and m.author is message.author)

            questions = m.content.split('\n')

            if len(questions) > 6:
                await message.channel.send('Too many questions! Maximum of 6.')
            elif len(m.content) > 400:
                await message.channel.send('Too long! Please use less than 400 characters')
            else:
                await message.channel.send('Your questions are: {}'.format(', '.join(questions)))
                server.questions = questions

        else:
            await message.channel.send('You must be an admin to run this command')

    async def submit_response(self, message, stripped):
        server = self.get_server(message.guild)

        if len(server.questions) < 1:
            await message.channel.send('No questions have been set! Please contact an admin.')
        else:
            response_list = []
            for question in server.questions:
                await message.channel.send(question + ' ({}/{}, `cancel` to stop)'.format(server.questions.index(question) + 1, len(server.questions)))
                m = await client.wait_for('message', check=lambda m: m.channel is message.channel and m.author is message.author)
                response_list.append(m.content)
                if m.content.lower() == 'cancel':
                    await message.channel.send('Application cancelled.')
                    return

            server.responses.append(response_list + [message.author.id])
            await message.channel.send('Thank you for your application!')

    async def view_responses(self, message, stripped):
        if message.author.guild_permissions.administrator:
            server = self.get_server(message.guild)

            if not stripped: #no page provided
                page = 0
            elif all([x in '0123456789' for x in stripped]): #page number is good
                page = int(stripped) - 1
            else: #BIG BAD
                await message.channel.send('Error: argument 1 must be <unsigned integer> page number')
                return

            total_pages = math.ceil(len(server.responses) / 5)
            if page > total_pages:
                await message.channel.send('Error: invalid page number')
                return

            while True:
                upper = (page + 1) * 5
                if upper > len(server.responses):
                    upper = len(server.responses)

                details = server.responses[page*5:upper]
                e = discord.Embed(title='Log')
                e.set_footer(text='Page {}/{} (results {}-{} of {})'.format(page+1, total_pages, page*5 +1, upper, len(server.responses)))
                for resp in details:
                    name = ''
                    content = ''
                    for question in resp:
                        if isinstance(question, int):
                            name = self.get_user(question).name + '#' + self.get_user(question).discriminator if self.get_user(question) != None else 'Unknown'
                        else:
                            q = server.questions[resp.index(question)]
                            content += '**' + q + '**' + (': ' if q[-1] not in ':;' else ' ') + question + ' '
                    e.add_field(name=name, value=content)

                m = await message.channel.send(embed=e)
                emojis = ['\U00002B05', '\U000027A1', '\U0000274C', '\U0001F5D1']

                for emoji in emojis:
                    await m.add_reaction(emoji)

                try:
                    reaction, _ = await client.wait_for('reaction_add', timeout=60.0, check=lambda reaction, user: reaction.message.id == m.id and user == message.author)
                except:
                    await m.clear_reactions()
                    return

                if reaction.emoji == '\U00002B05': # arrow left
                    await m.delete()
                    page = page - 1 if page else page
                elif reaction.emoji == '\U000027A1': # arrow right
                    await m.delete()
                    page = page + 1 if page != total_pages else page
                elif reaction.emoji == '\U0000274C': # cross
                    await m.delete()
                    return
                elif reaction.emoji == '\U0001F5D1': # wastebin
                    await m.edit(embed=discord.Embed(title='Log', description='Log has been cleared'))
                    await m.clear_reactions()
                    server.responses = []
                    return

    async def view_questions(self, message, stripped):
        server = self.get_server(message.guild)
        await message.channel.send(embed=discord.Embed(title='Questions', description='\n'.join(server.questions)))

try: ## token grabbing code
    with open('token','r') as token_f:
        token = token_f.read().strip('\n')

except:
    print('no token provided')
    sys.exit(-1)

client = BotClient()
client.run(token)
