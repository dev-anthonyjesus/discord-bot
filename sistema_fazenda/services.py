from datetime import datetime, timezone

from sistema_fazenda.config import CULTIVOS, SLOTS_POR_CANTEIRO, TAXA_FORNECEDOR
from sistema_fazenda.db import get_state, salvar_state


def agora_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def formatar_tempo(segundos: int) -> str:
    segundos = max(0, int(segundos))

    if segundos < 60:
        return "menos de 1min"

    minutos = segundos // 60

    return f"{minutos}min"


def cultivo_esta_na_estacao(cultivo_id: str, estacao: str) -> bool:
    cultivo = CULTIVOS.get(cultivo_id)

    if not cultivo:
        return False

    return estacao in cultivo["estacoes"]


def lote_por_id(data: dict, lote_id: int) -> dict | None:
    for lote in data["lotes"]:
        if int(lote["id"]) == int(lote_id):
            return lote

    return None


def canteiro_por_id(lote: dict, canteiro_id: int) -> dict | None:
    for canteiro in lote["canteiros"]:
        if int(canteiro["id"]) == int(canteiro_id):
            return canteiro

    return None


def slot_vazio(slot: dict) -> bool:
    return slot.get("cultivo") is None


def contar_slots_vazios(canteiro: dict) -> int:
    return sum(1 for slot in canteiro["slots"] if slot_vazio(slot))


def slot_segundos_restantes(slot: dict) -> int:
    cultivo_id = slot.get("cultivo")

    if not cultivo_id:
        return 0

    cultivo = CULTIVOS[cultivo_id]
    plantado_em = slot.get("plantado_em")

    if not plantado_em:
        return cultivo["tempo_segundos"]

    decorrido = agora_ts() - float(plantado_em)
    restante = cultivo["tempo_segundos"] - decorrido

    return max(0, int(restante))


def slot_pronto(slot: dict) -> bool:
    if slot_vazio(slot):
        return False

    return slot_segundos_restantes(slot) <= 0


def canteiro_tem_algo(canteiro: dict) -> bool:
    return any(not slot_vazio(slot) for slot in canteiro["slots"])


def comprar_semente(cultivo_id: str, quantidade: int = 3) -> tuple[bool, str]:
    data = get_state()
    cultivo = CULTIVOS.get(cultivo_id)

    if not cultivo:
        return False, "❌ Cultivo inválido."

    quantidade = 3
    custo_total = cultivo["preco_semente"] * quantidade

    if data["moedas"] < custo_total:
        return False, f"❌ Você não tem moedas rurais suficientes. Custa {custo_total}."

    data["moedas"] -= custo_total
    data["sementes"][cultivo_id] = data["sementes"].get(cultivo_id, 0) + quantidade
    data["estatisticas"]["moedas_gastas"] += custo_total

    salvar_state(data)

    return (
        True,
        f"✅ Comprou pacote com 3 sementes de {cultivo['nome']} por {custo_total} moedas rurais.",
    )


def plantar(
    lote_id: int, canteiro_id: int, cultivo_id: str, quantidade: int = 3
) -> tuple[bool, str]:
    data = get_state()
    cultivo = CULTIVOS.get(cultivo_id)

    if not cultivo:
        return False, "❌ Cultivo inválido."

    if not cultivo_esta_na_estacao(cultivo_id, data["estacao"]):
        return False, "❌ Esse cultivo não pode ser plantado nesta estação."

    lote = lote_por_id(data, lote_id)

    if not lote:
        return False, "❌ Lote inválido."

    if not lote.get("desbloqueado"):
        return False, "🔒 Esse lote ainda está bloqueado."

    canteiro = canteiro_por_id(lote, canteiro_id)

    if not canteiro:
        return False, "❌ Canteiro inválido."

    sementes_disponiveis = data["sementes"].get(cultivo_id, 0)

    if sementes_disponiveis <= 0:
        return False, f"❌ Você não tem sementes de {cultivo['nome']}."

    espacos = contar_slots_vazios(canteiro)

    if espacos <= 0:
        return False, "❌ Esse canteiro está cheio."

    quantidade = min(int(quantidade), SLOTS_POR_CANTEIRO, sementes_disponiveis, espacos)

    custo_energia = cultivo["energia_plantar"] * quantidade

    if data["energia"] < custo_energia:
        return False, "⚡ Energia insuficiente para plantar."

    data["energia"] -= custo_energia
    data["sementes"][cultivo_id] -= quantidade

    plantado = 0

    for slot in canteiro["slots"]:
        if slot_vazio(slot) and plantado < quantidade:
            slot["cultivo"] = cultivo_id
            slot["plantado_em"] = agora_ts()
            slot["regado"] = False
            plantado += 1

    data["estatisticas"]["plantios"] += plantado

    salvar_state(data)

    return (
        True,
        f"🌱 Plantou {plantado}x {cultivo['nome']} no lote {lote_id}, canteiro #{canteiro_id}.",
    )


