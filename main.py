from server_data import ServerData
import discord
import asyncio
import sys
import os
import json
import pickle #kmn

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
            'start' : self.submit_response
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

        with open('data.json', 'w') as f:
            json.dump([d.__dict__ for d in self.data], f)

    async def on_guild_remove(self, guild):
        self.data = [d for d in self.data if d.id != guild.id]

        with open('data.json', 'w') as f:
            json.dump([d.__dict__ for d in self.data], f)

    async def on_message(self, message):
        if len([d for d in self.data if d.id == message.guild.id]) == 0:
            self.data.append(ServerData(**{
                'id' : message.guild.id,
                'prefix' : '%',
                'questions' : [],
                'responses' : {}
                }
            ))

        if not await self.get_cmd(message):
            pass

    async def get_cmd(self, message):
        if isinstance(message.channel, discord.DMChannel) or message.author.bot or message.content == None:
            return False

        server = self.get_server(message.guild)
        prefix = server.prefix

        if message.content[0:len(prefix)] == prefix:
            command = (message.content + ' ')[len(prefix):message.content.find(' ')]
            if command in self.commands:
                stripped = message.content[message.content.find(' '):].strip()
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

        server.prefix = stripped
        await message.channel.send('Prefix changed to {}'.format(server.prefix))

        with open('data.json', 'w') as f:
            json.dump([d.__dict__ for d in self.data], f)

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

                with open('data.json', 'w') as f:
                    json.dump([d.__dict__ for d in self.data], f)
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

            server.responses[str(message.author.id)] = response_list
            await message.channel.send('Thank you for your application!')

            with open('data.json', 'w') as f:
                json.dump([d.__dict__ for d in self.data], f)

    async def view_responses(self, message, stripped):

try: ## token grabbing code
    with open('token','r') as token_f:
        token = token_f.read().strip('\n')

except:
    print('no token provided')
    sys.exit(-1)

client = BotClient()
client.run(token)
