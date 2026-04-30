import nextcord

from sistema_fazenda.animais.config import ANIMAIS, RACAO_MAXIMA, CUSTO_ENTREGA_RACAO
from sistema_fazenda.animais.services import (
    calcular_status_local,
    formatar_tempo,
    resumo_animais_para_embed,
    resumo_racao_para_embed,
    total_animais,
)
from sistema_fazenda.db import get_state
from sistema_fazenda.emojis import E


def criar_embed_resumo_fazenda() -> nextcord.Embed:
    data = get_state()
    stats = data.get("estatisticas", {})
    animais_stats = data.get("animais", {}).get("estatisticas", {})

    embed = nextcord.Embed(
        title=f"{E('farmhouse')} Gestão da Fazenda",
        description=(
            "Resumo administrativo da fazenda.\n"
            "Aqui ficam os números gerais, funcionários, animais e pedidos importantes."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.add_field(
        name="Faturamento",
        value=(
            f"Moedas atuais: `{data.get('moedas', 0)}`\n"
            f"Moedas ganhas: `{stats.get('moedas_ganhas', 0)}`\n"
            f"Produtos vendidos: `{stats.get('vendas', 0)}`"
        ),
        inline=False,
    )

    embed.add_field(
        name="Animais",
        value=(
            f"Total de animais: `{total_animais(data)}`\n"
            f"{resumo_animais_para_embed(data)}\n"
            f"{resumo_racao_para_embed(data)}"
        ),
        inline=False,
    )

    embed.add_field(
        name="Produção animal",
        value=(
            f"Produtos coletados: `{animais_stats.get('produtos_coletados', 0)}`\n"
            f"Nascimentos: `{animais_stats.get('nascimentos', 0)}`\n"
            f"Animais comprados: `{animais_stats.get('animais_comprados', 0)}`"
        ),
        inline=False,
    )

    embed.add_field(
        name="Meu cavalo",
        value="_em breve: nome, vínculo, energia, corrida e cuidados_",
        inline=False,
    )

    embed.set_footer(text="Farmhouse • gestão")
    return embed


def criar_embed_local_animais(local: str) -> nextcord.Embed:
    status = calcular_status_local(local)

    nomes = {
        "galinheiro": "Galinheiro",
        "celeiro": "Celeiro dos Animais",
        "estabulo": "Estábulo",
    }

    embed = nextcord.Embed(
        title=f"{E('farmhouse')} {nomes.get(local, local.title())}",
        description=(
            f"Ração disponível: `{status['racao']}/{RACAO_MAXIMA}`\n"
            "Esta mensagem some em `60s`."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    if not status["animais"]:
        embed.add_field(
            name="Sem animais",
            value="_nenhum animal neste local_",
            inline=False,
        )

    for item in status["animais"]:
        if item["quantidade"] <= 0:
            valor = "_nenhum comprado ainda_"
        elif item["produto_nome"] is None:
            valor = (
                f"Quantidade: `{item['quantidade']}`\n"
                "Produção: _não produz item, usado para vínculo/eventos_"
            )
        else:
            if item["prontos"] > 0:
                pronto_txt = f"`{item['prontos']}` pronto(s) para coletar"
            elif item["proximo"] is not None:
                pronto_txt = f"próximo em `{formatar_tempo(item['proximo'])}`"
            else:
                pronto_txt = "_aguardando produção_"

            valor = (
                f"Quantidade: `{item['quantidade']}`\n"
                f"Produto: {item['produto_emoji']} {item['produto_nome']}\n"
                f"Status: {pronto_txt}"
            )

        embed.add_field(
            name=f"{item['emoji']} {item['nome']}",
            value=valor,
            inline=False,
        )

    embed.set_footer(text=f"Farmhouse • {nomes.get(local, local)}")
    return embed


def criar_embed_entrega_racao() -> nextcord.Embed:
    embed = nextcord.Embed(
        title="🚚 Entrega de ração",
        description=(
            f"Peça uma entrega para repor a ração dos animais.\n\n"
            f"Custo: `{CUSTO_ENTREGA_RACAO} moedas rurais`\n"
            f"Reposição: `{RACAO_MAXIMA}/100`"
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    embed.set_footer(text="Farmhouse • ração")
    return embed
