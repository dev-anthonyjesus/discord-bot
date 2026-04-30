"""Cog: painel fixo da geladeira dos lembretes."""

import logging

from nextcord.ext import commands

from sistema_lembretes.config import CANAL_LEMBRETES_ID
from sistema_lembretes.embeds import criar_embed_lembretes
from sistema_lembretes.views import LembretesView
from utils.panels import send_or_update_panel

log = logging.getLogger(__name__)


class LembretesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_once:
            return

        self._ready_once = True

        try:
            self.bot.add_view(LembretesView())
            log.info("[OK] View persistente de lembretes carregada.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao registrar view de lembretes: {e}")

        try:
            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_LEMBRETES_ID,
                panel_key="lembretes_panel",
                embed=criar_embed_lembretes(),
                view=LembretesView(),
            )

            log.info("[OK] Painel de lembretes enviado/atualizado sem spam.")
        except Exception as e:
            log.error(f"[ERRO] Erro no painel de lembretes: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(LembretesCog(bot))
