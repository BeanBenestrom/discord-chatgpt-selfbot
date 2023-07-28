import discord, json, datetime, asyncio, traceback, re
from discord import Message as DiscordMessage
from discord.ext import commands

import configuration, ai
from interface import ConversationInterface
from structure import Message, channelConfiguration
from conversation import ComplexMemoryConversation
from memory import ComplexMemory
from delay import NaturalDelay
from vector_database import CollectionType
from debug import LogType, LogJsonFile, LogHanglerInterface
from utility import create_json_file_if_not_exist


class MainCog(commands.Cog):
    def __init__(self, bot, id: int, log: LogHanglerInterface):
        self.bot = bot
        self.id = id
        self.extra_info = False
        self.conversations: dict[str, ConversationInterface] = {}
        self.locks: dict[str, bool] = {}
        self.messages: dict[str, list[DiscordMessage]] = {}
        self.log = log
        self.writing_seconds_per_char = 18/84 / 5

    # async def ping(self, ctx, message):
    #     print(f"PING - ARGS: {message}")
    #     await ctx.send('pong!')


    async def get_users(self):
        users_info = "" 
        for user in self.bot.users:
            if user.id == self.id : continue
            if not user.dm_channel: continue
            users_info += f"{user.name}, {user.id}\n"
        return users_info


    async def get_DMChannels(self):
        
        # user = discord.Object(int(id))
        # dm = self.bot.create_dm(user)
        # print(f"DM Channel ID: {dm.id}")
        # print(self.bot.private_channels)

        private_channels = self.bot.private_channels
        info = []
        for channel in private_channels:
            if type(channel) == discord.DMChannel:
                info.append(f"DM Channel {channel.id} - {channel.recipient.name}")
        return info
        

    # async def printAllPrivateChannels(self):
    #     private_channels = self.bot.private_channels

    #     for channel in private_channels:
    #         if type(channel) == discord.DMChannel:
    #             print(f"DM Channel    {channel.id} - {channel.recipient.name}")
    #         elif type(channel) == discord.GroupChannel:
    #             print(f"Group Channel {channel.id} - {channel.name}")
    #         else:
    #             print(f"UNDEFINED     {channel}")


    async def get_history(self, channel_id, limit=200) -> list[Message]:
        channel = bot.get_channel(int(channel_id))

        messages = [message async for message in channel.history(limit=limit, oldest_first=False)]
        messages.reverse()
        parsed_messages = [ Message(
            message.id, 
            str(message.created_at), 
            message.author.name if str(message.author.discriminator) == '0' else f"{message.author.name}#{message.author.discriminator}", 
            message.content) for message in messages ]

        return parsed_messages


    async def get_history_around(self, channel_id, date, limit=20) -> list[Message]:
        channel = bot.get_channel(int(channel_id))

        if type(date) != datetime.datetime:
            if len(date) == 19: date += ".000000"
            date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')

        messages = [message async for message in channel.history(limit=limit, around=date, oldest_first=True)]

        index = 0
        for i in range(len(messages)):
            if messages[i].created_at == date: 
                index = i
                break

        left  = index
        right = len(messages) - 1 - index
        diff  = left - right

        if left > right: messages = messages[ diff:]
        else           : messages = messages[:-diff]

        parsed_messages = [ Message(
            message.id, 
            str(message.created_at), 
            message.author.name if str(message.author.discriminator) == '0' else f"{message.author.name}#{message.author.discriminator}", 
            message.content) for message in messages ]

        return parsed_messages

    
    async def send_message(self, discordMessage: DiscordMessage):
        try:
            channel_id = int(discordMessage.channel.id)

            if configuration.is_channel_real(channel_id) and configuration.is_blacklist_channel(channel_id):
                if str(channel_id) in self.conversations:
                    del self.conversations[str(channel_id)]
                return

            if not str(channel_id) in self.locks:
                self.locks[str(channel_id)] = False
            if not str(channel_id) in self.messages:
                self.messages[str(channel_id)] = []
            
            self.messages[str(channel_id)].append(discordMessage)

            if not self.locks[str(channel_id)]:
                self.locks[str(channel_id)] = True

                if not configuration.is_channel_real(channel_id):
                    self.log.log(LogType.INFO, f"ADDING NEW CHANNEL TO CONFIG - {channel_id}")
                    history = await self.get_history(channel_id, limit=20000)

                    for i in range(1, 21):
                        if len(history) < i:
                            break
                        if history[-i].id == self.messages[str(channel_id)][0].id:
                            self.log.log(LogType.INFO, f"Removed duplicate message history - {channel_id}\nmessages: {[str(message) for message in history[-i:]]}")
                            history = history[:-i]
                            break

                    with open("outputs/new-channel-added.json", 'w', encoding='utf-8') as file:
                        json.dump([message.object_to_list() for message in history], file, ensure_ascii=False)

                    memory = await ComplexMemory.create(channel_id, 1500, CollectionType.MAIN, log=self.log.sub(str(channel_id)))
                    await memory.clear_long_term_memory()
                    await memory.clear_short_term_memory()
                    await memory.add_messages(history, log=self.log.sub(str(channel_id)))

                    self.conversations[str(channel_id)] = ComplexMemoryConversation(channel_id, memory, NaturalDelay(), log=self.log.sub(str(channel_id)))
                    configuration.add_channel(channel_id, channelConfiguration(discordMessage.author.name))
                    self.log.log(LogType.OK, "Succesfully added new channel into configuration!")
                    

                if not str(channel_id) in self.conversations:
                    self.log.log(LogType.INFO, f"ADDING CHANNEL - {channel_id}")
                    history = await self.get_history(channel_id)

                    for i in range(1, 21):
                        if len(history) < i:
                            break
                        if history[-i].id == self.messages[str(channel_id)][0].id:
                            self.log.log(LogType.INFO, f"Removed duplicate message history - {channel_id}\nmessages: {[str(message) for message in history[-i:]]}")
                            history = history[:-i]
                            break

                    memory = await ComplexMemory.create(channel_id, 1500, CollectionType.MAIN, log=self.log.sub(str(channel_id)))
                    stm = await memory.get_short_term_memory(log=self.log.sub(str(channel_id)))

                    if len(stm):
                        for i in range(1, 201):
                            if len(history) < i:
                                break
                            if history[-i].id == stm[-1].id:
                                history = history[len(history)-i+1:]
                                self.log.log(LogType.INFO, f"Removed already saved message history - {channel_id}\nnew messages: {[str(message) for message in history]}")
                                break

                    with open("outputs/channel-added.json", 'w', encoding='utf-8') as file:
                        json.dump([message.object_to_list() for message in history], file, ensure_ascii=False)

                    await memory.add_messages(history, log=self.log.sub(str(channel_id)))            
                    self.conversations[str(channel_id)] = ComplexMemoryConversation(channel_id, memory, NaturalDelay(), log=self.log.sub(str(channel_id)))
                    self.log.log(LogType.OK, "Succesfully added channel into bot's conversation list!")

                # Respond
                async def respond(string: str):
                    # Writing delay
                    # await asyncio.sleep(0.5) 
                    writing_delay: float = self.writing_seconds_per_char*len(string.strip())
                    self.log.log(LogType.INFO, f"Writing... ({writing_delay}) - {discordMessage.channel.id}")
                    async with discordMessage.channel.typing():
                        await asyncio.sleep(writing_delay)                                          # Writing delay
                    await discordMessage.channel.send(string)
                    self.log.log(LogType.OK, f"Responded! - {discordMessage.channel.id}")
                    
                    create_json_file_if_not_exist(f"bot responses/{discordMessage.channel.id}.json", [])
                    with open(f"bot responses/{discordMessage.channel.id}.json", encoding='utf-8') as r_file:
                        data = json.load(r_file)
                        data.append(string)
                    with open(f"bot responses/{discordMessage.channel.id}.json", 'w', encoding='utf-8') as w_file:
                        json.dump(data, w_file, ensure_ascii=False)

                for message in self.messages[str(channel_id)]:
                    authorId = message.author.id
                    message = Message(message.id, str(message.created_at), message.author.name, message.content)
                    asyncio.create_task(self.conversations[str(channel_id)].add_message(message, self.id == authorId, log=self.log.sub(str(channel_id))))
                self.messages[str(channel_id)].clear()
                asyncio.create_task(self.conversations[str(channel_id)].communicate(respond, log=self.log.sub(str(channel_id))))
                
                self.locks[str(channel_id)] = False
        except Exception as e:
            self.log.log(LogType.ERROR, f"{str(e)}\n{traceback.format_exc()}")


    @commands.Cog.listener()
    async def on_message(self, message: DiscordMessage):

        if message.content is None or len(message.content) == 0: return
        
        name = message.author.name if str(message.author.discriminator) == '0' else f"{message.author.name}#{message.author.discriminator}"
        self.log.log(LogType.INFO, (f"Sent message\n"
                                    f"id     : {message.id}\n"
                                    f"channel: {message.channel}\n"
                                    f"author : {name} - {message.author.id}\n"
                                    f"content: {message.content}"))

        if message.guild != None: 
            self.log.log(LogType.INFO, (f"Skipped message. Sent inside a guild"))
            return
        
        if message.author.bot:
            self.log.log(LogType.INFO, (f"Skipped message. Sent by a bot"))
            return

        # self.log.log(LogType.INFO, f"Sent message - {message}")
        
        # INITIATE SENDING MESSAGE
        await self.send_message(message)


async def setup(_bot):
    global bot
    bot = _bot
    with open("private.json", encoding='utf-8') as file:
        await _bot.add_cog(MainCog(_bot, int(json.load(file)["userId"]), LogJsonFile(LogType.DEBUG)))