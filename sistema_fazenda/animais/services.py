from datetime import datetime, timezone

from sistema_fazenda.db import get_state, salvar_state
from sistema_fazenda.animais.config import (
    ANIMAIS,
    RACAO_MAXIMA,
    RACAO_INICIAL,
    CUSTO_ENTREGA_RACAO,
    VALOR_ENTREGA_RACAO,
)


def agora_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def formatar_tempo(segundos: int) -> str:
    segundos = max(0, int(segundos))

    if segundos < 60:
        return "menos de 1min"

    minutos = segundos // 60

    if minutos < 60:
        return f"{minutos}min"

    horas = minutos // 60
    resto = minutos % 60

    if resto == 0:
        return f"{horas}h"

    return f"{horas}h {resto}min"


def bloco_animais_inicial() -> dict:
    return {
        "racao": RACAO_INICIAL,
        "produtos": {},
        "galinha": [],
        "vaca": [],
        "ovelha": [],
        "cabra": [],
        "cavalo": [],
        "estatisticas": {
            "animais_comprados": 0,
            "produtos_coletados": 0,
            "nascimentos": 0,
            "carne_vendida": 0,
        },
    }


def garantir_bloco_animais(data: dict) -> dict:
    if not isinstance(data.get("animais"), dict):
        data["animais"] = bloco_animais_inicial()

    animais = data["animais"]

    animais.setdefault("racao", RACAO_INICIAL)
    animais.setdefault("produtos", {})
    animais.setdefault("estatisticas", {})

    for animal_id in ANIMAIS:
        animais.setdefault(animal_id, [])

    animais["estatisticas"].setdefault("animais_comprados", 0)
    animais["estatisticas"].setdefault("produtos_coletados", 0)
    animais["estatisticas"].setdefault("nascimentos", 0)
    animais["estatisticas"].setdefault("carne_vendida", 0)

    return data


def criar_animal(animal_id: str) -> dict:
    agora = agora_ts()

    return {
        "id": f"{animal_id}_{int(agora)}",
        "tipo": animal_id,
        "criado_em": agora,
        "ultimo_produto": agora,
        "ultima_procriacao": agora,
        "nome": None,
    }


def contar_animais(data: dict, animal_id: str) -> int:
    data = garantir_bloco_animais(data)
    return len(data["animais"].get(animal_id, []))


def total_animais(data: dict) -> int:
    data = garantir_bloco_animais(data)

    total = 0
    for animal_id in ANIMAIS:
        total += len(data["animais"].get(animal_id, []))

    return total


def resumo_animais_para_embed(data: dict) -> str:
    data = garantir_bloco_animais(data)
    animais = data["animais"]

    linhas = []

    for animal_id, cfg in ANIMAIS.items():
        qtd = len(animais.get(animal_id, []))
        linhas.append(f"{cfg['emoji']} {cfg['nome']}: `{qtd}`")

    return "\n".join(linhas)


def resumo_racao_para_embed(data: dict) -> str:
    data = garantir_bloco_animais(data)
    racao = data["animais"].get("racao", RACAO_INICIAL)

    return f"Ração: `{racao}/{RACAO_MAXIMA}`"


def comprar_animal(animal_id: str, quantidade: int = 1) -> tuple[bool, str]:
    data = get_state()
    data = garantir_bloco_animais(data)

    if animal_id not in ANIMAIS:
        return False, "❌ Animal inválido."

    quantidade = max(1, int(quantidade))
    cfg = ANIMAIS[animal_id]
    custo = cfg["preco_compra"] * quantidade

    if data.get("moedas", 0) < custo:
        return False, f"❌ Moedas insuficientes. Custa {custo} moedas rurais."

    data["moedas"] -= custo

    for _ in range(quantidade):
        data["animais"][animal_id].append(criar_animal(animal_id))

    data["animais"]["estatisticas"]["animais_comprados"] += quantidade

    salvar_state(data)

    return True, f"✅ Comprou {quantidade}x {cfg['nome']} por {custo} moedas rurais."


