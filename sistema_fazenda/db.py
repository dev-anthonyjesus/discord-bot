import json
import os
from datetime import datetime

from sistema_fazenda.config import (
    FAZENDA_FILE,
    ENERGIA_INICIAL,
    ENERGIA_MAXIMA,
    ESTACAO_INICIAL,
    SEMENTES_INICIAIS,
    MOEDAS_INICIAIS,
    TOTAL_LOTES,
    CANTEIROS_POR_LOTE,
    SLOTS_POR_CANTEIRO,
    LOTES_DESBLOQUEADOS_INICIAIS,
)


def garantir_pasta_json() -> None:
    pasta = os.path.dirname(FAZENDA_FILE)

    if pasta:
        os.makedirs(pasta, exist_ok=True)


def criar_canteiro(canteiro_id: int) -> dict:
    return {
        "id": canteiro_id,
        "slots": [
            {
                "cultivo": None,
                "plantado_em": None,
                "regado": False,
            }
            for _ in range(SLOTS_POR_CANTEIRO)
        ],
    }


def criar_lotes() -> list[dict]:
    lotes = []

    for lote_id in range(1, TOTAL_LOTES + 1):
        desbloqueado = lote_id in LOTES_DESBLOQUEADOS_INICIAIS

        lotes.append(
            {
                "id": lote_id,
                "desbloqueado": desbloqueado,
                "nivel": 1 if desbloqueado else 0,
                "canteiros": [criar_canteiro(i + 1) for i in range(CANTEIROS_POR_LOTE)],
            }
        )

    return lotes


def bloco_funcionarios_inicial() -> dict:
    return {
        "ativos": [],
        "historico": [],
        "limite": 4,
    }


def estado_inicial() -> dict:
    return {
        "moedas": MOEDAS_INICIAIS,
        "energia": ENERGIA_INICIAL,
        "energia_maxima": ENERGIA_MAXIMA,
        "estacao": ESTACAO_INICIAL,
        "dia": 1,
        "lotes": criar_lotes(),
        "sementes": SEMENTES_INICIAIS.copy(),
        "celeiro": {},
        "processados": {},
        "animais": {},
        "funcionarios": bloco_funcionarios_inicial(),
        "estatisticas": {
            "plantios": 0,
            "colheitas": 0,
            "vendas": 0,
            "moedas_ganhas": 0,
            "moedas_gastas": 0,
        },
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }


def garantir_chaves(data: dict) -> dict:
    data.setdefault("moedas", MOEDAS_INICIAIS)
    data.setdefault("energia", ENERGIA_INICIAL)
    data.setdefault("energia_maxima", ENERGIA_MAXIMA)
    data.setdefault("estacao", ESTACAO_INICIAL)
    data.setdefault("dia", 1)
    data.setdefault("lotes", criar_lotes())
    data.setdefault("sementes", SEMENTES_INICIAIS.copy())
    data.setdefault("celeiro", {})
    data.setdefault("processados", {})
    data.setdefault("animais", {})
    data.setdefault("estatisticas", {})
    data.setdefault("funcionarios", bloco_funcionarios_inicial())

    data["estatisticas"].setdefault("plantios", 0)
    data["estatisticas"].setdefault("colheitas", 0)
    data["estatisticas"].setdefault("vendas", 0)
    data["estatisticas"].setdefault("moedas_ganhas", 0)
    data["estatisticas"].setdefault("moedas_gastas", 0)

    data["funcionarios"].setdefault("ativos", [])
    data["funcionarios"].setdefault("historico", [])
    data["funcionarios"].setdefault("limite", 4)

    return data


def load_db() -> dict:
    if not os.path.exists(FAZENDA_FILE):
        data = estado_inicial()
        save_db(data)
        return data

    try:
        with open(FAZENDA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = estado_inicial()

    except Exception:
        data = estado_inicial()

    data = garantir_chaves(data)

    save_db(data)
    return data


def save_db(data: dict) -> None:
    garantir_pasta_json()

    data["atualizado_em"] = datetime.now().isoformat(timespec="seconds")

    with open(FAZENDA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_state() -> dict:
    return load_db()


def salvar_state(data: dict) -> None:
    save_db(data)


def reset_fazenda() -> dict:
    data = estado_inicial()
    save_db(data)
    return data


def repor_energia(valor: int = 100) -> dict:
    data = load_db()
    data["energia"] = max(0, min(int(valor), data.get("energia_maxima", 100)))
    save_db(data)
    return data


def marcar_tudo_pronto() -> dict:
    data = load_db()

    for lote in data.get("lotes", []):
        for canteiro in lote.get("canteiros", []):
            for slot in canteiro.get("slots", []):
                if slot.get("cultivo"):
                    slot["plantado_em"] = 0

    save_db(data)
    return data
