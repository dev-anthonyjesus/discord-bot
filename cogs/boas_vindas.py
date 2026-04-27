"""Cog: Boas-vindas (welcome embed)."""
import logging

from nextcord.ext import commands

from bemvindo import create_welcome_embed
from utils.constants import CANAL_WELCOME
from utils.panels import send_or_update_panel

log = logging.getLogger(__name__)


class BoasVindasCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_WELCOME,
                panel_key="welcome_panel",
                embed=create_welcome_embed(self.bot, self.bot.user),
                view=None,
            )
            log.info("Painel de boas-vindas enviado/atualizado.")
        except Exception as e:
            log.error(f"Erro no painel de boas-vindas: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(BoasVindasCog(bot))
