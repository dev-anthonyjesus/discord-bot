import logging

import nextcord
from nextcord.ui import View, Select, Button

from sistema_bebe.config import (
    ACOES_BASICAS,
    ACOES_PAGAS,
    CANAL_BEBE_ID,
    CARGO_NOIVO_ID,
    CARGO_NOIVA_ID,
    TRACOS,
)
from sistema_bebe.db import set_traco
from sistema_bebe.embeds import (
    criar_embed_escolha_tracos,
    criar_embed_painel_bebe,
    criar_embed_resultado_acao,
    criar_embed_adicionais,
    criar_embed_baby_monitor,
)
from sistema_bebe.emojis import E, PE
from sistema_bebe.services import (
    aplicar_acao_basica,
    aplicar_acao_paga,
    cargo_do_usuario,
)

log = logging.getLogger(__name__)


async def atualizar_painel_bebe(bot: nextcord.Client):
    from utils.panels import send_or_update_panel

    await send_or_update_panel(
        bot=bot,
        channel_id=CANAL_BEBE_ID,
        panel_key="bebe_panel",
        embed=criar_embed_painel_bebe(),
        view=BebeCuidadosView(),
    )


class TracoSelect(Select):
    def __init__(self):
        options = []

        for key, traco in TRACOS.items():
            options.append(
                nextcord.SelectOption(
                    label=traco["label"],
                    value=key,
                    description=traco["descricao"][:100],
                    emoji=PE(traco["emoji"]),
                )
            )

        super().__init__(
            placeholder="Escolha um traço para o bebê",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="bebe_select_traco",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member):
            await interaction.response.send_message(
                "❌ Não consegui identificar seus cargos.",
                ephemeral=True,
            )
            return

        cargo_id = cargo_do_usuario(interaction.user)

        if cargo_id is None:
            await interaction.response.send_message(
                f"❌ Apenas <@&{CARGO_NOIVO_ID}> e <@&{CARGO_NOIVA_ID}> podem escolher traços.",
                ephemeral=True,
            )
            return

        traco_id = self.values[0]
        data = set_traco(cargo_id, traco_id)

        traco = TRACOS[traco_id]

        await interaction.response.send_message(
            f"{E('ok')} Você escolheu {E(traco['emoji'])} **{traco['label']}**.",
            ephemeral=True,
        )

        if data.get("ativo"):
            try:
                await interaction.message.delete()
            except Exception:
                pass

            await atualizar_painel_bebe(interaction.client)
            return

        try:
            await interaction.message.edit(
                embed=criar_embed_escolha_tracos(),
                view=EscolhaTracosView(),
            )
        except Exception as e:
            log.error(f"Erro ao atualizar painel de traços: {e}")


class EscolhaTracosView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TracoSelect())


class CuidadoBasicoSelect(Select):
    def __init__(self):
        options = []

        for key, acao in ACOES_BASICAS.items():
            efeitos = []
            for campo, valor in acao["efeitos"].items():
                sinal = "+" if valor > 0 else ""
                efeitos.append(f"{sinal}{valor} {campo}")

            options.append(
                nextcord.SelectOption(
                    label=acao["label"],
                    value=key,
                    description=f"-{acao['custo_disposicao']} disposição • {' '.join(efeitos)}",
                    emoji=PE(acao["emoji"]),
                )
            )

        super().__init__(
            placeholder="Escolha um cuidado básico",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="bebe_select_cuidado_basico",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member):
            await interaction.response.send_message(
                "❌ Não consegui identificar seus cargos.",
                ephemeral=True,
            )
            return

        acao_id = self.values[0]

        sucesso, msg = aplicar_acao_basica(interaction.user, acao_id)

        await atualizar_painel_bebe(interaction.client)

        await interaction.response.send_message(
            embed=criar_embed_resultado_acao(msg, sucesso),
            ephemeral=True,
        )


class AcoesPagasSelect(Select):
    def __init__(self):
        options = []

        for key, acao in ACOES_PAGAS.items():
            options.append(
                nextcord.SelectOption(
                    label=acao["label"],
                    value=key,
                    description=f"{acao['preco']} moedas • efeitos no bebê",
                    emoji=PE(acao["emoji"]),
                )
            )

        super().__init__(
            placeholder="Escolha uma ação adicional",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member):
            await interaction.response.send_message(
                "❌ Não consegui identificar seus cargos.",
                ephemeral=True,
            )
            return

        acao_id = self.values[0]

        sucesso, msg = aplicar_acao_paga(interaction.user, acao_id)

        await atualizar_painel_bebe(interaction.client)

        await interaction.response.send_message(
            embed=criar_embed_resultado_acao(msg, sucesso),
            ephemeral=True,
        )


class AcoesPagasView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(AcoesPagasSelect())


class BebeCuidadosView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CuidadoBasicoSelect())

    @nextcord.ui.button(
        label="Baby Monitor",
        style=nextcord.ButtonStyle.blurple,
        emoji=PE("camera"),
        custom_id="bebe_baby_monitor",
    )
    async def baby_monitor(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_baby_monitor(),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Adicionais",
        style=nextcord.ButtonStyle.gray,
        emoji=PE("adicionais"),
        custom_id="bebe_acao_adicionais",
    )
    async def adicionais(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_adicionais(),
            view=AcoesPagasView(),
            ephemeral=True,
        )
