import nextcord


from sistema_fazenda.funcionarios.services import resumo_funcionarios_para_embed
from sistema_fazenda.config import CULTIVOS, ESTACOES, NOME_FAZENDA, SLOTS_POR_CANTEIRO
from sistema_fazenda.db import get_state
from sistema_fazenda.emojis import E
from sistema_fazenda.services import (
    slot_segundos_restantes,
    formatar_tempo,
    slot_pronto,
)

from sistema_fazenda.funcionarios.services import resumo_funcionarios_para_embed

CARGO_BRACO_DIREITO_ID = 1499469992264204298
CARGO_SECRETARIA_ID = 1499470168747806750


def listar_membros_do_cargo(guild: nextcord.Guild | None, role_id: int) -> str:
    if guild is None:
        return "_não consegui ler o servidor_"

    role = guild.get_role(role_id)

    if role is None:
        return "_cargo não encontrado_"

    if not role.members:
        return "_ninguém com esse cargo ainda_"

    return ", ".join(member.mention for member in role.members)


def ansi(texto: str) -> str:
    return f"```ansi\n{texto}\n```"


def c_verde(texto: str) -> str:
    return f"\u001b[32m{texto}\u001b[0m"


def c_amarelo(texto: str) -> str:
    return f"\u001b[33m{texto}\u001b[0m"


def c_cinza(texto: str) -> str:
    return f"\u001b[90m{texto}\u001b[0m"


def nome_estacao(estacao_id: str) -> str:
    estacao = ESTACOES.get(estacao_id, {})
    return f"{E(estacao.get('emoji', 'evento'))} {estacao.get('nome', estacao_id)}"


def resumo_lote(lote: dict) -> str:
    if not lote.get("desbloqueado"):
        return f"{E('bloqueado')} bloqueado"

    ocupados = 0
    prontos = 0

    for canteiro in lote["canteiros"]:
        for slot in canteiro["slots"]:
            if slot.get("cultivo"):
                ocupados += 1
                if slot_pronto(slot):
                    prontos += 1

    total = len(lote["canteiros"]) * SLOTS_POR_CANTEIRO

    if ocupados == 0:
        return f"`0/{total}` ocupado"

    if prontos > 0:
        return f"`{ocupados}/{total}` ocupado • `{prontos}` pronto(s)"

    return f"`{ocupados}/{total}` ocupado"


def formatar_slot_lote(slot: dict, numero: int) -> str:
    cultivo_id = slot.get("cultivo")

    if not cultivo_id:
        return c_cinza(f"{numero}. vazio")

    cultivo = CULTIVOS[cultivo_id]
    valor = cultivo["valor_venda"] * cultivo["rendimento"]

    if slot_pronto(slot):
        tempo = c_verde("pronto")
    else:
        tempo = c_amarelo(formatar_tempo(slot_segundos_restantes(slot)))

    return f"{numero}. {cultivo['nome']} • {tempo} • {E('moeda')} {valor}"


def formatar_canteiro_detalhado(canteiro: dict) -> str:
    linhas = [
        f"Canteiro #{canteiro['id']}",
        "────────────",
    ]

    for i, slot in enumerate(canteiro["slots"]):
        linhas.append(formatar_slot_lote(slot, i + 1))

    return ansi("\n".join(linhas))


def formatar_lista_itens(itens: dict) -> str:
    if not itens:
        return "_vazio_"

    linhas = []

    for cultivo_id, quantidade in itens.items():
        cultivo = CULTIVOS.get(cultivo_id)

        if not cultivo:
            continue

        linhas.append(f"{cultivo['nome']}: `{quantidade}`")

    return "\n".join(linhas) if linhas else "_vazio_"


