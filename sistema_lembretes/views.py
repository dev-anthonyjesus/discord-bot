from datetime import datetime

import nextcord
from nextcord.ui import View, Button, Modal, TextInput, Select

from sistema_economia.db import add_mimos
from sistema_lembretes.config import (
    CANAL_COMANDOS_ID,
    CANAL_LEMBRETES_ID,
    CANAL_SHOP_ID,
    CARGO_NOIVO_ID,
    CARGO_NOIVA_ID,
    EMOJI_CAT_ID,
    EMOJI_DOG_ID,
    LIMITE_TEXTO_LEMBRETE,
    RECOMPENSA_PET_MIMOS,
)
from sistema_lembretes.db import (
    add_lembrete,
    concluir_lembrete,
    excluir_lembrete,
    listar_ativos,
    get_pet_state,
    marcar_pet_alimentado,
)
from sistema_lembretes.embeds import (
    criar_embed_lembretes,
    criar_embed_pet_comendo,
    criar_embed_pet_soneca,
    criar_embed_pet_ja_alimentou,
    criar_embed_pet_fora_horario,
    criar_embed_log_pet,
    prazo_label,
)


def cargo_autor(member: nextcord.Member) -> str:
    role_ids = {role.id for role in member.roles}

    if CARGO_NOIVO_ID in role_ids:
        return "noivo"

    if CARGO_NOIVA_ID in role_ids:
        return "noiva"

    return "outro"


def usuario_pode_usar(member: nextcord.Member) -> bool:
    return cargo_autor(member) in ("noivo", "noiva")


async def atualizar_painel(bot: nextcord.Client):
    from utils.panels import send_or_update_panel

    await send_or_update_panel(
        bot=bot,
        channel_id=CANAL_LEMBRETES_ID,
        panel_key="lembretes_panel",
        embed=criar_embed_lembretes(),
        view=LembretesView(),
    )


def janela_atual() -> str | None:
    agora = datetime.now()
    hora = agora.hour

    if 7 <= hora < 10:
        return f"{agora.strftime('%Y-%m-%d')}:manha"

    if 12 <= hora < 14:
        return f"{agora.strftime('%Y-%m-%d')}:almoco"

    if 17 <= hora < 19:
        return f"{agora.strftime('%Y-%m-%d')}:noite"

    return None


def janela_label(janela: str) -> str:
    if janela.endswith(":manha"):
        return "manhã, 7h–10h"

    if janela.endswith(":almoco"):
        return "almoço, 12h–14h"

    if janela.endswith(":noite"):
        return "noite, 17h–19h"

    return janela


class ShopLinkView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @nextcord.ui.button(
        label="Ir para a shop",
        style=nextcord.ButtonStyle.blurple,
        emoji="🛒",
    )
    async def ir_shop(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            f"🛒 Canal da shop: <#{CANAL_SHOP_ID}>",
            ephemeral=True,
        )


class LembreteModal(Modal):
    def __init__(self, destino: str, prazo: str):
        super().__init__(title="Colar um lembrete")

        self.destino = destino
        self.prazo = prazo

        self.texto = TextInput(
            label="Lembrete",
            placeholder="Ex: comprar vitamina",
            max_length=LIMITE_TEXTO_LEMBRETE,
            required=True,
            style=nextcord.TextInputStyle.paragraph,
        )

        self.add_item(self.texto)

    async def callback(self, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member):
            await interaction.response.send_message(
                "❌ Não consegui identificar seus cargos.",
                ephemeral=True,
            )
            return

        autor = cargo_autor(interaction.user)

        add_lembrete(
            destino=self.destino,
            autor=autor,
            autor_id=interaction.user.id,
            texto=str(self.texto.value).strip(),
            prazo=self.prazo,
            prazo_label=prazo_label(self.prazo),
        )

        await atualizar_painel(interaction.client)

        await interaction.response.send_message(
            "✅ Lembrete colado na geladeira.",
            ephemeral=True,
        )


