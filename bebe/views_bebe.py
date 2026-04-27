import nextcord
import os
from nextcord.ui import View, button, Select, Modal, TextInput

SEU_ID = 1431111401522462741
ID_DA_NOIVA = 715329753032163379

TRACOS = [
    ("calminho", "Piora mais devagar."),
    ("sensivel", "Humor cai mais fácil."),
    ("intenso", "Oscila mais rápido."),
    ("risonho", "Melhora mais com atenção."),
    ("grudento", "Precisa de mais atenção."),
    ("agitado", "Dorme pior."),
]

GENEROS = [
    ("Neutro", "neutro"),
    ("Menino", "menino"),
    ("Menina", "menina"),
]

ADICIONAIS = [
    ("Babá", "baba", "Ajuda forte"),
    ("Brinquedo", "brinquedo", "Atenção/humor"),
    ("Chupeta", "chupeta", "Ajuda rápida"),
    ("Remédio", "remedio", "Evento ruim"),
    ("Comida especial", "comida_especial", "Fome/humor"),
    ("Passeio", "passeio", "Humor"),
    ("Música de ninar", "musica_ninar", "Sono"),
]


def usuario_eh_noivo(user_id: int) -> bool:
    return user_id == SEU_ID


def usuario_eh_noiva(user_id: int) -> bool:
    return user_id == ID_DA_NOIVA


def usuario_autorizado(user_id: int) -> bool:
    return user_id in [SEU_ID, ID_DA_NOIVA]


class NomeBebeModal(Modal):
    def __init__(self, sistema):
        super().__init__("Editar nome do bebê")
        self.sistema = sistema
        self.nome = TextInput(
            label="Nome do bebê",
            placeholder="Digite o nome",
            min_length=1,
            max_length=25,
            required=True,
            default_value=sistema.data.get("nome", "Bebê"),
        )
        self.add_item(self.nome)

    async def callback(self, interaction: nextcord.Interaction):
        self.sistema.data["nome"] = str(self.nome.value).strip()
        self.sistema.save()
        await interaction.response.send_message("✅ Nome atualizado.", ephemeral=True)
        if self.sistema.data.get("setup"):
            await self.sistema.atualizar_painel_principal()
        else:
            await self.sistema.atualizar_setup()


class MemoriaTextoModal(Modal):
    def __init__(self, sistema, foto_nome: str):
        super().__init__("Criar momento do bebê")
        self.sistema = sistema
        self.foto_nome = foto_nome

        self.titulo = TextInput(
            label="Título",
            placeholder="Ex.: 📸 Momento do bebê",
            required=False,
            max_length=40,
            default_value="📸 Momento do bebê",
        )

        self.texto = TextInput(
            label="Texto",
            placeholder="Escreva uma legenda curtinha",
            required=False,
            max_length=180,
            default_value="Mais um momento especial do bebê.",
        )

        self.add_item(self.titulo)
        self.add_item(self.texto)

    async def callback(self, interaction: nextcord.Interaction):
        titulo = str(self.titulo.value).strip() or "📸 Momento do bebê"
        texto = str(self.texto.value).strip() or "Mais um momento especial do bebê."

        await self.sistema.enviar_memoria_manual(
            interaction=interaction,
            foto_nome=self.foto_nome,
            titulo=titulo,
            descricao=texto,
        )


