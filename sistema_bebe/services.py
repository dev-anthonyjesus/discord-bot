import random

import nextcord

from sistema_bebe.config import (
    ACOES_BASICAS,
    ACOES_PAGAS,
    CARGO_NOIVO_ID,
    CARGO_NOIVA_ID,
)
from sistema_bebe.db import get_state, salvar_state
from sistema_bebe.emojis import E
from sistema_economia.db import get_moedas, remove_moedas


def clamp(valor: int) -> int:
    return max(0, min(100, int(valor)))


def cargo_do_usuario(member: nextcord.Member) -> int | None:
    role_ids = {role.id for role in member.roles}

    if CARGO_NOIVO_ID in role_ids:
        return CARGO_NOIVO_ID

    if CARGO_NOIVA_ID in role_ids:
        return CARGO_NOIVA_ID

    return None


def nome_cargo(cargo_id: int) -> str:
    if cargo_id == CARGO_NOIVO_ID:
        return "noivo"

    if cargo_id == CARGO_NOIVA_ID:
        return "noiva"

    return "responsável"


def nome_visual_acao(acao: dict) -> str:
    return f"{E(acao['emoji'])} {acao['label']}"


def calcular_humor(status: dict) -> str:
    media = sum(status.values()) / len(status)

    if media >= 85:
        return "Muito feliz"

    if media >= 70:
        return "Calminho"

    if media >= 55:
        return "Manhoso"

    if media >= 40:
        return "Choroso"

    return "Irritado"


def frase_bebe(humor: str) -> str:
    frases = {
        "Muito feliz": "Eu tô rindo à toa hoje.",
        "Calminho": "Eu tô quietinho, só observando tudo.",
        "Manhoso": "Eu queria um colinho agora...",
        "Choroso": "Eu não sei explicar, mas alguma coisa tá incomodando.",
        "Irritado": "Eu tô muito incomodado e preciso de cuidado logo.",
    }

    return frases.get(humor, "Eu só quero carinho.")


def aplicar_acao_basica(member: nextcord.Member, acao_id: str) -> tuple[bool, str]:
    data = get_state()
    cargo_id = cargo_do_usuario(member)

    if cargo_id is None:
        return False, "❌ Apenas o casal pode cuidar do bebê."

    if not data.get("ativo"):
        return False, "❌ O bebê ainda não começou. Use `/painelbebe` primeiro."

    acao = ACOES_BASICAS.get(acao_id)

    if not acao:
        return False, "❌ Ação inválida."

    pai = data["pais"][str(cargo_id)]
    custo = acao["custo_disposicao"]

    if pai["disposicao"] < custo:
        return False, "😵 Você não tem disposição suficiente para esse cuidado."

    for campo, efeito in acao["efeitos"].items():
        data["status"][campo] = clamp(data["status"].get(campo, 0) + efeito)

    pai["disposicao"] = clamp(pai["disposicao"] - custo)
    pai["cuidados_hoje"] += 1

    ultimo_cargo = data["sequencia_cuidados"].get("ultimo_cargo")

    if ultimo_cargo == str(cargo_id):
        data["sequencia_cuidados"]["quantidade"] += 1
    else:
        data["sequencia_cuidados"]["ultimo_cargo"] = str(cargo_id)
        data["sequencia_cuidados"]["quantidade"] = 1

    if data["sequencia_cuidados"]["quantidade"] >= 3:
        pai["disposicao"] = clamp(pai["disposicao"] - 5)

    data["ultimo_cuidado"] = {
        "acao": nome_visual_acao(acao),
        "por": nome_cargo(cargo_id),
    }

    data["humor"] = calcular_humor(data["status"])

    salvar_state(data)

    return True, f"✅ {nome_visual_acao(acao)} realizado."


def aplicar_acao_paga(member: nextcord.Member, acao_id: str) -> tuple[bool, str]:
    data = get_state()
    cargo_id = cargo_do_usuario(member)

    if cargo_id is None:
        return False, "❌ Apenas o casal pode usar adicionais."

    if not data.get("ativo"):
        return False, "❌ O bebê ainda não começou. Use `/painelbebe` primeiro."

    acao = ACOES_PAGAS.get(acao_id)

    if not acao:
        return False, "❌ Ação paga inválida."

    preco = acao["preco"]

    if get_moedas(member.id) < preco:
        return False, f"❌ Você não tem moedas suficientes. Custa {preco} moedas."

    ok = remove_moedas(member.id, preco)

    if not ok:
        return False, "❌ Não consegui descontar suas moedas."

    for campo, efeito in acao["efeitos"].items():
        data["status"][campo] = clamp(data["status"].get(campo, 0) + efeito)

    if acao.get("ativa_noite_tranquila"):
        data["noite"]["abajur_ativo"] = True

    if acao.get("cura_colica"):
        data["noite"]["colica_ativa"] = False

    data["ultimo_cuidado"] = {
        "acao": nome_visual_acao(acao),
        "por": nome_cargo(cargo_id),
    }

    data["humor"] = calcular_humor(data["status"])

    salvar_state(data)

    return True, f"✅ {nome_visual_acao(acao)} comprado por {preco} moedas."