def criar_embed_farmhouse(guild: nextcord.Guild | None = None) -> nextcord.Embed:
    data = get_state()

    embed = nextcord.Embed(
        title=f"{E('farmhouse')} {NOME_FAZENDA}",
        description=(
            "_Painel principal da fazenda do casal._\n\n"
            f"Estação atual: **{nome_estacao(data['estacao'])}**\n"
            f"Dia da fazenda: `{data['dia']}/7`\n\n"
            f"```ansi\n{E('moeda')} Moedas rurais: \u001b[33m{data['moedas']}\u001b[0m\n```"
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    lotes_txt = []

    for lote in data["lotes"]:
        lotes_txt.append(f"**Lote {lote['id']}** — {resumo_lote(lote)}")

    embed.add_field(
        name=f"{E('lote')} Lotes",
        value="\n".join(lotes_txt),
        inline=False,
    )

    embed.add_field(
        name="Sementes",
        value=formatar_lista_itens(data.get("sementes", {})),
        inline=True,
    )

    embed.add_field(
        name=f"{E('celeiro')} Celeiro",
        value=formatar_lista_itens(data.get("celeiro", {})),
        inline=True,
        
    )

    embed.add_field(
        name="Funcionários da Fazenda",
        value=resumo_funcionarios_para_embed(data),
        inline=True,
    )

    embed.add_field(
        name=f"{E('info')} Aliados da Fazenda",
        value=(
            f"<@&{CARGO_BRACO_DIREITO_ID}>:\n"
            f"{listar_membros_do_cargo(guild, CARGO_BRACO_DIREITO_ID)}\n\n"
            f"<@&{CARGO_SECRETARIA_ID}>:\n"
            f"{listar_membros_do_cargo(guild, CARGO_SECRETARIA_ID)}"
        ),
        inline=False,
    )

    embed.set_footer(text="Farmhouse • plantação v1")
    return embed


def criar_embed_lote(lote_id: int) -> nextcord.Embed:
    data = get_state()

    lote = None
    for item in data["lotes"]:
        if int(item["id"]) == int(lote_id):
            lote = item
            break

    embed = nextcord.Embed(
        title=f"{E('lote')} Lote {lote_id}",
        description=(
            "Cada canteiro tem `3 espaços` para sementes.\n"
            "Use **Colher tudo** para coletar tudo que estiver pronto."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    if lote is None:
        embed.description = "Esse lote não existe."
        embed.color = 0xE74C3C
        return embed

    if not lote.get("desbloqueado"):
        embed.description = "🔒 Este lote ainda está bloqueado."
        return embed

    for canteiro in lote["canteiros"]:
        embed.add_field(
            name=f"Canteiro #{canteiro['id']}",
            value=formatar_canteiro_detalhado(canteiro),
            inline=False,
        )

    embed.set_footer(text=f"Farmhouse • lote {lote_id}")
    return embed


def criar_embed_cangaco() -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"{E('cangaco')} Cangaço",
        description=(
            "_Área de aventura, exploração e eventos da fazenda._\n\n"
            "Aqui vão entrar missões, eventos aleatórios, clima e exploração."
        ),
        color=0xFFB347,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Farmhouse • cangaço e eventos")
    return embed


def criar_embed_prefeitura() -> nextcord.Embed:
    data = get_state()
    stats = data.get("estatisticas", {})

    embed = nextcord.Embed(
        title=f"{E('prefeitura')} Prefeitura Rural",
        description="_Central administrativa da fazenda._",
        color=0x87CEFA,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name=f"{E('info')} Estatísticas",
        value=(
            f"Plantios: `{stats.get('plantios', 0)}`\n"
            f"Colheitas: `{stats.get('colheitas', 0)}`\n"
            f"Vendas: `{stats.get('vendas', 0)}`\n"
            f"Moedas ganhas: `{stats.get('moedas_ganhas', 0)}`\n"
            f"Moedas gastas: `{stats.get('moedas_gastas', 0)}`"
        ),
        inline=False,
    )

    embed.set_footer(text="Farmhouse • prefeitura rural")
    return embed


def criar_embed_loja_sementes() -> nextcord.Embed:
    data = get_state()
    estacao = data["estacao"]

    embed = nextcord.Embed(
        title=f"{E('loja')} Fornecedor de sementes",
        description=(
            f"Estação atual: **{nome_estacao(estacao)}**\n"
            "As sementes são vendidas em pacotes de `3 unidades`."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    for cultivo_id, cultivo in CULTIVOS.items():
        if estacao not in cultivo["estacoes"]:
            continue

        pacote = 3
        preco_pacote = cultivo["preco_semente"] * pacote
        valor_total = cultivo["valor_venda"] * cultivo["rendimento"]

        embed.add_field(
            name=f"Semente de {cultivo['nome']}",
            value=(
                f"Pacote: `3 sementes`\n"
                f"Preço: `{E('moeda')} {preco_pacote} moedas`\n"
                f"Tempo: `{formatar_tempo(cultivo['tempo_segundos'])}`\n"
                f"Valor por espaço: `{E('moeda')} {valor_total}`"
            ),
            inline=False,
        )

    embed.set_footer(text="Farmhouse • fornecedor")
    return embed


def criar_embed_resultado(
    titulo: str,
    mensagem: str,
    sucesso: bool = True,
) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=titulo,
        description=mensagem,
        color=0x2ECC71 if sucesso else 0xE74C3C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Farmhouse")
    return embed


def criar_embed_estoque() -> nextcord.Embed:
    data = get_state()

    embed = nextcord.Embed(
        title=f"{E('celeiro')} Estoque da fazenda",
        description="Aqui ficam as sementes e produtos colhidos.",
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Sementes",
        value=formatar_lista_itens(data.get("sementes", {})),
        inline=False,
    )

    embed.add_field(
        name=f"{E('celeiro')} Produtos in natura",
        value=formatar_lista_itens(data.get("celeiro", {})),
        inline=False,
    )

    embed.add_field(
        name="Produtos processados",
        value=formatar_lista_itens(data.get("processados", {})),
        inline=False,
    )

    embed.add_field(
        name="Animais",
        value="_em breve_",
        inline=False,
    )

    embed.set_footer(text="Farmhouse • estoque")
    return embed


def criar_embed_fornecedor() -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"{E('loja')} Fornecedor Rural",
        description=(
            "O fornecedor vende sementes e compra produtos na hora.\n\n"
            "Ele fica com `10%` do valor como taxa de revenda. "
            "O dinheiro cai imediatamente."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Farmhouse • fornecedor")
    return embed


def criar_embed_feira() -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"{E('vender')} Feira Rural",
        description=(
            "Na feira, seus produtos podem render mais.\n\n"
            "A venda fica em andamento e o dinheiro retorna depois de `1h`."
        ),
        color=0xFFB347,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Farmhouse • feira")
    return embed


def criar_embed_confirmar_venda_fornecedor(dados: dict) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"{E('vender')} Confirmar venda ao fornecedor",
        description=(
            f"Produto: **{dados['nome']}**\n"
            f"Quantidade: `{dados['quantidade']}`\n\n"
            f"Valor bruto: `{E('moeda')} {dados['bruto']}`\n"
            f"Taxa do fornecedor: `{E('moeda')} {dados['taxa']}`\n"
            f"Retorno para a fazenda: `{E('moeda')} {dados['liquido']}`"
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Farmhouse • confirmação de venda")
    return embed


def criar_embed_relatorio_estoque() -> nextcord.Embed:
    data = get_state()

    embed = nextcord.Embed(
        title=f"{E('info')} Relatório do estoque",
        description=(
            "Valores estimados dos produtos guardados na fazenda.\n"
            "O fornecedor paga na hora, mas fica com `10%`.\n"
            "A feira retorna depois de `1h` e pode render mais."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    tem_algo = False

    for cultivo_id, cultivo in CULTIVOS.items():
        sementes = data.get("sementes", {}).get(cultivo_id, 0)
        quantidade = data.get("celeiro", {}).get(cultivo_id, 0)

        if sementes <= 0 and quantidade <= 0:
            continue

        tem_algo = True

        valor_bruto = cultivo["valor_venda"] * quantidade
        taxa_fornecedor = int(valor_bruto * 0.10)
        valor_fornecedor = valor_bruto - taxa_fornecedor
        valor_feira = int(valor_bruto * 1.20)

        embed.add_field(
            name=f"{cultivo['nome']}",
            value=(
                f"Sementes no estoque: `{sementes}`\n"
                f"Preço da semente: `{E('moeda')} {cultivo['preco_semente']}`\n"
                f"Produto in natura: `{quantidade}`\n"
                f"Valor bruto: `{E('moeda')} {valor_bruto}`\n"
                f"Fornecedor: `{E('moeda')} {valor_fornecedor}` "
                f"após taxa `{E('moeda')} {taxa_fornecedor}`\n"
                f"Feira: `{E('moeda')} {valor_feira}` após `1h`"
            ),
            inline=False,
        )

    if not tem_algo:
        embed.add_field(
            name="Estoque vazio",
            value="Ainda não há sementes ou produtos para analisar.",
            inline=False,
        )

    embed.add_field(
        name="Produtos processados",
        value=(
            "Ainda não há produtos processados.\n"
            "Futuramente entram itens como queijo, geleia, chocolate e derivados."
        ),
        inline=False,
    )

    embed.add_field(
        name="Animais",
        value=(
            "Ainda sem animais registrados.\n"
            "Depois este relatório também mostrará leite, ovos, carne, lã e produção animal."
        ),
        inline=False,
    )

    embed.set_footer(text="Farmhouse • relatório do estoque")
    return embed
