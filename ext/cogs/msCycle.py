import asyncio
import json
import logging
import os
import imgkit
import discord
import traceback
import concurrent.futures
from ..infoscraper import channelInfo
from ..share.dataUtils import botdb
from discord.ext import commands, tasks

async def milestoneCheck():
    db = await botdb.getDB()
    milestone = {}
    dbUpdate = []
    noWrite = True
    channels = await botdb.getAllData("channels", ("id", "milestone"), keyDict="id")

    async def getSubs(channel):
        for x in range(2):
            try:
                ytch = await channelInfo(channel)
                logging.debug(f'Milestone - Checking channel: {ytch["name"]}')
                if ytch["roundSubs"] > channels[channel]["milestone"]:
                    if ytch["roundSubs"] < 1000000:
                        subtext = f'{int(ytch["roundSubs"] / 1000)}K Subscribers'
                    else:
                        if ytch["roundSubs"] == ytch["roundSubs"] - (ytch["roundSubs"] % 1000000):
                            subtext = f'{int(ytch["roundSubs"] / 1000000)}M Subscribers'
                        else:
                            subtext = f'{ytch["roundSubs"] / 1000000}M Subscribers'
                    return {
                        "id": channel,
                        "name": ytch["name"],
                        "image": ytch["image"],
                        "banner": ytch["mbanner"],
                        "msText": subtext,
                        "roundSubs": ytch["roundSubs"]
                    }
                break
            except Exception as e:
                if x == 2:
                    logging.error(f'Milestone - Unable to get info for {channel}!')
                    print("An error has occurred.")
                    traceback.print_tb(e)
                    break
                else:
                    logging.warning(f'Milestone - Failed to get info for {channel}. Retrying...')
    
    chList = []
    for channel in channels:
        chList.append(getSubs(channel))
    msData = await asyncio.gather(*chList)

    for channel in msData:
        if channel != None:
            noWrite = False
            milestone[channel["id"]] = channel
            dbUpdate.append((channel["id"], channel["roundSubs"]))

    if not noWrite:
        await botdb.addMultiData(dbUpdate, ("id", "milestone"), "channels", db)
    
    return milestone

async def milestoneNotify(msDict, bot, test=False):
    logging.debug(f'Milestone Data: {msDict}')
    servers = await botdb.getAllData("servers", ("server", "channel", "milestone"))
    for channel in msDict:
        logging.debug(f'Generating milestone image for id {channel}')
        if msDict[channel]["banner"] is not None:
            with open("milestone/milestone.html") as f:
                msHTML = f.read()
        else:
            msDict[channel]["banner"] = ""
            with open("milestone/milestone-nobanner.html") as f:
                msHTML = f.read()
        options = {
            "enable-local-file-access": "",
            "encoding": "UTF-8",
            "quiet": ""
        }
        msHTML = msHTML.replace('[msBanner]', msDict[channel]["banner"]).replace('[msImage]', msDict[channel]["image"]).replace('[msName]', msDict[channel]["name"]).replace('[msSubs]', msDict[channel]["msText"])
        logging.debug(f'Replaced HTML code')
        with open("milestone/msTemp.html", "w", encoding="utf-8") as f:
            f.write(msHTML)
        logging.debug(f'Generating image for milestone')
        if not os.path.exists("milestone/generated"):
            os.mkdir("milestone/generated")
        imgkit.from_file("milestone/msTemp.html", f'milestone/generated/{channel}.png', options=options)
        logging.debug(f'Removed temporary HTML file')
        os.remove("milestone/msTemp.html")
        if not test:
            for server in servers:
                try:
                    logging.debug(f'Accessing server id {server}')
                    for dch in servers[server]:
                        milestone = server["milestone"].split("|yb|")
                        logging.debug(f'Milestone - Channel Data: {milestone}')
                        logging.debug(f'Milestone - Channel Check Pass: {channel in milestone}')
                        if channel in milestone:
                            logging.debug(f'Posting to {dch}...')
                            await bot.get_channel(int(dch)).send(f'{msDict[channel]["name"]} has reached {msDict[channel]["msText"].replace("Subscribers", "subscribers")}!', file=discord.File(f'milestone/generated/{channel}.png'))
                            await bot.get_channel(int(dch)).send("おめでとう！")
                except Exception as e:
                    logging.error("Milestone - Failed to post on a server/channel!", exc_info=True)

def mcWrapper():
    return asyncio.run(milestoneCheck())

class msCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timecheck.start()

    def cog_unload(self):
        self.timecheck.cancel()

    @tasks.loop(minutes=3.0)
    async def timecheck(self):
        logging.info("Starting milestone checks.")
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                msData = await loop.run_in_executor(pool, mcWrapper)
            if msData != {}:
                logging.info("Milestone - Notifying channels.")
                await milestoneNotify(msData, self.bot)
        except Exception as e:
            logging.error("Milestone - An error has occured in the cog!", exc_info=True)
            traceback.print_exception(type(e), e, e.__traceback__)
        else:
            logging.info("Milestone checks done.")