def colher_tudo_lote(lote_id: int) -> tuple[bool, str]:
    data = get_state()
    lote = lote_por_id(data, lote_id)

    if not lote:
        return False, "❌ Lote inválido."

    if not lote.get("desbloqueado"):
        return False, "🔒 Esse lote ainda está bloqueado."

    prontos = []

    for canteiro in lote["canteiros"]:
        for slot in canteiro["slots"]:
            if slot_pronto(slot):
                prontos.append(slot)

    if not prontos:
        return False, "⏳ Nada pronto para colher neste lote."

    custo_energia = 0
    resumo = {}

    for slot in prontos:
        cultivo_id = slot["cultivo"]
        cultivo = CULTIVOS[cultivo_id]

        custo_energia += cultivo["energia_colher"]
        resumo[cultivo_id] = resumo.get(cultivo_id, 0) + cultivo["rendimento"]

    if data["energia"] < custo_energia:
        return False, "⚡ Energia insuficiente para colher tudo."

    data["energia"] -= custo_energia

    for cultivo_id, qtd in resumo.items():
        data["celeiro"][cultivo_id] = data["celeiro"].get(cultivo_id, 0) + qtd

    for slot in prontos:
        slot["cultivo"] = None
        slot["plantado_em"] = None
        slot["regado"] = False

    data["estatisticas"]["colheitas"] += len(prontos)

    salvar_state(data)

    partes = [
        f"{qtd}x {CULTIVOS[cultivo_id]['nome']}" for cultivo_id, qtd in resumo.items()
    ]

    return True, f"🧺 Colheu tudo que estava pronto: {', '.join(partes)}."


def calcular_venda_fornecedor(cultivo_id: str) -> tuple[bool, dict | str]:
    data = get_state()
    cultivo = CULTIVOS.get(cultivo_id)

    if not cultivo:
        return False, "❌ Item inválido."

    quantidade = data["celeiro"].get(cultivo_id, 0)

    if quantidade <= 0:
        return False, f"❌ Você não tem {cultivo['nome']} no celeiro."

    bruto = cultivo["valor_venda"] * quantidade
    taxa = int(bruto * TAXA_FORNECEDOR)
    liquido = bruto - taxa

    return True, {
        "cultivo_id": cultivo_id,
        "nome": cultivo["nome"],
        "quantidade": quantidade,
        "bruto": bruto,
        "taxa": taxa,
        "liquido": liquido,
    }


def confirmar_venda_fornecedor(cultivo_id: str) -> tuple[bool, str]:
    ok, dados = calcular_venda_fornecedor(cultivo_id)

    if not ok:
        return False, str(dados)

    data = get_state()

    quantidade = int(dados["quantidade"])
    liquido = int(dados["liquido"])
    taxa = int(dados["taxa"])
    nome = dados["nome"]

    data["celeiro"].pop(cultivo_id, None)

    data["moedas"] += liquido
    data["estatisticas"]["vendas"] += quantidade
    data["estatisticas"]["moedas_ganhas"] += liquido

    salvar_state(data)

    return (
        True,
        f"💰 Venda confirmada: {quantidade}x {nome}. Entraram {liquido} moedas rurais. Taxa do fornecedor: {taxa}.",
    )


