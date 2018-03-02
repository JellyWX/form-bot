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
        self.data = []

        self.commands = {
            'ping' : self.ping,
            'help' : self.help,
            'prefix' : self.change_prefix
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
            'reference' : guild,
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
        if not await self.get_cmd(message):
            pass

    async def get_cmd(self, message):
        if isinstance(message.channel, discord.DMChannel) or message.author.bot or message.content == None:
            return False

        server = [d for d in self.data if d.id == message.guild.id][0]
        prefix = server.prefix

        if message.content[0] == prefix:
            command = (message.content + ' ')[1:message.content.find(' ')]
            if command in self.commands:
                stripped = message.content[message.content.find(' '):].strip()
                await self.commands[command](message, stripped)
                return True

        elif self.user.id in map(lambda x: x.id, message.mentions) and len(message.content.split(' ')) > 1:
            if message.content.split(' ')[1] in self.commands.keys():
                await self.commands[message.content.split(' ')[1]](message)
                return True

        return False

    async def change_prefix(self, message, stripped):
        server = [d for d in self.data if d.id == message.guild.id][0]

        server.prefix = stripped
        message.channel.send('Prefix changed to {}'.format(server.prefix))

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


try: ## token grabbing code
    with open('token','r') as token_f:
        token = token_f.read().strip('\n')

except:
    print('no token provided')
    sys.exit(-1)

client = BotClient()
client.run(token)
