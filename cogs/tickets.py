"""Cog: comandos slash do sistema de tickets."""

import logging

import nextcord
from nextcord.ext import commands

from sistema_ticket.config import (
    DEFAULT_TICKET_DESCRIPTION,
    load_config,
    save_config,
)
from sistema_ticket.embeds import (
    build_panel_embed,
    build_config_embed,
)
from sistema_ticket.views import TicketPanelView
from sistema_ticket.state import (
    setup_ticket_system,
    ticket_reminder_loop,
)
from utils.panels import send_or_update_panel

log = logging.getLogger(__name__)


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_once:
            return

        self._ready_once = True

        try:
            setup_ticket_system(self.bot)
            log.info("[OK] Sistema de ticket configurado.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao configurar sistema de ticket: {e}")

        try:
            self.bot.add_view(TicketPanelView())
            log.info("[OK] View persistente do ticket carregada.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao carregar view persistente do ticket: {e}")

        try:
            if not ticket_reminder_loop.is_running():
                ticket_reminder_loop.start()
                log.info("[OK] Loop do ticket iniciado.")
            else:
                log.info("[OK] Loop do ticket já estava rodando.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao iniciar loop do ticket: {e}")

        try:
            cfg = load_config()

            await send_or_update_panel(
                bot=self.bot,
                channel_id=cfg["panel_channel_id"],
                panel_key="ticket_panel",
                embed=build_panel_embed(cfg),
                view=TicketPanelView(),
            )

            log.info("[OK] Painel de ticket enviado/atualizado sem spam.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao enviar/atualizar painel de ticket: {e}")

    @nextcord.slash_command(
        name="painelembed",
        description="Atualiza o painel fixo de ticket",
    )
    async def painelembed(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Permissão negada.",
                ephemeral=True,
            )
            return

        try:
            cfg = load_config()

            await send_or_update_panel(
                bot=self.bot,
                channel_id=cfg["panel_channel_id"],
                panel_key="ticket_panel",
                embed=build_panel_embed(cfg),
                view=TicketPanelView(),
            )

            await interaction.response.send_message(
                "✅ Painel de ticket atualizado sem criar spam.",
                ephemeral=True,
            )

        except Exception as e:
            log.error(f"[ERRO] Erro ao atualizar painel de ticket: {e}")

            await interaction.response.send_message(
                f"❌ Erro ao atualizar painel de ticket:\n`{type(e).__name__}: {e}`",
                ephemeral=True,
            )

    @nextcord.slash_command(
        name="ticketconfig",
        description="Configura o sistema de ticket",
    )
    async def ticketconfig(
        self,
        interaction: nextcord.Interaction,
        canal_painel: nextcord.TextChannel,
        cargo_gestor: nextcord.Role,
        canal_logs: nextcord.TextChannel,
        titulo: str,
        descricao: str,
        imagem: str = "",
        nome_ticket: str = "<:tell:1493022801362423931> Report Love",
        descricao_ticket: str = DEFAULT_TICKET_DESCRIPTION,
        imagem_ticket: str = "",
        icone: str = "💗",
        placeholder: str = "Escolha uma opção",
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Permissão negada.",
                ephemeral=True,
            )
            return

        try:
            cfg = load_config()

            cfg.update(
                {
                    "panel_channel_id": canal_painel.id,
                    "manager_role_id": cargo_gestor.id,
                    "log_channel_id": canal_logs.id,
                    "panel_title": titulo,
                    "panel_description": descricao,
                    "panel_image_url": imagem or "",
                    "ticket_name": nome_ticket,
                    "ticket_description": descricao_ticket,
                    "ticket_image_url": imagem_ticket or "",
                    "ticket_icon": icone,
                    "select_placeholder": placeholder,
                }
            )

            save_config(cfg)

            await send_or_update_panel(
                bot=self.bot,
                channel_id=cfg["panel_channel_id"],
                panel_key="ticket_panel",
                embed=build_panel_embed(cfg),
                view=TicketPanelView(),
            )

            await interaction.response.send_message(
                "✅ Configuração salva e painel fixo atualizado.",
                ephemeral=True,
            )

            log.info("[OK] Configuração de ticket salva e painel atualizado.")

        except Exception as e:
            log.error(f"[ERRO] Erro ao salvar configuração de ticket: {e}")

            if interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ Erro ao salvar configuração:\n`{type(e).__name__}: {e}`",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"❌ Erro ao salvar configuração:\n`{type(e).__name__}: {e}`",
                    ephemeral=True,
                )

    @nextcord.slash_command(
        name="ticketcfgview",
        description="Mostra a configuração atual do ticket",
    )
    async def ticketcfgview(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Permissão negada.",
                ephemeral=True,
            )
            return

        try:
            cfg = load_config()
            embed = build_config_embed(cfg, interaction.guild)

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        except Exception as e:
            log.error(f"[ERRO] Erro ao exibir configuração do ticket: {e}")

            await interaction.response.send_message(
                f"❌ Erro ao exibir configuração:\n`{type(e).__name__}: {e}`",
                ephemeral=True,
            )


def setup(bot: commands.Bot):
    bot.add_cog(TicketsCog(bot))
