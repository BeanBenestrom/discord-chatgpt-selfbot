import json, datetime, asyncio, discord
from discord.ext import commands

from debug import LogHanglerInterface, LogNothing, LogType


LOG: LogHanglerInterface = None     #type: ignore

bot: commands.Bot = None    # type: ignore
STATUS = 0

async def reload():
    if STATUS != 1: return
    await bot.unload_extension("cog")
    await bot.load_extension("cog")
    LOG.log(LogType.OK, f"RELOADED")


async def _start():
    global STATUS
    with open("private.json") as file:
        try: 
            await bot.start(json.load(file)["token"])
        except:
            if STATUS != 1: LOG.log(LogType.ERROR, "Failed to connect to discord account. Check that your token is up-to-date.")
            STATUS = -1


async def start(log: LogHanglerInterface=LogNothing()):
    global STATUS, LOG, bot
    LOG = log
    bot = commands.Bot(command_prefix="@>>> ", self_bot=True)
    
    @bot.event
    async def on_ready():
        global STATUS
        STATUS = 1
        await bot.load_extension("cog")       # type:ignore
        LOG.log(LogType.OK, f"LOGGED IN TO ACCOUNT:\nuser: {bot.user.name}\nid  : {bot.user.id}")     #type:ignore

    # Start bot
    asyncio.create_task(_start())
    while STATUS == 0:
        await asyncio.sleep(0.5)
    if STATUS == -1: raise Exception("Failed to connect to discord account. Check that your token is up-to-date.")


async def stop():
    if not bot.is_closed():
        await bot.close()


def is_ready():
    return bot.is_ready()



# COMMANDS


async def get_users():
    cog = bot.get_cog('MainCog')    
    return await cog.get_users()                                    #type:ignore


async def get_DMChannels():
    cog = bot.get_cog('MainCog')    
    return await cog.get_DMChannels()                               #type:ignore


async def get_history(channel_id: int, limit: int=200):
    cog = bot.get_cog('MainCog')    
    return await cog.get_history(channel_id, limit)                 #type:ignore


async def get_history_around(channel_id: int, date: datetime.datetime | str, limit: int=20):
    cog = bot.get_cog('MainCog')    
    return await cog.get_history_around(channel_id, date, limit)    #type:ignore