class PrazoSelect(Select):
    def __init__(self, destino: str):
        self.destino = destino

        options = [
            nextcord.SelectOption(
                label="Hoje",
                value="hoje",
                description=prazo_label("hoje"),
            ),
            nextcord.SelectOption(
                label="Amanhã",
                value="amanha",
                description=prazo_label("amanha"),
            ),
            nextcord.SelectOption(
                label="Essa semana",
                value="semana",
                description=prazo_label("semana"),
            ),
            nextcord.SelectOption(
                label="Sem prazo",
                value="sem_prazo",
                description="Sem data marcada",
            ),
        ]

        super().__init__(
            placeholder="Escolha o prazo do lembrete",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        prazo = self.values[0]
        await interaction.response.send_modal(LembreteModal(self.destino, prazo))


class PrazoView(View):
    def __init__(self, destino: str):
        super().__init__(timeout=120)
        self.add_item(PrazoSelect(destino))


class DestinoLembreteSelect(Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(
                label="Para ela",
                value="noiva",
                description="Colar lembrete para a noiva",
            ),
            nextcord.SelectOption(
                label="Para ele",
                value="noivo",
                description="Colar lembrete para o noivo",
            ),
        ]

        super().__init__(
            placeholder="Para quem é o lembrete?",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        destino = self.values[0]

        await interaction.response.send_message(
            "Escolha o prazo:",
            view=PrazoView(destino),
            ephemeral=True,
        )


class DestinoLembreteView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(DestinoLembreteSelect())


class LembreteIdSelect(Select):
    def __init__(self, acao: str):
        self.acao = acao

        ativos = listar_ativos()
        options = []

        for item in ativos[:25]:
            texto = item.get("texto", "")[:70]
            destino = "ela" if item.get("destino") == "noiva" else "ele"

            options.append(
                nextcord.SelectOption(
                    label=f"#{item['id']} para {destino}",
                    value=str(item["id"]),
                    description=texto,
                )
            )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Nenhum lembrete ativo",
                    value="none",
                    description="Não há lembretes para selecionar.",
                )
            ]

        super().__init__(
            placeholder="Escolha o lembrete",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                "Não há lembretes ativos.",
                ephemeral=True,
            )
            return

        lembrete_id = int(self.values[0])

        if self.acao == "concluir":
            ok = concluir_lembrete(lembrete_id)
            msg = "✅ Tarefa concluída." if ok else "❌ Não encontrei esse lembrete."
        else:
            ok = excluir_lembrete(lembrete_id)
            msg = "🗑️ Lembrete excluído." if ok else "❌ Não encontrei esse lembrete."

        await atualizar_painel(interaction.client)

        await interaction.response.send_message(
            msg,
            ephemeral=True,
        )


class LembreteIdView(View):
    def __init__(self, acao: str):
        super().__init__(timeout=120)
        self.add_item(LembreteIdSelect(acao))


class PetSelect(Select):
    def __init__(self):
        emoji_cat = nextcord.PartialEmoji(name="cat", id=EMOJI_CAT_ID)
        emoji_dog = nextcord.PartialEmoji(name="dog", id=EMOJI_DOG_ID)

        options = [
            nextcord.SelectOption(
                label="Cachorrinhos",
                value="cachorros",
                description="Deixar comida para os cachorrinhos",
                emoji=emoji_dog,
            ),
            nextcord.SelectOption(
                label="Gatinhos",
                value="gatos",
                description="Deixar comida para os gatinhos",
                emoji=emoji_cat,
            ),
        ]

        super().__init__(
            placeholder="Escolha quem vai receber comida",
            min_values=1,
            max_values=2,
            options=options,
        )

    async def callback(self, interaction: nextcord.Interaction):
        janela = janela_atual()

        if janela is None:
            await interaction.response.send_message(
                embed=criar_embed_pet_fora_horario(),
                ephemeral=True,
            )
            return

        state = get_pet_state(interaction.user.id, janela)

        if state.get("usado"):
            await interaction.response.send_message(
                embed=criar_embed_pet_ja_alimentou(),
                ephemeral=True,
            )
            return

        pets = self.values

        marcar_pet_alimentado(interaction.user.id, janela, pets)
        add_mimos(interaction.user.id, RECOMPENSA_PET_MIMOS)

        await interaction.response.send_message(
            embed=criar_embed_pet_comendo(pets),
            view=ShopLinkView(),
            ephemeral=True,
        )

        canal = interaction.guild.get_channel(CANAL_COMANDOS_ID)

        if canal:
            await canal.send(
                embed=criar_embed_log_pet(
                    interaction.user,
                    pets,
                    janela_label(janela),
                )
            )


class PetView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(PetSelect())


class LembretesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(
        label="Post-it",
        style=nextcord.ButtonStyle.green,
        emoji="📝",
        custom_id="lembretes_postit",
    )
    async def postit(self, button: Button, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member) or not usuario_pode_usar(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Apenas o casal pode usar os lembretes.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Escolha para quem vai o lembrete:",
            view=DestinoLembreteView(),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Excluir lembrete",
        style=nextcord.ButtonStyle.red,
        emoji="🗑️",
        custom_id="lembretes_excluir",
    )
    async def excluir(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha qual lembrete deseja excluir:",
            view=LembreteIdView("excluir"),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Concluir tarefa",
        style=nextcord.ButtonStyle.blurple,
        emoji="✅",
        custom_id="lembretes_concluir",
    )
    async def concluir(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha qual tarefa foi concluída:",
            view=LembreteIdView("concluir"),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Pet",
        style=nextcord.ButtonStyle.gray,
        emoji="🐾",
        custom_id="lembretes_pet",
    )
    async def pet(self, button: Button, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member) or not usuario_pode_usar(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Apenas o casal pode alimentar os pets.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Escolha quem vai receber comida:",
            view=PetView(),
            ephemeral=True,
        )
