import json
import os
from datetime import datetime

from sistema_bebe.config import (
    BEBE_FILE,
    STATUS_INICIAL,
    DISPOSICAO_INICIAL,
    CARGO_NOIVO_ID,
    CARGO_NOIVA_ID,
    MELHORIAS_INICIAIS,
    MODO_TESTE_PADRAO,
)


def garantir_pasta_json() -> None:
    pasta = os.path.dirname(BEBE_FILE)

    if pasta:
        os.makedirs(pasta, exist_ok=True)


def estado_inicial() -> dict:
    return {
        "ativo": False,
        "modo_teste": MODO_TESTE_PADRAO,
        "fase": "escolha_tracos",
        "tracos": {
            str(CARGO_NOIVO_ID): None,
            str(CARGO_NOIVA_ID): None,
        },
        "status": STATUS_INICIAL.copy(),
        "humor": "Calminho",
        "pais": {
            str(CARGO_NOIVO_ID): {
                "nome": "noivo",
                "disposicao": DISPOSICAO_INICIAL,
                "cuidados_hoje": 0,
            },
            str(CARGO_NOIVA_ID): {
                "nome": "noiva",
                "disposicao": DISPOSICAO_INICIAL,
                "cuidados_hoje": 0,
            },
        },
        "ultimo_cuidado": None,
        "sequencia_cuidados": {
            "ultimo_cargo": None,
            "quantidade": 0,
        },
        "noite": {
            "modo_noturno": False,
            "score": None,
            "resultado": None,
            "abajur_ativo": False,
            "colica_ativa": False,
        },
        "melhorias": MELHORIAS_INICIAIS.copy(),
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }


def load_db() -> dict:
    if not os.path.exists(BEBE_FILE):
        data = estado_inicial()
        save_db(data)
        return data

    try:
        with open(BEBE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = estado_inicial()

    except Exception:
        data = estado_inicial()

    return data


def save_db(data: dict) -> None:
    garantir_pasta_json()

    data["atualizado_em"] = datetime.now().isoformat(timespec="seconds")

    with open(BEBE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def reset_bebe() -> dict:
    data = estado_inicial()
    save_db(data)
    return data


def get_state() -> dict:
    return load_db()


def set_modo_teste(valor: bool) -> None:
    data = load_db()
    data["modo_teste"] = valor
    save_db(data)


def set_traco(cargo_id: int, traco: str) -> dict:
    data = load_db()
    data["tracos"][str(cargo_id)] = traco

    if all(data["tracos"].values()):
        data["ativo"] = True
        data["fase"] = "cuidados"

    save_db(data)
    return data


def salvar_state(data: dict) -> None:
    save_db(data)


def repor_disposicao(valor: int = 100) -> dict:
    data = load_db()

    for uid in data["pais"]:
        data["pais"][uid]["disposicao"] = valor

    save_db(data)
    return data
