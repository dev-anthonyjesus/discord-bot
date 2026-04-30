import asyncio

import nextcord
from nextcord.ui import View, Button, Select

from sistema_fazenda.config import (
    CULTIVOS,
    CANAL_FARMHOUSE_ID,
    CATEGORIA_FARMHOUSE_ID,
)
from sistema_fazenda.db import get_state
from sistema_fazenda.embeds import (
    criar_embed_farmhouse,
    criar_embed_resultado,
    criar_embed_estoque,
    criar_embed_fornecedor,
    criar_embed_feira,
    criar_embed_lote,
    criar_embed_confirmar_venda_fornecedor,
    criar_embed_relatorio_estoque,
)
from sistema_fazenda.emojis import E, PE
from sistema_fazenda.services import (
    comprar_semente,
    plantar,
    colher_tudo_lote,
    calcular_venda_fornecedor,
    confirmar_venda_fornecedor,
)

from sistema_fazenda.funcionarios.embeds import criar_embed_funcionarios
from sistema_fazenda.funcionarios.views import FuncionariosView


from sistema_fazenda.animais.embeds import criar_embed_resumo_fazenda
from sistema_fazenda.animais.views import EntregaRacaoView, IrParaAnimaisView

from sistema_fazenda.animais.embeds import (
    criar_embed_resumo_fazenda,
    criar_embed_entrega_racao,
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


async def mensagem_temporaria(
    interaction: nextcord.Interaction,
    texto: str,
    segundos: int = 5,
):
    await interaction.response.send_message(texto, ephemeral=True)
    await asyncio.sleep(segundos)

    try:
        await interaction.delete_original_message()
    except Exception:
        pass


async def atualizar_painel_farmhouse(bot: nextcord.Client):
    from utils.panels import send_or_update_panel

    canal = bot.get_channel(CANAL_FARMHOUSE_ID)
    guild = canal.guild if canal else None

    await send_or_update_panel(
        bot=bot,
        channel_id=CANAL_FARMHOUSE_ID,
        panel_key="fazenda_farmhouse_panel",
        embed=criar_embed_farmhouse(guild),
        view=FarmhouseView(),
    )


async def atualizar_painel_lote(channel: nextcord.TextChannel, lote_id: int):
    try:
        async for msg in channel.history(limit=20):
            if msg.author.bot and msg.embeds:
                await msg.edit(embed=criar_embed_lote(lote_id), view=LoteView(lote_id))
                return

        await channel.send(embed=criar_embed_lote(lote_id), view=LoteView(lote_id))
    except Exception:
        pass


def cultivos_da_estacao():
    data = get_state()
    estacao = data["estacao"]

    return {
        key: cultivo
        for key, cultivo in CULTIVOS.items()
        if estacao in cultivo["estacoes"]
    }


async def criar_ou_pegar_canal_temporario(
    interaction: nextcord.Interaction,
    nome: str,
):
    guild = interaction.guild
    canal_farmhouse = guild.get_channel(CANAL_FARMHOUSE_ID)

    if canal_farmhouse is None:
        return None

    categoria = None

    if CATEGORIA_FARMHOUSE_ID:
        categoria = guild.get_channel(CATEGORIA_FARMHOUSE_ID)

    if categoria is None:
        categoria = canal_farmhouse.category

    nome_limpo = nome.lower().replace(" ", "-")

    for canal in guild.text_channels:
        if canal.name == nome_limpo:
            return canal

    overwrites = canal_farmhouse.overwrites if canal_farmhouse else {}

    canal = await guild.create_text_channel(
        name=nome_limpo,
        category=categoria,
        overwrites=overwrites,
    )

    return canal


class ComprarSementeSelect(Select):
    def __init__(self):
        options = []

        for key, cultivo in cultivos_da_estacao().items():
            preco_pacote = cultivo["preco_semente"] * 3

            options.append(
                nextcord.SelectOption(
                    label=f"Semente de {cultivo['nome']}",
                    value=key,
                    description=f"Pacote com 3 • {preco_pacote} moedas rurais",
                    emoji=PE(cultivo["semente_emoji"]),
                )
            )

        super().__init__(
            placeholder="Escolha um pacote de sementes",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        cultivo_id = self.values[0]
        ok, msg = comprar_semente(cultivo_id, 3)

        await atualizar_painel_farmhouse(interaction.client)

        await resposta_temporaria(
            interaction,
            criar_embed_resultado(
                f"{E('comprar')} Compra de sementes",
                msg,
                ok,
            ),
            5,
        )


class PlantarCultivoSelect(Select):
    def __init__(self, lote_id: int, canteiro_id: int):
        self.lote_id = lote_id
        self.canteiro_id = canteiro_id
        data = get_state()

        options = []

        for key, cultivo in cultivos_da_estacao().items():
            qtd = data.get("sementes", {}).get(key, 0)

            if qtd <= 0:
                continue

            options.append(
                nextcord.SelectOption(
                    label=cultivo["nome"],
                    value=key,
                    description=f"Você tem {qtd} semente(s)",
                    emoji=PE(cultivo["semente_emoji"]),
                )
            )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Sem sementes disponíveis",
                    value="none",
                    description="Compre sementes no fornecedor.",
                )
            ]

        super().__init__(
            placeholder="Escolha o cultivo para plantar",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == "none":
            await mensagem_temporaria(
                interaction,
                "🌱 Você não tem sementes disponíveis para plantar.",
                5,
            )
            return

        cultivo_id = self.values[0]
        ok, msg = plantar(self.lote_id, self.canteiro_id, cultivo_id, 3)

        await atualizar_painel_farmhouse(interaction.client)

        if isinstance(interaction.channel, nextcord.TextChannel):
            await atualizar_painel_lote(interaction.channel, self.lote_id)

        await resposta_temporaria(
            interaction,
            criar_embed_resultado(
                f"{E('plantar')} Plantio",
                msg,
                ok,
            ),
            5,
        )


class PlantarCultivoView(View):
    def __init__(self, lote_id: int, canteiro_id: int):
        super().__init__(timeout=180)
        self.add_item(PlantarCultivoSelect(lote_id, canteiro_id))


class CanteiroSelect(Select):
    def __init__(self, lote_id: int):
        self.lote_id = lote_id
        data = get_state()

        lote = None
        for item in data["lotes"]:
            if int(item["id"]) == int(lote_id):
                lote = item
                break

        options = []

        if lote and lote.get("desbloqueado"):
            for canteiro in lote["canteiros"]:
                options.append(
                    nextcord.SelectOption(
                        label=f"Canteiro #{canteiro['id']}",
                        value=str(canteiro["id"]),
                        description="Plantar neste canteiro",
                        emoji=PE("plantar"),
                    )
                )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Nenhum canteiro disponível",
                    value="none",
                    description="Este lote está vazio ou bloqueado.",
                )
            ]

        super().__init__(
            placeholder="Escolha o canteiro para plantar",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == "none":
            await mensagem_temporaria(
                interaction,
                "Nenhum canteiro disponível.",
                5,
            )
            return

        canteiro_id = int(self.values[0])

        await interaction.response.send_message(
            "Escolha o cultivo:",
            view=PlantarCultivoView(self.lote_id, canteiro_id),
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass


class CanteiroView(View):
    def __init__(self, lote_id: int):
        super().__init__(timeout=180)
        self.add_item(CanteiroSelect(lote_id))


class VenderFornecedorSelect(Select):
    def __init__(self):
        data = get_state()
        options = []

        for cultivo_id, quantidade in data.get("celeiro", {}).items():
            cultivo = CULTIVOS.get(cultivo_id)

            if not cultivo:
                continue

            bruto = cultivo["valor_venda"] * quantidade
            liquido = int(bruto * 0.90)

            options.append(
                nextcord.SelectOption(
                    label=f"Vender {cultivo['nome']}",
                    value=cultivo_id,
                    description=f"{quantidade} un. • retorno {liquido} após taxa",
                    emoji=PE(cultivo["emoji"]),
                )
            )

        if not options:
            options = [
                nextcord.SelectOption(
                    label="Celeiro vazio",
                    value="none",
                    description="Nada para vender.",
                )
            ]

        super().__init__(
            placeholder="Escolha o produto para vender tudo",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == "none":
            await mensagem_temporaria(
                interaction,
                "📦 O celeiro está vazio.",
                5,
            )
            return

        cultivo_id = self.values[0]
        ok, dados = calcular_venda_fornecedor(cultivo_id)

        if not ok:
            await mensagem_temporaria(interaction, str(dados), 5)
            return

        await interaction.response.send_message(
            embed=criar_embed_confirmar_venda_fornecedor(dados),
            view=ConfirmarVendaFornecedorView(cultivo_id),
            ephemeral=True,
        )


class ConfirmarVendaFornecedorView(View):
    def __init__(self, cultivo_id: str):
        super().__init__(timeout=120)
        self.cultivo_id = cultivo_id

    @nextcord.ui.button(
        label="Confirmar venda",
        style=nextcord.ButtonStyle.green,
        emoji=PE("ok"),
    )
    async def confirmar(self, button: Button, interaction: nextcord.Interaction):
        ok, msg = confirmar_venda_fornecedor(self.cultivo_id)

        await atualizar_painel_farmhouse(interaction.client)

        await resposta_temporaria(
            interaction,
            criar_embed_resultado(
                f"{E('vender')} Venda ao fornecedor",
                msg,
                ok,
            ),
            5,
        )

    @nextcord.ui.button(
        label="Cancelar",
        style=nextcord.ButtonStyle.red,
        emoji=PE("erro"),
    )
    async def cancelar(self, button: Button, interaction: nextcord.Interaction):
        await mensagem_temporaria(
            interaction,
            "Operação cancelada.",
            5,
        )


class FornecedorView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ComprarSementeSelect())
        self.add_item(VenderFornecedorSelect())

    @nextcord.ui.button(
        label="Voltar para fazenda",
        style=nextcord.ButtonStyle.green,
        emoji=PE("farmhouse"),
        custom_id="fornecedor_voltar_farmhouse",
    )
    async def voltar(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Voltando para a fazenda... este canal será fechado.",
            ephemeral=True,
        )

        await asyncio.sleep(1)

        try:
            await interaction.channel.delete()
        except Exception:
            pass


class LoteView(View):
    def __init__(self, lote_id: int):
        super().__init__(timeout=None)
        self.lote_id = lote_id

    @nextcord.ui.button(
        label="Plantar",
        style=nextcord.ButtonStyle.green,
        emoji=PE("plantar"),
        custom_id="lote_plantar",
    )
    async def plantar_btn(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha o canteiro:",
            view=CanteiroView(self.lote_id),
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass

    @nextcord.ui.button(
        label="Colher tudo",
        style=nextcord.ButtonStyle.blurple,
        emoji=PE("colher"),
        custom_id="lote_colher_tudo",
    )
    async def colher_tudo_btn(self, button: Button, interaction: nextcord.Interaction):
        ok, msg = colher_tudo_lote(self.lote_id)

        await atualizar_painel_farmhouse(interaction.client)

        if isinstance(interaction.channel, nextcord.TextChannel):
            await atualizar_painel_lote(interaction.channel, self.lote_id)

        await resposta_temporaria(
            interaction,
            criar_embed_resultado(
                f"{E('colher')} Colheita",
                msg,
                ok,
            ),
            5,
        )

    @nextcord.ui.button(
        label="Atualizar",
        style=nextcord.ButtonStyle.gray,
        emoji=PE("tempo"),
        custom_id="lote_atualizar",
    )
    async def atualizar_btn(self, button: Button, interaction: nextcord.Interaction):
        if isinstance(interaction.channel, nextcord.TextChannel):
            await atualizar_painel_lote(interaction.channel, self.lote_id)

        await mensagem_temporaria(
            interaction,
            "🔄 Lote atualizado.",
            5,
        )

    @nextcord.ui.button(
        label="Voltar para fazenda",
        style=nextcord.ButtonStyle.gray,
        emoji=PE("farmhouse"),
        custom_id="lote_voltar_farmhouse",
    )
    async def voltar(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Voltando para a fazenda... este canal será fechado.",
            ephemeral=True,
        )

        await asyncio.sleep(1)

        try:
            await interaction.channel.delete()
        except Exception:
            pass


class VoltarFazendaView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            nextcord.ui.Button(
                label="Abrir Farmhouse",
                style=nextcord.ButtonStyle.link,
                emoji=PE("farmhouse"),
                url="https://discord.com/channels/1491166103383179484/1499393422522581104",
            )
        )

    @nextcord.ui.button(
        label="Relatório",
        style=nextcord.ButtonStyle.blurple,
        emoji=PE("info"),
        custom_id="estoque_relatorio",
    )
    async def relatorio(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_relatorio_estoque(),
            ephemeral=True,
        )

        await asyncio.sleep(10)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass

    @nextcord.ui.button(
        label="Voltar para fazenda",
        style=nextcord.ButtonStyle.green,
        emoji=PE("farmhouse"),
        custom_id="fazenda_voltar_farmhouse",
    )
    async def voltar(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Voltando para a fazenda... este canal será fechado.",
            ephemeral=True,
        )

        await asyncio.sleep(1)

        try:
            await interaction.channel.delete()
        except Exception:
            pass


class IrParaSelect(Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(
                label="Lote 1",
                value="lote_1",
                description="Abrir canteiros do lote 1",
                emoji=PE("lote"),
            ),
            nextcord.SelectOption(
                label="Celeiro",
                value="celeiro",
                description="Ver estoque da fazenda",
                emoji=PE("celeiro"),
            ),
            nextcord.SelectOption(
                label="Fornecedor",
                value="fornecedor",
                description="Comprar sementes e negociar produtos",
                emoji=PE("loja"),
            ),
            nextcord.SelectOption(
                label="Feira",
                value="feira",
                description="Vender produtos com retorno após 1h",
                emoji=PE("vender"),
            ),
        ]

        super().__init__(
            placeholder="Escolha para onde ir",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: nextcord.Interaction):
        destino = self.values[0]

        if destino.startswith("lote_"):
            lote_id = int(destino.split("_")[1])
            nome = f"lote-{lote_id}"
            embed = criar_embed_lote(lote_id)
            view = LoteView(lote_id)
        elif destino == "celeiro":
            nome = "estoque"
            embed = criar_embed_estoque()
            view = VoltarFazendaView()
        elif destino == "fornecedor":
            nome = "fornecedor"
            embed = criar_embed_fornecedor()
            view = FornecedorView()
        else:
            nome = "feira"
            embed = criar_embed_feira()
            view = VoltarFazendaView()

        canal = await criar_ou_pegar_canal_temporario(interaction, nome)

        if canal is None:
            await mensagem_temporaria(
                interaction,
                "❌ Não consegui criar ou encontrar o canal.",
                5,
            )
            return

        try:
            async for msg in canal.history(limit=20):
                if msg.author.bot:
                    await msg.delete()
        except Exception:
            pass

        await canal.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"✅ Abri o canal: {canal.mention}",
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass


class IrParaView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(IrParaSelect())


class FarmhouseView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            nextcord.ui.Button(
                label="Prefeitura",
                style=nextcord.ButtonStyle.link,
                emoji=PE("prefeitura"),
                url="https://discord.com/channels/1491166103383179484/1499393713837969438",
            )
        )

        self.add_item(
            nextcord.ui.Button(
                label="Cangaço",
                style=nextcord.ButtonStyle.link,
                emoji=PE("cangaco"),
                url="https://discord.com/channels/1491166103383179484/1499393648997961738",
            )
        )
        
        
    @nextcord.ui.button(
        label="Fazenda",
        style=nextcord.ButtonStyle.green,
        emoji=PE("farmhouse"),
        custom_id="farmhouse_gestao",
    )
    async def fazenda_btn(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_resumo_fazenda(),
            view=FazendaGestaoView(interaction.user),
            ephemeral=True,
        )

        await asyncio.sleep(30)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass


    @nextcord.ui.button(
        label="Ir para",
        style=nextcord.ButtonStyle.gray,
        emoji=PE("fazenda"),
        custom_id="fazenda_ir_para",
    )
    async def ir_para_btn(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha o destino:",
            view=IrParaView(),
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass


class CangacoView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(
        label="Explorar",
        style=nextcord.ButtonStyle.green,
        emoji=PE("explorar"),
        custom_id="fazenda_explorar",
    )
    async def explorar(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "🧭 A exploração ainda vai ser configurada.",
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass

    @nextcord.ui.button(
        label="Missões",
        style=nextcord.ButtonStyle.blurple,
        emoji=PE("missao"),
        custom_id="fazenda_missoes",
    )
    async def missoes(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "📜 As missões ainda vão ser configuradas.",
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass


class PrefeituraView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(
        label="Informações",
        style=nextcord.ButtonStyle.blurple,
        emoji=PE("info"),
        custom_id="fazenda_info",
    )
    async def informacoes(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "📋 A prefeitura rural vai concentrar informações, rankings e comandos de teste.",
            ephemeral=True,
        )

        await asyncio.sleep(5)

        try:
            await interaction.delete_original_message()
        except Exception:
            pass


class FazendaGestaoView(View):
    def __init__(self, user: nextcord.Member):
        super().__init__(timeout=60)
        self.user = user

    @nextcord.ui.button(
        label="Contratar funcionário",
        style=nextcord.ButtonStyle.green,
        emoji="🤝",
    )
    async def contratar_funcionario(
        self, button: Button, interaction: nextcord.Interaction
    ):
        await interaction.response.send_message(
            embed=criar_embed_funcionarios(),
            view=FuncionariosView(),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Pedir entrega de ração",
        style=nextcord.ButtonStyle.blurple,
        emoji="🚚",
    )
    async def pedir_racao(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            embed=criar_embed_entrega_racao(),
            view=EntregaRacaoView(),
            ephemeral=True,
        )

    @nextcord.ui.button(
        label="Ir para animais",
        style=nextcord.ButtonStyle.gray,
        emoji="🐾",
    )
    async def ir_animais(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(
            "Escolha o espaço dos animais:",
            view=IrParaAnimaisView(),
            ephemeral=True,
        )
