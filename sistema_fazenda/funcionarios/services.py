import nextcord

from sistema_fazenda.db import get_state, salvar_state
from sistema_fazenda.funcionarios.config import (
    FUNCIONARIOS,
    LIMITE_FUNCIONARIOS_ATIVOS,
    CARGO_NOIVO_ID,
)


def garantir_bloco_funcionarios(data: dict) -> dict:
    data.setdefault(
        "funcionarios",
        {
            "ativos": [],
            "historico": [],
            "limite": LIMITE_FUNCIONARIOS_ATIVOS,
        },
    )

    data["funcionarios"].setdefault("ativos", [])
    data["funcionarios"].setdefault("historico", [])
    data["funcionarios"].setdefault("limite", LIMITE_FUNCIONARIOS_ATIVOS)

    return data


def usuario_e_noivo(member: nextcord.Member) -> bool:
    return any(role.id == CARGO_NOIVO_ID for role in member.roles)


def get_funcionarios_ativos() -> list[str]:
    data = get_state()
    data = garantir_bloco_funcionarios(data)
    salvar_state(data)

    return data["funcionarios"]["ativos"]


def contratar_funcionario(
    member: nextcord.Member, funcionario_id: str
) -> tuple[bool, str]:
    if not usuario_e_noivo(member):
        return False, "❌ Apenas o noivo pode contratar funcionários diretamente."

    data = get_state()
    data = garantir_bloco_funcionarios(data)

    if funcionario_id not in FUNCIONARIOS:
        return False, "❌ Funcionário inválido."

    ativos = data["funcionarios"]["ativos"]
    limite = data["funcionarios"].get("limite", LIMITE_FUNCIONARIOS_ATIVOS)

    if funcionario_id in ativos:
        return False, "❌ Esse funcionário já está contratado."

    if len(ativos) >= limite:
        return (
            False,
            f"❌ A fazenda já atingiu o limite de {limite} funcionários ativos.",
        )

    funcionario = FUNCIONARIOS[funcionario_id]
    custo = funcionario["contrato"]

    if data.get("moedas", 0) < custo:
        return False, f"❌ Moedas insuficientes. Contratar custa {custo} moedas rurais."

    data["moedas"] -= custo
    ativos.append(funcionario_id)

    data["funcionarios"]["historico"].append(
        {
            "acao": "contratado",
            "funcionario": funcionario_id,
            "custo": custo,
        }
    )

    salvar_state(data)

    return (
        True,
        f"✅ {funcionario['emoji']} **{funcionario['nome']}** contratado por {custo} moedas rurais.",
    )


def demitir_funcionario(
    member: nextcord.Member, funcionario_id: str
) -> tuple[bool, str]:
    if not usuario_e_noivo(member):
        return False, "❌ Apenas o noivo pode demitir funcionários diretamente."

    data = get_state()
    data = garantir_bloco_funcionarios(data)

    ativos = data["funcionarios"]["ativos"]

    if funcionario_id not in ativos:
        return False, "❌ Esse funcionário não está contratado."

    funcionario = FUNCIONARIOS.get(
        funcionario_id, {"nome": funcionario_id, "emoji": "👤"}
    )

    ativos.remove(funcionario_id)

    data["funcionarios"]["historico"].append(
        {
            "acao": "demitido",
            "funcionario": funcionario_id,
        }
    )

    salvar_state(data)

    return (
        True,
        f"✅ {funcionario['emoji']} **{funcionario['nome']}** foi desligado da fazenda.",
    )


def resumo_funcionarios_para_embed(data: dict) -> str:
    data = garantir_bloco_funcionarios(data)
    ativos = data["funcionarios"]["ativos"]
    limite = data["funcionarios"].get("limite", LIMITE_FUNCIONARIOS_ATIVOS)

    if not ativos:
        return f"_nenhum contratado_\nVagas: `0/{limite}`"

    linhas = []

    for funcionario_id in ativos:
        funcionario = FUNCIONARIOS.get(funcionario_id)

        if not funcionario:
            continue

        linhas.append(f"{funcionario['emoji']} {funcionario['nome']}")

    linhas.append(f"\nVagas: `{len(ativos)}/{limite}`")
    return "\n".join(linhas)
