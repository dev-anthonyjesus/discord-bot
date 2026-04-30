import asyncio

import nextcord
from nextcord.ui import View, Select, Button

from sistema_fazenda.embeds import criar_embed_resultado
from sistema_fazenda.funcionarios.config import FUNCIONARIOS
from sistema_fazenda.funcionarios.embeds import criar_embed_funcionarios
from sistema_fazenda.funcionarios.services import (
    contratar_funcionario,
    demitir_funcionario,
    get_funcionarios_ativos,
)


async def resposta_temporaria(
    interaction: nextcord.Interaction,
    embed: nextcord.Embed,
    segundos: int = 5,
):
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await asyncio.sleep(segundos)

    try:
        await interaction.delete_original_message()
    except Exception:
        pass


class ContratarFuncionarioSelect(Select):
    def __init__(self):
        ativos = get_funcionarios_ativos()
        options = []

        for funcionario_id, funcionario in FUNCIONARIOS.items():
            if funcionario_id in ativos:
                continue

            options.append(
                nextcord.SelectOption(
                    label=funcionario["nome"],
                    value=funcionario_id,
                    description=f"Contrato {funcionario['contrato']} • temporada {funcionario['custo_temporada']}",
                    emoji=funcionario["emoji"],
                )
            )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Nenhum disponível",
                    value="none",
                    description="Todos já estão contratados ou sem vagas.",
                    emoji="❌",
                )
            ]

        super().__init__(
            placeholder="Escolha um funcionário para contratar",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                "Nenhum funcionário disponível para contratar.",
                ephemeral=True,
            )
            return

        funcionario_id = self.values[0]
        ok, msg = contratar_funcionario(interaction.user, funcionario_id)

        await resposta_temporaria(
            interaction,
            criar_embed_resultado("Contratação", msg, ok),
            5,
        )


class DemitirFuncionarioSelect(Select):
    def __init__(self):
        ativos = get_funcionarios_ativos()
        options = []

        for funcionario_id in ativos:
            funcionario = FUNCIONARIOS.get(funcionario_id)

            if not funcionario:
                continue

            options.append(
                nextcord.SelectOption(
                    label=funcionario["nome"],
                    value=funcionario_id,
                    description="Demitir este funcionário",
                    emoji=funcionario["emoji"],
                )
            )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Nenhum contratado",
                    value="none",
                    description="Não há funcionários para demitir.",
                    emoji="❌",
                )
            ]

        super().__init__(
            placeholder="Escolha um funcionário para demitir",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                "Não há funcionários contratados.",
                ephemeral=True,
            )
            return

        funcionario_id = self.values[0]
        ok, msg = demitir_funcionario(interaction.user, funcionario_id)

        await resposta_temporaria(
            interaction,
            criar_embed_resultado("Demissão", msg, ok),
            5,
        )


class ContratarFuncionarioView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ContratarFuncionarioSelect())


class DemitirFuncionarioView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DemitirFuncionarioSelect())


class FuncionariosView(View):
    def __init__(self):
        super().__init__(timeout=180)

    @nextcord.ui.button(
        label="Contratar funcionário",
        style=nextcord.ButtonStyle.green,
        emoji="🤝",
    )
    async def contratar(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha quem deseja contratar:",
            view=ContratarFuncionarioView(),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Demitir funcionário",
        style=nextcord.ButtonStyle.red,
        emoji="📄",
    )
    async def demitir(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha quem deseja demitir:",
            view=DemitirFuncionarioView(),
            ephemeral=True,
        )
