"""Cog: Comandos administrativos (purge, etc.)."""
import logging

import nextcord
from nextcord.ext import commands

log = logging.getLogger(__name__)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(name="cl", description="Apaga mensagens do canal")
    async def cl(
        self,
        interaction: nextcord.Interaction,
        quantidade: int = nextcord.SlashOption(
            name="quantidade",
            description="Quantidade de mensagens para apagar",
            required=True,
            min_value=1,
            max_value=100,
        ),
    ):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Você não tem permissão para apagar mensagens.", ephemeral=True)
            return

        if not isinstance(interaction.channel, nextcord.TextChannel):
            await interaction.response.send_message("❌ Esse comando só funciona em canal de texto.", ephemeral=True)
            return

        await interaction.response.send_message(f"🧹 Apagando {quantidade} mensagens...", ephemeral=True)
        await interaction.channel.purge(limit=quantidade)


def setup(bot: commands.Bot):
    bot.add_cog(AdminCog(bot))
