import asyncio
import os
import discord
from typing import List, Tuple, Optional
from discord.ext import tasks, commands
from motor.motor_asyncio import AsyncIOMotorClient
from core.bot_config import Git

RELEASE_URL = 'https://api.github.com/repos/{owner}/{repo}/releases/latest'


class DatabaseWorkers(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.db_client: AsyncIOMotorClient = AsyncIOMotorClient(os.getenv('DB_CONNECTION'))
        self.db: AsyncIOMotorClient = self.db_client.store.guilds
        self.release_feed_worker.start()

    @tasks.loop(minutes=45)
    async def release_feed_worker(self) -> None:  # TODO Chunk this shit
        async for doc in self.db.find({}):
            changed: bool = False
            update: list = []
            for item in doc['feed']:
                res: Optional[dict] = await Git.get_latest_release(item['repo'])
                if res:
                    if (t := res['release']['tagName']) != item['release']:
                        await self.handle_feed_item(doc, item, res)
                        changed = True
                    update.append((item['repo'], t))
                else:
                    await self.handle_missing_item(doc, item)
                await asyncio.sleep(2)
            if changed:
                await self.update_with_data(doc['guild_id'], update)

    async def handle_feed_item(self, doc: dict, item: dict, new_release: dict) -> None:  # TODO Finish this
        embed = discord.Embed(
            color=new_release['color'],
            title=f'New {item["repo"]} release!',
            url=new_release['release']['url']
        )
        if new_release['usesCustomOpenGraphImage']:
            embed.set_image(url=new_release['openGraphImageUrl'])

        success = await self.doc_send(doc, embed)
        if not success:
            print('fuck')

    async def update_with_data(self, guild_id: int, to_update: List[Tuple[str]]) -> None:
        await self.db.find_one_and_update({'guild_id': guild_id}, {
            '$set': {'feed': [dict(repo=repo, release=release) for repo, release in to_update]}})

    async def handle_missing_item(self, doc: dict, item: dict) -> None:  # TODO Details here
        embed = discord.Embed(
            color=0xda4353,
            title=f'One of your saved repos was deleted/renamed!'
        )
        if len(doc['feed']) == 1:
            await self.db.find_one_and_delete(doc)
        else:
            await self.db.update_one(doc, {'$pull': {'feed': item}})
        success = await self.doc_send(doc, embed)
        if not success:
            print('fuck')

    @release_feed_worker.before_loop
    async def release_feed_worker_before_loop(self) -> None:
        print('Release worker sleeping until the bot is ready...')
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.db.find_one_and_delete({'guild_id': guild.id})

    async def doc_send(self, doc: dict, embed: discord.Embed) -> bool:
        channel: discord.TextChannel = await self.bot.fetch_channel(doc['channel_id'])
        if channel:
            await channel.send(embed=embed)
            return True
        return False


def setup(bot: commands.Bot) -> None:
    bot.add_cog(DatabaseWorkers(bot))