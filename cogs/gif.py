"""Cog: Compressão de GIF/imagem (fig) e painel de GIF."""
import asyncio
import logging

import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button

from utils.constants import CANAL_COMANDOS, GIFSICLE_PATH
from utils.image_utils import compress_static_image, compress_gif_quality, compress_gif_force
from utils.panels import send_or_update_panel
import os

log = logging.getLogger(__name__)


# ── Embed ─────────────────────────────────────────────────────────────────────

def create_gif_panel_embed() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="🖼️ Compressor de GIF",
        description=(
            "Envie seu GIF e eu vou tentar comprimir para **até 512 KB**.\n\n"
            "Escolha abaixo o modo que você quer usar."
        ),
        color=0xFF69B4,
    )
    embed.add_field(name="🖼️ Comprimir normal", value="Tenta reduzir o tamanho sem destruir muito a animação.", inline=False)
    embed.add_field(name="💥 Forçar 512KB",      value="Se precisar, reduz qualidade, cores, escala e até frames para caber em 512 KB.", inline=False)
    embed.set_footer(text="Painel de compressão de GIF")
    return embed


# ── View do painel ────────────────────────────────────────────────────────────

class GifPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _processar_gif(self, interaction: nextcord.Interaction, modo: str):
        await interaction.response.send_message(
            "📩 Envie um **GIF** neste canal em até **2 minutos**.",
            ephemeral=True,
        )

        def check(msg: nextcord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and len(msg.attachments) > 0
            )

        try:
            msg = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado. Clique no botão novamente.", ephemeral=True)
            return

        attachment = msg.attachments[0]
        if not attachment.filename.lower().endswith(".gif"):
            await interaction.followup.send("❌ O arquivo enviado não é um GIF.", ephemeral=True)
            return

        texto = "🛠️ Comprimindo o GIF sem destruir muito..." if modo == "quality" else "💥 Forçando compressão para 512 KB..."
        await interaction.followup.send(texto, ephemeral=True)

        try:
            data   = await attachment.read()
            result = compress_gif_quality(data) if modo == "quality" else compress_gif_force(data)
            nome   = "gif_comprimido_qualidade.gif" if modo == "quality" else "gif_comprimido_forcado.gif"
            size_kb = round(result.getbuffer().nbytes / 1024, 1)
            result.seek(0)
            await interaction.followup.send(
                content=f"✅ GIF pronto. Tamanho final: **{size_kb} KB**",
                file=nextcord.File(result, filename=nome),
                ephemeral=True,
            )
            log.info(f"GIF comprimido | modo={modo} | user={interaction.user} | tamanho={size_kb} KB")
        except Exception as e:
            log.error(f"Erro ao comprimir GIF | modo={modo} | erro={e}")
            await interaction.followup.send(f"❌ Falha ao comprimir o GIF.\n`{e}`", ephemeral=True)

    @nextcord.ui.button(label="🖼️ Comprimir normal", style=nextcord.ButtonStyle.green, custom_id="gif_panel_normal")
    async def comprimir_normal(self, button: Button, interaction: nextcord.Interaction):
        await self._processar_gif(interaction, "quality")

    @nextcord.ui.button(label="💥 Forçar 512KB", style=nextcord.ButtonStyle.red, custom_id="gif_panel_force")
    async def comprimir_forcado(self, button: Button, interaction: nextcord.Interaction):
        await self._processar_gif(interaction, "force")


# ── Cog ───────────────────────────────────────────────────────────────────────

class GifCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(GifPanelView())
        log.info("View persistente do painel de GIF carregada.")

        if os.path.exists(GIFSICLE_PATH):
            log.info(f"gifsicle encontrado em: {GIFSICLE_PATH}")
        else:
            log.warning(f"gifsicle não encontrado em: {GIFSICLE_PATH}")

        try:
            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_COMANDOS,
                panel_key="gif_panel",
                embed=create_gif_panel_embed(),
                view=GifPanelView(),
            )
            log.info("Painel de GIF enviado/atualizado.")
        except Exception as e:
            log.error(f"Erro no painel de GIF: {e}")

    # ── Slash command: /fig ───────────────────────────────────────────────────

    @nextcord.slash_command(name="fig", description="Comprime imagem ou GIF para até 512 KB")
    async def fig(self, interaction: nextcord.Interaction):
        await interaction.response.send_message("Envie o anexo neste canal em até 2 minutos.", ephemeral=True)

        def check(msg: nextcord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and len(msg.attachments) > 0
            )

        try:
            msg = await self.bot.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado. Use `/fig` novamente.", ephemeral=True)
            return

        attachment = msg.attachments[0]
        filename   = attachment.filename.lower()

        if not filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            await interaction.followup.send("❌ Envie PNG, JPG, WEBP ou GIF.", ephemeral=True)
            return

        await interaction.followup.send("🛠️ Processando arquivo...", ephemeral=True)

        try:
            data = await attachment.read()
            if filename.endswith(".gif"):
                result   = compress_gif_force(data)
                out_name = "figurinha.gif"
            else:
                result   = compress_static_image(data)
                out_name = "figurinha.png"

            size_kb = round(result.getbuffer().nbytes / 1024, 1)
            result.seek(0)
            await interaction.followup.send(
                content=f"✅ Pronto. Tamanho final: **{size_kb} KB**",
                file=nextcord.File(result, filename=out_name),
                ephemeral=True,
            )
        except Exception as e:
            log.error(f"Erro no /fig: {e}")
            await interaction.followup.send(f"❌ Erro ao processar o arquivo: `{e}`", ephemeral=True)

    # ── Comando: painelgif ────────────────────────────────────────────────────

    @commands.command()
    async def painelgif(self, ctx: commands.Context):
        if ctx.channel.id != CANAL_COMANDOS:
            await ctx.send("❌ Esse comando só pode ser usado no canal de comandos.")
            return
        await ctx.send(embed=create_gif_panel_embed(), view=GifPanelView())
        log.info("Painel de GIF enviado manualmente.")


def setup(bot: commands.Bot):
    bot.add_cog(GifCog(bot))
