import asyncio
import aiohttp
import json
import logging
import os
import traceback
import concurrent.futures
from tweepy.errors import NotFound
from tweepy.asynchronous import AsyncStream
from ..infoscraper import TwitterScrape
from discord.ext import commands, tasks
from discord import AsyncWebhookAdapter, Webhook
from ext.share.dataGrab import getwebhook

async def twtUpdater():
    """
    Update Twitter user IDs.
    Has to be run every 15 minutes, and shouldn't be less as quotas renew every 15 minutes.
    More is fine.
    """
    write = False
    with open("data/channels.json") as f:
        channels = json.load(f)
    with open("data/scrape.json") as f:
        scrape = json.load(f)
    if os.path.exists("data/twitter.json"):
        with open("data/twitter.json") as f:
            twitter = json.load(f)
    else:
        twitter = {}

    for channel in channels:
        if "twitter" not in channels[channel] and "twitter" in scrape[channel]:
            try:
                twtID = await TwitterScrape.getUserID(scrape[channel]["twitter"])
                if twtID is not None:
                    channels[channel]["twitter"] = twtID
                    twitter[twtID] = channel
                    write = True
            except NotFound:
                logging.error(f"Twitter - Could not find user @{scrape[channel]['twitter']}")
    
    if write:
        with open("data/channels.json", "w") as f:
            json.dump(channels, f, indent=4)
        with open("data/twitter.json", "w") as f:
            json.dump(twitter, f, indent=4)

async def twtSubscribe(bot):
    """
    Subscribes to tweets from Twitter IDs registered in `channels.json`.  
    Requires the async branch of `tweepy`.

    Arguments
    ---
    bot: An instance of `commands.Bot` from discord.py
    """
    twtUsers = []

    with open("data/channels.json") as f:
        channels = json.load(f)

    with open("data/twitter.json") as f:
        customAcc = (json.load(f))["custom"]

    for channel in channels:
        if "twitter" in channels[channel]:
            twtUsers.append(channels[channel]["twitter"])
    
    for account in customAcc:
        twtUsers.append(account)

    twtCred = await TwitterScrape.getCredentials()
    stream = twtPost(bot, twtCred["apiKey"], twtCred["apiSecret"], twtCred["accessKey"], twtCred["accessSecret"])
    await stream.filter(follow=twtUsers)

class twtPost(AsyncStream):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def on_connect(self):
        logging.info("Twitter - Connected to Twitter Tweets stream!")

    async def on_status(self, tweet):
        # print(f"{tweet.user.name}:{tweet.text}")
        # Twitter URL String: f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}"
        # Useful data points: User - tweet.user (dict), Tweet ID - tweet.id_str (string, no "_str" for actual number), Retweet - tweet.retweeted (boolean)
        # Retweeted Tweet - tweet.retweeted_status (Tweet Object), Quote Retweet - tweet.is_quote_status (boolean), Quoted Tweet - tweet.quoted_status (Tweet Object)
        # Like - tweet.favorited (boolean)
        # Wrap the url in "<>" to ensure no embeds are loaded (Which is probably not going to be used as we cannot send two embeds in one message)

        with open("data/servers.json") as f:
            servers = json.load(f)

        if tweet.is_quote_status:
            twtString = f'@{tweet.user.screen_name} just retweeted @{tweet.quoted_status.user.screen_name}\'s tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}\n'\
                        f'Quoted Tweet: https://twitter.com/{tweet.quoted_status.user.screen_name}/status/{tweet.quoted_status.id_str}'
        elif tweet.in_reply_to_screen_name != None:
            twtString = f'@{tweet.user.screen_name} just replied to @{tweet.in_reply_to_screen_name}\'s tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}\n'\
                        f'Replied Tweet: https://twitter.com/{tweet.in_reply_to_screen_name}/status/{tweet.in_reply_to_status_id_str}'
        elif "retweeted_status" in tweet._json:
            twtString = f'@{tweet.user.screen_name} just retweeted @{tweet.retweeted_status.user.screen_name}\'s tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'                
        elif tweet.favorited:
            twtString = f'@{tweet.user.screen_name} just liked @{tweet.retweeted_status.user.screen_name}\' tweet: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'
        else:
            twtString = f'@{tweet.user.screen_name} tweeted just now: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}'

        async def postTweet(ptServer, ptChannel):
            try:
                whurl = await getwebhook(self.bot, servers, ptServer, ptChannel)
                async with aiohttp.ClientSession() as session:
                    webhook = Webhook.from_url(whurl, adapter=AsyncWebhookAdapter(session))
                    await webhook.send(twtString, avatar_url=tweet.user.profile_image_url_https, username=tweet.user.name)
            except Exception as e:
                logging.error(f"Twitter - An error has occurred while publishing stream notification to {channel}!", exc_info=True)

        for server in servers:
            for channel in servers[server]:
                if "twitter" in servers[server][channel]:
                    if tweet.user.id_str in servers[server][channel]["twitter"]:
                        await postTweet(server, channel)
                if "custom" in servers[server][channel]:
                    if tweet.user.id_str in servers[server][channel]["custom"]:
                        await postTweet(server, channel)

    async def on_error(self, status):
        logging.error(f"Twitter - An error has occured!\nTweepy Error: {status}")

def updateWrapper():
    asyncio.run(twtUpdater())

class twtCycle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.subscribed = False
        self.twtIDcheck.start()
        self.twtSubWrapper.start()

    def cog_unload(self):
        self.subscribed = False
        self.twtIDcheck.cancel()
        self.twtSubWrapper.cancel()
    
    def botVar(self):
        return self.bot

    @tasks.loop(minutes=15.0)
    async def twtSubWrapper(self):
        try:
            if not self.subscribed:
                self.subscribed = True
            await twtSubscribe(self.bot)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

    @tasks.loop(minutes=15.0)
    async def twtIDcheck(self):
        logging.info("Starting Twitter ID checks.")
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(pool, updateWrapper)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
        logging.info("Twitter ID checks done.")