class MemoriaFotoSelect(Select):
    def __init__(self, sistema):
        self.sistema = sistema
        fotos = sistema.listar_memorias()

        options = []
        for nome in fotos[:25]:
            label = os.path.splitext(nome)[0][:100]
            options.append(
                nextcord.SelectOption(
                    label=label, value=nome, description="Usar esta foto"
                )
            )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Nenhuma foto encontrada",
                    value="__vazio__",
                    description="Adicione imagens na pasta memorias_bebe",
                )
            ]

        super().__init__(
            placeholder="Escolha uma foto",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="baby_memoria_foto",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return

        if self.values[0] == "__vazio__":
            await interaction.response.send_message(
                "❌ Não encontrei fotos em `memorias_bebe`.", ephemeral=True
            )
            return

        await interaction.response.send_modal(
            MemoriaTextoModal(self.sistema, self.values[0])
        )

class MomentosBebeView(View):
    def __init__(self, sistema):
        super().__init__(timeout=180)
        self.add_item(MemoriaFotoSelect(sistema))

class GeneroSelect(Select):
    def __init__(self, sistema):
        self.sistema = sistema
        options = [
            nextcord.SelectOption(label=label, value=value) for label, value in GENEROS
        ]
        super().__init__(
            placeholder="Escolher gênero",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="baby_genero_select",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return
        self.sistema.data["genero"] = self.values[0].title()
        self.sistema.save()
        await interaction.response.send_message("✅ Gênero atualizado.", ephemeral=True)
        if self.sistema.data.get("setup"):
            await self.sistema.atualizar_painel_principal()
        else:
            await self.sistema.atualizar_setup()


class TracoSelect(Select):
    def __init__(self, sistema, dono: str):
        self.sistema = sistema
        self.dono = dono
        options = [
            nextcord.SelectOption(label=nome.title(), value=nome, description=desc)
            for nome, desc in TRACOS
        ]
        super().__init__(
            placeholder=f"Escolha o traço do {dono}",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"baby_traco_{dono}",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.dono == "noivo" and not usuario_eh_noivo(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o noivo pode escolher esse traço.", ephemeral=True
            )
            return

        if self.dono == "noiva" and not usuario_eh_noiva(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só a noiva pode escolher esse traço.", ephemeral=True
            )
            return

        escolhido = self.values[0]
        outro = (
            self.sistema.data.get("traco_noiva")
            if self.dono == "noivo"
            else self.sistema.data.get("traco_noivo")
        )

        if outro == escolhido:
            await interaction.response.send_message(
                "❌ Esse traço já foi escolhido pelo outro.", ephemeral=True
            )
            return

        if self.dono == "noivo":
            self.sistema.data["traco_noivo"] = escolhido
        else:
            self.sistema.data["traco_noiva"] = escolhido

        self.sistema.save()
        await interaction.response.send_message(
            f"✅ Traço **{escolhido.title()}** escolhido.", ephemeral=True
        )
        await self.sistema.atualizar_setup()

        if self.sistema.setup_pronto():
            await self.sistema.finalizar_setup()


class SetupBebeView(View):
    def __init__(self, sistema):
        super().__init__(timeout=None)
        self.sistema = sistema
        self.add_item(GeneroSelect(sistema))
        self.add_item(TracoSelect(sistema, "noivo"))
        self.add_item(TracoSelect(sistema, "noiva"))

    @button(
        label="Editar Nome",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_setup_nome",
    )
    async def editar_nome(self, button, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return
        await interaction.response.send_modal(NomeBebeModal(self.sistema))


class PainelBebeView(View):
    def __init__(self, sistema):
        super().__init__(timeout=None)
        self.sistema = sistema

    def autorizado(self, interaction):
        return usuario_autorizado(interaction.user.id)

    @button(
        label="Mamadeira",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_mamadeira",
    )
    async def mamadeira(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode cuidar do bebê.", ephemeral=True
            )
            return
        await self.sistema.cuidar(interaction, "mamadeira")

    @button(
        label="Fralda",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_fralda",
    )
    async def fralda(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode cuidar do bebê.", ephemeral=True
            )
            return
        await self.sistema.cuidar(interaction, "fralda")

    @button(
        label="Dormir",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_dormir",
    )
    async def dormir(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode cuidar do bebê.", ephemeral=True
            )
            return
        await self.sistema.cuidar(interaction, "dormir")

    @button(
        label="Atenção",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_atencao",
    )
    async def atencao(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode cuidar do bebê.", ephemeral=True
            )
            return
        await self.sistema.cuidar(interaction, "atencao")

    @button(
        label="Banho",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_banho",
    )
    async def banho(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode cuidar do bebê.", ephemeral=True
            )
            return
        await self.sistema.cuidar(interaction, "banho")

    @button(
        label="Adicionais",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_adicionais",
    )
    async def adicionais(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return
        await self.sistema.abrir_painel_adicionais(interaction)

    @button(
        label="Momentos",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_care_momentos",
    )
    async def momentos(self, button, interaction: nextcord.Interaction):
        if not self.autorizado(interaction):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return
        await self.sistema.abrir_painel_momentos(interaction)


class AdicionalSelect(Select):
    def __init__(self, sistema):
        self.sistema = sistema
        options = [
            nextcord.SelectOption(label=label, value=value, description=desc)
            for label, value, desc in ADICIONAIS
        ]
        super().__init__(
            placeholder="Escolha um adicional",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="baby_addon_select",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return
        await self.sistema.usar_adicional(interaction, self.values[0])


class AdicionaisBebeView(View):
    def __init__(self, sistema):
        super().__init__(timeout=180)
        self.add_item(AdicionalSelect(sistema))


class AdminActionSelect(Select):
    def __init__(self, sistema):
        self.sistema = sistema
        options = [
            nextcord.SelectOption(label="Trocar gênero", value="trocar_genero"),
            nextcord.SelectOption(label="Trocar traço do noivo", value="traco_noivo"),
            nextcord.SelectOption(label="Trocar traço da noiva", value="traco_noiva"),
            nextcord.SelectOption(label="Resetar setup", value="reset_setup"),
            nextcord.SelectOption(label="Resetar status do bebê", value="reset_status"),
            nextcord.SelectOption(label="Atualizar painel", value="atualizar_painel"),
        ]
        super().__init__(
            placeholder="Escolha uma ação",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="baby_admin_action",
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return

        acao = self.values[0]

        if acao == "trocar_genero":
            view = View(timeout=120)
            view.add_item(GeneroSelect(self.sistema))
            await interaction.response.send_message(
                "Escolha o novo gênero:", view=view, ephemeral=True
            )
            return

        if acao == "traco_noivo":
            view = View(timeout=120)
            view.add_item(TracoSelect(self.sistema, "noivo"))
            await interaction.response.send_message(
                "Escolha o novo traço do noivo:", view=view, ephemeral=True
            )
            return

        if acao == "traco_noiva":
            view = View(timeout=120)
            view.add_item(TracoSelect(self.sistema, "noiva"))
            await interaction.response.send_message(
                "Escolha o novo traço da noiva:", view=view, ephemeral=True
            )
            return

        if acao == "reset_setup":
            await self.sistema.resetar_setup(interaction)
            return

        if acao == "reset_status":
            await self.sistema.resetar_status(interaction)
            return

        if acao == "atualizar_painel":
            await self.sistema.atualizar_painel_principal()
            await interaction.response.send_message(
                "✅ Painel atualizado.", ephemeral=True
            )
            return


class BabyAdminView(View):
    def __init__(self, sistema):
        super().__init__(timeout=180)
        self.sistema = sistema
        self.add_item(AdminActionSelect(sistema))

    @button(
        label="Editar Nome",
        style=nextcord.ButtonStyle.secondary,
        custom_id="baby_admin_nome",
    )
    async def editar_nome(self, button, interaction: nextcord.Interaction):
        if not usuario_autorizado(interaction.user.id):
            await interaction.response.send_message(
                "❌ Só o casal pode usar isso.", ephemeral=True
            )
            return
        await interaction.response.send_modal(NomeBebeModal(self.sistema))


def registrar_views_bebe(bot, sistema):
    """Registra todas as views persistentes do bebê no bot."""
    if sistema is None:
        raise ValueError("sistema não pode ser None em registrar_views_bebe()")
    
    # Registrar views com timeout=None (persistentes)
    bot.add_view(SetupBebeView(sistema))
    bot.add_view(PainelBebeView(sistema))
    bot.add_view(BabyAdminView(sistema))
    bot.add_view(AdicionaisBebeView(sistema))
    bot.add_view(MomentosBebeView(sistema))
