import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Konfigurasi Path dan Logging
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TokenRefresher.Main")

import discord
from discord.ext import commands
from database.manager import DatabaseManager

class TokenRefresherBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.db = DatabaseManager(BASE_DIR / "database" / "refresher.db")
        self.guild_id = int(os.getenv("DISCORD_GUILD_ID", 0))

        # Parsing Owner IDs
        raw_owners = os.getenv("OWNER_IDS", "")
        self.owner_ids = set()
        for oid in raw_owners.split(","):
            oid = oid.strip()
            if oid.isdigit():
                self.owner_ids.add(int(oid))

    async def setup_hook(self):
        # 1. Inisialisasi Database SQLite
        logger.info("Menghubungkan dan menginisialisasi database SQLite...")
        await self.db.init_db(BASE_DIR / "database" / "schema.sql")

        # 2. Muat Cogs
        cogs = ["cogs.refresher", "cogs.admin"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog '{cog}' berhasil dimuat.")
            except Exception as e:
                logger.error(f"Gagal memuat cog '{cog}': {e}", exc_info=True)

        # 3. Daftarkan persistent view (RefreshPanelView)
        from cogs.refresher import RefreshPanelView, RefresherCog
        refresher_cog = self.get_cog("Refresher")
        if refresher_cog:
            self.add_view(RefreshPanelView(refresher_cog))

        # 4. Sinkronisasi Slash Commands
        if self.guild_id:
            guild_obj = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            logger.info(f"Sinkronisasi {len(synced)} slash commands instan ke Guild ID: {self.guild_id}")
        else:
            synced = await self.tree.sync()
            logger.info(f"Sinkronisasi {len(synced)} slash commands secara global.")

    async def on_ready(self):
        logger.info("==================================================")
        logger.info(f"🤖 Bot Token Refresher Online sebagai: {self.user.name} (ID: {self.user.id})")
        logger.info(f"Discord.py Version : {discord.__version__}")
        logger.info("==================================================")

async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("Token bot Discord belum diatur di file .env! Harap masukkan DISCORD_BOT_TOKEN.")
        return

    bot = TokenRefresherBot()
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh pengguna.")
