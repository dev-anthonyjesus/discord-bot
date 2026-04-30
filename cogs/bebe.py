"""Cog: sistema do bebê virtual."""

import asyncio
import logging

import nextcord
from nextcord.ext import commands, tasks

from sistema_bebe.config import CANAL_BEBE_ID
from sistema_bebe.db import get_state, reset_bebe, set_modo_teste, repor_disposicao
from sistema_bebe.embeds import (
    criar_embed_escolha_tracos,
    criar_embed_painel_bebe,
    criar_embed_status,
    criar_embed_noite,
    criar_embed_camera_manha,
)
from sistema_bebe.services import (
    processar_noite,
    processar_manha,
    decair_status_manual,
)
from sistema_bebe.views import (
    EscolhaTracosView,
    BebeCuidadosView,
    atualizar_painel_bebe,
)
from utils.panels import send_or_update_panel

log = logging.getLogger(__name__)


class BebeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_once = False

    def cog_unload(self):
        try:
            self.decaimento_bebe_loop.cancel()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_once:
            return

        self._ready_once = True

        try:
            self.bot.add_view(EscolhaTracosView())
            self.bot.add_view(BebeCuidadosView())
            log.info("[OK] Views persistentes do bebê carregadas.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao registrar views do bebê: {e}")

        try:
            data = get_state()

            if data.get("ativo"):
                await send_or_update_panel(
                    bot=self.bot,
                    channel_id=CANAL_BEBE_ID,
                    panel_key="bebe_panel",
                    embed=criar_embed_painel_bebe(),
                    view=BebeCuidadosView(),
                )

                log.info("[OK] Painel do bebê enviado/atualizado sem spam.")
            else:
                log.info("[OK] Bebê ainda não iniciado; use /painelbebe.")

        except Exception as e:
            log.error(f"[ERRO] Erro ao carregar painel do bebê: {e}")

        try:
            if not self.decaimento_bebe_loop.is_running():
                self.decaimento_bebe_loop.start()
                log.info("[OK] Loop de decaimento do bebê iniciado.")
        except Exception as e:
            log.error(f"[ERRO] Erro ao iniciar loop de decaimento do bebê: {e}")

    @tasks.loop(minutes=30)
    async def decaimento_bebe_loop(self):
        data = get_state()

        if not data.get("ativo"):
            return

        if data.get("noite", {}).get("modo_noturno"):
            return

        decair_status_manual()
        await atualizar_painel_bebe(self.bot)
        log.info("[OK] Necessidades do bebê decaíram automaticamente.")

    @decaimento_bebe_loop.before_loop
    async def before_decaimento_bebe_loop(self):
        await self.bot.wait_until_ready()

    @nextcord.slash_command(
        name="painelbebe",
        description="Inicia o painel de escolha de traços do bebê",
    )
    async def painelbebe(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            await interaction.channel.send(
                embed=criar_embed_escolha_tracos(),
                view=EscolhaTracosView(),
            )

            await interaction.followup.send(
                "🍼 Painel de escolha de traços enviado.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erro ao enviar painel do bebê: `{type(e).__name__}: {e}`",
                ephemeral=True,
            )

    @nextcord.slash_command(
        name="resetbebe",
        description="Reseta o sistema do bebê para testes",
    )
    async def resetbebe(self, interaction: nextcord.Interaction):
        reset_bebe()

        await interaction.response.send_message(
            "♻️ Sistema do bebê resetado. Use `/painelbebe` para começar de novo.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="statusbebe",
        description="Mostra o status atual do bebê",
    )
    async def statusbebe(self, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_status(),
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="debugbebe",
        description="Ativa ou desativa o modo teste do bebê",
    )
    async def debugbebe(
        self,
        interaction: nextcord.Interaction,
        modo: str = nextcord.SlashOption(
            choices={
                "Ativar": "on",
                "Desativar": "off",
            }
        ),
    ):
        valor = modo == "on"
        set_modo_teste(valor)

        await interaction.response.send_message(
            f"🧪 Modo teste {'ativado' if valor else 'desativado'}.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="noitebebe",
        description="Processa manualmente o modo noturno do bebê",
    )
    async def noitebebe(self, interaction: nextcord.Interaction):
        data = processar_noite()

        await atualizar_painel_bebe(self.bot)

        await interaction.response.send_message(
            embed=criar_embed_noite(data),
            ephemeral=False,
        )

    @nextcord.slash_command(
        name="manhabebe",
        description="Envia manualmente o relatório da câmera do quartinho",
    )
    async def manhabebe(self, interaction: nextcord.Interaction):
        resultado = processar_manha()

        await atualizar_painel_bebe(self.bot)

        await interaction.response.send_message(
            embed=criar_embed_camera_manha(resultado),
            ephemeral=False,
        )

    @nextcord.slash_command(
        name="dispor",
        description="Repor disposição dos responsáveis para teste",
    )
    async def dispor(
        self,
        interaction: nextcord.Interaction,
        valor: int = nextcord.SlashOption(
            description="Valor da disposição",
            required=False,
            default=100,
            min_value=0,
            max_value=100,
        ),
    ):
        repor_disposicao(valor)

        await atualizar_painel_bebe(self.bot)

        await interaction.response.send_message(
            f"⚡ Disposição dos responsáveis reposta para `{valor}/100`.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="repor",
        description="Repor disposição dos responsáveis para teste",
    )
    async def repor(
        self,
        interaction: nextcord.Interaction,
        valor: int = nextcord.SlashOption(
            description="Valor da disposição",
            required=False,
            default=100,
            min_value=0,
            max_value=100,
        ),
    ):
        repor_disposicao(valor)

        await atualizar_painel_bebe(self.bot)

        await interaction.response.send_message(
            f"⚡ Disposição dos responsáveis reposta para `{valor}/100`.",
            ephemeral=True,
        )

    @nextcord.slash_command(
        name="decairbebe",
        description="Força a queda das necessidades do bebê para teste",
    )
    async def decairbebe(self, interaction: nextcord.Interaction):
        decair_status_manual()

        await atualizar_painel_bebe(self.bot)

        await interaction.response.send_message(
            "📉 As necessidades do bebê caíram um pouco para teste.",
            ephemeral=True,
        )


def setup(bot: commands.Bot):
    bot.add_cog(BebeCog(bot))
