import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from services.worker_client import LuciferWorkerClient

logger = logging.getLogger("TokenRefresher.RefresherCog")

class RefreshModal(discord.ui.Modal, title="Refresh LToken Growtopia"):
    token_input = discord.ui.TextInput(
        label="Masukkan LToken Lama Kamu",
        style=discord.TextStyle.paragraph,
        placeholder="Tempelkan LToken lama yang ingin kamu perbarui...",
        required=True,
        min_length=10,
        max_length=500
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_token_refresh(interaction, self.token_input.value.strip())

class RefreshPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Input LToken Lama",
        style=discord.ButtonStyle.primary,
        custom_id="btn_refresh_ltoken_modal",
        emoji="⚡"
    )
    async def btn_refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RefreshModal(self.cog))

class RefresherCog(commands.Cog, name="Refresher"):
    """Cog utama untuk menangani request refresh LToken dari user/buyer."""

    def __init__(self, bot):
        self.bot = bot
        self.worker_client = LuciferWorkerClient()

    async def process_token_refresh(self, interaction: discord.Interaction, old_token: str):
        """Logika inti memproses refresh token."""
        await interaction.response.defer(ephemeral=True)

        db = self.bot.db
        account = await db.find_account_by_token(old_token)

        if not account:
            embed_err = discord.Embed(
                title="Token Tidak Ditemukan",
                description="LToken yang kamu masukkan tidak terdaftar di sistem kami atau belum pernah disewakan.",
                color=0xE74C3C
            )
            embed_err.add_field(
                name="Tips",
                value="Pastikan kamu menyalin LToken aktif yang diberikan saat transaksi atau hubungi admin jika butuh bantuan.",
                inline=False
            )
            await interaction.followup.send(embed=embed_err, ephemeral=True)
            return

        # Validasi kepemilikan akun (jika di-assign ke user tertentu)
        assigned_user = account.get("assigned_user_id")
        if assigned_user and assigned_user != interaction.user.id and interaction.user.id not in self.bot.owner_ids:
            embed_auth = discord.Embed(
                title="Akses Ditolak",
                description="Akun ini terdaftar atas nama pengguna lain. Kamu tidak memiliki izin me-refresh token ini.",
                color=0xE74C3C
            )
            await interaction.followup.send(embed=embed_auth, ephemeral=True)
            return

        # Beri notifikasi proses sedang berlangsung
        desc_loading = f"Sedang menghubungkan ke Worker Lucifer untuk login akun **`{account['account_label']}`**.\nMohon tunggu sekitar 5 - 15 detik..."
        embed_loading = discord.Embed(
            title="Memproses Refresh Token...",
            description=desc_loading,
            color=0xF1C40F
        )
        msg_loading = await interaction.followup.send(embed=embed_loading, ephemeral=True)

        # Eksekusi refresh via Worker
        success, new_token, err_msg = await self.worker_client.refresh_ltoken(account)

        if success and new_token:
            # Update database
            await db.update_account_token(account["id"], new_token)
            await db.log_refresh(account["id"], interaction.user.id, old_token, new_token, "SUCCESS")

            desc_success = f"LToken untuk akun **`{account['account_label']}`** berhasil diperbarui.\nGunakan token baru di bawah ini pada executor kamu."
            embed_success = discord.Embed(
                title="LToken Berhasil Di-refresh!",
                description=desc_success,
                color=0x2ECC71,
                timestamp=datetime.utcnow()
            )
            embed_success.add_field(
                name="LToken Baru (Klik untuk Copy)",
                value=f"```{new_token}```",
                inline=False
            )
            embed_success.add_field(
                name="Akun",
                value=f"`{account['account_label']}` ({account['account_type']})",
                inline=True
            )
            embed_success.add_field(
                name="Masa Aktif Token",
                value="~6 Jam dari sekarang",
                inline=True
            )
            embed_success.set_footer(text="Token Refresher • Simpan token baru ini dengan aman!")
            await interaction.followup.send(embed=embed_success, ephemeral=True)
        else:
            # Gagal refresh
            await db.log_refresh(account["id"], interaction.user.id, old_token, None, "FAILED", err_msg)
            desc_fail = f"Worker gagal mengambil token baru untuk akun **`{account['account_label']}`**.\n\n**Detail Error:**\n`{err_msg}`"
            embed_fail = discord.Embed(
                title="Gagal Me-refresh Token",
                description=desc_fail,
                color=0xE74C3C
            )
            embed_fail.add_field(
                name="Apa yang harus dilakukan?",
                value="1. Coba beberapa saat lagi jika server Growtopia sedang sibuk.\n2. Hubungi admin jika akun terkena proteksi/suspended.",
                inline=False
            )
            await interaction.followup.send(embed=embed_fail, ephemeral=True)

    @app_commands.command(name="refresh_ltoken", description="Me-refresh LToken Growtopia menggunakan token lama kamu")
    @app_commands.describe(ltoken="LToken lama yang ingin diperbarui")
    async def cmd_refresh_ltoken(self, interaction: discord.Interaction, ltoken: str):
        await self.process_token_refresh(interaction, ltoken.strip())

    @app_commands.command(name="refresh_panel", description="[OWNER] Kirimkan panel interaktif refresh LToken ke channel")
    @app_commands.default_permissions(administrator=True)
    async def cmd_refresh_panel(self, interaction: discord.Interaction):
        if interaction.user.id not in self.bot.owner_ids and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Hanya admin yang dapat menggunakan perintah ini.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Layanan Auto Refresh LToken Growtopia",
            description=(
                "Token login Growtopia (`ltoken`) memiliki masa aktif sekitar **6 jam**.\n\n"
                "Jika token akun bot kamu sudah kedaluwarsa atau bot kamu terputus dari game, "
                "kamu bisa mendapatkan token baru yang masih segar secara instan di sini!\n\n"
                "**Cara Menggunakan:**\n"
                "1. Klik tombol **`[ Input LToken Lama ]`** di bawah.\n"
                "2. Masukkan LToken lama yang kamu miliki.\n"
                "3. Sistem akan memvalidasi dan mengirimkan LToken baru secara otomatis."
            ),
            color=0x3498DB
        )
        embed.set_footer(text="Auto LToken Refresher • Cepat, Aman & Praktis")
        view = RefreshPanelView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Panel berhasil dikirim ke channel ini!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RefresherCog(bot))
