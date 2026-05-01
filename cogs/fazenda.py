"""Cog: sistema da fazenda."""

import logging

import nextcord
from nextcord.ext import commands, tasks

from sistema_fazenda.config import (
    CANAL_FARMHOUSE_ID,
    CANAL_CANGACO_ID,
    CANAL_PREFEITURA_ID,
)
from sistema_fazenda.db import reset_fazenda, repor_energia, marcar_tudo_pronto
from sistema_fazenda.embeds import (
    criar_embed_farmhouse,
    criar_embed_cangaco,
    criar_embed_prefeitura,
)
from sistema_fazenda.views import (
    FarmhouseView,
    CangacoView,
    PrefeituraView,
    atualizar_painel_farmhouse,
)
from utils.panels import send_or_update_panel

from sistema_fazenda.animais.services import marcar_animais_prontos

log = logging.getLogger(__name__)


class FazendaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False

    def cog_unload(self):
        try:
            self.atualizar_farmhouse_loop.cancel()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_once:
            return

        self._ready_once = True

        try:
            self.bot.add_view(FarmhouseView())
            self.bot.add_view(CangacoView())
            self.bot.add_view(PrefeituraView())
            log.info("[OK] Views persistentes da fazenda carregadas.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao registrar views da fazenda: {e}")

        try:
            canal_farmhouse = self.bot.get_channel(CANAL_FARMHOUSE_ID)
            guild = canal_farmhouse.guild if canal_farmhouse else None

            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_FARMHOUSE_ID,
                panel_key="fazenda_farmhouse_panel",
                embed=criar_embed_farmhouse(guild),
                view=FarmhouseView(),
            )

            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_CANGACO_ID,
                panel_key="fazenda_cangaco_panel",
                embed=criar_embed_cangaco(),
                view=CangacoView(),
            )

            await send_or_update_panel(
                bot=self.bot,
                channel_id=CANAL_PREFEITURA_ID,
                panel_key="fazenda_prefeitura_panel",
                embed=criar_embed_prefeitura(),
                view=PrefeituraView(),
            )

            log.info("[OK] Painéis da fazenda enviados/atualizados sem spam.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao enviar painéis da fazenda: {e}")

        try:
            if not self.atualizar_farmhouse_loop.is_running():
                self.atualizar_farmhouse_loop.start()
                log.info("[OK] Loop de atualização da farmhouse iniciado.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao iniciar loop da farmhouse: {e}")

    @tasks.loop(minutes=1)
    async def atualizar_farmhouse_loop(self):
        await atualizar_painel_farmhouse(self.bot)

    @atualizar_farmhouse_loop.before_loop
    async def before_atualizar_farmhouse_loop(self):
        await self.bot.wait_until_ready()

    @nextcord.slash_command(
        name="rfazenda",
        description="Resetar a fazenda para testes",
    )
    async def rfazenda(self, interaction: nextcord.Interaction):
        reset_fazenda()

        await atualizar_painel_farmhouse(self.bot)

        await interaction.response.send_message(
            "♻️ Fazenda resetada para testes.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="resetfazenda",
        description="Resetar a fazenda para testes",
    )
    async def resetfazenda(self, interaction: nextcord.Interaction):
        reset_fazenda()

        await atualizar_painel_farmhouse(self.bot)

        await interaction.response.send_message(
            "♻️ Fazenda resetada para testes.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="energiafazenda",
        description="Repor energia da fazenda para testes",
    )
    async def energiafazenda(
        self,
        interaction: nextcord.Interaction,
        valor: int = nextcord.SlashOption(
            description="Valor da energia",
            required=False,
            default=100,
            min_value=0,
            max_value=100,
        ),
    ):
        repor_energia(valor)

        await atualizar_painel_farmhouse(self.bot)

        await interaction.response.send_message(
            f"⚡ Energia da fazenda reposta para `{valor}/100`.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="prontofazenda",
        description="Deixa todas as plantações prontas para teste",
    )
    async def prontofazenda(self, interaction: nextcord.Interaction):
        marcar_tudo_pronto()

        await atualizar_painel_farmhouse(self.bot)

        await interaction.response.send_message(
            "✅ Todas as plantações foram marcadas como prontas para colher.",
            ephemeral=True,
        )
    @nextcord.slash_command(
    name="prontotudo",
    description="Deixa plantações e animais prontos para teste",
)
    async def prontotudo(self, interaction: nextcord.Interaction):
        marcar_tudo_pronto()
        marcar_animais_prontos()

        await atualizar_painel_farmhouse(self.bot)

        await interaction.response.send_message(
        "✅ Tudo foi marcado como pronto para teste: plantações e animais.",
        ephemeral=True,
    )


def setup(bot: commands.Bot):
    bot.add_cog(FazendaCog(bot))
