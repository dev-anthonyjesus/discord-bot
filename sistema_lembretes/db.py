import json
import os
from datetime import datetime

from sistema_lembretes.config import LEMBRETES_FILE


def garantir_pasta_json() -> None:
    pasta = os.path.dirname(LEMBRETES_FILE)

    if pasta:
        os.makedirs(pasta, exist_ok=True)


def estrutura_default() -> dict:
    return {
        "ultimo_id": 0,
        "lembretes": [],
        "pets": {},
    }


def load_db() -> dict:
    if not os.path.exists(LEMBRETES_FILE):
        data = estrutura_default()
        save_db(data)
        return data

    try:
        with open(LEMBRETES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = estrutura_default()

    except Exception:
        data = estrutura_default()

    data.setdefault("ultimo_id", 0)
    data.setdefault("lembretes", [])
    data.setdefault("pets", {})

    save_db(data)
    return data


def save_db(data: dict) -> None:
    garantir_pasta_json()

    with open(LEMBRETES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def add_lembrete(
    destino: str,
    autor: str,
    autor_id: int,
    texto: str,
    prazo: str,
    prazo_label: str,
) -> dict:
    data = load_db()
    data["ultimo_id"] += 1

    lembrete = {
        "id": data["ultimo_id"],
        "destino": destino,
        "autor": autor,
        "autor_id": autor_id,
        "texto": texto,
        "prazo": prazo,
        "prazo_label": prazo_label,
        "feito": False,
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }

    data["lembretes"].append(lembrete)
    save_db(data)
    return lembrete


def listar_ativos(destino: str | None = None) -> list[dict]:
    data = load_db()
    lembretes = [item for item in data["lembretes"] if not item.get("feito", False)]

    if destino:
        lembretes = [item for item in lembretes if item.get("destino") == destino]

    return lembretes


def concluir_lembrete(lembrete_id: int) -> bool:
    data = load_db()

    for item in data["lembretes"]:
        if int(item.get("id")) == int(lembrete_id):
            item["feito"] = True
            item["concluido_em"] = datetime.now().isoformat(timespec="seconds")
            save_db(data)
            return True

    return False


def excluir_lembrete(lembrete_id: int) -> bool:
    data = load_db()
    antes = len(data["lembretes"])

    data["lembretes"] = [
        item for item in data["lembretes"] if int(item.get("id")) != int(lembrete_id)
    ]

    mudou = len(data["lembretes"]) != antes

    if mudou:
        save_db(data)

    return mudou


def get_pet_state(user_id: int, janela: str) -> dict:
    data = load_db()
    uid = str(user_id)

    data["pets"].setdefault(uid, {})
    data["pets"][uid].setdefault(janela, {"usado": False, "pets": []})

    save_db(data)
    return data["pets"][uid][janela]


def marcar_pet_alimentado(user_id: int, janela: str, pets: list[str]) -> None:
    data = load_db()
    uid = str(user_id)

    data["pets"].setdefault(uid, {})
    data["pets"][uid][janela] = {
        "usado": True,
        "pets": pets,
        "quando": datetime.now().isoformat(timespec="seconds"),
    }

    save_db(data)
