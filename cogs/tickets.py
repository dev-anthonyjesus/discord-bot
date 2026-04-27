"""Cog: Comandos slash do sistema de tickets."""
import logging

import nextcord
from nextcord.ext import commands

from ticket_system import (
    TicketPanelView,
    build_panel_embed,
    build_config_embed,
    load_config,
    save_config,
    setup_ticket_system,
    ticket_reminder_loop,
)
from utils.panels import send_or_update_panel

log = logging.getLogger(__name__)


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        setup_ticket_system(self.bot)
        self.bot.add_view(TicketPanelView())
        log.info("View persistente do ticket carregada.")

        if not ticket_reminder_loop.is_running():
            ticket_reminder_loop.start()
            log.info("Loop do ticket iniciado.")

        try:
            cfg = load_config()
            await send_or_update_panel(
                bot=self.bot,
                channel_id=cfg["panel_channel_id"],
                panel_key="ticket_panel",
                embed=build_panel_embed(cfg),
                view=TicketPanelView(),
            )
            log.info("Painel de ticket enviado/atualizado.")
        except Exception as e:
            log.error(f"Erro ao enviar/atualizar painel de ticket: {e}")

    @nextcord.slash_command(name="painelembed", description="Envia o painel de ticket")
    async def painelembed(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Negado.", ephemeral=True)
            return

        cfg   = load_config()
        canal = interaction.guild.get_channel(cfg["panel_channel_id"])
        if isinstance(canal, nextcord.TextChannel):
            await canal.send(embed=build_panel_embed(cfg), view=TicketPanelView())
            await interaction.response.send_message("Painel enviado.", ephemeral=True)
        else:
            await interaction.response.send_message("Canal do painel inválido.", ephemeral=True)

    @nextcord.slash_command(name="ticketconfig", description="Configura o sistema de ticket")
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
        descricao_ticket: str = ""Espaço para ajustes na nossa convivência. O diálogo é a nossa base. "
    "Regras rápidas: Respeito acima de tudo. O que é dito aqui, morre aqui. "
    "Se for urgente, priorize a call. Clique no botão abaixo para abrir um espaço de conversa."",
        imagem_ticket: str = "",
        icone: str = "💗",
        placeholder: str = "Escolha uma opção",
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Permissão negada.", ephemeral=True)
            return

        cfg = load_config()
        cfg.update({
            "panel_channel_id":   canal_painel.id,
            "manager_role_id":    cargo_gestor.id,
            "log_channel_id":     canal_logs.id,
            "panel_title":        titulo,
            "panel_description":  descricao,
            "panel_image_url":    imagem or "",
            "ticket_name":        nome_ticket,
            "ticket_description": descricao_ticket,
            "ticket_image_url":   imagem_ticket or "",
            "ticket_icon":        icone,
            "select_placeholder": placeholder,
        })
        save_config(cfg)
        await interaction.response.send_message("Configuração salva.", ephemeral=True)

    @nextcord.slash_command(name="ticketcfgview", description="Mostra a configuração atual do ticket")
    async def ticketcfgview(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Permissão negada.", ephemeral=True)
            return

        cfg   = load_config()
        embed = build_config_embed(cfg, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(TicketsCog(bot))
