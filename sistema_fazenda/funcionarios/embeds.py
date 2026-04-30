import nextcord

from sistema_fazenda.db import get_state
from sistema_fazenda.emojis import E
from sistema_fazenda.funcionarios.config import FUNCIONARIOS, LIMITE_FUNCIONARIOS_ATIVOS
from sistema_fazenda.funcionarios.services import garantir_bloco_funcionarios
from sistema_fazenda.funcionarios.services import resumo_funcionarios_para_embed

def criar_embed_funcionarios() -> nextcord.Embed:
    data = get_state()
    data = garantir_bloco_funcionarios(data)

    ativos = data["funcionarios"]["ativos"]
    limite = data["funcionarios"].get("limite", LIMITE_FUNCIONARIOS_ATIVOS)

    embed = nextcord.Embed(
        title=f"{E('farmhouse')} Funcionários da Fazenda",
        description=(
            "Funcionários ajudam a fazenda com buffs, produção e manutenção.\n"
            "Os contratos duram até o fim da temporada."
        ),
        color=0xBAFF7C,
        timestamp=nextcord.utils.utcnow(),
    )

    if ativos:
        linhas = []

        for funcionario_id in ativos:
            funcionario = FUNCIONARIOS.get(funcionario_id)

            if not funcionario:
                continue

            linhas.append(
                f"{funcionario['emoji']} **{funcionario['nome']}** — "
                f"`{funcionario['custo_temporada']} moedas/temporada`"
            )

        contratados = "\n".join(linhas)
    else:
        contratados = "_nenhum funcionário contratado_"

    embed.add_field(
        name=f"Contratados `{len(ativos)}/{limite}`",
        value=contratados,
        inline=False,
    )

    disponiveis = []

    for funcionario_id, funcionario in FUNCIONARIOS.items():
        status = "contratado" if funcionario_id in ativos else "disponível"

        buffs = "\n".join(f"• {buff}" for buff in funcionario["buffs"])

        disponiveis.append(
            f"{funcionario['emoji']} **{funcionario['nome']}** — `{status}`\n"
            f"Contrato: `{funcionario['contrato']} moedas`\n"
            f"Custo por temporada: `{funcionario['custo_temporada']} moedas`\n"
            f"{buffs}"
        )

    embed.add_field(
        name="Funcionários disponíveis",
        value="\n\n".join(disponiveis[:4]),
        inline=False,
    )

    embed.add_field(
        name="Mais funcionários",
        value="\n\n".join(disponiveis[4:]),
        inline=False,
    )

    embed.set_footer(text="Farmhouse • funcionários")
    return embed