def pedir_entrega_racao() -> tuple[bool, str]:
    data = get_state()
    data = garantir_bloco_animais(data)

    if data.get("moedas", 0) < CUSTO_ENTREGA_RACAO:
        return (
            False,
            f"❌ Moedas insuficientes. A entrega custa {CUSTO_ENTREGA_RACAO} moedas rurais.",
        )

    data["moedas"] -= CUSTO_ENTREGA_RACAO
    data["animais"]["racao"] = min(
        RACAO_MAXIMA, data["animais"].get("racao", 0) + VALOR_ENTREGA_RACAO
    )

    salvar_state(data)

    return (
        True,
        f"🚚 Entrega recebida! Ração agora está em {data['animais']['racao']}/{RACAO_MAXIMA}.",
    )


def segundos_para_produto(animal: dict) -> int:
    animal_id = animal["tipo"]
    cfg = ANIMAIS[animal_id]

    if cfg["tempo_produto_segundos"] is None:
        return 0

    decorrido = agora_ts() - float(animal.get("ultimo_produto", agora_ts()))
    restante = cfg["tempo_produto_segundos"] - decorrido

    return max(0, int(restante))


def animal_produto_pronto(animal: dict) -> bool:
    animal_id = animal["tipo"]
    cfg = ANIMAIS[animal_id]

    if cfg["produto"] is None:
        return False

    return segundos_para_produto(animal) <= 0


def coletar_produtos(local: str) -> tuple[bool, str]:
    data = get_state()
    data = garantir_bloco_animais(data)

    racao = data["animais"].get("racao", 0)
    coletados = {}

    for animal_id, cfg in ANIMAIS.items():
        if cfg["local"] != local:
            continue

        if cfg["produto"] is None:
            continue

        for animal in data["animais"].get(animal_id, []):
            if not animal_produto_pronto(animal):
                continue

            consumo = cfg["consumo_racao_produto"]

            if racao < consumo:
                continue

            racao -= consumo
            produto_id = cfg["produto"]
            coletados[produto_id] = coletados.get(produto_id, 0) + 1
            animal["ultimo_produto"] = agora_ts()

    if not coletados:
        return False, "⏳ Nenhum produto pronto ou ração insuficiente."

    data["animais"]["racao"] = racao

    for produto_id, qtd in coletados.items():
        data["animais"]["produtos"][produto_id] = (
            data["animais"]["produtos"].get(produto_id, 0) + qtd
        )

    data["animais"]["estatisticas"]["produtos_coletados"] += sum(coletados.values())

    salvar_state(data)

    partes = []
    for produto_id, qtd in coletados.items():
        nome = produto_id.replace("_", " ")
        partes.append(f"{qtd}x {nome}")

    return True, f"✅ Produtos coletados: {', '.join(partes)}."


def calcular_status_local(local: str) -> dict:
    data = get_state()
    data = garantir_bloco_animais(data)

    resultado = {
        "local": local,
        "animais": [],
        "racao": data["animais"].get("racao", RACAO_INICIAL),
    }

    for animal_id, cfg in ANIMAIS.items():
        if cfg["local"] != local:
            continue

        lista = data["animais"].get(animal_id, [])
        quantidade = len(lista)

        prontos = 0
        menor_tempo = None

        for animal in lista:
            if cfg["produto"] is None:
                continue

            restante = segundos_para_produto(animal)

            if restante <= 0:
                prontos += 1
            else:
                menor_tempo = (
                    restante if menor_tempo is None else min(menor_tempo, restante)
                )

        resultado["animais"].append(
            {
                "id": animal_id,
                "nome": cfg["nome"],
                "emoji": cfg["emoji"],
                "quantidade": quantidade,
                "produto_nome": cfg["produto_nome"],
                "produto_emoji": cfg["produto_emoji"],
                "prontos": prontos,
                "proximo": menor_tempo,
            }
        )

    return resultado