def decair_status_manual() -> dict:
    """
    Queda manual para teste.

    Depois, quando o sistema tiver loop por horário, essa função pode ser chamada
    automaticamente ao longo do dia.
    """
    data = get_state()
    tracos = list(data["tracos"].values())

    fome_delta = -8 if "faminto" in tracos else -5
    sono_delta = -3 if "dorminhoco" in tracos else -5
    atencao_delta = -8 if "carente" in tracos else -5
    higiene_delta = -8 if "bagunceiro" in tracos else -5

    data["status"]["fome"] = clamp(data["status"]["fome"] + fome_delta)
    data["status"]["sono"] = clamp(data["status"]["sono"] + sono_delta)
    data["status"]["atencao"] = clamp(data["status"]["atencao"] + atencao_delta)
    data["status"]["higiene"] = clamp(data["status"]["higiene"] + higiene_delta)
    data["status"]["fralda"] = clamp(data["status"]["fralda"] - 6)

    data["humor"] = calcular_humor(data["status"])

    salvar_state(data)
    return data


def calcular_score_noite(data: dict) -> int:
    status = data["status"]
    score = 0

    if status["fome"] >= 65:
        score += 20

    if status["fralda"] >= 65:
        score += 20

    if status["higiene"] >= 60:
        score += 15

    if status["sono"] >= 50:
        score += 15

    if status["atencao"] >= 50:
        score += 10

    humor_media = sum(status.values()) / len(status)

    if humor_media >= 60:
        score += 20

    if data["noite"].get("abajur_ativo"):
        score += 25

    if data["noite"].get("colica_ativa"):
        score -= 25

    return max(0, min(100, score))


def processar_noite() -> dict:
    data = get_state()
    score = calcular_score_noite(data)

    if score >= 80:
        resultado = "tranquila"
    elif score >= 60:
        resultado = "ok"
    elif score >= 40:
        resultado = "agitada"
    else:
        resultado = "ruim"

    data["noite"]["modo_noturno"] = True
    data["noite"]["score"] = score
    data["noite"]["resultado"] = resultado

    salvar_state(data)
    return data


def processar_manha() -> dict:
    data = get_state()
    resultado = data["noite"].get("resultado") or "ok"

    if resultado == "tranquila":
        disp_noivo = 100
        disp_noiva = 100
        msg = "🌙 O bebê dormiu a noite toda sem problemas. Os responsáveis acordaram descansados."
    elif resultado == "ok":
        disp_noivo = random.randint(90, 100)
        disp_noiva = random.randint(90, 100)
        msg = "🌤️ A câmera registrou uma noite tranquila, com alguns pequenos movimentos no bercinho."
    elif resultado == "agitada":
        disp_noivo = random.randint(75, 90)
        disp_noiva = random.randint(75, 90)
        msg = "😭 A câmera registrou chorinhos durante a madrugada. O descanso foi um pouco abalado."
    else:
        disp_noivo = random.randint(60, 85)
        disp_noiva = random.randint(60, 85)
        msg = "🚨 A câmera registrou uma madrugada difícil. O bebê acordou chorando e precisou de atenção."

    data["pais"][str(CARGO_NOIVO_ID)]["disposicao"] = disp_noivo
    data["pais"][str(CARGO_NOIVA_ID)]["disposicao"] = disp_noiva

    data["pais"][str(CARGO_NOIVO_ID)]["cuidados_hoje"] = 0
    data["pais"][str(CARGO_NOIVA_ID)]["cuidados_hoje"] = 0

    data["status"] = {
        "fome": random.randint(55, 75),
        "fralda": random.randint(55, 80),
        "sono": random.randint(45, 70),
        "atencao": random.randint(50, 75),
        "higiene": random.randint(55, 80),
    }

    data["humor"] = calcular_humor(data["status"])
    data["noite"]["modo_noturno"] = False
    data["noite"]["abajur_ativo"] = False

    if random.random() < 0.18:
        data["noite"]["colica_ativa"] = True
        msg += "\n\n😭 Chorinho sem motivo aparente. Parece cólica. Talvez seja bom comprar um remédio."

    salvar_state(data)

    return {
        "state": data,
        "mensagem": msg,
    }
