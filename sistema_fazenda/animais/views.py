import asyncio

import nextcord
from nextcord.ui import View, Button, Select

from sistema_fazenda.animais.config import ANIMAIS
from sistema_fazenda.animais.embeds import (
    criar_embed_entrega_racao,
    criar_embed_local_animais,
)
from sistema_fazenda.animais.services import (
    coletar_produtos,
    pedir_entrega_racao,
)
from sistema_fazenda.embeds import criar_embed_resultado
from sistema_fazenda.emojis import E


async def apagar_depois(msg: nextcord.Message, segundos: int = 60):
    await asyncio.sleep(segundos)

    try:
        await msg.delete()
    except Exception:
        pass


class ConfirmarEntregaRacaoView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @nextcord.ui.button(
        label="Confirmar entrega",
        style=nextcord.ButtonStyle.green,
        emoji="🚚",
    )
    async def confirmar(self, button: Button, interaction: nextcord.Interaction):
        ok, msg = pedir_entrega_racao()

        await interaction.response.send_message(
            embed=criar_embed_resultado("Entrega de ração", msg, ok),
            ephemeral=True,
        )


class LocalAnimaisView(View):
    def __init__(self, local: str):
        super().__init__(timeout=60)
        self.local = local

    @nextcord.ui.button(
        label="Coletar produtos",
        style=nextcord.ButtonStyle.green,
        emoji="🧺",
    )
    async def coletar(self, button: Button, interaction: nextcord.Interaction):
        ok, msg = coletar_produtos(self.local)

        await interaction.response.send_message(
            embed=criar_embed_resultado("Produção animal", msg, ok),
            ephemeral=True,
        )
        
    @nextcord.ui.button(
        label="Abater animal",
        style=nextcord.ButtonStyle.red,
        emoji="🥩",
    )
    async def abater(self, button: Button, interaction: nextcord.Interaction):
        from sistema_fazenda.views import AbaterAnimalView

        await interaction.response.send_message(
            "Escolha o animal para abater:",
            view=AbaterAnimalView(),
            ephemeral=True,
    )     


class IrParaAnimaisSelect(Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(
                label="Celeiro dos animais",
                value="celeiro",
                description="Vacas, cabras e ovelhas",
                emoji="🐄",
            ),
            nextcord.SelectOption(
                label="Galinheiro",
                value="galinheiro",
                description="Galinhas e ovos",
                emoji="🐔",
            ),
            nextcord.SelectOption(
                label="Estábulo",
                value="estabulo",
                description="Cavalos",
                emoji="🐎",
            ),
        ]

        super().__init__(
            placeholder="Escolha o espaço dos animais",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        local = self.values[0]

        await interaction.response.defer(ephemeral=True)

        msg = await interaction.channel.send(
            embed=criar_embed_local_animais(local),
            view=LocalAnimaisView(local),
        )

        await interaction.followup.send(
            "✅ Área dos animais aberta no canal. Ela some em 60s.",
            ephemeral=True,
        )

        asyncio.create_task(apagar_depois(msg, 60))


class IrParaAnimaisView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(IrParaAnimaisSelect())


class EntregaRacaoView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @nextcord.ui.button(
        label="Pedir entrega",
        style=nextcord.ButtonStyle.green,
        emoji="🚚",
    )
    async def pedir(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_entrega_racao(),
            view=ConfirmarEntregaRacaoView(),
            ephemeral=True,
        )
