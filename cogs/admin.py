import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.worker_client import LuciferWorkerClient

logger = logging.getLogger("TokenRefresher.AdminCog")

class AdminCog(commands.Cog, name="Admin"):
    """Cog untuk mengelola akun bot di database dan memeriksa status worker."""

    def __init__(self, bot):
        self.bot = bot
        self.worker_client = LuciferWorkerClient()

    def is_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in self.bot.owner_ids or interaction.user.guild_permissions.administrator

    @app_commands.command(name="add_account", description="[ADMIN] Mendaftarkan akun bot baru ke database")
    @app_commands.describe(
        label="Nama/Label bot (misal: Bot_Gmail_01)",
        email_or_growid="Email Gmail atau GrowID",
        password="Password akun (akan dienkripsi otomatis)",
        account_type="Tipe akun: GOOGLE / LEGACY / UBISOFT",
        recovery="Recovery email / phone jika ada (opsional)",
        initial_token="LToken awal yang sedang aktif (opsional)",
        assigned_user="Member Discord yang menyewa akun (opsional)"
    )
    async def cmd_add_account(
        self,
        interaction: discord.Interaction,
        label: str,
        email_or_growid: str,
        password: str,
        account_type: str = "GOOGLE",
        recovery: str = "",
        initial_token: str = "",
        assigned_user: discord.Member = None
    ):
        if not self.is_owner(interaction):
            await interaction.response.send_message("Akses ditolak. Hanya owner/admin.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        db = self.bot.db

        user_id = assigned_user.id if assigned_user else None
        token_val = initial_token.strip() if initial_token.strip() else None

        acc_id = await db.add_account(
            account_label=label.strip(),
            email_or_growid=email_or_growid.strip(),
            password=password.strip(),
            account_type=account_type.upper(),
            recovery=recovery.strip(),
            initial_token=token_val,
            assigned_user_id=user_id
        )

        embed = discord.Embed(
            title="Akun Berhasil Didaftarkan!",
            color=0x2ECC71
        )
        embed.add_field(name="ID Akun", value=f"`#{acc_id}`", inline=True)
        embed.add_field(name="Label", value=f"`{label}`", inline=True)
        embed.add_field(name="Tipe", value=f"`{account_type.upper()}`", inline=True)
        embed.add_field(name="Email / ID", value=f"`{email_or_growid}`", inline=False)
        if token_val:
            embed.add_field(name="Initial LToken", value=f"```{token_val}```", inline=False)
        if assigned_user:
            embed.add_field(name="Penyewa", value=assigned_user.mention, inline=True)

        embed.set_footer(text="Password telah disimpan dalam bentuk terenkripsi.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list_accounts", description="[ADMIN] Melihat daftar seluruh akun bot yang terdaftar")
    async def cmd_list_accounts(self, interaction: discord.Interaction):
        if not self.is_owner(interaction):
            await interaction.response.send_message("Akses ditolak.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        accounts = await self.bot.db.list_all_accounts()

        if not accounts:
            await interaction.followup.send("Belum ada akun yang terdaftar di database.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Daftar Akun Bot ({len(accounts)} Akun)",
            color=0x3498DB
        )

        for acc in accounts[:15]:
            token_display = f"`{acc['current_ltoken'][:15]}...`" if acc['current_ltoken'] else "*Belum ada token*"
            user_display = f"<@{acc['assigned_user_id']}>" if acc['assigned_user_id'] else "*Belum disewa*"
            field_val = f"User: {user_display}\nToken: {token_display}"
            embed.add_field(
                name=f"#{acc['id']} • {acc['account_label']} ({acc['account_type']})",
                value=field_val,
                inline=False
            )

        if len(accounts) > 15:
            embed.set_footer(text=f"Menampilkan 15 dari total {len(accounts)} akun.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="worker_status", description="[ADMIN] Memeriksa koneksi ke Worker Lucifer")
    async def cmd_worker_status(self, interaction: discord.Interaction):
        if not self.is_owner(interaction):
            await interaction.response.send_message("Akses ditolak.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        online, msg = await self.worker_client.check_health()

        embed = discord.Embed(
            title="Status Worker Lucifer",
            color=0x2ECC71 if online else 0xE74C3C
        )
        embed.add_field(name="Status", value="ONLINE & READY" if online else "OFFLINE / ERROR", inline=False)
        embed.add_field(name="URL Worker", value=f"`{self.worker_client.base_url}`", inline=False)
        embed.add_field(name="Respons", value=f"```{msg}```", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
